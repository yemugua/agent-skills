# -*- coding: utf-8 -*-
"""\u7f1d\u8865\u9488\u6cd5\u65b9\u6848\u6821\u9a8c\u811a\u672c\u3002

\u8bfb\u5165\u4e00\u4efd\u7f1d\u8865\u65b9\u6848\u7684 json\uff0c\u6838\u5bf9\uff1a
  1. \u5e03\u6599\u7c7b\u522b\u4e0e\u7834\u635f\u5f62\u6001\u662f\u5426\u88ab\u8bc6\u522b
  2. \u6240\u9009\u9488\u6cd5\u662f\u5426\u5728\u8be5\u7834\u635f\u5f62\u6001\u7684\u5141\u8bb8\u96c6\u5408\u5185
  3. \u662f\u5426\u547d\u4e2d\u7981\u7528\u7ec4\u5408\uff08\u9488\u7ec7\u914d\u68c9\u7ebf\u3001\u8584\u6599\u7528\u7c97\u9488\u3001\u53d7\u529b\u4f4d\u7528\u9690\u85cf\u7c7b\u9488\u6cd5\u7b49\uff09
  4. \u624b\u7f1d\u9488\u53f7\u662f\u5426\u5728\u5e03\u6599\u5141\u8bb8\u533a\u95f4
  5. \u9488\u8ddd\u3001\u7f1d\u4efd\u662f\u5426\u5728\u5141\u8bb8\u533a\u95f4
  6. \u56de\u9488\u6bd4\u4f8b\u662f\u5426\u843d\u5728\u6709\u6548\u5e26\u5185
  7. \u64cd\u4f5c\u987a\u5e8f\u662f\u5426\u8d70\u53cd\uff08\u6309\u7528\u6237\u586b\u7684\u539f\u5e8f\u53d6\u7d22\u5f15\uff0c\u4e0d\u91cd\u6392\uff09

\u7ed3\u8bba\u5206\u4e09\u6863\uff1a\u5148\u5904\u7406 / \u5f85\u786e\u8ba4 / \u53ef\u7167\u6b64\u6267\u884c\u3002
\u5224\u5b9a\u987a\u5e8f\u56fa\u5b9a\uff1a\u5148\u770b\u771f\u5b9e\u7f3a\u9677\uff0c\u518d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574\u3002

\u7528\u6cd5:
  python stitch_plan.py --selftest
  python stitch_plan.py --file plan.json
"""
import argparse
import json
import os
import sys

HEREDIR = os.path.dirname(os.path.abspath(__file__))

FABRIC = {
    "\u8584\u8f6f": ["\u771f\u4e1d", "\u96ea\u7eba", "\u4e54\u5176\u7eb1", "\u5df4\u5398\u7eb1", "\u8584\u8f6f"],
    "\u4e2d\u8584": ["\u886c\u886b\u68c9", "\u5e9c\u7ef8", "\u4eba\u9020\u68c9", "\u4e2d\u8584", "\u68c9\u5e03"],
    "\u4e2d\u539a": ["\u659c\u7eb9\u5e03", "\u725b\u6d25\u7eba", "\u706f\u82af\u7ed2", "\u4e2d\u539a"],
    "\u539a\u786c": ["\u725b\u4ed4", "\u5e06\u5e03", "\u7f8a\u6bdb\u5462", "\u539a\u786c"],
    "\u9488\u7ec7\u5e26\u5f39": ["\u9488\u7ec7", "\u6c57\u5e03", "\u7f57\u7eb9", "\u6293\u7ed2", "\u8fd0\u52a8\u9762\u6599", "\u5f39\u529b"],
}

FABRIC_LIMIT = {
    "\u8584\u8f6f": {"needle": (9, 11), "slen": (1.5, 2.0), "seam": (6, 20)},
    "\u4e2d\u8584": {"needle": (8, 9), "slen": (2.0, 2.5), "seam": (6, 20)},
    "\u4e2d\u539a": {"needle": (7, 8), "slen": (2.5, 3.0), "seam": (8, 20)},
    "\u539a\u786c": {"needle": (5, 7), "slen": (3.0, 4.0), "seam": (10, 20)},
    "\u9488\u7ec7\u5e26\u5f39": {"needle": (9, 11), "slen": (2.0, 3.0), "seam": (8, 20)},
}

DAMAGE = {
    "\u987a\u7f1d\u5d29\u7ebf": {"ok": ["\u56de\u9488\u7f1d", "\u534a\u56de\u9488\u7f1d"], "bad": ["\u5e73\u9488", "\u85cf\u9488\u7f1d", "\u7f2d\u9488\u7f1d"],
                 "alias": ["\u5d29\u7ebf", "\u8131\u7ebf"]},
    "\u76f4\u7ebf\u88c2\u53e3": {"ok": ["\u56de\u9488\u7f1d", "\u534a\u56de\u9488\u7f1d", "\u8d34\u5e03\u8865\u4e01"], "bad": ["\u7f2d\u9488\u7f1d", "\u85cf\u9488\u7f1d", "\u5e73\u9488"],
                 "alias": ["\u88c2\u5f00", "\u6495\u5f00"]},
    "\u7834\u6d1e\u7f3a\u8089": {"ok": ["\u8d34\u5e03\u8865\u4e01", "\u7ec7\u8865"], "bad": ["\u7f2d\u9488\u7f1d", "\u85cf\u9488\u7f1d", "\u56de\u9488\u7f1d"],
                 "alias": ["\u7834\u6d1e", "\u7f3a\u8089", "\u78e8\u7834"]},
    "\u6bdb\u8fb9\u8131\u6563": {"ok": ["\u9501\u8fb9\u7f1d"], "bad": ["\u7f2d\u9488\u7f1d", "\u85cf\u9488\u7f1d", "\u56de\u9488\u7f1d"],
                 "alias": ["\u6bdb\u8fb9", "\u8131\u6563", "\u8d77\u6bdb"]},
    "\u9488\u7ec7\u8131\u5708\u52fe\u4e1d": {"ok": ["\u7ec7\u8865", "\u8d34\u5e03\u8865\u4e01"], "bad": ["\u56de\u9488\u7f1d", "\u7f2d\u9488\u7f1d", "\u85cf\u9488\u7f1d", "\u5e73\u9488"],
                     "alias": ["\u8131\u5708", "\u52fe\u4e1d"]},
    "\u4e0b\u6446\u8131\u7ebf": {"ok": ["\u7f2d\u9488\u7f1d", "\u85cf\u9488\u7f1d"], "bad": ["\u56de\u9488\u7f1d"],
                 "alias": ["\u4e0b\u6446", "\u88e4\u811a"]},
}

HIDE_STITCH = ["\u7f2d\u9488\u7f1d", "\u85cf\u9488\u7f1d", "\u5e73\u9488"]
STRESS_POS = ["\u814b\u4e0b", "\u8896\u7abf", "\u88e4\u88c6", "\u8098\u90e8", "\u819d\u76d6", "\u81c0\u90e8"]
ORDER = ["\u71a8\u70eb\u5f52\u6b63", "\u758f\u7f1d\u56fa\u5b9a", "\u6b63\u5f0f\u7f1d\u5408", "\u6536\u5c3e\u71a8\u70eb"]
ORDER_ALIAS = {"\u71a8\u70eb": "\u71a8\u70eb\u5f52\u6b63", "\u71a8\u5e73": "\u71a8\u70eb\u5f52\u6b63", "\u758f\u7f1d": "\u758f\u7f1d\u56fa\u5b9a",
               "\u5047\u7f1d": "\u758f\u7f1d\u56fa\u5b9a", "\u7f1d\u5408": "\u6b63\u5f0f\u7f1d\u5408", "\u6b63\u5f0f\u7f1d": "\u6b63\u5f0f\u7f1d\u5408",
               "\u6536\u5c3e": "\u6536\u5c3e\u71a8\u70eb", "\u540e\u6574": "\u6536\u5c3e\u71a8\u70eb"}
REQUIRED = ["fabric", "damage", "position", "stitch", "thread", "needle",
            "stitch_length_mm", "seam_allowance_mm"]


def norm(s):
    """\u5f52\u4e00\u5316\uff1a\u53bb\u6389\u7a7a\u683c\u4e0e\u5168\u89d2\u7a7a\u683c\uff0c\u65b9\u4fbf\u7528\u6237\u8f93\u5165\u5e26\u7a7a\u683c\u7684\u5199\u6cd5\u3002"""
    return str(s).strip().replace(" ", "").replace("\u3000", "")


def load_plan(path):
    """\u8bfb\u53d6\u65b9\u6848\u6587\u4ef6\u3002\u7edf\u4e00\u7528 utf-8-sig\uff0c\u5e26 BOM \u7684\u6587\u4ef6\u4e5f\u80fd\u6b63\u786e\u89e3\u6790\u3002"""
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def pick_fabric(value):
    key = norm(value)
    for k, alias in FABRIC.items():
        if key == k or key in [norm(x) for x in alias]:
            return k
    return None


def pick_damage(value):
    key = norm(value)
    for k, v in DAMAGE.items():
        if key == k or key in [norm(x) for x in v["alias"]]:
            return k
    return None


def check(plan):
    bad = []
    warn = []
    miss = []
    fb = pick_fabric(plan.get("fabric", ""))
    dm = pick_damage(plan.get("damage", ""))
    if fb is None:
        miss.append("\u5e03\u6599\u7c7b\u522b\u65e0\u6cd5\u8bc6\u522b\uff0c\u586b\u7684\u662f\u300c%s\u300d\uff0c\u8bf7\u5728 %s \u4e2d\u53d6\u503c" % (
            plan.get("fabric", ""), "/".join(FABRIC.keys())))
    if dm is None:
        miss.append("\u7834\u635f\u5f62\u6001\u65e0\u6cd5\u8bc6\u522b\uff0c\u586b\u7684\u662f\u300c%s\u300d\uff0c\u8bf7\u5728 %s \u4e2d\u53d6\u503c" % (
            plan.get("damage", ""), "/".join(DAMAGE.keys())))
    for k in REQUIRED:
        if k not in plan or plan[k] in ("", None):
            miss.append("\u7f3a\u5c11\u5fc5\u586b\u5b57\u6bb5 %s" % k)

    st = norm(plan.get("stitch", ""))
    th = norm(plan.get("thread", ""))
    pos = norm(plan.get("position", ""))

    # 1. \u9488\u6cd5\u4e0e\u7834\u635f\u5f62\u6001\u662f\u5426\u5339\u914d
    if dm is not None and st:
        if st in [norm(x) for x in DAMAGE[dm]["bad"]]:
            bad.append("\u7834\u635f\u5f62\u6001\u300c%s\u300d\u4e0b\u7981\u7528\u9488\u6cd5\u300c%s\u300d\uff1a\u8fd9\u7c7b\u7834\u635f\u9760\u8be5\u9488\u6cd5\u65e0\u6cd5\u627f\u8f7d\uff0c"
                       "\u6b63\u786e\u505a\u6cd5\u662f\u6539\u7528\u300c%s\u300d" % (dm, st, DAMAGE[dm]["ok"][0]))
        elif st not in [norm(x) for x in DAMAGE[dm]["ok"]]:
            warn.append("\u9488\u6cd5\u300c%s\u300d\u4e0d\u5728\u300c%s\u300d\u7684\u63a8\u8350\u5217\u8868\u5185\uff0c\u63a8\u8350\u4e3a %s" % (
                st, dm, "/".join(DAMAGE[dm]["ok"])))

    # 2. \u7981\u7528\u7ec4\u5408
    if fb == "\u9488\u7ec7\u5e26\u5f39" and any(t in th or th in t for t in ["\u68c9\u7ebf"]):
        bad.append("\u9488\u7ec7\u6216\u5f39\u529b\u5e03\u6599\u914d\u68c9\u7ebf\uff1a\u68c9\u7ebf\u51e0\u4e4e\u65e0\u5f39\uff0c\u4e00\u6491\u5c31\u5d29\uff0c\u4e14\u6d17\u540e\u7f29\u7387\u4e0d\u4e00\u81f4\u5bfc\u81f4\u62bd\u76b1\uff1b"
                   "\u5e94\u6539\u7528\u6da4\u7eb6\u7ebf\u6216\u5f39\u529b\u7ebf")
    if fb == "\u9488\u7ec7\u5e26\u5f39" and norm(plan.get("needle_type", "")) not in ("", "\u7403\u5934\u9488"):
        bad.append("\u9488\u7ec7\u5e03\u6599\u7528\u4e86\u975e\u7403\u5934\u9488\uff1a\u666e\u901a\u5c16\u5934\u9488\u4f1a\u624e\u65ad\u7ebf\u5708\uff0c\u6d1e\u53e3\u6cbf\u7ebf\u8def\u7ee7\u7eed\u6269\u5927")
    if fb == "\u8584\u8f6f":
        try:
            nd = int(plan.get("needle"))
            if nd <= 7:
                bad.append("\u8584\u8f6f\u9762\u6599\u7528 %d \u53f7\u9488\u8fc7\u7c97\uff1a\u4f1a\u7559\u4e0b\u6c38\u4e45\u9488\u5b54\uff0c\u5e94\u6539\u7528 9 \u5230 11 \u53f7" % nd)
        except (TypeError, ValueError):
            pass
    if any(p in pos for p in STRESS_POS) and st in HIDE_STITCH:
        bad.append("\u53d7\u529b\u90e8\u4f4d\u300c%s\u300d\u7528\u4e86\u9690\u85cf\u7c7b\u9488\u6cd5\u300c%s\u300d\uff1a\u5403\u5e03\u6d45\u3001\u7ebf\u8ff9\u677e\uff0c\u7a7f\u4e0a\u5c31\u4f1a\u88ab\u62c9\u5f00\uff1b"
                   "\u6539\u7528\u56de\u9488\u7f1d\uff0c\u5fc5\u8981\u5904\u52a0\u5185\u4fa7\u8d34\u5e03" % (pos, st))

    # 3. \u9488\u53f7\u4e0e\u5c3a\u5bf8
    if fb is not None:
        lim = FABRIC_LIMIT[fb]
        try:
            nd = int(plan.get("needle"))
            if not (lim["needle"][0] <= nd <= lim["needle"][1]):
                bad.append("\u624b\u7f1d\u9488\u53f7 %d \u8d85\u51fa\u300c%s\u300d\u5141\u8bb8\u7684 %d \u5230 %d \u53f7\u533a\u95f4" % (
                    nd, fb, lim["needle"][0], lim["needle"][1]))
        except (TypeError, ValueError):
            pass
        try:
            sl = float(plan.get("stitch_length_mm"))
            if sl < lim["slen"][0]:
                bad.append("\u9488\u8ddd %.1f \u6beb\u7c73\u4f4e\u4e8e\u300c%s\u300d\u4e0b\u9650 %.1f \u6beb\u7c73\uff1a\u8fc7\u5bc6\u4f1a\u628a\u5e03\u624e\u6210\u4e00\u6392\u9488\u5b54\uff0c"
                           "\u7b49\u4e8e\u5f00\u4e86\u6761\u865a\u7ebf" % (sl, fb, lim["slen"][0]))
            elif sl > lim["slen"][1]:
                bad.append("\u9488\u8ddd %.1f \u6beb\u7c73\u8d85\u51fa\u300c%s\u300d\u4e0a\u9650 %.1f \u6beb\u7c73\uff1a\u8fc7\u5927\u5219\u8fde\u7ed3\u4e0d\u591f\uff0c"
                           "\u6d17\u4e24\u6b21\u5c31\u8c41\u53e3" % (sl, fb, lim["slen"][1]))
        except (TypeError, ValueError):
            pass
        try:
            sa = float(plan.get("seam_allowance_mm"))
            if sa < lim["seam"][0]:
                bad.append("\u7f1d\u4efd %.1f \u6beb\u7c73\u4f4e\u4e8e\u300c%s\u300d\u4e0b\u9650 %d \u6beb\u7c73\uff1a\u7f1d\u7ebf\u6240\u5728\u7684\u5e03\u8fb9\u672c\u6765\u5c31\u7a00\uff0c"
                           "\u4e00\u53d7\u529b\u5c31\u4ece\u7ebf\u90a3\u91cc\u6495\u5f00" % (sa, fb, lim["seam"][0]))
            elif sa > lim["seam"][1]:
                warn.append("\u7f1d\u4efd %.1f \u6beb\u7c73\u8d85\u8fc7 %d \u6beb\u7c73\u4e14\u672a\u4fee\u526a\uff1a\u4e0d\u5f71\u54cd\u7262\u5ea6\uff0c\u4f46\u7a7f\u7740\u4f1a\u784c" % (
                    sa, lim["seam"][1]))
        except (TypeError, ValueError):
            pass

    # 4. \u56de\u9488\u6bd4\u4f8b
    ratio = plan.get("backstitch_ratio")
    if ratio is not None:
        try:
            r = float(ratio)
            if r < 0.3:
                bad.append("\u56de\u9488\u6bd4\u4f8b %.2f \u4f4e\u4e8e 0.3\uff1a\u6b63\u9762\u7ebf\u8ff9\u53d8\u6210\u65ad\u7eed\u865a\u7ebf\uff0c"
                           "\u5f3a\u5ea6\u6389\u5230\u534a\u56de\u9488\u4ee5\u4e0b" % r)
            elif r > 0.7:
                warn.append("\u56de\u9488\u6bd4\u4f8b %.2f \u9ad8\u4e8e 0.7\uff1a\u504f\u6d6a\u8d39\u7ebf\u4e14\u80cc\u9762\u504f\u539a\uff0c\u4e0d\u5f71\u54cd\u7262\u5ea6" % r)
        except (TypeError, ValueError):
            warn.append("\u56de\u9488\u6bd4\u4f8b\u65e0\u6cd5\u89e3\u6790\u4e3a\u6570\u503c")

    # 5. \u64cd\u4f5c\u987a\u5e8f\uff1a\u6309\u7528\u6237\u586b\u7684\u539f\u5e8f\u53d6\u7d22\u5f15\uff0c\u7edd\u4e0d\u6309\u6b63\u786e\u987a\u5e8f\u91cd\u6392
    steps = plan.get("steps") or []
    picked = []
    for s in steps:
        n = norm(s)
        if n not in ORDER:
            for k, v in ORDER_ALIAS.items():
                if k in n:
                    n = v
                    break
        if n in ORDER:
            picked.append(n)
    if len(picked) < 4:
        miss.append("\u64cd\u4f5c\u987a\u5e8f\u53ea\u8bc6\u522b\u5230 %d \u6b65\uff0c\u672a\u51d1\u9f50\u56db\u6b65\uff0c\u65e0\u6cd5\u5224\u65ad\u987a\u5e8f\u662f\u5426\u8d70\u53cd" % len(picked))
    else:
        seq = [ORDER.index(x) for x in picked]
        if seq != sorted(seq):
            bad.append("\u64cd\u4f5c\u987a\u5e8f\u8d70\u53cd\uff1a\u5b9e\u9645\u4e3a %s\uff0c\u6b63\u786e\u5e94\u4e3a %s\uff1b"
                       "\u6b63\u5f0f\u7f1d\u5408\u6392\u5728\u758f\u7f1d\u56fa\u5b9a\u4e4b\u524d\u4f1a\u76f4\u63a5\u5bfc\u81f4\u4e0a\u4e0b\u7247\u8dd1\u4f4d" % (
                           " \u2192 ".join(picked), " \u2192 ".join(ORDER)))

    if bad:
        verdict = "\u5148\u5904\u7406"
    elif miss:
        verdict = "\u5f85\u786e\u8ba4"
    else:
        verdict = "\u53ef\u7167\u6b64\u6267\u884c"
    return {"verdict": verdict, "bad": bad, "warn": warn, "miss": miss}


def render(plan, res):
    lines = []
    lines.append("# \u7f1d\u8865\u9488\u6cd5\u65b9\u6848\u6838\u5bf9\u7ed3\u679c")
    lines.append("")
    lines.append("\u5e03\u6599\uff1a%s \uff5c \u7834\u635f\u5f62\u6001\uff1a%s \uff5c \u90e8\u4f4d\uff1a%s \uff5c \u9488\u6cd5\uff1a%s" % (
        plan.get("fabric", "-"), plan.get("damage", "-"),
        plan.get("position", "-"), plan.get("stitch", "-")))
    lines.append("")
    lines.append("\u7ed3\u8bba\uff1a**%s**" % res["verdict"])
    lines.append("")
    if res["bad"]:
        lines.append("## \u4e0d\u5408\u683c\u9879\uff08\u5fc5\u987b\u6539\u65b9\u6848\u540e\u518d\u843d\u9488\uff09")
        for x in res["bad"]:
            lines.append("- %s" % x)
        lines.append("")
    if res["miss"]:
        lines.append("## \u5f85\u786e\u8ba4\u9879\uff08\u4fe1\u606f\u4e0d\u8db3\uff09")
        for x in res["miss"]:
            lines.append("- %s" % x)
        lines.append("")
    if res["warn"]:
        lines.append("## \u63d0\u793a\u9879")
        for x in res["warn"]:
            lines.append("- %s" % x)
        lines.append("")
    if not res["bad"] and not res["miss"]:
        lines.append("\u672a\u53d1\u73b0\u7981\u7528\u7ec4\u5408\uff0c\u9488\u53f7\u3001\u9488\u8ddd\u3001\u7f1d\u4efd\u5747\u5728\u300c%s\u300d\u5141\u8bb8\u533a\u95f4\u5185\uff0c\u987a\u5e8f\u6b63\u786e\uff1b"
                     "\u6309\u89c4\u5219\u6587\u4ef6\u7684\u4eba\u5de5\u786e\u8ba4\u6e05\u5355\u9010\u9879\u505a\u5373\u53ef\u3002" % plan.get("fabric", ""))
    lines.append("")
    lines.append("\u6ce8\uff1a\u672c\u7ed3\u679c\u4e3a\u751f\u6d3b\u7f1d\u8865\u65b9\u6848\u6838\u5bf9\uff0c\u4e0d\u6784\u6210\u670d\u88c5\u5de5\u827a\u4e13\u4e1a\u610f\u89c1\u3002")
    return "\n".join(lines) + "\n"


def write_out(text, name="_last_result.txt"):
    p = os.path.join(HEREDIR, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


def selftest():
    ok = 0
    fail = []

    def check_case(name, cond, extra=""):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fail.append(name + (" -> " + extra if extra else ""))

    base = {
        "fabric": "\u68c9\u5e03", "damage": "\u5d29\u7ebf", "position": "\u4e0b\u6446", "stitch": "\u56de\u9488\u7f1d",
        "thread": "\u6da4\u7eb6\u7ebf", "needle": 8, "stitch_length_mm": 2.2,
        "seam_allowance_mm": 10, "backstitch_ratio": 0.5,
        "steps": ["\u71a8\u5e73\u9762\u6599", "\u758f\u7f1d\u56fa\u5b9a", "\u6b63\u5f0f\u7f1d\u5408", "\u6536\u5c3e\u71a8\u70eb"],
    }

    # 1 \u6b63\u4f8b\uff1a\u5b8c\u6574\u4e14\u6b63\u786e
    r = check(dict(base))
    check_case("\u6b63\u4f8b\u5e94\u5224\u53ef\u7167\u6b64\u6267\u884c", r["verdict"] == "\u53ef\u7167\u6b64\u6267\u884c", str(r))

    # 2 \u53cd\u4f8b\uff1a\u9488\u7ec7\u914d\u68c9\u7ebf
    bad1 = dict(base, fabric="\u9488\u7ec7", thread="\u68c9\u7ebf")
    r = check(bad1)
    check_case("\u53cd\u4f8b-\u9488\u7ec7\u914d\u68c9\u7ebf\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))
    check_case("\u53cd\u4f8b-\u9488\u7ec7\u914d\u68c9\u7ebf\u5e94\u5e26\u7981\u7528\u539f\u56e0",
               any("\u68c9\u7ebf" in x and "\u65e0\u5f39" in x for x in r["bad"]))

    # 3 \u53cd\u4f8b\uff1a\u53d7\u529b\u90e8\u4f4d\u7528\u9690\u85cf\u7c7b\u9488\u6cd5
    bad2 = dict(base, position="\u814b\u4e0b", stitch="\u85cf\u9488\u7f1d")
    r = check(bad2)
    check_case("\u53cd\u4f8b-\u814b\u4e0b\u7528\u85cf\u9488\u7f1d\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 4 \u53cd\u4f8b\uff1a\u8584\u8f6f\u9762\u6599\u7528\u7c97\u9488
    bad3 = dict(base, fabric="\u771f\u4e1d", needle=5, stitch_length_mm=1.8)
    r = check(bad3)
    check_case("\u53cd\u4f8b-\u771f\u4e1d\u75285\u53f7\u9488\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 5 \u53cd\u4f8b\uff1a\u7f1d\u4efd\u8fc7\u5c0f
    bad4 = dict(base, seam_allowance_mm=3)
    r = check(bad4)
    check_case("\u53cd\u4f8b-\u7f1d\u4efd3\u6beb\u7c73\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 6 \u53cd\u4f8b\uff1a\u987a\u5e8f\u8d70\u53cd\uff08\u5148\u7f1d\u5408\u540e\u758f\u7f1d\uff09
    bad5 = dict(base, steps=["\u71a8\u5e73\u9762\u6599", "\u6b63\u5f0f\u7f1d\u5408", "\u758f\u7f1d\u56fa\u5b9a", "\u6536\u5c3e\u71a8\u70eb"])
    r = check(bad5)
    check_case("\u53cd\u4f8b-\u987a\u5e8f\u8d70\u53cd\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))
    check_case("\u53cd\u4f8b-\u987a\u5e8f\u8d70\u53cd\u5e94\u70b9\u540d\u758f\u7f1d", any("\u758f\u7f1d" in x for x in r["bad"]))

    # 7 \u53cd\u4f8b\uff1a\u56de\u9488\u6bd4\u4f8b\u8fc7\u4f4e
    bad6 = dict(base, backstitch_ratio=0.1)
    r = check(bad6)
    check_case("\u53cd\u4f8b-\u56de\u9488\u6bd4\u4f8b0.1\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 8 \u53cd\u4f8b\uff1a\u7834\u6d1e\u7981\u7528\u7684\u9690\u85cf\u7c7b\u9488\u6cd5
    bad7 = dict(base, damage="\u7834\u6d1e", stitch="\u7f2d\u9488\u7f1d")
    r = check(bad7)
    check_case("\u53cd\u4f8b-\u7834\u6d1e\u7528\u7f2d\u9488\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 9 \u7f3a\u9879
    incom = dict(base)
    del incom["needle"]
    r = check(incom)
    check_case("\u7f3a\u9879\u5e94\u5224\u5f85\u786e\u8ba4", r["verdict"] == "\u5f85\u786e\u8ba4", str(r))

    # 10 \u5224\u5b9a\u987a\u5e8f\uff1a\u65e2\u6709\u7f3a\u9879\u53c8\u6709\u771f\u5b9e\u7f3a\u9677\u65f6\uff0c\u5fc5\u987b\u5148\u5904\u7406
    both = dict(base, fabric="\u9488\u7ec7", thread="\u68c9\u7ebf")
    del both["needle"]
    r = check(both)
    check_case("\u7f3a\u9677\u4f18\u5148\u4e8e\u7f3a\u9879", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 11 UTF-8 BOM \u8f93\u5165\u5fc5\u987b\u80fd\u88ab\u6b63\u786e\u5904\u7406
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "plan.json")
        with open(p, "w", encoding="utf-8-sig") as f:
            json.dump(dict(base), f, ensure_ascii=False)
        with open(p, "rb") as f:
            head = f.read(3)
        check_case("\u6837\u4f8b\u6587\u4ef6\u786e\u5b9e\u5e26BOM", head == b"\xef\xbb\xbf")
        r = check(load_plan(p))
        check_case("\u5e26BOM\u6587\u4ef6\u5e94\u6b63\u5e38\u89e3\u6790\u5e76\u5224\u53ef\u7167\u6b64\u6267\u884c", r["verdict"] == "\u53ef\u7167\u6b64\u6267\u884c", str(r))

        # 12 BOM + \u53cd\u4f8b\uff1a\u5e26 BOM \u7684\u53cd\u4f8b\u4ecd\u5fc5\u987b\u5224\u4e0d\u5408\u683c
        p2 = os.path.join(td, "bad.json")
        with open(p2, "w", encoding="utf-8-sig") as f:
            json.dump(dict(bad5), f, ensure_ascii=False)
        r = check(load_plan(p2))
        check_case("\u5e26BOM\u53cd\u4f8b\u4ecd\u5224\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 13 \u6392\u5e8f\u65b9\u5411\u9501\u5b9a\uff1a\u6b63\u5e8f\u7d22\u5f15\u5fc5\u987b\u7b49\u4e8e\u5176\u6392\u5e8f\u7ed3\u679c
    seq = [ORDER.index(x) for x in ORDER]
    check_case("\u6b63\u5e8f\u7d22\u5f15\u5e94\u7b49\u4e8e\u5176\u6392\u5e8f\u7ed3\u679c", seq == sorted(seq) and seq == [0, 1, 2, 3])

    lines = ["SELFTEST OK (%d passed, 0 failed)" % ok]
    if fail:
        lines = ["SELFTEST FAILED (%d passed, %d failed)" % (ok, len(fail))]
        lines += ["- " + x for x in fail]
    write_out("\n".join(lines) + "\n", "_selftest_result.txt")
    print("\n".join(lines))
    return 0 if not fail else 1


def main():
    ap = argparse.ArgumentParser(description="\u7f1d\u8865\u9488\u6cd5\u65b9\u6848\u6821\u9a8c")
    ap.add_argument("--file", help="\u65b9\u6848 json \u6587\u4ef6\u8def\u5f84")
    ap.add_argument("--selftest", action="store_true", help="\u8fd0\u884c\u81ea\u68c0")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.file:
        ap.print_help()
        return 2
    plan = load_plan(a.file)
    res = check(plan)
    p = write_out(render(plan, res))
    print("\u7ed3\u679c\u5df2\u5199\u5165: %s" % p)
    print("\u7ed3\u8bba: %s" % res["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

