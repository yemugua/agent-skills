# -*- coding: utf-8 -*-
"""\u5931\u80fd\u8001\u4eba\u7ffb\u8eab\u4e0e\u62cd\u80cc\u65b9\u6848\u751f\u6210\u5de5\u5177\u3002

\u7528\u6cd5:
  python bedridden_turning_plan.py --file case.json [--turn] [--pat] [--json]
  python bedridden_turning_plan.py --selftest

\u672c\u5de5\u5177\u4e0d\u7ed9\u836f\u7269\u3001\u4e0d\u7ed9\u5438\u75f0\u64cd\u4f5c\u3001\u4e0d\u5224\u65ad\u75f0\u91cf\u4e0e\u611f\u67d3\u3002
"""
import argparse
import io
import json
import os
import sys

RISK_DIMS = [
    ("immobile", "\u4e0d\u80fd\u81ea\u4e3b\u7ffb\u8eab\u6216\u8f6c\u79fb", "\u9700\u4ed6\u4eba\u534f\u52a9"),
    ("unconscious", "\u610f\u8bc6\u969c\u788d\u6216\u5b88\u7761", "\u4e0d\u80fd\u53c2\u4e0e\u914d\u5408"),
    ("hemiplegia", "\u504f\u762b\u6216\u4e00\u4fa7\u611f\u89c9\u969c\u788d", "\u60a3\u4fa7\u6446\u653e\u987a\u5e8f\u987b\u6309\u533b\u62a4\u8981\u6c42"),
    ("obesity", "\u660e\u663e\u80a5\u80d6", "\u4f53\u91cd\u589e\u52a0\u538b\u529b"),
    ("edema", "\u6c34\u80bf", "\u6d41\u52a8\u6027\u5dee\uff0c\u5bb9\u6613\u6f0f\u67e5"),
    ("incontinence", "\u5927\u5c0f\u4fbf\u5931\u7981", "\u6f6e\u6e7f\u4e0e\u523a\u6fc0\u52a0\u91cd\u98ce\u9669"),
]

TURN_TABLE = {
    "high": ("\u9ad8", "\u7ea6 1-2 \u5c0f\u65f6",
             "\u9700\u4e13\u4eba\u8d1f\u8d23\uff0c\u6392\u73ed\u8986\u76d6\u591c\u95f4"),
    "mid": ("\u4e2d", "\u7ea6 2-3 \u5c0f\u65f6", "\u4fdd\u8bc1\u6bcf\u6b21\u7ffb\u8eab\u786e\u5b9e\u6539\u53d8\u53d7\u529b\u70b9"),
    "low": ("\u4f4e", "\u6bcf 2-3 \u5c0f\u65f4\u63d0\u9192", "\u4ee5\u63d0\u9192\u4e0e\u534f\u52a9\u4e3a\u4e3b\uff0c\u591c\u95f4\u4e0d\u7701\u7565"),
}

TURN_NOTE = [
    "\u4e0a\u8868\u4e3a\u53c2\u8003\u533a\u95f4\uff0c\u5177\u4f53\u95f4\u9694\u4ee5\u533b\u62a4\u4eba\u5458\u7684\u8bc4\u4f30\u548c\u5efa\u8bae\u4e3a\u51c6",
    "\u6bcf\u6b21\u7ffb\u8eab\u90fd\u8981\u786e\u8ba4\u53d7\u529b\u70b9\u786e\u5b9e\u6539\u53d8\uff0c\u7ffb\u4e86\u8eab\u4f46\u538b\u5728\u540c\u4e00\u5904\u7b49\u4e8e\u6ca1\u7ffb",
    "\u591c\u95f4\u4e0e\u7761\u7720\u65f6\u6bb5\u6700\u5bb9\u6613\u6f0f\uff0c\u5fc5\u987b\u6392\u73ed\u8986\u76d6",
    "\u7ffb\u8eab\u540e\u8981\u68c0\u67e5\u5168\u90e8\u9ad8\u53d1\u90e8\u4f4d\uff0c\u4e0d\u662f\u7ffb\u4e00\u6b21\u5c31\u7b97\u5b8c\u6210",
]

BODY_POINTS = {
    "supine": ["\u9ab9\u5c3e\u90e8", "\u8db3\u8ddf", "\u80a9\u80db", "\u6795\u90e8", "\u810a\u67f1\u4e24\u4fa7", "\u4e0a\u81c2"],
    "side": ["\u8db3\u8ddf", "\u9ac2\u90e8\u5916\u4fa7", "\u80a9\u80db", "\u6795\u90e8", "\u819d\u4e0e\u8e1d\u5185\u5916\u4fa7", "\u8033\u7ffc"],
    "sitting": ["\u5c3e\u9aa8", "\u5750\u9aa8\u7ed3\u8282", "\u60ac\u5782\u8db3"],
}

POSITION_POINTS = [
    "\u4fa7\u5367\u65f6\u4e0a\u4fa7\u4e0a\u80a2\u7f6e\u4e8e\u80f8\u524d\uff0c\u524d\u81c2\u4e0e\u4e0a\u81c2\u4e4b\u95f4\u653e\u8f6f\u6795\u627f\u6258",
    "\u4e24\u817f\u95f4\u5939\u6795\uff0c\u9632\u6b62\u4e0a\u4fa7\u819d\u538b\u8feb\u4e0b\u4fa7\u9ac2\u90e8\u4e0e\u8e1d\u90e8\u53e0\u538b",
    "\u8db3\u8ddf\u60ac\u7a7a\uff0c\u8db3\u8ddf\u4e0b\u57ab\u8f6f\u5377\u6216\u8ba9\u8db3\u8ddf\u79bb\u5f00\u5e8a\u9762",
    "\u5934\u4e0e\u9888\u4e4b\u95f4\u57ab\u6795\uff0c\u907f\u514d\u9888\u90e8\u60ac\u7a7a\u6216\u8fc7\u5ea6\u626d\u8f6c",
    "\u80cc\u90e8\u4e0e\u81c0\u90e8\u4e4b\u95f4\u7528\u8f6f\u6795\u586b\u9699\uff0c\u51cf\u5c11\u80a9\u80db\u4e0e\u9ab9\u5c3e\u53d7\u538b",
    "\u53cc\u811a\u81ea\u7136\u4e0b\u5782\uff0c\u4e0d\u957f\u671f\u9876\u4f4f\u5e8a\u5c3e\u6321\u677f",
    "\u62ac\u800c\u4e0d\u62d6\u62fd\uff1a\u62d6\u62fd\u4ea7\u751f\u526a\u5207\u529b\uff0c\u662f\u538b\u75d5\u7684\u91cd\u8981\u6210\u56e0",
    "\u4e0d\u80fd\u81ea\u4e3b\u7ffb\u8eab\u8005\u7684\u60a3\u4fa7\u6446\u653e\u987a\u5e8f\u987b\u6309\u533b\u62a4\u8981\u6c42\u6267\u884c",
]

ROTATION = "\u57fa\u672c\u8f6e\u6362\uff1a\u4ef0\u5367 \u2192 \u5de6\u4fa7\u5367 \u2192 \u4ef0\u5367 \u2192 \u53f3\u4fa7\u5367 \u2192 \u4ef0\u5367 \u2192 \u5750\u4f4d\uff08\u5982\u53ef\u8010\u53d7\uff09"

PAT_METHOD = [
    ("\u624b\u578b", "\u7a7a\u5fc3\u638c\uff1a\u624b\u638c\u5f2f\u6210\u7897\u72b6\uff0c\u6307\u5c16\u5e76\u62e2\u5fae\u5f2f",
     "\u5b9e\u5fc3\u638c\u62cd\u3001\u63e1\u62f3\u6094\u3001\u6307\u5c16\u6233"),
    ("\u529b\u5ea6", "\u4ee5\u76ae\u80a4\u4e0d\u7ea2\u3001\u4e0d\u75db\u3001\u4e0d\u51fa\u73b0\u745e\u6591\u4e3a\u9650",
     "\u7528\u529b\u8fc7\u731b\u3001\u8d8a\u62cd\u8d8a\u91cd"),
    ("\u65b9\u5411", "\u7531\u4e0b\u5411\u4e0a\u3001\u7531\u5916\u5411\u5185\uff0c\u4ece\u80ba\u5e95\u5411\u80ba\u5c16",
     "\u5411\u4e0b\u62cd\u6216\u5411\u4e2d\u592e\u62cd"),
    ("\u8282\u594f", "\u6bcf\u6b21\u7ea6 3-5 \u5206\u949f\u6216\u4ee5\u8001\u4eba\u8010\u53d7\u4e3a\u9650\uff0c\u6709\u8282\u5f8b",
     "\u4e00\u53e3\u6c14\u62cd\u5f88\u4e45\u4e0d\u770b\u76ae\u80a4"),
    ("\u505c\u987f", "\u6bcf\u62cd\u51e0\u4e0b\u77ed\u6682\u505c\u987f\uff0c\u8ba9\u8001\u4eba\u53ef\u4ee5\u547c\u5438\u4e0e\u54b3\u6e05",
     "\u4e0d\u7559\u610f\u4f7f\u7528\u547c\u5438\u673a\u4f1a"),
]

PAT_AVOID = [
    ("\u810a\u67f1", "\u9707\u8361\u53ef\u80fd\u9020\u6210\u635f\u4f24"),
    ("\u80be\u533a", "\u810a\u90e8\u4e24\u4fa7\u540e\u4e0b\u65b9\uff0c\u51b2\u51fb\u53ef\u9020\u6210\u80be\u810f\u635f\u4f24"),
    ("\u9ac2\u9aa8\u3001\u80a9\u80db\u9aa8\u3001\u9ab9\u9aa8\u7a81\u8d77\u5904", "\u9aa8\u7a81\u5904\u53d7\u51b2\u51fb\u6613\u635f\u4f24"),
    ("\u624b\u672f\u5207\u53e3\u3001\u9aa8\u6298\u90e8\u4f4d", "\u76f4\u63a5\u635f\u4f24"),
    ("\u76ae\u80a4\u7834\u635f\u3001\u538b\u75d5\u521b\u9762\u3001\u75b1\u6591\u5904", "\u52a0\u91cd\u635f\u4f24"),
]

MEAL_WINDOW = [
    ("\u9910\u524d 1 \u5c0f\u65f6\u5185", False, "\u9971\u8179\u6613\u541e\u5410\u8bef\u5438"),
    ("\u9910\u540e 1-2 \u5c0f\u65f6\u5185", False, "\u541e\u5410\u8bef\u5438\u98ce\u9669"),
    ("\u9910\u540e 2 \u5c0f\u65f6\u4ee5\u4e0a\u6216\u9910\u524d 1 \u5c0f\u65f6\u4ee5\u4e0a", True, "\u53ef\u62cd"),
]

CONTRA = [
    "hemoptysis", "rib_fracture", "osteoporosis_risk", "pneumothorax",
    "chest_pain_cough", "resp_distress", "weak_cough_reflex", "unstable_vitals",
]

CONTRA_TEXT = {
    "hemoptysis": "\u54af\u8840\u6216\u75f0\u4e2d\u5e26\u8840",
    "rib_fracture": "\u5df2\u77e5\u6216\u7591\u4f3c\u7684\u808b\u9aa8\u9aa8\u6298\u3001\u80f8\u9aa8\u9aa8\u6298\u3001\u810a\u67f1\u75c5\u53d8",
    "osteoporosis_risk": "\u9aa8\u8d28\u758f\u677e\u7a0b\u5ea6\u660e\u663e\uff0c\u6709\u62cd\u80cc\u81f4\u9aa8\u6298\u98ce\u9669",
    "pneumothorax": "\u6c14\u80f8\u3001\u6c14\u80f8\u503e\u5411\u6216\u8fd1\u671f\u6c14\u80f8\u75c5\u53f2",
    "chest_pain_cough": "\u5267\u70c8\u54b3\u6e05\u5bfc\u81f4\u7684\u80f8\u75db\u3001\u547c\u5438\u56f0\u96be",
    "resp_distress": "\u547c\u5438\u7d27\u6025\u3001\u53d1\u7d2b\u3001\u9f3b\u7ffc\u6247\u52a8\u3001\u8868\u60c5\u75db\u82e6",
    "weak_cough_reflex": "\u54b3\u6e05\u53cd\u5c04\u6d88\u5931\u6216\u660e\u663e\u524a\u5f31\u3001\u541e\u54bd\u529f\u80fd\u5dee\u3001\u8bef\u5438\u53f2\u9891\u7e41",
    "unstable_vitals": "\u751f\u547d\u4f53\u5f81\u4e0d\u7a33\u5b9a\uff1a\u8840\u538b\u4e0b\u964d\u3001\u5fc3\u7387\u5f02\u5e38\u3001\u610f\u8bc6\u6539\u53d8",
}

CONTRA_ACTION = "\u7981\u62cd\uff0c\u7acb\u5373\u5c31\u533b"

CHOKING_SIGNALS = [
    "\u7a81\u7136\u4e0d\u80fd\u8bf4\u8bdd\u6216\u58f0\u97f3\u53d1\u4e0d\u51fa",
    "\u53cc\u624b\u6293\u5584\u3001\u8868\u60c5\u60ca\u6050",
    "\u9762\u8272\u9752\u7d2b\u3001\u53e3\u5507\u53d1\u7d2b",
    "\u54b3\u6e05\u65e0\u58f0",
    "\u547c\u5438\u6025\u901f\u3001\u5594\u54cd\u3001\u541f\u541f",
    "\u8eab\u4f53\u8f6f\u762b\u3001\u610f\u8bc6\u4e22\u5931",
]

CHOKING_FORBID = [
    "\u7ee7\u7eed\u62cd\u80cc\u6216\u62cd\u6253",
    "\u6311\u6316\u53e3\u8154\u3001\u7528\u624b\u6478\u5589\u5499",
    "\u7ed9\u6c34\u3001\u5582\u836f\u3001\u5582\u996d",
    "\u628a\u4eba\u5012\u63d0\u3001\u6296\u52a8",
]

NUTRITION = [
    "\u6bcf\u9910\u6709\u86cb\u767d\u6765\u6e90\uff0c\u5206\u6b21\u5c11\u91cf\u591a\u6b21\u4f18\u4e8e\u4e00\u6b21\u5927\u91cf",
    "\u4e0d\u7528\u996d\u6c64\u4ee3\u66ff\u5403\u996d\uff0c\u6c64\u6c34\u8425\u517b\u5bc6\u5ea6\u4f4e",
    "\u767d\u5929\u5206\u6b21\u996e\u6c34\uff0c\u4e0d\u56e0\u6015\u5931\u7981\u800c\u9650\u5236\u996e\u6c34",
    "\u4e0d\u81ea\u884c\u5927\u5242\u91cf\u8865\u5145\u86cb\u767d\u7c89\u6216\u8425\u517b\u5242",
    "\u8fde\u7eed 2 \u5468\u4f53\u91cd\u4e0b\u964d\u6216\u8fdb\u98df\u91cf\u660e\u663e\u4e0d\u8db3\u65f6\u4ea4\u533b\u751f\u6216\u4e34\u5e8a\u8425\u517b\u4e13\u4e1a\u4eba\u5458\u8bc4\u4f30",
]

INCONTINENCE = [
    "\u5b9a\u65f6\u63d0\u9192\u5e76\u534f\u52a9\u4e0a\u5395\u6240\uff0c\u51cf\u5c11\u957f\u671f\u4f7f\u7528\u5c3f\u57ab",
    "\u5c3f\u57ab\u6e7f\u6216\u810f\u7acb\u5373\u66f4\u6362\uff0c\u4e0d\u7b49\u4e0b\u4e00\u6b21\u66f4\u6362\u65f6\u95f4",
    "\u6bcf\u6b21\u5931\u7981\u540e\u7528\u6e29\u6c34\u4e0e\u6e29\u548c\u6e05\u6d01\u5242\u6e05\u6d17\uff0c\u8f7b\u62cd\u5438\u5e72\uff0c\u4e0d\u7528\u529b\u64e6",
    "\u4f7f\u7528\u9694\u79bb\u6f6e\u6e7f\u7684\u62a4\u7406\u57ab\u6216\u6577\u6599\uff0c\u4f46\u4fdd\u6301\u900f\u6c14",
    "\u89c4\u5f8b\u6392\u4fbf\uff0c\u907f\u514d\u957f\u65f6\u95f4\u7528\u529b\u4e0e\u4fbf\u5757\u538b\u80a1",
]

MED_FINDING = "\u4fdd\u6301\u6e05\u6670\u7684\u65e5\u5fc6\u529b\uff1a\u6253\u5f00\u7b14\u8bb0\u4e0b\u62cd\u80cc\u65f6\u95f4\u3001\u65f6\u957f\u3001\u5e72\u6d01\u4e0e\u91cf\u3001\u5f02\u5e38\u53cd\u5e94\u3001\u76ae\u80a4\u6709\u65e0\u7ea2\u75d5\u6216\u745e\u6591\uff1b\u672a\u5b9e\u65bd\u65f6\u5fc5\u987b\u5199\u6e05\u539f\u56e0\u3002"

TRANSFER_NOTE = [
    "\u4e0a\u6b21\u7ffb\u8eab\u65f6\u95f4\u4e0e\u4e0b\u6b21\u7ffb\u8eab\u65f6\u95f4",
    "\u5f53\u524d\u4f53\u4f4d\u4e0e\u6446\u653e\u662f\u5426\u5230\u4f4d\uff08\u5c24\u5176\u60a3\u4fa7\u4e0a\u80a2\u4e0e\u8db3\u8ddf\uff09",
    "\u76ae\u80a4\u5404\u90e8\u4f4d L \u7ea7\u522b\u4e0e\u53d8\u5316",
    "\u62cd\u80cc\u662f\u5426\u5b9e\u65bd\u3001\u6709\u65e0\u7981\u5fcc\u3001\u6709\u65e0\u5f02\u5e38\u53cd\u5e94",
    "\u4e0a\u6b21\u8fdb\u98df\u65f6\u95f4\u4e0e\u4e0b\u6b21\u8fdb\u98df\u65f6\u95f4",
    "\u6392\u6f8e\u4e0e\u5931\u7981\u60c5\u51b5",
    "\u9700\u4e0b\u4e00\u73ed\u7279\u522b\u6ce8\u610f\u7684\u4e8b\u9879",
]


def risk_level(hits):
    h = set(hits)
    if "immobile" in h or "unconscious" in h:
        return "high"
    if len([k for k in ("hemiplegia", "obesity", "edema", "incontinence") if k in h]) >= 2:
        return "mid"
    if h:
        return "mid"
    return "low"


def validate_list(raw, valid_keys):
    good, bad = [], []
    for k in list(raw or []):
        if k in valid_keys:
            good.append(k)
        else:
            bad.append(k)
    return good, bad


def meal_ok(hours):
    h = float(hours or 0)
    if h < 0:
        return False, "\u8ddd\u8fdb\u98df\u65f6\u957f\u4e3a\u8d1f\uff0c\u65f6\u95f4\u4e0d\u660e\u786e\uff0c\u672c\u8f6e\u4e0d\u62cd"
    if h < 1:
        return False, "\u9910\u524d 1 \u5c0f\u65f6\u5185\uff0c\u9971\u8179\u6613\u541e\u5410\u8bef\u5438"
    if h < 2:
        return False, "\u9910\u540e 1-2 \u5c0f\u65f6\u5185\uff0c\u541e\u5410\u8bef\u5438\u98ce\u9669"
    return True, "\u7b26\u5408\u65f6\u95f4\u7a97\uff0c\u53ef\u62cd"


def build_turn_plan(level, hits):
    lines = []
    label, interval, require = TURN_TABLE[level]
    lines.append("\u53d7\u538b\u98ce\u9669\u6863\u4f4d\uff1a%s" % label)
    lines.append("\u7ffb\u8eab\u95f4\u9694\u53c2\u8003\uff1a%s" % interval)
    lines.append("\u8981\u6c42\uff1a%s" % require)
    lines.append("")
    lines.append("\u7ffb\u8eab\u95f4\u9694\u53e3\u5f84\uff1a")
    for t in TURN_NOTE:
        lines.append("  - " + t)
    lines.append("")
    lines.append("\u4f53\u4f4d\u8f6e\u6362\uff1a" + ROTATION)
    lines.append("")
    lines.append("\u9ad8\u53d1\u90e8\u4f4d\u6e05\u5355\uff08\u6bcf\u6b21\u7ffb\u8eab\u9010\u4e2a\u770b\uff09\uff1a")
    for pos, pts in BODY_POINTS.items():
        lines.append("  %s\uff1a%s" % (pos, "\u3001".join(pts)))
    lines.append("")
    lines.append("\u4f53\u4f4d\u6446\u653e\u4e0e\u642c\u62fd\u8981\u70b9\uff1a")
    for p in POSITION_POINTS:
        lines.append("  - " + p)
    lines.append("")
    lines.append("\u538b\u75d5\u9884\u9632\u7684\u53e0\u52a0\u63aa\u65bd\uff08\u4e0d\u80fd\u53ea\u9760\u7ffb\u8eab\uff09\uff1a")
    lines.append("  1. \u5b9a\u65f6\u7ffb\u8eab")
    lines.append("  2. \u5408\u9002\u7684\u51cf\u538b\u6885\u57ab\u6216\u5750\u57ab\uff08\u4e0d\u66ff\u4ee3\u7ffb\u8eab\uff09")
    lines.append("  3. \u4f53\u4f4d\u6446\u653e\u4e0e\u652f\u6491")
    lines.append("  4. \u907f\u514d\u7275\u62fd\u62d6\u62fd")
    lines.append("  5. \u4fdd\u6301\u76ae\u80a4\u6e05\u6d01\u5e72\u71e5")
    lines.append("  6. \u8425\u517b\u4e0e\u6c34\u5206\u652f\u6301")
    lines.append("  7. \u5931\u7981\u7ba1\u7406")
    lines.append("  8. \u6392\u4fbf\u7ba1\u7406")
    lines.append("  9. \u76d1\u6d4b\u4e0e\u8bb0\u5f55")
    lines.append("")
    lines.append("\u4f53\u80a4\u6446\u653e\uff1a")
    for p in POSITION_POINTS[1:4]:
        lines.append("  - " + p)
    return lines


def build_pat_plan(conta_hits, meal_flag):
    lines = []
    lines.append("\u62cd\u80cc\u624b\u6cd5\u4e0e\u53c2\u6570\uff1a")
    for name, right, wrong in PAT_METHOD:
        lines.append("  %s\uff1a%s" % (name, right))
        lines.append("      \u4e0d\u8981\uff1a" + wrong)
    lines.append("")
    lines.append("\u65b9\u5411\uff1a\u7531\u4e0b\u5411\u4e0a\u3001\u7531\u5916\u5411\u5185\uff0c\u4ece\u80ba\u5e95\u5411\u80ba\u5c16\u3002")
    lines.append("")
    lines.append("\u7981\u62cd\u533a\u57df\uff1a")
    for area, why in PAT_AVOID:
        lines.append("  - %s\uff1a%s" % (area, why))
    lines.append("")
    lines.append("\u65f6\u95f4\u7a97\uff08\u4e0d\u53ef\u8d8a\u8fc7\uff09\uff1a")
    for when, ok, why in MEAL_WINDOW:
        mark = "\u53ef\u62cd" if ok else "\u4e0d\u62cd"
        lines.append("  %s\uff1a%s" % (mark, when))
    lines.append("")
    lines.append("\u516b\u9879\u62cd\u80cc\u7981\u5fcc\uff08\u547d\u4e2d\u5373\u505c\u6b62\u5e76\u5c31\u533b\uff09\uff1a")
    if conta_hits:
        for k in conta_hits:
            lines.append("  ! \u5df2\u547d\u4e2d\uff1a" + CONTRA_TEXT[k])
    else:
        for k in CONTRA:
            lines.append("  - " + CONTRA_TEXT[k])
    lines.append("  \u5904\u7f6e\uff1a" + CONTRA_ACTION)
    lines.append("")
    lines.append("\u53e6\u52a0\u4e00\u6761\uff1a\u54b3\u75f0\u540e\u7a81\u53d1\u547c\u5438\u56f0\u96be\u6216\u7591\u4f3c\u5f02\u7269\u6863\u963b \u2014\u2014 \u8fd9\u662f\u7a7a\u6b7b\uff0c\u4e0d\u662f\u6392\u75f0\uff0c\u7acb\u5373\u505c\u6b62\u5e76\u6025\u6551\u3002")
    lines.append("")
    lines.append("\u7a7a\u6b7b\u98ce\u9669\u9884\u8b66\u4fe1\u53f7\uff1a")
    for s in CHOKING_SIGNALS:
        lines.append("  - " + s)
    lines.append("")
    lines.append("\u7a7a\u6b7b\u5904\u7f6e\u7684\u7edd\u5bf9\u7981\u6b62\uff1a")
    for f in CHOKING_FORBID:
        lines.append("  - " + f)
    lines.append("")
    lines.append("\u62cd\u80cc\u4fdd\u8bc1\u79d1\u5b66\uff1a" + MED_FINDING)
    lines.append("")
    lines.append("\u6838\u5fc3\u8fb9\u754c\uff1a\u672c\u5de5\u5177\u4e0d\u7ed9\u836f\u7269\u4e0e\u96fe\u5316\u65b9\u6848\uff0c\u4e0d\u7ed9\u5438\u75f0\u64cd\u4f5c\uff0c\u4e0d\u5224\u65ad\u75f0\u91cf\u4e0e\u611f\u67d3\u3002")
    return lines


def build_report(data):
    raw_risk = list(data.get("risk", []))
    raw_contra = list(data.get("contraindication", []))
    flags = list(data.get("red_flags", []))
    meal = data.get("hours_since_meal", 0)
    turn_min = data.get("minutes_since_turn", 0)
    only = data.get("mode", "")

    lines = []
    lines.append("=" * 66)
    lines.append("\u5931\u80fd\u8001\u4eba\u7ffb\u8eab\u4e0e\u62cd\u80cc\u65b9\u6848")
    lines.append("=" * 66)
    lines.append("\u8ddd\u4e0a\u6b21\u8fdb\u98df\uff1a%g \u5c0f\u65f6   \u8ddd\u4e0a\u6b21\u7ffb\u8eab\uff1a%g \u5206\u949f"
                 % (float(meal or 0), float(turn_min or 0)))
    lines.append("")

    hit = [f for f in flags if f in CONTRA]
    unknown = [f for f in flags if f not in CONTRA]
    if hit:
        lines.append("[\u7ea2\u7ebf] \u5df2\u547d\u4e2d\u62cd\u80cc\u7981\u5fcc\uff0c\u505c\u6b62\u64cd\u4f5c\u5e76\u5c31\u533b\uff1a")
        for f in hit:
            lines.append("  ! " + CONTRA_TEXT[f])
        lines.append("  \u5904\u7f6e\uff1a" + CONTRA_ACTION)
        lines.append("")
        lines.append("  \u672c\u5de5\u5177\u4e0d\u7ed9\u836f\u7269\u3001\u4e0d\u7ed9\u5438\u75f0\u64cd\u4f5c\u3001\u4e0d\u5224\u65ad\u75f0\u91cf\u4e0e\u611f\u67d3\u3002")
        lines.append("=" * 66)
        return "\n".join(lines), {
            "blocked": True,
            "contraindication_hits": hit,
            "unknown_flags": unknown,
            "patting_allowed": False,
            "medication_provided": False,
            "suction_procedure_provided": False,
            "sputum_amount_judged": False,
        }

    good_risk, bad_risk = validate_list(
        raw_risk, [k for k, _l, _c in RISK_DIMS])
    contra, bad_contra = validate_list(raw_contra, CONTRA)
    if bad_risk:
        lines.append("[\u63d0\u793a] \u672a\u8bc6\u522b\u7684\u98ce\u9669\u6807\u8bb0\u5df2\u5ffd\u7565\uff1a" + "\u3001".join(bad_risk))
        lines.append("")
    if bad_contra:
        lines.append("[\u63d0\u793a] \u672a\u8bc6\u522b\u7684\u7981\u5fcc\u6807\u8bb0\u5df2\u5ffd\u7565\uff1a" + "\u3001".join(bad_contra))
        lines.append("")

    level = risk_level(good_risk)
    ok, meal_note = meal_ok(meal)

    lines.append("[\u4e00] \u53d7\u538b\u98ce\u9669\u6838\u67e5")
    for k, label, crit in RISK_DIMS:
        mark = "[\u6709]" if k in good_risk else "[\u65e0]"
        lines.append("  %s %s\uff5c%s" % (mark, label, crit))
    lines.append("")

    if only != "pat":
        lines.append("[\u4e8c] \u7ffb\u8eab\u4e0e\u4f53\u4f4d\u65b9\u6848")
        for line in build_turn_plan(level, good_risk):
            lines.append("  " + line if line else "")

    if only != "turn":
        lines.append("")
        lines.append("[\u4e09] \u62cd\u80cc\u65b9\u6848\u4e0e\u7981\u5fcc\u6838\u5bf9")
        lines.append("  \u65f6\u95f4\u7a97\u5224\u65ad\uff1a%s\uff08%s\uff09" % ("\u53ef\u62cd" if ok else "\u4e0d\u62cd", meal_note))
        for line in build_pat_plan(contra, meal_flag=ok):
            lines.append("  " + line if line else "")

    lines.append("")
    lines.append("[\u56db] \u8425\u517b\u4e0e\u5931\u7981\u7ba1\u7406")
    lines.append("  \u8425\u517b\uff1a")
    for n in NUTRITION:
        lines.append("    - " + n)
    lines.append("  \u5931\u7981\uff1a")
    for i in INCONTINENCE:
        lines.append("    - " + i)
    lines.append("")
    lines.append("[\u4e94] \u8bb0\u5f55\u4e0e\u4ea4\u63a5")
    lines.append("  " + MED_FINDING)
    lines.append("  \u4ea4\u63a5\u5fc5\u8bf4\uff1a")
    for t in TRANSFER_NOTE:
        lines.append("    - " + t)
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u7ffb\u8eab\u4e0e\u62cd\u80cc\u62a4\u7406\u53c2\u8003\uff0c\u4e0d\u6784\u6210\u533b\u7597\u610f\u89c1\u3002")
    lines.append("\u62cd\u80cc\u662f\u5426\u5b9e\u65bd\u4e0e\u5982\u4f55\u5b9e\u65bd\u987b\u7531\u533b\u62a4\u4eba\u5458\u8bc4\u4f30\u4e0e\u6307\u5bfc\uff0c\u4ee5\u6700\u65b0\u7248\u76f8\u5173\u6307\u5357\u4e3a\u51c6\u3002")
    lines.append("=" * 66)

    summary = {
        "blocked": False,
        "unknown_flags": unknown,
        "risk_level": level,
        "risk_hits": good_risk,
        "contraindication_hits": contra,
        "turn_interval_reference": TURN_TABLE[level][1],
        "interval_is_reference_only": True,
        "meal_window_ok": ok,
        "meal_window_note": meal_note,
        "patting_allowed": ok and not contra,
        "medication_provided": False,
        "suction_procedure_provided": False,
        "sputum_amount_judged": False,
        "pressure_ulcer_staging_provided": False,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("\u98ce\u9669\u7ef4\u5ea6\u4e3a 6 \u9879", len(RISK_DIMS) == 6))
    r.append(("\u62cd\u80cc\u7981\u5fcc\u4e3a 8 \u9879", len(CONTRA) == 8))
    r.append(("\u7981\u62cd\u533a\u57df\u81f3\u5c11 5 \u9879", len(PAT_AVOID) >= 5))
    r.append(("\u7a7a\u6b7b\u7981\u6b62\u4e3a 4 \u9879", len(CHOKING_FORBID) == 4))
    r.append(("\u7a7a\u6b7b\u9884\u8b66\u4fe1\u53f7\u81f3\u5c11 6 \u6761", len(CHOKING_SIGNALS) >= 6))
    r.append(("\u62cd\u80cc\u53c2\u6570\u5b8c\u6574", len(PAT_METHOD) == 5))
    r.append(("\u65f6\u95f4\u7a97\u8986\u76d6 3 \u79cd\u60c5\u5f62", len(MEAL_WINDOW) == 3))

    r.append(("\u65e0\u547d\u4e2d\u5224\u4e3a\u4f4e\u98ce\u9669", risk_level([]) == "low"))
    r.append(("\u4e0d\u80fd\u81ea\u4e3b\u7ffb\u8eab\u5224\u4e3a\u9ad8\u98ce\u9669", risk_level(["immobile"]) == "high"))
    r.append(("\u610f\u8bc6\u969c\u788d\u5224\u4e3a\u9ad8\u98ce\u9669", risk_level(["unconscious"]) == "high"))
    r.append(("\u4e24\u9879\u52a0\u91cd\u56e0\u7d20\u5224\u4e3a\u4e2d\u98ce\u9669",
              risk_level(["obesity", "edema"]) == "mid"))
    r.append(("\u5355\u9879\u52a0\u91cd\u56e0\u7d20\u4e5f\u4e3a\u4e2d\u98ce\u9669", risk_level(["incontinence"]) == "mid"))

    r.append(("\u9910\u524d 0.5 \u5c0f\u65f6\u4e0d\u53ef\u62cd", meal_ok(0.5)[0] is False))
    r.append(("\u9910\u540e 1.5 \u5c0f\u65f6\u4e0d\u53ef\u62cd", meal_ok(1.5)[0] is False))
    r.append(("\u9910\u540e 3 \u5c0f\u65f6\u53ef\u62cd", meal_ok(3)[0] is True))
    r.append(("\u65f6\u95f4\u4e3a\u8d1f\u65f6\u4e0d\u62cd", meal_ok(-1)[0] is False))
    r.append(("\u65f6\u95f4\u4e0d\u660e\u786e\u6709\u63d0\u793a", "\u4e0d\u660e\u786e" in meal_ok(-1)[1]))

    good, bad = validate_list(["immobile", "oops"], [k for k, _l, _c in RISK_DIMS])
    r.append(("\u5df2\u8bc6\u522b\u98ce\u9669\u7ef4\u5ea6\u8ba1\u6570\u6b63\u786e", good == ["immobile"]))
    r.append(("\u672a\u8bc6\u522b\u98ce\u9669\u7ef4\u5ea6\u88ab\u8fc7\u6ee4", bad == ["oops"]))
    gc, bc = validate_list(["rib_fracture", "zzz"], CONTRA)
    r.append(("\u5df2\u8bc6\u522b\u7981\u5fcc\u8ba1\u6570\u6b63\u786e", gc == ["rib_fracture"]))
    r.append(("\u672a\u8bc6\u522b\u7981\u5fcc\u88ab\u8fc7\u6ee4", bc == ["zzz"]))
    r.append(("\u6240\u6709\u7981\u5fcc\u5747\u6709\u6587\u672c", all(k in CONTRA_TEXT for k in CONTRA)))

    _, s = build_report({"risk": ["immobile"], "hours_since_meal": 3})
    r.append(("\u5b8c\u6574\u6837\u4f8b\u4e0d\u963b\u65ad", s["blocked"] is False))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u5224\u4e3a\u9ad8\u98ce\u9669", s["risk_level"] == "high"))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u65f6\u95f4\u7a97\u53ef\u62cd", s["meal_window_ok"] is True))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u5141\u8bb8\u62cd\u80cc", s["patting_allowed"] is True))
    r.append(("\u7ffb\u8eab\u95f4\u9694\u4e3a\u53c2\u8003", s["interval_is_reference_only"] is True))
    r.append(("\u4e0d\u7ed9\u836f\u7269", s["medication_provided"] is False))
    r.append(("\u4e0d\u7ed9\u5438\u75f0\u64cd\u4f5c", s["suction_procedure_provided"] is False))
    r.append(("\u4e0d\u5224\u65ad\u75f0\u91cf\u4e0e\u611f\u67d3", s["sputum_amount_judged"] is False))
    r.append(("\u4e0d\u7ed9\u538b\u75d5\u6b63\u5f0f\u5206\u671f", s["pressure_ulcer_staging_provided"] is False))

    _, s2 = build_report({"risk": ["immobile"], "contraindication": ["rib_fracture"]})
    r.append(("\u9aa8\u6298\u7981\u5fcc\u4e0d\u5141\u8bb8\u62cd\u80cc", s2["patting_allowed"] is False))
    r.append(("\u7981\u5fcc\u547d\u4e2d\u88ab\u8bb0\u5f55", s2["contraindication_hits"] == ["rib_fracture"]))

    _, s3 = build_report({"risk": ["immobile"], "hours_since_meal": 1.2})
    r.append(("\u9910\u540e\u65e9\u671f\u4e0d\u5141\u8bb8\u62cd\u80cc", s3["patting_allowed"] is False))

    _, s4 = build_report({"red_flags": ["resp_distress"]})
    r.append(("\u547c\u5438\u7d27\u6025\u76f4\u63a5\u963b\u65ad", s4["blocked"] is True))
    r.append(("\u963b\u65ad\u65f6\u4e0d\u5141\u8bb8\u62cd\u80cc", s4["patting_allowed"] is False))

    _, s5 = build_report({"risk": ["immobile"], "hours_since_meal": 3, "mode": "turn"})
    r.append(("\u4ec5\u7ffb\u8eab\u6a21\u5f0f\u4ecd\u6709\u8f93\u51fa", s5["blocked"] is False))

    txt, _ = build_report({"risk": ["hemiplegia"], "hours_since_meal": 3})
    r.append(("\u8f93\u51fa\u542b\u7a7a\u5fc3\u638c\u53e3\u5f84", "\u7a7a\u5fc3\u638c" in txt))
    r.append(("\u8f93\u51fa\u542b\u5ba1\u6279\u4e0e\u4ee5\u533b\u62a4\u8981\u6c42\u4e3a\u51c6",
              "\u6309\u533b\u62a4\u8981\u6c42" in txt))
    r.append(("\u8f93\u51fa\u542b\u5ba4\u808c\u65e0\u58f0\u7684\u7a7a\u6b7b\u5173\u952e\u4fe1\u53f7", "\u54b3\u6e05\u65e0\u58f0" in txt))
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
        description="\u5931\u80fd\u8001\u4eba\u7ffb\u8eab\u4e0e\u62cd\u80cc\u65b9\u6848\u751f\u6210\u5de5\u5177")
    parser.add_argument("--file", help="\u8f93\u5165 JSON \u6587\u4ef6\u8def\u5f84\uff08UTF-8\uff09")
    parser.add_argument("--turn", action="store_true", help="\u53ea\u8f93\u51fa\u7ffb\u8eab\u4e0e\u4f53\u4f4d\u65b9\u6848")
    parser.add_argument("--pat", action="store_true", help="\u53ea\u8f93\u51fa\u62cd\u80cc\u65b9\u6848\u4e0e\u7981\u5fcc\u6838\u5bf9")
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
    if args.turn:
        data["mode"] = "turn"
    if args.pat:
        data["mode"] = "pat"

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
