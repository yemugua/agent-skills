# -*- coding: utf-8 -*-
"""Term life insurance coverage gap calculator.

Usage:
  python coverage_calc.py --file household.txt
  python coverage_calc.py --file household.txt --json --out result.json
  python coverage_calc.py --selftest

All money units are 10k CNY (wan). This tool does arithmetic and caliber
checking only. It does not recommend any product and does not compute
premium or return. Source is pure ASCII on purpose.
"""
import argparse
import json
import os
import re
import sys

# ---- level tags (escaped to keep source ASCII) ----
OK = "\u5145\u8db3"
GAP = "\u6709\u7f3a\u53e3"
EXACT = "\u521a\u597d\u8986\u76d6"
NEG = "\u8d1f\u6570"
LOWLINE = "\u504f\u4f4e\u5224\u65ad\u7ebf"
AFFORD = "\u7f34\u8d39\u627f\u53d7\u529b"
RECHECK = "\u9700\u53e3\u5f84\u590d\u6838"

LEVEL_ORDER = {OK: 0, AFFORD: 1, RECHECK: 2, LOWLINE: 3, EXACT: 4, NEG: 5, GAP: 6}

TITLE = "\u5b9a\u671f\u5bff\u9669\u4fdd\u989d\u6d4b\u7b97"
DISCLAIMER = (
    "\u4fdd\u989d\u6d4b\u7b97\u4ec5\u4f9b\u5bb6\u5ead\u98ce\u9669\u7f3a\u53e3\u81ea\u67e5\uff0c"
    "\u5b9e\u9645\u6295\u4fdd\u4ee5\u4fdd\u9669\u516c\u53f8\u6838\u4fdd\u7ed3\u8bba\u4e0e\u5408\u540c\u7ea6\u5b9a\u4e3a\u51c6\u3002"
)

# ---- input keys ----
NUM_KEYS = (
    "debt_mortgage", "debt_car", "debt_other", "annual_expense",
    "support_years", "existing_coverage", "liquid_assets",
    "annual_income", "annual_premium",
)
BOOL_KEYS = (
    "has_mortgage", "supporting_dependent",
    "group_insurance_volatile", "annuity_pure_saving", "housing_counted",
)
DEFAULTS = {
    "debt_mortgage": 0,
    "debt_car": 0,
    "debt_other": 0,
    "annual_expense": 0,
    "support_years": 0,
    "existing_coverage": 0,
    "liquid_assets": 0,
    "annual_income": None,
    "annual_premium": 0,
}

KEY_CN = {
    "debt_mortgage": "\u623f\u8d37\u5269\u4f59\u672c\u91d1",
    "debt_car": "\u8f66\u8d37\u5269\u4f59\u672c\u91d1",
    "debt_other": "\u5176\u4ed6\u8d1f\u503a\u4f59\u989d",
    "annual_expense": "\u5bb6\u5ead\u5e74\u652f\u51fa",
    "support_years": "\u5269\u4f59\u629a\u517b\u5e74\u9650",
    "existing_coverage": "\u5df2\u6709\u5bff\u9669\u4fdd\u989d",
    "liquid_assets": "\u53ef\u53d8\u73b0\u8d44\u4ea7",
    "annual_income": "\u5bb6\u5ead\u5e74\u6536\u5165",
    "annual_premium": "\u5bb6\u5ead\u5e74\u4fdd\u8d39",
}

# caliber reminders that belong to specific input values
HOUSING_WARN = (
    "\u81ea\u4f4f\u623f\u9ed8\u8ba4\u4e0d\u8ba1\u5165\u53ef\u53d8\u73b0\u8d44\u4ea7\u3002"
    "\u82e5\u786e\u8ba4\u8ba1\u5165\uff0c\u9700\u540c\u65f6\u8ba1\u5165\u642c\u5bb6\u4e0e\u8fc7\u6e21\u79df\u623f\u6210\u672c\u3002"
)
CAR_WARN = (
    "\u79c1\u5bb6\u8f66\u9ed8\u8ba4\u4e0d\u8ba1\u5165\u53ef\u53d8\u73b0\u8d44\u4ea7\uff0c"
    "\u5b83\u662f\u6d88\u8d39\u8d44\u4ea7\u4e14\u6298\u4ef7\u5feb\u3002"
)
YEARS_WARN = (
    "\u5269\u4f59\u629a\u517b\u5e74\u9650\u5e94\u7b97\u5230\u5b69\u5b50\u7ecf\u6d4e\u72ec\u7acb\uff0822-25 \u5c81\uff09\uff0c"
    "\u7b97\u5230\u4e0a\u5e7c\u513f\u56ed\u56e0\u6b64\u4f1a\u5927\u5e45\u4f4e\u4f30\u7f3a\u53e3\u3002"
)
MORTGAGE_WARN = (
    "\u623f\u8d37\u5fc5\u987b\u7528\u5f53\u524d\u5269\u4f59\u672c\u91d1\uff0c\u4e0d\u662f\u539f\u8d37\u6b3e\u603b\u989d\u3002"
)
GROUPPOL_WARN = (
    "\u5355\u4f4d\u56e2\u9669\u7684\u8eab\u6545\u8d23\u4efb\u901a\u5e38\u5728\u79bb\u804c\u540e\u5931\u6548\uff0c"
    "\u82e5\u4f1a\u79bb\u804c\u5219\u5e94\u6263\u9664\u8be5\u90e8\u5206\u3002"
)
ANNUITY_WARN = (
    "\u7eaf\u751f\u5b58\u9886\u53d6\u578b\u5e74\u91d1\u9669\u6ca1\u6709\u72ec\u7acb\u8eab\u6545\u4fdd\u989d\uff0c"
    "\u4e0d\u5f97\u6309\u73b0\u91d1\u4ef7\u503c\u62b5\u6263\u5bff\u9669\u7f3a\u53e3\u3002"
)
NEG_WARN = (
    "\u8d1f\u6570\u662f\u590d\u6838\u4fe1\u53f7\uff0c\u4e0d\u662f\u7ed3\u8bba\u3002"
    "\u9010\u9879\u590d\u6838\u5df2\u6709\u4fdd\u989d\u6784\u6210\u3001\u56e2\u9669\u662f\u5426\u79bb\u804c\u5931\u6548\u3001"
    "\u8d44\u4ea7\u662f\u5426\u771f\u80fd\u53d8\u73b0\u3002"
)
GAP_WARN = (
    "\u7f3a\u53e3\u662f\u9700\u8981\u7684\u4fdd\u969c\u91d1\u989d\uff0c\u4e0d\u7b49\u4e8e\u5e94\u5f53\u4e70\u7684\u4fdd\u989d\uff0c"
    "\u7ed3\u5408\u7f34\u8d39\u627f\u53d7\u529b\u4e0e\u6838\u4fdd\u53ef\u884c\u6027\u518d\u5224\u65ad\u3002"
)
ZERO_COVER_WARN = (
    "\u5df2\u6709\u4fdd\u989d\u4e3a\u96f6\u8868\u793a\u5c1a\u65e0\u4efb\u4f55\u8eab\u6545\u4fdd\u969c\uff0c"
    "\u4f46\u4e5f\u53ef\u80fd\u662f\u5df2\u6709\u4fdd\u989d\u672a\u7eb3\u5165\u5f55\u5165\u3002"
)

# low-coverage judgment lines: (label, threshold_expr_key)
LOW_LINE_KEYS = ("debt_only", "one_year", "half_period", "full_period")
LOW_LINE_CN = {
    "debt_only": "\u4fdd\u989d < \u8d1f\u503a\u4f59\u989d",
    "one_year": "\u4fdd\u989d < \u5bb6\u5ead\u5e74\u652f\u51fa",
    "half_period": "\u4fdd\u989d < \u5e74\u652f\u51fa \u00d7 \u5e74\u9650 \u00d7 50%%",
    "full_period": "\u4fdd\u989d < \u5e74\u652f\u51fa \u00d7 \u5e74\u9650",
}
LOW_LINE_NOTE = {
    "debt_only": "\u8fde\u503a\u52a1\u90fd\u8986\u76d6\u4e0d\u4e86\uff0c\u6536\u5165\u4e2d\u65ad\u5373\u65ad\u4f9b",
    "one_year": "\u8fde\u4e00\u5e74\u5f00\u9500\u90fd\u8986\u76d6\u4e0d\u4e86",
    "half_period": "\u53ea\u80fd\u8986\u76d6\u4e00\u534a\u629a\u517b\u671f\u5f00\u9500",
    "full_period": "\u672a\u8986\u76d6\u5168\u671f\u629a\u517b\u6210\u672c\uff0c\u5c5e\u4e34\u754c",
}

MANUAL = (
    "\u6295\u4fdd\u5bf9\u8c61\u662f\u5bb6\u5ead\u7ecf\u6d4e\u652f\u67f1\u5417\uff08\u4e0d\u662f\u5b69\u5b50\u6216\u8001\u4eba\uff09",
    "\u623f\u8d37\u7528\u7684\u662f\u5269\u4f59\u672c\u91d1\u800c\u4e0d\u662f\u539f\u8d37\u6b3e\u603b\u989d",
    "\u5bb6\u5ead\u5e74\u652f\u51fa\u662f\u8fd1 12 \u4e2a\u6708\u5e73\u5747\uff0c\u4e14\u542b\u6559\u80b2\u4e0e\u8d61\u517b",
    "\u5269\u4f59\u629a\u517b\u5e74\u9650\u7b97\u5230\u5b69\u5b50\u7ecf\u6d4e\u72ec\u7acb\uff0c\u4e0d\u662f\u4e0a\u5e7c\u513f\u56ed",
    "\u5df2\u6709\u4fdd\u989d\u662f\u5426\u9010\u5f20\u6838\u5bf9\uff0c\u4e14\u53ea\u8ba1\u8eab\u6545\u8d23\u4efb",
    "\u91cd\u75be\u9669\u3001\u533b\u7597\u9669\u3001\u610f\u5916\u9669\u672a\u88ab\u8bef\u5f53\u4f5c\u5bff\u9669\u4fdd\u989d",
    "\u5355\u4f4d\u56e2\u9669\u662f\u5426\u79bb\u804c\u540e\u5931\u6548",
    "\u53ef\u53d8\u73b0\u8d44\u4ea7\u672a\u542b\u81ea\u4f4f\u623f\u4e0e\u8f66",
    "\u7ed3\u679c\u4e3a\u8d1f\u6570\u65f6\u5df2\u590d\u6838\u5168\u90e8\u4e94\u9879\u53e3\u5f84",
    "\u52a0\u8fd9\u7b14\u4fdd\u8d39\u540e\u5bb6\u5ead\u5e74\u5ea6\u7ed3\u4f59\u4ecd\u4e3a\u6b63",
    "\u5bb6\u5ead\u662f\u5426\u6709\u65e2\u5f80\u75c5\u53f2\u6216\u4f53\u68c0\u5f02\u5e38\uff08\u5f71\u54cd\u6838\u4fdd\u800c\u975e\u6d4b\u7b97\uff09",
    "\u7ed3\u8bba\u662f\u5426\u5df2\u660e\u786e\u544a\u77e5\u6d4b\u7b97\u4ec5\u4f9b\u81ea\u67e5\u3001\u6295\u4fdd\u4ee5\u6838\u4fdd\u7ed3\u8bba\u4e0e\u5408\u540c\u7ea6\u5b9a\u4e3a\u51c6",
)


def to_num(v):
    """Parse a money/number value; returns None when not parseable."""
    s = (v or "").strip()
    if not s:
        return None
    s = s.replace(",", "").replace("\uff0c", "").replace(" ", "")
    s = re.sub(r"[\u4e07\u5143]", "", s)
    m = re.match(r"^-?\d+(\.\d+)?$", s)
    if not m:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def to_bool(v):
    s = (v or "").strip().lower()
    if s in ("1", "true", "yes", "y", "on"):
        return True
    if s in ("0", "false", "no", "n", "off"):
        return False
    return None


def parse(text):
    """Parse key|value or key=value lines into a dict."""
    got = {}
    if not text:
        return got
    # strip a UTF-8 BOM so the first key is still recognised
    if text.startswith("\ufeff"):
        text = text[1:]
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            k, _, v = line.partition("|")
        elif "=" in line:
            k, _, v = line.partition("=")
        else:
            continue
        k = k.strip().lower()
        v = v.strip()
        if not k or not v:
            continue
        if k in BOOL_KEYS:
            got[k] = to_bool(v)
        elif k in NUM_KEYS:
            got[k] = to_num(v)
        else:
            got[k] = v
    return got


def d(dic, key):
    """Merged value: defaults <- parsed <- explicit zero allowed."""
    if key in dic and dic[key] is not None:
        return dic[key]
    return DEFAULTS.get(key, 0)


def worst(levels):
    return max(levels, key=lambda x: LEVEL_ORDER.get(x, 0)) if levels else OK


def compute(dic):
    """Run the coverage formula and the caliber checks."""
    mortgage = d(dic, "debt_mortgage")
    car = d(dic, "debt_car")
    other = d(dic, "debt_other")
    expense = d(dic, "annual_expense")
    years = d(dic, "support_years")
    existing = d(dic, "existing_coverage")
    liquid = d(dic, "liquid_assets")
    income = d(dic, "annual_income")
    premium = d(dic, "annual_premium")

    debt_total = mortgage + car + other
    period_need = expense * years
    demand = debt_total + period_need
    after_existing = demand - existing
    gap = after_existing - liquid

    # ---- caliber / direction rows ----
    rows = []

    if gap > 0:
        rows.append(("gap_dir", GAP,
                     "\u7f3a\u53e3 %.0f \u4e07\u5143" % gap))
    elif gap == 0:
        rows.append(("gap_dir", EXACT,
                     "\u7406\u8bba\u4e0a\u521a\u597d\u8986\u76d6\uff0c\u5efa\u8bae\u7559\u4f59\u91cf"))
    else:
        rows.append(("gap_dir", NEG,
                     "\u7ed3\u679c\u4e3a\u8d1f %.0f\uff0c\u4e0d\u7b49\u4e8e\u9700\u8981\u589e\u52a0\u4fdd\u989d" % gap))

    if gap < 0:
        rows.append(("gap_recheck", RECHECK, NEG_WARN))

    # ---- low coverage judgment lines ----
    gap_pos = max(gap, 0.0)
    thresholds = {
        "debt_only": debt_total,
        "one_year": expense,
        "half_period": period_need * 0.5,
        "full_period": period_need,
    }
    low_hits = []
    for key in LOW_LINE_KEYS:
        th = thresholds[key]
        if th <= 0:
            continue
        if gap_pos < th:
            low_hits.append(key)
    if low_hits:
        note = "; ".join(
            "%s\uff08%s\uff09" % (LOW_LINE_CN[k], LOW_LINE_NOTE[k]) for k in low_hits
        )
        rows.append(("low_line", LOWLINE, note))
    else:
        rows.append(("low_line", OK,
                     "\u4fdd\u989d\u8986\u76d6\u4e86\u8d1f\u503a\u4e0e\u5168\u671f\u629a\u517b\u671f\u5f00\u9500"))

    if existing <= 0:
        rows.append(("zero_cover", RECHECK, ZERO_COVER_WARN))

    # ---- caliber reminders ----
    if mortgage > 0:
        rows.append(("mortgage", OK, MORTGAGE_WARN))
    if years > 0 and years < 15:
        rows.append(("years", RECHECK, YEARS_WARN))
    if dic.get("housing_counted") is True:
        rows.append(("housing", RECHECK, HOUSING_WARN))
    if dic.get("group_insurance_volatile") is True:
        rows.append(("group_pol", RECHECK, GROUPPOL_WARN))
    if dic.get("annuity_pure_saving") is True:
        rows.append(("annuity", RECHECK, ANNUITY_WARN))
    if car > 0:
        rows.append(("car", OK, CAR_WARN))

    # ---- affordability gate ----
    if income is not None:
        balance = income - expense - premium
        if balance < 0:
            rows.append(("afford", GAP,
                         "\u52a0\u4fdd\u8d39\u540e\u5bb6\u5ead\u5e74\u7ed3\u4f59 %.0f\uff0c"
                         "\u4e0d\u53ef\u627f\u53d7\uff0c\u6709\u4e2d\u9014\u65ad\u7f34\u98ce\u9669" % balance))
        elif balance == 0:
            rows.append(("afford", RECHECK,
                         "\u52a0\u4fdd\u8d39\u540e\u5bb6\u5ead\u5e74\u7ed3\u4f59\u4e3a\u96f6\uff0c\u65e0\u7f13\u51b2\uff0c"
                         "\u5e94\u5148\u8865\u5e94\u6025\u50a8\u5907"))
        else:
            rows.append(("afford", OK,
                         "\u52a0\u4fdd\u8d39\u540e\u5bb6\u5ead\u5e74\u7ed3\u4f59 %.0f" % balance))
    else:
        rows.append(("afford", AFFORD,
                     "\u672a\u5f55\u5165\u5bb6\u5ead\u5e74\u6536\u5165\uff0c"
                     "\u65e0\u6cd5\u5224\u65ad\u7f34\u8d39\u627f\u53d7\u529b\uff0c\u8fd9\u662f\u7b2c\u4e8c\u9053\u95f8"))

    if gap > 0:
        rows.append(("gap_note", GAP, GAP_WARN))

    rows.sort(key=lambda r: LEVEL_ORDER.get(r[1], 0))
    overall = worst([r[1] for r in rows])

    return {
        "gap": gap,
        "overall": overall,
        "debt_total": debt_total,
        "period_need": period_need,
        "demand": demand,
        "after_existing": after_existing,
        "gap_pos": gap_pos,
        "low_hits": low_hits,
        "rows": [{"name": n, "level": lv, "note": nt} for n, lv, nt in rows],
        "input": {
            "debt_mortgage": mortgage, "debt_car": car, "debt_other": other,
            "annual_expense": expense, "support_years": years,
            "existing_coverage": existing, "liquid_assets": liquid,
            "annual_income": income, "annual_premium": premium,
        },
    }


def render_md(r):
    i = r["input"]
    L = []
    L.append("# %s" % TITLE)
    L.append("")
    L.append("## \u4e00 \u6d4b\u7b97\u53c2\u6570\uff08\u5355\u4f4d\uff1a\u4e07\u5143\uff09")
    L.append("")
    L.append("| \u9879 | \u6570\u503c |")
    L.append("|---|---|")
    for k in NUM_KEYS:
        val = i.get(k)
        if val is None:
            continue
        L.append("| %s | %s |" % (KEY_CN[k], ("%.0f" % val)))
    L.append("")
    L.append("## \u4e8c \u9010\u6b65\u4ee3\u5165")
    L.append("")
    L.append("```")
    L.append("\u4fdd\u989d = \u8d1f\u503a\u4f59\u989d + \u5bb6\u5ead\u5e74\u652f\u51fa \u00d7 \u5269\u4f59\u629a\u517b\u5e74\u9650"
             " \u2212 \u5df2\u6709\u5bff\u9669\u4fdd\u989d \u2212 \u53ef\u53d8\u73b0\u8d44\u4ea7")
    L.append("     = (%.0f + %.0f + %.0f) + %.0f \u00d7 %.0f \u2212 %.0f \u2212 %.0f"
             % (i["debt_mortgage"], i["debt_car"], i["debt_other"],
                i["annual_expense"], i["support_years"],
                i["existing_coverage"], i["liquid_assets"]))
    L.append("     = %.0f + %.0f \u2212 %.0f \u2212 %.0f"
             % (r["debt_total"], r["period_need"],
                i["existing_coverage"], i["liquid_assets"]))
    L.append("     = %.0f" % r["gap"])
    L.append("```")
    L.append("")
    L.append("## \u4e09 \u5224\u5b9a")
    L.append("")
    L.append("| \u9879 | \u7ed3\u8bba |")
    L.append("|---|---|")
    for it in r["rows"]:
        L.append("| %s | %s |" % (it["name"], it["note"]))
    L.append("")
    L.append("\u6574\u4f53\u7ed3\u8bba\uff1a**%s**" % r["overall"])
    L.append("")
    L.append("## \u56db \u5fc5\u987b\u4eba\u5de5\u786e\u8ba4")
    L.append("")
    for t in MANUAL:
        L.append("- [ ] %s" % t)
    L.append("")
    L.append("---")
    L.append("")
    L.append("> %s" % DISCLAIMER)
    return "\n".join(L) + "\n"


SAMPLE_DUAL = """debt_mortgage|180
debt_car|8
debt_other|0
annual_expense|30
support_years|18
existing_coverage|0
liquid_assets|60
"""

SAMPLE_SINGLE = """debt_mortgage|260
debt_car|0
debt_other|0
annual_expense|24
support_years|21
existing_coverage|50
liquid_assets|40
"""

SAMPLE_NEG = """debt_mortgage|0
annual_expense|36
support_years|15
existing_coverage|300
liquid_assets|480
"""

SAMPLE_SMALL = """debt_mortgage|0
annual_expense|14
support_years|8
existing_coverage|0
liquid_assets|90
"""

SAMPLE_AFFORD = """debt_mortgage|180
annual_expense|30
support_years|18
liquid_assets|60
annual_income|45
annual_premium|8
"""

SAMPLE_JUNK = """\u8fd9\u884c\u6ca1\u6709\u5206\u9694\u7b26
unknown_key|1
debt_mortgage|abc
has_mortgage|
"""

SAMPLE_EMPTY = "# \u53ea\u6709\u6ce8\u91ca\n"

SAMPLE_BADFLAGS = """annual_expense|20
support_years|5
group_insurance_volatile|1
annuity_pure_saving|1
housing_counted|1
"""


def selftest():
    res = []
    ok = True

    def ck(name, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        res.append("%s %s got=%r want=%r"
                   % ("PASS" if good else "FAIL", name, got, want))

    # ---- parsing ----
    p = parse(SAMPLE_DUAL)
    ck("parse_mortgage", p.get("debt_mortgage"), 180.0)
    ck("parse_years", p.get("support_years"), 18.0)
    ck("parse_pipe_and_eq", parse("annual_expense=25").get("annual_expense"), 25.0)
    ck("parse_comma", parse("annual_expense|1,200").get("annual_expense"), 1200.0)
    ck("parse_wan", parse("annual_expense|30\u4e07").get("annual_expense"), 30.0)
    ck("parse_bool", parse("has_mortgage|1").get("has_mortgage"), True)
    ck("parse_bool_no", parse("has_mortgage|no").get("has_mortgage"), False)
    ck("parse_junk_unknown", parse(SAMPLE_JUNK).get("unknown_key"), "1")
    ck("parse_junk_num", parse(SAMPLE_JUNK).get("debt_mortgage"), None)
    ck("parse_junk_empty", parse(SAMPLE_JUNK).get("has_mortgage"), None)
    ck("parse_empty", parse(SAMPLE_EMPTY), {})
    ck("parse_bom", parse("\ufeffdebt_mortgage|180").get("debt_mortgage"), 180.0)
    ck("parse_none", parse(None), {})
    ck("to_num_bad", to_num("abc"), None)
    ck("to_bool_bad", to_bool("maybe"), None)
    ck("d_zero_kept", d({"annual_expense": 0}, "annual_expense"), 0.0)
    ck("d_default", d({}, "liquid_assets"), 0.0)

    # ---- formula ----
    r1 = compute(parse(SAMPLE_DUAL))
    ck("dual_gap", r1["gap"], 668.0)
    ck("dual_debt", r1["debt_total"], 188.0)
    ck("dual_period", r1["period_need"], 540.0)
    ck("dual_demand", r1["demand"], 728.0)
    ck("dual_dir", r1["overall"], GAP)
    j1 = " ".join(it["note"] for it in r1["rows"])
    ck("dual_mortgage_note", "\u5269\u4f59\u672c\u91d1" in j1, True)

    r2 = compute(parse(SAMPLE_SINGLE))
    ck("single_gap", r2["gap"], 674.0)
    ck("single_debt", r2["debt_total"], 260.0)

    r3 = compute(parse(SAMPLE_NEG))
    ck("neg_gap", r3["gap"], -240.0)
    ck("neg_overall", r3["overall"], NEG)
    ck("neg_recheck", "gap_recheck" in [it["name"] for it in r3["rows"]], True)
    ck("neg_warn", NEG_WARN in " ".join(it["note"] for it in r3["rows"]), True)

    r4 = compute(parse(SAMPLE_SMALL))
    ck("small_gap", r4["gap"], 22.0)
    ck("small_dir", [it["level"] for it in r4["rows"]
                     if it["name"] == "gap_dir"][0], GAP)
    ck("small_low_hits", sorted(r4["low_hits"]),
       sorted(["half_period", "full_period"]))

    # ---- zero coverage warning ----
    j4 = " ".join(it["note"] for it in r4["rows"])
    ck("zero_cover_flag", "zero_cover" in [it["name"] for it in r4["rows"]], True)
    ck("zero_cover_text", ZERO_COVER_WARN in j4, True)

    # ---- affordability gate ----
    r5 = compute(parse(SAMPLE_AFFORD))
    ck("afford_ok", [it["level"] for it in r5["rows"]
                     if it["name"] == "afford"][0], OK)
    r6 = compute({"annual_expense": 30, "annual_income": 35, "annual_premium": 8})
    ck("afford_neg", [it["level"] for it in r6["rows"]
                      if it["name"] == "afford"][0], GAP)
    ck("afford_zero", [it["level"] for it in compute(
        {"annual_expense": 30, "annual_income": 30, "annual_premium": 0})["rows"]
        if it["name"] == "afford"][0], RECHECK)
    ck("afford_missing", [it["level"] for it in compute({"annual_expense": 20})["rows"]
                          if it["name"] == "afford"][0], AFFORD)

    # ---- low coverage lines ----
    r7 = compute({"debt_mortgage": 100, "annual_expense": 30, "support_years": 20,
                  "existing_coverage": 690})
    ck("low_all_hits", sorted(r7["low_hits"]),
       sorted(["debt_only", "one_year", "half_period", "full_period"]))
    ck("low_all_gap", r7["gap"], 10.0)
    r8 = compute({"debt_mortgage": 100, "annual_expense": 10, "support_years": 10,
                  "liquid_assets": 0})
    ck("low_none", r8["low_hits"], [])
    ck("low_ok_level", [it["level"] for it in r8["rows"]
                        if it["name"] == "low_line"][0], OK)

    # ---- caliber reminders ----
    r9 = compute(parse(SAMPLE_BADFLAGS))
    names = [it["name"] for it in r9["rows"]]
    ck("remind_years", "years" in names, True)
    ck("remind_group", "group_pol" in names, True)
    ck("remind_annuity", "annuity" in names, True)
    ck("remind_housing", "housing" in names, True)
    j9 = " ".join(it["note"] for it in r9["rows"])
    ck("remind_group_text", GROUPPOL_WARN in j9, True)
    ck("remind_annuity_text", ANNUITY_WARN in j9, True)

    # ---- empty input ----
    r10 = compute(parse(SAMPLE_EMPTY))
    ck("empty_gap", r10["gap"], 0.0)
    ck("empty_dir", [it["level"] for it in r10["rows"]
                     if it["name"] == "gap_dir"][0], EXACT)
    ck("empty_overall", r10["overall"], EXACT)

    # ---- render ----
    md = render_md(r1)
    ck("md_head", md.startswith("# "), True)
    ck("md_params", "\u6d4b\u7b97\u53c2\u6570" in md, True)
    ck("md_steps", "\u9010\u6b65\u4ee3\u5165" in md, True)
    ck("md_judge", "\u5224\u5b9a" in md, True)
    ck("md_manual", "\u5fc5\u987b\u4eba\u5de5\u786e\u8ba4" in md, True)
    ck("md_disclaimer", DISCLAIMER in md, True)
    js = json.loads(json.dumps(r1, ensure_ascii=False))
    ck("json_gap", js["gap"], 668.0)
    ck("json_keys", sorted(js.keys()),
       ["after_existing", "debt_total", "demand", "gap", "gap_pos",
        "input", "low_hits", "overall", "period_need", "rows"])

    # ---- constants ----
    ck("worst_fn", worst([OK, GAP, LOWLINE]), GAP)
    ck("worst_neg_wins", worst([OK, NEG]), NEG)
    ck("level_order", LEVEL_ORDER[GAP] > LEVEL_ORDER[RECHECK], True)
    ck("manual_len", len(MANUAL) >= 10, True)
    ck("low_keys_len", len(LOW_LINE_KEYS) >= 4, True)
    ck("source_ascii", all(ord(c) < 128 for c in open(__file__, encoding="utf-8").read()),
       True)

    for line in res:
        print(line)
    print("SELFTEST %s (%d assertions)" % ("OK" if ok else "FAILED", len(res)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        rc = selftest()
        outp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "_selftest_result.txt")
        with open(outp, "w", encoding="utf-8") as f:
            f.write("SELFTEST %s\nresult: %s\n"
                    % ("OK" if rc == 0 else "FAILED", "OK" if rc == 0 else "FAILED"))
        return rc

    if not a.file or not os.path.exists(a.file):
        print("ERROR --file does not exist")
        return 2

    with open(a.file, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    r = compute(parse(text))
    body = (json.dumps(r, ensure_ascii=False, indent=2) if a.json
            else render_md(r))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(body)
        print("WROTE %s" % a.out)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())