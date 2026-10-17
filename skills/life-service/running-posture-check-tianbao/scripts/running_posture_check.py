# -*- coding: utf-8 -*-
"""\u8dd1\u6b65\u59ff\u52bf\u6307\u6807\u5224\u5b9a\u4e0e\u8d1f\u8377\u9012\u589e\u6838\u5bf9\u5de5\u5177\u3002

\u7528\u6cd5:
  python running_posture_check.py --file case.json [--json]
  python running_posture_check.py --selftest

\u5224\u5b9a\u987a\u5e8f: \u5148\u770b\u771f\u5b9e\u7f3a\u9677(\u75bc\u75db\u3001\u8de8\u6b65\u3001\u6b65\u9891\u8fc7\u4f4e\u3001\u5782\u76f4\u632f\u5e45\u8d85\u6807\u3001\u5de6\u53f3\u5931\u8861\u3001
\u8170\u524d\u503e\u3001\u89e6\u5730\u65f6\u95f4\u8fc7\u957f\u3001\u8dd1\u91cf\u589e\u5e45\u8d85\u9650), \u518d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574; \u53ea\u586b\u4e86\u90e8\u5206\u6307\u6807
\u4f46\u586b\u4e86\u75bc\u75db\u65f6, \u76f4\u63a5\u5224\u4e0d\u5408\u683c\u800c\u4e0d\u662f\u5f85\u786e\u8ba4\u3002
"""
import argparse
import io
import json
import os
import sys
import tempfile

CADENCE_BAD = 160.0
CADENCE_OK = 170.0
OSC_BAD = 12.0
OSC_OK = 10.0
CONTACT_BAD = 330.0
CONTACT_OK = 300.0
BALANCE_BAD = 3.0
BALANCE_OK = 2.0
GROWTH_LIMIT = 10.0
LONGEST_RATE = 30.0

PAIN_ITEMS = [
    ("knee", u"\u819d\u5173\u8282\u75bc\u75db"),
    ("shin", u"\u5c0f\u817f\u524d\u4fa7\u6216\u5185\u4fa7\u75db"),
    ("achilles", u"\u8ddf\u8171\u75db"),
    ("itb", u"\u819d\u5916\u4fa7\u6216\u5927\u817f\u5916\u4fa7\u75db"),
    ("foot", u"\u8db3\u90e8\u75db"),
    ("hip", u"\u9acb\u90e8\u75db"),
]

LANDING_POS = {
    "under": (u"\u5408\u683c", u"\u843d\u5730\u70b9\u5728\u91cd\u5fc3\u6b63\u4e0b\u65b9"),
    "slightly_ahead": (u"\u5408\u683c", u"\u843d\u5730\u70b9\u7565\u5728\u91cd\u5fc3\u524d\u65b9\uff0c\u5c5e\u4e8e\u53ef\u63a5\u53d7\u8303\u56f4"),
    "ahead": (u"\u4e0d\u5408\u683c", u"\u843d\u5730\u70b9\u660e\u663e\u5728\u91cd\u5fc3\u524d\u65b9\uff1a\u8de8\u6b65\u5239\u8f66\uff0c\u51b2\u51fb\u5168\u90e8\u7531\u819d\u76d6\u627f\u62c5"),
}
TRUNK = {
    "ankle": (u"\u5408\u683c", u"\u4ece\u811a\u8e1d\u6574\u4f53\u5fae\u524d\u503e\uff0c\u59ff\u6001\u6b63\u786e"),
    "upright": (u"\u9700\u6539\u8fdb", u"\u8eaf\u5e72\u8fc7\u4e8e\u76f4\u7acb\uff0c\u53ef\u5c1d\u8bd5\u4ece\u811a\u8e1d\u6574\u4f53\u5fae\u524d\u503e 5-10 \u5ea6"),
    "waist": (u"\u4e0d\u5408\u683c", u"\u4ece\u8170\u90e8\u6298\u4e0b\u53bb\uff1a\u4f1a\u538b\u8feb\u8170\u690e\u5e76\u9650\u5236\u6446\u9acb\uff0c\u5e94\u6539\u4e3a\u4ece\u811a\u8e1d\u6574\u4f53\u524d\u503e"),
}


def num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def cadence_verdict(c):
    if c is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u6b65\u9891"
    if c >= 180.0:
        return u"\u4f18", u"\u6b65\u9891 %g \u6b65/\u5206\u949f\uff0c\u8fbe\u5230\u4f18\u7684\u533a\u95f4" % c
    if c >= CADENCE_OK:
        return u"\u5408\u683c", u"\u6b65\u9891 %g \u6b65/\u5206\u949f\uff0c\u5728 170-180 \u7684\u5b9e\u7528\u533a\u95f4" % c
    if c >= CADENCE_BAD:
        return u"\u9700\u6539\u8fdb", u"\u6b65\u9891 %g \u6b65/\u5206\u949f\uff0c\u591a\u534a\u4f34\u968f\u8de8\u6b65\uff0c\u5148\u63d0 5%% \u518d\u89c2\u5bdf" % c
    return u"\u4e0d\u5408\u683c", u"\u6b65\u9891 %g \u6b65/\u5206\u949f\uff0c\u4f4e\u4e8e 160\uff0c\u51e0\u4e4e\u5fc5\u7136\u4f34\u968f\u843d\u5730\u70b9\u9760\u524d\uff0c\u51b2\u51fb\u663e\u8457\u589e\u5927" % c


def osc_verdict(v):
    if v is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u5782\u76f4\u632f\u5e45"
    if v <= 8.0:
        return u"\u4f18", u"\u5782\u76f4\u632f\u5e45 %g \u5398\u7c73\uff0c\u91cd\u5fc3\u5e73\u7a33" % v
    if v <= OSC_OK:
        return u"\u5408\u683c", u"\u5782\u76f4\u632f\u5e45 %g \u5398\u7c73\uff0c\u5728\u5408\u7406\u533a\u95f4" % v
    if v <= OSC_BAD:
        return u"\u9700\u6539\u8fdb", u"\u5782\u76f4\u632f\u5e45 %g \u5398\u7c73\uff0c\u4e0a\u4e0b\u8d77\u4f0f\u6d6a\u8d39\u80fd\u91cf" % v
    return u"\u4e0d\u5408\u683c", u"\u5782\u76f4\u632f\u5e45 %g \u5398\u7c73\uff0c\u660e\u663e\u5728\u8df3\u800c\u4e0d\u662f\u8dd1" % v


def contact_verdict(v):
    if v is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u89e6\u5730\u65f6\u95f4"
    if v < 250.0:
        return u"\u4f18", u"\u89e6\u5730\u65f6\u95f4 %g \u6beb\u79d2\uff0c\u63a8\u8e6c\u6548\u7387\u9ad8" % v
    if v <= CONTACT_OK:
        return u"\u5408\u683c", u"\u89e6\u5730\u65f6\u95f4 %g \u6beb\u79d2\uff0c\u5728\u5408\u7406\u533a\u95f4" % v
    if v <= CONTACT_BAD:
        return u"\u9700\u6539\u8fdb", u"\u89e6\u5730\u65f6\u95f4 %g \u6beb\u79d2\uff0c\u63a8\u8e6c\u6548\u7387\u504f\u4f4e" % v
    return u"\u4e0d\u5408\u683c", u"\u89e6\u5730\u65f6\u95f4 %g \u6beb\u79d2\uff0c\u8bf4\u660e\u63a8\u8e6c\u6548\u7387\u4f4e\uff0c\u5148\u964d\u901f\u7ec3\u6280\u672f" % v


def balance_verdict(v):
    if v is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u5de6\u53f3\u89e6\u5730\u5e73\u8861\u5dee"
    if v <= BALANCE_OK:
        return u"\u5408\u683c", u"\u5de6\u53f3\u89e6\u5730\u5e73\u8861\u5dee %g%%\uff0c\u5bf9\u79f0\u6027\u826f\u597d" % v
    if v <= BALANCE_BAD:
        return u"\u9700\u6539\u8fdb", u"\u5de6\u53f3\u89e6\u5730\u5e73\u8861\u5dee %g%%\uff0c\u5efa\u8bae\u52a0\u5355\u4fa7\u529b\u91cf\u8bad\u7ec3" % v
    return u"\u4e0d\u5408\u683c", u"\u5de6\u53f3\u89e6\u5730\u5e73\u8861\u5dee %g%%\uff0c\u63d0\u793a\u5355\u4fa7\u529b\u91cf\u6216\u6d3b\u52a8\u5ea6\u4e0d\u5bf9\u79f0" % v


def growth_verdict(cur, prev):
    if cur is None or prev is None:
        return u"\u5f85\u786e\u8ba4", u"\u5468\u8dd1\u91cf\u6216\u4e0a\u5468\u8dd1\u91cf\u672a\u63d0\u4f9b\uff0c\u65e0\u6cd5\u6838\u7b97\u589e\u5e45"
    if prev <= 0:
        return u"\u5f85\u786e\u8ba4", u"\u4e0a\u5468\u8dd1\u91cf\u4e3a 0\uff0c\u65e0\u6cd5\u8ba1\u7b97\u589e\u5e45\u767e\u5206\u6bd4"
    rate = (cur - prev) / prev * 100.0
    if rate <= GROWTH_LIMIT:
        return u"\u5408\u683c", u"\u5468\u8dd1\u91cf\u589e\u5e45 %.1f%%\uff0c\u672a\u8d85\u8fc7 %.0f%% \u4e0a\u9650" % (rate, GROWTH_LIMIT)
    if rate <= 20.0:
        return u"\u9700\u6539\u8fdb", u"\u5468\u8dd1\u91cf\u589e\u5e45 %.1f%%\uff0c\u8d85\u8fc7 %.0f%% \u4e0a\u9650\uff0c\u5efa\u8bae\u56de\u843d" % (rate, GROWTH_LIMIT)
    return u"\u4e0d\u5408\u683c", u"\u5468\u8dd1\u91cf\u589e\u5e45 %.1f%%\uff0c\u8fdc\u8d85 %.0f%% \u4e0a\u9650\uff0c\u8fd9\u662f\u6700\u96c6\u4e2d\u7684\u53d7\u4f24\u7a97\u53e3" % (rate, GROWTH_LIMIT)


def longest_verdict(longest, weekly):
    if longest is None or weekly is None or weekly <= 0:
        return u"\u5f85\u786e\u8ba4", u"\u5355\u6b21\u6700\u957f\u8ddd\u79bb\u6216\u5468\u8dd1\u91cf\u672a\u63d0\u4f9b"
    rate = longest / weekly * 100.0
    if rate <= LONGEST_RATE:
        return u"\u5408\u683c", u"\u5355\u6b21\u6700\u957f\u8ddd\u79bb\u5360\u5468\u8dd1\u91cf %.0f%%\uff0c\u672a\u8d85\u8fc7 %.0f%%" % (rate, LONGEST_RATE)
    return u"\u9700\u6539\u8fdb", u"\u5355\u6b21\u6700\u957f\u8ddd\u79bb\u5360\u5468\u8dd1\u91cf %.0f%%\uff0c\u8d85\u8fc7 %.0f%% \u4e0a\u9650\uff0c\u5efa\u8bae\u62c6\u5206" % (rate, LONGEST_RATE)


def load_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def build_report(data):
    cadence = num(data.get("cadence"))
    osc = num(data.get("vertical_oscillation_cm"))
    contact = num(data.get("ground_contact_ms"))
    balance = num(data.get("balance_diff_pct"))
    weekly = num(data.get("weekly_km"))
    prev = num(data.get("prev_weekly_km"))
    longest = num(data.get("longest_run_km"))
    landing = data.get("landing_position")
    trunk = data.get("trunk_lean")
    arm_cross = data.get("arm_cross")
    head_down = data.get("head_down")
    noise = data.get("foot_strike_noise")
    pain = data.get("pain", {}) or {}
    pain_hit = [name for key, name in PAIN_ITEMS if pain.get(key) is True]

    defects = []
    fine = []
    pending = []

    # \u771f\u5b9e\u7f3a\u9677\u4e00\uff1a\u75bc\u75db\u4f18\u5148
    if pain_hit:
        defects.append(u"\u5b58\u5728\u75bc\u75db\u90e8\u4f4d\uff08%s\uff09\uff1a\u75bc\u75db\u662f\u505c\u8dd1\u4fe1\u53f7\uff0c\u5148\u505c\u8dd1\u5e76\u5c31\u533b\u8bc4\u4f30\uff0c\u4e0d\u8981\u9760\u6539\u59ff\u52bf\u786c\u625b" % (
            u"\u3001".join(pain_hit)))

    lv, lm = LANDING_POS.get(landing, (u"\u5f85\u786e\u8ba4", u"\u843d\u5730\u70b9\u53d6\u503c\u672a\u8bc6\u522b\uff0c\u5e94\u4e3a\u91cd\u5fc3\u4e0b\u65b9\u3001\u7565\u524d\u6216\u660e\u663e\u5728\u524d"))
    if lv == u"\u4e0d\u5408\u683c":
        defects.append(lm)
    elif lv == u"\u5f85\u786e\u8ba4":
        pending.append(lm)

    cv, cm = cadence_verdict(cadence)
    if cv == u"\u4e0d\u5408\u683c":
        defects.append(cm)
    elif cv == u"\u9700\u6539\u8fdb":
        fine.append(cm)
    elif cv == u"\u5f85\u786e\u8ba4":
        pending.append(cm)

    ov, om = osc_verdict(osc)
    if ov == u"\u4e0d\u5408\u683c":
        defects.append(om)
    elif ov == u"\u9700\u6539\u8fdb":
        fine.append(om)
    elif ov == u"\u5f85\u786e\u8ba4":
        pending.append(om)

    bv, bm = balance_verdict(balance)
    if bv == u"\u4e0d\u5408\u683c":
        defects.append(bm)
    elif bv == u"\u9700\u6539\u8fdb":
        fine.append(bm)
    elif bv == u"\u5f85\u786e\u8ba4":
        pending.append(bm)

    tv, tm = TRUNK.get(trunk, (u"\u5f85\u786e\u8ba4", u"\u8eaf\u5e72\u59ff\u6001\u53d6\u503c\u672a\u8bc6\u522b"))
    if tv == u"\u4e0d\u5408\u683c":
        defects.append(tm)
    elif tv == u"\u9700\u6539\u8fdb":
        fine.append(tm)
    elif tv == u"\u5f85\u786e\u8ba4":
        pending.append(tm)

    ctv, ctm = contact_verdict(contact)
    if ctv == u"\u4e0d\u5408\u683c":
        defects.append(ctm)
    elif ctv == u"\u9700\u6539\u8fdb":
        fine.append(ctm)
    elif ctv == u"\u5f85\u786e\u8ba4":
        pending.append(ctm)

    gv, gm = growth_verdict(weekly, prev)
    if gv == u"\u4e0d\u5408\u683c":
        defects.append(gm)
    elif gv == u"\u9700\u6539\u8fdb":
        fine.append(gm)
    elif gv == u"\u5f85\u786e\u8ba4":
        pending.append(gm)

    lvv, lvm = longest_verdict(longest, weekly)
    if lvv == u"\u9700\u6539\u8fdb":
        fine.append(lvm)
    elif lvv == u"\u5f85\u786e\u8ba4":
        pending.append(lvm)

    if arm_cross is True:
        fine.append(u"\u6446\u81c2\u6a2a\u8fc7\u8eab\u4f53\u4e2d\u7ebf\uff1a\u4f1a\u5e26\u52a8\u8eaf\u5e72\u65cb\u8f6c\u6d6a\u8d39\u80fd\u91cf\uff0c\u6539\u4e3a\u524d\u540e\u6446")
    if head_down is True:
        fine.append(u"\u4f4e\u5934\u770b\u811a\uff1a\u4f1a\u6539\u53d8\u9888\u690e\u4e0e\u8eaf\u5e72\u529b\u7ebf\uff0c\u6539\u4e3a\u76ee\u89c6\u524d\u65b9 20-30 \u7c73")
    if noise == "loud":
        fine.append(u"\u843d\u5730\u58f0\u5927\u3001\u6709\u7838\u5730\u611f\uff1a\u591a\u534a\u843d\u5730\u70b9\u9760\u524d\uff0c\u5148\u67e5\u843d\u5730\u70b9\u518d\u8c08\u89e6\u5730\u90e8\u4f4d")

    lines = []
    lines.append("=" * 62)
    lines.append(u"\u8dd1\u6b65\u59ff\u52bf\u6307\u6807\u5224\u5b9a\u4e0e\u8d1f\u8377\u6838\u5bf9")
    lines.append("=" * 62)
    lines.append(u"[\u4e00] \u6307\u6807\u5224\u5b9a")
    lines.append(u"  %-14s %s" % (u"\u843d\u5730\u70b9", u"%s \u2014\u2014 %s" % (lv, lm)))
    lines.append(u"  %-14s %s" % (u"\u6b65\u9891", u"%s \u2014\u2014 %s" % (cv, cm)))
    lines.append(u"  %-14s %s" % (u"\u5782\u76f4\u632f\u5e45", u"%s \u2014\u2014 %s" % (ov, om)))
    lines.append(u"  %-14s %s" % (u"\u89e6\u5730\u65f6\u95f4", u"%s \u2014\u2014 %s" % (ctv, ctm)))
    lines.append(u"  %-14s %s" % (u"\u5de6\u53f3\u5e73\u8861", u"%s \u2014\u2014 %s" % (bv, bm)))
    lines.append(u"  %-14s %s" % (u"\u8eaf\u5e72\u59ff\u6001", u"%s \u2014\u2014 %s" % (tv, tm)))
    lines.append(u"  %-14s %s" % (u"\u8dd1\u91cf\u589e\u5e45", u"%s \u2014\u2014 %s" % (gv, gm)))
    lines.append(u"  %-14s %s" % (u"\u6700\u957f\u5355\u6b21", u"%s \u2014\u2014 %s" % (lvv, lvm)))
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
    lines.append(u"[\u4e94] \u7ea0\u6b63\u4f18\u5148\u7ea7")
    if pain_hit:
        lines.append(u"  0. \u5148\u505c\u8dd1\u5e76\u5c31\u533b\u8bc4\u4f30\uff0c\u75bc\u75db\u671f\u95f4\u4e0d\u505a\u4efb\u4f55\u59ff\u52bf\u7ea0\u6b63")
    if lv == u"\u4e0d\u5408\u683c":
        lines.append(u"  1. \u843d\u5730\u70b9\uff1a\u63d0\u9ad8\u6b65\u9891 5%\uff0c\u539f\u5730\u5c0f\u6b65\u8dd1\u8ddf\u9891\uff0c\u843d\u5730\u70b9\u81ea\u7136\u56de\u5230\u91cd\u5fc3\u4e0b\u65b9")
    elif cv in (u"\u4e0d\u5408\u683c", u"\u9700\u6539\u8fdb"):
        lines.append(u"  1. \u6b65\u9891\uff1a\u8282\u62cd\u5668\u8bbe\u5f53\u524d +5%\uff0c\u8ddf\u9891\u6162\u8dd1 5 \u5206\u949f\uff0c\u6bcf\u5468 3 \u6b21")
    if ov in (u"\u4e0d\u5408\u683c", u"\u9700\u6539\u8fdb"):
        lines.append(u"  2. \u5782\u76f4\u632f\u5e45\uff1a\u60f3\u8c61\u5934\u9876\u6709\u5929\u82b1\u677f\uff0c\u914d\u5408\u6838\u5fc3\u4e0e\u81c0\u4e2d\u808c\u8bad\u7ec3")
    if tv != u"\u5408\u683c":
        lines.append(u"  3. \u8eaf\u5e72\uff1a\u4ece\u811a\u8e1d\u6574\u4f53\u5fae\u524d\u503e\uff0c\u4e0d\u8981\u4ece\u8170\u90e8\u6298")
    if bv in (u"\u4e0d\u5408\u683c", u"\u9700\u6539\u8fdb"):
        lines.append(u"  4. \u5de6\u53f3\u5e73\u8861\uff1a\u52a0\u5355\u4fa7\u529b\u91cf\u8bad\u7ec3\uff0c\u6301\u7eed\u8d85 3%% \u8bf7\u4e13\u4e1a\u4eba\u58eb\u8bc4\u4f30")
    lines.append(u"  5. \u4e00\u6b21\u53ea\u6539\u4e00\u9879\uff0c\u7a33\u5b9a\u4e24\u5468\u518d\u6539\u4e0b\u4e00\u9879")
    lines.append(u"  6. \u4e24\u5468\u540e\u5728\u540c\u6837\u914d\u901f\u4e0e\u8ddd\u79bb\u4e0b\u590d\u6d4b\uff0c\u4fdd\u8bc1\u6570\u636e\u53ef\u6bd4")

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
    lines.append(u"\u63d0\u793a\uff1a\u75bc\u75db\u8fdb\u884c\u6027\u52a0\u91cd\u3001\u591c\u95f4\u75db\u3001\u5173\u8282\u80bf\u80c0\u3001\u8ddf\u8171\u7a81\u53d1\u5267\u75db\u3001\u8dd1\u4e2d\u80f8\u95f7\u5934\u6655\u65f6\u7acb\u5373\u505c\u8dd1\u5c31\u533b\u3002")
    lines.append(u"\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u59ff\u52bf\u81ea\u67e5\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u533b\u5b66\u8bca\u65ad\u6216\u8fd0\u52a8\u5eb7\u590d\u65b9\u6848\u3002")
    lines.append("=" * 62)

    summary = {
        "landing_verdict": lv,
        "cadence_verdict": cv,
        "osc_verdict": ov,
        "contact_verdict": ctv,
        "balance_verdict": bv,
        "trunk_verdict": tv,
        "growth_verdict": gv,
        "pain_hit": pain_hit,
        "defects": defects,
        "fine": fine,
        "pending": pending,
        "overall": overall,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append((u"\u6b65\u9891 180 \u5224\u4f18", cadence_verdict(180)[0] == u"\u4f18"))
    r.append((u"\u6b65\u9891 172 \u5224\u5408\u683c", cadence_verdict(172)[0] == u"\u5408\u683c"))
    r.append((u"\u6b65\u9891 165 \u5224\u9700\u6539\u8fdb", cadence_verdict(165)[0] == u"\u9700\u6539\u8fdb"))
    r.append((u"\u53cd\u4f8b\uff1a\u6b65\u9891 150 \u5224\u4e0d\u5408\u683c", cadence_verdict(150)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u5782\u76f4\u632f\u5e45 13 \u5224\u4e0d\u5408\u683c", osc_verdict(13)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u5de6\u53f3\u5931\u8861 6 \u5224\u4e0d\u5408\u683c", balance_verdict(6)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u89e6\u5730 350 \u6beb\u79d2\u5224\u4e0d\u5408\u683c", contact_verdict(350)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u5468\u589e\u5e45 50 \u5224\u4e0d\u5408\u683c", growth_verdict(45, 30)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u5468\u589e\u5e45 8 \u5224\u5408\u683c", growth_verdict(32.4, 30)[0] == u"\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u5355\u6b21\u5360\u6bd4\u8d85 30 \u5224\u9700\u6539\u8fdb", longest_verdict(20, 40)[0] == u"\u9700\u6539\u8fdb"))
    r.append((u"\u843d\u5730\u70b9\u660e\u663e\u5728\u524d\u5224\u4e0d\u5408\u683c", LANDING_POS["ahead"][0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u8170\u524d\u503e\u5224\u4e0d\u5408\u683c", TRUNK["waist"][0] == u"\u4e0d\u5408\u683c"))

    _, s = build_report({
        "cadence": 174, "vertical_oscillation_cm": 9, "ground_contact_ms": 280,
        "balance_diff_pct": 1.5, "landing_position": "slightly_ahead",
        "trunk_lean": "ankle", "arm_cross": False, "head_down": False,
        "foot_strike_noise": "quiet", "weekly_km": 32, "prev_weekly_km": 30,
        "longest_run_km": 9, "pain": {},
    })
    r.append((u"\u6807\u51c6\u6837\u4f8b\u5224\u5b9a\u5408\u683c", s["overall"] == u"\u5408\u683c"))

    _, s1 = build_report({
        "cadence": 150, "vertical_oscillation_cm": 13, "ground_contact_ms": 300,
        "balance_diff_pct": 6, "landing_position": "ahead",
        "trunk_lean": "waist", "arm_cross": False, "head_down": False,
        "foot_strike_noise": "loud", "weekly_km": 32, "prev_weekly_km": 30,
        "longest_run_km": 9, "pain": {},
    })
    r.append((u"\u53cd\u4f8b\uff1a\u591a\u9879\u59ff\u52bf\u8fdd\u89c4\u5224\u4e0d\u5408\u683c", s1["overall"] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u8de8\u6b65\u8fdb\u7f3a\u9677\u8868", any(u"\u8de8\u6b65\u5239\u8f66" in d for d in s1["defects"])))
    r.append((u"\u53cd\u4f8b\uff1a\u8170\u524d\u503e\u8fdb\u7f3a\u9677\u8868", any(u"\u4ece\u8170\u90e8\u6298" in d for d in s1["defects"])))

    _, s2 = build_report({
        "cadence": 174, "vertical_oscillation_cm": 9, "ground_contact_ms": 280,
        "balance_diff_pct": 1.5, "landing_position": "slightly_ahead",
        "trunk_lean": "ankle", "weekly_km": 32, "prev_weekly_km": 30,
        "longest_run_km": 9, "pain": {"knee": True},
    })
    r.append((u"\u53cd\u4f8b\uff1a\u6709\u75bc\u75db\u5373\u5224\u4e0d\u5408\u683c", s2["overall"] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u75bc\u75db\u8fdb\u7f3a\u9677\u8868\u5e76\u63d0\u793a\u505c\u8dd1", any(u"\u505c\u8dd1" in d for d in s2["defects"])))

    _, s3 = build_report({"pain": {"shin": True}})
    r.append((u"\u7f3a\u6307\u6807\u4f46\u6709\u75bc\u75db\u4e0d\u5f97\u5224\u5f85\u786e\u8ba4", s3["overall"] == u"\u4e0d\u5408\u683c"))

    _, s4 = build_report({"landing_position": "xxx"})
    r.append((u"\u843d\u5730\u70b9\u53d6\u503c\u672a\u8bc6\u522b\u8bb0\u4e3a\u5f85\u786e\u8ba4", any(u"\u843d\u5730\u70b9" in p for p in s4["pending"])))

    _, s5 = build_report({
        "cadence": 174, "vertical_oscillation_cm": 9, "ground_contact_ms": 280,
        "balance_diff_pct": 1.5, "landing_position": "slightly_ahead",
        "trunk_lean": "ankle", "weekly_km": 60, "prev_weekly_km": 30,
        "longest_run_km": 9, "pain": {},
    })
    r.append((u"\u53cd\u4f8b\uff1a\u8dd1\u91cf\u7ffb\u500d\u5224\u4e0d\u5408\u683c", s5["overall"] == u"\u4e0d\u5408\u683c"))

    p = os.path.join(tempfile.gettempdir(), "_running_bom_case.json")
    blob = b"\xef\xbb\xbf" + json.dumps({
        "cadence": 174, "vertical_oscillation_cm": 9, "landing_position": "under",
        "trunk_lean": "ankle", "weekly_km": 30, "prev_weekly_km": 30,
        "longest_run_km": 8, "pain": {},
    }, ensure_ascii=False).encode("utf-8")
    with open(p, "wb") as f:
        f.write(blob)
    try:
        d = load_json(p)
        r.append((u"UTF-8 BOM \u8f93\u5165\u9996\u952e\u53ef\u8bfb", abs(d.get("cadence", 0) - 174.0) < 1e-9))
        r.append((u"UTF-8 BOM \u8f93\u5165\u5d4c\u5957\u7ed3\u6784\u53ef\u8bfb", d.get("pain", {}).get("knee") is None))
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
    parser = argparse.ArgumentParser(description=u"\u8dd1\u6b65\u59ff\u52bf\u6307\u6807\u5224\u5b9a\u5de5\u5177")
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

