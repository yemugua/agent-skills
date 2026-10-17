# MySQL 慢 SQL 定位与改写规则库

## 1. 先定位：三条互补路径

| 路径 | 怎么拿 | 适合解决什么 |
|---|---|---|
| **慢查询日志** | `slow_query_log=ON`，`long_query_time=1`（生产建议 0.5-1s），`log_queries_not_using_indexes=ON`（谨慎，量大） | 事后统计：哪些 SQL 慢、平均耗时、扫描行数 |
| `pt-query-digest` / `mysqldumpslow` | `mysqldumpslow -s t -t 20 slow.log` | 按总耗时排序，找出 TOP 20 |
| `performance_schema` + `sys` | `SELECT * FROM sys.statements_with_ranking_by_total_latency LIMIT 10` | 实时：不用等日志，看按延迟/扫描行/临时表排序的语句摘要 |
| **`SHOW PROCESSLIST` / `sys.session`** | 现场抓 | 突发的"现在卡住了"，配合 `WHERE command != 'Sleep' AND time > 2` |

> 只看执行次数少的 SQL 没意义。**总耗时 = 平均耗时 × 执行次数**，优化优先看总耗时 TOP10。

### 1.1 三个必看的数字

```
Rows_examined / Rows_sent  =  扫描比
```

| 扫描比 | 判定 | 动作 |
|---|---|---|
| ≈ 1-10 | 正常 | 索引基本生效 |
| 100-1000 | 可疑 | 检查是否没走索引或回表过多 |
| > 10000 | 严重 | 基本是全表扫或被 LIMIT 深分页拖累 |

另外两个必看：`Lock_time`（锁等待，可能是事务没提交或热点行）与 `Created_tmp_disk_tables`（落盘临时表，说明 `tmp_table_size` 不够或 SQL 写法问题）。

### 1.2 拿到 SQL 之后

```
1  EXPLAIN <SQL>                       看 type/key/rows/Extra
2  EXPLAIN ANALYZE <SQL>               MySQL 8：看真实行数与估算差
3  SHOW INDEX FROM <表>                看 Cardinality 是否与实际相符
4  ANALYZE TABLE <表>                  统计信息失准导致选错索引时刷新
5  FLUSH STATUS + SHOW STATUS LIKE 'Handler%'  核实扫描行数（会话级）
```

**统计信息失准的典型信号**：EXPLAIN 估算 100 行，实际 100 万行。

---

## 2. 十二类高频反模式（照条目打钩）

| # | 反模式 | 识别方法 | 改写方案 |
|---|---|---|---|
| 1 | **深分页** | `LIMIT 10000, 20` | 游标分页：`WHERE id > <上一页最大id> ORDER BY id LIMIT 20` |
| 2 | **列套函数** | `WHERE DATE(t)=x` `YEAR(t)=2026` | 改半开区间：`t >= '2026-01-01' AND t < '2027-01-01'` |
| 3 | **隐式类型转换** | 字符串列与数字比较 | 加引号；或统一列类型 |
| 4 | **前导 `%` 的 LIKE** | `LIKE '%x%'` | 后缀用反向列+函数索引；包含用 FULLTEXT / ES |
| 5 | **SELECT \*** | 查了不用的列 | 只查需要的列；利于覆盖索引 |
| 6 | **关联子查询** | WHERE 里嵌 `SELECT ... WHERE t.id = outer.id` | 改 JOIN 或 EXISTS（MySQL 8 对 IN 子查询优化已改善，仍需验证） |
| 7 | **OR 跨多个无索引列** | `WHERE a=1 OR b=2` | 改 `UNION ALL`；或给两边都建索引/合并成联合索引 |
| 8 | **大 IN 列表** | `IN (1,2,...,5000)` | 分批（每批 ≤ 500）或走临时表 JOIN |
| 9 | **随机排序** | `ORDER BY RAND()` | 先算随机主键再取：`WHERE id >= rand_id LIMIT 1` |
| 10 | **COUNT(\*) 大表** | `SELECT COUNT(*) FROM big WHERE ...` | 用近似值（`information_schema.TABLES.TABLE_ROWS`）、计数表或汇总表 |
| 11 | **派生表无法合并** | FROM 里有子查询且含聚合/去重 | 改为临时表存中间结果，或拆成两条 SQL |
| 12 | **大事务/批量写** | 单条 `UPDATE` 影响几十万行 | 分批 `LIMIT 1000` 循环，避免长事务与锁放大 |

---

## 3. 改写模板（直接抄）

### 3.1 深分页 → 游标分页

```sql
-- 慢：越往后越慢
SELECT id, order_no FROM orders WHERE tenant_id = 1 ORDER BY id LIMIT 10000, 20;
-- 快：必须依赖有序且唯一的游标列
SELECT id, order_no FROM orders WHERE tenant_id = 1 AND id > 12345 ORDER BY id LIMIT 20;
```

> 若必须跳页，退而求其次：用覆盖索引先取主键再回表
> `SELECT t.* FROM orders t JOIN (SELECT id FROM orders WHERE tenant_id=1 ORDER BY id LIMIT 10000,20) x USING(id)`

### 3.2 COUNT 优化

| 场景 | 方案 |
|---|---|
| 只要大概规模 | `SELECT TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA='db' AND TABLE_NAME='t'` |
| 精确且高频 | 独立计数表 / Redis 计数，写路径维护 |
| `COUNT(*)` 走二级索引 | 让 MySQL 选索引长度最小的二级索引扫描（`count(*)` 会被优化自动选） |
| 只要"有没有" | `SELECT 1 FROM t WHERE ... LIMIT 1`，别 COUNT |

### 3.3 JOIN 优化要点

```sql
-- 小表驱动大表：把过滤后结果集小的表放在驱动位
SELECT /*+ STRAIGHT_JOIN */ ...
-- JOIN 列必须类型一致、字符集一致（不一致会失效）
-- 关联键没有索引时，MySQL 用 BNL / Hash Join(8.0.18+)：
SHOW VARIABLES LIKE 'join_buffer_size';   -- 增大可缓解，但只是兜底不是根治
```

MySQL 8.0.18 起支持 Hash Join，**没有索引的等值关联不再必然走 BNL**，但仍远慢于有索引。不要因为有 Hash Join 就不建索引。

### 3.4 排序 / 分组

| 问题 | 解决 |
|---|---|
| `Using filesort` | 让 ORDER BY 列与索引顺序一致（见联合索引规则库 §7） |
| sort_buffer 太小导致落盘 | `sort_buffer_size` 适当调大，或 Limit 返回列减少不参与排序的列 |
| `GROUP BY` 走 `Using temporary` | 给分组列建索引；或加 `ORDER BY NULL` 取消隐式排序 |
| 只需要去重的前几条 | `GROUP BY` 加索引走 Loose Index Scan |

### 3.5 更新与删除

```sql
# 危险：一次更新几十万行，长事务 + 大 undo + 主从延迟
UPDATE orders SET status = 9 WHERE create_time < '2020-01-01';
# 稳：分批
UPDATE orders SET status = 9 WHERE create_time < '2020-01-01' AND id BETWEEN ? AND ? LIMIT 1000;
```

```sql
# 全表删除用 TRUNCATE（DDL，不能回滚，不走 undo）
TRUNCATE TABLE tmp_xxx;
```

---

## 4. 参数与资源：先看这是不是 SQL 的锅

| 现象 | 可能的非 SQL 原因 |
|---|---|
| 偶发慢，平时快 | Buffer Pool 命中率波动、`sync` 刷脏、备份任务、邻居 IO 抢占 |
| 慢但 EXPLAIN 很好 | 锁等待（`SHOW ENGINE INNODB STATUS` 看 `LATEST DETECTED DEADLOCK` / trx）。常被误判为"索引失效" |
| `Created_tmp_disk_tables` 高 | `tmp_table_size` / `max_heap_table_size` 太小 |
| 写慢 | redo log 太小（`innodb_log_file_size`）、刷盘策略（`innodb_flush_log_at_trx_commit`） |
| 主从延迟导致读到旧数据 | 读一致性要求高的场景走主库或等 GTID |

**先排除「锁等待」和「IO 抖动」，再谈 SQL 改写。** 一条执行计划很漂亮的 SQL，在行锁排队 3 秒的情况下照样慢。

---

## 5. 优化后的验证口径

| 指标 | 判定改善的标准 |
|---|---|
| `Rows_examined` | 下降到返回行数的 10 倍以内 |
| `rows`（EXPLAIN 估算） | 明显下降，且与 `EXPLAIN ANALYZE` 实际值同量级 |
| Extra | `Using filesort` / `Using temporary` 消失或降级为 `Using index` |
| 平均 RT | 看慢日志聚合后的 P95，不看单次执行 |
| 锁/IO | `Lock_time` 与 `Rows_sent` 无明显上升 |

一次长周期验证原则：**改索引后至少观察一个完整业务周期**（一天或一周），确认没有因为统计信息变化把另一条 SQL 拖慢。
