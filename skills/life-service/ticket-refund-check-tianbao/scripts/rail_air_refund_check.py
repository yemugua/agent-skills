#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""火车票 / 机票退改签与手续费测算核查。

用法：
  python rail_air_refund_check.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python rail_air_refund_check.py 采集表.md --json
退出码：0 正常；2 关键信息缺失。
"""
import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta

UNFILLED_MARK = re.compile(r"[/／]")
DATE_RE = re.compile(r"(20\d{2})[-年\.](\d{1,2})[-月\.](\d{1,2})")

PLACEHOLDER_WORDS = ["待填", "请填", "例如", "示例", "如：", "（", "(", "有/无", "是/否",
                     "选填", "填写"]

# 铁路退票费阶梯（距票面发车时间，通用口径，以 12306 现行规则为准）
RAIL_TIERS = [
    (8 * 24, 0.00, "开车前 8 天以上（含 8 天）", "不收退票费"),
    (48, 0.05, "开车前 48 小时至 8 天", "按票面 5% 收取"),
    (24, 0.10, "开车前 24 小时至 48 小时", "按票面 10% 收取"),
    (0, 0.20, "开车前不足 24 小时", "按票面 20% 收取"),
]
RAIL_AFTER_DEPART = "开车后（含已发车）不退票，只能按规定改签"

# 民航常见退票费阶梯（国内客票，以承运人公布规则为准）
AIR_TIERS = [
    (7 * 24, 0.00, "起飞前 7 天以上（含 7 天）", "不收退票费"),
    (48, 0.10, "起飞前 48 小时至 7 天", "按票面 10% 收取"),
    (24, 0.20, "起飞前 24 小时至 48 小时", "按票面 20% 收取"),
    (0, 0.30, "起飞前不足 24 小时", "按票面 30% 收取"),
]

# 承运方 / 不可归责于旅客的原因——决定能不能全额退
CARRIER_REASONS = [
    ("航班取消", ["取消", "停飞", "取消航班", "计划取消"]),
    ("航班延误", ["延误", "晚点", "延误导致"]),
    ("天气或流控", ["天气", "台风", "暴雨", "流控", "雷雨", "冰雪"]),
    ("机型或座位调整", ["机型", "座位", "舱位调整", "更换飞机", "机型变更"]),
    ("承运人合并航班", ["合并", "代码共享", "转机"]),
    ("票务差错", ["出票错误", "票面错误", "系统出票", "重复出票"]),
    ("不可抗力", ["不可抗力", "政策原因", "监管要求"]),
]

# 旅客个人原因
PERSONAL_REASONS = [
    ("生病或住院", ["生病", "病", "住院", "发烧", "急诊"]),
    ("直系亲属丧事", ["丧", "直系", "去世", "葬礼"]),
    ("工作单位证明", ["单位", "公司", "工作", "出差"]),
    ("学校或学业安排", ["学校", "考试", "学业", "学校统一"]),
    ("行程冲突", ["行程", "冲突", "撞期", "已有安排", "重复预订"]),
    ("买错票或不想去", ["买错", "不想去", "不去了", "误买"]),
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
    if n in ("有", "是", "已经", "已", "已完成", "已做", "可以", "能", "已取消", "已延误"):
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


def hit_any(v, words):
    s = norm(v)
    if not filled(s):
        return None
    for w in words:
        if norm(w) in s:
            return True
    return False


def mode_kind(v):
    """返回 (中文模式, code)，code in (rail/air/other/None)"""
    s = norm(v)
    if not filled(s):
        return ("未填", None)
    for k in ("铁路", "火车", "高铁", "动车", "12306", "列车", "车票"):
        if norm(k) in s:
            return ("铁路", "rail")
    for k in ("民航", "飞机", "航班", "机票", "航空", "值机", "登机"):
        if norm(k) in s:
            return ("民航", "air")
    for k in ("客运", "大巴", "长途", "拼车", "顺风车", "轮渡"):
        if norm(k) in s:
            return ("其他客运", "other")
    return ("其他", "other")


def hours_to_dep(f):
    """起飞/开车前的剩余小时数；已过返回负数。"""
    d = parse_date(f["dep_date"])
    if not d:
        return None
    dep = datetime(d.year, d.month, d.day, 0, 0)
    now = datetime(f["today"].year, f["today"].month, f["today"].day, 0, 0)
    return (dep - now).total_seconds() / 3600.0


# ------------------------------------------------------------------ 一 票种与可退性
def checks_type(f):
    out = []
    mname, code = mode_kind(f["mode"])
    if code is None:
        out.append(("票种定性", "待补正",
                    "运输方式未填（铁路/民航/其他客运）。**票种决定退改规则，"
                    "铁路和民航的退票阶梯完全不同**，请先明确。"))
        return out
    out.append(("票种定性", "通过", "定性为**%s**。%s"
                % (mname,
                   {"rail": "铁路票按 12306 的开车时间阶梯收退票费。",
                    "air": "民航票按承运人公布的票价档与起飞时间阶梯收退票费。",
                    "other": "长途客运与网约/拼车按承运方规则，差异较大，"
                             "建议先确认承运方是否有明码标价的退改规则。"}.get(code, ""))))

    h = hours_to_dep(f)
    if h is None:
        out.append(("距发车或起飞时间", "待补正", "未填出发/起飞日期，无法判断处在哪个退费档位。"))
    elif h < 0:
        out.append(("距发车或起飞时间", "不通过",
                    "出发/起飞时间已过（%s）。**已开车/已起飞后不再受理退票**，"
                    "铁路可按规定改签至当日其他车次，民航一般只能按承运人规则办理。" % f["dep_date"]))
    elif h <= 24:
        out.append(("距发车或起飞时间", "有风险",
                    "距出发仅 %d 小时，处在**最贵的退费档**（铁路 20%%、民航 30%%），"
                    "且临近时刻退改通道拥堵，建议优先试改签而不是退票。" % h))
    elif h <= 48:
        out.append(("距发车或起飞时间", "有风险",
                    "距出发 %d 小时，处于第二档退费水平（铁路 10%%、民航 20%%）。" % h))
    elif h < 8 * 24:
        out.append(("距发车或起飞时间", "有风险",
                    "距出发 %d 小时，**已进入收费档**（铁路 5%%、民航 10%%），"
                    "越临近越贵，能改签就别退票。" % h))
    else:
        out.append(("距发车或起飞时间", "通过",
                    "距出发 %d 小时，**尚在免退票费档位内**（铁路 8 天以上、民航 7 天以上），"
                    "此时退票不收手续费。" % h))

    chk = f["checked"]
    if unknown(chk):
        out.append(("是否已检票或值机", "待补正",
                    "是否已检票/值机未填。**已检票的票通常不予退票**，"
                    "未取票的退票相对简单，这项直接影响能不能退。"))
    elif yes(chk):
        out.append(("是否已检票或值机", "不通过",
                    "**已检票或已值机**，铁路与民航一般都不再受理退票；"
                    "铁路当日可在车站按规定办理改签，民航需看承运人规则。"))
    else:
        out.append(("是否已检票或值机", "通过", "未检票/未值机，具备退票条件。"))

    taken = f["ticket_taken"]
    if unknown(taken):
        out.append(("是否已取票或取报销凭证", "待补正", "是否已取纸质票未填，纸质票退回会影响退票流程。"))
    elif yes(taken):
        out.append(("是否已取票或取报销凭证", "有风险",
                    "已取纸质票或已取报销凭证，**需一并寄回或到站办理**；"
                    "电子客票需按要求留存票根，否则可能无法退。"))
    else:
        out.append(("是否已取票或取报销凭证", "通过", "未取票，无票据物理交接问题。"))
    return out


# ------------------------------------------------------------------ 二 退改原因定性
def checks_reason(f):
    out = []
    r = f["reason"]
    if not filled(r):
        out.append(("退改原因定性", "待补正",
                    "退改原因未填。**这是决定能不能全额退的核心**："
                    "承运方或不可归责于你的原因，铁路/民航应全额退款或无需付费；"
                    "个人原因则按阶梯收退票费。"))
        return out
    c = hit_any(r, sum([w for _l, w in CARRIER_REASONS], []))
    p = hit_any(r, sum([w for _l, w in PERSONAL_REASONS], []))
    if c is True and p is False:
        matched = [l for l, w in CARRIER_REASONS if any(norm(x) in norm(r) for x in w)]
        out.append(("退改原因定性", "通过",
                    "属于**不可归责于旅客**的原因（%s）：%s。"
                    "**这类情形应全额退款或不由旅客承担退票费**，"
                    "铁路因不可抗力可全额退，民航因承运人原因取消应全额退。"
                    % ("、".join(matched), r)))
    elif p is True and c is False:
        matched = [l for l, w in PERSONAL_REASONS if any(norm(x) in norm(r) for x in w)]
        out.append(("退改原因定性", "有风险",
                    "属于**旅客个人原因**（%s）：%s。"
                    "按阶梯收退票费；**能提供证明的疾病、直系亲属丧事、单位或学校证明，"
                    "有可能按非旅客原因或减免处理**，值得准备材料。" % ("、".join(matched), r)))
    elif c is True and p is True:
        out.append(("退改原因定性", "有风险",
                    "原因描述里同时出现承运方与个人原因要素：%s。"
                    "**以实际造成退改的直接原因为准**，沟通时务必说清"
                    "「是谁的原因导致我无法成行」。" % r))
    else:
        out.append(("退改原因定性", "有风险",
                    "原因不属于常见分类：%s。"
                    "建议直接问承运方**「这属于非旅客原因吗」**并要书面答复。" % r))
    return out


# ------------------------------------------------------------------ 三 手续费测算
def calc_refund(f):
    res = {"模式": "未填", "适用": False, "档位": None, "费率": None,
           "手续费": None, "可退": None, "说明": "", "算式": []}
    mname, code = mode_kind(f["mode"])
    res["模式"] = mname
    if code not in ("rail", "air"):
        res["说明"] = "票种不是铁路或民航，本技能不测算退票手续费，请按承运方公布规则核对。"
        return res
    res["适用"] = True
    face = parse_num(f["face"])
    paid = parse_num(f["paid"])
    base = face if face else paid
    if not base or base <= 0:
        res["说明"] = "票面金额或实付金额未填，无法测算退票手续费。"
        return res

    h = hours_to_dep(f)
    if h is None:
        res["说明"] = "未填出发/起飞日期，无法定位退费档位。"
        return res
    if h < 0:
        res["说明"] = "已开车/已起飞，不受理退票。%s" % (
            RAIL_AFTER_DEPART if code == "rail" else "民航按承运人规则办理，通常不予退票。")
        return res

    tiers = RAIL_TIERS if code == "rail" else AIR_TIERS
    picked = None
    for th, rate, label, desc in tiers:
        if h >= th:
            picked = (th, rate, label, desc)
            break
    if picked is None:
        picked = (0, tiers[-1][1], tiers[-1][2], tiers[-1][3])
    th, rate, label, desc = picked
    fee = round(base * rate, 2)
    res["档位"] = label
    res["费率"] = rate
    res["手续费"] = fee
    res["可退"] = round(base - fee, 2)
    res["算式"] = [
        "票面/实付金额 %s − 退票手续费 %s（%s × %s%%）= 可退 %s"
        % (money(base), money(fee), money(base), fmt_num(rate * 100), money(res["可退"])),
        "档位判定：距出发 %s 小时，落在「%s」，%s" % (fmt_num(h), label, desc),
    ]
    if rate == 0:
        res["说明"] = "距出发 %s 小时，处于**免退票费档位**，可全额退。" % fmt_num(h)
    else:
        res["说明"] = ("距出发 %s 小时，落在**%s**（%s）。"
                       "若能主张为非旅客原因，理论上应不收或减收退票费。"
                       % (fmt_num(h), label, desc))

    if f["non_traveller_claim"]:
        res["说明"] += " 你已主张为非旅客原因，**按对方答复结果为准**；" \
                       "对方仍按个人原因收费的，可走投诉与申诉阶梯。"
    if paid and face and abs(paid - face) > 0.01:
        res["算式"].append("实付 %s 与票面 %s 不一致（可能有保险或加价），"
                           "手续费一般以票面金额为基数，请以承运方实际计算为准。"
                           % (money(paid), money(face)))
    return res


def checks_amount(f, calc):
    out = []
    if not calc["适用"]:
        out.append(("退票手续费测算", "待补正", calc["说明"]))
        return out
    if calc["可退"] is None:
        out.append(("退票手续费测算", "待补正", calc["说明"]))
        return out
    if calc["费率"] == 0:
        out.append(("退票手续费", "通过",
                    "%s，可退 **%s**（全额）。" % (calc["说明"], money(calc["可退"]))))
    else:
        out.append(("退票手续费", "有风险",
                    "%s，退票手续费 **%s**，可退 **%s**。"
                    "**先试改签往往比退票划算**（同价或差价改签通常不收手续费）。"
                    % (calc["说明"], money(calc["手续费"]), money(calc["可退"]))))
    out.append(("可退金额", "通过" if calc["费率"] == 0 else "有风险",
                "算式：%s" % "；".join(calc["算式"])))

    if yes(f["insurance"]):
        out.append(("保险与附加费", "有风险",
                    "票面/实付金额里含保险或服务费。**退票时这部分通常不单独退**，"
                    "需单独向承运方或保险公司主张，测算口径也因此不同。"))
    elif no(f["insurance"]):
        out.append(("保险与附加费", "通过", "未涉及保险或附加服务费。"))
    else:
        out.append(("保险与附加费", "待补正", "是否含保险或附加费未填，这会影响可退金额口径。"))

    if unknown(f["rebooked"]):
        out.append(("是否已改签过", "待补正", "是否已改签或已申请改签未填，这影响还有哪些选项。"))
    elif yes(f["rebooked"]):
        out.append(("是否已改签过", "有风险",
                    "已改签过。**改签后的票按新票的退改规则计算**，"
                    "且部分票种改签次数有限制，务必以新票面与新时间重新算一遍。"))
    else:
        out.append(("是否已改签过", "通过", "未改签，仍在原票规则下计算。"))
    return out


# ------------------------------------------------------------------ 四 办理与到账
def checks_process(f):
    out = []
    if unknown(f["applied"]):
        out.append(("是否已提交退改申请", "待补正", "是否已提交退票或改签申请未填。"))
    elif yes(f["applied"]):
        out.append(("是否已提交退改申请", "通过", "已提交，**留存工单号或受理编号**。"))
    else:
        out.append(("是否已提交退改申请", "不通过",
                    "**尚未提交退改申请**，一切测算都只是预估。"
                    "自助渠道（12306/航司 App）先试，柜台办理需带身份证与购票凭证。"))

    if unknown(f["ticket_no"]):
        out.append(("是否取得工单号或受理编号", "待补正", "工单号缺失会让催办与投诉无从下手。"))
    elif yes(f["ticket_no"]):
        out.append(("是否取得工单号或受理编号", "通过", "已有工单号，催办与投诉都用得上。"))
    else:
        out.append(("是否取得工单号或受理编号", "不通过",
                    "没有工单号。**口头承诺不算证据**，每次沟通后立刻记下工单号与答复内容。"))

    if unknown(f["refunded"]):
        out.append(("票款是否已到账", "待补正", "是否已到账未填。"))
    elif yes(f["refunded"]):
        out.append(("票款是否已到账", "通过", "票款已到账，本项主张完成。"))
    else:
        out.append(("票款是否已到账", "有风险",
                    "**未到账**。铁路与民航的退款一般原路退回，"
                    "常见到账周期为 3~7 个工作日（保险与部分渠道会顺延）；"
                    "超期未到账就用工单号催办，并留存扣款记录。"))
    return out


# ------------------------------------------------------------------ 五 投诉阶梯
def checks_complaint(f):
    out = []
    channels = [
        ("承运方自助渠道（12306/航司 App）", f["self"],
         "先走自助：12306「行程」里可退改，航司 App/小程序同样。**自助成功就不必打人工**。"),
        ("承运方人工客服（12306/航司客服热线）", f["csr"],
         "人工客服可确认具体档位与材料要求，**要工单号**。"),
        ("12345 政务热线", f["hotline"],
         "涉及承运方设置障碍、拖延处理的，可向 12345 反映由主管部门转办。"),
        ("12315 消费投诉", f["market"],
         "作为消费服务争议向 12315 投诉，可与承运方投诉并行。"),
        ("民航/铁路主管部门渠道", f["gov"],
         "铁路可向 12306 客服中心与国铁集团渠道反映；民航可向民航主管部门渠道反映，"
         "**以当地主管部门公布的渠道为准**。"),
    ]
    for label, v, body in channels:
        if yes(v):
            out.append((label, "通过", body + " —— 已使用，建议留存受理编号与答复内容。"))
        elif no(v):
            out.append((label, "有风险", body + " —— 尚未使用，顺序建议从前往后。"))
        else:
            out.append((label, "待补正", "是否走过%s未填。" % label))
    return out


# ------------------------------------------------------------------ 六 证据
EVIDENCE = [
    ("购票凭证", ["订单号", "购票记录", "行程单", "电子客票", "支付记录", "出票记录"]),
    ("退改申请记录", ["退票申请", "改签申请", "工单", "受理编号", "申请记录"]),
    ("退改费用凭证", ["手续费", "退款金额", "扣费记录", "退款明细"]),
    ("承运方答复", ["答复", "客服回复", "告知", "拒绝理由", "沟通记录"]),
    ("原因证明", ["医院", "病历", "诊断", "死亡证明", "单位证明", "学校证明", "请假"]),
    ("不可抗力证明", ["取消公告", "航班取消", "延误通知", "天气预警", "官方公告"]),
]


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
                    "已有证据既没勾选也没写清单。**退改争议靠材料说话**："
                    "订单号、申请记录、工单号、扣费凭证，缺一样就催不动。请逐项对照补齐。"))
        return out
    for label, keys in EVIDENCE:
        hit = [k for k in keys if k in got]
        if hit:
            out.append((label + "证据", "通过",
                        "已具备：%s。截图要**带时间与订单号**，按时间顺序整理成册。" % "、".join(hit)))
        else:
            out.append((label + "证据", "有风险", "尚无%s证据，这类缺口会削弱主张，请尽快补齐。" % label))
    return out


def evidence_gap(f):
    got = (f["evidence_owned"] or "") + "|" + (f["evidence_desc"] or "")
    gaps = []
    if has_content(got):
        for label, keys in EVIDENCE:
            if not any(k in got for k in keys):
                gaps.append(label)
    else:
        gaps = [x[0] for x in EVIDENCE]
    if filled(f["reason"]):
        c = hit_any(f["reason"], sum([w for _l, w in CARRIER_REASONS], []))
        p = hit_any(f["reason"], sum([w for _l, w in PERSONAL_REASONS], []))
        if c is True and p is not True:
            gaps.append("不可抗力证明")
        if p is True:
            gaps.append("原因证明")
    if not yes(f["ticket_no"]):
        gaps.append("退改申请记录")
    seen = set()
    res = []
    for g in gaps:
        if g not in seen:
            seen.add(g)
            res.append(g)
    return res


EVID_FIX = {
    "购票凭证": "在 App 或邮箱里导出行程单/订单 PDF，截图含订单号",
    "退改申请记录": "保存申请页面截图、工单号与受理编号",
    "退改费用凭证": "保存扣费短信、账单明细与退款流水",
    "承运方答复": "保存客服答复截图或通话录音（合法留存，仅用于本人主张）",
    "原因证明": "就医的病历与诊断证明、单位或学校开具的证明",
    "不可抗力证明": "保存官方取消/延误公告截图与天气预警",
    "承运方答复证据": "要求书面答复并保存送达记录",
}


# ------------------------------------------------------------------ 路径
def path_steps(f):
    mname, code = mode_kind(f["mode"])
    out = []
    if code == "rail":
        out.append(("第 1 步（先算账）",
                    "打开 12306「订单」确认票号、开车时间与票面价；"
                    "**距开车 8 天以上退票不收手续费**，不足 24 小时要收 20%，"
                    "这个差距往往比折腾一趟更值得算清楚。"))
        out.append(("第 2 步（优先试改签）",
                    "12306 里的「改签」在开车前通常不收手续费，**同价或差价很少比退票再买划算**。"
                    "预售期内可改签，限次以系统提示为准；开车后可改签至当日其他车次。"))
        out.append(("第 3 步（要材料）",
                    "个人原因退票只退票面价扣手续费；"
                    "**因疾病、直系亲属丧事、单位或学校原因**，可尝试提交证明材料按非旅客原因办理。"))
        out.append(("第 4 步（留痕）",
                    "全程保存申请截图、工单号、扣费与退款流水；"
                    "退票款一般**原路退回，3~7 个工作日到账**。"))
        out.append(("第 5 步（争议升级）",
                    "12306 客服 → 12345 政务热线 → 12315 消费投诉 → 铁路主管部门渠道，"
                    "每次都附工单号与书面答复。"))
    elif code == "air":
        out.append(("第 1 步（看状态）",
                    "先查航班状态：取消或延误属于承运人原因，**应全额退票或免费改签**；"
                    "自主改期、行程冲突、生病等属个人原因，按票价档与起飞时间收退票费。"))
        out.append(("第 2 步（承运人原因先找承运人）",
                    "航班取消/延误请**直接联系承运人**，主张全额退款或免费改签到其他航班，"
                    "并保留官方公告与沟通记录。"))
        out.append(("第 3 步（个人原因算清账）",
                    "起飞前 7 天以上通常不收退票费；7 天内按 10%/20%/30% 阶梯，"
                    "**临近起飞不要退票，改签通常更划算**。"))
        out.append(("第 4 步（留痕）",
                    "保存支付记录、退改申请、工单号、退款流水；"
                    "退款一般**原路退回，到账周期 3~7 个工作日**。"))
        out.append(("第 5 步（争议升级）",
                    "航司客服 → 12315 消费投诉 → 民航主管部门渠道，附工单号与书面答复。"))
    else:
        out.append(("第 1 步（先找规则）",
                    "先确认承运方**是否有明码标价的退改规则**（网站、协议、客服告知），"
                    "本技能只测算铁路与民航口径。"))
        out.append(("第 2 步（走投诉阶梯）",
                    "承运方客服 → 12345 → 12315，附工单号与书面答复。"))
    out.append(("第 6 步（极端情况）",
                "承运方拒不受理或明显不合理的，可向人民法院提起诉讼，"
                "请求继续履行或赔偿损失；**是否值得走请先咨询律师**。"))
    return out


def todo_list(f, results, calc):
    todos = []
    for _t, rows in results:
        for name, state, _msg in rows:
            if state in ("不通过", "有风险", "待补正"):
                todos.append((name, state))
    extra = []
    if not yes(f["applied"]):
        extra.append(("提交退改申请", "先在自助渠道试，柜台需带身份证与购票凭证"))
    if not yes(f["ticket_no"]):
        extra.append(("取工单号", "每次沟通后立刻记下工单号与答复内容"))
    if calc.get("费率"):
        extra.append(("先比改签", "退票要收 %s%% 手续费，距出发越近越贵；"
                                   "同价或差价改签通常不收手续费，先比再决定"
                      % fmt_num((calc.get("费率") or 0) * 100)))
    if f["insurance"]:
        extra.append(("单独主张保险", "保险与附加费一般不随票退，需单独向承运方或保险公司主张"))
    if not yes(f["refunded"]):
        extra.append(("盯退款到账", "一般 3~7 个工作日原路退回，超期用工单号催办"))
    if unknown(f["reason"]):
        extra.append(("写清退改原因", "是承运方原因还是个人原因，直接决定能不能全额退"))
    extra.append(("导出行程单", "App 或邮箱导出行程单/订单 PDF，含订单号"))
    seen = set()
    res = []
    for n, s in todos + extra:
        if n in seen:
            continue
        seen.add(n)
        res.append((n, s))
    return res


# ------------------------------------------------------------------ 报告
SECTIONS = [
    "二、票种与可退性定性",
    "三、退改原因定性",
    "四、退票手续费测算",
    "五、办理流程与到账",
    "六、投诉与申诉阶梯",
    "七、证据清单与缺口",
]


def render(f, results, calc, steps, todos, today, gaps):
    L = []
    L.append("# 交通票务退改签核查报告")
    L.append("")
    L.append("- 核查日期：%s" % today.isoformat())
    L.append("- 票种：%s" % (mode_kind(f["mode"])[0]))
    L.append("- 车次/航班：%s" % (f["trip_no"] or "未填"))
    L.append("- 出发/起飞时间：%s" % (f["dep_date"] or "未填"))
    L.append("")
    bad = [r for _t, rows in results for r in rows if r[1] == "不通过"]
    risk = [r for _t, rows in results for r in rows if r[1] == "有风险"]
    todo = [r for _t, rows in results for r in rows if r[1] == "待补正"]
    L.append("## 一、结论摘要")
    L.append("")
    if calc.get("可退") is not None and calc.get("费率") == 0 and not bad:
        L.append("**判定：处于免退票费档位，可退 %s（全额），按第八段路径提交即可。**"
                 % money(calc["可退"]))
    elif calc.get("可退") is not None:
        L.append("**判定：可退金额约 %s，其中退票手续费 %s；"
                 "**若距出发较近，改签通常比退票划算**。"
                 % (money(calc["可退"]), money(calc["手续费"])))
    elif bad:
        L.append("**判定：存在明确不可退情形或未完成的关键动作，请按第八段路径处理。**")
    elif todo:
        L.append("**判定：采集表关键项未填，暂时给不出确定金额；"
                 "请把票种、出发时间、票面金额、退改原因填完再重跑。**"
                 "**未填的一律不算通过。**")
    else:
        L.append("**判定：未发现明显阻碍，建议按第八段路径一次办成。**")
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

    L.append("## 八、退改路径排序")
    L.append("")
    for step, txt in steps:
        L.append("- **%s**：%s" % (step, txt))
    L.append("")

    L.append("## 九、证据缺口速查")
    L.append("")
    if not gaps:
        L.append("当前填写的证据已较完整。")
    else:
        L.append("| 缺失类别 | 补法 |")
        L.append("|---|---|")
        for g in gaps[:12]:
            L.append("| %s | %s |" % (g, EVID_FIX.get(g, "按第八段操作卡补齐")))
    L.append("")

    L.append("## 十、待办补正动作")
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
             "铁路退改规则以 **12306 现行规定**为准，民航退改规则以**承运人公布的现行规则**为准。")
    L.append("- 本报告金额为按通用阶梯测算的**预估**，最终以承运方实际计算与答复为准。")
    L.append("- 不预测承运方、主管部门与法院的处理结果。")
    L.append("- **未填的一律不算通过**，只按已填内容判断。")
    L.append("- 本结果依通用规则整理，不替代专业意见，最终以承运人、主管部门与司法机关认定为准。")
    return "\n".join(L) + "\n"


def to_json(f, results, todos, today, gaps, calc):
    return {
        "核查日期": today.isoformat(),
        "票种": mode_kind(f["mode"])[0],
        "结论": {
            "不通过": [r[0] for _t, rows in results for r in rows if r[1] == "不通过"],
            "有风险": [r[0] for _t, rows in results for r in rows if r[1] == "有风险"],
            "待补正": [r[0] for _t, rows in results for r in rows if r[1] == "待补正"],
        },
        "退费测算": {
            "档位": calc["档位"],
            "费率": calc["费率"],
            "手续费": calc["手续费"],
            "可退金额": calc["可退"],
            "说明": calc["说明"],
        },
        "证据缺口": gaps,
        "待办": [{"动作": n, "状态": s} for n, s in todos],
    }


def build_fields(kv):
    return {
        "mode": get_text(kv, ["运输方式", "票种", "交通方式", "出行方式"]),
        "trip_no": get_text(kv, ["车次或航班号", "车次", "航班号", "班次"]),
        "dep_date": get_text(kv, ["出发或起飞日期", "出发日期", "起飞日期", "乘车日期", "行程日期"]),
        "face": get_text(kv, ["票面金额", "票价", "票面价"]),
        "paid": get_text(kv, ["实付金额", "支付金额", "实际付款金额"]),
        "insurance": get_text(kv, ["是否含保险或附加费", "是否含保险", "保险或附加费"]),
        "checked": get_text(kv, ["是否已检票或值机", "是否已检票", "是否已值机"]),
        "ticket_taken": get_text(kv, ["是否已取票或取报销凭证", "是否已取票", "是否取报销凭证"]),
        "reason": get_text(kv, ["退改原因", "退票原因", "无法成行的原因", "原因说明"]),
        "non_traveller_claim": yes(get_text(kv, ["是否主张非旅客原因", "是否主张非本人原因"])),
        "rebooked": get_text(kv, ["是否已改签过", "是否已改签", "改签情况"]),
        "applied": get_text(kv, ["是否已提交退改申请", "是否已申请退票", "是否已提交改签申请"]),
        "ticket_no": get_text(kv, ["是否取得工单号或受理编号", "工单号", "受理编号"]),
        "refunded": get_text(kv, ["票款是否已到账", "是否已到账", "退款到账"]),
        "self": get_text(kv, ["是否走过承运方自助渠道", "是否自助提交", "自助渠道"]),
        "csr": get_text(kv, ["是否走过承运方人工客服", "是否联系客服", "人工客服"]),
        "hotline": get_text(kv, ["是否已向12345反映", "是否12345", "12345"]),
        "market": get_text(kv, ["是否已向12315投诉", "是否12315", "12315"]),
        "gov": get_text(kv, ["是否已向主管部门渠道反映", "是否向主管部门反映", "主管部门渠道"]),
        "evidence_owned": get_text(kv, ["已有证据勾选", "证据勾选"]),
        "evidence_desc": get_text(kv, ["证据清单", "已有证据", "材料清单"]),
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
    f["today"] = today

    missing = []
    if not filled(f["mode"]):
        missing.append("运输方式")
    if not filled(f["dep_date"]):
        missing.append("出发或起飞日期")
    if not (parse_num(f["face"]) or parse_num(f["paid"])):
        missing.append("票面金额或实付金额")

    calc = calc_refund(f)
    results = [
        ("票种与可退性定性", checks_type(f)),
        ("退改原因定性", checks_reason(f)),
        ("退票手续费测算", checks_amount(f, calc)),
        ("办理流程与到账", checks_process(f)),
        ("投诉与申诉阶梯", checks_complaint(f)),
        ("证据清单与缺口", checks_evidence(f)),
    ]
    steps = path_steps(f)
    todos = todo_list(f, results, calc)
    gaps = evidence_gap(f)

    if args.json:
        print(json.dumps(to_json(f, results, todos, today, gaps, calc),
                         ensure_ascii=False, indent=2))
        return 0

    rep = render(f, results, calc, steps, todos, today, gaps)
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
