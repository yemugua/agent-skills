# -*- coding: utf-8 -*-
"""\u54d1\u94c3\u8bad\u7ec3\u52a8\u4f5c\u4e0e\u5242\u91cf\u6838\u5bf9\u5de5\u5177\u3002

\u7528\u6cd5:
  python dumbbell_training_check.py --file case.json [--json]
  python dumbbell_training_check.py --selftest

\u5224\u5b9a\u987a\u5e8f: \u5148\u770b\u771f\u5b9e\u7f3a\u9677(\u4ee3\u507f\u4fe1\u53f7\u3001\u7ec4\u95f4\u4f11\u606f\u4e25\u91cd\u4e0d\u8db3\u3001\u618b\u6c14\u53d1\u529b\u3001
\u540c\u4e00\u808c\u7fa4\u6bcf\u5468\u8fc7\u91cf\u3001\u8fde\u7eed\u505c\u6ede), \u518d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574; \u53ea\u586b\u4e86\u4ee3\u507f\u4fe1\u53f7
\u5374\u6ca1\u586b\u91cd\u91cf\u65f6, \u76f4\u63a5\u5224\u4e0d\u5408\u683c\u800c\u4e0d\u662f\u5f85\u786e\u8ba4\u3002
"""
import argparse
import io
import json
import os
import sys
import tempfile

GOAL_SPECS = {
    "strength": {"reps": (3, 6), "sets": (3, 5), "rest": (120, 180)},
    "hypertrophy": {"reps": (8, 12), "sets": (3, 4), "rest": (60, 120)},
    "endurance": {"reps": (15, 20), "sets": (2, 3), "rest": (30, 60)},
}
GOAL_LABEL = {
    "strength": u"\u529b\u91cf",
    "hypertrophy": u"\u589e\u808c",
    "endurance": u"\u8010\u529b",
}

COMP_ITEMS = [
    ("shrug", u"\u8038\u80a9", u"\u659c\u65b9\u808c\u4ee3\u507f\uff0c\u76ee\u6807\u808c\u6ca1\u5403\u5230\u529b\uff1a\u6c89\u80a9\u5e76\u51cf\u91cd\u91cf"),
    ("lumbar", u"\u8170\u90e8\u53cd\u5f13", u"\u6838\u5fc3\u6ca1\u6536\u4f4f\u6216\u91cd\u91cf\u8fc7\u5927\uff1a\u51cf\u91cd\u91cf\u3001\u7f29\u5c0f\u5e45\u5ea6\u6216\u6539\u652f\u6491\u4f4d"),
    ("elbow_flare", u"\u8098\u90e8\u8fc7\u5ea6\u5916\u7ffb", u"\u80a9\u5173\u8282\u53d7\u529b\u4e0d\u826f\uff1a\u628a\u8098\u89d2\u8c03\u5230 45-60 \u5ea6\u5e76\u51cf\u91cd\u91cf"),
    ("swing", u"\u501f\u529b\u7529\u52a8", u"\u91cd\u91cf\u8fdc\u8d85\u63a7\u5236\u80fd\u529b\uff1a\u7acb\u5373\u51cf\u91cd\u91cf"),
    ("neck_forward", u"\u9888\u90e8\u524d\u4f38", u"\u6838\u5fc3\u4e0e\u80a9\u80db\u5931\u7a33\uff1a\u6536\u4e0b\u5df4\u3001\u51cf\u91cd\u91cf\u3001\u91cd\u5efa\u652f\u6491"),
]

REST_HARD_MIN = 45.0
SAME_MUSCLE_MAX = 3.0
STALL_BAD = 3.0
STALL_WARN = 2.0
SESSIONS_MIN = 2.0
SESSIONS_MAX = 5.0


def num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def comp_list(ex):
    comp = ex.get("compensation", {}) or {}
    hit = []
    for key, name, why in COMP_ITEMS:
        if comp.get(key) is True:
            hit.append((name, why))
    return hit


def rank_exercises(exs):
    """\u6309\u4ee3\u507f\u6570\u91cf\u964d\u5e8f\u6392, \u4ee3\u507f\u6700\u591a\u7684\u6392\u6700\u524d, \u7528\u8d1f\u53f7\u9501\u4f4f\u65b9\u5411\u3002"""
    ranked = sorted(exs, key=lambda e: (-len(comp_list(e)), str(e.get("name", ""))))
    return [(str(e.get("name", u"\u672a\u547d\u540d")), len(comp_list(e))) for e in ranked]


def rest_verdict(goal, rest):
    if rest is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u7ec4\u95f4\u4f11\u606f\u65f6\u957f"
    v = float(rest)
    if v < REST_HARD_MIN:
        return u"\u4e0d\u5408\u683c", u"\u7ec4\u95f4\u4f11\u606f %g \u79d2\uff0c\u4f4e\u4e8e %g \u79d2\uff1a\u4e0b\u4e00\u7ec4\u51e0\u4e4e\u5fc5\u7136\u52a8\u4f5c\u53d8\u5f62\uff0c\u7b49\u4e8e\u7528\u9519\u8bef\u59ff\u52bf\u7ec3" % (
            v, REST_HARD_MIN)
    spec = GOAL_SPECS.get(goal)
    if spec is None:
        return u"\u5f85\u786e\u8ba4", u"\u8bad\u7ec3\u76ee\u6807\u672a\u8bc6\u522b\uff0c\u65e0\u6cd5\u6838\u5bf9\u4f11\u606f\u533a\u95f4"
    lo, hi = spec["rest"]
    if v < lo:
        return u"\u9700\u6539\u8fdb", u"\u7ec4\u95f4\u4f11\u606f %g \u79d2\uff0c\u4f4e\u4e8e\u8be5\u76ee\u6807\u5efa\u8bae\u7684 %g \u79d2\u4e0b\u9650" % (v, lo)
    if v > hi + 60:
        return u"\u9700\u6539\u8fdb", u"\u7ec4\u95f4\u4f11\u606f %g \u79d2\u504f\u957f\uff0c\u53ef\u538b\u5230 %g-%g \u79d2" % (v, lo, hi)
    return u"\u5408\u683c", u"\u7ec4\u95f4\u4f11\u606f %g \u79d2\uff0c\u5728 %g-%g \u79d2\u533a\u95f4" % (v, lo, hi)


def reps_verdict(goal, reps):
    if reps is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u6bcf\u7ec4\u6b21\u6570"
    v = float(reps)
    spec = GOAL_SPECS.get(goal)
    if spec is None:
        return u"\u5f85\u786e\u8ba4", u"\u8bad\u7ec3\u76ee\u6807\u672a\u8bc6\u522b\uff0c\u65e0\u6cd5\u6838\u5bf9\u6b21\u6570\u533a\u95f4"
    lo, hi = spec["reps"]
    if v < lo:
        return u"\u9700\u6539\u8fdb", u"\u6bcf\u7ec4 %g \u6b21\uff0c\u4f4e\u4e8e\u8be5\u76ee\u6807\u5efa\u8bae\u7684 %g \u6b21\u4e0b\u9650" % (v, lo)
    if v > hi:
        return u"\u9700\u6539\u8fdb", u"\u6bcf\u7ec4 %g \u6b21\uff0c\u9ad8\u4e8e\u8be5\u76ee\u6807\u5efa\u8bae\u7684 %g \u6b21\u4e0a\u9650" % (v, hi)
    return u"\u5408\u683c", u"\u6bcf\u7ec4 %g \u6b21\uff0c\u5728 %g-%g \u6b21\u533a\u95f4" % (v, lo, hi)


def sets_verdict(goal, sets):
    if sets is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u7ec4\u6570"
    v = float(sets)
    spec = GOAL_SPECS.get(goal)
    if spec is None:
        return u"\u5f85\u786e\u8ba4", u"\u8bad\u7ec3\u76ee\u6807\u672a\u8bc6\u522b\uff0c\u65e0\u6cd5\u6838\u5bf9\u7ec4\u6570\u533a\u95f4"
    lo, hi = spec["sets"]
    if v < lo:
        return u"\u9700\u6539\u8fdb", u"\u53ea\u505a %g \u7ec4\uff0c\u4f4e\u4e8e\u8be5\u76ee\u6807\u5efa\u8bae\u7684 %g \u7ec4\u4e0b\u9650" % (v, lo)
    if v > hi:
        return u"\u9700\u6539\u8fdb", u"\u505a %g \u7ec4\uff0c\u9ad8\u4e8e\u8be5\u76ee\u6807\u5efa\u8bae\u7684 %g \u7ec4\u4e0a\u9650\uff0c\u6ce8\u610f\u603b\u8bad\u7ec3\u91cf" % (v, hi)
    return u"\u5408\u683c", u"%g \u7ec4\uff0c\u5728 %g-%g \u7ec4\u533a\u95f4" % (v, lo, hi)


def rir_verdict(rir):
    if rir is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u4fdd\u7559\u6b21\u6570"
    v = float(rir)
    if v <= 1.0:
        return u"\u9700\u6539\u8fdb", u"\u4fdd\u7559\u6b21\u6570 %g\uff0c\u63a5\u8fd1\u529b\u7aed\uff1a\u6062\u590d\u65f6\u95f4\u957f\u4e14\u540e\u7eed\u7ec4\u522b\u5bb9\u6613\u53d8\u5f62\uff0c\u5efa\u8bae\u7559 2-3 \u6b21" % v
    if v >= 4.0:
        return u"\u9700\u6539\u8fdb", u"\u4fdd\u7559\u6b21\u6570 %g\uff0c\u5f3a\u5ea6\u4e0d\u8db3\uff1a\u53ef\u52a0\u91cd\u91cf\u6216\u52a0\u6b21\u6570" % v
    return u"\u5408\u683c", u"\u4fdd\u7559\u6b21\u6570 %g\uff0c\u5728 2-3 \u6b21\u7684\u5408\u9002\u533a\u95f4" % v


def load_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def build_report(data):
    goal = data.get("goal")
    exs = data.get("exercises", []) or []
    sessions = num(data.get("weekly_sessions"))
    same = num(data.get("same_muscle_per_week"))
    stalled = num(data.get("stalled_weeks"))
    breath = data.get("breath_holding")

    defects = []
    fine = []
    pending = []

    if goal not in GOAL_SPECS:
        pending.append(u"\u8bad\u7ec3\u76ee\u6807\u672a\u8bc6\u522b\uff0c\u5e94\u4e3a\u529b\u91cf\u3001\u589e\u808c\u6216\u8010\u529b")

    if not exs:
        pending.append(u"\u672a\u63d0\u4f9b\u52a8\u4f5c\u6e05\u5355\uff0c\u65e0\u6cd5\u505a\u52a8\u4f5c\u4e0e\u5242\u91cf\u6838\u5bf9")

    if breath is True:
        defects.append(u"\u618b\u6c14\u53d1\u529b\uff1a\u5927\u91cd\u91cf\u65f6\u618b\u6c14\u4f1a\u660e\u663e\u5347\u9ad8\u8840\u538b\uff0c\u5934\u6655\u773c\u9ed1\u5c31\u662f\u4fe1\u53f7\uff0c\u5e94\u6539\u4e3a\u53d1\u529b\u547c\u6c14\u8fd8\u539f\u5438\u6c14")

    for i, ex in enumerate(exs, 1):
        name = str(ex.get("name", u"\u7b2c %d \u4e2a\u52a8\u4f5c" % i))
        hit = comp_list(ex)
        for cname, why in hit:
            defects.append(u"\u52a8\u4f5c\u300c%s\u300d\u51fa\u73b0\u4ee3\u507f\uff1a%s \u2014\u2014 %s" % (name, cname, why))
        if not ex.get("compensation"):
            pending.append(u"\u52a8\u4f5c\u300c%s\u300d\u672a\u586b\u4ee3\u507f\u6838\u5bf9" % name)
        rv, rm = rest_verdict(goal, ex.get("rest_sec"))
        if rv == u"\u4e0d\u5408\u683c":
            defects.append(u"\u52a8\u4f5c\u300c%s\u300d\uff1a%s" % (name, rm))
        elif rv == u"\u9700\u6539\u8fdb":
            fine.append(u"\u52a8\u4f5c\u300c%s\u300d\uff1a%s" % (name, rm))
        elif rv == u"\u5f85\u786e\u8ba4":
            pending.append(u"\u52a8\u4f5c\u300c%s\u300d\uff1a%s" % (name, rm))
        pvr, pvm = reps_verdict(goal, ex.get("reps"))
        if pvr == u"\u9700\u6539\u8fdb":
            fine.append(u"\u52a8\u4f5c\u300c%s\u300d\uff1a%s" % (name, pvm))
        elif pvr == u"\u5f85\u786e\u8ba4":
            pending.append(u"\u52a8\u4f5c\u300c%s\u300d\uff1a%s" % (name, pvm))
        svr, svm = sets_verdict(goal, ex.get("sets"))
        if svr == u"\u9700\u6539\u8fdb":
            fine.append(u"\u52a8\u4f5c\u300c%s\u300d\uff1a%s" % (name, svm))
        rvr, rvm = rir_verdict(ex.get("rir"))
        if rvr == u"\u9700\u6539\u8fdb":
            fine.append(u"\u52a8\u4f5c\u300c%s\u300d\uff1a%s" % (name, rvm))

    if same is None:
        pending.append(u"\u672a\u63d0\u4f9b\u540c\u4e00\u808c\u7fa4\u6bcf\u5468\u8bad\u7ec3\u6b21\u6570")
    elif same > SAME_MUSCLE_MAX:
        defects.append(u"\u540c\u4e00\u808c\u7fa4\u6bcf\u5468\u7ec3 %g \u6b21\uff0c\u8d85\u8fc7 %g \u6b21\u4e0a\u9650\uff1a\u808c\u8089\u5728\u4f11\u606f\u65f6\u6062\u590d\uff0c\u7ec3\u5f97\u8d8a\u52e4\u4e0d\u7b49\u4e8e\u957f\u5f97\u8d8a\u5feb" % (
            same, SAME_MUSCLE_MAX))

    if stalled is None:
        pending.append(u"\u672a\u63d0\u4f9b\u8fde\u7eed\u65e0\u53d8\u5316\u5468\u6570")
    elif stalled >= STALL_BAD:
        defects.append(u"\u8fde\u7eed %g \u5468\u91cd\u91cf\u3001\u6b21\u6570\u3001\u7ec4\u6570\u90fd\u65e0\u53d8\u5316\uff1a\u5e94\u7cfb\u7edf\u68c0\u67e5\u8bad\u7ec3\u91cf\u3001\u6062\u590d\u4e0e\u7761\u7720\u996e\u98df\uff0c\u800c\u4e0d\u662f\u7ee7\u7eed\u786c\u52a0" % stalled)
    elif stalled >= STALL_WARN:
        fine.append(u"\u8fde\u7eed %g \u5468\u65e0\u53d8\u5316\uff0c\u8bf4\u660e\u8ba1\u5212\u9700\u8981\u8c03\u6574" % stalled)

    if sessions is None:
        pending.append(u"\u672a\u63d0\u4f9b\u6bcf\u5468\u8bad\u7ec3\u9891\u6b21")
    elif sessions < SESSIONS_MIN:
        fine.append(u"\u6bcf\u5468\u8bad\u7ec3 %g \u6b21\u504f\u5c11\uff0c\u521d\u5b66\u8005\u5efa\u8bae 2-3 \u6b21" % sessions)
    elif sessions > SESSIONS_MAX:
        fine.append(u"\u6bcf\u5468\u8bad\u7ec3 %g \u6b21\u504f\u591a\uff0c\u6ce8\u610f\u5b89\u6392\u51cf\u91cf\u5468" % sessions)

    ranked = rank_exercises(exs)

    lines = []
    lines.append("=" * 62)
    lines.append(u"\u54d1\u94c3\u8bad\u7ec3\u52a8\u4f5c\u4e0e\u5242\u91cf\u6838\u5bf9")
    lines.append("=" * 62)
    lines.append(u"\u8bad\u7ec3\u76ee\u6807\uff1a%s    \u52a8\u4f5c\u6570\uff1a%d" % (GOAL_LABEL.get(goal, u"\u672a\u8bc6\u522b"), len(exs)))
    lines.append("")
    lines.append(u"[\u4e00] \u9010\u52a8\u4f5c\u6982\u89c8")
    lines.append(u"%-14s %8s %8s %6s %6s %8s" % (u"\u52a8\u4f5c", u"\u91cd\u91cfkg", u"\u6b21\u6570", u"\u7ec4\u6570", u"RIR", u"\u4f11\u606f\u79d2"))
    lines.append("-" * 62)
    for ex in exs:
        lines.append(u"%-14s %8s %8s %6s %6s %8s" % (
            str(ex.get("name", u"--")),
            (u"%g" % float(ex["weight_kg"])) if num(ex.get("weight_kg")) is not None else u"--",
            (u"%g" % float(ex["reps"])) if num(ex.get("reps")) is not None else u"--",
            (u"%g" % float(ex["sets"])) if num(ex.get("sets")) is not None else u"--",
            (u"%g" % float(ex["rir"])) if num(ex.get("rir")) is not None else u"--",
            (u"%g" % float(ex["rest_sec"])) if num(ex.get("rest_sec")) is not None else u"--"))
    lines.append("-" * 62)
    lines.append("")
    lines.append(u"[\u4e8c] \u9700\u4f18\u5148\u5904\u7406\u7684\u52a8\u4f5c\uff08\u6309\u4ee3\u507f\u6570\u91cf\u964d\u5e8f\uff09")
    if ranked and ranked[0][1] > 0:
        for name, cnt in ranked:
            if cnt > 0:
                lines.append(u"  %s\uff1a%d \u9879\u4ee3\u507f" % (name, cnt))
    else:
        lines.append(u"  \u65e0\u4ee3\u507f\u4fe1\u53f7")
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
    lines.append(u"  1. \u51fa\u73b0\u4ee3\u507f\u7684\u7b2c\u4e00\u52a8\u4f5c\u6c38\u8fdc\u662f\u964d\u91cd\u91cf\u6216\u9000\u9636\uff0c\u4e0d\u662f\u7ee7\u7eed\u52a0\u91cd\u91cf")
    lines.append(u"  2. \u91cd\u91cf\u9009\u62e9\uff1a\u80fd\u6807\u51c6\u5b8c\u6210\u76ee\u6807\u6b21\u6570\u4e14\u8fd8\u5269 2-3 \u6b21\u4f59\u529b")
    if breath is True:
        lines.append(u"  3. \u7acb\u5373\u6539\u6389\u618b\u6c14\uff1a\u53d1\u529b\u547c\u6c14\u3001\u8fd8\u539f\u5438\u6c14\u30012-3 \u79d2\u63a7\u5236\u4e0b\u843d")
    else:
        lines.append(u"  3. \u547c\u5438\uff1a\u53d1\u529b\u547c\u6c14\u3001\u8fd8\u539f\u5438\u6c14\u30012-3 \u79d2\u63a7\u5236\u4e0b\u843d\uff0c\u5168\u7a0b\u4e0d\u618b\u6c14")
    lines.append(u"  4. \u6e10\u8fdb\u987a\u5e8f\uff1a\u5148\u52a0\u6b21\u6570\uff08\u5728\u76ee\u6807\u533a\u95f4\u5185\u52a0\u6ee1\uff09\u2192 \u518d\u52a0\u91cd\u91cf \u2192 \u6700\u540e\u8003\u8651\u52a0\u7ec4\u6570")
    lines.append(u"  5. \u540c\u4e00\u808c\u7fa4\u6bcf\u5468 2-3 \u6b21\uff0c\u95f4\u9694\u81f3\u5c11 48 \u5c0f\u65f6\uff0c\u6bcf 4-6 \u5468\u5b89\u6392\u51cf\u91cf\u5468")
    lines.append(u"  6. \u6bcf\u6b21\u8bb0\u5f55\u91cd\u91cf\u3001\u6b21\u6570\u3001\u7ec4\u6570\u3001RIR\uff0c\u6ca1\u6709\u8bb0\u5f55\u5c31\u65e0\u6cd5\u5224\u65ad\u6709\u6ca1\u6709\u6e10\u8fdb")

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
    lines.append(u"\u63d0\u793a\uff1a\u5173\u8282\u9510\u75db\u3001\u653e\u5c04\u75db\u3001\u80bf\u80c0\u3001\u591c\u95f4\u75db\u3001\u8bad\u7ec3\u4e2d\u5934\u6655\u80f8\u95f7\u65f6\u7acb\u5373\u505c\u7ec3\u5e76\u5c31\u533b\u3002")
    lines.append(u"\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u8bad\u7ec3\u81ea\u67e5\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u533b\u5b66\u8bca\u65ad\u6216\u5eb7\u590d\u65b9\u6848\u3002")
    lines.append("=" * 62)

    summary = {
        "goal": goal,
        "exercise_count": len(exs),
        "ranked": ranked,
        "defects": defects,
        "fine": fine,
        "pending": pending,
        "overall": overall,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append((u"\u589e\u808c\u4f11\u606f 90 \u79d2\u5224\u5408\u683c", rest_verdict("hypertrophy", 90)[0] == u"\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u4f11\u606f 30 \u79d2\u5224\u4e0d\u5408\u683c", rest_verdict("hypertrophy", 30)[0] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u529b\u91cf\u76ee\u6807\u589e\u808c\u6b21\u6570\u5224\u9700\u6539\u8fdb", reps_verdict("strength", 10)[0] == u"\u9700\u6539\u8fdb"))
    r.append((u"\u589e\u808c\u6b21\u6570 10 \u5224\u5408\u683c", reps_verdict("hypertrophy", 10)[0] == u"\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1aRIR 0 \u5224\u9700\u6539\u8fdb", rir_verdict(0)[0] == u"\u9700\u6539\u8fdb"))
    r.append((u"RIR 2 \u5224\u5408\u683c", rir_verdict(2)[0] == u"\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u7ec4\u6570 6 \u5224\u9700\u6539\u8fdb", sets_verdict("hypertrophy", 6)[0] == u"\u9700\u6539\u8fdb"))
    r.append((u"\u672a\u77e5\u76ee\u6807\u65f6\u6b21\u6570\u5224\u5f85\u786e\u8ba4", reps_verdict("xxx", 10)[0] == u"\u5f85\u786e\u8ba4"))

    exs = [
        {"name": u"A", "compensation": {"shrug": True}},
        {"name": u"B", "compensation": {"shrug": True, "lumbar": True, "swing": True}},
        {"name": u"C", "compensation": {}},
    ]
    ranked = rank_exercises(exs)
    r.append((u"\u6392\u5e8f\u65b9\u5411\uff1a\u4ee3\u507f\u6700\u591a\u7684\u6392\u6700\u524d", ranked[0][0] == u"B" and ranked[0][1] == 3))
    r.append((u"\u6392\u5e8f\u65b9\u5411\uff1a\u65e0\u4ee3\u507f\u7684\u6392\u6700\u540e", ranked[-1][0] == u"C" and ranked[-1][1] == 0))

    _, s = build_report({
        "goal": "hypertrophy",
        "exercises": [
            {"name": u"\u54d1\u94c3\u5367\u63a8", "weight_kg": 16, "reps": 10, "sets": 3, "rir": 2, "rest_sec": 100,
             "compensation": {"shrug": False, "lumbar": False, "elbow_flare": False, "swing": False}},
            {"name": u"\u5355\u81c2\u54d1\u94c3\u5212\u8239", "weight_kg": 14, "reps": 10, "sets": 3, "rir": 2, "rest_sec": 90,
             "compensation": {"shrug": False, "lumbar": False, "elbow_flare": False, "swing": False}},
        ],
        "weekly_sessions": 3, "same_muscle_per_week": 2, "stalled_weeks": 0,
        "breath_holding": False,
    })
    r.append((u"\u6807\u51c6\u6837\u4f8b\u5224\u5b9a\u5408\u683c", s["overall"] == u"\u5408\u683c"))

    _, s1 = build_report({
        "goal": "hypertrophy",
        "exercises": [
            {"name": u"\u54d1\u94c3\u80a9\u63a8", "weight_kg": 20, "reps": 8, "sets": 4, "rir": 1, "rest_sec": 30,
             "compensation": {"shrug": True, "lumbar": True, "elbow_flare": False, "swing": False}},
        ],
        "weekly_sessions": 3, "same_muscle_per_week": 2, "stalled_weeks": 0,
        "breath_holding": False,
    })
    r.append((u"\u53cd\u4f8b\uff1a\u4ee3\u507f\u52a0\u4f11\u606f\u4e0d\u8db3\u5224\u4e0d\u5408\u683c", s1["overall"] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u8038\u80a9\u8fdb\u7f3a\u9677\u8868", any(u"\u8038\u80a9" in d for d in s1["defects"])))
    r.append((u"\u53cd\u4f8b\uff1a\u8170\u90e8\u53cd\u5f13\u8fdb\u7f3a\u9677\u8868", any(u"\u8170\u90e8\u53cd\u5f13" in d for d in s1["defects"])))

    _, s2 = build_report({
        "goal": "hypertrophy",
        "exercises": [{"name": u"\u54d1\u94c3\u5367\u63a8", "reps": 10, "sets": 3, "rir": 2, "rest_sec": 90,
                       "compensation": {"shrug": False, "lumbar": False,
                                        "elbow_flare": False, "swing": False}}],
        "weekly_sessions": 3, "same_muscle_per_week": 2, "stalled_weeks": 0,
        "breath_holding": True,
    })
    r.append((u"\u53cd\u4f8b\uff1a\u618b\u6c14\u53d1\u529b\u5224\u4e0d\u5408\u683c", s2["overall"] == u"\u4e0d\u5408\u683c"))

    _, s3 = build_report({
        "goal": "hypertrophy",
        "exercises": [{"name": u"\u54d1\u94c3\u5367\u63a8", "reps": 10, "sets": 3, "rir": 2, "rest_sec": 90,
                       "compensation": {}}],
        "weekly_sessions": 3, "same_muscle_per_week": 5, "stalled_weeks": 0,
    })
    r.append((u"\u53cd\u4f8b\uff1a\u540c\u4e00\u808c\u7fa4\u6bcf\u5468 5 \u6b21\u5224\u4e0d\u5408\u683c", s3["overall"] == u"\u4e0d\u5408\u683c"))

    _, s4 = build_report({
        "goal": "hypertrophy",
        "exercises": [{"name": u"\u54d1\u94c3\u5367\u63a8", "reps": 10, "sets": 3, "rir": 2, "rest_sec": 90,
                       "compensation": {}}],
        "weekly_sessions": 3, "same_muscle_per_week": 2, "stalled_weeks": 4,
    })
    r.append((u"\u53cd\u4f8b\uff1a\u8fde\u7eed\u505c\u6ede 4 \u5468\u5224\u4e0d\u5408\u683c", s4["overall"] == u"\u4e0d\u5408\u683c"))

    _, s5 = build_report({"goal": "hypertrophy", "exercises": [{"name": u"X", "compensation": {"shrug": True}}]})
    r.append((u"\u7f3a\u5242\u91cf\u4f46\u6709\u4ee3\u507f\u4e0d\u5f97\u5224\u5f85\u786e\u8ba4", s5["overall"] == u"\u4e0d\u5408\u683c"))

    _, s6 = build_report({"goal": "xxx"})
    r.append((u"\u672a\u77e5\u76ee\u6807\u8bb0\u4e3a\u5f85\u786e\u8ba4", s6["overall"] == u"\u5f85\u786e\u8ba4"))

    p = os.path.join(tempfile.gettempdir(), "_dumbbell_bom_case.json")
    blob = b"\xef\xbb\xbf" + json.dumps({
        "goal": "hypertrophy",
        "exercises": [{"name": u"\u54d1\u94c3\u5367\u63a8", "reps": 10, "sets": 3, "rir": 2,
                       "rest_sec": 90, "compensation": {}}],
        "weekly_sessions": 3, "same_muscle_per_week": 2, "stalled_weeks": 0,
    }, ensure_ascii=False).encode("utf-8")
    with open(p, "wb") as f:
        f.write(blob)
    try:
        d = load_json(p)
        r.append((u"UTF-8 BOM \u8f93\u5165\u9996\u952e\u53ef\u8bfb", d.get("goal") == "hypertrophy"))
        r.append((u"UTF-8 BOM \u8f93\u5165\u5d4c\u5957\u7ed3\u6784\u53ef\u8bfb", d["exercises"][0]["name"] == u"\u54d1\u94c3\u5367\u63a8"))
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
    parser = argparse.ArgumentParser(description=u"\u54d1\u94c3\u8bad\u7ec3\u52a8\u4f5c\u4e0e\u5242\u91cf\u6838\u5bf9\u5de5\u5177")
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
