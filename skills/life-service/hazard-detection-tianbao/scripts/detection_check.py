#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
detection_check.py — 职业病危害因素检测台账体检脚本

检查项:
  Q1 周期       定期检测每年>=1次
  Q2 覆盖       检测点位覆盖全部危害岗位
  Q3 超标闭环   超标项有整改+复查; 复查达标
  Q4 告知       结果告知记录

用法:
  python detection_check.py --file 检测.json [--today 2026-10-13] [--format md|json]
  python detection_check.py --selftest
"""
import argparse
import json
import sys
from datetime import date

LIMITS = {"噪声": 85, "矽尘": 1.0, "其他粉尘": 4.0, "化学毒物": 1.0}  # 简化示意限值(以GBZ2为准)


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

    # Q1 周期
    detections = [parse_date(x.get("date")) for x in (data.get("detections") or [])]
    detections = [d for d in detections if d]
    if not detections or months_between(max(detections), today) > 12:
        last = max(detections) if detections else None
        findings.append(("FAIL", "Q1", f"定期检测超期（最近: {last}）"))
    else:
        findings.append(("PASS", "Q1", f"定期检测在周期内（最近: {max(detections)}）"))

    # Q2 覆盖
    posts = {p.get("post") for p in (data.get("posts") or [])}
    covered = {s.get("post") for s in (data.get("spots") or [])}
    miss = sorted(p for p in posts if p not in covered)
    if miss:
        findings.append(("FAIL", "Q2", f"未布点岗位: {', '.join(miss)}"))

    # Q3 超标闭环
    for ex in data.get("exceedances") or []:
        tag = f"{ex.get('post')}/{ex.get('factor')}"
        if not ex.get("rectification"):
            findings.append(("FAIL", "Q3", f"{tag} 超标无整改措施"))
        elif not ex.get("recheck_date"):
            findings.append(("FAIL", "Q3", f"{tag} 超标整改后无复查"))
        elif not ex.get("recheck_pass"):
            findings.append(("FAIL", "Q3", f"{tag} 复查未达标"))
        else:
            findings.append(("PASS", "Q3", f"{tag} 超标整改闭环完成"))

    # Q4 告知
    notices = data.get("notices") or []
    if not notices:
        findings.append(("WARN", "Q4", "无检测结果告知记录"))
    else:
        no_date = [n.get("post") for n in notices if not n.get("date")]
        if no_date:
            findings.append(("WARN", "Q4", f"告知无日期: {', '.join(no_date)}"))

    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    passes = [f for f in findings if f[0] == "PASS"]
    return findings, {"fail": len(fails), "warn": len(warns), "pass": len(passes),
                      "verdict": "不合格" if fails else ("有瑕疵" if warns else "合格")}


def render_md(findings, summary):
    lines = ["# 职业病危害检测台账体检报告", ""]
    lines.append(f"**结论：{summary['verdict']}**（FAIL {summary['fail']} / WARN {summary['warn']} / PASS {summary['pass']}）")
    lines.append("")
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    for lv, code, msg in findings:
        lines.append(f"- {icon[lv]} **[{code}]** {msg}")
    return "\n".join(lines)


SAMPLE = {
    "detections": [{"date": "2025-08-20", "agency": "XX职卫检测"}],
    "posts": [{"post": "打磨岗"}, {"post": "喷漆岗"}, {"post": "焊接岗"}],
    "spots": [{"post": "打磨岗"}, {"post": "喷漆岗"}],
    "exceedances": [
        {"post": "打磨岗", "factor": "矽尘", "rectification": "增设除尘设备",
         "recheck_date": "2026-03-15", "recheck_pass": True},
        {"post": "喷漆岗", "factor": "化学毒物", "rectification": "", "recheck_date": None},
    ],
    "notices": [],
}


def selftest():
    findings, summary = check(SAMPLE, date(2026, 10, 13))
    print(render_md(findings, summary))
    codes = [(lv, c) for lv, c, _ in findings]
    assert ("FAIL", "Q1") in codes, "应检出检测超期(2025-08-20 至今超12个月)"
    assert ("FAIL", "Q2") in codes, "应检出焊接岗未布点"
    assert ("FAIL", "Q3") in codes, "应检出喷漆岗超标无整改"
    assert ("WARN", "Q4") in codes, "应检出无告知记录"
    good = {
        "detections": [{"date": "2026-05-20", "agency": "XX职卫检测"}],
        "posts": [{"post": "打磨岗"}, {"post": "喷漆岗"}, {"post": "焊接岗"}],
        "spots": [{"post": "打磨岗"}, {"post": "喷漆岗"}, {"post": "焊接岗"}],
        "exceedances": [
            {"post": "打磨岗", "factor": "矽尘", "rectification": "增设除尘设备",
             "recheck_date": "2026-08-15", "recheck_pass": True},
        ],
        "notices": [{"post": "打磨岗", "date": "2026-06-01"},
                    {"post": "喷漆岗", "date": "2026-06-01"},
                    {"post": "焊接岗", "date": "2026-06-01"}],
    }
    f2, s2 = check(good, date(2026, 10, 13))
    assert s2["fail"] == 0, f"全合规样本不应 FAIL，实际 {s2}"
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="职业病危害检测台账体检")
    ap.add_argument("--file", help="检测 JSON 文件")
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
