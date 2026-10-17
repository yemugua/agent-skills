# -*- coding: utf-8 -*-
"""\u5b64\u72ec\u4e09\u578b\u81ea\u67e5\u4e0e\u5e94\u5bf9\u8def\u5f84\u5efa\u8bae\u3002\u6807\u51c6\u5e93\u3002

\u7528\u6cd5:
  python loneliness_selfcheck.py --file self.json
  python loneliness_selfcheck.py --selftest
"""

import argparse
import json
import os
import sys

RESULT_FILE = "_selftest_result.txt"

TYPE_COUNT = "\u4e3b\u89c2\u5b64\u72ec\u611f-\u793e\u4f1a\u5173\u7cfb\u4e0d\u8db3"
TYPE_QUALITY = "\u4e3b\u89c2\u5b64\u72ec\u611f-\u5173\u7cfb\u8d28\u91cf\u5dee"
TYPE_ISOLATION = "\u5fc3\u7406\u5b64\u7acb"
PATHS = {
    TYPE_COUNT: "\u589e\u52a0\u8fde\u63a5\u7684\u91cf\uff1a\u5efa\u7acb\u5f31\u8fde\u63a5\u3001\u52a0\u5165\u5174\u8da3\u793e\u7fa4\u3001\u56fa\u5b9a\u65f6\u95f4\u5730\u70b9\u91cd\u590d\u53c2\u4e0e",
    TYPE_QUALITY: "\u63d0\u5347\u5173\u7cfb\u7684\u6df1\u5ea6\uff1a\u4e0d\u8ffd\u6c42\u6269\u5927\u5708\u5b50\uff0c\u8ba9\u4e00\u4e24\u4e2a\u5173\u7cfb\u66f4\u771f\u5b9e",
    TYPE_ISOLATION: "\u5904\u7406\u4ef7\u503c\u4e0e\u610f\u4e49\u95ee\u9898\uff1a\u4e0e\u4fe1\u4efb\u7684\u4eba\u8c08\u771f\u6b63\u5173\u5fc3\u7684\u4e8b\uff0c\u5fc5\u8981\u65f6\u5bfb\u6c42\u4e13\u4e1a\u652f\u6301",
}
SHAME_WORDS = ["\u5acc\u6211\u9ebb\u70e6", "\u8bf4\u4e86\u4e5f\u6ca1\u7528", "\u81ea\u5df1\u625b", "\u4e0d\u7b97\u4ec0\u4e48", "\u9ebb\u70e6\u522b\u4eba", "\u4e0d\u597d\u610f\u601d"]
RED_LINE_WORDS = ["\u81ea\u6740", "\u81ea\u4f24", "\u8f7b\u751f", "\u4e0d\u60f3\u6d3b", "\u5e7b\u89c9", "\u5984\u60f3", "\u5c11\u7761\u5374\u4e0d\u56f0",
                  "\u60ca\u6050", "\u50ac\u5410", "\u6212\u65ad"]


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return json.loads(raw.lstrip("\ufeff"))


def judge_type(data):
    """\u6309\u7f3a\u4eba\u6570/\u7f3a\u6df1\u5ea6/\u7f3a\u610f\u4e49\u5224\u5b9a\u4e09\u578b\u3002"""
    try:
        contacts = int(data.get("contact_count") or 0)
    except (TypeError, ValueError):
        contacts = 0
    deep = bool(data.get("deep_talk"))
    meaning = bool(data.get("meaning"))
    if meaning:
        return TYPE_ISOLATION
    if contacts <= 0:
        return TYPE_COUNT
    if not deep:
        return TYPE_QUALITY
    if contacts > 0 and deep and meaning:
        return TYPE_ISOLATION
    return TYPE_COUNT


def alone_boundary(data):
    """\u72ec\u5904\u4e0e\u5b64\u72ec\u7684\u754c\u7ebf\u5224\u65ad\u3002"""
    chosen = bool(data.get("chosen_alone"))
    after = str(data.get("alone_after") or "").strip()
    empty = any(w in after for w in ["\u7a7a", "\u5b64\u72ec", "\u96be\u53d7", "\u5931\u843d", "\u6ca1\u610f\u4e49"])
    filled = any(w in after for w in ["\u5145\u76c8", "\u6062\u590d", "\u8212\u670d", "\u5e73\u9759", "\u6ee1\u8db3"])
    if chosen and filled:
        return {"is_lonely": False, "note": "\u72ec\u5904\u4e3a\u4e3b\u52a8\u9009\u62e9\u4e14\u7ed3\u675f\u540e\u5145\u76c8\uff0c\u5c5e\u6b63\u5e38\u72ec\u5904\u800c\u975e\u5b64\u72ec"}
    if not chosen and empty:
        return {"is_lonely": True, "note": "\u72ec\u5904\u4e3a\u88ab\u52a8\u627f\u53d7\u4e14\u7ed3\u675f\u540e\u4ecd\u7a7a\uff0c\u7b26\u5408\u5b64\u72ec\u7279\u5f81"}
    return {"is_lonely": bool(empty),
            "note": "\u9700\u518d\u89c2\u5bdf\u72ec\u5904\u662f\u4e3b\u52a8\u9009\u62e9\u8fd8\u662f\u88ab\u52a8\u627f\u53d7"}


def shame_check(data):
    tags = [str(t) for t in (data.get("shame_signals") or [])]
    hits = [w for w in SHAME_WORDS if any(w in t for t in tags)]
    return hits


def red_lines(data):
    text = " ".join(str(t) for t in (data.get("red_line_flags") or []))
    return [w for w in RED_LINE_WORDS if w in text]


def alone_advice(data):
    out = ["\u544a\u77e5\u53ef\u4fe1\u4efb\u7684\u4eba\u81ea\u5df1\u72ec\u5c45\uff0c\u907f\u514d\u65e0\u4eba\u77e5\u6653\u7684\u98ce\u9669",
           "\u624b\u673a\u4fdd\u6301\u7545\u901a\uff0c\u5fc5\u8981\u65f6\u8bbe\u7f6e\u7d27\u6025\u8054\u7cfb\u4eba",
           "\u56fa\u5b9a\u65f6\u95f4\u4e0e\u56fa\u5b9a\u7684\u4eba\u8054\u7cfb\uff0c\u800c\u4e0d\u662f\u6709\u4e8b\u624d\u8054\u7cfb"]
    if bool(data.get("living_alone")):
        out.append("\u53ef\u4e86\u89e3\u6240\u5728\u793e\u533a\u7684\u652f\u6301\u670d\u52a1\uff0c\u4ee5\u5f53\u5730\u73b0\u884c\u670d\u52a1\u53e3\u5f84\u4e3a\u51c6")
        out.append("\u4e0e\u5bb6\u4eba\u6216\u670b\u53cb\u7ea6\u5b9a\u56fa\u5b9a\u63a2\u8bbf\u65f6\u95f4")
        out.append("\u5173\u6ce8\u98df\u6b32\u3001\u7761\u7720\u4e0e\u6d3b\u52a8\u91cf\u7684\u53d8\u5316\uff0c\u8fd9\u4e9b\u662f\u65e9\u671f\u4fe1\u53f7")
    else:
        out.append("\u72ec\u5c45\u8005\u5c24\u9700\u6ce8\u610f\u5b89\u5168\u5b89\u6392\uff0c\u975e\u72ec\u5c45\u8005\u540c\u6837\u9700\u8981\u53ef\u89e6\u8fbe\u7684\u8fde\u63a5")
    return out


def analyze(data):
    t = judge_type(data)
    b = alone_boundary(data)
    shame = shame_check(data)
    red = red_lines(data)
    res = {"type": t, "path": PATHS[t], "boundary": b, "shame": shame,
           "red_lines": red, "alone_advice": alone_advice(data)}
    tips = ["\u5224\u5b9a\u7c7b\u578b: " + t, "\u5e94\u5bf9\u8def\u5f84: " + res["path"], b["note"]]
    if t in (TYPE_QUALITY, TYPE_ISOLATION):
        tips.append("\u591a\u793e\u4ea4\u53ea\u5bf9\u5173\u7cfb\u4e0d\u8db3\u578b\u6709\u6548\uff0c\u672c\u578b\u5e94\u907f\u514d\u5355\u7eaf\u589e\u52a0\u793e\u4ea4\u6570\u91cf")
    if shame:
        tips.append("\u5b58\u5728\u6c42\u52a9\u7f9e\u803b\u611f\uff0c\u6c42\u52a9\u662f\u5408\u7406\u9009\u62e9\u800c\u4e0d\u662f\u5931\u8d25")
        tips.append("\u53ef\u4ece\u4f4e\u6210\u672c\u4f4e\u66b4\u9732\u7684\u63a5\u89e6\u5f00\u59cb\uff0c\u4e0d\u5fc5\u4ece\u6700\u96be\u7684\u4e8b\u5f00\u59cb")
    for a in res["alone_advice"]:
        tips.append(a)
    tips.append("\u4e0d\u8981\u4e3a\u4e86\u4e0d\u5b64\u72ec\u800c\u52c9\u5f3a\u81ea\u5df1\u8fdb\u5165\u4e0d\u5408\u9002\u7684\u5173\u7cfb")
    tips.append("\u9000\u51fa\u4e0d\u5065\u5eb7\u7684\u5173\u7cfb\u662f\u6539\u5584\u5904\u5883\u800c\u975e\u9003\u907f")
    tips.append("\u957f\u671f\u5b64\u72ec\u4e0e\u5065\u5eb7\u5b58\u5728\u5173\u8054\u4f46\u975e\u5fc5\u7136\u56e0\u679c\uff0c\u4e0d\u8981\u636e\u6b64\u8d23\u5907\u81ea\u5df1")
    if red:
        tips.append("\u51fa\u73b0\u6c42\u52a9\u7ea2\u7ebf\u76f8\u5173\u4fe1\u53f7\uff0c\u8bf7\u7acb\u5373\u5bfb\u6c42\u4e13\u4e1a\u5e2e\u52a9")
    tips.append("\u5b64\u72ec\u6301\u7eed\u52a0\u91cd\u6216\u5f71\u54cd\u793e\u4f1a\u529f\u80fd\u65f6\uff0c\u6c42\u52a9\u662f\u5408\u7406\u9009\u62e9")
    tips.append("\u672c\u6280\u80fd\u4e0d\u63d0\u4f9b\u8bca\u65ad\uff0c\u4e0d\u66ff\u4ee3\u4e13\u4e1a\u5fc3\u7406\u6cbb\u7597")
    res["tips"] = tips
    return res


def run_file(path, as_json):
    res = analyze(read_json(path))
    if as_json:
        return json.dumps(res, ensure_ascii=False, indent=2)
    lines = []
    lines.append("\u5224\u5b9a\u7c7b\u578b: %s" % res["type"])
    lines.append("\u5e94\u5bf9\u8def\u5f84: %s" % res["path"])
    lines.append("\u72ec\u5904\u4e0e\u5b64\u72ec: %s" % res["boundary"]["note"])
    lines.append("\u6c42\u52a9\u7f9e\u803b\u611f: %s" % (res["shame"] or "\u65e0"))
    lines.append("\u6c42\u52a9\u7ea2\u7ebf: %s" % (res["red_lines"] or "\u65e0"))
    for t in res["tips"]:
        lines.append("- %s" % t)
    return "\n".join(lines)


def selftest():
    fails = []

    def ck(name, cond):
        if not cond:
            fails.append(name)

    ck("t1 \u65e0\u8fde\u63a5\u5224\u6570\u91cf\u578b", judge_type({"contact_count": 0}) == TYPE_COUNT)
    ck("t2 \u6709\u8fde\u63a5\u4f46\u4e0d\u80fd\u6df1\u804a\u5224\u8d28\u91cf\u578b",
       judge_type({"contact_count": 5, "deep_talk": False}) == TYPE_QUALITY)
    ck("t3 \u6709\u610f\u4e49\u8fde\u63a5\u5224\u5fc3\u7406\u5b64\u7acb",
       judge_type({"contact_count": 5, "deep_talk": True, "meaning": True}) == TYPE_ISOLATION)
    ck("t4 \u6709\u610f\u4e49\u4f18\u5148\u4e8e\u5176\u4ed6",
       judge_type({"contact_count": 0, "meaning": True}) == TYPE_ISOLATION)
    ck("t5 \u7f3a\u7701\u4e0d\u62a5\u9519", judge_type({}) == TYPE_COUNT)
    ck("t6 \u975e\u6570\u503c\u8fde\u63a5\u6570\u4e0d\u62a5\u9519", judge_type({"contact_count": "x"}) == TYPE_COUNT)

    ck("t7 \u4e3b\u52a8\u4e14\u5145\u76c8\u4e3a\u72ec\u5904", alone_boundary({"chosen_alone": True, "alone_after": "\u5145\u76c8"})["is_lonely"] is False)
    ck("t8 \u88ab\u52a8\u4e14\u7a7a\u4e3a\u5b64\u72ec", alone_boundary({"chosen_alone": False, "alone_after": "\u4ecd\u7136\u7a7a"})["is_lonely"] is True)
    ck("t9 \u9700\u89c2\u5bdf\u7684\u60c5\u51b5\u6709\u63d0\u793a", "\u89c2\u5bdf" in alone_boundary({})["note"])

    ck("t10 \u7f9e\u803b\u611f\u88ab\u8bc6\u522b", len(shame_check({"shame_signals": ["\u5acc\u6211\u9ebb\u70e6"]})) > 0)
    ck("t11 \u65e0\u7f9e\u803b\u611f\u4e0d\u62a5", shame_check({}) == [])

    ck("t12 \u7ea2\u7ebf\u88ab\u8bc6\u522b", "\u81ea\u6740" in red_lines({"red_line_flags": ["\u6709\u65f6\u4f1a\u60f3\u81ea\u6740"]}))
    ck("t13 \u65e0\u7ea2\u7ebf\u4e0d\u62a5", red_lines({}) == [])

    ck("t14 \u72ec\u5c45\u8005\u7ed9\u793e\u533a\u63d0\u793a", any("\u793e\u533a" in a for a in alone_advice({"living_alone": True})))
    ck("t15 \u975e\u72ec\u5c45\u4e5f\u7ed9\u7d27\u6025\u8054\u7edc", any("\u7d27\u6025\u8054\u7cfb\u4eba" in a for a in alone_advice({})))

    r = analyze({"contact_count": 5, "deep_talk": False})
    ck("t16 \u8d28\u91cf\u578b\u63d0\u793a\u52ff\u53ea\u589e\u6570\u91cf", any("\u589e\u52a0\u793e\u4ea4\u6570\u91cf" in t for t in r["tips"]))
    r2 = analyze({"shame_signals": ["\u8bf4\u4e86\u4e5f\u6ca1\u7528"]})
    ck("t17 \u7f9e\u803b\u611f\u7ed9\u6c42\u52a9\u5efa\u8bae", any("\u5408\u7406\u9009\u62e9" in t for t in r2["tips"]))
    ck("t18 \u63d0\u793a\u542b\u4e0d\u5fc5\u52c9\u5f3a", any("\u52c9\u5f3a" in t for t in analyze({})["tips"]))
    ck("t19 \u63d0\u793a\u542b\u5173\u8054\u975e\u56e0\u679c", any("\u975e\u5fc5\u7136\u56e0\u679c" in t for t in analyze({})["tips"]))
    ck("t20 \u7ea2\u7ebf\u89e6\u53d1\u7acb\u5373\u6c42\u52a9", any("\u7acb\u5373\u5bfb\u6c42\u4e13\u4e1a\u5e2e\u52a9" in t for t in
                               analyze({"red_line_flags": ["\u81ea\u4f24"]})["tips"]))
    ck("t21 \u4e09\u578b\u8def\u5f84\u5404\u4e0d\u76f8\u540c", len(set(PATHS.values())) == 3)
    ck("t22 \u7a7a\u8f93\u5165\u4e0d\u62a5\u9519", analyze({})["boundary"]["is_lonely"] is False)

    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_case.json")
    with open(tmp, "w", encoding="utf-8-sig") as f:
        json.dump({"contact_count": 3}, f, ensure_ascii=False)
    ck("t23 BOM \u8f93\u5165\u89e3\u6790\u6210\u529f", int(read_json(tmp)["contact_count"]) == 3)
    os.remove(tmp)

    ck("t24 \u63d0\u793a\u542b\u4e0d\u66ff\u4ee3\u6cbb\u7597", any("\u4e0d\u66ff\u4ee3\u4e13\u4e1a\u5fc3\u7406\u6cbb\u7597" in t for t in analyze({})["tips"]))

    out = []
    out.append("SELFTEST FAIL: %s" % "; ".join(fails) if fails else "SELFTEST OK  24/24")
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, RESULT_FILE), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="\u5b64\u72ec\u4e09\u578b\u81ea\u67e5\u4e0e\u8def\u5f84\u5efa\u8bae")
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