# Kafka 分区数规划与吞吐量估算 · 能力概览

## 你会得到什么

**一个能落地的数字，不是"视情况而定"**。分区数由三侧取最大值决定：生产侧 `ceil(目标生产吞吐 × 冗余系数 / 单分区生产吞吐)`、消费侧同样算一遍、消费者并发侧的峰值线程数，最后向上取整到 broker 数的整数倍以保证均匀分布。附完整算例，说明为什么绝大多数业务的分区数其实是被**消费侧**决定的。

**单分区吞吐基准不是拍脑袋**。给出五种环境（本地 NVMe + acks=1、本地 SSD + acks=all 三副本、云盘、跨可用区、消费侧带 DB 写入）的保守量级，并明确要求用 `kafka-producer-perf-test.sh --throughput -1` 与 `kafka-consumer-perf-test.sh --threads 1` 在本环境实测替换。

**四道门槛防住"分区多多益善"**。算完必须验：单分区保留体积 ≤ 50-100 GB、单 broker 含副本分区数 ≤ 4000、单 broker 宕机需重选的 leader 数超 2000-4000 时恢复从秒级退化为分钟级、每分区每副本活动 segment 约 3 个 fd 且 `ulimit -n` 建议 ≥ 100000。还给出 producer 管理超 1000 分区时 batch 被摊薄、`buffer.memory` 耗尽的判定口径。

**扩容风险讲透**。默认分区器是 `hash(key) % 分区数`，分区数一变同 key 就换分区，直接导致同 key 顺序被打断、依赖同 key 同分区的幂等去重失效、Kafka Streams / Flink 键控状态错配。给出三条应对路径：预留倍数（新建时用）、新 topic 双写迁移（有 key 或有状态时的唯一安全做法）、裸扩（仅限无 key）。

**脚本**：`scripts/kafka_partition_calc.py` 两种模式——估算模式按三侧公式出建议分区数并校验四道门槛；体检模式解析 `kafka-topics --describe` 输出，检查消费者是否被分区数卡住、`min.insync.replicas` 是否过严、`unclean.leader.election.enable` 是否开启、单 broker 分区数是否超限。

## 典型用法

1. 新建 topic：先压测拿单分区吞吐，再跑脚本估算，最后过四道门槛。
2. 消费积压：看 `kafka-consumer-groups.sh --describe` 的 `CONSUMER-ID` 列，若已有成员没分到分区，说明要加分区而不是加消费者。
3. 老 topic 扩容：先看有没有业务 key 和下游状态，有就走双写迁移方案。
4. 集群巡检：把 `--describe` 输出存下来跑体检，一次性扫完所有 topic 的副本配置风险。

## 边界

- 给的是估算与静态体检，不代表线上真实吞吐与恢复能力
- 所有吞吐基准受硬件、acks、压缩、linger/batch、JVM 与页缓存共同影响，以本机压测为准
- 分区扩容不可逆且伴随 key 重分布，必须走变更评审
- KRaft 与 ZooKeeper 模式在元数据上限和选主行为上差异明显，操作前确认版本
