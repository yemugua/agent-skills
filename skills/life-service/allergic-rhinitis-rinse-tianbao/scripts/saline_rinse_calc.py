# -*- coding: utf-8 -*-
"""\u9f3b\u8154\u51b2\u6d17\u6db2\u6d53\u5ea6\u6362\u7b97\u4e0e\u64cd\u4f5c\u5408\u89c4\u81ea\u67e5\u5de5\u5177\u3002

\u7528\u6cd5:
  python saline_rinse_calc.py --file case.json [--json]
  python saline_rinse_calc.py --selftest

\u6c34\u6e90\u4e0d\u5408\u89c4\u65f6\u963b\u65ad\u5e76\u53ea\u8f93\u51fa\u5b89\u5168\u63d0\u793a\u3002\u672c\u5de5\u5177\u4e0d\u8f93\u51fa\u4efb\u4f55\u836f\u7269\u5242\u91cf\u3002
"""
import argparse
import io
import json
import os
import sys

SAFE_WATER = {"sterile": "\u65e0\u83cc\u6c34\u6216\u706d\u83cc\u7528\u6c34",
              "boiled": "\u716e\u6cb8\u540e\u51b7\u5374\u7684\u6c34",
              "filtered": "\u7ecf 0.2 \u5fae\u7c73\u7ea7\u522b\u8fc7\u6ee4\u7684\u6c34",
              "commercial": "\u6210\u54c1\u51b2\u6d17\u6db2\u6216\u914d\u5957\u76d0\u5305"}
UNSAFE_WATER_TEXT = {
    "tap": "\u672a\u7ecf\u5904\u7406\u7684\u81ea\u6765\u6c34",
    "well": "\u4e95\u6c34\u6216\u6cb3\u6c34\u7b49\u672a\u7ecf\u6d88\u6bd2\u7684\u6c34",
    "stored": "\u957f\u65f6\u95f4\u5b58\u653e\u7684\u50a8\u6c34",
}
ISOTONIC = 0.9
HYPERTONIC_MIN = 1.5
HYPERTONIC_MAX = 3.0
TEMP_LOW = 35.0
TEMP_HIGH = 37.0
DECONG_MAX_DAYS = 7


def concentration(salt_grams, water_ml):
    """\u8fd4\u56de\u6d53\u5ea6\u767e\u5206\u6bd4\uff1b\u6c34\u91cf\u4e3a 0 \u8fd4\u56de None\u3002"""
    w = float(water_ml or 0)
    if w <= 0:
        return None
    return round(float(salt_grams or 0) / w * 100.0, 3)


def tonicity(pct):
    """\u7b49\u6e17 / \u504f\u4f4e\u6e17 / \u9ad8\u6e17 / \u8fc7\u9ad8\u3002"""
    if pct is None:
        return "\u65e0\u6cd5\u5224\u5b9a"
    d = abs(pct - ISOTONIC)
    if d <= 0.05:
        return "\u7b49\u6e17"
    if pct < ISOTONIC:
        return "\u4f4e\u4e8e\u7b49\u6e17"
    if pct <= HYPERTONIC_MAX:
        return "\u9ad8\u6e17"
    return "\u6d53\u5ea6\u8fc7\u9ad8"


def salt_needed(water_ml, pct=ISOTONIC):
    """\u6309\u76ee\u6807\u6d53\u5ea6\u8ba1\u7b97\u6240\u9700\u76d0\u91cf\uff08\u514b\uff09\u3002"""
    return round(float(water_ml or 0) * float(pct) / 100.0, 2)


def temp_check(temp_c):
    t = float(temp_c or 0)
    if t <= 0:
        return "\u672a\u63d0\u4f9b\u6c34\u6e29"
    if t < TEMP_LOW:
        return "\u504f\u51b7\uff0c\u53ef\u80fd\u5f15\u8d77\u4e0d\u9002\uff0c\u5e94\u8c03\u5230\u7ea6 35-37 \u6444\u6c0f\u5ea6"
    if t > TEMP_HIGH:
        return "\u504f\u70ed\uff0c\u6709\u9ecf\u819c\u70eb\u4f24\u98ce\u9669\uff0c\u5e94\u51b7\u5374\u5230\u7ea6 35-37 \u6444\u6c0f\u5ea6"
    return "\u5408\u9002"


def times_advice(times_per_day):
    t = float(times_per_day or 0)
    if t <= 0:
        return "\u672a\u63d0\u4f9b\u9891\u6b21"
    if t <= 2:
        return "\u6bcf\u65e5 %g \u6b21\uff0c\u5728\u5e38\u89c1\u53e3\u5f84\u8303\u56f4\u5185" % t
    return "\u6bcf\u65e5 %g \u6b21\u504f\u591a\uff0c\u8fc7\u5ea6\u51b2\u6d17\u53ef\u80fd\u7834\u574f\u9ecf\u819c\u73af\u5883\uff0c\u5efa\u8bae\u54a8\u8be2\u533b\u751f" % t


def build_report(data):
    salt = data.get("salt_grams", 0)
    water = data.get("water_ml", 0)
    source = data.get("water_source", "tap")
    temp = data.get("temp_c", 0)
    times = data.get("times_per_day", 1)
    decon_days = data.get("decongestant_days", 0)

    lines = []
    lines.append("=" * 66)
    lines.append("\u9f3b\u8154\u51b2\u6d17\u6db2\u6d53\u5ea6\u6362\u7b97\u4e0e\u64cd\u4f5c\u5408\u89c4\u81ea\u67e5")
    lines.append("=" * 66)

    if source in UNSAFE_WATER_TEXT:
        lines.append("")
        lines.append("[\u963b\u65ad] \u6c34\u6e90\u4e0d\u5408\u89c4\uff0c\u4e0d\u8f93\u51fa\u51b2\u6d17\u65b9\u6848")
        lines.append("-" * 66)
        lines.append("  \u5f53\u524d\u6c34\u6e90\uff1a%s" % UNSAFE_WATER_TEXT[source])
        lines.append("")
        lines.append("  \u5fc5\u987b\u4f7f\u7528\u4ee5\u4e0b\u4e4b\u4e00\uff1a")
        for k in ("sterile", "boiled", "filtered", "commercial"):
            lines.append("    + %s" % SAFE_WATER[k])
        lines.append("")
        lines.append("  \u672a\u7ecf\u5904\u7406\u7684\u81ea\u6765\u6c34\u53ef\u80fd\u542b\u5fae\u751f\u7269\uff0c\u7ecf\u9f3b\u8154\u51b2\u6d17\u8fdb\u5165\u4f53\u5185\uff0c")
        lines.append("  \u867d\u7f55\u89c1\u4f46\u53ef\u5f15\u8d77\u4e25\u91cd\u611f\u67d3\uff0c\u4e0d\u8981\u56fe\u7701\u4e8b\u76f4\u63a5\u4f7f\u7528\u3002")
        lines.append("")
        lines.append("  \u6539\u7528\u5408\u89c4\u6c34\u6e90\u540e\u91cd\u65b0\u6838\u5bf9\u6d53\u5ea6\u4e0e\u6c34\u6e29\u3002")
        lines.append("=" * 66)
        summary = {"blocked": True, "reason": "water_source_unsafe",
                   "water_source": source, "concentration": None,
                   "medication_dose_provided": False}
        return "\n".join(lines), summary

    pct = concentration(salt, water)
    ton = tonicity(pct)
    lines.append("\u76d0\u91cf\uff1a%g \u514b   \u6c34\u91cf\uff1a%g \u6beb\u5347   \u6c34\u6e90\uff1a%s" % (
        float(salt or 0), float(water or 0), SAFE_WATER.get(source, "\u672a\u8bc6\u522b")))
    lines.append("\u6c34\u6e29\uff1a%g \u6444\u6c0f\u5ea6   \u6bcf\u65e5\u9891\u6b21\uff1a%g \u6b21" % (float(temp or 0), float(times or 0)))
    lines.append("")
    lines.append("[\u4e00] \u6d53\u5ea6")
    if pct is None:
        lines.append("  \u6c34\u91cf\u4e3a 0 \u6216\u672a\u63d0\u4f9b\uff0c\u65e0\u6cd5\u8ba1\u7b97\u6d53\u5ea6")
        lines.append("  \u53c2\u8003\u914d\u6bd4\uff1a\u6bcf 1000 \u6beb\u5347\u6c34\u52a0\u7ea6 %g \u514b\u76d0\u5f97\u5230 %.1f%% \u7b49\u6e17\u76d0\u6c34" % (
            salt_needed(1000), ISOTONIC))
    else:
        lines.append("  \u5f53\u524d\u6d53\u5ea6\uff1a%.3f%%  -> %s" % (pct, ton))
        lines.append("  \u7b49\u6e17\u76ee\u6807 %.1f%%\uff1a%.3f \u514b\u76d0 + %g \u6beb\u5347\u6c34\u9700 %g \u514b" % (
            ISOTONIC, ISOTONIC, float(water or 0), salt_needed(water)))
        if ton == "\u7b49\u6e17":
            lines.append("  \u5224\u5b9a\uff1a\u7b26\u5408\u65e5\u5e38\u7ef4\u6301\u7528\u7b49\u6e17\u53e3\u5f84")
        elif ton == "\u4f4e\u4e8e\u7b49\u6e17":
            lines.append("  \u5224\u5b9a\uff1a\u6d53\u5ea6\u504f\u4f4e\uff0c\u5efa\u8bae\u8865\u76d0\u81f3 %g \u514b" % salt_needed(water))
        elif ton == "\u9ad8\u6e17":
            lines.append("  \u5224\u5b9a\uff1a\u5c5e\u4e8e\u9ad8\u6e17\u8303\u56f4\uff08%.1f%%-%.1f%%\uff09\uff0c\u9700\u533b\u751f\u6307\u5bfc\uff0c\u4e0d\u81ea\u884c\u957f\u671f\u4f7f\u7528" % (
                HYPERTONIC_MIN, HYPERTONIC_MAX))
        else:
            lines.append("  \u5224\u5b9a\uff1a\u8d85\u8fc7 %.1f%%\uff0c\u6d53\u5ea6\u8fc7\u9ad8\uff0c\u4f1a\u523a\u6fc0\u9ecf\u819c\uff0c\u5e94\u7a00\u91ca" % HYPERTONIC_MAX)
    lines.append("")
    lines.append("[\u4e8c] \u6c34\u6e29")
    lines.append("  " + temp_check(temp))
    lines.append("")
    lines.append("[\u4e09] \u9891\u6b21")
    lines.append("  " + times_advice(times))
    lines.append("")
    lines.append("[\u56db] \u64cd\u4f5c\u8981\u70b9")
    for c in ["\u5934\u524d\u503e\u7ea6 45 \u5ea6\uff0c\u5934\u7565\u8f6c\u5411\u5bf9\u4fa7",
              "\u51fa\u6db2\u53e3\u8f7b\u8d34\u9f3b\u5b54\u5f62\u6210\u8f6f\u5bc6\u5c01\uff0c\u4e0d\u8981\u7528\u529b\u9876\u5165",
              "\u5f20\u53e3\u81ea\u7136\u547c\u5438\u6216\u6301\u7eed\u53d1\u554a\u7684\u97f3\uff0c\u5168\u7a0b\u4e0d\u541e\u54bd",
              "\u9760\u91cd\u529b\u6216\u8f7b\u5fae\u6324\u538b\u6d41\u5165\uff0c\u4e0d\u7528\u5927\u529b",
              "\u7ed3\u675f\u540e\u5355\u4fa7\u4ea4\u66ff\u8f7b\u64e4\uff0c\u4e0d\u8981\u4e24\u4fa7\u540c\u65f6\u634f\u7d27\u7528\u529b",
              "\u5668\u5177\u6bcf\u6b21\u6e05\u6d17\u667e\u5e72\uff0c\u5b9a\u671f\u66f4\u6362\uff0c\u4e0d\u4e0e\u5bb6\u4eba\u5171\u7528"]:
        lines.append("  + %s" % c)
    lines.append("")
    lines.append("[\u4e94] \u51cf\u5145\u8840\u5242\u63d0\u9192")
    d = float(decon_days or 0)
    if d <= 0:
        lines.append("  \u672a\u4f7f\u7528\u6216\u672a\u586b\u5199\u3002\u51cf\u5145\u8840\u5242\u7c7b\u9f3b\u55b7\u5242\u8fde\u7eed\u4f7f\u7528\u901a\u5e38\u4e0d\u5b9c\u8d85\u8fc7 %d \u5929" % DECONG_MAX_DAYS)
    elif d > DECONG_MAX_DAYS:
        lines.append("  \u5df2\u8fde\u7eed %g \u5929\uff0c\u8d85\u8fc7\u5e38\u89c1\u7684 %d \u5929\u4e0a\u9650\uff1a\u5e94\u5c31\u8bca\uff0c\u4e0d\u8981\u7ee7\u7eed\u81ea\u884c\u5ef6\u957f" % (
            d, DECONG_MAX_DAYS))
    else:
        lines.append("  \u5df2\u8fde\u7eed %g \u5929\uff0c\u672a\u8d85\u8fc7\u5e38\u89c1\u7684 %d \u5929\u4e0a\u9650\uff0c\u4ecd\u4e0d\u5efa\u8bae\u81ea\u884c\u5ef6\u957f" % (d, DECONG_MAX_DAYS))
    lines.append("  \u4f9d\u8d56\u4fe1\u53f7\uff1a\u4e0d\u7528\u55b7\u5242\u5c31\u5b8c\u5168\u4e0d\u901a\u3001\u6b21\u6570\u8d8a\u6765\u8d8a\u591a\u3001\u95f4\u9694\u8d8a\u6765\u8d8a\u77ed")
    lines.append("")
    lines.append("[\u516d] \u505c\u6b62\u51b2\u6d17\u5e76\u5c31\u533b\u7684\u4fe1\u53f7")
    lines.append("  \u8033\u75db\u3001\u8033\u95f7\u3001\u542c\u529b\u4e0b\u964d\u3001\u7729\u6655\u3001\u9f3b\u51fa\u8840\u3001\u5267\u70c8\u54b3\u55fd\uff1a\u7acb\u5373\u505c\u6b62\u5e76\u5c31\u8bca")
    lines.append("  \u5355\u4fa7\u6301\u7eed\u8113\u8840\u6d95\u3001\u53cd\u590d\u9f3b\u51fa\u8840\u3001\u89c6\u529b\u6539\u53d8\u3001\u5267\u70c8\u5934\u75db\uff1a\u5c3d\u5feb\u5c31\u8bca")
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u64cd\u4f5c\u6838\u5bf9\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u8bca\u7597\u610f\u89c1\uff0c\u4e0d\u63d0\u4f9b\u836f\u7269\u5242\u91cf\u3002")
    lines.append("=" * 66)

    summary = {"blocked": False, "water_source": source, "concentration": pct,
               "tonicity": ton, "suggested_salt_grams": salt_needed(water),
               "temp_check": temp_check(temp), "times_advice": times_advice(times),
               "decongestant_days": decon_days,
               "decongestant_over_limit": d > DECONG_MAX_DAYS,
               "medication_dose_provided": False}
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("9 \u514b\u914d 1000 \u6beb\u5347\u4e3a 0.9", abs(concentration(9, 1000) - 0.9) < 1e-9))
    r.append(("4.5 \u514b\u914d 500 \u6beb\u5347\u4e3a 0.9", abs(concentration(4.5, 500) - 0.9) < 1e-9))
    r.append(("\u6c34\u91cf 0 \u8fd4\u56de None", concentration(9, 0) is None))
    r.append(("0.9 \u5224\u7b49\u6e17", tonicity(0.9) == "\u7b49\u6e17"))
    r.append(("0.88 \u5224\u7b49\u6e17\uff08\u5bb9\u5dee\uff09", tonicity(0.88) == "\u7b49\u6e17"))
    r.append(("0.5 \u5224\u4f4e\u4e8e\u7b49\u6e17", tonicity(0.5) == "\u4f4e\u4e8e\u7b49\u6e17"))
    r.append(("2.0 \u5224\u9ad8\u6e17", tonicity(2.0) == "\u9ad8\u6e17"))
    r.append(("5.0 \u5224\u6d53\u5ea6\u8fc7\u9ad8", tonicity(5.0) == "\u6d53\u5ea6\u8fc7\u9ad8"))
    r.append(("1000 \u6beb\u5347\u9700\u76d0 9 \u514b", abs(salt_needed(1000) - 9.0) < 1e-9))
    r.append(("500 \u6beb\u5347\u9700\u76d0 4.5 \u514b", abs(salt_needed(500) - 4.5) < 1e-9))
    r.append(("\u6c34\u6e29 36 \u5408\u9002", temp_check(36) == "\u5408\u9002"))
    r.append(("\u6c34\u6e29 30 \u504f\u51b7", "\u504f\u51b7" in temp_check(30)))
    r.append(("\u6c34\u6e29 45 \u504f\u70ed", "\u504f\u70ed" in temp_check(45)))
    r.append(("\u9891\u6b21 2 \u6b21\u5408\u89c4", "\u8303\u56f4\u5185" in times_advice(2)))
    r.append(("\u9891\u6b21 4 \u6b21\u504f\u591a", "\u504f\u591a" in times_advice(4)))

    _, s = build_report({"salt_grams": 9, "water_ml": 1000, "water_source": "boiled",
                         "temp_c": 36, "times_per_day": 2, "decongestant_days": 3})
    r.append(("\u5408\u89c4\u6837\u4f8b\u672a\u963b\u65ad", s["blocked"] is False))
    r.append(("\u5408\u89c4\u6837\u4f8b\u6d53\u5ea6 0.9", abs(s["concentration"] - 0.9) < 1e-9))
    r.append(("\u5408\u89c4\u6837\u4f8b\u7b49\u6e17", s["tonicity"] == "\u7b49\u6e17"))
    r.append(("\u51cf\u5145\u8840\u5242\u672a\u8d85\u9650", s["decongestant_over_limit"] is False))

    _, s2 = build_report({"salt_grams": 9, "water_ml": 1000, "water_source": "tap"})
    r.append(("\u81ea\u6765\u6c34\u963b\u65ad", s2["blocked"] is True))
    r.append(("\u963b\u65ad\u539f\u56e0\u4e3a\u6c34\u6e90", s2["reason"] == "water_source_unsafe"))
    r.append(("\u963b\u65ad\u65f6\u4e0d\u51fa\u6d53\u5ea6", s2["concentration"] is None))

    _, s3 = build_report({"salt_grams": 50, "water_ml": 1000,
                          "water_source": "boiled", "decongestant_days": 10})
    r.append(("\u9ad8\u6d53\u5ea6\u5224\u8fc7\u9ad8", s3["tonicity"] == "\u6d53\u5ea6\u8fc7\u9ad8"))
    r.append(("\u51cf\u5145\u8840\u5242\u8d85\u9650", s3["decongestant_over_limit"] is True))
    r.append(("\u4e0d\u63d0\u4f9b\u836f\u7269\u5242\u91cf", s3["medication_dose_provided"] is False))
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
    parser = argparse.ArgumentParser(description="\u9f3b\u8154\u51b2\u6d17\u6db2\u6d53\u5ea6\u6362\u7b97\u4e0e\u64cd\u4f5c\u5408\u89c4\u81ea\u67e5\u5de5\u5177")
    parser.add_argument("--file", help="\u8f93\u5165 JSON \u6587\u4ef6\u8def\u5f84\uff08UTF-8\uff09")
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
