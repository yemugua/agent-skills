---
name: mysql-composite-index
slug: mysql-composite-index-tianbao
displayName: MySQL 联合索引失效排查
display_name: "MySQL 联合索引失效排查"
display_name_en: "MySQL Composite Index Invalidation Troubleshooting"
version: "1.0.0"
summary: 按「最左前缀 + 范围列右侧截断 + 索引列不得被加工」三条基准，逐句式判断联合索引到底用到第几列：缺最左列、跳列、范围后截断、函数包裹、隐式类型转换、前导通配符、否定条件、OR、ORDER BY 方向不一致，每条都配错误写法与正确写法。
description: 索引建了却没走、EXPLAIN 里 key_len 比预期短、加了索引还是慢时使用。当用户说"为什么这个联合索引没生效""key_len 只有一部分""范围查询后面的条件为什么不走索引""varchar 字段传数字会失效吗""LIKE '%xx' 能走索引吗""联合索引字段顺序怎么排""order by 为什么还是 filesort"时使用。内置最左前缀判定表（7 种 WHERE 组合对应的实际可用列）、范围右侧截断规则、七类「索引列被加工」的失效写法与改法、LIKE 三种模式的去留、否定条件与 IS NULL 的真实口径、ORDER BY/GROUP BY 排序与索引一致性的判定、覆盖索引与 Extra 字段含义对照，配 scripts/composite_index_check.py 做 SQL 与索引定义的静态核对。适用于后端研发、DBA 与数据开发。
license: Apache-2.0
author: 刘天宝｜墨燊
category: dev-programming
subCategories:
  - dev-data-storage
icon: icon.svg
tags: [MySQL, 联合索引, 最左前缀, 索引失效, 隐式类型转换, key_len, EXPLAIN, SQL优化, 索引下推, 覆盖索引]
language: zh-CN
visibility: public
---

# MySQL 联合索引失效排查（mysql-composite-index）

联合索引能不能用，**看三件事**：有没有从最左列开始、中间有没有断、到哪一列为止能保持有序。
第三条最关键也最容易被忽略：**范围条件右侧的列，只能做索引下推过滤，不能减少扫描行数**。

这个技能做三件事：**判定用到第几列** → **定位属于哪类失效** → **给改写 SQL 或改索引的方案**。

---

## 硬边界（先看这条）

| 能做 | 不能做 |
|---|---|
| 按最左前缀/范围截断/列加工三条基准判索引用到第几列 | ❌ 预测优化器最终选哪个索引（受统计信息、成本估算影响） |
| 指出具体失效写法并给出改写 | ❌ 代替 `EXPLAIN` / `EXPLAIN ANALYZE` 的实际结果 |
| 给出索引列顺序的设计取舍（等值在前、区分度、ORDER BY） | ❌ 保证改完一定变快 |
| 检查 ORDER BY/深分页/SELECT * 等写法问题 | ❌ 覆盖分区表、直方图、优化器开关等高级特性判断 |

**必须先看实际执行计划的情形：**
- 表数据量 < 1 万行（优化器可能直接全表，看不出差异）
- 用了 `FORCE INDEX` / `optimizer_switch` / `IGNORE INDEX`
- SQL 里有子查询、CTE、窗口函数
- MySQL 5.6 以下版本（索引下推、降序索引行为不同）

---

## 一、什么时候用这个技能

| 用户这样说 | 就用 |
|---|---|
| "联合索引没生效，是不是没走最左前缀" | ✅ |
| "key_len 只显示了前两列" | ✅ |
| "范围查询后面的条件能走索引吗" | ✅ |
| "varchar 字段传数字会失效吗" | ✅ |
| "LIKE '%张%' 怎么样才能走索引" | ✅ |
| "联合索引字段顺序怎么排" | ✅ |
| "帮我建一个新索引压测一下" | ❌ 需要在库上实测 |

---

## 二、完整工作流

```
第 1 步  读规则文件 rules/leftmost_prefix.md
第 2 步  拿到真实索引定义：SHOW CREATE TABLE t\G
第 3 步  跑静态检查
         python scripts/composite_index_check.py \
             --index "tenant_id,status,create_time" \
             --sql "SELECT id FROM t WHERE tenant_id=1 AND status>2 AND create_time='2026-01-01'"
第 4 步  EXPLAIN 验证：看 key / key_len / rows / Extra 四项（见配套 explain 技能）
第 5 步  改 SQL 或改索引后再 EXPLAIN，对比 rows 是否下降
第 6 步  慢日志记录 actual rows 与 EXPLAIN 估算是否一个量级
```

---

## 三、三条基准（判定核心）

### 基准一：必须从最左列开始，且连续不断

设 `KEY idx_abc (a, b, c)`：

| WHERE | 实际可用列 |
|---|---|
| `a=1` | a |
| `a=1 AND b=2` | a,b |
| `a=1 AND b=2 AND c=3` | a,b,c |
| `b=2` | **无**（缺最左列） |
| `a=1 AND c=3` | **只有 a**（b 断掉） |
| `b=2 AND a=1` | a,b（顺序无关，优化器会重排） |

### 基准二：范围条件右侧全部截断

| WHERE | 实际可用列 | 说明 |
|---|---|---|
| `a=1 AND b>10 AND c=5` | a,b | c 无法减少扫描行数，只能 ICP 过滤 |
| `a>1 AND b=2` | a | 首个真范围列就停 |
| `a=1 AND b IN (1,2,3) AND c=3` | a,b,c | **IN 不算范围截断**，可继续 |

所以建索引时：**范围/排序列放到等值列之后**。

### 基准三：索引列被加工就失效

| 失效写法 | 正确写法 |
|---|---|
| `WHERE DATE(create_time)='2026-01-01'` | `WHERE create_time >= '2026-01-01' AND create_time < '2026-01-02'` |
| `WHERE phone = 13800138000`（phone 是 varchar） | `WHERE phone = '13800138000'` |
| `WHERE amount/100 = 30` | `WHERE amount = 3000` |
| `WHERE LEFT(order_no,4)='A202'` | `WHERE order_no LIKE 'A202%'` |

> 数字列给字符串通常**不失效**（`'5'` 会转数字）；真正致命的是**字符串列给数字**——等于给索引列套了 CAST。

---

## 四、几种特殊条件的真实口径（常搞反）

| 条件 | 能否用索引 | 备注 |
|---|---|---|
| `LIKE 'abc%'` | ✅ 范围扫描 | 前导确定 |
| `LIKE '%abc'` / `'%abc%'` | ❌ | 改全文索引或反向列+函数索引 |
| `IS NULL` / `IS NOT NULL` | ✅ **可以走** | 常被误判为失效 |
| `!=` / `<>` / `NOT IN` / `NOT LIKE` | ❌ 多半全表 | 改正向枚举 `IN (...)` |
| `OR`（任一支无索引） | ❌ | 改 `UNION ALL` 或补联合索引 |
| 联表字符集/排序规则不一致 | ❌ 被转换侧失效 | 统一 `utf8mb4` 与 collation |

---

## 五、脚本用法

```bash
python scripts/composite_index_check.py --file case.sql
python scripts/composite_index_check.py --index "a,b,c" --sql "SELECT ... WHERE ..."
```

输入文件格式：

```
INDEX idx_ts (tenant_id, status, create_time)
SELECT id FROM t WHERE tenant_id = 1 AND status > 2 AND create_time = '2026-01-01';
```

| 参数 | 说明 |
|---|---|
| `--file` | 含 `INDEX name (c1,c2,..)` 指令与若干条以 `;` 结尾的 SQL 的文本 |
| `--index` | 命令行直接给索引列，逗号分隔 |
| `--sql` | 命令行给单条 SQL |
| `--json` / `--out` | JSON 输出 / 指定输出文件 |
| `--selftest` | 跑内置自检 |

脚本做三件事：① 按列顺序逐列判定 **实际可用列**并给出**截断原因**（缺最左列 / 被函数加工 / 前导通配符 / 否定条件 / 范围之后截断）；② 全局写法问题扫描（`SELECT *` 阻止覆盖索引、OR、列参与算术运算、深分页 `LIMIT 10000,20`、ORDER BY 顺序或方向不一致、GROUP BY 临时表）；③ 输出每条 SQL 对每个索引的可用列清单。

> **静态推演不等于优化器结果。** 真实是否走索引受区分度、统计信息、回表成本影响，必须再跑 `EXPLAIN`。

---

## 六、人工确认清单（这步不能省）

- [ ] `SHOW CREATE TABLE` 里的实际列类型，与 SQL 里传的值类型一致吗（varchar 传数字是重灾区）
- [ ] `key_len` 算出来用了几列？与脚本推断是否一致（不一致以 EXPLAIN 为准）
- [ ] 索引列的字符集/collation 与关联表一致吗
- [ ] 区分度够吗：`SELECT COUNT(DISTINCT col)/COUNT(*) FROM t`，低于 0.1 的列放前面意义不大
- [ ] 改完索引后，**写入路径**（INSERT/UPDATE/DELETE）有没有变慢
- [ ] 有没有冗余索引（`sys.schema_redundant_indexes`）

---

## 七、最常见的坑

**坑一：以为条件顺序影响索引。**
`WHERE b=2 AND a=1` 和 `WHERE a=1 AND b=2` 完全等价，优化器会重排。真正决定的是**有没有这一列**，不是写在哪。

**坑二：忽略范围右侧截断。**
`(tenant_id, create_time, status)` 上跑 `tenant_id=? AND create_time>? AND status=?`，只有前两列有效。改成 `(tenant_id, status, create_time)` 才是真正的三列命中——这是把 range 列放最后的直接理由。

**坑三：varchar 列传数字。**
`WHERE order_no = 20260101001` 看着无害，实际上 MySQL 对列做 CAST，索引直接失效，全表扫。字符串列必须加引号。

**坑四：把 DATE() 套在时间列上。**
`DATE(create_time) = '2026-01-01'` 想查一天，代价是全表。改成半开区间 `[start, start+1天)`，还能保证连续性不受秒级精度影响。

**坑五：以为 `IS NULL` 会失效。**
`IS NULL` / `IS NOT NULL` **可以**走索引（MySQL 把 NULL 当成最小的分组值存在索引里）。真正失效的是 `!=`、`NOT IN`。

**坑六：OR 依赖 index_merge。**
出现 `index_merge` 往往说明索引没建全。两个索引各自扫一遍再合并去重，通常比一个恰当的联合索引慢得多。

**坑七：ORDER BY 混用方向。**
`ORDER BY status ASC, create_time DESC` 在 MySQL 5.7 必然 filesort。MySQL 8 要给对应列建降序索引 `KEY(status ASC, create_time DESC)`。

**坑八：深分页。**
`LIMIT 10000, 20` 要扫 10020 行再丢掉前 10000 行。改成游标分页：记录上一页最大 id，`WHERE id > ? ORDER BY id LIMIT 20`。

---

## 八、边界与免责

- 本技能给出的是**基于语法的推演**，最终以 `EXPLAIN` / `EXPLAIN ANALYZE` / 慢日志实测为准
- MySQL 5.6/5.7/8.0 在索引跳跃扫描、降序索引、直方图上的行为差异较大，**请以实际版本为准**
- 增删索引会影响写入性能与磁盘占用，**生产变更前先在预发环境验证 rollout 计划**
- 索引优化不能替代数据归档与表结构治理；数据量级失控时应考虑分区/分库分表

---

## 九、许可

本技能由 **刘天宝｜墨燊** 原创，采用 **Apache License 2.0**。

`rules/leftmost_prefix.md` 中的判定口径基于 InnoDB B+ 树索引与 MySQL 优化器的工程实践整理，不同版本存在差异，落地请以实际版本的官方文档与实测结果为准。
