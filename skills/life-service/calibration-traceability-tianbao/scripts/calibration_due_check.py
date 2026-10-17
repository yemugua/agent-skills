#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
calibration_due_check.py — 计量器具台账到期预警脚本

输出四类清单:
  1) 已超期(在用)
  2) 30/60 天内到期
  3) 台账要素缺失
  4) 停用/报废状态核对

用法:
  python calibration_due_check.py --file 器具台账.json [--warn-days 30] [--format md|json]
  python calibration_due_check.py --selftest
"""
import argparse
import json
import sys
from datetime import date


def parse_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def check(data: dict, today: date, warn_days: int):
    findings = []
    for it in data.get("instruments") or []:
        name = f"{it.get('name')}({it.get('asset_no') or '无编号'})"
        status = it.get("status", "合格")
        due = parse_date(it.get("due_date"))

        # 台账要素
        if not it.get("asset_no"):
            findings.append(("WARN", "Q1", f"{name} 缺出厂编号"))
        if not due:
            findings.append(("WARN", "Q1", f"{name} 缺到期日"))
            continue

        days = (due - today).days
        if status in ("停用", "报废"):
            if days >= 0:
                findings.append(("PASS", "Q4", f"{name} {status}状态，到期日 {due}"))
            continue
        if days < 0:
            findings.append(("FAIL", "Q2", f"{name} 已超期 {-days} 天仍在用（到期 {due}）"))
        elif days <= warn_days:
            findings.append(("WARN", "Q3", f"{name} {days} 天内到期（{due}）"))
        elif days <= warn_days * 2:
            findings.append(("PASS", "Q3", f"{name} {days} 天内到期，提前关注"))

    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    passes = [f for f in findings if f[0] == "PASS"]
    return findings, {"fail": len(fails), "warn": len(warns), "pass": len(passes),
                      "verdict": "有超期在用" if fails else ("有预警" if warns else "正常")}


def render_md(findings, summary, today):
    lines = [f"# 计量器具到期预警（基准日 {today}）", ""]
    lines.append(f"**结论：{summary['verdict']}**（FAIL {summary['fail']} / WARN {summary['warn']} / PASS {summary['pass']}）")
    lines.append("")
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    for lv, code, msg in findings:
        lines.append(f"- {icon[lv]} **[{code}]** {msg}")
    return "\n".join(lines)


SAMPLE = {
    "instruments": [
        {"name": "电子秤", "asset_no": "TC-001", "due_date": "2026-11-10", "status": "合格"},
        {"name": "卡尺", "asset_no": "CC-102", "due_date": "2026-10-25", "status": "合格"},
        {"name": "压力表", "asset_no": "YL-203", "due_date": "2026-09-30", "status": "合格"},
        {"name": "兆欧表", "asset_no": "ZY-304", "due_date": "2027-01-15", "status": "停用"},
        {"name": "温湿度计", "asset_no": "", "due_date": "", "status": "合格"},
        {"name": "秒表", "asset_no": "MB-405", "due_date": "2026-12-01", "status": "合格"},
    ],
}


def selftest():
    findings, summary = check(SAMPLE, date(2026, 10, 13), 30)
    print(render_md(findings, summary, date(2026, 10, 13)))
    codes = [(lv, c) for lv, c, _ in findings]
    assert ("FAIL", "Q2") in codes, "应检出压力表超期在用"
    assert ("WARN", "Q3") in codes, "应检出卡尺 12 天内到期"
    assert ("WARN", "Q1") in codes, "应检出温湿度计台账要素缺失"
    assert ("PASS", "Q4") in codes, "停用器具不应预警"
    # 无超期场景
    good = {"instruments": [dict(SAMPLE["instruments"][0])]}
    f2, s2 = check(good, date(2026, 10, 13), 30)
    assert s2["fail"] == 0, f"无超期样本不应 FAIL，实际 {s2}"
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="计量器具到期预警")
    ap.add_argument("--file", help="器具台账 JSON 文件")
    ap.add_argument("--warn-days", type=int, default=30)
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
    today = date.today()
    findings, summary = check(data, today, args.warn_days)
    if args.format == "json":
        print(json.dumps({"summary": summary,
                          "findings": [{"level": l, "code": c, "msg": m} for l, c, m in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print(render_md(findings, summary, today))
    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
