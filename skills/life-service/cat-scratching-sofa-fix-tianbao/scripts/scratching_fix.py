# -*- coding: utf-8 -*-
"""\u732b\u6293\u5bb6\u5177\u5f15\u5bfc\u65b9\u6848\u6821\u9a8c\u811a\u672c\u3002

\u8bfb\u5165\u4e00\u4efd\u65b9\u6848\u7684 json\uff0c\u6838\u5bf9\uff1a
  1. \u6293\u5177\u603b\u6570\u662f\u5426\u6ee1\u8db3\u732b\u6570\u52a0\u4e00
  2. \u6309\u88ab\u6293\u5bf9\u8c61\u5224\u65ad\u6240\u9700\u5f62\u6001\uff08\u7acb\u9762\u3001\u5e73\u9762\u3001\u9ad8\u7acb\u9762\uff09\u662f\u5426\u914d\u9f50
  3. \u7acb\u5f0f\u6293\u5177\u9ad8\u5ea6\u662f\u5426\u8db3\u591f
  4. \u65b0\u6293\u5177\u5230\u539f\u6293\u70b9\u7684\u8ddd\u79bb\u662f\u5426\u5728\u8f6c\u79fb\u6709\u6548\u8303\u56f4\u5185
  5. \u6293\u5177\u662f\u5426\u7a33\u56fa
  6. \u662f\u5426\u4f7f\u7528\u4e86\u7981\u6b62\u505a\u6cd5
  7. \u6307\u7532\u4fee\u526a\u95f4\u9694\u662f\u5426\u5728\u5468\u671f\u5185

\u7ed3\u8bba\u5206\u4e09\u6863\uff1a\u5148\u5904\u7406 / \u5f85\u786e\u8ba4 / \u53ef\u7167\u6b64\u6267\u884c\u3002
\u5224\u5b9a\u987a\u5e8f\u56fa\u5b9a\uff1a\u5148\u770b\u771f\u5b9e\u7f3a\u9677\uff0c\u518d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574\u3002

\u7528\u6cd5:
  python scratching_fix.py --selftest
  python scratching_fix.py --file plan.json
"""
import argparse
import json
import os
import sys

HEREDIR = os.path.dirname(os.path.abspath(__file__))

TARGET_FORM = {
    "\u6c99\u53d1\u6276\u624b": "\u7acb\u9762", "\u684c\u817f": "\u7acb\u9762", "\u95e8\u6846": "\u7acb\u9762", "\u6905\u5b50\u817f": "\u7acb\u9762",
    "\u7a97\u5e18": "\u9ad8\u7acb\u9762", "\u5899\u9762": "\u9ad8\u7acb\u9762", "\u4e66\u67dc\u8fb9": "\u9ad8\u7acb\u9762",
    "\u5730\u6bef": "\u5e73\u9762", "\u5730\u57ab": "\u5e73\u9762", "\u5e8a\u6cbf": "\u5e73\u9762", "\u6c99\u53d1\u5750\u9762": "\u5e73\u9762",
    "\u7eb8\u7bb1": "\u5e73\u9762", "\u88ab\u5b50": "\u5e73\u9762",
}
FORM_NEED = {"\u7acb\u9762": "\u7acb\u5f0f", "\u9ad8\u7acb\u9762": "\u7acb\u5f0f", "\u5e73\u9762": "\u5e73\u653e"}

MATERIAL = ["\u5251\u9ebb", "\u74e6\u695e\u7eb8", "\u5730\u6bef\u9762", "\u9ebb\u5e03\u9762"]
MATERIAL_ALIAS = {"\u5251\u9ebb\u7ef3": "\u5251\u9ebb", "\u9ebb\u7ef3": "\u5251\u9ebb", "\u7eb8\u8d28": "\u74e6\u695e\u7eb8",
                  "\u7eb8\u7bb1\u6293\u677f": "\u74e6\u695e\u7eb8", "\u5730\u6bef": "\u5730\u6bef\u9762", "\u9ebb\u5e03": "\u9ebb\u5e03\u9762"}
PREFER_MATERIAL = {
    "\u5730\u6bef": "\u5730\u6bef\u9762", "\u5730\u57ab": "\u5730\u6bef\u9762", "\u7eb8\u7bb1": "\u74e6\u695e\u7eb8", "\u88ab\u5b50": "\u74e6\u695e\u7eb8",
    "\u7a97\u5e18": "\u5251\u9ebb", "\u5899\u9762": "\u5251\u9ebb", "\u4e66\u67dc\u8fb9": "\u5251\u9ebb",
}

BAN_METHOD = ["\u4f53\u7f5a", "\u8ffd\u6253", "\u55b7\u6c34", "\u55b7\u96fe", "\u6050\u5413", "\u9632\u6293\u5957", "\u9664\u722a", "\u6447\u7f50"]
MILD_METHOD = ["\u6c14\u5473\u5f15\u5bfc", "\u4e34\u65f6\u906e\u6321", "\u5f53\u573a\u5956\u52b1", "\u5b9a\u671f\u4fee\u526a", "\u6e10\u8fdb\u64a4\u9664"]

HEIGHT_NEED = {"\u5c0f\u732b": 40, "\u6210\u732b": 60}
MAX_DISTANCE = 50
TRIM_MAX = 21
TRIM_MIN = 7
REQUIRED = ["cat_count", "total_posts", "damage_targets", "distance_cm", "methods"]


def norm(s):
    return str(s).strip().replace(" ", "").replace("\u3000", "")


def load_plan(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def canon_material(value):
    n = norm(value)
    if n in MATERIAL:
        return n
    return MATERIAL_ALIAS.get(n)


def check(plan):
    bad = []
    warn = []
    miss = []

    for k in REQUIRED:
        if k not in plan or plan[k] in ("", None):
            miss.append("\u7f3a\u5c11\u5fc5\u586b\u5b57\u6bb5 %s" % k)

    try:
        cats = int(plan.get("cat_count"))
    except (TypeError, ValueError):
        cats = None
        miss.append("\u732b\u7684\u6570\u91cf\u65e0\u6cd5\u89e3\u6790\u4e3a\u6574\u6570")

    try:
        total = int(plan.get("total_posts"))
    except (TypeError, ValueError):
        total = None
        miss.append("\u6293\u5177\u603b\u6570\u65e0\u6cd5\u89e3\u6790\u4e3a\u6574\u6570")

    targets = [norm(x) for x in (plan.get("damage_targets") or [])]
    unknown = [t for t in targets if t not in TARGET_FORM]
    if unknown:
        miss.append("\u88ab\u6293\u5bf9\u8c61 %s \u65e0\u6cd5\u8bc6\u522b\uff0c\u5e94\u5728 %s \u53d6\u503c" % (
            "/".join(unknown), "/".join(TARGET_FORM.keys())))

    # 1 \u6570\u91cf\uff1a\u732b\u6570\u52a0\u4e00
    if cats is not None and total is not None:
        need = cats + 1
        if total < need:
            bad.append("\u6293\u5177\u603b\u6570 %d \u5904\u5c11\u4e8e\u732b\u6570\u52a0\u4e00\u6240\u9700\u7684 %d \u5904\uff1a\u732b\u6ca1\u6709\u4efb\u4f55\u522b\u7684\u9009\u62e9\uff0c"
                       "\u5b83\u53ea\u80fd\u7ee7\u7eed\u6293\u5bb6\u5177\uff1b\u81f3\u5c11\u8981\u52a0\u5230 %d \u5904\u5e76\u5206\u6563\u5728\u4e0d\u540c\u623f\u95f4" % (total, need, need))

    # 2 \u5f62\u6001\uff1a\u6309\u88ab\u6293\u5bf9\u8c61\u53cd\u63a8\u9700\u8981\u54ea\u4e9b\u5f62\u6001
    need_form = set()
    for t in targets:
        if t in TARGET_FORM:
            need_form.add(FORM_NEED[TARGET_FORM[t]])
    if "\u7acb\u5f0f" in need_form and not plan.get("vertical_exists"):
        bad.append("\u88ab\u6293\u5bf9\u8c61\u542b\u7acb\u9762\u5f62\u6001\uff08%s\uff09\uff0c\u4f46\u65b9\u6848\u91cc\u6ca1\u6709\u7acb\u5f0f\u6293\u5177\uff1a"
                   "\u732b\u7ad9\u7acb\u62c9\u4f38\u7684\u9700\u6c42\u65e0\u6cd5\u88ab\u5e73\u653e\u6293\u677f\u6ee1\u8db3\uff0c\u5b83\u4f1a\u7ed5\u8fc7\u6293\u677f\u7ee7\u7eed\u6293\u5bb6\u5177" % (
                       "/".join([t for t in targets
                                 if TARGET_FORM.get(t) in ("\u7acb\u9762", "\u9ad8\u7acb\u9762")]) or "\u7acb\u9762\u5bb6\u5177"))
    if "\u5e73\u653e" in need_form and not plan.get("flat_exists"):
        bad.append("\u88ab\u6293\u5bf9\u8c61\u542b\u5e73\u9762\u5f62\u6001\uff0c\u4f46\u65b9\u6848\u91cc\u6ca1\u6709\u5e73\u653e\u6293\u677f\uff1a"
                   "\u52a0\u7acb\u5f0f\u6293\u67f1\u5bf9\u6293\u5730\u6bef\u5b8c\u5168\u6ca1\u6709\u4f5c\u7528\uff0c\u5fc5\u987b\u914d\u5e73\u653e\u6293\u677f\u5e76\u538b\u5728\u88ab\u6293\u5904")

    # 3 \u7acb\u5f0f\u9ad8\u5ea6
    if plan.get("vertical_exists"):
        try:
            h = float(plan.get("vertical_height_cm"))
        except (TypeError, ValueError):
            miss.append("\u7acb\u5f0f\u6293\u5177\u9ad8\u5ea6\u7f3a\u5931\u6216\u65e0\u6cd5\u89e3\u6790")
            h = None
        if h is not None:
            need_h = HEIGHT_NEED["\u5c0f\u732b"] if (plan.get("cat_age") == "\u5c0f\u732b") else HEIGHT_NEED["\u6210\u732b"]
            if h < need_h:
                bad.append("\u7acb\u5f0f\u6293\u5177\u9ad8\u5ea6 %.0f \u5398\u7c73\u4f4e\u4e8e %d \u5398\u7c73\uff1a\u9ad8\u5ea6\u4e0d\u591f\u65f6\u732b\u65e0\u6cd5\u5b8c\u6210\u7ad9\u7acb\u6293\u4f38\uff0c"
                           "\u5b83\u4f1a\u8df3\u8fc7\u8fd9\u4e2a\u6293\u5177\uff1b\u6b63\u786e\u505a\u6cd5\u662f\u8ba9\u5b83\u7ad9\u7740\u6293\u4e00\u6b21\uff0c"
                           "\u91cf\u524d\u722a\u6700\u9ad8\u70b9\u5230\u5730\u9762\u518d\u52a0 10 \u5398\u7c73" % (h, need_h))

    # 4 \u8f6c\u79fb\u8ddd\u79bb
    try:
        dist = float(plan.get("distance_cm"))
        if dist > MAX_DISTANCE:
            bad.append("\u65b0\u6293\u5177\u5230\u539f\u6293\u70b9 %.0f \u5398\u7c73\u8d85\u8fc7 %d \u5398\u7c73\u53e3\u5f84\uff1a"
                       "\u8fd9\u662f\u6574\u5957\u65b9\u6848\u91cc\u6700\u5bb9\u6613\u505a\u9519\u7684\u4e00\u9879\uff0c\u8ddd\u79bb\u8fc7\u8fdc\u65f6\u8f6c\u79fb\u57fa\u672c\u5931\u8d25\uff0c"
                       "\u4e14\u5e38\u88ab\u8bef\u5224\u6210\u732b\u4e0d\u559c\u6b22\u65b0\u6293\u5177" % (dist, MAX_DISTANCE))
        elif dist < 0:
            bad.append("\u8f6c\u79fb\u8ddd\u79bb\u4e3a\u8d1f\u6570\uff0c\u6570\u636e\u65e0\u6548")
    except (TypeError, ValueError):
        pass

    # 5 \u7a33\u5b9a\u6027
    if plan.get("stable") is False:
        bad.append("\u6293\u5177\u4e0d\u591f\u7a33\u56fa\uff1a\u732b\u7ad9\u7acb\u62c9\u4f38\u65f6\u91cd\u5fc3\u524d\u79fb\uff0c\u6643\u8fc7\u4e00\u6b21\u7684\u6293\u5177\u901a\u5e38\u88ab\u6c38\u4e45\u653e\u5f03\uff0c"
                   "\u8fd9\u4e00\u9879\u6ca1\u6709\u300c\u518d\u8bd5\u8bd5\u300d\u7684\u673a\u4f1a")

    # 6 \u7981\u6b62\u505a\u6cd5
    methods = [norm(m) for m in (plan.get("methods") or [])]
    hit = []
    for m in methods:
        for b in BAN_METHOD:
            if b in m:
                hit.append(b)
    for h in sorted(set(hit)):
        if h in ("\u4f53\u7f5a", "\u8ffd\u6253", "\u55b7\u6c34", "\u55b7\u96fe", "\u6050\u5413", "\u6447\u7f50"):
            bad.append("\u4f7f\u7528\u4e86\u7981\u6b62\u505a\u6cd5\u300c%s\u300d\uff1a\u53ea\u5728\u4eba\u5728\u65f6\u6709\u6548\u4e14\u5236\u9020\u5bf9\u4eba\u7684\u6050\u60e7\uff0c\u4e00\u51fa\u95e8\u7167\u6293\u4e0d\u8bef\uff1b"
                       "\u5e94\u6539\u7528\u4e34\u65f6\u906e\u6321\u52a0\u8f6c\u79fb\u671f\u4fdd\u62a4" % h)
        elif h == "\u9632\u6293\u5957":
            bad.append("\u4f7f\u7528\u4e86\u300c\u9632\u6293\u5957\u300d\uff1a\u957f\u671f\u4f69\u6234\u5f71\u54cd\u722a\u7684\u6b63\u5e38\u4f38\u7f29\u4e0e\u65e7\u722a\u9798\u8131\u843d\uff0c"
                       "\u4e14\u6293\u6320\u52a8\u4f5c\u7167\u505a\u5bb6\u5177\u7167\u635f\uff1b\u5e94\u6539\u4e3a\u5b9a\u671f\u4fee\u526a\u52a0\u63d0\u4f9b\u5145\u8db3\u6293\u5177\uff0c"
                       "\u786e\u6709\u4f7f\u7528\u5fc5\u8981\u65f6\u8bf7\u54a8\u8be2\u517d\u533b")
        elif h == "\u9664\u722a":
            bad.append("\u65b9\u6848\u6d89\u53ca\u9664\u722a\u624b\u672f\uff1a\u5c5e\u624b\u672f\u6027\u5904\u7f6e\uff0c\u6d89\u53ca\u75bc\u75db\u3001\u884c\u8d70\u6539\u53d8\u4e0e\u884c\u4e3a\u6076\u5316\u98ce\u9669\uff0c"
                       "\u4e14\u591a\u5730\u5df2\u9650\u5236\uff1b\u8bf7\u52a1\u5fc5\u5148\u5411\u517d\u533b\u5145\u5206\u54a8\u8be2")

    # 7 \u6307\u7532\u4fee\u526a\u5468\u671f
    trim = plan.get("nail_trim_days")
    if trim is not None:
        try:
            td = int(trim)
            if td > TRIM_MAX:
                bad.append("\u6307\u7532\u4fee\u526a\u95f4\u9694 %d \u5929\u8d85\u8fc7 %d \u5929\u4e0a\u9650\uff1a\u5ba4\u5185\u732b\u6253\u78e8\u4e0d\u8db3\uff0c"
                           "\u6307\u7532\u4f1a\u957f\u5230\u624e\u8fdb\u8089\u57ab" % (td, TRIM_MAX))
            elif td < TRIM_MIN:
                bad.append("\u6307\u7532\u4fee\u526a\u95f4\u9694 %d \u5929\u77ed\u4e8e %d \u5929\uff1a\u8fc7\u4e8e\u9891\u7e41\u5bb9\u6613\u5f15\u53d1\u6297\u62d2\u4e14\u6ca1\u6709\u5fc5\u8981" % (
                    td, TRIM_MIN))
        except (TypeError, ValueError):
            warn.append("\u4fee\u526a\u95f4\u9694\u65e0\u6cd5\u89e3\u6790\u4e3a\u6574\u6570")

    # 8 \u6750\u8d28\u504f\u597d\u662f\u5426\u5927\u81f4\u5339\u914d
    mat = canon_material(plan.get("material", ""))
    if mat is None and plan.get("material"):
        miss.append("\u6293\u9762\u6750\u8d28\u300c%s\u300d\u65e0\u6cd5\u8bc6\u522b\uff0c\u5e94\u5728 %s \u53d6\u503c" % (
            plan.get("material"), "/".join(MATERIAL)))
    for t in targets:
        want = PREFER_MATERIAL.get(t)
        if want and mat and mat != want:
            warn.append("\u88ab\u6293\u5bf9\u8c61\u300c%s\u300d\u901a\u5e38\u5bf9\u5e94\u504f\u597d\u6750\u8d28\u300c%s\u300d\uff0c\u5f53\u524d\u9009\u7684\u662f\u300c%s\u300d\uff1a"
                        "\u5efa\u8bae\u6309\u5b83\u73b0\u5728\u6293\u7684\u4e1c\u897f\u53cd\u63a8\uff0c\u800c\u4e0d\u662f\u6309\u5916\u89c2\u6311" % (t, want, mat))
            break

    if bad:
        verdict = "\u5148\u5904\u7406"
    elif miss:
        verdict = "\u5f85\u786e\u8ba4"
    else:
        verdict = "\u53ef\u7167\u6b64\u6267\u884c"
    return {"verdict": verdict, "bad": bad, "warn": warn, "miss": miss}


def render(plan, res):
    lines = []
    lines.append("# \u732b\u6293\u5bb6\u5177\u5f15\u5bfc\u65b9\u6848\u6838\u5bf9\u7ed3\u679c")
    lines.append("")
    lines.append("\u732b\u6570\uff1a%s \uff5c \u6293\u5177\uff1a%s \u5904 \uff5c \u88ab\u6293\u5bf9\u8c61\uff1a%s" % (
        plan.get("cat_count", "-"), plan.get("total_posts", "-"),
        "/".join(plan.get("damage_targets") or []) or "-"))
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
        lines.append("\u6570\u91cf\u3001\u5f62\u6001\u3001\u9ad8\u5ea6\u3001\u8ddd\u79bb\u3001\u7a33\u5b9a\u6027\u4e0e\u624b\u6bb5\u5747\u5728\u53e3\u5f84\u5185\u3002"
                     "\u6309\u56db\u6b65\u8f6c\u79fb\u6d41\u7a0b\u6267\u884c\uff0c\u56db\u5468\u96f6\u6539\u5584\u65f6\u56de\u5934\u590d\u67e5\u8fd9\u56db\u9879\uff0c\u4e0d\u8981\u53ea\u52a0\u4e00\u4e2a\u6293\u677f\u3002")
    lines.append("")
    lines.append("\u6ce8\uff1a\u672c\u7ed3\u679c\u4e3a\u5bb6\u5ead\u5f15\u5bfc\u65b9\u6848\u6838\u5bf9\uff0c\u4e0d\u6784\u6210\u517d\u533b\u8bca\u7597\u610f\u89c1\u3002")
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
        "cat_count": 2, "total_posts": 3, "vertical_exists": True,
        "vertical_height_cm": 70, "flat_exists": True,
        "damage_targets": ["\u6c99\u53d1\u6276\u624b", "\u5730\u6bef"], "distance_cm": 40,
        "material": "\u5251\u9ebb", "stable": True, "nail_trim_days": 14,
        "methods": ["\u6c14\u5473\u5f15\u5bfc", "\u4e34\u65f6\u906e\u6321", "\u5f53\u573a\u5956\u52b1"], "cat_age": "\u6210\u732b",
    }

    # 1 \u6b63\u4f8b
    r = check(dict(base))
    check_case("\u6b63\u4f8b\u5e94\u5224\u53ef\u7167\u6b64\u6267\u884c", r["verdict"] == "\u53ef\u7167\u6b64\u6267\u884c", str(r))

    # 2 \u53cd\u4f8b\uff1a\u6570\u91cf\u4e0d\u8db3\uff08\u732b\u6570\u52a0\u4e00\u90fd\u4e0d\u5230\uff09
    bad_cnt = dict(base, cat_count=3, total_posts=2)
    r = check(bad_cnt)
    check_case("\u53cd\u4f8b-\u6293\u5177\u6570\u91cf\u4e0d\u8db3\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))
    check_case("\u53cd\u4f8b-\u6570\u91cf\u4e0d\u8db3\u5e94\u70b9\u540d\u9700\u8981\u51e0\u5904", any("4" in x and "\u732b\u6570\u52a0\u4e00" in x for x in r["bad"]))

    # 3 \u53cd\u4f8b\uff1a\u7f3a\u7acb\u5f0f\u4f46\u6709\u7acb\u9762\u88ab\u6293\u5bf9\u8c61
    bad_form = dict(base, vertical_exists=False)
    r = check(bad_form)
    check_case("\u53cd\u4f8b-\u7f3a\u7acb\u5f0f\u6293\u5177\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 4 \u53cd\u4f8b\uff1a\u7f3a\u5e73\u653e\u4f46\u6709\u5730\u6bef\u88ab\u6293
    bad_flat = dict(base, flat_exists=False, damage_targets=["\u5730\u6bef"])
    r = check(bad_flat)
    check_case("\u53cd\u4f8b-\u7f3a\u5e73\u653e\u6293\u677f\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 5 \u53cd\u4f8b\uff1a\u7acb\u5f0f\u9ad8\u5ea6\u4e0d\u8db3
    bad_h = dict(base, vertical_height_cm=35)
    r = check(bad_h)
    check_case("\u53cd\u4f8b-\u9ad8\u5ea635\u5398\u7c73\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 6 \u53cd\u4f8b\uff1a\u8f6c\u79fb\u8ddd\u79bb\u8fc7\u8fdc
    bad_d = dict(base, distance_cm=180)
    r = check(bad_d)
    check_case("\u53cd\u4f8b-\u8ddd\u79bb180\u5398\u7c73\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 7 \u53cd\u4f8b\uff1a\u4f7f\u7528\u4e86\u7981\u6b62\u505a\u6cd5\u55b7\u6c34
    bad_spray = dict(base, methods=["\u6c14\u5473\u5f15\u5bfc", "\u55b7\u6c34"])
    r = check(bad_spray)
    check_case("\u53cd\u4f8b-\u55b7\u6c34\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))
    check_case("\u53cd\u4f8b-\u55b7\u6c34\u5e94\u7ed9\u66ff\u4ee3\u505a\u6cd5", any("\u4e34\u65f6\u906e\u6321" in x for x in r["bad"]))

    # 8 \u53cd\u4f8b\uff1a\u6d89\u53ca\u9664\u722a\u624b\u672f
    bad_dec = dict(base, methods=["\u6c14\u5473\u5f15\u5bfc", "\u9664\u722a\u624b\u672f"])
    r = check(bad_dec)
    check_case("\u53cd\u4f8b-\u9664\u722a\u624b\u672f\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 9 \u53cd\u4f8b\uff1a\u4fee\u526a\u95f4\u9694\u8fc7\u957f
    bad_trim = dict(base, nail_trim_days=45)
    r = check(bad_trim)
    check_case("\u53cd\u4f8b-\u4fee\u526a\u95f4\u969445\u5929\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 10 \u53cd\u4f8b\uff1a\u6293\u5177\u4e0d\u7a33
    bad_stable = dict(base, stable=False)
    r = check(bad_stable)
    check_case("\u53cd\u4f8b-\u6293\u5177\u4e0d\u7a33\u56fa\u5e94\u4e3a\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 11 \u7f3a\u9879 -> \u5f85\u786e\u8ba4
    incom = dict(base)
    del incom["distance_cm"]
    r = check(incom)
    check_case("\u7f3a\u8ddd\u79bb\u5e94\u5224\u5f85\u786e\u8ba4", r["verdict"] == "\u5f85\u786e\u8ba4", str(r))

    # 12 \u65e0\u6cd5\u8bc6\u522b\u7684\u88ab\u6293\u5bf9\u8c61 -> \u5f85\u786e\u8ba4
    unknown = dict(base, damage_targets=["\u51b0\u7bb1\u95e8"])
    r = check(unknown)
    check_case("\u672a\u77e5\u88ab\u6293\u5bf9\u8c61\u5e94\u51fa\u73b0\u5728\u5f85\u786e\u8ba4", any("\u65e0\u6cd5\u8bc6\u522b" in x for x in r["miss"]), str(r))

    # 13 \u5224\u5b9a\u987a\u5e8f\uff1a\u65e2\u6709\u7f3a\u9879\u53c8\u6709\u7f3a\u9677\u65f6\u5fc5\u987b\u5148\u5904\u7406
    both = dict(base, distance_cm=200)
    del both["material"]
    r = check(both)
    check_case("\u7f3a\u9677\u4f18\u5148\u4e8e\u7f3a\u9879", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 14 UTF-8 BOM \u8f93\u5165\u5fc5\u987b\u80fd\u88ab\u6b63\u786e\u5904\u7406
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

        # 15 BOM + \u53cd\u4f8b\u4ecd\u5fc5\u987b\u5224\u4e0d\u5408\u683c
        p2 = os.path.join(td, "bad.json")
        with open(p2, "w", encoding="utf-8-sig") as f:
            json.dump(dict(bad_spray), f, ensure_ascii=False)
        r = check(load_plan(p2))
        check_case("\u5e26BOM\u53cd\u4f8b\u4ecd\u5224\u5148\u5904\u7406", r["verdict"] == "\u5148\u5904\u7406", str(r))

    # 16 \u6750\u8d28\u522b\u540d\u89e3\u6790
    check_case("\u6750\u8d28\u522b\u540d\u5e94\u80fd\u89e3\u6790", canon_material("\u5251\u9ebb\u7ef3") == "\u5251\u9ebb")

    # 17 \u6392\u5e8f\u65b9\u5411\u9501\u5b9a\uff1a\u9ad8\u5ea6\u9700\u6c42\u4e2d\u6210\u732b\u5fc5\u987b\u9ad8\u4e8e\u5c0f\u732b
    check_case("\u6210\u732b\u9ad8\u5ea6\u9700\u6c42\u5e94\u9ad8\u4e8e\u5c0f\u732b", HEIGHT_NEED["\u6210\u732b"] > HEIGHT_NEED["\u5c0f\u732b"])

    lines = ["SELFTEST OK (%d passed, 0 failed)" % ok]
    if fail:
        lines = ["SELFTEST FAILED (%d passed, %d failed)" % (ok, len(fail))]
        lines += ["- " + x for x in fail]
    write_out("\n".join(lines) + "\n", "_selftest_result.txt")
    print("\n".join(lines))
    return 0 if not fail else 1


def main():
    ap = argparse.ArgumentParser(description="\u732b\u6293\u5bb6\u5177\u5f15\u5bfc\u65b9\u6848\u6821\u9a8c")
    ap.add_argument("--file", help="\u65b9\u6848 json \u6587\u4ef6\u8def\u5f84")
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

