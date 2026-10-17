# -*- coding: utf-8 -*-
"""\u8001\u5e74\u4eba\u591a\u91cd\u7528\u836f\u6e05\u5355\u6574\u7406\u4e0e\u91cd\u590d\u6210\u5206\u67e5\u91cd\u5de5\u5177\u3002

\u7528\u6cd5:
  python polypharmacy_audit.py --file case.json [--dup] [--json]
  python polypharmacy_audit.py --selftest

\u672c\u5de5\u5177\u4e0d\u8f93\u51fa\u4efb\u4f55\u836f\u7269\u540d\u79f0\u7ec4\u5408\u7684\u98ce\u9669\u7ed3\u8bba\uff0c\u4e0d\u542b\u5242\u91cf\u3001\u9891\u6b21\u4e0e\u52a0\u51cf\u836f\u5efa\u8bae\u3002
"""
import argparse
import io
import json
import os
import re
import sys

# \u6210\u5206\u7c7b\u522b\u5173\u952e\u8bcd\uff1a\u4ec5\u7528\u4e8e\u8bc6\u522b\u300c\u85cf\u8eab\u5904\u300d\uff0c\u4e0d\u5224\u5b9a\u4efb\u4f55\u5177\u4f53\u7ec4\u5408\u53ef\u5426\u540c\u670d
INGREDIENT_CLASSES = {
    "antipyretic_analgesic": ["\u89e3\u70ed", "\u9547\u75db", "\u6297\u708e\u6b62\u75db"],
    "antihistamine": ["\u6297\u8fc7\u654f", "\u9632\u8fc7\u654f"],
    "antitussive": ["\u6b62\u55fd", "\u954c\u55fd"],
    "anticoagulant": ["\u6297\u51dd", "\u9632\u51dd"],
    "antiplatelet": ["\u6297\u677f", "\u9632\u57fa\u5c0f\u677f"],
    "antidiabetic": ["\u964d\u7cd6", "\u53cc\u80c6"],
    "nsaid_like": ["\u814a\u9e1f", "\u7532\u7acb\u7532\u9176", "\u53bb\u7532\u8286\u9176", "\u975e\u5806\u7c7b\u6297\u708e"],
    "electrolyte_affect": ["\u7535\u89e3\u8d28", "\u9000\u538b\u5242", "\u5229\u5c3f\u5242", "\u7518\u96c6\u5242"],
    "sedative": ["\u9547\u9759", "\u5b89\u7761", "\u60c5\u7eea", "\u50ac\u7720"],
}

RISK_CATEGORIES = [
    ("R1", "\u51fa\u8840\u98ce\u9669\u589e\u52a0",
     ["\u6297\u51dd", "\u6297\u677f", "\u9632\u57fa\u5c0f\u677f", "\u814a\u9e1f",
      "\u7532\u7acb\u7532\u9176", "\u53bb\u7532\u8286\u9176", "\u975e\u5806\u7c7b\u6297\u708e"]),
    ("R2", "\u9547\u9759\u53e0\u52a0",
     ["\u9547\u9759", "\u5b89\u7761", "\u6297\u8fc7\u654f", "\u60c5\u7eea", "\u50ac\u7720", "\u55dc\u7761"]),
    ("R3", "\u964d\u7cd6\u4f5c\u7528\u53e0\u52a0",
     ["\u964d\u7cd6", "\u53cc\u80c6"]),
    ("R4", "\u5f71\u54cd\u7535\u89e3\u8d28",
     ["\u7535\u89e3\u8d28", "\u9000\u538b\u5242", "\u5229\u5c3f\u5242", "\u7518\u96c6\u5242", "\u9187\u82b3\u9178\u5242"]),
    ("R5", "\u80be\u6bd2\u6027\u53e0\u52a0",
     ["\u814a\u9e1f", "\u7532\u7acb\u7532\u9176", "\u53bb\u7532\u8286\u9176", "\u975e\u5806\u7c7b\u6297\u708e", "\u963f\u83b2\u53f0\u683c"]),
    ("R6", "QT \u95f4\u671f\u5ef6\u957f",
     ["\u6297\u5fc3\u5f8b\u5931\u5e38", "\u5fc3\u8109\u5934\u62d3\u4f5c\u7528", "\u6bd2\u6027\u4e16\u754c\u7ec4\u53ef"]),
]

RISK_OBSERVE = {
    "R1": "\u7259\u9f7f\u51fa\u8840\u3001\u9f3b\u51fa\u8840\u3001\u76ae\u4e0b\u75b9\u6591\u3001\u9ed1\u4fbf\u3001\u5455\u8840\u3001\u5c3f\u8840",
    "R2": "\u767d\u5929\u561f\u7761\u53eb\u4e0d\u9192\u3001\u8bf4\u8bdd\u542b\u7cca\u3001\u8d70\u8def\u4e0d\u7a33\u3001\u8dcc\u5012",
    "R3": "\u5fc3\u6145\u3001\u51fa\u51b7\u6c57\u3001\u624b\u6296\u3001\u610f\u8bc6\u6a21\u7cca",
    "R4": "\u529b\u7aed\u3001\u624b\u8db3\u9ebb\u6728\u3001\u5fc3\u5f8b\u4e0d\u9f50\u3001\u98df\u6b32\u6781\u5dee",
    "R5": "\u5c3f\u91cf\u51cf\u5c11\u3001\u5c3f\u8272\u52a0\u6df1\u3001\u4e0b\u80bf\u6c34\u80bf\u3001\u6076\u5fc3",
    "R6": "\u5fc3\u6162\u3001\u80f8\u95f7\u3001\u8109\u640f\u660e\u663e\u4e0d\u9f50\u3001\u6655\u53e5",
}

EMERGENCY = [
    "fall_head_injury", "vomit_blood", "melena", "uncontrolled_bleeding",
    "dyspnea", "cyanosis", "severe_rash_dyspnea",
    "sudden_confusion", "unresponsiveness",
    "palpitation_chest_pain", "fever_urinary_block",
]

EMERGENCY_TEXT = {
    "fall_head_injury": "\u8dcc\u5012\u540e\u5934\u90e8\u7740\u5730\u3001\u610f\u8bc6\u6539\u53d8\u3001\u541e\u5410\u3001\u5267\u70c8\u5934\u75db\u3001\u8bed\u8a00\u4e0d\u6e05\u3001\u5355\u4fa7\u65e0\u529b\u3001\u62bd\u6410",
    "vomit_blood": "\u5455\u8840",
    "melena": "\u9ed1\u4fbf\u3001\u67a0\u6cb9\u6837\u4fbf\u3001\u4fbf\u8840\u3001\u5c3f\u8840",
    "uncontrolled_bleeding": "\u76ae\u4e0b\u5927\u7247\u75b9\u6591\u6216\u51fa\u8840\u4e0d\u6b62",
    "dyspnea": "\u547c\u5438\u56f0\u96be\u3001\u5587\u5934\u6c34\u80bf\u611f",
    "cyanosis": "\u53e3\u5507\u53d1\u7d2b",
    "severe_rash_dyspnea": "\u4e25\u91cd\u76ae\u75b9\u4f34\u547c\u5438\u56f0\u96be",
    "sudden_confusion": "\u610f\u8bc6\u7a81\u7136\u6df7\u4e71\u3001\u5609\u7761\u53eb\u4e0d\u9192\u3001\u8bf4\u8bdd\u542b\u7cca\u3001\u77b3\u5b54\u5f02\u5e38",
    "palpitation_chest_pain": "\u5fc3\u6162\u3001\u80f8\u75db\u3001\u8109\u640f\u660e\u663e\u4e0d\u9f50\u3001\u8840\u538b\u5f02\u5e38\u5347\u9ad8\u4f34\u5934\u75db\u80f8\u95f7",
    "fever_urinary_block": "\u5bfc\u5c3f\u7ba1\u5835\u585e\u4f34\u53d1\u70ed\u3001\u5c3f\u75db\u3001\u5c3f\u6db2\u6d51\u6d4a\u6709\u5f02\u5473",
}

SAME_DAY = [
    "new_discomfort", "missed_or_wrong_dose", "self_adjust_symptom",
    "skin_reaction", "appetite_loss", "urine_reduction", "mood_change",
]

SAME_DAY_TEXT = {
    "new_discomfort": "\u65b0\u51fa\u73b0\u7684\u4e0d\u9002\uff1a\u5934\u6655\u3001\u529b\u7aed\u3001\u6076\u5fc3\u3001\u8179\u6cfb\u3001\u53e3\u5e72\u3001\u89c6\u7269\u6a21\u7cca\u3001\u4fbf\u79c1",
    "missed_or_wrong_dose": "\u6f0f\u670d\u3001\u9519\u670d\u3001\u91cd\u590d\u670d\u7528\u540e\u51fa\u73b0\u4efb\u4f55\u5f02\u5e38",
    "self_adjust_symptom": "\u81ea\u884c\u51cf\u91cf\u3001\u505c\u836f\u6216\u6362\u836f\u540e\u75c7\u72b6\u53d8\u5316",
    "skin_reaction": "\u76ae\u75b9\u3001\u7619\u75d2\u3001\u9762\u90e8\u6216\u53e3\u5507\u80bf\u80fa",
    "appetite_loss": "\u98df\u6b32\u660e\u663e\u4e0b\u964d\u3001\u4f53\u91cd\u5feb\u901f\u4e0b\u964d\u3001\u6301\u7eed\u541e\u5410\u6216\u8179\u6cfb",
    "urine_reduction": "\u5c3f\u91cf\u660e\u663e\u51cf\u5c11\u3001\u4e0b\u80bf\u6c34\u80bf",
    "mood_change": "\u60c5\u7eea\u660e\u663e\u6539\u53d8\u3001\u7a81\u7136\u8bdd\u5c11\u6216\u60c5\u7eea\u4f4e\u843d",
}

FORBIDDEN = [
    "\u7981\u6b62\u64c5\u81ea\u505c\u7528\u6162\u6027\u75c5\u57fa\u7840\u7528\u836f\uff08\u964d\u538b\u3001\u964d\u7cd6\u3001\u6297\u51dd\u3001\u6297\u5fc3\u5f8b\u5931\u5e38\u3001\u954c\u75db\u3001\u60c5\u7eea\u7c7b\u7b49\uff09",
    "\u7981\u6b62\u51ed\u611f\u89c9\u597d\u8f6c\u81ea\u884c\u51cf\u91cf\u6216\u505c\u836f",
    "\u7981\u6b62\u7528\u4fdd\u5065\u54c1\u6216\u8c03\u7406\u54c1\u66ff\u4ee3\u5904\u65b9\u836f",
    "\u7981\u6b62\u4e00\u6b21\u4e70\u591a\u79cd\u836f\u540e\u770b\u54ea\u4e2a\u7ba1\u7528\u5403\u54ea\u4e2a",
    "\u7981\u6b62\u51ed\u5e7f\u544a\u6216\u4ed6\u4eba\u7ecf\u9a8c\u7528\u836f",
    "\u7981\u6b62\u6f0f\u670d\u540e\u81ea\u884c\u52a0\u500d\u8865\u670d",
    "\u7981\u6b62\u628a\u836f\u5206\u5230\u65e0\u6807\u7b7e\u7684\u5c0f\u76d2\u5b50\u91cc",
    "\u7981\u6b62\u81ea\u884c\u5224\u65ad\u4e24\u836f\u80fd\u5426\u540c\u670d\u5e76\u636e\u6b64\u505c\u6389\u5176\u4e00",
    "\u7981\u6b62\u590d\u8bca\u65f6\u4e0d\u5e26\u6e05\u5355",
]

FIELD_SPEC = [
    ("generic", "\u901a\u7528\u540d", "\u6240\u6709\u540e\u7eed\u5224\u65ad\u7684\u552f\u4e00\u4f9d\u636e"),
    ("brand", "\u5546\u54c1\u540d", "\u53ea\u4f5c\u5bf9\u7167\uff0c\u4e0d\u7528\u4e8e\u5224\u65ad"),
    ("form", "\u5242\u578b", "\u540c\u4e00\u6210\u5206\u4e0d\u540c\u5242\u578b\u53ef\u80fd\u91cd\u590d"),
    ("dose", "\u5355\u6b21\u5242\u91cf", "\u590d\u6838\u7528\uff0c\u672c\u5de5\u5177\u4e0d\u636e\u6b64\u7ed9\u5efa\u8bae"),
    ("freq", "\u7528\u836f\u65f6\u95f4", "\u8bc6\u522b\u53e0\u52a0\u4e0e\u95f4\u9694\u95ee\u9898"),
    ("indication", "\u7528\u9014", "\u53d1\u73b0\u7528\u9014\u91cd\u53e0"),
    ("prescriber", "\u5f00\u5904\u65b9\u533b\u751f", "\u5c31\u8bca\u65f6\u6309\u79d1\u5ba4\u6838\u5bf9"),
]

COMPOUND_NOTE = "\u590d\u65b9\u5236\u5242\u5fc5\u987b\u6284\u5168\u5168\u90e8\u6210\u5206\uff0c\u91cd\u590d\u6210\u5206\u5f80\u5f80\u85cf\u5728\u590d\u65b9\u91cc"


def strip_fields(raw):
    """\u5f52\u4e00\u5316\u6210\u5206\u5b57\u7b26\u4e32\uff1a\u53bb\u7a7a\u767d\u3001\u8f6c\u5c0f\u5199\u3002"""
    s = "".join(raw or [])
    s = re.sub(r"\s+", "", s)
    return s.lower()


def med_text(m):
    parts = [str(m.get("generic", "") or ""), str(m.get("brand", "") or ""),
             str(m.get("form", "") or ""), str(m.get("indication", "") or ""),
             str(m.get("class", "") or "")]
    parts += list(m.get("ingredients", []) or [])
    return strip_fields("|".join(p for p in parts if p))


def find_dup(meds):
    """\u8fd4\u56de [(\u6210\u5206\u5173\u952e\u8bcd, [\u884c\u53f7...]), ...]\u3002\u4ec5\u63d0\u793a\u9700\u8981\u95ee\u533b\u751f\uff0c\u4e0d\u7ed9\u98ce\u9669\u7ed3\u8bba\u3002"""
    hits = []
    seen = set()
    for kws in INGREDIENT_CLASSES.values():
        for keyword in kws:
            if keyword in seen:
                continue
            seen.add(keyword)
            rows = [i + 1 for i, m in enumerate(meds) if keyword in med_text(m)]
            if len(rows) >= 2:
                hits.append((keyword, rows))
    hits.sort(key=lambda x: x[0])
    return hits


def risk_tags(meds):
    """\u6309\u516d\u7c7b\u98ce\u9669\u5f52\u6863\uff0c\u8fd4\u56de [(\u7f16\u53f7, \u540d\u79f0, [\u884c\u53f7...]), ...]\u3002"""
    out = []
    for code, label, keywords in RISK_CATEGORIES:
        rows = []
        for i, m in enumerate(meds):
            t = med_text(m)
            if any(k in t for k in keywords):
                rows.append(i + 1)
        out.append((code, label, rows))
    return out


def missing_fields(meds):
    gaps = []
    for i, m in enumerate(meds):
        miss = [label for key, label, _why in FIELD_SPEC
                if not str(m.get(key, "") or "").strip()]
        if miss:
            gaps.append((i + 1, miss))
    return gaps


def known_classes(raw):
    valid = set(INGREDIENT_CLASSES)
    good, bad = [], []
    for k in list(raw or []):
        if k in valid:
            good.append(k)
        else:
            bad.append(k)
    return good, bad


def build_report(data):
    meds = list(data.get("meds", []))
    flags = list(data.get("red_flags", []))
    classes = list(data.get("classes", []))
    pillbox = data.get("pillbox_days", 7)

    lines = []
    lines.append("=" * 66)
    lines.append("\u8001\u5e74\u4eba\u591a\u91cd\u7528\u836f\u6e05\u5355\u6574\u7406\u4e0e\u67e5\u91cd")
    lines.append("=" * 66)
    lines.append("\u6e05\u5355\u836f\u7269\u6570\uff1a%d \u79cd   \u5206\u836f\u76d2\u5468\u671f\uff1a%g \u5929"
                 % (len(meds), float(pillbox or 7)))
    lines.append("")

    em = [f for f in flags if f in EMERGENCY]
    sd = [f for f in flags if f in SAME_DAY]
    unknown = [f for f in flags if f not in EMERGENCY and f not in SAME_DAY]
    if em or sd:
        lines.append("[\u7ea2\u7ebf] \u5df2\u547d\u4e2d\u4e0b\u5217\u60c5\u5f62\uff0c\u5148\u5904\u7f6e\u518d\u8c08\u6574\u7406\uff1a")
        for f in em:
            lines.append("  ! \u7acb\u5373\u5c31\u533b\uff1a" + EMERGENCY_TEXT[f])
        for f in sd:
            lines.append("  ! \u5f53\u5929\u8054\u7cfb\u533b\u751f\uff1a" + SAME_DAY_TEXT[f])
        lines.append("")
        lines.append("  \u672c\u5de5\u5177\u4e0d\u7ed9\u51fa\u7528\u836f\u6574\u7406\u5efa\u8bae\uff0c\u4e0d\u7ed9\u5242\u91cf\u4e0e\u52a0\u51cf\u836f\u65b9\u6848\u3002")
        lines.append("=" * 66)
        return "\n".join(lines), {
            "blocked": True,
            "emergency": em,
            "same_day": sd,
            "unknown_flags": unknown,
            "medication_adjustment_provided": False,
            "drug_pair_verdict_provided": False,
        }

    lines.append("[\u4e00] \u6e05\u5355\u5b57\u6bb5\u5b8c\u6574\u6027")
    gaps = missing_fields(meds)
    if gaps:
        lines.append("  \u4ee5\u4e0b\u884c\u5b58\u5728\u7f3a\u5931\u5b57\u6bb5\uff0c\u8865\u9f50\u524d\u4e0d\u8fdb\u884c\u98ce\u9669\u5224\u65ad\uff1a")
        for row, miss in gaps:
            lines.append("    \u7b2c %d \u884c\u7f3a\uff1a%s" % (row, "\u3001".join(miss)))
    else:
        lines.append("  \u6240\u6709\u836f\u7269\u884c\u5747\u5df2\u586b\u9f50 7 \u4e2a\u5fc5\u5907\u5b57\u6bb5")
    lines.append("  " + COMPOUND_NOTE)
    lines.append("")

    lines.append("[\u4e8c] \u91cd\u590d\u6210\u5206\u68c0\u67e5")
    dup = find_dup(meds)
    if dup:
        lines.append("  \u4ee5\u4e0b\u6210\u5206\u5728 2 \u79cd\u53ca\u4ee5\u4e0a\u836f\u7269\u4e2d\u51fa\u73b0\uff0c\u9700\u5411\u533b\u751f\u6216\u836f\u5e08\u786e\u8ba4\uff1a")
        for kw, rows in dup:
            lines.append("    - %s \u51fa\u73b0\u5728\u7b2c %s \u884c" % (kw, "\u3001".join(str(x) for x in rows)))
    else:
        lines.append("  \u672a\u68c0\u51fa\u91cd\u590d\u6210\u5206\uff08\u4e14\u8bf4\u660e\uff1a\u672a\u68c0\u51fa\u4e0d\u7b49\u4e8e\u5b58\u5728\u98ce\u9669\uff09")
    lines.append("  \u53e3\u5f84\uff1a\u672c\u8868\u53ea\u63d0\u793a\u9700\u8981\u5411\u533b\u751f\u6216\u836f\u5e08\u786e\u8ba4\uff0c\u4e0d\u5224\u5b9a\u4efb\u4f55\u5177\u4f53\u7ec4\u5408\u80fd\u5426\u540c\u670d\u3002")
    lines.append("")

    lines.append("[\u4e09] \u516d\u7c7b\u98ce\u9669\u7c7b\u522b\u5f52\u6863\uff08\u4ec5\u6807\u9700\u95ee\u533b\u751f\uff09")
    tags = risk_tags(meds)
    for code, label, rows in tags:
        if rows:
            lines.append("  %s %s\uff1a\u6d89\u53ca\u7b2c %s \u884c\uff08\u9700\u95ee\u533b\u751f\uff09"
                         % (code, label, "\u3001".join(str(x) for x in rows)))
            lines.append("      \u5bb6\u5c5e\u89c2\u5bdf\uff1a" + RISK_OBSERVE[code])
    if not any(rows for _c, _l, rows in tags):
        lines.append("  \u672a\u6807\u8bb0\u5230\u516d\u7c7b\u98ce\u9669\u7c7b\u522b\u5173\u8054\u884c")
    lines.append("")

    lines.append("[\u56db] \u5206\u836f\u76d2\u4e0e\u6838\u5bf9\u673a\u5236")
    d = float(pillbox or 7)
    lines.append("  \u5206\u836f\u76d2\u5468\u671f\uff1a%g \u5929\uff0c\u6bcf\u5468\u56fa\u5b9a\u540c\u4e00\u5929\u88c5\u76d2\u5e76\u53cc\u4eba\u6838\u5bf9\u3002" % d)
    lines.append("  \u88c5\u76d2\u89c4\u5219\uff1a")
    for x in [
        "\u4fdd\u7559\u539f\u5305\u88c5\u4e0e\u8bf4\u660e\u4e66\uff0c\u4e0d\u6563\u88c5\u4e22\u5f03",
        "\u6807\u7b7e\u53ea\u5199\u65e9\u4e2d\u665a\u591c\u7b49\u6700\u5c0f\u4fe1\u606f",
        "\u5916\u7528\u836f\u5355\u72ec\u6536\u7eb3\u5e76\u6807\u660e\u5916\u7528",
        "\u4fdd\u5065\u54c1\u4e0e\u4e2d\u836f\u4e0e\u5904\u65b9\u836f\u5206\u5f00\u653e",
        "\u5916\u89c2\u76f8\u4f3c\u7684\u767d\u8272\u836f\u7247\u4e0d\u6df7\u683c",
    ]:
        lines.append("    - " + x)
    lines.append("  \u6838\u5bf9\u4eba\u6b21\u4e0d\u5f97\u7701\uff1a\u6bcf\u5468\u88c5\u76d2\u53cc\u4eba\u6838\u5bf9\u5e76\u786e\u8ba4\uff0c\u6bcf\u6b21\u5c31\u8bca\u5e26\u56de\u65b0\u836f\u540e\u91cd\u65b0\u6574\u7406\u3002")
    lines.append("")

    lines.append("[\u4e94] \u5f53\u5929\u8054\u7cfb\u533b\u751f\u7684\u60c5\u5f62\uff08\u672a\u547d\u4e2d\u7ea2\u7ebf\u65f6\u4ecd\u9700\u89c2\u5bdf\uff09")
    for k in SAME_DAY:
        lines.append("  - " + SAME_DAY_TEXT[k])
    lines.append("")

    lines.append("[\u516d] \u660e\u786e\u7981\u6b62\u505a\u6cd5")
    for f in FORBIDDEN:
        lines.append("  - " + f)
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u6574\u7406\u4e0e\u5f52\u7c7b\u53c2\u8003\uff0c\u4e0d\u6784\u6210\u5904\u65b9\u5efa\u8bae\u3002")
    lines.append("\u662f\u5426\u9700\u8c03\u6574\u7528\u836f\u3001\u67d0\u4e24\u836f\u80fd\u5426\u5408\u5e76\uff0c\u5fc5\u987b\u7531\u5f00\u5904\u65b9\u7684\u533b\u751f\u6216\u836f\u5e08\u5224\u65ad\u3002")
    lines.append("=" * 66)

    summary = {
        "blocked": False,
        "unknown_flags": unknown,
        "med_count": len(meds),
        "field_gaps": gaps,
        "dup_hits": dup,
        "dup_count": len(dup),
        "risk_tags": tags,
        "pillbox_days": d,
        "medication_adjustment_provided": False,
        "drug_pair_verdict_provided": False,
        "dose_provided": False,
        "diagnosis_provided": False,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("\u6210\u5206\u7c7b\u522b\u5df2\u5b9a\u4e49", len(INGREDIENT_CLASSES) >= 8))
    r.append(("\u98ce\u9669\u7c7b\u522b\u4e3a 6 \u7c7b", len(RISK_CATEGORIES) == 6))
    r.append(("\u98ce\u9669\u89c2\u5bdf\u4fe1\u53f7\u8986\u76d6 6 \u7c7b",
              all(c in RISK_OBSERVE for c, _l, _k in RISK_CATEGORIES)))
    r.append(("\u7acb\u5373\u5c31\u533b\u60c5\u5f62\u81f3\u5c11 10 \u6761", len(EMERGENCY) >= 10))
    r.append(("\u5f53\u5929\u8054\u7cfb\u60c5\u5f62\u81f3\u5c11 7 \u6761", len(SAME_DAY) >= 7))
    r.append(("\u7981\u6b62\u505a\u6cd5\u81f3\u5c11 8 \u6761", len(FORBIDDEN) >= 8))
    r.append(("\u6e05\u5355\u5fc5\u5907\u5b57\u6bb5\u4e3a 7 \u9879", len(FIELD_SPEC) == 7))

    good, bad = known_classes(["antipyretic_analgesic", "nope"])
    r.append(("\u5df2\u8bc6\u522b\u7c7b\u522b\u8ba1\u6570\u6b63\u786e", good == ["antipyretic_analgesic"]))
    r.append(("\u672a\u8bc6\u522b\u7c7b\u522b\u88ab\u8fc7\u6ee4", bad == ["nope"]))

    m1 = {"generic": "\u6297\u51dd\u836f", "brand": "A", "form": "\u7247", "dose": "1",
          "freq": "\u65e9\u665a", "indication": "\u623f\u98a4",
          "prescriber": "\u5fc3\u5185\u79d1", "ingredients": []}
    m2 = {"generic": "\u9547\u75db\u836f", "brand": "B", "form": "\u7247", "dose": "1",
          "freq": "\u665a", "indication": "\u5173\u8282\u75db", "prescriber": "\u5bb6\u5ead\u533b\u751f",
          "ingredients": ["\u89e3\u70ed\u9547\u75db\u6210\u5206"]}

    dup1 = find_dup([m1, m2])
    r.append(("\u65e0\u91cd\u590d\u6210\u5206\u65f6\u8fd4\u56de\u7a7a", dup1 == []))
    cold = {"generic": "\u590d\u65b9\u611f\u5192\u836f", "brand": "C", "form": "\u7c92\u7c92",
            "dose": "1", "freq": "\u65e5", "indication": "\u611f\u5192",
            "prescriber": "\u793e\u533a\u533b\u751f",
            "ingredients": ["\u89e3\u70ed\u9547\u75db\u6210\u5206", "\u6297\u8fc7\u654f\u6210\u5206", "\u954c\u55fd\u6210\u5206"]}
    dup2 = find_dup([cold, m2])
    r.append(("\u590d\u65b9\u611f\u5192\u836f\u4e0e\u5355\u72ec\u9547\u75db\u836f\u547d\u4e2d\u91cd\u590d",
              any("\u89e3\u70ed" in kw for kw, _rows in dup2)))
    r.append(("\u91cd\u590d\u547d\u4e2d\u884c\u53f7\u4e3a\u4e24\u884c", all(len(rows) == 2 for _kw, rows in dup2)))
    r.append(("\u590d\u65b9\u611f\u5192\u836f\u547d\u4e2d\u81f3\u5c11\u4e09\u4e2a\u6210\u5206\u7c7b\u522b",
              sum(1 for kws in INGREDIENT_CLASSES.values()
                  if any(k in med_text(cold) for k in kws)) >= 3))

    tags = risk_tags([m1, m2])
    r.append(("\u98ce\u9669\u5f52\u6863\u8fd4\u56de 6 \u7c7b", len(tags) == 6))
    r1 = dict((c, rows) for c, _l, rows in tags)["R1"]
    r.append(("\u6297\u51dd\u836f\u547d\u4e2d R1 \u51fa\u8840\u7c7b\u522b", 1 in r1))
    r2 = dict((c, rows) for c, _l, rows in tags)["R2"]
    r.append(("\u4e24\u836f\u5747\u672a\u547d\u4e2d R2 \u9547\u9759\u7c7b\u522b", len(r2) == 0))

    full = dict(m1, generic="\u6297\u51dd\u836f", brand="\u5546\u54c1A", form="\u7247", dose="1",
                freq="\u65e9\u665a", indication="\u623f\u98a4", prescriber="\u5fc3\u5185\u79d1")
    r.append(("\u5b57\u6bb5\u9f50\u5168\u65f6\u65e0\u7f3a\u53e3", missing_fields([full]) == []))
    partial = {"generic": "\u6d4b\u8bd5\u836f", "brand": "\u6d4b", "form": "\u7247"}
    gaps_only = missing_fields([partial])
    r.append(("\u7f3a\u5b57\u6bb5\u65f6\u80fd\u62a5\u51fa\u884c\u53f7", gaps_only[0][0] == 1))
    r.append(("\u7f3a\u5931\u5b57\u6bb5\u5217\u8868\u975e\u7a7a", len(gaps_only[0][1]) == 4))
    r.append(("\u65e0\u7f3a\u53e3\u65f6\u8fd4\u56de\u7a7a\u5217\u8868", missing_fields([]) == []))

    _, s = build_report({"meds": [full, cold, m2]})
    r.append(("\u5b8c\u6574\u6837\u4f8b\u4e0d\u963b\u65ad", s["blocked"] is False))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u68c0\u51fa\u91cd\u590d\u6210\u5206", s["dup_count"] >= 1))
    r.append(("\u6837\u4f8b\u65e0\u5b57\u6bb5\u7f3a\u53e3", s["field_gaps"] == []))
    r.append(("\u4e0d\u7ed9\u7528\u836f\u8c03\u6574\u5efa\u8bae", s["medication_adjustment_provided"] is False))
    r.append(("\u4e0d\u7ed9\u5177\u4f53\u7ec4\u5408\u53ef\u5426\u540c\u670d\u7ed3\u8bba", s["drug_pair_verdict_provided"] is False))
    r.append(("\u4e0d\u7ed9\u5242\u91cf", s["dose_provided"] is False))
    r.append(("\u4e0d\u4e0b\u8bca\u65ad\u7ed3\u8bba", s["diagnosis_provided"] is False))

    _, s2 = build_report({"meds": [full], "red_flags": ["melena"]})
    r.append(("\u9ed1\u4fbf\u76f4\u63a5\u963b\u65ad", s2["blocked"] is True))
    r.append(("\u963b\u65ad\u65f6\u4e0d\u7ed9\u67e5\u91cd\u7ed3\u679c", "dup_count" not in s2))
    r.append(("\u963b\u65ad\u65f6\u4e0d\u7ed9\u52a0\u51cf\u836f\u65b9\u6848", s2["medication_adjustment_provided"] is False))

    _, s3 = build_report({"meds": [full], "red_flags": ["appetite_loss"]})
    r.append(("\u5f53\u5929\u8054\u7cfb\u4e5f\u963b\u65ad", s3["blocked"] is True))
    r.append(("\u963b\u65ad\u65f6\u533a\u5206\u5373\u5c31\u533b\u4e0e\u5f53\u5929", s3["emergency"] == []))
    r.append(("\u963b\u65ad\u65f6\u5f53\u5929\u60c5\u5f62\u975e\u7a7a", len(s3["same_day"]) == 1))

    txt, _ = build_report({"meds": [full, cold, m2]})
    r.append(("\u8f93\u51fa\u542b\u7981\u6b62\u64c5\u81ea\u505c\u836f", "\u7981\u6b62\u64c5\u81ea\u505c\u7528" in txt))
    txt_clean, _ = build_report({"meds": [full]})
    r.append(("\u65e0\u91cd\u590d\u65f6\u8f93\u51fa\u542b\u4e0d\u7b49\u4e8e\u5b58\u5728\u98ce\u9669\u53e3\u5f84",
              "\u4e0d\u7b49\u4e8e\u5b58\u5728\u98ce\u9669" in txt_clean))
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
    parser = argparse.ArgumentParser(
        description="\u8001\u5e74\u4eba\u591a\u91cd\u7528\u836f\u6e05\u5355\u6574\u7406\u4e0e\u91cd\u590d\u6210\u5206\u67e5\u91cd\u5de5\u5177")
    parser.add_argument("--file", help="\u8f93\u5165 JSON \u6587\u4ef6\u8def\u5f84\uff08UTF-8\uff09")
    parser.add_argument("--dup", action="store_true", help="\u53ea\u8dd1\u91cd\u590d\u6210\u5206\u4e0e\u7c7b\u522b\u67e5\u91cd")
    parser.add_argument("--json", action="store_true", help="\u4ee5 JSON \u8f93\u51fa")
    parser.add_argument("--out", help="\u7ed3\u679c\u5199\u5165\u6307\u5b9a\u6587\u4ef6")
    parser.add_argument("--selftest", action="store_true", help="\u8fd0\u884c\u81ea\u68c0")
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))

    if args.selftest:
        sys.exit(0 if selftest() else 1)

    if not args.file:
        parser.error("\u9700\u8981 --file \u6216 --selftest")

    with io.open(args.file, "r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)

    if args.dup:
        meds = list(data.get("meds", []))
        dup = find_dup(meds)
        tags = risk_tags(meds)
        lines = ["=" * 66,
                 "\u91cd\u590d\u6210\u5206\u4e0e\u516d\u7c7b\u98ce\u9669\u7c7b\u522b\u67e5\u91cd", "=" * 66]
        if dup:
            for kw, rows in dup:
                lines.append("  - %s \u51fa\u73b0\u5728\u7b2c %s \u884c\uff08\u9700\u5411\u533b\u751f\u6216\u836f\u5e08\u786e\u8ba4\uff09"
                             % (kw, "\u3001".join(str(x) for x in rows)))
        else:
            lines.append("  \u672a\u68c0\u51fa\u91cd\u590d\u6210\u5206\uff08\u4e0d\u7b49\u4e8e\u5b58\u5728\u98ce\u9669\uff09")
        lines.append("")
        for code, label, rows in tags:
            if rows:
                lines.append("  %s %s\uff1a\u7b2c %s \u884c"
                             % (code, label, "\u3001".join(str(x) for x in rows)))
        lines.append("")
        lines.append("\u672c\u5de5\u5177\u4e0d\u5224\u5b9a\u4efb\u4f55\u5177\u4f53\u7ec4\u5408\u80fd\u5426\u540c\u670d\uff0c\u4e0d\u7ed9\u5242\u91cf\u4e0e\u52a0\u51cf\u836f\u65b9\u6848\u3002")
        lines.append("=" * 66)
        report = "\n".join(lines)
        summary = {"dup_count": len(dup), "dup_hits": dup, "risk_tags": tags,
                   "drug_pair_verdict_provided": False, "dose_provided": False}
    else:
        report, summary = build_report(data)

    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else report
    out_path = args.out or os.path.join(here, "_last_result.txt")
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write(body)
    print(body)
    print("")
    print("\u7ed3\u679c\u5df2\u5199\u5165\uff1a%s" % out_path)


if __name__ == "__main__":
    main()
