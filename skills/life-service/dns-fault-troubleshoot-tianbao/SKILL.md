---
name: dns-fault-troubleshoot
slug: dns-fault-troubleshoot-tianbao
displayName: DNS解析故障排查
display_name: "DNS解析故障排查"
display_name_en: "DNS Resolution Fault Troubleshooting"
version: "1.0.0"
summary: 按「本地 hosts 与缓存 → 客户端配置 → 递归解析器 → 权威 DNS → 传输链路」五层给出 dig/nslookup 具体用法与判定表，每层什么现象说明什么，配 TTL 影响分析、运营商 DNS 污染与劫持识别方法、五类常见错误现象对照与排查决策树。
description: 域名解析不了、解析到错误 IP、时好时坏、部分用户能访问部分不能、DNS 响应慢、刚改的解析不生效时使用。当用户说"DNS 解析不了怎么办""dig 怎么用""nslookup 和 dig 有什么区别""域名解析到错误的 IP""改了 DNS 记录不生效""TTL 是干什么的""内网域名解析不到""DNS 污染怎么识别""解析时好时坏"时使用。内置 dig/nslookup 具体命令与输出字段判读、五层定位表、TTL 与缓存影响分析、DNS 污染与劫持的识别特征、hosts 与缓存清理命令、六类常见错误现象对照（本地缓存 / hosts / 配置残留 / TTL 未过期 / 污染 / 上游故障）、排查决策树，配 scripts/dns_diagnose.py 做分层判定与现象归因。适用于系统管理员、运维工程师、开发人员、技术支持。本技能只做定位路径规划与现象判读，不代替现场网络与域名配置变更。
license: Apache-2.0
author: 刘天宝｜墨燊
category: it-ops-security
subCategories:
  - itops-network
icon: icon.svg
tags: [DNS, 域名解析, dig, nslookup, 解析故障, TTL, DNS缓存, hosts, DNS污染, 劫持, 网络故障, 解析不到]
language: zh-CN
visibility: public
---

# DNS解析故障排查（dns-fault-troubleshoot）

DNS 故障最容易走弯路的地方是：**你在自己的机器上能解析，别人不能**——因为你的机器有本地缓存、有 hosts、有内网 DNS。

这个技能做一件事：**按五层顺序定位，每层现象对应明确结论**。

---

## 硬边界（先看这条）

| 能做 | 不能做 |
|---|---|
| 给出五层定位顺序与判定表 | ❌ 代替你修改域名解析记录 |
| 判读 dig/nslookup 输出 | ❌ 代替域名服务商处理权威记录 |
| 识别污染、劫持、缓存问题 | ❌ 承诺「一定能解析成功」 |
| 给出清理缓存与配置核查命令 | ❌ 提供绕过安全与合规管控的做法 |
| 给出排查决策树 | ❌ 代替网络服务商与域名服务商处理故障 |

**出现以下情况，先停下来人工处理：**

- 权威 DNS 返回的记录**本身就是错的**（NS 记录、A 记录指向错误）→ 找域名服务商，不要在本地折腾
- 域名**过期未续费** → 显示 `NXDOMAIN` 且权威侧无记录，属注册问题
- 遇到 **DNS 劫持**：返回的 IP 属于完全无关的组织，且多个域名同时指向它 → 转安全事件处理
- 需要**修改注册商/DNS 服务商的账号** → 需授权，不要自行操作
- 出现在**生产环境的 DNS 变更** → 必须走变更流程并记录 TTL
- 内网域名解析不到 → 优先确认是否需要连 VPN 或内网，**公网 DNS 本来就解析不了内网域名**

---

## 一、什么时候用这个技能

| 用户这样说 | 就用 |
|---|---|
| "DNS 解析不了怎么办" | ✅ |
| "dig 怎么用 / 怎么看 dig 输出" | ✅ |
| "nslookup 和 dig 有什么区别" | ✅ |
| "域名解析到了错误的 IP" | ✅ |
| "改了 DNS 记录不生效" | ✅ |
| "TTL 是干什么的、设多少合适" | ✅ |
| "内网域名解析不到" | ✅ |
| "怎么判断 DNS 被污染了" | ✅ |
| "解析时好时坏" | ✅ |
| "帮我把域名解析改一下" | ❌ 需授权与变更流程 |

---

## 二、五层定位法（核心流程）

```
第 0 层  确认现象：哪台机器、哪个域名、是解析失败还是解析错误、是否时好时坏
第 1 层  本地层：hosts 文件 + 本地缓存 + resolv.conf 配置
第 2 层  客户端层：配置的 DNS 服务器是否可达、是否被改过
第 3 层  递归解析器层：换公共 DNS 试，判断是解析器问题还是上游问题
第 4 层  权威 DNS 层：记录本身是否正确、是否生效
第 5 层  传输层：53 端口 / UDP TCP / 链路是否被阻断或劫持
```

**铁律：每一层都用 `dig` 采集，不要用浏览器测试。** 浏览器有自己的 DNS 缓存（Chrome 有独立缓存进程），浏览器能打开不代表 `curl` 能通，反之亦然。

---

## 三、dig 与 nslookup：到底用哪个

| 维度 | dig | nslookup |
|---|---|---|
| 详细信息 | ✅ 完整（全部记录类型、TTL、权威标志、trace） | ❌ 简略 |
| 指定 DNS 服务器 | ✅ 直接指定 | ⚠️ 需交互设置 |
| 追踪解析过程 | ✅ `+trace` | ❌ |
| 指定记录类型 | ✅ 直接参数 | ⚠️ 需交互 |
| 批量/脚本化 | ✅ 好用 | ⚠� 差 |
| 跨平台 | Linux/macOS 内置，Windows 需装 | Windows 内置 |

**结论：排查一律用 `dig`。** `nslookup` 只在没有 dig 的 Windows 环境临时用。

### 3.1 dig 常用命令

```bash
# 1. 基础查询（走系统配置的 DNS）
dig example.com

# 2. 指定 DNS 服务器查询（排除本地配置影响）
dig @8.8.8.8 example.com
dig @223.5.5.5 example.com
dig @1.1.1.1 example.com

# 3. 指定记录类型
dig example.com A
dig example.com AAAA
dig example.com CNAME
dig example.com MX
dig example.com TXT
dig example.com NS
dig example.com SOA
dig example.com PTR            # 反查（-x 等价）

# 4. 只看答案，简化输出
dig +short example.com A

# 5. 只看关键行（最常用）
dig example.com | grep -E "^;; ->>HEADER|^example.com"

# 6. 追踪完整解析链（从根到权威）
dig +trace example.com

# 7. 反向追踪，确认到某个 IP 的解析来源
dig +trace -x 1.2.3.4

# 8. 显示完整解析过程（每次查询的服务器、耗时、缓存命中）
dig example.com +noall +answer +stats

# 9. 指定 TCP 查询（UDP 被阻断或大响应被截断时）
dig +tcp example.com

# 10. 测试指定端口的 DNS（自建 DNS 在非 53 端口）
dig -p 5353 @dns.example.com example.com

# 11. 控制超时与重试（排查时避免长时间等待）
dig +time=2 +tries=1 example.com

# 12. 查 DNSSEC 是否可用
dig +dnssec example.com
dig example.com DNSKEY
```

### 3.2 dig 输出字段判读

```
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 12345
;; flags: qr rd ra; QUERY: 1, ANSWER: 2, AUTHORITY: 0, ADDITIONAL: 1

;; QUESTION SECTION:
;example.com.            IN  A

;; ANSWER SECTION:
example.com.     600     IN  A     1.2.3.4        ← 关键行

;; Query time: 28 msec
;; SERVER: 192.168.1.1#53(192.168.1.1)     ← 是哪个 DNS 回答的
;; WHEN: Sun Oct 11 10:30:00 CST 2026
;; MSG SIZE  rcvd: 56
```

| 字段 | 含义 | 怎么用 |
|---|---|---|
| `status` | 响应状态 | **第一眼看这个**，见 §4 状态码表 |
| `flags` | `ra` 是否递归可用、`aa` 是否权威回答 | `ra` 缺失说明该服务器不能递归 |
| `ANSWER` | 应答条数 | 0 表示没解析到（配合 status 判断） |
| `600` | TTL（秒） | **排查时最关键的数字**，见 §5 |
| `SERVER` | 回答的 DNS 服务器 | 确认是不是你以为的那个 DNS |
| `Query time` | 响应耗时 | > 200ms 需关注，> 500ms 明显异常 |

---

## 四、status 状态码与现象对照

| status | 含义 | 通常原因 | 下一步 |
|---|---|---|---|
| `NOERROR` | 查询成功 | — | 看 ANSWER 是否有记录 |
| `NXDOMAIN` | 域名不存在 | 记录已删、拼写错、**域名过期未续费** | 查权威记录、查注册状态 |
| `SERVFAIL` | 服务器内部错误 | 权威侧配置错误、DNSSEC 验证失败、权威不可达 | 换 DNS 试、`dig +trace` |
| `REFUSED` | 被拒绝查询 | 服务器不允许该查询（无递归权限或被 ACL 拒绝） | 换 DNS、检查 ACL |
| `NOTIMP` | 不支持该查询 | 服务器不支持该记录类型 | 换 DNS |
| **超时无响应** | 无应答 | 53 端口被阻断、路由不通、服务器宕 | `nc -zv <dns> 53`、换 DNS |

**`NOERROR` 但 `ANSWER: 0` 的含义**：域名存在但没有该类型的记录。例如查 A 记录返回 0 条，可能是只有 AAAA 记录。

---

## 五、TTL 与缓存：最常见的「改了不生效」原因

### 5.1 缓存层次

```
浏览器缓存 → 操作系统缓存 → 递归 DNS 服务器缓存 → 中间链路缓存 → 权威 DNS
```

**任一层的缓存都会让你「改了不生效」。**

### 5.2 常见 TTL 取值

| 场景 | 常见 TTL | 说明 |
|---|---|---|
| 权威默认（未显式设置） | 3600–86400 | 很多域名不设 TTL，落到托管商默认值 |
| 变更前的准备期 | **300**（5 分钟） | **要改记录前先把 TTL 降到 300** |
| 稳定生产记录 | 3600（1 小时） | 平衡解析性能与切换灵活性 |
| 高频变更/灰度 | 60 | 切换快但解析器压力大 |
| CNAME 链 | 通常较短 | 链越长，问题定位越难 |

### 5.3 变更前的正确操作顺序

```
第 1 步  把要改的记录 TTL 降到 300（至少提前 24 小时）
第 2 步  等旧 TTL 过期（> 原来的 TTL 值）
第 3 步  修改记录
第 4 步  验证：dig @多个DNS <域名> 看新记录是否生效
第 5 步  确认稳定后，把 TTL 调回合理值
```

**跳过第 1–2 步直接改，现实中可能要等几小时甚至一天才全网生效。**

### 5.4 清理本地缓存

```bash
# systemd-resolved
resolvectl flush-caches
resolvectl query example.com

# nscd
sudo nscd -i hosts

# dnsmasq
sudo systemctl restart dnsmasq
sudo killall -HUP dnsmasq

# macOS
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder

# Windows
ipconfig /flushdns

# 浏览器（Chrome/Edge）
chrome://net-internals/#dns  -> Clear host cache
或直接改用无痕窗口对比

# Java 程序（JVM 有自己的 DNS 缓存）
-Dnetworkaddress.cache.ttl=0   # 设为 0 便于排查（生产慎用）

# 关键：用 +short 绕过本地缓存验证
dig +short example.com
# 再显式指定 DNS 验证
dig +short @223.5.5.5 example.com
dig +short @8.8.8.8 example.com
```

> **注意**：`ping example.com` 用的是**系统解析器**，也受本地缓存影响。`ping` 通了不代表权威记录已更新。

---

## 六、逐层现象 → 根因对照

### 6.1 第 1 层：本地层

| 现象 | 根因 | 验证 | 处置 |
|---|---|---|---|
| 某些域名解析到固定内网 IP | **hosts 文件里有记录** | `grep -v '^#' /etc/hosts`；`grep example /etc/hosts` | 删掉或注释掉 |
| 换了 DNS 还是同样的错 IP | 本地缓存 | `dig +short @8.8.8.8 <域名>` 与 `dig +short <域名>` 对比 | 清理本地缓存 |
| 只有这台机器解析错 | 本地配置问题 | 换另一台机器同样命令对比 | 查本机 hosts、缓存、resolv.conf |
| `dig` 正常但浏览器打不开 | 浏览器独立 DNS 缓存 | 无痕窗口测试；`chrome://net-internals/#dns` 清缓存 | 清浏览器缓存或换浏览器 |

### 6.2 第 2 层：客户端配置

| 现象 | 根因 | 验证 | 处置 |
|---|---|---|---|
| 所有域名都解析失败 | `/etc/resolv.conf` 指向的 DNS 不可达 | `cat /etc/resolv.conf`；`ping <dns>`；`nc -zv <dns> 53` | 修配置 |
| `status: REFUSED` | DNS 服务器拒绝递归 | `dig @<dns> example.com` | 换 DNS 或检查 ACL |
| `ra` 标志缺失 | 该服务器不做递归（纯权威服务器） | 看 dig 输出 flags | 不能当递归 DNS 用 |
| 只有内网域名失败 | 公网 DNS 解析不了内网域名 | 对比内外网域名 | 连内网/VPN，或用内网 DNS |
| DNS 配置被莫名改过 | 配置文件写入异常或 DHCP 下发 | `ls -l /etc/resolv.conf`；看 DHCP 下发 | 恢复配置并查变更记录 |

**内网 DNS 必须同时配置 search 域与内网 DNS 服务器：**

```
# /etc/resolv.conf  或通过 systemd-resolved
search corp.example.com
nameserver 10.0.0.53
nameserver 10.0.0.54
```

### 6.3 第 3 层：递归解析器

| 现象 | 根因 | 验证 | 处置 |
|---|---|---|---|
| 换公共 DNS 就正常 | 运营商/企业 DNS 故障或限流 | 对比 `dig @223.5.5.5` 与 `dig @<当前DNS>` | 临时换 DNS，报修原 DNS |
| 不同 DNS 返回不同 IP | 某解析器缓存过期或做了特殊解析 | 多个 DNS 交叉查询比对 | 查权威记录，清理该解析器缓存 |
| 间歇性解析失败（时好时坏） | 某解析器不稳定、负载高、或有健康检查摘除 | 连续多次查询统计成功率 | 换 DNS，报修 |
| `Query time` > 500ms | 解析器响应慢或链路差 | 看 Query time | 换就近 DNS |
| 返回内网地址但连不上 | 私有 DNS 泄露（split-horizon 配置错误） | 看返回 IP 是否私有段 | 查 DNS 配置 |

### 6.4 第 4 层：权威 DNS

| 现象 | 根因 | 验证 | 处置 |
|---|---|---|---|
| 所有 DNS 都返回 NXDOMAIN | 记录不存在或已删除 | `dig +trace example.com NS` 看权威是谁 | 查权威记录、查域名续费 |
| 所有 DNS 都返回 SERVFAIL | 权威配置错误（常见：NS 记录缺失、CAA 冲突） | `dig +trace` 看最后一步 | 找域名服务商 |
| 权威返回的 IP 是错的 | 记录配错 | `dig +trace` 看权威应答 | 改权威记录 |
| 记录改了部分 DNS 有部分没有 | 还没到 TTL 过期 | 对比 TTL 与等待时间 | 等 TTL 或降 TTL 后重来 |
| 域名过期 | 注册到期 | 权威无记录 + whois 显示异常 | 续费 |

### 6.5 第 5 层：传输与劫持

| 现象 | 根因 | 验证 | 处置 |
|---|---|---|---|
| 53 端口不通 | 防火墙/ACL 阻断 | `nc -zv <dns> 53`；`nc -uvz <dns> 53` | 通防火墙 |
| 只有 UDP 不通，TCP 通 | UDP 被阻断 | `dig +tcp @<dns> <域名>` | 换用 TCP 或开 UDP |
| 返回的 IP 属于完全无关的组织 | **DNS 污染 / 劫持** | 见 §7 | 转安全事件 |
| 多个不同域名返回同一个 IP | 劫持或泛解析配置 | 批量解析多个域名比对 | 转安全事件 |
| 用 8.8.8.8 被劫持但 223.5.5.5 正常 | 对特定 DNS 的定向劫持 | 换 DNS 对比 | 转安全事件 |

---

## 七、DNS 污染与劫持的识别

### 7.1 污染的典型特征

| 特征 | 说明 |
|---|---|
| **返回 IP 归属完全无关** | 查 IP 归属组织，与域名业务毫无关系 |
| **多个无关域名返回同一 IP** | 批量解析随机域名，看是否都指向同一处 |
| **返回 0.0.0.0 / 127.0.0.1 等** | 明显的 sinkhole 行为 |
| **TLD 缺失也能解析** | `dig example.fakedefinitelynotatld` 能返回结果 |
| **响应来自非配置 DNS** | dig 输出 `SERVER` 不是你配置的地址 |
| **公共 DNS 被劫持而国内 DNS 正常** | 定向劫持的典型表现 |

### 7.2 识别命令

```bash
# 1. 批量解析测试：随机不存在的域名若能返回结果，高度怀疑被劫持
dig +short asdfjkl1234567890.example
dig +short randomtest998877.com

# 2. 看权威应答（+trace 最后一步是权威给出的）
dig +trace example.com

# 3. 对比多个公共 DNS
dig +short @223.5.5.5 example.com
dig +short @8.8.8.8 example.com
dig +short @1.1.1.1 example.com
dig +short @9.9.9.9 example.com

# 4. 确认回答者身份
dig example.com | grep -E "^;; SERVER|^;; ANSWER"

# 5. 验证响应是否来自 UDP 53 的真实 DNS（用 +tcp 对比）
dig +tcp @<dns> example.com
```

### 7.3 处置原则

- **不要试图在客户端「绕过」污染后当作问题解决了**——问题在链路上，换台机器照样中招
- 确认污染后**转网络管理或安全团队**处理（通常需运营商配合）
- 企业内部可自建递归 DNS 并强制指定，但**必须确保内网所有出口都走它**，否则形同虚设

---

## 八、最常见的错误现象对照

| 现象 | 第一直觉 | 真实原因 | 正确做法 |
|---|---|---|---|
| 「域名解析不了」 | 域名有问题 | 可能只是这台机器的缓存或 hosts | 先换一台机器 + 指定公共 DNS 复现 |
| 改了记录不生效 | 记录没保存 | TTL 未过期，或只在一部分解析器生效 | `dig @多DNS` 看差异，查 TTL |
| `dig` 正常浏览器打不开 | DNS 没问题 | 浏览器独立 DNS 缓存 | 无痕窗口或清浏览器缓存 |
| `ping` 通了就以为好了 | 解析已恢复 | ping 也走缓存，且 ping 通不代表服务通 | 用 `curl -v` 验证实际业务 |
| 内网域名解析不到 | DNS 故障 | 公网 DNS 本来就解析不了内网域名 | 连内网/VPN，用内网 DNS |
| 时好时坏 | 随机故障 | 某解析器不稳定、TTL 造成多解析器结果不一致 | 多 DNS 交叉统计成功率 |
| 解析到旧 IP | 缓存 | TTL 未过期 | 降 TTL、等待、用 `dig @指定DNS` 验证 |
| `status: NOERROR` 但没结果 | 解析失败 | 域名存在但没有该类型记录 | 换记录类型查（AAAA/MX/CNAME） |

---

## 九、脚本用法

```bash
python scripts/dns_diagnose.py --file obs.txt --domain example.com
```

| 参数 | 说明 |
|---|---|
| `--file` | 观测结果文件，每行 `检查项\|结果`，见下表 |
| `--domain` | 排查的域名，用于生成命令清单 |
| `--json` / `--out` | JSON 输出 / 写入指定报告文件 |
| `--selftest` | 跑内置自检（≥ 8 条断言） |

**输入文件键名：**

```
local_hosts_hit=0/1        # hosts 是否有记录
local_cache_stale=0/1       # 本地缓存是否过期
resolve_conf_ok=1          # resolv.conf 配置是否正常
dns_reachable=1            # 配置的 DNS 是否可达
current_dns_status=NOERROR # 本地解析 status
current_dns_answer=1.2.3.4 # 本地解析到的 IP
public_dns_answer=1.2.3.4  # 公共 DNS 解析到的 IP
public_dns_status=NOERROR  # 公共 DNS status
auth_status=NOERROR        # 权威 status（+trace 结果）
auth_answer=1.2.3.4        # 权威返回的 IP
ttl=600                    # 记录 TTL（秒）
ip_consistent=1            # 各 DNS 返回 IP 是否一致
port53_ok=1                # 53 端口是否可达
suspect_pollution=0/1      # 是否疑似污染
```

脚本做四件事：① 按五层顺序定位问题落在哪一层；② 识别「本地层」问题（hosts / 缓存 / 配置）；③ 识别「权威层」问题（该找域名服务商）；④ 识别污染特征并输出下一步命令。

> 脚本**不发起任何 DNS 查询**，它只归拢你已采集到的观测结果。它的价值在于防止「跳过本地层直接怀疑域名服务商」。

---

## 十、人工确认清单（这步不能省）

- [ ] 现象是在**哪台机器**上出现的，换机器还能复现吗
- [ ] 是**解析失败**（报错）还是**解析到错误地址**（能通但走错地方）
- [ ] `dig` 的 `SERVER` 字段是不是你以为的那个 DNS
- [ ] `hosts` 文件是否被改过（是不是有人为了临时测试加过记录忘了删）
- [ ] 记录改动时间与 TTL 是否对得上（`记录改动时间 + TTL > 现在` 就是还没生效）
- [ ] 多个公共 DNS 的结果是否一致（不一致说明还没全网生效或存在劫持）
- [ ] 内网域名是否已连内网或 VPN
- [ ] 是否有人近期改过 DNS 配置（变更记录）
- [ ] 是否为域名过期或续费问题（查注册状态）

---

## 十一、最常见的坑

**坑一：只用浏览器测试。**
浏览器有独立的 DNS 缓存（Chrome 尤其），浏览器能打开不代表 `dig` 能通，反之亦然。**排查一律用 `dig`。**

**坑二：在本机测通就下结论。**
你的机器可能有 hosts 记录、有本地缓存、连着内网 VPN。换一台机器、换一个网络环境复现，才能确认是不是全局问题。**「我这儿能打开」是最常见的误判来源。**

**坑三：改了记录就以为立刻生效。**
TTL 未过期时，递归解析器继续返回旧记录。改记录前**先把 TTL 降到 300 并等旧 TTL 过期**，这是唯一可控的做法。

**坑四：把 `NXDOMAIN` 当成「DNS 服务器坏了」。**
`NXDOMAIN` 是明确的「域名不存在」，说明 DNS 工作正常。通常是记录被删、拼写错误，或**域名过期未续费**——后者经常被当成技术问题排查半天。

**坑五：看到 dig 有 ANSWER 就认为解析正常。**
要看 ANSWER 里的 IP 对不对。解析到一个错误的但存在的 IP，比解析失败更难发现。

**坑六：忘了 CNAME 链。**
`a.example.com` 可能 CNAME 到 `b.cdn.com` 再 CNAME 到实际地址。`dig a.example.com` 看到的可能不是最终地址。加 `+trace` 或查完整链。

**坑七：把 DNS 污染当普通解析错误处理。**
污染的特征是「多个无关域名解析到同一处」「随机不存在的域名也能解析」。识别出来后**不能只在客户端绕过**，问题在链路上，换机器照样中招，必须转网络或安全团队。

**坑八：JVM 的 DNS 缓存没清。**
Java 程序有独立的 DNS 缓存（受 `networkaddress.cache.ttl` 影响）。改了 DNS 记录后 Java 应用不生效、`curl` 正常，多半是这个原因。排查时可临时设为 0 验证。

**坑九：用公网 DNS 查内网域名。**
公网 DNS 解析不了内网域名。解析不到不代表故障，先确认是否连了内网。

**坑十：只看一个 DNS 服务器就下结论。**
单点查询无法区分「该解析器缓存过期」「某解析器故障」「被劫持」。**至少对比两个以上公共 DNS + 一个权威查询**。

**坑十一：清理缓存时忘了应用层也有缓存。**
清了系统缓存和浏览器缓存，但 CDN 边缘节点、反向代理、应用的连接池都可能缓存。改完要**从外部完整走一遍访问链路**验证。

**坑十二：把 `dig` 的 `Query time` 忽略掉。**
能解析成功但响应 800ms，在用户侧就是「打开很慢」。解析耗时是真实体验的一部分，必须纳入排查。

---

## 十二、边界与免责

- 本技能给出的是**定位路径与现象判读口径**，不代替现场网络与域名配置变更
- 涉及**修改域名解析记录、NS 记录、注册商信息**的操作**必须经授权并走变更流程**，记录 TTL 与变更时间
- 具体的**TTL 取值、记录配置方式**，以域名服务商的产品说明与**现行规定**为准
- 遇到 **DNS 劫持或疑似污染**，应转网络管理与安全专业人员处理，不在客户端自行绕过
- 涉及**未备案域名、跨境解析、特殊行业域名**的合规要求，**以现行规定和当地主管部门要求为准**
- 脚本**不发起任何网络请求**，也不修改任何配置，只做观测结果的归拢与判读

---

## 十三、许可

本技能由 **刘天宝｜墨燊** 原创，采用 **Apache License 2.0**。

`rules/dns_rules.md` 中的 TTL 取值、状态码判定与污染识别特征为通用工程实践整理，不同域名服务商与网络的实际情况会有差异，落地前请结合现场验证。