# -*- coding: utf-8 -*-
"""ssd_lifespan_audit: \u56fa\u6001\u786c\u76d8\u5bff\u547d\u4e0e\u5065\u5eb7\u5ea6\u6838\u67e5\u3002

\u7528\u6cd5:
    python ssd_lifespan_audit.py --file ssd.json --out result.md
    python ssd_lifespan_audit.py --text "health=72;tbw_used=45;power_hours=18000;temp=58;drop=yes"
    python ssd_lifespan_audit.py --selftest
"""
import argparse
import json
import os

BANDS = [
    (90.0, 100.1, "100% ~ 90%", "\u65e9\u671f\uff0c\u6d88\u8017\u5c11",
     "\u6b63\u5e38\u4f7f\u7528\uff0c\u6309\u5468\u671f\u8bb0\u5f55\u6307\u6807\u5373\u53ef"),
    (70.0, 90.0, "90% ~ 70%", "\u4e2d\u671f\uff0c\u6027\u80fd\u4e0e\u5bff\u547d\u4ecd\u5145\u88d5",
     "\u786e\u8ba4\u5907\u4efd\u5b8c\u6574\uff0c\u89c4\u5212\u6362\u76d8\u65f6\u95f4"),
    (50.0, 70.0, "70% ~ 50%", "\u540e\u671f\uff0c\u98ce\u9669\u5f00\u59cb\u4e0a\u5347",
     "\u5c3d\u5feb\u5b8c\u6210\u5907\u4efd\uff0c\u4e0d\u518d\u5f80\u8fd9\u5757\u76d8\u653e\u65b0\u6570\u636e"),
    (-1.0, 50.0, "50% \u4ee5\u4e0b", "\u672b\u671f\uff0c\u98ce\u9669\u9661\u5347",
     "\u5907\u4efd\u540e\u5b89\u6392\u66f4\u6362\uff0c\u4e0d\u8981\u518d\u4f9d\u8d56\u8fd9\u5757\u76d8"),
]

TEMP_WARN = 50
TEMP_HIGH = 60
POWER_HOURS_HIGH = 20000
TBW_LATE = 80.0

DROP_ALT = [
    ("\u56fa\u4ef6\u7f3a\u9677\u6216\u66f4\u65b0\u95ee\u9898", "\u5065\u5eb7\u5ea6\u4ecd\u9ad8\uff0c\u7a81\u7136\u5f00\u59cb\u6389\u76d8"),
    ("\u4f9b\u7535\u4e0d\u7a33", "\u7279\u5b9a\u8d1f\u8f7d\u6216\u7279\u5b9a\u65f6\u523b\u624d\u6389"),
    ("\u63a7\u5236\u5668\u6216\u786c\u4ef6\u6545\u969c", "\u5065\u5eb7\u5ea6\u6b63\u5e38\uff0c\u8bfb\u5199\u9519\u8bef\u6301\u7eed\u51fa\u73b0"),
    ("\u63a5\u53e3\u3001\u7ebf\u7f06\u6216\u8f6c\u63a5\u95ee\u9898", "\u6362\u7ebf\u6362\u53e3\u540e\u8868\u73b0\u53d8\u5316"),
    ("\u6587\u4ef6\u7cfb\u7edf\u635f\u574f", "\u76d8\u80fd\u8bc6\u522b\u4f46\u5206\u533a\u5f02\u5e38"),
    ("\u6e29\u5ea6\u8fc7\u9ad8\u89e6\u53d1\u4fdd\u62a4", "\u9ad8\u6e29\u65f6\u6389\u76d8\uff0c\u964d\u6e29\u540e\u6b63\u5e38"),
]

DROP_ORDER = [
    "\u5148\u786e\u8ba4\u5907\u4efd\u5230\u4f4d",
    "\u6362\u7ebf\u6362\u53e3\u9a8c\u8bc1",
    "\u770b\u5de5\u4f5c\u6e29\u5ea6\u662f\u5426\u8fc7\u9ad8",
    "\u67e5\u56fa\u4ef6\u7248\u672c\u4e0e\u66f4\u65b0\u60c5\u51b5",
    "\u518d\u8003\u8651\u786c\u4ef6\u95ee\u9898",
]


def load_json(path):
    """Read JSON, tolerating the UTF-8 BOM written by PowerShell."""
    raw = open(path, "r", encoding="utf-8-sig").read().strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise ValueError("json parse failed: %s" % exc)


def to_float(value, default=None):
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return default
    return default


def to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("y", "yes", "true", "1")
    return False


def parse_text(text):
    data = {}
    for chunk in str(text).replace(",", ";").split(";"):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        data[key.strip().lower()] = value.strip()
    return data


def band_of(health):
    for lo, hi, label, meaning, action in BANDS:
        if lo < health <= hi:
            return label, meaning, action
    return "\u672a\u77e5\u533a\u95f4", "\u8bfb\u6570\u8d85\u51fa\u5e38\u89c1\u8303\u56f4", "\u5148\u6838\u5bf9\u8bfb\u6570\u6765\u6e90\u662f\u5426\u6b63\u786e"


def assess(d):
    health = to_float(d.get("health"), 100.0)
    tbw_used = to_float(d.get("tbw_used"), 0.0)
    hours = to_float(d.get("power_hours"), 0.0)
    temp = to_float(d.get("temp"), 0.0)
    drop = to_bool(d.get("drop", False))
    return health, tbw_used, hours, temp, drop


def build_report(d):
    health, tbw_used, hours, temp, drop = assess(d)
    label, meaning, action = band_of(health)
    out = ["# \u56fa\u6001\u786c\u76d8\u5bff\u547d\u4e0e\u5065\u5eb7\u5ea6\u6838\u67e5", ""]
    out.append("| \u6307\u6807 | \u8bfb\u6570 |")
    out.append("|---|---|")
    out.append("| \u5065\u5eb7\u5ea6\u767e\u5206\u6bd4 | %.1f%% |" % health)
    out.append("| \u603b\u5199\u5165\u91cf\u767e\u5206\u6bd4 | %.1f%% |" % tbw_used)
    out.append("| \u901a\u7535\u65f6\u95f4 | %.0f \u5c0f\u65f6 |" % hours)
    out.append("| \u5de5\u4f5c\u6e29\u5ea6 | %.0f \u6444\u6c0f\u5ea6 |" % temp)
    out.append("")
    out.append("## \u5bff\u547d\u533a\u95f4")
    out.append("")
    out.append("- \u533a\u95f4\uff1a**%s**" % label)
    out.append("- \u542b\u4e49\uff1a%s" % meaning)
    out.append("- \u5efa\u8bae\uff1a%s" % action)
    out.append("")
    out.append("## \u9700\u8981\u6ce8\u610f\u7684\u53e3\u5f84")
    out.append("")
    out.append("- \u5065\u5eb7\u5ea6\u662f\u5382\u5546\u6298\u7b97\u503c\uff0c\u4e0d\u662f\u7269\u7406\u5269\u4f59\u5bff\u547d\u7684\u7cbe\u786e\u6d4b\u91cf")
    out.append("- \u8de8\u54c1\u724c\u6bd4\u8f83\u5065\u5eb7\u5ea6\u6ca1\u6709\u610f\u4e49\uff0c\u540c\u4e00\u5757\u76d8\u770b\u8d8b\u52bf\u624d\u6709\u610f\u4e49")
    out.append("- \u5bff\u547d\u672b\u671f\u7684\u98ce\u9669\u662f\u9661\u5347\u7684\uff0c\u4e0d\u662f\u7ebf\u6027\u4e0b\u964d")
    out.append("- \u5224\u65ad\u4f9d\u636e\u5e94\u8be5\u662f\u5907\u4efd\u5230\u4e0d\u5230\u4f4d\uff0c\u4e0d\u662f\u5065\u5eb7\u5ea6\u8fd8\u5269\u591a\u5c11")
    out.append("")
    out.append("## \u73af\u5883\u56e0\u7d20")
    out.append("")
    if temp >= TEMP_HIGH:
        out.append("- \u5de5\u4f5c\u6e29\u5ea6\u8fc7\u9ad8\uff1a\u9ad8\u6e29\u4f1a\u7f29\u77ed\u5199\u5165\u5355\u5143\u7684\u6570\u636e\u4fdd\u6301\u80fd\u529b\uff0c\u4f18\u5148\u5904\u7406\u6563\u70ed")
    elif temp >= TEMP_WARN:
        out.append("- \u5de5\u4f5c\u6e29\u5ea6\u504f\u9ad8\uff1a\u5df2\u63a5\u8fd1\u9700\u8981\u6ce8\u610f\u7684\u533a\u95f4\uff0c\u5efa\u8bae\u6539\u5584\u6563\u70ed")
    else:
        out.append("- \u5de5\u4f5c\u6e29\u5ea6\u5728\u5e38\u89c1\u533a\u95f4\u5185")
    if hours >= POWER_HOURS_HIGH:
        out.append("- \u901a\u7535\u65f6\u95f4\u504f\u957f\uff1a\u5e38\u5e74\u5f00\u673a\u4f1a\u8ba9\u5404\u9879\u6027\u80fd\u540c\u6b65\u4e0b\u964d")
    else:
        out.append("- \u901a\u7535\u65f6\u95f4\u5c1a\u672a\u8fdb\u5165\u660e\u663e\u8001\u5316\u533a\u95f4")
    if tbw_used >= TBW_LATE:
        out.append("- \u5df2\u5199\u5165\u6bd4\u4f8b\u504f\u9ad8\uff1a\u63a5\u8fd1\u6807\u79f0\u5199\u5165\u91cf\uff0c\u6ce8\u610f\u5269\u4f59\u4f59\u91cf")
    out.append("- \u957f\u671f\u5f52\u6863\u7684\u6570\u636e\uff0c\u65ad\u7535\u4fdd\u5b58\u6bd4\u4e00\u76f4\u6302\u7740\u901a\u7535\u66f4\u7a33\u59a5")
    out.append("")
    out.append("## \u6362\u76d8\u5224\u65ad")
    out.append("")
    if health >= 70.0:
        out.append("- \u6682\u4e0d\u9700\u8981\u66f4\u6362\uff0c\u4fdd\u6301\u5468\u671f\u8bb0\u5f55\u5e76\u786e\u8ba4\u5907\u4efd\u5b8c\u6574")
    elif health >= 50.0:
        out.append("- \u5217\u5165\u6362\u76d8\u8ba1\u5212\uff0c\u5148\u628a\u5907\u4efd\u505a\u5b8c")
    else:
        out.append("- \u5b89\u6392\u66f4\u6362\uff0c\u4e0d\u8981\u518d\u4f9d\u8d56\u8fd9\u5757\u76d8\u5b58\u653e\u91cd\u8981\u6570\u636e")
    if drop:
        out.append("")
        out.append("## \u6389\u76d8\u4f46\u5bff\u547d\u5bcc\u4f59\u65f6\u7684\u6392\u67e5\u65b9\u5411")
        out.append("")
        out.append("\u6389\u76d8\u4e0d\u4e00\u5b9a\u7b49\u4e8e\u5bff\u547d\u5230\u4e86\u3002\u6309\u4e0b\u9762\u987a\u5e8f\u6392\u67e5\uff1a")
        out.append("")
        for i, step in enumerate(DROP_ORDER, 1):
            out.append("%d. %s" % (i, step))
        out.append("")
        out.append("| \u53ef\u80fd\u539f\u56e0 | \u5224\u65ad\u7ebf\u7d22 |")
        out.append("|---|---|")
        for cn, clue in DROP_ALT:
            out.append("| %s | %s |" % (cn, clue))
    out.append("")
    out.append("## \u8fb9\u754c")
    out.append("")
    out.append("- \u672c\u811a\u672c\u53ea\u505a\u53e3\u5f84\u6362\u7b97\u4e0e\u89c4\u5219\u5224\u5b9a\uff0c\u4e0d\u8bfb\u53d6\u786c\u76d8\u6570\u636e")
    out.append("- \u5bff\u547d\u6570\u636e\u4ee5\u8bbe\u5907\u8bf4\u660e\u4e66\u4e0e\u5382\u5546\u5de5\u5177\u7684\u5b9e\u9645\u8f93\u51fa\u4e3a\u51c6")
    out.append("- \u4e0d\u627f\u8bfa\u5269\u4f59\u4f7f\u7528\u5e74\u9650\uff0c\u4efb\u4f55\u6570\u503c\u90fd\u53ea\u662f\u4f30\u7b97")
    return "\n".join(out) + "\n"


def selftest():
    cases = []
    cases.append(("band_95", band_of(95.0)[0] == "100% ~ 90%"))
    cases.append(("band_85", band_of(85.0)[0] == "90% ~ 70%"))
    cases.append(("band_65", band_of(65.0)[0] == "70% ~ 50%"))
    cases.append(("band_40", band_of(40.0)[0] == "50% \u4ee5\u4e0b"))
    cases.append(("band_90_edge", band_of(90.0)[0] == "90% ~ 70%"))
    cases.append(("band_70_edge", band_of(70.0)[0] == "70% ~ 50%"))
    cases.append(("float_str", to_float("72.5", 0.0) == 72.5))
    cases.append(("float_bad", to_float("abc", 1.0) == 1.0))
    cases.append(("bool_yes", to_bool("YES") is True))
    cases.append(("bool_no", to_bool("no") is False))
    cases.append(("parse_text", parse_text("health=72;drop=yes")["drop"] == "yes"))
    rep = build_report({"health": 95.0, "tbw_used": 10, "power_hours": 500,
                        "temp": 40, "drop": False})
    cases.append(("rep_band", "100% ~ 90%" in rep))
    cases.append(("rep_keep", "\u6682\u4e0d\u9700\u8981\u66f4\u6362" in rep))
    cases.append(("rep_no_drop", "\u6392\u67e5\u65b9\u5411" not in rep))
    rep2 = build_report({"health": 65.0, "tbw_used": 85, "power_hours": 25000,
                         "temp": 62, "drop": True})
    cases.append(("rep_plan", "\u5217\u5165\u6362\u76d8\u8ba1\u5212" in rep2))
    cases.append(("rep_temp", "\u5de5\u4f5c\u6e29\u5ea6\u8fc7\u9ad8" in rep2))
    cases.append(("rep_hours", "\u901a\u7535\u65f6\u95f4\u504f\u957f" in rep2))
    cases.append(("rep_tbw", "\u5df2\u5199\u5165\u6bd4\u4f8b\u504f\u9ad8" in rep2))
    cases.append(("rep_drop", "\u6389\u76d8\u4e0d\u4e00\u5b9a\u7b49\u4e8e\u5bff\u547d\u5230\u4e86" in rep2))
    cases.append(("rep_fw", "\u56fa\u4ef6\u7f3a\u9677\u6216\u66f4\u65b0\u95ee\u9898" in rep2))
    rep3 = build_report({"health": 40.0})
    cases.append(("rep_replace", "\u5b89\u6392\u66f4\u6362" in rep3))
    cases.append(("rep_archive", "\u65ad\u7535\u4fdd\u5b58" in rep3))
    bom = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_probe.json")
    with open(bom, "w", encoding="utf-8-sig") as f:
        f.write('{"health": 80}')
    try:
        cases.append(("bom_ok", to_float(load_json(bom).get("health")) == 80.0))
    finally:
        if os.path.exists(bom):
            os.remove(bom)
    lines = []
    for i, (name, ok) in enumerate(cases, 1):
        lines.append("case %02d %-18s %s" % (i, name, "PASS" if ok else "FAIL"))
    bad = [n for n, ok in cases if not ok]
    lines.append("")
    lines.append("SELFTEST %s (%d/%d)" % ("OK" if not bad else "FAILED",
                                         len(cases) - len(bad), len(cases)))
    if bad:
        lines.append("failed: " + ", ".join(bad))
    text = "\n".join(lines) + "\n"
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "_selftest_result.txt"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(text)
    return 0 if not bad else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="ssd lifespan audit")
    ap.add_argument("--file", default=None)
    ap.add_argument("--text", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--format", default="md")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    data = {}
    if a.file:
        try:
            data = load_json(a.file)
        except Exception as exc:
            print(str(exc))
            return 2
    elif a.text:
        data = parse_text(a.text)
    report = build_report(data)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "ssd_lifespan_result.md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
