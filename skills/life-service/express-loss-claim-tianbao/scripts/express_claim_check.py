# -*- coding: utf-8 -*-
"""\u5feb\u9012\u7406\u8d54\u6750\u6599\u5b8c\u6574\u6027\u4e0e\u8def\u5f84\u6838\u67e5\u3002\u6807\u51c6\u5e93\u3002

\u7528\u6cd5:
  python express_claim_check.py --file claim.json
  python express_claim_check.py --selftest
"""

import argparse
import json
import os
import sys

RESULT_FILE = "_selftest_result.txt"

CORE_EVIDENCE = ["\u9762\u5355", "\u7269\u6d41\u8f68\u8ff9"]
HIGH_EVIDENCE = ["\u9762\u5355", "\u7269\u6d41\u8f68\u8ff9", "\u7b7e\u6536\u8bb0\u5f55"]
VALUE_EVIDENCE = ["\u8ba2\u5355", "\u53d1\u7968", "\u4ed8\u6b3e\u51ed\u8bc1", "\u6e05\u5355", "\u5bc4\u4ef6\u6e05\u5355"]
ESCALATION = ["\u627f\u8fd0\u65b9\u5ba2\u670d", "\u627f\u8fd0\u65b9\u7533\u8bc9\u590d\u6838", "\u90ae\u653f\u4e1a\u7533\u8bc9\u6e20\u9053",
              "12345\u4fbf\u6c11\u70ed\u7ebf", "\u76d1\u7ba1\u4e0e\u6d88\u534f\u8c03\u89e3", "\u53f8\u6cd5\u9014\u5f84"]


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return json.loads(raw.lstrip("\ufeff"))


def classify_case(case_type, opened_before_sign):
    if case_type == "damaged":
        note = "\u7834\u635f\u7c7b\uff1a\u4e3e\u8bc1\u6838\u5fc3\u662f\u8bc1\u660e\u9001\u8fbe\u65f6\u5373\u4e3a\u635f\u574f\uff0c\u5f00\u7bb1\u89c6\u9891\u6700\u5173\u952e"
        need = HIGH_EVIDENCE + ["\u5f00\u7bb1\u89c6\u9891"]
    else:
        note = "\u4e22\u4ef6\u7c7b\uff1a\u4e3e\u8bc1\u6838\u5fc3\u662f\u8bc1\u660e\u5df2\u5bc4\u51fa\u4e14\u5e94\u5230\u8fbe\uff0c\u8f68\u8ff9\u4e2d\u65ad\u662f\u5173\u952e\u8bc1\u636e"
        need = HIGH_EVIDENCE
    if case_type == "damaged" and not opened_before_sign:
        note += "\uff1b\u672a\u5148\u9a8c\u540e\u7b7e\u65f6\u9001\u8fbe\u65f6\u72b6\u6001\u96be\u4ee5\u8bc1\u660e\uff0c\u4e3e\u8bc1\u96be\u5ea6\u663e\u8457\u589e\u52a0"
    return {"type": case_type, "needed": need, "note": note}


def check_evidence(ev_list, needed):
    evs = [str(e) for e in (ev_list or [])]
    missing = [n for n in needed if not any(n in e for e in evs)]
    has_core = all(any(c in e for e in evs) for c in CORE_EVIDENCE)
    has_value = any(any(v in e for v in VALUE_EVIDENCE) for e in evs)
    return {"count": len(evs), "missing_core": missing, "core_ok": has_core,
            "value_ok": has_value}


def insured_note(insured):
    if insured:
        return "\u5df2\u4fdd\u4ef7\uff1a\u6309\u4fdd\u4ef7\u7ea6\u5b9a\u4e0e\u5b9e\u9645\u635f\u5931\u8d54\u4ed8\uff0c\u9650\u989d\u4ee5\u7ea6\u5b9a\u4e3a\u51c6"
    return "\u672a\u4fdd\u4ef7\uff1a\u4f9d\u627f\u8fd0\u65b9\u8d54\u4ed8\u89c4\u5219\uff0c\u901a\u5e38\u6709\u8f83\u9ad8\u9650\u989d\u4e14\u8d54\u4ed8\u53ef\u80fd\u660e\u663e\u4f4e\u4e8e\u5b9e\u9645\u4ef7\u503c\uff0c\u9ad8\u4ef7\u503c\u7269\u54c1\u5e94\u8003\u8651\u4fdd\u4ef7"


def next_escalation(done):
    if not done:
        return ESCALATION[0]
    idx = -1
    for i, s in enumerate(done):
        if s in ESCALATION:
            idx = max(idx, i)
    return ESCALATION[idx + 1] if idx + 1 < len(ESCALATION) else None


def analyze(data):
    ct = str(data.get("case_type") or "lost").strip()
    ev = data.get("evidence") or []
    cls = classify_case(ct, bool(data.get("opened_before_sign")))
    res = {
        "case": cls,
        "evidence": check_evidence(ev, cls["needed"]),
        "insured_note": insured_note(bool(data.get("insured"))),
        "signed": bool(data.get("signed")),
        "next_step": next_escalation(data.get("escalation_done")),
    }
    tips = []
    if not res["evidence"]["core_ok"]:
        tips.append("\u7f3a\u5c11\u9762\u5355\u6216\u7269\u6d41\u8f68\u8ff9\uff0c\u65e0\u6cd5\u652f\u6491\u4e3b\u5f20\uff0c\u987b\u5c3d\u5feb\u8865\u9f50")
    if not res["evidence"]["value_ok"]:
        tips.append("\u7f3a\u5c11\u4ef7\u503c\u8bc1\u660e\u6750\u6599\uff0c\u8d54\u4ed8\u91d1\u989d\u96be\u4ee5\u786e\u5b9a")
    if ct == "damaged" and not data.get("opened_before_sign"):
        tips.append("\u7834\u635f\u7c7b\u672a\u5148\u9a8c\u540e\u7b7e\uff0c\u9001\u8fbe\u65f6\u72b6\u6001\u96be\u4ee5\u8bc1\u660e")
    tips.append("\u7b7e\u6536\u4ec5\u8bc1\u660e\u6536\u5230\uff0c\u4e0d\u8bc1\u660e\u5b8c\u597d\uff0c\u5b8c\u597d\u4e3e\u8bc1\u8d23\u4efb\u5728\u627f\u8fd0\u65b9")
    tips.append("\u4e0d\u8981\u56e0\u7b49\u5f85\u8c03\u67e5\u7ed3\u679c\u800c\u62d6\u5ef6\u6b63\u5f0f\u63d0\u4ea4\u7406\u8d54\u7533\u8bf7")
    tips.append("\u8d54\u4ed8\u91d1\u989d\u6d4b\u7b97\u5c5e\u6d4b\u7b97\u7c7b\u6280\u80fd\u8303\u56f4\uff0c\u672c\u6280\u80fd\u4e0d\u505a\u91d1\u989d\u6838\u7b97")
    tips.append("\u7406\u8d54\u65f6\u9650\u4e0e\u8d54\u4ed8\u6807\u51c6\u4ee5\u73b0\u884c\u89c4\u5b9a\u548c\u627f\u8fd0\u65b9\u53e3\u5f84\u4e3a\u51c6")
    res["tips"] = tips
    return res


def run_file(path, as_json):
    res = analyze(read_json(path))
    if as_json:
        return json.dumps(res, ensure_ascii=False, indent=2)
    lines = []
    c = res["case"]
    lines.append("\u60c5\u5f62: %s" % c["type"])
    lines.append("  %s" % c["note"])
    e = res["evidence"]
    lines.append("\u8bc1\u636e\u6570: %d  \u6838\u5fc3\u8bc1\u636e\u9f50\u5168: %s  \u7f3a\u5931: %s"
                 % (e["count"], "\u662f" if e["core_ok"] else "\u5426", e["missing_core"] or "\u65e0"))
    lines.append("\u4ef7\u503c\u8bc1\u660e: %s" % ("\u6709" if e["value_ok"] else "\u65e0"))
    lines.append("\u4fdd\u4ef7\u60c5\u51b5: %s" % res["insured_note"])
    lines.append("\u662f\u5426\u5df2\u7b7e\u6536: %s" % ("\u662f" if res["signed"] else "\u5426"))
    lines.append("\u5efa\u8bae\u4e0b\u4e00\u6e20\u9053: %s" % (res["next_step"] or "\u8def\u5f84\u5df2\u5230\u672b\u7aef\u6216\u9700\u4eba\u5de5\u5224\u65ad"))
    for t in res["tips"]:
        lines.append("- %s" % t)
    return "\n".join(lines)


def selftest():
    fails = []

    def ck(name, cond):
        if not cond:
            fails.append(name)

    l = classify_case("lost", False)
    d = classify_case("damaged", True)
    ck("t1 \u4e22\u4ef6\u5f52\u7c7b\u6b63\u786e", l["type"] == "lost")
    ck("t2 \u7834\u635f\u5f52\u7c7b\u6b63\u786e", d["type"] == "damaged")
    ck("t3 \u7834\u635f\u7c7b\u8981\u6c42\u5f00\u7bb1\u89c6\u9891", "\u5f00\u7bb1\u89c6\u9891" in d["needed"])
    ck("t4 \u672a\u5148\u9a8c\u540e\u7b7e\u63d0\u793a\u96be\u5ea6", "\u96be\u5ea6" in classify_case("damaged", False)["note"])
    ck("t5 \u5148\u9a8c\u540e\u7b7e\u65e0\u96be\u5ea6\u63d0\u793a", "\u96be\u5ea6" not in d["note"])

    full = check_evidence(["\u5feb\u9012\u9762\u5355", "\u7269\u6d41\u8f68\u8ff9\u622a\u56fe", "\u7b7e\u6536\u8bb0\u5f55", "\u8ba2\u5355"], HIGH_EVIDENCE)
    ck("t6 \u6838\u5fc3\u8bc1\u636e\u9f50\u5168", full["core_ok"] is True)
    ck("t7 \u4ef7\u503c\u8bc1\u660e\u88ab\u8bc6\u522b", full["value_ok"] is True)
    poor = check_evidence(["\u804a\u5929\u8bb0\u5f55"], HIGH_EVIDENCE)
    ck("t8 \u7f3a\u6838\u5fc3\u88ab\u8bc6\u522b", poor["core_ok"] is False)
    ck("t9 \u7f3a\u5931\u9879\u88ab\u5217\u51fa", len(poor["missing_core"]) > 0)

    ck("t10 \u4fdd\u4ef7\u8bf4\u660e\u6307\u5411\u7ea6\u5b9a", "\u4fdd\u4ef7\u7ea6\u5b9a" in insured_note(True))
    ck("t11 \u672a\u4fdd\u4ef7\u63d0\u793a\u9650\u989d", "\u9650\u989d" in insured_note(False))

    ck("t12 \u7a7a\u5347\u7ea7\u8def\u5f84\u4ece\u8d77\u6b65", next_escalation([]) == ESCALATION[0])
    ck("t13 \u5347\u7ea7\u9012\u8fdb", next_escalation(["\u627f\u8fd0\u65b9\u5ba2\u670d"]) == ESCALATION[1])
    ck("t14 \u8d70\u5b8c\u5230\u672b\u7aef", next_escalation(list(ESCALATION)) is None)
    ck("t15 \u65e0\u6548\u9879\u4e0d\u5f71\u54cd", next_escalation(["xyz"]) == ESCALATION[0])

    r = analyze({"case_type": "damaged", "opened_before_sign": False,
                 "evidence": ["\u5feb\u9012\u9762\u5355"]})
    ck("t16 \u7834\u635f\u672a\u5148\u9a8c\u6709\u63d0\u793a", any("\u5148\u9a8c\u540e\u7b7e" in t for t in r["tips"]))
    ck("t17 \u7f3a\u6838\u5fc3\u6709\u63d0\u793a", any("\u9762\u5355" in t for t in r["tips"]))
    r2 = analyze({"case_type": "lost", "evidence": ["\u9762\u5355", "\u7269\u6d41\u8f68\u8ff9", "\u8ba2\u5355"]})
    ck("t18 \u4e22\u4ef6\u9f50\u5168\u65e0\u6838\u5fc3\u63d0\u793a", not any("\u65e0\u6cd5\u652f\u6491" in t for t in r2["tips"]))
    ck("t19 \u63d0\u793a\u542b\u7b7e\u6536\u4e3e\u8bc1\u8d23\u4efb", any("\u5b8c\u597d\u4e3e\u8bc1\u8d23\u4efb\u5728\u627f\u8fd0\u65b9" in t for t in analyze({})["tips"]))
    ck("t20 \u7a7a\u8f93\u5165\u4e0d\u62a5\u9519", analyze({})["evidence"]["count"] == 0)

    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_case.json")
    with open(tmp, "w", encoding="utf-8-sig") as f:
        json.dump({"case_type": "lost"}, f, ensure_ascii=False)
    ck("t21 BOM \u8f93\u5165\u89e3\u6790\u6210\u529f", read_json(tmp)["case_type"] == "lost")
    os.remove(tmp)

    ck("t22 \u5347\u7ea7\u8def\u5f84\u975e\u7a7a", len(ESCALATION) == 6)
    ck("t23 \u63d0\u793a\u6307\u5411\u6d4b\u7b97\u7c7b\u6280\u80fd", any("\u6d4b\u7b97\u7c7b\u6280\u80fd" in t for t in analyze({})["tips"]))
    ck("t24 \u63d0\u793a\u542b\u65f6\u9650\u53e3\u5f84", any("\u627f\u8fd0\u65b9\u53e3\u5f84" in t for t in analyze({})["tips"]))

    out = []
    out.append("SELFTEST FAIL: %s" % "; ".join(fails) if fails else "SELFTEST OK  24/24")
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, RESULT_FILE), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="\u5feb\u9012\u7406\u8d54\u6750\u6599\u4e0e\u8def\u5f84\u6838\u67e5")
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