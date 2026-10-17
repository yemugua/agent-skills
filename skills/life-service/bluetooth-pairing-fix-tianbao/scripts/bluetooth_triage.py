# -*- coding: utf-8 -*-
"""bluetooth_triage: \u84dd\u7259\u8033\u673a\u8fde\u4e0d\u4e0a\u4e0e\u65ad\u8fde\u7684\u6392\u67e5\u987a\u5e8f\u51b3\u7b56\u3002

\u7528\u6cd5:
    python bluetooth_triage.py --symptoms "\u8fde\u4e0d\u4e0a,\u603b\u65ad\u8fde"
    python bluetooth_triage.py --file bt.json --out result.md
    python bluetooth_triage.py --selftest
"""
import argparse
import json
import os

# (\u540d\u79f0, \u89e6\u53d1\u5173\u952e\u8bcd, \u4f18\u5148\u7ea7\u6570\u5b57\u8d8a\u5c0f\u8d8a\u5148\u67e5, \u5178\u578b\u8868\u73b0, \u5904\u7406\u52a8\u4f5c)
CAUSES = [
    ("\u8033\u673a\u7535\u91cf\u4e0d\u8db3", ("\u6ca1\u7535", "\u7535\u91cf", "\u4e00\u53ea\u54cd", "\u7eed\u822a", "\u5355\u4fa7", "\u6ca1\u58f0\u97f3"),
     1, "\u4e00\u53ea\u54cd\u3001\u7eed\u822a\u5f88\u77ed\u3001\u7a81\u7136\u65ad\u8fde",
     "\u4e24\u53ea\u8033\u673a\u4e0e\u5145\u7535\u4ed3\u90fd\u5145\u6ee1\u7535\u540e\u518d\u6392\u67e5"),
    ("\u591a\u8bbe\u5907\u8fde\u63a5\u62a2\u5360", ("\u591a\u8bbe\u5907", "\u624b\u673a\u548c\u7535\u8111", "\u5207\u6362", "\u62a2", "\u4e24\u53f0", "multidevice"),
     2, "\u624b\u673a\u8fde\u4e0a\u53c8\u5207\u5230\u7535\u8111\uff0c\u53cd\u590d\u65ad\u8fde",
     "\u65ad\u5f00\u5176\u4ed6\u8bbe\u5907\u7684\u8fde\u63a5\uff0c\u53ea\u4fdd\u7559\u4e00\u53f0\u518d\u6d4b\u8bd5"),
    ("2.4G \u4e0e\u84dd\u7259\u62a2\u5360", ("2.4g", "\u63a5\u6536\u5668", "usb\u63a5\u6536", "\u63d2\u4e0a", "dongle"),
     3, "\u63d2\u4e0a\u63a5\u6536\u5668\u540e\u84dd\u7259\u5c31\u8fde\u4e0d\u4e0a\u6216\u9891\u7e41\u65ad",
     "\u5148\u65ad\u5f00\u84dd\u7259\u518d\u63d2\u63a5\u6536\u5668\uff0c\u4e00\u4e2a\u63a5\u6536\u5668\u53ea\u80fd\u4fdd\u6301\u4e00\u79cd\u8fde\u63a5"),
    ("\u914d\u5bf9\u8bb0\u5f55\u9519\u4e71", ("\u914d\u5bf9", "\u641c\u4e0d\u5230", "\u8fde\u4e0d\u4e0a\u8bbe\u5907", "\u8bb0\u5f55", "\u91cd\u8fde"),
     4, "\u641c\u4e0d\u5230\u8bbe\u5907\u3001\u914d\u5bf9\u53cd\u590d\u5931\u8d25",
     "\u5728\u8bbe\u5907\u7aef\u5220\u9664\u65e7\u914d\u5bf9\u8bb0\u5f55\u540e\u91cd\u65b0\u914d\u5bf9"),
    ("\u9a71\u52a8\u4e0e\u534f\u8bae\u4e0d\u5339\u914d", ("\u9a71\u52a8", "\u63a5\u53e3", "\u6362\u53f0", "\u6362\u7535\u8111", "\u534f\u8bae"),
     5, "\u6362\u4e00\u53f0\u8bbe\u5907\u6216\u6362\u4e00\u4e2a\u63a5\u53e3\u5c31\u6b63\u5e38",
     "\u6362\u63a5\u53e3\u6216\u6362\u8bbe\u5907\u9a8c\u8bc1\uff0c\u5b9a\u4f4d\u662f\u54ea\u4e00\u4fa7\u7684\u95ee\u9898"),
    ("\u84dd\u7259\u7248\u672c\u517c\u5bb9\u6027", ("\u7248\u672c", "\u8001\u8bbe\u5907", "\u65e7\u624b\u673a", "\u517c\u5bb9", "olddevice"),
     6, "\u8001\u8bbe\u5907\u53ea\u80fd\u4f7f\u7528\u4f4e\u7248\u672c\u529f\u80fd",
     "\u786e\u8ba4\u53cc\u65b9\u8bbe\u5907\u652f\u6301\u7684\u7248\u672c\u8303\u56f4"),
    ("USB 3.0 \u5e72\u6270", ("usb3", "\u79fb\u52a8\u786c\u76d8", "\u5e72\u6270", "hub", "\u96c6\u7ebf\u5668"),
     7, "\u9760\u8fd1\u79fb\u52a8\u786c\u76d8\u6216\u96c6\u7ebf\u5668\u5c31\u65ad",
     "\u6362\u63a5\u53e3\u3001\u52a0\u5ef6\u957f\u7ebf\u6216\u62c9\u5f00\u8ddd\u79bb"),
    ("\u7701\u7535\u76f8\u5173\u8bbe\u7f6e", ("\u7701\u7535", "\u4f11\u7720", "\u95f2\u7f6e", "\u8282\u80fd"),
     8, "\u95f2\u7f6e\u4e00\u6bb5\u65f6\u95f4\u540e\u8fde\u4e0d\u4e0a",
     "\u5173\u95ed\u76f8\u5173\u7701\u7535\u9009\u9879\u540e\u518d\u6d4b\u8bd5"),
    ("\u97f3\u9891\u7f16\u7801\u8bbe\u7f6e", ("\u5ef6\u8fdf", "\u97f3\u8d28", "\u7f16\u7801", "\u5361", "\u4e0d\u540c\u6b65"),
     9, "\u5ef6\u8fdf\u660e\u663e\u6216\u97f3\u8d28\u4e0d\u5982\u9884\u671f",
     "\u8c03\u6574\u7f16\u7801\u8bbe\u7f6e\uff1b\u4ecd\u7136\u660e\u663e\u5219\u8003\u8651\u6362 2.4G \u65b9\u6848"),
]

DECIDE = [
    ("\u53ea\u5728\u4e00\u53f0\u8bbe\u5907\u4e0a\u590d\u73b0", "\u8be5\u8bbe\u5907\u7684\u95ee\u9898\uff0c\u5148\u6362\u8bbe\u5907\u9a8c\u8bc1"),
    ("\u6362\u8bbe\u5907\u6b63\u5e38\u3001\u539f\u8bbe\u5907\u4e0d\u6b63\u5e38", "\u539f\u8bbe\u5907\u7684\u9a71\u52a8\u3001\u63a5\u53e3\u6216\u7cfb\u7edf\u95ee\u9898"),
    ("\u6240\u6709\u8bbe\u5907\u90fd\u590d\u73b0\u3001\u8033\u673a\u7528\u8fc7\u4e0d\u4e45", "\u8033\u673a\u672c\u4f53\u53ef\u80fd\u6709\u95ee\u9898\uff0c\u8d70\u552e\u540e"),
    ("\u6240\u6709\u8bbe\u5907\u90fd\u590d\u73b0\u3001\u5df2\u7528\u8f83\u4e45\u4e14\u591a\u5904\u8001\u5316", "\u8be5\u6362\u8033\u673a\u4e86"),
    ("\u8fdb\u6db2\u3001\u63a5\u53e3\u677e\u52a8\u3001\u7535\u6c60\u5f02\u5e38\u53d1\u70ed", "\u7acb\u5373\u505c\u7528\uff0c\u76f4\u63a5\u66f4\u6362"),
    ("\u5ef6\u8fdf\u59cb\u7ec8\u65e0\u6cd5\u63a5\u53d7", "\u6362 2.4G \u65b9\u6848\u6216\u6362\u8033\u673a"),
]

RESET_STEPS = [
    "\u5173\u6389\u8bbe\u5907\u7aef\u84dd\u7259\uff0c\u91cd\u65b0\u6253\u5f00",
    "\u5728\u8bbe\u5907\u7aef\u5220\u9664\u8be5\u8033\u673a\u7684\u914d\u5bf9\u8bb0\u5f55",
    "\u628a\u8033\u673a\u653e\u56de\u5145\u7535\u4ed3\uff0c\u957f\u6309\u591a\u529f\u80fd\u952e\u8fdb\u5165\u914d\u5bf9\u6a21\u5f0f",
    "\u5728\u8bbe\u5907\u7aef\u91cd\u65b0\u641c\u7d22\u5e76\u914d\u5bf9",
    "\u53ea\u8fde\u4e00\u53f0\u8bbe\u5907\uff0c\u89c2\u5bdf\u662f\u5426\u7a33\u5b9a",
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


def tokens(text):
    if isinstance(text, str):
        return [t for t in text.replace(",", " ").split() if t]
    return [str(x) for x in (text or [])]


def match(symptoms):
    """Return matching causes sorted by priority (smallest number first)."""
    tks = [t.lower() for t in tokens(symptoms)]
    joined = " ".join(tks)
    hits = []
    for name, keys, prio, symptom, action in CAUSES:
        for k in keys:
            if k in joined:
                hits.append((prio, name, symptom, action))
                break
    hits.sort(key=lambda x: x[0])
    return hits


def build_report(symptoms, context=None):
    hits = match(symptoms)
    out = ["# \u84dd\u7259\u8033\u673a\u6392\u67e5\u987a\u5e8f", ""]
    out.append("## \u547d\u4e2d\u7684\u53ef\u80fd\u539f\u56e0\uff08\u6309\u6982\u7387\u6392\u5e8f\uff09")
    out.append("")
    if hits:
        out.append("| \u987a\u5e8f | \u53ef\u80fd\u539f\u56e0 | \u5178\u578b\u8868\u73b0 | \u5904\u7406\u52a8\u4f5c |")
        out.append("|---|---|---|---|")
        for i, (_prio, name, symptom, action) in enumerate(hits, 1):
            out.append("| %d | %s | %s | %s |" % (i, name, symptom, action))
    else:
        out.append("- \u672a\u8bc6\u522b\u5230\u5df2\u77e5\u73b0\u8c61\uff0c\u8bf7\u8865\u5145\u66f4\u5177\u4f53\u7684\u63cf\u8ff0")
        out.append("- \u65e0\u8bba\u662f\u5426\u547d\u4e2d\uff0c\u90fd\u5148\u505a\u4e0b\u9762\u4e09\u6b65\uff1a")
        out.append("")
        out.append("1. \u4e24\u53ea\u8033\u673a\u4e0e\u5145\u7535\u4ed3\u90fd\u5145\u6ee1\u7535")
        out.append("2. \u53ea\u4fdd\u7559\u4e00\u53f0\u8bbe\u5907\u8fde\u63a5")
        out.append("3. \u5728\u8bbe\u5907\u7aef\u5220\u9664\u65e7\u914d\u5bf9\u8bb0\u5f55\u540e\u91cd\u65b0\u914d\u5bf9")
    out.append("")
    if context:
        ctx = str(context).lower()
        out.append("## \u573a\u666f\u63d0\u793a")
        out.append("")
        if "usb3" in ctx or "\u5e72\u6270" in ctx:
            out.append("- USB 3.0 \u4e0e 2.4G \u540c\u9891\u6bb5\uff0c\u6362\u63a5\u53e3\u6216\u52a0\u5ef6\u957f\u7ebf")
        if "gaming" in ctx or "\u6e38\u620f" in ctx or "\u4f4e\u5ef6\u8fdf" in ctx:
            out.append("- \u6e38\u620f\u4e0e\u4f4e\u5ef6\u8fdf\u573a\u666f\u4f18\u5148\u8003\u8651 2.4G \u65b9\u6848")
        if "multidevice" in ctx or "\u591a\u8bbe\u5907" in ctx:
            out.append("- \u591a\u8bbe\u5907\u573a\u666f\u8981\u9010\u4e2a\u65ad\u5f00\uff0c\u53ea\u7559\u4e00\u53f0\u6d4b\u8bd5")
        if "olddevice" in ctx or "\u8001\u8bbe\u5907" in ctx:
            out.append("- \u8001\u8bbe\u5907\u5148\u786e\u8ba4\u84dd\u7259\u7248\u672c\u517c\u5bb9\u6027")
        out.append("")
    out.append("## \u914d\u5bf9\u91cd\u7f6e\u6b65\u9aa4\uff08\u5148\u8f7b\u540e\u91cd\uff09")
    out.append("")
    for i, step in enumerate(RESET_STEPS, 1):
        out.append("%d. %s" % (i, step))
    out.append("")
    out.append("- \u901a\u7528\u539f\u5219\uff1a\u5173\u84dd\u7259\u3001\u5220\u8bb0\u5f55\u3001\u91cd\u542f\u8bbe\u5907\u3001\u6062\u590d\u51fa\u5382\u8bbe\u7f6e\uff0c\u4e0d\u8981\u8df3\u6b65")
    out.append("- \u6062\u590d\u51fa\u5382\u8bbe\u7f6e\u7684\u5165\u53e3\u56e0\u578b\u53f7\u800c\u5f02\uff0c\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e66\u4e3a\u51c6")
    out.append("- \u91cd\u7f6e\u540e\u53ea\u8fde\u4e00\u53f0\u8bbe\u5907\u6d4b\u8bd5")
    out.append("")
    out.append("## 2.4G \u4e0e\u84dd\u7259\u7684\u9009\u62e9")
    out.append("")
    out.append("- \u56fa\u5b9a\u7535\u8111\u524d\u3001\u6e38\u620f\u3001\u8981\u6c42\u4f4e\u5ef6\u8fdf\uff1a\u4f18\u5148 2.4G \u63a5\u6536\u5668")
    out.append("- \u901a\u52e4\u3001\u624b\u673a\u4f7f\u7528\uff1a\u84dd\u7259\u66f4\u65b9\u4fbf")
    out.append("- \u540c\u4e00\u4e2a\u63a5\u6536\u5668\u540c\u4e00\u65f6\u95f4\u53ea\u80fd\u4fdd\u6301\u4e00\u79cd\u8fde\u63a5\uff0c\u5148\u65ad\u5f00\u84dd\u7259\u518d\u63d2\u63a5\u6536\u5668")
    out.append("")
    out.append("## \u80fd\u4fee\u8fd8\u662f\u8be5\u6362")
    out.append("")
    out.append("| \u60c5\u51b5 | \u7ed3\u8bba |")
    out.append("|---|---|")
    for case, verdict in DECIDE:
        out.append("| %s | %s |" % (case, verdict))
    out.append("")
    out.append("- \u5148\u7528\u4e00\u53f0\u6b63\u5e38\u7684\u8bbe\u5907\u4ea4\u53c9\u9a8c\u8bc1\uff0c\u628a\u8d23\u4efb\u5206\u6e05\u518d\u51b3\u5b9a\u662f\u5426\u66f4\u6362")
    out.append("")
    out.append("## \u8fb9\u754c")
    out.append("")
    out.append("- \u672c\u811a\u672c\u53ea\u505a\u89c4\u5219\u5339\u914d\uff0c\u4e0d\u4ee3\u7528\u6237\u64cd\u4f5c\u8bbe\u5907")
    out.append("- \u4e0d\u627f\u8bfa\u91cd\u7f6e\u4e00\u6b21\u4e00\u5b9a\u80fd\u89e3\u51b3")
    out.append("- \u6d89\u53ca\u5237\u975e\u5b98\u65b9\u56fa\u4ef6\u6216\u4fee\u6539\u7cfb\u7edf\u6838\u5fc3\u8bbe\u7f6e\u7684\u4e0d\u63d0\u4f9b\u6307\u5bfc")
    return "\n".join(out) + "\n"


def selftest():
    cases = []
    cases.append(("battery", match(["\u4e00\u53ea\u54cd"])[0][1] == "\u8033\u673a\u7535\u91cf\u4e0d\u8db3"))
    cases.append(("multi", match(["\u591a\u8bbe\u5907\u62a2\u5360"])[0][1] == "\u591a\u8bbe\u5907\u8fde\u63a5\u62a2\u5360"))
    cases.append(("dongle", match(["\u63d2\u4e0a\u63a5\u6536\u5668"])[0][1] == "2.4G \u4e0e\u84dd\u7259\u62a2\u5360"))
    cases.append(("pair", match(["\u641c\u4e0d\u5230\u8bbe\u5907"])[0][1] == "\u914d\u5bf9\u8bb0\u5f55\u9519\u4e71"))
    cases.append(("driver", match(["\u6362\u53f0\u7535\u8111\u5c31\u597d"])[0][1] == "\u9a71\u52a8\u4e0e\u534f\u8bae\u4e0d\u5339\u914d"))
    cases.append(("usb3", match(["\u79fb\u52a8\u786c\u76d8\u5e72\u6270"])[0][1] == "USB 3.0 \u5e72\u6270"))
    cases.append(("latency", match(["\u5ef6\u8fdf\u592a\u5927"])[0][1] == "\u97f3\u9891\u7f16\u7801\u8bbe\u7f6e"))
    cases.append(("order", [h[0] for h in match(["\u5ef6\u8fdf\u592a\u5927,\u4e00\u53ea\u54cd"])] == [1, 9]))
    cases.append(("multi_hit", len(match(["\u4e00\u53ea\u54cd,\u5ef6\u8fdf\u592a\u5927"])) == 2))
    cases.append(("no_hit", match(["\u5b8c\u5168\u6ca1\u542c\u8fc7\u7684\u95ee\u9898"]) == []))
    cases.append(("tokens_none", tokens("") == []))
    rep = build_report(["\u8fde\u4e0d\u4e0a"], None)
    cases.append(("rep_reset", "\u914d\u5bf9\u91cd\u7f6e\u6b65\u9aa4" in rep))
    cases.append(("rep_decide", "\u80fd\u4fee\u8fd8\u662f\u8be5\u6362" in rep))
    cases.append(("rep_exclusive", "\u53ea\u80fd\u4fdd\u6301\u4e00\u79cd\u8fde\u63a5" in rep))
    cases.append(("rep_reset_order", rep.index("\u5145\u6ee1\u7535") < rep.index("\u914d\u5bf9\u8bb0\u5f55")))
    rep2 = build_report([], None)
    cases.append(("rep_fallback", "\u672a\u8bc6\u522b\u5230\u5df2\u77e5\u73b0\u8c61" in rep2))
    rep3 = build_report(["\u4e00\u53ea\u54cd"], "gaming usb3")
    cases.append(("rep_ctx_game", "\u4f18\u5148\u8003\u8651 2.4G \u65b9\u6848" in rep3))
    cases.append(("rep_ctx_usb", "\u540c\u9891\u6bb5" in rep3))
    bom = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_probe.json")
    with open(bom, "w", encoding="utf-8-sig") as f:
        f.write('{"symptoms": ["\u4e00\u53ea\u54cd"]}')
    try:
        cases.append(("bom_ok", load_json(bom).get("symptoms") == ["\u4e00\u53ea\u54cd"]))
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
    ap = argparse.ArgumentParser(description="bluetooth triage")
    ap.add_argument("--symptoms", default=None)
    ap.add_argument("--context", default=None)
    ap.add_argument("--file", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--format", default="md")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    symptoms, context = a.symptoms, a.context
    if a.file:
        try:
            data = load_json(a.file)
        except Exception as exc:
            print(str(exc))
            return 2
        symptoms = data.get("symptoms", symptoms)
        context = data.get("context", context)
    report = build_report(symptoms or [], context)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "bluetooth_result.md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
