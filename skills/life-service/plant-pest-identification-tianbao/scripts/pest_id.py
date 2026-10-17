# -*- coding: utf-8 -*-
"""\u690d\u7269\u75c5\u866b\u5bb3\u8bc6\u522b\u4e0e\u9632\u6cbb\u7c7b\u522b\u5206\u6d41\u5de5\u5177\u3002

\u7528\u6cd5:
  python pest_id.py --file pest.json [--json]
  python pest_id.py --selftest

\u672c\u5de5\u5177\u53ea\u8f93\u51fa\u8bc6\u522b\u7279\u5f81\u4e0e\u9632\u6cbb\u65b9\u5f0f\u7c7b\u522b, \u4e0d\u542b\u4efb\u4f55\u836f\u5242\u540d\u79f0\u3001\u54c1\u724c\u3001\u6d53\u5ea6\u4e0e\u914d\u6bd4\u3002
"""
import argparse
import io
import json
import os
import sys

# \u75c5\u5bb3\u7279\u5f81: \u4ee3\u53f7 -> (\u540d\u79f0, \u90e8\u4f4d, \u5f62\u6001, \u5206\u5e03, \u6613\u6df7\u6dc6)
DISEASES = {
    "white_powder": ("\u767d\u7c89\u75c5", "\u53f6\u9762\u4e3a\u4e3b",
                     "\u767d\u8272\u6216\u7070\u767d\u8272\u7c89\u72b6\u9709\u5c42, \u50cf\u6492\u4e86\u5c42\u9762\u7c89, \u64e6\u5f97\u6389",
                     "\u53f6\u7247\u6b63\u9762, \u6269\u5c55\u5feb, \u5e38\u8fde\u7247", "\u971c\u9709\u75c5, \u7070\u5c18"),
    "downy_mildew": ("\u971c\u9709\u75c5", "\u53f6\u9762",
                     "\u6c34\u6d78\u72b6\u9ec4\u6591, \u53f6\u80cc\u5bf9\u5e94\u4f4d\u7f6e\u6709\u7070\u7d2b\u8272\u9709\u5c42, \u64e6\u4e0d\u6389",
                     "\u53f6\u80cc\u6709\u9709\u662f\u5224\u636e, \u4e0e\u6b63\u9762\u6591\u4e00\u4e00\u5bf9\u5e94", "\u767d\u7c89\u75c5"),
    "rust": ("\u9508\u75c5", "\u53f6\u9762",
             "\u6de1\u9ec4\u5c0f\u6591\u540e\u957f\u51fa\u9ec4\u8910\u6216\u9508\u8910\u8272\u7c89\u72b6\u5c0f\u75b1",
             "\u5e38\u6709\u892a\u7eff\u5c0f\u6591\u5728\u524d\u3001\u9508\u7c89\u5728\u540e\u4e24\u4e2a\u9636\u6bb5", "\u767d\u7c89\u75c5, \u869c\u866b\u5206\u6ccc\u7269"),
    "anthracnose": ("\u70ad\u75bd\u75c5", "\u679c\u5b9e\u3001\u830e\u3001\u53f6",
                    "\u5706\u5f62\u6216\u4e0d\u89c4\u5219\u8910\u6216\u9ed1\u8910\u6591, \u4e2d\u5fc3\u51f9\u9677\u5e76\u6709\u9ed1\u8272\u5c0f\u70b9",
                    "\u679c\u5b9e\u4e0a\u51f9\u9677\u660e\u663e", "\u75ab\u75c5, \u65e5\u707c"),
    "blight": ("\u75ab\u75c5", "\u679c\u5b9e\u3001\u830e\u57fa",
               "\u6c34\u6d78\u72b6\u6697\u7eff\u6591, \u8fc5\u901f\u6269\u5927\u53d8\u8910\u8150\u70c2",
               "\u679c\u5b9e\u4e0a\u5448\u6cb9\u6d78\u72b6\u8f6f\u8150", "\u70ad\u75bd, \u8f6f\u8150"),
    "soft_rot": ("\u8f6f\u8150\u75c5", "\u830e\u57fa\u3001\u679c",
                 "\u7ec4\u7ec7\u8f6f\u70c2, \u6709\u8165\u81ed, \u6e17\u51fa\u9ecf\u6db2",
                 "\u5e38\u4ece\u4f24\u53e3\u6216\u866b\u5bb3\u5904\u5f00\u59cb", "\u75ab\u75c5"),
    "bacterial_wilt": ("\u9752\u67af\u75c5", "\u830e\u3001\u6839",
                       "\u830e\u57fa\u90e8\u53d8\u8910, \u7eb5\u5207\u53ef\u89c1\u7ef4\u7ba1\u675f\u53d8\u8910",
                       "\u4e2d\u5348\u840e\u852b\u591c\u95f4\u6062\u590d, \u6570\u65e5\u5168\u682a\u67af\u6b7b", "\u67af\u840e\u75c5, \u7f3a\u6c34"),
    "virus_like": ("\u7591\u4f3c\u75c5\u6bd2\u7c7b\u75c5\u5bb3", "\u5168\u682a",
                   "\u82b1\u53f6, \u6591\u9a73, \u6761\u7eb9, \u53f6\u7247\u76b1\u7f29\u7578\u5f62, \u690d\u682a\u77ee\u5316",
                   "\u7cfb\u7edf\u6027\u75c5\u5bb3, \u65b0\u53f6\u75c7\u72b6\u66f4\u660e\u663e", "\u7f3a\u7d20, \u836f\u5bb3"),
    "nutrient": ("\u7f3a\u7d20, \u975e\u75c5\u5bb3", "\u5168\u682a",
                 "\u5747\u5300\u9ec4\u5316\u6216\u53f6\u8109\u95f4\u9ec4\u5316, \u6309\u53f6\u9f84\u5206\u5e03\u6709\u89c4\u5f8b",
                 "\u4e0e\u65bd\u80a5\u8bb0\u5f55\u543b\u5408", "\u767d\u7c89\u75c5\u521d\u671f, \u75c5\u6bd2"),
    "herbicide": ("\u836f\u5bb3, \u975e\u75c5\u5bb3", "\u53f6\u9762",
                  "\u707c\u6591, \u836f\u6591, \u7578\u5f62, \u5e38\u5728\u65bd\u836f\u540e 1-3 \u5929\u51fa\u73b0",
                  "\u4e0e\u65bd\u836f\u65f6\u95f4\u9ad8\u5ea6\u91cd\u5408", "\u75c5\u5bb3, \u7ea2\u8718\u86db"),
}

# \u866b\u5bb3\u7279\u5f81: \u4ee3\u53f7 -> (\u540d\u79f0, \u90e8\u4f4d, \u5f62\u6001, \u786e\u8ba4\u65b9\u6cd5, \u6613\u6df7\u6dc6)
PESTS = {
    "aphid": ("\u869c\u866b", "\u5ae9\u53f6\u3001\u830e\u3001\u82b1",
              "\u5c0f\u578b\u8f6f\u866b, \u6210\u7fa4\u805a\u5728\u53f6\u80cc\u4e0e\u5ae9\u68a2, \u871c\u9732\u53d1\u4eae, \u53f6\u7247\u53d1\u9ecf",
              "\u6447\u52a8\u679d\u6761, \u767d\u7eb8\u4e0b\u65b9\u6709\u866b\u843d\u4e0b", "\u84df\u9a6c, \u767d\u7c89\u8671"),
    "spider_mite": ("\u7ea2\u8718\u86db(\u53f6\u87a8)", "\u53f6\u80cc",
                    "\u6781\u5c0f\u8089\u773c\u96be\u8fa8; \u53f6\u9762\u5bc6\u96c6\u9488\u5c16\u72b6\u767d\u70b9, \u53f6\u80cc\u6709\u7ec6\u7f51",
                    "\u653e\u5927\u955c\u770b\u53f6\u80cc\u6709\u79fb\u52a8\u5c0f\u70b9; \u624b\u6478\u53f6\u9762\u53d1\u6da9", "\u84df\u9a6c, \u767d\u7c89\u75c5\u65e9\u671f"),
    "thrips": ("\u84df\u9a6c", "\u82b1\u3001\u53f6\u3001\u5e7c\u679c",
               "\u7ec6\u957f\u5c0f\u866b 1-2 mm, \u53d7\u60ca\u5feb\u901f\u9003\u8d70; \u82b1\u671f\u4e0e\u5e7c\u679c\u671f\u4e3a\u5bb3\u91cd",
               "\u6447\u52a8\u6216\u62cd\u6253, \u770b\u6389\u843d\u4e0e\u98de\u8d70\u7684\u5c0f\u866b", "\u869c\u866b, \u5c0f\u98de\u866b"),
    "whitefly": ("\u767d\u7c89\u8671", "\u53f6\u80cc",
                 "\u6210\u866b\u767d\u8272\u5c0f\u86fe\u5584\u98de, \u5e7c\u866b\u4e0e\u5375\u5728\u53f6\u80cc, \u8986\u767d\u8272\u8721\u7c89",
                 "\u53f6\u80cc\u8f7b\u62cd, \u6210\u866b\u6210\u56e2\u98de\u8d77", "\u84df\u9a6c, \u869c\u866b"),
    "scale": ("\u86a7\u58f3\u866b", "\u830e\u3001\u53f6\u3001\u679c\u5b9e",
              "\u56fa\u5b9a\u4e0d\u52a8\u7684\u786c\u58f3\u72b6\u5c0f\u9686\u8d77, \u8910\u8272\u6216\u767d\u8272, \u522e\u6389\u58f3\u5185\u6709\u866b\u4f53",
              "\u786c\u58f3\u522e\u4e0d\u52a8, \u7528\u9488\u6311\u51fa\u767d\u8272\u866b\u4f53", "\u82bd\u9cde"),
    "caterpillar": ("\u9752\u866b", "\u53f6\u3001\u82b1\u3001\u679c\u5b9e",
                    "\u7c97\u58ee\u8089\u8d28\u5e7c\u866b, \u4f53\u8868\u5149\u6ed1\u6216\u5177\u521a\u6bdb, \u6392\u51fa\u660e\u663e\u866b\u7caa",
                    "\u89c1\u5927\u9897\u7c92\u6df1\u8272\u866b\u7caa\u5373\u5224\u65ad", "\u8717\u725b, \u86de\u8753"),
    "leafminer": ("\u6591\u6f5c\u8747", "\u53f6",
                  "\u53f6\u7247\u4e0a\u767d\u8272\u5f2f\u66f2\u6f5c\u9053\u96a7\u9053",
                  "\u53f6\u9762\u51fa\u73b0\u86c7\u5f62\u767d\u7ebf", "\u84df\u9a6c\u5371\u5bb3, \u53f6\u6591"),
    "slug": ("\u86de\u8753\u4e0e\u8717\u725b", "\u5168\u682a\u5c24\u5176\u591c\u95f4",
             "\u7559\u4e0b\u94f6\u767d\u8272\u9ecf\u6db2\u75d5\u8ff9\u4e0e\u5543\u98df\u5b54",
             "\u591c\u95f4\u7528\u624b\u7535\u68c0\u67e5, \u9ecf\u6db2\u662f\u5224\u636e", "\u5543\u98df\u5b54\u578b\u866b\u5bb3"),
}

# \u6613\u6df7\u6dc6\u5bf9\u7167: (A, B, \u533a\u5206\u8981\u70b9)
CONFUSE = [
    ("\u767d\u7c89\u75c5", "\u971c\u9709\u75c5", "\u6b63\u9762\u767d\u8272\u7c89\u5c42\u64e6\u5f97\u6389; \u53f6\u80cc\u7070\u7d2b\u9709\u5c42\u64e6\u4e0d\u6389"),
    ("\u767d\u7c89\u75c5", "\u7070\u5c18", "\u7c89\u5c42\u6709\u6269\u5c55\u8513\u5ef6; \u7070\u5c18\u5206\u5e03\u5747\u5300\u65e0\u6269\u5c55"),
    ("\u7ea2\u8718\u86db", "\u869c\u866b", "\u871c\u9732\u662f\u869c\u866b\u72ec\u6709"),
    ("\u7ea2\u8718\u86db", "\u767d\u7c89\u75c5\u65e9\u671f", "\u624b\u6478\u53f6\u9762\u53d1\u6da9\u662f\u53f6\u87a8"),
    ("\u84df\u9a6c", "\u869c\u866b", "\u84df\u9a6c\u53d7\u60ca\u5feb\u901f\u9003\u8d70\u4e0d\u805a\u56e2; \u869c\u866b\u805a\u56e2\u4e0d\u52a8"),
    ("\u86a7\u58f3\u866b", "\u82bd\u9cde", "\u80fd\u5426\u7528\u9488\u6311\u51fa\u767d\u8272\u866b\u4f53"),
    ("\u9752\u866b", "\u86de\u8753", "\u5e72\u9897\u7c92\u72b6\u866b\u7caa; \u94f6\u767d\u8272\u9ecf\u6db2\u75d5\u8ff9"),
    ("\u7f3a\u7d20", "\u75c5\u6bd2", "\u7f3a\u7d20\u5168\u682a\u89c4\u5f8b\u4e0e\u65bd\u80a5\u543b\u5408; \u75c5\u6bd2\u65b0\u53f6\u75c7\u72b6\u66f4\u91cd\u65e0\u89c4\u5f8b"),
    ("\u836f\u5bb3", "\u75c5\u5bb3", "\u836f\u5bb3\u4e0e\u65bd\u836f\u65f6\u95f4\u91cd\u5408; \u75c5\u5bb3\u6e10\u8fdb\u6269\u6563"),
    ("\u9752\u67af\u75c5", "\u7f3a\u6c34", "\u7eb5\u5207\u830e\u770b\u7ef4\u7ba1\u675f\u662f\u5426\u53d8\u8910"),
]

ENVS = {
    "indoor": "\u5ba4\u5185",
    "balcony": "\u9633\u53f0",
    "garden": "\u5ead\u9662\u6216\u83dc\u5730",
    "field": "\u751f\u4ea7\u573a\u6240",
}

# \u73af\u5883\u4e0e\u9632\u6cbb\u65b9\u5f0f\u7684\u53ef\u7528\u6027
def control_options(env, has_live, pets):
    e = (env or "balcony").strip()
    opts = []
    if not has_live:
        opts.append(("\u975e\u866b\u5bb3\u7c7b", "\u6309\u75c5\u5bb3\u6216\u975e\u4fb5\u67d3\u6027\u539f\u56e0\u5904\u7406, \u5148\u6392\u9664\u7f3a\u7d20\u4e0e\u836f\u5bb3"))
    else:
        opts.append(("\u7269\u7406\u9632\u6cbb", "\u866b\u91cf\u5c11\u4e0e\u53d1\u751f\u521d\u671f\u9002\u7528; \u624b\u6355\u3001\u526a\u9664\u53d7\u5bb3\u679d\u53f6\u3001\u51b2\u6c34\u3001\u7c98\u677f\u3001\u9632\u866b\u7f51"))
        opts.append(("\u751f\u7269\u9632\u6cbb", "\u866b\u91cf\u5df2\u6210\u89c4\u6a21\u65f6\u9002\u7528; \u4fdd\u62a4\u5929\u654c\u3001\u5fae\u751f\u7269\u5236\u5242\u3001\u8bf1\u6355\u88c5\u7f6e"))
        if e in ("indoor", "balcony"):
            opts.append(("\u5316\u5b66\u9632\u6cbb", "\u5ba4\u5185\u4e0e\u534a\u5c01\u95ed\u9633\u53f0\u539f\u5219\u4e0a\u4e0d\u4f7f\u7528"))
        else:
            opts.append(("\u5316\u5b66\u9632\u6cbb", "\u4ec5\u5728\u7269\u7406\u4e0e\u751f\u7269\u5df2\u4e0d\u8db3\u4ee5\u63a7\u5236\u65f6, \u6309\u5f53\u5730\u690d\u4fdd\u90e8\u95e8\u6307\u5bfc\u9009\u62e9\u767b\u8bb0\u836f\u5242"))
        if pets:
            opts.append(("\u5ba0\u7269\u7ea6\u675f", "\u5bb6\u6709\u732b\u72ac\u6216\u89c2\u8d4f\u9c7c, \u6392\u9664\u5bf9\u5176\u6bd2\u6027\u5927\u7684\u7c7b\u522b; \u9c7c\u7f38\u6c34\u9762\u4e0a\u65b9\u4e0d\u5f97\u65bd\u836f"))
    if e == "field":
        opts.append(("\u4e0a\u62a5\u53e3\u5f84", "\u751f\u4ea7\u573a\u6240\u7684\u75c5\u866b\u75ab\u60c5\u5e94\u8054\u7cfb\u5f53\u5730\u690d\u4fdd\u673a\u6784"))
    return opts


REFERRAL = [
    "\u7591\u4f3c\u68c0\u75ab\u6027\u75c5\u866b\u5bb3, \u6309\u5f53\u5730\u89c4\u5b9a\u7684\u68c0\u75ab\u5bf9\u8c61\u6e05\u5355\u6838\u5bf9",
    "\u7591\u4f3c\u75c5\u6bd2\u7c7b\u75c5\u5bb3, \u8868\u73b0\u4e3a\u82b1\u53f6\u3001\u6591\u9a73\u6216\u6761\u7eb9\u75c7\u72b6",
    "\u5927\u68da\u3001\u519c\u7530\u7b49\u751f\u4ea7\u573a\u6240\u7684\u75c5\u866b\u75ab\u60c5",
    "\u9700\u8981\u9274\u5b9a\u5bb3\u866b\u79cd\u7c7b\u4ee5\u786e\u5b9a\u9632\u6cbb\u65b9\u6848",
    "\u9700\u8981\u786e\u5b9a\u7528\u836f\u54c1\u79cd\u3001\u5242\u91cf\u3001\u6b21\u6570\u4e0e\u5b89\u5168\u95f4\u9694\u671f",
    "\u5bb6\u5ead\u4ee5\u5916\u516c\u5171\u7a7a\u95f4\u7684\u7eff\u5316\u517b\u62a4\u7528\u836f",
]


def build_report(data):
    part = (data.get("part", "") or "").strip()
    sign = (data.get("sign", "") or "").strip()
    dist = (data.get("distribution", "") or "").strip()
    has_live = data.get("has_live", None)
    env = (data.get("env", "balcony") or "balcony").strip()
    pets = bool(data.get("has_pets", False))
    signs = data.get("signs", []) or []

    lines = []
    summary = {
        "part": part, "candidates": [], "has_live": has_live,
        "category": None, "env": ENVS.get(env, "\u9633\u53f0"),
        "control_options": [], "referral": [], "pesticide_named": False,
    }

    lines.append("=" * 68)
    lines.append("\u690d\u7269\u75c5\u866b\u5bb3\u8bc6\u522b\u4e0e\u9632\u6cbb\u7c7b\u522b\u5206\u6d41")
    lines.append("=" * 68)
    lines.append("  \u672c\u5de5\u5177\u53ea\u7ed9\u8bc6\u522b\u7279\u5f81\u4e0e\u9632\u6cbb\u65b9\u5f0f\u7c7b\u522b, \u4e0d\u542b\u836f\u5242\u540d\u79f0\u3001\u54c1\u724c\u3001\u6d53\u5ea6\u4e0e\u914d\u6bd4\u3002")
    lines.append("")

    lines.append("[\u4e00] \u89c2\u5bdf\u8bb0\u5f55")
    lines.append("-" * 68)
    lines.append("  \u90e8\u4f4d: %s" % (part or "\u672a\u63d0\u4f9b"))
    lines.append("  \u5f62\u6001\u7279\u5f81\u4ee3\u53f7: %s" % (sign or "\u672a\u63d0\u4f9b"))
    lines.append("  \u5206\u5e03: %s" % (dist or "\u672a\u63d0\u4f9b"))
    lines.append("")
    lines.append("  \u4e09\u4e2a\u5feb\u901f\u786e\u8ba4\u6cd5:")
    lines.append("    \u767d\u7eb8\u6cd5: \u767d\u7eb8\u57ab\u5728\u679d\u53f6\u4e0b\u65b9\u8f7b\u62cd\u6216\u6447\u52a8, \u6389\u4e0b\u5c0f\u866b\u5373\u786e\u8ba4\u6709\u6d3b\u4f53")
    lines.append("    \u653e\u5927\u6cd5: 10 \u500d\u653e\u5927\u955c\u770b\u53f6\u80cc, \u79fb\u52a8\u7684\u70b9\u4e3a\u7ea2\u8718\u86db, \u64e6\u5f97\u6389\u7684\u7c89\u5c42\u4e3a\u767d\u7c89\u75c5")
    lines.append("    \u591c\u95f4\u6cd5: \u591c\u95f4\u7528\u624b\u7535\u68c0\u67e5, \u9ecf\u6db2\u75d5\u8ff9\u4e0e\u5543\u98df\u5b54\u6307\u5411\u86de\u8753\u4e0e\u8717\u725b")
    lines.append("")

    lines.append("[\u4e8c] \u6709\u65e0\u6d3b\u4f53\u5206\u6d41")
    lines.append("-" * 68)
    if has_live is True:
        cat = "\u6309\u866b\u5bb3\u65b9\u5411\u6392\u67e5"
        summary["category"] = "\u866b\u5bb3"
        lines.append("  \u5df2\u786e\u8ba4\u6709\u6d3b\u4f53 -> %s" % cat)
        lines.append("    \u4e0b\u4e00\u6b65: \u6309\u5f62\u6001\u7279\u5f81\u5728\u866b\u5bb3\u8868\u91cc\u6bd4\u5bf9\u5019\u9009")
    elif has_live is False:
        cat = "\u6309\u75c5\u5bb3\u6216\u975e\u4fb5\u67d3\u6027\u539f\u56e0\u6392\u67e5"
        summary["category"] = "\u975e\u866b\u5bb3"
        lines.append("  \u672a\u53d1\u73b0\u6d3b\u4f53 -> %s" % cat)
        lines.append("    \u63d0\u9192: \u65e0\u6d3b\u4f53\u5c31\u4e0d\u662f\u866b\u5bb3, \u5904\u7406\u65b9\u5f0f\u4e0e\u866b\u5bb3\u5b8c\u5168\u4e0d\u540c")
        lines.append("    \u4f18\u5148\u6392\u9664: \u7f3a\u7d20\u4e0e\u836f\u5bb3, \u67e5\u8fd1\u671f\u65bd\u80a5\u4e0e\u65bd\u836f\u8bb0\u5f55")
    else:
        summary["category"] = "\u5f85\u786e\u8ba4"
        lines.append("  \u672a\u786e\u8ba4\u6709\u65e0\u6d3b\u4f53, \u5148\u505a\u4e00\u6b21\u786e\u8ba4\u6cd5")
        lines.append("    \u8fd9\u6b65\u8df3\u8fc7\u662f\u5e38\u89c1\u7684\u767d\u82b1\u94b1\u539f\u56e0: \u6ca1\u786e\u8ba4\u6d3b\u4f53\u5c31\u4e0b\u836f")
    lines.append("")

    lines.append("[\u4e09] \u5019\u9009\u6e05\u5355")
    lines.append("-" * 68)
    table = []
    if sign and sign in DISEASES:
        table.append(("\u75c5\u5bb3", DISEASES[sign]))
    if sign and sign in PESTS:
        table.append(("\u866b\u5bb3", PESTS[sign]))
    if not table:
        if part:
            for k, v in PESTS.items():
                if part in v[1]:
                    table.append(("\u866b\u5bb3", v))
                    break
        if not table and part:
            for k, v in DISEASES.items():
                if part in v[1]:
                    table.append(("\u75c5\u5bb3", v))
                    break
    if not table:
        lines.append("  \u672a\u7ed9\u51fa\u6709\u6548\u7684\u5f62\u6001\u7279\u5f81\u4ee3\u53f7, \u65e0\u6cd5\u7ed9\u5019\u9009")
        lines.append("  \u8bf7\u5bf9\u7167\u4e0b\u9762\u7684\u7279\u5f81\u8868\u4eba\u5de5\u6bd4\u5bf9")
        summary["candidates"] = []
    for kind, v in table:
        lines.append("  [%s] %s" % (kind, v[0]))
        lines.append("    \u90e8\u4f4d: %s" % v[1])
        lines.append("    \u5f62\u6001: %s" % v[2])
        lines.append("    \u5206\u5e03: %s" % v[3])
        if kind == "\u866b\u5bb3":
            lines.append("    \u786e\u8ba4\u65b9\u6cd5: %s" % v[4])
            lines.append("    \u6613\u6df7\u6dc6: %s" % v[4])
        else:
            lines.append("    \u6613\u6df7\u6dc6: %s" % v[4])
        summary["candidates"].append(v[0])
    lines.append("")
    lines.append("  \u75c5\u5bb3\u7279\u5f81\u8868:")
    for k in DISEASES:
        v = DISEASES[k]
        lines.append("    %-16s %s" % (k, v[0]))
        lines.append("      \u90e8\u4f4d %s | \u5f62\u6001 %s" % (v[1], v[2]))
        lines.append("      \u5206\u5e03 %s | \u6613\u6df7\u6dc6 %s" % (v[3], v[4]))
    lines.append("")
    lines.append("  \u866b\u5bb3\u7279\u5f81\u8868:")
    for k in PESTS:
        v = PESTS[k]
        lines.append("    %-16s %s" % (k, v[0]))
        lines.append("      \u90e8\u4f4d %s | \u5f62\u6001 %s" % (v[1], v[2]))
        lines.append("      \u786e\u8ba4 %s | \u6613\u6df7\u6dc6 %s" % (v[3], v[4]))
    lines.append("")

    lines.append("[\u56db] \u6613\u6df7\u6dc6\u5bf9\u7167")
    lines.append("-" * 68)
    for a, b, key in CONFUSE:
        lines.append("  %s vs %s: %s" % (a, b, key))
    lines.append("")

    lines.append("[\u4e94] \u591a\u75c7\u72b6\u6c47\u603b")
    lines.append("-" * 68)
    if not signs:
        lines.append("  \u672a\u63d0\u4f9b\u75c7\u72b6\u5217\u8868")
    for s in signs:
        s = s.strip()
        if not s:
            continue
        if s in DISEASES:
            lines.append("  [\u75c5\u5bb3] %s: %s" % (DISEASES[s][0], DISEASES[s][2]))
            summary["candidates"].append(DISEASES[s][0])
        elif s in PESTS:
            lines.append("  [\u866b\u5bb3] %s: %s" % (PESTS[s][0], PESTS[s][2]))
            summary["candidates"].append(PESTS[s][0])
        else:
            lines.append("  [\u672a\u767b\u8bb0] %s -> \u9700\u4eba\u5de5\u6bd4\u5bf9\u7279\u5f81\u8868" % s)
    lines.append("")

    lines.append("[\u516d] \u9632\u6cbb\u65b9\u5f0f\u7c7b\u522b (\u73af\u5883: %s)" % ENVS.get(env, "\u9633\u53f0"))
    lines.append("-" * 68)
    if pets:
        lines.append("  [\u7ea6\u675f] \u5bb6\u4e2d\u6709\u732b\u72ac\u6216\u89c2\u8d4f\u9c7c")
    opts = control_options(env, has_live, pets)
    for name, adv in opts:
        lines.append("  %-12s %s" % (name, adv))
    summary["control_options"] = [o[0] for o in opts]
    lines.append("")
    lines.append("  \u9009\u62e9\u987a\u5e8f: \u7269\u7406 -> \u751f\u7269 -> \u5316\u5b66")
    lines.append("  \u7528\u836f\u8981\u6c42: \u54c1\u79cd\u3001\u7528\u91cf\u3001\u6b21\u6570\u4e0e\u5b89\u5168\u95f4\u9694\u671f\u4ee5\u4ea7\u54c1\u767b\u8bb0\u6807\u7b7e\u548c\u5f53\u5730\u690d\u4fdd\u90e8\u95e8\u8981\u6c42\u4e3a\u51c6")
    lines.append("  \u7981\u9650\u7528\u519c\u836f\u4e00\u5f8b\u4e0d\u4f7f\u7528")
    lines.append("  \u53ef\u98df\u90e8\u4f4d: \u4e25\u683c\u6267\u884c\u5b89\u5168\u95f4\u9694\u671f, \u671f\u5185\u4e0d\u91c7\u6536")
    lines.append("  \u672c\u5de5\u5177\u4e0d\u8f93\u51fa\u4efb\u4f55\u836f\u5242\u540d\u79f0\u3001\u54c1\u724c\u3001\u6d53\u5ea6\u4e0e\u914d\u6bd4")
    lines.append("")

    lines.append("[\u4e03] \u5fc5\u987b\u8f6c\u690d\u4fdd\u673a\u6784\u7684\u60c5\u5f62")
    lines.append("-" * 68)
    for r in REFERRAL:
        lines.append("  + %s" % r)
    summary["referral"] = REFERRAL
    lines.append("")

    lines.append("[\u516b] \u8bb0\u5f55\u4e0e\u590d\u770b")
    lines.append("-" * 68)
    lines.append("  \u53d1\u73b0\u5f53\u5929: \u62cd\u7167\u6574\u4f53\u4e0e\u5c40\u90e8; \u8bb0\u5f55\u90e8\u4f4d\u3001\u5f62\u6001\u3001\u5206\u5e03; \u505a\u4e00\u6b21\u786e\u8ba4\u6cd5")
    lines.append("  \u5904\u7406\u540e 3 \u5929: \u770b\u662f\u5426\u6709\u65b0\u75c5\u6591\u3001\u65b0\u866b\u53e3")
    lines.append("  \u5904\u7406\u540e 7 \u5929: \u590d\u770b; \u8303\u56f4\u6269\u5927\u6216\u51fa\u73b0\u68c0\u75ab\u5acc\u7591\u5219\u8f6c\u690d\u4fdd\u673a\u6784")
    lines.append("  \u65b9\u5411\u5bf9\u4e0d\u5bf9: \u6709\u6548\u7684\u5904\u7406, \u65b0\u75c7\u72b6\u51fa\u73b0\u901f\u5ea6\u4f1a\u660e\u663e\u653e\u7f13")
    lines.append("")
    lines.append("\u514d\u8d23: \u672c\u7ed3\u679c\u4e3a\u8bc6\u522b\u7279\u5f81\u4e0e\u9632\u6cbb\u65b9\u5f0f\u7c7b\u522b\u7684\u5206\u6d41, \u4e0d\u6784\u6210\u75c5\u539f\u5b66\u8bca\u65ad\u6216\u519c\u836f\u4f7f\u7528\u7ed3\u8bba\u3002")
    lines.append("\u514d\u8d23: \u75c5\u866b\u5bb3\u9274\u5b9a\u4ee5\u690d\u4fdd\u673a\u6784\u7ed3\u8bba\u4e3a\u51c6; \u519c\u836f\u4f7f\u7528\u4ee5\u4ea7\u54c1\u767b\u8bb0\u6807\u7b7e\u548c\u5f53\u5730\u690d\u4fdd\u90e8\u95e8\u8981\u6c42\u4e3a\u51c6\u3002")
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
    r.append(("\u75c5\u5bb3\u8868 10 \u6761", len(DISEASES) == 10))
    r.append(("\u866b\u5bb3\u8868 8 \u6761", len(PESTS) == 8))
    r.append(("\u6613\u6df7\u6dc6\u5bf9\u7167 10 \u7ec4", len(CONFUSE) == 10))
    r.append(("\u73af\u5883\u8868 4 \u7c7b", len(ENVS) == 4))
    r.append(("\u767d\u7c89\u75c5\u9709\u5c42\u64e6\u5f97\u6389", "\u64e6\u5f97\u6389" in DISEASES["white_powder"][2]))
    r.append(("\u971c\u9709\u75c5\u9709\u5c42\u64e6\u4e0d\u6389", "\u64e6\u4e0d\u6389" in DISEASES["downy_mildew"][2]))
    r.append(("\u869c\u866b\u6709\u871c\u9732", "\u871c\u9732" in PESTS["aphid"][2]))
    r.append(("\u7ea2\u8718\u86db\u6709\u7ec6\u7f51", "\u7ec6\u7f51" in PESTS["spider_mite"][2]))
    r.append(("\u9752\u866b\u6709\u866b\u7caa\u5224\u636e", "\u866b\u7caa" in PESTS["caterpillar"][3]))
    r.append(("\u86de\u8753\u5224\u636e\u662f\u9ecf\u6db2", "\u9ecf\u6db2" in PESTS["slug"][3]))
    r.append(("\u836f\u5bb3\u4e0e\u65bd\u836f\u65f6\u95f4\u76f8\u5173", "\u65bd\u836f" in DISEASES["herbicide"][3]))
    r.append(("\u7f3a\u7d20\u4e0e\u65bd\u80a5\u8bb0\u5f55\u76f8\u5173", "\u65bd\u80a5" in DISEASES["nutrient"][3]))
    r.append(("\u75c5\u6bd2\u7c7b\u5f52\u4e3a\u7591\u4f3c", "\u7591\u4f3c" in DISEASES["virus_like"][0]))

    r.append(("\u5ba4\u5185\u65e0\u6d3b\u4f53\u8d70\u75c5\u5bb3\u65b9\u5411",
              any(o[0] == "\u975e\u866b\u5bb3\u7c7b" for o in control_options("indoor", False, False))))
    r.append(("\u9633\u53f0\u6709\u6d3b\u4f53\u4e0d\u7528\u5316\u5b66",
              any("\u539f\u5219\u4e0a\u4e0d\u4f7f\u7528" in o[1] for o in control_options("balcony", True, False)
                  if o[0] == "\u5316\u5b66\u9632\u6cbb")))
    r.append(("\u5ead\u9662\u6709\u6d3b\u4f53\u53ef\u7528\u5316\u5b66\u7c7b\u522b",
              any(o[0] == "\u5316\u5b66\u9632\u6cbb" for o in control_options("garden", True, False))))
    r.append(("\u6709\u5ba0\u7269\u7ed9\u51fa\u7ea6\u675f",
              any(o[0] == "\u5ba0\u7269\u7ea6\u675f" for o in control_options("garden", True, True))))
    r.append(("\u65e0\u5ba0\u7269\u4e0d\u7ed9\u7ea6\u675f",
              not any(o[0] == "\u5ba0\u7269\u7ea6\u675f" for o in control_options("garden", True, False))))
    r.append(("\u751f\u4ea7\u573a\u6240\u7ed9\u51fa\u4e0a\u62a5\u53e3\u5f84",
              any(o[0] == "\u4e0a\u62a5\u53e3\u5f84" for o in control_options("field", True, False))))
    r.append(("\u672a\u767b\u8bb0\u73af\u5883\u56de\u843d\u9633\u53f0",
              any(o[0] == "\u5316\u5b66\u9632\u6cbb" for o in control_options("nope", True, False))))
    r.append(("\u8f6c\u690d\u4fdd\u60c5\u5f62 6 \u6761", len(REFERRAL) == 6))

    txt, s = build_report({
        "part": "\u53f6\u80cc", "sign": "spider_mite", "distribution": "\u591a\u682a\u53f6\u80cc",
        "has_live": True, "env": "balcony", "has_pets": True,
        "signs": ["white_powder"],
    })
    r.append(("\u6837\u4f8b\u5019\u9009\u4e3a\u7ea2\u8718\u86db", s["candidates"][0].startswith("\u7ea2\u8718\u86db")))
    r.append(("\u6837\u4f8b\u5f52\u4e3a\u866b\u5bb3", s["category"] == "\u866b\u5bb3"))
    r.append(("\u6837\u4f8b\u73af\u5883\u4e3a\u9633\u53f0", s["env"] == "\u9633\u53f0"))
    r.append(("\u6837\u4f8b\u6709\u5ba0\u7269\u7ea6\u675f", "\u5ba0\u7269\u7ea6\u675f" in s["control_options"]))
    r.append(("\u6837\u4f8b\u8ffd\u52a0\u767d\u7c89\u75c5", "\u767d\u7c89\u75c5" in s["candidates"]))
    r.append(("\u6837\u4f8b\u4e0d\u8f93\u51fa\u836f\u5242", s["pesticide_named"] is False))
    r.append(("\u6837\u4f8b\u6587\u672c\u542b\u786e\u8ba4\u6cd5", "\u767d\u7eb8\u6cd5" in txt))
    r.append(("\u6837\u4f8b\u6587\u672c\u542b\u5b89\u5168\u95f4\u9694\u671f", "\u5b89\u5168\u95f4\u9694\u671f" in txt))

    _, s2 = build_report({})
    r.append(("\u7a7a\u8f93\u5165\u4e0d\u62a5\u9519", s2["category"] == "\u5f85\u786e\u8ba4"))
    r.append(("\u7a7a\u8f93\u5165\u65e0\u5019\u9009", s2["candidates"] == []))
    r.append(("\u7a7a\u8f93\u5165\u8f6c\u690d\u4fdd\u60c5\u5f62\u9f50", len(s2["referral"]) == 6))

    _, s3 = build_report({"has_live": False, "sign": "nutrient",
                          "part": "\u5168\u682a", "env": "field"})
    r.append(("\u65e0\u6d3b\u4f53\u5f52\u4e3a\u975e\u866b\u5bb3", s3["category"] == "\u975e\u866b\u5bb3"))
    r.append(("\u5019\u9009\u542b\u7f3a\u7d20", "\u7f3a\u7d20" in s3["candidates"][0]))

    _, s4 = build_report({"sign": "nope", "signs": ["nope2"]})
    r.append(("\u672a\u767b\u8bb0\u4ee3\u53f7\u65e0\u5019\u9009", s4["candidates"] == []))

    r.append(("BOM \u8f93\u5165\u88ab\u6b63\u786e\u5265\u79bb",
               load_json(_write_bom_sample())["env"] == "garden"))
    r.append(("\u5b57\u7b26\u4e32\u5f62\u5f0f\u7684\u75c7\u72b6\u53ef\u89e3\u6790",
               build_report({"signs": ["aphid"]})[1]["candidates"] == ["\u869c\u866b"]))
    return r


def _write_bom_sample():
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "_selftest_bom_sample.json")
    with io.open(p, "w", encoding="utf-8") as f:
        f.write("\ufeff{\"env\": \"garden\", \"has_live\": true}")
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
        description="\u690d\u7269\u75c5\u866b\u5bb3\u8bc6\u522b\u4e0e\u9632\u6cbb\u7c7b\u522b\u5206\u6d41\u5de5\u5177")
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
    report, summary = build_report(data)
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else report
    out_path = args.out or os.path.join(here, "_last_result.txt")
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write(body)
    print(body)
    print("\u7ed3\u679c\u5df2\u5199\u5165: %s" % out_path)


if __name__ == "__main__":
    main()
