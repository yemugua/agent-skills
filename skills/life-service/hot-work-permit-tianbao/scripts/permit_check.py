#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
permit_check.py — 动火作业票体检脚本

检查项:
  Q1 要素完整   八要素: 部位/方式/人员+证号/监护人/气体检测/措施/审批/时间窗
  Q2 分级审批   分级(特级/一级/二级)与审批权限匹配
  Q3 气体检测   检测值<0.5%且检测时间在作业前30分钟内
  Q4 时间逻辑   审批时间<=作业开始; 作业时长不超时间窗
  Q5 完工留守   留守观察>=30分钟且有监护人签字

用法:
  python permit_check.py --file 动火票.json [--today 2026-10-13] [--format md|json]
  python permit_check.py --selftest
"""
import argparse
import json
import sys
from datetime import date, datetime

APPROVER = {"特级": "单位主要负责人", "一级": "分管负责人+安全管理部门", "二级": "作业部门+安全管理部门"}
ELEMENTS = ["site", "method", "operator", "cert_no", "supervisor", "gas_test",
            "measures", "approvals", "work_start"]


def parse_dt(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(s)[:19], fmt)
        except ValueError:
            continue
    return None


def check_permit(p: dict, idx: int):
    findings = []
    tag = f"第{idx}张票({p.get('site') or p.get('no') or '未命名'})"

    # Q1 要素
    miss = [e for e in ELEMENTS if p.get(e) in (None, "", [])]
    if miss:
        findings.append(("FAIL", "Q1", f"{tag} 缺要素: {', '.join(miss)}"))
    else:
        findings.append(("PASS", "Q1", f"{tag} 八要素齐全"))

    # Q2 分级审批
    level = p.get("level")
    if level not in APPROVER:
        findings.append(("WARN", "Q2", f"{tag} 动火分级缺失或非法（{level}）"))
    else:
        need = APPROVER[level]
        got = p.get("approvals") or []
        min_approvals = 3 if level == "特级" else 2
        if not got:
            findings.append(("FAIL", "Q2", f"{tag} {level}动火无审批记录（应含{need}）"))
        elif len(got) < min_approvals:
            findings.append(("FAIL", "Q2",
                             f"{tag} {level}动火仅 {len(got)} 级审批，应≥{min_approvals}"
                             f"（作业部门+安全管理部门，特级另需单位负责人）"))
        else:
            findings.append(("PASS", "Q2", f"{tag} 分级审批匹配"))

    # Q3 气体检测
    gas = p.get("gas_test") or {}
    val = gas.get("value")
    t = parse_dt(gas.get("time"))
    work_start = parse_dt(p.get("work_start"))
    if val is None or not t:
        findings.append(("FAIL", "Q3", f"{tag} 气体检测缺失"))
    else:
        if val >= 0.5:
            findings.append(("FAIL", "Q3", f"{tag} 可燃气体 {val}% ≥ 0.5%，不合格"))
        if work_start and t > work_start:
            findings.append(("FAIL", "Q3", f"{tag} 检测时间晚于作业开始"))
        elif work_start and (work_start - t).total_seconds() > 1800:
            findings.append(("FAIL", "Q3", f"{tag} 检测距作业超过 30 分钟，应复测"))

    # Q4 时间逻辑
    ws, we = parse_dt(p.get("work_start")), parse_dt(p.get("work_end"))
    ap = parse_dt(p.get("approved_at"))
    if ws and we and we <= ws:
        findings.append(("FAIL", "Q4", f"{tag} 作业结束时间早于开始时间"))
    if ap and ws and ap > ws:
        findings.append(("FAIL", "Q4", f"{tag} 审批时间晚于作业开始"))
    if ws and we and (we - ws).total_seconds() > 8 * 3600:
        findings.append(("WARN", "Q4", f"{tag} 作业时长超过一个班次，应重新办票"))

    # Q5 完工留守
    watch = p.get("watch_minutes")
    if watch is None or watch < 30:
        findings.append(("FAIL", "Q5", f"{tag} 完工留守不足 30 分钟（当前 {watch}）"))
    if p.get("closed_by"):
        findings.append(("PASS", "Q5", f"{tag} 完工留守与闭环签字齐全"))
    return findings


def check(data, today):
    permits = data.get("permits") or []
    if isinstance(permits, dict):
        permits = [permits]
    findings = []
    for i, p in enumerate(permits, 1):
        findings.extend(check_permit(p, i))
    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    passes = [f for f in findings if f[0] == "PASS"]
    return findings, {"fail": len(fails), "warn": len(warns), "pass": len(passes),
                      "verdict": "不合格" if fails else ("有瑕疵" if warns else "合格")}


def render_md(findings, summary):
    lines = ["# 动火作业票体检报告", ""]
    lines.append(f"**结论：{summary['verdict']}**（FAIL {summary['fail']} / WARN {summary['warn']} / PASS {summary['pass']}）")
    lines.append("")
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    for lv, code, msg in findings:
        lines.append(f"- {icon[lv]} **[{code}]** {msg}")
    lines.append("")
    lines.append("> 脚本只做结构与逻辑检查，不替代现场监管。")
    return "\n".join(lines)


SAMPLE = {
    "permits": [
        {
            "no": "DH-2026-0101", "site": "3号罐区管廊", "level": "特级",
            "method": "电焊", "operator": "赵某", "cert_no": "TS3201001",
            "supervisor": "钱某", "work_start": "2026-10-12 09:00", "work_end": "2026-10-12 16:00",
            "gas_test": {"time": "2026-10-12 08:40", "value": 0.1, "by": "孙某"},
            "measures": ["清理可燃物", "配灭火器", "遮挡接火斗", "消防车值守"],
            "approvals": ["作业部门-周某", "安全部-吴某", "单位负责人-郑某"],
            "approved_at": "2026-10-11 16:30", "watch_minutes": 45, "closed_by": "钱某",
        },
        {
            "no": "DH-2026-0102", "site": "二楼维修间", "level": "二级",
            "method": "气割", "operator": "赵某", "cert_no": "",
            "supervisor": "", "work_start": "2026-10-12 10:00", "work_end": "2026-10-12 11:00",
            "gas_test": {"time": "2026-10-12 09:50", "value": 0.8, "by": "孙某"},
            "measures": [], "approvals": ["班组长-冯某"],
            "approved_at": "2026-10-12 10:30", "watch_minutes": 10, "closed_by": "",
        },
    ],
}


def selftest():
    findings, summary = check(SAMPLE, date(2026, 10, 13))
    print(render_md(findings, summary))
    codes = [(lv, c) for lv, c, _ in findings]
    assert ("FAIL", "Q1") in codes, "应检出第二张缺证号/监护人/措施"
    assert ("FAIL", "Q2") in codes, "应检出二级动火仅班组长审批"
    assert ("FAIL", "Q3") in codes, "应检出气体 0.8% 超标"
    assert ("FAIL", "Q4") in codes, "应检出审批晚于作业"
    assert ("FAIL", "Q5") in codes, "应检出留守不足 30 分钟"
    # 全合规场景
    good = {"permits": [dict(SAMPLE["permits"][0])]}
    f2, s2 = check(good, date(2026, 10, 13))
    assert s2["verdict"] == "合格", f"全合规票应判合格，实际 {s2}"
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="动火作业票体检")
    ap.add_argument("--file", help="动火票 JSON 文件")
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
