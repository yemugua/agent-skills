# -*- coding: utf-8 -*-
"""\u538b\u75d5\u53d7\u538b\u98ce\u9669\u8bc4\u4f30\u4e0e\u7ffb\u8eab\u95f4\u9694\u751f\u6210\u5de5\u5177\u3002

\u7528\u6cd5:
  python pressure_ulcer_plan.py --file case.json [--json]
  python pressure_ulcer_plan.py --selftest

\u672c\u5de5\u5177\u4e0d\u7ed9\u836f\u54c1\u3001\u4e0d\u7ed9\u6362\u836f\u65b9\u6848\u3001\u4e0d\u505a\u6b63\u5f0f\u5206\u671f\u8bca\u65ad\u3002
"""
import argparse
import io
import json
import os
import sys

RISK_DIMS = [
    ("immobile", "V1 \u6d3b\u52a8\u53d7\u9650", "\u4e0d\u80fd\u81ea\u4e3b\u7ffb\u8eab\u6216\u8f6c\u79fb\uff0c\u9700\u4ed6\u4eba\u534f\u52a9"),
    ("unconscious", "V2 \u610f\u8bc6\u969c\u788d", "\u610f\u8bc6\u4e0d\u6e05\u6216\u6df1\u5ea6\u9547\u9759\uff0c\u4e0d\u80fd\u8868\u8fbe\u4e0d\u9002"),
    ("red_skin", "V3 \u76ae\u80a4\u5df2\u53d1\u7ea2\u6216\u7834\u635f", "\u4efb\u4e00\u53d7\u538b\u90e8\u4f4d\u5df2\u8fbe L1 \u53ca\u4ee5\u4e0a"),
    ("incontinence", "V4 \u5927\u5c0f\u4fbf\u5931\u7981", "\u6709\u5c3f\u5931\u7981\u3001\u4fbf\u5931\u7981\u6216\u5c3f\u57ab\u957f\u671f\u6f6e\u6e7f"),
    ("poor_intake", "V5 \u6444\u5165\u4e0d\u8db3", "\u98df\u6b32\u5dee\u3001\u8fdb\u98df\u91cf\u51cf\u5c11\u3001\u4f53\u91cd\u4e0b\u964d"),
    ("low_weight", "V6 \u4f4e\u4f53\u91cd\u6216\u6c34\u80bf", "\u4f53\u91cd\u660e\u663e\u504f\u4f4e\u6216\u5168\u8eab\u3001\u4e0b\u80bf\u6c34\u80bf"),
]

STAGES = [
    ("l0", "L0", "\u76ae\u80a4\u5b8c\u597d", "\u53d7\u538b\u90e8\u4f4d\u76ae\u80a4\u5b8c\u6574\uff0c\u65e0\u989c\u8272\u6539\u53d8",
     "\u9884\u9632\u4e3a\u4e3b\uff0c\u6309\u98ce\u9669\u6863\u4f4d\u6267\u884c\u7ffb\u8eab\u51cf\u538b"),
    ("l1", "L1", "\u538b\u4e4b\u892a\u8272\u7684\u7ea2\u6591", "\u5c40\u90e8\u53d1\u7ea2\uff0c\u624b\u6307\u6309\u538b\u540e\u53d8\u767d\uff0c\u677e\u624b\u6062\u590d\u7ea2\u8272",
     "\u7acb\u5373\u52a0\u5f3a\u51cf\u538b\uff0c\u505c\u6b62\u8be5\u90e8\u4f4d\u53d7\u538b"),
    ("l2", "L2", "\u538b\u4e4b\u4e0d\u892a\u8272\u7684\u7ea2\u6591", "\u53d1\u7ea2\u6301\u7eed\u5b58\u5728\uff0c\u6309\u538b\u4e0d\u892a\u8272",
     "\u51cf\u538b\u5e76\u901a\u77e5\u533b\u62a4\uff0c\u4e0d\u6309\u6469\u4e0d\u63c9\u63e1"),
    ("l3", "L3", "\u6c34\u75b1\u6216\u8868\u76ae\u7834\u635f", "\u51fa\u73b0\u6c34\u75b1\u6216\u8868\u76ae\u7834\u635f\u6e17\u6db2",
     "\u505c\u6b62\u53d7\u538b\uff0c\u8bf7\u533b\u62a4\u8bc4\u4f30\uff0c\u4e0d\u81ea\u884c\u6311\u7834"),
    ("l4", "L4", "\u6d45\u8868\u7834\u6e83", "\u8868\u76ae\u7f3a\u5931\uff0c\u521b\u9762\u6d45\uff0c\u672a\u89c1\u6df1\u5c42\u7ec4\u7ec7",
     "\u8f6c\u8bca\u7531\u533b\u62a4\u5904\u7406"),
    ("l5", "L5", "\u6df1\u90e8\u521b\u9762", "\u521b\u9762\u8f83\u6df1\uff0c\u53ef\u89c1\u8102\u80aa\u3001\u7b4b\u819f\u6216\u53ef\u89e6\u53ca\u9aa8\u5d16",
     "\u7acb\u5373\u5c31\u533b\uff0c\u4e0d\u505a\u5bb6\u5ead\u5904\u7406"),
]

STAGE_ORDER = ["l0", "l1", "l2", "l3", "l4", "l5"]

TURN_TABLE = {
    "high": ("\u9ad8\uff08\u542b\u610f\u8bc6\u969c\u788d\u6216\u5df2\u53d1\u7ea2\u7834\u635f\uff09",
             "\u7ea6 1-2 \u5c0f\u65f6",
             "\u9700\u4e13\u4eba\u8d1f\u8d23\uff0c\u6309\u8868\u6267\u884c\u5e76\u8bb0\u5f55\uff0c\u591c\u95f4\u540c\u6837\u4e0d\u7701"),
    "mid": ("\u4e2d", "\u7ea6 2-3 \u5c0f\u65f6", "\u4fdd\u8bc1\u6bcf\u6b21\u7ffb\u8eab\u786e\u5b9e\u6539\u53d8\u53d7\u529b\u70b9"),
    "low": ("\u4f4e\uff08\u53ef\u81ea\u4e3b\u7ffb\u8eab\uff09", "\u6bcf 2-3 \u5c0f\u65f4\u63d0\u9192\uff0c\u591c\u95f4\u540c\u6837\u4e0d\u7701",
            "\u4ee5\u63d0\u9192\u4e0e\u534f\u52a9\u4e3a\u4e3b"),
}

RED_FLAGS = [
    "bone_visible", "necrosis", "pus_odor", "black_edge",
    "worsening_fast", "no_heal_2w", "fever_chills", "heavy_exudate",
    "uti_signs", "nutrition_down", "painful_numb", "weight_bearing_site",
]

RED_FLAG_TEXT = {
    "bone_visible": "\u521b\u9762\u6df1\u8fbe\u9aa8\u9762\u3001\u53ef\u89c1\u7b4b\u819f\u6216\u53ef\u89e6\u53ca\u9aa8\u5d16",
    "necrosis": "\u521b\u9762\u5185\u6709\u574f\u6b7b\u7ec4\u7ec7\u3001\u7126\u7622\u3001\u8111\u6db2\u6216\u660e\u663e\u6076\u82b3",
    "pus_odor": "\u51fa\u73b0\u8111\u6db2\u6216\u660e\u663e\u6076\u82b3",
    "black_edge": "\u521b\u7f18\u53d1\u9ed1\u3001\u53d1\u7d2b\u6216\u56f4\u7ed5\u76ae\u80a4\u7ea2\u80bf\u70ed\u75db\u8fc5\u901f\u6269\u5c55",
    "worsening_fast": "\u4e24\u5929\u5185\u521b\u9762\u660e\u663e\u6269\u5927",
    "no_heal_2w": "\u4e24\u5468\u5b8c\u5168\u4e0d\u89c1\u6536\u53e3\u8ff9\u8c61",
    "fever_chills": "\u4f34\u53d1\u70ed\u3001\u5bd2\u6218\u3001\u610f\u8bc6\u6539\u53d8\u6216\u8840\u538b\u4e0b\u964d",
    "heavy_exudate": "\u6e17\u6db2\u91cf\u5927\u5e76\u4f34\u4f53\u6e29\u5347\u9ad8",
    "uti_signs": "\u4f34\u5c3f\u8def\u611f\u67d3\u8868\u73b0\uff1a\u5c3f\u9891\u5c3f\u75db\u53d1\u70ed\u3001\u5c3f\u6db2\u6d51\u6d4a\u5f02\u5473",
    "nutrition_down": "\u8001\u4eba\u98df\u6b32\u6781\u5dee\u3001\u4f53\u91cd\u5feb\u901f\u4e0b\u964d\u3001\u4e25\u91cd\u8d2b\u8840\u6216\u6c34\u80bf",
    "painful_numb": "\u75bc\u75db\u5267\u70c8\u4f46\u5bf9\u89e6\u78b0\u65e0\u53cd\u5e94",
    "weight_bearing_site": "\u7834\u6e83\u4f4d\u4e8e\u8db3\u8ddf\u3001\u9ab9\u9aa8\u6216\u9ac2\u90e8\u7b49\u627f\u91cd\u9aa8\u51f2\u5904",
}

BODY_POINTS = {
    "supine": ["\u9ab9\u5c3e\u90e8", "\u8db3\u8ddf", "\u80a9\u80db", "\u6795\u90e8", "\u810a\u67f1\u4e24\u4fa7", "\u4e0a\u81c2"],
    "side": ["\u8db3\u8ddf", "\u9ac2\u90e8\u5916\u4fa7", "\u80a9\u80db", "\u6795\u90e8", "\u819d\u4e0e\u8e1d\u5185\u5916\u4fa7", "\u8033\u7ffc"],
    "sitting": ["\u5c3e\u9aa8", "\u5750\u9aa8\u7ed3\u8282", "\u60ac\u5782\u8db3"],
    "foot": ["\u8db3\u8ddf\uff08\u7a7f\u978b\u65f6\u5bb9\u6613\u6f0f\u67e5\uff09", "\u8db3\u8db3\u95f4", "\u8db3\u5916\u8e1d", "\u8db3\u5f27"],
}

POSITION_POINTS = [
    "\u4fa7\u5367\u65f6\u5934\u4e0e\u9888\u4e4b\u95f4\u57ab\u6795\uff0c\u907f\u514d\u9888\u90e8\u60ac\u7a7a",
    "\u4fa7\u5367\u65f6\u4e0a\u4fa7\u80a2\u4f53\u7f6e\u4e8e\u80f8\u524d\uff0c\u524d\u81c2\u4e0e\u4e0a\u81c2\u4e4b\u95f4\u653e\u8f6f\u6795\u627f\u6258",
    "\u4e24\u817f\u95f4\u5939\u6795\uff0c\u9632\u6b62\u4e0a\u4fa7\u819d\u538b\u8feb\u4e0b\u4fa7\u9ac2\u90e8\u4e0e\u8e1d\u90e8\u53e0\u538b",
    "\u8db3\u8ddf\u60ac\u7a7a\uff0c\u8db3\u8ddf\u4e0b\u57ab\u8f6f\u5377\u6216\u8ba9\u8db3\u8ddf\u79bb\u5f00\u5e8a\u9762",
    "\u5750\u4f4d\u65f6\u6bcf 30-60 \u5206\u949f\u51cf\u538b\u4e00\u6b21",
    "\u642c\u8fd0\u65f6\u62ac\u800c\u4e0d\u62d6\u62fd\uff0c\u62d6\u62fd\u4f1a\u4ea7\u751f\u526a\u5207\u529b",
]

NUTRITION = [
    "\u6bcf\u9910\u6709\u86cb\u767d\u6765\u6e90\uff0c\u5206\u6b21\u5c11\u91cf\u591a\u6b21\u4f18\u4e8e\u4e00\u6b21\u5927\u91cf",
    "\u4e09\u9910\u52a0 1-2 \u6b21\u52a0\u9910\uff0c\u51cf\u5c11\u56e0\u6ca1\u80a5\u53e3\u800c\u6574\u9910\u4e0d\u5403",
    "\u4e0d\u7528\u996d\u6c64\u4ee3\u66ff\u5403\u996d\uff0c\u6c64\u6c34\u8425\u517b\u5bc6\u5ea6\u4f4e",
    "\u767d\u5929\u5206\u6b21\u996e\u6c34\uff0c\u4e0d\u56e0\u6015\u5931\u7981\u800c\u9650\u5236\u996e\u6c34",
    "\u4e0d\u81ea\u884c\u5927\u5242\u91cf\u8865\u5145\u86cb\u767d\u7c89\u6216\u8425\u517b\u5242",
    "\u8fde\u7eed 2 \u5468\u4f53\u91cd\u4e0b\u964d\u6216\u8fdb\u98df\u91cf\u660e\u663e\u4e0d\u8db3\u65f6\u4ea4\u533b\u751f\u6216\u4e34\u5e8a\u8425\u517b\u4e13\u4e1a\u4eba\u5458\u8bc4\u4f30",
]

INCONTINENCE = [
    "\u5b9a\u65f6\u63d0\u9192\u5e76\u534f\u52a9\u4e0a\u5395\u6240\uff0c\u51cf\u5c11\u957f\u671f\u4f7f\u7528\u5c3f\u57ab",
    "\u5c3f\u57ab\u6e7f\u6216\u810f\u7acb\u5373\u66f4\u6362\uff0c\u4e0d\u7b49\u4e0b\u4e00\u6b21\u66f4\u6362\u65f6\u95f4",
    "\u6bcf\u6b21\u5931\u7981\u540e\u7528\u6e29\u6c34\u4e0e\u6e29\u548c\u6e05\u6d01\u5242\u6e05\u6d17\uff0c\u8f7b\u62cd\u5438\u5e72\uff0c\u4e0d\u7528\u529b\u64e6",
    "\u6e05\u6d01\u540e\u786e\u4fdd\u76ae\u80a4\u5e72\u71e5\uff0c\u6f6e\u6e7f\u73af\u5883\u662f\u538b\u75d5\u63a8\u624b\u4e4b\u4e00",
    "\u4f7f\u7528\u9694\u79bb\u6f6e\u6e7f\u7684\u62a4\u7406\u57ab\u6216\u6577\u6599\uff0c\u4f46\u4fdd\u6301\u900f\u6c14",
    "\u8bb0\u5f55\u5931\u7981\u6b21\u6570\u4e0e\u6bcf\u65e5\u5c3f\u91cf",
]

FORBIDDEN = [
    "\u7981\u6b62\u6309\u6469\u3001\u63c9\u63e1\u53d1\u7ea2\u7684\u76ae\u80a4",
    "\u7981\u6b62\u7528\u529b\u6309\u538b\u9aa8\u51f2\u90e8\u4f4d\u6d4b\u8bd5",
    "\u7981\u6b62\u81ea\u884c\u6311\u7834\u6c34\u75b1",
    "\u7981\u6b62\u81ea\u884c\u5207\u5f00\u5f15\u6d41",
    "\u7981\u6b62\u7528\u5200\u6216\u526a\u5200\u526a\u9664\u9ed1\u8272\u7ec4\u7ec7",
    "\u7981\u6b62\u6d82\u62b9\u504f\u65b9\u3001\u8349\u836f\u3001\u7259\u818f\u3001\u9171\u6cb9\u7b49",
    "\u7981\u6b62\u81ea\u884c\u4f7f\u7528\u6297\u751f\u7d20\u8f6f\u818f",
    "\u7981\u6b62\u62d6\u62fd\u642c\u52a8\u75c5\u4eba",
]

METRICS = [
    ("\u7ffb\u8eab\u6b21\u6570\u4e0e\u65f6\u95f4", "\u6bcf\u6b21", "\u5224\u65ad\u65b9\u6848\u6267\u884c\u7387"),
    ("\u76ae\u80a4 L \u7ea7\u522b\uff08\u5206\u90e8\u4f4d\uff09", "\u6bcf\u65e5", "\u5224\u65ad\u8d8b\u52bf"),
    ("\u521b\u9762\u957f \u00d7 \u5bbd\uff08\u5398\u7c73\uff09", "\u6bcf 2 \u5929", "\u5224\u65ad\u662f\u5426\u6536\u53e3"),
    ("\u6e17\u6db2\u91cf\u4e0e\u6c14\u5473\u53d8\u5316", "\u6bcf\u65e5", "\u5224\u65ad\u6709\u65e0\u611f\u67d3"),
    ("\u4f53\u91cd\uff08\u516c\u65a4\uff09", "\u6bcf\u5468", "\u5224\u65ad\u8425\u517b\u8d8b\u52bf"),
    ("\u6bcf\u65e5\u996e\u6c34\u91cf\u4e0e\u8fdb\u98df\u91cf", "\u6bcf\u65e5", "\u5224\u65ad\u8425\u517b\u4e0e\u6c34\u5206"),
    ("\u5c3f\u91cf\u4e0e\u5931\u7981\u6b21\u6570", "\u6bcf\u65e5", "\u5224\u65ad\u5931\u7981\u7ba1\u7406\u6548\u679c"),
    ("\u4f53\u6e29", "\u6bcf\u65e5", "\u65e9\u671f\u53d1\u73b0\u611f\u67d3"),
]

TURN_NOTE = [
    "\u4e0a\u8868\u662f\u53c2\u8003\u533a\u95f4\uff0c\u4e0d\u662f\u6807\u51c6\u7b54\u6848",
    "\u5177\u4f53\u7ffb\u8eab\u95f4\u9694\u4ee5\u533b\u62a4\u4eba\u5458\u7684\u8bc4\u4f30\u548c\u5efa\u8bae\u4e3a\u51c6",
    "\u6bcf\u6b21\u7ffb\u8eab\u8981\u770b\u5168\u90e8\u9ad8\u53d1\u90e8\u4f4d\uff0c\u4e0d\u662f\u53ea\u7ffb\u4e00\u6b21\u5c31\u7b97\u5b8c\u6210",
    "\u591c\u95f4\u4e0e\u7761\u7720\u65f6\u6bb5\u6700\u5bb9\u6613\u6f0f\uff0c\u5fc5\u987b\u7eb3\u5165\u6392\u73ed",
    "\u9ad8\u98ce\u9669\u60a3\u8005\u7761\u7720\u8d85\u8fc7 3 \u5c0f\u65f6\u672a\u7ffb\u8eab\u5c5e\u6267\u884c\u4e0d\u5230\u4f4d\uff0c\u5e94\u7acb\u5373\u8865\u7ffb\u5e76\u7ea0\u6b63\u6392\u73ed",
]


def risk_level(hits):
    h = set(hits)
    if "immobile" in h or "unconscious" in h or "red_skin" in h:
        return "high"
    extra = len([k for k in ("incontinence", "poor_intake", "low_weight") if k in h])
    if extra >= 2:
        return "mid"
    return "low"


def validate_risk(raw):
    valid = dict((k, v) for k, v, _c in RISK_DIMS)
    good, bad = [], []
    for k in list(raw or []):
        if k in valid:
            good.append(k)
        else:
            bad.append(k)
    return good, bad


def stage_meta(key):
    for k, code, name, sign, action in STAGES:
        if k == key:
            return code, name, sign, action
    return key, key, "", ""


def max_stage(stage_keys):
    best = "l0"
    best_i = -1
    for k in stage_keys:
        if k in STAGE_ORDER and STAGE_ORDER.index(k) > best_i:
            best_i = STAGE_ORDER.index(k)
            best = k
    return best


def build_plan(level, top_stage):
    lines = []
    label, interval, note = TURN_TABLE[level]
    lines.append("\u98ce\u9669\u6863\u4f4d\uff1a%s" % label)
    lines.append("\u7ffb\u8eab\u95f4\u9694\u53c2\u8003\uff1a%s" % interval)
    lines.append("\u5907\u6ce8\uff1a%s" % note)
    lines.append("")
    lines.append("\u4e00\u5e76\u7684\u7ffb\u8eab\u95f4\u9694\u53e3\u5f84\uff1a")
    for t in TURN_NOTE:
        lines.append("  - " + t)
    lines.append("")
    lines.append("\u9ad8\u53d1\u90e8\u4f4d\u6e05\u5355\uff08\u6bcf\u6b21\u7ffb\u8eab\u9010\u4e2a\u770b\uff09\uff1a")
    for pos, pts in BODY_POINTS.items():
        lines.append("  %s\uff1a%s" % (pos, "\u3001".join(pts)))
    lines.append("")
    lines.append("\u4f53\u4f4d\u6446\u653e\u8981\u70b9\uff1a")
    for p in POSITION_POINTS:
        lines.append("  - " + p)
    lines.append("")
    lines.append("\u8425\u517b\u4e0e\u6c34\u5206\u7ba1\u7406\uff08\u539f\u5219\u5c42\u9762\uff09\uff1a")
    for n in NUTRITION:
        lines.append("  - " + n)
    lines.append("")
    lines.append("\u5931\u7981\u7ba1\u7406\uff1a")
    for i in INCONTINENCE:
        lines.append("  - " + i)
    lines.append("")
    lines.append("\u5fc5\u987b\u8bb0\u5f55\u7684\u53ef\u6d4b\u91cf\u6307\u6807\uff1a")
    for name, freq, why in METRICS:
        lines.append("  - %s\uff08%s\uff09\uff1a%s" % (name, freq, why))
    lines.append("")
    lines.append("\u7981\u6b62\u7684\u5bb6\u5ead\u5904\u7406\uff1a")
    for f in FORBIDDEN:
        lines.append("  - " + f)
    lines.append("")
    lines.append("\u5f53\u524d\u89c2\u5bdf\u5230\u7684\u6700\u9ad8\u7ea7\u522b\uff1a%s" % top_stage)
    lines.append("\u6b63\u5f0f\u5206\u671f\u8bca\u65ad\u4ee5\u533b\u62a4\u4eba\u5458\u5224\u65ad\u4e3a\u51c6\uff0c\u672c\u5de5\u5177\u4e0d\u505a\u5206\u671f\u8bca\u65ad\u3002")
    return lines


def build_report(data):
    raw_risk = list(data.get("risk", []))
    stage = data.get("stage", "l0")
    flags = list(data.get("red_flags", []))
    hours = data.get("hours_start", 0)

    lines = []
    lines.append("=" * 66)
    lines.append("\u538b\u75d5\u53d7\u538b\u98ce\u9669\u8bc4\u4f30\u4e0e\u7ffb\u8eab\u95f4\u9694\u751f\u6210")
    lines.append("=" * 66)
    lines.append("\u8d77\u59cb\u89c2\u5bdf\u65f6\u957f\uff1a%g \u5c0f\u65f6   \u6307\u5b9a\u89c2\u5bdf\u5230\u7684\u7ea7\u522b\uff1a%s"
                 % (float(hours or 0), stage_meta(stage)[0]))
    lines.append("")

    hit = [f for f in flags if f in RED_FLAGS]
    unknown = [f for f in flags if f not in RED_FLAGS]
    if hit:
        lines.append("[\u8f6c\u8bca] \u5df2\u547d\u4e2d\u4ee5\u4e0b\u60c5\u5f62\uff0c\u505c\u6b62\u5bb6\u5ead\u5904\u7406\uff1a")
        for f in hit:
            lines.append("  ! " + RED_FLAG_TEXT[f])
        lines.append("")
        lines.append("  \u672c\u5de5\u5177\u4e0d\u7ed9\u836f\u54c1\u3001\u4e0d\u7ed9\u6362\u836f\u65b9\u6848\u3001\u4e0d\u7ed9\u6e05\u521b\u65b9\u6848\u3002")
        lines.append("=" * 66)
        return "\n".join(lines), {
            "blocked": True,
            "refer_required": True,
            "red_flags": hit,
            "unknown_flags": unknown,
            "medication_provided": False,
            "dressing_provided": False,
            "staging_diagnosis_provided": False,
        }

    good, bad = validate_risk(raw_risk)
    if bad:
        lines.append("[\u63d0\u793a] \u672a\u8bc6\u522b\u7684\u98ce\u9669\u7ef4\u5ea6\u6807\u8bb0\u5df2\u5ffd\u7565\uff1a" + "\u3001".join(bad))
        lines.append("")

    level = risk_level(good)
    top = max_stage([stage])

    lines.append("[\u4e00] \u53d7\u538b\u98ce\u9669\u516d\u7ef4\u6838\u67e5")
    for k, label, crit in RISK_DIMS:
        mark = "[\u6709]" if k in good else "[\u65e0]"
        lines.append("  %s %s\uff5c%s" % (mark, label, crit))
    lines.append("")

    lines.append("[\u4e8c] \u5206\u7ea7\u5c55\u793a\uff08\u63cf\u8ff0\u6027\u53e3\u5f84\uff0c\u975e\u6b63\u5f0f\u5206\u671f\u8bca\u65ad\uff09")
    for k, code, name, sign, action in STAGES:
        mark = "[\u5f53\u524d]" if k == top else ""
        lines.append("  %s %s %s\uff5c%s" % (mark, code, name, sign))
        lines.append("      \u5bb6\u5ead\u5904\u7406\u5b9a\u4f4d\uff1a" + action)
    lines.append("")

    lines.append("[\u4e09] \u7ffb\u8eab\u4e0e\u51cf\u538b\u65b9\u6848")
    for line in build_plan(level, stage_meta(top)[0]):
        lines.append("  " + line if line else "")

    lines.append("")
    lines.append("[\u56db] \u5fc5\u987b\u8f6c\u8bca\u7684\u60c5\u5f62\uff08\u51fa\u73b0\u4efb\u4e00\u9879\u7acb\u5373\u5c31\u533b\uff09")
    for k in RED_FLAGS:
        lines.append("  - " + RED_FLAG_TEXT[k])
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u63cf\u8ff0\u6027\u89c2\u5bdf\u4e0e\u7ffb\u8eab\u51cf\u538b\u53c2\u8003\uff0c\u4e0d\u6784\u6210\u533b\u7597\u610f\u89c1\u3002")
    lines.append("\u6b63\u5f0f\u5206\u671f\u4e0e\u6362\u836f\u65b9\u6848\u4ee5\u533b\u62a4\u4eba\u5458\u5224\u65ad\u4e3a\u51c6\uff0c\u4ee5\u6700\u65b0\u7248\u76f8\u5173\u6307\u5357\u4e3a\u51c6\u3002")
    lines.append("=" * 66)

    summary = {
        "blocked": False,
        "unknown_flags": unknown,
        "risk_level": level,
        "risk_hits": good,
        "top_stage": stage_meta(top)[0],
        "turn_interval_reference": TURN_TABLE[level][1],
        "interval_is_reference_only": True,
        "medication_provided": False,
        "dressing_provided": False,
        "debridement_provided": False,
        "staging_diagnosis_provided": False,
        "healing_time_promised": False,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("\u98ce\u9669\u7ef4\u5ea6\u4e3a 6 \u9879", len(RISK_DIMS) == 6))
    r.append(("\u63cf\u8ff0\u5206\u7ea7\u4e3a 6 \u7ea7", len(STAGES) == 6))
    r.append(("\u8f6c\u8bca\u60c5\u5f62\u81f3\u5c11 12 \u6761", len(RED_FLAGS) >= 12))
    r.append(("\u7981\u6b62\u5904\u7406\u81f3\u5c11 8 \u6761", len(FORBIDDEN) >= 8))
    r.append(("\u53ef\u6d4b\u91cf\u6307\u6807\u81f3\u5c11 8 \u9879", len(METRICS) >= 8))

    good, bad = validate_risk(["immobile", "oops"])
    r.append(("\u5df2\u8bc6\u522b\u98ce\u9669\u7ef4\u5ea6\u8ba1\u6570\u6b63\u786e", good == ["immobile"]))
    r.append(("\u672a\u8bc6\u522b\u98ce\u9669\u7ef4\u5ea6\u88ab\u8fc7\u6ee4", bad == ["oops"]))

    r.append(("\u65e0\u4efb\u4f55\u547d\u4e2d\u5224\u4e3a\u4f4e\u98ce\u9669", risk_level([]) == "low"))
    r.append(("\u6d3b\u52a8\u53d7\u9650\u5373\u5224\u4e3a\u9ad8\u98ce\u9669", risk_level(["immobile"]) == "high"))
    r.append(("\u610f\u8bc6\u969c\u788d\u5373\u5224\u4e3a\u9ad8\u98ce\u9669", risk_level(["unconscious"]) == "high"))
    r.append(("\u5df2\u53d1\u7ea2\u5373\u5224\u4e3a\u9ad8\u98ce\u9669", risk_level(["red_skin"]) == "high"))
    r.append(("\u4e24\u9879\u52a0\u91cd\u56e0\u7d20\u5224\u4e3a\u4e2d\u98ce\u9669",
              risk_level(["incontinence", "poor_intake"]) == "mid"))
    r.append(("\u4e00\u9879\u52a0\u91cd\u56e0\u7d20\u5224\u4e3a\u4f4e\u98ce\u9669",
              risk_level(["incontinence"]) == "low"))

    r.append(("\u65e0\u6307\u5b9a\u65f6\u53d6\u6700\u4f4e\u7ea7\u522b", max_stage([]) == "l0"))
    r.append(("\u53d6\u591a\u4e2a\u7ea7\u522b\u7684\u6700\u9ad8\u8005", max_stage(["l1", "l3", "l2"]) == "l3"))
    r.append(("\u672a\u77e5\u7ea7\u522b\u4e0d\u5f71\u54cd\u6700\u9ad8\u7ea7\u522b", max_stage(["l2", "zzz"]) == "l2"))

    r.append(("\u9ad8\u98ce\u9669\u7ffb\u8eab\u95f4\u9694\u4e3a 1-2 \u5c0f\u65f4",
              "1-2" in TURN_TABLE["high"][1]))
    r.append(("\u4f4e\u98ce\u9669\u7ffb\u8eab\u95f4\u9694\u4e3a 2-3 \u5c0f\u65f4",
              "2-3" in TURN_TABLE["low"][1]))

    _, s = build_report({"risk": ["immobile"], "stage": "l2"})
    r.append(("\u5b8c\u6574\u6837\u4f8b\u4e0d\u963b\u65ad", s["blocked"] is False))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u5224\u4e3a\u9ad8\u98ce\u9669", s["risk_level"] == "high"))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u6700\u9ad8\u7ea7\u522b\u4e3a L2", s["top_stage"] == "L2"))
    r.append(("\u7ffb\u8eab\u95f4\u9694\u660e\u786e\u4e3a\u53c2\u8003", s["interval_is_reference_only"] is True))
    r.append(("\u4e0d\u7ed9\u836f\u54c1", s["medication_provided"] is False))
    r.append(("\u4e0d\u7ed9\u6362\u836f\u4e0e\u6577\u6599", s["dressing_provided"] is False))
    r.append(("\u4e0d\u7ed9\u6e05\u521b\u65b9\u6848", s["debridement_provided"] is False))
    r.append(("\u4e0d\u505a\u6b63\u5f0f\u5206\u671f\u8bca\u65ad", s["staging_diagnosis_provided"] is False))
    r.append(("\u4e0d\u627f\u8bfa\u6108\u5408\u65f6\u95f4", s["healing_time_promised"] is False))

    _, s2 = build_report({"risk": ["immobile"], "red_flags": ["pus_odor"]})
    r.append(("\u8111\u6db2\u6076\u82b3\u76f4\u63a5\u963b\u65ad", s2["blocked"] is True))
    r.append(("\u963b\u65ad\u65f6\u8981\u6c42\u8f6c\u8bca", s2["refer_required"] is True))
    r.append(("\u963b\u65ad\u65f6\u4e0d\u7ed9\u836f\u54c1", s2["medication_provided"] is False))

    _, s3 = build_report({"risk": [], "stage": "l5"})
    r.append(("\u6df1\u90e8\u521b\u9762\u4e0d\u81ea\u52a8\u963b\u65ad", s3["blocked"] is False))
    r.append(("\u6df1\u90e8\u521b\u9762\u6700\u9ad8\u7ea7\u522b\u4e3a L5", s3["top_stage"] == "L5"))

    txt, _ = build_report({"risk": ["immobile"], "stage": "l2"})
    r.append(("\u8f93\u51fa\u542b\u4ee5\u533b\u62a4\u4eba\u5458\u5224\u65ad\u4e3a\u51c6\u7684\u53e3\u5f84",
              "\u533b\u62a4\u4eba\u5458\u5224\u65ad\u4e3a\u51c6" in txt))
    r.append(("\u8f93\u51fa\u542b\u4e0d\u7b54\u5e94\u63a9\u64e6\u7684\u7ea2\u6591",
              "\u6309\u6469\u3001\u63c9\u63e1" in txt))
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
    parser = argparse.ArgumentParser(description="\u538b\u75d5\u53d7\u538b\u98ce\u9669\u8bc4\u4f30\u4e0e\u7ffb\u8eab\u95f4\u9694\u751f\u6210\u5de5\u5177")
    parser.add_argument("--file", help="\u8f93\u5165 JSON \u6587\u4ef6\u8def\u5f84\uff08UTF-8\uff09")
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
