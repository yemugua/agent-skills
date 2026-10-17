# -*- coding: utf-8 -*-
"""\u513f\u7ae5\u53d1\u70ed\u5c31\u8bca\u5206\u7ea7\u4e0e\u5bb6\u5ead\u62a4\u7406\u63d0\u793a\u5de5\u5177\u3002

\u7528\u6cd5:
  python child_fever_triage.py --file case.json [--json]
  python child_fever_triage.py --selftest

\u672c\u5de5\u5177\u4e0d\u8f93\u51fa\u4efb\u4f55\u836f\u7269\u5242\u91cf\u4e0e\u7528\u836f\u65b9\u6848\u3002
"""
import argparse
import io
import json
import os
import sys

# \u5404\u90e8\u4f4d\u53d1\u70ed\u5224\u5b9a\u9608\u503c
SITE_THRESHOLD = {"armpit": 37.3, "oral": 37.5, "ear": 38.0, "forehead": 38.0, "rectal": 38.0}
SITE_TEXT = {"armpit": "\u814b\u6e29", "oral": "\u53e3\u6e29", "ear": "\u8033\u6e29", "forehead": "\u989d\u6e29", "rectal": "\u809b\u6e29"}

EMERGENCY_FLAGS = [
    "seizure_over_5min",   # \u60ca\u53a5\u6301\u7eed\u8d85\u8fc7 5 \u5206\u949f
    "seizure_active",      # \u60ca\u53a5\u6b63\u5728\u53d1\u4f5c
    "consciousness",       # \u610f\u8bc6\u6539\u53d8
    "neck_stiffness",      # \u9888\u9879\u5f3a\u76f4
    "rash_non_blanching",  # \u76ae\u75b9\u538b\u4e4b\u4e0d\u892a\u8272
    "breathing_difficulty",  # \u547c\u5438\u56f0\u96be
    "cyanosis",            # \u53e3\u5507\u53d1\u7d2b
    "severe_dehydration",  # \u660e\u663e\u8131\u6c34
    "immunocompromised",   # \u514d\u75ab\u7f3a\u9677\u6216\u5316\u7597\u4e2d
]
EMERGENCY_TEXT = {
    "seizure_over_5min": "\u60ca\u53a5\u6301\u7eed\u8d85\u8fc7 5 \u5206\u949f",
    "seizure_active": "\u60ca\u53a5\u6b63\u5728\u53d1\u4f5c",
    "consciousness": "\u610f\u8bc6\u6539\u53d8\uff1a\u53eb\u4e0d\u9192\u3001\u5f02\u5e38\u55dc\u7761\u3001\u773c\u795e\u53d1\u76f4",
    "neck_stiffness": "\u9888\u9879\u5f3a\u76f4\u3001\u5267\u70c8\u5934\u75db",
    "rash_non_blanching": "\u76ae\u75b9\u538b\u4e4b\u4e0d\u892a\u8272\u6216\u76ae\u80a4\u7d2b\u7ea2\u6591\u70b9",
    "breathing_difficulty": "\u547c\u5438\u56f0\u96be\u3001\u9f3b\u7ffc\u6247\u52a8\u3001\u808b\u95f4\u51f9\u9677",
    "cyanosis": "\u53e3\u5507\u53d1\u7d2b",
    "severe_dehydration": "\u660e\u663e\u8131\u6c34\uff1a\u957f\u65f6\u95f4\u65e0\u5c3f\u3001\u54ed\u65e0\u6cea\u3001\u56df\u95e8\u51f9\u9677",
    "immunocompromised": "\u514d\u75ab\u7f3a\u9677\u6216\u5316\u7597\u4e2d",
}
WARNING_FLAGS = [
    "refuse_drink",     # \u6301\u7eed\u62d2\u7edd\u996e\u6c34
    "persistent_vomit",  # \u6301\u7eed\u5455\u5410
    "unwell_look",      # \u5bb6\u957f\u89c9\u5f97\u5b69\u5b50\u5f88\u4e0d\u5bf9\u52b2
]
WARNING_TEXT = {
    "refuse_drink": "\u6301\u7eed\u62d2\u7edd\u996e\u6c34\u6216\u65e0\u6cd5\u8fdb\u6c34",
    "persistent_vomit": "\u6301\u7eed\u5455\u5410\u8179\u6cfb",
    "unwell_look": "\u5bb6\u957f\u76f4\u89c9\u89c9\u5f97\u5b69\u5b50\u5f88\u4e0d\u5bf9\u52b2",
}


def is_fever(temp, site):
    """\u662f\u5426\u8fbe\u5230\u53d1\u70ed\u5224\u5b9a\u9608\u503c\u3002"""
    if site not in SITE_THRESHOLD:
        return None
    return float(temp) >= SITE_THRESHOLD[site]


def fever_grade(temp, site):
    """\u4ee5\u814b\u6e29\u53e3\u5f84\u5206\u7ea7\uff1b\u5176\u4ed6\u90e8\u4f4d\u4ec5\u4f5c\u53c2\u8003\u6362\u7b97\u63d0\u793a\u3002"""
    t = float(temp)
    if site == "rectal":
        t = t - 0.5
    elif site in ("ear", "forehead", "oral"):
        t = t - 0.3
    if t < 37.3:
        return "\u672a\u8fbe\u53d1\u70ed\uff08\u6309\u6362\u7b97\u53e3\u5f84\uff09"
    if t <= 38.0:
        return "\u4f4e\u70ed"
    if t <= 39.0:
        return "\u4e2d\u5ea6\u53d1\u70ed"
    if t <= 41.0:
        return "\u9ad8\u70ed"
    return "\u8d85\u9ad8\u70ed"


def age_band(months):
    m = float(months or 0)
    if m < 3:
        return "0-3 \u4e2a\u6708"
    if m < 6:
        return "3-6 \u4e2a\u6708"
    if m < 24:
        return "6-24 \u4e2a\u6708"
    return "2 \u5c81\u4ee5\u4e0a"


def triage(age_months, temp, site, duration_hours, flags):
    """\u8fd4\u56de (\u7ea7\u522b, \u5224\u5b9a\u4f9d\u636e\u5217\u8868)\u3002"""
    reasons = []
    em = [f for f in flags if f in EMERGENCY_FLAGS]
    wa = [f for f in flags if f in WARNING_FLAGS]

    if em:
        for f in em:
            reasons.append("\u6025\u8bca\u6307\u5f81\uff1a" + EMERGENCY_TEXT[f])
        return "\u6025\u8bca", reasons

    m = float(age_months or 0)
    t = float(temp or 0)
    if m < 3:
        if site == "rectal" and t >= 38.0:
            reasons.append("3 \u4e2a\u6708\u4ee5\u4e0b\u5a74\u513f\u809b\u6e29 %.1f\u2103 \u8fbe 38.0\u2103\uff0c\u9700\u6025\u8bca\u8bc4\u4f30" % t)
            return "\u6025\u8bca", reasons
        if site == "armpit" and t >= 37.5:
            reasons.append("3 \u4e2a\u6708\u4ee5\u4e0b\u5a74\u513f\u814b\u6e29 %.1f\u2103 \u8fbe 37.5\u2103\uff0c\u9700\u6025\u8bca\u8bc4\u4f30" % t)
            return "\u6025\u8bca", reasons
        if t >= 37.3:
            reasons.append("3 \u4e2a\u6708\u4ee5\u4e0b\u5a74\u513f\u4f53\u6e29\u504f\u9ad8\uff0c\u9700\u5c3d\u5feb\u5c31\u8bca\u8bc4\u4f30")
            return "\u5f53\u65e5\u5c31\u8bca", reasons

    if wa:
        for f in wa:
            reasons.append("\u9700\u5c3d\u5feb\u5c31\u8bca\uff1a" + WARNING_TEXT[f])
        return "\u5f53\u65e5\u5c31\u8bca", reasons

    d = float(duration_hours or 0)
    if d >= 72:
        reasons.append("\u53d1\u70ed\u5df2\u6301\u7eed %g \u5c0f\u65f6\uff08\u8d85\u8fc7 3 \u5929\uff09\uff0c\u5e94\u5c31\u8bca" % d)
        return "\u5f53\u65e5\u5c31\u8bca", reasons

    if m < 6 and t >= 38.5:
        reasons.append("3-6 \u4e2a\u6708\u4f53\u6e29 %.1f\u2103 \u8fbe 38.5\u2103\uff0c\u5e94\u5c31\u8bca" % t)
        return "\u5f53\u65e5\u5c31\u8bca", reasons

    if t >= 40.0:
        reasons.append("\u4f53\u6e29 %.1f\u2103 \u53cd\u590d\u8fbe\u5230 40\u2103 \u4ee5\u4e0a\uff0c\u5e94\u5c31\u8bca" % t)
        return "\u5f53\u65e5\u5c31\u8bca", reasons

    if m < 24 and t >= 39.0 and d >= 24:
        reasons.append("6-24 \u4e2a\u6708\u4f53\u6e29 %.1f\u2103 \u4f34\u53d1\u70ed\u8d85\u8fc7 24 \u5c0f\u65f6\uff0c\u5e94\u5c31\u8bca" % t)
        return "\u5f53\u65e5\u5c31\u8bca", reasons

    if not is_fever(t, site):
        reasons.append("\u4f53\u6e29\u672a\u8fbe\u53d1\u70ed\u9608\u503c\uff0c\u4ee5\u89c2\u5bdf\u4e3a\u4e3b")
        return "\u5bb6\u5ead\u62a4\u7406\u89c2\u5bdf", reasons

    reasons.append("\u672a\u547d\u4e2d\u7ea2\u7ebf\uff0c\u7cbe\u795e\u72b6\u6001\u4e0e\u996e\u6c34\u60c5\u51b5\u826f\u597d\u65f6\u53ef\u5148\u5bb6\u5ead\u62a4\u7406\u5e76\u5bc6\u5207\u89c2\u5bdf")
    return "\u5bb6\u5ead\u62a4\u7406\u89c2\u5bdf", reasons


CARE = [
    "\u51cf\u5c11\u8863\u7269\uff0c\u4e0d\u6342\u6c57\uff1b\u624b\u811a\u51c9\u65f6\u4fdd\u6696\u624b\u811a\uff0c\u8eaf\u5e72\u4e0d\u6342",
    "\u5ba4\u6e29\u5408\u9002\uff0c\u4fdd\u6301\u901a\u98ce\uff0c\u53ef\u7528\u7a7a\u8c03\uff0c\u907f\u514d\u76f4\u5439",
    "\u6e29\u6c34\u64e6\u62ed\uff08\u7ea6 32-34 \u6444\u6c0f\u5ea6\uff09\u9888\u90e8\u4e24\u4fa7\u3001\u814b\u4e0b\u3001\u8098\u7a9d\u3001\u8179\u80a1\u6c9f\u3001\u8158\u7a9d\uff0c\u6bcf\u6b21 10-20 \u5206\u949f\uff0c\u51fa\u73b0\u5bd2\u6218\u7acb\u5373\u505c\u6b62",
    "\u5c11\u91cf\u591a\u6b21\u8865\u6c34\uff0c\u4fdd\u6301\u5c3f\u91cf\u6b63\u5e38",
    "\u6bcf 4 \u5c0f\u65f6\u8bb0\u5f55\u4f53\u6e29\uff08\u6ce8\u660e\u90e8\u4f4d\uff09\u3001\u996e\u6c34\u3001\u5c3f\u91cf\u3001\u7cbe\u795e\u72b6\u6001",
]
FORBID = [
    "\u7981\u6b62\u6342\u6c57\u3001\u76d6\u539a\u88ab\u5b50\u53d1\u6c57",
    "\u7981\u6b62\u9152\u7cbe\u6216\u767d\u9152\u64e6\u6d74",
    "\u7981\u6b62\u51b0\u6c34\u6d74\u3001\u51b7\u6c34\u64e6\u6d74\u3001\u51b0\u888b\u76f4\u63a5\u63a5\u89e6\u76ae\u80a4",
    "\u7981\u6b62\u81ea\u884c\u51b3\u5b9a\u9000\u70ed\u836f\u79cd\u7c7b\u3001\u5242\u91cf\u4e0e\u95f4\u9694",
]


def build_report(data):
    months = data.get("age_months", 0)
    temp = data.get("temp", 0)
    site = data.get("site", "armpit")
    duration = data.get("duration_hours", 0)
    flags = list(data.get("flags", []))
    drinking = data.get("drinking", "unknown")
    mental = data.get("mental_state", "unknown")

    lines = []
    lines.append("=" * 66)
    lines.append("\u513f\u7ae5\u53d1\u70ed\u5c31\u8bca\u5206\u7ea7\u4e0e\u62a4\u7406\u63d0\u793a")
    lines.append("=" * 66)
    lines.append("\u6708\u9f84\uff1a%g \u4e2a\u6708\uff08%s\uff09   \u4f53\u6e29\uff1a%g\u2103\uff08%s\uff09   \u53d1\u70ed\u65f6\u957f\uff1a%g \u5c0f\u65f6" % (
        float(months or 0), age_band(months), float(temp or 0),
        SITE_TEXT.get(site, "\u672a\u77e5\u90e8\u4f4d"), float(duration or 0)))
    lines.append("\u7cbe\u795e\u72b6\u6001\uff1a%s   \u996e\u6c34\u60c5\u51b5\uff1a%s" % (mental, drinking))
    lines.append("")

    fever = is_fever(temp, site)
    if fever is None:
        lines.append("[\u4fe1\u606f\u4e0d\u8db3] \u6d4b\u91cf\u90e8\u4f4d %s \u672a\u6536\u5f55\uff0c\u65e0\u6cd5\u5224\u5b9a\u53d1\u70ed\u9608\u503c" % site)
        lines.append("\u8bf7\u6539\u7528\u814b\u6e29\u3001\u53e3\u6e29\u3001\u8033\u6e29\u3001\u989d\u6e29\u6216\u809b\u6e29\u4e4b\u4e00\u5e76\u6ce8\u660e")
        lines.append("=" * 66)
        return "\n".join(lines), {"level": "\u4fe1\u606f\u4e0d\u8db3", "fever": None}

    grade = fever_grade(temp, site)
    level, reasons = triage(months, temp, site, duration, flags)

    lines.append("[\u4e00] \u5224\u5b9a")
    lines.append("  \u662f\u5426\u8fbe\u53d1\u70ed\u9608\u503c\uff1a%s   \u5206\u7ea7\uff1a%s" % ("\u662f" if fever else "\u5426", grade))
    lines.append("  \u5c31\u8bca\u5206\u7ea7\uff1a%s" % level)
    lines.append("")
    lines.append("[\u4e8c] \u5224\u5b9a\u4f9d\u636e")
    for r in reasons:
        lines.append("  - %s" % r)
    lines.append("")

    if level == "\u6025\u8bca":
        lines.append("[\u4e09] \u5904\u7f6e")
        lines.append("  \u7acb\u5373\u5c31\u533b\u6216\u62e8\u6253\u6025\u6551\u7535\u8bdd\uff0c\u4e0d\u8981\u81ea\u884c\u5728\u5bb6\u89c2\u5bdf\u3002")
        lines.append("  \u60ca\u53a5\u53d1\u4f5c\u65f6\uff1a\u4fa7\u5367\u9632\u8bef\u5438\uff0c\u79fb\u5f00\u5468\u56f4\u786c\u7269\uff0c\u4e0d\u6309\u538b\u80a2\u4f53\u3001\u4e0d\u64ac\u5634\u3001\u4e0d\u585e\u4e1c\u897f\uff0c")
        lines.append("  \u8bb0\u5f55\u53d1\u4f5c\u8d77\u6b62\u65f6\u95f4\uff1b\u6301\u7eed\u8d85\u8fc7 5 \u5206\u949f\u6216\u53cd\u590d\u53d1\u4f5c\u7acb\u5373\u53eb\u6025\u6551\u3002")
        lines.append("")
        lines.append("  \u672c\u5de5\u5177\u4e0d\u8f93\u51fa\u4efb\u4f55\u836f\u7269\u5242\u91cf\u4e0e\u7528\u836f\u65b9\u6848\u3002")
        lines.append("=" * 66)
        summary = {"level": level, "fever": fever, "grade": grade,
                   "reasons": reasons, "care": [], "forbidden": FORBID,
                   "medication_dose_provided": False}
        return "\n".join(lines), summary

    lines.append("[\u4e09] \u5bb6\u5ead\u62a4\u7406\u53ef\u505a")
    for c in CARE:
        lines.append("  + %s" % c)
    lines.append("")
    lines.append("[\u56db] \u660e\u786e\u7981\u6b62")
    for f in FORBID:
        lines.append("  - %s" % f)
    lines.append("")
    lines.append("[\u4e94] \u89c2\u5bdf\u4e0e\u590d\u8bc4")
    if drinking == "refuse":
        lines.append("  \u62d2\u7edd\u996e\u6c34\uff1a\u5c5e\u4e8e\u9700\u5c3d\u5feb\u5c31\u8bca\u7684\u4fe1\u53f7")
    if mental == "poor":
        lines.append("  \u7cbe\u795e\u72b6\u6001\u5dee\uff1a\u5c5e\u4e8e\u9700\u5c3d\u5feb\u5c31\u8bca\u7684\u4fe1\u53f7")
    lines.append("  \u51fa\u73b0\u610f\u8bc6\u6539\u53d8\u3001\u60ca\u53a5\u3001\u547c\u5438\u56f0\u96be\u3001\u76ae\u75b9\u538b\u4e0d\u892a\u8272\u3001\u660e\u663e\u8131\u6c34\uff0c\u7acb\u5373\u5c31\u533b")
    lines.append("  \u53d1\u70ed\u8d85\u8fc7 3 \u5929\u6216\u53cd\u590d\u8d85\u8fc7 40 \u6444\u6c0f\u5ea6\uff0c\u5e94\u5c31\u8bca")
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u62a4\u7406\u63d0\u793a\uff0c\u4e0d\u6784\u6210\u8bca\u7597\u610f\u89c1\uff0c\u4e0d\u63d0\u4f9b\u836f\u7269\u5242\u91cf\u3002")
    lines.append("=" * 66)

    summary = {"level": level, "fever": fever, "grade": grade, "reasons": reasons,
               "care": CARE, "forbidden": FORBID, "medication_dose_provided": False}
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("\u814b\u6e29 37.5 \u5224\u4e3a\u53d1\u70ed", is_fever(37.5, "armpit") is True))
    r.append(("\u814b\u6e29 37.0 \u4e0d\u5224\u4e3a\u53d1\u70ed", is_fever(37.0, "armpit") is False))
    r.append(("\u809b\u6e29 38.0 \u5224\u4e3a\u53d1\u70ed", is_fever(38.0, "rectal") is True))
    r.append(("\u672a\u77e5\u90e8\u4f4d\u8fd4\u56de None", is_fever(38.0, "hand") is None))
    r.append(("\u6708\u9f84 1 \u5f52\u5165 0-3 \u4e2a\u6708", age_band(1) == "0-3 \u4e2a\u6708"))
    r.append(("\u6708\u9f84 4 \u5f52\u5165 3-6 \u4e2a\u6708", age_band(4) == "3-6 \u4e2a\u6708"))
    r.append(("\u6708\u9f84 12 \u5f52\u5165 6-24 \u4e2a\u6708", age_band(12) == "6-24 \u4e2a\u6708"))
    r.append(("\u6708\u9f84 36 \u5f52\u5165 2 \u5c81\u4ee5\u4e0a", age_band(36) == "2 \u5c81\u4ee5\u4e0a"))
    r.append(("\u814b\u6e29 38.5 \u4e3a\u4e2d\u5ea6\u53d1\u70ed", fever_grade(38.5, "armpit") == "\u4e2d\u5ea6\u53d1\u70ed"))
    r.append(("\u814b\u6e29 39.5 \u4e3a\u9ad8\u70ed", fever_grade(39.5, "armpit") == "\u9ad8\u70ed"))
    r.append(("\u814b\u6e29 41.5 \u4e3a\u8d85\u9ad8\u70ed", fever_grade(41.5, "armpit") == "\u8d85\u9ad8\u70ed"))

    lv, _ = triage(1, 38.0, "rectal", 2, [])
    r.append(("1 \u6708\u9f84\u809b\u6e29 38 \u4e3a\u6025\u8bca", lv == "\u6025\u8bca"))
    lv, _ = triage(1, 37.6, "armpit", 2, [])
    r.append(("1 \u6708\u9f84\u814b\u6e29 37.6 \u4e3a\u6025\u8bca", lv == "\u6025\u8bca"))
    lv, _ = triage(24, 38.5, "armpit", 5, [])
    r.append(("2 \u5c81 38.5 \u4e3a\u5bb6\u5ead\u62a4\u7406", lv == "\u5bb6\u5ead\u62a4\u7406\u89c2\u5bdf"))
    lv, _ = triage(24, 38.5, "armpit", 80, [])
    r.append(("\u53d1\u70ed\u8d85 72 \u5c0f\u65f6\u5c31\u8bca", lv == "\u5f53\u65e5\u5c31\u8bca"))
    lv, _ = triage(4, 38.6, "armpit", 3, [])
    r.append(("4 \u6708\u9f84 38.6 \u5c31\u8bca", lv == "\u5f53\u65e5\u5c31\u8bca"))
    lv, _ = triage(24, 40.5, "armpit", 2, [])
    r.append(("40.5 \u5ea6\u5c31\u8bca", lv == "\u5f53\u65e5\u5c31\u8bca"))
    lv, rs = triage(36, 38.0, "armpit", 2, ["seizure_active"])
    r.append(("\u60ca\u53a5\u53d1\u4f5c\u76f4\u63a5\u6025\u8bca", lv == "\u6025\u8bca"))
    r.append(("\u60ca\u53a5\u7406\u7531\u5df2\u5217\u51fa", any("\u60ca\u53a5" in x for x in rs)))
    lv, _ = triage(36, 37.0, "armpit", 2, [])
    r.append(("\u672a\u53d1\u70ed\u4e3a\u89c2\u5bdf", lv == "\u5bb6\u5ead\u62a4\u7406\u89c2\u5bdf"))

    _, s = build_report({"age_months": 12, "temp": 38.8, "site": "armpit",
                         "duration_hours": 6, "flags": [], "drinking": "ok",
                         "mental_state": "ok"})
    r.append(("\u6837\u4f8b\u4e3a\u5bb6\u5ead\u62a4\u7406", s["level"] == "\u5bb6\u5ead\u62a4\u7406\u89c2\u5bdf"))
    r.append(("\u4e0d\u63d0\u4f9b\u836f\u7269\u5242\u91cf", s["medication_dose_provided"] is False))
    r.append(("\u62a4\u7406\u9879\u4e0d\u5c11\u4e8e 4 \u6761", len(s["care"]) >= 4))

    _, s2 = build_report({"age_months": 12, "temp": 38.8, "site": "hand"})
    r.append(("\u672a\u77e5\u90e8\u4f4d\u4e3a\u4fe1\u606f\u4e0d\u8db3", s2["level"] == "\u4fe1\u606f\u4e0d\u8db3"))

    _, s3 = build_report({"age_months": 2, "temp": 38.2, "site": "rectal"})
    r.append(("\u5c0f\u5a74\u513f\u6025\u8bca\u4e0d\u51fa\u62a4\u7406\u9879", s3["care"] == []))
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
    parser = argparse.ArgumentParser(description="\u513f\u7ae5\u53d1\u70ed\u5c31\u8bca\u5206\u7ea7\u4e0e\u62a4\u7406\u63d0\u793a\u5de5\u5177")
    parser.add_argument("--file", help="\u8f93\u5165 JSON \u6587\u4ef6\u8def\u5f84\uff08UTF-8\uff09")
    parser.add_argument("--json", action="store_true", help="\u4ee5 JSON \u8f93\u51fa")
    parser.add_argument("--out", help="\u7ed3\u679c\u5199\u5165\u6307\u5b9a\u6587\u4ef6")
    parser.add_argument("--selftest", action="store_true", help="\u8fd0\u884c\u81ea\u68c0")
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))

    if args.selftest:
        sys.exit(0 if selftest() else 1)

    if not args.file:
        parser.error("\u9700\u8981 --file \u6216 --selftest")

    with io.open(args.file, "r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)

    report, summary = build_report(data)
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else report
    out_path = args.out or os.path.join(here, "_last_result.txt")
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write(body)
    print(body)
    print("")
    print("\u7ed3\u679c\u5df2\u5199\u5165\uff1a%s" % out_path)


if __name__ == "__main__":
    main()
