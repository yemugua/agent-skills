# -*- coding: utf-8 -*-
"""\u6295\u8bc9\u6e20\u9053\u5339\u914d\u4e0e\u6d41\u8f6c\u8def\u5f84\u5efa\u8bae\u3002\u6807\u51c6\u5e93\u3002

\u7528\u6cd5:
  python complaint_channel_router.py --file case.json
  python complaint_channel_router.py --selftest
"""

import argparse
import json
import os
import sys

RESULT_FILE = "_selftest_result.txt"

DOMAIN_CHANNEL = {
    "\u6d88\u8d39": ("12315", ["12345", "\u6d88\u8d39\u8005\u534f\u4f1a"]),
    "\u4ef7\u683c": ("12315", ["12345"]),
    "\u5e7f\u544a": ("12315", ["12345"]),
    "\u5e02\u573a\u4e3b\u4f53": ("12315", ["12345"]),
    "\u7a0e\u52a1": ("\u7a0e\u52a1\u90e8\u95e8", ["12345"]),
    "\u7f51\u7edc": ("\u7f51\u4fe1\u90e8\u95e8", ["12345"]),
    "\u73af\u5883": ("\u751f\u6001\u73af\u5883\u90e8\u95e8", ["12345"]),
    "\u836f\u54c1\u5668\u68b0": ("\u836f\u76d1\u90e8\u95e8", ["12345"]),
    "\u533b\u7597": ("\u536b\u751f\u5065\u5eb7\u90e8\u95e8", ["12345"]),
    "\u5feb\u9012": ("\u90ae\u653f\u4e1a\u7533\u8bc9\u6e20\u9053", ["12315"]),
    "\u52b3\u52a8": ("\u52b3\u52a8\u4fdd\u969c\u76d1\u5bdf", ["12345"]),
}
INTENT_SPLIT = {"\u6295\u8bc9", "\u4e3e\u62a5", "\u8c03\u89e3", "\u8bc9\u8bbc"}
VAGUE_CLAIM = ["\u7ed9\u4e2a\u8bf4\u6cd5", "\u7ed9\u4e2a\u4ea4\u4ee3", "\u6ee1\u610f", "\u5904\u7406\u4e00\u4e0b", "\u7ba1\u7ba1"]
EMOTIONAL = ["\u9a97\u5b50", "\u65e0\u826f", "\u9ed1\u5fc3", "\u592a\u8fc7\u5206", "\u5929\u7406\u96be\u5bb9", "\u5783\u573e"]
REJECT_REASONS = ["\u53d7\u7406\u8303\u56f4\u4e0d\u5bf9", "\u6750\u6599\u4e0d\u5145\u5206", "\u8bc9\u6c42\u4e0d\u660e\u786e", "\u4e0d\u5c5e\u8be5\u673a\u5173\u804c\u8d23"]
ESCALATION = ["\u7ecf\u8425\u8005\u534f\u5546", "\u5bf9\u5e94\u6e20\u9053\u63d0\u4ea4", "\u8981\u6c42\u4e66\u9762\u7b54\u590d", "\u5411\u4e0a\u4e00\u7ea7\u6216\u4e13\u95e8\u673a\u6784\u53cd\u6620",
              "\u7533\u8bf7\u8c03\u89e3", "\u8d70\u53f8\u6cd5\u9014\u5f84"]


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return json.loads(raw.lstrip("\ufeff"))


def pick_domain(data):
    d = str(data.get("domain") or "").strip()
    if d in DOMAIN_CHANNEL:
        return d
    for k in DOMAIN_CHANNEL:
        if k in d:
            return k
    return None


def route(data):
    dom = pick_domain(data)
    if dom is None:
        return {"domain": None, "primary": None, "alternatives": [],
                "tip": "\u95ee\u9898\u9886\u57df\u65e0\u6cd5\u5224\u5b9a\uff0c\u5e94\u5148\u786e\u8ba4\u5c5e\u4e8e\u6d88\u8d39\u7ea0\u7eb7\u8fd8\u662f\u5176\u4ed6\u9886\u57df"}
    primary, alts = DOMAIN_CHANNEL[dom]
    return {"domain": dom, "primary": primary, "alternatives": alts,
            "tip": "12345\u4e3a\u8f6c\u529e\u5165\u53e3\uff0c\u80fd\u76f4\u6295\u4e3b\u7ba1\u90e8\u95e8\u65f6\u4f18\u5148\u76f4\u6295"}


def check_content(data):
    tags = [str(t) for t in (data.get("content_tags") or [])]
    claim = str(data.get("claim") or "")
    vague = [c for c in VAGUE_CLAIM if c in claim or any(c in t for t in tags)]
    emo = [e for e in EMOTIONAL if e in claim or any(e in t for t in tags)]
    res = {"vague_claim": vague, "emotional": emo}
    if emo:
        res["tip"] = "\u542b\u60c5\u7eea\u5316\u8868\u8ff0\uff0c\u5904\u7406\u4eba\u5458\u4f1a\u4f18\u5148\u8df3\u8fc7\u5b9e\u8d28\u8bc9\u6c42"
    elif vague:
        res["tip"] = "\u8bc9\u6c42\u7b3c\u7edf\uff0c\u5e94\u6539\u5199\u4e3a\u660e\u786e\u53ef\u6267\u884c\u7684\u8bc9\u6c42"
    else:
        res["tip"] = "\u5185\u5bb9\u5e94\u53ea\u5199\u53ef\u6838\u67e5\u4e8b\u5b9e\uff0c\u8bc9\u6c42\u660e\u786e\u53ef\u6267\u884c"
    return res


def escalation_advice(rejected):
    """\u4f9d\u636e\u5df2\u9000\u56de\u60c5\u51b5\u7ed9\u5347\u7ea7\u5efa\u8bae\u3002"""
    idx = -1
    reasons = []
    for r in (rejected or []):
        if r in REJECT_REASONS:
            reasons.append(r)
        elif r in ESCALATION:
            idx = max(idx, ESCALATION.index(r))
    next_step = ESCALATION[min(idx + 1, len(ESCALATION) - 1)] if idx < len(ESCALATION) - 1 else None
    return {"reject_reasons": reasons, "next": next_step,
            "tip": "\u5347\u7ea7\u524d\u987b\u786e\u8ba4\u524d\u5e8f\u5df2\u8d70\u5b8c\u4e14\u7559\u75d5"}


def analyze(data):
    r = route(data)
    intent = str(data.get("intent") or "").strip()
    res = {
        "route": r,
        "intent": intent,
        "intent_valid": intent in INTENT_SPLIT,
        "content": check_content(data),
        "escalation": escalation_advice(data.get("rejected_before")),
    }
    tips = [r["tip"], res["content"]["tip"]]
    if intent == "\u4e3e\u62a5":
        tips.append("\u4e3e\u62a5\u7ed3\u679c\u4e0d\u5fc5\u7136\u5e26\u6765\u4e2a\u4eba\u8d54\u4ed8\uff0c\u89e3\u51b3\u7ea0\u7eb7\u5e94\u53e6\u8d70\u6295\u8bc9")
    if intent == "\u6295\u8bc9":
        tips.append("\u6295\u8bc9\u4e0e\u4e3e\u62a5\u76ee\u7684\u4e0d\u540c\uff0c\u53ef\u5206\u5f00\u63d0\u4ea4")
    if not res["intent_valid"]:
        tips.append("\u8bc9\u6c42\u7c7b\u578b\u5e94\u660e\u786e\u4e3a\u6295\u8bc9\u3001\u4e3e\u62a5\u3001\u8c03\u89e3\u6216\u8bc9\u8bbc")
    tips.append("\u63d0\u4ea4\u540e\u4e3b\u52a8\u67e5\u8be2\u662f\u5426\u53d7\u7406\uff0c\u5df2\u63d0\u4ea4\u4e0d\u7b49\u4e8e\u5df2\u53d7\u7406")
    tips.append("\u53d7\u7406\u8303\u56f4\u4e0e\u529e\u7406\u65f6\u9650\u4ee5\u73b0\u884c\u89c4\u5b9a\u548c\u53d7\u7406\u673a\u6784\u53e3\u5f84\u4e3a\u51c6")
    res["tips"] = tips
    return res


def run_file(path, as_json):
    res = analyze(read_json(path))
    if as_json:
        return json.dumps(res, ensure_ascii=False, indent=2)
    lines = []
    r = res["route"]
    lines.append("\u95ee\u9898\u9886\u57df: %s" % (r["domain"] or "\u65e0\u6cd5\u5224\u5b9a"))
    lines.append("\u63a8\u8350\u6e20\u9053: %s" % (r["primary"] or "\u9700\u5148\u786e\u8ba4\u9886\u57df"))
    lines.append("\u5907\u9009\u6e20\u9053: %s" % (", ".join(r["alternatives"]) or "\u65e0"))
    lines.append("\u8bc9\u6c42\u7c7b\u578b: %s  \u5408\u6cd5\u7c7b\u578b: %s" % (res["intent"] or "\u672a\u586b",
                                          "\u662f" if res["intent_valid"] else "\u5426"))
    c = res["content"]
    lines.append("\u8bc9\u6c42\u7b3c\u7edf: %s" % (c["vague_claim"] or "\u65e0"))
    lines.append("\u60c5\u7eea\u5316\u8868\u8ff0: %s" % (c["emotional"] or "\u65e0"))
    e = res["escalation"]
    lines.append("\u5df2\u9000\u56de\u539f\u56e0: %s" % (e["reject_reasons"] or "\u65e0"))
    lines.append("\u5efa\u8bae\u4e0b\u4e00\u6b65: %s" % (e["next"] or "\u8def\u5f84\u5df2\u5230\u672b\u7aef\u6216\u9700\u4eba\u5de5\u5224\u65ad"))
    for t in res["tips"]:
        lines.append("- %s" % t)
    return "\n".join(lines)


def selftest():
    fails = []

    def ck(name, cond):
        if not cond:
            fails.append(name)

    ck("t1 \u6d88\u8d39\u57df\u8def\u7531\u6b63\u786e", route({"domain": "\u6d88\u8d39"})["primary"] == "12315")
    ck("t2 \u7a0e\u52a1\u57df\u8def\u7531\u6b63\u786e", route({"domain": "\u7a0e\u52a1"})["primary"] == "\u7a0e\u52a1\u90e8\u95e8")
    ck("t3 \u5feb\u9012\u57df\u8def\u7531\u6b63\u786e", route({"domain": "\u5feb\u9012"})["primary"] == "\u90ae\u653f\u4e1a\u7533\u8bc9\u6e20\u9053")
    ck("t4 \u6a21\u7cca\u5339\u914d", route({"domain": "\u7f51\u7edc\u8fdd\u6cd5"})["domain"] == "\u7f51\u7edc")
    ck("t5 \u65e0\u6cd5\u5224\u5b9a\u4e0d\u62a5\u9519", route({"domain": "xyz"})["primary"] is None)

    ck("t6 \u6d88\u8d39\u57df\u6709\u5907\u9009", len(route({"domain": "\u6d88\u8d39"})["alternatives"]) > 0)

    cc = check_content({"claim": "\u5546\u5bb6\u592a\u8fc7\u5206"})
    ck("t7 \u60c5\u7eea\u5316\u88ab\u8bc6\u522b", len(cc["emotional"]) > 0)
    cv = check_content({"claim": "\u7ed9\u4e2a\u8bf4\u6cd5"})
    ck("t8 \u7b3c\u7edf\u8bc9\u6c42\u88ab\u8bc6\u522b", len(cv["vague_claim"]) > 0)
    ck("t9 \u6b63\u5e38\u5185\u5bb9\u65e0\u63d0\u793a", "\u65e0" not in check_content({"claim": "\u8981\u6c42\u9000\u8d27\u9000\u6b3e\u5e76\u8d54\u507f\u5dee\u989d"})["tip"])

    e1 = escalation_advice(["\u5bf9\u5e94\u6e20\u9053\u63d0\u4ea4"])
    ck("t10 \u5347\u7ea7\u8def\u5f84\u9012\u8fdb", e1["next"] == "\u8981\u6c42\u4e66\u9762\u7b54\u590d")
    e2 = escalation_advice([])
    ck("t11 \u7a7a\u8def\u5f84\u4ece\u8d77\u6b65", e2["next"] == "\u7ecf\u8425\u8005\u534f\u5546")
    e3 = escalation_advice(list(ESCALATION))
    ck("t12 \u8d70\u5b8c\u5230\u672b\u7aef", e3["next"] is None)
    ck("t13 \u9000\u56de\u539f\u56e0\u88ab\u8bc6\u522b", escalation_advice(["\u53d7\u7406\u8303\u56f4\u4e0d\u5bf9"])["reject_reasons"] == ["\u53d7\u7406\u8303\u56f4\u4e0d\u5bf9"])
    ck("t14 \u5347\u7ea7\u63d0\u793a\u542b\u7559\u75d5", "\u7559\u75d5" in escalation_advice([])["tip"])

    r1 = analyze({"domain": "\u6d88\u8d39", "intent": "\u4e3e\u62a5"})
    ck("t15 \u4e3e\u62a5\u63d0\u793a\u4e0d\u542b\u8d54\u4ed8", any("\u4e0d\u5fc5\u7136" in t for t in r1["tips"]))
    r2 = analyze({"domain": "\u6d88\u8d39", "intent": "\u6295\u8bc9"})
    ck("t16 \u6295\u8bc9\u63d0\u793a\u53ef\u5206\u5f00\u63d0\u4ea4", any("\u5206\u5f00\u63d0\u4ea4" in t for t in r2["tips"]))
    ck("t17 \u975e\u6cd5\u610f\u56fe\u88ab\u62a5", analyze({"domain": "\u6d88\u8d39", "intent": "\u80e1\u95f9"})["intent_valid"] is False)
    ck("t18 \u7a7a\u8f93\u5165\u4e0d\u62a5\u9519", analyze({})["route"]["primary"] is None)

    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_case.json")
    with open(tmp, "w", encoding="utf-8-sig") as f:
        json.dump({"domain": "\u6d88\u8d39"}, f, ensure_ascii=False)
    ck("t19 BOM \u8f93\u5165\u89e3\u6790\u6210\u529f", read_json(tmp)["domain"] == "\u6d88\u8d39")
    os.remove(tmp)

    ck("t20 \u9886\u57df\u8868\u8986\u76d6\u5168\u90e8\u952e", len(DOMAIN_CHANNEL) >= 10)
    ck("t21 \u63d0\u793a\u542b\u65f6\u9650\u53e3\u5f84", any("\u53d7\u7406\u673a\u6784" in t for t in analyze({})["tips"]))
    ck("t22 \u8bc9\u6c42\u7c7b\u578b\u8868\u5b8c\u6574", INTENT_SPLIT == {"\u6295\u8bc9", "\u4e3e\u62a5", "\u8c03\u89e3", "\u8bc9\u8bbc"})

    out = []
    out.append("SELFTEST FAIL: %s" % "; ".join(fails) if fails else "SELFTEST OK  22/22")
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, RESULT_FILE), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="\u6295\u8bc9\u6e20\u9053\u5339\u914d\u4e0e\u6d41\u8f6c\u5efa\u8bae")
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