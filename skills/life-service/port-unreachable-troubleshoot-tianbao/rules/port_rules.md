# 端口不通判定规则表：失败类型、监听、过滤

本文件是 `port-unreachable-troubleshoot` 的核心资产。**判断问题在哪一层之前，先读本文件。**

---

## 一、失败类型 → 排查起点（最重要的一张表）

| 现象 | 报文 | 本质 | 说明什么 | 排查起点 |
|---|---|---|---|---|
| 立即失败（毫秒级） | `Connection refused` | 收到 **RST** | 包**到达了目标**，但目标没监听该端口或主动拒绝 | **L1 目标侧监听** |
| 等待后超时 | `Connection timed out` | 无任何应答 | 包**没到目标**，或到达后被静默丢弃 | **L3/L4 防火墙与安全组** |
| 连接建立后中断 | `Connection reset by peer` | 收到 RST | 连接已建立，被对端或中间设备重置 | 看应用与中间设备 |
| 半连接堆积 | `SYN-RECV` 大量 | backlog 满或 SYN 攻击 | 服务 accept 不过来 | 查 `somaxconn` 与异常来源 |

**铁律：refused 直接跳 L1，timeout 从 L3 开始。不要交叉。**

---

## 二、四层定位执行表

| 层 | 范围 | 命令 | 通过标准 |
|---|---|---|---|
| L1 目标监听 | 服务有没有在监听、绑在哪个地址 | `ss -lntp \| grep :<port>` | 有监听且地址不是 `127.0.0.1` |
| L2 本机出网 | 路由与 DNS | `ip route get <IP>`、`dig +short <域名>` | 路由正确、解析到预期 IP |
| L3 中间过滤 | 云安全组 / 网络 ACL | 云控制台或 API | 入方向规则放行来源 |
| L4 目标过滤 | 目标机器系统防火墙 | `iptables -L INPUT -n -v` | INPUT 链允许该端口 |

---

## 三、监听状态 → 结论对照

| 现象 | 含义 | 结论 |
|---|---|---|
| 无该端口监听记录 | 服务没启动或监听在别的端口 | 端口号/服务问题 |
| `127.0.0.1:<port>` | 只监听回环 | **外网访问必然 refused** |
| `<内网IP>:<port>` | 只监听特定网卡 | 其他网卡访问 refused |
| `[::]:<port>` | 只监听 IPv6 通配 | 纯 IPv4 客户端可能 refused |
| `0.0.0.0:<port>` / `*:<port>` | 监听所有地址 | 监听正常，转查过滤 |
| 监听在容器网桥地址 | 只在容器网络可达 | 宿主机直连 refused，需端口映射 |

> **`127.0.0.1` 与 `0.0.0.0` 的区别是最高频的坑。** 本机 curl 正常而外网 refused，报错完全看不出原因。

---

## 四、两层过滤的区别

| 层 | 位置 | 形式 | 拒绝时的表现 |
|---|---|---|---|
| 云安全组 / 网络 ACL | 流量到达机器**之前** | 云控制台 | **timeout** |
| 系统防火墙 `DROP` | 机器内部 | iptables/nftables/firewalld | **timeout** |
| 系统防火墙 `REJECT` | 机器内部 | iptables `-j REJECT` | **refused** |

> **仅从失败现象无法确定是哪一层在拦**，两侧都要查。「只改了系统防火墙没改安全组」是最常见原因。

---

## 五、常见应用默认端口与监听坑

| 应用 | 默认端口 | 常见监听坑 |
|---|---|---|
| SSH | 22 | 一般绑 `0.0.0.0` |
| HTTP/HTTPS (nginx) | 80/443 | 一般绑 `0.0.0.0` |
| MySQL | 3306 | **常为 `127.0.0.1`** |
| PostgreSQL | 5432 | 常为 `localhost`，需改 `listen_addresses` |
| Redis | 6379 | 常为 `127.0.0.1`，且默认无密码 |
| MongoDB | 27017 | 常绑 `127.0.0.1` |
| Elasticsearch | 9200 | 常绑 `127.0.0.1` |
| Kafka | 9092/9093 | 注意 `advertised.listeners` |
| Docker | 随机 | 需 `-p` 映射，未映射则不通 |
| K8s NodePort | 30000+ | 需确认 Service 类型 |

---

## 六、命令速查

| 目的 | 命令 |
|---|---|
| 监听端口与进程 | `ss -lntp` |
| 指定端口监听 | `ss -lntp \| grep :8080` |
| 端口占用 | `lsof -i :8080` / `fuser -n tcp 8080` |
| 探测端口 | `nc -zv -w 3 <host> <port>` |
| 指定源地址探测 | `nc -zv -w 3 -s <本机IP> <host> <port>` |
| HTTP 详细探测 | `curl -sv http://<host>:<port>/` |
| 只测建连 | `curl -sv --connect-timeout 3 telnet://<host>:<port>` |
| 绕过代理 | `curl --noproxy '*' -sv <url>` |
| 指定端口路由跟踪 | `traceroute -n -T -p <port> <host>` |
| 看路由 | `ip route get <目标IP>` |
| 本机防火墙 | `iptables -L -n -v --line-numbers` |
| 连接汇总 | `ss -s` |
| 对端分布 | `ss -tan \| awk '{print $5}' \| sort \| uniq -c \| sort -rn \| head` |
| 抓包看 SYN/RST | `tcpdump -i any -n port 8080` |
| 代理环境变量 | `env \| grep -i proxy` |
| 内核限制 | `cat /proc/sys/net/core/somaxconn`、`ip_local_port_range` |

---

## 七、端口占用与连接数超限

### 7.1 端口被占

```
Address already in use
bind: address already in use
```

**两种情况要分清：**

| 情况 | 判定 | 处置 |
|---|---|---|
| 被别的进程占用 | `ss -lntp` 显示不同 PID 与程序 | 换端口或停掉占用进程 |
| 同进程重复启动 | 同一 PID 的多 worker/多实例 | **正常，不要误杀** |

**处置顺序（不要直接 kill -9）：**

```
ss -lntp | grep :8080     # 1 确认 PID 与进程名
ps -p <PID> -o pid,cmd    # 2 确认命令行，确认为什么在跑
                          # 3 确认无关后才停
kill <PID>                # 先温和停止
kill -9 <PID>             # 最后手段
```

### 7.2 连接数超限

| 现象 | 结论 | 处置 |
|---|---|---|
| `SYN-RECV` 大量堆积 | backlog 满或 SYN 攻击 | 查 `somaxconn` 与异常来源 |
| `cannot assign requested address` | **本地端口耗尽** | 扩大 `ip_local_port_range`、启用连接复用 |
| TIME-WAIT 大量 | 短连接高频 | 用连接池，别靠调内核参数掩盖 |
| 应用报 too many connections | 应用连接数上限 | 调应用配置，同时确认是需求还是泄漏 |

**相关内核参数与应用限制：**

```bash
cat /proc/sys/net/core/somaxconn              # 全局 backlog
cat /proc/sys/net/ipv4/tcp_max_syn_backlog    # SYN backlog
cat /proc/sys/net/ipv4/ip_local_port_range    # 本地端口范围
# nginx: worker_connections × worker_processes
# MySQL: max_connections
# Redis: maxclients
```

---

## 八、隐蔽干扰因素

| 因素 | 现象 | 验证 |
|---|---|---|
| 代理环境变量 | curl 失败与端口无关 | `env \| grep -i proxy`，加 `--noproxy '*'` 复测 |
| DNS 解析到 IPv6 | 域名失败、IP 成功 | `dig +short <域名> AAAA` |
| `/etc/hosts` 缺条目 | localhost 通、域名不通 | `getent hosts <域名>` |
| 容器未做端口映射 | 容器内通、宿主机不通 | `docker ps` 看映射 |
| 多网卡走错路由 | 时通时不通 | `ip route get <IP>` |
| ping 被禁 | ping 不通但服务正常 | 直接用 `nc` 测端口 |

> **ICMP 常被云环境与安全设备默认禁止**，`ping` 不通不能推出端口不通。

---

## 九、应用层报错与端口的对应

| 报错 | 含义 | 排查方向 |
|---|---|---|
| `Connection refused`（nginx 日志） | 后端端口没监听 | 后端服务与监听地址 |
| `502 Bad Gateway` | 后端连不上 | **先查后端端口是否监听** |
| `504 Gateway Timeout` | 后端连上但响应超时 | 后端慢、连接池、超时设置 |
| `499` | 客户端主动断开 | 客户端超时或取消 |
| `upstream timed out` | 后端响应慢 | 慢查询、后端负载、限流 |

---

## 十、人工确认清单

- [ ] refused 还是 timeout
- [ ] `ss -lntp` 里有没有这个端口
- [ ] 监听地址是 `127.0.0.1` 还是 `0.0.0.0`
- [ ] 服务是否真的在运行
- [ ] 端口是否被别的进程占用
- [ ] 云安全组与系统防火墙是否都查了
- [ ] 是否存在代理环境变量
- [ ] 域名解析到 IPv4 还是 IPv6
- [ ] 是否真要开放新端口（需安全审批）
- [ ] 是否需要设置临时放行的回收时间

---

## 十一、反误判清单

| 现象 | 误判 | 真实 | 正确 |
|---|---|---|---|
| refused | 防火墙拦了 | 包到了目标，是监听问题 | 查 `ss -lntp` 与监听地址 |
| ping 不通 | 端口不通 | ICMP 被禁 | 用 `nc` 直接测端口 |
| 本机 curl 通 | 服务正常 | 只监听 127.0.0.1 | 改监听地址 |
| 改了系统防火墙 | 应该通了 | 还要改安全组 | 两侧都查 |
| 域名不通 | 端口不通 | 可能解析到 IPv6 | `dig` 看解析结果 |
| 偶发 refused | 网络抖动 | 连接数打满 | 看 `ss -s` 与应用上限 |
| 502 | 防火墙问题 | 后端没监听 | 先查后端端口 |
| Address in use | 端口被占 | 可能是同进程多实例 | `ps` 确认后再处理 |
| 慢 | 带宽不够 | 端口没问题，看 SLOW 堆积 | 查应用与磁盘 |