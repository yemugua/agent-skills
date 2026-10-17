# -*- coding: utf-8 -*-
"""luggage_check: \u884c\u674e\u7269\u54c1\u6309\u7981\u8fd0\u3001\u9650\u91cf\u3001\u81ea\u8425\u4e09\u7c7b\u505a\u5224\u5b9a\u5f52\u7c7b\u3002

\u53ea\u505a\u903b\u8f91\u5f52\u7c7b\u4e0e\u6838\u5bf9\u63d0\u793a\uff0c\u4e0d\u7ed9\u51fa\u5177\u4f53\u80fd\u91cf\u4e0a\u9650\u4e0e\u989d\u5ea6\u6570\u5b57\u3002
"""
import argparse
import json
import os

# \u5173\u952e\u8bcd -> (\u7269\u54c1\u540d, \u7c7b\u522b, \u643a\u5e26\u65b9\u5f0f, \u5224\u5b9a\u8981\u70b9)
RULES = [
    ("\u5145\u7535\u5b9d", "\u9650\u91cf\u7269\u54c1", "\u5fc5\u987b\u968f\u8eab\uff0c\u4e0d\u53ef\u6258\u8fd0",
     "\u4fbf\u643a\u5f0f\u7535\u6c60\u987b\u968f\u8eab\u643a\u5e26\uff1b\u5224\u65ad\u4f9d\u636e\u662f\u6807\u79f0\u989d\u5b9a\u80fd\u91cf\uff0c\u4e0d\u662f\u5bb9\u91cf\u767e\u5206\u6bd4"),
    ("\u79fb\u52a8\u7535\u6e90", "\u9650\u91cf\u7269\u54c1", "\u5fc5\u987b\u968f\u8eab\uff0c\u4e0d\u53ef\u6258\u8fd0",
     "\u540c\u5145\u7535\u5b9d\uff0c\u6309\u989d\u5b9a\u80fd\u91cf\u5224\u65ad"),
    ("\u5907\u7528\u7535\u6c60", "\u9650\u91cf\u7269\u54c1", "\u5fc5\u987b\u968f\u8eab\uff0c\u4e0d\u53ef\u6258\u8fd0",
     "\u5907\u7528\u9502\u7535\u6c60\u540c\u6837\u4e0d\u53ef\u6258\u8fd0\uff0c\u7aef\u5b50\u9700\u6709\u4fdd\u62a4\u63aa\u65bd"),
    ("\u9502\u7535\u6c60", "\u9650\u91cf\u7269\u54c1", "\u5fc5\u987b\u968f\u8eab\uff0c\u4e0d\u53ef\u6258\u8fd0",
     "\u770b\u6807\u79f0\u989d\u5b9a\u80fd\u91cf\uff1b\u6613\u71c3\u6613\u7206\u7535\u6c60\u7981\u6b62\u6258\u8fd0"),
    ("\u6253\u706b\u673a", "\u9650\u91cf\u7269\u54c1", "\u6309\u627f\u8fd0\u65b9\u89c4\u5b9a\u968f\u8eab\u643a\u5e26", "\u968f\u8eab\u4e0e\u6258\u8fd0\u9650\u5236\u4e0d\u540c\uff0c\u987b\u6309\u89c4\u5219\u786e\u8ba4"),
    ("\u6253\u706b\u77f3", "\u9650\u91cf\u7269\u54c1", "\u6309\u627f\u8fd0\u65b9\u89c4\u5b9a\u968f\u8eab\u643a\u5e26", "\u968f\u8eab\u4e0e\u6258\u8fd0\u9650\u5236\u4e0d\u540c"),
    ("\u706b\u67f4", "\u9650\u91cf\u7269\u54c1", "\u6309\u627f\u8fd0\u65b9\u89c4\u5b9a\u968f\u8eab\u643a\u5e26", "\u901a\u5e38\u6709\u6570\u91cf\u9650\u5236"),
    ("\u55b7\u96fe", "\u9650\u91cf\u7269\u54c1", "\u6309\u627f\u8fd0\u65b9\u89c4\u5b9a\uff0c\u90e8\u5206\u79cd\u7c7b\u8981\u6c42\u968f\u8eab",
     "\u6709\u5bb9\u91cf\u9650\u5236\uff0c\u4e0d\u662f\u81ea\u7528\u5c31\u968f\u4fbf\u5e26"),
    ("\u9632\u6652\u55b7\u96fe", "\u9650\u91cf\u7269\u54c1", "\u6309\u627f\u8fd0\u65b9\u89c4\u5b9a\uff0c\u90e8\u5206\u79cd\u7c7b\u8981\u6c42\u968f\u8eab", "\u540c\u55b7\u96fe"),
    ("\u6307\u7532\u6cb9", "\u9650\u91cf\u7269\u54c1", "\u6309\u627f\u8fd0\u65b9\u89c4\u5b9a", "\u5c5e\u90e8\u5206\u9650\u91cf\u7684\u5316\u5b66\u54c1"),
    ("\u6c14\u4f53\u7f50", "\u9650\u91cf\u7269\u54c1", "\u6309\u627f\u8fd0\u65b9\u89c4\u5b9a", "\u901a\u5e38\u9650\u91cf"),
    ("\u9152\u7cbe", "\u9650\u91cf\u7269\u54c1", "\u6309\u627f\u8fd0\u65b9\u89c4\u5b9a", "\u5c5e\u6613\u71c3\u6db2\u4f53\uff0c\u987b\u6309\u89c4\u5219\u786e\u8ba4"),
    ("\u6c7d\u6cb9", "\u7981\u8fd0\u7269\u54c1", "\u4e0d\u80fd\u5e26", "\u6613\u71c3\u6db2\u4f53\uff0c\u7981\u6b62\u8fd0\u8f93"),
    ("\u5200\u5177", "\u7981\u8fd0\u7269\u54c1", "\u4e0d\u80fd\u5e26", "\u901a\u5e38\u7981\u8fd0\uff1b\u5de5\u5177\u7c7b\u53e6\u6709\u9650\u5236"),
    ("\u6298\u53e0\u5200", "\u7981\u8fd0\u7269\u54c1", "\u4e0d\u80fd\u5e26", "\u901a\u5e38\u7981\u8fd0"),
    ("\u6253\u706b\u673a\u6cb9", "\u7981\u8fd0\u7269\u54c1", "\u4e0d\u80fd\u5e26", "\u6613\u71c3\u6db2\u4f53\uff0c\u7981\u6b62\u8fd0\u8f93"),
    ("\u9152", "\u9650\u91cf\u7269\u54c1", "\u6309\u627f\u8fd0\u65b9\u89c4\u5b9a", "\u901a\u5e38\u6709\u5305\u88c5\u4e0e\u5bb9\u91cf\u8981\u6c42"),
    ("\u6d17\u53d1\u6c34", "\u9650\u91cf\u7269\u54c1", "\u968f\u8eab\u9700\u7b26\u5408\u5bb9\u91cf\u9650\u5236", "\u6db2\u4f53\u7c7b\u9700\u5bc6\u5c01\u9632\u6f0f"),
    ("\u996e\u6599", "\u9650\u91cf\u7269\u54c1", "\u968f\u8eab\u9700\u7b26\u5408\u5bb9\u91cf\u9650\u5236", "\u6db2\u4f53\u7c7b\u9700\u5bc6\u5c01\u9632\u6f0f"),
    ("\u836f\u54c1", "\u9650\u91cf\u7269\u54c1", "\u666e\u901a\u836f\u54c1\u901a\u5e38\u53ef\u5e26",
     "\u7279\u6b8a\u836f\u54c1\u4e0e\u9700\u51b7\u85cf\u836f\u54c1\u53e6\u884c\u786e\u8ba4"),
    ("\u79cd\u5b50", "\u7981\u8fd0\u7269\u54c1", "\u4e0d\u80fd\u5e26\u6216\u4e25\u683c\u53d7\u9650", "\u901a\u5e38\u53d7\u9650\u6216\u7981\u8fd0\uff0c\u987b\u6309\u89c4\u5219\u786e\u8ba4"),
    ("\u571f\u58e4", "\u7981\u8fd0\u7269\u54c1", "\u4e0d\u80fd\u5e26\u6216\u4e25\u683c\u53d7\u9650", "\u901a\u5e38\u53d7\u9650\u6216\u7981\u8fd0"),
    ("\u6d3b\u4f53\u5ba0\u7269", "\u7981\u8fd0\u7269\u54c1", "\u4e0d\u80fd\u5e26", "\u6d3b\u4f53\u52a8\u7269\u9650\u5236\u4e25\u683c"),
    ("\u6298\u53e0\u81ea\u884c\u8f66", "\u9650\u91cf\u7269\u54c1", "\u901a\u5e38\u9700\u6258\u8fd0", "\u5c5e\u9650\u91cf\u6216\u9700\u6258\u8fd0\uff0c\u6309\u89c4\u5219"),
    ("\u5de5\u5177", "\u9650\u91cf\u7269\u54c1", "\u6309\u627f\u8fd0\u65b9\u89c4\u5b9a", "\u5de5\u5177\u7c7b\u53e6\u6709\u9650\u5236"),
]

BATTERY_NOTE = [
    "\u5224\u65ad\u4f9d\u636e\u662f\u6807\u79f0\u989d\u5b9a\u80fd\u91cf\uff0c\u4e0d\u662f\u5bb9\u91cf\u767e\u5206\u6bd4\uff0c\u4e24\u8005\u4e0d\u80fd\u76f4\u63a5\u6362\u7b97",
    "\u4fbf\u643a\u5f0f\u7535\u6c60\u901a\u5e38\u8981\u6c42\u968f\u8eab\u643a\u5e26\uff0c\u4e0d\u5f97\u6258\u8fd0",
    "\u6613\u71c3\u6613\u7206\u7535\u6c60\u7981\u6b62\u6258\u8fd0",
    "\u7aef\u5b50\u9700\u6709\u4fdd\u62a4\u63aa\u65bd\uff0c\u907f\u514d\u77ed\u8def\u3001\u907f\u514d\u6324\u538b",
    "\u6570\u91cf\u4e0e\u80fd\u91cf\u4e0a\u9650\u4ee5\u627f\u8fd0\u65b9\u73b0\u884c\u89c4\u5b9a\u4e3a\u51c6",
]

BILLING_NOTE = [
    "\u5148\u51cf\u91cd\uff0c\u628a\u4e0d\u6025\u7528\u7684\u7269\u54c1\u8f6c\u5230\u968f\u8eab\u6216\u62ff\u51fa\u6765",
    "\u6ce8\u610f\u591a\u4ef6\u884c\u674e\u53ef\u80fd\u5408\u5e76\u8ba1\u7b97\u603b\u91cd",
    "\u5206\u4ef6\u65b9\u5f0f\u662f\u5426\u66f4\u7701\u8981\u770b\u627f\u8fd0\u65b9\u89c4\u5219",
    "\u8d39\u7528\u6807\u51c6\u4ee5\u627f\u8fd0\u65b9\u73b0\u884c\u89c4\u5b9a\u4e3a\u51c6",
]

CLAIM_STEPS = [
    "\u53d1\u73b0\u95ee\u9898\u7acb\u5373\u5728\u670d\u52a1\u5904\u529e\u7406\u767b\u8bb0",
    "\u4fdd\u7559\u597d\u884c\u674e\u724c\u4e0e\u76f8\u5173\u51ed\u8bc1",
    "\u6309\u627f\u8fd0\u65b9\u8981\u6c42\u63d0\u4ea4\u7533\u62a5\u6750\u6599",
    "\u5fc5\u8981\u65f6\u63d0\u4f9b\u7269\u54c1\u4ef7\u503c\u8bc1\u660e",
    "\u8ddf\u8fdb\u5904\u7406\u7ed3\u679c",
]

CLAIM_DOCS = ["\u884c\u674e\u724c", "\u8d2d\u4e70\u51ed\u8bc1", "\u7269\u54c1\u7684\u7535\u5b50\u7167\u7247", "\u5f02\u5e38\u767b\u8bb0\u5355"]

CARRY_LIMIT = "\u989d\u5ea6\u4e0e\u8ba1\u8d39\u89c4\u5219\u4ee5\u627f\u8fd0\u65b9\u73b0\u884c\u89c4\u5b9a\u4e3a\u51c6"


def load_json(path):
    """Read JSON, tolerating the UTF-8 BOM written by PowerShell."""
    raw = open(path, "r", encoding="utf-8-sig").read().strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise ValueError("json parse failed: %s" % exc)


def tokens(text):
    if isinstance(text, str):
        return [t for t in text.replace("\u3001", " ").replace(",", " ").split() if t]
    return [str(x) for x in (text or [])]


def classify(name):
    """Return the first matching rule for an item name, or a manual-confirm row."""
    n = str(name).strip()
    for key, cat, carry, tip in RULES:
        if key in n or n in key:
            return dict(name=key, category=cat, carry=carry, tip=tip, matched=n)
    return dict(name=None, category="\u9700\u4eba\u5de5\u786e\u8ba4",
                carry="\u6309\u627f\u8fd0\u65b9\u73b0\u884c\u89c4\u5b9a\u786e\u8ba4",
                tip="\u672a\u5339\u914d\u5230\u5df2\u77e5\u89c4\u5219\uff0c\u8bf7\u4ee5\u627f\u8fd0\u65b9\u516c\u5e03\u4e3a\u51c6", matched=n)


def classify_all(items):
    return [classify(it) for it in tokens(items)]


def battery_report(wh, powerbank):
    out = []
    if wh is None:
        return out
    out.append("## \u9502\u7535\u6c60\u4e13\u9879\u63d0\u793a")
    out.append("")
    out.append("- \u7c7b\u578b\uff1a%s" % ("\u5145\u7535\u5b9d\u6216\u79fb\u52a8\u7535\u6e90" if powerbank else "\u9502\u7535\u6c60"))
    out.append("- \u6807\u79f0\u989d\u5b9a\u80fd\u91cf\uff1a**%.0f \u74e6\u65f6**" % wh)
    out.append("- \u643a\u5e26\u65b9\u5f0f\uff1a**\u5fc5\u987b\u968f\u8eab\uff0c\u4e0d\u53ef\u6258\u8fd0**")
    out.append("")
    out.append("\u6838\u5bf9\u6b65\u9aa4\uff1a")
    out.append("")
    out.append("1. \u786e\u8ba4\u662f\u7535\u6c60\u8fd8\u662f\u5145\u7535\u5b9d\uff0c\u6807\u79f0\u989d\u5b9a\u80fd\u91cf\u662f\u591a\u5c11")
    out.append("2. \u786e\u8ba4\u5fc5\u987b\u968f\u8eab\uff0c\u4e0d\u5f97\u653e\u8fdb\u6258\u8fd0\u884c\u674e")
    out.append("3. \u786e\u8ba4\u7aef\u5b50\u6709\u4fdd\u62a4\u63aa\u65bd\uff0c\u4e0d\u4f1a\u77ed\u8def")
    out.append("4. \u786e\u8ba4\u6570\u91cf\u4e0e\u80fd\u91cf\u672a\u8d85\u51fa\u627f\u8fd0\u65b9\u89c4\u5b9a")
    out.append("5. \u6253\u5305\u65f6\u907f\u514d\u6324\u538b\u4e0e\u78b0\u649e")
    out.append("")
    for n in BATTERY_NOTE:
        out.append("- %s" % n)
    out.append("")
    return out


def build_report(items, battery_wh, powerbank):
    rows = classify_all(items)
    out = ["# \u884c\u674e\u7269\u54c1\u6838\u67e5\u7ed3\u679c", ""]
    out.append("## \u4e09\u7c7b\u5224\u5b9a\u903b\u8f91")
    out.append("")
    out.append("| \u7c7b\u522b | \u5224\u5b9a\u903b\u8f91 | \u643a\u5e26\u65b9\u5f0f |")
    out.append("|---|---|---|")
    out.append("| \u7981\u8fd0\u7269\u54c1 | \u672c\u8eab\u88ab\u7981\u6b62\u8fd0\u8f93\uff0c\u4e0d\u56e0\u6570\u91cf\u6216\u5305\u88c5\u6539\u53d8 | \u90fd\u4e0d\u80fd\u5e26 |")
    out.append("| \u9650\u91cf\u7269\u54c1 | \u5141\u8bb8\u643a\u5e26\u4f46\u6709\u6570\u91cf\u3001\u5bb9\u91cf\u3001\u80fd\u91cf\u7b49\u9650\u5236 | \u968f\u8eab\u4e0e\u6258\u8fd0\u5404\u6709\u9650\u5236 |")
    out.append("| \u81ea\u8425\u7269\u54c1 | \u627f\u8fd0\u65b9\u81ea\u8425\u7684\u7269\u54c1 | \u6309\u627f\u8fd0\u65b9\u89c4\u5219 |")
    out.append("")
    out.append("\u540c\u4e00\u7269\u54c1\u5728\u4e0d\u540c\u627f\u8fd0\u65b9\u3001\u4e0d\u540c\u8fd0\u8f93\u65b9\u5f0f\u89c4\u5219\u53ef\u80fd\u4e0d\u540c\uff0c"
               "\u4e00\u8d9f\u884c\u7a0b\u6d89\u53ca\u591a\u79cd\u65b9\u5f0f\u65f6\u6bcf\u6bb5\u90fd\u8981\u5355\u72ec\u6838\u5bf9\u3002")
    out.append("")
    out.append("## \u9010\u9879\u5224\u5b9a")
    out.append("")
    if rows:
        out.append("| \u7269\u54c1 | \u7c7b\u522b | \u643a\u5e26\u65b9\u5f0f | \u5224\u5b9a\u8981\u70b9 |")
        out.append("|---|---|---|---|")
        for r in rows:
            label = r["matched"] if r["name"] is None else r["name"]
            out.append("| %s | %s | %s | %s |" % (
                label, r["category"], r["carry"], r["tip"]))
    else:
        out.append("- \u672a\u63d0\u4f9b\u7269\u54c1\u6e05\u5355")
    out.append("")
    banned = [r for r in rows if r["category"] == "\u7981\u8fd0\u7269\u54c1"]
    if banned:
        out.append("**\u4e0b\u5217\u7269\u54c1\u5c5e\u4e8e\u7981\u8fd0\uff0c\u4e0d\u80fd\u5e26\uff1a**")
        out.append("")
        for r in banned:
            out.append("- %s" % r["matched"])
        out.append("")
    out.extend(battery_report(battery_wh, powerbank))
    out.append("## \u989d\u5ea6\u4e0e\u8d85\u91cd")
    out.append("")
    for n in BILLING_NOTE:
        out.append("- %s" % n)
    out.append("- %s" % CARRY_LIMIT)
    out.append("")
    out.append("## \u4e22\u5931\u4e0e\u7834\u635f\u7684\u7406\u8d54")
    out.append("")
    for i, s in enumerate(CLAIM_STEPS, 1):
        out.append("%d. %s" % (i, s))
    out.append("")
    out.append("\u5fc5\u987b\u4fdd\u7559\u7684\u51ed\u8bc1\uff1a%s" % "\u3001".join(CLAIM_DOCS))
    out.append("")
    out.append("- \u968f\u8eab\u7269\u54c1\u901a\u5e38\u4e0d\u5728\u6258\u8fd0\u884c\u674e\u7684\u7533\u62a5\u8303\u56f4\u5185\uff0c\u8d35\u91cd\u7269\u54c1\u4e0e\u8bc1\u4ef6\u5c3d\u91cf\u968f\u8eab\u643a\u5e26")
    out.append("")
    out.append("## \u8fb9\u754c")
    out.append("")
    out.append("- \u672c\u811a\u672c\u53ea\u505a\u903b\u8f91\u5f52\u7c7b\u4e0e\u6838\u5bf9\u63d0\u793a\uff0c\u4e0d\u7ed9\u51fa\u5177\u4f53\u80fd\u91cf\u4e0a\u9650\u4e0e\u989d\u5ea6\u6570\u5b57")
    out.append("- \u6700\u7ec8\u653e\u884c\u5224\u5b9a\u7531\u5b89\u68c0\u505a\u51fa")
    out.append("- \u8d54\u4ed8\u8303\u56f4\u4e0e\u6807\u51c6\u4ee5\u627f\u8fd0\u65b9\u73b0\u884c\u89c4\u5b9a\u4e3a\u51c6")
    return "\n".join(out) + "\n"


def selftest():
    cases = []
    cases.append(("powerbank", classify("\u5145\u7535\u5b9d")["category"] == "\u9650\u91cf\u7269\u54c1"))
    cases.append(("powerbank_carry", "\u4e0d\u53ef\u6258\u8fd0" in classify("\u5145\u7535\u5b9d")["carry"]))
    cases.append(("lighter", classify("\u6253\u706b\u673a")["category"] == "\u9650\u91cf\u7269\u54c1"))
    cases.append(("knife", classify("\u6298\u53e0\u5200")["category"] == "\u7981\u8fd0\u7269\u54c1"))
    cases.append(("gasoline", classify("\u6c7d\u6cb9")["category"] == "\u7981\u8fd0\u7269\u54c1"))
    cases.append(("spray", classify("\u9632\u6652\u55b7\u96fe")["category"] == "\u9650\u91cf\u7269\u54c1"))
    cases.append(("seed", classify("\u79cd\u5b50")["category"] == "\u7981\u8fd0\u7269\u54c1"))
    cases.append(("pet", classify("\u6d3b\u4f53\u5ba0\u7269")["category"] == "\u7981\u8fd0\u7269\u54c1"))
    cases.append(("bike", classify("\u6298\u53e0\u81ea\u884c\u8f66")["carry"].startswith("\u901a\u5e38\u9700\u6258\u8fd0")))
    cases.append(("unknown", classify("\u67d0\u4e2a\u6ca1\u89c1\u8fc7\u7684\u7269\u54c1")["category"] == "\u9700\u4eba\u5de5\u786e\u8ba4"))
    rows = classify_all("\u5145\u7535\u5b9d,\u6298\u53e0\u5200,\u5145\u7535\u5b9d")
    cases.append(("list_len", len(rows) == 3))
    cases.append(("list_dup", rows[0]["name"] == rows[2]["name"]))
    cases.append(("tokens_cn", len(tokens("\u6253\u706b\u673a\u3001\u55b7\u96fe")) == 2))
    rep = build_report("\u5145\u7535\u5b9d,\u6298\u53e0\u5200,\u6c7d\u6cb9", 20000, True)
    cases.append(("rep_banned", "\u5c5e\u4e8e\u7981\u8fd0\uff0c\u4e0d\u80fd\u5e26" in rep))
    cases.append(("rep_battery", "\u9502\u7535\u6c60\u4e13\u9879\u63d0\u793a" in rep))
    cases.append(("rep_wh", "20000 \u74e6\u65f6" in rep))
    cases.append(("rep_steps", "\u786e\u8ba4\u5fc5\u987b\u968f\u8eab" in rep))
    cases.append(("rep_wh_not_capacity", "\u4e0d\u662f\u5bb9\u91cf\u767e\u5206\u6bd4" in rep))
    cases.append(("rep_claim", "\u884c\u674e\u724c" in rep))
    cases.append(("rep_carry_note", "\u968f\u8eab\u643a\u5e26" in rep))
    rep2 = build_report([], None, False)
    cases.append(("rep_empty", "\u672a\u63d0\u4f9b\u7269\u54c1\u6e05\u5355" in rep2))
    cases.append(("rep_no_battery", "\u9502\u7535\u6c60\u4e13\u9879\u63d0\u793a" not in rep2))
    rep3 = build_report("\u6253\u706b\u673a", None, False)
    cases.append(("rep_no_banned", "\u5c5e\u4e8e\u7981\u8fd0\uff0c\u4e0d\u80fd\u5e26" not in rep3))
    bom = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_probe.json")
    with open(bom, "w", encoding="utf-8-sig") as f:
        f.write('{"items": "\u6253\u706b\u673a", "battery": 10000}')
    try:
        data = load_json(bom)
        cases.append(("bom_ok", data.get("items") == "\u6253\u706b\u673a"))
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
    ap = argparse.ArgumentParser(description="luggage items audit")
    ap.add_argument("--items", default=None)
    ap.add_argument("--battery", default=None)
    ap.add_argument("--powerbank", default=None)
    ap.add_argument("--file", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--format", default="md")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    items, wh, pb = a.items, a.battery, a.powerbank
    if a.file:
        try:
            data = load_json(a.file)
        except Exception as exc:
            print(str(exc))
            return 2
        items = data.get("items", items)
        wh = data.get("battery", wh)
        pb = data.get("powerbank", pb)
    battery_wh = None
    if wh is not None:
        try:
            battery_wh = float(wh)
        except (TypeError, ValueError):
            battery_wh = None
    is_pb = str(pb).lower() in ("y", "yes", "true", "1") if pb else False
    report = build_report(items or [], battery_wh, is_pb)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "luggage_result.md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
