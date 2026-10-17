# -*- coding: utf-8 -*-
"""物业费争议费用核算与拒缴抗辩核查工具。

用法:
  python fee_check.py --file 催缴单.txt --area 89.6 --unit 2.5 --from 2021-03 --to 2025-12
                      [--rate-daily 0.0005] [--delivery-date 2021-01-15] [--as-of 2026-10-08]
                      [--out out.md] [--format md|json]
  python fee_check.py --selftest
"""
import argparse
import datetime
import json
import os
import re
import sys

LIMIT_YEARS = 3

EVIDENCE = [
    ("物业服务合同", "物业服务合同|前期物业|服务合同|委托合同"),
    ("不动产权证或测绘面积", "不动产权|产权证|测绘|建筑面积|权证"),
    ("欠费明细单", "明细|清单|台账|欠费|催缴单|缴费通知"),
    ("交房交付文件", "交房|交付|收房|交付通知|验收|交付书"),
    ("催缴函与签收凭证", "催缴|催收|律师函|EMS|签收|送达"),
    ("缴费记录", "已缴|实缴|缴费记录|收据|凭证|转账"),
    ("收费公示", "公示|收费标准|明码标价|价格公示"),
    ("服务瑕疵记录", "报修|投诉|照片|视频|整改|回访"),
]

A_KEYS = ["未交付", "尚未交付", "未交房", "重复计费", "未经业主大会", "无进驻依据", "已超时效", "无约定"]
B_KEYS = ["服务不到位", "保洁不到位", "维修拖延", "报修未处理", "安保缺位", "电梯故障",
          "未处理", "未公示", "收费未公示", "空置", "擅自涨价", "消防隐患"]
C_KEYS = ["长期不住", "不用电梯", "服务态度", "别人也没交", "找租客", "开发商遗留", "我没签"]

NEG_DELIVERY = ["未交房", "尚未交付", "未交付", "没有交付"]
NEG_NOTICE = ["未收到催缴", "未收到催收", "未签收", "没有收到催缴", "从未催收"]
NEG_SERVICE = ["未提供", "不到位", "未处理", "未解决", "未回应", "尚未整改"]

CLAIM_WORDS = ["催缴", "催收", "律师函", "催款"]
ACK_WORDS = ["签收", "送达", "收到", "书面确认", "复函确认"]
NEG_PREFIX = ["未", "没", "尚未", "从未", "没有", "并不", "无从"]

SPLIT = re.compile("[。；，！？,;\n]")


def norm(s):
    return (s or "").replace(" ", "").replace("\u3000", "")


def parse_month(s):
    m = re.match(r"^(20\d{2})-(\d{1,2})$", s.strip())
    if not m:
        raise ValueError("bad month: %s" % s)
    return int(m.group(1)), int(m.group(2))


def month_range(start, end):
    (y1, m1) = start
    (y2, m2) = end
    out = []
    y, m = y1, m1
    while (y, m) <= (y2, m2):
        out.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def due_date(y, m):
    if m == 12:
        return datetime.date(y, 12, 31)
    return datetime.date(y, m + 1, 1) - datetime.timedelta(days=1)


def build_ledger(area, unit, start, end, delivery=None, as_of=None, paid_months=0):
    rows = []
    for (y, m) in month_range(start, end):
        due = due_date(y, m)
        owner = "建设单位承担待核实" if (delivery is not None and due < delivery) else "业主"
        days = (as_of - due).days if as_of is not None else None
        rows.append({
            "period": "%04d-%02d" % (y, m),
            "due": due.isoformat(),
            "amount": area * unit,
            "owner": owner,
            "days_since_due": days,
            "over_limit": bool(days is not None and days > LIMIT_YEARS * 365),
        })
    for r in rows[:paid_months]:
        r["amount"] = 0.0
        r["owner"] = "已缴纳"
        r["over_limit"] = False
    return rows


def lateness_rate_check(rate_daily):
    annual = rate_daily * 365 * 100
    if rate_daily <= 0.0003:
        level = "常规"
    elif rate_daily <= 0.0005:
        level = "偏高"
    elif rate_daily <= 0.001:
        level = "明显偏高"
    else:
        level = "畸高"
    return annual, level


def interest_over_principal(principal, rate_daily, days):
    return principal * rate_daily * days


def grade_defenses(text):
    t = norm(text)
    out = []
    for keys, lv in ((A_KEYS, "A"), (B_KEYS, "B"), (C_KEYS, "C")):
        for k in keys:
            if k in t:
                out.append((k, lv))
    return out


def ack_hits(seg):
    hits = []
    for w in ACK_WORDS:
        i = seg.find(w)
        while i >= 0:
            pre = seg[max(0, i - 3):i]
            if not any(n in pre for n in NEG_PREFIX):
                hits.append(w)
            i = seg.find(w, i + 1)
    return hits


def find_interrupts(text):
    t = norm(text)
    out = []
    for seg in SPLIT.split(t):
        if len(seg) < 4:
            continue
        if not any(w in seg for w in CLAIM_WORDS):
            continue
        hits = ack_hits(seg)
        if hits:
            out.append((seg[:40], hits[0]))
    return out


def scan_negatives(text):
    t = norm(text)
    hits = {"delivery": [], "notice": [], "service": [], "interrupt": []}
    for w in NEG_DELIVERY:
        if w in t:
            hits["delivery"].append(w)
    for w in NEG_NOTICE:
        if w in t:
            hits["notice"].append(w)
    for w in NEG_SERVICE:
        if w in t:
            hits["service"].append(w)
    for seg, _w in find_interrupts(t):
        hits["interrupt"].append(seg)
    return hits


def scan_evidence(text):
    t = norm(text)
    return [(n, "有" if re.search(p, t) else "缺") for n, p in EVIDENCE]


def money(x):
    return "%.2f" % x


def summarize(rows):
    total = sum(r["amount"] for r in rows)
    undisputed = sum(r["amount"] for r in rows if not r["over_limit"] and r["owner"] == "业主")
    return total, undisputed, total - undisputed


def render_md(text, rows, rate_daily, args):
    annual, level = lateness_rate_check(rate_daily)
    total, undisputed, disputed = summarize(rows)
    hits = scan_negatives(text)
    lines = ["# 物业费争议与拒缴抗辩核查结果", ""]
    lines.append("核算基准日：%s" % (args.as_of or datetime.date.today().isoformat()))
    lines.append("")
    lines.append("## 一、结论先行")
    lines.append("")
    lines.append("- 台账合计本金：**%s 元**" % money(total))
    lines.append("- 时效内核算金额：**%s 元**（建议作为核算基数）" % money(undisputed))
    lines.append("- 争议／待核实金额：**%s 元**" % money(disputed))
    if hits["delivery"]:
        lines.append("- 检出未交付类表述：%s —— **不得**直接认定业主承担" % "、".join(hits["delivery"]))
    if hits["notice"]:
        lines.append("- 检出未收到催缴类表述：%s —— **不得**认定为时效已中断" % "、".join(hits["notice"]))
    if hits["interrupt"]:
        lines.append("- 检出中断事由：%s —— 从中断日重新计算三年" % "；".join(hits["interrupt"][:3]))
    if hits["service"]:
        lines.append("- 检出服务瑕疵类表述：%s —— 属 B 级（可争取减免），不等于可全额免除"
                     % "、".join(hits["service"]))
    lines.append("")
    lines.append("## 二、滞纳金合理性")
    lines.append("")
    lines.append("| 项目 | 数值 |")
    lines.append("|---|---|")
    lines.append("| 约定日利率 | %g%%" % (rate_daily * 100))
    lines.append("| 年化换算 | 约 %s%%" % money(annual))
    lines.append("| 风险级别 | **%s**" % level)
    lines.append("")
    sp = rows[0]["amount"] if rows else 0.0
    lines.append("以单月 %s 元、逾期 365 天为例，滞纳金约 %s 元。"
                 % (money(sp), money(interest_over_principal(sp, rate_daily, 365))))
    if level in ("明显偏高", "畸高"):
        lines.append("")
        lines.append("**建议：**该利率档次的滞纳金被调整的可能性较高，建议以实际损失为口径主张调减。")
    lines.append("")
    lines.append("## 三、证据要件")
    lines.append("")
    lines.append("| # | 要件 | 状态 |")
    lines.append("|---|---|---|")
    for i, (n, st) in enumerate(scan_evidence(text), 1):
        lines.append("| %d | %s | %s |" % (i, n, st))
    lines.append("")
    lines.append("## 四、抗辩事由分级")
    lines.append("")
    ds = grade_defenses(text)
    if not ds:
        lines.append("未抽取到明确抗辩事由，请回到 rules/defense_grounds.md 逐条对照。")
    else:
        lines.append("| # | 事由 | 级别 | 含义 |")
        lines.append("|---|---|---|---|")
        meaning = {"A": "可主张免除", "B": "可主张减免", "C": "不成立，不要写入结论"}
        for i, (k, lv) in enumerate(ds, 1):
            lines.append("| %d | %s | %s | %s |" % (i, k, lv, meaning[lv]))
    lines.append("")
    lines.append("## 五、欠费台账")
    lines.append("")
    lines.append("| # | 期间 | 到期日 | 金额（元） | 承担主体 | 距今天数 | 时效状态 |")
    lines.append("|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        st = "已过三年" if r["over_limit"] else "时效内"
        days = r["days_since_due"] if r["days_since_due"] is not None else "-"
        lines.append("| %d | %s | %s | %s | %s | %s | %s |" % (
            i, r["period"], r["due"], money(r["amount"]), r["owner"], days, st))
    over = sum(1 for r in rows if r["over_limit"] and r["amount"] > 0)
    if over:
        lines.append("")
        lines.append("超过三年且未见中断事由的期数：%d 期，可在诉讼中提出时效抗辩。" % over)
    lines.append("")
    lines.append("---")
    lines.append("本结果为费用核算与材料整理产物，不构成法律意见。口径以现行规定和当地主管部门要求为准。")
    return "\n".join(lines)


def render_json(text, rows, rate_daily, args):
    annual, level = lateness_rate_check(rate_daily)
    total, undisputed, disputed = summarize(rows)
    return json.dumps({
        "as_of": args.as_of or datetime.date.today().isoformat(),
        "total": total,
        "undisputed": undisputed,
        "disputed": disputed,
        "late": {"rate_daily": rate_daily, "annual_percent": annual, "level": level},
        "evidence": [{"name": n, "status": s} for n, s in scan_evidence(text)],
        "defenses": [{"ground": k, "level": lv} for k, lv in grade_defenses(text)],
        "negatives": scan_negatives(text),
        "ledger": rows,
    }, ensure_ascii=False, indent=2)


SAMPLE_FULL = """
物业服务合同编号 WY-2019-004，前期物业服务合同已备案。
不动产权证记载建筑面积 89.60 平方米，测绘面积一致。
2021 年 3 月至 2025 年 12 月欠费明细单已收到。
交房日期 2021-01-15，交付通知书与验收单齐备。
2023-08-10 物业公司发出催缴函并由业主签收。
业主已缴纳前 12 个月费用。
小区公共部位维修长期未处理，报修单 5 张。
2024 年物业费收费标准已在小区公示。
"""

SAMPLE_NEG = """
房屋未交付，开发商未完成交房手续。
业主从未催收，未收到催缴函，也从未签收。
小区保洁未提供，消防设施长期未整改。
业主长期不住，不用电梯，认为不该缴费。
"""


def selftest():
    ok = True
    res = []

    def ck(name, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        res.append("%s %s got=%s want=%s" % ("PASS" if good else "FAIL", name, got, want))

    rows = build_ledger(89.6, 2.5, (2021, 1), (2021, 12))
    ck("ledger_len_12", len(rows), 12)
    ck("monthly_amount", money(rows[0]["amount"]), "224.00")

    rows2 = build_ledger(89.6, 2.5, (2021, 1), (2021, 12), delivery=datetime.date(2021, 7, 1))
    ck("pre_delivery_months", len([r for r in rows2 if r["owner"] == "建设单位承担待核实"]), 6)

    rows3 = build_ledger(89.6, 2.5, (2021, 1), (2021, 12), paid_months=2)
    ck("paid_first_zero", money(rows3[0]["amount"]), "0.00")
    ck("third_still_owed", money(rows3[2]["amount"]), "224.00")

    t, u, d = summarize(build_ledger(89.6, 2.5, (2021, 1), (2021, 12)))
    ck("sum_total", money(t), "2688.00")
    ck("sum_split", money(u + d), "2688.00")

    as_of = datetime.date(2026, 10, 8)
    rows5 = build_ledger(100.0, 2.0, (2021, 1), (2022, 12), as_of=as_of)
    ck("all_over_limit_before_2023", len([r for r in rows5 if r["over_limit"]]), 24)
    rows6 = build_ledger(100.0, 2.0, (2025, 1), (2025, 12), as_of=as_of)
    ck("none_over_limit_2025", len([r for r in rows6 if r["over_limit"]]), 0)

    ck("rate_normal", lateness_rate_check(0.0003)[1], "常规")
    ck("rate_high", lateness_rate_check(0.0005)[1], "偏高")
    ck("rate_very_high", lateness_rate_check(0.001)[1], "明显偏高")
    ck("rate_extreme", lateness_rate_check(0.003)[1], "畸高")
    ck("extreme_annual_gt_100", lateness_rate_check(0.003)[0] > 100, True)
    ck("interest_calc", money(interest_over_principal(1000.0, 0.0005, 365)), "182.50")

    ck("evidence_all_present", all(s == "有" for _, s in scan_evidence(SAMPLE_FULL)), True)
    ck("evidence_partial", all(s == "有" for _, s in scan_evidence(SAMPLE_NEG)), False)

    ds = dict(grade_defenses(SAMPLE_NEG))
    ck("neg_has_A", ds.get("未交付"), "A")
    ck("neg_has_C", ds.get("长期不住"), "C")
    ck("full_has_B", dict(grade_defenses(SAMPLE_FULL)).get("未处理"), "B")

    h = scan_negatives(SAMPLE_NEG)
    ck("neg_delivery_hit", len(h["delivery"]) > 0, True)
    ck("neg_notice_hit", len(h["notice"]) > 0, True)
    ck("neg_service_hit", len(h["service"]) > 0, True)
    ck("neg_no_interrupt", len(h["interrupt"]), 0)

    h2 = scan_negatives(SAMPLE_FULL)
    ck("full_interrupt_hit", len(h2["interrupt"]) > 0, True)
    ck("full_no_delivery_neg", len(h2["delivery"]), 0)

    ck("ack_not_negated", len(ack_hits("从未催收，未签收催缴函")), 0)
    ck("ack_not_double_neg", len(ack_hits("从未收到催缴函")), 0)
    ck("ack_positive_ok", len(ack_hits("2023-08-10 物业公司发出催缴函并由业主签收")) >= 1, True)

    class A(object):
        pass

    args = A()
    args.as_of = "2026-10-08"
    md = render_md(SAMPLE_FULL, rows5, 0.0005, args)
    ck("md_has_header", md.startswith("# "), True)
    js = json.loads(render_json(SAMPLE_FULL, rows5, 0.0005, args))
    ck("json_keys", sorted(js.keys()),
       ["as_of", "defenses", "disputed", "evidence", "late", "ledger",
        "negatives", "total", "undisputed"])

    for line in res:
        print(line)
    print("SELFTEST %s" % ("OK" if ok else "FAILED"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--area", type=float, default=0.0)
    ap.add_argument("--unit", type=float, default=0.0)
    ap.add_argument("--from", dest="frm", default="")
    ap.add_argument("--to", default="")
    ap.add_argument("--paid-months", type=int, default=0)
    ap.add_argument("--rate-daily", type=float, default=0.0005)
    ap.add_argument("--delivery-date", default="")
    ap.add_argument("--as-of", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--format", default="md", choices=["md", "json"])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    if not a.file or not os.path.exists(a.file):
        print("ERROR --file not found")
        return 2
    if a.area <= 0 or a.unit <= 0:
        print("ERROR --area and --unit must be positive")
        return 2
    if not a.frm or not a.to:
        print("ERROR --from and --to required, format 2021-03")
        return 2

    text = open(a.file, "r", encoding="utf-8", errors="replace").read()

    delivery = None
    if a.delivery_date:
        y, m, d = [int(x) for x in re.split(r"[-/]", a.delivery_date)[:3]]
        delivery = datetime.date(y, m, d)

    if a.as_of:
        y, m, d = [int(x) for x in re.split(r"[-/]", a.as_of)[:3]]
        as_of = datetime.date(y, m, d)
    else:
        as_of = datetime.date.today()

    rows = build_ledger(a.area, a.unit, parse_month(a.frm), parse_month(a.to),
                        delivery=delivery, as_of=as_of, paid_months=a.paid_months)

    body = render_md(text, rows, a.rate_daily, a) if a.format == "md" \
        else render_json(text, rows, a.rate_daily, a)

    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(body)
        print("WROTE %s" % a.out)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
