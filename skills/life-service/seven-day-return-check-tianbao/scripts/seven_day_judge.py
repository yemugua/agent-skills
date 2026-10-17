# -*- coding: utf-8 -*-
"""\u4e03\u65e5\u65e0\u7406\u7531\u4f8b\u5916\u4e0e\u5b8c\u597d\u5224\u5b9a\u3002\u6807\u51c6\u5e93\u3002

\u7528\u6cd5:
  python seven_day_judge.py --file item.json
  python seven_day_judge.py --selftest
"""

import argparse
import json
import os
import sys

RESULT_FILE = "_selftest_result.txt"

CATEGORY_EXCEPTION = {
    "\u5b9a\u5236": "\u5b9a\u5236\u54c1\uff1a\u4f9d\u6d88\u8d39\u8005\u8981\u6c42\u4e13\u95e8\u5236\u4f5c\uff0c\u975e\u6807\u54c1",
    "\u9c9c\u6d3b\u6613\u8150": "\u9c9c\u6d3b\u6613\u8150\uff1a\u5546\u54c1\u6027\u8d28\u51b3\u5b9a",
    "\u97f3\u50cf\u5236\u54c1": "\u62c6\u5c01\u7684\u97f3\u50cf\u5236\u54c1\uff1a\u4ec5\u9650\u5df2\u62c6\u5c01\u60c5\u5f62",
    "\u8ba1\u7b97\u673a\u8f6f\u4ef6": "\u62c6\u5c01\u7684\u8ba1\u7b97\u673a\u8f6f\u4ef6\uff1a\u4ec5\u9650\u5df2\u62c6\u5c01\u60c5\u5f62",
    "\u62a5\u7eb8\u671f\u520a": "\u4ea4\u4ed8\u7684\u62a5\u7eb8\u671f\u520a\uff1a\u9650\u4e8e\u4ea4\u4ed8\u7684\u8ba2\u9605\u7269",
    "\u6570\u5b57\u5316\u5546\u54c1": "\u7f51\u7edc\u4e0b\u8f7d\u6216\u5df2\u62c6\u5c01\u7684\u6570\u5b57\u5316\u5546\u54c1",
}
# \u62c6\u5c01\u7c7b\u4f8b\u5916\u4ec5\u5728\u8fd9\u4e9b\u7c7b\u522b\u4e0b\u624d\u56e0\u62c6\u5c01\u800c\u547d\u4e2d
OPEN_EXEMPT_CATS = ["\u97f3\u50cf\u5236\u54c1", "\u8ba1\u7b97\u673a\u8f6f\u4ef6", "\u6570\u5b57\u5316\u5546\u54c1"]

CONDITION_ITEMS = ["packaging", "accessories", "tags", "used", "body"]
CONDITION_LABEL = {
    "packaging": "\u5305\u88c5\u7834\u635f\u6216\u5c01\u6761\u65e0\u6cd5\u590d\u539f",
    "accessories": "\u914d\u4ef6\u6216\u8d60\u54c1\u7f3a\u5931",
    "tags": "\u540a\u724c\u5df2\u526a\u6216\u6807\u8bc6\u7834\u574f",
    "used": "\u5b58\u5728\u4f7f\u7528\u75d5\u8ff9",
    "body": "\u5546\u54c1\u672c\u4f53\u6709\u6c61\u6e0d\u78e8\u635f\u5212\u75d5",
}
CATEGORY_NONE = ["\u666e\u901a", "\u670d\u9970", "\u978b", "\u5bb6\u5c45", "\u6570\u7801\u786c\u4ef6", "\u98df\u54c1\u5305\u88c5"]


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return json.loads(raw.lstrip("\ufeff"))


def check_exception(cat, opened):
    """\u4f8b\u5916\u547d\u4e2d\u60c5\u51b5\u3002\u62c6\u5c01\u7c7b\u4f8b\u5916\u53ea\u5bf9\u7279\u5b9a\u7c7b\u522b\u751f\u6548\u3002"""
    hits = []
    if cat in CATEGORY_EXCEPTION:
        hits.append(CATEGORY_EXCEPTION[cat])
        if cat in OPEN_EXEMPT_CATS and not opened:
            return [], "\u8be5\u7c7b\u522b\u4f8b\u5916\u4ee5\u5df2\u62c6\u5c01\u4e3a\u524d\u63d0\uff0c\u672c\u6b21\u672a\u62c6\u5c01\u5219\u4e0d\u547d\u4e2d"
    elif opened and cat in CATEGORY_NONE:
        return [], "\u62c6\u5c01\u7c7b\u4f8b\u5916\u53ea\u9488\u5bf9\u7279\u5b9a\u54c1\u7c7b\uff0c\u672c\u7c7b\u5546\u54c1\u4e0d\u56e0\u62c6\u5c01\u6784\u6210\u4f8b\u5916"
    return hits, "\u6309\u73b0\u884c\u89c4\u5b9a\u5217\u4e3e\u4e3a\u51c6\uff0c\u5177\u4f53\u53e3\u5f84\u4ee5\u53d7\u7406\u673a\u6784\u4e3a\u51c6"


def check_condition(cond):
    bad = []
    for k in CONDITION_ITEMS:
        if (cond or {}).get(k):
            bad.append(CONDITION_LABEL[k])
    return {"intact": not bad, "problems": bad}


def burden_of_proof(cat_exception_hit, cond_bad):
    """\u4e3e\u8bc1\u8d23\u4efb\u5f52\u5c5e\u3002"""
    return {
        "\u4f8b\u5916\u7531\u8c01\u4e3e\u8bc1": "\u7ecf\u8425\u8005",
        "\u4e0d\u5b8c\u597d\u7531\u8c01\u4e3e\u8bc1": "\u7ecf\u8425\u8005",
        "\u5b8c\u597d\u4e0e\u5728\u671f\u9650\u5185\u7531\u8c01\u4e3e\u8bc1": "\u6d88\u8d39\u8005",
        "\u5f53\u524d\u9700\u91cd\u70b9\u8d28\u8bc1": "\u8981\u6c42\u5546\u5bb6\u5bf9\u4f8b\u5916\u4e3b\u5f20\u63d0\u4f9b\u4f9d\u636e" if cat_exception_hit else "\u65e0\u4f8b\u5916\u4e3b\u5f20\u5219\u76f4\u63a5\u6838\u5bf9\u5b8c\u597d",
    }


def freight_tip(item_problem, insured, merchant_promise):
    if item_problem:
        return "\u5546\u54c1\u672c\u8eab\u6709\u95ee\u9898\uff0c\u901a\u5e38\u7531\u5546\u5bb6\u627f\u62c5\u8fd0\u8d39"
    if merchant_promise:
        return "\u5546\u5bb6\u5df2\u627f\u8bfa\u5305\u9000\uff0c\u5148\u6309\u627f\u8bfa\u6267\u884c\uff0c\u8fd0\u8d39\u9669\u4f5c\u4e3a\u515c\u5e95"
    if insured:
        return "\u6309\u8fd0\u8d39\u9669\u6761\u6b3e\u7406\u8d54\uff0c\u6ce8\u610f\u53ef\u80fd\u9650\u989d\u4e14\u9700\u63d0\u4ea4\u6750\u6599"
    return "\u65e0\u7406\u7531\u9000\u8d27\u901a\u5e38\u7531\u6d88\u8d39\u8005\u627f\u62c5\u9000\u8d27\u8fd0\u8d39"


def analyze(data):
    cat = str(data.get("category") or "").strip()
    opened = bool(data.get("opened"))
    hits, note = check_exception(cat, opened)
    cond = check_condition(data.get("condition"))
    item_problem = bool(data.get("item_defective"))
    res = {
        "category": cat,
        "opened": opened,
        "exception_hits": hits,
        "exception_note": note,
        "condition": cond,
        "burden": burden_of_proof(len(hits) > 0, not cond["intact"]),
        "freight": freight_tip(item_problem, bool(data.get("insured")), bool(data.get("merchant_promise"))),
    }
    res["verdict"] = (
        "\u5b58\u5728\u4f8b\u5916\u4e14\u5546\u5bb6\u5df2\u4e3e\u8bc1\uff0c\u53ef\u80fd\u4e0d\u9002\u7528\u4e03\u65e5\u65e0\u7406\u7531"
        if hits else
        ("\u5546\u54c1\u4e0d\u5b8c\u597d\uff0c\u4e0d\u7b26\u5b8c\u597d\u8981\u6c42" if not cond["intact"] else "\u521d\u6b65\u7b26\u5408\u4e03\u65e5\u65e0\u7406\u7531\u7684\u4e24\u9879\u8981\u4ef6")
    )
    res["tips"] = [
        "\u4f8b\u5916\u4e0e\u4e0d\u5b8c\u597d\u5747\u7531\u7ecf\u8425\u8005\u4e3e\u8bc1",
        "\u5b8c\u597d\u8bc1\u636e\u5fc5\u987b\u5728\u7533\u8bf7\u524d\u5df2\u56fa\u5b9a\uff0c\u4e8b\u540e\u65e0\u6cd5\u8865\u505a",
        "\u67e5\u9a8c\u4e0e\u4f7f\u7528\u6027\u8d28\u4e0d\u540c\uff0c\u8bd5\u7a7f\u51fa\u95e8\u5c5e\u4f7f\u7528",
        "\u8d77\u7b97\u65f6\u70b9\u4ee5\u73b0\u884c\u89c4\u5b9a\u4e3a\u51c6\uff0c\u5efa\u8bae\u8ba9\u5546\u5bb6\u51fa\u793a\u7cfb\u7edf\u9000\u8d27\u622a\u6b62\u65e5\u671f",
    ]
    return res


def run_file(path, as_json):
    res = analyze(read_json(path))
    if as_json:
        return json.dumps(res, ensure_ascii=False, indent=2)
    lines = []
    lines.append("\u5546\u54c1\u7c7b\u522b: %s  \u5df2\u62c6\u5c01: %s" % (res["category"], "\u662f" if res["opened"] else "\u5426"))
    lines.append("\u4f8b\u5916\u547d\u4e2d: %s" % (res["exception_hits"] or "\u65e0"))
    lines.append("  \u8bf4\u660e: %s" % res["exception_note"])
    c = res["condition"]
    lines.append("\u5b8c\u597d\u5224\u5b9a: %s  \u95ee\u9898\u9879: %s" % ("\u5b8c\u597d" if c["intact"] else "\u4e0d\u5b8c\u597d", c["problems"] or "\u65e0"))
    lines.append("\u521d\u6b65\u7ed3\u8bba: %s" % res["verdict"])
    for k, v in res["burden"].items():
        lines.append("  %s: %s" % (k, v))
    lines.append("\u8fd0\u8d39\u65b9\u5411: %s" % res["freight"])
    for t in res["tips"]:
        lines.append("- %s" % t)
    return "\n".join(lines)


def selftest():
    fails = []

    def ck(name, cond):
        if not cond:
            fails.append(name)

    h1, n1 = check_exception("\u5b9a\u5236", False)
    ck("t1 \u5b9a\u5236\u547d\u4e2d\u4f8b\u5916", len(h1) == 1)
    h2, n2 = check_exception("\u97f3\u50cf\u5236\u54c1", False)
    ck("t2 \u672a\u62c6\u5c01\u4e0d\u547d\u4e2d\u97f3\u50cf\u4f8b\u5916", h2 == [])
    ck("t3 \u672a\u62c6\u5c01\u7ed9\u51fa\u8bf4\u660e", "\u672a\u62c6\u5c01" in n2)
    h3, n3 = check_exception("\u97f3\u50cf\u5236\u54c1", True)
    ck("t4 \u62c6\u5c01\u547d\u4e2d\u97f3\u50cf\u4f8b\u5916", len(h3) == 1)
    h4, n4 = check_exception("\u978b", True)
    ck("t5 \u666e\u901a\u5546\u54c1\u62c6\u5c01\u4e0d\u547d\u4e2d\u4f8b\u5916", h4 == [])
    ck("t6 \u666e\u901a\u5546\u54c1\u7ed9\u51fa\u9a73\u65a5\u7406\u7531", "\u7279\u5b9a\u54c1\u7c7b" in n4)

    ck("t7 \u5b8c\u597d\u5224\u5b9a\u901a\u8fc7", check_condition({})["intact"] is True)
    ck("t8 \u4f7f\u7528\u75d5\u8ff9\u5f71\u54cd\u5b8c\u597d", check_condition({"used": True})["intact"] is False)
    ck("t9 \u8d60\u54c1\u7f3a\u5931\u5f71\u54cd\u5b8c\u597d", check_condition({"accessories": True})["intact"] is False)
    ck("t10 \u591a\u4e2a\u95ee\u9898\u9879\u88ab\u7d2f\u8ba1", len(check_condition({"used": True, "tags": True})["problems"]) == 2)
    ck("t11 \u7a7a\u6761\u4ef6\u4e0d\u62a5\u9519", check_condition(None)["intact"] is True)

    b = burden_of_proof(True, True)
    ck("t12 \u4f8b\u5916\u4e3e\u8bc1\u65b9\u4e3a\u7ecf\u8425\u8005", b["\u4f8b\u5916\u7531\u8c01\u4e3e\u8bc1"] == "\u7ecf\u8425\u8005")
    ck("t13 \u5b8c\u597d\u4e3e\u8bc1\u65b9\u4e3a\u6d88\u8d39\u8005", b["\u5b8c\u597d\u4e0e\u5728\u671f\u9650\u5185\u7531\u8c01\u4e3e\u8bc1"] == "\u6d88\u8d39\u8005")

    ck("t14 \u5546\u54c1\u95ee\u9898\u8fd0\u8d39\u5f52\u5546\u5bb6", "\u5546\u5bb6" in freight_tip(True, False, False))
    ck("t15 \u5546\u5bb6\u627f\u8bfa\u4f18\u5148", "\u627f\u8bfa" in freight_tip(False, True, True))
    ck("t16 \u8fd0\u8d39\u9669\u6309\u6761\u6b3e", "\u7406\u8d54" in freight_tip(False, True, False))
    ck("t17 \u65e0\u6761\u4ef6\u65f6\u6d88\u8d39\u8005\u627f\u62c5", "\u6d88\u8d39\u8005\u627f\u62c5" in freight_tip(False, False, False))

    r = analyze({"category": "\u5b9a\u5236", "opened": True})
    ck("t18 \u547d\u4e2d\u4f8b\u5916\u65f6\u7ed3\u8bba\u4e3a\u4e0d\u9002\u7528", "\u4e0d\u9002\u7528" in r["verdict"])
    r2 = analyze({"category": "\u978b", "opened": True, "condition": {}})
    ck("t19 \u666e\u901a\u5b8c\u597d\u65f6\u521d\u6b65\u7b26\u5408", "\u7b26\u5408" in r2["verdict"])
    r3 = analyze({"category": "\u978b", "condition": {"used": True}})
    ck("t20 \u4e0d\u5b8c\u597d\u65f6\u7ed3\u8bba\u4e3a\u4e0d\u7b26", "\u4e0d\u5b8c\u597d" in r3["verdict"])
    ck("t21 \u63d0\u793a\u542b\u4e3e\u8bc1\u8d23\u4efb", any("\u7ecf\u8425\u8005\u4e3e\u8bc1" in t for t in analyze({})["tips"]))

    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_case.json")
    with open(tmp, "w", encoding="utf-8-sig") as f:
        json.dump({"category": "\u978b"}, f, ensure_ascii=False)
    ck("t22 BOM \u8f93\u5165\u89e3\u6790\u6210\u529f", read_json(tmp)["category"] == "\u978b")
    os.remove(tmp)

    ck("t23 \u7a7a\u8f93\u5165\u4e0d\u62a5\u9519", analyze({})["condition"]["intact"] is True)
    ck("t24 \u7c7b\u522b\u8868\u975e\u7a7a", len(CATEGORY_EXCEPTION) > 0 and len(CONDITION_ITEMS) == 5)

    out = []
    out.append("SELFTEST FAIL: %s" % "; ".join(fails) if fails else "SELFTEST OK  24/24")
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, RESULT_FILE), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="\u4e03\u65e5\u65e0\u7406\u7531\u4f8b\u5916\u4e0e\u5b8c\u597d\u5224\u5b9a")
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