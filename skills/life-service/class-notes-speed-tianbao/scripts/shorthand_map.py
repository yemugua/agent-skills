# -*- coding: utf-8 -*-
"""\u7b14\u8bb0\u7247\u6bb5\u5206\u7c7b\u3001\u7b26\u53f7\u8986\u76d6\u4e0e\u51b2\u7a81\u68c0\u6d4b\u3001\u7ed3\u6784\u5339\u914d\u5efa\u8bae\u3002\u6807\u51c6\u5e93\u3002

\u7528\u6cd5:
  python shorthand_map.py --file notes.json
  python shorthand_map.py --selftest
"""

import argparse
import json
import os
import sys

RESULT_FILE = "_selftest_result.txt"

KEEP_KINDS = ["\u5b9a\u4e49", "\u7ed3\u6784", "\u5f3a\u8c03", "\u7591\u95ee"]
DROP_KINDS = ["\u6f14\u7b97", "\u94fa\u57ab", "\u5df2\u77e5"]
STRUCTURE_ORDER = ["\u6d41\u7a0b", "\u63a8\u5bfc", "\u9012\u8fdb"]
STRUCTURE_PARALLEL = ["\u5e76\u5217", "\u8981\u70b9", "\u5bf9\u7167"]
MAP_STRUCTURE = {"linear": "\u7ebf\u6027", "branch": "\u5206\u652f", "hybrid": "\u7ebf\u6027\u4e3b\u5e72\u52a0\u5206\u652f"}


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return json.loads(raw.lstrip("\ufeff"))


def classify(segments):
    """\u7edf\u8ba1\u8be5\u8bb0\u4e0e\u4e0d\u8be5\u8bb0\u7247\u6bb5\u3002"""
    keep = []
    drop = []
    other = []
    for i, s in enumerate(segments or []):
        kind = str(s.get("kind") or "").strip()
        if kind in KEEP_KINDS:
            keep.append(i)
        elif kind in DROP_KINDS:
            drop.append(i)
        else:
            other.append({"index": i, "kind": kind})
    return {"keep": keep, "drop": drop, "unknown": other}


def check_symbols(segments, symbols):
    """\u7b26\u53f7\u8986\u76d6\u7387\u4e0e\u542b\u4e49\u51b2\u7a81\u68c0\u6d4b\u3002"""
    syms = symbols or {}
    used = set()
    for s in segments or []:
        for ch in str(s.get("text") or ""):
            if ch in "!?*!":
                used.add(ch)
    unknown = sorted(u for u in used if u not in syms)
    conflicts = []
    seen = {}
    for name, val in syms.items():
        v = str(val).strip()
        if not v:
            continue
        if v in seen and seen[v] != name:
            conflicts.append("%s\u4e0e%s\u5171\u7528\u540c\u4e00\u4e2a\u7b26\u53f7\uff0c\u542b\u4e49\u4f1a\u6df7\u6dc6" % (seen[v], name))
        else:
            seen[v] = name
    return {"used": sorted(used), "undefined": unknown, "conflicts": conflicts,
            "coverage": (len(used - set(unknown)) / len(used)) if used else 1.0}


def suggest_structure(form):
    """\u6309\u5185\u5bb9\u5f62\u6001\u7ed9\u7ed3\u6784\u5efa\u8bae\u3002"""
    f = form or ""
    linear = [k for k in STRUCTURE_ORDER if k in f]
    parallel = [k for k in STRUCTURE_PARALLEL if k in f]
    if linear and parallel:
        return "hybrid", "\u7ebf\u6027\u4e3b\u5e72\u52a0\u5206\u652f\uff1a\u4e3b\u5e72\u4fdd\u7559\u987a\u5e8f\uff0c\u65c1\u652f\u6302\u5206\u652f"
    if linear:
        return "linear", "\u987a\u5e8f\u672c\u8eab\u643a\u5e26\u4fe1\u606f\uff0c\u7528\u7ebf\u6027\u8bb0\u5f55\uff1b\u5206\u652f\u4f1a\u7834\u574f\u903b\u8f91\u94fe"
    if parallel:
        return "branch", "\u5e76\u5217\u5173\u7cfb\u9700\u540c\u5c42\u5c55\u793a\uff0c\u7528\u5206\u652f\u8bb0\u5f55"
    return "hybrid", "\u5f62\u6001\u4e0d\u660e\u786e\uff0c\u5efa\u8bae\u4e3b\u5e72\u7ebf\u6027\u5e76\u9884\u7559\u5206\u652f\u533a"


def analyze(data):
    segments = data.get("segments") or []
    cls = classify(segments)
    sym = check_symbols(segments, data.get("symbols"))
    st, why = suggest_structure(data.get("form"))
    cur = data.get("structure")
    cur_label = MAP_STRUCTURE.get(cur, cur or "\u672a\u6307\u5b9a")
    return {
        "total": len(segments),
        "classify": cls,
        "symbols": sym,
        "suggest_structure": st,
        "suggest_label": MAP_STRUCTURE[st],
        "reason": why,
        "current_label": cur_label,
        "mismatch": bool(cur) and cur != st,
        "tips": [
            "\u901f\u8bb0\u7684\u76ee\u7684\u662f\u8bb0\u4f4f\u7ed3\u6784\u800c\u4e0d\u662f\u5199\u5b57\u597d\u770b",
            "\u5f53\u573a\u6c42\u5feb\u8bfe\u540e\u6c42\u6574\uff0c\u5de5\u6574\u4e0d\u53ef\u6301\u7eed",
            "\u8bfe\u540e\u5341\u5206\u949f\u5185\u6e05\u7406\u95ee\u53f7\u6807\u8bb0\u5e76\u8865\u5168\u7a7a\u7f3a",
        ],
    }


def run_file(path, as_json):
    res = analyze(read_json(path))
    if as_json:
        return json.dumps(res, ensure_ascii=False, indent=2)
    lines = []
    lines.append("\u7247\u6bb5\u603b\u6570: %d" % res["total"])
    c = res["classify"]
    lines.append("\u8be5\u8bb0: %d  \u4e0d\u8be5\u8bb0: %d  \u672a\u5206\u7c7b: %d"
                 % (len(c["keep"]), len(c["drop"]), len(c["unknown"])))
    s = res["symbols"]
    lines.append("\u7b26\u53f7\u4f7f\u7528: %s" % (s["used"] or "\u65e0"))
    lines.append("\u672a\u5b9a\u4e49\u7b26\u53f7: %s" % (s["undefined"] or "\u65e0"))
    lines.append("\u7b26\u53f7\u542b\u4e49\u51b2\u7a81: %s" % (s["conflicts"] or "\u65e0"))
    lines.append("\u7b26\u53f7\u8986\u76d6\u7387: %.0f%%" % (s["coverage"] * 100))
    lines.append("\u5efa\u8bae\u7ed3\u6784: %s\uff08\u5f53\u524d: %s\uff09" % (res["suggest_label"], res["current_label"]))
    if res["mismatch"]:
        lines.append("  \u7ed3\u6784\u4e0e\u5185\u5bb9\u5f62\u6001\u4e0d\u5339\u914d\uff0c\u5efa\u8bae\u8c03\u6574")
    lines.append("\u7406\u7531: %s" % res["reason"])
    for t in res["tips"]:
        lines.append("- %s" % t)
    return "\n".join(lines)


def selftest():
    fails = []

    def ck(name, cond):
        if not cond:
            fails.append(name)

    segs = [{"kind": "\u5b9a\u4e49", "text": "\u5f39\u6027\u6a21\u91cf*"}, {"kind": "\u6f14\u7b97", "text": "x"},
            {"kind": "\u7591\u95ee", "text": "? \u4e3a\u4ec0\u4e48"}]
    cls = classify(segs)
    ck("t1 \u8be5\u8bb0\u7247\u6bb5\u88ab\u8bc6\u522b", cls["keep"] == [0, 2])
    ck("t2 \u4e0d\u8be5\u8bb0\u7247\u6bb5\u88ab\u8bc6\u522b", cls["drop"] == [1])
    ck("t3 \u672a\u5206\u7c7b\u88ab\u8bc6\u522b", len(cls["unknown"]) == 0)

    cls2 = classify([{"kind": "\u95f2\u804a"}])
    ck("t4 \u672a\u77e5\u7c7b\u578b\u8fdb\u672a\u5206\u7c7b", len(cls2["unknown"]) == 1)
    ck("t5 \u7a7a\u5217\u8868\u4e0d\u62a5\u9519", classify([])["keep"] == [])

    syms = {"\u91cd\u8981": "*", "\u95ee\u9898": "?", "\u6613\u9519\u70b9": "!"}
    s = check_symbols(segs, syms)
    ck("t6 \u672a\u5b9a\u4e49\u7b26\u53f7\u88ab\u62a5", "*" in s["undefined"] or "!" in s["undefined"])
    ck("t7 \u7b26\u53f7\u8986\u76d6\u7387\u57280\u52301\u4e4b\u95f4", 0.0 <= s["coverage"] <= 1.0)

    s2 = check_symbols([{"text": "\u65e0\u7b26\u53f7"}], {})
    ck("t8 \u65e0\u7b26\u53f7\u65f6\u8986\u76d6\u7387\u4e3a1", s2["coverage"] == 1.0)
    s3 = check_symbols([{"text": "!"}], {"\u91cd\u8981": "*", "\u6613\u9519\u70b9": "*"})
    ck("t9 \u51b2\u7a81\u88ab\u62a5", len(s3["conflicts"]) == 1)

    ck("t10 \u987a\u5e8f\u5185\u5bb9\u5efa\u8bae\u7ebf\u6027", suggest_structure("\u6d41\u7a0b\u4e0e\u63a8\u5bfc")[0] == "linear")
    ck("t11 \u5e76\u5217\u5185\u5bb9\u5efa\u8bae\u5206\u652f", suggest_structure("\u591a\u4e2a\u5e76\u5217\u8981\u70b9")[0] == "branch")
    ck("t12 \u6df7\u5408\u5efa\u8baehybrid", suggest_structure("\u9012\u8fdb\u4e0e\u5e76\u5217\u5bf9\u7167")[0] == "hybrid")
    ck("t13 \u5f62\u6001\u4e0d\u660e\u4e0d\u62a5\u9519", suggest_structure("")[0] == "hybrid")

    r = analyze({"segments": segs, "symbols": syms, "structure": "branch", "form": "\u6d41\u7a0b\u63a8\u5bfc"})
    ck("t14 \u7ed3\u6784\u4e0d\u5339\u914d\u88ab\u6807\u8bb0", r["mismatch"] is True)
    r2 = analyze({"segments": segs, "structure": "linear", "form": "\u6d41\u7a0b\u63a8\u5bfc"})
    ck("t15 \u7ed3\u6784\u5339\u914d\u4e0d\u62a5", r2["mismatch"] is False)

    ck("t16 \u7a7a\u8f93\u5165\u4e0d\u62a5\u9519", analyze({})["total"] == 0)

    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_case.json")
    with open(tmp, "w", encoding="utf-8-sig") as f:
        json.dump({"segments": []}, f, ensure_ascii=False)
    ck("t17 BOM \u8f93\u5165\u89e3\u6790\u6210\u529f", isinstance(read_json(tmp)["segments"], list))
    os.remove(tmp)

    ck("t18 \u7ed3\u6784\u6807\u7b7e\u6620\u5c04\u9f50\u5168", set(MAP_STRUCTURE.keys()) == {"linear", "branch", "hybrid"})
    ck("t19 tips \u5305\u542b\u6838\u5fc3\u539f\u5219", any("\u7ed3\u6784" in t for t in analyze({})["tips"]))

    out = []
    out.append("SELFTEST FAIL: %s" % "; ".join(fails) if fails else "SELFTEST OK  19/19")
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, RESULT_FILE), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="\u7b14\u8bb0\u7247\u6bb5\u5206\u7c7b\u4e0e\u7b26\u53f7\u68c0\u67e5")
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