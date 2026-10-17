# EXPLAIN 结果解读规则库

## 1. 十二列各自看什么

| 列 | 看什么 | 异常信号 |
|---|---|---|
| `id` | 执行层级 | id 相同从上往下；id 越大越先执行；id 为 NULL 表示 UNION 结果集 |
| `select_type` | 查询类型 | `DEPENDENT SUBQUERY` 出现在量大的表上 = 逐行执行子查询，重点怀疑对象 |
| `table` | 表名/别名 | `<derived2>` 是派生表；`<union1,2>` 是 UNION 临时表 |
| `partitions` | 命中分区 | 非 NULL 且数量大 → 分区裁剪没生效 |
| `type` | **访问方式**，最重要 | 见 §2 |
| `possible_keys` | 候选索引 | 为 NULL 表示**没有任何可用索引** |
| `key` | **实际选中的索引** | 为 NULL = 没走索引；与 possible_keys 不同属正常，但需验证 |
| `key_len` | **实际用到的索引字节数** | 见 §3，用来反推用到第几列 |
| `ref` | 与索引比较的对象 | `const` 最好；`func` 表示比较前要算值；NULL 表示全扫/范围 |
| `rows` | **预估扫描行数** | 与实际行数差一个量级 → 统计信息失准，先 `ANALYZE TABLE` |
| `filtered` | 经过条件过滤后剩余百分比 | 低于 10% 且行数大 → 条件没被索引吸收，大量行被读到 Server 层再过滤 |
| `Extra` | 附加信息 | 见 §4 |

> `type` / `key` / `rows` / `Extra` 是每次必须看的四项，其余八项用于解释异常。

---

## 2. type：从好到坏

| type | 含义 | 出现场景 | 判定 |
|---|---|---|---|
| `system` | 表只有一行（MyISAM 内存表） | 极少 | 最优 |
| `const` | 主键/唯一索引等值命中一次 | `WHERE id = 1` | 最优 |
| `eq_ref` | 联表时被驱动表主键等值匹配 | `JOIN ... ON t.id = x.id` | 好 |
| `ref` | 非唯一索引等值匹配 | `WHERE name = 'x'` | 好 |
| `ref_or_null` | 上面的变体，多了 `IS NULL` | `WHERE name='x' OR name IS NULL` | 可接受 |
| `range` | 范围扫描 | `>` `<` `BETWEEN` `IN` `LIKE 'x%'` | 可接受 |
| `index_merge` | 合并多个索引的结果 | `WHERE a=1 OR b=2` | 警示：通常说明索引没建全 |
| `unique_subquery` / `index_subquery` | 子查询转成了索引查找 | `IN (SELECT ...)` | 可接受 |
| `index` | **全索引扫描**（扫整个索引树） | `SELECT COUNT(*)` 走二级索引、或 ORDER BY 无过滤 | 警示：比 ALL 稍好，但一样是全量 |
| `ALL` | **全表扫描** | 没索引 / 索引失效 | 严重 |

判定阈值：

- OLTP 单表查询：`type` 至少要到 **`range`**，最好是 `ref` / `const`
- 出现 `ALL` 且 `rows > 1 万`：**必须处理**
- 出现 `index_merge`：优先改为恰当的联合索引

---

## 3. key_len：反推实际用了几列

`key_len` 是**实际用到的索引列的字节总和**（不是列数）。算字节数：

| 类型 | NOT NULL | 可为 NULL |
|---|---|---|
| TINYINT | 1 | 2 |
| SMALLINT | 2 | 3 |
| INT | 4 | 5 |
| BIGINT | 8 | 9 |
| DATE | 3 | 4 |
| TIMESTAMP | 4 | 5 |
| DATETIME | 5（5.6+） | 6 |
| CHAR(n) | n × 字符集字节 | +1 |
| VARCHAR(n) | n × 字符集字节 **+ 2**（长度前缀） | +1 |

字符集字节数：`latin1`=1、`utf8`=3、**`utf8mb4`=4**、`gbk`=2。

### 计算示例

```sql
CREATE TABLE t (
  tenant_id INT NOT NULL,
  status    TINYINT NOT NULL,
  nick      VARCHAR(64) NOT NULL,
  KEY idx_tsn (tenant_id, status, nick)
) CHARSET=utf8mb4;
```

| 用到的列 | key_len 计算 | 结果 |
|---|---|---|
| tenant_id | 4 | 4 |
| tenant_id, status | 4 + 1 | 5 |
| tenant_id, status, nick | 5 + (64×4 + 2) = 5 + 258 | 263 |

看到 `key_len = 5` 就知道只用了前两列（第三列被截断或没给条件）；`key_len = 263` 才是三列全用上。

> 可为 NULL 的列要**再加 1 字节**：上面如果 `status` 允许 NULL，两列的 key_len 就是 4 + 2 = 6。

> 反过来算：`(key_len - 已知前缀字节) / (单字符字节)` 可推出 VARCHAR 用了几个字符。

---

## 4. Extra 逐项解读

| Extra | 含义 | 处置 |
|---|---|---|
| `Using index` | **覆盖索引**，不回表 | 好，尽量达成 |
| `Using index condition` | **索引下推 ICP**，过滤下推到引擎层 | 好，但仍会回表 |
| `Using where` | Server 层再过滤一次 | 可接受；若与 `type=ALL` 同时出现则是全表 + 过滤 |
| `Using filesort` | **无法用索引顺序，额外排序** | 需要优化：给 ORDER BY 列配索引或缩小排序集 |
| `Using temporary` | **用了临时表**（GROUP BY / DISTINCT / UNION 常见） | 落盘则更糟，关注 `Created_tmp_disk_tables` |
| `Using join buffer (Block Nested Loop / hash join)` | **关联字段没有索引**，用 join buffer 兜底 | 补索引；MySQL 8 的 hash join 也远慢于有索引 |
| `Impossible WHERE` / `no matching row in const table` | 条件恒假，不需要执行 | 检查 SQL 是否写错（如 `WHERE 1=0`、类型不匹配导致恒假） |
| `Range checked for each record` | 每行都要判断是否用索引 | 严重，通常是关联条件写法有问题 |
| `Select tables optimized away` | 优化器直接算出来了（常见 `MIN/MAX` 走索引） | 最优 |
| `Using MRR` | 多范围读取，减少随机 IO | 好 |
| `Using filesort` + `Using temporary` 同现 | 排序 + 临时表，双杀 | 高优先级优化 |

---

## 5. 多表 JOIN 的读法

```
id 相同：从上往下执行，第一行是驱动表
id 不同：id 大的先执行（通常是子查询/派生表）
```

判断对错的关键：**驱动表应该是过滤后结果集最小的那张表**。

```sql
EXPLAIN SELECT * FROM orders o JOIN user u ON o.user_id = u.id WHERE o.status = 1;
```

| 期望 | 表现 | 如果不是这样 |
|---|---|---|
| `orders` 作驱动表（先过滤 status） | `orders` 在上，`type=ref/range`，`rows` 小 | 优化器选错时可用 `STRAIGHT_JOIN` 提示，但先确认统计信息准确 |
| `user` 走 `eq_ref` | `key=PRIMARY`，`rows=1` | 说明 `o.user_id` 与 `u.id` **类型不一致**，两侧都要 INT |

---

## 6. EXPLAIN ANALYZE（MySQL 8.0.18+）

`EXPLAIN` 给的是**估算**，`EXPLAIN ANALYZE` 给的是**实际执行**：

```sql
EXPLAIN ANALYZE SELECT * FROM t WHERE create_time > '2026-01-01';
-- 输出形如：-> Filter: (t.create_time > ...) (cost=... rows=...) (actual time=0.02..120.5 rows=987654 loops=1)
```

读法：**盯 `actual time` 与 `actual rows`**，`rows` 估算与实际差一个数量级就是统计信息失准，先 `ANALYZE TABLE`。

其他核实手段：

```sql
FLUSH STATUS;
SELECT ... ;
SHOW STATUS LIKE 'Handler%';   -- Handler_read_next/rnd_next 的量就是真实扫描行数
```

---

## 7. 六步排查清单

```
1  先看 type：有没有 ALL / index
2  看 key：为 NULL 就是没走索引，回去对照「联合索引失效」规则库
3  算 key_len：判断实际用到第几列
4  看 rows × filtered：估算真正参与后续计算的行数 = rows × filtered%
5  看 Extra：有没有 filesort / temporary / join buffer
6  rows 与实际差得多 → ANALYZE TABLE 或 EXPLAIN ANALYZE 复核
```
