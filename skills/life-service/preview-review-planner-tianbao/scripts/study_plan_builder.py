# -*- coding: utf-8 -*-
"""\u5b66\u4e60\u8ba1\u5212\u6392\u671f + \u56db\u680f\u5b57\u6bb5\u6821\u9a8c + \u5931\u8d25\u5f52\u7c7b\u3002\u6807\u51c6\u5e93\u3002

\u7528\u6cd5:
  python study_plan_builder.py --file plan.json
  python study_plan_builder.py --selftest
"""

import argparse
import json
import os
import sys

RESULT_FILE = "_selftest_result.txt"

REQUIRED_FIELDS = ["title", "minutes", "priority", "done_criteria"]
DEFAULT_NODES = [0, 2, 7, 21]

VAGUE_WORDS = ["\u590d\u4e60", "\u9884\u4e60", "\u770b\u4e66", "\u5b66\u4e60", "\u5237\u9898", "\u770b\u4e00\u4e0b", "\u8fc7\u4e00\u904d"]
CONCRETE_FAILURES = {
    "plan_overload": "\u8ba1\u5212\u8fc7\u6ee1\uff1a\u6309\u4e0a\u5468\u5b9e\u9645\u5b8c\u6210\u7387\u6253\u6298\u5e76\u7559\u51fa\u7f13\u51b2",
    "no_execution": "\u53ea\u6392\u4e0d\u6267\u884c\uff1a\u9996\u4efb\u52a1\u7f29\u52305\u523015\u5206\u949f\u5e76\u56fa\u5b9a\u65f6\u95f4\u5730\u70b9",
    "no_criteria": "\u6ca1\u6709\u5b8c\u6210\u6807\u51c6\uff1a\u4e3a\u6bcf\u6761\u4efb\u52a1\u8865\u53ef\u5224\u5b9a\u6807\u51c6",
    "grain_too_big": "\u4efb\u52a1\u7c92\u5ea6\u592a\u5927\uff1a\u62c6\u5230\u5355\u6b21\u4e13\u6ce8\u53ef\u5b8c\u6210",
    "review_squeezed": "\u590d\u4e60\u88ab\u6324\u6389\uff1a\u7ed9\u590d\u4e60\u56fa\u5b9a\u72ec\u7acb\u65f6\u6bb5",
}


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return json.loads(raw.lstrip("\ufeff"))


def check_fields(task):
    """\u8fd4\u56de\u7f3a\u5931\u5b57\u6bb5\u5217\u8868\u3002"""
    return [k for k in REQUIRED_FIELDS if not str(task.get(k) or "").strip()]


def is_vague(title):
    return any(w in (title or "") for w in VAGUE_WORDS) and len(title or "") <= 8


def diagnose(tasks, daily_minutes, total_minutes):
    """\u6309\u56db\u7c7b\u5931\u8d25\u539f\u56e0\u5f52\u7c7b\u3002"""
    hits = []
    if total_minutes > daily_minutes:
        hits.append("plan_overload")
    if any(check_fields(t) for t in tasks):
        if any("done_criteria" in check_fields(t) for t in tasks):
            hits.append("no_criteria")
        if any("minutes" in check_fields(t) for t in tasks):
            hits.append("grain_too_big")
    if not any(check_fields(t) for t in tasks) and total_minutes > daily_minutes * 1.5:
        hits.append("no_execution")
    if not any(str(t.get("field", "")) == "review" for t in tasks):
        hits.append("review_squeezed")
    return hits


def order_tasks(tasks):
    """\u6309\u4f18\u5148\u7ea7\u6392\u5e8f\uff0c\u9ad8\u4f18\u5148\u5728\u524d\u3002"""
    rank = {"\u9ad8": 0, "\u4e2d": 1, "\u4f4e": 2}
    return sorted(
        tasks,
        key=lambda t: (rank.get(str(t.get("priority", "\u4e2d")), 1), -int(t.get("minutes") or 0)),
    )


def build(data):
    tasks = data.get("tasks") or []
    daily = int(data.get("daily_minutes") or 0)
    ordered = order_tasks(tasks)
    total = sum(int(t.get("minutes") or 0) for t in tasks)
    missing = []
    vague = []
    for t in ordered:
        m = check_fields(t)
        if m:
            missing.append({"title": t.get("title", ""), "missing": m})
        if is_vague(t.get("title", "")):
            vague.append(t.get("title", ""))
    hits = diagnose(tasks, daily, total)
    return {
        "daily_minutes": daily,
        "total_minutes": total,
        "overload": total > daily,
        "ordered_tasks": ordered,
        "missing_fields": missing,
        "vague_titles": vague,
        "failure_types": hits,
        "fixes": [CONCRETE_FAILURES[h] for h in hits],
    }


def review_nodes(nodes=None):
    ns = nodes or DEFAULT_NODES
    if not ns:
        raise ValueError("\u590d\u4e60\u8282\u70b9\u4e0d\u80fd\u4e3a\u7a7a")
    return sorted(ns)


def run_file(path, as_json):
    res = build(read_json(path))
    if as_json:
        return json.dumps(res, ensure_ascii=False, indent=2)
    lines = []
    lines.append("\u6bcf\u65e5\u53ef\u7528: %d \u5206\u949f  \u8ba1\u5212\u603b\u91cf: %d \u5206\u949f  \u8d85\u8f7d: %s"
                 % (res["daily_minutes"], res["total_minutes"], "\u662f" if res["overload"] else "\u5426"))
    lines.append("\u6392\u5b9a\u987a\u5e8f:")
    for t in res["ordered_tasks"]:
        lines.append("  [%s] %s (%s\u5206\u949f) \u5b8c\u6210\u6807\u51c6=%s"
                     % (t.get("priority", "\u4e2d"), t.get("title", ""),
                        t.get("minutes", 0), t.get("done_criteria", "\u7f3a\u5931")))
    if res["missing_fields"]:
        lines.append("\u5b57\u6bb5\u7f3a\u5931:")
        for m in res["missing_fields"]:
            lines.append("  %s -> %s" % (m["title"], ",".join(m["missing"])))
    if res["vague_titles"]:
        lines.append("\u4efb\u52a1\u8fc7\u4e8e\u7b3c\u7edf: %s" % ",".join(res["vague_titles"]))
    lines.append("\u5931\u8d25\u5f52\u7c7b:")
    for f in res["fixes"]:
        lines.append("  - %s" % f)
    return "\n".join(lines)


def selftest():
    fails = []

    def ck(name, cond):
        if not cond:
            fails.append(name)

    good = {"title": "\u505a\u5b8c\u7b2c\u4e09\u7ae0\u8bfe\u540e\u98981\u523010\u5e76\u6807\u51fa\u9519\u9898", "minutes": 30,
            "priority": "\u9ad8", "done_criteria": "\u9519\u9898\u6570\u5199\u51fa", "field": "review"}

    ck("t1 \u56db\u680f\u9f50\u5168\u65e0\u7f3a\u5931", check_fields(good) == [])
    ck("t2 \u7f3a\u5b8c\u6210\u6807\u51c6\u88ab\u8bc6\u522b", "done_criteria" in check_fields(dict(good, done_criteria="")))
    ck("t3 \u7f3a\u8017\u65f6\u88ab\u8bc6\u522b", "minutes" in check_fields(dict(good, minutes="")))
    ck("t4 \u7b3c\u7edf\u6807\u9898\u88ab\u8bc6\u522b", is_vague("\u590d\u4e60\u6570\u5b66"))
    ck("t5 \u5177\u4f53\u6807\u9898\u4e0d\u5224\u7b3c\u7edf", not is_vague("\u505a\u5b8c\u8bfe\u540e\u9898\u5e76\u6807\u9519\u9898"))

    tasks = [dict(good, title="\u4efb\u52a1A", priority="\u4f4e"), dict(good, title="\u4efb\u52a1B", priority="\u9ad8")]
    o = order_tasks(tasks)
    ck("t6 \u9ad8\u4f18\u5148\u6392\u5728\u524d\u9762", o[0]["title"] == "\u4efb\u52a1B")

    r = build({"daily_minutes": 60, "tasks": [dict(good, minutes=120)]})
    ck("t7 \u8d85\u8f7d\u88ab\u5224\u5b9a", r["overload"] is True)
    ck("t8 \u8d85\u8f7d\u5f52\u7c7b\u4e3a\u8ba1\u5212\u8fc7\u6ee1", "plan_overload" in r["failure_types"])
    ck("t9 \u7ed9\u51fa\u4fee\u6b63\u52a8\u4f5c", len(r["fixes"]) > 0)

    r2 = build({"daily_minutes": 60, "tasks": [dict(good, done_criteria="")]})
    ck("t10 \u7f3a\u6807\u51c6\u5f52\u7c7b\u6b63\u786e", "no_criteria" in r2["failure_types"])

    r3 = build({"daily_minutes": 60, "tasks": [dict(good, field="new")]})
    ck("t11 \u65e0\u590d\u4e60\u4efb\u52a1\u5f52\u7c7b\u6b63\u786e", "review_squeezed" in r3["failure_types"])

    ck("t12 \u9ed8\u8ba4\u8282\u70b9\u542b\u5f53\u5929", 0 in DEFAULT_NODES)
    ck("t13 \u8282\u70b9\u53ef\u6392\u5e8f", review_nodes([7, 0, 2]) == [0, 2, 7])

    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_case.json")
    with open(tmp, "w", encoding="utf-8-sig") as f:
        json.dump({"daily_minutes": 60, "tasks": []}, f, ensure_ascii=False)
    ck("t14 BOM \u8f93\u5165\u89e3\u6790\u6210\u529f", int(read_json(tmp)["daily_minutes"]) == 60)
    os.remove(tmp)

    ck("t15 \u7a7a\u4efb\u52a1\u5217\u8868\u4e0d\u62a5\u9519", build({"daily_minutes": 30, "tasks": []})["total_minutes"] == 0)

    out = []
    out.append("SELFTEST FAIL: %s" % "; ".join(fails) if fails else "SELFTEST OK  15/15")
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, RESULT_FILE), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="\u5b66\u4e60\u8ba1\u5212\u6392\u671f\u4e0e\u5b57\u6bb5\u6821\u9a8c")
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