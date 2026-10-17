# -*- coding: utf-8 -*-
"""\u62d6\u5ef6\u6210\u56e0\u5224\u5b9a\u4e0e\u5bf9\u7b56\u5339\u914d\u3002\u6807\u51c6\u5e93\u3002

\u7528\u6cd5:
  python procrastination_check.py --file case.json
  python procrastination_check.py --selftest
"""

import argparse
import json
import os
import sys

RESULT_FILE = "_selftest_result.txt"

CAUSE_RULES = [
    ("\u6015\u5b8c\u7f8e", ["\u53cd\u590d\u6539", "\u4e0d\u6ee1\u610f", "\u4e0d\u80af\u4ea4\u4ed8", "\u518d\u6539\u6539", "\u603b\u89c9\u5f97\u4e0d\u5b8c\u7f8e", "\u7ec6\u8282"]),
    ("\u6015\u5931\u8d25", ["\u4e0d\u6562\u5f00\u59cb", "\u6015\u505a\u4e0d\u597d", "\u6015\u5931\u8d25", "\u6ca1\u51c6\u5907\u597d"]),
    ("\u5bf9\u6297\u63a7\u5236", ["\u8d8a\u50ac\u8d8a\u62d6", "\u8981\u6211\u505a", "\u975e\u8ba9\u6211", "\u51ed\u4ec0\u4e48", "\u522b\u4eba\u903c"]),
    ("\u76ee\u6807\u4e0d\u6e05", ["\u4e0d\u77e5\u9053\u8be5\u505a\u4ec0\u4e48", "\u8bf4\u4e0d\u6e05", "\u6ca1\u5934\u7eea", "\u4efb\u52a1\u6a21\u7cca"]),
    ("\u60c5\u7eea\u56de\u907f", ["\u4e00\u60f3\u5230\u5c31\u70e6", "\u4e0d\u60f3\u9762\u5bf9", "\u6d89\u53ca\u67d0\u4e2a\u4eba", "\u5c31\u70e6"]),
    ("\u5373\u65f6\u5956\u52b1\u504f\u597d\u4e0d\u8db3", ["\u65e0\u804a\u7684\u6d3b", "\u8ba8\u538c\u7684\u4e8b", "\u6ca1\u610f\u601d", "\u67af\u71e5"]),
]
FIXES = {
    "\u6015\u5b8c\u7f8e": "\u8bbe\u5148\u5b8c\u6210\u518d\u6539\u7684\u786c\u89c4\u5219\u5e76\u9650\u5236\u4fee\u6539\u6b21\u6570\uff0c\u7b2c\u4e00\u7248\u5141\u8bb8\u7c97\u7cd9",
    "\u6015\u5931\u8d25": "\u62c6\u5230\u6781\u5c0f\u9897\u7c92\u8ba9\u505a\u4e00\u70b9\u5c31\u6709\u5b8c\u6210\u611f\uff0c\u5148\u964d\u4f4e\u6807\u51c6\u505a\u5b8c",
    "\u5bf9\u6297\u63a7\u5236": "\u4fdd\u7559\u81ea\u4e3b\u6743\uff0c\u81ea\u5df1\u9009\u987a\u5e8f\u4e0e\u65f6\u95f4\uff0c\u628a\u5fc5\u987b\u6539\u6210\u6211\u6253\u7b97",
    "\u76ee\u6807\u4e0d\u6e05": "\u5148\u5199\u6e05\u4ea7\u51fa\u7269\uff0c\u628a\u6a21\u7cca\u4efb\u52a1\u53d8\u6210\u5177\u4f53\u4ea4\u4ed8",
    "\u60c5\u7eea\u56de\u907f": "\u5148\u8bb0\u5f55\u5e76\u547d\u540d\u60c5\u7eea\uff0c\u628a\u4efb\u52a1\u4e0e\u60c5\u7eea\u5206\u5f00\u5904\u7406",
    "\u5373\u65f6\u5956\u52b1\u504f\u597d\u4e0d\u8db3": "\u52a0\u5165\u5373\u65f6\u5956\u52b1\uff0c\u56fa\u5b9a\u542f\u52a8\u65f6\u95f4\u5730\u70b9\u5e76\u7528\u4e24\u5206\u949f\u6cd5\u5219",
}
GRAIN_MIN = 5
GRAIN_MAX = 15
RED_LINE_WORDS = ["\u81ea\u6740", "\u81ea\u4f24", "\u8f7b\u751f", "\u4e0d\u60f3\u6d3b", "\u5e7b\u89c9", "\u5984\u60f3", "\u5c11\u7761\u5374\u4e0d\u56f0",
                  "\u60ca\u6050", "\u50ac\u5410", "\u6212\u65ad", "\u5931\u63a7"]


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return json.loads(raw.lstrip("\ufeff"))


def all_text(data):
    parts = [str(data.get("avoided_thought") or "")]
    for s in (data.get("cause_signals") or []):
        parts.append(str(s))
    return " ".join(parts)


def judge_cause(data):
    t = all_text(data)
    hits = [name for name, kws in CAUSE_RULES if any(k in t for k in kws)]
    if not hits:
        return None, []
    return hits[0], hits


def check_grain(minutes):
    try:
        m = int(minutes or 0)
    except (TypeError, ValueError):
        return {"minutes": minutes, "ok": False, "tip": "\u9884\u8ba1\u8017\u65f6\u9700\u4e3a\u5177\u4f53\u6570\u5b57"}
    if m == 0:
        return {"minutes": m, "ok": False, "tip": "\u672a\u7ed9\u51fa\u9884\u8ba1\u8017\u65f6\uff0c\u65e0\u6cd5\u5224\u65ad\u9897\u7c92\u5ea6"}
    if m > GRAIN_MAX:
        return {"minutes": m, "ok": False,
                "tip": "\u9897\u7c92\u8d85\u8fc7%d\u5206\u949f\uff0c\u542f\u52a8\u963b\u529b\u4f1a\u4e0a\u5347\uff0c\u5e94\u7ee7\u7eed\u62c6\u5206" % GRAIN_MAX}
    if m < GRAIN_MIN:
        return {"minutes": m, "ok": True, "tip": "\u9897\u7c92\u504f\u5c0f\uff0c\u53ef\u4e0e\u76f8\u90bb\u4efb\u52a1\u5408\u5e76"}
    return {"minutes": m, "ok": True, "tip": "\u9897\u7c92\u5ea6\u5408\u9002\uff0c\u53ef\u4ee5\u542f\u52a8"}


def start_action(data):
    if data.get("start_action"):
        return str(data["start_action"]), "\u5df2\u5b9a\u4e49\u6700\u5c0f\u542f\u52a8\u52a8\u4f5c"
    return "\u6253\u5f00\u6587\u6863\u5199\u4e00\u884c", "\u5efa\u8bae\u7684\u6700\u5c0f\u542f\u52a8\u52a8\u4f5c\u793a\u4f8b\uff0c\u5199\u4e00\u884c\u5373\u7b97\u5f00\u59cb"


def delay_gratification_note(cause, sleep_bad=False, attention_bad=False):
    if attention_bad or sleep_bad:
        return "\u5b58\u5728\u6ce8\u610f\u529b\u6216\u7761\u7720\u95ee\u9898\uff0c\u4e0d\u5b9c\u4f9d\u8d56\u5ef6\u8fdf\u6ee1\u8db3\u8bad\u7ec3\u786c\u625b"
    if cause == "\u5373\u65f6\u5956\u52b1\u504f\u597d\u4e0d\u8db3":
        return "\u5ef6\u8fdf\u6ee1\u8db3\u8bad\u7ec3\u5bf9\u672c\u7c7b\u6210\u56e0\u9700\u914d\u5408\u5373\u65f6\u5956\u52b1\uff0c\u5426\u5219\u53ea\u9760\u610f\u5fd7\u4f1a\u8017\u5c3d\u5e76\u52a0\u91cd\u62d6\u5ef6"
    return "\u5ef6\u8fdf\u6ee1\u8db3\u8bad\u7ec3\u4e0d\u662f\u901a\u7528\u65b9\u6848\uff0c\u4e0d\u80fd\u4f5c\u4e3a\u552f\u4e00\u65b9\u6cd5"


def fail_plan(failures):
    n = int(failures or 0)
    if n == 0:
        return ["\u5c1a\u672a\u5931\u8d25\uff0c\u5148\u6309\u5bf9\u7b56\u6267\u884c"]
    return [
        "\u4e0d\u8981\u8ffd\u52a0\u60e9\u7f5a\uff0c\u4e5f\u4e0d\u8981\u4f7f\u7528\u4e0b\u4e0d\u4e3a\u4f8b\u7684\u8bf4\u6cd5",
        "\u627e\u51fa\u8fd9\u6b21\u7684\u5177\u4f53\u963b\u529b\u5728\u54ea\u4e00\u6b65",
        "\u628a\u90a3\u4e00\u6b65\u7684\u4efb\u52a1\u9897\u7c92\u518d\u7f29\u5c0f\u4e00\u534a",
        "\u91cd\u65b0\u56fa\u5b9a\u4e0b\u6b21\u7684\u542f\u52a8\u65f6\u95f4\u4e0e\u5730\u70b9",
    ]


def analyze(data):
    cause, all_hits = judge_cause(data)
    grain = check_grain(data.get("task_minutes"))
    action, action_note = start_action(data)
    t = all_text(data) + " " + str(data.get("avoided_thought") or "")
    red = [w for w in RED_LINE_WORDS if w in t]
    red += [w for w in (data.get("red_line_flags") or [])]
    res = {
        "cause": cause, "cause_hits": all_hits,
        "fix": FIXES.get(cause), "grain": grain,
        "start_action": action, "start_action_note": action_note,
        "delay_note": delay_gratification_note(cause,
                                               bool(data.get("sleep_bad")),
                                               bool(data.get("attention_bad"))),
        "fail_plan": fail_plan(data.get("previous_failures")),
        "red_lines": red,
    }
    tips = []
    if cause:
        tips.append("\u5224\u5b9a\u6210\u56e0: " + cause)
        tips.append("\u5bf9\u5e94\u5bf9\u7b56: " + res["fix"])
    else:
        tips.append("\u6210\u56e0\u4fe1\u53f7\u4e0d\u8db3\uff0c\u5efa\u8bae\u8865\u5145\u63cf\u8ff0\u4ee5\u5339\u914d\u5bf9\u7b56\uff0c\u4e0d\u540c\u6210\u56e0\u9700\u4e0d\u540c\u65b9\u6cd5")
    if not grain["ok"]:
        tips.append(grain["tip"])
    tips.append(action_note)
    tips.append("\u56fa\u5b9a\u540c\u4e00\u65f6\u95f4\u4e0e\u5730\u70b9\u542f\u52a8\uff0c\u53ea\u542f\u52a8\u4e0d\u8981\u6c42\u5b8c\u6210")
    tips.append("\u73af\u5883\u51c6\u5907\uff1a\u624b\u673a\u653e\u8fdc\u3001\u684c\u9762\u6e05\u7a7a")
    tips.append(res["delay_note"])
    for p in res["fail_plan"]:
        tips.append(p)
    if red:
        tips.append("\u51fa\u73b0\u6c42\u52a9\u7ea2\u7ebf\u76f8\u5173\u4fe1\u53f7\uff0c\u5e94\u4e3b\u52a8\u5bfb\u6c42\u4e13\u4e1a\u5e2e\u52a9")
    tips.append("\u62d6\u5ef6\u672c\u8eab\u901a\u5e38\u4e0d\u5c5e\u4e8e\u5fc3\u7406\u75be\u75c5\u8303\u7574")
    tips.append("\u672c\u6280\u80fd\u4e0d\u63d0\u4f9b\u8bca\u65ad\uff0c\u4e0d\u66ff\u4ee3\u4e13\u4e1a\u5fc3\u7406\u6cbb\u7597")
    res["tips"] = tips
    return res


def run_file(path, as_json):
    res = analyze(read_json(path))
    if as_json:
        return json.dumps(res, ensure_ascii=False, indent=2)
    lines = []
    lines.append("\u5224\u5b9a\u6210\u56e0: %s" % (res["cause"] or "\u4fe1\u53f7\u4e0d\u8db3"))
    lines.append("\u5339\u914d\u5bf9\u7b56: %s" % (res["fix"] or "\u9700\u5148\u660e\u786e\u6210\u56e0"))
    lines.append("\u4efb\u52a1\u9897\u7c92: %s \u5206\u949f  %s" % (res["grain"]["minutes"], res["grain"]["tip"]))
    lines.append("\u6700\u5c0f\u542f\u52a8\u52a8\u4f5c: %s\uff08%s\uff09" % (res["start_action"], res["start_action_note"]))
    lines.append("\u5ef6\u8fdf\u6ee1\u8db3\u8bad\u7ec3: %s" % res["delay_note"])
    lines.append("\u6c42\u52a9\u7ea2\u7ebf: %s" % (res["red_lines"] or "\u65e0"))
    lines.append("\u5931\u8d25\u5e94\u5bf9:")
    for p in res["fail_plan"]:
        lines.append("  - %s" % p)
    for t in res["tips"]:
        lines.append("- %s" % t)
    return "\n".join(lines)


def selftest():
    fails = []

    def ck(name, cond):
        if not cond:
            fails.append(name)

    ck("t1 \u6015\u5b8c\u7f8e\u8bc6\u522b", judge_cause({"cause_signals": ["\u53cd\u590d\u6539\u4e0d\u6ee1\u610f"]})[0] == "\u6015\u5b8c\u7f8e")
    ck("t2 \u6015\u5931\u8d25\u8bc6\u522b", judge_cause({"cause_signals": ["\u4e0d\u6562\u5f00\u59cb"]})[0] == "\u6015\u5931\u8d25")
    ck("t3 \u5bf9\u6297\u63a7\u5236\u8bc6\u522b", judge_cause({"cause_signals": ["\u8d8a\u50ac\u8d8a\u62d6"]})[0] == "\u5bf9\u6297\u63a7\u5236")
    ck("t4 \u76ee\u6807\u4e0d\u6e05\u8bc6\u522b", judge_cause({"cause_signals": ["\u6ca1\u5934\u7eea"]})[0] == "\u76ee\u6807\u4e0d\u6e05")
    ck("t5 \u60c5\u7eea\u56de\u907f\u8bc6\u522b", judge_cause({"avoided_thought": "\u4e00\u60f3\u5230\u5c31\u70e6"})[0] == "\u60c5\u7eea\u56de\u907f")
    ck("t6 \u65e0\u4fe1\u53f7\u4e0d\u5224\u5b9a", judge_cause({})[0] is None)

    ck("t7 \u9897\u7c92\u5408\u9002", check_grain(10)["ok"] is True)
    ck("t8 \u9897\u7c92\u8fc7\u5927\u88ab\u62e6", check_grain(90)["ok"] is False)
    ck("t9 \u9897\u7c92\u504f\u5c0f\u4ecd\u53ef\u7528", check_grain(2)["ok"] is True)
    ck("t10 \u7f3a\u8017\u65f6\u88ab\u62e6", check_grain(0)["ok"] is False)
    ck("t11 \u975e\u6570\u503c\u8017\u65f6\u88ab\u62e6", check_grain("x")["ok"] is False)

    a, note = start_action({})
    ck("t12 \u65e0\u52a8\u4f5c\u7ed9\u793a\u4f8b", a == "\u6253\u5f00\u6587\u6863\u5199\u4e00\u884c")
    b, note2 = start_action({"start_action": "\u7ffb\u5f00\u4e66"})
    ck("t13 \u5df2\u5b9a\u4e49\u88ab\u91c7\u7528", b == "\u7ffb\u5f00\u4e66")

    ck("t14 \u5373\u65f6\u5956\u52b1\u7c7b\u63d0\u793a", "\u5373\u65f6\u5956\u52b1" in delay_gratification_note("\u5373\u65f6\u5956\u52b1\u504f\u597d\u4e0d\u8db3"))
    ck("t15 \u7761\u7720\u95ee\u9898\u4e0d\u786c\u625b", "\u4e0d\u5b9c\u4f9d\u8d56" in delay_gratification_note(None, sleep_bad=True))
    ck("t16 \u901a\u7528\u63d0\u9192", "\u4e0d\u662f\u901a\u7528\u65b9\u6848" in delay_gratification_note(None))

    ck("t17 \u672a\u5931\u8d25\u7ed9\u6267\u884c\u5efa\u8bae", "\u5148\u6309\u5bf9\u7b56\u6267\u884c" in fail_plan(0)[0])
    ck("t18 \u5931\u8d25\u540e\u7981\u4e0b\u4e0d\u4e3a\u4f8b", any("\u4e0b\u4e0d\u4e3a\u4f8b" in p for p in fail_plan(3)))
    ck("t19 \u5931\u8d25\u540e\u8981\u6c42\u7f29\u5c0f\u9897\u7c92", any("\u7f29\u5c0f\u4e00\u534a" in p for p in fail_plan(3)))

    r = analyze({"cause_signals": ["\u8d8a\u50ac\u8d8a\u62d6"], "task_minutes": 120})
    ck("t20 \u5927\u9897\u7c92\u88ab\u63d0\u793a", any("\u7ee7\u7eed\u62c6\u5206" in t for t in r["tips"]))
    ck("t21 \u5bf9\u6297\u63a7\u5236\u5bf9\u7b56\u5339\u914d", "\u81ea\u4e3b\u6743" in (r["fix"] or ""))
    ck("t22 \u5b8c\u7f8e\u4e0e\u5931\u8d25\u5bf9\u7b56\u4e0d\u540c", FIXES["\u6015\u5b8c\u7f8e"] != FIXES["\u6015\u5931\u8d25"])
    ck("t23 \u5fc3\u7406\u652f\u6301\u7c7b\u539f\u56e0\u51b2\u7a81", FIXES["\u60c5\u7eea\u56de\u907f"] != FIXES["\u76ee\u6807\u4e0d\u6e05"])
    ck("t24 \u7ea2\u7ebf\u4fe1\u53f7\u88ab\u8bc6\u522b", "\u81ea\u6740" in analyze({"cause_signals": ["\u60f3\u81ea\u6740"]})["red_lines"])
    ck("t25 \u63d0\u793a\u4e0d\u542b\u8bca\u65ad", any("\u4e0d\u63d0\u4f9b\u8bca\u65ad" in t for t in analyze({})["tips"]))
    ck("t26 \u6210\u56e0\u8868\u975e\u7a7a", len(CAUSE_RULES) == 6 and len(FIXES) == 6)
    ck("t27 \u56fa\u5b9a\u542f\u52a8\u63d0\u793a", any("\u56fa\u5b9a\u540c\u4e00\u65f6\u95f4" in t for t in analyze({})["tips"]))

    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_case.json")
    with open(tmp, "w", encoding="utf-8-sig") as f:
        json.dump({"task_minutes": 10}, f, ensure_ascii=False)
    ck("t28 BOM \u8f93\u5165\u89e3\u6790\u6210\u529f", int(read_json(tmp)["task_minutes"]) == 10)
    os.remove(tmp)

    out = []
    out.append("SELFTEST FAIL: %s" % "; ".join(fails) if fails else "SELFTEST OK  28/28")
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, RESULT_FILE), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="\u62d6\u5ef6\u6210\u56e0\u4e0e\u5bf9\u7b56\u6838\u67e5")
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