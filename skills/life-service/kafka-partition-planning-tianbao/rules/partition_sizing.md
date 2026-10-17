# Kafka 分区数规划 · 核心规则库

> 生成任何分区方案前，**先读本文件**，不要凭印象给数字。
> 所有吞吐基准都是**经验值**，只能用来估算，**定稿前必须用本机环境实测替换**。

---

## 一、分区的作用（决定了所有取舍）

| 作用 | 结论 |
|---|---|
| 提高并行度 | 一个分区在同一时刻只能被同组**一个消费者**占有 |
| 水平扩展 | 分区是 Kafka **唯一的并行单位** |
| 顺序保证 | Kafka **只保证分区内有序**，跨分区无序 |
| 存储分散 | 分区分布在不同 broker，受单机磁盘限制 |

由此直接推出三条硬约束：

1. **消费者数 ≤ 分区数**，多出来的消费者拿不到分区，永远空转。
2. **想要全局有序，只能一个分区**（或靠业务 key 收敛到同key同分区）。
3. **分区数可以加，不能减**（没有删除分区的 API）。

---

## 二、单分区吞吐基准表（估算用，必须实测校准）

| 环境 / 配置 | 单分区生产上限 | 单分区消费上限 | 备注 |
|---|---|---|---|
| 本地 NVMe，`acks=1`，开启压缩 | 10-20 MB/s | 10-20 MB/s | 常见乐观基准 |
| 本地 SSD，`acks=all`，`rf=3` | 5-10 MB/s | 8-15 MB/s | 副本同步拖慢写入 |
| 云盘（gp3 / EBS / SSD 云盘） | 2-10 MB/s | 5-15 MB/s | 受网络带宽与 IOPS 限制 |
| 跨可用区复制 `rf=3` | 2-6 MB/s | 5-10 MB/s | 网络 RTT 放大延迟 |
| 消费者每消息有 DB 写入 | — | 0.5-3 MB/s | 消费处理逻辑才是瓶颈 |

**实测命令（必须做）：**

```bash
bin/kafka-producer-perf-test.sh --topic perf-test \
  --num-records 5000000 --record-size 1024 --throughput -1 \
  --producer-props bootstrap.servers=localhost:9092 acks=all compression.type=lz4 batch.size=65536 linger.ms=20

bin/kafka-consumer-perf-test.sh --topic perf-test \
  --broker-list localhost:9092 --messages 5000000 --threads 1
```

把 `--throughput -1`（不限速）跑出来的 MB/s **除以当时的分区数**，才是你这套环境的单分区吞吐。

> 消费侧基准必须用**一份真实的处理逻辑**测，用 `--threads 1` 空转测出来的数字没有意义。

---

## 三、分区数估算公式

```
P_prod = ceil( 目标生产吞吐(MB/s) × 冗余系数 / 单分区生产吞吐(MB/s) )
P_cons = ceil( 目标消费吞吐(MB/s) × 冗余系数 / 单分区消费吞吐(MB/s) )
P_user = 需要的最大消费者线程数（消费组的峰值并发）
P      = max(P_prod, P_cons, P_user) 向上取整到 broker 数的整数倍
```

| 变量 | 取值口径 |
|---|---|
| 目标吞吐 | **峰值**，不是均值。取业务高峰的 95 分位，别用日均 |
| 冗余系数 | 常年稳定 1.3；有明显大促/热点 2.0；**不建议超过 3.0**（过多分区有代价，见 §5） |
| 单分区吞吐 | §2 实测值；估算时取**环境**对应的保守值 |
| 向上取整到 broker 倍数 | 保证分区在 broker 间均匀分布，避免热点 |

算例：

```
目标生产峰值 120 MB/s，单分区生产 10 MB/s，冗余 1.5 → P_prod = ceil(180/10) = 18
目标消费峰值 200 MB/s，单分区消费 5 MB/s，冗余 1.5  → P_cons = ceil(300/5)  = 60
消费组峰值并发 8 个实例                              → P_user = 8
broker 3 台                                          → max(18,60,8)=60，60 已是 3 的倍数 → P = 60
```

**这里消费侧决定了分区数**：典型的「生产快、消费慢」场景，分区要按消费能力算。

---

## 四、消费者并发关系表

| 分区数 | 消费者数 | 结果 |
|---|---|---|
| 12 | 12 | 刚好一人一区，最佳 |
| 12 | 16 | **4 个消费者空闲**，且每次 rebalance 都要重分配，纯浪费 |
| 12 | 6 | 一人两区，可跑；再加到 12 才有提升 |
| 1 | 4 | 3 个空转；且这一个分区是全局瓶颈 |

扩容消费者之前**先看 `kafka-consumer-groups.sh` 的 LAG 和分区分配**，再决定要不要扩；消费者数超过分区数扩容毫无意义。

```bash
bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --describe --group order-consumer
# 看 LAG 列：持续为正且增长 → 真的消费不过来
# 看 CONSUMER-ID 列：有分配不到分区的成员 → 消费者数已经超过分区数
```

---

## 五、分区过多的代价（为什么不能「多留点」）

| 代价项 | 量化口径 | 触发边界 |
|---|---|---|
| 文件句柄 | 每个分区每副本 = 1 个活动 segment（`.log` + `.index` + `.timeindex` 约 3 个 fd），历史 segment 不常驻 | `ulimit -n` 建议 ≥ 100000；单 broker **含副本分区数 ≤ 4000** |
| 磁盘文件数 | `分区数 × rf × ceil(保留数据/segment.bytes) × 3` | 小 topic 大量分区会产生几万个小文件，inode 吃紧 |
| leader 选举 / 故障恢复 | 单 broker 宕机后需重新选主的分区数 ≈ `总分区数 × rf / broker 数` | 超过约 **2000-4000 个分区需重选** 时，恢复时间从秒级上升到分钟级 |
| 端到端延迟 | 分区越多，producer 端 batch 越分散，`linger.ms` 到期时更容易攒不满一批 → 小包变多，p99 上升 | 单 producer 管理 > 1000 分区时明显 |
| Producer batch 效率 | 每个分区独立攒批，`buffer.memory`（默认 32MB）被摊薄 | `max.block.ms` 超时报错常由此引起 |
| 元数据开销 | 分区数进入 metadata 与 consumer group 协调 | 集群分区总数参考上限：ZK 模式 ~10 万，KRaft 模式可更高但不建议超 |
| ZK/KRaft 元数据 | 分区状态变动引发 controller 压力 | 频繁扩缩topic会放大 |
| 内存 | 每分区都有一份leader 副本的内存索引与清理/同步状态（常驻几十 KB）；量大可观 |

**经验上限（不是硬限制，超过就要有理由）：**

| 维度 | 建议上限 |
|---|---|
| 单 broker 分区数（含副本） | 4000 |
| 单 topic 分区数 | 200（再多先看是不是业务拆分不对） |
| 集群总分区数 | KRaft 20 万；ZK 10 万 |
| 每topic broker 比例 | 分区数 ≥ broker 数，否则不均衡 |

---

## 六、保留数据量与单分区体积

```
单分区保留数据量(GB) = 该分区写入速率(MB/s) × 3600 × 保留小时数 / 1024
                       （副本占用再 × rf，分布在 rf 台机器上）
```

| 写入速率 | 保留 24h | 保留 168h（7 天） | 保留 720h（30 天） |
|---|---|---|---|
| 0.5 MB/s | 42 GB | 295 GB | 1266 GB |
| 1 MB/s | 84 GB | 590 GB | 2531 GB |
| 5 MB/s | 422 GB | 2953 GB | 12656 GB |

**单分区建议控制在 50-100 GB 以内**：超过这个值，副本追平、分区迁移、日志清理、故障恢复的时间都会显著变长。

当「按吞吐算出来的分区数」导致单分区体积过大时，说明你需要**更多分区**；当导致分区数过多时，说明需要**缩短保留时间**或**减少副本**。两者冲突时优先缩短保留时间。

相关配置：

```properties
retention.ms=604800000        # 7 天
retention.bytes=-1            # -1 表示不限制；与 retention.ms 同时配置时，谁先触发谁生效
segment.bytes=1073741824      # 1GB；小而多的 segment = 更多文件
segment.ms=604800000
cleanup.policy=delete         # compact 用于 __consumer_offsets 与 KTable
```

---

## 七、扩容分区的风险（最容易被忽略）

### 1. key 重分布 —— 必须提前说清楚

默认分区器：`partition = hash(key) % numPartitions`（非 key 消息走粘性分区策略）。

分区数从 **12 → 16** 后：

```
hash("user-123") % 12 = 5
hash("user-123") % 16 = 11     # 同一个 key 跑到别的分区去了
```

后果：

| 影响面 | 具体损害 |
|---|---|
| 顺序性 | **同 key 的顺序保证被打断**，跃迁期间乱序 |
| 幂等 / 去重 | 依赖「同 key 同分区」的去重逻辑失效 |
| 有状态计算 | Kafka Streams、Flink 键控状态的算子迁移到错误实例，状态错配 |
| 消费侧本地缓存 | 按 partition 做本地聚合/缓存的下游会得到错误结果 |

### 2. 无法缩容、无法迁移部分数据

- 分区只能加不能删
- 加分区**不会**自动搬运历史数据，历史数据仍留在旧分区，新旧分区的数据分布长期不均匀

### 3. 安全做法（二选一）

**做法 A：一开始就多留（推荐）**

```
首次定分区时直接取「按峰值算出来的值 × 2 ~ 3 倍」，
但要核算 §5 的代价（文件句柄、选举耗时、端到端延迟）。
```

代价可控的前提：单 broker 含副本分区数仍在建议上限内。

**做法 B：新 topic + 双写迁移（已有 key 语义的场景必须用这个）**

```
1. 建新 topic：orders-v2，分区数按需
2. 生产者双写 v1 + v2（或写 v1，用 MirrorMaker / Connect 复制）
3. 消费者切到 v2，但**先只消费验证，不断流**
4. 逐 ADD migration：先迁无状态消费，再迁有状态
5. 观察旧 topic 无生产、无 lag 后停止双写，下线 v1
```

**做法 C（仅限不需要保证 key 顺序的场景）**：直接扩，接受跃迁期乱序，并在下游做去重/乱序容忍。

### 4. 扩容前必须确认的三件事

- [ ] 这个 topic 有没有 key？有 key → 走做法 B
- [ ] 下游有没有依赖分区分配的状态（RocksDB、本地缓存、KStream/Flink state）？有 → 走做法 B
- [ ] 扩完之后单 broker 分区数是否超 4000？超 → 先扩 broker

---

## 八、副本相关配置（分区数的乘数）

```properties
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2
default.replication.factor=3
min.insync.replicas=2           # 与 acks=all 配合才有意义
unclean.leader.election.enable=false
```

| 配置组合 | 判定 |
|---|---|
| `acks=all` + `min.insync.replicas=2` + `rf=3` | 标准可靠配置，容忍 1 副本掉线 |
| `acks=all` + `min.insync.replicas=rf` | **任一副本抖动就不可写**，可用性差 |
| `min.insync.replicas=1` | 等价于放弃 ack=all 的意义 |
| `unclean.leader.election.enable=true` | **可能丢数据**（允许不同步副本成为 leader） |

---

## 九、常见场景分区策略速查

| 场景 | 建议分区策略 |
|---|---|
| 顺序无关日志收集 | 分区数 = max(P_prod, broker数×2)，key=null 走轮询/粘性 |
| 订单/交易（需同 key 有序） | 按 user_id 或 order_id 作 key；分区数预留 2-3 倍，**永不扩容** |
| 高扇出广播（多个互不相干的消费组） | 分区数取决于**最大那个消费组**的并发需求 |
| 严格全局有序 | 1 个分区（吞吐上限即单分区上限，这是代价） |
| 消费侧有 DB 写入瓶颈 | 分区数主要由消费侧决定，先解决 DB 瓶颈再增分区 |
| 峰值/低谷差异巨大 | 冗余系数取 2.0，并评估是否用 Serverless/HPA 消费 |

---

## 十、判定口径备忘

- 「分区数不够」的信号：LAG 持续增长 + 消费者数已达分区数
- 「分区数过多」的信号：`libs/kafka` 报错 `Too many open files`；broker 重启后 leader 恢复慢；producer 报 `buffer pool is exhausted`；p99 延迟随分区数线性上涨
- 任何静态估算都建立在「单分区吞吐基准正确」这一前提上，**这个前提只能靠压测证实**
