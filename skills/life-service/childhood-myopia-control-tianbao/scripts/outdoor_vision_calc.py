# -*- coding: utf-8 -*-
"""\u513f\u7ae5\u6237\u5916\u65f6\u957f\u4e0e\u7528\u773c\u8d1f\u8377\u5468\u8fbe\u6807\u6838\u7b97\u5de5\u5177\u3002

\u7528\u6cd5:
  python outdoor_vision_calc.py --file week.json [--json]
  python outdoor_vision_calc.py --selftest

\u4ec5\u4f5c\u8bb0\u5f55\u4e0e\u8fbe\u6807\u5224\u5b9a\uff0c\u4e0d\u6d89\u53ca\u4efb\u4f55\u533b\u7597\u5904\u7f6e\u3002
"""
import argparse
import io
import json
import os
import sys

DAILY_OUTDOOR_TARGET = 120.0   # \u5206\u949f
WEEKLY_OUTDOOR_TARGET = 840.0  # \u5206\u949f
NEAR_LIMIT = {"preschool": 20.0, "primary": 40.0, "teen": 50.0}
SCREEN_LIMIT = {"preschool": 60.0, "primary": 120.0, "teen": 120.0}
AGE_TEXT = {"preschool": "3-6 \u5c81", "primary": "6-12 \u5c81", "teen": "12-18 \u5c81"}


def age_group(age):
    a = float(age or 0)
    if a < 3:
        return "preschool"
    if a < 6:
        return "preschool"
    if a < 12:
        return "primary"
    return "teen"


def near_limit(age):
    return NEAR_LIMIT[age_group(age)]


def screen_limit(age):
    return SCREEN_LIMIT[age_group(age)]


def build_report(data):
    age = data.get("age", 8)
    days = data.get("days", [])
    group = age_group(age)
    nl = near_limit(age)
    sl = screen_limit(age)

    total_out = 0.0
    total_near = 0.0
    total_screen = 0.0
    ok_days = 0
    max_near = 0.0
    bad_days = []
    for d in days:
        out = float(d.get("outdoor_minutes", 0) or 0)
        near = float(d.get("near_work_minutes", 0) or 0)
        screen = float(d.get("screen_minutes", 0) or 0)
        longest = float(d.get("longest_continuous_minutes", 0) or 0)
        total_out += out
        total_near += near
        total_screen += screen
        if out >= DAILY_OUTDOOR_TARGET:
            ok_days += 1
        if longest > max_near:
            max_near = longest
        if longest > nl:
            bad_days.append((d.get("label", "?"), longest))

    n = len(days) if days else 1
    avg_out = total_out / n
    avg_screen = total_screen / n
    gap = DAILY_OUTDOOR_TARGET - avg_out

    lines = []
    lines.append("=" * 66)
    lines.append("\u513f\u7ae5\u6237\u5916\u65f6\u957f\u4e0e\u7528\u773c\u8d1f\u8377\u5468\u6838\u7b97")
    lines.append("=" * 66)
    lines.append("\u5e74\u9f84\uff1a%g \u5c81   \u9002\u7528\u5206\u7ec4\uff1a%s" % (float(age or 0), AGE_TEXT[group]))
    if float(age or 0) < 3:
        lines.append("\u6ce8\uff1a3 \u5c81\u4ee5\u4e0b\u5e84\u5e55\u65f6\u95f4\u53e3\u5f84\u66f4\u4e25\uff0c\u5e94\u5c3d\u91cf\u907f\u514d\u63a5\u89e6\u7535\u5b50\u5c4f\u5e55\uff0c\u672c\u5206\u7ec4\u4ec5\u4f5c\u4fdd\u5b88\u53c2\u8003")
    lines.append("\u8bb0\u5f55\u5929\u6570\uff1a%d \u5929" % len(days))
    lines.append("")
    lines.append("[\u4e00] \u6237\u5916\u65f6\u957f")
    lines.append("  \u6bcf\u65e5\u76ee\u6807\uff1a%g \u5206\u949f   \u6bcf\u5468\u76ee\u6807\uff1a%g \u5206\u949f" % (DAILY_OUTDOOR_TARGET, WEEKLY_OUTDOOR_TARGET))
    lines.append("  \u672c\u5468\u5408\u8ba1\uff1a%g \u5206\u949f   \u65e5\u5747\uff1a%.1f \u5206\u949f   \u8fbe\u6807\u5929\u6570\uff1a%d/%d" % (
        total_out, avg_out, ok_days, len(days)))
    if gap > 0:
        lines.append("  \u65e5\u5747\u7f3a\u53e3 %.1f \u5206\u949f\uff0c\u5efa\u8bae\u6bcf\u5929\u8865 %.0f \u5206\u949f" % (gap, min(gap, 60.0)))
    else:
        lines.append("  \u65e5\u5747\u8fbe\u6807\uff0c\u7ee7\u7eed\u4fdd\u6301")
    if total_out < WEEKLY_OUTDOOR_TARGET * len(days) / 7.0:
        lines.append("  \u5468\u7d2f\u8ba1\u672a\u8fbe %g \u5206\u949f\uff0c\u6237\u5916\u5e94\u5206\u6563\u5230\u6bcf\u5929\uff0c\u4e0d\u5b9c\u5468\u672b\u96c6\u4e2d\u8865" % WEEKLY_OUTDOOR_TARGET)
    lines.append("  \u8ba1\u5165\u53e3\u5f84\uff1a\u4ec5\u6237\u5916\u81ea\u7136\u5149\u7167\u4e0b\u7684\u6d3b\u52a8\uff0c\u5ba4\u5185\u4f53\u80b2\u9986\u4e0e\u8f66\u5185\u4e0d\u8ba1\u5165")
    lines.append("")
    lines.append("[\u4e8c] \u8fd1\u8ddd\u79bb\u7528\u773c")
    lines.append("  \u672c\u5468\u5408\u8ba1\uff1a%g \u5206\u949f   \u65e5\u5747\uff1a%.1f \u5206\u949f" % (total_near, total_near / n))
    lines.append("  \u5355\u6b21\u8fde\u7eed\u4e0a\u9650\uff08%s\uff09\uff1a%g \u5206\u949f" % (AGE_TEXT[group], nl))
    lines.append("  \u8bb0\u5f55\u5230\u7684\u6700\u957f\u8fde\u7eed\uff1a%g \u5206\u949f" % max_near)
    if bad_days:
        lines.append("  \u8d85\u4e0a\u9650\u7684\u5929\u6570\uff1a")
        for label, v in bad_days:
            lines.append("    - %s \u8fde\u7eed %g \u5206\u949f\uff0c\u5e94\u6bcf %g \u5206\u949f\u4f11\u606f 10 \u5206\u949f" % (label, v, nl))
    else:
        lines.append("  \u672a\u8d85\u8fc7\u5355\u6b21\u8fde\u7eed\u4e0a\u9650")
    lines.append("")
    lines.append("[\u4e09] \u5c4f\u5e55\u65f6\u95f4")
    lines.append("  \u5a31\u4e50\u5c4f\u5e55\u65e5\u5747\u4e0a\u9650\uff08%s\uff09\uff1a%g \u5206\u949f" % (AGE_TEXT[group], sl))
    lines.append("  \u672c\u5468\u5408\u8ba1\uff1a%g \u5206\u949f   \u65e5\u5747\uff1a%.1f \u5206\u949f" % (total_screen, avg_screen))
    if avg_screen > sl:
        lines.append("  \u8d85\u51fa %.1f \u5206\u949f\uff1a\u4f18\u5148\u780d\u5a31\u4e50\u5c4f\u5e55\uff0c\u5b66\u4e60\u7528\u9014\u53e6\u8bbe\u4f11\u606f" % (avg_screen - sl))
    else:
        lines.append("  \u672a\u8d85\u51fa\u65e5\u5747\u4e0a\u9650")
    lines.append("")
    lines.append("[\u56db] \u53e3\u5f84\u8bf4\u660e")
    lines.append("  1. \u8fd1\u8ddd\u79bb\u7528\u773c\u542b\u4f5c\u4e1a\u3001\u9605\u8bfb\u3001\u7ec3\u7434\u3001\u753b\u753b\u3001\u62fc\u642d\u4e0e\u5c4f\u5e55\uff0c\u4e0d\u53ea\u770b\u624b\u673a")
    lines.append("  2. \u4f11\u606f\u5e94\u79bb\u5f00\u5ea7\u4f4d\u8fdc\u773a\uff0c\u4e0d\u662f\u4ece\u624b\u673a\u6362\u6210\u5e73\u677f")
    lines.append("  3. \u591c\u95f4\u6237\u5916\u5149\u7167\u5f3a\u5ea6\u8fdc\u4f4e\u4e8e\u767d\u5929\uff0c\u4e0d\u80fd\u7b49\u540c\u66ff\u4ee3")
    lines.append("  4. \u6570\u503c\u53e3\u5f84\u4ee5\u6700\u65b0\u7248\u6307\u5357\u548c\u773c\u79d1\u533b\u5e08\u5224\u65ad\u4e3a\u51c6")
    lines.append("")
    lines.append("[\u4e94] \u5c31\u533b\u7ea2\u7ebf\u63d0\u793a")
    lines.append("  \u51fa\u73b0\u89c6\u529b\u9aa4\u964d\u3001\u772f\u773c\u6b6a\u5934\u3001\u773c\u4f4d\u504f\u659c\u3001\u773c\u7403\u6296\u52a8\u3001\u77b3\u5b54\u53d1\u767d\u3001")
    lines.append("  \u773c\u7ea2\u75db\u4f34\u89c6\u529b\u4e0b\u964d\u3001\u773c\u5916\u4f24\uff0c\u5e94\u5c3d\u5feb\u5230\u773c\u79d1\u5c31\u8bca\uff0c\u4e0d\u4ee5\u672c\u8868\u66ff\u4ee3\u5c31\u8bca\u3002")
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u8bb0\u5f55\u6838\u7b97\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u8bca\u7597\u610f\u89c1\u3002")
    lines.append("=" * 66)

    summary = {
        "age": age,
        "age_group": group,
        "days": len(days),
        "total_outdoor": total_out,
        "avg_outdoor": round(avg_out, 2),
        "outdoor_ok_days": ok_days,
        "outdoor_gap_per_day": round(gap, 2),
        "total_near": total_near,
        "longest_continuous": max_near,
        "near_limit": nl,
        "total_screen": total_screen,
        "avg_screen": round(avg_screen, 2),
        "screen_limit": sl,
        "over_near_limit_days": [{"label": l, "minutes": v} for l, v in bad_days],
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("2 \u5c81\u5f52\u5165\u5b66\u9f84\u524d\u7ec4", age_group(2) == "preschool"))
    r.append(("8 \u5c81\u5f52\u5165\u5c0f\u5b66\u7ec4", age_group(8) == "primary"))
    r.append(("15 \u5c81\u5f52\u5165\u5c11\u5e74\u7ec4", age_group(15) == "teen"))
    r.append(("\u5b66\u9f84\u524d\u8fd1\u8ddd\u79bb\u4e0a\u9650 20", near_limit(5) == 20.0))
    r.append(("\u5c0f\u5b66\u8fd1\u8ddd\u79bb\u4e0a\u9650 40", near_limit(8) == 40.0))
    r.append(("\u5c11\u5e74\u5c4f\u5e55\u4e0a\u9650 120", screen_limit(15) == 120.0))

    days = [
        {"label": "\u4e00", "outdoor_minutes": 150, "near_work_minutes": 180,
         "screen_minutes": 60, "longest_continuous_minutes": 30},
        {"label": "\u4e8c", "outdoor_minutes": 60, "near_work_minutes": 240,
         "screen_minutes": 90, "longest_continuous_minutes": 55},
    ]
    _, s = build_report({"age": 9, "days": days})
    r.append(("\u6237\u5916\u5408\u8ba1 210", abs(s["total_outdoor"] - 210.0) < 1e-9))
    r.append(("\u8fbe\u6807 1 \u5929", s["outdoor_ok_days"] == 1))
    r.append(("\u65e5\u5747\u6237\u5916 105", abs(s["avg_outdoor"] - 105.0) < 1e-9))
    r.append(("\u65e5\u5747\u7f3a\u53e3 15", abs(s["outdoor_gap_per_day"] - 15.0) < 1e-9))
    r.append(("\u6700\u957f\u8fde\u7eed 55", s["longest_continuous"] == 55.0))
    r.append(("\u8d85\u4e0a\u9650 1 \u5929", len(s["over_near_limit_days"]) == 1))
    r.append(("\u8d85\u4e0a\u9650\u4e3a\u5468\u4e8c", s["over_near_limit_days"][0]["label"] == "\u4e8c"))

    days2 = [{"label": "\u4e00", "outdoor_minutes": 130, "near_work_minutes": 100,
              "screen_minutes": 30, "longest_continuous_minutes": 20}]
    _, s2 = build_report({"age": 9, "days": days2})
    r.append(("\u5168\u8fbe\u6807\u65e0\u8d85\u9650", s2["over_near_limit_days"] == []))
    r.append(("\u7f3a\u53e3\u4e3a\u8d1f\u8868\u793a\u8fbe\u6807", s2["outdoor_gap_per_day"] < 0))

    _, s3 = build_report({"age": 9, "days": []})
    r.append(("\u7a7a\u8bb0\u5f55\u4e0d\u62a5\u9519", s3["days"] == 0))
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
    parser = argparse.ArgumentParser(description="\u513f\u7ae5\u6237\u5916\u65f6\u957f\u4e0e\u7528\u773c\u8d1f\u8377\u6838\u7b97\u5de5\u5177")
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
