---
name: port-unreachable-troubleshoot
slug: port-unreachable-troubleshoot-tianbao
displayName: 端口不通与连接失败排查
display_name: "端口不通与连接失败排查"
display_name_en: "Port Unreachable and Connection Failure Troubleshooting"
version: "1.0.0"
summary: 按「目标是否在监听 → 本机能否出网 → 中间链路是否阻断 → 目标侧防火墙与安全组」四层给出 telnet/nc/ss/curl 具体命令与判定表，每种失败报文对应明确结论，含连接被占、连接数超限、IPv6 回退等易误判场景。
description: 连不上某个端口、telnet 超时、curl 报 connection refused、nginx 502、数据库连不上、服务明明启动了却访问不了时使用。当用户说"端口不通怎么查""Connection refused 什么意思""telnet 不通但 ping 通""服务启动了却连不上""端口被占怎么办""ss 怎么看监听端口""防火墙和安全组的区别""502 怎么排查""连接数超限"时使用。内置四层定位表、Connection refused 与 timeout 的本质区别、telnet/nc/ncat/ss/curl/lsof/fuser 具体命令与输出判读、连接被占与端口被占的识别、防火墙与安全组的区别、IPv6 回退误判、常见应用端口对照、配 scripts/port_diagnose.py 做分层判定与失败原因归因。适用于系统管理员、运维工程师、开发人员、技术支持。本技能只做定位路径规划与现象判读，不代替现场网络策略变更与端口开放审批。
license: Apache-2.0
author: 刘天宝｜墨燊
category: it-ops-security
subCategories:
  - itops-network
icon: icon.svg
tags: [端口不通, 连接失败, telnet, nc, ss, netstat, 防火墙, 安全组, Connection refused, 502, 端口占用, 连接数, 运维排查]
language: zh-CN
visibility: public
---

# 端口不通与连接失败排查（port-unreachable-troubleshoot）

端口不通的排查第一件事是**分清 `Connection refused` 和 `timeout`**——它们指向完全不同的层，分错会让整个排查走反方向。

这个技能做一件事：**按四层顺序定位，每种失败报文对应明确结论**。

---

## 硬边界（先看这条）

| 能做 | 不能做 |
|---|---|
| 给出四层定位顺序与判定表 | ❌ 代替你开放端口或修改防火墙 |
| 判读 refused / timeout / reset 的含义 | ❌ 承诺「改完一定能通」 |
| 给出 telnet/nc/ss/curl 命令与判读 | ❌ 代替安全团队做端口开放审批 |
| 识别端口占用与连接数超限 | ❌ 提供绕过安全管控的做法 |
| 给出常见应用端口对照 | ❌ 代替开发排查应用内部问题 |

**出现以下情况，先停下来人工处理，不要自行开放端口：**

- 目标是**生产环境的数据库、中间件、管理后台** → 端口开放必须走审批并评估暴露面
- 需要**在防火墙/安全组新增放行规则** → 这是安全变更，必须经审批，**且要先确认服务是否真的需要对外暴露**
- 出现 `SYN` 已发出但持续 `RST` → 目标侧有东西在主动拒绝，先确认是什么在拒绝
- 需要**临时开放端口排查** → 必须设明确回收时间与责任人，不能「先开着再说」
- 目标是**云主机** → 安全组与系统防火墙是**两层**，只改一层不生效是常见原因
- 怀疑**扫描行为或攻击流量** → 转安全事件处理，不要为了「让它通」而放行

---

## 一、什么时候用这个技能

| 用户这样说 | 就用 |
|---|---|
| "端口不通怎么查" | ✅ |
| "Connection refused 和 timeout 有什么区别" | ✅ |
| "telnet 不通但 ping 通" | ✅ |
| "服务启动了却连不上" | ✅ |
| "端口被占怎么查" | ✅ |
| "ss 怎么看监听端口" | ✅ |
| "防火墙和安全组有什么区别" | ✅ |
| "nginx 502 怎么排查" | ✅ |
| "连接数太多怎么办" | ✅ |
| "帮我把 8080 端口开放一下" | ❌ 需审批与安全评估 |

---

## 二、第一步：先分清两种失败（最关键）

| 现象 | 报文 | 本质 | 说明什么 | 下一步 |
|---|---|---|---|---|
| **立即失败**（毫秒级） | `Connection refused` | 收到 **RST** | **请求到达了目标，但目标没有监听该端口**，或被主动拒绝 | 查目标侧：服务是否启动、监听地址、端口号 |
| **等待后超时**（数秒到数分钟） | `Connection timed out` / 无响应 | **没有收到任何应答** | 包**没有到达目标**，或到达了但被静默丢弃 | 查链路与过滤：防火墙、安全组、路由、ACL |

**两种失败指向完全不同的层：**

```
Connection refused（立即失败）
  → 包到了目标机器 → 问题在目标侧（服务没起/端口不对/监听在别的地址）

Timeout（超时）
  → 包没到目标，或被静默丢弃 → 问题在中间链路（防火墙/安全组/路由/ACL）
```

> **这是整个技能最重要的一条判断。** 把 refused 当防火墙问题去查防火墙，会白查很久；把 timeout 当服务没启动去重启服务，同样白查。

**怎么区分「立即」和「超时」：**

```bash
# telnet 会明确打印两种不同的提示
telnet example.com 8080
# 立即出现 "Connection refused" → refused
# 一直挂着最后 "Connection timed out" → timeout

# nc 更快
nc -zv -w 3 example.com 8080
# refused 几乎瞬间返回；timeout 会等满 -w 秒

# 带耗时更直观
nc -zv -w 3 example.com 8080 2>&1 | grep -E "refused|timed out|succeeded"
```

---

## 三、四层定位法

```
第 0 步  先分清 refused 还是 timeout
第 1  层  目标侧：端口有没有在监听？监听在哪个地址？
第 2  层  本机：能不能出网？路由与 DNS 是否正常？
第 3  层  中间链路：防火墙 / 安全组 / ACL 是否阻断
第 4  层  目标侧过滤：目标机器的防火墙是否放行来源
```

**铁律：refused 直接跳到第 1 层（不用查防火墙），timeout 从第 2 层开始查。**

---

## 四、第 1 层：目标侧监听状态

### 4.1 常用端口与排查命令

```bash
# ss 查监听端口（Linux，推荐）
ss -lntp                          # 所有 TCP 监听，含进程
ss -lntup                         # 含 UDP
ss -lntp | grep :8080            # 查指定端口
ss -lntp 'sport = :8080'         # 语法过滤

# 只看本机监听，不含连接
ss -lnt

# netstat 等价命令
netstat -lntp
netstat -lntp | grep :8080

# lsof 查占用
lsof -i :8080
lsof -i -P -n | grep LISTEN | grep 8080
fuser -n tcp 8080                 # 更快，直接给出 PID

# 确认服务是否真的在跑
systemctl status <服务名>
ps -ef | grep <服务名> | grep -v grep

# 从目标机器本机测试（绕过所有网络环节）
ss -lntp | grep :8080
curl -sv http://127.0.0.1:8080/ # 或 localhost
telnet 127.0.0.1 8080
```

### 4.2 监听状态 → 结论对照

| 现象 | 含义 | 结论 | 处置 |
|---|---|---|---|
| 完全没有该端口的监听记录 | 服务没启动或监听在别的端口 | **端口号/服务问题** | 查服务状态与配置 |
| `127.0.0.1:8080` | 只监听本地回环 | **外网访问必然 refused** | 改监听地址为 `0.0.0.0` 或实际 IP |
| `10.0.0.5:8080` | 只监听具体内网 IP | 其他网卡访问会 refused | 确认客户端是否走同一网卡 |
| `[::]:8080` | 只监听 IPv6 通配 | 纯 IPv4 客户端可能 refused | 确认双栈配置 |
| `*:8080` / `0.0.0.0:8080` | 监听所有地址 | 监听正常，问题在链路或过滤 | 转查防火墙/安全组 |
| 监听在容器网桥地址 | 只在容器网络内可达 | 宿主机直连会 refused | 确认网络模式与端口映射 |

> **`127.0.0.1` 与 `0.0.0.0` 的区别是「服务启动配置」里最高频的坑。**
> 很多服务默认只绑 `127.0.0.1`，本机 curl 正常，外网一律 refused，而报错信息完全看不出原因。

### 4.3 常见应用默认端口对照

| 应用 | 默认端口 | 监听地址常见坑 |
|---|---|---|
| SSH | 22 | 通常 `0.0.0.0` |
| HTTP (nginx) | 80 | 通常 `0.0.0.0` |
| HTTPS (nginx) | 443 | 同上 |
| MySQL | 3306 | **常为 `127.0.0.1`**，远程连不上第一原因 |
| PostgreSQL | 5432 | 常为 `localhost`，需改 `listen_addresses` |
| Redis | 6379 | 常为 `127.0.0.1`，且默认无密码 |
| MongoDB | 27017 | 常绑 `127.0.0.1` |
| Elasticsearch | 9200 | 常绑 `127.0.0.1` |
| Kafka | 9092/9093 | 注意 `advertised.listeners` 配置 |
| Docker (映射) | 随机 | 需 `-p` 映射，未映射则宿主机端口不通 |
| Kubernetes NodePort | 30000+ | 需确认 Service 类型 |

---

## 五、第 2 层：本机出网与路由

```bash
# 基本连通性（ping 通不代表端口通）
ping -c 3 <目标IP>

# 路由是否正确（多网卡/策略路由场景必查）
ip route get <目标IP>
traceroute -n -T -p <端口> <目标IP>     # 指定 TCP 端口的路由跟踪
mtr -r -c 50 -T -P <端口> <目标IP>        # mtr 的 TCP 模式（需较新版本）

# DNS 是否正常（域名访问时必查）
dig +short <域名>
# 注意：telnet/nc 传域名时会先做 DNS 解析，解析失败也会表现为连不上

# 本机防火墙
iptables -L -n -v | head -50
iptables -L INPUT -n --line-numbers
nft list ruleset 2>/dev/null
firewall-cmd --list-all 2>/dev/null       # CentOS/RHEL
ufw status 2>/dev/null                    # Ubuntu
```

**判定：**

| 现象 | 结论 |
|---|---|
| `ping` 通但端口 refused | 服务侧问题（监听），转第 1 层 |
| `ping` 通但端口 timeout | 过滤或 ACL 问题，转第 3、4 层 |
| `ping` 不通 | 网络或防火墙问题，先解决基础连通 |
| `ip route get` 走了非预期网卡 | 多网卡/策略路由问题 |

> **注意**：很多云环境与安全设备**默认禁止 ICMP**，此时 `ping` 不通但服务完全正常。**`ping` 不通不能推出端口不通**，必须用 `nc`/`telnet` 直接测端口。

---

## 六、第 3、4 层：防火墙与安全组

### 6.1 两层过滤的区别（必须分清）

| 层 | 位置 | 常见形式 | 配置位置 |
|---|---|---|---|
| **安全组 / 网络 ACL** | 云平台侧，在流量到达机器**之前** | 云控制台、虚拟网络 ACL | 云厂商控制台 |
| **系统防火墙** | 机器内部，流量**已到达机器** | `iptables`/`nftables`/`firewalld`/`ufw` | 服务器内 |

**关键差异：**

- 安全组拒绝 → 表现为 **timeout**（包被静默丢弃）
- 系统防火墙 `REJECT` 规则 → 也可能是 **refused**（主动回 RST）
- 系统防火墙 `DROP` 规则 → **timeout**

> **因此仅从失败现象无法确定是哪一层在拦**，必须两侧都查。云主机上「只改了系统防火墙没改安全组」或反之，是最常见的原因。

### 6.2 排查命令

```bash
# 系统防火墙：看 INPUT 链与默认策略
iptables -L INPUT -n -v --line-numbers
iptables -S INPUT
# 默认策略 DROP 时，未放行的端口就是 timeout

# 看某个具体端口有没有规则
iptables -L -n | grep 8080

# firewalld
firewall-cmd --list-all
firewall-cmd --list-ports
firewall-cmd --get-active-zones

# ufw
ufw status verbose

# nftables
nft list ruleset

# 云安全组（无法从机器内查清，必须去控制台或 API 确认）
# 关注：入方向规则、源 IP 段、优先级、被其他高优先级规则拒绝
```

**端口被防火墙拦下的三种表现：**

| 规则动作 | 现象 |
|---|---|
| `DROP` / 未匹配且默认 DROP | timeout |
| `REJECT` | refused（RST） |
| 云安全组拒绝 | timeout |

---

## 七、端口被占与连接数超限

### 7.1 端口被占（启动时报错）

```bash
# 查谁占了端口
ss -lntp | grep :8080
lsof -i :8080
fuser -n tcp 8080

# 启动失败的典型信息
# Address already in use
# bind: address already in use
# listen tcp :8080: bind: address already in use
```

> **注意区分两种情况：**
> - **端口被别的进程占用**（`Address already in use`）→ 换端口或停掉占用进程
> - **同一进程重复启动**（如 Nginx 多个 worker、systemd 重复拉起）→ 正常，不要误杀

**处置：**

```bash
# 确认进程后再决定，不要直接 kill
ss -lntp | grep :8080           # 确认 PID 与进程名
ps -p <PID> -o pid,cmd          # 确认命令行为什么
# 确认无关后再停
kill <PID>                      # 先温和停止
kill -9 <PID>                   # 最后手段
```

### 7.2 连接数超限（服务偶发拒绝连接）

```bash
# 连接总数汇总
ss -s

# 分类统计
ss -tan state established | wc -l
ss -tan state time-wait | wc -l
ss -tan state syn-recv | wc -l       # 半连接堆积 = SYN 攻击或 backlog 满

# 按对端统计
ss -tan | awk '{print $5}' | sort | uniq -c | sort -rn | head -20

# 内核限制
cat /proc/sys/net/core/somaxconn            # 全局 backlog 上限
cat /proc/sys/net/ipv4/tcp_max_syn_backlog  # SYN backlog 上限
cat /proc/sys/net/ipv4/ip_local_port_range  # 本地端口范围（耗尽会无法建连）
cat /proc/sys/net/ipv4/tcp_fin_timeout

# 应用层限制（常见于 nginx / 数据库）
# nginx: worker_connections、worker_connections * worker_processes
# MySQL: max_connections
# Redis: maxclients
```

**现象 → 结论：**

| 现象 | 结论 | 处置 |
|---|---|---|
| `SYN-RECV` 大量堆积 | backlog 满或 SYN 攻击 | 查 `somaxconn`、是否有异常来源 |
| 报 `cannot assign requested address` | **本地端口耗尽** | 扩大 `ip_local_port_range`、启用连接复用 |
| TIME-WAIT 大量堆积 | 短连接高频 | 用连接池，不要靠调内核参数掩盖 |
| 应用报 too many connections | 应用连接数上限 | 调应用配置，同时确认是真需求还是连接泄漏 |

---

## 八、IPv6 回退与双栈误判

| 现象 | 原因 | 验证 | 处置 |
|---|---|---|---|
| IPv4 通、IPv6 不通 | 服务只监听 IPv4 | `ss -lntp \| grep :端口` | 明确只用 IPv4，或配置双栈 |
| IPv6 通、IPv4 不通 | 服务只监听 IPv6 | 同上 | 同上 |
| 用域名访问失败、用 IP 成功 | **DNS 返回了 AAAA 记录** | `dig +short <域名> AAAA` | 客户端 IPv6 不可达 |
| `localhost` 通、域名不通 | `/etc/hosts` 缺该域名 | `getent hosts <域名>` | 补 hosts 或修 DNS |

> **排查技巧**：客户端用域名时，先 `dig` 确认解析到哪个 IP（可能是 IPv6），
> 再用那个 IP 直接测端口，排除 DNS 与双栈因素。

---

## 九、命令速查表

| 目的 | 命令 |
|---|---|
| 查监听端口与进程 | `ss -lntp` |
| 查指定端口监听 | `ss -lntp \| grep :8080` |
| 查端口占用 | `lsof -i :8080` / `fuser -n tcp 8080` |
| 探测目标端口 | `nc -zv -w 3 <host> <port>` |
| 探测（TCP 指定源） | `nc -zv -w 3 -s <本机IP> <host> <port>` |
| telnet 探测 | `telnet <host> <port>` |
| HTTP 探测（更完整） | `curl -sv http://<host>:<port>/` |
| 只测 TCP 是否建连 | `curl -sv --connect-timeout 3 telnet://<host>:<port>` |
| 指定端口做路由跟踪 | `traceroute -n -T -p <port> <host>` |
| 看路由 | `ip route get <目标IP>` |
| 看本机防火墙 | `iptables -L -n -v --line-numbers` |
| 看连接汇总 | `ss -s` |
| 看对端分布 | `ss -tan \| awk '{print $5}' \| sort \| uniq -c \| sort -rn \| head` |
| 抓包确认 SYN/RST | `tcpdump -i any -n port 8080` |
| 目标本机自测 | `curl -sv http://127.0.0.1:<port>/` |

> **`curl telnet://` 很好用**：它能给出详细的连接过程与失败原因，比裸 telnet 输出更明确。

---

## 十、502 / 504 等应用层报错的端口含义

| 报错 | 含义 | 排查方向 |
|---|---|---|
| `Connection refused`（nginx 日志） | **后端端口没在监听** | 查后端服务与监听地址 |
| `502 Bad Gateway` | 后端连不上（refused/不可达） | 后端服务、监听地址、端口 |
| `504 Gateway Timeout` | 后端连上了但**响应超时** | 后端慢、连接池、超时设置 |
| `499` | 客户端主动断开 | 客户端超时或取消 |
| `upstream timed out` | 后端响应慢 | 慢查询、后端负载、限流 |

> **502 优先查后端端口是否在监听**——这是最常见且最容易修的一类。

---

## 十一、脚本用法

```bash
python scripts/port_diagnose.py --file obs.txt --host example.com --port 8080
```

| 参数 | 说明 |
|---|---|
| `--file` | 观测数据，每行 `检查项\|结果`，见下表 |
| `--host` | 目标主机，用于生成命令清单 |
| `--port` | 目标端口 |
| `--json` / `--out` | JSON 输出 / 写入指定报告文件 |
| `--selftest` | 跑内置自检（≥ 8 条断言） |

**输入文件键名：**

```
probe_result=refused|timeout|ok     # nc/telnet 探测结果
listen_found=1                       # 目标侧是否有该端口监听
listen_addr=127.0.0.1               # 监听地址（关键！）
service_running=1                   # 目标服务是否在运行
port_occupied=0                     # 端口是否被别的进程占用
route_ok=1                          # 本机路由是否正确
ping_ok=1                           # ping 是否通（仅供参考）
local_firewall_ok=1                 # 本机防火墙是否放行
secgroup_ok=1                       # 云安全组是否放行
target_firewall_ok=1                # 目标机器防火墙是否放行
est_conn=180                        # 目标 ESTABLISHED 连接数
timewait_conn=960                   # 目标 TIME-WAIT 连接数
syn_recv=0                          # 目标 SYN-RECV 数
resolved_ip=1.2.3.4                 # 域名解析到的 IP
proxy_env_hit=1                     # 是否存在代理环境变量干扰
```

脚本做四件事：① 区分 refused 与 timeout 并给出**不同的排查起点**；② 识别监听地址类问题（`127.0.0.1` 只对本地可达）；③ 识别端口占用、连接数超限、端口耗尽；④ 识别代理环境变量、DNS 解析、IPv6 等隐蔽干扰因素。

> 脚本**不发起任何网络连接**，它只归拢你已采集的观测结果。它的价值在于**防止「refused 却去查防火墙」这类方向性错误**。

---

## 十二、人工确认清单（这步不能省）

- [ ] 失败是 **refused（立即）** 还是 **timeout（等待后）**
- [ ] 目标侧 `ss -lntp` 里**有没有**这个端口
- [ ] 监听地址是 `127.0.0.1` 还是 `0.0.0.0`（这是最高频的坑）
- [ ] 服务是否真的在运行（`systemctl status`）
- [ ] 端口是否被别的进程占用
- [ ] 云安全组与系统防火墙**两层都查了吗**
- [ ] 是否存在代理环境变量（`env | grep -i proxy`）干扰
- [ ] 域名解析到的是 IPv4 还是 IPv6
- [ ] 目标机器上是否有**其他东西在主动拒绝**（不是没监听，是被 reject）
- [ ] 是要开放新端口还是修复已有配置（**前者需安全审批**）

---

## 十三、最常见的坑

**坑一：不看 refused 还是 timeout，直接查防火墙。**
`Connection refused` 说明包**到了目标机器**，是目标侧没有监听或主动拒绝，跟防火墙基本无关。查防火墙会白查很久。

**坑二：服务只监听 127.0.0.1。**
本机 `curl localhost:8080` 完全正常，一换外部就 refused，而报错信息看不出任何原因。数据库与中间件尤其常见。**监听地址是排查监听类问题的第一检查项。**

**坑三：把 ping 不通当成端口不通。**
很多云环境与安全设备默认禁止 ICMP，ping 不通但服务完全正常。**必须用 `nc`/`telnet` 直接测端口**，ping 只能作为参考。

**坑四：只改了系统防火墙，忘了云安全组。**
云主机有两层过滤，只改一层不生效。反过来也一样。**两侧都要查。**

**坑五：用域名测试却不看解析结果。**
域名可能解析到 IPv6 地址，而服务只监听 IPv4。先 `dig` 看解析到什么，再用 IP 直接测端口。

**坑六：忽略代理环境变量。**
机器上设了 `http_proxy`/`https_proxy` 时，`curl` 的失败可能与端口无关，而是走了代理。先 `env | grep -i proxy` 确认，并加 `--noproxy '*'` 复测。

**坑七：端口被占就 kill -9。**
没确认占用者是什么就 kill，可能杀掉的是正常业务进程，甚至杀掉正在服务的进程导致中断。正确顺序：`ss -lntp` 确认 PID → `ps -p` 确认命令行 → 再决定。

**坑八：把连接数超限当端口不通。**
服务偶发 refused 但实际是 `max_connections` 打满。现象相似，根因完全不同，必须看 `ss -s` 与应用连接数指标。

**坑九：把 502 当端口问题一直查防火墙。**
502 的第一原因是**后端端口没在监听**，先查后端服务状态，而不是网络链路。

**坑十：临时开放端口后忘了回收。**
「先开着排查一下」变成长期开放，是最常见的配置债务来源。临时放行必须设回收时间与责任人。

**坑十一：NAT/端口映射场景没查映射。**
容器 `-p` 未映射、负载均衡未配置监听端口、云主机安全组放行但实际未监听——都要对照确认。

**坑十二：内核参数当作万能解法。**
SYN-RECV 堆积就调大 `somaxconn`、TIME-WAIT 多就调内核超时，可能掩盖真实问题（比如 SYN 攻击或连接泄漏）。先定位根因再调参。

---

## 十四、边界与免责

- 本技能给出的是**定位路径与判读口径**，不代替现场网络策略变更与端口开放审批
- **在防火墙或安全组新增放行规则属于安全变更**，必须经审批，并先确认服务是否真的需要对外暴露
- 涉及**生产环境数据库、中间件、管理后台的端口开放**，需评估暴露面与最小化方案，**以现行规定和本单位安全要求为准**
- 脚本**不发起任何网络连接**，只归拢观测结果
- 探测他人系统端口须取得授权；**不得对未授权目标进行端口扫描或连通性探测**
- 调整内核网络参数需评估对整机的影响，并记录变更

---

## 十五、许可

本技能由 **刘天宝｜墨燊** 原创，采用 **Apache License 2.0**。

`rules/port_rules.md` 中的端口对照与阈值整理为通用实践，不同应用版本与环境的默认值会有差异，落地前请以现场实际配置为准。