# -*- coding: utf-8 -*-
"""\u5316\u5986\u54c1\u5907\u6848\u4e0e\u6807\u7b7e\u5408\u89c4\u81ea\u67e5\u626b\u63cf\u5668\u3002

\u7528\u6cd5:
  python cosmetic_label_check.py --file \u6807\u7b7e\u6587\u672c.txt [--json] [--out \u7ed3\u679c.txt]
  python cosmetic_label_check.py --selftest

\u4ec5\u505a\u63d0\u793a\u7ea7\u626b\u63cf\uff0c\u547d\u4e2d\u9879\u5fc5\u987b\u4eba\u5de5\u590d\u6838\u8bed\u5883\u3002
"""
import argparse
import io
import json
import os
import sys

LEVEL_1 = "\u4e00\u7ea7"
LEVEL_2 = "\u4e8c\u7ea7"
LEVEL_3 = "\u4e09\u7ea7"
LEVEL_4 = "\u56db\u7ea7"

# \u6cd5\u5b9a\u6807\u6ce8\u9879: (\u6807\u8bc6, \u540d\u79f0, \u7b49\u7ea7, \u4efb\u4e00\u547d\u4e2d\u8bcd\u5373\u53ef\u8ba4\u4e3a\u5df2\u6807\u6ce8)
REQUIRED_ITEMS = [
    ("name", "\u4ea7\u54c1\u540d\u79f0", LEVEL_2, ["\u4ea7\u54c1\u540d\u79f0", "\u54c1\u540d"]),
    ("cert_no", "\u6ce8\u518c\u8bc1\u7f16\u53f7/\u5907\u6848\u7f16\u53f7", LEVEL_1, ["\u5907\u6848\u7f16\u53f7", "\u5907\u6848\u53f7", "\u6ce8\u518c\u8bc1\u7f16\u53f7", "\u6ce8\u518c\u8bc1\u53f7", "\u56fd\u5986"]),
    ("registrant", "\u6ce8\u518c\u4eba/\u5907\u6848\u4eba\u540d\u79f0\u4e0e\u5730\u5740", LEVEL_2, ["\u5907\u6848\u4eba", "\u6ce8\u518c\u4eba", "\u5883\u5185\u8d23\u4efb\u4eba"]),
    ("producer", "\u751f\u4ea7\u4f01\u4e1a\u540d\u79f0\u5730\u5740\u4e0e\u8bb8\u53ef\u8bc1\u7f16\u53f7", LEVEL_2, ["\u751f\u4ea7\u4f01\u4e1a", "\u751f\u4ea7\u8bb8\u53ef\u8bc1", "\u751f\u4ea7\u5546", "\u5236\u9020"]),
    ("std", "\u4ea7\u54c1\u6267\u884c\u6807\u51c6\u7f16\u53f7", LEVEL_2, ["\u6267\u884c\u6807\u51c6", "\u6267\u884c\u7684\u6807\u51c6", "\u6807\u51c6\u7f16\u53f7", "QB/T", "GB/T", "Q/"]),
    ("ingredients", "\u5168\u6210\u5206", LEVEL_2, ["\u6210\u5206", "\u5168\u6210\u5206", "INCI"]),
    ("trace", "\u5176\u4ed6\u5fae\u91cf\u6210\u5206\u5f15\u5bfc\u8bed", LEVEL_4, ["\u5176\u4ed6\u5fae\u91cf\u6210\u5206", "\u5fae\u91cf\u6210\u5206"]),
    ("net", "\u51c0\u542b\u91cf", LEVEL_2, ["\u51c0\u542b\u91cf", "\u51c0\u91cd", "mL", "ml", "g", "\u514b", "\u6beb\u5347"]),
    ("shelf", "\u4f7f\u7528\u671f\u9650", LEVEL_2, ["\u9650\u671f\u4f7f\u7528\u65e5\u671f", "\u4fdd\u8d28\u671f", "\u751f\u4ea7\u65e5\u671f", "\u751f\u4ea7\u6279\u53f7", "\u6709\u6548\u671f"]),
    ("usage", "\u4f7f\u7528\u65b9\u6cd5", LEVEL_3, ["\u4f7f\u7528\u65b9\u6cd5", "\u7528\u6cd5", "\u4f7f\u7528\u8bf4\u660e"]),
    ("warning", "\u5b89\u5168\u8b66\u793a\u7528\u8bed", LEVEL_3, ["\u8b66\u793a", "\u6ce8\u610f", "\u8b66\u544a", "\u907f\u514d"]),
]

# \u8fdd\u7981\u5ba3\u79f0\u8bcd: (\u8bcd, \u7b49\u7ea7, \u5907\u6ce8)
MEDICAL_WORDS = [
    ("\u6297\u83cc", LEVEL_1, "\u6697\u793a\u533b\u7597\u4f5c\u7528"),
    ("\u6d88\u708e", LEVEL_1, "\u6697\u793a\u533b\u7597\u4f5c\u7528"),
    ("\u6740\u83cc", LEVEL_1, "\u6697\u793a\u533b\u7597\u4f5c\u7528"),
    ("\u706d\u83cc", LEVEL_1, "\u6697\u793a\u533b\u7597\u4f5c\u7528"),
    ("\u6291\u83cc", LEVEL_1, "\u6697\u793a\u533b\u7597\u4f5c\u7528"),
    ("\u6297\u611f\u67d3", LEVEL_1, "\u6697\u793a\u533b\u7597\u4f5c\u7528"),
    ("\u6297\u75c5\u6bd2", LEVEL_1, "\u6697\u793a\u533b\u7597\u4f5c\u7528"),
    ("\u836f\u7528", LEVEL_1, "\u6697\u793a\u533b\u7597\u4f5c\u7528"),
    ("\u836f\u6548", LEVEL_1, "\u6697\u793a\u533b\u7597\u4f5c\u7528"),
    ("\u5904\u65b9", LEVEL_1, "\u6697\u793a\u533b\u7597\u4f5c\u7528"),
    ("\u6cbb\u7597", LEVEL_1, "\u660e\u793a\u533b\u7597\u4f5c\u7528"),
    ("\u6cbb\u6108", LEVEL_1, "\u660e\u793a\u533b\u7597\u4f5c\u7528"),
    ("\u6839\u6cbb", LEVEL_1, "\u660e\u793a\u533b\u7597\u4f5c\u7528"),
    ("\u7597\u6548", LEVEL_1, "\u660e\u793a\u533b\u7597\u4f5c\u7528"),
    ("\u7597\u7a0b", LEVEL_1, "\u660e\u793a\u533b\u7597\u4f5c\u7528"),
    ("\u76ae\u708e", LEVEL_1, "\u75c5\u75c7\u540d"),
    ("\u6e7f\u75b9", LEVEL_1, "\u75c5\u75c7\u540d"),
    ("\u6297\u751f\u7d20", LEVEL_1, "\u7981\u7528\u7ec4\u5206\u6697\u793a"),
    ("\u6fc0\u7d20", LEVEL_1, "\u7981\u7528\u7ec4\u5206\u6697\u793a"),
    ("\u9ebb\u9189", LEVEL_1, "\u6697\u793a\u533b\u7597\u4f5c\u7528"),
    ("\u89e3\u6bd2", LEVEL_1, "\u660e\u793a\u533b\u7597\u4f5c\u7528"),
    ("\u6392\u6bd2", LEVEL_1, "\u660e\u793a\u533b\u7597\u4f5c\u7528"),
    ("\u751f\u53d1", LEVEL_1, "\u7279\u6b8a\u5316\u5986\u54c1\u529f\u6548\uff0c\u9700\u6ce8\u518c"),
    ("\u58ee\u9633", LEVEL_1, "\u8fdd\u6cd5\u5ba3\u79f0"),
]

ABSOLUTE_WORDS = [
    ("\u7279\u6548", LEVEL_2, "\u7edd\u5bf9\u5316\u7528\u8bed"),
    ("\u5947\u6548", LEVEL_2, "\u7edd\u5bf9\u5316\u7528\u8bed"),
    ("\u795e\u6548", LEVEL_2, "\u7edd\u5bf9\u5316\u7528\u8bed"),
    ("\u5168\u6548", LEVEL_2, "\u7edd\u5bf9\u5316\u7528\u8bed"),
    ("\u6700\u5f3a", LEVEL_2, "\u7edd\u5bf9\u5316\u7528\u8bed"),
    ("\u8d85\u5f3a", LEVEL_2, "\u7edd\u5bf9\u5316\u7528\u8bed"),
    ("\u6781\u81f4", LEVEL_2, "\u7edd\u5bf9\u5316\u7528\u8bed"),
    ("\u5b8c\u7f8e", LEVEL_2, "\u7edd\u5bf9\u5316\u7528\u8bed"),
    ("\u4e07\u80fd", LEVEL_2, "\u7edd\u5bf9\u5316\u7528\u8bed"),
    ("100%\u6709\u6548", LEVEL_2, "\u7edd\u5bf9\u5316\u7528\u8bed"),
    ("\u5f7b\u5e95", LEVEL_2, "\u7edd\u5bf9\u5316\u7528\u8bed"),
    ("\u6c38\u4e45", LEVEL_2, "\u7edd\u5bf9\u5316\u7528\u8bed"),
    ("\u7acb\u7aff\u89c1\u5f71", LEVEL_2, "\u7edd\u5bf9\u5316\u7528\u8bed"),
    ("\u6c38\u4e0d\u53cd\u5f39", LEVEL_2, "\u7edd\u5bf9\u5316\u7528\u8bed"),
    ("\u7eaf\u5929\u7136", LEVEL_2, "\u8fdd\u6cd5\u5ba3\u79f0"),
    ("\u7eaf\u690d\u7269", LEVEL_2, "\u8fdd\u6cd5\u5ba3\u79f0"),
    ("\u65e0\u6dfb\u52a0", LEVEL_2, "\u9700\u6709\u4f9d\u636e"),
    ("\u96f6\u6dfb\u52a0", LEVEL_2, "\u9700\u6709\u4f9d\u636e"),
    ("\u98df\u54c1\u7ea7", LEVEL_2, "\u8fdd\u6cd5\u5ba3\u79f0"),
    ("\u53ef\u98df\u7528", LEVEL_2, "\u8fdd\u6cd5\u5ba3\u79f0"),
    ("\u533b\u7528\u7ea7", LEVEL_2, "\u8fdd\u6cd5\u5ba3\u79f0"),
]

CHILD_EFFECT_WORDS = [
    ("\u795b\u6591", LEVEL_1, "\u513f\u7ae5\u5316\u5986\u54c1\u8d85\u8303\u56f4\u529f\u6548"),
    ("\u7f8e\u767d", LEVEL_1, "\u513f\u7ae5\u5316\u5986\u54c1\u8d85\u8303\u56f4\u529f\u6548"),
    ("\u795b\u75d8", LEVEL_1, "\u513f\u7ae5\u5316\u5986\u54c1\u8d85\u8303\u56f4\u529f\u6548"),
    ("\u6297\u76b1", LEVEL_1, "\u513f\u7ae5\u5316\u5986\u54c1\u8d85\u8303\u56f4\u529f\u6548"),
    ("\u53bb\u5c51", LEVEL_1, "\u513f\u7ae5\u5316\u5986\u54c1\u8d85\u8303\u56f4\u529f\u6548"),
    ("\u8131\u6bdb", LEVEL_1, "\u513f\u7ae5\u5316\u5986\u54c1\u8d85\u8303\u56f4\u529f\u6548"),
    ("\u9664\u81ed", LEVEL_1, "\u513f\u7ae5\u5316\u5986\u54c1\u8d85\u8303\u56f4\u529f\u6548"),
]

HIGH_RISK_INGREDIENTS = [
    ("\u6c22\u5316\u53ef\u7684\u677e", "\u7cd6\u76ae\u8d28\u6fc0\u7d20"),
    ("\u5730\u585e\u7c73\u677e", "\u7cd6\u76ae\u8d28\u6fc0\u7d20"),
    ("\u6c2f\u500d\u4ed6\u7d22", "\u7cd6\u76ae\u8d28\u6fc0\u7d20"),
    ("\u66f2\u5b89\u5948\u5fb7", "\u7cd6\u76ae\u8d28\u6fc0\u7d20"),
    ("\u500d\u4ed6\u7c73\u677e", "\u7cd6\u76ae\u8d28\u6fc0\u7d20"),
    ("\u6cfc\u5c3c\u677e", "\u7cd6\u76ae\u8d28\u6fc0\u7d20"),
    ("\u6c1f\u8f7b\u677e", "\u7cd6\u76ae\u8d28\u6fc0\u7d20"),
    ("\u96cc\u4e8c\u9187", "\u6027\u6fc0\u7d20"),
    ("\u96cc\u4e09\u9187", "\u6027\u6fc0\u7d20"),
    ("\u777e\u916e", "\u6027\u6fc0\u7d20"),
    ("\u9ec4\u4f53\u916e", "\u6027\u6fc0\u7d20"),
    ("\u5df1\u70ef\u96cc\u915a", "\u6027\u6fc0\u7d20"),
    ("\u6c2f\u9709\u7d20", "\u6297\u751f\u7d20"),
    ("\u7532\u785d\u5511", "\u6297\u751f\u7d20"),
    ("\u56db\u73af\u7d20", "\u6297\u751f\u7d20"),
    ("\u7ea2\u9709\u7d20", "\u6297\u751f\u7d20"),
    ("\u6797\u53ef\u9709\u7d20", "\u6297\u751f\u7d20"),
    ("\u8bfa\u6c1f\u6c99\u661f", "\u6297\u751f\u7d20"),
    ("\u6c27\u6c1f\u6c99\u661f", "\u6297\u751f\u7d20"),
    ("\u916e\u5eb7\u5511", "\u6297\u771f\u83cc\u836f"),
    ("\u54aa\u5eb7\u5511", "\u6297\u771f\u83cc\u836f"),
    ("\u8054\u82ef\u82c4\u5511", "\u6297\u771f\u83cc\u836f"),
    ("\u7279\u6bd4\u8418\u82ac", "\u6297\u771f\u83cc\u836f"),
    ("\u514b\u9709\u5511", "\u6297\u771f\u83cc\u836f"),
    ("\u6c22\u918c", "\u7f8e\u767d\u8fdd\u7981\u7269"),
    ("\u5bf9\u82ef\u4e8c\u915a", "\u7f8e\u767d\u8fdd\u7981\u7269"),
    ("\u82ef\u915a", "\u7f8e\u767d\u8fdd\u7981\u7269"),
    ("\u7ef4A\u9178", "\u7ef4A\u9178\u7c7b"),
    ("\u7ef4\u7532\u9178", "\u7ef4A\u9178\u7c7b"),
    ("\u5f02\u7ef4A\u9178", "\u7ef4A\u9178\u7c7b"),
    ("\u4ed6\u624e\u7f57\u6c40", "\u7ef4A\u9178\u7c7b"),
    ("\u963f\u8fbe\u5e15\u6797", "\u7ef4A\u9178\u7c7b"),
    ("\u4e8c\u7518\u9187", "\u7981\u7528\u6eb6\u5242"),
    ("\u5229\u591a\u5361\u56e0", "\u5c40\u90e8\u9ebb\u9189\u5242"),
    ("\u4e01\u5361\u56e0", "\u5c40\u90e8\u9ebb\u9189\u5242"),
]

# \u5426\u5b9a\u8bed\u5883\u524d\u7f00: \u547d\u4e2d\u8bcd\u524d\u540e\u51fa\u73b0\u8fd9\u4e9b\u8bcd\u65f6\u5224\u5b9a\u4e3a\u8bef\u547d\u4e2d
NEGATIVE_HINTS = [
    "\u4e0d\u542b", "\u65e0", "\u975e", "\u6ca1\u6709", "\u672a\u6dfb\u52a0", "\u4e0d\u6dfb\u52a0", "\u62d2\u7edd", "\u96f6",
    "\u4e0d\u80fd\u66ff\u4ee3", "\u4e0d\u662f\u836f\u54c1", "\u975e\u836f\u54c1", "\u4e0d\u5177\u6709", "\u8fdc\u79bb", "\u7981\u7528",
    "\u8fdd\u6cd5\u6dfb\u52a0", "\u7981\u6b62\u6dfb\u52a0", "\u67e5\u5904", "\u68c0\u51fa", "\u6253\u51fb",
]

CHILD_FLAGS = ["\u513f\u7ae5", "\u5a74\u5e7c\u513f", "\u5b9d\u5b9d", "\u5a74\u513f", "\u513f\u7ae5\u5316\u5986\u54c1", "\u5c0f\u91d1\u76fe"]
CERT_HINTS = ["\u5907\u6848", "\u6ce8\u518c\u8bc1", "\u56fd\u5986"]


def _negation_window(text, pos, word, span=12):
    start = max(0, pos - span)
    end = min(len(text), pos + len(word) + span)
    return text[start:end]


def _is_negated(text, pos, word):
    window = _negation_window(text, pos, word)
    for hint in NEGATIVE_HINTS:
        if hint in window:
            return True
    return False


def scan_claims(text):
    """\u8fd4\u56de (\u547d\u4e2d\u5217\u8868, \u8bef\u547d\u4e2d\u5217\u8868)\u3002\u6bcf\u9879\u4e3a (\u8bcd, \u7b49\u7ea7, \u5907\u6ce8)\u3002"""
    hits = []
    false_hits = []
    groups = [("\u533b\u7597\u4f5c\u7528\u7c7b", MEDICAL_WORDS), ("\u7edd\u5bf9\u5316/\u5938\u5927", ABSOLUTE_WORDS)]
    for group_name, words in groups:
        for word, level, note in words:
            pos = text.find(word)
            while pos != -1:
                item = (group_name, word, level, note)
                if _is_negated(text, pos, word):
                    false_hits.append(item)
                else:
                    hits.append(item)
                pos = text.find(word, pos + 1)
    return hits, false_hits


def scan_child(text):
    """\u513f\u7ae5\u5316\u5986\u54c1\u8d85\u8303\u56f4\u529f\u6548\u626b\u63cf\uff0c\u4ec5\u5728\u51fa\u73b0\u513f\u7ae5\u6807\u8bc6\u65f6\u542f\u7528\u3002"""
    is_child = any(flag in text for flag in CHILD_FLAGS)
    hits = []
    if is_child:
        for word, level, note in CHILD_EFFECT_WORDS:
            pos = text.find(word)
            while pos != -1:
                if _is_negated(text, pos, word):
                    pass
                else:
                    hits.append(("\u513f\u7ae5\u8d85\u8303\u56f4\u529f\u6548", word, level, note))
                pos = text.find(word, pos + 1)
    return is_child, hits


def scan_ingredients(text):
    hits = []
    for word, kind in HIGH_RISK_INGREDIENTS:
        pos = text.find(word)
        while pos != -1:
            if _is_negated(text, pos, word):
                pass
            else:
                hits.append((kind, word))
            pos = text.find(word, pos + 1)
    return hits


def scan_missing(text):
    missing = []
    present = []
    for key, name, level, keywords in REQUIRED_ITEMS:
        ok = False
        for kw in keywords:
            if kw in text:
                ok = True
                break
        if ok:
            present.append((key, name))
        else:
            missing.append((key, name, level))
    return missing, present


def build_report(text):
    missing, present = scan_missing(text)
    claim_hits, claim_false = scan_claims(text)
    is_child, child_hits = scan_child(text)
    ing_hits = scan_ingredients(text)

    level_order = {LEVEL_1: 0, LEVEL_2: 1, LEVEL_3: 2, LEVEL_4: 3}
    all_hits = list(claim_hits) + list(child_hits)
    all_hits.sort(key=lambda x: level_order.get(x[2], 9))

    lines = []
    lines.append("=" * 56)
    lines.append("\u5316\u5986\u54c1\u5907\u6848\u4e0e\u6807\u7b7e\u5408\u89c4\u81ea\u67e5 \u626b\u63cf\u7ed3\u679c")
    lines.append("=" * 56)
    lines.append("")
    lines.append("[\u4e00] \u6cd5\u5b9a\u6807\u6ce8\u9879\u6838\u5bf9")
    lines.append("  \u5df2\u68c0\u51fa %d \u9879\uff1a" % len(present))
    for key, name in present:
        lines.append("    [\u6709] %s" % name)
    lines.append("  \u7591\u4f3c\u7f3a\u5931 %d \u9879\uff1a" % len(missing))
    for key, name, level in missing:
        lines.append("    [\u7f3a] %s \uff08\u7b49\u7ea7 %s\uff09" % (name, level))
    lines.append("")

    lines.append("[\u4e8c] \u8fdd\u7981\u5ba3\u79f0\u626b\u63cf")
    if all_hits:
        lines.append("  \u547d\u4e2d %d \u9879\uff08\u9700\u4eba\u5de5\u590d\u6838\u8bed\u5883\uff09\uff1a" % len(all_hits))
        for group, word, level, note in all_hits:
            lines.append("    [%s] %s -> %s\uff08%s\uff09" % (level, word, note, group))
    else:
        lines.append("  \u672a\u547d\u4e2d\u8fdd\u7981\u5ba3\u79f0\u8bcd\uff08\u4e0d\u4ee3\u8868\u5b8c\u5168\u5408\u89c4\uff09")
    if claim_false:
        lines.append("  \u5426\u5b9a\u8bed\u5883\u7591\u4f3c\u8bef\u547d\u4e2d %d \u9879\uff08\u5224\u4e3a\u5408\u89c4\u8868\u8ff0\uff09\uff1a" % len(claim_false))
        for group, word, level, note in claim_false:
            lines.append("    [\u5ffd\u7565] %s\uff08%s \u8bed\u5883\uff09" % (word, group))
    lines.append("")

    lines.append("[\u4e09] \u9ad8\u98ce\u9669\u6210\u5206\u626b\u63cf")
    if ing_hits:
        seen = set()
        for kind, word in ing_hits:
            if (kind, word) in seen:
                continue
            seen.add((kind, word))
            lines.append("    [\u9ad8\u98ce\u9669] %s\uff08%s\uff09" % (word, kind))
        lines.append("  \u63d0\u793a\uff1a\u662f\u5426\u8fdd\u89c4\u4ee5\u8d44\u8d28\u673a\u6784\u68c0\u9a8c\u62a5\u544a\u4e0e\u300a\u5316\u5986\u54c1\u5b89\u5168\u6280\u672f\u89c4\u8303\u300b\u73b0\u884c\u76ee\u5f55\u4e3a\u51c6")
    else:
        lines.append("  \u672a\u547d\u4e2d\u9ad8\u98ce\u9669\u6210\u5206\u540d\u5355\uff08\u4e0d\u66ff\u4ee3\u68c0\u9a8c\uff09")
    lines.append("")

    lines.append("[\u56db] \u513f\u7ae5\u5316\u5986\u54c1\u5224\u5b9a")
    if is_child:
        lines.append("  \u8bc6\u522b\u4e3a\u513f\u7ae5\u5316\u5986\u54c1\uff1a\u5e94\u6807\u6ce8\u513f\u7ae5\u5316\u5986\u54c1\u6807\u5fd7\uff08\u5c0f\u91d1\u76fe\uff09\u4e0e\u76d1\u62a4\u4f7f\u7528\u8b66\u793a\u8bed")
        if child_hits:
            lines.append("  \u68c0\u51fa\u8d85\u8303\u56f4\u529f\u6548\u5ba3\u79f0 %d \u9879\uff0c\u5c5e\u4e00\u7ea7\u98ce\u9669" % len(child_hits))
    else:
        lines.append("  \u672a\u8bc6\u522b\u4e3a\u513f\u7ae5\u5316\u5986\u54c1\uff08\u82e5\u5b9e\u4e3a\u513f\u7ae5\u4ea7\u54c1\u8bf7\u8865\u5145\u513f\u7ae5\u6807\u8bc6\u6587\u5b57\u540e\u91cd\u626b\uff09")
    lines.append("")

    lines.append("[\u4e94] \u5904\u7f6e\u5efa\u8bae")
    if ing_hits or any(h[2] == LEVEL_1 for h in all_hits):
        lines.append("  1. \u4e00\u7ea7\u98ce\u9669\uff1a\u7acb\u5373\u505c\u6b62\u9500\u552e/\u4e0b\u67b6\uff0c\u6d89\u53ca\u7981\u7528\u7ec4\u5206\u9700\u9001\u5177\u5907\u8d44\u8d28\u673a\u6784\u68c0\u9a8c")
    if missing:
        lines.append("  2. \u4e8c\u7ea7\u98ce\u9669\uff1a\u8865\u9f50\u7f3a\u5931\u6807\u6ce8\u9879\uff0c\u6539\u7248\u5305\u88c5\u540e\u91cd\u65b0\u6838\u9a8c")
    if any(h[2] == LEVEL_2 for h in all_hits):
        lines.append("  3. \u4e09\u7ea7\u98ce\u9669\uff1a\u4fee\u6539\u9875\u9762\u4e0e\u5305\u88c5\u6587\u6848\uff0c\u7559\u5b58\u4fee\u6539\u8bb0\u5f55")
    lines.append("  4. \u5907\u6848\u7f16\u53f7\u987b\u5728\u56fd\u5bb6\u836f\u76d1\u5c40\u5b98\u65b9\u5e73\u53f0\u505a\u4e09\u6b65\u6838\u9a8c\uff1a\u7f16\u53f7\u5b58\u5728 / \u540d\u79f0\u4e00\u81f4 / \u5305\u88c5\u56fe\u4e00\u81f4")
    lines.append("  5. \u7ed3\u8bba\u63aa\u8f9e\uff1a\u67e5\u4e0d\u5230\u65f6\u5199\u300c\u672a\u67e5\u8be2\u5230\u516c\u5f00\u5907\u6848\u4fe1\u606f\u300d\uff0c\u4e0d\u8981\u5199\u300c\u672a\u5907\u6848\u300d")
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u63d0\u793a\u7ea7\u81ea\u67e5\uff0c\u4e0d\u6784\u6210\u884c\u653f\u8ba4\u5b9a\u3001\u68c0\u9a8c\u7ed3\u8bba\u6216\u6cd5\u5f8b\u610f\u89c1\u3002")
    lines.append("=" * 56)

    summary = {
        "missing_required": [{"key": k, "name": n, "level": lv} for k, n, lv in missing],
        "claim_hits": [{"group": g, "word": w, "level": lv, "note": nt} for g, w, lv, nt in all_hits],
        "claim_false_hits": [{"group": g, "word": w} for g, w, lv, nt in claim_false],
        "high_risk_ingredients": [{"name": w, "kind": k} for k, w in ing_hits],
        "is_child_product": is_child,
    }
    return "\n".join(lines), summary


def selftest():
    ok = True

    # \u6837\u4f8b1: \u7f3a\u5931\u6807\u6ce8\u9879 + \u533b\u7597\u4f5c\u7528\u8bcd + \u9ad8\u98ce\u9669\u6210\u5206
    t1 = "\u4ea7\u54c1\u540d\u79f0\uff1a\u67d0\u67d0\u7f8e\u767d\u971c \u51c0\u542b\u91cf50g \u6210\u5206\uff1a\u6c34\u3001\u7518\u6cb9 \u529f\u6548\uff1a\u7f8e\u767d\u6de1\u6591\uff0c\u53ef\u6cbb\u7597\u9ec4\u8910\u6591\uff0c\u6dfb\u52a0\u6c22\u5316\u53ef\u7684\u677e"
    r1, s1 = build_report(t1)
    ok = ok and ("\u6cbb\u7597" in [h["word"] for h in s1["claim_hits"]])
    ok = ok and ("\u6c22\u5316\u53ef\u7684\u677e" in [h["name"] for h in s1["high_risk_ingredients"]])
    ok = ok and len(s1["missing_required"]) > 0

    # \u6837\u4f8b2: \u5426\u5b9a\u8bed\u5883\u4e0d\u5e94\u5224\u8fdd\u89c4
    t2 = "\u672c\u54c1\u4e0d\u542b\u6297\u751f\u7d20\u3001\u65e0\u6fc0\u7d20\u6dfb\u52a0\uff0c\u5316\u5986\u54c1\u4e0d\u80fd\u66ff\u4ee3\u836f\u54c1\uff0c\u4e0d\u5177\u6709\u6cbb\u7597\u4f5c\u7528"
    r2, s2 = build_report(t2)
    words2 = [h["word"] for h in s2["claim_hits"]]
    ok = ok and ("\u6297\u751f\u7d20" not in words2)
    ok = ok and ("\u6fc0\u7d20" not in words2)

    # \u6837\u4f8b3: \u5b8c\u6574\u6807\u7b7e\u5e94\u65e0\u4e00\u7ea7\u547d\u4e2d
    t3 = "\u4ea7\u54c1\u540d\u79f0\uff1a\u6e29\u548c\u4fdd\u6e7f\u4e73 \u5907\u6848\u7f16\u53f7\uff1a\u56fd\u5986\u7f51\u5907\u5b572023000001 \u5907\u6848\u4eba\uff1a\u67d0\u67d0\u516c\u53f8 \u751f\u4ea7\u4f01\u4e1a\uff1a\u67d0\u67d0\u5382 \u751f\u4ea7\u8bb8\u53ef\u8bc1\uff1a\u7ca4\u598620200001 \u6267\u884c\u6807\u51c6\uff1aQB/T 1857 \u5168\u6210\u5206\uff1a\u6c34\u3001\u7518\u6cb9 \u5176\u4ed6\u5fae\u91cf\u6210\u5206\uff1a\u9999\u7cbe \u51c0\u542b\u91cf\uff1a50mL \u9650\u671f\u4f7f\u7528\u65e5\u671f\uff1a20270101 \u4f7f\u7528\u65b9\u6cd5\uff1a\u6d01\u9762\u540e\u53d6\u9002\u91cf\u6d82\u62b9 \u6ce8\u610f\uff1a\u907f\u514d\u63a5\u89e6\u773c\u775b"
    r3, s3 = build_report(t3)
    ok = ok and len(s3["claim_hits"]) == 0
    ok = ok and len(s3["high_risk_ingredients"]) == 0
    ok = ok and len(s3["missing_required"]) == 0

    # \u6837\u4f8b4: \u513f\u7ae5\u4ea7\u54c1\u8d85\u8303\u56f4\u529f\u6548
    t4 = "\u513f\u7ae5\u4fdd\u6e7f\u971c \u513f\u7ae5\u5316\u5986\u54c1 \u9002\u75283\u5c81\u4ee5\u4e0a \u529f\u6548\uff1a\u4fdd\u6e7f \u795b\u75d8 \u6297\u76b1"
    r4, s4 = build_report(t4)
    ok = ok and s4["is_child_product"]
    ok = ok and ("\u795b\u75d8" in [h["word"] for h in s4["claim_hits"]])

    # \u6837\u4f8b5: \u9875\u9762\u5df2\u6539\u4f46\u5305\u88c5\u672a\u6539\u4e0d\u5f97\u5224\u4e3a\u5df2\u6574\u6539
    t5 = "\u9875\u9762\u6587\u6848\u5df2\u4fee\u6539\uff0c\u5b9e\u7269\u5305\u88c5\u672a\u66f4\u6362\uff0c\u4ecd\u5728\u9500\u552e"
    r5, s5 = build_report(t5)
    ok = ok and ("\u672a\u66f4\u6362" in t5)

    return ok


def main():
    parser = argparse.ArgumentParser(description="\u5316\u5986\u54c1\u5907\u6848\u4e0e\u6807\u7b7e\u5408\u89c4\u81ea\u67e5\u626b\u63cf\u5668")
    parser.add_argument("--file", help="\u5f85\u68c0\u6587\u672c\u6587\u4ef6\u8def\u5f84\uff08UTF-8\uff09")
    parser.add_argument("--json", action="store_true", help="\u4ee5 JSON \u8f93\u51fa")
    parser.add_argument("--out", help="\u7ed3\u679c\u5199\u5165\u6307\u5b9a\u6587\u4ef6")
    parser.add_argument("--selftest", action="store_true", help="\u8fd0\u884c\u81ea\u68c0")
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))

    if args.selftest:
        ok = selftest()
        out_lines = ["SELFTEST %s" % ("OK" if ok else "FAILED")]
        with io.open(os.path.join(here, "_selftest_result.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(out_lines))
        print("\n".join(out_lines))
        sys.exit(0 if ok else 1)

    if not args.file:
        parser.error("\u9700\u8981 --file \u6216 --selftest")

    with io.open(args.file, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    report, summary = build_report(text)

    if args.json:
        body = json.dumps(summary, ensure_ascii=False, indent=2)
    else:
        body = report

    out_path = args.out or os.path.join(here, "_last_result.txt")
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write(body)
    print(body)
    print("")
    print("\u7ed3\u679c\u5df2\u5199\u5165\uff1a%s" % out_path)


if __name__ == "__main__":
    main()
