---
name: ssl-certificate-expiry
slug: ssl-certificate-expiry-tianbao
displayName: SSL证书到期更换与配置核查
display_name: "SSL证书到期更换与配置核查"
display_name_en: "SSL Certificate Expiry, Renewal and Configuration Check"
version: "1.0.0"
summary: 用 openssl s_client 核查证书剩余天数、证书链完整性、SAN 与域名匹配、签名算法与密钥强度，按剩余天数给出四级到期分级预警，并给出 Nginx/Apache/负载均衡场景的常见错误配置写法与整改命令。
description: 排查网站 HTTPS 报警、证书过期、浏览器提示不安全、API 调用报 SSL 错误时使用。当用户说"证书快到期了怎么换""怎么查证书剩余多少天""证书链不完整怎么解决""SAN 和域名对不上""Nginx 证书配置报错""curl 报 SSL certificate problem""换了证书还是提示不安全""证书续签流程是什么"时使用。内置 openssl s_client/s_x509 具体命令、四级到期分级、证书链三层校验法、SAN 通配符匹配规则、算法与密钥强度禁用清单、Nginx/Apache/ELB 常见错误写法对照、换证后验证清单，配 scripts/cert_expiry_check.py 做证书文本解析与分级预警。适用于系统管理员、运维工程师、DevOps、后端开发。本技能只做证书状态核查与配置指引，不代替现场签发与替换操作。
license: Apache-2.0
author: 刘天宝｜墨燊
category: it-ops-security
subCategories:
  - itops-security
icon: icon.svg
tags: [SSL证书, HTTPS, 证书到期, 证书链, openssl, SAN, Nginx, Apache, TLS, 续签, 换证, 安全配置]
language: zh-CN
visibility: public
---

# SSL证书到期更换与配置核查（ssl-certificate-expiry）

证书问题分两类：**到期类**（过期、即将过期）和**配置类**（链不全、域名不匹配、算法过旧）。两类排查手段完全不同，到期看日期，配置看内容。

这个技能做三件事：**算剩余天数并分级** → **验链与验名** → **对照错误配置写法**。

---

## 硬边界（先看这条）

| 能做 | 不能做 |
|---|---|
| 解析证书文本，给出剩余天数与分级 | ❌ 代替你向 CA 签发或上传 CSR |
| 核查证书链完整性、SAN 匹配、算法强度 | ❌ 自动执行换证与 reload |
| 给出整改命令与验证步骤 | ❌ 承诺「换了就一定不报错」 |
| 识别常见错误配置写法 | ❌ 代替安全团队做渗透或合规判定 |
| 输出换证验证清单 | ❌ 提供绕过证书校验的做法 |

**出现以下情况，先停下来人工处理，不要照着流程改配置：**

- 证书剩余天数 > 0 但客户端仍报 `certificate has expired` —— 这是**时间问题**（本机时钟漂移），不是证书问题
- 证书 CN 是旧域名、SAN 里没有当前域名 —— **不能靠改 `server_name` 解决，必须重新签发**
- 自签名证书要上生产 —— 走内部 CA，不要用自签名
- 私钥权限不是 600、证书文件权限过宽 —— 先修权限再谈其他
- 浏览器/客户端报 `ERR_CERT_COMMON_NAME_INVALID` 但 SAN 看着没问题 —— 检查是不是**只看了 CN 没看 SAN**（现代客户端已完全忽略 CN）
- 换了证书仍不生效 —— 检查是**没 reload、reload 的不是同一份文件、还是 CDN/负载均衡上缓存的旧证书**

---

## 一、什么时候用这个技能

| 用户这样说 | 就用 |
|---|---|
| "证书还有多久到期" | ✅ |
| "怎么查证书剩余天数" | ✅ |
| "证书快到期了怎么换" | ✅ |
| "curl 报 SSL certificate problem" | ✅ |
| "浏览器提示连接不安全" | ✅ |
| "证书链不完整 / unable to get local issuer" | ✅ |
| "SAN 和域名对不上怎么办" | ✅ |
| "换了证书还是不生效" | ✅ |
| "Nginx 证书配置怎么写" | ✅ |
| "帮我直接把证书换上去" | ❌ 需现场权限与审批 |

---

## 二、完整工作流

```
第 1 步  确认是「到期」还是「配置」问题（见 §3 分类表）
第 2 步  取证书：openssl s_client -connect <host>:443 -servername <host> -showcerts
         落盘后：openssl x509 -in cert.pem -noout -text -dates
第 3 步  算剩余天数并定级（规则文件 §1），同时核查算法、密钥长度、SAN
第 4 步  验链（三层校验法，见 §5），验名（SAN 通配符规则，见 §6）
第 5 步  对照 §7 常见错误配置写法逐条排查服务端配置
第 6 步  换证后按 §8 验证清单逐条验证（改完不验证等于没换）
```

**一步取到证书并算出天数：**

```bash
echo | openssl s_client -connect example.com:443 -servername example.com 2>/dev/null \
  | openssl x509 -noout -dates -subject -issuer
```

**拿完整证书文本（含链）落盘：**

```bash
echo | openssl s_client -connect example.com:443 -servername example.com -showcerts 2>/dev/null \
  > chain.pem
# 取第一张（服务端证书）
awk '/BEGIN CERTIFICATE/,/END CERTIFICATE/' chain.pem > cert.pem
# 用脚本解析
python scripts/cert_expiry_check.py --file cert.pem --host example.com
```

---

## 三、问题分类：先分到期还是配置

| 现象 | 大概率类别 | 下一步 |
|---|---|---|
| `certificate has expired` | 到期 | 查 notAfter，看本机时钟 |
| `certificate is not yet valid` | 时间 | 查 notBefore 与本机时钟（**几乎都是客户端时钟错**） |
| `unable to get local issuer certificate` | 链 | 三层校验法 |
| `hostname mismatch` / `ERR_CERT_COMMON_NAME_INVALID` | 名 | 看 SAN，不看 CN |
| `SSL routines: ssl3_read_bytes: tlsv1 alert protocol version` | 协议 | 客户端 TLS 版本与 `ssl_protocols` |
| `no shared cipher` | 加密套件 | `ssl_ciphers` 与客户端交集为空 |
| 监控报「7 天后到期」但站点正常 | 正常 | 到期未到，只是预警 |

---

## 四、证书检查命令速查

```bash
# 1. 在线看证书（最常用）
echo | openssl s_client -connect example.com:443 -servername example.com 2>/dev/null \
  | openssl x509 -noout -dates -subject -issuer -serial

# 2. 看剩余天数（本机 Linux）
END=$(echo | openssl s_client -connect example.com:443 -servername example.com 2>/dev/null \
  | openssl x509 -noout -enddate | cut -d= -f2)
echo $(( ( $(date -d "$END" +%s) - $(date +%s) ) / 86400 ))

# 3. 看完整内容（算法、密钥长度、SAN、指纹）
openssl x509 -in cert.pem -noout -text

# 4. 只看 SAN（关键！现代客户端忽略 CN）
openssl x509 -in cert.pem -noout -ext subjectAltName

# 5. 验证证书链（用系统 CA 库验证）
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt cert.pem
openssl verify -untrusted intermediate.pem cert.pem   # 自带中间证书时

# 6. 看服务器实际发了哪几张证书
echo | openssl s_client -connect example.com:443 -servername example.com -showcerts 2>/dev/null \
  | grep -E "^( [0-9]+ s:|Certificate chain| [0-9]+ s:)"
# 期望：Certificate chain 后应是 0 s:（叶子） → 1 s:（中间） → 2 s:（根，通常不发）

# 7. 看协商结果（协议、套件、是否支持 TLS1.2/1.3）
echo | openssl s_client -connect example.com:443 -servername example.com -servername example.com 2>/dev/null \
  | grep -E "Protocol|Cipher|Verification|Verify return code"

# 8. 测指定 TLS 1.2 是否可用
openssl s_client -connect example.com:443 -servername example.com -tls1_2 </dev/null 2>&1 | grep -E "Protocol|Cipher"

# 9. 强制只测 TLS1.0（应失败）
openssl s_client -connect example.com:443 -servername example.com -tls1 </dev/null 2>&1 | grep -E "alert|Protocol"

# 10. 看实际生效的服务端配置（Nginx）
nginx -T 2>/dev/null | grep -nA3 "ssl_certificate"

# 11. 多域名/多 IP 场景要带 -servername，否则拿到的是默认站点证书
#     （不带 -servername 是最常见的「明明配了却说不匹配」原因）
```

---

## 五、证书链三层校验法

```
第 1 层  叶子证书      服务端直接发的那张（openssl s_client 输出第一张）
第 2 层  中间证书      CA 签发给叶子用的，必须由服务端下发
第 3 层  根证书        客户端本地信任库里有，通常不需要服务端下发
```

**判定口径：**

| 现象 | 说明 | 处置 |
|---|---|---|
| 服务器只发了 1 张 | 只有叶子 | 客户端若没缓存中间证书就报 `unable to get local issuer` |
| 服务器发了叶子+中间 | 正常 | 用 `-untrusted` 复验 |
| 服务器把**根**也发了 | 浪费带宽，且部分客户端反而不认 | 去掉根证书 |
| 顺序颠倒（中间在前） | 部分客户端（尤其旧 Java）会失败 | 调整 `ssl_certificate` 为 `leaf + intermediate` |
| 客户端报 `unable to get local issuer` 但链看着完整 | 中间证书对应的根不在客户端信任库 | 换用公共 CA 签发的证书 |

**验证命令：**

```bash
# 完整链验证（把服务器下发的所有证书合并后验）
cat leaf.pem intermediate.pem > fullchain.pem
openssl verify -untrusted fullchain.pem leaf.pem
# 输出 OK 才算链正确；输出 19/20 表示缺某个中间证书
```

---

## 六、SAN 与域名匹配规则

**现代客户端（Chrome/Firefox/Edge/Safari/Android/iOS 14+）已完全忽略 CN 字段，只看 SAN。** 只看 CN 判断匹配是过时做法。

| SAN 内容 | `example.com` | `www.example.com` | `a.example.com` |
|---|---|---|---|
| `example.com` | ✅ | ❌ | ❌ |
| `*.example.com` | ❌ | ✅ | ✅ |
| `*.example.com` + `example.com` | ✅ | ✅ | ✅ |
| `*.com` | ❌ | ❌ | ❌ |
| `*.sub.example.com` | ❌ | ❌ | ✅ |
| IP 地址需单列在 SAN 的 iPAddress 项 | ❌ | ❌ | ❌ |

**硬规则：**

- **通配符只能匹配一级子域**，不跨点。`*.example.com` 不匹配 `a.b.example.com`
- **通配符不能匹配裸域**。`*.example.com` 不匹配 `example.com`，必须把裸域单列
- **一个 `*` 不能出现在多个标签位**。`www*.example.com` 是无效 SAN
- **IP 访问必须把 IP 写进 SAN 的 iPAddress 项**，写成 DNS 名无效
- SAN 条目数量上限：主流 CA 一般限制在 **100 条以内**，超了签发失败或极慢

---

## 七、Nginx / Apache 常见错误配置写法

### Nginx

| # | 错误写法 | 后果 | 正确写法 |
|---|---|---|---|
| 1 | `ssl_certificate server.crt;`（只配一张） | 客户端报 `unable to get local issuer` | `ssl_certificate fullchain.pem;`（含叶子+中间） |
| 2 | `ssl_certificate` 指向的目录 root 用户不可读 | reload 失败，报 `cannot load certificate` | 路径权限 755，文件 644，私钥 600，属主与 nginx worker 一致 |
| 3 | `ssl_protocols TLSv1 TLSv1.1 TLSv1.2;` | 老旧协议被扫描器判不合规 | `ssl_protocols TLSv1.2 TLSv1.3;` |
| 4 | `ssl_prefer_server_ciphers on;` 且 ciphers 不含 ECDHE | 协商结果差 | 用 `ssl_ciphers` 指定强套件（含 ECDHE），或交给 TLS1.3 默认 |
| 5 | 缺 `ssl_session_timeout` / `ssl_session_cache` | 每次握手全量运算，高并发下 CPU 高 | `ssl_session_timeout 1d; ssl_session_cache shared:SSL:10m;` |
| 6 | 缺 `ssl_stapling` / `ssl_stapling_verify` | OCSP 响应走 CA，客户端握手慢 | 配 `ssl_stapling on; ssl_stapling_verify on;` |
| 7 | `server_name` 与 SAN 不一致且无 default_server 兜底 | 访问非预期域名拿到默认站点证书 | 每个域名单独 server 块，证书用 SAN 全覆盖 |
| 8 | **只 reload 不重载证书内容** | 换证后仍报旧证书 | 确认改的是同一份文件，再 `nginx -s reload` |
| 9 | 多台机器证书不同步 | 负载均衡逐台换，有的换有的没换 | 先全部换完再切流量，或用双证书灰度 |
| 10 | `proxy_ssl_server_name off;` 反向代理到后端 HTTPS | 后端收到 SNI=空，返回默认证书 | `proxy_ssl_server_name on; proxy_ssl_name <后端域名>;` |

**Nginx 正确的最小配置片段：**

```nginx
server {
    listen 443 ssl;
    server_name example.com www.example.com;

    ssl_certificate     /etc/nginx/ssl/fullchain.pem;   # 叶子 + 中间
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;      # 私钥，权限 600
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_stapling        on;
    ssl_stapling_verify on;

    location / { proxy_pass http://127.0.0.1:8080; }
}
```

### Apache

| # | 错误写法 | 后果 | 正确写法 |
|---|---|---|---|
| 1 | `SSLCertificateFile` 指向 fullchain，`SSLCertificateKeyFile` 指向错私钥 | 启动失败 `does not match` | 两行必须来自同一次签发 |
| 2 | `SSLEngine off` 放在非 443 的 vhost 里 | 该 vhost 不加密 | 443 vhost 内 `SSLEngine on` |
| 3 | `SSLProtocol all -SSLv3` | 仍启用 TLS1.0/1.1 | `SSLProtocol -all +TLSv1.2 +TLSv1.3` |
| 4 | `SSLCACertificateFile` 指向根而非中间 | 链不全 | 中间证书放 `SSLCACertificateFile` 或追加进 fullchain |
| 5 | 改完没 `apachectl configtest` | reload 直接挂，服务中断 | 改完必须 `apachectl configtest` 再 reload |

---

## 八、换证后验证清单（这步不能省）

- [ ] `openssl s_client` 拿到的是**新证书**的序列号，不是旧的
- [ ] `-showcerts` 输出的证书链里，叶子在最前，中间在根之后（根通常不发）
- [ ] `openssl verify -untrusted fullchain.pem leaf.pem` 输出 `OK`
- [ ] 从**外部客户端**（不是服务器本机）访问一次，排除本机缓存与 hosts 影响
- [ ] 换 SAN 里的每个域名各访问一次，不要只测主域名
- [ ] 走 CDN/WAF 时，确认**源站与边缘节点的证书都已换**，不要只在源站换
- [ ] 确认私钥与证书是**同一次签发**（对比 modulus / 公钥是否一致）
- [ ] 确认 reload 的进程用的是**同一份文件路径**（`nginx -T | grep ssl_certificate`）
- [ ] 私钥权限 600、证书 644、目录 755
- [ ] 日志里不再出现 TLS 握手失败告警

**检查证书与私钥是否配对：**

```bash
openssl x509 -noout -modulus -in cert.pem | openssl md5
openssl rsa  -noout -modulus -in privkey.pem | openssl md5
# 两行输出必须一致
```

---

## 九、脚本用法

```bash
python scripts/cert_expiry_check.py --file cert.pem --host example.com
```

| 参数 | 说明 |
|---|---|
| `--file` | 证书文件（`openssl x509` 输出，或 `s_client` 导出的第一张 PEM） |
| `--host` | 要匹配的域名，用于核 SAN 是否覆盖；不填则跳过域名匹配 |
| `--as-of` | 基准日 `YYYY-MM-DD`，默认今天，用于算剩余天数 |
| `--chain` | 链文件（含中间证书），做三层校验；不填则跳过链校验 |
| `--json` / `--out` | JSON 输出 / 写入指定报告文件 |
| `--selftest` | 跑内置自检（≥ 8 条断言） |

脚本做五件事：① 解析 subject / issuer / 序列号 / 生效与到期时间；② 算剩余天数并给**四级分级**（正常 / 关注 / 告警 / 已过期）；③ 核算法与密钥长度是否过旧；④ 核 SAN 是否覆盖指定域名（含通配符匹配）；⑤ 输出换证验证清单。

> 脚本读的是**证书文本**，不是线上端口。它能告诉你这张证书还剩多少天、SAN 里有没有你的域名，但**不能**告诉你服务器现在发的是不是这张证书、reload 有没有生效——那两件事必须用 §4 的在线命令验证。

---

## 十、最常见的坑

**坑一：只看 CN，不看 SAN。**
现代客户端完全忽略 CN 字段。一张 CN 写对但 SAN 里没有对应域名的证书，浏览器照样报 `ERR_CERT_COMMON_NAME_INVALID`。用 `openssl x509 -ext subjectAltName` 核。

**坑二：`openssl s_client` 不带 `-servername`。**
不带就是不带 SNI，服务器会返回**默认站点**的证书。在多域名服务器上，这会让你看到一张「根本不认识的证书」，从而误判「配置错了」。**任何在线检查都要带 `-servername <域名>`。**

**坑三：只配了叶子证书，没下发中间证书。**
`ssl_certificate` 指向叶子而不是 fullchain。浏览器因为缓存过中间证书可能还正常，换一台新机器、换一个客户端（尤其移动端 App）立刻报 `unable to get local issuer`。这类问题「本机测是好的」极具迷惑性。

**坑四：把根证书也一起下发。**
不影响功能，但白占带宽，而且部分严格实现会因此报错。服务端应只发叶子 + 中间。

**坑五：换了证书但没 reload，或者 reload 的不是这份文件。**
文件改了、进程还在用内存里的旧证书；或者改了 A 路径、配置里引用的是 B 路径。用 `nginx -T | grep ssl_certificate` 确认实际路径。

**坑六：把 `certificate has expired` 当成证书问题，先去续签。**
客户端时钟漂移也会报这个。先在客户端核对时间——差几小时到几天时，续签也解决不了。

**坑七：通配符证书当万能的用。**
`*.example.com` 不匹配 `example.com`，也不匹配 `a.b.example.com`，也不匹配 IP。签之前先把要用到的所有域名列出来，包括裸域、二级子域、内网访问用的 IP。

**坑八：证书文件权限过宽。**
私钥 644 等于同机任何用户都能读到密钥。这不只是「不规范」，在审计里通常直接判不合规。改完权限一定要 `nginx -t` 确认能读。

**坑九：换了证书没从外部验证。**
在本机用 `curl https://127.0.0.1 -H "Host: ..."` 测通了就认为完成，绕过了 CDN、DNS 解析、旧缓存、负载均衡逐台不一致这四类问题。**必须从外部访问。**

**坑十：监控只看 notAfter，不看 notBefore。**
还没生效的证书（notBefore 在未来）同样不可用，而且 `notAfter` 看起来还很长，监控不会报警。签发后先确认 notBefore 已过。

---

## 十一、边界与免责

- 本技能给的是**证书状态核查口径与配置指引**，不代替现场签发、替换与 reload 操作
- 证书有效期长度、算法要求、是否需要公共 CA 签发，**以现行规定、浏览器与操作系统厂商的根证书要求、以及你所在行业的合规要求为准**，各 CA 与客户端的策略会变动
- 本技能不涉及任何绕过证书校验的手段，也不建议关闭校验（`-k` / `verify=False`）来「解决」问题——那只是把问题藏起来
- 涉及国密算法（SM2/SM3/SM4）、金融行业专用证书等场景，**以对应主管部门与行业规范的具体要求为准**
- 私钥一旦疑似泄露，应立即吊销证书并重新签发，而不是只换证书文件

---

## 十二、许可

本技能由 **刘天宝｜墨燊** 原创，采用 **Apache License 2.0**。

`rules/cert_rules.md` 中的算法禁用清单与分级天数为通用工程实践整理，浏览器与 CA 的策略会持续变化，落地前请以当前实际客户端与 CA 的要求为准。