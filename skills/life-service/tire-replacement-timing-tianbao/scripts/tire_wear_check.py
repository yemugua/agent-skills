# -*- coding: utf-8 -*-
"""tire_wear_check: \u8f6e\u80ce\u78e8\u635f\u3001\u5e74\u9650\u4e0e\u504f\u78e8\u7684\u5224\u5b9a\u3002

\u7528\u6cd5:
    python tire_wear_check.py --week 22 --year 2022 --depth 2.5 --skew 3
    python tire_wear_check.py --file tire.json --out result.md
    python tire_wear_check.py --selftest
"""
import argparse
import json
import os
from datetime import date

# \u5e38\u89c1\u5e74\u9650\u53c2\u8003\uff08\u5e74\uff09\u3002\u5177\u4f53\u4ee5\u8f6e\u80ce\u5382\u5bb6\u6807\u6ce8\u7684\u4f7f\u7528\u5e74\u9650\u4e3a\u51c6
LIFE_REF = {"\u8f7b": 3, "\u4e2d": 4, "\u91cd": 5}
# \u5e38\u89c1\u4f46\u4e0d\u662f\u6cd5\u5b9a\u503c\u7684\u53c2\u8003\u523b\u5ea6\uff0c\u7528\u4e8e\u63d0\u793a\u800c\u4e0d\u662f\u5224\u5b9a
DEPTH_HINT = [(6.0, "\u4f59\u91cf\u5145\u8db3"), (4.0, "\u8fdb\u5165\u9700\u8981\u5173\u6ce8\u7684\u533a\u95f4"),
              (2.0, "\u4f59\u91cf\u504f\u5c11"), (0.0, "\u4f59\u91cf\u6781\u5c11")]

SKEW_CAUSE = [
    ("\u5355\u4fa7\u504f\u78e8\uff0c\u5de6\u53f3\u5dee\u5f02\u5927", "\u80ce\u538b\u957f\u671f\u504f\u9ad8\u6216\u504f\u4f4e"),
    ("\u504f\u78e8\u540c\u65f6\u65b9\u5411\u76d8\u504f", "\u5b9a\u4f4d\u504f\u5dee"),
    ("\u80ce\u9762\u8fb9\u7f18\u78e8\u635f", "\u80ce\u538b\u957f\u671f\u504f\u4f4e"),
    ("\u80ce\u9762\u4e2d\u95f4\u78e8\u635f\u4e24\u4fa7\u6d45", "\u80ce\u538b\u957f\u671f\u504f\u9ad8"),
    ("\u5355\u80ce\u4e0d\u89c4\u5219\u952f\u9f7f\u72b6", "\u8f6e\u8f8b\u53d8\u5f62\u6216\u8f74\u627f\u5f02\u5e38"),
    ("\u80ce\u4fa7\u5f02\u5e38\u78e8\u635f", "\u5b9a\u4f4d\u504f\u5dee\u6216\u8f7d\u91cd\u5f02\u5e38"),
    ("\u524d\u540e\u78e8\u635f\u5dee\u5f02\u5927", "\u9a71\u52a8\u5f62\u5f0f\u4e0e\u8f74\u8377\u5206\u914d\uff0c\u5148\u786e\u8ba4\u662f\u5426\u4e3a\u8be5\u8f66\u6b63\u5e38\u8868\u73b0"),
]

SKEW_THRESHOLD = 1.5

RED_LINES = [
    "\u9f13\u5305",
    "\u80ce\u4fa7\u5272\u4f24\u6216\u88c2\u53e3",
    "\u5e18\u7ebf\u66b4\u9732",
    "\u80ce\u7eb9\u4f4e\u4e8e\u73b0\u884c\u89c4\u5b9a\u4e0b\u9650",
    "\u5f02\u5e38\u53d1\u70ed",
    "\u884c\u9a76\u4e2d\u5f02\u5e38\u9707\u52a8\u4e14\u65b9\u5411\u4e0d\u7a33",
]

AFTER_STEPS = [
    "\u505a\u52a8\u5e73\u8861\uff1a\u65b0\u80ce\u88c5\u4e0a\u540e\u5fc5\u987b\u505a\u52a8\u5e73\u8861",
    "\u6309\u8f66\u8f86\u8bf4\u660e\u4e66\u89c4\u5b9a\u7684\u51b7\u80ce\u80ce\u538b\u68c0\u67e5\u80ce\u538b",
    "\u505a\u56db\u8f6e\u5b9a\u4f4d\uff0c\u5c24\u5176\u662f\u6709\u504f\u78e8\u6216\u539f\u8f66\u6709\u5b9a\u4f4d\u6570\u636e\u8bb0\u5f55\u7684",
    "\u786e\u8ba4\u65b9\u5411\u76d8\u5c45\u4e2d\uff0c\u8f66\u8f86\u4e0d\u8dd1\u504f",
    "\u91cc\u7a0b\u4e0a\u6765\u540e\u590d\u6d4b\u4e00\u6b21\u80ce\u538b\u4e0e\u78e8\u635f\u662f\u5426\u5747\u5300",
]


def load_json(path):
    """Read JSON, tolerating the UTF-8 BOM written by PowerShell."""
    raw = open(path, "r", encoding="utf-8-sig").read().strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise ValueError("json parse failed: %s" % exc)


def to_float(value, default=0.0):
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return default
    return default


def parse_week_code(week, year):
    """Return an approximate production date from a week/year code."""
    w = int(week)
    y = int(year)
    if w < 1 or w > 53:
        raise ValueError("week out of range: %s" % week)
    if y < 1980 or y > 2200:
        raise ValueError("year out of range: %s" % year)
    base = date(y, 1, 1)
    days = (w - 1) * 7 + base.weekday()
    ordinal = days + 1
    if ordinal > (date(y, 12, 31).timetuple().tm_yday):
        y += 1
        ordinal -= date(y - 1, 12, 31).timetuple().tm_yday
        ordinal = max(1, ordinal)
    lengths = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if y % 4 == 0:
        lengths[1] = 29
    left = ordinal
    month = 12
    for idx in range(12):
        if left <= lengths[idx]:
            month = idx + 1
            break
        left -= lengths[idx]
    return y, month


def months_between(y1, m1, y2, m2):
    return (y2 - y1) * 12 + (m2 - m1)


def depth_hint(depth):
    for limit, label in DEPTH_HINT:
        if depth >= limit:
            return label
    return "\u4f59\u91cf\u6781\u5c11"


def skew_causes(skew):
    if skew <= 0:
        return []
    if skew < SKEW_THRESHOLD:
        return [("\u5de6\u53f3\u78e8\u635f\u5dee\u5f02\u8f83\u5c0f", "\u7ee7\u7eed\u89c2\u5bdf\u5373\u53ef")]
    return [(name, cause) for name, cause in SKEW_CAUSE]


def build_report(d):
    week = d.get("week", 22)
    year = d.get("year", 2022)
    depth = to_float(d.get("depth"), 0.0)
    skew = abs(to_float(d.get("skew"), 0.0))
    duty = str(d.get("duty", "\u4e2d")).strip() or "\u4e2d"
    if duty not in LIFE_REF:
        duty = "\u4e2d"
    today = date.today()

    out = ["# \u8f6e\u80ce\u78e8\u635f\u4e0e\u5e74\u9650\u5224\u5b9a", ""]
    out.append("## \u751f\u4ea7\u65e5\u671f\u89e3\u6790")
    out.append("")
    try:
        py, pm = parse_week_code(week, year)
        months = months_between(py, pm, today.year, today.month)
        out.append("- \u5468\u6570\u7f16\u7801\uff1a%02d%02d \u8868\u793a\u7b2c %d \u5468\u3001\u751f\u4ea7\u4e8e %d \u5e74"
                   % (int(week), int(year) % 100, int(week), int(year)))
        out.append("- \u4f30\u7b97\u751f\u4ea7\u5e74\u6708\uff1a**%d \u5e74 %d \u6708**" % (py, pm))
        out.append("- \u8ddd\u4eca\u7ea6\uff1a**%d \u4e2a\u6708**" % months)
        ref = LIFE_REF[duty]
        limit = months - ref * 12
        out.append("- \u5e38\u89c1\u5e74\u9650\u53c2\u8003\uff08%s \u8d1f\u8377\uff09\uff1a\u7ea6 %d \u5e74" % (duty, ref))
        if limit >= 0:
            out.append("- \u5224\u5b9a\uff1a**\u5df2\u8d85\u8fc7\u5e38\u89c1\u5e74\u9650\u53c2\u8003\uff0c\u5efa\u8bae\u66f4\u6362**\uff0c"
                       "\u5373\u4f7f\u80ce\u7eb9\u4ecd\u7136\u8f83\u6df1")
        else:
            out.append("- \u5224\u5b9a\uff1a\u5c1a\u672a\u8d85\u8fc7\u5e38\u89c1\u5e74\u9650\u53c2\u8003\uff0c\u4ecd\u9700\u7ed3\u5408\u5b9e\u9645\u78e8\u635f\u72b6\u6001")
        out.append("- \u6ce8\u610f\uff1a\u4e0d\u540c\u54c1\u724c\u7684\u7f16\u7801\u89c4\u5219\u4e0d\u5b8c\u5168\u4e00\u81f4\uff0c"
                   "\u62ff\u4e0d\u51c6\u65f6\u4ee5\u5382\u5bb6\u8bf4\u660e\u4e3a\u51c6")
    except (ValueError, TypeError) as exc:
        out.append("- \u5468\u6570\u7f16\u7801\u65e0\u6cd5\u89e3\u6790\uff1a%s" % exc)
        out.append("- \u8bf7\u786e\u8ba4\u5468\u6570\u5728 01 \u5230 53 \u4e4b\u95f4\u3001\u5e74\u4efd\u53d6\u503c\u5408\u7406")
    out.append("")
    out.append("## \u78e8\u635f\u5224\u65ad")
    out.append("")
    out.append("| \u7ef4\u5ea6 | \u8bfb\u6570 | \u8bf4\u660e |")
    out.append("|---|---|---|")
    out.append("| \u80ce\u7eb9\u6df1\u5ea6 | %.1f \u6beb\u7c73 | %s |" % (depth, depth_hint(depth)))
    out.append("| \u4f7f\u7528\u5e74\u9650 | \u89c1\u4e0a | \u4e0e\u91cc\u7a0b\u5148\u5230\u8005\u4e3a\u51c6 |")
    out.append("| \u78e8\u635f\u5747\u5300\u5ea6 | \u5de6\u53f3\u5dee\u5f02 %.1f \u6beb\u7c73 | %s |" % (
        skew, "\u5dee\u5f02\u660e\u663e" if skew >= SKEW_THRESHOLD else "\u5dee\u5f02\u4e0d\u5927"))
    out.append("")
    out.append("- \u80ce\u7eb9\u6df1\u5ea6\u4e0b\u9650\u4ee5\u73b0\u884c\u89c4\u5b9a\u548c\u8f66\u8f86\u8bf4\u660e\u4e66\u4e3a\u51c6\uff0c\u672c\u811a\u672c\u4e0d\u5199\u6b7b\u6570\u503c")
    out.append("- \u91cc\u7a0b\u4e0e\u5e74\u9650\u4e24\u4e2a\u90fd\u770b\uff0c\u5148\u5230\u8005\u4e3a\u51c6\uff0c\u6700\u7ec8\u770b\u5b9e\u9645\u78e8\u635f\u72b6\u6001")
    out.append("")
    out.append("## \u504f\u78e8\u539f\u56e0\u63d0\u793a")
    out.append("")
    causes = skew_causes(skew)
    if causes:
        out.append("| \u8868\u73b0 | \u5e38\u89c1\u539f\u56e0 |")
        out.append("|---|---|")
        for name, cause in causes:
            out.append("| %s | %s |" % (name, cause))
    else:
        out.append("- \u672a\u63d0\u4f9b\u78e8\u635f\u5dee\u5f02\u6570\u636e\uff0c\u65e0\u6cd5\u5224\u65ad\u662f\u5426\u504f\u78e8")
    out.append("")
    out.append("\u6362\u80ce\u524d\u5148\u627e\u51fa\u504f\u78e8\u7684\u539f\u56e0\uff0c\u80ce\u538b\u6216\u5b9a\u4f4d\u95ee\u9898\u4e0d\u89e3\u51b3\uff0c\u65b0\u80ce\u4f1a\u91cd\u590d\u540c\u6837\u7684\u78e8\u635f\u3002")
    out.append("")
    out.append("## \u5b89\u5168\u7ea2\u7ebf\uff08\u7acb\u5373\u505c\u8f66\uff09")
    out.append("")
    for item in RED_LINES:
        out.append("- %s" % item)
    out.append("")
    out.append("## \u66f4\u6362\u540e\u5fc5\u505a\u9879")
    out.append("")
    for i, step in enumerate(AFTER_STEPS, 1):
        out.append("%d. %s" % (i, step))
    out.append("")
    out.append("## \u8865\u80ce\u4e0e\u5907\u80ce\u8fb9\u754c")
    out.append("")
    out.append("- \u80ce\u9762\u624e\u9489\u5b54\u4e14\u4e0d\u5728\u80ce\u80a9\u80ce\u4fa7\uff0c\u901a\u5e38\u53ef\u8865")
    out.append("- \u80ce\u4fa7\u6216\u80ce\u80a9\u9644\u8fd1\u624e\u4f24\u3001\u5b54\u6d1e\u8f83\u5927\u3001\u591a\u6b21\u4fee\u8865\uff0c\u901a\u5e38\u4e0d\u5efa\u8bae")
    out.append("- \u5e18\u7ebf\u66b4\u9732\u4e0d\u53ef\u8865\uff0c\u5fc5\u987b\u6362")
    out.append("- \u5907\u80ce\u901a\u5e38\u9650\u901f\u4f7f\u7528\uff0c\u4e0d\u9002\u5408\u957f\u8ddd\u79bb\u9ad8\u901f\uff0c\u9650\u901f\u6570\u503c\u770b\u80ce\u58c1\u6807\u6ce8")
    out.append("- \u5907\u80ce\u4f7f\u7528\u540e\u68c0\u67e5\u6c14\u538b\u5e76\u5bf9\u5168\u8f6e\u505a\u52a8\u5e73\u8861\u4e0e\u5b9a\u4f4d")
    out.append("")
    out.append("## \u8fb9\u754c")
    out.append("")
    out.append("- \u672c\u811a\u672c\u53ea\u505a\u7b97\u672f\u4e0e\u89c4\u5219\u5224\u5b9a\uff0c\u4e0d\u4ee3\u8868\u73b0\u573a\u6d4b\u91cf")
    out.append("- \u80ce\u7eb9\u4e0b\u9650\u7b49\u5b89\u5168\u6570\u503c\u4ee5\u73b0\u884c\u89c4\u5b9a\u548c\u8f66\u8f86\u8bf4\u660e\u4e66\u4e3a\u51c6")
    out.append("- \u662f\u5426\u8fd8\u80fd\u7ee7\u7eed\u4f7f\u7528\u3001\u80fd\u5426\u4fee\u8865\u7531\u4e13\u4e1a\u4eba\u5458\u5224\u5b9a")
    return "\n".join(out) + "\n"


def selftest():
    cases = []
    y, m = parse_week_code(1, 2024)
    cases.append(("week1", m == 1))
    y2, m2 = parse_week_code(52, 2023)
    cases.append(("week52", y2 == 2023 and 12 <= m2 <= 12))
    cases.append(("week52_leap", m2 == 12))
    cases.append(("week_bad", _err(parse_week_code, 54, 2024)))
    cases.append(("week_zero", _err(parse_week_code, 0, 2024)))
    cases.append(("year_bad", _err(parse_week_code, 10, 1900)))
    cases.append(("months", months_between(2020, 1, 2022, 1) == 24))
    cases.append(("months_neg", months_between(2024, 6, 2020, 1) < 0))
    cases.append(("depth_high", depth_hint(7.0) == "\u4f59\u91cf\u5145\u8db3"))
    cases.append(("depth_low", depth_hint(0.5) == "\u4f59\u91cf\u6781\u5c11"))
    cases.append(("skew_small", len(skew_causes(0.5)) == 1))
    cases.append(("skew_big", len(skew_causes(4.0)) > 3))
    cases.append(("skew_none", skew_causes(0.0) == []))
    cases.append(("float_str", to_float("2.5", 0.0) == 2.5))
    rep = build_report({"week": 22, "year": 2020, "depth": 3.2, "skew": 4.0,
                        "duty": "\u4e2d"})
    cases.append(("rep_prod", "\u4f30\u7b97\u751f\u4ea7\u5e74\u6708" in rep))
    cases.append(("rep_old", "\u5efa\u8bae\u66f4\u6362" in rep))
    cases.append(("rep_skew", "\u5b9a\u4f4d\u504f\u5dee" in rep))
    cases.append(("rep_red", "\u9f13\u5305" in rep))
    cases.append(("rep_after", "\u505a\u52a8\u5e73\u8861" in rep))
    cases.append(("rep_patch", "\u5e18\u7ebf\u66b4\u9732\u4e0d\u53ef\u8865" in rep))
    rep2 = build_report({"week": 1, "year": date.today().year,
                         "depth": 8.0, "skew": 0.2})
    cases.append(("rep_new", "\u5c1a\u672a\u8d85\u8fc7" in rep2))
    rep3 = build_report({"week": 99})
    cases.append(("rep_bad_code", "\u65e0\u6cd5\u89e3\u6790" in rep3))
    rep4 = build_report({"duty": "\u672a\u77e5", "week": 22, "year": 2024})
    cases.append(("rep_duty_fallback", "\u4e2d" in rep4))
    bom = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_probe.json")
    with open(bom, "w", encoding="utf-8-sig") as f:
        f.write('{"depth": 4.0}')
    try:
        cases.append(("bom_ok", to_float(load_json(bom).get("depth")) == 4.0))
    finally:
        if os.path.exists(bom):
            os.remove(bom)
    lines = []
    for i, (name, ok) in enumerate(cases, 1):
        lines.append("case %02d %-18s %s" % (i, name, "PASS" if ok else "FAIL"))
    bad = [n for n, ok in cases if not ok]
    lines.append("")
    lines.append("SELFTEST %s (%d/%d)" % ("OK" if not bad else "FAILED",
                                         len(cases) - len(bad), len(cases)))
    if bad:
        lines.append("failed: " + ", ".join(bad))
    text = "\n".join(lines) + "\n"
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "_selftest_result.txt"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(text)
    return 0 if not bad else 1


def _err(fn, *a):
    try:
        fn(*a)
    except (ValueError, TypeError):
        return True
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description="tire wear and age audit")
    ap.add_argument("--week", default=None)
    ap.add_argument("--year", default=None)
    ap.add_argument("--depth", default=None)
    ap.add_argument("--skew", default=None)
    ap.add_argument("--duty", default=None)
    ap.add_argument("--file", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--format", default="md")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    data = {}
    if a.file:
        try:
            data = load_json(a.file)
        except Exception as exc:
            print(str(exc))
            return 2
    for key, val in (("week", a.week), ("year", a.year), ("depth", a.depth),
                     ("skew", a.skew), ("duty", a.duty)):
        if val is not None:
            data[key] = val
    report = build_report(data)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "tire_result.md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
