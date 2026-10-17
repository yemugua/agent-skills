# -*- coding: utf-8 -*-
"""train_change_check: \u9ad8\u94c1\u7968\u6539\u7b7e\u4e0e\u9000\u7968\u7684\u72b6\u6001\u5224\u65ad\u4e0e\u5904\u7f6e\u65b9\u5411\u3002

\u53ea\u505a\u72b6\u6001\u5224\u65ad\u4e0e\u7ed3\u6784\u8bf4\u660e\uff0c\u4e0d\u7ed9\u51fa\u4efb\u4f55\u8d39\u7387\u4e0e\u65f6\u95f4\u7a97\u6570\u5b57\u3002
"""
import argparse
import json
import os

STATUS_CN = {
    "before": "\u5f00\u8f66\u524d",
    "after": "\u5f00\u8f66\u540e\u672a\u5230\u7ad9",
    "passed": "\u5df2\u8fc7\u7ad9",
    "cancelled": "\u5217\u8f66\u505c\u8fd0",
    "void": "\u7968\u636e\u5df2\u4f5c\u5e9f",
}

STATUS_OPTION = {
    "before": "\u6539\u7b7e\u4e0e\u9000\u7968\u90fd\u8fd8\u6709\u9009\u62e9\uff0c\u9009\u62e9\u9762\u6700\u5927",
    "after": "\u901a\u5e38\u4ecd\u53ef\u6309\u627f\u8fd0\u65b9\u89c4\u5219\u529e\u7406\u53d8\u66f4\uff0c\u53d7\u89c4\u5219\u9650\u5236",
    "passed": "\u901a\u5e38\u65e0\u6cd5\u6309\u666e\u901a\u6539\u7b7e\u6d41\u7a0b\u529e\u7406\uff0c\u9700\u8054\u7cfb\u5b98\u65b9\u6e20\u9053",
    "cancelled": "\u6309\u627f\u8fd0\u65b9\u516c\u544a\u7684\u5904\u7f6e\u65b9\u6848\u529e\u7406\uff0c\u9000\u7968\u901a\u5e38\u4e0d\u6536\u8d39\u7528",
    "void": "\u65e0\u6cd5\u518d\u529e\u7406\uff0c\u9700\u67e5\u6e05\u4f5c\u5e9f\u539f\u56e0",
}

WANT_CN = {"change": "\u60f3\u6539\u671f", "refund": "\u60f3\u9000\u7968"}

CHANGE_COST = [
    ("\u65b0\u73ed\u6b21\u7968\u4ef7\u9ad8\u4e8e\u539f\u7968\u4ef7", "\u901a\u5e38\u9700\u8865\u5dee\u4ef7"),
    ("\u65b0\u73ed\u6b21\u7968\u4ef7\u4f4e\u4e8e\u539f\u7968\u4ef7", "\u5dee\u989d\u90e8\u5206\u7684\u5904\u7406\u65b9\u5f0f\u4ee5\u627f\u8fd0\u65b9\u73b0\u884c\u89c4\u5b9a\u4e3a\u51c6"),
    ("\u6539\u7b7e\u672c\u8eab", "\u4e0d\u662f\u514d\u8d39\u6539\uff0c\u901a\u5e38\u6d89\u53ca\u65b0\u65e7\u7968\u4ef7\u5dee\u989d\u5904\u7406"),
]

REFUND_COST = [
    ("\u5206\u6863\u65b9\u5f0f", "\u901a\u5e38\u6309\u8ddd\u5f00\u8f66\u65f6\u95f4\u7684\u957f\u77ed\u5206\u6863"),
    ("\u53d8\u5316\u8d8b\u52bf", "\u8d8a\u4e34\u8fd1\u5f00\u8f66\uff0c\u8d39\u7387\u901a\u5e38\u8d8a\u9ad8"),
    ("\u5177\u4f53\u6863\u4f4d\u4e0e\u8d39\u7387", "\u4ee5\u627f\u8fd0\u65b9\u73b0\u884c\u89c4\u5b9a\u4e3a\u51c6"),
    ("\u505c\u8fd0\u8bef\u70b9\u60c5\u5f62", "\u901a\u5e38\u6709\u4e13\u95e8\u7684\u5904\u7406\u65b9\u5f0f"),
]

DISRUPT_STEPS = [
    "\u5148\u770b\u5b98\u65b9\u516c\u544a\u6216\u901a\u77e5\uff0c\u786e\u8ba4\u5217\u8f66\u72b6\u6001",
    "\u786e\u8ba4\u81ea\u5df1\u80fd\u5426\u6362\u4e58\u540c\u4e00\u884c\u7a0b\u7684\u5176\u4ed6\u73ed\u6b21",
    "\u6709\u8854\u63a5\u884c\u7a0b\u7684\u5148\u5904\u7406\u8854\u63a5\u5173\u7cfb\uff0c\u4e0d\u8981\u53ea\u6539\u81ea\u5df1\u8fd9\u4e00\u6bb5",
    "\u6309\u627f\u8fd0\u65b9\u516c\u5e03\u7684\u5904\u7f6e\u65b9\u6848\u529e\u7406\u6539\u7b7e\u6216\u9000\u7968",
    "\u4fdd\u7559\u597d\u516c\u544a\u622a\u56fe\u4e0e\u529e\u7406\u51ed\u8bc1",
]

CHAIN_NOTES = [
    ("\u53ea\u6539\u4e86\u7b2c\u4e00\u6bb5\uff0c\u540e\u7eed\u8854\u63a5\u4f1a\u65ad", "\u540e\u7eed\u884c\u7a0b\u5f88\u53ef\u80fd\u9700\u8981\u4e00\u8d77\u5904\u7406"),
    ("\u53ea\u6539\u4e86\u6700\u540e\u4e00\u6bb5\uff0c\u524d\u6bb5\u53ef\u80fd\u767d\u8d39", "\u524d\u6bb5\u7968\u6b3e\u53ef\u80fd\u6d89\u53ca\u9000\u6539"),
    ("\u524d\u540e\u4e24\u6bb5\u4e0d\u5728\u540c\u4e00\u8ba2\u5355", "\u5904\u7406\u8d77\u6765\u66f4\u590d\u6742\uff0c\u9700\u8981\u5206\u522b\u786e\u8ba4"),
    ("\u4e2d\u95f4\u6bb5\u65e0\u6cd5\u6539", "\u6574\u6761\u884c\u7a0b\u53ef\u80fd\u53ea\u80fd\u91cd\u8ba2"),
]

CHAIN_ACTIONS = [
    "\u5148\u628a\u6240\u6709\u8981\u8854\u63a5\u7684\u884c\u7a0b\u5217\u51fa\u6765",
    "\u786e\u8ba4\u6bcf\u6bb5\u80fd\u5426\u6539\u3001\u80fd\u5426\u9000",
    "\u4f18\u5148\u6309\u6574\u6761\u884c\u7a0b\u7684\u53ef\u884c\u6027\u51b3\u7b56\uff0c\u800c\u4e0d\u662f\u53ea\u4fdd\u4f4f\u5176\u4e2d\u4e00\u6bb5",
    "\u6539\u5b8c\u540e\u91cd\u65b0\u786e\u8ba4\u8854\u63a5\u65f6\u95f4\u662f\u5426\u5408\u7406",
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


def build_report(status, segments, want):
    key = status if status in STATUS_CN else "before"
    try:
        segs = int(segments)
    except (TypeError, ValueError):
        segs = 1
    if segs < 1:
        segs = 1
    wkey = want if want in WANT_CN else "change"

    out = ["# \u9ad8\u94c1\u7968\u6539\u7b7e\u4e0e\u9000\u7968\u5904\u7f6e\u5efa\u8bae", ""]
    out.append("## \u7968\u7684\u72b6\u6001")
    out.append("")
    out.append("- \u72b6\u6001\uff1a**%s**" % STATUS_CN[key])
    out.append("- \u9009\u62e9\u9762\uff1a%s" % STATUS_OPTION[key])
    out.append("- \u4f60\u7684\u8bc9\u6c42\uff1a%s" % WANT_CN[wkey])
    out.append("- \u884c\u7a0b\u6bb5\u6570\uff1a%d \u6bb5" % segs)
    out.append("")
    out.append("\u6838\u5fc3\u53e3\u5f84\uff1a**\u80fd\u65e9\u5904\u7406\u5c31\u65e9\u5904\u7406\u3002** \u8d8a\u5f80\u540e\u53ef\u9009\u65b9\u6848\u8d8a\u5c11\u3001\u8fde\u5e26\u5f71\u54cd\u8d8a\u5927\u3002")
    out.append("")
    if wkey == "change":
        out.append("## \u6539\u7b7e\u8d39\u7684\u7ed3\u6784")
        out.append("")
        out.append("| \u60c5\u51b5 | \u5904\u7406\u65b9\u5411 |")
        out.append("|---|---|")
        for k, v in CHANGE_COST:
            out.append("| %s | %s |" % (k, v))
    else:
        out.append("## \u9000\u7968\u8d39\u7684\u7ed3\u6784")
        out.append("")
        out.append("| \u9879\u76ee | \u8bf4\u660e |")
        out.append("|---|---|")
        for k, v in REFUND_COST:
            out.append("| %s | %s |" % (k, v))
    out.append("")
    out.append("## \u6539\u7b7e\u4e0e\u9000\u7968\u7684\u5173\u952e\u5dee\u5f02")
    out.append("")
    out.append("| \u7ef4\u5ea6 | \u6539\u7b7e | \u9000\u7968 |")
    out.append("|---|---|---|")
    out.append("| \u7ed3\u679c | \u4fdd\u7559\u4e58\u8f66\u8d44\u683c\uff0c\u53e6\u51fa\u4e00\u5f20\u7968 | \u53d6\u6d88\u4e58\u8f66\uff0c\u9000\u56de\u7968\u6b3e\u6263\u9664\u8d39\u7528 |")
    out.append("| \u8d39\u7528\u7ed3\u6784 | \u6309\u65b0\u65e7\u7968\u4ef7\u5dee\u989d | \u6309\u8ddd\u5f00\u8f66\u65f6\u95f4\u5206\u6863 |")
    out.append("| \u9002\u7528 | \u8fd8\u60f3\u53bb\uff0c\u53ea\u662f\u65f6\u95f4\u53d8\u4e86 | \u884c\u7a0b\u672c\u8eab\u53d6\u6d88\u4e86 |")
    out.append("")
    out.append("\u5224\u65ad\u65b9\u5411\uff1a\u884c\u7a0b\u8fd8\u60f3\u53bb\u4f46\u65f6\u95f4\u8981\u53d8\uff0c\u4f18\u5148\u8003\u8651\u6539\u7b7e\uff1b\u884c\u7a0b\u53d6\u6d88\u4e86\uff0c\u518d\u8003\u8651\u9000\u7968\u3002")
    out.append("")
    if key in ("cancelled",):
        out.append("## \u8bef\u70b9\u4e0e\u505c\u8fd0\u7684\u5904\u7f6e\u987a\u5e8f")
        out.append("")
        for i, step in enumerate(DISRUPT_STEPS, 1):
            out.append("%d. %s" % (i, step))
        out.append("")
    if segs > 1:
        out.append("## \u8054\u7a0b\u4e0e\u5206\u6bb5\u884c\u7a0b\u7684\u8fde\u5e26\u5f71\u54cd")
        out.append("")
        out.append("| \u60c5\u51b5 | \u9700\u8981\u6ce8\u610f |")
        out.append("|---|---|")
        for k, v in CHAIN_NOTES:
            out.append("| %s | %s |" % (k, v))
        out.append("")
        out.append("\u5904\u7406\u8981\u70b9\uff1a")
        out.append("")
        for i, a in enumerate(CHAIN_ACTIONS, 1):
            out.append("%d. %s" % (i, a))
        out.append("")
        out.append("\u6709\u8854\u63a5\u884c\u7a0b\u65f6\uff0c\u6539\u7b7e\u4e0d\u80fd\u53ea\u770b\u81ea\u5df1\u8fd9\u4e00\u6bb5\u3002")
        out.append("")
    out.append("## \u4e0b\u4e00\u6b65")
    out.append("")
    out.append("1. \u5728\u627f\u8fd0\u65b9\u5b98\u65b9\u6e20\u9053\u786e\u8ba4\u5f53\u524d\u53ef\u6539\u73ed\u6b21\u4e0e\u5b9e\u9645\u8d39\u7528")
    out.append("2. \u4e00\u6b21\u628a\u8981\u6539\u7684\u90fd\u6539\u5b8c\uff0c\u4e0d\u8981\u5206\u591a\u6b21\u64cd\u4f5c")
    out.append("3. \u4fdd\u7559\u516c\u544a\u622a\u56fe\u4e0e\u529e\u7406\u51ed\u8bc1")
    out.append("")
    out.append("## \u8fb9\u754c")
    out.append("")
    out.append("- \u6539\u7b7e\u65f6\u95f4\u7a97\u3001\u6b21\u6570\u3001\u8d39\u7387\u4e0e\u9000\u7968\u8d39\u6863\u4f4d\u4ee5\u627f\u8fd0\u65b9\u73b0\u884c\u89c4\u5b9a\u4e3a\u51c6")
    out.append("- \u672c\u811a\u672c\u4e0d\u7ed9\u51fa\u4efb\u4f55\u8d39\u7387\u4e0e\u65f6\u95f4\u7a97\u6570\u5b57\uff0c\u4e5f\u4e0d\u5f15\u7528\u6761\u6b3e\u53f7")
    out.append("- \u4e0d\u5224\u65ad\u67d0\u6b21\u5217\u8f66\u662f\u5426\u4e00\u5b9a\u505c\u8fd0\u6216\u665a\u70b9\uff0c\u4ee5\u5b98\u65b9\u516c\u544a\u4e3a\u51c6")
    out.append("- \u4e0d\u4ee3\u7528\u6237\u5728\u8d2d\u7968\u6e20\u9053\u6267\u884c\u4efb\u4f55\u64cd\u4f5c")
    return "\n".join(out) + "\n"


def selftest():
    cases = []
    cases.append(("st_before", "\u5f00\u8f66\u524d" in build_report("before", 1, "change")))
    cases.append(("st_after", "\u5f00\u8f66\u540e\u672a\u5230\u7ad9" in build_report("after", 1, "change")))
    cases.append(("st_passed", "\u5df2\u8fc7\u7ad9" in build_report("passed", 1, "change")))
    cases.append(("st_cancel", "\u5217\u8f66\u505c\u8fd0" in build_report("cancelled", 1, "change")))
    cases.append(("st_void", "\u7968\u636e\u5df2\u4f5c\u5e9f" in build_report("void", 1, "change")))
    cases.append(("st_fallback", "\u5f00\u8f66\u524d" in build_report("weird", 1, "change")))
    rep_refund = build_report("before", 1, "refund")
    cases.append(("refund_cost", "\u9000\u7968\u8d39\u7684\u7ed3\u6784" in rep_refund))
    cases.append(("refund_banding", "\u6309\u8ddd\u5f00\u8f66\u65f6\u95f4\u7684\u957f\u77ed\u5206\u6863" in rep_refund))
    rep_change = build_report("before", 1, "change")
    cases.append(("change_cost", "\u6539\u7b7e\u8d39\u7684\u7ed3\u6784" in rep_change))
    cases.append(("change_diff", "\u8865\u5dee\u4ef7" in rep_change))
    rep_chain = build_report("before", 3, "change")
    cases.append(("chain_note", "\u8fde\u5e26\u5f71\u54cd" in rep_chain))
    cases.append(("chain_actions", "\u6bcf\u6bb5\u80fd\u5426\u6539" in rep_chain))
    cases.append(("no_chain_single", "\u8054\u7a0b\u4e0e\u5206\u6bb5\u884c\u7a0b" not in rep_change))
    rep_dis = build_report("cancelled", 1, "change")
    cases.append(("disrupt_steps", "\u5904\u7f6e\u987a\u5e8f" in rep_dis))
    cases.append(("no_disrupt_before", "\u8bef\u70b9\u4e0e\u505c\u8fd0\u7684\u5904\u7f6e\u987a\u5e8f" not in rep_change))
    cases.append(("seg_str_fallback", "\u884c\u7a0b\u6bb5\u6570\uff1a1 \u6bb5" in build_report(
        "before", "abc", "change")))
    cases.append(("seg_zero", "\u884c\u7a0b\u6bb5\u6570\uff1a1 \u6bb5" in build_report(
        "before", 0, "change")))
    cases.append(("want_fallback", "\u60f3\u6539\u671f" in build_report(
        "before", 1, "weird")))
    cases.append(("no_numbers", "\u4e0d\u7ed9\u51fa\u4efb\u4f55\u8d39\u7387\u4e0e\u65f6\u95f4\u7a97\u6570\u5b57" in rep_change))
    bom = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_probe.json")
    with open(bom, "w", encoding="utf-8-sig") as f:
        f.write('{"status": "after", "segments": 2}')
    try:
        data = load_json(bom)
        cases.append(("bom_ok", data.get("status") == "after"))
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
    ap = argparse.ArgumentParser(description="train ticket change audit")
    ap.add_argument("--status", default=None)
    ap.add_argument("--segments", default=None)
    ap.add_argument("--want", default=None)
    ap.add_argument("--file", default=None)
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
    for key, val in (("status", a.status), ("segments", a.segments),
                     ("want", a.want)):
        if val is not None:
            data[key] = val
    report = build_report(data.get("status", "before"),
                          data.get("segments", 1),
                          data.get("want", "change"))
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "train_change_result.md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
