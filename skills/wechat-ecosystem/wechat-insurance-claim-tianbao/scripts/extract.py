#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信保险理赔要件扫描器

从微信聊天记录导出文本中扫描保险理赔的关键要件、金额与关键日期，
生成"结论先行"的理赔材料分析报告。

仅依赖 Python 标准库。全程本地运行，不发起任何网络请求。

用法:
    python extract.py --file 聊天记录.md --scenario health
    python extract.py --file 聊天记录.md --scenario accident
    python extract.py --file 聊天记录.md --scenario property
    python extract.py --file 聊天记录.md --scenario liability
    python extract.py --file 聊天记录.md --scenario all --as-of 2026-10-04
    python extract.py --file 聊天记录.md --scenario all --format json --out 报告.json

输入格式（每行一条消息）:
    [2026-03-05 14:32] 对方姓名: 消息内容
    - [2026-03-05 14:32] 对方姓名: 消息内容   （markdown 导出可带前导 - ）
也支持不带发送者的纯文本行。
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------------------
# 消息解析
# ---------------------------------------------------------------------------

LINE_RE = re.compile(
    r"^\s*-?\s*\[(?P<ts>\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?)?)\]\s*"
    r"(?:(?P<who>[^\[\]:：]{1,40}?)\s*[:：]\s*)?"
    r"(?P<text>.*)$"
)

TS_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")


def parse_ts(raw):
    """依次尝试多种时间格式。返回 datetime 或 None。"""
    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def parse_messages(path):
    """读取聊天记录，返回 (messages, meta)。"""
    if not os.path.exists(path):
        sys.exit("[错误] 文件不存在: %s" % path)

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        raw_lines = fh.read().splitlines()

    messages = []
    unmatched = 0
    for line in raw_lines:
        if not line.strip():
            continue
        m = LINE_RE.match(line)
        if not m:
            unmatched += 1
            continue
        dt = parse_ts(m.group("ts"))
        who = (m.group("who") or "").strip()
        text = (m.group("text") or "").strip()
        if not text:
            continue
        messages.append({
            "ts": dt,
            "ts_raw": m.group("ts"),
            "who": who,
            "text": text,
        })

    meta = {
        "file": os.path.basename(path),
        "total_lines": len(raw_lines),
        "parsed": len(messages),
        "unmatched": unmatched,
        "with_ts": sum(1 for x in messages if x["ts"]),
        "speakers": sorted({x["who"] for x in messages if x["who"]}),
    }
    return messages, meta


# ---------------------------------------------------------------------------
# 金额抽取
# ---------------------------------------------------------------------------

AMOUNT_RE = re.compile(
    r"(?<![\d.])(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)"
    r"\s*(万元|万|元|块|钱|人民币)?"
)

AMONEY_CTX = re.compile(
    r"[块元万钱币]|工资|月薪|年薪|薪资|薪酬|薪水|底薪|绩效|奖金|提成|报酬|费用|"
    r"金额|医疗费|医药费|费用|花费|损失|赔偿|理赔|赔付|保额|保单|"
    r"保费|缴费|发票|收据|账单|结算|定损|残值|"
    r"垫付|自付|自费|免赔|起付|折扣|比例|"
    r"押金|定金|租金|房租|利息|本金|欠款|余额|转账|汇款|"
    r"日均|误工|护理|伙食|营养|交通|住宿|鉴定|评估|维修|购置"
)


def extract_amounts(messages):
    """抽取金额。返回 [{amount, context, ts_raw, who, snippet}]。"""
    results = []
    for msg in messages:
        text = msg["text"]
        for m in AMOUNT_RE.finditer(text):
            raw = m.group(1).replace(",", "")
            unit = m.group(2) or ""
            tail = text[m.end():m.end() + 2]
            head = text[max(0, m.start() - 12):m.start()]

            # 年份不算金额
            if not unit and tail.startswith("年"):
                continue
            # 纯数字且上下文无金额语义 → 跳过（日期、编号、条数等）
            if not unit and not AMONEY_CTX.search(head + text[m.end():m.end() + 8]):
                continue
            # 明显的年份/时长
            if not unit and re.match(r"^\s*年|^\s*%|^\s*岁", tail):
                continue

            try:
                val = float(raw)
            except ValueError:
                continue
            if unit == "万" or unit == "万元":
                val *= 10000
            if val < 10 or val > 100000000:
                continue

            ctx_start = max(0, m.start() - 18)
            results.append({
                "amount": val,
                "raw": m.group(0).strip(),
                "context": text[ctx_start:m.end() + 18].strip(),
                "ts_raw": msg["ts_raw"],
                "who": msg["who"],
                "snippet": text[:70],
            })
    # 同金额同上下文去重
    seen = set()
    uniq = []
    for r in results:
        key = (r["amount"], r["context"][:24], r["ts_raw"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    return uniq


# ---------------------------------------------------------------------------
# 要件库
# ---------------------------------------------------------------------------

def kw(*words):
    return list(words)


ELEMENTS = {
    "health": {
        "label": "健康保险（疾病/医疗）",
        "items": [
            ("投保生效日", "保险公司", kw("投保", "生效", "保单生效", "承保", "扣款成功")),
            ("等待期是否经过", "被保险人", kw("等待期", "等待", "观察期", "过了等待", "等待期内")),
            ("既往症排除", "保险公司", kw("既往症", "既往", "历史病史", "带病投保", "投保前")),
            ("健康告知记录", "被保险人", kw("健康告知", "告知问卷", "智能核保", "如实告知", "问诊记录")),
            ("疾病确诊事实", "被保险人", kw("确诊", "诊断", "病理", "报告显示", "确诊为", "恶性")),
            ("治疗与因果关系", "保险公司", kw("因果", "病因", "导致", "引起", "术后", "治疗方案")),
            ("医疗费用明细", "被保险人", kw("发票", "费用清单", "明细", "住院费用", "收费")),
            ("医保已报销部分", "保险公司", kw("医保", "统筹", "社保报销", "已报销", "医保结算")),
            ("免赔额约定", "保险公司", kw("免赔", "起付", "免赔额", "起付线")),
            ("就诊医院等级", "双方", kw("二级", "三级", "公立", "私立", "医院等级", "社区医院")),
            ("出险通知及时性", "被保险人", kw("报案", "出险通知", "报了案", "通知保险公司", "受理")),
        ],
    },
    "accident": {
        "label": "意外伤害保险",
        "items": [
            ("事故客观发生", "被保险人", kw("事故", "现场", "报警", "急救", "120", "照片", "视频")),
            ("意外伤害四要件", "被保险人", kw("外来", "突发", "非本意", "非疾病", "意外伤害")),
            ("是否疾病导致", "保险公司", kw("猝死", "猝倒", "心梗", "脑梗", "疾病发作", "基础病")),
            ("既往伤残/疾病", "保险公司", kw("旧伤", "既往伤", "复发", "原位", "陈旧")),
            ("意外险除外责任", "保险公司", kw("猝死", "食物中毒", "酒精", "妊娠", "分娩", "故意")),
            ("伤残等级评定", "被保险人", kw("伤残", "鉴定", "等级", "十级", "九级", "八级", "评定标准")),
            ("误工费", "被保险人", kw("误工", "工资", "收入", "误工日", "停工", "少赚")),
            ("护理费", "被保险人", kw("护理", "护工", "护理费", "专人护理")),
            ("特定场景额外保障", "被保险人", kw("交通", "航空", "航空意外", "公共交通", "轮渡", "地铁")),
            ("施救费用", "被保险人", kw("施救", "抢救", "施救费用")),
        ],
    },
    "property": {
        "label": "财产保险",
        "items": [
            ("保险标的同一性", "被保险人", kw("标的", "保额", "投保财产", "承保财产", "买的是")),
            ("保险金额是否覆盖", "保险公司", kw("保额", "保额不足", "不足额", "赔偿限额")),
            ("损失实际金额", "被保险人", kw("维修", "购置发票", "评估", "定损", "折旧", "残值")),
            ("事故原因", "双方", kw("原因", "事故原因", "导致损坏", "外力", "漏水", "火灾", "暴击")),
            ("自然磨损排除", "保险公司", kw("磨损", "老化", "折旧", "自然损耗", "旧损")),
            ("免赔额与免赔率", "保险公司", kw("免赔", "免赔率", "起赔", "免赔额")),
            ("重复保险", "保险公司", kw("重复", "多份保单", "重复投保", "其他保险")),
            ("第三方代位求偿", "保险公司", kw("第三方", "代位", "已获赔", "别人赔了")),
            ("危险物处置合规", "双方", kw("危险品", "危化", "特殊物品", "仓储", "资质")),
            ("自然灾害条款", "被保险人", kw("暴雨", "台风", "洪水", "地震", "自然灾害", "气象证明")),
        ],
    },
    "liability": {
        "label": "责任保险",
        "items": [
            ("损害事实发生", "受害方", kw("损害", "受伤", "损失", "事故", "伤害")),
            ("行为与损害因果关系", "受害方", kw("因果", "导致", "造成", "因为", "所致")),
            ("受害方确已受损", "受害方", kw("诊疗", "票据", "误工", "诊断", "医疗")),
            ("在保险期内", "保险公司", kw("保险期", "保单期间", "生效期间", "在保")),
            ("每次事故限额", "保险公司", kw("每次事故", "事故限额", "每次限额", "赔偿限额")),
            ("免赔额", "保险公司", kw("免赔", "起赔")),
            ("附加险覆盖", "双方", kw("附加", "附加险", "职业病", "上下班", "批单")),
            ("追偿权", "保险公司", kw("追偿", "第三方责任人", "代位")),
        ],
    },
}

# 拒赔理由识别
REFUSAL_RE = re.compile(
    r"拒赔|不予赔付|不予受理|拒绝赔付|无法赔付|不能赔|不赔|"
    r"不符合.{0,6}条件|不符合.{0,6}约定|属于.{0,6}免责|免责范围|"
    r"条款约定.{0,8}不承担|未如实告知|既往症|等待期|"
    r"责任不明确|证据不足|材料不齐|无法认定|不予认定"
)

# 关键节点：这些是"程序节点"，比闲聊重要
MILESTONE_PATTERNS = {
    "报案/出险通知": kw("报案", "出险", "报了案", "已受理", "立案", "受理"),
    "材料提交": kw("提交", "上传", "发你", "材料", "单据", "发票", "报告", "证明"),
    "定损/核定": kw("定损", "核定", "核损", "赔付金额", "赔付结论", "核定金额", "初步"),
    "拒赔通知": kw("拒赔", "不赔", "不予赔付", "不符合", "免责"),
    "赔付到账": kw("到账", "已付", "转账", "打款", "赔付完成", "已赔付", "收到款"),
    "催告": kw("催", "尽快", "什么时候", "进度", "回复", "麻烦快", "加急"),
    "协议/调解": kw("协议", "调解", "协商一致", "解决方案", "补偿方案", "和解"),
}


def scan_elements(messages, scenario):
    """扫描要件命中情况。返回 (命中项列表, 缺失项列表, 命中片段)。"""
    scen = ELEMENTS.get(scenario)
    if not scen:
        return [], [], []
    all_items = scen["items"]
    hits, misses, snippets = [], [], []
    # 记录已被用作证据的消息下标，避免同一段对话重复出现在多个要件下
    used = set()
    for name, burden, words in all_items:
        matched_msgs = []
        for idx, msg in enumerate(messages):
            if idx in used:
                continue
            t = msg["text"]
            for w in words:
                if w in t:
                    matched_msgs.append((idx, msg, w))
                    break
        if matched_msgs:
            # 证据片段只取前2条且标记已用，要件命中数量仍统计全部
            for idx, msg, w in matched_msgs[:2]:
                used.add(idx)
                snippets.append((name, burden, msg, w))
            hits.append({
                "name": name,
                "burden": burden,
                "count": len(matched_msgs),
                "words": sorted({w for _, _, w in matched_msgs}),
            })
        else:
            misses.append({"name": name, "burden": burden, "words": words})
    return hits, misses, snippets


def scan_milestones(messages):
    """识别程序节点。返回 [(节点名, [消息...])]。"""
    out = []
    for label, words in MILESTONE_PATTERNS.items():
        got = []
        for msg in messages:
            t = msg["text"]
            if any(w in t for w in words):
                got.append(msg)
        if got:
            out.append((label, got))
    return out


def detect_refusals(messages):
    """找出拒赔/否定性表述。"""
    out = []
    for msg in messages:
        if REFUSAL_RE.search(msg["text"]):
            out.append(msg)
    return out


# ---------------------------------------------------------------------------
# 时效计算
# ---------------------------------------------------------------------------

# 各场景的时效（年）
LIMIT_YEARS = {
    "health": 2,
    "accident": 2,
    "property": 2,
    "liability": 2,
}


def add_years(d, years):
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        # 2/29 → 平年取 2/28
        return date(d.year + years, 2, 28)


def find_trigger_date(messages, scenario):
    """
    找时效起算点。
    优先级：明确事故/确诊日期 > 报案日期 > 首次提及日期。
    """
    trigger_words = {
        "health": kw("确诊", "住院", "手术", "发病", "检查出", "确诊为"),
        "accident": kw("事故", "摔", "出车祸", "被撞", "受伤", "工伤"),
        "property": kw("损坏", "丢失", "被盗", "被泡", "烧了", "淋了", "进水"),
        "liability": kw("事故", "造成", "损害", "受伤"),
    }
    words = trigger_words.get(scenario, [])

    best = None
    for msg in messages:
        if msg["ts"] is None:
            continue
        t = msg["text"]
        if any(w in t for w in words):
            best = msg
            break
    if best:
        return best["ts"].date(), best
    # 退而求其次：最早有时间戳的消息
    dated = [m for m in messages if m["ts"]]
    if dated:
        return dated[0]["ts"].date(), dated[0]
    return None, None


def compute_deadline(start, years, as_of):
    if start is None:
        return None, None
    end = add_years(start, years)
    return end, (end - as_of).days


# ---------------------------------------------------------------------------
# 报告渲染
# ---------------------------------------------------------------------------

DISCLAIMER = (
    "本报告由本地脚本对聊天记录做**要件与关键词扫描**生成，"
    "仅用于整理材料、发现缺口，不构成法律意见，不预测赔付结果。"
    "重大、复杂或临近时效的案件请咨询执业律师。"
)


def render_markdown(res, args):
    out = []
    w = out.append
    scen_label = ELEMENTS.get(res["scenario"], {}).get("label", res["scenario"])
    as_of = res["as_of"]

    w("# 微信保险理赔要件扫描报告")
    w("")
    w("> 场景：**%s**　扫描日期：%s　文件：`%s`" % (scen_label, as_of, res["meta"]["file"]))
    w("")
    if res["meta"].get("focused"):
        w("> ⚠️ 过滤模式：仅分析含「**%s**」的消息（命中 %d 条），"
          "要件覆盖率会偏低，属预期。完整分析请去掉 `--focus`。"
          % (res["meta"]["focused"], res["meta"].get("matched_focus", 0)))
        w("")

    # 一、结论先行
    w("## 一、结论先行")
    w("")
    hits, misses = res["hits"], res["misses"]
    total = len(hits) + len(misses)
    cover = len(hits) * 100.0 / total if total else 0
    w("- 要件覆盖：**%d / %d（%.0f%%）**" % (len(hits), total, cover))

    dl, days_left = res["deadline_info"]
    if dl:
        if days_left is None:
            w("- 时效：**无法计算**（记录中没有可识别的事故/确诊日期）")
        elif days_left < 0:
            w("- 时效：**⚠️ 已过期 %d 天**（起算日 %s，%d 年时效届满 %s）"
              % (-days_left, res["trigger_date"], res["limit_years"], dl))
        elif days_left < 90:
            w("- 时效：**⚠️ 仅剩 %d 天**（起算日 %s，届满 %s）"
              % (days_left, res["trigger_date"], dl))
        else:
            w("- 时效：剩余 **%d 天**（起算日 %s，届满 %s）"
              % (days_left, res["trigger_date"], dl))
    else:
        w("- 时效：**无法计算**，请先补充事故或确诊日期")

    if res["refusals"]:
        w("- 发现 **%d 条拒赔/否定性表述**，这是本案的争议焦点" % len(res["refusals"]))
    if res["amounts"]:
        w("- 抽取到 **%d 处金额**，最大 %s 元" % (len(res["amounts"]), format_max(res["amounts"])))
    if res["milestones"]:
        w("- 识别到 **%d 类关键程序节点**：%s"
          % (len(res["milestones"]), "、".join(m[0] for m in res["milestones"])))
    w("")

    if days_left is not None and days_left < 0:
        w("> **本案首要问题不是材料够不够，而是时效。**"
          "《保险法》第 26 条规定非人寿保险的保险金请求权时效为 2 年，"
          "时效届满后即使责任成立也可能无法获赔。"
          "若已过时效，请尽快咨询律师评估是否有其他救济途径。")
        w("")

    # 二、要件命中表
    w("## 二、要件命中表")
    w("")
    w("| 要件 | 举证责任 | 命中 | 命中关键词 |")
    w("|---|---|---|---|")
    for h in hits:
        w("| %s | %s | ✅ %d 处 | %s |" % (h["name"], h["burden"], h["count"],
                                          "、".join(h["words"][:4])))
    for m in misses:
        w("| %s | %s | ❌ | — |" % (m["name"], m["burden"]))
    w("")

    # 三、缺失要件与补强
    if misses:
        w("## 三、缺失要件与补强方向")
        w("")
        w("以下要件在聊天记录中**没有找到线索**。注意：**聊天里没有 ≠ 没有材料**，"
          "很可能存在于纸质单据、系统后台或微信之外。")
        w("")
        w("| 缺失要件 | 举证责任 | 去哪里补 |")
        w("|---|---|---|")
        for m in misses:
            w("| %s | %s | %s |" % (m["name"], m["burden"], _where_to_get(m["name"])))
        w("")

    # 四、拒赔/争议焦点
    if res["refusals"]:
        w("## 四、争议焦点（拒赔与否定性表述）")
        w("")
        w("以下是对方在聊天中给出的拒赔或否定性理由，需逐条对照条款与法条判断是否成立。")
        w("")
        for i, msg in enumerate(res["refusals"][:12], 1):
            w("%d. **%s**%s" % (i, f"[{msg['ts_raw']}] " if msg["ts_raw"] else "",
                                f"{msg['who']}：" if msg["who"] else ""))
            w("   > %s" % msg["text"][:120])
        w("")
        w("> **破局参照**：")
        w("> - 《保险法》第 19 条：格式条款中免除保险人责任的条款，"
          "保险人**未作提示或明确说明的，该条款不产生效力**。")
        w("> - 《保险法》第 16 条：如实告知义务以**询问范围**为限，"
          "投保人如实回答了健康告知问卷的，**不得以未告知为由拒赔**。")
        w("> - 《保险法》第 24 条：不属于保险责任的，应在 **3 日内**发拒赔通知书并说明理由。")
        w("> - 《保险法》第 25 条：收到拒赔通知后有 **3 日内申请复核**的窗口，别错过。")
        w("")

    # 五、关键节点时间线
    if res["milestones"]:
        w("## 五、关键程序节点")
        w("")
        for label, msgs in res["milestones"]:
            w("**%s**（%d 条）" % (label, len(msgs)))
            for msg in sorted(msgs, key=lambda x: x["ts_raw"])[:4]:
                w("- `[%s]`%s %s" % (msg["ts_raw"],
                                      ("**%s：**" % msg["who"]) if msg["who"] else "",
                                      msg["text"][:90]))
            w("")

    # 六、金额梳理
    if res["amounts"]:
        w("## 六、金额梳理")
        w("")
        w("| 时间 | 金额 | 上下文 | 出处 |")
        w("|---|---|---|---|")
        for a in sorted(res["amounts"], key=lambda x: -x["amount"])[:25]:
            w("| %s | **%s** | %s | %s |"
              % (a["ts_raw"], format_num(a["amount"]), a["context"][:40], a["who"] or "—"))
        w("")
        big = max(a["amount"] for a in res["amounts"])
        w("> 最大金额 **%s 元**。请与保单保额、发票、鉴定报告**逐笔交叉核对**。"
          % format_num(big))
        w("> 注意医保统筹、第三方已赔、保单免赔额这三重扣除，别按总额主张。")
        w("")

    # 七、命中片段
    if res["snippets"]:
        w("## 七、关键证据片段")
        w("")
        w("> 导出完整对话时**不要只截取有利片段**。对方最常见的抗辩是"
          "\"断章取义\"和\"被剪辑\"，主动提交完整记录反而更有力。")
        w("")
        for name, burden, msg, word in res["snippets"][:15]:
            w("- **[%s] %s**（%s · 命中「%s」）"
              % (msg["ts_raw"], name, burden, word))
            w("  > %s" % msg["text"][:110])
        w("")

    # 八、下一步
    w("## 八、下一步行动清单")
    w("")
    for i, act in enumerate(_next_actions(res), 1):
        w("%d. %s" % (i, act))
    w("")
    w("---")
    w("")
    w("**免责声明**：%s" % DISCLAIMER)
    w("")
    w("本报告由 `%s` 生成。重新扫描：".replace("%s", os.path.basename(__file__)))
    w("```bash")
    w("python %s --file %s --scenario %s" % (os.path.basename(__file__), res["meta"]["file"],
                                              res["scenario"]))
    w("```")
    return "\n".join(out)


def _where_to_get(element_name):
    hint = {
        "投保生效日": "保单原件 / 保险公司 App 保单页",
        "等待期是否经过": "保单条款「等待期」章节",
        "既往症排除": "投保前的体检报告、门诊病历",
        "健康告知记录": "投保时的健康告知问卷截图或录音录像",
        "疾病确诊事实": "诊断证明、病理报告、出院小结",
        "医疗费用明细": "医疗发票、费用清单",
        "医保已报销部分": "医保结算单",
        "免赔额约定": "保单条款「免赔额」章节",
        "就诊医院等级": "病历首页的医院等级信息",
        "伤残等级评定": "正规鉴定机构出具的伤残鉴定书",
        "误工费": "单位误工证明 + 工资流水",
        "护理费": "医嘱 + 护理人员身份证明",
        "事故客观发生": "报警回执、现场照片视频、事故证明",
        "损失实际金额": "购置发票、维修单、评估报告",
        "保险标的同一性": "购置发票、权属登记（房产证等）",
        "免赔额与免赔率": "保单条款「责任免除」与「免赔」章节",
    }
    return hint.get(element_name, "对应单据 / 系统后台记录 / 保单条款")


def _next_actions(res):
    acts = []
    days = res["deadline_info"][1]
    if days is not None and days < 0:
        acts.append("**立即咨询执业律师**评估时效已过情形下的救济途径，不要再自行协商消耗时间。")
    elif days is not None and days < 90:
        acts.append("**本周内发出正式书面催告**（微信或邮件均可），保住时效并留痕。")
    elif days is not None:
        acts.append("每 6–12 个月发一次书面催告，维持时效中断（《民法典》第 195 条）。")

    if res["refusals"]:
        acts.append("把每条拒赔理由与保单条款原文逐条比对，"
                    "重点核查保险公司是否履行了《保险法》第 19 条的提示与明确说明义务。")
    if res["misses"]:
        names = "、".join(m["name"] for m in res["misses"][:4])
        acts.append("补齐缺失要件的材料：%s。" % names)
    if res["scenario"] == "accident" and not any(
            h["name"] == "伤残等级评定" for h in res["hits"]):
        acts.append("如涉及伤残，**尽快做伤残鉴定**——治疗终结后越早鉴定越好，拖延可能影响等级。")
    acts.append("向保险公司索取书面《拒赔通知书》，"
                "并在收到后 3 日内申请复核（《保险法》第 25 条）。")
    acts.append("导出与保险公司沟通的**完整连续记录**（含对你不利的内容），不要只截片段。")
    acts.append("全部材料至少三处备份：本机 + 云盘 + 原件。")
    return acts


def format_num(n):
    if abs(n - int(n)) < 1e-9:
        return "{:,}".format(int(n))
    return "{:,.2f}".format(n)


def format_max(amounts):
    return format_num(max(a["amount"] for a in amounts))


# ---------------------------------------------------------------------------
# JSON 输出
# ---------------------------------------------------------------------------

def render_json(res):
    out = {
        "scenario": res["scenario"],
        "scenarioLabel": ELEMENTS.get(res["scenario"], {}).get("label", res["scenario"]),
        "asOf": res["as_of"].isoformat(),
        "meta": res["meta"],
        "coverage": {
            "hit": len(res["hits"]),
            "miss": len(res["misses"]),
            "percent": round(len(res["hits"]) * 100.0 /
                            max(1, len(res["hits"]) + len(res["misses"])), 1),
        },
        "deadline": {
            "limitYears": res["limit_years"],
            "triggerDate": res["trigger_date"].isoformat() if res["trigger_date"] else None,
            "expireDate": res["deadline_info"][0].isoformat() if res["deadline_info"][0] else None,
            "daysLeft": res["deadline_info"][1],
        },
        "hits": res["hits"],
        "misses": res["misses"],
        "amounts": res["amounts"],
        "milestones": [
            {"name": label,
             "count": len(msgs),
             "messages": [{"ts": m["ts_raw"], "who": m["who"], "text": m["text"][:200]}
                          for m in sorted(msgs, key=lambda x: x["ts_raw"])[:10]]}
            for label, msgs in res["milestones"]
        ],
        "refusals": [{"ts": m["ts_raw"], "who": m["who"], "text": m["text"][:300]}
                     for m in res["refusals"]],
        "disclaimer": DISCLAIMER,
    }
    return json.dumps(out, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="从微信聊天记录中扫描保险理赔要件、金额与关键日期（本地运行）")
    ap.add_argument("--file", required=True, help="聊天记录文件（.md / .txt）")
    ap.add_argument("--scenario", default="all",
                    help="health健康险 | accident意外险 | property财产险 | "
                         "liability责任险 | all全部")
    ap.add_argument("--as-of", dest="as_of", default=None,
                    help="计算时效的基准日 YYYY-MM-DD，默认今天")
    ap.add_argument("--focus", default=None, help="只看包含该关键词的消息（调试用）")
    ap.add_argument("--out", default=None, help="输出文件路径；不填则打印到stdout")
    ap.add_argument("--format", default="md", choices=["md", "json"])
    args = ap.parse_args()

    if args.as_of:
        try:
            as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date()
        except ValueError:
            sys.exit("[错误] --as-of 格式应为 YYYY-MM-DD")
    else:
        as_of = date.today()

    if args.scenario not in list(ELEMENTS.keys()) + ["all"]:
        sys.exit("[错误] --scenario 取值：health | accident | property | liability | all")

    messages, meta = parse_messages(args.file)

    if args.focus:
        messages = [m for m in messages if args.focus in m["text"]]
        meta["focused"] = args.focus
        meta["parsed"] = len(messages)
        meta["matched_focus"] = len(messages)

    if not messages and not args.focus:
        sys.exit("[警告] 未解析出任何消息。\n"
                 "请确认文件格式为每行 `[YYYY-MM-DD HH:MM] 发送者: 内容`。\n"
                 "可先用技能 wechat-local-reader-tianbao 导出聊天记录。")

    if args.scenario == "all":
        scenario = "health" if not meta["speakers"] else "all"
    else:
        scenario = args.scenario

    # all 模式：合并全部场景的要件库，标注目录
    if scenario == "all":
        hits, misses, snippets = [], [], []
        for sc in ("health", "accident", "property", "liability"):
            h, m, s = scan_elements(messages, sc)
            for x in h:
                x["scenario"] = ELEMENTS[sc]["label"]
            for x in m:
                x["scenario"] = ELEMENTS[sc]["label"]
            hits += h
            misses += m
            snippets += s
        scenario = "all"
    else:
        hits, misses, snippets = scan_elements(messages, scenario)

    amounts = extract_amounts(messages)
    milestones = scan_milestones(messages)
    refusals = detect_refusals(messages)

    limit_years = LIMIT_YEARS.get(scenario, 2)
    trig_date, trig_msg = (None, None)
    if scenario != "all":
        trig_date, trig_msg = find_trigger_date(messages, scenario)
    else:
        # all 模式：取所有场景中最早的触发日期
        cands = []
        for sc in ("health", "accident", "property", "liability"):
            d, msg = find_trigger_date(messages, sc)
            if d:
                cands.append(d)
        trig_date = min(cands) if cands else None
    expire, days_left = compute_deadline(trig_date, limit_years, as_of)

    res = {
        "scenario": scenario,
        "as_of": as_of,
        "meta": meta,
        "hits": hits,
        "misses": misses,
        "snippets": snippets,
        "amounts": amounts,
        "milestones": milestones,
        "refusals": refusals,
        "trigger_date": trig_date,
        "limit_years": limit_years,
        "deadline_info": (expire, days_left),
    }

    text = render_json(res) if args.format == "json" else render_markdown(res, args)

    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print("已生成报告: %s" % args.out)
    else:
        print(text)


if __name__ == "__main__":
    main()
