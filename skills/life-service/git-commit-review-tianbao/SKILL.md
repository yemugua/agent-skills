---
name: git-commit-review
slug: git-commit-review-tianbao
displayName: Git 提交规范与 Code Review
display_name: "Git 提交规范与 Code Review"
display_name_en: "Git Commit Convention and Code Review"
version: "1.0.0"
summary: 按 Conventional Commits 校验提交信息（type 白名单、72 字符上限、正文必填场景、BREAKING CHANGE 大小写），按文件数/改动行数给 PR 分级并指派必审角色，附 A/B/C 三级必审项清单与带级别前缀的评审话术规范。
description: 提交信息写得不规范、PR 太大不知道怎么审、评审意见没人当回事时使用。当用户说"提交信息怎么才算合格""feat 和 fix 怎么区分""这个 PR 八百个文件能合吗""Code Review 应该看什么""评审评论怎么写""BREAKING CHANGE 到底怎么写""为什么我的 PR 挂了三天没人看"时使用。内置 type 白名单与所属 11 类语义、标题长度与祈使句规则、四种必须写正文的场景、footer 白名单与常见拼错对照、PR XS/S/M/L/XL 分级与评审人数要求、A 级拦截项（密钥入库/无迁移方案的破坏性变更/不可回滚的表变更/幂等缺失）与 B 级必审项、blocking/suggestion/nit/question 评论前缀规范，配 scripts/commit_msg_check.py 做提交信息与 PR 尺寸检查。适用于后端/前端/客户端团队的研发与 reviewer。
license: Apache-2.0
author: 刘天宝｜墨燊
category: dev-programming
subCategories:
  - dev-code-quality
icon: icon.svg
tags: [Git, 提交规范, Conventional Commits, Code Review, PR, 代码评审, 提交信息, 版本管理, 研发流程, 代码质量]
language: zh-CN
visibility: public
---

# Git 提交规范与 Code Review（git-commit-review）

提交信息要解决两件事：**半年后能不能看懂**、**能不能自动生成版本号和变更日志**。
Code Review 要解决一件事：**风险控制**，不是风格偏好。

这个技能做三件事：**校格式** → **给 PR 分级** → **给必审项清单**。

---

## 硬边界（先看这条）

| 能做 | 不能做 |
|---|---|
| 校验提交信息格式与 footer 写法 | ❌ 判断这条提交的代码对不对 |
| 按文件数/行数给 PR 分级 | ❌ 决定这个 PR 能不能合（要 owner 批） |
| 列出 A/B/C 级必审项 | ❌ 代替安全审计、性能测试、压测 |
| 提示必审路径与 CODEOWNERS 配法 | ❌ 保证合入无故障 |
| 给出评论话术前缀规范 | ❌ 代替架构设计评审 |

**必须人工拦截的情形：**
- diff 里出现密钥、私钥、真实口令（即便只是测试环境的）
- 数据库不可逆变更（`DROP`、改字段类型）且没有双写过渡
- 支付/退款/库存类改动没有幂等与并发控制
- 引入新依赖却没核对 License
- CI 通过是靠反复 rerun 掩盖偶发失败

---

## 一、什么时候用这个技能

| 用户这样说 | 就用 |
|---|---|
| "提交信息怎么算合格" | ✅ |
| "feat 和 refactor 怎么选" | ✅ |
| "这个 PR 800 个文件能合吗" | ✅ |
| "Code Review 到底看什么" | ✅ |
| "BREAKING CHANGE 写错了会怎样" | ✅ |
| "评审意见没人回怎么办" | ✅ |
| "帮我写测试用例" | ❌ 超出本技能范围 |

---

## 二、完整工作流

```
第 1 步  读规则文件 rules/commit_convention.md 与 rules/code_review.md
第 2 步  导出待检提交：git log --format='%B' -n 30 > commits.txt
第 3 步  跑检查脚本
         python scripts/commit_msg_check.py --file commits.txt \
             --files 42 --additions 1300
第 4 步  按脚本输出的 PR 级别走对应评审流程（ XS/S → 1 人；M → owner；L → 2 人；XL → 拆 PR）
第 5 步  按 rules/code_review.md §2 的 A/B/C 级清单逐项过一遍
第 6 步  评论统一带 [blocking]/[suggestion]/[nit]/[question] 前缀
```

---

## 三、提交信息四件套

**格式**：`<type>(<scope>): <subject>` + 空行 + 正文 + 空行 + footer

**type 只有 11 个**：`feat` `fix` `perf` `refactor` `style` `docs` `test` `build` `ci` `chore` `revert`
（`feature`→`feat`、`bugfix`→`fix`、`优化`看是否改行为→`perf`/`refactor`）

**subject 硬规则**：≤72 字符（建议 ≤50）、**不加句号**、动词开头、不许写「修复 bug」这种无信息量的话

**必须写正文的四种情况**：
1. type 是 `feat` / `refactor` / `perf`
2. 破坏性变更（标题带 `!` 或 footer 有 `BREAKING CHANGE`）
3. 涉及数据库迁移、支付链路、鉴权、定时任务
4. `revert` 必须写明被回滚的 commit

> **footer 大小写是硬伤**：写 `Breaking Change:` 语义化版本工具识别不到，会当普通 patch 发出去。
> 必须全大写 `BREAKING CHANGE:`，且描述里要回答「改了什么、老代码怎么迁移、谁推进迁移」。

---

## 四、PR 尺寸分级 → 评审方式

| 级别 | 判定 | 评审要求 |
|---|---|---|
| XS | ≤5 文件且 ≤30 行 | 1 人 |
| S | ≤15 文件且 ≤150 行 | 1 人 |
| M | ≤30 文件且 ≤500 行 | 1-2 人，含模块 owner |
| L | ≤60 文件或 ≤1500 行 | **2 人 + 测试证据** |
| XL | >60 文件或 >1500 行 | **拆 PR**，不直接合 |

自动生成文件、锁文件、格式化结果**必须单独成 PR**，混进来会把 S 级变 XL 级。

必审路径指派：`pay/refund/settle` → 交易 owner；`auth/permission/token` → 安全 owner；`db/migration`、`*.sql` → DBA + 后端 owner；`Dockerfile`、`k8s/`、`terraform/`、`.github/workflows` → SRE。

---

## 五、脚本用法

```bash
python scripts/commit_msg_check.py --file commits.txt --files 42 --additions 1300
python scripts/commit_msg_check.py --subject "bugfix: 修复退款回调重入问题"
```

| 参数 | 说明 |
|---|---|
| `--file` | 提交信息文本（多条提交用单独一行 `^^^^` 分隔，块内首行标题、其余正文） |
| `--subject` | 只校验单行标题，快速自查 |
| `--files` / `--additions` | PR 改动文件数 / 行数，用于分级 |
| `--json` / `--out` | JSON 输出 / 指定输出文件 |
| `--selftest` | 跑内置自检 |

脚本做四件事：① title 格式与 type 白名单、72 字符、句号结尾、祈使句检查；② 正文必填场景与单行 72 字符检查；③ footer 白名单与**常见拼错对照**（`Breaking Change` / `BREAKING-CHANGE` / `closes` / `Ref` / `Beadline`）；④ PR 分级与必审路径命中。

> 只做静态格式检查。**标题合规不等于代码对了**，这一条必须说清楚。

---

## 六、人工确认清单（这步不能省）

- [ ] diff 里有没有密钥/口令/私钥（`grep -nE 'AKIA|-----BEGIN|password\s*='`）
- [ ] 破坏性变更是否在 footer 里写了迁移办法
- [ ] 表结构变更能不能回滚，有没有双写过渡期
- [ ] 支付/退款/库存类逻辑有没有幂等键
- [ ] 异常被吞（`catch(e){}`）还是正确抛出
- [ ] CI 是不是真绿，有没有靠 rerun 掩盖偶发失败
- [ ] 回滚方式明确了吗（回滚提交 / 关开关 / 数据补偿）

---

## 七、最常见的坑

**坑一：`Breaking Change` 大小写写错。**
语义化版本工具只认全大写 `BREAKING CHANGE`，写错会按 patch 发版，调用方突然炸。这也是 [blocking] 级问题。

**坑二：标题写「修复 bug」「update code」。**
半年后 `git log --oneline` 全是同一句话，`git bisect` 根本没法用。必须写清模块 + 现象。

**坑三：一个 commit 混两个无关改动。**
需要 `git revert` 时会连带回滚无关代码。拆 commit 的成本远低于回滚事故的成本。

**坑四：自动生成物和格式化结果混进业务 PR。**
一个 800 文件的 PR 里 780 个是 lock 文件跳动，评审会直接放弃，真正的逻辑改动没人看。单独发 PR。

**坑五：评审评论没有级别前缀。**
「这里不太对」作者不知道能不能合；`[nit]` 级别的偏好也会被人当成必须修改，来回三轮。强制带 `[blocking]/[suggestion]/[nit]/[question]`。

**坑六：用嘴做 lint。**
评审里反复提没写进 lint 规则的风格偏好，团队会累积怨气。把规则写进 ESLint/Checkstyle，让机器说。

**坑七：prod 配置先改了再说。**
直接动 `application-prod.yml`、K8s ConfigMap，没有开关、没有灰度。生产配置变更必须走配置中心或 PR 双批。

**坑八：别人 approve 了我就 approve。**
批准是连带责任的。没看懂改动就点批准，出事故时一样算在你的评审记录上。

---

## 八、边界与免责

- 本技能提供的是**格式规则与评审清单**，不构成对该次代码变更正确性的判断
- 各团队的 type 白名单、语言习惯、CI 能力不同，**以团队现行规范为准**
- 安全相关（注入、越权、加密）必须由安全专岗复核，本技能只提示检查点
- 数据库变更为不可逆操作，**执行前必须有备份与回滚预案**，不以评审结论替代演练

---

## 九、许可

本技能由 **刘天宝｜墨燊** 原创，采用 **Apache License 2.0**。

`rules/` 中的 type 语义与阈值基于 Conventional Commits 与团队工程实践整理，落地时请结合本仓库现有工具链（commitlint / husky / CODEOWNERS）调整。
