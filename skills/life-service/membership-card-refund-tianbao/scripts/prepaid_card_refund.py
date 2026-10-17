# -*- coding: utf-8 -*-
"""\u4f1a\u5458\u5361/\u50a8\u503c\u5361\u9000\u8d39\u6838\u7b97\u5de5\u5177\u3002

\u7528\u6cd5:
  python prepaid_card_refund.py --file \u5361\u7247.json [--json]
  python prepaid_card_refund.py --selftest

\u53ea\u505a\u91d1\u989d\u4e0e\u4e0a\u9650\u6838\u7b97\uff0c\u4e0d\u5224\u65ad\u6761\u6b3e\u6548\u529b\u3002
"""
import argparse
import io
import json
import os
import sys

LOSS_CAP_RATIO = 0.3  # \u8fdd\u7ea6\u91d1\u8fc7\u9ad8\u7684\u53c2\u8003\u6bd4\u4f8b\uff0c\u975e\u7edd\u5bf9\u6807\u51c6


def discount_factor(paid, gift):
    """\u6298\u6263\u7cfb\u6570 k = \u5b9e\u4ed8\u672c\u91d1 / (\u672c\u91d1 + \u8d60\u9001)\u3002\u8d60\u9001\u4e3a 0 \u65f6 k = 1\u3002"""
    paid = float(paid)
    gift = float(gift)
    total = paid + gift
    if total <= 0:
        return 0.0
    return paid / total


def refund_amortized(remaining, paid, gift):
    """\u53e3\u5f84 A \u4ef7\u683c\u644a\u9500\u6cd5\uff1a\u5e94\u9000 = \u5269\u4f59\u5361\u5185\u4f59\u989d \u00d7 k\u3002"""
    k = discount_factor(paid, gift)
    value = float(remaining) * k
    return max(0.0, value), k


def refund_list_price(paid, consumed_list_price):
    """\u53e3\u5f84 B \u95e8\u5e02\u4ef7\u6cd5\uff1a\u5e94\u9000 = \u5b9e\u4ed8\u672c\u91d1 - \u5df2\u6d88\u8d39\u9879\u76ee\u95e8\u5e02\u4ef7\u5408\u8ba1\uff08\u4e0b\u9650 0\uff09\u3002"""
    value = float(paid) - float(consumed_list_price)
    return max(0.0, value)


def penalty_check(base, penalty_rate, actual_loss, notice_penalty):
    """\u8fdd\u7ea6\u91d1/\u624b\u7eed\u8d39\u53ef\u6263\u6821\u9a8c\u3002

    \u672a\u7ea6\u5b9a\u6216\u5f00\u5361\u65f6\u672a\u663e\u8457\u63d0\u793a -> \u53ef\u6263 0
    \u5df2\u7ea6\u5b9a\u4e14\u5df2\u63d0\u793a -> \u53d6 min(\u7ea6\u5b9a\u6263\u6b3e, \u5b9e\u9645\u635f\u5931) \u4e0e min(\u7ea6\u5b9a\u6263\u6b3e, \u5b9e\u9645\u635f\u5931 * (1 + \u53c2\u8003\u6bd4\u4f8b)) \u4e24\u8005\u4e2d\u7684\u8f83\u4e25\u8005
    """
    rate = float(penalty_rate or 0)
    if rate <= 0 or not notice_penalty:
        return {
            "allowed": 0.0,
            "contract_amount": 0.0,
            "reason": "\u65e0\u7ea6\u5b9a\u6216\u5f00\u5361\u65f6\u672a\u663e\u8457\u63d0\u793a\uff0c\u4e0d\u5f97\u6536\u53d6",
            "exceeds_loss": False,
        }
    contract_amount = float(base) * rate
    loss = float(actual_loss or 0)
    allowed = min(contract_amount, loss * (1 + LOSS_CAP_RATIO))
    return {
        "allowed": round(allowed, 4),
        "contract_amount": round(contract_amount, 4),
        "reason": "\u6709\u7ea6\u5b9a\u5e76\u5df2\u63d0\u793a\uff0c\u6309\u5b9e\u9645\u635f\u5931\u52a0\u53c2\u8003\u6bd4\u4f8b\u6821\u9a8c\u4e0a\u9650",
        "exceeds_loss": contract_amount > loss * (1 + LOSS_CAP_RATIO),
    }


def build_report(data):
    paid = float(data.get("paid", 0) or 0)
    gift = float(data.get("gift", 0) or 0)
    remaining = float(data.get("remaining", 0) or 0)
    consumed_list_price = float(data.get("consumed_list_price", 0) or 0)
    penalty_rate = float(data.get("penalty_rate", 0) or 0)
    actual_loss = float(data.get("actual_loss", 0) or 0)
    notice_penalty = bool(data.get("notice_penalty", False))
    expired = bool(data.get("expired", False))

    amount_a, k = refund_amortized(remaining, paid, gift)
    amount_b = refund_list_price(paid, consumed_list_price)
    low = min(amount_a, amount_b)
    high = max(amount_a, amount_b)
    penalty = penalty_check(amount_a, penalty_rate, actual_loss, notice_penalty)
    net_a = max(0.0, amount_a - penalty["allowed"])

    lines = []
    lines.append("=" * 56)
    lines.append("\u4f1a\u5458\u5361/\u50a8\u503c\u5361\u9000\u8d39 \u6838\u7b97\u7ed3\u679c")
    lines.append("=" * 56)
    lines.append("\u5b9e\u4ed8\u672c\u91d1\uff1a%.2f \u5143" % paid)
    lines.append("\u8d60\u9001\u91d1\u989d\uff1a%.2f \u5143" % gift)
    lines.append("\u5269\u4f59\u53ef\u7528\u4f59\u989d\uff1a%.2f \u5143" % remaining)
    lines.append("\u5df2\u6d88\u8d39\u9879\u76ee\u95e8\u5e02\u4ef7\u5408\u8ba1\uff1a%.2f \u5143" % consumed_list_price)
    lines.append("")
    lines.append("[\u4e00] \u6298\u6263\u7cfb\u6570")
    lines.append("  k = \u5b9e\u4ed8\u672c\u91d1 / (\u672c\u91d1 + \u8d60\u9001) = %.4f" % k)
    lines.append("  \u542b\u4e49\uff1a\u5361\u5185\u6bcf 1 \u5143\u53ef\u7528\u989d\u5ea6\uff0c\u5b9e\u9645\u652f\u4ed8 %.4f \u5143" % k)
    lines.append("")
    lines.append("[\u4e8c] \u4e24\u5957\u53e3\u5f84")
    lines.append("  \u53e3\u5f84 A \u4ef7\u683c\u644a\u9500\u6cd5\uff08\u6d88\u8d39\u8005\u53e3\u5f84\uff09\uff1a\u5e94\u9000 = \u5269\u4f59\u4f59\u989d x k = %.2f \u5143" % amount_a)
    lines.append("  \u53e3\u5f84 B \u95e8\u5e02\u4ef7\u6cd5\uff08\u5546\u5bb6\u53e3\u5f84\uff09\uff1a\u5e94\u9000 = \u672c\u91d1 - \u5df2\u6d88\u8d39\u539f\u4ef7 = %.2f \u5143" % amount_b)
    lines.append("  \u5efa\u8bae\u4e3b\u5f20\u533a\u95f4\uff1a[%.2f , %.2f] \u5143\uff0c\u4f18\u5148\u6309\u53e3\u5f84 A \u63d0\u51fa" % (low, high))
    lines.append("")
    lines.append("[\u4e09] \u8fdd\u7ea6\u91d1/\u624b\u7eed\u8d39\u6821\u9a8c")
    lines.append("  \u7ea6\u5b9a\u6bd4\u4f8b\uff1a%.2f%%" % (penalty_rate * 100))
    lines.append("  \u662f\u5426\u5df2\u663e\u8457\u63d0\u793a\uff1a%s" % ("\u662f" if notice_penalty else "\u5426"))
    lines.append("  \u5546\u5bb6\u5b9e\u9645\u635f\u5931\uff1a%.2f \u5143" % actual_loss)
    lines.append("  \u6309\u7ea6\u5b9a\u8ba1\u7b97\uff1a%.2f \u5143" % penalty["contract_amount"])
    lines.append("  \u53ef\u6263\u4e0a\u9650\uff1a%.2f \u5143" % penalty["allowed"])
    lines.append("  \u7ed3\u8bba\uff1a%s" % penalty["reason"])
    if penalty["exceeds_loss"]:
        lines.append("  \u63d0\u793a\uff1a\u7ea6\u5b9a\u6263\u6b3e\u660e\u663e\u9ad8\u4e8e\u5b9e\u9645\u635f\u5931\uff0c\u53ef\u8bf7\u6c42\u9002\u5f53\u8c03\u6574")
    lines.append("  \u6263\u9664\u540e\u53ef\u4e3b\u5f20\u91d1\u989d\uff08\u53e3\u5f84 A\uff09\uff1a%.2f \u5143" % net_a)
    lines.append("")
    lines.append("[\u56db] \u5176\u4ed6\u63d0\u793a")
    if gift > 0:
        lines.append("  - \u8d60\u9001\u91d1\u989d %.2f \u5143\u5bf9\u5e94\u7684\u90e8\u5206\u4e0d\u9000\u672c\u91d1\uff0c\u6574\u5361\u6309\u6298\u6263\u7cfb\u6570\u6298\u7b97" % gift)
    if expired:
        lines.append("  - \u5361\u9762\u6709\u6548\u671f\u5df2\u8fc7\uff1a\u300c\u8fc7\u671f\u4f5c\u5e9f\u300d\u5c5e\u6392\u9664\u6d88\u8d39\u8005\u4e3b\u8981\u6743\u5229\u7684\u683c\u5f0f\u6761\u6b3e\u65b9\u5411\uff0c")
        lines.append("    \u5b58\u5728\u6548\u529b\u4e89\u8bae\uff0c\u4f59\u989d\u4e00\u822c\u4ecd\u53ef\u4e3b\u5f20\u9000\u8fd8\uff08\u4ee5\u73b0\u884c\u89c4\u5b9a\u4e3a\u51c6\uff09")
    lines.append("  - \u4f59\u989d\u4e0e\u6d88\u8d39\u660e\u7ec6\u7531\u5546\u5bb6\u638c\u63e1\uff0c\u5e94\u7b2c\u4e00\u65f6\u95f4\u622a\u56fe\u56fa\u5b9a\uff0c\u5e76\u4e66\u9762\u8981\u6c42\u5546\u5bb6\u63d0\u4f9b")
    lines.append("  - \u4e3b\u5f20\u5bf9\u8c61\u4e3a\u8425\u4e1a\u6267\u7167\u4e0a\u7684\u4e3b\u4f53\u540d\u79f0\uff0c\u4e0d\u662f\u95e8\u5e97\u62db\u724c\u540d")
    lines.append("  - \u9000\u4e00\u8d54\u4e09\u4ec5\u5728\u6784\u6210\u6b3a\u8bc8\u65f6\u9002\u7528\uff1b\u7ecf\u8425\u4e0d\u5584\u505c\u4e1a\u4e0d\u7b49\u4e8e\u6b3a\u8bc8")
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u91d1\u989d\u6838\u7b97\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u6761\u6b3e\u6548\u529b\u8ba4\u5b9a\u6216\u6cd5\u5f8b\u610f\u89c1\u3002")
    lines.append("=" * 56)

    summary = {
        "paid": paid,
        "gift": gift,
        "remaining": remaining,
        "discount_factor": round(k, 6),
        "refund_amortized": round(amount_a, 4),
        "refund_list_price": round(amount_b, 4),
        "claim_range": [round(low, 4), round(high, 4)],
        "penalty": penalty,
        "net_claim": round(net_a, 4),
        "expired": expired,
    }
    return "\n".join(lines), summary


def _run_checks():
    results = []

    # 1) \u6298\u6263\u7cfb\u6570
    k = discount_factor(5000, 1000)
    results.append(("\u6298\u6263\u7cfb\u6570 5000/(5000+1000)", abs(k - 0.8333333333) < 1e-6))

    # 2) \u65e0\u8d60\u9001\u65f6\u7cfb\u6570\u4e3a 1
    results.append(("\u65e0\u8d60\u9001\u65f6\u7cfb\u6570=1", abs(discount_factor(1000, 0) - 1.0) < 1e-9))

    # 3) \u53e3\u5f84 A: 3000 * 0.8333 = 2500
    a, _ = refund_amortized(3000, 5000, 1000)
    results.append(("\u53e3\u5f84A \u5e94\u9000 2500", abs(a - 2500.0) < 1e-3))

    # 4) \u53e3\u5f84 B: 5000 - 3200 = 1800
    b = refund_list_price(5000, 3200)
    results.append(("\u53e3\u5f84B \u5e94\u9000 1800", abs(b - 1800.0) < 1e-9))

    # 5) \u53e3\u5f84 B \u4e0b\u9650\u4e3a 0
    results.append(("\u53e3\u5f84B \u4e0b\u9650\u4e3a0", refund_list_price(1000, 5000) == 0.0))

    # 6) \u672a\u7ea6\u5b9a\u8fdd\u7ea6\u91d1\u4e0d\u5f97\u6263
    p0 = penalty_check(2500, 0.3, 100, False)
    results.append(("\u672a\u63d0\u793a\u4e0d\u5f97\u6263\u8fdd\u7ea6\u91d1", p0["allowed"] == 0.0))

    # 7) \u6709\u7ea6\u5b9a\u5e76\u63d0\u793a\u65f6\u6309\u635f\u5931\u6821\u9a8c
    p1 = penalty_check(2500, 0.3, 100, True)
    results.append(("\u8fdd\u7ea6\u91d1\u4e0d\u8d85\u635f\u5931\u53c2\u8003\u4e0a\u9650", abs(p1["allowed"] - 130.0) < 1e-9))

    # 8) \u65e0\u7ea6\u5b9a\u6bd4\u4f8b\u65f6\u4e0d\u5f97\u6263
    p2 = penalty_check(2500, 0, 100, True)
    results.append(("\u65e0\u7ea6\u5b9a\u6bd4\u4f8b\u4e0d\u5f97\u6263", p2["allowed"] == 0.0))

    # 9) \u6574\u4f53\u62a5\u544a\uff1a\u4e3b\u5f20\u533a\u95f4
    _, s = build_report({
        "paid": 5000, "gift": 1000, "remaining": 3000,
        "consumed_list_price": 3200, "penalty_rate": 0.0,
        "actual_loss": 0, "notice_penalty": False, "expired": False,
    })
    results.append(("\u4e3b\u5f20\u533a\u95f4 [1800,2500]",
                    abs(s["claim_range"][0] - 1800.0) < 1e-6 and abs(s["claim_range"][1] - 2500.0) < 1e-6))

    # 10) \u672a\u5f00\u5361\u5168\u989d\u9000\uff1a\u65e0\u8d60\u9001\u3001\u4f59\u989d=\u672c\u91d1
    a2, k2 = refund_amortized(5000, 5000, 0)
    results.append(("\u672a\u6d88\u8d39\u5168\u989d\u9000\u672c\u91d1", abs(a2 - 5000.0) < 1e-9 and abs(k2 - 1.0) < 1e-9))

    return results


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
    parser = argparse.ArgumentParser(description="\u4f1a\u5458\u5361/\u50a8\u503c\u5361\u9000\u8d39\u6838\u7b97\u5de5\u5177")
    parser.add_argument("--file", help="\u5361\u7247 JSON \u6587\u4ef6\u8def\u5f84\uff08UTF-8\uff09")
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
