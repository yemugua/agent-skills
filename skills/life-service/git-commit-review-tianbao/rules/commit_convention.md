# Git 提交信息规范（Conventional Commits 落地版）

## 1. 格式

```
<type>(<scope>): <subject>
<空一行>
<body>
<空一行>
<footer>
```

示例：

```
fix(order): 修复退款单重复入账

退款回调重入时未做幂等判断，重复消息会生成两条退款流水。
改为以 refund_no 加唯一索引兜底，并在入口加幂等拦截器。

Refs: PROJ-142
Breaking Change: 否
```

## 2. type 清单（只能取这些）

| type | 用在哪 | 是否触发版本号变更 |
|---|---|---|
| `feat` | 新增用户可见功能 | minor |
| `fix` | 缺陷修复 | patch |
| `perf` | 不改行为的性能改动 | patch |
| `refactor` | 重构，既不修缺陷也不加功能 | —— |
| `style` | 格式、补分号、去空白，**不改语义** | —— |
| `docs` | 只改文档/注释 | —— |
| `test` | 只补测/改测 | —— |
| `build` | 构建系统、依赖、打包配置 | —— |
| `ci` | CI 配置与流水线脚本 | —— |
| `chore` | 上面都放不下的杂项 | —— |
| `revert` | 回滚某次提交，必须写明被回滚的 commit | follow 原提交 |

**禁止自造 type**：`update` / `modify` / `feature` / `bugfix` / `优化` / `wip` 一律不收。
`feature`→`feat`，`bugfix`→`fix`，`优化`要看是否改了行为：`perf` 或 `refactor`。

## 3. scope（可选，但要写对）

- 小写英文单词或短横线：`order`、`trade`、`user-api`、`web`
- 只写一个层级，**不要写 `order/refund/detail`**
- 跨模块改动：不写 scope，或用 `misc`，并在正文里列清楚改了哪几个模块
- 禁止用中文、大写、空格

## 4. subject 硬规则

| 规则 | 口径 |
|---|---|
| 长度 | 建议 ≤ 50 字符，**硬上限 72**（含 type 与 scope） |
| 结尾标点 | **不加句号**，不写 `。` `.` |
| 语序 | 祈使句 / 动词开头：「修复」「新增」「移除」；禁止「修改了」「已处理」 |
| 内容 | 说清**改了什么**，禁止 `update code`、`修复 bug`、`提交代码`、`finish` |
| 语言 | 全团队统一。中文也要**动词开头且不加句号** |
| 大小写 | 英文开头小写（动词原型） |

反例 vs 正例：

| 反例 | 问题 | 正例 |
|---|---|---|
| `修改了登录判断` | 语序不对 | `fix(auth): 修复登录态过期判断错误` |
| `bug fix` | type 非法且无信息 | `fix(cart): 修复购物车数量为 0 时报错` |
| `feat: 新功能上线了。` | 结尾句号 + 无 scope | `feat(order): 新增订单导出 CSV` |
| `update #123` | type 非法 | `chore(deps): 升级 log4j 至 2.17.1` |

## 5. body（什么情况必须写）

**必须写正文的四种情况**（其余可选）：

1. type 为 `feat` / `refactor` / `perf`
2. 属于破坏性变更（`feat!:` / `fix!:` 或 footer 含 `BREAKING CHANGE`）
3. 涉及数据库迁移、支付链路、鉴权逻辑、定时任务
4. `revert` 必须写明被回滚的 commit hash 与回滚原因

正文要求：

- 第一行 before subject 之间必须有一个**空行**
- 每行 ≤ 72 字符
- 三段式：**为什么改 → 改了什么 → 有没有副作用 / 怎么回滚**
- 能贴图/贴日志链接就贴，别只写"已处理"

## 6. footer

| 字段 | 写法 | 说明 |
|---|---|---|
| 工单关联 | `Refs: PROJ-142` / `Closes: #142` | 两者不要混用；能自动关闭工单才用 `Closes` |
| 破坏性变更 | `BREAKING CHANGE: 描述 + 迁移办法` | **必须全大写**，写 `Breaking Change` 不会触发 semver major |
| 影响面 | `Impact: 需同步更新 xxx 服务` | 可选 |
| 协同作者 | `Co-authored-by: Name <mail>` | 结对编程时使用 |

破坏性变更 footer 必须回答三个问题：**改了什么行为、老代码怎么迁移、谁负责推进迁移**。

## 7. 高频錯誤写法速查

| 错误 | 后果 | 正确 |
|---|---|---|
| `Breaking Change: xxx` | 语义化版本工具识别不到，发 patch 包上线后炸 | `BREAKING CHANGE: xxx` |
| `feat!: xxx` 但正文没写 | 没人知道怎么迁移 | `feat!:` + 正文迁移说明 |
| subject 写 `修复 bug` | `git log --oneline` 里全是同一句话，无法定位 | 写明模块与现象 |
| 一个 commit 混两个改动 | `git revert` 时会连带回滚无关代码 | 拆成两个 commit |
| `Closes: #142` 但其实没解决 | 工单被自动关闭，需求丢失 | 未解决用 `Refs:` |
| 合并 pulls 时保留 12 个 fixup commit | 历史全是 `wip` | squash merge |

## 8. 本地配置（一次配好长期受益）

```bash
# 提交模板
git config --global commit.template ~/.gitmessage
# husky / lefthook 做格式门禁（commit-msg hook 校验 type 与长度）
# Commitlint 配置要点
#   subject-case: 不限制（中文团队）
#   header-max-length: 72
#   body-max-line-length: 72
#   type-enum: 上面 11 个
```

配套的 commit-msg hook 之外，再约定一条：**跳过流水线必须在提交里写清原因**。
推荐做法是用 `[skip ci]` 的同时补一行 `Skip-Reason: 仅改注释，全量流水线前一个 commit 已跑过`，
禁止无任何说明地跳过 e2e。
