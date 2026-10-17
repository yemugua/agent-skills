# -*- coding: utf-8 -*-
"""motion_sickness_check: \u6655\u8f66\u65b9\u6cd5\u6709\u6548\u6027\u5206\u7ea7\u4e0e\u51fa\u884c\u5efa\u8bae\u3002

\u53ea\u505a\u65b9\u6cd5\u5206\u7ea7\u4e0e\u63d0\u793a\uff0c\u4e0d\u63d0\u4f9b\u4efb\u4f55\u836f\u7269\u5242\u91cf\u3002
"""
import argparse
import json
import os

# (\u65b9\u6cd5\u540d, \u6548\u679c\u5206\u7ea7 1-4 \u8d8a\u9ad8\u8d8a\u6709\u6548, \u5c40\u9650\u8bf4\u660e)
METHODS = [
    ("\u770b\u7a97\u5916\u8fdc\u5904\u56fa\u5b9a\u53c2\u7167\u7269", 3,
     "\u8ba9\u89c6\u89c9\u4e0e\u524d\u5ead\u4fe1\u606f\u8d8b\u4e8e\u4e00\u81f4\uff1b\u53ea\u5bf9\u8f7b\u4e2d\u5ea6\u6709\u6548\uff0c\u4e0d\u80fd\u5b8c\u5168\u9884\u9632"),
    ("\u5ea7\u4f4d\u9760\u524d\u9762\u5411\u884c\u9a76\u65b9\u5411", 3,
     "\u51cf\u5c11\u6643\u52a8\u65b9\u5411\u4e0e\u89c6\u91ce\u7684\u4e0d\u5339\u914d"),
    ("\u63d0\u524d\u6309\u8bf4\u660e\u4e66\u670d\u7528\u6655\u8f66\u836f", 3,
     "\u5c11\u6570\u80fd\u4f5c\u7528\u4e8e\u6210\u56e0\u7684\u624b\u6bb5\u4e4b\u4e00\uff0c\u9700\u6309\u8bf4\u660e\u4e66\u6216\u533b\u5631\u63d0\u524d\u670d\u7528"),
    ("\u7ec4\u5408\u4f7f\u7528\u591a\u79cd\u63aa\u65bd", 4,
     "\u7ec4\u5408\u6548\u679c\u901a\u5e38\u4f18\u4e8e\u4efb\u4f55\u5355\u4e00\u624b\u6bb5"),
    ("\u5f00\u7a97\u901a\u98ce", 2,
     "\u6539\u5584\u6c14\u5473\u5e26\u6765\u7684\u4e0d\u9002\u611f\uff0c\u4f46\u4e0d\u89e3\u51b3\u4fe1\u606f\u4e0d\u4e00\u81f4"),
    ("\u6e05\u6de1\u996e\u98df\u5c11\u91cf\u8fdb\u98df", 2,
     "\u51cf\u5c11\u80c3\u90e8\u4e0d\u9002\uff0c\u7a7a\u8179\u53cd\u800c\u53ef\u80fd\u66f4\u96be\u53d7"),
    ("\u56bc\u53e3\u9999\u7cd6\u6216\u5403\u4e1c\u897f", 2,
     "\u4e3b\u8981\u7f13\u89e3\u6076\u5fc3\u611f\uff0c\u4e0d\u89e3\u51b3\u6210\u56e0"),
    ("\u6655\u8f66\u8d34", 2,
     "\u6210\u5206\u4e0e\u4f5c\u7528\u673a\u5236\u7684\u8bf4\u6cd5\u8f83\u591a\uff0c\u6548\u679c\u56e0\u4eba\u800c\u5f02\uff0c\u4e0d\u80fd\u66ff\u4ee3\u5176\u4ed6\u63aa\u65bd"),
    ("\u5206\u6563\u6ce8\u610f\u529b\uff08\u770b\u7535\u5f71\u3001\u804a\u5929\uff09", 1,
     "\u628a\u6ce8\u610f\u529b\u56fa\u5b9a\u5728\u8fd1\u8ddd\u79bb\u9759\u6b62\u76ee\u6807\u4e0a\uff0c\u4f1a\u52a0\u5927\u89c6\u89c9\u4e0e\u524d\u5ead\u7684\u4e0d\u4e00\u81f4\uff0c\u672c\u8eab\u662f\u52a0\u91cd\u56e0\u7d20"),
    ("\u95fb\u5473\u9053\uff08\u9999\u6c34\u3001\u7eb8\u5dfe\u7b49\uff09", 1,
     "\u53ea\u662f\u8f6c\u79fb\u5bf9\u6076\u5fc3\u7684\u6ce8\u610f\u529b\uff0c\u4e0d\u5f71\u54cd\u6210\u56e0"),
]

GROUP_CN = {"adult": "\u6210\u4eba", "child": "\u513f\u7ae5", "pregnant": "\u5b55\u5987"}

GROUP_NOTE = {
    "adult": "\u5148\u9009\u5bf9\u5ea7\u4f4d\u4e0e\u53c2\u7167\u7269\uff0c\u518d\u6309\u8bf4\u660e\u4e66\u6216\u533b\u5631\u8003\u8651\u7528\u836f",
    "child": "\u4e0d\u8981\u76f4\u63a5\u7528\u6210\u4eba\u7684\u836f\u6216\u6210\u4eba\u5242\u91cf\uff0c\u5177\u4f53\u53ef\u7528\u5e74\u9f84\u4ee5\u836f\u54c1\u8bf4\u660e\u4e66\u4e3a\u51c6\uff1b\u75c7\u72b6\u4e25\u91cd\u6216\u6301\u7eed\u4e0d\u7f13\u89e3\u8981\u770b\u533b\u751f",
    "pregnant": "\u5b55\u671f\u7528\u836f\u5fc5\u987b\u5148\u54a8\u8be2\u533b\u751f\uff1b\u9996\u9009\u9760\u524d\u5ea7\u4f4d\u3001\u770b\u7a97\u5916\u3001\u6e05\u6de1\u996e\u98df\u3001\u901a\u98ce\u7b49\u975e\u836f\u7269\u63aa\u65bd",
}

SEE_DOC = [
    "\u75c7\u72b6\u6301\u7eed\u4e0d\u7f13\u89e3",
    "\u53cd\u590d\u5267\u70c8\u5455\u5410",
    "\u4f34\u968f\u5934\u75db\u3001\u89c6\u7269\u6a21\u7cca\u3001\u8bf4\u8bdd\u542b\u7cca",
    "\u4f34\u968f\u80a2\u4f53\u9ebb\u6728\u65e0\u529b",
    "\u80f8\u95f7\u3001\u5fc3\u60b8\u3001\u610f\u8bc6\u6a21\u7cca",
    "\u513f\u7ae5\u9ad8\u70ed\u4f34\u968f\u5455\u5410",
    "\u5b55\u5987\u4f34\u968f\u8179\u75db\u6216\u51fa\u8840",
]

DRUG_NOTE = [
    "\u7528\u91cf\u3001\u9891\u6b21\u4e0e\u5e74\u9f84\u9650\u5236\u4ee5\u836f\u54c1\u8bf4\u660e\u4e66\u548c\u533b\u5631\u4e3a\u51c6",
    "\u9a7e\u9a76\u5458\u80fd\u5426\u4f7f\u7528\u5fc5\u987b\u770b\u8bf4\u660e\u4e66\u660e\u786e\u8bf4\u660e\uff0c\u4e0d\u51ed\u611f\u89c9",
    "\u591a\u6570\u6655\u8f66\u836f\u9700\u63d0\u524d\u670d\u7528\uff0c\u4e34\u65f6\u53d1\u4f5c\u65f6\u518d\u5403\u5f80\u5f80\u6765\u4e0d\u53ca",
    "\u540c\u7c7b\u836f\u7269\u4e0d\u8981\u540c\u65f6\u670d\u7528",
    "\u6b63\u5728\u670d\u7528\u5176\u4ed6\u836f\u7269\u65f6\uff0c\u5148\u95ee\u533b\u751f\u6216\u836f\u5e08",
]

PREP_STEPS = [
    "\u9009\u5ea7\u4f4d\uff1a\u9760\u524d\u3001\u9762\u5411\u884c\u9a76\u65b9\u5411\u3001\u5c3d\u91cf\u9760\u4e2d\u95f4\u5c11\u6643",
    "\u51fa\u884c\u524d\u996e\u98df\u6e05\u6de1\uff0c\u522b\u5403\u592a\u9971\u4e5f\u522b\u7a7a\u8179",
    "\u9700\u8981\u65f6\u6309\u8bf4\u660e\u4e66\u6216\u533b\u5631\u63d0\u524d\u670d\u7528\u6655\u8f66\u836f",
    "\u8def\u4e0a\u770b\u7a97\u5916\u8fdc\u5904\u56fa\u5b9a\u53c2\u7167\u7269\uff0c\u4e0d\u770b\u8fd1\u8ddd\u79bb\u5c4f\u5e55",
    "\u5f00\u7a97\u901a\u98ce\uff0c\u628a\u6ce8\u610f\u529b\u653e\u5728\u8fdc\u5904\u98ce\u666f\u4e0a",
    "\u63d0\u524d\u4e0b\u8f66\u4f11\u606f\uff0c\u4e0d\u8981\u786c\u6491\u5230\u76ee\u7684\u5730",
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
        return [t for t in text.replace(",", " ").replace("\u3001", " ").split() if t]
    return [str(x) for x in (text or [])]


def match_methods(symptoms):
    """Return matching methods sorted by effect level (best first)."""
    joined = " ".join(s.lower() for s in tokens(symptoms))
    hits = []
    for name, level, limit in METHODS:
        if name in joined:
            hits.append((level, name, limit))
            continue
        for key in KEYWORDS.get(name, []):
            if key in joined:
                hits.append((level, name, limit))
                break
    hits.sort(key=lambda x: -x[0])
    return hits


KEYWORDS = {
    "\u770b\u7a97\u5916\u8fdc\u5904\u56fa\u5b9a\u53c2\u7167\u7269": ["\u7a97\u5916", "\u770b\u8fdc\u5904", "\u8fdc\u5904", "\u770b\u98ce\u666f"],
    "\u5ea7\u4f4d\u9760\u524d\u9762\u5411\u884c\u9a76\u65b9\u5411": ["\u9760\u524d", "\u524d\u6392", "\u5ea7\u4f4d"],
    "\u63d0\u524d\u6309\u8bf4\u660e\u4e66\u670d\u7528\u6655\u8f66\u836f": ["\u5403\u836f", "\u6655\u8f66\u836f", "\u670d\u836f", "\u63d0\u524d\u5403"],
    "\u7ec4\u5408\u4f7f\u7528\u591a\u79cd\u63aa\u65bd": ["\u7ec4\u5408", "\u591a\u79cd\u65b9\u6cd5"],
    "\u5f00\u7a97\u901a\u98ce": ["\u5f00\u7a97", "\u901a\u98ce"],
    "\u6e05\u6de1\u996e\u98df\u5c11\u91cf\u8fdb\u98df": ["\u6e05\u6de1", "\u5c11\u98df", "\u5403\u70b9\u4e1c\u897f", "\u7a7a\u8179"],
    "\u56bc\u53e3\u9999\u7cd6\u6216\u5403\u4e1c\u897f": ["\u53e3\u9999\u7cd6", "\u56bc"],
    "\u6655\u8f66\u8d34": ["\u6655\u8f66\u8d34", "\u8d34"],
    "\u5206\u6563\u6ce8\u610f\u529b\uff08\u770b\u7535\u5f71\u3001\u804a\u5929\uff09": ["\u5206\u6563\u6ce8\u610f\u529b", "\u770b\u7535\u5f71", "\u804a\u5929", "\u5237\u624b\u673a",
                                   "\u770b\u624b\u673a", "\u6ce8\u610f\u529b"],
    "\u95fb\u5473\u9053\uff08\u9999\u6c34\u3001\u7eb8\u5dfe\u7b49\uff09": ["\u95fb\u5473\u9053", "\u95fb", "\u9999\u6c34"],
}


def level_word(level):
    level_word_cache = {4: "\u76f8\u5bf9\u6700\u6709\u6548", 3: "\u76f8\u5bf9\u6709\u6548", 2: "\u6709\u9650\u7f13\u89e3",
                        1: "\u57fa\u672c\u65e0\u6548\u6216\u53ef\u80fd\u52a0\u91cd"}
    return level_word_cache.get(level, "\u672a\u8bc4\u4f30")


def build_report(symptoms, group):
    hits = match_methods(symptoms)
    gkey = group if group in GROUP_NOTE else "adult"
    out = ["# \u6655\u8f66\u65b9\u6cd5\u4e0e\u51fa\u884c\u5efa\u8bae", ""]
    out.append("## \u673a\u5236")
    out.append("")
    out.append("\u6655\u52a8\u75c7\u7684\u57fa\u672c\u539f\u56e0\u662f\u524d\u5ead\u7cfb\u7edf\u611f\u53d7\u5230\u7684\u8fd0\u52a8\u4fe1\u606f\u4e0e\u89c6\u89c9\u3001\u672c\u4f53\u611f\u89c9\u63d0\u4f9b\u7684\u4fe1\u606f\u4e0d\u4e00\u81f4\u3002")
    out.append("\u773c\u775b\u770b\u5230\u7684\u548c\u524d\u5ead\u611f\u53d7\u5230\u7684\u8d8a\u662f\u5bf9\u4e0d\u4e0a\uff0c\u8d8a\u5bb9\u6613\u6655\uff1b\u8fd9\u6b63\u662f\u770b\u624b\u673a\u6bd4\u770b\u7a97\u5916\u66f4\u5bb9\u6613\u6655\u7684\u539f\u56e0\u3002")
    out.append("")
    out.append("## \u5df2\u7528\u65b9\u6cd5\u7684\u6548\u679c\u5206\u7ea7")
    out.append("")
    if hits:
        out.append("| \u65b9\u6cd5 | \u6548\u679c | \u5c40\u9650\u8bf4\u660e |")
        out.append("|---|---|---|")
        for level, name, limit in hits:
            out.append("| %s | %s | %s |" % (name, level_word(level), limit))
        out.append("")
        worst = [h for h in hits if h[0] == 1]
        if worst:
            out.append("\u6ce8\u610f\uff1a\u5206\u6563\u6ce8\u610f\u529b\u4e0e\u95fb\u5473\u9053\u8fd9\u7c7b\u65b9\u6cd5\u672c\u8eab**\u53ef\u80fd\u5c31\u662f\u52a0\u91cd\u56e0\u7d20**\uff0c"
                       "\u5b83\u4eec\u628a\u6ce8\u610f\u529b\u653e\u5230\u8fd1\u8ddd\u79bb\u9759\u6b62\u76ee\u6807\u4e0a\uff0c\u52a0\u5927\u4e86\u89c6\u89c9\u4e0e\u524d\u5ead\u7684\u4e0d\u4e00\u81f4\u3002")
            out.append("")
    else:
        out.append("- \u672a\u8bc6\u522b\u5230\u5df2\u7528\u65b9\u6cd5\uff0c\u53ef\u53c2\u8003\u4e0b\u9762\u7684\u51c6\u5907\u987a\u5e8f")
        out.append("")
    out.append("## \u76f8\u5bf9\u6709\u6548\u7684\u505a\u6cd5")
    out.append("")
    for name, level, limit in METHODS:
        if level >= 3:
            out.append("- **%s**\uff1a%s" % (name, limit))
    out.append("")
    out.append("## %s \u7279\u522b\u63d0\u793a" % GROUP_CN[gkey])
    out.append("")
    out.append("- %s" % GROUP_NOTE[gkey])
    if gkey == "child":
        out.append("- \u513f\u7ae5\u6655\u8f66\u5e38\u8868\u73b0\u4e3a\u54ed\u95f9\u3001\u8138\u8272\u82cd\u767d\u3001\u5455\u5410\uff0c\u4f34\u968f\u51fa\u6c57\u4e0e\u4e4f\u529b")
        out.append("- \u5455\u5410\u540e\u9700\u8981\u8865\u5145\u6c34\u5206")
    if gkey == "pregnant":
        out.append("- \u6655\u8f66\u5bf9\u5b55\u5987\u7684\u5f71\u54cd\u901a\u5e38\u5927\u4e8e\u666e\u901a\u4e58\u5ba2")
        out.append("- \u4f34\u968f\u8179\u75db\u3001\u51fa\u8840\u3001\u80ce\u52a8\u5f02\u5e38\u65f6\u7acb\u5373\u5c31\u533b")
    out.append("")
    out.append("## \u51fa\u884c\u524d\u51c6\u5907\u987a\u5e8f")
    out.append("")
    for i, step in enumerate(PREP_STEPS, 1):
        out.append("%d. %s" % (i, step))
    out.append("")
    out.append("## \u7528\u836f\u6ce8\u610f\u4e8b\u9879")
    out.append("")
    for note in DRUG_NOTE:
        out.append("- %s" % note)
    out.append("")
    out.append("- \u672c\u811a\u672c\u4e0d\u63d0\u4f9b\u4efb\u4f55\u836f\u7269\u5242\u91cf")
    out.append("- \u6655\u8f66\u836f\u5e38\u89c1\u7c7b\u522b\u4e3a\u6297\u7ec4\u80fa\u7c7b\u4e0e\u6297\u80c6\u78b1\u7c7b\uff0c\u53ef\u80fd\u51fa\u73b0\u55dc\u7761\u3001\u53e3\u5e72\u7b49")
    out.append("")
    out.append("## \u9700\u8981\u5c31\u533b\u7684\u4fe1\u53f7")
    out.append("")
    for item in SEE_DOC:
        out.append("- %s" % item)
    out.append("")
    out.append("\u4ee5\u4e0a\u4efb\u4e00\u60c5\u51b5\u51fa\u73b0\u65f6\uff0c\u4e0d\u8981\u6309\u6655\u8f66\u7ee7\u7eed\u5904\u7406\uff0c\u5e94\u5c3d\u5feb\u5c31\u533b\u3002")
    out.append("")
    out.append("## \u8fb9\u754c")
    out.append("")
    out.append("- \u672c\u811a\u672c\u53ea\u505a\u65b9\u6cd5\u6709\u6548\u6027\u5206\u7ea7\uff0c\u4e0d\u63d0\u4f9b\u836f\u7269\u7528\u91cf")
    out.append("- \u7528\u91cf\u3001\u9891\u6b21\u4e0e\u5e74\u9f84\u9650\u5236\u4ee5\u836f\u54c1\u8bf4\u660e\u4e66\u548c\u533b\u5631\u4e3a\u51c6")
    out.append("- \u662f\u5426\u9700\u8981\u5c31\u533b\u3001\u80fd\u5426\u4f7f\u7528\u67d0\u7c7b\u836f\u7269\u7531\u533b\u751f\u6216\u836f\u5e08\u5224\u65ad")
    return "\n".join(out) + "\n"


def selftest():
    cases = []
    cases.append(("window", match_methods(["\u770b\u7a97\u5916"])[0][1] == "\u770b\u7a97\u5916\u8fdc\u5904\u56fa\u5b9a\u53c2\u7167\u7269"))
    cases.append(("phone", match_methods(["\u770b\u624b\u673a"])[0][0] == 1))
    cases.append(("smell", match_methods(["\u95fb\u5473\u9053"])[0][0] == 1))
    cases.append(("drug", match_methods(["\u5403\u4e86\u6655\u8f66\u836f"])[0][0] == 3))
    cases.append(("sort_best_first", [h[0] for h in match_methods(
        ["\u95fb\u5473\u9053", "\u770b\u7a97\u5916"])] == [3, 1]))
    cases.append(("no_hit", match_methods(["\u5b8c\u5168\u65e0\u5173\u7684\u63cf\u8ff0"]) == []))
    cases.append(("tokens_cn", len(tokens("\u6076\u5fc3\u3001\u770b\u624b\u673a")) == 2))
    cases.append(("tokens_none", tokens("") == []))
    cases.append(("word4", level_word(4) == "\u76f8\u5bf9\u6700\u6709\u6548"))
    cases.append(("word1", "\u52a0\u91cd" in level_word(1)))
    rep = build_report(["\u770b\u624b\u673a", "\u95fb\u5473\u9053"], "adult")
    cases.append(("rep_mech", "\u672c\u4f53\u611f\u89c9\u63d0\u4f9b\u7684\u4fe1\u606f\u4e0d\u4e00\u81f4" in rep))
    cases.append(("rep_table", "\u5c40\u9650\u8bf4\u660e" in rep))
    cases.append(("rep_warn", "\u52a0\u91cd\u56e0\u7d20" in rep))
    cases.append(("rep_no_dose", "\u4e0d\u63d0\u4f9b\u4efb\u4f55\u836f\u7269\u5242\u91cf" in rep))
    cases.append(("rep_see", "\u5c3d\u5feb\u5c31\u533b" in rep))
    rep2 = build_report([], "child")
    cases.append(("rep_child", "\u6210\u4eba\u7684\u836f\u6216\u6210\u4eba\u5242\u91cf" in rep2))
    cases.append(("rep_child_water", "\u8865\u5145\u6c34\u5206" in rep2))
    rep3 = build_report([], "pregnant")
    cases.append(("rep_pregnant", "\u5fc5\u987b\u5148\u54a8\u8be2\u533b\u751f" in rep3))
    cases.append(("rep_pregnant2", "\u80ce\u52a8\u5f02\u5e38" in rep3))
    rep4 = build_report([], "unknown-group")
    cases.append(("rep_group_fallback", "## \u6210\u4eba \u7279\u522b\u63d0\u793a" in rep4))
    bom = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_probe.json")
    with open(bom, "w", encoding="utf-8-sig") as f:
        f.write('{"symptoms": ["\u770b\u7a97\u5916"]}')
    try:
        cases.append(("bom_ok", load_json(bom).get("symptoms") == ["\u770b\u7a97\u5916"]))
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
    ap = argparse.ArgumentParser(description="motion sickness method audit")
    ap.add_argument("--symptoms", default=None)
    ap.add_argument("--group", default=None)
    ap.add_argument("--file", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--format", default="md")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    symptoms, group = a.symptoms, a.group
    if a.file:
        try:
            data = load_json(a.file)
        except Exception as exc:
            print(str(exc))
            return 2
        symptoms = data.get("symptoms", symptoms)
        group = data.get("group", group)
    report = build_report(symptoms or [], group or "adult")
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "motion_sickness_result.md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
