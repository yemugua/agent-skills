# -*- coding: utf-8 -*-
"""\u6c34\u57f9\u8425\u517b\u6db2\u6d53\u5ea6\u4e0e\u7f3a\u7d20\u6392\u67e5\u5de5\u5177\u3002

\u7528\u6cd5:
  python hydro_check.py --file tank.json [--json]
  python hydro_check.py --selftest

\u672c\u5de5\u5177\u4e0d\u63a8\u8350\u8425\u517b\u6db2\u5546\u54c1, \u4e0d\u63d0\u4f9b\u914d\u65b9, \u4e0d\u8bca\u65ad\u75c5\u539f\u3002
"""
import argparse
import io
import json
import os
import sys

# \u4f5c\u7269 -> \u82d7\u671f/\u751f\u957f\u671f/\u6210\u719f\u671f EC \u533a\u95f4\u4e0e pH \u533a\u95f4
CROPS = {
    "lettuce": {"name": "\u751f\u83dc", "ec": (0.4, 0.8, 0.8, 1.2, 1.0, 1.6), "ph": (5.5, 6.5)},
    "bokchoy": {"name": "\u5c0f\u767d\u83dc", "ec": (0.4, 0.8, 0.8, 1.2, 1.0, 1.5), "ph": (5.5, 6.5)},
    "spinach": {"name": "\u83e0\u83dc", "ec": (0.5, 0.9, 0.9, 1.4, 1.2, 1.8), "ph": (5.5, 6.8)},
    "tomato": {"name": "\u756a\u8304", "ec": (0.6, 1.0, 1.2, 2.0, 1.8, 2.5), "ph": (5.5, 6.5)},
    "pepper": {"name": "\u8fa3\u6912", "ec": (0.5, 0.9, 1.0, 1.8, 1.6, 2.2), "ph": (5.5, 6.5)},
    "cucumber": {"name": "\u9ec4\u74dc", "ec": (0.6, 1.0, 1.2, 2.0, 1.8, 2.4), "ph": (5.5, 6.8)},
    "basil": {"name": "\u7f57\u52d2", "ec": (0.4, 0.8, 0.8, 1.4, 1.0, 1.6), "ph": (5.5, 6.5)},
    "strawberry": {"name": "\u8349\u8393", "ec": (0.5, 0.9, 0.9, 1.5, 1.2, 1.8), "ph": (5.5, 6.5)},
}

STAGE_INDEX = {"seedling": 0, "growing": 1, "mature": 2}

# \u75c7\u72b6 -> (\u63cf\u8ff0, \u75c5\u56e0\u7c7b\u522b, \u90e8\u4f4d, \u5904\u7f6e\u65b9\u5411)
SYMPTOMS = {
    "old_uniform_yellow": ("\u8001\u53f6\u5747\u5300\u53d1\u9ec4, \u4ece\u53f6\u5c16\u5411\u5185\u53d1\u5c55", "\u7f3a\u6c2e", "\u8001\u53f6",
                           "\u63d0\u9ad8\u6c2e\u7d20\u4f9b\u7ed9, \u590d\u6d4b EC"),
    "old_purple": ("\u8001\u53f6\u7d2b\u7ea2, \u53f6\u80cc\u6709\u6697\u8272", "\u7f3a\u78f7", "\u8001\u53f6",
                   "\u63d0\u9ad8\u78f7\u7d20\u4f9b\u7ed9; \u4f4e\u6e29\u65f6\u78f7\u5438\u6536\u5dee"),
    "old_margin_burn": ("\u8001\u53f6\u53f6\u7f18\u7126\u67af, \u53f6\u5c16\u5148\u67af", "\u7f3a\u94be", "\u8001\u53f6",
                        "\u63d0\u9ad8\u94be\u7d20\u4f9b\u7ed9"),
    "old_interveinal": ("\u8001\u53f6\u53f6\u8109\u95f4\u53d1\u9ec4, \u53f6\u8109\u4ecd\u7eff", "\u7f3a\u9541", "\u8001\u53f6",
                        "\u8865\u5145\u9541; \u4f4e\u6e29\u65f6\u9541\u5438\u6536\u53d7\u5f71\u54cd"),
    "new_interveinal": ("\u65b0\u53f6\u53d1\u9ec4\u4f46\u53f6\u8109\u6e05\u6670", "\u7f3a\u94c1", "\u65b0\u53f6",
                        "\u8c03\u6574 pH \u5e76\u4f9b\u94c1; pH \u8fc7\u9ad8\u65f6\u94c1\u88ab\u56fa\u5b9a"),
    "new_tip_curl": ("\u65b0\u53f6\u9876\u7aef\u5377\u66f2, \u751f\u957f\u70b9\u574f\u6b7b", "\u7f3a\u9499", "\u65b0\u53f6",
                     "\u4f9b\u9499; \u91cd\u70b9\u7a33\u6c34\u5206\u4e0e\u6839\u533a\u6e29\u5ea6"),
    "overall_pale": ("\u53f6\u7247\u6574\u4f53\u892a\u7eff\u53d1\u767d", "\u7f3a\u786b", "\u65b0\u53f6",
                     "\u4e0e\u7f3a\u6c2e\u533a\u5206: \u7f3a\u786b\u662f\u65b0\u53f6\u5148\u9ec4"),
    "root_brown": ("\u6839\u8910\u53d8, \u9ecf\u6ed1, \u6709\u5f02\u5473", "\u6839\u8150, \u4e0d\u662f\u7f3a\u7d20", "\u6839",
                   "\u5148\u67e5\u4f9b\u6c27\u4e0e\u6c34\u6e29, \u6309\u6839\u75c5\u5904\u7406"),
    "root_crust": ("\u6839\u8868\u6709\u8910\u8272\u9508\u6591\u6216\u767d\u8272\u9644\u7740\u7269", "\u6839\u90e8\u6c89\u79ef\u6216\u85fb\u7c7b", "\u6839",
                   "\u68c0\u67e5\u786c\u5ea6\u4e0e\u5149\u7167"),
    "leaf_spot": ("\u53f6\u7247\u51fa\u73b0\u6df1\u8272\u6591\u70b9\u6216\u9709\u5c42", "\u75c5\u5bb3, \u4e0d\u662f\u7f3a\u7d20", "\u53f6",
                  "\u9700\u4e13\u4e1a\u5224\u65ad, \u6309\u75c5\u5bb3\u5904\u7406"),
}


def stage_index(stage):
    return STAGE_INDEX.get((stage or "").strip(), 1)


def ec_range(crop, stage):
    c = CROPS.get(crop) or CROPS["lettuce"]
    v = c["ec"]
    i = stage_index(stage) * 2
    return v[i], v[i + 1]


def ph_range(crop):
    c = CROPS.get(crop) or CROPS["lettuce"]
    return c["ph"]


def mid_value(lo, hi):
    return round((lo + hi) / 2.0 * 10) / 10.0


def ec_status(ec, lo, hi):
    v = float(ec or 0)
    if v < lo:
        return 0, "\u4f4e\u4e8e\u533a\u95f4, \u5355\u6b21\u4e0a\u8c03\u4e0d\u8d85\u8fc7 0.2 mS/cm"
    if v > hi:
        return 2, "\u9ad8\u4e8e\u533a\u95f4, \u5355\u6b21\u4e0b\u8c03\u4e0d\u8d85\u8fc7 0.2 mS/cm"
    return 1, "\u5728\u533a\u95f4\u5185, \u7ef4\u6301\u89c2\u5bdf"


def ph_status(ph, lo, hi):
    v = float(ph or 0)
    if v < lo:
        return 0, "\u504f\u4f4e, \u9499\u9541\u5438\u6536\u53d7\u963b; \u6bcf\u6b21\u4e0a\u8c03 1 \u4e2a\u5355\u4f4d\u4ee5\u5185"
    if v > hi:
        return 2, "\u504f\u9ad8, \u94c1\u9530\u7b49\u5fae\u91cf\u5143\u7d20\u6613\u88ab\u56fa\u5b9a; \u6bcf\u6b21\u4e0b\u8c03 1 \u4e2a\u5355\u4f4d\u4ee5\u5185"
    return 1, "\u5728\u533a\u95f4\u5185, \u6bcf\u5929\u6d4b\u4e00\u6b21\u5fc5\u8981\u65f6\u8865\u8c03"


EC_GRADE = ["\u4f4e\u4e8e\u533a\u95f4", "\u533a\u95f4\u5185", "\u9ad8\u4e8e\u533a\u95f4"]
PH_GRADE = ["\u4f4e\u4e8e\u533a\u95f4", "\u533a\u95f4\u5185", "\u9ad8\u4e8e\u533a\u95f4"]


def change_cycle(days_since, temp_ok):
    d = float(days_since or 0)
    if temp_ok is False:
        return 5, 7, "\u6db2\u6e29\u504f\u9ad8, \u6362\u6db2\u5468\u671f\u7f29\u77ed"
    if d < 10:
        return 7, 10, "\u751f\u957f\u65fa\u76db\u671f\u5e38\u89c4\u5468\u671f"
    return 7, 10, "\u5df2\u63a5\u8fd1\u6362\u6db2\u5468\u671f"


def topup_liters(tank_liters, ec, lo, hi, evap_ratio=0.15):
    """\u6309\u84b8\u53d1\u6bd4\u4f8b\u4f30\u7b97\u8865\u6c34\u91cf\u3002EC \u504f\u9ad8\u8865\u6e05\u6c34, \u504f\u4f4e\u8865\u8425\u517b\u6db2\u3002"""
    v = float(tank_liters or 0)
    if v <= 0:
        return 0.0, "\u6db2\u91cf\u672a\u63d0\u4f9b, \u65e0\u6cd5\u4f30\u7b97"
    water = round(v * float(evap_ratio), 2)
    cur = float(ec or 0)
    if cur > hi:
        return water, "EC \u504f\u9ad8, \u8865\u6e05\u6c34"
    if cur < lo:
        return water, "EC \u504f\u4f4e, \u8865\u8425\u517b\u6db2"
    return water, "EC \u6b63\u5e38, \u8865\u6e05\u6c34\u540e\u590d\u6d4b\u786e\u8ba4"


ROOT_BRANCH = {
    "white": ("\u6839\u4e3a\u767d\u8272", "\u4f18\u5148\u6309\u7f3a\u7d20\u6392\u67e5"),
    "brown": ("\u6839\u5df2\u8910\u53d8", "\u5148\u5904\u7406\u6839\u533a, \u65e0\u8bba\u53f6\u5b50\u600e\u4e48\u9ec4\u90fd\u4e0d\u8981\u5148\u52a0\u80a5"),
    "black": ("\u6839\u5df2\u53d1\u9ed1\u53d1\u8f6f", "\u5148\u5904\u7406\u6839\u533a, \u5e76\u68c0\u67e5\u4f9b\u6c27\u4e0e\u6c34\u6e29"),
    "mushy": ("\u6839\u9ecf\u6ed1\u6709\u5f02\u5473", "\u5148\u5904\u7406\u6839\u533a, \u6309\u6839\u75c5\u5904\u7406, \u5fc5\u8981\u65f6\u8f6c\u4e13\u4e1a\u673a\u6784"),
}


def build_report(data):
    crop = data.get("crop", "")
    stage = data.get("stage", "")
    ec = data.get("ec", 0)
    ph = data.get("ph", 0)
    tank = data.get("tank_liters", 0)
    days = data.get("days_since_change", 0)
    temp_ok = data.get("temp_ok", None)
    symptoms = data.get("symptoms", []) or []
    root_state = (data.get("root_state", "") or "").strip()

    lines = []
    summary = {
        "crop": None, "ec_low": None, "ec_high": None, "ec_start": None,
        "ec_status": None, "ph_low": None, "ph_high": None,
        "ph_status": None, "topup_liters": None, "topup_advice": None,
        "root_branch": None, "symptoms": [], "product_recommended": False,
    }

    lines.append("=" * 68)
    lines.append("\u6c34\u57f9\u8425\u517b\u6db2\u6d53\u5ea6\u4e0e\u7f3a\u7d20\u6392\u67e5")
    lines.append("=" * 68)

    info = CROPS.get(crop) or CROPS["lettuce"]
    summary["crop"] = info["name"]
    lo, hi = ec_range(crop, stage)
    plo, phi = ph_range(crop)
    start = mid_value(lo, hi)
    summary["ec_low"] = lo
    summary["ec_high"] = hi
    summary["ec_start"] = start
    summary["ph_low"] = plo
    summary["ph_high"] = phi

    lines.append("[\u4e00] \u4f5c\u7269\u4e0e\u751f\u80b2\u9636\u6bb5")
    lines.append("-" * 68)
    lines.append("  \u4f5c\u7269: %s" % info["name"])
    lines.append("  \u751f\u80b2\u9636\u6bb5: %s" % (stage or "\u672a\u63d0\u4f9b, \u6309\u751f\u957f\u671f\u5904\u7406"))
    lines.append("")

    lines.append("[\u4e8c] EC \u6d53\u5ea6\u533a\u95f4")
    lines.append("-" * 68)
    lines.append("  \u672c\u9636\u6bb5\u533a\u95f4: %.1f - %.1f mS/cm" % (lo, hi))
    lines.append("    \u8d77\u6b65\u53e3\u5f84: \u53d6\u533a\u95f4\u4e2d\u4f4d\u504f\u4e0b %.1f mS/cm, \u89c2\u5bdf 3-5 \u5929\u65e0\u5f02\u5e38\u518d\u4e0a\u8c03" % start)
    lines.append("    \u8c03\u6574\u5e45\u5ea6: \u6bcf\u6b21\u4e0d\u8d85\u8fc7 0.2 mS/cm, \u8c03\u540e\u7b49 1-2 \u5929\u518d\u770b")
    e_st, e_adv = ec_status(ec, lo, hi)
    summary["ec_status"] = EC_GRADE[e_st]
    lines.append("  \u5f53\u524d\u5b9e\u6d4b: %g mS/cm -> %s" % (float(ec or 0), EC_GRADE[e_st]))
    lines.append("    \u8c03\u6574\u65b9\u5411: %s" % e_adv)
    lines.append("")
    lines.append("  \u5404\u4f5c\u7269\u5206\u9636\u6bb5\u533a\u95f4\u5bf9\u7167:")
    for k in ("lettuce", "bokchoy", "spinach", "tomato", "pepper",
              "cucumber", "basil", "strawberry"):
        v = CROPS[k]
        e = v["ec"]
        lines.append("    %-8s \u82d7 %.1f-%.1f  \u751f %.1f-%.1f  \u719f %.1f-%.1f  pH %.1f-%.1f" % (
            v["name"], e[0], e[1], e[2], e[3], e[4], e[5], v["ph"][0], v["ph"][1]))
    lines.append("")

    lines.append("[\u4e09] pH \u533a\u95f4")
    lines.append("-" * 68)
    lines.append("  \u533a\u95f4: %.1f - %.1f" % (plo, phi))
    p_st, p_adv = ph_status(ph, plo, phi)
    summary["ph_status"] = PH_GRADE[p_st]
    lines.append("  \u5f53\u524d\u5b9e\u6d4b: %g -> %s" % (float(ph or 0), PH_GRADE[p_st]))
    lines.append("    \u8c03\u8282\u65b9\u5411: %s" % p_adv)
    lines.append("    \u8c03\u6574\u5e45\u5ea6: \u6bcf\u6b21 1 \u4e2a\u5355\u4f4d\u4ee5\u5185, \u8c03\u540e\u9759\u7f6e 1-2 \u5c0f\u65f6\u590d\u6d4b")
    lines.append("    \u6b63\u5e38\u73b0\u8c61: pH \u6bcf\u5929\u4f1a\u5f80\u4e0b\u6389, \u6839\u7cfb\u547c\u5438\u4ea7\u9178, \u6309\u5929\u8c03\u5373\u53ef")
    lines.append("")

    lines.append("[\u56db] \u6362\u6db2\u4e0e\u8865\u6db2")
    lines.append("-" * 68)
    if temp_ok is None:
        lines.append("  \u672a\u63d0\u4f9b\u6db2\u6e29, \u6309\u751f\u957f\u65fa\u76db\u671f\u5e38\u89c4\u5468\u671f")
        clo, chi = 7, 10
        cnote = "\u672a\u63d0\u4f9b\u6db2\u6e29, \u6309\u5e38\u89c4"
    else:
        clo, chi, cnote = change_cycle(days, temp_ok)
    lines.append("  \u8ddd\u4e0a\u6b21\u6362\u6db2: %g \u5929" % float(days or 0))
    lines.append("    \u6362\u6db2\u5468\u671f: %d-%d \u5929 (%s)" % (clo, chi, cnote))
    lines.append("    \u82d7\u671f\u53ef\u5ef6\u957f\u5230 10-14 \u5929; \u9ad8\u6e29\u671f\u7f29\u77ed\u5230 5-7 \u5929")
    top, tadv = topup_liters(tank, ec, lo, hi)
    summary["topup_liters"] = top
    summary["topup_advice"] = tadv
    lines.append("  \u8865\u6db2\u4f30\u7b97: \u7ea6 %g L (%s)" % (top, tadv))
    lines.append("    \u5173\u952e\u52a8\u4f5c: \u8865\u6db2\u540e\u5fc5\u987b\u590d\u6d4b EC")
    lines.append("    \u5e38\u89c1\u9519\u8bef: \u53ea\u8865\u6c34\u4e0d\u8865\u8425\u517b\u6db2, \u6eb6\u8d28\u8d8a\u6765\u8d8a\u4f4e, \u690d\u682a\u6301\u7eed\u7f3a\u80a5")
    lines.append("    \u53f0\u8d26: \u6bcf\u6b21\u8bb0\u5f55\u65e5\u671f\u3001EC\u3001pH\u3001\u6e29\u5ea6\u3001\u6362\u6db2\u6216\u8865\u6db2\u91cf")
    lines.append("")

    lines.append("[\u4e94] \u7f3a\u7d20\u4e0e\u6839\u75c5\u5206\u6d41 (\u5148\u770b\u6839)")
    lines.append("-" * 68)
    if root_state and root_state in ROOT_BRANCH:
        label, advice = ROOT_BRANCH[root_state]
        summary["root_branch"] = advice
        lines.append("  \u6839\u7684\u72b6\u6001: %s" % label)
        lines.append("    \u5206\u6d41: %s" % advice)
    elif root_state:
        lines.append("  \u6839\u7684\u72b6\u6001: %s (\u672a\u767b\u8bb0, \u9700\u4eba\u5de5\u786e\u8ba4)" % root_state)
        lines.append("    \u5206\u6d41: \u6839\u767d\u53f6\u9ec4\u6309\u7f3a\u7d20\u6392\u67e5; \u6839\u8910\u53d8\u53d1\u81ed\u5148\u5904\u7406\u6839\u533a")
    else:
        lines.append("  \u672a\u63d0\u4f9b\u6839\u7684\u72b6\u6001, \u5206\u6d41\u53e3\u5f84\u5982\u4e0b:")
        lines.append("    \u6839\u662f\u767d\u7684, \u53ea\u662f\u53f6\u9ec4 -> \u4f18\u5148\u6309\u7f3a\u7d20\u6392\u67e5")
        lines.append("    \u6839\u5df2\u8910\u53d8\u53d1\u81ed       -> \u5148\u5904\u7406\u6839\u533a, \u65e0\u8bba\u53f6\u5b50\u600e\u4e48\u9ec4\u90fd\u4e0d\u8981\u5148\u52a0\u80a5")
    lines.append("")

    lines.append("[\u516d] \u75c7\u72b6\u5bf9\u7167")
    lines.append("-" * 68)
    if not symptoms:
        lines.append("  \u672a\u63d0\u4f9b\u75c7\u72b6")
    for s in symptoms:
        s = s.strip()
        if not s:
            continue
        if s in SYMPTOMS:
            desc, cause, part, action = SYMPTOMS[s]
            lines.append("  [%s] %s" % (part, desc))
            lines.append("    \u53ef\u80fd\u75c5\u56e0: %s" % cause)
            lines.append("    \u5904\u7f6e\u65b9\u5411: %s" % action)
            summary["symptoms"].append(s)
        else:
            lines.append("  [\u672a\u767b\u8bb0] %s -> \u9700\u4eba\u5de5\u6bd4\u5bf9\u75c7\u72b6\u8868" % s)
    lines.append("")
    lines.append("  \u5224\u65ad\u7b2c\u4e00\u6b65: \u8001\u53f6\u5148\u51fa\u73b0\u6307\u5411\u79fb\u52a8\u6027\u5143\u7d20\u4e0d\u8db3; \u65b0\u53f6\u5148\u51fa\u73b0\u6307\u5411\u4e0d\u53ef\u79fb\u52a8\u5143\u7d20\u4e0d\u8db3")
    lines.append("")

    lines.append("[\u4e03] \u5b89\u5168\u4e0e\u536b\u751f")
    lines.append("-" * 68)
    for c in ["\u6d53\u7f29\u8425\u517b\u6db2\u539f\u6db2\u653e\u5230\u9ad8\u5904\u6216\u4e0a\u9501\u67dc\u4e2d, \u513f\u7ae5\u4e0e\u5ba0\u7269\u4e0d\u53ef\u89e6\u53ca",
              "\u6e85\u5230\u76ae\u80a4\u7acb\u5373\u7528\u5927\u91cf\u6e05\u6c34\u51b2\u6d17",
              "\u81ea\u914d\u65f6\u6bcf\u79cd\u76d0\u5355\u72ec\u79f0\u91cf\u6eb6\u89e3, \u9010\u4e00\u6838\u5bf9\u540e\u518d\u6df7\u5408",
              "\u5148\u5927\u91cf\u5143\u7d20\u540e\u5fae\u91cf\u5143\u7d20, \u907f\u514d\u5c40\u90e8\u6d53\u5ea6\u8fc7\u9ad8\u70e7\u6839",
              "\u4e0d\u6df7\u7528\u4e24\u4e2a\u54c1\u724c\u7684\u8425\u517b\u6db2, \u4e0d\u6df7\u7528\u8425\u517b\u6db2\u4e0e\u81ea\u914d\u6db2",
              "\u5e9f\u8425\u517b\u6db2\u4e0d\u5012\u5165\u4e0b\u6c34\u9053\u76f4\u6392, \u6309\u5f53\u5730\u73af\u4fdd\u8981\u6c42\u5904\u7f6e",
              "\u6c34\u6cf5\u4e0e\u589e\u6c27\u6cf5\u4f7f\u7528\u5e26\u63a5\u5730\u63d2\u5ea7; \u6e7f\u533a\u4e0d\u5e26\u7535\u64cd\u4f5c"]:
        lines.append("  + %s" % c)
    lines.append("")
    lines.append("\u514d\u8d23: \u672c\u7ed3\u679c\u4e3a\u6d53\u5ea6\u533a\u95f4\u4e0e\u7f3a\u7d20\u5206\u6d41\u53e3\u5f84, \u4e0d\u6784\u6210\u8425\u517b\u6db2\u914d\u65b9\u6216\u75c5\u5bb3\u8bca\u65ad\u7ed3\u8bba\u3002")
    lines.append("\u514d\u8d23: \u5177\u4f53\u4ea7\u54c1\u4e0e\u7528\u91cf\u4ee5\u4ea7\u54c1\u8bf4\u660e\u548c\u5f53\u5730\u519c\u6280\u90e8\u95e8\u8981\u6c42\u4e3a\u51c6\u3002")
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
    r.append(("\u751f\u83dc\u82d7\u671f 0.4-0.8", ec_range("lettuce", "seedling") == (0.4, 0.8)))
    r.append(("\u751f\u83dc\u6210\u719f\u671f 1.0-1.6", ec_range("lettuce", "mature") == (1.0, 1.6)))
    r.append(("\u756a\u8304\u751f\u957f\u671f 1.2-2.0", ec_range("tomato", "growing") == (1.2, 2.0)))
    r.append(("\u9ec4\u74dc pH \u4e0a\u9650 6.8", ph_range("cucumber")[1] == 6.8))
    r.append(("\u672a\u767b\u8bb0\u4f5c\u7269\u56de\u843d\u751f\u83dc", ph_range("nope") == (5.5, 6.5)))
    r.append(("\u672a\u767b\u8bb0\u9636\u6bb5\u6309\u751f\u957f\u671f", ec_range("lettuce", "x") == (0.8, 1.2)))
    r.append(("\u4e2d\u4f4d\u53d6\u503c\u6b63\u786e", mid_value(0.8, 1.2) == 1.0))
    r.append(("EC \u4f4e\u4e8e\u533a\u95f4", ec_status(0.5, 0.8, 1.2)[0] == 0))
    r.append(("EC \u533a\u95f4\u5185", ec_status(1.0, 0.8, 1.2)[0] == 1))
    r.append(("EC \u9ad8\u4e8e\u533a\u95f4", ec_status(1.5, 0.8, 1.2)[0] == 2))
    r.append(("pH \u4f4e\u4e8e\u533a\u95f4", ph_status(5.0, 5.5, 6.5)[0] == 0))
    r.append(("pH \u533a\u95f4\u5185", ph_status(6.0, 5.5, 6.5)[0] == 1))
    r.append(("pH \u9ad8\u4e8e\u533a\u95f4", ph_status(7.0, 5.5, 6.5)[0] == 2))
    r.append(("\u9ad8\u6e29\u671f\u6362\u6db2 5-7 \u5929", change_cycle(3, False)[:2] == (5, 7)))
    r.append(("\u5e38\u6e29\u671f\u6362\u6db2 7-10 \u5929", change_cycle(3, True)[:2] == (7, 10)))
    r.append(("100 L \u8865\u6db2 15 L", topup_liters(100, 1.0, 0.8, 1.2)[0] == 15.0))
    r.append(("EC \u504f\u9ad8\u63d0\u793a\u8865\u6e05\u6c34", "\u6e05\u6c34" in topup_liters(100, 2.0, 0.8, 1.2)[1]))
    r.append(("EC \u504f\u4f4e\u63d0\u793a\u8865\u8425\u517b\u6db2", "\u8425\u517b\u6db2" in topup_liters(100, 0.5, 0.8, 1.2)[1]))
    r.append(("\u6db2\u91cf\u4e3a 0 \u65f6\u8865\u6db2\u4e3a 0", topup_liters(0, 1.0, 0.8, 1.2)[0] == 0.0))
    r.append(("\u767d\u6839\u6307\u5411\u7f3a\u7d20", "\u7f3a\u7d20" in ROOT_BRANCH["white"][1]))
    r.append(("\u8910\u6839\u6307\u5411\u6839\u533a", "\u6839\u533a" in ROOT_BRANCH["brown"][1]))
    r.append(("\u9ecf\u6ed1\u6839\u6307\u5411\u6839\u75c5", "\u6839\u75c5" in ROOT_BRANCH["mushy"][1]))
    r.append(("\u75c7\u72b6\u8868\u5171 10 \u6761", len(SYMPTOMS) == 10))
    r.append(("\u4f5c\u7269\u8868\u5171 8 \u79cd", len(CROPS) == 8))
    r.append(("\u6839\u8910\u53d8\u5224\u4e3a\u6839\u8150\u800c\u975e\u7f3a\u7d20", SYMPTOMS["root_brown"][1].startswith("\u6839\u8150")))
    r.append(("\u65b0\u53f6\u9ec4\u5224\u4e3a\u7f3a\u94c1", SYMPTOMS["new_interveinal"][1] == "\u7f3a\u94c1"))
    r.append(("\u8001\u53f6\u9ec4\u5224\u4e3a\u7f3a\u6c2e", SYMPTOMS["old_uniform_yellow"][1] == "\u7f3a\u6c2e"))
    r.append(("\u7f3a\u786b\u90e8\u4f4d\u4e3a\u65b0\u53f6", SYMPTOMS["overall_pale"][2] == "\u65b0\u53f6"))

    txt, s = build_report({
        "crop": "lettuce", "stage": "growing", "ec": 0.5, "ph": 6.0,
        "tank_liters": 50, "days_since_change": 8, "temp_ok": True,
        "root_state": "white", "symptoms": ["old_uniform_yellow"],
    })
    r.append(("\u6837\u4f8b\u4f5c\u7269\u4e3a\u751f\u83dc", s["crop"] == "\u751f\u83dc"))
    r.append(("\u6837\u4f8b EC \u4f4e\u4e8e\u533a\u95f4", s["ec_status"] == "\u4f4e\u4e8e\u533a\u95f4"))
    r.append(("\u6837\u4f8b pH \u533a\u95f4\u5185", s["ph_status"] == "\u533a\u95f4\u5185"))
    r.append(("\u6837\u4f8b\u8d77\u6b65 1.0", s["ec_start"] == 1.0))
    r.append(("\u6837\u4f8b\u8865\u6db2 7.5 L", s["topup_liters"] == 7.5))
    r.append(("\u6837\u4f8b\u5206\u6d41\u5230\u7f3a\u7d20", "\u7f3a\u7d20" in s["root_branch"]))
    r.append(("\u6837\u4f8b\u8bb0\u5f55\u75c7\u72b6", s["symptoms"] == ["old_uniform_yellow"]))
    r.append(("\u6837\u4f8b\u4e0d\u63a8\u8350\u5546\u54c1", s["product_recommended"] is False))
    r.append(("\u6837\u4f8b\u6587\u672c\u542b\u5224\u65ad\u7b2c\u4e00\u6b65", "\u5224\u65ad\u7b2c\u4e00\u6b65" in txt))

    _, s2 = build_report({})
    r.append(("\u7a7a\u8f93\u5165\u4e0d\u62a5\u9519", s2["crop"] == "\u751f\u83dc"))
    r.append(("\u7a7a\u8f93\u5165\u65e0\u6839\u5206\u6d41", s2["root_branch"] is None))
    r.append(("\u7a7a\u8f93\u5165\u65e0\u75c7\u72b6", s2["symptoms"] == []))

    _, s3 = build_report({"crop": "strawberry", "stage": "mature",
                          "ec": 2.5, "ph": 7.2, "root_state": "mushy",
                          "symptoms": ["root_brown", "nope"]})
    r.append(("\u8349\u8393\u6210\u719f\u671f\u4e0a\u9650 1.8", s3["ec_high"] == 1.8))
    r.append(("\u6837\u4f8b EC \u9ad8\u4e8e\u533a\u95f4", s3["ec_status"] == "\u9ad8\u4e8e\u533a\u95f4"))
    r.append(("\u6837\u4f8b pH \u9ad8\u4e8e\u533a\u95f4", s3["ph_status"] == "\u9ad8\u4e8e\u533a\u95f4"))
    r.append(("\u9ecf\u6ed1\u6839\u5206\u6d41\u5230\u6839\u75c5", "\u6839\u75c5" in s3["root_branch"]))
    r.append(("\u672a\u767b\u8bb0\u75c7\u72b6\u88ab\u5ffd\u7565", s3["symptoms"] == ["root_brown"]))

    r.append(("BOM \u8f93\u5165\u88ab\u6b63\u786e\u5265\u79bb",
               load_json(_write_bom_sample())["crop"] == "spinach"))
    r.append(("\u5b57\u7b26\u4e32\u5f62\u5f0f\u7684\u75c7\u72b6\u53ef\u89e3\u6790",
               build_report({"symptoms": ["new_tip_curl"]})[1]["symptoms"] ==
               ["new_tip_curl"]))
    return r


def _write_bom_sample():
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "_selftest_bom_sample.json")
    with io.open(p, "w", encoding="utf-8") as f:
        f.write("\ufeff{\"crop\": \"spinach\", \"stage\": \"growing\"}")
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
        description="\u6c34\u57f9\u8425\u517b\u6db2\u6d53\u5ea6\u4e0e\u7f3a\u7d20\u6392\u67e5\u5de5\u5177")
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
