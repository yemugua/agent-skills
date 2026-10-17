---
name: server-daily-inspection
slug: server-daily-inspection-tianbao
displayName: 服务器日常巡检清单与阈值核查
display_name: "服务器日常巡检清单与阈值核查"
display_name_en: "Server Daily Inspection Checklist and Threshold Review"
version: "1.0.0"
summary: 按 CPU / 内存 / 磁盘 / IO / 负载 / 时钟 / 日志 七类给出具体阈值与正常区间，逐项判定「正常 / 关注 / 告警」，输出带处置动作的巡检记录表与阈值速查表。
description: 服务器例行巡检不知道查什么、阈值定多少、看到高使用率该不该报警时使用。当用户说"帮我出一份服务器巡检清单""CPU 到了 80% 要不要告警""磁盘满了怎么排查""服务器巡检表怎么填""负载很高但 CPU 不高怎么回事""怎么判断服务器是不是健康""巡检要看哪些指标"时使用。内置 Linux 常用阈值表（CPU 单核与整体、load average 与核数比、内存与 swap、inode、磁盘 IO await、TCP 连接数、时钟偏移）、巡检命令速查、误判识别规则、巡检记录表模板，配 scripts/server_inspection_check.py 做阈值自动判定与巡检表生成。适用于系统管理员、运维工程师、云平台客户、SRE。本技能只做阈值判定与记录整理，不代替现场处置动作。
license: Apache-2.0
author: 刘天宝｜墨燊
category: it-ops-security
subCategories:
  - itops-monitoring
icon: icon.svg
tags: [服务器巡检, 运维, Linux, 性能监控, 阈值, CPU, 内存, 磁盘, 巡检表, SRE, 健康检查, 日常运维]
language: zh-CN
visibility: public
---

# 服务器日常巡检清单与阈值核查（server-daily-inspection）

服务器巡检最常见的两个失败：**只写「检查网络是否正常」这种没法执行的条目**，以及**阈值拍脑袋定 80%**，结果要么该报的没报、要么天天误报被无视。

这个技能做两件事：**给出可执行的巡检项与阈值** → **逐项判定等级并给出处置动作**。

---

## 硬边界（先看这条）

| 能做 | 不能做 |
|---|---|
| 给出每项的采集命令与判定阈值 | ❌ 代替你在机器上执行命令、改配置 |
| 判定「正常 / 关注 / 告警」三级 | ❌ 承诺「服务器一定没问题」 |
| 识别高使用率误判（负载高但 CPU 低等） | ❌ 自动做性能调优或重启决策 |
| 导出巡检记录表 | ❌ 代替监控告警系统的阈值配置 |
| 提示需转人工的场景 | ❌ 处理数据丢失、安全事件定性 |

**出现以下情况，先停下来人工处理，不要照着巡检流程往下走：**

- 磁盘使用率 ≥ 90%、inode 使用率 ≥ 85% —— 先定位大文件与删除目录，再谈清理
- 出现 `I/O error`、`EXT4-fs error`、`XFS metadata corruption` —— 可能是文件系统损坏，**先备份再操作，不要在线 fsck**
- `/var/log/messages` 出现 `kernel panic`、`Out of memory: Killed process` —— 需查 OOM 详情与触发进程
- 阵列降级、SMART 报 `Failed`、`Reallocated_Sector_Ct` 持续增长 —— 转硬件处理
- 检测到账号、远程接入策略、计划任务或开放端口与本单位台账不一致 —— 转安全事件流程，不要只填「已记录」
- 时钟偏移超过 120 秒 —— 先修 NTP 再做其他判断，否则日志时间线全部不可信

---

## 一、什么时候用这个技能

| 用户这样说 | 就用 |
|---|---|
| "帮我出一份服务器巡检清单" | ✅ |
| "CPU 80% 了要不要告警" | ✅ |
| "磁盘快满了怎么排查" | ✅ |
| "load average 很高但 CPU 很闲，是什么问题" | ✅ |
| "巡检表长什么样、怎么填" | ✅ |
| "服务器健康检查一般看哪些东西" | ✅ |
| "内存涨到 90% 正常吗" | ✅ |
| "帮我直接去服务器上查一下" | ❌ 需要现场权限 |

---

## 二、完整工作流

```
第 1 步  确认系统与角色：Linux/Windows、物理机/云主机、Web/DB/中间件
第 2 步  读规则文件 rules/inspection_thresholds.md，取对应角色的阈值
第 3 步  逐项执行采集命令（见 §4 命令速查），把结果写成 指标|数值 一行一条
第 4 步  跑脚本判定等级
         python scripts/server_inspection_check.py --file collect.txt --role web
第 5 步  按 §6 人工确认清单复核，特别是「采集失败 ≠ 正常」
第 6 步  填 templates/inspection_record.md，附处置动作与责任人
```

---

## 三、阈值速查（最常用的一张表）

Linux 单机通用阈值，具体角色的微调见规则文件 §2。

| 指标 | 正常 | 关注 | 告警 | 采集命令 |
|---|---|---|---|---|
| CPU 使用率（1 分钟均值） | < 70% | 70–85% | > 85% 持续 10 分钟 | `top -bn1 \| head -5` 的 `%id` |
| load average / 核数 | < 0.7 | 0.7–1.0 | > 1.0 且持续 | `cat /proc/loadavg` |
| 内存使用率（不含缓存） | < 75% | 75–88% | > 88% | `free -m` 的 `available` |
| swap 使用率 | 0% | > 0 但 < 30% | > 30% | `free -m` 的 `swap` |
| 磁盘分区使用率 | < 70% | 70–85% | > 85%（90% 必须处理） | `df -h` |
| inode 使用率 | < 60% | 60–80% | > 80% | `df -i` |
| 磁盘 IO await | < 10 ms | 10–30 ms | > 30 ms | `iostat -x 1 3` |
| 磁盘 %util | < 70% | 70–90% | > 90% 持续 | `iostat -x 1 3` |
| TCP ESTABLISHED 数 | < 5000 | 5000–10000 | > 10000 或接近 `somaxconn/ports` | `ss -s` |
| 系统时钟偏移 | < 30 秒 | 30–120 秒 | > 120 秒 | `timedatectl show -p NTPSynchronized` + 手工比对 |
| `/var/log` 近 1 天 ERROR 级条数 | < 20 | 20–100 | > 100 或出现致命关键字 | `journalctl -p err --since today \| wc -l` |

**判定规则（务必记牢）：**

1. **单点不判定，要看持续时间。** CPU 90% 持续 5 秒和持续 30 分钟完全不是一回事。
2. **load 高不等于 CPU 高。** load 含不可中断进程（D 状态）。`vmstat` 里 `b` 列持续 > 0 而 `us+sy` 很低 → **磁盘或网络 IO 阻塞**，不是 CPU 不足。
3. **`df -h` 说没满但报 No space left** → 几乎一定是 **inode 用尽**（小文件太多），看 `df -i`。
4. **内存使用率高不等于要加内存。** 看 `available` 而不是 `free`，Linux 用空闲内存做缓存是正常行为。
5. **采集失败 ≠ 正常。** 命令报错、权限不足、命令写错时必须记「采集失败」并补采，不能填 0。

---

## 四、巡检命令速查（可直接复制）

```bash
# 系统与运行时长
uptime ; uname -r ; cat /etc/redhat-release 2>/dev/null || cat /etc/os-release

# CPU
top -bn1 | head -5          # %us %sy %id
mpstat -P ALL 1 3           # 每核使用率（需 sysstat）
vmstat 1 5                  # r 列为运行队列，b 列为阻塞队列，wa 为 IO 等待

# 内存与 swap
free -m                    # 看 available 与 swap used，不要看 free
cat /proc/meminfo | egrep 'MemTotal|MemAvailable|SwapTotal|SwapFree'
smem -s swap -r             # 找出吃 swap 的进程（需安装）

# 磁盘
df -hT                     # 按类型看挂载与容量
df -i                      # inode，必查
du -xh --max-depth=1 /var 2>/dev/null | sort -h | tail -10
find /var -xdev -type f -size +500M -exec ls -lh {} \; 2>/dev/null

# 磁盘 IO
iostat -x 1 3              # await 与 %util 最重要
iotop -oPa                  # 哪个进程在读写（需安装）

# 网络与连接数
ss -s                      # 总连接数汇总
ss -tan state established | wc -l
cat /proc/sys/net/core/somaxconn /proc/sys/net/ipv4/ip_local_port_range

# 服务与日志
systemctl --failed --no-pager
journalctl -p err --since "-24h" | wc -l
journalctl -p err --since "-24h" --no-pager | tail -50
grep -iE 'oom|killed process|segfault|I/O error' /var/log/messages | tail -20

# 时钟与 NTP
timedatectl
chronyc tracking 2>/dev/null || ntpq -p 2>/dev/null
chronyc sources -v 2>/dev/null | head

# 连接与端口台账核对
ss -s                      # 连接数汇总（指标类，已在上方）
ss -lnt                    # 当前对外监听端口，与「开放端口台账」逐条比对
```

---

## 五、脚本用法

```bash
python scripts/server_inspection_check.py --file collect.txt --role web
```

| 参数 | 说明 |
|---|---|
| `--file` | 采集结果文件，每行 `指标名|数值`，支持 `#` 注释与空行 |
| `--role` | `web` / `db` / `middleware` / `batch` / `generic`，决定阈值微调 |
| `--cores` | CPU 核数（不填则读本机），load 比值按核数折算 |
| `--as-of` | 巡检日期 `YYYY-MM-DD` |
| `--json` / `--out` | JSON 输出 / 写入指定报告文件 |
| `--selftest` | 跑内置自检（≥ 8 条断言） |

脚本做四件事：① 按角色套用阈值判定每项等级；② 识别采集失败项（不静默当正常）；③ 识别组合型异常（load 高 CPU 低 / 磁盘满但 inode 满 / 内存高 swap 猛涨）；④ 输出可直接贴进巡检表的 Markdown。

> 阈值判定是**静态检查**：它不知道你这台机器的历史基线。同样的 60% 内存占用，对一台空闲的备份机正常，对一台跑满的数据库就是异常——**必须结合角色与基线**。

---

## 六、人工确认清单（这步不能省）

- [ ] 每项是真的采到了，还是「采集失败」被写成了 0
- [ ] CPU 高：是用户态（`us`）还是系统态（`sy`）？`sy` 高往往是中断/上下文切换风暴
- [ ] load 高时，`vmstat` 的 `b` 列是否为 0（区分 CPU 瓶颈与 IO 瓶颈）
- [ ] 内存高时看的是 `available` 还是 `free`
- [ ] 磁盘高时是否同时查了 `df -i`
- [ ] 「已处理」有没有写明**动作与验证方式**，而不是只写「已处理」
- [ ] 时钟是否已同步（未同步时的时间记录不具备证据效力）
- [ ] 合规项（特权账号 / 口令基线 / 远程接入 / 计划任务 / 开放端口）是否逐条对照过台账，而不是只打了勾

---

## 七、最常见的坑

**坑一：把阈值定成「都正常」，告警等于没有。**
每项都写「正常」，出了故障翻记录全是绿的。至少要有「关注」这一档能承接早期信号，并写清触发后的动作。

**坑二：`free` 显示内存用了 90% 就报内存不足。**
Linux 把空闲内存拿去做缓存，`free` 常年接近 0 是正常现象。看 `available`（估算真正还能分配的），它低才说明有压力。

**坑三：只查 `df -h`，inode 满了完全看不见。**
邮件、缓存、小文件服务最容易踩这个：容量还剩 40%，inode 已经 100%，写入直接失败，报错却是 `No space left on device`。**每次都要跑 `df -i`。**

**坑四：load average 高就加 CPU。**
`/proc/loadavg` 的第一个数统计的是**不可中断睡眠 + 运行中**的任务。磁盘慢、NFS 挂载卡、网络设备排队，都会把 load 顶高而 CPU 很闲。先看 `vmstat` 的 `b` 列：为 0 才是 CPU 瓶颈。

**坑五：采集命令报错当成「该项正常」。**
没权限、命令不存在、参数写错，输出为空 → 被填成 0 → 判定正常。脚本会把这类项标成「采集失败」，**必须补采后再判**。

**坑六：巡检记录写「已处理」但没有验证。**
最常见的假闭环。正确写法：「已清理 `/var/log/journal` 至 42%，复查 `df -h` 已降至 42%」——**动作 + 证据**缺一不可。

**坑七：不做基线，只看绝对值。**
同一台机器，凌晨 3 点的 30% CPU 是正常，早上 9 点的 30% 就是异常。绝对阈值只适合做兜底，**告警要基于同机同时段的基线**。

**坑八：合规项走过场。**
特权账号、口令基线、远程接入策略、计划任务、开放端口——这些要拿台账逐条对，不能在巡检表里勾个「无异常」。对不上就走安全事件流程，不要自己判断「应该没问题」。

---

## 八、边界与免责

- 本技能给出的是**阈值与判定口径**，不代替监控告警系统的实际配置，也不保证覆盖全部故障模式
- 阈值是通用起点，**不同机型、不同业务峰谷、容器共享宿主机**的场景必须按自身基线上调或下调，以现场压测与历史数据为准
- 涉及磁盘、阵列、文件系统告警时，**以厂商工具输出与现场处置规范为准**，不要凭本技能的命令清单自行做在线修复
- 巡检记录涉及审计合规要求时，**以现行规定和本单位审计要求为准**
- 任何涉及数据删除、格式化、服务重启的动作，必须经人工确认后执行

---

## 九、许可

本技能由 **刘天宝｜墨燊** 原创，采用 **Apache License 2.0**。

`rules/inspection_thresholds.md` 中的阈值为通用工程实践整理，机器规格与业务形态差异较大，落地前请用本机至少 7 天历史数据校准后再启用告警。