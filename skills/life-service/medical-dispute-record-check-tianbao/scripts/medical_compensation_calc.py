# -*- coding: utf-8 -*-
"""\u533b\u7597\u7ea0\u7eb7\u4eba\u8eab\u635f\u5bb3\u8d54\u507f\u6838\u7b97\u5de5\u5177\u3002

\u7528\u6cd5:
  python medical_compensation_calc.py --file \u6848\u4ef6.json [--json]
  python medical_compensation_calc.py --selftest

\u8ba1\u7b97\u6807\u51c6\u7531\u4f7f\u7528\u8005\u6309\u53d7\u8bc9\u6cd5\u9662\u6240\u5728\u5730\u73b0\u884c\u516c\u5e03\u6570\u636e\u586b\u5165\u3002
"""
import argparse
import io
import json
import os
import sys

DISABILITY_COEF = {1: 1.0, 2: 0.9, 3: 0.8, 4: 0.7, 5: 0.6,
                   6: 0.5, 7: 0.4, 8: 0.3, 9: 0.2, 10: 0.1}
DAYS_PER_MONTH = 30.0
FUNERAL_MONTHS = 6


def compensation_years(age):
    """\u8d54\u507f\u5e74\u9650\uff1a60\u5c81\u4ee5\u4e0b20\u5e74\uff1b60\u5c81\u4ee5\u4e0a\u6bcf\u589e\u52a01\u5c81\u51cf1\u5e74\uff1b75\u5c81\u4ee5\u4e0a\u63095\u5e74\u3002"""
    age = float(age)
    if age < 60:
        return 20.0
    if age >= 75:
        return 5.0
    return 20.0 - (age - 60.0)


def disability_coef(level):
    level = int(level or 0)
    if level <= 0:
        return 0.0
    return DISABILITY_COEF.get(level, 0.0)


def lost_income(lost_days, monthly_income):
    return float(lost_days) * (float(monthly_income) / DAYS_PER_MONTH)


def nursing_fee(nursing_days, nursing_rate, nursing_count=1):
    return float(nursing_days) * float(nursing_rate) * float(nursing_count or 1)


def meal_allowance(hospital_days, meal_rate):
    return float(hospital_days) * float(meal_rate)


def nutrition_fee(nutrition_days, nutrition_rate):
    return float(nutrition_days) * float(nutrition_rate)


def disability_compensation(urban_income, age, level):
    return float(urban_income) * compensation_years(age) * disability_coef(level)


def death_compensation(urban_income, age):
    return float(urban_income) * compensation_years(age)


def funeral_fee(wage_monthly):
    return float(wage_monthly) * FUNERAL_MONTHS


def dependent_living(dependent_annual, dependent_years, supporters):
    supporters = float(supporters or 1)
    if supporters <= 0:
        supporters = 1.0
    return float(dependent_annual) * float(dependent_years) / supporters


def build_report(data):
    medical = float(data.get("medical_expense", 0) or 0)
    lost_days = float(data.get("lost_days", 0) or 0)
    monthly_income = float(data.get("monthly_income", 0) or 0)
    nursing_days = float(data.get("nursing_days", 0) or 0)
    nursing_rate = float(data.get("nursing_rate", 0) or 0)
    nursing_count = float(data.get("nursing_count", 1) or 1)
    hospital_days = float(data.get("hospital_days", 0) or 0)
    meal_rate = float(data.get("meal_rate", 0) or 0)
    nutrition_days = float(data.get("nutrition_days", 0) or 0)
    nutrition_rate = float(data.get("nutrition_rate", 0) or 0)
    transport = float(data.get("transport", 0) or 0)
    level = int(data.get("disability_level", 0) or 0)
    death = bool(data.get("death", False))
    age = float(data.get("age", 0) or 0)
    urban_income = float(data.get("urban_income", 0) or 0)
    wage_monthly = float(data.get("wage_monthly", 0) or 0)
    aid_device = float(data.get("aid_device", 0) or 0)
    spiritual = float(data.get("spiritual", 0) or 0)
    spiritual_with_ratio = bool(data.get("spiritual_with_ratio", False))
    fault_ratio = float(data.get("fault_ratio", 1) or 1)
    dep_annual = float(data.get("dependent_annual", 0) or 0)
    dep_years = float(data.get("dependent_years", 0) or 0)
    supporters = float(data.get("supporters", 1) or 1)

    items = []
    items.append(("\u533b\u7597\u8d39", medical, "\u6309\u7968\u636e\u636e\u5b9e\uff0c\u542b\u786e\u5b9a\u5fc5\u7136\u53d1\u751f\u7684\u540e\u7eed\u6cbb\u7597\u8d39"))
    items.append(("\u8bef\u5de5\u8d39", lost_income(lost_days, monthly_income),
                  "%g \u5929 x \u6708\u6536\u5165 %.2f / 30" % (lost_days, monthly_income)))
    items.append(("\u62a4\u7406\u8d39", nursing_fee(nursing_days, nursing_rate, nursing_count),
                  "%g \u5929 x %.2f \u5143/\u5929 x %g \u4eba" % (nursing_days, nursing_rate, nursing_count)))
    items.append(("\u4ea4\u901a\u8d39", transport, "\u51ed\u7968\u636e\u636e\u5b9e"))
    items.append(("\u4f4f\u9662\u4f19\u98df\u8865\u52a9\u8d39", meal_allowance(hospital_days, meal_rate),
                  "%g \u5929 x %.2f \u5143/\u5929\uff08\u5f53\u5730\u51fa\u5dee\u4f19\u98df\u8865\u52a9\u6807\u51c6\uff09" % (hospital_days, meal_rate)))
    items.append(("\u8425\u517b\u8d39", nutrition_fee(nutrition_days, nutrition_rate),
                  "%g \u5929 x %.2f \u5143/\u5929\uff08\u53c2\u7167\u533b\u7597\u673a\u6784\u610f\u89c1\uff09" % (nutrition_days, nutrition_rate)))
    if death:
        items.append(("\u6b7b\u4ea1\u8d54\u507f\u91d1", death_compensation(urban_income, age),
                      "%.2f x %.1f \u5e74" % (urban_income, compensation_years(age))))
        items.append(("\u4e27\u846c\u8d39", funeral_fee(wage_monthly),
                      "\u804c\u5de5\u6708\u5e73\u5747\u5de5\u8d44 %.2f x 6 \u4e2a\u6708" % wage_monthly))
    elif level > 0:
        items.append(("\u6b8b\u75be\u8d54\u507f\u91d1", disability_compensation(urban_income, age, level),
                      "%.2f x %.1f \u5e74 x \u4f24\u6b8b\u7cfb\u6570 %.1f" % (
                          urban_income, compensation_years(age), disability_coef(level))))
    if aid_device > 0:
        items.append(("\u6b8b\u75be\u8f85\u52a9\u5668\u5177\u8d39", aid_device, "\u6309\u666e\u901a\u9002\u7528\u5668\u5177\u7684\u5408\u7406\u8d39\u7528"))
    dep = dependent_living(dep_annual, dep_years, supporters) if dep_annual > 0 else 0.0
    if dep > 0:
        items.append(("\u88ab\u6276\u517b\u4eba\u751f\u6d3b\u8d39", dep,
                      "%.2f x %.1f \u5e74 / %g \u4eba" % (dep_annual, dep_years, supporters)))

    material_total = sum(v for _, v, _ in items)
    material_after = material_total * fault_ratio
    spiritual_after = spiritual * fault_ratio if spiritual_with_ratio else spiritual
    total = material_after + spiritual_after

    lines = []
    lines.append("=" * 60)
    lines.append("\u533b\u7597\u7ea0\u7eb7\u4eba\u8eab\u635f\u5bb3\u8d54\u507f \u6838\u7b97\u7ed3\u679c")
    lines.append("=" * 60)
    lines.append("\u53d7\u5bb3\u4eba\u5e74\u9f84\uff1a%g \u5c81   \u8d54\u507f\u5e74\u9650\uff1a%.1f \u5e74" % (age, compensation_years(age)))
    lines.append("\u4f24\u6b8b\u7b49\u7ea7\uff1a%s   \u6b7b\u4ea1\u60c5\u5f62\uff1a%s" % (level if level > 0 else "\u672a\u8bc4\u5b9a", "\u662f" if death else "\u5426"))
    lines.append("\u8fc7\u9519\u53c2\u4e0e\u5ea6\uff1a%.2f\uff08%.0f%%\uff09" % (fault_ratio, fault_ratio * 100))
    lines.append("")
    lines.append("[\u4e00] \u8d54\u507f\u9879\u76ee\u660e\u7ec6")
    lines.append("%-16s %14s   \u8ba1\u7b97\u8bf4\u660e" % ("\u9879\u76ee", "\u91d1\u989d"))
    lines.append("-" * 60)
    for name, value, note in items:
        lines.append("%-16s %14.2f   %s" % (name, value, note))
    lines.append("-" * 60)
    lines.append("%-16s %14.2f" % ("\u7269\u8d28\u635f\u5931\u5408\u8ba1", material_total))
    lines.append("")
    lines.append("[\u4e8c] \u8fc7\u9519\u53c2\u4e0e\u5ea6\u6298\u7b97")
    lines.append("  \u7269\u8d28\u635f\u5931 x \u53c2\u4e0e\u5ea6 = %.2f x %.2f = %.2f" % (material_total, fault_ratio, material_after))
    if spiritual > 0:
        if spiritual_with_ratio:
            lines.append("  \u7cbe\u795e\u635f\u5bb3\u629a\u6170\u91d1\uff08\u6309\u53c2\u4e0e\u5ea6\u6298\u7b97\uff09= %.2f x %.2f = %.2f" % (
                spiritual, fault_ratio, spiritual_after))
            lines.append("  \u53e6\u4e00\u53e3\u5f84\uff1a\u7cbe\u795e\u635f\u5bb3\u629a\u6170\u91d1\u4e0d\u6298\u7b97 = %.2f\uff08\u5408\u8ba1 %.2f\uff09" % (
                spiritual, material_after + spiritual))
        else:
            lines.append("  \u7cbe\u795e\u635f\u5bb3\u629a\u6170\u91d1\uff08\u4e0d\u6298\u7b97\uff09= %.2f" % spiritual)
            lines.append("  \u53e6\u4e00\u53e3\u5f84\uff1a\u6309\u53c2\u4e0e\u5ea6\u6298\u7b97 = %.2f\uff08\u5408\u8ba1 %.2f\uff09" % (
                spiritual * fault_ratio, material_after + spiritual * fault_ratio))
        lines.append("  \u63d0\u793a\uff1a\u7cbe\u795e\u635f\u5bb3\u629a\u6170\u91d1\u662f\u5426\u518d\u4e58\u53c2\u4e0e\u5ea6\uff0c\u5404\u5730\u53e3\u5f84\u4e0d\u540c\uff0c\u4e24\u79cd\u90fd\u5217\u51fa")
    lines.append("")
    lines.append("[\u4e09] \u53ef\u4e3b\u5f20\u91d1\u989d")
    lines.append("  \u5408\u8ba1\uff1a%.2f \u5143" % total)
    lines.append("")
    lines.append("[\u56db] \u5173\u952e\u63d0\u793a")
    lines.append("  1. \u672a\u505a\u9274\u5b9a\u7684\uff0c\u53c2\u4e0e\u5ea6\u4e0e\u4f24\u6b8b\u7b49\u7ea7\u5c1a\u65e0\u4f9d\u636e\uff0c\u672c\u7ed3\u679c\u4ec5\u4e3a\u4f30\u7b97\u533a\u95f4")
    lines.append("  2. \u4e0d\u6784\u6210\u533b\u7597\u4e8b\u6545\u4e0d\u7b49\u4e8e\u4e0d\u627f\u62c5\u533b\u7597\u635f\u5bb3\u8d54\u507f\u8d23\u4efb")
    lines.append("  3. \u5e76\u53d1\u75c7\u4e0d\u7b49\u4e8e\u65e0\u8fc7\u9519\uff0c\u9700\u770b\u8bca\u7597\u4e49\u52a1\u3001\u544a\u77e5\u4e49\u52a1\u4e0e\u5904\u7f6e\u53ca\u65f6\u6027")
    lines.append("  4. \u8c03\u89e3\u534f\u8bae\u53ef\u7533\u8bf7\u53f8\u6cd5\u786e\u8ba4\uff0c\u672a\u7ecf\u786e\u8ba4\u7684\u5f3a\u5236\u6267\u884c\u529b\u6709\u9650")
    lines.append("  5. \u91cd\u5927\u635f\u5bb3\u4e0d\u8981\u5728\u9274\u5b9a\u524d\u7b7e\u7f72\u4e00\u6b21\u6027\u4e86\u7ed3\u534f\u8bae")
    lines.append("  6. \u8ba1\u7b97\u6807\u51c6\u4ee5\u53d7\u8bc9\u6cd5\u9662\u6240\u5728\u5730\u73b0\u884c\u516c\u5e03\u6570\u636e\u4e3a\u51c6")
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u91d1\u989d\u6838\u7b97\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u8fc7\u9519\u8ba4\u5b9a\u3001\u9274\u5b9a\u610f\u89c1\u6216\u6cd5\u5f8b\u610f\u89c1\u3002")
    lines.append("=" * 60)

    summary = {
        "age": age,
        "compensation_years": compensation_years(age),
        "disability_level": level,
        "death": death,
        "fault_ratio": fault_ratio,
        "items": [{"name": n, "amount": round(v, 4), "note": note} for n, v, note in items],
        "material_total": round(material_total, 4),
        "material_after_ratio": round(material_after, 4),
        "spiritual": round(spiritual, 4),
        "spiritual_after_ratio": round(spiritual_after, 4),
        "spiritual_with_ratio": spiritual_with_ratio,
        "total": round(total, 4),
        "total_alt": round(material_after + (spiritual if spiritual_with_ratio else spiritual * fault_ratio), 4),
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []

    # 1) \u8d54\u507f\u5e74\u9650
    r.append(("\u5e74\u9650 45\u5c81=20", compensation_years(45) == 20.0))
    r.append(("\u5e74\u9650 65\u5c81=15", abs(compensation_years(65) - 15.0) < 1e-9))
    r.append(("\u5e74\u9650 75\u5c81=5", compensation_years(75) == 5.0))
    r.append(("\u5e74\u9650 80\u5c81=5", compensation_years(80) == 5.0))

    # 2) \u4f24\u6b8b\u7cfb\u6570
    r.append(("\u4e00\u7ea7\u7cfb\u6570 1.0", disability_coef(1) == 1.0))
    r.append(("\u5341\u7ea7\u7cfb\u6570 0.1", abs(disability_coef(10) - 0.1) < 1e-9))
    r.append(("\u672a\u8bc4\u6b8b\u7cfb\u6570 0", disability_coef(0) == 0.0))

    # 3) \u8bef\u5de5\u8d39 90\u5929 * 9000/30 = 27000
    r.append(("\u8bef\u5de5\u8d39 27000", abs(lost_income(90, 9000) - 27000.0) < 1e-6))

    # 4) \u62a4\u7406\u8d39 60*150*1 = 9000
    r.append(("\u62a4\u7406\u8d39 9000", abs(nursing_fee(60, 150, 1) - 9000.0) < 1e-9))

    # 5) \u4e27\u846c\u8d39 = \u6708\u5de5\u8d44*6
    r.append(("\u4e27\u846c\u8d39 60000", abs(funeral_fee(10000) - 60000.0) < 1e-9))

    # 6) \u6b8b\u75be\u8d54\u507f\u91d1 60000*20*0.3 = 360000 (8\u7ea7)
    r.append(("\u6b8b\u75be\u8d54\u507f\u91d1 360000", abs(disability_compensation(60000, 45, 8) - 360000.0) < 1e-6))

    # 7) \u6b7b\u4ea1\u8d54\u507f\u91d1 60000*20 = 1200000
    r.append(("\u6b7b\u4ea1\u8d54\u507f\u91d1 1200000", abs(death_compensation(60000, 45) - 1200000.0) < 1e-6))

    # 8) \u88ab\u6276\u517b\u4eba\u751f\u6d3b\u8d39 24000*10/2 = 120000
    r.append(("\u88ab\u6276\u517b\u4eba\u751f\u6d3b\u8d39 120000", abs(dependent_living(24000, 10, 2) - 120000.0) < 1e-6))

    # 9) \u53c2\u4e0e\u5ea6\u6298\u7b97
    _, s = build_report({
        "medical_expense": 80000, "lost_days": 90, "monthly_income": 9000,
        "nursing_days": 60, "nursing_rate": 150, "hospital_days": 45,
        "meal_rate": 100, "nutrition_days": 60, "nutrition_rate": 50,
        "transport": 2000, "disability_level": 8, "death": False,
        "age": 45, "urban_income": 60000, "wage_monthly": 10000,
        "aid_device": 0, "spiritual": 30000, "spiritual_with_ratio": False,
        "fault_ratio": 0.6,
    })
    material = 80000 + 27000 + 9000 + 2000 + 4500 + 3000 + 360000
    r.append(("\u7269\u8d28\u635f\u5931\u5408\u8ba1", abs(s["material_total"] - material) < 1e-6))
    r.append(("\u53c2\u4e0e\u5ea6\u6298\u7b97", abs(s["material_after_ratio"] - material * 0.6) < 1e-6))
    r.append(("\u5408\u8ba1\u542b\u7cbe\u795e\u629a\u6170\u91d1", abs(s["total"] - (material * 0.6 + 30000)) < 1e-6))

    # 10) \u7cbe\u795e\u635f\u5bb3\u629a\u6170\u91d1\u6309\u53c2\u4e0e\u5ea6\u6298\u7b97\u7684\u53e6\u4e00\u79cd\u53e3\u5f84
    _, s2 = build_report({
        "medical_expense": 10000, "age": 45, "urban_income": 60000,
        "disability_level": 0, "spiritual": 20000,
        "spiritual_with_ratio": True, "fault_ratio": 0.5,
    })
    r.append(("\u7cbe\u795e\u629a\u6170\u91d1\u6298\u7b97", abs(s2["spiritual_after_ratio"] - 10000.0) < 1e-6))

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
    parser = argparse.ArgumentParser(description="\u533b\u7597\u7ea0\u7eb7\u4eba\u8eab\u635f\u5bb3\u8d54\u507f\u6838\u7b97\u5de5\u5177")
    parser.add_argument("--file", help="\u6848\u4ef6 JSON \u6587\u4ef6\u8def\u5f84\uff08UTF-8\uff09")
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
