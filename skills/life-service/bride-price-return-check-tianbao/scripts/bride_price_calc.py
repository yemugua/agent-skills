# -*- coding: utf-8 -*-
"""\u5f69\u793c\u8fd4\u8fd8\u60c5\u5f62\u4e0e\u6bd4\u4f8b\u6838\u7b97\u5de5\u5177\u3002

\u7528\u6cd5:
  python bride_price_calc.py --file \u5f69\u793c.json [--json]
  python bride_price_calc.py --selftest

\u8f93\u51fa\u6bd4\u4f8b\u533a\u95f4\u4f30\u7b97\uff0c\u4e0d\u662f\u88c1\u5224\u7ed3\u8bba\u3002
"""
import argparse
import io
import json
import os
import sys

# \u57fa\u51c6\u6bd4\u4f8b\u533a\u95f4: (\u4e0a\u9650\u6708\u6570, \u4e0b\u9650\u6bd4\u4f8b, \u4e0a\u9650\u6bd4\u4f8b)\uff0c\u6309\u6708\u6570\u5347\u5e8f\u5339\u914d
BASE_RATIO = [
    (0, 0.80, 1.00),
    (3, 0.70, 0.90),
    (12, 0.50, 0.70),
    (24, 0.30, 0.50),
    (10 ** 9, 0.00, 0.30),
]

ADJ_REGISTERED = -0.15
ADJ_CHILD = -0.25
ADJ_PAYER_FAULT = {0: 0.0, 1: -0.05, 2: -0.15}
ADJ_RECEIVER_FAULT = {0: 0.0, 1: 0.05, 2: 0.15}
ADJ_HARDSHIP = 0.10


def base_ratio(months):
    """\u6309\u5171\u540c\u751f\u6d3b\u6708\u6570\u53d6\u57fa\u51c6\u6bd4\u4f8b\u533a\u95f4\u3002"""
    months = float(months or 0)
    for limit, low, high in BASE_RATIO:
        if months <= limit:
            return low, high
    return 0.0, 0.30


def _clamp(v):
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def gate_check(registered, cohabitation_months, payer_hardship, divorce):
    """\u4e09\u79cd\u6cd5\u5b9a\u60c5\u5f62\u95e8\u69db\u5224\u5b9a\u3002\u8fd4\u56de (\u662f\u5426\u6210\u7acb, \u6210\u7acb\u60c5\u5f62\u5217\u8868, \u8bf4\u660e)\u3002"""
    months = float(cohabitation_months or 0)
    reasons = []
    notes = []

    if not registered:
        reasons.append("\u60c5\u5f62\u4e00\uff1a\u672a\u529e\u7406\u7ed3\u5a5a\u767b\u8bb0")
        return True, reasons, notes

    if not divorce:
        notes.append("\u5df2\u529e\u7406\u7ed3\u5a5a\u767b\u8bb0\u4f46\u672a\u79bb\u5a5a\uff1a\u60c5\u5f62\u4e8c\u3001\u4e09\u5747\u4ee5\u79bb\u5a5a\u4e3a\u6761\u4ef6\uff0c\u76ee\u524d\u4e0d\u6210\u7acb")
        return False, reasons, notes

    if months <= 0:
        reasons.append("\u60c5\u5f62\u4e8c\uff1a\u5df2\u767b\u8bb0\u4f46\u786e\u672a\u5171\u540c\u751f\u6d3b\uff0c\u4e14\u5df2\u79bb\u5a5a")

    if payer_hardship:
        reasons.append("\u60c5\u5f62\u4e09\uff1a\u5a5a\u524d\u7ed9\u4ed8\u5bfc\u81f4\u7ed9\u4ed8\u4eba\u751f\u6d3b\u56f0\u96be\uff0c\u4e14\u5df2\u79bb\u5a5a")

    if reasons:
        return True, reasons, notes

    notes.append("\u5df2\u767b\u8bb0\u4e14\u5df2\u5171\u540c\u751f\u6d3b\uff0c\u4e14\u4e0d\u6784\u6210\u751f\u6d3b\u56f0\u96be\uff1a\u5f69\u793c\u8fd4\u8fd8\u4e00\u822c\u4e0d\u4e88\u652f\u6301\uff0c\u5e94\u8d70\u5171\u540c\u8d22\u4ea7\u5206\u5272")
    return False, reasons, notes


def build_report(data):
    total = float(data.get("total", 0) or 0)
    registered = bool(data.get("registered", False))
    months = float(data.get("cohabitation_months", 0) or 0)
    has_child = bool(data.get("has_child", False))
    used_for_common = float(data.get("used_for_common", 0) or 0)
    payer_fault = int(data.get("payer_fault", 0) or 0)
    receiver_fault = int(data.get("receiver_fault", 0) or 0)
    hardship = bool(data.get("payer_hardship", False))
    divorce = bool(data.get("divorce", False))

    passed, reasons, notes = gate_check(registered, months, hardship, divorce)
    low, high = base_ratio(months)

    adjusts = []
    if registered:
        adjusts.append(("\u5df2\u529e\u7406\u7ed3\u5a5a\u767b\u8bb0", ADJ_REGISTERED))
    if has_child:
        adjusts.append(("\u5df2\u751f\u80b2\u5b50\u5973", ADJ_CHILD))
    if payer_fault:
        adjusts.append(("\u7ed9\u4ed8\u65b9\u5b58\u5728\u8fc7\u9519\uff08\u7b49\u7ea7%d\uff09" % payer_fault, ADJ_PAYER_FAULT.get(payer_fault, 0.0)))
    if receiver_fault:
        adjusts.append(("\u6536\u53d7\u65b9\u5b58\u5728\u8fc7\u9519\uff08\u7b49\u7ea7%d\uff09" % receiver_fault, ADJ_RECEIVER_FAULT.get(receiver_fault, 0.0)))
    if hardship:
        adjusts.append(("\u6784\u6210\u751f\u6d3b\u56f0\u96be", ADJ_HARDSHIP))

    delta = sum(v for _, v in adjusts)
    adj_low = _clamp(low + delta)
    adj_high = _clamp(high + delta)
    if adj_low > adj_high:
        adj_low = adj_high

    base_amount = max(0.0, total - used_for_common)
    refund_low = base_amount * adj_low
    refund_high = base_amount * adj_high

    lines = []
    lines.append("=" * 60)
    lines.append("\u5f69\u793c\u8fd4\u8fd8\u60c5\u5f62\u4e0e\u6bd4\u4f8b \u6838\u7b97\u7ed3\u679c")
    lines.append("=" * 60)
    lines.append("\u6838\u5b9a\u5f69\u793c\u603b\u989d\uff1a%.2f \u5143" % total)
    lines.append("\u662f\u5426\u767b\u8bb0\uff1a%s   \u5171\u540c\u751f\u6d3b\uff1a%g \u4e2a\u6708   \u662f\u5426\u79bb\u5a5a\uff1a%s" % (
        "\u662f" if registered else "\u5426", months, "\u662f" if divorce else "\u5426"))
    lines.append("\u662f\u5426\u751f\u80b2\u5b50\u5973\uff1a%s   \u662f\u5426\u6784\u6210\u751f\u6d3b\u56f0\u96be\uff1a%s" % ("\u662f" if has_child else "\u5426", "\u662f" if hardship else "\u5426"))
    lines.append("")
    lines.append("[\u4e00] \u60c5\u5f62\u95e8\u69db\u5224\u5b9a")
    if passed:
        lines.append("  \u7ed3\u8bba\uff1a%s" % "\u60c5\u5f62\u6210\u7acb")
        for r in reasons:
            lines.append("    - %s" % r)
    else:
        lines.append("  \u7ed3\u8bba\uff1a\u60c5\u5f62\u6210\u7acb\u4f9d\u636e\u4e0d\u8db3")
        for n in notes:
            lines.append("    - %s" % n)
    lines.append("")
    lines.append("[\u4e8c] \u53ef\u8fd4\u8fd8\u57fa\u6570")
    lines.append("  \u6838\u5b9a\u5f69\u793c\u603b\u989d          %.2f \u5143" % total)
    lines.append("  \u51cf\uff1a\u5df2\u7528\u4e8e\u5171\u540c\u751f\u6d3b    %.2f \u5143" % used_for_common)
    lines.append("  \u53ef\u8fd4\u8fd8\u57fa\u6570            %.2f \u5143" % base_amount)
    lines.append("")
    lines.append("[\u4e09] \u6bd4\u4f8b\u6838\u7b97")
    lines.append("  \u57fa\u51c6\u533a\u95f4\uff08\u6309\u5171\u540c\u751f\u6d3b %g \u4e2a\u6708\uff09\uff1a%.0f%% ~ %.0f%%" % (months, low * 100, high * 100))
    if adjusts:
        for name, v in adjusts:
            lines.append("  \u8c03\u6574\uff1a%s  %+0.0f%%" % (name, v * 100))
    else:
        lines.append("  \u8c03\u6574\uff1a\u65e0")
    lines.append("  \u8c03\u6574\u540e\u533a\u95f4\uff1a%.0f%% ~ %.0f%%" % (adj_low * 100, adj_high * 100))
    lines.append("")
    lines.append("[\u56db] \u8fd4\u8fd8\u91d1\u989d\u533a\u95f4")
    if passed:
        lines.append("  %.2f \u5143  ~  %.2f \u5143" % (refund_low, refund_high))
    else:
        lines.append("  \u60c5\u5f62\u6210\u7acb\u4f9d\u636e\u4e0d\u8db3\uff0c\u8fd4\u8fd8\u91d1\u989d\u533a\u95f4\u4e3a 0 \u5143 ~ 0 \u5143")
        lines.append("  \u5efa\u8bae\u8f6c\u5411\uff1a\u592b\u59bb\u5171\u540c\u8d22\u4ea7\u5206\u5272 / \u5148\u5b8c\u6210\u79bb\u5a5a\u7a0b\u5e8f")
        refund_low = 0.0
        refund_high = 0.0
    lines.append("")
    lines.append("[\u4e94] \u5173\u952e\u63d0\u793a")
    lines.append("  1. \u672c\u7ed3\u679c\u4e3a\u533a\u95f4\u4f30\u7b97\uff0c\u4e0d\u662f\u88c1\u5224\u7ed3\u8bba\uff0c\u5404\u5730\u6cd5\u9662\u638c\u63e1\u5b58\u5728\u5dee\u5f02")
    lines.append("  2. \u6838\u5b9a\u603b\u989d\u53ea\u5e94\u5305\u542b\u5f69\u793c\u6027\u8d28\u7684\u7ed9\u4ed8\uff0c\u604b\u7231\u671f\u95f4\u4e00\u822c\u8d60\u4e0e\u987b\u5254\u9664")
    lines.append("  3. \u5ac1\u5986\u72ec\u7acb\u5904\u7406\uff0c\u4e0d\u5f97\u7528\u4e8e\u62b5\u6263\u5f69\u793c")
    lines.append("  4. \u5df2\u8f6c\u5316\u4e3a\u5171\u540c\u8d22\u4ea7\u7684\u90e8\u5206\u4e0d\u5f97\u5728\u5f69\u793c\u8fd4\u8fd8\u4e2d\u91cd\u590d\u4e3b\u5f20")
    lines.append("  5. \u751f\u6d3b\u56f0\u96be\u662f\u9ad8\u6807\u51c6\uff1a\u65e0\u6cd5\u7ef4\u6301\u5f53\u5730\u57fa\u672c\u751f\u6d3b\u6c34\u5e73\uff0c\u4e0d\u662f\u624b\u5934\u7d27")
    lines.append("  6. \u88ab\u544a\u5e94\u5217\u5b9e\u9645\u6536\u53d7\u4eba\uff0c\u539f\u544a\u5e94\u5217\u5b9e\u9645\u7ed9\u4ed8\u4eba")
    lines.append("  7. \u8bc9\u8bbc\u65f6\u6548\u4e00\u822c\u4e3a\u4e09\u5e74\uff0c\u81ea\u5a5a\u7ea6\u89e3\u9664\u6216\u79bb\u5a5a\u65f6\u8d77\u7b97\uff08\u4ee5\u73b0\u884c\u89c4\u5b9a\u4e3a\u51c6\uff09")
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u6bd4\u4f8b\u533a\u95f4\u4f30\u7b97\uff0c\u4e0d\u6784\u6210\u6cd5\u5f8b\u610f\u89c1\u6216\u88c1\u5224\u7ed3\u8bba\u3002")
    lines.append("=" * 60)

    summary = {
        "total": total,
        "registered": registered,
        "cohabitation_months": months,
        "has_child": has_child,
        "divorce": divorce,
        "gate_passed": passed,
        "gate_reasons": reasons,
        "gate_notes": notes,
        "base_amount": round(base_amount, 4),
        "base_ratio": [round(low, 4), round(high, 4)],
        "adjusts": [{"name": n, "delta": round(v, 4)} for n, v in adjusts],
        "adjusted_ratio": [round(adj_low, 4), round(adj_high, 4)],
        "refund_range": [round(refund_low, 4), round(refund_high, 4)],
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []

    # 1) \u57fa\u51c6\u6bd4\u4f8b\uff1a0 \u4e2a\u6708
    lo, hi = base_ratio(0)
    r.append(("\u672a\u5171\u540c\u751f\u6d3b\u57fa\u51c6 80%~100%", abs(lo - 0.8) < 1e-9 and abs(hi - 1.0) < 1e-9))

    # 2) 5 \u4e2a\u6708 -> 50%~70%
    lo, hi = base_ratio(5)
    r.append(("5\u4e2a\u6708\u57fa\u51c6 50%~70%", abs(lo - 0.5) < 1e-9 and abs(hi - 0.7) < 1e-9))

    # 3) 14 \u4e2a\u6708 -> 30%~50%
    lo, hi = base_ratio(14)
    r.append(("14\u4e2a\u6708\u57fa\u51c6 30%~50%", abs(lo - 0.3) < 1e-9 and abs(hi - 0.5) < 1e-9))

    # 4) 30 \u4e2a\u6708 -> 0%~30%
    lo, hi = base_ratio(30)
    r.append(("30\u4e2a\u6708\u57fa\u51c6 0%~30%", abs(lo - 0.0) < 1e-9 and abs(hi - 0.3) < 1e-9))

    # 5) \u95e8\u69db\uff1a\u672a\u767b\u8bb0\u6210\u7acb
    ok, reasons, _ = gate_check(False, 5, False, False)
    r.append(("\u672a\u767b\u8bb0\u95e8\u69db\u6210\u7acb", ok and len(reasons) == 1))

    # 6) \u95e8\u69db\uff1a\u5df2\u767b\u8bb0\u672a\u79bb\u5a5a\u4e0d\u6210\u7acb
    ok, _, notes = gate_check(True, 0, False, False)
    r.append(("\u5df2\u767b\u8bb0\u672a\u79bb\u5a5a\u95e8\u69db\u4e0d\u6210\u7acb", (not ok) and len(notes) > 0))

    # 7) \u95e8\u69db\uff1a\u5df2\u767b\u8bb0\u672a\u5171\u540c\u751f\u6d3b\u5df2\u79bb\u5a5a\u6210\u7acb
    ok, reasons, _ = gate_check(True, 0, False, True)
    r.append(("\u60c5\u5f62\u4e8c\u6210\u7acb", ok and len(reasons) == 1))

    # 8) \u95e8\u69db\uff1a\u5df2\u767b\u8bb0\u5171\u540c\u751f\u6d3b\u65e0\u56f0\u96be\u4e0d\u6210\u7acb
    ok, _, notes = gate_check(True, 14, False, True)
    r.append(("\u5df2\u767b\u8bb0\u5171\u540c\u751f\u6d3b\u65e0\u56f0\u96be\u4e0d\u6210\u7acb", (not ok) and len(notes) > 0))

    # 9) \u95e8\u69db\uff1a\u751f\u6d3b\u56f0\u96be\u4e14\u5df2\u79bb\u5a5a\u6210\u7acb
    ok, reasons, _ = gate_check(True, 14, True, True)
    r.append(("\u60c5\u5f62\u4e09\u6210\u7acb", ok and len(reasons) == 1))

    # 10) \u793a\u4f8bA\uff1a\u672a\u767b\u8bb0\uff0c5\u4e2a\u6708\uff0c20\u4e07\uff0c3\u4e07\u5df2\u7528 -> 17\u4e07*50%~70%
    _, s = build_report({"total": 200000, "registered": False, "cohabitation_months": 5,
                         "has_child": False, "used_for_common": 30000, "payer_fault": 0,
                         "receiver_fault": 0, "payer_hardship": False, "divorce": False})
    r.append(("\u793a\u4f8bA\u533a\u95f4", abs(s["refund_range"][0] - 85000.0) < 1e-3
              and abs(s["refund_range"][1] - 119000.0) < 1e-3))

    # 11) \u793a\u4f8bC\uff1a\u5df2\u767b\u8bb0\u672a\u5171\u540c\u751f\u6d3b\u5df2\u79bb\u5a5a\uff0c20\u4e07 -> 65%~85%
    _, s2 = build_report({"total": 200000, "registered": True, "cohabitation_months": 0,
                          "has_child": False, "used_for_common": 0, "payer_fault": 0,
                          "receiver_fault": 0, "payer_hardship": False, "divorce": True})
    r.append(("\u793a\u4f8bC\u533a\u95f4", abs(s2["refund_range"][0] - 130000.0) < 1e-3
              and abs(s2["refund_range"][1] - 170000.0) < 1e-3))

    # 12) \u95e8\u69db\u4e0d\u6210\u7acb\u65f6\u533a\u95f4\u4e3a 0
    _, s3 = build_report({"total": 200000, "registered": True, "cohabitation_months": 14,
                          "has_child": False, "used_for_common": 0, "payer_fault": 0,
                          "receiver_fault": 0, "payer_hardship": False, "divorce": True})
    r.append(("\u95e8\u69db\u4e0d\u6210\u7acb\u533a\u95f4\u4e3a0", s3["refund_range"] == [0.0, 0.0]))

    # 13) \u6bd4\u4f8b\u4e0a\u9650\u4e0d\u8d85\u8fc7 100%\uff0c\u4e0b\u9650\u4e0d\u4f4e\u4e8e 0
    r.append(("\u6bd4\u4f8b\u94b3\u5236\u57280~1", _clamp(1.5) == 1.0 and _clamp(-0.2) == 0.0))

    return r


def selftest():
    results = _run_checks()
    failed = [name for name, ok in results if not ok]
    ok = len(failed) == 0
    lines = ["SELFTEST %s" % ("OK" if ok else "FAILED")]
    lines.append("checks=%d passed=%d failed=%d" % (len(results), len(results) - len(failed), len(failed)))
    for name in failed:
        lines.append("FAILED: %s" % name)
    with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_selftest_result.txt"),
                 "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    return ok


def main():
    parser = argparse.ArgumentParser(description="\u5f69\u793c\u8fd4\u8fd8\u60c5\u5f62\u4e0e\u6bd4\u4f8b\u6838\u7b97\u5de5\u5177")
    parser.add_argument("--file", help="\u5f69\u793c JSON \u6587\u4ef6\u8def\u5f84\uff08UTF-8\uff09")
    parser.add_argument("--json", action="store_true", help="\u4ee5 JSON \u8f93\u51fa")
    parser.add_argument("--out", help="\u7ed3\u679c\u5199\u5165\u6307\u5b9a\u6587\u4ef6")
    parser.add_argument("--selftest", action="store_true", help="\u8fd0\u884c\u81ea\u68c0")
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))

    if args.selftest:
        sys.exit(0 if selftest() else 1)

    if not args.file:
        parser.error("\u9700\u8981 --file \u6216 --selftest")

    with io.open(args.file, "r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)

    report, summary = build_report(data)
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else report
    out_path = args.out or os.path.join(here, "_last_result.txt")
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write(body)
    print(body)
    print("")
    print("\u7ed3\u679c\u5df2\u5199\u5165\uff1a%s" % out_path)


if __name__ == "__main__":
    main()
