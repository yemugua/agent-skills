# -*- coding: utf-8 -*-
"""\u5efa\u8bbe\u5de5\u7a0b\u6d88\u9632\u9a8c\u6536\u6750\u6599\u6838\u67e5\u3002

\u7528\u6cd5:
  python acceptance_check.py --file \u9879\u76ee\u60c5\u51b5.txt --as-of 2026-10-08
  python acceptance_check.py --file \u9879\u76ee\u60c5\u51b5.txt --accept-date 2026-10-01
  python acceptance_check.py --selftest
"""
import argparse
import datetime
import json
import os
import re
import sys

# ---- 15 \u9879\u5fc5\u5907\u6750\u6599 ----
MATERIALS = [
    ("\u7533\u8bf7\u8868", "\u7533\u8bf7\u8868|\u9a8c\u6536\u7533\u8bf7|\u6d88\u9632\u9a8c\u6536\u7533\u8bf7"),
    ("\u7ae3\u5de5\u9a8c\u6536\u62a5\u544a", "\u7ae3\u5de5\u9a8c\u6536\u62a5\u544a|\u7ae3\u5de5\u9a8c\u6536|\u56db\u65b9\u9a8c\u6536|\u5206\u90e8\u5de5\u7a0b\u9a8c\u6536"),
    ("\u7ae3\u5de5\u56fe\u7eb8", "\u7ae3\u5de5\u56fe\u7eb8|\u7ae3\u5de5\u56fe|\u56fe\u7eb8"),
    ("\u6d88\u9632\u8bbe\u65bd\u6e05\u5355\u4e0e\u4ea7\u54c1\u6587\u4ef6", "\u8bbe\u65bd\u6e05\u5355|\u7cfb\u7edf\u6e05\u5355|\u5408\u683c\u8bc1\u660e|\u4ea7\u54c1\u5408\u683c\u8bc1|\u5f3a\u5236\u6027\u8ba4\u8bc1|\u578b\u5f0f\u68c0\u9a8c"),
    ("\u5efa\u7b51\u6784\u4ef6\u4e0e\u88c5\u4fee\u6750\u6599\u8bc1\u660e", "\u71c3\u70e7\u6027\u80fd|\u88c5\u4fee\u6750\u6599|\u5efa\u7b51\u6784\u4ef6|\u5efa\u7b51\u6750\u6599|\u51fa\u5382\u5408\u683c\u8bc1"),
    ("\u6d88\u9632\u8bbe\u65bd\u68c0\u6d4b\u5408\u683c\u62a5\u544a", "\u68c0\u6d4b\u62a5\u544a|\u68c0\u6d4b\u5408\u683c|\u6d88\u9632\u8bbe\u65bd\u68c0\u6d4b"),
    ("\u65bd\u5de5\u76d1\u7406\u68c0\u6d4b\u5355\u4f4d\u8d44\u8d28", "\u8d44\u8d28\u8bc1\u660e|\u8d44\u683c\u8bc1\u660e|\u8425\u4e1a\u6267\u7167|\u8d44\u8d28\u7b49\u7ea7"),
    ("\u5efa\u8bbe\u5355\u4f4d\u8eab\u4efd\u8bc1\u660e", "\u5efa\u8bbe\u5355\u4f4d|\u8425\u4e1a\u6267\u7167|\u6cd5\u5b9a\u4ee3\u8868\u4eba|\u7edf\u4e00\u793e\u4f1a\u4fe1\u7528\u4ee3\u7801"),
    ("\u89c4\u5212\u4e0e\u65bd\u5de5\u8bb8\u53ef", "\u89c4\u5212\u8bb8\u53ef|\u65bd\u5de5\u8bb8\u53ef|\u5efa\u8bbe\u5de5\u7a0b\u89c4\u5212"),
    ("\u6d88\u9632\u8bbe\u8ba1\u5ba1\u67e5\u610f\u89c1", "\u8bbe\u8ba1\u5ba1\u67e5|\u5ba1\u67e5\u610f\u89c1|\u5ba1\u67e5\u5408\u683c\u4e66|\u8bbe\u8ba1\u6587\u4ef6\u5ba1\u67e5"),
    ("\u8bbe\u8ba1\u53d8\u66f4\u590d\u6838\u6587\u4ef6", "\u6280\u672f\u590d\u6838|\u91cd\u65b0\u5ba1\u67e5|\u8bbe\u8ba1\u53d8\u66f4|\u53d8\u66f4\u8bf4\u660e"),
    ("\u9690\u853d\u5de5\u7a0b\u9a8c\u6536\u8bb0\u5f55", "\u9690\u853d\u5de5\u7a0b|\u9690\u853d\u9a8c\u6536|\u9632\u706b\u5c01\u5835|\u9632\u706b\u6d82\u6599"),
    ("\u65bd\u5de5\u8c03\u8bd5\u4e0e\u8054\u52a8\u8bd5\u9a8c\u8bb0\u5f55", "\u8054\u52a8\u8bd5\u9a8c|\u8c03\u8bd5\u8bb0\u5f55|\u8bd5\u9a8c\u8bb0\u5f55|\u65bd\u5de5\u8bb0\u5f55"),
    ("\u6d88\u9632\u5b89\u5168\u5236\u5ea6\u4e0e\u9884\u6848", "\u7ba1\u7406\u5236\u5ea6|\u5e94\u6025\u758f\u6563|\u9884\u6848|\u7ba1\u7406\u4eba|\u8d23\u4efb\u4eba"),
    ("\u4e13\u5bb6\u8bc4\u5ba1\u610f\u89c1", "\u4e13\u5bb6\u8bc4\u5ba1|\u4e13\u5bb6\u8bba\u8bc1|\u8bc4\u5ba1\u610f\u89c1"),
]

VETO = ["\u7ae3\u5de5\u56fe\u7eb8", "\u6d88\u9632\u8bbe\u65bd\u68c0\u6d4b\u5408\u683c\u62a5\u544a", "\u6d88\u9632\u8bbe\u8ba1\u5ba1\u67e5\u610f\u89c1"]

# ---- \u7279\u6b8a\u5efa\u8bbe\u5de5\u7a0b\u5224\u5b9a\uff1a\u573a\u6240\u7c7b\u578b\u5173\u952e\u8bcd ----
SPECIAL_KEYWORDS = [
    ("\u5bbe\u9986\u996d\u5e97", "\u5bbe\u9986|\u996d\u5e97|\u9152\u5e97|\u65c5\u5e97|\u62db\u5f85\u6240"),
    ("\u5546\u573a\u5e02\u573a", "\u5546\u573a|\u5e02\u573a|\u8d85\u5e02|\u8d2d\u7269\u4e2d\u5fc3|\u5546\u4e1a\u7efc\u5408\u4f53"),
    ("\u4ea4\u901a\u573a\u7ad9", "\u5019\u8f66\u5ba4|\u5019\u8239\u5385|\u822a\u7ad9\u697c|\u5ba2\u8fd0\u7ad9|\u673a\u573a"),
    ("\u4f53\u80b2\u573a\u9986\u4f1a\u5802", "\u4f53\u80b2\u9986|\u4f53\u80b2\u573a|\u4f1a\u5802|\u793c\u5802|\u89c2\u4f17\u5385"),
    ("\u5c55\u89c8\u9986\u535a\u7269\u9986", "\u5c55\u89c8\u9986|\u535a\u7269\u9986|\u5c55\u793a\u5385|\u4f1a\u5c55"),
    ("\u5f71\u5267\u9662", "\u5f71\u5267\u9662|\u5267\u573a|\u7535\u5f71\u9662"),
    ("\u6b4c\u821e\u5a31\u4e50\u653e\u6620\u6e38\u827a", "\u6b4c\u821e\u5385|\u5f55\u50cf\u5385|\u5361\u62c9OK|\u591c\u603b\u4f1a|\u6e38\u827a\u5385|\u6851\u62ff|\u7f51\u5427|\u9152\u5427"),
    ("\u533b\u7597\u6559\u80b2\u517b\u8001", "\u533b\u9662|\u95e8\u8bca|\u6559\u5b66\u697c|\u517b\u8001\u9662|\u798f\u5229\u9662"),
    ("\u6613\u71c3\u6613\u7206", "\u6613\u71c3\u6613\u7206|\u5371\u9669\u7269\u54c1|\u5316\u5de5|\u6cb9\u5e93|\u6c14\u7ad9|\u5145\u88c5\u7ad9|\u8c03\u538b\u7ad9"),
    ("\u516c\u5171\u5efa\u7b51", "\u529e\u516c\u697c|\u5199\u5b57\u697c|\u5e7f\u64ad\u7535\u89c6|\u7535\u4fe1\u697c|\u90ae\u653f|\u6863\u6848|\u7535\u529b\u8c03\u5ea6"),
    ("\u96a7\u9053\u4e0e\u8f68\u9053\u4ea4\u901a", "\u96a7\u9053|\u8f68\u9053\u4ea4\u901a|\u5730\u94c1|\u5730\u4e0b\u5de5\u7a0b"),
]

SMALL_HOTEL_MIN = 10000.0
ENTERTAIN_MIN = 500.0
PUBLIC_HEIGHT_MIN = 50.0

# ---- \u4e0d\u5408\u683c\u9879\u5e93\uff1a(\u7c7b\u522b, \u7b49\u7ea7, \u5173\u952e\u8bcd) ----
DEFECTS = [
    ("\u64c5\u81ea\u53d8\u66f4", "A", "\u64c5\u81ea\u53d8\u66f4|\u64c5\u81ea\u6539\u53d8|\u672a\u7ecf\u8bbe\u8ba1\u5ba1\u67e5|\u64c5\u81ea\u65bd\u5de5|\u4e0e\u56fe\u7eb8\u4e0d\u7b26|\u672a\u6309\u56fe\u65bd\u5de5"),
    ("\u6d88\u9632\u4ea7\u54c1\u4e0d\u7b26", "A", "\u65e0\u8ba4\u8bc1|\u8ba4\u8bc1\u4e0d\u7b26|\u7f3a\u5c11\u8ba4\u8bc1|\u4ea7\u54c1\u4e0d\u5408\u683c|\u901a\u62a5\u4e0d\u5408\u683c|\u578b\u53f7\u4e0d\u7b26"),
    ("\u7cfb\u7edf\u4e0e\u8054\u52a8", "A", "\u8054\u52a8\u5931\u6548|\u672a\u8054\u52a8|\u8054\u52a8\u672a\u5b8c\u6210|\u5207\u6362\u5931\u6548|\u672a\u5b8c\u5de5|\u7cfb\u7edf\u762b\u75ea"),
    ("\u758f\u6563\u6761\u4ef6", "A", "\u51fa\u53e3\u4e0d\u8db3|\u758f\u6563\u5bbd\u5ea6\u4e0d\u8db3|\u758f\u6563\u8ddd\u79bb\u8d85\u9650|\u901a\u9053\u5835\u585e|\u51fa\u53e3\u9501\u95ed|\u5b89\u5168\u51fa\u53e3\u88ab\u5360"),
    ("\u9632\u706b\u5206\u9694", "A", "\u9632\u706b\u5206\u533a\u8d85\u6807|\u9632\u706b\u5206\u9694\u4e0d\u5230\u4f4d|\u9632\u706b\u5c01\u5835\u7f3a\u5931|\u9632\u706b\u95e8\u7b49\u7ea7\u4e0d\u7b26|\u5377\u5e18\u4e0b\u964d\u4e0d\u5230\u4f4d"),
    ("\u88c5\u4fee\u6750\u6599", "A", "\u71c3\u70e7\u6027\u80fd\u4e0d\u8fbe\u6807|\u53ef\u71c3\u6750\u6599|\u6613\u71c3\u88c5\u4fee|\u6750\u6599\u65e0\u68c0\u6d4b"),
    ("\u603b\u5e73\u9762", "B", "\u9632\u706b\u95f4\u8ddd\u4e0d\u8db3|\u8f66\u9053\u5bbd\u5ea6\u4e0d\u8db3|\u8f66\u9053\u51c0\u9ad8\u4e0d\u8db3|\u767b\u9ad8\u573a\u5730\u88ab\u5360|\u56de\u8f66\u573a\u7f3a\u5931|\u6d88\u9632\u8f66\u9053\u88ab\u5360"),
    ("\u6c34\u7cfb\u7edf", "B", "\u6c34\u4f4d\u4e0d\u8db3|\u538b\u529b\u4e0d\u8db3|\u6d41\u91cf\u4e0d\u8db3|\u6c34\u6c60\u65e0\u6c34|\u7a33\u538b\u5f02\u5e38|\u6c34\u6cf5\u65e0\u6cd5\u542f\u52a8"),
    ("\u6d88\u9632\u4f9b\u914d\u7535", "B", "\u672a\u672b\u7aef\u5207\u6362|\u672a\u80fd\u5207\u6362|\u5907\u7528\u7535\u6e90\u4e0d\u8db3|\u8d1f\u8377\u6df7\u63a5|\u914d\u7535\u7ebf\u8def\u65e0\u4fdd\u62a4"),
    ("\u9632\u6392\u70df", "B", "\u98ce\u91cf\u4e0d\u8db3|\u4f59\u538b\u4e0d\u8db3|\u9632\u706b\u9600\u672a\u8054\u52a8|\u6392\u70df\u53e3\u88ab\u906e\u6321|\u98ce\u673a\u65e0\u6cd5\u542f\u52a8"),
    ("\u8d44\u6599\u5b8c\u6574\u6027", "C", "\u8bb0\u5f55\u7f3a\u5931|\u8d44\u6599\u7f3a\u5931|\u6863\u6848\u4e0d\u5b8c\u6574|\u65e0\u5b9e\u6d4b\u6570\u636e|\u672a\u7b7e\u5b57|\u62a5\u544a\u8fc7\u671f"),
    ("\u7ba1\u7406\u6761\u4ef6", "C", "\u65e0\u5236\u5ea6|\u65e0\u9884\u6848|\u8d23\u4efb\u4eba\u672a\u660e\u786e|\u6807\u8bc6\u7f3a\u5931|\u53f0\u8d26\u7f3a\u5931"),
]

LEVEL_ORDER = {"A": 0, "B": 1, "C": 2}

DONE_PAT = re.compile("\u5df2\u6574\u6539|\u5df2\u4fee\u590d|\u5df2\u66f4\u6362|\u5df2\u5b8c\u6210\u6574\u6539|\u5df2\u8865\u505a")
NEG_PAT = re.compile("\u672a\u6574\u6539|\u5c1a\u672a\u6574\u6539|\u672a\u4fee\u590d|\u5f85\u6574\u6539|\u5c1a\u672a\u5904\u7406|\u672a\u66f4\u6362")
DATE_PAT = re.compile(r"(20\d{2})[-./\u5e74](\d{1,2})[-./\u6708](\d{1,2})")
AREA_PAT = re.compile("(\\d+(?:\\.\\d+)?)\\s*(?:\u5e73\u65b9\u7c73|\u5e73\u7c73|m2|\u33a1)")
HEIGHT_PAT = re.compile("(?:\u5efa\u7b51\u9ad8\u5ea6|\u9ad8\u5ea6)\\D{0,4}(\\d+(?:\\.\\d+)?)\\s*(?:\u7c73|m)")
FLOOR_PAT = re.compile("(\\d+)\\s*\u5c42")


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def hit(pattern, text):
    return re.search(pattern, text) is not None


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except Exception:
        return None


def add_days(d, n):
    return d + datetime.timedelta(days=n)


def days_between(a, b):
    return (b - a).days


def judge_path(args, text):
    """\u5224\u5b9a\u7a0b\u5e8f\u8def\u5f84\uff0c\u8fd4\u56de (\u8def\u5f84, \u8bc1\u636e\u5217\u8868, \u662f\u5426\u5f85\u786e\u8ba4)"""
    evidences = []
    hits = []
    for name, pat in SPECIAL_KEYWORDS:
        if hit(pat, text):
            hits.append(name)
    if hits:
        evidences.append("\u573a\u6240\u7c7b\u578b\u547d\u4e2d\uff1a" + "\u3001".join(hits))

    areas = [float(x) for x in AREA_PAT.findall(text)]
    max_area = max(areas) if areas else 0.0
    if max_area >= SMALL_HOTEL_MIN:
        evidences.append("\u5efa\u7b51\u9762\u79ef %.0f \u5e73\u65b9\u7c73\uff0c\u8fbe\u5230\u516c\u5171\u6d3b\u52a8\u573a\u6240\u5e38\u89c1\u95e8\u69db 10000" % max_area)
    elif max_area >= ENTERTAIN_MIN:
        evidences.append("\u5efa\u7b51\u9762\u79ef %.0f \u5e73\u65b9\u7c73\uff0c\u82e5\u5c5e\u6b4c\u821e\u5a31\u4e50\u653e\u6620\u6e38\u827a\u573a\u6240\u5219\u8fbe\u5230\u5e38\u89c1\u95e8\u69db 500" % max_area)
    elif max_area > 0:
        evidences.append("\u5efa\u7b51\u9762\u79ef %.0f \u5e73\u65b9\u7c73\uff0c\u672a\u8fbe\u5e38\u89c1\u95e8\u69db" % max_area)

    heights = [float(x) for x in HEIGHT_PAT.findall(text)]
    if heights and max(heights) >= PUBLIC_HEIGHT_MIN:
        evidences.append("\u5efa\u7b51\u9ad8\u5ea6 %.1f \u7c73\uff0c\u8fbe\u5230\u516c\u5171\u5efa\u7b51\u5e38\u89c1\u95e8\u69db 50 \u7c73" % max(heights))

    if args.type == "special":
        return ("\u6d88\u9632\u9a8c\u6536", evidences + ["\u547d\u4ee4\u884c\u6307\u5b9a type=special"], False)
    if args.type == "other":
        return ("\u7ae3\u5de5\u9a8c\u6536\u6d88\u9632\u5907\u6848\u52a0\u62bd\u67e5", evidences + ["\u547d\u4ee4\u884c\u6307\u5b9a type=other"], False)

    if max_area <= 0 and not heights:
        return ("\u5f85\u786e\u8ba4", evidences + ["\u672a\u63d0\u53d6\u5230\u6709\u6548\u7684\u573a\u6240\u7c7b\u578b\u3001\u9762\u79ef\u6216\u9ad8\u5ea6\u4fe1\u606f"], True)
    if max_area >= SMALL_HOTEL_MIN:
        special = True
    elif heights and max(heights) >= PUBLIC_HEIGHT_MIN:
        special = True
    elif hits and max_area >= ENTERTAIN_MIN:
        special = True
    else:
        special = False
    path = "\u6d88\u9632\u9a8c\u6536" if special else "\u7ae3\u5de5\u9a8c\u6536\u6d88\u9632\u5907\u6848\u52a0\u62bd\u67e5"
    evidences.append("\u63a8\u5b9a\u4f9d\u636e\uff1a\u4e0a\u8ff0\u95e8\u69db\u4e3a\u5b9e\u8df5\u4e2d\u5e38\u89c1\u7406\u89e3\uff0c\u4ee5\u73b0\u884c\u89c4\u5b9a\u548c\u5f53\u5730\u4e3b\u7ba1\u90e8\u95e8\u8ba4\u5b9a\u4e3a\u51c6")
    return (path, evidences, False)


def scan_materials(text):
    out = []
    for name, pat in MATERIALS:
        ok = hit(pat, text)
        note = "" if ok else "\u672a\u68c0\u7d22\u5230\u4e0e\u8be5\u9879\u76f8\u5173\u7684\u8868\u8ff0"
        out.append((name, ("\u6709" if ok else "\u7f3a"), note))
    return out


def scan_defects(text):
    out = []
    done = bool(DONE_PAT.search(text))
    neg = bool(NEG_PAT.search(text))
    for cat, level, pat in DEFECTS:
        if hit(pat, text):
            status = "\u5df2\u6574\u6539\uff08\u987b\u6838\u5bf9\u590d\u68c0\u8bb0\u5f55\uff09" if (done and not neg) else "\u672a\u6574\u6539"
            out.append((cat, level, status))
    out.sort(key=lambda x: LEVEL_ORDER.get(x[1], 3))
    return out


def compute_deadlines(args, as_of):
    rows = []
    d = parse_date(args.accept_date)
    if d:
        due = add_days(d, 15)
        rows.append(("\u53d7\u7406\u540e\u51fa\u4ef6", str(d), "15 \u65e5\u5185", str(due), days_between(as_of, due)))
    d = parse_date(args.complete_date)
    if d:
        due = add_days(d, 5)
        rows.append(("\u7ae3\u5de5\u9a8c\u6536\u6d88\u9632\u5907\u6848", str(d), "5 \u65e5\u5185", str(due), days_between(as_of, due)))
    return rows


def build_report(args):
    text = read_text(args.file)
    as_of = parse_date(args.as_of) or datetime.date.today()
    path, evidences, pending = judge_path(args, text)
    materials = scan_materials(text)
    missing = [m[0] for m in materials if m[1] == "\u7f3a"]
    veto_missing = [m for m in missing if m in VETO]
    defects = scan_defects(text)
    deadlines = compute_deadlines(args, as_of)

    lines = []
    lines.append("# \u5efa\u8bbe\u5de5\u7a0b\u6d88\u9632\u9a8c\u6536\u6750\u6599\u6838\u67e5\u7ed3\u679c")
    lines.append("")
    lines.append("\u6838\u67e5\u57fa\u51c6\u65e5\uff1a" + str(as_of))
    lines.append("")
    lines.append("## \u4e00\u3001\u7a0b\u5e8f\u8def\u5f84")
    lines.append("")
    lines.append("**\u5224\u5b9a\u7ed3\u679c\uff1a" + path + "**")
    lines.append("")
    for e in evidences:
        lines.append("- " + e)
    if pending:
        lines.append("")
        lines.append("> \u8bc1\u636e\u4e0d\u8db3\uff0c\u672a\u4e0b\u7ed3\u8bba\u3002\u5efa\u8bae\u6309\u6d88\u9632\u9a8c\u6536\u6807\u51c6\u51c6\u5907\u6750\u6599\uff0c\u5e76\u5411\u4e3b\u7ba1\u90e8\u95e8\u7a97\u53e3\u786e\u8ba4\u3002")
    lines.append("")
    lines.append("## \u4e8c\u300115 \u9879\u6750\u6599\u6838\u67e5")
    lines.append("")
    lines.append("| # | \u6750\u6599 | \u72b6\u6001 | \u8bf4\u660e |")
    lines.append("|---|---|---|---|")
    for i, (name, st, note) in enumerate(materials, 1):
        mark = "\uff08\u4e00\u7968\u5426\u51b3\uff09" if name in VETO else ""
        lines.append("| %d | %s%s | %s | %s |" % (i, name, mark, st, note))
    lines.append("")
    lines.append("\u7f3a\u5931\u9879\uff1a" + ("\u3001".join(missing) if missing else "\u65e0"))
    if veto_missing:
        lines.append("")
        lines.append("**\u5b58\u5728\u4e00\u7968\u5426\u51b3\u6750\u6599\u7f3a\u5931\uff1a" + "\u3001".join(veto_missing) + "\u3002\u8fd9\u4e09\u9879\u4e0d\u9f50\uff0c\u5176\u4f59\u6750\u6599\u518d\u5168\u4e5f\u63a8\u8fdb\u4e0d\u52a8\u3002**")
    lines.append("")
    lines.append("## \u4e09\u3001\u4e0d\u5408\u683c\u9879")
    lines.append("")
    if defects:
        lines.append("| \u5e8f\u53f7 | \u7c7b\u522b | \u7b49\u7ea7 | \u72b6\u6001 |")
        lines.append("|---|---|---|---|")
        for i, (cat, lv, st) in enumerate(defects, 1):
            lines.append("| %d | %s | %s | %s |" % (i, cat, lv, st))
        lines.append("")
        lines.append("\u6574\u6539\u987a\u5e8f\uff1aA \u7c7b\u4f18\u5148\uff1b\u540c\u7c7b\u6309\u300c\u5148\u758f\u6563\u4e0e\u8054\u52a8\uff0c\u540e\u8bbe\u5907\u4e0e\u8d44\u6599\u300d\u63a8\u8fdb\u3002")
    else:
        lines.append("\u672a\u68c0\u7d22\u5230\u4e0d\u5408\u683c\u9879\u8868\u8ff0\u3002**\u672a\u68c0\u7d22\u5230\u4e0d\u7b49\u4e8e\u6ca1\u6709\u95ee\u9898**\uff0c\u987b\u4eba\u5de5\u7ffb\u5230\u6574\u4efd\u8d44\u6599\u6838\u5bf9\u3002")
    if deadlines:
        lines.append("")
        lines.append("## \u56db\u3001\u671f\u9650")
        lines.append("")
        lines.append("| \u4e8b\u9879 | \u8d77\u7b97\u65e5 | \u671f\u9650 | \u622a\u6b62\u65e5 | \u8ddd\u57fa\u51c6\u65e5 |")
        lines.append("|---|---|---|---|---|")
        for name, start, limit, end, left in deadlines:
            lines.append("| %s | %s | %s | %s | %d \u5929 |" % (name, start, limit, end, left))
    lines.append("")
    lines.append("## \u4e94\u3001\u5907\u6ce8")
    lines.append("")
    lines.append("- \u811a\u672c\u53ea\u505a\u5173\u952e\u8bcd\u5339\u914d\uff0c\u4e0d\u4ee3\u8868\u5de5\u7a0b\u5224\u65ad\u3002\u6807\u300c\u6709\u300d\u4e0d\u7b49\u4e8e\u8be5\u9879\u771f\u7684\u7b26\u5408\u8981\u6c42\u3002")
    lines.append("- \u671f\u9650\u53e3\u5f84\u4e3a\u5b9e\u8df5\u4e2d\u5e38\u89c1\u7406\u89e3\uff0c\u4ee5\u73b0\u884c\u89c4\u5b9a\u548c\u5f53\u5730\u4e3b\u7ba1\u90e8\u95e8\u8981\u6c42\u4e3a\u51c6\u3002")
    lines.append("- \u4e0d\u5f97\u7528\u4e8e\u4fee\u6539\u3001\u5012\u7b7e\u3001\u4f2a\u9020\u7533\u62a5\u6750\u6599\u3001\u9690\u853d\u5de5\u7a0b\u8bb0\u5f55\u6216\u68c0\u6d4b\u62a5\u544a\u3002")
    return "\n".join(lines)


def selftest():
    fails = []

    def check(cond, msg):
        if not cond:
            fails.append(msg)

    args_auto = argparse.Namespace(type="auto")

    # \u7528\u4f8b 1\uff1a\u6750\u6599\u9f50\u5168\u7684\u5927\u578b\u5546\u573a\u9879\u76ee\uff0c\u5e94\u5224\u4e3a\u6d88\u9632\u9a8c\u6536\u4e14\u6750\u6599\u65e0\u7f3a\u5931
    t1 = "\n".join([
        "\u67d0\u67d0\u5546\u573a\u5efa\u8bbe\u5de5\u7a0b", "\u5efa\u7b51\u9762\u79ef 12000 \u5e73\u65b9\u7c73", "\u5730\u4e0a 5 \u5c42",
        "\u5df2\u53d6\u5f97\u5efa\u8bbe\u5de5\u7a0b\u6d88\u9632\u8bbe\u8ba1\u5ba1\u67e5\u610f\u89c1\u4e66", "\u7ae3\u5de5\u56fe\u7eb8\u9f50\u5168", "\u6d88\u9632\u8bbe\u65bd\u68c0\u6d4b\u5408\u683c\u62a5\u544a\u5df2\u51fa\u5177",
        "\u7ae3\u5de5\u9a8c\u6536\u62a5\u544a\u5df2\u51fa\u5177", "\u7533\u8bf7\u8868\u5df2\u63d0\u4ea4", "\u9690\u853d\u5de5\u7a0b\u9a8c\u6536\u8bb0\u5f55\u5b8c\u6574",
        "\u8054\u52a8\u8bd5\u9a8c\u8bb0\u5f55\u5b8c\u6574", "\u6d88\u9632\u4ea7\u54c1\u5408\u683c\u8bc1\u9f50\u5168", "\u71c3\u70e7\u6027\u80fd\u68c0\u6d4b\u62a5\u544a\u9f50\u5168",
        "\u65bd\u5de5\u5355\u4f4d\u8d44\u8d28\u8bc1\u660e\u9f50\u5168", "\u5efa\u8bbe\u5355\u4f4d\u8425\u4e1a\u6267\u7167", "\u89c4\u5212\u8bb8\u53ef\u4e0e\u65bd\u5de5\u8bb8\u53ef\u9f50\u5168",
        "\u8bbe\u8ba1\u53d8\u66f4\u5df2\u5b8c\u6210\u6280\u672f\u590d\u6838", "\u6d88\u9632\u5b89\u5168\u7ba1\u7406\u5236\u5ea6\u4e0e\u5e94\u6025\u758f\u6563\u9884\u6848\u9f50\u5168",
        "\u4e13\u5bb6\u8bc4\u5ba1\u610f\u89c1\u5df2\u843d\u5b9e",
    ])
    path1, ev1, pend1 = judge_path(args_auto, t1)
    check(path1 == "\u6d88\u9632\u9a8c\u6536", "\u7528\u4f8b1 \u5e94\u5224\u4e3a\u6d88\u9632\u9a8c\u6536\uff0c\u5b9e\u9645\uff1a" + path1)
    check(not pend1, "\u7528\u4f8b1 \u4e0d\u5e94\u4e3a\u5f85\u786e\u8ba4")
    miss1 = [x[0] for x in scan_materials(t1) if x[1] == "\u7f3a"]
    check(miss1 == [], "\u7528\u4f8b1 \u6750\u6599\u5e94\u9f50\u5168\uff0c\u7f3a\uff1a" + str(miss1))

    # \u7528\u4f8b 2\uff1a350 \u5e73\u65b9\u7c73\u7684\u5355\u5c42\u666e\u901a\u9879\u76ee\uff0c\u65e0\u573a\u6240\u7c7b\u578b\u547d\u4e2d\uff0c\u5e94\u8d70\u5907\u6848\u62bd\u67e5
    t2 = "\n".join([
        "\u67d0\u67d0\u6751\u96c6\u4f53\u5de5\u5177\u623f\u65b0\u5efa\u5de5\u7a0b", "\u5efa\u7b51\u9762\u79ef 350 \u5e73\u65b9\u7c73", "\u5730\u4e0a 1 \u5c42",
        "\u7ae3\u5de5\u9a8c\u6536\u5408\u683c", "\u7533\u8bf7\u8868\u5df2\u63d0\u4ea4", "\u7ae3\u5de5\u9a8c\u6536\u62a5\u544a\u5df2\u51fa\u5177",
    ])
    path2, ev2, pend2 = judge_path(args_auto, t2)
    check(path2 == "\u7ae3\u5de5\u9a8c\u6536\u6d88\u9632\u5907\u6848\u52a0\u62bd\u67e5", "\u7528\u4f8b2 \u5e94\u8d70\u5907\u6848\u62bd\u67e5\uff0c\u5b9e\u9645\uff1a" + path2)

    # \u7528\u4f8b 3\uff1a\u53ea\u63d0\u4ea4\u4e86\u7533\u8bf7\u8868\u7684\u60c5\u5f62\uff0c\u5e94\u8bc6\u522b\u51fa\u4e09\u4e2a\u4e00\u7968\u5426\u51b3\u6750\u6599\u7f3a\u5931
    t3 = "\u67d0\u67d0\u529e\u516c\u697c\u88c5\u4fee\u6539\u9020\u5de5\u7a0b\uff0c\u5efa\u7b51\u9762\u79ef 800 \u5e73\u65b9\u7c73\uff0c\u7533\u8bf7\u8868\u5df2\u63d0\u4ea4\uff0c\u7ae3\u5de5\u9a8c\u6536\u62a5\u544a\u5df2\u51fa\u5177"
    miss3 = set(x[0] for x in scan_materials(t3) if x[1] == "\u7f3a")
    for item in VETO:
        check(item in miss3, "\u7528\u4f8b3 \u5e94\u8bc6\u522b\u51fa\u7f3a\uff1a" + item + "\uff0c\u5b9e\u9645\u7f3a\uff1a" + str(sorted(miss3)))

    # \u7528\u4f8b 4\uff1a\u671f\u9650\u8ba1\u7b97
    check(str(add_days(parse_date("2026-10-01"), 15)) == "2026-10-16", "\u7528\u4f8b4 \u53d7\u7406\u540e 15 \u65e5\u622a\u6b62\u65e5\u8ba1\u7b97\u9519\u8bef")
    check(str(add_days(parse_date("2026-10-01"), 5)) == "2026-10-06", "\u7528\u4f8b4 \u5907\u6848 5 \u65e5\u7a97\u53e3\u8ba1\u7b97\u9519\u8bef")
    check(days_between(parse_date("2026-10-01"), parse_date("2026-10-16")) == 15, "\u7528\u4f8b4 \u5929\u6570\u5dee\u8ba1\u7b97\u9519\u8bef")

    # \u7528\u4f8b 5\uff1a\u4e0d\u5408\u683c\u9879\u5206\u7ea7\uff0c\u4e14\u542b\u5426\u5b9a\u8bcd\u65f6\u5e94\u5168\u90e8\u8bb0\u4e3a\u672a\u6574\u6539
    t5 = "\u64c5\u81ea\u53d8\u66f4\u5e73\u9762\u5e03\u5c40\uff0c\u9632\u706b\u5206\u533a\u8d85\u6807\uff0c\u758f\u6563\u901a\u9053\u5835\u585e\uff0c\u6d88\u9632\u8f66\u9053\u5bbd\u5ea6\u4e0d\u8db3\uff0c\u6d88\u9632\u6c34\u6c60\u6c34\u4f4d\u4e0d\u8db3\uff0c\u65bd\u5de5\u8bb0\u5f55\u7f3a\u5931\uff0c\u4e0a\u8ff0\u4e8b\u9879\u5c1a\u672a\u6574\u6539"
    dd = scan_defects(t5)
    check(len(dd) > 0, "\u7528\u4f8b5 \u5e94\u62bd\u5230\u4e0d\u5408\u683c\u9879")
    check(dd[0][1] == "A", "\u7528\u4f8b5 \u6700\u9ad8\u7b49\u7ea7\u5e94\u4e3a A\uff0c\u5b9e\u9645\uff1a" + dd[0][1])
    check(all(x[2] == "\u672a\u6574\u6539" for x in dd), "\u7528\u4f8b5 \u542b\u672a\u6574\u6539\u8868\u8ff0\u65f6\u5e94\u5168\u90e8\u8bb0\u4e3a\u672a\u6574\u6539\uff0c\u5b9e\u9645\uff1a" + str(dd))
    cats = [x[0] for x in dd]
    for c in ["\u64c5\u81ea\u53d8\u66f4", "\u9632\u706b\u5206\u9694", "\u758f\u6563\u6761\u4ef6", "\u603b\u5e73\u9762", "\u6c34\u7cfb\u7edf", "\u8d44\u6599\u5b8c\u6574\u6027"]:
        check(c in cats, "\u7528\u4f8b5 \u5e94\u547d\u4e2d\u7c7b\u522b\uff1a" + c + "\uff0c\u5b9e\u9645\uff1a" + str(cats))

    # \u7528\u4f8b 6\uff1a\u540c\u65f6\u51fa\u73b0\u5df2\u6574\u6539\u4e0e\u672a\u6574\u6539\u65f6\uff0c\u4e0d\u5f97\u6309\u6574\u6539\u4e3a\u5df2\u5b8c\u6210
    t6 = "\u9632\u706b\u5206\u533a\u8d85\u6807\u5df2\u6574\u6539\uff1b\u758f\u6563\u901a\u9053\u5835\u585e\u5c1a\u672a\u6574\u6539"
    dd6 = scan_defects(t6)
    check(all(x[2] == "\u672a\u6574\u6539" for x in dd6), "\u7528\u4f8b6 \u5b58\u5728\u5c1a\u672a\u6574\u6539\u9879\u65f6\u4e0d\u5e94\u8bb0\u4e3a\u5df2\u6574\u6539\uff0c\u5b9e\u9645\uff1a" + str(dd6))

    # \u7528\u4f8b 7\uff1a\u4fe1\u606f\u4e0d\u8db3\u5e94\u5224\u4e3a\u5f85\u786e\u8ba4
    path7, ev7, pend7 = judge_path(args_auto, "\u67d0\u67d0\u5de5\u7a0b")
    check(path7 == "\u5f85\u786e\u8ba4" and pend7, "\u7528\u4f8b7 \u4fe1\u606f\u4e0d\u8db3\u65f6\u5e94\u4e3a\u5f85\u786e\u8ba4\uff0c\u5b9e\u9645\uff1a" + path7)

    lines = []
    if fails:
        lines.append("SELFTEST FAILED")
        for f in fails:
            lines.append(" - " + f)
    else:
        lines.append("SELFTEST OK")
        lines.append("\u65ad\u8a00\u7ec4\u6570\uff1a7")
        lines.append("\u8986\u76d6\uff1a\u7a0b\u5e8f\u8def\u5f84\u5224\u5b9a 3 \u7ec4\u3001\u6750\u6599\u7f3a\u5931\u4e0e\u4e00\u7968\u5426\u51b3\u8bc6\u522b\u3001\u671f\u9650\u8ba1\u7b97\u3001\u7f3a\u9677\u5206\u7ea7\u3001\u5426\u5b9a\u8bcd\u4fdd\u7559\u3001\u4fe1\u606f\u4e0d\u8db3\u63d0\u793a")
    return "\n".join(lines), len(fails)


def write_out(path, content):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main(argv=None):
    ap = argparse.ArgumentParser(description="\u5efa\u8bbe\u5de5\u7a0b\u6d88\u9632\u9a8c\u6536\u6750\u6599\u6838\u67e5")
    ap.add_argument("--file", help="\u9879\u76ee\u60c5\u51b5\u8bf4\u660e\u6216\u6750\u6599\u6e05\u5355\u6587\u672c\u6587\u4ef6")
    ap.add_argument("--as-of", help="\u6838\u67e5\u57fa\u51c6\u65e5 YYYY-MM-DD\uff0c\u9ed8\u8ba4\u4eca\u5929")
    ap.add_argument("--accept-date", help="\u53d7\u7406\u65e5\u671f YYYY-MM-DD")
    ap.add_argument("--complete-date", help="\u7ae3\u5de5\u9a8c\u6536\u5408\u683c\u65e5\u671f YYYY-MM-DD")
    ap.add_argument("--type", default="auto", choices=["auto", "special", "other"])
    ap.add_argument("--out", help="\u8f93\u51fa\u6587\u4ef6\u8def\u5f84")
    ap.add_argument("--format", default="md", choices=["md", "json"])
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    result_file = os.path.join(here, "_selftest_result.txt")

    if args.selftest:
        report, nfail = selftest()
        write_out(result_file, report + "\n")
        sys.stderr.write(report + "\n")
        return 0 if nfail == 0 else 1

    if not args.file:
        msg = "\u7f3a\u5c11 --file \u53c2\u6570\uff0c\u793a\u4f8b\uff1apython acceptance_check.py --file \u9879\u76ee\u60c5\u51b5.txt"
        write_out(result_file, msg + "\n")
        sys.stderr.write(msg + "\n")
        return 2
    if not os.path.exists(args.file):
        msg = "\u6587\u4ef6\u4e0d\u5b58\u5728\uff1a" + args.file
        write_out(result_file, msg + "\n")
        sys.stderr.write(msg + "\n")
        return 2

    md = build_report(args)
    if args.format == "json":
        text = read_text(args.file)
        as_of = parse_date(args.as_of) or datetime.date.today()
        path, evidences, pending = judge_path(args, text)
        data = {
            "as_of": str(as_of),
            "path": path,
            "pending": pending,
            "evidences": evidences,
            "materials": [
                {"name": n, "status": s, "veto": n in VETO, "note": t}
                for n, s, t in scan_materials(text)
            ],
            "defects": [
                {"category": c, "level": l, "status": s}
                for c, l, s in scan_defects(text)
            ],
            "deadlines": [
                {"item": a, "start": b, "limit": c, "due": d, "days_left": e}
                for a, b, c, d, e in compute_deadlines(args, as_of)
            ],
        }
        out = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        out = md

    if args.out:
        write_out(args.out, out + "\n")
    write_out(result_file, (json.dumps(data, ensure_ascii=False, indent=2)[:2000] if args.format == "json" else md) + "\n")
    sys.stderr.write("\u7ed3\u679c\u5df2\u5199\u5165\uff1a" + (args.out or result_file) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
