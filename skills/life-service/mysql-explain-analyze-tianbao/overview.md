# MySQL 执行计划 EXPLAIN 解读 · 能力概览

## 你会得到什么

**四列定生死**：把 EXPLAIN 的 12 列压缩到每次必看的 `type` / `key` / `rows` / `Extra`，其余八列用来解释这四个为什么是这样。`type` 给了完整的十二级排序（`system` → `const` → `eq_ref` → `ref` → `range` → `index_merge` → `index` → `ALL`），每一级对应什么场景、到哪一级才算合格都有明确阈值。

**key_len 会算了**。这是大多数人看不懂 EXPLAIN 的卡点。给定索引列的类型与字符集，能算出「用到第几列」应该对应多少字节：INT 4、BIGINT 8、DATETIME 5（5.6+）、VARCHAR(n) 是 n×字符集字节再加 2、可为 NULL 再 +1、utf8mb4 按 4 字节算。看到 `key_len=5` 就知道第三列没用上，而不是只知道"用了索引"。

**Extra 知道该管哪一条**。`Using filesort`、`Using temporary`、`Using join buffer`、`Range checked for each record`、`Impossible WHERE`、`Select tables optimized away` 共 11 项，每项给出处置动作而不是翻译。

**脚本**：`scripts/explain_check.py` 直接吃 mysql 客户端的 EXPLAIN 表格输出（`+---+` 格式或竖线简化格式都支持），解析后按 严重/错误/警示/提示 四级输出诊断；给定 `--cols` 还能反推 key_len 对应到第几列。

## 典型用法

1. 拿到一份 EXPLAIN 不知道怎么看：贴进文件跑一遍，先看分级结论。
2. 怀疑索引只用了部分列：`--cols` 传入索引定义，看脚本反推的列数。
3. 优化前后对比：两次 EXPLAIN 各存一份，对比 rows 与 Extra。
4. 团队教学：把 type 排序表和 key_len 计算表贴在 wiki 上，统一 review 口径。

## 边界

- 解读的是 EXPLAIN 的**估算值**，真实执行请以 EXPLAIN ANALYZE 与慢日志为准
- 版本差异明显：DATETIME 字节数、`EXPLAIN ANALYZE` 可用性、hash join 支持都取决于版本
- 改索引属生产变更，必须走评审并在预发验证回滚方案
- `FORCE INDEX`、`optimizer_switch` 只能作为临时手段，并留整改 TODO
