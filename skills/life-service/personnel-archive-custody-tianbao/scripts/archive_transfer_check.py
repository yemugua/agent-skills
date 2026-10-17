# -*- coding: utf-8 -*-
"""\u4eba\u4e8b\u6863\u6848\u6258\u7ba1\u4e0e\u8f6c\u9012\u6838\u67e5\u3002

\u7528\u6cd5:
  python archive_transfer_check.py --selftest
  python archive_transfer_check.py --file \u60c5\u51b5.txt --as-of 2026-10-08
  python archive_transfer_check.py --file \u60c5\u51b5.txt --letter-date 2026-09-20 --out \u7ed3\u679c.md
"""
import argparse
import datetime
import io
import json
import os
import re
import sys

FAILS = []

# \u5224\u5b9a\u4f18\u5148\u7ea7\uff1a\u6709\u4eba\u4e8b\u6863\u6848\u7ba1\u7406\u6743\u7684\u7528\u4eba\u5355\u4f4d > \u6559\u80b2\u7cfb\u7edf\u4e0e\u5b66\u6821 > \u516c\u5171\u5c31\u4e1a\u548c\u4eba\u624d\u670d\u52a1\u673a\u6784 > \u4eba\u793e\u90e8\u95e8\u6240\u5c5e\u673a\u6784
CUSTODY_PATTERNS = [
    ("\u6709\u4eba\u4e8b\u6863\u6848\u7ba1\u7406\u6743\u7684\u7528\u4eba\u5355\u4f4d", r"(\u56fd\u4f01|\u4e8b\u4e1a\u5355\u4f4d|\u673a\u5173|\u5728\u7f16|\u7f16\u5236\u5185|\u5355\u4f4d\u4fdd\u7ba1|\u5355\u4f4d\u4eba\u4e8b\u90e8\u95e8\u4fdd\u7ba1|\u592e\u4f01)"),
    ("\u6559\u80b2\u7cfb\u7edf\u4e0e\u5b66\u6821", r"(\u5b66\u6821|\u6bd5\u4e1a\u9662\u6821|\u9ad8\u6821|\u5927\u5b66|\u5b66\u7c4d|\u5728\u6821)"),
    ("\u516c\u5171\u5c31\u4e1a\u548c\u4eba\u624d\u670d\u52a1\u673a\u6784", r"(\u4eba\u624d\u4e2d\u5fc3|\u4eba\u624d\u5e02\u573a|\u4eba\u624d\u670d\u52a1\u4e2d\u5fc3|\u516c\u5171\u5c31\u4e1a|\u6d41\u52a8\u4eba\u5458)"),
    ("\u4eba\u793e\u90e8\u95e8\u6240\u5c5e\u673a\u6784", r"(\u4eba\u793e\u5c40|\u4eba\u793e\u90e8\u95e8|\u6237\u7c4d\u5730\u6258\u7ba1|\u8857\u9053|\u793e\u533a)"),
]
CUSTODY_ORDER = [t for t, _ in CUSTODY_PATTERNS]

# \u8f6c\u9012\u6e20\u9053\uff1a(\u6e20\u9053, \u6b63\u5219, \u662f\u5426\u5408\u89c4)
CHANNEL_PATTERNS = [
    ("\u673a\u8981\u901a\u4fe1", r"(\u673a\u8981|\u673a\u8981\u901a\u4fe1|\u673a\u8981\u6e20\u9053|\u673a\u8981\u5c40|\u673a\u8981\u5bc4)", True),
    ("\u6d3e\u4e13\u4eba\u9001\u8fbe", r"(\u6d3e\u4e13\u4eba|\u4e13\u4eba\u9001\u8fbe|\u4e24\u4eba\u9001\u8fbe|\u4e13\u4eba\u9001|\u5bc6\u5c01\u7b7e\u6536)", True),
    ("\u90ae\u653f\u5feb\u9012", r"(\u5feb\u9012|\u987a\u4e30|\u5bc4\u8fc7\u53bb|\u7269\u6d41|\u90ae\u5bc4)", False),
    ("\u4e2a\u4eba\u81ea\u5e26", r"(\u81ea\u5df1\u62ff|\u81ea\u5df1\u5e26|\u62ff\u5728\u624b\u91cc|\u81ea\u5df1\u9001\u53bb|\u6258\u4eba\u634e|\u653e\u5728\u5bb6\u91cc|\u5728\u81ea\u5df1\u624b\u91cc)", False),
    ("\u62c6\u5c01\u540e\u81ea\u884c\u5c01\u88c5", r"(\u62c6\u5c01|\u62c6\u5f00|\u5c01\u6761\u7834|\u5c01\u6761\u65ad|\u81ea\u5df1\u5c01|\u91cd\u65b0\u7c98|\u6495\u5f00)", False),
]

# \u5f52\u6863\u6750\u6599\uff1a(\u7c7b\u522b, \u6b63\u5219)
MATERIAL_PATTERNS = [
    ("\u5c65\u5386\u6750\u6599", r"(\u5c65\u5386|\u5c65\u5386\u8868|\u804c\u5de5\u767b\u8bb0\u8868|\u767b\u8bb0\u8868)"),
    ("\u5b66\u5386\u5b66\u4f4d\u6750\u6599", r"(\u5b66\u5386|\u5b66\u4f4d|\u6bd5\u4e1a\u751f\u767b\u8bb0\u8868|\u6210\u7ee9\u5355|\u6bd5\u4e1a\u8bc1|\u5b66\u4f4d\u8bc1)"),
    ("\u653f\u6cbb\u9762\u8c8c\u6750\u6599", r"(\u515a\u5458|\u5165\u515a|\u5165\u56e2|\u5fd7\u613f\u4e66|\u653f\u6cbb\u9762\u8c8c|\u56e2\u5458)"),
    ("\u5de5\u8d44\u4e0e\u4efb\u514d\u6750\u6599", r"(\u5de5\u8d44|\u5de5\u8d44\u5ba1\u6279|\u4efb\u514d|\u4efb\u804c|\u8c03\u8d44)"),
    ("\u8003\u6838\u4e0e\u5956\u60e9\u6750\u6599", r"(\u8003\u6838|\u5e74\u5ea6\u8003\u6838|\u5956\u60e9|\u5956\u52b1|\u5904\u5206)"),
    ("\u52b3\u52a8\u5408\u540c\u4e0e\u5c31\u4e1a\u6750\u6599", r"(\u52b3\u52a8\u5408\u540c|\u5c31\u4e1a\u767b\u8bb0|\u79bb\u804c|\u7528\u5de5|\u5c31\u4e1a)"),
    ("\u804c\u79f0\u4e0e\u6280\u80fd\u6750\u6599", r"(\u804c\u79f0|\u6280\u80fd\u7b49\u7ea7|\u8bc4\u5ba1\u8868|\u8d44\u683c\u8bc1)"),
    ("\u8f6c\u9012\u4e0e\u63a5\u6536\u624b\u7eed", r"(\u8f6c\u9012\u5355|\u56de\u6267|\u6258\u7ba1\u534f\u8bae|\u8f6c\u9012|\u63a5\u6536\u624b\u7eed|\u5b58\u6863\u8bc1\u660e)"),
]

# \u6b7b\u6863\u6210\u56e0
DEAD_PATTERNS = [
    ("\u6ede\u7559\u4e2a\u4eba\u624b\u4e2d", r"(\u5728\u81ea\u5df1\u624b\u91cc|\u81ea\u5df1\u62ff\u7740|\u653e\u5728\u5bb6\u91cc|\u4e2a\u4eba\u624b\u4e2d|\u81ea\u5df1\u4fdd\u7ba1\u6863\u6848)"),
    ("\u5c01\u6761\u7834\u635f", r"(\u62c6\u5c01|\u62c6\u5f00|\u5c01\u6761\u7834|\u5c01\u6761\u65ad|\u5c01\u6761\u6389\u4e86)"),
    ("\u957f\u671f\u672a\u529e\u6258\u7ba1", r"(\u6bd5\u4e1a\u591a\u5e74|\u4e00\u76f4\u6ca1\u529e|\u591a\u5e74\u6ca1\u7ba1|\u627e\u4e0d\u5230\u6863\u6848|\u53bb\u5411\u4e0d\u660e)"),
    ("\u5173\u952e\u6750\u6599\u7f3a\u5931", r"(\u7f3a\u5b66\u5386|\u7f3a\u5de5\u9f84|\u7f3a\u515a\u5458\u6750\u6599|\u6750\u6599\u7f3a\u5931|\u7f3a\u6750\u6599)"),
    ("\u673a\u6784\u5bf9\u63a5\u4e0d\u7545", r"(\u8de8\u7701|\u4e24\u5730\u4e0d\u8ba4|\u4e92\u76f8\u63a8|\u4e0d\u7ed9\u63a5\u6536|\u9000\u56de)"),
]

NEGATIVE_WATCH = [
    (r"\u6863\u6848\u672a\u8f6c\u9012", "\u300c\u6863\u6848\u672a\u8f6c\u9012\u300d\u4e0d\u7b49\u4e8e\u300c\u6863\u6848\u5df2\u8f6c\u9012\u300d"),
    (r"\u6863\u6848\u5728\u4e2a\u4eba\u624b\u4e2d", "\u300c\u6863\u6848\u5728\u4e2a\u4eba\u624b\u4e2d\u300d\u4e0d\u7b49\u4e8e\u300c\u6863\u6848\u5df2\u6258\u7ba1\u300d"),
    (r"\u5c01\u6761\u5df2\u7834\u635f", "\u300c\u5c01\u6761\u5df2\u7834\u635f\u300d\u4e0d\u7b49\u4e8e\u300c\u5c01\u6761\u5b8c\u597d\u300d"),
    (r"\u672a\u53d6\u5f97\u56de\u6267", "\u300c\u672a\u53d6\u5f97\u56de\u6267\u300d\u4e0d\u7b49\u4e8e\u300c\u5bf9\u65b9\u5df2\u6536\u5230\u300d"),
    (r"\u6750\u6599\u7f3a\u5931", "\u300c\u6750\u6599\u7f3a\u5931\u300d\u4e0d\u7b49\u4e8e\u300c\u6750\u6599\u9f50\u5168\u300d"),
    (r"\u4e0d\u4e88\u63a5\u6536", "\u300c\u673a\u6784\u4e0d\u4e88\u63a5\u6536\u300d\u4e0d\u7b49\u4e8e\u300c\u673a\u6784\u5df2\u63a5\u6536\u300d"),
]

NEG_WORDS = r"(\u6ca1(?:\u6709|\u529e|\u4ea4|\u5e26|\u8f6c)?|\u672a|\u5c1a\u672a|\u8fd8\u6ca1|\u7f3a|\u5fd8\u8bb0|\u6f0f\u4e86|\u672a\u53d6\u5f97|\u672a\u5f00|\u4e0d\u77e5\u9053|\u627e\u4e0d\u5230)"

DATE_RE = re.compile(r"(\d{4})[-/.\u5e74](\d{1,2})[-/.\u6708](\d{1,2})")

LETTER_VALID_DAYS = 30


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
    m = DATE_RE.search(str(text).strip())
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def hit_with_negation(text, pat):
    """\u5173\u952e\u8bcd\u547d\u4e2d\u4f46\u9644\u8fd1\u6709\u5426\u5b9a\u8bcd\u65f6\u89c6\u4e3a\u672a\u5907\u9f50\u3002"""
    found = False
    for m in re.finditer(pat, text):
        s = max(0, m.start() - 4)
        e = min(len(text), m.end() + 6)
        if re.search(NEG_WORDS, text[s:e]):
            continue
        found = True
    return found


def detect_custody(text):
    hits = [t for t, pat in CUSTODY_PATTERNS if re.search(pat, text)]
    if not hits:
        return "\u672a\u5224\u5b9a", []
    main = min(hits, key=lambda x: CUSTODY_ORDER.index(x))
    return main, hits


def check_channels(text):
    rows = []
    for name, pat, ok in CHANNEL_PATTERNS:
        if re.search(pat, text):
            rows.append({"\u6e20\u9053": name, "\u5408\u89c4": ok,
                         "\u5224\u5b9a": "\u5408\u89c4" if ok else "\u8fdd\u89c4"})
    return rows


def check_materials(text):
    rows = []
    for name, pat in MATERIAL_PATTERNS:
        hit = hit_with_negation(text, pat)
        rows.append({"\u7c7b\u522b": name, "\u72b6\u6001": ("\u9f50\u5907" if hit else "\u7f3a\u5931")})
    return rows


def dead_scan(text):
    return [n for n, pat in DEAD_PATTERNS if re.search(pat, text)]


def negative_watch(text):
    return [tip for pat, tip in NEGATIVE_WATCH if re.search(pat, text)]


def letter_valid(issue_date, as_of):
    if issue_date is None or as_of is None:
        return None
    left = (issue_date + datetime.timedelta(days=LETTER_VALID_DAYS) - as_of).days
    if left < 0:
        level = "\u5df2\u903e\u671f"
    elif left <= 7:
        level = "\u5373\u5c06\u5230\u671f"
    else:
        level = "\u6709\u6548"
    return {"\u5f00\u5177\u65e5": issue_date.isoformat(), "\u6709\u6548\u671f\u5929\u6570": LETTER_VALID_DAYS,
            "\u5230\u671f\u65e5": (issue_date + datetime.timedelta(days=LETTER_VALID_DAYS)).isoformat(),
            "\u5269\u4f59\u5929\u6570": left, "\u72b6\u6001": level}


def build_report(text, as_of_str, letter_str):
    as_of = parse_date(as_of_str) or datetime.date.today()
    custody, cand = detect_custody(text)
    channels = check_channels(text)
    materials = check_materials(text)
    dead = dead_scan(text)
    negs = negative_watch(text)
    letter = letter_valid(parse_date(letter_str), as_of)
    violations = [c["\u6e20\u9053"] for c in channels if not c["\u5408\u89c4"]]

    lines = []
    lines.append("=" * 62)
    lines.append("\u4eba\u4e8b\u6863\u6848\u6258\u7ba1\u4e0e\u8f6c\u9012\u6838\u67e5\u62a5\u544a")
    lines.append("=" * 62)
    lines.append("")
    lines.append("[\u6258\u7ba1\u673a\u6784] %s" % custody)
    if len(cand) > 1:
        lines.append("  \u5019\u9009\u673a\u6784\uff1a%s\uff08\u53d6\u4f18\u5148\u7ea7\u6700\u9ad8\u7684\u4e00\u9879\uff09" % "\u3001".join(cand))
    if custody == "\u672a\u5224\u5b9a":
        lines.append("  [\u63d0\u793a] \u673a\u6784\u672a\u5224\u5b9a\u524d\u4e0d\u8981\u6309\u63a8\u6d4b\u529e\u7406\uff0c\u5148\u5411\u62df\u6258\u7ba1\u673a\u6784\u786e\u8ba4")
    lines.append("")
    lines.append("[\u8f6c\u9012\u6e20\u9053]")
    if not channels:
        lines.append("  \u672a\u63d0\u53ca\u8f6c\u9012\u65b9\u5f0f\uff0c\u9700\u4eba\u5de5\u786e\u8ba4")
    for c in channels:
        lines.append("  %-10s %s" % (c["\u6e20\u9053"], c["\u5224\u5b9a"]))
    if violations:
        lines.append("  [\u7ea2\u7ebf] \u547d\u4e2d\u8fdd\u89c4\u6e20\u9053\uff1a%s" % "\u3001".join(violations))
        lines.append("  \u6863\u6848\u4e0d\u5f97\u4e2a\u4eba\u81ea\u5e26\u3001\u4e0d\u5f97\u901a\u8fc7\u5feb\u9012\u5bc4\u9001\u3001\u4e0d\u5f97\u62c6\u5c01\u540e\u81ea\u884c\u5c01\u88c5")
    lines.append("")
    lines.append("[\u5f52\u6863\u6750\u6599\u6838\u67e5]")
    for m in materials:
        lines.append("  %-12s %s" % (m["\u7c7b\u522b"], m["\u72b6\u6001"]))
    missing = [m["\u7c7b\u522b"] for m in materials if m["\u72b6\u6001"] == "\u7f3a\u5931"]
    lines.append("  \u7f3a\u5931\u9879\uff1a%s" % ("\u3001".join(missing) if missing else "\u65e0"))
    if missing:
        lines.append("  [\u63d0\u793a] \u7f3a\u5931\u6750\u6599\u5e94\u5411\u539f\u5f62\u6210\u5355\u4f4d\u7533\u8bf7\u8865\u5236\uff0c\u4e0d\u5f97\u81ea\u884c\u5236\u4f5c")
    lines.append("")
    lines.append("[\u6b7b\u6863\u98ce\u9669] %s" % ("\u3001".join(dead) if dead else "\u672a\u547d\u4e2d"))
    if dead:
        lines.append("  [\u63d0\u793a] \u80fd\u5426\u63a5\u6536\u4e0e\u5982\u4f55\u8865\u6551\uff0c\u4e00\u5f8b\u4ee5\u62df\u6258\u7ba1\u673a\u6784\u7b54\u590d\u4e3a\u51c6")
    lines.append("")
    lines.append("[\u8c03\u6863\u51fd]")
    if letter:
        lines.append("  \u5f00\u5177\u65e5 %s\uff0c\u6309 %d \u5929\u8ba1\u5230\u671f\u65e5 %s\uff0c\u5269\u4f59 %d \u5929\uff08%s\uff09" % (
            letter["\u5f00\u5177\u65e5"], letter["\u6709\u6548\u671f\u5929\u6570"], letter["\u5230\u671f\u65e5"],
            letter["\u5269\u4f59\u5929\u6570"], letter["\u72b6\u6001"]))
        if letter["\u72b6\u6001"] != "\u6709\u6548":
            lines.append("  [\u63d0\u793a] \u8c03\u6863\u51fd\u903e\u671f\u901a\u5e38\u9700\u91cd\u65b0\u5f00\u5177\uff0c\u5e76\u786e\u8ba4\u5bf9\u65b9\u673a\u6784\u662f\u5426\u5df2\u5b9e\u9645\u6536\u5230")
    else:
        lines.append("  \u672a\u63d0\u4f9b --letter-date\uff0c\u8df3\u8fc7")
    lines.append("")
    if negs:
        lines.append("[\u5426\u5b9a\u8bcd\u63d0\u9192]")
        for n in negs:
            lines.append("  - %s" % n)
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u811a\u672c\u53ea\u505a\u5173\u952e\u8bcd\u5339\u914d\uff0c\u4e0d\u4ee3\u8868\u63a5\u6536\u7ed3\u8bba\u3002")
    lines.append("      \u6258\u7ba1\u6761\u4ef6\u3001\u8f6c\u9012\u8981\u6c42\u3001\u65f6\u9650\u4ee5\u73b0\u884c\u89c4\u5b9a\u548c\u6863\u6848\u7ba1\u7406\u670d\u52a1\u673a\u6784\u8981\u6c42\u4e3a\u51c6\u3002")
    lines.append("=" * 62)

    summary = {"\u6258\u7ba1\u673a\u6784": custody, "\u5019\u9009\u673a\u6784": cand, "\u8f6c\u9012\u6e20\u9053": channels,
               "\u8fdd\u89c4\u6e20\u9053": violations, "\u6750\u6599": materials, "\u7f3a\u5931\u9879": missing,
               "\u6b7b\u6863\u98ce\u9669": dead, "\u5426\u5b9a\u8bcd\u63d0\u9192": negs, "\u8c03\u6863\u51fd": letter}
    return "\n".join(lines), summary


SAMPLE = """\u6211\u6bd5\u4e1a\u540e\u6863\u6848\u4e00\u76f4\u5728\u4eba\u624d\u4e2d\u5fc3\u6258\u7ba1\uff0c\u73b0\u5728\u6362\u4e86\u57ce\u5e02\u5de5\u4f5c\uff0c
\u51c6\u5907\u901a\u8fc7\u673a\u8981\u901a\u4fe1\u628a\u6863\u6848\u8f6c\u8fc7\u53bb\uff0c\u5df2\u7ecf\u5f00\u4e86\u8c03\u6863\u51fd\uff0c\u6709\u5b66\u5386\u6750\u6599\u548c\u52b3\u52a8\u5408\u540c\u3002"""


def selftest():
    ck("\u5e94\u89e3\u6790\u6807\u51c6\u65e5\u671f", parse_date("2026-10-08") == datetime.date(2026, 10, 8))
    ck("\u5e94\u89e3\u6790\u4e2d\u6587\u65e5\u671f", parse_date("2026\u5e749\u670820\u65e5") == datetime.date(2026, 9, 20))
    ck("\u7a7a\u503c\u5e94\u8fd4\u56de None", parse_date("") is None)

    c1, _ = detect_custody("\u6863\u6848\u653e\u5728\u4eba\u624d\u4e2d\u5fc3")
    ck("\u4eba\u624d\u4e2d\u5fc3\u5e94\u5224\u4e3a\u516c\u5171\u5c31\u4e1a\u548c\u4eba\u624d\u670d\u52a1\u673a\u6784", c1 == "\u516c\u5171\u5c31\u4e1a\u548c\u4eba\u624d\u670d\u52a1\u673a\u6784")
    c2, _ = detect_custody("\u6211\u5728\u56fd\u4f01\uff0c\u6863\u6848\u5355\u4f4d\u4fdd\u7ba1")
    ck("\u56fd\u4f01\u5e94\u5224\u4e3a\u6709\u4eba\u4e8b\u6863\u6848\u7ba1\u7406\u6743\u7684\u7528\u4eba\u5355\u4f4d", c2 == "\u6709\u4eba\u4e8b\u6863\u6848\u7ba1\u7406\u6743\u7684\u7528\u4eba\u5355\u4f4d")
    c3, _ = detect_custody("\u6bd5\u4e1a\u9662\u6821\u8fd8\u7559\u7740\u6211\u7684\u6863\u6848")
    ck("\u5b66\u6821\u5e94\u5224\u4e3a\u6559\u80b2\u7cfb\u7edf\u4e0e\u5b66\u6821", c3 == "\u6559\u80b2\u7cfb\u7edf\u4e0e\u5b66\u6821")
    c4, _ = detect_custody("\u6863\u6848\u4e0d\u77e5\u9053\u5728\u54ea")
    ck("\u65e0\u5173\u952e\u8bcd\u5e94\u5224\u4e3a\u672a\u5224\u5b9a", c4 == "\u672a\u5224\u5b9a")
    c5, cand5 = detect_custody("\u56fd\u4f01\u5de5\u4f5c\uff0c\u6863\u6848\u8fd8\u5728\u5b66\u6821")
    ck("\u591a\u9879\u547d\u4e2d\u5e94\u53d6\u4f18\u5148\u7ea7\u6700\u9ad8\u7684", c5 == "\u6709\u4eba\u4e8b\u6863\u6848\u7ba1\u7406\u6743\u7684\u7528\u4eba\u5355\u4f4d")
    ck("\u5019\u9009\u673a\u6784\u5e94\u4fdd\u7559\u5176\u4ed6\u547d\u4e2d\u9879", "\u6559\u80b2\u7cfb\u7edf\u4e0e\u5b66\u6821" in cand5)

    ch = check_channels("\u6211\u81ea\u5df1\u62ff\u7740\u6863\u6848\u7528\u5feb\u9012\u5bc4\u8fc7\u53bb")
    names = [x["\u6e20\u9053"] for x in ch]
    ck("\u5e94\u8bc6\u522b\u51fa\u4e2a\u4eba\u81ea\u5e26", "\u4e2a\u4eba\u81ea\u5e26" in names)
    ck("\u5e94\u8bc6\u522b\u51fa\u90ae\u653f\u5feb\u9012", "\u90ae\u653f\u5feb\u9012" in names)
    ck("\u4e2a\u4eba\u81ea\u5e26\u5e94\u5224\u8fdd\u89c4",
       [x["\u5224\u5b9a"] for x in ch if x["\u6e20\u9053"] == "\u4e2a\u4eba\u81ea\u5e26"][0] == "\u8fdd\u89c4")
    ch2 = check_channels("\u901a\u8fc7\u673a\u8981\u901a\u4fe1\u8f6c\u9012\uff0c\u6d3e\u4e13\u4eba\u9001\u8fbe")
    ck("\u673a\u8981\u901a\u4fe1\u5e94\u5224\u5408\u89c4",
       [x["\u5224\u5b9a"] for x in ch2 if x["\u6e20\u9053"] == "\u673a\u8981\u901a\u4fe1"][0] == "\u5408\u89c4")
    ck("\u672a\u63d0\u53ca\u6e20\u9053\u65f6\u5e94\u8fd4\u56de\u7a7a\u5217\u8868", check_channels("\u60f3\u6258\u7ba1\u6863\u6848") == [])

    d = dict((x["\u7c7b\u522b"], x["\u72b6\u6001"]) for x in check_materials("\u6709\u5b66\u5386\u6750\u6599\u3001\u52b3\u52a8\u5408\u540c\u3001\u515a\u5458\u6750\u6599"))
    ck("\u5b66\u5386\u6750\u6599\u5e94\u5224\u9f50\u5907", d["\u5b66\u5386\u5b66\u4f4d\u6750\u6599"] == "\u9f50\u5907")
    ck("\u653f\u6cbb\u9762\u8c8c\u6750\u6599\u5e94\u5224\u9f50\u5907", d["\u653f\u6cbb\u9762\u8c8c\u6750\u6599"] == "\u9f50\u5907")
    ck("\u672a\u63d0\u53ca\u7684\u5de5\u8d44\u6750\u6599\u5e94\u5224\u7f3a\u5931", d["\u5de5\u8d44\u4e0e\u4efb\u514d\u6750\u6599"] == "\u7f3a\u5931")
    ck("\u7f3a\u5b66\u5386\u5e94\u5224\u7f3a\u5931",
       dict((x["\u7c7b\u522b"], x["\u72b6\u6001"]) for x in check_materials("\u6863\u6848\u91cc\u7f3a\u5b66\u5386\u6750\u6599"))["\u5b66\u5386\u5b66\u4f4d\u6750\u6599"] == "\u7f3a\u5931")

    dd = dead_scan("\u6863\u6848\u5728\u81ea\u5df1\u624b\u91cc\uff0c\u5c01\u6761\u62c6\u5f00\u4e86\uff0c\u6bd5\u4e1a\u591a\u5e74\u4e00\u76f4\u6ca1\u529e")
    ck("\u5e94\u547d\u4e2d\u6ede\u7559\u4e2a\u4eba\u624b\u4e2d", "\u6ede\u7559\u4e2a\u4eba\u624b\u4e2d" in dd)
    ck("\u5e94\u547d\u4e2d\u5c01\u6761\u7834\u635f", "\u5c01\u6761\u7834\u635f" in dd)
    ck("\u5e94\u547d\u4e2d\u957f\u671f\u672a\u529e\u6258\u7ba1", "\u957f\u671f\u672a\u529e\u6258\u7ba1" in dd)
    ck("\u6b63\u5e38\u6587\u672c\u4e0d\u5e94\u547d\u4e2d\u6b7b\u6863\u6210\u56e0", dead_scan("\u6863\u6848\u6b63\u5e38\u6258\u7ba1\u4e2d") == [])

    l1 = letter_valid(datetime.date(2026, 9, 20), datetime.date(2026, 10, 8))
    ck("\u8c03\u6863\u51fd\u5269\u4f59\u5929\u6570\u5e94\u6b63\u786e", l1["\u5269\u4f59\u5929\u6570"] == 12)
    ck("\u8c03\u6863\u51fd\u5e94\u5224\u4e3a\u6709\u6548", l1["\u72b6\u6001"] == "\u6709\u6548")
    l2 = letter_valid(datetime.date(2026, 8, 1), datetime.date(2026, 10, 8))
    ck("\u8c03\u6863\u51fd\u5e94\u5224\u4e3a\u5df2\u903e\u671f", l2["\u72b6\u6001"] == "\u5df2\u903e\u671f")
    l3 = letter_valid(datetime.date(2026, 9, 15), datetime.date(2026, 10, 8))
    ck("\u4e34\u8fd1\u5230\u671f\u5e94\u5224\u4e3a\u5373\u5c06\u5230\u671f", l3["\u72b6\u6001"] == "\u5373\u5c06\u5230\u671f")
    ck("\u672a\u63d0\u4f9b\u65e5\u671f\u5e94\u8fd4\u56de None", letter_valid(None, datetime.date(2026, 10, 8)) is None)

    n = negative_watch("\u6863\u6848\u672a\u8f6c\u9012\uff0c\u672a\u53d6\u5f97\u56de\u6267\uff0c\u673a\u6784\u4e0d\u4e88\u63a5\u6536")
    ck("\u5e94\u7ed9\u51fa\u4e09\u6761\u5426\u5b9a\u8bcd\u63d0\u9192", len(n) == 3)

    rep, sm = build_report(SAMPLE, "2026-10-08", None)
    ck("\u62a5\u544a\u5e94\u542b\u6807\u9898", "\u4eba\u4e8b\u6863\u6848\u6258\u7ba1\u4e0e\u8f6c\u9012\u6838\u67e5\u62a5\u544a" in rep)
    ck("\u6837\u4f8b\u5e94\u5224\u4e3a\u4eba\u624d\u4e2d\u5fc3\u6258\u7ba1", sm["\u6258\u7ba1\u673a\u6784"] == "\u516c\u5171\u5c31\u4e1a\u548c\u4eba\u624d\u670d\u52a1\u673a\u6784")
    ck("\u6837\u4f8b\u4e0d\u5e94\u6709\u8fdd\u89c4\u6e20\u9053", sm["\u8fdd\u89c4\u6e20\u9053"] == [])
    ck("\u6837\u4f8b\u5e94\u547d\u4e2d\u673a\u8981\u901a\u4fe1",
       "\u673a\u8981\u901a\u4fe1" in [x["\u6e20\u9053"] for x in sm["\u8f6c\u9012\u6e20\u9053"]])
    ck("\u6837\u4f8b\u4e0d\u5e94\u547d\u4e2d\u6b7b\u6863\u6210\u56e0", sm["\u6b7b\u6863\u98ce\u9669"] == [])
    return not FAILS


def main():
    ap = argparse.ArgumentParser(description="\u4eba\u4e8b\u6863\u6848\u6258\u7ba1\u4e0e\u8f6c\u9012\u6838\u67e5")
    ap.add_argument("--file", help="\u5f85\u6838\u67e5\u6587\u672c\uff1a\u60c5\u51b5\u8bf4\u660e\u3001\u6750\u6599\u6e05\u5355\u6216\u804a\u5929\u8bb0\u5f55\u5bfc\u51fa\uff08.txt/.md\uff09")
    ap.add_argument("--text", help="\u76f4\u63a5\u7ed9\u4e00\u6bb5\u60c5\u51b5\u63cf\u8ff0")
    ap.add_argument("--as-of", default=None, help="\u6838\u67e5\u57fa\u51c6\u65e5\uff0c\u5982 2026-10-08")
    ap.add_argument("--letter-date", default=None, help="\u8c03\u6863\u51fd\u5f00\u5177\u65e5")
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

    report, summary = build_report(text, args.as_of, args.letter_date)
    out_path = args.out or os.path.join(here, "_last_result.txt")
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.format == "json" else report
    io.open(out_path, "w", encoding="utf-8").write(body)
    print(body)
    print("")
    print("\u7ed3\u679c\u5df2\u5199\u5165: %s" % out_path)


if __name__ == "__main__":
    main()
