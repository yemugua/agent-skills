#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gas_site_check.py — 燃气使用场所安全检查脚本

检查项:
  Q1 泄漏感知   可燃气体报警器 + 紧急切断阀(联动); 通风
  Q2 连接管     类型合规(优先不锈钢波纹); 橡胶软管<=18个月; 不穿墙/超长
  Q3 灶具       熄火保护装置
  Q4 钢瓶       数量限量(50kg<=3瓶/间); 存放合规; 检验有效; 地下禁用
  Q5 巡查       近12个月巡查按月覆盖

用法:
  python gas_site_check.py --file 燃气场所.json [--format md|json]
  python gas_site_check.py --selftest
"""
import argparse
import json
import sys
from datetime import date

MAX_CYL_PER_ROOM = 3
MAX_HOSE_MONTHS = 18


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
    gas_type = data.get("gas_type", "管道气")
    underground = data.get("underground", False)

    # Q1 泄漏感知
    if not data.get("alarm"):
        findings.append(("FAIL", "Q1", "未安装可燃气体报警器"))
    if not data.get("emergency_cutoff"):
        findings.append(("FAIL", "Q1", "无紧急切断阀或报警未联动切断"))
    if underground and gas_type == "瓶装气":
        findings.append(("FAIL", "Q1", "地下/半地下场所使用瓶装气，违反规定"))

    # Q2 连接管
    for h in data.get("hoses") or []:
        tag = f"{h.get('location') or '未命名部位'}"
        htype = h.get("type", "")
        install = parse_date(h.get("install_date"))
        if "波纹" not in htype and "金属包覆" not in htype:
            if install and months_between(install, today) > MAX_HOSE_MONTHS:
                findings.append(("FAIL", "Q2",
                                 f"{tag} 橡胶软管已用 {months_between(install, today)} 个月 > {MAX_HOSE_MONTHS} 个月"))
            else:
                findings.append(("WARN", "Q2", f"{tag} 使用{htype or '橡胶软管'}，建议更换不锈钢波纹管"))
        if h.get("through_wall"):
            findings.append(("FAIL", "Q2", f"{tag} 软管穿墙/穿顶棚"))

    # Q3 灶具
    for a in data.get("appliances") or []:
        if not a.get("flame_failure_protection"):
            findings.append(("FAIL", "Q3",
                             f"灶具「{a.get('name') or '未命名'}」无熄火保护装置"))

    # Q4 钢瓶
    cylinders = data.get("cylinders") or []
    per_room = {}
    for c in cylinders:
        room = c.get("room") or "未命名房间"
        per_room[room] = per_room.get(room, 0) + (c.get("count") or 1)
        if c.get("overdue"):
            findings.append(("FAIL", "Q4", f"钢瓶超检验期: {c.get('spec') or c.get('room')}"))
        if c.get("lying"):
            findings.append(("FAIL", "Q4", "钢瓶倒卧存放"))
    for room, n in per_room.items():
        if n > MAX_CYL_PER_ROOM:
            findings.append(("FAIL", "Q4", f"{room} 存放 {n} 瓶，超过 {MAX_CYL_PER_ROOM} 瓶限量"))

    # Q5 巡查
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
    lines = ["# 燃气场所安全检查报告", ""]
    lines.append(f"**结论：{summary['verdict']}**（FAIL {summary['fail']} / WARN {summary['warn']} / PASS {summary['pass']}）")
    lines.append("")
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    for lv, code, msg in findings:
        lines.append(f"- {icon[lv]} **[{code}]** {msg}")
    lines.append("")
    lines.append("> 脚本只做结构与逻辑检查，不判定现场实际安全状态。")
    return "\n".join(lines)


SAMPLE = {
    "gas_type": "瓶装气", "underground": False,
    "alarm": True, "emergency_cutoff": False,
    "hoses": [
        {"location": "后厨灶台", "type": "橡胶软管", "install_date": "2024-06-01", "through_wall": True},
        {"location": "仓库热水器", "type": "不锈钢波纹管", "install_date": "2026-01-10"},
    ],
    "appliances": [
        {"name": "后厨双眼灶", "flame_failure_protection": True},
        {"name": "仓库热水器", "flame_failure_protection": False},
    ],
    "cylinders": [
        {"spec": "50kg 液化气瓶", "room": "后厨杂物间", "count": 4, "overdue": False, "lying": True},
        {"spec": "15kg 液化气瓶", "room": "后厨杂物间", "count": 2, "overdue": True, "lying": False},
    ],
    "patrols": [{"date": f"2026-{m:02d}-10"} for m in range(1, 10)],
}


def selftest():
    findings, summary = check(SAMPLE, date(2026, 10, 13))
    print(render_md(findings, summary))
    codes = [(lv, c) for lv, c, _ in findings]
    assert ("FAIL", "Q1") in codes, "应检出无紧急切断阀"
    assert ("FAIL", "Q2") in codes, "应检出软管超期/穿墙"
    assert ("FAIL", "Q3") in codes, "应检出具无熄火保护"
    assert ("FAIL", "Q4") in codes, "应检出钢瓶超量/倒卧/超期"
    assert ("WARN", "Q5") in codes, "应检出巡查断档"
    good = {
        "gas_type": "管道气", "underground": False,
        "alarm": True, "emergency_cutoff": True,
        "hoses": [
            {"location": "后厨灶台", "type": "不锈钢波纹管", "install_date": "2026-01-10"},
        ],
        "appliances": [{"name": "后厨双眼灶", "flame_failure_protection": True}],
        "cylinders": [],
        "patrols": [{"date": f"{y}-{m:02d}-10"}
                    for (y, m) in [(2025, 11), (2025, 12)] + [(2026, m) for m in range(1, 11)]],
    }
    f2, s2 = check(good, date(2026, 10, 13))
    assert s2["fail"] == 0, f"全合规样本不应 FAIL，实际 {s2}"
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="燃气使用场所安全检查")
    ap.add_argument("--file", help="燃气场所 JSON 文件")
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
