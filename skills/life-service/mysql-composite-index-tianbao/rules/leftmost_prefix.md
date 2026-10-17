# MySQL 联合索引失效排查规则库

> 判定基准：**最左前缀 + 范围列右侧截断 + 索引列不能被加工**。
> 每一条都给「错误写法 → 正确写法 → 原理」，可直接照着改 SQL。

---

## 1. 最左前缀：就是「连续能用多少列」

设索引 `KEY idx_abc (a, b, c)`，索引在磁盘上的组织方式是**先按 a 排序、a 相同再按 b 排序、再按 c**。所以只有从最左且**连续不断**的列才能走。

| WHERE 写法 | 用到的列 | 判定 |
|---|---|---|
| `WHERE a = 1` | a | 走索引（最左列） |
| `WHERE a = 1 AND b = 2` | a,b | 走索引 |
| `WHERE a = 1 AND b = 2 AND c = 3` | a,b,c | 走索引（全命中） |
| `WHERE b = 2` | —— | **失效**，缺最左列 a，全表扫 |
| `WHERE c = 3` | —— | **失效** |
| `WHERE a = 1 AND c = 3` | a | **只用 a**，c 被跳过，不能连续（MySQL 8 索引跳跃扫描除外，且仅 a 区分度很低时才可能启用） |
| `WHERE b = 2 AND c = 3` | —— | **失效** |

> **顺序无关**：`WHERE b=2 AND a=1` 与 `WHERE a=1 AND b=2` 等价，优化器会重排。**真正决定的是「有没有」而不是「写在哪」**。

### 建索引时的列顺序三原则

1. **等值条件列在前**，范围/排序列在后
2. **区分度高的列尽量靠前**（同一份数据，`status` 只有 3 个值，`order_no` 几乎唯一 → `order_no` 在前）
3. **兼顾 ORDER BY**：若查询固定 `WHERE tenant_id=? ORDER BY create_time`，应建 `(tenant_id, create_time)`，让排序直接从索引取，避免 filesort

---

## 2. 范围条件右侧全部截断（最容易被忽略的一条）

设 `KEY idx_abc (a, b, c)`：

| WHERE | 用到的列 | 说明 |
|---|---|---|
| `a=1 AND b>10 AND c=5` | a,b | **c 用不上**：b 是范围，之后的列不再有序，c 只能做 ICP 过滤，不能减少扫描行数 |
| `a>1 AND b=2` | a | b 用不上 |
| `a=1 AND b BETWEEN 1 AND 9 AND c=3` | a,b | c 用不上（BETWEEN 等同范围） |
| `a=1 AND b LIKE 'x%' AND c=3` | a,b | c 用不上（前导确定的 LIKE 是范围扫描） |
| `a=1 AND b IN (1,2,3) AND c=3` | a,b,c | **IN 不算范围截断**（MySQL 视多个等值点去重后再探测），c 仍可用 |

**改法**：把范围列放到最后，或把范围条件再拆。

```sql
-- 错：c 被 b 的范围截断
WHERE tenant_id = 7 AND create_time > '2026-01-01' AND status = 1
-- 索引 (tenant_id, create_time, status)：只用到 (tenant_id, create_time)
-- 对
KEY idx_t_s_time (tenant_id, status, create_time)
```

---

## 3. 索引列被「加工」就失效（包括隐式加工）

只要 `WHERE` 里索引列不是**单独出现在 `=` / `IN` / 范围右侧**，优化器就用不上它的有序性。

| 类型 | 失效写法 | 正确写法 |
|---|---|---|
| 套函数 | `WHERE DATE(create_time) = '2026-01-01'` | `WHERE create_time >= '2026-01-01' AND create_time < '2026-01-02'` |
| 隐式计算 | `WHERE amount / 100 = 30` | `WHERE amount = 3000` |
| 字符串函数 | `WHERE LEFT(order_no, 4) = 'A202'` | `WHERE order_no LIKE 'A202%'` |
| 隐式类型转换（字符串列给数字） | `WHERE phone = 13800138000`（phone 是 varchar） | `WHERE phone = '13800138000'` |
| 隐式字符集转换 | 两表 `utf8mb4` 与 `utf8` 联表，字符集不同的一侧索引失效 | 统一字符集与排序规则 |
| 运算在列上 | `WHERE id + 1 = 5` | `WHERE id = 4` |

**反向说明**：数字列给字符串通常**不会**失效（`WHERE id = '5'` 会把字符串转成数字比较），真正致命的是**字符串列给数字**——MySQL 会对列做 CAST，等于给索引列套了函数。

---

## 4. LIKE：只有「前导确定」才能走范围

| 写法 | 能否用索引 |
|---|---|
| `LIKE 'abc%'` | ✅ 走范围扫描（首字符确定，能定位起点） |
| `LIKE '%abc'` | ❌ 失效，全表扫 |
| `LIKE '%abc%'` | ❌ 失效，全表扫 |
| `LIKE 'ab_c'` | ✅ `_` 单个占位不影响前导确定 |
| `LIKE '\abc%'`（`\` 转义一次） | ✅ 仍可用 |

替代方案（前缀/后缀/包含三种需求分别对应）：

```sql
-- 前缀：直接索引
WHERE name LIKE 'abc%'
-- 后缀：反向存储 + 函数索引 / 生成列 + 索引
ALTER TABLE t ADD name_rev VARCHAR(64) AS (REVERSE(name)), ADD KEY(name_rev);
WHERE name_rev LIKE REVERSE('%abc')
-- 包含：走全文索引 FULLTEXT 或外部检索（ES）
MATCH(name) AGAINST ('abc' IN BOOLEAN MODE)
```

---

## 5. 否定类条件几乎必然失效

| 写法 | 判定 |
|---|---|
| `status != 1` / `status <> 1` | 通常全表扫（除非该值占比极小且优化器判断回表成本更高时才可能走 index scan） |
| `NOT IN (1,2)` | 同上 |
| `NOT LIKE 'a%'` | 失效 |
| `IS NULL` | ✅ **可以走索引**（这是常被误解的一条） |
| `IS NOT NULL` | ✅ 通常可以走索引 |

改法：把否定改成正向枚举，或利用默认值把 NULL 消除：

```sql
-- 错
WHERE status != 3
-- 对：枚举正向值（能用上时 IN 也走索引）
WHERE status IN (0, 1, 2, 4)
```

---

## 6. OR：一边没索引就全崩

```sql
-- 错：name 无索引，整个条件退化成全表
WHERE phone = '138...' OR name = '张三'
-- 对 1：给 name 也建索引，优化器会走 index_merge（注意：index_merge 常比预期慢）
-- 对 2：拆成 UNION ALL（两边各自走索引，多数情况更稳）
SELECT * FROM t WHERE phone = '138...'
UNION ALL
SELECT * FROM t WHERE name = '张三'
```

> `index_merge` 出现常常说明**索引建得不完整**，应优先改成联合索引，而不是依赖 OR 合并两个索引的扫描结果再合并去重。

---

## 7. ORDER BY / GROUP BY：排序要用索引必须「顺序一致 + 方向一致」

设 `KEY idx_tsc (tenant_id, status, create_time)`：

| 写法 | 是否用索引排序 |
|---|---|
| `WHERE tenant_id=1 ORDER BY create_time` | ⚠️ 中间跳过了 status，只用 tenant_id，**需 filesort** |
| `WHERE tenant_id=1 AND status=2 ORDER BY create_time` | ✅ 不排序，直接顺序读 |
| `ORDER BY status, create_time`（方向同 ASC） | ✅ |
| `ORDER BY status ASC, create_time DESC` | ❌ MySQL 8 支持降序索引才可行；5.7 需 filesort，或建 `(status ASC, create_time DESC)` 降序索引 |
| `GROUP BY` 缺失索引 | ❌ 会走 Using temporary + Using filesort |

**降序索引写法（MySQL 8）**：

```sql
KEY idx_desc (status ASC, create_time DESC)
```

---

## 8. 覆盖索引：`Extra` 出现 `Using index` 才是真省

```sql
-- 需要回表（查了索引里没有的列 extra_data）
SELECT order_no, extra_data FROM t WHERE tenant_id=1 AND status=2
-- 走覆盖索引，不回表
CREATE KEY idx_cov (tenant_id, status, order_no);
SELECT tenant_id, status, order_no FROM t WHERE tenant_id=1 AND status=2
```

判定口径：

| Extra 出现 | 含义 |
|---|---|
| `Using index` | 覆盖索引生效，不回表 ✅ |
| `Using index condition` | 索引条件下推（ICP），减少了回表次数，但**仍然回表** |
| `Using where` | 在 Server 层再过滤一遍，说明索引没能完全覆盖条件 |
| `Using filesort` | 无法用索引顺序，额外排序 |
| `Using temporary` | 用了临时表（GROUP BY / DISTINCT 常见） |

---

## 9. 设计索引时的取舍表

| 场景 | 建议 |
|---|---|
| WHERE + ORDER BY 一起出现 | 把 ORDER BY 列接在 WHERE 等值列之后 |
| 区分度极低的列（性别、是否删除、状态码 0/1） | 不要单独建；作为联合索引**后面**的列尚可，但要看区分度 —— `WHERE deleted=0 AND tenant_id=?` 应写成 `(tenant_id, deleted)` |
| 超长字符串（TEXT/VARCHAR(500)） | 用前缀索引 `KEY(email(20))`，并验证区分度：`SELECT COUNT(DISTINCT LEFT(email,20))/COUNT(*) FROM t` 应 ≥ 0.9 |
| 频繁更新的列 | 少建；每个索引都会让写入多一次 B+ 树维护 |
| 冗余索引 | `(a,b)` 和 `(a)` 同时存在时 `(a)` 是冗余；用 `sys.schema_redundant_indexes` 查 |

---

## 10. 排查动作清单（按顺序做）

```
1  EXPLAIN <原SQL>                                 看 key / key_len / rows / Extra
2  SHOW CREATE TABLE <表>                          拿到实际索引定义与字符集
3  对照 §1-§7 逐条匹配失效写法
4  用 key_len 反推实际用了几列（见 explain 技能为何 4+4+8 之类）
5  改 SQL / 改索引后，再 EXPLAIN 一次对比 rows
6  SET optimizer_trace='enabled=on' 看是否考虑过该索引
7  上生产前用 EXPLAIN ANALYZE 或慢日志 actual rows 校验
```
