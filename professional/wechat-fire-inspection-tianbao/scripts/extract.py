# -*- coding: utf-8 -*-
"""
wechat-fire-inspection / extract.py

从微信聊天记录中扫描消防隐患条目、整改期限与超期、责任方、验收备案节点。纯标准库，不联网、不上传。

用法：
    python extract.py --file 聊天记录.md
    python extract.py --file 聊天记录.md --scenario problem   # problem隐患|acceptance验收|duty维保
    python extract.py --file 聊天记录.md --focus 整改
    python extract.py --file 聊天记录.md --as-of 2026-10-04
    python extract.py --file 聊天记录.md --format json --out out.json

输入行格式（每行一条）：
    [2026-03-08 14:20] 甲方老张: 3层东区12只烟感连续误报 限3月15日前处理完
    [2026-03-08 14:35] 施工小李: 收到，我这边3月15日前换完
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
    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except (ValueError, TypeError):
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
# 消防设施子系统归类
# ---------------------------------------------------------------------------

SYSTEMS = [
    ("火灾自动报警", ("烟感", "感烟", "温感", "感温", "探测器", "手报", "手报按钮",
                      "报警按钮", "模块", "主机", "联动", "误报", "探测器")),
    ("自动喷水灭火", ("喷淋", "喷头", "喷头", "末端试水", "水流指示", "报警阀",
                      "湿式", "稳压", "稳压泵", "洒水", "喷淋泵")),
    ("消火栓系统", ("消火栓", "栓箱", "水带", "水枪", "栓口", "按钮",
                    "水泵接合器", "消防泵", "消防水池", "管网", "阀门", "稳压装置")),
    ("灭火器等消防器材", ("灭火器", "干粉", "二氧化碳", "推车", "灭火毯", "消防沙")),
    ("防烟排烟", ("排烟", "送风", "加压", "风机", "风管", "排烟口", "排烟窗", "正压")),
    ("应急照明与疏散指示", ("应急灯", "应急照明", "疏散指示", "疏散标志", "安全出口",
                            "疏散门", "蓄电", "指示灯", "疏散通道")),
    ("防火分隔", ("防火门", "防火卷帘", "卷帘", "防火封堵", "防火分隔", "管道井",
                  "闭门器", "_seq", "防火窗")),
    ("消防给水与供水", ("消防给水", "消防水泵", "消防泵房", "高位水箱", "气压罐",
                        "消防水源", "消防管道")),
    ("消防通信与广播", ("广播", "消防电话", "电话插孔", "119", "应急广播", "话筒")),
    ("消防控制室与值班", ("控制室", "值班", "操作员", "持证", "图形显示", "监控室",
                          "交接班", "值班表")),
]
SYSTEMS = [(n, tuple(w for w in ws if w != "_seq")) for n, ws in SYSTEMS]

ALL_SYS_WORDS = set()
for _n, _ws in SYSTEMS:
    ALL_SYS_WORDS |= set(_ws)


def classify_system(text):
    """按 10 类消防设施归类；返回 [(系统, 命中的词)]。"""
    return [(n, w) for n, ws in SYSTEMS for w in ws if w in text]


# ---------------------------------------------------------------------------
# 数量抽取：12 只烟感 / 3 处 / 1 台 / 3 层 / 5 个
# ---------------------------------------------------------------------------

CN_DIGIT = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
# ⚠️ 别放「层」「栋」——「3 层东区 2 只应急灯」会把楼层数 3 当成设备数量，
# 结果 2 只应急灯变成 5（层 3 + 只 2）。楼层是部位不是数量。
QTY_UNIT = ("只", "个", "处", "台", "套", "具", "盏", "条", "块", "根", "组",
            "路", "点", "次", "人", "张", "扇")
QTY_RE = re.compile(r"([0-9]{1,3}|[一二两三四五六七八九十]{1,3})\s*(%s)" % "|".join(QTY_UNIT))


def parse_cn_num(seg):
    if seg in CN_DIGIT:
        return CN_DIGIT[seg]
    total, cur, seen_ten = 0, 0, False
    for ch in seg:
        if ch == "十":
            cur = (cur if cur else 1) * 10
            seen_ten = True
        elif ch in CN_DIGIT:
            if seen_ten:
                total += cur
                cur = CN_DIGIT[ch]
            else:
                cur = CN_DIGIT[ch]
        else:
            return None
    return (total + cur) if (total or cur) else None


def extract_qty(text):
    """抽「数量+单位」，如 12只 / 3处 / 两只 / 十二处。返回 [(value, unit)]。"""
    out = []
    for m in QTY_RE.finditer(text):
        raw = m.group(1)
        v = int(raw) if raw.isdigit() else parse_cn_num(raw)
        if v is not None and v > 0:
            out.append((v, m.group(2)))
    return out


# ---------------------------------------------------------------------------
# 整改期限与超期
# ---------------------------------------------------------------------------

# 限3月15日前 / 3月15号前 / 5月20日前 / 本周五前 / 下周一
DEADLINE_DATE_RE = re.compile(
    r"(?:限|最晚|截止|在)?\s*(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]\s*前")
DEADLINE_MONTH_RE = re.compile(r"(?:限|最晚|截止)?\s*(\d{1,2})\s*月\s*前")
WEEK_RE = re.compile(r"(本|下)\s*(?:周|礼拜)\s*([一二三四五六日天1-7])")

WEEKDAY_MAP = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7,
               "天": 7, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7}


def compute_deadline(text, ref):
    """从文本里找整改期限，返回 (deadline_date, raw_text, kind)。"""
    m = DEADLINE_DATE_RE.search(text)
    if m:
        return _mk_date(ref, int(m.group(1)), int(m.group(2))), m.group(0), "具体日期"
    if ref:
        m2 = DEADLINE_MONTH_RE.search(text)
        if m2:
            return _mk_date(ref, int(m2.group(1)), None), m2.group(0), "只到月"
    return None, None, None


def _mk_date(ref, month, day):
    """
    默认**取基准年**——3 月 20 日说「限3月15日前」就是当年 3 月 15 日，
    别自作聪明退到去年（第一版就是这么错的，测出来 2025-03-15）。
    只有当算出来的日子比基准日早 6 个月以上，才判定是跨年/去年写的，退一年。
    只给了月 → 取当月最后一天。
    """
    if not ref or not (1 <= month <= 12):
        return None
    if day and not (1 <= day <= 31):
        return None
    import calendar
    year = ref.year
    try:
        d = date(year, month, day) if day else \
            date(year, month, calendar.monthrange(year, month)[1])
    except ValueError:
        return None
    if (ref - d).days > 180:        # 早了大半年，多半是跨年，退一年
        try:
            d = d.replace(year=year - 1)
        except ValueError:
            return None
    return d


# ---------------------------------------------------------------------------
# 责任方识别
# ---------------------------------------------------------------------------

PARTIES = [
    ("建设单位/甲方", ("甲方", "建设方", "建设单位", "业主", "项目公司", "委托方")),
    ("施工/总包", ("总包", "施工方", "施工单位", "承包方", "项目部", "包工头", "施工队")),
    ("分包", ("分包", "劳务", "班组", "专业分包")),
    ("消防维保单位", ("维保", "维保单位", "保养单位", "消防设施维保", "维保公司")),
    ("监理单位", ("监理", "监理方", "监理公司")),
    ("供货/材料商", ("供货", "供应商", "材料商", "厂家", "经销商")),
    ("消防救援机构", ("消防救援", "消防队", "消防救援机构", "消防支", "消防大")),
    ("住建部门", ("住建", "住建部门", "审图", "消防验收", "备案", "规划")),
    ("设计单位", ("设计院", "设计方", "设计单位", "设计变更")),
]


def detect_parties(text, who=None):
    """识别责任方。发送人名字本身也是线索（比如『维保王工』），所以把 who 一起看。"""
    scope = text + (" " + who if who else "")
    return [n for n, ws in PARTIES if any(w in scope for w in ws)]


# ---------------------------------------------------------------------------
# 要件库
# ---------------------------------------------------------------------------


def kw(*words):
    return list(words)


ELEMENTS = {
    "problem": {
        "label": "隐患发现与登记",
        "items": [
            ("发现时间", "职工",
             kw("发现", "巡检", "检查", "抽查", "排查", "看到", "反馈", "通报")),
            ("部位", "职工",
             kw("层", "楼", "车", "库", "厅", "间", "房", "区域", "东", "西", "南", "北",
                "中庭", "地下", "一层", "二层", "三楼", "B1", "B2", "负一层")),
            ("设施系统", "职工", tuple(sorted(ALL_SYS_WORDS))[:40]),
            ("故障描述", "职工",
             kw("故障", "坏了", "损坏", "失效", "误报", "不亮", "不动", "被堵", "被挡",
                "遮挡", "缺失", "漏", "断", "离线", "无法", "不能", "没电", "过期")),
            ("数量", "职工", tuple(QTY_UNIT)),
            ("整改期限", "职工",
             kw("限", "最晚", "截止", "前完成", "之前", "日前", "到期", "期限", "整改期限")),
            ("责任方", "职工",
             kw("甲方", "总包", "施工", "分包", "维保", "监理", "供货", "厂家", "我方",
                "他们", "由谁", "负责")),
            ("重大隐患", "职工",
             kw("重大", "严重", "停用", "查封", "停产", "挂牌", "督办", "封死", "堵死")),
            ("已下书面", "单位举证",
             kw("整改单", "通知书", "责令", "整改通知", "回复单", "联系单", "函", "签收")),
            ("复检安排", "单位举证",
             kw("复检", "复查", "验收", "再来看", "复查", "上门", "到场", "安排人")),
        ],
    },
    "acceptance": {
        "label": "验收备案",
        "items": [
            ("报审/审图", "职工",
             kw("审图", "设计审查", "报审", "图纸", "审查意见", "消防设计")),
            ("施工记录", "职工",
             kw("施工", "隐蔽", "验收记录", "过程记录", "调试", "联动调试", "竣工图")),
            ("检测报告", "职工",
             kw("检测", "检测报告", "年检", "出具报告", "第三方", "有资质")),
            # 「材料缺口」要排在吃掉同一条消息的要件前面，否则永远抢不到
            ("材料缺口", "职工",
             kw("缺", "没有提供", "拿不出", "还没做", "未提交", "待补", "补材料",
                "材料还缺")),
            ("验收申请", "职工",
             kw("验收", "申请验收", "报验", "竣工验收", "投入使用", "开业", "备案")),
            ("备案凭证", "职工", kw("备案", "凭证", "受理", "抽查", "号令", "58号")),
            ("未保持完好", "单位举证",
             kw("未保持", "完好有效", "停用", "关阀", "锁闭", "取消", "拆了", "没开通")),
            ("整改回复闭环", "单位举证",
             kw("整改回复", "回复单", "整改完成", "已整改", "闭环", "复验", "销号")),
        ],
    },
    "duty": {
        "label": "维保履职与值班",
        "items": [
            ("维保合同", "职工",
             kw("合同", "维保合同", "协议", "服务期", "委托", "招标文件", "中标")),
            ("巡检频次", "职工",
             kw("月检", "季检", "年检", "每日", "每天", "定期", "台账", "巡检记录")),
            ("派工与响应", "职工",
             kw("派工", "派人", "安排", "明天来", "今天来", "到场", "处理", "维修")),
            ("故障修复", "职工",
             kw("修好", "更换", "已换", "修复", "恢复", "装好", "调好", "通了")),
            ("控制室值班", "职工",
             kw("值班", "值班表", "交接班", "24小时", "24小时", "持证", "证书",
                "操作员", "在岗", "脱岗", "空岗")),
            ("记录归档", "单位举证",
             kw("记录", "台账", "签到", "签字", "归档", "存档", "日志", "值班日志")),
            ("资质", "单位举证",
             kw("资质", "资格", "证书", "一级消防", "消防设施操作员", "注册")),
            ("拒不履行", "单位举证",
             kw("不管", "没人管", "推", "拖", "没时间", "再说", "以后", "下个月再说")),
        ],
    },
}

# 问题确认 / 承诺整改 / 拒拖 / 升级监管 / 已完成
MILESTONE_PATTERNS = {
    "问题提出": kw("发现", "问题", "故障", "隐患", "不行", "有问题", "缺", "坏了"),
    "确认收到": kw("收到", "知道了", "好的", "行", "OK", "ok", "明白"),
    "承诺整改": kw("限", "最晚", "前完成", "之前", "日前", "改完", "过来修", "派工"),
    "责任推诿": kw("不是我们", "我们不管", "找", "他们负责", "维保的", "甲方负责",
                   "没地说", "等着", "再说"),
    "修复完成": kw("修好", "已换", "更换", "修复", "恢复", "装好", "调好", "处理完了"),
    "申请升级": kw("报", "12345", "消防救援", "投诉", "举报", "停工", "停产", "挂牌"),
    "书面单据": kw("整改单", "通知书", "责令", "回复单", "函", "签收", "盖章"),
}

# 推诿/拖延表述（跟「责任推诿」里程碑同一套词；词太窄会让争议章节整段不渲染）
REFUSAL_WORDS = ("不管", "没人管", "不归我们", "这个找", "他们负责", "甲方负责",
                 "维保的", "不是我们", "等着", "以后", "再说", "下个月", "拖",
                 "没时间", "别催", "等货")

# 有效催办四要素（跟前面几个技能同一套思路）
DEMAND_FLAG = {
    "有部位": lambda t: bool(re.search(r"(层|楼|B\d|地下|车库|大厅|中庭|机房|控制室|"
                                      r"东|西|南|北|区)", t)),
    "有设施": lambda t: bool(classify_system(t)),
    "有时限": lambda t: bool(DEADLINE_DATE_RE.search(t) or WEEK_RE.search(t) or
                             any(w in t for w in ("前完成", "之前", "日前", "限"))),
    "有数量": lambda t: bool(extract_qty(t)),
}


def scan_elements(messages, scenario):
    """返回 (hits, misses, snippets)。一条消息最多被 2 个要件引用，防止后面的饿死。"""
    scen = ELEMENTS.get(scenario)
    if not scen:
        return [], [], []
    hits, misses, snippets = [], [], []
    used = {}
    MAX_USE = 3       # 一条消息最多被 3 个要件引用：太少会让靠后的要件一分不到
    for name, burden, words in scen["items"]:
        matched = []
        for idx, msg in enumerate(messages):
            if used.get(idx, 0) >= MAX_USE:
                continue
            for w in words:
                if w in msg["text"]:
                    matched.append((idx, msg, w))
                    break
        if matched:
            for idx, msg, w in matched[:2]:
                used[idx] = used.get(idx, 0) + 1
                snippets.append((name, burden, msg, w))
            hits.append({"name": name, "burden": burden, "count": len(matched),
                         "words": sorted({x[2] for x in matched})})
        else:
            misses.append({"name": name, "burden": burden})
    return hits, misses, snippets


def scan_milestones(messages):
    return [(label, [m for m in messages if any(w in m["text"] for w in words)])
            for label, words in MILESTONE_PATTERNS.items()]


# ---------------------------------------------------------------------------
# 问题条目抽取（同系统合并、算超期）
# ---------------------------------------------------------------------------


CLAUSE_SPLIT = re.compile(r"[，,。；;！!?？\n]|还有|另外|以及|顺便|再看一下")


def extract_items(messages, as_of):
    """
    把聊天里的消防问题抽成条目：系统归类 + 数量 + 期限 + 超期 + 责任方 + 是否反复出现。

    ⚠️ 必须**按子句拆**——一条消息常同时报好几个问题：
    「2 只应急灯不亮，还有防火门闭门器坏了 3 个」是两个条目（2 只 / 3 个），
    整句一起抽会变成 5，数量直接失真。
    """
    items = []
    for msg in messages:
        t = msg["text"]
        ref = msg["ts"].date() if msg["ts"] else as_of
        clauses = [c.strip() for c in CLAUSE_SPLIT.split(t) if c and c.strip()]

        # 只在整条消息里找一次，子句里没有就落到整句上（子句拆分会吃掉分隔符）
        dl_all, dl_raw_all, dl_kind_all = compute_deadline(t, ref)

        matched_sys = False
        for c in clauses:
            cls = classify_system(c)
            if not cls:
                continue
            matched_sys = True
            sys_name, hit = cls[0]
            qty = extract_qty(c)
            dl, dl_raw, dl_kind = compute_deadline(c, ref)
            if dl is None:
                dl, dl_raw, dl_kind = dl_all, dl_raw_all, dl_kind_all
            over = (dl - as_of).days if (dl and as_of) else None
            items.append({
                "date": msg["ts"].date().isoformat() if msg["ts"] else None,
                "ts_raw": msg["ts_raw"],
                "who": msg["who"],
                "system": sys_name,
                "hitWord": hit,
                "qty": qty[:3],
                "qtyTotal": sum(v for v, _ in qty[:3]),
                "deadline": dl.isoformat() if dl else None,
                "deadlineRaw": dl_raw,
                "deadlineKind": dl_kind,
                "daysLeft": over,
                "overdue": bool(dl and as_of and (dl - as_of).days < 0),
                "parties": detect_parties(c, msg["who"]),
                "text": c[:80],
            })

        # 提了期限但没报设施的，也别丢——标「未归类」，提醒人工补系统
        if not matched_sys and (dl_all or detect_parties(t, msg["who"])):
            over = (dl_all - as_of).days if (dl_all and as_of) else None
            items.append({
                "date": msg["ts"].date().isoformat() if msg["ts"] else None,
                "ts_raw": msg["ts_raw"],
                "who": msg["who"],
                "system": "未归类（需补设施类别）",
                "hitWord": None,
                "qty": [],
                "qtyTotal": 0,
                "deadline": dl_all.isoformat() if dl_all else None,
                "deadlineRaw": dl_raw_all,
                "deadlineKind": dl_kind_all,
                "daysLeft": over,
                "overdue": bool(dl_all and as_of and (dl_all - as_of).days < 0),
                "parties": detect_parties(t, msg["who"]),
                "text": t[:80],
            })

    # 同一系统反复出现 → 标「反复」
    from collections import Counter
    cnt = Counter(i["system"] for i in items)
    seen = set()
    for i in items:
        key = i["system"]
        mark = None
        if cnt[key] >= 2:
            n = i["date"] + "|" + key
            if n in seen or cnt[key] > 1 and key in seen:
                mark = "反复"
            seen.add(n)
        i["repeat"] = cnt[key]
        i["repeatFlag"] = mark
    return items


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------

DISCLAIMER = (
    "本报告由本地脚本对聊天记录做**要件与关键词扫描**生成，"
    "仅用于整理材料、发现缺口，不构成消防技术鉴定或法律意见，不预测检查结果。"
    "涉及重大火灾隐患、行政处罚或验收否决的，请报辖区消防救援机构并请专业人士复核。"
)


def fmt(n):
    return "{:,.2f}".format(n) if isinstance(n, (int, float)) else "—"


def _where_to_get(name):
    table = {
        "发现时间": "聊天时间戳 + 巡检记录；精确到点",
        "部位": "拍编号、拍全貌，说明哪层哪区（别只写『某处』）",
        "设施系统": "按 10 类归到一个系统里，整改单才写得清",
        "故障描述": "写清『什么坏了/什么挡住了/多少次』，别写『有问题』",
        "数量": "逐条清点：只 / 处 / 台，没数量就没法复核",
        "整改期限": "要**书面**文书（限期改正通知书），微信口头期限不算数",
        "责任方": "按合同和法条分：甲/总包/分包/维保/监理/供货",
        "重大隐患": "按《重大火灾隐患判定规则》判要素，别当小毛病拖",
        "已下书面": "整改单要有编号、发出日、签收人；回复单要有验收人签字",
        "复检安排": "复检时间必须 > 整改到期日，同日=事后补材料",
        "报审/审图": "消防设计审查意见 / 审图合格书",
        "施工记录": "隐蔽工程验收、施工过程记录、竣工图",
        "检测报告": "找有资质的检测机构出，别用维保自检代替",
        "验收申请": "验收申请 / 备案受理凭证，以当地住建部门口径为准",
        "备案凭证": "备案回执；抽查结果要跟整改回复一起归档",
        "未保持完好": "⚠️ 消防泵、阀门被关是最典型、最容易罚的项",
        "整改回复闭环": "整改回复单 + 复检照片 + 验收人签字，三样齐才算闭环",
        "材料缺口": "缺什么列什么，报审窗口一次问清材料清单",
        "维保合同": "维保范围、频次、响应时限、备件责任，最好附合同复印件",
        "巡检频次": "月检/季检/年检 + 每日防火巡查，台账要能对应到人",
        "派工与响应": "报修→派工→到场→修复→验收，串成一条线",
        "故障修复": "换件/修复要有前后对比照片，改完没改看得见",
        "控制室值班": "每日 24h、每班不少于 2 人、持证上岗（消防设施操作员）",
        "记录归档": "值班日志、巡检记录、检测报告三本台账分文件夹存",
        "资质": "消防设施操作员证、维保单位资质，检查当场就要出示",
        "拒不履行": "书面留痕 + 报消防救援机构 / 12345，把风险外移",
    }
    return table.get(name, "按聊天记录与项目留存材料整理")


def _next_actions(res):
    acts = []
    over = [i for i in res["items"] if i["overdue"]]
    soon = [i for i in res["items"] if i["daysLeft"] is not None and 0 <= i["daysLeft"] <= 7]

    if over:
        acts.append("**有 %d 条已过整改期限**（%s）——先发书面催办；"
                    "再报消防救援机构/12345，别在微信里陪他拖"
                    % (len(over), "、".join(sorted({i["system"] for i in over})[:3])))
    if soon:
        acts.append("**%d 条 7 天内到期**：%s，到期没复检就默认没改完"
                    % (len(soon), "、".join(sorted({i["system"] for i in soon})[:3])))

    miss_names = {m["name"] for m in res["misses"]}
    for key, msg in (
        ("整改期限", "⚠️ 期限只有口头没有书面 → 找他要**限期改正通知书/整改单**；"
                     "没有文书的『限X日前』在复议时等于没说"),
        ("责任方", "责任没 pinned → @ 到具体单位并写清楚由谁负责，不然最后都是你的"),
        ("数量", "⚠️ 没数量 → 逐处清点写全（只/处/台），否则复检时指认不了"),
        ("已下书面", "只有微信没有书面 → 补一份带编号的整改通知 + 签收，闭环凭证在书面"),
        ("复检安排", "复检没排 → 复检日期必须晚于整改期限，且要有照片+验收人签字"),
        ("重大隐患", "出现『重大/停产/挂牌』字样 → 按《重大火灾隐患判定规则》判要素，"
                     "别当普通隐患慢慢改"),
        ("检测报告", "检测报告缺失 → 找有资质机构出，维保自检不能代替"),
        ("备案凭证", "验收/备案没落 → 未经消防验收合格就投用是最容易爆的雷，先去窗口问清口径"),
        ("控制室值班", "值班没记录 → 24h 值班 + 每班不少于 2 人 + 持证，检查当场就查这个"),
        ("记录归档", "台账不全 → 值班日志/巡检记录/检测报告三本分开存，按月份文件夹"),
        ("拒不履行", "对方一直拖 → 书面留痕 + 报消防救援机构或 12345，把责任外移"),
        ("维保合同", "合同没提到频次和响应时限 → 补签/补充协议，出事才能追"),
    ):
        if key in miss_names:
            acts.append(msg)
            break

    if res["repeat"]:
        acts.append("有 **%d 个系统反复出问题**（%s）——反复=没真正闭环，"
                    "检查时这一栏最扎眼"
                    % (len(res["repeat"]),
                       "、".join("%s×%d" % (k, v) for k, v in res["repeat"][:3])))

    acts.append("问题写法统一成四件套：**部位 + 设施 + 故障 + 数量**，"
                "复检时一眼能判定改没改完")
    acts.append("整改单要写：部位、措施、数量、完成时间、验收人 —— 缺验收人=没闭环")
    acts.append("⭐ 关键那一步：让对方在群里**复述**你报的问题"
                "（『收到，B2 车库 3月8日 那批烟感，限3月15日前换完』= 三关全过）")
    acts.append("完整连续记录（含对你不利的部分），录屏 > 导出 > 截图；重要节点单独存证")
    acts.append("三处备份：本机 + 云盘 + 项目归档；记录日期**别倒签**")
    return acts


def render_markdown(res):
    out = []
    w = out.append
    scen_label = ELEMENTS.get(res["scenario"], {}).get("label", res["scenario"])
    as_of = res["as_of"]

    w("# 消防隐患与整改扫描报告")
    w("")
    w("> 场景：**%s**　基准日：%s　文件：`%s`"
      % (scen_label, as_of, res["meta"]["file"]))
    w("")

    focus_mode = bool(res["meta"].get("focused"))
    if focus_mode:
        w("> ⚠️ 过滤模式：按「**%s**」（%s匹配）筛出 %d 条，覆盖率偏低，属预期。"
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

    items = res["items"]
    if items:
        sys_cnt = {}
        for i in items:
            sys_cnt[i["system"]] = sys_cnt.get(i["system"], 0) + 1
        qty_total = sum(i["qtyTotal"] for i in items)
        over = [i for i in items if i["overdue"]]
        soon = [i for i in items if i["daysLeft"] is not None and 0 <= i["daysLeft"] <= 7]
        w("- 抽出 **%d 条消防问题**，覆盖 **%d 类**设施（%s）"
          % (len(items), len(sys_cnt), "、".join(
              "%s×%d" % (k, v) for k, v in sorted(sys_cnt.items(), key=lambda x: -x[1])[:4])))
        if qty_total:
            w("- 提到数量合计 **%s**" % qty_total)
        if over:
            w("- ⚠️ **已过期限 %d 条**：%s"
              % (len(over), "、".join(sorted({i["system"] for i in over}))))
        if soon:
            w("- ⚠️ **7 天内到期 %d 条**：%s"
              % (len(soon), "、".join(sorted({i["system"] for i in soon}))))

    if res["repeat"]:
        w("- 反复出现的系统：**%s**"
          % "、".join("%s（%d 次）" % (k, v) for k, v in res["repeat"][:4]))
    if res["milestones"]:
        w("- 识别到 **%d 类节点**：%s"
          % (len(res["milestones"]),
             "、".join(m[0] for m in res["milestones"] if m[1])))
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
        w("| 缺失要件 | 举证方 | 去哪里补 |")
        w("|---|---|---|")
        for m in misses:
            w("| %s | %s | %s |" % (m["name"], m["burden"], _where_to_get(m["name"])))
        w("")

    if focus_mode or items:
        w("## 四、问题条目（按设施系统归类）")
        w("")
        if not items:
            w("本次过滤范围内没抽到消防设施类问题。"
              "脚本按 10 类设施词库匹配（烟感/喷淋/消火栓/灭火器/防排烟/应急照明/"
              "防火分隔/消防给水/广播电话/控制室值班），换个词再跑一次试试。")
            w("")
        else:
            w("| 发现日 | 系统 | 数量 | 期限 | 距到期 | 责任方 | 反复 | 原话 |")
            w("|---|---|---|---|---|---|---|---|")
            for i in items[:24]:
                dl = i["deadline"] or "—"
                if i["daysLeft"] is None:
                    dls = "—"
                elif i["overdue"]:
                    dls = "**超期 %d 天**" % (-i["daysLeft"])
                else:
                    dls = "%d 天" % i["daysLeft"]
                w("| %s | %s | %s | %s | %s | %s | %s | %s |"
                  % (i["date"] or "—", i["system"],
                     ("%d%s" % (i["qtyTotal"], i["qty"][0][1])) if i["qty"] else "—",
                     dl + ("（%s）" % i["deadlineRaw"] if i["deadlineRaw"] else ""),
                     dls,
                     "、".join(i["parties"]) if i["parties"] else "—",
                     "×%d" % i["repeat"] if i["repeat"] > 1 else "",
                     i["text"][:26].replace("|", "/")))
            w("")
            w("> 只给了月的期限按当月月末算；跨年（如 12 月说的限 3 月前）自动往前找年。"
              "⚠️ **口头期限不算数，以书面《责令限期改正通知书》为准。**")
            w("")

    if focus_mode or res["refusals"]:
        w("## 五、责任推诿与升级节点")
        w("")
        if not res["refusals"]:
            w("过滤范围内没有推诿表述。")
            w("")
        for i, msg in enumerate(res["refusals"][:12], 1):
            w("%d. **%s**%s" % (i, f"[{msg['ts_raw']}] " if msg["ts_raw"] else "",
                                f"{msg['who']}：" if msg["who"] else ""))
            w("   > %s" % msg["text"][:120])
        w("")
        w("> **破局参照**：")
        w("> - 微信记录只要**真实、完整、能核对原始载体**就有效；对方说「微信不算数」不用怕")
        w("> - 但**闭环凭证在书面**：整改单要有编号、发出日、签收人；回复单要有验收人签字")
        w("> - 对方一直拖 → 报消防救援机构或 **12345**，把风险从自己身上移出去")
        w("> - 拒不整改 / 可能严重影响公共安全 → 会往停产停业、挂牌督办走")
        w("")

    if focus_mode or res["milestones"]:
        w("## 六、关键节点")
        w("")
        for label, msgs in res["milestones"]:
            if not msgs:
                continue
            w("**%s**（%d 条）" % (label, len(msgs)))
            for msg in sorted(msgs, key=lambda x: x["ts_raw"])[:4]:
                w("- `[%s]`%s %s"
                  % (msg["ts_raw"], ("**%s：**" % msg["who"]) if msg["who"] else "",
                     msg["text"][:90]))
            w("")

    if focus_mode or res["snippets"]:
        w("## 七、关键证据片段")
        w("")
        w("> 导出完整对话时**不要只截有利片段**。对方最容易攻击「剪辑」，"
          "完整连续记录反而更有力。群通知比私聊强，因为能证明是管理行为。")
        w("")
        for name, burden, msg, word in res["snippets"][:14]:
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
    w("本报告由 `extract.py` v%s 生成。重新扫描：" % VERSION)
    w("```bash")
    w("python %s --file %s --scenario %s"
      % (os.path.basename(__file__), res["meta"]["file"], res["scenario"]))
    w("```")
    return "\n".join(out)


def render_json(res):
    from collections import Counter
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
        "items": res["items"],
        "itemSummary": {
            "count": len(res["items"]),
            "systems": dict(Counter(i["system"] for i in res["items"])),
            "overdueCount": len([i for i in res["items"] if i["overdue"]]),
        } if res["items"] else None,
        "repeatSystems": res["repeat"],
        "hits": res["hits"],
        "misses": res["misses"],
        "milestones": [
            {"name": label, "count": len(msgs),
             "messages": [{"ts": m["ts_raw"], "who": m["who"], "text": m["text"]}
                          for m in msgs]}
            for label, msgs in res["milestones"]
        ],
        "refusals": [
            {"ts": m["ts_raw"], "who": m["who"], "text": m["text"]}
            for m in res["refusals"]
        ],
        "disclaimer": DISCLAIMER,
    }, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

FOCUS_ALIAS = {
    "整改": ["整改", "限", "最晚", "前完成", "之前", "日前", "到期", "修", "换",
             "派工", "处理完"],
    "隐患": ["隐患", "故障", "坏了", "失效", "误报", "不亮", "被堵", "遮挡",
             "缺失", "停用", "重大问题"],
    "验收": ["验收", "备案", "审图", "报审", "检测", "调试", "竣工", "投入使用"],
    "值班": ["值班", "控制室", "交接班", "持证", "操作员", "24小时"],
    "推诿": ["不管", "再说", "下个月", "他们负责", "不是我们", "找", "等着", "拖"],
    "升级": ["12345", "举报", "投诉", "消防救援", "挂牌", "停产", "停工", "查封"],
}


def match_focus(text, focus):
    words = FOCUS_ALIAS.get(focus)
    if words:
        return any(w in text for w in words)
    return focus in text


def main():
    ap = argparse.ArgumentParser(
        description="从微信聊天记录中扫描消防隐患条目、整改期限与超期（本地运行）")
    ap.add_argument("--file", required=True, help="聊天记录文件（.md / .txt）")
    ap.add_argument("--scenario", default="all",
                    help="problem隐患登记 | acceptance验收备案 | duty维保履职 | all全部（默认）")
    ap.add_argument("--as-of", dest="as_of", default=None,
                    help="期限判定基准日 YYYY-MM-DD，默认今天")
    ap.add_argument("--focus", default=None,
                    help="只看含该关键词/类别的消息。类别：整改、隐患、验收、值班、推诿、升级")
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
        sys.exit("[错误] --scenario 取值：problem | acceptance | duty | all")

    messages, meta = parse_messages(args.file)

    if args.focus:
        messages = [m for m in messages if match_focus(m["text"], args.focus)]
        meta["focused"] = args.focus
        meta["matched_focus"] = len(messages)
        meta["focus_kind"] = "类别" if args.focus in FOCUS_ALIAS else "字面"
        if not messages:
            hit_words = FOCUS_ALIAS.get(args.focus)
            hint = ("（该类别下可匹配的说法：%s）"
                    % "、".join(hit_words[:6])) if hit_words else ""
            sys.exit("[提示] 没有消息命中「%s」%s\n"
                     "过滤后没有可分析内容，请去掉 --focus 重新扫描。"
                     % (args.focus, hint))

    if not messages and not args.focus:
        sys.exit("[警告] 未解析出任何消息。\n"
                 "请确认文件格式为每行 `[YYYY-MM-DD HH:MM] 发送者: 内容`。\n"
                 "可先用技能 wechat-local-reader-tianbao 导出聊天记录。")

    scenario = args.scenario if args.scenario != "all" else "all"

    if scenario == "all":
        hits, misses, snippets = [], [], []
        for sc in ("problem", "acceptance", "duty"):
            h, m, s = scan_elements(messages, sc)
            for x in h + m:
                x["scenario"] = ELEMENTS[sc]["label"]
            hits += h
            misses += m
            snippets += s
    else:
        hits, misses, snippets = scan_elements(messages, scenario)

    items = extract_items(messages, as_of)
    milestones = scan_milestones(messages)
    refusals = [m for m in messages if any(w in m["text"] for w in REFUSAL_WORDS)]

    repeat = []
    from collections import Counter
    for k, v in Counter(i["system"] for i in items).most_common():
        if v >= 2:
            repeat.append((k, v))

    res = {
        "scenario": scenario,
        "as_of": as_of,
        "meta": meta,
        "hits": hits,
        "misses": misses,
        "snippets": snippets,
        "items": items,
        "repeat": repeat,
        "milestones": milestones,
        "refusals": refusals,
    }

    text = render_json(res) if args.format == "json" else render_markdown(res)
    if args.out:
        d = os.path.dirname(args.out)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        sys.stderr.write("已写入 %s\n" % args.out)
    else:
        print(text)


if __name__ == "__main__":
    main()
