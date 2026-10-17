# SSL 证书规则表：分级、算法、链、SAN 匹配

本文件是 `ssl-certificate-expiry` 的核心资产。**给证书定级、判算法是否过旧、核域名是否匹配之前，先读本文件，不要凭印象。**

---

## 一、到期分级阈值表

基准日 = 校验当天（不是今天，也不是证书签发日）。

| 剩余天数 | 分级 | 动作 | 责任层级 |
|---|---|---|---|
| > 45 天 | 正常 | 无需动作 | — |
| 16–45 天 | 关注 | 确认续签渠道是否打通，记录证书序列号与到期日 | 运维 |
| 8–15 天 | 告警 | 立即发起续签，提交签发申请 | 运维 + 审批 |
| 1–7 天 | 紧急 | 升级处理，走加急签发或临时续期 | 主管 + 运维 |
| ≤ 0 | 已过期 | 立即处置：先评估能否临时回退到可用证书，再走加急 | 主管 + 运维 + 业务方 |
| notBefore 在未来 | 未生效 | 核对本机时钟与 CA 时区，确认不是时钟漂移 | 运维 |

**分级判定口径：**

1. **先确认基准日可信。** `date -u` 与标准时对比，偏移超过 2 分钟时剩余天数结论不可靠
2. **剩余天数按日历天算，不按秒。** `⌈(notAfter − now) / 86400⌉`
3. **多次续签要按域名清单整体看**，不能只看主域名。同一张证书覆盖的任一域名过期，整张都不可用
4. **监控阈值必须比人工阈值早**：建议在 45 / 30 / 14 / 7 / 1 天各配一级，避免与人工分级口径不一致

---

## 二、到期检查：三种环境的具体命令

### 2.1 Linux 一行算天数

```bash
END=$(echo | openssl s_client -connect example.com:443 -servername example.com 2>/dev/null \
  | openssl x509 -noout -enddate | cut -d= -f2)
DAYS=$(( ( $(date -d "$END" +%s) - $(date +%s) ) / 86400 ))
echo "剩余 ${DAYS} 天"
```

### 2.2 在线取证书并落盘

```bash
echo | openssl s_client -connect example.com:443 -servername example.com -showcerts 2>/dev/null > chain.pem
awk '/BEGIN CERTIFICATE/,/END CERTIFICATE/' chain.pem > cert.pem   # 第一张 = 叶子
```

> **必须带 `-servername`。** 不带就是不带 SNI，返回的是默认站点证书。

### 2.3 Python（跨平台，推荐用于批量巡检）

```python
import ssl, socket
from datetime import datetime, timezone
ctx = ssl.create_default_context()
with socket.create_connection(("example.com", 443), timeout=5) as s:
    with ctx.wrap_socket(s, server_hostname="example.com") as ss:
        cert = ss.getpeercert()
print(cert["notAfter"])   # 形如 'Oct  8 12:00:00 2026 GMT'
```

批量巡检时用这个写法，避免依赖 `date -d`（BSD/macOS 上是 `date -j -f`）。

---

## 三、算法与密钥强度禁用清单

### 3.1 签名算法

| 算法 | 判定 | 说明 |
|---|---|---|
| `sha256WithRSAEncryption` | 允许 | 通用主流 |
| `sha384WithRSAEncryption` | 允许 | 更强 |
| `sha512WithRSAEncryption` | 允许 | 更强 |
| `sha256WithRSAEncryption`（ECDSA 公钥） | 允许 | |
| `ecdsa-with-SHA256` / `ecdsa-with-SHA384` | 允许 | |
| `sha1WithRSAEncryption` | **禁用** | 已被主流浏览器与 CA 全面拒绝 |
| `md5WithRSAEncryption` | **禁用** | 已碰撞可构造 |

### 3.2 密钥算法与长度

| 项目 | 最低要求 | 建议 |
|---|---|---|
| RSA 密钥长度 | ≥ 2048 位 | 3072 位及以上 |
| EC 曲线 | ≥ P-256 | P-384 |
| 对称加密套件 | ≥ AES-128-GCM | AES-256-GCM |
| 摘要 | SHA-256 | SHA-384 |

> RSA 1024 位已被主流浏览器拒绝；更老的密钥长度同样不可用。签发时选错算法只能重签，没有配置层面的补救办法。

### 3.3 协议版本

| 协议 | 状态 |
|---|---|
| SSLv2 / SSLv3 | 禁用（POODLE / DROWN 等） |
| TLS 1.0 / 1.1 | 禁用 |
| TLS 1.2 | 允许（需配强套件） |
| TLS 1.3 | 建议开启 |

---

## 四、证书链三层校验

### 4.1 三层结构

```
叶子证书     包含公钥与 SAN，服务端直接下发
中间证书     由 CA 签发给 CA，把叶子与根连起来，必须由服务端下发
根证书       客户端本地信任库自带，通常不需要服务端下发
```

### 4.2 判定表

| 服务器下发张数 | 结构 | 结论 |
|---|---|---|
| 1 | 只有叶子 | ❌ 中间缺失，新客户端会报 `unable to get local issuer` |
| 2 | 叶子 + 中间 | ✅ 正确 |
| 3 | 叶子 + 中间 + 根 | ⚠️ 多余，白占带宽，部分严格实现报错 |
| 2 但顺序为「中间 + 叶子」 | 顺序错 | ❌ 部分旧客户端（尤其旧 Java）会失败 |

### 4.3 验证命令

```bash
# 合并后验证
cat leaf.pem intermediate.pem > fullchain.pem
openssl verify -untrusted fullchain.pem leaf.pem

# 典型输出与含义
# leaf.pem: OK                      -> 链正确
# error 19/20 ... unable to get local issuer certificate -> 缺中间证书
# error 2/2 ... unable to get issuer certificate -> 上游签发者不在信任库
```

### 4.4 中间证书从哪来

- CA 官网下载（权威来源）
- **绝不能**用搜索引擎随便下的 `.crt` 文件
- 下载后先核指纹（CA 官网上会公布 SHA-256 指纹）
- 中间证书会更新，**要定期复核**，CA 换链会导致老中间失效

---

## 五、SAN 与域名匹配规则

### 5.1 匹配表

| SAN 内容 | example.com | www.example.com | a.example.com | a.b.example.com | 1.2.3.4 |
|---|---|---|---|---|---|
| `example.com` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `www.example.com` | ❌ | ✅ | ❌ | ❌ | ❌ |
| `*.example.com` | ❌ | ✅ | ✅ | ❌ | ❌ |
| `*.example.com` + `example.com` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `*.a.example.com` | ❌ | ❌ | ❌ | ✅ | ❌ |
| `*.com` | ❌ | ❌ | ❌ | ❌ | ❌ |
| iPAddress:1.2.3.4 | ❌ | ❌ | ❌ | ❌ | ✅ |
| `www*.example.com` | ❌ | 非法 | 非法 | 非法 | 非法 |

### 5.2 硬规则

1. **通配符只匹配一级**，不跨点：`*.example.com` 不匹配 `a.b.example.com`
2. **通配符不匹配裸域**：`*.example.com` 不匹配 `example.com`，裸域必须单列
3. **一个 `*` 只能出现在最左标签位**：`www*.example.com` 是无效 SAN
4. **IP 必须写在 iPAddress 项**，写进 DNS 名无效
5. **SAN 条目数量上限一般 100 条**，超出会签发失败或极慢
6. **现代客户端完全忽略 CN**，`CN=example.com` 但 SAN 为空必然不匹配
7. **国际域名要写 punycode**：`*.中文域名.com` 应写成 `*.xn--...` 形式，签发前先转码核对

### 5.3 签发前的域名清单自查

```
[ ] 主域裸域（不带 www）        [ ] www
[ ] 所有二级子域                [ ] 泛域名（确认要几级）
[ ] 内网访问域名                [ ] 内网 IP（iPAddress）
[ ] 移动端 App 调用的 API 域名  [ ] 老系统不能改的旧域名
[ ] 国际域名已转 punycode       [ ] 条目数未超上限
```

---

## 六、换证流程与验证清单

### 6.1 流程

```
第 1 步  按 §5.3 汇总全部域名清单
第 2 步  生成私钥与 CSR（私钥算法按 §3.2）
         openssl req -new -newkey rsa:3072 -nodes -keyout privkey.pem -out csr.csr -subj "/CN=主域名"
第 3 步  提交 CSR 签发，拿到 leaf + intermediate
第 4 步  合并为 fullchain.pem（叶子在前，中间在后，不含根）
         cat leaf.pem intermediate.pem > fullchain.pem
第 5 步  部署：fullchain 644、privkey 600、目录 755
第 6 步  配置检查（Nginx: nginx -t；Apache: apachectl configtest）
第 7 步  reload
第 8 步  执行 §6.2 验证清单
第 9 步  记录新证书序列号与到期日，删除旧证书文件
```

### 6.2 验证清单（一条都不能少）

- [ ] `openssl s_client` 拿到的序列号是**新证书**的
- [ ] `-showcerts` 的链：叶子在最前，中间次之，根未下发
- [ ] `openssl verify -untrusted fullchain.pem leaf.pem` 输出 `OK`
- [ ] 证书与私钥配对：两个 `md5` 一致
- [ ] notBefore 已生效（不是未来时间）
- [ ] **从外部客户端**访问一次（不是服务器本机，不是 curl 到 127.0.0.1）
- [ ] SAN 里**每一个**域名都访问一次，不能只测主域名
- [ ] 走 CDN/WAF 时确认边缘节点与源站证书都已换
- [ ] 负载均衡集群**逐台**都已换，不是只换了一台
- [ ] `nginx -T | grep ssl_certificate` 确认实际生效路径
- [ ] 私钥 600、证书 644、目录 755
- [ ] 新证书到期日已录入监控，序列号已登记
- [ ] 旧证书文件已从服务器删除（私钥尤其）
- [ ] 日志中不再出现 TLS 握手失败

---

## 七、错误信息对照表

| 报错 / 现象 | 根因 | 处置 |
|---|---|---|
| `certificate has expired` | 证书到期 **或客户端时钟漂移** | 先对时，再核 notAfter |
| `certificate is not yet valid` | notBefore 在未来，**几乎都是客户端时钟错** | 对时 |
| `unable to get local issuer certificate` | 缺中间证书，或根不在客户端信任库 | 补中间证书 / 换公共 CA |
| `self signed certificate` | 自签名证书 | 生产走商业或内部 CA |
| `hostname mismatch` | SAN 不含该域名 | 重签，不是改配置 |
| `ERR_CERT_COMMON_NAME_INVALID` | 只看 CN 导致误判，实际是 SAN 不匹配 | `openssl x509 -ext subjectAltName` |
| `tlsv1 alert protocol version` | 客户端 TLS 版本与服务端 `ssl_protocols` 无交集 | 开启 TLS1.2 或更新 |
| `no shared cipher` | 套件交集为空 | 检查 `ssl_ciphers` 与客户端支持 |
| Nginx `cannot load certificate` | 路径不存在或权限不足（key 需 600） | 修权限与属主 |
| Nginx `does not match` | 证书与私钥不是同一次签发 | 重新签发配对 |
| Nginx `SSL_do_handshake() failed` | 上游 HTTPS 代理未开 SNI | `proxy_ssl_server_name on` |
| Apache `does not match ... certificate` | 证书与私钥不配对 | 重新配对 |
| 换证后仍报旧序列号 | 未 reload / 路径不同 / CDN 缓存 | 见 §8 坑五 |

---

## 八、常见坑速查

| # | 坑 | 错误做法 | 正确做法 |
|---|---|---|---|
| 1 | 只看 CN 不看 SAN | `openssl x509 -subject` 看到 CN 对了就认为 OK | `openssl x509 -ext subjectAltName` 逐条核 |
| 2 | 在线检查不带 SNI | `openssl s_client -connect host:443` | 必须加 `-servername host` |
| 3 | 只配叶子证书 | `ssl_certificate server.crt` | `ssl_certificate fullchain.pem` |
| 4 | 把根证书也下发 | fullchain 里含根 | 只含叶子 + 中间 |
| 5 | 换了不 reload 或路径不对 | 改完就以为生效 | `nginx -T \| grep ssl_certificate` 确认路径后 reload |
| 6 | 把过期报错当证书问题 | 直接去续签 | 先核客户端时钟 |
| 7 | 通配符当万能 | 只签 `*.example.com` | 裸域必须单列；跨级不通配 |
| 8 | 私钥 644 | 图省事不改权限 | 私钥必须 600 |
| 9 | 只在本机验证 | `curl https://127.0.0.1 -H "Host: ..."` 通了就算完成 | 必须从外部访问，绕过缓存与 CDN |
| 10 | 监控只看 notAfter | 证书没生效也不报警 | 同时看 notBefore 与 notAfter |
| 11 | 中间证书来源不明 | 搜索引擎随便下 .crt | 只从 CA 官网下载并核指纹 |
| 12 | 集群只换一台 | 逐台替换，流量随机命中 | 全部换完再切流量，或双证书灰度 |

---

## 九、批量巡检的合规红线

自动化脚本必须遵守：

- 在线检查**一律带 `-servername`**，否则结果不可信
- **不要把 `-k` / `verify=False` / `check_hostname=False` 当解决方案**——它只隐藏问题
- 私钥**不落日志、不进版本库、不进告警内容**
- 证书文本可以入库（含公钥信息），但要评估序列号与域名是否属于敏感资产清单
- 巡检输出**不要包含** `Authorization` 头或 Cookie

具体留存期限与审计要求，**以现行规定和本单位审计要求为准**。