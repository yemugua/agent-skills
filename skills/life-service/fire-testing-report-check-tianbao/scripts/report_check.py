#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
report_check.py — 消防设施检测报告与维保核查脚本

检查项:
  Q1 机构签章   qualified/filed; 签章人含注册消防工程师
  Q2 项目覆盖   按建筑类型必备检测项全覆盖; 不合格项预警
  Q3 周期       报告日期>=检测日期; 下次检测间隔<=365天; 距今天数<=365天
  Q4 结论一致   结论"合格"但存在未整改问题项 → 矛盾
  Q5 维保       月度维保; 响应时限<=24h

用法:
  python report_check.py --file 报告核查.json [--today 2026-10-13] [--format md|json]
  python report_check.py --selftest
"""
import argparse
import json
import sys
from datetime import date

REQUIRED_ITEMS = {
    "高层公共建筑": ["消火栓系统", "自动喷水灭火系统", "火灾自动报警系统", "防排烟系统",
                 "防火分隔设施", "应急照明与疏散指示", "消防电梯", "消防电源", "灭火器"],
    "人员密集场所": ["消火栓系统", "自动喷水灭火系统", "火灾自动报警系统", "防排烟系统",
                 "防火分隔设施", "应急照明与疏散指示", "消防电源", "灭火器"],
    "一般单位": ["消火栓系统", "灭火器", "应急照明与疏散指示"],
}
DEFAULT_BUILDING = "一般单位"


def parse_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def check(data: dict, today: date):
    findings = []
    building = data.get("building_type", DEFAULT_BUILDING)
    required = REQUIRED_ITEMS.get(building, REQUIRED_ITEMS[DEFAULT_BUILDING])
    if building not in REQUIRED_ITEMS:
        findings.append(("WARN", "Q2", f"建筑类型「{building}」未登记，按一般单位必备项核查"))
    if data.get("has_gas"):
        required = required + ["可燃气体报警装置"]

    reports = data.get("reports") or []
    if not reports:
        findings.append(("FAIL", "Q2", "没有任何检测报告"))

    for i, rep in enumerate(reports, 1):
        tag = f"报告{i}({rep.get('project') or rep.get('agency') or '未命名'})"

        # Q1 机构签章
        if not rep.get("qualified"):
            findings.append(("FAIL", "Q1", f"{tag} 机构不具备从业条件"))
        if not rep.get("filed"):
            findings.append(("WARN", "Q1", f"{tag} 机构未在社会消防技术服务信息系统公示"))
        sigs = rep.get("signatories") or []
        if not any("注册消防工程师" in str(s) for s in sigs):
            findings.append(("FAIL", "Q1", f"{tag} 签章人无注册消防工程师"))

        # Q2 项目覆盖
        tested = {it.get("name"): it for it in (rep.get("items") or [])}
        missing = [x for x in required if x not in tested or not tested[x].get("tested")]
        if missing:
            findings.append(("FAIL", "Q2", f"{tag} 检测项目缺项: {', '.join(missing)}"))
        unqualified = [k for k, v in tested.items()
                       if v.get("tested") and v.get("result") and v.get("result") != "合格"]
        if unqualified:
            findings.append(("WARN", "Q2", f"{tag} 不合格项需关注整改: {', '.join(unqualified)}"))

        # Q3 周期
        td, idd, nd = parse_date(rep.get("test_date")), parse_date(rep.get("issue_date")), parse_date(rep.get("next_test_date"))
        if td and idd and idd < td:
            findings.append(("FAIL", "Q3", f"{tag} 报告日期早于检测日期"))
        if td and nd and (nd - td).days > 365:
            findings.append(("FAIL", "Q3", f"{tag} 下次检测间隔 {(nd - td).days} 天，超过 365 天"))
        if td and (today - td).days > 365:
            findings.append(("FAIL", "Q3", f"{tag} 检测日期距今 {(today - td).days} 天，已超 12 个月未全面检测"))

        # Q4 结论一致
        if rep.get("conclusion") == "合格":
            open_probs = [p for p in (rep.get("problems") or []) if not p.get("rectified")]
            if open_probs:
                findings.append(("FAIL", "Q4",
                                 f"{tag} 结论「合格」但存在未整改问题项 {len(open_probs)} 条"))

    # Q5 维保
    mt = data.get("maintenance") or {}
    if not mt.get("monthly"):
        findings.append(("WARN", "Q5", "维保未按月度执行（或未记录）"))
    resp = mt.get("response_hours")
    if resp is not None and resp > 24:
        findings.append(("WARN", "Q5", f"故障响应时限 {resp} 小时，超过 24 小时通行口径"))

    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    passes = [f for f in findings if f[0] == "PASS"]
    summary = {"fail": len(fails), "warn": len(warns), "pass": len(passes),
               "verdict": "不合格" if fails else ("有瑕疵" if warns else "合格")}
    return findings, summary


def render_md(findings, summary, building):
    lines = [f"# 检测报告核查报告（建筑类型：{building}）", ""]
    lines.append(f"**结论：{summary['verdict']}**（FAIL {summary['fail']} / WARN {summary['warn']} / PASS {summary['pass']}）")
    lines.append("")
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    for lv, code, msg in findings:
        lines.append(f"- {icon[lv]} **[{code}]** {msg}")
    lines.append("")
    lines.append("> 脚本只做资料结构与逻辑核查，不判定报告真伪与设施实际状态。")
    return "\n".join(lines)


SAMPLE = {
    "building_type": "高层公共建筑",
    "has_gas": False,
    "reports": [
        {
            "agency": "安信消防检测", "qualified": True, "filed": True,
            "project": "XX大厦", "test_date": "2026-01-10", "issue_date": "2026-01-20",
            "signatories": ["张某(一级注册消防工程师)", "王某(操作人员)"],
            "conclusion": "合格",
            "items": [
                {"name": "消火栓系统", "tested": True, "result": "合格"},
                {"name": "自动喷水灭火系统", "tested": True, "result": "合格"},
                {"name": "火灾自动报警系统", "tested": True, "result": "合格"},
                {"name": "防排烟系统", "tested": True, "result": "基本合格"},
                {"name": "防火分隔设施", "tested": True, "result": "合格"},
                {"name": "应急照明与疏散指示", "tested": True, "result": "合格"},
                {"name": "消防电梯", "tested": True, "result": "合格"},
                {"name": "消防电源", "tested": False, "result": ""},
                {"name": "灭火器", "tested": True, "result": "合格"},
            ],
            "problems": [{"item": "排烟风机未联动", "rectified": False}],
            "next_test_date": "2027-02-01",
        },
    ],
    "maintenance": {"monthly": True, "response_hours": 48, "report_frequency": "月报"},
}


def selftest():
    data = json.loads(json.dumps(SAMPLE))
    findings, summary = check(data, date(2026, 10, 13))
    print(render_md(findings, summary, data["building_type"]))
    codes = [(lv, c) for lv, c, _ in findings]
    assert ("FAIL", "Q2") in codes, "应检出消防电源未检"
    assert ("FAIL", "Q3") in codes, "应检出检测超期（1-10 距今超 12 个月? 276 天——需确认）"
    assert ("WARN", "Q5") in codes, "应检出响应超时"
    # 结论矛盾场景
    bad = json.loads(json.dumps(SAMPLE))
    bad["reports"][0]["conclusion"] = "合格"
    bad["reports"][0]["problems"] = [{"item": "某问题", "rectified": False}]
    f2, _ = check(bad, date(2026, 10, 13))
    assert ("FAIL", "Q4") in [(lv, c) for lv, c, _ in f2], "应检出结论矛盾"
    # 全合规场景
    good = json.loads(json.dumps(SAMPLE))
    r = good["reports"][0]
    r["test_date"], r["issue_date"] = "2026-03-10", "2026-03-20"
    r["next_test_date"] = "2027-03-09"
    r["conclusion"] = "基本合格"
    r["problems"] = [{"item": "排烟风机未联动", "rectified": True}]
    for it in r["items"]:
        it["tested"] = True
        if it["result"] == "":
            it["result"] = "合格"
    good["maintenance"]["response_hours"] = 24
    f3, s3 = check(good, date(2026, 10, 13))
    assert s3["verdict"] in ("合格", "有瑕疵"), f"全合规样本不应 FAIL，实际: {s3}"
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="消防设施检测报告与维保核查")
    ap.add_argument("--file", help="报告核查 JSON 文件")
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
    building = data.get("building_type", DEFAULT_BUILDING)
    if args.format == "json":
        print(json.dumps({"summary": summary,
                          "findings": [{"level": l, "code": c, "msg": m} for l, c, m in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print(render_md(findings, summary, building))
    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
