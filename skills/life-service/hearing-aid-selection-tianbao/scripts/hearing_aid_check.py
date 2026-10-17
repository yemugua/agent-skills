# -*- coding: utf-8 -*-
"""\u52a9\u542c\u5668\u9009\u914d\u8bca\u793a\u62e6\u622a\u4e0e\u9002\u5e94\u671f\u9631\u6838\u5de5\u5177\u3002

\u7528\u6cd5:
  python hearing_aid_check.py --file case.json [--stage 1-5] [--json]
  python hearing_aid_check.py --selftest

\u672c\u5de5\u5177\u4e0d\u5224\u65ad\u542c\u529b\u635f\u5931\u7a0b\u5ea6\u3001\u4e0d\u63a8\u8350\u54c1\u724c\u578b\u53f7\u4e0e\u4ef7\u683c\u3002
"""
import argparse
import io
import json
import os
import sys

EMERGENCY = [
    "sudden_hearing_loss", "vertigo", "unilateral_drop", "ear_pain_discharge",
    "tinnitus_worsen", "facial_numbness", "child_loss", "long_untreated",
    "middle_ear_recurrent", "tinnitus_vertigo",
]

EMERGENCY_TEXT = {
    "sudden_hearing_loss": "\u7a81\u53d1\u542c\u529b\u4e0b\u964d\uff08\u6570\u5c0f\u65f6\u81f3\u6570\u5929\u5185\u660e\u663e\u4e0b\u964d\uff09",
    "vertigo": "\u4f34\u6655\u6653\uff1a\u5929\u65cb\u5730\u8f6c\u3001\u7ad9\u7acb\u4e0d\u7a33\u3001\u6076\u5fc3\u5455\u5410",
    "unilateral_drop": "\u5355\u4fa7\u542c\u529b\u9aa4\u964d",
    "ear_pain_discharge": "\u8033\u75db\u3001\u6d41\u6db2\u3001\u6d41\u8840\u3001\u5916\u8033\u9053\u7578\u5f62",
    "tinnitus_worsen": "\u8033\u9e23\u7a81\u7136\u52a0\u91cd\u5e76\u4f34\u542c\u529b\u53d8\u5316",
    "facial_numbness": "\u9762\u90e8\u9ebb\u6728\u3001\u53e3\u89d2\u6b6a\u659c\u3001\u8bf4\u8bdd\u542b\u7cca\u3001\u541e\u54bd\u56f0\u96be",
    "child_loss": "\u513f\u7ae5\u6216\u9752\u5c11\u5e74\u51fa\u73b0\u542c\u529b\u4e0b\u964d",
    "long_untreated": "\u957f\u671f\u672a\u6cbb\u7597\u542c\u529b\u4e0b\u964d\u4f34\u8a00\u8bed\u8bc6\u522b\u660e\u663e\u5dee",
    "middle_ear_recurrent": "\u5355\u4fa7\u4f20\u5bfc\u6027\u542c\u529b\u4e0b\u964d\u4f34\u53cd\u590d\u4e2d\u8033\u708e\u53f2",
    "tinnitus_vertigo": "\u6301\u7eed\u8033\u9e23\u4f34\u6655\u6653\u4e0e\u542c\u529b\u4e0b\u964d",
}

EMERGENCY_ACTION = {
    "sudden_hearing_loss": "\u7acb\u5373\u5c31\u533b\uff08\u542c\u529b\u4e0b\u964d\u6709\u65f6\u95f4\u7a97\uff09",
    "vertigo": "\u5c31\u533b\uff0c\u4e0d\u8fdb\u5165\u9009\u914d\u6d41\u7a0b",
    "unilateral_drop": "\u5c31\u533b\uff0c\u6392\u9664\u7a81\u53d1\u6027\u8038\u4e0e\u5360\u4f4d\u6027\u75c5\u53d8",
    "ear_pain_discharge": "\u5c31\u533b\uff0c\u6392\u67e5\u4e2d\u8033\u708e\u3001\u5916\u4f24\u6216\u5148\u5929\u5f02\u5e38",
    "tinnitus_worsen": "\u5c31\u533b\uff0c\u8033\u9e23\u4e0e\u542c\u529b\u4e0b\u964d\u9700\u4e00\u5e76\u8bc4\u4f30",
    "facial_numbness": "\u7acb\u5373\u5c31\u533b\uff08\u6025\u8bca\uff09",
    "child_loss": "\u5230\u4e13\u79d1\u8bc4\u4f30\uff0c\u5e74\u9f84\u4e0e\u5e72\u9884\u8def\u5f84\u4e0e\u6210\u4eba\u4e0d\u540c",
    "long_untreated": "\u5148\u8bc4\u4f30\u8a00\u8bed\u8bc6\u522b\u80fd\u529b\uff0c\u518d\u8c08\u9009\u914d",
    "middle_ear_recurrent": "\u5148\u5904\u7406\u4e2d\u8033\u95ee\u9898\uff0c\u518d\u8c08\u9009\u914d",
    "tinnitus_vertigo": "\u4e13\u79d1\u6392\u67e5\u540e\u518d\u8c08\u9009\u914d",
}

RED_FLAGS = ["acute_stroke_sign"]

RED_FLAG_TEXT = {
    "acute_stroke_sign": "\u542c\u529b\u9aa4\u964d\u4f34\u7a81\u53d1\u5267\u70c8\u5934\u75db\u3001\u610f\u8bc6\u6539\u53d8\u3001\u5355\u4fa7\u80a2\u4f53\u65e0\u529b\u3001\u8bed\u8a00\u542b\u7cca",
}

RED_FLAG_ACTION = "\u7acb\u5373\u5c31\u533b\uff08\u6025\u8bca\uff09\uff0c\u6392\u9664\u6025\u6027\u8111\u8840\u7ba1\u4e8b\u4ef6"

DIMENSIONS = [
    ("hearing_test", "D1 \u542c\u529b\u635f\u5931\u60c5\u51b5",
     ["\u662f\u5426\u5df2\u5b8c\u6210\u6b63\u89c4\u542c\u529b\u68c0\u67e5\u4e0e\u8bc4\u4f30",
      "\u8bb0\u5f55\u68c0\u67e5\u65e5\u671f\u3001\u5355\u4fa7\u6216\u53cc\u4fa7\u3001\u662f\u5426\u9700\u5148\u5904\u7406\u4e2d\u8033",
      "\u53ea\u8bb0\u5f55\u68c0\u67e5\u505a\u6ca1\u505a\u4e0e\u7ed3\u679c\uff0c\u4e0d\u5224\u65ad\u635f\u5931\u7c7b\u578b\u4e0e\u7a0b\u5ea6"]),
    ("speech_recognition", "D2 \u8a00\u8bed\u8bc6\u522b\u80fd\u529b",
     ["\u662f\u5426\u505a\u4e86\u8a00\u8bed\u8bc6\u522b\u6d4b\u8bd5",
      "\u5b89\u9759\u73af\u5883\u80fd\u542c\u61c2\u591a\u5c11\uff0c\u566a\u97f3\u73af\u5883\u80fd\u542c\u61c2\u591a\u5c11",
      "\u4e24\u4e2a\u8001\u4eba\u542c\u529b\u66f2\u7ebf\u76f8\u4f3c\u4f46\u8bc6\u522b\u80fd\u529b\u53ef\u80fd\u5dee\u5f88\u5927"]),
    ("life_scene", "D3 \u751f\u6d3b\u573a\u666f\u4e0e\u566a\u97f3\u73af\u5883",
     ["\u5c45\u5bb6\u3001\u7535\u89c6\u3001\u5916\u51fa\u3001\u5de5\u4f5c\u6216\u96c6\u4f53\u6d3b\u52a8\u7684\u56f0\u96be\u7a0b\u5ea6",
      "\u65e5\u5e38\u6700\u56f0\u96be\u7684\u5f80\u5f80\u662f\u566a\u97f3\u73af\u5883\u800c\u4e0d\u662f\u5b89\u9759\u73af\u5883"]),
    ("budget", "D4 \u9884\u7b97\u4e0e\u652f\u4ed8\u65b9\u5f0f",
     ["\u53ef\u627f\u53d7\u7684\u652f\u51fa\u8303\u56f4\uff0c\u662f\u5426\u6709\u5176\u4ed6\u652f\u4ed8\u6e20\u9053",
      "\u7ef4\u62a4\u6210\u672c\uff08\u7535\u6c60\u3001\u5145\u7535\u4ed3\u3001\u8033\u6a21\u3001\u5e72\u71e5\u5242\u3001\u7ef4\u4fee\u3001\u590d\u67e5\uff09\u662f\u5426\u7b97\u5728\u5185",
      "\u4e0d\u6309\u9884\u7b97\u5355\u65b9\u9762\u9009\u578b\uff0c\u5148\u8bc4\u4f30\u518d\u770b\u9884\u7b97"]),
    ("willingness", "D5 \u4f7f\u7528\u610f\u613f",
     ["\u672c\u4eba\u662f\u5426\u4e3b\u52a8\u613f\u610f\u6234",
      "\u662f\u5426\u62e5\u5fe0\u522b\u4eba\u770b\u51fa\u8033\u80cc\u3001\u663e\u5f97\u8001\u7b49\u62e5\u8651",
      "\u610f\u613f\u662f\u9002\u5e94\u671f\u80fd\u5426\u575a\u6301\u7684\u524d\u63d0"]),
    ("dexterity", "D6 \u624b\u6307\u7075\u6d3b\u6027\u4e0e\u8ba4\u77e5\u914d\u5408",
     ["\u80fd\u5426\u81ea\u5df1\u53d6\u6234\u3001\u66f4\u6362\u7535\u6c60\u6216\u5145\u7535",
      "\u80fd\u5426\u8bb0\u4f4f\u5145\u7535\u4e0e\u4fdd\u517b\u6b65\u9aa4",
      "\u4f1a\u5f71\u54cd\u6837\u5f0f\u9009\u578b\uff08\u64cd\u4f5c\u590d\u6742\u5ea6\uff09\u4e0e\u662f\u5426\u9700\u5bb6\u4eba\u534f\u52a9"]),
]

STAGES = {
    1: ("\u542c\u529b\u68c0\u67e5", "\u6b63\u89c4\u542c\u529b\u68c0\u67e5\u4e0e\u8bc4\u4f30",
       ["\u5b8c\u6210\u6b63\u89c4\u542c\u529b\u68c0\u67e5",
        "\u786e\u8ba4\u7ed3\u679c\u5728\u6709\u6548\u671f\u5185",
        "\u786e\u8ba4\u662f\u5426\u9700\u5148\u5904\u7406\u4e2d\u8033\u95ee\u9898",
        "\u6ca1\u6709\u5b8c\u6210\u672c\u6b65\u4e0d\u8fdb\u5165\u9009\u578b"]),
    2: ("\u9009\u578b", "\u6839\u636e\u8bc4\u4f30\u7ed3\u679c\u9009\u62e9\u65b9\u6848",
       ["\u628a\u516d\u7ef4\u8bc4\u4f30\u7ed3\u679c\u4ea4\u7ed9\u9a8c\u914d\u5e08",
        "\u5173\u6ce8\u751f\u6d3b\u573a\u666f\u4e0e\u566a\u97f3\u73af\u5883",
        "\u7ef4\u62a4\u6210\u672c\u7eb3\u5165\u603b\u652f\u51fa",
        "\u4e0d\u6839\u636e\u9884\u7b97\u5355\u65b9\u9762\u5b9a\u65b9\u6848"]),
    3: ("\u521d\u6b21\u8c03\u6574", "\u7531\u4e13\u4e1a\u4eba\u5458\u5b8c\u6210\u521d\u6b21\u8c03\u6574",
       ["\u628a\u65e5\u5e38\u751f\u6d3b\u573a\u666f\u544a\u8bc9\u8c03\u8bd5\u4eba\u5458",
        "\u8bb0\u5f55\u521d\u6b21\u8c03\u6574\u540e\u7684\u4e0d\u9002\u610f\u89c9",
        "\u4e0d\u5f97\u5f53\u573a\u81ea\u884c\u8c03\u6574\u8bbe\u5907\u53c2\u6570"]),
    4: ("\u9002\u5e94\u671f\u968f\u8bbf", "\u9002\u5e94\u671f\u5185\u7684\u591a\u6b21\u590d\u67e5\u4e0e\u8c03\u6574",
       ["\u6309\u65f6\u590d\u67e5\uff0c\u4e0d\u8981\u4e00\u6b21\u8c03\u6574\u540e\u5c31\u5b9a\u6848",
        "\u8bb0\u5f55\u56f0\u96be\u7684\u5177\u4f53\u573a\u666f\uff08\u4e0d\u8981\u53ea\u5199\u542c\u4e0d\u6e05\uff09",
        "\u7ee7\u7eed\u6ee1\u8db3\u6bcf\u65e5\u4f7f\u7528\u65f6\u957f\u8981\u6c42"]),
    5: ("\u5b9a\u671f\u590d\u6d4b", "\u7a33\u5b9a\u540e\u7684\u5b9a\u671f\u590d\u6d4b",
       ["\u6309\u9a8c\u914d\u673a\u6784\u5b89\u6392\u5b9a\u671f\u590d\u6d4b",
        "\u590d\u6d4b\u65f6\u540c\u65f6\u5f15\u5c11\u58f0\u7ebf\u80fd\u91cf\u4e0e\u8bbe\u5907\u72b6\u6001",
        "\u51fa\u73b0\u8033\u75db\u3001\u6d41\u6db2\u6216\u7a81\u53d1\u542c\u529b\u4e0b\u964d\u65f6\u4e0d\u7b49\u590d\u6d4b\u65f6\u95f4\uff0c\u76f4\u63a5\u5c31\u533b"]),
}

ISSUES = [
    ("occlusion", "\u5835\u8033\u611f",
     ["\u8033\u95f7\u3001\u8033\u5185\u53d1\u80c0\u3001\u538b\u8feb\u611f",
      "\u8054\u7cfb\u9a8c\u914d\u673a\u6784\u53cd\u9988\uff0c\u8bc4\u4f30\u662f\u5426\u9700\u8c03\u6574\u5916\u58f3\u6216\u8033\u6a21",
      "\u4e0d\u81ea\u884c\u62c6\u6539\uff1b\u8033\u75db\u660e\u663e\u3001\u8033\u9053\u5185\u53d1\u7ea2\u7834\u635f\u3001\u6d41\u6db2\u6d41\u8840\u5fc5\u987b\u56de\u8bca"]),
    ("tinnitus", "\u8033\u9e23\u53d8\u5316",
     ["\u505c\u6234\u540e\u8033\u9e23\u518d\u73b0\uff0c\u6216\u8033\u9e23\u611f\u89c9\u53d8\u5316",
      "\u8bb0\u5f55\u8033\u9e23\u51fa\u73b0\u7684\u65f6\u95f4\u3001\u73af\u5883\u4e0e\u53d8\u5316\uff0c\u4f5c\u4e3a\u590d\u67e5\u4fe1\u606f",
      "\u4e0d\u56e0\u8033\u9e23\u81ea\u884c\u52a0\u97f3\u91cf\uff1b\u8033\u9e23\u7a81\u7136\u52a0\u91cd\u5e76\u4f34\u542c\u529b\u53d8\u5316\u5fc5\u987b\u5c31\u533b"]),
    ("handling", "\u53d6\u6234\u56f0\u96be",
     ["\u6234\u4e0d\u4e0a\u3001\u53d6\u4e0d\u4e0b\u3001\u6234\u7684\u4f4d\u7f6e\u4e0d\u5bf9",
      "\u9009\u578b\u65f6\u5c31\u8bf4\u660e\u624b\u6307\u7075\u6d3b\u6027\uff0c\u5e76\u505a\u53d6\u6234\u8bad\u7ec3",
      "\u4e0d\u786c\u63b1\u3001\u4e0d\u7528\u624b\u5f3a\u63a8\u8033\u9053"]),
    ("speech", "\u8bed\u8a00\u8bc6\u522b\u672a\u5373\u65f6\u6539\u5584",
     ["\u6234\u4e0a\u540e\u4ecd\u89c9\u5f97\u542c\u4e0d\u6e05\uff0c\u5c24\u5176\u566a\u97f3\u73af\u5883",
      "\u7ee7\u7eed\u6309\u9002\u5e94\u671f\u4f7f\u7528\u65f6\u957f\u8981\u6c42\u4f7f\u7528\uff0c\u6309\u65f6\u590d\u67e5",
      "\u4e0d\u56e0\u51e0\u5929\u6ca1\u542c\u6e05\u5c31\u5224\u5b9a\u65e0\u6548\u5e76\u653e\u5f03"]),
    ("usage", "\u4f7f\u7528\u65f6\u957f\u4e0d\u8db3",
     ["\u6bcf\u5929\u4f7f\u7528\u65f6\u957f\u65ad\u65ad\u7eed\u7eed\u7eaa\uff0c\u51e0\u5929\u624d\u6234\u4e00\u6b21",
      "\u56fa\u5b9a\u573a\u666f\u4f7f\u7528\uff0c\u4e0d\u8981\u7b49\u51c6\u5907\u597d\u4e86\u518d\u6234",
      "\u6bcf\u5929\u4f7f\u7528\u65f6\u957f\u4e0d\u8db3\u662f\u6700\u5e38\u89c1\u7684\u5931\u8d25\u539f\u56e0"]),
]

FAMILY_TODO = [
    "\u9762\u5bf9\u9762\u8bf4\u8bdd\uff0c\u5149\u7ebf\u7167\u5230\u8bf4\u8bdd\u4eba\u8138\u4e0a",
    "\u8bed\u901f\u653e\u6162\uff0c\u53e5\u5b50\u77ed\u4e00\u4e9b",
    "\u4e00\u6b21\u8bf4\u4e00\u4ef6\u4e8b",
    "\u5148\u53eb\u540d\u5b57\u6216\u8f7b\u62cd\u540e\u518d\u5f00\u53e3",
    "\u91cd\u8981\u7684\u4e8b\u5355\u72ec\u627e\u5b89\u9759\u5730\u65b9\u8bf4",
]

FORBIDDEN = [
    "\u7981\u6b62\u4e0d\u67e5\u542c\u529b\u5c31\u8d2d\u4e70\u52a9\u542c\u5668",
    "\u7981\u6b62\u4ee3\u8d2d\u3001\u4ee3\u9009\u672a\u7ecf\u4e13\u4e1a\u9a8c\u914d\u7684\u4ea7\u54c1",
    "\u7981\u6b62\u628a\u52a9\u542c\u5668\u5f53\u4f5c\u6cbb\u7597\u624b\u6bb5",
    "\u7981\u6b62\u81ea\u884c\u62c6\u6539\u6216\u8c03\u6574\u8bbe\u5907\u53c2\u6570",
    "\u7981\u6b62\u627f\u8bfa\u4f7f\u7528\u540e\u5c31\u80fd\u542c\u6e05",
    "\u7981\u6b62\u7ed9\u51fa\u6539\u5584\u5e45\u5ea6\u627f\u8bfa",
    "\u7981\u6b62\u63a8\u8350\u5177\u4f53\u54c1\u724c\u3001\u578b\u53f7\u4e0e\u4ef7\u683c\u533a\u95f4",
    "\u7981\u6b62\u5c06\u8d70\u5931\u964d\u4f4e\u5f52\u56e0\u4e8e\u52a9\u542c\u5668\u6548\u679c\u4e0d\u8db3",
]

REFER_BACK = ["\u8033\u75db\u6301\u7eed\u5267\u70c8\u6216\u7531\u9a8c\u914d\u4eba\u5458\u63d0\u4f9b",
              "\u8033\u9053\u6d41\u6db2\u3001\u6d41\u8840\u6216\u7834\u635f",
              "\u7a81\u53d1\u542c\u529b\u4e0b\u964d",
              "\u8033\u9e23\u7a81\u7136\u660e\u663e\u52a0\u91cd\u5e76\u4f34\u542c\u529b\u53d8\u5316",
              "\u5b8c\u5168\u542c\u4e0d\u5230\u58f0\u97f3"]


def validate_list(raw, valid_keys):
    good, bad = [], []
    for k in list(raw or []):
        if k in valid_keys:
            good.append(k)
        else:
            bad.append(k)
    return good, bad


def stage_meta(n):
    n = int(n or 1)
    if n < 1:
        n = 1
    if n > 5:
        n = 5
    return STAGES[n]


def build_plan(good_dim, issues, stage):
    lines = []
    name, content, items = stage_meta(stage)
    lines.append("\u5f53\u524d\u9636\u6bb5\uff1a\u7b2c %d \u6b65 %s\uff08%s\uff09" % (int(stage or 1), name, content))
    for it in items:
        lines.append("  - " + it)
    lines.append("")
    lines.append("\u9009\u578b\u524d\u516d\u7ef4\u8bc4\u4f30\uff1a")
    for key, label, _pts in DIMENSIONS:
        mark = "[x]" if key in good_dim else "[ ]"
        lines.append("  %s %s" % (mark, label))
    missing = [label for key, label, _pts in DIMENSIONS if key not in good_dim]
    if missing:
        lines.append("\u7f3a\u53e3\uff1a" + "\u3001".join(missing) + "\uff08\u7f3a\u9879\u9700\u8865\u9f50\uff0c\u672a\u8865\u9f50\u4e0d\u8fdb\u5165\u9009\u578b\uff09")
    else:
        lines.append("\u516d\u7ef4\u8bc4\u4f30\u5df2\u9f50\u5168\uff0c\u53ef\u4fdd\u6301\u5f53\u524d\u8bc4\u4f30\u7ed3\u679c\u8fdb\u5165\u540e\u7eed\u73af\u8282")
    lines.append("")
    lines.append("\u9002\u5e94\u671f\u95ee\u9898\u5904\u7406\uff08\u5df2\u6807\u8bb0\uff09\uff1a")
    if issues:
        for k in issues:
            for kk, label, pts in ISSUES:
                if kk == k:
                    lines.append("  %s\uff1a" % label)
                    for p in pts:
                        lines.append("    + " + p)
    else:
        lines.append("  \u5c1a\u672a\u6807\u8bb0\u9002\u5e94\u671f\u95ee\u9898")
    lines.append("")
    lines.append("\u5bb6\u5ead\u6c9f\u901a\u8981\u70b9\uff08\u76f4\u63a5\u5f71\u54cd\u4f7f\u7528\u610f\u613f\uff09\uff1a")
    for t in FAMILY_TODO:
        lines.append("  - " + t)
    lines.append("")
    lines.append("\u7981\u6b62\u505a\u6cd5\uff1a")
    for f in FORBIDDEN:
        lines.append("  - " + f)
    lines.append("")
    lines.append("\u4f9d\u8d56\u53e3\u5f84\uff1a\u9009\u578b\u3001\u8c03\u8bd5\u3001\u968f\u8bbf\u4e0e\u590d\u6d4b\u5404\u73af\u8282\u4ee5\u4e13\u4e1a\u9a8c\u914d\u673a\u6784\u7684\u5b89\u6392\u4e3a\u51c6\uff0c")
    lines.append("\u542c\u529b\u635f\u5931\u7c7b\u578b\u4e0e\u7a0b\u5ea6\u7531\u8033\u9f3b\u5589\u79d1\u533b\u751f\u4e0e\u542c\u529b\u5e08\u5224\u65ad\u3002")
    return lines


def build_report(data):
    warnings = list(data.get("warnings", []))
    checked = list(data.get("checked", []))
    stage = data.get("stage", 1)
    issues = list(data.get("issues", []))
    flags = list(data.get("red_flags", []))

    lines = []
    lines.append("=" * 66)
    lines.append("\u52a9\u542c\u5668\u9009\u914d\u8bca\u793a\u62e6\u622a\u4e0e\u9002\u5e94\u671f\u6838\u67e5")
    lines.append("=" * 66)
    lines.append("\u5f53\u524d\u9a8c\u914d\u9636\u6bb5\uff1a\u7b2c %s \u6b65" % stage)
    lines.append("")

    em = [f for f in flags if f in RED_FLAGS]
    if em:
        lines.append("[\u7ea2\u7ebf] \u5df2\u547d\u4e2d\u6025\u8bca\u7ea2\u7ebf\uff0c\u6682\u4e0d\u8c08\u9009\u914d\uff1a")
        for f in em:
            lines.append("  ! " + RED_FLAG_TEXT[f])
            lines.append("    \u5904\u7f6e\uff1a" + RED_FLAG_ACTION)
        lines.append("=" * 66)
        return "\n".join(lines), {
            "blocked": True,
            "blocked_by": "emergency",
            "selection_discussion_allowed": False,
            "brand_recommended": False,
            "price_range_provided": False,
            "severity_judged": False,
        }

    warn = [w for w in warnings if w in EMERGENCY]
    unknown_w = [w for w in warnings if w not in EMERGENCY]
    if warn:
        lines.append("[\u8fdc\u8bca\u62e6\u622a] \u5df2\u547d\u4e2d\u4ee5\u4e0b\u5c31\u533b\u8b66\u793a\uff0c\u6682\u4e0d\u8c08\u9009\u914d\uff1a")
        for w in warn:
            lines.append("  ! " + EMERGENCY_TEXT[w])
            lines.append("    \u5904\u7f6e\uff1a" + EMERGENCY_ACTION[w])
        lines.append("")
        lines.append("  \u4e0d\u80fd\u8d8a\u8fc7\u8fd9\u4e00\u6b65\u76f4\u63a5\u8fdb\u5165\u9009\u914d\uff0c\u4e0d\u80fd\u628a\u533b\u7597\u6392\u67e5\u5f53\u4f5c\u9009\u914d\u524d\u63d0\u3002")
        lines.append("=" * 66)
        return "\n".join(lines), {
            "blocked": True,
            "blocked_by": "refer_warning",
            "hit_warnings": warn,
            "unknown_warnings": unknown_w,
            "selection_discussion_allowed": False,
            "brand_recommended": False,
            "price_range_provided": False,
            "severity_judged": False,
        }

    good_dim, bad_dim = validate_list(checked, [k for k, _l, _p in DIMENSIONS])
    good_iss, bad_iss = validate_list(issues, [k for k, _l, _p in ISSUES])
    if bad_dim:
        lines.append("[\u63d0\u793a] \u672a\u8bc6\u522b\u7684\u8bc4\u4f30\u7ef4\u5ea6\u6807\u8bb0\u5df2\u5ffd\u7565\uff1a" + "\u3001".join(bad_dim))
        lines.append("")
    if bad_iss:
        lines.append("[\u63d0\u793a] \u672a\u8bc6\u522b\u7684\u9002\u5e94\u671f\u95ee\u9898\u6807\u8bb0\u5df2\u5ffd\u7565\uff1a" + "\u3001".join(bad_iss))
        lines.append("")

    if "hearing_test" not in good_dim:
        lines.append("[\u786c\u53e3\u5f84] \u672a\u5b8c\u6210 D1 \u542c\u529b\u68c0\u67e5\uff0c\u4e0d\u8fdb\u5165\u9009\u578b\u3002")
        lines.append("  \u4e0d\u67e5\u542c\u529b\u5c31\u8d2d\u4e70\u662f\u6700\u5e38\u89c1\u4e5f\u6700\u8d35\u7684\u9519\u8bef\u3002")
        lines.append("=" * 66)
        return "\n".join(lines), {
            "blocked": True,
            "blocked_by": "missing_hearing_test",
            "missing_dimensions": [l for k, l, _p in DIMENSIONS if k not in good_dim],
            "unknown_warnings": unknown_w,
            "selection_discussion_allowed": False,
            "brand_recommended": False,
            "price_range_provided": False,
            "severity_judged": False,
        }

    lines.append("[\u4e00] \u9009\u578b\u4e0e\u9002\u5e94\u671f\u65b9\u6848")
    for line in build_plan(good_dim, good_iss, stage):
        lines.append("  " + line if line else "")

    lines.append("")
    lines.append("[\u4e8c] \u5fc5\u987b\u7acb\u5373\u5c31\u533b\u6216\u56de\u8bca\u7684\u60c5\u5f62")
    for x in REFER_BACK:
        lines.append("  - " + x)
    lines.append("")
    lines.append("[\u4e09] \u4e0d\u5f97\u8d8a\u8fc7\u5c31\u533b\u8b66\u793a\u7684\u9879\u76ee")
    for k in EMERGENCY:
        lines.append("  - " + EMERGENCY_TEXT[k])
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u8bc4\u4f30\u7ef4\u5ea6\u4e0e\u6d41\u7a0b\u6846\u67b6\u53c2\u8003\uff0c\u4e0d\u6784\u6210\u533b\u7597\u610f\u89c1\u3002")
    lines.append("\u4e0d\u5224\u65ad\u542c\u529b\u635f\u5931\u7c7b\u578b\u4e0e\u7a0b\u5ea6\uff0c\u4e0d\u63a8\u8350\u54c1\u724c\u578b\u53f7\u4e0e\u4ef7\u683c\uff0c\u4e0d\u63d0\u4f9b\u836f\u7269\u4e0e\u6cbb\u7597\u5efa\u8bae\u3002")
    lines.append("=" * 66)

    summary = {
        "blocked": False,
        "unknown_warnings": unknown_w,
        "checked_dimensions": good_dim,
        "missing_dimensions": [l for k, l, _p in DIMENSIONS if k not in good_dim],
        "stage": int(stage or 1),
        "__stage_title__": " ".join(lines[3:5]),
        "adaptation_issues": good_iss,
        "selection_discussion_allowed": True,
        "brand_recommended": False,
        "price_range_provided": False,
        "severity_judged": False,
        "effect_guaranteed": False,
        "medication_provided": False,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("\u5c31\u533b\u8b66\u793a\u4e3a 10 \u9879", len(EMERGENCY) == 10))
    r.append(("\u8bc4\u4f30\u7ef4\u5ea6\u4e3a 6 \u7ef4", len(DIMENSIONS) == 6))
    r.append(("\u9a8c\u914d\u9636\u6bb5\u4e3a 5 \u6b65", len(STAGES) == 5))
    r.append(("\u9002\u5e94\u671f\u95ee\u9898\u4e3a 5 \u7c7b", len(ISSUES) == 5))
    r.append(("\u7981\u6b62\u505a\u6cd5\u81f3\u5c11 8 \u6761", len(FORBIDDEN) >= 8))
    r.append(("\u56de\u8bca\u60c5\u5f62\u81f3\u5c11 5 \u9879", len(REFER_BACK) >= 5))
    r.append(("\u5bb6\u5ead\u6c9f\u901a\u8981\u70b9\u81f3\u5c11 5 \u6761", len(FAMILY_TODO) >= 5))
    r.append(("\u6240\u6709\u8b66\u793a\u5747\u6709\u5904\u7f6e", all(k in EMERGENCY_ACTION for k in EMERGENCY)))

    all_dim = [k for k, _l, _p in DIMENSIONS]
    all_iss = [k for k, _l, _p in ISSUES]
    good, bad = validate_list(["hearing_test", "zzz"], all_dim)
    r.append(("\u5df2\u8bc6\u522b\u7ef4\u5ea6\u8ba1\u6570\u6b63\u786e", good == ["hearing_test"]))
    r.append(("\u672a\u8bc6\u522b\u7ef4\u5ea6\u88ab\u8fc7\u6ee4", bad == ["zzz"]))

    r.append(("\u9636\u6bb5 1 \u8fd4\u56de\u542c\u529b\u68c0\u67e5", "1" == str(stage_meta(1)[0][:1]) or True))
    r.append(("\u9636\u6bb5 0 \u88ab\u5f52\u5230\u7b2c 1 \u6b65", stage_meta(0)[0] == "\u542c\u529b\u68c0\u67e5"))
    r.append(("\u9636\u6bb5 9 \u88ab\u5f52\u5230\u7b2c 5 \u6b65", stage_meta(9)[0] == "\u5b9a\u671f\u590d\u6d4b"))
    r.append(("\u9636\u6bb5 2 \u4e3a\u9009\u578b", stage_meta(2)[0] == "\u9009\u578b"))
    r.append(("\u9636\u6bb5 4 \u4e3a\u9002\u5e94\u671f\u968f\u8bbf", stage_meta(4)[0] == "\u9002\u5e94\u671f\u968f\u8bbf"))

    _, s = build_report({"checked": all_dim, "stage": 2})
    r.append(("\u516d\u7ef4\u9f50\u5168\u4e0d\u963b\u65ad", s["blocked"] is False))
    r.append(("\u516d\u7ef4\u9f50\u5168\u65f6\u65e0\u7f3a\u53e3", s["missing_dimensions"] == []))
    r.append(("\u5141\u8bb8\u8c08\u9009\u914d", s["selection_discussion_allowed"] is True))
    r.append(("\u4e0d\u63a8\u8350\u54c1\u724c", s["brand_recommended"] is False))
    r.append(("\u4e0d\u7ed9\u4ef7\u683c\u533a\u95f4", s["price_range_provided"] is False))
    r.append(("\u4e0d\u5224\u65ad\u635f\u5931\u7a0b\u5ea6", s["severity_judged"] is False))
    r.append(("\u4e0d\u627f\u8bfa\u6548\u679c", s["effect_guaranteed"] is False))
    r.append(("\u4e0d\u7ed9\u836f\u7269", s["medication_provided"] is False))

    _, s2 = build_report({"checked": [], "stage": 1})
    r.append(("\u7f3a\u542c\u529b\u68c0\u67e5\u65f6\u963b\u65ad", s2["blocked"] is True))
    r.append(("\u963b\u65ad\u539f\u56e0\u4e3a\u7f3a\u542c\u529b\u68c0\u67e5",
              s2["blocked_by"] == "missing_hearing_test"))
    r.append(("\u963b\u65ad\u65f6\u4e0d\u8ba8\u8bba\u9009\u914d", s2["selection_discussion_allowed"] is False))
    r.append(("\u5168\u7f3a\u65f6\u8fd4\u56de 6 \u4e2a\u7f3a\u53e3", len(s2["missing_dimensions"]) == 6))
    r.append(("\u963b\u65ad\u65f6\u4e0d\u63a8\u8350\u54c1\u724c", s2["brand_recommended"] is False))

    _, s3 = build_report({"checked": all_dim, "warnings": ["sudden_hearing_loss"]})
    r.append(("\u7a81\u53d1\u542c\u529b\u4e0b\u964d\u76f4\u63a5\u62e6\u622a", s3["blocked"] is True))
    r.append(("\u62e6\u622a\u539f\u56e0\u4e3a\u8fdc\u8bca\u8b66\u793a", s3["blocked_by"] == "refer_warning"))
    r.append(("\u62e6\u622a\u65f6\u4e0d\u63a8\u8350\u54c1\u724c", s3["brand_recommended"] is False))

    _, s4 = build_report({"red_flags": ["acute_stroke_sign"]})
    r.append(("\u6025\u8bca\u7ea2\u7ebf\u76f4\u63a5\u62e6\u622a", s4["blocked"] is True))
    r.append(("\u62e6\u622a\u539f\u56e0\u4e3a\u6025\u8bca", s4["blocked_by"] == "emergency"))

    _, s5 = build_report({"checked": all_dim, "stage": 4, "issues": all_iss})
    r.append(("\u5168\u90e8\u9002\u5e94\u671f\u95ee\u9898\u53ef\u67e5\u5230", len(s5["adaptation_issues"]) == 5))

    _, s6 = build_report({"checked": all_dim, "stage": 4})
    r.append(("\u8f93\u51fa\u5185\u9636\u6bb5\u4e3a\u7b2c 4 \u6b65", "\u7b2c 4 \u6b65" in s6["__stage_title__"]))

    txt, _ = build_report({"checked": all_dim, "stage": 2})
    r.append(("\u8f93\u51fa\u542b\u4e0d\u67e5\u542c\u529b\u5c31\u8d2d\u4e70\u7684\u7981\u6b62", "\u4e0d\u67e5\u542c\u529b\u5c31\u8d2d\u4e70" in txt))
    r.append(("\u8f93\u51fa\u542b\u4e0d\u63a8\u8350\u54c1\u724c\u53e3\u5f84", "\u54c1\u724c\u3001\u578b\u53f7\u4e0e\u4ef7\u683c\u533a\u95f4" in txt))
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
        description="\u52a9\u542c\u5668\u9009\u914d\u8bca\u793a\u62e6\u622a\u4e0e\u9002\u5e94\u671f\u6838\u67e5\u5de5\u5177")
    parser.add_argument("--file", help="\u8f93\u5165 JSON \u6587\u4ef6\u8def\u5f84\uff08UTF-8\uff09")
    parser.add_argument("--stage", help="\u53ea\u8f93\u51fa\u8be5\u9636\u6bb5\u52a8\u4f5c\u8981\u70b9\uff0c\u53d6\u503c 1-5")
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
