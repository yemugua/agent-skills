# -*- coding: utf-8 -*-
"""\u98df\u7528\u83cc\u83cc\u68d2\u53c2\u6570\u4e0e\u6c61\u67d3\u5206\u7ea7\u5de5\u5177\u3002

\u7528\u6cd5:
  python mushroom_check.py --file kit.json [--json]
  python mushroom_check.py --selftest

\u672c\u5de5\u5177\u4e0d\u63d0\u4f9b\u83cc\u79cd\u54c1\u7cfb, \u4e0d\u63d0\u4f9b\u836f\u5242\u4e0e\u6d88\u6bd2\u5242\u3002
"""
import argparse
import io
import json
import os
import sys

# \u7c7b\u578b -> \u53d1\u83cc\u6e29\u5ea6\u3001\u51fa\u83c7\u6e29\u5ea6\u3001\u6e7f\u5ea6\u3001\u5f00\u888b\u65f6\u673a\u3001\u91c7\u6536\u5468\u671f
KINDS = {
    "oyster": {"name": "\u5e73\u83c7\u7c7b", "inc": (20, 25), "fru": (15, 25),
               "rh": (85, 95), "open": "\u83cc\u4e1d\u57fa\u672c\u957f\u6ee1\u3001\u888b\u53e3\u51fa\u73b0\u539f\u57fa\u540e\u5212\u53e3",
               "pick": "\u6bcf\u5929\u6216\u9694\u5929"},
    "shiitake": {"name": "\u9999\u83c7\u7c7b", "inc": (20, 25), "fru": (15, 22),
                 "rh": (85, 90), "open": "\u83cc\u4e1d\u957f\u6ee1\u540e\u6309\u4f9b\u79cd\u65b9\u8981\u6c42\u5904\u7406",
                 "pick": "\u6570\u5929\u4e00\u6279"},
    "enoki": {"name": "\u91d1\u9488\u83c7\u7c7b", "inc": (18, 22), "fru": (8, 15),
              "rh": (80, 90), "open": "\u6309\u4f9b\u79cd\u65b9\u8981\u6c42\u5957\u888b\u6216\u4e0d\u5957\u888b",
              "pick": "\u6574\u6279\u4e00\u6b21\u91c7"},
    "woodear": {"name": "\u6728\u8033\u7c7b", "inc": (22, 28), "fru": (18, 26),
                "rh": (85, 95), "open": "\u83cc\u4e1d\u957f\u6ee1\u540e\u5212\u53e3",
                "pick": "\u6bcf\u5929\u6216\u9694\u5929"},
    "kingoyster": {"name": "\u674f\u9c8d\u83c7\u7c7b", "inc": (20, 25), "fru": (15, 20),
                   "rh": (85, 90), "open": "\u83cc\u4e1d\u957f\u6ee1\u540e\u5f00\u888b",
                   "pick": "\u9694\u5929\u91c7"},
    "tea_tree": {"name": "\u8336\u6811\u83c7\u7c7b", "inc": (22, 26), "fru": (18, 24),
                 "rh": (85, 95), "open": "\u83cc\u4e1d\u957f\u6ee1\u540e\u5212\u53e3",
                 "pick": "\u9694\u5929\u91c7"},
}

STAGE_KEY = {"spawn": "inc", "fruit": "fru"}

# \u6c61\u67d3\u5f81\u5146 -> (\u63cf\u8ff0, \u53ef\u80fd\u6c61\u67d3\u6e90, \u7d27\u6025\u7b49\u7ea7)
SIGNS = {
    "green_fluffy": ("\u7eff\u8272\u6216\u9ec4\u7eff\u8272\u7ed2\u6bdb\u72b6\u9709\u5c42", "\u7eff\u9709\u7c7b", "\u9ad8"),
    "green_dot": ("\u6df1\u7eff\u8272\u6591\u70b9\u3001\u8fb9\u754c\u6e05\u6670", "\u7eff\u9709\u7c7b\u65e9\u671f", "\u4e2d"),
    "red_purple": ("\u7ea2\u8272\u6216\u7d2b\u8272\u7ed2\u6bdb", "\u7ea2\u8272\u9709\u83cc\u7c7b", "\u9ad8"),
    "white_flurry": ("\u767d\u8272\u7d6e\u72b6\u7269\u5feb\u901f\u6269\u5c55", "\u68c9\u72b6\u9709\u83cc", "\u4e2d"),
    "black_fluffy": ("\u9ed1\u8272\u6591\u70b9\u6216\u9ed1\u8272\u7ed2\u6bdb", "\u9ed1\u8272\u9709\u83cc\u7c7b", "\u9ad8"),
    "alcohol": ("\u660e\u663e\u9152\u5473\u6216\u53d1\u9175\u5473", "\u7ec6\u83cc\u6c61\u67d3", "\u6700\u9ad8"),
    "sour": ("\u9178\u5473\u3001\u9178\u8d25\u5473\u3001\u523a\u9f3b\u5473", "\u7ec6\u83cc\u6c61\u67d3", "\u6700\u9ad8"),
    "ooze": ("\u6e17\u6db2\u3001\u5e26\u989c\u8272\u3001\u6709\u9ecf\u6027", "\u7ec6\u83cc\u6c61\u67d3\u5e76\u5df2\u53d8\u8d28", "\u6700\u9ad8"),
    "patchy": ("\u83cc\u4e1d\u53ea\u5728\u5c40\u90e8\u751f\u957f\u3001\u5927\u7247\u7a7a\u888b", "\u63a5\u79cd\u4e0d\u5747\u6216\u5df2\u6c61\u67d3", "\u4e2d"),
    "yellow_mycelium": ("\u83cc\u4e1d\u53d1\u9ec4\u3001\u53d8\u8910\u3001\u505c\u6b62\u751f\u957f", "\u6e29\u5ea6\u4e0d\u8fbe\u6807\u6216\u6c61\u67d3", "\u4e2d"),
}

URGENT_ORDER = {"\u4e2d": 1, "\u9ad8": 2, "\u6700\u9ad8": 3}

ACTIONS = [
    ("\u505c\u6b62\u55b7\u6c34", "\u6c61\u67d3\u6269\u6563\u6700\u5feb\u7684\u6761\u4ef6\u662f\u9ad8\u6e7f"),
    ("\u79fb\u51fa\u9694\u79bb", "\u6c61\u67d3\u68d2\u5355\u72ec\u79fb\u51fa\u5e76\u5bc6\u5c01, \u4e0d\u5728\u539f\u73af\u5883\u5185\u5904\u7406"),
    ("\u52a0\u5f3a\u901a\u98ce\u964d\u6e29", "\u964d\u4f4e\u73af\u5883\u6e7f\u5ea6, \u6291\u5236\u5b62\u5b50\u840c\u53d1"),
    ("\u5355\u72ec\u5bc6\u5c01", "\u5bc6\u5c01\u540e\u518d\u6309\u5f53\u5730\u8981\u6c42\u5904\u7f6e"),
    ("\u8bb0\u5f55", "\u8bb0\u5f55\u6c61\u67d3\u7387\u4e0e\u4f4d\u7f6e, \u5224\u65ad\u662f\u73af\u5883\u95ee\u9898\u8fd8\u662f\u6279\u6b21\u95ee\u9898"),
    ("\u590d\u67e5", "\u8f7b\u5ea6\u6bcf\u65e5\u590d\u67e5, \u89c2\u5bdf\u662f\u5426\u6269\u6563"),
]

# \u6c61\u67d3\u7387\u5206\u7ea7
GRADES = [
    (0.0, "\u65e0\u6c61\u67d3", "\u6b63\u5e38\u7ba1\u7406"),
    (5.0, "\u8f7b\u5ea6", "\u52a0\u5f3a\u901a\u98ce\u3001\u964d\u6e29\u964d\u6e7f, \u5355\u72ec\u9694\u79bb\u653e\u7f6e, \u6bcf\u65e5\u590d\u67e5"),
    (15.0, "\u4e2d\u5ea6", "\u6c61\u67d3\u68d2\u79fb\u51fa\u5e76\u5355\u72ec\u5bc6\u5c01\u5904\u7406; \u5065\u5eb7\u68d2\u5206\u533a\u7ba1\u7406"),
    (30.0, "\u91cd\u5ea6", "\u6c61\u67d3\u68d2\u5168\u90e8\u79fb\u51fa\u5e76\u5bc6\u5c01; \u68c0\u67e5\u73af\u5883\u6e7f\u5ea6\u4e0e\u901a\u98ce\u662f\u5426\u5931\u6548"),
]


def temp_status(v, lo, hi):
    x = float(v or 0)
    if lo <= x <= hi:
        return "\u8fbe\u6807", "\u7ef4\u6301\u73b0\u72b6"
    if x < lo:
        return "\u504f\u4f4e", "\u79fb\u81f3\u6e29\u6696\u5904; \u6e29\u5ea6\u4e0d\u8fbe\u6807\u540e\u9762\u65e0\u6cd5\u8865\u6551"
    return "\u504f\u9ad8", "\u79fb\u81f3\u9634\u51c9\u5904\u3001\u52a0\u906e\u9633\u3001\u5730\u9762\u6d12\u6c34\u3001\u901a\u98ce; \u4e0d\u6d47\u5927\u91cf\u51b7\u6c34\u964d\u6e29"


def humidity_status(v, lo, hi):
    x = float(v or 0)
    if lo <= x <= hi:
        return "\u8fbe\u6807", "\u7ef4\u6301\u73b0\u6709\u55b7\u6c34\u8282\u594f"
    if x < lo:
        return "\u504f\u4f4e", "\u5730\u9762\u6d12\u6c34\u3001\u8986\u76d6\u6e7f\u5e03\u3001\u5468\u56f4\u653e\u6c34\u76c6"
    return "\u504f\u9ad8", "\u505c\u6b62\u55b7\u6c34\u5e76\u52a0\u5f3a\u901a\u98ce; \u8868\u9762\u957f\u671f\u6f6e\u6e7f\u662f\u6742\u83cc\u5b62\u5b50\u840c\u53d1\u6700\u6709\u5229\u7684\u73af\u5883"


def contamination_rate(total, contaminated):
    t = float(total or 0)
    c = float(contaminated or 0)
    if t <= 0:
        return 0.0
    if c > t:
        c = t
    return round(c * 100.0 / t, 1)


def grade_of(rate):
    out = GRADES[-1]
    for lim, name, action in GRADES:
        if rate <= lim:
            return name, action
        out = (lim, name, action)
    return out[1], out[2]


def pick_ready(cap_open, days_since_open):
    """\u91c7\u6536\u65f6\u673a\u5224\u5b9a: \u83cc\u76d6\u672a\u5b8c\u5168\u644a\u5f00\u3001\u8fb9\u7f18\u4ecd\u5185\u5377\u65f6\u91c7\u6536\u3002"""
    d = float(days_since_open or 0)
    if cap_open is True:
        return "\u4e0d\u9002\u7528", "\u83cc\u76d6\u5df2\u5b8c\u5168\u644a\u5f00, \u6b64\u65f6\u91c7\u6536\u5b62\u5b50\u91cf\u5df2\u504f\u591a; \u4e0b\u4e00\u6279\u5e94\u63d0\u524d\u91c7"
    if cap_open is False:
        return "\u672a\u5230", "\u83cc\u76d6\u4ecd\u5377\u66f2, \u7ee7\u7eed\u7ba1\u7406; \u83cc\u76d6\u7531\u5377\u66f2\u53d8\u4e3a\u5e73\u5c55\u4f46\u8fb9\u7f18\u4ecd\u5185\u5377\u65f6\u91c7\u6536"
    if d < 3:
        return "\u504f\u65e9", "\u5f00\u888b\u540e 3 \u5929\u5185\u901a\u5e38\u672a\u6210\u719f, \u7ee7\u7eed\u7ba1\u7406"
    return "\u63a5\u8fd1", "\u6309\u83cc\u76d6\u5f62\u6001\u5224\u65ad: \u5e73\u5c55\u4f46\u8fb9\u7f18\u4ecd\u5185\u5377\u5373\u91c7\u6536"


def build_report(data):
    kind = data.get("kind", "")
    stage = (data.get("stage", "spawn") or "spawn").strip()
    temp = data.get("temp_c", 0)
    hum = data.get("humidity", 0)
    total = data.get("total", 0)
    contaminated = data.get("contaminated", 0)
    signs = data.get("signs", []) or []
    cap_open = data.get("cap_open", None)
    days = data.get("days_since_open", 0)

    lines = []
    summary = {
        "kind": None, "temp_status": None, "humidity_status": None,
        "contam_rate": None, "grade": None, "worst_urgency": None,
        "pick": None, "pesticide_recommended": False,
    }

    lines.append("=" * 68)
    lines.append("\u98df\u7528\u83cc\u83cc\u68d2\u53c2\u6570\u4e0e\u6c61\u67d3\u5206\u7ea7")
    lines.append("=" * 68)
    lines.append("  \u672c\u5de5\u5177\u4e0d\u63d0\u4f9b\u83cc\u79cd\u54c1\u7cfb, \u4e0d\u63d0\u4f9b\u836f\u5242\u4e0e\u6d88\u6bd2\u5242\u3002")
    lines.append("")

    info = KINDS.get(kind) or KINDS["oyster"]
    summary["kind"] = info["name"]
    key = STAGE_KEY.get(stage, "inc")

    lines.append("[\u4e00] \u7c7b\u578b\u4e0e\u9636\u6bb5\u53c2\u6570")
    lines.append("-" * 68)
    lines.append("  \u83cc\u68d2\u7c7b\u578b: %s" % info["name"])
    lines.append("  \u5f53\u524d\u9636\u6bb5: %s" % ("\u53d1\u83cc\u671f" if key == "inc" else "\u51fa\u83c7\u671f"))
    tlo, thi = info[key]
    hlo, hhi = info["rh"]
    lines.append("    \u6e29\u5ea6\u8981\u6c42: %d-%d\u2103" % (tlo, thi))
    lines.append("    \u76f8\u5bf9\u6e7f\u5ea6: %d-%d%%" % (hlo, hhi))
    lines.append("    \u5f00\u888b\u6216\u5212\u53e3\u65f6\u673a: %s" % info["open"])
    lines.append("    \u91c7\u6536\u5468\u671f: %s" % info["pick"])
    lines.append("")
    lines.append("  \u63d0\u9192: \u6e29\u5ea6\u662f\u7b2c\u4e00\u53d8\u91cf; \u53d1\u83cc\u671f\u6e29\u5ea6\u4e0d\u8fbe\u6807, \u540e\u9762\u6e7f\u5ea6\u600e\u4e48\u63a7\u90fd\u8865\u4e0d\u56de\u6765")
    lines.append("")
    lines.append("  \u5404\u7c7b\u578b\u53c2\u6570\u5bf9\u7167:")
    for k in ("oyster", "shiitake", "enoki", "woodear", "kingoyster", "tea_tree"):
        v = KINDS[k]
        lines.append("    %-10s \u53d1\u83cc %d-%d\u2103  \u51fa\u83c7 %d-%d\u2103  \u6e7f\u5ea6 %d-%d%%" % (
            v["name"], v["inc"][0], v["inc"][1], v["fru"][0], v["fru"][1],
            v["rh"][0], v["rh"][1]))
    lines.append("")

    lines.append("[\u4e8c] \u6e29\u5ea6\u4e0e\u6e7f\u5ea6\u6838\u5bf9")
    lines.append("-" * 68)
    ts, tadv = temp_status(temp, tlo, thi)
    hs, hadv = humidity_status(hum, hlo, hhi)
    summary["temp_status"] = ts
    summary["humidity_status"] = hs
    lines.append("  \u5b9e\u6d4b\u6e29\u5ea6: %g\u2103 -> %s" % (float(temp or 0), ts))
    lines.append("    \u5904\u7f6e: %s" % tadv)
    lines.append("  \u5b9e\u6d4b\u6e7f\u5ea6: %g%% -> %s" % (float(hum or 0), hs))
    lines.append("    \u5904\u7f6e: %s" % hadv)
    lines.append("")
    lines.append("  \u6e7f\u5ea6\u7ef4\u6301\u65b9\u5f0f: \u5730\u9762\u6d12\u6c34\u3001\u8986\u76d6\u6e7f\u5e03\u3001\u5468\u56f4\u653e\u6c34\u76c6; \u4e0d\u9760\u5929\u5929\u5f80\u83cc\u68d2\u4e0a\u55b7\u6c34")
    lines.append("  \u901a\u98ce\u4e0e\u6e7f\u5ea6\u77db\u76fe: \u7528\u65f6\u95f4\u9519\u5f00, \u767d\u5929\u901a\u98ce, \u591c\u95f4\u8986\u76d6\u4fdd\u6e7f")
    lines.append("  \u5149\u7167: \u6563\u5c04\u5149\u5373\u53ef; \u5b8c\u5168\u9ed1\u6697\u4f1a\u5bfc\u81f4\u83c7\u4f53\u82cd\u767d\u3001\u83c7\u67c4\u8fc7\u957f")
    lines.append("")

    lines.append("[\u4e09] \u6c61\u67d3\u5f81\u5146\u5224\u522b")
    lines.append("-" * 68)
    worst = None
    if not signs:
        lines.append("  \u672a\u62a5\u544a\u6c61\u67d3\u5f81\u5146, \u4ecd\u9700\u6bcf\u5929\u68c0\u67e5\u7eff\u6591\u3001\u9152\u5473\u3001\u6e17\u6db2\u3001\u9178\u8d25\u5473")
    for s in signs:
        s = s.strip()
        if not s:
            continue
        if s in SIGNS:
            desc, source, level = SIGNS[s]
            lines.append("  [%s] %s" % (level, desc))
            lines.append("    \u53ef\u80fd\u6c61\u67d3\u6e90: %s" % source)
            if level == "\u6700\u9ad8":
                lines.append("    \u5904\u7f6e: \u7acb\u5373\u79fb\u51fa, \u4e0d\u518d\u5c1d\u8bd5\u633d\u6551")
            if URGENT_ORDER[level] > URGENT_ORDER.get(worst, 0):
                worst = level
            summary["worst_urgency"] = worst
        else:
            lines.append("  [\u672a\u767b\u8bb0] %s -> \u9700\u4eba\u5de5\u6bd4\u5bf9\u6c61\u67d3\u5f81\u5146\u8868" % s)
    lines.append("")
    lines.append("  \u767d\u8272\u83cc\u4e1d\u4e0e\u767d\u8272\u9709\u83cc\u7684\u533a\u5206:")
    lines.append("    \u751f\u957f\u901f\u5ea6: \u6b63\u5e38\u83cc\u4e1d\u6309\u65e5\u63a8\u8fdb; \u767d\u8272\u9709\u83cc\u5e38\u5728 1-2 \u5929\u5185\u5927\u7247\u6269\u5c55")
    lines.append("    \u6c14\u5473: \u6b63\u5e38\u83cc\u4e1d\u65e0\u5f02\u5473; \u9709\u83cc\u53ef\u80fd\u6709\u571f\u8165\u5473\u6216\u53d1\u9175\u5473")
    lines.append("    \u5206\u5e03: \u6b63\u5e38\u83cc\u4e1d\u4ece\u63a5\u79cd\u70b9\u5747\u5300\u63a8\u8fdb; \u9709\u83cc\u5e38\u4ece\u4e00\u5904\u6269\u5c55\u6709\u660e\u786e\u8fb9\u754c")
    lines.append("    \u624b\u611f: \u6b63\u5e38\u83cc\u4e1d\u7ec6\u817b\u5747\u5300; \u9709\u83cc\u5448\u7d6e\u72b6\u6216\u7ed2\u6bdb\u72b6")
    lines.append("    \u5224\u5b9a\u539f\u5219: \u5224\u65ad\u4e0d\u786e\u5b9a\u65f6\u6309\u6c61\u67d3\u5904\u7406\u5e76\u79fb\u51fa; \u6c61\u67d3\u68d2\u7559\u5728\u539f\u5904\u4f1a\u6c61\u67d3\u6574\u6279")
    lines.append("")

    lines.append("[\u56db] \u6c61\u67d3\u7387\u4e0e\u5206\u7ea7\u5904\u7f6e")
    lines.append("-" * 68)
    rate = contamination_rate(total, contaminated)
    gname, gaction = grade_of(rate)
    summary["contam_rate"] = rate
    summary["grade"] = gname
    lines.append("  \u603b\u68d2\u6570: %g   \u6c61\u67d3\u68d2\u6570: %g" % (float(total or 0), float(contaminated or 0)))
    lines.append("  \u6c61\u67d3\u7387: %.1f%% -> %s" % (rate, gname))
    lines.append("    \u5904\u7f6e: %s" % gaction)
    lines.append("")
    lines.append("  \u5904\u7f6e\u987a\u5e8f (\u4e0d\u80fd\u8df3\u6b65):")
    for i, (name, detail) in enumerate(ACTIONS, 1):
        lines.append("    %d. %s: %s" % (i, name, detail))
    lines.append("")
    lines.append("  \u660e\u786e\u7981\u6b62: \u5bb6\u5ead\u6761\u4ef6\u4e0b\u4e0d\u4f7f\u7528\u4efb\u4f55\u6740\u83cc\u5242\u6216\u519c\u836f\u5904\u7406\u83cc\u68d2")
    lines.append("    \u83cc\u4e1d\u4e0e\u6742\u83cc\u540c\u5904\u4e00\u888b, \u836f\u5242\u4f1a\u540c\u65f6\u4f24\u5230\u83cc\u4e1d, \u4e14\u6b8b\u7559\u5f71\u54cd\u98df\u7528\u5b89\u5168")
    lines.append("    \u6c61\u67d3\u7684\u5904\u7f6e\u662f\u79fb\u51fa\u3001\u9694\u79bb\u3001\u5e9f\u5f03")
    lines.append("")

    lines.append("[\u4e94] \u91c7\u6536\u65f6\u673a")
    lines.append("-" * 68)
    p, padv = pick_ready(cap_open, days)
    summary["pick"] = p
    lines.append("  \u83cc\u76d6\u72b6\u6001: %s" % ("\u5df2\u5b8c\u5168\u644a\u5f00" if cap_open is True
                                else ("\u672a\u644a\u5f00" if cap_open is False else "\u672a\u63d0\u4f9b")))
    lines.append("    \u5224\u5b9a: %s" % p)
    lines.append("    \u8bf4\u660e: %s" % padv)
    lines.append("    \u6210\u719f\u671f\u7279\u5f81: \u83cc\u76d6\u7531\u5377\u66f2\u53d8\u4e3a\u5e73\u5c55\u4f46\u5c1a\u672a\u5b8c\u5168\u644a\u5f00, \u8fb9\u7f18\u4ecd\u5185\u5377")
    lines.append("    \u91c7\u6536\u624b\u6cd5: \u6574\u4e1b\u4ece\u57fa\u90e8\u62e7\u4e0b\u6216\u7528\u5200\u6cbf\u57fa\u90e8\u5207\u4e0b, \u4e0d\u4ece\u83c7\u4f53\u4e2d\u6bb5\u786c\u62fd")
    lines.append("    \u91c7\u6536\u5f53\u5929: \u4e0d\u55b7\u6c34, \u91c7\u540e\u5c3d\u5feb\u98df\u7528")
    lines.append("")

    lines.append("[\u516d] \u4e0d\u51fa\u83c7\u6392\u67e5\u987a\u5e8f")
    lines.append("-" * 68)
    for i, step in enumerate([
            "\u6e29\u5ea6\u662f\u5426\u5728\u51fa\u83c7\u671f\u8303\u56f4, \u5f88\u591a\u662f\u6e29\u5ea6\u592a\u9ad8",
            "\u5149\u7167\u662f\u5426\u4e3a\u96f6, \u957f\u671f\u5b8c\u5168\u9ed1\u6697\u5bfc\u81f4\u83c7\u4f53\u7578\u5f62\u6216\u4e0d\u5f62\u6210",
            "\u6e7f\u5ea6\u662f\u5426\u4e0d\u8db3, \u5c24\u5176\u82b1\u671f\u4e0e\u5e7c\u83c7\u671f",
            "\u662f\u5426\u5145\u5206\u6210\u719f\u624d\u5f00\u888b, \u83cc\u4e1d\u672a\u957f\u6ee1\u5c31\u5f00\u888b\u4f1a\u5bfc\u81f4\u4e0d\u51fa\u83c7",
            "\u662f\u5426\u5df2\u56e0\u6c61\u67d3\u5931\u53bb\u4ea7\u83c7\u80fd\u529b"], 1):
        lines.append("    %d. %s" % (i, step))
    lines.append("")
    lines.append("\u514d\u8d23: \u672c\u7ed3\u679c\u4e3a\u53c2\u6570\u6838\u5bf9\u4e0e\u6c61\u67d3\u5206\u7ea7, \u4e0d\u6784\u6210\u83cc\u79cd\u8bc4\u4ef7\u6216\u5fae\u751f\u7269\u9274\u5b9a\u7ed3\u8bba\u3002")
    lines.append("\u514d\u8d23: \u83cc\u79cd\u6765\u6e90\u4ee5\u4f9b\u79cd\u65b9\u8bf4\u660e\u548c\u5f53\u5730\u519c\u6280\u90e8\u95e8\u4e3a\u51c6; \u6c61\u67d3\u6e90\u9274\u5b9a\u4ee5\u4e13\u4e1a\u68c0\u6d4b\u7ed3\u8bba\u4e3a\u51c6\u3002")
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
    r.append(("\u7c7b\u578b\u8868 6 \u7c7b", len(KINDS) == 6))
    r.append(("\u5e73\u83c7\u53d1\u83cc 20-25", KINDS["oyster"]["inc"] == (20, 25)))
    r.append(("\u91d1\u9488\u83c7\u51fa\u83c7 8-15", KINDS["enoki"]["fru"] == (8, 15)))
    r.append(("\u6728\u8033\u53d1\u83cc 22-28", KINDS["woodear"]["inc"] == (22, 28)))
    r.append(("\u672a\u767b\u8bb0\u7c7b\u578b\u56de\u843d\u5e73\u83c7", (KINDS.get("nope") or KINDS["oyster"])["name"] == "\u5e73\u83c7\u7c7b"))
    r.append(("\u53d1\u83cc\u671f\u53d6 inc", STAGE_KEY.get("spawn") == "inc"))
    r.append(("\u51fa\u83c7\u671f\u53d6 fru", STAGE_KEY.get("fruit") == "fru"))
    r.append(("\u672a\u767b\u8bb0\u9636\u6bb5\u6309\u53d1\u83cc\u671f", STAGE_KEY.get("x", "inc") == "inc"))

    r.append(("\u6e29\u5ea6 22 \u5728\u5e73\u83c7\u53d1\u83cc\u533a\u95f4", temp_status(22, 20, 25)[0] == "\u8fbe\u6807"))
    r.append(("\u6e29\u5ea6 30 \u4e3a\u504f\u9ad8", temp_status(30, 20, 25)[0] == "\u504f\u9ad8"))
    r.append(("\u6e29\u5ea6 15 \u4e3a\u504f\u4f4e", temp_status(15, 20, 25)[0] == "\u504f\u4f4e"))
    r.append(("\u6e7f\u5ea6 90 \u5728\u533a\u95f4", humidity_status(90, 85, 95)[0] == "\u8fbe\u6807"))
    r.append(("\u6e7f\u5ea6 99 \u4e3a\u504f\u9ad8", humidity_status(99, 85, 95)[0] == "\u504f\u9ad8"))
    r.append(("\u6e7f\u5ea6 50 \u4e3a\u504f\u4f4e", humidity_status(50, 85, 95)[0] == "\u504f\u4f4e"))

    r.append(("\u6c61\u67d3\u7387 10 \u68d2 2 \u6839\u4e3a 20%", contamination_rate(10, 2) == 20.0))
    r.append(("\u6c61\u67d3\u7387 0 \u4e3a 0%", contamination_rate(10, 0) == 0.0))
    r.append(("\u603b\u68d2\u6570\u4e3a 0 \u65f6\u4e3a 0", contamination_rate(0, 5) == 0.0))
    r.append(("\u6c61\u67d3\u6570\u8d85\u603b\u6570\u88ab\u622a\u65ad", contamination_rate(5, 9) == 100.0))
    r.append(("0% \u4e3a\u65e0\u6c61\u67d3", grade_of(0.0)[0] == "\u65e0\u6c61\u67d3"))
    r.append(("3% \u4e3a\u8f7b\u5ea6", grade_of(3.0)[0] == "\u8f7b\u5ea6"))
    r.append(("10% \u4e3a\u4e2d\u5ea6", grade_of(10.0)[0] == "\u4e2d\u5ea6"))
    r.append(("25% \u4e3a\u91cd\u5ea6", grade_of(25.0)[0] == "\u91cd\u5ea6"))
    r.append(("50% \u4e3a\u91cd\u5ea6", grade_of(50.0)[0] == "\u91cd\u5ea6"))

    r.append(("\u9152\u5473\u4e3a\u6700\u9ad8\u7b49\u7ea7", SIGNS["alcohol"][2] == "\u6700\u9ad8"))
    r.append(("\u9178\u5473\u4e3a\u6700\u9ad8\u7b49\u7ea7", SIGNS["sour"][2] == "\u6700\u9ad8"))
    r.append(("\u6e17\u6db2\u4e3a\u6700\u9ad8\u7b49\u7ea7", SIGNS["ooze"][2] == "\u6700\u9ad8"))
    r.append(("\u7eff\u6591\u4e3a\u9ad8", SIGNS["green_fluffy"][2] == "\u9ad8"))
    r.append(("\u6df1\u7eff\u6591\u4e3a\u4e2d", SIGNS["green_dot"][2] == "\u4e2d"))
    r.append(("\u5f81\u5146\u8868 10 \u6761", len(SIGNS) == 10))
    r.append(("\u5904\u7f6e\u516d\u6b65", len(ACTIONS) == 6))
    r.append(("\u83cc\u76d6\u644a\u5f00\u65f6\u4e0d\u9002\u7528", pick_ready(True, 5)[0] == "\u4e0d\u9002\u7528"))
    r.append(("\u83cc\u76d6\u672a\u644a\u5f00\u65f6\u672a\u5230", pick_ready(False, 5)[0] == "\u672a\u5230"))
    r.append(("\u5f00\u888b 2 \u5929\u4e3a\u504f\u65e9", pick_ready(None, 2)[0] == "\u504f\u65e9"))
    r.append(("\u5f00\u888b 5 \u5929\u4e3a\u63a5\u8fd1", pick_ready(None, 5)[0] == "\u63a5\u8fd1"))
    r.append(("\u7d27\u6025\u7b49\u7ea7\u5e8f\u6b63\u786e", URGENT_ORDER["\u6700\u9ad8"] > URGENT_ORDER["\u9ad8"] > URGENT_ORDER["\u4e2d"]))
    r.append(("\u9152\u5473\u63d0\u793a\u4e0d\u633d\u6551", "\u4e0d\u518d\u5c1d\u8bd5\u633d\u6551" in "\u7acb\u5373\u79fb\u51fa, \u4e0d\u518d\u5c1d\u8bd5\u633d\u6551"))

    txt, s = build_report({
        "kind": "oyster", "stage": "spawn", "temp_c": 30, "humidity": 99,
        "total": 10, "contaminated": 2, "signs": ["alcohol", "green_fluffy"],
        "cap_open": True, "days_since_open": 6,
    })
    r.append(("\u6837\u4f8b\u7c7b\u578b\u4e3a\u5e73\u83c7\u7c7b", s["kind"] == "\u5e73\u83c7\u7c7b"))
    r.append(("\u6837\u4f8b\u6e29\u5ea6\u504f\u9ad8", s["temp_status"] == "\u504f\u9ad8"))
    r.append(("\u6837\u4f8b\u6e7f\u5ea6\u504f\u9ad8", s["humidity_status"] == "\u504f\u9ad8"))
    r.append(("\u6837\u4f8b\u6c61\u67d3\u7387 20%", s["contam_rate"] == 20.0))
    r.append(("\u6837\u4f8b\u5224\u4e3a\u91cd\u5ea6", s["grade"] == "\u91cd\u5ea6"))
    r.append(("\u6837\u4f8b\u6700\u9ad8\u7b49\u7ea7\u4e3a\u6700\u9ad8", s["worst_urgency"] == "\u6700\u9ad8"))
    r.append(("\u6837\u4f8b\u91c7\u6536\u4e0d\u9002\u7528", s["pick"] == "\u4e0d\u9002\u7528"))
    r.append(("\u6837\u4f8b\u4e0d\u63a8\u8350\u836f\u5242", s["pesticide_recommended"] is False))
    r.append(("\u6837\u4f8b\u6587\u672c\u542b\u7981\u6b62\u9879", "\u660e\u786e\u7981\u6b62" in txt))

    _, s2 = build_report({})
    r.append(("\u7a7a\u8f93\u5165\u4e0d\u62a5\u9519", s2["kind"] == "\u5e73\u83c7\u7c7b"))
    r.append(("\u7a7a\u8f93\u5165\u65e0\u5f81\u5146", s2["worst_urgency"] is None))
    r.append(("\u7a7a\u8f93\u5165\u6c61\u67d3\u7387\u4e3a 0", s2["contam_rate"] == 0.0))

    _, s3 = build_report({"kind": "enoki", "stage": "fruit", "temp_c": 18,
                          "humidity": 75, "signs": ["nope"]})
    r.append(("\u91d1\u9488\u83c7\u6837\u4f8b\u6b63\u786e", s3["kind"] == "\u91d1\u9488\u83c7\u7c7b"))
    r.append(("\u51fa\u83c7\u671f 18\u2103 \u504f\u9ad8", s3["temp_status"] == "\u504f\u9ad8"))
    r.append(("\u672a\u767b\u8bb0\u5f81\u5146\u4e0d\u62a5\u9519", s3["worst_urgency"] is None))

    r.append(("BOM \u8f93\u5165\u88ab\u6b63\u786e\u5265\u79bb",
               load_json(_write_bom_sample())["kind"] == "shiitake"))
    r.append(("\u5b57\u7b26\u4e32\u5f62\u5f0f\u7684\u5f81\u5146\u53ef\u89e3\u6790",
               build_report({"signs": ["sour"]})[1]["worst_urgency"] == "\u6700\u9ad8"))
    return r


def _write_bom_sample():
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "_selftest_bom_sample.json")
    with io.open(p, "w", encoding="utf-8") as f:
        f.write("\ufeff{\"kind\": \"shiitake\", \"stage\": \"spawn\"}")
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
        description="\u98df\u7528\u83cc\u83cc\u68d2\u53c2\u6570\u4e0e\u6c61\u67d3\u5206\u7ea7\u5de5\u5177")
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
