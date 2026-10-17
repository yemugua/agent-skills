# -*- coding: utf-8 -*-
"""健身房私教课退费与套路识别核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：9 段核查报告，含结论摘要、合同主体与资质、退费条款效力、课时与退费测算、
      有效期教练变更与门店变更、证据清单、维权路径、待办补正动作、边界与纪律。

退出码：0 正常；2 关键信息缺失（打印提示，不崩）。
"""
import argparse
import json
import os
import re
import sys
from datetime import date

FIELD_ALIAS = {
    "健身房名称": ["健身房名称", "门店名称", "会所名称", "健身馆", "门店"],
    "合同主体": ["合同主体", "签约主体", "合同上的公司名", "签约公司", "合同甲方"],
    "实际收款主体": ["实际收款主体", "收款方", "收款主体", "付款给谁", "收款单位", "发票抬头"],
    "门店现状": ["门店现状", "门店状态", "经营状态", "是否还在营业", "机构现状"],
    "课程类型": ["课程类型", "课程种类", "买的什么课", "卡种"],
    "购课日期": ["购课日期", "购买日期", "办卡日期", "签约日期"],
    "购课总节数": ["购课总节数", "总节数", "买了多少节", "课程总数", "购买节数"],
    "已上节数": ["已上节数", "已用节数", "上了多少节", "已消费节数", "使用节数"],
    "单节价格": ["单节价格", "每节价格", "单价", "单节课费"],
    "合同总金额": ["合同总金额", "合同金额", "套餐总价", "合同价"],
    "已付金额": ["已付金额", "已支付金额", "实付金额", "付款金额", "已交费用"],
    "已退金额": ["已退金额", "已退款金额", "退款金额", "已返还金额"],
    "约定有效期": ["约定有效期", "有效期", "合同期限", "使用期限"],
    "有效期至": ["有效期至", "到期日", "过期日期", "截止日期"],
    "是否已过期": ["是否已过期", "是否过期", "过期情况"],
    "退款条款摘录": ["退款条款摘录", "退费条款", "合同条款", "格式条款原文", "条款摘录"],
    "销售承诺摘录": ["销售承诺摘录", "销售话术", "承诺话术", "宣传承诺", "口头承诺"],
    "是否书面提示有效期": ["是否书面提示有效期", "有效期是否提示", "有无显著提示", "提示情况"],
    "教练是否已离职": ["教练是否已离职", "教练是否离职", "教练离职", "教练走了吗"],
    "是否指定教练": ["是否指定教练", "有无指定教练", "指定教练"],
    "是否同意更换教练": ["是否同意更换教练", "是否接受换教练", "换教练是否同意"],
    "是否可转卡转让": ["是否可转卡转让", "能否转卡", "是否可转让", "转卡情况"],
    "转卡手续费": ["转卡手续费", "转让手续费", "过户费", "转卡费用"],
    "门店是否转让": ["门店是否转让", "是否转让", "是否易主", "老板是否换了"],
    "是否书面提出退费": ["是否书面提出退费", "是否书面申请", "有无书面申请", "是否提交退费申请"],
    "书面提出日期": ["书面提出日期", "申请日期", "提交日期"],
    "机构答复": ["机构答复", "门店答复", "答复情况", "对方怎么说"],
    "是否已投诉": ["是否已投诉", "有无投诉", "投诉情况"],
    "证据留存情况": ["证据留存情况", "证据情况", "有哪些证据", "留证情况", "已保存材料"],
    "诉求": ["诉求", "希望怎么解决", "期望结果", "想要什么结果"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)


def norm(s):
    if s is None:
        return ""
    out = str(s).strip()
    out = out.replace("：", ":").replace("　", " ")
    out = out.replace("（", "(").replace("）", ")")
    out = re.sub(r"\s+", "", out)
    return out.lower()


def filled(v):
    if v is None:
        return False
    return norm(v) not in {norm(t) for t in EMPTY_TOKENS}


def unknown(v):
    return not filled(v)


def fmt_num(n):
    if n is None:
        return "-"
    if isinstance(n, float):
        if n == int(n):
            return str(int(n))
        return ("%.2f" % n).rstrip("0").rstrip(".")
    return str(n)


def money(n):
    if n is None:
        return "-"
    return "¥" + fmt_num(round(float(n), 2))


def parse_num(v):
    if v is None:
        return None
    s = str(v).replace(",", "").replace("，", "")
    s = re.sub(r"[¥￥元人民币rmb$]", "", s)
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def parse_date(v):
    if v is None or unknown(v):
        return None
    s = str(v).strip()
    s = s.replace("年", "-").replace("月", "-").replace("日", "")
    s = s.replace("/", "-").replace(".", "-")
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except Exception:
        return None


def days_between(a, b):
    if not a or not b:
        return None
    return (b - a).days


def parse_md(path):
    data = {}
    if not path or not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            line = line.lstrip(">").strip()
        if not line:
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 2:
                continue
            key_raw = cells[0]
            if set(key_raw) <= set("-: "):
                continue
            val = " ".join(c.strip() for c in cells[1:]).strip()
            if val:
                data[norm(key_raw)] = val
            continue
        if ":" in line or "：" in line:
            parts = re.split(r"[:：]", line, 1)
            if len(parts) == 2:
                k = parts[0].strip().lstrip("-*# ").strip()
                v = parts[1].strip()
                if k and v:
                    data[norm(k)] = v
    return data


def get_text(f, key):
    """精确匹配表头，绝不用子串 in（会串字段）。"""
    aliases = sorted(FIELD_ALIAS.get(key, [key]), key=len, reverse=True)
    for a in aliases:
        na = norm(a)
        if not na:
            continue
        if na in f:
            v = f.get(na)
            if filled(v):
                return v
        stripped = re.sub(r"^\d+[.、)]\s*", "", na)
        if stripped != na and stripped in f:
            v = f.get(stripped)
            if filled(v):
                return v
    return ""


NEG_WORDS = ("否", "没有", "未", "不", "无", "否认", "拒绝", "不知情", "没做")
POS_WORDS = ("是", "已", "有", "承认", "确认", "同意", "认可", "已做")


def yesno(text):
    if unknown(text):
        return None
    n = norm(text)
    for w in NEG_WORDS:
        if n.startswith(w):
            return False
    for w in POS_WORDS:
        if n.startswith(w):
            return True
    return None


def check_entity(f):
    """合同主体与收款主体一致性：返回 (状态, 说明列表)。"""
    items = []
    org = get_text(f, "合同主体")
    payee = get_text(f, "实际收款主体")
    status_now = get_text(f, "门店现状")
    n_now = norm(status_now)
    # 先判经营状态，避免被主体字段的空值分支挡住
    if any(k in n_now for k in ("停业", "关门", "跑路", "失联", "倒闭")):
        items.append("门店已停业或失联：立即固定合同与付款凭证，同步投诉与报案")
        return "不通过", items
    if not filled(org) and not filled(payee):
        items.append("未填写合同主体与实际收款主体，**向谁主张退费无法判断**")
        return "待补正", items
    if filled(org) and filled(payee):
        if norm(org) == norm(payee):
            items.append("合同主体与收款主体一致：%s" % org)
        else:
            items.append("**合同主体「%s」与收款主体「%s」不一致**："
                         "出事后极易互相推诿，两家都应列入主张对象" % (org, payee))
            return "不通过", items
    else:
        items.append("仅有一方主体信息（合同主体=%s / 收款主体=%s），"
                     "需核对付款凭证上的收款方名称" % (org or "未填写", payee or "未填写"))
        return "有风险", items
    n_now = norm(status_now)
    if filled(status_now):
        if any(k in n_now for k in ("停业", "关门", "跑路", "失联", "倒闭")):
            items.append("门店已停业或失联：立即固定合同与付款凭证，同步投诉与报案")
            return "不通过", items
        if "转让" in n_now or "易主" in n_now or "换老板" in n_now:
            items.append("门店已转让：要求受让方书面确认承接会员债务，不确认的向原主体主张")
            return "有风险", items
        items.append("门店现状：%s" % status_now)
    else:
        items.append("未填写门店现状，无法判断履约风险")
    return "通过", items


def check_terms(f):
    """退费条款效力：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    term = get_text(f, "退款条款摘录")
    promo = get_text(f, "销售承诺摘录")
    told = yesno(get_text(f, "是否书面提示有效期"))
    t = norm(term)
    if filled(term):
        items.append("条款摘录：%s" % str(term)[:120])
        bad = {
            "概不退费": "「概不退费」不合理免除经营者责任、排除消费者主要权利，可主张无效",
            "概不退款": "「概不退款」同上，可主张无效",
            "过期作废": "「过期作废」不能使未消费余额当然消灭，且须显著提示",
            "最终解释权": "「最终解释权归本店」是典型的排除消费者权利表述",
            "只能转": "「只能转让不能退」限制了消费者的法定退款请求权",
            "概不负责": "免除责任的条款无效",
            "不予退还": "排除退款请求权的条款可主张无效",
        }
        for k, v in bad.items():
            if k in t:
                crit.append("条款问题：%s" % v)
    else:
        risk.append("未填写退款条款摘录，无法判断是否存在不公平格式条款")

    p = norm(promo)
    if filled(promo):
        items.append("销售承诺：%s" % str(promo)[:120])
        for k in ("随时退", "随时可退", "随时可以退", "不想上就退", "包退", "无条件退"):
            if k in p:
                risk.append("销售曾承诺「%s」，但未写入合同的，需以聊天记录或录音固定" % k)
        for k in ("不退", "不能退", "办了就不能退"):
            if k in p:
                risk.append("销售口径含「%s」，与其承诺义务冲突，应留存原始载体" % k)
    else:
        risk.append("未填写销售承诺摘录；口头承诺是最有力的证据，建议补全")

    if told is False:
        risk.append("有效期未做书面显著提示，可主张该条款不成为合同内容")
    elif told is None:
        risk.append("未填写是否书面提示有效期")
    return crit, risk, items


def calc_refund(f, org_reason):
    """课时与退费测算：返回 (应退金额或 None, 说明列表)。"""
    items = []
    paid = parse_num(get_text(f, "已付金额"))
    total_amt = parse_num(get_text(f, "合同总金额"))
    back = parse_num(get_text(f, "已退金额")) or 0.0
    total_cnt = parse_num(get_text(f, "购课总节数"))
    used = parse_num(get_text(f, "已上节数"))
    unit = parse_num(get_text(f, "单节价格"))

    if paid is None and total_amt is None:
        return None, ["未填写已付金额与合同总金额，**应退无法测算**"]
    base_amt = paid if paid is not None else total_amt
    items.append("计算基数取%s：%s" % ("已付金额" if paid is not None else "合同总金额", money(base_amt)))

    if total_cnt and used is not None:
        left = total_cnt - used
        items.append("购课 %s 节，已上 %s 节，剩余 %s 节" %
                     (fmt_num(total_cnt), fmt_num(used), fmt_num(max(left, 0))))
        if unit is None:
            if total_cnt > 0:
                unit = base_amt / total_cnt
                items.append("合同未写单节价格，按 总价÷总节数 推算单节价：%s" % money(round(unit, 2)))
            else:
                items.append("购课总节数为 0，无法推算单节价")
        if unit is not None:
            consumed = used * unit
            unconsumed = max(base_amt - consumed, 0.0)
            items.append("已消费金额 = 已上 %s 节 × %s = %s" %
                         (fmt_num(used), money(round(unit, 2)), money(round(consumed, 2))))
            items.append("未消费金额 = %s − %s = %s" %
                         (money(base_amt), money(round(consumed, 2)), money(round(unconsumed, 2))))
            refund = max(unconsumed - back, 0.0)
            if back > 0:
                items.append("扣除已退 %s 后，参考应退 %s" % (money(back), money(round(refund, 2))))
            else:
                items.append("参考应退（未扣违约金）：%s" % money(round(refund, 2)))
            if org_reason:
                items.append("属**机构原因**（门店停业/教练离职不可安排），未消费部分应全额退还，"
                             "机构主张的违约金一般不应支持")
            else:
                items.append("属**消费者原因**，机构可主张扣除与实际损失相当的违约金，"
                             "但销售提成、管理费等内部成本不应转嫁")
            return refund, items
    else:
        items.append("购课总节数或已上节数未填写，**按课时测算无法进行**；"
                     "需以系统内的剩余节数截图为准")
        return None, items
    return None, items


def check_validity(f, base):
    """有效期、教练变更、门店变更：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    exp = parse_date(get_text(f, "有效期至"))
    expired = yesno(get_text(f, "是否已过期"))
    coach = yesno(get_text(f, "教练是否已离职"))
    assigned = yesno(get_text(f, "是否指定教练"))
    agree = yesno(get_text(f, "是否同意更换教练"))
    transfer = yesno(get_text(f, "是否可转卡转让"))
    fee = parse_num(get_text(f, "转卡手续费"))
    moved = yesno(get_text(f, "门店是否转让"))

    if exp is not None:
        d = days_between(exp, base)
        if d > 0:
            items.append("有效期已于 %s 届满，逾期 %s 天" % (exp.isoformat(), fmt_num(d)))
            risk.append("已过期：有效期条款须显著提示；未消费余额不因期限届满而当然消灭，"
                        "仍可主张返还未消费部分")
        else:
            items.append("有效期至 %s，剩余 %s 天" % (exp.isoformat(), fmt_num(-d)))
    elif expired is True:
        risk.append("已申报过期但未填写有效期至，无法核算逾期天数")
    elif expired is None:
        items.append("未填写有效期至与是否已过期")

    if coach is True:
        if assigned is True and agree is False:
            crit.append("指定教练离职且未同意更换：属合同主要内容变更，可主张解除并退还未消费部分")
        elif assigned is True and agree is None:
            risk.append("指定教练离职，是否同意更换未填写——不同意的要**第一时间书面提出**，"
                        "已接受新教练上课的会被视为默认变更")
        elif assigned is True:
            items.append("指定教练离职但已同意更换，退费主张难度上升")
        else:
            items.append("教练离职但未指定教练，需核实课程是否仍可正常安排")
    elif coach is None:
        items.append("未填写教练是否离职")

    if transfer is False:
        risk.append("明确不可转卡转让：转让不能替代法定退款请求权，仍可主张退费")
    elif transfer is True and fee is not None:
        if fee >= 300:
            risk.append("转卡手续费 %s 偏高，应与实际成本相当，过高可请求调整" % money(fee))
        else:
            items.append("可转卡，手续费 %s" % money(fee))
    elif transfer is None:
        items.append("未填写是否可转卡转让")

    if moved is True:
        crit.append("门店已转让：受让方承接原会员债务，原主体仍有责任；"
                    "应要求新店书面确认承接，不确认的向原主体主张")
    elif moved is None:
        items.append("未填写门店是否转让")
    return crit, risk, items


def check_evidence(f):
    ev = norm(get_text(f, "证据留存情况"))
    need = [
        ("书面合同或协议原件", ("合同", "协议", "签约")),
        ("付款凭证与发票", ("付款", "发票", "收据", "转账", "流水", "pos")),
        ("剩余节数与有效期截图", ("节数", "截图", "有效期", "系统")),
        ("上课记录与约课记录", ("上课记录", "约课", "签到", "课时记录")),
        ("销售承诺原始载体", ("聊天", "录音", "宣传", "承诺", "微信")),
        ("书面退费申请与 EMS 面单", ("申请", "ems", "面单", "快递")),
    ]
    if not ev:
        return [], [n for n, _ in need]
    have = []
    miss = []
    for name, kws in need:
        if any(k in ev for k in kws):
            have.append(name)
        else:
            miss.append(name)
    return have, miss


def build_report(f, base):
    rep = []
    crit = []
    risk = []
    todo = []

    gym = get_text(f, "健身房名称")
    course = get_text(f, "课程类型")
    demand = get_text(f, "诉求")
    paid = parse_num(get_text(f, "已付金额"))
    total_amt = parse_num(get_text(f, "合同总金额"))
    status_now = get_text(f, "门店现状")
    coach = yesno(get_text(f, "教练是否已离职"))
    assigned = yesno(get_text(f, "是否指定教练"))
    agree = yesno(get_text(f, "是否同意更换教练"))
    moved = yesno(get_text(f, "门店是否转让"))
    n_now = norm(status_now)

    closed = any(k in n_now for k in ("停业", "关门", "跑路", "失联", "倒闭"))
    org_reason = closed or (coach is True and assigned is True and agree is False) or moved is True

    ent_status, ent_items = check_entity(f)
    t_crit, t_risk, t_items = check_terms(f)
    refund, refund_items = calc_refund(f, org_reason)
    v_crit, v_risk, v_items = check_validity(f, base)
    have_ev, miss_ev = check_evidence(f)

    core_missing = paid is None and total_amt is None
    if not core_missing:
        crit.extend(t_crit)
        crit.extend(v_crit)
        if ent_status == "不通过":
            crit.append("主体或经营状态异常：见合同主体与资质核查")
        risk.extend(t_risk)
        risk.extend(v_risk)
        if ent_status == "待补正":
            risk.append("主体信息未填写，需补录合同主体与实际收款主体")
        if miss_ev:
            risk.append("证据缺失 %d 项：%s" % (len(miss_ev), "、".join(miss_ev[:3])))
        if yesno(get_text(f, "是否书面提出退费")) is False:
            risk.append("尚未书面提出退费：口头主张不留痕，应补 EMS 书面申请")

    if core_missing:
        verdict = "待补正"
    elif crit:
        verdict = "不通过"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "通过"

    # 1 结论摘要
    rep.append("## 结论摘要")
    rep.append("")
    rep.append("- 门店：%s" % (gym if filled(gym) else "未填写"))
    rep.append("- 课程类型：%s" % (course if filled(course) else "未填写"))
    rep.append("- 合同金额：%s；已付：%s" % (money(total_amt) if total_amt is not None else "未填写",
                                   money(paid) if paid is not None else "未填写"))
    rep.append("- 主体核查：%s" % ent_status)
    rep.append("- 门店现状：%s" % (status_now if filled(status_now) else "未填写"))
    rep.append("- 参考应退：%s" % (money(round(refund, 2)) if refund is not None else "无法测算"))
    rep.append("- 高危项 %d 项 / 风险项 %d 项" % (len(crit), len(risk)))
    rep.append("- **总体结论：%s**" % verdict)
    rep.append("")

    # 2 主体
    rep.append("## 合同主体与资质核查")
    rep.append("")
    for it in ent_items:
        rep.append("- %s" % it)
    rep.append("- 查询入口：国家企业信用信息公示系统（查主体存续与经营异常）；"
               "付款凭证上的收款方名称是最直接的证据")
    rep.append("")

    # 3 条款
    rep.append("## 退费条款效力核查")
    rep.append("")
    for it in t_items:
        rep.append("- %s" % it)
    for c in t_crit:
        rep.append("- **%s**" % c)
    for r in t_risk:
        rep.append("- %s" % r)
    rep.append("")

    # 4 课时与退费
    rep.append("## 课时与退费测算")
    rep.append("")
    for it in refund_items:
        rep.append("- %s" % it)
    if refund is None and not core_missing:
        rep.append("- 需补齐购课总节数与已上节数后才能给出数值")
    rep.append("")

    # 5 有效期与变更
    rep.append("## 有效期、教练变更与门店变更")
    rep.append("")
    for it in v_items:
        rep.append("- %s" % it)
    for c in v_crit:
        rep.append("- **%s**" % c)
    for r in v_risk:
        rep.append("- %s" % r)
    rep.append("")

    # 6 证据
    rep.append("## 证据清单与固定要点")
    rep.append("")
    if have_ev:
        rep.append("已具备：")
        for h in have_ev:
            rep.append("- %s" % h)
    else:
        rep.append("- 采集表未填写任何已留存证据")
    rep.append("")
    if miss_ev:
        rep.append("仍缺失：")
        for m in miss_ev:
            rep.append("- **%s**" % m)
    else:
        rep.append("- 主要证据类别已覆盖，仍需确认原件与截图时间")
    rep.append("")
    rep.append("固定要点：剩余节数要在系统里截图并注明时间；销售口头承诺用微信文字复述请对方确认；"
               "书面申请用 EMS 寄到合同主体注册地址。")
    rep.append("")

    # 7 路径
    rep.append("## 维权路径")
    rep.append("")
    rep.append("| 层级 | 找谁 | 适用 |")
    rep.append("| --- | --- | --- |")
    rep.append("| 1 | 门店/机构书面申请退费 | 全部情形，先书面留痕 |")
    rep.append("| 2 | 第三方平台介入 | 经平台下单的 |")
    rep.append("| 3 | 12315 投诉 | 拒退、不公平格式条款、虚假承诺 |")
    rep.append("| 4 | 当地商务主管部门 | 单用途商业预付卡（储值卡、年卡） |")
    rep.append("| 5 | 消费者协会调解 | 仍有协商空间 |")
    rep.append("| 6 | 人民法院起诉/小额诉讼 | 金额明确、协商不成 |")
    rep.append("")
    if closed:
        rep.append("- 门店已停业或失联：不要单人反复上门，联合其他会员统计人数与金额，"
                   "投诉与报案同步推进")
    if yesno(get_text(f, "是否已投诉")) is True:
        rep.append("- 已申报投诉，请保留受理编号与处理时限")
    else:
        rep.append("- 尚未投诉：先补书面申请与 EMS 面单，再进 12315")
    rep.append("")

    # 8 待办
    rep.append("## 待办补正动作")
    rep.append("")
    if core_missing:
        todo.append("补齐「已付金额」或「合同总金额」——这是出具任何结论的前提")
    if not filled(get_text(f, "合同主体")) or not filled(get_text(f, "实际收款主体")):
        todo.append("核对合同主体与付款凭证上的收款方名称，两家都要列入主张对象")
    if not filled(get_text(f, "购课总节数")) or not filled(get_text(f, "已上节数")):
        todo.append("截图固定系统内的购课总节数、已上节数与剩余节数")
    if yesno(get_text(f, "是否书面提出退费")) is not True:
        todo.append("用 EMS 向合同主体注册地址寄送书面退费申请，保留面单与签收记录")
    if not filled(get_text(f, "退款条款摘录")):
        todo.append("调取合同原件，逐条摘录退费、有效期、违约责任条款")
    for m in miss_ev:
        todo.append("补齐证据：%s" % m)
    if coach is True and assigned is True and agree is None:
        todo.append("对更换教练明确表态并书面留痕——不接受就第一时间提出")
    if not filled(demand):
        todo.append("明确诉求：退还未消费部分 / 顺延有效期 / 转卡 / 解除合同")
    if not todo:
        todo.append("信息已较完整，可直接进入书面协商，不成按维权路径升级")
    for i, t in enumerate(todo, 1):
        rep.append("%d. %s" % (i, t))
    rep.append("")

    # 9 边界
    rep.append("## 边界与纪律")
    rep.append("")
    rep.append("- 本结果依通用规则整理，不替代专业法律意见，"
               "最终以市场监管部门、商务主管部门及司法机关认定为准。")
    rep.append("- 「参考应退」是按课时与单节价推算的**参考值**，违约金是否扣除以协商或裁判为准。")
    rep.append("- 主张退费的诉讼时效为三年，不要无限期拖延；门店出现转让或停业传闻时应立即书面主张。")
    rep.append("- 本技能不提供任何代办投诉、代写诉状或代为谈判服务。")

    return "\n".join(rep), verdict, crit + risk, todo


def main():
    ap = argparse.ArgumentParser(description="健身房私教课退费与套路识别核查")
    ap.add_argument("md", nargs="?", default="样例.md")
    ap.add_argument("--input", dest="input", default=None)
    ap.add_argument("--base", default=None, help="基准日期 YYYY-MM-DD")
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    path = args.input or args.md
    base = parse_date(args.base) if args.base else date.today()

    if not path or not os.path.exists(path):
        msg = "采集表不存在：%s" % path
        print(json.dumps({"错误": msg, "结论": "待补正"}, ensure_ascii=False) if args.json else msg)
        return 2
    f = parse_md(path)
    if not f:
        msg = "采集表为空或格式无法解析，请用「| 字段 | 值 |」或「字段：值」格式填写"
        print(json.dumps({"错误": msg, "结论": "待补正"}, ensure_ascii=False) if args.json else msg)
        return 2

    report, verdict, issues, todo = build_report(f, base)

    if args.json:
        print(json.dumps({"结论": verdict, "风险项": issues, "待办": todo, "报告": report},
                         ensure_ascii=False, indent=2))
    else:
        print(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report)

    if parse_num(get_text(f, "已付金额")) is None and parse_num(get_text(f, "合同总金额")) is None:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
