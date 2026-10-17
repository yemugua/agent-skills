# -*- coding: utf-8 -*-
"""\u4f53\u6d4b\u9879\u76ee\u5dee\u8ddd\u6d4b\u7b97\u4e0e\u5468\u671f\u53ef\u884c\u6027\u5224\u5b9a\u5de5\u5177\u3002

\u7528\u6cd5:
  python fitness_test_check.py --file case.json [--json]
  python fitness_test_check.py --selftest

\u8fbe\u6807\u503c\u9700\u7531\u4f7f\u7528\u8005\u4ece\u5f53\u5e74\u516c\u5e03\u7684\u6267\u884c\u6587\u4ef6\u53d6\u5f97, \u672c\u811a\u672c\u4e0d\u5185\u7f6e\u4efb\u4f55\u8fbe\u6807\u5206\u6570\u7ebf\u3002
\u5224\u5b9a\u987a\u5e8f: \u5148\u770b\u771f\u5b9e\u7f3a\u9677(\u5468\u671f\u4e0d\u8db3\u7684\u672a\u8fbe\u6807\u9879\u3001\u5dee\u8ddd\u8fc7\u5927\u9879\u3001\u8bad\u7ec3\u9891\u6b21\u4e0d\u8db3),
\u518d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574; \u8ddd\u8003\u8bd5\u53ea\u5269\u51e0\u5929\u800c\u67d0\u9879\u5dee\u8ddd 30% \u65f6\u76f4\u63a5\u5224\u6765\u4e0d\u53ca, \u4e0d\u662f\u5f85\u786e\u8ba4\u3002
"""
import argparse
import io
import json
import os
import sys
import tempfile

SESSION_MIN = 3.0
GAP_QUICK = 5.0
URGENT_WEEKS = 2.0


def num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def gap_pct(item):
    """\u8d8a\u5c0f\u8d8a\u597d: (\u5f53\u524d-\u76ee\u6807)/\u76ee\u6807; \u8d8a\u5927\u8d8a\u597d: (\u76ee\u6807-\u5f53\u524d)/\u76ee\u6807\u3002"""
    typ = item.get("type")
    cur = num(item.get("current"))
    tgt = num(item.get("target"))
    if typ not in ("lower_better", "higher_better") or cur is None or tgt is None or tgt == 0:
        return None
    if typ == "lower_better":
        return (cur - tgt) / tgt * 100.0
    return (tgt - cur) / tgt * 100.0


def need_weeks(gap):
    g = float(gap)
    if g <= 3.0:
        return 2.0
    if g <= 6.0:
        return 4.0
    if g <= 10.0:
        return 8.0
    if g <= 15.0:
        return 12.0
    return 16.0


def feasibility(gap, weeks):
    """\u8fd4\u56de (\u5224\u5b9a, \u8bf4\u660e)\u3002\u5224\u5b9a\u4e3a \u5df2\u8fbe\u6807 / \u53ef\u8fbe\u6807 / \u9700\u51b2\u523a / \u4e0d\u4e50\u89c2 / \u6765\u4e0d\u53ca / \u5f85\u786e\u8ba4\u3002"""
    if gap is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u5f53\u524d\u6210\u7ee9\u3001\u8fbe\u6807\u503c\u6216\u9879\u76ee\u7c7b\u578b"
    if weeks is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u8ddd\u8003\u8bd5\u5468\u6570"
    if gap <= 0:
        return u"\u5df2\u8fbe\u6807", u"\u5f53\u524d\u6210\u7ee9\u5df2\u8fbe\u5230\u8fbe\u6807\u503c\uff0c\u4fdd\u6301\u5373\u53ef"
    nw = need_weeks(gap)
    if weeks < URGENT_WEEKS and gap > GAP_QUICK:
        return u"\u6765\u4e0d\u53ca", u"\u8ddd\u8003\u8bd5\u4ec5 %g \u5468\u800c\u5dee\u8ddd %.1f%%\uff1a\u8be5\u9879\u5b9e\u8d28\u63d0\u5347\u57fa\u672c\u4e0d\u53ef\u80fd\uff0c\u53ea\u505a\u6d41\u7a0b\u719f\u6089\u4e0e\u7a33\u5b9a\u53d1\u6325" % (
            weeks, gap)
    if weeks < nw / 2.0:
        return u"\u4e0d\u4e50\u89c2", u"\u5dee\u8ddd %.1f%% \u7ea6\u9700 %g \u5468\uff0c\u5269\u4f59\u4ec5 %g \u5468\uff1a\u5e94\u8c03\u6574\u9884\u671f\uff0c\u628a\u65f6\u95f4\u6295\u5411\u5dee\u8ddd\u5c0f\u89c1\u6548\u5feb\u7684\u9879\u76ee" % (
            gap, nw, weeks)
    if weeks < nw:
        return u"\u9700\u51b2\u523a", u"\u5dee\u8ddd %.1f%% \u7ea6\u9700 %g \u5468\uff0c\u5269\u4f59 %g \u5468\uff1a\u63d0\u9ad8\u9891\u6b21\u5230\u6bcf\u5468 4 \u6b21\u5e76\u4f18\u5148\u5b89\u6392" % (gap, nw, weeks)
    return u"\u53ef\u8fbe\u6807", u"\u5dee\u8ddd %.1f%% \u7ea6\u9700 %g \u5468\uff0c\u5269\u4f59 %g \u5468\uff0c\u5468\u671f\u5145\u8db3" % (gap, nw, weeks)


def rank_items(rows):
    """\u6309\u5dee\u8ddd\u964d\u5e8f\u6392, \u5dee\u8ddd\u6700\u5927\u7684\u6392\u6700\u524d, \u7528\u8d1f\u53f7\u9501\u4f4f\u65b9\u5411\u3002"""
    return sorted(rows, key=lambda r: -r["gap"])


def load_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def build_report(data):
    items = data.get("items", []) or []
    weeks = num(data.get("weeks_to_exam"))
    sessions = num(data.get("weekly_sessions"))

    rows = []
    for it in items:
        g = gap_pct(it)
        rows.append({
            "name": str(it.get("name", u"\u672a\u547d\u540d\u9879\u76ee")),
            "type": it.get("type"),
            "unit": it.get("unit", ""),
            "current": num(it.get("current")),
            "target": num(it.get("target")),
            "gap": g,
        })

    ranked = [r for r in rank_items(rows) if r["gap"] is not None]
    unknown = [r for r in rows if r["gap"] is None]

    defects = []
    fine = []
    pending = []

    if not items:
        pending.append(u"\u672a\u63d0\u4f9b\u4efb\u4f55\u4f53\u6d4b\u9879\u76ee\uff0c\u65e0\u6cd5\u505a\u5dee\u8ddd\u6d4b\u7b97")
    for r in unknown:
        pending.append(u"\u9879\u76ee\u300c%s\u300d\u7684\u7c7b\u578b\u3001\u5f53\u524d\u6210\u7ee9\u6216\u8fbe\u6807\u503c\u7f3a\u5931\uff0c\u65e0\u6cd5\u8ba1\u7b97\u5dee\u8ddd" % r["name"])

    if weeks is None:
        pending.append(u"\u672a\u63d0\u4f9b\u8ddd\u8003\u8bd5\u5468\u6570\uff0c\u65e0\u6cd5\u505a\u5468\u671f\u53ef\u884c\u6027\u5224\u5b9a")

    for r in ranked:
        v, msg = feasibility(r["gap"], weeks)
        r["verdict"] = v
        r["msg"] = msg
        if v in (u"\u6765\u4e0d\u53ca", u"\u4e0d\u4e50\u89c2"):
            defects.append(u"\u9879\u76ee\u300c%s\u300d[%s]\uff1a%s" % (r["name"], v, msg))
        elif v == u"\u9700\u51b2\u523a":
            fine.append(u"\u9879\u76ee\u300c%s\u300d[%s]\uff1a%s" % (r["name"], v, msg))

    if sessions is None:
        pending.append(u"\u672a\u63d0\u4f9b\u6bcf\u5468\u8bad\u7ec3\u6b21\u6570")
    elif sessions < SESSION_MIN:
        fine.append(u"\u6bcf\u5468\u8bad\u7ec3 %g \u6b21\u504f\u5c11\uff0c\u4f4e\u4e8e %g \u6b21\u65f6\u8fdb\u6b65\u5f88\u6162" % (sessions, SESSION_MIN))

    lines = []
    lines.append("=" * 62)
    lines.append(u"\u4f53\u6d4b\u9879\u76ee\u5dee\u8ddd\u6d4b\u7b97\u4e0e\u5468\u671f\u53ef\u884c\u6027\u5224\u5b9a")
    lines.append("=" * 62)
    lines.append(u"\u8ddd\u8003\u8bd5\u5468\u6570\uff1a%s    \u6bcf\u5468\u8bad\u7ec3\u6b21\u6570\uff1a%s" % (
        (u"%g" % weeks) if weeks is not None else u"--",
        (u"%g" % sessions) if sessions is not None else u"--"))
    lines.append("")
    lines.append(u"[\u4e00] \u9010\u9879\u5dee\u8ddd\uff08\u6309\u5dee\u8ddd\u4ece\u5927\u5230\u5c0f\u6392\u5e8f\uff09")
    lines.append(u"%-14s %10s %10s %10s %10s" % (u"\u9879\u76ee", u"\u5f53\u524d", u"\u8fbe\u6807\u503c", u"\u5dee\u8ddd", u"\u5224\u5b9a"))
    lines.append("-" * 62)
    for r in ranked:
        lines.append(u"%-14s %10s %10s %10s %10s" % (
            r["name"],
            (u"%g" % r["current"]) if r["current"] is not None else u"--",
            (u"%g" % r["target"]) if r["target"] is not None else u"--",
            u"%.1f%%" % r["gap"],
            r.get("verdict", u"--")))
    if unknown:
        for r in unknown:
            lines.append(u"%-14s %10s %10s %10s %10s" % (r["name"], u"--", u"--", u"--", u"\u5f85\u786e\u8ba4"))
    lines.append("-" * 62)
    lines.append("")
    lines.append(u"[\u4e8c] \u5468\u671f\u53ef\u884c\u6027")
    lines.append(u"%-14s %10s %10s  %s" % (u"\u9879\u76ee", u"\u5dee\u8ddd", u"\u6240\u9700\u5468", u"\u8bf4\u660e"))
    lines.append("-" * 62)
    for r in ranked:
        lines.append(u"%-14s %10s %10s  %s" % (
            r["name"], u"%.1f%%" % r["gap"], u"%g" % need_weeks(r["gap"]), r.get("msg", u"--")))
    lines.append("-" * 62)
    lines.append("")
    lines.append(u"[\u4e09] \u4e0d\u5408\u683c\u9879\u4e0e\u539f\u56e0")
    if defects:
        for i, d in enumerate(defects, 1):
            lines.append(u"  %d. %s" % (i, d))
    else:
        lines.append(u"  \u65e0")
    lines.append("")
    lines.append(u"[\u56db] \u9700\u6539\u8fdb\u9879")
    if fine:
        for i, d in enumerate(fine, 1):
            lines.append(u"  %d. %s" % (i, d))
    else:
        lines.append(u"  \u65e0")
    lines.append("")
    lines.append(u"[\u4e94] \u5f85\u786e\u8ba4\u9879")
    if pending:
        for i, d in enumerate(pending, 1):
            lines.append(u"  %d. %s" % (i, d))
    else:
        lines.append(u"  \u65e0")
    lines.append("")
    lines.append(u"[\u516d] \u8bad\u7ec3\u5904\u65b9")
    lines.append(u"  1. \u8fbe\u6807\u503c\u5fc5\u987b\u53d6\u81ea\u5f53\u5e74\u516c\u5e03\u7684\u6267\u884c\u6587\u4ef6\uff0c\u4e0d\u8981\u7528\u65e7\u7248\u672c")
    if ranked:
        top = ranked[0]
        lines.append(u"  2. \u8bad\u7ec3\u91cd\u70b9\uff1a%s\uff08\u5dee\u8ddd %.1f%%\uff09" % (top["name"], top["gap"]))
    lines.append(u"  3. \u957f\u8dd1\u6743\u91cd\u9ad8\u4e14\u63d0\u5347\u6162\uff0c\u5373\u4f7f\u5dee\u8ddd\u4e0d\u662f\u6700\u5927\u4e5f\u8981\u4f18\u5148\u5b89\u6392")
    lines.append(u"  4. \u6bcf\u5468 3-4 \u6b21\uff1a\u6709\u6c27 2 \u6b21\u3001\u529b\u91cf 2 \u6b21\u3001\u4e13\u9879 1 \u6b21\uff0c\u6bcf 4 \u5468\u5b89\u6392\u51cf\u91cf\u5468")
    lines.append(u"  5. \u5f15\u4f53\u5411\u4e0a\u505a\u4e0d\u4e86\u65f6\u8d70\u9000\u9636\u94fe\uff1a\u60ac\u5782 \u2192 \u5f39\u529b\u5e26\u8f85\u52a9 \u2192 \u79bb\u5fc3 \u2192 \u6807\u51c6")
    lines.append(u"  6. \u8003\u524d\u4e00\u5468\u51cf\u91cf\u5230 50-60%\uff0c\u8003\u524d\u4e00\u5929\u5b8c\u5168\u4f11\u606f")
    lines.append(u"  7. \u957f\u8dd1\u524d 200 \u7c73\u4e0d\u8981\u51b2\uff0c\u6700\u540e 150-200 \u7c73\u518d\u52a0\u901f")

    if defects:
        overall = u"\u4e0d\u5408\u683c"
    elif fine:
        overall = u"\u9700\u6539\u8fdb"
    elif pending:
        overall = u"\u5f85\u786e\u8ba4"
    else:
        overall = u"\u5408\u683c"

    lines.append("")
    lines.append(u"\u603b\u5224\u5b9a\uff1a%s" % overall)
    lines.append(u"\u63d0\u793a\uff1a\u672c\u811a\u672c\u4e0d\u5185\u7f6e\u4efb\u4f55\u8fbe\u6807\u5206\u6570\u7ebf\uff0c\u6807\u51c6\u4ee5\u5f53\u5e74\u516c\u5e03\u7684\u6267\u884c\u6587\u4ef6\u4e3a\u51c6\u3002")
    lines.append(u"\u63d0\u793a\uff1a\u80f8\u95f7\u80f8\u75db\u3001\u5fc3\u60b8\u3001\u5934\u6655\u3001\u5f02\u5e38\u6c14\u77ed\u65f6\u7acb\u5373\u505c\u6b62\u8bad\u7ec3\u5e76\u5c31\u533b\u3002")
    lines.append(u"\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u5dee\u8ddd\u81ea\u67e5\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u8fbe\u6807\u627f\u8bfa\u6216\u4f53\u68c0\u7ed3\u8bba\u3002")
    lines.append("=" * 62)

    summary = {
        "weeks_to_exam": weeks,
        "ranked": [{"name": r["name"], "gap": r["gap"], "verdict": r.get("verdict")} for r in ranked],
        "defects": defects,
        "fine": fine,
        "pending": pending,
        "overall": overall,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append((u"\u8d8a\u5c0f\u8d8a\u597d\u5dee\u8ddd\u7b97\u6cd5", abs(gap_pct({"type": "lower_better", "current": 300,
                                          "target": 250}) - 20.0) < 1e-9))
    r.append((u"\u8d8a\u5927\u8d8a\u597d\u5dee\u8ddd\u7b97\u6cd5", abs(gap_pct({"type": "higher_better", "current": 1.8,
                                          "target": 2.0}) - 10.0) < 1e-9))
    r.append((u"\u5df2\u8fbe\u6807\u65f6\u5dee\u8ddd\u4e3a\u8d1f", gap_pct({"type": "lower_better", "current": 240,
                                      "target": 250}) < 0))
    r.append((u"\u7c7b\u578b\u7f3a\u5931\u65f6\u5dee\u8ddd\u4e3a None", gap_pct({"type": "xxx", "current": 1, "target": 2}) is None))
    r.append((u"\u8fbe\u6807\u503c\u4e3a 0 \u65f6\u5dee\u8ddd\u4e3a None", gap_pct({"type": "higher_better", "current": 1,
                                            "target": 0}) is None))
    r.append((u"\u6240\u9700\u5468\u671f\u6620\u5c04 3% \u4e3a 2 \u5468", need_weeks(3.0) == 2.0))
    r.append((u"\u6240\u9700\u5468\u671f\u6620\u5c04 8% \u4e3a 8 \u5468", need_weeks(8.0) == 8.0))
    r.append((u"\u6240\u9700\u5468\u671f\u6620\u5c04 20% \u4e3a 16 \u5468", need_weeks(20.0) == 16.0))

    rows = [
        {"name": u"A", "gap": 5.0},
        {"name": u"B", "gap": 25.0},
        {"name": u"C", "gap": 12.0},
    ]
    ranked = rank_items(rows)
    r.append((u"\u6392\u5e8f\u65b9\u5411\uff1a\u5dee\u8ddd\u6700\u5927\u7684\u6392\u6700\u524d", ranked[0]["name"] == u"B"))
    r.append((u"\u6392\u5e8f\u65b9\u5411\uff1a\u5dee\u8ddd\u6700\u5c0f\u7684\u6392\u6700\u540e", ranked[-1]["name"] == u"A"))

    r.append((u"\u53cd\u4f8b\uff1a3 \u5929\u4e14\u5dee\u8ddd 30% \u5224\u6765\u4e0d\u53ca", feasibility(30.0, 0.5)[0] == u"\u6765\u4e0d\u53ca"))
    r.append((u"\u53cd\u4f8b\uff1a4 \u5468\u4e14\u5dee\u8ddd 12% \u5224\u4e0d\u4e50\u89c2", feasibility(12.0, 4.0)[0] == u"\u4e0d\u4e50\u89c2"))
    r.append((u"6 \u5468\u4e14\u5dee\u8ddd 8% \u5224\u9700\u51b2\u523a", feasibility(8.0, 6.0)[0] == u"\u9700\u51b2\u523a"))
    r.append((u"12 \u5468\u4e14\u5dee\u8ddd 5% \u5224\u53ef\u8fbe\u6807", feasibility(5.0, 12.0)[0] == u"\u53ef\u8fbe\u6807"))
    r.append((u"\u5df2\u8fbe\u6807\u5224\u5b9a", feasibility(-2.0, 12.0)[0] == u"\u5df2\u8fbe\u6807"))
    r.append((u"\u7f3a\u5468\u6570\u65f6\u5224\u5f85\u786e\u8ba4", feasibility(5.0, None)[0] == u"\u5f85\u786e\u8ba4"))

    _, s = build_report({
        "weeks_to_exam": 12, "weekly_sessions": 4,
        "items": [
            {"name": u"1000\u7c73", "type": "lower_better", "current": 260, "target": 250, "unit": u"\u79d2"},
            {"name": u"\u7acb\u5b9a\u8df3\u8fdc", "type": "higher_better", "current": 1.9, "target": 2.0, "unit": u"\u7c73"},
        ],
    })
    r.append((u"\u6807\u51c6\u6837\u4f8b\u5224\u5b9a\u5408\u683c", s["overall"] == u"\u5408\u683c"))
    r.append((u"\u6807\u51c6\u6837\u4f8b\u6392\u5e8f\u6309\u5dee\u8ddd\u964d\u5e8f", s["ranked"][0]["name"] == u"\u7acb\u5b9a\u8df3\u8fdc"))

    _, s1 = build_report({
        "weeks_to_exam": 0.5, "weekly_sessions": 4,
        "items": [
            {"name": u"1000\u7c73", "type": "lower_better", "current": 330, "target": 250, "unit": u"\u79d2"},
        ],
    })
    r.append((u"\u53cd\u4f8b\uff1a\u8003\u524d 3 \u5929\u5dee\u8ddd 32% \u5224\u4e0d\u5408\u683c", s1["overall"] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u6765\u4e0d\u53ca\u8fdb\u7f3a\u9677\u8868", any(u"\u6765\u4e0d\u53ca" in d for d in s1["defects"])))

    _, s2 = build_report({
        "weeks_to_exam": 4, "weekly_sessions": 3,
        "items": [
            {"name": u"\u5f15\u4f53\u5411\u4e0a", "type": "higher_better", "current": 2, "target": 10, "unit": u"\u4e2a"},
        ],
    })
    r.append((u"\u53cd\u4f8b\uff1a4 \u5468\u5dee\u8ddd 80% \u5224\u4e0d\u4e50\u89c2", s2["overall"] == u"\u4e0d\u5408\u683c"))

    _, s3 = build_report({
        "weeks_to_exam": 12, "weekly_sessions": 2,
        "items": [
            {"name": u"1000\u7c73", "type": "lower_better", "current": 255, "target": 250, "unit": u"\u79d2"},
        ],
    })
    r.append((u"\u53cd\u4f8b\uff1a\u6bcf\u5468 2 \u6b21\u5224\u9700\u6539\u8fdb", s3["overall"] == u"\u9700\u6539\u8fdb"))

    _, s4 = build_report({"weeks_to_exam": 12})
    r.append((u"\u65e0\u9879\u76ee\u8bb0\u4e3a\u5f85\u786e\u8ba4", s4["overall"] == u"\u5f85\u786e\u8ba4"))

    _, s5 = build_report({
        "weeks_to_exam": 0.5,
        "items": [{"name": u"1000\u7c73", "type": "lower_better", "current": 330, "target": 250}],
    })
    r.append((u"\u7f3a\u8bad\u7ec3\u9891\u6b21\u4f46\u5dee\u8ddd\u5de8\u5927\u4e0d\u5f97\u5224\u5f85\u786e\u8ba4", s5["overall"] == u"\u4e0d\u5408\u683c"))

    p = os.path.join(tempfile.gettempdir(), "_fitness_bom_case.json")
    blob = b"\xef\xbb\xbf" + json.dumps({
        "weeks_to_exam": 12, "weekly_sessions": 4,
        "items": [{"name": u"1000\u7c73", "type": "lower_better", "current": 255,
                   "target": 250, "unit": u"\u79d2"}],
    }, ensure_ascii=False).encode("utf-8")
    with open(p, "wb") as f:
        f.write(blob)
    try:
        d = load_json(p)
        r.append((u"UTF-8 BOM \u8f93\u5165\u9996\u952e\u53ef\u8bfb", abs(d.get("weeks_to_exam", 0) - 12.0) < 1e-9))
        r.append((u"UTF-8 BOM \u8f93\u5165\u5d4c\u5957\u7ed3\u6784\u53ef\u8bfb", d["items"][0]["name"] == u"1000\u7c73"))
    finally:
        if os.path.exists(p):
            os.remove(p)

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
    parser = argparse.ArgumentParser(description=u"\u4f53\u6d4b\u5dee\u8ddd\u6d4b\u7b97\u4e0e\u5468\u671f\u53ef\u884c\u6027\u5de5\u5177")
    parser.add_argument("--file", help=u"\u8f93\u5165 JSON \u6587\u4ef6\u8def\u5f84\uff08UTF-8\uff09")
    parser.add_argument("--json", action="store_true", help=u"\u4ee5 JSON \u8f93\u51fa")
    parser.add_argument("--out", help=u"\u7ed3\u679c\u5199\u5165\u6307\u5b9a\u6587\u4ef6")
    parser.add_argument("--selftest", action="store_true", help=u"\u8fd0\u884c\u81ea\u68c0")
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))

    if args.selftest:
        sys.exit(0 if selftest() else 1)

    if not args.file:
        parser.error(u"\u9700\u8981 --file \u6216 --selftest")

    data = load_json(args.file)

    report, summary = build_report(data)
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else report
    out_path = args.out or os.path.join(here, "_last_result.txt")
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write(body)
    print(body)
    print("")
    print(u"\u7ed3\u679c\u5df2\u5199\u5165\uff1a%s" % out_path)


if __name__ == "__main__":
    main()

