# -*- coding: utf-8 -*-
"""\u9ec4\u74dc\u5ac1\u63a5\u6108\u5408\u671f\u4e0e\u6210\u6d3b\u7387\u6838\u7b97\u5de5\u5177\u3002

\u7528\u6cd5:
  python graft_check.py --file graft.json [--json]
  python graft_check.py --selftest

\u672c\u5de5\u5177\u4e0d\u63d0\u4f9b\u7827\u6728\u5546\u54c1\u540d, \u4e0d\u7ed9\u75c5\u5bb3\u6297\u6027\u7b49\u7ea7\u7ed3\u8bba, \u4e0d\u542b\u519c\u836f\u4e0e\u751f\u957f\u8c03\u8282\u5242\u3002
"""
import argparse
import io
import json
import os
import sys

# \u7827\u6728\u7c7b\u578b -> \u642d\u914d\u5efa\u8bae
ROOTSTOCK = {
    "black_seed_pumpkin": {
        "name": "\u9ed1\u7c7d\u5357\u74dc\u7c7b",
        "relation": "\u540c\u79d1\u8fdc\u7f18",
        "strength": "\u6297\u67af\u840e\u75c5\u80fd\u529b\u5f3a, \u4e3b\u6839\u53d1\u8fbe",
        "note": "\u4e0b\u80da\u8f74\u4f38\u957f\u5feb, \u6ce8\u610f\u82d7\u671f\u5f92\u957f",
        "affinity": "\u4e2d",
    },
    "chowua": {
        "name": "\u846b\u74dc\u7c7b",
        "relation": "\u540c\u79d1\u8fd1\u7f18",
        "strength": "\u6297\u9006\u6027\u597d, \u63a5\u53e3\u7c97\u58ee",
        "note": "\u90e8\u5206\u7ec4\u5408\u53ef\u80fd\u5f71\u54cd\u74dc\u5473, \u5148\u5c0f\u533a\u9a8c\u8bc1",
        "affinity": "\u4e2d\u9ad8",
    },
    "wild_cucumber": {
        "name": "\u91ce\u9ec4\u74dc\u7c7b",
        "relation": "\u540c\u5c5e\u8fd1\u7f18",
        "strength": "\u4eb2\u548c\u6027\u597d, \u751f\u957f\u52bf\u4e0d\u7a81\u53d8",
        "note": "\u6297\u67af\u840e\u75c5\u7b49\u7ea7\u4f4e\u4e8e\u5357\u74dc\u7c7b",
        "affinity": "\u9ad8",
    },
    "winter_squash": {
        "name": "\u7b0b\u74dc\u7c7b",
        "relation": "\u540c\u79d1\u8fdc\u7f18",
        "strength": "\u8010\u76d0\u78b1\u80fd\u529b\u8f83\u597d",
        "note": "\u4eb2\u548c\u6027\u9700\u5148\u505a\u5c0f\u533a\u8bd5\u9a8c",
        "affinity": "\u4e2d",
    },
    "long_gourd": {
        "name": "\u957f\u846b\u82a6\u7c7b",
        "relation": "\u540c\u79d1\u8fdc\u7f18",
        "strength": "\u8010\u4f4e\u6e29\u8f83\u597d",
        "note": "\u540c\u6837\u9700\u5148\u505a\u5c0f\u533a\u8bd5\u9a8c",
        "affinity": "\u4e2d",
    },
}

# \u6108\u5408\u671f\u4e03\u9636\u6bb5
STAGES = [
    (0, 1, "\u4e00", "\u7acb\u5373\u5165\u6108\u5408\u5ba4, \u5168\u906e\u5149\u6216\u5f31\u5149, \u6e7f\u5ea6 90% \u4ee5\u4e0a"),
    (1, 2, "\u4e8c", "\u6e29\u5ea6 25-28\u2103, \u6e7f\u5ea6 90% \u4ee5\u4e0a, \u63a5\u53e3\u4e0d\u6cbe\u6c34"),
    (2, 3, "\u4e09", "\u6563\u5c04\u5149\u6bcf\u6b21 10-20 \u5206\u949f, \u6bcf\u5929 2-3 \u6b21"),
    (3, 5, "\u56db", "\u9010\u6b65\u5ef6\u957f\u89c1\u5149\u65f6\u95f4, \u9632\u6b62\u5f92\u957f\u4e0e\u63a5\u53e3\u5931\u6c34"),
    (5, 7, "\u4e94", "\u5f00\u59cb\u5c0f\u53e3\u901a\u98ce, \u63a5\u53e3\u4e0d\u5f97\u7ed3\u9732"),
    (7, 10, "\u516d", "\u677e\u7ed1\u6216\u53bb\u9664\u624e\u5e26, \u6e7f\u5ea6\u964d\u5230 60-70%"),
    (10, 15, "\u4e03", "\u8fdb\u5165\u70bc\u82d7\u9636\u6bb5, \u63a5\u53e3\u6478\u4e4b\u6709\u786c\u611f"),
]

# \u63a5\u53e3\u5f81\u5146 -> (\u6700\u53ef\u80fd\u539f\u56e0, \u5904\u7f6e)
SIGNS = {
    "black_soft": ("\u63a5\u53e3\u6cbe\u6c34\u52a0\u9ad8\u6e7f\u4e0d\u901a\u98ce, \u7acb\u5373\u8150\u70c2",
                   "\u7acb\u5373\u505c\u6b62\u55b7\u96fe\u4e0e\u6d47\u6c34, \u5f00\u5c0f\u53e3\u901a\u98ce; \u5df2\u8150\u70c2\u6574\u682a\u79fb\u51fa\u9500\u6bc1"),
    "mold": ("\u82d7\u5e8a\u9ad8\u6e7f, \u6d88\u6bd2\u4e0d\u5f7b\u5e95, \u901a\u98ce\u4e0d\u8db3",
             "\u901a\u98ce\u964d\u6e7f, \u79fb\u51fa\u75c5\u682a, \u5200\u5177\u4e0e\u53f0\u9762\u91cd\u65b0\u6d88\u6bd2"),
    "dry_separate": ("\u6108\u5408\u671f\u6e7f\u5ea6\u4e0d\u8db3\u6216\u6210\u6d3b\u540e\u624d\u5931\u6c34",
                     "\u524d\u671f\u7ef4\u6301 90% \u4ee5\u4e0a\u6e7f\u5ea6, \u906e\u9634\u5230\u4f4d"),
    "scion_wilt": ("\u63a5\u7a57\u5931\u6c34\u8fc7\u5ea6, \u65e9\u671f\u672a\u53ca\u65f6\u5165\u9ad8\u6e7f\u5ba4",
                   "\u7acb\u5373\u8f6c\u5165\u9ad8\u6e7f\u73af\u5883\u8865\u5931\u6c34"),
    "rootstock_burst": ("\u7827\u6728\u82bd\u672a\u53ca\u65f6\u62b9\u9664",
                        "\u53ca\u65f6\u62b9\u82bd, \u63a5\u7a57\u6062\u590d\u751f\u957f\u540e\u53ef\u8ffd\u56de"),
    "uneven_graft": ("\u64ad\u671f\u672a\u63a7\u597d, \u7827\u7a57\u830e\u7c97\u4e0d\u5339\u914d",
                     "\u7827\u6728\u65e9\u64ad 5-10 \u5929, \u7c97\u7ec6\u5dee\u63a7\u5236\u5728 1-2 mm"),
    "constrict": ("\u7ed1\u624e\u8fc7\u7d27\u6216\u672a\u53ca\u65f6\u677e\u7ed1",
                  "\u6108\u5408\u540e 7-10 \u5929\u53ca\u65f6\u677e\u7ed1\u6216\u53bb\u9664"),
    "late_wilt": ("\u6839\u7cfb\u95ee\u9898\u6216\u7827\u7a57\u4e0d\u4eb2\u548c",
                  "\u62d4\u8d77\u67e5\u6839, \u6839\u7cfb\u8910\u53d8\u9700\u6392\u67e5\u82d7\u5e8a\u75c5\u5bb3"),
    "no_new_leaf": ("\u63a5\u7a57\u5df2\u6b7b, \u7827\u6728\u5355\u72ec\u751f\u957f",
                    "\u62d4\u9664, \u7528\u540c\u7ea7\u6210\u6d3b\u82d7\u8865\u4f4d"),
    "rot_after_plant": ("\u5b9a\u690d\u65f6\u5ac1\u63a5\u53e3\u88ab\u57cb\u5165\u571f\u4e2d",
                        "\u8c03\u6574\u5b9a\u690d\u6df1\u5ea6, \u4fdd\u6301\u63a5\u53e3\u5728\u571f\u9762\u4e4b\u4e0a"),
}

AFFINITY_ORDER = {"\u4f4e": 1, "\u4e2d": 2, "\u4e2d\u9ad8": 3, "\u9ad8": 4}

# \u82d7\u7ea7\u5224\u636e
GRADES = [
    ("\u4e00\u7ea7\u82d7", "\u63a5\u53e3\u6108\u5408\u5b8c\u6574, \u65b0\u53f6 2-3 \u7247, \u830e\u7c97\u58ee, \u65e0\u75c5\u6591", "\u4e3b\u7528\u82d7"),
    ("\u4e8c\u7ea7\u82d7", "\u63a5\u53e3\u6108\u5408, \u65b0\u53f6 1-2 \u7247, \u7565\u5c0f", "\u5907\u7528\u82d7\u4e0e\u8865\u82d7"),
    ("\u4e09\u7ea7\u82d7", "\u63a5\u53e3\u521a\u6108\u5408, \u82d7\u504f\u5c0f", "\u5355\u72ec\u7f13\u82d7, \u4e0d\u6025\u4e8e\u5b9a\u690d"),
    ("\u6dd8\u6c70\u82d7", "\u63a5\u53e3\u672a\u6108\u5408, \u65b0\u53f6\u4e0d\u5c55, \u830e\u57fa\u90e8\u6709\u75c5\u6591", "\u79fb\u51fa\u9500\u6bc1, \u4e0d\u8fdb\u5b9a\u690d\u68da"),
]


def stage_of(days):
    d = int(days or 0)
    for i, (lo, hi, name, advice) in enumerate(STAGES):
        if d < hi:
            return name, advice, (d < lo)
    return "\u5df2\u8fc7\u6108\u5408\u671f", "\u6309\u5b9a\u690d\u524d\u70bc\u82d7\u4e0e\u6210\u6d3b\u7387\u590d\u6838\u53e3\u5f84\u5904\u7406", True


def stage_index(days):
    d = int(days or 0)
    for i, (lo, hi, name, advice) in enumerate(STAGES):
        if d < hi:
            return i
    return len(STAGES)


def survival_rate(total, survived):
    t = float(total or 0)
    s = float(survived or 0)
    if t <= 0:
        return 0.0
    if s > t:
        s = t
    return round(s / t * 100.0, 1)


def rate_grade(rate):
    if rate >= 85:
        return "\u5408\u683c", "\u53ef\u8fdb\u5165\u5b9a\u690d, \u6309\u82d7\u7ea7\u6b63\u5e38\u4f7f\u7528"
    if rate >= 70:
        return "\u504f\u4f4e", "\u8865\u82d7\u5230\u4f4d\u540e\u518d\u5b9a\u690d, \u67e5\u660e\u5931\u8d25\u539f\u56e0"
    if rate >= 50:
        return "\u4e0d\u5408\u683c", "\u672c\u6279\u5168\u6570\u62a5\u5e9f, \u91cd\u65b0\u80b2\u82d7"
    return "\u4e25\u91cd\u4e0d\u5408\u683c", "\u7acb\u5373\u505c\u6b62\u4e0b\u4e00\u6279, \u5148\u67e5\u64cd\u4f5c\u4e0e\u73af\u5883\u518d\u80b2\u82d7"


def risk_level(total, survived):
    r = survival_rate(total, survived)
    if r >= 85:
        return 0
    if r >= 70:
        return 1
    if r >= 50:
        return 2
    return 3


RISK_NAMES = {0: "\u6b63\u5e38", 1: "\u9700\u8865\u82d7", 2: "\u672c\u6279\u62a5\u5e9f", 3: "\u7acb\u5373\u505c\u6b62\u80b2\u82d7"}

MATCH_ADVICE = {
    "\u9ed1\u7c7d\u5357\u74dc\u7c7b": "\u9732\u5730\u4e0e\u8fde\u4f5c\u91cd\u5730\u5757\u7684\u5e38\u7528\u9009\u62e9, \u6297\u67af\u840e\u75c5\u4f18\u5148\u8003\u8651",
    "\u846b\u74dc\u7c7b": "\u77ed\u5b63\u8282\u6216\u9700\u8981\u8f83\u5f3a\u4eb2\u548c\u6027\u7684\u573a\u666f, \u5148\u5c0f\u533a\u9a8c\u8bc1\u74dc\u5473",
    "\u91ce\u9ec4\u74dc\u7c7b": "\u4eb2\u548c\u6027\u6700\u597d\u4f46\u6297\u6027\u63d0\u5347\u6709\u9650, \u9002\u5408\u8fde\u4f5c\u538b\u529b\u5c0f\u7684\u5730\u5757",
    "\u7b0b\u74dc\u7c7b": "\u571f\u58e4\u504f\u76d0\u78b1\u7684\u5730\u5757\u53ef\u8003\u8651, \u4eb2\u548c\u6027\u987b\u5148\u9a8c\u8bc1",
    "\u957f\u846b\u82a6\u7c7b": "\u65e9\u6625\u4f4e\u6e29\u683d\u57f9\u53ef\u8003\u8651, \u540c\u6837\u5148\u505a\u5c0f\u533a\u8bd5\u9a8c",
}


def describe_rootstock(key):
    info = ROOTSTOCK.get(key)
    if not info:
        return None
    return dict(info)


def affinity_rank(name):
    for k, v in AFFINITY_ORDER.items():
        if name == k:
            return v
    return 0


def build_report(data):
    rootstock_key = data.get("rootstock", "")
    scion_state = data.get("scion_state", "")
    days = int(data.get("days_after_graft", 0) or 0)
    signs = data.get("stage_s_signs", []) or []
    total = data.get("seedling_count", 0) or 0
    survived = data.get("survived_count", 0) or 0

    lines = []
    summary = {
        "rootstock": rootstock_key,
        "rootstock_name": None,
        "stage": None,
        "risk": None,
        "risk_name": None,
        "survival_rate": None,
        "grade": None,
        "signs": [],
        "product_recommendation": False,
    }

    lines.append("=" * 68)
    lines.append("\u9ec4\u74dc\u5ac1\u63a5\u6108\u5408\u671f\u4e0e\u6210\u6d3b\u7387\u6838\u7b97")
    lines.append("=" * 68)

    info = describe_rootstock(rootstock_key)
    lines.append("[\u4e00] \u7827\u6728\u4e0e\u63a5\u7a57\u642d\u914d")
    lines.append("-" * 68)
    if info:
        summary["rootstock_name"] = info["name"]
        lines.append("  \u7827\u6728\u7c7b\u578b: %s" % info["name"])
        lines.append("    \u4e0e\u9ec4\u74dc\u4eb2\u7f18\u5173\u7cfb: %s" % info["relation"])
        lines.append("    \u4e3b\u8981\u4f5c\u7528: %s" % info["strength"])
        lines.append("    \u4f7f\u7528\u6ce8\u610f: %s" % info["note"])
        lines.append("    \u4eb2\u548c\u6027\u53c2\u8003: %s" % info["affinity"])
        lines.append("    \u642d\u914d\u5efa\u8bae: %s" % MATCH_ADVICE[info["name"]])
        lines.append("    \u64ad\u671f\u5dee: \u7827\u6728\u6bd4\u63a5\u7a57\u65e9\u64ad 5-10 \u5929, \u830e\u7c97\u5dee\u63a7\u5236\u5728 1-2 mm \u5185")
        lines.append("    \u63d0\u9192: \u6362\u65b0\u7ec4\u5408\u5148\u79cd 20-30 \u682a\u5c0f\u533a\u8bd5\u9a8c, \u4e0d\u8981\u7b2c\u4e00\u5e74\u5168\u68da\u6362")
    else:
        lines.append("  \u672a\u63d0\u4f9b\u5df2\u767b\u8bb0\u7684\u7827\u6728\u7c7b\u578b, \u901a\u7528\u539f\u5219:")
        lines.append("    \u4eb2\u7f18\u5173\u7cfb\u4e0d\u80fd\u592a\u8fdc\u4e5f\u4e0d\u80fd\u592a\u8fd1; \u770b\u7528\u9014\u9009\u62e9; \u5148\u505a\u5c0f\u533a\u8bd5\u9a8c")
        lines.append("    \u64ad\u671f\u5dee 5-10 \u5929; \u54c1\u79cd\u9009\u62e9\u4ee5\u4f9b\u79cd\u65b9\u8bf4\u660e\u548c\u5f53\u5730\u519c\u6280\u90e8\u95e8\u4e3a\u51c6")
    lines.append("")

    lines.append("[\u4e8c] \u63a5\u7a57\u82d7\u6001\u6838\u67e5")
    lines.append("-" * 68)
    ok_states = {"\u5408\u683c": "\u5b50\u53f6\u5c55\u5f00, \u771f\u53f6 2-3 \u7247, \u830e\u6bb5 4-5 cm \u5e26 2-3 \u7247\u53f6",
                 "\u504f\u5c0f": "\u5b50\u53f6\u5c55\u5f00\u4f46\u771f\u53f6\u4e0d\u8db3 2 \u7247, \u5ac1\u63a5\u540e\u53ef\u5206\u6279\u8fdb\u884c",
                 "\u5f92\u957f": "\u830e\u7ec6\u5f31\u8282\u95f4\u62c9\u957f, \u63a5\u53e3\u96be\u7ed1\u7262, \u4e0d\u5b9c\u5ac1\u63a5",
                 "\u5e26\u75c5": "\u830e\u57fa\u90e8\u6216\u53f6\u7247\u6709\u75c5\u6591, \u4e0d\u53ef\u5165\u6108\u5408\u5ba4"}
    for st in (scion_state or "").split(","):
        st = st.strip()
        if not st:
            continue
        lines.append("  %s -> %s" % (st, ok_states.get(st, "\u672a\u767b\u8bb0\u72b6\u6001, \u9700\u4eba\u5de5\u786e\u8ba4")))
    if not scion_state:
        lines.append("  \u672a\u63d0\u4f9b\u63a5\u7a57\u82d7\u6001, \u8bf7\u6309\u5408\u683c\u82d7\u6807\u51c6\u81ea\u67e5")
    lines.append("")

    lines.append("[\u4e09] \u6108\u5408\u671f\u9636\u6bb5\u5b9a\u4f4d (\u5ac1\u540e\u7b2c %d \u5929)" % days)
    lines.append("-" * 68)
    idx = stage_index(days)
    name, advice, passed = stage_of(days)
    summary["stage"] = name
    lines.append("  \u5f53\u524d\u9636\u6bb5: \u7b2c %s \u9636\u6bb5" % name)
    lines.append("    \u7ba1\u7406\u53e3\u5f84: %s" % advice)
    lines.append("    \u8fdb\u5ea6\u4f4d\u7f6e: \u7b2c %d / %d \u9636\u6bb5" % (idx + 1, len(STAGES)))
    if days <= 2:
        lines.append("    \u91cd\u70b9: \u6e7f\u5ea6\u7ef4\u6301 90% \u4ee5\u4e0a, \u63a5\u53e3\u4e0d\u6cbe\u6c34, \u7827\u6728\u4e0e\u63a5\u7a57\u4e0d\u9519\u4f4d")
    if 2 < days <= 7:
        lines.append("    \u91cd\u70b9: \u9010\u6b65\u89c1\u5149; \u7b2c 5 \u5929\u8d77\u5f00\u59cb\u5c0f\u53e3\u901a\u98ce, \u63a5\u53e3\u4e0d\u5f97\u7ed3\u9732")
    if 7 < days <= 10:
        lines.append("    \u91cd\u70b9: \u53ca\u65f6\u677e\u7ed1\u6216\u53bb\u9664\u624e\u5e26, \u6e7f\u5ea6\u964d\u5230 60-70%")
    if days > 10:
        lines.append("    \u91cd\u70b9: \u8fdb\u5165\u70bc\u82d7; \u5f00\u59cb\u6309\u63a5\u53e3\u6108\u5408\u52a0\u65b0\u53f6\u6b63\u5e38\u5c55\u5f00\u53cc\u6761\u4ef6\u590d\u6838")
    lines.append("")
    lines.append("  \u5168\u9636\u6bb5\u65f6\u95f4\u8f74:")
    for lo, hi, sname, sadvice in STAGES:
        mark = "<<" if sname == name else "  "
        lines.append("   %s \u7b2c%s\u9636\u6bb5 %2d-%2d \u5929: %s" % (
            mark, sname, lo, hi, sadvice))
    lines.append("")

    lines.append("[\u56db] \u63a5\u53e3\u5f81\u5146\u5224\u522b")
    lines.append("-" * 68)
    if not signs:
        lines.append("  \u672a\u62a5\u544a\u63a5\u53e3\u5f02\u5e38\u5f81\u5146")
        lines.append("  \u4e09\u6761\u94c1\u5f8b: \u7b2c5\u5929\u8d77\u901a\u98ce\u4e14\u63a5\u53e3\u4e0d\u7ed3\u9732; \u7827\u6728\u82bd 1-2 mm \u5373\u62b9; \u6e29\u5ea6\u4e0d\u9aa4\u53d8\u5927\u843d")
    for s in signs:
        s = s.strip()
        if not s:
            continue
        if s in SIGNS:
            cause, action = SIGNS[s]
            lines.append("  [\u5f02\u5e38] %s" % s)
            lines.append("    \u6700\u53ef\u80fd\u539f\u56e0: %s" % cause)
            lines.append("    \u5904\u7f6e\u53e3\u5f84: %s" % action)
            summary["signs"].append(s)
        else:
            lines.append("  [\u672a\u767b\u8bb0] %s -> \u9700\u4eba\u5de5\u6bd4\u5bf9\u5f81\u5146\u5bf9\u7167\u8868" % s)
    lines.append("")

    lines.append("[\u4e94] \u6210\u6d3b\u7387\u590d\u6838\u4e0e\u82d7\u7ea7")
    lines.append("-" * 68)
    rate = survival_rate(total, survived)
    grade, gadvice = rate_grade(rate)
    risk = risk_level(total, survived)
    summary["survival_rate"] = rate
    summary["grade"] = grade
    summary["risk"] = risk
    summary["risk_name"] = RISK_NAMES[risk]
    lines.append("  \u5ac1\u63a5\u603b\u82d7\u6570: %g   \u6210\u6d3b\u82d7\u6570: %g" % (float(total or 0), float(survived or 0)))
    lines.append("  \u6210\u6d3b\u7387: %.1f%% -> %s" % (rate, grade))
    lines.append("  \u5904\u7f6e: %s" % gadvice)
    lines.append("")
    lines.append("  \u6210\u6d3b\u7387 = (\u63a5\u53e3\u6108\u5408\u4e14\u65b0\u53f6\u6b63\u5e38\u5c55\u5f00\u7684\u82d7\u6570) / (\u5ac1\u63a5\u603b\u82d7\u6570)")
    lines.append("  \u4e0d\u80fd\u53ea\u770b\u63a5\u53e3\u989c\u8272: \u6709\u7684\u82d7\u63a5\u53e3\u770b\u7740\u63a5\u4e0a\u4e86, \u63a5\u7a57\u65e9\u5df2\u6b7b\u4ea1, \u9760\u7827\u6728\u82bd\u5728\u6491")
    lines.append("")
    lines.append("  \u82d7\u7ea7\u5224\u636e:")
    for gname, crit, usage in GRADES:
        lines.append("    %s: %s -> %s" % (gname, crit, usage))
    lines.append("")

    lines.append("[\u516d] \u5b9a\u690d\u524d\u540e\u63d0\u9192")
    lines.append("-" * 68)
    lines.append("  \u5b9a\u690d\u6df1\u5ea6\u4e0e\u82d7\u5e8a\u76f8\u5e73, \u5ac1\u63a5\u53e3\u4e0d\u57cb\u8fdb\u571f\u91cc")
    lines.append("  \u5ac1\u63a5\u82d7\u9760\u7827\u6728\u5f3a\u6839\u7cfb\u4f9b\u6c34, \u7f13\u82d7\u671f\u4e0d\u8ffd\u5927\u6c34, \u4e0d\u6309\u81ea\u6839\u82d7\u7684\u813e\u6c14\u5927\u6c34\u5927\u80a5")
    lines.append("  \u79fb\u683d\u540e 3-5 \u5929\u642d\u906e\u9633\u7f51, \u7f13\u82d7\u540e\u9010\u6b65\u53bb\u9664")
    lines.append("")
    lines.append("\u514d\u8d23: \u672c\u7ed3\u679c\u4e3a\u6108\u5408\u671f\u7ba1\u7406\u4e0e\u6210\u6d3b\u7387\u81ea\u67e5, \u4e0d\u6784\u6210\u54c1\u79cd\u8bc4\u4ef7\u6216\u75c5\u5bb3\u6297\u6027\u7ed3\u8bba\u3002")
    lines.append("\u514d\u8d23: \u75c5\u539f\u68c0\u6d4b\u4e0e\u7827\u6728\u79cd\u5b50\u68c0\u75ab\u72b6\u6001\u4ee5\u68c0\u6d4b\u4e0e\u68c0\u75ab\u7ed3\u8bba\u4e3a\u51c6\u3002")
    lines.append("\u514d\u8d23: \u7528\u836f\u4e0e\u751f\u957f\u8c03\u8282\u5242\u4ee5\u4ea7\u54c1\u6807\u7b7e\u8bf4\u660e\u548c\u5f53\u5730\u519c\u6280\u90e8\u95e8\u8981\u6c42\u4e3a\u51c6\u3002")
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
    r.append(("\u7b2c 0 \u5929\u4e3a\u7b2c\u4e00\u9636\u6bb5", stage_of(0)[0] == "\u4e00"))
    r.append(("\u7b2c 2 \u5929\u4e3a\u7b2c\u4e09\u9636\u6bb5", stage_of(2)[0] == "\u4e09"))
    r.append(("\u7b2c 5 \u5929\u4e3a\u7b2c\u4e94\u9636\u6bb5", stage_of(5)[0] == "\u4e94"))
    r.append(("\u7b2c 9 \u5929\u4e3a\u7b2c\u516d\u9636\u6bb5", stage_of(9)[0] == "\u516d"))
    r.append(("\u7b2c 12 \u5929\u4e3a\u7b2c\u4e03\u9636\u6bb5", stage_of(12)[0] == "\u4e03"))
    r.append(("\u7b2c 30 \u5929\u4e3a\u5df2\u8fc7\u6108\u5408\u671f", stage_of(30)[0] == "\u5df2\u8fc7\u6108\u5408\u671f"))
    r.append(("\u9636\u6bb5\u7d22\u5f15\u5355\u8c03\u9012\u589e",
              stage_index(0) < stage_index(6) < stage_index(12)))
    r.append(("\u6210\u6d3b\u7387 90 \u6b63\u786e", survival_rate(100, 90) == 90.0))
    r.append(("\u6210\u6d3b\u7387\u56db\u820d\u4e94\u5165\u4e00\u4f4d\u5c0f\u6570", survival_rate(3, 2) == 66.7))
    r.append(("\u603b\u82d7\u6570\u4e3a 0 \u65f6\u6210\u6d3b\u7387\u4e3a 0", survival_rate(0, 5) == 0.0))
    r.append(("\u6210\u6d3b\u6570\u8d85\u603b\u6570\u88ab\u622a\u65ad", survival_rate(10, 15) == 100.0))
    r.append(("90% \u4e3a\u5408\u683c", rate_grade(90.0)[0] == "\u5408\u683c"))
    r.append(("75% \u4e3a\u504f\u4f4e", rate_grade(75.0)[0] == "\u504f\u4f4e"))
    r.append(("55% \u4e3a\u4e0d\u5408\u683c", rate_grade(55.0)[0] == "\u4e0d\u5408\u683c"))
    r.append(("30% \u4e3a\u4e25\u91cd\u4e0d\u5408\u683c", rate_grade(30.0)[0] == "\u4e25\u91cd\u4e0d\u5408\u683c"))
    r.append(("\u98ce\u9669\u7b49\u7ea7 0 \u5bf9\u5e94\u6b63\u5e38", risk_level(100, 95) == 0))
    r.append(("\u98ce\u9669\u7b49\u7ea7 3 \u5bf9\u5e94\u7acb\u5373\u505c\u6b62", risk_level(100, 10) == 3))
    r.append(("\u9ed1\u7c7d\u5357\u74dc\u5c5e\u540c\u79d1\u8fdc\u7f18",
              describe_rootstock("black_seed_pumpkin")["relation"] == "\u540c\u79d1\u8fdc\u7f18"))
    r.append(("\u91ce\u9ec4\u74dc\u4eb2\u7f18\u4e3a\u540c\u5c5e\u8fd1\u7f18",
              describe_rootstock("wild_cucumber")["relation"] == "\u540c\u5c5e\u8fd1\u7f18"))
    r.append(("\u91ce\u9ec4\u74dc\u4eb2\u548c\u6027\u6700\u9ad8",
              affinity_rank(describe_rootstock("wild_cucumber")["affinity"]) >=
              affinity_rank(describe_rootstock("black_seed_pumpkin")["affinity"])))
    r.append(("\u672a\u767b\u8bb0\u7827\u6728\u8fd4\u56de\u7a7a", describe_rootstock("none") is None))
    r.append(("\u63a5\u53e3\u53d1\u9ed1\u5bf9\u5e94\u6cbe\u6c34",
              "\u6cbe\u6c34" in SIGNS["black_soft"][0]))
    r.append(("\u63a5\u53e3\u53d1\u9709\u5bf9\u5e94\u9ad8\u6e7f",
              "\u9ad8\u6e7f" in SIGNS["mold"][0]))
    r.append(("\u82d7\u7ea7\u5171\u56db\u7ea7", len(GRADES) == 4))

    txt, s = build_report({
        "rootstock": "black_seed_pumpkin", "scion_state": "\u5408\u683c",
        "days_after_graft": 6, "stage_s_signs": ["black_soft"],
        "seedling_count": 100, "survived_count": 78,
    })
    r.append(("\u6837\u4f8b\u7827\u6728\u540d\u6b63\u786e", s["rootstock_name"] == "\u9ed1\u7c7d\u5357\u74dc\u7c7b"))
    r.append(("\u6837\u4f8b\u5b9a\u4f4d\u7b2c\u4e94\u9636\u6bb5", s["stage"] == "\u4e94"))
    r.append(("\u6837\u4f8b\u6210\u6d3b\u7387 78", s["survival_rate"] == 78.0))
    r.append(("\u6837\u4f8b\u5224\u4e3a\u504f\u4f4e", s["grade"] == "\u504f\u4f4e"))
    r.append(("\u6837\u4f8b\u8bb0\u5f55\u5f81\u5146", s["signs"] == ["black_soft"]))
    r.append(("\u6837\u4f8b\u4e0d\u63a8\u8350\u5546\u54c1", s["product_recommendation"] is False))
    r.append(("\u6837\u4f8b\u6587\u672c\u542b\u9636\u6bb5", "\u7b2c\u4e03\u9636\u6bb5" in txt))

    _, s2 = build_report({})
    r.append(("\u7a7a\u8f93\u5165\u4e0d\u62a5\u9519", s2["rootstock_name"] is None))
    r.append(("\u7a7a\u8f93\u5165\u65e0\u5f81\u5146", s2["signs"] == []))
    r.append(("\u7a7a\u8f93\u5165\u6210\u6d3b\u7387 0", s2["survival_rate"] == 0.0))

    _, s3 = build_report({"rootstock": "wild_cucumber", "days_after_graft": 30})
    r.append(("\u91ce\u9ec4\u74dc\u6837\u4f8b\u540d\u6b63\u786e", s3["rootstock_name"] == "\u91ce\u9ec4\u74dc\u7c7b"))
    r.append(("\u8d85\u671f\u5b9a\u4f4d\u5df2\u8fc7\u6108\u5408\u671f", s3["stage"] == "\u5df2\u8fc7\u6108\u5408\u671f"))

    r.append(("BOM \u8f93\u5165\u88ab\u6b63\u786e\u5265\u79bb",
               load_json(_write_bom_sample())["rootstock"] == "chowua"))
    r.append(("\u5b57\u7b26\u4e32\u5f62\u5f0f\u7684\u5f81\u5146\u53ef\u89e3\u6790",
               build_report({"stage_s_signs": ["mold"]})[1]["signs"] == ["mold"]))
    return r


def _write_bom_sample():
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "_selftest_bom_sample.json")
    with io.open(p, "w", encoding="utf-8") as f:
        f.write("\ufeff{\"rootstock\": \"chowua\", \"days_after_graft\": 6}")
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
        description="\u9ec4\u74dc\u5ac1\u63a5\u6108\u5408\u671f\u4e0e\u6210\u6d3b\u7387\u6838\u7b97\u5de5\u5177")
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
