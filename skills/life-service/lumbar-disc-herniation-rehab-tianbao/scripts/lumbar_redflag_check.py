# -*- coding: utf-8 -*-
"""\u8170\u7a81\u7ea2\u65d7\u75c7\u7b5b\u67e5\u4e0e\u5206\u671f\u5eb7\u590d\u8bb8\u53ef\u5224\u5b9a\u5de5\u5177\u3002

\u7528\u6cd5:
  python lumbar_redflag_check.py --file case.json [--json]
  python lumbar_redflag_check.py --selftest

\u547d\u4e2d\u7ea2\u65d7\u75c7\u65f6\u53ea\u8f93\u51fa\u5c31\u533b\u63d0\u793a\uff0c\u4e0d\u8f93\u51fa\u4efb\u4f55\u953b\u70bc\u52a8\u4f5c\u3002
"""
import argparse
import io
import json
import os
import sys

RED_FLAGS = [
    "saddle_numbness",   # \u978d\u533a\u9ebb\u6728
    "bladder_bowel",     # \u5927\u5c0f\u4fbf\u969c\u788d\u6216\u5c3f\u6f74\u7559
    "bilateral_weakness",  # \u53cc\u817f\u8fdb\u884c\u6027\u65e0\u529b
    "fever_back_pain",   # \u8170\u75db\u4f34\u53d1\u70ed
    "cancer_history",    # \u80bf\u7624\u53f2\u65b0\u53d1\u8170\u75db
    "trauma",            # \u5916\u4f24\u540e\u6025\u6027\u8170\u75db
    "night_pain_weight_loss",  # \u591c\u95f4\u75db\u4f34\u4f53\u91cd\u4e0b\u964d
    "foot_drop",         # \u8db3\u4e0b\u5782
]
RED_FLAG_TEXT = {
    "saddle_numbness": "\u4f1a\u9634\u533a\u6216\u5927\u817f\u5185\u4fa7\u9ebb\u6728\uff08\u978d\u533a\u9ebb\u6728\uff09",
    "bladder_bowel": "\u5c0f\u4fbf\u6392\u4e0d\u51fa\u6216\u5931\u7981\u3001\u5927\u4fbf\u969c\u788d",
    "bilateral_weakness": "\u53cc\u817f\u8fdb\u884c\u6027\u65e0\u529b\u3001\u8d70\u8def\u62d6\u6b65",
    "fever_back_pain": "\u8170\u75db\u4f34\u53d1\u70ed\u5bd2\u6218\uff0c\u9700\u6392\u9664\u810a\u67f1\u611f\u67d3",
    "cancer_history": "\u6076\u6027\u80bf\u7624\u75c5\u53f2\u8005\u65b0\u53d1\u6301\u7eed\u8170\u75db",
    "trauma": "\u5916\u4f24\u540e\u6025\u6027\u8170\u75db\uff0c\u9700\u6392\u9664\u9aa8\u6298",
    "night_pain_weight_loss": "\u591c\u95f4\u75db\u4e3a\u4e3b\u4f34\u4f53\u91cd\u4e0b\u964d",
    "foot_drop": "\u8db3\u4e0b\u5782\u6216\u8e1d\u80cc\u4f38\u65e0\u529b",
}
CAUDA_FLAGS = ("saddle_numbness", "bladder_bowel", "bilateral_weakness")
EMERGENCY_FLAGS = CAUDA_FLAGS

ALLOWED = {
    "\u6025\u6027\u671f": ["\u4ef0\u5367\u5c48\u819d\u62b1\u817f\uff08\u5355\u4fa7\u4ea4\u66ff\uff0c\u7f13\u6162\uff09", "\u8179\u5f0f\u547c\u5438\u52a0\u8179\u90e8\u6536\u7d27", "\u4fef\u5367\u8098\u6491\uff08\u65e0\u75db\u8303\u56f4\u5185\uff0c10-30 \u79d2\uff09"],
    "\u4e9a\u6025\u6027\u671f": ["\u4ef0\u5367\u5c48\u819d\u62b1\u817f", "\u4fef\u5367\u8098\u6491", "\u4fef\u5367\u4f38\u5c55\uff08\u75bc\u75db\u5411\u5fc3\u5316\u65f6\u53ef\u505a\uff09",
             "\u6b7b\u866b\u5f0f", "\u81c0\u6865", "\u8179\u5f0f\u547c\u5438\u6838\u5fc3\u6fc0\u6d3b"],
    "\u7f13\u89e3\u671f": ["\u6b7b\u866b\u5f0f", "\u9e1f\u72d7\u5f0f", "\u81c0\u6865", "\u4fa7\u5e73\u677f\uff08\u8dea\u59ff\u8d77\u6b65\uff09",
            "\u4fef\u5367\u4f38\u5c55", "\u6b65\u884c\u4e0e\u6709\u6c27\uff08\u6bcf\u65e5 30-60 \u5206\u949f\uff09"],
}
FORBIDDEN = {
    "\u6025\u6027\u671f": ["\u5c0f\u71d5\u98de", "\u4ef0\u5367\u8d77\u5750\u4e0e\u5377\u8179", "\u7ad9\u7acb\u4f53\u524d\u5c48\u6478\u5730", "\u53cc\u817f\u540c\u65f6\u76f4\u817f\u62ac\u9ad8", "\u8d1f\u91cd\u6df1\u8e72\u4e0e\u786c\u62c9"],
    "\u4e9a\u6025\u6027\u671f": ["\u4ef0\u5367\u8d77\u5750\u4e0e\u5377\u8179", "\u7ad9\u7acb\u4f53\u524d\u5c48\u6478\u5730", "\u8d1f\u91cd\u6df1\u8e72\u4e0e\u786c\u62c9"],
    "\u7f13\u89e3\u671f": ["\u6025\u6027\u671f\u5f0f\u731b\u7ec3\u5c0f\u71d5\u98de\uff08\u9700\u533b\u5e08\u786e\u8ba4\uff09", "\u65e0\u51c6\u5907\u7684\u76f4\u63a5\u8d1f\u91cd\u6df1\u8e72\u4e0e\u786c\u62c9"],
}
WALK_TARGET = {"\u6025\u6027\u671f": "\u6bcf\u6b21 5-10 \u5206\u949f\uff0c\u6bcf\u65e5 3-5 \u6b21",
               "\u4e9a\u6025\u6027\u671f": "\u6bcf\u6b21 10-20 \u5206\u949f\uff0c\u6bcf\u65e5 2-3 \u6b21",
               "\u7f13\u89e3\u671f": "\u6bcf\u65e5\u7d2f\u8ba1 30-60 \u5206\u949f"}
SIT_LIMIT = {"\u6025\u6027\u671f": "\u5355\u6b21\u4e0d\u8d85\u8fc7 15-20 \u5206\u949f",
             "\u4e9a\u6025\u6027\u671f": "\u5355\u6b21\u4e0d\u8d85\u8fc7 30 \u5206\u949f",
             "\u7f13\u89e3\u671f": "\u5355\u6b21\u4e0d\u8d85\u8fc7 45-60 \u5206\u949f\uff0c\u5b9a\u65f6\u8d77\u8eab"}


def stage_of(days, pain_score, radiating):
    """\u5206\u671f\u5224\u5b9a\uff1a\u5929\u6570\u7ed3\u5408\u75bc\u75db\u8bc4\u5206\u3002"""
    d = float(days or 0)
    p = float(pain_score or 0)
    if d <= 14 and p >= 7:
        return "\u6025\u6027\u671f"
    if d <= 14 and p >= 4:
        return "\u4e9a\u6025\u6027\u671f"
    return "\u4e9a\u6025\u6027\u671f" if p >= 4 else "\u7f13\u89e3\u671f"


def bed_rest_advice(stage):
    if stage == "\u6025\u6027\u671f":
        return "\u53ef\u77ed\u671f\u4f11\u606f\uff0c\u7edd\u5bf9\u5367\u5e8a\u4e00\u822c\u4e0d\u8d85\u8fc7 48 \u5c0f\u65f6\uff0c\u5c3d\u65e9\u6062\u590d\u53ef\u8010\u53d7\u6d3b\u52a8"
    return "\u4e0d\u9700\u5367\u5e8a\uff0c\u4e45\u5367\u5ef6\u7f13\u6062\u590d"


def build_report(data):
    days = data.get("pain_days", 0)
    pain_score = data.get("pain_score", 0)
    radiating = bool(data.get("radiating_to_leg", False))
    flags = [f for f in data.get("red_flags", []) if f in RED_FLAGS]
    walk_now = data.get("current_walk_minutes_per_day", 0)

    lines = []
    lines.append("=" * 62)
    lines.append("\u8170\u7a81\u7ea2\u65d7\u75c7\u7b5b\u67e5\u4e0e\u5206\u671f\u5eb7\u590d\u8bb8\u53ef")
    lines.append("=" * 62)
    lines.append("\u75bc\u75db\u5929\u6570\uff1a%g \u5929   \u75bc\u75db\u8bc4\u5206\uff1a%g/10   \u653e\u5c04\u5230\u817f\uff1a%s" % (
        float(days or 0), float(pain_score or 0), "\u662f" if radiating else "\u5426"))
    lines.append("\u5f53\u524d\u6bcf\u65e5\u6b65\u884c\uff1a%g \u5206\u949f" % float(walk_now or 0))

    if flags:
        lines.append("")
        lines.append("[\u7d27\u6025] \u547d\u4e2d\u7ea2\u65d7\u75c7\uff0c\u4e0d\u8f93\u51fa\u4efb\u4f55\u953b\u70bc\u52a8\u4f5c")
        lines.append("-" * 62)
        for f in flags:
            tag = "\u7591\u4f3c\u9a6c\u5c3e\u7efc\u5408\u5f81\uff0c\u6025\u8bca" if f in CAUDA_FLAGS else "\u5c3d\u5feb\u5c31\u8bca"
            lines.append("  [%s] %s" % (tag, RED_FLAG_TEXT[f]))
        lines.append("")
        lines.append("\u5904\u7f6e\uff1a\u7acb\u5373\u505c\u6b62\u953b\u70bc\u3001\u6309\u6469\u3001\u7275\u5f15\u548c\u81ea\u884c\u7528\u836f\u3002")
        lines.append("\u51fa\u73b0\u978d\u533a\u9ebb\u6728\u6216\u4e8c\u4fbf\u5f02\u5e38\u8005\u76f4\u63a5\u53bb\u6025\u8bca\uff0c\u4e0d\u8981\u7b49\u7b2c\u4e8c\u5929\u95e8\u8bca\u3002")
        lines.append("")
        lines.append("\u514d\u8d23\uff1a\u672c\u8f93\u51fa\u4e3a\u5c31\u533b\u63d0\u793a\uff0c\u4e0d\u6784\u6210\u8bca\u65ad\u3002")
        lines.append("=" * 62)
        summary = {
            "red_flag_hit": True,
            "flags": flags,
            "cauda_suspected": any(f in CAUDA_FLAGS for f in flags),
            "emergency": [f for f in flags if f in EMERGENCY_FLAGS],
            "exercise_blocked": True,
            "stage": None,
        }
        return "\n".join(lines), summary

    stage = stage_of(days, pain_score, radiating)
    lines.append("")
    lines.append("[\u4e00] \u5206\u671f\u5224\u5b9a\uff1a%s" % stage)
    lines.append("  " + bed_rest_advice(stage))
    lines.append("")
    lines.append("[\u4e8c] \u53ef\u505a\u52a8\u4f5c")
    for a in ALLOWED[stage]:
        lines.append("  + %s" % a)
    lines.append("")
    lines.append("[\u4e09] \u7981\u5fcc\u52a8\u4f5c")
    for a in FORBIDDEN[stage]:
        lines.append("  - %s" % a)
    lines.append("")
    lines.append("[\u56db] \u6d3b\u52a8\u91cf")
    lines.append("  \u6b65\u884c\u76ee\u6807\uff1a%s" % WALK_TARGET[stage])
    lines.append("  \u4e45\u5750\u4e0a\u9650\uff1a%s" % SIT_LIMIT[stage])
    gap = float(walk_now or 0)
    if stage == "\u6025\u6027\u671f" and gap < 15:
        lines.append("  \u5f53\u524d\u6b65\u884c\u504f\u5c11\uff0c\u53ef\u4ece\u6bcf\u6b21 5 \u5206\u949f\u3001\u6bcf\u65e5 3 \u6b21\u8d77\u6b65")
    lines.append("")
    lines.append("[\u4e94] \u505c\u6b62\u539f\u5219")
    lines.append("  \u75bc\u75db\u4ece\u817f\u5f80\u8170\u96c6\u4e2d\uff08\u5411\u5fc3\u5316\uff09\u53ef\u7ee7\u7eed\uff1b\u4ece\u8170\u5f80\u817f\u6269\u6563\uff08\u5916\u5468\u5316\uff09\u7acb\u5373\u505c\u6b62")
    lines.append("  \u51fa\u73b0\u65b0\u53d1\u9ebb\u6728\u6216\u65e0\u529b\u3001\u4e8c\u4fbf\u5f02\u5e38\uff0c\u505c\u6b62\u8bad\u7ec3\u5e76\u5c3d\u5feb\u5c31\u533b")
    lines.append("  2 \u5468\u590d\u8bc4\u4e00\u6b21\uff1b4-6 \u5468\u65e0\u6539\u5584\u6216\u52a0\u91cd\u8f6c\u4e13\u79d1")
    lines.append("")
    lines.append("\u63d0\u793a\uff1a\u4e0d\u505a\u66b4\u529b\u63a8\u62ff\u3001\u6273\u8170\u3001\u81ea\u884c\u7275\u5f15\uff1b\u4e0d\u957f\u671f\u7edd\u5bf9\u5367\u5e8a\u3002")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u5206\u671f\u53e3\u5f84\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u8bca\u7597\u610f\u89c1\u3002\u5242\u91cf\u4ee5\u6700\u65b0\u7248\u6307\u5357\u548c\u533b\u5e08\u5224\u65ad\u4e3a\u51c6\u3002")
    lines.append("=" * 62)

    summary = {
        "red_flag_hit": False,
        "flags": [],
        "cauda_suspected": False,
        "emergency": [],
        "exercise_blocked": False,
        "stage": stage,
        "allowed": ALLOWED[stage],
        "forbidden": FORBIDDEN[stage],
        "walk_target": WALK_TARGET[stage],
        "sit_limit": SIT_LIMIT[stage],
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("0 \u5929 8 \u5206\u4e3a\u6025\u6027\u671f", stage_of(0, 8, True) == "\u6025\u6027\u671f"))
    r.append(("10 \u5929 5 \u5206\u4e3a\u4e9a\u6025\u6027\u671f", stage_of(10, 5, True) == "\u4e9a\u6025\u6027\u671f"))
    r.append(("30 \u5929 3 \u5206\u4e3a\u7f13\u89e3\u671f", stage_of(30, 3, False) == "\u7f13\u89e3\u671f"))
    r.append(("60 \u5929 6 \u5206\u4e3a\u4e9a\u6025\u6027\u671f", stage_of(60, 6, True) == "\u4e9a\u6025\u6027\u671f"))
    r.append(("\u6025\u6027\u671f\u7981\u5c0f\u71d5\u98de", "\u5c0f\u71d5\u98de" in FORBIDDEN["\u6025\u6027\u671f"]))
    r.append(("\u6025\u6027\u671f\u4e0d\u542b\u6b7b\u866b\u5f0f", "\u6b7b\u866b\u5f0f" not in ALLOWED["\u6025\u6027\u671f"]))
    r.append(("\u7f13\u89e3\u671f\u542b\u9e1f\u72d7\u5f0f", "\u9e1f\u72d7\u5f0f" in ALLOWED["\u7f13\u89e3\u671f"]))
    r.append(("\u5367\u5e8a\u53e3\u5f84", "48" in bed_rest_advice("\u6025\u6027\u671f")))

    _, s = build_report({"pain_days": 3, "pain_score": 8, "radiating_to_leg": True,
                         "red_flags": [], "current_walk_minutes_per_day": 5})
    r.append(("\u6025\u6027\u671f\u6837\u4f8b", s["stage"] == "\u6025\u6027\u671f"))
    r.append(("\u6b65\u884c\u76ee\u6807\u542b 5-10 \u5206\u949f", "5-10" in s["walk_target"]))

    _, s2 = build_report({"red_flags": ["saddle_numbness", "bladder_bowel"]})
    r.append(("\u9a6c\u5c3e\u7591\u4f3c\u62e6\u622a", s2["cauda_suspected"] is True))
    r.append(("\u9a6c\u5c3e\u65f6\u4e0d\u51fa\u52a8\u4f5c", s2["exercise_blocked"] is True))
    r.append(("\u9a6c\u5c3e\u65f6\u5206\u671f\u4e3a\u7a7a", s2["stage"] is None))

    _, s3 = build_report({"red_flags": ["fever_back_pain"]})
    r.append(("\u53d1\u70ed\u7ea2\u65d7\u975e\u9a6c\u5c3e", s3["cauda_suspected"] is False))
    r.append(("\u53d1\u70ed\u7ea2\u65d7\u4ecd\u62e6\u622a", s3["exercise_blocked"] is True))

    _, s4 = build_report({"red_flags": ["not_a_flag"]})
    r.append(("\u672a\u77e5\u7ea2\u65d7\u9879\u5ffd\u7565", s4["red_flag_hit"] is False))
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
    parser = argparse.ArgumentParser(description="\u8170\u7a81\u7ea2\u65d7\u75c7\u7b5b\u67e5\u4e0e\u5206\u671f\u5eb7\u590d\u8bb8\u53ef\u5de5\u5177")
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
