# -*- coding: utf-8 -*-
"""\u52b3\u52a8\u4ef2\u88c1\u6750\u6599\u6e05\u5355\u4e0e\u8bc1\u636e\u77e9\u9635\u6838\u67e5\u3002\u6807\u51c6\u5e93\u3002

\u7528\u6cd5:
  python arbitration_checklist.py --file case.json
  python arbitration_checklist.py --selftest
"""

import argparse
import json
import os
import sys

RESULT_FILE = "_selftest_result.txt"

# \u8bc1\u636e\u5f3a\u5f31\u6392\u5e8f\uff1a\u503c\u8d8a\u5927\u8d8a\u5f3a
STRENGTH = {"\u52b3\u52a8\u5408\u540c": 5, "\u793e\u4fdd\u8bb0\u5f55": 4, "\u5de5\u8d44\u6d41\u6c34": 3, "\u8003\u52e4\u8bb0\u5f55": 2, "\u5458\u5de5\u9648\u8ff0": 1}
BASE_MATERIALS = ["\u4ef2\u88c1\u7533\u8bf7\u4e66", "\u8eab\u4efd\u8bc1\u660e", "\u8bc1\u636e\u76ee\u5f55"]
EMPLOYER_DOCS = ["\u8003\u52e4\u8bb0\u5f55", "\u5de5\u8d44\u53f0\u8d26", "\u89c4\u7ae0\u5236\u5ea6"]
CLAIM_EVIDENCE = {
    "\u786e\u8ba4\u52b3\u52a8\u5173\u7cfb": ["\u793e\u4fdd\u8bb0\u5f55", "\u5de5\u8d44\u6d41\u6c34", "\u8003\u52e4\u8bb0\u5f55"],
    "\u8ffd\u8ba8\u5de5\u8d44": ["\u5de5\u8d44\u6d41\u6c34", "\u8003\u52e4\u8bb0\u5f55", "\u52b3\u52a8\u5408\u540c"],
    "\u672a\u7b7e\u52b3\u52a8\u5408\u540c\u4e8c\u500d\u5de5\u8d44": ["\u5de5\u8d44\u6d41\u6c34", "\u8003\u52e4\u8bb0\u5f55"],
    "\u52a0\u73ed\u8d39": ["\u8003\u52e4\u8bb0\u5f55", "\u5de5\u8d44\u6d41\u6c34"],
    "\u7ecf\u6d4e\u8865\u507f": ["\u52b3\u52a8\u5408\u540c", "\u5de5\u8d44\u6d41\u6c34"],
    "\u8d54\u507f\u91d1": ["\u52b3\u52a8\u5408\u540c", "\u5de5\u8d44\u6d41\u6c34", "\u5458\u5de5\u9648\u8ff0"],
    "\u672a\u4f11\u5e74\u5047": ["\u52b3\u52a8\u5408\u540c", "\u5458\u5de5\u9648\u8ff0"],
}
STAGES = ["\u51c6\u5907", "\u4ef2\u88c1", "\u88c1\u51b3", "\u6267\u884c"]
# \u4ec5\u7528\u4e8e\u76f8\u5bf9\u63d0\u9192\uff0c\u4e0d\u5199\u6b7b\u6cd5\u5b9a\u65f6\u9650
TIME_REMINDER = [
    (24, "\u5df2\u63a5\u8fd1\u5e38\u89c1\u65f6\u9650\u533a\u95f4\uff0c\u8bf7\u7acb\u5373\u6838\u7b97\u65f6\u6548\u5e76\u4e3b\u5f20\u6743\u5229"),
    (12, "\u8ddd\u7591\u4f3c\u6743\u5229\u88ab\u4fb5\u5bb3\u65f6\u95f4\u8f83\u957f\uff0c\u8bf7\u5c3d\u5feb\u6838\u7b97\u65f6\u6548"),
]


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return json.loads(raw.lstrip("\ufeff"))


def rank_evidence(ev_list):
    """\u6309\u5f3a\u5f31\u6392\u5e8f\uff0c\u8fd4\u56de [(\u5f3a\u5ea6, \u540d\u79f0)]\u3002"""
    out = []
    for e in (ev_list or []):
        name = str(e)
        strength = 0
        for k, v in STRENGTH.items():
            if k in name and v > strength:
                strength = v
        out.append((strength, name))
    return sorted(out, key=lambda x: (-x[0], x[1]))


def matrix(claims, ev_list):
    """\u8bf7\u6c42\u7c7b\u578b\u4e0e\u8bc1\u636e\u5339\u914d\u77e9\u9635\u3002"""
    evs = [str(e) for e in (ev_list or [])]
    rows = []
    for c in (claims or []):
        need = CLAIM_EVIDENCE.get(c, [])
        missing = [n for n in need if not any(n in e for e in evs)]
        rows.append({"claim": c, "need": need, "missing": missing,
                     "matched": len(need) - len(missing)})
    return rows


def check_materials(ev_list):
    names = [str(e) for e in (ev_list or [])]
    missing = [m for m in BASE_MATERIALS if not any(m in n for n in names)]
    return {"missing": missing, "has_catalog": any("\u8bc1\u636e\u76ee\u5f55" in n for n in names)}


def time_reminder(months):
    m = int(months or 0)
    for limit, msg in TIME_REMINDER:
        if m >= limit:
            return {"months": m, "tip": msg}
    return {"months": m, "tip": "\u4ecd\u5e94\u6838\u7b97\u65f6\u6548\u5e76\u4fdd\u7559\u4e3b\u5f20\u6743\u5229\u7684\u8bc1\u636e"}


def employer_doc_gap(ev_list, claimed):
    have = [str(e) for e in (ev_list or [])]
    claim = [str(c) for c in (claimed or [])]
    missing = [d for d in EMPLOYER_DOCS if not any(d in e for e in have)]
    unclaimed = [d for d in missing if not any(d in c for c in claim)]
    return {"missing_from_own": missing, "not_claimed": unclaimed}


def next_stage(stage):
    if stage not in STAGES:
        return STAGES[0]
    i = STAGES.index(stage)
    return STAGES[i + 1] if i + 1 < len(STAGES) else None


def analyze(data):
    evs = data.get("evidence") or []
    rows = matrix(data.get("claims"), evs)
    res = {
        "ranked": rank_evidence(evs),
        "matrix": rows,
        "materials": check_materials(evs),
        "time": time_reminder(data.get("months_since_known")),
        "employer_docs": employer_doc_gap(evs, data.get("employer_docs")),
        "next_stage": next_stage(str(data.get("stage") or "\u51c6\u5907").strip()),
    }
    tips = []
    if res["materials"]["missing"]:
        tips.append("\u57fa\u7840\u6750\u6599\u7f3a\u5931: " + ",".join(res["materials"]["missing"]))
    if not res["materials"]["has_catalog"]:
        tips.append("\u7f3a\u8bc1\u636e\u76ee\u5f55\uff0c\u4ef2\u88c1\u5458\u96be\u4ee5\u5b9a\u4f4d\u8981\u8bc1\u660e\u7684\u4e8b\u5b9e")
    for r in rows:
        if r["missing"]:
            tips.append("\u8bf7\u6c42%s \u7f3a\u8bc1\u636e: %s" % (r["claim"], ",".join(r["missing"])))
    weak = [n for s, n in res["ranked"] if s <= 1]
    if weak:
        tips.append("\u8bc1\u636e\u8f83\u5f31: " + ",".join(weak) + "\uff0c\u9700\u5176\u4ed6\u8bc1\u636e\u5370\u8bc1")
    if res["employer_docs"]["not_claimed"]:
        tips.append("\u4f01\u4e1a\u638c\u63e1\u7684\u8bc1\u636e\u672a\u4e3b\u5f20\u8c03\u53d6: " + ",".join(res["employer_docs"]["not_claimed"]))
    tips.append(res["time"]["tip"])
    tips.append("\u65f6\u6548\u4e2d\u65ad\u9700\u8981\u4e3b\u5f20\u6743\u5229\u7684\u4e66\u9762\u8bc1\u636e")
    tips.append("\u7ecf\u6d4e\u8865\u507f\u4e0e\u8d54\u507f\u91d1\u9002\u7528\u60c5\u5f62\u4e0d\u540c\uff0c\u5e94\u5206\u522b\u5217\u660e")
    tips.append("\u8c03\u89e3\u534f\u8bae\u8fbe\u6210\u540e\u53ef\u7533\u8bf7\u53f8\u6cd5\u786e\u8ba4")
    res["tips"] = tips
    return res


def run_file(path, as_json):
    res = analyze(read_json(path))
    if as_json:
        return json.dumps(res, ensure_ascii=False, indent=2)
    lines = []
    lines.append("\u8bc1\u636e\u5f3a\u5f31\u6392\u5e8f:")
    for s, n in res["ranked"]:
        lines.append("  \u5f3a\u5ea6%s  %s" % (s, n))
    lines.append("\u8bf7\u6c42\u4e0e\u8bc1\u636e\u5339\u914d\u77e9\u9635:")
    for r in res["matrix"]:
        lines.append("  %s  \u7f3a: %s" % (r["claim"], ",".join(r["missing"]) or "\u65e0"))
    lines.append("\u57fa\u7840\u6750\u6599\u7f3a\u5931: %s" % (", ".join(res["materials"]["missing"]) or "\u65e0"))
    lines.append("\u8bc1\u636e\u76ee\u5f55: %s" % ("\u6709" if res["materials"]["has_catalog"] else "\u65e0"))
    lines.append("\u65f6\u6548\u76f8\u5bf9\u63d0\u9192: %s" % res["time"]["tip"])
    lines.append("\u4f01\u4e1a\u638c\u63e1\u4f46\u672a\u4e3b\u5f20\u8c03\u53d6: %s"
                 % (", ".join(res["employer_docs"]["not_claimed"]) or "\u65e0"))
    lines.append("\u4e0b\u4e00\u9636\u6bb5: %s" % (res["next_stage"] or "\u5df2\u5230\u672b\u7aef\u6216\u9700\u4eba\u5de5\u5224\u65ad"))
    for t in res["tips"]:
        lines.append("- %s" % t)
    return "\n".join(lines)


def selftest():
    fails = []

    def ck(name, cond):
        if not cond:
            fails.append(name)

    r = rank_evidence(["\u5458\u5de5\u9648\u8ff0", "\u52b3\u52a8\u5408\u540c", "\u5de5\u8d44\u6d41\u6c34"])
    ck("t1 \u8bc1\u636e\u6309\u5f3a\u5f31\u6392\u5e8f", r[0][1] == "\u52b3\u52a8\u5408\u540c" and r[-1][1] == "\u5458\u5de5\u9648\u8ff0")
    ck("t2 \u5f3a\u5ea6\u503c\u6b63\u786e", r[0][0] == 5)
    ck("t3 \u7a7a\u8bc1\u636e\u4e0d\u62a5\u9519", rank_evidence([]) == [])

    m = matrix(["\u8ffd\u8ba8\u5de5\u8d44"], ["\u5de5\u8d44\u6d41\u6c34"])
    ck("t4 \u77e9\u9635\u8bc6\u522b\u7f3a\u5931", "\u8003\u52e4\u8bb0\u5f55" in m[0]["missing"])
    m2 = matrix(["\u8ffd\u8ba8\u5de5\u8d44"], ["\u5de5\u8d44\u6d41\u6c34", "\u8003\u52e4\u8bb0\u5f55", "\u52b3\u52a8\u5408\u540c"])
    ck("t5 \u8bc1\u636e\u9f50\u5168\u65e0\u7f3a\u5931", m2[0]["missing"] == [])
    ck("t6 \u672a\u77e5\u8bf7\u6c42\u4e0d\u62a5\u9519", matrix(["xyz"], [])[0]["need"] == [])

    mat = check_materials(["\u4ef2\u88c1\u7533\u8bf7\u4e66", "\u8eab\u4efd\u8bc1\u660e", "\u8bc1\u636e\u76ee\u5f55"])
    ck("t7 \u57fa\u7840\u6750\u6599\u9f50\u5168", mat["missing"] == [])
    ck("t8 \u8bc1\u636e\u76ee\u5f55\u88ab\u8bc6\u522b", mat["has_catalog"] is True)
    ck("t9 \u7f3a\u6750\u6599\u88ab\u62a5", "\u4ef2\u88c1\u7533\u8bf7\u4e66" in check_materials([])["missing"])

    ck("t10 \u957f\u65f6\u8ddd\u89e6\u53d1\u63d0\u9192", "\u65f6\u6548" in time_reminder(24)["tip"])
    ck("t11 \u77ed\u65f6\u8ddd\u4ecd\u63d0\u9192", time_reminder(1)["months"] == 1)
    ck("t12 \u96f6\u6708\u4e0d\u62a5\u9519", time_reminder(0)["months"] == 0)

    g = employer_doc_gap(["\u52b3\u52a8\u5408\u540c"], ["\u8003\u52e4\u8bb0\u5f55"])
    ck("t13 \u4f01\u4e1a\u8bc1\u636e\u7f3a\u53e3\u88ab\u8bc6\u522b", "\u8003\u52e4\u8bb0\u5f55" in g["missing_from_own"])
    ck("t14 \u672a\u4e3b\u5f20\u8c03\u53d6\u88ab\u62a5", "\u5de5\u8d44\u53f0\u8d26" in g["not_claimed"] and "\u8003\u52e4\u8bb0\u5f55" not in g["not_claimed"])
    g2 = employer_doc_gap(["\u52b3\u52a8\u5408\u540c", "\u8003\u52e4\u8bb0\u5f55", "\u5de5\u8d44\u53f0\u8d26", "\u89c4\u7ae0\u5236\u5ea6"], [])
    ck("t15 \u5168\u90e8\u6301\u6709\u65e0\u7f3a\u53e3", g2["missing_from_own"] == [])

    ck("t16 \u51c6\u5907\u9636\u6bb5\u4e0b\u4e00\u6b65", next_stage("\u51c6\u5907") == "\u4ef2\u88c1")
    ck("t17 \u88c1\u51b3\u540e\u4e0b\u4e00\u6b65\u4e3a\u6267\u884c", next_stage("\u88c1\u51b3") == "\u6267\u884c")
    ck("t18 \u6267\u884c\u5230\u672b\u7aef", next_stage("\u6267\u884c") is None)
    ck("t19 \u975e\u6cd5\u9636\u6bb5\u56de\u843d\u51c6\u5907", next_stage("xyz") == "\u51c6\u5907")

    a = analyze({"claims": ["\u8ffd\u8ba8\u5de5\u8d44"], "evidence": ["\u5458\u5de5\u9648\u8ff0"], "stage": "\u51c6\u5907"})
    ck("t20 \u5f31\u8bc1\u636e\u88ab\u63d0\u793a", any("\u8bc1\u636e\u8f83\u5f31" in t for t in a["tips"]))
    ck("t21 \u7f3a\u76ee\u5f55\u88ab\u63d0\u793a", any("\u8bc1\u636e\u76ee\u5f55" in t for t in a["tips"]))
    ck("t22 \u63d0\u793a\u542b\u53f8\u6cd5\u786e\u8ba4", any("\u53f8\u6cd5\u786e\u8ba4" in t for t in a["tips"]))
    ck("t23 \u63d0\u793a\u542b\u8865\u507f\u8d54\u507f\u533a\u5206", any("\u5206\u522b\u5217\u660e" in t for t in analyze({})["tips"]))
    ck("t24 \u7a7a\u8f93\u5165\u4e0d\u62a5\u9519", analyze({})["matrix"] == [])

    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_case.json")
    with open(tmp, "w", encoding="utf-8-sig") as f:
        json.dump({"claims": []}, f, ensure_ascii=False)
    ck("t25 BOM \u8f93\u5165\u89e3\u6790\u6210\u529f", isinstance(read_json(tmp)["claims"], list))
    os.remove(tmp)

    ck("t26 \u8bf7\u6c42\u7c7b\u578b\u8868\u8986\u76d6\u4e03\u7c7b", len(CLAIM_EVIDENCE) == 7)
    ck("t27 \u8bc1\u636e\u5f3a\u5ea6\u8868\u975e\u7a7a", len(STRENGTH) == 5)

    out = []
    out.append("SELFTEST FAIL: %s" % "; ".join(fails) if fails else "SELFTEST OK  27/27")
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, RESULT_FILE), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="\u52b3\u52a8\u4ef2\u88c1\u6750\u6599\u4e0e\u8bc1\u636e\u6838\u67e5")
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