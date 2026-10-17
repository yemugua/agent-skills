---
name: mysql-slow-query-tune
slug: mysql-slow-query-tune-tianbao
displayName: SQL 慢查询优化与改写
display_name: "SQL 慢查询优化与改写"
display_name_en: "MySQL Slow Query Tuning and Rewrite"
version: "1.0.0"
summary: 从慢日志 / performance_schema / sys.statements 三条路径定位 TOP 慢 SQL，用「扫描比 = Rows_examined / Rows_sent」判定严重程度，给出深分页、列套函数、隐式转换、OR、关联子查询、大 IN、随机排序、COUNT、大事务等 12 类反模式的识别与改写模板，附维护成本与验证口径。
description: 线上 SQL 慢、不知道该优化哪一条、改完也不知道有没有变好用时使用。当用户说"这个 SQL 为什么这么慢""慢日志怎么看""count(*) 太慢怎么办""limit 分页越往后越卡""批量更新把库拖垮了""order by rand 能不能用""SQL 改了还是慢，是不是锁"时使用。内置慢日志三条定位路径（慢日志 / sys.statements_with_ranking_by_total_latency / SHOW PROCESSLIST 抓现场）、扫描比分级口径、先排除锁等待与 IO 抖动的判断顺序、12 类高频反模式表（每类给出改写 SQL）、COUNT/JOIN/排序分组/批量写的专项套路、优化后五个验证指标，配 scripts/slow_sql_check.py 支持直接解析慢日志文件（自动算扫描比）与扫描 SQL 写法并输出风险分。适用于后端研发、DBA 与数据开发。
license: Apache-2.0
author: 刘天宝｜墨燊
category: dev-programming
subCategories:
  - dev-data-storage
icon: icon.svg
tags: [MySQL, 慢查询, 慢日志, SQL优化, 深分页, COUNT优化, 锁等待, 批量写, EXPLAIN, 性能优化]
language: zh-CN
visibility: public
---

# SQL 慢查询优化与改写（mysql-slow-query-tune）

慢 SQL 优化的顺序是：**先定位 TOP SQL → 排除非 SQL 因素（锁、IO）→ 再看写法 → 最后才谈加索引**。
判定严重程度看一个数字：**扫描比 = Rows_examined / Rows_sent**。

这个技能做三件事：**排优先级** → **归类反模式** → **给改写模板与验证口径**。

---

## 硬边界（先看这条）

| 能做 | 不能做 |
|---|---|
| 按慢日志/sys 视图定位 TOP 慢 SQL | ❌ 代替线上实际执行与压测 |
| 用扫描比判定严重程度与改进优先级 | ❌ 保证改完一定变快 |
| 给出 12 类反模式的改写模板 | ❌ 覆盖所有业务特殊场景 |
| 提示「先看是不是锁等待」 | ❌ 诊断死锁/锁等待的根因（需 `SHOW ENGINE INNODB STATUS`） |
| 解析慢日志 + 扫描 SQL 写法 | ❌ 直接执行 DDL/DML |

**先停手排查的情形：**
- `Lock_time` 明显偏高 → 大概率是锁等待，不是索引问题
- 偶发慢平时快 → 先看 Buffer Pool 命中、刷脏、备份、邻居 IO
- 慢但 EXPLAIN 很好 → 查 `SHOW ENGINE INNODB STATUS` 与长事务
- 准备批量改数据 → 先分批演练，不要一次几十万行

---

## 一、什么时候用这个技能

| 用户这样说 | 就用 |
|---|---|
| "这条 SQL 为什么这么慢" | ✅ |
| "慢日志怎么看，重点看什么" | ✅ |
| "深分页越来越慢怎么改" | ✅ |
| "COUNT(*) 太慢有什么办法" | ✅ |
| "批量 update 把库拖垮了" | ✅ |
| "改了索引还是慢" | ✅（先看是不是锁） |
| "帮我直接在线上改这条 SQL" | ❌ 需走变更流程 |

---

## 二、完整工作流

```
第 1 步  读规则文件 rules/slow_query_tuning.md
第 2 步  定位 TOP SQL（三选一）
         慢日志      : pt-query-digest slow.log / mysqldumpslow -s t -t 20
         实时摘要    : SELECT * FROM sys.statements_with_ranking_by_total_latency LIMIT 10
         现场抓      : SELECT * FROM sys.session WHERE command != 'Sleep' AND time > 2
第 3 步  算扫描比 Rows_examined / Rows_sent，按 §1.1 表判定严重程度
第 4 步  排除非 SQL 因素：Lock_time、临时表落盘、刷脏抖动
第 5 步  跑脚本（可直连解析慢日志）
         python scripts/slow_sql_check.py --file slow.log --slowlog
第 6 步  按 §2 的十二类反模式归类，套 §3 的改写模板
第 7 步  EXPLAIN + EXPLAIN ANALYZE 验证，按 §5 五项指标确认改善
```

---

## 三、扫描比判定（一个数字定优先级）

| `Rows_examined / Rows_sent` | 判定 | 动作 |
|---|---|---|
| 1 - 10 | 正常 | 索引基本生效 |
| 10 - 100 | 留意 | 可考虑覆盖索引 |
| 1000 - 10000 | 可疑 | 检查索引是否生效、是否被深分页拖累 |
| > 10000 | 严重 | 基本是全表扫或深分页 |

排序优先级：**总耗时 = 平均耗时 × 执行次数**，先看总耗时 TOP 10，别只看单次最慢的那条。

---

## 四、十二类高频反模式（识别 → 改写）

| # | 反模式 | 改写方向 |
|---|---|---|
| 1 | 深分页 `LIMIT 10000,20` | 游标分页 `WHERE id > <上一页最大id> ORDER BY id LIMIT 20` |
| 2 | 列套函数 `DATE(t)=x` | 半开区间 `t >= '2026-01-01' AND t < '2026-01-02'` |
| 3 | 隐式类型转换（varchar 列传数字） | 加引号；统一列类型 |
| 4 | `LIKE '%x%'` | 后缀：反向列+函数索引；包含：FULLTEXT / ES |
| 5 | `SELECT *` | 只查需要的列，利于覆盖索引 |
| 6 | 关联子查询 | 改 JOIN / EXISTS，用 EXPLAIN 验证 |
| 7 | `OR` 跨无索引列 | `UNION ALL` 或补联合索引 |
| 8 | 大 IN 列表 | 分批 ≤500 或临时表 JOIN |
| 9 | `ORDER BY RAND()` | 随机主键区间取值 |
| 10 | 大表 `COUNT(*)` | 近似值 / 计数表 / 只要存在性改 `SELECT 1 ... LIMIT 1` |
| 11 | 不可合并的派生表 | 拆两条 SQL 或落临时表 |
| 12 | 一次更新几十万行 | 分批 `LIMIT 1000` 循环，控长事务 |

> 批量写模板：
> `UPDATE orders SET status=9 WHERE create_time<'2020-01-01' AND id BETWEEN ? AND ? LIMIT 1000;`

---

## 五、脚本用法

```bash
# 直接解析慢日志（自动算扫描比、按耗时排序、判定严重程度）
python scripts/slow_sql_check.py --file slow.log --slowlog

# 扫描 SQL 写法，输出每条 SQL 的风险分与改写建议
python scripts/slow_sql_check.py --file sql.txt
python scripts/slow_sql_check.py --sql "SELECT * FROM t LIMIT 10000, 20"
```

| 参数 | 说明 |
|---|---|
| `--file` | SQL 文本（多条以 `;` 分隔）或慢日志文件 |
| `--slowlog` | 按慢日志格式解析（识别 Query_time / Lock_time / Rows_sent / Rows_examined） |
| `--sql` | 单条 SQL 快速检查 |
| `--json` / `--out` | JSON 输出 / 指定输出文件 |
| `--selftest` | 跑内置自检 |

脚本两种模式：
- **慢日志模式**：算每条语句的扫描比并分级（>10000 严重 / >1000 可疑 / >10 留意），`Lock_time` 占比异常时提示「优先排查行锁」，按 Query_time 倒序输出 TOP 10。
- **SQL 模式**：15 条规则扫描写法问题，按严重/错误/警示/提示四级打分，输出总风险分。

> **静态扫描不代表真实耗时。** 单条 SQL 的实际表现要看 `EXPLAIN ANALYZE` 与慢日志 P95。

---

## 六、人工确认清单（这步不能省）

- [ ] `Lock_time` 高不高？高就先查锁，别改 SQL
- [ ] `Rows_examined` 与 EXPLAIN 的 `rows` 是否同量级（差得多说明统计信息失准）
- [ ] 是否跑过 `ANALYZE TABLE`
- [ ] 改写后的 SQL 在预发用真实数据量验证过吗
- [ ] 加索引会拖慢哪些写入？有没有冗余索引
- [ ] 批量写有没有分批 + 限流 + 可中断
- [ ] 上线后观察至少一个完整业务周期，确认没把别条 SQL 拖慢

---

## 七、最常见的坑

**坑一：一上来就加索引。**
慢的原因可能是锁等待（另一个长事务没提交）、可能是刷脏抖动、可能是备份任务占 IO。先看 `Lock_time` 和发生时间规律。

**坑二：只看单次最慢的 SQL。**
一次执行 30 秒的 SQL，一天跑 2 次；另一条 200ms 的，一天跑 50 万次——后者的总耗时高两个量级。**按总耗时排。**

**坑三：`LIMIT 10000,20` 当成"只查 20 行"。**
MySQL 要扫 10020 行再丢掉前 10000 行。游标分页才是正解；必须跳页时用覆盖索引先取主键再 JOIN 回表。

**坑四：`SELECT *` 顺手改成分页列表。**
更大的行宽意味着更多的回表 IO、更大概率的落盘临时表，也直接堵死覆盖索引这条路。

**坑五：`COUNT(*)` 想绕开又绕错。**
别用 `count(列)` 代替 `count(*)` —— 前者不统计 NULL，语义变了；而且 `count(*)` 早已被优化到自动挑最小的二级索引。真正该问的是**业务侧是否真需要精确值**。

**坑六：依赖 `ORDER BY RAND()`。**
每行算一次随机值再排序，等于全表扫 + filesort。改成随机主键区间取值。

**坑七：批量更新一把梭。**
几十万行的单条 UPDATE，长事务 + undo 暴涨 + 主从延迟 + 锁范围放大。分批 `LIMIT 1000`，并且要能中断、能续跑。

**坑八：` JOIN ` 字段类型和字符集不一致。**
`int` 对 `varchar`、`utf8mb4` 对 `utf8`，被转换的一侧索引直接失效。关联前先对齐类型和排序规则。

**坑九：改完只看一次执行时间。**
要至少观察一个完整业务周期，确认统计信息变化后没把别的 SQL 拖慢，也没因为新索引让写入变慢。

---

## 八、边界与免责

- 本技能给出的是**静态分析与改写建议**，真实效果必须以 `EXPLAIN ANALYZE`、慢日志 P95 与线上观测为准
- MySQL 版本差异（5.6/5.7/8.0）在 Hash Join、CTE 合并、临时表策略上表现不同，**以实际版本为准**
- 生产库的 DDL、批量 DML 属于高风险操作，**必须走变更评审并在预发验证回滚方案**
- 参数调整（`join_buffer_size`、`sort_buffer_size`、`tmp_table_size`）是会话级/全局级影响，**不要盲抄数值**

---

## 九、许可

本技能由 **刘天宝｜墨燊** 原创，采用 **Apache License 2.0**。

`rules/slow_query_tuning.md` 中的阈值（扫描比分级、分批大小、IN 列表上限）为工程经验值，不同数据规模与硬件条件下应重新校准。
