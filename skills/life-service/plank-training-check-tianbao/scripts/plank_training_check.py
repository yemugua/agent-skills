# -*- coding: utf-8 -*-
"""\u5e73\u677f\u652f\u6491\u59ff\u52bf\u6807\u51c6\u4e0e\u5242\u91cf\u6838\u5bf9\u5de5\u5177\u3002

\u7528\u6cd5:
  python plank_training_check.py --file case.json [--json]
  python plank_training_check.py --selftest

\u6838\u5fc3\u5224\u5b9a\u539f\u5219: \u59ff\u52bf\u4e0d\u5408\u683c\u65f6, \u5355\u6b21\u65f6\u957f\u518d\u957f\u4e5f\u4e0d\u8ba1\u5165\u6210\u7ee9\u3002
\u5224\u5b9a\u987a\u5e8f: \u5148\u770b\u771f\u5b9e\u7f3a\u9677(\u584c\u8170\u3001\u6485\u81c0\u3001\u8098\u4f4d\u4e0d\u5bf9\u3001\u6838\u5fc3\u6ca1\u6536\u7d27\u3001\u618b\u6c14\u3001
\u75bc\u75db\u3001\u5355\u6b21\u8d85\u957f), \u518d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574; \u53ea\u586b\u4e86\u59ff\u52bf\u5374\u6ca1\u586b\u65f6\u957f\u65f6,
\u59ff\u52bf\u95ee\u9898\u4ecd\u5224\u4e0d\u5408\u683c\u800c\u4e0d\u662f\u5f85\u786e\u8ba4\u3002
"""
import argparse
import io
import json
import os
import sys
import tempfile

HOLD_MIN = 20.0
HOLD_MAX = 60.0
HOLD_BAD = 120.0
HOLD_SHORT = 10.0
SETS_MIN = 2.0
SETS_MAX = 4.0
REST_MIN = 30.0

POSTURE_ITEMS = [
    ("elbow_under_shoulder", u"\u8098\u5728\u80a9\u6b63\u4e0b\u65b9", False,
     u"\u8098\u90e8\u8dd1\u5230\u80a9\u524d\u65b9\u4f1a\u8ba9\u80a9\u5173\u8282\u627f\u62c5\u5927\u90e8\u5206\u8d1f\u8377\uff0c\u662f\u80a9\u75db\u7684\u5e38\u89c1\u6765\u6e90"),
    ("body_line", u"\u5934\u80a9\u9acb\u819d\u8e1d\u6210\u4e00\u6761\u76f4\u7ebf", False,
     u"\u8eab\u4f53\u4e0d\u6210\u76f4\u7ebf\u8bf4\u660e\u6838\u5fc3\u4e0e\u4e0b\u80a2\u652f\u6491\u6ca1\u6709\u8fde\u6210\u6574\u4f53"),
    ("no_hip_sag", u"\u65e0\u584c\u8170\uff08\u8170\u90e8\u4e0b\u6c89\uff09", False,
     u"\u584c\u8170\u8bf4\u660e\u6838\u5fc3\u5df2\u7ecf\u5931\u5b88\uff0c\u8d1f\u8377\u5168\u7531\u8170\u690e\u627f\u62c5\uff0c\u5e94\u7acb\u5373\u7ed3\u675f\u8be5\u7ec4"),
    ("no_hip_up", u"\u65e0\u6485\u81c0\uff08\u81c0\u90e8\u62ac\u9ad8\uff09", False,
     u"\u6485\u81c0\u65f6\u6838\u5fc3\u51e0\u4e4e\u4e0d\u53c2\u4e0e\uff0c\u7b49\u4e8e\u767d\u505a"),
    ("core_engaged", u"\u6838\u5fc3\u6536\u7d27", False,
     u"\u6838\u5fc3\u6ca1\u6536\u7d27\u7684\u52a8\u4f5c\u5931\u53bb\u610f\u4e49\uff0c\u5148\u5728\u4ef0\u5367\u4f4d\u5efa\u7acb\u8179\u90e8\u6536\u7d27\u611f"),
    ("head_neutral", u"\u5934\u9888\u4e2d\u7acb", True,
     u"\u5934\u9888\u4e0b\u5782\u6216\u62ac\u8d77\u4f1a\u6539\u53d8\u8eaf\u5e72\u529b\u7ebf"),
    ("feet_stable", u"\u811a\u8ddf\u540e\u8e6c\u3001\u811a\u4f4d\u7a33\u5b9a", True,
     u"\u811a\u5c16\u70b9\u5730\u4e0d\u7a33\u8bf4\u660e\u4e0b\u80a2\u652f\u6491\u4e0d\u5145\u5206"),
]

PAIN_ITEMS = [
    ("low_back", u"\u8170\u90e8\u75bc\u75db\u6216\u5411\u817f\u90e8\u653e\u5c04"),
    ("shoulder", u"\u80a9\u90e8\u75bc\u75db\u6216\u62ac\u624b\u53d7\u9650"),
    ("abdomen", u"\u8179\u90e8\u7275\u62c9\u75db\u6216\u4e0d\u9002"),
    ("dizzy", u"\u5934\u6655\u3001\u80f8\u95f7\u3001\u773c\u524d\u53d1\u9ed1"),
]


def num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def posture_verdict(posture):
    """\u8fd4\u56de (\u4e0d\u5408\u683c\u9879, \u9700\u6539\u8fdb\u9879, \u672a\u586b\u9879, \u59ff\u52bf\u662f\u5426\u6574\u4f53\u5408\u683c)\u3002"""
    if not posture:
        return [], [], [name for _, name, _, _ in POSTURE_ITEMS], None
    bad = []
    warn = []
    unknown = []
    for key, name, is_warn, why in POSTURE_ITEMS:
        v = posture.get(key)
        if v is None:
            unknown.append(name)
        elif v is False:
            if is_warn:
                warn.append((name, why))
            else:
                bad.append((name, why))
    ok = (not bad) and (not unknown)
    return bad, warn, unknown, ok


def hold_verdict(hold, posture_ok):
    if hold is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u5355\u6b21\u652f\u6491\u65f6\u957f"
    v = float(hold)
    if posture_ok is False:
        return u"\u4e0d\u5408\u683c", u"\u5355\u6b21 %g \u79d2\uff1a\u59ff\u52bf\u4e0d\u5408\u683c\uff0c\u8be5\u7ec4\u65f6\u957f\u4e0d\u8ba1\u5165\u6210\u7ee9\uff0c\u7ec3\u7684\u662f\u4ee3\u507f\u800c\u4e0d\u662f\u6838\u5fc3" % v
    if v > HOLD_BAD:
        return u"\u4e0d\u5408\u683c", u"\u5355\u6b21 %g \u79d2\uff0c\u8d85\u8fc7 %g \u79d2\uff1a\u7edd\u5927\u591a\u6570\u4eba\u6b64\u65f6\u59ff\u52bf\u5df2\u53d8\u5f62\uff0c\u5e94\u505a\u8fdb\u9636\u52a8\u4f5c\u800c\u4e0d\u662f\u62c9\u957f\u65f6\u957f" % (
            v, HOLD_BAD)
    if v < HOLD_SHORT:
        return u"\u9700\u6539\u8fdb", u"\u5355\u6b21 %g \u79d2\u504f\u77ed\uff0c\u53ef\u5148\u9000\u9636\u5230\u8dea\u59ff\u6216\u4e0a\u659c\u7248\u672c" % v
    if v < HOLD_MIN:
        return u"\u9700\u6539\u8fdb", u"\u5355\u6b21 %g \u79d2\uff0c\u76ee\u6807\u5411 %g-%g \u79d2\u63a8\u8fdb" % (v, HOLD_MIN, HOLD_MAX)
    if v > HOLD_MAX:
        return u"\u9700\u6539\u8fdb", u"\u5355\u6b21 %g \u79d2\u8d85\u8fc7\u8fdb\u9636\u533a\u95f4\uff0c\u5efa\u8bae\u6539\u62ac\u624b\u6216\u62ac\u811a\u7b49\u8fdb\u9636\u52a8\u4f5c" % v
    return u"\u5408\u683c", u"\u5355\u6b21 %g \u79d2\uff0c\u5728 %g-%g \u79d2\u533a\u95f4" % (v, HOLD_MIN, HOLD_MAX)


def sets_verdict(sets):
    if sets is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u7ec4\u6570"
    v = float(sets)
    if v < SETS_MIN:
        return u"\u9700\u6539\u8fdb", u"\u53ea\u505a %g \u7ec4\uff0c\u5efa\u8bae %g-%g \u7ec4" % (v, SETS_MIN, SETS_MAX)
    if v > SETS_MAX:
        return u"\u9700\u6539\u8fdb", u"\u505a %g \u7ec4\u504f\u591a\uff0c\u6ce8\u610f\u603b\u8bad\u7ec3\u91cf" % v
    return u"\u5408\u683c", u"%g \u7ec4\uff0c\u5728 %g-%g \u7ec4\u533a\u95f4" % (v, SETS_MIN, SETS_MAX)


def rest_verdict(rest):
    if rest is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u7ec4\u95f4\u4f11\u606f\u65f6\u957f"
    v = float(rest)
    if v < REST_MIN:
        return u"\u9700\u6539\u8fdb", u"\u7ec4\u95f4\u4f11\u606f %g \u79d2\u504f\u77ed\uff0c\u5efa\u8bae 30-60 \u79d2" % v
    if v > 120.0:
        return u"\u9700\u6539\u8fdb", u"\u7ec4\u95f4\u4f11\u606f %g \u79d2\u504f\u957f\uff0c\u53ef\u538b\u5230 30-60 \u79d2" % v
    return u"\u5408\u683c", u"\u7ec4\u95f4\u4f11\u606f %g \u79d2\uff0c\u5728\u5408\u7406\u533a\u95f4" % v


def build_report(data):
    posture = data.get("posture", {}) or {}
    hold = num(data.get("hold_seconds"))
    sets = num(data.get("sets"))
    rest = num(data.get("rest_sec"))
    breath = data.get("breath_holding")
    pain = data.get("pain", {}) or {}

    bad, warn, unknown, posture_ok = posture_verdict(posture)
    pain_hit = [name for key, name in PAIN_ITEMS if pain.get(key) is True]

    defects = []
    fine = []
    pending = []

    for name, why in bad:
        defects.append(u"\u59ff\u52bf\u4e0d\u5408\u683c\uff1a%s \u2014\u2014 %s" % (name, why))
    for name in unknown:
        pending.append(u"\u59ff\u52bf\u9879\u672a\u586b\uff1a%s" % name)

    if pain_hit:
        defects.append(u"\u5b58\u5728\u4e0d\u9002\uff08%s\uff09\uff1a\u505c\u6b62\u7ec3\u4e60\u5e76\u5c31\u533b\u8bc4\u4f30\uff0c\u4e0d\u8981\u9760\u8c03\u6574\u59ff\u52bf\u786c\u6491" % u"\u3001".join(pain_hit))
    if breath is True:
        defects.append(u"\u618b\u6c14\uff1a\u4f1a\u5347\u9ad8\u8840\u538b\u3001\u52a0\u5feb\u75b2\u52b3\uff0c\u8fd8\u4f1a\u8ba9\u6838\u5fc3\u66f4\u96be\u7ef4\u6301\uff0c\u5168\u7a0b\u6b63\u5e38\u547c\u5438")

    hv, hm = hold_verdict(hold, posture_ok)
    if hv == u"\u4e0d\u5408\u683c":
        defects.append(hm)
    elif hv == u"\u9700\u6539\u8fdb":
        fine.append(hm)
    elif hv == u"\u5f85\u786e\u8ba4":
        pending.append(hm)

    sv, sm = sets_verdict(sets)
    if sv == u"\u9700\u6539\u8fdb":
        fine.append(sm)
    elif sv == u"\u5f85\u786e\u8ba4":
        pending.append(sm)

    rv, rm = rest_verdict(rest)
    if rv == u"\u9700\u6539\u8fdb":
        fine.append(rm)
    elif rv == u"\u5f85\u786e\u8ba4":
        pending.append(rm)

    for name, why in warn:
        fine.append(u"\u59ff\u52bf\u9700\u6539\u8fdb\uff1a%s \u2014\u2014 %s" % (name, why))

    counted = (hold is not None and posture_ok is True and hv == u"\u5408\u683c")

    lines = []
    lines.append("=" * 62)
    lines.append(u"\u5e73\u677f\u652f\u6491\u59ff\u52bf\u4e0e\u5242\u91cf\u6838\u5bf9")
    lines.append("=" * 62)
    lines.append(u"\u5355\u6b21\u65f6\u957f\uff1a%s \u79d2    \u7ec4\u6570\uff1a%s    \u7ec4\u95f4\u4f11\u606f\uff1a%s \u79d2" % (
        (u"%g" % hold) if hold is not None else u"--",
        (u"%g" % sets) if sets is not None else u"--",
        (u"%g" % rest) if rest is not None else u"--"))
    lines.append("")
    lines.append(u"[\u4e00] \u59ff\u52bf\u5224\u5b9a")
    if posture_ok is None:
        lines.append(u"  \u672a\u586b\u4efb\u4f55\u59ff\u52bf\u9879\uff0c\u65e0\u6cd5\u5224\u5b9a")
    else:
        lines.append(u"  \u59ff\u52bf\u6574\u4f53\uff1a%s" % (u"\u5408\u683c" if posture_ok else u"\u4e0d\u5408\u683c"))
        for name, why in bad:
            lines.append(u"    \u4e0d\u5408\u683c\uff1a%s \u2014\u2014 %s" % (name, why))
        for name, why in warn:
            lines.append(u"    \u9700\u6539\u8fdb\uff1a%s \u2014\u2014 %s" % (name, why))
    lines.append(u"  \u547c\u5438\uff1a%s" % (u"\u618b\u6c14\uff08\u4e0d\u5408\u683c\uff09" if breath is True else u"\u672a\u89c1\u618b\u6c14"))
    lines.append("")
    lines.append(u"[\u4e8c] \u65f6\u957f\u4e0e\u7ec4\u6570")
    lines.append(u"  \u65f6\u957f\u5224\u5b9a\uff1a%s \u2014\u2014 %s" % (hv, hm))
    lines.append(u"  \u7ec4\u6570\u5224\u5b9a\uff1a%s \u2014\u2014 %s" % (sv, sm))
    lines.append(u"  \u4f11\u606f\u5224\u5b9a\uff1a%s \u2014\u2014 %s" % (rv, rm))
    lines.append(u"  \u672c\u6b21\u662f\u5426\u8ba1\u5165\u6210\u7ee9\uff1a%s" % (u"\u662f" if counted else u"\u5426"))
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
    lines.append(u"[\u516d] \u5904\u65b9")
    lines.append(u"  1. \u8098\u5728\u80a9\u6b63\u4e0b\u65b9\uff0c\u524d\u81c2\u4e0e\u80a9\u540c\u5bbd\uff0c\u5934\u80a9\u9acb\u819d\u8e1d\u6210\u4e00\u6761\u76f4\u7ebf")
    if any(n == u"\u65e0\u584c\u8170\uff08\u8170\u90e8\u4e0b\u6c89\uff09" for n, _ in bad):
        lines.append(u"  2. \u584c\u8170\uff1a\u7acb\u5373\u7ed3\u675f\u8be5\u7ec4\uff0c\u6539\u8dea\u59ff\u6216\u4e0a\u659c\u7248\u672c\u91cd\u5efa\u6838\u5fc3\u5f20\u529b")
    elif any(n == u"\u65e0\u6485\u81c0\uff08\u81c0\u90e8\u62ac\u9ad8\uff09" for n, _ in bad):
        lines.append(u"  2. \u6485\u81c0\uff1a\u628a\u81c0\u964d\u5230\u4e0e\u80a9\u540c\u9ad8\uff0c\u7f29\u77ed\u65f6\u957f")
    else:
        lines.append(u"  2. \u6838\u5fc3\u6536\u7d27\uff1a\u809a\u8110\u5411\u810a\u67f1\u65b9\u5411\u6536\uff0c\u4e0d\u662f\u628a\u8170\u5f80\u4e0b\u538b")
    lines.append(u"  3. \u5168\u7a0b\u6b63\u5e38\u547c\u5438\uff0c\u7528 3-4 \u79d2\u4e00\u5438\u30013-4 \u79d2\u4e00\u547c\u7684\u6162\u8282\u594f")
    lines.append(u"  4. \u5242\u91cf\uff1a\u6807\u51c6\u59ff\u52bf 3 \u7ec4 \u00d7 20-40 \u79d2\uff0c\u7ec4\u95f4\u4f11\u606f 30-60 \u79d2")
    lines.append(u"  5. \u6491\u4e0d\u5230 20 \u79d2\u7528\u8dea\u59ff\u6216\u4e0a\u659c\uff1b\u80fd\u6807\u51c6\u6491\u6ee1 60 \u79d2\u518d\u8003\u8651\u62ac\u624b\u62ac\u811a")
    lines.append(u"  6. \u59ff\u52bf\u53d8\u5f62\u90a3\u4e00\u523b\u5c31\u7ed3\u675f\u8be5\u7ec4\uff0c\u8be5\u7ec4\u65f6\u957f\u4e0d\u8ba1\u5165\u6210\u7ee9")

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
    lines.append(u"\u63d0\u793a\uff1a\u8170\u817f\u653e\u5c04\u75db\u3001\u80a9\u90e8\u591c\u95f4\u75db\u3001\u8179\u90e8\u7275\u62c9\u75db\u3001\u5934\u6655\u80f8\u95f7\u65f6\u7acb\u5373\u505c\u6b62\u5e76\u5c31\u533b\u3002")
    lines.append(u"\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u59ff\u52bf\u81ea\u67e5\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u533b\u5b66\u8bca\u65ad\u6216\u5eb7\u590d\u65b9\u6848\u3002")
    lines.append("=" * 62)

    summary = {
        "posture_ok": posture_ok,
        "posture_bad": [n for n, _ in bad],
        "hold_verdict": hv,
        "counted": counted,
        "defects": defects,
        "fine": fine,
        "pending": pending,
        "overall": overall,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    b, w, u, ok = posture_verdict({})
    r.append((u"\u672a\u586b\u59ff\u52bf\u65f6\u8fd4\u56de None", ok is None and len(u) == len(POSTURE_ITEMS)))
    b1, _, _, ok1 = posture_verdict({
        "elbow_under_shoulder": True, "body_line": True, "no_hip_sag": True,
        "no_hip_up": True, "core_engaged": True, "head_neutral": True, "feet_stable": True})
    r.append((u"\u5168\u5408\u683c\u59ff\u52bf\u5224\u5408\u683c", ok1 is True and not b1))
    b2, _, _, ok2 = posture_verdict({
        "elbow_under_shoulder": True, "body_line": True, "no_hip_sag": False,
        "no_hip_up": True, "core_engaged": True, "head_neutral": True, "feet_stable": True})
    r.append((u"\u53cd\u4f8b\uff1a\u584c\u8170\u5224\u59ff\u52bf\u4e0d\u5408\u683c", ok2 is False))
    r.append((u"\u53cd\u4f8b\uff1a\u584c\u8170\u8fdb\u4e0d\u5408\u683c\u9879", any(u"\u584c\u8170" in n for n, _ in b2)))
    b3, w3, _, ok3 = posture_verdict({
        "elbow_under_shoulder": True, "body_line": True, "no_hip_sag": True,
        "no_hip_up": True, "core_engaged": True, "head_neutral": False, "feet_stable": True})
    r.append((u"\u5934\u9888\u4e0d\u6b63\u53ea\u5224\u9700\u6539\u8fdb", ok3 is True and len(w3) == 1))

    r.append((u"\u53cd\u4f8b\uff1a\u59ff\u52bf\u4e0d\u5408\u683c\u65f6\u957f\u4e0d\u8ba1\u5165", hold_verdict(300, False)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u5355\u6b21 180 \u79d2\u5224\u4e0d\u5408\u683c", hold_verdict(180, True)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u5355\u6b21 30 \u79d2\u5224\u5408\u683c", hold_verdict(30, True)[0] == u"\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u5355\u6b21 5 \u79d2\u5224\u9700\u6539\u8fdb", hold_verdict(5, True)[0] == u"\u9700\u6539\u8fdb"))
    r.append((u"\u53cd\u4f8b\uff1a\u53ea\u505a 1 \u7ec4\u5224\u9700\u6539\u8fdb", sets_verdict(1)[0] == u"\u9700\u6539\u8fdb"))
    r.append((u"\u53cd\u4f8b\uff1a\u7ec4\u95f4\u4f11\u606f 10 \u79d2\u5224\u9700\u6539\u8fdb", rest_verdict(10)[0] == u"\u9700\u6539\u8fdb"))

    _, s = build_report({
        "hold_seconds": 30, "sets": 3, "rest_sec": 45, "breath_holding": False,
        "posture": {"elbow_under_shoulder": True, "body_line": True, "no_hip_sag": True,
                    "no_hip_up": True, "core_engaged": True, "head_neutral": True,
                    "feet_stable": True},
        "pain": {},
    })
    r.append((u"\u6807\u51c6\u6837\u4f8b\u5224\u5b9a\u5408\u683c", s["overall"] == u"\u5408\u683c"))
    r.append((u"\u6807\u51c6\u6837\u4f8b\u65f6\u957f\u8ba1\u5165\u6210\u7ee9", s["counted"] is True))

    _, s1 = build_report({
        "hold_seconds": 300, "sets": 3, "rest_sec": 45, "breath_holding": True,
        "posture": {"elbow_under_shoulder": True, "body_line": True, "no_hip_sag": False,
                    "no_hip_up": True, "core_engaged": True, "head_neutral": True,
                    "feet_stable": True},
        "pain": {},
    })
    r.append((u"\u53cd\u4f8b\uff1a\u584c\u8170\u52a0\u618b\u6c14\u52a0\u8d85\u957f\u5224\u4e0d\u5408\u683c", s1["overall"] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u584c\u8170\u8fdb\u7f3a\u9677\u8868", any(u"\u584c\u8170" in d for d in s1["defects"])))
    r.append((u"\u53cd\u4f8b\uff1a\u8d85\u957f\u65f6\u957f\u4e0d\u8ba1\u5165\u6210\u7ee9", s1["counted"] is False))

    _, s2 = build_report({
        "hold_seconds": 30, "sets": 3, "rest_sec": 45,
        "posture": {"elbow_under_shoulder": True, "body_line": True, "no_hip_sag": True,
                    "no_hip_up": True, "core_engaged": True, "head_neutral": True,
                    "feet_stable": True},
        "pain": {"low_back": True},
    })
    r.append((u"\u53cd\u4f8b\uff1a\u8170\u75db\u5224\u4e0d\u5408\u683c\u5e76\u63d0\u793a\u505c\u6b62", s2["overall"] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u8170\u75db\u8fdb\u7f3a\u9677\u8868", any(u"\u8170\u90e8\u75bc\u75db" in d for d in s2["defects"])))

    _, s3 = build_report({"posture": {"no_hip_sag": False}})
    r.append((u"\u7f3a\u65f6\u957f\u4f46\u6709\u584c\u8170\u4e0d\u5f97\u5224\u5f85\u786e\u8ba4", s3["overall"] == u"\u4e0d\u5408\u683c"))

    _, s4 = build_report({})
    r.append((u"\u5168\u672a\u586b\u8bb0\u4e3a\u5f85\u786e\u8ba4", s4["overall"] == u"\u5f85\u786e\u8ba4"))

    p = os.path.join(tempfile.gettempdir(), "_plank_bom_case.json")
    blob = b"\xef\xbb\xbf" + json.dumps({
        "hold_seconds": 30, "sets": 3, "rest_sec": 45, "breath_holding": False,
        "posture": {"no_hip_sag": True},
    }, ensure_ascii=False).encode("utf-8")
    with open(p, "wb") as f:
        f.write(blob)
    try:
        d = load_json(p)
        r.append((u"UTF-8 BOM \u8f93\u5165\u9996\u952e\u53ef\u8bfb", abs(d.get("hold_seconds", 0) - 30.0) < 1e-9))
        r.append((u"UTF-8 BOM \u8f93\u5165\u5d4c\u5957\u7ed3\u6784\u53ef\u8bfb", d.get("posture", {}).get("no_hip_sag") is True))
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
    parser = argparse.ArgumentParser(description=u"\u5e73\u677f\u652f\u6491\u59ff\u52bf\u4e0e\u5242\u91cf\u6838\u5bf9\u5de5\u5177")
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
