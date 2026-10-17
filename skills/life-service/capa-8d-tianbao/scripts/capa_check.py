#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
capa_check.py — 8D/CAPA 闭环体检脚本

检查项:
  Q1 要素完整   D0~D8 九步关键要素
  Q2 根因深度   5Why>=3层且触系统; "员工疏忽"判深度不足
  Q3 围堵退出   围堵措施须有退出机制
  Q4 验证窗口   >=3批次或>=30天
  Q5 横向展开   同类过程/供方排查记录

用法:
  python capa_check.py --file 8D报告.json [--format md|json]
  python capa_check.py --selftest
"""
import argparse
import json
import sys

STEPS = ["team", "problem", "containment", "root_cause", "permanent_action",
         "prevention", "standardization", "closure"]
SHALLOW_CAUSES = {"员工疏忽", "意识不足", "责任心不强", "管理不到位"}


def check(data: dict):
    findings = []
    tag = data.get("title") or data.get("no") or "未命名报告"

    # Q1 要素
    miss = [s for s in STEPS if not data.get(s)]
    if miss:
        findings.append(("FAIL", "Q1", f"{tag} 缺要素: {', '.join(miss)}"))

    # Q2 根因深度
    whys = data.get("five_whys") or []
    if len(whys) < 3:
        findings.append(("WARN", "Q2", f"{tag} 5Why 仅 {len(whys)} 层，少于 3 层"))
    rc = str(data.get("root_cause") or "")
    if any(s in rc for s in SHALLOW_CAUSES):
        findings.append(("FAIL", "Q2", f"{tag} 根因「{rc[:20]}」停在人的层面，须触系统（流程/设计/标准）"))
    if not data.get("outflow_cause"):
        findings.append(("WARN", "Q2", f"{tag} 未区分流出原因"))

    # Q3 围堵退出
    cont = data.get("containment") or {}
    if cont.get("is_100pct_inspection") and not cont.get("exit_plan"):
        findings.append(("WARN", "Q3", f"{tag} 围堵为 100% 全检但无退出机制"))

    # Q4 验证窗口
    ver = data.get("verification") or {}
    batches = ver.get("batches") or 0
    days = ver.get("days") or 0
    if batches < 3 and days < 30:
        findings.append(("FAIL", "Q4",
                         f"{tag} 验证窗口不足（{batches} 批次/{days} 天，需 ≥3 批次或 ≥30 天）"))

    # Q5 横向展开
    prev = data.get("prevention") or {}
    if not prev.get("horizontal_scope"):
        findings.append(("WARN", "Q5", f"{tag} 无横向展开范围（同类过程/供方/型号）"))
    elif not prev.get("check_evidence"):
        findings.append(("WARN", "Q5", f"{tag} 横向展开无排查证据"))

    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    passes = [f for f in findings if f[0] == "PASS"]
    return findings, {"fail": len(fails), "warn": len(warns), "pass": len(passes),
                      "verdict": "不合格" if fails else ("有瑕疵" if warns else "合格")}


def render_md(findings, summary):
    lines = ["# 8D/CAPA 闭环体检报告", ""]
    lines.append(f"**结论：{summary['verdict']}**（FAIL {summary['fail']} / WARN {summary['warn']}）")
    lines.append("")
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    for lv, code, msg in findings:
        lines.append(f"- {icon[lv]} **[{code}]** {msg}")
    return "\n".join(lines)


SAMPLE = {
    "no": "8D-2026-011",
    "team": "质量/生产/工艺",
    "problem": "XX 产品孔径超差 12 件",
    "containment": {"is_100pct_inspection": True, "exit_plan": ""},
    "root_cause": "员工疏忽漏检",
    "outflow_cause": "",
    "five_whys": ["超差", "装夹不到位", "定位销磨损"],
    "permanent_action": "更换定位销并修订点检表",
    "prevention": {"horizontal_scope": "", "check_evidence": ""},
    "standardization": "点检表 V2.0 培训",
    "closure": "已关闭",
    "verification": {"batches": 1, "days": 5},
}


def selftest():
    findings, summary = check(SAMPLE)
    print(render_md(findings, summary))
    codes = [(lv, c) for lv, c, _ in findings]
    assert ("FAIL", "Q2") in codes, "应检出根因停在人的层面"
    assert ("WARN", "Q3") in codes, "应检出全检无退出机制"
    assert ("FAIL", "Q4") in codes, "应检出验证窗口不足"
    assert ("WARN", "Q5") in codes, "应检出无横向展开"
    good = {
        "no": "8D-2026-012",
        "team": "质量/生产/工艺/SQE",
        "problem": "XX 产品孔径超差 12 件（IS/IS NOT 已界定）",
        "containment": {"is_100pct_inspection": True,
                        "exit_plan": "连续 3 批合格后取消全检，质量经理批准"},
        "root_cause": "点检表三年未修订，定位销磨损无点检项",
        "outflow_cause": "终检抽样方案未覆盖该尺寸",
        "five_whys": ["孔径超差", "装夹不到位", "定位销磨损", "点检表无该项",
                      "无文件定期评审机制"],
        "permanent_action": "更换定位销；修订点检表；终检方案更新",
        "prevention": {"horizontal_scope": "同工艺 3 条线、同型号 2 个产品",
                       "check_evidence": "排查记录 3 份"},
        "standardization": "点检表 V2.0 + 培训 12 人",
        "closure": "已关闭",
        "verification": {"batches": 4, "days": 45},
    }
    f2, s2 = check(good)
    assert s2["verdict"] == "合格", f"全合规样本应判合格，实际 {s2}"
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="8D/CAPA 闭环体检")
    ap.add_argument("--file", help="8D 报告 JSON 文件")
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
    findings, summary = check(data)
    if args.format == "json":
        print(json.dumps({"summary": summary,
                          "findings": [{"level": l, "code": c, "msg": m} for l, c, m in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print(render_md(findings, summary))
    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
