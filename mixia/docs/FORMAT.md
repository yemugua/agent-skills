# 秘匣保险库格式规范 v1

这份文档是**规范**，不是实现说明。任何程序只要按这里的描述，就能在不知道秘匣存在的情况下
解开一个保险库。这么做只有一个目的：**即使秘匣不再维护，你的文件也解得开。**

本文档与 `src-tauri/src/crypto.rs`、`src-tauri/src/vault.rs` 一一对应，
`src-tauri/src/bin/mixia-cli.rs` 是它的参考实现之一。

## 0. 术语与常量

| 名称 | 值 | 说明 |
| --- | --- | --- |
| `KEY_LEN` | 32 字节 | 所有对称密钥长度 |
| `NONCE_LEN` | 24 字节 | XChaCha20-Poly1305 nonce |
| `TAG_LEN` | 16 字节 | Poly1305 认证标签（由 AEAD 附加在密文尾部） |
| `CHUNK_SIZE` | 1 MiB = 1048576 字节 | 分块明文大小 |
| `BLOB_MAGIC` | `"MIXBLOB1"` | 密文对象文件头 |
| `HEADER_MAGIC` | `"MIXIA01"` | vault.json 的 magic 字段 |
| `INDEX_MAGIC` | `"MIXIDX01"` | index.enc 明文的前 8 字节 |
| `FORMAT_VERSION` | 1 | 索引与头部共用 |

这些以 `MIX` 开头的标识和所有 `mixia-*-v1` AAD 域名是格式的一部分，与软件叫什么名字无关：
产品名改过，它们也不改，改了就是破坏格式、老库解不开。

算法：

- 认证加密统一使用 **XChaCha20-Poly1305**（AEAD， Associated Data 参与认证）。
- 密钥派生使用 **Argon2id**，参数固定写在头部里，因此参数可以随版本升级。
- 所有 base64 均为标准字母表、带 padding。
- 所有整数（长度、标志、块号）均为**小端**。

## 1. 目录结构

一个保险库就是一个普通文件夹，可以整体复制、移动、备份：

```
<保险库目录>/
├── vault.json      # 明文头部：KDF 参数 + 被包装的主密钥
├── index.enc       # 加密索引：全部文件的元数据
├── blobs/<id>.bin  # 每个文件的密文
└── thumbs/<id>.bin # 图片缩略图密文（可选）
```

`<id>` 是 UUID v4 字符串（36 字符）。文件名里**不含任何用户可见信息**。

写入约定：所有文件先写 `.mixia-<id8>.part` 或 `.<id>.part` 临时文件，
再 `rename` 覆盖目标，保证任何一步中断都不会留下半截索引。
解锁时 `blobs/` 与 `thumbs/` 里凡是不属于索引的文件、以及 `.part` 残留都会被删除。

## 2. vault.json（明文）

```json
{
  "magic": "MIXIA01",
  "version": 1,
  "created_at": 1761480000,
  "kdf": {
    "name": "argon2id",
    "m_cost": 65536,
    "t_cost": 3,
    "p_cost": 4,
    "salt": "<base64, 16 字节>"
  },
  "wrap": { "data": "<base64, 见下文>" }
}
```

- `m_cost` 单位是 KiB，即 64 MiB 内存；`t_cost` 为 3 轮；`p_cost` 为 4 并行度。
- `created_at` 是 Unix 秒。

### 2.1 KEK 派生

```
KEK = Argon2id(password, salt, m_cost, t_cost, p_cost, output_len = 32)
```

`password` 直接取 UTF-8 字节，不做归一化、不加盐前缀。

### 2.2 主密钥 MK

`wrap.data` 是下面这个密封块的 base64：

```
MK          = 32 字节随机数（每个保险库一个，创建时生成，永不改变）
wrap.data   = base64( XChaCha20Poly1305.seal(KEK, MK, nonce=rand24, aad="mixia-mk-v1") )
              密文布局：nonce(24) || ciphertext || tag(16)
```

解 `wrap.data` 得到 MK，是打开保险库的第一步。密码错误时 Poly1305 校验必然失败，
因此"密码错误"和"数据损坏"在同一条路径上，统一报 `BadPassword`。

**改密码只重新计算 KEK 并重新包装 MK**，不重新加密任何文件，所以瞬间完成。

## 3. index.enc（加密索引）

```
明文 = "MIXIDX01" || serde_json(Manifest)
index.enc = XChaCha20Poly1305.seal(MK, 明文, aad="mixia-index-v1")
```

`Manifest`：

```json
{ "version": 1, "items": [ { ...Item... } ] }
```

`Item`：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | UUID v4，同时决定 `blobs/<id>.bin` 与 `thumbs/<id>.bin` 的路径 |
| `name` | string | 原始文件名（含扩展名），**在索引里，因此是密文** |
| `path` | string，**可选** | 导入时的相对路径，`/` 分隔，最后一段等于 `name`；导入整个文件夹时，第一段就是那个文件夹自己的名字。缺省表示平铺导入或旧库 |
| `size` | u64 | 明文字节数 |
| `mime` | string | 由扩展名猜测 |
| `kind` | string | `image` / `video` / `audio` / `document` / `other` |
| `added_at` | u64 | Unix 秒 |
| `chunks` | u32 | 密文块数量，解密时用于检测截断 |
| `has_thumb` | bool | 是否存在缩略图 |
| `key` | `{data: base64}` | 被 MK 包装的**该文件自己的密钥** |

```
key.data = seal(MK, file_key(32 随机字节), aad="mixia-fk-v1:" + id)
```

每个文件独立密钥的意义：单个密文块被针对性攻击时影响面不叠加，
且删除文件后其密钥随索引消失，不需要"重加密剩余文件"。

### `path` 的还原规则

整库导出时目标路径 = `输出目录 / path`（`path` 为空则用 `name`）。
**实现必须把 `path` 当作不可信输入**：即使它有 AEAD 保护，也要在拼接前拒绝
绝对路径、盘符、UNC、空段、`.` 与 `..`，任何一项不合格就退化成只用 `name`。
否则一个被手工篡改过的索引可以让你把明文写到输出目录之外的任意位置。

这是向后兼容的新增字段：不认识它的读取方忽略即可，仍能用 `name` 平铺导出。

## 4. blobs/&lt;id&gt;.bin（文件密文）

```
"MIXBLOB1"                       # 8 字节
repeat:
  u32  plaintext_len             # 本块明文长度
  u32  flags                     # bit0 = 1 表示这是最后一块
  bytes nonce[24]
  bytes ciphertext[plaintext_len + 16]   # 含 Poly1305 tag
```

每块的 AAD：

```
base = "mixia-chunk-v1" || domain || ":" || id        # domain 为 "blob" 或 "thumb"
aad  = base || u32_le(chunk_index) || u8(final ? 1 : 0)
```

把块号和 final 标志绑进 AAD，意味着**重排序、删除中间块、复制别的文件的块**
都会导致认证失败；`chunks` 字段与"读完后必须正好是文件末尾"两道检查共同防止截断。

分块规则：

- 明文按 1 MiB 切块；
- 最后一块 `plaintext_len < CHUNK_SIZE` 且 `flags.bit0 = 1`；
- 明文长度恰好是 1 MiB 整数倍时，**额外再写一个 `plaintext_len = 0` 的 final 块**；
- 空文件即只有一个 `plaintext_len = 0` 的 final 块，所以 `chunks` 至少为 1。

解密时逐块认证，并核对解出的总长度是否等于索引里的 `size`。

## 5. thumbs/&lt;id&gt;.bin（缩略图）

仅对 `kind = image` 且原文件 ≤ 40 MiB 的条目生成：

```
明文 = JPEG（长边 ≤ 480 像素）
thumb = XChaCha20Poly1305.seal(MK, 明文, aad="mixia-thumb-v1:" + id)
```

缩略图用 MK 而不是文件密钥，是为了批量读缩略图时不必逐个解包文件密钥。

## 6. 打开一个保险库的完整步骤

```
1. 读 vault.json，取 kdf.salt / kdf 参数 / wrap.data
2. KEK  = Argon2id(password, salt, ...)
3. MK   = open(KEK, base64decode(wrap.data), "mixia-mk-v1")     # 失败 = 密码错误或数据损坏
4. 明文 = open(MK, index.enc, "mixia-index-v1")
   断言前 8 字节 == "MIXIDX01"，其余 JSON 解析成 Manifest
5. 对某个 item：
   file_key = open(MK, base64decode(item.key.data), "mixia-fk-v1:" + item.id)
   按第 4 节的布局用 file_key 解 blobs/<id>.bin，校验块数与总长度
```

## 7. 版本与兼容

- `vault.json` 的 `version` 与 `index.enc` 里 `Manifest.version` 目前都是 1。
- 破坏性变更（换算法、改 AAD 构造、改块头）必须升 `version`，
  同时提供把旧库无损迁移到新库的工具，并且**保留旧版本的解密代码**。
- 新增字段应保证旧版本读取时能忽略（JSON 层面），不要把新语义塞进 v1 的旧字段。

## 8. 参考实现

| 实现 | 用途 |
| --- | --- |
| `src-tauri/src/crypto.rs` + `vault.rs` | 权威实现，含单元测试 |
| `src-tauri/src/bin/mixia-cli.rs` | 命令行读写：`info` / `list` / `verify` / `export` / `extract` / `import` |

如果你用别的语言重写了这套格式，欢迎把实现链接补到这里，供他人交叉验证。
