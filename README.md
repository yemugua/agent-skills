[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-14%2C232-blue)](https://github.com/yemugua/agent-skills)
[![Platform](https://img.shields.io/badge/works%20on-Claude%20%7C%20Codex%20%7C%20Cursor%20%7C%20Gemini%20%7C%2055%2B%20agents-orange)](https://skills.sh)
[![Mirror](https://img.shields.io/badge/国内镜像-Gitee-red)](https://gitee.com/liu-tianbao9088/agent-skills)

> **🇨🇳 16,808 个中文 AI Agent 技能库** · **The largest Chinese AI Agent Skills collection** · Free · MIT

# Agent Skills 中文技能库（Chinese AI Agent Skills）

**English:** The largest open collection of Chinese-life AI agent skills — 16,808 SKILL.md packages covering daily-life services in China: government services, social insurance, real estate, healthcare, pets, cars, weddings, funerals, side hustles, elder care, consumer rights and more. Works with Claude Code, Codex CLI, Cursor, Gemini CLI, Copilot and 55+ agents reading the open SKILL.md standard.

**一键安装 / One-line install:**
```bash
npx skills add yemugua/agent-skills          # GitHub (global)
npx skills add yemugua/agent-skills --skill '*' -a claude-code   # 只装进 Claude Code
git clone https://gitee.com/liu-tianbao9088/agent-skills.git    # 国内镜像（无需科学上网）
```

## 📦 品类覆盖 / Categories

life-service (10865) · side-hustle (344) · real-estate (190) · pet-disputes (160) · baby-consumer (152) · vehicle-services (144) · elder-care (144) · funeral-services (128) · renovation (128) · medical-beauty (128) · fitness-consumer (112) · accessibility (110)

**共 43 个品类 / 43 categories** —— 精选导览见 [FEATURED.md](FEATURED.md) · 完整统计 [STATS.md](STATS.md) · 全量索引 [manifest.json](manifest.json)

## 🇨🇳 特色 / Why Chinese Life Skills

- **全网独一份**：政务办理、社保医保、涉农补贴、殡葬白事、军属优待、维权报案……这些"中国人一生必办"的场景，海外技能库完全空白
- **强意图选题**：每个技能对应一个真实办事/消费/维权场景，含材料清单、办理时限、费用行情、避坑与维权路径
- **每周更新**：流水线自动生成→审核→上架，持续补充新品类

# Agent Skills 中文技能库（Chinese AI Agent Skills）

目前**最大规模之一的中文 Agent Skills 开源合集**：**16,808 个 SKILL.md 技能**，覆盖life-service(10489)、real-estate(190)、funeral-services(128)、accessibility(110)、consumer-rights(110)、wechat-ecosystem(102)、veterans(72)、pet-disputes(72)等 20 个品类高频场景。
适用于 **Claude Code、Claude、Codex CLI、Cursor、OpenCode、Windsurf、Cline** 等所有支持 Anthropic Agent Skills 规范的 AI 编程工具与 Agent 框架。

## ⚡ 快速安装（三种方式）

### 方式一：Git 克隆（推荐）
```bash
git clone https://gitee.com/liu-tianbao9088/agent-skills.git
cp -r agent-skills/skills/life-service/<技能名> ~/.claude/skills/   # Claude Code / Claude Desktop
```

### 方式二：只拉单个技能
```bash
# 用浏览器直接打开对应 SKILL.md 复制内容，保存为 ~/.claude/skills/<技能名>/SKILL.md 即可
```

### 方式三：给 AI Agent 的自动安装指令
```text
请从 https://gitee.com/liu-tianbao9088/agent-skills 仓库的 skills/ 目录下载 <技能名> 并安装到我的技能目录
```

## 🔍 这个库里有什么（按搜索热词索引）

| 你想找 | 对应分类 | 数量 |
|---|---|---|
| 微信小程序、公众号、视频号、微信支付技能 | 💬 微信生态 | 105 |
| Excel、SQL、数据可视化、爬虫 | 📊 数据分析 | 42 |
| 日常家务、办事流程、省钱技巧 | 🏠 生活服务 | 1641 |
| 消防演练、消防检查 | 🚒 消防安全 | 19 |
| 质量体系、ISO、检验 | ✅ 质量管理 | 19 |
| 安全生产、隐患排查、EHS | 🦺 安全生产 | 26 |
| 招聘面试、绩效、劳动法 | 👁 人力资源 | 18 |
| PS、剪辑、设计规范 | 🎨 设计媒体 | 22 |
| 开店、运营、工商 | 💼 商业运营 | 16 |

## 📂 完整目录

### 💬 微信生态（105）

| 技能 | 说明 |
|---|---|
| `miniprogram-realtime-debug-tianbao` | 面向小程序开发的真机调试指南 |
| `mp-audio-crossfade-tianbao` | 小程序 InnerAudioContext 双通道切换杂音与爆音排查指引。。触发词：小程序、音频、切换、杂音、cross |
| `mp-background-play-tianbao` | 小程序后台播放中断排查与恢复指引。。触发词：小程序、后台播放、中断、音频 |
| `mp-cache-expire-tianbao` | 小程序版本更新与本地缓存过期排查指引。。触发词：小程序、缓存、更新、强制更新 |
| `mp-image-lazy-tianbao` | 小程序图片懒加载与体积优化指引。。触发词：小程序、图片、懒加载、性能 |
| `mp-liveplayer-tianbao` | 小程序直播组件接入与播放问题排查指引。。触发词：小程序、直播、live-player、推流 |
| `mp-share-onetime-tianbao` | 小程序分享参数丢失与落地页错乱排查指引。。触发词：小程序、分享、参数、onShareAppMessage |
| `mp-skeleton-screen-tianbao` | 小程序骨架屏与加载态优化指引，消除白屏与闪烁。。触发词：小程序、骨架屏、加载、白屏 |
| `mp-sku-order-tianbao` | 小程序商城下单与支付链路排查指引。。触发词：小程序、商城、下单、订单 |
| `mp-template-msg-tianbao` | 小程序订阅消息推送配置与失败排查指引。。触发词：小程序、订阅消息、模板、推送 |
| `mp-voice-input-tianbao` | 小程序语音输入与实时识别接入排查指引。。触发词：小程序、语音、识别、插件 |
| `official-account-reprint-compliance-tianbao` | 面向微信公众号运营者的原创声明、授权转载与洗稿边界合规核查。输入一张采集表，输出含结论摘要、原创声明合规、授权转载合规、 |
| `shipinhao-download-tianbao` | 输入视频号内容的情况说明，理清视频号没有网页版这一关键限制，给出App内保存、转发收藏、直播回放与手机录屏的实际可行顺序 |
| `shipinhao-ecommerce` | 视频号带货的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `shipinhao-live-replay` | 视频号直播回放的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `shipinhao-shop-open` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `shipinhao-shop-return` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `shipinhao-showcase` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `shipinhao-verify` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-aa-payment` | 微信AA收款：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-account-cancellation` | 微信注销流程：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-account-freeze` | 微信冻结解冻：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-antifold` | 微信防折叠的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-audiobook-vip` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-batch-delete-friends` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-cache-pitfall-tianbao` | 面向小程序开发的缓存坑点排查，覆盖存储/一致性/性能/安全四域 |
| `wechat-cardbag-add` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-change-finance` | 微信零钱理财：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-channels-report` | 微信视频号举报：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-chat-export` | 微信聊天记录导出的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-custom-redpacket` | 微信专属红包：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-dark-mode` | 微信深色模式：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-debt-claim-tianbao` | 把微信聊天记录转成欠款催款材料。本地扫描催款沟通记录，扫出借贷/货款/工程款三类债权要件命中与缺口、金额清单、催告质量评 |
| `wechat-device-management` | 微信设备管理：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-dou-topup` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-dual-app` | 微信双开：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-ecosystem-tianbao` | 覆盖微信支付、小程序、公众号、视频号、企业微信、账号安全与投诉维权的微信生态使用与排障助手，用「稳定入口 + 通用定位法 |
| `wechat-evidence-chain-tianbao` | 把微信聊天记录变成能用的证据材料。当用户说"我要劳动仲裁""帮我整理证据""聊天记录能当证据吗""押金能不能要回来""这 |
| `wechat-family-card` | 微信亲属卡的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-family-guard` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-fee-waiver` | 微信手续费的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-floating-window` | 微信浮窗功能：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-fold-groups` | 微信折叠群聊：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-font-size` | 微信字体调大：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-friend-request-settings` | 微信好友申请设置：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-group-admin` | 微信群管理：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-group-homework` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-group-notice` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-insurance-claim-tianbao` | 把微信聊天记录变成能用的保险理赔材料。当用户说"保险理赔""保险公司拒赔""我被拒赔了""理赔材料怎么准备""意外险怎么 |
| `wechat-invoice-title` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-iou-feature` | 微信借条功能：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-keyboard-clipboard` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-keyboard-tips` | 微信输入法的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-local-reader-tianbao` | 在本机读取你自己登录的微信电脑版加密数据库，把聊天记录、群消息、联系人、收藏导出成 Markdown 或纯文本，可按时间 |
| `wechat-mention-all` | 微信群@所有人：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-merchant-account` | 微信经营账户：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-merchant-fee-waiver` | 微信手续费减免：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-merchant-pay` | 微信商家收款的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-minigame-refund` | 微信小游戏充值退款：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-miniprogram-dispute` | 微信小程序纠纷：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-miniprogram-shop` | 微信小程序开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-moments-privacy` | 微信朋友圈权限：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-moments-schedule` | 微信朋友圈定时的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-moments-visibility` | 微信三天天数：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-mp-article-pdf` |  |
| `wechat-mp-comment-manage` | 公众号留言管理的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-mp-repost-whitelist` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-mp-reward` | 公众号赞赏的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-mp-traffic-ads` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-multi-device-login` | 微信多设备登录：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-newyear-greetings` | 微信拜年信息：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-one-way-friends` | 微信单向好友检测：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-opening-writing-tianbao` | 给出前 3 秒钩子的五种开头写法、开头信息密度控制标准、长短句节奏规则与需要避开的四类写法，核查开头与标题是否重复、首段 |
| `wechat-pat-function` | 微信拍一拍：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-pat-undo` | 微信拍一拍撤回：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-pay-merchant-coupon` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-payscore-rental` | 微信支付分借电的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-pin-messages` | 微信消息置顶：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-qq-binding` | 微信QQ号绑定：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-read-membership` | 微信读书会员：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-realname-release` | 微信实名解除：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-redpacket-tips` | 微信红包技巧：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-remote-login-alert` | 微信异地登录：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-ringtone` | 微信来电铃声：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-scan-identify` | 微信扫一扫识物：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-shift-roster-tianbao` | 把微信聊天记录转成排班考勤与加班费材料。本地扫描排班沟通记录，抽出夜班/白班/值班的起止时间与跨天时长，扫出排班、考勤、 |
| `wechat-sports-donation` | 微信运动捐赠：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-sports-ranking` | 微信运动排行：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-status-guide` | 微信状态设置的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-steps-privacy` | 微信步数关闭：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-steps-rank` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-teen-mode` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-traffic-claim-tianbao` | 把微信聊天记录转成交通事故索赔材料。本地扫描车祸现场沟通记录，扫描出赔偿要件命中与缺口、金额清单、程序时间点和时效倒计时 |
| `wechat-transfer-memo` | 微信转账备注：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-unban-appeal` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-unbind-bankcard` | 微信解绑银行卡：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-unblock-contacts` | 微信黑名单恢复：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `wechat-video-archive-tianbao` | 面向想把微信里收到的、朋友圈看到的、收藏的视频留存下来的用户，说明私聊群聊视频、朋友圈视频、收藏视频的本地缓存找回路径与 |
| `wechat-voice-export` |  |
| `wechat-voice-lock` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechat-wallet-lock` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wechatread-export` | 微信读书导出的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |

### 📊 数据分析（42）

| 技能 | 说明 |
|---|---|
| `ab-test-design` | ab测试设计的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `bi-dashboard-build` | BI仪表盘的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `conversion-funnel-analysis` | 转化漏斗分析的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `csv-merge-handling` | csv合并处理的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `dashboard-setup-guide` | dashboard搭建的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `data-cleaning-steps` | 数据清洗步骤的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `data-dedup-methods` | 数据去重方法的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `data-viz-basics` | 数据可视化入门的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `event-tracking-design` | 埋点设计的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `funnel-optimization` | 漏斗转化优化的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `git-conflict-resolve-tianbao` | 面向开发的 Git 合并冲突解决指南，覆盖识别/解决/收尾/预防四阶段 |
| `git-rebase-workflow-tianbao` | 面向团队的 Git 变基与线性历史工作流指南，含安全强推与协作规范 |
| `json-schema-design-tianbao` | 面向后端的 JSON Schema 设计规范指南 |
| `jwt-security-audit-tianbao` | 面向开发的 JWT 使用安全审查，覆盖算法/声明/传输/撤销四域 |
| `k8s-pod-debug-tianbao` | 面向运维的 K8s Pod 故障排查指南，覆盖定位/取证/处置/预防四阶段 |
| `k8s-resource-quota-tianbao` | 面向运维的 K8s 资源配额与限额管理指南，防止单业务挤爆集群 |
| `linux-log-triage-tianbao` | 面向运维的 Linux 日志分级排障指南，从盘点到固化的完整流程 |
| `linux-perf-bottleneck-tianbao` | 面向运维的 Linux 性能瓶颈定位指南，USE 方法 + 工具组合拳 |
| `linux-security-baseline-tianbao` | 面向运维的 Linux 安全基线核查，覆盖账号/服务/文件/审计四域 |
| `mysql-index-design-tianbao` | 面向开发的 MySQL 索引设计与优化指南，从执行计划到变更验证 |
| `nginx-config-audit-tianbao` | 面向运维与开发的 Nginx 配置审计核查，覆盖基础/响应头/TLS/访问控制四域 |
| `pc-boot-slow-tianbao` | 电脑开机加速排查与硬件升级指引 |
| `powershell-batch-audit-tianbao` | 面向 Windows 运维的 PowerShell 批处理脚本审计，覆盖编码/安全/健壮性/维护四域 |
| `python-async-debug-tianbao` | 面向开发的 Python 异步协程调试指南，覆盖现象/定位/根因/修复四阶段 |
| `redis-hotkey-tianbao` | 面向运维与开发的 Redis 热 key 与大 key 治理指南 |
| `report-automation` | 报表自动化的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `report-chart-pick-tianbao` | 汇报图表选型与设计原则指引 |
| `rest-api-versioning-tianbao` | 面向后端的 REST API 版本管理策略指南 |
| `rfm-segmentation` | rfm用户分层的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `sales-data-analysis` | 销售数据分析的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `sql-injection-scan-tianbao` | 面向开发的 SQL 注入风险代码审查，覆盖输入/ORM/账号/出口四域 |
| `sql-window-functions` | sql窗口函数的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `ssd-data-rescue-tianbao` | 数据抢救止损操作与软件恢复指引 |
| `survey-data-analysis` | 问卷数据分析的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `terraform-state-tianbao` | 面向 DevOps 的 Terraform State 安全管理指南 |
| `tv-cast-issue-tianbao` | 电视投屏失败排查与画质优化指引 |
| `user-retention-analysis` | 用户留存分析的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wifi-weak-fix-tianbao` | WiFi 信号弱排查、组网升级与安全加固指引 |
| `windows-printer-triage-tianbao` | 面向办公运维的 Windows 打印机故障排查核查，覆盖连接/服务/共享/质量四域 |
| `yoy-growth-calc` | 同比增长计算的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `yoy-mom-formulas` | 同比环比公式的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `zabbix-alert-tune-tianbao` | 面向运维的 Zabbix 告警治理与调优指南 |

### 🎨 设计与媒体（22）

| 技能 | 说明 |
|---|---|
| `archive-password-recover` | 压缩包密码破解的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `audio-denoise-guide` | 音频降噪处理的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `auto-subtitle-generate` | 字幕自动生成的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `baidu-netdisk-speedup` | 百度网盘加速的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `bilibili-cover-download` | b站封面下载的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `free-ocr-guide` | ocr文字识别免费的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `fullpage-screenshot` | 网页长截图的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `gif-maker-guide` | gif制作工具的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `idphoto-bg-change` | 证件照换底色的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `image-upscale-lossless` | 图片无损放大的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `netease-playlist-export` | 网易云音乐歌单导出的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `pdf-merge-split` | pdf合并拆分的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `phone-photo-skill-tianbao` | 手机摄影构图、光线、专业模式与后期技巧指引 |
| `phone-to-pc-cast` | 手机投屏电脑的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `ppt-quick-build-tianbao` | PPT 快速搭建指引，从结构到风格到交付检查的全流程 |
| `ppt-visual-polish-tianbao` | PPT 视觉美化指引，对齐、配色、数据呈现与高阶手法 |
| `qqmusic-playlist-export` | qq音乐歌单导出的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `screen-recorder-picks` | 录屏软件推荐的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `video-format-convert` | 视频格式转换的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `weibo-album-download` | 微博相册下载的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wifi-boost-pro` | wifi信号增强的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `zhihu-answer-export` | 知乎回答导出的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |

### 📱 常用 App 指南（30）

| 技能 | 说明 |
|---|---|
| `alipay-autopay-cancel` | 支付宝代扣取消：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `alipay-charity` | 支付宝公益捐赠：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `alipay-charity-certificate` | 支付宝爱心捐赠证书：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `alipay-facepay-setup` | 支付宝刷脸设置：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `alipay-family-account` | 支付宝亲情账号：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `alipay-family-card-limit` | 支付宝亲情卡额度：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `alipay-game-guard` | 支付宝游戏保护：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `alipay-medical-code` | 支付宝医保码：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `alipay-mini-wallet` | 支付宝小荷包：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `alipay-miniprogram-compliance-tianbao` | 面向支付宝小程序开发者的合规核查。输入一张采集表，输出含结论摘要、类目资质与备案、支付与虚拟商品、隐私与数据、内容安全、 |
| `alipay-night-guard` | 支付宝夜间保护：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `alipay-payment-history` | 支付宝缴费记录：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `alipay-refund-tracking` | 支付宝退款追踪：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `alipay-scam-report` | 支付宝诈骗举报：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `alipay-smallpay-nopass` | 支付宝小额免密：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `alipay-subscription-cancel` | 支付宝自动续费关闭：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `alipay-transit-weekpass` | 支付宝公交周卡：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `alipay-utility-bills` | 支付宝水电缴费：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `alipay-wufu` | 支付宝五福：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `douyin-mall-return` | 抖音商城退货：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `douyin-video-download-tianbao` | 输入抖音视频链接或分享口令，判断该视频能否合法下载（自己的作品/已获授权/平台提供下载），给出官方保存、创作者后台、浏览 |
| `douyin-watermark-download` |  |
| `jd-channel-analysis-tianbao` | 招聘岗位 JD 的编写与招聘渠道的效果分析：JD 七段结构、职责动词库、硬性/加分项区分、关键词优化、渠道-岗位匹配表、 |
| `jd-video-download-tianbao` | 面向想把京东商品视频、买家秀与直播回放存到本地的用户，区分自有店铺内容、已授权素材与第三方作品，说明官方保存、商家后台与 |
| `meituan-coupon-stack` | 美团红包叠加：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `meituan-video-download-tianbao` | 面向想把美团探店、商家视频存到本地的用户，区分自有发布、已授权素材与第三方作品，说明官方保存、账号后台与合规边界，给出留 |
| `taobao-return-rules` | 淘宝退货规则：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `tax-refund-app-tianbao` | 个税年度汇算退税申请操作与规划要点指引 |
| `xiaohongshu-download-tianbao` | 输入小红书笔记链接，区分图文笔记与视频笔记，说明图片长按保存、视频官方保存、创作者后台与通用工具的适用情况，处理水印、图 |
| `xiaohongshu-note-writing-tianbao` | 用数字、痛点、对比、悬念、身份标签五类公式拟标题，用钩子-共鸣-干货-行动四段搭正文，核查标题长度、关键词布局、极限词与 |

### 💼 商业运营（16）

| 技能 | 说明 |
|---|---|
| `huabei-credit-limit` | 支付宝花呗提额：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `inbox-triage-tianbao` | 邮件与待办分级处理指引，含四象限与批处理法 |
| `interview-simulate-tianbao` | 面试模拟问答指引，覆盖自我介绍到薪资谈判 |
| `invoice-check-tianbao` | 发票查验渠道、异常识别与报销规范指引 |
| `jiebei-loan-rate` | 支付宝借呗利率：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `meeting-minutes-write-tianbao` | 会议纪要撰写规范，从会前准备到会后归档全流程 |
| `official-writing-tianbao` | 机关常用公文写作指引，含文种选择与格式规范 |
| `qms-calibration-cert-tianbao` | 面向质量管理负责人的校准证书与测量溯源管理核查，覆盖证书/溯源/应用/档案四域 |
| `qms-doc-numbering-tianbao` | 消防技术服务机构体系文件编号与受控管理指南，含换版与回收流程 |
| `qms-form-generator-tianbao` | 依据 DB31/T 1380-2022 生成消防技术服务机构受控表单，含编号规则与版式要素 |
| `resume-rebuild-tianbao` | 简历重写指引，含 STAR 法则量化与岗位匹配 |
| `webank-microlloan-rate` | 微粒贷利率：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `weekly-report-write-tianbao` | 周报撰写指引，含结构模板、写法要点与常见误区 |
| `word-style-setup-tianbao` | Word 样式体系与自动化目录设置指引 |
| `work-email-write-tianbao` | 工作邮件撰写与管理指引 |
| `zhima-credit-score` | 支付宝芝麻信用：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |

### 🦺 安全生产 EHS（26）

| 技能 | 说明 |
|---|---|
| `cold-work-environment-tianbao` | 依据《低温作业分级》GB/T 14440 与防寒装备要求，生成清单：低温分级与暴露时长、个体防寒装备配备、作业轮换与取暖 |
| `dual-prevention-tianbao` | 依据《安全生产风险分级管控和隐患排查治理双重预防机制》要求，生成清单：风险点划分与辨识清单、风险评估分级与管控层级、责任 |
| `eia-management-tianbao` | 依据《环境影响评价法》与建设项目竣工环保验收规定，生成清单：环评类别判定与文件层级、批复意见与三同时衔接、施工期环境监理 |
| `electric-arc-protection-tianbao` | 依据低压配电安全与电气作业防护要求，生成清单：电弧危害分析与计算、带电作业接近距离限制、防弧服与面部防护、工具绝缘与验电 |
| `emergency-response-team-tianbao` | 依据《生产安全事故应急条例》与专职队建设要求，生成清单：队伍组建与人员资质、装备配置与维护、培训训练与考核计划、值守联动 |
| `first-aid-responder-tianbao` | 依据现场救护指南与 GB/T 相关培训要求，生成清单：救护员配置比例与持证、急救箱配置与药品效期、常见伤情处置流程、AE |
| `gas-detector-config-tianbao` | 依据《可燃气体探测器》GB 15322 与 GB 12358 有毒气体检测报警要求，生成清单：检测点布设与泄漏源识别、探 |
| `hazardous-chemical-transport-tianbao` | 依据《危险货物道路运输安全管理办法》与 JT/T 617，生成清单：承运单位与车辆资质、驾驶员押运员持证、包装标识与随车 |
| `indoor-air-quality-tianbao` | 依据《室内空气质量标准》GB/T 18883 与 GB 50325，生成清单：污染来源辨识、新风量与换气次数、空调系统清 |
| `lab-safety-tianbao` | 依据《高等学校实验室安全规范》与通用实验室安全管理要求，生成清单：危险源分类与台账、危化品采购领用与储存、通风柜与防护设 |
| `laser-safety-tianbao` | 依据《激光产品的安全》GB 7247.1，生成清单：激光等级判定与安全标识、防护围封与联锁装置、操作员培训与个体防护镜、 |
| `plant-traffic-safety-tianbao` | 依据厂区道路与场内车辆安全要求，生成清单：道路宽度与转弯半径、人车分流与标志标线、限速与减速设施、车辆准入与驾驶员管理、 |
| `pressure-pipeline-safety-tianbao` | 依据《压力管道安全技术监察规程》与 TSG D0001，生成清单：管道级别与设计文件、安装告知与监督检验、在线检验与全面 |
| `pressure-vessel-safety-tianbao` | 依据《特种设备安全法》与 TSG 规程，生成清单：使用登记与检验周期、安全附件校验（安全阀/压力表）、作业人员持证、运行 |
| `psychosocial-risk-tianbao` | 依据职业健康促进与工作场所心理风险管理理念，生成清单：压力源识别与评估、工作量与角色冲突、管理支持与沟通机制、员工援助计 |
| `public-health-emergency-tianbao` | 依据《突发公共卫生事件应急条例》，生成清单：应急组织与分级响应、监测报告与信息报送、隔离观察与密接管理、消杀通风与物资保 |
| `racking-safety-tianbao` | 依据仓储货架使用安全要求，生成清单：额定载荷标识与不超载、货架安装与地脚固定、横梁挂扣与安全销、货物堆码与平衡、定期巡检 |
| `radiation-safety-tianbao` | 依据《放射性同位素与射线装置安全和防护条例》与 GB 18871，生成清单：辐射源许可与台账、场所分区与警示标志、个人剂 |
| `safety-campaign-tianbao` | 依据安全生产月活动与传统安全教育方法，生成清单：主题策划与目标设定、活动形式组合与参与度、宣传物料与阵地布置、关键人群与 |
| `safety-incentive-tianbao` | 依据安全生产举报奖励与安全文化建设要求，生成清单：正负激励组合设计、举报渠道与匿名保护、奖励标准与兑现时效、结果型与行为 |
| `safety-observation-card-tianbao` | 依据行为安全观察与全员隐患排查要求，生成清单：观察卡要素与填写规范、观察频次与覆盖面、沟通式反馈而非指责、数据聚合与趋势 |
| `safety-signage-tianbao` | 依据《安全标志及其使用导则》GB 2894 与 GB 5768，生成清单：标志类型与适用场合、设置位置与视距、夜间可视与 |
| `shift-fatigue-tianbao` | 依据疲劳风险管理（FRMS）方法，生成清单：排班时长与连续工作限制、夜班数量与倒班方向、休息间隔与加班上限、高危岗位疲劳 |
| `stop-work-authority-tianbao` | 依据全员安全管理与不安全行为干预理念，生成清单：授权对象与适用范围、叫停流程与汇报要求、免责保护与反报复承诺、叫停后处置 |
| `toolbox-talk-tianbao` | 依据班组管理与作业前交底要求，生成清单：当日任务与危险源交底、岗位防护与禁令提醒、交叉作业协调事项、交底签名与理解确认、 |
| `wastewater-station-safety-tianbao` | 依据有限空间作业与污水处理安全措施要求，生成清单：构筑物防护栏与盖板、有限空间作业审批与气体检测、加药间化学品存储与投加 |

### 🚒 消防安全（19）

| 技能 | 说明 |
|---|---|
| `coal-yard-fire-tianbao` | 依据电力行业防火与运煤系统设计要求，生成清单：煤场堆放高度与压实、堆取料与消防设施配置、皮带输送机防火与沿线停线、煤粉制 |
| `construction-site-fire-tianbao` | 依据《建设工程施工现场消防安全技术规范》GB 50720，生成清单：总平面布置与消防车道、临时消防设施与给水、临时用房防 |
| `fire-case-analysis-tianbao` | 依据火灾事故调查规定与案例复盘方法，生成清单：案例信息要素结构化、起火原因与蔓延路径还原、管理原因与暴露问题、教训转化为 |
| `fire-engineer-continuing-ed-tianbao` | 依据注册消防工程师继续教育要求，生成清单：学时组成与年度要求、课程范围与标准更新、学习记录与证明留存、执业签章与执业档案 |
| `fire-monitor-system-tianbao` | 依据《自动跟踪定位射流灭火系统》GB 25204，生成清单：场所适用性判定与选型、探测定位组件配置、供水压力与流量校核、 |
| `fire-safety-grid-tianbao` | 依据消防安全责任制实施办法与基层网格化管理要求，生成清单：网格划分与责任到人、基础台账与重点对象、日常巡查与隐患上报、宣 |
| `fire-standard-retrieval-tianbao` | 依据现行工程建设标准体系，生成清单：检索渠道与现行有效性核对、强制性条文与推荐性条文区分、适用范围判定、标准冲突时的优先 |
| `garage-fire-tianbao` | 依据《汽车库、修车库、停车场设计防火规范》GB 50067，生成清单：库类别划分与耐火等级、防火分区与人员疏散、机械停车 |
| `grain-storage-fire-tianbao` | 依据《粮食钢板筒仓设计规范》与粮库防火要求，生成清单：仓房耐火等级与防火间距、除尘与防爆、熏蒸药剂与火源管控、电气防火与 |
| `highrise-fire-tianbao` | 依据《建筑设计防火规范》GB 50016，生成清单：建筑高度与分类判定、防火分区与安全疏散、避难层（间）与消防电梯、竖向 |
| `hotel-fire-tianbao` | 依据《建筑设计防火规范》GB 50016 与旅馆建筑设计防火要求，生成清单：客房层疏散距离与安全出口、厨房与燃气用房分隔 |
| `large-space-fire-tianbao` | 依据 GB 50016 与《建筑钢结构防火技术规范》GB 51249，生成清单：钢结构耐火极限与防火涂料、防火分区面积折 |
| `mass-event-fire-tianbao` | 依据《大型群众性活动安全管理条例》与临时建筑防火要求，生成清单：临时设施搭建材料燃烧性能、疏散通道宽度与人流控制、临时电 |
| `metal-smelting-fire-tianbao` | 依据《有色金属工程设计防火规范》与冶金企业安全要求，生成清单：熔融金属与水接触防控、炉窑冷却系统冗余与断电保障、液压站与 |
| `petrochemical-fire-tianbao` | 依据《石油化工企业设计防火标准》GB 50160，生成清单：装置区消防车道与回车场地、消防站与车辆器材配置、泡沫站与固定 |
| `pv-fire-tianbao` | 依据光伏电站安全与屋面防火要求，生成清单：组件与逆变器选型资质、直流拉弧与热斑防控、屋面布置与疏散通道、断电隔离与标识、 |
| `recycling-yard-fire-tianbao` | 依据再生资源回收场所防火要求，生成清单：分区堆放与垛距通道、废纸塑料橡胶分类管控、易燃液体与危险废物隔离、消防水源与器材 |
| `residential-community-fire-tianbao` | 依据《消防法》与住宅物业消防管理要求，生成清单：消防设施日常维保与标识、疏散通道与电动车集中充电、物业管理履职与巡查频次 |
| `textile-fire-tianbao` | 依据《纺织工程设计防火规范》与丙类厂房防火要求，生成清单：原料与成品仓库防火、清梳并粗车间飞花粉尘清理、印染车间蒸汽与导 |

### ✅ 质量管理（19）

| 技能 | 说明 |
|---|---|
| `counterfeit-part-prevention-tianbao` | 依据防假冒件与供应链追溯要求，生成清单：可疑件定义与报告流程、供应商资质与授权链核验、到货外观与标识比对、开封检验与破坏 |
| `customer-factory-audit-tianbao` | 依据二方审核与社会责任守则要求，生成清单：审核范围与检查表确认、劳工与人权合规要点、健康安全与环境要求、文件与现场一致性 |
| `failure-analysis-tianbao` | 依据失效分析通用流程，生成清单：现场保护与失效现象收集、宏观检查与无损检测、断口与显微分析、机理分析与复现验证、纠正措施 |
| `field-quality-analysis-tianbao` | 依据早期故障与市场失效分析方法，生成清单：故障信息采集与要素完整、失效件回收与检验、帕累托故障模式分布、浴盆曲线与浴盆期 |
| `iso13485-system-tianbao` | 依据 YY/T 0287 / ISO 13485 与《医疗器械生产质量管理规范》，生成清单：风险管理贯穿全生命周期、设计 |
| `iso17025-system-tianbao` | 依据 CNAS-CL01 / ISO/IEC 17025，生成清单：公正性与保密承诺、人员能力与授权、方法选择与验证确认 |
| `iso22000-haccp-tianbao` | 依据 GB/T 22000 / ISO 22000 与 HACCP 原理，生成清单：前提方案与良好操作规范、危害分析与  |
| `npi-trial-run-tianbao` | 依据先期质量策划与试产管控方法，生成清单：试产方案与准入条件、物料与工装准备确认、过程参数记录与偏差、试产问题清单与责任 |
| `oee-management-tianbao` | 依据设备综合效率计算与损失分解方法，生成清单：时间开动率与停机损失、性能开动率与速度损失、合格品率与质量损失、数据采集口 |
| `quality-digitalization-tianbao` | 依据质量管理体系信息化实施方法，生成清单：业务痛点与需求范围、数据模型与编码统一、系统集成接口（ERP/MES/PLM） |
| `quality-escalation-tianbao` | 依据危机管理与顾客投诉处理要求，生成清单：升级判定标准与等级、响应组织架构与授权、时效要求与信息通报、围堵遏制与根因处理 |
| `quality-gate-review-tianbao` | 依据先期策划与阶段控制思路，生成清单：阶段划分与门禁标准、交付物清单与评审记录、风险项与开口问题跟踪、退出准则与放行权限 |
| `reliability-testing-tianbao` | 依据可靠性试验标准 GB/T 5080 系列与 GB/T 2423 环境试验，生成清单：环境应力与工况剖面、试验方案与样 |
| `sampling-plan-gb2828-tianbao` | 依据《计数抽样检验程序》GB/T 2828.1，生成清单：批量与样本量字码确定、检验水平与 AQL 选取、抽样方案检索与 |
| `supplier-quality-improvement-tianbao` | 依据供应商开发与目标管理方法，生成清单：绩效排名与分级策略、共性缺陷与要因诊断、联合改善项目与目标、过程能力帮扶与验证、 |
| `tqm-management-tianbao` | 依据 TQM 与卓越绩效评价准则 GB/T 19580，生成清单：领导作用与全员参与、过程导向与 PDCA 循环、质量方 |
| `visual-inspection-competency-tianbao` | 依据检验人员能力管理要求，生成清单：视力与色觉要求、标准样件与缺陷限度样本、培训考核与持证上岗、检验照明与视角距离、复检 |
| `warranty-management-tianbao` | 依据产品保修政策与家用汽车及消费品三包规定，生成清单：保修范围判定与免责条款、索赔数据统计分析、失效责任划分与供应商追偿 |
| `yield-improvement-tianbao` | 依据过程能力分析与损失分解方法，生成清单：良率漏斗与损失工序定位、缺陷 Pareto 与主要损失、要因验证与参数优化、标 |

### 👥 人力资源招聘（18）

| 技能 | 说明 |
|---|---|
| `cross-border-hiring-tianbao` | 依据劳动合同法与外籍人员就业管理规定，生成清单：用工主体与合同适用、社保公积金缴纳地、外国人工作许可与居留、个税扣缴与双 |
| `diversity-inclusion-tianbao` | 依据公平就业与包容性管理方法，生成清单：招聘JD 中性化与去偏见、面试评分结构化、晋升与薪酬公平性分析、反歧视投诉渠道、 |
| `employee-data-privacy-tianbao` | 依据《个人信息保护法》与劳动用工场景要求，生成清单：处理目的的必要性界定、告知同意与单独同意、敏感信息与健康信息处理边界 |
| `headhunter-management-tianbao` | 依据采购与供应商管理逻辑，生成清单：猎头供应商准入与分级、费率与合同条款、推荐质量与流程规范、保密与人选冲突规则、季度复 |
| `hiring-decision-meeting-tianbao` | 依据集体决策与评价校准方法，生成清单：参会角色与决策权限、评价材料齐备性检查、独立打分与集体评议、异议处理与表决规则、录 |
| `hiring-manager-enablement-tianbao` | 依据招聘协作机制设计方法，生成清单：用人标准共识与需求澄清、招聘时效承诺与分工、面试技能与反问环节训练、决策会议规则与异 |
| `hr-budget-tianbao` | 依据预算管理与 HR 财务分析逻辑，生成清单：岗位编制与人员计划、薪酬福利与五险一金测算、招聘培训与遣散成本、预算科目与 |
| `intern-management-tianbao` | 依据劳动法与实习相关规定，生成清单：实习协议与三方安排、岗位与导师配置、工时上限与安全防护、实习津贴与考勤、考核评价与转 |
| `internal-mobility-tianbao` | 依据人才发展通道设计方法，生成清单：内部岗位发布与报名资格、竞聘流程与评价标准、现岗位交接与放行、轮岗周期与目标、效果评 |
| `interviewer-certification-tianbao` | 依据结构化面试方法论，生成清单：面试官分级与资格标准、结构化题库与评分表、面试技能培训与演练、考官数量与回避规则、评价一 |
| `labor-dispute-tianbao` | 依据《劳动争议调解仲裁法》与相关司法解释，生成清单：争议风险点梳理、证据收集与保存、协商调解流程、仲裁答辩与时限、合规整 |
| `offboarding-process-tianbao` | 依据劳动合同法离职管理要求，生成清单：离职申请与协商方式选择、工作交接清单与知识留存、资产回收与账号权限注销、薪资结算与 |
| `personnel-file-management-tianbao` | 依据人事档案管理与个保合规要求，生成清单：档案目录与材料清单、入职材料核对与更新机制、借阅审批与保密权限、电子档案备份与 |
| `pip-management-tianbao` | 依据绩效管理与劳动合规实践，生成清单：适用情形与启动条件、目标设定与改进周期、过程辅导与书面记录、评价标准与证据留存、解 |
| `remote-work-policy-tianbao` | 依据劳动管理与信息安全要求，生成清单：适用岗位与审批流程、设备配置与费用承担、工时记录与成果考核、信息安全与数据防泄漏、 |
| `requisition-approval-tianbao` | 依据编制与人效管理逻辑，生成清单：岗位必要性论证与替代方案、层级与薪酬区间核准、编制额度与总员控制、审批链条与权限阈值、 |
| `retention-plan-tianbao` | 依据留才管理与离职预警方法，生成清单：关键岗位与流失风险识别、离职面谈与前兆信号、个性化保留包与职业发展、直线经理留才责 |
| `working-hours-management-tianbao` | 依据《劳动法》工时制度规定，生成清单：标准工时与综合计算工时制审批、加班自愿与时长上限、考勤记录完整性、调休与加班费支付 |

### 🏠 生活服务（1641）

| 技能 | 说明 |
|---|---|
| `12315-complaint-check-tianbao` | 输入消费纠纷信息，判断 12315 是否受理、给出投诉与举报的最佳渠道、法定诉求依据（退一赔三/退一赔十）、证据清单与话 |
| `1905-movie-download-tianbao` | 面向想把 1905 电影网（官方的电影资讯与正片片段）内容存到本地的用户，区分预告片、正片片段与受版权保护的完整影片，说 |
| `5s-management-tianbao` | 生成5S（整理/整顿/清扫/清洁/素养）现场管理推行方案与检查表：区域责任、红牌作战、目视化、评分与持续改善。 |
| `ab-test-sample-size-tianbao` | 按 α/power/MDE 三参数算出每组真实所需样本量，并反解「现有流量要跑多久才够」，配 SRM 抽样比例失衡检验、 |
| `ac-filter-clean-tianbao` | 空调滤网清洗与异味预防指南。。触发词：空调、滤网、清洗、家电 |
| `ac-outdoor-icing-tianbao` | 空调外机除冰：分步骤实操指南 |
| `ac-refrigerant-recharge` | 空调加氟判断：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `ac-self-cleaning-tianbao` | 空调自行清洗：分步骤实操指南 |
| `acfun-video-download-tianbao` | 面向想把 AcFun 视频、番剧与直播回放存到本地的用户，区分自有投稿、已授权素材与第三方作品，说明官方离线缓存、创作者 |
| `achilles-rehab-tianbao` | 跟腱断裂康复：就医准备与操作规范指南 |
| `adult-gaokao-application-check-tianbao` | 按考生实际情况核查成人高考能不能报、报哪个层次、缺什么材料、能加多少分，并给出志愿填报策略与避坑清单。输出可直接执行的报 |
| `advertising-compliance-review-tianbao` | 发布前逐项核查广告禁用词、绝对化用语、医疗食品教育特殊规则、功效宣称与证据链。 |
| `ai-agent-build-tianbao` | 智能体搭建入门指引，含测试迭代与安全治理。。触发词：AI、智能体、agent、搭建 |
| `ai-copywriting-tianbao` | AI 文案创作流程指引，含合规红线与质量把关。。触发词：AI、文案、写作、营销 |
| `ai-doc-read-tianbao` | AI 长文档分层阅读与提炼指引。。触发词：AI、文档、阅读、提炼 |
| `ai-meeting-notes-tianbao` | AI 录音转写与纪要提炼流程指引，含隐私合规。。触发词：AI、录音、纪要、转写 |
| `ai-poster-design-tianbao` | AI 海报设计全流程指引，含提示词组织与合规检查。。触发词：AI、海报、文生图、设计 |
| `ai-ppt-draft-tianbao` | AI 辅助 PPT 从大纲到成稿的起草流程。。触发词：AI、PPT、起草、大纲 |
| `ai-prompt-patterns-tianbao` | AI 提示词常用模式速查指引。。触发词：AI、提示词、prompt、模式 |
| `ai-tool-compare-tianbao` | AI 工具横向对比与选型决策指引。。触发词：AI、工具、选型、对比 |
| `air-fryer-cleaning` | 空气炸锅清洗：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `air-fryer-cleaning-tianbao` | 空气炸锅清洁：分步骤实操指南 |
| `air-purifier-filter-tianbao` | 空气净化器滤芯更换与维护指南。。触发词：空气净化器、滤芯、维护、家电 |
| `aircon-cleaning-guide-tianbao` | 家用空调自行清洗步骤与周期的实操指南 |
| `airline-miles-redeem-tianbao` | 机票里程兑换：分步骤实操指南 |
| `airport-terminal-fire-tianbao` | 依据《民用机场航站楼消防设施配置》与交通建筑防火要求，生成清单：大空间防火分区与隔离、登机桥与行李系统防火、行李托运安检 |
| `airport-transit` | 机场中转：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `allergic-rhinitis-rinse-tianbao` | 给出鼻腔冲洗的水质水温、浓度口径、操作姿势与器具清洁规范，以及鼻出血等就医红线。 |
| `allnighter-recovery-tianbao` | 通宵后恢复：分步骤实操指南 |
| `anemia-diet-tianbao` | 贫血食疗：就医准备与操作规范指南 |
| `anger-management-tianbao` | 优先给出延长呼气、暂停离场、降温、用力握拳再松开等生理降激活动作，说明早期身体信号识别、认知重评与表达训练的区别，并给出 |
| `animal-injury-check-tianbao` | 被狗咬、被猫抓、遛狗被扑、被驴踢伤——先别急着找对方赔钱，这个技能先帮你锁定责任主体（谁养的、谁管的）、判断对方能拿什么 |
| `anniversary-memorial-tianbao` | 周年祭流程：分步骤实操指南 |
| `annual-business-report-tianbao` | 核查企业年度报告公示的填报期限、数据口径、材料来源、逾期后果、补报与经营异常名录移出路径。 |
| `annual-leave-expiry-tianbao` | 年假清零前休假安排：分步骤实操指南 |
| `annual-party-performances` | 公司年会节目：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `annual-review-tianbao` | 年终述职材料准备指引。。触发词：述职、年终、汇报、材料 |
| `annual-tax-settlement-tianbao` | 个人所得税年度汇算办理指引，覆盖准备/流程/补税/异议四阶段。。触发词：个税、年度汇算、退税、专项扣除 |
| `annuity-irr-check-tianbao` | 按缴费期、领取期与每年领取额构造现金流，用内部收益率IRR口径核算年金险的真实回报，并对比演示利率（假设投资收益率）与保 |
| `ant-control` | 蚂蚁防治：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `ant-farm` | 蚂蚁庄园：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `ant-forest` | 支付宝蚂蚁森林：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `anti-mite-spray` | 除螨喷雾：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `api-idempotent-tianbao` | 面向后端开发的接口幂等性设计与落地指南，含对账兜底机制。。触发词：幂等、接口设计、分布式、防重 |
| `api-scraping-basics` |  |
| `appendicitis-aftercare-tianbao` | 阑尾炎术后护理：就医准备与操作规范指南 |
| `apqp-tianbao` | 依据 AIAG APQP 手册与 IATF 16949，生成 APQP 策划清单：五个阶段（计划/产品设计/过程设计/验 |
| `aquarium-water-change` | 鱼缸换水：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `aquatic-plant-trimming` | 水草修剪：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `arrival-card` | 入境卡：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `art-of-apology` | 道歉艺术：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `as9100-system-tianbao` | 依据 AS9100 系列与航空航天特殊要求，生成清单：产品安全关键特性识别、首件检验 FAI 与控制、不合格品 MRB  |
| `asbestos-management-tianbao` | 依据《石棉作业场所有害因素职业接触限值》与职业病防治要求，生成清单：含石棉材料排查与台账、拆除作业审批与专业队伍、湿式作 |
| `assessment-center-tianbao` | 依据评价中心（AC）方法，生成清单：测评维度与素质模型对应、情景模拟设计（无领导小组/公文筐/角色扮演）、评分标准与观察 |
| `asthma-inhaler-technique-tianbao` | 哮喘吸入器使用规范：就医准备与操作规范指南 |
| `auto-backup-script` |  |
| `auto-insurance-coverage-check-tianbao` | 对比交强险、商业三者险、车损险与附加险的组合方案，测算不同事故场景下的自付缺口、每万元保额的保费成本与免赔影响，并给出投 |
| `auto-renew-refund-tianbao` | 自动续费扣款追回核查，覆盖开通事实/证据/追回三域。。触发词：自动续费、扣款、追回、会员 |
| `baby-night-crying-tianbao` | 婴儿夜啼：分步骤实操指南 |
| `baby-rice-cereal-tianbao` | 婴儿辅食添加时机、质地进阶与营养搭配指引。。触发词：辅食、添加、婴儿、喂养 |
| `baby-sleep-training-tianbao` | 婴幼儿睡眠引导指引，含睡前程序与夜醒处理。。触发词：婴儿、睡眠、哄睡、夜醒 |
| `baby-vaccine-schedule-tianbao` | 疫苗接种时间安排与接种前后管理指引。。触发词：疫苗、接种、婴儿、免疫 |
| `background-check-guide` | 背调环节：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `background-check-tianbao` | 生成员工背景调查方案与授权文书：身份信息、学历、工作经历、犯罪记录（合规范围内）、竞业限制与前雇主核实，含《个人信息保护 |
| `backlit-photo-fix-tianbao` | 按补光与剪影两条路线核查逆光照片，给出测光方式、曝光锁定、四种补光方式与有效距离、眩光控制、发丝光与剪影五要素的合格口径 |
| `backup-habit-check-tianbao` | 按 3-2-1 原则逐项核查备份是否真的有效：对比云盘、移动硬盘、NAS 与电脑自动备份的口径，说明为什么恢复演练比备份 |
| `backup-strategy-audit-tianbao` | 按 3-2-1 原则核对备份副本分布，给出 RPO/RTO 定义与逐系统对齐表、备份频率与保留周期阶梯、有效性校验方法（ |
| `badminton-footwork` | 羽毛球步法：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `bag-care` | 包包保养：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `baggage-allowance-buy` | 行李额购买：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `baitiao-open-reqs` |  |
| `balcony-drying-system-tianbao` | 阳台晾衣系统规划指南。。触发词：阳台、晾衣、烘干、规划 |
| `balcony-vegetable-growing-tianbao` | 按阳台朝向与实际日照时数定作物，按容器深度配基质，按月份排茬口。含光照判定、容器深度对照、基质配方、四季茬口表、水肥与病 |
| `bandaid-proper-use` | 创可贴使用：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `bandwidth-saturated-troubleshoot-tianbao` | 先分清内网跑满与出口打满，再按「进程定位 → 连接数排查 → 队列与丢包 → 出口链路确认」四步定位，给出 iftop/ |
| `bank-card-fraud-check-tianbao` | 银行卡莫名被扣钱、手机银行被人登录、点了陌生链接后连续小额扣款——这个技能先帮你判断争议类型（伪卡盗刷、网络盗刷、诈骗转 |
| `bank-card-reissue-tianbao` | 银行卡挂失补办：分步骤实操指南 |
| `bank-card-unfreeze-tianbao` | 银行卡冻结申诉解冻指引。。触发词：银行卡、冻结、解冻、申诉 |
| `bank-deposit-rate-compare` |  |
| `bank-points-guide-tianbao` | 银行积分薅羊毛：分步骤实操指南 |
| `bank-wealth-nav-risk-tianbao` | 区分净值型理财与业绩比较基准的含义，逐级说明 R1 到 R5 风险等级对应的可承受风险人群，核查赎回规则 T+0 与 T |
| `barbell-squat` | 杠铃深蹲：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `barrier-free-subsidy-tianbao` | 无障碍改造补贴：分步骤实操指南 |
| `bastion-host-deploy-tianbao` | 按「部署形态 / 账号权限最小化 / 会话审计留存 / 高危命令拦截 / 与 VPN 和零信任的职责边界」五项给出核查口 |
| `batch-release-review-tianbao` | 依据 GB/T 19001 与 GMP 放行控制思路，生成清单：批记录完整性与签名留痕、关键参数符合性、偏差与变更闭合、 |
| `bath-mat-safety` | 浴室防滑垫：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `bathroom-anti-slip-tianbao` | 浴室防滑：分步骤实操指南 |
| `bathroom-cleaning-tianbao` | 按区域分频次清洁台面镜面马桶浴缸地漏瓷砖缝玻璃排气扇，六类污渍（水垢、皂垢、霉斑、锈渍、尿碱、油污）的识别与处理差异，含 |
| `bathroom-grout-mildew-tianbao` | 卫浴瓷砖缝隙除霉与美缝重做指南。。触发词：瓷砖、缝隙、除霉、卫浴 |
| `bathroom-mold-spray` | 浴室除霉喷剂：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `battery-jump-steps` | 汽车搭电步骤：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `bbq-marinade-guide-tianbao` | 烧烤腌料配方、腌制时间与嫩肉用量的实用指南 |
| `beauty-loan-traps` | 美容贷陷阱：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `beauty-prepaid-refund-tianbao` | 美容预付卡退费维权材料核查。。触发词：美容、预付卡、退费、维权 |
| `bedridden-turning-patting-tianbao` | 给出失能老人翻身间隔与体位轮换、拍背排痰的手势与节奏、压疮叠加措施，以及必须立即停止拍背并就医的禁忌清单。 |
| `bedroom-environment-setup-tianbao` | 睡眠环境布置：分步骤实操指南 |
| `behavioral-safety-tianbao` | 依据行为安全管理（BBS）方法，生成行为安全清单：关键安全行为观察、观察卡与频次、反馈与沟通、数据分析与趋势、正向激励。 |
| `belt-care` | 皮带保养：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `benefits-design-tianbao` | 依据薪酬福利实践，生成清单：法定福利合规（社保公积金休假）、补充福利项目（商业保险/体检/餐补）、弹性福利与员工选择、福 |
| `best-man-duties-tianbao` | 伴郎伴娘职责：分步骤实操指南 |
| `betrothal-gift-list-tianbao` | 彩礼嫁妆清单：分步骤实操指南 |
| `bi-dashboard-design-tianbao` | 按「结果指标/过程指标/健康度指标」三层给看板定指标配额（每层 4-6 个、总数不超 12），配八类可视化选型对照表、指 |
| `bicycle-derailleur-adjust-tianbao` | 区分磨损与调校两类问题并给出正确的调整顺序：含链条磨损判定、限位螺丝与拉线张力的调整次序、跳链与蹭链的原因对照、碳纤维扭 |
| `bilibili-danmaku-export` |  |
| `bilibili-video-download-tianbao` | 输入B站视频BV号或链接，区分普通稿件、番剧、会员专享与付费课程四类内容的下载权限，给出App离线缓存、创作者稿件管理、 |
| `binlog-parsing` | binlog解析：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `biogas-pool-maintain-tianbao` | 沼气池维护：分步骤实操指南 |
| `birth-cert-reissue` | 出生证明补办：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `birthday-banquet-planning` | 生日宴安排：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `birthday-banquet-return-gift-tianbao` | 寿宴回礼：分步骤实操指南 |
| `black-cat-complaint-guide-tianbao` | 黑猫投诉材料撰写与跟进指南。。触发词：黑猫投诉、投诉材料、维权 |
| `blender-odor-remove-tianbao` | 破壁机异味去除：分步骤实操指南 |
| `blinds-cleaning` | 百叶窗清洗：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `blood-donation-cert-reissue-tianbao` | 献血证补办：分步骤实操指南 |
| `blood-donation-guide` | 无偿献血：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `blood-pressure-monitor-buying-tianbao` | 给出上臂式与腕式血压计的选购口径、袖带尺寸选择、家庭测量规范与周记录均值计算。 |
| `blood-pressure-selftest-tianbao` | 血压自测方法：分步骤实操指南 |
| `blue-collar-recruitment-tianbao` | 依据批量招聘运营方法，生成清单：需求波峰测算与产能规划、渠道组合与到面转化、面试流程与极速入职、体检体检与岗前安全培训、 |
| `blue-green-deployment` | 蓝绿部署：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `bluetooth-pairing-fix-tianbao` | 按原因概率排序排查蓝牙连不上与频繁断连：先分清 2.4G 接收器与蓝牙的抢占关系，再依次排查耳机电量、多设备连接抢占、驱 |
| `boiler-scale-remove-tianbao` | 烧水壶水垢清除：分步骤实操指南 |
| `bond-reverse-repo-guide` |  |
| `bookshelf-pests` | 书柜防虫：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `bottled-water-shelf-life-tianbao` | 桶装水开封保质期：分步骤实操指南 |
| `bp-daily-care-tianbao` | 高血压日常监测、生活方式与用药配合指引。。触发词：高血压、血压、管理、慢病 |
| `braised-snack-making-tianbao` | 家常卤味配方、卤制时间与卤水养护的安全要点 |
| `braising-liquid-recipe` | 卤水调配：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `brake-pad-replacement` | 刹车片更换判断：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `bread-baking` | 做面包：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `bread-kneading-check-tianbao` | 判断面团揉面阶段与手法是否到位，避免断筋或揉过头 |
| `bride-price-return-check-tianbao` | 先界定哪些给付属于彩礼，再核三种法定返还情形是否成立，按共同生活时长、子女、过错、用途逐项调减，输出返还比例区间而非单一 |
| `buckwheat-pillow` | 荞麦枕：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `building-fire-resistance-tianbao` | 依据《建筑设计防火规范》GB 50016 耐火等级章节，生成建筑耐火等级与构件耐火极限核查清单：建筑分类与耐火等级、柱梁 |
| `burn-first-aid` | 烫伤处理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `business-card-organizing` | 名片管理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `business-plan-writing-tianbao` | 按问题-方案-市场-商业模式-竞争-财务六大模块搭商业计划书骨架，给出每章必答问题清单、三年财务预测表必备科目与勾稽关系 |
| `business-trip-reimburse` | 出差报销：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `c-section-recovery-tianbao` | 剖腹产后护理：就医准备与操作规范指南 |
| `cabinet-moisture-proof` | 橱柜防潮：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `cable-fire-tianbao` | 依据《电力工程电缆设计标准》GB 50217 与建筑防火封堵要求，生成清单：阻燃耐火电缆选型、电缆桥架与穿墙封堵、隧道通 |
| `cad-dwg-review-tianbao` | 面向工程与绘图人员的 DWG 图纸审查核查，覆盖完整性/规范/一致性/问题记录四域。。触发词：CAD、图纸审查、DWG、 |
| `cake-collapse-fix` | 烤蛋糕防塌陷：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `cake-piping-basics` | 裱花入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `cake-removal-tianbao` | 蛋糕脱模：分步骤实操指南 |
| `cake-roll` | 做蛋糕卷：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `cake-whipping-check-tianbao` | 给出蛋白、淡奶油、全蛋、黄油打发的状态判定、温度与器具要求、糖的加入时机、打过头识别与补救。 |
| `calibration-interval-tianbao` | 依据 GB/T 19022 测量管理体系与 JJF 相关规范，生成清单：器具用途与风险分级、历次校准结果趋势、使用频次与 |
| `calibration-traceability-tianbao` | 测量设备与计量器具的溯源管理：台账建立、检定/校准区分、证书六要素核查、符合性判定与修正值使用、到期预警、不合格处置。输 |
| `calligraphy-basics` | 书法入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `calligraphy-copy-start-tianbao` | 书法临帖文房准备、笔画基础与日课规划指引。。触发词：书法、临帖、毛笔、入门 |
| `camera-moisture-care-tianbao` | 相机防潮：分步骤实操指南 |
| `camera-ticket-appeal` | 电子眼申诉：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `camping-gear-checklist-tianbao` | 按人数、天数、季节与场景给出露营装备清单与数量核算口径：帐篷按标称容量减一、睡袋按舒适温标选、水按每人每天 3-4 升备 |
| `campus-loan-scam` | 校园贷防范：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `campus-recruitment-tianbao` | 生成校园招聘全流程组织方案：目标院校与专业、宣讲会、笔试面试、录用与offer管理、雇主品牌与转化追踪。 |
| `candidate-experience-tianbao` | 依据候选人旅程管理方法，生成清单：触点点位与关键环节、响应时效与沟通话术、面试环境与接待标准、反馈闭环与拒信管理、净推荐 |
| `cane-height-fitting` | 拐杖高度：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `canteen-hygiene-tianbao` | 依据《食品安全法》与生活饮用水卫生标准，生成清单：食品经营许可与健康证、原料采购索证与留样、加工过程生熟分开、餐具消毒与 |
| `canvas-shoe-wash` | 帆布鞋清洗：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `capa-8d-tianbao` | 质量问题解决的 CAPA 全流程与 8D 方法：围堵与纠正的区分、根因分析工具（5Why/鱼骨/树图）、8D 九步推进、 |
| `car-accident-handle-tianbao` | 交通事故现场处置、定责与理赔跟进指引。。触发词：交通事故、处理、定责、理赔 |
| `car-annual-inspect-tianbao` | 车辆年检办理流程与逾期后果指引。。触发词：年检、审车、车辆、办理 |
| `car-battery-check-tianbao` | 按原因概率排序排查电瓶亏电，说明搭电与搭电瓶的正确顺序与连接位置、正负极不可反接等禁忌，并讲清什么情况必须换电池、冬季低 |
| `car-battery-dead` | 电瓶亏电：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `car-battery-jumpstart-tianbao` | 电瓶搭电：分步骤实操指南 |
| `car-cabin-filter-tianbao` | 汽车空调滤芯更换：分步骤实操指南 |
| `car-care-cycle-tianbao` | 汽车保养周期与易损件更换指引。。触发词：汽车、保养、周期、维护 |
| `car-fire-extinguisher-tianbao` | 车载灭火器选购放置：分步骤实操指南 |
| `car-insurance-check-tianbao` | 车主用它查保单有没有保障缺口、这次事故该不该报保险、会不会被拒赔。输入车辆与保单信息、事故情况、拒赔自查，输出保障缺口核 |
| `car-insurance-claim` | 车险理赔流程：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `car-insurance-selection` | 车险选择：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `car-interior-odor` | 车内除味：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `car-interior-odor-tianbao` | 车内异味源排查与清除指南，突出蒸发箱清洗。。触发词：汽车、异味、除味、空调 |
| `car-key-dead-battery` | 车钥匙没电：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `car-navigation-update-tianbao` | 车机导航升级：分步骤实操指南 |
| `car-odor-remove-tianbao` | 汽车除味：分步骤实操指南 |
| `car-seat-adjustment` | 座椅调节：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `car-start-troubleshooting` | 汽车打火：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `car-washer-fluid-tianbao` | 汽车玻璃水添加：分步骤实操指南 |
| `car-waxing-tianbao` | 汽车打蜡：分步骤实操指南 |
| `car-window-fog-tianbao` | 车窗玻璃起雾处理：分步骤实操指南 |
| `carbon-management-tianbao` | 依据碳排放核算与双碳工作要求，生成清单：排放边界与源识别（范围一二三）、核算方法与活动数据、减排措施与项目、数据质量与核 |
| `carbon-manager-exam-tianbao` | 碳排放管理师报名：分步骤实操指南 |
| `carbon-monoxide-poisoning` | 一氧化碳中毒：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `card-skimming-prevention` | 证件防盗刷：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `career-path-tianbao` | 依据职业发展与任职资格实践，生成职业发展通道清单：通道划分（管理/专业/技能）、职级与晋升标准、任职资格与评审、轮岗与横 |
| `carpal-tunnel-prevention-tianbao` | 鼠标手预防：分步骤实操指南 |
| `carpool-refund-tianbao` | 顺风车费用争议处理指引。。触发词：顺风车、费用争议、分摊、平台 |
| `carrier-portability-check-tianbao` | 想把手机号携到另一家运营商，被告知合约未满、宽带不能拆、主卡有副卡、靓号有低消，或者已经申请却被"办理了携出"却没在 2 |
| `carwash-card-transfer-tianbao` | 洗车卡转让：分步骤实操指南 |
| `cashmere-washing` | 羊绒衫洗护：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `cast-care-tianbao` | 骨折石膏护理：就医准备与操作规范指南 |
| `cat-hair-cleanup` | 猫毛清理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `cat-hair-manage-tianbao` | 猫毛源头管理与家居清理工具选型指引。。触发词：猫毛、清理、掉毛、家居 |
| `cat-litter-box-choice-tianbao` | 按盆型偏好、猫数加一、数量与位置口径给配置方案，逐项对比四类猫砂的粉尘、结团、误食风险与适用场景，并给出拒绝使用猫砂盆的 |
| `cat-litter-selection` | 猫砂选择：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `cat-neuter-aftercare-tianbao` | 猫绝育术后护理：分步骤实操指南 |
| `cat-scratching-sofa-fix-tianbao` | 按猫的数量与抓点分布给出抓板的数量、形状、材质与摆放口径，讲清从旧抓点向新抓具转移的四步引导流程，列出打骂、喷水、防抓套 |
| `cat-vaccination-schedule` | 猫咪疫苗时间表：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `cataract-early-visit-tianbao` | 白内障早期就医指引：就医准备与操作规范指南 |
| `cataract-surgery-tianbao` | 白内障手术流程：分步骤实操指南 |
| `cc-live-download-tianbao` | 面向想把网易 CC 直播（游戏与娱乐）回放留存下来的用户，区分主播自有回放、公开回放与粉丝专属回放，说明回放生成条件、保 |
| `cctv-video-download-tianbao` | 面向想把央视频、央视节目内容存到本地的用户，区分新闻、纪录片、电视剧与直播，说明官方离线缓存、节目的公开传播属性与版权边 |
| `ceiling-panel-removal-tianbao` | 断电验电后安全拆装集成吊顶扣板与电器模块：含扣板拆卸手法、电器模块拆装接线顺序、检修口位置选择、龙骨不承重的红线、燃气与 |
| `cemetery-purchase-tianbao` | 墓地选购：分步骤实操指南 |
| `central-heating-adjustment` | 集中供暖调节：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `cert-expiry-monitoring` | 证书过期监控：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `cervical-exercise-guide-tianbao` | 给出颈椎劳损的安全动作库、训练剂量、疼痛停止原则、工位改造口径和就医红线清单。 |
| `cet46-exam-check-tianbao` | 按写作、听力、阅读、翻译四部分的分值构成估算分数，核查各题型小题分值与时间分配，定位最薄弱的一项。 |
| `chandelier-cleaning` | 吊灯清洗：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `change-management-tianbao` | 依据 IATF 16949 与变更管理要求，生成清单：变更类型识别（人/机/料/法/环）、变更申请与评审、验证确认与批准 |
| `channels-ecology-compliance-tianbao` | 输入视频号账号类型、内容领域、违规记录、限流信号、带货类目、原创与版权、引流方式等信息，核查是否触碰平台红线（医疗/财经 |
| `channels-shop-compliance-tianbao` | 视频号小店带货合规核查与整改指引。依据《广告法》《价格法》《电子商务法》与微信视频号小店公开规则（商品信息发布规范、违规 |
| `channels-shop-onboarding` | 视频号小店入驻：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `chaos-engineering-basics` | 混沌工程入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `charging-wire-report-tianbao` | 飞线充电举报：分步骤实操指南 |
| `cheap-tour-traps` | 旅游低价团：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `chemical-sds-tianbao` | 依据 GB/T 16483《化学品安全技术说明书 内容和项目顺序》与 GHS，生成化学品 SDS 管理清单：SDS 获取 |
| `chilblain-care` | 冻疮处理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `chilblain-treatment-tianbao` | 冻疮处理：分步骤实操指南 |
| `child-car-seat-check-tianbao` | 讲清安装方式对保护效果的影响、后向安装的适用阶段与产品说明书依据、身高体重与阶段的对应关系，给出安装后必须检查的松紧与倾 |
| `child-custody-support-check-tianbao` | 按年龄分层与综合因素核查子女抚养权归属口径，并按月总收入的法定比例区间测算抚养费三档金额与给付期限。 |
| `child-fever-care-tianbao` | 按月龄分段给出儿童发热的家庭护理、物理降温做法与禁忌，以及必须立即就医的红线清单。 |
| `child-seat-install-tianbao` | 儿童安全座椅安装：分步骤实操指南 |
| `child-sleepwalking-tianbao` | 孩子梦游：分步骤实操指南 |
| `child-solo-sleep-tianbao` | 孩子分房睡过渡：分步骤实操指南 |
| `child-vaccine-schedule-tianbao` | 儿童疫苗时间表：就医准备与操作规范指南 |
| `childhood-myopia-control-tianbao` | 按年龄分段给出儿童户外时长、近距离用眼与屏幕时间口径，含视功能异常就医红线。 |
| `chinese-flatbread` | 烙饼：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `chinese-ink-technique` | 国画用墨：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `chinese-painting-basics` | 国画入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `choke-first-aid-tianbao` | 气道异物梗阻急救指引，含婴儿手法。。触发词：急救、噎住、海姆立克、异物 |
| `choking-first-aid` | 异物卡喉：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `ci-cache-optimize-tianbao` | 面向 DevOps 的 CI 缓存优化指南。。触发词：CI、缓存、构建加速 |
| `ci-cache-strategy` | CI 缓存策略：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `circuit-breaker-trip-tianbao` | 电路跳闸排查：分步骤实操指南 |
| `civil-lawsuit-filing-tianbao` | 核查民事起诉的管辖法院、诉讼请求、起诉状、证据目录、主体材料与诉讼费，输出可补正的立案清单。 |
| `class-notes-speed-tianbao` | 给出可直接照用的关键词缩写表与符号约定表，配合康奈尔等结构化速记框架、线性与分支记录的取舍原则，强调事后整理优先于当场完 |
| `classical-chinese-reading` | 古文阅读：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `cleaner-production-tianbao` | 依据《清洁生产促进法》与清洁生产审核办法，生成清单：审核准备与现状调研、物料与能耗平衡分析、备选方案产生与筛选、中高费方 |
| `cleanroom-fire-tianbao` | 依据《洁净厂房设计规范》GB 50073 与电子工业消防要求，生成清单：洁净区防火分隔与疏散、可燃气体与化学品管控、排烟 |
| `clothes-drying-rack-install-tianbao` | 晾衣架安装：分步骤实操指南 |
| `clothes-ironing-guide-tianbao` | 衣物熨烫温度与手法的实操指南 |
| `clothes-mold-prevention-tianbao` | 衣物防霉：分步骤实操指南 |
| `clothing-donation` | 旧衣捐赠：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `cloudbase-cost-check-tianbao` | 输入微信云开发环境的资源用量（云函数调用次数与资源使用量、数据库读写次数与存储容量、云存储容量与外网下行流量）与套餐类型 |
| `cloudpan-video-download-tianbao` | 面向想把网盘里视频存到本地的用户，区分自己上传的文件与他人分享的链接，说明在线播放的转码流不等于原始文件、非会员限速、分 |
| `cnas-lab-tianbao` | 依据 CNAS-CL01（等同 ISO/IEC 17025），生成实验室认可清单：认可范围、体系文件、人员能力、设备管理 |
| `cockroach-control` | 蟑螂防治：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `coding-roadmap-beginner` | 编程入门路线：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `coffee-machine-descale-tianbao` | 咖啡机除垢：分步骤实操指南 |
| `cohort-analysis-guide` |  |
| `cold-dish-dressing` | 凉菜调制：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `cold-snap-warmth` | 寒潮保暖：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `cold-storage-fire-tianbao` | 依据《冷库设计规范》GB 50072 与冷库安全要求，生成冷库消防清单：保温材料燃烧性能、防火分隔与穿堂、制冷机房与氨泄 |
| `colonoscopy-preparation-tianbao` | 肠镜检查前准备：就医准备与操作规范指南 |
| `color-matching-basics` | 配色基础：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `commercial-complex-fire-tianbao` | 依据《大型商业综合体消防安全管理规则》（XF/T 3019）生成综合体消防管理清单：多产权统一管理、餐饮动火、疏散救援、 |
| `commercial-liability-insurance-tianbao` | 按年营业额、场地财产价值与人员规模三条口径分别估算商业三者险所需保额，拆解各责任限额、免赔额与责任比例，测算社保与商业险 |
| `community-noise-dispute-tianbao` | 邻里噪声纠纷处理指引。。触发词：邻里、噪声、纠纷、物业 |
| `companion-bed-rental-tianbao` | 陪护床租借：分步骤实操指南 |
| `company-deregistration-tianbao` | 判断公司适用简易还是一般注销，核查解散、清算、税务清缴、公告、债权债务、分支机构与登记材料。 |
| `competency-model-tianbao` | 依据胜任力建模方法（BEI/冰山），生成胜任力模型清单：序列/层级划分、胜任力词典、行为锚定与应用场景（招聘/晋升/培养 |
| `complaint-channel-check-tianbao` | 按主管部门受理范围区分12315、市场监管、消协、税务、网信、生态环境等渠道的分工，给出渠道选择逻辑、投诉内容的事实化要 |
| `complaint-letter-check-tianbao` | 逐项核查投诉信十二项必备要素与措辞风险，并对照事项选定正确的受理渠道、管辖层级与跟进路径。 |
| `compliance-evaluation-tianbao` | 依据 ISO 14001/45001 合规义务要求，生成清单：法律法规与其他要求识别、合规义务清单与动态更新、合规性评价 |
| `condiment-storage` | 调料保存：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `confession-approaches` | 表白方式：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `confined-space-tianbao` | 依据《工贸企业有限空间作业安全管理与监督暂行规定》与 GB 30871，生成有限空间清单：辨识建账、审批（先通风后检测再 |
| `congee-technique` | 煲粥技巧：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `connection-pool-tuning` | 连接池参数：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `constructor-cert-check-tianbao` | 核查一级、二级建造师的报考条件与年限够不够、免试能不能申请，并测算注册有效期、延续注册窗口与继续教育学时缺口，列出九类不 |
| `consumer-315-claim-tianbao` | 给出商家协商到平台介入、12315投诉举报、报案、消协调解、诉讼的路径顺序与各自成本口径，用证据四要素与取证手段清单支撑 |
| `consumer-complaint-check-tianbao` | 买的东西出问题不知道先找谁、能要回多少钱。输入交易与争议情况，输出维权路径排序（商家→平台→12315→行政投诉→小额诉 |
| `consumer-rights-12315-tianbao` | 一个帮你把"被坑经历"变成标准投诉材料的工具型技能。覆盖网购、外卖、旅游、培训、月子、网约车、二手、预付费跑路、虚假宣传 |
| `contact-lens-care` | 隐形眼镜护理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `container-odor` | 保鲜盒除味：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `contraception-comparison-tianbao` | 避孕方式对比：就医准备与操作规范指南 |
| `contract-review-remedy-tianbao` | 逐项审查合同必备条款是否齐全、识别十类高风险条款，并测算违约金是否过分高于损失、定金是否超标的额 20%、违约金与定金能 |
| `contractor-hse-tianbao` | 依据 ISO 45001 与相关方管理要求，生成承包商 HSE 审计清单：资质审查、HSE 协议、入场培训、现场监督、绩 |
| `control-plan-tianbao` | 依据 AIAG APQP 控制计划手册与 IATF 16949，生成控制计划清单：过程清单、产品/过程特性、特殊特性符号 |
| `cookie-storage` | 饼干保存：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `coolant-topup` | 冷却液补充：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `corporate-culture-tianbao` | 依据企业文化建设实践，生成清单：使命愿景价值观梳理、文化行为化与准则、宣贯活动与内部传播、管理者示范与践行、文化评估与迭 |
| `corporate-income-tax-settlement-tianbao` | 按利润总额加减纳税调整项核算应纳税所得额与应纳税额，逐项核对限额扣除类费用的调整口径、亏损弥补与优惠税率适用，并给出汇算 |
| `correlation-analysis-steps` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `corridor-clutter-complaint-tianbao` | 楼道堆物投诉：分步骤实操指南 |
| `cosmetic-expiry-clear-tianbao` | 化妆品过期清理：分步骤实操指南 |
| `cosmetics-filing-check-tianbao` | 逐项核对化妆品备案/注册状态、标签标注要件与功效宣称依据，识别违禁宣称与高风险成分，输出可执行的整改与维权路径。 |
| `cost-of-quality-tianbao` | 依据质量经济学与 ISO 9001，生成质量成本（COQ）分析清单：预防/鉴定/内部失败/外部失败四类比、数据采集口径、 |
| `couplet-posting` | 对联张贴：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `courier-no-doorstep-complaint-tianbao` | 快递不上门投诉：分步骤实操指南 |
| `courier-suspension-check-tianbao` | 快递停发区查询：分步骤实操指南 |
| `course-video-cache-merge` |  |
| `cover-letter-writing` | 求职信：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `cpk-process-capability-tianbao` | 依据 SPC 与过程能力分析，生成 Cpk 应用清单：数据正态性检验、Cp/Cpk 计算、规格上下限、过程能力判定（≥1 |
| `cpr-home-steps-tianbao` | 心肺复苏家庭操作指引，含 AED 使用配合。。触发词：心肺复苏、CPR、急救、猝死 |
| `cqrs-pattern` | cqrs模式：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `crab-preparation` | 螃蟹处理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `credit-card-billday-change` |  |
| `credit-card-billing-date` | 信用卡账单日：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `credit-card-installment` | 信用卡分期：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `credit-card-installment-cost-tianbao` | 按每期手续费率与总手续费两种口径核算信用卡分期的真实年化成本，给出手续费率乘 24 除以本金加手续费与 IRR 口径两种 |
| `credit-report-query` |  |
| `critical-illness-rider-check-tianbao` | 核对重疾险犹豫期天数与到期日、犹豫期内退保的现金价值口径、等待期与犹豫期的区别、如实告知义务对理赔的影响，并逐条比对等待 |
| `cross-border-product-selection-tianbao` | 按采购价、头程、平台佣金、FBA 配送费、仓储、广告占比与退货率逐项核算单品毛利，算出毛利率、保本广告占比、保本 ROI |
| `cross-contamination-check-tianbao` | 按先洗菜再切生肉最后切熟食的顺序核查生熟分开执行情况，给出砧板颜色分区、八项具体做法、常见致病菌说明、冷藏温度区间与高风 |
| `cross-province-social-security-tianbao` | 跨省社保衔接：分步骤实操指南 |
| `crutch-usage-tianbao` | 拐杖使用方法：分步骤实操指南 |
| `crystal-lamp-care` | 水晶灯：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `csrf-protection` | csrf防护：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `cucumber-grafting-tianbao` | 按砧木与接穗搭配表选择亲缘关系合适的组合，逐日给出接口愈合期的温湿度与遮阴口径，列出嫁接失败的征兆判据与成活率复核方法。 |
| `curtain-rail-install-tianbao` | 窗帘轨道安装：分步骤实操指南 |
| `curtain-selection` | 窗帘选择：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `curtain-wash-guide-tianbao` | 窗帘拆洗与异味处理指南，按材质分区清洗。。触发词：窗帘、清洗、除味、家居 |
| `curtain-washing` | 窗帘清洗：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `customer-complaint-tianbao` | 依据 ISO 9001 顾客沟通与不满意处理要求，生成顾客投诉处理清单：受理与登记、根因分析（8D/5Why）、围堵与纠 |
| `customer-satisfaction-tianbao` | 依据 ISO 9001:2015 9.1.2 与顾客满意度测评模型，生成满意度测评方案：指标维度、抽样、测评方法、分析与 |
| `customer-specific-requirements-tianbao` | 依据 IATF 16949 顾客特殊要求（CSR）管理要求，生成清单：CSR 识别与清单建立、与体系条款映射、转化到内部 |
| `cutting-board-color-coding-tianbao` | 砧板分色使用：分步骤实操指南 |
| `cutting-board-oiling` | 砧板保养上油：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `dailymotion-video-download-tianbao` | 面向想把 Dailymotion 上的公开视频存到本地的用户，区分自有发布、已授权素材与第三方作品，说明官方保存、账号后 |
| `dashcam-install` | 行车记录仪安装：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `data-anomaly-attribution-tianbao` | 先用 z-score 与环比同比双阈值把波动分成真异常与假异常，再按「时间→渠道→地区→机型→版本→用户群」的固定顺序拆 |
| `data-center-fire-tianbao` | 依据《数据中心设计规范》GB 50174 与机房消防要求，生成数据中心与机房消防清单：机房分级与防火分隔、火灾早期探测（ |
| `data-dictionary-build` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `data-masking-methods` |  |
| `db-charset-guide` | 数据库字符集：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `db-connection-leak` | 数据库连接泄漏排查：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `db-deadlock-hunting` | 死锁排查：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `db-sharding` | 分库分表：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `deadlift-form` | 硬拉姿势：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `debate-basics` | 辩论入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `declutter-old-items` | 旧物断舍离：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `decoration-material-check-tianbao` | 建筑内部装修材料燃烧性能等级的核查：A/B1/B2/B3 分级体系、按场所与部位（顶棚/墙面/地面）的等级要求、燃烧性能 |
| `dehumidifier-picking-tianbao` | 除湿机选购：分步骤实操指南 |
| `dehumidifier-water-tank` | 除湿机使用：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `delivery-box-reuse` | 快递纸箱再利用：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `delivery-damage-claim-tianbao` | 快递损毁赔偿主张指引。。触发词：快递、损毁、赔偿、理赔 |
| `dementia-communication-tianbao` | 给出与失智老人的沟通原则、四类常见沟通障碍处理、随身识别卡与门禁设置、走失后 6 小时黄金期处置和报警信息清单。 |
| `dental-floss-guide` | 牙线使用：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `denture-cleaning` | 假牙清洁：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `deposit-insurance-guide` |  |
| `deposit-refund-tianbao` | 押金退还：分步骤实操指南 |
| `design-verification-tianbao` | 依据 ISO 9001 设计与开发控制要求，生成设计验证与确认清单：设计输入与输出、设计评审、验证（试验/计算/对比）、 |
| `designated-driver-service` | 代驾选择：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `diabetes-meal-planning-tianbao` | 按主食定量、碳水计数和食物交换份给出糖尿病配餐口径，含血糖极值与并发症就医红线。 |
| `diabetic-foot-prevention-tianbao` | 糖尿病足日常预防：就医准备与操作规范指南 |
| `dialysis-companion-tianbao` | 透析陪护：分步骤实操指南 |
| `dianping-video-download-tianbao` | 面向想把大众点评探店视频存到本地的用户，区分自有发布、已授权素材与第三方作品，说明官方保存、账号后台与合规边界，给出留存 |
| `diaper-rash-care-tianbao` | 宝宝红臀护理：分步骤实操指南 |
| `didi-emergency-contact` | 滴滴紧急联系人：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `didi-trip-sharing` | 滴滴行程分享：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `dingding-video-download-tianbao` | 面向想把钉钉直播回放、会议录制留存下来的用户，区分主持人/管理员权限、企业内部已授权内容与私密会议，说明官方导出、本地录 |
| `dinner-party-menu` | 宴客菜单：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `disabled-entrepreneur-aid-tianbao` | 残疾人创业扶持：分步骤实操指南 |
| `disaster-recovery-plan` | 容灾预案：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `dishwasher-drain-clog-tianbao` | 洗碗机排水不畅排查指南，按排查顺序操作。。触发词：洗碗机、排水、堵塞、家电 |
| `dishwasher-filter-clean-tianbao` | 洗碗机滤网清洗：分步骤实操指南 |
| `dishwasher-salt-rinse-tianbao` | 洗碗机耗材选型与投放规范指南。。触发词：洗碗机、耗材、软水盐、亮碟剂 |
| `dishwasher-usage` | 洗碗机使用：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `disk-partition-resize` |  |
| `distributed-id-generation` | 分布式id：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `distributed-transaction-patterns` | 分布式事务：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `divorce-registration-cooling-off-tianbao` | 算清协议离婚的冷静期起算日、届满日与领证窗口，核查管辖机关、双方共同到场要求、离婚协议要素与常见被卡原因，输出可直接照着 |
| `diy-scratching-post` | 猫抓板自制：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `dns-fault-troubleshoot-tianbao` | 按「本地 hosts 与缓存 → 客户端配置 → 递归解析器 → 权威 DNS → 传输链路」五层给出 dig/nslo |
| `docker-compose-prod-tianbao` | 面向运维的 Docker Compose 生产编排指南，覆盖服务/配置/数据/运维四阶段。。触发词：Docker、Com |
| `docker-image-slimming` | Docker 镜像瘦身：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `docker-log-rotation-tianbao` | 面向运维的容器日志治理指南，防止日志盘打满导致业务中断。。触发词：Docker、日志、轮转、磁盘 |
| `docker-multi-stage-tianbao` | 面向开发的 Docker 多阶段构建与镜像瘦身指南，含 CI 门禁阈值建议。。触发词：Docker、镜像瘦身、多阶段构建 |
| `doe-design-tianbao` | 依据试验设计方法论，生成 DOE 应用清单：因子与水平确定、设计类型（全因子/部分因子/响应面）、随机化与重复、方差/回 |
| `dog-food-selection` | 狗粮选择：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `dog-hair-cleanup` | 狗毛清理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `dog-indigestion-check-tianbao` | 按常见有毒食物清单与异物吞咽识别给出观察时限，逐项列出不能催吐的具体情形与必须立即就医的红线，并给出呕吐、腹泻、便血等消 |
| `dog-leash-selection` | 遛狗绳选择：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `dog-teeth-cleaning` | 狗狗洁牙：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `dog-training-basics-tianbao` | 按犬龄与基础水平排出基础服从训练的顺序、单次时长、频次与阶段进阶口径，逐项讲清坐姿、趴下、等待、随行、召回、松绳走位的训 |
| `dog-vaccine-schedule-tianbao` | 狗疫苗时间表：分步骤实操指南 |
| `domestic-violence-check-tianbao` | 被打、被骂、被威胁、被控制人身自由又走不掉——用它先确认这算不算家庭暴力、你能不能申请（夫妻、同居、前伴侣都在范围内）， |
| `door-blocking-games-tianbao` | 婚礼拦门游戏：分步骤实操指南 |
| `door-peephole-replace-tianbao` | 猫眼更换：分步骤实操指南 |
| `doormat-selection` | 门垫选择：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `douban-video-download-tianbao` | 面向想把豆瓣里的视频、短片与影评视频存到本地的用户，区分自有发布、已授权素材与第三方作品，说明官方保存、账号后台与合规边 |
| `double-eyelid-aftercare-tianbao` | 双眼皮术后护理：就医准备与操作规范指南 |
| `double-ninth-elderly` | 重阳敬老：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `dough-fermentation-test` | 面团发酵判断：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `down-jacket-leaking` | 羽绒服钻绒：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `down-jacket-machine-wash-tianbao` | 羽绒服机洗：分步骤实操指南 |
| `down-jacket-storage` | 羽绒服收纳：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `down-jacket-wash-dry-tianbao` | 羽绒服清洗晾晒：分步骤实操指南 |
| `down-jacket-wash-tianbao` | 羽绒服在家清洗与蓬松恢复指南，强调忌拧绞与拍打结团。。触发词：羽绒服、清洗、晾晒、衣物 |
| `drain-odor` | 下水道除味：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `drain-odor-prevention-tianbao` | 先分诊来源的七类判定表（地漏芯失效、存水弯干涸、通气管堵塞、装修时未做水封、水封被破坏、洗手盆下水返味、洗手间无地漏区返 |
| `drain-unclogging` | 下水道疏通：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `dried-goods-soaking` | 泡发干货：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `dried-tangerine-storage-tianbao` | 陈皮保存：分步骤实操指南 |
| `driver-license-renew-tianbao` | 驾驶证期满换证：分步骤实操指南 |
| `drone-beginner` | 无人机入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `drunk-ride-home` | 酒后叫车：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `dryer-buying-guide` | 烘干机选购：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `dryer-lint-clean-tianbao` | 烘干机绒毛清理：分步骤实操指南 |
| `dryer-lint-cleaning` | 烘干机积絮清理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `dslr-beginner` | 单反入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `dumbbell-training-basics-tianbao` | 给出哑铃基础动作的标准要点、代偿信号清单、重量与组次剂量、渐进超负荷判定、每周安排与停练红线。 |
| `dumpling-dough-making-tianbao` | 饺子皮和面：分步骤实操指南 |
| `duozhuayu-selling` | 多抓鱼卖书：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `duplicate-photo-cleanup` |  |
| `dust-explosion-tianbao` | 依据《工贸企业粉尘防爆安全规定》与 GB 15577《粉尘防爆安全规程》，生成粉尘防爆清单：涉粉作业辨识、爆炸危险区域划 |
| `dust-mite-removal` | 除螨方法：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `dust-storm-driving-tianbao` | 沙尘天行车：分步骤实操指南 |
| `dust-storm-protection` | 沙尘天防护：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `e-bike-fire-tianbao` | 依据国务院安委办电动自行车全链条整治与GB 17761，生成电动自行车停放充电消防管理清单：集中充电、禁入楼、电池安全、 |
| `earbud-trouble-tianbao` | 耳机连接、音质、续航故障排查与保养指引。。触发词：耳机、蓝牙、故障、排查 |
| `ebike-battery-care-tianbao` | 铅酸与锂电池分别怎么充、怎么放、什么时候必须停用更换：含充电时机与时长、久放补电要求、冬季与夏季差异、续航下降的非电池原 |
| `ebike-charging-spot-tianbao` | 电动车充电位置：分步骤实操指南 |
| `ebike-registration-check-tianbao` | 买了电动车不知道能不能上牌、要什么材料、自己买的是不是机动车，用它一次查清。输入车辆指标（脚踏、车速、整车质量、电机功率 |
| `ebook-format-convert` |  |
| `ecom-product-video-download-tianbao` | 面向电商商家与运营，判定商品主图视频、详情页视频属于自有商品还是他人商品，给出商家后台素材中心、原文件、手机端保存与命令 |
| `eczema-moisturizing-care-tianbao` | 给出湿疹的润肤剂剂型选择、每周用量估算、涂抹与沐浴口径，以及继发感染等就医红线。 |
| `edu-training-refund-tianbao` | 教育培训退费维权材料核查，含办学资质核实要点。。触发词：教育培训、退费、维权、课程 |
| `edu-upgrade-check-tianbao` | 想专升本、考成考、走自考，被机构说「保过」「不过退款」「不用考试」「一年拿证」，还让你贷款分期、钱打到个人微信、协议写着 |
| `elasticsearch-shard-sizing` | ES 分片规划：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `elder-fraud-check-tianbao` | 输入老年人遭遇的诈骗场景与转账、聊天、宣传材料信息，核查话术特征、红线信号、资金去向与已支付金额，判定诈骗类型与责任，输 |
| `elder-phone-setup-tianbao` | 老人手机设置：分步骤实操指南 |
| `elderly-care-fire-tianbao` | 依据《建筑设计防火规范》GB 50016 老年人照料设施章节与《养老机构消防安全管理规定》，生成清单：建筑耐火与楼层布置 |
| `elderly-care-institution-check-tianbao` | 按机构类型、十个核查维度、合同必看条款与探访实查清单逐项排查，识别资质、消防、护理配比、收费结构与退住条款中的隐患。 |
| `elderly-meals` | 老人餐：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `elderly-polypharmacy-tianbao` | 用清单整理法梳理老人全部用药、识别重复成分、按六类相互作用风险分类，并给出分药盒使用与必须立刻找医生的情形。 |
| `electric-blanket-safety-tianbao` | 电热毯安全使用：分步骤实操指南 |
| `electric-fan-cleaning` | 电风扇清洗：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `electric-heater-picking-tianbao` | 电暖气选购：分步骤实操指南 |
| `electrical-fire-inspection-tianbao` | 电气火灾防控的检测与巡查：年度电气防火检测项目清单、红外测温判据、线路与配电箱巡查要点、隐患分级与整改闭环、报告核查口径 |
| `electrical-safety-tianbao` | 依据《用电安全导则》GB/T 13869 与《低压配电设计规范》GB 50054，生成电气安全清单：配电箱与线路保护、接 |
| `elevator-inspection-query-tianbao` | 电梯年检查询：分步骤实操指南 |
| `elevator-trapped-rescue-tianbao` | 电梯困人自救：分步骤实操指南 |
| `emergency-drill-eval-tianbao` | 依据《生产安全事故应急预案管理办法》与 GB/T 29639，生成应急演练评估清单：演练计划、类型（综合/专项/现场处置 |
| `emergency-material-tianbao` | 依据《生产安全事故应急条例》与 GB 30077《危险化学品单位应急救援物资配备要求》，生成应急物资清单：物资配置标准、 |
| `emergency-plan-preparation-tianbao` | 依据《生产安全事故应急预案管理办法》与 GB/T 29639，生成清单：风险评估与应急资源调查、预案体系（综合/专项/现 |
| `emotion-logging-method-tianbao` | 给出触发事件到身体反应再到情绪强度、想法、行为、结果的结构化记录模板，说明记录频次、长期模式识别价值，以及防止记录变成反 |
| `employee-engagement-tianbao` | 依据敬业度调研方法论，生成清单：调研维度与问卷设计（薪酬/发展/管理/文化）、量表与样本代表性、匿名与保密机制、数据分析 |
| `employee-handbook-tianbao` | 依据《劳动合同法》与规章制度实操要求，生成员工手册编制清单：必备内容（录用/工时/休假/薪酬/纪律/离职）、民主程序、公 |
| `employee-relations-tianbao` | 依据员工关系管理实践，生成清单：沟通渠道与诉求受理、劳动争议预防与调解、员工关怀与活动、纪律处分与申诉机制、群体事件与舆 |
| `employer-branding-tianbao` | 生成雇主品牌清单：雇主价值主张（EVP）、目标人才画像、传播渠道与内容、候选人体验、效果度量（投递量/认可度/留存）。 |
| `ems-environmental-aspects-tianbao` | 依据ISO 14001:2015 条款6.1.2，生成环境因素识别与评价表：输入输出法、影响评价（定量/定性）、重要环境 |
| `endowment-insurance-planning-tianbao` | 用「负债余额 + 家庭年支出 × 剩余抚养年限 − 已有寿险保额 − 可变现资产」的口径算出家庭风险缺口，逐项界定负债是 |
| `energy-storage-fire-tianbao` | 依据《电化学储能电站设计规范》GB 51048 与锂电池储能消防要求，生成储能与锂电池消防安全清单：电池舱室布置与防火分 |
| `engine-oil-grade` | 机油标号选择：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `english-interview-check-tianbao` | 按 Present-Past-Future 三段核查自我介绍时长与词数，按 STAR 四要素核查经历类问题回答结构，覆盖 |
| `env-risk-grading-tianbao` | 依据《企业突发环境事件风险分级方法》与环境影响评价要求，生成环境风险分级清单：风险源识别、分级标准（重大/较大/一般）、 |
| `environmental-emergency-plan-tianbao` | 依据《突发环境事件应急管理办法》与 HJ 941，生成环境应急预案清单：环境风险辨识（危废/化学品/废水）、应急组织、分 |
| `environmental-monitoring-tianbao` | 依据排污许可与自行监测要求，生成清单：监测因子与点位确定、监测频次与方法、委托监测与自测能力、数据记录与信息公开、超标处 |
| `ergonomics-tianbao` | 依据人机工程学与职业危害防护要求，生成清单：作业姿势与负荷评估、工位与工具设计、搬运与重复动作风险、工间休息与轮岗、损伤 |
| `erhu-string-tuning-tianbao` | 给出二胡定弦的目标频率、五度校验口径、拧弦方向、千斤与琴码检查、把位音准校正和跑弦处理清单。 |
| `escalator-falls` | 扶手梯摔倒：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `etc-cancel-tianbao` | ETC注销：分步骤实操指南 |
| `etl-scheduling` | etl调度：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `ev-charge-habit-tianbao` | 新能源车充电习惯与电池养护指引。。触发词：新能源、充电、电动车、电池 |
| `ev-charger-application` | 充电桩申请：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `ev-charger-install-tianbao` | 报装充电桩：分步骤实操指南 |
| `ev-charging-fire-tianbao` | 依据充电设施防火要求与相关国家标准，生成清单：场所选择与布置、充电设备与配电保护、防火分隔与疏散、灭火器材与水源、运维巡 |
| `ev-charging-usage-tianbao` | 分清交流慢充与直流快充的特性，按电表读数与表显里程两种口径估算真实续航与充电时长，并给出跳枪、枪未拔、启动失败等常见故障 |
| `ev-insurance-choose` |  |
| `event-ticket-check-tianbao` | 演唱会、话剧、赛事门票退不掉、想转手被拒、演出取消或延期、黄牛票溢价亏了——用它先判票种是强实名还是非实名，再判是主办方 |
| `event-tracking-design-tianbao` | 给出埋点清单六要素（事件名/触发时机/属性/上报时机/优先级/去重规则）、曝光与点击的时机差异、去重上报三种方案，以及联 |
| `eventual-consistency-guide` | 最终一致性：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `excavation-safety-tianbao` | 依据建筑施工土石方安全规范与管线保护要求，生成清单：地下管线交底与探测、边坡放坡或支护、降水与基坑监测、临边围护与通道、 |
| `excel-formula-audit-tianbao` | 面向办公与财务人员的 Excel 公式审查核查，覆盖引用/函数/一致性/保护四域。。触发词：Excel、公式审查、表格排 |
| `excel-func-toolkit-tianbao` | Excel 常用函数与数据处理速查指引。。触发词：Excel、函数、公式、速查 |
| `excel-pivot-basics-tianbao` | 数据透视表从建表规范到动态更新的入门指引。。触发词：Excel、透视表、汇总、分析 |
| `exhaust-fan-grease` | 排气扇油污：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `exit-interview-tianbao` | 依据离职管理实践，生成离职面谈清单：面谈对象与时机、结构化问题（真实原因/管理/薪酬/发展）、记录与保密、归因分析与组织 |
| `expired-medicine-disposal` | 过期药处理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `explosion-proof-electrical-tianbao` | 依据 GB 3836 爆炸性环境用设备与《爆炸危险环境电力装置设计规范》GB 50058，生成清单：爆炸危险区域划分、防 |
| `express-loss-claim-tianbao` | 按理赔时限口径与保价未保价的赔付规则差异，给出丢件与破损的区分处理、举证责任清单、先验后签的留证习惯，以及拒赔时的申诉升 |
| `express-lost-check-tianbao` | 快递寄丢、快递柜里没了、被冒领、生鲜烂在路上——用它算清能赔多少、两套赔偿口径差多少（企业口径 vs 可主张口径）、该找 |
| `express-refund-process` | 快递退款流程：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `external-wall-insulation-tianbao` | 依据《建筑设计防火规范》GB 50016 与外墙外保温防火要求，生成清单：保温材料燃烧性能等级、防火隔离带与防护层、施工 |
| `eye-20-20-20-tianbao` | 用眼休息法则实操与视疲劳缓解指引。。触发词：用眼、眼疲劳、20-20-20、护眼 |
| `eye-care-habits` | 护眼习惯：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `eye-care-lamp-picking-tianbao` | 护眼灯选择：分步骤实操指南 |
| `facebook-video-download-tianbao` | 面向想把 Facebook 上的公开视频、直播回放存到本地的用户，区分自有发布、已授权素材与第三方作品，说明官方保存、账 |
| `fake-goods-claim-check-tianbao` | 买到假货后按证据链核验 12 项要件、算清退一赔三金额（含 500 元兜底与平台承诺取高），并给出平台维权、12315  |
| `fall-protection-tianbao` | 依据 GB 6095 安全带与 GB 30871 高处作业要求，生成清单：坠落危险源辨识、安全带与安全绳选型、生命线与挂 |
| `falling-object-rights-tianbao` | 高空抛物维权：分步骤实操指南 |
| `family-ledger-tianbao` | 家庭记账体系、预算复盘与目标管理指引。。触发词：记账、家庭、预算、理财 |
| `farm-env-assessment-tianbao` | 养殖场环评手续：分步骤实操指南 |
| `farm-irrigation-permit-tianbao` | 农田灌溉取水证：分步骤实操指南 |
| `farm-machinery-license-tianbao` | 农机驾驶证申领：分步骤实操指南 |
| `farm-subsidy-apply-tianbao` | 农业补贴申请：分步骤实操指南 |
| `faucet-cartridge-replace-tianbao` | 按漏水位置定位水龙头漏水的真实原因，选对阀芯型号并规范更换：含漏水位置对照表、阀芯规格识别、拆装作业顺序、工具材料清单、 |
| `faucet-descaling` | 水龙头除垢：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `faucet-shower-scale-tianbao` | 水龙头与花洒水垢清除指南，含镀层保护要点。。触发词：水垢、花洒、水龙头、五金 |
| `feature-toggle-cleanup` | 功能开关清理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `feishu-video-download-tianbao` | 面向想把飞书直播回放、会议录制留存下来的用户，区分主持人/管理员权限、企业内部已授权内容与私密会议，说明官方导出、本地录 |
| `few-shot-example-selection` | few-shot选择：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `fire-acceptance-check-tianbao` | 建设工程竣工验收走消防验收还是竣工验收消防备案抽查，材料齐不齐，会在哪一环节被退回，常见不合格项怎么排整改顺序。输出 1 |
| `fire-acceptance-tianbao` | 消防技术服务机构竣工检测与验收配合核查，覆盖资料/检测/验收移交三域。。触发词：消防验收、竣工检测、维保、配合 |
| `fire-alarm-host-check-tianbao` | 火灾自动报警主机日常巡查核查，含主机状态、探测器、联动广播与记录整改。。触发词：消防、报警主机、巡检、火警 |
| `fire-alarm-system-tianbao` | 依据《火灾自动报警系统设计规范》GB 50116，生成火灾自动报警系统核查清单：探测器布置、报警主机与回路、手动报警按钮 |
| `fire-compartment-check-tianbao` | 防火分区面积与防火分隔设施的核查：分区面积限值、防火墙/防火卷帘/楼板构造要求、连通部位处理（中庭/风管/管道穿墙封堵） |
| `fire-control-room-duty-tianbao` | 消防控制室值班全流程作业指南：交接班核对、火警信息确认、误报与真火警判别、应急处置步骤（广播/防排烟/电梯迫降/防火卷帘 |
| `fire-control-room-remote-tianbao` | 依据《消防控制室通用技术要求》GB 25506 与建筑消防设施的维护管理 GB 25201，生成消防控制室清单：设施接入 |
| `fire-design-review-tianbao` | 依据《建设工程消防设计审查验收管理暂行规定》，生成清单：审查范围与申报资料、设计文件完整性与深度、总平面与建筑防火审查、 |
| `fire-door-check-tianbao` | 面向消防维保人员的防火门与防火卷帘巡查核查，覆盖门体/卷帘/五金/维护四大域。。触发词：消防维保、巡检、防火门、卷帘 |
| `fire-door-shutter-tianbao` | 依据 GB 12955《防火门》与 GB 14102《防火卷帘》，生成清单：防火门等级与开启方向、闭门器与顺序器、常开防 |
| `fire-drill-evaluation-tianbao` | 依据《消防法》与《机关团体企业事业单位消防安全管理规定》（公安部61号令），生成消防演练评估清单：演练计划/方案、演练类 |
| `fire-drill-plan-tianbao` | 社会单位灭火和应急疏散演练方案编制指南，覆盖策划/实施/评估。。触发词：消防演练、疏散演练、方案 |
| `fire-duty-record-tianbao` | 消防控制室值班记录类表单生成指南，覆盖记录要素/填写规范/检查要点。。触发词：消防、值班记录、表单、消控室 |
| `fire-elevator-check-tianbao` | 面向消防维保人员的消防电梯与消防电源巡查核查，覆盖电梯/电源/电缆保护/管理四大域。。触发词：消防维保、巡检、消防电梯、 |
| `fire-elevator-refuge-tianbao` | 依据 GB 50016 消防电梯与避难层（间）要求，生成清单：消防电梯设置与参数（载重/速度）、前室面积与防烟、井底排水 |
| `fire-emergency-drill-tianbao` | 灭火和应急疏散预案演练的策划、实施、评估与整改闭环：法定频次底线、演练类型选择矩阵、方案九要素、评估四维度、问题整改闭环 |
| `fire-emergency-light-check-tianbao` | 面向消防维保人员的应急照明与疏散指示系统巡查核查，覆盖灯具/功能/安装/维护四大域。。触发词：消防维保、巡检、应急灯、疏 |
| `fire-emergency-lighting-test-tianbao` | 消防应急照明与疏散指示持续供电测试核查。。触发词：消防、应急照明、疏散指示、测试 |
| `fire-engineer-exam-prep-tianbao` | 一级注册消防工程师备考全流程规划：三科框架拆解、考点权重、案例分析答题模板、时间规划与轮次安排、资料筛选原则。输出个人备 |
| `fire-evacuation-calc-tianbao` | 安全疏散设计与核查的核算方法：疏散距离限值（直通/袋形走道）、安全出口数量与间距、百人宽度指标计算、最小净宽度规则、疏散 |
| `fire-evacuation-plan-tianbao` | 社会单位灭火和应急疏散预案编制指南，符合预案编制导则结构。。触发词：消防预案、疏散预案、灭火预案 |
| `fire-exam-case-tianbao` | 一级注册消防工程师《案例分析》题库与解题思路训练，含答题方法域。。触发词：一消、备考、案例分析、答题 |
| `fire-exam-comprehensive-tianbao` | 一级注册消防工程师《综合能力》题库与速记卡片，按法规/维护/验收/评估抽题。。触发词：一消、备考、综合能力、题库 |
| `fire-exam-numbers-tianbao` | 注册消防工程师备考规范数字速记题库，按距离/时间/面积/高度四类抽记。。触发词：一消、备考、规范数字、速记 |
| `fire-exam-tech-tianbao` | 一级注册消防工程师《技术实务》题库与速记卡片，按四大考点域抽题训练。。触发词：一消、备考、技术实务、题库 |
| `fire-exit-complaint-tianbao` | 消防通道投诉：分步骤实操指南 |
| `fire-extinguisher-calc-tianbao` | 建筑灭火器配置设计的核算方法：危险级划分、计算单元划分、Q=K·S/U 计算、修正系数、每个设置点最小灭火级别、最大保护 |
| `fire-extinguisher-check-tianbao` | 面向消防维保人员的灭火器配置与日常巡查核查，覆盖配置/状态/摆放/维护四大域。。触发词：消防维保、巡检、灭火器 |
| `fire-extinguisher-fill-tianbao` | 灭火器配置、状态、维修充装与报废判定核查。。触发词：消防、灭火器、充装、报废 |
| `fire-facility-maintenance-tianbao` | 依据《建筑消防设施的维护管理》GB 25201，生成消防设施维保清单：维保对象、周期（月/季/年）、功能性试验、维保记录 |
| `fire-firewater-pipe-check-tianbao` | 消防给水管网日常检查核查，含管网外观、阀门状态、压力稳压与防冻排水。。触发词：消防、给水、管网、检查 |
| `fire-four-ability-tianbao` | 社会单位消防安全四个能力建设核查，四项能力分域评分。。触发词：消防、四个能力、消防安全管理 |
| `fire-hidden-rectify-tianbao` | 社会单位火灾隐患整改闭环管理核查，覆盖登记/实施/复查/统计四域。。触发词：消防、隐患整改、闭环 |
| `fire-hydrant-button-check-tianbao` | 面向消防维保与消控室人员的消火栓按钮与启泵功能测试核查，覆盖按钮/启泵/联动/记录四大域。。触发词：消防维保、巡检、消火 |
| `fire-hydrant-check-tianbao` | 面向消防维保与消控室值班人员的消火栓系统日常巡查核查，覆盖箱体/压力/配件/标识四大域。。触发词：消防维保、巡检、消火栓 |
| `fire-hydrant-pressure-test-tianbao` | 室内消火栓系统静压动压与出水试验核查，含泵组联动。。触发词：消防、消火栓、试压、检测 |
| `fire-inspection-check-tianbao` | 逐项核查建筑消防设施检测报告的合规性与可用性：机构从业条件、报告必备要素、不合格项分级、判定结论逻辑、整改闭环与有效期。 |
| `fire-investigation-tianbao` | 依据《火灾事故调查规定》，生成清单：现场保护与封闭、调查询问与证据收集、起火部位与起火原因认定、损失统计与责任分析、整改 |
| `fire-iot-monitoring-tianbao` | 依据城市消防远程监控系统与消防物联感知数据标准，生成物联网消防方案：感知终端、联网上云、报警处置闭环、平台值守与数据运维 |
| `fire-key-unit-tianbao` | 依据《消防法》第十七条与《机关团体企业事业单位消防安全管理规定》（公安部61号令），生成消防安全重点单位管理清单：列入界 |
| `fire-keyunit-file-tianbao` | 重点单位消防档案建立指引，含三类备案与动态记录管理。。触发词：消防、档案、重点单位、台账 |
| `fire-lane-check-tianbao` | 消防车道、回车场、登高操作场地与消防救援口的核查：净宽净空坡度要求、尽头式回车场尺寸、登高场地长宽与间距、消防救援口设置 |
| `fire-law-update-tracker-tianbao` | 面向质量管理人员的消防法规更新追踪指南，从采集到落地的全流程。。触发词：消防法规、更新、追踪、标准变化 |
| `fire-law-version-check-tianbao` | 面向维保项目与质量管理人员的消防标准现行有效性核查，覆盖法规/技术标准/地方专项/替代作废四域。。触发词：消防法规、标准 |
| `fire-maintenance-contract-tianbao` | 依据《消防法》与消防设施维护管理要求，生成清单：维保单位资质与合同、维保范围与频次、维保记录与报告、故障响应与修复时限、 |
| `fire-merchant-license-tianbao` | 消防行政许可办理指引，含公众聚集场所营业前消防安全检查全流程。。触发词：消防、许可、备案、办理 |
| `fire-micro-station-tianbao` | 重点单位微型消防站建设与管理核查，覆盖站房装备/人员值守/运行台账三域。。触发词：微型消防站、消防、建设标准 |
| `fire-power-supply-tianbao` | 依据《建筑设计防火规范》GB 50016 与消防电源要求，生成清单：消防负荷等级与供电要求、双电源与末端自动切换、备用电 |
| `fire-product-ccc-tianbao` | 依据《消防产品监督管理规定》与 CCC/CCCF 强制认证目录，生成消防产品合规清单：产品类别、证书有效性、现场判定、到 |
| `fire-product-inspection-tianbao` | 依据《消防产品监督管理规定》（公安部令第122号）与 CCCF 认证要求，生成消防产品现场检查清单：灭火器/防火门/消防 |
| `fire-pump-room-check-tianbao` | 面向消防维保人员的消防泵房与水泵巡查核查，覆盖水泵/控制柜/稳压/环境四大域。。触发词：消防维保、巡检、消防泵、泵房 |
| `fire-pump-room-tianbao` | 依据《消防给水及消火栓系统技术规范》GB 50974，生成清单：水泵性能与备用泵、泵房布置与通道、供电与自动启动、稳压装 |
| `fire-responsibility-letter-tianbao` | 消防安全责任书与承诺函生成指南，覆盖分层签订与存档管理。。触发词：消防、责任书、承诺、逐级 |
| `fire-risk-assessment-tianbao` | 逐项核查消防安全评估报告能不能用：九个一级评估单元齐不齐、14 项报告要素全不全、风险等级与扣分值对不对得上、整改建议落 |
| `fire-safe-evacuation-width-tianbao` | 疏散通道宽度、畅通情况、安全出口与标识照明核查。。触发词：消防、疏散通道、畅通、宽度 |
| `fire-safety-archive-tianbao` | 消防安全重点单位消防档案的搭建与合规：基本情况与管理情况两大类档案框架、各类记录更新频次红线、记录填写五要素、隐患整改闭 |
| `fire-safety-assessment-check-tianbao` | 依据《消防安全评估规范》（XF/T 3005）与GB 35181，核查第三方消防安全评估报告的完整性与结论合规性：评估范 |
| `fire-safety-education-tianbao` | 按《消防法》第六条与应急管理部门要求，生成消防宣传计划、培训课件大纲、演练方案与考核题，覆盖重点岗位与全员。 |
| `fire-safety-patrol-tianbao` | 按《机关团体企业事业单位消防安全管理规定》（公安部61号令）生成防火巡查/检查计划与记录表，逐条对标隐患判定。 |
| `fire-safety-responsibility-tianbao` | 依据《消防法》与《消防安全责任制实施办法》，生成消防安全责任制清单：责任人与组织架构、逐级签订责任书、履职清单、考核奖惩 |
| `fire-safety-training-record-tianbao` | 消防安全培训与演练记录管理核查，含计划、要素、频次与效果评估。。触发词：消防、培训、记录、台账 |
| `fire-separation-layout-tianbao` | 依据《建筑设计防火规范》GB 50016，生成防火间距与总平面布局核查清单：建筑之间防火间距、与储罐堆场及明火地点间距、 |
| `fire-sign-standard-tianbao` | 依据 GB 13495《消防安全标志》与 GB 15630《消防安全标志设置要求》，生成消防标识标准化清单：安全出口/疏 |
| `fire-smoke-detector-check-tianbao` | 面向消控室值班与维保人员的火灾自动报警系统巡查核查，覆盖探测器/联动/主机备电/值班四大域。。触发词：消防维保、巡检、烟 |
| `fire-smoke-exhaust-check-tianbao` | 面向消防维保人员的防排烟系统巡查核查，覆盖风机/风口阀门/联动/维护四大域。。触发词：消防维保、巡检、防排烟、风机 |
| `fire-sprinkler-check-tianbao` | 面向消防维保人员的自动喷水灭火系统巡查核查，覆盖喷头/报警阀组/水泵/维护记录四大域。。触发词：消防维保、巡检、喷淋 |
| `fire-stopping-tianbao` | 依据《建筑防火封堵应用技术标准》GB/T 51410，生成清单：封堵部位识别（贯穿孔口/缝隙/竖向井道）、封堵材料与构件 |
| `fire-tech-agency-check-tianbao` | 依据《消防技术服务机构从业条件》（应急〔2019〕88号）与《社会消防技术服务管理规定》（应急管理部7号令），核对机构/ |
| `fire-testing-report-check-tianbao` | 建筑消防设施年度检测报告与维保记录的核查：机构从业条件与备案核验、报告七要点核查、按场所必备检测项目清单、检测周期红线、 |
| `fire-training-assembly-tianbao` | 面向人员密集场所消防控制室与安保负责人的培训课件生成，突出分流疏散。。触发词：消防培训、人员密集、课件、公共场所 |
| `fire-training-course-tianbao` | 面向消防安全重点单位的培训课件全流程制作：按场所定制内容、35 页以上结构化课件、图文并茂呈现、随堂练习与考核题、讲师授 |
| `fire-training-customs-tianbao` | 面向海关等监管场所消防控制室与窗口人员的培训课件生成，突出监管区域疏散。。触发词：消防培训、海关、课件、口岸 |
| `fire-training-factory-tianbao` | 面向工厂消防控制室与车间人员的培训课件生成，突出工艺处置与危化品管理。。触发词：消防培训、工厂、课件、车间 |
| `fire-training-highrise-tianbao` | 面向高层建筑消防控制室与物业人员的培训课件生成，突出竖向疏散与防烟。。触发词：消防培训、高层、课件、写字楼 |
| `fire-training-hospital-tianbao` | 面向医院消防控制室与医护人员的培训课件生成，突出病患疏散与供氧管理。。触发词：消防培训、医院、课件、病区 |
| `fire-training-mall-tianbao` | 面向商场消防控制室与安保人员的培训课件生成，四模块输出图文要点与讲授提示。。触发词：消防培训、商场、课件、讲座 |
| `fire-training-school-tianbao` | 面向学校消防控制室与教职工的培训课件生成，突出学生疏散组织与演练。。触发词：消防培训、学校、课件、校园 |
| `fire-training-underground-tianbao` | 面向地下建筑消防控制室与安保人员的培训课件生成，突出烟气与方向迷失处置。。触发词：消防培训、地下、课件、商场 |
| `fire-water-supply-tianbao` | 依据《消防给水及消火栓系统技术规范》GB 50974，生成消防给水与消火栓系统核查清单：水源与消防用水量、消防水池与水箱 |
| `fireplace-cleaning` | 壁炉清洁：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `first-article-inspection-tianbao` | 依据 ISO 9001 8.5/8.6 与 AS9102，生成首件检验清单：确认触发场景、检验项目与依据、首件报告/标识 |
| `first-birthday-zhuazhou-tianbao` | 周岁抓周礼：分步骤实操指南 |
| `fish-debone` | 鱼类去刺：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `fish-feed-selection` | 鱼饲料选择：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `fish-pond-aeration-tianbao` | 给出鱼塘缺氧的判断信号与增氧时机（凌晨、高温、高密度、投喂后），增氧设备类型与功率配置口径、运行时长与摆放要求，以及必须 |
| `fish-tank-algae` | 鱼缸除藻：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `fishtank-moving-tianbao` | 鱼缸搬运：分步骤实操指南 |
| `fitness-test-passing-tianbao` | 给出学生与职工体测项目的差距测算、周期可行性判定、分项训练方法、考前安排与停练红线。 |
| `flexible-employment-insurance-tianbao` | 核查灵活就业人员参保的险种选择、缴费基数档次、费率与年缴费额，测算累计缴费年限、养老与医保年限缺口和退休时养老金估算口径 |
| `flexible-staffing-tianbao` | 依据劳务派遣与灵活用工规定，生成清单：用工形式选择（派遣/外包/兼职/实习）、派遣三性岗位与比例限制、供应商资质与协议、 |
| `flight-delay-claim` | 航班延误理赔：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `flight-hotel-refund-tianbao` | 机票酒店退改维权核查，含捆绑销售识别要点。。触发词：机票、酒店、退改、维权 |
| `float-fishing-tuning-tianbao` | 按标准流程调漂：重铅找底、下拉定深、剪铅调目、挂饵找钓目、按鱼情微调，再按目标鱼与水情配线组。含调目钓目对照、漂型与吃铅 |
| `flood-typhoon-tianbao` | 依据防汛防台应急管理要求，生成防汛防台清单：风险点排查（低洼/屋顶/门窗/广告牌）、应急物资与队伍准备、预警响应分级、值 |
| `flooded-garage-response-tianbao` | 暴雨车库泡水应对：分步骤实操指南 |
| `floor-drain-clog-tianbao` | 地漏堵塞疏通与防臭改造指南，含深水封芯选型。。触发词：地漏、堵塞、防臭、疏通 |
| `floor-drain-deodorize-tianbao` | 地漏防臭处理：分步骤实操指南 |
| `floor-drain-odor` | 地漏返味：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `floor-drain-odor-fix-tianbao` | 判断卫生间地漏返味的真实原因并按顺序处理：先排除存水弯干涸与管道堵塞，再选对防臭芯型号，最后规范更换。含芯体选型表、更换 |
| `floor-heating-bleeding-tianbao` | 地暖不热时自己动手排气与排查的实操指南 |
| `floor-scratch-repair` | 地板划痕修复：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `flooring-installation-check-tianbao` | 铺装完成后必查项清单：空鼓检测方法与判定口径、拼缝高低差、表面平整度、含水率、封边与踢脚线、异响、缝隙直线度，含含水率与 |
| `flower-repotting` | 花卉换盆：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `flu-prevention` | 流感预防：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `flue-check-valve-install-tianbao` | 烟道止逆阀安装：分步骤实操指南 |
| `fmea-tianbao` | 依据 AIAG-VDA FMEA 手册，生成 FMEA 清单：结构/功能/失效三层分析、S/O/D 评级、AP 动作优先 |
| `foam-system-tianbao` | 依据 GB 50151《泡沫灭火系统设计规范》，生成清单：系统选型（低/中/高倍数）、泡沫液类型与储量、比例混合器与管网 |
| `fog-driving` | 雾天行车：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `fog-driving-tianbao` | 大雾天驾驶：分步骤实操指南 |
| `folic-acid-guide-tianbao` | 叶酸补充须知：就医准备与操作规范指南 |
| `folic-acid-supplement-tianbao` | 叶酸补充须知：就医准备与操作规范指南 |
| `fondant-basics` | 翻糖入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `food-business-permit-tianbao` | 核查食品经营许可申办材料是否齐全、场所与设施是否达到现场核查要求，并测算许可证有效期与延续窗口，列出不予许可情形和迁址变 |
| `food-safety-complaint-tianbao` | 食品安全问题投诉指引，含价款十倍赔偿主张要点。。触发词：食品安全、投诉、12315、维权 |
| `food-storage-freshness-tianbao` | 按食材品类给出冷藏与冷冻保存期对照表、变质三条硬指标与感官不可靠场景说明，并按实际存放天数核算是否超期。 |
| `food-thawing-guide-tianbao` | 按食材给出四类解冻方式（冷藏慢解、室温、微波、热水）的适用与风险，明确绝对禁止热水解冻的品类、提前转移时点、能否复冻与解 |
| `football-juggling` | 足球颠球：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `foreign-license-exchange-tianbao` | 境外驾照换证：分步骤实操指南 |
| `forest-right-certificate-tianbao` | 林权证办理：分步骤实操指南 |
| `forklift-safety-tianbao` | 依据厂内机动车辆安全管理要求，生成清单：车辆检验与登记、驾驶员持证与培训、限速与人车分流、载重与盲区管控、充电与停放管理 |
| `formaldehyde-removal` | 除甲醛方法：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `free-audio-transcribe` |  |
| `freezer-frost-removal` | 冰箱冷冻室除霜：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `fresh-food-damage-claim-tianbao` | 生鲜快递损坏索赔：分步骤实操指南 |
| `fridge-door-seal` | 冰箱门封条更换：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `fridge-door-seal-tianbao` | 冰箱门封条更换：分步骤实操指南 |
| `fridge-full-power-myth-tianbao` | 冰箱塞满省电误区：分步骤实操指南 |
| `fridge-odor-removal` | 冰箱除味：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `fridge-odor-removal-tianbao` | 先分清十类异味来源再动手，重点是必须先清理再除味，附吸附类与中和类与遮蔽类的区别与局限、除味剂使用安全、门封检查与清洁、 |
| `fridge-odor-remove-tianbao` | 冰箱异味清除与分区管理指南，含密封条检查。。触发词：冰箱、异味、除臭、收纳 |
| `fridge-raw-cooked-separation-tianbao` | 冰箱生熟分区：分步骤实操指南 |
| `fridge-zone-organizing` | 冰箱分区收纳：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `fridge-zone-storage-tianbao` | 冰箱分区收纳：分步骤实操指南 |
| `fried-egg-technique` | 煎蛋技巧：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `fried-food-recrisp` | 炸物复脆：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `fried-rice-technique` | 炒饭技巧：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `frontend-asset-compression` | 前端资源压缩：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `frozen-meat-thawing` | 冷冻肉解冻：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `frozen-pipe-burst` | 水管冻裂：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `frozen-shoulder-exercise-tianbao` | 肩周炎锻炼：就医准备与操作规范指南 |
| `fruit-tree-pruning-tianbao` | 果树剪枝：分步骤实操指南 |
| `fu-character-placing` | 福字贴法：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `fuel-cap-stuck` | 油箱盖打不开：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `fuel-gauge-inaccurate` | 油表不准：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `full-moon-banquet-tianbao` | 满月酒流程：分步骤实操指南 |
| `full-moon-haircut-tianbao` | 满月剃头习俗：分步骤实操指南 |
| `full-time-fire-brigade-tianbao` | 依据《消防法》与《企业专职消防队组织条例》，生成专职消防队清单：建队法定情形、人员编配与执勤、装备配备、训练演练与消防救 |
| `fund-auto-invest-setup` |  |
| `fund-basic-terms-tianbao` | 基金基础术语、费用结构与风险认知入门指引。。触发词：基金、入门、术语、理财 |
| `funeral-gift-etiquette-tianbao` | 丧事随礼规范：分步骤实操指南 |
| `funeral-hall-setup-tianbao` | 灵堂布置：分步骤实操指南 |
| `funeral-procedure-tianbao` | 白事流程指引：分步骤实操指南 |
| `funnel-model-building-tianbao` | 把相邻转化率与总体转化率算清并区分使用场景，给出流失节点定位的判定阈值（最大绝对流失占比 ≥30% 优先处理）、严格递增 |
| `funnel-tracking-design` |  |
| `furniture-care-guide-tianbao` | 按材质分类的家具保养手册：实木、板式、软包、皮革、金属、玻璃、藤编、大理石八类各自的禁忌与清洁手法，常见损伤的类型与成因 |
| `furniture-select-tianbao` | 家具选购指南，含环保等级与验收要点。。触发词：家具、选购、环保、尺寸 |
| `furniture-touchup` | 家具补漆：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `gallstone-aftercare-tianbao` | 胆结石术后护理：就医准备与操作规范指南 |
| `game-live-vod-download-tianbao` | 面向想把斗鱼、虎牙、B站直播的回放留存下来的用户，按平台说明各自的回放保留期、生成条件与入口差异，明确过期无回放不可恢复 |
| `game-topup-refund-tianbao` | 游戏充值退款维权核查，重点覆盖未成年人举证。。触发词：游戏、充值、退款、未成年人 |
| `garbage-disposal-refresh` | 垃圾处理器清洁：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `garment-steamer-descaling` | 挂烫机除垢：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `gas-bill-dispute` | 燃气费争议申诉：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `gas-cylinder-safety-tianbao` | 依据气瓶安全技术规程与常用气瓶要求，生成气瓶安全清单：气瓶检验周期与色标、直立固定与防倾倒、间距与防晒、减压器与软管、空 |
| `gas-extinguishing-system-tianbao` | 依据 GB 50370《气体灭火系统设计规范》，生成清单：防护区与容积核定、灭火剂类型与设计用量、泄压口与围护结构密闭性 |
| `gas-meter-battery-tianbao` | 燃气表换电池：分步骤实操指南 |
| `gas-station-fire-tianbao` | 依据《汽车加油加气加氢站技术标准》GB 50156，生成加油加气站消防安全清单：站址与站内防火间距、储罐与储气瓶组、卸油 |
| `gas-stove-cleaning` | 燃气灶清洁：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `gas-stove-flame-failure` | 燃气灶熄火保护：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `gas-stove-ignition-fix-tianbao` | 燃气灶打不着火排查：分步骤实操指南 |
| `gas-stove-no-ignition` | 燃气灶打不着火：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `gas-topup-tianbao` | 天然气充值：分步骤实操指南 |
| `gas-usage-site-check-tianbao` | 燃气使用场所（管道气/瓶装气）的消防安全检查：报警与紧急切断联动、用气设备与连接管要求、钢瓶存放规则、日常巡查要点、泄漏 |
| `gastroscopy-preparation-tianbao` | 胃镜检查前准备：就医准备与操作规范指南 |
| `gdpr-basics-guide` | GDPR 入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `geektime-video-tianbao` | 面向想把极客时间课程视频存到本地反复学习的用户，区分免费内容、订阅专栏与付费课程，说明平台是否提供官方离线、讲义与源码能 |
| `genealogy-compile-tianbao` | 族谱修编：分步骤实操指南 |
| `git-branch-strategy-tianbao` | 按「并行版本数 / 发布节奏 / 环境级数 / 回滚方式」四项硬指标选定分支策略，核对分支命名与生命周期，给出 cont |
| `git-commit-review-tianbao` | 按 Conventional Commits 校验提交信息（type 白名单、72 字符上限、正文必填场景、BREAKI |
| `glass-hard-water-stain-tianbao` | 淋浴房玻璃与镜面水渍清除指南，含防雾处理 |
| `glass-scale-removal` | 玻璃除垢：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `glasses-antifog` | 眼镜防雾：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `glucose-meter-usage-tianbao` | 血糖仪正确使用：就医准备与操作规范指南 |
| `gold-jewelry-cleaning` | 金饰清洗：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `gongfu-tea` | 功夫茶：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `gout-diet-purine-tianbao` | 按嘌呤分级给出痛风急性期与缓解期的饮食禁忌、酒与果糖控制口径和就医红线。 |
| `gout-diet-taboo-tianbao` | 痛风饮食禁忌：就医准备与操作规范指南 |
| `gout-flare-homecare-tianbao` | 痛风急性期居家护理：就医准备与操作规范指南 |
| `graduate-archive-transfer-tianbao` | 毕业档案去向：分步骤实操指南 |
| `graduation-project-check-tianbao` | 判断毕业设计题目范围是否合适、能否做完，并按答辩日倒排开题、中期、初稿、查重、定稿节点，核查每个节点的剩余天数与完成状态 |
| `grain-grower-certify-tianbao` | 种粮大户认定：分步骤实操指南 |
| `grain-insect-proof-tianbao` | 米面防虫：分步骤实操指南 |
| `grain-storage-tianbao` | 粮食储存防潮：分步骤实操指南 |
| `grain-subsidy-query-tianbao` | 粮补查询：分步骤实操指南 |
| `grave-relocation-tianbao` | 迁坟手续：分步骤实操指南 |
| `gre-text-completion-tianbao` | 用信号词表判定空格的逻辑方向（同向/反向/解释），按单空、双空、三空给出解题顺序，并核查词汇背诵覆盖率与每日新词量。 |
| `green-factory-tianbao` | 依据《绿色工厂评价导则》GB/T 36132，生成清单：基本要求与合规性、基础设施与能源资源投入、产品生态设计、环境排放 |
| `greenhouse-vegetable-rotation-tianbao` | 按大棚茬次表安排一年多茬生产，逐茬核对同科连作年限、土壤盐分与休耕间隔，给出常见茬口搭配表与连作障碍的判断口径。含茬口排 |
| `groomsman-duties` | 伴郎任务：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `grpc-retry-policy` | gRPC 重试策略：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `guide-dog-apply-tianbao` | 导盲犬申请：分步骤实操指南 |
| `guitar-basics` | 吉他入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `guitar-chord-start-tianbao` | 吉他入门器材、基础和弦、节奏与练习计划指引 |
| `guitar-tuning-method-tianbao` | 按 A4 等于 440 赫兹计算六根空弦标准音，用音分量化偏差并分级，核查五品调弦法步骤（含三弦四品的唯一例外）与调音方 |
| `gym-pt-course-refund-check-tianbao` | 输入健身房私教课/年卡的合同、收款、课时与门店状况，核查合同主体与收款主体是否一致、概不退费等格式条款效力、已上课时与应 |
| `gym-refund-check-tianbao` | 健身卡不想用了、门店跑路了、被拒绝退费，用它算清能退多少。输入办卡与用卡情况，输出能不能退的结论、按会员优惠单价折算的退 |
| `gym-refund-tianbao` | 健身房预付卡退费维权材料核查，覆盖合同/证据/协商投诉三域 |
| `hail-damage-claim-tianbao` | 冰雹车损理赔：分步骤实操指南 |
| `hamster-care-basics` | 仓鼠饲养入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `handmade-noodles` | 擀面条：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `hangover-recovery-tianbao` | 宿醉自救：分步骤实操指南 |
| `haokan-video-download-tianbao` | 面向想和好看视频（百度短视频）存到本地的用户，区分自有作品、已授权素材与第三方作品，说明官方保存、创作者后台与合规边界， |
| `haoyibao-claim` | 好医保理赔：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `harmonica-playing-basics-tianbao` | 按 C 调十孔口琴给出各音孔吹/吸对应的音名与频率，核对旋律每一步的音孔与吹吸是否一致，并核查单音发声与气息基础是否到位 |
| `hazard-detection-tianbao` | 工作场所职业病危害因素检测的全流程管理：定期检测周期、检测机构能力、布点原则、结果运用（超标整改/复查）、结果告知与公示 |
| `hazard-identification-tianbao` | 依据ISO 45001:2018 条款6.1.2与GB/T 13861，生成危险源辨识与风险评价（LEC/风险矩阵）清单 |
| `hazard-work-permit-tianbao` | 依据 GB 30871《危险化学品企业特殊作业安全规范》，生成危险作业许可清单：作业票类型（动火/高处/有限空间/临时用 |
| `hazardous-waste-tianbao` | 依据《固体废物污染环境防治法》与《国家危险废物名录》，生成危废管理清单：分类代码、贮存（危废间）、转移联单、台账与标识。 |
| `hazmat-storage-check-tianbao` | 危险化学品储存场所的合规管理：专用仓库要求、禁忌物混存规则、五距管理、温湿度控制、防爆与静电、MSDS与出入库台账、应急 |
| `hdd-dropping-tianbao` | 识别机械硬盘掉盘的典型征兆与 SMART 预警项，给出不要反复通电、先镜像后恢复的抢救流程，说明备份优先于修复原则，以及 |
| `health-checkup-prep-tianbao` | 体检前注意事项：就医准备与操作规范指南 |
| `health-checkup-read-tianbao` | 体检报告结构解读与就医判断指引 |
| `health-checkup-report-tianbao` | 把体检报告几十项指标逐条比对参考区间，输出四档分级（正常/临界/偏高偏低/明显异常）、红旗项就医提醒、带时间的复查计划与 |
| `health-disclosure-check-tianbao` | 按询问回答制的口径逐项核对健康告知问卷，讲清体检异常、门诊记录、既往确诊三类回答口径的常见错误，说明未如实告知可能导致的 |
| `health-product-report-check-tianbao` | 输入保健品的批准文号、宣传话术、购买渠道与付款信息，核查批准文号真伪、识别宣称疾病治疗功能等违法宣称、判断销售主体与渠道 |
| `health-report-reading-tianbao` | 体检报告解读入门：分步骤实操指南 |
| `hearing-aid-care` | 助听器保养：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `hearing-aid-selection-tianbao` | 先做听力筛查必要性与就医警示，再给选型前评估维度、五步验配流程、适应期常见问题与随访安排。 |
| `heat-stress-tianbao` | 依据《防暑降温措施管理办法》与 GBZ 2.2 高温接触限值，生成高温作业清单：高温岗位识别、WBGT/温度检测、工程与 |
| `heat-stroke-prevention` | 高温防暑：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `heating-check-tianbao` | 冬天屋里不暖和、室温不达标、交了取暖费却不热——用它先定性供暖方式与责任主体（找供热企业不是找物业），再按当地供热条例判 |
| `heatstroke-firstaid-tianbao` | 高温中暑急救：分步骤实操指南 |
| `hemorrhoid-aftercare-tianbao` | 痔疮术后护理：就医准备与操作规范指南 |
| `herb-growing` | 香草种植：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `heritage-building-fire-tianbao` | 依据《文物建筑消防安全管理》（GA/T 1463）与《古建筑消防管理规则》，生成文物建筑消防清单：禁火管控、防雷、用电限 |
| `hernia-aftercare-tianbao` | 疝气术后护理：就医准备与操作规范指南 |
| `hidden-danger-governance-tianbao` | 依据《安全生产事故隐患排查治理暂行规定》与GB/T 33000，生成隐患排查治理体系：排查清单、分级（一般/重大）、治理 |
| `high-speed-blender-recipes` | 破壁机食谱：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `highway-blowout` | 高速爆胎：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `highway-driving-tips` | 高速驾驶：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `highway-service-area-tianbao` | 高速服务区攻略：分步骤实操指南 |
| `hill-start` | 坡道起步：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `hinge-squeak` | 合页异响：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `hoa-rights-guide-tianbao` | 业主权益边界与物业沟通维权指引 |
| `home-bp-monitoring-log-tianbao` | 高血压居家自测记录：就医准备与操作规范指南 |
| `home-medicine-box-tianbao` | 家庭药箱配置与管理指引，含安全红线 |
| `home-medicine-cabinet-tianbao` | 家庭药箱配置清单：就医准备与操作规范指南 |
| `home-mesh-wifi-tianbao` | 按户型面积与承重墙结构选单路由、Mesh 还是 AP 加路由，给出 2.4G 与 5G 的分工、回程带宽下限与摆放方案， |
| `home-mold-removal-tianbao` | 先分清是霉菌、返碱还是污渍，再按断湿源、通风、清洁、防霉四步处理，附安全红线：不得直接用含氯消毒剂或强酸强碱处理大面积霉 |
| `home-oxygen-machine-tianbao` | 家用制氧机使用：分步骤实操指南 |
| `home-oxygen-therapy-care-tianbao` | 给出制氧设备类型差异、吸氧管路清洁与鼻氧ifold更换周期、感染预防要点，以及氧气安全红线与必须立即就医的情形。 |
| `home-service-dispute-check-tianbao` | 针对钟点工、月嫂、保姆、保洁等家政服务中的跑路、服务缩水、预付费不退、人身财产损害等纠纷，做信息采集、风险核查与退费维权 |
| `homestead-rebuild-approval-tianbao` | 宅基地翻建审批：分步骤实操指南 |
| `homestead-right-confirm-tianbao` | 宅基地确权办理：分步骤实操指南 |
| `hometown-gift-picking-tianbao` | 探亲特产选择：分步骤实操指南 |
| `hospital-discharge-settlement` | 出院结算：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `hospital-fire-tianbao` | 依据《医疗机构消防安全管理》（WS 308）与重点单位要求，生成医院消防管理清单：住院部疏散、供氧站、手术室、夜间值守、 |
| `hospital-visit-gift-tianbao` | 探病送礼指南：分步骤实操指南 |
| `hot-work-permit-tianbao` | 动火作业的全流程票证管理：动火三级分级、作业票八要素、审批权限、可燃气体检测、监护人职责、完工留守。输出动火作业票模板与 |
| `hotel-checkin-early` | 酒店提前入住：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `hotel-status-match-tianbao` | 酒店会籍匹配：分步骤实操指南 |
| `household-registration-move-tianbao` | 判定户口迁移类型与迁入地准入门槛，核查准予迁入证明、户口迁出与落户三段的材料清单、办理时限与常见被卡原因，输出可直接照着 |
| `housing-deal-check-tianbao` | 买二手房最怕的不是房价，是产权有坑、定金要不回、钱付给中介人没过户。这个技能先帮你把产权与共有人、抵押查封、租赁户口、定 |
| `housing-fund-withdrawal` |  |
| `housing-repair-fund-tianbao` | 房屋维修基金使用：分步骤实操指南 |
| `hpv-vaccine-guide-tianbao` | HPV疫苗接种指引：就医准备与操作规范指南 |
| `hr-analytics-tianbao` | 依据 HR 数据分析实践，生成清单：分析主题与指标体系（招聘/离职/人效）、数据口径与来源统一、分析方法与可视化、洞察解 |
| `hr-planning-tianbao` | 依据人力资源规划方法论，生成清单：业务需求与人力预测、现有人力盘点、定岗定编与岗位设置、供需差距分析、行动计划与人力预算 |
| `hsr-standing-ticket` | 高铁无座：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `huabei-installment-compare` |  |
| `huajiao-live-download-tianbao` | 面向想把花椒直播回放留存下来的用户，区分主播自有回放、公开回放与粉丝专属回放，说明回放生成条件、保留期与访问限制，给出主 |
| `humid-weather-dehumidify-tianbao` | 回南天除湿：分步骤实操指南 |
| `humid-weather-survival` | 回南天应对：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `humidifier-descaling` | 加湿器除垢：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `humidifier-scale-clean-tianbao` | 加湿器水垢清洗与消毒指南，含滤芯更换与水质要求 |
| `humidifier-usage` | 加湿器使用：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `hydroponic-vegetable-tianbao` | 按作物生育阶段给出营养液浓度区间与 pH 范围，按水培常见缺素症状对照表定位可能病因，给出光照时长、换液周期与补液口径。 |
| `hygiene-permit-check-tianbao` | 分清公共场所卫生许可、餐饮食品经营许可、饮用水供水单位卫生许可三条线，核查申办条件与材料、办理时限、延续窗口与变更手续。 |
| `hypothesis-test-basics` |  |
| `hypothesis-testing-tianbao` | 依据统计推断方法，生成清单：假设建立（原假设与备择假设）、检验方法选择（t检验/卡方/方差分析）、显著性水平与 P 值判 |
| `iatf-16949-tianbao` | 依据 IATF 16949:2016 与 ISO 9001:2015，生成汽车供应链 QMS 清单：过程方法、顾客特殊要 |
| `ice-heat-therapy` | 冰敷热敷时机：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `id-card-reissue` | 身份证补办：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `id-photo-shooting-tianbao` | 按常见规格与硬指标核查自拍证件照，给出像素尺寸、分辨率、底色、构图比例、五官着装、拍摄时间与文件大小的合格口径与退回风险 |
| `idempotency-design` | 幂等设计：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `ielts-writing-check-tianbao` | 按 TR/CC/LR/GRA 四项评分标准逐条对表，核查 Task1 与 Task2 字数、时间分配与分数权重，定位最短 |
| `incident-investigation-tianbao` | 依据《生产安全事故报告和调查处理条例》与事故调查方法论，生成调查清单：报告与保护现场程序、直接/间接/根本原因分析（RC |
| `incident-postmortem-guide` | 生产事故复盘：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `incoming-inspection-tianbao` | 依据ISO 9001:2015 条款8.4与GB/T 2828.1（抽样），生成来料检验（IQC）规范：检验计划、抽样方 |
| `individual-tax-settlement-tianbao` | 按七级超额累进税率表核算综合所得年度汇算的应纳税额、应退或应补税额，判断是否需要办理、能否免于办理、全年一次性奖金单独计 |
| `indoor-plant-lighting` | 室内植物补光：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `induction-cooktop-care` | 电磁炉养护：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `infant-food-introduction-check-tianbao` | 按月龄给出辅食引入的择机信号、引入顺序、食物质地进阶、单次一种的观察间隔与过敏观察记录口径，以及立刻就医的红线清单。 |
| `infant-sleep-training-check-tianbao` | 按月龄给出睡眠时长天花板、清醒时长上限、作息安排与安全睡眠环境口径，以及先排出的就医红线清单。 |
| `ink-cartridge-refill-tianbao` | 墨盒加墨：分步骤实操指南 |
| `inspection-instruction-tianbao` | 依据 ISO 9001 与检验策划要求，生成检验规程编制清单：检验对象与阶段（来料/过程/成品）、检验项目与规范限、抽样 |
| `instagram-video-download-tianbao` | 面向想把 Instagram 上的 Reels、视频与直播回放存到本地的用户，区分自有发布、已授权素材与第三方作品，说明 |
| `instant-noodle-upgrade` | 泡面升级吃法：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `insulin-injection-technique-tianbao` | 胰岛素注射手法规范：就医准备与操作规范指南 |
| `insulin-storage-tianbao` | 胰岛素保存：分步骤实操指南 |
| `insurance-claim-reject-tianbao` | 保险拒赔应对指引，含 12378 投诉路径 |
| `insurance-exemption-reading-tianbao` | 按既往症、先天性、特定疾病、特定行为、特别约定等类别逐段定位保险合同的责任免除条款，说明格式条款的不利解释原则，输出投保 |
| `integrated-stove-deep-clean-tianbao` | 集成灶深度清洗：分步骤实操指南 |
| `intercity-moving-compare-tianbao` | 跨市搬家比价：分步骤实操指南 |
| `interested-party-safety-tianbao` | 依据 ISO 45001 与相关方管理实践，生成相关方安全清单：承包商/供应商/访客/实习生的安全准入、交底、现场监督与 |
| `interview-evaluation-tianbao` | 结构化面试的设计与评估：按胜任力维度设计行为锚定问题、STAR 追问法、评分锚与量表、多面试官独立评分与校准、偏见规避、 |
| `interview-late-salvage` | 面试迟到：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `interview-question-bank-tianbao` | 依据结构化面试与行为面试（STAR）方法，生成面试题库清单：按维度/岗位分层、行为面试题（STAR）、专业题与情景题、评 |
| `invoice-verification-check-tianbao` | 按要素校验与查验流程核查发票真伪、金额勾稽、税率适用、抬头税号、备注栏与三流一致性，识别不合规票据并给出退回重开或补充资 |
| `iou-writing-check-tianbao` | 区分借条欠条收条，逐项核对借条必备要素，按 LPR 四倍上限、砍头息与复利规则核算本息，给出瑕疵借条的补正路径与时效中断 |
| `iron-soleplate-residue` | 电熨斗焦垢：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `irrigation-fertilization-plan-tianbao` | 按作物与地块给出灌溉频次、方式与时段口径，以及施肥的记录与核对框架（只做记录模板与通用原则，不给农药稀释浓度强指令），列 |
| `iso9001-risk-opportunity-tianbao` | 依据 GB/T 19001-2016 / ISO 9001:2015 条款 6.1，生成清单：内外部议题识别、相关方需求 |
| `istio-traffic-split` | Istio 流量切分：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `ixigua-video-download-tianbao` | 输入西瓜视频链接，判定能否合法下载（自有作品/已授权/作者允许保存），给出原始文件、西瓜创作平台、官方缓存与通用命令行工 |
| `japanese-gojuon-check-tianbao` | 按行给出清音浊音半浊音拗音的假名与罗马音对照，标出发音要点与易混音，生成默写测验并批改统计薄弱行。 |
| `java-deadlock-hunting` | 线程死锁排查：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `jeans-fading` | 牛仔裤褪色：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `jet-lag-adjustment` | 时差调整：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `jewelry-cleaning` | 首饰清洁：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `jewelry-cleaning-tianbao` | 首饰清洁：分步骤实操指南 |
| `jiaxiao-tuifei-tianbao` | 按培训进度算清驾校该退你多少钱，并生成退费申请书、投诉话术与维权路径。 |
| `jike-video-download-tianbao` | 面向想和即刻动态里的视频存到本地的用户，区分自有发布、已授权素材与第三方作品，说明官方保存、账号后台与合规边界，给出留存 |
| `job-analysis-tianbao` | 依据岗位分析方法论，生成清单：信息收集（访谈/问卷/观察）、岗位职责与工作任务、任职资格（知识/技能/经验）、绩效标准与 |
| `job-competition-speech-tianbao` | 按自我介绍、岗位认知、胜任证据、上任打算四段搭竞聘演讲稿，给出 STAR 化的胜任证据写法、五段时长分配表与语速换算、八 |
| `job-evaluation-tianbao` | 依据岗位价值评估（海氏/美世等）方法，生成清单：评估要素与权重确定、岗位信息收集与校准、评估打分与等级划分、与薪酬职级体 |
| `job-fit-analysis-tianbao` | 用硬技能、软技能、经验年限、行业背景、动机五个维度给人岗匹配度打分，输出能力差距矩阵与 90 天补齐优先级，配面试双向验 |
| `job-safety-analysis-tianbao` | 依据作业安全管理实践与GB 30871（特殊作业），生成JSA（作业安全分析）表：步骤分解、危害识别、控制措施与许可衔接 |
| `jpa-audit-fields` | JPA 审计字段：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `jump-rope-weight-loss` | 跳绳减肥：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `jwt-security` | jwt安全：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `k8s-resource-limits` | K8s 资源限额：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `kafka-partition-planning-tianbao` | 用「目标吞吐 ÷ 单分区吞吐」算出分区数，再校验消费者并发、单分区体积、文件句柄、故障恢复耗时四道门槛：含各环境单分区吞 |
| `kettle-descale-tianbao` | 电水壶水垢清除：分步骤实操指南 |
| `kettle-descaler-tianbao` | 电水壶除垢剂使用：分步骤实操指南 |
| `kettle-scale-clean-tianbao` | 电水壶水垢清除操作指南，四种方案对比与操作步骤 |
| `kid-fever-judge-tianbao` | 儿童发热程度判断与家庭处理指引，含就医红线 |
| `kid-picture-book-tianbao` | 绘本共读方法与亲子阅读习惯养成指引 |
| `kid-screen-limit-tianbao` | 儿童屏幕时间管理与风险防范指引 |
| `kid-snack-pick-tianbao` | 儿童零食成分审阅与健康挑选指引 |
| `kids-pocket-money` | 儿童零花钱：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `kids-vision-protection` | 儿童视力保护：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `kindergarten-school-fire-tianbao` | 依据《中小学幼儿园消防安全管理规定》《托育机构消防安全指南（试行）》，生成学段化消防清单：儿童疏散、厨房/宿舍/实验室、 |
| `kinship-notarization-tianbao` | 亲属关系公证：分步骤实操指南 |
| `kitchen-drawer-organize-tianbao` | 厨房抽屉分区收纳指南，含台面清空目标 |
| `kitchen-duct-cleaning-cycle-tianbao` | 油烟管道清洗周期：分步骤实操指南 |
| `kitchen-god-custom` | 祭灶习俗：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `kitchen-god-festival-tianbao` | 小年祭灶：分步骤实操指南 |
| `kitchen-grease-clean-tianbao` | 厨房油污清洁：分步骤实操指南 |
| `kitchen-grease-wall-tianbao` | 厨房墙面与瓷砖重油污清除指南，强调事前防护 |
| `kitchen-hood-fire-tianbao` | 依据餐饮场所燃气与厨房防火要求，生成清单：油烟管道清洗与油脂积聚、灶台自动灭火装置、燃气报警与紧急切断、排油烟罩与防火阀 |
| `kitchen-sink-unclog` | 厨房水槽疏通：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `kitchen-storage-tianbao` | 从洗切炒的动线出发规划厨房收纳：灶台区、备餐区、清洗区、储存区各自的配置逻辑，容器选择原则（尺寸与灶具匹配、可叠放、材质 |
| `kitchen-ventilation-clean-tianbao` | 用油垢厚度、吸力下降与噪音变化作为清洗触发条件，比死按月更实用。含安全红线：清洗前必须断电、高处与拆机有触电与坠落风险、 |
| `kitten-feed-tianbao` | 幼猫口粮选择、喂养节奏与健康信号指引 |
| `knee-ligament-rehab-tianbao` | 膝盖韧带康复训练：就医准备与操作规范指南 |
| `knife-sharpening-angle` | 磨刀角度技巧：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `knife-sharpening-care-tianbao` | 按刀型给出刃口角度与磨刀参数、磨刀器与磨刀石对比、逆刃推磨与去毛刺要求、收纳与清洗禁忌、生熟刀分离规则，以及九项刀具状态 |
| `knife-sharpening-tianbao` | 菜刀磨刀：分步骤实操指南 |
| `kotlin-coroutine-basics` | Kotlin 协程入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `kuaishou-video-download` |  |
| `kuaishou-video-download-tianbao` | 输入快手视频链接或分享口令，判定能否合法下载（自有作品/已授权/作者允许保存），给出官方保存、快手创作者服务平台、通用命 |
| `kugou-music-video-tianbao` | 面向想把酷狗音乐里的 MV、视频与直播回放存到本地的用户，区分自有上传、已授权素材与第三方作品，说明官方保存、创作者后台 |
| `lab-report-writing-tianbao` | 给出实验报告八要素清单与数据记录规范，按系统误差/随机误差/过失误差三分类判定表述方式，并检查有效数字、单位、异常值标注 |
| `laba-porridge` | 腊八粥：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `labor-arbitration-check-tianbao` | 输入争议类型、入职离职时间、工资、合同与社保、解除方式、欠薪与加班、证据与申请时效等信息，核查是否属于劳动争议仲裁受理范 |
| `labor-arbitration-process-tianbao` | 给出仲裁申请时效与管辖口径、七类常见请求类型、证据强弱排序与材料清单，说明时效中断情形、调解与裁决衔接及企业在仲裁中的常 |
| `labor-arbitration-tianbao` | 劳动仲裁申请指引，含时效核算与举证要点 |
| `labor-compliance-tianbao` | 依据《劳动合同法》《社会保险法》等，生成清单：合同签订与试用期、工时与加班管理、社保公积金缴纳、劳务派遣与外包合规、解除 |
| `labor-contract-review-tianbao` | 劳动合同审查要点指引，覆盖必备条款/薪酬社保/风险/签署四阶段 |
| `lampshade-cleaning` | 灯罩清洗：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `lantern-festival-yuanxiao` | 元宵汤圆：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `lantern-hanging` | 灯笼悬挂：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `late-night-commute-safety-tianbao` | 凌晨下班回家安全：分步骤实操指南 |
| `late-night-eatery-startup-tianbao` | 深夜食堂创业：分步骤实操指南 |
| `late-night-snack-choices-tianbao` | 宵夜健康选择：分步骤实操指南 |
| `latex-pillow-cleaning` | 乳胶枕清洗：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `latte-art-basics` | 拉花入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `laundry-label-reading-tianbao` | 洗涤标签符号识读与对应洗护的指南 |
| `lawyer-letter-check-tianbao` | 核查律师函九项要素是否齐全、扫描六类禁止性表述、判断履行期限是否合理，并测算诉讼时效与中断方式；收到函后给出四步应对与回 |
| `layered-process-audit-tianbao` | 依据分层过程审核（LPA）方法，生成清单：分层设置（班组/车间/厂级）、审核频次与检查项、问题记录与升级、闭环跟踪与看板 |
| `lean-production-tianbao` | 依据精益生产（丰田生产方式）方法论，生成精益推行清单：价值流识别、七大浪费消除、5S 与目视化、标准化作业、拉动与节拍、 |
| `leather-care-guide-tianbao` | 皮包皮带等皮具护理与存放的实操指南 |
| `leather-jacket-care` | 皮衣保养：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `leather-shoe-care` | 皮鞋保养：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `leather-shoes-care-tianbao` | 皮鞋清洁保养指南，含换季收纳与禁忌 |
| `leather-sofa-care-tianbao` | 皮沙发清洁保养指南，含损伤修复与禁忌 |
| `leather-sofa-repair` | 真皮沙发修复：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `leave-request-writing` | 请假条：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `leftover-handling-tianbao` | 按菜品分类给出剩菜冷藏保存期、隔夜适宜度与复热中心温度要求，说明绿叶菜亚硝酸盐与米饭耐热毒素两个关键限制，并给出变质三条 |
| `leftover-reheating` | 剩菜复热：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `leftover-rice-recipes` | 剩饭改造食谱：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `leftover-storage` | 剩菜保存：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `leshi-video-download-tianbao` | 面向想把乐视视频内容存到本地的用户，区分免费影视、会员专享与版权受限内容，说明离线缓存加密、会员权益差异，给出合规的离线 |
| `license-renew-check-tianbao` | 驾驶证临期或已过期，用它算清还能不能换、要不要重考。输入准驾车型、有效期止、记分与异地情况，输出逾期三档判定（正常/1年 |
| `life-insurance-allocation-tianbao` | 按先大人后小孩、先保障后理财、先足额保额后高额保额的家庭配置顺序逐层核查，讲清重疾险、医疗险、意外险、定期寿险各自解决什 |
| `life-insurance-beneficiary-tianbao` | 寿险受益人变更：分步骤实操指南 |
| `lifting-equipment-tianbao` | 依据《起重机械安全规程》GB 6067，生成清单：设备检验与合格证明、吊索具与限位装置、司索指挥与持证、作业区域警戒、日 |
| `lightning-protection-tianbao` | 依据《建筑物防雷设计规范》GB 50057 与防静电要求，生成清单：防雷分类与装置、接地与等电位联结、防静电措施（接地/ |
| `limitation-period-check-tianbao` | 算清诉讼时效从哪天起算、有没有有效中断、还剩多少天届满，并给出剩余天数风险分级与取证动作清单。 |
| `linkedin-video-download-tianbao` | 面向想把 LinkedIn 上的职业视频、直播回放存到本地的用户，区分自有发布、已授权素材与第三方作品，说明官方保存、账 |
| `liping-video-download-tianbao` | 面向想和梨视频资讯短视频存到本地的用户，区分自有作品、已授权素材与第三方作品，说明官方保存、创作者后台与合规边界，给出留 |
| `litter-box-placement` | 猫砂盆位置：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `live-commerce-compliance-tianbao` | 面向主播、商家、MCN 的直播带货合规与避坑指南，覆盖《广告法》虚假宣传红线（极限词/功效宣称/对比贬低/虚构数据）、带 |
| `livestream-lighting-setup-tianbao` | 按三点布光核查直播灯位，给出主光角度与照度、辅光比例、轮廓光与背景光、色温统一、眼镜反光与三种场景方案的合格口径。 |
| `livestream-replay-archive-tianbao` | 面向主播与运营，梳理直播回放的保留期限、画质差异与合规留存方式，给出开播端本地录制、平台回放下载、切条二次发布与命令行工 |
| `llm-hallucination-mitigation-tianbao` | 给出 RAG 场景下 grounding 约束的六条要求、每句结论挂来源的引用溯源规范、可答/需人工/拒答的三级置信判定 |
| `lock-cylinder-replace-tianbao` | 锁芯更换：分步骤实操指南 |
| `locked-out-emergency-tianbao` | 钥匙反锁应急：分步骤实操指南 |
| `lockout-tagout-tianbao` | 依据 GB/T 33579《机械安全 危险能量控制方法 上锁/挂牌》，生成上锁挂牌清单：危险能量源识别（电/液压/气动/ |
| `log-trace-correlation` | 日志链路关联：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `logistics-warehouse-fire-tianbao` | 依据《仓储场所消防安全管理通则》（XF 1131）与GB 50016，生成仓库消防管理清单：货架防火间距、丙类/甲乙类分 |
| `loneliness-coping-tianbao` | 先区分社会关系不足、关系质量差、心理孤立三种孤独并给不同应对路径，说明独处与孤独的界线，识别求助羞耻感，并对独居人群给出 |
| `long-distance-relationship` | 异地恋维护：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `long-drive-prep-tianbao` | 长途驾驶车辆检查、路线规划与疲劳管理指引 |
| `longvideo-offline-check-tianbao` | 面向腾讯视频、爱奇艺、优酷、芒果TV等长视频平台，说明会员离线缓存为什么拿不到通用视频文件，给出官方离线、投屏、版权方渠 |
| `lost-phone-response` | 手机丢失应对：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `low-cal-meal-tianbao` | 低卡餐热量框架、食材替换与坚持策略指引 |
| `luggage-consignment-check-tianbao` | 按禁运、限量、自营三类物品的判定逻辑核对随身与托运物品，重点讲锂电池的额定能量标识、必须随身不可托运的类别，以及超重计费 |
| `luggage-loss-claim` | 行李丢失理赔：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `luggage-lost-report` | 行李丢失申报：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `luggage-packing-tianbao` | 行李箱收纳：分步骤实操指南 |
| `luggage-theft-prevention` | 行李防盗：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `luggage-wheel-fix` | 行李箱轮子维修：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `lumbar-disc-herniation-rehab-tianbao` | 按急性期与缓解期给出腰突的分期处置、动作许可清单、康复训练剂量和马尾综合征就医红线。 |
| `lumbar-protection-exercise` | 腰椎保护操：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `lumbar-strain-exercise-tianbao` | 腰肌劳损锻炼：就医准备与操作规范指南 |
| `lumbar-surgery-rehab-tianbao` | 腰椎术后康复锻炼：就医准备与操作规范指南 |
| `machine-guarding-tianbao` | 依据 GB/T 8196《机械安全 防护装置》与机械安全要求，生成机械设备防护清单：危险部位识别（转动/传动/剪切/挤压 |
| `magnetic-chip-card-tianbao` | 磁条卡换芯片卡：分步骤实操指南 |
| `major-hazard-source-tianbao` | 依据《危险化学品重大危险源辨识》GB 18218，生成重大危险源管理清单：辨识与分级（一~四级）、安全评估与备案、监测监 |
| `male-health-checkup-tianbao` | 男科检查项目：就医准备与操作规范指南 |
| `marble-countertop-care-tianbao` | 大理石台面养护与渗色处理指南，强调酸性禁忌 |
| `massage-basics` | 按摩手法入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `matchmaker-check-tianbao` | 被婚介机构说「包成功」「不结婚全退」「优质资源多」忽悠签了两万八，介绍四个人没一个能联系上，对方照片还跟本人对不上，销售 |
| `mattress-dust-mite` | 床垫除螨：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `mattress-flipping` | 床垫翻转：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `meal-plate-balance-tianbao` | 餐盘配比与三餐营养搭配指引 |
| `measurement-uncertainty-tianbao` | 依据 JJF 1059《测量不确定度评定与表示》，生成测量不确定度评定清单：不确定度来源识别（设备/环境/人员/方法）、 |
| `meat-cutting-grain` | 切肉纹理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `meat-marinating` | 腌肉技巧：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `medical-beauty-refund-check-tianbao` | 输入医美机构的执业资质、医师注册、项目合同、付款与效果情况，核查机构与医师资质合法性、识别无资质行医与效果未达等风险、判 |
| `medical-dispute-guide-tianbao` | 医疗纠纷处理路径指引，突出病历封存与复制 |
| `medical-dispute-record-check-tianbao` | 按时间顺序锁住病历与实物证据，区分两种鉴定路径，按人身损害赔偿项目逐项核算并按过错参与度折算，输出调解与诉讼路径。 |
| `medical-insurance-transfer-tianbao` | 核查医保关系转移接续的适用情形、办理流程、时限、材料、年限折算、中断处理与待遇衔接。 |
| `medical-reimbursement-check-tianbao` | 把一笔住院/门诊费用按「总费用 − 目录外自费 − 先行自付 − 起付线 × 比例（再扣封顶线）」四层拆开算清，核查 1 |
| `medical-remote-filing` |  |
| `medicated-patch-apply-tianbao` | 膏药正确贴法：分步骤实操指南 |
| `medicine-moisture-storage-tianbao` | 药品防潮储存：分步骤实操指南 |
| `meipai-video-download-tianbao` | 面向想把美拍短视频存到本地的用户，区分自有作品、已授权素材与第三方作品，说明官方保存、创作者后台与合规边界，给出留存方式 |
| `melatonin-usage-tianbao` | 褪黑素使用须知：分步骤实操指南 |
| `membership-card-refund-tianbao` | 判定预付卡类型与责任主体，按价格摊销法核算应退本金与可扣项上限，识别退一赔三适用与不适用场景，输出投诉与保全路径。 |
| `mens-shaving` | 男士剃须：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `mentorship-tianbao` | 依据导师制实践，生成清单：导师选拔与匹配、带教目标与计划、过程辅导与记录、效果评估与激励、项目复盘与优化。 |
| `metric-dictionary-writing-tianbao` | 给出指标字典九个必备字段（指标名/业务定义/计算公式/统计维度/时间窗口/数据来源/负责人/更新频率/口径变更记录）、命 |
| `metro-security-check` | 地铁安检：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `metrology-confirmation-tianbao` | 依据 ISO 10012 与 JJF 1112《计量检测体系确认规范》，生成计量确认清单：确认依据（计量要求/校准规范） |
| `mgtv-video-download-tianbao` | 面向想把芒果TV内容留到本地的用户，区分免费内容、会员专有与版权受限内容，说明离线缓存同样加密、电视端与手机端权益不互通 |
| `micro-fire-station-run-tianbao` | 依据《消防安全重点单位微型消防站建设标准》，生成微型消防站运行清单：站点设置（3分钟到场）、人员装备、值守训练、联勤联动 |
| `micro-fire-station-tianbao` | 消防安全重点单位微型消防站的建设标准与日常管理：设置范围、人员配备与持证、装备配置清单、值守制度、训练演练频次、调度联动 |
| `microwave-grease-clean-tianbao` | 微波炉油污与异味清除指南，蒸汽软化法 |
| `microwave-safety-rules` | 微波炉加热禁忌：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `microwave-sparks` | 微波炉打火处理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `midautumn-gift-elders-tianbao` | 中秋送长辈指南：分步骤实操指南 |
| `migu-video-download-tianbao` | 面向想把咪咕视频（含体育、影视、音乐会）存到本地的用户，区分免费内容、会员专享与版权受限内容，说明离线缓存加密、体育赛事 |
| `mineral-vs-pure-water-tianbao` | 矿泉水与纯净水区别：分步骤实操指南 |
| `miniprogram-ad-compliance-tianbao` | 面向小程序广告变现 / 流量主接入的合规核查。核查流量主主体资质、广告位与形式合规（诱导点击/虚假点击/功能捆绑）、广告 |
| `miniprogram-audit-fix-tianbao` | 输入小程序提交审核的基本信息与官方驳回原因原文，归类驳回类型（类目与资质、内容与功能、隐私与授权、诱导分享、外链跳转、技 |
| `miniprogram-content-safety-tianbao` | 面向内容类 / UGC 小程序的微信内容安全合规核查。核查内容审核机制、微信内容安全接口接入、版权与知识产权、诱导分享、 |
| `miniprogram-icp-agent-tianbao` | 输入小程序主体类型、营业执照、域名实名与备案、服务类目与资质、接入商、当前备案状态、是否委托代备案、负责人信息、人脸核验 |
| `miniprogram-icp-check-tianbao` | 输入小程序主体、ICP 备案、服务类目与资质、隐私保护指引等信息，核查是否完成备案、备案主体一致性、特殊类目所需资质、类 |
| `miniprogram-perf-check-tianbao` | 输入小程序的包体积、冷启动耗时、首屏渲染耗时、setData 数据量、接口响应与图片体积等运行指标，对照官方性能参考值给 |
| `miniprogram-privacy-compliance-tianbao` | 小程序个人信息保护合规核查与整改指引。依据《个人信息保护法》(PIPL)、《数据安全法》、GB/T 35273-2020 |
| `miniprogram-verification` | 小程序认证的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `miniprogram-xpay-guide-tianbao` | 面向小程序开发者，核查微信虚拟支付（xpay）接入链路的前置条件、配置、回调发货、合规要点，输出避坑清单与下一步。当用户 |
| `minor-recharge-refund-tianbao` | 孩子背着家长给游戏、直播、短视频、小说充了几千块，平台说"实名是成年人、已尽审查义务"就不退——这个技能先帮你把年龄认定 |
| `mirror-adjustment` | 后视镜调节：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `mirror-limescale` | 镜子水垢：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `mobile-plan-audit-tianbao` | 核算手机套餐实际支出、识别降套与携号转网障碍，输出资费对比、办理话术与投诉路径。 |
| `mogujie-video-download-tianbao` | 面向想把蘑菇街穿搭视频、买家秀存到本地的用户，区分自有店铺内容、已授权素材与第三方作品，说明官方保存、商家后台与合规边界 |
| `momo-live-download-tianbao` | 面向想把陌陌直播回放留存下来的用户，区分主播自有回放、公开回放与粉丝专属回放，说明回放生成条件、保留期与访问限制，给出主 |
| `monitoring-alert-setup` |  |
| `mop-care-guide-tianbao` | 按材质分类的拖把适用场景与保养方法（棉、绒布、平板、旋转 mop、一次性），清洗与彻底晾干的判断方法，更换周期与四个更换 |
| `morning-first-water-tianbao` | 晨起第一杯水：分步骤实操指南 |
| `mortgage-choice-tianbao` | 房贷类型对比、成本测算与申请流程指引 |
| `mortgage-prepay-calc` |  |
| `mosquito-repel-methods-tianbao` | 驱蚊方法大全：分步骤实操指南 |
| `mosquito-repellent-plants` | 驱蚊植物：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `moss-terrarium` | 苔藓微景观：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `motion-sickness-relief` | 晕车缓解：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `motion-sickness-relief-tianbao` | 说明晕车的成因是前庭与视觉信息不一致，逐条讲清哪些方法只是缓解有限、哪些准备真正有效，并按药物类别说明注意事项、儿童与孕 |
| `motorcycle-license` | 摩托车驾照：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `move-in-cleansing` | 入住净化：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `move-out-cleaning-tianbao` | 退租清洁标准：分步骤实操指南 |
| `moving-check-list-tianbao` | 搬迁全流程清单管理指引 |
| `moving-packing-tianbao` | 搬家按类别与频率打包的方法、书籍与被褥的真空压缩适用与禁忌、瓷器玻璃的包裹填充、易碎品标注、证件单独随身，附可打印核查清 |
| `moving-scam-prevention-tianbao` | 搬家公司套路防范：分步骤实操指南 |
| `msa-analysis-tianbao` | 依据 AIAG MSA 手册与 ISO 22514，生成测量系统分析清单：重复性再现性（GRR）、偏倚/稳定性/线性研究 |
| `mushroom-grow-kit-tianbao` | 按菌棒类型给出温湿度与通风口径，逐项列出绿斑、绿霉、酒味等杂菌污染的识别特征与处置顺序，给出出菇管理与采收时机判据。含菌 |
| `music-theory-basics` | 乐理基础：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `mybatis-cache-guide` | MyBatis 缓存：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `mysql-composite-index-tianbao` | 按「最左前缀 + 范围列右侧截断 + 索引列不得被加工」三条基准，逐句式判断联合索引到底用到第几列：缺最左列、跳列、范围 |
| `mysql-explain-analyze-tianbao` | 逐列讲清 EXPLAIN 的 12 个字段怎么看：type 从优到劣的完整排序与各自场景、用 key_len 反推实际用 |
| `mysql-slow-query-tune-tianbao` | 从慢日志 / performance_schema / sys.statements 三条路径定位 TOP 慢 SQL， |
| `nap-duration-science-tianbao` | 午睡时长科学：分步骤实操指南 |
| `nap-posture-tianbao` | 午睡姿势：分步骤实操指南 |
| `nas-beginner` | nas入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `nas-setup-basics` |  |
| `nasal-rinse-usage-tianbao` | 洗鼻器正确使用：就医准备与操作规范指南 |
| `near-miss-tianbao` | 依据事件管理与风险前置理念，生成未遂事件管理清单：未遂事件定义与上报渠道、无责/鼓励报告机制、分级与调查分析、整改与经验 |
| `neck-stretch-routine-tianbao` | 颈椎放松训练与日常习惯改善指引 |
| `neighbor-dispute-evidence-tianbao` | 逐项核查邻里纠纷的纠纷类型、必备要件、证据清单覆盖度、取证手段合法性与损害赔偿时效参考，区分物业协调、行政投诉与诉讼三条 |
| `neighbor-noise-complaint-tianbao` | 邻里噪音投诉：分步骤实操指南 |
| `network-packet-loss-troubleshoot-tianbao` | 按「本机 → 网关 → 运营商 → 目标」四层给出 ping / mtr / traceroute / tcpdump  |
| `new-home-first-cook` | 新房开火：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `new-house-accept-tianbao` | 新房收房验房全流程指引 |
| `new-year-eve-menu` | 年夜饭菜单：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `new-year-eve-tianbao` | 除夕守岁安排：分步骤实操指南 |
| `new-year-greetings-etiquette` | 拜年礼仪：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `new-year-visit-order-tianbao` | 拜年顺序：分步骤实操指南 |
| `night-driver-safety-tianbao` | 夜班司机安全：分步骤实操指南 |
| `night-driving-tips` | 夜间驾驶：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `night-meeting-vehicle` | 夜间会车：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `night-scene-photography-tianbao` | 按安全快门、ISO 上限、闪光灯、曝光补偿与三脚架操作核查夜景参数，给出手持与三脚架两套流程、题材曝光时长参考与常见坑。 |
| `night-shift-allowance-tianbao` | 夜班补贴标准：分步骤实操指南 |
| `night-shift-skincare-tianbao` | 夜班护肤：分步骤实操指南 |
| `night-stall-license-tianbao` | 夜宵摊证照：分步骤实操指南 |
| `night-work-health-check-tianbao` | 夜班工种体检：分步骤实操指南 |
| `nightmare-wakeup-tianbao` | 噩梦惊醒处理：分步骤实操指南 |
| `nitrifying-bacteria` | 硝化细菌：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `no-contract-double-wage-tianbao` | 未签劳动合同双倍工资主张指引，覆盖关系证明/主张/补强三阶段 |
| `noise-complaint-check-tianbao` | 楼上跑跳、邻居音响、广场舞、商铺喇叭、装修电钻、工地夜间施工被吵到，用它判断该找谁、证据够不够、下一步怎么走。输入噪声来 |
| `noise-control-tianbao` | 依据《工业企业噪声控制设计规范》与 GBZ 2.2 职业接触限值，生成噪声控制清单：噪声源识别与检测、岗位暴露评估（8h |
| `nonconforming-control-tianbao` | 依据 ISO 9001 不合格输出控制要求，生成不合格品控制清单：识别与隔离、评审与处置方式（返工/返修/让步/报废）、 |
| `noodle-dough-tianbao` | 面团原料、揉制手法、发酵与失败排查指引 |
| `nosebleed-first-aid` | 流鼻血处理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `numpy-vectorization` | numpy 向量化：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `nutritionist-exam-tianbao` | 公共营养师报名：分步骤实操指南 |
| `occupational-hazard-monitoring-tianbao` | 依据《职业病防治法》与 GBZ 159/189，生成职业病危害因素检测清单：危害因素识别（粉尘/毒物/噪声/放射/高温） |
| `occupational-health-archive-tianbao` | 接触职业病危害作业人员的职业健康监护档案管理与体检合规：档案九项内容、体检四类型与周期表、离岗检查规则、异常处置闭环、档 |
| `occupational-health-surveillance-tianbao` | 依据《职业健康监护技术规范》GBZ 188，生成清单：危害岗位识别与监护项目、上岗前/在岗/离岗体检周期、体检机构与项目 |
| `odor-removal-guide-tianbao` | 全屋异味分诊：下水道返味、装修遗留味、霉味、油烟味、宠物味、织物味、电器味、洗衣机残留、鞋柜柜体等十二类来源的定位方法与 |
| `offer-management-tianbao` | 生成 offer 管理清单：审批与授权（谁可发offer）、核心条款（薪酬/职级/生效日/附条件）、薪酬沟通与谈判、候选 |
| `office-firstaid-kit-tianbao` | 办公室急救包：分步骤实操指南 |
| `official-account-matrix-compliance-tianbao` | 输入公众号矩阵的账号数量、主体类型与一致性、账号类型分布与认证、互推引流方式、诱导关注/分享/集赞、原创与转载授权、名称 |
| `official-account-violation-check-tianbao` | 输入公众号类型、内容领域与来源、运营方式、是否含诱导分享/集赞/诱导下载、标题党、敏感领域资质、营销占比、近期限流或违规 |
| `official-doc-writing-check-tianbao` | 按通知、报告、请示、函、纪要、意见六类文种的适用场景与行文规则选型，核对标题、主送机关、正文、附件说明、发文机关署名、成 |
| `ohsms-45001-tianbao` | 依据ISO 45001:2018，生成职业健康安全管理体系搭建/审核清单：方针、风险机遇、目标、运行控制、应急与绩效监测 |
| `oil-pastel-basics` | 油画棒入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `okr-tianbao` | 依据 OKR（目标与关键结果）方法论，生成 OKR 推行清单：目标(O)设定原则、关键结果(KR)量化、对齐与拉通、周期 |
| `old-furniture-disposal` | 旧家具处理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `old-phone-data-migrate` |  |
| `onboarding-tianbao` | 生成入职引导清单：入职前准备（offer确认/工位/账号）、首日首周计划、导师/伙伴（buddy）机制、30/60/90 |
| `online-return-check-tianbao` | 网购的东西想退、商家拒绝退货、页面写着不支持七天无理由、被扣了运费——用它判断到底能不能退、还剩几天、运费谁出、要留什么 |
| `online-shopping-refund-tianbao` | 网购退货退款维权核查，覆盖证据/平台/升级路径三域 |
| `openclass-video-download-tianbao` | 面向想把公开课、慕课视频存到本地反复学习的用户，区分免费公开课、在校课程与付费证书项目，说明平台是否提供官方离线、课件与 |
| `order-timeout-closing` | 订单超时关闭：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `org-structure-design-tianbao` | 依据组织设计方法论，生成清单：战略与业务对组织的要求、部门划分与职能定位、管理幅度与层级、汇报关系与权责划分、编制配置与 |
| `organ-donation-register` | 器官捐献登记：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `ornamental-fish-care-tianbao` | 给出开缸养水、氨氮与亚硝酸盐等核心水质指标的判断口径、换水与困水操作要求、新鱼过温过水的完整流程、按鱼种与水体密度计算的 |
| `orthodontics-cost-check-tianbao` | 输入正畸/牙齿矫正的机构、方案、报价、增项与付款信息，核查机构与医师资质、隐形矫治器品牌授权、报价与增项是否事前告知、分 |
| `os-reinstall-prep` |  |
| `osteoporosis-diet-tianbao` | 骨质疏松饮食：就医准备与操作规范指南 |
| `outbox-pattern` | outbox模式：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `outlier-detection` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `oven-baking-start-tianbao` | 烤箱烘焙设备认知、基础配方与失败排查指引 |
| `oven-grease-clean-tianbao` | 烤箱内腔油垢清除指南，含加热管防护 |
| `oven-preheat-temp` | 烤箱预热温度：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `oven-temperature-control-tianbao` | 给出华氏与摄氏温度换算表、上下火与风扇模式差异、预热必要性、按食材的温度时间对照表，以及易焦与不熟的具体成因与探针温度计 |
| `overseas-data-roaming` | 境外流量：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `oyster-cleaning` | 生蚝清洗：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `packaging-storage-tianbao` | 依据 ISO 9001 防护要求，生成清单：包装设计与防护等级、标识与搬运要求、仓储环境（温湿度/堆放/先进先出）、库存 |
| `paint-selection-check-tianbao` | 区分乳胶漆与艺术漆、硅藻泥、贝壳粉的特性差异，说明 VOC、甲醛释放与耐擦洗次数等环保指标应该怎么看，基层处理与环境条件 |
| `pan-fish-no-stick` | 煎鱼不粘锅：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `parcel-station-refusal-tianbao` | 驿站拒收处理：分步骤实操指南 |
| `parking-brake-frozen` | 手刹冻住：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `parking-fee-check-tianbao` | 停车被乱收费、小区停车费说涨就涨、车停在收费场被刮没人管、路边被贴条——用它判断这笔钱该不该交、能退多少、找谁、要留什么 |
| `parking-fee-dispute-tianbao` | 停车收费争议处理指引 |
| `parking-scratch-claim` | 停车剐蹭处理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `parking-troubles` | 停车难题：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `parttime-scam-check-tianbao` | 刷单返利骗局的核心是「先给你几十块返利尝甜头，再诱导大额垫资，最后以解冻、补单、保证金为名继续要钱」——这个技能先帮你识 |
| `passport-application-check-tianbao` | 分清首次申领、换发、补发的适用情形与材料差异，核查身份证与照片规格、登记备案人员审批、异地办理条件、办理时限与取证方式， |
| `passport-expedited-tianbao` | 护照加急办理：分步骤实操指南 |
| `password-policy` | 密码强度策略：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `password-storage-design` | 密码存储方案：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `pc-dust-cleaning` | 电脑清灰：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `pc-dust-cleaning-tianbao` | 电脑除尘清灰：分步骤实操指南 |
| `pc-file-sync` |  |
| `pdd-video-download-tianbao` | 面向想把拼多多商品视频、买家秀与直播回放存到本地的用户，区分自有店铺内容、已授权素材与第三方作品，说明官方保存、商家后台 |
| `pearl-care` | 珍珠保养：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `pension-benefit-claim-tianbao` | 抚恤金办理：分步骤实操指南 |
| `pension-verify-tianbao` | 养老金认证：分步骤实操指南 |
| `performance-excellence-tianbao` | 依据 GB/T 19580《卓越绩效评价准则》与 GB/Z 19579，生成卓越绩效自评清单：领导/战略/顾客/测量/员 |
| `performance-review-report-tianbao` | 按「结论-数据-问题-计划」四段搭述职结构，用同比/环比/目标达成率三个口径把业绩算实，核查量化覆盖率、指标口径与基线缺 |
| `performance-review-talk-tianbao` | 按「自评-数据-归因」准备清单和认可/改进/申诉三类话术脚本应对绩效面谈，给出异议处理五步路径、书面申诉的正式表达格式与 |
| `performance-system-tianbao` | 依据绩效管理方法论，生成绩效体系清单：战略解码与目标分解、指标库(KPI/OKR)、考核周期与权重、绩效面谈与反馈、结果 |
| `perm-maintenance` | 烫发维持：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `personal-archive-keeping` | 档案存放：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `personnel-archive-custody-tianbao` | 判定档案该由谁保管、转递该走什么通道，核查托管与转递材料清单、严禁个人自带与私自拆封的红线、死档成因与处置路径，输出可直 |
| `pest-control-log-tianbao` | 虫鼠防治记录：分步骤实操指南 |
| `pet-bath-skill-tianbao` | 宠物洗澡操作与洗后护理指引 |
| `pet-boarding-dispute-check-tianbao` | 输入宠物寄养/寄养协议与纠纷事实，核查寄养方与平台的免责条款效力、宠物意外与死亡的过错责任、押金与余款退费规则、超期与临 |
| `pet-deworming-cycle-tianbao` | 按体内外驱虫的作用对象差异给出周期核查口径，逐项列出给药间隔、与疫苗的间隔、体重口径的确认要求，并给出异常反应与延误风险 |
| `pet-medical-dispute-tianbao` | 核查宠物医疗纠纷的证据是否齐备（病历、处方、知情同意、尸检、监控）、识别未做项目收费与重复收费等十类乱收费，并按购买价与 |
| `pet-neuter-surgery-check-tianbao` | 按术前检查项、年龄与体重窗口、发情期时机、术后拆线与活动限制逐项核查，并给出出血、粘连、切口裂开三类并发症的识别信号与就 |
| `pet-shipping-quarantine-tianbao` | 宠物托运检疫：分步骤实操指南 |
| `pet-teeth-brushing` | 宠物刷牙：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `pet-toilet-training-tianbao` | 按犬猫各自的排便习性做定点训练：先定如厕点，再用时机捕捉与奖励固化，最后排查乱拉是行为问题还是疾病信号。含训前体检红线、 |
| `pet-vaccine-interval-tianbao` | 按核心与非核心疫苗的区分给出接种程序表的核查口径，逐项列出首免与加强间隔、与驱虫的间隔、接种后不良反应观察项与免疫失败迹 |
| `pet-vaccine-reactions` | 宠物疫苗反应：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `pet-vomit-judge-tianbao` | 宠物呕吐分类观察与就医判断指引 |
| `pg-table-partitioning` | pg分区表：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `phone-battery-health-tianbao` | 手机电池保养、续航优化与更换判断指引 |
| `phone-data-migration` | 手机换机迁移：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `phone-photo-composition-tianbao` | 按七种构图法核查照片主体位置、水平倾斜、地平线、头顶留白与画面杂物，给出坐标化合格区间、六项自查、问题分级与整改顺序。 |
| `phone-points-redeem-tianbao` | 话费积分兑换：分步骤实操指南 |
| `phone-repair-scam-check-tianbao` | 输入手机维修的维修方、报修问题、对方诊断、报价与已付、是否官方售后、是否换件原装、旧件是否归还、维修后是否复发等信息，核 |
| `phone-screen-protector-tianbao` | 手机贴膜技巧：分步骤实操指南 |
| `phone-storage-clean-tianbao` | 手机存储空间分析与长期清理策略指引 |
| `phone-storage-cleanup-tianbao` | 按占用类别逐项清理手机空间：区分照片视频、应用本体、应用缓存、聊天记录、下载目录与系统文件，给出每一类的清理方式与风险等 |
| `photo-deposit-refund-tianbao` | 摄影定金退还：分步骤实操指南 |
| `photo-sort-by-date` |  |
| `piano-fingering-practice-tianbao` | 给出钢琴指法编号规则、音阶与琶音指法表、手型自查项、慢练与提速口径、分手练习流程与常见错误纠正。 |
| `piano-moving-tianbao` | 钢琴搬运：分步骤实操指南 |
| `piano-note-read-tianbao` | 五线谱谱表、音位、时值与视奏练习入门指引 |
| `pickle-making-guide-tianbao` | 家常腌菜盐量配比、发酵温度与亚硝酸盐安全要点 |
| `pickled-vegetables` | 腌制咸菜：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `pillbug-control` | 潮虫处理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `pillow-replacement` | 枕头更换：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `pinterest-video-download-tianbao` | 面向想把 Pinterest 上的视频图钉存到本地的用户，区分自有发布、已授权素材与第三方作品，说明官方保存、账号后台与 |
| `pipe-freeze-prevention-tianbao` | 寒潮水管防冻：分步骤实操指南 |
| `pipixia-video-download-tianbao` | 面向想把皮皮虾短视频存到本地的用户，区分自有作品、已授权素材与第三方作品，说明官方保存、创作者后台与合规边界，给出留存方 |
| `plank-training-check-tianbao` | 给出平板支撑的姿势标准、塌腰与撅臀等错误判定、时长与组数剂量、退阶与进阶、呼吸要求和停练红线。 |
| `plant-cutting-propagation` | 扦插方法：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `plant-pest-identification-tianbao` | 按症状部位、形态与分布特征区分常见病虫害，逐项给出可能病因与处理方式类别，并标明用药以当地植保部门指导和产品登记为准。含 |
| `plantar-fasciitis-relief-tianbao` | 足底筋膜炎缓解：就医准备与操作规范指南 |
| `plastic-bag-organizing` | 塑料袋收纳：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `plastic-wrap-use` | 保鲜膜用法：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `plum-rain-mold-prevention-tianbao` | 梅雨季防霉：分步骤实操指南 |
| `plumbing-wiring-acceptance-tianbao` | 装修水电工程打压测试、绝缘电阻与验收要点的检查清单 |
| `poka-yoke-tianbao` | 依据防错（Poka-Yoke）技术方法论，生成防错设计清单：错误类型识别（遗漏/错装/超量）、防错装置（接触/定数/动作 |
| `police-record-request-tianbao` | 110报警记录调取：分步骤实操指南 |
| `policy-cash-value-tianbao` | 按合同载明的现金价值表读数与已交保费逐档核算退保损失，区分犹豫期内与犹豫期外的退还口径，说明现金价值表的读法、保单年度对 |
| `pollutant-permit-tianbao` | 依据《排污许可管理条例》与HJ 608，生成排污许可管理清单：许可证执行、自行监测、台账、执行报告（月/季/年）与合规自 |
| `port-unreachable-troubleshoot-tianbao` | 按「目标是否在监听 → 本机能否出网 → 中间链路是否阻断 → 目标侧防火墙与安全组」四层给出 telnet/nc/ss |
| `portrait-posing-guide-tianbao` | 按十二项自查核查人像摆姿，给出镜头焦段、重心腿、手臂三角、转体角度、下巴前伸、裁切位置与留白的合格口径，附三组万能摆姿与 |
| `post-flood-car-check` | 涉水后检查：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `postal-complaint-tianbao` | 邮政快递投诉办理指引，含 12305 申诉路径 |
| `postgres-vacuum-guide` | Postgres VACUUM 指南：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `postpartum-recovery-timeline-tianbao` | 产后修复时间表：就医准备与操作规范指南 |
| `postpartum-refund-check-tianbao` | 针对月子中心、产后康复机构中的预付费不退、服务缩水、护理不当致母婴损害、合同主体与收款方不一致、跑路等纠纷，做信息采集、 |
| `pot-bottom-black-removal-tianbao` | 锅底除黑：分步骤实操指南 |
| `pothos-care` | 绿萝养护：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `potted-plant-repotting-tianbao` | 按根系盘根、盆底孔出水、土板结三类信号判断是否该换盆，给出盆径跳跃幅度与配土比例、换盆后缓苗期管理与换盆失败征兆。含换盆 |
| `poultry-vaccine-tianbao` | 家禽防疫：分步骤实操指南 |
| `pour-over-coffee-guide-tianbao` | 给出手冲咖啡的粉水比、研磨度、水温、分段注水与总时长口径，以及萃取不足与过度的判断和单变量调整流程。 |
| `power-of-attorney-notarization-tianbao` | 逐项核查授权委托书的六项必备要素（委托人 / 受托人 / 代理事项 / 权限范围 / 有效期限 / 签名捺印）、办理条件 |
| `powerbank-flight-rules` | 充电宝托运：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `powerquery-cleaning` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `ppap-tianbao` | 依据 AIAG PPAP 手册与 IATF 16949，生成 PPAP 提交清单：提交等级（1~5）、18 项要素（设计 |
| `ppe-management-tianbao` | 劳动防护用品的全流程管理：按岗位危害选型（GB/T 11651）、采购与验收、发放标准与台账、使用培训、定期更换、报废回 |
| `pptv-video-download-tianbao` | 面向想把 PP 视频内容存到本地的用户，区分免费影视、会员专享与版权受限内容，说明离线缓存加密、会员权益差异，给出合规的 |
| `preconception-checkup-list-tianbao` | 备孕检查项目清单：就医准备与操作规范指南 |
| `pregnancy-medication-safety-tianbao` | 孕期用药安全须知：就医准备与操作规范指南 |
| `prenatal-checkup-tianbao` | 按孕周整理产检项目时间表、报告指标与异常提示，输出记录表和问医生的问题清单。 |
| `prepaid-card-check-tianbao` | 输入预付卡（健身/美容/教育/餐饮等）消费与商家现状，核查退款条款效力、应退余额、商家跑路风险，并给出 12315、商务 |
| `preschool-transition-check-tianbao` | 用八大能力维度的核查清单判断孩子是否做好入学准备，输出入学前 3 个月倒排准备表，并纠正「提前学一年级知识」的常见误区。 |
| `pressure-cooker-safety-tianbao` | 给出高压锅十项安全红线自检、按食材的压力档位匹配表、必须立即停用的情形与八条明确禁止的操作，重点锁定压力未释放严禁强行开 |
| `pressure-ulcer-prevention-tianbao` | 用描述性分期口径识别压疮进展，按受压风险给出翻身间隔参考，并列出减压措施、营养与失禁管理要点和必须转诊的情形。 |
| `pressure-vessel-check-tianbao` | 逐台核查压力容器使用登记状态与全面检验、年度检查、耐压试验、安全阀校验、压力表检定的到期日，输出剩余天数与预警分级。 |
| `preview-review-planner-tianbao` | 给出预习三步法与复习间隔安排，把计划表字段设计为任务/预计耗时/完成标准/优先级四栏，并提供计划失败的归类诊断与错题 2 |
| `printer-paper-jam-fix-tianbao` | 按进纸方向安全取纸并找出反复卡纸的真实原因：含卡纸位置对照、断电与高温烫伤红线、残片清理方法、搓纸轮与分离垫检查、纸张存 |
| `printer-sharing-setup` |  |
| `probation-mgmt-tianbao` | 依据《劳动合同法》第十九条/二十一条，生成试用期合规清单：期限合法性、可举证录用条件、工资≥80%与考核解除程序。 |
| `process-audit-tianbao` | 依据 VDA 6.3 与 IATF 16949，生成过程审核清单：审核范围与过程识别（P2~P7）、提问表与评分（0/4 |
| `process-safety-tianbao` | 依据《化工企业工艺安全管理实施导则》AQ/T 3034，生成工艺安全管理清单：工艺安全信息(PSI)、PHA  haza |
| `procrastination-breakthrough-tianbao` | 给出任务拆分到五到十五分钟颗粒、缩小开始动作、两分钟法则、固定启动时间地点与环境准备等可执行方法，并按成因分类给不同对策 |
| `product-audit-tianbao` | 依据 IATF 16949 与 VDA 6.5 产品审核要求，生成产品审核清单：审核对象与抽样、检验特性（外观/尺寸/功 |
| `product-safety-liability-tianbao` | 依据《产品质量法》与产品责任要求，生成清单：安全特性识别与警示说明、合规标准与认证、缺陷追溯与召回、责任风险与产品保险、 |
| `projector-keystone-correction-tianbao` | 先摆位后校正的投影画面调校：含投射距离与画幅换算、梯形与四角校正的代价、光学镜头位移优先原则、吊装与高空作业安全红线、画 |
| `prometheus-metrics-alert-tianbao` | 写 exporter 前先定取名：namespace_subsystem_name_unit_suffix 全小写下划线 |
| `promotion-management-tianbao` | 依据晋升管理实践，生成清单：晋升通道与职级标准、晋升条件与年限、评审流程与评委构成、公示与申诉机制、晋升后跟踪与反馈。 |
| `property-company-replace-tianbao` | 物业公司更换：分步骤实操指南 |
| `property-fee-dispute-check-tianbao` | 把物业费争议拆成本金、滞纳金、时效三层核算，对照三级抗辩事由分级库判断哪些能免、哪些只能减、哪些说了没用，输出无争议金额 |
| `property-fee-hearing-tianbao` | 物业费调价听证：分步骤实操指南 |
| `property-repair-fund-tianbao` | 住宅专项维修资金使用监督指引 |
| `prosthesis-fitting-tianbao` | 假肢适配流程：分步骤实操指南 |
| `puppy-feed-tianbao` | 幼犬口粮选择、行为基础与健康信号指引 |
| `putonghua-test-check-tianbao` | 按分数判定普通话三级六等等级、核查是否达到语文教师与其他学科教师等用途的等级要求、判断证书是否长期有效、测算复测间隔是否 |
| `pwa-offline` | pwa离线：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `qc-circle-tianbao` | 依据《QC 小组活动准则》T/CAQ 10201，生成 QC 小组活动清单：小组组建与注册、PDCA 活动程序、课题类型 |
| `qc-seven-tools-tianbao` | 依据质量管理老七种工具方法，生成 QC 七大手法应用清单：检查表、层别法、柏拉图、因果图、散布图、直方图、控制图的数据收 |
| `qfd-tianbao` | 依据 QFD 方法，生成质量屋清单：顾客需求（VOC）收集与重要度、技术特性与相关矩阵、关系矩阵与重要度排序、向零部件/ |
| `qms-document-system-tianbao` | 质量管理体系四层文件架构设计与受控管理：质量手册、程序文件、作业指导书、记录表单的编号规则、编制审核批准流程、发放回收、 |
| `qms-internal-audit-tianbao` | ISO 9001 内部审核的全流程组织：年度审核方案编制、检查表设计、现场审核技巧、不符合开具与分级、末次会议与报告、纠 |
| `qms-management-review-tianbao` | 质量管理体系管理评审的组织与输出：评审输入九项材料准备、会议组织流程、评审报告要素、改进决议跟踪、与内审和战略的衔接。输 |
| `qms-manual-tianbao` | 依据 GB/T 19001-2016 文件化信息要求，生成清单：组织环境与范围界定、过程框架与相互关系、方针目标与职责权 |
| `qms-records-control-tianbao` | 质量管理体系记录的受控管理：记录清单建立、填写规范（现在时/不空栏/划改留痕）、归档与检索、保存期限、电子记录备份、销毁 |
| `qq-music-video-tianbao` | 面向想把 QQ 音乐里的 MV、视频与直播回放存到本地的用户，区分自有上传、已授权素材与第三方作品，说明官方保存、创作者 |
| `qqzone-video-download-tianbao` | 面向想把 QQ 空间（说说、相册、日志）里的视频存到本地的用户，区分自有发布、已授权素材与第三方作品，说明官方保存、空间 |
| `quality-agreement-tianbao` | 依据采购与供方管理实践，生成清单：协议主体与适用范围、质量标准与验收准则、不合格与索赔条款、变更与通知义务、保密与知识产 |
| `quality-certification-tianbao` | 依据 ISO 9001 等体系认证流程，生成清单：认证范围与机构选择、体系运行与内审管评、文件与记录准备、现场迎审与陪同 |
| `quality-culture-tianbao` | 依据质量文化实践，生成清单：质量价值观与方针宣贯、全员参与与提案改善、质量激励与追责机制、质量培训与案例教育、氛围评估与 |
| `quality-data-analysis-tianbao` | 依据质量数据统计实践，生成清单：数据类型与采集（计量/计数）、分层与帕累托分析、趋势与控制图判异、相关与回归分析、结论与 |
| `quality-kpi-tianbao` | 依据 ISO 9001 质量目标要求，生成清单：目标承接战略并可测量、逐层分解到部门与岗位、指标定义与计算口径、监测频次 |
| `quality-month-tianbao` | 依据全国“质量月”活动部署与企业实践，生成质量月方案：主题与目标、活动矩阵（宣传/培训/竞赛/改进）、全员参与与成效固化 |
| `quality-redline-tianbao` | 依据 ISO 9001 与制造企业质量管理实践，生成质量红线与三不原则清单：质量红线清单、三不原则（不接收/不制造/不流 |
| `quality-risk-management-tianbao` | 依据 ISO 9001 基于风险的思维与 FMEA 方法，生成清单：风险识别（产品/过程/体系）、风险评价（严重度/发生 |
| `quanmin-video-download-tianbao` | 面向想和全民小视频存到本地的用户，区分自有作品、已授权素材与第三方作品，说明官方保存、创作者后台与合规边界，给出留存方式 |
| `rabbit-care-guide-tianbao` | 按兔龄给出兔笼空间、垫料与每日护理口径，定出以牧草为主的饮食结构、禁忌食物表、磨牙与清洁要求，并列出牙齿与消化道异常的观 |
| `rabbit-heat-signs` | 兔子上火：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `radiator-bleeding` | 暖气片放气：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `raft-consensus` | raft共识：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `rag-doc-chunking-strategy-tianbao` | 给四类切分策略（固定长度/按结构/语义/父子块）的适用场景与取舍，给出 chunk size 与 overlap 的取值 |
| `rainy-driving-tips` | 雨天驾驶：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `range-hood-check-valve` | 油烟机止逆阀：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `range-hood-cleaning` | 油烟机清洗周期：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `range-hood-deep-clean-tianbao` | 抽油烟机深度清洗指南，含拆机防护与动平衡检查 |
| `range-hood-degrease` | 油烟机重油除垢：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `range-hood-duct` | 油烟机管道清理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `range-hood-filter-soak` | 油烟机滤网浸泡：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `range-hood-mesh-clean-tianbao` | 油烟机油网清洗：分步骤实操指南 |
| `range-hood-noise` | 油烟机异响：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `rat-control` | 老鼠防治：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `rate-limit-algorithms` | 限流算法：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `react-rerender-optimize-tianbao` | 先量化再优化：Profiler 的 Flamegraph 与 Ranked 面板配合 Record why each c |
| `reading-comprehension-skill-tianbao` | 把阅读理解拆成六类题型并给出各自的定位动作，逐项列出选项常见陷阱类型与比对方法，配套限时训练与错因归类表。 |
| `reading-glasses-fitting` | 老花镜选配：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `reboil-water-harm-tianbao` | 饮水机反复加热危害：分步骤实操指南 |
| `recall-management-tianbao` | 依据缺陷产品召回要求与《消费品召回管理暂行规定》，生成清单：缺陷识别与风险评估、召回决策与分级、召回计划与公告、实施与进 |
| `recommendation-letter-check-tianbao` | 按关联度、了解深度、职称公信力、表达意愿四项给推荐人打分，按四段结构核查推荐信要素，核字数与具体事例条数。 |
| `recruitment-funnel-tianbao` | 生成招聘漏斗分析清单：漏斗阶段定义（曝光/投递/筛选/面试/offer/入职）、各环节转化率、瓶颈识别、优化建议与数据周 |
| `recruitment-roi-tianbao` | 依据人力资源管理 ROI 方法，生成招聘 ROI 分析清单：招聘成本（渠道/猎头/内推）、到岗质量、留存表现、投产比（价 |
| `recycling-sorting` | 废品分类回收：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `red-eye-flight-rest` | 红眼航班休息：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `reddit-video-download-tianbao` | 面向想把 Reddit 上的公开视频存到本地的用户，区分自有发布、已授权素材与第三方作品，说明官方保存、账号后台与合规边 |
| `redis-bigkey-cleanup` | Redis 大 Key 清理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `redis-persistence-choose-tianbao` | 按「能接受丢多少数据」这一个问题的答案选持久化方案：RDB 丢最后一次快照后的全部写入、AOF everysec 丢 1 |
| `rednote-image-save` |  |
| `rednote-return-process` | 小红书退货流程：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `reference-material-tianbao` | 依据 CNAS-CL01 与计量相关要求，生成清单：标准物质（有证/内部）台账与有效期、储存条件与标识、期间核查策划与频 |
| `referral-probation-tianbao` | 生成内推与试用期管理清单：内推流程与激励、质量把控（筛选/背调），及试用期考核标准、转正与解除合规（劳动合同法）。 |
| `refrigerator-defrost-tianbao` | 按冷冻室结霜厚度四档给出是否化霜的判断与建议周期，明确严禁刀凿与热水浇淋的正确做法、化霜期间食品处理与回温后再放回的顺序 |
| `regression-analysis-basics` |  |
| `relationship-safety-check-tianbao` | 输入相识渠道、见面与身份核实情况、是否出现索要转账或推荐投资理财、情感推进节奏、是否存在贬低/冷热交替/限制社交/查岗控 |
| `reliability-engineering-tianbao` | 依据可靠性工程方法，生成可靠性清单：可靠性指标（MTBF/可用度/失效率）、建模与预计、可靠性试验（环境/寿命/加速）、 |
| `reno-budget-control-tianbao` | 装修预算分配、报价审阅与合同要点指引 |
| `renovation-quote-check-tianbao` | 拿装修报价单逐行核查：判断是全包/半包/整装、九项必看项缺了哪几项、哪些是"按实际/另计/不含"这类开口条款、报价单项数 |
| `rent-contract-read-tianbao` | 租房合同审查与退租交割指引 |
| `rent-deposit-check-tianbao` | 把退租时被扣的押金逐条判「正当 / 存疑 / 不成立」，算清押金性质（押金没有双倍返还，定金才适用定金罚则）、应退日与逾 |
| `rent-deposit-refund-tianbao` | 租房押金退还维权核查，含损耗界定与催告路径 |
| `rental-meter-reading-tianbao` | 租房水电抄表交接：分步骤实操指南 |
| `rental-scam-agents` | 租房黑中介：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `report-logic-building-tianbao` | 用金字塔结构（结论先行、以上统下、归类分组、逻辑递进）搭汇报骨架，以 SCQA 引入开场，按 MECE 检查分组是否穷尽 |
| `residence-permit-check-tianbao` | 逐项核查居住证的申办路径、材料清单、居住登记半年级门槛、签注期限与逾期后果、积分材料覆盖度。输出可直接照着备材料的核查表 |
| `resume-screening-scorecard-tianbao` | 用 100 分制多维评分卡替代"凭感觉看简历"：七维度权重、S/A/B/C/D 分档、硬性红线一票否决、邀约优先级排序、 |
| `retention-analysis-definition-tianbao` | 把次日/7日/30日留存的口径、回访窗口与分组基准一次写清，给出加权留存率与流失率的互算校验、按注册日与按活跃日分组的差 |
| `retention-curve-reading` |  |
| `return-ticket-waitlist-tianbao` | 返程票候补技巧：分步骤实操指南 |
| `rework-repair-tianbao` | 依据不合格输出控制与返工返修要求，生成清单：返工与返修的区分、作业指导与授权、返工后重新检验、返修的批准与顾客告知、记录 |
| `rice-cooker-buying` | 电饭煲选购：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `rice-cooker-coating-care-tianbao` | 电饭煲内胆涂层保养：分步骤实操指南 |
| `rice-cooker-maintenance` | 电饭煲保养：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `rice-flour-pests` | 米面防虫：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `rice-washer-tips` | 淘米技巧：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `rice-water-ratio` | 煮饭比例：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `rice-wine-brewing` | 自酿米酒：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `ride-hailing-tianbao` | 覆盖滴滴、高德打车、花小猪、曹操出行、美团打车、腾讯出行等主流网约车平台的使用、省钱、乱扣费/绕路维权、发票报销、行程安 |
| `risk-classification-tianbao` | 依据双重预防机制与《安全风险分级管控体系通则》，生成风险分级管控清单：风险点辨识、评价分级（红橙黄蓝）、管控措施与四色图 |
| `rj45-crimping` | 网线水晶头：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `road-hazard-avoidance` | 马路避险：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `road-trip-planning-tianbao` | 按里程与油耗口径做自驾游测算，说明高速与国道油耗差异、出发前检查清单、路况与限行查询方法、疲劳驾驶休息间隔、恶劣天气约束 |
| `robot-vacuum-maintenance` | 扫地机器人养护：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `robot-vacuum-obstacle` | 扫地机避障：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `robot-vacuum-parts-tianbao` | 扫地机器人耗材更换：分步骤实操指南 |
| `rolling-update-strategy` | 滚动更新：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `root-cause-5why-tianbao` | 依据根因分析方法论，生成 5Why 分析清单：问题界定、逐层追问（5 层）、验证根因、制定对策与防再发、横向展开。 |
| `rose-pruning-guide-tianbao` | 按品种类型与本地气候给出月季修剪的时机窗口、工具消毒要求、留芽方向与剪口角度，以及花后、病枝、冬季三类修剪的操作步骤，并 |
| `router-firmware-upgrade` |  |
| `rug-anti-slip` | 地毯防滑：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `runner-knee-prevention-tianbao` | 跑步膝预防：就医准备与操作规范指南 |
| `running-posture-check-tianbao` | 给出步频、触地方式、落地点、垂直振幅、躯干前倾、摆臂等指标的判定口径与纠正动作，以及负荷递增上限与疼痛停跑清单。 |
| `rural-dangerous-house-tianbao` | 农村危房改造申请：分步骤实操指南 |
| `rural-housing-reinforce-tianbao` | 农房抗震改造申请：分步骤实操指南 |
| `rural-medical-insurance-tianbao` | 农村合作医疗缴费：分步骤实操指南 |
| `rural-toilet-subsidy-tianbao` | 农村改厕补贴：分步骤实操指南 |
| `s3-lifecycle-policy` | S3 生命周期策略：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `safety-cost-tianbao` | 依据《企业安全生产费用提取和使用管理办法》，生成安全生产费用清单：提取依据与比例、使用范围（安全/培训/应急/隐患治理） |
| `safety-culture-tianbao` | 依据《企业安全文化建设导则》AQ/T 9004，生成安全文化建设清单：安全承诺、行为规范与程序、安全培训与沟通、安全激励 |
| `safety-education-training-tianbao` | 依据《安全生产法》与《生产经营单位安全培训规定》，生成安全教育培训清单：培训对象（三级/特种/管理人/全员）、三级安全教 |
| `safety-liability-insurance-tianbao` | 依据《安全生产责任保险实施办法》与新《安全生产法》第五十一条，生成安责险清单：强制投保范围、投保主体与责任限额、保险+事 |
| `safety-production-license-tianbao` | 依据《安全生产许可证条例》，生成清单：取证范围与条件、安全投入与机构人员配备、安全评价与工伤保险、申报材料与审查、有效期 |
| `safety-standardization-tianbao` | 依据《企业安全生产标准化基本规范》GB/T 33000，生成安全生产标准化清单：目标/责任/制度/教育/现场/风险/应急 |
| `salad-dressing` | 沙拉酱汁：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `salad-pairing` | 沙拉搭配：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `salary-band-tianbao` | 依据薪酬体系设计方法，生成薪酬带宽清单：职级序列、带宽宽度（中位值±%）、级差、市场分位对标、重叠度、晋升路径。 |
| `salary-negotiation-tianbao` | 用锚定区间报价、用「到手现金 + 公积金双边 + 福利 + 期权年化」的全成本口径横向对比多个 Offer，按加班与通勤 |
| `salary-structure-tianbao` | 依据薪酬设计方法论，生成薪酬结构清单：薪酬构成（固定/浮动/津贴）、固浮比与岗位差异、绩效工资挂钩规则、津补贴与福利项目 |
| `salary-survey-tianbao` | 生成薪酬调研方案与数据分析：职位匹配、样本渠道、分位值（P25/P50/P90）、内外部公平性诊断与调薪建议，对接BOS |
| `sample-size-calc` |  |
| `sampling-inspection-tianbao` | 依据 GB 2828.1《计数抽样检验程序》与 ISO 2859，生成抽样检验清单：抽样标准、检验水平与 AQL、正常/ |
| `sauce-mix-basic-tianbao` | 基础味型与常用酱汁调配配方指引 |
| `scaffold-safety-tianbao` | 依据《建筑施工脚手架安全技术统一标准》GB 51210，生成清单：方案编制与审批、材质与构配件检查、立杆基础与扫地杆、连 |
| `scarf-tying` | 丝巾系法：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `school-bullying-response-tianbao` | 用五维判定口径区分霸凌与普通冲突，给出取证路径、处置顺序、受欺凌方与围观同学的话术，明确禁止以暴制暴。 |
| `school-transfer-midterm-tianbao` | 孩子转学插班：分步骤实操指南 |
| `screen-window-repair-tianbao` | 纱窗修补：分步骤实操指南 |
| `seal-carving-basics` | 篆刻入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `seasickness-relief` | 晕船应对：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `secondhand-dispute-check-tianbao` | 输入二手交易的平台、商品描述、付款方式、收货与纠纷事实，核查交易方式风险、七天无理由退货的适用边界、描述不符与假货的责任 |
| `secondhand-house-inspection-tianbao` | 二手房收房验房的分区检查清单与缺陷判定口径 |
| `secondhand-trade-tianbao` | 覆盖闲鱼、转转、拍拍、找靓机、闲转等二手交易平台的使用、验货、防骗与维权指南。用「稳定入口 + 通用三步定位法 + 止损 |
| `seed-germination` | 种子催芽：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `senior-discount-card-tianbao` | 老年优待证办理：分步骤实操指南 |
| `senior-fall-proofing-tianbao` | 老人居家防跌倒改造：就医准备与操作规范指南 |
| `server-daily-inspection-tianbao` | 按 CPU / 内存 / 磁盘 / IO / 负载 / 时钟 / 日志 七类给出具体阈值与正常区间，逐项判定「正常 /  |
| `server-remote-login-failure-tianbao` | 按「客户端 → 网络与端口 → sshd 服务与配置 → 认证策略 → 连接数与资源」五层给出 ssh -vvv 关键日 |
| `session-fixation-defense` | 会话固定攻击：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `seven-day-return-check-tianbao` | 逐项核查七日无理由退货的例外情形与商品完好判断标准，说明起算时点口径与运费承担、换货退货差异及举证责任分配。 |
| `sewing-stitch-guide-tianbao` | 按布料类型、破损形态与受力情况选对手缝针法，给出回针缝、缭针缝、藏针缝、锁边缝、贴布补丁的适用范围与步骤，并核对手缝针号 |
| `shared-utility-dispute-tianbao` | 水电公摊异议：分步骤实操指南 |
| `sheer-curtain-washing` | 纱帘清洗：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `shingles-care-tianbao` | 给出带状疱疹的皮疹护理、隔离口径、抗病毒就医窗口和后遗神经痛风险自查与预防要点。 |
| `shirt-collar-yellowing` | 衬衫领口发黄：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `shoe-cabinet-odor` | 鞋柜除臭：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `shoe-care-guide-tianbao` | 皮鞋与运动鞋清洁养护的实操指南 |
| `short-video-camera-move-tianbao` | 按起幅、运镜段、落幅三段结构核查每个镜头，给出八种运镜手法、五条硬约束、四条使用约束、运镜目的清单与整片节奏判定。 |
| `shower-holder-replace-tianbao` | 花洒支架更换：分步骤实操指南 |
| `shower-scale-removal` | 淋浴房水垢：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `showerhead-descale-tianbao` | 花洒除垢：分步骤实操指南 |
| `sibling-conflict` | 多孩矛盾：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `side-hustle-launch-tianbao` | 从每周可用小时出发算清副业产能、单位时间收益与回本周期，给出试错成本上限、止损线与四类副业的启动门槛对比，避免把主业时间 |
| `silicone-mold` | 玻璃胶发霉：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `silicone-mold-remove-tianbao` | 玻璃胶除霉：分步骤实操指南 |
| `silk-care-wash-tianbao` | 真丝衣物洗护指南，覆盖清洗/干燥/整烫/禁忌四阶段 |
| `silk-quilt-care` | 桑蚕丝被：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `silk-washing-tianbao` | 真丝洗涤：分步骤实操指南 |
| `silver-tarnish` | 银饰发黑：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `sing-breath-train-tianbao` | 唱歌呼吸支撑、发声练习与嗓音保护指引 |
| `singing-pitch-correction-tianbao` | 给出音准偏差的分级口径、跑调成因拆分、逐日训练流程、伴奏与监听设置、常见误区与就医提示。 |
| `singing-techniques` | 唱歌技巧：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `sink-hair-clog-tianbao` | 洗手盆毛发堵塞疏通指南，含过滤网预防 |
| `sit-stand-habit-tianbao` | 久坐间断与微运动习惯养成指引 |
| `six-sigma-tianbao` | 依据六西格玛管理方法论，生成 DMAIC 改进清单：定义（DCTQ/项目章程）、测量（Y 与 X 数据）、分析（根因/假 |
| `sketching-basics` | 素描基础：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `skewer-grill-tips` | 串串签子：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `slaughter-quarantine-tianbao` | 屠宰检疫流程：分步骤实操指南 |
| `sleep-hygiene-tianbao` | 睡眠卫生改善指引，含刺激控制与就医判断 |
| `sleep-paralysis-tianbao` | 睡眠瘫痪应对：分步骤实操指南 |
| `sleeping-pill-dependence-tianbao` | 安眠药依赖防范：分步骤实操指南 |
| `sleepwalking-response-tianbao` | 梦游处理：分步骤实操指南 |
| `slippers-disinfection` | 拖鞋消毒：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `slow-api-hunting` | 慢接口排查：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `smart-fire-platform-tianbao` | 依据《城市消防远程监控系统技术标准》GB 50440 与智慧消防建设要求，生成智慧消防平台建设清单：物联感知（烟感/用电 |
| `smart-lock-fingerprint-fix-tianbao` | 按现象定位智能门锁指纹失灵的真实原因并给出应急开锁顺序：含故障树、指纹重录规范、机械与门体检查、应急供电与机械钥匙使用顺 |
| `smoke-control-tianbao` | 依据《建筑防烟排烟系统技术标准》GB 51251，生成防烟排烟系统核查清单：防烟分区、机械加压送风、机械排烟、自然排烟、 |
| `sms-provider-selection` | 短信通道选择：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `smzdm-video-download-tianbao` | 面向想和什么值得买里的好物视频存到本地的用户，区分自有发布、已授权素材与第三方作品，说明官方保存、账号后台与合规边界，给 |
| `snoring-cause-check-tianbao` | 打呼噜原因排查：分步骤实操指南 |
| `snoring-relief` | 打鼾应对：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `snow-driving` | 雪天行车：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `snow-loaded-roof-tianbao` | 大雪压棚处理：分步骤实操指南 |
| `social-card-loss` | 社保卡挂失：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `social-insurance-transfer-tianbao` | 社保跨地区转移接续办理与断缴影响指引 |
| `social-security-backpay` |  |
| `social-security-retroactive-payment-tianbao` | 核查社保补缴的适用情形与不可补缴情形、养老与医保累计缴费年限认定口径、视同缴费年限、补缴本金与滞纳金测算、材料清单与办理 |
| `social-security-transfer-tianbao` | 换城市工作、多地参保的人，用它判断社保能不能转、卡在哪、养老待遇领取地会落在哪。输入参保地与缴费年限，输出能不能办的硬性 |
| `socket-overheat-fix-tianbao` | 插座发热处理：分步骤实操指南 |
| `sofa-care-guide-tianbao` | 不同材质沙发清洁保养的实操指南 |
| `sofa-stain-removal` | 沙发污渍清理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `soft-boiled-egg` | 溏心蛋火候：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `sohu-video-download-tianbao` | 面向想把搜狐视频内容存到本地的用户，区分免费影视、会员专享与版权受限内容，说明离线缓存加密、会员与电视端权益差异，给出合 |
| `soil-compaction-fix-tianbao` | 给出土壤板结的判断口径与成因排查，讲清停践踏、浅松土、增施腐熟有机质、覆盖、轮作绿肥的改良五步与顺序，以及改良前后的记录 |
| `soilless-growing` | 无土栽培：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `solid-wood-floor-care-tianbao` | 实木地板保养与划痕修复指南 |
| `solo-female-safety-tianbao` | 独居女性防护：分步骤实操指南 |
| `soup-deodorize` | 炖汤去腥：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `souvenir-gift-picking-tianbao` | 伴手礼挑选：分步骤实操指南 |
| `soybean-grinding` | 磨豆浆：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `soymilk-maker` | 豆浆机使用：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `space-heater-safety` | 取暖器安全使用：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `spc-control-chart-tianbao` | 依据 SPC 原理与 GB/T 4091，生成统计过程控制清单：控制图选择、判异准则、过程能力 CPK/PPK 分析与异 |
| `speaker-placement` | 音响摆放：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `special-additional-deduction-tianbao` | 按现行口径核查七项个税专项附加扣除的扣除标准、分摊方式与留存资料，算出年度可扣除额与应纳税所得额影响，逐项标出超额、重复 |
| `special-equipment-safety-tianbao` | 依据《特种设备安全法》与 TS.G 08，生成特种设备清单：设备类别（锅炉/压力容器/电梯/起重/厂内车）、使用登记与定 |
| `special-operation-personnel-tianbao` | 依据《特种作业人员安全技术培训考核管理规定》，生成特种作业人员管理清单：工种范围界定（电工/焊接/高处/制冷等）、持证与 |
| `special-work-cert-verify-tianbao` | 输入特种作业操作证（电工/焊工/高处作业等）的证书信息与核验情况，给出官方查询入口与核验要点、识别常见招生与办证骗局话术 |
| `sprain-first-aid` | 扭伤处理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `spray-booth-fire-tianbao` | 依据涂装作业安全规程与爆炸危险环境电气要求，生成清单：爆炸危险区域划分与防爆电气、通风与可燃气体浓度报警、漆雾与积漆清理 |
| `spring-cleaning-tianbao` | 春节大扫除：分步骤实操指南 |
| `spring-festival-shopping` | 春节备年货：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `spring-visit-gift-tianbao` | 春节串门礼：分步骤实操指南 |
| `springboot-monitoring` | Spring Boot 监控：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `springboot-slow-startup` | Spring Boot 启动慢：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `sprinkler-system-tianbao` | 依据《自动喷水灭火系统设计规范》GB 50084，生成自动喷水灭火系统核查清单：系统选型（湿式/干式/预作用）、喷头布置 |
| `sqlite-basics` |  |
| `square-dancing-noise-tianbao` | 广场舞噪音处理：分步骤实操指南 |
| `ssd-lifespan-tianbao` | 讲清固态硬盘寿命指标的读法：总写入量与健康度百分比的关系、通电时间与温度的影响、寿命末期不等于立刻损坏，以及掉盘与寿命无 |
| `ssl-certificate-expiry-tianbao` | 用 openssl s_client 核查证书剩余天数、证书链完整性、SAN 与域名匹配、签名算法与密钥强度，按剩余天数 |
| `sso-design-guide` | SSO 单点登录：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `staying-up-recovery` | 熬夜补救：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `stent-aftercare-tianbao` | 心脏支架术后护理：分步骤实操指南 |
| `sticker-maker-guide` |  |
| `stir-fry-basic-tianbao` | 家常炒菜备料、火候、调味与出品基本功指引 |
| `stirfry-greens-heat` | 炒青菜火候：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `storage-box-system-tianbao` | 收纳盒选型与标签体系搭建指南 |
| `stranger-knocking-response-tianbao` | 夜间陌生人敲门：分步骤实操指南 |
| `stray-cat-feeding` | 流浪猫喂养：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `stretching-routine-guide-tianbao` | 给出运动前后拉伸的顺序规则、保持时长与组数剂量、强度判定、主要肌群清单、弹震式拉伸风险与禁忌清单。 |
| `stroller-fold-store-tianbao` | 婴儿车折叠收纳：分步骤实操指南 |
| `student-loan-renewal-tianbao` | 助学贷款续贷：分步骤实操指南 |
| `study-abroad-sop-check-tianbao` | 按五段结构核查 PS/SOP 的各段字数与配比，用六问素材挖掘表把经历变成可写素材，核字数上限与项目针对性。 |
| `subway-fire-tianbao` | 依据《地铁设计规范》GB 50157 与轨道交通消防要求，生成清单：车站防火分区与疏散、区间排烟与联络通道、消防给水与报 |
| `succession-plan-tianbao` | 依据人才管理实践，生成关键人才继任清单：关键岗位识别、人才盘点、继任者储备（Ready now/1年内/2年内）、发展计 |
| `succulent-arrangement` | 多肉拼盘：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `succulent-leaf-propagation` | 多肉叶插：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `sugar-cookies` | 糖霜饼干：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `sugar-diet-control-tianbao` | 控糖饮食管理指引，含 GI 选择与外食策略 |
| `suit-care` | 西装保养：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `summer-mat-cleaning-tianbao` | 凉席清洁：分步骤实操指南 |
| `sunscreen-selection` | 防晒选择：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `supplier-audit-tianbao` | 依据 ISO 9001 外部提供控制与 VDA 6.3，生成供应商审核清单：审核策划与检查表、体系与过程审核、问题分级与 |
| `supplier-evaluation-tianbao` | 供应商全生命周期管理：准入评价（资质/体系/样品）、绩效评价（质量/交付/服务）、加权评分与 A/B/C 分级、淘汰与再 |
| `svg-animation` | svg动画：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `sweater-pilling` | 毛衣起球：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `swimming-breathing-technique-tianbao` | 按蛙泳与自由泳各自的换气机制拆解动作：先练水下呼气与节律，再练水面吸气的时机与身体位置，最后逐个纠正常见错误。含分阶练习 |
| `tableware-disinfection-log-tianbao` | 餐具消毒记录：分步骤实操指南 |
| `taguchi-method-tianbao` | 依据田口质量工程学，生成田口方法应用清单：信噪比（SN比）评价、参数设计、正交表试验、稳健性优化、质量损失函数。 |
| `talent-assessment-tianbao` | 生成人才测评清单：测评维度/模型设计、工具选择（胜任力/心理/情景/笔试）、信效度与公平、结果应用（录用/发展）。 |
| `talent-pool-tianbao` | 依据人才库运营实践，生成清单：人才库结构与标签体系、候选人来源与录入、分级与定期激活维护、招聘匹配与转化跟踪、数据清理与 |
| `talent-review-tianbao` | 依据人才盘点方法论，生成人才盘点清单：盘点范围与标准、绩效-潜力九宫格、校准会、关键岗位风险、个人发展计划(IDP)与梯 |
| `tank-farm-fire-tianbao` | 依据《石油化工企业设计防火标准》GB 50160 与储罐区要求，生成清单：罐区布置与防火堤、储罐间距与分组、消防冷却水系 |
| `tatami-care` | 榻榻米保养：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `tax-deduction-appeal-tianbao` | 个税专项附加扣除信息维护指引 |
| `tax-refund-rejected-tianbao` | 退税申请被拒应对指引，覆盖拒因/申诉/跟进三阶段 |
| `tax-special-deduction` |  |
| `taxi-receipt-reissue` | 出租车发票补开：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `tcc-transaction` | tcc事务：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `tea-brewing-guide-tianbao` | 按茶类给出冲泡水温、茶水比与出汤时间的实用指南 |
| `tea-moisture-storage-tianbao` | 茶叶防潮保存：分步骤实操指南 |
| `teacher-day-gift-rules-tianbao` | 教师节送礼规定：分步骤实操指南 |
| `teacher-thanks-banquet-tianbao` | 谢师宴筹备：分步骤实操指南 |
| `teeth-cleaning-schedule` | 洗牙周期：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `telecom-complaint-tianbao` | 电信业务投诉办理指引，含工信部升级路径 |
| `telegram-video-download-tianbao` | 面向想把 Telegram 频道、群组与私聊里的视频存到本地的用户，区分自有发布、已授权素材与第三方作品，说明官方保存、 |
| `temporary-electricity-tianbao` | 依据《施工现场临时用电安全技术规范》JGJ 46，生成清单：临时用电方案与审批、三级配电两级保护、一机一闸一漏一箱、电缆 |
| `tengxun-class-video-tianbao` | 面向想把腾讯课堂课程视频存到本地反复学习的用户，区分免费公开课、在校课程与付费证书项目，说明平台是否提供官方离线、课件与 |
| `tengxun-meeting-video-tianbao` | 面向想把腾讯会议录制文件留存下来的用户，区分主持人/联席主持人的云端录制、本地录制与参会者被授权获取的回放，说明官方导出 |
| `tennis-elbow-relief-tianbao` | 网球肘处理：就医准备与操作规范指南 |
| `tenosynovitis-relief-tianbao` | 腱鞘炎缓解：就医准备与操作规范指南 |
| `tent-setup-tianbao` | 帐篷搭建：分步骤实操指南 |
| `termite-identification` | 白蚁识别：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `thermal-paste-replace-tianbao` | 硅脂更换：分步骤实操指南 |
| `thermometer-choice` | 体温计选择：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `three-pillar-hr-tianbao` | 依据 HR 三支柱（COE/SSC/HRBP）模型，生成清单：三角色定位与职责划分、COE 政策与专业设计、SSC 事务 |
| `three-simultaneous-tianbao` | 依据《安全生产法》与建设项目安全设施三同时要求，生成三同时清单：安全预评价/安全生产条件和设施综合分析、安全设施设计、安 |
| `thyroid-nodule-aftercare-tianbao` | 甲状腺结节术后：就医准备与操作规范指南 |
| `tick-removal` | 蜱虫处理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `ticket-refund-check-tianbao` | 火车票、机票买错了退不掉、临时有事去不了、航班取消延误想全额退、临近开车票价扣得心疼——用它先判票种（铁路还是民航，规则 |
| `tieba-video-download-tianbao` | 面向想把百度贴吧里的视频帖存到本地的用户，区分自有发布、已授权素材与第三方作品，说明官方保存、楼主后台与合规边界，给出留 |
| `tiktok-reels-download-tianbao` | 输入 TikTok 或 Instagram Reels 链接，判定能否合法保存（自有作品/已授权/作者允许保存），给出原 |
| `tile-anti-slip` | 瓷砖防滑：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `tile-grout-care-tianbao` | 区分填缝剂、美缝剂与环氧彩砂的特性与适用场景，说明厨房卫生间是否适合环氧，施工前必须处理的空鼓破损与基层干燥问题，以及不 |
| `tile-grouting` | 瓷砖美缝：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `tile-grouting-timing-tianbao` | 瓷砖美缝时机：分步骤实操指南 |
| `tile-hollow-check-tianbao` | 瓷砖空鼓的敲击判定、空鼓率标准与处理工艺清单 |
| `timeseries-forecast-basics` |  |
| `tinnitus-visit-guide-tianbao` | 耳鸣就医检查指引：就医准备与操作规范指南 |
| `tire-pressure-check` | 胎压检查：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `tire-pressure-inflate-tianbao` | 轮胎补气与胎压：分步骤实操指南 |
| `tire-pressure-reset` | 胎压复位：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `tire-replacement-timing-tianbao` | 按胎纹深度刻度、胎侧使用年限标记与生产日期周数编码判断轮胎该不该换，说明前后轮差异与偏磨的含义、更换周期与里程的关系，以 |
| `tire-tread-check` | 胎纹深度检查：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `tiyu-video-download-tianbao` | 面向想把体育赛事视频（直播回看、集锦、进球片段）存到本地的用户，区分免费集锦、会员专享与版权受限内容，说明官方离线缓存、 |
| `tobacco-license-tianbao` | 烟草证办理：分步骤实操指南 |
| `toefl-speaking-check-tianbao` | 按独立题与三类综合题的结构模板核查要点覆盖，对照 Delivery/Language Use/Topic Develop |
| `toilet-brush-replacement` | 马桶刷更换：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `toilet-clog-tianbao` | 马桶堵塞疏通指南，强调疏通剂混用禁忌 |
| `toilet-deodorizing` | 马桶除臭：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `toilet-flange-replace-tianbao` | 判断马桶底座渗水是不是法兰圈问题，选对法兰类型并按规范拆装：含漏水来源对照、法兰选型表、十五步拆装作业顺序、搬运与陶瓷安 |
| `toilet-scale-clean-tianbao` | 马桶水垢与尿垢清除指南，强调含氯清洁剂混用禁忌 |
| `toilet-tank-parts-tianbao` | 马桶水箱配件更换：分步骤实操指南 |
| `toilet-training-steps-tianbao` | 用准备信号清单判断孩子是否适合开始如厕训练，并给出四阶段训练步骤、夜间把尿、倒退期处理与记录模板。 |
| `tomato-pruning-tianbao` | 按单干、双干、四干整枝的适用条件给出选择口径，逐时段列出整枝时间窗、打杈伤口处理要求与留叶留果的数量关系。含整枝方式对照 |
| `tomb-sweeping-booking-tianbao` | 祭扫预约：分步骤实操指南 |
| `tomb-sweeping-guide` | 清明祭扫：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `tonsillectomy-aftercare-tianbao` | 扁桃体切除术后：就医准备与操作规范指南 |
| `tooth-extraction-aftercare-tianbao` | 拔牙后护理：就医准备与操作规范指南 |
| `toothbrush-head-replace` | 电动牙刷刷头更换：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `tour-complaint-check-tianbao` | 跟团游擅自改行程、强迫购物、住宿餐饮缩水、退团被扣钱、不可抗力取消、OTA 订单与宣传不符——输入合同行程与费用明细，输 |
| `tour-refund-check-tianbao` | 旅游消费退款维权核查——行程缩水、强制购物、旅行社跑路、预付费退费、投诉路径与证据固定要点。 |
| `tpms-reset-tianbao` | 胎压监测复位：分步骤实操指南 |
| `traceability-batch-tianbao` | 依据 ISO 9001 标识与可追溯性要求，生成追溯与批次管理清单：批次编号规则、物料标识与流转卡、过程记录（人/机/料 |
| `tractor-inspection-tianbao` | 拖拉机年检：分步骤实操指南 |
| `traffic-accident-aftermath` | 交通肇事后处理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `traffic-violation-check-tianbao` | 收到 12123 的违法通知、不知道扣了几分、扣分被人栽赃、标志被树挡住看不清、单位让你自己掏罚款扣绩效——这个技能先帮 |
| `traffic-violation-recheck-tianbao` | 交通违章申诉复核材料准备与提交指引 |
| `train-sleeper-tips` | 火车卧铺：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `train-ticket-change-tianbao` | 讲清改签的时间窗与次数逻辑、退票的阶梯退票费结构、开车前与开车后的差异，以及误点取消和联程票连带改签的处置顺序。 |
| `train-ticket-refund` | 火车票退改签：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `train12306-seat-selection` | 12306选座：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `train12306-waitlist` | 12306候补技巧：分步骤实操指南，覆盖准备清单、操作流程、常见坑与维权/求助渠道。 |
| `training-refund-check-tianbao` | 培训班交了钱不想上、机构跑路、长期停课、承诺的保过保就业没兑现、被机构用"原价扣课时费"推脱不退——用它算出到底该退多少 |
| `training-system-tianbao` | 依据 ISO 9001（7.2 能力）与培训管理实践，生成培训体系清单：年度培训规划、需求分析、课程与师资、效果评估（柯 |
| `transit-card-topup` | 公交卡充值：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `trapped-in-elevator` | 电梯被困：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `trash-can-odor` | 垃圾桶除臭：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `trash-odor-remove-tianbao` | 垃圾桶异味与防蝇处理指南，强调日清日结 |
| `travel-agency-dispute-tianbao` | 旅行社纠纷维权指引 |
| `trunk-organizing-tianbao` | 后备箱收纳：分步骤实操指南 |
| `trunk-wont-open` | 后备箱打不开：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `tunnel-fire-tianbao` | 依据《建筑设计防火规范》GB 50016 与隧道消防要求，生成隧道消防清单：隧道分类与耐火、疏散通道与联络通道、排烟与通 |
| `turnover-analysis-tianbao` | 生成员工离职分析清单：离职口径（主动/被动/整体）、离职率计算、结构分析（部门/司龄/职级/原因）、关键人才流失预警与留 |
| `turtle-care-guide-tianbao` | 按龟的种类给出水深、晒台、晒背温度与配套设备口径，讲清龟苗到成龟的投喂频次与单次量、水质管理、冬眠的条件筛查与控温要求， |
| `turtle-hibernation` | 乌龟冬眠：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `turtle-tank-setup` | 龟缸布置：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `tv-wall-mount` | 电视挂架：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `twitch-video-download-tianbao` | 面向想把 Twitch 直播回放、切片存到本地的用户，区分主播自有回放、公开 VOD 与订阅专属内容，说明回放生成条件、 |
| `typhoon-window-protection-tianbao` | 台风天窗户防护：分步骤实操指南 |
| `ukulele-starter-guide-tianbao` | 按 gCEA 标准调弦给出四根弦标准音与音分判定，核对九个入门和弦指法（含每弦按品正误），并核查练习路径是否先打基础再练 |
| `umbrella-repair` | 雨伞修复：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `unaccompanied-minor-tianbao` | 机场无陪儿童：分步骤实操指南 |
| `underground-space-fire-tianbao` | 依据《建筑设计防火规范》GB 50016 与人防工程防火要求，生成地下空间消防清单：防火分区与防烟分区、疏散距离与安全出 |
| `upward-management-cadence-tianbao` | 把向上管理拆成可执行的汇报节奏表（日/周/月/季各报什么、报给谁、什么形式），用三段式汇报模板和坏消息上报时限守住预期对 |
| `used-books-hunting` | 二手书淘书：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `used-camera-inspection` | 二手相机验机：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `used-phone-inspect` |  |
| `used-phone-inspection` | 二手手机验机：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `used-watch-authentication` | 二手表验真：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `user-persona-build` | 视频号开店的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `user-segment-jump-analysis-tianbao` | 用「本期分层 × 上期分层」的跃迁矩阵算出升层率、降层率、跨层跃迁率与层内留存率，给出跃迁口径四条硬约束（同期同窗口、去 |
| `utility-bill-check-tianbao` | 用账单与表具数据定位水电费异常来源，按阶梯/倍率/表计误差口径核算应退应补金额，输出书面申请与投诉路径。 |
| `vaccine-booklet-reissue-tianbao` | 疫苗本补办：分步骤实操指南 |
| `vaccine-catchup-tianbao` | 疫苗补种：分步骤实操指南 |
| `vacuum-filter-replace-tianbao` | 吸尘器滤芯更换：分步骤实操指南 |
| `veg-storage-tianbao` | 蔬菜分类储存、预处理与保鲜判断指引 |
| `vehicle-compliance-check-tianbao` | 把一辆车的年检周期、检验标志节点、保险到期、违章记分、过户前置条件逐项算清，输出到期倒计时、记分是否满 12、过户材料清 |
| `vehicle-inspection-agent-tianbao` | 汽车年检代办：分步骤实操指南 |
| `vehicle-inspection-book-tianbao` | 车辆年检预约：分步骤实操指南 |
| `vehicle-inspection-booking` | 车辆年审预约：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `vehicle-inspection-tianbao` | 核查机动车年检周期、免检标志、所需材料、常见不合格项、整改复检流程与逾期后果。 |
| `vehicle-license-reissue-tianbao` | 行驶证补办：分步骤实操指南 |
| `vehicle-service-interval-tianbao` | 按里程与时间双轨判定保养时机，以先到者为准，说明常见保养项目的作用与不同工况的调整，并给出保养记录留存的作用与判断不必要 |
| `vermicompost-making-tianbao` | 按原料碳氮比与含水率判断配比，逐阶段给出堆温、蚯蚓密度与转箱口径，用无氨味、褐色、腐殖质三项判成熟度，并给出氨味发酸的成 |
| `veteran-card-reissue-tianbao` | 退伍证补办：分步骤实操指南 |
| `veteran-registration-tianbao` | 退役士兵登记：分步骤实操指南 |
| `veterinary-drug-rules-tianbao` | 兽药购买规定：分步骤实操指南 |
| `video-vip-carpool-tianbao` | 视频会员拼车：分步骤实操指南 |
| `vimeo-video-download-tianbao` | 输入 Vimeo 链接，区分作者开放下载、密码保护、域名白名单嵌入与付费点播四类权限，给出官方下载、创作者后台与通用命令 |
| `visa-photo-rules` | 签证照片规格：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `voc-control-tianbao` | 依据挥发性有机物治理与排放标准要求，生成清单：VOCs 源头识别与排放台账、收集与治理设施（吸附/燃烧/冷凝）、治理效率 |
| `vocabulary-memory-method-tianbao` | 用主动回忆与间隔重复替代反复阅读，给出艾宾浩斯节点表、词根词缀与例句联想法的可操作流程，并排出每日复习量与词汇量达成节奏 |
| `vue3-composable-design` | Vue3 组合式函数设计：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `walking-aid-selection` | 助行器选择：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `walking-alone-night` | 夜间独行：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `wall-crack-check-tianbao` | 墙面裂缝成因判断、严重程度分级与修补工艺清单 |
| `wall-hung-boiler-use` | 壁挂炉使用：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `wall-mildew-clean-tianbao` | 墙面霉斑清除与防复发指南，强调基层干燥与防霉底漆 |
| `wall-peel-repair-tianbao` | 墙皮脱落修补：分步骤实操指南 |
| `wallpaper-cleaning` | 墙纸清洁：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `wallpaper-edge-fix` | 墙纸翘边：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `wangyi-class-video-tianbao` | 面向想把网易云课堂课程视频存到本地反复学习的用户，区分免费公开课、在校课程与付费证书项目，说明平台是否提供官方离线、课件 |
| `wangyi-music-video-tianbao` | 面向想把网易云音乐里的 MV、视频与直播回放存到本地的用户，区分自有上传、已授权素材与第三方作品，说明官方保存、创作者后 |
| `wardrobe-audit-check-tianbao` | 先给可执行的判定标准：收纳前提是洗净晾干与除味，物品该处理的五条量化判据（一年未穿且场合无延伸可能、同功能重复且有明确短 |
| `wardrobe-dehumidify` | 衣柜除湿：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `wardrobe-moisture-proof-tianbao` | 衣柜防潮：分步骤实操指南 |
| `wardrobe-renovation-tianbao` | 衣柜分区改造规划指南，含一进一出维持机制 |
| `warning-triangle-place-tianbao` | 三角警示牌摆放：分步骤实操指南 |
| `washer-fluid-refill` | 玻璃水添加：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `washer-seal-mildew-tianbao` | 洗衣机胶圈霉斑清除与筒体清洁指南 |
| `washing-machine-balance` | 洗衣机不平衡处理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `washing-machine-cleaning-tianbao` | 洗衣机筒清洁与日常维护的实操指南 |
| `washing-machine-mold` | 洗衣机除霉：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `watch-water-damage` | 手表进水：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `water-dispenser-cleaning` | 饮水机清洗：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `water-dispenser-cleaning-tianbao` | 饮水机清洗：分步骤实操指南 |
| `water-filter-cartridge-tianbao` | 按原水水质与用水量选滤芯与通量，按时间与累计净水量双指标核查更换周期，并给出出水异常的排查顺序。含滤芯类型对照、通量选型 |
| `water-filter-replace-cycle-tianbao` | 净水器滤芯更换周期：分步骤实操指南 |
| `water-heater-descaling-tianbao` | 电热水器水垢清理与保养的实操指南 |
| `water-heater-flushing` | 热水器排污：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `water-heater-magnesium-rod-tianbao` | 热水器镁棒更换：分步骤实操指南 |
| `water-leak-check-tianbao` | 家里/楼下/店铺漏水，先别急着认栽或吵架——用它判断漏的是谁的责、还在不在保修期、物业该不该管、能要回多少修复费和财产损 |
| `water-purifier-filter-order-tianbao` | 净水器滤芯更换顺序：分步骤实操指南 |
| `watermelon-picking-tianbao` | 西瓜挑选：分步骤实操指南 |
| `waterproof-leak-repair-tianbao` | 漏水渗水先定位来源再动手：按楼上、外墙、管道、防水层、窗缝、女儿墙、设备七类来源给出识别特征与排查顺序，区分渗漏与冷凝水 |
| `waybill-info-leak-tianbao` | 快递单信息泄露：分步骤实操指南 |
| `webpack-build-speedup-tianbao` | 一切提速从测量开始：speed-measure-webpack-plugin 的 SMP 输出怎么读（先看 Loader |
| `websocket-reconnect-backoff` | WebSocket 重连退避：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `wecom-config-check-tianbao` | 输入企业微信自建/第三方应用的可信域名、网页授权、消息回调、通讯录权限、客户联系(SCRM)、会话存档、IP 白名单等配 |
| `wecom-private-compliance-tianbao` | 企业微信私域运营合规核查与整改指引。依据《个人信息保护法》《微信外部链接内容管理规范》《企业微信使用规范》及客户端使用规 |
| `wedding-banquet-seating-tianbao` | 按人数核算桌数，按主桌、双方亲属、同事、同学、朋友分区排布桌次，给出座次原则、禁忌清单与当天引导口径。含人数到桌数的换算 |
| `wedding-car-rental-tianbao` | 婚车租赁：分步骤实操指南 |
| `wedding-deposit-dispute-tianbao` | 婚庆定金纠纷：分步骤实操指南 |
| `weibo-video-download-tianbao` | 输入微博视频链接，判断视频本源是否为秒拍等外部源，给出官方保存、微博创作中心与通用命令行工具的可用顺序，处理微博视频多为 |
| `weight-loss-plateau` | 体重平台期：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `well-drilling-permit-tianbao` | 水井打井审批：分步骤实操指南 |
| `wework-approval-flow` | 企业微信审批的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wework-attendance` | 企业微信考勤的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wework-registration` | 企业微信注册的实操指南：场景、分步流程、常见坑与注意事项，一次讲清。 |
| `wheelchair-rental-tianbao` | 轮椅租赁：分步骤实操指南 |
| `white-shoes-yellow-fix-tianbao` | 白鞋发黄恢复：分步骤实操指南 |
| `white-shoes-yellowing` | 白鞋发黄：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `wifi-channel-selection-tianbao` | 先分清是覆盖问题还是干扰问题，再选信道：含 2.4G 与 5G 信道规划、信道宽度取舍、非 WiFi 干扰源识别、双频合 |
| `wifi-through-wall` | WiFi穿墙：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `wig-care` | 假发打理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `will-notarization-tianbao` | 遗嘱公证：分步骤实操指南 |
| `will-validity-check-tianbao` | 自己写或家里人写了遗嘱，用它逐条核形式要件会不会白写。输入遗嘱形式与订立情况，输出形式要件逐条核查（自书/代书/打印/录 |
| `willow-catkin-protection` | 柳絮防护：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `window-draft-sealing-tianbao` | 窗户漏风自己封堵处理的实操指南 |
| `window-screen-cleaning` | 纱窗清洗：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `window-seal-strip-tianbao` | 窗户密封条更换：分步骤实操指南 |
| `windshield-fogging` | 车窗起雾：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `wine-decanting-guide-tianbao` | 红酒是否需要醒酒、醒酒时间与操作的实用指南 |
| `wine-tasting-basics` | 品酒入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `winter-solstice-nourishment` | 冬至进补：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `winter-tire-change-tianbao` | 冬季轮胎更换：分步骤实操指南 |
| `wiper-blade-replace` | 雨刮器更换：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `wiper-blade-replace-tianbao` | 雨刮器更换：分步骤实操指南 |
| `wisdom-tooth-extraction` | 智齿拔除：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `womens-hair-removal` | 女士脱毛：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `wonton-wrapping` | 包馄饨：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `wood-floor-waxing` | 木地板打蜡：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `wood-furniture-crack` | 实木家具开裂：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `wood-furniture-wax-tianbao` | 实木家具打蜡保养指南，含环境湿度控制 |
| `wool-coat-care` | 呢子大衣护理：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `work-at-height-tianbao` | 依据《高处作业分级》GB/T 3608 与建筑施工高处作业安全要求，生成高处作业安全清单：作业分级与审批、安全带与生命线 |
| `work-injury-check-tianbao` | 输入受伤时间、地点、原因、劳动关系、参保与伤情等信息，核查是否符合工伤认定情形（工伤保险条例第十四条/第十五条）、认定申 |
| `work-injury-claim-tianbao` | 工伤认定申请办理指引，覆盖认定/鉴定/待遇/争议四阶段 |
| `work-injury-tianbao` | 依据《工伤保险条例》与事故管理要求，生成清单：事故报告与应急响应、工伤认定申请与材料、医疗救治与劳动能力鉴定、待遇支付与 |
| `work-instruction-tianbao` | 依据标准化作业要求，生成清单：作业步骤与节拍、关键控制点与参数、质量与安全要点、可视化与现场可得、版本更新与培训。 |
| `x-video-download-tianbao` | 输入 X（原 Twitter）推文链接，判定能否合法保存（自有推文/已授权/作者允许），给出原文件、官方保存、创作者后台 |
| `xiaoe-video-download-tianbao` | 面向想把自己在小鹅通店铺购买的课程视频存到本地的用户，区分已购内容、试用内容与付费专享，说明官方缓存、机构提供的原始文件 |
| `xiecheng-video-download-tianbao` | 面向想把携程旅行视频、攻略视频存到本地的用户，区分自有发布、已授权素材与第三方作品，说明官方保存、账号后台与合规边界，给 |
| `xss-protection` | XSS 防护：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `year-end-review-ppt-tianbao` | 按结论先行-数据-亮点-问题-计划五段排页序，给出每页一句话结论的写法模板、同比环比目标达成率人均效能四个量化口径与换算 |
| `yingke-live-download-tianbao` | 面向想把映客直播回放留存下来的用户，区分主播自有回放、公开回放与粉丝专属回放，说明回放生成条件、保留期与访问限制，给出主 |
| `yoga-card-transfer-tianbao` | 瑜伽馆转卡：分步骤实操指南 |
| `youtube-video-download-tianbao` | 输入 YouTube 链接，区分公开视频、会员专享、付费购买与DRM保护内容的下载边界，给出Premium离线、创作者后 |
| `yy-live-download-tianbao` | 面向想把 YY 直播回放留存下来的用户，区分主播自有回放、公开回放与粉丝专属回放，说明回放生成条件、保留期与访问限制，给 |
| `zero-defect-tianbao` | 依据零缺陷（ZD）管理理念与质量成本管理方法，生成清单：需求明确与标准共识、源头预防与过程控制、一次做对意识培养、缺陷根 |
| `zhihu-video-download-tianbao` | 输入知乎回答、文章或想法的链接，先识别视频是知乎自传还是外链（B站/腾讯/优酷等），再按来源判断能否保存，给出原文件、创 |
| `zhishixingqiu-video-tianbao` | 面向想把自己在知识星球加入的星主视频存到本地的用户，区分星主已公开内容、付费专享与私密内容，说明官方缓存、星主提供的原始 |
| `zig-build-basics` | Zig 构建入门：分步骤实操指南，含准备清单、标准流程、常见坑与自查清单。 |
| `zuoyou-video-download-tianbao` | 面向想和最右短视频存到本地的用户，区分自有作品、已授权素材与第三方作品，说明官方保存、创作者后台与合规边界，给出留存方式 |

## 🏷️ 关键词

AI Agent Skills, Claude Skills, Claude Code 技能, SKILL.md 中文, Cursor 技能, Codex 技能, OpenCode, Windsurf, Cline,
微信小程序技能, 公众号运营技能, 数据分析技能, Excel 技能, 生活服务指南, 办事流程, 消防安全, EHS 安全生产, 质量管理, ISO9001,
人力资源面试, 招聘技能, 中文技能库, 技能市场, AI 工具箱, agent skills chinese, free claude skills

## 📄 License

MIT — 可自由使用、修改、二次分发（请保留版权声明）。

---
*持续更新中。国内镜像：本仓库；技能持续生成：每周新增。*