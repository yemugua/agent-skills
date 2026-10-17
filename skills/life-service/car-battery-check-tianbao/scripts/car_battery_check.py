# -*- coding: utf-8 -*-
"""car_battery_check: \u6c7d\u8f66\u7535\u74f6\u4e8f\u7535\u539f\u56e0\u6392\u5e8f\u4e0e\u642d\u7535\u6b65\u9aa4\u6838\u5bf9\u3002

\u53ea\u505a\u539f\u56e0\u6392\u5e8f\u4e0e\u6b65\u9aa4\u6838\u5bf9\uff0c\u4e0d\u7ed9\u51fa\u5bb9\u91cf\u4e0e\u7535\u538b\u6570\u503c\u6807\u51c6\u3002
"""
import argparse
import json
import os

# (\u539f\u56e0, \u5173\u952e\u8bcd, \u5178\u578b\u8868\u73b0, \u68c0\u67e5\u65b9\u5411)
CAUSES = [
    ("\u957f\u671f\u505c\u653e\u672a\u65ad\u7535", ("\u957f\u671f\u505c\u653e", "\u505c\u653e", "\u653e\u4e86\u4e00\u5468", "\u51e0\u5929\u6ca1\u5f00", "\u6ca1\u5f00"),
     "\u505c\u653e\u51e0\u5929\u5c31\u6253\u4e0d\u7740", "\u505c\u653e\u65f6\u957f\u3001\u662f\u5426\u6709\u957f\u671f\u4e0d\u65ad\u7535\u7684\u8bbe\u5907"),
    ("\u9891\u7e41\u77ed\u9014\u884c\u9a76", ("\u77ed\u9014", "\u6bcf\u5929\u5f00\u4e00\u70b9", "\u4e0a\u4e0b\u73ed", "\u8dd1\u5f97\u5c11"),
     "\u6bcf\u5929\u5f00\u4e00\u70b9\uff0c\u7535\u91cf\u8865\u4e0d\u6ee1", "\u884c\u9a76\u65f6\u957f\u4e0e\u8ddd\u79bb"),
    ("\u7a7a\u8c03\u3001\u706f\u5149\u672a\u5173", ("\u5fd8\u5173", "\u7a7a\u8c03\u6ca1\u5173", "\u706f\u5149\u6ca1\u5173", "\u5927\u706f"),
     "\u7184\u706b\u540e\u624d\u53d1\u73b0", "\u7528\u8f66\u4e60\u60ef"),
    ("\u7535\u74f6\u8001\u5316", ("\u7528\u4e86\u51e0\u5e74", "\u8001\u5316", "\u597d\u51e0\u5e74", "\u7535\u6c60\u4e0d\u884c"),
     "\u7528\u51e0\u5e74\u540e\u7a81\u7136\u66f4\u5bb9\u6613\u4e8f", "\u4f7f\u7528\u5e74\u9650\u4e0e\u8f66\u51b5"),
    ("\u52a0\u88c5\u8bbe\u5907\u8017\u7535", ("\u52a0\u88c5", "\u8bb0\u5f55\u4eea", "\u6539\u88c5", "\u97f3\u54cd"),
     "\u52a0\u88c5\u540e\u5f00\u59cb\u51fa\u73b0\u4e8f\u7535", "\u540e\u88c5\u8bbe\u5907\u4e0e\u52a0\u88c5\u60c5\u51b5"),
    ("\u7535\u8def\u6216\u7528\u7535\u5f02\u5e38", ("\u9759\u7f6e", "\u505c\u4e00\u591c", "\u6301\u7eed\u8017\u7535", "\u65e0\u6545\u4e8f\u7535"),
     "\u7184\u706b\u540e\u4ecd\u6301\u7eed\u8017\u7535", "\u9700\u4e13\u4e1a\u68c0\u67e5"),
    ("\u4f4e\u6e29\u5f71\u54cd", ("\u51ac\u5929", "\u4f4e\u6e29", "\u5bd2\u51b7", "\u96ea"),
     "\u51ac\u5b63\u660e\u663e\u66f4\u5bb9\u6613\u6ca1\u7535", "\u770b\u4f4e\u6e29\u4e00\u8282"),
]

JUMP_STEPS = [
    "\u642d\u7535\u8f66\u7535\u74f6\u6b63\u6781",
    "\u4e8f\u7535\u8f66\u7535\u74f6\u6b63\u6781",
    "\u4e8f\u7535\u8f66\u7535\u74f6\u8d1f\u6781",
    "\u642d\u7535\u8f66\u7535\u74f6\u8d1f\u6781\uff08\u6700\u540e\u63a5\u8d1f\u6781\uff09",
]

JUMP_TABOO = [
    ("\u6b63\u8d1f\u6781\u4e0d\u53ef\u53cd\u63a5", "\u53cd\u63a5\u53ef\u80fd\u635f\u574f\u8f66\u8f7d\u7535\u5b50\u8bbe\u5907"),
    ("\u4e0d\u8981\u5728\u4e8f\u7535\u8f66\u53d1\u52a8\u673a\u8fd0\u8f6c\u65f6\u642d", "\u7535\u538b\u4e0d\u7a33\u53ef\u80fd\u635f\u574f\u53cc\u65b9\u8f66\u8f86"),
    ("\u4e0d\u8981\u7528\u7ec6\u5bfc\u7ebf", "\u7535\u6d41\u5927\u6613\u53d1\u70ed\u7194\u65ad\uff0c\u7ebf\u5f84\u8981\u591f"),
    ("\u4e0d\u8981\u540c\u65f6\u89e6\u78b0\u4e24\u4e2a\u7aef\u5b50\u4e0e\u91d1\u5c5e", "\u907f\u514d\u77ed\u8def\u4e0e\u7535\u5f27"),
]

RETRY_ORDER = [
    "\u786e\u8ba4\u63a5\u7ebf\u987a\u5e8f\u6b63\u786e\u3001\u6b63\u8d1f\u6781\u6ca1\u6709\u63a5\u53cd",
    "\u786e\u8ba4\u642d\u7535\u8f66\u7535\u91cf\u5145\u8db3\u3001\u5df2\u70b9\u706b\u4fdd\u6301\u6020\u901f",
    "\u786e\u8ba4\u642d\u7535\u7ebf\u7ebf\u5f84\u8db3\u591f\u3001\u8fde\u63a5\u7262\u56fa\u65e0\u677e\u52a8",
    "\u786e\u8ba4\u6863\u4f4d\u6b63\u786e\uff1a\u81ea\u52a8\u6321\u5728 P \u6321\uff0c\u624b\u52a8\u6321\u6302\u7a7a\u6321",
    "\u786e\u8ba4\u624b\u5239\u62c9\u8d77\u3001\u65b9\u5411\u76d8\u89e3\u9501\uff0c\u94a5\u5319\u8f6c\u5230\u542f\u52a8\u4f4d\u7f6e",
    "\u95f4\u9694\u5341\u51e0\u79d2\u540e\u91cd\u65b0\u5c1d\u8bd5\uff0c\u4e0d\u8981\u8fde\u7eed\u957f\u65f6\u95f4\u53cd\u590d\u6253",
]

REPLACE_CASES = [
    ("\u642d\u7535\u540e\u5f88\u5feb\u518d\u6b21\u4e8f\u7535", "\u53ef\u80fd\u662f\u5bb9\u91cf\u8870\u51cf\u6216\u5b58\u5728\u6301\u7eed\u8017\u7535"),
    ("\u4f7f\u7528\u5e74\u9650\u5df2\u5230", "\u6309\u7535\u74f6\u6807\u8bc6\u4e0e\u5382\u5bb6\u8bf4\u660e\u4e3a\u51c6"),
    ("\u7535\u74f6\u9f13\u5305", "\u7acb\u5373\u505c\u7528\uff0c\u4e0d\u8981\u7ee7\u7eed\u4f7f\u7528\u6216\u642d\u7535"),
    ("\u7535\u74f6\u6f0f\u6db2", "\u7acb\u5373\u505c\u7528\uff0c\u62a5\u4fee"),
    ("\u7aef\u5b50\u8150\u8680\u4e25\u91cd", "\u9700\u8981\u68c0\u67e5\uff0c\u5fc5\u8981\u65f6\u66f4\u6362"),
    ("\u4f4e\u6e29\u4e0b\u9891\u7e41\u65e0\u6cd5\u542f\u52a8", "\u5bb9\u91cf\u53ef\u80fd\u5df2\u660e\u663e\u4e0b\u964d"),
    ("\u8f66\u8f86\u7535\u6c14\u7cfb\u7edf\u62a5\u8b66", "\u5e94\u7531\u4e13\u4e1a\u4eba\u5458\u5224\u65ad"),
]

WINTER_NOTE = [
    "\u7535\u74f6\u5bb9\u91cf\u5728\u4f4e\u6e29\u4e0b\u4e0b\u964d\uff0c\u53ef\u7528\u5bb9\u91cf\u51cf\u5c11",
    "\u4f4e\u6e29\u4e0b\u673a\u6cb9\u9ecf\u5ea6\u9ad8\uff0c\u53d1\u52a8\u673a\u963b\u529b\u53d8\u5927\uff0c\u542f\u52a8\u7535\u6d41\u9700\u6c42\u66f4\u5927",
    "\u51ac\u5b63\u4f7f\u7528\u9891\u7387\u53ef\u80fd\u4e0b\u964d\uff0c\u884c\u9a76\u65f6\u95f4\u4e0d\u591f\uff0c\u5145\u7535\u4e0d\u8db3",
    "\u96e8\u96ea\u5929\u6c14\u9664\u971c\u4e0e\u540e\u6321\u52a0\u70ed\u7b49\u589e\u52a0\u8017\u7535",
]

KITTING = [
    "\u642d\u7535\u7ebf\uff08\u7ebf\u5f84\u8db3\u591f\uff09",
    "\u4e09\u89d2\u8b66\u793a\u724c",
    "\u5e94\u6025\u542f\u52a8\u7535\u6e90",
    "\u53cd\u5149\u80cc\u5fc3",
    "\u624b\u673a\u4e0e\u5145\u7535\u7ebf",
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


def tokens(text):
    if isinstance(text, str):
        return [t for t in text.replace("\u3001", " ").replace(",", " ").split() if t]
    return [str(x) for x in (text or [])]


def match_causes(symptoms):
    joined = " ".join(tokens(symptoms)).lower()
    hits = []
    for i, (name, keys, symptom, check) in enumerate(CAUSES, 1):
        for k in keys:
            if k in joined:
                hits.append((i, name, symptom, check))
                break
    hits.sort(key=lambda x: x[0])
    return hits


def build_report(symptoms):
    hits = match_causes(symptoms)
    out = ["# \u6c7d\u8f66\u7535\u74f6\u4e8f\u7535\u6392\u67e5\u4e0e\u642d\u7535\u6838\u5bf9", ""]
    out.append("## \u4e8f\u7535\u539f\u56e0\u6392\u5e8f\uff08\u6309\u6982\u7387\uff09")
    out.append("")
    if hits:
        out.append("| \u987a\u5e8f | \u53ef\u80fd\u539f\u56e0 | \u5178\u578b\u8868\u73b0 | \u68c0\u67e5\u65b9\u5411 |")
        out.append("|---|---|---|---|")
        for i, name, symptom, check in hits:
            out.append("| %d | %s | %s | %s |" % (i, name, symptom, check))
    else:
        out.append("- \u672a\u8bc6\u522b\u5230\u5df2\u77e5\u73b0\u8c61\uff0c\u53ef\u6309\u4e0b\u65b9\u987a\u5e8f\u9010\u6761\u6392\u67e5")
        out.append("")
        out.append("| \u987a\u5e8f | \u53ef\u80fd\u539f\u56e0 | \u5178\u578b\u8868\u73b0 | \u68c0\u67e5\u65b9\u5411 |")
        out.append("|---|---|---|---|")
        for i, name, _keys, symptom, check in [(i, c[0], c[1], c[2], c[3])
                                               for i, c in enumerate(CAUSES, 1)]:
            out.append("| %d | %s | %s | %s |" % (i, name, symptom, check))
    out.append("")
    out.append("\u73b0\u4ee3\u8f66\u8f86\u7184\u706b\u540e\u4ecd\u6709\u5c11\u91cf\u5e38\u7535\u8bbe\u5907\u5728\u5de5\u4f5c\uff0c\u957f\u671f\u505c\u653e\u4f1a\u6162\u6162\u6d88\u8017\u7535\u91cf\u3002")
    out.append("\u7184\u706b\u9759\u7f6e\u4e00\u591c\u540e\u660e\u663e\u4e8f\u7535\uff0c\u53ef\u80fd\u4e0d\u662f\u7535\u74f6\u672c\u8eab\u95ee\u9898\uff0c\u800c\u662f\u6709\u8bbe\u5907\u6301\u7eed\u8017\u7535\uff0c"
               "\u8fd9\u7c7b\u60c5\u51b5\u9700\u4e13\u4e1a\u68c0\u67e5\u3002")
    out.append("")
    out.append("## \u642d\u7535\u6b63\u786e\u987a\u5e8f")
    out.append("")
    for i, step in enumerate(JUMP_STEPS, 1):
        out.append("%d. %s" % (i, step))
    out.append("")
    out.append("- \u6700\u540e\u63a5\u8d1f\u6781\uff0c\u5b8c\u6210\u642d\u7535\u540e\u518d\u62c6\u8d1f\u6781\uff0c\u8ba9\u8f66\u8f86\u6709\u7a33\u5b9a\u7535\u5e73\u53c2\u8003")
    out.append("- **\u62c6\u7684\u987a\u5e8f\u4e0e\u63a5\u7684\u76f8\u53cd**\uff1a\u5148\u62c6\u8d1f\u6781\uff0c\u518d\u62c6\u6b63\u6781")
    out.append("- \u642d\u7535\u8f66**\u5148\u70b9\u706b\u5e76\u4fdd\u6301\u6020\u901f**\uff0c\u518d\u8ba9\u4e8f\u7535\u8f66\u5c1d\u8bd5\u542f\u52a8")
    out.append("- \u542f\u52a8\u540e\u4e0d\u8981\u7acb\u523b\u7184\u706b\uff0c\u8ba9\u5145\u7535\u7cfb\u7edf\u6709\u65f6\u95f4\u5145\u7535")
    out.append("")
    out.append("## \u642d\u7535\u7981\u5fcc")
    out.append("")
    out.append("| \u7981\u5fcc | \u539f\u56e0 |")
    out.append("|---|---|")
    for taboo, why in JUMP_TABOO:
        out.append("| %s | %s |" % (taboo, why))
    out.append("")
    out.append("- \u642d\u7535\u7ebf\u8981\u9009\u6b63\u89c4\u4ea7\u54c1\u3001\u7ebf\u5f84\u8db3\u591f\uff0c**\u4e0d\u8981\u7528\u7ec6\u94c1\u4e1d\u6216\u666e\u901a\u7535\u7ebf\u4ee3\u66ff**")
    out.append("- \u9009\u62e9\u901a\u98ce\u3001\u5e72\u71e5\u3001\u5e73\u6574\u7684\u573a\u5730\uff0c\u624b\u4e0d\u8981\u540c\u65f6\u63a5\u89e6\u4e24\u4e2a\u7aef\u5b50")
    out.append("")
    out.append("## \u642d\u7535\u540e\u4ecd\u65e0\u6cd5\u542f\u52a8\u7684\u6392\u67e5")
    out.append("")
    for i, step in enumerate(RETRY_ORDER, 1):
        out.append("%d. %s" % (i, step))
    out.append("")
    out.append("\u8fde\u7eed\u957f\u65f6\u95f4\u53cd\u590d\u6253\u706b\u4f1a\u6d88\u8017\u7535\u91cf\u8fd8\u53ef\u80fd\u635f\u4f24\u7535\u74f6\u3002")
    out.append("")
    out.append("## \u5fc5\u987b\u6362\u7535\u6c60\u7684\u5224\u5b9a")
    out.append("")
    out.append("| \u60c5\u51b5 | \u5224\u5b9a |")
    out.append("|---|---|")
    for case, verdict in REPLACE_CASES:
        out.append("| %s | %s |" % (case, verdict))
    out.append("")
    out.append("\u53cd\u590d\u642d\u7535\u4e0d\u662f\u957f\u4e45\u4e4b\u8ba1\u3002\u7ecf\u5e38\u9700\u8981\u642d\u7535\uff0c\u8bf4\u660e\u7535\u74f6\u6216\u7535\u8def\u6709\u95ee\u9898\u3002")
    out.append("")
    out.append("## \u51ac\u5b63\u4f4e\u6e29\u5f71\u54cd")
    out.append("")
    for n in WINTER_NOTE:
        out.append("- %s" % n)
    out.append("")
    out.append("\u4f4e\u6e29\u4e0d\u589e\u52a0\u7535\u91cf\u6d88\u8017\u901f\u5ea6\uff0c\u4f46\u4f1a\u964d\u4f4e\u7535\u74f6\u53ef\u7528\u5bb9\u91cf\uff0c\u4e24\u8005\u53e0\u52a0\u66f4\u5bb9\u6613\u542f\u52a8\u56f0\u96be\u3002")
    out.append("")
    out.append("## \u5e94\u6025\u51c6\u5907")
    out.append("")
    for k in KITTING:
        out.append("- [ ] %s" % k)
    out.append("")
    out.append("\u4f7f\u7528\u5e94\u6025\u542f\u52a8\u7535\u6e90\u65f6\u6309\u8bbe\u5907\u8bf4\u660e\u4e66\u64cd\u4f5c\uff0c**\u6b63\u8d1f\u6781\u8fde\u63a5\u540c\u6837\u4e0d\u53ef\u53cd\u63a5**\u3002")
    out.append("")
    out.append("## \u8fb9\u754c")
    out.append("")
    out.append("- \u672c\u811a\u672c\u53ea\u505a\u539f\u56e0\u6392\u5e8f\u4e0e\u6b65\u9aa4\u6838\u5bf9\uff0c\u4e0d\u7ed9\u51fa\u5bb9\u91cf\u4e0e\u7535\u538b\u6570\u503c\u6807\u51c6")
    out.append("- \u5bb9\u91cf\u3001\u7535\u538b\u4e0e\u66f4\u6362\u6807\u51c6\u4ee5\u8f66\u8f86\u8bf4\u660e\u4e66\u548c\u7535\u74f6\u6807\u8bc6\u4e3a\u51c6")
    out.append("- \u7535\u8def\u6216\u7528\u7535\u8bbe\u5907\u7684\u6df1\u5c42\u6545\u969c\u5e94\u7531\u4e13\u4e1a\u4eba\u5458\u68c0\u67e5")
    return "\n".join(out) + "\n"


def selftest():
    cases = []
    cases.append(("park", match_causes(["\u957f\u671f\u505c\u653e"])[0][1] == "\u957f\u671f\u505c\u653e\u672a\u65ad\u7535"))
    cases.append(("short", match_causes(["\u6bcf\u5929\u5f00\u4e00\u70b9"])[0][1] == "\u9891\u7e41\u77ed\u9014\u884c\u9a76"))
    cases.append(("forget", match_causes(["\u7a7a\u8c03\u6ca1\u5173"])[0][1] == "\u7a7a\u8c03\u3001\u706f\u5149\u672a\u5173"))
    cases.append(("age", match_causes(["\u7528\u4e86\u51e0\u5e74"])[0][1] == "\u7535\u74f6\u8001\u5316"))
    cases.append(("add", match_causes(["\u52a0\u4e86\u8bb0\u5f55\u4eea"])[0][1] == "\u52a0\u88c5\u8bbe\u5907\u8017\u7535"))
    cases.append(("circuit", match_causes(["\u505c\u4e00\u591c\u5c31\u4e8f\u7535"])[0][1] == "\u7535\u8def\u6216\u7528\u7535\u5f02\u5e38"))
    cases.append(("winter", match_causes(["\u51ac\u5929"])[0][1] == "\u4f4e\u6e29\u5f71\u54cd"))
    cases.append(("order", [h[0] for h in match_causes(
        ["\u51ac\u5929", "\u957f\u671f\u505c\u653e"])] == [1, 7]))
    cases.append(("no_hit", match_causes(["\u5b8c\u5168\u65e0\u5173\u7684\u63cf\u8ff0"]) == []))
    cases.append(("tokens_cn", len(tokens("\u6253\u4e0d\u7740\u706b\u3001\u505c\u653e\u4e00\u5468")) == 2))
    rep = build_report(["\u6253\u4e0d\u7740\u706b", "\u505c\u653e\u4e00\u5468"])
    cases.append(("rep_cause", "\u4e8f\u7535\u539f\u56e0\u6392\u5e8f" in rep))
    cases.append(("rep_steps", "\u642d\u7535\u6b63\u786e\u987a\u5e8f" in rep))
    cases.append(("rep_last_neg", "\u6700\u540e\u63a5\u8d1f\u6781" in rep))
    cases.append(("rep_taboo", "\u6b63\u8d1f\u6781\u4e0d\u53ef\u53cd\u63a5" in rep))
    cases.append(("rep_wire", "\u7ebf\u5f84\u8981\u591f" in rep))
    cases.append(("rep_retry", "\u4e0d\u8981\u8fde\u7eed\u957f\u65f6\u95f4\u53cd\u590d\u6253" in rep))
    cases.append(("rep_replace", "\u5fc5\u987b\u6362\u7535\u6c60\u7684\u5224\u5b9a" in rep))
    cases.append(("rep_bulge", "\u7535\u74f6\u9f13\u5305" in rep))
    cases.append(("rep_winter", "\u51ac\u5b63\u4f4e\u6e29\u5f71\u54cd" in rep))
    cases.append(("rep_kitting", "\u5e94\u6025\u542f\u52a8\u7535\u6e90" in rep))
    rep2 = build_report([])
    cases.append(("rep_fallback", "\u53ef\u6309\u4e0b\u65b9\u987a\u5e8f\u9010\u6761\u6392\u67e5" in rep2))
    rep3 = build_report(["\u5b8c\u5168\u65e0\u5173"])
    cases.append(("rep_fallback2", "\u957f\u671f\u505c\u653e\u672a\u65ad\u7535" in rep3))
    bom = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_probe.json")
    with open(bom, "w", encoding="utf-8-sig") as f:
        f.write('{"symptoms": ["\u51ac\u5929"]}')
    try:
        cases.append(("bom_ok", load_json(bom).get("symptoms") == ["\u51ac\u5929"]))
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
    ap = argparse.ArgumentParser(description="car battery audit")
    ap.add_argument("--symptoms", default=None)
    ap.add_argument("--file", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--format", default="md")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    symptoms = a.symptoms
    if a.file:
        try:
            data = load_json(a.file)
        except Exception as exc:
            print(str(exc))
            return 2
        symptoms = data.get("symptoms", symptoms)
    report = build_report(symptoms or [])
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "car_battery_result.md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
