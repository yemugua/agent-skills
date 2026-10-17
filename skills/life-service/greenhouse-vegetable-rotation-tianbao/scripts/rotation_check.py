# -*- coding: utf-8 -*-
"""\u5927\u68da\u852c\u83dc\u832c\u53e3\u6392\u671f\u4e0e\u8fde\u4f5c\u969c\u788d\u6821\u9a8c\u5de5\u5177\u3002

\u7528\u6cd5:
  python rotation_check.py --file plan.json [--json]
  python rotation_check.py --selftest

\u672c\u5de5\u5177\u4e0d\u505a\u6d4b\u571f, \u4e0d\u7ed9\u571f\u58e4\u517b\u5206\u4e0e\u76d0\u5206\u7684\u7cbe\u786e\u6570\u503c, \u4e0d\u63a8\u8350\u4efb\u4f55\u519c\u836f\u5546\u54c1\u3002
"""
import argparse
import io
import json
import os
import sys

# \u79d1\u5c5e\u8868: \u4f5c\u7269 -> \u79d1\u540d
FAMILY = {
    "\u9ec4\u74dc": "\u846b\u82a6\u79d1", "\u897f\u74dc": "\u846b\u82a6\u79d1", "\u5357\u74dc": "\u846b\u82a6\u79d1", "\u4e1d\u74dc": "\u846b\u82a6\u79d1",
    "\u751c\u74dc": "\u846b\u82a6\u79d1", "\u82e6\u74dc": "\u846b\u82a6\u79d1", "\u897f\u846b\u82a6": "\u846b\u82a6\u79d1",
    "\u756a\u8304": "\u8304\u79d1", "\u8304\u5b50": "\u8304\u79d1", "\u8fa3\u6912": "\u8304\u79d1", "\u67ff\u5b50\u6912": "\u8304\u79d1",
    "\u9a6c\u94c3\u85af": "\u8304\u79d1",
    "\u767d\u83dc": "\u5341\u5b57\u82b1\u79d1", "\u841d\u535c": "\u5341\u5b57\u82b1\u79d1", "\u9752\u83dc": "\u5341\u5b57\u82b1\u79d1",
    "\u7518\u84dd": "\u5341\u5b57\u82b1\u79d1", "\u82b1\u6930\u83dc": "\u5341\u5b57\u82b1\u79d1", "\u82a5\u84dd": "\u5341\u5b57\u82b1\u79d1",
    "\u83e0\u83dc": "\u85dc\u79d1", "\u82b9\u83dc": "\u4f1e\u5f62\u79d1", "\u80e1\u841d\u535c": "\u4f1e\u5f62\u79d1",
    "\u751f\u83dc": "\u83ca\u79d1", "\u83b4\u82e3": "\u83ca\u79d1",
    "\u83dc\u8c46": "\u8c46\u79d1", "\u8c47\u8c46": "\u8c46\u79d1", "\u8c4c\u8c46": "\u8c46\u79d1", "\u8695\u8c46": "\u8c46\u79d1",
    "\u7389\u7c73": "\u79be\u672c\u79d1", "\u5c0f\u9ea6": "\u79be\u672c\u79d1",
    "\u5927\u849c": "\u767e\u5408\u79d1", "\u6d0b\u8471": "\u767e\u5408\u79d1", "\u97ed\u83dc": "\u767e\u5408\u79d1",
    "\u82dc\u84ff": "\u8c46\u79d1",
}

# \u6839\u6df1: \u6d45 / \u4e2d / \u6df1
ROOT_DEPTH = {
    "\u751f\u83dc": "\u6d45", "\u83e0\u83dc": "\u6d45", "\u5c0f\u767d\u83dc": "\u6d45", "\u7a7a\u5fc3\u83dc": "\u6d45", "\u82cb\u83dc": "\u6d45",
    "\u9752\u83dc": "\u6d45", "\u849c\u82d7": "\u6d45",
    "\u9ec4\u74dc": "\u6d45", "\u756a\u8304": "\u4e2d", "\u8304\u5b50": "\u4e2d", "\u8fa3\u6912": "\u4e2d", "\u897f\u846b\u82a6": "\u4e2d",
    "\u83dc\u8c46": "\u4e2d", "\u8c47\u8c46": "\u4e2d", "\u82b9\u83dc": "\u6d45", "\u97ed\u83dc": "\u6d45",
    "\u841d\u535c": "\u6df1", "\u80e1\u841d\u535c": "\u6df1", "\u7518\u84dd": "\u4e2d", "\u767d\u83dc": "\u6d45", "\u751c\u74dc": "\u6df1",
    "\u897f\u74dc": "\u6df1", "\u5357\u74dc": "\u6df1", "\u4e1d\u74dc": "\u4e2d", "\u82e6\u74dc": "\u4e2d", "\u9a6c\u94c3\u85af": "\u4e2d",
    "\u7389\u7c73": "\u6df1", "\u5c0f\u9ea6": "\u6d45", "\u82dc\u84ff": "\u6df1", "\u8c4c\u8c46": "\u4e2d", "\u8695\u8c46": "\u4e2d",
}

# \u751f\u80b2\u671f\u53c2\u8003\u5929\u6570 (\u64ad\u79cd\u5230\u91c7\u6536)
GROW_DAYS = {
    "\u9ec4\u74dc": 65, "\u897f\u74dc": 95, "\u5357\u74dc": 90, "\u4e1d\u74dc": 80, "\u751c\u74dc": 85, "\u82e6\u74dc": 80,
    "\u897f\u846b\u82a6": 60, "\u756a\u8304": 105, "\u8304\u5b50": 115, "\u8fa3\u6912": 95, "\u9a6c\u94c3\u85af": 90,
    "\u767d\u83dc": 65, "\u841d\u535c": 55, "\u9752\u83dc": 40, "\u7518\u84dd": 80, "\u82b1\u6930\u83dc": 90,
    "\u82a5\u84dd": 75, "\u83e0\u83dc": 38, "\u751f\u83dc": 50, "\u83b4\u82e3": 55, "\u83dc\u8c46": 60, "\u8c47\u8c46": 70,
    "\u8c4c\u8c46": 75, "\u8695\u8c46": 90, "\u7389\u7c73": 100, "\u5c0f\u9ea6": 230, "\u5927\u849c": 240,
    "\u6d0b\u8471": 250, "\u97ed\u83dc": 90, "\u80e1\u841d\u535c": 100, "\u82b9\u83dc": 100, "\u82dc\u84ff": 90,
    "\u7a7a\u5fc3\u83dc": 35, "\u82cb\u83dc": 35, "\u5c0f\u767d\u83dc": 32, "\u849c\u82d7": 60,
}

# \u7f13\u82d7\u671f\u5929\u6570
TRANSPLANT_RECOVERY = {
    "\u53f6\u83dc": 4, "\u679c\u83dc": 8,
}

# \u6309\u533a\u57df\u7ed9\u832c\u6b21\u6a21\u677f: (\u540d\u79f0, \u5b9a\u690d\u6708, \u91c7\u6536\u6708, \u4ee3\u8868\u4f5c\u7269, \u751f\u80b2\u671f\u5929\u6570)
REGION_TEMPLATES = {
    "north": [
        ("\u6625\u832c", 2, 5, "\u9ec4\u74dc", 100),
        ("\u590f\u832c", 6, 7, "\u7a7a\u5fc3\u83dc", 45),
        ("\u79cb\u832c", 8, 10, "\u756a\u8304", 80),
        ("\u51ac\u832c", 11, 1, "\u897f\u846b\u82a6", 110),
    ],
    "south": [
        ("\u51ac\u6625\u832c", 12, 3, "\u756a\u8304", 100),
        ("\u6625\u672b\u590f\u521d\u832c", 3, 5, "\u4e1d\u74dc", 70),
        ("\u590f\u5b63\u4f11\u6574\u671f", 7, 8, "\u82dc\u84ff", 60),
        ("\u79cb\u51ac\u832c", 9, 11, "\u767d\u83dc", 75),
    ],
}

RISK_TEXT = {0: "\u4f4e", 1: "\u4e2d", 2: "\u9ad8", 3: "\u6781\u9ad8"}

ADVICE_BY_RISK = {
    "\u4f4e": "\u6b63\u5e38\u5b89\u6392\uff0c\u4fdd\u6301\u8f6e\u79d1\u8bb0\u5f55",
    "\u4e2d": "\u6362\u79d1\u6216\u4f11\u8015\u4e00\u832c, \u540c\u68da\u6539\u79cd\u4e0d\u540c\u79d1\u4f5c\u7269",
    "\u9ad8": "\u5fc5\u987b\u4f11\u8015\u6216\u6362\u68da\u5b89\u6392, \u540c\u68da\u4e0d\u518d\u79cd\u8be5\u79d1",
    "\u6781\u9ad8": "\u89c6\u4e3a\u5df2\u53d1\u751f\u8fde\u4f5c\u969c\u788d, \u9700\u4e13\u4e1a\u8bca\u65ad\u4e0e\u6539\u826f\u65b9\u6848",
}


def family_of(crop):
    return FAMILY.get(crop, "\u672a\u767b\u8bb0")


def root_depth_of(crop):
    return ROOT_DEPTH.get(crop, "\u672a\u767b\u8bb0")


def grow_days_of(crop, default=60):
    return GROW_DAYS.get(crop, default)


def classify_kind(crop):
    if crop in ("\u751f\u83dc", "\u83e0\u83dc", "\u5c0f\u767d\u83dc", "\u7a7a\u5fc3\u83dc", "\u82cb\u83dc", "\u9752\u83dc", "\u849c\u82d7"):
        return "\u53f6\u83dc"
    return "\u679c\u83dc"


def plant_date_offset(crop):
    """\u5b9a\u690d\u65e5\u5f80\u524d\u63a8\u7684\u80b2\u82d7\u671f\u5929\u6570 = \u751f\u80b2\u671f - \u91c7\u6536\u5230\u5b9a\u690d\u7684\u91c7\u524d\u671f, \u7b80\u5316\u4e3a\u7f13\u82d7+\u82d7\u671f."""
    kind = classify_kind(crop)
    base = TRANSPLANT_RECOVERY[kind]
    if kind == "\u679c\u83dc":
        base = base + 25  # \u679c\u83dc\u82d7\u9f84 25-35 \u5929
    else:
        base = base + 10  # \u53f6\u83dc\u591a\u76f4\u64ad\u6216\u5c0f\u82d7\u79fb\u683d
    return base


def rotation_risk(history, planned_crop):
    """\u540c\u79d1\u8fde\u4f5c\u5e74\u9650 -> \u98ce\u9669\u7b49\u7ea7 0/1/2/3"""
    target = family_of(planned_crop)
    years = 0
    for h in history:
        if not isinstance(h, dict):
            continue
        crop = h.get("crop")
        if not crop:
            continue
        if family_of(crop) == target:
            years += 1
    if years <= 1:
        return 0
    if years == 2:
        return 1
    if years == 3:
        return 2
    return 3


def combo_score(prev_crop, next_crop):
    """\u642d\u914d\u8bc4\u5206: \u6362\u79d1+1 \u6362\u6839\u6df1+1, \u6ee1\u5206 2"""
    score = 0
    if family_of(prev_crop) != family_of(next_crop):
        score += 1
    if root_depth_of(prev_crop) != root_depth_of(next_crop):
        score += 1
    return score


def build_plan(region, history, planned, months_available):
    region = (region or "north").strip().lower()
    if region not in REGION_TEMPLATES:
        region = "north"
    tpl = REGION_TEMPLATES[region]
    history = history or []
    planned = planned or []
    lines = []
    summary = {
        "region": region,
        "crop_count": len(planned),
        "months_available": months_available,
        "items": [],
        "warnings": [],
    }

    lines.append("=" * 68)
    lines.append("\u5927\u68da\u852c\u83dc\u832c\u53e3\u6392\u671f\u4e0e\u8fde\u4f5c\u969c\u788d\u6821\u9a8c")
    lines.append("=" * 68)
    region_name = "\u5317\u65b9\u65e5\u5149\u6e29\u5ba4" if region == "north" else "\u5357\u65b9\u51ac\u6625\u68da"
    lines.append("\u533a\u57df\u6a21\u677f: %s (\u901a\u7528\u53c2\u8003)" % region_name)
    lines.append("\u53ef\u7528\u832c\u671f\u6570: %s" % (months_available if months_available else "\u672a\u6307\u5b9a"))
    lines.append("")

    lines.append("[\u4e00] \u533a\u57df\u832c\u6b21\u6a21\u677f (\u53ef\u53c2\u8003\u7684\u5168\u5e74\u8282\u594f)")
    lines.append("-" * 68)
    lines.append("  %-12s %-10s %-10s %-10s" % ("\u832c\u6b21", "\u5b9a\u690d\u671f", "\u91c7\u6536\u671f", "\u751f\u80b2\u671f"))
    for name, pm, cm, crop, days in tpl:
        lines.append("  %-12s %-10s %-10s %-10s" % (
            name,
            "%d \u6708" % pm if pm <= 12 else "%d \u6708" % pm,
            "%d \u6708" % cm,
            "%d \u5929" % days))
    lines.append("")
    lines.append("\u63d0\u793a: \u5b9e\u9645\u5b9a\u690d\u65e5\u987b\u540c\u65f6\u6ee1\u8db3\u5730\u6e29 12-15\u2103 \u4ee5\u4e0a\u3001\u82d7\u9f84\u8fbe\u6807\u3001\u4e0a\u5e02\u7a97\u53e3\u4e09\u4e2a\u7ea6\u675f")
    lines.append("")

    lines.append("[\u4e8c] \u62df\u6392\u832c\u6b21\u9010\u9879\u6821\u9a8c")
    lines.append("-" * 68)
    if not planned:
        lines.append("  \u672a\u63d0\u4f9b planned \u832c\u6b21, \u4ec5\u8f93\u51fa\u6a21\u677f\u4e0e\u8fde\u4f5c\u53f0\u8d26\u6838\u5bf9\u7ed3\u679c")
    prev_crop = None
    for idx, item in enumerate(planned):
        crop = item.get("crop") if isinstance(item, dict) else str(item)
        if not crop:
            continue
        fam = family_of(crop)
        depth = root_depth_of(crop)
        days = grow_days_of(crop)
        risk = rotation_risk(history, crop)
        risk_name = RISK_TEXT[risk]
        combo = combo_score(prev_crop, crop) if prev_crop else None
        if risk >= 2:
            summary["warnings"].append("%s \u540c\u79d1\u8fde\u4f5c %d \u5e74, \u98ce\u9669 %s" % (crop, risk, risk_name))
        lines.append("  \u7b2c %d \u832c  \u4f5c\u7269: %s" % (idx + 1, crop))
        lines.append("    \u79d1\u5c5e: %s   \u6839\u6df1: %s   \u751f\u80b2\u671f\u53c2\u8003: %d \u5929" % (fam, depth, days))
        lines.append("    \u540c\u79d1\u8fde\u4f5c: %d \u5e74 -> \u98ce\u9669\u7b49\u7ea7 %s" % (risk, risk_name))
        lines.append("    \u5904\u7f6e: %s" % ADVICE_BY_RISK[risk_name])
        if combo is not None:
            verdict = "\u6ee1\u8db3\u6362\u79d1\u6362\u6839\u6df1" if combo >= 2 else ("\u90e8\u5206\u6ee1\u8db3, \u9700\u52a0\u4f11\u8015\u6216\u7eff\u80a5" if combo == 1 else "\u672a\u6362\u79d1\u6362\u6839\u6df1, \u98ce\u9669\u9ad8")
            lines.append("    \u4e0e\u524d\u832c\u642d\u914d: %d/2 \u5206 -> %s" % (combo, verdict))
        lines.append("    \u80b2\u82d7\u65e5\u5012\u63a8: \u5b9a\u690d\u65e5\u5f80\u524d\u63a8 %d \u5929 (\u7f13\u82d7+\u82d7\u671f)" % plant_date_offset(crop))
        summary["items"].append({
            "index": idx + 1,
            "crop": crop,
            "family": fam,
            "root_depth": depth,
            "grow_days": days,
            "rotation_years": risk,
            "risk": risk_name,
            "advice": ADVICE_BY_RISK[risk_name],
            "combo_score": combo,
        })
        prev_crop = crop
    lines.append("")

    lines.append("[\u4e09] \u5386\u53f2\u53f0\u8d26\u6838\u5bf9 (\u4ee5\u53f0\u8d26\u4e3a\u51c6, \u4e0d\u9760\u73b0\u573a\u731c\u6d4b)")
    lines.append("-" * 68)
    if not history:
        lines.append("  \u672a\u63d0\u4f9b history, \u8fde\u4f5c\u5e74\u9650\u6309 0 \u8ba1; \u6392\u832c\u53e3\u524d\u8bf7\u5148\u7ffb\u51fa\u8fd1\u4e09\u5e74\u53f0\u8d26")
    else:
        seen = {}
        for h in history:
            crop = h.get("crop") if isinstance(h, dict) else str(h)
            if not crop:
                continue
            seen.setdefault(family_of(crop), []).append(crop)
        if not seen:
            lines.append("  \u53f0\u8d26\u4e3a\u7a7a")
        for fam in sorted(seen):
            lines.append("  %-10s \u51fa\u73b0 %d \u6b21: %s" % (fam, len(seen[fam]), "\u3001".join(seen[fam])))
    lines.append("")

    lines.append("[\u56db] \u7ed3\u8bba")
    lines.append("-" * 68)
    if summary["warnings"]:
        for w in summary["warnings"]:
            lines.append("  [\u6ce8\u610f] %s" % w)
    else:
        lines.append("  \u672a\u68c0\u51fa\u540c\u79d1\u8fde\u4f5c 3 \u5e74\u53ca\u4ee5\u4e0a\u7684\u9ad8\u98ce\u9669\u832c\u6b21")
    lines.append("  \u4e00\u5e74\u4e24\u832c + \u4e00\u6b21\u8ba4\u771f\u4f11\u8015, \u901a\u5e38\u4f18\u4e8e\u786c\u6491\u56db\u832c")
    lines.append("")
    lines.append("\u514d\u8d23: \u672c\u7ed3\u679c\u4e3a\u832c\u53e3\u7f16\u6392\u4e0e\u8fde\u4f5c\u5e74\u9650\u81ea\u67e5, \u4e0d\u4ee3\u66ff\u6d4b\u571f\u62a5\u544a\u4e0e\u519c\u6280\u63a8\u5e7f\u90e8\u95e8\u6307\u5bfc\u3002")
    lines.append("\u514d\u8d23: \u571f\u58e4\u76d0\u5206\u3001\u517b\u5206\u3001\u75c5\u539f\u4e0e\u7ebf\u866b\u7684\u786e\u8ba4\u987b\u4ee5\u68c0\u6d4b\u7ed3\u8bba\u4e3a\u51c6\u3002")
    lines.append("\u514d\u8d23: \u519c\u836f\u7684\u54c1\u79cd\u3001\u7528\u91cf\u4e0e\u5b89\u5168\u95f4\u9694\u671f\u4ee5\u4ea7\u54c1\u767b\u8bb0\u6807\u7b7e\u548c\u5f53\u5730\u690d\u4fdd\u90e8\u95e8\u8981\u6c42\u4e3a\u51c6\u3002")
    lines.append("=" * 68)
    return "\n".join(lines), summary


def load_json(path):
    with io.open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()
    # PowerShell \u5199\u51fa\u7684 UTF-8 \u6587\u4ef6\u53ef\u80fd\u5e26 BOM, \u4e0d\u5265\u6389\u4f1a\u8ba9\u9996\u4e2a key \u53d6\u4e0d\u5230\u503c\u4e14\u4e0d\u62a5\u9519
    raw = raw.lstrip("\ufeff")
    return json.loads(raw)


def _run_checks():
    r = []
    r.append(("\u756a\u8304\u5c5e\u8304\u79d1", family_of("\u756a\u8304") == "\u8304\u79d1"))
    r.append(("\u8304\u5b50\u5c5e\u8304\u79d1", family_of("\u8304\u5b50") == "\u8304\u79d1"))
    r.append(("\u9ec4\u74dc\u5c5e\u846b\u82a6\u79d1", family_of("\u9ec4\u74dc") == "\u846b\u82a6\u79d1"))
    r.append(("\u767d\u83dc\u5c5e\u5341\u5b57\u82b1\u79d1", family_of("\u767d\u83dc") == "\u5341\u5b57\u82b1\u79d1"))
    r.append(("\u751f\u83dc\u5c5e\u83ca\u79d1", family_of("\u751f\u83dc") == "\u83ca\u79d1"))
    r.append(("\u751f\u83dc\u4e3a\u6d45\u6839", root_depth_of("\u751f\u83dc") == "\u6d45"))
    r.append(("\u80e1\u841d\u535c\u4e3a\u6df1\u6839", root_depth_of("\u80e1\u841d\u535c") == "\u6df1"))
    r.append(("\u756a\u8304\u4e0e\u8304\u5b50\u540c\u79d1\u98ce\u9669\u9ad8", family_of("\u756a\u8304") == family_of("\u8304\u5b50")))
    r.append(("\u9ec4\u74dc\u4e0e\u756a\u8304\u4e0d\u540c\u79d1", family_of("\u9ec4\u74dc") != family_of("\u756a\u8304")))

    hist3 = [{"crop": "\u756a\u8304"}, {"crop": "\u8304\u5b50"}, {"crop": "\u8fa3\u6912"}]
    r.append(("\u8304\u79d1\u8fde\u4f5c 3 \u5e74\u4e3a\u9ad8\u98ce\u9669", rotation_risk(hist3, "\u756a\u8304") == 2))
    hist4 = [{"crop": "\u756a\u8304"}, {"crop": "\u8304\u5b50"}, {"crop": "\u8fa3\u6912"}, {"crop": "\u9a6c\u94c3\u85af"}]
    r.append(("\u8304\u79d1\u8fde\u4f5c 4 \u5e74\u4e3a\u6781\u9ad8", rotation_risk(hist4, "\u756a\u8304") == 3))
    r.append(("\u65e0\u5386\u53f2\u4e3a\u4f4e\u98ce\u9669", rotation_risk([], "\u756a\u8304") == 0))
    r.append(("\u6362\u79d1\u540e\u98ce\u9669\u5f52\u96f6", rotation_risk(hist3, "\u9ec4\u74dc") == 0))

    r.append(("\u756a\u8304\u63a5\u9ec4\u74dc\u6362\u79d1\u6362\u6839\u6df1\u5f97 2 \u5206", combo_score("\u756a\u8304", "\u9ec4\u74dc") == 2))
    r.append(("\u756a\u8304\u63a5\u8304\u5b50\u5f97 0 \u5206", combo_score("\u756a\u8304", "\u8304\u5b50") == 0))
    r.append(("\u9ec4\u74dc\u63a5\u751c\u74dc\u6362\u79d1\u672a\u6362\u6839\u6df1\u5f97 1 \u5206", combo_score("\u9ec4\u74dc", "\u751c\u74dc") == 1))
    r.append(("2 \u5206\u5224\u4e3a\u6ee1\u8db3", combo_score("\u756a\u8304", "\u9ec4\u74dc") >= 2))
    r.append(("1 \u5206\u5224\u4e3a\u90e8\u5206\u6ee1\u8db3", combo_score("\u9ec4\u74dc", "\u751c\u74dc") == 1))

    r.append(("\u53f6\u83dc\u7f13\u82d7 4 \u5929", TRANSPLANT_RECOVERY["\u53f6\u83dc"] == 4))
    r.append(("\u679c\u83dc\u7f13\u82d7 8 \u5929", TRANSPLANT_RECOVERY["\u679c\u83dc"] == 8))
    r.append(("\u756a\u8304\u5012\u63a8\u5929\u6570\u5927\u4e8e 25", plant_date_offset("\u756a\u8304") > 25))
    r.append(("\u751f\u83dc\u5012\u63a8\u5929\u6570\u5c0f\u4e8e\u756a\u8304", plant_date_offset("\u751f\u83dc") < plant_date_offset("\u756a\u8304")))

    txt, s = build_plan("north", hist3,
                        [{"crop": "\u9ec4\u74dc"}, {"crop": "\u756a\u8304"}], 4)
    r.append(("\u6837\u4f8b\u4ea7\u51fa\u4e24\u6761\u832c\u6b21", s["crop_count"] == 2))
    r.append(("\u6837\u4f8b\u7b2c\u4e8c\u6761\u4e3a\u9ad8\u98ce\u9669", s["items"][1]["risk"] == "\u9ad8"))
    r.append(("\u6837\u4f8b\u6709\u65e0\u79d1\u8fde\u4f5c", s["items"][0]["risk"] == "\u4f4e"))
    r.append(("\u6837\u4f8b\u9996\u6761\u65e0\u642d\u914d\u5206", s["items"][0]["combo_score"] is None))
    r.append(("\u6837\u4f8b\u4ea7\u51fa\u544a\u8b66", len(s["warnings"]) >= 1))
    r.append(("\u6837\u4f8b\u6587\u672c\u542b\u533a\u57df\u540d", "\u5317\u65b9\u65e5\u5149\u6e29\u5ba4" in txt))

    txt2, s2 = build_plan("south", [], [], 4)
    r.append(("\u5357\u65b9\u6a21\u677f\u751f\u6548", s2["region"] == "south"))
    r.append(("\u7a7a\u8ba1\u5212\u4e0d\u62a5\u9519", s2["crop_count"] == 0))
    r.append(("\u7a7a\u8ba1\u5212\u65e0\u544a\u8b66", len(s2["warnings"]) == 0))

    r.append(("BOM \u8f93\u5165\u88ab\u6b63\u786e\u5265\u79bb",
               load_json(_write_bom_sample())["region"] == "north"))
    r.append(("\u975e\u6cd5\u533a\u57df\u56de\u843d\u5317\u65b9", build_plan("west", [], [], 2)[1]["region"] == "north"))
    r.append(("\u5b57\u7b26\u4e32\u5f62\u5f0f\u7684 planned \u53ef\u89e3\u6790",
               build_plan("north", [], ["\u9ec4\u74dc"], 2)[1]["crop_count"] == 1))
    return r


def _write_bom_sample():
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "_selftest_bom_sample.json")
    with io.open(p, "w", encoding="utf-8") as f:
        f.write("\ufeff{\"region\": \"north\", \"history\": [], "
                "\"planned\": [], \"months_available\": 4}")
    return p


def selftest():
    results = _run_checks()
    failed = [name for name, ok in results if not ok]
    ok = len(failed) == 0
    lines = ["SELFTEST %s" % ("OK" if ok else "FAILED")]
    lines.append("checks=%d passed=%d failed=%d" % (
        len(results), len(results) - len(failed), len(failed)))
    for name in failed:
        lines.append("FAILED: %s" % name)
    here = os.path.dirname(os.path.abspath(__file__))
    with io.open(os.path.join(here, "_selftest_result.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    return ok


def main():
    parser = argparse.ArgumentParser(
        description="\u5927\u68da\u852c\u83dc\u832c\u53e3\u6392\u671f\u4e0e\u8fde\u4f5c\u969c\u788d\u6821\u9a8c\u5de5\u5177")
    parser.add_argument("--file", help="\u8f93\u5165 JSON \u6587\u4ef6\u8def\u5f84 (UTF-8)")
    parser.add_argument("--json", action="store_true", help="\u4ee5 JSON \u8f93\u51fa")
    parser.add_argument("--out", help="\u7ed3\u679c\u5199\u5165\u6307\u5b9a\u6587\u4ef6")
    parser.add_argument("--selftest", action="store_true", help="\u8fd0\u884c\u81ea\u68c0")
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))

    if args.selftest:
        sys.exit(0 if selftest() else 1)

    if not args.file:
        parser.error("\u9700\u8981 --file \u6216 --selftest")

    data = load_json(args.file)
    report, summary = build_plan(
        data.get("region", "north"),
        data.get("history", []),
        data.get("planned", []),
        data.get("months_available", 0),
    )
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else report
    out_path = args.out or os.path.join(here, "_last_result.txt")
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write(body)
    print(body)
    print("\u7ed3\u679c\u5df2\u5199\u5165: %s" % out_path)


if __name__ == "__main__":
    main()
