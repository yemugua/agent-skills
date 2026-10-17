# Git 分支策略选择规则库

> 用法：先看第 1 节选型，再按第 2 节命名，第 3 节生命周期，第 4 节处理冲突。**不要凭印象选型**，按 §1 的四个硬指标打分。

---

## 1. 四种策略的选型依据（按这 4 个硬指标定）

| 硬指标 | 取值 | 指向的策略 |
|---|---|---|
| ① 需要同时维护的线上**版本数** | 只维护 1 个 | Trunk-Based / GitHub Flow / GitLab Flow |
| | 同时有 v1.x、v2.x 都要修 | **GitFlow**（必须能双分支热修） |
| ② 发布节奏 | 每天多次 / 每天 | **Trunk-Based**（分支存活 < 24 小时） |
| | 每周 1-2 次 | GitHub Flow |
| | 按月 / 按季，有固定发版窗口 | GitLab Flow + release 分支 |
| ③ 是否需要多环境分级发布（dev → staging → prod） | 否 | Trunk-Based / GitHub Flow |
| | 是 | **GitLab Flow**（用 env 分支承载环境） |
| ④ 发布失败时能否回滚且不阻塞后续开发 | 要求「随时发、随时回滚」 | Trunk-Based + Feature Flag |
| | 要求「版本冻结、只修缺陷」 | GitFlow release 分支 |

### 1.1 推荐速查

| 场景 | 团队规模 | 推荐 | 分支构成 |
|---|---|---|---|
| SaaS / Web 后端，每天可发 | 1-8 人 | **Trunk-Based** | `main` + 短分支（< 24h）+ Feature Flag |
| Web 前后端，每周发，要有 PR 评审 | 5-25 人 | **GitHub Flow** | `main` + `feature/*` + PR + squash merge |
| ToB 交付，多套客户环境并存 | 10-50 人 | **GitLab Flow** | `main` + `pre-prod` + `prod` + `feature/*`，按环境合并 |
| 客户端 App / 嵌入式 / 中间件，多版本并行维护 | 任意 | **GitFlow** | `master` + `develop` + `feature/*` + `release/x.y.z` + `hotfix/x.y.z` |

### 1.2 明确不建议的组合

| 组合 | 为什么坏 |
|---|---|
| 小团队 + 每天发布 + GitFlow | develop/master 双主干 + release 分支，每次发布要合 3 处，merge 次数是 GitHub Flow 的 4 倍以上 |
| CDN/静态站 + Trunk-Based 但无 Feature Flag | 半成品代码上线后无法关闭，只能回滚整站 |
| 多版本并行的 SDK 用 GitHub Flow | v1.2 的热修合回 main 时，会把 v2.0 的破坏性变更一起带给老用户 |
| 50 人团队共用 develop，无 CI 门禁 | develop 长期处于红/黄状态，谁都不知道能不能发 |

---

## 2. 分支命名与作用（强制）

| 前缀 | 用途 | 命名格式 | 示例 |
|---|---|---|---|
| `feature/` | 新功能 | `feature/<工单号>-<小写短横线简述>` | `feature/PROJ-142-order-refund` |
| `fix/` | 非紧急缺陷 | `fix/<工单号>-<简述>` | `fix/PROJ-203-null-pointer` |
| `hotfix/` | 线上紧急修复，跳过常规发布流程 | `hotfix/<版本号>` | `hotfix/2.7.1` |
| `release/` | 版本冻结 / 发布窗口 | `release/<语义化版本>` | `release/3.0.0` |
| `chore/` | 依赖升级、CI 配置、文档 | `chore/<简述>` | `chore/bump-webpack5` |
| `experiment/` | 明确不打算合入的验证分支 | `experiment/<简述>` | `experiment/grpc-migration` |

### 命名硬规则

- 只允许 `[a-z0-9._/-]`，**禁止大写字母、空格、中文、下划线混用具名**
- 长度 ≤ 60 字符（`git describe`、CI 名称、镜像 tag 都会截断）
- 必须以工单号开头（能用脚本批量清理已关闭工单的分支）
- 禁止用个人信息命名（`feature/zhang-new`，人走了没人敢删）
- 保护分支白名单：`main` / `master` / `develop` / `release/*` —— 禁止 push，只允许 PR 合入

---

## 3. 分支生命周期（超时就要处理）

| 分支类型 | 建议存活上限 | 超时处置 |
|---|---|---|
| `feature/*` | **3 天**（Trunk-Based 要求 24 小时内） | 拆分子任务；或先同步主干 `git rebase origin/main` 再重开 PR |
| `fix/*` | 2 天 | 同上 |
| `hotfix/*` | 1 天 | 超时说明故障定位没做完，先在 PR 里记录现状 |
| `release/*` | 14 天 | 冻结期超过 2 周，说明发版流程有问题，应缩短窗口 |
| `experiment/*` | 30 天 | 30 天未合入直接删除（代码已存在 ILFS/PR 里） |

清理命令（先查，再删，别直接 `-D`）：

```bash
# 查看哪些分支已经合入主干（安全可删）
git branch --merged origin/main | grep -E 'feature/|fix/|hotfix/|chore/'
# 查看落后的分支数量（判断是否长期不同步）
git for-each-ref --format='%(refname:short) %(committerdate:short)' refs/heads
# 级联删除本地已合入的 <旧前缀> 分支
git branch --merged origin/main | grep '^  feature/' | xargs -r git branch -d
```

---

## 4. 合并冲突：先分类，再处理

### 4.1 冲突类型 → 处理方式

| 冲突类型 | `git status` 里的表现 | 处理方式 |
|---|---|---|
| **content**（内容冲突，最常见） | `both modified: xxx` | 手工编辑冲突段，或用 `--ours` / `--theirs` 二选一 |
| **add/add**（双方都新建同名文件） | `both added: xxx` | 二选一，或把两份内容手工合并成一份 |
| **modify/delete**（一边改一边删） | `deleted by us: xxx` | 明确「要删」还是「要留」：`git rm xxx` 或 `git checkout --ours xxx` |
| **rename/modify** | `renamed: old -> new` | 多数情况 Git 能自动合；合不了时配 `merge.conflictStyle diff3` 看三方差异 |
| **binary**（二进制文件） | `both modified: a.xlsx` | **无法行级合并**，必须 `git checkout --ours a.xlsx` 或 `--theirs` 二选一，再人工补数据 |
| **submodule**（子模块指针漂移） | `both modified: vendor/sdk` | 进子模块目录 checkout 到目标 commit，再回主仓 add |
| **merge commit 本身冲突**（octopus / 二次合并） | `UU` 出现在合并提交上 | 先 `git merge --abort` 重来，不要在一棵已经 merge 过的树上接着 merge |

### 4.2 定位冲突来源（改之前必须先看）

```bash
# 1) 只列出冲突文件（比 git status 干净）
git diff --name-only --diff-filter=U
# 2) 看某个文件两边各自的改动历史（谁写的、什么时候）
git log --merge -p -- path/to/file
# 3) 打开 diff3 风格，能同时看到「共同祖先版本」（强烈建议配成默认）
git config --global merge.conflictStyle diff3
# 4) 看冲突块数量，判断工作量
grep -c '^<<<<<<<' path/to/file
```

### 4.3 二选一时的正确命令（两种别混）

| 目的 | 命令 | 生效范围 |
|---|---|---|
| 只解决冲突块，保留对方的其他改动 | `git checkout --theirs path/to/file` | **整个文件**取对方版本 |
| 只把冲突块判给对方 | `git merge -X theirs feature/x` | 仅冲突行，非冲突改动仍合并 |
| 整个文件取本分支 | `git checkout --ours path/to/file` | 整个文件 |
| 合并时整体策略偏向本分支（**危险**） | `git merge -X ours feature/x` | 冲突行全用我方，**对方在别处的删除/重命名也会丢** |

> ⚠️ `-X ours` / `-X theirs` 与 `--ours` / `--theirs` **不是一回事**。前者是合并策略开关（只在冲突点生效），后者是 checkout 某个 stage（覆盖整个文件）。用错会静默丢代码。

### 4.4 中止重来（比硬着头皮改更省时间）

```bash
git merge --abort      # 取消本次 merge
git rebase --abort     # 取消本次 rebase
git cherry-pick --abort
```

### 4.5 重复冲突：`git rerere`（非常值得开）

同一个长期分支反复和测试/发布分支冲突时：

```bash
git config --global rerere.enabled true   # 全局开启，记录解决过的话术
git config --global rerere.autoupdate true # 自动暂存已自动解决的冲突
```

开启后，第二次遇到相同冲突会自动按上次解法处理，`git rerere diff` 可查看记录。
**注意**：rerere 只记录方案，不保证方案还正确；风险分支合入前要人工确认一次。

---

## 5. merge 还是 rebase（取舍条件）

| 条件 | 选 merge | 选 rebase |
|---|---|---|
| 分支已经 push 到远端并被他人拉取 | ✅ 必须 | ❌ 禁止（会改写他人基于旧 commit 的历史） |
| 追求线性历史、便于 `git bisect` | ❌ | ✅ |
| 需要保留「这个功能是一整块合进来的」语义 | ✅（`--no-ff`） | ❌（会摊平成多个 commit） |
| CI 对每个 commit 都要跑全量流水线 | ❌（rebase 会重跑） | 视情况 |
| 分支上有 **merge commit** | —— | ❌ 别 rebase，`--rebase-merges` 会翻车 |

推荐组合：**个人未推送分支用 `git pull --rebase`（配 `pull.rebase=true`），合入主干用 `git merge --no-ff`（保留功能块）**。

```bash
git config --global pull.rebase true          # 拉主干时自动变基
git config --global push.default current
```

---

## 6. 从根上减少冲突的配置

### 6.1 换行符（Windows + Linux 混合团队的高频元凶）

```gitattributes
# 统一用 LF 入库，检出时按平台转换
* text=auto eol=lf
*.bat text eol=crlf
*.sh  text eol=lf
*.png binary
*.jar binary
*.xlsx binary
```

修改后执行 `git add --renormalize .`，否则存量文件会在下次编辑时整文件变冲突。

### 6.2 禁止生成物入库

```gitignore
dist/
build/
*.min.js
package-lock.json.bak
*.class
target/
node_modules/
```

**生成物一旦入库，每次重新生成都会全量冲突。**

### 6.3 锁类文件的合并策略

```gitattributes
package-lock.json merge=binary     # 冲突时强制二选一，避免合出一个装不上的树
yarn.lock         merge=binary
poetry.lock       merge=binary
```

### 6.4 评审与门禁

- `.github/CODEOWNERS`：核心模块（支付/鉴权/迁移脚本）必须指定 owner 才能合
- CI 强制：单元测通过 + lint 无错 + 代码围栏检查，任一项不过不许合
- 保护分支：`require linear history`（若采用 rebase 流）、`delete branch on merge`

---

## 7. 冲突处理的标准动作序列（照着走）

```
1  git status                                  # 确认处于冲突态
2  git diff --name-only --diff-filter=U        # 拿到冲突文件清单
3  git log --merge -p -- <file>                # 看清两边在干什么
4  逐文件处理：  文本 → 手工合并；二进制 → --ours/--theirs 二选一
5  grep -rn '^<<<<<<<' .                       # 全局确认标记清干净（含不同 unicode 变体）
6  git add <file>                              # 千万别 git add . 把 .orig 加进去
7  git diff --cached --check                   # 检查空白/合并标记残留
8  git commit  /  git rebase --continue
9  跑一遍单测 + lint                            # 冲突合并常常只崩一小处语义
10 git push（rebase 过则需要 --force-with-lease，禁止 --force）
```

> `git mergetool` / IDE 合并视图会生成 `*.orig` 备份文件，务必先执行
> `git config --global mergetool.keepBackup false` 或事后清理。
