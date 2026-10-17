# -*- coding: utf-8 -*-
"""\u5ba0\u7269\u72d7\u57fa\u7840\u670d\u4ece\u8bad\u7ec3\u8ba1\u5212\u6821\u9a8c\u811a\u672c\u3002

\u8bfb\u5165\u4e00\u4efd\u8bad\u7ec3\u8ba1\u5212\u7684 json\uff0c\u6838\u5bf9\uff1a
  1. \u72ac\u9f84\u5206\u7ec4\u662f\u5426\u88ab\u8bc6\u522b\uff0c\u5355\u6b21\u65f6\u957f\u4e0e\u6bcf\u65e5\u6b21\u6570\u662f\u5426\u5728\u786c\u533a\u95f4\u5185
  2. \u662f\u5426\u4f7f\u7528\u4e86\u7981\u6b62\u624b\u6bb5\u6216\u7981\u6b62\u5668\u5177
  3. \u53ec\u56de\u540e\u662f\u5426\u88ab\u60e9\u7f5a\uff08\u53ec\u56de\u57ae\u6389\u7684\u7b2c\u4e00\u539f\u56e0\uff09
  4. \u6807\u8bb0\u5ef6\u8fdf\u662f\u5426\u843d\u5728\u6709\u6548\u7a97\u53e3\u5185
  5. \u76ee\u6807\u52a8\u4f5c\u7684\u524d\u7f6e\u9636\u6bb5\u662f\u5426\u5df2\u5b8c\u6210\uff08\u662f\u5426\u8df3\u6b65\uff09
  6. \u5931\u8d25\u5904\u7406\u662f\u5426\u4e3a\u964d\u7ea7\uff0c\u800c\u975e\u52a0\u7801\u91cd\u590d
  7. \u73af\u5883\u7ea7\u522b\u662f\u5426\u4e0e\u76ee\u6807\u9636\u6bb5\u7684\u8fdb\u5ea6\u76f8\u79f0

\u7ed3\u8bba\u5206\u4e09\u6863\uff1a\u5148\u5904\u7406 / \u5f85\u786e\u8ba4 / \u53ef\u7167\u6b64\u6267\u884c\u3002
\u5224\u5b9a\u987a\u5e8f\u56fa\u5b9a\uff1a\u5148\u770b\u771f\u5b9e\u7f3a\u9677\uff0c\u518d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574\u3002

\u7528\u6cd5:
  python dog_training_plan.py --selftest
  python dog_training_plan.py --file plan.json
"""
import argparse
import json
import os
import sys

HEREDIR = os.path.dirname(os.path.abspath(__file__))

AGE_LIMIT = {
    "\u5e7c\u72ac": {"lo": 2, "hi": 6, "minute": (3, 10), "times": (1, 5)},
    "\u9752\u72ac": {"lo": 6, "hi": 12, "minute": (5, 15), "times": (1, 3)},
    "\u6210\u72ac": {"lo": 12, "hi": 240, "minute": (5, 20), "times": (1, 3)},
}

STAGES = ["\u6ce8\u610f\u529b", "\u5750\u4e0b", "\u8db4\u4e0b", "\u7b49\u5f85", "\u968f\u884c", "\u53ec\u56de"]
PREREQ = {
    "\u6ce8\u610f\u529b": [],
    "\u5750\u4e0b": ["\u6ce8\u610f\u529b"],
    "\u8db4\u4e0b": ["\u6ce8\u610f\u529b", "\u5750\u4e0b"],
    "\u7b49\u5f85": ["\u6ce8\u610f\u529b", "\u5750\u4e0b", "\u8db4\u4e0b"],
    "\u968f\u884c": ["\u6ce8\u610f\u529b", "\u5750\u4e0b", "\u8db4\u4e0b", "\u7b49\u5f85"],
    "\u53ec\u56de": ["\u6ce8\u610f\u529b", "\u5750\u4e0b", "\u8db4\u4e0b", "\u7b49\u5f85", "\u968f\u884c"],
}

BAN_TOOL = ["\u7535\u51fb\u9879\u5708", "\u9488\u523a\u9879\u5708", "\u91d1\u5c5e\u6ed1\u52a8\u94fe", "\u81ea\u52a8\u6536\u7d27\u7ef3", "\u9489\u523a\u9879\u5708"]
BAN_METHOD = ["\u4f53\u7f5a", "\u6253\u5634\u5df4", "\u6572\u6253", "\u5f3a\u884c\u6309\u538b", "\u5173\u7981\u95ed", "\u55b7\u6c34\u60e9\u7f5a"]
BAN_STRESS = {"\u957f\u65f6\u95f4\u5173\u7981\u95ed": "\u7834\u574f\u5982\u5395\u4e60\u60ef\u4e0e\u72ec\u5904\u5b89\u5168\u611f"}

ENV_LEVEL = {"\u5ba4\u5185\u5b89\u9759": 1, "\u5ba4\u5185\u6709\u5e72\u6270": 2, "\u9662\u5b50\u697c\u9053": 3, "\u6237\u5916\u4f4e\u5e72\u6270": 4, "\u6237\u5916\u9ad8\u5e72\u6270": 5}
TOOL_ALIAS = {"\u7535\u51fb": "\u7535\u51fb\u9879\u5708", "P\u5b57\u94fe": "\u91d1\u5c5e\u6ed1\u52a8\u94fe", "\u6536\u675f\u7ef3": "\u81ea\u52a8\u6536\u7d27\u7ef3"}
TARGET_ALIAS = {"\u5750": "\u5750\u4e0b", "\u8db4": "\u8db4\u4e0b", "\u7b49": "\u7b49\u5f85", "\u53ec\u56de\u8bad\u7ec3": "\u53ec\u56de", "\u968f\u884c\u8bad\u7ec3": "\u968f\u884c"}
STAGE_ALIAS = {"\u5750": "\u5750\u4e0b", "\u8db4": "\u8db4\u4e0b", "\u7b49": "\u7b49\u5f85"}
REQUIRED = ["age_months", "minutes_per_session", "sessions_per_day", "target",
            "marker_established", "reward_delay_sec"]


def norm(s):
    return str(s).strip().replace(" ", "").replace("\u3000", "")


def load_plan(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def age_group(months):
    try:
        m = float(months)
    except (TypeError, ValueError):
        return None
    for k, v in AGE_LIMIT.items():
        if v["lo"] <= m < v["hi"]:
            return k
    return None


def canon(value, table, valid):
    """\u628a\u522b\u540d\u548c\u89c4\u8303\u540d\u90fd\u5f52\u4e00\u5230\u89c4\u8303\u540d\u3002"""
    n = norm(value)
    if n in valid:
        return n
    return table.get(n, None)


def check(plan):
    bad = []
    warn = []
    miss = []

    for k in REQUIRED:
        if k not in plan or plan[k] in ("", None):
            miss.append("\u7f3a\u5c11\u5fc5\u586b\u5b57\u6bb5 %s" % k)

    grp = age_group(plan.get("age_months"))
    if grp is None:
        miss.append("\u6708\u9f84\u300c%s\u300d\u65e0\u6cd5\u5f52\u5165\u5e7c\u72ac\u3001\u9752\u72ac\u6216\u6210\u72ac\uff0c\u65e0\u6cd5\u5224\u5b9a\u65f6\u957f\u533a\u95f4" % plan.get("age_months"))

    target = canon(plan.get("target", ""), TARGET_ALIAS, STAGES)
    if target is None:
        miss.append("\u8bad\u7ec3\u76ee\u6807\u300c%s\u300d\u65e0\u6cd5\u8bc6\u522b\uff0c\u5e94\u5728 %s \u53d6\u503c" % (
            plan.get("target", ""), "/".join(STAGES)))

    # 1 \u65f6\u957f\u4e0e\u9891\u6b21
    if grp is not None:
        lim = AGE_LIMIT[grp]
        try:
            mi = float(plan.get("minutes_per_session"))
            if mi > lim["minute"][1]:
                bad.append("\u5355\u6b21\u65f6\u957f %.0f \u5206\u949f\u8d85\u51fa\u300c%s\u300d\u4e0a\u9650 %d \u5206\u949f\uff1a\u540e\u534a\u6bb5\u5168\u5728\u7ec3\u4e60\u8d70\u795e\uff0c"
                           "\u7b49\u4e8e\u6bcf\u5929\u767d\u7ec3" % (mi, grp, lim["minute"][1]))
            elif mi < lim["minute"][0]:
                bad.append("\u5355\u6b21\u65f6\u957f %.0f \u5206\u949f\u4f4e\u4e8e\u300c%s\u300d\u4e0b\u9650 %d \u5206\u949f\uff1a\u5355\u6b21\u8fc7\u77ed\u8d77\u4e0d\u5230\u7ec3\u4e60\u4f5c\u7528" % (
                    mi, grp, lim["minute"][0]))
        except (TypeError, ValueError):
            pass
        try:
            ts = int(plan.get("sessions_per_day"))
            if ts > lim["times"][1]:
                bad.append("\u6bcf\u65e5\u8bad\u7ec3 %d \u6b21\u8d85\u51fa\u300c%s\u300d\u4e0a\u9650 %d \u6b21\uff1a\u8d85\u9891\u4f1a\u5f62\u6210\u538b\u529b\uff0c"
                           "\u5e94\u6539\u4e3a\u77ed\u800c\u591a\u6b21\u5e76\u5728\u51fa\u73b0\u538b\u529b\u4fe1\u53f7\u65f6\u7acb\u5373\u505c\u6b62" % (ts, grp, lim["times"][1]))
            elif ts < lim["times"][0]:
                bad.append("\u6bcf\u65e5\u8bad\u7ec3 %d \u6b21\u4f4e\u4e8e\u4e0b\u9650 %d \u6b21\uff1a\u9891\u6b21\u4e0d\u8db3\u96be\u4ee5\u5f62\u6210\u7a33\u5b9a\u8054\u7ed3" % (
                    ts, lim["times"][0]))
        except (TypeError, ValueError):
            pass

    # 2 \u7981\u6b62\u5668\u5177
    tools = plan.get("tools") or []
    hit_tool = []
    hit_method = []
    for t in tools:
        c = canon(t, TOOL_ALIAS, BAN_TOOL)
        if c in BAN_TOOL:
            hit_tool.append(c)
        for b in BAN_TOOL:
            if b in norm(t):
                hit_tool.append(b)
    methods = plan.get("methods") or []
    for m in methods:
        for b in BAN_METHOD:
            if b in norm(m):
                hit_method.append(b)
    for h in sorted(set(hit_tool)):
        bad.append("\u5668\u5177\u6e05\u5355\u542b\u7981\u7528\u9879\u300c%s\u300d\uff1a\u9760\u75bc\u75db\u6216\u6050\u5413\u5236\u52a8\uff0c\u4f1a\u52a0\u5267\u66b4\u51b2\u6216\u5f15\u53d1\u9632\u5fa1\u53cd\u5e94\uff1b"
                   "\u5e94\u6539\u7528\u80f8\u80cc\u5e26\u4e0e\u957f\u7ef3" % h)
    for h in sorted(set(hit_method)):
        bad.append("\u8bad\u7ec3\u624b\u6bb5\u542b\u7981\u7528\u9879\u300c%s\u300d\uff1a%s\uff1b\u5e94\u6539\u7528\u5ffd\u7565\u52a0\u66ff\u4ee3\u884c\u4e3a\u7684\u505a\u6cd5" % (
            h, BAN_STRESS.get(h, "\u53ea\u6559\u51fa\u8eb2\u907f\uff0c\u4e0d\u6559\u51fa\u6b63\u786e\u884c\u4e3a")))

    # 3 \u53ec\u56de\u540e\u88ab\u60e9\u7f5a
    if plan.get("punish_recall"):
        bad.append("\u53ec\u56de\u540e\u60e9\u7f5a\uff1a\u72d7\u4f1a\u628a\u300c\u56de\u6765\u300d\u4e0e\u574f\u4e8b\u8fde\u8d77\u6765\uff0c\u8fd9\u662f\u53ec\u56de\u57ae\u6389\u7684\u7b2c\u4e00\u539f\u56e0\uff1b"
                   "\u6b63\u786e\u505a\u6cd5\u662f\u53ec\u56de\u540e\u5956\u52b1\uff0c\u7136\u540e\u653e\u5b83\u56de\u53bb\u73a9")

    # 4 \u6807\u8bb0\u5ef6\u8fdf
    try:
        dl = float(plan.get("reward_delay_sec"))
        if dl > 2.0:
            bad.append("\u5956\u52b1\u5ef6\u8fdf %.1f \u79d2\u8d85\u8fc7 2 \u79d2\u53e3\u5f84\uff1a\u6807\u8bb0\u665a\u4e00\u79d2\uff0c\u5f3a\u5316\u5230\u7684\u5c31\u662f\u4e0b\u4e00\u4e2a\u52a8\u4f5c\uff0c"
                       "\u8fd9\u662f\u96f6\u98df\u7ed9\u4e0d\u5c11\u5374\u6ca1\u6548\u679c\u7684\u6700\u5e38\u89c1\u539f\u56e0" % dl)
        elif dl < 0:
            bad.append("\u5956\u52b1\u5ef6\u8fdf\u4e3a\u8d1f\u6570\uff0c\u6570\u636e\u65e0\u6548")
    except (TypeError, ValueError):
        pass

    # 5 \u524d\u7f6e\u9636\u6bb5\u662f\u5426\u5b8c\u6210\uff08\u8df3\u6b65\uff09
    if target is not None:
        done = []
        for s in plan.get("done_stages") or []:
            c = canon(s, STAGE_ALIAS, STAGES)
            if c:
                done.append(c)
        need = PREREQ[target]
        lack = [x for x in need if x not in done]
        if lack:
            bad.append("\u76ee\u6807\u300c%s\u300d\u7f3a\u524d\u7f6e\u9636\u6bb5 %s\uff1a\u6ca1\u8fbe\u6807\u5c31\u8fdb\u9636\u57fa\u672c\u5fc5\u5e9f\uff0c"
                       "\u5e94\u5148\u628a\u7f3a\u7684\u9636\u6bb5\u5404\u7ec3 3 \u5230 5 \u5929" % (target, "/".join(lack)))
        if not plan.get("marker_established"):
            bad.append("\u5c1a\u672a\u5efa\u7acb\u6807\u8bb0\u8bcd\u6216\u54cd\u7247\u7684\u914d\u5bf9\u5c31\u5f00\u59cb\u7ec3\u52a8\u4f5c\uff0c\u7b49\u4e8e\u8df3\u8fc7\u5730\u57fa\uff1b"
                       "\u5e94\u5148\u7528\u8fde\u7eed 20 \u6b21\u54cd\u7247\u540e\u7acb\u523b\u7ed9\u98df\u5b8c\u6210\u914d\u5bf9")

    # 6 \u5931\u8d25\u5904\u7406\uff1a\u5fc5\u987b\u662f\u964d\u7ea7\uff0c\u4e0d\u8bb8\u52a0\u7801\u91cd\u590d
    try:
        rp = int(plan.get("repeat_on_fail"))
        if rp > 3:
            bad.append("\u540c\u4e00\u53e3\u4ee4\u91cd\u590d %d \u6b21\u8fdc\u8d85 3 \u6b21\u4e0a\u9650\uff1a\u558a\u5230\u7b2c\u4e94\u904d\u72d7\u5df2\u5b66\u4f1a\u524d\u51e0\u904d\u53ef\u4ee5\u4e0d\u5f53\u56de\u4e8b\uff0c"
                       "\u53e3\u4ee4\u88ab\u81ea\u5df1\u7a00\u91ca\u6389\uff1b\u5e94\u6539\u4e3a\u91cd\u590d 3 \u6b21\u65e0\u54cd\u5e94\u5c31\u964d\u56de\u4e0a\u4e00\u96be\u5ea6\u91cd\u6765" % rp)
    except (TypeError, ValueError):
        pass

    # 7 \u73af\u5883\u7ea7\u522b
    env = norm(plan.get("env", ""))
    lv = ENV_LEVEL.get(env, 0)
    if target is not None and lv >= 4:
        done = [canon(s, STAGE_ALIAS, STAGES) for s in plan.get("done_stages") or []]
        if target not in done:
            bad.append("\u65b0\u76ee\u6807\u300c%s\u300d\u76f4\u63a5\u5728\u300c%s\u300d\u8d77\u6b65\uff1a\u6839\u672c\u6c92\u8fbe\u6807\u5c31\u76f4\u63a5\u4e0a\u9ad8\u5e72\u6270\u73af\u5883\u5fc5\u7136\u5931\u7075\uff1b"
                       "\u5e94\u4ece\u5ba4\u5185\u5b89\u9759\u8d77\u6b65\u9010\u7ea7\u9012\u8fdb" % (target, env))

    if bad:
        verdict = "\u5148\u5904\u7406"
    elif miss:
        verdict = "\u5f85\u786e\u8ba4"
    else:
        verdict = "\u53ef\u7167\u6b64\u6267\u884c"
    return {"verdict": verdict, "bad": bad, "warn": warn, "miss": miss}


def render(plan, res):
    lines = []
    lines.append("# \u5ba0\u7269\u72d7\u8bad\u7ec3\u8ba1\u5212\u6838\u5bf9\u7ed3\u679c")
    lines.append("")
    lines.append("\u76ee\u6807\uff1a%s \uff5c \u6708\u9f84\uff1a%s \uff5c \u5355\u6b21\uff1a%s \u5206\u949f \uff5c \u6bcf\u65e5\uff1a%s \u6b21" % (
        plan.get("target", "-"), plan.get("age_months", "-"),
        plan.get("minutes_per_session", "-"), plan.get("sessions_per_day", "-")))
    lines.append("")
    lines.append("\u7ed3\u8bba\uff1a**%s**" % res["verdict"])
    lines.append("")
    if res["bad"]:
        lines.append("## \u4e0d\u5408\u683c\u9879\uff08\u5fc5\u987b\u6539\u65b9\u6848\u540e\u518d\u5b9e\u65bd\uff09")
        for x in res["bad"]:
            lines.append("- %s" % x)
        lines.append("")
    if res["miss"]:
        lines.append("## \u5f85\u786e\u8ba4\u9879\uff08\u4fe1\u606f\u4e0d\u8db3\uff09")
        for x in res["miss"]:
            lines.append("- %s" % x)
        lines.append("")
    if res["warn"]:
        lines.append("## \u63d0\u793a\u9879")
        for x in res["warn"]:
            lines.append("- %s" % x)
        lines.append("")
    if not res["bad"] and not res["miss"]:
        lines.append("\u672a\u53d1\u73b0\u7981\u7528\u624b\u6bb5\uff0c\u65f6\u957f\u3001\u9891\u6b21\u3001\u5956\u52b1\u65f6\u673a\u5747\u5728\u53e3\u5f84\u5185\uff0c\u524d\u7f6e\u9636\u6bb5\u5df2\u8fbe\u6807\u3002"
                     "\u8bad\u7ec3\u4e2d\u51fa\u73b0\u8214\u5634\u3001\u6253\u54c8\u6b20\u3001\u8f6c\u5934\u3001\u8db4\u4e0b\u4e0d\u52a8\u7b49\u538b\u529b\u4fe1\u53f7\u5e94\u7acb\u5373\u505c\u6b62\u672c\u6b21\u8bad\u7ec3\u3002")
    lines.append("")
    lines.append("\u6ce8\uff1a\u672c\u7ed3\u679c\u4e3a\u5bb6\u5ead\u57fa\u7840\u670d\u4ece\u8bad\u7ec3\u7684\u8ba1\u5212\u6838\u5bf9\uff0c\u4e0d\u6784\u6210\u517d\u533b\u8bca\u7597\u6216\u4e13\u4e1a\u8bad\u72ac\u610f\u89c1\u3002")
    return "\n".join(lines) + "\n"


def write_out(text, name="_last_result.txt"):
    p = os.path.join(HEREDIR, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


def selftest():
    ok = 0
    fail = []

    def check_case(name, cond, extra=""):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fail.append(name + (" -> " + extra if extra else ""))

    base = {
        "age_months": 24, "minutes_per_session": 15, "sessions_per_day": 2,
        "target": "\u5750\u4e0b", "done_stages": ["\u6ce8\u610f\u529b"], "marker_established": True,
        "reward_delay_sec": 1.0, "repeat_on_fail": 3,
        "tools": ["\u54cd\u7247", "\u96f6\u98df\u5305", "\u80f8\u80cc\u5e26"], "methods": ["\u6b63\u5f3a\u5316"],
        "env": "\u5ba4\u5185\u5b89\u9759", "punish_recall": False,
    }

    # 1 \u6b63\u4f8b
    r = check(dict(base))
    check_case("\u6b63\u4f8b\u5e94\u5224\u53ef\u7167\u6b64\u6267\u884c", r["verdict"] == "\u53ef\u7167\u6b64\u6267\u884c", str(r))

    # 2 \u53cd\u4f8b\uff1a\u7981\u7528\u5668\u5177\u7535\u51fb\u9879\u5708
    bad_tool = dict(base, tools=["\u54cd\u7247", "\u7535\u51fb\u9879\u5708"])
    r = check(bad_tool)
    check_case("\u53cd\u4f8b-\u7535\u51fb\u9879\u5708\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))
    check_case("\u53cd\u4f8b-\u7535\u51fb\u9879\u5708\u5e94\u7ed9\u51fa\u66ff\u4ee3\u505a\u6cd5",
               any("\u80f8\u80cc\u5e26" in x for x in r["bad"]))

    # 3 \u53cd\u4f8b\uff1a\u53ec\u56de\u540e\u60e9\u7f5a
    bad_recall = dict(base, punish_recall=True)
    r = check(bad_recall)
    check_case("\u53cd\u4f8b-\u53ec\u56de\u540e\u60e9\u7f5a\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 4 \u53cd\u4f8b\uff1a\u5355\u6b21\u65f6\u957f\u8d85\u4e0a\u9650
    bad_min = dict(base, minutes_per_session=35)
    r = check(bad_min)
    check_case("\u53cd\u4f8b-\u5355\u6b2135\u5206\u949f\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 5 \u53cd\u4f8b\uff1a\u5956\u52b1\u5ef6\u8fdf\u8fc7\u957f
    bad_delay = dict(base, reward_delay_sec=4.0)
    r = check(bad_delay)
    check_case("\u53cd\u4f8b-\u5956\u52b1\u5ef6\u8fdf4\u79d2\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 6 \u53cd\u4f8b\uff1a\u8df3\u6b65\uff08\u76ee\u6807\u53ec\u56de\u4f46\u524d\u7f6e\u672a\u5b8c\u6210\uff09
    bad_skip = dict(base, target="\u53ec\u56de", done_stages=["\u6ce8\u610f\u529b"],
                    env="\u5ba4\u5185\u5b89\u9759", minutes_per_session=15, sessions_per_day=2)
    r = check(bad_skip)
    check_case("\u53cd\u4f8b-\u53ec\u56de\u7f3a\u524d\u7f6e\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))
    check_case("\u53cd\u4f8b-\u8df3\u6b65\u5e94\u70b9\u540d\u7f3a\u54ea\u4e2a\u9636\u6bb5", any("\u8db4\u4e0b" in x for x in r["bad"]))

    # 7 \u53cd\u4f8b\uff1a\u672a\u5efa\u7acb\u6807\u8bb0
    bad_marker = dict(base, marker_established=False)
    r = check(bad_marker)
    check_case("\u53cd\u4f8b-\u672a\u5efa\u7acb\u6807\u8bb0\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 8 \u53cd\u4f8b\uff1a\u65b0\u76ee\u6807\u76f4\u63a5\u4e0a\u6237\u5916\u9ad8\u5e72\u6270
    bad_env = dict(base, env="\u6237\u5916\u9ad8\u5e72\u6270")
    r = check(bad_env)
    check_case("\u53cd\u4f8b-\u65b0\u76ee\u6807\u76f4\u63a5\u6237\u5916\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 9 \u53cd\u4f8b\uff1a\u91cd\u590d 10 \u6b21
    bad_rep = dict(base, repeat_on_fail=10)
    r = check(bad_rep)
    check_case("\u53cd\u4f8b-\u91cd\u590d10\u6b21\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 10 \u5e7c\u72ac\u53e3\u5f84\uff1a\u6210\u72ac\u53ef\u884c\u7684 15 \u5206\u949f\u5728\u5e7c\u72ac\u4e0b\u5fc5\u987b\u8d85\u4e0a\u9650
    bad_puppy = dict(base, age_months=4, minutes_per_session=15)
    r = check(bad_puppy)
    check_case("\u53cd\u4f8b-\u5e7c\u72ac15\u5206\u949f\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 11 \u7f3a\u9879 -> \u5f85\u786e\u8ba4
    incom = dict(base)
    del incom["tools"]
    r = check(incom)
    check_case("\u7f3a\u975e\u5173\u952e\u5b57\u6bb5\u4e14\u65e0\u7f3a\u9677\u65f6\u4ecd\u53ef\u5224\u53ef\u7167\u6b64\u6267\u884c", r["verdict"] == "\u53ef\u7167\u6b64\u6267\u884c", str(r))
    incom2 = dict(base)
    del incom2["age_months"]
    r = check(incom2)
    check_case("\u7f3a\u6708\u9f84\u5e94\u5224\u5f85\u786e\u8ba4", r["verdict"] == "\u5f85\u786e\u8ba4", str(r))

    # 12 \u5224\u5b9a\u987a\u5e8f\uff1a\u65e2\u6709\u7f3a\u9879\u53c8\u6709\u7f3a\u9677\u65f6\u5fc5\u987b\u5148\u5904\u7406
    both = dict(base, tools=["\u7535\u51fb\u9879\u5708"])
    del both["age_months"]
    r = check(both)
    check_case("\u7f3a\u9677\u4f18\u5148\u4e8e\u7f3a\u9879", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 13 UTF-8 BOM \u8f93\u5165\u5fc5\u987b\u80fd\u88ab\u6b63\u786e\u5904\u7406
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "plan.json")
        with open(p, "w", encoding="utf-8-sig") as f:
            json.dump(dict(base), f, ensure_ascii=False)
        with open(p, "rb") as f:
            head = f.read(3)
        check_case("\u6837\u4f8b\u6587\u4ef6\u786e\u5b9e\u5e26BOM", head == b"\xef\xbb\xbf")
        r = check(load_plan(p))
        check_case("\u5e26BOM\u6587\u4ef6\u5e94\u6b63\u5e38\u89e3\u6790\u5e76\u5224\u53ef\u7167\u6b64\u6267\u884c", r["verdict"] == "\u53ef\u7167\u6b64\u6267\u884c", str(r))

        # 14 BOM + \u53cd\u4f8b\u4ecd\u5fc5\u987b\u5224\u4e0d\u5408\u683c
        p2 = os.path.join(td, "bad.json")
        with open(p2, "w", encoding="utf-8-sig") as f:
            json.dump(dict(bad_recall), f, ensure_ascii=False)
        r = check(load_plan(p2))
        check_case("\u5e26BOM\u53cd\u4f8b\u4ecd\u5224\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 15 \u6392\u5e8f\u65b9\u5411\u9501\u5b9a\uff1a\u9636\u6bb5\u5e8f\u53f7\u5fc5\u987b\u9012\u589e\uff0cPREREQ \u7684\u5c42\u7ea7\u4e0d\u80fd\u5012\u6302
    seq = [STAGES.index(x) for x in ["\u6ce8\u610f\u529b", "\u5750\u4e0b", "\u8db4\u4e0b", "\u7b49\u5f85", "\u968f\u884c", "\u53ec\u56de"]]
    check_case("\u9636\u6bb5\u5e8f\u53f7\u5e94\u9012\u589e\u4e14\u7b49\u4e8e\u6392\u5e8f\u7ed3\u679c",
               seq == sorted(seq) and seq == [0, 1, 2, 3, 4, 5])
    check_case("\u53ec\u56de\u7684\u524d\u7f6e\u5e94\u5305\u542b\u968f\u884c", "\u968f\u884c" in PREREQ["\u53ec\u56de"])

    lines = ["SELFTEST OK (%d passed, 0 failed)" % ok]
    if fail:
        lines = ["SELFTEST FAILED (%d passed, %d failed)" % (ok, len(fail))]
        lines += ["- " + x for x in fail]
    write_out("\n".join(lines) + "\n", "_selftest_result.txt")
    print("\n".join(lines))
    return 0 if not fail else 1


def main():
    ap = argparse.ArgumentParser(description="\u5ba0\u7269\u72d7\u57fa\u7840\u670d\u4ece\u8bad\u7ec3\u8ba1\u5212\u6821\u9a8c")
    ap.add_argument("--file", help="\u8bad\u7ec3\u8ba1\u5212 json \u6587\u4ef6\u8def\u5f84")
    ap.add_argument("--selftest", action="store_true", help="\u8fd0\u884c\u81ea\u68c0")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.file:
        ap.print_help()
        return 2
    plan = load_plan(a.file)
    res = check(plan)
    p = write_out(render(plan, res))
    print("\u7ed3\u679c\u5df2\u5199\u5165: %s" % p)
    print("\u7ed3\u8bba: %s" % res["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
