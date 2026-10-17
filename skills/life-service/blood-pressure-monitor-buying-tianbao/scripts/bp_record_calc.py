# -*- coding: utf-8 -*-
"""\u5bb6\u5ead\u8840\u538b\u5468\u8bb0\u5f55\u5747\u503c\u6838\u7b97\u4e0e\u8896\u5e26\u5c3a\u5bf8\u63d0\u793a\u5de5\u5177\u3002

\u7528\u6cd5:
  python bp_record_calc.py --file week.json [--json]
  python bp_record_calc.py --selftest

\u547d\u4e2d\u8840\u538b\u6781\u503c\u7ea2\u7ebf\u65f6\u53ea\u8f93\u51fa\u5c31\u533b\u63d0\u793a\u3002\u672c\u5de5\u5177\u4e0d\u8f93\u51fa\u4efb\u4f55\u836f\u7269\u5242\u91cf\u3002
"""
import argparse
import io
import json
import os
import sys

CRISIS_SBP = 180
CRISIS_DBP = 120
LOW_SBP = 90
LOW_DBP = 60
MIN_VALID = 12
HOME_NORMAL_SBP = 135
HOME_NORMAL_DBP = 85


def mean_of(values):
    if not values:
        return None
    return round(sum(values) / float(len(values)), 1)


def bp_grade(sbp, dbp):
    """\u5bb6\u5ead\u8840\u538b\u5e38\u7528\u53c2\u8003\u53e3\u5f84\u7684\u5206\u7ea7\u63d0\u793a\u3002"""
    if sbp is None or dbp is None:
        return "\u6570\u636e\u4e0d\u8db3"
    if sbp >= CRISIS_SBP or dbp >= CRISIS_DBP:
        return "\u8fbe\u5230\u9700\u7d27\u6025\u5c31\u533b\u7684\u6781\u503c\u8303\u56f4"
    if sbp < LOW_SBP and dbp < LOW_DBP:
        return "\u4f4e\u4e8e\u5e38\u89c1\u4f4e\u503c\u53e3\u5f84\uff0c\u4f34\u75c7\u72b6\u9700\u5c31\u533b"
    if sbp >= HOME_NORMAL_SBP or dbp >= HOME_NORMAL_DBP:
        return "\u9ad8\u4e8e\u5bb6\u5ead\u8840\u538b\u5e38\u7528\u53c2\u8003\u503c\uff08135/85\uff09"
    return "\u5728\u5bb6\u5ead\u8840\u538b\u5e38\u7528\u53c2\u8003\u503c\uff08135/85\uff09\u4ee5\u4e0b"


def cuff_advice(arm_cm):
    """\u6309\u4e0a\u81c2\u5468\u957f\u7ed9\u51fa\u8896\u5e26\u5c3a\u5bf8\u53e3\u5f84\u3002"""
    a = float(arm_cm or 0)
    if a <= 0:
        return "\u672a\u63d0\u4f9b\u81c2\u56f4\uff0c\u65e0\u6cd5\u5224\u65ad\u8896\u5e26\u5c3a\u5bf8"
    width = round(a * 0.4, 1)
    length = round(a * 0.8, 1)
    if a < 22:
        size = "\u504f\u5c0f\u81c2\u56f4\uff0c\u5e94\u9009\u5c0f\u53f7\u8896\u5e26"
    elif a <= 32:
        size = "\u6807\u51c6\u6210\u4eba\u8896\u5e26\u901a\u5e38\u9002\u914d\u8be5\u81c2\u56f4"
    else:
        size = "\u81c2\u56f4\u8f83\u5927\uff0c\u5e94\u9009\u5927\u53f7\u8896\u5e26\uff0c\u7528\u6807\u51c6\u8896\u5e26\u4f1a\u8bfb\u6570\u504f\u9ad8"
    return "\u81c2\u56f4 %g \u5398\u7c73\uff1a\u6c14\u56ca\u5bbd\u7ea6 %g \u5398\u7c73\u3001\u957f\u7ea6 %g \u5398\u7c73\uff1b%s" % (a, width, length, size)


def build_report(data):
    readings = data.get("readings", [])
    arm_cm = data.get("arm_circumference_cm", 0)
    irregular = bool(data.get("irregular_pulse_reported", False))

    sbp_all, dbp_all = [], []
    sbp_am, dbp_am = [], []
    sbp_pm, dbp_pm = [], []
    pulse_all = []
    crisis = []
    for r in readings:
        s = float(r.get("systolic", 0) or 0)
        d = float(r.get("diastolic", 0) or 0)
        p = float(r.get("pulse", 0) or 0)
        slot = r.get("slot", "")
        if s <= 0 or d <= 0:
            continue
        sbp_all.append(s)
        dbp_all.append(d)
        if p > 0:
            pulse_all.append(p)
        if slot == "morning":
            sbp_am.append(s)
            dbp_am.append(d)
        elif slot == "evening":
            sbp_pm.append(s)
            dbp_pm.append(d)
        if s >= CRISIS_SBP or d >= CRISIS_DBP:
            crisis.append((r.get("date", "?"), slot, s, d))

    lines = []
    lines.append("=" * 66)
    lines.append("\u5bb6\u5ead\u8840\u538b\u5468\u8bb0\u5f55\u6838\u7b97")
    lines.append("=" * 66)
    lines.append("\u6709\u6548\u6d4b\u91cf\u6b21\u6570\uff1a%d\uff08\u5efa\u8bae\u4e0d\u5c11\u4e8e %d \u6b21\uff09" % (len(sbp_all), MIN_VALID))
    lines.append("")

    if crisis:
        lines.append("[\u7d27\u6025] \u68c0\u51fa\u8fbe\u5230\u6781\u503c\u8303\u56f4\u7684\u6d4b\u91cf")
        lines.append("-" * 66)
        for date, slot, s, d in crisis:
            lines.append("  %s %s\uff1a%g/%g mmHg" % (date, slot, s, d))
        lines.append("")
        lines.append("\u5904\u7f6e\uff1a\u82e5\u540c\u65f6\u4f34\u6709\u80f8\u75db\u80f8\u95f7\u3001\u547c\u5438\u56f0\u96be\u3001\u89c6\u7269\u6a21\u7cca\u3001\u4e00\u4fa7\u80a2\u4f53\u65e0\u529b\u3001")
        lines.append("\u8a00\u8bed\u4e0d\u6e05\u3001\u5267\u70c8\u5934\u75db\u6216\u610f\u8bc6\u6539\u53d8\uff0c\u7acb\u5373\u53bb\u6025\u8bca\uff0c\u4e0d\u8981\u5148\u5728\u5bb6\u590d\u6d4b\u3002")
        lines.append("\u53cd\u590d\u8fbe\u5230 180/120 \u4ee5\u4e0a\u5373\u4f7f\u6682\u65e0\u4e0d\u9002\uff0c\u4e5f\u5e94\u5c3d\u5feb\u5c31\u533b\u3002")
        lines.append("")
        lines.append("\u514d\u8d23\uff1a\u672c\u8f93\u51fa\u4e3a\u5c31\u533b\u63d0\u793a\uff0c\u4e0d\u6784\u6210\u8bca\u65ad\u3002")
        lines.append("=" * 66)
        summary = {
            "crisis_hit": True, "crisis_readings": [
                {"date": d0, "slot": s0, "systolic": s0v, "diastolic": d0v}
                for d0, s0, s0v, d0v in crisis],
            "avg_systolic": None, "avg_diastolic": None,
            "medication_dose_provided": False,
        }
        return "\n".join(lines), summary

    ms, md = mean_of(sbp_all), mean_of(dbp_all)
    lines.append("[\u4e00] \u5747\u503c")
    if ms is None:
        lines.append("  \u65e0\u6709\u6548\u6d4b\u91cf\u6570\u636e\uff0c\u8bf7\u68c0\u67e5\u8f93\u5165")
        lines.append("=" * 66)
        return "\n".join(lines), {"crisis_hit": False, "avg_systolic": None,
                                  "avg_diastolic": None, "valid_count": 0,
                                  "medication_dose_provided": False}

    lines.append("  \u5168\u90e8\u5747\u503c\uff1a%g/%g mmHg   \u8109\u640f\u5747\u503c\uff1a%s" % (
        ms, md, mean_of(pulse_all) if pulse_all else "\u672a\u8bb0\u5f55"))
    if sbp_am:
        lines.append("  \u6e05\u6668\u5747\u503c\uff1a%g/%g mmHg\uff08%d \u6b21\uff09" % (mean_of(sbp_am), mean_of(dbp_am), len(sbp_am)))
    else:
        lines.append("  \u6e05\u6668\u5747\u503c\uff1a\u65e0\u8bb0\u5f55")
    if sbp_pm:
        lines.append("  \u665a\u95f4\u5747\u503c\uff1a%g/%g mmHg\uff08%d \u6b21\uff09" % (mean_of(sbp_pm), mean_of(dbp_pm), len(sbp_pm)))
    else:
        lines.append("  \u665a\u95f4\u5747\u503c\uff1a\u65e0\u8bb0\u5f55")
    lines.append("")
    lines.append("[\u4e8c] \u5206\u7ea7\u63d0\u793a\uff08\u5bb6\u5ead\u8840\u538b\u5e38\u7528\u53c2\u8003\u53e3\u5f84\uff09")
    lines.append("  %s" % bp_grade(ms, md))
    lines.append("  \u53c2\u8003\u53e3\u5f84\uff1a\u5bb6\u5ead\u8840\u538b\u5e38\u7528\u53c2\u8003\u503c\u7ea6 135/85 mmHg\uff0c\u4e0e\u8bca\u5ba4\u53e3\u5f84\u4e0d\u540c")
    lines.append("  \u8fbe\u6807\u76ee\u6807\u56e0\u5e74\u9f84\u3001\u5408\u5e76\u75be\u75c5\u4e0e\u598a\u5a20\u72b6\u6001\u800c\u5f02\uff0c\u7531\u533b\u751f\u4e2a\u4f53\u5316\u8bbe\u5b9a")
    lines.append("")
    lines.append("[\u4e09] \u8bb0\u5f55\u5b8c\u6574\u6027")
    if len(sbp_all) < MIN_VALID:
        lines.append("  \u6709\u6548\u6b21\u6570 %d \u5c11\u4e8e\u5efa\u8bae\u7684 %d \u6b21\uff0c\u5efa\u8bae\u7ee7\u7eed\u8fde\u7eed\u8bb0\u5f55 7 \u5929" % (len(sbp_all), MIN_VALID))
    else:
        lines.append("  \u6709\u6548\u6b21\u6570\u8fbe\u6807")
    if not sbp_am:
        lines.append("  \u7f3a\u5c11\u6e05\u6668\u6d4b\u91cf\uff1a\u6e05\u6668\u8840\u538b\u662f\u8bc4\u4f30\u7684\u91cd\u8981\u65f6\u6bb5")
    if not sbp_pm:
        lines.append("  \u7f3a\u5c11\u665a\u95f4\u6d4b\u91cf\uff1a\u90e8\u5206\u4eba\u4ec5\u665a\u95f4\u5347\u9ad8\uff0c\u53ea\u770b\u6e05\u6668\u4f1a\u6f0f\u6389")
    lines.append("")
    lines.append("[\u56db] \u8896\u5e26\u5c3a\u5bf8")
    lines.append("  " + cuff_advice(arm_cm))
    lines.append("  \u8896\u5e26\u8fc7\u5c0f\u8bfb\u6570\u504f\u9ad8\uff0c\u8fc7\u5927\u8bfb\u6570\u504f\u4f4e")
    lines.append("")
    lines.append("[\u4e94] \u6d4b\u91cf\u89c4\u8303\u6838\u5bf9")
    for c in ["\u6d4b\u524d 30 \u5206\u949f\u4e0d\u5438\u70df\u3001\u4e0d\u996e\u5496\u5561\u6d53\u8336\u3001\u4e0d\u8fd0\u52a8",
              "\u6392\u7a7a\u8180\u80f1\uff0c\u9759\u5750\u4f11\u606f 5 \u5206\u949f",
              "\u80cc\u9760\u6905\u80cc\u3001\u53cc\u811a\u5e73\u653e\u3001\u4e0d\u7fd8\u817f\u3001\u6d4b\u91cf\u4e2d\u4e0d\u8bf4\u8bdd",
              "\u4e0a\u81c2\u88f8\u9732\u6216\u4ec5\u8584\u8863\uff0c\u8896\u5e26\u4e0b\u7f18\u8ddd\u8098\u7a9d\u7ea6 2-3 \u5398\u7c73",
              "\u4e0a\u81c2\u4e2d\u70b9\u4e0e\u5fc3\u810f\u540c\u9ad8",
              "\u6bcf\u6b21\u95f4\u9694 1-2 \u5206\u949f\u6d4b 2 \u6b21\u5e76\u53d6\u5e73\u5747"]:
        lines.append("  + %s" % c)
    lines.append("")
    if irregular:
        lines.append("[\u516d] \u5fc3\u5f8b\u63d0\u793a")
        lines.append("  \u5df2\u62a5\u544a\u8109\u640f\u4e0d\u89c4\u5219\u6216\u8840\u538b\u8ba1\u63d0\u793a\u5fc3\u5f8b\u5f02\u5e38\uff1a\u5e94\u5c31\u533b\u8bc4\u4f30\uff0c\u4e0d\u4f5c\u4e3a\u81ea\u6211\u8bca\u65ad")
    else:
        lines.append("[\u516d] \u5fc3\u5f8b\u63d0\u793a")
        lines.append("  \u82e5\u8840\u538b\u8ba1\u53cd\u590d\u63d0\u793a\u5fc3\u5f8b\u5f02\u5e38\u5e76\u4f34\u5fc3\u614c\uff0c\u5e94\u5c31\u533b\u8bc4\u4f30")
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u8bb0\u5f55\u6838\u7b97\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u8bca\u7597\u610f\u89c1\uff0c\u4e0d\u63d0\u4f9b\u836f\u7269\u5242\u91cf\u3002")
    lines.append("=" * 66)

    summary = {
        "crisis_hit": False,
        "valid_count": len(sbp_all),
        "avg_systolic": ms, "avg_diastolic": md,
        "avg_pulse": mean_of(pulse_all) if pulse_all else None,
        "morning_systolic": mean_of(sbp_am), "morning_diastolic": mean_of(dbp_am),
        "evening_systolic": mean_of(sbp_pm), "evening_diastolic": mean_of(dbp_pm),
        "grade": bp_grade(ms, md),
        "enough_readings": len(sbp_all) >= MIN_VALID,
        "cuff_advice": cuff_advice(arm_cm),
        "medication_dose_provided": False,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("\u5747\u503c\u8ba1\u7b97", mean_of([120, 130, 140]) == 130.0))
    r.append(("\u7a7a\u5217\u8868\u8fd4\u56de None", mean_of([]) is None))
    r.append(("180/120 \u4e3a\u6781\u503c", bp_grade(180, 120) == "\u8fbe\u5230\u9700\u7d27\u6025\u5c31\u533b\u7684\u6781\u503c\u8303\u56f4"))
    r.append(("185/95 \u4e3a\u6781\u503c", "\u6781\u503c" in bp_grade(185, 95)))
    r.append(("130/80 \u5728\u6b63\u5e38\u8303\u56f4", "\u4ee5\u4e0b" in bp_grade(130, 80)))
    r.append(("138/86 \u9ad8\u4e8e\u53c2\u8003\u503c", "\u9ad8\u4e8e" in bp_grade(138, 86)))
    r.append(("85/55 \u4f4e\u4e8e\u4f4e\u503c\u53e3\u5f84", "\u4f4e\u4e8e" in bp_grade(85, 55)))
    r.append(("\u81c2\u56f4 26 \u4e3a\u6807\u51c6\u8896\u5e26", "\u6807\u51c6" in cuff_advice(26)))
    r.append(("\u81c2\u56f4 38 \u5e94\u4e3a\u5927\u53f7", "\u5927\u53f7" in cuff_advice(38)))
    r.append(("\u81c2\u56f4 0 \u63d0\u793a\u672a\u63d0\u4f9b", "\u672a\u63d0\u4f9b" in cuff_advice(0)))

    readings = [
        {"date": "d1", "slot": "morning", "systolic": 132, "diastolic": 84, "pulse": 72},
        {"date": "d1", "slot": "evening", "systolic": 138, "diastolic": 88, "pulse": 76},
        {"date": "d2", "slot": "morning", "systolic": 136, "diastolic": 86, "pulse": 74},
    ]
    _, s = build_report({"readings": readings, "arm_circumference_cm": 30})
    r.append(("\u6709\u6548\u6b21\u6570 3", s["valid_count"] == 3))
    r.append(("\u6536\u7f29\u5747\u503c\u4e3a 135.3", abs(s["avg_systolic"] - 135.3) < 0.05))
    r.append(("\u8212\u5f20\u5747\u503c\u4e3a 86", abs(s["avg_diastolic"] - 86.0) < 0.05))
    r.append(("\u8109\u640f\u5747\u503c 74", abs(s["avg_pulse"] - 74.0) < 0.05))
    r.append(("\u6e05\u6668\u5747\u503c 134", abs(s["morning_systolic"] - 134.0) < 0.05))
    r.append(("\u665a\u95f4\u5747\u503c 138", abs(s["evening_systolic"] - 138.0) < 0.05))
    r.append(("\u6b21\u6570\u4e0d\u8db3", s["enough_readings"] is False))
    r.append(("\u4e0d\u63d0\u4f9b\u836f\u7269\u5242\u91cf", s["medication_dose_provided"] is False))

    _, s2 = build_report({"readings": [
        {"date": "d1", "slot": "morning", "systolic": 185, "diastolic": 95, "pulse": 80}]})
    r.append(("\u6781\u503c\u62e6\u622a", s2["crisis_hit"] is True))
    r.append(("\u6781\u503c\u65f6\u4e0d\u7ed9\u5747\u503c", s2["avg_systolic"] is None))

    _, s3 = build_report({"readings": []})
    r.append(("\u7a7a\u8bb0\u5f55\u6709\u6548\u6b21\u6570 0", s3["valid_count"] == 0))
    r.append(("\u7a7a\u8bb0\u5f55\u5747\u503c None", s3["avg_systolic"] is None))

    _, s4 = build_report({"readings": [
        {"date": "d1", "slot": "morning", "systolic": 0, "diastolic": 0, "pulse": 0}]})
    r.append(("\u65e0\u6548\u6570\u503c\u88ab\u8df3\u8fc7", s4["valid_count"] == 0))
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
    parser = argparse.ArgumentParser(description="\u5bb6\u5ead\u8840\u538b\u5468\u8bb0\u5f55\u6838\u7b97\u5de5\u5177")
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
