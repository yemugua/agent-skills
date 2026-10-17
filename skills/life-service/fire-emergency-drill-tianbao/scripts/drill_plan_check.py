#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
drill_plan_check.py — 消防演练记录/方案体检脚本

检查项:
  Q1 频次合规   相邻演练间隔; 重点单位<=6个月, 其他<=12个月; 最近一次距今年数不超上限
  Q2 方案九要素 目的/依据/时间地点/组织机构/情景设定/实施步骤/保障措施/评估安排/整改要求
  Q3 评估必填   报警响应时间/疏散用时/参演人数/问题清单
  Q4 整改闭环   每项问题有责任人+期限; 已整改有复查日期
  Q5 日期逻辑   演练日期>=预案批准日期; 复查日期>=演练日期

用法:
  python drill_plan_check.py --file 演练记录.json [--today 2026-10-13] [--format md|json]
  python drill_plan_check.py --selftest
"""
import argparse
import json
import sys
from datetime import date

INTERVAL_MONTHS = {"重点单位": 6, "其他单位": 12}
PLAN_ELEMENTS = ["目的", "依据", "时间地点", "组织机构", "情景设定",
                 "实施步骤", "保障措施", "评估安排", "整改要求"]
EVAL_REQUIRED = ["alarm_response_min", "evacuation_min", "participants"]


def months_between(d1: date, d2: date) -> int:
    """d2 相对 d1 的整月数（向下取整，同月为 0）"""
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
    """返回 (findings, summary)。findings: [(level, code, message)]"""
    findings = []
    unit_type = data.get("unit_type", "重点单位")
    limit = INTERVAL_MONTHS.get(unit_type, 6)
    plan_approved = parse_date(data.get("plan_approved_date"))
    drills = data.get("drills") or []

    # ---- Q1 频次 ----
    if not drills:
        findings.append(("FAIL", "Q1", "没有任何演练记录"))
    else:
        dates = sorted(d for d in (parse_date(x.get("date")) for x in drills) if d)
        if len(dates) < len(drills):
            findings.append(("WARN", "Q1", "存在日期缺失或非法的演练记录"))
        for a, b in zip(dates, dates[1:]):
            gap = months_between(a, b)
            if gap > limit:
                findings.append(("FAIL", "Q1",
                                 f"演练间隔 {gap} 个月（{a} → {b}），超过 {unit_type} {limit} 个月上限"))
        if dates:
            gap_today = months_between(dates[-1], today)
            if gap_today > limit:
                findings.append(("FAIL", "Q1",
                                 f"最近一次演练距今 {gap_today} 个月（{dates[-1]}），超过 {limit} 个月上限"))
            else:
                findings.append(("PASS", "Q1",
                                 f"最近一次演练 {dates[-1]}，距今 {gap_today} 个月，未超 {limit} 个月上限"))

    # ---- Q2~Q5 逐次演练 ----
    for i, dr in enumerate(drills, 1):
        tag = f"第{i}次演练({dr.get('date')})"
        d_date = parse_date(dr.get("date"))

        # Q2 方案九要素
        els = dr.get("plan_elements") or {}
        missing = [e for e in PLAN_ELEMENTS if not els.get(e)]
        if missing:
            findings.append(("WARN", "Q2", f"{tag} 方案缺失要素: {', '.join(missing)}"))
        else:
            findings.append(("PASS", "Q2", f"{tag} 方案九要素齐全"))

        # Q3 评估必填
        ev = dr.get("evaluation") or {}
        miss_ev = [k for k in EVAL_REQUIRED if ev.get(k) in (None, "", [])]
        if miss_ev:
            findings.append(("WARN", "Q3", f"{tag} 评估缺必填项: {', '.join(miss_ev)}"))
        else:
            findings.append(("PASS", "Q3", f"{tag} 评估必填项齐全"))

        # Q4 整改闭环
        probs = dr.get("problems") or []
        if not probs:
            findings.append(("WARN", "Q4", f"{tag} 未记录问题清单（演练无问题极少见，确认评估是否做实）"))
        for p in probs:
            item = (p.get("item") or "未命名问题")[:20]
            if not p.get("owner") or not p.get("deadline"):
                findings.append(("FAIL", "Q4", f"{tag} 问题「{item}」缺责任人或完成期限"))
            if p.get("rectified") and not p.get("review_date"):
                findings.append(("WARN", "Q4", f"{tag} 问题「{item}」已整改但无复查日期"))

        # Q5 日期逻辑
        if d_date and plan_approved and d_date < plan_approved:
            findings.append(("FAIL", "Q5", f"{tag} 演练日期早于预案批准日期（{plan_approved}）"))
        for p in probs:
            rd = parse_date(p.get("review_date"))
            if rd and d_date and rd < d_date:
                findings.append(("FAIL", "Q5",
                                 f"{tag} 问题「{(p.get('item') or '')[:20]}」复查日期早于演练日期"))

    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    passes = [f for f in findings if f[0] == "PASS"]
    summary = {"fail": len(fails), "warn": len(warns), "pass": len(passes),
               "verdict": "不合格" if fails else ("有瑕疵" if warns else "合格")}
    return findings, summary


def render_md(findings, summary, unit_type, limit):
    lines = [f"# 演练记录体检报告（{unit_type}，间隔上限 {limit} 个月）", ""]
    lines.append(f"**结论：{summary['verdict']}**（FAIL {summary['fail']} / WARN {summary['warn']} / PASS {summary['pass']}）")
    lines.append("")
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    for lv, code, msg in findings:
        lines.append(f"- {icon[lv]} **[{code}]** {msg}")
    lines.append("")
    lines.append("> 脚本只做结构与逻辑检查，不判定演练实际效果。")
    return "\n".join(lines)


SAMPLE = {
    "unit_type": "重点单位",
    "plan_approved_date": "2026-02-01",
    "drills": [
        {
            "date": "2026-03-15", "type": "综合演练",
            "plan_elements": {e: True for e in PLAN_ELEMENTS},
            "evaluation": {"alarm_response_min": 3, "evacuation_min": 8,
                           "participants": 120, "problems": []},
            "problems": [
                {"item": "二层疏散指示损坏", "owner": "工程部-王工", "deadline": "2026-04-15",
                 "rectified": True, "review_date": "2026-04-10"},
                {"item": "广播话术不统一", "owner": "消防管理人", "deadline": "2026-04-30",
                 "rectified": False, "review_date": None},
            ],
        },
        {
            "date": "2026-09-20", "type": "疏散演练",
            "plan_elements": {"目的": True, "组织机构": True, "情景设定": True,
                              "实施步骤": True, "评估安排": True},
            "evaluation": {"alarm_response_min": 5, "participants": 95, "problems": []},
            "problems": [
                {"item": "车库出口堵塞", "owner": "物业", "deadline": "",
                 "rectified": True, "review_date": "2026-09-10"},
            ],
        },
    ],
}


def selftest():
    data = json.loads(json.dumps(SAMPLE))
    findings, summary = check(data, date(2026, 10, 13))
    print(render_md(findings, summary, data["unit_type"], INTERVAL_MONTHS["重点单位"]))
    # 断言: 间隔 6 个月(3-15 → 9-20)不超; 第二次缺4要素+疏散用时; 问题无期限FAIL; 复查早于演练FAIL
    codes = [(lv, c) for lv, c, _ in findings]
    assert ("FAIL", "Q1") not in codes, "间隔 6 个月不应判 FAIL"
    assert ("WARN", "Q2") in codes, "应检出第二次方案缺要素"
    assert ("WARN", "Q3") in codes, "应检出缺疏散用时"
    assert ("FAIL", "Q4") in codes, "应检出问题无期限"
    assert ("FAIL", "Q5") in codes, "应检出复查日期早于演练日期"
    # 间隔超标场景
    bad = json.loads(json.dumps(SAMPLE))
    bad["drills"][1]["date"] = "2026-10-20"
    f2, s2 = check(bad, date(2026, 11, 1))
    assert ("FAIL", "Q1") in [(lv, c) for lv, c, _ in f2], "间隔 7 个月应判 FAIL"
    # 无记录场景
    f3, s3 = check({"unit_type": "其他单位", "drills": []}, date(2026, 10, 13))
    assert ("FAIL", "Q1") in [(lv, c) for lv, c, _ in f3]
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="消防演练记录/方案体检")
    ap.add_argument("--file", help="演练记录 JSON 文件")
    ap.add_argument("--today", help="核查基准日 YYYY-MM-DD，默认今天")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    ap.add_argument("--selftest", action="store_true", help="跑内置样例自检")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.file:
        ap.error("必须提供 --file 或 --selftest")

    today = parse_date(args.today) or date.today()
    try:
        with open(args.file, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"读取失败: {e}", file=sys.stderr)
        return 2

    findings, summary = check(data, today)
    unit_type = data.get("unit_type", "重点单位")
    limit = INTERVAL_MONTHS.get(unit_type, 6)
    if args.format == "json":
        print(json.dumps({"summary": summary,
                          "findings": [{"level": l, "code": c, "msg": m} for l, c, m in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print(render_md(findings, summary, unit_type, limit))
    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
