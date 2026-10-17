# -*- coding: utf-8 -*-
"""\u9888\u690e\u8d1f\u8377\u81ea\u67e5\u6253\u5206\u4e0e\u953b\u70bc\u9891\u6b21\u6838\u5bf9\u5de5\u5177\u3002

\u7528\u6cd5:
  python cervical_load_check.py --file case.json [--json]
  python cervical_load_check.py --selftest

\u547d\u4e2d\u5c31\u533b\u7ea2\u7ebf\u65f6\u53ea\u8f93\u51fa\u5c31\u533b\u63d0\u793a\uff0c\u4e0d\u8f93\u51fa\u4efb\u4f55\u953b\u70bc\u65b9\u6848\u3002
"""
import argparse
import io
import json
import os
import sys

RED_FLAGS = [
    "hand_numbness",      # \u624b\u9ebb\u6216\u4e0a\u80a2\u65e0\u529b
    "gait_unsteady",      # \u8d70\u8def\u53d1\u98d8\u8e29\u68c9\u611f
    "bowel_bladder",      # \u5927\u5c0f\u4fbf\u969c\u788d\u6216\u4f1a\u9634\u9ebb\u6728
    "radiating_pain",     # \u4e0a\u80a2\u653e\u5c04\u75db\u6301\u7eed\u52a0\u91cd
    "dizziness_neuro",    # \u5934\u6655\u4f34\u590d\u89c6\u8bf4\u8bdd\u4e0d\u6e05\u541e\u54bd\u56f0\u96be
    "trauma",             # \u5916\u4f24\u540e\u9888\u75db
    "fever_neck",         # \u9888\u75db\u4f34\u53d1\u70ed\u4f53\u91cd\u4e0b\u964d
    "severe_headache",    # \u9888\u75db\u4f34\u5267\u70c8\u5934\u75db\u6076\u5fc3\u610f\u8bc6\u6539\u53d8
]
RED_FLAG_TEXT = {
    "hand_numbness": "\u624b\u6216\u624b\u6307\u9ebb\u6728\u65e0\u529b\u3001\u63e1\u529b\u4e0b\u964d",
    "gait_unsteady": "\u8d70\u8def\u53d1\u98d8\u3001\u8e29\u68c9\u82b1\u611f\u3001\u6613\u7eca\u5012",
    "bowel_bladder": "\u5927\u5c0f\u4fbf\u969c\u788d\u6216\u4f1a\u9634\u533a\u9ebb\u6728",
    "radiating_pain": "\u4e0a\u80a2\u653e\u5c04\u75db\u6301\u7eed\u52a0\u91cd\u6216\u591c\u95f4\u75db\u660e\u663e",
    "dizziness_neuro": "\u5934\u6655\u4f34\u89c6\u7269\u65cb\u8f6c\u3001\u590d\u89c6\u3001\u8bf4\u8bdd\u4e0d\u6e05\u3001\u541e\u54bd\u56f0\u96be",
    "trauma": "\u5916\u4f24\u540e\u9888\u75db",
    "fever_neck": "\u9888\u75db\u4f34\u53d1\u70ed\u3001\u4f53\u91cd\u660e\u663e\u4e0b\u964d\u3001\u591c\u95f4\u76d7\u6c57",
    "severe_headache": "\u9888\u75db\u4f34\u5267\u70c8\u5934\u75db\u3001\u6076\u5fc3\u5455\u5410\u6216\u610f\u8bc6\u6539\u53d8",
}
EMERGENCY_FLAGS = ("bowel_bladder", "dizziness_neuro", "trauma", "severe_headache")


def break_penalty(interval_min):
    """\u8d77\u8eab\u6d3b\u52a8\u95f4\u9694\u60e9\u7f5a\u5206\u3002"""
    v = float(interval_min or 0)
    if v <= 0:
        return 3.0
    if v <= 30:
        return 0.0
    if v <= 60:
        return 1.0
    if v <= 90:
        return 2.0
    return 3.0


def exercise_gap(days):
    """\u6bcf\u5468\u953b\u70bc\u5929\u6570\u7f3a\u53e3\uff0c\u76ee\u6807 5 \u5929\uff0c\u6700\u591a\u8bb0 5 \u5206\u3002"""
    d = float(days or 0)
    gap = 5.0 - d
    if gap < 0:
        return 0.0
    if gap > 5.0:
        return 5.0
    return gap


def load_score(screen_hours, phone_hours, screen_below_eye, interval_min, days):
    s = 0.0
    s += min(float(screen_hours or 0), 12.0) * 1.0
    s += min(float(phone_hours or 0), 8.0) * 1.5
    s += 3.0 if screen_below_eye else 0.0
    s += break_penalty(interval_min)
    s += exercise_gap(days)
    return round(s, 2)


def load_level(score):
    if score <= 10:
        return "\u4f4e\u8d1f\u8377"
    if score <= 20:
        return "\u4e2d\u8d1f\u8377"
    return "\u9ad8\u8d1f\u8377"


def action_count(level):
    return {"\u4f4e\u8d1f\u8377": 3, "\u4e2d\u8d1f\u8377": 4, "\u9ad8\u8d1f\u8377": 5}[level]


def pain_rule(pain_score, pain_after):
    """\u75bc\u75db\u505c\u6b62\u539f\u5219\u5224\u5b9a\u3002"""
    p = float(pain_score or 0)
    if pain_after == "worse":
        return "\u75bc\u75db\u52a0\u91cd\uff1a\u8be5\u52a8\u4f5c\u51cf\u534a\u6b21\u6570\u6216\u9000\u56de\u4e0a\u4e00\u6863\uff0c\u6b21\u65e5\u4ecd\u52a0\u91cd\u5219\u6682\u505c 2 \u5929"
    if pain_after == "numbness":
        return "\u51fa\u73b0\u653e\u5c04\u75db\u6216\u9ebb\u6728\uff1a\u7acb\u5373\u505c\u6b62\u8be5\u52a8\u4f5c\uff0c\u672c\u8f6e\u4e0d\u518d\u505a\uff0c\u5e76\u5c3d\u5feb\u5c31\u533b\u8bc4\u4f30"
    if pain_after == "dizzy":
        return "\u51fa\u73b0\u5934\u6655\u89c6\u7269\u65cb\u8f6c\uff1a\u7acb\u5373\u505c\u6b62\u5e76\u5750\u4e0b\u4f11\u606f\uff0c\u53cd\u590d\u51fa\u73b0\u9700\u5c31\u533b"
    if p >= 7:
        return "\u75bc\u75db\u57fa\u7ebf\u504f\u9ad8\uff087 \u5206\u53ca\u4ee5\u4e0a\uff09\uff1a\u5148\u51cf\u5c11\u4e45\u5750\u8d1f\u8377\uff0c\u52a8\u4f5c\u4ee5\u7b49\u957f\u548c\u9000\u9636\u7248\u672c\u4e3a\u4e3b"
    if p >= 4:
        return "\u75bc\u75db\u57fa\u7ebf\u4e2d\u7b49\uff1a\u52a8\u4f5c\u5e45\u5ea6\u63a7\u5236\u5728\u65e0\u75db\u8303\u56f4\u7684\u4e03\u6210\u4ee5\u5185"
    return "\u75bc\u75db\u57fa\u7ebf\u8f83\u4f4e\uff1a\u53ef\u6309\u6807\u51c6\u5242\u91cf\u6267\u884c\uff0c\u6bcf 1-2 \u5468\u5c0f\u5e45\u8fdb\u9636"


def build_report(data):
    screen_hours = data.get("screen_hours", 0)
    phone_hours = data.get("phone_hours", 0)
    screen_below_eye = bool(data.get("screen_below_eye", False))
    interval_min = data.get("break_interval_min", 60)
    days = data.get("exercise_days_per_week", 0)
    pain_score = data.get("pain_score", 0)
    pain_after = data.get("pain_after", "none")
    flags = [f for f in data.get("red_flags", []) if f in RED_FLAGS]

    lines = []
    lines.append("=" * 62)
    lines.append("\u9888\u690e\u8d1f\u8377\u81ea\u67e5\u4e0e\u953b\u70bc\u9891\u6b21\u6838\u5bf9")
    lines.append("=" * 62)

    if flags:
        lines.append("")
        lines.append("[\u7d27\u6025] \u547d\u4e2d\u5c31\u533b\u7ea2\u7ebf\uff0c\u4e0d\u8f93\u51fa\u4efb\u4f55\u953b\u70bc\u65b9\u6848")
        lines.append("-" * 62)
        for f in flags:
            tag = "\u6025\u8bca" if f in EMERGENCY_FLAGS else "\u5c3d\u5feb\u5c31\u8bca"
            lines.append("  [%s] %s" % (tag, RED_FLAG_TEXT[f]))
        lines.append("")
        lines.append("\u5904\u7f6e\uff1a\u7acb\u5373\u505c\u6b62\u81ea\u884c\u953b\u70bc\u3001\u6309\u6469\u3001\u7275\u5f15\u548c\u6b63\u9aa8\uff0c\u5c3d\u5feb\u5230\u9aa8\u79d1\u6216\u795e\u7ecf\u5916\u79d1\u8bc4\u4f30\u3002")
        lines.append("\u82e5\u51fa\u73b0\u5927\u5c0f\u4fbf\u969c\u788d\u3001\u4f1a\u9634\u9ebb\u6728\u3001\u80a2\u4f53\u65e0\u529b\u6216\u5916\u4f24\u540e\u9888\u75db\uff0c\u76f4\u63a5\u53bb\u6025\u8bca\u3002")
        lines.append("")
        lines.append("\u514d\u8d23\uff1a\u672c\u8f93\u51fa\u4e3a\u5c31\u533b\u63d0\u793a\uff0c\u4e0d\u6784\u6210\u8bca\u65ad\u3002")
        lines.append("=" * 62)
        summary = {
            "red_flag_hit": True,
            "flags": flags,
            "emergency": [f for f in flags if f in EMERGENCY_FLAGS],
            "exercise_blocked": True,
            "load_score": None,
            "load_level": None,
        }
        return "\n".join(lines), summary

    score = load_score(screen_hours, phone_hours, screen_below_eye, interval_min, days)
    level = load_level(score)
    cnt = action_count(level)
    gap = exercise_gap(days)

    lines.append("\u6bcf\u65e5\u5c4f\u5e55\u65f6\u957f\uff1a%g \u5c0f\u65f6   \u624b\u673a\u4f4e\u5934\u65f6\u957f\uff1a%g \u5c0f\u65f6" % (
        float(screen_hours or 0), float(phone_hours or 0)))
    lines.append("\u5c4f\u5e55\u4f4e\u4e8e\u89c6\u7ebf\uff1a%s   \u8d77\u8eab\u95f4\u9694\uff1a%g \u5206\u949f   \u6bcf\u5468\u953b\u70bc\uff1a%g \u5929" % (
        "\u662f" if screen_below_eye else "\u5426", float(interval_min or 0), float(days or 0)))
    lines.append("\u75bc\u75db\u8bc4\u5206\uff080-10\uff09\uff1a%g" % float(pain_score or 0))
    lines.append("")
    lines.append("[\u4e00] \u8d1f\u8377\u6784\u6210")
    lines.append("%-20s %10s" % ("\u9879\u76ee", "\u5f97\u5206"))
    lines.append("-" * 62)
    lines.append("%-20s %10.2f" % ("\u5c4f\u5e55\u65f6\u957f", min(float(screen_hours or 0), 12.0) * 1.0))
    lines.append("%-20s %10.2f" % ("\u624b\u673a\u4f4e\u5934\u65f6\u957f", min(float(phone_hours or 0), 8.0) * 1.5))
    lines.append("%-20s %10.2f" % ("\u5c4f\u5e55\u4f4e\u4e8e\u89c6\u7ebf", 3.0 if screen_below_eye else 0.0))
    lines.append("%-20s %10.2f" % ("\u8d77\u8eab\u95f4\u9694\u60e9\u7f5a", break_penalty(interval_min)))
    lines.append("%-20s %10.2f" % ("\u953b\u70bc\u5929\u6570\u7f3a\u53e3", gap))
    lines.append("-" * 62)
    lines.append("%-20s %10.2f  -> %s" % ("\u5408\u8ba1", score, level))
    lines.append("")
    lines.append("[\u4e8c] \u953b\u70bc\u65b9\u6848")
    lines.append("  \u63a8\u8350\u52a8\u4f5c\u6570\uff1a%d \u4e2a\uff08\u6bcf\u65e5\u603b\u91cf 10-15 \u5206\u949f\uff09" % cnt)
    lines.append("  \u63a8\u8350\u9891\u6b21\uff1a\u6bcf\u5468 5-7 \u5929\uff0c\u5f53\u524d\u7f3a\u53e3 %g \u5929" % gap)
    lines.append("  \u8d77\u8eab\u9891\u7387\uff1a\u6bcf 30-60 \u5206\u949f\u8d77\u8eab\u6d3b\u52a8 2-3 \u5206\u949f")
    lines.append("")
    lines.append("[\u4e09] \u75bc\u75db\u505c\u6b62\u539f\u5219")
    lines.append("  " + pain_rule(pain_score, pain_after))
    lines.append("")
    lines.append("[\u56db] \u4f18\u5148\u7ea7\u5efa\u8bae")
    if screen_below_eye:
        lines.append("  1. \u5148\u628a\u5c4f\u5e55\u62ac\u5230\u89c6\u7ebf\u4e0a\u4e09\u5206\u4e4b\u4e00\u5904\uff0c\u7b14\u8bb0\u672c\u7528\u652f\u67b6\u52a0\u5916\u63a5\u952e\u76d8")
    else:
        lines.append("  1. \u5c4f\u5e55\u9ad8\u5ea6\u5df2\u57fa\u672c\u5408\u9002\uff0c\u7ee7\u7eed\u4fdd\u6301")
    if float(phone_hours or 0) >= 3:
        lines.append("  2. \u624b\u673a\u62ac\u5230\u9762\u90e8\u9ad8\u5ea6\u770b\uff0c\u957f\u65f6\u95f4\u9605\u8bfb\u6539\u7528\u652f\u67b6")
    if break_penalty(interval_min) >= 2:
        lines.append("  3. \u8bbe\u5b9a\u65f6\u5668\uff0c\u628a\u8d77\u8eab\u95f4\u9694\u538b\u5230 60 \u5206\u949f\u4ee5\u5185")
    if gap > 0:
        lines.append("  4. \u672c\u5468\u628a\u953b\u70bc\u5929\u6570\u8865\u5230 5 \u5929\uff0c\u6bcf\u6b21 10-15 \u5206\u949f")
    lines.append("  5. \u8fde\u7eed\u8bb0\u5f55 2 \u5468\uff0c\u65e0\u6539\u5584\u6216\u52a0\u91cd\u8f6c\u5eb7\u590d\u79d1\u6216\u9aa8\u79d1\u8bc4\u4f30")
    lines.append("")
    lines.append("\u63d0\u793a\uff1a\u4e0d\u63a8\u8350\u5feb\u901f\u7529\u5934\u73af\u7ed5\u3001\u66b4\u529b\u6273\u9888\u3001\u81ea\u884c\u7275\u5f15\u548c\u957f\u671f\u4f69\u6234\u9888\u6258\u3002")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u8d1f\u8377\u81ea\u67e5\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u8bca\u7597\u610f\u89c1\u3002\u5242\u91cf\u4ee5\u6700\u65b0\u7248\u6307\u5357\u548c\u533b\u5e08\u5224\u65ad\u4e3a\u51c6\u3002")
    lines.append("=" * 62)

    summary = {
        "red_flag_hit": False,
        "flags": [],
        "exercise_blocked": False,
        "load_score": score,
        "load_level": level,
        "action_count": cnt,
        "exercise_gap_days": gap,
        "pain_rule": pain_rule(pain_score, pain_after),
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("\u95f4\u9694 30 \u5206\u949f\u60e9\u7f5a\u4e3a 0", break_penalty(30) == 0.0))
    r.append(("\u95f4\u9694 60 \u5206\u949f\u60e9\u7f5a\u4e3a 1", abs(break_penalty(60) - 1.0) < 1e-9))
    r.append(("\u95f4\u9694 90 \u5206\u949f\u60e9\u7f5a\u4e3a 2", abs(break_penalty(90) - 2.0) < 1e-9))
    r.append(("\u95f4\u9694 120 \u5206\u949f\u60e9\u7f5a\u4e3a 3", break_penalty(120) == 3.0))
    r.append(("\u953b\u70bc 5 \u5929\u7f3a\u53e3\u4e3a 0", exercise_gap(5) == 0.0))
    r.append(("\u953b\u70bc 2 \u5929\u7f3a\u53e3\u4e3a 3", abs(exercise_gap(2) - 3.0) < 1e-9))
    r.append(("\u953b\u70bc 7 \u5929\u7f3a\u53e3\u4e0d\u4e3a\u8d1f", exercise_gap(7) == 0.0))
    r.append(("\u8d1f\u8377 8+3+3+1+3=18 \u4e2d\u8d1f\u8377", abs(load_score(8, 2, True, 60, 2) - 18.0) < 1e-9))
    r.append(("\u4e2d\u8d1f\u8377\u5206\u7ea7", load_level(18.0) == "\u4e2d\u8d1f\u8377"))
    r.append(("\u4f4e\u8d1f\u8377\u5206\u7ea7", load_level(6.0) == "\u4f4e\u8d1f\u8377"))
    r.append(("\u9ad8\u8d1f\u8377\u5206\u7ea7", load_level(25.0) == "\u9ad8\u8d1f\u8377"))
    r.append(("\u52a8\u4f5c\u6570\u6620\u5c04", action_count("\u9ad8\u8d1f\u8377") == 5 and action_count("\u4f4e\u8d1f\u8377") == 3))

    _, s = build_report({
        "screen_hours": 9, "phone_hours": 4, "screen_below_eye": True,
        "break_interval_min": 120, "exercise_days_per_week": 1,
        "pain_score": 5, "pain_after": "none", "red_flags": [],
    })
    r.append(("\u65e0\u7ea2\u7ebf\u65f6\u7ed9\u51fa\u65b9\u6848", s["exercise_blocked"] is False))
    r.append(("\u9ad8\u8d1f\u8377\u6837\u4f8b\u5224\u5b9a", s["load_level"] == "\u9ad8\u8d1f\u8377"))

    _, s2 = build_report({"red_flags": ["hand_numbness", "bowel_bladder"]})
    r.append(("\u547d\u4e2d\u7ea2\u7ebf\u62e6\u622a\u953b\u70bc", s2["exercise_blocked"] is True))
    r.append(("\u6025\u8bca\u9879\u8bc6\u522b", s2["emergency"] == ["bowel_bladder"]))
    r.append(("\u7ea2\u7ebf\u65f6\u4e0d\u51fa\u8d1f\u8377\u5206", s2["load_score"] is None))

    _, s3 = build_report({"red_flags": ["xxx_unknown"]})
    r.append(("\u672a\u77e5\u7ea2\u7ebf\u9879\u5ffd\u7565", s3["red_flag_hit"] is False))

    r.append(("\u75bc\u75db\u52a0\u91cd\u89c4\u5219", "\u51cf\u534a" in pain_rule(3, "worse")))
    r.append(("\u9ebb\u6728\u89c4\u5219", "\u5c31\u533b" in pain_rule(3, "numbness")))
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
    parser = argparse.ArgumentParser(description="\u9888\u690e\u8d1f\u8377\u81ea\u67e5\u6253\u5206\u5de5\u5177")
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
