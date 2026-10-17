# Redis 持久化 RDB AOF 选型 · 能力概览

## 你会得到什么

**一个选型依据**：把「RDB 还是 AOF」这种问法换成「这个实例最坏能接受丢多少数据」。答案直接决定配置——能接受 15 分钟就只开 RDB，只能接受 1 秒就混合持久化 + everysec，要求一个都不能丢就 always（并接受吞吐下降到 everysec 的三分之一到十分之一）。

**一张丢数窗口对照表**：RDB 丢最后一次快照后的全部写入；AOF everysec 丢 1 秒（fsync 落后时 2 秒）；`appendfsync no` 丢由操作系统决定的约 30 秒；混合持久化（4.0+ 的 `aof-use-rdb-preamble`）用 RDB 头 + 增量命令，兼顾加载速度与安全，是当前默认推荐。

**两个容易被忽略的代价**：fork 与 COW。32GB 实例配 `save 60 10000` 意味着每分钟 fork 一次、每分钟抖一次；`vm.overcommit_memory=0` 且内存吃紧时 fork 会失败并让持久化静默停止，必须配 `vm.overcommit_memory=1` 并关闭 THP。

**三个必须做的取舍**：`no-appendfsync-on-rewrite` 的安全与延迟怎么选；`stop-writes-on-bgsave-error` 改成 no 之后为什么必须配套监控（否则备份可能失败一个月无人知晓）；`auto-aof-rewrite-percentage 0` 为什么等于让 AOF 无限膨胀。

**脚本**：`scripts/redis_persistence_check.py` 直接吃 `redis.conf` 或 `CONFIG GET` / `INFO persistence` 的输出，算出丢数窗口、评估 fork 风险、扫高危组合（fsync=no、重写被关、always 与 no-appendfsync 矛盾、主节点无持久化、副本未持久化），并检查 `INFO persistence` 里三个 status 字段是否健康。

## 典型用法

1. 新实例上线：先问业务"能丢多少"，再对照选型表落配置。
2. 存量集群巡检：批量导出 CONFIG GET + INFO persistence，批量跑脚本。
3. 事故复盘：主库崩了数据丢了，用脚本复现当时的配置组合，定位是不是「主无持久化 + 自动重启」链路。
4. 改配置前预演：在 staging 实例上先跑一遍，看有没有被脚本判为严重。

## 边界

- 静态配置体检不等于实际可靠性，唯一能证明备份可用的是恢复演练
- fork 耗时与 COW 峰值依赖机型、内核、内存与写入模式，以 latest_fork_usec 实测为准
- 生产 Redis 配置变更属高风险操作，必须走评审并先在从节点验证
- Redis 7 的 multi-part AOF 目录结构与旧版本差异较大，操作前确认版本
