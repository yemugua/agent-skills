---
name: mysql-explain-analyze
slug: mysql-explain-analyze-tianbao
displayName: MySQL 执行计划 EXPLAIN 解读
display_name: "MySQL 执行计划 EXPLAIN 解读"
display_name_en: "MySQL EXPLAIN Execution Plan Analysis"
version: "1.0.0"
summary: 逐列讲清 EXPLAIN 的 12 个字段怎么看：type 从优到劣的完整排序与各自场景、用 key_len 反推实际用到第几列（含各类型字节数与可为 NULL 加 1）、rows × filtered 的真实含义、Extra 里 Using filesort / temporary / join buffer / index condition 的处置口径，配脚本直接解析 EXPLAIN 表格输出并分级诊断。
description: 拿到 EXPLAIN 结果不知道怎么读、看不出哪里有问题、key_len 算不出用了几列、Extra 里一堆英文名词不知道哪个要紧时使用。当用户说"EXPLAIN 怎么看""type=ALL 是不是很严重""key_len 怎么算出用了几个索引字段""Using filesort 要不要管""filtered 只有 10 是什么意思""为什么 possible_keys 有值但 key 是 NULL""EXPLAIN ANALYZE 和 EXPLAIN 有什么区别"时使用。内置 type 十二级优劣表与各类型含义、key_len 字节计算表（INT 4 / BIGINT 8 / DATETIME 5 / VARCHAR 长度×字符集+2 / 可为 NULL +1，utf8mb4 按 4 字节算）、Extra 十一项逐条处置、多表 JOIN 的驱动表判断法、EXPLAIN ANALYZE 与 Handler% 状态核实法，配 scripts/explain_check.py 解析 EXPLAIN 表格并按严重/错误/警示/提示分级输出诊断。适用于后端研发、DBA 与数据开发。
license: Apache-2.0
author: 刘天宝｜墨燊
category: dev-programming
subCategories:
  - dev-data-storage
icon: icon.svg
tags: [MySQL, EXPLAIN, 执行计划, key_len, 索引失效, filesort, JOIN, SQL优化, 执行计划分析, 数据库调优]
language: zh-CN
visibility: public
---

# MySQL 执行计划 EXPLAIN 解读（mysql-explain-analyze）

EXPLAIN 有 12 列，但**每次必看的只有四项**：`type`、`key`、`rows`、`Extra`。
其余八列用来解释这四个为什么是这样。

这个技能做三件事：**读四列** → **用 key_len 反推用到第几列** → **按 Extra 给处置动作**。

---

## 硬边界（先看这条）

| 能做 | 不能做 |
|---|---|
| 逐列解释 EXPLAIN 输出的含义 | ❌ 代替 `EXPLAIN ANALYZE` 的真实执行数据 |
| 按 type/rows/Extra 给出严重度分级 | ❌ 保证按下述建议改完一定变快 |
| 用 key_len 反推实际用到的索引列 | ❌ 处理分区裁剪、直方图、优化器开关等高级场景 |
| 指出 join buffer / filesort 的根因方向 | ❌ 直接给出最终索引方案（需结合表结构与统计信息） |

**以下情况必须先做别的：**
- `rows` 估算与实际差一个数量级 → 先 `ANALYZE TABLE` 刷新统计信息
- 想看真实执行 → 用 `EXPLAIN ANALYZE`（MySQL 8.0.18+）
- `Impossible WHERE` → 先检查 SQL 是不是写错了，不是优化问题

---

## 一、什么时候用这个技能

| 用户这样说 | 就用 |
|---|---|
| "EXPLAIN 结果怎么看" | ✅ |
| "type=ALL 是不是很严重" | ✅ |
| "key_len 怎么算出用了几列" | ✅ |
| "Using filesort 要不要管" | ✅ |
| "filtered 只有 10 是什么情况" | ✅ |
| "possible_keys 有值但 key 是 NULL" | ✅ |
| "EXPLAIN 和 EXPLAIN ANALYZE 有什么区别" | ✅ |

---

## 二、完整工作流

```
第 1 步  读规则文件 rules/explain_fields.md
第 2 步  拿到执行计划：EXPLAIN <SQL>;  或 MySQL 8 的 EXPLAIN ANALYZE <SQL>;
第 3 步  把结果存成文本，跑诊断脚本
         python scripts/explain_check.py --file explain.txt \
             --cols "tenant_id:int:no,status:tinyint:no,nick:varchar(64):no" --charset utf8mb4
第 4 步  按脚本给出的严重/错误/警示逐项处理（先看 type 与 key）
第 5 步  改完再 EXPLAIN 一次，对比 rows 与 Extra
第 6 步  rows 与实际不符时用 EXPLAIN ANALYZE 或 Handler% 状态核实
```

---

## 三、type：从优到劣（最重要的一列）

| # | type | 含义 | 判定 |
|---|---|---|---|
| 1 | `system` / `const` | 主键或唯一索引一次命中 | 最优 |
| 2 | `eq_ref` | 联表时被驱动表主键等值匹配 | 好 |
| 3 | `ref` / `ref_or_null` | 非唯一索引等值匹配 | 好 |
| 4 | `range` | 范围扫描（`>` `<` `BETWEEN` `IN` `LIKE 'x%'`） | 可接受 |
| 5 | `unique_subquery` / `index_subquery` | 子查询转索引查找 | 可接受 |
| 6 | `index_merge` | 合并多个索引 | **警示**：说明索引没建全 |
| 7 | `index` | **全索引扫描**（扫整棵树） | 警示：比 ALL 略好而已 |
| 8 | `ALL` | **全表扫描** | **严重** |

判定阈值：OLTP 单表查询 `type` 至少要到 `range`，最好是 `ref`/`const`；出现 `ALL` 且 `rows > 1 万`必须处理。

---

## 四、key_len：反推用到第几列（很多人不会算）

| 类型 | NOT NULL | 可为 NULL |
|---|---|---|
| TINYINT / SMALLINT / INT / BIGINT | 1 / 2 / 4 / 8 | +1 |
| DATE / TIMESTAMP / DATETIME | 3 / 4 / 5 | +1 |
| CHAR(n) | n × 字符集字节 | +1 |
| VARCHAR(n) | n × 字符集字节 **+ 2**（长度前缀） | +1 |

字符集字节：`latin1`=1、`utf8`=3、**`utf8mb4`=4**、`gbk`=2。

例：`KEY idx_tsn (tenant_id INT, status TINYINT, nick VARCHAR(64))`，utf8mb4：

| 用到几列 | 计算 | key_len |
|---|---|---|
| tenant_id | 4 | **4** |
| + status | 4 + 1 | **5** |
| + nick | 5 + (64×4+2) | **263** |

看到 `key_len=5` 说明第三列没被用上（很可能被范围条件截断了，见「联合索引失效」技能）。

---

## 五、Extra 逐条处置

| Extra | 要紧吗 | 处置 |
|---|---|---|
| `Using index` | 好 | 覆盖索引，不回表，保持 |
| `Using index condition` | 好 | ICP，减少回表但**仍会回表** |
| `Using where` | 看情况 | 与 `type=ALL` 同现说明全表 + Server 层过滤 |
| `Using filesort` | **要管** | 排序没用上索引顺序 |
| `Using temporary` | **要管** | 用了临时表，关注是否落盘 |
| `Using join buffer (BNL / hash join)` | **严重** | 关联字段没索引 |
| `Range checked for each record` | **严重** | 关联写法有问题 |
| `Impossible WHERE` | 提示 | 条件恒假，检查 SQL 是否写错 |
| `Select tables optimized away` | 最优 | 优化器直接算出（如 MIN/MAX 走索引） |

---

## 六、脚本用法

```bash
python scripts/explain_check.py --file explain.txt
python scripts/explain_check.py --file explain.txt \
    --cols "tenant_id:int:no,status:tinyint:no,nick:varchar(64):no" --charset utf8mb4
```

| 参数 | 说明 |
|---|---|
| `--file` | EXPLAIN 输出文本（支持 mysql 客户端 `+---+` 表格与竖线简化格式） |
| `--cols` | 索引列定义，用于 **key_len 反推用到第几列**：`名:类型:是否可空` |
| `--charset` | 字符集，默认 `utf8mb4`（决定 VARCHAR/CHAR 的字节数） |
| `--json` / `--out` | JSON 输出 / 指定输出文件 |
| `--selftest` | 跑内置自检 |

脚本做四件事：① 解析 EXPLAIN 表格；② 按 type 排序判访问方式优劣（`ALL`/`index` 直接提示）；③ `key_len` 反推实际用到第几列；④ `rows × filtered` 与 Extra 逐项给出严重/错误/警示/提示分级诊断。

> 静态诊断基于 EXPLAIN 的**估算值**。估算与实际差得多时，用 `EXPLAIN ANALYZE` 的 `actual rows` 复核。

---

## 七、人工确认清单（这步不能省）

- [ ] `rows` 与实际行数是否同量级（差得多先 `ANALYZE TABLE`）
- [ ] `key` 选的和你预期一致吗（不一致先看统计信息，不要急着 `FORCE INDEX`）
- [ ] JOIN 两侧关联字段的类型与字符集一致吗（不一致会静默失效）
- [ ] `filtered` 低是因为条件没进索引，还是数据分布本身如此
- [ ] 驱动表是过滤后行数最小的那张吗
- [ ] 有没有用 `EXPLAIN ANALYZE` 复核过 `actual time`

---

## 八、最常见的坑

**坑一：只看到 key 有值就以为没问题。**
`key` 有值但 `key_len` 只有 4，说明只用了最左一列；后面的条件全部在 Server 层过滤。必须算 key_len。

**坑二：以为 `type=index` 是好事。**
`index` 是**全索引扫描**，扫的是整棵索引树，只是比全表扫的行宽小一点。真正好的是 `ref`/`const`/`range`。

**坑三：忽略 `filtered`。**
`rows=50000, filtered=10%` 意味着 5 万行被读出来，最后只剩 5 千行。**真正参与后续计算的是 rows × filtered%**，这个数才决定 JOIN 与排序的成本。

**坑四：把 `index_merge` 当优化成果。**
它说明**没有一条能覆盖条件的联合索引**，只能把两个索引各自扫一遍再合并去重。正解是补联合索引。

**坑五：`rows` 是估算值。**
EXPLAIN 从来不会真的执行 SQL。统计信息过期时它能报 100 行而实际 100 万行。验证用 `EXPLAIN ANALYZE` 的 `actual rows`，或用 `FLUSH STATUS` + `SHOW STATUS LIKE 'Handler%'`。

**坑六：看到 filesort 就加索引，不看排序方向。**
`ORDER BY a ASC, b DESC` 混用方向时，MySQL 5.7 加了索引照样 filesort。要么统一方向，要么 MySQL 8 建对应降序索引。

**坑七：JOIN 两边字段类型不一致。**
`orders.user_id` 是 `varchar`，`user.id` 是 `int`，被转换的一侧索引失效，表现为 `Using join buffer`。这是最常见的静默失效。

**坑八：用 `FORCE INDEX` 掩盖问题。**
统计信息没刷新、数据分布变了，`FORCE INDEX` 短期有效，长期会在数据量变化后突然反向。先 `ANALYZE TABLE`，再考虑 hint。

---

## 九、边界与免责

- 本技能解读的是 **EXPLAIN 估算结果**，真实执行请以 `EXPLAIN ANALYZE`、慢日志与线上观测为准
- MySQL 版本差异明显：`DATETIME` 在 5.5 是 8 字节、5.6+ 是 5 字节；`EXPLAIN ANALYZE` 需要 8.0.18+；8.0.18 起才有 hash join
- 修改索引属于生产变更，**必须先走评审并在预发验证回滚方案**
- 涉及 `FORCE INDEX`、`optimizer_switch` 的改动应作为临时手段并留整改 TODO

---

## 十、许可

本技能由 **刘天宝｜墨燊** 原创，采用 **Apache License 2.0**。

`rules/explain_fields.md` 中的字节数与版本差异以 MySQL 官方文档为准；不同版本请重新核对 `DATETIME` 等类型的字节长度。
