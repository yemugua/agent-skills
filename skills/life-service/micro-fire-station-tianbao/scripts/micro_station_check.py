#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
micro_station_check.py — 微型消防站建设与日常管理体检脚本

检查项:
  Q1 人员配置   数量>=6; 站长明确; 消防设施操作员持证
  Q2 装备配置   五类装备清单覆盖且维护在期
  Q3 值守排班   排班连续无断档(按月样本)
  Q4 训练演练   每月>=1次训练; 每季度>=1次演练
  Q5 出动记录   出动与维护记录留痕

用法:
  python micro_station_check.py --file 微型站.json [--today 2026-10-13] [--format md|json]
  python micro_station_check.py --selftest
"""
import argparse
import json
import sys
from datetime import date

EQUIP_REQUIRED = {
    "灭火器材": ["灭火器", "灭火毯", "水带", "水枪"],
    "破拆救生": ["消防斧", "应急照明"],
    "个人防护": ["灭火防护服", "头盔"],
    "通信指挥": ["对讲机"],
}


def months_between(d1: date, d2: date) -> int:
    m = (d2.year - d1.year) * 12 + (d2.month - d1.month)
    if d2.day < d1.day:
        m -= 1
    return max(m, 0)


def parse_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def check(data: dict, today: date):
    findings = []

    # Q1 人员
    staff = data.get("staff") or []
    if len(staff) < 6:
        findings.append(("FAIL", "Q1", f"人员 {len(staff)} 人，少于 6 人标准"))
    else:
        findings.append(("PASS", "Q1", f"人员 {len(staff)} 人，达标"))
    if not data.get("captain"):
        findings.append(("WARN", "Q1", "未明确站长"))
    uncertified = [s.get("name") for s in staff if s.get("operates_facility") and not s.get("cert")]
    if uncertified:
        findings.append(("FAIL", "Q1", f"操作消防设施但无证: {', '.join(uncertified)}"))

    # Q2 装备
    equip = data.get("equipment") or []
    have = {}
    for e in equip:
        have.setdefault(e.get("category"), []).append(e)
    for cat, items in EQUIP_REQUIRED.items():
        missing = [x for x in items if not any(x in (e.get("name") or "") for e in have.get(cat, []))]
        if missing:
            findings.append(("FAIL", "Q2", f"{cat}缺: {', '.join(missing)}"))
    expired = [e.get("name") for e in equip if e.get("expired")]
    if expired:
        findings.append(("WARN", "Q2", f"装备过期未换: {', '.join(expired)}"))

    # Q3 值守排班（按月检查近 6 个月排班天数覆盖）
    duty = data.get("duty") or []
    months = sorted({(d.year, d.month) for d in (parse_date(x.get("date")) for x in duty) if d})
    cur = (today.year, today.month)
    gap = []
    y, m = cur[0], cur[1]
    for _ in range(6):
        y2, m2 = (y - 1, 12) if m == 1 else (y, m - 1)
        if (y2, m2) not in months:
            gap.append(f"{y2}-{m2:02d}")
        y, m = y2, m2
    if gap:
        findings.append(("FAIL", "Q3", f"值守排班断档月份: {', '.join(gap)}"))
    else:
        findings.append(("PASS", "Q3", "近 6 个月值守排班连续"))

    # Q4 训练演练
    trainings = [parse_date(x.get("date")) for x in (data.get("trainings") or [])]
    trainings = [t for t in trainings if t]
    drills = [parse_date(x.get("date")) for x in (data.get("drills") or [])]
    drills = [d for d in drills if d]
    last_train = max(trainings) if trainings else None
    if not last_train or months_between(last_train, today) > 1:
        findings.append(("WARN", "Q4", f"技能训练超一个月未开展（最近: {last_train}）"))
    last_drill = max(drills) if drills else None
    if not last_drill or months_between(last_drill, today) > 3:
        findings.append(("WARN", "Q4", f"演练超一个季度未开展（最近: {last_drill}）"))

    # Q5 出动记录
    actions = data.get("actions") or []
    if not actions:
        findings.append(("WARN", "Q5", "无出动/维护记录"))
    else:
        missing_sig = [a.get("date") for a in actions if not a.get("signed")]
        if missing_sig:
            findings.append(("WARN", "Q5", f"记录未签字: {', '.join(missing_sig[:5])}"))

    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    passes = [f for f in findings if f[0] == "PASS"]
    return findings, {"fail": len(fails), "warn": len(warns), "pass": len(passes),
                      "verdict": "不合格" if fails else ("有瑕疵" if warns else "合格")}


def render_md(findings, summary):
    lines = ["# 微型消防站体检报告", ""]
    lines.append(f"**结论：{summary['verdict']}**（FAIL {summary['fail']} / WARN {summary['warn']} / PASS {summary['pass']}）")
    lines.append("")
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    for lv, code, msg in findings:
        lines.append(f"- {icon[lv]} **[{code}]** {msg}")
    return "\n".join(lines)


SAMPLE = {
    "captain": "李四(消防安全管理人)",
    "staff": [{"name": f"队员{i}", "operates_facility": i <= 2, "cert": "消防设施操作员" if i <= 1 else ""}
              for i in range(1, 8)],
    "equipment": [
        {"category": "灭火器材", "name": "灭火器", "expired": False},
        {"category": "灭火器材", "name": "灭火毯", "expired": False},
        {"category": "灭火器材", "name": "水带", "expired": True},
        {"category": "灭火器材", "name": "水枪", "expired": False},
        {"category": "破拆救生", "name": "消防斧", "expired": False},
        {"category": "破拆救生", "name": "应急照明", "expired": False},
        {"category": "个人防护", "name": "灭火防护服", "expired": False},
        {"category": "个人防护", "name": "头盔", "expired": False},
        {"category": "通信指挥", "name": "对讲机", "expired": False},
    ],
    "duty": [{"date": f"2026-{m:02d}-01"} for m in (5, 6, 8, 9, 10)],
    "trainings": [{"date": "2026-06-05"}, {"date": "2026-03-10"}],
    "drills": [{"date": "2026-02-20"}],
    "actions": [{"date": "2026-08-12", "signed": True}],
}


def selftest():
    findings, summary = check(SAMPLE, date(2026, 10, 13))
    print(render_md(findings, summary))
    codes = [(lv, c) for lv, c, _ in findings]
    assert ("FAIL", "Q1") in codes, "应检出无证操作设施人员"
    assert ("WARN", "Q2") in codes, "应检出水带过期"
    assert ("FAIL", "Q3") in codes, "应检出排班断档(7月)"
    assert ("WARN", "Q4") in codes, "应检出训练/演练超期"
    good = json.loads(json.dumps(SAMPLE))
    good["staff"][1]["cert"] = "消防设施操作员"
    good["equipment"][2]["expired"] = False
    good["duty"] = [{"date": f"2026-{m:02d}-01"} for m in range(4, 11)]
    good["trainings"] = [{"date": "2026-10-05"}]
    good["drills"] = [{"date": "2026-09-20"}]
    f2, s2 = check(good, date(2026, 10, 13))
    assert s2["fail"] == 0, f"全合规样本不应 FAIL，实际 {s2}"
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="微型消防站体检")
    ap.add_argument("--file", help="微型站 JSON 文件")
    ap.add_argument("--today", help="核查基准日，默认今天")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.file:
        ap.error("必须提供 --file 或 --selftest")
    try:
        with open(args.file, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"读取失败: {e}", file=sys.stderr)
        return 2
    findings, summary = check(data, date.today())
    if args.format == "json":
        print(json.dumps({"summary": summary,
                          "findings": [{"level": l, "code": c, "msg": m} for l, c, m in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print(render_md(findings, summary))
    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
