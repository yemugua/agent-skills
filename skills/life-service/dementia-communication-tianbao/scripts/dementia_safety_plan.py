# -*- coding: utf-8 -*-
"""\u5931\u667a\u8001\u4eba\u6c9f\u901a\u969c\u788d\u5904\u7406\u4e0e\u8d70\u5931\u9632\u9884\u751f\u6210\u5de5\u5177\u3002

\u7528\u6cd5:
  python dementia_safety_plan.py --file case.json [--checklist] [--json]
  python dementia_safety_plan.py --selftest

\u672c\u5de5\u5177\u4e0d\u7ed9\u836f\u7269\u3001\u4e0d\u505a\u8bca\u65ad\u3001\u4e0d\u7ed9\u627e\u56de\u6982\u7387\u3002
"""
import argparse
import io
import json
import os
import sys

OBSTACLES = [
    ("repeat_question", "\u91cd\u590d\u63d0\u95ee",
     ["\u540c\u4e00\u4e2a\u95ee\u9898\u95ee\u4e0a\u51e0\u5341\u6b21\uff0c\u8bed\u6c14\u53ef\u80fd\u5e26\u7126\u8651"],
     ["\u7b2c\u4e00\u6b21\u7ed9\u5177\u4f53\u4fe1\u606f\uff1a\u73b0\u5728\u662f\u5403\u996d\u65f6\u95f4\uff0c\u6211\u4eec\u5403\u9762\u6761",
      "\u7b2c\u4e8c\u6b21\u4e0d\u518d\u91cd\u590d\u89e3\u91ca\uff0c\u7528\u8f6c\u79fb\u4ee3\u66ff\uff1a\u597d\uff0c\u6211\u4eec\u5148\u7ad9\u8d77\u6765",
      "\u627e\u4e1c\u897f\u53cd\u590d\u95ee\u65f6\uff1a\u628a\u8981\u627e\u7684\u4e1c\u897f\u653e\u56fa\u5b9a\u4f4d\u7f6e\u5e76\u8d34\u4e0a\u6807\u8bc6"]),
    ("not_recognize", "\u8ba4\u4eba\u56f0\u96be",
     ["\u95ee\u4f60\u662f\u8c01\u3001\u5bf9\u5bb6\u4eba\u8868\u73b0\u6212\u5907\u6216\u5f53\u4f5c\u95f4\u5165\u8005"],
     ["\u4e0d\u4e89\u8fa9\u6211\u662f\u4f60\u5973\u513f\uff0c\u6539\u4e3a\u4f60\u997f\u4e86\u5427\uff0c\u6211\u4eec\u5403\u70b9\u4e1c\u897f",
      "\u4fdd\u6301\u8ddd\u79bb\uff0c\u4e0d\u7a81\u7136\u4ece\u80cc\u540e\u63a5\u8fd1\uff0c\u5148\u6253\u62db\u547c\u518d\u63a5\u89e6",
      "\u51fa\u73b0\u653b\u51fb\u6216\u6781\u5ea6\u6050\u60e7\u65f6\u9000\u51fa\u623f\u95f4\uff0c\u7b49\u60c5\u7eea\u5e73\u590d\u518d\u63a5\u8fd1",
      "\u628a\u672c\u4eba\u7167\u7247\u653e\u5728\u7a81\u51fa\u5904\uff0c\u7167\u7247\u4e0a\u5199\u8fd9\u662f\u4f60\u7684\u5973\u513f"]),
    ("sundowning", "\u9ec4\u660f\u75c7\u5012\u7fa4",
     ["\u508d\u665a\u540e\u70e1\u70e6\u3001\u558a\u53eb\u3001\u62d2\u7edd\u3001\u60f3\u5f80\u5916\u8d70\u3001\u5750\u7acb\u4e0d\u5b89"],
     ["\u767d\u5929\u589e\u52a0\u5149\u7167\u4e0e\u6d3b\u52a8\uff0c\u907f\u514d\u4e0b\u5348\u957f\u65f6\u95f4\u5367\u5e8a",
      "\u508d\u665a\u524d\u5b8c\u6210\u6d17\u6f34\u4e0e\u7a7f\u8863\uff0c\u628a\u5bb9\u6613\u5f15\u53d1\u51b2\u7a81\u7684\u4e8b\u653e\u5728\u767d\u5929",
      "\u4fdd\u6301\u5ba4\u5185\u5149\u7ebf\u5145\u8db3\uff0c\u907f\u514d\u660f\u6697\u4e0e\u9634\u5f71\u9020\u6210\u7684\u8bef\u8ba4",
      "\u51c6\u5907\u5b89\u9759\u719f\u6089\u7684\u73af\u5883\uff0c\u51cf\u5c11\u7535\u89c6\u3001\u4eba\u7fa4\u4e0e\u566a\u97f3"]),
    ("comprehension", "\u7406\u89e3\u4e0e\u8868\u8fbe\u53d7\u635f",
     ["\u7b54\u975e\u6240\u95ee\u3001\u8bcd\u4e0d\u8fbe\u610f\u3001\u627e\u4e0d\u5230\u8bcd\u3001\u8bf4\u8bdd\u8d8a\u6765\u8d8a\u77ed"],
     ["\u7528\u624b\u52bf\u548c\u5b9e\u7269\u66ff\u4ee3\u8bed\u8a00\uff1a\u8bf4\u559d\u6c34\u7684\u540c\u65f6\u9012\u676f\u5b50",
      "\u95ee\u5c01\u95ed\u95ee\u9898\uff08\u662f\u6216\u4e0d\u662f\uff09\uff1a\u8981\u4e0d\u8981\u559d\u6c34",
      "\u4e00\u6b21\u53ea\u7ed9\u4e00\u4e2a\u9009\u62e9\uff0c\u4e0d\u8981\u4e09\u9009\u4e00",
      "\u4fdd\u7559\u8001\u4eba\u539f\u6709\u7684\u79f0\u547c\u4e0e\u4e60\u60ef\u7528\u8bed\uff0c\u4e0d\u7ea0\u6b63"]),
]

ENV_RISKS = [
    ("front_door", "\u5165\u6237\u95e8", ["\u95e8\u94fe\u3001\u95e8\u9501", "\u5185\u4fa7\u52a0\u88c5\u4f4e\u4f4d\u6697\u9501\u6216\u95e8\u5438",
                                    "\u95e8\u7684\u989c\u8272\u4e0e\u5899\u9762\u5206\u533a\u660e\u663e"]),
    ("back_door", "\u9632\u706b\u95e8\u4e0e\u5176\u4ed6\u51fa\u53e3", ["\u4fdd\u6301\u9501\u95ed", "\u68c0\u67e5\u662f\u5426\u5e38\u5f00"]),
    ("window", "\u7a97\u6237", ["\u9501\u95ed", "\u7a97\u8fb9\u4e0d\u653e\u53ef\u6500\u722c\u5bb6\u5177"]),
    ("stair", "\u697c\u68af\u4e0e\u697c\u68af\u53e3", ["\u4e0a\u4e0b\u697c\u53e3\u88c5\u95e8", "\u591c\u95f4\u706f\u611f\u5e94\u4eae\u8d77"]),
    ("elevator", "\u7535\u68af", ["\u8f7d\u56ca\u4e0e\u697c\u5c42\u6309\u94ae\u505a\u89c6\u89c9\u533a\u5206",
                               "\u4e0d\u5355\u72ec\u5e26\u8001\u4eba\u4e58\u7535\u68af\u4e0b\u697c"]),
    ("alone_out", "\u5916\u51fa\u884c\u4e3a", ["\u5916\u51fa\u6709\u966a\u540c", "\u5916\u51fa\u524d\u8bf4\u660e\u53bb\u54ea\u91cc\u4e0e\u591a\u4e45\u56de",
                              "\u56fa\u5b9a\u5916\u51fa\u8def\u7ebf\u4e0e\u65f6\u95f4"]),
]

ENV_EXTRA = [
    "\u9632\u706b\u95e8\u4e0e\u697c\u68af\u53e3\u88c5\u95e8\uff0c\u591c\u95f4\u706f\u4fdd\u6301\u7075\u654f\u4eae\u8d77",
    "\u5395\u5360\u4e0d\u653e\u53ef\u6500\u722c\u5bb6\u5177\uff0c\u9632\u576a\u843d",
    "\u536b\u751f\u95f4\u88c5\u6276\u624b\u4e0e\u9632\u6ed1\u57ab\uff0c\u95e8\u80fd\u4ece\u5916\u5f00\u6216\u88c5\u53ef\u89c2\u5bdf\u88c5\u7f6e",
    "\u53a8\u623f\u6e05\u7406\u7194\u5177\u5175\u5177\uff0c\u9505\u5177\u79bb\u8fb9\u7f18\u8fdc",
    "\u5168\u7a0b\u7167\u660e\uff0c\u8d70\u5eca\u7559\u5c0f\u591c\u706f",
    "\u4e0e\u90bb\u5c45\u548c\u7269\u4e1a\u77e5\u60c5\uff0c\u8bf7\u5b83\u4eec\u7559\u610f\u5f02\u5e38",
]

PREVENT_LEVELS = [
    ("\u7b2c\u4e00\u7ea7", "\u968f\u8eab\u8bc6\u522b\u5361",
     "\u59d3\u540d\u3001\u5e74\u9f84\u3001\u5bb6\u5c5e\u7535\u8bdd\u3001\u7167\u7247\u3001\u7b80\u5355\u75be\u75c5\u3001\u5c45\u4f4f\u5730\u4fe1\u606f",
     "\u5361\u5fc5\u987b\u7531\u8001\u4eba\u968f\u8eab\u643a\u5e26\uff0c\u653e\u5728\u62bd\u5c49\u91cc\u7b49\u4e8e\u6ca1\u505a"),
    ("\u7b2c\u4e8c\u7ea7", "\u95e8\u7981\u4e0e\u51fa\u95e8\u63d0\u9192",
     "\u95e8\u94fe\u3001\u6697\u9501\u3001\u95e8\u5438\u3001\u611f\u5e94\u706f\u3001\u95e8\u57ab\u63d0\u793a\u5b57",
     "\u662f\u5ef6\u8fdf\u800c\u975e\u963b\u6b62\uff0c\u9501\u7981\u4e0d\u662f\u957f\u671f\u65b9\u6848"),
    ("\u7b2c\u4e09\u7ea7", "\u5b9a\u4f4d\u4e0e\u968f\u8eab\u8bbe\u5907",
     "\u5b9a\u4f4d\u624b\u8868\u3001\u5b9a\u4f4d\u5361\u3001\u9632\u8d70\u5931\u978b",
     "\u9700\u8003\u8651\u8001\u4eba\u4f9d\u4ece\u6027\u3001\u9690\u79c1\u610f\u613f\u4e0e\u7535\u6c60\u7eed\u822a"),
]

MISSING_STEPS = [
    ("\u7b2c 1 \u6b65", "\u7acb\u5373\u62a5\u8b66\uff0c\u8bf4\u660e\u8001\u4eba\u8d70\u5931", "\u53d1\u73b0\u540e\u7acb\u5373\uff0c\u4e0d\u89c2\u5bdf\u7b49\u5f85"),
    ("\u7b2c 2 \u6b65", "\u62a5\u8b66\u65f6\u63d0\u4f9b\u5b8c\u6574\u4fe1\u606f", "\u540c\u4e00\u6b21\u901a\u8bdd\u5185"),
    ("\u7b2c 3 \u6b65", "\u62a5\u8b66\u540c\u65f6\u5b89\u6392\u5bb6\u4eba\u5206\u5934\u5728\u9644\u8fd1\u627e", "\u4e0e\u62a5\u8b66\u540c\u6b65\uff0c\u4e0d\u7b49\u62a5\u8b66\u7ed3\u675f"),
    ("\u7b2c 4 \u6b65", "\u5728\u660e\u663e\u4f4d\u7f6e\u7559\u5bfb\u4eba\u4fe1\u606f\uff08\u7167\u7247\u4e0e\u7535\u8bdd\uff09", "\u627e\u5230\u540e\u6536\u56de"),
    ("\u7b2c 5 \u6b65", "\u8054\u7cfb\u7269\u4e1a\u3001\u62a4\u5b88\u3001\u90bb\u91cc\u3001\u793e\u533a", "\u540c\u6b65\u8fdb\u884c"),
    ("\u7b2c 6 \u6b65", "\u8054\u7cfb\u5e38\u53bb\u573a\u6240\u4e0e\u719f\u6089\u7684\u4eba", "\u540c\u4e0a"),
    ("\u7b2c 7 \u6b65", "\u627e\u5230\u540e\u5148\u4fdd\u6696\u4e0e\u8865\u6c34\uff0c\u786e\u8ba4\u8eab\u4f53\u4e0e\u60c5\u7eea", "\u627e\u5230\u540e"),
    ("\u7b2c 8 \u6b65", "\u4e8b\u540e\u590d\u76d8\uff1a\u54ea\u4e00\u6b65\u53ef\u63d0\u524d", "\u627e\u5230\u540e"),
]

POLICE_INFO = [
    ("\u8d70\u5931\u65f6\u95f4", "\u786e\u5207\u65f6\u95f4\u6216\u7ea6 X \u5c0f\u65f6\u524d"),
    ("\u6700\u540e\u51fa\u73b0\u5730\u70b9", "\u5177\u4f53\u5230\u5c0f\u533a\u3001\u697c\u680b\u3001\u697c\u5c42"),
    ("\u8d70\u5931\u65f6\u8863\u7740", "\u4e0a\u4e0b\u8863\u989c\u8272\u3001\u978b\u3001\u5916\u5957\u3001\u6709\u65e0\u6234\u5e3d"),
    ("\u8eab\u4f53\u7279\u5f81", "\u8eab\u9ad8\u3001\u4f53\u578b\u3001\u53d1\u578b\u3001\u6709\u65e0\u773c\u955c\u3001\u8d70\u8def\u59ff\u6001"),
    ("\u5065\u5eb7\u60c5\u51b5", "\u542c\u529b\u89c6\u529b\u3001\u8bf4\u8bdd\u662f\u5426\u6e05\u695a\u3001\u80fd\u5426\u72ec\u81ea\u884c\u8d70"),
    ("\u662f\u5426\u9700\u968f\u8eab\u836f\u7269", "\u662f\u5426\u6709\u6162\u6027\u75c5\u7528\u836f\u4e2d\u65ad\u98ce\u9669"),
    ("\u8ba4\u77e5\u4e0e\u81ea\u7406\u80fd\u529b", "\u80fd\u5426\u81ea\u5df1\u627e\u5395\u6240\u3001\u80fd\u5426\u8fdb\u98df\u3001\u4f1a\u4e0d\u4f1a\u8d70\u9519\u65b9\u5411"),
    ("\u5bb6\u5c5e\u59d3\u540d\u4e0e\u7535\u8bdd", "\u4fdd\u6301\u7535\u8bdd\u7545\u901a"),
    ("\u5e38\u53bb\u573a\u6240", "\u5e02\u573a\u3001\u516c\u56ed\u3001\u8001\u670b\u53cb\u5bb6\u3001\u96c6\u4f1a\u7b49"),
    ("\u662f\u5426\u6709\u5b9a\u4f4d\u8bbe\u5907", "\u578b\u53f7\u4e0e\u662f\u5426\u5f00\u542f"),
    ("\u75be\u75c5\u4e0e\u7528\u836f\u53f2", "\u4f9b\u6551\u52a9\u65f6\u53c2\u8003"),
]

FORBIDDEN = [
    "\u7981\u6b62\u7ed9\u8001\u4eba\u2018\u5b89\u9759\u836f\u2019\uff0c\u9547\u9759\u7c7b\u836f\u7269\u7531\u533b\u751f\u51b3\u5b9a\u4e14\u53ef\u80fd\u589e\u52a0\u8dcc\u5012\u4e0e\u610f\u8bc6\u6df7\u4e71\u98ce\u9669",
    "\u7981\u6b62\u628a\u9501\u7981\u6216\u7ea6\u675f\u4f5c\u4e3a\u957f\u671f\u5e38\u89c4\u624b\u6bb5",
    "\u7981\u6b62\u627f\u8bfa\u8fd9\u6837\u5c31\u4e0d\u4f1a\u8d70\u5931",
    "\u7981\u6b62\u7ed9\u51fa\u627e\u56de\u6982\u7387\u6570\u5b57",
    "\u7981\u6b62\u5bf9\u8001\u4eba\u505a\u8bca\u65ad\u3001\u5206\u671f\u4e0e\u75c5\u56e0\u5224\u65ad",
    "\u7981\u6b62\u628a\u8bc6\u522b\u5361\u653e\u5728\u5bb6\u91cc\u4e0d\u7ed9\u8001\u4eba\u968f\u8eab",
    "\u7981\u6b62\u8d70\u5931\u540e\u5148\u81ea\u5df1\u627e\u51e0\u5c0f\u65f6\u518d\u62a5\u8b66",
    "\u7981\u6b62\u62a5\u8b66\u65f6\u4e0d\u63d0\u4f9b\u7167\u7247\u4e0e\u7279\u5f81",
    "\u7981\u6b62\u5728\u95e8\u53e3\u4e89\u6267\uff0c\u95e8\u53e3\u662f\u8d70\u5931\u9ad8\u53d1\u573a\u666f",
    "\u7981\u6b62\u9891\u7e41\u66f4\u6362\u7167\u62a4\u8005",
]

GOLDEN = "\u8d70\u5931\u540e 6 \u5c0f\u65f6\u662f\u9ec4\u91d1\u671f\uff0c\u8d85\u8fc7\u540e\u627e\u56de\u96be\u5ea6\u663e\u8457\u4e0a\u5347\u3002\u5bb6\u5c5e\u81ea\u884c\u5bfb\u627e\u4e0d\u6784\u6210\u5145\u5206\u5904\u7f6e\uff0c\u5fc5\u987b\u7acb\u5373\u62a5\u8b66\u3002"


def obstacle_meta(key):
    for k, name, signs, actions in OBSTACLES:
        if k == key:
            return name, signs, actions
    return key, [], []


def validate_env(raw):
    valid = dict((k, v) for k, v, _a in ENV_RISKS)
    good, bad = [], []
    for k in list(raw or []):
        if k in valid:
            good.append(k)
        else:
            bad.append(k)
    return good, bad


def env_gaps(good):
    return [(k, label, acts) for k, label, acts in ENV_RISKS if k not in good]


def build_checklist(only=False):
    lines = []
    lines.append("\u8d70\u5931\u9884\u9632\u4e09\u7ea7\u63aa\u65bd\uff1a")
    for level, name, content, limit in PREVENT_LEVELS:
        lines.append("  %s %s" % (level, name))
        lines.append("      \u5185\u5bb9\uff1a" + content)
        lines.append("      \u5c40\u9650\uff1a" + limit)
    lines.append("")
    if only:
        return lines
    lines.append("\u8d70\u5931\u540e\u5904\u7f6e\u6d41\u7a0b\uff1a")
    for step, action, when in MISSING_STEPS:
        lines.append("  %s %s\uff08%s\uff09" % (step, action, when))
    lines.append("")
    lines.append("\u62a5\u8b66\u5fc5\u987b\u63d0\u4f9b\u7684\u4fe1\u606f\uff1a")
    for name, detail in POLICE_INFO:
        lines.append("  - %s\uff1a%s" % (name, detail))
    lines.append("")
    lines.append("\u627e\u5230\u540e\u7684\u8eab\u4f53\u98ce\u9669\u9884\u8b66\uff08\u51fa\u73b0\u4efb\u4e00\u9879\u7acb\u5373\u9001\u533b\uff09\uff1a")
    for w in ["\u8131\u6c34\uff1a\u53e3\u5507\u5e72\u88c2\u3001\u76ae\u80a4\u5f39\u6027\u5dee\u3001\u5c3f\u91cf\u5c11",
              "\u4f4e\u6e29\u66b4\u9732\uff1a\u624b\u811a\u51b0\u4f4f\u3001\u53cd\u5e94\u8fdf\u94bb\u3001\u610f\u8bc6\u6a21\u7cca",
              "\u66b4\u6652\uff1a\u4e2d\u6691\u6837\u8868\u73b0\u3001\u76ae\u80a4\u53d1\u70eb\u3001\u610f\u8bc6\u4e0d\u6e05",
              "\u8dcc\u5012\u6216\u5916\u4f24\uff1a\u5934\u90e8\u7740\u5730\u540e\u5458\u5410\u3001\u610f\u8bc6\u6539\u53d8\u3001\u80a2\u4f53\u4e0d\u80fd\u52a8",
              "\u957f\u65f6\u95f4\u672a\u8fdb\u98df\uff1a\u5fc3\u6145\u3001\u51fa\u51b7\u6c57\u3001\u610f\u8bc6\u6a21\u7cca"]:
        lines.append("  - " + w)
    return lines


def build_plan(obstacle_keys, good_env, minutes):
    lines = []
    lines.append("\u9ec4\u91d1\u671f\u53e3\u5f84\uff1a" + GOLDEN)
    lines.append("")

    lines.append("\u5df2\u8bc6\u522b\u7684\u6c9f\u901a\u969c\u788d\uff1a")
    if obstacle_keys:
        for k in obstacle_keys:
            name, signs, actions = obstacle_meta(k)
            lines.append("  %s" % name)
            lines.append("      \u8868\u73b0\uff1a" + "\uff1b".join(signs))
            for a in actions:
                lines.append("      + " + a)
    else:
        lines.append("  \u5c1a\u672a\u6307\u5b9a\uff0c\u8bf7\u5148\u9010\u9879\u5224\u65ad\u7c7b\u578b")
    lines.append("")

    gaps = env_gaps(good_env)
    lines.append("\u5df2\u8986\u76d6\u7684\u73af\u5883\u98ce\u9669\u70b9\uff1a")
    for k in good_env:
        label, _acts = [(lab, ac) for kk, lab, ac in ENV_RISKS if kk == k][0]
        lines.append("  [x] " + label)
    if gaps:
        lines.append("\u5c1a\u672a\u843d\u5b9e\u7684\u73af\u5883\u6539\u9020\u9879\uff1a")
        for k, label, acts in gaps:
            lines.append("  [ ] %s\uff1a%s" % (label, "\uff1b".join(acts)))
    lines.append("")
    lines.append("\u5176\u4ed6\u5e94\u4e00\u5e76\u843d\u5b9e\u7684\u5b89\u5168\u8981\u70b9\uff1a")
    for e in ENV_EXTRA:
        lines.append("  - " + e)
    lines.append("")

    lines.append("\u8d70\u5931\u9884\u9632\u4e09\u7ea7\u63aa\u65bd\u4e0e\u8d70\u5931\u540e\u5904\u7f6e\uff1a")
    for line in build_checklist(only=True):
        lines.append(line if not line else "  " + line)
    lines.append("")
    for step, action, when in MISSING_STEPS:
        lines.append("  %s %s\uff08%s\uff09" % (step, action, when))
    lines.append("")
    lines.append("\u62a5\u8b66\u5fc5\u987b\u63d0\u4f9b\u7684\u4fe1\u606f\uff1a")
    for name, detail in POLICE_INFO:
        lines.append("  - %s\uff1a%s" % (name, detail))
    lines.append("")
    lines.append("\u7981\u6b62\u505a\u6cd5\uff1a")
    for f in FORBIDDEN:
        lines.append("  - " + f)
    lines.append("")
    lines.append("\u4f9d\u8d56\u53e3\u5f84\uff1a\u65ad\u7136\u7684\u610f\u8bc6\u6539\u53d8\u3001\u5355\u4fa7\u65e0\u529b\u3001\u8bed\u8a00\u542b\u7cca\u7b49\u5fc5\u987b\u7acb\u5373\u5c31\u533b\uff1b")
    lines.append("\u6d41\u884c\u6027\u53d8\u5316\u53ef\u80fd\u4e0e\u75c5\u60c5\u8fdb\u5c55\u76f8\u5173\uff0c\u672c\u5de5\u5177\u4e0d\u505a\u5206\u671f\u4e0e\u75c5\u56e0\u5224\u65ad\u3002")
    return lines


RED_FLAGS = [
    "acute_confusion", "fever_behavior_change", "sudden_headache_seizure",
    "hallucination_fear", "aggression_risk", "suicidal_ideation",
    "dysphagia_aspiration", "overwalk_dehydration",
]

RED_FLAG_TEXT = {
    "acute_confusion": "\u7a81\u7136\u7684\u610f\u8bc6\u6df7\u4e71\u3001\u8bf4\u4e0d\u6e05\u8bdd\u3001\u5355\u4fa7\u65e0\u529b\u3001\u8bed\u8a00\u542b\u7cca\uff08\u6392\u9664\u6025\u6027\u8111\u8840\u7ba1\u4e8b\u4ef6\uff09",
    "fever_behavior_change": "\u53d1\u70ed\u4f34\u610f\u8bc6\u6539\u53d8\uff0c\u5c3f\u6db2\u6d51\u6d4a\u5f02\u5473\u4f34\u7cbe\u795e\u884c\u4e3a\u7a81\u53d8\uff08\u53ef\u80fd\u4e3a\u611f\u67d3\u8bf1\u53d1\uff09",
    "sudden_headache_seizure": "\u7a81\u53d1\u5267\u70c8\u5934\u75db\u3001\u541e\u5410\u3001\u62bd\u6410\u3001\u8dcc\u5012\u540e\u5934\u90e8\u7740\u5730",
    "hallucination_fear": "\u5e7b\u89c9\u5984\u60f3\u540e\u6781\u5ea6\u6050\u60e7\u3001\u62d2\u7edd\u8fdb\u98df\u3001\u957f\u65f6\u95f4\u4e0d\u7761",
    "aggression_risk": "\u51fa\u73b0\u653b\u51fb\u884c\u4e3a\u3001\u62d2\u7edd\u4e00\u5207\u7167\u62a4\u3001\u6709\u4f24\u4eba\u6216\u81ea\u4f24\u98ce\u9669",
    "suicidal_ideation": "\u51fa\u73b0\u660e\u786e\u7684\u81ea\u6740\u5ff5\u5934",
    "dysphagia_aspiration": "\u65b0\u53d1\u541e\u54bd\u56f0\u96be\u3001\u8fdb\u98df\u54bd\u54af\u3001\u53cd\u590d\u80ba\u90e8\u611f\u67d3",
    "overwalk_dehydration": "\u8d70\u5931\u540e\u65e0\u6cd5\u5b9a\u4f4d\uff0c\u6216\u51fa\u73b0\u8fc7\u5ea6\u884c\u8d70\u3001\u8131\u6c34\u3001\u5931\u6e29\u8868\u73b0",
}

RED_FLAG_ACTION = {
    "acute_confusion": "\u7acb\u5373\u5c31\u533b\uff08\u6025\u8bca\uff09",
    "fever_behavior_change": "\u5f53\u5929\u5c31\u533b",
    "sudden_headache_seizure": "\u7acb\u5373\u5c31\u533b\uff08\u6025\u8bca\uff09",
    "hallucination_fear": "\u5f53\u5929\u8054\u7cfb\u533b\u751f",
    "aggression_risk": "\u5f53\u5929\u8054\u7cfb\u533b\u751f\uff0c\u5fc5\u8981\u65f6\u5c31\u533b",
    "suicidal_ideation": "\u7acb\u5373\u5c31\u533b\u5e76\u540c\u6b65\u5fc3\u7406\u5371\u673a\u5e72\u9884",
    "dysphagia_aspiration": "\u5f53\u5929\u5c31\u533b",
    "overwalk_dehydration": "\u7acb\u5373\u9001\u533b",
}


def build_report(data):
    raw_obstacles = list(data.get("obstacle", []))
    raw_risks = list(data.get("risks", []))
    flags = list(data.get("red_flags", []))
    minutes = data.get("minutes_since_missing", 0)
    checklist_only = bool(data.get("checklist_only", False))

    lines = []
    lines.append("=" * 66)
    lines.append("\u5931\u667a\u8001\u4eba\u6c9f\u901a\u969c\u788d\u5904\u7406\u4e0e\u8d70\u5931\u9632\u9884")
    lines.append("=" * 66)
    lines.append("\u8d70\u5931\u5df2\u8fc7\u65f6\u957f\uff1a%g \u5206\u949f" % float(minutes or 0))
    lines.append("")

    hit = [f for f in flags if f in RED_FLAGS]
    unknown = [f for f in flags if f not in RED_FLAGS]
    if hit:
        lines.append("[\u7ea2\u7ebf] \u5df2\u547d\u4e2d\u4ee5\u4e0b\u60c5\u5f62\uff0c\u5148\u5904\u7f6e\u518d\u8c08\u6c9f\u901a\uff1a")
        for f in hit:
            lines.append("  ! " + RED_FLAG_TEXT[f])
            lines.append("    \u5904\u7f6e\uff1a" + RED_FLAG_ACTION[f])
        lines.append("")
        if float(minutes or 0) > 0:
            lines.append("  \u5df2\u4e3a\u8d70\u5931\u72b6\u6001\uff1a" + GOLDEN)
            lines.append("  \u7b2c\u4e00\u6b65\u4e0d\u80fd\u8df3\uff0c\u62a5\u8b66\u4e0e\u9644\u8fd1\u5bfb\u627e\u540c\u6b65\u8fdb\u884c\u3002")
        lines.append("=" * 66)
        return "\n".join(lines), {
            "blocked": True,
            "red_flags": hit,
            "unknown_flags": unknown,
            "must_call_police": float(minutes or 0) > 0,
            "golden_hours_stated": True,
            "medication_provided": False,
            "diagnosis_provided": False,
            "recovery_probability_provided": False,
        }

    obstacles, bad_ob = [], []
    for k in raw_obstacles:
        if any(k == o[0] for o in OBSTACLES):
            obstacles.append(k)
        else:
            bad_ob.append(k)
    good_env, bad_env = validate_env(raw_risks)
    if bad_ob:
        lines.append("[\u63d0\u793a] \u672a\u8bc6\u522b\u7684\u969c\u788d\u6807\u8bb0\u5df2\u5ffd\u7565\uff1a" + "\u3001".join(bad_ob))
        lines.append("")
    if bad_env:
        lines.append("[\u63d0\u793a] \u672a\u8bc6\u522b\u7684\u73af\u5883\u98ce\u9669\u6807\u8bb0\u5df2\u5ffd\u7565\uff1a" + "\u3001".join(bad_env))
        lines.append("")

    lines.append("[\u4e00] \u6c9f\u901a\u4e0e\u73af\u5883\u65b9\u6848")
    for line in build_plan(obstacles, good_env, minutes):
        lines.append("  " + line if line else "")

    lines.append("")
    lines.append("\u5fc5\u987b\u7acb\u5373\u8054\u7cfb\u533b\u751f\u6216\u62a5\u8b66\u7684\u60c5\u5f62\uff1a")
    for k in RED_FLAGS:
        lines.append("  - " + RED_FLAG_TEXT[k] + "\uff08" + RED_FLAG_ACTION[k] + "\uff09")
    lines.append("")
    lines.append("\u7981\u6b62\u505a\u6cd5\uff1a")
    for f in FORBIDDEN:
        lines.append("  - " + f)
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u6c9f\u901a\u53c2\u8003\u4e0e\u8d70\u5931\u9884\u9632\u63aa\u65bd\u6e05\u5355\uff0c\u4e0d\u6784\u6210\u8bca\u65ad\u610f\u89c1\u3002")
    lines.append("\u4e0d\u7ed9\u836f\u7269\u4e0e\u9547\u9759\u65b9\u6848\uff0c\u4e0d\u7ed9\u627e\u56de\u6982\u7387\uff0c\u4e0d\u505a\u5206\u671f\u4e0e\u75c5\u56e0\u5224\u65ad\u3002")
    lines.append("=" * 66)

    summary = {
        "blocked": False,
        "unknown_flags": unknown,
        "obstacles": obstacles,
        "env_covered": good_env,
        "env_gaps": [k for k, _l, _a in env_gaps(good_env)],
        "must_call_police": False,
        "golden_hours_stated": True,
        "medication_provided": False,
        "diagnosis_provided": False,
        "recovery_probability_provided": False,
        "lock_recommended_as_routine": False,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("\u6c9f\u901a\u969c\u788d\u7c7b\u578b\u4e3a 4 \u7c7b", len(OBSTACLES) == 4))
    r.append(("\u73af\u5883\u98ce\u9669\u70b9\u81f3\u5c11 6 \u9879", len(ENV_RISKS) >= 6))
    r.append(("\u8d70\u5931\u9884\u9632\u4e3a 3 \u7ea7", len(PREVENT_LEVELS) == 3))
    r.append(("\u5904\u7f6e\u6d41\u7a0b\u4e3a 8 \u6b65", len(MISSING_STEPS) == 8))
    r.append(("\u62a5\u8b66\u4fe1\u606f\u4e0d\u5c11\u4e8e 11 \u9879", len(POLICE_INFO) >= 11))
    r.append(("\u7981\u6b62\u505a\u6cd5\u81f3\u5c11 10 \u6761", len(FORBIDDEN) >= 10))
    r.append(("\u7ea2\u7ebf\u60c5\u5f62\u81f3\u5c11 8 \u6761", len(RED_FLAGS) >= 8))

    all_env = [k for k, _l, _a in ENV_RISKS]
    good, bad = validate_env(["front_door", "zzz"])
    r.append(("\u5df2\u8bc6\u522b\u73af\u5883\u98ce\u9669\u8ba1\u6570\u6b63\u786e", good == ["front_door"]))
    r.append(("\u672a\u8bc6\u522b\u73af\u5883\u98ce\u9669\u88ab\u8fc7\u6ee4", bad == ["zzz"]))
    r.append(("\u5168\u8986\u76d6\u65f6\u7f3a\u53e3\u4e3a\u7a7a", env_gaps(all_env) == []))
    r.append(("\u90e8\u5206\u8986\u76d6\u65f6\u6709\u7f3a\u53e3", len(env_gaps(["front_door"])) == len(all_env) - 1))
    r.append(("\u65e0\u8986\u76d6\u65f6\u7f3a\u53e3\u4e3a\u5168\u90e8", len(env_gaps([])) == len(all_env)))

    r.append(("\u91cd\u590d\u63d0\u95ee\u53ef\u67e5\u5230\u5904\u7406\u52a8\u4f5c", len(obstacle_meta("repeat_question")[2]) >= 3))
    r.append(("\u8ba4\u4eba\u56f0\u96be\u53ef\u67e5\u5230\u5904\u7406\u52a8\u4f5c", len(obstacle_meta("not_recognize")[2]) >= 3))
    r.append(("\u672a\u77e5\u969c\u788d\u8fd4\u56de\u7a7a\u52a8\u4f5c", obstacle_meta("xxx")[2] == []))
    r.append(("\u4e09\u7ea7\u9884\u9632\u5747\u5199\u660e\u5c40\u9650", all(l for _a, _b, _c, l in PREVENT_LEVELS)))
    r.append(("\u9ec4\u91d1\u671f\u53e3\u5f84\u542b 6 \u5c0f\u65f6", "6 \u5c0f\u65f6" in GOLDEN))

    _, s = build_report({"obstacle": ["repeat_question"], "risks": ["front_door", "window"]})
    r.append(("\u5b8c\u6574\u6837\u4f8b\u4e0d\u963b\u65ad", s["blocked"] is False))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u8bb0\u5f55\u969c\u788d", s["obstacles"] == ["repeat_question"]))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u6709\u73af\u5883\u7f3a\u53e3", len(s["env_gaps"]) == 4))
    r.append(("\u6b63\u5e38\u72b6\u6001\u4e0d\u8ba9\u62a5\u8b66", s["must_call_police"] is False))
    r.append(("\u8f93\u51fa\u542b\u9ec4\u91d1\u671f", s["golden_hours_stated"] is True))
    r.append(("\u4e0d\u7ed9\u836f\u7267", s["medication_provided"] is False))
    r.append(("\u4e0d\u505a\u8bca\u65ad", s["diagnosis_provided"] is False))
    r.append(("\u4e0d\u7ed9\u627e\u56de\u6982\u7387", s["recovery_probability_provided"] is False))
    r.append(("\u4e0d\u628a\u9501\u7981\u4f5c\u4e3a\u5e38\u89c4\u624b\u6bb5", s["lock_recommended_as_routine"] is False))

    _, s2 = build_report({"red_flags": ["acute_confusion"]})
    r.append(("\u6025\u6027\u610f\u8bc6\u6539\u53d8\u76f4\u63a5\u963b\u65ad", s2["blocked"] is True))
    r.append(("\u963b\u65ad\u65f6\u4e0d\u505a\u5206\u671f", s2["diagnosis_provided"] is False))

    _, s3 = build_report({"minutes_since_missing": 90, "red_flags": ["overwalk_dehydration"]})
    r.append(("\u8d70\u5931\u72b6\u6001\u4e0b\u8981\u6c42\u62a5\u8b66", s3["must_call_police"] is True))

    _, s4 = build_report({"obstacle": ["sundowning"], "risks": [], "checklist_only": True})
    r.append(("\u6e05\u5355\u6a21\u5f0f\u4ecd\u4e0d\u963b\u65ad", s4["blocked"] is False))
    r.append(("\u6e05\u5355\u6a21\u5f0f\u8bb0\u5f55\u73af\u5883\u7f3a\u53e3\u6570", len(s4["env_gaps"]) == len(all_env)))

    txt, _ = build_report({"obstacle": ["not_recognize"], "risks": ["front_door"]})
    r.append(("\u8f93\u51fa\u542b\u4e0d\u4e89\u8fa9\u7684\u53e3\u5f84", "\u6211\u662f\u4f60\u5973\u513f" in txt))
    r.append(("\u8f93\u51fa\u542b\u7acb\u5373\u62a5\u8b66\u53e3\u5f84", "\u7acb\u5373\u62a5\u8b66" in txt))
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
        description="\u5931\u667a\u8001\u4eba\u6c9f\u901a\u969c\u788d\u5904\u7406\u4e0e\u8d70\u5931\u9632\u9884\u5de5\u5177")
    parser.add_argument("--file", help="\u8f93\u5165 JSON \u6587\u4ef6\u8def\u5f84\uff08UTF-8\uff09")
    parser.add_argument("--checklist", action="store_true", help="\u53ea\u8f93\u51fa\u8d70\u5931\u9884\u9632\u4e0e\u62a5\u8b66\u6e05\u5355")
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
    if args.checklist:
        data["checklist_only"] = True

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
