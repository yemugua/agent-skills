# -*- coding: utf-8 -*-
"""service_interval_check: \u6c7d\u8f66\u4fdd\u517b\u7684\u91cc\u7a0b\u4e0e\u65f6\u95f4\u53cc\u8f68\u5224\u5b9a\u3002

\u53ea\u505a\u7ed3\u6784\u6027\u5224\u5b9a\uff0c\u4e0d\u5185\u7f6e\u4efb\u4f55\u5177\u4f53\u5468\u671f\u6570\u503c\u3002
"""
import argparse
import json
import os

# (\u9879\u76ee, \u4f5c\u7528, \u5468\u671f\u53e3\u5f84, \u662f\u5426\u5b89\u5168\u76f8\u5173)
ITEMS = [
    ("\u673a\u6cb9", "\u6da6\u6ed1\u3001\u6e05\u6d01\u3001\u5e26\u8d70\u78e8\u635f\u9897\u7c92\u4e0e\u70ed\u91cf", "\u91cc\u7a0b\u4e0e\u65f6\u95f4\u5148\u5230\u8005\u4e3a\u51c6", False),
    ("\u673a\u6ee4", "\u62e6\u622a\u673a\u6cb9\u4e2d\u7684\u9897\u7c92\u6742\u8d28", "\u901a\u5e38\u4e0e\u673a\u6cb9\u540c\u6b65\u6216\u66f4\u9891\u7e41", False),
    ("\u7a7a\u6ee4", "\u8fc7\u6ee4\u8fdb\u5165\u53d1\u52a8\u673a\u7684\u7a7a\u6c14", "\u6309\u91cc\u7a0b\uff0c\u5c18\u571f\u591a\u7684\u5730\u533a\u66f4\u9891\u7e41", False),
    ("\u6c7d\u6ee4", "\u8fc7\u6ee4\u71c3\u6cb9\u4e2d\u7684\u6742\u8d28", "\u6309\u91cc\u7a0b", False),
    ("\u51b7\u5374\u6db2", "\u5e26\u8d70\u53d1\u52a8\u673a\u70ed\u91cf\u3001\u9632\u51bb\u9632\u6cb8", "\u6309\u91cc\u7a0b\u4e0e\u65f6\u95f4", False),
    ("\u53d8\u901f\u7bb1\u6cb9", "\u6da6\u6ed1\u4e0e\u6db2\u538b\u4f20\u52a8", "\u6309\u91cc\u7a0b\u4e0e\u65f6\u95f4\uff0c\u81ea\u52a8\u53d8\u901f\u7bb1\u66f4\u654f\u611f", False),
    ("\u5239\u8f66\u6cb9", "\u5236\u52a8\u6db2\u538b\u4f20\u9012", "\u6309\u65f6\u95f4\u4e3a\u4e3b\uff0c\u542b\u6c34\u91cf\u968f\u65f6\u95f4\u4e0a\u5347", True),
    ("\u706b\u82b1\u585e", "\u70b9\u706b", "\u6309\u91cc\u7a0b\uff0c\u4e0d\u540c\u7c7b\u578b\u5dee\u5f02\u5f88\u5927", False),
    ("\u5239\u8f66", "\u5236\u52a8\u529f\u80fd", "\u6309\u5b9e\u9645\u78e8\u635f\u68c0\u67e5\uff0c\u4e0d\u662f\u56fa\u5b9a\u5468\u671f", True),
    ("\u8f6e\u80ce", "\u6293\u5730\u4e0e\u627f\u8f7d", "\u6309\u78e8\u635f\u72b6\u6001\u4e0e\u5e74\u9650\uff0c\u4e0d\u662f\u56fa\u5b9a\u5468\u671f", True),
    ("\u96e8\u5237", "\u89c6\u91ce", "\u6309\u4f7f\u7528\u72b6\u6001\uff0c\u6a61\u80f6\u4f1a\u8001\u5316", False),
]

EXTRA_ITEMS = [
    ("\u6e05\u6d17\u8282\u6c14\u95e8", "\u72b6\u6001\u76f8\u5173\uff0c\u4e0d\u662f\u6240\u6709\u8f66\u5230\u70b9\u5c31\u5fc5\u987b\u505a"),
    ("\u6e05\u6d17\u55b7\u6cb9\u5634", "\u72b6\u6001\u76f8\u5173\uff0c\u4e0d\u662f\u6240\u6709\u8f66\u5230\u70b9\u5c31\u5fc5\u987b\u505a"),
    ("\u53d8\u901f\u7bb1\u6df1\u5ea6\u4fdd\u517b", "\u6309\u91cc\u7a0b\u4e0e\u65f6\u95f4\u4e3a\u4e3b\uff0c\u81ea\u52a8\u53d8\u901f\u7bb1\u901a\u5e38\u66f4\u654f\u611f\uff0c\u4e0d\u662f\u60f3\u6d17\u5c31\u6d17"),
    ("\u71c3\u6cb9\u6dfb\u52a0\u5242", "\u4e0d\u5c5e\u4e8e\u5e38\u89c4\u5fc5\u5907\u9879\u76ee"),
    ("\u7a7a\u8c03\u6ee4\u82af", "\u7070\u5c18\u591a\u7684\u5730\u533a\u786e\u5b9e\u9700\u8981\u66f4\u9891\u7e41\uff0c\u4f46\u8981\u6309\u8bf4\u660e\u4e66\u5468\u671f"),
]

CONDITIONS = {
    "normal": ("\u5e38\u89c4\u5de5\u51b5", "\u6309\u8bf4\u660e\u4e66\u5468\u671f\u5373\u53ef"),
    "shorttrip": ("\u957f\u671f\u77ed\u9014", "\u53d1\u52a8\u673a\u65e0\u6cd5\u5145\u5206\u70ed\u900f\uff0c\u53ef\u80fd\u9700\u8981\u7f29\u77ed\u5468\u671f"),
    "harsh": ("\u6076\u52a3\u73af\u5883", "\u6c99\u5c18\u6ce5\u6d46\u7b49\u73af\u5883\u6ee4\u82af\u6d88\u8017\u5feb\uff0c\u53ef\u80fd\u9700\u8981\u7f29\u77ed\u5468\u671f"),
    "trailer": ("\u9891\u7e41\u62d6\u6302", "\u8d1f\u8377\u52a0\u91cd\uff0c\u53ef\u80fd\u9700\u8981\u7f29\u77ed\u5468\u671f"),
    "highalt": ("\u9ad8\u539f", "\u7a7a\u6c14\u7a00\u8584\u3001\u5de5\u51b5\u4e0d\u540c\uff0c\u6309\u5382\u5bb6\u8981\u6c42\uff0c\u5fc5\u8981\u65f6\u54a8\u8be2"),
    "idle": ("\u957f\u671f\u6020\u901f", "\u6cb9\u6db2\u4e0e\u79ef\u78b3\u76f8\u5173\uff0c\u53ef\u80fd\u9700\u8981\u7f29\u77ed\u5468\u671f"),
}

RECORD_WHY = [
    "\u5224\u65ad\u8f66\u51b5\uff1a\u77e5\u9053\u5386\u53f2\u4e0a\u505a\u8fc7\u4ec0\u4e48",
    "\u4e8c\u624b\u8f66\u8bc4\u4f30\uff1a\u8bb0\u5f55\u5b8c\u6574\u7684\u8f66\u66f4\u5bb9\u6613\u88ab\u5408\u7406\u4f30\u4ef7",
    "\u8d28\u4fdd\u4f9d\u636e\uff1a\u8d28\u4fdd\u671f\u5185\u6709\u8bb0\u5f55\u66f4\u7a33\u59a5",
    "\u5b9a\u4f4d\u95ee\u9898\uff1a\u51fa\u73b0\u5f02\u5e38\u65f6\u80fd\u8ffd\u6eaf\u6700\u8fd1\u6539\u52a8",
]

JUDGE_QUESTIONS = [
    "\u8fd9\u4e2a\u9879\u76ee\u662f\u5e72\u4ec0\u4e48\u7684",
    "\u5b83\u5c5e\u4e8e\u5468\u671f\u4fdd\u517b\u8fd8\u662f\u72b6\u6001\u68c0\u67e5",
    "\u8bf4\u660e\u4e66\u4e0a\u6709\u6ca1\u6709\u8fd9\u4e00\u9879",
    "\u6211\u7684\u5de5\u51b5\u9700\u8981\u7f29\u77ed\u8fd9\u4e2a\u5468\u671f\u5417",
    "\u8fd9\u4e2a\u9879\u76ee\u5f71\u54cd\u8d28\u4fdd\u5417",
    "\u4e0d\u505a\u4f1a\u6709\u4ec0\u4e48\u540e\u679c",
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


def parse_text(text):
    data = {}
    for chunk in str(text).replace(",", ";").split(";"):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        data[key.strip().lower()] = value.strip()
    return data


def tokens(text):
    if isinstance(text, str):
        return [t for t in text.replace("\u3001", " ").replace(",", " ").split() if t]
    return [str(x) for x in (text or [])]


def km_since(last_km, now_km):
    return max(0.0, now_km - last_km)


def track(last_km, now_km, months_since):
    """Return (km_delta, dimension verdict strings)."""
    delta = km_since(last_km, now_km)
    verdicts = []
    if delta <= 0:
        verdicts.append("\u91cc\u7a0b\uff1a\u672a\u8fbe\u5230\u9700\u8981\u6309\u91cc\u7a0b\u66f4\u6362\u7684\u91cf")
    else:
        verdicts.append("\u91cc\u7a0b\uff1a\u5df2\u884c\u9a76 %.0f \u516c\u91cc\uff0c\u6309\u8f66\u8f86\u8bf4\u660e\u4e66\u6838\u5bf9\u662f\u5426\u5230\u671f" % delta)
    if months_since <= 0:
        verdicts.append("\u65f6\u95f4\uff1a\u8ddd\u4e0a\u6b21\u4fdd\u517b\u65f6\u95f4\u5f88\u77ed\uff0c\u6309\u8bf4\u660e\u4e66\u6838\u5bf9")
    else:
        verdicts.append("\u65f6\u95f4\uff1a\u8ddd\u4e0a\u6b21\u4fdd\u517b\u7ea6 %.0f \u4e2a\u6708\uff0c\u6309\u8f66\u8f86\u8bf4\u660e\u4e66\u6838\u5bf9\u662f\u5426\u5230\u671f" % months_since)
    verdicts.append("\u6838\u5fc3\u53e3\u5f84\uff1a\u91cc\u7a0b\u4e0e\u65f6\u95f4\u53cc\u8f68\u5224\u5b9a\uff0c\u5148\u5230\u8005\u4e3a\u51c6")
    return delta, verdicts


def find_items(names):
    """Return matched ITEMS rows for the given names."""
    names = tokens(names)
    if not names:
        return list(ITEMS)
    hits = []
    for it in ITEMS:
        for n in names:
            if it[0] == n or n in it[0] or it[0] in n:
                hits.append(it)
                break
    return hits

def build_report(d):
    last_km = to_float(d.get("last_km"), 0.0)
    now_km = to_float(d.get("now_km"), 0.0)
    months = to_float(d.get("months_since"), 0.0)
    cond_key = str(d.get("condition", "normal")).lower()
    if cond_key not in CONDITIONS:
        cond_key = "normal"
    cond_name, cond_note = CONDITIONS[cond_key]

    delta, verdicts = track(last_km, now_km, months)
    rows = find_items(d.get("items"))

    out = ["# \u6c7d\u8f66\u4fdd\u517b\u53cc\u8f68\u5224\u5b9a\u4e0e\u9879\u76ee\u6838\u5bf9", ""]
    out.append("## \u91cc\u7a0b\u4e0e\u65f6\u95f4\u53cc\u8f68\u5224\u5b9a")
    out.append("")
    out.append("| \u7ef4\u5ea6 | \u6570\u636e |")
    out.append("|---|---|")
    out.append("| \u4e0a\u6b21\u4fdd\u517b\u91cc\u7a0b | %.0f \u516c\u91cc |" % last_km)
    out.append("| \u5f53\u524d\u91cc\u7a0b | %.0f \u516c\u91cc |" % now_km)
    out.append("| \u8ddd\u4e0a\u6b21\u91cc\u7a0b | %.0f \u516c\u91cc |" % delta)
    out.append("| \u8ddd\u4e0a\u6b21\u65f6\u95f4 | %.0f \u4e2a\u6708 |" % months)
    out.append("")
    for v in verdicts:
        out.append("- %s" % v)
    out.append("- \u5177\u4f53\u5468\u671f\u6570\u503c\u4ee5\u8f66\u8f86\u8bf4\u660e\u4e66\u548c\u5382\u5bb6\u8981\u6c42\u4e3a\u51c6\uff0c\u672c\u811a\u672c\u4e0d\u5185\u7f6e\u4efb\u4f55\u5468\u671f\u6570\u5b57")
    out.append("")
    out.append("## \u5de5\u51b5\u8c03\u6574")
    out.append("")
    out.append("- \u5f53\u524d\u5de5\u51b5\uff1a**%s**" % cond_name)
    out.append("- \u8c03\u6574\u65b9\u5411\uff1a%s" % cond_note)
    out.append("")
    out.append("\u5de5\u51b5\u660e\u663e\u504f\u79bb\u5e38\u89c4\u65f6\u5468\u671f\u53ef\u80fd\u8981\u7f29\u77ed\uff0c**\u4ee5\u5382\u5bb6\u8981\u6c42\u4e3a\u51c6\uff0c\u4e0d\u8981\u81ea\u5df1\u62cd\u6570\u5b57**\u3002")
    out.append("")
    out.append("## \u9879\u76ee\u4f5c\u7528\u4e0e\u5468\u671f\u53e3\u5f84")
    out.append("")
    if rows:
        out.append("| \u9879\u76ee | \u4e3b\u8981\u4f5c\u7528 | \u5468\u671f\u53e3\u5f84 | \u5b89\u5168\u76f8\u5173 |")
        out.append("|---|---|---|---|")
        for name, role, cycle, safety in rows:
            out.append("| %s | %s | %s | %s |" % (
                name, role, cycle, "\u662f" if safety else "\u5426"))
    else:
        out.append("- \u672a\u5339\u914d\u5230\u9879\u76ee\u540d\u79f0\uff0c\u663e\u793a\u5168\u90e8\u5e38\u89c1\u9879\u76ee")
        out.append("")
        out.append("| \u9879\u76ee | \u4e3b\u8981\u4f5c\u7528 | \u5468\u671f\u53e3\u5f84 | \u5b89\u5168\u76f8\u5173 |")
        out.append("|---|---|---|---|")
        for name, role, cycle, safety in ITEMS:
            out.append("| %s | %s | %s | %s |" % (
                name, role, cycle, "\u662f" if safety else "\u5426"))
    out.append("")
    out.append("\u5239\u8f66\u4e0e\u8f6e\u80ce\u5c5e\u4e8e\u5b89\u5168\u4ef6\uff0c**\u6309\u5b9e\u9645\u72b6\u6001\u68c0\u67e5\uff0c\u4e0d\u662f\u7b49\u5230\u5468\u671f\u5230\u4e86\u624d\u770b**\u3002")
    out.append("")
    out.append("## \u72b6\u6001\u76f8\u5173\u4e0e\u989d\u5916\u9879\u76ee")
    out.append("")
    out.append("| \u9879\u76ee | \u5224\u65ad |")
    out.append("|---|---|")
    for name, verdict in EXTRA_ITEMS:
        out.append("| %s | %s |" % (name, verdict))
    out.append("")
    out.append("\u5224\u65ad\u4f9d\u636e\u662f**\u8f66\u8f86\u8bf4\u660e\u4e66**\uff0c\u4e0d\u662f\u522b\u4eba\u7684\u7ecf\u9a8c\u3002")
    out.append("")
    out.append("## \u88ab\u8981\u6c42\u505a\u9879\u76ee\u65f6\u7684\u5224\u65ad\u6846\u67b6")
    out.append("")
    for q in JUDGE_QUESTIONS:
        out.append("- %s\uff1f" % q)
    out.append("")
    out.append("\u5148\u95ee\u6e05\u695a\u8fd9\u4e2a\u9879\u76ee\u7684\u4f5c\u7528\u4e0e\u4f9d\u636e\uff0c\u8bf4\u660e\u4e66\u4e0a\u6709\u8fd8\u662f\u6ca1\u6709\uff0c"
               "**\u6bd4\u76f4\u63a5\u8bf4\u4e0d\u9700\u8981\u6709\u8bf4\u670d\u529b**\u3002")
    out.append("")
    out.append("## \u4fdd\u517b\u8bb0\u5f55\u7684\u4f5c\u7528")
    out.append("")
    for r in RECORD_WHY:
        out.append("- %s" % r)
    out.append("")
    out.append("- \u6bcf\u6b21\u4fdd\u517b\u540e\u7d22\u53d6\u8bb0\u5f55\uff0c\u5e76\u786e\u8ba4\u7535\u5b50\u8bb0\u5f55\u771f\u7684\u8fdb\u4e86\u7cfb\u7edf")
    out.append("- \u8bb0\u5f55\u4fdd\u5b58\u597d\uff0c\u4e0d\u8981\u968f\u624b\u4e22")
    out.append("")
    out.append("## \u8fb9\u754c")
    out.append("")
    out.append("- \u672c\u811a\u672c\u53ea\u505a\u53cc\u8f68\u5224\u5b9a\u7684\u7ed3\u6784\u6027\u63d0\u793a\uff0c\u4e0d\u5185\u7f6e\u4efb\u4f55\u5468\u671f\u6570\u503c")
    out.append("- \u5177\u4f53\u4fdd\u517b\u5468\u671f\u3001\u9879\u76ee\u4e0e\u7528\u91cf\u4ee5\u8f66\u8f86\u8bf4\u660e\u4e66\u548c\u5382\u5bb6\u8981\u6c42\u4e3a\u51c6")
    out.append("- \u8f66\u8f86\u51fa\u73b0\u5f02\u5e38\u75c7\u72b6\u65f6\u5e94\u7531\u4e13\u4e1a\u7ef4\u4fee\u4eba\u5458\u5224\u65ad")
    return "\n".join(out) + "\n"


def selftest():
    cases = []
    cases.append(("km_delta", km_since(42000, 52000) == 10000.0))
    cases.append(("km_neg", km_since(50000, 42000) == 0.0))
    cases.append(("track_ok", len(track(42000, 52000, 8)[1]) == 3))
    cases.append(("track_key", "\u5148\u5230\u8005\u4e3a\u51c6" in track(42000, 52000, 8)[1][2]))
    cases.append(("float_str", to_float("8.5", 0.0) == 8.5))
    cases.append(("float_bad", to_float("abc", 1.0) == 1.0))
    cases.append(("tokens_cn", len(tokens("\u673a\u6cb9\u3001\u5239\u8f66")) == 2))
    cases.append(("find_one", len(find_items("\u673a\u6cb9")) == 1))
    cases.append(("find_none", len(find_items("")) == len(ITEMS)))
    cases.append(("find_safety", find_items("\u8f6e\u80ce")[0][3] is True))
    rep = build_report({"last_km": 42000, "now_km": 52000,
                        "months_since": 8, "condition": "shorttrip"})
    cases.append(("rep_dual", "\u53cc\u8f68\u5224\u5b9a" in rep))
    cases.append(("rep_delta", "10000 \u516c\u91cc" in rep))
    cases.append(("rep_cond", "\u957f\u671f\u77ed\u9014" in rep))
    cases.append(("rep_cond_note", "\u5145\u5206\u70ed\u900f" in rep))
    cases.append(("rep_safety", "\u5b89\u5168\u4ef6" in rep))
    cases.append(("rep_extra", "\u71c3\u6cb9\u6dfb\u52a0\u5242" in rep))
    cases.append(("rep_judge", "\u8bf4\u660e\u4e66\u4e0a\u6709\u8fd8\u662f\u6ca1\u6709" in rep))
    cases.append(("rep_record", "\u4e8c\u624b\u8f66\u8bc4\u4f30" in rep))
    cases.append(("rep_no_number", "\u4e0d\u5185\u7f6e\u4efb\u4f55\u5468\u671f\u6570\u5b57" in rep))
    rep2 = build_report({"condition": "bad", "items": "\u673a\u6cb9,\u8f6e\u80ce"})
    cases.append(("rep_cond_fallback", "\u5e38\u89c4\u5de5\u51b5" in rep2))
    cases.append(("rep_two_items", rep2.count("| \u673a\u6cb9 |") == 1
                  and rep2.count("| \u8f6e\u80ce |") == 1))
    bom = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_probe.json")
    with open(bom, "w", encoding="utf-8-sig") as f:
        f.write('{"last_km": 42000}')
    try:
        cases.append(("bom_ok", to_float(load_json(bom).get("last_km")) == 42000.0))
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


def main(argv=None):
    ap = argparse.ArgumentParser(description="vehicle service interval audit")
    ap.add_argument("--last-km", dest="last_km", default=None)
    ap.add_argument("--now-km", dest="now_km", default=None)
    ap.add_argument("--months-since", dest="months_since", default=None)
    ap.add_argument("--condition", default=None)
    ap.add_argument("--items", default=None)
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
    for key, val in (("last_km", a.last_km), ("now_km", a.now_km),
                     ("months_since", a.months_since), ("condition", a.condition),
                     ("items", a.items)):
        if val is not None:
            data[key] = val
    if not data:
        data = {"last_km": 40000, "now_km": 45000, "months_since": 6,
                "condition": "normal"}
    report = build_report(data)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "service_interval_result.md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
