# -*- coding: utf-8 -*-
"""\u8fd0\u52a8\u524d\u540e\u62c9\u4f38\u6d41\u7a0b\u987a\u5e8f\u6838\u5bf9\u4e0e\u5242\u91cf\u5224\u5b9a\u5de5\u5177\u3002

\u7528\u6cd5:
  python stretching_routine_check.py --file case.json [--json]
  python stretching_routine_check.py --selftest

\u987a\u5e8f\u6838\u5bf9\u6309\u8f93\u5165\u539f\u5e8f\u53d6\u7d22\u5f15, \u4e0d\u6309\u6b63\u786e\u987a\u5e8f\u91cd\u65b0\u6392\u5217\u540e\u6bd4\u5bf9,
\u5426\u5219\u300c\u5148\u9759\u6001\u62c9\u4f38\u518d\u4e3b\u8fd0\u52a8\u300d\u4f1a\u88ab\u8bef\u5224\u6210\u6b63\u786e\u3002
\u5224\u5b9a\u987a\u5e8f: \u5148\u770b\u771f\u5b9e\u7f3a\u9677(\u987a\u5e8f\u9519\u8bef\u3001\u8fd0\u52a8\u524d\u957f\u65f6\u95f4\u9759\u6001\u62c9\u4f38\u3001\u5f39\u9707\u5f0f\u3001\u5f3a\u5ea6\u8fc7\u75db\u3001
\u6025\u6027\u635f\u4f24\u671f\u62c9\u4f38\u3001\u9ebb\u6728\u653e\u5c04\u75db), \u518d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574\u3002
"""
import argparse
import io
import json
import os
import sys
import tempfile

CORRECT_ORDER = [u"\u52a8\u6001\u70ed\u8eab", u"\u4e3b\u8fd0\u52a8", u"\u9759\u6001\u62c9\u4f38"]

ALIAS = {
    u"\u52a8\u6001\u70ed\u8eab": u"\u52a8\u6001\u70ed\u8eab",
    u"\u70ed\u8eab": u"\u52a8\u6001\u70ed\u8eab",
    u"\u52a8\u6001\u62c9\u4f38": u"\u52a8\u6001\u70ed\u8eab",
    u"\u52a8\u6001\u6d3b\u52a8": u"\u52a8\u6001\u70ed\u8eab",
    u"\u4e3b\u8fd0\u52a8": u"\u4e3b\u8fd0\u52a8",
    u"\u4e3b\u8bad\u7ec3": u"\u4e3b\u8fd0\u52a8",
    u"\u6b63\u5f0f\u8bad\u7ec3": u"\u4e3b\u8fd0\u52a8",
    u"\u8bad\u7ec3": u"\u4e3b\u8fd0\u52a8",
    u"\u9759\u6001\u62c9\u4f38": u"\u9759\u6001\u62c9\u4f38",
    u"\u9759\u6001\u4f38\u5c55": u"\u9759\u6001\u62c9\u4f38",
    u"\u62c9\u4f38": u"\u9759\u6001\u62c9\u4f38",
}

HOLD_MIN = 15.0
HOLD_MAX = 30.0
HOLD_SHORT = 10.0
HOLD_LONG = 60.0
PRE_STATIC_BAD = 30.0
PAIN_BAD = 6.0
TARGET_MIN = 4
WARMUP_MIN = 5.0


def normalize(step):
    s = str(step).strip()
    return ALIAS.get(s)


def take_order(steps):
    """\u6309\u8f93\u5165\u539f\u5e8f\u53d6\u7d22\u5f15, \u4e0d\u505a\u4efb\u4f55\u91cd\u6392\u3002"""
    order = []
    for s in steps or []:
        n = normalize(s)
        if n is not None:
            order.append(n)
    return order


def order_verdict(steps):
    order = take_order(steps)
    if len(order) < 2:
        return None, order, u"\u53ef\u8bc6\u522b\u7684\u6d41\u7a0b\u73af\u8282\u4e0d\u8db3\u4e24\u4e2a\uff0c\u65e0\u6cd5\u6838\u5bf9\u987a\u5e8f"
    idx = [CORRECT_ORDER.index(x) for x in order]
    if idx == sorted(idx):
        return True, order, u"\u987a\u5e8f\u6b63\u786e\uff08%s\uff09" % u" \u2192 ".join(order)
    wrong = []
    for i in range(1, len(idx)):
        if idx[i] < idx[i - 1]:
            wrong.append((order[i - 1], order[i]))
    return False, order, u"\u987a\u5e8f\u9519\u8bef\uff1a%s\u3002\u6b63\u786e\u987a\u5e8f\u5e94\u4e3a %s" % (
        u"\u3001".join(u"%s \u4e4b\u540e\u505a\u4e86 %s" % (a, b) for a, b in wrong),
        u" \u2192 ".join(CORRECT_ORDER))


def hold_verdict(phase, hold):
    if hold is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u9759\u6001\u62c9\u4f38\u4fdd\u6301\u65f6\u957f"
    v = float(hold)
    if phase == "pre":
        if v >= PRE_STATIC_BAD:
            return u"\u4e0d\u5408\u683c", u"\u8fd0\u52a8\u524d\u9759\u6001\u62c9\u4f38\u4fdd\u6301 %g \u79d2\uff0c\u8d85\u8fc7 %g \u79d2\u4f1a\u6682\u65f6\u964d\u4f4e\u529b\u91cf\u4e0e\u7206\u53d1\u8f93\u51fa\uff0c\u8fd0\u52a8\u524d\u5e94\u505a\u52a8\u6001\u70ed\u8eab" % (
                v, PRE_STATIC_BAD)
        return u"\u5408\u683c", u"\u8fd0\u52a8\u524d\u62c9\u4f38\u4fdd\u6301 %g \u79d2\uff0c\u672a\u8d85\u8fc7 %g \u79d2" % (v, PRE_STATIC_BAD)
    if v < HOLD_SHORT:
        return u"\u9700\u6539\u8fdb", u"\u4fdd\u6301 %g \u79d2\u504f\u77ed\uff0c\u4f4e\u4e8e %g \u79d2\u6548\u679c\u4e0d\u8db3" % (v, HOLD_SHORT)
    if v > HOLD_LONG:
        return u"\u9700\u6539\u8fdb", u"\u4fdd\u6301 %g \u79d2\u504f\u957f\uff0c\u8d85\u8fc7 %g \u79d2\u4e0d\u5fc5\u8981\u4e14\u6613\u8fc7\u5ea6" % (v, HOLD_LONG)
    if v < HOLD_MIN:
        return u"\u9700\u6539\u8fdb", u"\u4fdd\u6301 %g \u79d2\uff0c\u5efa\u8bae\u62c9\u5230 %g-%g \u79d2" % (v, HOLD_MIN, HOLD_MAX)
    if v > HOLD_MAX:
        return u"\u9700\u6539\u8fdb", u"\u4fdd\u6301 %g \u79d2\uff0c\u5efa\u8bae\u63a7\u5236\u5728 %g-%g \u79d2" % (v, HOLD_MIN, HOLD_MAX)
    return u"\u5408\u683c", u"\u4fdd\u6301 %g \u79d2\uff0c\u5728 %g-%g \u79d2\u533a\u95f4" % (v, HOLD_MIN, HOLD_MAX)


def pain_verdict(p):
    if p is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u62c9\u4f38\u5f3a\u5ea6\u8bc4\u5206"
    v = float(p)
    if v > PAIN_BAD:
        return u"\u4e0d\u5408\u683c", u"\u5f3a\u5ea6\u8bc4\u5206 %g \u5206\uff0c\u8d85\u8fc7 %g \u5206\u5373\u5c5e\u4e8e\u75bc\u75db\u8303\u56f4\uff0c\u75bc\u75db\u662f\u505c\u6b62\u4fe1\u53f7\u4e0d\u662f\u6709\u6548\u4fe1\u53f7" % (v, PAIN_BAD)
    if v < 3.0:
        return u"\u9700\u6539\u8fdb", u"\u5f3a\u5ea6\u8bc4\u5206 %g \u5206\uff0c\u51e0\u4e4e\u6ca1\u611f\u89c9\uff0c\u53ef\u52a0\u5927\u5e45\u5ea6\u5230\u8f7b\u5fae\u7d27\u7ef7" % v
    return u"\u5408\u683c", u"\u5f3a\u5ea6\u8bc4\u5206 %g \u5206\uff0c\u5728\u8f7b\u5fae\u7d27\u7ef7\u533a\u95f4" % v


def load_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def build_report(data):
    phase = data.get("phase")
    steps = data.get("steps", []) or []
    hold = data.get("hold_seconds")
    sets = data.get("sets")
    pain = data.get("pain_score")
    ballistic = data.get("ballistic")
    warmup = data.get("warmup_minutes")
    targets = data.get("targets", []) or []
    acute = data.get("acute_injury")
    numb = data.get("numbness_or_radiating")
    breath_hold = data.get("breath_holding")

    defects = []
    fine = []
    pending = []

    if phase not in ("pre", "post"):
        pending.append(u"\u9636\u6bb5\u672a\u586b\u6216\u53d6\u503c\u672a\u8bc6\u522b\uff0c\u5e94\u4e3a\u8fd0\u52a8\u524d\u6216\u8fd0\u52a8\u540e")

    ok, order, omsg = order_verdict(steps)
    if ok is False:
        defects.append(omsg)
    elif ok is None:
        pending.append(omsg)

    if acute is True:
        defects.append(u"\u6025\u6027\u635f\u4f24\u671f\uff0848 \u5c0f\u65f6\u5185\uff09\u62c9\u4f38\uff1a\u4f1a\u52a0\u91cd\u51fa\u8840\u4e0e\u80bf\u80c0\uff0c\u8fd9\u9636\u6bb5\u4e0d\u505a\u62c9\u4f38")
    if numb is True:
        defects.append(u"\u62c9\u4f38\u90e8\u4f4d\u6709\u9ebb\u6728\u6216\u653e\u5c04\u75db\uff1a\u53ef\u80fd\u6d89\u53ca\u795e\u7ecf\uff0c\u505c\u6b62\u62c9\u4f38\u5e76\u5c31\u533b\u8bc4\u4f30")
    if ballistic is True:
        defects.append(u"\u4f7f\u7528\u5f39\u9707\u5f0f\u62c9\u4f38\uff1a\u9760\u60ef\u6027\u4e00\u5f39\u4e00\u5f39\u4f1a\u89e6\u53d1\u7275\u5f20\u53cd\u5c04\u5bfc\u81f4\u808c\u8089\u5bf9\u6297\u6027\u6536\u7f29\uff0c\u53cd\u800c\u66f4\u5bb9\u6613\u62c9\u4f24")
    if data.get("forced_by_other") is True:
        defects.append(u"\u7531\u4ed6\u4eba\u5f3a\u884c\u52a0\u538b\u6216\u6273\u62c9\uff1a\u65e0\u6cd5\u611f\u77e5\u5b9e\u9645\u8010\u53d7\uff0c\u5bb9\u6613\u8d85\u8fc7\u7ec4\u7ec7\u627f\u53d7\u8303\u56f4")

    pv, pm = pain_verdict(pain)
    if pv == u"\u4e0d\u5408\u683c":
        defects.append(pm)
    elif pv == u"\u9700\u6539\u8fdb":
        fine.append(pm)
    elif pv == u"\u5f85\u786e\u8ba4":
        pending.append(pm)

    hv, hm = hold_verdict(phase, hold)
    if hv == u"\u4e0d\u5408\u683c":
        defects.append(hm)
    elif hv == u"\u9700\u6539\u8fdb":
        fine.append(hm)
    elif hv == u"\u5f85\u786e\u8ba4":
        pending.append(hm)

    if phase == "pre":
        if u"\u52a8\u6001\u70ed\u8eab" not in order and order:
            fine.append(u"\u8fd0\u52a8\u524d\u6d41\u7a0b\u91cc\u6ca1\u6709\u52a8\u6001\u70ed\u8eab\uff0c\u5e94\u5b89\u6392 5-10 \u5206\u949f\u52a8\u6001\u6d3b\u52a8")
        if warmup is None:
            pending.append(u"\u672a\u63d0\u4f9b\u8fd0\u52a8\u524d\u70ed\u8eab\u65f6\u957f")
        elif float(warmup) < WARMUP_MIN:
            fine.append(u"\u70ed\u8eab %.0f \u5206\u949f\u504f\u77ed\uff0c\u5efa\u8bae 5-10 \u5206\u949f\u5230\u5fae\u5fae\u51fa\u6c57" % float(warmup))
    elif phase == "post":
        if u"\u9759\u6001\u62c9\u4f38" not in order and order:
            fine.append(u"\u8fd0\u52a8\u540e\u6d41\u7a0b\u91cc\u6ca1\u6709\u9759\u6001\u62c9\u4f38\uff0c\u653e\u677e\u73af\u8282\u7f3a\u5931")

    if sets is None:
        pending.append(u"\u672a\u63d0\u4f9b\u6bcf\u4e2a\u808c\u7fa4\u7684\u62c9\u4f38\u7ec4\u6570")
    elif float(sets) < 2.0:
        fine.append(u"\u6bcf\u7ec4\u53ea\u505a %g \u7ec4\uff0c\u5efa\u8bae 2-3 \u7ec4" % float(sets))

    if not targets:
        pending.append(u"\u672a\u63d0\u4f9b\u62c9\u4f38\u808c\u7fa4\u6e05\u5355")
    elif len(targets) < TARGET_MIN:
        fine.append(u"\u53ea\u8986\u76d6 %d \u4e2a\u808c\u7fa4\uff0c\u5efa\u8bae\u8986\u76d6 4-6 \u4e2a\uff0c\u4e0d\u8981\u53ea\u62c9\u6700\u9178\u7684\u4e00\u5904" % len(targets))

    if breath_hold is True:
        fine.append(u"\u62c9\u4f38\u65f6\u618b\u6c14\uff1a\u4f1a\u5347\u9ad8\u8179\u538b\u5e76\u964d\u4f4e\u6548\u679c\uff0c\u5168\u7a0b\u4fdd\u6301\u7f13\u6162\u547c\u5438")

    lines = []
    lines.append("=" * 62)
    lines.append(u"\u62c9\u4f38\u6d41\u7a0b\u987a\u5e8f\u6838\u5bf9\u4e0e\u5242\u91cf\u5224\u5b9a")
    lines.append("=" * 62)
    lines.append(u"\u9636\u6bb5\uff1a%s" % (u"\u8fd0\u52a8\u524d" if phase == "pre" else (u"\u8fd0\u52a8\u540e" if phase == "post" else u"\u672a\u586b")))
    lines.append(u"\u7528\u6237\u586b\u5199\u7684\u6d41\u7a0b\uff08\u539f\u5e8f\uff09\uff1a%s" % (u" \u2192 ".join(str(s) for s in steps) if steps else u"\u672a\u586b"))
    lines.append(u"\u8bc6\u522b\u51fa\u7684\u73af\u8282\uff08\u539f\u5e8f\uff09\uff1a%s" % (u" \u2192 ".join(order) if order else u"\u65e0"))
    lines.append("")
    lines.append(u"[\u4e00] \u987a\u5e8f\u6838\u5bf9")
    lines.append(u"  %s" % omsg)
    lines.append("")
    lines.append(u"[\u4e8c] \u5242\u91cf\u4e0e\u5f3a\u5ea6")
    lines.append(u"  \u4fdd\u6301\u65f6\u957f\uff1a%s \u2014\u2014 %s" % (hv, hm))
    lines.append(u"  \u5f3a\u5ea6\u8bc4\u5206\uff1a%s \u2014\u2014 %s" % (pv, pm))
    lines.append(u"  \u8986\u76d6\u808c\u7fa4\uff1a%s" % (u"\u3001".join(str(t) for t in targets) if targets else u"\u672a\u586b"))
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
    lines.append(u"[\u516d] \u6d41\u7a0b\u5904\u65b9")
    lines.append(u"  1. \u6b63\u786e\u987a\u5e8f\uff1a\u52a8\u6001\u70ed\u8eab \u2192 \u4e3b\u8fd0\u52a8 \u2192 \u9759\u6001\u62c9\u4f38")
    if phase == "pre":
        lines.append(u"  2. \u8fd0\u52a8\u524d\u4ee5\u52a8\u6001\u6d3b\u52a8\u4e3a\u4e3b\uff1a\u6162\u8dd1\u3001\u52a8\u6001\u817f\u6446\u3001\u52a8\u6001\u5f13\u6b65\u8f6c\u4f53\u3001\u80a9\u7ed5\u73af\uff0c5-10 \u5206\u949f")
        lines.append(u"  3. \u8fd0\u52a8\u524d\u4e0d\u505a\u4fdd\u6301 30 \u79d2\u4ee5\u4e0a\u7684\u9759\u6001\u62c9\u4f38")
    else:
        lines.append(u"  2. \u8fd0\u52a8\u540e\u9759\u6001\u62c9\u4f38\uff1a\u7f13\u6162\u5230\u4f4d\u540e\u4fdd\u6301 15-30 \u79d2\uff0c\u6bcf\u4e2a\u808c\u7fa4 2-3 \u7ec4")
        lines.append(u"  3. \u8986\u76d6 4-6 \u4e2a\u808c\u7fa4\uff1a\u5c0f\u817f\u3001\u80a1\u56db\u5934\u3001\u8158\u7ef3\u3001\u81c0\u3001\u9ac2\u8170\u3001\u80f8\u5927")
    lines.append(u"  4. \u5f3a\u5ea6\u63a7\u5236\u5728\u8f7b\u5fae\u7d27\u7ef7\uff0c0-10 \u5206\u4e0d\u8d85\u8fc7 6 \u5206\uff0c\u51fa\u73b0\u523a\u75db\u7acb\u5373\u505c\u6b62")
    lines.append(u"  5. \u5168\u7a0b\u7f13\u6162\u547c\u5438\uff0c\u4e0d\u618b\u6c14\uff0c\u4e0d\u5f39\u9707\uff0c\u4e0d\u8ba9\u4ed6\u4eba\u5f3a\u884c\u52a0\u538b")

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
    lines.append(u"\u63d0\u793a\uff1a\u6025\u6027\u635f\u4f24 48 \u5c0f\u65f6\u5185\u4e0d\u62c9\u4f38\uff1b\u9ebb\u6728\u653e\u5c04\u75db\u3001\u5173\u8282\u80bf\u80c0\u3001\u7591\u4f3c\u6495\u88c2\u65f6\u5c31\u533b\u3002")
    lines.append(u"\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u6d41\u7a0b\u81ea\u67e5\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u533b\u5b66\u8bca\u65ad\u6216\u5eb7\u590d\u65b9\u6848\u3002")
    lines.append("=" * 62)

    summary = {
        "order_ok": ok,
        "order_recognized": order,
        "hold_verdict": hv,
        "pain_verdict": pv,
        "defects": defects,
        "fine": fine,
        "pending": pending,
        "overall": overall,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    ok, _, _ = order_verdict([u"\u52a8\u6001\u70ed\u8eab", u"\u4e3b\u8fd0\u52a8", u"\u9759\u6001\u62c9\u4f38"])
    r.append((u"\u6b63\u5e8f\u6d41\u7a0b\u5224\u6b63\u786e", ok is True))
    ok1, _, _ = order_verdict([u"\u52a8\u6001\u70ed\u8eab", u"\u9759\u6001\u62c9\u4f38"])
    r.append((u"\u5b50\u96c6\u4fdd\u6301\u76f8\u5bf9\u987a\u5e8f\u5224\u6b63\u786e", ok1 is True))
    ok2, o2, m2 = order_verdict([u"\u9759\u6001\u62c9\u4f38", u"\u52a8\u6001\u70ed\u8eab", u"\u4e3b\u8fd0\u52a8"])
    r.append((u"\u53cd\u4f8b\uff1a\u5148\u9759\u6001\u518d\u4e3b\u8fd0\u52a8\u5224\u987a\u5e8f\u9519\u8bef", ok2 is False))
    r.append((u"\u53cd\u4f8b\uff1a\u987a\u5e8f\u9519\u8bef\u63d0\u793a\u542b\u6b63\u786e\u987a\u5e8f", u"\u6b63\u786e\u987a\u5e8f\u5e94\u4e3a" in m2))
    r.append((u"\u53cd\u4f8b\uff1a\u8bc6\u522b\u987a\u5e8f\u4fdd\u6301\u8f93\u5165\u539f\u5e8f", o2 == [u"\u9759\u6001\u62c9\u4f38", u"\u52a8\u6001\u70ed\u8eab", u"\u4e3b\u8fd0\u52a8"]))
    ok3, _, _ = order_verdict([u"\u9759\u6001\u62c9\u4f38", u"\u4e3b\u8fd0\u52a8"])
    r.append((u"\u53cd\u4f8b\uff1a\u7f3a\u5c11\u52a8\u6001\u70ed\u8eab\u4e14\u9759\u6001\u5728\u524d\u5224\u9519\u8bef", ok3 is False))
    r.append((u"\u73af\u8282\u4e0d\u8db3\u4e24\u4e2a\u65e0\u6cd5\u6838\u5bf9\u987a\u5e8f", order_verdict([u"\u9759\u6001\u62c9\u4f38"])[0] is None))
    r.append((u"\u522b\u540d\u5f52\u4e00\u5316", normalize(u"\u70ed\u8eab") == u"\u52a8\u6001\u70ed\u8eab"))

    r.append((u"\u53cd\u4f8b\uff1a\u8fd0\u52a8\u524d\u9759\u6001\u62c9\u4f38 60 \u79d2\u5224\u4e0d\u5408\u683c", hold_verdict("pre", 60)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u8fd0\u52a8\u540e\u4fdd\u6301 20 \u79d2\u5224\u5408\u683c", hold_verdict("post", 20)[0] == u"\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u4fdd\u6301 5 \u79d2\u5224\u9700\u6539\u8fdb", hold_verdict("post", 5)[0] == u"\u9700\u6539\u8fdb"))
    r.append((u"\u53cd\u4f8b\uff1a\u5f3a\u5ea6 8 \u5206\u5224\u4e0d\u5408\u683c", pain_verdict(8)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u5f3a\u5ea6 4 \u5206\u5224\u5408\u683c", pain_verdict(4)[0] == u"\u5408\u683c"))

    _, s = build_report({
        "phase": "post",
        "steps": [u"\u52a8\u6001\u70ed\u8eab", u"\u4e3b\u8fd0\u52a8", u"\u9759\u6001\u62c9\u4f38"],
        "hold_seconds": 20, "sets": 2, "pain_score": 4,
        "ballistic": False, "warmup_minutes": 10,
        "targets": [u"\u5c0f\u817f\u4e09\u5934\u808c", u"\u80a1\u56db\u5934\u808c", u"\u8158\u7ef3\u808c", u"\u81c0\u808c"],
        "acute_injury": False, "numbness_or_radiating": False, "breath_holding": False,
    })
    r.append((u"\u6807\u51c6\u8fd0\u52a8\u540e\u6837\u4f8b\u5224\u5b9a\u5408\u683c", s["overall"] == u"\u5408\u683c"))

    _, s1 = build_report({
        "phase": "post",
        "steps": [u"\u9759\u6001\u62c9\u4f38", u"\u52a8\u6001\u70ed\u8eab", u"\u4e3b\u8fd0\u52a8"],
        "hold_seconds": 20, "sets": 2, "pain_score": 4,
        "ballistic": False, "warmup_minutes": 10,
        "targets": [u"\u5c0f\u817f\u4e09\u5934\u808c", u"\u80a1\u56db\u5934\u808c", u"\u8158\u7ef3\u808c", u"\u81c0\u808c"],
        "acute_injury": False, "numbness_or_radiating": False,
    })
    r.append((u"\u53cd\u4f8b\uff1a\u987a\u5e8f\u98a0\u5012\u5224\u4e0d\u5408\u683c", s1["overall"] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u987a\u5e8f\u9519\u8bef\u8fdb\u7f3a\u9677\u8868", any(u"\u987a\u5e8f\u9519\u8bef" in d for d in s1["defects"])))

    _, s2 = build_report({
        "phase": "pre",
        "steps": [u"\u9759\u6001\u62c9\u4f38", u"\u4e3b\u8fd0\u52a8"],
        "hold_seconds": 60, "sets": 2, "pain_score": 3,
        "ballistic": False, "warmup_minutes": 8,
        "targets": [u"\u80a1\u56db\u5934\u808c", u"\u8158\u7ef3\u808c", u"\u5c0f\u817f\u4e09\u5934\u808c", u"\u81c0\u808c"],
        "acute_injury": False,
    })
    r.append((u"\u53cd\u4f8b\uff1a\u8fd0\u52a8\u524d\u957f\u65f6\u95f4\u9759\u6001\u62c9\u4f38\u5224\u4e0d\u5408\u683c", s2["overall"] == u"\u4e0d\u5408\u683c"))

    _, s3 = build_report({
        "phase": "post", "steps": [u"\u4e3b\u8fd0\u52a8", u"\u9759\u6001\u62c9\u4f38"],
        "hold_seconds": 20, "sets": 2, "pain_score": 4, "ballistic": True,
        "targets": [u"\u80a1\u56db\u5934\u808c", u"\u8158\u7ef3\u808c", u"\u5c0f\u817f\u4e09\u5934\u808c", u"\u81c0\u808c"],
    })
    r.append((u"\u53cd\u4f8b\uff1a\u5f39\u9707\u5f0f\u62c9\u4f38\u5224\u4e0d\u5408\u683c", s3["overall"] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u5f39\u9707\u5f0f\u8fdb\u7f3a\u9677\u8868", any(u"\u5f39\u9707\u5f0f" in d for d in s3["defects"])))

    _, s4 = build_report({"phase": "post", "ballistic": True})
    r.append((u"\u7f3a\u6d41\u7a0b\u4f46\u6709\u5f39\u9707\u5f0f\u4e0d\u5f97\u5224\u5f85\u786e\u8ba4", s4["overall"] == u"\u4e0d\u5408\u683c"))

    _, s5 = build_report({
        "phase": "post", "steps": [u"\u4e3b\u8fd0\u52a8", u"\u9759\u6001\u62c9\u4f38"],
        "hold_seconds": 20, "sets": 2, "pain_score": 4,
        "acute_injury": True,
        "targets": [u"\u80a1\u56db\u5934\u808c", u"\u8158\u7ef3\u808c", u"\u5c0f\u817f\u4e09\u5934\u808c", u"\u81c0\u808c"],
    })
    r.append((u"\u53cd\u4f8b\uff1a\u6025\u6027\u635f\u4f24\u671f\u62c9\u4f38\u5224\u4e0d\u5408\u683c", s5["overall"] == u"\u4e0d\u5408\u683c"))

    _, s6 = build_report({"phase": "post"})
    r.append((u"\u4ec5\u586b\u9636\u6bb5\u8bb0\u4e3a\u5f85\u786e\u8ba4", s6["overall"] == u"\u5f85\u786e\u8ba4"))

    p = os.path.join(tempfile.gettempdir(), "_stretch_bom_case.json")
    blob = b"\xef\xbb\xbf" + json.dumps({
        "phase": "post", "steps": [u"\u4e3b\u8fd0\u52a8", u"\u9759\u6001\u62c9\u4f38"],
        "hold_seconds": 20, "sets": 2, "pain_score": 4,
    }, ensure_ascii=False).encode("utf-8")
    with open(p, "wb") as f:
        f.write(blob)
    try:
        d = load_json(p)
        r.append((u"UTF-8 BOM \u8f93\u5165\u9996\u952e\u53ef\u8bfb", d.get("phase") == "post"))
        r.append((u"UTF-8 BOM \u8f93\u5165\u5217\u8868\u53ef\u8bfb", d.get("steps")[0] == u"\u4e3b\u8fd0\u52a8"))
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
    parser = argparse.ArgumentParser(description=u"\u62c9\u4f38\u6d41\u7a0b\u987a\u5e8f\u6838\u5bf9\u5de5\u5177")
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

