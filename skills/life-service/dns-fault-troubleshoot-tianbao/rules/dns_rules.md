# DNS 排查规则表：状态码、分层、TTL、污染识别

本文件是 `dns-fault-troubleshoot` 的核心资产。**判定问题落在哪一层、如何读 dig 输出之前，先读本文件。**

---

## 一、五层定位执行表

| 层 | 范围 | 采集命令 | 通过标准 |
|---|---|---|---|
| L1 本地 | hosts + 本地缓存 + resolv.conf | `grep -v '^#' /etc/hosts`、`dig +short <域名>` | hosts 无记录、两处结果一致 |
| L2 客户端 | 配置的 DNS 是否可达 | `cat /etc/resolv.conf`、`nc -zv <dns> 53` | 可达且返回 ra 标志 |
| L3 递归解析器 | 换公共 DNS 对比 | `dig +short @223.5.5.5 <域名>` | 与本地结果一致 |
| L4 权威 DNS | 记录本身 | `dig +trace <域名>` | 权威返回正确记录 |
| L5 传输 | 53 端口 / 劫持 | `nc -zv <dns> 53`、`dig +tcp` | 端口可达、无劫持特征 |

**铁律：**

1. **L1 不通过不进 L2。** hosts 记录与本地缓存是最常见也最容易被跳过的原因。
2. **每层至少两个数据点**（本地 + 公共 DNS），单点无法区分缓存问题与全局问题。
3. **全程用 dig，不用浏览器。**

---

## 二、dig status 状态码对照

| status | 含义 | 通常原因 | 下一步 |
|---|---|---|---|
| `NOERROR` | 查询成功 | — | 看 ANSWER 是否有记录 |
| `NXDOMAIN` | 域名不存在 | 记录已删 / 拼写错 / **域名过期未续费** | 查权威记录、查注册状态 |
| `SERVFAIL` | 服务器内部错误 | 权威配置错、DNSSEC 失败、权威不可达 | 换 DNS、`dig +trace` |
| `REFUSED` | 拒绝查询 | 无递归权限或被 ACL 拒绝 | 换 DNS、检查 ACL |
| `NOTIMP` | 不支持该查询 | 不支持该记录类型 | 换 DNS |
| 超时无响应 | 无应答 | 53 端口阻断、路由不通、宕机 | `nc -zv <dns> 53`、换 DNS |

**关键理解：`NXDOMAIN` 说明 DNS 工作正常**——它是一个明确答复。把域名过期当 DNS 故障排查是常见弯路。

**`NOERROR` 但 `ANSWER: 0`**：域名存在但没有该类型记录。例如只有 AAAA 没有 A。

---

## 三、dig 输出字段判读

| 字段 | 含义 | 排查用途 |
|---|---|---|
| `status` | 响应状态 | **第一眼看** |
| `qr` | 响应标志 | 确认收到应答 |
| `rd` | 请求递归 | 查询是否请求递归 |
| `ra` | 递归可用 | **缺失 = 该服务器不做递归，不能当 DNS 用** |
| `aa` | 权威回答 | 是否来自权威服务器 |
| `ANSWER` | 应答条数 | 0 = 没解析到 |
| TTL 数字 | 缓存时间（秒） | **判断「改了不生效」的关键** |
| `SERVER` | 回答的服务器 | **确认是不是你以为的 DNS** |
| `Query time` | 响应耗时 | > 200ms 关注，> 500ms 异常 |

---

## 四、TTL 与缓存层次

### 4.1 缓存层次

```
浏览器缓存 → 操作系统缓存 → 递归 DNS 缓存 → 中间链路缓存 → 权威 DNS
```

任一层缓存都会导致「改了不生效」。

### 4.2 TTL 常见取值

| 场景 | 常见 TTL | 说明 |
|---|---|---|
| 托管商默认（未设置） | 3600–86400 | 很多域名不设 TTL |
| 变更前准备期 | **300** | **改记录前必须先降到 300** |
| 稳定生产记录 | 3600 | 平衡性能与灵活性 |
| 高频变更/灰度 | 60 | 切换快但解析器压力大 |

### 4.3 变更操作顺序（不可跳过）

```
1. TTL 降到 300（提前至少 24 小时）
2. 等旧 TTL 过期（> 原 TTL 值）
3. 修改记录
4. dig @多个DNS 验证
5. 稳定后调回合理 TTL
```

### 4.4 清理本地缓存

```bash
resolvectl flush-caches            # systemd-resolved
sudo nscd -i hosts                 # nscd
sudo systemctl restart dnsmasq     # dnsmasq
sudo dscacheutil -flushcache       # macOS
sudo killall -HUP mDNSResponder    # macOS
ipconfig /flushdns                # Windows
chrome://net-internals/#dns        # Chrome/Edge
-Dnetworkaddress.cache.ttl=0       # JVM（生产慎用）
```

---

## 五、逐层现象根因对照

### L1 本地层

| 现象 | 根因 | 验证 | 处置 |
|---|---|---|---|
| 某些域名解析到固定内网 IP | hosts 有记录 | `grep -v '^#' /etc/hosts` | 删/注释 |
| 换 DNS 仍返回同一错 IP | 本地缓存 | `dig +short <域名>` 与 `dig +short @8.8.8.8 <域名>` 对比 | 清缓存 |
| 只有这台机器解析错 | 本地配置 | 换机器同命令对比 | 查 hosts/缓存/resolv.conf |
| dig 正常浏览器打不开 | 浏览器独立缓存 | 无痕窗口；清 Chrome DNS 缓存 | 清浏览器缓存 |

### L2 客户端层

| 现象 | 根因 | 验证 | 处置 |
|---|---|---|---|
| 所有域名解析失败 | resolv.conf 指向不可达 | `cat /etc/resolv.conf`、`nc -zv <dns> 53` | 修配置 |
| `REFUSED` | 无递归权限/ACL | `dig @<dns> <域名>` | 换 DNS 或查 ACL |
| `ra` 缺失 | 纯权威服务器被当递归用 | 看 flags | 换服务器 |
| 只有内网域名失败 | 公网 DNS 解析不了内网域名 | 对比内外网域名 | 连内网/VPN 或用内网 DNS |
| 配置被改过 | DHCP 下发或人为改动 | `ls -l /etc/resolv.conf`、查变更记录 | 恢复配置 |

**内网 DNS 正确配置：**

```
search corp.example.com
nameserver 10.0.0.53
nameserver 10.0.0.54
```

### L3 递归解析器层

| 现象 | 根因 | 验证 | 处置 |
|---|---|---|---|
| 换公共 DNS 就正常 | 原 DNS 故障或限流 | 对比本地与公共 DNS | 临时换、报修 |
| 不同 DNS 返回不同 IP | 缓存过期或特殊解析 | 多 DNS 交叉比对 | 查权威、清该解析器缓存 |
| 间歇解析失败 | 解析器不稳定或负载高 | 连续查询统计成功率 | 换 DNS、报修 |
| `Query time` > 500ms | 解析器慢或链路差 | 看 Query time | 换就近 DNS |
| 返回私有地址 | split-horizon 配置错误 | 看 IP 是否私有段 | 查 DNS 配置 |

### L4 权威层

| 现象 | 根因 | 验证 | 处置 |
|---|---|---|---|
| 全部 NXDOMAIN | 记录不存在/已删/域名过期 | `dig +trace <域名> NS` | 查权威记录、查续费 |
| 全部 SERVFAIL | 权威配置错（NS 缺失、CAA 冲突） | `dig +trace` 看最后一步 | 找域名服务商 |
| 权威返回错 IP | 记录配错 | 看权威应答 | 改权威记录 |
| 改后部分 DNS 未生效 | TTL 未过期 | 对比 TTL 与等待时间 | 等 TTL 或降 TTL 重来 |
| 域名过期 | 注册到期 | 权威无记录 + 注册状态异常 | 续费 |

### L5 传输层

| 现象 | 根因 | 验证 | 处置 |
|---|---|---|---|
| 53 端口不通 | 防火墙/ACL | `nc -zv <dns> 53`、`nc -uvz <dns> 53` | 通防火墙 |
| UDP 不通 TCP 通 | UDP 被阻断 | `dig +tcp @<dns> <域名>` | 用 TCP 或开 UDP |
| 返回 IP 归属无关 | **污染/劫持** | 见 §6 | 转安全事件 |
| 多域名返回同一 IP | 劫持或泛解析 | 批量解析比对 | 转安全事件 |
| 8.8.8.8 被劫持但 223.5.5.5 正常 | 定向劫持 | 换 DNS 对比 | 转安全事件 |

---

## 六、DNS 污染识别特征

| 特征 | 说明 |
|---|---|
| 返回 IP 归属完全无关 | 与域名业务无关的组织 |
| 多个无关域名返回同一 IP | 批量解析看是否同址 |
| 返回 `0.0.0.0` / `127.0.0.1` | sinkhole 行为 |
| 不存在的 TLD 也能解析 | 泛劫持 |
| `SERVER` 不是配置的 DNS | 应答来源异常 |
| 公共 DNS 被劫持国内正常 | 定向劫持典型表现 |

**识别命令：**

```bash
dig +short asdfjkl1234567890.example     # 随机不存在域名
dig +short randomtest998877.com
dig +trace example.com                   # 看权威应答
dig +short @223.5.5.5 example.com
dig +short @8.8.8.8   example.com
dig +short @1.1.1.1   example.com
dig +short @9.9.9.9   example.com
dig +tcp @<dns> example.com
```

**处置原则：不要只在客户端绕过。** 问题在链路上，换机器照样中招。确认后转网络管理或安全团队；企业可自建递归 DNS 并强制全部出口使用。

---

## 七、常见错误现象对照

| 现象 | 第一直觉 | 真实原因 | 正确做法 |
|---|---|---|---|
| 域名解析不了 | 域名有问题 | 这台机器的缓存或 hosts | 换机器 + 指定公共 DNS 复现 |
| 改了记录不生效 | 记录没保存 | TTL 未过期 | `dig @多DNS` 看差异、查 TTL |
| dig 正常浏览器打不开 | DNS 没问题 | 浏览器独立缓存 | 无痕窗口、清浏览器 DNS |
| ping 通了 | 解析已恢复 | ping 也走缓存且不代表服务通 | `curl -v` 验证业务 |
| 内网域名解析不到 | DNS 故障 | 公网 DNS 本就解析不了 | 连内网、用内网 DNS |
| 时好时坏 | 随机故障 | 解析器不稳或多解析器结果不一致 | 多 DNS 交叉统计成功率 |
| 解析到旧 IP | 缓存 | TTL 未过期 | 降 TTL、等待、指定 DNS 验证 |
| NOERROR 但没结果 | 解析失败 | 域名存在但无该类型记录 | 换类型查 AAAA/MX/CNAME |

---

## 八、dig 命令速查表

| 目的 | 命令 |
|---|---|
| 基础查询 | `dig example.com` |
| 指定 DNS | `dig @8.8.8.8 example.com` |
| 指定记录类型 | `dig example.com A/AAAA/CNAME/MX/TXT/NS/SOA/PTR` |
| 只看答案 | `dig +short example.com A` |
| 只看关键行 | `dig example.com \| grep -E "^;; ->>HEADER\|^example.com"` |
| 追踪解析链 | `dig +trace example.com` |
| 反向追踪 | `dig +trace -x 1.2.3.4` |
| 答案 + 统计 | `dig +noall +answer +stats example.com` |
| 强制 TCP | `dig +tcp example.com` |
| 非 53 端口 | `dig -p 5353 @dns.example.com example.com` |
| 短超时 | `dig +time=2 +tries=1 example.com` |
| 查 DNSSEC | `dig +dnssec example.com`、`dig example.com DNSKEY` |

**nslookup 何时用**：仅在没有 dig 的 Windows 环境。它信息不完整、无 `+trace`、难脚本化。

---

## 九、人工确认清单

- [ ] 现象在哪台机器出现，换机器能复现吗
- [ ] 是解析失败还是解析到错误地址
- [ ] `SERVER` 是不是配置的 DNS
- [ ] hosts 是否被改过（临时测试记录忘了删是常见原因）
- [ ] 记录改动时间 + TTL 是否大于当前时间（是则还没生效）
- [ ] 多个公共 DNS 结果是否一致
- [ ] 内网域名是否已连内网/VPN
- [ ] 是否有人近期改过 DNS 配置
- [ ] 是否为域名过期或续费问题

---

## 十、反误判清单

| 现象 | 误判 | 真实 | 正确 |
|---|---|---|---|
| NXDOMAIN | DNS 坏了 | DNS 正常，域名不存在 | 查记录与续费 |
| 本机能访问 | 全网正常 | 本地有缓存/hosts/VPN | 换机换网复现 |
| 有 ANSWER | 解析正确 | IP 可能是错的 | 核对 IP 归属 |
| ping 通 | 服务正常 | ping 走缓存且服务可能 5xx | `curl -v` 验证 |
| 改了记录 | 应该生效 | TTL 未过期 | 降 TTL 并等待 |
| 解析慢 | 不算故障 | Query time 800ms 是真实体验问题 | 纳入体验指标 |
| 解析到 CDN IP | 是 CDN 加速 | 也可能是被劫持到公共 CDN | 查 IP 归属与是否为预期 CDN |