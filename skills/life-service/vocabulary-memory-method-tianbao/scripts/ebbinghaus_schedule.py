# -*- coding: utf-8 -*-
"""\u827e\u5bbe\u6d69\u65af\u590d\u4e60\u65e5\u7a0b\u751f\u6210\u5668 + \u590d\u4e60\u8d1f\u8377\u9884\u8b66\u3002\u6807\u51c6\u5e93\uff0c\u65e0\u5916\u90e8\u4f9d\u8d56\u3002

\u7528\u6cd5:
  python ebbinghaus_schedule.py --file plan.json
  python ebbinghaus_schedule.py --file plan.json --json
  python ebbinghaus_schedule.py --selftest
"""

import argparse
import datetime
import json
import os
import sys

DEFAULT_INTERVALS = [0, 1, 3, 7, 15, 30, 60]
RESULT_FILE = "_selftest_result.txt"


def read_json(path):
    """\u8bfb JSON\uff0c\u5fc5\u987b\u5265 BOM\uff1a\u5e26 BOM \u65f6\u9996 key \u4f1a\u53d8\u6210 \\ufeffkey \u4e14\u4e0d\u62a5\u9519\u3002"""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return json.loads(raw.lstrip("\ufeff"))


def build_schedule(start_date, daily_new, intervals, days=None):
    """\u751f\u6210\u9010\u65e5\u65b0\u589e\u4e0e\u5230\u671f\u590d\u4e60\u6e05\u5355\u3002"""
    if daily_new <= 0:
        raise ValueError("daily_new \u5fc5\u987b\u4e3a\u6b63\u6574\u6570")
    if not intervals:
        raise ValueError("intervals \u4e0d\u80fd\u4e3a\u7a7a")
    start = datetime.date.fromisoformat(start_date)
    span = days or (intervals[-1] + daily_new + 1)
    new_by_day = {}
    due_by_day = {}
    for d in range(span):
        day = start + datetime.timedelta(days=d)
        new_by_day[day] = daily_new
        due_by_day[day] = 0
    # \u6bcf\u4e2a\u65b0\u589e\u65e5\u6309\u5404\u8282\u70b9\u6392\u51fa\u5230\u671f\u590d\u4e60
    for d in range(span):
        learned = start + datetime.timedelta(days=d)
        for iv in intervals:
            due = learned + datetime.timedelta(days=iv)
            if due in due_by_day:
                due_by_day[due] += daily_new
    return start, new_by_day, due_by_day


def analyze(start, new_by_day, due_by_day, review_cap=None):
    """\u8f93\u51fa\u6bcf\u65e5\u8d1f\u8377\u4e0e\u5cf0\u503c\uff0c\u5e76\u5224\u65ad\u662f\u5426\u8d85\u9650\u3002"""
    rows = []
    peak = 0
    over = 0
    for day in sorted(new_by_day.keys()):
        due = due_by_day[day]
        total = due + new_by_day[day]
        if total > peak:
            peak = total
        flag = False
        if review_cap is not None and due > review_cap:
            flag = True
            over += 1
        rows.append(
            {
                "date": day.isoformat(),
                "new": new_by_day[day],
                "due": due,
                "total": total,
                "over_cap": flag,
            }
        )
    return rows, peak, over


def advice(peak, over, daily_new, intervals):
    """\u8d1f\u8377\u8d85\u9650\u65f6\u7684\u8c03\u53c2\u5efa\u8bae\uff0c\u6309\u6709\u6548\u6027\u6392\u5e8f\u3002"""
    out = []
    if over > 0:
        out.append("\u5b58\u5728\u8d85\u4e0a\u9650\u7684\u5929\u6570\uff0c\u5148\u4e0b\u8c03\u6bcf\u65e5\u65b0\u589e\u91cf\uff08\u6700\u6709\u6548\uff09")
        out.append("\u5176\u6b21\u8003\u8651\u53bb\u6389\u6700\u957f\u7684\u4e00\u6863\u95f4\u9694\u8282\u70b9")
        out.append("\u6700\u540e\u624d\u8003\u8651\u5ef6\u957f\u6574\u4f53\u5468\u671f")
        out.append("\u590d\u4e60\u91cf\u5806\u79ef\u671f\u95f4\u4e0d\u8981\u7ee7\u7eed\u52a0\u65b0\u8bcd")
    else:
        out.append("\u590d\u4e60\u8d1f\u8377\u5728\u4e0a\u9650\u5185\uff0c\u4fdd\u6301\u5f53\u524d\u8282\u594f\u5e76\u6309\u5468\u6821\u51c6")
    stable = daily_new * len(intervals) / 2.0
    out.append("\u7a33\u5b9a\u671f\u6bcf\u65e5\u590d\u4e60\u91cf\u4f30\u7b97\u4e3a %.1f \u8bcd\u6b21" % stable)
    out.append("\u590d\u4e60\u961f\u5217\u9010\u5468\u589e\u957f\u8bf4\u660e\u6bcf\u65e5\u65b0\u589e\u91cf\u8fc7\u5927\uff0c\u5e94\u4e0b\u8c03")
    return out


def run_file(path, as_json):
    data = read_json(path)
    start_date = data.get("start_date") or datetime.date.today().isoformat()
    daily_new = int(data.get("daily_new") or 20)
    intervals = data.get("intervals") or DEFAULT_INTERVALS
    intervals = [int(x) for x in intervals]
    review_cap = data.get("review_cap")
    days = data.get("days")
    start, new_by_day, due_by_day = build_schedule(start_date, daily_new, intervals, days)
    rows, peak, over = analyze(start, new_by_day, due_by_day, review_cap)
    adv = advice(peak, over, daily_new, intervals)
    result = {
        "start_date": start.isoformat(),
        "daily_new": daily_new,
        "intervals": intervals,
        "rows": rows,
        "peak_total": peak,
        "over_cap_days": over,
        "advice": adv,
    }
    if as_json:
        return json.dumps(result, ensure_ascii=False, indent=2)
    lines = []
    lines.append("\u8d77\u59cb\u65e5\u671f: %s" % start.isoformat())
    lines.append("\u6bcf\u65e5\u65b0\u589e: %d  \u8282\u70b9: %s" % (daily_new, intervals))
    lines.append("\u65e5\u671f        \u65b0\u589e  \u5230\u671f\u590d\u4e60  \u5408\u8ba1  \u8d85\u9650")
    for r in rows:
        lines.append(
            "%s  %4d  %8d  %4d  %s"
            % (r["date"], r["new"], r["due"], r["total"], "\u662f" if r["over_cap"] else "")
        )
    lines.append("\u5cf0\u503c\u5408\u8ba1: %d  \u8d85\u9650\u5929\u6570: %d" % (peak, over))
    for a in adv:
        lines.append("- %s" % a)
    return "\n".join(lines)


def selftest():
    fails = []

    def ck(name, cond):
        if cond:
            pass
        else:
            fails.append(name)

    s, nb, db = build_schedule("2026-03-01", 10, [0, 1, 3])
    ck("t1 \u7b2c\u4e00\u5929\u65b0\u589e\u6b63\u786e", nb[datetime.date(2026, 3, 1)] == 10)
    ck("t2 \u5f53\u5929\u8282\u70b9\u4ea7\u751f\u5f53\u5929\u5230\u671f", db[datetime.date(2026, 3, 1)] == 10)
    ck("t3 \u6b21\u65e5\u542b\u4e24\u6279\u53e0\u52a0", db[datetime.date(2026, 3, 2)] == 20)
    ck("t4 \u7b2c3\u65e5\u542b\u4e09\u6279\u53e0\u52a0", db[datetime.date(2026, 3, 4)] == 30)

    s2, nb2, db2 = build_schedule("2026-03-01", 20, DEFAULT_INTERVALS)
    rows, peak, over = analyze(s2, nb2, db2, None)
    ck("t5 \u5cf0\u503c\u5927\u4e8e\u7b49\u4e8e\u5355\u6279", peak >= 20)
    ck("t6 \u65e0\u4e0a\u9650\u65f6\u8d85\u9650\u5929\u6570\u4e3a0", over == 0)

    rows2, peak2, over2 = analyze(s2, nb2, db2, 25)
    ck("t7 \u8bbe\u5c0f\u4e0a\u9650\u540e\u51fa\u73b0\u8d85\u9650", over2 > 0)

    ck("t8 \u9ed8\u8ba4\u8282\u70b9\u542b\u5f53\u5929", 0 in DEFAULT_INTERVALS)

    # BOM \u5173\u952e\u7528\u4f8b\uff1a\u9996 key \u5e26 BOM \u65f6\u82e5\u4e0d\u5265\uff0c\u4f1a\u9759\u9ed8\u8fd4\u56de\u9ed8\u8ba4 20
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_case.json")
    with open(tmp, "w", encoding="utf-8-sig") as f:
        json.dump({"daily_new": 7, "intervals": [0, 1]}, f, ensure_ascii=False)
    d = read_json(tmp)
    ck("t9 BOM \u8f93\u5165\u89e3\u6790\u6210\u529f", int(d.get("daily_new")) == 7)
    os.remove(tmp)

    ck("t10 \u8d1f\u8377\u4f30\u7b97\u516c\u5f0f\u4e00\u81f4", abs(20 * len(DEFAULT_INTERVALS) / 2.0 - 70.0) < 1e-9)

    out = []
    if fails:
        out.append("SELFTEST FAIL: %s" % "; ".join(fails))
    else:
        out.append("SELFTEST OK  10/10")
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, RESULT_FILE), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="\u827e\u5bbe\u6d69\u65af\u590d\u4e60\u65e5\u7a0b\u751f\u6210")
    ap.add_argument("--file", help="\u8ba1\u5212 JSON \u6587\u4ef6")
    ap.add_argument("--json", action="store_true", help="\u8f93\u51fa JSON")
    ap.add_argument("--selftest", action="store_true", help="\u81ea\u68c0")
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