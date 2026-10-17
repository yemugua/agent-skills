#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信交通事故索赔要件扫描器

从微信聊天记录导出文本中扫描交通事故索赔的关键要件、赔偿项目、金额与关键日期，
生成"结论先行"的索赔材料分析报告。

仅依赖 Python 标准库。全程本地运行，不发起任何网络请求。

用法:
    python extract.py --file 聊天记录.md --scenario injury      # 人伤
    python extract.py --file 聊天记录.md --scenario property    # 车损财物
    python extract.py --file 聊天记录.md --scenario fatal       # 致死
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
from datetime import date, datetime

VERSION = "1.0.0"

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
    """依次尝试三种时间格式。返回 datetime 或 None。"""
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

    messages, unmatched = [], 0
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
        messages.append({"ts": dt, "ts_raw": m.group("ts"),
                         "who": who, "text": text})

    meta = {
        "file": os.path.basename(path),
        "total_lines": len(raw_lines),
        "parsed": len(messages),
        "unmatched": unmatched,
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
    r"[块元万钱币]|医药|医疗|医疗|住院|手术|检查|拍片|CT|核磁|输液|挂号|费|"
    r"金额|花费|损失|赔偿|赔付|理赔|保险|交强险|三者|定损|维修|钣金|喷漆|拖车|救援|"
    r"误工|护理|营养|伙食|交通|打车|丧葬|死亡|伤残|鉴定|假肢|轮椅|"
    r"工资|收入|月薪|年薪|补助|补助费|护理费|营养费|补偿|"
    r"押金|定金|修理|配件|工时|评估|停运|营运"
)


def extract_amounts(messages):
    """抽取金额。返回去重后的 [{amount, context, ts_raw, who, snippet}]。"""
    results = []
    for msg in messages:
        text = msg["text"]
        for m in AMOUNT_RE.finditer(text):
            raw = m.group(1).replace(",", "")
            unit = m.group(2) or ""
            tail = text[m.end():m.end() + 2]
            head = text[max(0, m.start() - 16):m.start()]
            after = text[m.end():m.end() + 8]

            # 年份不算金额
            if not unit and tail.startswith("年"):
                continue
            # 纯数字且上下文无金额语义 → 跳过（编号、条数、温度等）
            if not unit and not AMONEY_CTX.search(head + after):
                continue
            # 明显的百分号、岁数、天数等噪声
            if re.match(r"^\s*%|^\s*岁|^\s*天|^\s*年", tail):
                continue

            try:
                val = float(raw)
            except ValueError:
                continue
            if unit in ("万", "万元"):
                val *= 10000
            if val < 10 or val > 100000000:
                continue

            ctx_start = max(0, m.start() - 20)
            results.append({
                "amount": val,
                "raw": m.group(0).strip(),
                "context": text[ctx_start:m.end() + 20].strip(),
                "ts_raw": msg["ts_raw"],
                "who": msg["who"],
                "snippet": text[:70],
            })

    seen, uniq = set(), []
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
    "injury": {
        "label": "人身损害赔偿",
        "items": [
            ("事故认定书", "受害方", kw("认定书", "责任认定", "事故认定", "交警", "认定")),
            ("责任比例", "交警勘验", kw("全责", "主要责任", "同等责任", "次责", "次要责任",
                                  "三七", "八二", "无责")),
            ("复核期是否已过", "受害方", kw("复核", "复议", "不服", "上一级")),
            ("逃逸情形", "对方抗辩", kw("逃逸", "跑了", "掉头就走", "没停")),
            ("酒驾醉驾", "对方抗辩", kw("酒驾", "醉驾", "酒精", "吹了", "喝酒了", "驾车")),
            ("医疗事实", "受害方", kw("住院", "出院", "手术", "拍片", "CT", "核磁", "急诊",
                               "诊断", "缝合", "打石膏")),
            ("医嘱含加强营养", "受害方", kw("加强营养", "营养", "补充营养", "饮食")),
            ("医嘱含护理建议", "受害方", kw("护理", "陪护", "专人照顾", "需人照顾")),
            ("误工期", "受害方", kw("误工", "休息", "病假", "请假", "休养", "不能上班")),
            ("护理期", "受害方", kw("护理", "护工", "陪床", "照顾")),
            ("伤残鉴定", "受害方", kw("伤残", "鉴定", "等级", "十级", "九级", "八级", "七级",
                             "六级", "五级", "四级", "三级", "二级", "一级", "评定")),
            ("残疾赔偿金", "受害方", kw("残疾赔偿金", "伤残赔偿金", "赔偿金")),
            ("精神损害抚慰金", "受害方", kw("精神", "抚慰", "精神损害")),
            ("辅助器具费", "受害方", kw("假肢", "轮椅", "支具", "矫形", "拐杖", "助听")),
            ("被扶养人生活费", "受害方", kw("被扶养", "扶养", "赡养", "孩子", "父亲", "母亲",
                                   "老人", "抚养")),
            ("后续治疗费", "受害方", kw("后续", "二次手术", "取钢板", "取钢钉", "复查治疗")),
            ("收入流水", "受害方", kw("工资", "流水", "收入", "月薪", "年薪", "奖金")),
        ],
    },
    "property": {
        # 注意：词表顺序有语义意义——先匹配更具体、更能代表"本项"的词，
        # 避免 "随身物品损失" 被 "车载物品损失" 抢走同一条消息（scan_elements 会跳过已用消息）
        "label": "车损与财物损失",
        "items": [
            ("车辆维修费", "受害方", kw("维修", "修车", "4S", "钣金", "喷漆", "配件", "修理费")),
            ("定损", "保险公司", kw("定损", "核损", "评估", "报价", "维修单")),
            ("施救费", "受害方", kw("拖车", "救援", "施救", "吊车")),
            ("随身物品损失", "受害方", kw("手机", "手表", "眼镜", "随身", "包坏了", "-my")),
            ("车载物品损失", "受害方", kw("车内", "车载", "车上物品", "后备箱", "东西坏了")),
            ("停运损失", "受害方", kw("停运", "营运", "出租", "客运", "货拉拉", "营运证")),
            ("鉴定费评估费", "双方", kw("鉴定费", "评估费", "公估")),
            ("对方保险情况", "受害方", kw("三者", "交强险", "商业", "保险单", "保险公司")),
            ("责任认定", "交警勘验", kw("认定书", "责任", "全责", "次责", "同等")),
        ],
    },
    "fatal": {
        "label": "致死情形赔偿",
        "items": [
            # 致死场景必须严格：单字"死亡"会误命中「死亡伤残18万封顶」这类交强险话术，
            # 把普通人伤案错判成致死案。必须用完整词组。
            ("死亡事实", "受害方", kw("抢救无效", "当场死亡", "宣告死亡", "死亡证明",
                               "人没了", "人走了", "人已经不在")),
            ("死亡证明", "受害方", kw("死亡证明", "火化", "殡仪", "追悼", "后事")),
            ("丧葬费", "受害方", kw("丧葬", "火化费", "骨灰")),
            ("死亡赔偿金", "受害方", kw("死亡赔偿金", "死亡赔偿")),
            ("被扶养人生活费", "受害方", kw("被扶养", "扶养", "赡养", "孩子", "父亲", "母亲",
                                    "老人", "抚养")),
            ("直系亲属关系", "受害方", kw("配偶", "夫妻", "儿子", "女儿", "父母", "继承")),
            ("责任认定", "交警勘验", kw("认定书", "责任", "全责", "次责", "同等")),
            ("精神损害抚慰金", "受害方", kw("精神损害", "抚慰金", "精神抚慰")),
            ("交通事故认定", "交警", kw("事故认定", "交警", "认定")),
        ],
    },
}

# 对方拒赔/推诿表述
REFUSAL_RE = re.compile(
    r"拒赔|不赔|不予赔付|无法赔付|不能赔|我们只赔|只赔交强险|超出.{0,4}不赔|"
    r"不是.{0,6}我们责任|我们没责任|你也有责任|你自身|旧伤|"
    r"没有医嘱|没说.{0,4}营养|没有护理|不认可|无法认定|材料不齐|证据不足|"
    r"仅此金额|就这么多|已经是最多|只能给"
)

# --focus 的语义别名
# 实测踩坑：真人在微信里几乎不会写「拒赔」两个字，说的是「不赔」「只赔交强险」「我们不认可」。
# 只做字面匹配会让 --focus 拒赔 命中 0 条，看起来像坏了。这里把常见说法归到类别名下。
FOCUS_ALIAS = {
    "拒赔": ["拒赔", "不赔", "只赔", "不认可", "无法赔付", "不予赔付", "不能赔",
             "超出", "旧伤", "没有医嘱", "没说", "没有护理", "材料不齐", "证据不足",
             "只能给", "就这么多", "不是我们责任", "我们没责任", "你也有责任"],
    "金额": ["元", "块", "钱", "费用", "赔付", "赔偿", "金额", "发票", "垫付"],
    "鉴定": ["鉴定", "伤残", "三期", "等级", "评定"],
    "时效": ["催", "什么时候", "拖", "尽快", "再不", "起诉", "法院", "立案", "时效",
             "过期", "复核"],
    "保险": ["保险", "交强险", "三者", "核赔", "定损", "理赔", "报案"],
    "医疗": ["住院", "出院", "手术", "医嘱", "病历", "诊断", "急诊", "药店", "复查"],
    "责任": ["认定书", "责任", "全责", "次责", "同等", "复核", "交警", "监控"],
}


def match_focus(text, focus):
    """判断消息是否命中焦点。焦点可以是类别名（走别名表），也可以是任意字面词。"""
    words = FOCUS_ALIAS.get(focus)
    if words:
        return any(w in text for w in words)
    return focus in text


# 程序里程碑
MILESTONE_PATTERNS = {
    "报警/出险": kw("报警", "110", "交警", "出险", "报案"),
    "事故认定书": kw("认定书", "责任认定", "事故认定", "认定"),
    "复核申请": kw("复核", "复议", "不服认定"),
    "医疗救治": kw("急诊", "送医院", "住院", "手术", "抢救", "拍片"),
    "材料提交": kw("材料", "发票", "单据", "病历", "诊断", "发给你", "上传"),
    "三期/伤残鉴定": kw("鉴定", "三期", "误工期", "护理期", "营养期", "伤残鉴定"),
    "定损/核赔": kw("定损", "核损", "核赔", "赔付金额", "赔付方案", "核定"),
    "拒赔/推诿": kw("拒赔", "不赔", "只赔", "不认可", "无法赔付", "超出"),
    "协议/调解": kw("协议", "调解", "和解", "一次性了结", "签字"),
    "赔付到账": kw("到账", "已经付", "转你", "打款", "赔款", "收到款"),
    "催告": kw("催", "什么时候", "进度", "尽快", "加急", "再不", "拖"),
}

# 交强险限额（2020年车综改后，单位：元）
CLAIM_LIMITS = {
    "有责": {"死亡伤残": 180000, "医疗费用": 18000, "财产损失": 2000},
    "无责": {"死亡伤残": 18000, "医疗费用": 1800, "财产损失": 100},
}

# 伤残等级系数
DISABILITY_COEF = {
    "一级": 1.00, "二级": 0.90, "三级": 0.80, "四级": 0.70, "五级": 0.60,
    "六级": 0.50, "七级": 0.40, "八级": 0.30, "九级": 0.20, "十级": 0.10,
}


def scan_elements(messages, scenario):
    scen = ELEMENTS.get(scenario)
    if not scen:
        return [], [], []
    hits, misses, snippets = [], [], []
    used = set()
    for name, burden, words in scen["items"]:
        matched = []
        for idx, msg in enumerate(messages):
            if idx in used:
                continue
            t = msg["text"]
            for w in words:
                if w in t:
                    matched.append((idx, msg, w))
                    break
        if matched:
            for idx, msg, w in matched[:2]:
                used.add(idx)
                snippets.append((name, burden, msg, w))
            hits.append({
                "name": name, "burden": burden, "count": len(matched),
                "words": sorted({w for _, _, w in matched}),
            })
        else:
            misses.append({"name": name, "burden": burden, "words": words})
    return hits, misses, snippets


def scan_milestones(messages):
    out = []
    for label, words in MILESTONE_PATTERNS.items():
        got = [m for m in messages if any(w in m["text"] for w in words)]
        if got:
            out.append((label, got))
    return out


def detect_refusals(messages):
    return [m for m in messages if REFUSAL_RE.search(m["text"])]


# ---------------------------------------------------------------------------
# 时效计算
# ---------------------------------------------------------------------------

def add_years(d, years):
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return date(d.year + years, 2, 28)


def find_trigger_date(messages, scenario):
    trigger_words = {
        "injury": kw("撞", "事故", "出事", "车祸", "车辆", "受伤", "被撞"),
        "property": kw("撞", "事故", "刮", "蹭", "追尾", "碰撞"),
        "fatal": kw("撞", "事故", "出事", "车祸", "死亡", "被撞"),
    }
    words = trigger_words.get(scenario, [])
    for msg in messages:
        if msg["ts"] is None:
            continue
        if any(w in msg["text"] for w in words):
            return msg["ts"].date(), msg
    dated = [m for m in messages if m["ts"]]
    if dated:
        return dated[0]["ts"].date(), dated[0]
    return None, None


def compute_deadline(start, years, as_of):
    if start is None:
        return None, None
    end = add_years(start, years)
    return end, (end - as_of).days


def detect_disability(messages):
    """识别聊天中提到的伤残等级。返回 {等级: 系数} 或 None。"""
    found = {}
    for msg in messages:
        for lvl, coef in DISABILITY_COEF.items():
            if lvl in msg["text"]:
                found[lvl] = coef
    return found or None


# ---------------------------------------------------------------------------
# 报告渲染
# ---------------------------------------------------------------------------

DISCLAIMER = (
    "本报告由本地脚本对聊天记录做**要件与关键词扫描**生成，"
    "仅用于整理材料、发现缺口，不构成法律意见，不预测赔付结果。"
    "涉及人身伤亡、死亡、伤残鉴定或临近时效的案件，请咨询执业律师。"
)


def fmt(n):
    if abs(n - int(n)) < 1e-9:
        return "{:,}".format(int(n))
    return "{:,.2f}".format(n)


def _where_to_get(name):
    hint = {
        "事故认定书": "交警队（处理窗口领取）",
        "责任比例": "认定书原文 + 复核（3日内）",
        "复核期是否已过": "认定书签收日期起算，3日内",
        "逃逸情形": "交警调查 / 监控调取",
        "酒驾醉驾": "交警酒精检测单 / 血检报告",
        "医疗事实": "病历、出院小结、诊断证明",
        "医嘱含加强营养": "主治医生在医嘱上补写",
        "医嘱含护理建议": "主治医生在医嘱上补写",
        "误工期": "医嘱休息证明 / 三期鉴定",
        "护理期": "三期鉴定 / 医嘱",
        "伤残鉴定": "有资质的司法鉴定机构",
        "残疾赔偿金": "伤残鉴定书 + 受诉法院所在地标准",
        "精神损害抚慰金": "法院酌定，与伤残等级挂钩",
        "辅助器具费": "假肢/轮椅装配机构证明",
        "被扶养人生活费": "户籍/居委会证明 + 无劳动收入证明",
        "后续治疗费": "医疗证明或鉴定结论",
        "收入流水": "银行流水 / 工资卡（事发前12个月）",
        "车辆维修费": "4S店或修理厂维修清单 + 发票",
        "定损": "保险公司定损单",
        "施救费": "拖车/救援公司票据",
        "车载物品损失": "购买凭证 + 现场照片",
        "随身物品损失": "购买凭证",
        "停运损失": "营运证 + 停运天数证明",
        "鉴定费评估费": "鉴定机构票据",
        "对方保险情况": "保险公司 App / 保单",
        "死亡事实": "死亡证明 / 殡仪馆证明",
        "死亡证明": "医院或公安机关出具",
        "丧葬费": "丧葬票据",
        "死亡赔偿金": "法院标准受诉法院所在地",
        "直系亲属关系": "户口本 / 结婚证 / 亲属关系证明",
    }
    return hint.get(name, "对应单据 / 交警队 / 鉴定机构")


def _next_actions(res):
    acts = []
    days = res["deadline_info"][1]
    if days is not None and days < 0:
        acts.append("**立即咨询执业律师**评估时效已过情形，不要再自行协商消耗时间。")
    elif days is not None and days < 90:
        acts.append("**本周内发出正式书面催告**（微信或短信均可），保住时效并留痕。")
    elif days is not None:
        acts.append("每 6–12 个月发一次书面催告，维持时效中断（《民法典》第 195 条）。")

    names = {m["name"] for m in res["misses"]}
    if "事故认定书" in names:
        acts.append("**首要任务：拿到《道路交通事故认定书》**。没有它，责任比例和赔多少都无法确定。")
    if "伤残鉴定" in names:
        acts.append("如涉及伤残，**尽快安排伤残鉴定**——必须在治疗终结后做（一般伤后 3–6 个月），"
                    "做早了等级偏低。十级和一级差 10 倍。")
    if "医嘱含加强营养" in names or "医嘱含护理建议" in names:
        acts.append("**去补开医嘱**：主动请医生在病历/医嘱上写明「加强营养」「建议护理/陪护」。"
                    "营养费和护理费全靠这一行字，没有就赔不了。")
    if "误工期" in names:
        acts.append("申请**三期鉴定**（误工期 / 护理期 / 营养期），以鉴定结论为准，别只认医嘱天数。")
    if "收入流水" in names:
        acts.append("准备**事发前 12 个月工资流水**，误工费全靠它，否则法院按最低工资算。")
    if res["refusals"]:
        acts.append("把对方每条拒赔/推诿表述与认定书、保单条款逐条比对。"
                    "对方说「只赔交强险」的，注意《民法典》第 1213 条：交强险之外的部分由商业三者险按责任比例赔付。")
    if res["scenario"] != "fatal":
        acts.append("**先算交强险再谈责任比例**：交强险有责限额内全额赔（伤残 18 万 / 医疗 1.8 万 / 财产 2000），"
                    "超出部分才按责任比例走三者险。直接按责任比例打折是常见的少拿钱原因。")
    acts.append("拿到认定书后若不服，**3 日内**向上一级交管部门申请复核（《道路交通事故处理程序规定》）。")
    acts.append("导出与对方/保险公司沟通的**完整连续记录**（含对你不利的内容），不要只截片段。")
    acts.append("全部材料至少三处备份：本机 + 云盘 + 原件。")
    return acts


def render_markdown(res):
    out = []
    w = out.append
    scen_label = ELEMENTS.get(res["scenario"], {}).get("label", res["scenario"])
    as_of = res["as_of"]

    w("# 微信交通事故索赔要件扫描报告")
    w("")
    w("> 场景：**%s**　扫描日期：%s　文件：`%s`"
      % (scen_label, as_of, res["meta"]["file"]))
    w("")
    if res["meta"].get("focused"):
        w("> ⚠️ 过滤模式：按「**%s**」（%s匹配）筛出 %d 条，要件覆盖率会偏低，属预期。"
          "完整分析请去掉 `--focus`。"
          % (res["meta"]["focused"], res["meta"].get("focus_kind", "字面"),
             res["meta"].get("matched_focus", 0)))
        w("")

    hits, misses = res["hits"], res["misses"]
    total = len(hits) + len(misses)
    cover = (len(hits) * 100.0 / total) if total else 0

    w("## 一、结论先行")
    w("")
    w("- 要件覆盖：**%d / %d（%.0f%%）**" % (len(hits), total, cover))

    expires, days_left = res["deadline_info"]
    if expires:
        if days_left is None:
            w("- 时效：**无法计算**（记录中没有可识别的事故日期）")
        elif days_left < 0:
            w("- 时效：**⚠️ 已过期 %d 天**（起算 %s，%d 年时效届满 %s）"
              % (-days_left, res["trigger_date"], res["limit_years"], expires))
        elif days_left < 90:
            w("- 时效：**⚠️ 仅剩 %d 天**（起算 %s，届满 %s）"
              % (days_left, res["trigger_date"], expires))
        else:
            w("- 时效：剩余 **%d 天**（起算 %s，届满 %s）"
              % (days_left, res["trigger_date"], expires))
    else:
        w("- 时效：**无法计算**，请先补充事故日期")

    # 只有人伤/全场景才谈伤残等级；车损场景报伤残等级是自相矛盾的
    if res["disability"] and res["scenario"] in ("injury", "all"):
        best = max(res["disability"].items(), key=lambda kv: kv[1])
        w("- 聊天中提到伤残等级：**%s（系数 %.0f%%）**"
          % ("、".join(res["disability"].keys()), best[1] * 100))

    dl = CLAIM_LIMITS["有责"]
    w("- 交强险有责限额参考：伤残 **%s** / 医疗 **%s** / 财产 **%s**"
      % (fmt(dl["死亡伤残"]), fmt(dl["医疗费用"]), fmt(dl["财产损失"])))
    if res["amounts"]:
        w("- 抽取到 **%d 处金额**，最大 %s 元"
          % (len(res["amounts"]), fmt(max(a["amount"] for a in res["amounts"]))))
    if res["refusals"]:
        w("- 发现 **%d 条拒赔/推诿表述**，这是本案争议焦点" % len(res["refusals"]))
    if res["milestones"]:
        w("- 识别到 **%d 类程序节点**：%s"
          % (len(res["milestones"]), "、".join(m[0] for m in res["milestones"])))
    w("")

    if days_left is not None and days_left < 0:
        w("> **本案首要问题不是材料够不够，而是时效。**人伤索赔适用《民法典》第 188 条的 3 年时效，"
          "但保守做法按交强险财产部分的 2 年算，全程留催告记录。")
        w("")

    w("## 二、要件命中表")
    w("")
    w("| 要件 | 举证方 | 命中 | 命中关键词 |")
    w("|---|---|---|---|")
    for h in hits:
        w("| %s | %s | ✅ %d 处 | %s |"
          % (h["name"], h["burden"], h["count"], "、".join(h["words"][:4])))
    for m in misses:
        w("| %s | %s | ❌ | — |" % (m["name"], m["burden"]))
    w("")

    if misses:
        w("## 三、缺失要件与补强方向")
        w("")
        w("聊天里没有 ≠ 没有材料，很可能躺在纸质单据、交警队或保险公司系统里。")
        w("")
        w("| 缺失要件 | 举证方 | 去哪里补 |")
        w("|---|---|---|")
        for m in misses:
            w("| %s | %s | %s |" % (m["name"], m["burden"], _where_to_get(m["name"])))
        w("")

    # 过滤模式下也强制输出争议焦点与金额：这两节才是过滤的真正目的
    focus_mode = bool(res["meta"].get("focused"))

    if focus_mode or res["refusals"]:
        w("## 四、争议焦点（拒赔与推诿表述）")
        w("")
        if not res["refusals"]:
            w("本次过滤范围内没有提取到拒赔/推诿表述。要看全貌请去掉 `--focus` 重跑。")
            w("")
        for i, msg in enumerate(res["refusals"][:12], 1):
            w("%d. **%s**%s" % (i, f"[{msg['ts_raw']}] " if msg["ts_raw"] else "",
                                f"{msg['who']}：" if msg["who"] else ""))
            w("   > %s" % msg["text"][:120])
        w("")
        w("> **破局参照**：")
        w("> - 《民法典》第 1213 条：机动车发生交通事故造成损害的，"
          "**先由交强险在限额内赔付，不足的由商业三者险按责任比例赔付，仍不足的由侵权人赔偿**。"
          "对方说「只赔交强险」是不成立的。")
        w("> - 《民法典》第 1179 条：人身损害赔偿项目清单"
          "（医疗费、护理费、误工费、营养费、交通费等），逐项主张。")
        w("> - 《道路交通事故处理程序规定》：收到认定书后 **3 日内**可申请复核。")
        w("> - 《民法典》第 188 条：人身损害赔偿诉讼时效 **3 年**。")
        w("")

    if res["milestones"]:
        w("## 五、关键程序节点")
        w("")
        for label, msgs in res["milestones"]:
            w("**%s**（%d 条）" % (label, len(msgs)))
            for msg in sorted(msgs, key=lambda x: x["ts_raw"])[:4]:
                w("- `[%s]`%s %s"
                  % (msg["ts_raw"],
                     ("**%s：**" % msg["who"]) if msg["who"] else "", msg["text"][:90]))
            w("")

    if focus_mode or res["amounts"]:
        w("## 六、金额梳理")
        w("")
        if not res["amounts"]:
            w("本次过滤范围内没有抽到金额。金额识别依赖「元/块/万」等后缀或"
              "「医药/误工/维修/赔付」等上下文词，请把金额写成「32800元」这种带单位的写法，"
              "或用 `--focus 金额` 全量重跑。")
            w("")
        if res["amounts"]:
            w("| 时间 | 金额 | 上下文 | 出处 |")
            w("|---|---|---|---|")
            for a in sorted(res["amounts"], key=lambda x: -x["amount"])[:25]:
                w("| %s | **%s** | %s | %s |"
                  % (a["ts_raw"], fmt(a["amount"]), a["context"][:40], a["who"] or "—"))
            w("")
            w("> 最大金额 **%s 元**。请与医疗费票据、维修单、定损单**逐笔交叉核对**。"
              % fmt(max(a["amount"] for a in res["amounts"])))
        if res["disability"]:
            lvl = max(res["disability"].items(), key=lambda kv: kv[1])[0]
            coef = res["disability"][lvl]
            w("> 已提及伤残等级 **%s**，系数 %.0f%%。据此估算残疾赔偿金基数："
              "受诉法院上年度城镇居民人均可支配收入 × 20年 × %.2f。"
              % (lvl, coef * 100, coef))
        w("")
        w("> ⚠️ **赔付顺序**：先走交强险（有责限额内全额，不打折），超出部分再按责任比例走商业三者险。"
          "直接按责任比例算总账会少拿一大截。")
        w("")

    if res["snippets"]:
        w("## 七、关键证据片段")
        w("")
        w("> 导出完整对话时**不要只截取有利片段**。对方最常见的抗辩是\"断章取义\"和\"被剪辑\"，"
          "主动提交完整记录反而更有力。")
        w("")
        for name, burden, msg, word in res["snippets"][:15]:
            w("- **[%s] %s**（%s · 命中「%s」）" % (msg["ts_raw"], name, burden, word))
            w("  > %s" % msg["text"][:110])
        w("")

    w("## 八、下一步行动清单")
    w("")
    for i, act in enumerate(_next_actions(res), 1):
        w("%d. %s" % (i, act))
    w("")
    w("---")
    w("")
    w("**免责声明**：%s" % DISCLAIMER)
    w("")
    w("本报告由 `%s` v%s 生成。重新扫描："
      % (os.path.basename(__file__), VERSION))
    w("```bash")
    w("python %s --file %s --scenario %s" % (os.path.basename(__file__),
                                              res["meta"]["file"], res["scenario"]))
    w("```")
    return "\n".join(out)


def render_json(res):
    return json.dumps({
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
        "disability": res["disability"],
        "claimLimits": CLAIM_LIMITS,
        "hits": res["hits"],
        "misses": res["misses"],
        "amounts": res["amounts"],
        "milestones": [
            {"name": label, "count": len(msgs),
             "messages": [{"ts": m["ts_raw"], "who": m["who"], "text": m["text"][:200]}
                          for m in sorted(msgs, key=lambda x: x["ts_raw"])[:10]]}
            for label, msgs in res["milestones"]
        ],
        "refusals": [{"ts": m["ts_raw"], "who": m["who"], "text": m["text"][:300]}
                     for m in res["refusals"]],
        "disclaimer": DISCLAIMER,
    }, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="从微信聊天记录中扫描交通事故索赔要件、金额与关键日期（本地运行）")
    ap.add_argument("--file", required=True, help="聊天记录文件（.md / .txt）")
    ap.add_argument("--scenario", default="all",
                    help="injury人伤 | property车损 | fatal致死 | all全部")
    ap.add_argument("--as-of", dest="as_of", default=None,
                    help="时效基准日 YYYY-MM-DD，默认今天")
    ap.add_argument("--focus", default=None,
                    help="只看含该关键词/类别的消息。类别名：拒赔、金额、鉴定、时效、"
                         "保险、医疗、责任；也可传任意字面词")
    ap.add_argument("--out", default=None, help="输出文件路径；不填打印到 stdout")
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
        sys.exit("[错误] --scenario 取值：injury | property | fatal | all")

    messages, meta = parse_messages(args.file)

    if args.focus:
        messages = [m for m in messages if match_focus(m["text"], args.focus)]
        meta["focused"] = args.focus
        meta["matched_focus"] = len(messages)
        meta["focus_kind"] = "类别" if args.focus in FOCUS_ALIAS else "字面"
        if not messages:
            hit_words = FOCUS_ALIAS.get(args.focus)
            hint = ("（该类别下可匹配的说法：%s）" % "、".join(hit_words[:6])) if hit_words else ""
            sys.exit("[提示] 没有消息命中「%s」%s\n"
                     "过滤后没有可分析内容，请去掉 --focus 重新扫描。" % (args.focus, hint))

    if not messages and not args.focus:
        sys.exit("[警告] 未解析出任何消息。\n"
                 "请确认文件格式为每行 `[YYYY-MM-DD HH:MM] 发送者: 内容`。\n"
                 "可先用技能 wechat-local-reader-tianbao 导出聊天记录。")

    scenario = args.scenario if args.scenario != "all" else "all"

    if scenario == "all":
        hits, misses, snippets = [], [], []
        for sc in ("injury", "property", "fatal"):
            h, m, s = scan_elements(messages, sc)
            for x in h + m:
                x["scenario"] = ELEMENTS[sc]["label"]
            hits += h
            misses += m
            snippets += s
    else:
        hits, misses, snippets = scan_elements(messages, scenario)

    amounts = extract_amounts(messages)
    milestones = scan_milestones(messages)
    refusals = detect_refusals(messages)
    disability = detect_disability(messages)

    limit_years = 3 if scenario == "fatal" else 3  # 人伤/财产均按民法典 3 年保守处理
    trigger_date, _ = (None, None)
    if scenario == "all":
        cands = []
        for sc in ("injury", "property", "fatal"):
            d, _ = find_trigger_date(messages, sc)
            if d:
                cands.append(d)
        trigger_date = min(cands) if cands else None
    else:
        trigger_date, _ = find_trigger_date(messages, scenario)

    expires, days_left = compute_deadline(trigger_date, limit_years, as_of)

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
        "disability": disability,
        "trigger_date": trigger_date,
        "limit_years": limit_years,
        "deadline_info": (expires, days_left),
    }

    text = render_json(res) if args.format == "json" else render_markdown(res)

    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print("已生成报告: %s" % args.out)
    else:
        print(text)


if __name__ == "__main__":
    main()
