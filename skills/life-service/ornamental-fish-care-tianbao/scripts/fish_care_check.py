# -*- coding: utf-8 -*-
"""\u89c2\u8d4f\u9c7c\u6c34\u8d28\u4e0e\u5582\u517b\u7ba1\u7406\u6821\u9a8c\u811a\u672c\u3002

\u8bfb\u5165\u4e00\u4efd\u9c7c\u7f38\u72b6\u6001\u7684 json\uff0c\u6838\u5bf9\uff1a
  1. \u6c2e\u4ee3\u8c22\u4e09\u9879\u6307\u6807\u662f\u5426\u843d\u5165\u5371\u9669\u533a\u95f4
  2. \u9178\u78b1\u5ea6\u662f\u5426\u5728\u6240\u9009\u9c7c\u79cd\u7684\u9002\u751f\u533a\u95f4\u5185
  3. \u6c34\u6e29\u4e0e\u4e8c\u5341\u56db\u5c0f\u65f6\u6e29\u5dee\u662f\u5426\u7b26\u5408\u8981\u6c42
  4. \u5bc6\u5ea6\u662f\u5426\u8d85\u8fc7 fish_type \u5bf9\u5e94\u7684\u627f\u8f7d\u4e0a\u9650
  5. \u5355\u6b21\u6362\u6c34\u6bd4\u4f8b\u4e0e\u6295\u5582\u6b21\u6570\u662f\u5426\u7b26\u5408\u53e3\u5f84
  6. \u662f\u5426\u4f7f\u7528\u672a\u5904\u7406\u7684\u81ea\u6765\u6c34\u3001\u517b\u6c34\u5929\u6570\u662f\u5426\u8db3\u591f
  7. \u8fc7\u6ee4\u505c\u8f6c\u65f6\u957f\u662f\u5426\u8d85\u8fc7\u5bb9\u5fcd\u7ebf
  8. \u65b0\u9c7c\u5165\u7f38\u7684\u8fc7\u6e29\u3001\u8fc7\u6c34\u987a\u5e8f\u662f\u5426\u8d70\u5bf9\uff08\u6309\u586b\u7684\u539f\u5e8f\u53d6\u7d22\u5f15\uff09

\u7ed3\u8bba\u5206\u4e09\u6863\uff1a\u5148\u5904\u7406 / \u5f85\u786e\u8ba4 / \u53ef\u7167\u6b64\u6267\u884c\u3002
\u5224\u5b9a\u987a\u5e8f\u56fa\u5b9a\uff1a\u5148\u770b\u771f\u5b9e\u7f3a\u9677\uff0c\u518d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574\u3002

\u7528\u6cd5:
  python fish_care_check.py --selftest
  python fish_care_check.py --file tank.json
"""
import argparse
import json
import os
import sys

HEREDIR = os.path.dirname(os.path.abspath(__file__))

FISH_NEED = {"\u5c0f\u578b\u70ed\u5e26\u9c7c": 1.0, "\u4e2d\u578b\u70ed\u5e26\u9c7c": 2.0, "\u91d1\u9c7c": 3.0, "\u9526\u9ca4": 5.0}
FISH_ALIAS = {"\u70ed\u5e26\u9c7c": "\u5c0f\u578b\u70ed\u5e26\u9c7c", "\u706f\u79d1\u9c7c": "\u5c0f\u578b\u70ed\u5e26\u9c7c", "\u5b54\u96c0\u9c7c": "\u5c0f\u578b\u70ed\u5e26\u9c7c",
              "\u91d1\u9c7c": "\u91d1\u9c7c"}
PH_RANGE = {
    "\u5c0f\u578b\u70ed\u5e26\u9c7c": (6.0, 7.2),
    "\u4e2d\u578b\u70ed\u5e26\u9c7c": (6.2, 7.5),
    "\u91d1\u9c7c": (7.0, 8.0),
    "\u9526\u9ca4": (7.0, 8.5),
}
TEMP_RANGE = {
    "\u5c0f\u578b\u70ed\u5e26\u9c7c": (24, 28),
    "\u4e2d\u578b\u70ed\u5e26\u9c7c": (24, 28),
    "\u91d1\u9c7c": (18, 24),
    "\u9526\u9ca4": (15, 25),
}
CYCLE_MIN = {"\u6210\u719f\u6ee4\u6750": 7, "\u785d\u5316\u83cc\u5236\u5242": 7, "\u65e0": 21}
ORDER = ["\u8fde\u888b\u8fc7\u6e29", "\u5206\u6279\u8fc7\u6c34", "\u635e\u9c7c\u5165\u7f38", "\u9759\u517b\u89c2\u5bdf"]
ORDER_ALIAS = {"\u8fc7\u6e29": "\u8fde\u888b\u8fc7\u6e29", "\u6ce1\u888b": "\u8fde\u888b\u8fc7\u6e29", "\u6ce1\u7f38": "\u8fde\u888b\u8fc7\u6e29",
               "\u8fde\u888b": "\u8fde\u888b\u8fc7\u6e29", "\u8fc7\u6c34": "\u5206\u6279\u8fc7\u6c34",
               "\u5151\u6c34": "\u5206\u6279\u8fc7\u6c34", "\u5165\u7f38": "\u635e\u9c7c\u5165\u7f38", "\u653e\u9c7c": "\u635e\u9c7c\u5165\u7f38",
               "\u89c2\u5bdf": "\u9759\u517b\u89c2\u5bdf", "\u9759\u517b": "\u9759\u517b\u89c2\u5bdf"}
REQUIRED = ["tank_liters", "fish_cm_total", "fish_type", "cycle_days"]


def norm(s):
    return str(s).strip().replace(" ", "").replace("\u3000", "")


def load_plan(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def canon_type(value):
    n = norm(value)
    if n in FISH_NEED:
        return n
    return FISH_ALIAS.get(n)


def check(plan):
    bad = []
    warn = []
    miss = []

    for k in REQUIRED:
        if k not in plan or plan[k] in ("", None):
            miss.append("\u7f3a\u5c11\u5fc5\u586b\u5b57\u6bb5 %s" % k)

    ftype = canon_type(plan.get("fish_type", ""))
    if ftype is None:
        miss.append("\u9c7c\u79cd\u7c7b\u522b\u300c%s\u300d\u65e0\u6cd5\u8bc6\u522b\uff0c\u5e94\u5728 %s \u53d6\u503c" % (
            plan.get("fish_type", ""), "/".join(FISH_NEED.keys())))

    # 1 \u4e09\u9879\u542b\u6c2e\u6307\u6807
    if all(plan.get(k) is None for k in ("ammonia", "nitrite", "nitrate")):
        miss.append("\u4e09\u9879\u542b\u6c2e\u6307\u6807\u4e00\u9879\u90fd\u6ca1\u63d0\u4f9b\uff1a\u6ca1\u6709\u5b9e\u6d4b\u503c\u5c31\u65e0\u6cd5\u5224\u65ad\u6c34\u8d28\uff0c"                "\u8bf7\u5148\u5b8c\u6210\u4e00\u6b21\u57fa\u7840\u6d4b\u8bd5\u518d\u6838\u5bf9")
    for key, danger, warn_at, label, why in (
            ("ammonia", 0.25, 0.02, "\u6c28\u6c2e",
             "\u6c28\u6c2e\u76f4\u63a5\u635f\u4f24\u9cc3\u7ec4\u7ec7\uff0c\u7b49\u6307\u6807\u51fa\u73b0\u884c\u4e3a\u5f02\u5e38\u65f6\u635f\u4f24\u5f80\u5f80\u5df2\u7ecf\u53d1\u751f"),
            ("nitrite", 0.25, 0.05, "\u4e9a\u785d\u9178\u76d0",
             "\u4e9a\u785d\u9178\u76d0\u5f71\u54cd\u8840\u6db2\u643a\u6c27\u80fd\u529b\uff0c\u770b\u4e0d\u89c1\u4f46\u5371\u5bb3\u5927"),
            ("nitrate", 40.0, 20.0, "\u785d\u9178\u76d0",
             "\u785d\u9178\u76d0\u957f\u671f\u504f\u9ad8\u4f1a\u6291\u5236\u751f\u957f\u4e0e\u62b5\u6297\u529b")):
        if plan.get(key) is None:
            continue
        try:
            v = float(plan.get(key))
        except (TypeError, ValueError):
            miss.append("%s \u65e0\u6cd5\u89e3\u6790\u4e3a\u6570\u503c" % label)
            continue
        if v > danger:
            bad.append("%s %.2f \u6beb\u514b\u6bcf\u5347\u5df2\u8fdb\u5371\u9669\u533a\u95f4\uff08\u8d85\u8fc7 %.2f\uff09\uff1a%s\uff1b"
                       "\u5e94\u7acb\u5373\u505c\u5582\u5e76\u5b89\u6392\u90e8\u5206\u6362\u6c34\u3001\u68c0\u67e5\u8fc7\u6ee4\u4e0e\u5bc6\u5ea6" % (
                           label, v, danger, why))
        elif v > warn_at:
            warn.append("%s %.2f \u6beb\u514b\u6bcf\u5347\u5904\u4e8e\u8b66\u6212\u533a\u95f4\uff08\u8d85\u8fc7 %.2f\uff09\uff1a"
                        "\u5c1a\u672a\u5230\u5371\u9669\u5730\u6b65\uff0c\u4f46\u5e94\u63d0\u524d\u5b89\u6392\u6362\u6c34" % (label, v, warn_at))

    # 2 \u9178\u78b1\u5ea6
    if ftype is not None and plan.get("ph") is not None:
        try:
            ph = float(plan.get("ph"))
        except (TypeError, ValueError):
            miss.append("\u9178\u78b1\u5ea6\u65e0\u6cd5\u89e3\u6790\u4e3a\u6570\u503c")
            ph = None
        if ph is not None:
            lo, hi = PH_RANGE[ftype]
            if ph < lo or ph > hi:
                bad.append("\u9178\u78b1\u5ea6 %.1f \u4e0d\u5728\u300c%s\u300d\u9002\u751f\u533a\u95f4 %.1f \u5230 %.1f \u5185\uff1a"
                           "\u6c34\u8d28\u504f\u79bb\u4f1a\u8ba9\u9c7c\u957f\u671f\u5904\u4e8e\u5e94\u6fc0\u72b6\u6001\uff1b"
                           "\u6ce8\u610f\u7a33\u5b9a\u6027\u6bd4\u7cbe\u786e\u6570\u503c\u66f4\u91cd\u8981" % (ph, ftype, lo, hi))

    # 3 \u6c34\u6e29
    if ftype is not None:
        try:
            tc = float(plan.get("temp_c"))
            lo, hi = TEMP_RANGE[ftype]
            if tc < lo or tc > hi:
                bad.append("\u6c34\u6e29 %.1f \u6444\u6c0f\u5ea6\u4e0d\u5728\u300c%s\u300d\u9002\u7528\u533a\u95f4 %d \u5230 %d \u5185\uff1a"
                           "\u504f\u79bb\u4f1a\u76f4\u63a5\u5f71\u54cd\u4ee3\u8c22\u4e0e\u514d\u75ab" % (tc, ftype, lo, hi))
        except (TypeError, ValueError):
            pass
    try:
        d = abs(float(plan.get("temp_change_24h")))
        if d > 2.0:
            bad.append("\u4e8c\u5341\u56db\u5c0f\u65f6\u6c34\u6e29\u53d8\u5316 %.1f \u6444\u6c0f\u5ea6\u8d85\u8fc7 2 \u6444\u6c0f\u5ea6\uff1a"
                       "\u6c34\u6e29\u7a81\u53d8\u6bd4\u504f\u4f4e\u504f\u9ad8\u672c\u8eab\u5371\u5bb3\u66f4\u5927\uff0c\u6362\u6c34\u65f6\u7684\u65b0\u6c34\u4e5f\u8981\u63a7\u5236\u5728 2 \u6444\u6c0f\u5ea6\u5185" % d)
    except (TypeError, ValueError):
        pass

    # 4 \u5bc6\u5ea6
    if ftype is not None:
        try:
            liters = float(plan.get("tank_liters"))
            cm = float(plan.get("fish_cm_total"))
            limit = liters / FISH_NEED[ftype]
            if cm > limit:
                bad.append("\u5bc6\u5ea6\u8d85\u6807\uff1a%.0f \u5347\u6c34\u517b\u300c%s\u300d\uff0c\u4f53\u957f\u4e0a\u9650\u7ea6 %.0f \u5398\u7c73\uff0c"
                           "\u5f53\u524d %.0f \u5398\u7c73\uff08\u6bcf\u5398\u7c73\u9700 %.0f \u5347\uff09\uff1a"
                           "\u9700\u51cf\u9c7c\u3001\u6362\u5927\u7f38\u6216\u63d0\u9ad8\u6362\u6c34\u9891\u6b21\u4e09\u9009\u4e00" % (
                               liters, ftype, limit, cm, FISH_NEED[ftype]))
        except (TypeError, ValueError):
            pass

    # 5 \u6362\u6c34\u6bd4\u4f8b
    try:
        wc = float(plan.get("water_change_percent"))
        if wc > 50:
            bad.append("\u5355\u6b21\u6362\u6c34 %.0f \u8d85\u8fc7 50 \u4e0a\u9650\uff1a"
                       "\u8fd9\u662f\u6700\u5e38\u89c1\u7684\u64cd\u4f5c\u9519\u8bef\uff0c\u6c34\u8d28\u4e0e\u6e29\u5ea6\u53cc\u91cd\u7a81\u53d8\u4f1a\u8ba9\u4f53\u8d28\u5dee\u7684\u9c7c\u5f53\u573a\u51fa\u4e8b\uff1b"
                       "\u5e38\u89c4\u5e94\u4e3a 20 \u5230 30\uff0c\u7279\u6b8a\u60c5\u51b5\u6700\u591a 50 \u4e14\u5e94\u5206\u4e24\u6b21\u8fdb\u884c" % wc)
        elif wc < 0:
            bad.append("\u6362\u6c34\u6bd4\u4f8b\u4e3a\u8d1f\u6570\uff0c\u6570\u636e\u65e0\u6548")
    except (TypeError, ValueError):
        pass

    if plan.get("dechlorinated") is False:
        bad.append("\u65b0\u6c34\u672a\u7ecf\u9664\u6c2f\u5904\u7406\uff1a\u81ea\u6765\u6c34\u4e2d\u7684\u4f59\u6c2f\u4f1a\u635f\u4f24\u9cc3\u7ec4\u7ec7\uff0c"
                   "\u540c\u65f6\u6740\u706d\u6ee4\u6750\u4e2d\u7684\u785d\u5316\u83cc\uff1b\u5e94\u56f0\u6c34\u3001\u66dd\u6c14\u6216\u4f7f\u7528\u9664\u6c2f\u5242")

    # 6 \u517b\u6c34\u5468\u671f
    seed = norm(plan.get("cycle_seed", "\u65e0"))
    min_day = CYCLE_MIN.get(seed, CYCLE_MIN["\u65e0"])
    try:
        cd = int(plan.get("cycle_days"))
        if cd < min_day:
            bad.append("\u5f00\u7f38\u517b\u6c34 %d \u5929\u5c11\u4e8e\u300c%s\u300d\u8def\u5f84\u6240\u9700\u7684 %d \u5929\uff1a"
                       "\u517b\u6c34\u6ca1\u5b8c\u6210\u5c31\u4e0b\u9c7c\uff0c\u7b49\u540c\u4e8e\u8ba9\u9c7c\u751f\u6d3b\u5728\u81ea\u5df1\u7684\u6392\u6cc4\u7269\u91cc\uff1b"
                       "\u4e14\u5224\u636e\u4e0d\u770b\u5929\u6570\uff0c\u8981\u4ee5\u6c28\u6c2e\u4e0e\u4e9a\u785d\u9178\u76d0\u90fd\u80fd\u5728\u4e00\u5230\u4e24\u5929\u5185\u964d\u5230\u4e0d\u53ef\u6d4b\u4e3a\u51c6" % (
                           cd, seed, min_day))
    except (TypeError, ValueError):
        pass

    # 7 \u6295\u5582
    try:
        ft = int(plan.get("feed_times_per_day"))
        if ft > 3:
            bad.append("\u6bcf\u65e5\u6295\u5582 %d \u6b21\u8d85\u8fc7 3 \u6b21\u4e0a\u9650\uff1a\u6295\u5582\u8fc7\u91cf\u662f\u6700\u5e38\u89c1\u7684\u6c34\u8d28\u6076\u5316\u6765\u6e90\uff1b"
                       "\u6210\u9c7c\u5e94\u4e3a 1 \u5230 2 \u6b21" % ft)
    except (TypeError, ValueError):
        pass
    try:
        fm = float(plan.get("fed_in_minutes"))
        if fm > 5:
            bad.append("\u672c\u6b21\u6295\u9975 %.0f \u5206\u949f\u540e\u4ecd\u6709\u6b8b\u98df\uff0c\u8bf4\u660e\u6295\u5582\u8fc7\u91cf\uff1a"
                       "\u6807\u51c6\u53e3\u5f84\u662f 2 \u5230 3 \u5206\u949f\u5185\u5403\u5b8c\uff0c"
                       "\u4e14\u6295\u5582\u540e 10 \u5206\u949f\u5185\u7684\u6b8b\u9975\u8981\u5438\u51fa\uff0c\u5426\u5219\u4f1a\u5206\u89e3\u4e3a\u6c28\u6c2e" % fm)
    except (TypeError, ValueError):
        pass

    # 8 \u8fc7\u6ee4\u505c\u8f6c
    try:
        fs = float(plan.get("filter_stop_hours"))
        if fs > 4:
            bad.append("\u8fc7\u6ee4\u505c\u8f6c %.1f \u5c0f\u65f6\u8d85\u8fc7 4 \u5c0f\u65f6\uff1a\u785d\u5316\u83cc\u662f\u9700\u6c27\u83cc\uff0c"
                       "\u505c\u8f6c\u6216\u6ee4\u6750\u5e72\u6db8\u4f1a\u9020\u6210\u5904\u7406\u80fd\u529b\u660e\u663e\u5012\u9000\uff0c\u9700\u91cd\u65b0\u6d4b\u6c34" % fs)
        elif fs > 1:
            warn.append("\u8fc7\u6ee4\u505c\u8f6c %.1f \u5c0f\u65f6\uff1a\u8d85\u8fc7 1 \u5c0f\u65f6\u5e94\u52a0\u5f3a\u6c34\u8d28\u89c2\u5bdf" % fs)
    except (TypeError, ValueError):
        pass

    # 9 \u65b0\u9c7c\u5165\u7f38\u987a\u5e8f\uff1a\u6309\u586b\u7684\u539f\u5e8f\u53d6\u7d22\u5f15\uff0c\u4e0d\u91cd\u6392
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
        miss.append("\u5165\u7f38\u64cd\u4f5c\u53ea\u8bc6\u522b\u5230 %d \u6b65\uff0c\u672a\u51d1\u9f50\u56db\u6b65\uff0c\u65e0\u6cd5\u5224\u65ad\u987a\u5e8f\u662f\u5426\u8d70\u53cd" % len(picked))
    else:
        seq = [ORDER.index(x) for x in picked]
        if seq != sorted(seq):
            bad.append("\u5165\u7f38\u987a\u5e8f\u8d70\u53cd\uff1a\u5b9e\u9645\u4e3a %s\uff0c\u6b63\u786e\u5e94\u4e3a %s\uff1b"
                       "\u8fc7\u6e29\u5bf9\u4ed8\u6e29\u5dee\u3001\u8fc7\u6c34\u5bf9\u4ed8\u6c34\u8d28\u7a81\u53d8\uff0c\u4e24\u6b65\u5206\u522b\u5bf9\u4ed8\u4e24\u79cd\u6253\u51fb\uff0c"
                       "\u7701\u6389\u4efb\u4f55\u4e00\u6b65\u90fd\u7b49\u4e8e\u8ba9\u9c7c\u81ea\u5df1\u625b" % (
                           " \u2192 ".join(picked), " \u2192 ".join(ORDER)))
    for s in [norm(x) for x in steps]:
        if "\u5012\u888b\u6c34" in s or "\u8fde\u6c34\u5012" in s or "\u6574\u888b\u5012\u5165" in s:
            bad.append("\u64cd\u4f5c\u542b\u300c\u628a\u888b\u91cc\u7684\u6c34\u5012\u8fdb\u7f38\u300d\uff1a\u8fd0\u8f93\u888b\u91cc\u7684\u6c34\u6c28\u6c2e\u5f80\u5f80\u5f88\u9ad8\uff0c"
                       "\u4e14\u53ef\u80fd\u542b\u8fd0\u8f93\u9014\u4e2d\u6dfb\u52a0\u7684\u6210\u5206\uff0c\u5e94\u53ea\u7528\u7f51\u628a\u9c7c\u635e\u51fa\uff0c\u888b\u6c34\u4e0d\u8fdb\u7f38")

    if bad:
        verdict = "\u5148\u5904\u7406"
    elif miss:
        verdict = "\u5f85\u786e\u8ba4"
    else:
        verdict = "\u53ef\u7167\u6b64\u6267\u884c"
    return {"verdict": verdict, "bad": bad, "warn": warn, "miss": miss}


def render(plan, res):
    lines = []
    lines.append("# \u89c2\u8d4f\u9c7c\u6c34\u8d28\u4e0e\u5582\u517b\u6838\u5bf9\u7ed3\u679c")
    lines.append("")
    lines.append("\u6c34\u4f53\uff1a%s \u5347 \uff5c \u9c7c\u4f53\u957f\u5408\u8ba1\uff1a%s \u5398\u7c73 \uff5c \u79cd\u7c7b\uff1a%s \uff5c \u517b\u6c34\uff1a%s \u5929" % (
        plan.get("tank_liters", "-"), plan.get("fish_cm_total", "-"),
        plan.get("fish_type", "-"), plan.get("cycle_days", "-")))
    lines.append("")
    lines.append("\u7ed3\u8bba\uff1a**%s**" % res["verdict"])
    lines.append("")
    if res["bad"]:
        lines.append("## \u4e0d\u5408\u683c\u9879\uff08\u5fc5\u987b\u6539\u65b9\u6848\u540e\u518d\u5b9e\u65bd\uff09")
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
        lines.append("\u6c34\u8d28\u3001\u5bc6\u5ea6\u3001\u6362\u6c34\u4e0e\u6295\u5582\u5747\u5728\u53e3\u5f84\u5185\uff0c\u5165\u7f38\u6b65\u9aa4\u987a\u5e8f\u6b63\u786e\u3002"
                     "\u4fdd\u6301\u4e24\u5468\u4e00\u6b21\u7684\u6d4b\u6c34\u8282\u594f\u5e76\u505a\u8bb0\u5f55\uff0c\u8d8b\u52bf\u6bd4\u5355\u6b21\u6570\u503c\u66f4\u80fd\u8bf4\u660e\u95ee\u9898\u3002")
    lines.append("")
    lines.append("\u6ce8\uff1a\u672c\u7ed3\u679c\u4e3a\u5bb6\u5ead\u9972\u517b\u7ba1\u7406\u6838\u5bf9\uff0c\u4e0d\u6784\u6210\u6c34\u4ea7\u517d\u533b\u8bca\u7597\u610f\u89c1\uff1b"
                 "\u6d89\u53ca\u9c7c\u75c5\u8bf7\u54a8\u8be2\u4e13\u4e1a\u4eba\u5458\u3002")
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
        "tank_liters": 60, "fish_cm_total": 45, "fish_type": "\u5c0f\u578b\u70ed\u5e26\u9c7c",
        "ammonia": 0.0, "nitrite": 0.0, "nitrate": 20, "ph": 7.0,
        "temp_c": 26, "temp_change_24h": 0.5, "cycle_days": 14,
        "cycle_seed": "\u6210\u719f\u6ee4\u6750", "water_change_percent": 30,
        "dechlorinated": True, "feed_times_per_day": 2, "fed_in_minutes": 3,
        "filter_stop_hours": 0,
        "steps": ["\u8fde\u888b\u6ce1\u7f3820\u5206\u949f", "\u5206\u6279\u5151\u6c3440\u5206\u949f", "\u7528\u7f51\u635e\u9c7c\u5165\u7f38", "\u5173\u706f\u9759\u517b\u89c2\u5bdf"],
    }

    # 1 \u6b63\u4f8b
    r = check(dict(base))
    check_case("\u6b63\u4f8b\u5e94\u5224\u53ef\u7167\u6b64\u6267\u884c", r["verdict"] == "\u53ef\u7167\u6b64\u6267\u884c", str(r))

    # 2 \u53cd\u4f8b\uff1a\u6c28\u6c2e\u8fdb\u5371\u9669\u533a\u95f4
    bad_nh3 = dict(base, ammonia=0.6)
    r = check(bad_nh3)
    check_case("\u53cd\u4f8b-\u6c28\u6c2e0.6\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))
    check_case("\u53cd\u4f8b-\u6c28\u6c2e\u5e94\u5e26\u635f\u4f24\u539f\u56e0", any("\u9cc3" in x for x in r["bad"]))

    # 3 \u53cd\u4f8b\uff1a\u4e9a\u785d\u9178\u76d0\u8d85\u6807
    bad_no2 = dict(base, nitrite=0.8)
    r = check(bad_no2)
    check_case("\u53cd\u4f8b-\u4e9a\u785d\u9178\u76d00.8\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 4 \u53cd\u4f8b\uff1a\u785d\u9178\u76d0\u8d85\u6807
    bad_no3 = dict(base, nitrate=60)
    r = check(bad_no3)
    check_case("\u53cd\u4f8b-\u785d\u9178\u76d060\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 5 \u53cd\u4f8b\uff1a\u5355\u6b21\u6362\u6c34\u8d85\u8fc7\u4e0a\u9650
    bad_wc = dict(base, water_change_percent=70)
    r = check(bad_wc)
    check_case("\u53cd\u4f8b-\u6362\u6c34\u4e03\u6210\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 6 \u53cd\u4f8b\uff1a\u81ea\u6765\u6c34\u672a\u5904\u7406
    bad_chl = dict(base, dechlorinated=False)
    r = check(bad_chl)
    check_case("\u53cd\u4f8b-\u672a\u9664\u6c2f\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 7 \u53cd\u4f8b\uff1a\u517b\u6c34\u5929\u6570\u4e0d\u8db3
    bad_cyc = dict(base, cycle_days=3, cycle_seed="\u6210\u719f\u6ee4\u6750")
    r = check(bad_cyc)
    check_case("\u53cd\u4f8b-\u517b\u6c343\u5929\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 8 \u53cd\u4f8b\uff1a\u5bc6\u5ea6\u8d85\u6807
    bad_den = dict(base, fish_cm_total=120)
    r = check(bad_den)
    check_case("\u53cd\u4f8b-\u5bc6\u5ea6\u8d85\u6807\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 9 \u53cd\u4f8b\uff1a\u5165\u7f38\u987a\u5e8f\u8d70\u53cd
    bad_ord = dict(base, steps=["\u5206\u6279\u5151\u6c3440\u5206\u949f", "\u8fde\u888b\u6ce1\u7f3820\u5206\u949f", "\u7528\u7f51\u635e\u9c7c\u5165\u7f38", "\u5173\u706f\u9759\u517b\u89c2\u5bdf"])
    r = check(bad_ord)
    check_case("\u53cd\u4f8b-\u5165\u7f38\u987a\u5e8f\u8d70\u53cd\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))
    check_case("\u53cd\u4f8b-\u987a\u5e8f\u8d70\u53cd\u5e94\u70b9\u540d\u8fc7\u6e29", any("\u8fc7\u6e29" in x for x in r["bad"]))

    # 10 \u53cd\u4f8b\uff1a\u628a\u888b\u6c34\u5012\u8fdb\u7f38
    bad_bag = dict(base, steps=["\u8fde\u888b\u6ce1\u7f38", "\u5206\u6279\u5151\u6c34", "\u6574\u888b\u5012\u5165\u7f38\u4e2d", "\u9759\u517b\u89c2\u5bdf"])
    r = check(bad_bag)
    check_case("\u53cd\u4f8b-\u5012\u888b\u6c34\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 11 \u53cd\u4f8b\uff1a\u6295\u5582\u6b21\u6570\u8fc7\u591a
    bad_feed = dict(base, feed_times_per_day=5)
    r = check(bad_feed)
    check_case("\u53cd\u4f8b-\u6bcf\u65e5\u55825\u6b21\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 12 \u53cd\u4f8b\uff1a\u8fc7\u6ee4\u505c\u8f6c\u8fc7\u4e45
    bad_filt = dict(base, filter_stop_hours=8)
    r = check(bad_filt)
    check_case("\u53cd\u4f8b-\u8fc7\u6ee4\u505c\u8f6c8\u5c0f\u65f6\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 13 \u53cd\u4f8b\uff1a\u9178\u78b1\u5ea6\u504f\u79bb\u9c7c\u79cd\u533a\u95f4
    bad_ph = dict(base, fish_type="\u9526\u9ca4", ph=6.0)
    r = check(bad_ph)
    check_case("\u53cd\u4f8b-\u9526\u9ca4\u9178\u78b1\u5ea66.0\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 14 \u7f3a\u9879 -> \u5f85\u786e\u8ba4
    incom = dict(base)
    del incom["ammonia"]
    del incom["nitrate"]
    del incom["nitrite"]
    del incom["ph"]
    del incom["temp_c"]
    r = check(incom)
    check_case("\u7f3a\u6c34\u8d28\u6570\u636e\u5e94\u5224\u5f85\u786e\u8ba4", r["verdict"] == "\u5f85\u786e\u8ba4", str(r))

    # 15 \u5224\u5b9a\u987a\u5e8f\uff1a\u65e2\u6709\u7f3a\u9879\u53c8\u6709\u7f3a\u9677\u65f6\u5fc5\u987b\u5148\u5904\u7406
    both = dict(base, ammonia=1.0)
    del both["nitrate"]
    del both["nitrite"]
    del both["ph"]
    del both["temp_c"]
    r = check(both)
    check_case("\u7f3a\u9677\u4f18\u5148\u4e8e\u7f3a\u9879", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 16 UTF-8 BOM \u8f93\u5165\u5fc5\u987b\u80fd\u88ab\u6b63\u786e\u5904\u7406
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "tank.json")
        with open(p, "w", encoding="utf-8-sig") as f:
            json.dump(dict(base), f, ensure_ascii=False)
        with open(p, "rb") as f:
            head = f.read(3)
        check_case("\u6837\u4f8b\u6587\u4ef6\u786e\u5b9e\u5e26BOM", head == b"\xef\xbb\xbf")
        r = check(load_plan(p))
        check_case("\u5e26BOM\u6587\u4ef6\u5e94\u6b63\u5e38\u89e3\u6790\u5e76\u5224\u53ef\u7167\u6b64\u6267\u884c", r["verdict"] == "\u53ef\u7167\u6b64\u6267\u884c", str(r))

        # 17 BOM + \u53cd\u4f8b\u4ecd\u5fc5\u987b\u5224\u4e0d\u5408\u683c
        p2 = os.path.join(td, "bad.json")
        with open(p2, "w", encoding="utf-8-sig") as f:
            json.dump(dict(bad_nh3), f, ensure_ascii=False)
        r = check(load_plan(p2))
        check_case("\u5e26BOM\u53cd\u4f8b\u4ecd\u5224\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 18 \u6392\u5e8f\u65b9\u5411\u9501\u5b9a\uff1a\u5bc6\u5ea6\u7cfb\u6570\u5fc5\u987b\u968f\u6392\u6cc4\u91cf\u9012\u589e
    vals = [FISH_NEED[k] for k in ["\u5c0f\u578b\u70ed\u5e26\u9c7c", "\u4e2d\u578b\u70ed\u5e26\u9c7c", "\u91d1\u9c7c", "\u9526\u9ca4"]]
    check_case("\u9c7c\u79cd\u6240\u9700\u6c34\u4f53\u5e94\u9012\u589e", vals == sorted(vals) and vals[0] < vals[-1])

    # 19 \u517b\u6c34\u5468\u671f\uff1a\u52a0\u4e86\u83cc\u6e90\u7684\u5e94\u77ed\u4e8e\u81ea\u7136\u5efa\u7acb
    check_case("\u52a0\u5165\u6210\u719f\u6ee4\u6750\u7684\u517b\u6c34\u5468\u671f\u5e94\u77ed\u4e8e\u65e0\u83cc\u6e90",
               CYCLE_MIN["\u6210\u719f\u6ee4\u6750"] < CYCLE_MIN["\u65e0"])

    lines = ["SELFTEST OK (%d passed, 0 failed)" % ok]
    if fail:
        lines = ["SELFTEST FAILED (%d passed, %d failed)" % (ok, len(fail))]
        lines += ["- " + x for x in fail]
    write_out("\n".join(lines) + "\n", "_selftest_result.txt")
    print("\n".join(lines))
    return 0 if not fail else 1


def main():
    ap = argparse.ArgumentParser(description="\u89c2\u8d4f\u9c7c\u6c34\u8d28\u4e0e\u5582\u517b\u7ba1\u7406\u6821\u9a8c")
    ap.add_argument("--file", help="\u9c7c\u7f38\u72b6\u6001 json \u6587\u4ef6\u8def\u5f84")
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


