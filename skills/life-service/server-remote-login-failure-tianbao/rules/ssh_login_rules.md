# SSH 登录失败判定规则表

本文件是 `server-remote-login-failure` 的核心资产。**判读客户端日志、服务端日志与配置项之前，先读本文件。**

---

## 一、五层定位执行表

| 层 | 范围 | 关键命令 | 通过标准 |
|---|---|---|---|
| L1 客户端 | 本地配置、密钥、代理、known_hosts、时钟 | `ssh -vvv`、`ssh -G host`、`ssh-add -l` | 无多余密钥尝试 |
| L2 网络端口 | 22 端口可达 | `nc -zv -w 3 <host> 22` | 端口可达 |
| L3 sshd 服务 | 服务状态、监听、配置语法 | `systemctl status sshd`、`sshd -t`、`ss -lntp` | 运行中 + 语法通过 + 监听正常 |
| L4 认证策略 | 关键项、Match 块、账号、fail2ban | `sshd -T -C`、`journalctl -u sshd` | 认证方式与凭据匹配 |
| L5 连接与资源 | MaxStartups、磁盘、OOM | `sshd -T \| grep maxstartups`、`df -h` | 无拒绝、无空间问题 |

**铁律：L3 必须在服务器本地验证，不要靠猜。**

---

## 二、客户端日志判读表

| 日志关键片段 | 含义 | 结论 |
|---|---|---|
| `connect to host X port 22: Connection refused` | 立即 RST | 22 未监听或有东西主动拒绝 |
| `connect to host X port 22: Operation timed out` | 无应答 | 22 被过滤 |
| `Connection closed by remote host` | 连上后被断 | banner 阶段被关，或服务端主动断 |
| `Connection reset by remote host` | 被重置 | MaxStartups 或中间设备 |
| `Permission denied (publickey,password)` | 认证失败 | 凭据错或尝试次数耗尽 |
| `Too many authentication failures` | 本地密钥过多 | **加 IdentitiesOnly=yes** |
| `no matching host key type found` | 主机密钥算法无交集 | 客户端太老或服务端太新 |
| `no matching key exchange method found` | KEX 无交集 | 同上 |
| `no matching cipher found` | 套件无交集 | 同上 |
| `no matching MAC found` | MAC 无交集 | 同上 |
| `Host key verification failed` | 主机密钥变化 | **先核实**再处理 |
| `Authenticated to X` 后卡住 | 会话建立慢 | shell 脚本慢 / 密钥扫描慢 |
| `Entering interactive session` 后立刻断 | 会话被断 | shell 配置、磁盘满、资源限制 |

---

## 三、sshd_config 关键项核对表

| 项 | 推荐值 | 常见错误 | 后果 |
|---|---|---|---|
| `PermitRootLogin` | `no` | 值为 `yes` | root 可被爆破；也可能被拒登 |
| `PasswordAuthentication` | 按需 | **键名拼错** | **静默失效，走默认值** |
| `PubkeyAuthentication` | 按需 | 键名拼错 | 同上 |
| `MaxAuthTries` | 3–6 | `0` | 无爆破防护 |
| `MaxStartups` | 默认或按需调大 | 过小 | 高并发直接拒新连接 |
| `AllowUsers` / `DenyUsers` | 按需 | 写了但未生效 | 用户被拒 |
| `ClientAliveInterval` | 300 | 未配置 | 死连接堆积 |
| `ClientAliveCountMax` | 2 | 未配置 | 同上 |
| `X11Forwarding` | 非必要则 `no` | 开着 | 攻击面增大 |

> **sshd 对无法识别的配置项不报错**，静默使用默认值。
> **改完必须 `sshd -T` 看实际生效值，不能只看配置文件写了什么。**

---

## 四、Match 块陷阱

```
PasswordAuthentication yes

Match User deploy
    PasswordAuthentication no
```

**三个必须知道的点：**

| # | 规则 |
|---|---|
| 1 | Match 块之后的配置项，只在该 Match 上下文中生效 |
| 2 | Match 出现后，后续全局配置项被限制只能用于 Match 块 |
| 3 | 本地 `sshd -T` 不带 `-C` 显示的是**默认上下文**的值，可能与实际不同 |

**验证命令：**

```bash
grep -n -A10 "^Match" /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf
sshd -T -C user=alice,host=<客户端IP>,addr=<客户端IP> | grep -i passwordauth
sshd -T -C user=deploy,host=<客户端IP>,addr=<客户端IP> | grep -i passwordauth
```

---

## 五、Too many authentication failures

**机制**：ssh 客户端默认依次尝试 agent 与 `~/.ssh/` 里**所有**密钥。服务端 `MaxAuthTries` 默认 6。密钥数量超过尝试次数时，**正确的密钥根本没机会被验证**，于是报 `Permission denied`——看起来像凭据错，实际是尝试次数耗尽。

**解决：**

```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 user@host

# 固化到 ~/.ssh/config
Host target
    HostName 10.0.0.5
    User deploy
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes

# 清理 agent
ssh-add -l
ssh-add -D
ssh-add ~/.ssh/id_ed25519
```

> **该问题在不同机器上表现不一致**，因为密钥数量不同，因此极具隐蔽性。

---

## 六、MaxStartups 与暴力破解

**现象**：多人同时登录或有人在爆破时，新连接被拒，且**时好时坏**。

**机制**：`MaxStartups <起始>:<最大>:<随机丢弃阈值>` 控制未认证连接的并发数。超过阈值时随机丢弃部分连接。

```
默认典型值 10:30:100
  10  = 达到 10 个未认证连接开始丢弃
  30  = 达到 30 个后全部拒绝
  100 = 随机丢弃比例达到 100% 时全部丢弃
```

```bash
sshd -T | grep -i maxstartups
journalctl -u sshd --since "-10m" --no-pager | grep -icE "Failed password|Invalid user"
journalctl -u sshd --since "-10m" --no-pager | grep -i "Invalid user" | awk '{print $NF}' | sort | uniq -c | sort -rn | head
```

**必须同时做三件事：**

1. 查是否正在被爆破（`Invalid user` 统计）
2. 在入口设备或用 fail2ban **封禁来源**
3. 改用密钥认证、关闭密码认证

> **仅调大 MaxStartups 会更糟**：未认证连接消耗内存与文件句柄，且爆破流量一起进来，等于把拒绝推迟了。

---

## 七、fail2ban

```bash
fail2ban-client status
fail2ban-client status sshd
fail2ban-client set sshd unbanip <你的IP>       # 解封自己
fail2ban-client set sshd unbanip --all          # 全部解封
fail2ban-client get sshd banip --with-time      # 看封禁时间与原因
```

> 被封的是**出口 IP**，同一网络的同事可能一起被封。发现自己被封时先 `unbanip`，**不要停掉整个服务**——停服务等于放弃防护且影响整网。

---

## 八、被踢下线（登录后被断）

| 根因 | 识别 | 处置 |
|---|---|---|
| `ClientAliveInterval` 太短 + 网络抖动 | 日志 `Timeout, client not responding` | 调大该值 |
| shell 启动脚本卡住 | 本机登录也慢，查 `.bashrc`/`.profile` | 去掉网络请求、慢目录 `cd` |
| 内存耗尽 | `dmesg` 有 OOM | 查内存占用 |
| 会话数超 `MaxSessions`（默认 10） | `who` / `w` 会话数多 | 关闭闲置会话 |
| 强制命令超时 | 配置了 ForceCommand | 查该配置 |

```bash
who ; w
dmesg -T | grep -i "out of memory" | tail
journalctl -k --since "-1d" | grep -i oom | tail
```

---

## 九、磁盘满与 OOM

**磁盘/inode 100% 时 sshd 可能无法写入登录记录**，登录会卡住或失败。

```bash
df -h
df -i
du -xh --max-depth=1 / | sort -h | tail
journalctl --vacuum-size=500M
```

> 磁盘满时改 sshd 配置不解决问题，**必须先清空间**。

---

## 十、登录慢的根因

| 根因 | 识别 | 处置 |
|---|---|---|
| 客户端密钥太多 | `-vvv` 显示尝试多个密钥 | `IdentitiesOnly=yes` |
| 服务端反向 DNS 慢 | sshd 日志延迟 | 评估后 `UseDNS no` |
| `.bashrc` 有网络请求 | 本机登录也慢 | 去掉网络调用 |
| 起始目录在慢盘/NFS | `cd ~` 很慢 | 检查挂载 |
| 时钟偏差过大 | 客户端与服务端 `date -u` 对比 | 修 NTP |

---

## 十一、算法不匹配

| 报错 | 处置 |
|---|---|
| `no matching host key type found` | 升级客户端；临时 `-o HostKeyAlgorithms=+ssh-rsa` |
| `no matching key exchange method found` | 升级客户端；临时 `-o KexAlgorithms=+diffie-hellman-group14-sha1` |
| `no matching cipher found` | 升级客户端 |
| `no matching MAC found` | 升级客户端 |

> 为兼容老客户端放开旧算法会**降低安全性**，这是权衡不是修复。
> 长期做法是升级客户端；临时兼容要限定来源 IP 并设回收时间。

---

## 十二、反误判清单

| 现象 | 误判 | 真实 | 正确 |
|---|---|---|---|
| 密码没错却失败 | 密码真错 | 尝试次数耗尽 | 加 `IdentitiesOnly=yes` |
| 配置写了没生效 | 没 reload | 键名拼错静默失效 | `sshd -T` 看生效值 |
| 有的用户能登有的不能 | 账号问题 | Match 块差异 | `sshd -T -C user=...` |
| 偶发连不上 | 网络抖动 | MaxStartups 丢连接 | 查未认证连接数与爆破 |
| 连接通但立刻断 | 网络问题 | 服务端主动断 | 看 sshd 日志 |
| 登录很慢 | 带宽问题 | 密钥扫描/shell 脚本 | `-vvv` 与本机对比 |
| 磁盘满时改配置 | 配置问题 | 空间问题导致 sshd 起不来 | 先清空间 |
| 被封就停 fail2ban | 快速恢复 | 放弃防护且影响整网 | `unbanip` |
| Host key 变了就忽略 | 解决报错 | 可能是中间人 | 先核实服务端 |
| 连不上就调大 MaxStartups | 缓解拒绝 | 爆破流量一起进来 | 同时封禁来源 |

---

## 十三、必须人工确认

- [ ] 有其他登录入口吗（云控制台 VNC / 控制台 / 物理）
- [ ] 客户端 `-vvv` 完整日志
- [ ] 服务端 `journalctl -u sshd` 日志
- [ ] `sshd -t` 与 `sshd -T` 的实际生效值
- [ ] 是否存在 Match 块
- [ ] AllowUsers / DenyUsers 是否限制当前用户
- [ ] 客户端是否带了过多密钥
- [ ] 是否被 fail2ban 封禁
- [ ] 磁盘与 inode 是否已满
- [ ] 24 小时内是否有 OOM
- [ ] 是否正在遭受爆破
- [ ] 客户端与服务端时钟偏差

---

## 十四、改配置的安全顺序（必须遵守）

```
第 1 步  确认有其他登录入口（云控制台 VNC / 控制台 / 物理）
第 2 步  备份当前配置：cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak
第 3 步  修改配置
第 4 步  sshd -t            # 语法必须通过，输出为空
第 5 步  sshd -T            # 确认实际生效值符合预期
第 6 步  保留当前登录会话，不要退出
第 7 步  开一个新会话验证能连上
第 8 步  通过后再 reload：systemctl reload sshd
第 9 步  确认无异常后再关闭旧会话
```

> **第 6、7 步是防锁死的关键**：先验证新会话能连上，再关掉旧会话。
> 反过来做（先关旧会话再验证）就是标准的事故制造流程。