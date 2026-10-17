# -*- coding: utf-8 -*-
"""\u9605\u8bfb\u7406\u89e3\u9898\u578b\u63a8\u65ad\u4e0e\u9009\u9879\u9677\u9631\u626b\u63cf\u3002\u6807\u51c6\u5e93\u3002

\u7528\u6cd5:
  python answer_trap_scanner.py --file item.json
  python answer_trap_scanner.py --selftest
"""

import argparse
import json
import os
import sys

RESULT_FILE = "_selftest_result.txt"

TYPE_RULES = [
    ("\u63a8\u65ad\u9898", ["\u63a8\u65ad", "\u63a8\u51fa", "\u8868\u660e", "\u8bf4\u660e", "imply", "suggest"]),
    ("\u8bcd\u53e5\u7406\u89e3\u9898", ["\u52a0\u7c97", "\u5212\u7ebf", "\u753b\u7ebf", "\u4e0b\u5212\u7ebf", "\u6307\u4ee3", "\u610f\u601d\u662f"]),
    ("\u6001\u5ea6\u9898", ["\u6001\u5ea6", "\u770b\u6cd5", "\u89c2\u70b9", "\u8bc4\u4ef7", "opinion", "attitude"]),
    ("\u4e3b\u65e8\u9898", ["\u4e3b\u65e8", "\u4e3b\u8981\u610f\u601d", "\u6807\u9898", "\u4e2d\u5fc3", "main idea", "purpose", "title"]),
    ("\u6982\u62ec\u9898", ["\u6982\u62ec", "\u5f52\u7eb3", "\u7b80\u8ff0", "summary", "summarize"]),
    ("\u7ec6\u8282\u9898", ["\u6b63\u786e", "\u7b26\u5408", "\u54ea\u9879", "according", "true", "except"]),
]

ABSOLUTE_WORDS = ["\u6240\u6709", "\u5168\u90e8", "\u4e00\u5b9a", "\u5fc5\u7136", "\u603b\u662f", "\u4ece\u4e0d", "\u5b8c\u5168", "\u7edd\u5bf9",
                  "all", "always", "never", "must", "certainly", "only"]
EXTREME_WORDS = ["\u5927\u90e8\u5206", "\u7edd\u5927\u591a\u6570", "\u5927\u591a\u6570", "\u5927\u90e8\u5206\u7684", "\u666e\u904d", "\u5f80\u5f80",
                 "most", "majority", "generally", "widely"]
CAUSAL_WORDS = ["\u5bfc\u81f4", "\u5f15\u8d77", "\u9020\u6210", "\u56e0\u4e3a", "\u6240\u4ee5", "\u4f7f\u5f97", "\u51b3\u5b9a",
                "cause", "lead to", "result in", "due to", "determine"]


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return json.loads(raw.lstrip("\ufeff"))


def guess_type(stem):
    low = (stem or "").lower()
    for name, kws in TYPE_RULES:
        for k in kws:
            if k in low:
                return name
    return "\u7ec6\u8282\u9898"


def scan_option(text):
    low = (text or "").lower()
    hits = []
    if any(w in low for w in ABSOLUTE_WORDS):
        hits.append("\u7edd\u5bf9\u5316")
    if any(w in low for w in EXTREME_WORDS):
        hits.append("\u8303\u56f4\u6269\u5927")
    if any(w in low for w in CAUSAL_WORDS):
        hits.append("\u56e0\u679c\u654f\u611f\u9879")
    if len(text or "") > 80:
        hits.append("\u8986\u76d6\u9762\u8fc7\u5927")
    return hits


def analyze(stem, options):
    qtype = guess_type(stem)
    rows = []
    for idx, opt in enumerate(options):
        hits = scan_option(opt)
        rows.append({"index": idx, "text": opt, "trap_types": hits})
    risky = sum(1 for r in rows if r["trap_types"])
    checks = []
    if qtype == "\u63a8\u65ad\u9898":
        checks.append("\u9010\u6761\u628a\u9009\u9879\u6539\u5199\u6210\u539f\u6587\u9648\u8ff0\u53e5\uff0c\u627e\u4e0d\u5230\u4f9d\u636e\u5373\u6392\u9664")
        checks.append("\u6bd4\u8f83\u5f3a\u5ea6\u8bcd\uff1a\u539f\u6587 may \u5bf9\u9009\u9879 will \u76f4\u63a5\u6392\u9664")
    elif qtype == "\u4e3b\u65e8\u9898":
        checks.append("\u68c0\u67e5\u8986\u76d6\u9762\uff1a\u95ee\u8fd9\u4e2a\u9009\u9879\u5728\u7b2c\u51e0\u6bb5\u80fd\u88ab\u5b8c\u6574\u652f\u6301")
    elif qtype == "\u6001\u5ea6\u9898":
        checks.append("\u533a\u5206\u4f5c\u8005\u7acb\u573a\u4e0e\u6587\u4e2d\u88ab\u5f15\u8ff0\u8005\u7684\u7acb\u573a")
    elif qtype == "\u8bcd\u53e5\u7406\u89e3\u9898":
        checks.append("\u56de\u539f\u6587\u5b9a\u4f4d\u8be5\u8bcd\uff0c\u5148\u5b9a\u672c\u53e5\u4e49\u518d\u770b\u4e0a\u4e0b\u6587")
    elif qtype == "\u7ec6\u8282\u9898":
        checks.append("\u9010\u5b57\u6838\u5bf9\u6570\u5b57\u3001\u65f6\u95f4\u3001\u8303\u56f4\u4e09\u5904")
    else:
        checks.append("\u5148\u7ed9\u6bcf\u6bb5\u5199\u4e00\u53e5\u6982\u62ec\uff0c\u518d\u5408\u5e76")
    checks.append("\u56db\u4e2a\u9009\u9879\u5168\u90e8\u6bd4\u5bf9\u8fc7\u624d\u786e\u5b9a\u7b54\u6848")
    return {
        "question_type": qtype,
        "options": rows,
        "risky_options": risky,
        "checks": checks,
        "note": "\u9677\u9631\u547d\u4e2d\u53ea\u662f\u63d0\u793a\uff0c\u6700\u7ec8\u5fc5\u987b\u56de\u539f\u6587\u9010\u5b57\u6bd4\u5bf9",
    }


def run_file(path, as_json):
    data = read_json(path)
    res = analyze(data.get("stem", ""), data.get("options") or [])
    if as_json:
        return json.dumps(res, ensure_ascii=False, indent=2)
    lines = []
    lines.append("\u63a8\u65ad\u9898\u578b: %s" % res["question_type"])
    for r in res["options"]:
        tag = "/".join(r["trap_types"]) if r["trap_types"] else "\u65e0\u660e\u663e\u9677\u9631\u7279\u5f81"
        lines.append("  \u9009\u9879%d  %s  [%s]" % (r["index"], r["text"][:40], tag))
    lines.append("\u542b\u9677\u9631\u7279\u5f81\u7684\u9009\u9879\u6570: %d" % res["risky_options"])
    for c in res["checks"]:
        lines.append("- %s" % c)
    lines.append(res["note"])
    return "\n".join(lines)


def selftest():
    fails = []

    def ck(name, cond):
        if not cond:
            fails.append(name)

    ck("t1 \u63a8\u65ad\u9898\u8bc6\u522b", guess_type("\u4ee5\u4e0b\u53ef\u4ee5\u63a8\u65ad\u51fa\u4ec0\u4e48") == "\u63a8\u65ad\u9898")
    ck("t2 \u4e3b\u65e8\u9898\u8bc6\u522b", guess_type("\u8fd9\u7bc7\u6587\u7ae0\u7684\u4e3b\u8981\u610f\u601d") == "\u4e3b\u65e8\u9898")
    ck("t3 \u6001\u5ea6\u9898\u8bc6\u522b", guess_type("\u4f5c\u8005\u5bf9\u8fd9\u4e00\u89c2\u70b9\u7684\u6001\u5ea6") == "\u6001\u5ea6\u9898")
    ck("t4 \u8bcd\u53e5\u7406\u89e3\u9898\u8bc6\u522b", guess_type("\u5212\u7ebf\u90e8\u5206\u7684\u542b\u4e49") == "\u8bcd\u53e5\u7406\u89e3\u9898")
    ck("t5 \u515c\u5e95\u4e3a\u7ec6\u8282\u9898", guess_type("") == "\u7ec6\u8282\u9898")

    ck("t6 \u7edd\u5bf9\u5316\u547d\u4e2d", "\u7edd\u5bf9\u5316" in scan_option("\u6240\u6709\u4eba\u90fd\u8fd9\u6837\u505a"))
    ck("t7 \u8303\u56f4\u6269\u5927\u547d\u4e2d", "\u8303\u56f4\u6269\u5927" in scan_option("\u5927\u90e8\u5206\u7814\u7a76\u8868\u660e"))
    ck("t8 \u56e0\u679c\u654f\u611f\u547d\u4e2d", "\u56e0\u679c\u654f\u611f\u9879" in scan_option("\u8fd9\u5bfc\u81f4\u4e86\u4ef7\u683c\u4e0a\u6da8"))
    ck("t9 \u666e\u901a\u9009\u9879\u65e0\u9677\u9631", scan_option("\u4ed6\u5728\u56fe\u4e66\u9986\u770b\u4e66") == [])

    r = analyze("\u4ee5\u4e0b\u53ef\u4ee5\u63a8\u51fa\u7684\u662f", ["\u4e00\u5b9a\u4f1a\u6210\u529f", "\u4e5f\u8bb8\u53ef\u80fd", "x"])
    ck("t10 \u63a8\u65ad\u9898\u5e26\u51fa\u5f3a\u5ea6\u6bd4\u5bf9\u68c0\u67e5", any("\u5f3a\u5ea6" in c for c in r["checks"]))
    ck("t11 \u56db\u9879\u5168\u6bd4\u5bf9\u63d0\u793a\u5b58\u5728", any("\u56db\u4e2a\u9009\u9879" in c for c in r["checks"]))

    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_case.json")
    with open(tmp, "w", encoding="utf-8-sig") as f:
        json.dump({"stem": "\u4e3b\u65e8\u662f\u4ec0\u4e48", "options": ["a"]}, f, ensure_ascii=False)
    d = read_json(tmp)
    ck("t12 BOM \u8f93\u5165\u89e3\u6790\u6210\u529f", d.get("stem") == "\u4e3b\u65e8\u662f\u4ec0\u4e48")
    os.remove(tmp)

    ck("t13 \u7a7a\u9009\u9879\u4e0d\u62a5\u9519", analyze("", [])["risky_options"] == 0)

    out = []
    out.append("SELFTEST FAIL: %s" % "; ".join(fails) if fails else "SELFTEST OK  13/13")
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, RESULT_FILE), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="\u9605\u8bfb\u7406\u89e3\u9898\u578b\u4e0e\u9677\u9631\u626b\u63cf")
    ap.add_argument("--file")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.file:
        print(run_file(a.file, a.json))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())