# -*- coding: utf-8 -*-
"""\u5c45\u4f4f\u8bc1\u7533\u529e\u3001\u7b7e\u6ce8\u4e0e\u79ef\u5206\u6838\u67e5\u3002

\u7528\u6cd5:
  python residence_permit_check.py --file \u60c5\u51b5\u8bf4\u660e.txt --register-date 2026-01-15 --as-of 2026-10-08
  python residence_permit_check.py --selftest
"""
import argparse
import datetime
import json
import os
import re
import sys

# ---- \u4e09\u6761\u7533\u529e\u8def\u5f84\u53ca\u5176\u5173\u952e\u8bcd ----
PATHS = [
    ("\u5408\u6cd5\u7a33\u5b9a\u5c31\u4e1a", "\u52b3\u52a8\u5408\u540c|\u52b3\u52a1\u5408\u540c|\u7528\u4eba\u5355\u4f4d|\u793e\u4fdd|\u8425\u4e1a\u6267\u7167|\u7528\u5de5|\u4efb\u804c|\u5de5\u8d44|\u5c31\u4e1a\u8bc1\u660e"),
    ("\u5408\u6cd5\u7a33\u5b9a\u4f4f\u6240", "\u79df\u8d41\u5408\u540c|\u79df\u623f|\u623f\u4ea7\u8bc1|\u623f\u5c4b\u4ea7\u6743|\u8d2d\u623f\u5408\u540c|\u5b89\u7f6e\u623f|\u81ea\u8d2d|\u4f4f\u5bbf\u8bc1\u660e|\u623f\u4e1c|\u51fa\u79df\u4eba"),
    ("\u8fde\u7eed\u5c31\u8bfb", "\u5b66\u751f\u8bc1|\u5c31\u8bfb|\u5b66\u7c4d|\u5f55\u53d6\u901a\u77e5|\u5728\u8bfb\u8bc1\u660e|\u5b66\u6821"),
]

# ---- \u901a\u7528\u6750\u6599\u6e05\u5355 ----
MATERIALS = [
    ("\u672c\u4eba\u5c45\u6c11\u8eab\u4efd\u8bc1", "\u8eab\u4efd\u8bc1|\u5c45\u6c11\u8eab\u4efd\u8bc1\u660e|\u4e8c\u4ee3\u8bc1"),
    ("\u8fd1\u671f\u514d\u51a0\u7167\u7247", "\u7167\u7247|\u514d\u51a0|\u76f8\u7247|\u4eba\u50cf\u91c7\u96c6"),
    ("\u5c45\u4f4f\u5730\u4f4f\u5740\u8bc1\u660e", "\u4f4f\u5740\u8bc1\u660e|\u79df\u8d41\u5408\u540c|\u623f\u4ea7\u8bc1|\u623f\u5c4b\u4ea7\u6743|\u8d2d\u623f\u5408\u540c|\u4f4f\u5bbf\u8bc1\u660e"),
    ("\u5c31\u4e1a\u6216\u5c31\u8bfb\u8bc1\u660e\u6750\u6599", "\u52b3\u52a8\u5408\u540c|\u8425\u4e1a\u6267\u7167|\u52b3\u52a8\u5173\u7cfb\u8bc1\u660e|\u5b66\u751f\u8bc1|\u5c31\u8bfb\u8bc1\u660e|\u5b66\u7c4d\u8bc1\u660e"),
    ("\u5c45\u4f4f\u767b\u8bb0\u51ed\u8bc1", "\u5c45\u4f4f\u767b\u8bb0|\u767b\u8bb0\u56de\u6267|\u767b\u8bb0\u51ed\u8bc1|\u53d7\u7406\u544a\u77e5\u5355|\u767b\u8bb0\u7c3f"),
    ("\u4ee3\u529e\u4eba\u4e0e\u59d4\u6258\u4e66\uff08\u5982\u4ee3\u529e\uff09", "\u59d4\u6258\u4e66|\u4ee3\u529e|\u76d1\u62a4\u4eba"),
]

# ---- \u4e0d\u4e88\u53d7\u7406 / \u5e38\u89c1\u9000\u56de\u60c5\u5f62 ----
BLOCKERS = [
    ("\u672a\u6ee116\u5468\u5c81\u672a\u7531\u76d1\u62a4\u4eba\u4ee3\u529e", "\u672a\u6ee116\u5468\u5c81|\u672a\u6ee1\u5341\u516d\u5468\u5c81|\u672a\u6210\u5e74|\u5c0f\u5b66\u751f|\u521d\u4e2d\u751f"),
    ("\u6750\u6599\u4e0d\u9f50\u6216\u590d\u5370\u4ef6\u4e0d\u6e05\u6670", "\u6750\u6599\u4e0d\u9f50|\u590d\u5370\u4ef6\u4e0d\u6e05|\u7f3a\u6750\u6599|\u906e\u6321|\u6a21\u7cca"),
    ("\u767b\u8bb0\u5730\u5740\u4e0e\u5b9e\u9645\u5c45\u4f4f\u5730\u4e0d\u4e00\u81f4", "\u5730\u5740\u4e0d\u4e00\u81f4|\u4f4f\u6240\u4e0d\u7b26|\u5730\u5740\u4e0d\u5b9e|\u4e0d\u5728\u8f96\u533a"),
    ("\u5c45\u4f4f\u767b\u8bb0\u672a\u529e\u6216\u672a\u6ee1\u89c4\u5b9a\u671f\u9650", "\u672a\u767b\u8bb0|\u6ca1\u6709\u767b\u8bb0|\u521a\u767b\u8bb0|\u767b\u8bb0\u672a\u6ee1"),
    ("\u4ee3\u529e\u7f3a\u59d4\u6258\u4e66\u6216\u4ee3\u529e\u4eba\u8eab\u4efd\u8bc1\u4ef6", "\u65e0\u59d4\u6258\u4e66|\u7f3a\u5c11\u4ee3\u529e\u4eba|\u4ee3\u529e\u672a"),
]

# ---- \u79ef\u5206\u5e38\u89c1\u7ef4\u5ea6\uff08\u5206\u503c\u56e0\u5730\u800c\u5f02\uff0c\u53ea\u6838\u67e5\u6750\u6599\u6709\u6ca1\u6709\u8986\u76d6\uff09----
POINT_DIMS = [
    ("\u5e74\u9f84", "\u5e74\u9f84|\u51fa\u751f|\u5468\u5c81"),
    ("\u5b66\u5386\u6280\u80fd\u6c34\u5e73", "\u5b66\u5386|\u5927\u4e13|\u672c\u79d1|\u7814\u7a76\u751f|\u5b66\u4f4d|\u804c\u4e1a\u8d44\u683c|\u6280\u80fd\u7b49\u7ea7|\u804c\u79f0"),
    ("\u793e\u4f1a\u4fdd\u9669\u7f34\u8d39\u5e74\u9650", "\u793e\u4fdd|\u793e\u4f1a\u4fdd\u9669|\u517b\u8001\u4fdd\u9669|\u7f34\u8d39\u5e74\u9650|\u53c2\u4fdd"),
    ("\u4f4f\u623f\u60c5\u51b5", "\u623f\u4ea7|\u81ea\u8d2d|\u4f4f\u623f|\u79df\u623f\u5907\u6848|\u516c\u79ef\u91d1"),
    ("\u5c45\u4f4f\u5e74\u9650", "\u5c45\u4f4f\u5e74\u9650|\u8fde\u7eed\u5c45\u4f4f|\u767b\u8bb0\u5e74\u9650|\u6682\u4f4f"),
    ("\u804c\u4e1a\u4e0e\u884c\u4e1a\u7d27\u7f3a\u76ee\u5f55", "\u7d27\u7f3a\u804c\u4e1a|\u7d27\u7f3a\u5de5\u79cd|\u804c\u4e1a\u76ee\u5f55|\u884c\u4e1a\u76ee\u5f55"),
    ("\u6295\u8d44\u7eb3\u7a0e", "\u7eb3\u7a0e|\u4e2a\u7a0e|\u6295\u8d44|\u7f34\u7a0e"),
    ("\u8868\u5f70\u5956\u52b1\u4e0e\u5fd7\u613f\u670d\u52a1", "\u8868\u5f70|\u5956\u52b1|\u8363\u8a89|\u5fd7\u613f\u8005|\u5fd7\u613f\u670d\u52a1|\u65e0\u507f\u732e\u8840|\u6350\u732e"),
]

DATE_PAT = re.compile(r"(20\d{2})[\-\./](\d{1,2})[\-\./](\d{1,2})")


def norm(s):
    return (s or "").replace(" ", "").replace("\u3000", "")


def add_months(d, n):
    y = d.year + (d.month - 1 + n) // 12
    m = (d.month - 1 + n) % 12 + 1
    day = d.day
    while True:
        try:
            return datetime.date(y, m, day)
        except ValueError:
            day -= 1


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


def pick_path(text):
    t = norm(text)
    hits = []
    for name, pat in PATHS:
        if re.search(pat, t):
            hits.append(name)
    return hits


AGENT_PAT = "\u59d4\u6258\u4e66|\u4ee3\u529e|\u76d1\u62a4\u4eba|\u59d4\u6258\u4ed6\u4eba"


def check_materials(text):
    t = norm(text)
    out = []
    for name, pat in MATERIALS:
        if name.startswith("\u4ee3\u529e"):
            st = "\u5f85\u6838" if re.search(AGENT_PAT, t) else "\u4e0d\u6d89\u53ca\uff08\u81ea\u529e\uff09"
        else:
            st = "\u9f50\u5907" if re.search(pat, t) else "\u7f3a\u5931"
        out.append((name, st))
    return out


def check_blockers(text):
    t = norm(text)
    out = []
    for name, pat in BLOCKERS:
        if re.search(pat, t):
            out.append(name)
    return out


def check_points(text):
    t = norm(text)
    out = []
    for name, pat in POINT_DIMS:
        out.append((name, "\u6709\u6750\u6599" if re.search(pat, t) else "\u672a\u89c1\u6750\u6599"))
    return out


def residence_gate(reg_date, as_of):
    """\u5c45\u4f4f\u767b\u8bb0\u8d77\u7b97\uff1a\u6ee1\u8db3\u300e\u5c45\u4f4f\u534a\u5e74\u4ee5\u4e0a\u300f\u7684\u6700\u65e9\u53ef\u7533\u9886\u65e5\uff08\u6309\u767b\u8bb0\u6ee1 6 \u4e2a\u6708\u638c\u63e1\uff09\u3002"""
    if reg_date is None:
        return None
    eligible = add_months(reg_date, 6)
    waited = (as_of - reg_date).days
    remain = (eligible - as_of).days
    return reg_date, eligible, waited, remain


def endorsement_state(issue_date, as_of):
    """\u7b7e\u6ce8\uff1a\u6bcf\u5e74\u7b7e\u6ce8 1 \u6b21\uff0c\u5c45\u4f4f\u6bcf\u6ee1 1 \u5e74\u4e4b\u65e5\u524d 1 \u4e2a\u6708\u5185\u529e\u7406\u3002"""
    if issue_date is None:
        return None
    due = add_years(issue_date, 1)
    window_start = add_months(due, -1)
    remain = (due - as_of).days
    if as_of < window_start:
        stage = "\u672a\u5230\u7b7e\u6ce8\u671f"
    elif as_of <= due:
        stage = "\u7b7e\u6ce8\u7a97\u53e3\u671f"
    else:
        stage = "\u5df2\u903e\u671f"
    return issue_date, due, window_start, remain, stage


def render_md(text, as_of, reg_date=None, issue_date=None):
    lines = ["# \u5c45\u4f4f\u8bc1\u7533\u529e\u4e0e\u7b7e\u6ce8\u6838\u67e5\u7ed3\u679c", ""]
    lines.append("\u6838\u67e5\u57fa\u51c6\u65e5\uff1a%s" % as_of.isoformat())
    lines.append("")

    lines.append("## \u4e00\u3001\u7533\u529e\u8def\u5f84")
    lines.append("")
    paths = pick_path(text)
    if paths:
        lines.append("\u547d\u4e2d\u8def\u5f84\uff1a%s" % "\u3001".join(paths))
        lines.append("")
        lines.append("\u4e09\u6761\u8def\u5f84\u7b26\u5408\u5176\u4e00\u5373\u53ef\u7533\u9886\uff08\u4ee5\u5f53\u5730\u516c\u5b89\u6d3e\u51fa\u6240\u53e3\u5f84\u4e3a\u51c6\uff09\u3002")
    else:
        lines.append("\u672a\u547d\u4e2d\u4efb\u4f55\u4e00\u6761\u7533\u529e\u8def\u5f84\uff1a\u672a\u5728\u6587\u672c\u4e2d\u89c1\u5230\u5c31\u4e1a\u3001\u4f4f\u6240\u6216\u8fde\u7eed\u5c31\u8bfb\u7684\u8bc1\u660e\u6750\u6599\u3002")
        lines.append("\u672a\u89c1\u6709\u6548\u7acb\u8db3\u70b9\u65f6\uff0c\u4e0d\u5e94\u5047\u8bbe\u53ef\u4ee5\u300e\u5148\u529e\u518d\u8bf4\u300f\u3002")
    lines.append("")

    lines.append("## \u4e8c\u3001\u6750\u6599\u6e05\u5355\u6838\u67e5")
    lines.append("")
    lines.append("| # | \u6750\u6599 | \u72b6\u6001 |")
    lines.append("|---|---|---|")
    mats = check_materials(text)
    for i, (n, st) in enumerate(mats, 1):
        lines.append("| %d | %s | %s |" % (i, n, st))
    miss = [n for n, st in mats if st == "\u7f3a\u5931"]
    lines.append("")
    lines.append("\u7f3a\u5931\u6750\u6599\uff1a%s" % ("\u3001".join(miss) if miss else "\u65e0"))
    lines.append("")

    lines.append("## \u4e09\u3001\u4e0d\u4e88\u53d7\u7406\u4e0e\u9000\u56de\u98ce\u9669")
    lines.append("")
    blk = check_blockers(text)
    if blk:
        for b in blk:
            lines.append("- \u547d\u4e2d\u9000\u56de\u60c5\u5f62\uff1a%s" % b)
    else:
        lines.append("- \u672a\u547d\u4e2d\u5e38\u89c1\u9000\u56de\u60c5\u5f62\uff08\u4ecd\u9700\u4eba\u5de5\u590d\u6838\uff09")
    lines.append("")

    lines.append("## \u56db\u3001\u5c45\u4f4f\u767b\u8bb0\u534a\u5e74\u95e8\u69db")
    lines.append("")
    g = residence_gate(reg_date, as_of)
    if g is None:
        lines.append("\u672a\u63d0\u4f9b\u5c45\u4f4f\u767b\u8bb0\u65e5\u671f\uff0c\u65e0\u6cd5\u8ba1\u7b97\u534a\u5e74\u95e8\u69db\u3002\u53ef\u7528 --register-date \u6307\u5b9a\u3002")
    else:
        rd, elig, waited, remain = g
        lines.append("- \u5c45\u4f4f\u767b\u8bb0\u65e5\u671f\uff1a%s" % rd.isoformat())
        lines.append("- \u6309\u767b\u8bb0\u6ee1 6 \u4e2a\u6708\u638c\u63e1\uff0c\u6700\u65e9\u53ef\u7533\u9886\u65e5\uff1a%s" % elig.isoformat())
        lines.append("- \u5df2\u767b\u8bb0 %d \u5929" % waited)
        if remain > 0:
            lines.append("- \u8ddd\u53ef\u7533\u9886\u8fd8\u5dee %d \u5929\uff0c\u6b64\u671f\u95f4\u63d0\u4ea4\u5927\u6982\u7387\u88ab\u9000\u56de\u3002" % remain)
        else:
            lines.append("- \u5df2\u6ee1\u8db3\u534a\u5e74\u7ea7\u522b\u8981\u6c42\uff08%d \u5929\u524d\u8fbe\u5230\uff09\u3002" % abs(remain))
        lines.append("- \u672a\u6ee1\u534a\u5e74\u4f46\u80fd\u8bc1\u660e\u9884\u671f\u5c45\u4f4f\u534a\u5e74\u4ee5\u4e0a\uff08\u5982 1 \u5e74\u671f\u4ee5\u4e0a\u52b3\u52a8\u5408\u540c\u3001\u79df\u8d41\u5408\u540c\uff09\u7684\uff0c\u80fd\u5426\u53d7\u7406\u4ee5\u5f53\u5730\u6d3e\u51fa\u6240\u7b54\u590d\u4e3a\u51c6\u3002")
    lines.append("")

    lines.append("## \u4e94\u3001\u7b7e\u6ce8\u72b6\u6001")
    lines.append("")
    e = endorsement_state(issue_date, as_of)
    if e is None:
        lines.append("\u672a\u63d0\u4f9b\u53d1\u8bc1\u65e5\u671f\uff0c\u65e0\u6cd5\u5224\u65ad\u7b7e\u6ce8\u671f\u3002\u53ef\u7528 --issue-date \u6307\u5b9a\u3002")
    else:
        iss, due, ws, remain, stage = e
        lines.append("- \u53d1\u8bc1/\u4e0a\u6b21\u7b7e\u6ce8\u65e5\u671f\uff1a%s" % iss.isoformat())
        lines.append("- \u672c\u6b21\u7b7e\u6ce8\u5230\u671f\u65e5\uff1a%s" % due.isoformat())
        lines.append("- \u5efa\u8bae\u529e\u7406\u7a97\u53e3\uff1a%s \u8d77\u4e00\u4e2a\u6708\u5185" % ws.isoformat())
        lines.append("- \u5f53\u524d\u72b6\u6001\uff1a%s\uff08\u8ddd\u5230\u671f %d \u5929\uff09" % (stage, remain))
        if stage == "\u5df2\u903e\u671f":
            lines.append("- **\u5df2\u903e\u671f**\uff1a\u903e\u671f\u672a\u529e\u7b7e\u6ce8\u7684\uff0c\u5c45\u4f4f\u8bc1\u4f7f\u7528\u529f\u80fd\u4e2d\u6b62\uff1b\u8865\u529e\u7b7e\u6ce8\u540e\u6062\u590d\u529f\u80fd\u3002\u529e\u7406\u65f6\u540c\u6b65\u786e\u8ba4\u5f53\u5730\u662f\u5426\u5141\u8bb8\u7ebf\u4e0a\u8865\u7b7e\u6ce8\u3002")
    lines.append("")

    lines.append("## \u516d\u3001\u79ef\u5206\u6750\u6599\u8986\u76d6\u5ea6")
    lines.append("")
    lines.append("| # | \u7ef4\u5ea6 | \u6750\u6599\u60c5\u51b5 |")
    lines.append("|---|---|---|")
    for i, (n, st) in enumerate(check_points(text), 1):
        lines.append("| %d | %s | %s |" % (i, n, st))
    lines.append("")
    lines.append("> \u5404\u57ce\u5e02\u79ef\u5206\u6307\u6807\u4e0e\u5206\u503c\u4e0d\u4e00\u81f4\uff0c\u672c\u8868\u53ea\u6838\u67e5\u6750\u6599\u8986\u76d6\uff0c\u4e0d\u4f30\u7b97\u5206\u503c\u3002")
    lines.append("")

    lines.append("---")
    lines.append("\u672c\u7ed3\u679c\u4e3a\u6750\u6599\u6574\u7406\u4e0e\u65f6\u6548\u63d0\u9192\uff0c\u4e0d\u6784\u6210\u53d7\u7406\u627f\u8bfa\u3002")
    return "\n".join(lines)


def render_json(text, as_of, reg_date=None, issue_date=None):
    obj = {
        "as_of": as_of.isoformat(),
        "paths": pick_path(text),
        "materials": [{"name": n, "status": s} for n, s in check_materials(text)],
        "blockers": check_blockers(text),
        "points": [{"name": n, "status": s} for n, s in check_points(text)],
        "residence_gate": None,
        "endorsement": None,
    }
    g = residence_gate(reg_date, as_of)
    if g:
        obj["residence_gate"] = {
            "register_date": g[0].isoformat(),
            "eligible_from": g[1].isoformat(),
            "waited_days": g[2],
            "remain_days": g[3],
            "eligible": g[3] <= 0,
        }
    e = endorsement_state(issue_date, as_of)
    if e:
        obj["endorsement"] = {
            "issue_date": e[0].isoformat(),
            "due": e[1].isoformat(),
            "window_start": e[2].isoformat(),
            "remain_days": e[3],
            "stage": e[4],
        }
    return json.dumps(obj, ensure_ascii=False, indent=2)


SAMPLE_OK = """
\u5c45\u4f4f\u8bc1\u7533\u9886\u6750\u6599
\u8eab\u4efd\u8bc1\uff1a\u672c\u4eba\u5c45\u6c11\u8eab\u4efd\u8bc1\u539f\u4ef6\u53ca\u590d\u5370\u4ef6\u3002
\u7167\u7247\uff1a\u8fd1\u671f\u514d\u51a0\u7167\u7247\uff0c\u5df2\u5728\u53d7\u7406\u70b9\u4eba\u50cf\u91c7\u96c6\u3002
\u4f4f\u5740\u8bc1\u660e\uff1a\u4e0e\u623f\u4e1c\u7b7e\u8ba2\u7684\u623f\u5c4b\u79df\u8d41\u5408\u540c\uff0c\u79df\u8d41\u671f\u4e24\u5e74\u3002
\u52b3\u52a8\u5408\u540c\uff1a\u4e0e\u67d0\u67d0\u516c\u53f8\u7b7e\u8ba2\u4e09\u5e74\u671f\u52b3\u52a8\u5408\u540c\uff0c\u5df2\u7f34\u793e\u4fdd\u3002
\u5c45\u4f4f\u767b\u8bb0\uff1a2025-12-01 \u5728\u67d0\u67d0\u6d3e\u51fa\u6240\u529e\u7406\u5c45\u4f4f\u767b\u8bb0\uff0c\u767b\u8bb0\u51ed\u8bc1\u9f50\u5168\u3002
"""

SAMPLE_BAD = """
\u5c45\u4f4f\u8bc1\u54a8\u8be2
\u7533\u8bf7\u4eba\u672a\u6ee116\u5468\u5c81\uff0c\u5c0f\u5b66\u5728\u8bfb\uff0c\u5bb6\u957f\u60f3\u81ea\u5df1\u529e\u4e00\u4e0b\u3002
\u6750\u6599\u4e0d\u9f50\uff0c\u590d\u5370\u4ef6\u906e\u6321\u770b\u4e0d\u6e05\u3002
\u5c45\u4f4f\u5730\u5740\u4e0e\u5b9e\u9645\u4e0d\u7b26\uff0c\u767b\u8bb0\u5730\u5740\u4e0d\u5b9e\u3002
"""

SAMPLE_ENDORSE = """
\u5c45\u4f4f\u8bc1\u7b7e\u6ce8\u54a8\u8be2
\u6301\u8bc1\u4eba\u751f\u65e5 1990 \u5e74\uff0c\u672c\u79d1\u5b66\u5386\uff0c\u793e\u4fdd\u8fde\u7eed\u7f34\u7eb3 5 \u5e74\u3002
\u6709\u623f\u4ea7\u8bc1\uff0c\u81ea\u8d2d\u4f4f\u623f\uff0c\u83b7\u5e02\u7ea7\u8868\u5f70\u5956\u52b1\u4e00\u6b21\u3002
\u5c45\u4f4f\u8bc1\u53d1\u8bc1\u65e5\u671f 2025-09-20\uff0c\u4e00\u76f4\u6ca1\u6709\u529e\u7406\u7b7e\u6ce8\u3002
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

    ck("ok_has_path", "\u5408\u6cd5\u7a33\u5b9a\u5c31\u4e1a" in pick_path(SAMPLE_OK), True)
    ck("ok_materials_core", all(s == "\u9f50\u5907" for i, (_, s) in enumerate(check_materials(SAMPLE_OK)) if i < 5), True)
    ck("ok_no_blocker", check_blockers(SAMPLE_OK), [])

    mb = check_materials(SAMPLE_BAD)
    miss = [n for n, s in mb if s == "\u7f3a\u5931"]
    ck("bad_missing_gt0", len(miss) > 0, True)
    ck("bad_has_blocker", len(check_blockers(SAMPLE_BAD)) >= 2, True)
    ck("bad_no_path", pick_path(SAMPLE_BAD), [])

    g = residence_gate(datetime.date(2026, 1, 15), as_of)
    ck("gate_eligible_date", g[1].isoformat(), "2026-07-15")
    ck("gate_is_eligible", g[3] <= 0, True)
    g2 = residence_gate(datetime.date(2026, 8, 1), as_of)
    ck("gate_not_eligible_yet", g2[3] > 0, True)

    e = endorsement_state(datetime.date(2025, 9, 20), as_of)
    ck("endorse_due", e[1].isoformat(), "2026-09-20")
    ck("endorse_stage_overdue", e[4], "\u5df2\u903e\u671f")
    e2 = endorsement_state(datetime.date(2026, 4, 10), as_of)
    ck("endorse_stage_normal", e2[4], "\u672a\u5230\u7b7e\u6ce8\u671f")

    ck("points_dims_covered", len([1 for _, s in check_points(SAMPLE_ENDORSE) if s == "\u6709\u6750\u6599"]) >= 3, True)

    md = render_md(SAMPLE_OK, as_of, datetime.date(2025, 12, 1), datetime.date(2025, 9, 20))
    ck("md_header", md.startswith("# "), True)
    js = json.loads(render_json(SAMPLE_OK, as_of, datetime.date(2025, 12, 1), None))
    ck("json_keys", sorted(js.keys()),
       ["as_of", "blockers", "endorsement", "materials", "paths", "points", "residence_gate"])

    for line in res:
        print(line)
    print("SELFTEST %s" % ("OK" if ok else "FAILED"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--register-date", default="")
    ap.add_argument("--issue-date", default="")
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
    reg = parse_date(a.register_date)
    iss = parse_date(a.issue_date)

    body = render_md(text, as_of, reg, iss) if a.format == "md" else render_json(text, as_of, reg, iss)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(body)
        print("WROTE %s" % a.out)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
