---
name: git-branch-strategy
slug: git-branch-strategy-tianbao
displayName: Git 分支管理与合并冲突处理
display_name: "Git 分支管理与合并冲突处理"
display_name_en: "Git Branch Strategy and Merge Conflict Resolution"
version: "1.0.0"
summary: 按「并行版本数 / 发布节奏 / 环境级数 / 回滚方式」四项硬指标选定分支策略，核对分支命名与生命周期，给出 content/add-add/modify-delete/binary 六类冲突的具体处理命令与预防配置。
description: 团队要定 Git 分支策略、一堆分支该清理谁、合并冲突炸了怎么处理时使用。当用户说"我们团队该用 GitFlow 还是主干开发""分支怎么命名""这个冲突谁改了我要留谁的""rebase 还是 merge""同样的冲突每次都要解一遍""release 分支拖了三周怎么办"时使用。内置四策略选型依据表、分支命名硬规则、生命周期上限、冲突类型-处置对照表、-X ours 与 --ours 的差异说明、rerere 与 .gitattributes 防冲突配置，配 scripts/git_branch_check.py 做分支清单体检。适用于后端/前端/客户端团队的技术负责人、研发工程师与 DevOps。本技能只做策略建议与命令指引，不代替现场 git 操作。
license: Apache-2.0
author: 刘天宝｜墨燊
category: dev-programming
subCategories:
  - dev-code-quality
icon: icon.svg
tags: [Git, 分支策略, GitFlow, 主干开发, 合并冲突, rebase, branch, 版本发布, 代码管理, 研发流程]
language: zh-CN
visibility: public
---

# Git 分支管理与合并冲突处理（git-branch-strategy）

分支策略选型看 **四个硬指标**：并行维护几个版本、多久发一次、有几级发布环境、发布失败怎么回滚。
冲突处理看 **冲突类型**：是内容冲突还是树结构冲突（add-add / modify-delete），处理方式完全不同。

这个技能做三件事：**选策略** → **核分支命名与生命周期** → **按类型拆冲突**。

---

## 硬边界（先看这条）

| 能做 | 不能做 |
|---|---|
| 按四项指标推荐分支策略 | ❌ 代替团队对发布流程的决策与责任 |
| 核对分支命名是否合规范 | ❌ 代替你在仓库里执行 merge/rebase |
| 给出每类冲突的处理命令 | ❌ 自动解决冲突（语义冲突只能人看） |
| 提示 `-X ours` / `--ours` 的语义差异 | ❌ 保证不丢代码 |
| 输出清理/终止/重来命令 | ❌ 建议对已推送并被他人拉取的分支做变基 |

**出现以下情况先停下来，别照着命令一路敲：**
- 冲突文件是**二进制**（表格、图片、pb/thrift 生成的源码）—— 选边后必须人工补数据
- 冲突涉及**数据库迁移脚本 / 支付与鉴权代码** —— 必须 owner 参与评审
- 冲突数量超过 30 个文件 —— 大概率是长期分支没同步，应先终止并拆分 PR
- 准备执行 `--force` —— 一律改用 `--force-with-lease`

---

## 一、什么时候用这个技能

| 用户这样说 | 就用 |
|---|---|
| "我们该用 GitFlow 还是主干开发" | ✅ |
| "这些分支哪些该删了" | ✅ |
| "冲突了，我要保留对方的怎么弄" | ✅ |
| "每次拉分支都要解一遍同样的冲突" | ✅ |
| "release 分支冻了两周还没上线" | ✅ |
| "rebase 会把历史搞乱吗" | ✅ |
| "帮我把这个 PR 直接合了" | ❌ 需要人工评审 |

---

## 二、完整工作流

```
第 1 步  收集四个指标：并行版本数 / 发布节奏 / 环境级数 / 回滚方式
第 2 步  先读规则文件 rules/branch_strategy.md，再套 §1 选型表
第 3 步  导出分支清单（见下方命令）并跑体检脚本
         python scripts/git_branch_check.py --file branches.txt --as-of 2026-10-08 \
             --versions 1 --cadence weekly --stages 1 --rollback freeze --team 12
第 4 步  按脚本给出的高冲突风险分支，先同步主干再合并
第 5 步  冲突发生时按 §4.1 判定类型，按 §4.3 选命令，按 §7 序列收尾
第 6 步  把防冲突配置（.gitattributes / rerere / CODEOWNERS）落到仓库
第 7 步  填 templates/merge_conflict_record.md，记录根因与改进动作
```

导出分支清单：

```bash
git for-each-ref --sort=committerdate \
  --format='%(refname:short)|%(committerdate:short)|%(ahead-behind:origin/main)' \
  refs/heads > branches.txt
```

> `%(ahead-behind:X)` 输出的是「领先 落后」两个数字，正好对应脚本第 3、4 列。

---

## 三、策略选型速查（四指标 → 策略）

| 并行版本数 | 发布节奏 | 环境级数 | 回滚方式 | 推荐 |
|---|---|---|---|---|
| ≥2 | 任意 | 任意 | 任意 | **GitFlow** |
| 1 | daily | 1 | anytime | **Trunk-Based** |
| 1 | weekly | 1 | 任意 | **GitHub Flow**（main + 短 feature 分支 + PR） |
| 1 | monthly / quarterly | ≥2 | freeze | **GitLab Flow**（环境分支承载） |
| 1 | monthly | 1 | freeze | **GitLab Flow** + release 分支 |

**不建议的组合**（规则文件 §1.2 有完整说明）：
小团队日更却用 GitFlow（每次发版要合 3 处）、多版本 SDK 用 GitHub Flow（热修会把 v2 破坏性变更带给 v1 用户）、无 CI 门禁的大团队共用 develop。

---

## 四、冲突怎么拆（关键）

先 `git diff --name-only --diff-filter=U` 拿到清单，再判定类型：

| 类型 | 表现 | 处理 |
|---|---|---|
| content | `both modified` | 手工编辑冲突段 |
| add/add | `both added` | 二选一或手工合成一份 |
| modify/delete | `deleted by us` | `git rm` 或 `git checkout --ours` |
| binary | `.xlsx` / `.png` / 生成代码 | **只能选一边**，再人工补数据 |
| submodule | `both modified: vendor/sdk` | 进子模块 checkout 目标 commit |
| merge commit 冲突 | 合并提交上出现 UU | `--abort` 重来 |

三个必记命令差异：

| 命令 | 生效范围 |
|---|---|
| `git checkout --ours f` | **整个文件**取本分支 |
| `git merge -X theirs b` | 只在**冲突行**判给对方，其余照改 |
| `git merge -X ours b` | 冲突行全用我方，**对方的删除/重命名也会丢** |

> `-X` 是合并策略开关，`--ours` 是 checkout 某个 stage，两者**不是一回事**，用错会静默丢代码。

---

## 五、脚本用法

```bash
python scripts/git_branch_check.py --file branches.txt --as-of 2026-10-08 \
    --versions 1 --cadence weekly --stages 1 --rollback freeze --team 12
```

| 参数 | 说明 |
|---|---|
| `--file` | 分支清单（每行：分支名 / 最后提交日期 / 领先数 / 落后数，Tab 或 `|` 分隔） |
| `--as-of` | 基准日 `YYYY-MM-DD`，默认今天，用于算分支是否超期 |
| `--versions` | 并行维护的线上版本数，默认 1 |
| `--cadence` | `daily` / `weekly` / `monthly` / `quarterly` |
| `--stages` | 发布环境级数，≥2 表示有 staging/pre-prod |
| `--rollback` | `anytime`（随时回滚）/ `freeze`（版本冻结） |
| `--team` | 团队人数，用于提示人力是否匹配策略 |
| `--json` / `--out` | JSON 输出 / 指定输出文件 |
| `--selftest` | 跑内置自检 |

脚本做三件事：① 按四指标推荐策略并给出依据；② 逐分支核命名（大写、下划线、中文、超长、缺工单号、非法前缀）；③ 按「落后数 + 领先数」算冲突风险等级并给处理建议。

> 冲突风险只是**概率提示**：落后 520 个提交一定高危，但不等于一定冲突；反过来零差异也不代表合完能编译。

---

## 六、人工确认清单（这步不能省）

- [ ] 高冲突风险分支是否已先 `git pull --rebase origin main` 同步过
- [ ] 冲突文件里有没有二进制/生成代码，是不是被静默二选一了
- [ ] `grep -rn '^<<<<<<<' .` 是否为空（含 IDE 残留的 `.orig`）
- [ ] 用 `-X ours` 之前，是否确认过对方在本文件里的删除/重命名不想要
- [ ] release 分支冻结期超过 14 天，是否有人负责通气
- [ ] 删除分支前是否已用 `git branch --merged origin/main` 确认合入（**必须带上 origin/main 参数**）
- [ ] 变基过的分支是否已推送过——推送过就**不许**再变基

---

## 七、最常见的坑

**坑一：`-X ours` 和 `--ours` 混用。**
前者只对冲突行生效，后者直接覆盖整个文件。用后者处理一个 2000 行的文件，会把对方在非冲突区的修改整段删掉，而且 **git 不会报错**。

**坑二：对已推送并被他人拉取的分支执行 rebase。**
本地历史被改写后，别人 push 时会分叉，他一把基金 `--force` 上去就把你的 commit 冲掉了。一律用 `--force-with-lease`。

**坑三：没清理冲突标记就提交了。**
冲突标记偶而能编译通过（被注释吞掉、或落在模板字符串里）。每次合并完必须 `grep -rn '^<<<<<<<' .` 与 `git diff --cached --check`。

**坑四：二进制冲突当文本合并。**
表格/图片/codegen 输出没法行级合并，必须 `git checkout --ours/--theirs` 选一边，再人工把另一侧的修改补回去。合并视图里显示"已解决"不代表内容对。

**坑五：换行符没统一。**
Windows 团队 checkout 出 CRLF，Linux 提交 LF，一次格式化就会整文件冲突。先在 `.gitattributes` 写 `* text=auto eol=lf`，再 `git add --renormalize .`。

**坑六：生成物入库。**
`dist/`、`*.min.js`、锁文件的临时副本一旦进版本库，每次重新构建都会全量冲突。加 `.gitignore`，并给 `package-lock.json` 设 `merge=binary`。

**坑七：同一个长期分支反复解同样的冲突。**
开 `git config --global rerere.enabled true`，Git 会记住你的解法。但要定期 `git rerere diff` 抽查——记的是上个方案，不一定还适合本次上下文。

**坑八：release 分支长期冻结。**
冻结超过两周，说明分支策略与发布节奏不匹配（通常是缺少 Feature Flag 或环境分支），应缩短发布窗口，而不是继续往 release 里堆自动修复。

---

## 八、边界与免责

- 本技能给出的是**策略建议与命令指引**，不构成发布决策，也不能保证不丢代码
- Git 客户端版本、平台（GitLab/GitHub/Gitea）的保护分支规则、CI 门禁能力各不相同，**以现场实际配置为准**
- 涉及已推送历史的改写操作（rebase / reset / amend / force push），**执行前先备份分支**：`git branch backup/<分支名>-<日期>`
- 数据库迁移、支付与鉴权相关冲突，必须由模块 owner 参与评审，不以脚本结论代替人工判断

---

## 九、许可

本技能由 **刘天宝｜墨燊** 原创，采用 **Apache License 2.0**。

`rules/branch_strategy.md` 中的策略与阈值为工程实践整理，不同团队规模、发布流程、平台版本会有差异，落地前请结合团队实际情况调整。
