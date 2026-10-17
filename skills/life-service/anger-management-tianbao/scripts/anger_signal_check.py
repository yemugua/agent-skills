# -*- coding: utf-8 -*-
"""\u6124\u6012\u4fe1\u53f7\u5c42\u7ea7\u5224\u5b9a\u4e0e\u5e72\u9884\u987a\u5e8f\u68c0\u67e5\u3002\u6807\u51c6\u5e93\u3002

\u7528\u6cd5:
  python anger_signal_check.py --file scene.json
  python anger_signal_check.py --selftest
"""

import argparse
import json
import os
import sys

RESULT_FILE = "_selftest_result.txt"

EARLY = ["\u4e0b\u5df4\u7d27", "\u80a9\u9888\u50f5", "\u547c\u5438\u53d8\u6d45", "\u547c\u5438\u53d8\u5feb", "\u624b\u5fc3\u51fa\u6c57", "\u58f0\u97f3\u53d8\u9ad8", "\u5fc3\u8df3\u52a0\u5feb"]
RISING = ["\u8bed\u901f\u52a0\u5feb", "\u53cd\u590d\u6253\u65ad", "\u4f53\u6e29\u4e0a\u5347", "\u660e\u663e\u70e6\u8e81"]
OUT = ["\u97f3\u91cf\u5931\u63a7", "\u4eba\u8eab\u653b\u51fb", "\u6454\u4e1c\u897f", "\u7838", "\u8bf4\u4e0d\u51fa\u8bdd", "\u52a8\u624b"]
HARM = ["\u4f24\u5bb3\u4ed6\u4eba", "\u52a8\u624b\u6253", "\u7838\u5411", "\u9a7e\u8f66\u53d1\u6cc4", "\u6454\u5411", "\u6390", "\u6345"]
COOLING = ["\u5ef6\u957f\u547c\u6c14", "\u6682\u505c\u79bb\u573a", "\u51b7\u6c34", "\u63e1\u62f3", "\u653e\u6162\u8bed\u901f", "\u79bb\u5f00\u73b0\u573a"]
STAGES = ["early", "rising", "out_of_control"]
STAGE_CN = {"early": "\u4e00\u7ea7\u65e9\u671f\u8eab\u4f53\u4fe1\u53f7", "rising": "\u4e8c\u7ea7\u60c5\u7eea\u5347\u7ea7", "out_of_control": "\u4e09\u7ea7\u5931\u63a7\u8fb9\u7f18"}


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return json.loads(raw.lstrip("\ufeff"))


def join_signals(data):
    sig = data.get("signals")
    if isinstance(sig, list):
        return " ".join(str(s) for s in sig)
    return str(sig or "")


def judge_level(data):
    t = join_signals(data)
    explicit = str(data.get("level") or "").strip()
    if explicit in STAGES:
        return explicit
    if any(w in t for w in OUT):
        return "out_of_control"
    if any(w in t for w in RISING):
        return "rising"
    if any(w in t for w in EARLY):
        return "early"
    return "early"


def harm_risk(data):
    t = join_signals(data) + " " + str(data.get("violence_intent") or "")
    return [w for w in HARM if w in t]


def cooling_actions(data):
    t = join_signals(data) + " " + str(data.get("cooling_done") or "")
    return [w for w in COOLING if w in t]


def check_order(data):
    """\u987a\u5e8f\u5e94\u4e3a \u964d\u6e29 -> \u91cd\u8bc4 -> \u8868\u8fbe\u3002"""
    cooling = bool(data.get("cooling_done"))
    rerating = bool(data.get("rerating_done"))
    issues = []
    if rerating and not cooling:
        issues.append("\u672a\u964d\u6e29\u5c31\u505a\u8ba4\u77e5\u91cd\u8bc4\uff0c\u6b64\u65f6\u7406\u6027\u5224\u65ad\u529f\u80fd\u4e0b\u964d\uff0c\u91cd\u8bc4\u65e0\u6548")
    if not cooling:
        issues.append("\u672a\u505a\u751f\u7406\u964d\u6fc0\u6d3b\uff0c\u964d\u6e29\u4f18\u5148\u4e8e\u8bb2\u9053\u7406")
    return {"cooling": cooling, "rerating": rerating, "issues": issues,
            "ok": cooling and (not rerating or cooling)}


def analyze(data):
    lvl = judge_level(data)
    harm = harm_risk(data)
    cool = cooling_actions(data)
    order = check_order(data)
    res = {"level": lvl, "level_cn": STAGE_CN[lvl], "harm_risk": harm,
           "cooling_actions": cool, "order": order}
    tips = []
    if lvl == "early":
        tips.append("\u4e00\u7ea7\u4fe1\u53f7\u662f\u6700\u4f73\u4ecb\u5165\u70b9\uff0c\u7acb\u5373\u505a\u751f\u7406\u964d\u6fc0\u6d3b\u52a8\u4f5c")
    elif lvl == "rising":
        tips.append("\u5df2\u8fdb\u5165\u4e8c\u7ea7\uff0c\u5e94\u4e3b\u52a8\u79bb\u5f00\u73b0\u573a\u800c\u4e0d\u662f\u7ee7\u7eed\u8bb2\u9053\u7406")
    else:
        tips.append("\u5df2\u8fdb\u5165\u4e09\u7ea7\u5931\u63a7\u8fb9\u7f18\uff0c\u5fc5\u987b\u7acb\u5373\u79bb\u5f00\u73b0\u573a\uff0c\u4e0d\u5f97\u4ee5\u4efb\u4f55\u5f62\u5f0f\u53d1\u6cc4")
    if harm:
        tips.append("\u5b58\u5728\u4f24\u5bb3\u81ea\u5df1\u6216\u4ed6\u4eba\u7684\u98ce\u9669\uff0c\u5fc5\u987b\u7acb\u5373\u8fdc\u79bb\u4ed6\u4eba\u4e0e\u5371\u9669\u7269\u54c1\u5e76\u6c42\u52a9")
        tips.append("\u4e0d\u53ef\u7528\u7838\u7269\u3001\u52a8\u624b\u3001\u9a7e\u8f66\u6216\u9157\u9152\u65b9\u5f0f\u53d1\u6cc4")
    if not order["cooling"]:
        tips.append("\u7f3a\u5c11\u751f\u7406\u964d\u6fc0\u6d3b\u52a8\u4f5c\uff1a\u5ef6\u957f\u547c\u6c14\u3001\u6682\u505c\u79bb\u573a\u3001\u51b7\u6c34\u3001\u63e1\u62f3\u518d\u677e\u5f00")
    for it in order["issues"]:
        tips.append(it)
    tips.append("\u6124\u6012\u65f6\u8bb2\u9053\u7406\u65e0\u6548\uff0c\u5148\u964d\u6e29\u518d\u6c9f\u901a")
    tips.append("\u8ba4\u77e5\u91cd\u8bc4\u7528\u4e8e\u4e8b\u540e\u5e73\u9759\u65f6\uff0c\u4e0d\u5728\u6124\u6012\u73b0\u573a")
    tips.append("\u8868\u8fbe\u7528\u6211\u611f\u5230\u56e0\u4e3a\u5e0c\u671b\u7684\u53e5\u5f0f\uff0c\u907f\u514d\u7528\u4f60\u5f00\u5934\u7684\u6307\u8d23\u53e5\u5f0f")
    tips.append("\u672c\u6280\u80fd\u4e0d\u63d0\u4f9b\u8bca\u65ad\uff0c\u4e0d\u66ff\u4ee3\u4e13\u4e1a\u5fc3\u7406\u6cbb\u7597")
    res["tips"] = tips
    return res


def run_file(path, as_json):
    res = analyze(read_json(path))
    if as_json:
        return json.dumps(res, ensure_ascii=False, indent=2)
    lines = []
    lines.append("\u4fe1\u53f7\u5c42\u7ea7: %s" % res["level_cn"])
    lines.append("\u4f24\u5bb3\u98ce\u9669: %s" % (res["harm_risk"] or "\u65e0"))
    lines.append("\u5df2\u7528\u964d\u6e29\u52a8\u4f5c: %s" % (res["cooling_actions"] or "\u65e0"))
    lines.append("\u987a\u5e8f\u6b63\u786e: %s" % ("\u662f" if res["order"]["ok"] else "\u5426"))
    for it in res["order"]["issues"]:
        lines.append("  - %s" % it)
    for t in res["tips"]:
        lines.append("- %s" % t)
    return "\n".join(lines)


def selftest():
    fails = []

    def ck(name, cond):
        if not cond:
            fails.append(name)

    ck("t1 \u4e00\u7ea7\u4fe1\u53f7\u8bc6\u522b", judge_level({"signals": ["\u4e0b\u5df4\u7d27"]}) == "early")
    ck("t2 \u4e8c\u7ea7\u4fe1\u53f7\u8bc6\u522b", judge_level({"signals": ["\u8bed\u901f\u52a0\u5feb"]}) == "rising")
    ck("t3 \u4e09\u7ea7\u4fe1\u53f7\u8bc6\u522b", judge_level({"signals": ["\u97f3\u91cf\u5931\u63a7"]}) == "out_of_control")
    ck("t4 \u65e0\u4fe1\u53f7\u9ed8\u8ba4\u4e00\u7ea7", judge_level({}) == "early")
    ck("t5 \u663e\u5f0f\u5c42\u7ea7\u4f18\u5148", judge_level({"signals": ["\u97f3\u91cf\u5931\u63a7"], "level": "early"}) == "early")
    ck("t6 \u5b57\u7b26\u4e32\u578b\u4fe1\u53f7\u53ef\u89e3\u6790", judge_level({"signals": "\u4e0b\u5df4\u7d27 \u624b\u5fc3\u51fa\u6c57"}) == "early")

    ck("t7 \u4f24\u5bb3\u98ce\u9669\u88ab\u8bc6\u522b", len(harm_risk({"violence_intent": "\u60f3\u7838\u5411\u5bf9\u65b9"})) > 0)
    ck("t8 \u65e0\u4f24\u5bb3\u610f\u56fe\u4e0d\u62a5", harm_risk({}) == [])

    ck("t9 \u964d\u6e29\u52a8\u4f5c\u88ab\u8bc6\u522b", len(cooling_actions({"cooling_done": "\u5ef6\u957f\u547c\u6c14"})) > 0)
    ck("t10 \u65e0\u964d\u6e29\u4e0d\u62a5", cooling_actions({}) == [])

    ck("t11 \u5148\u91cd\u8bc4\u88ab\u5224\u987a\u5e8f\u9519", check_order({"rerating_done": True})["ok"] is False)
    ck("t12 \u5148\u964d\u6e29\u518d\u91cd\u8bc4\u6b63\u786e", check_order({"cooling_done": True, "rerating_done": True})["ok"] is True)
    ck("t13 \u53ea\u964d\u6e29\u6b63\u786e", check_order({"cooling_done": True})["ok"] is True)
    ck("t14 \u987a\u5e8f\u95ee\u9898\u88ab\u8bb0\u5f55", len(check_order({})["issues"]) == 1 and len(check_order({"rerating_done": True})["issues"]) == 2)

    r1 = analyze({"signals": ["\u97f3\u91cf\u5931\u63a7"]})
    ck("t15 \u4e09\u7ea7\u63d0\u793a\u79bb\u573a", any("\u79bb\u5f00\u73b0\u573a" in t for t in r1["tips"]))
    r2 = analyze({"signals": ["\u4e0b\u5df4\u7d27"]})
    ck("t16 \u4e00\u7ea7\u63d0\u793a\u7acb\u5373\u4ecb\u5165", any("\u6700\u4f73\u4ecb\u5165\u70b9" in t for t in r2["tips"]))
    r3 = analyze({"signals": ["\u4e0b\u5df4\u7d27"], "violence_intent": "\u60f3\u52a8\u624b\u6253"})
    ck("t17 \u4f24\u5bb3\u89e6\u53d1\u8fdc\u79bb\u63d0\u793a", any("\u8fdc\u79bb" in t for t in r3["tips"]))
    ck("t18 \u4f24\u5bb3\u89e6\u53d1\u7981\u53d1\u6cc4", any("\u4e0d\u53ef\u7528" in t for t in r3["tips"]))
    ck("t19 \u63d0\u793a\u542b\u4e0d\u66ff\u4ee3\u6cbb\u7597", any("\u4e0d\u66ff\u4ee3\u4e13\u4e1a\u5fc3\u7406\u6cbb\u7597" in t for t in analyze({})["tips"]))
    ck("t20 \u7a7a\u8f93\u5165\u4e0d\u62a5\u9519", analyze({})["level"] == "early")

    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_case.json")
    with open(tmp, "w", encoding="utf-8-sig") as f:
        json.dump({"signals": []}, f, ensure_ascii=False)
    ck("t21 BOM \u8f93\u5165\u89e3\u6790\u6210\u529f", isinstance(read_json(tmp)["signals"], list))
    os.remove(tmp)

    ck("t22 \u5c42\u7ea7\u6807\u7b7e\u5b8c\u6574", set(STAGES) == {"early", "rising", "out_of_control"})
    ck("t23 \u63d0\u793a\u542b\u5148\u964d\u6e29", any("\u5148\u964d\u6e29" in t for t in analyze({})["tips"]))
    ck("t24 \u63d0\u793a\u542b\u8868\u8fbe\u53e5\u5f0f", any("\u6211\u611f\u5230" in t for t in analyze({})["tips"]))

    out = []
    out.append("SELFTEST FAIL: %s" % "; ".join(fails) if fails else "SELFTEST OK  24/24")
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, RESULT_FILE), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="\u6124\u6012\u4fe1\u53f7\u4e0e\u5e72\u9884\u987a\u5e8f\u6838\u67e5")
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