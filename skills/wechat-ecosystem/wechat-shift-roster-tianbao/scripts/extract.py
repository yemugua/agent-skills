# -*- coding: utf-8 -*-
"""
wechat-shift-roster / extract.py

从微信聊天记录中扫描排班考勤要点、班次与加班线索、仲裁时效。纯标准库，不联网、不上传。

用法：
    python extract.py --file 聊天记录.md
    python extract.py --file 聊天记录.md --scenario roster   # roster排班 | overtime加班| leave假期
    python extract.py --file 聊天记录.md --focus 排班
    python extract.py --file 聊天记录.md --as-of 2026-09-01  # 时效基准日
    python extract.py --file 聊天记录.md --format json --out out.json

输入行格式（每行一条）：
    [2026-05-12 18:42] 主管: 本周排班 23号白班9点到18点 24号夜班22点到6点
    [2026-05-12 18:45] 小李: 收到，24号夜班我上
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
# 班次时间抽取（夜班 -> 跨天）
# ---------------------------------------------------------------------------

# 一个时间段里的四种写法：9:00-18:00 / 9:00到18:00 / 9点到18点 / 22-6 / 22:00~6:00
# 思路：时 +（可选分 + 可选「点」这种分隔符）+ 连接词（到/至/-/~/~）+ 时 +（可选分）
TIME_RE = re.compile(
    r"(?P<h1>\d{1,2})\s*(?P<sep1>[点:：])?\s*(?P<m1>\d{2})?\s*"
    r"(?P<sep2>[-–—~到至]|点到)\s*"
    r"(?P<h2>\d{1,2})\s*(?P<sep3>[点:：])?\s*(?P<m2>\d{2})?"
)

SHIFT_KINDS = [
    ("夜班", ("夜班", "晚班", "通宵", "零点班", "大夜")),
    ("早班", ("早班", "上午班", "早八")),
    ("中班", ("中班", "下午班", "午班")),
    ("白班", ("白班", "日班", "正常班")),
    ("值班", ("值班", "值守", "坐岗", "待命", "值守班")),
    ("加班", ("加班", "加点", "延时")),
]

# 中文数字（几号）
CN_DIGIT = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
DAY_RE = re.compile(r"(?P<n>[0-9]{1,2}|[一二两三四五六七八九十]{1,3})\s*号")


def parse_cn_day(seg):
    """「三」→3、「十五」→15、「二十」→20、「十一」→11。"""
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


def _kind_near(text, lo, hi):
    """
    找这个时间点属于哪个班次。

    排班通知常写成「5号白班9点到18点，6号夜班22点到6点」——
    只看整句会把两个班都算成夜班，所以先紧贴时间点往前 10 字找，
    再放宽到 ±20 字，最后才退回整条消息。
    """
    for s, e in ((max(0, lo - 10), lo), (max(0, lo - 20), min(len(text), hi + 20))):
        win = text[s:e]
        for name, words in SHIFT_KINDS:
            if any(w in win for w in words):
                return name
    return None


def extract_shifts(messages):
    """从聊天文本里抽取班次：日期 + 班次类型 + 起止时间（含跨天、一话多班）。"""
    out = []
    for msg in messages:
        t = msg["text"]
        # 先找整条消息里出现过的班次类型（作为兜底）
        whole_kinds = [name for name, words in SHIFT_KINDS if any(w in t for w in words)]

        # 一股话里可能列多个班（「13号夜班22点到6点，14号白班9点到18点」），逐个时间点抽
        day_marks = list(DAY_RE.finditer(t))
        for tm in TIME_RE.finditer(t):
            try:
                h1 = int(tm.group("h1"))
                h2 = int(tm.group("h2"))
            except (TypeError, ValueError):
                continue
            if not (0 <= h1 <= 23 and 0 <= h2 <= 23):
                continue
            m1 = int(tm.group("m1") or 0)
            m2 = int(tm.group("m2") or 0)

            end_h, end_m = h2, m2
            cross_day = end_h < h1 or (end_h == h1 and end_m < m1)
            if cross_day:
                end_h += 24
            hours = round(end_h + end_m / 60.0 - (h1 + m1 / 60.0), 2)
            if hours <= 0 or hours > 16:      # 滤掉「工资20到30」这类误伤
                continue

            # 班次类型：优先取时间点附近的
            kind = _kind_near(t, tm.start(), tm.end()) or (whole_kinds[0] if whole_kinds else "班次")

            # 日期：取时间点之前最近的「N号」
            pre = t[:tm.start()]
            day_val = None
            day_raw = None
            for dm in DAY_RE.finditer(pre):
                day_raw = dm.group("n")
                n = int(day_raw) if day_raw.isdigit() else parse_cn_day(day_raw)
                if n is not None:
                    day_val = n

            out.append({
                "date": msg["ts"].date().isoformat() if msg["ts"] else None,
                "day": day_val,
                "dayRaw": day_raw,
                "kind": kind,
                "start": "%02d:%02d" % (h1, m1),
                "end": "%02d:%02d" % (h2, m2),
                "crossDay": cross_day,
                "hours": hours,
                "ts_raw": msg["ts_raw"],
                "who": msg["who"],
                "text": t[:70],
            })
    return out


# ---------------------------------------------------------------------------
# 要件库
# ---------------------------------------------------------------------------


def kw(*words):
    return list(words)


ELEMENTS = {
    "roster": {
        "label": "排班与考勤",
        "items": [
            ("排班主体", "职工",
             kw("排班", "值班表", "值班表发", "排一下", "排个", "安排一下", "值班安排")),
            ("排班周期", "职工",
             kw("这周", "本周", "下周", "这个月", "本月", "轮值", "倒班", "轮班", "一轮")),
            ("班次时间", "职工",
             kw("白班", "夜班", "早班", "中班", "通宵", "零点", "几点", "点到", "上到", "几点到")),
            ("岗位与地点", "职工",
             kw("岗位", "在岗", "打卡", "到岗", "现场", "值班室", "控制室", "门店", "工地点")),
            ("本人确认" , "职工",
             kw("收到", "知道了", "好的我上", "我上", "我排", "认了", "确认", "OK", "ok")),
            ("考勤记录", "单位举证",
             kw("打卡", "考勤", "签到", "签退", "刷脸", "指纹", "门禁", "定位", "钉钉", "企微")),
            ("加班审批", "单位举证",
             kw("审批", "申请加班", "报备", "走流程", "打申请", "领导批", "没批")),
            ("调休记录", "单位举证",
             kw("调休", "补休", "倒休", "换班", "顶个班", "换一下班")),
        ],
    },
    "overtime": {
        "label": "加班与加班费",
        "items": [
            ("加班事实", "职工",
             kw("加班", "加点", "加班费", "延时", "额外上了", "没走")),
            ("延长时长", "职工",
             kw("小时", "时长", "几个小时", "熬了", "干到", "忙到", "几点才")),
            ("工作日加班", "职工",
             kw("工作日加班", "晚上加班", "下班后", "延长时间", "平时加班", "加点")),
            ("休息日加班", "职工",
             kw("周末", "周六", "周日", "休息日", "礼拜六", "礼拜天", "节假日加班")),
            ("法定节假日", "职工",
             kw("春节", "国庆", "劳动节", "五一", "十一", "清明", "端午", "中秋", "元旦",
                "法定节", "过节", "过年")) ,
            ("加班费基数", "单位举证",
             kw("小时工资", "日工资", "底薪", "基本工资", "最低工资", "工资标准", "合同约定")),
            ("已付加班费", "单位举证",
             kw("加班费", "已含", "含在", "工资里", "补了", "已经补", "发过了", "这块发了")),
            ("不定时/综合工时", "单位举证",
             kw("不定时", "综合计算", "综合工时", "不定时工时", "弹性工作", "备勤")),
            ("值班而非加班", "单位举证",
             kw("值班", "值守", "值班津贴", "值守费", "不是加班", "算值班", "坐岗", "待命")),
        ],
    },
    "leave": {
        "label": "假期与离职结算",
        "items": [
            ("年假未休", "职工",
             kw("年假", "年休假", "没休", "未休", "带薪假", "年假没")),
            ("年假天数", "职工",
             kw("五天", "10天", "十五天", "5天假", "10天假", "累计工作")),
            ("离职结算", "职工",
             kw("离职", "辞职", "交接", "走人", "不干了", "离职结算", "最后一个月")),
            ("未签合同二倍", "职工",
             kw("没签", "未签", "没合同", "二倍工资", "双倍工资", "没给我一份")),
            ("经济补偿", "职工",
             kw("补偿", "N", "赔偿", "遣散", "解除合同", "裁员")),
            ("争议时效", "职工",
             kw("仲裁", "投诉", "劳动监察", "12333", "起诉", "去劳动", "仲裁委")),
        ],
    },
}

# 单位拒付/推诿表述
REFUSAL_RE = re.compile(
    r"没有加班|不算加班|不是加班|算值班|值班费|没有审批|没申请|没走流程|"
    r"不定时|综合工时|不用给|不给|没法给|不能算|已经调休|已经补休|"
    r"已经含|工资里含|含在工资|都发过了|结清了|一次性给|这个不能要"
)

# 程序里程碑
MILESTONE_PATTERNS = {
    "排班通知": kw("排班", "值班表", "安排一下", "本周上", "轮到"),
    "收到确认": kw("收到", "知道了", "好", "OK", "ok"),
    "加班安排": kw("加班", "加点", "延长时间", "加班通知", "今晚上"),
    "考勤记录": kw("打卡", "考勤", "签到", "签退", "门禁", "定位打卡"),
    "调休补休": kw("调休", "补休", "倒休", "换班"),
    "拒付推诿": kw("不算加班", "不是加班", "算值班", "没审批", "没申请", "已经调休",
                   "已经补休", "工资里含", "都发过了"),
    "协商补偿": kw("补偿", "给你补", "一起结", "和解", "算了"),
    "法律途径": kw("仲裁", "劳动监察", "12333", "投诉", "起诉", "仲裁委", "律师"),
}

# 有效催告四要素（跟催款技能同一套思路）
DEMAND_FLAG = {
    "有金额": lambda t: bool(re.search(r"\d+\s*小时|\d+\s*天|\d+\s*倍", t)),
    "有时段": lambda t: bool(TIME_RE.search(t)),
    "有日期": lambda t: bool(re.search(r"\d{1,2}\s*号|\d{4}年|今天|明天|本周|这周", t)),
    "有主张": lambda t: any(w in t for w in ("加班费", "补", "结", "核算", "仲裁",
                                             "小时工资", "天数", "折算")),
}


def scan_elements(messages, scenario):
    """返回 (hits, misses, snippets)。同一条消息只归属一个要件。"""
    scen = ELEMENTS.get(scenario)
    if not scen:
        return [], [], []
    hits, misses, snippets = [], [], []
    # 一条消息最多被 2 个要件引用（全禁会让后面的要件饿死，全放又是一句顶十条）
    used = {}
    MAX_USE = 2
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
            hits.append({
                "name": name, "burden": burden, "count": len(matched),
                "words": sorted({w for _, _, w in matched}),
            })
        else:
            misses.append({"name": name, "burden": burden, "words": words})
    return hits, misses, snippets


def scan_milestones(messages):
    return [(label, [m for m in messages if any(w in m["text"] for w in words)])
            for label, words in MILESTONE_PATTERNS.items()]


def detect_refusals(messages):
    return [m for m in messages if REFUSAL_RE.search(m["text"])]


# ---------------------------------------------------------------------------
# 时效（劳动仲裁 1 年）
# ---------------------------------------------------------------------------


def add_years(d, years):
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return date(d.year + years, 2, 28)


def _earliest_date(messages):
    """消息列表里最早的那个日期（注意 min(key=) 返回的是 dict，不是时间戳）。"""
    dated = [m for m in messages if m["ts"]]
    if not dated:
        return None
    return min(dated, key=lambda m: m["ts"])["ts"].date()


def find_trigger_date(messages):
    """找最早的排班/加班相关日期（时效起算点）。"""
    words = ("排班", "加班", "值班", "考勤", "打卡")
    dated = [m for m in messages if any(w in m["text"] for w in words)]
    d = _earliest_date(dated)
    return d if d else _earliest_date(messages)


def compute_deadline(start, years, as_of):
    if start is None:
        return None, None
    end = add_years(start, years)
    return end, (end - as_of).days


# ---------------------------------------------------------------------------
# 催告质量评估
# ---------------------------------------------------------------------------

CLOSURE_RE = re.compile(r"(收到|知道了|好的|嗯|OK|ok|行)")


def assess_demands(messages):
    """找带"主张权利"色彩的消息并打分。"""
    out = []
    for msg in messages:
        t = msg["text"]
        if not any(w in t for w in ("加班", "值班", "排班", "考勤", "补", "结清",
                                    "仲裁", "小时", "天数", "小时工资")):
            continue
        flags = {name: fn(t) for name, fn in DEMAND_FLAG.items()}
        score = sum(1 for v in flags.values() if v)
        out.append({"msg": msg, "flags": flags, "score": score})
    out.sort(key=lambda x: -x["score"])
    return out


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------

DISCLAIMER = (
    "本报告由本地脚本对聊天记录做**要件与关键词扫描**生成，"
    "仅用于整理材料、发现缺口，不构成法律意见，不预测裁决结果。"
    "涉及违法解除、二倍工资或金额较大的，请咨询执业律师或当地法律援助。"
)


def fmt(n):
    return "{:,.2f}".format(n)


def _where_to_get(name):
    table = {
        "排班主体": "微信排班通知 / 群公告 / 排班系统",
        "排班周期": "排班表原文（保留时间线）",
        "班次时间": "排班通知里的几点到几点；夜班注意跨天",
        "岗位与地点": "排班表 / 打卡定位 / 工牌",
        "本人确认": "在群里回一句「收到，X号夜班 X点到X点」——钉死排班事实",
        "考勤记录": "向单位索要；不给就在仲裁里申请责令其提供（须保存 2 年以上）",
        "加班审批": "单位系统里的审批记录；单位主张时由他举证",
        "调休记录": "调休单 / 系统记录 / 打卡对应的休息日",
        "加班事实": "排班表 + 考勤 + 在岗痕迹三样凑齐",
        "延长时长": "逐天算小时数，别只说「经常加班」",
        "工作日加班": "小时工资 × 150% × 小时数",
        "休息日加班": "小时工资 × 200%（或安排补休）",
        "法定节假日": "小时工资 × 300%，❗不能调休替代",
        "加班费基数": "劳动合同约定；没约定按正常出勤工资，且不低于当地最低工资",
        "已付加班费": "要他出示工资条分项 + 计算方式；笼统「含」不成立",
        "不定时/综合工时": "要人社部门批复；没有就按标准工时算",
        "值班而非加班": "按「能不能干私事／有没有产出／有没有休息条件」三步拆",
        "年假未休": "累计工龄满 1 年才有；离职时一次性结（额外 200%）",
        "年假天数": "满1年5天 / 满10年10天 / 满20年15天",
        "离职结算": "离职当月把加班费、未休年假一并结清",
        "未签合同二倍": "入职满 1 个月没签书面合同，可主张二倍工资（最高 11 个月）",
        "经济补偿": "N / 2N，看解除是否合法",
        "争议时效": "在职期间追讨加班费**不受 1 年限制**；离职后 1 年内申请仲裁",
    }
    return table.get(name, "按聊天记录与单位留存材料整理")


def _next_actions(res):
    acts = []
    if res["deadline_info"][1] is not None and res["deadline_info"][1] < 0:
        acts.append("**已超仲裁时效 1 年**，先看能不能主张时效中断（离职后一年内发过书面催告吗）")
    elif res["deadline_info"][1] is not None and res["deadline_info"][1] < 90:
        acts.append("**距时效届满仅 %d 天**，立刻发一条书面催告并留痕（中断 1 年时效）"
                    % res["deadline_info"][1])
    else:
        acts.append("还在职：追讨加班费**不受 1 年限制**（《劳动争议调解仲裁法》27条第3款），"
                    "但离职后就开始跑 1 年，别拖到离职那天才想起")

    weak = [d for d in res["demands"] if d["score"] <= 2]
    strong = [d for d in res["demands"] if d["score"] >= 3]
    if strong:
        acts.append("有 %d 条表述可作为主张权利的证据（含时段/日期/金额/主张）" % len(strong))
    if weak:
        acts.append("有 %d 条偏弱：补一句写清「X 月 X 日 加班 X 小时，按小时工资 150%% 应补 ___」"
                    % len(weak))

    miss_names = {m["name"] for m in res["misses"]}
    for key, msg in (
        ("本人确认", "⭐ 收到排班通知务必回一句「收到，X 号夜班 X 点到 X 点」——"
                     "排班通知 + 对方确认 = 加班事实直接钉死，比十张截图都值钱"),
        ("考勤记录", "向单位索要考勤；他拿不出或给的不对，可作对单位不利的认定"),
        ("加班事实", "把排班表、考勤、在岗痕迹三样凑齐，缺一样都会被说成「自愿留下」"),
        ("法定节假日", "法定节假日那几天单独拎出来——**不能调休，必须 300%**"),
        ("加班审批", "他说「没审批不算」，要那套制度**公示告知过你**；且实际安排的加班不因没申请而免付"),
        ("不定时/综合工时", "他要主张不定时/综合工时，得拿**人社部门批复**；没有就按标准工时算"),
        ("加班费基数", "合同有约定按约定；没约定按正常出勤工资，**别让他按最低工资糊弄**"),
        ("年假未休", "未休年假额外 200%（另 100% 是正常工资），离职时一并结"),
        ("未签合同二倍", "入职满 1 个月没签书面劳动合同 → 二倍工资，**金额往往比加班费高，别漏**"),
        ("调休记录", "休息日可补休；但要他证明**什么时候、有没有真调**"),
    ):
        if key in miss_names:
            acts.append(msg)
            break

    if res["refusals"]:
        acts.append("把对方每条拒付/推诿原话列出来逐条回怼：重点打「举证责任在单位」"
                    "——考勤、工资台账都是他保管")
    acts.append("逐天算小时数：工作日 150% / 休息日 200% / 法定节假日 300%，"
                "分开列，别笼统算一个总数")
    acts.append("仲裁**前置**，先去劳动人事争议仲裁委员会，不收费，别直接去法院")
    acts.append("导出完整连续记录（含对你不利的部分），保留群名与时间线")
    acts.append("三处备份：本机 + 云盘 + 原件；重要通知做录屏（显示群名、发送者、时间）")
    return acts


def render_markdown(res):
    out = []
    w = out.append
    scen_label = ELEMENTS.get(res["scenario"], {}).get("label", res["scenario"])
    as_of = res["as_of"]

    w("# 微信排班考勤扫描报告")
    w("")
    w("> 场景：**%s**　扫描日期：%s　文件：`%s`"
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

    if res["shifts"]:
        tot = sum(s["hours"] for s in res["shifts"])
        cross = len([s for s in res["shifts"] if s["crossDay"]])
        kinds = sorted({s["kind"] for s in res["shifts"]})
        w("- 抽出 **%d 个班次**，合计 **%s 小时**（其中跨天夜班 %d 个）"
          % (len(res["shifts"]), fmt(tot), cross))
        w("- 涉及班次类型：%s" % "、".join(kinds))

    expires, days_left = res["deadline_info"]
    if expires:
        if days_left is None:
            w("- 仲裁时效：**无法计算**（记录里没有可识别的排班日期）")
        elif days_left < 0:
            w("- 仲裁时效：**⚠️ 已过 %d 天**（起算 %s，1 年届满 %s）"
              % (-days_left, res["trigger_date"], expires))
        elif days_left < 90:
            w("- 仲裁时效：**⚠️ 仅剩 %d 天**（起算 %s，届满 %s）"
              % (days_left, res["trigger_date"], expires))
        else:
            w("- 仲裁时效：剩余 **%d 天**（起算 %s，届满 %s）"
              % (days_left, res["trigger_date"], expires))
    else:
        w("- 仲裁时效：**无法计算**，请先补充排班日期")

    if res["inService"]:
        w("- 你在职中：追讨加班费**不受 1 年限制**"
          "（《劳动争议调解仲裁法》第 27 条第 3 款第四项，加班费属劳动报酬）")
    if res["demands"]:
        strong = [d for d in res["demands"] if d["score"] >= 3]
        weak = [d for d in res["demands"] if d["score"] <= 2]
        if strong:
            w("- 可作为主张权利依据：**%d 条**" % len(strong))
        if weak:
            w("- ⚠️ **偏弱表述 %d 条**——缺日期/时段/小时数，法律上难以认定" % len(weak))
    if res["refusals"]:
        w("- 对方**拒付/推诿表述 %d 条**，这是争议焦点" % len(res["refusals"]))
    if res["milestones"]:
        w("- 识别到 **%d 类程序节点**：%s"
          % (len(res["milestones"]), "、".join(m[0] for m in res["milestones"])))
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
        w("聊天里没有 ≠ 没有材料，很多在单位手里（考勤、工资台账由他保管）。")
        w("")
        w("| 缺失要件 | 举证方 | 去哪里补 |")
        w("|---|---|---|")
        for m in misses:
            w("| %s | %s | %s |" % (m["name"], m["burden"], _where_to_get(m["name"])))
        w("")

    if focus_mode or res["refusals"]:
        w("## 四、争议焦点（拒付与推诿表述）")
        w("")
        if not res["refusals"]:
            w("本次过滤范围内没有提取到拒付/推诿表述。要看全貌请去掉 `--focus` 重跑。")
            w("")
        for i, msg in enumerate(res["refusals"][:12], 1):
            w("%d. **%s**%s" % (i, f"[{msg['ts_raw']}] " if msg["ts_raw"] else "",
                                f"{msg['who']}：" if msg["who"] else ""))
            w("   > %s" % msg["text"][:120])
        w("")
        w("> **破局参照**：")
        w("> - 考勤记录、工资台账由**单位保管**（须保存 2 年以上），他不给 → 可作出**对单位不利的认定**。")
        w("> - 《劳动法》第 44 条：加班费 **150% / 200% / 300%** 三档，法定节假日不能调休替代。")
        w("> - 单位主张「不定时/综合工时」→ 要**人社部门批复**，没有就按标准工时算。")
        w("> - **值班 ≠ 加班**：看能不能干私事、有没有业务产出、有没有休息条件。")
        w("")

    if focus_mode or res["shifts"]:
        w("## 五、班次抽取（从聊天里提出来的时间）")
        w("")
        if not res["shifts"]:
            w("本次过滤范围内没抽到班次时间。班次识别要「几点到几点」这种写法"
              "（如 9:00-18:00 / 22点到6点 / 22:00~6:00），"
              "只说「上夜班」没有时间抽不出来，可用 `--focus 排班` 全量重跑。")
            w("")
        if res["shifts"]:
            w("| 日期 | 班次 | 起止 | 是否跨天 | 时长(h) | 出处 |")
            w("|---|---|---|---|---|---|")
            for s in res["shifts"][:20]:
                w("| %s | %s | %s–%s | %s | %s | %s |"
                  % (s["date"] or "—", s["kind"], s["start"], s["end"],
                     "是（次日）" if s["crossDay"] else "否", fmt(s["hours"]),
                     (s["who"] or "—")))
            w("")
            tot = sum(s["hours"] for s in res["shifts"])
            w("> 合计 **%s 小时**。夜班跨天要留意：22:00–6:00 算 8 小时，别按 6 小时算。"
              % fmt(tot))
            w("> ⚠️ 夜班/值通宵属于「值班还是加班」的争议高发区，按"
              "「能不能干私事／有没有业务产出／有没有休息条件」三步判断。")
            w("")

    if focus_mode or res["demands"]:
        w("## 六、主张表述质量评估（关系时效能否中断）")
        w("")
        w("> 一条主张要有效，最好同时有**日期 + 时段 + 小时数 + 明确主张**。")
        w(">「加班费以后再算」不算，「X月X日 加了 X 小时，按小时工资 150% 应补 ___」才算。")
        w("")
        w("| 时间 | 谁 | 日期 | 时段 | 小时/天数 | 主张 | 得分 | 原话 |")
        w("|---|---|---|---|---|---|---|---|")
        for d in res["demands"][:12]:
            m = d["msg"]
            f = d["flags"]
            g = lambda k: "✅" if f[k] else "—"
            w("| %s | %s | %s | %s | %s | %s | %d/4 | %s |"
              % (m["ts_raw"], m["who"] or "—", g("有日期"), g("有时段"),
                 g("有金额"), g("有主张"), d["score"], m["text"][:34].replace("|", "/")))
        w("")
        w("> 得分 **≥3** 才算有效主张；**≤2** 的补一条新的。")
        w("")

    if focus_mode or res["milestones"]:
        w("## 七、关键程序节点")
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
        w("## 八、关键证据片段")
        w("")
        w("> 导出完整对话时**不要只截取有利片段**。对方最容易攻击「剪辑」，"
          "完整连续记录反而更有力。群通知比私聊强，因为能证明是管理行为。")
        w("")
        for name, burden, msg, word in res["snippets"][:14]:
            w("- **[%s] %s**（%s · 命中「%s」）" % (msg["ts_raw"], name, burden, word))
            w("  > %s" % msg["text"][:110])
        w("")

    w("## 九、下一步行动清单")
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
        "shifts": res["shifts"],
        "shiftSummary": {
            "count": len(res["shifts"]),
            "totalHours": round(sum(s["hours"] for s in res["shifts"]), 2),
            "crossDayCount": len([s for s in res["shifts"] if s["crossDay"]]),
            "kinds": sorted({s["kind"] for s in res["shifts"]}),
        } if res["shifts"] else None,
        "deadline": {
            "limitYears": 1,
            "triggerDate": res["trigger_date"].isoformat() if res["trigger_date"] else None,
            "expireDate": res["deadline_info"][0].isoformat() if res["deadline_info"][0] else None,
            "daysLeft": res["deadline_info"][1],
        },
        "inService": res["inService"],
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
        "demands": [
            {"ts": d["msg"]["ts_raw"], "who": d["msg"]["who"], "text": d["msg"]["text"],
             "flags": d["flags"], "score": d["score"]}
            for d in res["demands"]
        ],
        "disclaimer": DISCLAIMER,
    }, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

FOCUS_ALIAS = {
    "排班": ["排班", "值班表", "值班", "轮班", "倒班", "上夜班", "白班", "夜班",
             "安排一下", "轮到", "几点到"],
    "加班": ["加班", "加点", "延时", "小时", "时长", "熬", "干到", "忙到",
             "150", "200", "300", "倍"],
    "调休": ["调休", "补休", "倒休", "换班", "顶班"],
    "拒付": ["不算加班", "不是加班", "算值班", "没审批", "没申请", "没走流程",
             "已经调休", "已经补休", "工资里含", "都发过了", "不能要"],
    "时效": ["仲裁", "劳动监察", "12333", "投诉", "起诉", "律师", "时效",
             "过期", "一年", "离职"],
}


def match_focus(text, focus):
    words = FOCUS_ALIAS.get(focus)
    if words:
        return any(w in text for w in words)
    return focus in text


def main():
    ap = argparse.ArgumentParser(
        description="从微信聊天记录中扫描排班考勤、班次与加班费要件（本地运行）")
    ap.add_argument("--file", required=True, help="聊天记录文件（.md / .txt）")
    ap.add_argument("--scenario", default="all",
                    help="roster排班考勤 | overtime加班费 | leave假期离职 | all全部（默认）")
    ap.add_argument("--as-of", dest="as_of", default=None,
                    help="时效基准日 YYYY-MM-DD，默认今天")
    ap.add_argument("--focus", default=None,
                    help="只看含该关键词/类别的消息。类别：排班、加班、调休、拒付、时效；"
                         "也可传任意字面词")
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
        sys.exit("[错误] --scenario 取值：roster | overtime | leave | all")

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
        for sc in ("roster", "overtime", "leave"):
            h, m, s = scan_elements(messages, sc)
            for x in h + m:
                x["scenario"] = ELEMENTS[sc]["label"]
            hits += h
            misses += m
            snippets += s
    else:
        hits, misses, snippets = scan_elements(messages, scenario)

    shifts = extract_shifts(messages)
    milestones = scan_milestones(messages)
    refusals = detect_refusals(messages)
    demands = assess_demands(messages)

    trigger_date = find_trigger_date(messages)
    expires, days_left = compute_deadline(trigger_date, 1, as_of)
    # 简单判断"是否还在职"：最后一条消息距今 90 天内 → 视为在职
    in_service = False
    dated = [m for m in messages if m["ts"]]
    if dated:
        last = max(dated, key=lambda m: m["ts"])["ts"].date()
        in_service = (as_of - last).days <= 90

    res = {
        "scenario": scenario,
        "as_of": as_of,
        "meta": meta,
        "hits": hits,
        "misses": misses,
        "snippets": snippets,
        "shifts": shifts,
        "milestones": milestones,
        "refusals": refusals,
        "demands": demands,
        "trigger_date": trigger_date,
        "deadline_info": (expires, days_left),
        "limit_years": 1,
        "inService": in_service,
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
