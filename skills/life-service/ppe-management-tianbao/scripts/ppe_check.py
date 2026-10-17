#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ppe_check.py — 劳动防护用品台账体检脚本

检查项:
  Q1 岗位匹配   每个岗位有对应防护用品(按岗位危害表)
  Q2 发放超期   按发放周期检查最近发放日期
  Q3 培训检查   有佩戴培训与使用检查记录
  Q4 报废处置   损坏/失效品有回收处置记录

用法:
  python ppe_check.py --file 防护台账.json [--today 2026-10-13] [--format md|json]
  python ppe_check.py --selftest
"""
import argparse
import json
import sys
from datetime import date

POST_PPE = {
    "打磨岗": ["防尘口罩", "防护眼镜"],
    "喷漆岗": ["防毒面具", "防化手套"],
    "焊接岗": ["焊接面罩", "阻燃手套"],
    "噪声岗": ["耳塞"],
    "电工岗": ["绝缘手套"],
}
DEFAULT_PPE = ["安全帽"]
ISSUE_PERIOD_DAYS = 90   # 普通防护用品发放周期口径(易耗品按更短)


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
    standards = data.get("standards") or []   # 岗位-用品对应表

    # Q1 岗位匹配
    for std in standards:
        post = std.get("post")
        required = POST_PPE.get(post, DEFAULT_PPE)
        assigned = std.get("ppe") or []
        miss = [p for p in required if p not in assigned]
        if miss:
            findings.append(("FAIL", "Q1", f"{post} 未配备: {', '.join(miss)}"))

    # Q2 发放超期
    for iss in data.get("issues") or []:
        d = parse_date(iss.get("date"))
        item = iss.get("ppe") or iss.get("item") or "防护用品"
        if not d:
            findings.append(("WARN", "Q2", f"{item} 发放记录缺日期"))
        elif (today - d).days > ISSUE_PERIOD_DAYS and not iss.get("returned"):
            findings.append(("WARN", "Q2",
                             f"{item} 上次发放 {d}，超过 {ISSUE_PERIOD_DAYS} 天未换发"))
        if not iss.get("signature"):
            findings.append(("WARN", "Q2", f"{item} 发放无签字"))

    # Q3 培训检查
    if not data.get("trainings"):
        findings.append(("WARN", "Q3", "无防护用品佩戴培训记录"))
    if not data.get("checks"):
        findings.append(("WARN", "Q3", "无使用情况检查记录"))

    # Q4 报废处置
    for sc in data.get("scraps") or []:
        if not sc.get("disposed"):
            findings.append(("WARN", "Q4",
                             f"报废品「{sc.get('item') or '未命名'}」无处置记录"))

    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    passes = [f for f in findings if f[0] == "PASS"]
    return findings, {"fail": len(fails), "warn": len(warns), "pass": len(passes),
                      "verdict": "不合格" if fails else ("有瑕疵" if warns else "合格")}


def render_md(findings, summary):
    lines = ["# 防护用品台账体检报告", ""]
    lines.append(f"**结论：{summary['verdict']}**（FAIL {summary['fail']} / WARN {summary['warn']}）")
    lines.append("")
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    for lv, code, msg in findings:
        lines.append(f"- {icon[lv]} **[{code}]** {msg}")
    return "\n".join(lines)


SAMPLE = {
    "standards": [
        {"post": "打磨岗", "ppe": ["防护眼镜"]},
        {"post": "喷漆岗", "ppe": ["防毒面具", "防化手套"]},
        {"post": "焊接岗", "ppe": ["焊接面罩", "阻燃手套"]},
    ],
    "issues": [
        {"ppe": "防尘口罩", "date": "2026-06-10", "signature": True},
        {"ppe": "防护眼镜", "date": "2026-09-01", "signature": False},
        {"ppe": "防毒面具滤盒", "date": "2026-01-15", "signature": True, "returned": False},
    ],
    "trainings": [{"date": "2026-03-10"}],
    "checks": [],
    "scraps": [{"item": "破安全绳", "disposed": False}],
}


def selftest():
    findings, summary = check(SAMPLE, date(2026, 10, 13))
    print(render_md(findings, summary))
    codes = [(lv, c) for lv, c, _ in findings]
    assert ("FAIL", "Q1") in codes, "应检出打磨岗缺防尘口罩"
    assert ("WARN", "Q2") in codes, "应检出无签字/超期换发"
    assert ("WARN", "Q3") in codes, "应检出无使用检查记录"
    assert ("WARN", "Q4") in codes, "应检出报废品无处置记录"
    good = {
        "standards": [
            {"post": "打磨岗", "ppe": ["防尘口罩", "防护眼镜"]},
            {"post": "喷漆岗", "ppe": ["防毒面具", "防化手套"]},
            {"post": "焊接岗", "ppe": ["焊接面罩", "阻燃手套"]},
        ],
        "issues": [
            {"ppe": "防尘口罩", "date": "2026-10-08", "signature": True},
            {"ppe": "防护眼镜", "date": "2026-10-08", "signature": True},
        ],
        "trainings": [{"date": "2026-09-20"}],
        "checks": [{"date": "2026-09-25"}],
        "scraps": [{"item": "破安全绳", "disposed": True}],
    }
    f2, s2 = check(good, date(2026, 10, 13))
    assert s2["fail"] == 0, f"全合规样本不应 FAIL，实际 {s2}"
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="防护用品台账体检")
    ap.add_argument("--file", help="防护台账 JSON 文件")
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
