# -*- coding: utf-8 -*-
"""\u624b\u51b2\u5496\u5561\u53c2\u6570\u6838\u5bf9\u4e0e\u98ce\u5473\u5f52\u56e0\u5de5\u5177\u3002

\u7528\u6cd5:
  python pour_over_check.py --file case.json [--json]
  python pour_over_check.py --selftest

\u5224\u5b9a\u987a\u5e8f: \u5148\u770b\u771f\u5b9e\u7f3a\u9677(\u7c89\u6c34\u6bd4\u8d8a\u754c\u3001\u6c34\u6e29\u4e25\u91cd\u504f\u79bb\u3001\u65f6\u957f\u4e25\u91cd\u504f\u79bb\u3001
\u7814\u78e8\u5ea6\u4e25\u91cd\u504f\u79bb\u3001\u95f7\u84b8\u4e0d\u8db3), \u518d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574; \u53ea\u586b\u4e86\u6c34\u6e29\u5374\u4e25\u91cd\u8d85\u6807\u65f6,
\u76f4\u63a5\u5224\u4e0d\u5408\u683c\u800c\u4e0d\u662f\u5f85\u786e\u8ba4\u3002
"""
import argparse
import io
import json
import os
import sys
import tempfile

RATIO_OK = (15.0, 17.0)
RATIO_BAD = (13.0, 19.0)

TEMP_RANGE = {
    "light": (90.0, 94.0),
    "medium": (88.0, 92.0),
    "dark": (85.0, 90.0),
}
ROAST_LABEL = {"light": u"\u6d45\u70d8", "medium": u"\u4e2d\u70d8", "dark": u"\u6df1\u70d8"}

GRIND_INDEX = {"fine": 1, "medium_fine": 2, "medium": 3, "medium_coarse": 4, "coarse": 5}
GRIND_LABEL = {
    "fine": u"\u7ec6", "medium_fine": u"\u4e2d\u7ec6", "medium": u"\u4e2d",
    "medium_coarse": u"\u4e2d\u7c97", "coarse": u"\u7c97",
}
GRIND_IDEAL = {"light": 2, "medium": 3, "dark": 4}

TIME_RATE = (9.0, 12.0)
TIME_SHORT = 0.75
TIME_LONG = 1.30
BLOOM_RATE = (2.0, 3.0)
BLOOM_SEC = (25.0, 45.0)


def num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def ratio_verdict(dose, water):
    if dose is None or water is None or dose <= 0:
        return u"\u5f85\u786e\u8ba4", u"\u7c89\u91cf\u6216\u6c34\u91cf\u672a\u63d0\u4f9b\uff0c\u65e0\u6cd5\u7b97\u7c89\u6c34\u6bd4"
    r = water / dose
    if r < RATIO_BAD[0]:
        return u"\u4e0d\u5408\u683c", u"\u7c89\u6c34\u6bd4 1:%.1f \u8fc7\u6d53\uff08\u4f4e\u4e8e 1:%.0f\uff09\uff0c\u6d53\u5ea6\u8fc7\u9ad8\u4f1a\u63a9\u76d6\u98ce\u5473\u5c42\u6b21" % (r, RATIO_BAD[0])
    if r > RATIO_BAD[1]:
        return u"\u4e0d\u5408\u683c", u"\u7c89\u6c34\u6bd4 1:%.1f \u8fc7\u6de1\uff08\u9ad8\u4e8e 1:%.0f\uff09\uff0c\u6c34\u592a\u591a\u4f1a\u5bfc\u81f4\u6c34\u8584\u5be1\u6de1" % (r, RATIO_BAD[1])
    if r < RATIO_OK[0]:
        return u"\u9700\u6539\u8fdb", u"\u7c89\u6c34\u6bd4 1:%.1f \u504f\u6d53\uff0c\u5e38\u7528\u533a\u95f4\u4e3a 1:%.0f-1:%.0f" % (r, RATIO_OK[0], RATIO_OK[1])
    if r > RATIO_OK[1]:
        return u"\u9700\u6539\u8fdb", u"\u7c89\u6c34\u6bd4 1:%.1f \u504f\u6de1\uff0c\u5e38\u7528\u533a\u95f4\u4e3a 1:%.0f-1:%.0f" % (r, RATIO_OK[0], RATIO_OK[1])
    return u"\u5408\u683c", u"\u7c89\u6c34\u6bd4 1:%.1f\uff0c\u5728\u5e38\u7528\u533a\u95f4\u5185" % r


def temp_verdict(roast, temp):
    if roast not in TEMP_RANGE:
        return u"\u5f85\u786e\u8ba4", u"\u70d8\u7119\u5ea6\u672a\u8bc6\u522b\uff0c\u65e0\u6cd5\u6838\u5bf9\u6c34\u6e29"
    if temp is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u6c34\u6e29"
    lo, hi = TEMP_RANGE[roast]
    v = float(temp)
    if v < lo - 3.0:
        return u"\u4e0d\u5408\u683c", u"%s\u7528 %g \u6444\u6c0f\u5ea6\uff0c\u4f4e\u4e8e %g-%.0f \u533a\u95f4\u4e0b\u9650\u592a\u591a\uff1a\u8403\u53d6\u4e0d\u8db3\uff0c\u5c16\u9178\u6c34\u8584" % (
            ROAST_LABEL[roast], v, lo, hi)
    if v > hi + 3.0:
        return u"\u4e0d\u5408\u683c", u"%s\u7528 %g \u6444\u6c0f\u5ea6\uff0c\u9ad8\u4e8e %g-%.0f \u533a\u95f4\u4e0a\u9650\u592a\u591a\uff1a\u8403\u53d6\u8fc7\u5ea6\uff0c\u82e6\u6da9\u5589\u5e72" % (
            ROAST_LABEL[roast], v, lo, hi)
    if v < lo:
        return u"\u9700\u6539\u8fdb", u"%s\u7528 %g \u6444\u6c0f\u5ea6\uff0c\u7565\u4f4e\u4e8e %g \u5ea6\u4e0b\u9650\uff0c\u53ef\u63d0\u9ad8 2 \u6444\u6c0f\u5ea6" % (ROAST_LABEL[roast], v, lo)
    if v > hi:
        return u"\u9700\u6539\u8fdb", u"%s\u7528 %g \u6444\u6c0f\u5ea6\uff0c\u7565\u9ad8\u4e8e %.0f \u5ea6\u4e0a\u9650\uff0c\u53ef\u964d\u4f4e 2 \u6444\u6c0f\u5ea6" % (ROAST_LABEL[roast], v, hi)
    return u"\u5408\u683c", u"%s\u7528 %g \u6444\u6c0f\u5ea6\uff0c\u5728 %g-%.0f \u533a\u95f4" % (ROAST_LABEL[roast], v, lo, hi)


def time_verdict(dose, total):
    if dose is None or dose <= 0:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u7c89\u91cf\uff0c\u65e0\u6cd5\u63a8\u7b97\u76ee\u6807\u65f6\u957f"
    if total is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u603b\u65f6\u957f"
    lo = TIME_RATE[0] * dose
    hi = TIME_RATE[1] * dose
    v = float(total)
    if v < lo * TIME_SHORT:
        return u"\u4e0d\u5408\u683c", u"\u603b\u65f6\u957f %g \u79d2\uff0c\u8fdc\u4f4e\u4e8e %g \u79d2\u4e0b\u9650\uff1a\u8403\u53d6\u4e0d\u8db3\uff0c\u9178\u8584\u4e14\u6c34\u611f\u91cd" % (v, lo)
    if v > hi * TIME_LONG:
        return u"\u4e0d\u5408\u683c", u"\u603b\u65f6\u957f %g \u79d2\uff0c\u8fdc\u9ad8\u4e8e %g \u79d2\u4e0a\u9650\uff1a\u8403\u53d6\u8fc7\u5ea6\uff0c\u82e6\u6da9\u53d1\u5e72" % (v, hi)
    if v < lo:
        return u"\u9700\u6539\u8fdb", u"\u603b\u65f6\u957f %g \u79d2\uff0c\u4f4e\u4e8e %g \u79d2\u4e0b\u9650\uff0c\u53ef\u5ef6\u957f 15-20 \u79d2" % (v, lo)
    if v > hi:
        return u"\u9700\u6539\u8fdb", u"\u603b\u65f6\u957f %g \u79d2\uff0c\u9ad8\u4e8e %g \u79d2\u4e0a\u9650\uff0c\u53ef\u7f29\u77ed 15-20 \u79d2" % (v, hi)
    return u"\u5408\u683c", u"\u603b\u65f6\u957f %g \u79d2\uff0c\u5728 %g-%g \u79d2\u533a\u95f4" % (v, lo, hi)


def grind_verdict(roast, grind):
    if roast not in GRIND_IDEAL:
        return u"\u5f85\u786e\u8ba4", u"\u70d8\u7119\u5ea6\u672a\u8bc6\u522b\uff0c\u65e0\u6cd5\u6838\u5bf9\u7814\u78e8\u5ea6"
    if grind not in GRIND_INDEX:
        return u"\u5f85\u786e\u8ba4", u"\u7814\u78e8\u5ea6\u53d6\u503c\u672a\u8bc6\u522b\uff0c\u5e94\u4e3a\u7ec6\u3001\u4e2d\u7ec6\u3001\u4e2d\u3001\u4e2d\u7c97\u6216\u7c97"
    d = abs(GRIND_INDEX[grind] - GRIND_IDEAL[roast])
    if d >= 2:
        return u"\u4e0d\u5408\u683c", u"%s\u7528%s\u7814\u78e8\uff0c\u504f\u79bb\u5efa\u8bae\u6863\u4f4d %d \u6863\uff1a\u660e\u663e\u5f71\u54cd\u8403\u53d6\u5747\u5300\u5ea6" % (
            ROAST_LABEL[roast], GRIND_LABEL[grind], d)
    if d == 1:
        return u"\u9700\u6539\u8fdb", u"%s\u7528%s\u7814\u78e8\uff0c\u504f\u79bb\u5efa\u8bae\u6863\u4f4d 1 \u6863\uff0c\u5c5e\u53ef\u8c03\u6574\u8303\u56f4" % (
            ROAST_LABEL[roast], GRIND_LABEL[grind])
    return u"\u5408\u683c", u"%s\u7528%s\u7814\u78e8\uff0c\u4e0e\u5efa\u8bae\u6863\u4f4d\u4e00\u81f4" % (ROAST_LABEL[roast], GRIND_LABEL[grind])


def bloom_verdict(dose, bloom_water, bloom_sec):
    if dose is None or bloom_water is None:
        return u"\u5f85\u786e\u8ba4", u"\u7c89\u91cf\u6216\u95f7\u84b8\u6c34\u91cf\u672a\u63d0\u4f9b"
    lo = BLOOM_RATE[0] * dose
    hi = BLOOM_RATE[1] * dose
    v = float(bloom_water)
    if v < lo:
        return u"\u4e0d\u5408\u683c", u"\u95f7\u84b8\u6c34\u91cf %g \u514b\uff0c\u4f4e\u4e8e\u7c89\u91cf 2 \u500d\u7684 %g \u514b\uff1a\u7c89\u5c42\u6b8b\u7559\u5e72\u7c89\uff0c\u98ce\u5473\u8584\u4e14\u6742" % (v, lo)
    if v > hi:
        return u"\u9700\u6539\u8fdb", u"\u95f7\u84b8\u6c34\u91cf %g \u514b\uff0c\u9ad8\u4e8e\u7c89\u91cf 3 \u500d\u7684 %g \u514b\uff0c\u53ef\u9002\u5f53\u51cf\u5c11" % (v, hi)
    if bloom_sec is None:
        return u"\u5408\u683c", u"\u95f7\u84b8\u6c34\u91cf %g \u514b\u5408\u9002\uff0c\u672a\u63d0\u4f9b\u95f7\u84b8\u65f6\u957f" % v
    s = float(bloom_sec)
    if s < BLOOM_SEC[0]:
        return u"\u9700\u6539\u8fdb", u"\u95f7\u84b8 %g \u79d2\u504f\u77ed\uff0c\u5efa\u8bae %g-%g \u79d2" % (s, BLOOM_SEC[0], BLOOM_SEC[1])
    if s > BLOOM_SEC[1]:
        return u"\u9700\u6539\u8fdb", u"\u95f7\u84b8 %g \u79d2\u504f\u957f\uff0c\u5efa\u8bae %g-%g \u79d2" % (s, BLOOM_SEC[0], BLOOM_SEC[1])
    return u"\u5408\u683c", u"\u95f7\u84b8 %g \u514b\u6c34\u3001%g \u79d2\uff0c\u5747\u5728\u533a\u95f4\u5185" % (v, s)


def taste_advice(taste, temp_v, grind_v, time_v, ratio_v):
    """\u98ce\u5473\u5f52\u56e0: \u8fd4\u56de (\u5f52\u56e0\u5224\u5b9a, \u5efa\u8bae\u5217\u8868)\u3002"""
    if taste is None or taste == "none":
        return u"\u672a\u8bc4\u4ef7", []
    if taste == "sour_thin":
        causes = [n for n, v in ((u"\u6c34\u6e29", temp_v), (u"\u7814\u78e8", grind_v),
                                 (u"\u65f6\u957f", time_v), (u"\u7c89\u6c34\u6bd4", ratio_v)) if v == u"\u9700\u6539\u8fdb" or v == u"\u4e0d\u5408\u683c"]
        tips = [u"\u8403\u53d6\u4e0d\u8db3\uff08\u5c16\u9178\u6c34\u8584\uff09\uff1a\u7814\u78e8\u8c03\u7ec6\u4e00\u6863"]
        tips.append(u"\u7b2c\u4e8c\u6539\uff1a\u6c34\u6e29\u63d0\u9ad8 2 \u6444\u6c0f\u5ea6")
        tips.append(u"\u7b2c\u4e09\u6539\uff1a\u603b\u65f6\u957f\u5ef6\u957f 15-20 \u79d2")
        if causes:
            return u"\u8403\u53d6\u4e0d\u8db3\uff0c\u53c2\u6570\u547d\u4e2d\uff1a%s" % u"\u3001".join(causes), tips
        return u"\u8403\u53d6\u4e0d\u8db3\uff0c\u4f46\u53c2\u6570\u57fa\u672c\u5728\u533a\u95f4\u5185\uff0c\u5148\u67e5\u6ce8\u6c34\u65b9\u5f0f\u662f\u5426\u51b2\u7a7f\u7c89\u58c1", tips
    if taste == "bitter_dry":
        causes = [n for n, v in ((u"\u6c34\u6e29", temp_v), (u"\u7814\u78e8", grind_v),
                                 (u"\u65f6\u957f", time_v), (u"\u7c89\u6c34\u6bd4", ratio_v)) if v == u"\u9700\u6539\u8fdb" or v == u"\u4e0d\u5408\u683c"]
        tips = [u"\u8403\u53d6\u8fc7\u5ea6\uff08\u82e6\u6da9\u5589\u5e72\uff09\uff1a\u7814\u78e8\u8c03\u7c97\u4e00\u6863"]
        tips.append(u"\u7b2c\u4e8c\u6539\uff1a\u6c34\u6e29\u964d\u4f4e 2 \u6444\u6c0f\u5ea6")
        tips.append(u"\u7b2c\u4e09\u6539\uff1a\u603b\u65f6\u957f\u7f29\u77ed 15-20 \u79d2")
        if causes:
            return u"\u8403\u53d6\u8fc7\u5ea6\uff0c\u53c2\u6570\u547d\u4e2d\uff1a%s" % u"\u3001".join(causes), tips
        return u"\u8403\u53d6\u8fc7\u5ea6\uff0c\u4f46\u53c2\u6570\u57fa\u672c\u5728\u533a\u95f4\u5185\uff0c\u5148\u67e5\u662f\u5426\u672a\u64a4\u6ee4\u676f\u5bfc\u81f4\u5c3e\u6bb5\u8fc7\u8403", tips
    if taste == "mixed":
        return u"\u8403\u53d6\u4e0d\u5747\uff08\u53c8\u9178\u53c8\u82e6\uff09\uff1a\u5148\u89c4\u8303\u6ce8\u6c34\u4e0e\u95f7\u84b8\uff0c\u518d\u67e5\u78e8\u8c46\u673a\u51fa\u7c89\u5747\u5300\u5ea6", [
            u"\u95f7\u84b8\u6c34\u91cf\u53d6\u7c89\u91cf 2-3 \u500d\u3001\u95f7\u84b8 25-45 \u79d2",
            u"\u4e2d\u5fc3\u5411\u5916\u753b\u5708\u6ce8\u6c34\uff0c\u907f\u5f00\u6ee4\u7eb8\u8fb9\u7f18\uff0c\u4e0d\u8981\u51b2\u7a7f\u7c89\u58c1",
            u"\u68c0\u67e5\u78e8\u8c46\u673a\u51fa\u7c89\u662f\u5426\u7c97\u7ec6\u4e0d\u5747"]
    return u"\u672a\u8bc6\u522b\u7684\u98ce\u5473\u63cf\u8ff0", []


def load_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def build_report(data):
    dose = num(data.get("dose_g"))
    water = num(data.get("water_g"))
    temp = num(data.get("water_temp_c"))
    roast = data.get("roast")
    grind = data.get("grind")
    total = num(data.get("total_seconds"))
    bloom_w = num(data.get("bloom_water_g"))
    bloom_s = num(data.get("bloom_seconds"))
    segments = num(data.get("segments"))
    preheat = data.get("preheat")
    rinse = data.get("rinse_filter")
    taste = data.get("taste")

    rv, rm = ratio_verdict(dose, water)
    tv, tm = temp_verdict(roast, temp)
    gv, gm = grind_verdict(roast, grind)
    tiv, tim = time_verdict(dose, total)
    bv, bm = bloom_verdict(dose, bloom_w, bloom_s)

    defects = []
    fine = []
    pending = []

    if dose is None:
        pending.append(u"\u672a\u63d0\u4f9b\u7c89\u91cf")
    if water is None:
        pending.append(u"\u672a\u63d0\u4f9b\u6ce8\u6c34\u603b\u91cf")
    if roast not in TEMP_RANGE:
        pending.append(u"\u70d8\u7119\u5ea6\u672a\u586b\u6216\u53d6\u503c\u672a\u8bc6\u522b\uff0c\u5e94\u4e3a\u6d45\u70d8\u3001\u4e2d\u70d8\u6216\u6df1\u70d8")

    for v, m in ((rv, rm), (tv, tm), (gv, gm), (tiv, tim), (bv, bm)):
        if v == u"\u4e0d\u5408\u683c":
            defects.append(m)
        elif v == u"\u9700\u6539\u8fdb":
            fine.append(m)
        elif v == u"\u5f85\u786e\u8ba4":
            pending.append(m)

    if preheat is False:
        fine.append(u"\u672a\u9884\u70ed\u5206\u4eab\u58f6\u4e0e\u6ee4\u676f\uff1a\u6700\u521d\u51e0\u5341\u79d2\u6c34\u6e29\u4f1a\u9aa4\u964d")
    if rinse is False:
        fine.append(u"\u672a\u6da6\u6d17\u6ee4\u7eb8\uff1a\u4f1a\u6709\u7eb8\u5473\u6b8b\u7559")
    if segments is None:
        pending.append(u"\u672a\u63d0\u4f9b\u5206\u6bb5\u6ce8\u6c34\u6b21\u6570")
    elif segments < 2.0:
        fine.append(u"\u53ea\u5206 %g \u6bb5\u6ce8\u6c34\uff0c\u5efa\u8bae\u95f7\u84b8\u540e\u5206 2-4 \u6bb5" % segments)
    elif segments > 5.0:
        fine.append(u"\u5206 %g \u6bb5\u6ce8\u6c34\u504f\u591a\uff0c\u6c34\u4f4d\u6ce2\u52a8\u5927\uff0c\u5efa\u8bae 2-4 \u6bb5" % segments)

    tlabel, ttips = taste_advice(taste, tv, gv, tiv, rv)

    lines = []
    lines.append("=" * 62)
    lines.append(u"\u624b\u51b2\u5496\u5561\u53c2\u6570\u6838\u5bf9\u4e0e\u98ce\u5473\u5f52\u56e0")
    lines.append("=" * 62)
    lines.append(u"\u7c89\u91cf\uff1a%s \u514b    \u6c34\u91cf\uff1a%s \u514b    \u70d8\u7119\u5ea6\uff1a%s" % (
        (u"%g" % dose) if dose is not None else u"--",
        (u"%g" % water) if water is not None else u"--",
        ROAST_LABEL.get(roast, u"\u672a\u8bc6\u522b")))
    lines.append("")
    lines.append(u"[\u4e00] \u53c2\u6570\u5224\u5b9a")
    lines.append(u"  %-8s %s \u2014\u2014 %s" % (u"\u7c89\u6c34\u6bd4", rv, rm))
    lines.append(u"  %-8s %s \u2014\u2014 %s" % (u"\u6c34\u6e29", tv, tm))
    lines.append(u"  %-8s %s \u2014\u2014 %s" % (u"\u7814\u78e8\u5ea6", gv, gm))
    lines.append(u"  %-8s %s \u2014\u2014 %s" % (u"\u603b\u65f6\u957f", tiv, tim))
    lines.append(u"  %-8s %s \u2014\u2014 %s" % (u"\u95f7\u84b8", bv, bm))
    lines.append("")
    lines.append(u"[\u4e8c] \u98ce\u5473\u5f52\u56e0")
    lines.append(u"  %s" % tlabel)
    for t in ttips:
        lines.append(u"    - %s" % t)
    lines.append("")
    lines.append(u"[\u4e09] \u4e0d\u5408\u683c\u9879\u4e0e\u539f\u56e0")
    if defects:
        for i, d in enumerate(defects, 1):
            lines.append(u"  %d. %s" % (i, d))
    else:
        lines.append(u"  \u65e0")
    lines.append("")
    lines.append(u"[\u56db] \u9700\u6539\u8fdb\u9879")
    if fine:
        for i, d in enumerate(fine, 1):
            lines.append(u"  %d. %s" % (i, d))
    else:
        lines.append(u"  \u65e0")
    lines.append("")
    lines.append(u"[\u4e94] \u5f85\u786e\u8ba4\u9879")
    if pending:
        for i, d in enumerate(pending, 1):
            lines.append(u"  %d. %s" % (i, d))
    else:
        lines.append(u"  \u65e0")
    lines.append("")
    lines.append(u"[\u516d] \u8c03\u6574\u5904\u65b9")
    lines.append(u"  1. \u4e00\u6b21\u53ea\u6539\u4e00\u4e2a\u53d8\u91cf\uff0c\u6539\u5b8c\u8fde\u51b2\u4e24\u676f\u786e\u8ba4\uff0c\u518d\u6539\u4e0b\u4e00\u4e2a")
    lines.append(u"  2. \u987a\u5e8f\uff1a\u5148\u6539\u7814\u78e8 \u2192 \u518d\u6539\u6c34\u6e29 \u2192 \u518d\u6539\u65f6\u957f \u2192 \u6700\u540e\u624d\u52a8\u7c89\u6c34\u6bd4")
    lines.append(u"  3. \u8c03\u6574\u5e45\u5ea6\uff1a\u7814\u78e8\u4e00\u6863\u3001\u6c34\u6e29 2 \u6444\u6c0f\u5ea6\u3001\u65f6\u957f 15-20 \u79d2")
    lines.append(u"  4. \u6ce8\u6c34\uff1a\u4e2d\u5fc3\u5411\u5916\u753b\u5708\uff0c\u907f\u5f00\u6ee4\u7eb8\u8fb9\u7f18\uff0c\u4e0d\u8981\u51b2\u7a7f\u7c89\u58c1")
    lines.append(u"  5. \u6c34\u5feb\u6ef4\u5b8c\u5373\u64a4\u8d70\u6ee4\u676f\uff0c\u907f\u514d\u5c3e\u6bb5\u8fc7\u5ea6\u8403\u53d6")
    lines.append(u"  6. \u6392\u67e5\u987a\u5e8f\u5148\u770b\u8c46\u5b50\u65b0\u9c9c\u5ea6\u3001\u51fa\u7c89\u5747\u5300\u5ea6\u3001\u5b9e\u9645\u51fa\u6c34\u6e29\u5ea6")

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
    lines.append(u"\u63d0\u793a\uff1a\u8c46\u5b50\u4e0d\u65b0\u9c9c\u3001\u51fa\u7c89\u4e0d\u5747\u3001\u6c34\u8d28\u6709\u5f02\u5473\u65f6\uff0c\u8c03\u53c2\u6570\u65e0\u6548\uff0c\u5148\u89e3\u51b3\u524d\u63d0\u3002")
    lines.append(u"\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u53c2\u6570\u81ea\u67e5\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u8c46\u5b50\u6216\u5668\u5177\u7684\u54c1\u8d28\u8bc4\u4ef7\u3002")
    lines.append("=" * 62)

    summary = {
        "ratio_verdict": rv,
        "temp_verdict": tv,
        "grind_verdict": gv,
        "time_verdict": tiv,
        "bloom_verdict": bv,
        "taste_label": tlabel,
        "defects": defects,
        "fine": fine,
        "pending": pending,
        "overall": overall,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append((u"\u7c89\u6c34\u6bd4 1:16 \u5224\u5408\u683c", ratio_verdict(15, 240)[0] == u"\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u7c89\u6c34\u6bd4 1:25 \u5224\u4e0d\u5408\u683c", ratio_verdict(15, 375)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u7c89\u6c34\u6bd4 1:10 \u5224\u4e0d\u5408\u683c", ratio_verdict(15, 150)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u7c89\u6c34\u6bd4 1:14 \u5224\u9700\u6539\u8fdb", ratio_verdict(15, 210)[0] == u"\u9700\u6539\u8fdb"))
    r.append((u"\u6d45\u70d8 92 \u5ea6\u5224\u5408\u683c", temp_verdict("light", 92)[0] == u"\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u6d45\u70d8 78 \u5ea6\u5224\u4e0d\u5408\u683c", temp_verdict("light", 78)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u6df1\u70d8 96 \u5ea6\u5224\u4e0d\u5408\u683c", temp_verdict("dark", 96)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u6df1\u70d8 88 \u5ea6\u5224\u5408\u683c", temp_verdict("dark", 88)[0] == u"\u5408\u683c"))
    r.append((u"\u672a\u77e5\u70d8\u7119\u5ea6\u5224\u5f85\u786e\u8ba4", temp_verdict("xxx", 90)[0] == u"\u5f85\u786e\u8ba4"))
    r.append((u"\u65f6\u957f 150 \u79d2\u5224\u5408\u683c", time_verdict(15, 150)[0] == u"\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u65f6\u957f 70 \u79d2\u5224\u4e0d\u5408\u683c", time_verdict(15, 70)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u65f6\u957f 400 \u79d2\u5224\u4e0d\u5408\u683c", time_verdict(15, 400)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u6d45\u70d8\u4e2d\u7ec6\u5224\u5408\u683c", grind_verdict("light", "medium_fine")[0] == u"\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u6df1\u70d8\u7ec6\u78e8\u5224\u4e0d\u5408\u683c", grind_verdict("dark", "fine")[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u4e2d\u70d8\u4e2d\u7ec6\u5224\u9700\u6539\u8fdb", grind_verdict("medium", "medium_fine")[0] == u"\u9700\u6539\u8fdb"))
    r.append((u"\u53cd\u4f8b\uff1a\u95f7\u84b8\u6c34 10 \u514b\u5224\u4e0d\u5408\u683c", bloom_verdict(15, 10, 30)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u95f7\u84b8 30 \u514b 30 \u79d2\u5224\u5408\u683c", bloom_verdict(15, 30, 30)[0] == u"\u5408\u683c"))
    lab, tips = taste_advice("sour_thin", u"\u4e0d\u5408\u683c", u"\u5408\u683c", u"\u5408\u683c", u"\u5408\u683c")
    r.append((u"\u9178\u8584\u5224\u8403\u53d6\u4e0d\u8db3", u"\u8403\u53d6\u4e0d\u8db3" in lab))
    r.append((u"\u9178\u8584\u5904\u65b9\u542b\u8c03\u7ec6\u7814\u78e8", any(u"\u8c03\u7ec6" in t for t in tips)))
    lab2, tips2 = taste_advice("bitter_dry", u"\u5408\u683c", u"\u5408\u683c", u"\u5408\u683c", u"\u5408\u683c")
    r.append((u"\u82e6\u5e72\u5224\u8403\u53d6\u8fc7\u5ea6", u"\u8403\u53d6\u8fc7\u5ea6" in lab2))
    r.append((u"\u82e6\u5e72\u5904\u65b9\u542b\u8c03\u7c97\u7814\u78e8", any(u"\u8c03\u7c97" in t for t in tips2)))

    _, s = build_report({
        "dose_g": 15, "water_g": 240, "water_temp_c": 92, "roast": "light",
        "grind": "medium_fine", "total_seconds": 150, "bloom_water_g": 35,
        "bloom_seconds": 30, "segments": 3, "preheat": True, "rinse_filter": True,
        "taste": "none",
    })
    r.append((u"\u6807\u51c6\u6837\u4f8b\u5224\u5b9a\u5408\u683c", s["overall"] == u"\u5408\u683c"))

    _, s1 = build_report({
        "dose_g": 15, "water_g": 375, "water_temp_c": 96, "roast": "dark",
        "grind": "fine", "total_seconds": 70, "bloom_water_g": 10,
        "bloom_seconds": 10, "segments": 1, "preheat": False, "rinse_filter": False,
        "taste": "sour_thin",
    })
    r.append((u"\u53cd\u4f8b\uff1a\u591a\u9879\u53c2\u6570\u8d8a\u754c\u5224\u4e0d\u5408\u683c", s1["overall"] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u7c89\u6c34\u6bd4\u8fdb\u7f3a\u9677\u8868", any(u"\u7c89\u6c34\u6bd4" in d for d in s1["defects"])))
    r.append((u"\u53cd\u4f8b\uff1a\u95f7\u84b8\u4e0d\u8db3\u8fdb\u7f3a\u9677\u8868", any(u"\u95f7\u84b8\u6c34\u91cf" in d for d in s1["defects"])))

    _, s2 = build_report({"roast": "dark", "water_temp_c": 96})
    r.append((u"\u7f3a\u7c89\u91cf\u4f46\u6c34\u6e29\u4e25\u91cd\u8d85\u6807\u4e0d\u5f97\u5224\u5f85\u786e\u8ba4", s2["overall"] == u"\u4e0d\u5408\u683c"))

    _, s3 = build_report({})
    r.append((u"\u5168\u672a\u586b\u8bb0\u4e3a\u5f85\u786e\u8ba4", s3["overall"] == u"\u5f85\u786e\u8ba4"))

    p = os.path.join(tempfile.gettempdir(), "_coffee_bom_case.json")
    blob = b"\xef\xbb\xbf" + json.dumps({
        "dose_g": 15, "water_g": 240, "water_temp_c": 92, "roast": "light",
        "grind": "medium_fine", "total_seconds": 150,
    }, ensure_ascii=False).encode("utf-8")
    with open(p, "wb") as f:
        f.write(blob)
    try:
        d = load_json(p)
        r.append((u"UTF-8 BOM \u8f93\u5165\u9996\u952e\u53ef\u8bfb", abs(d.get("dose_g", 0) - 15.0) < 1e-9))
        r.append((u"UTF-8 BOM \u8f93\u5165\u5b57\u7b26\u4e32\u952e\u53ef\u8bfb", d.get("roast") == "light"))
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
    parser = argparse.ArgumentParser(description=u"\u624b\u51b2\u5496\u5561\u53c2\u6570\u6838\u5bf9\u5de5\u5177")
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
