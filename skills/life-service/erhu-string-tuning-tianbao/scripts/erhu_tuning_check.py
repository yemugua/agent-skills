# -*- coding: utf-8 -*-
"""\u4e8c\u80e1\u5b9a\u5f26\u6838\u9a8c\u4e0e\u97f3\u51c6\u504f\u5dee\u5224\u5b9a\u5de5\u5177\u3002

\u7528\u6cd5:
  python erhu_tuning_check.py --file case.json [--json]
  python erhu_tuning_check.py --selftest

\u5224\u5b9a\u987a\u5e8f: \u5148\u770b\u771f\u5b9e\u7f3a\u9677(\u5f26\u5e8f\u98a0\u5012\u3001\u4e94\u5ea6\u8d85\u5dee\u3001\u5355\u5f26\u8d85\u5dee\u3001\u8dd1\u5f26\u3001\u5343\u65a4\u8d8a\u754c),
\u518d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574; \u4fe1\u606f\u4e0d\u5168\u53ea\u8bb0\u4e3a\u5f85\u786e\u8ba4, \u4e0d\u63a9\u76d6\u5df2\u67e5\u51fa\u7684\u504f\u5dee\u3002
"""
import argparse
import io
import json
import math
import os
import sys
import tempfile

TUNINGS = {
    "D/A": {"inner": 293.66, "outer": 440.00, "label": u"\u6807\u51c6 D/A\uff08\u5185 d1 \u5916 a1\uff09"},
    "G/D": {"inner": 196.00, "outer": 293.66, "label": u"\u4f4e\u4e94\u5ea6 G/D\uff08\u5185 g \u5916 d1\uff09"},
    "C/G": {"inner": 261.63, "outer": 392.00, "label": u"C/G\uff08\u5185 c1 \u5916 g1\uff09"},
}
TARGET_NAMES = {
    "D/A": {"inner": u"\u5185\u5f26 d1", "outer": u"\u5916\u5f26 a1"},
    "G/D": {"inner": u"\u5185\u5f26 g", "outer": u"\u5916\u5f26 d1"},
    "C/G": {"inner": u"\u5185\u5f26 c1", "outer": u"\u5916\u5f26 g1"},
}
JUST_FIFTH = 1.5
EQUAL_FIFTH = 2 ** (7.0 / 12.0)

# \u5bb9\u5dee\u53e3\u5f84\uff08\u97f3\u5206\uff09
SINGLE_OK = 5.0
SINGLE_FINE = 20.0
FIFTH_OK = 8.0
FIFTH_FINE = 20.0


def cents(measured, target):
    if not measured or not target:
        return None
    return 1200.0 * math.log(float(measured) / float(target), 2)


def single_verdict(c):
    if c is None:
        return u"\u5f85\u786e\u8ba4"
    a = abs(c)
    if a <= SINGLE_OK:
        return u"\u51c6"
    if a <= SINGLE_FINE:
        return u"\u9700\u5fae\u8c03"
    return u"\u4e0d\u5408\u683c"


def fifth_verdict(c):
    if c is None:
        return u"\u5f85\u786e\u8ba4"
    a = abs(c)
    if a <= FIFTH_OK:
        return u"\u51c6"
    if a <= FIFTH_FINE:
        return u"\u9700\u91cd\u5b9a"
    return u"\u4e0d\u5408\u683c"


def peg_advice(name, c):
    if c is None:
        return u"%s\uff1a\u672a\u63d0\u4f9b\u5b9e\u6d4b\u9891\u7387\uff0c\u65e0\u6cd5\u5224\u65ad\u62e7\u5f26\u65b9\u5411" % name
    if c > SINGLE_OK:
        return u"%s\uff1a\u504f\u9ad8 %+.1f \u97f3\u5206\uff0c\u677e\u5bf9\u5e94\u7434\u8f74\uff08\u97f3\u4f1a\u4e0b\u964d\uff09" % (name, c)
    if c < -SINGLE_OK:
        return u"%s\uff1a\u504f\u4f4e %+.1f \u97f3\u5206\uff0c\u7d27\u5bf9\u5e94\u7434\u8f74\uff08\u97f3\u4f1a\u5347\u9ad8\uff09" % (name, c)
    return u"%s\uff1a\u504f\u5dee\u5728\u5bb9\u5dee\u5185\uff0c\u4fdd\u6301\u4e0d\u52a8" % name


def qianjin_verdict(cm):
    if cm is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u5343\u65a4\u6709\u6548\u5f26\u957f"
    v = float(cm)
    if v < 38.0:
        return u"\u4e0d\u5408\u683c", u"\u5343\u65a4\u6709\u6548\u5f26\u957f %g \u5398\u7c73\uff0c\u4f4e\u4e8e 38 \u5398\u7c73\uff0c\u97f3\u8272\u53d1\u95f7\u4e14\u628a\u4f4d\u6324" % v
    if v > 42.0:
        return u"\u4e0d\u5408\u683c", u"\u5343\u65a4\u6709\u6548\u5f26\u957f %g \u5398\u7c73\uff0c\u9ad8\u4e8e 42 \u5398\u7c73\uff0c\u6309\u5f26\u5403\u529b\u4e14\u97f3\u57df\u865a" % v
    return u"\u5408\u683c", u"\u5343\u65a4\u6709\u6548\u5f26\u957f %g \u5398\u7c73\uff0c\u5728 38-42 \u5398\u7c73\u8303\u56f4" % v


def temp_verdict(t):
    if t is None:
        return None
    v = float(t)
    if v < 5.0:
        return u"\u73af\u5883\u6e29\u5ea6 %g \u6444\u6c0f\u5ea6\uff0c\u8fc7\u4f4e\uff0c\u5f26\u4e0e\u87d2\u76ae\u672a\u7a33\u5b9a\uff0c\u9700\u7b49\u7434\u4f53\u9002\u5e94\u540e\u91cd\u5b9a" % v
    if v > 30.0:
        return u"\u73af\u5883\u6e29\u5ea6 %g \u6444\u6c0f\u5ea6\uff0c\u8fc7\u9ad8\uff0c\u5f26\u5f20\u529b\u4e0b\u964d\u97f3\u6613\u8d70\u4f4e\uff0c\u9700\u9891\u7e41\u590d\u6821" % v
    return None


def load_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def build_report(data):
    tuning = data.get("tuning", "D/A")
    spec = TUNINGS.get(tuning)
    names = TARGET_NAMES.get(tuning, TARGET_NAMES["D/A"])
    inner = data.get("inner_freq")
    outer = data.get("outer_freq")
    peg_slip = bool(data.get("peg_slip", False))
    temp = data.get("temperature_c")
    qj = data.get("qianjin_cm")
    temperament = data.get("temperament", "just")

    fifth_target = EQUAL_FIFTH if temperament == "equal" else JUST_FIFTH

    lines = []
    lines.append("=" * 62)
    lines.append(u"\u4e8c\u80e1\u5b9a\u5f26\u6838\u9a8c\u4e0e\u97f3\u51c6\u504f\u5dee\u5224\u5b9a")
    lines.append("=" * 62)
    lines.append(u"\u5b9a\u5f26\u65b9\u6848\uff1a%s" % (spec["label"] if spec else u"\u672a\u8bc6\u522b\uff08%s\uff09\uff0c\u6309\u6807\u51c6 D/A \u57fa\u51c6\u63d0\u793a" % tuning))
    lines.append(u"\u4e94\u5ea6\u57fa\u51c6\uff1a%s\uff08%s\uff09" % (
        u"\u7eaf\u4e94\u5ea6 3:2" if temperament != "equal" else u"\u5e73\u5747\u5f8b\u4e94\u5ea6",
        u"%.4f" % fifth_target))
    lines.append("")

    defects = []
    pending = []
    fine = []

    if spec is None:
        pending.append(u"\u5b9a\u5f26\u65b9\u6848\u672a\u8bc6\u522b\uff0c\u8bf7\u786e\u8ba4\u4f7f\u7528\u7684\u662f\u6807\u51c6 D/A\u3001\u4f4e\u4e94\u5ea6 G/D \u8fd8\u662f C/G")

    # \u771f\u5b9e\u7f3a\u9677\u4e00\uff1a\u5f26\u5e8f\u98a0\u5012
    reversed_order = False
    if inner and outer and float(inner) >= float(outer):
        reversed_order = True
        defects.append(u"\u5185\u5f26\u5b9e\u6d4b %g \u8d6b\u5179\u4e0d\u4f4e\u4e8e\u5916\u5f26\u5b9e\u6d4b %g \u8d6b\u5179\uff0c\u5f26\u5e8f\u98a0\u5012\uff0c\u5185\u5f26\u5fc5\u987b\u4f4e\u4e8e\u5916\u5f26" % (
            float(inner), float(outer)))
    elif not inner or not outer:
        pending.append(u"\u5185\u5f26\u6216\u5916\u5f26\u5b9e\u6d4b\u9891\u7387\u672a\u63d0\u4f9b\uff0c\u65e0\u6cd5\u5b8c\u6210\u4e94\u5ea6\u6821\u9a8c")

    ci = cents(inner, spec["inner"]) if spec else None
    co = cents(outer, spec["outer"]) if spec else None
    cf = None
    if inner and outer and float(inner) > 0:
        cf = cents(float(outer) / float(inner), fifth_target)

    # \u771f\u5b9e\u7f3a\u9677\u4e8c\uff1a\u5355\u5f26\u8d85\u5dee
    if ci is not None:
        v = single_verdict(ci)
        if v == u"\u4e0d\u5408\u683c":
            defects.append(u"%s\u504f\u5dee %+.1f \u97f3\u5206\uff0c\u8d85\u8fc7 %g \u97f3\u5206\u5bb9\u5dee" % (names["inner"], ci, SINGLE_FINE))
        elif v == u"\u9700\u5fae\u8c03":
            fine.append(u"%s\u504f\u5dee %+.1f \u97f3\u5206\uff0c\u9700\u5fae\u8c03" % (names["inner"], ci))
    if co is not None:
        v = single_verdict(co)
        if v == u"\u4e0d\u5408\u683c":
            defects.append(u"%s\u504f\u5dee %+.1f \u97f3\u5206\uff0c\u8d85\u8fc7 %g \u97f3\u5206\u5bb9\u5dee" % (names["outer"], co, SINGLE_FINE))
        elif v == u"\u9700\u5fae\u8c03":
            fine.append(u"%s\u504f\u5dee %+.1f \u97f3\u5206\uff0c\u9700\u5fae\u8c03" % (names["outer"], co))

    # \u771f\u5b9e\u7f3a\u9677\u4e09\uff1a\u4e94\u5ea6\u8d85\u5dee
    if cf is not None:
        v = fifth_verdict(cf)
        ratio = float(outer) / float(inner)
        if v == u"\u4e0d\u5408\u683c":
            defects.append(u"\u4e94\u5ea6\u6bd4\u503c %.4f\uff0c\u504f\u5dee %+.1f \u97f3\u5206\uff0c\u8d85\u8fc7 %g \u97f3\u5206\u5bb9\u5dee" % (ratio, cf, FIFTH_FINE))
        elif v == u"\u9700\u91cd\u5b9a":
            fine.append(u"\u4e94\u5ea6\u6bd4\u503c %.4f\uff0c\u504f\u5dee %+.1f \u97f3\u5206\uff0c\u9700\u91cd\u5b9a" % (ratio, cf))

    # \u771f\u5b9e\u7f3a\u9677\u56db\uff1a\u8dd1\u5f26
    if peg_slip:
        defects.append(u"\u7434\u8f74\u6253\u6ed1\uff0c\u97f3\u5b9a\u4e0d\u4f4f\u3002\u7981\u6b62\u6ef4\u80f6\u6c34\u3001\u7f20\u80f6\u5e26\u3001\u57ab\u7eb8\u7247\uff0c\u5e94\u9000\u5f26\u68c0\u67e5\u8f74\u5b54\u914d\u5408\u5e76\u9001\u4fee")

    # \u771f\u5b9e\u7f3a\u9677\u4e94\uff1a\u5343\u65a4\u8d8a\u754c
    qj_v, qj_msg = qianjin_verdict(qj)
    if qj_v == u"\u4e0d\u5408\u683c":
        defects.append(qj_msg)
    elif qj_v == u"\u5f85\u786e\u8ba4":
        pending.append(qj_msg)

    lines.append(u"[\u4e00] \u504f\u5dee\u660e\u7ec6")
    lines.append(u"%-14s %12s %12s %10s" % (u"\u9879\u76ee", u"\u76ee\u6807\u8d6b\u5179", u"\u5b9e\u6d4b\u8d6b\u5179", u"\u504f\u5dee\u97f3\u5206"))
    lines.append("-" * 62)
    ti = spec["inner"] if spec else 0.0
    to = spec["outer"] if spec else 0.0
    lines.append(u"%-14s %12.2f %12s %10s" % (
        names["inner"], ti, (u"%.2f" % float(inner)) if inner else u"--",
        (u"%+.1f" % ci) if ci is not None else u"--"))
    lines.append(u"%-14s %12.2f %12s %10s" % (
        names["outer"], to, (u"%.2f" % float(outer)) if outer else u"--",
        (u"%+.1f" % co) if co is not None else u"--"))
    lines.append(u"%-14s %12s %12s %10s" % (
        u"\u4e94\u5ea6\u6bd4\u503c", u"%.4f" % fifth_target,
        (u"%.4f" % (float(outer) / float(inner))) if (inner and outer and float(inner) > 0) else u"--",
        (u"%+.1f" % cf) if cf is not None else u"--"))
    lines.append("-" * 62)

    lines.append("")
    lines.append(u"[\u4e8c] \u4e0d\u5408\u683c\u9879\u4e0e\u539f\u56e0")
    if defects:
        for i, d in enumerate(defects, 1):
            lines.append(u"  %d. %s" % (i, d))
    else:
        lines.append(u"  \u65e0")

    lines.append("")
    lines.append(u"[\u4e09] \u9700\u8c03\u6574\u9879")
    if fine:
        for i, d in enumerate(fine, 1):
            lines.append(u"  %d. %s" % (i, d))
    else:
        lines.append(u"  \u65e0")

    lines.append("")
    lines.append(u"[\u56db] \u62e7\u5f26\u65b9\u5411")
    if reversed_order:
        lines.append(u"  \u5f26\u5e8f\u5df2\u98a0\u5012\uff0c\u5148\u786e\u8ba4\u54ea\u6839\u662f\u5185\u5f26\u54ea\u6839\u662f\u5916\u5f26\uff0c\u518d\u8c08\u62e7\u5f26\u65b9\u5411")
    else:
        lines.append(u"  " + peg_advice(names["inner"], ci))
        lines.append(u"  " + peg_advice(names["outer"], co))
    lines.append(u"  \u63d0\u793a\uff1a\u5b9a\u5b8c\u5185\u5f26\u5fc5\u987b\u56de\u6821\u5916\u5f26\uff0c\u518d\u590d\u68c0\u4e94\u5ea6\uff0c\u6765\u56de\u4e24\u5230\u4e09\u8f6e")

    lines.append("")
    lines.append(u"[\u4e94] \u5f85\u786e\u8ba4\u9879")
    if pending:
        for i, d in enumerate(pending, 1):
            lines.append(u"  %d. %s" % (i, d))
    else:
        lines.append(u"  \u65e0")

    tv = temp_verdict(temp)
    lines.append("")
    lines.append(u"[\u516d] \u73af\u5883\u4e0e\u5176\u4ed6\u63d0\u793a")
    if tv:
        lines.append(u"  " + tv)
    lines.append(u"  \u5b9a\u5b8c\u5f26\u62c9\u6ee1 10 \u5206\u949f\u518d\u590d\u6d4b\u4e00\u6b21\uff0c\u4e24\u6b21\u5dee\u503c\u8d85\u8fc7 15 \u97f3\u5206\u8bf4\u660e\u5f26\u6216\u8f74\u6709\u95ee\u9898")
    lines.append(u"  \u4e0d\u63a8\u8350\u7528\u80f6\u6c34\u3001\u80f6\u5e26\u3001\u7eb8\u7247\u56fa\u5b9a\u7434\u8f74\uff0c\u8fd9\u7c7b\u505a\u6cd5\u4f1a\u6269\u5927\u8f74\u5b54\u635f\u4f24")

    if defects:
        overall = u"\u4e0d\u5408\u683c"
    elif fine:
        overall = u"\u9700\u8c03\u6574"
    elif pending:
        overall = u"\u5f85\u786e\u8ba4"
    else:
        overall = u"\u5408\u683c"

    lines.append("")
    lines.append(u"\u603b\u5224\u5b9a\uff1a%s" % overall)
    lines.append(u"\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u5b9a\u5f26\u81ea\u67e5\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u4e50\u5668\u7ef4\u4fee\u7ed3\u8bba\u3002\u5408\u594f\u4ee5\u4e50\u961f\u57fa\u51c6\u97f3\u4e3a\u51c6\u3002")
    lines.append("=" * 62)

    summary = {
        "tuning": tuning,
        "tuning_known": spec is not None,
        "inner_cents": ci,
        "outer_cents": co,
        "fifth_cents": cf,
        "defects": defects,
        "fine": fine,
        "pending": pending,
        "qianjin_verdict": qj_v,
        "overall": overall,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append((u"\u540c\u9891\u504f\u5dee\u4e3a 0", abs(cents(440.0, 440.0)) < 1e-9))
    r.append((u"\u9ad8\u516b\u5ea6\u4e3a 1200 \u97f3\u5206", abs(cents(880.0, 440.0) - 1200.0) < 1e-6))
    r.append((u"\u5e73\u5747\u5f8b\u4e94\u5ea6\u6bd4 1.4983", abs(EQUAL_FIFTH - 1.498307) < 1e-5))
    r.append((u"\u7eaf\u4e94\u5ea6\u4e0e\u5e73\u5747\u5f8b\u76f8\u5dee\u7ea6 2 \u97f3\u5206", abs(cents(EQUAL_FIFTH, JUST_FIFTH) + 1.955) < 0.01))

    _, s = build_report({
        "tuning": "D/A", "inner_freq": 293.7, "outer_freq": 440.1,
        "peg_slip": False, "temperature_c": 24, "qianjin_cm": 40.0,
        "temperament": "just",
    })
    r.append((u"\u6807\u51c6\u5b9a\u5f26\u6837\u4f8b\u5224\u5b9a\u5408\u683c", s["overall"] == u"\u5408\u683c"))

    _, s1 = build_report({
        "tuning": "D/A", "inner_freq": 460.0, "outer_freq": 440.0,
        "peg_slip": False, "temperature_c": 24, "qianjin_cm": 40.0,
    })
    r.append((u"\u53cd\u4f8b\uff1a\u5185\u5f26\u9ad8\u4e8e\u5916\u5f26\u5224\u4e0d\u5408\u683c", s1["overall"] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u5f26\u5e8f\u98a0\u5012\u8fdb\u7f3a\u9677\u8868", any(u"\u5f26\u5e8f\u98a0\u5012" in d for d in s1["defects"])))

    _, s2 = build_report({
        "tuning": "D/A", "inner_freq": 314.0, "outer_freq": 440.0,
        "peg_slip": False, "temperature_c": 24, "qianjin_cm": 40.0,
    })
    r.append((u"\u53cd\u4f8b\uff1a\u4e94\u5ea6\u592a\u7a84\u5224\u4e0d\u5408\u683c", s2["overall"] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u4e94\u5ea6\u8d85\u5dee\u8fdb\u7f3a\u9677\u8868", any(u"\u4e94\u5ea6\u6bd4\u503c" in d for d in s2["defects"])))

    _, s3 = build_report({
        "tuning": "D/A", "inner_freq": 287.0, "outer_freq": 440.0,
        "peg_slip": False, "temperature_c": 24, "qianjin_cm": 40.0,
    })
    r.append((u"\u53cd\u4f8b\uff1a\u5185\u5f26\u504f\u4f4e 40 \u97f3\u5206\u5224\u4e0d\u5408\u683c", s3["overall"] == u"\u4e0d\u5408\u683c"))

    _, s4 = build_report({
        "tuning": "D/A", "inner_freq": 293.7, "outer_freq": 440.1,
        "peg_slip": True, "temperature_c": 24, "qianjin_cm": 40.0,
    })
    r.append((u"\u53cd\u4f8b\uff1a\u7434\u8f74\u6253\u6ed1\u5224\u4e0d\u5408\u683c", s4["overall"] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u6253\u6ed1\u8fdb\u7f3a\u9677\u8868", any(u"\u7434\u8f74\u6253\u6ed1" in d for d in s4["defects"])))

    _, s5 = build_report({
        "tuning": "D/A", "inner_freq": 293.7, "outer_freq": 440.1,
        "peg_slip": False, "temperature_c": 24, "qianjin_cm": 45.0,
    })
    r.append((u"\u53cd\u4f8b\uff1a\u5343\u65a4 45 \u5398\u7c73\u5224\u4e0d\u5408\u683c", s5["overall"] == u"\u4e0d\u5408\u683c"))

    _, s6 = build_report({"tuning": "D/A", "peg_slip": False})
    r.append((u"\u7f3a\u5b9e\u6d4b\u9891\u7387\u8bb0\u4e3a\u5f85\u786e\u8ba4\u800c\u975e\u5408\u683c", s6["overall"] == u"\u5f85\u786e\u8ba4"))
    r.append((u"\u7f3a\u9891\u7387\u8fdb\u5f85\u786e\u8ba4\u8868", len(s6["pending"]) > 0))

    _, s7 = build_report({
        "tuning": "G/D", "inner_freq": 196.0, "outer_freq": 293.7,
        "peg_slip": False, "temperature_c": 24, "qianjin_cm": 40.0,
    })
    r.append((u"\u4f4e\u4e94\u5ea6\u5b9a\u5f26\u6309\u81ea\u8eab\u57fa\u51c6\u5224\u5b9a", s7["overall"] == u"\u5408\u683c"))

    _, s8 = build_report({
        "tuning": "D/A", "inner_freq": 296.0, "outer_freq": 440.0,
        "peg_slip": False, "temperature_c": 24, "qianjin_cm": 40.0,
    })
    r.append((u"\u8f7b\u5fae\u504f\u5dee\u5224\u9700\u8c03\u6574\u800c\u975e\u5408\u683c", s8["overall"] == u"\u9700\u8c03\u6574"))

    _, s9 = build_report({
        "tuning": "X/Y", "inner_freq": 293.66, "outer_freq": 440.0,
        "peg_slip": False, "temperature_c": 24, "qianjin_cm": 40.0,
    })
    r.append((u"\u672a\u8bc6\u522b\u5b9a\u5f26\u65b9\u6848\u8fdb\u5f85\u786e\u8ba4\u8868", any(u"\u672a\u8bc6\u522b" in p for p in s9["pending"])))

    # UTF-8 BOM \u8f93\u5165\u5fc5\u987b\u80fd\u88ab\u6b63\u786e\u89e3\u6790
    p = os.path.join(tempfile.gettempdir(), "_erhu_bom_case.json")
    blob = b"\xef\xbb\xbf" + json.dumps({
        "tuning": "D/A", "inner_freq": 293.66, "outer_freq": 440.0,
        "peg_slip": False, "temperature_c": 24, "qianjin_cm": 40.0,
    }, ensure_ascii=False).encode("utf-8")
    with open(p, "wb") as f:
        f.write(blob)
    try:
        d = load_json(p)
        r.append((u"UTF-8 BOM \u8f93\u5165\u9996\u952e\u53ef\u8bfb", d.get("tuning") == "D/A"))
        r.append((u"UTF-8 BOM \u8f93\u5165\u6570\u503c\u53ef\u8bfb", abs(d.get("inner_freq", 0) - 293.66) < 1e-9))
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
    parser = argparse.ArgumentParser(description=u"\u4e8c\u80e1\u5b9a\u5f26\u6838\u9a8c\u5de5\u5177")
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

