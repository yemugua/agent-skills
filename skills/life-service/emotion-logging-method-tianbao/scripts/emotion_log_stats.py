# -*- coding: utf-8 -*-
"""\u60c5\u7eea\u8bb0\u5f55\u7edf\u8ba1\u4e0e\u6c42\u52a9\u7ea2\u7ebf\u63d0\u793a\u3002\u6807\u51c6\u5e93\u3002

\u7528\u6cd5:
  python emotion_log_stats.py --file log.json
  python emotion_log_stats.py --selftest
"""

import argparse
import json
import os
import sys

RESULT_FILE = "_selftest_result.txt"

# \u6c42\u52a9\u7ea2\u7ebf\u4fe1\u53f7\u8bcd
RED_LINE_WORDS = ["\u81ea\u6740", "\u81ea\u4f24", "\u8f7b\u751f", "\u4e0d\u60f3\u6d3b", "\u7ed3\u675f\u751f\u547d", "\u4f24\u5bb3\u81ea\u5df1"]
RED_LINE_LONG = ["\u5e7b\u89c9", "\u5984\u60f3"]
RED_LINE_MANIA = ["\u5c11\u7761\u5374\u4e0d\u56f0", "\u5f02\u5e38\u5174\u594b", "\u601d\u7ef4\u5954\u9038", "\u505c\u4e0d\u4e0b\u6765"]
RED_LINE_ANXIETY = ["\u60ca\u6050", "\u53d1\u4f5c"]
RED_LINE_EATING = ["\u50ac\u5410", "\u8fc7\u5ea6\u8fd0\u52a8", "\u4f53\u91cd\u9aa4\u964d"]
RED_LINE_SUBSTANCE = ["\u5931\u63a7", "\u6212\u65ad"]
SELF_CRITICAL = ["\u6211\u600e\u4e48\u8fd9\u4e48\u5dee", "\u6211\u771f\u6ca1\u7528", "\u8ba8\u538c\u81ea\u5df1", "\u4e0d\u591f\u597d", "\u5931\u8d25\u8005", "\u5e9f\u7269"]
POSITIVE = ["\u987a\u5229", "\u5f00\u5fc3", "\u5b8c\u6210", "\u88ab\u8ba4\u53ef", "\u653e\u677e"]


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return json.loads(raw.lstrip("\ufeff"))


def all_text(entry):
    return " ".join(str(entry.get(k) or "") for k in
                     ("trigger", "body", "emotion", "thought", "behavior", "result"))


def check_red_lines(entries):
    hits = []
    for i, e in enumerate(entries or []):
        t = all_text(e)
        for w in RED_LINE_WORDS:
            if w in t:
                hits.append({"index": i, "level": "\u5371\u673a", "word": w})
        for w in RED_LINE_LONG:
            if w in t:
                hits.append({"index": i, "level": "\u9700\u7acb\u5373\u8bc4\u4f30", "word": w})
        for w in RED_LINE_MANIA:
            if w in t:
                hits.append({"index": i, "level": "\u9700\u7acb\u5373\u8bc4\u4f30", "word": w})
        for w in RED_LINE_ANXIETY:
            if w in t:
                hits.append({"index": i, "level": "\u9700\u4e13\u4e1a\u6cbb\u7597", "word": w})
        for w in RED_LINE_EATING:
            if w in t:
                hits.append({"index": i, "level": "\u9700\u4e13\u4e1a\u5e72\u9884", "word": w})
        for w in RED_LINE_SUBSTANCE:
            if w in t:
                hits.append({"index": i, "level": "\u9700\u4e13\u4e1a\u5e72\u9884", "word": w})
    return hits


def intensity_trend(entries):
    vals = []
    for e in entries or []:
        v = e.get("intensity")
        if v is not None:
            try:
                vals.append(float(v))
            except (TypeError, ValueError):
                pass
    if len(vals) < 2:
        return {"values": vals, "rising": False, "avg": (sum(vals) / len(vals)) if vals else 0.0}
    half = len(vals) // 2
    early = sum(vals[:half]) / half
    late = sum(vals[half:]) / max(1, len(vals) - half)
    return {"values": vals, "rising": late > early, "avg": sum(vals) / len(vals)}


def top_repeat(entries, field):
    counts = {}
    for e in entries or []:
        v = str(e.get(field) or "").strip()
        if not v:
            continue
        key = v if len(v) <= 12 else v[:12]
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return [], 0
    top = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    return top, top[0][1]


def check_self_critical(entries):
    hits = []
    for i, e in enumerate(entries or []):
        t = all_text(e)
        for w in SELF_CRITICAL:
            if w in t:
                hits.append({"index": i, "word": w})
    return hits


def check_positive(entries):
    return any(any(w in all_text(e) for w in POSITIVE) for e in entries or [])


def analyze(data):
    entries = data.get("entries") or []
    red = check_red_lines(entries)
    trend = intensity_trend(entries)
    trig, trig_n = top_repeat(entries, "trigger")
    body, body_n = top_repeat(entries, "body")
    thought, thought_n = top_repeat(entries, "thought")
    sc = check_self_critical(entries)
    res = {
        "count": len(entries),
        "red_lines": red,
        "trend": trend,
        "top_trigger": trig,
        "top_body": body,
        "top_thought": thought,
        "self_critical": sc,
        "has_positive": check_positive(entries),
        "concern_window": bool(data.get("concern_window")),
    }
    tips = []
    if red:
        tips.append("\u547d\u4e2d\u6c42\u52a9\u7ea2\u7ebf\u4fe1\u53f7\uff0c\u5fc5\u987b\u4f18\u5148\u8f6c\u4ecb\u4e13\u4e1a\u652f\u6301\uff0c\u4e0d\u8fdb\u884c\u81ea\u6211\u8bb0\u5f55\u5904\u7406")
    if trend["rising"]:
        tips.append("\u5f3a\u5ea6\u5448\u9012\u589e\u8d8b\u52bf\uff0c\u538b\u529b\u53ef\u80fd\u5728\u7d2f\u79ef\uff0c\u5efa\u8bae\u4e3b\u52a8\u5bfb\u6c42\u4e13\u4e1a\u652f\u6301")
    if trig_n >= 3:
        tips.append("\u5b58\u5728\u91cd\u590d\u89e6\u53d1\u6e90\uff0c\u9700\u5728\u56de\u770b\u65f6\u91cd\u70b9\u5173\u6ce8")
    if body_n >= 3:
        tips.append("\u8eab\u4f53\u53cd\u5e94\u9ad8\u5ea6\u91cd\u590d\uff0c\u53ef\u4f5c\u4e3a\u8bc6\u522b\u6a21\u5f0f\u7684\u951a\u70b9")
    if sc:
        tips.append("\u8bb0\u5f55\u4e2d\u51fa\u73b0\u81ea\u6211\u5ba1\u5224\u8868\u8ff0\uff0c\u6539\u4e3a\u89c2\u5bdf\u5f0f\u8bb0\u5f55")
    if not res["has_positive"] and entries:
        tips.append("\u672a\u89c1\u6b63\u5411\u8bb0\u5f55\uff0c\u53ea\u8bb0\u8d1f\u9762\u4f1a\u4f7f\u8bb0\u5f55\u53d8\u6210\u75db\u82e6\u6e05\u5355")
    if not res["concern_window"] and entries:
        tips.append("\u672a\u8bbe\u7f6e\u62c5\u5fe7\u65f6\u6bb5\uff0c\u5b58\u5728\u5168\u5929\u53cd\u520d\u98ce\u9669")
    tips.append("\u6bcf\u5468\u56de\u770b\u8bb0\u5f55\u624d\u80fd\u8bc6\u522b\u6a21\u5f0f\uff0c\u53ea\u8bb0\u4e0d\u770b\u6ca1\u6709\u4ef7\u503c")
    tips.append("\u672c\u6280\u80fd\u4e0d\u63d0\u4f9b\u8bca\u65ad\uff0c\u4e0d\u66ff\u4ee3\u4e13\u4e1a\u5fc3\u7406\u6cbb\u7597")
    res["tips"] = tips
    return res


def run_file(path, as_json):
    res = analyze(read_json(path))
    if as_json:
        return json.dumps(res, ensure_ascii=False, indent=2)
    lines = []
    lines.append("\u8bb0\u5f55\u6761\u6570: %d" % res["count"])
    lines.append("\u6c42\u52a9\u7ea2\u7ebf\u547d\u4e2d: %s" % (res["red_lines"] or "\u65e0"))
    t = res["trend"]
    lines.append("\u5f3a\u5ea6\u5747\u503c: %.1f  \u8d8b\u52bf: %s" % (t["avg"], "\u4e0a\u5347" if t["rising"] else "\u5e73\u7a33"))
    lines.append("\u91cd\u590d\u89e6\u53d1\u6e90: %s" % (res["top_trigger"] or "\u65e0"))
    lines.append("\u91cd\u590d\u8eab\u4f53\u53cd\u5e94: %s" % (res["top_body"] or "\u65e0"))
    lines.append("\u91cd\u590d\u60f3\u6cd5: %s" % (res["top_thought"] or "\u65e0"))
    lines.append("\u81ea\u6211\u5ba1\u5224\u8868\u8ff0: %s" % (res["self_critical"] or "\u65e0"))
    lines.append("\u542b\u6b63\u5411\u8bb0\u5f55: %s" % ("\u662f" if res["has_positive"] else "\u5426"))
    lines.append("\u5df2\u8bbe\u62c5\u5fe7\u65f6\u6bb5: %s" % ("\u662f" if res["concern_window"] else "\u5426"))
    for x in res["tips"]:
        lines.append("- %s" % x)
    return "\n".join(lines)


def selftest():
    fails = []

    def ck(name, cond):
        if not cond:
            fails.append(name)

    e1 = [{"trigger": "\u4ed6\u5632\u7b11\u6211", "body": "\u80f8\u95f7", "thought": "\u6211\u679c\u7136\u4e0d\u884c",
           "intensity": 5}]
    e2 = [{"trigger": "\u5435\u67b6", "body": "\u80f8\u95f7", "thought": "\u6211\u53c8\u641e\u7838\u4e86", "intensity": 8}]
    e3 = [{"trigger": "\u666e\u901a\u7684\u4e00\u5929", "body": "\u80a9\u7d27", "thought": "\u8fd8\u597d", "intensity": 4}]

    ck("t1 \u65e0\u7ea2\u7ebf\u65f6\u4e0d\u62a5", check_red_lines(e1) == [])
    crisis = check_red_lines([{"thought": "\u6709\u65f6\u4f1a\u60f3\u81ea\u6740"}])
    ck("t2 \u81ea\u4f24\u4fe1\u53f7\u88ab\u8bc6\u522b", len(crisis) > 0 and crisis[0]["level"] == "\u5371\u673a")
    ck("t3 \u5e7b\u89c9\u4fe1\u53f7\u88ab\u8bc6\u522b", len(check_red_lines([{"behavior": "\u542c\u5230\u5e7b\u89c9\u58f0\u97f3"}])) > 0)
    ck("t4 \u8e81\u72c2\u4fe1\u53f7\u88ab\u8bc6\u522b", len(check_red_lines([{"emotion": "\u5c11\u7761\u5374\u4e0d\u56f0"}])) > 0)
    ck("t5 \u8fdb\u98df\u969c\u788d\u4fe1\u53f7\u88ab\u8bc6\u522b", len(check_red_lines([{"behavior": "\u50ac\u5410"}])) > 0)

    tr = intensity_trend(e1)
    ck("t6 \u5355\u6761\u4e0d\u7b97\u8d8b\u52bf", tr["rising"] is False)
    tr2 = intensity_trend([{"intensity": 3}, {"intensity": 9}])
    ck("t7 \u9012\u589e\u88ab\u8bc6\u522b", tr2["rising"] is True)
    ck("t8 \u5f3a\u5ea6\u5747\u503c\u6b63\u786e", abs(intensity_trend([{"intensity": 4}, {"intensity": 6}])["avg"] - 5.0) < 1e-9)
    ck("t9 \u975e\u6570\u503c\u5f3a\u5ea6\u88ab\u8df3\u8fc7", len(intensity_trend([{"intensity": "x"}, {"intensity": 2}])["values"]) == 1)

    tk, n = top_repeat([e1[0], e2[0]], "body")
    ck("t10 \u91cd\u590d\u9879\u88ab\u8bc6\u522b", n == 2)
    ck("t11 \u7a7a\u5b57\u6bb5\u4e0d\u8ba1\u5165", top_repeat([{"trigger": ""}], "trigger") == ([], 0))

    ck("t12 \u81ea\u6211\u5ba1\u5224\u88ab\u8bc6\u522b", len(check_self_critical([{"thought": "\u6211\u771f\u6ca1\u7528"}])) > 0)
    ck("t13 \u65e0\u81ea\u6211\u5ba1\u5224\u4e0d\u62a5", check_self_critical(e3) == [])
    ck("t14 \u6b63\u5411\u88ab\u8bc6\u522b", check_positive([{"result": "\u4eca\u5929\u5f88\u987a\u5229"}]) is True)
    ck("t15 \u65e0\u6b63\u5411\u4e0d\u62a5", check_positive(e1) is False)

    r = analyze({"entries": [e1[0], e2[0]]})
    ck("t16 \u9012\u589e\u89e6\u53d1\u5efa\u8bae", any("\u9012\u589e" in t for t in r["tips"]))
    ck("t17 \u91cd\u590d\u89e6\u53d1\u63d0\u793a", any("\u91cd\u590d\u89e6\u53d1\u6e90" in t for t in
               analyze({"entries": [e1[0], dict(e1[0]), dict(e1[0])]})["tips"]))
    r2 = analyze({"entries": [{"thought": "\u53c8\u60f3\u81ea\u6740\u4e86"}]})
    ck("t18 \u7ea2\u7ebf\u89e6\u53d1\u8f6c\u4ecb\u63d0\u793a", any("\u8f6c\u4ecb" in t for t in r2["tips"]))
    ck("t19 \u672a\u8bbe\u65f6\u6bb5\u6709\u53cd\u520d\u63d0\u793a", any("\u53cd\u520d" in t for t in analyze({"entries": e1})["tips"]))
    ck("t20 \u7a7a\u8f93\u5165\u4e0d\u62a5\u9519", analyze({})["count"] == 0)

    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_case.json")
    with open(tmp, "w", encoding="utf-8-sig") as f:
        json.dump({"entries": []}, f, ensure_ascii=False)
    ck("t21 BOM \u8f93\u5165\u89e3\u6790\u6210\u529f", isinstance(read_json(tmp)["entries"], list))
    os.remove(tmp)

    ck("t22 \u63d0\u793a\u542b\u4e0d\u66ff\u4ee3\u6cbb\u7597", any("\u4e0d\u66ff\u4ee3\u4e13\u4e1a\u5fc3\u7406\u6cbb\u7597" in t for t in analyze({})["tips"]))
    ck("t23 \u63d0\u793a\u542b\u6bcf\u5468\u56de\u770b", any("\u56de\u770b" in t for t in analyze({})["tips"]))

    out = []
    out.append("SELFTEST FAIL: %s" % "; ".join(fails) if fails else "SELFTEST OK  23/23")
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, RESULT_FILE), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="\u60c5\u7eea\u8bb0\u5f55\u7edf\u8ba1\u4e0e\u7ea2\u7ebf\u63d0\u793a")
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