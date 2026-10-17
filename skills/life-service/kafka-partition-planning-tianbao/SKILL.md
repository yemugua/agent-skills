---
name: kafka-partition-planning
slug: kafka-partition-planning-tianbao
displayName: Kafka 分区数规划与吞吐量估算
display_name: "Kafka 分区数规划与吞吐量估算"
display_name_en: "Kafka Partition Count Planning and Throughput Estimation"
version: "1.0.0"
summary: 用「目标吞吐 ÷ 单分区吞吐」算出分区数，再校验消费者并发、单分区体积、文件句柄、故障恢复耗时四道门槛：含各环境单分区吞吐基准表（acks=all 与云盘下的保守值）、冷热倍的冗余系数取值、消费侧决定分区数的典型算例、消费者数超过分区数即空转的判定、单分区超过 50-100GB 必须拆分段的口径，以及扩容分区导致 hash(key)%n 重分布、同 key 顺序被打断的完整应对（预留倍数 vs 新 topic 双写迁移），配脚本按 topic 输出可落地的分区建议并扫描 rf、min.insync.replicas、unclean 选举等高危组合。
description: 要给 Kafka topic 定分区数、估算能扛多少吞吐、纠结是否扩分区、担心 key 乱序或 broker 恢复慢时使用。当用户说"分区数怎么定""多少个分区合适""分区是不是越多越好""目标 100MB/s 要几个分区""消费者加到 12 个为什么吞吐没涨""分区扩容会不会打乱顺序""分区多了为什么重启恢复很慢""Too many open files 是不是分区太多"时使用。内置三侧估算公式（生产侧 / 消费侧 / 消费者并发取最大值并对齐 broker 倍数）、五种环境的单分区吞吐基准、分区过多在文件句柄与 leader 选举上的量化代价、保留数据量与单分区体积换算、key 重分布风险与三种应对方案，配 scripts/kafka_partition_calc.py 计算建议分区数并解析 kafka-topics --describe 输出做配置体检。适用于后端研发、消息中间件运维与数据平台工程师。
license: Apache-2.0
author: 刘天宝｜墨燊
category: dev-programming
subCategories:
  - dev-data-storage
icon: icon.svg
tags: [Kafka, 分区数, 吞吐量估算, 消息有序性, 消费者组, rebalance, 分区扩容, min.insync.replicas, 消息中间件调优, 性能规划]
language: zh-CN
visibility: public
---

# Kafka 分区数规划与吞吐量估算（kafka-partition-planning）

分区数是 Kafka **唯一无法缩减的架构决策**：加会有 key 重分布问题，删则没有 API。

这个技能做三件事：**算分区数** → **验四道门槛** → **判扩容风险**。

---

## 硬边界（先看这条）

| 能做 | 不能做 |
|---|---|
| 按目标吞吐给出分区数建议区间 | ❌ 预测你这套环境的真实吞吐（必须本机压测） |
| 量化文件句柄、选举耗时、单分区体积 | ❌ 直接在线执行扩分区命令 |
| 判定消费者是否被分区数卡住 | ❌ 承担扩容导致的顺序性风险 |
| 给出 key 重分布的应对路径 | ❌ 计算 GC、页缓存、ISR 抖动等内核级细节 |

**以下情况必须停下来先做人工确认：**
- topic 有业务 key 且下游有状态 → 扩分区前必须走新 topic 双写迁移
- 单 broker 含副本分区数已超 4000 → 先扩 broker，不是再算分区
- 打算在线改 `unclean.leader.election.enable` → 走变更评审

---

## 一、什么时候用这个技能

| 用户这样说 | 就用 |
|---|---|
| "这个 topic 该设多少分区" | ✅ |
| "分区是不是越多越好" | ✅ |
| "目标 100 MB/s 需要几个分区" | ✅ |
| "消费者加到 12 个为什么吞吐没变化" | ✅ |
| "扩分区会不会导致消息乱序" | ✅ |
| "broker 重启后为什么 leader 恢复这么慢" | ✅ |
| "Too many open files 是不是分区太多" | ✅ |
| "帮我在生产集群直接执行扩容" | ❌ 只出方案，走变更流程 |

---

## 二、完整工作流

```
第 1 步  读规则文件 rules/partition_sizing.md（所有公式与门槛值在这）
第 2 步  实测单分区吞吐（不能跳过）
         kafka-producer-perf-test.sh / kafka-consumer-perf-test.sh
第 3 步  跑脚本算建议值
         python scripts/kafka_partition_calc.py --target-mbps 120 \
             --prod-per-partition 10 --cons-per-partition 5 \
             --consumers 8 --brokers 3 --rf 3 --growth 1.5 --retention-hours 168
第 4 步  用脚本体检现有 topic
         kafka-topics.sh --describe > topics.txt
         python scripts/kafka_partition_calc.py --file topics.txt --consumers-file groups.txt
第 5 步  过四道门槛：单分区体积 / 单 broker 分区数 / 故障恢复耗时 / 消费者并发
第 6 步  若建议值大于现有分区数 → 按 rules 第七节判定走「预留倍数」还是「双写迁移」
第 7 步  变更后观察 LAG 与 p99 延迟一个完整业务周期
```

---

## 三、三侧公式：取最大值，对齐 broker 倍数

```
P_prod = ceil(目标生产吞吐 × 冗余系数 / 单分区生产吞吐)
P_cons = ceil(目标消费吞吐 × 冗余系数 / 单分区消费吞吐)
P_user = 消费组峰值并发消费者数
P      = max(P_prod, P_cons, P_user)  向上取整到 broker 数的整数倍
```

**目标吞吐要取峰值**，不是日均值。冗余系数常年稳定取 1.3，有明显大促取 2.0，**不建议超过 3.0**。

典型算例（消费侧决定分区数）：

```
生产 120 MB/s，单分区生产 10 MB/s，冗余 1.5 → 18
消费 200 MB/s，单分区消费 5 MB/s，冗余 1.5  → 60   ← 决定值
消费者并发 8                                   → 8
broker 3 台 → max(18, 60, 8) = 60，已是 3 的倍数 → 建议 60
```

**消费者数超过分区数就一定有人空转。** 扩容消费者前先看 `kafka-consumer-groups.sh --describe` 的 `CONSUMER-ID` 列：有成员分不到分区，说明瓶颈在分区数。

完整的单分区吞吐基准表（含 `acks=all` 与云盘下的保守值）在 `rules/partition_sizing.md` 第二节，**这些数是量级估算，必须压测替换**。

---

## 四、四道门槛（算完必须验）

| # | 门槛 | 口径 | 超了怎么办 |
|---|---|---|---|
| 1 | 单分区体积 | 写入速率 × 3600 × 保留小时 / 1024，**建议 ≤ 50-100 GB** | 加分区，或缩短保留时间 |
| 2 | 单 broker 分区数（含副本） | `分区数 × rf / broker数`，**建议 ≤ 4000** | 扩 broker |
| 3 | 故障恢复 | 单个 broker 宕机需重选的 leader 数 ≈ `分区数 × rf / broker数`，超过约 2000-4000 个时恢复从秒级退化到分钟级 | 减少分区，或启用 KRaft 并实测恢复时间 |
| 4 | 文件句柄 | 每分区每副本活动 segment 约 3 个 fd；`ulimit -n` 建议 ≥ 100000 | 提高句柄上限；控制分区数 |
| 5 | 生产者攒批 | 单 producer 管理 > 1000 分区时 batch 被摊薄，`buffer.memory` 易耗尽 | 减少单 producer 的 topic 数；调大 `batch.size` / `linger.ms` |

---

## 五、扩容分区：key 重分布风险

默认分区器是 `hash(key) % 分区数`。**分区数一变，同一个 key 就换分区。**

| 影响面 | 损害 |
|---|---|
| 顺序性 | 同 key 的消息在跃迁期乱序 |
| 幂等去重 | 依赖「同 key 同分区」的逻辑失效 |
| 有状态计算 | Kafka Streams / Flink 键控状态错配 |
| 消费侧按分区缓存 | 本地聚合结果错误 |

**三条应对路径（详见 `rules/partition_sizing.md` 第七节）：**

- **A 预留倍数**：新建 topic 时直接按建议值 × 2~3 倍，前提是单 broker 分区数不超门槛
- **B 双写迁移**：已有 key 语义或下游有状态时的**唯一安全做法**，新 topic + 双写 + 逐步切流
- **C 裸扩**：仅限无 key、可接受跃迁期乱序的场景

> 分区数永远不能减，也不需要"扩容后自动搬历史数据"的幻想——历史数据会留在旧分区，新旧分布长期不均。

---

## 六、脚本用法

```bash
# 模式一：估算建议分区数
python scripts/kafka_partition_calc.py --selftest
python scripts/kafka_partition_calc.py --target-mbps 120 --cons-mbps 200 \
    --prod-per-partition 10 --cons-per-partition 5 \
    --consumers 8 --brokers 3 --rf 3 --growth 1.5 --retention-hours 168

# 模式二：体检现有 topic（kafka-topics --describe 输出）
kafka-topics.sh --bootstrap-server localhost:9092 --describe > topics.txt
python scripts/kafka_partition_calc.py --file topics.txt --consumers-file groups.txt --ulimit 65536
```

| 参数 | 说明 |
|---|---|
| `--target-mbps` / `--cons-mbps` | 目标生产 / 消费吞吐（MB/s），省略消费侧则与生产相同 |
| `--prod-per-partition` / `--cons-per-partition` | 单分区生产 / 消费吞吐（MB/s），**建议填实测值** |
| `--consumers` | 消费组峰值消费者数，用于校验是否被分区数卡住 |
| `--brokers` / `--rf` | broker 数与副本因子，用于均匀分布与体积换算 |
| `--growth` | 冗余系数，默认 1.5 |
| `--retention-hours` | 保留小时数，用于算单分区体积 |
| `--seg-gb` | segment 大小（GB），默认 1，用于算文件数 |
| `--file` | `kafka-topics --describe` 输出，进入体检模式 |
| `--consumers-file` | topic 到消费者数的映射文件：`orders=8` 每行一条 |
| `--ulimit` | 单 broker 文件句柄上限，用于 fd 风险判定 |
| `--election-ms` | 单个分区重选耗时（毫秒），默认 2，用于估算恢复时间 |
| `--json` / `--out` | JSON 输出 / 指定输出文件 |
| `--selftest` | 跑内置自检 |

脚本输出五段：**建议分区数**（三侧取最大并对齐 broker 倍数）、**单分区体积**、**文件句柄与文件数**、**故障恢复耗时**、**配置体检**（消费者被卡、`min.insync.replicas` 过严、`unclean` 选举开启、单 broker 分区超限等）。

> 体检结论基于静态配置，**不等于真实健康状态**。恢复时间、fd 占用以实际监控为准。

---

## 七、人工确认清单（这步不能省）

- [ ] 单分区吞吐是**本机压测值**还是网上的数
- [ ] 目标吞吐取的是**峰值**还是日均
- [ ] 这个 topic 有没有业务 key；有 key 的话下游有没有状态
- [ ] 扩完后单 broker 含副本分区数是否 ≤ 4000
- [ ] 单分区保留体积是否 ≤ 100 GB
- [ ] 消费组峰值消费者数是否 ≤ 分区数
- [ ] `acks` 与 `min.insync.replicas` 的组合是否留了容错余量
- [ ] 有没有在预发跑过一次 broker 重启恢复演练

---

## 八、最常见的坑

**坑一：拿网上抄的吞吐当自己的基准。**
别人的 20 MB/s 是 `acks=1` + 本地 NVMe。换成 `acks=all` + 跨可用区云盘，单分区可能只剩 3 MB/s。**估算前必须跑一次 `kafka-producer-perf-test`。**

**坑二：用平均吞吐算分区数。**
日均 10 MB/s，大促峰值 80 MB/s。按日均算出来的分区数在峰值时会积压。**必须取峰值或用分位数。**

**坑三：盲目加消费者。**
12 个分区加到 16 个消费者，4 个永远空转，而且每次 rebalance 白白重分配。扩容前看 `CONSUMER-ID` 列：**有成员没分到分区，说明该加分区而不是加消费者。**

**坑四：以为分区越多吞吐越高。**
分区到一定数量后，producer 的 batch 被摊薄，`linger.ms` 到期就发小包，小包占比上升、p99 反而变差；同时 `buffer.memory`（默认 32MB）分给上千个分区，容易触发 `buffer pool is exhausted`。

**坑五：有 key 的 topic 直接扩分区。**
`hash(key) % 12` 变成 `hash(key) % 16`，同一个用户的消息跳到别的分区，**同 key 顺序保证在跃迁期内被打断**。下游若依赖这个顺序（如对同一订单的创建/支付消息做时序处理），直接出错。有 key 就必须走双写迁移。

**坑六：`min.insync.replicas` 设成等于 `rf`。**
`rf=3` 配 `min.insync.replicas=3` + `acks=all`：任何一个副本抖动，整个 topic 立刻不可写。正确是 `min.insync.replicas=2`，容忍 1 个副本掉线。

**坑七：开了 `unclean.leader.election.enable=true` 还以为数据没丢。**
允许不同步的副本成为 leader，就是用可用性换数据安全性。它对延迟确实友好，但**恢复时静默丢掉那段没同步的数据**。

**坑八：只看 `retention.ms`，忘了 `retention.bytes`。**
两个同时配时**谁先触发谁生效**。配了 `retention.bytes` 却以为保留 7 天，实际可能 1 天就把数据删了。

**坑九：把小 topic 划成很多分区。**
几十 MB/s 的 topic 划 200 个分区，产生几万个小文件吃满 inode，还对 leader 选举毫无帮助。**分区数要有下限（≥ broker 数），更要有上限。**

---

## 九、边界与免责

- 本技能给出的是**估算与静态体检**，不代表线上的真实吞吐与恢复能力
- 所有单分区吞吐基准受硬件、`acks`、`compression`、`linger/batch` 参数、JVM 与页缓存共同影响，**以本机压测为准**
- 分区扩容属于不可逆操作且伴随 key 重分布风险，**必须走变更评审，先在预发验证并准备回滚方案**
- Kafka 版本差异明显：KRaft 取代 ZooKeeper 后，元数据上限与选主行为都不同，**操作前确认版本**

---

## 十、许可

本技能由 **刘天宝｜墨燊** 原创，采用 **Apache License 2.0**。

`rules/partition_sizing.md` 中的吞吐基准与阈值来自 Kafka 官方运维实践与常见硬件经验，不同版本（尤其是 KRaft 模式）与不同云厂商盘型存在差异，请以官方文档与实际压测结果为准。
