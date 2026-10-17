# -*- coding: utf-8 -*-
"""\u62a4\u7167\u9996\u6b21\u7533\u9886\u4e0e\u6362\u53d1\u8865\u53d1\u6838\u67e5\u3002

\u7528\u6cd5:
  python passport_material_check.py --selftest
  python passport_material_check.py --file \u60c5\u51b5.txt --category \u6362\u53d1 --as-of 2026-10-08
  python passport_material_check.py --file \u60c5\u51b5.txt --expiry 2027-03-01 --out \u7ed3\u679c.md
"""
import argparse
import datetime
import io
import json
import os
import re
import sys

FAILS = []

CATEGORIES = ("\u9996\u6b21\u7533\u9886", "\u6362\u53d1", "\u8865\u53d1")

# \u60c5\u5f62\u5224\u5b9a\u5173\u952e\u8bcd\uff08\u8865\u53d1 > \u6362\u53d1 > \u9996\u6b21\u7533\u9886\uff09
LOST_PAT = r"(\u4e22\u5931|\u9057\u5931|\u4e22\u4e86|\u88ab\u76d7|\u88ab\u5077|\u5077\u4e86|\u627e\u4e0d\u5230|\u5f04\u4e22)"
RENEW_PAT = r"(\u8fc7\u671f|\u5230\u671f|\u6362\u53d1|\u6362\u65b0|\u6362\u8bc1|\u6709\u6548\u671f(?:\u5c4a\u6ee1|\u4e0d\u8db3)|\u7b7e\u8bc1\u9875(?:\u7528\u5b8c|\u7528\u5c3d)|\u7834\u635f|\u635f\u574f|\u6495\u574f)"
FIRST_PAT = r"(\u9996\u6b21|\u7b2c\u4e00\u6b21|\u6ca1\u529e\u8fc7|\u672a\u66fe(?:\u6301\u6709|\u529e\u7406)|\u521d\u6b21\u7533\u9886|\u4ece\u6765\u6ca1\u6709)"

# \u6750\u6599\u8868\uff1a(\u540d\u79f0, \u6b63\u5219, \u9002\u7528\u60c5\u5f62, \u89e6\u53d1\u6761\u4ef6)
# \u89e6\u53d1\u6761\u4ef6\u4e3a None \u8868\u793a\u6309\u9002\u7528\u60c5\u5f62\u5224\u5b9a\uff1b\u5426\u5219\u4ec5\u5728\u547d\u4e2d\u8be5\u7279\u6b8a\u60c5\u5f62\u65f6\u624d\u8981\u6c42\u63d0\u4ea4
MATERIAL_PATTERNS = [
    ("\u5c45\u6c11\u8eab\u4efd\u8bc1", r"(\u8eab\u4efd\u8bc1|\u5c45\u6c11\u8eab\u4efd\u8bc1|\u4e34\u65f6\u8eab\u4efd\u8bc1)", ("\u9996\u6b21\u7533\u9886", "\u6362\u53d1", "\u8865\u53d1"), None),
    ("\u6237\u53e3\u7c3f", r"(\u6237\u53e3\u7c3f|\u6237\u53e3\u672c|\u6237\u7c4d(?:\u8bc1\u660e|\u6750\u6599)|\u96c6\u4f53\u6237\u53e3)", ("\u9996\u6b21\u7533\u9886", "\u6362\u53d1", "\u8865\u53d1"), None),
    ("\u7167\u7247\u53ca\u56de\u6267", r"(\u7167\u7247|\u514d\u51a0|\u7167\u7247\u56de\u6267|\u76f8\u7247|\u8bc1\u4ef6\u7167|\u62cd\u7167|\u91c7\u96c6)", ("\u9996\u6b21\u7533\u9886", "\u6362\u53d1", "\u8865\u53d1"), None),
    ("\u7533\u8bf7\u8868", r"(\u7533\u8bf7\u8868|\u7533\u9886\u8868|\u586b\u5199\u8868|\u9884\u586b|\u7f51\u4e0a\u9884\u586b)", ("\u9996\u6b21\u7533\u9886", "\u6362\u53d1", "\u8865\u53d1"), None),
    ("\u539f\u62a4\u7167", r"(\u539f\u62a4\u7167|\u65e7\u62a4\u7167|\u73b0\u6301\u62a4\u7167|\u62a4\u7167\u539f\u4ef6|\u4ea4\u56de\u539f\u8bc1|\u6b8b\u635f\u8bc1\u4ef6)", ("\u6362\u53d1",), None),
    ("\u5355\u4f4d\u5ba1\u6279\u610f\u89c1", r"(\u5355\u4f4d(?:\u5ba1\u6279|\u540c\u610f|\u610f\u89c1|\u76d6\u7ae0)|\u7ec4\u7ec7\u4eba\u4e8b\u90e8\u95e8\u5ba1\u6279|\u5df2\u53d6\u5f97\u5355\u4f4d)",
     ("\u9996\u6b21\u7533\u9886", "\u6362\u53d1", "\u8865\u53d1"), "\u767b\u8bb0\u5907\u6848\u4eba\u5458"),
    ("\u76d1\u62a4\u5173\u7cfb\u8bc1\u660e", r"(\u76d1\u62a4(?:\u4eba|\u5173\u7cfb)|\u51fa\u751f\u533b\u5b66\u8bc1\u660e|\u76d1\u62a4\u4eba\u966a\u540c)",
     ("\u9996\u6b21\u7533\u9886", "\u6362\u53d1", "\u8865\u53d1"), "\u672a\u6210\u5e74\u4eba"),
    ("\u5c45\u4f4f\u8bc1\u660e\u6750\u6599", r"(\u5c45\u4f4f\u8bc1|\u5c45\u4f4f\u8bc1\u660e|\u5c45\u4f4f\u767b\u8bb0|\u6682\u4f4f\u8bc1)",
     ("\u9996\u6b21\u7533\u9886", "\u6362\u53d1", "\u8865\u53d1"), "\u5f02\u5730\u529e\u7406"),
]

SPECIAL_FLAGS = [
    ("\u767b\u8bb0\u5907\u6848\u4eba\u5458", r"(\u767b\u8bb0\u5907\u6848|\u5907\u6848\u4eba\u5458|\u516c\u52a1\u5458|\u56fd\u5bb6\u673a\u5173|\u56fd\u6709\u4f01\u4e1a|\u4e8b\u4e1a\u5355\u4f4d|\u7ec4\u7ec7\u4eba\u4e8b\u90e8\u95e8)"),
    ("\u672a\u6210\u5e74\u4eba", r"(\u672a\u6210\u5e74|\u672a\u6ee1\s*\d+\s*\u5468\u5c81|\u5c0f\u5b69|\u5b69\u5b50|\u5b50\u5973)"),
    ("\u5f02\u5730\u529e\u7406", r"(\u5f02\u5730|\u975e\u6237\u7c4d\u5730|\u5916\u7701|\u5916\u5e02|\u8de8\u7701|\u5c45\u4f4f\u5730\u529e\u7406|\u6682\u4f4f\u5730)"),
    ("\u52a0\u6025\u9700\u6c42", r"(\u52a0\u6025|\u7740\u6025|\u7d27\u6025|\u5954\u4e27|\u63a2\u75c5|\u5f00\u5b66|\u4e34\u8fd1\u51fa\u53d1|\u9a6c\u4e0a\u8981\u98de)"),
]

RISK_PATTERNS = [
    ("\u8eab\u4efd\u6750\u6599\u5b58\u7591", r"(\u8eab\u4efd\u4e0d\u660e|\u65e0\u6cd5\u8bc1\u660e\u8eab\u4efd|\u8eab\u4efd\u5b58\u7591|\u6237\u7c4d\u4e0d\u4e00\u81f4|\u59d3\u540d\u4e0d\u4e00\u81f4)"),
    ("\u6750\u6599\u771f\u5b9e\u6027\u98ce\u9669", r"(\u4f2a\u9020|\u53d8\u9020|\u5047\u6750\u6599|\u5f04\u865a\u4f5c\u5047|\u865a\u5047\u6750\u6599|PS|\u4fee\u56fe)"),
    ("\u9650\u5236\u51fa\u5883\u98ce\u9669", r"(\u9650\u5236\u51fa\u5883|\u4e0d\u51c6\u51fa\u5883|\u670d\u5211|\u672a\u4e86\u7ed3|\u6c11\u4e8b\u6848\u4ef6|\u88ab\u6267\u884c|\u8fb9\u63a7)"),
    ("\u56fd\u7c4d\u5b58\u7591", r"(\u5916\u56fd\u56fd\u7c4d|\u53cc\u91cd\u56fd\u7c4d|\u5df2\u5165\u5916\u7c4d|\u5b9a\u5c45\u56fd\u5916|\u5916\u56fd\u62a4\u7167)"),
]

NEGATIVE_WATCH = [
    (r"\u672a\u63d0\u4ea4\u5355\u4f4d\u5ba1\u6279\u610f\u89c1", "\u300c\u672a\u63d0\u4ea4\u5355\u4f4d\u5ba1\u6279\u610f\u89c1\u300d\u4e0d\u7b49\u4e8e\u300c\u5df2\u83b7\u5355\u4f4d\u540c\u610f\u300d"),
    (r"\u4e0d\u4e88\u53d7\u7406", "\u300c\u4e0d\u4e88\u53d7\u7406\u300d\u4e0d\u7b49\u4e8e\u300c\u6682\u7f13\u529e\u7406\u300d"),
    (r"\u4e0d\u4e88\u7b7e\u53d1", "\u300c\u4e0d\u4e88\u7b7e\u53d1\u300d\u4e0d\u7b49\u4e8e\u300c\u5c1a\u672a\u7b7e\u53d1\u300d"),
    (r"\u539f\u62a4\u7167\u4f5c\u5e9f", "\u300c\u539f\u62a4\u7167\u4f5c\u5e9f\u300d\u4e0d\u7b49\u4e8e\u300c\u539f\u62a4\u7167\u4ecd\u53ef\u4f7f\u7528\u300d"),
    (r"\u7167\u7247\u4e0d\u5408\u683c", "\u300c\u7167\u7247\u4e0d\u5408\u683c\u300d\u4e0d\u7b49\u4e8e\u300c\u7167\u7247\u5f85\u5ba1\u6838\u300d"),
]

DATE_RE = re.compile(r"(\d{4})[-/.\u5e74](\d{1,2})[-/.\u6708](\d{1,2})")


def ck(label, cond):
    if not cond:
        FAILS.append(label)
    return bool(cond)


def write_result(path):
    lines = ["SELFTEST %s" % ("OK" if not FAILS else "FAILED")]
    for f in FAILS:
        lines.append("  FAILED: %s" % f)
    io.open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))


def parse_date(text):
    if not text:
        return None
    s = str(text).strip()
    m = DATE_RE.search(s)
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def detect_category(text, override=None):
    if override:
        for c in CATEGORIES:
            if override in c or c in override:
                return c, "\u53c2\u6570\u6307\u5b9a"
        return override, "\u53c2\u6570\u6307\u5b9a"
    if re.search(LOST_PAT, text):
        return "\u8865\u53d1", "\u6587\u672c\u547d\u4e2d\u9057\u5931/\u88ab\u76d7"
    if re.search(RENEW_PAT, text):
        return "\u6362\u53d1", "\u6587\u672c\u547d\u4e2d\u65ad\u53d1\u4e8b\u7531"
    if re.search(FIRST_PAT, text):
        return "\u9996\u6b21\u7533\u9886", "\u6587\u672c\u547d\u4e2d\u9996\u6b21\u7533\u9886"
    return "\u672a\u5224\u5b9a", "\u6587\u672c\u672a\u547d\u4e2d\uff0c\u9700\u4eba\u5de5\u786e\u8ba4"


def check_materials(text, category, flags):
    rows = []
    for name, pat, applies, cond in MATERIAL_PATTERNS:
        hit = re.search(pat, text) is not None
        if cond is not None and cond not in flags:
            rows.append({"\u6750\u6599": name, "\u72b6\u6001": "\u4e0d\u6d89\u53ca", "\u547d\u4e2d": hit})
            continue
        if category in applies:
            rows.append({"\u6750\u6599": name, "\u72b6\u6001": ("\u9f50\u5907" if hit else "\u7f3a\u5931"), "\u547d\u4e2d": hit})
        else:
            rows.append({"\u6750\u6599": name, "\u72b6\u6001": "\u4e0d\u6d89\u53ca", "\u547d\u4e2d": hit})
    return rows


def special_flags(text):
    out = []
    for name, pat in SPECIAL_FLAGS:
        if re.search(pat, text):
            out.append(name)
    return out


def risk_scan(text):
    out = []
    for name, pat in RISK_PATTERNS:
        if re.search(pat, text):
            out.append(name)
    return out


def negative_watch(text):
    out = []
    for pat, tip in NEGATIVE_WATCH:
        if re.search(pat, text):
            out.append(tip)
    return out


def expiry_advice(expiry, as_of):
    """\u6309\u5269\u4f59\u6709\u6548\u671f\u7ed9\u51fa\u6362\u53d1\u7a97\u53e3\u5efa\u8bae\u3002"""
    if expiry is None or as_of is None:
        return None
    days = (expiry - as_of).days
    if days < 0:
        level, advice = "\u5df2\u8fc7\u671f", "\u62a4\u7167\u5df2\u8fc7\u671f\uff0c\u53ea\u80fd\u8d70\u6362\u53d1\uff0c\u4e0d\u80fd\u518d\u7528\u4e8e\u51fa\u5883"
    elif days <= 180:
        level, advice = "\u4e0d\u8db3\u516d\u4e2a\u6708", "\u5efa\u8bae\u5c3d\u5feb\u6362\u53d1\uff0c\u5e76\u6838\u5bf9\u76ee\u7684\u5730\u56fd\u4e0e\u822a\u7a7a\u516c\u53f8\u7684\u6709\u6548\u671f\u8981\u6c42"
    elif days <= 365:
        level, advice = "\u516d\u81f3\u5341\u4e8c\u4e2a\u6708", "\u5173\u6ce8\u6709\u6548\u671f\uff0c\u591a\u6570\u76ee\u7684\u5730\u8981\u6c42\u5165\u5883\u65f6\u6709\u6548\u671f\u8d85\u8fc7\u516d\u4e2a\u6708"
    else:
        level, advice = "\u5145\u8db3", "\u6b63\u5e38\u4f7f\u7528\uff0c\u6309\u51fa\u884c\u8ba1\u5212\u63d0\u524d\u6392\u671f\u5373\u53ef"
    return {"\u5269\u4f59\u5929\u6570": days, "\u533a\u95f4": level, "\u5efa\u8bae": advice,
            "\u6709\u6548\u671f\u622a\u6b62": expiry.isoformat(), "\u57fa\u51c6\u65e5": as_of.isoformat()}


def build_report(text, category_arg, as_of_str, expiry_str):
    as_of = parse_date(as_of_str) or datetime.date.today()
    expiry = parse_date(expiry_str)
    category, why = detect_category(text, category_arg)
    flags = special_flags(text)
    materials = check_materials(text, category, flags)
    risks = risk_scan(text)
    negs = negative_watch(text)
    exp = expiry_advice(expiry, as_of)

    lines = []
    lines.append("=" * 62)
    lines.append("\u62a4\u7167\u7533\u9886\u4e0e\u6362\u53d1\u8865\u53d1\u6838\u67e5\u62a5\u544a")
    lines.append("=" * 62)
    lines.append("")
    lines.append("[\u529e\u7406\u60c5\u5f62] %s  \uff08\u4f9d\u636e\uff1a%s\uff09" % (category, why))
    if category == "\u672a\u5224\u5b9a":
        lines.append("  [\u63d0\u793a] \u60c5\u5f62\u672a\u5224\u5b9a\u524d\u4e0d\u8981\u6309\u63a8\u6d4b\u5907\u6750\u6599\uff0c\u5148\u5411\u51fa\u5165\u5883\u7ba1\u7406\u90e8\u95e8\u786e\u8ba4")
    lines.append("")
    lines.append("[\u6750\u6599\u6e05\u5355\u6838\u67e5]")
    for r in materials:
        lines.append("  %-8s %s" % (r["\u6750\u6599"], r["\u72b6\u6001"]))
    missing = [r["\u6750\u6599"] for r in materials if r["\u72b6\u6001"] == "\u7f3a\u5931"]
    lines.append("  \u7f3a\u5931\u9879\uff1a%s" % ("\u3001".join(missing) if missing else "\u65e0"))
    lines.append("")
    lines.append("[\u7279\u6b8a\u60c5\u5f62] %s" % ("\u3001".join(flags) if flags else "\u672a\u547d\u4e2d"))
    if "\u767b\u8bb0\u5907\u6848\u4eba\u5458" in flags:
        lines.append("  [\u7ea2\u7ebf] \u767b\u8bb0\u5907\u6848\u4eba\u5458\u987b\u5148\u53d6\u5f97\u5355\u4f4d\u5ba1\u6279\u610f\u89c1\uff0c\u4e0d\u5f97\u4ee5\u4efb\u4f55\u65b9\u5f0f\u89c4\u907f")
    if "\u672a\u6210\u5e74\u4eba" in flags:
        lines.append("  [\u63d0\u793a] \u672a\u6210\u5e74\u4eba\u987b\u7531\u76d1\u62a4\u4eba\u966a\u540c\u5e76\u63d0\u4ea4\u76d1\u62a4\u5173\u7cfb\u8bc1\u660e\u6750\u6599")
    if "\u5f02\u5730\u529e\u7406" in flags:
        lines.append("  [\u63d0\u793a] \u5f02\u5730\u529e\u7406\u6761\u4ef6\u4e0e\u6750\u6599\u4ee5\u62df\u529e\u7406\u5730\u51fa\u5165\u5883\u7ba1\u7406\u90e8\u95e8\u7b54\u590d\u4e3a\u51c6")
    lines.append("")
    lines.append("[\u6709\u6548\u671f]")
    if exp:
        lines.append("  \u6709\u6548\u671f\u622a\u6b62 %s\uff0c\u57fa\u51c6\u65e5 %s\uff0c\u5269\u4f59 %d \u5929\uff08%s\uff09" % (
            exp["\u6709\u6548\u671f\u622a\u6b62"], exp["\u57fa\u51c6\u65e5"], exp["\u5269\u4f59\u5929\u6570"], exp["\u533a\u95f4"]))
        lines.append("  \u5efa\u8bae\uff1a%s" % exp["\u5efa\u8bae"])
    else:
        lines.append("  \u672a\u63d0\u4f9b --expiry\uff0c\u8df3\u8fc7\u6709\u6548\u671f\u6362\u7b97")
    lines.append("")
    lines.append("[\u4e0d\u4e88\u7b7e\u53d1\u98ce\u9669] %s" % ("\u3001".join(risks) if risks else "\u672a\u547d\u4e2d"))
    if risks:
        lines.append("  [\u63d0\u793a] \u547d\u4e2d\u98ce\u9669\u9879\u5e94\u5148\u5411\u51fa\u5165\u5883\u7ba1\u7406\u90e8\u95e8\u95ee\u6e05\u5177\u4f53\u4f9d\u636e\uff0c\u4e0d\u8981\u53cd\u590d\u91cd\u590d\u63d0\u4ea4")
    lines.append("")
    if negs:
        lines.append("[\u5426\u5b9a\u8bcd\u63d0\u9192]")
        for n in negs:
            lines.append("  - %s" % n)
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u811a\u672c\u53ea\u505a\u5173\u952e\u8bcd\u5339\u914d\uff0c\u4e0d\u4ee3\u8868\u53d7\u7406\u7ed3\u8bba\u3002")
    lines.append("      \u6750\u6599\u3001\u65f6\u9650\u3001\u5f02\u5730\u529e\u7406\u53e3\u5f84\u4ee5\u73b0\u884c\u89c4\u5b9a\u548c\u5f53\u5730\u51fa\u5165\u5883\u7ba1\u7406\u90e8\u95e8\u8981\u6c42\u4e3a\u51c6\u3002")
    lines.append("=" * 62)

    summary = {"\u529e\u7406\u60c5\u5f62": category, "\u5224\u5b9a\u4f9d\u636e": why,
               "\u6750\u6599": materials, "\u7f3a\u5931\u9879": missing,
               "\u7279\u6b8a\u60c5\u5f62": flags, "\u98ce\u9669": risks,
               "\u5426\u5b9a\u8bcd\u63d0\u9192": negs, "\u6709\u6548\u671f": exp}
    return "\n".join(lines), summary


SAMPLE = """\u6211\u7b2c\u4e00\u6b21\u529e\u62a4\u7167\uff0c\u8eab\u4efd\u8bc1\u548c\u6237\u53e3\u7c3f\u90fd\u5e26\u4e0a\u4e86\uff0c\u7167\u7247\u51c6\u5907\u53bb\u73b0\u573a\u62cd\uff0c\u7533\u8bf7\u8868\u5df2\u7ecf\u7f51\u4e0a\u9884\u586b\u597d\u4e86\u3002
\u6211\u5728\u5916\u7701\u5de5\u4f5c\uff0c\u6709\u5c45\u4f4f\u8bc1\uff0c\u60f3\u5f02\u5730\u529e\u7406\u3002"""


def selftest():
    ck("\u5e94\u628a\u56db\u6bb5\u65e5\u671f\u89e3\u6790\u4e3a date", parse_date("2027-03-01") == datetime.date(2027, 3, 1))
    ck("\u4e2d\u6587\u65e5\u671f\u4e5f\u5e94\u80fd\u89e3\u6790", parse_date("2026\u5e7410\u67088\u65e5") == datetime.date(2026, 10, 8))
    ck("\u7a7a\u503c\u5e94\u8fd4\u56de None", parse_date("") is None)

    c1, _ = detect_category("\u62a4\u7167\u4e22\u4e86\u600e\u4e48\u529e")
    ck("\u4e22\u4e86\u5e94\u5224\u4e3a\u8865\u53d1", c1 == "\u8865\u53d1")
    c2, _ = detect_category("\u62a4\u7167\u5feb\u5230\u671f\u4e86\u60f3\u6362\u4e00\u672c")
    ck("\u5230\u671f\u5e94\u5224\u4e3a\u6362\u53d1", c2 == "\u6362\u53d1")
    c3, _ = detect_category("\u6211\u7b2c\u4e00\u6b21\u529e\u62a4\u7167")
    ck("\u7b2c\u4e00\u6b21\u5e94\u5224\u4e3a\u9996\u6b21\u7533\u9886", c3 == "\u9996\u6b21\u7533\u9886")
    c4, _ = detect_category("\u60f3\u54a8\u8be2\u4e00\u4e0b\u62a4\u7167")
    ck("\u65e0\u5173\u952e\u8bcd\u5e94\u5224\u4e3a\u672a\u5224\u5b9a", c4 == "\u672a\u5224\u5b9a")
    c5, _ = detect_category("\u62a4\u7167\u4e22\u4e86\u800c\u4e14\u65e9\u5c31\u8fc7\u671f\u4e86")
    ck("\u540c\u65f6\u547d\u4e2d\u9057\u5931\u4e0e\u8fc7\u671f\u5e94\u6309\u8865\u53d1\u4f18\u5148", c5 == "\u8865\u53d1")
    c6, _ = detect_category("\u968f\u4fbf\u5199\u70b9\u4ec0\u4e48", override="\u6362\u53d1")
    ck("\u53c2\u6570\u6307\u5b9a\u5e94\u4f18\u5148\u751f\u6548", c6 == "\u6362\u53d1")

    ms = check_materials("\u5e26\u4e86\u8eab\u4efd\u8bc1\u3001\u6237\u53e3\u7c3f\uff0c\u7167\u7247\u73b0\u573a\u91c7\u96c6\uff0c\u5df2\u9884\u586b\u7533\u8bf7\u8868", "\u9996\u6b21\u7533\u9886", [])
    d = dict((m["\u6750\u6599"], m["\u72b6\u6001"]) for m in ms)
    ck("\u8eab\u4efd\u8bc1\u5e94\u5224\u9f50\u5907", d["\u5c45\u6c11\u8eab\u4efd\u8bc1"] == "\u9f50\u5907")
    ck("\u6237\u53e3\u7c3f\u5e94\u5224\u9f50\u5907", d["\u6237\u53e3\u7c3f"] == "\u9f50\u5907")
    ck("\u7167\u7247\u5e94\u5224\u9f50\u5907", d["\u7167\u7247\u53ca\u56de\u6267"] == "\u9f50\u5907")
    ck("\u9996\u6b21\u7533\u9886\u65f6\u539f\u62a4\u7167\u5e94\u4e0d\u6d89\u53ca", d["\u539f\u62a4\u7167"] == "\u4e0d\u6d89\u53ca")
    ck("\u975e\u5907\u6848\u4eba\u5458\u65f6\u5355\u4f4d\u5ba1\u6279\u610f\u89c1\u5e94\u4e0d\u6d89\u53ca", d["\u5355\u4f4d\u5ba1\u6279\u610f\u89c1"] == "\u4e0d\u6d89\u53ca")

    ms2 = check_materials("\u5e26\u4e86\u8eab\u4efd\u8bc1\u3001\u6237\u53e3\u7c3f\u3001\u7167\u7247\u3001\u7533\u8bf7\u8868\u3001\u539f\u62a4\u7167\u3001\u5355\u4f4d\u5ba1\u6279\u610f\u89c1", "\u6362\u53d1", ["\u767b\u8bb0\u5907\u6848\u4eba\u5458"])
    d2 = dict((m["\u6750\u6599"], m["\u72b6\u6001"]) for m in ms2)
    ck("\u6362\u53d1\u65f6\u539f\u62a4\u7167\u9700\u4ea4\u56de\u4e14\u5224\u9f50\u5907", d2["\u539f\u62a4\u7167"] == "\u9f50\u5907")
    ck("\u5907\u6848\u4eba\u5458\u53d6\u5f97\u610f\u89c1\u5e94\u5224\u9f50\u5907", d2["\u5355\u4f4d\u5ba1\u6279\u610f\u89c1"] == "\u9f50\u5907")

    ms3 = check_materials("\u5e26\u4e86\u8eab\u4efd\u8bc1\uff0c\u5b69\u5b50\u672a\u6ee110\u5468\u5c81", "\u9996\u6b21\u7533\u9886", ["\u672a\u6210\u5e74\u4eba"])
    d3 = dict((m["\u6750\u6599"], m["\u72b6\u6001"]) for m in ms3)
    ck("\u672a\u6210\u5e74\u4eba\u7f3a\u76d1\u62a4\u5173\u7cfb\u8bc1\u660e\u5e94\u5224\u7f3a\u5931", d3["\u76d1\u62a4\u5173\u7cfb\u8bc1\u660e"] == "\u7f3a\u5931")
    ck("\u7a7a\u6587\u672c\u65f6\u8eab\u4efd\u8bc1\u5e94\u5224\u7f3a\u5931",
       dict((m["\u6750\u6599"], m["\u72b6\u6001"]) for m in check_materials("", "\u6362\u53d1", []))["\u5c45\u6c11\u8eab\u4efd\u8bc1"] == "\u7f3a\u5931")

    f = special_flags("\u6211\u662f\u4e8b\u4e1a\u5355\u4f4d\u7684\u767b\u8bb0\u5907\u6848\u4eba\u5458\uff0c\u5b69\u5b50\u672a\u6ee110\u5468\u5c81\uff0c\u5728\u5916\u7701\u5f02\u5730\u529e\u7406\uff0c\u7740\u6025\u52a0\u6025")
    ck("\u5e94\u547d\u4e2d\u767b\u8bb0\u5907\u6848\u4eba\u5458", "\u767b\u8bb0\u5907\u6848\u4eba\u5458" in f)
    ck("\u5e94\u547d\u4e2d\u672a\u6210\u5e74\u4eba", "\u672a\u6210\u5e74\u4eba" in f)
    ck("\u5e94\u547d\u4e2d\u5f02\u5730\u529e\u7406", "\u5f02\u5730\u529e\u7406" in f)
    ck("\u5e94\u547d\u4e2d\u52a0\u6025\u9700\u6c42", "\u52a0\u6025\u9700\u6c42" in f)
    ck("\u666e\u901a\u6587\u672c\u4e0d\u5e94\u547d\u4e2d\u7279\u6b8a\u60c5\u5f62", special_flags("\u60f3\u529e\u62a4\u7167") == [])

    r = risk_scan("\u4e4b\u524d\u88ab\u9650\u5236\u51fa\u5883\uff0c\u8fd8\u6709\u672a\u4e86\u7ed3\u7684\u6c11\u4e8b\u6848\u4ef6")
    ck("\u5e94\u547d\u4e2d\u9650\u5236\u51fa\u5883\u98ce\u9669", "\u9650\u5236\u51fa\u5883\u98ce\u9669" in r)
    ck("\u5e94\u626b\u63cf\u51fa\u6750\u6599\u771f\u5b9e\u6027\u98ce\u9669", "\u6750\u6599\u771f\u5b9e\u6027\u98ce\u9669" in risk_scan("\u60f3\u7528\u5047\u6750\u6599\u529e"))

    e1 = expiry_advice(datetime.date(2027, 3, 1), datetime.date(2027, 1, 1))
    ck("\u5269\u4f59\u4e0d\u8db3\u516d\u4e2a\u6708\u5e94\u7ed9\u51fa\u5efa\u8bae\u6362\u53d1", e1["\u533a\u95f4"] == "\u4e0d\u8db3\u516d\u4e2a\u6708")
    e2 = expiry_advice(datetime.date(2026, 1, 1), datetime.date(2026, 10, 8))
    ck("\u5df2\u8fc7\u671f\u5e94\u5224\u4e3a\u5df2\u8fc7\u671f", e2["\u533a\u95f4"] == "\u5df2\u8fc7\u671f")
    e3 = expiry_advice(datetime.date(2029, 1, 1), datetime.date(2026, 10, 8))
    ck("\u6709\u6548\u671f\u5145\u8db3\u5e94\u5224\u4e3a\u5145\u8db3", e3["\u533a\u95f4"] == "\u5145\u8db3")
    ck("\u5269\u4f59\u5929\u6570\u5e94\u6b63\u786e",
       e3["\u5269\u4f59\u5929\u6570"] == (datetime.date(2029, 1, 1) - datetime.date(2026, 10, 8)).days)
    ck("\u672a\u63d0\u4f9b\u6709\u6548\u671f\u65f6\u5e94\u8fd4\u56de None", expiry_advice(None, datetime.date(2026, 10, 8)) is None)

    n = negative_watch("\u7a97\u53e3\u8bf4\u4e0d\u4e88\u53d7\u7406\uff0c\u539f\u62a4\u7167\u4f5c\u5e9f\uff0c\u7167\u7247\u4e0d\u5408\u683c")
    ck("\u5e94\u7ed9\u51fa\u4e09\u6761\u5426\u5b9a\u8bcd\u63d0\u9192", len(n) == 3)

    rep, sm = build_report(SAMPLE, None, "2026-10-08", "2027-03-01")
    ck("\u62a5\u544a\u5e94\u542b\u6807\u9898", "\u62a4\u7167\u7533\u9886\u4e0e\u6362\u53d1\u8865\u53d1\u6838\u67e5\u62a5\u544a" in rep)
    ck("\u6837\u4f8b\u5e94\u5224\u4e3a\u9996\u6b21\u7533\u9886", sm["\u529e\u7406\u60c5\u5f62"] == "\u9996\u6b21\u7533\u9886")
    ck("\u6837\u4f8b\u5e94\u547d\u4e2d\u5f02\u5730\u529e\u7406", "\u5f02\u5730\u529e\u7406" in sm["\u7279\u6b8a\u60c5\u5f62"])
    ck("\u6837\u4f8b\u6709\u6548\u671f\u5e94\u4e0d\u8db3\u516d\u4e2a\u6708", sm["\u6709\u6548\u671f"]["\u533a\u95f4"] == "\u4e0d\u8db3\u516d\u4e2a\u6708")
    ck("\u6837\u4f8b\u4e0d\u5e94\u6709\u7f3a\u5931\u7684\u5fc5\u4ea4\u6750\u6599", len(sm["\u7f3a\u5931\u9879"]) == 0)
    return not FAILS


def main():
    ap = argparse.ArgumentParser(description="\u62a4\u7167\u9996\u6b21\u7533\u9886\u4e0e\u6362\u53d1\u8865\u53d1\u6838\u67e5")
    ap.add_argument("--file", help="\u5f85\u6838\u67e5\u6587\u672c\uff1a\u60c5\u51b5\u8bf4\u660e\u3001\u6750\u6599\u6e05\u5355\u6216\u804a\u5929\u8bb0\u5f55\u5bfc\u51fa\uff08.txt/.md\uff09")
    ap.add_argument("--text", help="\u76f4\u63a5\u7ed9\u4e00\u6bb5\u60c5\u51b5\u63cf\u8ff0")
    ap.add_argument("--category", default=None, help="\u529e\u7406\u60c5\u5f62\uff1a\u9996\u6b21 / \u6362\u53d1 / \u8865\u53d1")
    ap.add_argument("--as-of", default=None, help="\u6838\u67e5\u57fa\u51c6\u65e5\uff0c\u5982 2026-10-08")
    ap.add_argument("--expiry", default=None, help="\u73b0\u6301\u62a4\u7167\u6709\u6548\u671f\u622a\u6b62\u65e5\uff0c\u7528\u4e8e\u7b97\u6362\u53d1\u7a97\u53e3")
    ap.add_argument("--out", help="\u7ed3\u679c\u5199\u5165\u6587\u4ef6")
    ap.add_argument("--format", default="md", choices=["md", "json"])
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    if args.selftest:
        ok = selftest()
        write_result(os.path.join(here, "_selftest_result.txt"))
        sys.exit(0 if ok else 1)

    if args.file:
        text = io.open(args.file, "r", encoding="utf-8", errors="ignore").read()
    elif args.text:
        text = args.text
    else:
        ap.error("\u9700\u8981 --file\u3001--text \u6216 --selftest")

    report, summary = build_report(text, args.category, args.as_of, args.expiry)
    out_path = args.out or os.path.join(here, "_last_result.txt")
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.format == "json" else report
    io.open(out_path, "w", encoding="utf-8").write(body)
    print(body)
    print("")
    print("\u7ed3\u679c\u5df2\u5199\u5165: %s" % out_path)


if __name__ == "__main__":
    main()
