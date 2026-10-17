# -*- coding: utf-8 -*-
"""\u86af\u8693\u5806\u80a5\u78b3\u6c2e\u6bd4\u914d\u6bd4\u4e0e\u8150\u719f\u5ea6\u5224\u5b9a\u5de5\u5177\u3002

\u7528\u6cd5:
  python vermi_calc.py --file compost.json [--json]
  python vermi_calc.py --selftest

\u672c\u5de5\u5177\u4e0d\u63a8\u8350\u4efb\u4f55\u836f\u5242, \u6d88\u6bd2\u5242\u4e0e\u9664\u81ed\u5242\u3002
"""
import argparse
import io
import json
import os
import sys

# \u76ee\u6807\u78b3\u6c2e\u6bd4: (\u8d77\u6b62\u6bd4, \u9636\u6bb5\u540d, \u8bf4\u660e)
TARGETS = {
    "start": (25.0, 30.0, "\u8d77\u59cb\u53d1\u9175\u671f", "\u5e38\u7528\u8d77\u70b9"),
    "breed": (20.0, 25.0, "\u86af\u8693\u7e41\u6b96\u671f", "\u78b3\u7565\u964d, \u6c2e\u7565\u5347"),
    "mature": (15.0, 20.0, "\u8150\u719f\u671f", "\u4ee5\u6c2e\u4e3a\u4e3b, \u4fc3\u5206\u89e3"),
}

# \u539f\u6599\u78b3\u6c2e\u6bd4
MATERIALS = {
    "leaves": ("\u843d\u53f6\u3001\u5e72\u6811\u53f6", 40.0, 80.0, "\u9ad8\u78b3(\u5e72\u6599)", "\u526a\u788e\u81f3 3-5 cm"),
    "straw": ("\u5e72\u8349\u3001\u79f8\u79c6", 60.0, 100.0, "\u9ad8\u78b3(\u5e72\u6599)", "\u526a\u788e\u81f3 3-5 cm"),
    "cardboard": ("\u7eb8\u677f\u3001\u725b\u76ae\u7eb8", 60.0, 100.0, "\u9ad8\u78b3(\u5e72\u6599)",
                  "\u6495\u788e\u6ce1\u8f6f, \u53bb\u6389\u5370\u5237\u4e0e\u80f6\u7c98\u90e8\u5206"),
    "coffee": ("\u5496\u5561\u6e23", 15.0, 20.0, "\u504f\u6c2e", "\u6ee4\u7eb8\u53bb\u6389, \u542b\u6c34\u7387\u9ad8\u9700\u667e"),
    "tea": ("\u8336\u53f6\u6e23", 15.0, 25.0, "\u504f\u6c2e", "\u6ee4\u7eb8\u53bb\u6389"),
    "fruit_peel": ("\u6c34\u679c\u76ae(\u82f9\u679c\u3001\u68a8)", 25.0, 40.0, "\u4e2d\u6027\u504f\u78b3", "\u5207\u788e\u3001\u6ca5\u6c34"),
    "melon_peel": ("\u74dc\u76ae(\u897f\u74dc\u3001\u751c\u74dc)", 20.0, 30.0, "\u4e2d\u6027", "\u5207\u788e\u3001\u6ca5\u6c34"),
    "veg_leaf": ("\u852c\u83dc\u53f6\u3001\u83dc\u5e2e", 15.0, 25.0, "\u504f\u6c2e", "\u5207\u788e"),
    "rice": ("\u5269\u7c73\u996d\u3001\u9992\u5934", 20.0, 30.0, "\u4e2d\u6027\u504f\u6c2e", "\u5f7b\u5e95\u6ca5\u5e72\u6216\u6652\u5e72"),
    "bean_residue": ("\u8c46\u6e23", 10.0, 15.0, "\u9ad8\u6c2e", "\u9700\u4e0e\u5e72\u6599\u914d\u6bd4\u4f7f\u7528"),
    "grass": ("\u65b0\u9c9c\u8349\u576a\u8349", 15.0, 25.0, "\u504f\u6c2e", "\u526a\u77ed\u3001\u5207\u788e"),
    "corrugated": ("\u7eb8\u7bb1\u74e6\u695e\u7eb8", 60.0, 90.0, "\u9ad8\u78b3", "\u6495\u788e\u6ce1\u8f6f"),
}

# \u542b\u6c34\u7387\u624b\u611f
MOISTURE = {
    "just_right": ("\u624b\u63e1\u80fd\u6210\u56e2, \u677e\u624b\u5373\u6563\u5f00", "\u5408\u9002", "\u7ef4\u6301"),
    "wet": ("\u624b\u63e1\u6210\u56e2, \u677e\u624b\u6210\u56e2\u4e0d\u6563, \u67d4\u8f6f\u53ef\u634f\u51fa\u5c11\u91cf\u6c34", "\u504f\u6e7f",
            "\u52a0\u5e72\u6599\u5e76\u7ffb\u677e, \u589e\u52a0\u901a\u6c14\u5b54"),
    "dry": ("\u624b\u63e1\u4e0d\u51fa\u6c34\u4f46\u6599\u677e\u6563, \u4e00\u634f\u5373\u788e", "\u504f\u5e72",
            "\u5206\u6b21\u5c11\u91cf\u52a0\u6c34, \u8fb9\u52a0\u8fb9\u62cc"),
    "soaked": ("\u624b\u63e1\u51fa\u6c34, \u6599\u6ef4\u6c34", "\u8fc7\u6e7f",
               "\u52a0\u5e72\u6599\u6bd4\u4f8b\u8f83\u5927, \u5145\u5206\u7ffb\u677e; \u5fc5\u8981\u65f6\u91cd\u65b0\u914d\u6599"),
}

# \u56db\u9636\u6bb5\u6e29\u5ea6
STAGES = [
    (0, 3, "\u5347\u6e29\u671f", "20\u2103 -> 40-50\u2103", "\u4e0d\u5e72\u9884, \u8bb0\u5f55\u6e29\u5ea6"),
    (3, 15, "\u9ad8\u6e29\u671f", "45-65\u2103", "\u86af\u8693\u5df2\u4e0b\u6c89\u6216\u94bb\u5165\u5e95\u5c42, \u5c5e\u6b63\u5e38"),
    (15, 30, "\u964d\u6e29\u671f", "40\u2103 -> 30\u2103", "\u53ef\u8f6c\u7bb1\u4e00\u6b21"),
    (30, 60, "\u8150\u719f\u671f", "25-30\u2103", "\u8865\u6599\u3001\u5224\u8150\u719f"),
]


def dry_parts(wet_parts, wet_cn, target_cn):
    """\u5e72\u6599\u4efd\u6570 = (\u6e7f\u6599\u4efd\u6570 \u00d7 \u6e7f\u6599\u78b3\u6c2e\u6bd4) / \u76ee\u6807\u78b3\u6c2e\u6bd4"""
    wp = float(wet_parts or 0)
    cn = float(wet_cn or 0)
    tgt = float(target_cn or 0)
    if tgt <= 0:
        return 0.0
    return round(wp * cn / tgt, 2)


def cn_status(target_cn):
    t = float(target_cn or 0)
    if 25.0 <= t <= 30.0:
        return "\u8d77\u59cb\u533a\u95f4", "\u8d77\u59cb\u53d1\u9175\u671f\u5e38\u7528\u8d77\u70b9"
    if 20.0 <= t < 25.0:
        return "\u7e41\u6b96\u533a\u95f4", "\u86af\u8693\u7e41\u6b96\u671f\u9002\u7528"
    if 15.0 <= t < 20.0:
        return "\u8150\u719f\u533a\u95f4", "\u8150\u719f\u671f\u9002\u7528"
    if t < 15.0:
        return "\u504f\u4f4e", "\u6c2e\u8fc7\u5269, \u6c28\u6325\u53d1\u98ce\u9669\u4e0e\u70e7\u6b7b\u86af\u8693\u98ce\u9669\u4e0a\u5347"
    return "\u504f\u9ad8", "\u78b3\u8fc7\u5269, \u5206\u89e3\u6162, \u5806\u4f53\u6e29\u5ea6\u4e0a\u4e0d\u53bb"


def stage_of(days):
    d = int(days or 0)
    for i, (lo, hi, name, temp, action) in enumerate(STAGES):
        if d < hi or i == len(STAGES) - 1:
            return name, temp, action, (d < lo)
    return "\u5df2\u8d85\u51fa\u5e38\u89c4\u5468\u671f", "", "", True


def temp_note(temp_c, smell):
    t = float(temp_c or 0)
    if t < 25:
        base = "\u6e29\u5ea6\u504f\u4f4e: \u67e5\u78b3\u6c2e\u6bd4\u662f\u5426\u8fc7\u9ad8\u6216\u6c34\u5206\u662f\u5426\u4e0d\u8db3"
    elif t <= 45:
        base = "\u6e29\u5ea6\u5904\u4e8e\u5347\u6e29\u6216\u4e2d\u6e29\u8303\u56f4, \u5c5e\u6b63\u5e38"
    elif t <= 65:
        base = "\u9ad8\u6e29\u671f: \u86af\u8693\u4e3b\u52a8\u4e0b\u6c89\u5c5e\u6b63\u5e38\u73b0\u8c61, \u4e0d\u8981\u7ffb\u52a8"
    elif t <= 70:
        base = "\u6e29\u5ea6\u504f\u9ad8: \u63a5\u8fd1\u4e0a\u9650, \u5173\u6ce8\u662f\u5426\u6301\u7eed\u5347\u9ad8"
    else:
        base = "\u6e29\u5ea6\u8fc7\u9ad8: \u52a0\u5e72\u6599\u3001\u644a\u8584\u3001\u589e\u52a0\u901a\u98ce"
    if smell in ("ammonia",):
        base += "; \u4f34\u968f\u6c28\u5473, \u6309\u6c2e\u8fc7\u5269\u4e0e\u7f3a\u6c27\u5904\u7f6e"
    elif smell in ("sour", "alcohol"):
        base += "; \u4f34\u968f\u9178\u5473\u6216\u9152\u5473, \u6309\u6c34\u5206\u8fc7\u9ad8\u4e0e\u7f3a\u6c27\u5904\u7f6e"
    return base


AMMONIA = [
    ("\u6210\u56e0 1", "\u78b3\u6c2e\u6bd4\u8fc7\u4f4e, \u6e7f\u6599(\u8c46\u6e23\u3001\u5269\u996d\u3001\u5496\u5561\u6e23)\u6bd4\u4f8b\u8fc7\u5927"),
    ("\u6210\u56e0 2", "\u5806\u4f53\u8fc7\u539a\u3001\u538b\u5b9e\u8fc7\u7d27, \u5185\u90e8\u7f3a\u6c27"),
    ("\u6210\u56e0 3", "\u901a\u6c14\u5b54\u5835\u585e\u6216\u7bb1\u4f53\u5bc6\u95ed, \u6c28\u6c14\u6392\u4e0d\u51fa\u53bb"),
    ("\u5904\u7f6e 1", "\u7acb\u5373\u52a0\u5e72\u6599(\u526a\u788e\u7684\u843d\u53f6\u3001\u79f8\u79c6\u3001\u7eb8\u677f)"),
    ("\u5904\u7f6e 2", "\u7ffb\u677e\u5806\u4f53\u3001\u589e\u52a0\u901a\u6c14\u5b54"),
    ("\u5904\u7f6e 3", "\u964d\u4f4e\u5806\u4f53\u539a\u5ea6\u3001\u644a\u5f00\u6269\u5927\u8868\u9762\u79ef"),
    ("\u5904\u7f6e 4", "\u79fb\u51fa\u4e0a\u90e8\u6599\u5c42, \u68c0\u67e5\u5e95\u5c42\u662f\u5426\u5df2\u7cca\u5316"),
]

SOUR = [
    ("\u6210\u56e0 1", "\u6c34\u5206\u8fc7\u9ad8, \u5806\u4f53\u538b\u5b9e, \u6c27\u6c14\u4e0d\u8db3\u540e\u8fdb\u5165\u538c\u6c27\u53d1\u9175"),
    ("\u6210\u56e0 2", "\u542b\u6c34\u7387\u9ad8\u7684\u53a8\u4f59\u6bd4\u4f8b\u8fc7\u5927\u4e14\u672a\u6ca5\u5e72"),
    ("\u6210\u56e0 3", "\u7ffb\u5806\u9891\u7387\u592a\u4f4e, \u957f\u671f\u4e0d\u6270\u52a8"),
    ("\u5904\u7f6e 1", "\u52a0\u5e72\u6599\u5e76\u5145\u5206\u7ffb\u677e, \u8ba9\u7a7a\u6c14\u8fdb\u5165\u5806\u4f53\u5185\u90e8"),
    ("\u5904\u7f6e 2", "\u51cf\u5c11\u540e\u7eed\u6e7f\u6599\u6295\u653e, \u7279\u522b\u662f\u9ad8\u542b\u6c34\u53a8\u4f59"),
    ("\u5904\u7f6e 3", "\u68c0\u67e5\u6392\u6c34\u5b54\u662f\u5426\u5835\u585e, \u5fc5\u8981\u65f6\u5e95\u90e8\u52a0\u900f\u6c14\u5c42"),
    ("\u5904\u7f6e 4", "\u4e25\u91cd\u53d1\u9178\u4e14\u5df2\u6e17\u6db2\u7684\u6599\u6574\u6279\u53d6\u51fa\u91cd\u65b0\u914d\u6599"),
]

MATURITY = [
    ("\u6c14\u5473", "\u65e0\u6c28\u5473\u3001\u65e0\u9178\u5473\u3001\u65e0\u9152\u5473; \u6de1\u6ce5\u571f\u5473\u6216\u8150\u6b96\u8d28\u6c14\u5473",
     "\u523a\u9f3b\u6c28\u5473\u3001\u9178\u8150\u5473\u6216\u9152\u5473"),
    ("\u989c\u8272", "\u5747\u5300\u8910\u8272\u6216\u6df1\u8910\u8272", "\u4ecd\u80fd\u770b\u5230\u660e\u663e\u7684\u6d45\u8272\u539f\u6599\u788e\u7247"),
    ("\u8d28\u5730", "\u677e\u8f6f\u3001\u6709\u8150\u6b96\u8d28\u611f\u3001\u634f\u4e4b\u5373\u6563", "\u9ecf\u3001\u7ed3\u5757\u3001\u6709\u751f\u786c\u539f\u6599\u611f"),
    ("\u6e29\u5ea6", "\u4e0e\u73af\u5883\u6e29\u5ea6\u63a5\u8fd1(25-30\u2103)", "\u4ecd\u660e\u663e\u9ad8\u4e8e\u73af\u5883\u6e29\u5ea6"),
]

BANNED_MATERIALS = [
    ("\u533b\u7597\u5e9f\u7269(\u7ef7\u5e26\u3001\u68c9\u7b7e\u3001\u9488\u5177\u3001\u836f\u54c1\u5305\u88c5)", "\u75c5\u539f\u98ce\u9669"),
    ("\u5ba0\u7269\u7caa\u4fbf", "\u53ef\u80fd\u5e26\u5bc4\u751f\u866b\u4e0e\u75c5\u539f"),
    ("\u8150\u8d25\u8089\u7c7b", "\u75c5\u539f\u4e0e\u62db\u866b"),
    ("\u542b\u6a1f\u8111\u4e38\u4e0e\u6740\u866b\u5242\u5305\u88c5\u7684\u7269\u54c1",
     "\u6a1f\u8111\u4e38\u5bf9\u86af\u8693\u662f\u5f3a\u6bd2\u7269, \u4e00\u9897\u5c31\u53ef\u80fd\u6bc1\u6389\u6574\u7bb1"),
    ("\u542b\u91cd\u91d1\u5c5e\u571f\u58e4\u3001\u5de5\u4e1a\u6c61\u6ce5", "\u91cd\u91d1\u5c5e\u5bcc\u96c6"),
    ("\u5efa\u7b51\u5783\u573e", "\u975e\u6709\u673a\u7269"),
]

BANNED_AGENTS = [
    ("\u6740\u866b\u5242", "\u6bd2\u6b7b\u86af\u8693"),
    ("\u6d88\u6bd2\u5242", "\u6740\u6b7b\u5806\u4f53\u5fae\u751f\u7269, \u7ec8\u6b62\u5206\u89e3"),
    ("\u9664\u81ed\u5242", "\u5e72\u6270\u83cc\u7fa4"),
    ("\u6c28\u6c34", "\u77ac\u95f4\u63d0\u9ad8 pH \u4e0e\u6c2e\u6d53\u5ea6"),
    ("\u77f3\u7070", "\u6539\u53d8 pH \u4e14\u4e0d\u5229\u86af\u8693, \u5c24\u5176\u5728\u53d1\u9178\u65f6"),
]


def maturity_checks(color, texture, temp_ok, smell_ok):
    checks = [
        ("\u6c14\u5473", bool(smell_ok)),
        ("\u989c\u8272", color == "brown"),
        ("\u8d28\u5730", texture == "crumbly"),
        ("\u6e29\u5ea6", bool(temp_ok)),
    ]
    passed = [c[0] for c in checks if c[1]]
    failed = [c[0] for c in checks if not c[1]]
    return checks, passed, failed


def build_report(data):
    wet = data.get("wet_parts", 0)
    wet_cn = data.get("wet_cn", 20)
    target = data.get("target_cn", 25)
    days = data.get("days", 0)
    temp_c = data.get("temp_c", 0)
    moisture = (data.get("moisture", "") or "").strip()
    smell = (data.get("smell", "") or "").strip()
    color = (data.get("color", "") or "").strip()
    texture = (data.get("texture", "") or "").strip()
    temp_ok = data.get("temp_ambient", None)
    smell_ok = data.get("smell_clean", None)

    lines = []
    summary = {
        "dry_parts": None, "cn_status": None, "stage": None,
        "moisture_state": None, "maturity_passed": None,
        "maturity_failed": None, "agent_recommended": False,
    }

    lines.append("=" * 68)
    lines.append("\u86af\u8693\u5806\u80a5\u78b3\u6c2e\u6bd4\u914d\u6bd4\u4e0e\u8150\u719f\u5ea6\u5224\u5b9a")
    lines.append("=" * 68)
    lines.append("  \u672c\u5de5\u5177\u4e0d\u63a8\u8350\u4efb\u4f55\u836f\u5242\u3001\u6d88\u6bd2\u5242\u4e0e\u9664\u81ed\u5242\u3002")
    lines.append("")

    lines.append("[\u4e00] \u78b3\u6c2e\u6bd4\u914d\u6bd4")
    lines.append("-" * 68)
    dp = dry_parts(wet, wet_cn, target)
    summary["dry_parts"] = dp
    lines.append("  \u6e7f\u6599\u4efd\u6570: %g   \u6e7f\u6599\u78b3\u6c2e\u6bd4: %g   \u76ee\u6807\u78b3\u6c2e\u6bd4: %g" % (
        float(wet or 0), float(wet_cn or 20), float(target or 25)))
    lines.append("  \u5e72\u6599\u4efd\u6570 = (\u6e7f\u6599\u4efd\u6570 \u00d7 \u6e7f\u6599\u78b3\u6c2e\u6bd4) / \u76ee\u6807\u78b3\u6c2e\u6bd4")
    lines.append("    -> %g \u4efd" % dp)
    cs, cnote = cn_status(target)
    summary["cn_status"] = cs
    lines.append("  \u76ee\u6807\u533a\u95f4\u5224\u5b9a: %s (%s)" % (cs, cnote))
    lines.append("")
    lines.append("  \u4e09\u9636\u6bb5\u76ee\u6807\u533a\u95f4:")
    for k in ("start", "breed", "mature"):
        lo, hi, name, note = TARGETS[k]
        lines.append("    %-12s %.0f:1 - %.0f:1  %s" % (name, lo, hi, note))
    lines.append("    \u78b3\u8fc7\u5269: \u5206\u89e3\u6162, \u6e29\u5ea6\u4e0a\u4e0d\u53bb; \u6c2e\u8fc7\u5269: \u6c28\u6325\u53d1, pH \u4e0a\u5347, \u70e7\u6b7b\u86af\u8693")
    lines.append("")
    lines.append("  \u63d0\u9192: \u6e7f\u6599\u5fc5\u987b\u5148\u6ca5\u6c34\u518d\u79f0\u91cd, \u5426\u5219\u79f0\u51fa\u7684\u91cd\u91cf\u91cc\u5927\u90e8\u5206\u662f\u6c34, \u914d\u6bd4\u5168\u9519")
    lines.append("")
    lines.append("  \u539f\u6599\u78b3\u6c2e\u6bd4\u5bf9\u7167:")
    for k in MATERIALS:
        v = MATERIALS[k]
        lines.append("    %-22s %.0f-%.0f  %s" % (v[0], v[1], v[2], v[3]))
        lines.append("      \u5904\u7406: %s" % v[4])
    lines.append("")

    lines.append("[\u4e8c] \u542b\u6c34\u7387\u5224\u5b9a")
    lines.append("-" * 68)
    if moisture and moisture in MOISTURE:
        desc, state, action = MOISTURE[moisture]
        summary["moisture_state"] = state
        lines.append("  \u624b\u611f: %s" % desc)
        lines.append("    \u5224\u5b9a: %s" % state)
        lines.append("    \u5904\u7f6e: %s" % action)
    elif moisture:
        lines.append("  \u624b\u611f\u4ee3\u53f7\u672a\u767b\u8bb0: %s, \u9700\u4eba\u5de5\u786e\u8ba4" % moisture)
    else:
        lines.append("  \u672a\u63d0\u4f9b\u624b\u611f, \u8bf7\u6309\u624b\u611f\u6cd5\u81ea\u6d4b")
    lines.append("")
    lines.append("  \u76ee\u6807\u533a\u95f4: 50%-60% (\u624b\u63e1\u6210\u56e2, \u677e\u5f00\u5373\u6563)")
    lines.append("  \u539f\u56e0: \u6c34\u592a\u591a\u5835\u585e\u86af\u8693\u4f53\u8868\u6c14\u5b54\u5bfc\u81f4\u7a92\u606f; \u6c34\u592a\u5c11\u4f53\u8868\u5931\u6c34\u6b7b\u4ea1")
    lines.append("  \u6d47\u6c34\u65b9\u5f0f: \u5c11\u91cf\u591a\u6b21, \u55b7\u6d12\u5728\u6599\u9762\u540e\u7ffb\u62cc\u5747\u5300")
    lines.append("")

    lines.append("[\u4e09] \u9636\u6bb5\u4e0e\u5806\u6e29 (\u8d77\u59cb\u540e\u7b2c %d \u5929)" % int(days or 0))
    lines.append("-" * 68)
    name, tnote, action, passed = stage_of(days)
    summary["stage"] = name
    lines.append("  \u5f53\u524d\u9636\u6bb5: %s" % name)
    lines.append("    \u5806\u6e29\u53c2\u8003: %s" % tnote)
    lines.append("    \u5173\u952e\u52a8\u4f5c: %s" % action)
    lines.append("    \u5806\u6e29\u6838\u5bf9: %s" % temp_note(temp_c, smell))
    lines.append("")
    lines.append("  \u56db\u9636\u6bb5\u65f6\u95f4\u8f74:")
    for lo, hi, sname, stemp, saction in STAGES:
        lines.append("    %-8s %2d-%2d \u5929: %s | %s" % (
            sname, lo, hi, stemp, saction))
    lines.append("")
    lines.append("  \u6d4b\u6e29\u53e3\u5f84: \u957f\u6746\u6e29\u5ea6\u8ba1\u63d2\u5165\u5806\u4f53\u4e2d\u5fc3, \u907f\u5f00\u8fb9\u7f18\u4e0e\u8868\u9762; \u540c\u4e00\u4f4d\u7f6e\u6bcf\u65e5\u540c\u4e00\u65f6\u95f4\u6d4b")
    lines.append("")

    lines.append("[\u56db] \u6c14\u5473\u5b9a\u4f4d\u4e0e\u5904\u7f6e")
    lines.append("-" * 68)
    if smell == "ammonia":
        lines.append("  \u5224\u5b9a: \u6c28\u5473 -> \u67e5\u6c2e\u8fc7\u5269\u4e0e\u7f3a\u6c27")
        lines.append("  \u4e0d\u55b7\u6c34, \u4e0d\u52a0\u6c28\u6c34, \u4e0d\u52a0\u6d88\u6bd2\u5242, \u4e0d\u55b7\u9664\u81ed\u5242")
        for tag, txt in AMMONIA:
            lines.append("    %s: %s" % (tag, txt))
    elif smell in ("sour", "alcohol"):
        lines.append("  \u5224\u5b9a: \u9178\u5473\u6216\u9152\u5473 -> \u67e5\u6c34\u5206\u8fc7\u9ad8\u4e0e\u7f3a\u6c27")
        lines.append("  \u4e0d\u55b7\u6c34, \u4e0d\u52a0\u77f3\u7070\u4e2d\u548c")
        for tag, txt in SOUR:
            lines.append("    %s: %s" % (tag, txt))
    elif smell == "none":
        lines.append("  \u5224\u5b9a: \u65e0\u6c28\u5473\u3001\u65e0\u9178\u5473\u3001\u65e0\u9152\u5473")
        lines.append("    \u7ee7\u7eed\u6309\u9636\u6bb5\u63a8\u8fdb, \u5230\u8150\u719f\u671f\u518d\u505a\u56db\u9879\u5224\u636e")
    elif smell:
        lines.append("  \u6c14\u5473\u4ee3\u53f7\u672a\u767b\u8bb0: %s, \u9700\u4eba\u5de5\u786e\u8ba4" % smell)
    else:
        lines.append("  \u672a\u63d0\u4f9b\u6c14\u5473, \u6bcf\u65e5\u95fb\u4e00\u6b21; \u5224\u65ad\u53e3\u8bc0: \u6c28\u5473\u67e5\u6c2e\u548c\u6c27, \u9178\u5473\u67e5\u6c34\u548c\u6c27")
    lines.append("")

    lines.append("[\u4e94] \u8150\u719f\u5ea6\u56db\u9879\u5224\u636e")
    lines.append("-" * 68)
    checks, passed_list, failed_list = maturity_checks(
        color, texture, temp_ok, smell_ok)
    summary["maturity_passed"] = passed_list
    summary["maturity_failed"] = failed_list
    lines.append("  %-6s %-8s %s" % ("\u5224\u636e", "\u72b6\u6001", "\u8150\u719f\u7279\u5f81 / \u672a\u719f\u7279\u5f81"))
    state_map = dict((k, v) for k, v in checks)
    for k, good, bad in MATURITY:
        st = state_map.get(k)
        lines.append("  %-6s %-8s %s" % (k, "\u901a\u8fc7" if st else "\u672a\u901a\u8fc7",
                                 good if st else bad))
    lines.append("")
    if failed_list:
        lines.append("  \u672a\u901a\u8fc7: %s -> \u5c1a\u672a\u8150\u719f, \u4e0d\u53ef\u4f7f\u7528" % "\u3001".join(failed_list))
    else:
        lines.append("  \u56db\u9879\u5168\u90e8\u901a\u8fc7 -> \u8fbe\u5230\u8150\u719f\u5224\u636e")
        lines.append("    \u4ecd\u9700\u9759\u7f6e\u719f\u5316 2-4 \u5468\u518d\u4f7f\u7528")
    lines.append("")
    lines.append("  \u8f85\u52a9\u5224\u636e: \u86af\u8693\u6570\u91cf\u660e\u663e\u51cf\u5c11\u751a\u81f3\u6d88\u5931 (\u4e0d\u662f\u8150\u719f\u6807\u51c6, \u53ea\u662f\u4f34\u968f\u73b0\u8c61)")
    lines.append("              \u539f\u6599\u5f62\u6001\u57fa\u672c\u6d88\u5931; \u4f53\u79ef\u660e\u663e\u7f29\u5c0f")
    lines.append("  \u4f7f\u7528\u53e3\u5f84: \u5bb6\u5ead\u5806\u80a5\u536b\u751f\u6307\u6807\u65e0\u6cd5\u5728\u5bb6\u786e\u8ba4, \u5efa\u8bae\u5148\u7528\u4e8e\u76c6\u683d\u82b1\u5349\u4e0e\u89c2\u53f6\u690d\u7269")
    lines.append("            \u672a\u5145\u5206\u8150\u719f\u7684\u5806\u80a5\u4e0d\u5f97\u76f4\u63a5\u63a5\u89e6\u53ef\u98df\u90e8\u4f4d")
    lines.append("")

    lines.append("[\u516d] \u7981\u5165\u7269\u6599")
    lines.append("-" * 68)
    for m, why in BANNED_MATERIALS:
        lines.append("  %-34s %s" % (m, why))
    lines.append("")

    lines.append("[\u4e03] \u4e0d\u5f97\u6dfb\u52a0\u7684\u836f\u5242")
    lines.append("-" * 68)
    for a, why in BANNED_AGENTS:
        lines.append("  %-10s %s" % (a, why))
    lines.append("")

    lines.append("\u514d\u8d23: \u672c\u7ed3\u679c\u4e3a\u78b3\u6c2e\u6bd4\u914d\u6bd4\u4e0e\u8150\u719f\u5ea6\u81ea\u67e5, \u4e0d\u6784\u6210\u536b\u751f\u68c0\u6d4b\u7ed3\u8bba\u3002")
    lines.append("\u514d\u8d23: \u539f\u6599\u78b3\u6c2e\u6bd4\u4e0e\u536b\u751f\u6307\u6807\u4ee5\u4e13\u4e1a\u68c0\u6d4b\u7ed3\u8bba\u4e3a\u51c6; \u5e9f\u5f03\u7269\u5904\u7f6e\u4ee5\u5f53\u5730\u89c4\u5b9a\u4e3a\u51c6\u3002")
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
    r.append(("\u6e7f\u6599 2 \u4efd\u78b3\u6c2e\u6bd4 20 \u76ee\u6807 25 \u5f97 1.6 \u4efd", dry_parts(2, 20, 25) == 1.6))
    r.append(("\u6e7f\u6599 5 \u4efd\u78b3\u6c2e\u6bd4 30 \u76ee\u6807 30 \u5f97 5 \u4efd", dry_parts(5, 30, 30) == 5.0))
    r.append(("\u76ee\u6807\u4e3a 0 \u65f6\u5f97 0", dry_parts(5, 20, 0) == 0.0))
    r.append(("\u6e7f\u6599\u4e3a 0 \u65f6\u5f97 0", dry_parts(0, 20, 25) == 0.0))
    r.append(("\u5e72\u6599\u4efd\u6570\u4fdd\u7559\u4e24\u4f4d\u5c0f\u6570", dry_parts(3, 22, 28) == 2.36))
    r.append(("25 \u5c5e\u8d77\u59cb\u533a\u95f4", cn_status(25)[0] == "\u8d77\u59cb\u533a\u95f4"))
    r.append(("30 \u5c5e\u8d77\u59cb\u533a\u95f4", cn_status(30)[0] == "\u8d77\u59cb\u533a\u95f4"))
    r.append(("22 \u5c5e\u7e41\u6b96\u533a\u95f4", cn_status(22)[0] == "\u7e41\u6b96\u533a\u95f4"))
    r.append(("18 \u5c5e\u8150\u719f\u533a\u95f4", cn_status(18)[0] == "\u8150\u719f\u533a\u95f4"))
    r.append(("12 \u4e3a\u504f\u4f4e", cn_status(12)[0] == "\u504f\u4f4e"))
    r.append(("40 \u4e3a\u504f\u9ad8", cn_status(40)[0] == "\u504f\u9ad8"))

    r.append(("\u7b2c 1 \u5929\u4e3a\u5347\u6e29\u671f", stage_of(1)[0] == "\u5347\u6e29\u671f"))
    r.append(("\u7b2c 5 \u5929\u4e3a\u9ad8\u6e29\u671f", stage_of(5)[0] == "\u9ad8\u6e29\u671f"))
    r.append(("\u7b2c 20 \u5929\u4e3a\u964d\u6e29\u671f", stage_of(20)[0] == "\u964d\u6e29\u671f"))
    r.append(("\u7b2c 40 \u5929\u4e3a\u8150\u719f\u671f", stage_of(40)[0] == "\u8150\u719f\u671f"))
    r.append(("\u56db\u9636\u6bb5\u65f6\u95f4\u8f74", len(STAGES) == 4))

    r.append(("\u6210\u56e2\u5373\u6563\u4e3a\u5408\u9002", MOISTURE["just_right"][1] == "\u5408\u9002"))
    r.append(("\u6210\u56e2\u4e0d\u6563\u4e3a\u504f\u6e7f", MOISTURE["wet"][1] == "\u504f\u6e7f"))
    r.append(("\u4e00\u634f\u5373\u788e\u4e3a\u504f\u5e72", MOISTURE["dry"][1] == "\u504f\u5e72"))
    r.append(("\u624b\u63e1\u51fa\u6c34\u4e3a\u8fc7\u6e7f", MOISTURE["soaked"][1] == "\u8fc7\u6e7f"))
    r.append(("\u542b\u6c34\u7387\u624b\u611f\u56db\u6863", len(MOISTURE) == 4))
    r.append(("\u539f\u6599\u8868 12 \u79cd", len(MATERIALS) == 12))
    r.append(("\u8c46\u6e23\u78b3\u6c2e\u6bd4\u6700\u4f4e", MATERIALS["bean_residue"][1] == 10.0))
    r.append(("\u79f8\u79c6\u78b3\u6c2e\u6bd4\u6700\u9ad8", MATERIALS["straw"][2] == 100.0))
    r.append(("\u7eb8\u677f\u8981\u53bb\u5370\u5237", "\u5370\u5237" in MATERIALS["cardboard"][4]))
    r.append(("\u6c28\u5473\u6210\u56e0 3 \u5904\u7f6e 4", len(AMMONIA) == 7))
    r.append(("\u9178\u5473\u6210\u56e0 3 \u5904\u7f6e 4", len(SOUR) == 7))
    r.append(("\u7981\u5165\u7269\u6599 6 \u7c7b", len(BANNED_MATERIALS) == 6))
    r.append(("\u6a1f\u8111\u4e38\u6807\u6ce8\u5f3a\u6bd2", "\u5f3a\u6bd2" in BANNED_MATERIALS[3][1]))
    r.append(("\u7981\u7528\u836f\u5242 5 \u7c7b", len(BANNED_AGENTS) == 5))
    r.append(("\u6d88\u6bd2\u5242\u7ec8\u6b62\u5206\u89e3", "\u7ec8\u6b62\u5206\u89e3" in BANNED_AGENTS[1][1]))
    r.append(("\u8150\u719f\u56db\u9879\u5224\u636e", len(MATURITY) == 4))

    ck, pa, fa = maturity_checks("brown", "crumbly", True, True)
    r.append(("\u56db\u9879\u5168\u901a\u8fc7", pa == ["\u6c14\u5473", "\u989c\u8272", "\u8d28\u5730", "\u6e29\u5ea6"] and fa == []))
    ck2, pa2, fa2 = maturity_checks("brown", "sticky", True, True)
    r.append(("\u8d28\u5730\u4e0d\u5408\u683c\u65f6\u5176\u4f59\u901a\u8fc7", "\u8d28\u5730" in fa2 and len(pa2) == 3))
    ck3, pa3, fa3 = maturity_checks("mixed", "sticky", False, False)
    r.append(("\u5168\u4e0d\u5408\u683c", len(fa3) == 4))

    txt, s = build_report({
        "wet_parts": 2, "wet_cn": 20, "target_cn": 25, "days": 5,
        "temp_c": 55, "moisture": "wet", "smell": "ammonia",
        "color": "mixed", "texture": "sticky", "temp_ambient": False,
        "smell_clean": False,
    })
    r.append(("\u6837\u4f8b\u5e72\u6599 1.6 \u4efd", s["dry_parts"] == 1.6))
    r.append(("\u6837\u4f8b\u8d77\u59cb\u533a\u95f4", s["cn_status"] == "\u8d77\u59cb\u533a\u95f4"))
    r.append(("\u6837\u4f8b\u4e3a\u9ad8\u6e29\u671f", s["stage"] == "\u9ad8\u6e29\u671f"))
    r.append(("\u6837\u4f8b\u542b\u6c34\u504f\u6e7f", s["moisture_state"] == "\u504f\u6e7f"))
    r.append(("\u6837\u4f8b\u56db\u9879\u5747\u672a\u901a\u8fc7", len(s["maturity_failed"]) == 4))
    r.append(("\u6837\u4f8b\u4e0d\u63a8\u8350\u836f\u5242", s["agent_recommended"] is False))
    r.append(("\u6837\u4f8b\u6587\u672c\u542b\u7981\u6b62\u55b7\u6c34", "\u4e0d\u55b7\u6c34" in txt))
    r.append(("\u6837\u4f8b\u6587\u672c\u542b\u5224\u65ad\u53e3\u8bc0", "\u5224\u65ad\u53e3\u8bc0" in build_report({})[0]))

    _, s2 = build_report({})
    r.append(("\u7a7a\u8f93\u5165\u4e0d\u62a5\u9519", s2["stage"] == "\u5347\u6e29\u671f"))
    r.append(("\u7a7a\u8f93\u5165\u5e72\u6599\u4e3a 0", s2["dry_parts"] == 0.0))
    r.append(("\u7a7a\u8f93\u5165\u65e0\u542b\u6c34\u5224\u5b9a", s2["moisture_state"] is None))

    _, s3 = build_report({"smell": "sour", "color": "brown",
                          "texture": "crumbly", "temp_ambient": True,
                          "smell_clean": True})
    r.append(("\u9178\u5473\u6837\u4f8b\u5168\u901a\u8fc7", len(s3["maturity_passed"]) == 4))
    r.append(("\u9178\u5473\u6837\u4f8b\u65e0\u672a\u901a\u8fc7\u9879", s3["maturity_failed"] == []))

    r.append(("BOM \u8f93\u5165\u88ab\u6b63\u786e\u5265\u79bb",
               load_json(_write_bom_sample())["target_cn"] == 30))
    r.append(("\u672a\u767b\u8bb0\u6c14\u5473\u4e0d\u62a5\u9519",
               build_report({"smell": "weird"})[1]["agent_recommended"] is False))
    return r


def _write_bom_sample():
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "_selftest_bom_sample.json")
    with io.open(p, "w", encoding="utf-8") as f:
        f.write("\ufeff{\"wet_parts\": 5, \"wet_cn\": 30, \"target_cn\": 30}")
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
        description="\u86af\u8693\u5806\u80a5\u78b3\u6c2e\u6bd4\u914d\u6bd4\u4e0e\u8150\u719f\u5ea6\u5224\u5b9a\u5de5\u5177")
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
