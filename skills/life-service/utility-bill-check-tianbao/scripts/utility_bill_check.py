# -*- coding: utf-8 -*-
"""\u6c34\u7535\u8d39\u5f02\u5e38\u6838\u67e5\u4e0e\u9000\u8865\u6838\u7b97\u5de5\u5177\u3002

\u7528\u6cd5:
  python utility_bill_check.py --file \u8d26\u5355.json [--json]
  python utility_bill_check.py --selftest

\u4e0d\u5185\u7f6e\u4efb\u4f55\u5730\u533a\u7684\u6c34\u4ef7\u7535\u4ef7\uff0c\u4ef7\u683c\u4e0e\u9636\u68af\u8868\u7531\u4f7f\u7528\u8005\u6309\u5f53\u5730\u516c\u5e03\u6807\u51c6\u586b\u5165\u3002
"""
import argparse
import io
import json
import os
import sys


def tier_amount(usage, tiers):
    """\u5206\u6bb5\u7d2f\u8fdb\u8ba1\u7b97\u9636\u68af\u91d1\u989d\u3002tiers: [(limit, price), ...]\uff0c\u6700\u540e\u4e00\u6863 limit \u4e3a None\u3002"""
    left = float(usage)
    total = 0.0
    detail = []
    for limit, price in tiers:
        if left <= 0:
            break
        if limit is None:
            part = left
        else:
            part = min(left, float(limit))
        amount = part * float(price)
        total += amount
        detail.append({"usage": round(part, 4), "price": float(price), "amount": round(amount, 4)})
        left -= part
    return total, detail


def year_tier_amount(usage, tiers):
    """\u6309\u5e74\u7d2f\u8ba1\u5206\u6863\uff1a\u7528\u91cf\u843d\u5728\u54ea\u4e00\u6863\uff0c\u8be5\u6863\u533a\u95f4\u5185\u6309\u8be5\u6863\u4ef7\u8ba1\u7b97\uff08\u5206\u6bb5\u7d2f\u8fdb\uff0c\u540c tier_amount\uff09\u3002"""
    return tier_amount(usage, tiers)


def running_total(months):
    out = []
    acc = 0.0
    for m in months:
        acc += float(m.get("usage", 0) or 0)
        out.append(acc)
    return out


def detect_spike(months, threshold=0.5):
    """\u73af\u6bd4\u5f02\u5e38\u68c0\u6d4b\uff1a\u6da8\u5e45\u8d85\u8fc7\u9608\u503c\u4e14\u4e0e\u53bb\u5e74\u540c\u671f\u76f8\u6bd4\u540c\u6837\u5f02\u5e38\u65f6\u6807\u8bb0\u3002"""
    flags = []
    values = [float(m.get("usage", 0) or 0) for m in months]
    for i in range(1, len(values)):
        prev = values[i - 1]
        cur = values[i]
        if prev <= 0:
            continue
        rate = (cur - prev) / prev
        if rate >= threshold:
            flags.append({
                "index": i,
                "label": months[i].get("label", "#%d" % i),
                "prev": prev,
                "cur": cur,
                "rate": round(rate, 4),
            })
    return flags


def year_over_year(months, threshold=0.5):
    """\u540c\u6bd4\u5f02\u5e38\u68c0\u6d4b\uff1a\u4e0e 12 \u4e2a\u6708\u524d\u76f8\u6bd4\u3002"""
    flags = []
    values = [float(m.get("usage", 0) or 0) for m in months]
    for i in range(12, len(values)):
        base = values[i - 12]
        cur = values[i]
        if base <= 0:
            continue
        rate = (cur - base) / base
        if rate >= threshold:
            flags.append({
                "index": i,
                "label": months[i].get("label", "#%d" % i),
                "base": base,
                "cur": cur,
                "rate": round(rate, 4),
            })
    return flags


def meter_error_refund(measured, error_rate):
    """\u8868\u8ba1\u8d85\u5dee\u6298\u7b97\u3002error_rate>0 \u8868\u5feb\uff08\u5e94\u9000\uff09\uff0c<0 \u8868\u6162\uff08\u5e94\u8865\uff09\u3002

    \u5b9e\u9645\u7528\u91cf = measured / (1 + r)
    \u5e94\u9000\u8865\u91cf = measured * r / (1 + r)
    """
    r = float(error_rate)
    if r <= -1.0:
        raise ValueError("error_rate must be > -1")
    actual = measured / (1.0 + r)
    diff = measured - actual
    return {
        "measured": round(measured, 4),
        "error_rate": r,
        "actual": round(actual, 4),
        "diff": round(diff, 4),
        "direction": "\u5e94\u9000\u7ed9\u7528\u6237" if diff > 0 else ("\u5e94\u5411\u7528\u6237\u8865\u6536" if diff < 0 else "\u65e0\u5dee\u989d"),
    }


def late_fee(principal, days, daily_rate=0.001, cap_ratio=0.3):
    """\u8fdd\u7ea6\u91d1\u8ba1\u7b97\uff0c\u542b\u672c\u91d1\u6bd4\u4f8b\u4e0a\u9650\u622a\u65ad\uff0c\u4e14\u4e0d\u8ba1\u6536\u5229\u6eda\u5229\u3002"""
    raw = float(principal) * float(daily_rate) * float(days)
    cap = float(principal) * float(cap_ratio)
    fee = min(raw, cap)
    return {
        "principal": round(principal, 4),
        "days": int(days),
        "daily_rate": float(daily_rate),
        "raw_fee": round(raw, 4),
        "cap": round(cap, 4),
        "fee": round(fee, 4),
        "capped": raw > cap,
    }


def build_report(data):
    tiers = []
    for t in data.get("tiers", []):
        limit = t.get("limit")
        tiers.append((None if limit is None else float(limit), float(t.get("price", 0))))
    months = data.get("months", [])
    cycle = data.get("cycle", "month")
    threshold = float(data.get("spike_threshold", 0.5))

    if not tiers:
        raise ValueError("\u7f3a\u5c11 tiers \u9636\u68af\u8868")

    lines = []
    lines.append("=" * 56)
    lines.append("\u6c34\u7535\u8d39\u5f02\u5e38\u6838\u67e5\u4e0e\u9000\u8865 \u6838\u7b97\u7ed3\u679c")
    lines.append("=" * 56)
    lines.append("\u5206\u6863\u5468\u671f\uff1a%s" % ("\u6309\u6708" if cycle == "month" else "\u6309\u5e74\u7d2f\u8ba1"))
    lines.append("\u73af\u6bd4\u5f02\u5e38\u9608\u503c\uff1a%s%%" % round(threshold * 100, 1))
    lines.append("")

    rows = []
    total_due = 0.0
    total_billed = 0.0
    has_billed = False
    if cycle == "year":
        accs = running_total(months)
    else:
        accs = None

    for i, m in enumerate(months):
        label = m.get("label", "#%d" % (i + 1))
        usage = float(m.get("usage", 0) or 0)
        if cycle == "year":
            # \u6309\u5e74\u7d2f\u8ba1\u5206\u6863\uff1a\u5bf9\u5f53\u5e74\u7d2f\u8ba1\u91cf\u5206\u6863\uff0c\u9010\u6708\u53d6\u5dee\u989d
            prev_acc = accs[i] - usage
            amt_all, _ = tier_amount(accs[i], tiers)
            amt_prev, _ = tier_amount(prev_acc, tiers)
            due = amt_all - amt_prev
            detail_note = "\u5e74\u5185\u7d2f\u8ba1 %.2f" % accs[i]
        else:
            due, _ = tier_amount(usage, tiers)
            detail_note = "\u672c\u6708\u7528\u91cf %.2f" % usage
        billed = m.get("amount")
        if billed is None:
            billed = None
        else:
            billed = float(billed)
            has_billed = True
            total_billed += billed
        total_due += due
        rows.append({
            "label": label,
            "usage": round(usage, 4),
            "due": round(due, 4),
            "billed": None if billed is None else round(billed, 4),
            "diff": None if billed is None else round(billed - due, 4),
            "note": detail_note,
        })

    lines.append("[\u4e00] \u9010\u6708\u6838\u7b97")
    header = "\u6708\u4efd        \u7528\u91cf      \u5e94\u7f34      \u5b9e\u6536      \u5dee\u989d"
    lines.append(header)
    lines.append("-" * 56)
    for r in rows:
        billed_s = "      -" if r["billed"] is None else "%8.2f" % r["billed"]
        diff_s = "      -" if r["diff"] is None else "%8.2f" % r["diff"]
        lines.append("%-10s %8.2f %8.2f %s %s" % (r["label"], r["usage"], r["due"], billed_s, diff_s))
    lines.append("-" * 56)
    lines.append("\u5e94\u7f34\u5408\u8ba1\uff1a%.2f" % total_due)
    if has_billed:
        lines.append("\u5b9e\u6536\u5408\u8ba1\uff1a%.2f" % total_billed)
        lines.append("\u5dee\u989d\u5408\u8ba1\uff08\u6b63\u6570\u4e3a\u591a\u6536\uff09\uff1a%.2f" % (total_billed - total_due))
    lines.append("")

    lines.append("[\u4e8c] \u5f02\u5e38\u6708\u4efd")
    spikes = detect_spike(months, threshold)
    yoy = year_over_year(months, threshold)
    if spikes:
        lines.append("  \u73af\u6bd4\u5f02\u5e38 %d \u4e2a\u6708\uff1a" % len(spikes))
        for s in spikes:
            lines.append("    %s  \u4e0a\u671f %.2f -> \u672c\u671f %.2f  \u6da8\u5e45 %.1f%%" % (
                s["label"], s["prev"], s["cur"], s["rate"] * 100))
    else:
        lines.append("  \u73af\u6bd4\u672a\u89c1\u8d85\u8fc7\u9608\u503c\u7684\u5f02\u5e38")
    if yoy:
        lines.append("  \u540c\u6bd4\u5f02\u5e38 %d \u4e2a\u6708\uff1a" % len(yoy))
        for s in yoy:
            lines.append("    %s  \u53bb\u5e74\u540c\u671f %.2f -> \u672c\u671f %.2f  \u6da8\u5e45 %.1f%%" % (
                s["label"], s["base"], s["cur"], s["rate"] * 100))
    else:
        lines.append("  \u540c\u6bd4\u672a\u89c1\u8d85\u8fc7\u9608\u503c\u7684\u5f02\u5e38\uff08\u6216\u6570\u636e\u4e0d\u8db3 12 \u4e2a\u6708\uff09")
    lines.append("")
    lines.append("  \u63d0\u793a\uff1a\u73af\u6bd4\u5f02\u5e38\u9700\u5254\u9664\u5b63\u8282\u6027\u56e0\u7d20\u540e\u518d\u5f52\u56e0\uff1b\u5148\u67e5\u6284\u8868\u6bb5\u4e0e\u8ba1\u8d39\u6bb5\uff0c\u518d\u8003\u8651\u6821\u8868\u3002")
    lines.append("")

    lines.append("[\u4e09] \u540e\u7eed\u52a8\u4f5c")
    lines.append("  1. \u6838\u5bf9\u6237\u53f7\u4e0e\u8868\u53f7\u662f\u5426\u5bf9\u5e94\uff0c\u786e\u8ba4\u6284\u8868\u65b9\u5f0f\u4e3a\u5b9e\u6284/\u4f30\u6284/\u8fdc\u6284")
    lines.append("  2. \u786e\u8ba4\u5f53\u5730\u6267\u884c\u7684\u662f\u6309\u6708\u5206\u6863\u8fd8\u662f\u6309\u5e74\u5206\u6863\uff08\u672c\u7ed3\u679c\u6309 %s \u8ba1\u7b97\uff09" % ("\u6309\u6708" if cycle == "month" else "\u6309\u5e74\u7d2f\u8ba1"))
    lines.append("  3. \u505a\u5173\u9600/\u65ad\u7535\u8bd5\u9a8c\u5e76\u5f55\u50cf\uff1b\u8fde\u7eed\u4f30\u6284\u5e94\u63d0\u51fa\u5f02\u8bae")
    lines.append("  4. \u8868\u5177\u8bef\u5dee\u9000\u8865\u7528\u6298\u7b97\u516c\u5f0f\uff1a\u5e94\u9000\u8865 = \u6284\u89c1\u91cf x r / (1 + r)")
    lines.append("  5. \u4e66\u9762\u63d0\u51fa\u9000\u8865\u7533\u8bf7\u5e76\u4fdd\u7559\u5de5\u5355\u53f7\uff0c\u4e89\u8bae\u671f\u95f4\u7f34\u65e0\u4e89\u8bae\u90e8\u5206")
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u4ef7\u683c\u4e0e\u9636\u68af\u57fa\u6570\u4ee5\u5f53\u5730\u73b0\u884c\u516c\u5e03\u4e3a\u51c6\uff0c\u672c\u7ed3\u679c\u4e3a\u6838\u7b97\u65b9\u6cd5\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u8d26\u52a1\u8ba4\u5b9a\u3002")
    lines.append("=" * 56)

    summary = {
        "cycle": cycle,
        "threshold": threshold,
        "rows": rows,
        "total_due": round(total_due, 4),
        "total_billed": round(total_billed, 4) if has_billed else None,
        "total_diff": round(total_billed - total_due, 4) if has_billed else None,
        "spikes": spikes,
        "year_over_year": yoy,
    }
    return "\n".join(lines), summary


def selftest():
    ok = True
    tiers = [(180, 0.5), (220, 0.6), (None, 0.8)]

    # 1) \u9636\u68af\u7d2f\u8fdb\uff1a100 \u5ea6 -> 50
    amt, _ = tier_amount(100, tiers)
    ok = ok and abs(amt - 50.0) < 1e-9

    # 2) \u9636\u68af\u7d2f\u8fdb\u8de8\u4e8c\u6863\uff1a200 \u5ea6 -> 180*0.5 + 20*0.6 = 102
    amt2, _ = tier_amount(200, tiers)
    ok = ok and abs(amt2 - 102.0) < 1e-9

    # 3) \u9636\u68af\u7d2f\u8fdb\u8de8\u4e09\u6863\uff1a500 \u5ea6 -> 90 + 132 + 100*0.8 = 302
    amt3, _ = tier_amount(500, tiers)
    ok = ok and abs(amt3 - 302.0) < 1e-9

    # 4) \u8868\u8ba1\u8d85\u5dee\u6298\u7b97\uff1a3000, r=0.05 -> \u591a\u8ba1\u7ea6 142.857
    res = meter_error_refund(3000, 0.05)
    ok = ok and abs(res["actual"] - 2857.142857) < 1e-3
    ok = ok and abs(res["diff"] - 142.857143) < 1e-3
    ok = ok and res["direction"] == "\u5e94\u9000\u7ed9\u7528\u6237"

    # 5) \u8868\u6162\u5e94\u8865\u6536
    res2 = meter_error_refund(1000, -0.1)
    ok = ok and res2["diff"] < 0 and res2["direction"] == "\u5e94\u5411\u7528\u6237\u8865\u6536"

    # 6) \u8fdd\u7ea6\u91d1\u4e0a\u9650\u622a\u65ad
    lf = late_fee(1000, 400, daily_rate=0.001, cap_ratio=0.3)
    ok = ok and abs(lf["raw_fee"] - 400.0) < 1e-9
    ok = ok and abs(lf["fee"] - 300.0) < 1e-9
    ok = ok and lf["capped"] is True
    lf2 = late_fee(1000, 10, daily_rate=0.001, cap_ratio=0.3)
    ok = ok and lf2["capped"] is False

    # 7) \u73af\u6bd4\u5f02\u5e38\u68c0\u6d4b
    months = [
        {"label": "M1", "usage": 100, "amount": 50.0},
        {"label": "M2", "usage": 105, "amount": 52.5},
        {"label": "M3", "usage": 300, "amount": 200.0},
    ]
    spikes = detect_spike(months, 0.5)
    ok = ok and len(spikes) == 1 and spikes[0]["label"] == "M3"

    # 8) \u8d26\u5355\u6bd4\u5bf9\uff1a\u591a\u6536\u5dee\u989d
    _, summary = build_report({"cycle": "month", "tiers": [{"limit": 180, "price": 0.5},
                                                          {"limit": 220, "price": 0.6},
                                                          {"limit": None, "price": 0.8}],
                               "months": months})
    ok = ok and abs(summary["total_due"] - 264.5) < 1e-9
    ok = ok and abs(summary["total_diff"] - 38.0) < 1e-9

    return ok


def main():
    parser = argparse.ArgumentParser(description="\u6c34\u7535\u8d39\u5f02\u5e38\u6838\u67e5\u4e0e\u9000\u8865\u6838\u7b97\u5de5\u5177")
    parser.add_argument("--file", help="\u8d26\u5355 JSON \u6587\u4ef6\u8def\u5f84\uff08UTF-8\uff09")
    parser.add_argument("--json", action="store_true", help="\u4ee5 JSON \u8f93\u51fa")
    parser.add_argument("--out", help="\u7ed3\u679c\u5199\u5165\u6307\u5b9a\u6587\u4ef6")
    parser.add_argument("--selftest", action="store_true", help="\u8fd0\u884c\u81ea\u68c0")
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))

    if args.selftest:
        ok = selftest()
        out_lines = ["SELFTEST %s" % ("OK" if ok else "FAILED")]
        with io.open(os.path.join(here, "_selftest_result.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(out_lines))
        print("\n".join(out_lines))
        sys.exit(0 if ok else 1)

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
