# -*- coding: utf-8 -*-
"""\u6e7f\u75b9\u6da6\u80a4\u5242\u6bcf\u5468\u7528\u91cf\u4f30\u7b97\u4e0e\u6d82\u62b9\u9891\u6b21\u6838\u5bf9\u5de5\u5177\u3002

\u7528\u6cd5:
  python emollient_dose_calc.py --file case.json [--json]
  python emollient_dose_calc.py --selftest

\u672c\u5de5\u5177\u4e0d\u8f93\u51fa\u4efb\u4f55\u836f\u7269\u5242\u91cf\u3002
"""
import argparse
import io
import json
import os
import sys

# \u5168\u8eab\u6bcf\u5468\u7528\u91cf\u53c2\u8003\uff08\u514b\uff09
BASE_WEEKLY = {"infant": 100.0, "child": 250.0, "adult": 500.0}
AGE_TEXT = {"infant": "\u5a74\u5e7c\u513f\uff082 \u5c81\u4ee5\u4e0b\uff09", "child": "\u513f\u7ae5\uff082-12 \u5c81\uff09", "adult": "\u9752\u5c11\u5e74\u4e0e\u6210\u4eba"}
FORM_TEXT = {
    "ointment": "\u8f6f\u818f\uff08\u6cb9\u8102\u9ad8\u3001\u5c01\u95ed\u5f3a\uff0c\u9002\u5408\u5e72\u71e5\u90e8\u4f4d\u4e0e\u51ac\u5b63\uff09",
    "cream": "\u971c\u5242\uff08\u6cb9\u6c34\u5e73\u8861\uff0c\u65e5\u5e38\u9996\u9009\uff09",
    "lotion": "\u4e73\u5242\uff08\u6e05\u723d\uff0c\u9002\u5408\u5927\u9762\u79ef\u4e0e\u590f\u5b63\uff09",
    "oil": "\u6cb9\u5242\uff08\u52a0\u5165\u6d17\u6fa1\u6c34\u51cf\u5c11\u8131\u8102\uff09",
}
FTU_GRAMS = 0.5   # \u4e00\u4e2a\u6307\u5c16\u5355\u4f4d\u7ea6 0.5 \u514b
FTU_AREA = 2.0    # \u7ea6\u8986\u76d6 2% \u4f53\u8868\u9762\u79ef
MIN_WEEKLY = 25.0


def age_group(age_years):
    a = float(age_years or 0)
    if a < 2:
        return "infant"
    if a < 13:
        return "child"
    return "adult"


def weekly_grams(age_years, area_pct):
    base = BASE_WEEKLY[age_group(age_years)]
    pct = float(area_pct or 0)
    if pct <= 0:
        return 0.0
    if pct > 100:
        pct = 100.0
    v = base * pct / 100.0
    if v < MIN_WEEKLY:
        v = MIN_WEEKLY
    return round(v, 1)


def ftu_per_application(area_pct):
    pct = float(area_pct or 0)
    if pct <= 0:
        return 0.0
    return round(pct / FTU_AREA, 1)


def single_grams(weekly, times_per_day):
    t = float(times_per_day or 0)
    if t <= 0:
        return 0.0
    return round(weekly / (t * 7.0), 1)


def freq_advice(age_years, dryness):
    base = "\u6bcf\u65e5\u81f3\u5c11 2 \u6b21"
    if dryness == "severe":
        return base + "\uff0c\u5e72\u71e5\u5b63\u8282\u6216\u5e72\u51b7\u5730\u533a\u53ef\u589e\u81f3\u6bcf\u65e5 3-4 \u6b21"
    if dryness == "mild":
        return base + "\uff0c\u590f\u5b63\u6216\u51fa\u6c57\u591a\u65f6\u53ef\u7ef4\u6301 2 \u6b21"
    return base


def build_report(data):
    age = data.get("age_years", 0)
    area = data.get("area_pct", 0)
    times = data.get("times_per_day", 2)
    form = data.get("form", "cream")
    dryness = data.get("dryness", "moderate")

    group = age_group(age)
    weekly = weekly_grams(age, area)
    ftu = ftu_per_application(area)
    single = single_grams(weekly, times)

    lines = []
    lines.append("=" * 66)
    lines.append("\u6e7f\u75b9\u6da6\u80a4\u5242\u7528\u91cf\u4f30\u7b97\u4e0e\u6d82\u62b9\u9891\u6b21")
    lines.append("=" * 66)
    lines.append("\u5e74\u9f84\uff1a%g \u5c81\uff08%s\uff09   \u53d7\u7d2f\u9762\u79ef\uff1a%g%%   \u6bcf\u65e5\u6d82\u62b9\uff1a%g \u6b21" % (
        float(age or 0), AGE_TEXT[group], float(area or 0), float(times or 0)))
    lines.append("\u5242\u578b\uff1a%s" % FORM_TEXT.get(form, "\u672a\u6307\u5b9a\uff0c\u6309\u971c\u5242\u5904\u7406"))
    lines.append("")
    lines.append("[\u4e00] \u7528\u91cf\u4f30\u7b97")
    lines.append("  \u8be5\u4eba\u7fa4\u5168\u8eab\u6bcf\u5468\u53c2\u8003\u7528\u91cf\uff1a%g \u514b" % BASE_WEEKLY[group])
    lines.append("  \u6309 %g%% \u53d7\u7d2f\u9762\u79ef\u6298\u7b97\uff0c\u6bcf\u5468\u7ea6\u9700\uff1a%g \u514b" % (float(area or 0), weekly))
    lines.append("  \u6bcf\u6b21\u7528\u91cf\u7ea6\uff1a%g \u514b\uff08\u6307\u5c16\u5355\u4f4d\u7ea6 %g \u4e2a\uff09" % (single, ftu))
    lines.append("  \u6307\u5c16\u5355\u4f4d\u53e3\u5f84\uff1a1 \u4e2a\u7ea6 %.1f \u514b\uff0c\u8986\u76d6\u7ea6 %g%% \u4f53\u8868\u9762\u79ef" % (FTU_GRAMS, FTU_AREA))
    if weekly <= MIN_WEEKLY and float(area or 0) > 0:
        lines.append("  \u9762\u79ef\u5f88\u5c0f\uff0c\u5df2\u6309\u6700\u4f4e %g \u514b/\u5468\u7ed9\u51fa\uff0c\u907f\u514d\u7528\u91cf\u4e0d\u8db3" % MIN_WEEKLY)
    lines.append("")
    lines.append("[\u4e8c] \u6d82\u62b9\u9891\u6b21")
    lines.append("  " + freq_advice(age, dryness))
    lines.append("  \u5173\u952e\u65f6\u673a\uff1a\u6c90\u6d74\u6216\u6d17\u624b\u540e 3 \u5206\u949f\u5185\u6d82\u62b9")
    lines.append("  \u76ae\u75b9\u7f13\u89e3\u540e\u4ecd\u5e94\u7ef4\u6301\u6d82\u62b9\uff0c\u4e0d\u8981\u4e00\u597d\u8f6c\u5c31\u505c")
    lines.append("")
    lines.append("[\u4e09] \u5e38\u89c1\u4e0d\u8db3\u4fe1\u53f7")
    if float(times or 0) < 2:
        lines.append("  \u5f53\u524d\u6bcf\u65e5 %g \u6b21\uff0c\u4f4e\u4e8e\u6bcf\u65e5\u81f3\u5c11 2 \u6b21\u7684\u57fa\u7840\u9891\u6b21" % float(times or 0))
    else:
        lines.append("  \u9891\u6b21\u5df2\u8fbe\u6807\uff0c\u91cd\u70b9\u6838\u5bf9\u5355\u6b21\u7528\u91cf\u662f\u5426\u8db3\u591f")
    lines.append("  \u6d82\u5b8c\u76ae\u80a4\u5e94\u6709\u4e00\u5c42\u8584\u8584\u5149\u6cfd\uff0c\u4e0d\u662f\u62b9\u5230\u5b8c\u5168\u770b\u4e0d\u89c1")
    lines.append("  \u4e00\u5468\u4e0b\u6765\u6da6\u80a4\u5242\u7528\u4e0d\u5b8c\uff0c\u901a\u5e38\u8bf4\u660e\u6d82\u5f97\u592a\u5c11")
    lines.append("")
    lines.append("[\u56db] \u6210\u5206\u4e0e\u5242\u578b\u63d0\u9192")
    lines.append("  \u4f18\u5148\uff1a\u65e0\u9999\u7cbe\u3001\u65e0\u9152\u7cbe\u3001\u542b\u795e\u7ecf\u9170\u80fa\u6216\u7518\u6cb9\u7b49\u4fdd\u6e7f\u4fee\u590d\u6210\u5206")
    lines.append("  \u907f\u5f00\uff1a\u9999\u7cbe\u3001\u9152\u7cbe\u3001\u7cbe\u6cb9\u4e0e\u690d\u7269\u63d0\u53d6\u7269\u3001\u5f3a\u6548\u9632\u8150\u6210\u5206")
    lines.append("  \u8d8a\u5e72\u8d8a\u539a\uff08\u8f6f\u818f\uff09\uff0c\u8d8a\u70ed\u8d8a\u8584\uff08\u4e73\u5242\uff09\uff1b\u65b0\u4ea7\u54c1\u5148\u5c0f\u9762\u79ef\u8bd5\u7528 2-3 \u5929")
    lines.append("")
    lines.append("[\u4e94] \u5c31\u533b\u7ea2\u7ebf\u63d0\u793a")
    lines.append("  \u6e17\u6db2\u5316\u8113\u3001\u9ec4\u8272\u7ed3\u75c2\u589e\u591a\u3001\u5468\u56f4\u7ea2\u80bf\u53d1\u70eb\uff1a\u5c3d\u5feb\u5c31\u8bca")
    lines.append("  \u5bc6\u96c6\u6c34\u75b1\u8113\u75b1\u4f34\u9ad8\u70ed\u3001\u76ae\u75b9\u5feb\u901f\u6269\u6563\u3001\u773c\u7751\u4e25\u91cd\u80bf\u80c0\uff1a\u6025\u8bca")
    lines.append("  \u5267\u70c8\u7619\u75d2\u65e0\u6cd5\u5165\u7761\u3001\u89c4\u8303\u62a4\u7406 2 \u5468\u65e0\u6539\u5584\uff1a\u5c31\u8bca")
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u62a4\u7406\u7528\u91cf\u4f30\u7b97\uff0c\u4e0d\u6784\u6210\u8bca\u7597\u610f\u89c1\uff0c\u4e0d\u63d0\u4f9b\u836f\u7269\u5242\u91cf\u3002")
    lines.append("=" * 66)

    summary = {
        "age_group": group, "area_pct": area,
        "weekly_grams": weekly, "single_grams": single,
        "ftu_per_application": ftu, "times_per_day": times,
        "freq_advice": freq_advice(age, dryness),
        "medication_dose_provided": False,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("1 \u5c81\u5f52\u5a74\u5e7c\u513f", age_group(1) == "infant"))
    r.append(("8 \u5c81\u5f52\u513f\u7ae5", age_group(8) == "child"))
    r.append(("30 \u5c81\u5f52\u6210\u4eba", age_group(30) == "adult"))
    r.append(("\u6210\u4eba\u5168\u8eab\u6bcf\u5468 500", weekly_grams(30, 100) == 500.0))
    r.append(("\u6210\u4eba\u534a\u8eab\u6bcf\u5468 250", weekly_grams(30, 50) == 250.0))
    r.append(("\u513f\u7ae5\u5168\u8eab\u6bcf\u5468 250", weekly_grams(8, 100) == 250.0))
    r.append(("\u5a74\u5e7c\u513f\u5168\u8eab\u6bcf\u5468 100", weekly_grams(1, 100) == 100.0))
    r.append(("\u9762\u79ef 0 \u7528\u91cf\u4e3a 0", weekly_grams(30, 0) == 0.0))
    r.append(("\u9762\u79ef\u8d85 100 \u6309 100 \u7b97", weekly_grams(30, 150) == 500.0))
    r.append(("\u5c0f\u9762\u79ef\u7ed9\u6700\u4f4e\u91cf", weekly_grams(30, 2) == MIN_WEEKLY))
    r.append(("\u6307\u5c16\u5355\u4f4d\u6362\u7b97", ftu_per_application(10) == 5.0))
    r.append(("\u5355\u6b21\u7528\u91cf\u6362\u7b97", single_grams(500.0, 2) == 35.7))

    _, s = build_report({"age_years": 30, "area_pct": 40, "times_per_day": 2,
                         "form": "cream", "dryness": "moderate"})
    r.append(("\u6837\u4f8b\u6bcf\u5468\u7528\u91cf 200", s["weekly_grams"] == 200.0))
    r.append(("\u6837\u4f8b\u5355\u6b21 14.3", abs(s["single_grams"] - 14.3) < 0.05))
    r.append(("\u6837\u4f8b\u6307\u5c16\u5355\u4f4d 20", s["ftu_per_application"] == 20.0))
    r.append(("\u4e0d\u63d0\u4f9b\u836f\u7269\u5242\u91cf", s["medication_dose_provided"] is False))

    _, s2 = build_report({"age_years": 30, "area_pct": 40, "times_per_day": 1})
    r.append(("\u9891\u6b21\u8bb0\u5f55\u4e3a 1 \u6b21", s2["times_per_day"] == 1))
    r.append(("\u9891\u6b21\u4e0d\u8db3\u65f6\u5355\u6b21\u7528\u91cf\u53d8\u5927", s2["single_grams"] > s["single_grams"]))

    r.append(("\u91cd\u5ea6\u5e72\u71e5\u589e\u9891\u6b21", "3-4" in freq_advice(30, "severe")))
    r.append(("\u8f7b\u5ea6\u5e72\u71e5\u7ef4\u6301 2 \u6b21", "\u590f\u5b63" in freq_advice(30, "mild")))
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
    parser = argparse.ArgumentParser(description="\u6e7f\u75b9\u6da6\u80a4\u5242\u7528\u91cf\u4f30\u7b97\u5de5\u5177")
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
