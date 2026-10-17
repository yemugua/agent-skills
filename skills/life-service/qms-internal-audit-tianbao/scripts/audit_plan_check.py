#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_plan_check.py — 内审方案与不符合闭环体检脚本

检查项:
  Q1 覆盖度     条款/过程/部门/班次覆盖
  Q2 独立性     审核员不审本岗
  Q3 时间分布   按月/季度滚动, 不集中年底
  Q4 不符合闭环 每项不符合有原因/措施/验证/关闭

用法:
  python audit_plan_check.py --file 审核方案.json [--today 2026-10-13] [--format md|json]
  python audit_plan_check.py --selftest
"""
import argparse
import json
import sys
from datetime import date

CLAUSES = ["4", "5", "6", "7", "8", "9", "10"]          # ISO 9001 章节组
DEPARTMENTS = ["总经理办公室", "质量部", "生产部", "技术部", "采购部", "销售部", "人事部", "设备部"]


def parse_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def check(data: dict, today: date):
    findings = []
    plans = data.get("plan") or []

    # Q1 覆盖度
    covered_clauses = {c for p in plans for c in (p.get("clauses") or [])}
    miss_c = [c for c in CLAUSES if c not in covered_clauses]
    if miss_c:
        findings.append(("FAIL", "Q1", f"审核方案未覆盖条款: {', '.join(miss_c)}"))
    covered_depts = {p.get("department") for p in plans}
    miss_d = [d for d in DEPARTMENTS if d not in covered_depts]
    if miss_d:
        findings.append(("FAIL", "Q1", f"审核方案未覆盖部门: {', '.join(miss_d)}"))

    # Q2 独立性
    for p in plans:
        auditor, dept = p.get("auditor"), p.get("department")
        own = p.get("auditor_department")
        if auditor and own and own == dept:
            findings.append(("FAIL", "Q2", f"{auditor} 审核本部门({dept})，违反独立性"))

    # Q3 时间分布
    dates = sorted(d for d in (parse_date(p.get("date")) for p in plans) if d)
    months = {}
    for d in dates:
        months.setdefault(d.month, 0)
        months[d.month] += 1
    if months:
        top_month, top_count = max(months.items(), key=lambda kv: kv[1])
        if top_count >= 2 and top_count >= len(plans) * 0.5:
            findings.append(("WARN", "Q3",
                             f"{top_month} 月集中 {top_count}/{len(plans)} 次审核，应滚动分布"))

    # Q4 不符合闭环
    for nc in data.get("nonconformities") or []:
        tag = (nc.get("item") or "未命名不符合")[:20]
        if not nc.get("root_cause"):
            findings.append(("FAIL", "Q4", f"不符合「{tag}」缺原因分析"))
        if not nc.get("action") or not nc.get("owner") or not nc.get("deadline"):
            findings.append(("FAIL", "Q4", f"不符合「{tag}」缺措施/责任人/期限"))
        if nc.get("status") == "closed" and not nc.get("verify_evidence"):
            findings.append(("FAIL", "Q4", f"不符合「{tag}」已关闭但无验证证据"))

    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    passes = [f for f in findings if f[0] == "PASS"]
    return findings, {"fail": len(fails), "warn": len(warns), "pass": len(passes),
                      "verdict": "不合格" if fails else ("有瑕疵" if warns else "合格")}


def render_md(findings, summary):
    lines = ["# 内审方案体检报告", ""]
    lines.append(f"**结论：{summary['verdict']}**（FAIL {summary['fail']} / WARN {summary['warn']}）")
    lines.append("")
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    for lv, code, msg in findings:
        lines.append(f"- {icon[lv]} **[{code}]** {msg}")
    return "\n".join(lines)


SAMPLE = {
    "plan": [
        {"date": "2026-01-20", "department": "质量部", "auditor": "张某",
         "auditor_department": "生产部", "clauses": ["4", "5", "9"]},
        {"date": "2026-04-15", "department": "生产部", "auditor": "李某",
         "auditor_department": "质量部", "clauses": ["6", "7", "8"]},
        {"date": "2026-12-20", "department": "采购部", "auditor": "王某",
         "auditor_department": "销售部", "clauses": ["8"]},
        {"date": "2026-12-25", "department": "销售部", "auditor": "赵某",
         "auditor_department": "销售部", "clauses": ["8"]},
    ],
    "nonconformities": [
        {"item": "检验记录缺确认签字", "root_cause": "记录填写规范未培训",
         "action": "补充培训并修订规范", "owner": "质量部", "deadline": "2026-05-01",
         "status": "closed", "verify_evidence": "培训签到+修订记录"},
        {"item": "供方评价超期", "root_cause": "", "action": "", "owner": "",
         "deadline": "", "status": "open"},
    ],
}


def selftest():
    findings, summary = check(SAMPLE, date(2026, 10, 13))
    print(render_md(findings, summary))
    codes = [(lv, c) for lv, c, _ in findings]
    assert ("FAIL", "Q1") in codes, "应检出条款/部门覆盖缺口"
    assert ("FAIL", "Q2") in codes, "应检出赵某审本部门"
    assert ("WARN", "Q3") in codes, "应检出 12 月集中"
    assert ("FAIL", "Q4") in codes, "应检出不符合无原因/措施"
    good = {
        "plan": [
            {"date": f"2026-{m:02d}-15", "department": d, "auditor": f"审核员{i}",
             "auditor_department": "质量部" if d != "质量部" else "生产部",
             "clauses": cs}
            for i, (d, cs) in enumerate([
                ("质量部", ["4", "9", "10"]), ("生产部", ["6", "7", "8"]), ("技术部", ["8"]),
                ("采购部", ["8"]), ("销售部", ["8"]), ("人事部", ["7"]),
                ("设备部", ["7"]), ("总经理办公室", ["5", "6"])])
            for m in [1 + i * 1]
        ],
        "nonconformities": [
            {"item": "检验记录缺确认签字", "root_cause": "培训缺失",
             "action": "培训+修订规范", "owner": "质量部", "deadline": "2026-05-01",
             "status": "closed", "verify_evidence": "签到+修订记录"},
        ],
    }
    f2, s2 = check(good, date(2026, 10, 13))
    assert s2["fail"] == 0, f"全合规样本不应 FAIL，实际 {s2}"
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="内审方案与不符合闭环体检")
    ap.add_argument("--file", help="审核方案 JSON 文件")
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
