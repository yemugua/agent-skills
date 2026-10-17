#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
electrical_check.py — 电气防火检测记录体检脚本

检查项:
  Q1 部位覆盖   五类区域必测部位覆盖度
  Q2 测温异常   温升超限/三相温差异常的处置状态
  Q3 整改闭环   隐患有责任人+期限; 已整改有证据
  Q4 周期       年度检测与防雷防静电检测不超期
  Q5 巡查断档   近 12 个月巡查记录按月覆盖

用法:
  python electrical_check.py --file 电气检测.json [--today 2026-10-13] [--format md|json]
  python electrical_check.py --selftest
"""
import argparse
import json
import sys
from datetime import date

REQUIRED_AREAS = {
    "变配电室": ["变压器", "开关柜", "电缆接头"],
    "配电线路": ["楼层配电箱"],
    "用电设备": ["大功率设备"],
    "照明与插座": ["灯具"],
    "接地": ["接地干线"],
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

    # Q1 部位覆盖
    spots = data.get("spots") or []
    names = [s.get("name") or "" for s in spots]
    for area, reqs in REQUIRED_AREAS.items():
        miss = [r for r in reqs if not any(r in n for n in names)]
        if miss:
            findings.append(("FAIL", "Q1", f"{area}未覆盖: {', '.join(miss)}"))
    if not findings or all(f[1] != "Q1" for f in findings):
        findings.append(("PASS", "Q1", "五类区域必测部位全覆盖"))

    # Q2 测温异常
    abnormals = [s for s in spots if s.get("abnormal")]
    for s in abnormals:
        tag = f"{s.get('name')}({s.get('date')})"
        if not s.get("handled"):
            findings.append(("FAIL", "Q2", f"测温异常未处置: {tag}"))
        else:
            findings.append(("WARN", "Q2", f"测温异常已处置待复查: {tag}"))
    if not abnormals:
        findings.append(("PASS", "Q2", "无测温异常记录"))

    # Q3 整改闭环
    for h in data.get("hazards") or []:
        tag = (h.get("item") or "未命名隐患")[:20]
        if not h.get("owner") or not h.get("deadline"):
            findings.append(("FAIL", "Q3", f"隐患「{tag}」缺责任人或期限"))
        if h.get("rectified") and not h.get("evidence"):
            findings.append(("WARN", "Q3", f"隐患「{tag}」已整改无证据"))

    # Q4 周期
    for kind in ("电气检测", "防雷防静电检测"):
        recs = [parse_date(x.get("date")) for x in (data.get("inspections") or [])
                if x.get("type") == kind]
        recs = [r for r in recs if r]
        if not recs or months_between(max(recs), today) > 12:
            last = max(recs) if recs else None
            findings.append(("FAIL", "Q4", f"{kind}超期（最近: {last}）"))

    # Q5 巡查断档
    patrols = sorted({(d.year, d.month) for d in
                      (parse_date(x.get("date")) for x in (data.get("patrols") or [])) if d})
    y, m = today.year, today.month
    gaps = []
    for _ in range(12):
        y2, m2 = (y - 1, 12) if m == 1 else (y, m - 1)
        if (y2, m2) not in patrols:
            gaps.append(f"{y2}-{m2:02d}")
        y, m = y2, m2
    if gaps:
        findings.append(("WARN", "Q5", f"巡查断档月份: {', '.join(gaps)}"))

    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    passes = [f for f in findings if f[0] == "PASS"]
    return findings, {"fail": len(fails), "warn": len(warns), "pass": len(passes),
                      "verdict": "不合格" if fails else ("有瑕疵" if warns else "合格")}


def render_md(findings, summary):
    lines = ["# 电气防火检测体检报告", ""]
    lines.append(f"**结论：{summary['verdict']}**（FAIL {summary['fail']} / WARN {summary['warn']} / PASS {summary['pass']}）")
    lines.append("")
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    for lv, code, msg in findings:
        lines.append(f"- {icon[lv]} **[{code}]** {msg}")
    return "\n".join(lines)


SAMPLE = {
    "spots": [
        {"name": "变压器低压接头", "area": "变配电室", "date": "2026-04-10", "abnormal": True, "handled": False},
        {"name": "开关柜母线接头", "area": "变配电室", "date": "2026-04-10", "abnormal": False},
        {"name": "电缆接头", "area": "变配电室", "date": "2026-04-10", "abnormal": False},
        {"name": "楼层配电箱", "area": "配电线路", "date": "2026-04-10", "abnormal": False},
        {"name": "大功率设备", "area": "用电设备", "date": "2026-04-10", "abnormal": False},
        {"name": "筒灯灯具回路", "area": "照明与插座", "date": "2026-04-10", "abnormal": False},
        {"name": "接地干线", "area": "接地", "date": "2026-04-10", "abnormal": False},
    ],
    "inspections": [
        {"type": "电气检测", "date": "2025-03-15"},
        {"type": "防雷防静电检测", "date": "2026-05-20"},
    ],
    "patrols": [{"date": f"2026-{m:02d}-15"} for m in range(1, 11)],
    "hazards": [
        {"item": "低压接头过热", "owner": "工程部", "deadline": "2026-05-01", "rectified": True, "evidence": ""},
        {"item": "私拉乱接", "owner": "", "deadline": "", "rectified": False},
    ],
}


def selftest():
    findings, summary = check(SAMPLE, date(2026, 10, 13))
    print(render_md(findings, summary))
    codes = [(lv, c) for lv, c, _ in findings]
    assert ("FAIL", "Q2") in codes, "应检出测温异常未处置"
    assert ("FAIL", "Q3") in codes, "应检出隐患无责任人/期限"
    assert ("FAIL", "Q4") in codes, "应检出电气检测超期"
    assert ("WARN", "Q5") in codes, "应检出 11-12 月巡查断档"
    good = json.loads(json.dumps(SAMPLE))
    good["spots"][0]["handled"] = True
    good["inspections"] = [{"type": "电气检测", "date": "2026-04-10"},
                           {"type": "防雷防静电检测", "date": "2026-05-20"}]
    good["patrols"] = [{"date": f"{y}-{m:02d}-15"}
                       for (y, m) in [(2025, 11), (2025, 12)] + [(2026, m) for m in range(1, 11)]]
    good["hazards"][0]["evidence"] = "紧固+复测记录"
    good["hazards"][1] = {"item": "私拉乱接", "owner": "物业", "deadline": "2026-10-30", "rectified": False}
    f2, s2 = check(good, date(2026, 10, 13))
    assert s2["fail"] == 0, f"全合规样本不应 FAIL，实际 {s2}"
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="电气防火检测记录体检")
    ap.add_argument("--file", help="电气检测 JSON 文件")
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
