# -*- coding: utf-8 -*-
"""\u94a2\u7434\u6307\u6cd5\u8fdd\u89c4\u68c0\u67e5\u4e0e\u7ec3\u4e60\u5242\u91cf\u6838\u5bf9\u5de5\u5177\u3002

\u7528\u6cd5:
  python piano_fingering_check.py --file case.json [--json]
  python piano_fingering_check.py --selftest

\u5224\u5b9a\u987a\u5e8f: \u5148\u770b\u771f\u5b9e\u7f3a\u9677(\u6307\u6cd5\u8fdd\u89c4\u3001\u97f3\u9636\u6307\u6cd5\u4e0d\u7b26\u3001\u624b\u578b\u4e0d\u5408\u683c\u3001\u51c6\u786e\u7387\u4e0d\u8fbe\u6807\u3001\u63d0\u901f\u8fc7\u65e9),
\u518d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574; \u7f3a\u6307\u6cd5\u6570\u636e\u65f6\u4e0d\u5f97\u63a9\u76d6\u5df2\u67e5\u51fa\u7684\u624b\u578b\u95ee\u9898\u3002
"""
import argparse
import io
import json
import os
import sys
import tempfile

SCALE_FINGERS = {
    ("C", "right"): [1, 2, 3, 1, 2, 3, 4, 5],
    ("C", "left"): [5, 4, 3, 2, 1, 3, 2, 1],
    ("G", "right"): [1, 2, 3, 1, 2, 3, 4, 5],
    ("G", "left"): [5, 4, 3, 2, 1, 3, 2, 1],
    ("D", "right"): [1, 2, 3, 1, 2, 3, 4, 5],
    ("D", "left"): [5, 4, 3, 2, 1, 3, 2, 1],
    ("F", "right"): [1, 2, 3, 4, 1, 2, 3, 4],
    ("Am", "right"): [1, 2, 3, 1, 2, 3, 4, 5],
}

HAND_SHAPE_ITEMS = [
    ("palm_arch", u"\u638c\u5173\u8282\u81ea\u7136\u62f1\u8d77", u"\u624b\u80cc\u5e73\u584c\u3001\u638c\u5173\u8282\u51f9\u9677\uff0c\u9700\u6162\u901f\u65ad\u594f\u91cd\u5efa\u62f1\u5f62"),
    ("knuckle_support", u"\u7b2c\u4e00\u6307\u8282\u4e0d\u584c\u9677", u"\u584c\u6307\u4f1a\u8ba9\u6307\u5c16\u5931\u53bb\u652f\u6491\uff0c\u5f39\u4e0d\u5feb\u4e5f\u5f39\u4e0d\u5300"),
    ("wrist_level", u"\u624b\u8155\u4e0e\u638c\u5173\u8282\u6301\u5e73\u6216\u7565\u9ad8", u"\u624b\u8155\u4f4e\u4e8e\u638c\u5173\u8282\u4f1a\u5361\u6b7b\uff0c\u62ac\u9ad8\u4f1a\u50f5\u786c"),
    ("thumb_bent", u"\u62c7\u6307\u81ea\u7136\u5f2f\u66f2\u4e0d\u5916\u7fd8", u"\u62c7\u6307\u4f38\u76f4\u5916\u7fd8\u4f1a\u5e26\u504f\u540e\u7eed\u6307\u6cd5"),
    ("arm_relaxed", u"\u80a9\u81c2\u653e\u677e\u4e0d\u8038\u80a9", u"\u8038\u80a9\u4f1a\u5bfc\u81f4\u80a9\u9888\u9178\u75db\u4e0e\u8010\u529b\u5dee"),
]

ACC_BAD = 90.0
ACC_SPEED = 95.0
MIN_MINUTES = 15.0
MAX_MINUTES = 60.0
MIN_DAYS = 4.0


def finger_violations(notes):
    """\u6309\u8f93\u5165\u539f\u5e8f\u626b\u63cf, \u4e0d\u505a\u4efb\u4f55\u91cd\u6392\u3002"""
    bad_range = []
    thumb_black = []
    same_run = []
    run = 1
    prev_f = None
    prev_k = None
    for i, n in enumerate(notes, 1):
        f = n.get("finger")
        k = n.get("key")
        black = bool(n.get("black", False))
        if f is None:
            continue
        try:
            fi = int(f)
        except (TypeError, ValueError):
            bad_range.append(i)
            continue
        if fi < 1 or fi > 5:
            bad_range.append(i)
        if fi == 1 and black:
            thumb_black.append(i)
        if prev_f is not None and fi == prev_f and k != prev_k:
            run += 1
            if run >= 3:
                same_run.append(i)
        else:
            run = 1
        prev_f = fi
        prev_k = k
    return bad_range, thumb_black, same_run


def scale_check(scale, hand, notes):
    std = SCALE_FINGERS.get((scale, hand))
    if std is None:
        return None, u"\u6ca1\u6709\u8be5\u8c03\u8be5\u624b\u7684\u6807\u51c6\u6307\u6cd5\u8868\uff0c\u8df3\u8fc7\u6bd4\u5bf9"
    if len(notes) != len(std):
        return None, u"\u97f3\u7b26\u6570 %d \u4e0e\u6807\u51c6\u6307\u6cd5\u957f\u5ea6 %d \u4e0d\u4e00\u81f4\uff0c\u8df3\u8fc7\u6bd4\u5bf9" % (len(notes), len(std))
    actual = []
    for n in notes:
        try:
            actual.append(int(n.get("finger")))
        except (TypeError, ValueError):
            return None, u"\u5b58\u5728\u65e0\u6548\u6307\u53f7\uff0c\u8df3\u8fc7\u6bd4\u5bf9"
    if actual == std:
        return True, u"%s %s \u97f3\u9636\u6307\u6cd5\u4e0e\u6807\u51c6\u8868\u4e00\u81f4" % (scale, hand)
    diff = [i + 1 for i in range(len(std)) if actual[i] != std[i]]
    return False, u"%s %s \u97f3\u9636\u6307\u6cd5\u4e0e\u6807\u51c6\u8868\u4e0d\u4e00\u81f4\uff0c\u7b2c %s \u4e2a\u97f3\u4e0d\u7b26\uff08\u5e94\u4e3a %s\uff09" % (
        scale, hand, u"\u3001".join(str(i) for i in diff), u" ".join(str(x) for x in std))


def speed_verdict(acc, target, actual):
    if acc is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u51c6\u786e\u7387"
    a = float(acc)
    if a < ACC_BAD:
        return u"\u4e0d\u5408\u683c", u"\u51c6\u786e\u7387 %.1f%% \u4f4e\u4e8e %.0f%%\uff0c\u56de\u5230\u5206\u624b\u6162\u7ec3\uff0c\u4e0d\u8981\u5408\u624b\u63d0\u901f" % (a, ACC_BAD)
    t = None if target is None else float(target)
    x = None if actual is None else float(actual)
    if t is not None and x is not None and x > t and a < ACC_SPEED:
        return u"\u4e0d\u5408\u683c", u"\u5b9e\u9645\u901f\u5ea6 %g BPM \u5df2\u8d85\u8fc7\u76ee\u6807 %g BPM\uff0c\u4f46\u51c6\u786e\u7387\u4ec5 %.1f%%\uff0c\u5c5e\u4e8e\u63d0\u901f\u8fc7\u65e9" % (x, t, a)
    if t is not None and x is not None and x > t + 10:
        return u"\u9700\u6539\u8fdb", u"\u5355\u6b21\u63d0\u901f\u8d85\u8fc7 10 BPM\uff08\u76ee\u6807 %g\uff0c\u5b9e\u9645 %g\uff09\uff0c\u5e45\u5ea6\u8fc7\u5927" % (t, x)
    if a < ACC_SPEED:
        return u"\u9700\u6539\u8fdb", u"\u51c6\u786e\u7387 %.1f%% \u672a\u8fbe\u63d0\u901f\u95e8\u69db %.0f%%\uff0c\u7ef4\u6301\u5f53\u524d\u901f\u5ea6" % (a, ACC_SPEED)
    return u"\u5408\u683c", u"\u51c6\u786e\u7387 %.1f%% \u8fbe\u6807\uff0c\u53ef\u63d0\u901f 5-10 BPM" % a


def dose_advice(minutes, days, separate):
    """\u8fd4\u56de (\u9700\u6539\u8fdb\u9879, \u5f85\u786e\u8ba4\u9879), \u6ca1\u586b\u7684\u5b57\u6bb5\u53ea\u8bb0\u5f85\u786e\u8ba4, \u4e0d\u5f53\u6210\u9700\u6539\u8fdb\u3002"""
    out = []
    pend = []
    if minutes is None:
        pend.append(u"\u672a\u63d0\u4f9b\u5355\u6b21\u7ec3\u4e60\u65f6\u957f")
    else:
        m = float(minutes)
        if m < MIN_MINUTES:
            out.append(u"\u5355\u6b21 %.0f \u5206\u949f\u504f\u77ed\uff0c\u5efa\u8bae 20-30 \u5206\u949f\u5e76\u5206 2-3 \u6bb5" % m)
        elif m > MAX_MINUTES:
            out.append(u"\u5355\u6b21 %.0f \u5206\u949f\u504f\u957f\uff0c\u5206 2-3 \u6bb5\u5e76\u5728\u6bb5\u95f4\u4f11\u606f 5-10 \u5206\u949f" % m)
    if days is None:
        pend.append(u"\u672a\u63d0\u4f9b\u6bcf\u5468\u7ec3\u4e60\u5929\u6570")
    else:
        d = float(days)
        if d < MIN_DAYS:
            out.append(u"\u6bcf\u5468 %.0f \u5929\u504f\u5c11\uff0c\u89c4\u5f8b\u6027\u6bd4\u5355\u6b21\u65f6\u957f\u66f4\u91cd\u8981\uff0c\u5efa\u8bae 4-5 \u5929" % d)
    if separate is None:
        pend.append(u"\u672a\u586b\u662f\u5426\u505a\u8fc7\u5206\u624b\u7ec3\u4e60")
    elif separate is False:
        out.append(u"\u672a\u505a\u5206\u624b\u7ec3\u4e60\uff1a\u5148\u5355\u624b\uff0c\u8fde\u7eed\u4e09\u904d\u65e0\u9519\u518d\u5408\u624b")
    return out, pend


def load_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def build_report(data):
    notes = data.get("notes", []) or []
    hand = data.get("hand", "right")
    scale = data.get("scale")
    hs = data.get("hand_shape", {}) or {}
    acc = data.get("accuracy")
    target = data.get("tempo_target")
    actual = data.get("tempo_actual")
    minutes = data.get("session_minutes")
    days = data.get("practice_days_per_week")
    separate = data.get("separate_hands")

    defects = []
    fine = []
    pending = []

    if not notes:
        pending.append(u"\u672a\u63d0\u4f9b\u9010\u97f3\u6307\u6cd5\uff0c\u65e0\u6cd5\u505a\u6307\u6cd5\u8fdd\u89c4\u68c0\u67e5")
        bad_range, thumb_black, same_run = [], [], []
        sok, smsg = None, u"\u672a\u63d0\u4f9b\u97f3\u7b26\uff0c\u8df3\u8fc7\u97f3\u9636\u6bd4\u5bf9"
    else:
        bad_range, thumb_black, same_run = finger_violations(notes)
        if bad_range:
            defects.append(u"\u6307\u53f7\u8d8a\u754c\uff08\u7b2c %s \u4e2a\u97f3\uff09\uff0c\u6307\u53f7\u53ea\u80fd\u662f 1-5" % u"\u3001".join(str(i) for i in bad_range))
        if thumb_black:
            defects.append(u"\u7b2c %s \u4e2a\u97f3\u7528 1 \u6307\u5f39\u9ed1\u952e\uff1a\u62c7\u6307\u77ed\u4e14\u9760\u5916\uff0c\u4e0a\u9ed1\u952e\u4f1a\u628a\u624b\u638c\u626d\u6b6a\u5e76\u5e26\u504f\u540e\u7eed\u6307\u6cd5" % (
                u"\u3001".join(str(i) for i in thumb_black)))
        if same_run:
            defects.append(u"\u7b2c %s \u4e2a\u97f3\u51fa\u73b0\u8fde\u7eed\u4e09\u6b21\u4ee5\u4e0a\u540c\u6307\u6309\u4e0d\u540c\u952e\uff0c\u672a\u505a\u540c\u97f3\u6216\u957f\u97f3\u6362\u6307" % (
                u"\u3001".join(str(i) for i in same_run)))
        sok, smsg = scale_check(scale, hand, notes)
        if sok is False:
            defects.append(smsg)
        elif sok is None:
            pending.append(smsg)

    shape_bad = []
    shape_unknown = []
    for key, name, why in HAND_SHAPE_ITEMS:
        v = hs.get(key)
        if v is None:
            shape_unknown.append(name)
        elif v is False:
            shape_bad.append((name, why))
    if shape_bad:
        for name, why in shape_bad:
            defects.append(u"\u624b\u578b\u4e0d\u5408\u683c\uff1a%s \u2014\u2014 %s" % (name, why))
    if shape_unknown:
        pending.append(u"\u624b\u578b\u9879\u672a\u586b\uff1a%s" % u"\u3001".join(shape_unknown))

    sv, smsg2 = speed_verdict(acc, target, actual)
    if sv == u"\u4e0d\u5408\u683c":
        defects.append(smsg2)
    elif sv == u"\u9700\u6539\u8fdb":
        fine.append(smsg2)
    elif sv == u"\u5f85\u786e\u8ba4":
        pending.append(smsg2)

    dose, dose_pending = dose_advice(minutes, days, separate)
    fine.extend(dose)
    pending.extend(dose_pending)

    lines = []
    lines.append("=" * 62)
    lines.append(u"\u94a2\u7434\u6307\u6cd5\u8fdd\u89c4\u68c0\u67e5\u4e0e\u7ec3\u4e60\u5242\u91cf\u6838\u5bf9")
    lines.append("=" * 62)
    lines.append(u"\u624b\u522b\uff1a%s    \u66f2\u76ee\u8c03\u6027\uff1a%s    \u97f3\u7b26\u6570\uff1a%d" % (
        u"\u53f3\u624b" if hand == "right" else u"\u5de6\u624b", scale if scale else u"\u672a\u586b", len(notes)))
    lines.append("")
    lines.append(u"[\u4e00] \u6307\u6cd5\u68c0\u67e5")
    lines.append(u"  \u6307\u53f7\u8d8a\u754c\uff1a%s" % (u"%d \u5904" % len(bad_range) if bad_range else u"\u65e0"))
    lines.append(u"  1 \u6307\u4e0a\u9ed1\u952e\uff1a%s" % (u"%d \u5904" % len(thumb_black) if thumb_black else u"\u65e0"))
    lines.append(u"  \u8fde\u7eed\u540c\u6307\uff1a%s" % (u"%d \u5904" % len(same_run) if same_run else u"\u65e0"))
    lines.append(u"  \u97f3\u9636\u6307\u6cd5\u6bd4\u5bf9\uff1a%s" % smsg)
    lines.append("")
    lines.append(u"[\u4e8c] \u624b\u578b\u68c0\u67e5")
    if shape_bad:
        for name, why in shape_bad:
            lines.append(u"  \u4e0d\u5408\u683c\uff1a%s \u2014\u2014 %s" % (name, why))
    else:
        lines.append(u"  \u5df2\u586b\u9879\u5168\u90e8\u5408\u683c")
    lines.append("")
    lines.append(u"[\u4e09] \u901f\u5ea6\u4e0e\u51c6\u786e\u7387")
    lines.append(u"  \u51c6\u786e\u7387\uff1a%s    \u76ee\u6807\u901f\u5ea6\uff1a%s BPM    \u5b9e\u9645\u901f\u5ea6\uff1a%s BPM" % (
        (u"%.1f%%" % float(acc)) if acc is not None else u"--",
        (u"%g" % float(target)) if target is not None else u"--",
        (u"%g" % float(actual)) if actual is not None else u"--"))
    lines.append(u"  \u5224\u5b9a\uff1a%s \u2014\u2014 %s" % (sv, smsg2))
    lines.append("")
    lines.append(u"[\u56db] \u4e0d\u5408\u683c\u9879\u4e0e\u539f\u56e0")
    if defects:
        for i, d in enumerate(defects, 1):
            lines.append(u"  %d. %s" % (i, d))
    else:
        lines.append(u"  \u65e0")
    lines.append("")
    lines.append(u"[\u4e94] \u9700\u6539\u8fdb\u9879")
    if fine:
        for i, d in enumerate(fine, 1):
            lines.append(u"  %d. %s" % (i, d))
    else:
        lines.append(u"  \u65e0")
    lines.append("")
    lines.append(u"[\u516d] \u5f85\u786e\u8ba4\u9879")
    if pending:
        for i, d in enumerate(pending, 1):
            lines.append(u"  %d. %s" % (i, d))
    else:
        lines.append(u"  \u65e0")
    lines.append("")
    lines.append(u"[\u4e03] \u7ec3\u4e60\u5904\u65b9")
    lines.append(u"  1. \u6307\u6cd5\u4e00\u65e6\u786e\u5b9a\u5c31\u4e0d\u518d\u6539\uff0c\u6bcf\u6b21\u5f39\u540c\u4e00\u6bb5\u7528\u540c\u4e00\u5957\u6307\u6cd5")
    if thumb_black or bad_range or same_run:
        lines.append(u"  2. \u5148\u4fee\u6307\u6cd5\u8fdd\u89c4\uff0c\u7528\u6162\u901f\u65ad\u594f\u9010\u97f3\u91cd\u6392\u6307\u6cd5")
    if shape_bad:
        lines.append(u"  3. \u624b\u578b\u672a\u8fc7\u4e0d\u8c08\u901f\u5ea6\uff1a\u964d\u901f\u3001\u65ad\u594f\u3001\u8fde\u594f\u3001\u518d\u63d0\u901f")
    lines.append(u"  4. \u63d0\u901f\u6761\u4ef6\uff1a\u5f53\u524d\u901f\u5ea6\u8fde\u7eed\u4e09\u904d 100%% \u65e0\u9519\uff0c\u6bcf\u6b21\u53ea\u52a0 5-10 BPM")
    lines.append(u"  5. \u6bcf\u65e5 20-30 \u5206\u949f\u5206 2-3 \u6bb5\uff0c\u6bcf\u5468 4-5 \u5929")
    lines.append(u"  6. \u624b\u6307\u624b\u8155\u75bc\u75db\u65f6\u7acb\u5373\u505c\u624b\uff0c\u4e0d\u8981\u5fcd\u75db\u7ec3\u4e60")

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
    lines.append(u"\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u6307\u6cd5\u81ea\u67e5\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u94a2\u7434\u6559\u5b66\u7ed3\u8bba\u6216\u533b\u5b66\u8bca\u65ad\u3002")
    lines.append("=" * 62)

    summary = {
        "finger_out_of_range": bad_range,
        "thumb_on_black": thumb_black,
        "same_finger_runs": same_run,
        "scale_match": sok,
        "hand_shape_bad": [n for n, _ in shape_bad],
        "speed_verdict": sv,
        "defects": defects,
        "fine": fine,
        "pending": pending,
        "overall": overall,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    b, t, s = finger_violations([{"key": "C4", "finger": 1, "black": False},
                                 {"key": "D4", "finger": 2, "black": False}])
    r.append((u"\u6b63\u5e38\u6307\u6cd5\u65e0\u8fdd\u89c4", not b and not t and not s))

    b1, t1, _ = finger_violations([{"key": "C#4", "finger": 1, "black": True}])
    r.append((u"\u53cd\u4f8b\uff1a1 \u6307\u4e0a\u9ed1\u952e\u88ab\u68c0\u51fa", t1 == [1]))

    b2, _, _ = finger_violations([{"key": "C4", "finger": 6, "black": False}])
    r.append((u"\u53cd\u4f8b\uff1a\u6307\u53f7 6 \u88ab\u5224\u8d8a\u754c", b2 == [1]))

    _, _, s3 = finger_violations([
        {"key": "C4", "finger": 3, "black": False},
        {"key": "D4", "finger": 3, "black": False},
        {"key": "E4", "finger": 3, "black": False},
    ])
    r.append((u"\u53cd\u4f8b\uff1a\u8fde\u7eed\u4e09\u6b21\u540c\u6307\u88ab\u68c0\u51fa", s3 == [3]))

    ok, msg = scale_check("C", "right", [{"key": "C4", "finger": 1}, {"key": "D4", "finger": 2},
                                         {"key": "E4", "finger": 3}, {"key": "F4", "finger": 1},
                                         {"key": "G4", "finger": 2}, {"key": "A4", "finger": 3},
                                         {"key": "B4", "finger": 4}, {"key": "C5", "finger": 5}])
    r.append((u"C \u5927\u8c03\u53f3\u624b\u6307\u6cd5\u4e00\u81f4", ok is True))

    ok2, _ = scale_check("C", "right", [{"key": "C4", "finger": 1}, {"key": "D4", "finger": 2},
                                        {"key": "E4", "finger": 3}, {"key": "F4", "finger": 4},
                                        {"key": "G4", "finger": 5}, {"key": "A4", "finger": 4},
                                        {"key": "B4", "finger": 3}, {"key": "C5", "finger": 2}])
    r.append((u"\u53cd\u4f8b\uff1a\u6307\u6cd5\u4e0e\u6807\u51c6\u8868\u4e0d\u4e00\u81f4\u5224\u4e0d\u5408\u683c", ok2 is False))

    ok3, _ = scale_check("X", "right", [{"key": "C4", "finger": 1}])
    r.append((u"\u65e0\u5bf9\u5e94\u6807\u51c6\u8868\u65f6\u8df3\u8fc7\u6bd4\u5bf9", ok3 is None))

    r.append((u"\u51c6\u786e\u7387 85 \u5224\u4e0d\u5408\u683c", speed_verdict(85, 80, 80)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u63d0\u901f\u8fc7\u65e9\u5224\u4e0d\u5408\u683c", speed_verdict(92, 80, 100)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u5355\u6b21\u63d0\u901f\u8d85 10 BPM \u5224\u9700\u6539\u8fdb", speed_verdict(100, 80, 95)[0] == u"\u9700\u6539\u8fdb"))
    r.append((u"\u51c6\u786e\u7387\u8fbe\u6807\u5224\u5408\u683c", speed_verdict(100, 80, 85)[0] == u"\u5408\u683c"))

    _, s = build_report({
        "notes": [{"key": "C4", "finger": 1, "black": False},
                  {"key": "D4", "finger": 2, "black": False},
                  {"key": "E4", "finger": 3, "black": False},
                  {"key": "F4", "finger": 1, "black": False},
                  {"key": "G4", "finger": 2, "black": False},
                  {"key": "A4", "finger": 3, "black": False},
                  {"key": "B4", "finger": 4, "black": False},
                  {"key": "C5", "finger": 5, "black": False}],
        "hand": "right", "scale": "C",
        "hand_shape": {"palm_arch": True, "knuckle_support": True, "wrist_level": True,
                       "thumb_bent": True, "arm_relaxed": True},
        "accuracy": 100, "tempo_target": 80, "tempo_actual": 85,
        "session_minutes": 30, "practice_days_per_week": 5, "separate_hands": True,
    })
    r.append((u"\u6807\u51c6\u6837\u4f8b\u5224\u5b9a\u5408\u683c", s["overall"] == u"\u5408\u683c"))

    _, s1 = build_report({
        "notes": [{"key": "C#4", "finger": 1, "black": True},
                  {"key": "D#4", "finger": 2, "black": True}],
        "hand": "right",
        "hand_shape": {"palm_arch": True, "knuckle_support": False, "wrist_level": True,
                       "thumb_bent": True, "arm_relaxed": True},
        "accuracy": 92, "tempo_target": 80, "tempo_actual": 100,
        "session_minutes": 30, "practice_days_per_week": 5, "separate_hands": True,
    })
    r.append((u"\u53cd\u4f8b\uff1a\u7efc\u5408\u8fdd\u89c4\u5224\u4e0d\u5408\u683c", s1["overall"] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a1 \u6307\u9ed1\u952e\u8fdb\u7f3a\u9677\u8868", any(u"1 \u6307\u5f39\u9ed1\u952e" in d for d in s1["defects"])))
    r.append((u"\u53cd\u4f8b\uff1a\u584c\u6307\u8fdb\u7f3a\u9677\u8868", any(u"\u7b2c\u4e00\u6307\u8282" in d for d in s1["defects"])))

    _, s2 = build_report({
        "hand_shape": {"palm_arch": True, "knuckle_support": False, "wrist_level": True,
                       "thumb_bent": True, "arm_relaxed": True},
    })
    r.append((u"\u7f3a\u6307\u6cd5\u6570\u636e\u65f6\u624b\u578b\u95ee\u9898\u4ecd\u5224\u4e0d\u5408\u683c", s2["overall"] == u"\u4e0d\u5408\u683c"))

    _, s3 = build_report({"hand_shape": {}})
    r.append((u"\u624b\u578b\u5168\u672a\u586b\u8bb0\u4e3a\u5f85\u786e\u8ba4", s3["overall"] == u"\u5f85\u786e\u8ba4"))

    p = os.path.join(tempfile.gettempdir(), "_piano_bom_case.json")
    blob = b"\xef\xbb\xbf" + json.dumps({
        "notes": [{"key": "C4", "finger": 1, "black": False}],
        "hand": "right", "accuracy": 100, "tempo_target": 80, "tempo_actual": 80,
    }, ensure_ascii=False).encode("utf-8")
    with open(p, "wb") as f:
        f.write(blob)
    try:
        d = load_json(p)
        r.append((u"UTF-8 BOM \u8f93\u5165\u9996\u952e\u53ef\u8bfb", len(d.get("notes", [])) == 1))
        r.append((u"UTF-8 BOM \u8f93\u5165\u6570\u503c\u53ef\u8bfb", abs(d.get("accuracy", 0) - 100.0) < 1e-9))
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
    parser = argparse.ArgumentParser(description=u"\u94a2\u7434\u6307\u6cd5\u8fdd\u89c4\u68c0\u67e5\u5de5\u5177")
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

