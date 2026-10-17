# -*- coding: utf-8 -*-
"""\u5b9e\u9a8c\u62a5\u544a\u6570\u636e\u4e0e\u56fe\u8868\u89c4\u8303\u6838\u67e5\u3002\u6807\u51c6\u5e93\u3002

\u7528\u6cd5:
  python lab_data_check.py --file lab.json
  python lab_data_check.py --selftest
"""

import argparse
import json
import os
import sys

RESULT_FILE = "_selftest_result.txt"

CHART_FIELDS = ["xlabel", "ylabel", "unit"]
OVER_STRONG = ["\u666e\u904d", "\u4e00\u5f8b", "\u603b\u662f", "\u5fc5\u7136", "\u8bc1\u660e", "\u5b8c\u5168\u9002\u7528\u4e8e", "all", "always", "proves"]
SUPPORTED = ["\u672c\u6b21", "\u5728\u672c\u6b21\u5b9e\u9a8c\u6761\u4ef6\u4e0b", "\u7ea6\u4e3a", "\u6761\u4ef6\u4e0b"]


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return json.loads(raw.lstrip("\ufeff"))


def sig_of(value):
    """\u53d6\u6709\u6548\u6570\u5b57\u4f4d\u6570\uff08\u6309\u6d6e\u70b9\u8868\u793a\u4f30\u8ba1\uff09\u3002"""
    if value == 0:
        return 1
    s = repr(float(value))
    if "e" in s or "E" in s:
        return len(s.replace("-", "").replace(".", "").replace("e", "").replace("E", "")) - 1
    if "." in s:
        frac = s.split(".")[1].rstrip("0")
        return len(frac) if frac else 1
    return 1


def check_units(records):
    units = [str(r.get("unit") or "").strip() for r in records]
    missing = [i for i, u in enumerate(units) if not u]
    unique = sorted({u for u in units if u})
    consistent = len(unique) <= 1
    return {"missing": missing, "unique": unique, "consistent": consistent}


def check_sig(records, instrument_sig):
    """\u6709\u6548\u6570\u5b57\u4f4d\u6570\u4e0d\u5f97\u8d85\u8fc7\u4eea\u5668\u7cbe\u5ea6\u3002"""
    over = []
    for i, r in enumerate(records):
        want = r.get("sig")
        if want is None and r.get("value") is not None:
            want = sig_of(r["value"])
        if want and instrument_sig and int(want) > int(instrument_sig):
            over.append({"index": i, "record_sig": int(want), "instrument_sig": int(instrument_sig)})
    return over


def check_overwrite(records):
    return [i for i, r in enumerate(records) if r.get("overwritten")]


def check_outliers(records, outliers):
    """\u5f02\u5e38\u503c\u5fc5\u987b\u6807\u6ce8\u5904\u7406\u65b9\u5f0f\uff0c\u4e14\u4e0d\u5f97\u76f4\u63a5\u5220\u9664\u3002"""
    issues = []
    for idx in outliers or []:
        if idx >= len(records):
            issues.append({"index": idx, "problem": "\u7d22\u5f15\u8d8a\u754c"})
            continue
        r = records[idx]
        if not str(r.get("outlier_action") or "").strip():
            issues.append({"index": idx, "problem": "\u5f02\u5e38\u503c\u672a\u6807\u6ce8\u5904\u7406\u65b9\u5f0f"})
        elif r.get("deleted"):
            issues.append({"index": idx, "problem": "\u76f4\u63a5\u5220\u9664\u5f02\u5e38\u503c\u4e0d\u5408\u89c4"})
    return issues


def check_chart(chart):
    c = chart or {}
    missing = [k for k in CHART_FIELDS if not str(c.get(k) or "").strip()]
    if not str(c.get("legend") or "").strip() and int(c.get("series") or 1) > 1:
        missing.append("legend")
    if int(c.get("measure_times") or 1) > 1 and not c.get("error_bar"):
        missing.append("error_bar")
    return missing


def check_conclusion(conclusion, repeats):
    """\u7ed3\u8bba\u5f3a\u5ea6\u662f\u5426\u4e0e\u6570\u636e\u5f3a\u5ea6\u5339\u914d\u3002"""
    text = conclusion or ""
    strong = [w for w in OVER_STRONG if w in text]
    hedged = any(w in text for w in SUPPORTED)
    if strong and not hedged:
        return {"ok": False, "strong_words": strong, "tip": "\u5355\u6b21\u6216\u5c11\u91cf\u6570\u636e\u4e0d\u5f97\u4f5c\u666e\u904d\u5316\u63a8\u5e7f\uff0c\u5e94\u9650\u5b9a\u6761\u4ef6"}
    if repeats <= 1 and not hedged:
        return {"ok": False, "strong_words": strong, "tip": "\u5355\u6b21\u6d4b\u91cf\u53ea\u80fd\u5199\u672c\u6b21\u6d4b\u5f97"}
    return {"ok": True, "strong_words": strong, "tip": "\u7ed3\u8bba\u5f3a\u5ea6\u4e0e\u6570\u636e\u5f3a\u5ea6\u5339\u914d"}


def analyze(data):
    records = data.get("records") or []
    inst = data.get("instrument_sig")
    return {
        "count": len(records),
        "units": check_units(records),
        "over_precision": check_sig(records, inst),
        "overwritten": check_overwrite(records),
        "outlier_issues": check_outliers(records, data.get("outliers")),
        "chart_missing": check_chart(data.get("chart")),
        "conclusion": check_conclusion(data.get("conclusion"), int(data.get("repeats") or 1)),
    }


def run_file(path, as_json):
    res = analyze(read_json(path))
    if as_json:
        return json.dumps(res, ensure_ascii=False, indent=2)
    lines = []
    lines.append("\u6570\u636e\u6761\u6570: %d" % res["count"])
    u = res["units"]
    lines.append("\u5355\u4f4d: \u7f3a\u5931=%s \u79cd\u7c7b=%s \u4e00\u81f4=%s"
                 % (u["missing"] or "\u65e0", u["unique"] or "\u65e0", "\u662f" if u["consistent"] else "\u5426"))
    lines.append("\u6709\u6548\u6570\u5b57\u8d85\u4eea\u5668\u7cbe\u5ea6: %s" % (res["over_precision"] or "\u65e0"))
    lines.append("\u539f\u59cb\u8bb0\u5f55\u88ab\u6d82\u6539: %s" % (res["overwritten"] or "\u65e0"))
    if res["overwritten"]:
        lines.append("  \u6d82\u6539\u987b\u7528\u5212\u7ebf\u66f4\u6b63\u5e76\u4fdd\u7559\u539f\u503c\u53ef\u8fa8\u8ba4\uff0c\u4e14\u7b7e\u540d\u65e5\u671f")
    lines.append("\u5f02\u5e38\u503c\u95ee\u9898: %s" % (res["outlier_issues"] or "\u65e0"))
    lines.append("\u56fe\u8868\u7f3a\u9879: %s" % (res["chart_missing"] or "\u65e0"))
    lines.append("\u7ed3\u8bba\u68c0\u67e5: \u901a\u8fc7=%s \u63d0\u793a=%s"
                 % ("\u662f" if res["conclusion"]["ok"] else "\u5426", res["conclusion"]["tip"]))
    return "\n".join(lines)


def selftest():
    fails = []

    def ck(name, cond):
        if not cond:
            fails.append(name)

    ck("t1 \u6709\u6548\u4f4d\u6570\u8ba1\u7b97", sig_of(1.234) == 3)
    ck("t2 \u6574\u6570\u6709\u6548\u4f4d\u4e3a1", sig_of(12) == 1)
    ck("t3 \u96f6\u7684\u6709\u6548\u4f4d\u4e3a1", sig_of(0) == 1)

    recs = [{"value": 1.234, "unit": "m"}, {"value": 2.345, "unit": "m"}]
    ck("t4 \u5355\u4f4d\u4e00\u81f4", check_units(recs)["consistent"] is True)
    recs2 = [{"value": 1.0, "unit": "m"}, {"value": 2.0, "unit": ""}]
    ck("t5 \u7f3a\u5355\u4f4d\u88ab\u8bc6\u522b", check_units(recs2)["missing"] == [1])

    ck("t6 \u8d85\u51fa\u4eea\u5668\u7cbe\u5ea6\u88ab\u8bc6\u522b", len(check_sig([{"value": 1.234}], 2)) == 1)
    ck("t7 \u672a\u8d85\u7cbe\u5ea6\u4e0d\u62a5", check_sig([{"value": 1.2}], 3) == [])

    ck("t8 \u6d82\u6539\u88ab\u8bc6\u522b", check_overwrite([{"value": 1, "overwritten": True}]) == [0])
    ck("t9 \u672a\u6d82\u6539\u4e0d\u62a5", check_overwrite([{"value": 1}]) == [])

    oi = check_outliers([{"value": 9.9}, {"value": 1.0}], [0])
    ck("t10 \u5f02\u5e38\u503c\u672a\u6807\u6ce8\u88ab\u62a5", len(oi) == 1)
    oi2 = check_outliers([{"value": 9.9, "outlier_action": "\u820d\u5f03", "deleted": True}], [0])
    ck("t11 \u76f4\u63a5\u5220\u9664\u88ab\u62a5", any("\u5220\u9664" in x["problem"] for x in oi2))
    ck("t12 \u5408\u89c4\u5f02\u5e38\u503c\u4e0d\u62a5", check_outliers([{"value": 1, "outlier_action": "\u4fdd\u7559"}], [0]) == [])

    ck("t13 \u56fe\u8868\u7f3a\u9879\u88ab\u8bc6\u522b", "xlabel" in check_chart({"ylabel": "y", "unit": "s"}))
    ck("t14 \u591a\u7cfb\u5217\u7f3a\u56fe\u4f8b\u88ab\u8bc6\u522b", "legend" in check_chart({"xlabel": "x", "ylabel": "y", "unit": "s", "series": 2}))
    ck("t15 \u591a\u6b21\u6d4b\u91cf\u7f3a\u8bef\u5dee\u68d2\u88ab\u8bc6\u522b", "error_bar" in check_chart({"xlabel": "x", "ylabel": "y", "unit": "s", "measure_times": 5}))

    ck("t16 \u5355\u6b21\u6d4b\u91cf\u8fc7\u5ea6\u6982\u62ec\u88ab\u62e6", check_conclusion("\u9a8c\u8bc1\u4e86\u666e\u904d\u89c4\u5f8b", 1)["ok"] is False)
    ck("t17 \u5355\u6b21\u6d4b\u91cf\u9650\u5b9a\u8868\u8ff0\u901a\u8fc7", check_conclusion("\u672c\u6b21\u6d4b\u5f97\u7ea6\u4e3a 1.2", 1)["ok"] is True)

    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_case.json")
    with open(tmp, "w", encoding="utf-8-sig") as f:
        json.dump({"records": []}, f, ensure_ascii=False)
    ck("t18 BOM \u8f93\u5165\u89e3\u6790\u6210\u529f", isinstance(read_json(tmp)["records"], list))
    os.remove(tmp)

    ck("t19 \u7a7a\u6570\u636e\u4e0d\u62a5\u9519", analyze({})["count"] == 0)
    ck("t20 \u8d8a\u754c\u7d22\u5f15\u88ab\u62a5", len(check_outliers([{"value": 1}], [5])) == 1)

    out = []
    out.append("SELFTEST FAIL: %s" % "; ".join(fails) if fails else "SELFTEST OK  20/20")
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, RESULT_FILE), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="\u5b9e\u9a8c\u62a5\u544a\u89c4\u8303\u6838\u67e5")
    ap.add_argument("--file")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.file:
        print(run_file(a.file, a.json))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())