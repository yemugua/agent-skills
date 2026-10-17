# Redis 持久化选型规则库（RDB / AOF / 混合）

## 1. 三种模式的核心差异：丢多少、多久恢复

| 模式 | 配置 | 数据丢失窗口 | 恢复速度 | 文件体积 |
|---|---|---|---|---|
| **RDB** | `save 900 1` 等时间点快照 | 最后一次快照到故障之间的**全部写入**（可能是 15 分钟） | 快（二进制直接载入） | 小 |
| **AOF always** | `appendonly yes` + `appendfsync always` | 理论 0，实际最多丢正在写入的**一个事件循环**的命令 | 慢（重放所有命令） | 大 |
| **AOF everysec** | `appendfsync everysec`（默认） | **约 1 秒**的写入（极端情况 2 秒） | 慢 | 大 |
| **AOF no** | `appendfsync no` | 由 OS 决定，通常 **30 秒** | 慢 | 大 |
| **混合持久化** | `appendonly yes` + `aof-use-rdb-preamble yes`（4.0+） | 同 everysec / always（取决于 appendfsync） | **快**（主体是 RDB 格式，只有增量是命令） | 中等 |
| **全关** | `save ""` + `appendonly no` | 进程退出即全丢 | 无 | 无 |

> **混合持久化是当前默认推荐**：AOF 重写时把 Rewrite 那一刻的内存数据以 RDB 格式写在 AOF 文件头部，之后的增量命令仍以 AOF 格式追加，兼顾恢复速度与安全。

---

## 2. 选型决策表

| 使用场景 | 推荐配置 | 理由 |
|---|---|---|
| **纯缓存**，后端有数据源，丢了只是击穿 | 关持久化（`save ""` + `appendonly no`）或 `save 3600 1` | 省掉 fork 开销与磁盘 IO；注意主从不都关（见 §5 事故） |
| **缓存但要保预热**，丢几分钟可接受 | 混合持久化 + `everysec`，或只开 RDB `save 900 1` | 重启后能较快恢复热点数据 |
| **分布式锁、幂等键、限流计数** | 混合持久化 + `everysec` + 至少一个副本 | 允许最多 1 秒误差，但不允许整体丢 |
| **轻量可靠存储**（任务队列、去重集合） | 混合持久化 + `always` + **副本开启持久化** + 定期离线备份 | always 每次写都 fsync，吞吐约降到 everysec 的 1/3 到 1/10，要有心理预期 |
| **大内存（>16GB）且要求快速恢复** | RDB 为主（较短间隔）+ AOF 混合 | fork 成本随内存线性上升，太密的 RDB 会让 latency 抖动 |
| **对 fork 极其敏感**（超低延迟场景） | 关 RDB，只用 AOF everysec，并在从节点做 RDB | 避免定期 fork 造成的 COW 抖动 |

---

## 3. AOF 的写入与重写（必须搞清的三件事）

### 3.1 appendfsync 三档的真实含义

| 值 | 行为 | 丢数据风险 | 吞吐 |
|---|---|---|---|
| `always` | 每个事件循环都 fsync | 最小（仅丢当前正在处理的命令） | 最低 |
| `everysec` | 后台线程每秒 fsync | **丢 1 秒**（fsync 落后时会丢 2 秒） | 高 |
| `no` | 交给操作系统刷盘，通常 30 秒 | 最多丢 30 秒 | 最高 |

### 3.2 AOF 重写触发

```
auto-aof-rewrite-percentage 100   # 相比上次重写后体积增长 100% 触发
auto-aof-rewrite-min-size   64mb  # 且当前体积不小于 64MB
```

- `percentage` 设为 **0 = 关闭自动重写**（AOF 会一直膨胀）
- 重写期间新命令进 `aof_rewrite_buffer`，重写完成后追加到新文件
- **`no-appendfsync-on-rewrite` 的取舍**：
  - `yes`：重写期间主线程不做 fsync，**延迟更稳，但可能丢失重写期间的数据**
  - `no`：重写期间照常 fsync，**更安全，但可能出现延迟尖峰**
  - 要求不丢数据就选 `no`（默认），要求延迟平稳可选 `yes` 但要接受丢数窗口变大

### 3.3 AOF 损坏处理

```
aof-load-truncated yes    # AOF 尾部写入不完整时截断后启动，不然后拒绝启动
```

正常修复流程：

```bash
redis-check-aof --fix appendonlydir/appendonly.aof.1.incr.aof   # 7.x 多文件 AOF 指向实际文件
redis-check-rdb dump.rdb
```

---

## 4. fork 与内存：RDB 真正的成本

`BGSAVE` / `BGREWRITEAOF` 都要 fork 子进程：

| 关注点 | 口径 |
|---|---|
| fork 耗时 | 与页表大小相关，通常 10-100ms/GB；**实例越大约慢** |
| COW 峰值 | 理论可能接近 **2 倍内存**，实际取决于写入速率与 fork 耗时 |
| fork 失败 | `vm.overcommit_memory=0` 且内存吃紧时 fork 失败，**导致持久化静默停止** |
| 延迟抖动 | 开启 THP（Transparent Huge Page）会让 fork 与 COW 抖动加剧 |

必配项：

```bash
# redis.conf
stop-writes-on-bgsave-error no   # 见下方说明
rdbcompression yes
rdbchecksum yes

# 系统层
echo never > /sys/kernel/mm/transparent_hugepage/enabled
sysctl -w vm.overcommit_memory=1
```

> `stop-writes-on-bgsave-error` 默认是 `yes`：快照失败后**拒绝写入**。
> 很多人为了"不影响业务"改成 `no`，结果磁盘坏了、快照一直失败，业务完全不知情，直到重启才发现一个月没备份。**改成 no 必须配套告警**（监控 `rdb_last_bgsave_status`）。

---

## 5. 三个必看的健康指标

```bash
redis-cli INFO persistence | grep -E 'rdb_last_bgsave_status|aof_last_bgrewrite_status|aof_last_write_status|rdb_last_save_time|aof_rewrite_in_progress|rdb_bgsave_in_progress|aof_buffer_length|aof_delayed_fsync'
```

| 字段 | 期望 |
|---|---|
| `rdb_last_bgsave_status` | `ok` |
| `aof_last_bgrewrite_status` | `ok` |
| `aof_last_write_status` | `ok`（为 err 说明 AOF 写失败，通常是磁盘满） |
| `aof_delayed_fsync` | 持续增长说明 fsync 跟不上，磁盘 IO 有瓶颈 |
| `rdb_last_save_time` | 距当前时间不应远大于你的 save 间隔 |

Redis 7 走 multi-part AOF：`INFO persistence` 里还有 `aof_rewrite_in_progress`、`aof_last_cow_size` 等。

---

## 6. 主从场景的经典事故

**事故链路**：主节点没开持久化 + 配置了自动重启 → 主节点崩溃重启后内存为空 → 从节点向主节点同步 → **从节点数据被清空**。

规避措施：

| 措施 | 做法 |
|---|---|
| 主节点必须开持久化 | 至少 `appendonly yes`，哪怕只用 RDB |
| 关闭主节点自动重启 | 崩溃后由人工/哨兵决策，不要 systemd 直接拉起空实例 |
| 副本也要持久化 | 副本重启默认走全量同步，会短时间打满主库带宽 |
| 定期异地备份 RDB | cron 复制 `dump.rdb` 到对象存储，保留多天 |

---

## 7. 落地检查清单

```
[ ] 明确这个实例丢了数据最坏可以接受多少（0 / 1秒 / 15分钟 / 全丢）
[ ] 按 §2 选模式，写进配置管理（不要手工改 redis.conf 然后忘了）
[ ] INFO persistence 三个 status 全为 ok
[ ] 监控项至少包含：rdb_last_save_time 距今间隔、aof_last_write_status、bgsave 失败次数
[ ] vm.overcommit_memory=1、THP=never
[ ] 做过一次真实的恢复演练（拿备份文件起一个新实例，确认能起来、数据条数对得上）
[ ] 主从都在的配置 —— 确认从节点也开了持久化
```
