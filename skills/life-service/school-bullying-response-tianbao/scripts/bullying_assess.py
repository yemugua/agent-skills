# -*- coding: utf-8 -*-
"""\u6821\u56ed\u9738\u51cc\u4e94\u7ef4\u5224\u5b9a\u4e0e\u5904\u7f6e\u987a\u5e8f\u751f\u6210\u5de5\u5177\u3002

\u7528\u6cd5:
  python bullying_assess.py --file case.json [--json]
  python bullying_assess.py --selftest

\u672c\u5de5\u5177\u4e0d\u4f5c\u5b9a\u6027\u7ed3\u8bba\uff0c\u4e0d\u63d0\u4f9b\u836f\u7269\u4e0e\u5fc3\u7406\u6cbb\u7597\u65b9\u6848\uff0c\u4e0d\u7ec4\u7ec7\u79c1\u81ea\u53d6\u8bc1\u3002
"""
import argparse
import io
import json
import os
import sys

DIMENSIONS = [
    ("repeated", "D1 \u91cd\u590d\u53d1\u751f", "\u53d1\u751f\u8fc7 2 \u6b21\u53ca\u4ee5\u4e0a\uff0c\u6216\u6301\u7eed 2 \u5468\u4ee5\u4e0a", "\u5199\u6e05\u7b2c 1 \u6b21\u4e0e\u6700\u8fd1 1 \u6b21\u7684\u65f6\u95f4"),
    ("intentional", "D2 \u6545\u610f\u4e3a\u4e4b", "\u6709\u9884\u8c0b\u6216\u84c4\u610f\uff0c\u5305\u62ec\u6311\u65f6\u673a\u907f\u5f00\u8001\u5e08\u3001\u7ed3\u4f19", "\u5199\u6e05\u9884\u8c0b\u8ff9\u8c61"),
    ("power_imbalance", "D3 \u529b\u91cf\u4e0d\u5bf9\u7b49", "\u4eba\u6570\u3001\u4f53\u683c\u3001\u5730\u4f4d\u3001\u6027\u522b\u7b49\u4e0d\u5bf9\u79f0", "\u5199\u6e05\u4e0d\u5bf9\u7b49\u7684\u5177\u4f53\u5f62\u5f0f"),
    ("harm", "D4 \u9020\u6210\u4f24\u5bb3", "\u8eab\u4f53\u3001\u5fc3\u7406\u3001\u8d22\u7269\u3001\u540d\u8a89\u4e0e\u9690\u79c1\u53d7\u635f", "\u5199\u6e05\u4f24\u5bb3\u5f62\u5f0f\u4e0e\u53ef\u89c2\u5bdf\u8868\u73b0"),
    ("not_provable", "D5 \u6392\u9664\u5408\u7406\u4e89\u8fa9", "\u5df2\u6392\u9664\u5355\u6b21\u4e89\u6267\u3001\u6253\u95f9\u8bef\u4f1a\u7b49\u60c5\u5f62", "\u5199\u6e05\u6392\u9664\u8fc7\u7a0b\u4e0e\u4ecd\u5b58\u7591\u70b9"),
]

KEY_DIMENSIONS = ("repeated", "intentional", "harm")

RED_FLAGS = [
    "physical_attack",
    "sexual_harm",
    "extortion",
    "nude_photo",
    "threat_no_tell",
    "head_injury",
    "self_harm_idea",
    "group_beat",
    "spread_with_coercion",
]

RED_FLAG_TEXT = {
    "physical_attack": "\u5df2\u53d1\u751f\u6216\u5373\u5c06\u53d1\u751f\u7684\u4eba\u8eab\u4f24\u5bb3",
    "sexual_harm": "\u6d89\u53ca\u6027\u76f8\u5173\u7684\u8a00\u8bed\u3001\u5f71\u50cf\u3001\u80c1\u8feb\u6216\u63a5\u89e6",
    "extortion": "\u88ab\u7d22\u8981\u8d22\u7269\u6216\u8d22\u7269\u88ab\u62a2",
    "nude_photo": "\u88ab\u62cd\u88f8\u7167\u6216\u9690\u79c1\u90e8\u4f4d\u7167\u7247\u5e76\u88ab\u8981\u631f",
    "threat_no_tell": "\u6536\u5230\u4e0d\u51c6\u544a\u8bc9\u5bb6\u957f\u7c7b\u5a01\u80c1",
    "head_injury": "\u5934\u90e8\u649e\u51fb\u540e\u5455\u5410\u3001\u610f\u8bc6\u6a21\u7cca\u3001\u5267\u70c8\u5934\u75db\u6216\u62bd\u6410",
    "self_harm_idea": "\u51fa\u73b0\u81ea\u4f24\u884c\u4e3a\u6216\u660e\u786e\u7684\u81ea\u6740\u5ff5\u5934",
    "group_beat": "\u51fa\u73b0\u7fa4\u4f53\u6027\u56f4\u6bb4\u6216\u7ec4\u7ec7\u6027\u6392\u6324\u5a01\u80c1",
    "spread_with_coercion": "\u4f20\u64ad\u9690\u79c1\u7167\u7247\u89c6\u9891\u5e76\u4f34\u968f\u8981\u631f",
}

RED_FLAG_ACTION = {
    "physical_attack": "\u7acb\u5373\u62a5\u8b66\uff1b\u5df2\u6709\u4f24\u60c5\u7684\u7acb\u5373\u5c31\u533b",
    "sexual_harm": "\u7acb\u5373\u62a5\u8b66\uff0c\u4fdd\u7559\u539f\u59cb\u8bc1\u636e\uff0c\u4e0d\u4e0e\u5bf9\u65b9\u79c1\u4e0b\u534f\u5546",
    "extortion": "\u7acb\u5373\u62a5\u8b66",
    "nude_photo": "\u7acb\u5373\u62a5\u8b66\uff0c\u4fdd\u7559\u539f\u59cb\u8bbe\u5907\u4e0e\u4fe1\u606f",
    "threat_no_tell": "\u7acb\u5373\u62a5\u8b66",
    "head_injury": "\u7acb\u5373\u5c31\u533b\uff0c\u5fc5\u8981\u65f6\u62a5\u8b66",
    "self_harm_idea": "\u7acb\u5373\u62a5\u8b66\u5e76\u540c\u6b65\u5fc3\u7406\u5371\u673a\u5e72\u9884",
    "group_beat": "\u7acb\u5373\u62a5\u8b66",
    "spread_with_coercion": "\u7acb\u5373\u62a5\u8b66",
}

EVIDENCE_TYPES = [
    "timeline", "chat_record", "injury_record", "school_record", "witness", "behavior_change",
]

EVIDENCE_TEXT = {
    "timeline": "\u4e8b\u4ef6\u65f6\u95f4\u7ebf",
    "chat_record": "\u804a\u5929\u4e0e\u4fe1\u606f\u8bb0\u5f55",
    "injury_record": "\u4f24\u60c5\u8bb0\u5f55\u4e0e\u7167\u7247",
    "school_record": "\u6821\u5185\u5728\u573a\u8bc1\u636e",
    "witness": "\u7b2c\u4e09\u65b9\u8bc1\u8a00",
    "behavior_change": "\u884c\u4e3a\u53d8\u5316\u89c2\u5bdf",
}

LEVELS = [
    ("\u5b66\u751f", "\u7acb\u5373\uff0c\u5b89\u5168\u4f18\u5148",
     ["\u79bb\u5f00\u73b0\u573a\u5230\u53ef\u770b\u89c1\u6210\u4eba\u7684\u5730\u65b9", "\u544a\u77e5\u81f3\u5c11\u4e00\u4f4d\u53ef\u4fe1\u4efb\u7684\u6210\u5e74\u4eba",
      "\u4e0d\u72ec\u81ea\u5bf9\u5cd9\u3001\u4e0d\u8ffd\u8d76\u3001\u4e0d\u8fd8\u624b", "\u8bb0\u4f4f\u53ef\u8bb0\u5f55\u7684\u65f6\u95f4\u4e0e\u5728\u573a\u4eba\uff0c\u4e0d\u5f3a\u884c\u53d6\u8bc1"]),
    ("\u5bb6\u957f", "24-72 \u5c0f\u65f6\u5185\u542f\u52a8",
     ["\u7528\u4e00\u9875\u7eb8\u6574\u7406\u65f6\u95f4\u7ebf\u4e0e\u8bc9\u6c42", "\u5148\u4e0e\u5b69\u5b50\u5171\u540c\u786e\u8ba4\u4e8b\u5b9e\u4e0e\u8bc9\u6c42",
      "\u4e0e\u73ed\u4e3b\u4efb\u6216\u5e74\u7ea7\u6559\u5e08\u5355\u72ec\u6c9f\u901a", "\u4fdd\u7559\u6c9f\u901a\u8bb0\u5f55"]),
    ("\u5b66\u6821", "\u4e66\u9762\u63d0\u51fa\uff0c\u8ddf\u8e2a\u95ed\u73af",
     ["\u4e66\u9762\u63d0\u51fa\u56db\u9879\u8bc9\u6c42\uff1a\u67e5\u660e\u4e8b\u5b9e\u3001\u660e\u786e\u5904\u7406\u3001\u9632\u6b62\u590d\u53d1\u3001\u540e\u7eed\u8ddf\u8e2a",
      "\u63a5\u53d7\u5b66\u6821\u5185\u90e8\u7a0b\u5e8f\u65f6\u9650\u4e0d\u7531\u5bb6\u957f\u51b3\u5b9a", "\u5904\u7406\u540e 4 \u5468\u5185\u6bcf\u4e24\u5468\u786e\u8ba4\u662f\u5426\u590d\u53d1"]),
    ("\u5916\u90e8\u6e20\u9053", "\u89c6\u60c5\u5f62\u7acb\u5373\u4f7f\u7528",
     ["\u4eba\u8eab\u4f24\u5bb3\u3001\u6027\u76f8\u5173\u4f24\u5bb3\u3001\u7d22\u8981\u8d22\u7269\u3001\u5a01\u80c1\u6050\u5413\u3001\u62cd\u6444\u4f20\u64ad\u3001\u81ea\u4f24\u98ce\u9669\uff1a\u7acb\u5373\u62a5\u8b66",
      "\u672a\u6210\u5e74\u4eba\u4fdd\u62a4\u76f8\u5173\u6e20\u9053\uff08\u5987\u8054\u8bbe\u6709\u76f8\u5173\u804c\u80fd\u3001\u5404\u5730\u8bbe\u6709\u672a\u6210\u5e74\u4eba\u4fdd\u62a4\u70ed\u7ebf\uff09",
      "\u6559\u80b2\u884c\u653f\u90e8\u95e8\uff1a\u5b66\u6821\u957f\u671f\u4e0d\u5904\u7406\u53ef\u5411\u4e3b\u7ba1\u90e8\u95e8\u53cd\u6620",
      "\u9700\u8981\u65f6\u8054\u7cfb\u5b66\u6821\u5fc3\u7406\u8001\u5e08\u6216\u5fc3\u7406\u63f4\u52a9\u70ed\u7ebf"]),
]

PSY_SIGNALS = [
    "\u8fde\u7eed\u4e24\u5468\u4ee5\u4e0a\u7761\u7720\u969c\u788d\u3001\u5669\u68a6\u3001\u62d2\u7edd\u4e0a\u5b66",
    "\u660e\u663e\u98df\u6b32\u4e0b\u964d\u6216\u4f53\u91cd\u53d8\u5316",
    "\u53cd\u590d\u8179\u75db\u5934\u75db\u4f46\u67e5\u4e0d\u51fa\u539f\u56e0",
    "\u60c5\u7eea\u4f4e\u843d\u3001\u6613\u6012\u3001\u60c5\u7eea\u7206\u53d1\u589e\u591a",
    "\u81ea\u4f24\u884c\u4e3a\u6216\u8bf4\u51fa\u4e0d\u60f3\u6d3b\u4e86",
    "\u62d2\u5b66\u3001\u88c5\u75c5\u3001\u6210\u7ee9\u7a81\u7136\u5927\u5e45\u4e0b\u6ed1",
]

EVIDENCE_FORBIDDEN = [
    "\u5e26\u5b69\u5b50\u53bb\u65bd\u66b4\u8005\u5bb6\u6216\u6821\u5916\u573a\u6240",
    "\u7ec4\u7ec7\u5077\u62cd\u3001\u5f55\u97f3\u3001\u8bbe\u5957\u3001\u5f15\u8bf1",
    "\u79c1\u4e0b\u8c03\u53d6\u6216\u62f7\u8d1d\u5b66\u6821\u76d1\u63a7",
    "\u8ba9\u5b69\u5b50\u72ec\u81ea\u53bb\u627e\u65bd\u66b4\u8005\u8bf4\u6e05\u695a",
    "\u627e\u4eba\u8c08\u4e00\u8c08\u6216\u6446\u5e73",
    "\u5728\u793e\u4ea4\u5e73\u53f0\u66dd\u5149\u65bd\u66b4\u8005\u7167\u7247\u3001\u59d3\u540d\u6216\u4e2a\u4eba\u4fe1\u606f",
    "\u7ec4\u7ec7\u5b69\u5b50\u4e4b\u95f4\u548c\u89e3\u89c1\u9762\u4f5c\u4e3a\u53d6\u8bc1\u624b\u6bb5",
]

BEHAVIOR_FORBIDDEN = [
    "\u6559\u5506\u5b69\u5b50\u8fd8\u624b\u3001\u62a5\u590d\u3001\u56f4\u5835",
    "\u6559\u5506\u627e\u6821\u5916\u4eba\u5458\u89e3\u51b3",
    "\u6559\u5506\u5077\u62cd\u6216\u66dd\u5149\u65bd\u66b4\u8005\u9690\u79c1",
    "\u7ec4\u7ec7\u548c\u89e3\u89c1\u9762\u4f5c\u4e3a\u538b\u529b\u624b\u6bb5",
    "\u8ba9\u5b69\u5b50\u91cd\u590d\u8bb2\u8ff0\u88ab\u6b3a\u8d1f\u7ec6\u8282",
    "\u5728\u793e\u4ea4\u5e73\u53f0\u516c\u5f00\u4e8b\u4ef6\u5e76\u70b9\u540d\u5f53\u4e8b\u4eba",
    "\u628a\u8f6c\u5b66\u5f53\u4f5c\u7b2c\u4e00\u624b\u6bb5",
    "\u53cd\u590d\u8ffd\u95ee\u7ec6\u8282\u6216\u5f15\u5bfc\u6027\u63d0\u95ee",
]

TALK = {
    "\u5b69\u5b50": [
        "\u6211\u76f8\u4fe1\u4f60\uff0c\u8fd9\u4e0d\u662f\u4f60\u7684\u9519\u3002",
        "\u8c22\u8c22\u4f60\u544a\u8bc9\u6211\u3002\u4f60\u4e0d\u9700\u8981\u4e00\u4e2a\u4eba\u625b\u3002",
        "\u4f60\u60f3\u600e\u4e48\u5904\u7406\uff1f\u6211\u966a\u4f60\u4e00\u8d77\u60f3\u529e\u6cd5\u3002",
        "\u4e0d\u9700\u8981\u4f60\u73b0\u5728\u628a\u7ec6\u8282\u8bb2\u6e05\u695a\uff0c\u7b49\u4f60\u51c6\u5907\u597d\u4e86\u518d\u8bf4\u3002",
    ],
    "\u8001\u5e08": [
        "\u6211\u60f3\u5148\u8bf4\u660e\u4e8b\u5b9e\uff0c\u518d\u8c08\u600e\u4e48\u5904\u7406\uff0c\u65f6\u95f4\u7ebf\u6211\u6574\u7406\u4e86\u4e00\u9875\u7eb8\u3002",
        "\u8fd9\u4ef6\u4e8b\u5df2\u7ecf\u53d1\u751f\u8fc7\u51e0\u6b21\uff0c\u6211\u5e0c\u671b\u5b66\u6821\u80fd\u67e5\u660e\u5e76\u9632\u6b62\u590d\u53d1\u3002",
        "\u9664\u4e86\u5904\u7406\u8fd9\u6b21\uff0c\u6211\u5e0c\u671b\u6709\u540e\u7eed\u7684\u8ddf\u8e2a\u5b89\u6392\u3002",
        "\u6211\u4e0d\u9700\u8981\u627f\u8bfa\u5177\u4f53\u7ed3\u679c\uff0c\u4f46\u9700\u8981\u77e5\u9053\u5b66\u6821\u7684\u5904\u7406\u4f9d\u636e\u548c\u8ddf\u8fdb\u65b9\u5f0f\u3002",
    ],
    "\u65bd\u66b4\u65b9\u5bb6\u957f": [
        "\u6211\u4eca\u5929\u8054\u7cfb\u4f60\u4e0d\u662f\u6765\u5435\u67b6\u7684\uff0c\u5b69\u5b50\u7684\u4e8b\u9700\u8981\u4e00\u4e2a\u5904\u7406\u65b9\u5f0f\u3002",
        "\u6211\u4eec\u5e0c\u671b\u53cc\u65b9\u5b69\u5b50\u90fd\u80fd\u5b89\u5168\u4e0a\u5b66\u3002",
        "\u5177\u4f53\u8bf7\u901a\u8fc7\u5b66\u6821\u6216\u76f8\u5173\u90e8\u95e8\u6c9f\u901a\uff0c\u6211\u4e0d\u5728\u73b0\u573a\u51b2\u7a81\u3002",
    ],
    "\u56f4\u89c2\u540c\u5b66": [
        "\u770b\u5230\u6709\u4eba\u5728\u88ab\u6b3a\u8d1f\uff0c\u53ef\u4ee5\u5927\u58f0\u8bf4\u4f4f\u624b\u3001\u966a\u88ab\u6b3a\u8d1f\u7684\u540c\u5b66\u4e00\u8d77\u79bb\u5f00\u3001\u544a\u8bc9\u8001\u5e08\u3001\u8bb0\u4e0b\u65f6\u95f4\u5730\u70b9\u5728\u573a\u4eba\u3002",
        "\u4e0d\u8981\u8d77\u54c4\u3001\u4e0d\u8981\u62cd\u6444\u4f20\u64ad\u3001\u4e0d\u8981\u8ddf\u7740\u4e00\u8d77\u7b11\u3002",
        "\u4f60\u4e0d\u9700\u8981\u4e00\u4e2a\u4eba\u53bb\u5bf9\u6297\uff0c\u53ea\u8981\u505a\u5230\u5176\u4e2d\u4e00\u4ef6\u4e8b\u5c31\u6709\u6548\u3002",
    ],
}

MYTHS = [
    "\u628a\u6240\u6709\u51b2\u7a81\u90fd\u5f53\u9738\u51cc\uff1a\u4e00\u6b21\u4e89\u6267\u3001\u4e00\u6b21\u62a2\u4e1c\u897f\u90fd\u4e0d\u662f\uff0c\u4f1a\u8ba9\u5bb6\u957f\u88ab\u8ba4\u4e3a\u4e0d\u5ba2\u89c2\u3002",
    "\u628a\u6240\u6709\u9738\u51cc\u90fd\u5f53\u5c0f\u5b69\u4e4b\u95f4\u7684\u4e8b\uff1a\u6709\u4f24\u5bb3\u3001\u6709\u4f20\u64ad\u3001\u6709\u8981\u631f\u5df2\u7ecf\u4e0d\u662f\u5c0f\u4e8b\u3002",
    "\u53ea\u8ba9\u5b69\u5b50\u522b\u7406\u4ed6\u6216\u5f3a\u5927\u4e00\u70b9\uff1a\u65e0\u6548\u4e14\u53ef\u80fd\u8ba9\u5b69\u5b50\u89c9\u5f97\u662f\u81ea\u5df1\u7684\u9519\u3002",
    "\u4ee5\u66b4\u5236\u66b4\uff1a\u77ed\u671f\u89e3\u6c14\uff0c\u5b9e\u9645\u628a\u5b69\u5b50\u63a8\u5411\u98ce\u9669\u66f4\u9ad8\u4f4d\u7f6e\u3002",
    "\u79c1\u81ea\u53d6\u8bc1\uff1a\u628a\u5b89\u5168\u98ce\u9669\u5168\u90e8\u8f6c\u7ed9\u5b69\u5b50\u3002",
    "\u6269\u6563\u65bd\u66b4\u8005\u7167\u7247\u66dd\u5149\uff1a\u53ef\u80fd\u6784\u6210\u4fb5\u6743\u4e0e\u4e8c\u6b21\u4f24\u5bb3\uff0c\u5e76\u5f15\u53d1\u62a5\u590d\u5faa\u73af\u3002",
    "\u4e00\u6b21\u8c08\u8bdd\u5c31\u7ed3\u6848\uff1a\u9738\u51cc\u5f80\u5f80\u91cd\u590d\u53d1\u751f\uff0c\u53ea\u5904\u7406\u5355\u6b21\u7b49\u4e8e\u6ca1\u5904\u7406\u3002",
    "\u8ba9\u5b69\u5b50\u5f53\u5c0f\u4fa6\u63a2\uff1a\u53cd\u590d\u8ffd\u95ee\u7ec6\u8282\u4f1a\u9020\u6210\u4e8c\u6b21\u521b\u4f24\uff0c\u62d2\u7edd\u8bf4\u4e0d\u7b49\u4e8e\u6ca1\u53d1\u751f\u3002",
    "\u5148\u8f6c\u5b66\u540e\u5904\u7406\uff1a\u98ce\u9669\u5e26\u7ed9\u5b69\u5b50\uff0c\u5b66\u6821\u95ee\u9898\u672a\u6574\u6539\u3002",
    "\u5ffd\u7565\u56f4\u89c2\u8005\uff1a\u56f4\u89c2\u8005\u4e0d\u4f5c\u4e3a\u4f1a\u5f3a\u5316\u65bd\u66b4\u884c\u4e3a\u3002",
]


def dim_meta(key):
    for k, label, crit, note in DIMENSIONS:
        if k == key:
            return label, crit, note
    return key, "", ""


def validate(raw):
    valid = dict((k, v) for k, v, _c, _n in DIMENSIONS)
    good, bad = [], []
    for k in list(raw or []):
        if k in valid:
            good.append(k)
        else:
            bad.append(k)
    return good, bad


def judge(hit):
    n_key = len([k for k in KEY_DIMENSIONS if k in hit])
    if n_key >= 2 and ("power_imbalance" in hit or "not_provable" in hit):
        return "\u503e\u5411\u9738\u51cc"
    if "repeated" not in hit:
        return "\u503e\u5411\u51b2\u7a81"
    return "\u4fe1\u606f\u4e0d\u8db3"


def evidence_gaps(have):
    valid = list(EVIDENCE_TYPES)
    got = [e for e in (have or []) if e in valid]
    return got, [e for e in valid if e not in got]


def build_plan(level, got, gaps):
    lines = []
    lines.append("\u5f53\u524d\u6863\u4f4d\uff1a" + level + "\uff08\u8fd9\u662f\u4e0b\u4e00\u6b65\u52a8\u4f5c\u7684\u4f9d\u636e\uff0c\u4e0d\u662f\u6027\u8d28\u8ba4\u5b9a\uff09")
    lines.append("")
    lines.append("\u56db\u7ea7\u5904\u7f6e\u987a\u5e8f\uff1a")
    for name, when, items in LEVELS:
        lines.append("  \u7b2c %s \u7ea7 %s\uff5c%s" % (name, when, name))
        lines.append("      \u65f6\u70b9\uff1a%s" % when)
        for it in items:
            lines.append("      + " + it)
    lines.append("")
    lines.append("\u5df2\u6709\u6750\u6599\uff1a")
    if got:
        for g in got:
            lines.append("  [\u6709] " + EVIDENCE_TEXT[g])
    else:
        lines.append("  [\u65e0] \u5c1a\u672a\u6574\u7406\u6750\u6599")
    lines.append("\u53d6\u8bc1\u7f3a\u53e3\uff08\u53ea\u8865\u5408\u6cd5\u53ef\u5f97\u7684\uff0c\u4e0d\u7ec4\u7ec7\u79c1\u81ea\u53d6\u8bc1\uff09\uff1a")
    if gaps:
        for g in gaps:
            lines.append("  - " + EVIDENCE_TEXT[g])
    else:
        lines.append("  - \u65e0\u7f3a\u53e3")
    lines.append("")
    lines.append("\u53d6\u8bc1\u7edd\u5bf9\u8fb9\u754c\uff1a")
    for f in EVIDENCE_FORBIDDEN:
        lines.append("  - \u7981\u6b62\uff1a" + f)
    lines.append("")
    lines.append("\u884c\u4e3a\u7edd\u5bf9\u7981\u6b62\uff1a")
    for f in BEHAVIOR_FORBIDDEN:
        lines.append("  - \u7981\u6b62\uff1a" + f)
    lines.append("")
    lines.append("\u56db\u65b9\u8bdd\u672f\uff1a")
    for who in ("\u5b69\u5b50", "\u8001\u5e08", "\u65bd\u66b4\u65b9\u5bb6\u957f", "\u56f4\u89c2\u540c\u5b66"):
        lines.append("  \u5bf9%s\uff1a" % who)
        for t in TALK[who]:
            lines.append("    + " + t)
    lines.append("")
    lines.append("\u9700\u4e13\u4e1a\u5fc3\u7406\u652f\u6301\u7684\u4fe1\u53f7\uff084 \u5468\u5185\u6bcf\u5468\u89c2\u5bdf\u4e00\u6b21\uff09\uff1a")
    for s in PSY_SIGNALS:
        lines.append("  - " + s)
    lines.append("")
    lines.append("\u5e38\u89c1\u8bef\u533a\uff1a")
    for m in MYTHS:
        lines.append("  - \u8bef\u533a\uff1a" + m)
    lines.append("")
    lines.append("\u6027\u8d28\u8ba4\u5b9a\u8fb9\u754c\uff1a\u4e8b\u4ef6\u6027\u8d28\u7531\u5b66\u6821\u53ca\u6559\u80b2\u3001\u516c\u5b89\u7b49\u4e3b\u7ba1\u90e8\u95e8\u4f9d\u804c\u6743\u8ba4\u5b9a\uff0c")
    lines.append("\u4ee5\u5b66\u6821\u6b63\u5f0f\u5904\u7406\u7ed3\u679c\u548c\u5f53\u5730\u4e3b\u7ba1\u90e8\u95e8\u8981\u6c42\u4e3a\u51c6\u3002\u672c\u5de5\u5177\u4e0d\u4f5c\u5b9a\u6027\u7ed3\u8bba\u3002")
    return lines


def build_report(data):
    raw = list(data.get("dimensions", []))
    flags = list(data.get("red_flags", []))
    have = list(data.get("evidence", []))
    weeks = data.get("weeks", 0)

    lines = []
    lines.append("=" * 66)
    lines.append("\u6821\u56ed\u9738\u51cc\u4e94\u7ef4\u5224\u5b9a\u4e0e\u5904\u7f6e\u987a\u5e8f")
    lines.append("=" * 66)
    lines.append("\u5df2\u6301\u7eed\u5468\u6570\uff1a%g" % float(weeks or 0))
    lines.append("")

    hit = [f for f in flags if f in RED_FLAGS]
    hit_unknown = [f for f in flags if f not in RED_FLAGS]
    if hit:
        lines.append("[\u7ea2\u7ebf] \u5fc5\u987b\u5148\u4fdd\u8bc1\u5b89\u5168\uff0c\u6682\u4e0d\u8d70\u5b66\u6821\u6d41\u7a0b\uff1a")
        for f in hit:
            lines.append("  ! %s" % RED_FLAG_TEXT[f])
            lines.append("    \u52a8\u4f5c\uff1a%s" % RED_FLAG_ACTION[f])
        lines.append("")
        lines.append("  \u5904\u7406\u987a\u5e8f\uff1a\u5148\u62a5\u8b66\u4e0e\u5c31\u533b\uff0c\u5b89\u5168\u4f18\u5148\uff1b\u6750\u6599\u53ea\u6574\u7406\u5408\u6cd5\u53ef\u5f97\u7684\u539f\u6709\u8bb0\u5f55\u3002")
        lines.append("=" * 66)
        return "\n".join(lines), {
            "blocked": True, "red_flags": hit, "level": "\u7ea2\u7ebf\u4f18\u5148",
            "next_level": "\u7acb\u5373\u62a5\u8b66\u4e0e\u5c31\u533b", "verdict_provided": False,
            "medication_provided": False,
        }

    good, unknown = validate(raw)
    if unknown:
        lines.append("[\u63d0\u793a] \u672a\u8bc6\u522b\u7684\u7ef4\u5ea6\u6807\u8bb0\u5df2\u5ffd\u7565\uff1a" + "\u3001".join(unknown))
        lines.append("")

    level = judge(good)
    lines.append("[\u4e00] \u4e94\u7ef4\u6838\u67e5")
    for k, label, crit, note in DIMENSIONS:
        mark = "[\u662f]" if k in good else "[\u5426/\u4e0d\u786e\u5b9a]"
        lines.append("  %s %s\uff5c\u5224\u5b9a\u53e3\u5f84\uff1a%s\uff5c\u8bb0\u5f55\uff1a%s" % (mark, label, crit, note))
    lines.append("")
    if float(weeks or 0) >= 2 and "repeated" not in good:
        lines.append("[\u63d0\u9192] \u5df2\u6301\u7eed %g \u5468\u4f46\u91cd\u590d\u53d1\u751f\u7ef4\u5ea6\u672a\u6807\u8bb0\u4e3a\u662f\uff0c\u8bf7\u786e\u8ba4\u8fd9\u4e00\u7ef4\u662f\u5426\u6f0f\u8bb0" % float(weeks or 0))
        lines.append("")
    lines.append("[\u4e8c] \u6863\u4f4d\u4e0e\u5904\u7f6e")
    got, gaps = evidence_gaps(have)
    for line in build_plan(level, got, gaps):
        lines.append("  " + line if line else "")

    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u5224\u5b9a\u7ef4\u5ea6\u4e0e\u5904\u7f6e\u987a\u5e8f\u53c2\u8003\uff0c\u4e0d\u4f5c\u6027\u8d28\u8ba4\u5b9a\u7ed3\u8bba\uff0c\u4e0d\u542b\u5fc3\u7406\u8bca\u65ad\u4e0e\u836f\u7269\u5efa\u8bae\u3002")
    lines.append("=" * 66)
    summary = {
        "blocked": False,
        "red_flags": hit_unknown,
        "level": level,
        "key_dimension_hits": len([k for k in KEY_DIMENSIONS if k in good]),
        "evidence_present": got,
        "evidence_gaps": gaps,
        "verdict_provided": False,
        "medication_provided": False,
        "therapy_provided": False,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("\u4e94\u7ef4\u5df2\u5b9a\u4e49", len(DIMENSIONS) == 5))
    r.append(("\u5173\u952e\u7ef4\u5ea6\u4e3a 3 \u9879", len(KEY_DIMENSIONS) == 3))
    r.append(("\u5904\u7f6e\u56db\u7ea7\u5df2\u5b9a\u4e49", len(LEVELS) == 4))
    r.append(("\u7ea2\u7ebf\u81f3\u5c11 9 \u6761", len(RED_FLAGS) >= 9))
    r.append(("\u53d6\u8bc1\u7981\u6b62\u9879\u81f3\u5c11 7 \u6761", len(EVIDENCE_FORBIDDEN) >= 7))
    r.append(("\u884c\u4e3a\u7981\u6b62\u9879\u81f3\u5c11 8 \u6761", len(BEHAVIOR_FORBIDDEN) >= 8))
    r.append(("\u8bef\u533a\u81f3\u5c11 10 \u6761", len(MYTHS) >= 10))

    good, bad = validate(["repeated", "xxx"])
    r.append(("\u5df2\u8bc6\u522b\u7ef4\u5ea6\u8ba1\u6570\u6b63\u786e", good == ["repeated"]))
    r.append(("\u672a\u8bc6\u522b\u7ef4\u5ea6\u88ab\u8fc7\u6ee4", bad == ["xxx"]))

    all_keys = [k for k, _l, _c, _n in DIMENSIONS]
    r.append(("\u5168\u7ef4\u547d\u4e2d\u4e14\u6709\u4e0d\u5bf9\u7b49\u5224\u4e3a\u503e\u5411\u9738\u51cc", judge(all_keys) == "\u503e\u5411\u9738\u51cc"))
    r.append(("\u4ec5\u91cd\u590d\u4e0e\u4e0d\u5bf9\u7b49\u4e0d\u8db3\u4ee5\u5224\u4e3a\u4fe1\u606f\u4e0d\u8db3",
              judge(["repeated", "power_imbalance"]) == "\u4fe1\u606f\u4e0d\u8db3"))
    r.append(("\u91cd\u590d\u4e0e\u4f24\u5bb3\u540c\u73b0\u4e14\u6709\u4e0d\u5bf9\u7b49\u5224\u4e3a\u503e\u5411\u9738\u51cc",
              judge(["repeated", "harm", "power_imbalance"]) == "\u503e\u5411\u9738\u51cc"))
    r.append(("\u65e0\u91cd\u590d\u5224\u4e3a\u503e\u5411\u51b2\u7a81", judge(["intentional", "harm"]) == "\u503e\u5411\u51b2\u7a81"))
    r.append(("\u4ec5\u6709\u91cd\u590d\u5224\u4e3a\u4fe1\u606f\u4e0d\u8db3", judge(["repeated"]) == "\u4fe1\u606f\u4e0d\u8db3"))
    r.append(("\u7a7a\u8f93\u5165\u5224\u4e3a\u503e\u5411\u51b2\u7a81", judge([]) == "\u503e\u5411\u51b2\u7a81"))

    got, gaps = evidence_gaps(["timeline", "bad_type"])
    r.append(("\u5df2\u6709\u6750\u6599\u8fc7\u6ee4\u975e\u6cd5\u9879", got == ["timeline"]))
    r.append(("\u7f3a\u53e3\u8ba1\u7b97\u6b63\u786e", len(gaps) == len(EVIDENCE_TYPES) - 1))
    r.append(("\u5168\u6750\u6599\u9f50\u5168\u65f6\u7f3a\u53e3\u4e3a\u7a7a", evidence_gaps(list(EVIDENCE_TYPES))[1] == []))
    r.append(("\u65e0\u6750\u6599\u65f6\u7f3a\u53e3\u4e3a\u5168\u90e8", len(evidence_gaps([])[1]) == len(EVIDENCE_TYPES)))

    _, s = build_report({"dimensions": all_keys, "evidence": list(EVIDENCE_TYPES), "weeks": 6})
    r.append(("\u5b8c\u6574\u6837\u4f8b\u4e0d\u963b\u65ad", s["blocked"] is False))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u5224\u5b9a\u503e\u5411\u9738\u51cc", s["level"] == "\u503e\u5411\u9738\u51cc"))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u4e0d\u7ed9\u6027\u8d28\u8ba4\u5b9a", s["verdict_provided"] is False))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u65e0\u6750\u6599\u7f3a\u53e3", s["evidence_gaps"] == []))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u4e0d\u7ed9\u836f\u7269", s["medication_provided"] is False))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u4e0d\u7ed9\u6cbb\u7597\u65b9\u6848", s["therapy_provided"] is False))

    _, s2 = build_report({"dimensions": all_keys, "red_flags": ["sexual_harm"]})
    r.append(("\u6027\u76f8\u5173\u7ea2\u7ebf\u76f4\u63a5\u963b\u65ad", s2["blocked"] is True))
    r.append(("\u963b\u65ad\u65f6\u4e0b\u4e00\u6b65\u4e3a\u62a5\u8b66\u5c31\u533b", s2["next_level"] == "\u7acb\u5373\u62a5\u8b66\u4e0e\u5c31\u533b"))
    r.append(("\u963b\u65ad\u65f6\u5224\u5b9a\u4e3a\u7ea2\u7ebf\u4f18\u5148", s2["level"] == "\u7ea2\u7ebf\u4f18\u5148"))

    _, s3 = build_report({"dimensions": ["repeated"], "weeks": 4})
    r.append(("\u4fe1\u606f\u4e0d\u8db3\u6863\u4f4d\u4e0d\u5347\u7ea7\u4e3a\u9738\u51cc", s3["level"] == "\u4fe1\u606f\u4e0d\u8db3"))

    txt, _ = build_report({"dimensions": all_keys, "weeks": 6})
    r.append(("\u8f93\u51fa\u542b\u4ee5\u66b4\u5236\u66b4\u7981\u4ee4", "\u4ee5\u66b4\u5236\u66b4" in txt))
    r.append(("\u8f93\u51fa\u542b\u79c1\u81ea\u53d6\u8bc1\u7981\u4ee4", "\u7981\u6b62\u5077\u62cd" in txt or "\u7ec4\u7ec7\u5077\u62cd" in txt))
    r.append(("\u8f93\u51fa\u542b\u56f4\u89c2\u540c\u5b66\u6b63\u786e\u505a\u6cd5", "\u966a\u88ab\u6b3a\u8d1f\u7684\u540c\u5b66\u4e00\u8d77\u79bb\u5f00" in txt))
    r.append(("\u8f93\u51fa\u542b\u4f9d\u804c\u6743\u8ba4\u5b9a\u53e3\u5f84", "\u4f9d\u804c\u6743\u8ba4\u5b9a" in txt))
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
    parser = argparse.ArgumentParser(description="\u6821\u56ed\u9738\u51cc\u4e94\u7ef4\u5224\u5b9a\u4e0e\u5904\u7f6e\u987a\u5e8f\u751f\u6210\u5de5\u5177")
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
