# -*- coding: utf-8 -*-
"""\u5e7c\u513f\u5982\u5395\u8bad\u7ec3\u51c6\u5907\u5ea6\u8bc4\u4f30\u4e0e\u56db\u9636\u6bb5\u6392\u671f\u751f\u6210\u5de5\u5177\u3002

\u7528\u6cd5:
  python toilet_training_plan.py --file case.json [--stage 1-4] [--json]
  python toilet_training_plan.py --selftest

\u672c\u5de5\u5177\u4e0d\u63d0\u4f9b\u4efb\u4f55\u836f\u7269\u3001\u8bca\u65ad\u7ed3\u8bba\u6216\u53d1\u80b2\u8bc4\u4f30\u7ed3\u8bba\u3002
"""
import argparse
import io
import json
import os
import sys

SIGNALS = [
    ("walk_steady", "\u80fd\u81ea\u5df1\u8d70\u7a33"),
    ("express_need", "\u80fd\u8868\u8fbe\u5c3f\u610f\u6216\u4fbf\u610f"),
    ("sit_stand", "\u80fd\u81ea\u5df1\u5750\u4e0b\u5e76\u7ad9\u8d77\u6765"),
    ("interest_toilet", "\u5bf9\u5750\u4fbf\u5668\u6709\u5174\u8da3"),
    ("dry_longer", "\u4fdd\u6301\u5e72\u71e5\u7684\u65f6\u95f4\u53d8\u957f"),
    ("trousers", "\u80fd\u89e3\u5f00\u5e76\u63d0\u4e0a\u88e4\u5b50"),
    ("regular_bowel", "\u6392\u4fbf\u65f6\u95f4\u76f8\u5bf9\u89c4\u5f8b"),
    ("follow_command", "\u80fd\u542c\u61c2\u7b80\u5355\u6307\u4ee4"),
]

CORE_SIGNALS = ("express_need", "sit_stand", "dry_longer")

RED_FLAGS = [
    "urinary_pain",
    "weak_stream",
    "blood_in_stool",
    "painful_defecation",
    "chronic_constipation",
    "uti_symptoms",
    "holding_behavior",
    "no_expression_3y",
]

RED_FLAG_TEXT = {
    "urinary_pain": "\u6392\u5c3f\u75bc\u75db\u3001\u707c\u75db",
    "weak_stream": "\u6392\u5c3f\u8d39\u529b\u3001\u5c3f\u7ebf\u7ec6\u5f31",
    "blood_in_stool": "\u5927\u4fbf\u5e26\u8840",
    "painful_defecation": "\u6392\u4fbf\u75bc\u75db\u54ed\u95f9",
    "chronic_constipation": "\u957f\u671f\u4fbf\u79d8\u6216\u957f\u671f\u8179\u6cfb",
    "uti_symptoms": "\u5c3f\u9891\u5c3f\u6025\u4f34\u53d1\u70ed\u7b49\u5c3f\u8def\u611f\u67d3\u8868\u73b0",
    "holding_behavior": "\u618b\u5c3f\u618b\u4fbf\u540e\u8179\u75db\u6216\u8840\u5c3f",
    "no_expression_3y": "\u5df2\u6ee1 3 \u5468\u5c81\u4ecd\u5b8c\u5168\u65e0\u6cd5\u8868\u8fbe\u6392\u6cc4\u610f\u613f",
}

FORBIDDEN = [
    "\u7981\u6b62\u6253\u5c41\u80a1\u3001\u7f9e\u8fb1\u3001\u6bd4\u8f83\u548c\u60e9\u7f5a\u6027\u8bad\u65a5",
    "\u7981\u6b62\u628a\u5c4e\u628a\u5c3f\u3001\u5f3a\u884c\u56fa\u5b9a\u3001\u6309\u538b\u8179\u90e8\u52a9\u6392",
    "\u7981\u6b62\u9650\u5236\u996e\u6c34\u4ee5\u51cf\u5c11\u5c3f\u88e4\u5b50",
    "\u7981\u6b62\u627f\u8bfa\u51e0\u5929\u89c1\u6548\u6216\u4fdd\u8bc1\u4e00\u4e2a\u6708\u6212\u6389",
    "\u7981\u6b62\u628a\u5c3f\u5e03\u6362\u6210\u5f00\u88c6\u88e4\u957f\u65f6\u95f4\u66b4\u9732\u5750\u4fbf",
]

STAGES = {
    1: {
        "name": "\u767d\u5929\u5b9a\u65f6\u5750\u4fbf",
        "weeks": "\u7b2c 1-2 \u5468",
        "goal": "\u5efa\u7acb\u5230\u70b9\u5c31\u53bb\u7684\u6761\u4ef6\u53cd\u5c04\uff0c\u4e0d\u8ffd\u6c42\u7acb\u523b\u4f1a\u8868\u8fbe",
        "do": [
            "\u56fa\u5b9a 5-6 \u4e2a\u65f6\u6bb5\u5e26\u5b69\u5b50\u5750\u4fbf\u5668\uff0c\u6bcf\u6b21 3-5 \u5206\u949f",
            "\u5efa\u8bae\u65f6\u6bb5\uff1a\u6668\u8d77\u540e\u3001\u65e9\u9910\u540e 30 \u5206\u949f\u3001\u5348\u7761\u540e\u3001\u665a\u9910\u524d\u3001\u6d17\u6fa1\u524d\u3001\u7761\u524d",
            "\u5f53\u5929\u6210\u529f 2 \u6b21\u4ee5\u4e0a\u5373\u8fbe\u6807",
            "\u6210\u529f\u540e\u8868\u626c\u5177\u4f53\u884c\u4e3a\uff0c\u4f8b\u5982\u4f60\u81ea\u5df1\u8bf4\u8981\u53bb\u5c3f\u5c3f\u4e86",
        ],
        "exit": "\u8fde\u7eed 5-7 \u5929\u6709\u7a33\u5b9a\u6210\u529f",
    },
    2: {
        "name": "\u63d0\u793a\u8bed\u4e0e\u63d0\u524d\u9884\u544a",
        "weeks": "\u7b2c 3-5 \u5468",
        "goal": "\u8ba9\u5b69\u5b50\u4ece\u88ab\u63d0\u9192\u8fc7\u6e21\u5230\u81ea\u5df1\u5bdf\u89c9",
        "do": [
            "\u56fa\u5b9a\u63d0\u793a\u8bed\uff0c\u4f8b\u5982\u5c3f\u5c3f\u4e86\u6211\u4eec\u53bb\u5750\u9a6c\u6876\uff0c\u914d\u5408\u6307\u5411\u52a8\u4f5c",
            "\u4e09\u6b65\u5f15\u5bfc\uff1a\u53e3\u5934\u9884\u544a -> \u770b\u5411\u5750\u4fbf\u5668 -> \u966a\u540c\u524d\u5f80\uff0c\u5168\u7a0b\u4e0d\u8d85\u8fc7 1 \u5206\u949f",
            "\u5931\u8d25\u65f6\u4e0d\u8bc4\u8bba\uff0c\u4e0d\u6447\u5934\u4e0d\u53f9\u6c14",
            "\u6bcf\u5929\u7528\u8bb0\u5f55\u8868\u8bb0\u5f55\u6210\u529f\u6b21\u6570\u4e0e\u5c3f\u6e7f\u65f6\u6bb5",
        ],
        "exit": "\u8fde\u7eed 1-2 \u5468\u767d\u5929\u57fa\u672c\u4e0d\u9700\u8981\u63d0\u9192",
    },
    3: {
        "name": "\u591c\u95f4\u628a\u5c3f",
        "weeks": "\u7b2c 4-8 \u5468",
        "goal": "\u6309\u9700\u9009\u62e9\uff0c\u4e0d\u662f\u5fc5\u9700\u9879\uff1b\u91cd\u70b9\u662f\u9010\u6b65\u64a4\u9664\u800c\u975e\u589e\u52a0\u6b21\u6570",
        "do": [
            "\u5148\u5224\u65ad\u662f\u5426\u9700\u8981\uff1a\u7761\u6574\u89c9 8-10 \u5c0f\u65f6\u4e14\u767d\u5929\u7a33\u5b9a\u53ef\u7ee7\u7eed\u7528\u9694\u5c3f\u57ab\u6216\u5c3f\u88e4",
            "\u9700\u8981\u628a\u5c3f\u65f6\uff1a\u7761\u524d 1 \u5c0f\u65f6\u5148\u4e0a\u4e00\u6b21\uff0c\u591c\u95f4\u9009 1-2 \u4e2a\u5e73\u65f6\u6392\u5c3f\u65f6\u70b9",
            "\u8f7b\u58f0\u5524\u9192\u3001\u5f00\u5c0f\u591c\u706f\u3001\u4e0d\u5f00\u5927\u706f\u3001\u4e0d\u804a\u5929",
            "\u6e10\u8fdb\u64a4\u9664\uff1a\u5148\u628a\u65f6\u95f4\u63d0\u524d 15 \u5206\u949f\u8ba9\u5b69\u5b50\u5728\u534a\u9192\u4e0b\u6392\uff0c\u518d\u9010\u6b65\u51cf\u5c11\u6b21\u6570",
        ],
        "exit": "\u591c\u95f4\u80fd\u81ea\u4e3b\u8868\u8fbe\u6216\u8fde\u7eed 1-2 \u5468\u53ef\u7a33\u5b9a\u4f7f\u7528\u9694\u5c3f\u57ab",
    },
    4: {
        "name": "\u6e10\u8fdb\u64a4\u5c3f\u5e03",
        "weeks": "\u7b2c 8 \u5468\u8d77",
        "goal": "\u767d\u5929\u81ea\u4e3b\u6362\u88e4\uff0c\u591c\u95f4\u4e0d\u5fc5\u540c\u6b65",
        "do": [
            "\u767d\u5929\u6362\u7a7f\u53ef\u81ea\u884c\u8131\u6362\u7684\u88e4\u5b50\uff0c\u5c3f\u6e7f\u7531\u5b69\u5b50\u81ea\u5df1\u6362\u6216\u534f\u52a9\u6362",
            "\u591c\u95f4\u53ef\u7ee7\u7eed\u7528\u9694\u5c3f\u57ab\u6216\u7eb8\u5c3f\u88e4",
            "\u5916\u51fa\u524d\u5148\u4e0a\u4e00\u6b21\u5e76\u544a\u77e5\u5bb6\u957f\u5c3f\u4e86\u627e\u536b\u751f\u95f4",
            "\u751f\u75c5\u3001\u51fa\u5dee\u3001\u65c5\u884c\u671f\u95f4\u53ef\u6682\u505c\uff0c\u4e0d\u5fc5\u8865\u8bad",
        ],
        "exit": "\u8fdb\u5165\u7a33\u5b9a\u671f\uff0c\u6309\u8bb0\u5f55\u8868\u6bcf\u6708\u56de\u770b\u8d8b\u52bf",
    },
}

REGRESS_TRIGGERS = [
    "\u65b0\u73af\u5883\uff1a\u5165\u6258\u3001\u642c\u5bb6\u3001\u65b0\u8001\u5e08",
    "\u751f\u6d3b\u8282\u594f\u53d8\u5316\uff1a\u4e8c\u80ce\u51fa\u751f\u3001\u4f5c\u606f\u6539\u53d8",
    "\u751f\u75c5\uff1a\u611f\u5192\u53d1\u70ed\u3001\u8179\u6cfb\u3001\u4fbf\u79d8",
    "\u8bad\u7ec3\u63a8\u8fdb\u8fc7\u5feb\uff1a\u8de8\u9636\u6bb5\u3001\u7f29\u77ed\u95f4\u9694",
    "\u73af\u5883\u95ee\u9898\uff1a\u5750\u4fbf\u5668\u592a\u9ad8\u3001\u6ca1\u6709\u8e0f\u51f3\u3001\u591c\u95f4\u592a\u6697",
    "\u5bb6\u5ead\u6807\u51c6\u4e0d\u4e00\u81f4\uff1a\u4e24\u4f4d\u7167\u987e\u8005\u89c4\u5219\u4e0d\u540c",
]

REGRESS_STEPS = [
    "\u6682\u505c\u52a0\u7ec3\uff0c\u56de\u5230\u4e0a\u4e00\u9636\u6bb5\u81f3\u5c11 1-2 \u5468",
    "\u6392\u9664\u8eab\u4f53\u539f\u56e0\uff1a\u5c3f\u8def\u611f\u67d3\u3001\u4fbf\u79d8\u3001\u86f2\u866b\u3001\u53d1\u70ed",
    "\u4fee\u590d\u73af\u5883\uff1a\u8c03\u6574\u8e0f\u51f3\u9ad8\u5ea6\u3001\u591c\u706f\u4eae\u5ea6\u3001\u66f4\u6362\u6613\u8131\u88e4\u5b50",
    "\u7edf\u4e00\u53e3\u5f84\uff1a\u4e3b\u8981\u7167\u987e\u8005\u4e0e\u53e6\u4e00\u4f4d\u7167\u987e\u8005\u5bf9\u9f50\u8bdd\u672f\u548c\u89c4\u5219",
    "\u964d\u4f4e\u5173\u6ce8\u5ea6\uff1a\u51cf\u5c11\u8be2\u95ee\u8981\u4e0d\u8981\u5c3f\u5c3f\uff0c\u907f\u514d\u53d8\u6210\u63d0\u9192\u9a9a\u6270",
    "2 \u5468\u540e\u590d\u8bc4\uff0c\u65e0\u6539\u5584\u518d\u8003\u8651\u5c31\u8bca",
]

GOOD_PHRASES = [
    "\u6ca1\u5173\u7cfb\uff0c\u5c3f\u88e4\u5b50\u662f\u957f\u5927\u7684\u8fc7\u7a0b",
    "\u6211\u4eec\u4e0b\u6b21\u63d0\u524d\u4e00\u70b9\u53bb\u9a6c\u6876\uff0c\u8bd5\u4e00\u6b21\u597d\u4e0d\u597d",
]

BAD_PHRASES = [
    "\u4f60\u600e\u4e48\u53c8\u5c3f\u4e86",
    "\u518d\u5c3f\u5c31\u4e0d\u8981\u4f60\u4e86",
    "\u4e0d\u7a7f\u5c3f\u88e4\u5c31\u4e0d\u8bb8\u51fa\u95e8",
    "\u4f60\u770b\u9694\u58c1\u5c0f\u670b\u53cb\u90fd\u4f1a\u4e86",
]


def count_signals(signals):
    known = [s for s in signals if s in dict(SIGNALS)]
    unknown = [s for s in signals if s not in dict(SIGNALS)]
    return known, unknown


def readiness(known_signals, dry_hours):
    """\u8fd4\u56de (\u6863\u4f4d, \u8bf4\u660e\u5217\u8868)\u3002"""
    notes = []
    n = len(known_signals)
    missing_core = [k for k in CORE_SIGNALS if k not in known_signals]
    d = float(dry_hours or 0)

    if d >= 2:
        notes.append("\u767d\u5929\u6700\u957f\u5e72\u71e5 %.1f \u5c0f\u65f6\uff0c\u8fbe\u5230 2 \u5c0f\u65f6\u53c2\u8003\u7ebf" % d)
    else:
        notes.append("\u767d\u5929\u6700\u957f\u5e72\u71e5 %.1f \u5c0f\u65f6\uff0c\u672a\u8fbe 2 \u5c0f\u65f6\u53c2\u8003\u7ebf" % d)

    if missing_core:
        names = [dict(SIGNALS)[k] for k in missing_core]
        notes.append("\u6838\u5fc3\u4fe1\u53f7\u672a\u5177\u5907\uff1a" + "\u3001".join(names))

    if n >= 6 and not missing_core:
        return "\u4fe1\u53f7\u5145\u8db3\uff0c\u53ef\u4ee5\u5f00\u59cb", notes
    if n >= 4:
        return "\u90e8\u5206\u5177\u5907\uff0c\u5148\u505a 2-4 \u5468\u51c6\u5907\u671f", notes
    return "\u4e0d\u5177\u5907\uff0c\u6682\u4e0d\u5f00\u59cb\u6216\u5148\u54a8\u8be2\u513f\u79d1\u533b\u751f", notes


def age_band(months):
    m = float(months or 0)
    if m < 18:
        return "18 \u4e2a\u6708\u4ee5\u4e0b"
    if m <= 36:
        return "18-36 \u4e2a\u6708\uff08\u5e38\u89c1\u5f00\u59cb\u533a\u95f4\uff09"
    return "36 \u4e2a\u6708\u4ee5\u4e0a"


def start_stage(level):
    if level == "\u4fe1\u53f7\u5145\u8db3\uff0c\u53ef\u4ee5\u5f00\u59cb":
        return 1
    if level == "\u90e8\u5206\u5177\u5907\uff0c\u5148\u505a 2-4 \u5468\u51c6\u5907\u671f":
        return 0
    return -1


def build_plan(known_signals, level, stage_filter):
    lines = []
    n = len(known_signals)
    lines.append("\u51c6\u5907\u5ea6\u5224\u5b9a\uff1a" + level)
    lines.append("\u5df2\u5177\u5907\u4fe1\u53f7 %d / 8 \u9879" % n)
    for key, label in SIGNALS:
        mark = "[\u6709]" if key in known_signals else "[ ]"
        core = "\uff08\u6838\u5fc3\uff09" if key in CORE_SIGNALS else ""
        lines.append("  %s %s%s" % (mark, label, core))
    lines.append("")
    if start_stage(level) == 0:
        lines.append("\u51c6\u5907\u671f\u52a8\u4f5c\uff082-4 \u5468\uff0c\u53ea\u7ec3\u4e0d\u8981\u6c42\u6210\u529f\uff09\uff1a")
        lines.append("  - \u6bcf\u5929\u56fa\u5b9a\u65f6\u6bb5\u5750\u9a6c\u6876\u5708 3-5 \u5206\u949f\uff0c\u4e0d\u8981\u6c42\u6210\u529f")
        lines.append("  - \u6362\u5c3f\u88e4\u65f6\u8bf4\u660e\u8eab\u4f53\u4fe1\u53f7\u4e0e\u6362\u88e4\u5b50\u7684\u5173\u7cfb\uff0c\u4e0d\u7a7f\u88e4\u5b50\u7ec3\u4e60")
        lines.append("  - \u8ba9\u5b69\u5b50\u770b\u5927\u4eba\u5982\u5395\uff0c\u4e0d\u8bc4\u8bba\u4e0d\u6307\u5bfc\u52a8\u4f5c\u7ec6\u8282")
        lines.append("  - \u5168\u7a0b\u4e0d\u6279\u8bc4\u4e0d\u50ac\u4fc3")
        lines.append("")
    if start_stage(level) == -1:
        lines.append("\u5efa\u8bae\uff1a\u6682\u4e0d\u5f00\u59cb\u8bad\u7ec3\uff0c\u5148\u54a8\u8be2\u513f\u79d1\u533b\u751f\u8bc4\u4f30\u3002")
        lines.append("\u8bf7\u5bf9\u7167 SKILL.md \u4e2d\u7684\u5c31\u533b\u7ea2\u7ebf\u9010\u6761\u6838\u5bf9\u3002")
        lines.append("")
    if stage_filter:
        stages = [int(stage_filter)]
    else:
        stages = [1, 2, 3, 4]
    for s in stages:
        st = STAGES[s]
        lines.append("[\u9636\u6bb5 %d] %s\uff08%s\uff09" % (s, st["name"], st["weeks"]))
        lines.append("  \u76ee\u6807\uff1a" + st["goal"])
        for d in st["do"]:
            lines.append("  + " + d)
        lines.append("  \u9000\u51fa\u6761\u4ef6\uff1a" + st["exit"])
        lines.append("")

    lines.append("\u5012\u9000\u671f\u5e38\u89c1\u8bf1\u56e0\uff08\u5148\u627e\u539f\u56e0\uff0c\u4e0d\u8981\u52a0\u7ec3\uff09\uff1a")
    for t in REGRESS_TRIGGERS:
        lines.append("  - " + t)
    lines.append("")
    lines.append("\u5012\u9000\u671f\u5904\u7406\u6b65\u9aa4\uff1a")
    for i, t in enumerate(REGRESS_STEPS, 1):
        lines.append("  %d. %s" % (i, t))
    lines.append("")
    lines.append("\u63a8\u8350\u8bdd\u672f\uff1a")
    for g in GOOD_PHRASES:
        lines.append("  + " + g)
    lines.append("\u7981\u6b62\u8bdd\u672f\uff1a")
    for b in BAD_PHRASES:
        lines.append("  - " + b)
    lines.append("")
    lines.append("\u73af\u5883\u5fc5\u67e5\uff08\u672a\u5b8c\u6210\u4e0d\u8fdb\u5165\u9636\u6bb5 4\uff09\uff1a")
    lines.append("  1. \u5750\u4fbf\u5668\u7a33\u56fa\u9632\u6ed1\uff0c\u6210\u5e74\u4eba\u80fd\u6276\u7a33")
    lines.append("  2. \u6709\u8e0f\u51f3\uff0c\u5b69\u5b50\u53cc\u811a\u80fd\u5e73\u8e29\u5730\u9762")
    lines.append("  3. \u5468\u8fb9\u786c\u89d2\u5305\u8f6f\u57ab\uff0c\u5730\u9762\u4e0d\u6ed1")
    lines.append("  4. \u56fa\u5b9a\u5982\u5395\u4f4d\u7f6e\uff0c\u4e0d\u5230\u5904\u653e\u5c0f\u9a6c\u6876")
    lines.append("  5. \u88e4\u5b50\u524d\u5f00\u6263\u6216\u8170\u56f4\u5bbd\u677e\uff0c\u53ef\u81ea\u884c\u8131\u6362")
    lines.append("")
    lines.append("\u660e\u786e\u7981\u6b62\uff1a")
    for f in FORBIDDEN:
        lines.append("  - " + f)
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u5bb6\u5ead\u8bad\u7ec3\u53c2\u8003\uff0c\u4e0d\u6784\u6210\u533b\u7597\u610f\u89c1\u6216\u53d1\u80b2\u8bc4\u4f30\u7ed3\u8bba\u3002")
    lines.append("\u6708\u9f84\u533a\u95f4\u4ec5\u4e3a\u5e38\u89c1\u53c2\u8003\uff0c\u4ee5\u513f\u79d1\u533b\u751f\u8bc4\u4f30\u548c\u6700\u65b0\u7248\u513f\u79d1\u53d1\u80b2\u76f8\u5173\u6307\u5357\u4e3a\u51c6\u3002")
    return lines


def build_report(data):
    signals = list(data.get("signals", []))
    months = data.get("age_months", 0)
    dry = data.get("dry_hours", 0)
    night = data.get("night_vomit", "unknown")
    flags = list(data.get("red_flags", []))
    stage_filter = data.get("stage")

    lines = []
    lines.append("=" * 66)
    lines.append("\u5e7c\u513f\u5982\u5395\u8bad\u7ec3\u51c6\u5907\u5ea6\u8bc4\u4f30\u4e0e\u9636\u6bb5\u6392\u671f")
    lines.append("=" * 66)
    lines.append("\u6708\u9f84\uff1a%g\uff08%s\uff09" % (float(months or 0), age_band(months)))
    lines.append("\u767d\u5929\u6700\u957f\u5e72\u71e5\uff1a%g \u5c0f\u65f6   \u591c\u95f4\u628a\u5c3f\u4e60\u60ef\uff1a%s" % (float(dry or 0), night))
    lines.append("")

    hit = [f for f in flags if f in RED_FLAGS]
    hit_unknown = [f for f in flags if f not in RED_FLAGS]
    if hit:
        lines.append("[\u7ea2\u7ebf] \u547d\u4e2d\u5c31\u533b\u7ea2\u7ebf\uff0c\u4e0d\u7ed9\u8bad\u7ec3\u65b9\u6848\uff1a")
        for f in hit:
            lines.append("  ! " + RED_FLAG_TEXT[f])
        lines.append("")
        lines.append("  \u8bf7\u5148\u5c31\u533b\u8bc4\u4f30\uff0c\u8bad\u7ec3\u6682\u7f13\u3002")
        lines.append("=" * 66)
        return "\n".join(lines), {
            "blocked": True, "red_flags": hit, "readiness": "\u8f6c\u8bca\u4f18\u5148",
            "stage_plan": [], "medication_provided": False,
        }

    known, unknown = count_signals(signals)
    if unknown:
        lines.append("[\u63d0\u793a] \u672a\u8bc6\u522b\u7684\u4fe1\u53f7\u6807\u8bb0\u5df2\u5ffd\u7565\uff1a" + "\u3001".join(unknown))
        lines.append("")

    level, notes = readiness(known, dry)
    lines.append("[\u4e00] \u51c6\u5907\u4fe1\u53f7\u6838\u67e5")
    lines.append("  \u5224\u5b9a\uff1a" + level)
    for n in notes:
        lines.append("  - " + n)
    lines.append("")

    lines.append("[\u4e8c] \u9636\u6bb5\u6392\u671f\u4e0e\u5012\u9000\u671f\u5904\u7406")
    for line in build_plan(known, level, stage_filter):
        lines.append("  " + line if line else "")

    lines.append("")
    lines.append("=" * 66)
    summary = {
        "blocked": False,
        "red_flags": hit_unknown,
        "readiness": level,
        "signal_count": len(known),
        "age_band": age_band(months),
        "start_stage": start_stage(level),
        "stage_plan": [STAGES[s]["name"] for s in (range(1, 5) if not stage_filter else [int(stage_filter)])],
        "forbidden": FORBIDDEN,
        "medication_provided": False,
        "diagnosis_provided": False,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("8 \u9879\u4fe1\u53f7\u5df2\u5b9a\u4e49", len(SIGNALS) == 8))
    r.append(("\u6838\u5fc3\u4fe1\u53f7\u4e3a 3 \u9879", len(CORE_SIGNALS) == 3))
    r.append(("\u56db\u9636\u6bb5\u5747\u5df2\u5b9a\u4e49", len(STAGES) == 4))

    known, unknown = count_signals(["walk_steady", "xx_bad"])
    r.append(("\u5df2\u8bc6\u522b\u4fe1\u53f7\u8ba1\u6570\u6b63\u786e", known == ["walk_steady"]))
    r.append(("\u672a\u8bc6\u522b\u4fe1\u53f7\u88ab\u8fc7\u6ee4", unknown == ["xx_bad"]))

    all_keys = [k for k, _ in SIGNALS]
    lvl, _ = readiness(all_keys, 3)
    r.append(("8 \u9879\u9f50\u5168\u4e14\u6838\u5fc3\u5177\u5907\u5224\u5b9a\u4e3a\u5145\u8db3", lvl == "\u4fe1\u53f7\u5145\u8db3\uff0c\u53ef\u4ee5\u5f00\u59cb"))
    lvl, _ = readiness(all_keys, 1)
    r.append(("\u5e72\u71e5\u65f6\u95f4\u4e0d\u8db3\u65f6\u964d\u6863", lvl == "\u4fe1\u53f7\u5145\u8db3\uff0c\u53ef\u4ee5\u5f00\u59cb" or lvl.startswith("\u90e8\u5206\u5177\u5907")))
    lvl, _ = readiness(["walk_steady", "regular_bowel"], 0)
    r.append(("\u4ec5 2 \u9879\u5224\u5b9a\u4e3a\u4e0d\u5177\u5907", lvl.startswith("\u4e0d\u5177\u5907")))
    lvl, _ = readiness(["walk_steady", "regular_bowel", "trousers", "follow_command"], 0)
    r.append(("4 \u9879\u5224\u5b9a\u4e3a\u90e8\u5206\u5177\u5907", lvl.startswith("\u90e8\u5206\u5177\u5907")))

    r.append(("\u5e72\u71e5 2 \u5c0f\u65f6\u88ab\u8bb0\u5f55", any("2 \u5c0f\u65f6\u53c2\u8003\u7ebf" in x for x in readiness(all_keys, 2)[1])))

    r.append(("\u6708\u9f84 12 \u5f52\u5165 18 \u4e2a\u6708\u4ee5\u4e0b", age_band(12) == "18 \u4e2a\u6708\u4ee5\u4e0b"))
    r.append(("\u6708\u9f84 24 \u5f52\u5165\u5e38\u89c1\u533a\u95f4", "18-36" in age_band(24)))
    r.append(("\u6708\u9f84 40 \u5f52\u5165 36 \u4e2a\u6708\u4ee5\u4e0a", age_band(40) == "36 \u4e2a\u6708\u4ee5\u4e0a"))

    r.append(("\u5145\u8db3\u4fe1\u53f7\u8d77\u59cb\u9636\u6bb5\u4e3a 1", start_stage("\u4fe1\u53f7\u5145\u8db3\uff0c\u53ef\u4ee5\u5f00\u59cb") == 1))
    r.append(("\u90e8\u5206\u5177\u5907\u8d77\u59cb\u9636\u6bb5\u4e3a 0", start_stage("\u90e8\u5206\u5177\u5907\uff0c\u5148\u505a 2-4 \u5468\u51c6\u5907\u671f") == 0))
    r.append(("\u4e0d\u5177\u5907\u8d77\u59cb\u9636\u6bb5\u4e3a -1", start_stage("\u4e0d\u5177\u5907\uff0c\u6682\u4e0d\u5f00\u59cb\u6216\u5148\u54a8\u8be2\u513f\u79d1\u533b\u751f") == -1))

    _, s = build_report({"age_months": 24, "signals": all_keys, "dry_hours": 3})
    r.append(("\u5b8c\u6574\u6837\u4f8b\u4e0d\u89e6\u53d1\u7ea2\u7ebf", s["blocked"] is False))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u5224\u5b9a\u4e3a\u4fe1\u53f7\u5145\u8db3", s["readiness"] == "\u4fe1\u53f7\u5145\u8db3\uff0c\u53ef\u4ee5\u5f00\u59cb"))
    r.append(("\u6837\u4f8b\u4e0d\u63d0\u4f9b\u836f\u7269", s["medication_provided"] is False))
    r.append(("\u6837\u4f8b\u4e0d\u4e0b\u8bca\u65ad\u7ed3\u8bba", s["diagnosis_provided"] is False))
    r.append(("\u9636\u6bb5\u8ba1\u5212\u542b 4 \u9879", len(s["stage_plan"]) == 4))

    _, s2 = build_report({"age_months": 26, "signals": all_keys, "red_flags": ["blood_in_stool"]})
    r.append(("\u547d\u4e2d\u8840\u4fbf\u76f4\u63a5\u963b\u65ad", s2["blocked"] is True))
    r.append(("\u963b\u65ad\u65f6\u4e0d\u7ed9\u9636\u6bb5\u8ba1\u5212", s2["stage_plan"] == []))
    r.append(("\u963b\u65ad\u65f6\u5224\u5b9a\u4e3a\u8f6c\u8bca\u4f18\u5148", s2["readiness"] == "\u8f6c\u8bca\u4f18\u5148"))

    _, s3 = build_report({"age_months": 24, "signals": all_keys, "stage": 2})
    r.append(("\u6307\u5b9a\u9636\u6bb5\u53ea\u8f93\u51fa 1 \u9879", len(s3["stage_plan"]) == 1))
    r.append(("\u6307\u5b9a\u9636\u6bb5\u540d\u79f0\u6b63\u786e", s3["stage_plan"][0] == "\u63d0\u793a\u8bed\u4e0e\u63d0\u524d\u9884\u544a"))

    txt, _ = build_report({"age_months": 24, "signals": all_keys})
    r.append(("\u8f93\u51fa\u542b\u56db\u7981\u6b62\u4e2d\u7684\u6253\u5c41\u80a1\u7981\u4ee4", "\u6253\u5c41\u80a1" in txt))
    r.append(("\u8f93\u51fa\u542b\u628a\u5c3f\u7981\u4ee4", "\u628a\u5c4e\u628a\u5c3f" in txt))
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
    parser = argparse.ArgumentParser(description="\u5e7c\u513f\u5982\u5395\u8bad\u7ec3\u51c6\u5907\u5ea6\u8bc4\u4f30\u4e0e\u9636\u6bb5\u6392\u671f\u751f\u6210\u5de5\u5177")
    parser.add_argument("--file", help="\u8f93\u5165 JSON \u6587\u4ef6\u8def\u5f84\uff08UTF-8\uff09")
    parser.add_argument("--stage", help="\u53ea\u8f93\u51fa\u67d0\u4e00\u9636\u6bb5\u8ba1\u5212\uff0c\u53d6\u503c 1-4")
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
    if args.stage:
        data["stage"] = args.stage

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
