# -*- coding: utf-8 -*-
"""\u756a\u8304\u6574\u679d\u65b9\u5f0f\u63a8\u8350\u4e0e\u7559\u53f6\u7559\u679c\u6838\u7b97\u5de5\u5177\u3002

\u7528\u6cd5:
  python pruning_plan.py --file plant.json [--json]
  python pruning_plan.py --selftest

\u672c\u5de5\u5177\u4e0d\u8bca\u65ad\u75c5\u5bb3, \u4e0d\u7ed9\u519c\u836f\u4e0e\u751f\u957f\u8c03\u8282\u5242\u3002
"""
import argparse
import io
import json
import os
import sys

METHODS = {
    "single": {"name": "\u5355\u5e72\u6574\u679d", "stems": 1,
               "fit": "\u682a\u8ddd\u7a84\u3001\u5149\u7167\u4e0d\u8db3\u3001\u751f\u957f\u5b63\u957f\u3001\u5bc6\u5ea6\u9ad8\u7684\u751f\u4ea7\u573a\u666f"},
    "double": {"name": "\u53cc\u5e72\u6574\u679d", "stems": 2,
               "fit": "\u682a\u8ddd\u4e2d\u7b49\u3001\u5149\u7167\u8f83\u597d\u3001\u5bb6\u5ead\u5ead\u9662\u6216\u5c0f\u68da\u573a\u666f"},
    "quad": {"name": "\u56db\u5e72\u6574\u679d", "stems": 4,
              "fit": "\u682a\u8ddd\u5bbd\u3001\u5149\u7167\u5145\u8db3\u3001\u751f\u80b2\u671f\u77ed\u7684\u7c97\u653e\u573a\u666f"},
    "head": {"name": "\u6362\u5934\u6574\u679d", "stems": 1,
             "fit": "\u957f\u5b63\u8282\u683d\u57f9\u7eed\u63a5, \u907f\u514d\u690d\u682a\u8001\u5316"},
    "none": {"name": "\u7b80\u5316\u6574\u679d", "stems": 0,
             "fit": "\u52a0\u5de5\u756a\u8304\u3001\u90e8\u5206\u5ead\u9662\u7c97\u653e\u573a\u666f"},
}

# \u6bcf\u7a57\u6240\u9700\u529f\u80fd\u53f6\u6570(\u7ecf\u9a8c\u503c), \u4e0b\u6807\u4e3a\u7a57\u5e8f(\u4ece 1 \u5f00\u59cb)
LEAF_PER_TRUSS = {1: 2.5, 2: 2.0}
TRUSS_TAIL = {3: 1.75, 4: 1.5, 5: 1.4, 6: 1.3}


def leaf_needed(truss_no):
    n = int(truss_no or 0)
    if n <= 0:
        return 0.0
    if n in LEAF_PER_TRUSS:
        return LEAF_PER_TRUSS[n]
    if n >= 4:
        # \u7b2c\u56db\u7a57\u53ca\u4ee5\u540e\u6309 1.5 / 1.4 / 1.3 \u9012\u51cf, \u4e0e rules \u8868\u4e00\u81f4
        return TRUSS_TAIL.get(n, TRUSS_TAIL[6])
    return TRUSS_TAIL[3]


def recommend_method(spacing, light, long_season):
    sp = float(spacing or 0)
    lh = float(light or 0)
    if long_season:
        if lh < 5 or sp < 40:
            return "single", "\u957f\u5b63\u683d\u57f9\u4e14\u5149\u7167\u6216\u682a\u8ddd\u504f\u7d27, \u4f18\u5148\u5355\u5e72\u4fbf\u4e8e\u843d\u8513\u7eed\u63a5"
        return "head", "\u957f\u5b63\u683d\u57f9\u53ef\u8003\u8651\u6362\u5934\u6574\u679d\u7eed\u63a5\u7ed3\u679c, \u9700\u4eba\u5de5\u8ddf\u5f97\u4e0a"
    if sp < 35:
        return "single", "\u682a\u8ddd\u5c0f\u4e8e 35 cm, \u53ea\u80fd\u5355\u5e72"
    if sp < 50:
        if lh < 4:
            return "single", "\u682a\u8ddd\u4e2d\u7b49\u4f46\u5149\u7167\u4e0d\u8db3 4 \u5c0f\u65f6, \u4ecd\u4ee5\u5355\u5e72\u4e3a\u4e3b"
        return "double", "\u682a\u8ddd 35-50 cm \u4e14\u5149\u7167\u8fbe 4 \u5c0f\u65f6\u4ee5\u4e0a, \u53ef\u9009\u53cc\u5e72"
    if lh >= 6:
        return "quad", "\u682a\u8ddd\u5bbd\u4e14\u5149\u7167\u5145\u8db3, \u53ef\u8003\u8651\u56db\u5e72"
    return "double", "\u682a\u8ddd\u5bbd\u4f46\u5149\u7167\u4e0d\u8db3 6 \u5c0f\u65f6, \u53cc\u5e72\u6bd4\u56db\u5e72\u66f4\u7a33"


def prune_ratio_grade(pct):
    p = float(pct or 0)
    if p < 10:
        return 0, "\u5c11\u91cf, \u6b63\u5e38\u8282\u594f"
    if p <= 25:
        return 1, "\u4e2d\u7b49, \u5c5e\u6b63\u5e38\u4e0a\u9650"
    if p <= 50:
        return 2, "\u504f\u591a, \u8d85\u51fa\u4e0a\u9650, \u5efa\u8bae\u505c\u624b\u89c2\u5bdf 7 \u5929"
    return 3, "\u8fc7\u91cf, \u690d\u682a\u4f1a\u660e\u663e\u65e9\u8870\u4e0e\u51cf\u4ea7"


RATIO_TEXT = ["\u5c11\u91cf, \u6b63\u5e38\u8282\u594f", "\u4e2d\u7b49, \u5c5e\u6b63\u5e38\u4e0a\u9650",
              "\u504f\u591a, \u8d85\u51fa\u4e0a\u9650, \u5efa\u8bae\u505c\u624b\u89c2\u5bdf 7 \u5929",
              "\u8fc7\u91cf, \u690d\u682a\u4f1a\u660e\u663e\u65e9\u8870\u4e0e\u51cf\u4ea7"]


def tasks_of(days):
    d = int(days or 0)
    if d < 5:
        return "\u7f13\u82d7\u671f", "\u53ea\u786e\u8ba4\u6839\u7cfb\u6062\u590d, \u4e0d\u526a\u53f6; \u9ad8\u6e29\u65f6\u6bb5\u907f\u514d\u8fdb\u68da\u4f5c\u4e1a"
    if d <= 7:
        return "\u7f13\u82d7\u7ed3\u675f", "\u5f00\u59cb\u540a\u8513\u6216\u642d\u67b6\u56fa\u5b9a\u4e3b\u8513, \u4ecd\u4e0d\u526a\u53f6"
    if d <= 15:
        return "\u7b2c\u4e00\u6b21\u6574\u679d\u7a97\u53e3", "\u53bb\u9664\u7b2c\u4e00\u7a57\u82b1\u4e0b\u65b9\u814b\u82bd, \u5b9a\u9aa8\u67b6, \u8d8a\u65e9\u8d8a\u597d"
    if d <= 40:
        return "\u62b9\u814b\u82bd\u4e0e\u642d\u67b6\u7a97\u53e3", "\u6bcf\u5468\u81f3\u5c11\u4e00\u6b21\u62b9\u814b\u82bd, \u814b\u82bd 1-2 cm \u5ae9\u68a2\u72b6\u6001\u62b9\u9664"
    return "\u5e38\u89c4\u6574\u679d\u7a97\u53e3", "\u9010\u6b21\u6253\u6748\u3001\u53bb\u8001\u53f6\u9ec4\u53f6\u75c5\u53f6; \u5355\u6b21\u526a\u9664\u4e0d\u8d85\u8fc7\u5168\u682a 1/4; \u76ee\u6807\u7a57\u6570\u5750\u4f4f\u540e\u6458\u5fc3"


def load_balance(healthy_leaves, truss_count, per_truss_fruit=5):
    leaves = float(healthy_leaves or 0)
    trusses = int(truss_count or 0)
    total_needed = 0.0
    detail = []
    for i in range(1, trusses + 1):
        need = leaf_needed(i)
        total_needed += need
        detail.append((i, need))
    max_trusses = 0
    acc = 0.0
    for i in range(1, 21):
        acc += leaf_needed(i)
        if acc <= leaves:
            max_trusses = i
    fruit_capacity = int(max_trusses * float(per_truss_fruit or 5))
    overloaded = trusses > max_trusses
    return {
        "total_needed": round(total_needed, 2),
        "max_trusses": max_trusses,
        "fruit_capacity": fruit_capacity,
        "overloaded": overloaded,
        "detail": detail,
    }


SYMPTOMS = {
    "no_fruit": ["\u786e\u8ba4\u76f4\u5c04\u5149\u662f\u5426\u8fbe 5 \u5c0f\u65f6\u4ee5\u4e0a", "\u67e5\u591c\u6e29\u662f\u5426\u8fc7\u9ad8(\u591c\u6e29\u9ad8\u4f1a\u6291\u5236\u5750\u679c)",
                 "\u67e5\u6c2e\u80a5\u662f\u5426\u8fc7\u91cf\u3001\u78f7\u94be\u662f\u5426\u4e0d\u8db3", "\u67e5\u6253\u6748\u662f\u5426\u8fc7\u72e0\u3001\u529f\u80fd\u53f6\u662f\u5426\u4e0d\u8db3",
                 "\u67e5\u662f\u5426\u9047\u8fde\u7eed\u9634\u96e8\u5929\u6216\u9ad8\u6e29\u9ad8\u591c\u6e29"],
    "small_fruit": ["\u67e5\u7559\u679c\u91cf\u662f\u5426\u8d85\u8f7d", "\u67e5\u6839\u533a\u662f\u5426\u7f3a\u6c34",
                    "\u67e5\u529f\u80fd\u53f6\u662f\u5426\u4e0d\u8db3", "\u67e5\u6e29\u5ea6\u662f\u5426\u8fc7\u4f4e\u5f71\u54cd\u5438\u6536"],
    "black_bottom": ["\u67e5\u6839\u533a\u6c34\u5206\u662f\u5426\u5ffd\u5e72\u5ffd\u6e7f(\u9499\u4f9b\u7ed9\u6ce2\u52a8\u7684\u6839\u56e0)",
                     "\u67e5\u571f\u58e4\u662f\u5426\u5ffd\u5e72\u5ffd\u6e7f", "\u67e5\u6c2e\u80a5\u662f\u5426\u8fc7\u91cf", "\u67e5\u679c\u5b9e\u662f\u5426\u8d85\u8f7d"],
    "sunburn": ["\u67e5\u662f\u5426\u9634\u96e8\u5929\u9aa4\u6674\u7a81\u7136\u66b4\u6652", "\u67e5\u53f6\u7247\u662f\u5426\u88ab\u526a\u592a\u591a\u5931\u53bb\u906e\u836b", "\u67e5\u662f\u5426\u9ad8\u6e29"],
    "wilt_after": ["\u67e5\u5de5\u5177\u662f\u5426\u6d88\u6bd2", "\u67e5\u662f\u5426\u6e7f\u526a", "\u67e5\u526a\u9664\u91cf\u662f\u5426\u8d85 1/4", "\u67e5\u662f\u5426\u4f24\u5230\u4e3b\u8513"],
    "leggy": ["\u67e5\u591c\u6e29\u662f\u5426\u8fc7\u9ad8", "\u67e5\u6c2e\u80a5\u662f\u5426\u8fc7\u91cf", "\u67e5\u5149\u7167\u662f\u5426\u4e0d\u8db3", "\u67e5\u662f\u5426\u672a\u53ca\u65f6\u62b9\u814b\u82bd"],
}


def build_report(data):
    spacing = data.get("spacing_cm", 0)
    light = data.get("light_hours", 0)
    long_season = bool(data.get("long_season", False))
    leaves = data.get("healthy_leaves", 0)
    trusses = data.get("truss_count", 0)
    per_truss = data.get("per_truss_fruit", 5)
    days = data.get("days_after_planting", 0)
    prune_pct = data.get("last_prune_percent", 0)
    symptoms = data.get("symptoms", []) or []

    lines = []
    summary = {
        "method": None, "method_name": None,
        "current_task": None,
        "max_trusses": None, "fruit_capacity": None,
        "overloaded": None, "prune_ratio_grade": None,
        "symptoms": [], "pesticide_recommended": False,
    }

    lines.append("=" * 68)
    lines.append("\u756a\u8304\u6574\u679d\u65b9\u5f0f\u63a8\u8350\u4e0e\u7559\u53f6\u7559\u679c\u6838\u7b97")
    lines.append("=" * 68)

    lines.append("[\u4e00] \u6574\u679d\u65b9\u5f0f\u63a8\u8350")
    lines.append("-" * 68)
    key, why = recommend_method(spacing, light, long_season)
    info = METHODS[key]
    summary["method"] = key
    summary["method_name"] = info["name"]
    lines.append("  \u63a8\u8350\u65b9\u5f0f: %s (\u4fdd\u7559\u4e3b\u8513 %s)" % (info["name"], info["stems"] or "\u5c11\u5e72\u9884"))
    lines.append("    \u5224\u65ad\u4f9d\u636e: %s" % why)
    lines.append("    \u9002\u7528\u6761\u4ef6: %s" % info["fit"])
    lines.append("")
    lines.append("  \u5404\u65b9\u5f0f\u5bf9\u7167:")
    for k in ("single", "double", "quad", "head", "none"):
        m = METHODS[k]
        lines.append("    %-10s \u4e3b\u8513 %s: %s" % (m["name"], m["stems"] or "\u5c11\u5e72\u9884", m["fit"]))
    lines.append("")
    lines.append("  \u682a\u8ddd\u91cf\u5316\u53e3\u5f84: \u5c0f\u4e8e 35 cm \u53ea\u80fd\u5355\u5e72; 35-50 cm \u53ef\u53cc\u5e72; \u5927\u4e8e 50 cm \u624d\u8003\u8651\u56db\u5e72")
    lines.append("")

    lines.append("[\u4e8c] \u5f53\u524d\u65f6\u95f4\u7a97\u5e94\u505a\u7684\u4e8b\u9879 (\u5b9a\u690d\u540e\u7b2c %d \u5929)" % int(days or 0))
    lines.append("-" * 68)
    stage, todo = tasks_of(days)
    summary["current_task"] = stage
    lines.append("  \u5f53\u524d\u9636\u6bb5: %s" % stage)
    lines.append("    \u5e94\u505a: %s" % todo)
    lines.append("    \u9891\u7387\u4e0b\u9650: \u6253\u6748\u4e0e\u62b9\u814b\u82bd\u95f4\u9694\u4e0d\u8d85\u8fc7 7 \u5929")
    lines.append("    \u526a\u9664\u4e0a\u9650: \u5355\u6b21\u526a\u9664\u4e0d\u8d85\u8fc7\u5168\u682a\u679d\u53f6 1/4")
    lines.append("")

    lines.append("[\u4e09] \u5355\u6b21\u526a\u9664\u91cf\u4f30\u7b97")
    lines.append("-" * 68)
    g, _ = prune_ratio_grade(prune_pct)
    summary["prune_ratio_grade"] = g
    lines.append("  \u672c\u6b21\u526a\u9664\u6bd4\u4f8b: %g%% -> %s" % (float(prune_pct or 0), RATIO_TEXT[g]))
    lines.append("  \u8d85\u51fa 25% \u7684\u5904\u7406: \u505c\u6b62\u6574\u679d, \u89c2\u5bdf 7 \u5929\u518d\u5224\u65ad")
    lines.append("")

    lines.append("[\u56db] \u7559\u53f6\u7559\u679c\u6838\u7b97")
    lines.append("-" * 68)
    bal = load_balance(leaves, trusses, per_truss)
    summary["max_trusses"] = bal["max_trusses"]
    summary["fruit_capacity"] = bal["fruit_capacity"]
    summary["overloaded"] = bal["overloaded"]
    lines.append("  \u529f\u80fd\u53f6\u6570: %g \u7247" % float(leaves or 0))
    lines.append("  \u5df2\u7559\u7a57\u6570: %d \u7a57, \u6bcf\u7a57\u6309 %g \u4e2a\u679c\u8ba1" % (int(trusses or 0), float(per_truss or 5)))
    lines.append("  \u5df2\u7559\u7a57\u6240\u9700\u529f\u80fd\u53f6\u5408\u8ba1: %g \u7247" % bal["total_needed"])
    lines.append("  \u5f53\u524d\u529f\u80fd\u53f6\u53ef\u652f\u6491\u7684\u7a57\u6570\u4e0a\u9650: %d \u7a57" % bal["max_trusses"])
    lines.append("  \u5bf9\u5e94\u679c\u5b9e\u627f\u8f7d\u91cf: \u7ea6 %d \u4e2a" % bal["fruit_capacity"])
    if bal["overloaded"]:
        lines.append("  [\u8d85\u8f7d] \u5df2\u7559\u7a57\u6570\u8d85\u8fc7\u529f\u80fd\u53f6\u652f\u6491\u4e0a\u9650, \u9700\u758f\u679c")
        lines.append("    \u8d85\u8f7d\u540e\u679c: \u679c\u5b9e\u81a8\u5927\u6162, \u843d\u679c, \u8110\u8150, \u65e5\u707c, \u9876\u7aef\u5c0f\u53f6\u5377\u66f2")
    else:
        lines.append("  \u672a\u8d85\u8f7d, \u4fdd\u6301\u5f53\u524d\u7559\u679c\u91cf")
    lines.append("")
    lines.append("  \u5404\u7a57\u6b21\u6bcf\u7a57\u6240\u9700\u529f\u80fd\u53f6\u6570:")
    for i, need in bal["detail"]:
        lines.append("    \u7b2c %d \u7a57: %.2f \u7247" % (i, need))
    if not bal["detail"]:
        lines.append("    \u672a\u63d0\u4f9b\u7a57\u6570")
    lines.append("")
    lines.append("  \u529f\u80fd\u53f6\u81ea\u67e5: \u5728\u690d\u682a\u4e2d\u90e8\u9009\u4e00\u7247\u4e3b\u529f\u80fd\u53f6, \u5f80\u4e0a\u627e\u5b83\u4f9b\u7ed9\u7684\u679c\u7a57;")
    lines.append("    \u5224\u65ad\u8fd9\u7247\u53f6\u88ab\u526a\u6389\u540e\u8be5\u7a57\u679c\u8fd8\u80fd\u4e0d\u80fd\u6b63\u5e38\u81a8\u5927; \u4e0d\u80fd\u5373\u529f\u80fd\u53f6\u4e0d\u8db3")
    lines.append("")

    lines.append("[\u4e94] \u75c7\u72b6\u6392\u67e5\u987a\u5e8f (\u4e0d\u80fd\u8df3\u6b65)")
    lines.append("-" * 68)
    if not symptoms:
        lines.append("  \u672a\u63d0\u4f9b\u75c7\u72b6")
    for s in symptoms:
        s = s.strip()
        if not s:
            continue
        if s in SYMPTOMS:
            lines.append("  [\u6392\u67e5] %s" % s)
            for i, step in enumerate(SYMPTOMS[s], 1):
                lines.append("    %d. %s" % (i, step))
            summary["symptoms"].append(s)
        else:
            lines.append("  [\u672a\u767b\u8bb0] %s -> \u9700\u4eba\u5de5\u6bd4\u5bf9\u6392\u67e5\u8868" % s)
    lines.append("")

    lines.append("[\u516d] \u4f24\u53e3\u5904\u7406\u8981\u70b9")
    lines.append("-" * 68)
    for c in ["\u659c\u526a\u7565\u9ad8\u4e8e\u814b\u82bd, \u8d34\u7d27\u814b\u82bd\u57fa\u90e8\u4e0d\u7559\u957f\u6869",
              "\u4e0d\u6d82\u7259\u818f\u8349\u6728\u7070\u7b49\u975e\u63a8\u8350\u7269\u8d28, \u5207\u53e3\u4fdd\u6301\u5e72\u71e5\u901a\u98ce",
              "\u526a\u5200\u6bcf\u6362\u4e00\u682a\u6216\u4e00\u6279\u91cd\u65b0\u6d88\u6bd2, \u6d88\u6bd2\u6db2\u73b0\u914d\u73b0\u7528",
              "\u4e0d\u5728\u96e8\u540e\u3001\u9732\u6c34\u672a\u5e72\u3001\u6d47\u6c34\u540e\u7acb\u523b\u526a",
              "\u526a\u4e0b\u7684\u679d\u53f6\u5f53\u5929\u5e26\u51fa\u7530\u5916\u96c6\u4e2d\u65e0\u5bb3\u5316\u5904\u7406"]:
        lines.append("  + %s" % c)
    lines.append("")
    lines.append("\u514d\u8d23: \u672c\u7ed3\u679c\u4e3a\u6574\u679d\u53e3\u5f84\u4e0e\u7559\u679c\u91cf\u6838\u7b97, \u4e0d\u6784\u6210\u75c5\u5bb3\u8bca\u65ad\u6216\u519c\u836f\u4f7f\u7528\u7ed3\u8bba\u3002")
    lines.append("\u514d\u8d23: \u836f\u5242\u4e0e\u8c03\u8282\u5242\u4ee5\u4ea7\u54c1\u6807\u7b7e\u8bf4\u660e\u548c\u5f53\u5730\u519c\u6280\u90e8\u95e8\u8981\u6c42\u4e3a\u51c6\u3002")
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
    r.append(("\u95e8\u679c\u9700 2.5 \u7247\u529f\u80fd\u53f6", leaf_needed(1) == 2.5))
    r.append(("\u7b2c\u4e8c\u7a57\u9700 2 \u7247\u529f\u80fd\u53f6", leaf_needed(2) == 2.0))
    r.append(("\u7b2c\u4e09\u7a57\u9700 1.75 \u7247", leaf_needed(3) == 1.75))
    r.append(("\u7b2c\u56db\u7a57\u9700 1.5 \u7247", leaf_needed(4) == 1.5))
    r.append(("\u7b2c\u4e94\u7a57\u9700 1.4 \u7247", leaf_needed(5) == 1.4))
    r.append(("\u7b2c\u516d\u7a57\u9700 1.3 \u7247", leaf_needed(6) == 1.3))
    r.append(("\u7b2c\u5341\u7a57\u6309 1.3 \u7247\u5c01\u5e95", leaf_needed(10) == 1.3))
    r.append(("\u7a57\u5e8f 0 \u4e0d\u8ba1\u529f\u80fd\u53f6", leaf_needed(0) == 0.0))
    r.append(("20 \u7247\u53f6\u652f\u6491 13 \u7a57", load_balance(20, 8)["max_trusses"] == 13))
    r.append(("5 \u7247\u53f6\u652f\u6491 2 \u7a57", load_balance(5, 2)["max_trusses"] == 2))
    r.append(("3 \u7247\u53f6\u652f\u6491 1 \u7a57", load_balance(3, 1)["max_trusses"] == 1))
    r.append(("2 \u7247\u53f6\u4e0d\u8db3\u95e8\u679c", load_balance(2, 1)["max_trusses"] == 0))
    r.append(("13 \u7a57\u672a\u8d85\u8f7d",
              load_balance(20, 13)["overloaded"] is False))
    r.append(("14 \u7a57\u8d85\u51fa\u4e0a\u9650\u5224\u8d85\u8f7d",
              load_balance(20, 14)["overloaded"] is True))
    r.append(("\u6bcf\u7a57 5 \u679c\u65f6\u627f\u8f7d\u91cf\u6b63\u786e",
              load_balance(20, 13, 5)["fruit_capacity"] == 65))
    r.append(("\u6240\u9700\u529f\u80fd\u53f6\u5408\u8ba1\u6b63\u786e",
              load_balance(10, 2)["total_needed"] == 4.5))
    r.append(("\u682a\u8ddd 30 \u9009\u5355\u5e72", recommend_method(30, 6, False)[0] == "single"))
    r.append(("\u682a\u8ddd 40 \u5149\u7167 5 \u9009\u53cc\u5e72", recommend_method(40, 5, False)[0] == "double"))
    r.append(("\u682a\u8ddd 40 \u5149\u7167 3 \u9009\u5355\u5e72", recommend_method(40, 3, False)[0] == "single"))
    r.append(("\u682a\u8ddd 60 \u5149\u7167 7 \u9009\u56db\u5e72", recommend_method(60, 7, False)[0] == "quad"))
    r.append(("\u682a\u8ddd 60 \u5149\u7167 4 \u9009\u53cc\u5e72", recommend_method(60, 4, False)[0] == "double"))
    r.append(("\u957f\u5b63\u683d\u57f9\u9009\u5355\u5e72\u6216\u6362\u5934",
              recommend_method(40, 7, True)[0] == "head"))
    r.append(("\u957f\u5b63\u683d\u57f9\u5149\u7167\u4e0d\u8db3\u9009\u5355\u5e72",
              recommend_method(30, 4, True)[0] == "single"))
    r.append(("\u526a\u9664 5% \u4e3a\u5c11\u91cf", prune_ratio_grade(5)[0] == 0))
    r.append(("\u526a\u9664 25% \u5c5e\u4e0a\u9650", prune_ratio_grade(25)[0] == 1))
    r.append(("\u526a\u9664 40% \u4e3a\u504f\u591a", prune_ratio_grade(40)[0] == 2))
    r.append(("\u526a\u9664 60% \u4e3a\u8fc7\u91cf", prune_ratio_grade(60)[0] == 3))
    r.append(("\u7b2c 3 \u5929\u4e3a\u7f13\u82d7\u671f", tasks_of(3)[0] == "\u7f13\u82d7\u671f"))
    r.append(("\u7b2c 7 \u5929\u4e3a\u7f13\u82d7\u7ed3\u675f", tasks_of(7)[0] == "\u7f13\u82d7\u7ed3\u675f"))
    r.append(("\u7b2c 12 \u5929\u4e3a\u7b2c\u4e00\u6b21\u6574\u679d\u7a97\u53e3", tasks_of(12)[0] == "\u7b2c\u4e00\u6b21\u6574\u679d\u7a97\u53e3"))
    r.append(("\u7b2c 30 \u5929\u4e3a\u62b9\u814b\u82bd\u7a97\u53e3", tasks_of(30)[0] == "\u62b9\u814b\u82bd\u4e0e\u642d\u67b6\u7a97\u53e3"))
    r.append(("\u7b2c 90 \u5929\u4e3a\u5e38\u89c4\u6574\u679d\u7a97\u53e3", tasks_of(90)[0] == "\u5e38\u89c4\u6574\u679d\u7a97\u53e3"))
    r.append(("\u4e0d\u7ed3\u679c\u6392\u67e5\u4e3a 5 \u6b65", len(SYMPTOMS["no_fruit"]) == 5))
    r.append(("\u840e\u852b\u6392\u67e5\u4e3a 4 \u6b65", len(SYMPTOMS["wilt_after"]) == 4))
    r.append(("\u5355\u5e72\u4fdd\u7559 1 \u4e3b\u8513", METHODS["single"]["stems"] == 1))
    r.append(("\u56db\u5e72\u4fdd\u7559 4 \u4e3b\u8513", METHODS["quad"]["stems"] == 4))

    txt, s = build_report({
        "spacing_cm": 40, "light_hours": 5, "long_season": False,
        "healthy_leaves": 20, "truss_count": 14, "per_truss_fruit": 5,
        "days_after_planting": 12, "last_prune_percent": 15,
        "symptoms": ["no_fruit"],
    })
    r.append(("\u6837\u4f8b\u63a8\u8350\u53cc\u5e72", s["method"] == "double"))
    r.append(("\u6837\u4f8b\u540d\u79f0\u6b63\u786e", s["method_name"] == "\u53cc\u5e72\u6574\u679d"))
    r.append(("\u6837\u4f8b\u9636\u6bb5\u6b63\u786e", s["current_task"] == "\u7b2c\u4e00\u6b21\u6574\u679d\u7a97\u53e3"))
    r.append(("\u6837\u4f8b\u4e0a\u9650 13 \u7a57", s["max_trusses"] == 13))
    r.append(("\u6837\u4f8b\u5224\u4e3a\u8d85\u8f7d", s["overloaded"] is True))
    r.append(("\u6837\u4f8b\u627f\u8f7d 65 \u4e2a", s["fruit_capacity"] == 65))
    r.append(("\u6837\u4f8b\u526a\u9664\u4e3a\u4e2d\u7b49", s["prune_ratio_grade"] == 1))
    r.append(("\u6837\u4f8b\u8bb0\u5f55\u75c7\u72b6", s["symptoms"] == ["no_fruit"]))
    r.append(("\u6837\u4f8b\u4e0d\u63a8\u8350\u836f\u5242", s["pesticide_recommended"] is False))
    r.append(("\u6837\u4f8b\u6587\u672c\u542b\u81ea\u67e5", "\u529f\u80fd\u53f6\u81ea\u67e5" in txt))

    _, s2 = build_report({})
    r.append(("\u7a7a\u8f93\u5165\u4e0d\u62a5\u9519", s2["method"] == "single"))
    r.append(("\u7a7a\u8f93\u5165\u65e0\u75c7\u72b6", s2["symptoms"] == []))
    r.append(("\u7a7a\u8f93\u5165\u4e0d\u8d85\u8f7d", s2["overloaded"] is False))

    _, s3 = build_report({"healthy_leaves": 20, "truss_count": 13,
                          "symptoms": ["unknown_sign"]})
    r.append(("\u672a\u77e5\u75c7\u72b6\u88ab\u5ffd\u7565", s3["symptoms"] == []))
    r.append(("13 \u7a57\u4e0d\u8d85\u8f7d", s3["overloaded"] is False))

    r.append(("BOM \u8f93\u5165\u88ab\u6b63\u786e\u5265\u79bb",
               load_json(_write_bom_sample())["spacing_cm"] == 40))
    r.append(("\u5b57\u7b26\u4e32\u5f62\u5f0f\u7684\u75c7\u72b6\u53ef\u89e3\u6790",
               build_report({"symptoms": ["leggy"]})[1]["symptoms"] == ["leggy"]))
    return r


def _write_bom_sample():
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "_selftest_bom_sample.json")
    with io.open(p, "w", encoding="utf-8") as f:
        f.write("\ufeff{\"spacing_cm\": 40, \"light_hours\": 5}")
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
        description="\u756a\u8304\u6574\u679d\u65b9\u5f0f\u63a8\u8350\u4e0e\u7559\u53f6\u7559\u679c\u6838\u7b97\u5de5\u5177")
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
