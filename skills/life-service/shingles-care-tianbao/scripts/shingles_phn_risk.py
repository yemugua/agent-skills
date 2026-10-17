# -*- coding: utf-8 -*-
"""\u5e26\u72b6\u75b1\u75b9\u5c31\u533b\u7a97\u53e3\u63d0\u793a\u4e0e\u540e\u9057\u795e\u7ecf\u75db\u98ce\u9669\u81ea\u67e5\u5de5\u5177\u3002

\u7528\u6cd5:
  python shingles_phn_risk.py --file case.json [--json]
  python shingles_phn_risk.py --selftest

\u672c\u5de5\u5177\u4e0d\u8f93\u51fa\u4efb\u4f55\u836f\u7269\u540d\u79f0\u4e0e\u5242\u91cf\u3002
"""
import argparse
import io
import json
import os
import sys

RED_FLAGS = [
    "eye_area",         # \u773c\u5468\u9f3b\u5c16\u989d\u5934
    "ear_with_palsy",   # \u8033\u90e8\u76ae\u75b9\u4f34\u9762\u762b
    "disseminated",     # \u64ad\u6563\u6027\u76ae\u75b9
    "immunocompromised",  # \u514d\u75ab\u4f4e\u4e0b
    "pregnancy",        # \u598a\u5a20
    "high_fever_neuro",  # \u9ad8\u70ed\u4f34\u795e\u7ecf\u75c7\u72b6
    "saddle_area",      # \u4f1a\u9634\u9ab6\u90e8\u4f34\u4e8c\u4fbf\u5f02\u5e38
    "secondary_infection",  # \u7ee7\u53d1\u611f\u67d3
    "severe_pain",      # \u75bc\u75db\u96be\u4ee5\u5fcd\u53d7
]
RED_FLAG_TEXT = {
    "eye_area": "\u76ae\u75b9\u4f4d\u4e8e\u773c\u5468\u3001\u9f3b\u5c16\u6216\u989d\u5934\u4e00\u4fa7\uff08\u773c\u652f\u53d7\u7d2f\u98ce\u9669\uff09",
    "ear_with_palsy": "\u8033\u90e8\u76ae\u75b9\u4f34\u9762\u762b\u3001\u8033\u9e23\u3001\u542c\u529b\u4e0b\u964d\u6216\u7729\u6655",
    "disseminated": "\u76ae\u75b9\u64ad\u6563\uff0c\u8d85\u51fa\u76f8\u90bb\u76ae\u8282\u6216\u5168\u8eab\u6563\u5728",
    "immunocompromised": "\u514d\u75ab\u4f4e\u4e0b\u72b6\u6001\uff08\u5316\u7597\u3001\u79fb\u690d\u3001\u957f\u671f\u6fc0\u7d20\u6216\u514d\u75ab\u6291\u5236\u5242\uff09",
    "pregnancy": "\u598a\u5a20\u671f",
    "high_fever_neuro": "\u76ae\u75b9\u4f34\u9ad8\u70ed\u3001\u5267\u70c8\u5934\u75db\u3001\u610f\u8bc6\u6539\u53d8\u6216\u9888\u9879\u5f3a\u76f4",
    "saddle_area": "\u4f1a\u9634\u6216\u9ab6\u90e8\u76ae\u75b9\u4f34\u6392\u5c3f\u6392\u4fbf\u56f0\u96be",
    "secondary_infection": "\u76ae\u75b9\u7ee7\u53d1\u611f\u67d3\uff1a\u7ea2\u80bf\u5316\u8113\u3001\u6e17\u6db2\u589e\u591a\u3001\u5468\u56f4\u53d1\u70eb",
    "severe_pain": "\u75bc\u75db\u5267\u70c8\u96be\u4ee5\u5fcd\u53d7\u6216\u76ae\u75b9\u5feb\u901f\u6269\u5927",
}
EMERGENCY_FLAGS = ("eye_area", "ear_with_palsy", "disseminated",
                   "high_fever_neuro", "saddle_area")
WINDOW_HOURS = 72.0


def age_points(age):
    a = float(age or 0)
    if a >= 70:
        return 3
    if a >= 60:
        return 2
    if a >= 50:
        return 1
    return 0


def pain_points(pain):
    p = float(pain or 0)
    if p >= 7:
        return 2
    if p >= 4:
        return 1
    return 0


def risk_score(age, pain, extensive, head_face, immuno, late):
    s = age_points(age) + pain_points(pain)
    if extensive:
        s += 1
    if head_face:
        s += 2
    if immuno:
        s += 2
    if late:
        s += 1
    return s


def risk_level(score):
    if score <= 2:
        return "\u4f4e\u98ce\u9669"
    if score <= 5:
        return "\u4e2d\u98ce\u9669"
    return "\u9ad8\u98ce\u9669"


def window_advice(hours):
    h = float(hours or 0)
    if h <= WINDOW_HOURS:
        return "\u4ecd\u5728\u5e38\u89c1\u7684 72 \u5c0f\u65f6\u6297\u75c5\u6bd2\u7a97\u53e3\u5185\uff0c\u5e94\u5c3d\u5feb\u5c31\u8bca\uff0c\u4e0d\u8981\u7b49\u5f85"
    return "\u5df2\u8d85\u8fc7\u5e38\u89c1\u7684 72 \u5c0f\u65f6\u7a97\u53e3\uff0c\u4ecd\u5e94\u5c3d\u5feb\u5c31\u8bca\uff1b\u662f\u5426\u7528\u836f\u7531\u533b\u751f\u7ed3\u5408\u65b0\u75b1\u3001\u75c5\u7a0b\u4e0e\u90e8\u4f4d\u5224\u65ad"


def build_report(data):
    age = data.get("age", 0)
    hours = data.get("hours_since_rash", 0)
    pain = data.get("pain_score", 0)
    extensive = bool(data.get("extensive_rash", False))
    head_face = bool(data.get("head_or_face", False))
    immuno = bool(data.get("immunocompromised", False))
    flags = [f for f in data.get("red_flags", []) if f in RED_FLAGS]

    lines = []
    lines.append("=" * 66)
    lines.append("\u5e26\u72b6\u75b1\u75b9\u5c31\u533b\u7a97\u53e3\u4e0e\u540e\u9057\u795e\u7ecf\u75db\u98ce\u9669\u81ea\u67e5")
    lines.append("=" * 66)
    lines.append("\u5e74\u9f84\uff1a%g \u5c81   \u8d77\u75b9\u81f3\u4eca\uff1a%g \u5c0f\u65f6   \u6025\u6027\u671f\u75bc\u75db\u8bc4\u5206\uff1a%g/10" % (
        float(age or 0), float(hours or 0), float(pain or 0)))
    lines.append("\u76ae\u75b9\u8303\u56f4\uff1a%s   \u5934\u9762\u90e8\u53d7\u7d2f\uff1a%s   \u514d\u75ab\u4f4e\u4e0b\uff1a%s" % (
        "\u5e7f\u6cdb\u6216\u878d\u5408" if extensive else "\u5c40\u9650",
        "\u662f" if head_face else "\u5426",
        "\u662f" if immuno else "\u5426"))
    lines.append("")

    if flags:
        lines.append("[\u7d27\u6025] \u547d\u4e2d\u5c31\u533b\u7ea2\u7ebf")
        lines.append("-" * 66)
        for f in flags:
            tag = "\u6025\u8bca" if f in EMERGENCY_FLAGS else "\u5c3d\u5feb\u5c31\u8bca"
            lines.append("  [%s] %s" % (tag, RED_FLAG_TEXT[f]))
        lines.append("")
        lines.append("\u5904\u7f6e\uff1a\u7acb\u5373\u5230\u76ae\u80a4\u79d1\u5c31\u8bca\uff1b\u773c\u5468\u9f3b\u5c16\u4e0e\u8033\u90e8\u4f34\u9762\u762b\u8005\u8d70\u6025\u8bca\u6216\u4e13\u79d1\u6025\u8bca\u901a\u9053\u3002")
        lines.append("\u4e0d\u8981\u81ea\u884c\u6311\u7834\u6c34\u75b1\u3001\u6d82\u62b9\u504f\u65b9\u6216\u81ea\u884c\u4f7f\u7528\u542b\u6fc0\u7d20\u836f\u818f\u3002")
        lines.append("")
        lines.append("\u514d\u8d23\uff1a\u672c\u8f93\u51fa\u4e3a\u5c31\u533b\u63d0\u793a\uff0c\u4e0d\u6784\u6210\u8bca\u65ad\u3002")
        lines.append("=" * 66)
        summary = {
            "red_flag_hit": True, "flags": flags,
            "emergency": [f for f in flags if f in EMERGENCY_FLAGS],
            "risk_score": None, "risk_level": None,
            "medication_dose_provided": False,
        }
        return "\n".join(lines), summary

    late = float(hours or 0) > WINDOW_HOURS
    score = risk_score(age, pain, extensive, head_face, immuno, late)
    level = risk_level(score)

    lines.append("[\u4e00] \u6297\u75c5\u6bd2\u5c31\u533b\u7a97\u53e3")
    lines.append("  " + window_advice(hours))
    lines.append("  \u8bb0\u5f55\u8981\u70b9\uff1a\u5206\u522b\u8bb0\u6e05\u75bc\u75db\u8d77\u59cb\u65e5\u4e0e\u76ae\u75b9\u51fa\u73b0\u65e5\uff0c\u5c31\u8bca\u65f6\u76f4\u63a5\u544a\u77e5\u533b\u751f")
    lines.append("")
    lines.append("[\u4e8c] \u540e\u9057\u795e\u7ecf\u75db\u98ce\u9669\u81ea\u67e5")
    lines.append("  \u5e74\u9f84\u5206\uff1a%d\uff08%g \u5c81\uff09" % (age_points(age), float(age or 0)))
    lines.append("  \u75bc\u75db\u5206\uff1a%d\uff08%g \u5206\uff09" % (pain_points(pain), float(pain or 0)))
    lines.append("  \u76ae\u75b9\u5e7f\u6cdb\uff1a%d   \u5934\u9762\u90e8\uff1a%d   \u514d\u75ab\u4f4e\u4e0b\uff1a%d   \u8d85\u8fc7\u7a97\u53e3\u5c31\u533b\uff1a%d" % (
        1 if extensive else 0, 2 if head_face else 0,
        2 if immuno else 0, 1 if late else 0))
    lines.append("  \u5408\u8ba1\uff1a%d \u5206 -> %s" % (score, level))
    lines.append("")
    lines.append("[\u4e09] \u968f\u8bbf\u5efa\u8bae")
    if level == "\u9ad8\u98ce\u9669":
        lines.append("  \u75bc\u75db\u7ba1\u7406\u5e94\u66f4\u79ef\u6781\uff0c\u5efa\u8bae\u4e0e\u533b\u751f\u6c9f\u901a\u662f\u5426\u9700\u8981\u75bc\u75db\u79d1\u8bc4\u4f30")
    elif level == "\u4e2d\u98ce\u9669":
        lines.append("  \u6309\u533b\u5631\u5b8c\u6210\u7597\u7a0b\uff0c\u75bc\u75db\u63a7\u5236\u4e0d\u4f73\u65f6\u4e3b\u52a8\u590d\u8bca")
    else:
        lines.append("  \u89c4\u8303\u62a4\u7406\u4e0e\u968f\u8bbf\uff0c\u76ae\u75b9\u6108\u5408\u540e\u4ecd\u75db\u9700\u590d\u8bca")
    lines.append("  \u76ae\u75b9\u6108\u5408\u540e\u75bc\u75db\u6301\u7eed\u8d85\u8fc7 1 \u4e2a\u6708\uff1a\u590d\u8bca\u8bc4\u4f30")
    lines.append("  \u75bc\u75db\u6301\u7eed\u8d85\u8fc7 3 \u4e2a\u6708\uff1a\u5c5e\u4e8e\u540e\u9057\u795e\u7ecf\u75db\u8303\u7574\uff0c\u9700\u7cfb\u7edf\u8bc4\u4f30")
    lines.append("")
    lines.append("[\u56db] \u76ae\u75b9\u62a4\u7406")
    for c in ["\u6e05\u6c34\u8f7b\u67d4\u6e05\u6d17\u5e76\u5438\u5e72\uff0c\u4e0d\u7528\u529b\u6413\u64e6", "\u7528\u5e72\u51c0\u6577\u6599\u677e\u677e\u8986\u76d6\uff0c\u51cf\u5c11\u6469\u64e6\u4e0e\u6269\u6563",
              "\u526a\u77ed\u6307\u7532\u9632\u6293\u7834\uff0c\u591c\u95f4\u53ef\u6234\u68c9\u624b\u5957", "\u7a7f\u5bbd\u677e\u67d4\u8f6f\u900f\u6c14\u8863\u7269",
              "\u4e0d\u81ea\u884c\u6311\u7834\u6c34\u75b1\uff0c\u4e0d\u6d82\u7259\u818f\u9999\u7070\u7b49\u504f\u65b9\uff0c\u4e0d\u81ea\u884c\u7528\u542b\u6fc0\u7d20\u836f\u818f"]:
        lines.append("  + %s" % c)
    lines.append("")
    lines.append("[\u4e94] \u4f20\u67d3\u7ba1\u7406")
    lines.append("  \u6c34\u75b1\u5b8c\u5168\u7ed3\u75c2\u524d\u907f\u514d\u63a5\u89e6\u672a\u60a3\u8fc7\u6c34\u75d8\u8005\u3001\u5b55\u5987\u3001\u65b0\u751f\u513f\u4e0e\u514d\u75ab\u4f4e\u4e0b\u8005")
    lines.append("  \u4e0d\u5171\u7528\u6bdb\u5dfe\u8863\u7269\uff0c\u52e4\u6d17\u624b")
    lines.append("")
    lines.append("\u63d0\u793a\uff1a\u5206\u7ea7\u53ea\u63d0\u793a\u968f\u8bbf\u5f3a\u5ea6\uff0c\u4e0d\u80fd\u66ff\u4ee3\u533b\u751f\u5224\u65ad\uff0c\u4e5f\u4e0d\u9884\u6d4b\u4e2a\u4eba\u7ed3\u5c40\u3002")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u98ce\u9669\u81ea\u67e5\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u8bca\u7597\u610f\u89c1\uff0c\u4e0d\u63d0\u4f9b\u836f\u7269\u5242\u91cf\u3002")
    lines.append("=" * 66)

    summary = {
        "red_flag_hit": False, "flags": [], "emergency": [],
        "risk_score": score, "risk_level": level,
        "window_hours": WINDOW_HOURS, "in_window": not late,
        "window_advice": window_advice(hours),
        "medication_dose_provided": False,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("45 \u5c81\u5e74\u9f84\u5206 0", age_points(45) == 0))
    r.append(("55 \u5c81\u5e74\u9f84\u5206 1", age_points(55) == 1))
    r.append(("65 \u5c81\u5e74\u9f84\u5206 2", age_points(65) == 2))
    r.append(("75 \u5c81\u5e74\u9f84\u5206 3", age_points(75) == 3))
    r.append(("\u75bc\u75db 8 \u5206\u8ba1 2", pain_points(8) == 2))
    r.append(("\u75bc\u75db 5 \u5206\u8ba1 1", pain_points(5) == 1))
    r.append(("\u75bc\u75db 2 \u5206\u8ba1 0", pain_points(2) == 0))
    r.append(("\u98ce\u9669\u5206\u5408\u8ba1", risk_score(75, 8, True, True, True, True) == 11))
    r.append(("2 \u5206\u4e3a\u4f4e\u98ce\u9669", risk_level(2) == "\u4f4e\u98ce\u9669"))
    r.append(("3 \u5206\u4e3a\u4e2d\u98ce\u9669", risk_level(3) == "\u4e2d\u98ce\u9669"))
    r.append(("6 \u5206\u4e3a\u9ad8\u98ce\u9669", risk_level(6) == "\u9ad8\u98ce\u9669"))
    r.append(("72 \u5c0f\u65f6\u5185\u63d0\u793a", "\u5c3d\u5feb\u5c31\u8bca" in window_advice(48)))
    r.append(("\u8d85\u7a97\u53e3\u63d0\u793a", "\u5df2\u8d85\u8fc7" in window_advice(96)))

    _, s = build_report({"age": 68, "hours_since_rash": 30, "pain_score": 8,
                         "extensive_rash": True, "head_or_face": False,
                         "immunocompromised": False, "red_flags": []})
    r.append(("\u6837\u4f8b\u98ce\u9669\u5206 5", s["risk_score"] == 5))
    r.append(("\u6837\u4f8b\u4e3a\u4e2d\u98ce\u9669", s["risk_level"] == "\u4e2d\u98ce\u9669"))
    r.append(("\u6837\u4f8b\u5728\u7a97\u53e3\u5185", s["in_window"] is True))
    r.append(("\u4e0d\u63d0\u4f9b\u836f\u7269\u5242\u91cf", s["medication_dose_provided"] is False))

    _, s2 = build_report({"red_flags": ["eye_area"]})
    r.append(("\u773c\u90e8\u7ea2\u7ebf\u62e6\u622a", s2["red_flag_hit"] is True))
    r.append(("\u773c\u90e8\u5c5e\u6025\u8bca\u9879", s2["emergency"] == ["eye_area"]))
    r.append(("\u7ea2\u7ebf\u65f6\u4e0d\u51fa\u98ce\u9669\u5206", s2["risk_score"] is None))

    _, s3 = build_report({"red_flags": ["pregnancy"]})
    r.append(("\u598a\u5a20\u975e\u6025\u8bca\u9879\u4f46\u62e6\u622a", s3["emergency"] == [] and s3["red_flag_hit"] is True))

    _, s4 = build_report({"red_flags": ["no_such_flag"]})
    r.append(("\u672a\u77e5\u7ea2\u7ebf\u9879\u5ffd\u7565", s4["red_flag_hit"] is False))
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
    parser = argparse.ArgumentParser(description="\u5e26\u72b6\u75b1\u75b9\u5c31\u533b\u7a97\u53e3\u4e0e\u540e\u9057\u795e\u7ecf\u75db\u98ce\u9669\u81ea\u67e5\u5de5\u5177")
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
