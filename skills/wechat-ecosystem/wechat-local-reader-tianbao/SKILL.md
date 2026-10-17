---
name: wechat-local-reader
slug: wechat-local-reader-tianbao
displayName: 微信本地读取导出
display_name: "微信本地读取导出"
display_name_en: "WeChat Local Reader"
version: "1.1.1"
summary: 本机解密、零上传。把微信电脑版的聊天记录、群消息、联系人、收藏导出成 Markdown 或纯文本，支持时间区间筛选和手机号/身份证/银行卡/邮箱自动脱敏。
description: 在本机读取你自己登录的微信电脑版加密数据库，把聊天记录、群消息、联系人、收藏导出成 Markdown 或纯文本，可按时间区间筛选，可选自动脱敏手机号/身份证/银行卡/邮箱。全程本地解密、零上传。当用户说"导出微信聊天记录""把某个群的聊天导出来""查一下我和某某的聊天""搜微信里提到某关键词的消息""整理微信聊天做日报/总结/归档"时使用。仅支持 Windows / macOS / Linux 桌面端微信，不支持手机、平板、鸿蒙；仅限本人本机数据。
description_zh: "在本机解密你本人登录的微信电脑版数据库，把聊天记录、群消息、联系人、收藏导出成 Markdown / 纯文本，支持时间筛选与敏感信息脱敏。全程本地运行、零上传。"
description_en: "Decrypt your own WeChat desktop database locally and export chats, group messages, contacts and favorites to Markdown or plain text, with time-range filtering and optional masking of phone numbers, ID and bank card numbers. Fully local, zero upload."
license: Apache-2.0
author: 刘天宝（改进版）；原 Skill「微信本地管家」作者：宜生
category: 实用工具
tags: [微信, 聊天记录, 导出, 本地隐私, Markdown, 数据归档, 群消息, 脱敏]
language: zh-CN
visibility: public
agent_created: true
platforms:
  - WorkBuddy
---

# 微信本地读取 / 导出工具（wechat-local-reader）

把你自己电脑上登录的微信，变成一个可查询、可导出的本地数据源。

核心能力：解密微信本地数据库 → 读出会话、消息、联系人、群成员、收藏 → 导出成 Markdown / txt → 可选脱敏。

**全程在本机完成，没有任何网络请求**——工具代码里不存在上传逻辑，聊天数据不出你的电脑。

> 本版为改进版。原始 Skill（slug `wechat-local-butler`，显示名「微信本地管家」）由 SkillHub 用户「宜生」创作；
> 底层工具 `wechat-cli` 为 Apache-2.0 开源项目。本版修复了若干 Windows 实测缺陷，说明文档为重新撰写。
> 详细的许可证与归属信息见 `tool/README_CN.md`「归属与许可声明」章节。

---

## 一、先确认适用范围

| 环境 | 支持情况 |
|---|---|
| Windows 微信 4.x | ✅ 开箱可用（4.1+ 走只读扫描，无需管理员权限） |
| macOS | ⚠️ SkillHub 禁止上传二进制可执行文件，发布包未内置 helper，需自行编译 `find_all_keys_macos.c` |
| Linux | ✅ 可用 |
| 手机 / 平板 / 鸿蒙 | ❌ 不支持。数据在 App 沙盒里，没有可扫描的桌面进程 |

**只用于读取你本人、本机登录的微信。** 拿去读别人的账号是侵犯隐私，责任自负。

---

## 二、安装

依赖 Python ≥ 3.10。

```bash
# Windows
.\tool\setup.ps1

# macOS / Linux
bash tool/setup.sh
```

脚本会建 `.venv`、装依赖、生成 `wechat-cli.bat` 启动器。

装完把 `tool/` 加入 PATH，或用绝对路径调用 `tool/wechat-cli.bat`。

---

## 三、使用流程

### 第 1 步：提取密钥（只需做一次）

微信电脑版必须**已登录且正在运行**。

```bash
wechat-cli init
```

成功后密钥存到 `~/.wechat-cli/all_keys.json`，之后所有查询都用它解密，不用再登录也不用联网。

**什么时候需要重跑：**

| 情况 | 要不要重跑 |
|---|---|
| 微信大版本升级 | ✅ `wechat-cli init --force` |
| 换账号登录 | ✅ 且要换 `--db-dir` |
| 提示「密钥文件不存在」 | ✅ |
| 日常导出 | ❌ |

### 第 2 步：看看有哪些会话

```bash
wechat-cli sessions --limit 20
```

这一步是为了拿到**准确的群名/联系人名**——后面的命令要求名字一字不差，包括全角符号。

### 第 3 步：导出

```bash
wechat-cli export "群名或联系人名" --format markdown --limit 500 --output "D:\导出\xxx.md"
```

**参数：**

| 参数 | 说明 |
|---|---|
| `--format` | `markdown` 或 `txt` |
| `--output` | 输出路径；不写就打到屏幕 |
| `--limit` | 条数 |
| `--start-time` / `--end-time` | 时间区间，`YYYY-MM-DD` 或带时分秒 |
| `--mask` | 脱敏手机号 / 身份证 / 银行卡 / 邮箱 |

按月份导出：

```bash
wechat-cli export "某某群" --start-time "2026-09-01" --end-time "2026-09-30" --output "9月.md"
```

### 第 4 步（可选）：清理明文缓存

```bash
wechat-cli clean
```

删掉解密产生的明文副本，**不会动微信原始数据**。公用电脑上建议用完就清。

---

## 四、全部命令

| 命令 | 作用 |
|---|---|
| `sessions` | 最近会话列表 |
| `history "名字" --limit N` | 某会话最近 N 条消息 |
| `search "关键词"` | 全局搜消息内容，可加 `--chat` 限定在某个群 |
| `export "名字"` | 导出为 md / txt |
| `new-messages` | 自上次调用以来的增量消息 |
| `contacts --query "李"` | 搜联系人 |
| `members "群名"` | 群成员列表 |
| `stats` | 聊天统计 |
| `unread` | 未读会话 |
| `favorites` | 微信收藏 |
| `clean` | 清理解密缓存 |

---

## 五、排错

### 报「0/N salts 找到密钥」——先怀疑账号选错

一台电脑登录过多个微信号时，数据目录下会有多个账号的 `db_storage`。**请先确认当前登录的是哪个账号**：

```powershell
Get-ChildItem "D:\xxx\xwechat_files" -Directory | ForEach-Object {
  $db = Join-Path $_.FullName "db_storage"
  if (Test-Path $db) {
    $r = Get-ChildItem $db -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $_.Name + " | " + $r.LastWriteTime
  }
}
```

最近有写入、体积最大的那个就是当前账号。然后显式指定：

```bash
wechat-cli init --db-dir "D:\xxx\xwechat_files\<当前账号>\db_storage"
```

> 本改进版已对候选目录按活跃度排序，但仍建议多账号环境显式指定，最稳妥。

### 提示找不到微信数据目录

微信没运行，或数据目录不在默认位置（被搬过家、改过路径）。用 `--db-dir` 手动指定。

### Windows 下中文输出乱码

PowerShell 捕获 CLI 输出时，默认按 GBK 解码 Python 写出的 UTF-8 字节。调用前加：

```powershell
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

在 cmd 里直接运行不受影响（CLI 已自动把控制台代码页切到 65001）。

### 写 bat 脚本要注意

**Windows 的 .bat 不能存成 UTF-8**——cmd 按 ANSI 逐字节解析，中文会吞掉相邻字符，出现 `set` 变 `et` 之类的诡异报错。需要中文交互脚本时，用纯 ASCII 的 .bat 做引导器（`powershell -File xxx.ps1`），逻辑写在 UTF-8 **带 BOM** 的 .ps1 里。

### 解密失败 / 读不到消息

多半是微信升级导致密钥变了，重跑 `wechat-cli init --force`。

---

## 六、导出的内容边界

| 消息类型 | 效果 |
|---|---|
| 文字 | ✅ 完整 |
| 图片 | ⚠️ 只有占位 `[图片] (local_id=xxx)`，不导出图片文件 |
| 视频 | ⚠️ 输出原始 XML |
| 链接 / 文件 | ⚠️ 多数显示「当前版本不支持展示该内容」 |
| 语音 | ⚠️ 不支持 |

**适合**：文字内容的归档、整理、总结、日报。
**不适合**：图片和语音的完整备份。

---

## 七、隐私

- 全程本地，无网络上传（已审计：代码中无 http / socket / 上传行为）。
- 但这些文件是**明文**，别外传、别提交 git、别云同步：
  - `~/.wechat-cli/all_keys.json` —— 相当于你聊天库的钥匙
  - `~/.wechat-cli/decrypted/` 和系统临时目录里的解密副本
  - 任何导出的 `.md` / `.txt`
- 用完执行 `wechat-cli clean`。

---

## 八、归属与许可

- 核心代码 `wechat-cli`：上游项目 [freestylefly/wechat-cli](https://github.com/freestylefly/wechat-cli)，**Apache License 2.0**，全文见 `tool/README_CN.md`。
- Windows 4.1+ 密钥扫描算法：借鉴自 [TANGandXUE/wcdb-key-tool](https://github.com/TANGandXUE/wcdb-key-tool)，**MIT License**，署名保留在 `tool/wechat_cli/keys/scanner_windows.py` 文件头。
- 原始 Skill 作者：SkillHub 用户「宜生」。
- 本改进版的修改清单：见 `tool/README_CN.md`「归属与许可声明」章节。

再分发时须保留 README 中的「归属与许可声明」与「许可证」两个章节。
