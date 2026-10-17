---
name: english-interview-check
slug: english-interview-check-tianbao
displayName: 英文面试自我介绍与常见问题核查
display_name: "英文面试自我介绍与常见问题核查"
display_name_en: "English Interview Self-Introduction and Common Questions Check"
version: "1.0.0"
summary: 按 Present-Past-Future 三段核查自我介绍时长与词数，按 STAR 四要素核查经历类问题回答结构，覆盖八类常见问题的回答骨架与 10 条失分点。
description: 准备英文面试、写完自我介绍不知道行不行、被问到项目经历不知道怎么组织时使用。当用户说"英文自我介绍怎么说""面试自我介绍多久合适""英文面试常见问题有哪些""怎么回答你的缺点""用英文讲一个项目经历""STAR 怎么用""面试最后该问什么""英文面试紧张说不利索怎么办"时使用。内置自我介绍三段结构与词数语速硬指标、STAR 四要素配比、八类常见问题回答骨架、10 条错误答法与正确答法对照，配 scripts/english_interview_check.py 做自我介绍时长语速与 STAR 结构自检。适用于求职者、应届生、外企候选人与求职辅导者。本技能只做回答结构梳理与练习核查，不代替面试结果。
license: Apache-2.0
author: 刘天宝｜墨燊
category: education
subCategories:
  - edu-study-methods
  - edu-exam-prep
icon: icon.svg
tags: [英文面试, 自我介绍, 面试英语, STAR, 外企面试, 求职, 常见问题, 行为面试, 口语表达]
language: zh-CN
visibility: public
---

# 英文面试自我介绍与常见问题核查（english-interview-check）

英文面试里最容易被低估的部分是**自我介绍的时长**：说 30 秒显得单薄，说 3 分钟面试官已经开始走神。合理区间是 **60~90 秒、约 130~180 词**。

经历类问题看 **STAR 四要素**：Situation、Task、Action、Result。四要素里 **Action 要占一半以上**，Result 要能说清结果。

这个技能做三件事：**核自我介绍的时长与词数** → **核 STAR 四要素与配比** → **按八类问题给回答骨架**。

---

## 硬边界（先看这条）

| 能做 | 不能做 |
|---|---|
| 给出自我介绍的三段结构与硬指标 | ❌ 保证拿到 offer |
| 核查时长、词数、语速是否达标 | ❌ 替你参加面试或代写英文回答 |
| 按 STAR 核查经历类回答的要素与配比 | ❌ 建议编造项目经历与数据 |
| 给出八类问题的回答骨架 | ❌ 判断是否该接受某个薪资或条款 |
| 输出练习顺序与自查清单 | ❌ 提供具体的行业薪资数字 |

**出现以下情况先停下来，别照着模板硬套：**
- 涉及薪资、工时、试用期、竞业限制等**劳动条款** —— 以用人单位正式文件与当地现行规定为准，本技能不提供具体条款与数字
- 被要求描述**不属于自己的项目成果** —— 一律改为说明自己在其中的角色
- 面试官明确要求中文回答 —— 不要为了展示英语硬用英文
- 涉及简历上未写的内容 —— 先确认要不要补充进简历，避免面试与简历不一致

---

## 一、什么时候用这个技能

| 用户这样说 | 就用 |
|---|---|
| "英文自我介绍怎么说" | ✅ |
| "自我介绍说多久合适" | ✅ |
| "英文面试常见问题有哪些" | ✅ |
| "怎么回答你的缺点" | ✅ |
| "用英文讲一个项目经历" | ✅ |
| "STAR 到底怎么用" | ✅ |
| "面试最后该问什么" | ✅ |
| "帮我把这段自我介绍背下来就行了吧" | ❌ 背稿会在追问时崩，需理解结构 |
| "帮我编一个项目数据" | ❌ 不编造经历与数据 |

---

## 二、完整工作流

```
第 1 步  确认场景（社招 / 校招 / 外企 / 技术岗 / 非技术岗）与面试轮次
第 2 步  先读 rules/self_intro.md，按 Present-Past-Future 三段写出自我介绍
第 3 步  读 rules/star_and_questions.md，抄下八类问题的回答骨架
第 4 步  计时录音，记录秒数与词数，跑体检脚本
         python scripts/english_interview_check.py --intro-words 165 --intro-seconds 75
         python scripts/english_interview_check.py --star-parts situation,task,action,result \
             --action-ratio 0.6 --result-numbers 2
第 5 步  看脚本给出的语速判定与 STAR 缺口，按 §4 修
第 6 步  填 templates/回答自查表.md，记录每题的要素覆盖与时长
第 7 步  做完自我介绍后自问三个追问，确认追问不会崩
```

---

## 三、自我介绍三段结构

| 段落 | 内容 | 建议篇幅 |
|---|---|---|
| Present | 现在是谁、当前角色、核心方向 | 约 20% |
| Past | 1~2 个与目标岗位相关的关键经历 + 结果 | 约 50% |
| Future | 为什么来这个岗位 / 这家公司 | 约 20% |
| 收尾 | 一句开放的过渡句 | 约 10% |

**硬指标**：时长 60~90 秒，词数 130~180 词，语速 120~160 词/分钟。

> 语速低于 100 词/分钟会显得不熟练，高于 180 词/分钟会听不清；宁可慢一点，也不要快到需要听者费力。

---

## 四、STAR 四要素与配比

| 要素 | 内容 | 建议占比 |
|---|---|---|
| Situation | 背景是什么 | 约 15% |
| Task | 你要解决什么 | 约 15% |
| Action | **你具体做了什么** | **50%~70%** |
| Result | 结果如何，最好量化 | 约 20% |

**三条判定**：
1. 缺 Result —— 判定为"没说结果"，等于经历讲了一半
2. Action 占比低于 40% —— 判定为"在讲背景不是在讲自己"
3. Result 没有数字 —— 判定为"结果不够具体"，补一个可核验的量

---

## 五、八类常见问题速查

| 类别 | 典型问题 | 回答要点 |
|---|---|---|
| 动机类 | Why this company / Why this role | 具体说公司或岗位的哪一点吸引你，不要泛泛说"平台好" |
| 能力类 | What are your strengths / weaknesses | 优点配例子；缺点选真实且已改善的，并说改进行动 |
| 经历类 | Tell me about a project / a challenge | 用 STAR，Action 占一半以上 |
| 冲突类 | How do you handle conflict | 讲事实与处理方式，不评价对方人品 |
| 压力类 | How do you handle pressure | 讲具体的应对机制，不是"我很抗压" |
| 职业类 | Where do you see yourself in 5 years | 与岗位路径一致，不要说"想创业" |
| 反问类 | Do you have any questions | **必须有问题**，问团队、问岗位、问成功标准 |
| 薪资类 | What are your expectations | 给区间并说明可谈，具体条款以用人单位正式文件为准 |

---

## 六、脚本用法

```bash
python scripts/english_interview_check.py --intro-words 165 --intro-seconds 75
python scripts/english_interview_check.py --star-parts situation,task,action,result \
    --action-ratio 0.6 --result-numbers 2
```

| 参数 | 说明 |
|---|---|
| `--intro-words` | 自我介绍词数 |
| `--intro-seconds` | 自我介绍秒数 |
| `--star-parts` | STAR 已覆盖要素，逗号分隔，如 `situation,task,action,result` |
| `--action-ratio` | Action 部分占比（0~1） |
| `--result-numbers` | 结果部分出现的可量化数字个数 |
| `--out` / `--format` | 输出文件路径 / `md`（默认）或 `json` |
| `--selftest` | 跑内置自检 |

脚本做四件事：① 算语速并判是否在 120~160 词/分钟；② 核词数与时长是否落在建议区间；③ 核 STAR 四要素是否齐全并标出缺口；④ 核 Action 占比与 Result 量化情况。

> 语速与配比是**练习指标**，不是面试评分标准；面试官的评价维度以实际岗位要求为准。

---

## 七、人工确认清单（这步不能省）

- [ ] 自我介绍是否逐字背稿（背稿在追问时会崩）
- [ ] Past 段是否只挑了 1~2 个与目标岗位相关的经历
- [ ] STAR 的 Action 是不是"我做了什么"，而不是"我们做了什么"
- [ ] Result 有没有可核验的量
- [ ] 反问环节是否至少准备了 2 个问题
- [ ] 简历上写的内容与口述是否一致
- [ ] 涉及薪资与工时等条款的部分，是否以用人单位正式文件与当地现行规定为准

---

## 八、最常见的坑

**坑一：自我介绍背稿。**
错误答法：逐字背诵一段 3 分钟稿子；正确答法：只记三段的关键词，每次用词可以不同。背稿一旦被打断或追问，就会卡在原文里接不上。

**坑二：自我介绍超时。**
错误答法：从大学讲到现在，讲了 3 分钟还在说第一份实习；正确答法：60~90 秒，Past 段只挑 1~2 个相关经历。

**坑三：经历题讲背景不讲自己。**
错误答法："The project was very large and the team had 20 people..."（Situation 占了 70%）；正确答法：背景一句带过，Action 占 50%~70%，说清"我做了什么"。

**坑四：STAR 缺 Result。**
错误答法：讲完 Action 就停；正确答法：补一句结果，最好带一个可核验的量。

**坑五：缺点说成致命缺陷。**
错误答法："My weakness is that I often miss deadlines."；正确答法：选真实且已在改善的缺点，说明具体改进行动，如"I used to take on too much at once; I now use a weekly priority list."

**坑六：反问环节说没有。**
错误答法："No, I have no questions."（浪费了最后一个展示机会）；正确答法：准备 2~3 个关于团队、岗位成功标准、近期挑战的问题。

**坑七：动机题答得太泛。**
错误答法："Your company is very famous and has a great platform."；正确答法：指出具体的产品线、技术方向或团队做法，并说明与自己的关联。

**坑八：五年规划说想创业。**
错误答法："In five years I want to start my own company."；正确答法：与岗位路径一致，说明想在这个方向上深入。

**坑九：把团队成果说成个人成果。**
错误答法：把团队做的功能全说成自己做的；正确答法：说清自己在其中的角色与贡献，用"I was responsible for..."而不是"We built..."。

**坑十：语速失控。**
错误答法：紧张时越说越快，180 词/分钟以上；正确答法：控制在 120~160 词/分钟，允许短暂停顿。

**坑十一：用大词炫技。**
错误答法：硬塞 leverage、synergy、paradigm shift 这类词；正确答法：用准确的动词与具体名词，面试官要的是清楚。

**坑十二：不准备追问。**
错误答法：只准备自我介绍本身；正确答法：写完自我介绍后自问三个追问（为什么这么做、结果怎么衡量、有没有更好的做法）。

---

## 九、边界与免责

- 本技能给出的是**回答结构梳理与练习核查**，不构成面试通过的任何承诺
- 不同行业、岗位、轮次的面试形式差异很大，实际要求**以用人单位的面试安排为准**
- 涉及薪资、工时、试用期、竞业限制等劳动条款，以**用人单位正式文件与当地现行规定为准**，本技能不提供具体条款与行业薪资数字
- 本技能不代写虚假经历、不提供任何违背诚信的做法

---

## 十、许可

本技能由 **刘天宝｜墨燊** 原创，采用 **Apache License 2.0**。

`rules/self_intro.md` 与 `rules/star_and_questions.md` 中的时长、词数、语速与 STAR 配比为常见面试准备的整理，不同岗位与文化差异较大，落地前请结合目标岗位调整；失分点为经验总结，请结合自身实际使用。
