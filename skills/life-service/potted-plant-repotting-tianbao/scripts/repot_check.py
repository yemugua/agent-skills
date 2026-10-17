# -*- coding: utf-8 -*-
"""\u76c6\u683d\u6362\u76c6\u65f6\u673a\u5224\u522b\u4e0e\u914d\u6bd4\u6838\u7b97\u5de5\u5177\u3002

\u7528\u6cd5:
  python repot_check.py --file pot.json [--json]
  python repot_check.py --selftest

\u672c\u5de5\u5177\u4e0d\u8bca\u65ad\u6839\u8150\u75c5\u539f, \u4e0d\u7ed9\u836f\u5242\u4e0e\u80a5\u6599\u54c1\u724c\u3002
"""
import argparse
import io
import json
import os
import sys

# \u914d\u571f\u6bd4\u4f8b: \u57fa\u8d28 : \u9897\u7c92 : \u6709\u673a
MIX = {
    "foliage": {"name": "\u89c2\u53f6\u7eff\u690d", "base": 5, "grit": 3, "org": 2},
    "succulent": {"name": "\u591a\u8089\u4e0e\u4ed9\u4eba\u638c", "base": 3, "grit": 6, "org": 1},
    "flowering": {"name": "\u5f00\u82b1\u690d\u7269", "base": 5, "grit": 3, "org": 2},
    "orchid": {"name": "\u5170\u82b1\u7c7b", "base": 6, "grit": 4, "org": 0},
    "woody": {"name": "\u6728\u672c\u76c6\u683d", "base": 4, "grit": 4, "org": 2},
    "veg": {"name": "\u9633\u53f0\u53f6\u83dc", "base": 5, "grit": 3, "org": 2},
    "general": {"name": "\u901a\u7528\u578b", "base": 5, "grit": 3, "org": 2},
}

# \u65f6\u673a\u7ea2\u7ebf\u9636\u6bb5
PHASES = {
    "flower": "\u6b63\u5728\u5f00\u82b1\u6216\u5373\u5c06\u5f00\u82b1, \u82b1\u671f\u5bf9\u6839\u7cfb\u6270\u52a8\u654f\u611f",
    "summer_dormant": "\u590f\u5b63\u9ad8\u6e29\u4f11\u7720\u671f, \u6839\u7cfb\u6d3b\u6027\u4f4e, \u7f13\u82d7\u671f\u957f",
    "recent_move": "\u521a\u6362\u8fc7\u73af\u5883, \u5df2\u5728\u9002\u5e94\u671f, \u53e0\u52a0\u6362\u76c6\u6613\u5931\u6c34",
    "recovering": "\u6b63\u5728\u7f13\u82d7\u671f, \u4e8c\u6b21\u6270\u52a8\u4f1a\u653e\u5927\u635f\u4f24",
    "unwell": "\u690d\u682a\u660e\u663e\u75c5\u5f31\u4e14\u75c5\u56e0\u672a\u67e5\u660e",
    "stable": "\u7a33\u5b9a\u751f\u957f\u671f, \u53ef\u4ee5\u5b89\u6392\u6362\u76c6",
}


def new_pot_size(old):
    d = float(old or 0)
    if d <= 0:
        return 0
    if d < 10:
        return d + 2
    if d < 20:
        return d + 3
    if d < 30:
        return d + 4
    return d + 5


def jump_note(old):
    d = float(old or 0)
    if d <= 0:
        return "\u539f\u76c6\u53e3\u5f84\u672a\u63d0\u4f9b, \u65e0\u6cd5\u7ed9\u51fa\u53e3\u5f84"
    if d < 10:
        return "\u5c0f\u76c6\u53ef\u7565\u6fc0\u8fdb, \u52a0 2 cm"
    if d < 20:
        return "\u5e38\u89c4\u8df3\u8dc3, \u52a0 3 cm"
    if d < 30:
        return "\u5927\u76c6\u9700\u7ed9\u6839\u7cfb\u66f4\u591a\u7a7a\u95f4, \u52a0 4 cm"
    return "\u8d85\u5927\u76c6, \u52a0 5 cm"


def signal_count(data):
    keys = (("root_bound", "\u6839\u7cfb\u76d8\u6839"),
            ("drain_water", "\u76c6\u5e95\u5b54\u51fa\u6c34"),
            ("soil_compact", "\u571f\u677f\u7ed3"))
    hits = []
    for k, label in keys:
        if bool(data.get(k, False)):
            hits.append(label)
    return hits


def decide_repot(hits, phase):
    n = len(hits)
    if phase in PHASES and phase != "stable":
        return "\u6682\u4e0d\u6362", "\u5148\u5904\u7406\u65f6\u673a\u7ea2\u7ebf, \u6362\u76c6\u5f80\u540e\u653e"
    if n == 0:
        return "\u6682\u4e0d\u6362", "\u4e09\u7c7b\u5224\u636e\u5747\u672a\u547d\u4e2d, \u76ee\u524d\u4e0d\u9700\u8981\u6362\u76c6"
    if n == 1:
        return "\u53ef\u5b89\u6392", "\u547d\u4e2d 1 \u9879\u5224\u636e, \u53ef\u5728\u6625\u79cb\u4e24\u5b63\u9009\u62e9\u8fde\u7eed\u9634\u5929\u6216\u508d\u665a\u6362\u76c6"
    return "\u5e94\u5c3d\u5feb\u6362", "\u547d\u4e2d %d \u9879\u5224\u636e, \u8d8a\u62d6\u6839\u533a\u8d8a\u7d27, \u5c3d\u5feb\u5b89\u6392\u6362\u76c6" % n


SYMPTOMS = {
    "yellow_wilt": ("\u6362\u76c6\u540e 1 \u5468\u5185\u53f6\u7247\u5927\u9762\u79ef\u53d1\u9ec4\u840e\u852b",
                    "\u6839\u7cfb\u53d7\u635f\u672a\u7f13\u82d7, \u6216\u6d47\u6c34\u8fc7\u591a",
                    "\u505c\u6c34 3-5 \u5929\u89c2\u5bdf, \u51cf\u5c11\u6d47\u6c34\u9891\u6b21"),
    "leaf_drop": ("\u6362\u76c6\u540e\u7acb\u523b\u6301\u7eed\u843d\u53f6",
                  "\u6839\u7cfb\u635f\u4f24\u8fc7\u5927\u6216\u571f\u4e0d\u900f\u6c14",
                  "\u68c0\u67e5\u76c6\u571f\u6e7f\u5ea6\u4e0e\u901a\u6c14, \u5fc5\u8981\u65f6\u91cd\u65b0\u4e0a\u76c6"),
    "bud_black": ("\u65b0\u53f6\u4e0d\u5c55, \u9876\u82bd\u53d1\u9ed1",
                  "\u6839\u7cfb\u6b7b\u4ea1\u6216\u70c2\u6839",
                  "\u8131\u76c6\u68c0\u6839, \u4fee\u9664\u8910\u9ed1\u8f6f\u70c2\u6839\u5e76\u6362\u758f\u677e\u571f"),
    "wet_smell": ("\u76c6\u571f\u957f\u671f\u4e0d\u5e72, \u6709\u5f02\u5473",
                  "\u76c6\u592a\u5927\u571f\u592a\u591a, \u6216\u571f\u4e0d\u900f\u6c14",
                  "\u51cf\u5c11\u6d47\u6c34, \u52a0\u5f3a\u901a\u98ce; \u5fc5\u8981\u65f6\u6362\u5c0f\u4e00\u53f7\u76c6"),
    "bottom_black": ("\u5e95\u90e8\u53f6\u7247\u53d1\u9ed1\u53d1\u8f6f",
                     "\u6839\u533a\u957f\u671f\u8fc7\u6e7f",
                     "\u505c\u6c34, \u57ab\u9ad8\u82b1\u76c6\u6539\u5584\u5e95\u90e8\u901a\u98ce"),
    "drain_slow": ("\u76c6\u5e95\u5b54\u5927\u91cf\u6e17\u6c34\u4e14\u571f\u677f\u7ed3",
                   "\u65e7\u571f\u677f\u7ed3\u672a\u6362\u900f",
                   "\u5c3d\u5feb\u5b89\u6392\u6362\u76c6\u5e76\u6362\u900f\u6c14\u914d\u571f"),
}

RECOVERY = [
    ("\u65f6\u957f", "2-4 \u5468; \u9634\u5929\u4e0e\u534a\u9634\u5904\u53ef\u5230 4-6 \u5468"),
    ("\u5149\u7167", "\u6563\u5c04\u5149\u6216\u534a\u9634, \u907f\u514d\u66b4\u6652, \u9010\u6b65\u9002\u5e94\u540e\u518d\u79fb\u5230\u5168\u65e5\u7167\u4f4d"),
    ("\u6d47\u6c34", "\u89c1\u5e72\u89c1\u6e7f, \u6bd4\u7f13\u82d7\u524d\u7565\u51cf; \u571f\u9762 2-3 cm \u5e72\u4e86\u518d\u6d47"),
    ("\u65bd\u80a5", "\u7f13\u82d7\u671f\u5185\u4e0d\u65bd\u80a5, \u81f3\u5c11 4-6 \u5468"),
    ("\u4fee\u526a", "\u4e0d\u505a\u5927\u4fee, \u53ea\u526a\u660e\u663e\u67af\u840e\u90e8\u5206"),
    ("\u79fb\u76c6", "\u7f13\u82d7\u671f\u5185\u4e0d\u642c\u52a8\u4f4d\u7f6e"),
    ("\u8f6c\u76c6", "\u6bcf 7-10 \u5929\u8f6c\u4e00\u6b21\u65b9\u5411, \u907f\u514d\u504f\u51a0"),
    ("\u6e29\u6e7f\u5ea6", "\u907f\u5f00\u7a7a\u8c03\u76f4\u5439, \u6696\u6c14\u53e3, \u95e8\u7a97\u51b7\u98ce"),
]


def mix_text(key):
    m = MIX.get(key) or MIX["general"]
    total = m["base"] + m["grit"] + m["org"]
    return m, total


def build_report(data):
    old_d = data.get("pot_diameter_cm", 0)
    plant = data.get("plant_type", "")
    phase = (data.get("phase", "") or "").strip()
    symptoms = data.get("symptoms", []) or []

    lines = []
    summary = {
        "decision": None, "signals": [], "signal_count": None,
        "new_pot_cm": None, "mix_name": None,
        "dose": None, "symptoms": [], "chemical_recommended": False,
    }

    lines.append("=" * 68)
    lines.append("\u76c6\u683d\u6362\u76c6\u65f6\u673a\u5224\u522b\u4e0e\u914d\u6bd4\u6838\u7b97")
    lines.append("=" * 68)

    lines.append("[\u4e00] \u6362\u76c6\u5224\u636e\u6838\u5bf9")
    lines.append("-" * 68)
    hits = signal_count(data)
    summary["signals"] = hits
    summary["signal_count"] = len(hits)
    for label in ("\u6839\u7cfb\u76d8\u6839", "\u76c6\u5e95\u5b54\u51fa\u6c34", "\u571f\u677f\u7ed3"):
        lines.append("  [%s] %s" % ("\u547d\u4e2d" if label in hits else "\u672a\u547d\u4e2d", label))
    lines.append("  \u547d\u4e2d\u9879\u6570: %d" % len(hits))
    lines.append("")

    lines.append("[\u4e8c] \u65f6\u673a\u7ea2\u7ebf")
    lines.append("-" * 68)
    if phase and phase != "stable":
        lines.append("  [\u7ea2\u7ebf] \u5f53\u524d\u9636\u6bb5: %s" % PHASES.get(phase, "\u672a\u767b\u8bb0\u9636\u6bb5, \u9700\u4eba\u5de5\u786e\u8ba4"))
        lines.append("    \u542b\u4e49: %s" % PHASES.get(phase, ""))
        lines.append("    \u5904\u7f6e: \u8fd9\u56db\u79cd\u60c5\u51b5\u4e4b\u4e00\u4e0d\u6362\u76c6, \u7b49\u8fc7\u4e86\u518d\u5b89\u6392")
    elif phase == "stable":
        lines.append("  \u5f53\u524d\u9636\u6bb5: \u7a33\u5b9a\u751f\u957f\u671f, \u53ef\u4ee5\u5b89\u6392\u6362\u76c6")
    else:
        lines.append("  \u672a\u63d0\u4f9b\u5f53\u524d\u9636\u6bb5, \u8bf7\u81ea\u67e5\u662f\u5426\u5904\u4e8e\u82b1\u671f, \u9ad8\u6e29\u4f11\u7720\u671f, \u521a\u632a\u8fc7\u4f4d\u7f6e\u6216\u7f13\u82d7\u671f\u5185")
    lines.append("")
    lines.append("  \u65f6\u673a\u7ea2\u7ebf\u4e00\u89c8:")
    for k in ("flower", "summer_dormant", "recent_move", "recovering", "unwell"):
        lines.append("    %-14s %s" % (k, PHASES[k]))
    lines.append("")

    lines.append("[\u4e09] \u662f\u5426\u8be5\u6362\u76c6")
    lines.append("-" * 68)
    decision, why = decide_repot(hits, phase)
    summary["decision"] = decision
    lines.append("  \u7ed3\u8bba: %s" % decision)
    lines.append("    \u7406\u7531: %s" % why)
    lines.append("")

    lines.append("[\u56db] \u65b0\u76c6\u53e3\u5f84 (\u539f\u76c6 %g cm)" % float(old_d or 0))
    lines.append("-" * 68)
    np = new_pot_size(old_d)
    summary["new_pot_cm"] = np
    lines.append("  \u5efa\u8bae\u65b0\u76c6\u53e3\u5f84: %g cm" % np)
    lines.append("    \u8df3\u8dc3\u5e45\u5ea6: %s" % jump_note(old_d))
    lines.append("    \u8fb9\u754c: \u4e0d\u8de8\u7ea7\u653e\u5927; \u5b81\u53ef\u7528\u5c0f\u4e00\u53f7\u76c6, \u4e5f\u4e0d\u8981\u7528\u5927\u4e00\u53f7\u7684\u76c6")
    lines.append("    \u539f\u56e0: \u76c6\u5927\u571f\u591a\u6d47\u4e0d\u900f, \u591a\u4f59\u6e7f\u571f\u957f\u671f\u4e0d\u5e72, \u6839\u7cfb\u95f7\u5728\u6e7f\u571f\u91cc")
    lines.append("")

    lines.append("[\u4e94] \u914d\u571f\u6bd4\u4f8b")
    lines.append("-" * 68)
    m, total = mix_text(plant)
    summary["mix_name"] = m["name"]
    lines.append("  \u9002\u7528\u7c7b\u578b: %s" % m["name"])
    lines.append("    \u57fa\u8d28(\u6ce5\u70ad\u6216\u6930\u7ce0) : \u9897\u7c92(\u73cd\u73e0\u5ca9\u6216\u6d6e\u77f3) : \u6709\u673a(\u8150\u53f6\u571f\u6216\u5806\u80a5)")
    lines.append("    %d : %d : %d" % (m["base"], m["grit"], m["org"]))
    dose = []
    pcts = []
    for k, v in (("\u57fa\u8d28", m["base"]), ("\u9897\u7c92", m["grit"]), ("\u6709\u673a", m["org"])):
        pct = 0.0
        if total:
            pct = round(v * 100.0 / total, 1)
        pcts.append(pct)
        dose.append("%s %.1f%% (%d \u4efd)" % (k, pct, v))
    summary["mix_pct"] = pcts
    summary["dose"] = dose
    lines.append("    \u4f53\u79ef\u5360\u6bd4: %s" % " / ".join(dose))
    lines.append("    \u914d\u571f\u4e09\u6761\u786c\u8981\u6c42: \u9897\u7c92\u6599\u4e0d\u80fd\u7701; \u6709\u673a\u6599\u5fc5\u987b\u8150\u719f; \u65b0\u571f\u5148\u6da6\u6e7f")
    lines.append("    \u76c6\u5e95\u57ab\u5c42: 2-3 cm \u8db3\u591f, \u57ab\u592a\u539a\u4f1a\u8ba9\u6392\u6c34\u53d8\u6162; \u4e0d\u57ab\u4e5f\u53ef, \u53ea\u8981\u5b54\u4e0d\u5835")
    lines.append("")
    lines.append("  \u5404\u7c7b\u578b\u914d\u6bd4\u5bf9\u7167:")
    for k in ("foliage", "succulent", "flowering", "orchid", "woody", "veg", "general"):
        v = MIX[k]
        lines.append("    %-14s %d : %d : %d" % (v["name"], v["base"], v["grit"], v["org"]))
    lines.append("")

    lines.append("[\u516d] \u5931\u8d25\u5f81\u5146\u5904\u7f6e")
    lines.append("-" * 68)
    if not symptoms:
        lines.append("  \u672a\u63d0\u4f9b\u5931\u8d25\u5f81\u5146")
    for s in symptoms:
        s = s.strip()
        if not s:
            continue
        if s in SYMPTOMS:
            sign, cause, action = SYMPTOMS[s]
            lines.append("  [\u5f02\u5e38] %s" % sign)
            lines.append("    \u53ef\u80fd\u539f\u56e0: %s" % cause)
            lines.append("    \u5904\u7f6e\u53e3\u5f84: %s" % action)
            summary["symptoms"].append(s)
        else:
            lines.append("  [\u672a\u767b\u8bb0] %s -> \u9700\u4eba\u5de5\u6bd4\u5bf9\u5f81\u5146\u8868" % s)
    lines.append("")
    lines.append("  \u5224\u522b\u8981\u70b9: \u6362\u76c6\u540e\u4e00\u5468\u5185\u8f7b\u5fae\u9ec4\u53f6\u5c5e\u5e38\u89c1\u7f13\u82d7\u53cd\u5e94;")
    lines.append("            \u6301\u7eed\u843d\u53f6, \u65b0\u53f6\u4e0d\u5c55, \u9876\u82bd\u53d1\u9ed1\u5219\u8d85\u51fa\u6b63\u5e38\u7f13\u82d7\u8303\u56f4")
    lines.append("")

    lines.append("[\u4e03] \u7f13\u82d7\u671f\u7ba1\u7406")
    lines.append("-" * 68)
    for k, v in RECOVERY:
        lines.append("  %-6s %s" % (k, v))
    lines.append("")
    lines.append("\u514d\u8d23: \u672c\u7ed3\u679c\u4e3a\u6362\u76c6\u65f6\u673a\u4e0e\u914d\u6bd4\u53e3\u5f84, \u4e0d\u6784\u6210\u75c5\u5bb3\u8bca\u65ad\u6216\u56ed\u6797\u6280\u672f\u7ed3\u8bba\u3002")
    lines.append("\u514d\u8d23: \u836f\u5242\u4e0e\u80a5\u6599\u4ee5\u4ea7\u54c1\u6807\u7b7e\u8bf4\u660e\u548c\u5f53\u5730\u4e3b\u7ba1\u90e8\u95e8\u8981\u6c42\u4e3a\u51c6\u3002")
    lines.append("=" * 68)
    return "\n".join(lines), summary


def load_json(path):
    with io.open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()
    # PowerShell \u5199\u51fa\u7684 UTF-8 \u6587\u4ef6\u53ef\u80fd\u5e26 BOM, \u4e0d\u5265\u6389\u4f1a\u8ba9\u9996\u4e2a key \u53d6\u4e0d\u5230\u503c\u4e14\u4e0d\u62a5\u9519
    raw = raw.lstrip("\ufeff")
    return json.loads(raw)


def _run_checks():
    r = []
    r.append(("8 cm \u76c6\u52a0 2 cm", new_pot_size(8) == 10))
    r.append(("15 cm \u76c6\u52a0 3 cm", new_pot_size(15) == 18))
    r.append(("25 cm \u76c6\u52a0 4 cm", new_pot_size(25) == 29))
    r.append(("35 cm \u76c6\u52a0 5 cm", new_pot_size(35) == 40))
    r.append(("\u53e3\u5f84\u4e3a 0 \u65f6\u8fd4\u56de 0", new_pot_size(0) == 0))
    r.append(("\u901a\u7528\u578b\u914d\u6bd4\u6b63\u786e",
              (MIX["general"]["base"], MIX["general"]["grit"], MIX["general"]["org"]) == (5, 3, 2)))
    r.append(("\u591a\u8089\u9897\u7c92\u5360\u6bd4\u66f4\u9ad8", MIX["succulent"]["grit"] == 6))
    r.append(("\u5170\u82b1\u4e0d\u542b\u6709\u673a\u6599", MIX["orchid"]["org"] == 0))
    r.append(("\u6728\u672c\u914d\u6bd4 4 \u6bd4 4 \u6bd4 2",
              (MIX["woody"]["base"], MIX["woody"]["grit"], MIX["woody"]["org"]) == (4, 4, 2)))
    r.append(("\u672a\u767b\u8bb0\u7c7b\u578b\u56de\u843d\u901a\u7528\u578b", mix_text("nope")[0]["name"] == "\u901a\u7528\u578b"))
    r.append(("\u89c2\u53f6\u7eff\u690d\u914d\u6bd4\u4e0e\u901a\u7528\u578b\u76f8\u540c",
              mix_text("foliage")[0]["grit"] == mix_text("general")[0]["grit"]))

    r.append(("\u65e0\u547d\u4e2d\u4e14\u7a33\u5b9a\u671f\u4e0d\u6362",
              decide_repot([], "stable")[0] == "\u6682\u4e0d\u6362"))
    r.append(("\u547d\u4e2d 1 \u9879\u53ef\u5b89\u6392",
              decide_repot(["\u6839\u7cfb\u76d8\u6839"], "stable")[0] == "\u53ef\u5b89\u6392"))
    r.append(("\u547d\u4e2d 3 \u9879\u5e94\u5c3d\u5feb\u6362",
              decide_repot(["\u6839\u7cfb\u76d8\u6839", "\u76c6\u5e95\u5b54\u51fa\u6c34", "\u571f\u677f\u7ed3"], "stable")[0] == "\u5e94\u5c3d\u5feb\u6362"))
    r.append(("\u82b1\u671f\u547d\u4e2d\u4e5f\u4e0d\u6362",
              decide_repot(["\u6839\u7cfb\u76d8\u6839", "\u571f\u677f\u7ed3"], "flower")[0] == "\u6682\u4e0d\u6362"))
    r.append(("\u4f11\u7720\u671f\u547d\u4e2d\u4e5f\u4e0d\u6362",
              decide_repot(["\u571f\u677f\u7ed3"], "summer_dormant")[0] == "\u6682\u4e0d\u6362"))
    r.append(("\u7f13\u82d7\u671f\u547d\u4e2d\u4e5f\u4e0d\u6362",
              decide_repot(["\u6839\u7cfb\u76d8\u6839"], "recovering")[0] == "\u6682\u4e0d\u6362"))
    r.append(("\u75c5\u56e0\u672a\u660e\u547d\u4e2d\u4e5f\u4e0d\u6362",
              decide_repot(["\u76c6\u5e95\u5b54\u51fa\u6c34"], "unwell")[0] == "\u6682\u4e0d\u6362"))
    r.append(("\u521a\u632a\u8fc7\u4f4d\u7f6e\u547d\u4e2d\u4e5f\u4e0d\u6362",
              decide_repot(["\u571f\u677f\u7ed3"], "recent_move")[0] == "\u6682\u4e0d\u6362"))

    base = {"root_bound": False, "drain_water": False, "soil_compact": False}
    r.append(("\u5168\u672a\u547d\u4e2d\u8ba1\u6570\u4e3a 0", len(signal_count(base)) == 0))
    r.append(("\u547d\u4e2d\u76d8\u6839\u8ba1\u6570\u4e3a 1",
              len(signal_count(dict(base, root_bound=True))) == 1))
    r.append(("\u547d\u4e2d\u4e24\u9879\u8ba1\u6570\u4e3a 2",
              len(signal_count(dict(base, root_bound=True, soil_compact=True))) == 2))
    r.append(("\u5f81\u5146\u8868\u5171 6 \u6761", len(SYMPTOMS) == 6))
    r.append(("\u7f13\u82d7\u671f\u5171 8 \u9879", len(RECOVERY) == 8))
    r.append(("\u5ae9\u53f6\u53d1\u9ed1\u914d\u5904\u7f6e", "\u4fee\u9664" in SYMPTOMS["bud_black"][2]))
    r.append(("\u76c6\u571f\u4e0d\u5e72\u914d\u51cf\u6d47", "\u51cf\u5c11\u6d47\u6c34" in SYMPTOMS["wet_smell"][2]))

    txt, s = build_report({
        "pot_diameter_cm": 15, "root_bound": True, "drain_water": False,
        "soil_compact": True, "plant_type": "flowering",
        "phase": "stable", "symptoms": ["yellow_wilt"],
    })
    r.append(("\u6837\u4f8b\u5224\u4e3a\u5e94\u5c3d\u5feb\u6362", s["decision"] == "\u5e94\u5c3d\u5feb\u6362"))
    r.append(("\u6837\u4f8b\u547d\u4e2d 2 \u9879", s["signal_count"] == 2))
    r.append(("\u6837\u4f8b\u65b0\u76c6 18 cm", s["new_pot_cm"] == 18))
    r.append(("\u6837\u4f8b\u914d\u571f\u4e3a\u5f00\u82b1\u690d\u7269", s["mix_name"] == "\u5f00\u82b1\u690d\u7269"))
    r.append(("\u6837\u4f8b\u8bb0\u5f55\u5f81\u5146", s["symptoms"] == ["yellow_wilt"]))
    r.append(("\u6837\u4f8b\u4e0d\u63a8\u8350\u836f\u5242", s["chemical_recommended"] is False))
    r.append(("\u6837\u4f8b\u6587\u672c\u542b\u5224\u522b\u8981\u70b9", "\u5224\u522b\u8981\u70b9" in txt))
    r.append(("\u6837\u4f8b\u5360\u6bd4\u5408\u8ba1 100", round(sum(s["mix_pct"]), 1) == 100.0))

    _, s2 = build_report({})
    r.append(("\u7a7a\u8f93\u5165\u4e0d\u62a5\u9519", s2["decision"] == "\u6682\u4e0d\u6362"))
    r.append(("\u7a7a\u8f93\u5165\u65e0\u5f81\u5146", s2["symptoms"] == []))
    r.append(("\u7a7a\u8f93\u5165\u56de\u843d\u901a\u7528\u578b", s2["mix_name"] == "\u901a\u7528\u578b"))

    _, s3 = build_report({"pot_diameter_cm": 35, "plant_type": "orchid",
                          "symptoms": ["bud_black", "nope"]})
    r.append(("\u8d85\u5927\u76c6 40 cm", s3["new_pot_cm"] == 40))
    r.append(("\u5170\u82b1\u6709\u673a\u6599\u4e3a 0", "\u6709\u673a 0.0%" in s3["dose"][2]))
    r.append(("\u672a\u767b\u8bb0\u5f81\u5146\u88ab\u5ffd\u7565", s3["symptoms"] == ["bud_black"]))

    r.append(("BOM \u8f93\u5165\u88ab\u6b63\u786e\u5265\u79bb",
               load_json(_write_bom_sample())["pot_diameter_cm"] == 15))
    r.append(("\u5b57\u7b26\u4e32\u5f62\u5f0f\u7684\u5f81\u5146\u53ef\u89e3\u6790",
               build_report({"symptoms": ["leaf_drop"]})[1]["symptoms"] == ["leaf_drop"]))
    return r


def _write_bom_sample():
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "_selftest_bom_sample.json")
    with io.open(p, "w", encoding="utf-8") as f:
        f.write("\ufeff{\"pot_diameter_cm\": 15, \"phase\": \"stable\"}")
    return p


def selftest():
    results = _run_checks()
    failed = [name for name, ok in results if not ok]
    ok = len(failed) == 0
    lines = ["SELFTEST %s" % ("OK" if ok else "FAILED")]
    lines.append("checks=%d passed=%d failed=%d" % (
        len(results), len(results) - len(failed), len(failed)))
    for name in failed:
        lines.append("FAILED: %s" % name)
    here = os.path.dirname(os.path.abspath(__file__))
    with io.open(os.path.join(here, "_selftest_result.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    return ok


def main():
    parser = argparse.ArgumentParser(
        description="\u76c6\u683d\u6362\u76c6\u65f6\u673a\u5224\u522b\u4e0e\u914d\u6bd4\u6838\u7b97\u5de5\u5177")
    parser.add_argument("--file", help="\u8f93\u5165 JSON \u6587\u4ef6\u8def\u5f84 (UTF-8)")
    parser.add_argument("--json", action="store_true", help="\u4ee5 JSON \u8f93\u51fa")
    parser.add_argument("--out", help="\u7ed3\u679c\u5199\u5165\u6307\u5b9a\u6587\u4ef6")
    parser.add_argument("--selftest", action="store_true", help="\u8fd0\u884c\u81ea\u68c0")
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))

    if args.selftest:
        sys.exit(0 if selftest() else 1)

    if not args.file:
        parser.error("\u9700\u8981 --file \u6216 --selftest")

    data = load_json(args.file)
    report, summary = build_report(data)
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else report
    out_path = args.out or os.path.join(here, "_last_result.txt")
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write(body)
    print(body)
    print("\u7ed3\u679c\u5df2\u5199\u5165: %s" % out_path)


if __name__ == "__main__":
    main()
