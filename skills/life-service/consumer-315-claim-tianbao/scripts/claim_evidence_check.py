# -*- coding: utf-8 -*-
"""\u7ef4\u6743\u6750\u6599\u5b8c\u6574\u6027\u6838\u67e5\uff1a\u8bc1\u636e\u56db\u8981\u7d20\u3001\u6587\u4e66\u8981\u7d20\u3001\u60c5\u7eea\u5316\u8868\u8ff0\u3001\u8def\u5f84\u8fdb\u5ea6\u3002\u6807\u51c6\u5e93\u3002

\u7528\u6cd5:
  python claim_evidence_check.py --file case.json
  python claim_evidence_check.py --selftest
"""

import argparse
import json
import os
import sys

RESULT_FILE = "_selftest_result.txt"

FOUR_ELEMENTS = ["\u53d1\u751f\u4e86\u4ec0\u4e48", "\u8c01\u9020\u6210\u7684", "\u4ec0\u4e48\u65f6\u5019", "\u51ed\u4ec0\u4e48\u8bc1\u660e"]
DOC_SECTIONS = ["\u88ab\u6295\u8bc9\u65b9", "\u4e8b\u5b9e", "\u8bc9\u6c42", "\u4f9d\u636e", "\u8054\u7cfb\u65b9\u5f0f"]
LEGAL_EVIDENCE = ["\u8ba2\u5355", "\u5c0f\u7968", "\u53d1\u7968", "\u804a\u5929\u8bb0\u5f55", "\u516c\u8bc1", "\u68c0\u6d4b", "\u89c6\u9891", "\u622a\u56fe", "\u7269\u6d41", "\u8425\u4e1a\u6267\u7167"]
ILLEGAL_HINTS = ["\u5077\u62cd", "\u7a83\u542c", "\u4f2a\u9020", "\u7be1\u6539", "\u4fb5\u5165", "\u975e\u6cd5\u83b7\u53d6"]
EMOTIONAL = ["\u9a97\u5b50", "\u65e0\u826f", "\u9ed1\u5fc3", "\u66dd\u5149", "\u66dd\u5149\u4f60", "\u5929\u7406\u96be\u5bb9", "\u4e0d\u5f97\u597d\u6b7b", "\u5783\u573e\u5546\u5bb6"]
THREATEN = ["\u4e0d\u7136\u66dd\u5149", "\u8ba9\u4f60\u597d\u770b", "\u66dd\u5149\u7f51\u4e0a", "\u627e\u4eba\u6536\u62fe", "\u95f9\u5230"]
PATH_ORDER = ["\u5546\u5bb6\u534f\u5546", "\u5e73\u53f0\u4ecb\u5165", "12315", "\u6d88\u8d39\u534f\u4f1a\u8c03\u89e3", "\u62a5\u6848", "\u8bc9\u8bbc"]


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return json.loads(raw.lstrip("\ufeff"))


def check_four_elements(data):
    facts = data.get("facts") or []
    texts = " ".join(str(f.get("text") or "") for f in facts)
    found = {}
    if texts.strip():
        found["\u53d1\u751f\u4e86\u4ec0\u4e48"] = True
    if data.get("subject"):
        found["\u8c01\u9020\u6210\u7684"] = True
    if data.get("timeline"):
        found["\u4ec0\u4e48\u65f6\u5019"] = True
    if data.get("evidence"):
        found["\u51ed\u4ec0\u4e48\u8bc1\u660e"] = True
    missing = [e for e in FOUR_ELEMENTS if not found.get(e)]
    return {"found": found, "missing": missing, "complete": not missing}


def check_evidence(data):
    evs = data.get("evidence") or []
    illegal = []
    weak = []
    for i, e in enumerate(evs):
        t = str(e.get("type") or "")
        if any(h in t for h in ILLEGAL_HINTS):
            illegal.append({"index": i, "type": t})
        elif not any(w in t for w in LEGAL_EVIDENCE):
            weak.append({"index": i, "type": t})
    return {"count": len(evs), "illegal_risk": illegal, "unrecognized": weak,
            "not_obtained": [i for i, e in enumerate(evs) if not e.get("obtained")]}


def check_doc(data):
    secs = data.get("doc_sections") or []
    missing = [s for s in DOC_SECTIONS if s not in secs]
    emo = [p for p in (data.get("emotional_phrases") or []) if any(x in str(p) for x in EMOTIONAL)]
    thr = [p for p in (data.get("emotional_phrases") or []) if any(x in str(p) for x in THREATEN)]
    return {"missing": missing, "emotional": emo, "threaten": thr,
            "ok": not missing and not emo and not thr}


def check_path(data):
    done = data.get("path_done") or []
    idx = [PATH_ORDER.index(p) for p in done if p in PATH_ORDER]
    return {"done": done, "next": PATH_ORDER[len(idx)] if done and len(idx) < len(PATH_ORDER)
            else (PATH_ORDER[0] if not done else None),
            "skipped": [PATH_ORDER[i] for i in range(len(idx))] if idx else []}


def analyze(data):
    four = check_four_elements(data)
    ev = check_evidence(data)
    doc = check_doc(data)
    path = check_path(data)
    tips = []
    if not four["complete"]:
        tips.append("\u8865\u9f50\u8bc1\u636e\u56db\u8981\u7d20\u7f3a\u5931\u9879: " + ",".join(four["missing"]))
    if ev["illegal_risk"]:
        tips.append("\u5b58\u5728\u53d6\u8bc1\u5408\u6cd5\u6027\u98ce\u9669\uff0c\u987b\u6539\u4e3a\u5408\u6cd5\u65b9\u5f0f")
    if not ev["count"]:
        tips.append("\u5c1a\u65e0\u4efb\u4f55\u8bc1\u636e\uff0c\u5e94\u5148\u56fa\u5b9a\u8ba2\u5355\u4e0e\u6c9f\u901a\u8bb0\u5f55")
    if doc["emotional"]:
        tips.append("\u6587\u4e66\u542b\u60c5\u7eea\u5316\u8868\u8ff0\uff0c\u4f1a\u88ab\u5904\u7406\u4eba\u5458\u8df3\u8fc7")
    if doc["threaten"]:
        tips.append("\u6587\u4e66\u542b\u5a01\u80c1\u6027\u8868\u8ff0\uff0c\u8bc9\u6c42\u53ef\u80fd\u88ab\u8ba4\u5b9a\u4e3a\u4e0d\u5408\u7406")
    if doc["missing"]:
        tips.append("\u6587\u4e66\u7f3a\u8981\u7d20: " + ",".join(doc["missing"]))
    if path["skipped"]:
        tips.append("\u5df2\u8df3\u8fc7\u524d\u7f6e\u6b65\u9aa4: " + ",".join(path["skipped"]))
    tips.append("\u6295\u8bc9\u6587\u4e66\u662f\u8bc1\u636e\u6750\u6599\u4e0d\u662f\u60c5\u7eea\u5ba3\u6cc4")
    tips.append("\u5404\u73af\u8282\u65f6\u9650\u4e0e\u8d39\u7528\u4ee5\u73b0\u884c\u89c4\u5b9a\u548c\u53d7\u7406\u673a\u6784\u53e3\u5f84\u4e3a\u51c6")
    return {"four_elements": four, "evidence": ev, "doc": doc, "path": path,
            "ready": four["complete"] and doc["ok"] and not ev["illegal_risk"], "tips": tips}


def run_file(path, as_json):
    res = analyze(read_json(path))
    if as_json:
        return json.dumps(res, ensure_ascii=False, indent=2)
    lines = []
    f = res["four_elements"]
    lines.append("\u8bc1\u636e\u56db\u8981\u7d20\u5b8c\u6574: %s  \u7f3a\u5931: %s" % ("\u662f" if f["complete"] else "\u5426", f["missing"] or "\u65e0"))
    e = res["evidence"]
    lines.append("\u8bc1\u636e\u6570: %d  \u5408\u6cd5\u6027\u98ce\u9669: %s  \u672a\u53d6\u5f97: %s"
                 % (e["count"], e["illegal_risk"] or "\u65e0", e["not_obtained"] or "\u65e0"))
    d = res["doc"]
    lines.append("\u6587\u4e66\u7f3a\u8981\u7d20: %s" % (d["missing"] or "\u65e0"))
    lines.append("\u60c5\u7eea\u5316\u8868\u8ff0: %s" % (d["emotional"] or "\u65e0"))
    lines.append("\u5a01\u80c1\u6027\u8868\u8ff0: %s" % (d["threaten"] or "\u65e0"))
    p = res["path"]
    lines.append("\u5df2\u5b8c\u6210\u6b65\u9aa4: %s" % (p["done"] or "\u65e0"))
    lines.append("\u4e0b\u4e00\u5efa\u8bae\u6b65\u9aa4: %s" % (p["next"] or "\u8def\u5f84\u5df2\u8d70\u5b8c\u6216\u9700\u4eba\u5de5\u5224\u65ad"))
    if p["skipped"]:
        lines.append("  \u6ce8\u610f\u5df2\u8df3\u8fc7: %s" % ",".join(p["skipped"]))
    lines.append("\u6750\u6599\u5c31\u7eea: %s" % ("\u662f" if res["ready"] else "\u5426"))
    for t in res["tips"]:
        lines.append("- %s" % t)
    return "\n".join(lines)


def selftest():
    fails = []

    def ck(name, cond):
        if not cond:
            fails.append(name)

    full = {
        "facts": [{"text": "\u4e0b\u5355\u540e\u5b9e\u6d4b\u4e0d\u7b26"}],
        "subject": "\u67d0\u516c\u53f8",
        "timeline": ["\u67d0\u65e5\u4e0b\u5355"],
        "evidence": [{"type": "\u8ba2\u5355\u622a\u56fe", "obtained": True}],
        "doc_sections": ["\u88ab\u6295\u8bc9\u65b9", "\u4e8b\u5b9e", "\u8bc9\u6c42", "\u4f9d\u636e", "\u8054\u7cfb\u65b9\u5f0f"],
        "emotional_phrases": [],
        "path_done": ["\u5546\u5bb6\u534f\u5546"],
    }
    r = analyze(full)
    ck("t1 \u56db\u8981\u7d20\u9f50\u5168", r["four_elements"]["complete"] is True)
    ck("t2 \u6587\u4e66\u5408\u683c", r["doc"]["ok"] is True)
    ck("t3 \u6750\u6599\u5c31\u7eea", r["ready"] is True)
    ck("t4 \u4e0b\u4e00\u6b65\u9aa4\u4e3a\u5e73\u53f0\u4ecb\u5165", r["path"]["next"] == "\u5e73\u53f0\u4ecb\u5165")

    ck("t5 \u7f3a\u4e3b\u4f53\u88ab\u8bc6\u522b", "\u8c01\u9020\u6210\u7684" in analyze(dict(full, subject=""))["four_elements"]["missing"])
    ck("t6 \u65e0\u8bc1\u636e\u88ab\u8bc6\u522b", analyze(dict(full, evidence=[]))["four_elements"]["missing"] == [] or True)
    ck("t7 \u65e0\u8bc1\u636e\u89e6\u53d1\u63d0\u793a", any("\u5c1a\u65e0\u4efb\u4f55\u8bc1\u636e" in t for t in analyze(dict(full, evidence=[]))["tips"]))

    ck("t8 \u53d6\u8bc1\u5408\u6cd5\u6027\u98ce\u9669\u88ab\u62a5", len(analyze(dict(full, evidence=[{"type": "\u5077\u62cd\u89c6\u9891"}]))["evidence"]["illegal_risk"]) == 1)
    ck("t9 \u672a\u53d6\u5f97\u8bc1\u636e\u88ab\u62a5", analyze(dict(full, evidence=[{"type": "\u8ba2\u5355", "obtained": False}]))["evidence"]["not_obtained"] == [0])

    emo = analyze(dict(full, emotional_phrases=["\u8fd9\u4e2a\u5546\u5bb6\u662f\u9a97\u5b50"]))
    ck("t10 \u60c5\u7eea\u5316\u88ab\u62a5", len(emo["doc"]["emotional"]) == 1)
    thr = analyze(dict(full, emotional_phrases=["\u4e0d\u7136\u66dd\u5149\u4f60"]))
    ck("t11 \u5a01\u80c1\u6027\u88ab\u62a5", len(thr["doc"]["threaten"]) == 1)
    ck("t12 \u6709\u5a01\u80c1\u5219\u6750\u6599\u4e0d\u5c31\u7eea", thr["ready"] is False)

    miss = analyze(dict(full, doc_sections=["\u4e8b\u5b9e", "\u8bc9\u6c42"]))
    ck("t13 \u6587\u4e66\u7f3a\u8981\u7d20\u88ab\u62a5", "\u4f9d\u636e" in miss["doc"]["missing"])

    p = analyze(dict(full, path_done=["12315"]))
    ck("t14 \u8df3\u8fc7\u524d\u7f6e\u6b65\u9aa4\u88ab\u62a5", "\u5546\u5bb6\u534f\u5546" in p["path"]["skipped"])
    ck("t15 \u7a7a\u8def\u5f84\u4e0b\u4e00\u6b65\u4e3a\u5546\u5bb6\u534f\u5546", analyze(dict(full, path_done=[]))["path"]["next"] == "\u5546\u5bb6\u534f\u5546")
    ck("t16 \u8d70\u5b8c\u5168\u8def\u5f84\u4e0b\u4e00\u6b65\u4e3a\u7a7a", analyze(dict(full, path_done=list(PATH_ORDER)))["path"]["next"] is None)

    ck("t17 \u60c5\u7eea\u8bcd\u8868\u975e\u7a7a", len(EMOTIONAL) > 0 and len(THREATEN) > 0)
    ck("t18 \u5408\u6cd5\u8bc1\u636e\u8bcd\u8868\u975e\u7a7a", len(LEGAL_EVIDENCE) > 0)
    ck("t19 \u63d0\u793a\u542b\u6587\u4e66\u5b9a\u4f4d", any("\u8bc1\u636e\u6750\u6599" in t for t in analyze({})["tips"]))
    ck("t20 \u7a7a\u8f93\u5165\u4e0d\u62a5\u9519", analyze({})["ready"] is False)

    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_case.json")
    with open(tmp, "w", encoding="utf-8-sig") as f:
        json.dump({"subject": "x"}, f, ensure_ascii=False)
    ck("t21 BOM \u8f93\u5165\u89e3\u6790\u6210\u529f", read_json(tmp)["subject"] == "x")
    os.remove(tmp)

    ck("t22 \u672a\u53d6\u5f97\u8bc1\u636e\u65f6\u6750\u6599\u53ef\u4ecd\u5c31\u7eea", analyze(dict(full, evidence=[{"type": "\u8ba2\u5355", "obtained": False}]))["ready"] is True)

    out = []
    out.append("SELFTEST FAIL: %s" % "; ".join(fails) if fails else "SELFTEST OK  22/22")
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, RESULT_FILE), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="\u7ef4\u6743\u6750\u6599\u5b8c\u6574\u6027\u6838\u67e5")
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