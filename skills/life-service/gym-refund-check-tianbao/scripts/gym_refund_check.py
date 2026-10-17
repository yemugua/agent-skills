#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""健身房退卡退费核算。

用法：
  python gym_refund_check.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python gym_refund_check.py 采集表.md --json
退出码：0 正常；2 关键信息缺失（给提示串，不崩）。
"""
import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta

UNFILLED_MARK = re.compile(r"[/／]")
DATE_RE = re.compile(r"(20\d{2})[-年\.](\d{1,2})[-月\.](\d{1,2})")

PLACEHOLDER_WORDS = ["待填", "请填", "例如", "示例", "如："]


# ------------------------------------------------------------------ 解析
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
    """解析 markdown 表格行与 '字段：值' 行，保留表头。"""
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
            parts = re.split(r"[:：]", line, maxsplit=1)
            if len(parts) == 2:
                k, v = parts[0].strip(), parts[1].strip()
                if k and k not in kv:
                    kv[k] = v
    return kv


def get_text(kv, aliases):
    """最长别名优先匹配。"""
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
    v = (v or "").strip()
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
    return n in ("有", "是", "已经", "已", "已完成", "true", "yes")


def no(v):
    n = norm(v)
    return n in ("无", "否", "没有", "未", "未做", "false", "no")


def unknown(v):
    n = norm(v)
    return (not filled(v)) or n in ("不清楚", "不确定", "不知道", "待确认", "未知")


def parse_num(s):
    if not s:
        return None
    s = str(s).replace(",", "").replace("，", "").replace("¥", "").replace("元", "")
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def pct_num(s):
    """百分比/倍数：'20%' -> 20.0；'千分之' 不 special；返回百分数数值。"""
    if not s:
        return None
    t = str(s).replace("，", "").replace("%", "").replace("％", "").replace("个", "")
    if "%" not in str(s) and "％" not in str(s):
        m = re.search(r"(\d+(?:\.\d+)?)\s*倍", str(s))
        if m:
            try:
                return float(m.group(1)) * 100
            except Exception:
                return None
    m = re.search(r"\d+(?:\.\d+)?", t)
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
    return "¥" + fmt_num(x)


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


# ------------------------------------------------------------------ 情形识别
SCENARIOS = [
    ("s1", "门店关闭/停业跑路", ["关门", "关闭", "跑路", "停业", "歇业", "已注销", "人去楼空", "锁门"]),
    ("s2", "迁址至明显不便处", ["迁址", "搬迁", "搬走", "换址", "地址变更", "搬到很远", "关门换址"]),
    ("s3", "门店转让后新主体不承接", ["转让", "出兑", "易主", "不承接", "新老板", "不认旧卡"]),
    ("s4", "教练与承诺不符/课程无法预约", ["教练", "承诺", "约不上", "预约不上", "约不到", "停课",
                                      "缩水", "器材", "设施", "课程减少", "私教换了"]),
    ("s5", "消费者健康原因", ["健康", "伤病", "医院", "医嘱", "怀孕", "手术", "康复"]),
    ("s0", "单纯不想用了/无具体事由", ["不想用", "没时间", "搬家远", "其他", "无"]),
]


def detect_scenario(text_field):
    s = norm(text_field)
    if not s:
        return ("未填", None)
    for code, name, kws in SCENARIOS:
        for kw in kws:
            if kw in s:
                return (name, code)
    for code, name, kws in SCENARIOS:
        for kw in kws:
            if kw in str(text_field):
                return (name, code)
    return ("未识别", None)


SHOP_CLOSED = ("s1",)
TRIGGER_FULL = ("s1", "s2", "s3")

# ------------------------------------------------------------------ 格式条款
FORM_CLAUSES = [
    ("概不退费", "概不退费", "排除消费者主要权利、免除经营者责任，该格式条款无效"),
    ("最终解释权归本店", "最终解释权", "排除消费者权利，该格式条款无效"),
    ("余额过期作废", "余额过期作废", "加重消费者责任、免除经营者责任，该格式条款无效"),
    ("不得转让/高额转卡费", "不得转让", "加重消费者责任，明显不合理部分无效"),
    ("单方变更服务内容", "单方变更", "排除消费者权利，该格式条款无效"),
]


def clause_flags(kv):
    clause = get_text(kv, ["会籍协议中的退卡条款", "协议退卡条款", "退卡条款", "协议条款"])
    s = norm(clause) + " " + norm(get_text(kv, ["协议原文摘录", "条款摘录"]))
    out = []
    for label, kw, why in FORM_CLAUSES:
        if kw in s:
            out.append((label, why))
    return out, clause


# ------------------------------------------------------------------ 测算
def calc_refund(f):
    """返回测算字典。口径缺失的证据一律 None。"""
    res = {}
    paid = f["paid"]
    total_days = f["total_days"]
    used_days = f["used_days"]
    bonus_days = f["bonus_days"]
    type_ = f["card_type"]
    total_lessons = f["total_lessons"]
    used_lessons = f["used_lessons"]
    bonus_lessons = f["bonus_lessons"]

    res["mode"] = "未知"
    res["unit"] = None
    res["consumed"] = None
    res["payable_days"] = None
    res["um_paid"] = None
    res["um_consumed"] = None
    res["um_unpaid"] = None
    res["um_penalty"] = None
    res["um_refund"] = None

    if type_ == "私教课包":
        tot = (total_lessons or 0) + (bonus_lessons or 0)
        if paid and tot and used_lessons is not None:
            unit = paid / tot
            consumed = unit * used_lessons
            unpaid = paid - consumed
            res.update(mode="课时", unit=unit, consumed=consumed, payable_days=tot,
                       um_paid=paid, um_consumed=consumed, um_unpaid=unpaid)
        elif paid and used_lessons is not None and total_lessons:
            unit = paid / total_lessons
            consumed = unit * used_lessons
            unpaid = paid - consumed
            res.update(mode="课时", unit=unit, consumed=consumed, payable_days=total_lessons,
                       um_paid=paid, um_consumed=consumed, um_unpaid=unpaid)
    else:
        tot = (total_days or 0) + (bonus_days or 0)
        if paid and tot and used_days is not None:
            unit = paid / tot
            consumed = unit * used_days
            unpaid = paid - consumed
            res.update(mode="天数", unit=unit, consumed=consumed, payable_days=tot,
                       um_paid=paid, um_consumed=consumed, um_unpaid=unpaid)
        elif paid and used_days is not None and total_days:
            unit = paid / total_days
            consumed = unit * used_days
            unpaid = paid - consumed
            res.update(mode="天数", unit=unit, consumed=consumed, payable_days=total_days,
                       um_paid=paid, um_consumed=consumed, um_unpaid=unpaid)

    # 挂牌原价口径对照
    lp = f["list_price_month"]
    if lp is not None and f["used_months"] is not None:
        res["list_consumed"] = lp * f["used_months"]
    return res


def penalty_calc(f, unpaid, scenario_code):
    """返回 (违约金, 说明, 状态)。"""
    if unpaid is None:
        return None, "未履行部分算不出来，违约金暂无法测算——请补齐实付总额与已用数量。", "待补正"
    if scenario_code in TRIGGER_FULL:
        return 0.0, ("属**经营者违约**情形（%s），消费者解除合同的，"
                     "不应向经营者支付违约金，反而可主张经营者承担违约责任。"
                     % f["scenario"][0]), "通过"
    if scenario_code == "s5":
        return None, ("因自身健康原因退卡，违约金可能仍需承担，但可请求按经营者实际损失酌减；"
                      "请提交医院诊断证明并书面主张减免。"), "有风险"
    rate = f["penalty_rate"]
    has = f["has_penalty"]
    if has is True and rate is None:
        return round(unpaid * 0.20, 2), (
            "协议约定了违约金但未填比例，按司法实践常见参考上限（未履行部分的 20%）暂测；"
            "注意违约金以**实际损失**为限、由经营者举证，约定过高可请求减少。"), "有风险"
    if has is False and rate is None:
        return 0.0, ("协议未约定违约金，按 0 计；经营者临时主张违约金的，"
                     "须举证其实际损失。"), "通过"
    if rate is not None:
        p = rate / 100.0
        return round(unpaid * p, 2), (
            "按协议约定比例 %s%% 测算：未履行部分 %s × %s%% = %s；"
            "如约定明显高于实际损失可请求适当减少。"
            % (fmt_num(rate), money(unpaid), fmt_num(rate),
               money(unpaid * p))), "通过"
    return None, "违约金比例未填，请填「协议约定的违约金比例」。", "待补正"


def cooling_period(f, today):
    """冷静期三分支。返回 (状态, 说明, 截止日)。"""
    city = f["city"]
    has_rule = f["cooling_rule"]
    buy = f["buy_date"]
    used_any = f["used_any"]
    if has_rule is True:
        if buy is None:
            return ("待补正", "所在地（%s）有健身消费冷静期规定，但**未填购卡日期**，算不出是否还在期内。"
                    "请补填购卡日期。" % (city or "未填City")), None
        left = (buy + timedelta(days=7) - today).days
        if left < 0:
            return ("不通过", "所在地（%s）设有健身类冷静期（常见 7 日），但自 %s 购卡起算已过 %d 天，"
                    "冷静期已届满；是否仍可退，看当地规定是否以「未实际消费」为条件。%s"
                    % (city or "未填", buy.isoformat(), -left,
                       "" if used_any else "所填未实际消费，仍可再尝试以未消费为由主张。")), None
        if used_any is True:
            return ("有风险", "所在地（%s）设有冷静期，但购卡后已实际消费，多数地方以「未实际消费」"
                    "作为冷静期退卡条件，冷静期适用存在不确定性；%s" % (city or "未填",
                                                            "仍可书面主张并要求按当地规定办理。")), None
        return ("通过", "所在地（%s）设有健身类预付消费冷静期（常见 7 日），"
                "自 %s 购卡起算尚在期内且未实际消费，**可主张全额退款**；"
                "具体期限与扣费口径以当地规定为准。" % (city or "未填", buy.isoformat())), None
    if has_rule is False:
        return ("待补正", "填了「所在地无明确冷静期规定」，则不适用冷静期全额退，"
                "退费按第三段算式主张；是否另有地方性规则，请以当地商务、市场监管口径为准。"), None
    return ("待补正", "所在地是否有健身消费冷静期规定**未填**"
            "（如 %s 未填）。上海、北京等地对体育健身类预付消费有相关规定，"
            "是否适用、期限多长一律**以当地商务主管部门与市场监管部门口径为准**。"
            % (city if city else "所在地")), None


def path_order(f, scenario_code):
    base = [
        ("第 1 步", "固定证据并书面交涉：拍门店门头与现状、截会员系统余额、"
                    "导出消费与预约记录，向门店出具**书面退卡申请**（写明卡号、实付、"
                    "已用、诉求金额、期限 7 日），通过微信/邮件留痕并索要回执"),
        ("第 2 步", "门店拒绝或失联的，向**品牌总部/运营公司**书面主张（连锁加盟店总部可能承担相应责任）"),
        ("第 3 步", "双线投诉：**12315（市场监管）+ 属地商务主管部门（单用途商业预付卡主管条线）**"
                    "同步提交；涉众的联合其他会员集体反映"),
        ("第 4 步", "仍有争议的，就退费争议提起民事诉讼，标的额较小的走**小额诉讼**程序（诉讼时效 3 年）"),
    ]
    steps = list(base)
    if scenario_code == "s1":
        steps.insert(2, ("第 2.5 步", "**门店已关闭/跑路**：先查经营者主体（国家企业信用信息公示系统）"
                                     "是否已注销、股东清算责任；同时联合同案会员向公安经侦反映"
                                     "（涉嫌非法吸收公众存款、集资诈骗的）"))
    elif scenario_code == "s3":
        steps.insert(2, ("第 2.5 步", "**转让不承接**：向**原经营者**主张（原经营者是收款方，"
                                     "未履行债务转移义务），要求其出具转让公告与新主体拒绝承接的书面回复"))
    if f["loan"] is True:
        steps.append(("第 5 步", "**分期贷/培训贷付款的单独处理**：贷款合同与健身服务合同是两层关系，"
                                 "商家跑路不当然免除还款义务——立即联系贷款机构说明情况，"
                                 "申请停贷、展期或走争议处理，避免逾期上征信；"
                                 "同时以「根本违约」为由主张解除贷款合同"))
    return steps


def todo_list(f, results, calc, penalty, cooling):
    todos = []
    for _, rows in results:
        for name, state, _msg in rows:
            if state in ("不通过", "有风险", "待补正"):
                todos.append((name, state))
    extra = []
    if f["scenario"][1] == "s1" or f["scenario"][1] == "s3":
        extra.append(("查主体", "在国家企业信用信息公示系统查经营者全称、法定代表人与存续状态"))
    if f["scenario"][1] == "s5" and f["health_proof"] is not True:
        extra.append(("医院诊断证明", "健康原因退卡必须提交医院诊断证明/医嘱，口头说明不被采信"))
    if f["loan"] is True:
        extra.append(("联系贷款机构", "商家跑路不当然免除还款义务，立即申请停贷/展期并保留书面回复"))
    extra.append(("书面申请留痕", "一律用可留存的形式（微信文字、邮件、纸质回执），不要只打电话"))
    extra.append(("集体维权", "同店会员人数较多的，联名投诉效果明显好于单人"))
    seen = set()
    out = []
    for n, s in todos + extra:
        if n in seen:
            continue
        seen.add(n)
        out.append((n, s))
    return out


# ------------------------------------------------------------------ 报告
def render(f, results, calc, pen, cool, steps, todos, today):
    L = []
    L.append("# 健身房退卡退费核算报告")
    L.append("")
    L.append("- 核查日期：%s" % today.isoformat())
    L.append("- 经营者/门店：%s" % (f["subject"] or "未填"))
    L.append("- 卡种：%s" % (f["card_type"] or "未填"))
    L.append("")
    scen_name, scen_code = f["scenario"]

    # 1 结论摘要
    bad = [r for _, rows in results for r in rows if r[1] == "不通过"]
    risk = [r for _, rows in results for r in rows if r[1] == "有风险"]
    todo = [r for _, rows in results for r in rows if r[1] == "待补正"]
    L.append("## 一、结论摘要")
    L.append("")
    if scen_code in TRIGGER_FULL:
        L.append("**判定：门店存在根本违约情形（%s），可以主张全额退未履行部分，且不应承担违约金。**" % scen_name)
    elif scen_code == "s5":
        L.append("**判定：可退，但属消费者自身原因，需折抵已消耗部分并可能承担违约金——"
                 "关键是拿到医院诊断证明。**")
    elif scen_code == "s4":
        L.append("**判定：可退。教练/课程与承诺不符属经营者违约，服务缩水部分应折价扣减，"
                 "应退金额高于单纯按已用天数折算的结果。**")
    elif scen_code in (None, "未填", "未识别"):
        L.append("**判定：退卡权没有疑问（预付卡不是「买了就不能退」），但可退多少取决于"
                 "已消耗按什么单价折算——本报告中第第二段算式可直接用于谈判。**")
    else:
        L.append("**判定：单纯不想用也能退，已消耗按会员优惠单价折抵，剩余部分应退。**")
    L.append("")
    L.append("| 项 | 数量 |")
    L.append("|---|---|")
    L.append("| 不通过 | %d |" % len(bad))
    L.append("| 有风险 | %d |" % len(risk))
    L.append("| 待补正 | %d |" % len(todo))
    L.append("")
    for name, _s, msg in bad[:5]:
        L.append("- **%s**：%s" % (name, (msg or "").replace("**", "")))
    for name, _s, msg in risk[:5]:
        L.append("- %s：%s" % (name, (msg or "").replace("**", "")))
    L.append("")

    titles = ["二、退费测算（含完整算式）", "三、格式条款效力判定",
              "四、触发情形与能否退", "五、冷静期判定"]
    for (title, rows), t in zip(results, titles):
        if not rows:
            continue
        L.append("## %s" % t)
        L.append("")
        L.append("| 核查项 | 判定 | 说明 |")
        L.append("|---|---|---|")
        for name, state, msg in rows:
            L.append("| %s | %s | %s |" % (name, state, (msg or "").replace("|", " ")))
        L.append("")

    # 六 维权路径
    L.append("## 六、维权路径排序")
    L.append("")
    for step, txt in steps:
        L.append("- **%s**：%s" % (step, txt))
    L.append("")

    # 七 证据缺口
    L.append("## 七、证据缺口与清单核对")
    L.append("")
    L.append("| 材料 | 状态 | 说明 |")
    L.append("|---|---|---|")
    for name, state, note in f["evidence_rows"]:
        L.append("| %s | %s | %s |" % (name, state, note.replace("|", " ")))
    L.append("")
    miss = [n for n, s, _ in f["evidence_rows"] if s in ("否", "未填")]
    L.append("缺口：%s。" % ("、".join(miss) if miss else "已填项无缺口；未填的不算已具备"))
    L.append("")

    # 八 时限
    L.append("## 八、时限清单")
    L.append("")
    L.append("| 事项 | 期限 |")
    L.append("|---|---|")
    buy = f["buy_date"]
    if buy:
        L.append("| 冷静期（以当地规定为准，常见 7 日） | 自 %s 起算，届满日 %s |"
                 % (buy.isoformat(), (buy + timedelta(days=7)).isoformat()))
    L.append("| 书面催告建议期限 | 7 日（催告可中断诉讼时效，务必留送达证据） |")
    L.append("| 民事诉讼时效 | 3 年，自知道或应当知道权利受损及义务人之日起算 |")
    L.append("| 12315 投诉办结时限 | 一般 7 日内决定是否受理，60 日内办结，可延长 30 日 |")
    L.append("| 预收资金存管/清算 | 门店停业后由商务主管部门与清算程序处理，越早申报越优先 |")
    L.append("")
    if buy:
        left = (buy + timedelta(days=7) - today).days
        if left >= 0:
            L.append("- 距冷静期届满约 %d 天，**这几天内主张全额退成功率最高**，建议明天就书面提出。" % left)
        else:
            L.append("- 冷静期已过 %d 天，转按「已消耗折抵 + 未履行部分返还」口径主张。" % -left)
    L.append("")

    # 九 待办
    L.append("## 九、待办补正动作")
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
    L.append("- 本结果依《消费者权益保护法》及商务主管部门**单用途商业预付卡管理相关规定**等"
             "通用规则整理，**不替代律师意见**。")
    L.append("- 冷静期是否适用、期限多长、是否以「未实际消费」为条件，"
             "**一律以当地商务主管部门、市场监管部门与体育主管部门口径为准**；"
             "查询入口为当地商务局（单用途商业预付卡条线）、市场监管局官网/公众号、12345。")
    L.append("- 违约金以**实际损失**为限，由主张方举证；20%~30% 只是司法实践常见参考区间，"
             "测算值为**谈判起点**而非法院必然支持的金额，不预测判决结果。")
    L.append("- **未填的一律不算通过**，只按已填内容判断。")
    L.append("")
    L.append("本结果依通用规则整理，不替代专业意见，最终以主管部门/司法机关认定为准。")
    return "\n".join(L) + "\n"


def to_json(f, results, calc, pen, cool, todos, today):
    return {
        "核查日期": today.isoformat(),
        "经营者": f["subject"],
        "卡种": f["card_type"],
        "退卡触发情形": f["scenario"][0],
        "测算": {
            "口径": calc["mode"],
            "实付总额": calc["um_paid"],
            "应计量单位数": calc["payable_days"],
            "单价": calc["unit"],
            "已消耗价值": calc["um_consumed"],
            "未履行部分": calc["um_unpaid"],
            "违约金": pen[0],
            "应退": calc["um_refund"],
        },
        "冷静期": cool[0],
        "结论": {
            "不通过": [r[0] for _, rows in results for r in rows if r[1] == "不通过"],
            "有风险": [r[0] for _, rows in results for r in rows if r[1] == "有风险"],
            "待补正": [r[0] for _, rows in results for r in rows if r[1] == "待补正"],
        },
        "待办": [{"动作": n, "状态": s} for n, s in todos],
    }


EVIDENCE_ROWS = [
    ("办卡合同/会籍协议", "协议文本", "手办卡协议、电子协议截图，重点圈出退卡与违约金条款"),
    ("付款凭证", "凭证", "收据、POS 单、支付记录、发票；分期贷的还要打印贷款合同与还款流水"),
    ("实付总额与赠送约定", "凭证", "赠送课时/赠送期限有无书面或聊天记录，是摊薄单价的依据"),
    ("已消耗记录", "记录", "会员系统消费明细、预约记录、课程打卡记录"),
    ("门店现状照片", "照片", "关闭/迁址/转让时拍门头、锁门照、物业或公告、会员群通知"),
    ("承诺与宣传材料", "截图", "教练承诺、宣传页、直播间话术、 APP 课程介绍的截图与链接"),
    ("书面交涉记录", "记录", "退卡申请的微信/邮件/纸质回执，门店的书面拒绝回复最有价值"),
    ("诊断证明（健康原因退卡）", "证明", "医院出具的诊断证明或医嘱，必须是书面件"),
    ("主体信息", "查询", "国家企业信用信息公示系统打印的经营者主体信息"),
]


def evidence_rows(kv):
    status = {
        "办卡合同/会籍协议": get_text(kv, ["有无办卡合同", "会籍协议"]),
        "付款凭证": get_text(kv, ["有无付款凭证", "付款凭证"]),
        "实付总额与赠送约定": get_text(kv, ["赠送课时/赠送期限有无书面约定", "赠送约定"]),
        "已消耗记录": get_text(kv, ["有无已消耗记录", "已消耗记录"]),
        "门店现状照片": get_text(kv, ["有无门店现状照片", "门店现状"]),
        "承诺与宣传材料": get_text(kv, ["有无承诺或宣传材料", "承诺材料"]),
        "书面交涉记录": get_text(kv, ["有无书面交涉记录", "交涉记录"]),
        "诊断证明（健康原因退卡）": get_text(kv, ["有无医院诊断证明", "诊断证明"]),
        "主体信息": get_text(kv, ["是否已查经营者主体", "经营者主体"]),
    }
    out = []
    for name, _d, note in EVIDENCE_ROWS:
        v = status.get(name, "")
        if yes(v):
            st = "是"
        elif no(v):
            st = "否"
        elif filled(v):
            st = "待确认"
        else:
            st = "未填"
        out.append((name, st, note))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--base", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    text = read_text(args.input)
    kv = build_kv(text)
    today = base_date(args.base)

    card_raw = get_text(kv, ["卡种", "卡的类型", "会员卡类型"])
    cnorm = norm(card_raw)
    if "私教" in cnorm or "课时" in cnorm or "课包" in cnorm:
        card_type = "私教课包"
    elif "次卡" in cnorm or "次数" in cnorm:
        card_type = "次卡"
    elif "年卡" in cnorm or "月卡" in cnorm or "季卡" in cnorm or "通卡" in cnorm:
        card_type = "期限卡"
    else:
        card_type = card_raw or ""

    f = {
        "subject": get_text(kv, ["门店名称", "经营者名称", "经营主体"]),
        "city": get_text(kv, ["门店所在地", "所在地", "城市"]),
        "buy_date": parse_date(get_text(kv, ["办卡日期", "购卡日期", "购卡时间"])),
        "card_type": card_type,
        "paid": parse_num(get_text(kv, ["实付总额", "办卡实付金额", "实际支付金额", "会员卡实付"])),
        "total_days": parse_num(get_text(kv, ["约定使用天数", "约定总天数", "卡有效期天数"])),
        "total_months": parse_num(get_text(kv, ["约定使用月数", "约定总月数", "会员期月数"])),
        "used_days": parse_num(get_text(kv, ["已使用天数", "已用天数", "已消耗天数"])),
        "used_months": parse_num(get_text(kv, ["已使用月数", "已用月数", "已过去月数"])),
        "bonus_days": parse_num(get_text(kv, ["赠送天数", "赠送使用期限"])),
        "total_lessons": parse_num(get_text(kv, ["约定总课时", "约定课程总数", "课包总课时"])),
        "used_lessons": parse_num(get_text(kv, ["已消耗课时", "已上课时数", "已用课时"])),
        "bonus_lessons": parse_num(get_text(kv, ["赠送课时数", "赠送课程数"])),
        "list_price_month": parse_num(get_text(kv, ["挂牌原价月单价", "原价月单价", "挂牌单价"])),
        "penalty_rate": pct_num(get_text(kv, ["协议约定的违约金比例", "违约金比例", "违约金标准"])),
        "has_penalty": None,
        "scenario": detect_scenario(get_text(kv, ["退卡触发情形", "退卡原因", "主张退卡的事由"])),
        "health_proof": None,
        "loan": None,
        "used_any": None,
        "cooling_rule": None,
        "evidence_rows": evidence_rows(kv),
    }
    hp = get_text(kv, ["是否有医院诊断证明", "诊断证明"])
    if yes(hp):
        f["health_proof"] = True
    elif no(hp):
        f["health_proof"] = False
    lo = get_text(kv, ["是否为分期贷/培训贷付款", "是否分期贷付款", "贷款分期"])
    if yes(lo):
        f["loan"] = True
    elif no(lo):
        f["loan"] = False
    ua = get_text(kv, ["购卡后是否已实际消费", "是否已实际消费"])
    if yes(ua):
        f["used_any"] = True
    elif no(ua):
        f["used_any"] = False
    cr = get_text(kv, ["所在地是否有健身消费冷静期规定", "当地有无冷静期"])
    if yes(cr):
        f["cooling_rule"] = True
    elif no(cr):
        f["cooling_rule"] = False

    hp_text = get_text(kv, ["协议是否约定违约金", "是否约定违约金"])
    if yes(hp_text):
        f["has_penalty"] = True
    elif no(hp_text):
        f["has_penalty"] = False

    if f["total_days"] is None and f["total_months"] is not None:
        f["total_days"] = f["total_months"] * 30
    if f["total_days"] is not None and f["total_months"] is None:
        f["total_months"] = f["total_days"] / 30.0
    if f["used_days"] is None and f["used_months"] is not None:
        f["used_days"] = f["used_months"] * 30

    missing = []
    if not filled(f["subject"]):
        missing.append("门店名称")
    if f["paid"] is None:
        missing.append("实付总额")
    if f["scenario"][1] is None and not filled(f.get("scenario")[0] or ""):
        pass
    if not filled(get_text(kv, ["退卡触发情形", "退卡原因", "主张退卡的事由"])):
        missing.append("退卡触发情形")

    calc = calc_refund(f)
    if calc["um_unpaid"] is not None:
        pen = penalty_calc(f, calc["um_unpaid"], f["scenario"][1])
        calc["um_penalty"] = pen[0]
        calc["um_refund"] = round(calc["um_unpaid"] - (pen[0] or 0), 2)
    else:
        pen = (None, "未履行部分算不出来，违约金暂无法测算——请补齐实付总额与已用数量。", "待补正")
    cool = cooling_period(f, today)
    steps = path_order(f, f["scenario"][1])
    todos = todo_list(f, [], calc, pen, cool)

    # ---------------------------------------------------------- 各段结果
    r_calc = []
    if calc["mode"] == "未知":
        r_calc.append(("退费测算", "待补正",
                       "实付总额、约定总量、已用数量三者缺一，算不出退多少——"
                       "请补齐后再跑。退费的基本模型是：应退 = 实付总额 − 已消耗价值 − 合理违约金。"))
    else:
        unit = calc["unit"]
        consumed = calc["um_consumed"]
        unpaid = calc["um_unpaid"]
        base_desc = ("实付总额 %s ÷ 应计量总量 %s = 单价 %s；"
                     "已消耗价值 = 单价 %s × 已用 %s。"
                     % (money(calc["um_paid"]), fmt_num(calc["payable_days"]), money(unit),
                        money(unit), fmt_num(consumed / unit) if unit else "—"))
        r_calc.append(("已消耗折算口径", "通过",
                       "本表按**会员优惠单价**折算（实付总额 ÷ 应计量总量），"
                       "这是消费者应当主张的口径。" + base_desc))
        lc = calc.get("list_consumed")
        if lc is not None:
            diff = consumed - lc
            txt = ("若门店改按挂牌原价扣（月单价 %s × 已用 %s 个月 = %s），"
                   "比会员优惠口径**多扣 %s**。先打折收钱、退费时按原价扣是两头占便宜，"
                   "谈判时直接把这两个数摆一起。"
                   % (money(f["list_price_month"]),
                      fmt_num(f["used_months"]), money(lc), money(abs(diff))))
            r_calc.append(("与挂牌原价口径的差额", "有风险", txt))
        r_calc.append(("未履行部分", "通过",
                       "实付总额 %s − 已消耗价值 %s = %s，这是主张退还的基数。"
                       % (money(calc["um_paid"]), money(consumed), money(unpaid))))
        r_calc.append(("合理违约金", pen[2], pen[1]))
        if calc["um_refund"] is not None:
            r_calc.append(("应退金额测算", "通过",
                           "未履行部分 %s − 违约金 %s = **应退约 %s**；"
                           "此数为谈判起点，最终以协商或裁判为准。"
                           % (money(calc["um_unpaid"]), money(pen[0]), money(calc["um_refund"]))))

    r_clause = []
    flags, _clause_text = clause_flags(kv)
    if flags:
        r_clause.append(("格式条款", "有风险",
                         "协议中出现：%s。**这些属经营者以格式条款排除或者限制消费者权利、"
                         "减轻或免除自身责任的内容，该条款无效**；但条款无效 ≠ 全额退，"
                         "已享受的服务仍应按会员价折抵。"
                         % "；".join('"%s"（%s）' % (a, b) for a, b in flags)))
    else:
        r_clause.append(("格式条款", "待补正",
                         "未填协议退卡条款。若协议里有「概不退费」「最终解释权归本店」"
                         "「余额过期作废」等字样，这些是**无效的格式条款**（排除消费者主要权利、"
                         "免除经营者责任），但拆掉这堵墙不等于全额退。"))

    r_scen = []
    sn, sc = f["scenario"]
    if sc in TRIGGER_FULL:
        r_scen.append(("触发情形", "通过",
                       "**%s** 属经营者根本违约/债务未妥善转移，合同目的不能实现，"
                       "可主张解除并要求退还未履行部分，**且不应向经营者支付违约金**。"
                       % sn))
    elif sc == "s5":
        r_scen.append(("触发情形", "有风险",
                       "**%s** 属消费者自身原因，可要求退未履行部分，"
                       "但违约金未必全免，可请求按经营者实际损失酌减。" % sn))
    elif sc == "s4":
        r_scen.append(("触发情形", "通过",
                       "**%s** 属服务与约定不符、经营者违约，"
                       "除退未履行部分外，还可就承诺未兑现主张损失；"
                       "关键是固定「承诺」与「未兑现」两方面的证据。" % sn))
    else:
        r_scen.append(("触发情形", "通过",
                       "退卡权本身没有疑问：健身卡属单用途商业预付卡，"
                       "受商务主管部门单用途商业预付卡管理规定规范，不是「买了就不能退」。"
                       "已消耗部分按会员优惠单价折抵，剩余部分应退。"))
    if f["loan"] is True:
        r_scen.append(("分期贷/培训贷", "有风险",
                       "该笔办卡是分期贷付款的：**贷款合同与健身服务合同是两层法律关系**，"
                       "商家跑路或关门不当然免除你的还款义务。请立即联系贷款机构申请停贷、展期"
                       "或走争议处理，避免逾期上征信；同时以根本违约为由主张解除贷款合同。"))
    elif f["loan"] is None:
        r_scen.append(("分期贷/培训贷", "待补正",
                       "是否通过分期贷/培训贷付款未填。若办卡时办了贷款，"
                       "贷款与服务是两层关系，商家跑路不当然免除还款义务，需单独处理。"))

    cool_state, cool_text = cool[0]
    r_cool = [("冷静期", cool_state, cool_text)]

    results = [("退费测算", r_calc), ("格式条款效力", r_clause),
               ("触发情形", r_scen), ("冷静期", r_cool)]

    todos = todo_list(f, results, calc, pen, cool)
    todos = [(n, s) for n, s in todos
             if n not in ("已消耗折算口径", "未履行部分", "应退金额测算", "退费测算")]

    if args.json:
        print(json.dumps(to_json(f, results, calc, pen, cool, todos, today),
                         ensure_ascii=False, indent=2))
        return 0

    rep = render(f, results, calc, pen, cool, steps, todos, today)
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
