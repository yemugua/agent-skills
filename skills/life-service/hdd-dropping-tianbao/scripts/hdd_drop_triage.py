# -*- coding: utf-8 -*-
"""hdd_drop_triage: \u673a\u68b0\u786c\u76d8\u6389\u76d8\u5f81\u5146\u4e0e\u5904\u7f6e\u7ea7\u522b\u8bc4\u4f30\u3002

\u7528\u6cd5:
    python hdd_drop_triage.py --symptoms "\u5f02\u54cd,\u8bfb\u53d6\u62a5\u9519"
    python hdd_drop_triage.py --file case.json --out result.md
    python hdd_drop_triage.py --selftest
"""
import argparse
import json
import os

SYMPTOM_CN = {
    "click": ("\u5f02\u54cd", 0),
    "clicks": ("\u5f02\u54cd", 0),
    "noise": ("\u5f02\u54cd", 0),
    "scratch": ("\u5f02\u54cd", 0),
    "seek": ("\u5f02\u54cd", 0),
    "grind": ("\u5f02\u54cd", 0),
    "bootclick": ("\u542f\u52a8\u65f6\u5f02\u54cd", 0),
    "notfound": ("\u5b8c\u5168\u4e0d\u8bc6\u522b", 1),
    "missing": ("\u5b8c\u5168\u4e0d\u8bc6\u522b", 1),
    "drop": ("\u65f6\u597d\u65f6\u574f", 1),
    "intermittent": ("\u65f6\u597d\u65f6\u574f", 1),
    "failread": ("\u8bfb\u53d6\u62a5\u9519", 1),
    "copyfail": ("\u62f7\u8d1d\u5927\u6587\u4ef6\u4e2d\u65ad", 1),
    "slow": ("\u6253\u5f00\u6587\u4ef6\u5f88\u6162", 2),
    "flaky": ("\u5076\u53d1\u8ba4\u4e0d\u5230\u76d8", 3),
}

SMART_CN = {
    "pending": ("\u5f85\u6620\u5c04\u6247\u533a\u6570\u4e0d\u4e3a\u96f6", 1),
    "realloc": ("\u91cd\u65b0\u5206\u914d\u6247\u533a\u6570\u6301\u7eed\u589e\u957f", 1),
    "uncorrect": ("\u65e0\u6cd5\u6821\u6b63\u6247\u533a\u6570\u4e0d\u4e3a\u96f6", 1),
    "rawread": ("\u5e95\u5c42\u6570\u636e\u9519\u8bef\u7387\u4e0a\u5347", 1),
    "timeout": ("\u901a\u7535\u8d85\u65f6\u8ba1\u6570\u589e\u957f", 1),
    "seekerr": ("\u5bfb\u9053\u9519\u8bef\u7387\u5f02\u5e38", 2),
    "calib": ("\u51fa\u5382\u6821\u51c6\u8ba1\u6570\u5f02\u5e38", 2),
    "temp": ("\u6e29\u5ea6\u544a\u8b66", 2),
    "poweron": ("\u901a\u7535\u5c0f\u65f6\u6570\u5f88\u9ad8", 2),
}

LEVEL_CN = {
    0: "L0 \u7acb\u5373\u505c\u7528",
    1: "L1 \u9ad8\u4f18\u5148\u5904\u7406",
    2: "L2 \u5148\u5907\u4efd",
    3: "L3 \u7ee7\u7eed\u89c2\u5bdf",
}

LEVEL_ACTION = {
    0: "\u7acb\u523b\u65ad\u7535\u505c\u7528\uff0c\u4e0d\u8981\u518d\u901a\u7535\u8bd5\uff1b\u6570\u636e\u91cd\u8981\u4e14\u65e0\u5907\u4efd\u65f6\u8f6c\u4e13\u4e1a\u6570\u636e\u6062\u590d\u673a\u6784",
    1: "\u505c\u6b62\u5411\u8be5\u76d8\u5199\u5165\u6570\u636e\uff0c\u8bc4\u4f30\u505a\u6574\u76d8\u955c\u50cf\u540e\u4ece\u955c\u50cf\u4e0a\u6062\u590d",
    2: "\u5c3d\u5feb\u505a\u4e00\u6b21\u5b8c\u6574\u5907\u4efd\uff0c\u5907\u4efd\u540e\u518d\u8bc4\u4f30\u76d8\u7684\u72b6\u6001",
    3: "\u5148\u6362\u7ebf\u6362\u53e3\u9a8c\u8bc1\u6392\u9664\u63a5\u53e3\u4e0e\u4f9b\u7535\u56e0\u7d20\uff0c\u89c2\u5bdf\u662f\u5426\u590d\u73b0",
}

NEVER = [
    "\u4e3a\u4e86\u8bd5\u8bd5\u770b\u800c\u53cd\u590d\u901a\u7535",
    "\u628a\u6062\u590d\u51fa\u6765\u7684\u6570\u636e\u5199\u56de\u6545\u969c\u76d8",
    "\u683c\u5f0f\u5316\u6545\u969c\u76d8\u770b\u8fd8\u8ba4\u4e0d\u8ba4",
    "\u7ee7\u7eed\u5f80\u6545\u969c\u76d8\u62f7\u65b0\u6570\u636e",
]

RESCUE = [
    "\u505c\u6b62\u4f7f\u7528\uff0c\u4e0d\u518d\u5f80\u8fd9\u5757\u76d8\u5199\u4efb\u4f55\u6570\u636e",
    "\u65ad\u7535\u9759\u7f6e\uff0c\u907f\u514d\u9707\u52a8\u4e0e\u9ad8\u6e29",
    "\u628a\u80fd\u8bfb\u5230\u7684\u90e8\u5206\u505a\u6574\u76d8\u6216\u5206\u533a\u955c\u50cf\u5230\u5065\u5eb7\u4ecb\u8d28",
    "\u5728\u955c\u50cf\u4ef6\u4e0a\u8dd1\u6062\u590d\u5de5\u5177\uff0c\u4e0d\u52a8\u539f\u76d8",
    "\u6838\u5bf9\u955c\u50cf\u4ef6\u91cc\u7684\u6587\u4ef6\u662f\u5426\u5b8c\u6574\u53ef\u7528",
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


def split_tokens(text):
    if isinstance(text, str):
        raw = text.replace(",", ",").replace(",", ",")
        parts = [p for p in raw.replace("\u3001", ",").replace(" ", ",").split(",")]
        return [p for p in parts if p]
    return [str(x) for x in (text or [])]


def match_symptom(token):
    t = str(token).strip().lower()
    if t in SYMPTOM_CN:
        return SYMPTOM_CN[t]
    for key, val in SYMPTOM_CN.items():
        if key in t:
            return val
    for key, val in SYMPTOM_CN.items():
        if val[0] in str(token):
            return val
    return None


def match_smart(token):
    t = str(token).strip().lower()
    if t in SMART_CN:
        return SMART_CN[t]
    for key, val in SMART_CN.items():
        if key in t:
            return val
    for key, val in SMART_CN.items():
        if val[0] in str(token):
            return val
    return None


def assess(symptom_tokens, smart_tokens):
    hits = []
    for tk in split_tokens(symptom_tokens):
        m = match_symptom(tk)
        if m:
            hits.append(("symptom", m))
    for tk in split_tokens(smart_tokens):
        m = match_smart(tk)
        if m:
            hits.append(("smart", m))
    if not hits:
        level = 3
    else:
        level = min(h[1][1] for h in hits)
    return level, hits


def build_report(symptom_tokens, smart_tokens):
    level, hits = assess(symptom_tokens, smart_tokens)
    out = ["# \u673a\u68b0\u786c\u76d8\u6389\u76d8\u5904\u7f6e\u8bc4\u4f30", ""]
    out.append("## \u5904\u7f6e\u7ea7\u522b")
    out.append("")
    out.append("**%s**" % LEVEL_CN[level])
    out.append("")
    out.append("- \u5e94\u505a\uff1a%s" % LEVEL_ACTION[level])
    out.append("")
    if level == 0:
        out.append("\u5f02\u54cd\u662f\u6700\u5f3a\u4fe1\u53f7\u3002**\u65e0\u8bba\u5176\u4ed6\u6307\u6807\u591a\u597d\uff0c\u4e00\u5f8b\u6309\u6700\u574f\u60c5\u51b5\u5904\u7406\u3002**")
        out.append("")
        out.append("- SMART \u5168\u7eff\u4e0d\u7b49\u4e8e\u76d8\u5065\u5eb7\uff0c\u673a\u68b0\u6545\u969c\u5e38\u6765\u4e0d\u53ca\u53cd\u6620\u5230\u8fd9\u4e9b\u6570\u503c\u4e0a")
        out.append("- \u53cd\u590d\u901a\u7535\u4f1a\u6301\u7eed\u635f\u4f24\u76d8\u9762\uff0c\u53ef\u6551\u8303\u56f4\u8d8a\u6765\u8d8a\u5c0f")
        out.append("")
    out.append("## \u547d\u4e2d\u7684\u5f81\u5146\u4e0e\u9884\u8b66\u9879")
    out.append("")
    if hits:
        for src, (cn, lv) in hits:
            out.append("- %s\uff1a%s\uff08\u5bf9\u5e94\u7ea7\u522b %s\uff09" % (
                "\u5f81\u5146" if src == "symptom" else "\u9884\u8b66\u9879", cn, LEVEL_CN[lv]))
    else:
        out.append("- \u672a\u8bc6\u522b\u5230\u5df2\u77e5\u7684\u5f81\u5146\u6216\u9884\u8b66\u9879\uff0c\u5efa\u8bae\u8865\u5145\u66f4\u5177\u4f53\u7684\u73b0\u8c61\u63cf\u8ff0")
    out.append("")
    out.append("## \u62a2\u6551\u6d41\u7a0b\uff08\u987a\u5e8f\u4e0d\u80fd\u4e71\uff09")
    out.append("")
    for i, step in enumerate(RESCUE, 1):
        out.append("%d. %s" % (i, step))
    out.append("")
    out.append("## \u7edd\u5bf9\u4e0d\u8981\u505a")
    out.append("")
    for item in NEVER:
        out.append("- " + item)
    out.append("")
    out.append("## \u653e\u5f03\u6570\u636e\u7684\u5224\u5b9a\u7ebf")
    out.append("")
    out.append("\u51fa\u73b0\u4e0b\u5217\u4efb\u4e00\u60c5\u51b5\uff0c\u505c\u6b62\u81ea\u884c\u5c1d\u8bd5\uff0c\u8f6c\u4e13\u4e1a\u673a\u6784\u6216\u63a5\u53d7\u635f\u5931\uff1a")
    out.append("- \u6709\u5f02\u54cd\u4e14\u6570\u636e\u65e0\u4efb\u4f55\u6709\u6548\u5907\u4efd")
    out.append("- \u5df2\u53cd\u590d\u901a\u7535\u591a\u6b21\u4ecd\u8bfb\u4e0d\u51fa")
    out.append("- \u9700\u8981\u5f00\u76d8\u624d\u80fd\u8bfb")
    out.append("- \u76d8\u7247\u6709\u7269\u7406\u53d8\u5f62\u6216\u6db2\u4f53\u75d5\u8ff9")
    out.append("- \u6570\u636e\u91cf\u5927\u4e14\u5206\u6563\u591a\u5757\u76d8")
    out.append("")
    out.append("\u6838\u5fc3\u539f\u5219\uff1a\u5907\u4efd\u4f18\u5148\u4e8e\u4fee\u590d\u3002\u62a2\u6551\u4e4b\u524d\u5148\u56de\u7b54\u8fd9\u5757\u76d8\u7684\u6570\u636e\u6709\u6ca1\u6709\u7b2c\u4e8c\u4efd\u3002")
    out.append("")
    out.append("## \u8fb9\u754c")
    out.append("")
    out.append("- \u672c\u811a\u672c\u53ea\u505a\u5f81\u5146\u4e0e\u9884\u8b66\u9879\u7684\u89c4\u5219\u5224\u5b9a\uff0c\u4e0d\u63a5\u89e6\u786c\u76d8\u3001\u4e0d\u8bfb\u53d6\u6570\u636e")
    out.append("- \u6d89\u53ca\u5f00\u76d8\u6216\u62c6\u78c1\u5934\u7684\u5904\u7406\u4e00\u5f8b\u8f6c\u4ea4\u4e13\u4e1a\u6570\u636e\u6062\u590d\u673a\u6784")
    out.append("- \u65e0\u6cd5\u627f\u8bfa\u6570\u636e\u4e00\u5b9a\u80fd\u6062\u590d\uff0c\u53ef\u6062\u590d\u6027\u53d6\u51b3\u4e8e\u635f\u4f24\u7c7b\u578b\u4e0e\u7a0b\u5ea6")
    return "\n".join(out) + "\n"


def selftest():
    cases = []
    cases.append(("click_l0", assess(["\u5f02\u54cd"], [])[0] == 0))
    cases.append(("click_en", assess(["click"], [])[0] == 0))
    cases.append(("bootclick", assess(["bootclick"], [])[0] == 0))
    cases.append(("scratch_l0", assess(["scratch noise"], [])[0] == 0))
    cases.append(("notfound_l1", assess(["notfound"], [])[0] == 1))
    cases.append(("drop_l1", assess(["drop"], [])[0] == 1))
    cases.append(("slow_l2", assess(["slow"], [])[0] == 2))
    cases.append(("flaky_l3", assess(["flaky"], [])[0] == 3))
    cases.append(("click_beats_l1", assess(["notfound", "click"], [])[0] == 0))
    cases.append(("smart_l1", assess([], ["pending"])[0] == 1))
    cases.append(("smart_temp_l2", assess([], ["temp"])[0] == 2))
    cases.append(("smart_mixed", assess([], ["temp", "uncorrect"])[0] == 1))
    cases.append(("empty_l3", assess([], [])[0] == 3))
    cases.append(("split_cn", len(split_tokens("\u5f02\u54cd\u3001\u8bfb\u53d6\u62a5\u9519")) == 2))
    cases.append(("split_none", split_tokens("") == []))
    rep = build_report(["\u5f02\u54cd", "\u8bfb\u53d6\u62a5\u9519"], ["pending"])
    cases.append(("rep_level0", "L0 \u7acb\u5373\u505c\u7528" in rep))
    cases.append(("rep_smart_green", "SMART \u5168\u7eff\u4e0d\u7b49\u4e8e\u76d8\u5065\u5eb7" in rep))
    cases.append(("rep_never", "\u683c\u5f0f\u5316\u6545\u969c\u76d8" in rep))
    cases.append(("rep_rescue", "\u955c\u50cf" in rep))
    cases.append(("rep_abandon", "\u653e\u5f03\u6570\u636e\u7684\u5224\u5b9a\u7ebf" in rep))
    rep2 = build_report([], [])
    cases.append(("rep_empty_hint", "\u672a\u8bc6\u522b\u5230\u5df2\u77e5" in rep2))
    bom = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_probe.json")
    with open(bom, "w", encoding="utf-8-sig") as f:
        f.write('{"symptoms": ["click"]}')
    try:
        data = load_json(bom)
        cases.append(("bom_ok", data.get("symptoms") == ["click"]))
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
    ap = argparse.ArgumentParser(description="hdd dropping triage")
    ap.add_argument("--symptoms", default=None)
    ap.add_argument("--smart", default=None)
    ap.add_argument("--file", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--format", default="md")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    symptoms, smart = a.symptoms, a.smart
    if a.file:
        try:
            data = load_json(a.file)
        except Exception as exc:
            print(str(exc))
            return 2
        symptoms = data.get("symptoms", symptoms)
        smart = data.get("smart", smart)
    report = build_report(symptoms or [], smart or [])
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "hdd_triage_result.md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
