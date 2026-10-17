# -*- coding: utf-8 -*-
"""\u90bb\u91cc\u7ea0\u7eb7\u53d6\u8bc1\u4e0e\u5904\u7f6e\u8def\u5f84\u6838\u67e5\u3002

\u7528\u6cd5:
  python neighbor_dispute_check.py --file \u6848\u60c5.txt --occurrence-date 2025-03-12 --as-of 2026-10-08
  python neighbor_dispute_check.py --selftest
"""
import argparse
import datetime
import json
import os
import re
import sys

# ---- \u56db\u7c7b\u5e38\u89c1\u7ea0\u7eb7\u53ca\u5176\u8981\u4ef6\u5173\u952e\u8bcd ----
DISPUTE_TYPES = [
    ("\u6f0f\u6c34\u6e17\u6f0f", "\u6f0f\u6c34|\u6e17\u6f0f|\u6e17\u6c34|\u6ce1\u6c34|\u4e0b\u6c34\u7ba1|\u8fd4\u6c34|\u9632\u6c34\u5c42|\u623f\u9876|\u6f0f\u6c34\u70b9|\u540a\u9876"),
    ("\u566a\u97f3\u6270\u6c11", "\u566a\u97f3|\u566a\u58f0|\u5435|\u97f3\u54cd|\u88c5\u4fee\u58f0|\u591c\u91cc|\u5348\u4f11|\u9707\u697c|\u8e66|\u5f39\u594f|\u5531\u6b4c|\u7a7a\u8c03\u5916\u673a"),
    ("\u8fdd\u5efa\u52a0\u5efa", "\u8fdd\u5efa|\u8fdd\u6cd5\u5efa\u8bbe|\u52a0\u5efa|\u642d\u68da|\u5c01\u9633\u53f0|\u9633\u5149\u623f|\u5360\u7528|\u6269\u5efa|\u52a0\u76d6|\u62c6\u627f\u91cd\u5899"),
    ("\u91c7\u5149\u901a\u98ce\u901a\u884c", "\u91c7\u5149|\u906e\u9633|\u6321\u5149|\u901a\u98ce|\u901a\u9053|\u51fa\u8def|\u901a\u884c|\u8ddd\u79bb|\u65e5\u7167|\u95f4\u9694"),
]

# ---- \u901a\u7528\u8bc1\u636e\u6e05\u5355\uff08\u6309\u7c7b\u578b\u5206\u522b\u8981\u6c42\u7684\u5199\u5728 rules \u91cc\uff0c\u8fd9\u91cc\u505a\u8986\u76d6\u9762\u6838\u67e5\uff09----
EVIDENCE = [
    ("\u73b0\u573a\u7167\u7247/\u89c6\u9891\uff08\u542b\u65f6\u95f4\u6c34\u5370\uff09", "\u7167\u7247|\u89c6\u9891|\u5f55\u50cf|\u62cd\u6444|\u5f71\u50cf|\u8bb0\u5f55\u89c6\u9891"),
    ("\u7269\u4e1a\u6216\u793e\u533a\u5728\u573a\u8bb0\u5f55", "\u7269\u4e1a|\u7269\u4e1a\u7ba1\u7406|\u524d\u53f0|\u4fdd\u5b89|\u5c45\u59d4|\u793e\u533a|\u7f51\u683c\u5458|\u53f0\u8d26"),
    ("\u62a5\u8b66\u6216\u516c\u5b89\u673a\u5173\u5904\u7f6e\u8bb0\u5f55", "\u62a5\u8b66|110|\u6d3e\u51fa\u6240|\u51fa\u8b66|\u7b14\u5f55|\u516c\u5b89\u673a\u5173"),
    ("\u4e13\u4e1a\u9274\u5b9a\u610f\u89c1\uff08\u6f0f\u6c34\u70b9/\u566a\u97f3\u503c/\u65e5\u7167\uff09", "\u9274\u5b9a|\u68c0\u6d4b\u62a5\u544a|\u9274\u5b9a\u610f\u89c1|\u7b2c\u4e09\u65b9|\u8bc4\u4f30|\u6d4b\u91cf\u7ed3\u679c|\u5206\u8d1d"),
    ("\u7ef4\u4fee\u62a5\u4ef7\u6216\u53d1\u7968", "\u62a5\u4ef7|\u53d1\u7968|\u6536\u636e|\u7ef4\u4fee\u8d39|\u6e05\u5355|\u82b1\u8d39|\u652f\u51fa|\u7968\u636e"),
    ("\u6743\u5c5e\u6216\u623f\u5c4b\u5173\u7cfb\u8bc1\u660e", "\u623f\u4ea7\u8bc1|\u4e0d\u52a8\u4ea7\u6743|\u4ea7\u6743|\u4e1a\u4e3b|\u79df\u623f\u5408\u540c|\u627f\u79df"),
    ("\u6c9f\u901a\u8bb0\u5f55\uff08\u5fae\u4fe1/\u77ed\u4fe1/\u5f55\u97f3\uff09", "\u5fae\u4fe1|\u77ed\u4fe1|\u804a\u5929\u8bb0\u5f55|\u5f55\u97f3|\u901a\u8bdd|\u6c9f\u901a\u8bb0\u5f55"),
    ("\u635f\u5931\u6e05\u5355\u4e0e\u4fee\u590d\u524d\u7167\u7247", "\u635f\u5931|\u6e05\u5355|\u53d7\u635f|\u539f\u72b6|\u8d2d\u4e70\u51ed\u8bc1|\u8f6c\u8d26\u8bb0\u5f55"),
]

# ---- \u5404\u7c7b\u578b\u5fc5\u5907\u8981\u4ef6 ----
REQUIRED = {
    "\u6f0f\u6c34\u6e17\u6f0f": [
        ("\u6f0f\u6c34\u70b9\u6216\u6f0f\u6c34\u539f\u56e0", "\u6f0f\u6c34\u70b9|\u6f0f\u6c34\u539f\u56e0|\u6e17\u6f0f\u539f\u56e0|\u9632\u6c34\u5c42\u8001\u5316|\u7ba1\u9053\u7834\u88c2"),
        ("\u635f\u5931\u8303\u56f4\u4e0e\u91d1\u989d", "\u635f\u5931|\u62a5\u4ef7|\u7ef4\u4fee\u8d39|\u91d1\u989d|\u5143|\u53d1\u7968"),
        ("\u4e0e\u697c\u4e0a\u6216\u76f8\u90bb\u65b9\u7684\u5173\u7cfb", "\u697c\u4e0a|\u697c\u4e0b|\u90bb\u5c45|\u4e1a\u4e3b|\u76f8\u90bb"),
    ],
    "\u566a\u97f3\u6270\u6c11": [
        ("\u566a\u58f0\u53d1\u751f\u7684\u5177\u4f53\u65f6\u6bb5", "\u591c\u91cc|\u591c\u95f4|\u5348\u4f11|\u51e0\u70b9|\u65f6\u6bb5|\u665a\u4e0a|\u51cc\u6668"),
        ("\u6301\u7eed\u65f6\u95f4\u4e0e\u9891\u6b21", "\u6bcf\u5929|\u6301\u7eed|\u7ecf\u5e38|\u6570\u6708|\u9891\u6b21|\u5929\u5929|\u6bcf\u5468"),
        ("\u5e72\u6270\u7a0b\u5ea6\u7684\u5ba2\u89c2\u4f50\u8bc1", "\u5206\u8d1d|\u68c0\u6d4b|\u6d4b\u91cf\u7ed3\u679c|\u62a5\u8b66|\u7269\u4e1a\u7ba1\u7406|\u7b2c\u4e09\u65b9|\u5f55\u50cf"),
    ],
    "\u8fdd\u5efa\u52a0\u5efa": [
        ("\u5efa\u8bbe\u884c\u4e3a\u7684\u5177\u4f53\u4f4d\u7f6e\u4e0e\u5f62\u6001", "\u52a0\u5efa|\u642d\u5efa|\u5c01\u9633\u53f0|\u9633\u5149\u623f|\u4f4d\u7f6e|\u5c42"),
        ("\u5ba1\u6279\u624b\u7eed\u6709\u65e0", "\u5ba1\u6279|\u624b\u7eed|\u89c4\u5212\u8bb8\u53ef|\u6ca1\u6709\u4efb\u4f55|\u672a\u6279"),
        ("\u4e3b\u7ba1\u90e8\u95e8\u67e5\u5904\u8fdb\u5c55", "\u57ce\u5e02\u7ba1\u7406|\u57ce\u7ba1|\u7efc\u5408\u6267\u6cd5|\u81ea\u7136\u8d44\u6e90|\u53cd\u6620|\u7acb\u6848|\u67e5\u5904"),
    ],
    "\u91c7\u5149\u901a\u98ce\u901a\u884c": [
        ("\u906e\u6321\u4e8b\u5b9e\u4e0e\u5efa\u6210\u65f6\u95f4\u5148\u540e", "\u906e|\u6321\u5149|\u65e5\u7167|\u5e74\u52a0\u5efa|\u5efa\u6210"),
        ("\u5b9e\u9645\u5f71\u54cd\u7a0b\u5ea6", "\u6652\u4e0d\u5230|\u5f71\u54cd|\u901a\u98ce|\u91c7\u5149"),
        ("\u89c4\u5212\u4e0e\u95f4\u8ddd\u8981\u6c42", "\u89c4\u5212|\u6838\u5b9e\u610f\u89c1|\u95f4\u8ddd|\u8ddd\u79bb|\u65e5\u7167\u6807\u51c6"),
    ],
}

# ---- \u53d6\u8bc1\u624b\u6bb5\u5408\u6cd5\u6027\u7ea2\u7ebf ----
ILLEGAL_METHODS = [
    ("\u79c1\u81ea\u5728\u4ed6\u4eba\u4f4f\u5b85\u95e8\u53e3\u957f\u671f\u53cc\u5411\u5f55\u97f3\u4fa6\u67e5", "\u7a83\u542c|\u76d1\u542c\u5668|\u5077\u542c|\u5077\u5f55\u8bbe\u5907"),
    ("\u5bf9\u51c6\u4ed6\u4eba\u79c1\u5bc6\u7a7a\u95f4\u7684\u6444\u50cf\u5934", "\u6444\u50cf\u5934\u5bf9\u51c6|\u62cd\u5367\u623f|\u5bf9\u7740\u4ed6\u5bb6|\u76d1\u63a7\u90bb\u5c45|\u88c5\u4e2a\u6444\u50cf\u5934|\u6444\u50cf\u5934\u76d1\u63a7|\u5077\u62cd"),
    ("\u64c5\u81ea\u64ac\u9501\u3001\u7834\u5899\u3001\u8fdb\u5165\u90bb\u5c45\u5bb6\u4e2d", "\u64ac\u9501|\u7834\u95e8|\u8e39\u95e8|\u7ffb\u7a97|\u79c1\u95ef|\u64c5\u81ea\u8fdb\u5165"),
    ("\u64c5\u81ea\u4e2d\u65ad\u6c34\u7535\u3001\u5835\u9501\u773c\u7b49\u62a5\u590d\u624b\u6bb5", "\u65ad\u6c34|\u65ad\u7535|\u5835\u9501\u773c|\u9501\u773c\u5835\u4e0a|\u6cfc\u6cb9\u6f06|\u9707\u697c\u5668"),
    ("\u7f51\u7edc\u66dd\u5149\u9690\u79c1\u4e2a\u4eba\u4fe1\u606f", "\u66dd\u5149\u4e2a\u4eba\u4fe1\u606f|\u4e2a\u4eba\u4fe1\u606f\u66dd\u5149|\u8d34\u5427|\u7fa4\u91cc\u9a82|\u4eba\u8089|\u66dd\u5149\u51fa\u6765"),
]

# ---- \u635f\u5bb3\u8d54\u507f\u8bc9\u8bbc\u65f6\u6548 ----
LIMIT_YEARS = 3


def norm(s):
    return (s or "").replace(" ", "").replace("\u3000", "")


def add_years(d, n):
    try:
        return datetime.date(d.year + n, d.month, d.day)
    except ValueError:
        return datetime.date(d.year + n, d.month, d.day - 1)


def parse_date(s):
    if not s:
        return None
    m = re.search(r"(20\d{2})[\-\./](\d{1,2})[\-\./](\d{1,2})", s)
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def pick_types(text):
    t = norm(text)
    return [n for n, p in DISPUTE_TYPES if re.search(p, t)]


def check_evidence(text):
    t = norm(text)
    return [(n, "\u6709" if re.search(p, t) else "\u672a\u89c1") for n, p in EVIDENCE]


def check_required(text, types):
    t = norm(text)
    out = []
    for ty in types:
        for item, pat in REQUIRED.get(ty, []):
            out.append((ty, item, "\u5df2\u8986\u76d6" if re.search(pat, t) else "\u5f85\u8865"))
    return out


def check_methods(text):
    t = norm(text)
    return [n for n, p in ILLEGAL_METHODS if re.search(p, t)]


def path_advice(types, has_report, has_police, has_property):
    lines = []
    for ty in types:
        if ty == "\u566a\u97f3\u6270\u6c11":
            who = "\u516c\u5b89\u673a\u5173\uff08\u793e\u4f1a\u751f\u6d3b\u566a\u58f0\uff09\u6216\u751f\u6001\u73af\u5883\u4e3b\u7ba1\u90e8\u95e8\uff08\u5de5\u4e1a\u3001\u5efa\u7b51\u65bd\u5de5\u566a\u58f0\uff09"
        elif ty == "\u8fdd\u5efa\u52a0\u5efa":
            who = "\u57ce\u5e02\u7ba1\u7406\u7efc\u5408\u884c\u653f\u6267\u6cd5\u90e8\u95e8\u3001\u81ea\u7136\u8d44\u6e90\u4e3b\u7ba1\u90e8\u95e8"
        elif ty == "\u91c7\u5149\u901a\u98ce\u901a\u884c":
            who = "\u81ea\u7136\u8d44\u6e90\u4e3b\u7ba1\u90e8\u95e8\uff1b\u5c5e\u8fdd\u6cd5\u5efa\u8bbe\u7684\u540c\u6b65\u8d70\u8fdd\u5efa\u67e5\u5904"
        else:
            who = "\u7269\u4e1a\u534f\u8c03\u4e3a\u4e3b\uff0c\u8bc9\u8bbc\u4e3a\u8f85"
        lines.append((ty, who))
    return lines


def limitation(occ, as_of):
    if occ is None:
        return None
    due = add_years(occ, LIMIT_YEARS)
    remain = (due - as_of).days
    past = max(0, (as_of - occ).days)
    return occ, due, remain, past


def render_md(text, as_of, occ=None):
    lines = ["# \u90bb\u91cc\u7ea0\u7eb7\u53d6\u8bc1\u4e0e\u5904\u7f6e\u8def\u5f84\u6838\u67e5\u7ed3\u679c", ""]
    lines.append("\u6838\u67e5\u57fa\u51c6\u65e5\uff1a%s" % as_of.isoformat())
    lines.append("")

    types = pick_types(text)
    lines.append("## \u4e00\u3001\u7ea0\u7eb7\u7c7b\u578b")
    lines.append("")
    if types:
        lines.append("\u547d\u4e2d\u7c7b\u578b\uff1a%s" % "\u3001".join(types))
        lines.append("")
        lines.append("| \u7c7b\u578b | \u4e3b\u7ba1\u6216\u5904\u7f6e\u90e8\u95e8 |")
        lines.append("|---|---|")
        for ty, who in path_advice(types, False, False, False):
            lines.append("| %s | %s |" % (ty, who))
    else:
        lines.append("\u672a\u547d\u4e2d\u5e38\u89c1\u7c7b\u578b\uff0c\u9000\u56de\u4eba\u5de5\u68b3\u7406\uff1a\u6f0f\u6c34\u3001\u566a\u97f3\u3001\u8fdd\u5efa\u3001\u91c7\u5149\u901a\u98ce\u662f\u6700\u5e38\u89c1\u7684\u56db\u7c7b\u3002")
    lines.append("")

    lines.append("## \u4e8c\u3001\u5fc5\u5907\u8981\u4ef6\u6838\u67e5")
    lines.append("")
    reqs = check_required(text, types)
    if not reqs:
        lines.append("\uff08\u672a\u8bc6\u522b\u7c7b\u578b\uff0c\u65e0\u5bf9\u5e94\u8981\u4ef6\uff09")
    else:
        lines.append("| \u7c7b\u578b | \u8981\u4ef6 | \u72b6\u6001 |")
        lines.append("|---|---|---|")
        for ty, item, st in reqs:
            lines.append("| %s | %s | %s |" % (ty, item, st))
    lines.append("")

    lines.append("## \u4e09\u3001\u8bc1\u636e\u6e05\u5355\u8986\u76d6")
    lines.append("")
    lines.append("| # | \u8bc1\u636e | \u72b6\u6001 |")
    lines.append("|---|---|---|")
    evs = check_evidence(text)
    for i, (n, st) in enumerate(evs, 1):
        lines.append("| %d | %s | %s |" % (i, n, st))
    miss = [n for n, st in evs if st == "\u672a\u89c1"]
    lines.append("")
    lines.append("\u672a\u89c1\u6750\u6599\uff1a%s" % ("\u3001".join(miss) if miss else "\u65e0"))
    cov = len(evs) - len(miss)
    lines.append("")
    lines.append("\u8986\u76d6\u5ea6\uff1a%d / %d" % (cov, len(evs)))
    lines.append("")

    lines.append("## \u56db\u3001\u53d6\u8bc1\u624b\u6bb5\u5408\u6cd5\u6027")
    lines.append("")
    bad = check_methods(text)
    if bad:
        lines.append("**\u547d\u4e2d\u975e\u6cd5\u53d6\u8bc1\u98ce\u9669\uff0c\u4ee5\u4e0b\u60c5\u5f62\u53d6\u5f97\u7684\u8bc1\u636e\u53ef\u80fd\u4e0d\u88ab\u91c7\u4fe1\uff0c\u4e14\u53ef\u80fd\u53cd\u566c\uff1a**")
        lines.append("")
        for b in bad:
            lines.append("- %s" % b)
        lines.append("")
        lines.append("\u53d6\u8bc1\u7ea2\u7ebf\uff1a\u4e0d\u5f97\u7a83\u542c\u3001\u5077\u62cd\u4ed6\u4eba\u79c1\u5bc6\u7a7a\u95f4\uff0c\u4e0d\u5f97\u64ac\u9501\u8fdb\u5165\u4ed6\u4eba\u4f4f\u5b85\uff0c"
                     "\u4e0d\u5f97\u4ee5\u65ad\u6c34\u65ad\u7535\u3001\u5835\u9501\u773c\u7b49\u65b9\u5f0f\u62a5\u590d\uff0c\u4e0d\u5f97\u5728\u7f51\u7edc\u4e0a\u516c\u5f00\u90bb\u5c45\u4e2a\u4eba\u4fe1\u606f\u3002"
                     "\u5728\u81ea\u5df1\u7684\u623f\u5c4b\u5185\u5b89\u88c5\u6444\u50cf\u5934\u4e5f\u8981\u6ce8\u610f\u89d2\u5ea6\uff0c\u957f\u671f\u5bf9\u51c6\u4ed6\u4eba\u95e8\u7a97\u4ecd\u53ef\u80fd\u6784\u6210\u4fb5\u6743\u3002")
    else:
        lines.append("\u672a\u547d\u4e2d\u5e38\u89c1\u975e\u6cd5\u53d6\u8bc1\u8868\u8ff0\u3002\u4ecd\u9700\u6ce8\u610f\uff1a\u6444\u50cf\u5934\u4e0d\u5f97\u5bf9\u51c6\u4ed6\u4eba\u5367\u5ba4\u3001\u536b\u751f\u95f4\u7b49\u79c1\u5bc6\u7a7a\u95f4\uff0c"
                     "\u5f55\u97f3\u987b\u5728\u516c\u5f00\u573a\u5408\u6216\u81ea\u5df1\u53c2\u4e0e\u7684\u5bf9\u8bdd\u4e2d\u53d6\u5f97\u3002")
    lines.append("")

    lines.append("## \u4e94\u3001\u65f6\u6548")
    lines.append("")
    lm = limitation(occ, as_of)
    if lm is None:
        lines.append("\u672a\u63d0\u4f9b\u4e8b\u4ef6\u53d1\u751f\u65e5\u671f\uff0c\u65e0\u6cd5\u8ba1\u7b97\u3002\u53ef\u7528 --occurrence-date \u6307\u5b9a\u3002")
    else:
        occ_d, due, remain, past = lm
        lines.append("- \u635f\u5bb3\u53d1\u751f\u65e5\u671f\uff1a%s\uff08\u5df2\u8fc7 %d \u5929\uff09" % (occ_d.isoformat(), past))
        lines.append("- \u635f\u5bb3\u8d54\u507f\u8bf7\u6c42\u6743\u7684\u8bc9\u8bbc\u65f6\u6548\u4e00\u822c\u671f\u95f4\u6309 %d \u5e74\u638c\u63e1\uff0c\u53c2\u8003\u622a\u6b62\uff1a%s" % (LIMIT_YEARS, due.isoformat()))
        if remain < 0:
            lines.append("- **\u5df2\u8d85\u8fc7\u53c2\u8003\u671f\u95f4 %d \u5929**\uff0c\u4e3b\u5f20\u635f\u5bb3\u8d54\u507f\u53ef\u80fd\u4e27\u5931\u80dc\u8bc9\u6743\uff0c\u9700\u8981\u91cd\u65b0\u5ba1\u89c6\u6709\u65e0\u4e2d\u65ad\u3001\u4e2d\u6b62\u4e8b\u7531\u3002" % abs(remain))
        elif remain <= 90:
            lines.append("- \u4ec5\u5269 %d \u5929\uff0c\u5c3d\u5feb\u4e3b\u5f20\u6743\u5229\u5e76\u7559\u75d5\u3002" % remain)
        else:
            lines.append("- \u5269\u4f59 %d \u5929\u3002" % remain)
        lines.append("- \u8bf7\u6c42\u505c\u6b62\u4fb5\u5bb3\u3001\u6392\u9664\u59a8\u788d\u3001\u6d88\u9664\u5371\u9669\u7684\uff0c\u901a\u5e38\u4e0d\u9002\u7528\u8bc9\u8bbc\u65f6\u6548\u89c4\u5b9a\uff1b"
                     "\u635f\u5bb3\u8d54\u507f\u8bf7\u6c42\u6743\u624d\u53d7\u671f\u95f4\u9650\u5236\u3002\u4ee5\u73b0\u884c\u89c4\u5b9a\u548c\u53d7\u8bc9\u6cd5\u9662\u8ba4\u5b9a\u4e3a\u51c6\u3002")
    lines.append("")

    lines.append("---")
    lines.append("\u672c\u7ed3\u679c\u4e3a\u8bc1\u636e\u6574\u7406\u4e0e\u8def\u5f84\u63d0\u793a\uff0c\u4e0d\u6784\u6210\u6cd5\u5f8b\u610f\u89c1\uff0c\u4e5f\u4e0d\u4ee3\u8868\u88c1\u5224\u7ed3\u679c\u3002")
    return "\n".join(lines)


def render_json(text, as_of, occ=None):
    obj = {
        "as_of": as_of.isoformat(),
        "types": pick_types(text),
        "required": [{"type": t, "item": i, "status": s} for t, i, s in check_required(text, pick_types(text))],
        "evidence": [{"name": n, "status": s} for n, s in check_evidence(text)],
        "illegal_methods": check_methods(text),
        "limitation": None,
    }
    lm = limitation(occ, as_of)
    if lm:
        obj["limitation"] = {
            "occurrence": lm[0].isoformat(),
            "due": lm[1].isoformat(),
            "remain_days": lm[2],
            "past_days": lm[3],
            "overdue": lm[2] < 0,
        }
    return json.dumps(obj, ensure_ascii=False, indent=2)


SAMPLE_LEAK = """
\u697c\u4e0a\u6f0f\u6c34\u7ea0\u7eb7
2025-03-12 \u665a\u4e0a\u53d1\u73b0\u4e3b\u5367\u540a\u9876\u5f80\u4e0b\u6ef4\u6c34\uff0c\u7269\u4e1a\u5230\u573a\u62cd\u7167\u5e76\u51fa\u5177\u4e86\u60c5\u51b5\u8bf4\u660e\u3002
\u7269\u4e1a\u8054\u7cfb\u697c\u4e0a\u4e1a\u4e3b\uff0c\u697c\u4e0a\u79f0\u662f\u81ea\u5bb6\u9632\u6c34\u5c42\u8001\u5316\uff0c\u613f\u610f\u8d70\u7ef4\u4fee\u3002
\u5df2\u8bf7\u7b2c\u4e09\u65b9\u9274\u5b9a\u673a\u6784\u51fa\u5177\u9274\u5b9a\u610f\u89c1\uff0c\u786e\u8ba4\u6f0f\u6c34\u70b9\u5728\u697c\u4e0a\u536b\u751f\u95f4\u9632\u6c34\u5c42\u3002
\u7ef4\u4fee\u62a5\u4ef7\u5355\u663e\u793a\u91cd\u505a\u9632\u6c34\u53ca\u540a\u9876\u6062\u590d\u5171\u9700 8600 \u5143\uff0c\u5df2\u652f\u4ed8\u5e76\u7559\u6709\u53d1\u7968\u3002
\u66fe\u5728\u4e1a\u4e3b\u7fa4\u548c\u90bb\u5c45\u6c9f\u901a\uff0c\u6709\u5fae\u4fe1\u804a\u5929\u8bb0\u5f55\u3002\u4e4b\u524d\u8fd8\u62a5\u8fc7\u4e00\u6b21\u8b66\uff0c\u6d3e\u51fa\u6240\u6709\u51fa\u8b66\u8bb0\u5f55\u3002
"""

SAMPLE_NOISE = """
\u566a\u97f3\u6270\u6c11
\u697c\u4e0a\u6bcf\u5929\u591c\u91cc\u5341\u4e00\u70b9\u540e\u5435\uff0c\u8dd1\u6b65\u673a\u549a\u549a\u54cd\uff0c\u7a7a\u8c03\u5916\u673a\u4e5f\u54cd\uff0c\u5348\u4f11\u4e5f\u4e0d\u6d88\u505c\u3002
\u6211\u51c6\u5907\u4e70\u4e00\u4e2a\u9707\u697c\u5668\u5bf9\u4ed8\u4ed6\uff0c\u518d\u53bb\u4ed6\u5bb6\u95e8\u53e3\u88c5\u4e2a\u6444\u50cf\u5934\u76d1\u63a7\uff0c
\u987a\u4fbf\u628a\u4ed6\u5bb6\u9501\u773c\u5835\u4e0a\uff0c\u5728\u4e1a\u4e3b\u7fa4\u91cc\u628a\u4ed6\u4e2a\u4eba\u4fe1\u606f\u66dd\u5149\u51fa\u6765\u3002
\u5bb6\u91cc\u4eba\u5fc3\u795e\u4e0d\u5b89\uff0c\u5df2\u6301\u7eed\u6570\u6708\u3002
"""

SAMPLE_SUN = """
\u91c7\u5149\u7ea0\u7eb7
\u524d\u9762\u4e00\u680b\u697c 2024 \u5e74\u52a0\u5efa\u4e86\u4e24\u5c42\uff0c\u628a\u6211\u5bb6\u7684\u65e5\u7167\u906e\u4f4f\u4e86\uff0c\u51ac\u5929\u57fa\u672c\u6652\u4e0d\u5230\u592a\u9633\u3002
\u90a3\u662f\u8fdd\u5efa\uff0c\u6ca1\u6709\u4efb\u4f55\u5ba1\u6279\u624b\u7eed\u3002\u6211\u5df2\u5411\u57ce\u5e02\u7ba1\u7406\u90e8\u95e8\u53cd\u6620\u8fc7\u3002
\u73b0\u6709\u89c4\u5212\u6838\u5b9e\u610f\u89c1\u4e66\u4e00\u4efd\u3002
"""


def selftest():
    ok = True
    res = []

    def ck(name, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        res.append("%s %s got=%r want=%r" % ("PASS" if good else "FAIL", name, got, want))

    as_of = datetime.date(2026, 10, 8)

    ck("leak_type", pick_types(SAMPLE_LEAK), ["\u6f0f\u6c34\u6e17\u6f0f"])
    ck("noise_type", pick_types(SAMPLE_NOISE), ["\u566a\u97f3\u6270\u6c11"])
    ck("sun_types", sorted(pick_types(SAMPLE_SUN)), sorted(["\u91c7\u5149\u901a\u98ce\u901a\u884c", "\u8fdd\u5efa\u52a0\u5efa"]))

    ev = check_evidence(SAMPLE_LEAK)
    ck("leak_evidence_cov_ge5", sum(1 for _, s in ev if s == "\u6709") >= 5, True)
    ev2 = check_evidence(SAMPLE_NOISE)
    ck("noise_evidence_weak", sum(1 for _, s in ev2 if s == "\u6709") <= 3, True)

    req = check_required(SAMPLE_LEAK, ["\u6f0f\u6c34\u6e17\u6f0f"])
    ck("leak_req_all", all(s == "\u5df2\u8986\u76d6" for _, _, s in req), True)
    req2 = check_required(SAMPLE_NOISE, ["\u566a\u97f3\u6270\u6c11"])
    ck("noise_req_not_all", any(s == "\u5f85\u8865" for _, _, s in req2), True)

    bad = check_methods(SAMPLE_NOISE)
    ck("noise_illegal_ge3", len(bad) >= 3, True)
    ck("leak_no_illegal", check_methods(SAMPLE_LEAK), [])

    lm = limitation(datetime.date(2025, 3, 12), as_of)
    ck("limit_due", lm[1].isoformat(), "2028-03-12")
    ck("limit_not_overdue", lm[2] < 0, False)
    lm2 = limitation(datetime.date(2020, 3, 12), as_of)
    ck("limit_overdue", lm2[2] < 0, True)

    md = render_md(SAMPLE_LEAK, as_of, datetime.date(2025, 3, 12))
    ck("md_header", md.startswith("# "), True)
    js = json.loads(render_json(SAMPLE_NOISE, as_of, None))
    ck("json_keys", sorted(js.keys()),
       ["as_of", "evidence", "illegal_methods", "limitation", "required", "types"])

    for line in res:
        print(line)
    print("SELFTEST %s" % ("OK" if ok else "FAILED"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--occurrence-date", default="")
    ap.add_argument("--as-of", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--format", default="md", choices=["md", "json"])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    if not a.file or not os.path.exists(a.file):
        print("ERROR --file \u4e0d\u5b58\u5728")
        return 2

    text = open(a.file, "r", encoding="utf-8", errors="replace").read()
    as_of = parse_date(a.as_of) or datetime.date.today()
    occ = parse_date(a.occurrence_date)

    body = render_md(text, as_of, occ) if a.format == "md" else render_json(text, as_of, occ)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(body)
        print("WROTE %s" % a.out)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
