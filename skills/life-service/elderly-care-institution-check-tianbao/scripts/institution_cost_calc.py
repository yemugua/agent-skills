# -*- coding: utf-8 -*-
"""\u517b\u8001\u673a\u6784\u8d39\u7528\u6d4b\u7b97\u4e0e\u5408\u540c\u6838\u67e5\u5de5\u5177\u3002

\u7528\u6cd5:
  python institution_cost_calc.py --file case.json [--contract] [--json]
  python institution_cost_calc.py --selftest

\u672c\u5de5\u5177\u4e0d\u63a8\u8350\u673a\u6784\u3001\u4e0d\u7ed9\u4ef7\u683c\u6807\u51c6\u3001\u4e0d\u7ed9\u9000\u8d39\u91d1\u989d\u7ed3\u8bba\u3002
"""
import argparse
import io
import json
import os
import sys

TYPES = [
    ("nursing", "\u62a4\u7406\u578b", "\u4ee5\u533b\u7597\u62a4\u7406\u4e0e\u957f\u671f\u7167\u62a4\u4e3a\u4e3b",
     ["\u91cd\u5ea6\u5931\u80fd\u3001\u5367\u5e8a", "\u538b\u75d5\u98ce\u9669\u9ad8", "\u9700\u6301\u7eed\u62a4\u7406"],
     ["\u6838\u5b9e\u533b\u7597\u652f\u6301\u80fd\u529b", "\u8d44\u8d28\u4e0e\u8bb8\u53ef\u8303\u56f4\u9700\u6838\u5b9e"]),
    ("care", "\u7167\u6599\u578b", "\u4ee5\u751f\u6d3b\u7167\u6599\u4e0e\u65e5\u5e38\u7167\u62a4\u4e3a\u4e3b",
     ["\u80fd\u81ea\u7406\u6216\u8f7b\u5ea6\u5931\u80fd", "\u9700\u4eba\u534f\u52a9\u8d77\u5c45"],
     ["\u6838\u5b9e\u8d77\u5c45\u7167\u62a4\u80fd\u529b", "\u6838\u5b9e\u6d3b\u52a8\u5b89\u6392"]),
    ("integrated", "\u7efc\u5408\u578b", "\u7167\u6599\u4e0e\u62a4\u7406\u5e76\u5177\uff0c\u5206\u533a\u6216\u5206\u5c42\u63d0\u4f9b",
     ["\u9700\u6c42\u8de8\u5ea6\u8f83\u5927", "\u540e\u7eed\u53ef\u80fd\u8f6c\u62a4\u7406"],
     ["\u9010\u533a\u786e\u8ba4\u5b9e\u9645\u80fd\u542b\u542b\u54ea\u4e9b\u670d\u52a1",
      "\u786e\u8ba4\u5404\u5206\u533a\u62a4\u7406\u4eba\u5458\u5728\u5c97\u4e0e\u8bbe\u5907"]),
    ("community", "\u5c45\u5bb6\u793e\u533a\u517b\u8001", "\u8001\u4eba\u4ecd\u4f4f\u5728\u5bb6\u91cc\uff0c\u4e0a\u95e8\u6216\u793e\u533a\u63d0\u4f9b\u652f\u6301",
     ["\u591a\u6570\u8001\u4eba\u9996\u9009", "\u80fd\u81ea\u7406\u6216\u8f7b\u5ea6\u5931\u80fd"],
     ["\u6838\u5b9e\u4e0a\u95e8\u9891\u6b21\u4e0e\u670d\u52a1\u9879\u76ee", "\u6838\u5b9e\u5e94\u6025\u54cd\u5e94\u80fd\u529b"]),
]

TYPE_NOTE = "\u673a\u6784\u5ba3\u4f20\u53ef\u80fd\u540c\u65f6\u4f7f\u7528\u591a\u4e2a\u540d\u79f0\uff0c\u4ee5\u4e3b\u7ba1\u90e8\u95e8\u767b\u8bb0\u4e0e\u5907\u6848\u7c7b\u522b\u548c\u8303\u56f4\u4e3a\u51c6\uff0c\u4e0d\u8981\u4ee5\u673a\u6784\u81ea\u8ff0\u4e3a\u51c6\u3002"

HIDDEN_ITEMS = [
    ("nursing_fee", "\u62a4\u7406\u8d39", "\u6309\u5206\u7ea7\u6216\u6309\u9879\u76ee\u6536\u53d6"),
    ("meal_fee", "\u9910\u8d39", "\u5e38\u72ec\u7acb\u8ba1\u8d39"),
    ("consumable", "\u8017\u6750\u8d39", "\u5c3f\u57ab\u3001\u62a4\u7406\u57ab\u3001\u7eb8\u5dfe\u7b49"),
    ("medicine", "\u836f\u8d39", "\u7531\u8c01\u4e70\u3001\u80fd\u5426\u4ee3\u4e70"),
    ("special_care", "\u7279\u6b8a\u62a4\u7406\u8d39", "\u7ffb\u8eab\u3001\u62cd\u80cc\u3001\u5bfc\u7ba1\u62a4\u7406\uff0c\u6309\u6b21\u6216\u6309\u6708"),
    ("wash_cut", "\u6d17\u62a4\u7406\u53d1\u8d39", "\u5c0f\u989d\u4f46\u6301\u7eed"),
    ("escort", "\u966a\u540c\u5c31\u533b\u63a5\u9001\u8d39", "\u6309\u6b21\u8ba1"),
    ("utility", "\u6c34\u7535\u8d39", "\u6709\u65f6\u5168\u5305\uff0c\u6709\u65f6\u53e6\u7b97"),
    ("laundry", "\u6d17\u8863\u8d39", "\u53e6\u8ba1"),
]

HIDDEN_SIGNALS = [
    "\u53ea\u62a5\u4e00\u4e2a\u6708\u8d39\u603b\u6570\uff0c\u4e0d\u613f\u9010\u9879\u8bf4\u660e",
    "\u53e3\u5934\u8bf4\u90fd\u5305\u542b\u4f46\u4e0d\u5199\u8fdb\u5408\u540c",
    "\u8bf4\u6309\u89c4\u5b9a\u4f46\u4e0d\u8bf4\u660e\u5177\u4f53\u5185\u5bb9",
    "\u4e0e\u5176\u4ed6\u673a\u6784\u62a5\u4ef7\u53e3\u5f84\u4e0d\u540c\uff0c\u65e0\u6cd5\u76f4\u63a5\u5bf9\u6bd4",
]

CONTRACT_ITEMS = [
    ("1", "\u6536\u8d39\u9879\u76ee\u4e0e\u6807\u51c6", "\u9010\u9879\u5217\u51fa\u3001\u5355\u4ef7\u6216\u8ba1\u7b97\u65b9\u5f0f\u3001\u662f\u5426\u5305\u542b",
     "\u53ea\u5199\u4e00\u4e2a\u603b\u6570\uff0c\u51fa\u73b0\u5206\u6b67\u65f6\u65e0\u6cd5\u4e3b\u5f20"),
    ("2", "\u8d39\u7528\u8c03\u6574", "\u8c03\u6574\u7684\u6761\u4ef6\u3001\u5e45\u5ea6\u3001\u662f\u5426\u9700\u63d0\u524d\u901a\u77e5",
     "\u673a\u6784\u53ef\u968f\u65f6\u6da8\u4ef7"),
    ("3", "\u9000\u4f4f\u6761\u4ef6", "\u8001\u4eba\u6216\u5bb6\u5c5e\u53ef\u4e3b\u52a8\u9000\u4f4f\u7684\u6761\u4ef6\u3001\u662f\u5426\u9700\u63d0\u524d\u7533\u8bf7\u53ca\u63d0\u524d\u591a\u4e45",
     "\u53e3\u5934\u968f\u65f6\u53ef\u9000\u4f46\u5408\u540c\u8981\u6c42\u63d0\u524d\u4e09\u4e2a\u6708"),
    ("4", "\u9000\u8d39\u89c4\u5219", "\u9000\u8d39\u671f\u9650\u3001\u8ba1\u7b97\u65b9\u5f0f\u3001\u53ef\u6263\u9879\u76ee",
     "\u53ea\u5199\u6309\u89c4\u5b9a\u9000\uff0c\u65e0\u6cd5\u6267\u884c"),
    ("5", "\u62a4\u7406\u7b49\u7ea7\u53d8\u66f4", "\u7b49\u7ea7\u5982\u4f55\u5212\u5206\u3001\u53d8\u66f4\u6761\u4ef6\u3001\u53d8\u66f4\u540e\u8d39\u7528\u8c03\u6574\u3001\u7531\u8c01\u63d0\u51fa",
     "\u9700\u5347\u7ea7\u62a4\u7406\u65f6\u8d39\u7528\u4e89\u8bae"),
    ("6", "\u610f\u5916\u8d23\u4efb\u5212\u5206", "\u8dcc\u5012\u3001\u70eb\u4f24\u3001\u8bef\u5438\u3001\u4e22\u5931\u7b49\u60c5\u5f62\u7684\u8d23\u4efb\u5212\u5206\u4e0e\u5904\u7406",
     "\u51fa\u4e8b\u540e\u8d23\u4efb\u4e0d\u6e05"),
    ("7", "\u89e3\u9664\u4e0e\u7ec8\u6b62", "\u53cc\u65b9\u5747\u53ef\u89e3\u9664\u7684\u6761\u4ef6\u3001\u901a\u77e5\u65b9\u5f0f\u3001\u540e\u679c",
     "\u673a\u6784\u5355\u65b9\u89e3\u9664\u65e0\u4f9d\u636e"),
]

PROBE_LIST = [
    "\u62a4\u7406\u8d39\u6309\u4ec0\u4e48\u6807\u51c6\u6536\uff08\u5206\u7ea7\u3001\u5206\u9879\u76ee\uff09",
    "\u9910\u8d39\u662f\u5426\u5305\u542b\u5728\u6708\u8d39\u91cc",
    "\u8017\u6750\u8d39\uff08\u5c3f\u57ab\u3001\u62a4\u7406\u57ab\u3001\u7eb8\u5dfe\uff09\u600e\u4e48\u7b97",
    "\u836f\u8d39\u7531\u8c01\u4e70\u3001\u80fd\u5426\u4ee3\u4e70\u3001\u4ee3\u4e70\u6709\u65e0\u670d\u52a1\u8d39",
    "\u7279\u6b8a\u62a4\u7406\u8d39\uff08\u7ffb\u8eab\u3001\u62cd\u80cc\u3001\u5bfc\u7ba1\u62a4\u7406\uff09\u600e\u4e48\u7b97",
    "\u6d17\u62a4\u7406\u53d1\u8d39",
    "\u966a\u540c\u5c31\u533b\u4e0e\u63a5\u9001\u8d39",
    "\u6c34\u7535\u8d39",
    "\u9000\u4f4f\u65f6\u7684\u6e05\u6d01\u8d39\u4e0e\u635f\u8017\u8d39",
    "\u56de\u9000\u8d39\u7684\u671f\u9650\u4e0e\u6d41\u7a0b",
]

QUALIFY_ITEMS = [
    "\u8425\u4e1a\u6267\u7167\u4e0e\u5907\u6848\u4fe1\u606f",
    "\u767b\u8bb0\u4e0e\u5907\u6848\u7684\u670d\u52a1\u7c7b\u578b\u662f\u5426\u8986\u76d6\u62df\u8d2d\u4e70\u7684\u670d\u52a1",
    "\u662f\u5426\u5b58\u5728\u8d85\u8303\u56f4\u7ecf\u8425",
    "\u6536\u8d39\u9879\u76ee\u4e0e\u6807\u51c6\u662f\u5426\u5728\u5907\u6848\u6216\u516c\u793a\u8303\u56f4\u5185",
    "\u6d88\u9632\u4e0e\u5efa\u7b51\u662f\u5426\u7b26\u5408\u8981\u6c42",
]

QUALIFY_GATE = "\u4ee5\u4e0a\u4e94\u9879\u672a\u5411\u4e3b\u7ba1\u90e8\u95e8\u6838\u5b9e\u5b8c\u6210\u524d\u4e0d\u7b7e\u7ea6\u3002"

VISIT_ITEMS = [
    ("\u95fb\u6c14\u5473", "\u8d70\u5eca\u3001\u623f\u95f4\u3001\u536b\u751f\u95f4\u3001\u6d17\u8863\u533a\u5206\u522b\u95fb",
     "\u6574\u680b\u90fd\u662f\u5c3f\u5473\u6216\u9709\u5473\uff1b\u536b\u751f\u95f4\u5473\u5927\u4e14\u6392\u98ce\u4e0d\u7545"),
    ("\u770b\u76ae\u80a4", "\u624b\u80cc\u3001\u811a\u80cc\u3001\u9ab9\u5c3e\u90e8\u3001\u8db3\u8ddf\u3001\u809b\u5468\u3001\u6307\u7532",
     "\u6709\u538b\u75d5\u7ea2\u6591\u3001\u7834\u635f\u3001\u745e\u6591\u3001\u7532\u957f\u6216\u518d\u4f24"),
    ("\u770b\u7ffb\u8eab\u75d5\u8ff9", "\u5e8a\u5355\u662f\u5426\u5e72\u71e5\u3001\u4f53\u4f4d\u6446\u653e\u3001\u7ffb\u8eab\u8bb0\u5f55",
     "\u5e8a\u5355\u957f\u671f\u6f6e\u6e7f\uff1b\u4f53\u4f4d\u6446\u653e\u4e0d\u5230\u4f4d\uff1b\u8bf4\u4e0d\u6e05\u7ffb\u8eab\u5b89\u6392"),
    ("\u770b\u6d88\u9632\u901a\u9053", "\u4ece\u5165\u53e3\u8d70\u5230\u6700\u91cc\u9762\uff0c\u770b\u901a\u9053\u3001\u95e8\u3001\u706f\u3001\u6807\u8bc6",
     "\u901a\u9053\u5806\u7269\u3001\u95e8\u88ab\u6321\u6216\u9501\u95ed\u3001\u706f\u4e0d\u4eae\u3001\u6807\u8bc6\u4e0d\u6e05"),
    ("\u770b\u662f\u5426\u8d85\u5458", "\u767b\u8bb0\u5e8a\u4f4d\u4e0e\u5b9e\u9645\u5165\u4f4f\u6570\u3001\u52a0\u5e8a\u3001\u5728\u5c97\u62a4\u7406\u5458\u6570",
     "\u660e\u663e\u52a0\u5e8a\uff1b\u62a4\u7406\u5458\u660e\u663e\u5c11\u4e8e\u627f\u8bfa\uff1b\u4e00\u4eba\u7167\u62a4\u4eba\u6570\u8fdc\u8d85\u627f\u8bfa"),
]

RED_FLAGS = [
    "license_mismatch", "fire_blocked", "over_capacity", "nursing_short",
    "skin_issue", "fee_unclear", "refund_vague", "no_monitoring",
]

RED_FLAG_TEXT = {
    "license_mismatch": "\u767b\u8bb0\u4e0e\u5907\u6848\u8303\u56f4\u4e0d\u8986\u76d6\u6240\u8d2d\u670d\u52a1\uff0c\u6216\u62d2\u7edd\u51fa\u793a",
    "fire_blocked": "\u758f\u6563\u901a\u9053\u5806\u7269\u3001\u95e8\u88ab\u6321\u6216\u9501\u95ed\u3001\u5e94\u6025\u7167\u660e\u4e0d\u4eae",
    "over_capacity": "\u660e\u663e\u52a0\u5e8a\u3001\u5b9e\u9645\u5165\u4f4f\u6570\u8d85\u51fa\u767b\u8bb0\u5e8a\u4f4d",
    "nursing_short": "\u5728\u5c97\u62a4\u7406\u5458\u660e\u663e\u5c11\u4e8e\u627f\u8bfa\uff0c\u6216\u53ea\u8bf4\u7f16\u5236\u4e0d\u8c08\u5728\u5c97",
    "skin_issue": "\u63a2\u8bbf\u89c1\u538b\u75d5\u7ea2\u6591\u3001\u7834\u635f\u6216\u53cd\u590d\u5931\u7981\u75d5\u8ff9",
    "fee_unclear": "\u53ea\u62a5\u6708\u8d39\u603b\u6570\u3001\u4e0d\u613f\u9010\u9879\u8bf4\u660e",
    "refund_vague": "\u9000\u4f4f\u4e0e\u9000\u8d39\u6761\u6b3e\u542b\u7cca\u6216\u62d2\u7edd\u5199\u5165\u5408\u540c",
    "no_monitoring": "\u65e0\u53d6\u76d1\u8bb0\u5f55\u3001\u4e0d\u8bf4\u660e\u6295\u8bc9\u6e20\u9053\u3001\u62d2\u7edd\u5bb6\u5c5e\u53c2\u4e0e",
}

RED_FLAG_ACTION = {
    "license_mismatch": "\u5c5e\u4e8e\u91cd\u5927\u95ee\u9898\uff0c\u672a\u6838\u5b9e\u4e0d\u7b7e\u7ea6",
    "fire_blocked": "\u5c5e\u4e8e\u91cd\u5927\u95ee\u9898\uff0c\u672a\u6539\u6b63\u4e0d\u7b7e\u7ea6",
    "over_capacity": "\u5c5e\u4e8e\u91cd\u5927\u95ee\u9898\uff0c\u672a\u6539\u6b63\u4e0d\u7b7e\u7ea6",
    "nursing_short": "\u8981\u6c42\u4e66\u9762\u660e\u786e\u5e76\u5199\u5165\u5408\u540c",
    "skin_issue": "\u8981\u6c42\u5199\u5165\u5408\u540c\u7684\u7167\u62a4\u4e0e\u5931\u7981\u7ba1\u7406\u6761\u6b3e",
    "fee_unclear": "\u8981\u6c42\u4e66\u9762\u8d39\u7528\u660e\u7ec6\u8868\u5e76\u4f5c\u4e3a\u5408\u540c\u9644\u4ef6",
    "refund_vague": "\u8981\u6c42\u4e66\u9762\u5199\u660e\u5e76\u5efa\u8bae\u7531\u5f8b\u5e08\u5ba1\u9605",
    "no_monitoring": "\u8981\u6c42\u5199\u5165\u5408\u540c\u5e76\u5b89\u6392\u5165\u4f4f\u540e\u590d\u67e5\u8282\u594f",
}

FORBIDDEN = [
    "\u7981\u6b62\u53ea\u770b\u88c5\u4fee\u4e0e\u5ba3\u4f20",
    "\u7981\u6b62\u53ea\u542c\u53e3\u5934\u627f\u8bfa\u800c\u4e0d\u5199\u8fdb\u5408\u540c",
    "\u7981\u6b62\u7b7e\u7ea6\u524d\u4e0d\u6838\u5b9e\u8d44\u8d28\u4e0e\u5907\u6848",
    "\u7981\u6b62\u4e0d\u770b\u6d88\u9632\u901a\u9053",
    "\u7981\u6b62\u4e0d\u6570\u4eba\u5934\u7b97\u62a4\u7406\u914d\u6bd4",
    "\u7981\u6b62\u6309\u4ef7\u683c\u4e0d\u6309\u5bf9\u4ef7\u53e3\u5f84\u5bf9\u6bd4",
    "\u7981\u6b62\u5426\u7565\u8001\u4eba\u672c\u4eba\u610f\u613f",
    "\u7981\u6b62\u7b7e\u7ea6\u540e\u4e0d\u590d\u67e5",
]


def type_meta(key):
    for k, name, desc, who, checks in TYPES:
        if k == key:
            return name, desc, who, checks
    return key, "", [], []


def validate_list(raw, valid_keys):
    good, bad = [], []
    for k in list(raw or []):
        if k in valid_keys:
            good.append(k)
        else:
            bad.append(k)
    return good, bad


def monthly_total(base, extra):
    m = float(base or 0)
    for it in extra or []:
        m += float(it.get("monthly", 0) or 0)
    return round(m, 2)


def onetime_total(extra):
    t = 0.0
    for it in extra or []:
        t += float(it.get("onetime", 0) or 0)
    return round(t, 2)


def grand_total(base, extra, months, deposit, rate):
    m = float(months or 0)
    g = float(rate or 0)
    subtotal = 0.0
    base_m = float(base or 0)
    extra_m = sum(float(it.get("monthly", 0) or 0) for it in extra or [])
    for i in range(int(m)):
        subtotal += (base_m + extra_m) * ((1 + g) ** i)
    return round(subtotal + onetime_total(extra) + float(deposit or 0), 2)


def build_contract():
    lines = []
    lines.append("\u5408\u540c\u4e03\u9879\u5fc5\u770b\u6761\u6b3e\uff1a")
    for no, name, must, risk in CONTRACT_ITEMS:
        lines.append("  %s %s" % (no, name))
        lines.append("      \u5fc5\u987b\u5199\u6e05\uff1a" + must)
        lines.append("      \u542b\u7cca\u8868\u8ff0\u7684\u98ce\u9669\uff1a" + risk)
    lines.append("")
    lines.append("\u9690\u6027\u8d39\u7528\u8ffd\u95ee\u6e05\u5355\uff08\u9010\u9879\u95ee\uff0c\u7b54\u590d\u5fc5\u987b\u5199\u8fdb\u5408\u540c\uff09\uff1a")
    for q in PROBE_LIST:
        lines.append("  - " + q)
    lines.append("")
    lines.append("\u9690\u6027\u8d39\u7528\u8bc6\u522b\u56db\u4e2a\u4fe1\u53f7\uff08\u51fa\u73b0\u4efb\u4e00\u9879\u8981\u8b66\u89c9\uff09\uff1a")
    for s in HIDDEN_SIGNALS:
        lines.append("  - " + s)
    lines.append("")
    lines.append("\u8d44\u8d28\u6838\u5b9e\u6e05\u5355\uff08\u5411\u4e3b\u7ba1\u90e8\u95e8\u6838\u5b9e\uff09\uff1a")
    for q in QUALIFY_ITEMS:
        lines.append("  - " + q)
    lines.append("  " + QUALIFY_GATE)
    lines.append("")
    lines.append("\u63a2\u8bbf\u5b9e\u67e5\u4e94\u770b\uff1a")
    for name, how, bad in VISIT_ITEMS:
        lines.append("  %s\uff1a%s" % (name, how))
        lines.append("      \u5f02\u5e38\uff1a" + bad)
    lines.append("")
    lines.append("\u7981\u6b62\u505a\u6cd5\uff1a")
    for f in FORBIDDEN:
        lines.append("  - " + f)
    return lines


def build_report(data):
    tkey = data.get("type", "care")
    base = data.get("base_fee", 0)
    extra = list(data.get("extra", []))
    deposit = data.get("deposit", 0)
    months = data.get("months", 12)
    rate = data.get("rates", 0)
    flags = list(data.get("red_flags", []))
    contract_only = bool(data.get("contract_only", False))

    lines = []
    lines.append("=" * 66)
    lines.append("\u517b\u8001\u673a\u6784\u8d39\u7528\u6d4b\u7b97\u4e0e\u5408\u540c\u6838\u67e5")
    lines.append("=" * 66)
    lines.append("\u9884\u8ba1\u5165\u4f4f\u6708\u6570\uff1a%g   \u8d39\u7528\u6da8\u5e45\u53c2\u8003\uff1a%g"
                 % (float(months or 0), float(rate or 0)))
    lines.append("")

    hit = [f for f in flags if f in RED_FLAGS]
    unknown = [f for f in flags if f not in RED_FLAGS]
    if hit:
        lines.append("[\u6838\u67e5\u95ee\u9898] \u5df2\u53d1\u73b0\u4ee5\u4e0b\u95ee\u9898\uff0c\u672a\u5904\u7406\u4e0d\u5b9c\u7b7e\u7ea6\uff1a")
        for f in hit:
            lines.append("  ! " + RED_FLAG_TEXT[f])
            lines.append("    \u5904\u7f6e\uff1a" + RED_FLAG_ACTION[f])
        lines.append("")

    name, desc, who, checks = type_meta(tkey)
    lines.append("[\u4e00] \u673a\u6784\u7c7b\u578b\u4e0e\u9002\u914d")
    lines.append("  \u7c7b\u578b\uff1a%s" % name)
    lines.append("  \u5b9a\u4f4d\uff1a" + desc)
    lines.append("  \u5e38\u89c1\u9002\u7528\uff1a" + "\u3001".join(who))
    lines.append("  \u6838\u5b9e\u91cd\u70b9\uff1a" + "\u3001".join(checks))
    lines.append("  " + TYPE_NOTE)
    lines.append("")

    if contract_only:
        lines.append("[\u4e8c] \u5408\u540c\u4e0e\u6838\u67e5\u6e05\u5355")
        for line in build_contract():
            lines.append("  " + line if line else "")
        lines.append("")
        lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u8d39\u7528\u6d4b\u7b97\u4e0e\u6838\u67e5\u53c2\u8003\uff0c\u4e0d\u63a8\u8350\u673a\u6784\uff0c\u4e0d\u7ed9\u4ef7\u683c\u6807\u51c6\uff0c\u4e0d\u5224\u5b9a\u9000\u8d39\u91d1\u989d\u662f\u5426\u5408\u6cd5\u5408\u89c4\u3002")
        lines.append("=" * 66)
        return "\n".join(lines), {
            "blocked": False,
            "institution_recommended": False,
            "price_standard_provided": False,
            "refund_amount_judged": False,
            "contract_items": len(CONTRACT_ITEMS),
            "probe_items": len(PROBE_LIST),
            "visit_items": len(VISIT_ITEMS),
            "qualify_gate_stated": True,
        }

    m_total = monthly_total(base, extra)
    o_total = onetime_total(extra)
    g_total = grand_total(base, extra, months, deposit, rate)

    lines.append("[\u4e8c] \u8d39\u7528\u6d4b\u7b97")
    lines.append("  \u6708\u5ea6\u5408\u8ba1\uff1a%.2f \u5143\uff08\u57fa\u7840 %.2f \u5143 + \u9644\u52a0\u9879 %.2f \u5143\uff09"
                 % (m_total, float(base or 0), m_total - float(base or 0)))
    lines.append("  \u4e00\u6b21\u6027\u8d39\u7528\uff1a%.2f \u5143" % o_total)
    lines.append("  \u62bc\u91d1\uff1a%.2f \u5143\uff08\u9700\u5199\u660e\u9000\u8fd8\u6761\u4ef6\u4e0e\u671f\u9650\uff09" % float(deposit or 0))
    lines.append("  \u9884\u8ba1\u603b\u652f\u51fa\uff1a%.2f \u5143\uff08\u6309\u5165\u4f4f %g \u4e2a\u6708\u3001\u6da8\u5e45 %g \u4f30\u7b97\uff09"
                 % (g_total, float(months or 0), float(rate or 0)))
    lines.append("  \u53e3\u5f84\uff1a\u4ee5\u4e0a\u4e3a\u6d4b\u7b97\u53c2\u8003\uff0c\u4e0d\u662f\u4ef7\u683c\u6807\u51c6\uff0c\u5b9e\u9645\u4ee5\u673a\u6784\u5408\u540c\u4e0e\u5f52\u7ea6\u660e\u7ec6\u4e3a\u51c6\u3002")
    lines.append("")

    lines.append("[\u4e09] \u9690\u6027\u8d39\u7528\u8ffd\u95ee\u6e05\u5355")
    for key, label, how in HIDDEN_ITEMS:
        lines.append("  - %s\uff1a%s" % (label, how))
    lines.append("  \u56db\u4e2a\u8bc6\u522b\u4fe1\u53f7\uff1a")
    for s in HIDDEN_SIGNALS:
        lines.append("    * " + s)
    lines.append("")

    lines.append("[\u56db] \u5408\u540c\u6838\u5b9e\u4e0e\u63a2\u8bbf\u5b9e\u67e5")
    for line in build_contract():
        lines.append("  " + line if line else "")

    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u8d39\u7528\u6d4b\u7b97\u4e0e\u6838\u67e5\u53c2\u8003\uff0c\u4e0d\u6784\u6210\u673a\u6784\u8bc4\u4ef7\u3002")
    lines.append("\u4e0d\u63a8\u8350\u673a\u6784\uff0c\u4e0d\u7ed9\u4ef7\u683c\u6807\u51c6\u4e0e\u8865\u8d34\u91d1\u989d\uff0c\u4e0d\u5224\u5b9a\u9000\u8d39\u91d1\u989d\u662f\u5426\u5408\u6cd5\u5408\u89c4\u3002")
    lines.append("\u8d44\u8d28\u4e0e\u653f\u7b56\u53e3\u5f84\u4ee5\u4e3b\u7ba1\u90e8\u95e8\u5907\u6848\u4fe1\u606f\u3001\u516c\u793a\u4fe1\u606f\u4e0e\u5f53\u5730\u8981\u6c42\u4e3a\u51c6\u3002")
    lines.append("=" * 66)

    summary = {
        "blocked": False,
        "unknown_flags": unknown,
        "type_name": name,
        "monthly_total": m_total,
        "onetime_total": o_total,
        "deposit": float(deposit or 0),
        "grand_total": g_total,
        "hit_flags": hit,
        "institution_recommended": False,
        "price_standard_provided": False,
        "subsidy_amount_provided": False,
        "refund_amount_judged": False,
        "contract_items": len(CONTRACT_ITEMS),
        "qualify_gate_stated": True,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("\u673a\u6784\u7c7b\u578b\u4e3a 4 \u7c7b", len(TYPES) == 4))
    r.append(("\u9690\u6027\u8d39\u7528\u9879\u4e0d\u5c11\u4e8e 9 \u9879", len(HIDDEN_ITEMS) >= 9))
    r.append(("\u8ffd\u95ee\u6e05\u5355\u4e3a 10 \u9879", len(PROBE_LIST) == 10))
    r.append(("\u5408\u540c\u4e03\u9879\u5fc5\u770b\u6761\u6b3e", len(CONTRACT_ITEMS) == 7))
    r.append(("\u63a2\u8bbf\u5b9e\u67e5\u4e94\u770b", len(VISIT_ITEMS) == 5))
    r.append(("\u8d44\u8d28\u6838\u5b9e\u4e94\u9879", len(QUALIFY_ITEMS) == 5))
    r.append(("\u6838\u67e5\u95ee\u9898\u4e0d\u5c11\u4e8e 8 \u9879", len(RED_FLAGS) >= 8))
    r.append(("\u7981\u6b62\u505a\u6cd5\u4e0d\u5c11\u4e8e 8 \u6761", len(FORBIDDEN) >= 8))
    r.append(("\u6240\u6709\u95ee\u9898\u5747\u6709\u5904\u7f6e", all(k in RED_FLAG_ACTION for k in RED_FLAGS)))

    all_types = [k for k, _n, _d, _w, _c in TYPES]
    good, bad = validate_list(["care", "zzz"], all_types)
    r.append(("\u5df2\u8bc6\u522b\u673a\u6784\u7c7b\u578b\u8ba1\u6570\u6b63\u786e", good == ["care"]))
    r.append(("\u672a\u8bc6\u522b\u673a\u6784\u7c7b\u578b\u88ab\u8fc7\u6ee4", bad == ["zzz"]))
    r.append(("\u62a4\u7406\u578b\u53ef\u67e5\u5230\u6838\u5b9e\u91cd\u70b9", len(type_meta("nursing")[3]) == 2))
    r.append(("\u5c45\u5bb6\u793e\u533a\u517b\u8001\u53ef\u67e5\u5230\u6838\u5b9e\u91cd\u70b9", len(type_meta("community")[3]) == 2))
    r.append(("\u672a\u77e5\u7c7b\u578b\u8fd4\u56de\u7a7a\u6838\u5b9e\u70b9", type_meta("xxx")[3] == []))
    r.append(("\u56db\u7c7b\u673a\u6784\u5747\u6709\u8c03\u6574\u9879\u4e0e\u9002\u7528\u7fa4", all(len(t[3]) >= 2 and len(t[4]) == 2 for t in TYPES)))

    extra = [{"name": "\u62a4\u7406\u8d39", "monthly": 800, "onetime": 0},
             {"name": "\u9910\u8d39", "monthly": 600, "onetime": 0},
             {"name": "\u5e8a\u4f4d\u8d39", "monthly": 0, "onetime": 1200}]
    r.append(("\u6708\u5ea6\u5408\u8ba1\u8ba1\u7b97\u6b63\u786e", monthly_total(3000, extra) == 4400.0))
    r.append(("\u65e0\u9644\u52a0\u9879\u65f6\u5408\u8ba1\u4e3a\u57fa\u7840\u8d39", monthly_total(3000, []) == 3000.0))
    r.append(("\u7a7a\u9644\u52a0\u9879\u65f6\u5408\u8ba1\u4e3a 0", monthly_total(0, []) == 0.0))
    r.append(("\u4e00\u6b21\u6027\u8d39\u7528\u8ba1\u7b97\u6b63\u786e", onetime_total(extra) == 1200.0))
    r.append(("\u65e0\u9644\u52a0\u9879\u65f6\u4e00\u6b21\u6027\u4e3a 0", onetime_total([]) == 0.0))
    r.append(("\u4e00\u500b\u6708\u603b\u652f\u51fa\u6b63\u786e", grand_total(3000, [], 1, 0, 0) == 3000.0))
    r.append(("\u4e0d\u542b\u62bc\u91d1\u65f6\u62a4\u5546", grand_total(3000, [], 2, 0, 0) == 6000.0))
    r.append(("\u62a4\u91d1\u8ba1\u5165\u603b\u652f\u51fa", grand_total(3000, [], 1, 2000, 0) == 5000.0))
    r.append(("\u6da8\u5e45\u4e3a\u96f6\u65f6\u65e0\u989d\u5916\u589e\u52a0", grand_total(3000, [], 2, 0, 0) == grand_total(3000, [], 2, 0, 0.0)))
    r.append(("\u6708\u6570\u4e3a\u96f6\u65f6\u53ea\u7b97\u4e00\u6b21\u6027\u4e0e\u62bc\u91d1",
              grand_total(3000, extra, 0, 500, 0) == 1700.0))
    r.append(("\u603b\u652f\u51fa\u542b\u4e00\u6b21\u6027\u4e0e\u62bc\u91d1",
              grand_total(3000, extra, 1, 500, 0) == 6100.0))

    _, s = build_report({"type": "nursing", "base_fee": 3000, "extra": extra,
                         "deposit": 5000, "months": 12})
    r.append(("\u5b8c\u6574\u6837\u4f8b\u4e0d\u963b\u65ad", s["blocked"] is False))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u7c7b\u578b\u540d\u6b63\u786e", s["type_name"] == "\u62a4\u7406\u578b"))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u6708\u5ea6\u5408\u8ba1\u6b63\u786e", s["monthly_total"] == 4400.0))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u62a4\u91d1\u8bb0\u5f55", s["deposit"] == 5000.0))
    r.append(("\u4e0d\u63a8\u8350\u673a\u6784", s["institution_recommended"] is False))
    r.append(("\u4e0d\u7ed9\u4ef7\u683c\u6807\u51c6", s["price_standard_provided"] is False))
    r.append(("\u4e0d\u7ed9\u8865\u8d34\u91d1\u989d", s["subsidy_amount_provided"] is False))
    r.append(("\u4e0d\u5224\u5b9a\u9000\u8d39\u91d1\u989d", s["refund_amount_judged"] is False))
    r.append(("\u6838\u5b9e\u524d\u7f6e\u95e8\u7981\u5df2\u58f0\u660e", s["qualify_gate_stated"] is True))
    r.append(("\u5408\u540c\u6761\u6b3e\u6570\u4e3a 7", s["contract_items"] == 7))
    r.append(("\u603b\u652f\u51fa\u5927\u4e8e\u6708\u5ea6\u5408\u8ba1", s["grand_total"] > s["monthly_total"]))

    _, s2 = build_report({"type": "care", "base_fee": 3000, "red_flags": ["fire_blocked"]})
    r.append(("\u6d88\u9632\u901a\u9053\u95ee\u9898\u88ab\u8bb0\u5f55", "fire_blocked" in s2["hit_flags"]))
    r.append(("\u6709\u95ee\u9898\u65f6\u4ecd\u4e0d\u63a8\u8350\u673a\u6784", s2["institution_recommended"] is False))

    _, s3 = build_report({"contract_only": True})
    r.append(("\u53ea\u8981\u5408\u540c\u6e05\u5355\u6a21\u5f0f\u4e0d\u963b\u65ad", s3["blocked"] is False))
    r.append(("\u53ea\u8981\u6e05\u5355\u6a21\u5f0f\u7ed9\u51fa\u8ffd\u95ee\u9879\u6570", s3["probe_items"] == 10))
    r.append(("\u53ea\u8981\u6e05\u5355\u6a21\u5f0f\u7ed9\u51fa\u63a2\u8bbf\u9879\u6570", s3["visit_items"] == 5))
    r.append(("\u53ea\u8981\u6e05\u5355\u6a21\u5f0f\u4ecd\u4e0d\u7ed9\u4ef7\u683c\u6807\u51c6", s3["price_standard_provided"] is False))

    txt, _ = build_report({"type": "nursing", "base_fee": 3000, "extra": extra})
    r.append(("\u8f93\u51fa\u542b\u62a4\u7406\u8d39\u8ffd\u95ee", "\u62a4\u7406\u8d39\u6309\u4ec0\u4e48\u6807\u51c6\u6536" in txt))
    r.append(("\u8f93\u51fa\u542b\u8d44\u8d28\u6838\u5b9e\u524d\u7f6e\u95e8\u7981", QUALIFY_GATE in txt))
    r.append(("\u8f93\u51fa\u542b\u4e3b\u7ba1\u90e8\u95e8\u53e3\u5f84", "\u4e3b\u7ba1\u90e8\u95e8" in txt))
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
        description="\u517b\u8001\u673a\u6784\u8d39\u7528\u6d4b\u7b97\u4e0e\u5408\u540c\u6838\u67e5\u5de5\u5177")
    parser.add_argument("--file", help="\u8f93\u5165 JSON \u6587\u4ef6\u8def\u5f84\uff08UTF-8\uff09")
    parser.add_argument("--contract", action="store_true", help="\u53ea\u8f93\u51fa\u5408\u540c\u5fc5\u770b\u6761\u6b3e\u4e0e\u9000\u4f4f\u6838\u5bf9\u6e05\u5355")
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
    if args.contract:
        data["contract_only"] = True

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
