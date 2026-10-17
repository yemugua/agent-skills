> ⚠️ **安装方式以本 skill 的 `SKILL.md` 为准**：执行 `tool/setup.sh`（macOS/Linux）或 `tool/setup.ps1`（Windows）会在 `tool/` 下创建隔离 `.venv` 并注册 `wechat-cli` 命令。下方“npm 安装”为上游原版项目（`@canghe_ai/wechat-cli`）的方式，**本打包不使用 npm**，请勿照抄。系统要求以 `SKILL.md` 为准（Windows / Weixin.exe 为默认支持平台）。

<div align="center">

# WeChat CLI

**命令行查询本地微信数据，专为 AI 集成设计。**

[![npm version](https://img.shields.io/npm/v/@canghe_ai/wechat-cli.svg)](https://www.npmjs.com/package/@canghe_ai/wechat-cli)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)](https://github.com/freestylefly/wechat-cli)

聊天记录 · 联系人 · 会话 · 收藏 · 统计 · 导出

[English](README.md)

</div>

---

## ✨ 功能亮点

- **🚀 开箱即用** — `npm install -g` 一键安装，无需 Python
- **📦 12 个命令** — sessions、history、search、contacts、members、stats、export、favorites、unread、new-messages、clean、init
- **🤖 AI 优先** — 默认 JSON 输出，专为 LLM Agent 工具调用设计
- **🔒 全程本地** — SQLCipher 即时解密，数据不出本机
- **📊 丰富统计** — 发言排行、消息类型分布、24 小时活跃图
- **📝 灵活导出** — Markdown 或纯文本，支持时间范围过滤

---

## 📥 安装（给人类看）

AI Agent 请直接移步到“安装（给 Agent 看）”

### npm（推荐）

```bash
npm install -g @canghe_ai/wechat-cli
```

> 目前提供 **macOS arm64** 二进制。其他平台可使用下方 pip 安装。欢迎提交其他平台二进制 PR。

**更新到最新版本：**

```bash
npm update -g @canghe_ai/wechat-cli
```

### pip

```bash
pip install wechat-cli
```

需要 Python >= 3.10。

### 从源码安装

```bash
git clone https://github.com/freestylefly/wechat-cli.git
cd wechat-cli
pip install -e .
```

---

## 📥 安装（给 Agent 看）

直接将在你的 Claude Code 或者 OpenClaw 中输入以下提示即可：

```bash
帮我配置并安装：npm install -g @canghe_ai/wechat-cli
```

比如在 Claude Code 中输入：

![install-claude-code-1](image/install-claude-code-1.png)

注意：请先确保有 node.js 环境。没雨可以让你的 cc 安装环境。

## 🚀 快速开始

### 第一步 — 初始化

确保微信正在运行，然后：

```bash
# macOS/Linux: 可能需要 sudo 权限
sudo wechat-cli init

# Windows: 在有足够权限的终端中运行
wechat-cli init
```

这一步会自动检测微信数据目录、提取加密密钥，并保存到 `~/.wechat-cli/`。

![init-claude-code-1](image/init-claude-code-1.png)

如果是 mac，需要执行 sudo 命令，然后需要输入密码：

![init-claude-code-code-2](image/init-claude-code-2.png)

特别注意，如果你本地有登录微信多个账号，会有多份数据需要你做选择，选择你当前登录的微信账号（默认是第一个）：

![init-claude-code-3](image/init-claude-code-3.png)

这里不确定自己现在的登录微信号，可以找到该文件夹，然后按照修改时间排序，你就可以看到了。（）

![init-claude-code-4](image/init-claude-code-4.png)

#### macOS：提前开启终端的完全磁盘访问权限

在执行 `init` 之前，请确保已为终端开启**完全磁盘访问权限**：

1. 打开 **系统设置 → 隐私与安全性 → 完全磁盘访问权限**
2. 添加你使用的终端应用（如 Terminal、iTerm2 或 IDE 内置终端）
3. 开启后重启终端

未开启此权限会导致工具无法访问微信数据目录，密钥提取将失败。

#### macOS 遇到 `task_for_pid failed` 错误？

在某些 macOS 系统上，即使使用了 `sudo`，`init` 也可能报 `task_for_pid failed`。这是 macOS 的安全策略限制了进程内存访问。

**WeChat CLI 会自动尝试修复此问题**——对微信重新签名以获取必要权限（会保留微信原有权限）。按提示操作即可：

1. 工具会自动对微信重新签名
2. 完全退出微信（不是最小化）
3. 重新打开微信并登录
4. 再次执行 `sudo wechat-cli init`

如果自动签名失败，可以手动执行：

```bash
# 先退出微信，然后：
sudo codesign --force --sign - --entitlements /dev/stdin /Applications/WeChat.app <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.get-task-allow</key>
    <true/>
</dict>
</plist>
EOF
```

> **温馨提示：** 重新签名是安全的，**不会**导致封号或账号异常。但可能影响微信的部分功能或自动更新。如果发现任何功能异常（如搜一搜无法使用），或想更新到微信最新版，直接从[微信官网](https://mac.weixin.qq.com/)重新下载安装即可，**无需重新执行 init**，已有的配置和密钥不受影响。

### 第二步 — 开始使用

```bash
wechat-cli sessions                        # 最近会话
wechat-cli history "张三" --limit 20       # 聊天记录
wechat-cli search "截止日期" --chat "项目组" # 搜索消息
```

---

## 🤖 AI 工具集成

WeChat CLI 专为 AI Agent 设计，所有命令默认输出结构化 JSON。

### Claude Code

在项目的 `CLAUDE.md` 中添加：

```markdown
## WeChat CLI

你可以使用 `wechat-cli` 查询我的本地微信数据。

常用命令：
- `wechat-cli sessions --limit 10` — 列出最近会话
- `wechat-cli history "名称" --limit 20 --format text` — 读取聊天记录
- `wechat-cli search "关键词" --chat "聊天名"` — 搜索消息
- `wechat-cli contacts --query "名称"` — 搜索联系人
- `wechat-cli unread` — 显示未读会话
- `wechat-cli new-messages` — 获取上次以来的新消息
- `wechat-cli members "群名"` — 列出群成员
- `wechat-cli stats "聊天名" --format text` — 聊天统计
```

然后在对话中可以直接问 Claude：
- "帮我看看微信有没有未读消息"
- "在项目群里搜索关于截止日期的消息"
- "看看这周 AI 群里谁发言最多？"

### OpenClaw / MCP 集成

WeChat CLI 兼容任何能执行 shell 命令的 AI 工具：

```bash
# 获取最近会话
wechat-cli sessions --limit 5

# 读取指定聊天
wechat-cli history "张三" --limit 30 --format text

# 带过滤条件搜索
wechat-cli search "报告" --type file --limit 10

# 监控新消息（适合定时任务）
wechat-cli new-messages --format text
```

---

## 📖 命令一览

### 🔒 敏感信息脱敏（`--mask`）

`history` / `search` / `new_messages` / `export` 四个命令支持 `--mask` 开关，输出前自动掩码**手机号、身份证号、银行卡号、电子邮箱**（如 `138****5678`、`****0123`、`z***n@qq.com`），避免把个人明文隐私泄露到外部渠道或日志。推送 / 导出聊天内容前推荐加上：

```bash
wechat-cli history "群名" --limit 20 --mask
wechat-cli new-messages --mask
```

### `sessions` — 最近会话

```bash
wechat-cli sessions                        # 最近 20 个会话
wechat-cli sessions --limit 10             # 最近 10 个
wechat-cli sessions --format text          # 纯文本输出
```

### `history` — 聊天记录

```bash
wechat-cli history "张三"                  # 最近 50 条消息
wechat-cli history "张三" --limit 100 --offset 50
wechat-cli history "交流群" --start-time "2026-04-01" --end-time "2026-04-03"
wechat-cli history "张三" --type link      # 只看链接
wechat-cli history "张三" --format text
```

**选项：** `--limit`、`--offset`、`--start-time`、`--end-time`、`--type`、`--format`

### `search` — 搜索消息

```bash
wechat-cli search "Claude"                 # 全局搜索
wechat-cli search "Claude" --chat "交流群"  # 指定聊天搜索
wechat-cli search "开会" --chat "群A" --chat "群B"  # 多个聊天
wechat-cli search "报告" --type file        # 只搜文件
```

**选项：** `--chat`（可多次指定）、`--start-time`、`--end-time`、`--limit`、`--offset`、`--type`、`--format`

### `contacts` — 联系人搜索与详情

```bash
wechat-cli contacts --query "李"           # 搜索联系人
wechat-cli contacts --detail "张三"        # 查看详情
wechat-cli contacts --detail "wxid_xxx"    # 通过 wxid 查看
```

详情包括：昵称、备注、微信号、个性签名、头像 URL、账号类型。

### `members` — 群成员列表

```bash
wechat-cli members "AI交流群"              # 成员列表
wechat-cli members "AI交流群" --format text
```

### `stats` — 聊天统计

```bash
wechat-cli stats "AI交流群"
wechat-cli stats "张三" --start-time "2026-04-01" --end-time "2026-04-03"
wechat-cli stats "AI交流群" --format text
```

返回：消息总数、类型分布、发言 Top 10、24 小时活跃分布。

### `export` — 导出聊天记录

```bash
wechat-cli export "张三" --format markdown              # 输出到 stdout
wechat-cli export "张三" --format txt --output chat.txt  # 输出到文件
wechat-cli export "群聊" --start-time "2026-04-01" --limit 1000
```

**选项：** `--format markdown|txt`、`--output`、`--start-time`、`--end-time`、`--limit`

### `favorites` — 微信收藏

```bash
wechat-cli favorites                       # 最近收藏
wechat-cli favorites --type article        # 只看文章
wechat-cli favorites --query "计算机网络"    # 搜索收藏
```

**类型：** text、image、article、card、video

### `unread` — 未读会话

```bash
wechat-cli unread                          # 所有未读会话
wechat-cli unread --limit 10 --format text
```

### `new-messages` — 增量新消息

```bash
wechat-cli new-messages                    # 首次: 返回未读消息 + 保存状态
wechat-cli new-messages                    # 后续: 仅返回上次以来的新消息
wechat-cli new-messages --mask --clean     # 脱敏 + 输出后清空明文缓存（自动化推荐）
```

状态保存在 `~/.wechat-cli/last_check.json`，删除此文件可重置。

### `clean` — 清理明文缓存

```bash
wechat-cli clean                           # 删除解密缓存（明文数据库），不影响微信原始加密库
```

解密后的明文库缓存在系统临时目录，共享/公用电脑用完建议执行一次；或直接在自动化命令里加 `--clean`。

---

## 🔍 消息类型过滤

`--type` 选项（适用于 `history` 和 `search`）：

| 值 | 说明 |
|---|------|
| `text` | 文本消息 |
| `image` | 图片 |
| `voice` | 语音 |
| `video` | 视频 |
| `sticker` | 表情 |
| `location` | 位置 |
| `link` | 链接/应用消息 |
| `file` | 文件 |
| `call` | 音视频通话 |
| `system` | 系统消息 |

---

## 💻 系统要求

- **macOS** ≥ 26.3.1
- **微信 Mac 版** ≤ 4.1.8.100

> macOS 老版本或更新的微信版本可能不兼容。

---

## 🖥️ 平台支持

| 平台 | 状态 | 说明 |
|------|------|------|
| macOS (Apple Silicon) | ✅ 支持 | 内置 arm64 二进制 |
| macOS (Intel) | ✅ 支持 | 需要 x86_64 二进制 |
| Windows | ✅ 支持 | 读取 Weixin.exe 进程内存 |
| Linux | ✅ 支持 | 读取 /proc/pid/mem，需要 root |

---

## 🔧 工作原理

微信将聊天数据存储在本地的 SQLCipher 加密 SQLite 数据库中。WeChat CLI：

1. **提取密钥** — 扫描微信进程内存获取加密密钥（`init`）
2. **即时解密** — 透明页级 AES-256-CBC 解密，带缓存
3. **本地查询** — 所有数据留在本机，无需网络访问

---

## 📄 开源协议

[Apache License 2.0](#许可证apache-license-20)

---

## ⚖️ 免责声明

本项目为个人使用的本地数据查询工具，请注意：

- **只读不写** — 本工具仅读取本地存储的数据，不会发送、修改或删除任何消息
- **数据不出本机** — 所有数据仅在你本机处理，不会上传至任何云端服务器
- **不破坏微信生态** — 本工具不会干扰微信正常运行，不会自动化任何操作，不违反微信使用协议
- **风险自担** — 本项目仅供个人学习研究使用，使用者需确保遵守当地法律法规

---

## 🙏 致谢

本项目基于 [wechat-decrypt](https://github.com/ylytdeng/wechat-decrypt) 开发，该仓库提供了微信数据库解密和数据解析的核心能力。

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=freestylefly/wechat-cli&type=Date)](https://star-history.com/#freestylefly/wechat-cli&Date)

---

## 归属与许可声明

> 说明：SkillHub 社区源不接受名为 `LICENSE` / `NOTICE` 的独立文件，故以下内容内嵌于本文档。再分发时请保留本段。

微信本地管家 / wechat-local-reader
====================================

一、组件来源与许可
------------------

1) wechat-cli（本工具的核心代码，位于 wechat_cli/）
   上游开源项目：https://github.com/freestylefly/wechat-cli
   许可证：Apache License 2.0（见同目录 LICENSE 文件）
   本包已包含该许可证全文，符合 Apache-2.0 第 4(a) 条的再分发要求。

2) Windows 端微信 4.1+ 的 Config.Cipher 只读密钥扫描算法
   （wechat_cli/keys/scanner_windows.py）
   借鉴自开源项目：TANGandXUE/wcdb-key-tool
   https://github.com/TANGandXUE/wcdb-key-tool
   许可证：MIT License
   原作者署名与许可证说明已保留在 scanner_windows.py 文件头的
   「版权与归属」段落中，未做删改。

   MIT 许可证要点：保留上述版权声明和许可声明即可，允许使用、复制、
   修改、合并、出版发行、散布、再授权和/或贩售副本。

3) 早期版本参考了 wechat-decrypt 的解密与解析思路
   https://github.com/ylytdeng/wechat-decrypt

二、Skill 层说明文字的作者
--------------------------

原始 Skill（slug: wechat-local-butler，显示名「微信本地管家」）
由 SkillHub 用户「宜生」（handle: user_84dd700e）创作并发布。

本改进版中的 SKILL.md 说明文档为重新撰写，未复制原作者的文字内容；
仅沿用了工具名称与功能事实描述。

三、本改进版所做的修改（Apache-2.0 第 4(b) 条要求的变更声明）
----------------------------------------------------------

修改人：刘天宝
修改文件与内容：

1. tool/wechat_cli/core/config.py
   - 新增 _dir_activity_score() / _sort_candidates_by_activity()；
   - 修复多账号机器下自动探测选中已停用账号的缺陷。原实现仅 Linux 分支
     按 mtime 排序，Windows / macOS 分支直接取候选列表第一项，导致
     登录过多个微信号的电脑上 init 报「0/N salts 找到密钥」。
     现统一按 db_storage 活跃度（最近写入时间）降序排列。
   - _choose_candidate() 在非交互模式下明确打印所选目录，便于排查。

2. tool/wechat_cli/main.py
   - 新增 _force_utf8_output()，在 CLI 入口统一将 stdout/stderr 重配置为
     UTF-8，并在 Windows 下把控制台代码页切换到 65001，修复中文输出在
     Windows 控制台下变成乱码的问题。

3. tool/setup.ps1
   - 原文件为 UTF-8 无 BOM，Windows PowerShell 5.1 按 ANSI 解析会导致
     中文字符串引号乱码、脚本无法执行。已改写为纯 ASCII。
   - pip 安装改为优先使用镜像源，失败回退 PyPI；并改用
     PYTHONPATH + python -c 方式生成启动器，绕开 pip install -e . 在
     无 build isolation 环境下的 setuptools 拉取失败问题。
   - 新增 Python 解释器探测：依次尝试 python / python3 / py -3，
     并校验版本 >= 3.10，避免只装了 py 启动器的机器上直接报错退出。

4. tool/setup.sh
   - 原脚本同样使用 pip install -e .，在国内网络下会因构建隔离拉不到
     setuptools>=68.0 而失败。已改为安装 requirements.txt + PYTHONPATH
     启动器方式，与 Windows 端行为一致。
   - 新增 python3 / python 解释器探测与阿里云镜像回退 PyPI 逻辑。

5. SKILL.md
   - 修正文件结构段落的重复行；
   - 补充「多账号机器必读」与「Windows 输出中文乱码」两节实测经验。

6. 新增文件
   - LICENSE（Apache License 2.0 全文，原发布包缺失，导致 README 中
     [Apache License 2.0](#许可证apache-license-20) 链接失效；包根目录与 tool/ 各一份）
   - NOTICE（本文件）

四、适用范围声明
----------------

本工具仅限用于读取使用者本人、本机登录的微信数据。严禁用于读取他人账号、
公司共用机或任何非本人账号的数据，使用者须自行承担全部法律责任。

---

## 许可证（Apache License 2.0）

本工具核心代码 `wechat_cli/` 采用 **Apache License 2.0** 授权（上游项目 <https://github.com/freestylefly/wechat-cli>）。
Windows 端密钥扫描算法借鉴 `TANGandXUE/wcdb-key-tool`（MIT）。

以下为 Apache License 2.0 许可证全文（对应 Apache-2.0 第 4(a) 条的再分发要求）：

                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work
      (an example is provided in the Appendix below).

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship. For the purposes
      of this License, Derivative Works shall not include works that remain
      separable from, or merely link (or bind by name) to the interfaces of,
      the Work and Derivative Works thereof.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof, that is intentionally
      submitted to Licensor for inclusion in the Work by the copyright owner
      or by an individual or Legal Entity authorized to submit on behalf of
      the copyright owner. For the purposes of this definition, "submitted"
      means any form of electronic, verbal, or written communication sent
      to the Licensor or its representatives, including but not limited to
      communication on electronic mailing lists, source code control systems,
      and issue tracking systems that are managed by, or on behalf of, the
      Licensor for the purpose of discussing and improving the Work, but
      excluding communication that is conspicuously marked or otherwise
      designated in writing by the copyright owner as "Not a Contribution."

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by combination of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a
      cross-claim or counterclaim in a lawsuit) alleging that the Work
      or a Contribution incorporated within the Work constitutes direct
      or contributory patent infringement, then any patent licenses
      granted to You under this License for that Work shall terminate
      as of the date such litigation is filed.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or
          Derivative Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work,
          excluding those notices that do not pertain to any part of
          the Derivative Works; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute must
          include a readable copy of the attribution notices contained
          within such NOTICE file, excluding those notices that do not
          pertain to any part of the Derivative Works, in at least one
          of the following places: within a NOTICE text file distributed
          as part of the Derivative Works; within the Source form or
          documentation, if provided along with the Derivative Works; or,
          within a display generated by the Derivative Works, if and
          wherever such third-party notices normally appear. The contents
          of the NOTICE file are for informational purposes only and
          do not modify the License. You may add Your own attribution
          notices within Derivative Works that You distribute, alongside
          or as an addendum to the NOTICE text from the Work, provided
          that such additional attribution notices cannot be construed
          as modifying the License.

      You may add Your own copyright statement to Your modifications and
      may provide additional or different license terms and conditions
      for use, reproduction, or distribution of Your modifications, or
      for any such Derivative Works as a whole, provided Your use,
      reproduction, and distribution of the Work otherwise complies with
      the conditions stated in this License.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.
      Notwithstanding the above, nothing herein shall supersede or modify
      the terms of any separate license agreement you may have executed
      with Licensor regarding such Contributions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor,
      except as required for reasonable and customary use in describing the
      origin of the Work and reproducing the content of the NOTICE file.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied, including, without limitation, any warranties or conditions
      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
      PARTICULAR PURPOSE. You are solely responsible for determining the
      appropriateness of using or redistributing the Work and assume any
      risks associated with Your exercise of permissions under this License.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or consequential damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work (including but not limited to damages for loss of goodwill,
      work stoppage, computer failure or malfunction, or any and all
      other commercial damages or losses), even if such Contributor
      has been advised of the possibility of such damages.

   9. Accepting Warranty or Additional Liability. While redistributing
      the Work or Derivative Works thereof, You may choose to offer,
      and charge a fee for, acceptance of support, warranty, indemnity,
      or other liability obligations and/or rights consistent with this
      License. However, in accepting such obligations, You may act only
      on Your own behalf and on Your sole responsibility, not on behalf
      of any other Contributor, and only if You agree to indemnify,
      defend, and hold each Contributor harmless for any liability
      incurred by, or claims asserted against, such Contributor by reason
      of your accepting any such warranty or additional liability.

   END OF TERMS AND CONDITIONS

   APPENDIX: How to apply the Apache License to your work.

      To apply the Apache License to your work, attach the following
      boilerplate notice, with the fields enclosed by brackets "[]"
      replaced with your own identifying information. (Don't include
      the brackets!)  The text should be enclosed in the appropriate
      comment syntax for the file format. We also recommend that a
      file or class name and description of purpose be included on the
      same "printed page" as the copyright notice for easier
      identification within third-party archives.

   Copyright [yyyy] [name of copyright owner]

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
