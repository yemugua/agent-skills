---
name: redis-persistence-choose
slug: redis-persistence-choose-tianbao
displayName: Redis 持久化 RDB AOF 选型
display_name: "Redis 持久化 RDB AOF 选型"
display_name_en: "Redis Persistence RDB vs AOF Selection"
version: "1.0.0"
summary: 按「能接受丢多少数据」这一个问题的答案选持久化方案：RDB 丢最后一次快照后的全部写入、AOF everysec 丢 1 秒、always 每次 fsync、no 丢 30 秒、混合持久化兼顾恢复速度与安全；附丢数窗口测算表、fork/COW 风险评估、auto-aof-rewrite 与 no-appendfsync-on-rewrite 的取舍、INFO persistence 必看健康字段、主节点无持久化导致从库被清空的经典事故规避。
description: 要给 Redis 定持久化方案、不确定该用 RDB 还是 AOF、担心重启丢数据或 fork 抖动时使用。当用户说"Redis 该用 RDB 还是 AOF""持久化怎么配才不丢数据""everysec 到底丢多少""混合持久化要不要开""BGSAVE 失败为什么还能写入""主库崩了为什么从库数据也没了""fork 太慢导致延迟抖动怎么办"时使用。内置五种模式的丢数窗口对照、六类场景的推荐配置表、appendfsync 三档的真实语义与吞吐代价、AOF 重写触发条件与 no-appendfsync-on-rewrite 的安全取舍、fork 耗时与 COW 峰值内存口径、vm.overcommit 与 THP 的系统层必配项、stop-writes-on-bgsave-error 改成 no 后必须配套的监控、主从场景的清空事故链路与四条规避措施，配 scripts/redis_persistence_check.py 解析 redis.conf 与 INFO persistence 输出，输出丢数窗口、fork 风险与高危组合检查。
license: Apache-2.0
author: 刘天宝｜墨燊
category: it-ops-security
subCategories:
  - itops-middleware
icon: icon.svg
tags: [Redis, 持久化, RDB, AOF, 混合持久化, fork, 数据可靠性, 快照, appendfsync, 缓存架构]
language: zh-CN
visibility: public
---

# Redis 持久化 RDB AOF 选型（redis-persistence-choose）

持久化选型只需要回答一个问题：**这个实例丢了数据，最坏能接受多少？**
答案决定了配置：**0 → AOF always**；**1 秒 → 混合持久化 + everysec**；**15 分钟 → 只开 RDB**；**全丢也可以 → 关掉，前提是它不是主库**。

这个技能做三件事：**算丢数窗口** → **评 fork 风险** → **扫高危配置组合**。

---

## 硬边界（先看这条）

| 能做 | 不能做 |
|---|---|
| 按「允许丢多少」推荐持久化组合 | ❌ 替代真实的恢复演练（备份能不能起来只有演练能证明） |
| 测算丢数窗口与 fork/COW 风险 | ❌ 预测具体 fork 耗时（依赖机型、内存、写入速率） |
| 扫出高危配置组合（如 fsync=no、重写被关） | ❌ 直接修改线上实例的 redis.conf |
| 给出 INFO persistence 的监控字段 | ❌ 承担数据丢失的责任 |

**以下情况必须停下来，先做人工确认：**
- 主节点未开持久化 + 配置了自动重启 → **随时可能清空全部从节点**
- `aof_last_write_status` 不是 `ok` → 磁盘或 IO 已有故障
- 准备把实例的持久化从「有」改成「无」→ 必须先把现有备份复制走，再改配置

---

## 一、什么时候用这个技能

| 用户这样说 | 就用 |
|---|---|
| "Redis 该用 RDB 还是 AOF" | ✅ |
| "持久化怎么配最少丢数据" | ✅ |
| "everysec 到底会丢多少" | ✅ |
| "混合持久化要不要开" | ✅ |
| "BGSAVE 失败为什么还能写入" | ✅ |
| "主库崩了为什么从库数据也没了" | ✅ |
| "fork 导致延迟抖动怎么办" | ✅ |
| "帮我在线上直接改 redis.conf" | ❌ 走变更流程 |

---

## 二、完整工作流

```
第 1 步  读规则文件 rules/persistence_choice.md
第 2 步  明确回答：这个实例最坏能接受丢多少数据？
第 3 步  导出配置与状态
         redis-cli CONFIG GET '*' > redis.conf.txt
         redis-cli INFO persistence >> redis.conf.txt
第 4 步  跑体检脚本
         python scripts/redis_persistence_check.py --file redis.conf.txt \
             --role master --maxmemory-gb 16
第 5 步  按脚本的「丢数窗口 + fork 风险 + 配置检查」三段结论调整
第 6 步  做恢复演练：拿备份文件另起实例，确认能起来、数据条数对得上
第 7 步  补监控告警：rdb_last_bgsave_status / aof_last_write_status / 距上次快照间隔
```

---

## 三、丢数窗口对照表（选型的唯一依据）

| 模式 | 配置 | 丢失窗口 | 恢复速度 |
|---|---|---|---|
| RDB | `save 900 1` | 最后一次快照之后的**全部写入**（可达 15 分钟） | 快 |
| AOF always | `appendfsync always` | 理论 0，实际最多丢一个事件循环 | 慢 |
| **AOF everysec** | `appendfsync everysec`（默认） | **约 1 秒**（fsync 落后时 2 秒） | 慢 |
| AOF no | `appendfsync no` | 由 OS 决定，通常 **30 秒** | 慢 |
| **混合持久化** | `appendonly yes` + `aof-use-rdb-preamble yes` | 同所选 fsync 档位 | **快**（主体 RDB + 增量命令） |
| 全关 | `save ""` + `appendonly no` | 进程退出即全丢 | 无 |

**选型速查：**

| 场景 | 推荐 |
|---|---|
| 纯缓存，丢了最多造成缓存击穿 | 关持久化（**但主节点不要关，见 §6**）或 `save 3600 1` |
| 缓存要保预热 | 混合持久化 + everysec |
| 分布式锁 / 幂等键 / 限流计数 | 混合持久化 + everysec + 至少一个副本 |
| 轻量可靠存储（任务队列、去重集合） | 混合持久化 + **always** + 副本持久化 + 定期离线备份 |
| >16GB 且要求快速恢复 | RDB 为主 + AOF 混合 |

---

## 四、fork 与延迟抖动

`BGSAVE` / `BGREWRITEAOF` 都要 fork：

| 关注点 | 口径 |
|---|---|
| fork 耗时 | 通常 10-100ms/GB，实例越大约慢；看 `latest_fork_usec` |
| COW 峰值 | 理论可接近 **2 倍内存** |
| fork 失败 | `vm.overcommit_memory=0` 且内存吃紧时 fork 失败，**持久化静默停止** |
| 抖动加剧 | 开启 THP 会显著放大 fork 与 COW 抖动 |

系统层必配：

```bash
sysctl -w vm.overcommit_memory=1
echo never > /sys/kernel/mm/transparent_hugepage/enabled
```

---

## 五、三个必须做的取舍

1. **`no-appendfsync-on-rewrite`**：`yes` 延迟更稳但重写期间会丢数据；`no`（默认）更安全但可能延迟尖峰。要求不丢就选 `no`。
2. **`stop-writes-on-bgsave-error`**：默认 `yes`（快照失败拒绝写入）。改成 `no` 必须配套监控 `rdb_last_bgsave_status`，否则备份可能长期静默失败而你毫不知情。
3. **`auto-aof-rewrite-percentage`**：设为 `0` 等于关闭自动重写，AOF 会一直膨胀。

---

## 六、主从场景的经典事故

**链路**：主节点没开持久化 + 自动重启 → 主节点重启后内存为空 → 从节点向主节点同步 → **从节点数据被清空**。

四条规避：主节点至少开 AOF；关闭主节点自动重启；副本也要开持久化（否则重启动全量同步打满主库带宽）；定期把 RDB 复制到对象存储。

---

## 七、脚本用法

```bash
redis-cli CONFIG GET '*' > redis.txt
redis-cli INFO persistence >> redis.txt
python scripts/redis_persistence_check.py --file redis.txt --role master --maxmemory-gb 16
```

| 参数 | 说明 |
|---|---|
| `--file` | `redis.conf` 文本，或 `CONFIG GET` / `INFO persistence` 的输出 |
| `--role` | `master` / `slave` / `replica`，用于角色相关的风险判定 |
| `--maxmemory-gb` | 实例内存（GB），用于 fork 风险评估 |
| `--now` | 当前时间戳，配合 INFO 的 `rdb_last_save_time` 算距上次快照多久 |
| `--json` / `--out` | JSON 输出 / 指定输出文件 |
| `--selftest` | 跑内置自检 |

脚本输出四段：**丢数窗口**（含 `no-appendfsync-on-rewrite` 打开后的窗口放大提示）、**fork 风险**（按内存与快照间隔分级）、**配置检查**（严重/警示/提示/好）、**健康字段**（`rdb_last_bgsave_status` 不为 ok 时直接报严重）。

> 静态配置检查**不等于实际可靠性**。唯一能证明备份可用的是恢复演练。

---

## 八、人工确认清单（这步不能省）

- [ ] 业务侧确认过「最坏能丢多少」吗
- [ ] `INFO persistence` 三个 status 是否全为 `ok`
- [ ] `rdb_last_save_time` 距今不超过配置的 save 间隔
- [ ] `vm.overcommit_memory=1` 且 THP 已关闭
- [ ] `stop-writes-on-bgsave-error=no` 的实例有对应的告警吗
- [ ] 主从都开了持久化吗；主节点有没有配自动重启
- [ ] **做过一次真实恢复演练吗**（起新实例、验证数据条数）

---

## 九、最常见的坑

**坑一：开了 RDB 就以为万无一失。**
`save 900 1` 意味着最坏丢 15 分钟的全部写入。对金额、库存、幂等键来说完全不可接受。

**坑二：以为 everysec 只丢 1 秒，从不验证。**
fsync 落后时实际可能丢 2 秒。而且这个结论建立在磁盘 IO 正常的前提上——IO 打满时更长。

**坑三：为了不影响业务把 `stop-writes-on-bgsave-error` 改成 no。**
磁盘满了、权限错了，BGSAVE 一直失败，写入却照常进行。直到重启才发现一个月没备份过。**改 no 必须配套告警。**

**坑四：主节点无持久化 + systemd 自动重启。**
主库崩溃重启后是空实例，从库老老实实同步，把自己清空。**这是最经典的 Redis 数据全损事故链路。**

**坑五：`auto-aof-rewrite-percentage 0`。**
写 0 的人是想要"禁止自动重写以避免抖动"，结果是 AOF 无限膨胀直到磁盘写满。

**坑六：`always` + `no-appendfsync-on-rewrite yes`。**
自相矛盾：重写期间 fsync 暂停，此时已经不是 always 语义了，但你以为自己是最高安全档。

**坑七：忽略 fork 抖动。**
32GB 实例配 `save 60 10000`，写入密集时每分钟 fork 一次，每分钟抖一次。大内存实例应该放宽 RDB 间隔，改由 AOF 承担时效性。

**坑八：只备份不演练。**
备份文件的唯一意义是能恢复出来。定期把 RDB 拉到隔离环境起实例验证——这一步没人做，但它是唯一能证明备份可用的方法。

---

## 十、边界与免责

- 本技能给出的是**配置层面的静态体检与选型建议**，不构成对实际数据可靠性的承诺
- fork 耗时、COW 峰值受机型、内核版本、内存大小与写入模式共同影响，**以 `latest_fork_usec` 实测为准**
- 生产 Redis 的配置变更属于高风险操作，**必须走变更评审，先在从节点或非关键实例验证**
- Redis 7 的 multi-part AOF 目录结构与旧版本差异较大，**操作前确认版本**

---

## 十一、许可

本技能由 **刘天宝｜墨燊** 原创，采用 **Apache License 2.0**。

`rules/persistence_choice.md` 中的丢失窗口与阈值基于 Redis 官方行为与工程实践整理，不同版本（尤其是 Redis 7 的 multi-part AOF）存在差异，请以实际版本官方文档为准。
