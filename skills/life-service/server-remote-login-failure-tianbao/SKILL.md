---
name: server-remote-login-failure
slug: server-remote-login-failure-tianbao
displayName: 服务器无法远程登录排查
display_name: "服务器无法远程登录排查"
display_name_en: "Server Remote Login Failure Troubleshooting"
version: "1.0.0"
summary: 按「客户端 → 网络与端口 → sshd 服务与配置 → 认证策略 → 连接数与资源」五层给出 ssh -vvv 关键日志判读、sshd_config 关键项核对表、fail2ban 与 MaxStartups 机制说明、根目录残留会话、自锁与暴力破解的识别与解锁命令。
description: SSH 连不上服务器、密码对却登不上、被踢下线、提示 too many authentication failures、连接很慢很卡、root 登不上、密钥认证失败、sshd 改坏了进不去时使用。当用户说"SSH 连不上怎么办""密码没错却登录失败""too many authentication failures""Connection closed by remote host""sshd 改完连不上了""root 登录被拒""SSH 登录很慢""fail2ban 把自己封了"时使用。内置五层定位表、ssh -vvv 关键日志逐行判读、sshd_config 关键项核对表（含错误写法对照）、PermitRootLogin/PasswordAuthentication/AllowUsers/AllowTcpForwarding 生效优先级与 Match 块陷阱、MaxStartups 与 SSHD 暴力破解机制、fail2ban 解锁命令、被踢下线的三类根因、磁盘满导致 sshd 无法启动、时钟错误导致认证失败等隐蔽原因。适用于系统管理员、运维工程师、开发人员、技术支持。本技能只做定位路径规划与现象判读，不代替现场登录解锁操作与配置变更审批。
license: Apache-2.0
author: 刘天宝｜墨燊
category: it-ops-security
subCategories:
  - itops-security
icon: icon.svg
tags: [SSH, 远程登录, 连不上, sshd, 认证失败, fail2ban, MaxStartups, 暴力破解, root登录, 密钥认证, 运维排查, 自锁]
language: zh-CN
visibility: public
---

# 服务器无法远程登录排查（server-remote-login-failure）

SSH 连不上的排查，第一件事是**拿到客户端的详细日志**。没有 `-vvv` 的输出就开始猜，是这类问题最常见的浪费。

这个技能做一件事：**按五层顺序定位，每条日志对应明确结论**。

---

## 硬边界（先看这条）

| 能做 | 不能做 |
|---|---|
| 给出五层定位顺序与日志判读 | ❌ 代替你解锁账号或改认证配置 |
| 给出 sshd_config 关键项核对表 | ❌ 承诺「按我说的改完就能登」 |
| 给出 fail2ban 解锁命令 | ❌ 提供暴力破解他人主机的方法 |
| 识别自锁与暴力破解 | ❌ 提供绕过认证的技巧 |
| 给出改配置前的安全操作顺序 | ❌ 代替你做配置变更（需审批） |

**出现以下情况，先停下来人工处理，不要自行操作：**

- **已改过 sshd 配置且现在登不上** → **先不要关 sshd**，先本机验证语法再 reload，否则会把自己彻底锁在外面
- **唯一的远程入口就是这台机器的 SSH** → 任何改动前必须先确认有其他入口（云控制台 VNC、控制台登录、物理访问）
- 疑似**暴力破解或攻击流量** → 转安全事件处理，不要为了「让自己进去」而关掉防护
- 涉及**生产服务器认证配置变更** → 走变更流程，且必须保留回滚路径
- 需要**重置 root 或他人密码** → 需授权并留记录
- 磁盘/ inode **已 100% 满** → sshd 可能无法启动，先处理空间问题（见 §7.4）

> **最重要的一条安全提醒**：`sshd_config` 改错且 `systemctl reload sshd` 失败，是把自己锁在门外的经典方式。**永远不要在只有 SSH 一个入口的机器上直接改配置并 reload**——先 `sshd -t` 验证，再确认有其他入口，最后才 reload。

---

## 一、什么时候用这个技能

| 用户这样说 | 就用 |
|---|---|
| "SSH 连不上服务器怎么办" | ✅ |
| "密码没错却登录失败" | ✅ |
| "too many authentication failures" | ✅ |
| "Connection closed by remote host" | ✅ |
| "sshd 改完连不上了" | ✅ |
| "root 登录被拒" | ✅ |
| "SSH 登录很慢很卡" | ✅ |
| "fail2ban 把自己封了" | ✅ |
| "每次登录都被踢下线" | ✅ |
| "帮我登上服务器看看" | ❌ 需授权与现场操作 |

---

## 二、五层定位法

```
第 1 层  客户端：本地 SSH 配置、密钥、代理、已知主机、时钟
第 2 层  网络与端口：目标 22 端口是否可达
第 3 层  sshd 服务：服务是否在运行、监听状态、配置是否有效
第 4 层  认证策略：sshd_config 关键项与 Match 块、账号状态、密钥、fail2ban
第 5 层  连接数与资源：MaxStartups、磁盘满、内存、内存耗尽、负载
```

**铁律：第 3 层必须先在服务器本地验证，不要靠猜。**

---

## 三、第 1 层：客户端

### 3.1 必须先拿到的信息

```bash
# 客户端详细日志（最重要的输入）
ssh -vvv user@host
# Windows 也支持：ssh -vvv user@host

# 只看关键部分
ssh -vvv user@host 2>&1 | grep -iE "debug1:|authentications that can continue|\
permission denied|connection|refused|timed out|banner exchange"
```

### 3.2 客户端日志关键行判读

| 日志关键片段 | 含义 | 结论 | 下一步 |
|---|---|---|---|
| `ssh: connect to host X port 22: Connection refused` | 立即 RST | 服务没监听 22 或有东西主动拒绝 | 转第 2、3 层 |
| `ssh: connect to host X port 22: Operation timed out` | 无应答 | 22 端口被过滤 | 转第 2 层 |
| `Connection closed by remote host` | 连上后被断开 | **banner 阶段就被关**，或服务端主动断开 | 看服务端 sshd 日志 |
| `Connection reset by remote host` | 被重置 | 可能是 MaxStartups 或中间设备 | 转第 5 层 |
| `Permission denied (publickey,password)` | 认证失败 | 认证方式不匹配或凭据错误 | 转第 4 层 |
| `Too many authentication failures` | 本地密钥尝试过多 | **客户端发了太多密钥**，见 §6.1 | 转第 6.1 |
| `no matching host key type found` | 算法不匹配 | 客户端与服务端算法无交集 | 见 §5.3 |
| `no matching key exchange method found` | KEX 算法不匹配 | 同上 | 见 §5.3 |
| `Host key verification failed` | 主机密钥变了 | 服务端重装/密钥变更，或中间人 | **不要盲目忽略**，先核实 |
| `no matching MAC found` | MAC 算法不匹配 | 见 §5.3 | 见 §5.3 |
| `Authenticated to X` 之后长时间卡 | 认证通过但会话建立慢 | shell 启动脚本慢、密钥扫描慢 | 见 §7.3 |
| `Entering interactive session` 后立刻断开 | 会话建立后被断 | shell 配置、磁盘满、资源限制 | 转第 5 层 |

### 3.3 客户端常见干扰因素

```bash
# SSH 配置是否有问题
cat ~/.ssh/config
ssh -G host              # 查看最终生效的配置（不发起连接）

# 本地密钥列表与顺序
ls -la ~/.ssh/
ssh-add -l                # agent 中的密钥

# 代理是否干扰
env | grep -i proxy
ssh -o ProxyCommand=none user@host    # 排除代理干扰

# 已知主机记录（改过服务端密钥后会冲突）
cat ~/.ssh/known_hosts
ssh-keygen -F host        # 查看某个主机的记录
# 确认服务端确实变更过密钥后再清理
sed -i '/^host /d' ~/.ssh/known_hosts

# 本地时钟（认证失败有时与时钟有关）
date; timedatectl
```

> **`IdentitiesOnly` 是高频坑**：ssh 默认会把 agent 或 `~/.ssh/id_*` 里**所有**密钥依次尝试给服务端。如果服务端设了 `MaxAuthTries 3` 或客户端里有十几个密钥，就会先把这三次机会用光，导致真正正确的密钥根本没机会被试——于是报 `Permission denied`，看起来像「密码或密钥错了」，实际是**尝试次数耗尽**。
> 解决办法：`ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 user@host`

---

## 四、第 2 层：网络与端口

```bash
# 端口探测（区分 refused 与 timeout，含义完全不同）
nc -zv -w 3 <host> 22
telnet <host> 22

# 路由与链路
ip route get <目标IP>
traceroute -n -T -p 22 <host>

# 目标 22 端口是否放行（云安全组与系统防火墙都要看）
```

| 现象 | 结论 |
|---|---|
| `Connection refused` | 包到了目标，22 没在监听或有东西主动拒绝 |
| `Operation timed out` | 22 端口被过滤（安全组/防火墙/ACL） |
| 通但 `Connection closed by remote host` | 端口没问题，转第 3、4 层 |

> 端口不通的详细排查方法见「端口不通与连接失败排查」类技能的口径：安全组与系统防火墙是**两层**，只改一层不生效。

---

## 五、第 3 层与第 4 层：sshd 服务与认证策略

### 5.1 必须在服务器本地执行的检查

```bash
# 服务是否在运行、是否启用
systemctl status sshd
systemctl is-active sshd
systemctl is-enabled sshd

# 监听状态（关键：看绑在哪个地址）
ss -lntp | grep :22
netstat -lntp | grep :22

# 配置语法是否正确（改配置后必做）
sshd -t
# 输出为空 = 语法正确

# 当前生效配置（注意 Match 块的上下文）
sshd -T | grep -iE "permitrootlogin|passwordauthentication|\
pubkeyauthentication|maxauthtries|maxstartups|allowusers|denyusers|port"
sshd -T -C user=<测试用户>,host=<客户端IP>,addr=<客户端IP>
# ↑ 用 -C 模拟连接上下文，正确评估 Match 块的影响

# 服务端日志（最重要的服务端证据）
journalctl -u sshd --since "-30m" --no-pager
journalctl -u sshd -n 200 --no-pager
tail -100 /var/log/secure            # CentOS/RHEL
tail -100 /var/log/auth.log          # Debian/Ubuntu

# 认证失败统计
journalctl -u sshd --since "-1h" --no-pager | grep -icE "Failed password|Invalid user"
```

### 5.2 sshd_config 关键项核对表

| 项 | 推荐值 | 常见错误 | 错误的后果 |
|---|---|---|---|
| `PermitRootLogin` | `no` | 值为 `yes` | root 可被暴力破解；也可能被策略拒登 |
| `PasswordAuthentication` | 按需 | 键名拼错（如 `PasswordAuthenication`） | **配置项不生效，走默认值** |
| `PubkeyAuthentication` | 按需 | 同上 | 同上 |
| `MaxAuthTries` | 3–6 | `0`（不限） | 无暴力破解防护 |
| `MaxStartups` | 默认或调大 | 过小 | 高并发时**直接拒绝新连接**（见 §6.2） |
| `AllowUsers` | 按需 | 写了但没生效（见 §5.4） | 用户被拒 |
| `DenyUsers` | 按需 | 同上 | 同上 |
| `ClientAliveInterval` | 300 | 未配置 | 死连接堆积 |
| `ClientAliveCountMax` | 2 | 未配置 | 同上 |
| `X11Forwarding` | `no`（非必要） | 开着 | 攻击面增大 |

> **拼错配置项名是隐蔽的坑**：sshd 对无法识别的配置项**不报错**，会静默使用默认值。所以改完务必用 `sshd -T` 确认**实际生效值**，而不是看配置文件写了什么。

### 5.3 算法不匹配（老旧客户端连新服务端）

| 报错 | 原因 | 处置 |
|---|---|---|
| `no matching host key type found` | 服务端只开新算法，客户端太老 | 升级客户端；临时指定 `-o HostKeyAlgorithms=+ssh-rsa` |
| `no matching key exchange method found` | KEX 算法无交集 | 升级客户端；临时指定 `-o KexAlgorithms=+diffie-hellman-group14-sha1` |
| `no matching MAC found` | MAC 算法无交集 | 升级客户端 |
| `no matching cipher found` | 加密套件无交集 | 升级客户端；服务端放开 `ssh-rsa` 需评估安全性 |

**取舍说明**：为兼容老客户端而在服务端放开 `ssh-rsa`、`diffie-hellman-group14-sha1` 等旧算法，会**降低安全性**。这是权衡，不是纯粹的修复。长期做法是**升级客户端**，临时兼容要限定来源 IP 并设回收时间。

### 5.4 Match 块陷阱（最隐蔽的一类）

```
# /etc/ssh/sshd_config
PasswordAuthentication yes

Match User deploy
    PasswordAuthentication no
```

**影响**：`deploy` 用户走 no，其他用户走 yes。

**三个必须知道的点：**

1. **Match 块之后的配置项，只在 Match 上下文中生效**。写在 Match 块之后的全局配置**对普通用户不再生效**。
2. **`Match` 一旦出现，后面的全局配置项被限制只能用于 Match 块**，写成全局项会报配置错误或行为异常。
3. **本地 `sshd -T` 不带 `-C` 时看到的是「默认上下文」的值**，可能与实际连接时的值不同。必须用 `sshd -T -C user=<用户>,host=<客户端IP>,addr=<客户端IP>` 验证。

**排查要点：**

```bash
grep -n -A10 "^Match" /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf
sshd -T -C user=alice,host=10.0.0.5,addr=10.0.0.5 | grep -i passwordauth
sshd -T -C user=deploy,host=10.0.0.5,addr=10.0.0.5 | grep -i passwordauth
```

---

## 六、第 5 层：连接数与暴力破解

### 6.1 Too many authentication failures（客户端密钥过多）

**现象**：`Too many authentication failures` 或明明密钥正确却 `Permission denied`。

**机制**：ssh 客户端默认会依次尝试 agent 与 `~/.ssh/` 里的**所有**密钥。服务端 `MaxAuthTries` 默认 6 次。一旦密钥数量超过尝试次数，真正的正确密钥**根本没机会被验证**。

**解决：**

```bash
# 只用指定密钥
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 user@host

# 或在 ~/.ssh/config 里固化
cat >> ~/.ssh/config <<'EOF'
Host target-host
    HostName 10.0.0.5
    User deploy
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
EOF

# 清理 agent 中多余密钥
ssh-add -l
ssh-add -D                  # 全部移除后按需重新添加
ssh-add ~/.ssh/id_ed25519
```

### 6.2 MaxStartups 与 sshd 暴力破解（服务端拒绝连接）

**现象**：多人同时登录或有人在爆破时，新连接直接被拒（`Connection closed by remote host` 或 `Connection reset`）。

**机制**：`MaxStartups <起始>:<最大>:<随机丢弃阈值>` 控制**未认证连接**的并发数。超过阈值时 sshd 会**随机丢弃**部分连接——所以表现为「有时候能连上，有时候连不上」。

```bash
# 查看当前配置
sshd -T | grep -i maxstartups

# 默认典型值 10:30:100
#   10 = 达到 10 个未认证连接开始丢弃
#   30 = 达到 30 个后全部拒绝
#   100 = 随机丢弃比例达到 100% 时全部丢弃

# 调整（示例，需评估后使用）
# MaxStartups 30:30:60
```

**必须同时做的三件事：**

```bash
# 1. 查是否正在被爆破
journalctl -u sshd --since "-10m" --no-pager | grep -icE "Failed password|Invalid user"
journalctl -u sshd --since "-10m" --no-pager | grep -i "Invalid user" | awk '{print $NF}' | sort | uniq -c | sort -rn | head

# 2. 封禁来源（防火墙层，比 sshd 内部封禁更有效）
#    在入口设备上封禁，或用 fail2ban

# 3. 改用密钥认证、关闭密码认证
```

> **仅调大 MaxStartups 会让情况更糟**——未认证连接会消耗更多内存与文件句柄，而且爆破流量也一起放进来。**必须同时封禁来源**，否则只是把拒绝推迟了。

### 6.3 fail2ban

```bash
# 查看是否在运行与当前封禁
fail2ban-client status
fail2ban-client status sshd

# 解封（把自己锁在外面时的第一件事）
fail2ban-client set sshd unbanip <你的IP>

# 全部解封
fail2ban-client set sshd unbanip --all

# 查看某 IP 的封禁原因
fail2ban-client get sshd banip --with-time
```

> **fail2ban 封禁的是你正在用的出口 IP**，如果你在同一网络里，可能连带同事一起被封。发现自己被封时，先 `unbanip`，不要去停掉整个服务——停服务等于放弃防护。

---

## 七、容易被忽略的三类根因

### 7.1 被踢下线（Connected to ... then closed）

| 根因 | 识别 | 处置 |
|---|---|---|
| `ClientAliveInterval` 太短 + 网络抖动 | 服务端日志有 `Timeout, client not responding` | 调大 `ClientAliveInterval` |
| shell 启动脚本卡住 | 本机登录也慢，检查 `.bashrc`/`.profile` | 去掉网络请求、`cd` 到慢目录 |
| 内存耗尽 | `dmesg` 有 OOM 记录 | 查内存占用 |
| 强制命令超时 | 配置了 `ClientAlive*` + 强制命令 | 查 ForceCommand |
| 会话被并发限制踢出 | `MaxSessions` 默认 10 | 查已登录会话数 |

```bash
# 当前登录会话
who
w
# 已登录用户数超 MaxSessions（默认 10）会导致新会话被拒

# OOM 记录
dmesg -T | grep -i "out of memory" | tail
journalctl -k --since "-1d" | grep -i oom | tail
```

### 7.2 磁盘满导致 sshd 无法启动

**现象**：磁盘 100% 后 sshd 起不来或登录时卡死。

```bash
df -h
df -i                    # inode 也可能是元凶

# 清理空间（先确认再删，不要盲删日志目录）
du -xh --max-depth=1 / | sort -h | tail
journalctl --vacuum-size=500M
```

> 磁盘满时 sshd 可能无法写入 `utmp`/`wtmp`，登录会卡住或失败。**必须先处理空间问题**，改配置不解决。

### 7.3 登录很慢（认证通过但会话建立慢）

| 根因 | 识别 | 处置 |
|---|---|---|
| 客户端密钥太多 | `-vvv` 显示尝试多个密钥 | 加 `IdentitiesOnly=yes` |
| 服务端反向 DNS 查询慢 | sshd 日志有延迟 | 配 `UseDNS no`（注意副作用） |
| `.bashrc` 里有网络请求 | 本机登录也慢 | 去掉网络调用 |
| shell 起始目录在慢盘/NFS | `cd ~` 很慢 | 检查挂载 |
| 熵池不足（旧系统） | 启动日志提示熵 | 用 `haveged` 类方案 |

### 7.4 时钟错误导致认证失败

```bash
# 客户端与服务端时钟偏差过大会导致 SSH 协议时间戳校验失败
date -u
timedatectl
chronyc tracking 2>/dev/null || ntpq -p 2>/dev/null
```

**现象**：`Connection reset by peer` 或在启用 `StrictModes` 与公钥认证时出现难以解释的失败。

---

## 八、排查决策树

```
SSH 连不上
 │
 ├─ 有其他入口吗？（云控制台 VNC / 控制台 / 物理）
 │    └─ 没有 → 先确认有其他入口再动配置（不要把自己锁死）
 │
 ├─ 端口通吗？（nc -zv -w 3 <host> 22）
 │    ├─ refused → 转「端口不通」类排查：22 未监听
 │    └─ timeout → 查安全组与防火墙
 │
 ├─ 拿到客户端 -vvv 日志了吗？
 │    └─ 必须拿。Connection closed / reset / Permission denied
 │       的处置完全不同
 │
 ├─ Connection closed / reset
 │    ├─ 服务端 sshd 日志有 Timeout → ClientAlive 配置或网络抖动
 │    ├─ 日志有 MaxStartups 相关 → 未认证连接过多（查爆破）
 │    ├─ 日志无记录 → 看磁盘满、内存、服务是否在跑
 │    └─ 本机也登不上 → 转「服务端本地排查」（云控制台进入）
 │
 ├─ Permission denied
 │    ├─ 密钥/密码确实错？→ 改对后重试
 │    ├─ 尝试次数耗尽？→ 加 IdentitiesOnly=yes
 │    ├─ sshd_config 里 AllowUsers/DenyUsers 限制？→ 看配置
 │    ├─ 账号被锁定？→ passwd -S、查 faillock
 │    ├─ 失败但日志显示认证成功？→ Match 块陷阱
 │    └─ 被 fail2ban 封？→ unbanip
 │
 └─ 服务端本地检查（云控制台 / 物理进入）
      systemctl status sshd
      sshd -t                     # 配置语法
      sshd -T -C user=<用户>,addr=<客户端IP>
      ss -lntp | grep :22         # 监听地址
      journalctl -u sshd -n 200
      df -h ; df -i               # 磁盘满会导致 sshd 起不来
```

---

## 九、脚本用法

```bash
python scripts/ssh_login_check.py --file obs.txt --user deploy
```

| 参数 | 说明 |
|---|---|
| `--file` | 观测数据，每行 `检查项\|结果`，见下表 |
| `--user` | 登录的用户名 |
| `--client-ip` | 客户端 IP，用于评估 AllowUsers/DenyUsers 与封禁 |
| `--json` / `--out` | JSON 输出 / 写入指定报告文件 |
| `--selftest` | 跑内置自检（≥ 8 条断言） |

**输入文件键名：**

```
probe_result=refused|timeout|ok        # nc/telnet 探测 22 端口结果
sshd_active=1                          # sshd 服务是否在运行
sshd_syntax_ok=1                       # sshd -t 是否通过
listen_addr=0.0.0.0                    # 22 端口监听地址
login_ok=0                             # 能否成功登录
auth_error=1                           # 是否报认证失败
client_err=too many authentication failures   # 客户端关键日志行
server_log=Timeout, client not responding  # 服务端日志关键行
max_auth_tries=6                       # 服务端 MaxAuthTries
max_startups=10:30:100                 # 服务端 MaxStartups
fail2ban_banned=1                      # 是否被 fail2ban 封禁
fail2ban_jail=1                        # 是否存在 jail 配置
disk_used_pct=96                       # 磁盘使用率
inode_used_pct=99                      # inode 使用率
oom_seen=1                             # 24h 内是否有 OOM
allowusers_ok=0                        # AllowUsers 是否限制了当前用户
match_block_hit=1                      # 是否存在 Match 块陷阱
```

脚本做五件事：① 区分 refused / timeout / 认证失败三类根因；② 识别 `Too many authentication failures` 这一**看起来像凭据错、实际是客户端密钥过多**的场景；③ 识别服务端侧的暴力破解与 `MaxStartups` 拒绝；④ 识别磁盘满、OOM、fail2ban 封禁这类隐蔽根因；⑤ 输出按层推进的排查步骤。

> 脚本**不发起任何 SSH 连接、不修改任何配置**，它只归拢已采集的观测结果。

---

## 十、人工确认清单（这步不能省）

- [ ] 有**其他登录入口**吗（云控制台 VNC / 控制台 / 物理）
- [ ] 客户端 `-vvv` 的完整日志（不要凭描述排查）
- [ ] 服务端 `journalctl -u sshd` 的日志（这才是真正的证据）
- [ ] `sshd -t` 是否通过、`sshd -T` 的**实际生效值**是什么
- [ ] 是否存在 `Match` 块（用 `sshd -T -C user=<用户>,addr=<IP>` 验证）
- [ ] `AllowUsers` / `DenyUsers` 是否限制了当前用户
- [ ] 客户端是否带了过多密钥（`ssh -vvv` 看尝试了几次）
- [ ] 是否被 fail2ban 封禁（`fail2ban-client status sshd`）
- [ ] 磁盘与 inode 是否已满（磁盘满会导致 sshd 起不来）
- [ ] 24 小时内是否有 OOM
- [ ] 是否正在遭受爆破（`Invalid user` 统计）
- [ ] 客户端与服务端时钟偏差是否过大

---

## 十一、最常见的坑

**坑一：没有 `-vvv` 日志就开始猜。**
「密码没错」是主观判断。`ssh -vvv` 会明确告诉你尝试了几个密钥、服务端接受了哪些认证方式、失败在哪一步。**没有日志的排查基本是蒙。**

**坑二：客户端密钥过多，把正确密钥挤掉了。**
本地 agent 或 `~/.ssh/id_*` 里密钥一多，就会先耗尽服务端的 `MaxAuthTries`，真正的正确密钥根本没机会被试，于是报 `Permission denied`——看起来像凭据错了，**实际是尝试次数耗尽**。加 `IdentitiesOnly=yes -i <指定密钥>` 即可。这类问题非常隐蔽，因为它在不同机器上表现不一致。

**坑三：sshd_config 键名拼错，静默失效。**
sshd 对无法识别的配置项**不报错**，直接用默认值。改完必须 `sshd -T` 看**实际生效值**，而不是看配置文件写了什么。

**坑四：Match 块之后的全局配置不再生效。**
`Match` 一旦出现，后续配置项只在该 Match 上下文中生效。而且本地 `sshd -T` 不带 `-C` 看到的是默认上下文的值，可能与实际不同。**必须用 `sshd -T -C user=<用户>,addr=<客户端IP>` 验证。**

**坑五：把 MaxStartups 调大来「解决」连接被拒。**
未认证连接过多时调大 MaxStartups，爆破流量也一起进来，未认证连接会消耗内存与文件句柄。**必须同时封禁来源**，否则只是把拒绝推迟了。

**坑六：sshd 配置改坏后 reload 失败，把自己锁在外面。**
经典事故。正确顺序：先 `sshd -t` 验证语法 → 确认有其他登录入口 → 保留当前会话不要退出 → 再 reload。

**坑七：磁盘满了还在改 sshd 配置。**
磁盘/inode 100% 时 sshd 可能无法写入登录记录，登录会卡死或失败。**先清空间**，改配置不解决问题。

**坑八：发现自己被 fail2ban 封了就停掉 fail2ban。**
等于放弃防护，而且影响整网。正确做法是 `fail2ban-client set sshd unbanip <你的IP>`。注意同一出口 IP 的同事可能一起被封。

**坑九：Host key 变更就直接忽略。**
`Host key verification failed` 时盲目 `StrictHostKeyChecking no` 会掩盖中间人攻击。正确做法是**先核实服务端是否确实重装或变更过密钥**，确认后再清理 `known_hosts` 对应条目。

**坑十：把「服务端日志无记录」当作「没发生」。**
服务端日志是轮转的，也可能被日志级别配置过滤了。查不到记录不代表事件没发生，要结合 `journalctl` 的时间范围与 `LogLevel` 配置判断。

**坑十一：只调大 `ClientAliveInterval` 治被踢下线。**
如果根因是 shell 启动脚本慢或 `.bashrc` 里有网络请求，调这个参数不解决问题，还会延迟真正的故障暴露。

**坑十二：在只有 SSH 一个入口的机器上做认证配置变更。**
没有回滚路径。必须先建立其他入口（云控制台 VNC 最常见），再动配置。

---

## 十二、边界与免责

- 本技能给出的是**定位路径与日志判读口径**，不代替现场登录解锁操作与配置变更审批
- **在只有 SSH 一个入口的服务器上修改认证配置属于高风险操作**，必须先建立其他登录入口
- 涉及**生产服务器认证配置变更**必须走变更流程，`sshd -t` 验证 + 保留回滚路径 + 保留当前会话
- 重置账号密码、调整账号锁定状态、修改防爆破策略需**经授权并留记录**
- 遇到疑似暴力破解或攻击流量，**转安全事件处理**，不要为了让自己登录而关闭防护
- 调整内核与 sshd 的资源限制参数需评估对整机的影响
- 本技能不提供任何绕过认证的方法，也不建议为兼容老旧客户端长期放开弱算法

---

## 十三、许可

本技能由 **刘天宝｜墨燊** 原创，采用 **Apache License 2.0**。

`rules/ssh_login_rules.md` 中的默认值整理自通用实践，不同发行版与 sshd 版本的默认值会有差异，落地前请以现场 `sshd -T` 的实际输出为准。