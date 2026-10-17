# -*- coding: utf-8 -*-
"""\u7cd6\u5c3f\u75c5\u4e00\u9910\u78b3\u6c34\u6838\u7b97\u4e0e\u98df\u7269\u4ea4\u6362\u4efd\u901f\u7b97\u5de5\u5177\u3002

\u7528\u6cd5:
  python carb_exchange_calc.py --file meal.json [--json]
  python carb_exchange_calc.py --selftest

\u78b3\u6c34\u6570\u503c\u4e3a\u901a\u7528\u98df\u7269\u6210\u5206\u8868\u53e3\u5f84\uff08\u6bcf 100 \u514b\u53ef\u98df\u90e8\uff09\uff0c\u54c1\u79cd\u4e0e\u505a\u6cd5\u5dee\u5f02\u8f83\u5927\u3002
\u672a\u6536\u5f55\u7684\u98df\u7269\u4e0d\u4f1a\u51ed\u7a7a\u4f30\u7b97\uff0c\u5217\u5165\u5f85\u786e\u8ba4\u9879\u3002
"""
import argparse
import io
import json
import os
import sys

# \u6bcf 100 \u514b\uff08\u6216 100 \u6beb\u5347\uff09\u53ef\u98df\u90e8\u78b3\u6c34\u514b\u6570\uff0c\u8fd1\u4f3c\u503c
FOODS = {
    "\u7c73\u996d": (26.0, "\u719f", "\u9ad8"),
    "\u5927\u7c73": (77.0, "\u751f", "\u9ad8"),
    "\u9992\u5934": (47.0, "\u719f", "\u9ad8"),
    "\u9762\u6761": (25.0, "\u716e", "\u4e2d"),
    "\u6302\u9762": (70.0, "\u5e72", "\u4e2d"),
    "\u5168\u9ea6\u9762\u5305": (45.0, "\u719f", "\u4e2d"),
    "\u71d5\u9ea6\u7247": (60.0, "\u5e72", "\u4e2d"),
    "\u7ea2\u85af": (25.0, "\u751f", "\u4e2d"),
    "\u571f\u8c46": (17.0, "\u751f", "\u9ad8"),
    "\u7389\u7c73": (22.0, "\u9c9c", "\u4e2d"),
    "\u5c0f\u7c73": (75.0, "\u751f", "\u4e2d"),
    "\u5c71\u836f": (12.0, "\u751f", "\u4f4e"),
    "\u5357\u74dc": (6.0, "\u751f", "\u9ad8"),
    "\u82f9\u679c": (13.5, "\u751f", "\u4f4e"),
    "\u9999\u8549": (22.0, "\u751f", "\u4e2d"),
    "\u6a59\u5b50": (11.0, "\u751f", "\u4f4e"),
    "\u897f\u74dc": (6.0, "\u751f", "\u9ad8"),
    "\u8461\u8404": (16.0, "\u751f", "\u4e2d"),
    "\u68a8": (13.0, "\u751f", "\u4f4e"),
    "\u725b\u5976": (5.0, "\u6db2\u4f53", "\u4f4e"),
    "\u65e0\u7cd6\u9178\u5976": (5.0, "\u6db2\u4f53", "\u4f4e"),
    "\u65e0\u7cd6\u8c46\u6d46": (1.5, "\u6db2\u4f53", "\u4f4e"),
    "\u8c46\u8150": (3.0, "\u719f", "\u4f4e"),
    "\u9e21\u86cb": (1.5, "\u719f", "\u4f4e"),
    "\u9e21\u80f8\u8089": (0.0, "\u719f", "\u4f4e"),
    "\u9752\u83dc": (3.0, "\u719f", "\u4f4e"),
    "\u9ec4\u74dc": (3.0, "\u751f", "\u4f4e"),
    "\u756a\u8304": (4.0, "\u751f", "\u4f4e"),
}
UNIT_PER = 20.0  # \u4e00\u4efd\u8c37\u85af\u7c7b\u7ea6\u542b\u78b3\u6c34 20 \u514b
GI_TEXT = {"\u4f4e": "\u4f4e\u5347\u7cd6\u6307\u6570", "\u4e2d": "\u4e2d\u5347\u7cd6\u6307\u6570", "\u9ad8": "\u9ad8\u5347\u7cd6\u6307\u6570"}


def carb_of(name, grams):
    """\u8fd4\u56de\u8be5\u9879\u78b3\u6c34\u514b\u6570\uff1b\u672a\u6536\u5f55\u8fd4\u56de None\u3002"""
    if name not in FOODS:
        return None
    return FOODS[name][0] * float(grams) / 100.0


def units_of(carb):
    return float(carb) / UNIT_PER


def gi_of(name):
    if name in FOODS:
        return FOODS[name][2]
    return None


def build_report(data):
    items = data.get("items", [])
    target = data.get("target_carb", None)

    rows = []
    unknown = []
    total = 0.0
    for it in items:
        name = it.get("name", "")
        grams = float(it.get("grams", 0) or 0)
        c = carb_of(name, grams)
        if c is None:
            unknown.append((name, grams))
            continue
        state = FOODS[name][1]
        gi = gi_of(name)
        rows.append((name, grams, state, c, units_of(c), gi))
        total += c

    lines = []
    lines.append("=" * 66)
    lines.append("\u4e00\u9910\u78b3\u6c34\u6838\u7b97\u4e0e\u98df\u7269\u4ea4\u6362\u4efd")
    lines.append("=" * 66)
    lines.append("%-12s %8s %6s %10s %8s  %s" % ("\u98df\u7269", "\u91cd\u91cfg", "\u72b6\u6001", "\u78b3\u6c34g", "\u4ea4\u6362\u4efd", "\u5347\u7cd6"))
    lines.append("-" * 66)
    for name, grams, state, c, u, gi in rows:
        lines.append("%-12s %8g %6s %10.1f %8.2f  %s" % (name, grams, state, c, u, GI_TEXT[gi]))
    lines.append("-" * 66)
    lines.append("%-12s %8s %6s %10.1f %8.2f" % ("\u5408\u8ba1", "", "", total, units_of(total)))
    lines.append("")

    if unknown:
        lines.append("[\u5f85\u786e\u8ba4] \u4ee5\u4e0b\u98df\u7269\u672a\u6536\u5f55\uff0c\u672a\u8ba1\u5165\u5408\u8ba1\uff08\u4e0d\u51ed\u7a7a\u4f30\u7b97\uff09")
        for name, grams in unknown:
            lines.append("  - %s %g \u514b\uff1a\u8bf7\u67e5\u98df\u7269\u6210\u5206\u8868\u6216\u8425\u517b\u79e4 App \u540e\u624b\u5de5\u8865\u5f55" % (name, grams))
        lines.append("")

    if target is not None:
        t = float(target)
        lines.append("[\u76ee\u6807\u5bf9\u6bd4] \u8be5\u9910\u78b3\u6c34\u76ee\u6807 %.1f \u514b" % t)
        diff = total - t
        if diff > 0.5:
            lines.append("  \u8d85\u51fa %.1f \u514b\uff08\u7ea6 %.2f \u4efd\uff09\uff1a\u4f18\u5148\u51cf\u4e3b\u98df\u548c\u6c34\u679c\uff0c\u4e0d\u8981\u51cf\u852c\u83dc\u4e0e\u86cb\u767d\u8d28" % (
                diff, units_of(diff)))
        elif diff < -0.5:
            lines.append("  \u4f4e\u4e8e\u76ee\u6807 %.1f \u514b\uff1a\u6ce8\u610f\u662f\u5426\u4e3b\u98df\u8fc7\u5c11\uff0c\u957f\u671f\u8fc7\u5c11\u6709\u4f4e\u8840\u7cd6\u4e0e\u916e\u75c7\u98ce\u9669" % (-diff))
        else:
            lines.append("  \u57fa\u672c\u8fbe\u6807\uff08\u5bb9\u5dee 0.5 \u514b\u4ee5\u5185\uff09")
        lines.append("")

    high = [n for n, _, _, _, _, g in rows if g == "\u9ad8"]
    if high:
        lines.append("[\u5347\u7cd6\u63d0\u793a] \u542b\u9ad8\u5347\u7cd6\u6307\u6570\u98df\u7269\uff1a%s" % "\u3001".join(high))
        lines.append("  \u5efa\u8bae\uff1a\u4e0e\u852c\u83dc\u548c\u86cb\u767d\u8d28\u540c\u5403\u3001\u7f29\u77ed\u71ac\u716e\u65f6\u95f4\u3001\u6539\u6574\u7c92\u6216\u5e72\u996d\u5f62\u6001")
        lines.append("")

    lines.append("[\u53e3\u5f84\u8bf4\u660e]")
    lines.append("  1. \u4ea4\u6362\u4efd\u53e3\u5f84\uff1a\u4e00\u4efd\u8c37\u85af\u7c7b\u7ea6\u542b\u78b3\u6c34 %.0f \u514b" % UNIT_PER)
    lines.append("  2. \u78b3\u6c34\u503c\u4e3a\u901a\u7528\u98df\u7269\u6210\u5206\u8868\u8fd1\u4f3c\u503c\uff0c\u54c1\u79cd\u4ea7\u5730\u505a\u6cd5\u5dee\u5f02\u8f83\u5927")
    lines.append("  3. \u91cd\u91cf\u987b\u533a\u5206\u751f\u91cd\u4e0e\u53ef\u98df\u90e8\uff0c\u719f\u7c73\u996d\u4e0e\u751f\u5927\u7c73\u4e0d\u80fd\u6df7\u7528")
    lines.append("  4. \u76ee\u6807\u503c\u987b\u7531\u533b\u751f\u6216\u8425\u517b\u5e08\u4e2a\u4f53\u5316\u8bbe\u5b9a")
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u81b3\u98df\u6838\u7b97\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u533b\u7597\u5efa\u8bae\u6216\u8425\u517b\u5904\u65b9\u3002")
    lines.append("=" * 66)

    summary = {
        "total_carb": round(total, 2),
        "total_units": round(units_of(total), 3),
        "target_carb": target,
        "over_target": (round(total - float(target), 2) if target is not None else None),
        "high_gi_items": high,
        "unknown_items": [{"name": n, "grams": g} for n, g in unknown],
        "items": [{"name": n, "grams": g, "carb": round(c, 2), "units": round(u, 3), "gi": gi}
                  for n, g, _s, c, u, gi in rows],
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("\u7c73\u996d 150 \u514b\u78b3\u6c34 39", abs(carb_of("\u7c73\u996d", 150) - 39.0) < 1e-6))
    r.append(("\u9992\u5934 50 \u514b\u78b3\u6c34 23.5", abs(carb_of("\u9992\u5934", 50) - 23.5) < 1e-6))
    r.append(("\u672a\u6536\u5f55\u98df\u7269\u8fd4\u56de None", carb_of("\u69b4\u83b2", 100) is None))
    r.append(("\u4ea4\u6362\u4efd\u6362\u7b97", abs(units_of(40.0) - 2.0) < 1e-9))
    r.append(("\u7c73\u996d GI \u4e3a\u9ad8", gi_of("\u7c73\u996d") == "\u9ad8"))
    r.append(("\u82f9\u679c GI \u4e3a\u4f4e", gi_of("\u82f9\u679c") == "\u4f4e"))

    _, s = build_report({"items": [
        {"name": "\u7c73\u996d", "grams": 150},
        {"name": "\u9992\u5934", "grams": 50},
        {"name": "\u725b\u5976", "grams": 200},
    ], "target_carb": 60})
    r.append(("\u5408\u8ba1\u78b3\u6c34 72.5", abs(s["total_carb"] - 72.5) < 1e-6))
    r.append(("\u8d85\u76ee\u6807 12.5", abs(s["over_target"] - 12.5) < 1e-6))
    r.append(("\u9ad8\u5347\u7cd6\u9879\u8bc6\u522b", "\u7c73\u996d" in s["high_gi_items"]))
    r.append(("\u65e0\u672a\u6536\u5f55\u9879", s["unknown_items"] == []))

    _, s2 = build_report({"items": [{"name": "\u69b4\u83b2", "grams": 100}], "target_carb": 50})
    r.append(("\u672a\u6536\u5f55\u4e0d\u8ba1\u5165\u5408\u8ba1", s2["total_carb"] == 0.0))
    r.append(("\u672a\u6536\u5f55\u5217\u5165\u5f85\u786e\u8ba4", s2["unknown_items"][0]["name"] == "\u69b4\u83b2"))

    _, s3 = build_report({"items": [{"name": "\u82f9\u679c", "grams": 100}], "target_carb": 60})
    r.append(("\u4f4e\u4e8e\u76ee\u6807\u4e3a\u8d1f", s3["over_target"] < 0))

    _, s4 = build_report({"items": [{"name": "\u7c73\u996d", "grams": 100}], "target_carb": 26})
    r.append(("\u8fbe\u6807\u5224\u5b9a", abs(s4["over_target"]) < 0.5))
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
    parser = argparse.ArgumentParser(description="\u7cd6\u5c3f\u75c5\u4e00\u9910\u78b3\u6c34\u6838\u7b97\u5de5\u5177")
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
