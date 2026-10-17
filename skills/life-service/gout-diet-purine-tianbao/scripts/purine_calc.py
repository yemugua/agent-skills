# -*- coding: utf-8 -*-
"""\u75db\u98ce\u4e00\u9910\u560c\u5464\u6838\u7b97\u4e0e\u5fcc\u53e3\u63d0\u793a\u5de5\u5177\u3002

\u7528\u6cd5:
  python purine_calc.py --file meal.json [--json]
  python purine_calc.py --selftest

\u560c\u5464\u6570\u503c\u4e3a\u901a\u7528\u98df\u7269\u6210\u5206\u8868\u53e3\u5f84\uff08\u6bcf 100 \u514b\u53ef\u98df\u90e8\uff0c\u5355\u4f4d\u6beb\u514b\uff09\uff0c\u5dee\u5f02\u8f83\u5927\u3002
\u672a\u6536\u5f55\u7684\u98df\u7269\u4e0d\u4f1a\u51ed\u7a7a\u4f30\u7b97\uff0c\u5217\u5165\u5f85\u786e\u8ba4\u9879\u3002
"""
import argparse
import io
import json
import os
import sys

# \u6bcf 100 \u514b\u53ef\u98df\u90e8\u560c\u5464\u6beb\u514b\u6570\uff0c\u8fd1\u4f3c\u503c
FOODS = {
    "\u732a\u809d": 275.0,
    "\u9e21\u809d": 293.0,
    "\u732a\u80be": 269.0,
    "\u732a\u8111": 175.0,
    "\u6c99\u4e01\u9c7c": 345.0,
    "\u51e4\u5c3e\u9c7c": 239.0,
    "\u5c0f\u9c7c\u5e72": 1538.0,
    "\u7261\u86ce": 239.0,
    "\u86e4\u870a": 316.0,
    "\u867e": 137.0,
    "\u87f9": 81.0,
    "\u5e26\u9c7c": 391.0,
    "\u8349\u9c7c": 140.0,
    "\u9cb3\u9c7c": 133.0,
    "\u732a\u8089": 122.0,
    "\u725b\u8089": 83.0,
    "\u7f8a\u8089": 111.0,
    "\u9e21\u8089": 137.0,
    "\u9e2d\u8089": 138.0,
    "\u9e21\u86cb": 3.0,
    "\u725b\u5976": 1.4,
    "\u65e0\u7cd6\u9178\u5976": 1.5,
    "\u8c46\u8150": 55.0,
    "\u8c46\u6d46": 27.0,
    "\u9ec4\u8c46": 166.0,
    "\u83e0\u83dc": 23.0,
    "\u9752\u83dc": 15.0,
    "\u9ec4\u74dc": 9.0,
    "\u756a\u8304": 11.0,
    "\u571f\u8c46": 18.0,
    "\u7c73\u996d": 18.0,
    "\u9992\u5934": 27.0,
    "\u5e72\u9999\u83c7": 379.0,
    "\u9c9c\u9999\u83c7": 21.0,
    "\u7d2b\u83dc": 274.0,
    "\u82b1\u751f": 96.0,
    "\u82f9\u679c": 0.9,
    "\u897f\u74dc": 1.1,
}
ALCOHOL = {"\u5564\u9152": 10.0, "\u9ec4\u9152": 12.0, "\u767d\u9152": 0.0, "\u7ea2\u9152": 0.5}
LOW = 50.0
MID = 150.0
ACUTE_LIMIT = 150.0   # \u6025\u6027\u671f\u4e00\u9910\u560c\u5464\u53c2\u8003\u4e0a\u9650\uff08\u6beb\u514b\uff09
CHRONIC_LIMIT = 300.0  # \u7f13\u89e3\u671f\u4e00\u9910\u560c\u5464\u53c2\u8003\u4e0a\u9650\uff08\u6beb\u514b\uff09


def purine_of(name, grams):
    if name in FOODS:
        return FOODS[name] * float(grams) / 100.0
    if name in ALCOHOL:
        return ALCOHOL[name] * float(grams) / 100.0
    return None


def grade_of(p100):
    if p100 < LOW:
        return "\u4f4e"
    if p100 < MID:
        return "\u4e2d"
    return "\u9ad8"


def p100_of(name):
    if name in FOODS:
        return FOODS[name]
    if name in ALCOHOL:
        return ALCOHOL[name]
    return None


def build_report(data):
    items = data.get("items", [])
    stage = data.get("stage", "chronic")
    limit = ACUTE_LIMIT if stage == "acute" else CHRONIC_LIMIT
    stage_text = "\u6025\u6027\u53d1\u4f5c\u671f" if stage == "acute" else "\u7f13\u89e3\u671f"

    rows = []
    unknown = []
    alcohol = []
    total = 0.0
    for it in items:
        name = it.get("name", "")
        grams = float(it.get("grams", 0) or 0)
        p = purine_of(name, grams)
        if p is None:
            unknown.append((name, grams))
            continue
        p100 = p100_of(name)
        rows.append((name, grams, p100, p, grade_of(p100)))
        total += p
        if name in ALCOHOL:
            alcohol.append((name, grams))

    lines = []
    lines.append("=" * 66)
    lines.append("\u4e00\u9910\u560c\u5464\u6838\u7b97\u4e0e\u5fcc\u53e3\u63d0\u793a\uff08%s\uff09" % stage_text)
    lines.append("=" * 66)
    lines.append("%-12s %8s %12s %10s %6s" % ("\u98df\u7269", "\u91cd\u91cfg", "\u6bcf\u767e\u514bmg", "\u8be5\u9879mg", "\u5206\u7ea7"))
    lines.append("-" * 66)
    for name, grams, p100, p, g in rows:
        lines.append("%-12s %8g %12.1f %10.1f %6s" % (name, grams, p100, p, g))
    lines.append("-" * 66)
    lines.append("%-12s %8s %12s %10.1f" % ("\u5408\u8ba1", "", "", total))
    lines.append("")

    if unknown:
        lines.append("[\u5f85\u786e\u8ba4] \u4ee5\u4e0b\u98df\u7269\u672a\u6536\u5f55\uff0c\u672a\u8ba1\u5165\u5408\u8ba1\uff08\u4e0d\u51ed\u7a7a\u4f30\u7b97\uff09")
        for name, grams in unknown:
            lines.append("  - %s %g \u514b\uff1a\u8bf7\u67e5\u98df\u7269\u6210\u5206\u8868\u540e\u624b\u5de5\u8865\u5f55" % (name, grams))
        lines.append("")

    high = [(n, g, v) for n, g, _p, v, gr in rows if gr == "\u9ad8"]
    lines.append("[\u4e00] \u9700\u5220\u9664\u7684\u9ad8\u560c\u5464\u9879")
    if high:
        for n, g, v in high:
            lines.append("  - %s %g \u514b\uff08%.0f \u6beb\u514b\uff09\uff1a%s\u5e94\u53bb\u9664" % (n, g, v, "\u6025\u6027\u671f\u4e25\u683c" if stage == "acute" else "\u5efa\u8bae"))
    else:
        lines.append("  \u65e0")
    lines.append("")

    lines.append("[\u4e8c] \u8be5\u9910\u603b\u91cf\u5bf9\u6bd4")
    lines.append("  \u53c2\u8003\u4e0a\u9650\uff08%s\uff09\uff1a%.0f \u6beb\u514b" % (stage_text, limit))
    if total > limit:
        lines.append("  \u8d85\u51fa %.0f \u6beb\u514b\uff1a\u4f18\u5148\u5220\u9ad8\u560c\u5464\u9879\uff0c\u5176\u6b21\u538b\u4e2d\u560c\u5464\u4efd\u91cf" % (total - limit))
    else:
        lines.append("  \u672a\u8d85\u8fc7\u53c2\u8003\u4e0a\u9650 %.0f \u6beb\u514b" % limit)
    lines.append("")

    lines.append("[\u4e09] \u9152\u7cbe\u4e0e\u679c\u7cd6\u6838\u67e5\uff08\u6700\u5bb9\u6613\u6f0f\uff09")
    if alcohol:
        for n, g in alcohol:
            lines.append("  - \u68c0\u51fa\u9152\u7c7b\uff1a%s %g \u6beb\u5347/\u514b\u3002\u9152\u7cbe\u6291\u5236\u5c3f\u9178\u6392\u6cc4\uff0c\u6025\u6027\u671f\u5e94\u5b8c\u5168\u907f\u514d" % (n, g))
    else:
        lines.append("  \u672c\u9910\u672a\u8bb0\u5f55\u9152\u7c7b\uff0c\u8bf7\u81ea\u884c\u786e\u8ba4\u662f\u5426\u6f0f\u586b")
    lines.append("  \u542b\u7cd6\u996e\u6599\u3001\u679c\u6c41\u3001\u8702\u871c\u5c5e\u4e8e\u679c\u7cd6\u6765\u6e90\uff0c\u4e0d\u4f53\u73b0\u5728\u560c\u5464\u6570\u503c\u91cc\uff0c\u9700\u5355\u72ec\u6838\u5bf9")
    lines.append("")

    lines.append("[\u56db] \u6c64\u6c41\u7c7b\u63d0\u9192")
    lines.append("  \u706b\u9505\u6c64\u3001\u8001\u706b\u6c64\u3001\u6d53\u8089\u6c64\u7684\u560c\u5464\u6eb6\u51fa\u91cf\u9ad8\uff0c\u4e0d\u80fd\u7528\u56fa\u4f53\u91cd\u91cf\u4f30\u7b97\uff0c\u6309\u907f\u514d\u5904\u7406")
    lines.append("")

    lines.append("[\u4e94] \u53e3\u5f84\u8bf4\u660e")
    lines.append("  1. \u5206\u7ea7\u53e3\u5f84\uff1a\u4f4e\u4e8e 50 \u4e3a\u4f4e\uff0c50-150 \u4e3a\u4e2d\uff0c150 \u4ee5\u4e0a\u4e3a\u9ad8\uff08\u6bcf 100 \u514b\u6beb\u514b\uff09")
    lines.append("  2. \u6570\u503c\u4e3a\u901a\u7528\u98df\u7269\u6210\u5206\u8868\u8fd1\u4f3c\u503c\uff0c\u54c1\u79cd\u90e8\u4f4d\u505a\u6cd5\u5dee\u5f02\u8f83\u5927")
    lines.append("  3. \u5e72\u5236\u54c1\u6309\u5e72\u91cd\u8ba1\uff0c\u6ce1\u53d1\u540e\u9700\u6309\u5b9e\u9645\u5e72\u91cd\u6298\u7b97")
    lines.append("  4. \u4e0a\u9650\u4e3a\u7406\u89e3\u7528\u7684\u53c2\u8003\u503c\uff0c\u4e0d\u662f\u6cbb\u7597\u76ee\u6807")
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u81b3\u98df\u6838\u7b97\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u533b\u7597\u5efa\u8bae\u3002\u5c3f\u9178\u63a7\u5236\u76ee\u6807\u4e0e\u7528\u836f\u7531\u533b\u751f\u51b3\u5b9a\u3002")
    lines.append("=" * 66)

    summary = {
        "stage": stage,
        "total_purine": round(total, 2),
        "limit": limit,
        "over_limit": round(total - limit, 2),
        "high_items": [{"name": n, "grams": g, "purine": round(v, 2)} for n, g, v in high],
        "alcohol_items": [{"name": n, "grams": g} for n, g in alcohol],
        "unknown_items": [{"name": n, "grams": g} for n, g in unknown],
        "items": [{"name": n, "grams": g, "purine": round(v, 2), "grade": gr}
                  for n, g, _p, v, gr in rows],
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("\u732a\u809d 100 \u514b 275 \u6beb\u514b", abs(purine_of("\u732a\u809d", 100) - 275.0) < 1e-6))
    r.append(("\u732a\u809d 50 \u514b 137.5 \u6beb\u514b", abs(purine_of("\u732a\u809d", 50) - 137.5) < 1e-6))
    r.append(("\u672a\u6536\u5f55\u8fd4\u56de None", purine_of("\u725b\u809a", 100) is None))
    r.append(("\u732a\u809d\u5206\u7ea7\u4e3a\u9ad8", grade_of(275.0) == "\u9ad8"))
    r.append(("\u8c46\u8150\u5206\u7ea7\u4e3a\u4e2d", grade_of(55.0) == "\u4e2d"))
    r.append(("\u725b\u5976\u5206\u7ea7\u4e3a\u4f4e", grade_of(1.4) == "\u4f4e"))
    r.append(("\u5206\u754c 50 \u4e3a\u4e2d", grade_of(50.0) == "\u4e2d"))
    r.append(("\u5206\u754c 150 \u4e3a\u9ad8", grade_of(150.0) == "\u9ad8"))

    _, s = build_report({"stage": "acute", "items": [
        {"name": "\u732a\u809d", "grams": 80}, {"name": "\u7c73\u996d", "grams": 150}]})
    r.append(("\u6025\u6027\u671f\u4e0a\u9650 150", s["limit"] == 150.0))
    r.append(("\u5408\u8ba1 238.8", abs(s["total_purine"] - round(275.0 * 0.8 + 18.0 * 1.5, 2)) < 0.02))
    r.append(("\u732a\u809d\u5217\u5165\u9ad8\u5371\u9879", s["high_items"][0]["name"] == "\u732a\u809d"))
    r.append(("\u8d85\u4e0a\u9650", s["over_limit"] > 0))

    _, s2 = build_report({"stage": "chronic", "items": [
        {"name": "\u9752\u83dc", "grams": 200}, {"name": "\u9e21\u86cb", "grams": 100}]})
    r.append(("\u7f13\u89e3\u671f\u4e0a\u9650 300", s2["limit"] == 300.0))
    r.append(("\u4f4e\u560c\u5464\u9910\u672a\u8d85\u4e0a\u9650", s2["over_limit"] < 0))
    r.append(("\u4f4e\u560c\u5464\u9910\u65e0\u9ad8\u5371\u9879", s2["high_items"] == []))

    _, s3 = build_report({"stage": "acute", "items": [
        {"name": "\u5564\u9152", "grams": 500}]})
    r.append(("\u9152\u7c7b\u8bc6\u522b", s3["alcohol_items"][0]["name"] == "\u5564\u9152"))

    _, s4 = build_report({"stage": "acute", "items": [{"name": "\u725b\u809a", "grams": 100}]})
    r.append(("\u672a\u6536\u5f55\u4e0d\u8ba1\u5165", s4["total_purine"] == 0.0))
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
    parser = argparse.ArgumentParser(description="\u75db\u98ce\u4e00\u9910\u560c\u5464\u6838\u7b97\u5de5\u5177")
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
