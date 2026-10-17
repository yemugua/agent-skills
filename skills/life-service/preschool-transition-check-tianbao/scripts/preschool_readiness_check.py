# -*- coding: utf-8 -*-
"""\u5e7c\u5c0f\u8854\u63a5\u516b\u5927\u80fd\u529b\u6838\u67e5\u4e0e\u5012\u6392\u5efa\u8bae\u751f\u6210\u5de5\u5177\u3002

\u7528\u6cd5:
  python preschool_readiness_check.py --file case.json [--focus selfcare] [--json]
  python preschool_readiness_check.py --selftest

\u672c\u5de5\u5177\u4e0d\u9884\u6d4b\u5165\u5b66\u6210\u7ee9\uff0c\u4e0d\u505a\u53d1\u80b2\u6216\u5b66\u4e60\u80fd\u529b\u8bca\u65ad\uff0c\u4e0d\u6307\u5b9a\u6559\u6750\u4e0e\u8bfe\u7a0b\u4f53\u7cfb\u3002
"""
import argparse
import io
import json
import os
import sys

DIMENSIONS = [
    ("selfcare", "\u751f\u6d3b\u81ea\u7406", "\u81ea\u8bc4", "\u81ea\u5df1\u5403\u996d\u7a7f\u8863\u4e0a\u5395\u6240\u3001\u6574\u7406\u4e66\u5305\u7269\u54c1"),
    ("time", "\u65f6\u95f4\u7ba1\u7406", "\u81ea\u8bc4", "\u4f5c\u606f\u56fa\u5b9a\u3001\u80fd\u5148\u505a\u4e00\u4ef6\u4e8b\u518d\u505a\u4e0b\u4e00\u4ef6\u3001\u73a9\u5b8c\u77e5\u9053\u6536\u5c3e"),
    ("focus", "\u4e13\u6ce8\u529b", "\u81ea\u8bc4", "\u80fd\u4e13\u6ce8 15-20 \u5206\u949f\uff0c\u88ab\u6253\u65ad\u540e\u80fd\u56de\u5230\u539f\u4efb\u52a1"),
    ("rule", "\u89c4\u5219\u610f\u8bc6", "\u81ea\u8bc4", "\u4e3e\u624b\u53d1\u8a00\u3001\u80fd\u8f6e\u6d41\u3001\u542c\u5b8c\u4efb\u52a1\u80fd\u5f00\u59cb\u505a"),
    ("reading", "\u524d\u9605\u8bfb", "\u524d\u9605\u8bfb", "\u5bf9\u6545\u4e8b\u6709\u5174\u8da3\u3001\u4f1a\u7ffb\u9875\u3001\u80fd\u7528\u81ea\u5df1\u7684\u8bdd\u8bb2\u8ff0"),
    ("writing", "\u524d\u4e66\u5199", "\u524d\u4e66\u5199", "\u63e1\u59ff\u57fa\u672c\u6b63\u786e\u3001\u80fd\u63a7\u7ebf\u6d82\u9e26\u3001\u624b\u90e8\u529b\u91cf\u591f\u7528"),
    ("express", "\u8868\u8fbe", "\u81ea\u8bc4", "\u80fd\u8bf4\u5b8c\u6574\u77ed\u53e5\u3001\u542c\u61c2\u5e76\u590d\u8ff0\u6307\u4ee4\u3001\u80fd\u7528\u8bed\u8a00\u62d2\u7edd"),
    ("motor", "\u8fd0\u52a8", "\u81ea\u8bc4", "\u80fd\u53cc\u811a\u8df3\u3001\u80fd\u62cd\u7403\u3001\u6bcf\u5929\u6709\u6237\u5916\u6d3b\u52a8"),
]

PRIORITY_ORDER = ["selfcare", "time", "focus", "rule", "express", "reading", "writing", "motor"]

RED_FLAGS = [
    "no_selfcare",
    "language_delay",
    "attention_impulse",
    "fine_motor_delay",
    "vision_hearing_suspect",
    "diagnosed_disorder",
    "failed_screening",
]

RED_FLAG_TEXT = {
    "no_selfcare": "\u5230\u5165\u5b66\u5e74\u9f84\u4ecd\u65e0\u6cd5\u5b8c\u6210\u57fa\u672c\u81ea\u7406\uff0c\u4e0d\u4f1a\u81ea\u5df1\u5403\u996d\u7a7f\u8863\u559d\u6c34\u3001\u65e0\u6cd5\u8868\u8fbe\u5982\u5395\u9700\u6c42",
    "language_delay": "\u8bed\u8a00\u8868\u8fbe\u660e\u663e\u843d\u540e\uff0c\u4e0d\u80fd\u8bf4\u5b8c\u6574\u77ed\u53e5\u3001\u542c\u4e0d\u61c2\u7b80\u5355\u6307\u4ee4",
    "attention_impulse": "\u6ce8\u610f\u4e0e\u51b2\u52a8\u8868\u73b0\u6301\u7eed\u5b58\u5728\uff0c\u591a\u6570\u573a\u5408\u65e0\u6cd5\u5b89\u9759\u542c\u6307\u4ee4\u3001\u7ecf\u5e38\u6253\u65ad\u4ed6\u4eba",
    "fine_motor_delay": "\u7cbe\u7ec6\u52a8\u4f5c\u660e\u663e\u56f0\u96be\uff0c\u4e0d\u4f1a\u7528\u526a\u5200\u3001\u63e1\u59ff\u5f02\u5e38\u3001\u4e0d\u4f1a\u4e32\u73e0",
    "vision_hearing_suspect": "\u53cd\u590d\u4e2d\u8033\u708e\u53f2\u3001\u7591\u4f3c\u542c\u5f31\u3001\u770b\u4e1c\u897f\u772f\u773c\u6216\u6b6a\u5934",
    "diagnosed_disorder": "\u5df2\u786e\u8bca\u53d1\u80b2\u969c\u788d\u3001\u5b66\u4e60\u969c\u788d\u6216\u5b64\u72ec\u75c7\u8c31\u7cfb",
    "failed_screening": "\u542c\u529b\u89c6\u529b\u7b5b\u67e5\u672a\u901a\u8fc7\u6216\u5b66\u6821\u4f53\u68c0\u5f02\u5e38",
}

REFERRAL = {
    "no_selfcare": "\u513f\u79d1\u6216\u513f\u7ae5\u4fdd\u5065\u79d1\u8bc4\u4f30",
    "language_delay": "\u513f\u7ae5\u4fdd\u5065\u79d1\u6216\u8a00\u8bed\u6cbb\u7597\u79d1\u8bc4\u4f30",
    "attention_impulse": "\u513f\u79d1\u6216\u513f\u7ae5\u5fc3\u7406\u4e13\u4e1a\u8bc4\u4f30",
    "fine_motor_delay": "\u4f5c\u4e1a\u6cbb\u7597\u6216\u513f\u79d1\u8bc4\u4f30",
    "vision_hearing_suspect": "\u5148\u5230\u8033\u9f3b\u5589\u79d1\u548c\u773c\u79d1\u6392\u67e5",
    "diagnosed_disorder": "\u7531\u4e13\u4e1a\u673a\u6784\u5236\u5b9a\u8854\u63a5\u65b9\u6848",
    "failed_screening": "\u5148\u590d\u67e5\u518d\u8c08\u8854\u63a5",
}

PHASES = [
    (12, 9, "\u7b2c\u4e00\u9636\u6bb5", "\u81ea\u7406\u653b\u575a\uff1a\u5403\u996d\u3001\u7a7f\u8863\u3001\u5982\u5395\u3001\u6574\u7406\u4e66\u5305",
     "\u72ec\u7acb\u5b8c\u6210\u7684\u81ea\u7406\u73af\u8282\u6570\u662f\u5426\u5728\u589e\u52a0"),
    (8, 5, "\u7b2c\u4e8c\u9636\u6bb5", "\u4e13\u6ce8\u4e0e\u65f6\u95f4\uff1a\u4f5c\u606f\u56fa\u5b9a\u3001\u4efb\u52a1\u987a\u5e8f\u3001\u9650\u65f6\u6d3b\u52a8",
     "\u4e13\u6ce8\u65f6\u957f\u6bcf\u5468\u589e\u52a0 2 \u5206\u949f\u4e3a\u8fbe\u6807"),
    (4, 2, "\u7b2c\u4e09\u9636\u6bb5", "\u89c4\u5219\u4e0e\u524d\u9605\u8bfb\u524d\u4e66\u5199\uff1a\u5bb6\u5ead\u4f1a\u8bae\u3001\u5171\u8bfb\u3001\u7c97\u6746\u63a7\u7b14",
     "\u80fd\u5426\u590d\u8ff0\u5e76\u6267\u884c 2 \u6761\u5bb6\u91cc\u89c4\u5219"),
    (1, 1, "\u7b2c\u56db\u9636\u6bb5", "\u8868\u8fbe\u4e0e\u9002\u5e94\u9884\u6f14\uff1a\u6a21\u62df\u4e0a\u5b66\u65e5\u3001\u719f\u6089\u6821\u56ed\u6d41\u7a0b",
     "\u80fd\u5426\u8bf4\u51fa\u6211\u8981\u4e0a\u5395\u6240\u3001\u6211\u4e0d\u8212\u670d"),
]

NORMAL_FLUCTUATION = [
    "\u5165\u5b66\u540e\u4e00\u6bb5\u65f6\u95f4\u4e0d\u8bf4\u8bdd\u6216\u6c89\u9ed8",
    "\u8bf4\u60f3\u4e0a\u5395\u6240\u5374\u4e0d\u613f\u610f\u53bb",
    "\u4f5c\u4e1a\u8d28\u91cf\u660e\u663e\u4f4e\u4e8e\u5b66\u524d\u6c34\u5e73",
    "\u8bf4\u4e0d\u60f3\u4e0a\u5b66\u4f46\u539f\u56e0\u8bf4\u4e0d\u6e05",
    "\u52a8\u4f5c\u53d8\u6162\u505a\u4e8b\u6ca1\u5934\u7eea",
]

NEED_ATTENTION = [
    "6 \u5468\u540e\u4ecd\u51e0\u4e4e\u4e0d\u4e0e\u540c\u4f34\u4ea4\u5f80\u3001\u4e0d\u53c2\u52a0\u96c6\u4f53\u6d3b\u52a8",
    "\u53cd\u590d\u8179\u75db\u5934\u75db\u3001\u5c3f\u5e8a\u590d\u53d1\u7b49\u8eaf\u4f53\u5316\u8868\u73b0",
    "\u7761\u7720\u969c\u788d\u660e\u663e\u52a0\u91cd\u3001\u591c\u60ca\u9891\u7e41",
    "\u6301\u7eed\u8bf4\u809a\u5b50\u75bc\u4f46\u67e5\u4e0d\u51fa\u539f\u56e0",
    "\u51fa\u73b0\u653b\u51fb\u884c\u4e3a\u6216\u4e25\u91cd\u9000\u7f29",
]

MYTHS = [
    "\u8bef\u533a\uff1a\u63d0\u524d\u5b66\u4e00\u5e74\u7ea7\u8bfe\u672c\u5f53\u4e3b\u8981\u51c6\u5907\u3002\u77ed\u671f\u9886\u5148\u4f46\u81ea\u7406\u4e0e\u89c4\u5219\u843d\u540e\uff0c\u4e8c\u5e74\u7ea7\u5206\u5316\u66f4\u660e\u663e\u3002",
    "\u8bef\u533a\uff1a\u7528\u6284\u5b57\u91cf\u8861\u91cf\u524d\u4e66\u5199\u3002\u524d\u4e66\u5199\u662f\u63e1\u59ff\u3001\u529b\u91cf\u3001\u4e13\u6ce8\u4e0e\u8868\u8fbe\u3002",
    "\u8bef\u533a\uff1a\u7528\u6210\u4eba 40 \u5206\u949f\u6807\u51c6\u8861\u91cf\u5e7c\u513f\u4e13\u6ce8\u3002\u5e94\u770b 15-20 \u5206\u949f\u4e14\u80fd\u88ab\u6253\u65ad\u540e\u56de\u6765\u3002",
    "\u8bef\u533a\uff1a\u4e00\u5929\u5b89\u6392\u4e09\u56db\u4e2a\u73ed\u3002\u538b\u7f29\u7761\u7720\u4e0e\u8fd0\u52a8\uff0c\u635f\u5bb3\u6ce8\u610f\u529b\u4e0e\u60c5\u7eea\u3002",
    "\u8bef\u533a\uff1a\u5305\u529e\u5f0f\u966a\u5199\u3002\u5b69\u5b50\u5931\u53bb\u7ec3\u4e60\u673a\u4f1a\uff0c\u5165\u5b66\u540e\u4ecd\u4f9d\u8d56\u5bb6\u957f\u3002",
    "\u8bef\u533a\uff1a\u628a\u8bed\u8a00\u843d\u540e\u5f53\u8bf4\u8bdd\u665a\u4e00\u70b9\u6ca1\u5173\u7cfb\u3002\u8d8a\u65e9\u8bc4\u4f30\u8d8a\u5b89\u5168\u3002",
    "\u8bef\u533a\uff1a\u7528\u4e00\u5b9a\u8ddf\u5f97\u4e0a\u5b89\u6170\u6216\u7528\u8ddf\u4e0d\u4e0a\u5413\u552c\u3002\u672c\u5de5\u5177\u53ea\u63cf\u8ff0\u73b0\u72b6\uff0c\u4e0d\u9884\u6d4b\u7ed3\u679c\u3002",
]

POLICY_NOTE = [
    "\u4e49\u52a1\u6559\u80b2\u9636\u6bb5\u5165\u5b66\u5e74\u9f84\u3001\u514d\u8bd5\u5c31\u8fd1\u5165\u5b66\u3001\u5212\u7247\u4e0e\u6237\u7c4d\u6761\u4ef6\u5404\u5730\u4e0d\u540c\u4e14\u9010\u5e74\u53ef\u80fd\u8c03\u6574\u3002",
    "\u4efb\u4f55\u5f15\u7528\u4e00\u5f8b\u4ee5\u5f53\u5730\u6559\u80b2\u90e8\u95e8\u5f53\u5e74\u53d1\u5e03\u7684\u62db\u751f\u5165\u5b66\u5de5\u4f5c\u901a\u77e5\u4e3a\u51c6\u3002",
    "\u672c\u5de5\u5177\u4e0d\u7f16\u5199\u5177\u4f53\u6761\u6b3e\u53f7\u3001\u653f\u7b56\u6587\u4ef6\u540d\u79f0\u6216\u5e74\u4efd\u3002",
]

PRINCIPLES = [
    "\u987a\u5e8f\uff1a\u81ea\u7406\u4e0e\u89c4\u5219 -> \u4e13\u6ce8\u4e0e\u65f6\u95f4 -> \u524d\u9605\u8bfb\u524d\u4e66\u5199 -> \u8868\u8fbe\u4e0e\u8fd0\u52a8\uff0c\u77e5\u8bc6\u7c7b\u5185\u5bb9\u4e0d\u6392\u5165\u4e3b\u65f6\u6bb5\u3002",
    "\u603b\u91cf\uff1a\u6bcf\u65e5\u96c6\u4e2d\u7ec3\u4e60\u4e0d\u8d85\u8fc7 60 \u5206\u949f\uff0c\u6bcf\u5929\u6237\u5916 1 \u5c0f\u65f6\u4ee5\u4e0a\uff0c\u7761\u7720\u88ab\u538b\u7f29\u65f6\u5148\u51cf\u7ec3\u4e60\u91cf\u3002",
    "\u7a33\u5b9a\uff1a\u5b81\u53ef\u6bcf\u5929 20 \u5206\u949f\u8fde\u7eed 12 \u5468\uff0c\u4e0d\u8981\u5468\u672b\u7a81\u51fb 3 \u5c0f\u65f6\u3002",
    "\u5426\u5b9a\u8bcd\u9632\u8bef\u4f24\uff1a\u5355\u9879\u5f85\u8865\u4e0d\u7b49\u4e8e\u4e0d\u9002\u5408\u4e0a\u5c0f\u5b66\uff0c\u672c\u8868\u53ea\u63cf\u8ff0\u80fd\u529b\u73b0\u72b6\uff0c\u4e0d\u9884\u6d4b\u5165\u5b66\u7ed3\u679c\u3002",
]


def dim_label(key):
    for k, label, _t, _d in DIMENSIONS:
        if k == key:
            return label
    return key


def known_keys(raw):
    valid = dict((k, v) for k, v, _t, _d in DIMENSIONS)
    good, bad = [], []
    for k in list(raw or []):
        if k in valid:
            good.append(k)
        else:
            bad.append(k)
    return good, bad


def grade(ready_keys):
    n = len(ready_keys)
    if n >= 6:
        return "\u5c31\u7eea"
    if n >= 4:
        return "\u57fa\u672c\u5c31\u7eea"
    return "\u9700\u96c6\u4e2d\u8865\u77ed\u677f"


def phase_for(months_to_school):
    m = float(months_to_school or 0)
    if m < 3:
        return "\u5df2\u8fdb\u5165\u6700\u540e 3 \u5468\uff0c\u53ea\u505a\u7ef4\u6301\u4e0e\u9002\u5e94\u9884\u6f14\uff0c\u4e0d\u518d\u52a0\u91cf"
    for hi, lo, name, task, metric in PHASES:
        if lo <= m <= hi:
            return "%s\uff08\u8ddd\u5165\u5b66 %g \u4e2a\u6708\uff09\uff1a%s\u3002\u81ea\u68c0\u6307\u6807\uff1a%s" % (name, m, task, metric)
    return "\u8ddd\u5165\u5b66\u65f6\u95f4\u8d85\u51fa 3 \u4e2a\u6708\u8303\u56f4\uff0c\u8bf7\u6838\u5bf9\u5165\u5b66\u65f6\u95f4\u540e\u91cd\u6392"


def weak_order(ready_keys):
    rest = [k for k in PRIORITY_ORDER if k not in ready_keys]
    rest.sort(key=lambda k: PRIORITY_ORDER.index(k))
    return rest


def build_plan(ready_keys, months_to_school, focus):
    lines = []
    lines.append("\u5c31\u7eea\u7ef4\u5ea6\uff1a%d / 8" % len(ready_keys))
    rest = weak_order(ready_keys)
    if rest:
        lines.append("\u77ed\u677f\u4f18\u5148\u987a\u5e8f\uff1a" + "\u3001".join(dim_label(k) for k in rest))
    else:
        lines.append("\u77ed\u677f\u4f18\u5148\u987a\u5e8f\uff1a\u65e0\uff0c\u516b\u7ef4\u5ea6\u5747\u5df2\u5c31\u7eea")
    lines.append("")
    lines.append("\u5f53\u524d\u9636\u6bb5\u4efb\u52a1\uff1a")
    lines.append("  " + phase_for(months_to_school))
    lines.append("")
    if focus:
        lines.append("\u5355\u7ef4\u5ea6\u8be6\u60c5 [%s]\uff1a%s" % (focus, dim_label(focus)))
        for k, label, tag, desc in DIMENSIONS:
            if k == focus:
                lines.append("  \u5224\u5b9a\u7c7b\u522b\uff1a" + tag)
                lines.append("  \u89c2\u5bdf\u53e3\u5f84\uff1a" + desc)
        lines.append("  \u7ec3\u4e60\u539f\u5219\uff1a\u6bcf\u5929\u63a7\u5236\u5728 20-30 \u5206\u949f\uff0c\u6709\u660e\u786e\u7ec8\u70b9\uff0c\u5b81\u5c11\u52ff\u591a\u3002")
        lines.append("")
    lines.append("\u56db\u9636\u6bb5\u5012\u6392\u6846\u67b6\uff1a")
    for hi, lo, name, task, metric in PHASES:
        lines.append("  %s\uff08\u8ddd\u5165\u5b66 %d-%d \u5468\uff09\uff1a%s" % (name, hi, lo, task))
        lines.append("      \u81ea\u68c0\u6307\u6807\uff1a" + metric)
    lines.append("")
    lines.append("\u5012\u6392\u539f\u5219\uff1a")
    for p in PRINCIPLES:
        lines.append("  - " + p)
    lines.append("")
    lines.append("\u5165\u5b66\u9002\u5e94\u671f\u6b63\u5e38\u6ce2\u52a8\uff08\u5165\u5b66\u540e 4-6 \u5468\u5185\uff09\uff1a")
    for x in NORMAL_FLUCTUATION:
        lines.append("  - " + x)
    lines.append("")
    lines.append("\u9700\u8981\u5173\u6ce8\u7684\u4fe1\u53f7\uff08\u51fa\u73b0\u5373\u4e0e\u8001\u5e08\u6c9f\u901a\uff0c\u5fc5\u8981\u65f6\u4e13\u4e1a\u8bc4\u4f30\uff09\uff1a")
    for x in NEED_ATTENTION:
        lines.append("  - " + x)
    lines.append("")
    lines.append("\u5e38\u89c1\u8bef\u533a\uff1a")
    for x in MYTHS:
        lines.append("  - " + x)
    lines.append("")
    lines.append("\u653f\u7b56\u53e3\u5f84\uff1a")
    for x in POLICY_NOTE:
        lines.append("  - " + x)
    return lines


def build_report(data):
    raw_skills = list(data.get("skills", []))
    months = data.get("age_months", 0)
    mts = data.get("months_to_school", 3)
    flags = list(data.get("red_flags", []))
    focus = data.get("focus")

    lines = []
    lines.append("=" * 66)
    lines.append("\u5e7c\u5c0f\u8854\u63a5\u516b\u5927\u80fd\u529b\u6838\u67e5\u4e0e\u5012\u6392\u5efa\u8bae")
    lines.append("=" * 66)
    lines.append("\u5f53\u524d\u6708\u9f84\uff1a%g   \u8ddd\u5165\u5b66\uff1a%g \u4e2a\u6708" % (float(months or 0), float(mts or 0)))
    lines.append("")

    hit = [f for f in flags if f in RED_FLAGS]
    hit_unknown = [f for f in flags if f not in RED_FLAGS]
    if hit:
        lines.append("[\u7ea2\u7ebf] \u547d\u4e2d\u8bc4\u4f30\u7ea2\u7ebf\uff0c\u4e0d\u7ed9\u8854\u63a5\u65b9\u6848\uff1a")
        for f in hit:
            lines.append("  ! %s" % RED_FLAG_TEXT[f])
            lines.append("    \u8f6c\u4ea4\uff1a%s" % REFERRAL[f])
        lines.append("")
        lines.append("  \u8bf7\u5148\u5b8c\u6210\u4e13\u4e1a\u8bc4\u4f30\uff0c\u518d\u7531\u4e13\u4e1a\u673a\u6784\u5236\u5b9a\u8854\u63a5\u65b9\u6848\u3002")
        lines.append("=" * 66)
        return "\n".join(lines), {
            "blocked": True, "red_flags": hit, "level": "\u9700\u4e13\u4e1a\u8bc4\u4f30",
            "weak_order": [], "prediction_provided": False,
            "diagnosis_provided": False,
        }

    ready, unknown = known_keys(raw_skills)
    if unknown:
        lines.append("[\u63d0\u793a] \u672a\u8bc6\u522b\u7684\u7ef4\u5ea6\u6807\u8bb0\u5df2\u5ffd\u7565\uff1a" + "\u3001".join(unknown))
        lines.append("")

    lines.append("[\u4e00] \u516b\u7ef4\u5ea6\u6838\u67e5")
    for k, label, tag, desc in DIMENSIONS:
        mark = "[\u5c31\u7eea]" if k in ready else "[\u5f85\u8865]"
        lines.append("  %s %s\uff5c%s\uff5c%s" % (mark, label, tag, desc))
    lines.append("")

    lvl = grade(ready)
    lines.append("[\u4e8c] \u6863\u4f4d\u4e0e\u5012\u6392\u5efa\u8bae")
    lines.append("  \u6863\u4f4d\uff1a" + lvl)
    for line in build_plan(ready, mts, focus):
        lines.append("  " + line if line else "")

    lines.append("")
    lines.append("[\u4e09] \u6bcf\u6708\u5fc5\u505a")
    lines.append("  \u6bcf\u5468\u4e00\u6b21 10 \u5206\u949f\u4ee5\u5185\u7684\u5bb6\u5ead\u4f1a\u8bae\uff1a")
    lines.append("  1. \u8bf4\u51fa\u8fd9\u4e00\u5468\u505a\u5230\u6700\u597d\u7684\u4e00\u4ef6\u5177\u4f53\u4e8b\uff0c\u4e0d\u6cdb\u6cdb\u5938\u771f\u68d2")
    lines.append("  2. \u53ea\u7acb 1-2 \u6761\u4e0b\u5468\u8981\u7ec3\u7684\u89c4\u5219\uff0c\u5168\u5bb6\u5305\u62ec\u5bb6\u957f\u4e00\u8d77\u9075\u5b88")
    lines.append("  3. \u5b69\u5b50\u8bf4\u4e00\u4ef6\u5b66\u6821\u6216\u5bb6\u91cc\u7684\u4e8b\uff0c\u5bb6\u957f\u53ea\u542c\u4e0d\u8bc4\u4ef7")
    lines.append("  4. \u4e0d\u6bd4\u8f83\u3001\u4e0d\u6392\u540d\u3001\u4e0d\u52a0\u7801")
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u53ea\u63cf\u8ff0\u80fd\u529b\u73b0\u72b6\uff0c\u4e0d\u9884\u6d4b\u5165\u5b66\u6210\u7ee9\uff0c\u4e0d\u6784\u6210\u533b\u7597\u6216\u6559\u80b2\u8bca\u65ad\u610f\u89c1\u3002")
    lines.append("\u5165\u5b66\u653f\u7b56\u4ee5\u5f53\u5730\u6559\u80b2\u90e8\u95e8\u5f53\u5e74\u53d1\u5e03\u7684\u62db\u751f\u5165\u5b66\u5de5\u4f5c\u901a\u77e5\u4e3a\u51c6\u3002")
    lines.append("=" * 66)
    summary = {
        "blocked": False,
        "red_flags": hit_unknown,
        "level": lvl,
        "ready_count": len(ready),
        "weak_order": weak_order(ready),
        "phase": phase_for(mts),
        "prediction_provided": False,
        "diagnosis_provided": False,
        "textbook_recommended": False,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("\u516b\u7ef4\u5ea6\u5df2\u5b9a\u4e49", len(DIMENSIONS) == 8))
    r.append(("\u5012\u6392\u56db\u9636\u6bb5\u5df2\u5b9a\u4e49", len(PHASES) == 4))
    r.append(("\u7ea2\u7ebf\u81f3\u5c11 7 \u6761", len(RED_FLAGS) >= 7))

    good, bad = known_keys(["selfcare", "not_exist"])
    r.append(("\u5df2\u8bc6\u522b\u7ef4\u5ea6\u8ba1\u6570\u6b63\u786e", good == ["selfcare"]))
    r.append(("\u672a\u8bc6\u522b\u7ef4\u5ea6\u88ab\u8fc7\u6ee4", bad == ["not_exist"]))

    all_keys = [k for k, _l, _t, _d in DIMENSIONS]
    r.append(("8 \u9879\u5c31\u7eea\u5224\u5b9a\u4e3a\u5c31\u7eea", grade(all_keys) == "\u5c31\u7eea"))
    r.append(("5 \u9879\u5c31\u7eea\u5224\u5b9a\u4e3a\u57fa\u672c\u5c31\u7eea", grade(all_keys[:5]) == "\u57fa\u672c\u5c31\u7eea"))
    r.append(("3 \u9879\u5c31\u7eea\u5224\u5b9a\u4e3a\u9700\u96c6\u4e2d\u8865\u77ed\u677f", grade(all_keys[:3]) == "\u9700\u96c6\u4e2d\u8865\u77ed\u677f"))

    order = weak_order(["selfcare", "rule"])
    r.append(("\u77ed\u677f\u6392\u5e8f\u9996\u9879\u4e3a\u65f6\u95f4\u7ba1\u7406", order[0] == "time"))
    r.append(("\u77ed\u677f\u6392\u5e8f\u4e0d\u542b\u5df2\u5c31\u7eea\u9879", "selfcare" not in order))
    r.append(("\u77ed\u677f\u5168\u5c31\u7eea\u65f6\u8fd4\u56de\u7a7a\u5217\u8868", weak_order(all_keys) == []))

    r.append(("\u8ddd\u5165\u5b66 12 \u5468\u843d\u5728\u7b2c\u4e00\u9636\u6bb5", "\u7b2c\u4e00\u9636\u6bb5" in phase_for(12)))
    r.append(("\u8ddd\u5165\u5b66 6 \u5468\u843d\u5728\u7b2c\u4e8c\u9636\u6bb5", "\u7b2c\u4e8c\u9636\u6bb5" in phase_for(6)))
    r.append(("\u8ddd\u5165\u5b66 3 \u5468\u843d\u5728\u7b2c\u4e09\u9636\u6bb5", "\u7b2c\u4e09\u9636\u6bb5" in phase_for(3)))
    r.append(("\u8ddd\u5165\u5b66 2 \u5468\u8fdb\u5165\u6700\u540e 3 \u5468", "\u6700\u540e 3 \u5468" in phase_for(2)))
    r.append(("\u8ddd\u5165\u5b66 24 \u4e2a\u6708\u7ed9\u51fa\u8d85\u8303\u56f4\u63d0\u793a", "\u8d85\u51fa 3 \u4e2a\u6708\u8303\u56f4" in phase_for(24)))

    _, s = build_report({"age_months": 72, "months_to_school": 4, "skills": all_keys})
    r.append(("\u5b8c\u6574\u6837\u4f8b\u4e0d\u963b\u65ad", s["blocked"] is False))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u5224\u5b9a\u4e3a\u5c31\u7eea", s["level"] == "\u5c31\u7eea"))
    r.append(("\u4e0d\u9884\u6d4b\u5165\u5b66\u6210\u7ee9", s["prediction_provided"] is False))
    r.append(("\u4e0d\u505a\u8bca\u65ad\u7ed3\u8bba", s["diagnosis_provided"] is False))
    r.append(("\u4e0d\u6307\u5b9a\u6559\u6750", s["textbook_recommended"] is False))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u77ed\u677f\u4e3a\u7a7a", s["weak_order"] == []))

    _, s2 = build_report({"age_months": 72, "skills": all_keys, "red_flags": ["language_delay"]})
    r.append(("\u8bed\u8a00\u843d\u540e\u76f4\u63a5\u963b\u65ad", s2["blocked"] is True))
    r.append(("\u963b\u65ad\u65f6\u5224\u5b9a\u4e3a\u9700\u4e13\u4e1a\u8bc4\u4f30", s2["level"] == "\u9700\u4e13\u4e1a\u8bc4\u4f30"))
    r.append(("\u963b\u65ad\u65f6\u4e0d\u7ed9\u77ed\u677f\u6392\u5e8f", s2["weak_order"] == []))

    _, s3 = build_report({"age_months": 72, "skills": all_keys, "focus": "writing"})
    r.append(("\u6307\u5b9a\u7ef4\u5ea6\u56de\u663e\u6b63\u786e", s3["blocked"] is False))

    txt, _ = build_report({"age_months": 72, "months_to_school": 4, "skills": all_keys})
    r.append(("\u8f93\u51fa\u542b\u6559\u80b2\u90e8\u95e8\u53e3\u5f84", "\u5f53\u5730\u6559\u80b2\u90e8\u95e8" in txt))
    r.append(("\u8f93\u51fa\u542b\u4e0d\u9884\u6d4b\u7ed3\u679c\u53e3\u5f84", "\u4e0d\u9884\u6d4b\u5165\u5b66\u7ed3\u679c" in txt))
    r.append(("\u8f93\u51fa\u542b\u8bef\u533a\u6e05\u5355", "\u8bef\u533a\uff1a\u63d0\u524d\u5b66\u4e00\u5e74\u7ea7\u8bfe\u672c" in txt))
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
    parser = argparse.ArgumentParser(description="\u5e7c\u5c0f\u8854\u63a5\u516b\u5927\u80fd\u529b\u6838\u67e5\u4e0e\u5012\u6392\u5efa\u8bae\u751f\u6210\u5de5\u5177")
    parser.add_argument("--file", help="\u8f93\u5165 JSON \u6587\u4ef6\u8def\u5f84\uff08UTF-8\uff09")
    parser.add_argument("--focus", help="\u53ea\u5c55\u5f00\u67d0\u7ef4\u5ea6\uff1aselfcare time focus rule reading writing express motor")
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
    if args.focus:
        data["focus"] = args.focus

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
