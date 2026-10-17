#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交通违法处理与扣分核查。

用法：
  python traffic_violation_check.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python traffic_violation_check.py 采集表.md --json
退出码：0 正常；2 关键信息缺失。
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta

UNFILLED_MARK = re.compile(r"[/／]")
DATE_RE = re.compile(r"(20\d{2})[-年\.](\d{1,2})[-月\.](\d{1,2})")

PLACEHOLDER_WORDS = ["待填", "请填", "例如", "示例", "如：", "（", "(", "有/无", "是/否",
                     "选填", "填写"]

# 违法类型：不同类型的处理渠道、扣分与罚款口径差别很大
VIOLATION_TYPES = [
    ("机动车超速", ["超速", "超速行驶", "超速50", "超过规定时速"]),
    ("闯红灯", ["闯红灯", "闯灯", "信号灯"]),
    ("违停", ["违停", "违章停车", "停车违规", "违例停车", "停在"]),
    ("不按导向车道", ["不按导向", "导向车道", "车道行驶", "压导向"]),
    ("违法变道/加塞", ["变道", "加塞", "并线", "强行变道"]),
    ("占用应急车道", ["应急车道", "应急通道", "占用应急"]),
    ("违规使用远光灯", ["远光灯", "开远光"]),
    ("未悬挂号牌/遮挡", ["号牌", "牌照", "遮挡号牌", "故意遮挡"]),
    ("酒驾醉驾", ["酒驾", "醉驾", "饮酒", "喝酒后", "酒后驾驶", "酒后开车", "饮酒后驾驶",
               "血液酒精"]),
    ("无证驾驶", ["无证", "未取得驾驶证", "驾驶证被吊销", "准驾不符"]),
    ("交通事故", ["事故", "剐蹭", "碰撞", "追尾", "交通事故"]),
    ("非机动车/电动自行车", ["电动车", "非机动车", "电动自行车", "自行车", "外卖", "电动车"]),
]

# 扣分规则（常见口径，2022 年 4 月 1 日起施行的《道路交通安全违法行为记分管理办法》）
SCORE_TABLE = [
    ("饮酒后驾驶机动车", 12),
    ("醉酒后驾驶机动车", 12),
    ("使用伪造变造牌证", 9),
    ("驾驶与准驾车型不符", 9),
    ("未悬挂号牌或故意遮挡", 9),
    ("超速 50% 以上", 12),
    ("超速 20%~50%", 6),
    ("超速不足 20%", 3),
    ("驾驶机动车在高速公路上倒车逆行穿越中央分隔带掉头", 12),
    ("驾驶机动车在高速公路违法停车", 9),
    ("驾驶未悬挂号牌机动车在高速公路上", 12),
    ("不按导向车道行驶", 2),
    ("不按规定超车", 2),
    ("不礼让行人", 3),
    ("驾驶时拨打接听手持电话", 3),
    ("闯红灯", 6),
    ("违反禁令标志指示", 6),
    ("违反禁止标线指示", 1),
    ("违法停放", 1),
    ("未按规定使用灯光", 1),
    ("未系安全带", 1),
    ("摩托车未戴安全头盔", 1),
]

# 高分/吊销重点情形
MAJOR_FLAGS = [
    ("酒驾醉驾", ["醉驾", "醉酒后驾驶", "血液酒精", "醉后驾驶", "醉酒驾驶"]),
    ("可能吊销驾驶证", ["吊销", "12分", "十二分", "暂扣", "驾驶证被扣"]),
    ("造成事故", ["事故", "剐蹭", "碰撞", "伤亡", "人伤", "死亡"]),
    ("无证驾驶", ["无证", "未取得驾驶证", "驾驶证被吊销"]),
    ("肇事逃逸", ["逃逸", "逃跑", "离开现场"]),
]

# 处理渠道关键词
CHANNELS = [
    ("交管 APP 线上处理", ["交管12123", "12123", "APP", "线上", "互联网"]),
    ("交警队窗口", ["交警", "窗口", "车管所", "现场"]),
    ("邮局代收", ["邮局", "代收"]),
    ("保险公司代扣", ["保险", "代扣", "保险公司"]),
    ("单位/雇主处理", ["单位", "雇主", "公司", "雇主处理"]),
]

# 常见加分/减分类情形
MITIGATIONS = [
    ("有证据可证明非机动车/非本人操作", ["非本人", "不是本人", "车辆被盗", "被借走", "套牌",
                          "被冒用", "非本人操作"]),
    ("有证据可证明客观情况变化", ["标志被遮挡", "标线不清", "信号灯故障", "摄像头异常",
                        "设备故障", "标志被覆盖"]),
    ("已主动处理并主动缴罚款", ["主动", "已缴", "已处理", "主动缴纳"]),
    ("首次违法且情节轻微", ["首次", "第一次", "轻微", "情节较轻"]),
    ("已接受罚款扣分", ["已接受", "已处理完毕", "已执行"]),
    ("有家庭困难需要处理", ["困难", "低保", "残疾", "重病", "特殊情况"]),
]

# 维权路径
PATHS = [
    ("第 1 步（先确认违法事实）",
     "登录**交管 12123**（官方 App）查询：违法时间、地点、违法行为、罚款金额、扣分数。**以这个为准**，"
     "别人告知的不一定准。若查不到，**去交警队或单位所在辖区窗口拉取**。"),
    ("第 2 步（判断是不是自己的车）",
     "看违法时的监控或照片：**车牌是否清楚、驾驶人是否可辨认**。"
     "如果车确实被套牌、被盗或被借走，**这条最重要**——可主张不是本车驾驶人。"),
    ("第 3 步（符合条件就申请撤销）",
     "**符合撤销条件的应当事人到现场或通过 12123 提交申请**："
     "① 违法记录被录入后，**机动车已转让**（须提供转让证明或过户记录）；"
     "② **违法行为被确认无效**（标志被遮挡、标线不清、信号灯故障、设备故障等）；"
     "③ **已被简易程序处罚的可以申请撤销**（本人到场并说明）；"
     "④ 机动车号牌被他人套用。"),
    ("第 4 步（先处理，再申诉）",
     "**对罚款有异议的**：在**收到处罚决定书 7 日内**向上一级交警部门申请行政复议；"
     "对扣分有异议的：先按程序处理，再向省级交管部门申请复核。**不要拒不接受处理**——"
     "逾期不处理会产生加处罚款，还会影响年检。"),
    ("第 5 步（主动处理、争取减免）",
     "**及时主动缴款**。首次违法、情节轻微、已改正的，可在申请时说明，争取从轻处理。"
     "**逾期未缴款会加处罚款**，得不偿失。"),
    ("第 6 步（单位/雇主的扣分分摊）",
     "营运车辆、货车、企业车辆的违法处理责任由单位承担。"
     "**但要注意**：很多地方对**驾驶人个人记分**不影响记在司机名下，"
     "单位代处理与个人记分是两件事，**要问清并保留书面说明**。"),
    ("第 7 步（影响与处理结果）",
     "扣分周期内累积扣满 12 分的，**暂扣驾驶证并参加学习考试**；"
     "**醉驾的还可能被吊销驾驶证、承担刑事责任**。"
     "**处理期间保持驾驶不违法记录，是最实际的做法。**"),
]

# 证据类别
EVIDENCE = [
    ("违法信息与决定书", ["违法记录", "决定书", "处罚决定", "告知书", "12123"]),
    ("本人身份与车辆信息", ["身份证", "驾驶证", "行驶证", "车辆", "车牌"]),
    ("车辆转让或过户证明", ["过户", "转让", "交强险", "登记", "变更"]),
    ("非本人操作的证明", ["监控", "照片", "车库", "泊位", "行车记录仪", "不在场", "出差",
                     "被借", "被盗", "套牌"]),
    ("客观情况异常的证明", ["标志", "标线", "信号灯", "设备故障", "摄像头", "施工"]),
    ("缴纳与处理凭证", ["缴费", "交款", "已处理", "发票", "回执"]),
    ("申诉与沟通记录", ["复议", "复核", "申请", "答复", "工单", "录音", "聊天"]),
]


def norm(s):
    if s is None:
        return ""
    s = str(s)
    s = s.replace("：", ":").replace("（", "(").replace("）", ")")
    s = s.replace("，", ",").replace("。", ".")
    s = re.sub(r"\s+", "", s)
    return s.strip()


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def build_kv(text):
    kv = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 2:
                k, v = cells[0], "|".join(cells[1:]).strip()
                if set(k) <= set("-: ") or set(v) <= set("-: "):
                    continue
                if k and k not in kv:
                    kv[k] = v
            continue
        if ":" in line or "：" in line:
            parts = re.split(r"[:：]", line, 1)
            if len(parts) == 2:
                k, v = parts[0].strip(), parts[1].strip()
                if k and k not in kv:
                    kv[k] = v
    return kv


def get_text(kv, aliases):
    for a in sorted(aliases, key=len, reverse=True):
        na = norm(a)
        for k, v in kv.items():
            if norm(k) == na:
                return v.strip()
    for a in sorted(aliases, key=len, reverse=True):
        na = norm(a)
        for k, v in kv.items():
            if na in norm(k):
                return v.strip()
    return ""


def filled(v):
    if v is None:
        return False
    v = str(v).strip()
    if not v:
        return False
    if UNFILLED_MARK.search(v):
        return False
    for w in PLACEHOLDER_WORDS:
        if v.startswith(w):
            return False
    return True


def yes(v):
    n = norm(v)
    if n in ("有", "是", "已经", "已", "已完成", "已做", "可以", "能", "已处理", "已缴"):
        return True
    return n.startswith("已") or n.startswith("有")


def no(v):
    n = norm(v)
    if n in ("无", "否", "没有", "未", "未做", "false", "no", "正常"):
        return True
    return n.startswith("无") or n.startswith("未") or n.startswith("没有")


def unknown(v):
    n = norm(v)
    return (not filled(v)) or n in ("不清楚", "不确定", "不知道", "待确认", "未知", "没填")


def hit_any(v, words):
    s = norm(v)
    if not filled(s):
        return None
    for w in words:
        if norm(w) in s:
            return True
    return False


def parse_num(s):
    if s is None:
        return None
    s = str(s).replace(",", "").replace("，", "")
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def fmt_num(x):
    if x is None:
        return "—"
    if abs(x - round(x)) < 1e-6:
        return str(int(round(x)))
    return ("%.2f" % x).rstrip("0").rstrip(".")


def money(x):
    return "¥" + fmt_num(x) if x is not None else "—"


def parse_date(s):
    if not s:
        return None
    m = DATE_RE.search(str(s))
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except Exception:
        return None


def base_date(s):
    d = parse_date(s or "")
    return d or date.today()


# ------------------------------------------------------------------ 一 违法定性
def classify(f):
    txt = (f["kind"] or "") + "|" + (f["detail"] or "")
    if not filled(txt):
        return []
    return [lbl for lbl, ws in VIOLATION_TYPES if hit_any(txt, ws) is True]


def checks_kind(f):
    out = []
    kinds = classify(f)
    k = f["kind"]
    if unknown(k) and unknown(f["detail"]):
        out.append(("违法行为类型", "待补正",
                    "违法是什么、什么时候、在哪里未填。"
                    "**违法类型决定扣分与罚款标准**。"
                    "请在 12123 上查，或按这些词填：超速、闯红灯、违停、"
                    "不按导向车道、违法变道、应急车道、远光灯、号牌、"
                    "酒驾醉驾、无证、事故、电动车。"))
    elif not kinds:
        out.append(("违法行为类型", "待补正",
                    "描述里没识别出具体违法类型。请用这些词："
                    "超速、闯红灯、违停、不按导向车道、违法变道加塞、"
                    "应急车道、远光灯、号牌遮挡、酒驾醉驾、无证驾驶、事故。"))
    else:
        out.append(("违法行为类型", "通过", "本次违法属于：**%s**。" % "、".join(kinds)))
    return out


def calc_score(f, kinds):
    """按类型估算扣分（取各类型内最重的口径）。"""
    txt = (f["kind"] or "") + "|" + (f["detail"] or "")
    if not filled(txt):
        return None, []
    matched = []
    for name, sc in SCORE_TABLE:
        if hit_any(txt, [name]) is True:
            matched.append((name, sc))
    if matched:
        return max(s[1] for s in matched), [m[0] for m in matched]
    # 类型识别到了但没匹配到具体记分项，按类型给个默认量级
    default = {
        "机动车超速": (3, "超速档位未写明"),
        "闯红灯": (6, "闯红灯"),
        "违停": (1, "违停"),
        "不按导向车道": (2, "不按导向车道"),
        "违法变道/加塞": (2, "违法变道"),
        "占用应急车道": (3, "占用应急车道"),
        "违规使用远光灯": (1, "远光灯"),
        "未悬挂号牌/遮挡": (9, "号牌"),
        "酒驾醉驾": (12, "酒驾醉驾"),
        "无证驾驶": (9, "无证或准驾不符"),
        "交通事故": (None, "事故按责任与后果认定"),
        "非机动车/电动自行车": (None, "电动自行车按地方规定处理"),
    }
    for kd in kinds:
        if kd in default:
            return default[kd]
    return None, []


def checks_score(f, kinds):
    out = []
    stated = parse_num(f["score"])
    calc, matched = calc_score(f, kinds)
    if unknown(f["score"]):
        if calc is None:
            out.append(("记分与罚款", "待补正",
                        "扣分与罚款金额未填，且无法从描述中推算。"
                        "**以 12123 或处罚决定书上的数字为准**；"
                        "电动自行车、事故类各地规定差别大，务必查本地口径。"))
        else:
            out.append(("记分与罚款", "有风险",
                        "采集表未填，脚本按「%s」推算约 **%s 分**。"
                        "**务必与 12123 上的实际扣分核对**，"
                        "不一致的以官方记录为准。" % (matched[0] if matched else kinds[0],
                                              calc if calc else "需自行确认")))
    else:
        # 12 分是暂扣驾驶证的临界点，属高风险；超过 12 属不通过
        if stated > 12:
            state = "不通过"
        elif stated >= 12:
            state = "有风险"
        else:
            state = "通过"
        msg = "申报扣分 %s 分。" % fmt_num(stated)
        if stated and stated >= 12:
            msg += ("**扣满 12 分将被暂扣驾驶证并参加学习考试**；"
                    "若周期内再次累积，驾驶证可能被吊销。")
        elif stated and stated >= 9:
            msg += "**9 分以上已属高风险档**，接近 12 分吊销线，务必逐条核对有无错误记录。"
        else:
            msg += "在记分周期内可承受，**但仍要逐条核对是否属本人驾驶**。"
        if calc is not None and calc != stated:
            msg += " 另：脚本按描述推算约 %s 分，**与申报值不一致，需向交管部门确认**。" % fmt_num(calc)
        out.append(("记分与罚款", state, msg))
    return out


def checks_major(f, kinds=None):
    out = []
    # 注意：不能把两个字段用 "|" 拼起来再判 filled——分隔符竖线不是未填标记，
    # 会让两个空字段拼出的 "|" 被判成已填，导致空表误判为"无重大情形"
    has_any = filled(f["kind"]) or filled(f["detail"])
    if not has_any:
        out.append(("是否属于重大违法", "待补正",
                    "是否醉驾、是否造成事故、是否有无证或逃逸情形未填。"
                    "**这几类不只是扣分罚款**——可能涉及吊销驾驶证、"
                    "刑事责任与保险拒赔。"))
        return out
    txt = (f["kind"] or "") + "|" + (f["detail"] or "")
    hits = [lbl for lbl, ws in MAJOR_FLAGS if hit_any(txt, ws) is True]
    if not hits:
        out.append(("是否属于重大违法", "通过", "未发现醉驾、事故、无证或逃逸等重大情形。"))
    else:
        out.append(("是否属于重大违法", "不通过",
                    "涉及：**%s**。这类情形的后果远超普通罚款："
                    "醉驾可能**吊销驾驶证并承担刑事责任**；"
                    "造成事故可能涉及**民事赔偿与保险拒赔**；"
                    "逃逸**加重处罚**。**立即咨询律师，不要自行处理**。" % "、".join(hits)))
    return out


# ------------------------------------------------------------------ 二 归属核实
def checks_owner(f):
    out = []
    who = f["driver_who"]
    if unknown(who):
        out.append(("违法驾驶人是否为本车", "待补正",
                    "违法时开车的是不是本人/本车未填。"
                    "**这是能不能撤销的第一判断**："
                    "车辆被盗、被套牌、被借出，**可以主张不是本车驾驶人**。"))
    elif hit_any(who, ["非本人", "不是本人", "被盗", "被借", "套牌", "被冒用",
                        "另有他人", "不在场"]) is True:
        out.append(("违法驾驶人是否为本车", "有风险",
                    "非本车驾驶人：**符合撤销条件的情形应尽快向交管部门申请**。"
                    "**要在收到处罚决定后尽快提出**，"
                    "并提供车辆不在本人控制范围内的证据（监控、行车记录仪、车位照片、"
                    "借用协议、报案记录等）。"))
    elif yes(who) or hit_any(who, ["本人", "自己开", "我开", "确系本人"]) is True:
        out.append(("违法驾驶人是否为本车", "通过",
                    "确认为本人或本车驾驶。**接下来重点看能否从轻或撤销事实本身**"
                    "（标志被遮挡、设备故障等）。"))
    else:
        out.append(("违法驾驶人是否为本车", "待补正",
                    "填的是「%s」，无法判断。请用这些词："
                    "本人 / 非本人 / 被盗 / 被借出 / 被套牌 / 不清楚。" % who))
    return out


def checks_objective(f):
    out = []
    v = f["objective_issue"]
    if unknown(v):
        out.append(("是否存在客观情况异常", "待补正",
                    "标志是否被遮挡、标线是否不清、信号灯是否故障、"
                    "摄像头是否异常未填。**这类属于可申请撤销的情形**。"))
        return out
    if hit_any(v, ["遮挡", "不清", "故障", "异常", "被覆盖", "施工", "移位",
                   "未看清", "模糊", "挡住", "遮挡物", "被挡", "树枝", "树叶",
                   "缺失", "损坏", "看不清", "误标"]) is True:
        out.append(("是否存在客观情况异常", "有风险",
                    "存在客观情况问题：**%s**。"
                    "**这是最有价值的撤销理由**，务必现场拍照取证："
                    "标志位置、标线清晰度、信号灯工作状态、摄像头位置与视角，"
                    "并保留原始照片的拍摄时间信息。" % v))
    else:
        out.append(("是否存在客观情况异常", "通过", "未发现客观情况异常，事实认定较难推翻。"))
    return out


# ------------------------------------------------------------------ 三 处理与时限
def checks_process(f, today):
    out = []
    d = f["notice_date"]
    dt = parse_date(d)
    if unknown(d):
        out.append(("收到处罚决定的时间", "待补正",
                    "什么时候收到处罚决定书或短信通知未填。"
                    "**复议与复核都有时限，错过就无法救济**。"))
    else:
        out.append(("收到处罚决定的时间", "通过",
                    "收到通知：%s（距核查日 %d 天）。"
                    % (d, (today - dt).days)))
    if dt:
        deadline = dt + timedelta(days=7)
        left = (deadline - today).days
        if left < 0:
            out.append(("行政复议时限", "不通过",
                        "**7 日复议时限已过**（%s 到期）。"
                        "**复议这条路基本走不通了**，但仍可："
                        "① 尝试向省级交管部门申请复核记分；"
                        "② 就扣分错误向交管部门申请更正。"
                        "**先处理再申诉，别让罚款一直挂着。**" % deadline.isoformat()))
        elif left <= 3:
            out.append(("行政复议时限", "有风险",
                        "复议时限剩 **%d 天**（%s 到期），**动作要快**。"
                        "对罚款有异议的，**收到决定书 7 日内**向上一级交警部门"
                        "申请行政复议；不要先按罚款处理。" % (left,
                                                    deadline.isoformat())))
        else:
            out.append(("行政复议时限", "通过",
                        "复议时限尚有 **%d 天**（%s 到期），"
                        "**对罚款有异议的应在此期间提出**。" % (left,
                                                     deadline.isoformat())))
    else:
        out.append(("行政复议时限", "待补正",
                    "因未填收到决定的时间，**无法判断复议时限是否已过**。"
                    "这一项很关键，请尽快确认。"))

    if unknown(f["handled"]):
        out.append(("是否已处理缴款", "待补正",
                    "罚款是否已缴、是否已申请撤销未填。"
                    "**逾期不处理会产生加处罚款**，还会影响年检与保险。"))
    elif yes(f["handled"]):
        out.append(("是否已处理缴款", "通过",
                    "已处理。**保存缴费凭证与处理回执**，"
                    "若后续记分有误可作为已配合处理的证明。"))
    else:
        out.append(("是否已处理缴款", "不通过",
                    "**尚未处理**。逾期不缴会产生**加处罚款**（按日计），"
                    "并可能影响**年检与保险续保**。"
                    "**即使有异议也要先处理，再另行申诉**。"))
    return out


# ------------------------------------------------------------------ 四 单位车辆
def checks_unit(f):
    out = []
    vtype = f["vehicle_type"]
    if unknown(vtype):
        out.append(("车辆性质", "待补正",
                    "是自有车、单位车、营运车还是租赁车未填。"
                    "**单位车与营运车的处理责任主体不同**，"
                    "涉及扣分分摊时差别很大。"))
    elif hit_any(vtype, ["单位", "营运", "公司", "货车", "出租", "网约", "租赁",
                        "租赁车"]) is True:
        out.append(("车辆性质", "有风险",
                    "属于：**%s**。单位或营运车辆通常由单位承担处理责任，"
                    "但**驾驶人记分仍记在本人名下**——这两件事要分开确认。"
                    "**要求单位出具书面说明并留存**，"
                    "避免出现「单位认了但分还在我名下」的情况。" % vtype))
    else:
        out.append(("车辆性质", "通过", "自有车辆，责任主体清晰。"))
    if unknown(f["unit_said"]):
        out.append(("单位如何处理", "待补正",
                    "单位或雇主怎么说的、要你出多少钱未填。"
                    "**扣分分摊的约定要落实到书面**，口头说了不算。"))
    elif hit_any(f["unit_said"], ["全扣", "扣钱", "罚款要我", "分摊", "扣绩效", "自己承担",
                        "要我出", "扣了", "扣工资", "从工资"]) is True:
        out.append(("单位如何处理", "有风险",
                    "单位说法：**%s**。**核对自己签的劳动合同、"
                    "员工手册或雇佣协议里关于交通违法处理的约定**——"
                    "用人单位不得随意扣押工资或罚款；"
                    "即使有约定，**也不得低于当地最低工资标准或造成生活困难**。"
                    "有争议的先保留书面依据。" % f["unit_said"]))
    else:
        out.append(("单位如何处理", "通过", "单位处理方式明确，无明显争议。"))
    return out


# ------------------------------------------------------------------ 五 证据
def has_content(s):
    for part in str(s or "").split("|"):
        if filled(part):
            return True
    return False


def checks_evidence(f):
    out = []
    got = (f["evidence_owned"] or "") + "|" + (f["evidence_desc"] or "")
    if not has_content(got):
        out.append(("证据总览", "待补正",
                    "已有证据既没勾选也没写清单。"
                    "**撤销申请的关键是「证明不是本车驾驶人」或「事实认定有误」**，"
                    "只留罚款照片没有用。"))
        return out
    for label, keys in EVIDENCE:
        hit = [k for k in keys if k in got]
        if hit:
            out.append((label, "通过",
                        "已具备：%s。**原件留存、复印件提交**。" % "、".join(hit)))
        else:
            out.append((label, "有风险", "尚无%s材料，这类缺口会让申请被驳回。" % label))
    return out


EVID_FIX = {
    "违法信息与决定书": "在 12123 导出或到窗口打印违法决定书，含扣分与罚款金额",
    "本人身份与车辆信息": "准备身份证、驾驶证、行驶证原件与复印件",
    "车辆转让或过户证明": "已过户的提供交强险变更记录、过户单",
    "非本人操作的证明": "车库监控、车位照片、行车记录仪、借用协议、报案记录",
    "客观情况异常的证明": "现场拍摄标志、标线、信号灯、摄像头状态，带时间信息",
    "缴纳与处理凭证": "保存缴费凭证与处理回执，证明已配合处理",
    "申诉与沟通记录": "保存复议/复核申请、回执、答复、工单号、通话录音",
}


def evidence_gap(f):
    got = (f["evidence_owned"] or "") + "|" + (f["evidence_desc"] or "")
    gaps = []
    if has_content(got):
        for label, keys in EVIDENCE:
            if not any(k in got for k in keys):
                gaps.append(label)
    else:
        gaps = [x[0] for x in EVIDENCE]
    if not any(k in got for k in ["违法记录", "决定书", "处罚", "12123"]):
        gaps.append("违法信息与决定书")
    if hit_any(f["driver_who"], ["非本人", "被盗", "被借", "套牌"]) is True and \
            not any(k in got for k in ["监控", "照片", "行车记录仪", "不在场", "被借", "被盗"]):
        gaps.append("非本人操作的证明")
    seen = set()
    res = []
    for g in gaps:
        if g not in seen:
            seen.add(g)
            res.append(g)
    return res


# ------------------------------------------------------------------ 路径与待办
def path_steps(f):
    return [(k, v) for k, v in PATHS]


def todo_list(f, results):
    todos = []
    for _t, rows in results:
        for name, state, _msg in rows:
            if state in ("不通过", "有风险", "待补正"):
                todos.append((name, state))
    extra = []
    if not yes(f["handled"]):
        extra.append(("先处理缴款避免加罚", "逾期按日加处罚款，还影响年检与保险"))
    if hit_any(f["driver_who"], ["非本人", "被盗", "被借", "套牌"]) is True:
        extra.append(("申请撤销违法记录", "带监控、车位照片、行车记录仪等非本人证据"))
    if hit_any(f["objective_issue"], ["遮挡", "不清", "故障", "异常"]) is True:
        extra.append(("现场拍照固定客观异常", "标志、标线、信号灯、摄像头状态带时间"))
    if hit_any(f["vehicle_type"], ["单位", "营运", "公司", "货车"]) is True:
        extra.append(("向单位索取书面处理说明", "驾驶人记分与单位处理责任要分开确认"))
    if not filled(f["score"]):
        extra.append(("在 12123 核对实际扣分与罚款", "以官方记录为准，逐条核对"))
    extra.append(("记住复议 7 日时限", "对罚款有异议的，收决定书 7 日内提出"))
    seen = set()
    res = []
    for n, s in todos + extra:
        if n not in seen:
            seen.add(n)
            res.append((n, s))
    return res


# ------------------------------------------------------------------ 报告
SECTIONS = [
    "二、违法类型与记分认定",
    "三、重大违法情形核查",
    "四、驾驶人归属与事实异议",
    "五、处理时限与缴费",
    "六、单位与营运车辆",
    "七、证据清单与缺口",
]


def render(f, results, steps, todos, today, gaps):
    L = []
    L.append("# 交通违法处理与扣分核查报告")
    L.append("")
    L.append("- 核查日期：%s" % today.isoformat())
    L.append("- 车辆：%s" % (f["plate"] or "未填"))
    L.append("- 违法类型：%s" % (f["kind"] or "未填"))
    L.append("- 申报扣分：%s" % (f["score"] or "未填"))
    L.append("")
    bad = [r for _t, rows in results for r in rows if r[1] == "不通过"]
    risk = [r for _t, rows in results for r in rows if r[1] == "有风险"]
    todo = [r for _t, rows in results for r in rows if r[1] == "待补正"]
    L.append("## 一、结论摘要")
    L.append("")
    if bad:
        L.append("**判定：存在重大违法情形或关键逾期项，必须优先处理。**"
                 "涉及醉驾、事故、无证的，**先咨询律师，不要自行处理**。")
    elif risk:
        L.append("**判定：违法事实已确认，但有可争取的撤销或从轻空间。**"
                 "**注意 7 日复议时限**，并按第十段补齐证据。")
    else:
        L.append("**判定：采集表关键项未填，暂时给不出确定结论；**"
                 "请把违法类型、扣分、驾驶人归属与处理状态填完再重跑。"
                 "**未填的一律不算通过。**")
    L.append("")
    L.append("| 项 | 数量 |")
    L.append("|---|---|")
    L.append("| 不通过 | %d |" % len(bad))
    L.append("| 有风险 | %d |" % len(risk))
    L.append("| 待补正 | %d |" % len(todo))
    L.append("")
    for name, _s, msg in bad[:5]:
        L.append("- **%s**：%s" % (name, msg.replace("**", "")))
    for name, _s, msg in risk[:5]:
        L.append("- %s：%s" % (name, msg.replace("**", "")))
    L.append("")

    for (title, rows), t in zip(results, SECTIONS):
        if not rows:
            L.append("## %s" % t)
            L.append("")
            L.append("暂无可核查项（未填不按通过处理）。")
            L.append("")
            continue
        L.append("## %s" % t)
        L.append("")
        L.append("| 核查项 | 判定 | 说明 |")
        L.append("|---|---|---|")
        for row in rows:
            if len(row) < 3:
                continue
            name, state, msg = row[0], row[1], row[2]
            if not isinstance(msg, str):
                msg = str(msg)
            L.append("| %s | %s | %s |" % (name, state, msg.replace("|", " ")))
        L.append("")

    L.append("## 八、处理与维权路径")
    L.append("")
    for step, txt in steps:
        L.append("- **%s**：%s" % (step, txt))
    L.append("")

    L.append("## 九、常见处理渠道")
    L.append("")
    L.append("| 渠道 | 适用场景 |")
    L.append("|---|---|")
    L.append("| 交管 12123 App | 查违法、缴罚款、提交撤销申请，**多数情形线上即可办** |")
    L.append("| 交警队或车管所窗口 | 需要现场核实、当事人到场、纸质材料受理 |")
    L.append("| 邮局代收 | 部分地区支持邮寄处理，适合不会线上操作的人 |")
    L.append("| 单位/雇主处理 | 营运与单位车辆，由单位集中处理 |")
    L.append("| 复议与复核 | 对罚款有异议走复议，对记分有异议走复核 |")
    L.append("")

    L.append("## 十、证据缺口速查")
    L.append("")
    if not gaps:
        L.append("当前填写的材料已较完整。")
    else:
        L.append("| 缺失类别 | 补法 |")
        L.append("|---|---|")
        for g in gaps[:12]:
            L.append("| %s | %s |" % (g, EVID_FIX.get(g, "按操作卡补齐")))
    L.append("")

    L.append("## 十一、待办补正动作")
    L.append("")
    if not todos:
        L.append("当前未发现必须补正的事项。")
    else:
        L.append("| 动作 | 状态 |")
        L.append("|---|---|")
        for n, s in todos:
            L.append("| %s | %s |" % (n, s))
    L.append("")

    L.append("## 边界与纪律")
    L.append("")
    L.append("- 依**通用规则**整理，**不替代律师意见**；"
             "记分与罚款标准、撤销条件、电动自行车与事故处理规定，"
             "**以交管部门与现行《道路交通安全违法行为记分管理办法》口径为准**。")
    L.append("- **本报告的推算分值仅供参考**，实际以 12123 与处罚决定书为准。")
    L.append("- 不预测交管部门是否批准撤销或复核。")
    L.append("- **未填的一律不算通过**，只按已填内容判断。")
    L.append("- 车牌号、驾驶证号等敏感信息**本地处理，不要外发**。")
    L.append("- 本结果依通用规则整理，不替代专业意见，"
             "最终以主管部门与司法机关认定为准。")
    return "\n".join(L) + "\n"


def to_json(f, results, todos, today, gaps):
    return {
        "核查日期": today.isoformat(),
        "结论": {
            "不通过": [r[0] for _t, rows in results for r in rows if r[1] == "不通过"],
            "有风险": [r[0] for _t, rows in results for r in rows if r[1] == "有风险"],
            "待补正": [r[0] for _t, rows in results for r in rows if r[1] == "待补正"],
        },
        "违法类型": classify(f),
        "推算扣分": calc_score(f, classify(f))[0],
        "证据缺口": gaps,
        "待办": [{"动作": n, "状态": s} for n, s in todos],
    }


def build_fields(kv):
    return {
        "plate": get_text(kv, ["车牌号", "车牌", "车辆号牌"]),
        "kind": get_text(kv, ["违法行为类型", "违法类型", "违法行为"]),
        "detail": get_text(kv, ["违法经过", "违法经过描述", "情况说明"]),
        "occur_date": get_text(kv, ["违法时间", "违法日期", "什么时候"]),
        "score": get_text(kv, ["扣分数", "记分", "扣分"]),
        "fine": get_text(kv, ["罚款金额", "罚款"]),
        "notice_date": get_text(kv, ["收到处罚决定的时间", "收到通知时间", "通知日期"]),
        "driver_who": get_text(kv, ["违法时驾驶人是谁", "驾驶人是谁", "开车的是谁"]),
        "objective_issue": get_text(kv, ["标志标线或设备是否异常", "客观情况是否异常",
                                "是否有客观问题", "标志是否被遮挡"]),
        "handled": get_text(kv, ["是否已处理缴款", "是否已缴罚款", "罚款是否已缴"]),
        "vehicle_type": get_text(kv, ["车辆性质", "车辆类型", "什么车"]),
        "unit_said": get_text(kv, ["单位如何处理", "单位或雇主怎么说", "单位要求"]),
        "evidence_owned": get_text(kv, ["已有材料勾选", "材料勾选", "证据勾选"]),
        "evidence_desc": get_text(kv, ["材料清单", "已有材料", "证据清单"]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--base", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    kv = build_kv(read_text(args.input))
    today = base_date(args.base)
    f = build_fields(kv)

    missing = []
    if not filled(f["kind"]):
        missing.append("违法行为类型")
    if not filled(f["score"]):
        missing.append("扣分数")
    if not filled(f["driver_who"]):
        missing.append("违法时驾驶人是谁")

    results = [
        ("违法类型与记分认定", checks_kind(f) + checks_score(f, classify(f))),
        ("重大违法情形核查", checks_major(f, classify(f))),
        ("驾驶人归属与事实异议", checks_owner(f) + checks_objective(f)),
        ("处理时限与缴费", checks_process(f, today)),
        ("单位与营运车辆", checks_unit(f)),
        ("证据清单与缺口", checks_evidence(f)),
    ]
    steps = path_steps(f)
    todos = todo_list(f, results)
    gaps = evidence_gap(f)

    if args.json:
        print(json.dumps(to_json(f, results, todos, today, gaps),
                         ensure_ascii=False, indent=2))
        return 0

    rep = render(f, results, steps, todos, today, gaps)
    if missing:
        rep += ("\n> 提示：关键信息缺失——%s，相关判断已按\"待补正\"处理，"
                "补齐后重跑可得到确定结论。\n" % "、".join(missing))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(rep)
        print("已写出 %s" % args.out)
    else:
        sys.stdout.write(rep)
    return 2 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
