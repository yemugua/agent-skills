# -*- coding: utf-8 -*-
"""\u5531\u6b4c\u97f3\u51c6\u504f\u5dee\u7edf\u8ba1\u4e0e\u8dd1\u8c03\u5f52\u56e0\u5de5\u5177\u3002

\u7528\u6cd5:
  python singing_pitch_check.py --file case.json [--json]
  python singing_pitch_check.py --selftest

\u5224\u5b9a\u987a\u5e8f: \u5148\u770b\u771f\u5b9e\u7f3a\u9677(\u660e\u663e\u8dd1\u8c03\u3001\u97f3\u7a0b\u65b9\u5411\u9519\u8bef\u3001\u7cfb\u7edf\u6027\u504f\u79fb\u8d85\u9608\u3001\u66f2\u76ee\u8d8a\u754c),
\u518d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574; \u6837\u672c\u4e0d\u8db3\u53ea\u8bb0\u4e3a\u5f85\u786e\u8ba4, \u4e0d\u63a9\u76d6\u5df2\u67e5\u51fa\u7684\u504f\u5dee\u3002
"""
import argparse
import io
import json
import os
import sys
import tempfile

HIT_CENTS = 20.0
LEVEL_STABLE = 20.0
LEVEL_BASIC = 35.0
LEVEL_OFF = 60.0
SYS_SHIFT = 25.0
SYS_SHIFT_BAD = 40.0


def mae(devs):
    if not devs:
        return None
    return sum(abs(float(d)) for d in devs) / len(devs)


def hit_rate(devs):
    if not devs:
        return None
    n = sum(1 for d in devs if abs(float(d)) <= HIT_CENTS)
    return float(n) / len(devs)


def signed_mean(devs):
    if not devs:
        return None
    return sum(float(d) for d in devs) / len(devs)


def direction_errors(notes):
    """\u6309\u8f93\u5165\u539f\u5e8f\u6bd4\u8f83\u76ee\u6807\u8d70\u5411\u4e0e\u5b9e\u9645\u8d70\u5411, \u4e0d\u505a\u4efb\u4f55\u91cd\u6392\u3002"""
    err = 0
    bad = []
    for i in range(1, len(notes)):
        t0 = float(notes[i - 1].get("target_midi", 0))
        t1 = float(notes[i].get("target_midi", 0))
        if t1 == t0:
            continue
        s0 = t0 * 100.0 + float(notes[i - 1].get("dev_cents", 0) or 0)
        s1 = t1 * 100.0 + float(notes[i].get("dev_cents", 0) or 0)
        if (t1 > t0 and s1 <= s0) or (t1 < t0 and s1 >= s0):
            err += 1
            bad.append((i, i + 1))
    return err, bad


def level_of(v):
    if v is None:
        return u"\u5f85\u786e\u8ba4"
    if v <= LEVEL_STABLE:
        return u"\u97f3\u51c6\u7a33\u5b9a"
    if v <= LEVEL_BASIC:
        return u"\u57fa\u672c\u7a33\u5b9a"
    if v <= LEVEL_OFF:
        return u"\u660e\u663e\u504f\u79bb"
    return u"\u660e\u663e\u8dd1\u8c03"


def shift_verdict(m):
    if m is None:
        return u"\u5f85\u786e\u8ba4", u"\u672a\u63d0\u4f9b\u9010\u97f3\u504f\u5dee"
    if m > SYS_SHIFT_BAD:
        return u"\u4e0d\u5408\u683c", u"\u7cfb\u7edf\u6027\u504f\u9ad8\uff08\u5747\u503c %+.1f \u97f3\u5206\uff09\uff0c\u591a\u4e3a\u5589\u90e8\u7d27\u5f20\u6216\u7528\u558a\u7684\u65b9\u5f0f\u627e\u9ad8\u97f3" % m
    if m < -SYS_SHIFT_BAD:
        return u"\u4e0d\u5408\u683c", u"\u7cfb\u7edf\u6027\u504f\u4f4e\uff08\u5747\u503c %+.1f \u97f3\u5206\uff09\uff0c\u591a\u4e3a\u6c14\u606f\u652f\u6491\u4e0d\u8db3\u3001\u53e5\u5c3e\u6389\u6c14\u6216\u97f3\u57df\u4e0d\u591f\u9ad8" % m
    if m > SYS_SHIFT:
        return u"\u9700\u6539\u8fdb", u"\u6574\u4f53\u504f\u9ad8 %+.1f \u97f3\u5206\uff0c\u5148\u653e\u677e\u5589\u90e8\u518d\u9010\u97f3\u7ea0\u504f" % m
    if m < -SYS_SHIFT:
        return u"\u9700\u6539\u8fdb", u"\u6574\u4f53\u504f\u4f4e %+.1f \u97f3\u5206\uff0c\u5148\u7ec3\u6c14\u606f\u652f\u6491\u548c\u53e5\u5c3e\u4fdd\u6301" % m
    return u"\u5408\u683c", u"\u65e0\u7cfb\u7edf\u6027\u504f\u79fb\uff08\u5747\u503c %+.1f \u97f3\u5206\uff09" % m


def range_verdict(range_low, range_high, song_low, song_high):
    if range_high is None or range_low is None or song_high is None or song_low is None:
        return u"\u5f85\u786e\u8ba4", u"\u97f3\u57df\u6216\u66f2\u76ee\u97f3\u57df\u672a\u63d0\u4f9b\uff0c\u65e0\u6cd5\u5224\u65ad\u662f\u5426\u8d8a\u754c"
    if float(song_high) > float(range_high):
        gap = float(song_high) - float(range_high)
        return u"\u4e0d\u5408\u683c", u"\u66f2\u76ee\u6700\u9ad8\u97f3\u8d85\u51fa\u8212\u9002\u6700\u9ad8\u97f3 %g \u4e2a\u534a\u97f3\uff0c\u8d8a\u754c\u7684\u9ad8\u97f3\u600e\u4e48\u7ec3\u90fd\u4e0a\u4e0d\u53bb\uff0c\u5148\u6362\u8c03" % gap
    if float(song_low) < float(range_low):
        gap = float(range_low) - float(song_low)
        return u"\u4e0d\u5408\u683c", u"\u66f2\u76ee\u6700\u4f4e\u97f3\u4f4e\u4e8e\u8212\u9002\u6700\u4f4e\u97f3 %g \u4e2a\u534a\u97f3\uff0c\u4f4e\u97f3\u533a\u4f1a\u865a\u4e14\u8dd1\uff0c\u5148\u6362\u8c03" % gap
    return u"\u5408\u683c", u"\u66f2\u76ee\u97f3\u57df\u5728\u8212\u9002\u97f3\u57df\u5185"


def load_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def build_report(data):
    notes = data.get("notes", []) or []
    devs = [float(n.get("dev_cents", 0) or 0) for n in notes]
    n = len(notes)
    v = mae(devs)
    hr = hit_rate(devs)
    sm = signed_mean(devs)
    lv = level_of(v)
    err, bad = direction_errors(notes)
    rv, rmsg = range_verdict(
        data.get("range_low"), data.get("range_high"),
        data.get("song_low"), data.get("song_high"))
    breath = data.get("breath_support", "ok")
    monitor = data.get("monitor_able", True)
    tempo = data.get("tempo_bpm", 80)

    defects = []
    fine = []
    pending = []

    if n == 0:
        pending.append(u"\u672a\u63d0\u4f9b\u9010\u97f3\u504f\u5dee\uff0c\u65e0\u6cd5\u7edf\u8ba1")
    elif n < 4:
        pending.append(u"\u4ec5 %d \u4e2a\u97f3\uff0c\u6837\u672c\u4e0d\u8db3\uff0c\u7ed3\u8bba\u4ec5\u4f9b\u53c2\u8003" % n)

    if lv == u"\u660e\u663e\u8dd1\u8c03":
        defects.append(u"\u5e73\u5747\u7edd\u5bf9\u504f\u5dee %.1f \u97f3\u5206\uff0c\u8fbe\u5230\u660e\u663e\u8dd1\u8c03\uff0c\u5148\u4ece\u5355\u97f3\u6a21\u4eff\u7ec3\u8d77\uff0c\u4e0d\u8981\u7ec3\u6574\u9996\u6b4c" % v)
    elif lv == u"\u660e\u663e\u504f\u79bb":
        fine.append(u"\u5e73\u5747\u7edd\u5bf9\u504f\u5dee %.1f \u97f3\u5206\uff0c\u542c\u4f17\u80fd\u542c\u51fa\u8dd1\u8c03\uff0c\u5148\u505a\u7cfb\u7edf\u6027\u7ea0\u504f" % v)
    if hr is not None and hr < 0.8:
        fine.append(u"\u547d\u4e2d\u7387\u4ec5 %.0f%%\uff0c\u9700\u628a\u9010\u97f3\u504f\u5dee\u538b\u5230 20 \u97f3\u5206\u4ee5\u5185" % (hr * 100))

    sv, smsg = shift_verdict(sm)
    if sv == u"\u4e0d\u5408\u683c":
        defects.append(smsg)
    elif sv == u"\u9700\u6539\u8fdb":
        fine.append(smsg)
    elif sv == u"\u5f85\u786e\u8ba4":
        pending.append(smsg)

    if err > 0:
        defects.append(u"\u97f3\u7a0b\u65b9\u5411\u9519\u8bef %d \u5904\uff08\u7b2c %s \u4e2a\u97f3\u4e4b\u95f4\uff09\uff0c\u56de\u5230\u4e8c\u97f3\u6a21\u8fdb\u5355\u72ec\u7ec3\u8df3\u8fdb" % (
            err, u"\u3001".join(u"%d-%d" % b for b in bad)))

    if rv == u"\u4e0d\u5408\u683c":
        defects.append(rmsg)
    elif rv == u"\u5f85\u786e\u8ba4":
        pending.append(rmsg)

    if not monitor:
        fine.append(u"\u542c\u4e0d\u5230\u81ea\u5df1\u7684\u58f0\u97f3\uff0c\u8fd9\u662f\u6e05\u5531\u8fd8\u884c\u3001\u8ddf\u4f34\u594f\u5c31\u8dd1\u7684\u9996\u8981\u539f\u56e0\uff1a\u538b\u4f4e\u4f34\u594f\u97f3\u91cf\uff0c\u8033\u673a\u53ea\u6234\u4e00\u53ea\u8033\u6735")
    if breath == "weak":
        fine.append(u"\u6c14\u606f\u652f\u6491\u4e0d\u8db3\uff1a\u5148\u7ec3\u5438\u8db3\u540e\u5300\u901f\u5410\u6c14\u6570\u5230 20\uff0c\u518d\u8c08\u97f3\u51c6")
    if float(tempo or 0) > 100.0 and v is not None and v > LEVEL_BASIC:
        fine.append(u"\u901f\u5ea6 %g BPM \u504f\u5feb\u4e14\u504f\u5dee\u5df2\u8fbe %.1f \u97f3\u5206\uff0c\u5148\u964d\u901f\u5230 70 BPM \u7ec3\u51c6\u518d\u63d0\u901f" % (float(tempo), v))

    lines = []
    lines.append("=" * 62)
    lines.append(u"\u5531\u6b4c\u97f3\u51c6\u504f\u5dee\u7edf\u8ba1\u4e0e\u8dd1\u8c03\u5f52\u56e0")
    lines.append("=" * 62)
    lines.append(u"\u6837\u672c\u97f3\u6570\uff1a%d    \u4f34\u594f\u901f\u5ea6\uff1a%g BPM" % (n, float(tempo or 0)))
    lines.append("")
    lines.append(u"[\u4e00] \u504f\u5dee\u7edf\u8ba1")
    lines.append(u"%-18s %s" % (u"\u5e73\u5747\u7edd\u5bf9\u504f\u5dee", (u"%.1f \u97f3\u5206" % v) if v is not None else u"--"))
    lines.append(u"%-18s %s" % (u"\u547d\u4e2d\u7387", (u"%.0f%%" % (hr * 100)) if hr is not None else u"--"))
    lines.append(u"%-18s %s" % (u"\u5e73\u5747\u6709\u7b26\u53f7\u504f\u5dee", (u"%+.1f \u97f3\u5206" % sm) if sm is not None else u"--"))
    lines.append(u"%-18s %s" % (u"\u97f3\u7a0b\u65b9\u5411\u9519\u8bef", u"%d \u5904" % err))
    lines.append(u"%-18s %s" % (u"\u97f3\u51c6\u7b49\u7ea7", lv))
    lines.append(u"%-18s %s" % (u"\u7cfb\u7edf\u6027\u504f\u79fb\u5224\u5b9a", sv))
    lines.append(u"%-18s %s" % (u"\u97f3\u57df\u5224\u5b9a", rv))
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
    lines.append(u"[\u4e94] \u8bad\u7ec3\u5904\u65b9")
    if lv == u"\u660e\u663e\u8dd1\u8c03":
        lines.append(u"  1. \u9636\u6bb5\u4e00\uff1a\u5355\u97f3\u6a21\u4eff\uff0c\u8fde\u7eed 8 \u4e2a\u97f3\u504f\u5dee \u2264 20 \u97f3\u5206\u518d\u8fdb\u9636")
    elif lv == u"\u660e\u663e\u504f\u79bb":
        lines.append(u"  1. \u9636\u6bb5\u4e8c\uff1a\u4e8c\u97f3\u6a21\u8fdb\uff0c\u5148\u89e3\u51b3\u7cfb\u7edf\u6027\u504f\u79fb")
    elif lv == u"\u57fa\u672c\u7a33\u5b9a":
        lines.append(u"  1. \u9636\u6bb5\u4e09\uff1a\u4e00\u4e2a\u516b\u5ea6\u97f3\u9636\u6162\u901f\u4e0a\u4e0b\u884c\uff0c\u538b\u957f\u97f3\u4e0e\u8df3\u8fdb")
    else:
        lines.append(u"  1. \u9636\u6bb5\u56db\u81f3\u4e94\uff1a\u77ed\u53e5\u4e0e\u5e26\u4f34\u594f\uff0c\u547d\u4e2d\u7387\u7ef4\u6301 80%% \u4ee5\u4e0a")
    if err > 0:
        lines.append(u"  2. \u8df3\u8fdb\u5355\u72ec\u7ec3\uff1a\u5148\u628a\u65b9\u5411\u5531\u5bf9\uff0c\u518d\u8c08\u504f\u5dee\u5927\u5c0f")
    if not monitor:
        lines.append(u"  3. \u6539\u76d1\u542c\uff1a\u4f34\u594f\u538b\u5230\u4eba\u58f0\u4e4b\u4e0b\uff0c\u8033\u673a\u53ea\u6234\u4e00\u53ea\u8033\u6735")
    if breath == "weak":
        lines.append(u"  4. \u6c14\u606f\u7ec3\u4e60\u6bcf\u65e5 5 \u5206\u949f\uff1a\u5438\u8db3\u540e\u5300\u901f\u5410\u6c14\u6570\u5230 20")
    lines.append(u"  5. \u6bcf\u8f6e\u8bad\u7ec3\u5f55\u97f3\u56de\u542c\uff0c\u53ea\u6807\u504f\u9ad8\u504f\u4f4e\u65b9\u5411\u9519\uff0c\u4e0d\u505a\u60c5\u7eea\u8bc4\u4ef7")
    lines.append(u"  6. \u6bcf\u4e24\u5468\u7528\u540c\u4e00\u9996\u6d4b\u8bd5\u66f2\u590d\u8bc4\uff0c\u770b\u5e73\u5747\u7edd\u5bf9\u504f\u5dee\u662f\u5426\u4e0b\u964d 10 \u97f3\u5206\u4ee5\u4e0a")

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
    lines.append(u"\u63d0\u793a\uff1a\u58f0\u5636\u8d85\u8fc7\u4e24\u5468\u3001\u542c\u529b\u4e0b\u964d\u3001\u80f8\u95f7\u6c14\u77ed\u65f6\u505c\u6b62\u8bad\u7ec3\u5e76\u5c31\u533b\u3002")
    lines.append(u"\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u97f3\u51c6\u81ea\u67e5\u8f93\u51fa\uff0c\u4e0d\u6784\u6210\u533b\u5b66\u8bca\u65ad\u6216\u58f0\u4e50\u6c34\u5e73\u8bc4\u4ef7\u3002")
    lines.append("=" * 62)

    summary = {
        "note_count": n,
        "mae": v,
        "hit_rate": hr,
        "signed_mean": sm,
        "level": lv,
        "direction_errors": err,
        "shift_verdict": sv,
        "range_verdict": rv,
        "defects": defects,
        "fine": fine,
        "pending": pending,
        "overall": overall,
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append((u"\u5e73\u5747\u7edd\u5bf9\u504f\u5dee\u8ba1\u7b97", abs(mae([10.0, -10.0, 20.0]) - 13.3333) < 1e-3))
    r.append((u"\u547d\u4e2d\u7387\u8ba1\u7b97", abs(hit_rate([10.0, 30.0, -50.0]) - 1.0 / 3.0) < 1e-9))
    r.append((u"\u6709\u7b26\u53f7\u5747\u503c\u8ba1\u7b97", abs(signed_mean([-10.0, -30.0]) + 20.0) < 1e-9))
    r.append((u"\u7a7a\u6837\u672c\u8fd4\u56de None", mae([]) is None and hit_rate([]) is None))
    r.append((u"\u7b49\u7ea7\u6620\u5c04", level_of(15.0) == u"\u97f3\u51c6\u7a33\u5b9a" and level_of(70.0) == u"\u660e\u663e\u8dd1\u8c03"))

    e, _ = direction_errors([{"target_midi": 60, "dev_cents": 0},
                             {"target_midi": 62, "dev_cents": 0}])
    r.append((u"\u540c\u5411\u97f3\u7a0b\u65e0\u65b9\u5411\u9519\u8bef", e == 0))
    e2, _ = direction_errors([{"target_midi": 60, "dev_cents": 0},
                              {"target_midi": 61, "dev_cents": -150}])
    r.append((u"\u53cd\u4f8b\uff1a\u76ee\u6807\u4e0a\u884c\u5b9e\u9645\u4e0b\u884c\u5224\u65b9\u5411\u9519\u8bef", e2 == 1))
    e3, _ = direction_errors([{"target_midi": 61, "dev_cents": -150},
                              {"target_midi": 60, "dev_cents": 0}])
    r.append((u"\u53cd\u4f8b\uff1a\u76ee\u6807\u4e0b\u884c\u5b9e\u9645\u4e0a\u884c\u5224\u65b9\u5411\u9519\u8bef", e3 == 1))

    _, s = build_report({
        "notes": [{"target_midi": 60 + i, "dev_cents": 8 * (i % 3) - 8} for i in range(8)],
        "range_low": 55, "range_high": 72, "song_low": 57, "song_high": 70,
        "breath_support": "ok", "monitor_able": True, "tempo_bpm": 80,
    })
    r.append((u"\u6b63\u5e38\u6837\u4f8b\u5224\u5b9a\u5408\u683c", s["overall"] == u"\u5408\u683c"))

    _, s1 = build_report({
        "notes": [{"target_midi": 60, "dev_cents": -80} for _ in range(8)],
        "range_low": 55, "range_high": 72, "song_low": 57, "song_high": 70,
        "breath_support": "ok", "monitor_able": True, "tempo_bpm": 80,
    })
    r.append((u"\u53cd\u4f8b\uff1a\u6574\u4f53\u504f\u4f4e 80 \u97f3\u5206\u5224\u4e0d\u5408\u683c", s1["overall"] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u660e\u663e\u8dd1\u8c03\u8fdb\u7f3a\u9677\u8868", any(u"\u660e\u663e\u8dd1\u8c03" in d for d in s1["defects"])))

    _, s2 = build_report({
        "notes": [{"target_midi": 60, "dev_cents": 0},
                  {"target_midi": 61, "dev_cents": -150},
                  {"target_midi": 62, "dev_cents": 0},
                  {"target_midi": 63, "dev_cents": 0}],
        "range_low": 55, "range_high": 72, "song_low": 57, "song_high": 70,
        "breath_support": "ok", "monitor_able": True, "tempo_bpm": 80,
    })
    r.append((u"\u53cd\u4f8b\uff1a\u65b9\u5411\u9519\u8bef\u5224\u4e0d\u5408\u683c", s2["overall"] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u65b9\u5411\u9519\u8bef\u8fdb\u7f3a\u9677\u8868", any(u"\u97f3\u7a0b\u65b9\u5411\u9519\u8bef" in d for d in s2["defects"])))

    _, s3 = build_report({
        "notes": [{"target_midi": 60 + i, "dev_cents": 5} for i in range(8)],
        "range_low": 55, "range_high": 72, "song_low": 57, "song_high": 78,
        "breath_support": "ok", "monitor_able": True, "tempo_bpm": 80,
    })
    r.append((u"\u53cd\u4f8b\uff1a\u66f2\u76ee\u8d85\u51fa\u97f3\u57df\u5224\u4e0d\u5408\u683c", s3["overall"] == u"\u4e0d\u5408\u683c"))
    r.append((u"\u53cd\u4f8b\uff1a\u97f3\u57df\u8d8a\u754c\u8fdb\u7f3a\u9677\u8868", any(u"\u6362\u8c03" in d for d in s3["defects"])))

    _, s4 = build_report({
        "notes": [{"target_midi": 60, "dev_cents": -95},
                  {"target_midi": 61, "dev_cents": -90}],
        "range_low": 55, "range_high": 72, "song_low": 57, "song_high": 70,
        "breath_support": "ok", "monitor_able": True, "tempo_bpm": 80,
    })
    r.append((u"\u53cd\u4f8b\uff1a\u6837\u672c\u4e0d\u8db3\u4f46\u504f\u5dee\u5de8\u5927\u4e0d\u5f97\u5224\u5f85\u786e\u8ba4", s4["overall"] == u"\u4e0d\u5408\u683c"))

    _, s5 = build_report({"notes": []})
    r.append((u"\u65e0\u9010\u97f3\u6570\u636e\u8bb0\u4e3a\u5f85\u786e\u8ba4", s5["overall"] == u"\u5f85\u786e\u8ba4"))

    _, s6 = build_report({
        "notes": [{"target_midi": 60 + i, "dev_cents": 5} for i in range(8)],
        "range_low": 55, "range_high": 72, "song_low": 57, "song_high": 70,
        "breath_support": "weak", "monitor_able": False, "tempo_bpm": 80,
    })
    r.append((u"\u76d1\u542c\u4e0e\u6c14\u606f\u95ee\u9898\u5224\u9700\u6539\u8fdb", s6["overall"] == u"\u9700\u6539\u8fdb"))
    r.append((u"\u76d1\u542c\u95ee\u9898\u8fdb\u9700\u6539\u8fdb\u8868", any(u"\u542c\u4e0d\u5230\u81ea\u5df1" in d for d in s6["fine"])))

    p = os.path.join(tempfile.gettempdir(), "_singing_bom_case.json")
    blob = b"\xef\xbb\xbf" + json.dumps({
        "notes": [{"target_midi": 60, "dev_cents": 5}],
        "range_low": 55, "range_high": 72, "song_low": 57, "song_high": 70,
    }, ensure_ascii=False).encode("utf-8")
    with open(p, "wb") as f:
        f.write(blob)
    try:
        d = load_json(p)
        r.append((u"UTF-8 BOM \u8f93\u5165\u9996\u952e\u53ef\u8bfb", len(d.get("notes", [])) == 1))
        r.append((u"UTF-8 BOM \u8f93\u5165\u6570\u503c\u53ef\u8bfb", abs(d["notes"][0]["dev_cents"] - 5.0) < 1e-9))
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
    parser = argparse.ArgumentParser(description=u"\u5531\u6b4c\u97f3\u51c6\u504f\u5dee\u7edf\u8ba1\u5de5\u5177")
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
