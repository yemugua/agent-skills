# -*- coding: utf-8 -*-
"""\u86cb\u7cd5\u6253\u53d1\u72b6\u6001\u6838\u5bf9\u4e0e\u8865\u6551\u5de5\u5177\u3002

\u7528\u6cd5:
  python cake_whipping_check.py --file case.json [--json]
  python cake_whipping_check.py --selftest

\u5224\u5b9a\u987a\u5e8f: \u5148\u770b\u771f\u5b9e\u7f3a\u9677(\u5668\u5177\u5e26\u6cb9\u5e26\u6c34\u3001\u6df7\u5165\u86cb\u9ec4\u3001\u6e29\u5ea6\u8d8a\u754c\u3001\u4e73\u8102\u4e0d\u8db3\u3001
\u6253\u8fc7\u5934\u3001\u6cb9\u6c34\u5206\u79bb), \u518d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574; \u53ea\u586b\u4e86\u300c\u5df2\u6cb9\u6c34\u5206\u79bb\u300d\u8fd9\u4e00\u4e2a\u5b57\u6bb5\u65f6,
\u76f4\u63a5\u5224\u4e0d\u5408\u683c\u5e76\u7ed9\u51fa\u8865\u6551, \u4e0d\u662f\u5f85\u786e\u8ba4\u3002
"""
import argparse
import io
import json
import os
import sys
import tempfile

TYPE_LABEL = {
    "meringue": u"\u86cb\u767d",
    "cream": u"\u6de1\u5976\u6cb9",
    "sponge": u"\u5168\u86cb",
    "butter": u"\u9ec4\u6cb9",
}

STATE_ORDER = ["soft_peak", "medium_peak", "stiff_peak"]
STATE_LABEL = {
    "meringue": {
        "soft_peak": u"\u6e7f\u6027\u53d1\u6ce1\uff08\u63d0\u8d77\u6709\u5927\u5f2f\u94a9\uff09",
        "medium_peak": u"\u4e2d\u6027\u53d1\u6ce1\uff08\u63d0\u8d77\u6709\u5c0f\u5f2f\u94a9\uff09",
        "stiff_peak": u"\u5e72\u6027\u53d1\u6ce1\uff08\u63d0\u8d77\u662f\u76f4\u7acb\u5c16\u89d2\uff09",
    },
    "cream": {
        "soft_peak": u"\u516d\u4e03\u53d1\uff08\u6d53\u7a20\u53ef\u7f13\u6162\u6d41\u52a8\uff09",
        "medium_peak": u"\u516b\u53d1\uff08\u7eb9\u8def\u6e05\u6670\u3001\u5c16\u5cf0\u5f2f\u94a9\uff09",
        "stiff_peak": u"\u4e5d\u5341\u53d1\uff08\u786c\u633a\u3001\u5c16\u5cf0\u76f4\u7acb\uff09",
    },
    "sponge": {
        "soft_peak": u"\u7c97\u6ce1\u9636\u6bb5\uff08\u6c14\u6ce1\u5927\u800c\u7c97\uff09",
        "medium_peak": u"\u7ec6\u817b\u9636\u6bb5\uff08\u6c14\u6ce1\u7ec6\u5bc6\uff09",
        "stiff_peak": u"\u753b\u516b\u5b57\u9636\u6bb5\uff08\u75d5\u8ff9\u53ef\u4fdd\u6301\u6570\u79d2\uff09",
    },
    "butter": {
        "soft_peak": u"\u6253\u53d1\u4e0d\u8db3\uff08\u989c\u8272\u672a\u53d8\u6d45\u3001\u4f53\u79ef\u672a\u81a8\u5927\uff09",
        "medium_peak": u"\u6253\u53d1\u5408\u9002\uff08\u989c\u8272\u53d8\u6d45\u3001\u4f53\u79ef\u81a8\u5927\uff09",
        "stiff_peak": u"\u6253\u8fc7\u5934\uff08\u5448\u6cb9\u72b6\u6216\u5df2\u5316\u5f00\uff09",
    },
}

TEMP_OK = {
    "meringue": (17.0, 22.0),
    "cream": (0.0, 10.0),
    "sponge": (38.0, 42.0),
    "butter": (20.0, 22.0),
}
TEMP_HARD = {
    "meringue": (8.0, 30.0),
    "cream": (0.0, 15.0),
    "sponge": (30.0, 50.0),
    "butter": (15.0, 26.0),
}
FAT_MIN = 30.0
SUGAR_OK = (8.0, 10.0)
SUGAR_HARD = (5.0, 13.0)


def num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def temp_verdict(wtype, temp):
    if wtype not in TEMP_OK:
        return u"\u5f85\u786e\u8ba4", u"\u6253\u53d1\u7c7b\u578b\u672a\u8bc6\u522b\uff0c\u65e0\u6cd5\u6838\u5bf9\u6e29\u5ea6"
    if temp is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u6750\u6599\u6e29\u5ea6"
    v = float(temp)
    olo, ohi = TEMP_OK[wtype]
    hlo, hhi = TEMP_HARD[wtype]
    label = TYPE_LABEL[wtype]
    if v < hlo or v > hhi:
        if wtype == "cream":
            return u"\u4e0d\u5408\u683c", u"%s\u6e29\u5ea6 %g \u6444\u6c0f\u5ea6\uff0c\u8d85\u8fc7 %.0f \u6444\u6c0f\u5ea6\u4e0a\u9650\uff1a\u6e29\u5ea6\u4e0d\u591f\u4f4e\u65f6\u600e\u4e48\u6253\u90fd\u662f\u7a00\u7684\uff0c\u8fde\u540c\u76c6\u4e0e\u6253\u86cb\u5934\u4e00\u8d77\u51b7\u85cf\u5e76\u57ab\u51b0\u6c34" % (
                label, v, hhi)
        return u"\u4e0d\u5408\u683c", u"%s\u6e29\u5ea6 %g \u6444\u6c0f\u5ea6\uff0c\u8d85\u51fa %.0f-%.0f \u7684\u53ef\u64cd\u4f5c\u8303\u56f4\uff0c\u65e0\u6cd5\u7a33\u5b9a\u6253\u53d1" % (label, v, hlo, hhi)
    if v < olo or v > ohi:
        return u"\u9700\u6539\u8fdb", u"%s\u6e29\u5ea6 %g \u6444\u6c0f\u5ea6\uff0c\u5728 %.0f-%.0f \u4e4b\u5916\uff0c\u5efa\u8bae\u8c03\u5230\u8be5\u533a\u95f4" % (label, v, olo, ohi)
    return u"\u5408\u683c", u"%s\u6e29\u5ea6 %g \u6444\u6c0f\u5ea6\uff0c\u5728 %.0f-%.0f \u533a\u95f4" % (label, v, olo, ohi)


def state_verdict(wtype, target, observed):
    if wtype not in STATE_LABEL:
        return u"\u5f85\u786e\u8ba4", u"\u6253\u53d1\u7c7b\u578b\u672a\u8bc6\u522b\uff0c\u65e0\u6cd5\u6838\u5bf9\u72b6\u6001"
    if target not in STATE_ORDER or observed not in STATE_ORDER:
        return u"\u5f85\u786e\u8ba4", u"\u76ee\u6807\u72b6\u6001\u6216\u89c2\u5bdf\u5230\u7684\u72b6\u6001\u672a\u63d0\u4f9b\u6216\u53d6\u503c\u672a\u8bc6\u522b"
    ti = STATE_ORDER.index(target)
    oi = STATE_ORDER.index(observed)
    tlab = STATE_LABEL[wtype][target]
    olab = STATE_LABEL[wtype][observed]
    if oi > ti:
        return u"\u4e0d\u5408\u683c", u"%s\u6253\u8fc7\u5934\uff1a\u76ee\u6807\u4e3a%s\uff0c\u5b9e\u9645\u5df2\u5230%s\u3002%s" % (
            TYPE_LABEL[wtype], tlab, olab, u"\u6253\u8fc7\u5934\u6bd4\u6253\u4e0d\u591f\u66f4\u96be\u6551")
    if oi < ti:
        return u"\u9700\u6539\u8fdb", u"%s\u6253\u53d1\u4e0d\u8db3\uff1a\u76ee\u6807\u4e3a%s\uff0c\u5f53\u524d\u53ea\u5230%s\uff0c\u7ee7\u7eed\u6253\u5230\u76ee\u6807\u72b6\u6001\u5c31\u505c" % (
            TYPE_LABEL[wtype], tlab, olab)
    return u"\u5408\u683c", u"%s\u8fbe\u5230\u76ee\u6807\u72b6\u6001\uff1a%s" % (TYPE_LABEL[wtype], olab)


def fat_verdict(wtype, fat):
    if wtype != "cream":
        return None, None
    if fat is None:
        return u"\u5f85\u786e\u8ba4", u"\u6de1\u5976\u6cb9\u672a\u63d0\u4f9b\u4e73\u8102\u542b\u91cf"
    v = float(fat)
    if v < FAT_MIN:
        return u"\u4e0d\u5408\u683c", u"\u6de1\u5976\u6cb9\u4e73\u8102\u542b\u91cf %.0f%%\uff0c\u4f4e\u4e8e %.0f%%\uff1a\u57fa\u672c\u6253\u4e0d\u53d1\uff0c\u9700\u6362\u4e73\u8102\u542b\u91cf\u66f4\u9ad8\u7684\u4ea7\u54c1" % (v, FAT_MIN)
    return u"\u5408\u683c", u"\u6de1\u5976\u6cb9\u4e73\u8102\u542b\u91cf %.0f%%\uff0c\u6ee1\u8db3 %.0f%% \u4ee5\u4e0a\u8981\u6c42" % (v, FAT_MIN)


def sugar_verdict(wtype, ratio):
    if wtype != "cream":
        return None, None
    if ratio is None:
        return u"\u5f85\u786e\u8ba4", u"\u6de1\u5976\u6cb9\u672a\u63d0\u4f9b\u7cd6\u91cf\u5360\u6bd4"
    v = float(ratio)
    if v < SUGAR_HARD[0] or v > SUGAR_HARD[1]:
        return u"\u9700\u6539\u8fdb", u"\u7cd6\u91cf\u5360\u6bd4 %.0f%% \u504f\u79bb %.0f%%-%.0f%% \u592a\u591a\uff0c\u5f71\u54cd\u6253\u53d1\u4e0e\u7a33\u5b9a\u6027" % (
            v, SUGAR_OK[0], SUGAR_OK[1])
    if v < SUGAR_OK[0] or v > SUGAR_OK[1]:
        return u"\u9700\u6539\u8fdb", u"\u7cd6\u91cf\u5360\u6bd4 %.0f%%\uff0c\u5e38\u7528\u533a\u95f4\u4e3a %.0f%%-%.0f%%" % (v, SUGAR_OK[0], SUGAR_OK[1])
    return u"\u5408\u683c", u"\u7cd6\u91cf\u5360\u6bd4 %.0f%%\uff0c\u5728 %.0f%%-%.0f%% \u533a\u95f4" % (v, SUGAR_OK[0], SUGAR_OK[1])


def stage_verdict(wtype, stages):
    if wtype != "meringue":
        return None, None
    if stages is None:
        return u"\u5f85\u786e\u8ba4", u"\u86cb\u767d\u672a\u63d0\u4f9b\u52a0\u7cd6\u6b21\u6570"
    v = float(stages)
    if v >= 3.0:
        return u"\u5408\u683c", u"\u86cb\u767d\u5206 %g \u6b21\u52a0\u7cd6\uff0c\u7b26\u5408\u5206\u4e09\u6b21\u52a0\u7cd6\u7684\u8981\u6c42" % v
    if v >= 1.0:
        return u"\u9700\u6539\u8fdb", u"\u86cb\u767d\u53ea\u52a0 %g \u6b21\u7cd6\uff1a\u4e00\u6b21\u6027\u52a0\u7cd6\u4f1a\u62d6\u6162\u6253\u53d1\u5e76\u964d\u4f4e\u7a33\u5b9a\u6027\uff0c\u5e94\u5728\u7c97\u6ce1\u3001\u7ec6\u6ce1\u3001\u51fa\u73b0\u7eb9\u8def\u65f6\u5404\u52a0\u4e00\u6b21" % v
    return u"\u9700\u6539\u8fdb", u"\u86cb\u767d\u672a\u52a0\u7cd6\uff1a\u7cd6\u4e0d\u53ea\u662f\u8c03\u5473\uff0c\u4e5f\u53c2\u4e0e\u7a33\u5b9a\u6c14\u6ce1\u7ed3\u6784"


def speed_verdict(profile):
    if profile is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u6253\u86cb\u901f\u5ea6\u65b9\u5f0f"
    if profile == "low_finish":
        return u"\u5408\u683c", u"\u6700\u540e\u8f6c\u4f4e\u901f\u6574\u7406\uff0c\u6c14\u6ce1\u7ec6\u817b\u7a33\u5b9a"
    if profile == "high_throughout":
        return u"\u9700\u6539\u8fdb", u"\u5168\u7a0b\u9ad8\u901f\uff1a\u6253\u51fa\u7684\u6c14\u6ce1\u7c97\u5927\u4e0d\u7a33\u5b9a\uff0c\u6210\u54c1\u6613\u584c\u9677\uff0c\u6700\u540e\u5e94\u8f6c\u4f4e\u901f\u6574\u7406 30 \u79d2\u5230 1 \u5206\u949f"
    return u"\u5f85\u786e\u8ba4", u"\u6253\u86cb\u901f\u5ea6\u65b9\u5f0f\u53d6\u503c\u672a\u8bc6\u522b"


def rescue_steps(wtype, separated, over_whipped, state_v):
    steps = []
    if separated:
        if wtype == "cream":
            steps.append(u"\u4e25\u91cd\u6cb9\u6c34\u5206\u79bb\uff1a\u65e0\u6cd5\u7528\u4e8e\u88f1\u82b1\u62b9\u9762")
            steps.append(u"\u56fa\u4f53\u90e8\u5206\u53ef\u7ee7\u7eed\u6405\u6253\u5206\u79bb\u51fa\u9ec4\u6cb9\u7528\u4e8e\u70d8\u7119\uff0c\u6db2\u4f53\u90e8\u5206\u53ef\u53e6\u4f5c\u4ed6\u7528")
            steps.append(u"\u6216\u52a0\u5165\u5927\u91cf\u672a\u6253\u53d1\u6db2\u4f53\u5976\u6cb9\uff08\u7ea6\u539f\u91cf 30% \u4ee5\u4e0a\uff09\u4f4e\u901f\u91cd\u6253\uff0c\u4ec5\u80fd\u90e8\u5206\u633d\u56de")
        else:
            steps.append(u"\u5df2\u6790\u51fa\u6c34\u5206\uff1a\u6ca5\u6389\u6790\u51fa\u7684\u6c34\uff0c\u52a0\u65b0\u86cb\u767d\u4f4e\u901f\u91cd\u6253\uff0c\u6210\u54c1\u7a33\u5b9a\u6027\u4f1a\u4e0b\u964d")
            steps.append(u"\u4e25\u91cd\u5206\u79bb\u65f6\u6539\u505a\u86cb\u767d\u971c\u8106\u997c\u7c7b\uff0c\u6216\u76f4\u63a5\u91cd\u505a")
        return steps
    if over_whipped or state_v == u"\u4e0d\u5408\u683c":
        if wtype == "cream":
            steps.append(u"\u8f7b\u5fae\uff1a\u7acb\u5373\u505c\u6b62\uff0c\u52a0\u5165\u5c11\u91cf\u672a\u6253\u53d1\u6db2\u4f53\u6de1\u5976\u6cb9\uff0c\u4f4e\u901f\u6405\u81f3\u91cd\u65b0\u987a\u6ed1")
            steps.append(u"\u4e2d\u5ea6\uff1a\u5012\u51fa\u6db2\u4f53\uff0c\u52a0\u5165\u672a\u6253\u53d1\u5976\u6cb9\u7ea6\u539f\u91cf 20-30%\uff0c\u4f4e\u901f\u91cd\u6253\uff0c\u4ec5\u9002\u5408\u4f5c\u5939\u9985")
            steps.append(u"\u4e25\u91cd\uff1a\u6309\u6cb9\u6c34\u5206\u79bb\u5904\u7406")
        elif wtype == "meringue":
            steps.append(u"\u8f7b\u5fae\uff1a\u52a0\u5c11\u91cf\u65b0\u86cb\u767d\uff08\u539f\u91cf 10-15%\uff09\uff0c\u4f4e\u901f\u91cd\u65b0\u62cc\u5300\u6253\u53d1\uff0c\u53ef\u90e8\u5206\u6062\u590d")
            steps.append(u"\u4e2d\u5ea6\uff1a\u6ca5\u6389\u6790\u6c34\uff0c\u52a0\u65b0\u86cb\u767d\u4f4e\u901f\u91cd\u6253\uff0c\u4f53\u79ef\u4e0e\u7ec6\u817b\u5ea6\u4f1a\u6253\u6298")
            steps.append(u"\u4e25\u91cd\uff1a\u68c9\u7d6e\u72b6\u5927\u91cf\u6790\u6c34\u65f6\u57fa\u672c\u65e0\u6cd5\u7528\u4e8e\u86cb\u7cd5\uff0c\u5efa\u8bae\u91cd\u505a")
        elif wtype == "butter":
            steps.append(u"\u9ec4\u6cb9\u5448\u6cb9\u72b6\uff1a\u51b7\u85cf\u56de\u786c\u540e\u91cd\u65b0\u8f6f\u5316\u5230 20-22 \u6444\u6c0f\u5ea6\u518d\u6253")
        else:
            steps.append(u"\u5168\u86cb\u8fc7\u5934\uff1a\u6c14\u6ce1\u5df2\u7834\u88c2\uff0c\u5efa\u8bae\u91cd\u65b0\u6253\u53d1")
        return steps
    return steps


def load_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def build_report(data):
    wtype = data.get("type")
    bowl = data.get("bowl_clean_dry")
    yolk = data.get("yolk_mixed")
    temp = num(data.get("temp_c"))
    stages = num(data.get("sugar_stages"))
    profile = data.get("speed_profile")
    target = data.get("target_state")
    observed = data.get("observed_state")
    over = data.get("over_whipped")
    separated = data.get("separated")
    fat = num(data.get("cream_fat_pct"))
    sugar = num(data.get("sugar_ratio_pct"))

    tv, tm = temp_verdict(wtype, temp)
    sv, sm = state_verdict(wtype, target, observed)
    fv, fm = fat_verdict(wtype, fat)
    suv, sum_ = sugar_verdict(wtype, sugar)
    stv, stm = stage_verdict(wtype, stages)
    spv, spm = speed_verdict(profile)

    defects = []
    fine = []
    pending = []

    if wtype not in TYPE_LABEL:
        pending.append(u"\u6253\u53d1\u7c7b\u578b\u672a\u586b\u6216\u53d6\u503c\u672a\u8bc6\u522b\uff0c\u5e94\u4e3a\u86cb\u767d\u3001\u6de1\u5976\u6cb9\u3001\u5168\u86cb\u6216\u9ec4\u6cb9")

    if bowl is False:
        defects.append(u"\u76c6\u6216\u6253\u86cb\u5934\u5e26\u6cb9\u5e26\u6c34\uff1a\u54ea\u6015\u4e00\u70b9\u70b9\u6cb9\u8102\u86cb\u767d\u4e5f\u57fa\u672c\u6253\u4e0d\u8d77\u6765\uff0c\u8fd9\u662f\u6e05\u6d01\u95ee\u9898\u4e0d\u662f\u6280\u672f\u95ee\u9898")
    elif bowl is None:
        pending.append(u"\u672a\u586b\u76c6\u4e0e\u6253\u86cb\u5934\u662f\u5426\u65e0\u6c34\u65e0\u6cb9")

    if yolk is True:
        defects.append(u"\u86cb\u767d\u6df7\u5165\u86cb\u9ec4\uff1a\u86cb\u9ec4\u542b\u8102\u80aa\u4f1a\u963b\u6b62\u6253\u53d1\uff0c\u6df7\u5165\u7684\u86cb\u767d\u5e94\u6539\u505a\u5176\u4ed6\u7528\u9014")
    elif yolk is None:
        pending.append(u"\u672a\u586b\u662f\u5426\u6df7\u5165\u86cb\u9ec4")

    if separated is True:
        defects.append(u"\u5df2\u6cb9\u6c34\u5206\u79bb\uff1a\u6309\u5206\u7ea7\u8865\u6551\u5904\u7406\uff0c\u65e0\u6cd5\u6062\u590d\u5230\u7406\u60f3\u72b6\u6001")

    if over is True:
        defects.append(u"\u5df2\u6253\u8fc7\u5934\uff1a\u6253\u8fc7\u5934\u6bd4\u6253\u4e0d\u591f\u66f4\u96be\u6551\uff0c\u6309\u5206\u7ea7\u8865\u6551\u5904\u7406")

    if tv == u"\u4e0d\u5408\u683c":
        defects.append(tm)
    elif tv == u"\u9700\u6539\u8fdb":
        fine.append(tm)
    elif tv == u"\u5f85\u786e\u8ba4":
        pending.append(tm)

    if sv == u"\u4e0d\u5408\u683c":
        defects.append(sm)
    elif sv == u"\u9700\u6539\u8fdb":
        fine.append(sm)
    elif sv == u"\u5f85\u786e\u8ba4":
        pending.append(sm)

    if fv == u"\u4e0d\u5408\u683c":
        defects.append(fm)
    elif fv == u"\u9700\u6539\u8fdb":
        fine.append(fm)
    elif fv == u"\u5f85\u786e\u8ba4":
        pending.append(fm)

    if suv == u"\u9700\u6539\u8fdb":
        fine.append(sum_)
    elif suv == u"\u5f85\u786e\u8ba4":
        pending.append(sum_)

    if stv == u"\u9700\u6539\u8fdb":
        fine.append(stm)
    elif stv == u"\u5f85\u786e\u8ba4":
        pending.append(stm)

    if spv == u"\u9700\u6539\u8fdb":
        fine.append(spm)
    elif spv == u"\u5f85\u786e\u8ba4":
        pending.append(spm)

    steps = rescue_steps(wtype, separated is True, over is True, sv)

    lines = []
    lines.append("=" * 62)
    lines.append(u"\u86cb\u7cd5\u6253\u53d1\u72b6\u6001\u6838\u5bf9\u4e0e\u8865\u6551")
    lines.append("=" * 62)
    lines.append(u"\u6253\u53d1\u5bf9\u8c61\uff1a%s" % TYPE_LABEL.get(wtype, u"\u672a\u8bc6\u522b"))
    lines.append("")
    lines.append(u"[\u4e00] \u9010\u9879\u5224\u5b9a")
    lines.append(u"  \u5668\u5177\u65e0\u6c34\u65e0\u6cb9\uff1a%s" % (u"\u662f" if bowl is True else (u"\u5426" if bowl is False else u"\u672a\u586b")))
    lines.append(u"  \u6df7\u5165\u86cb\u9ec4\uff1a%s" % (u"\u662f" if yolk is True else (u"\u5426" if yolk is False else u"\u672a\u586b")))
    lines.append(u"  \u6e29\u5ea6\uff1a%s \u2014\u2014 %s" % (tv, tm))
    lines.append(u"  \u72b6\u6001\uff1a%s \u2014\u2014 %s" % (sv, sm))
    if fv:
        lines.append(u"  \u4e73\u8102\uff1a%s \u2014\u2014 %s" % (fv, fm))
    if suv:
        lines.append(u"  \u7cd6\u91cf\uff1a%s \u2014\u2014 %s" % (suv, sum_))
    if stv:
        lines.append(u"  \u52a0\u7cd6\u6b21\u6570\uff1a%s \u2014\u2014 %s" % (stv, stm))
    lines.append(u"  \u901f\u5ea6\uff1a%s \u2014\u2014 %s" % (spv, spm))
    lines.append(u"  \u6253\u8fc7\u5934\uff1a%s    \u6cb9\u6c34\u5206\u79bb\uff1a%s" % (
        u"\u662f" if over is True else u"\u5426", u"\u662f" if separated is True else u"\u5426"))
    lines.append("")
    lines.append(u"[\u4e8c] \u4e0d\u5408\u683c\u9879\u4e0e\u539f\u56e0")
    if defects:
        for i, d in enumerate(defects, 1):
            lines.append(u"  %d. %s" % (i, d))
    else:
        lines.append(u"  \u65e0")
    lines.append("")
    lines.append(u"[\u4e09] \u9700\u6539\u8fdb\u9879")
    if fine:
        for i, d in enumerate(fine, 1):
            lines.append(u"  %d. %s" % (i, d))
    else:
        lines.append(u"  \u65e0")
    lines.append("")
    lines.append(u"[\u56db] \u5f85\u786e\u8ba4\u9879")
    if pending:
        for i, d in enumerate(pending, 1):
            lines.append(u"  %d. %s" % (i, d))
    else:
        lines.append(u"  \u65e0")
    lines.append("")
    lines.append(u"[\u4e94] \u8865\u6551\u6b65\u9aa4")
    if steps:
        for i, s in enumerate(steps, 1):
            lines.append(u"  %d. %s" % (i, s))
        lines.append(u"  \u63d0\u793a\uff1a\u8865\u6551\u53ea\u80fd\u90e8\u5206\u633d\u56de\uff0c\u4e0d\u4fdd\u8bc1\u6062\u590d\u5982\u521d")
    else:
        lines.append(u"  \u65e0\u9700\u8865\u6551")
    lines.append("")
    lines.append(u"[\u516d] \u64cd\u4f5c\u8981\u70b9")
    lines.append(u"  1. \u6392\u67e5\u987a\u5e8f\uff1a\u5668\u5177 \u2192 \u6df7\u5165\u86cb\u9ec4 \u2192 \u6e29\u5ea6 \u2192 \u4e73\u8102 \u2192 \u52a0\u7cd6 \u2192 \u65b0\u9c9c\u5ea6")
    lines.append(u"  2. \u5230\u76ee\u6807\u72b6\u6001\u5c31\u505c\uff0c\u4e0d\u8981\u300c\u518d\u6253\u4e00\u4f1a\u513f\u4fdd\u9669\u300d")
    lines.append(u"  3. \u86cb\u767d\u5206\u4e09\u6b21\u52a0\u7cd6\uff1a\u7c97\u6ce1\u3001\u7ec6\u6ce1\u3001\u51fa\u73b0\u7eb9\u8def")
    lines.append(u"  4. \u6700\u540e\u8f6c\u4f4e\u901f\u6574\u7406 30 \u79d2\u5230 1 \u5206\u949f\uff0c\u6c14\u6ce1\u66f4\u7ec6\u817b")
    lines.append(u"  5. \u6de1\u5976\u6cb9\u5168\u7a0b\u76ef\u7740\uff0c\u4ece\u516b\u53d1\u5230\u6cb9\u6c34\u5206\u79bb\u5f80\u5f80\u53ea\u6709\u5341\u51e0\u79d2")
    lines.append(u"  6. \u51fa\u73b0\u9178\u5473\u3001\u5f02\u5473\u3001\u53d8\u8272\u5c5e\u4e8e\u53d8\u8d28\uff0c\u4e0d\u98df\u7528\u4e5f\u4e0d\u8865\u6551")

    if defects:
        overall = u"\u4e0d\u5408\u683c"
    elif fine:
        overall = u"\u9700\u6539\u8fdb"
    elif pending:
        overall = u"\u5f85\u786e\u8ba4"
    else:
        overall = u"\u5408\u683c"

    lines.append("")
    lines.append(u"\u603b\u5224\u5b9a\uff1a%s" % overall)
    lines.append(u"\u63d0\u793a\uff1a\u8865\u6551\u53ea\u80fd\u90e8\u5206\u633d\u56de\uff1b\u6750\u6599\u53d8\u8d28\u65f6\u4e0d\u8981\u98df\u7528\u3002")
    lines.append(u"\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u6253\u53d1\u81ea\u67e5\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u914d\u65b9\u6216\u539f\u6599\u7684\u54c1\u8d28\u8bc4\u4ef7\u3002")
    lines.append("=" * 62)

    summary = {
        "type": wtype,
        "temp_verdict": tv,
        "state_verdict": sv,
        "fat_verdict": fv,
        "defects": defects,
        "fine": fine,
        "pending": pending,
        "rescue_steps": steps,
        "overall": overall,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append((u"\u86cb\u767d 20 \u5ea6\u5224\u5408\u683c", temp_verdict("meringue", 20)[0] == u"\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u6de1\u5976\u6cb9 22 \u5ea6\u5224\u4e0d\u5408\u683c", temp_verdict("cream", 22)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u6de1\u5976\u6cb9 8 \u5ea6\u5224\u5408\u683c", temp_verdict("cream", 8)[0] == u"\u5408\u683c"))
    r.append((u"\u9ec4\u6cb9 21 \u5ea6\u5224\u5408\u683c", temp_verdict("butter", 21)[0] == u"\u5408\u683c"))
    r.append((u"\u672a\u77e5\u7c7b\u578b\u6e29\u5ea6\u5224\u5f85\u786e\u8ba4", temp_verdict("xxx", 20)[0] == u"\u5f85\u786e\u8ba4"))
    r.append((u"\u72b6\u6001\u4e00\u81f4\u5224\u5408\u683c", state_verdict("meringue", "medium_peak", "medium_peak")[0] == u"\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u6253\u8fc7\u5934\u5224\u4e0d\u5408\u683c", state_verdict("meringue", "soft_peak", "stiff_peak")[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u6253\u53d1\u4e0d\u8db3\u5224\u9700\u6539\u8fdb", state_verdict("meringue", "stiff_peak", "soft_peak")[0] == u"\u9700\u6539\u8fdb"))
    r.append((u"\u72b6\u6001\u7f3a\u5931\u5224\u5f85\u786e\u8ba4", state_verdict("meringue", "soft_peak", None)[0] == u"\u5f85\u786e\u8ba4"))
    r.append((u"\u53cd\u4f8b\uff1a\u4e73\u8102 28% \u5224\u4e0d\u5408\u683c", fat_verdict("cream", 28)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u4e73\u8102 35% \u5224\u5408\u683c", fat_verdict("cream", 35)[0] == u"\u5408\u683c"))
    r.append((u"\u975e\u6de1\u5976\u6cb9\u4e0d\u67e5\u4e73\u8102", fat_verdict("meringue", 28) == (None, None)))
    r.append((u"\u7cd6\u91cf 9% \u5224\u5408\u683c", sugar_verdict("cream", 9)[0] == u"\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u7cd6\u91cf 20% \u5224\u9700\u6539\u8fdb", sugar_verdict("cream", 20)[0] == u"\u9700\u6539\u8fdb"))
    r.append((u"\u52a0\u7cd6 3 \u6b21\u5224\u5408\u683c", stage_verdict("meringue", 3)[0] == u"\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u52a0\u7cd6 1 \u6b21\u5224\u9700\u6539\u8fdb", stage_verdict("meringue", 1)[0] == u"\u9700\u6539\u8fdb"))
    r.append((u"\u975e\u86cb\u767d\u4e0d\u67e5\u52a0\u7cd6\u6b21\u6570", stage_verdict("cream", 1) == (None, None)))
    r.append((u"\u53cd\u4f8b\uff1a\u5168\u7a0b\u9ad8\u901f\u5224\u9700\u6539\u8fdb", speed_verdict("high_throughout")[0] == u"\u9700\u6539\u8fdb"))
    r.append((u"\u4f4e\u901f\u6536\u5c3e\u5224\u5408\u683c", speed_verdict("low_finish")[0] == u"\u5408\u683c"))
    st = rescue_steps("cream", True, False, u"\u5408\u683c")
    r.append((u"\u6cb9\u6c34\u5206\u79bb\u7ed9\u51fa\u8865\u6551\u6b65\u9aa4", len(st) >= 2 and any(u"\u6cb9\u6c34\u5206\u79bb" in x for x in st)))
    st2 = rescue_steps("meringue", False, True, u"\u5408\u683c")
    r.append((u"\u6253\u8fc7\u5934\u7ed9\u51fa\u8865\u6551\u6b65\u9aa4", len(st2) >= 2))
    r.append((u"\u65e0\u9700\u8865\u6551\u65f6\u8fd4\u56de\u7a7a", rescue_steps("meringue", False, False, u"\u5408\u683c") == []))

    _, s = build_report({
        "type": "meringue", "bowl_clean_dry": True, "yolk_mixed": False,
        "temp_c": 20, "sugar_stages": 3, "speed_profile": "low_finish",
        "target_state": "medium_peak", "observed_state": "medium_peak",
        "over_whipped": False, "separated": False,
    })
    r.append((u"\u6807\u51c6\u86cb\u767d\u6837\u4f8b\u5224\u5b9a\u5408\u683c", s["overall"] == u"\u5408\u683c"))

    _, s1 = build_report({
        "type": "meringue", "bowl_clean_dry": False, "yolk_mixed": True,
        "temp_c": 20, "sugar_stages": 3, "speed_profile": "low_finish",
        "target_state": "medium_peak", "observed_state": "medium_peak",
        "over_whipped": False, "separated": False,
    })
    r.append((u"\u53cd\u4f8b\uff1a\u5668\u5177\u5e26\u6cb9\u5224\u4e0d\u5408\u683c", s1["overall"] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u5668\u5177\u95ee\u9898\u8fdb\u7f3a\u9677\u8868", any(u"\u5e26\u6cb9\u5e26\u6c34" in d for d in s1["defects"])))
    r.append((u"\u53cd\u4f8b\uff1a\u6df7\u5165\u86cb\u9ec4\u8fdb\u7f3a\u9677\u8868", any(u"\u6df7\u5165\u86cb\u9ec4" in d for d in s1["defects"])))

    _, s2 = build_report({
        "type": "cream", "bowl_clean_dry": True, "yolk_mixed": False,
        "temp_c": 22, "sugar_ratio_pct": 9, "speed_profile": "low_finish",
        "target_state": "medium_peak", "observed_state": "soft_peak",
        "cream_fat_pct": 28, "over_whipped": False, "separated": False,
    })
    r.append((u"\u53cd\u4f8b\uff1a\u6de1\u5976\u6cb9\u6e29\u5ea6\u4e0e\u4e73\u8102\u53cc\u8d85\u5224\u4e0d\u5408\u683c", s2["overall"] == u"\u4e0d\u5408\u683c"))

    _, s3 = build_report({"type": "cream", "separated": True})
    r.append((u"\u53ea\u586b\u6cb9\u6c34\u5206\u79bb\u4e0d\u5f97\u5224\u5f85\u786e\u8ba4", s3["overall"] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u6cb9\u6c34\u5206\u79bb\u65f6\u7ed9\u51fa\u8865\u6551\u6b65\u9aa4", len(s3["rescue_steps"]) >= 2))

    _, s4 = build_report({})
    r.append((u"\u5168\u672a\u586b\u8bb0\u4e3a\u5f85\u786e\u8ba4", s4["overall"] == u"\u5f85\u786e\u8ba4"))

    p = os.path.join(tempfile.gettempdir(), "_cake_bom_case.json")
    blob = b"\xef\xbb\xbf" + json.dumps({
        "type": "meringue", "bowl_clean_dry": True, "yolk_mixed": False,
        "temp_c": 20, "sugar_stages": 3, "speed_profile": "low_finish",
        "target_state": "medium_peak", "observed_state": "medium_peak",
    }, ensure_ascii=False).encode("utf-8")
    with open(p, "wb") as f:
        f.write(blob)
    try:
        d = load_json(p)
        r.append((u"UTF-8 BOM \u8f93\u5165\u9996\u952e\u53ef\u8bfb", d.get("type") == "meringue"))
        r.append((u"UTF-8 BOM \u8f93\u5165\u6570\u503c\u53ef\u8bfb", abs(d.get("temp_c", 0) - 20.0) < 1e-9))
    finally:
        if os.path.exists(p):
            os.remove(p)

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
    parser = argparse.ArgumentParser(description=u"\u86cb\u7cd5\u6253\u53d1\u72b6\u6001\u6838\u5bf9\u5de5\u5177")
    parser.add_argument("--file", help=u"\u8f93\u5165 JSON \u6587\u4ef6\u8def\u5f84\uff08UTF-8\uff09")
    parser.add_argument("--json", action="store_true", help=u"\u4ee5 JSON \u8f93\u51fa")
    parser.add_argument("--out", help=u"\u7ed3\u679c\u5199\u5165\u6307\u5b9a\u6587\u4ef6")
    parser.add_argument("--selftest", action="store_true", help=u"\u8fd0\u884c\u81ea\u68c0")
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))

    if args.selftest:
        sys.exit(0 if selftest() else 1)

    if not args.file:
        parser.error(u"\u9700\u8981 --file \u6216 --selftest")

    data = load_json(args.file)

    report, summary = build_report(data)
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else report
    out_path = args.out or os.path.join(here, "_last_result.txt")
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write(body)
    print(body)
    print("")
    print(u"\u7ed3\u679c\u5df2\u5199\u5165\uff1a%s" % out_path)


if __name__ == "__main__":
    main()
