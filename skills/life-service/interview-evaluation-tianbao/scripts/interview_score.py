#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interview_score.py — 结构化面试评分汇总脚本

功能:
  1) 多面试官评分汇总(均值/加权)
  2) 分歧提示: 维度分差>=2 标红, 建议校准
  3) 加权总分与录用建议区间

用法:
  python interview_score.py --file 评分.json [--format md|json]
  python interview_score.py --selftest
"""
import argparse
import json
import sys

DIMS = ["专业能力", "问题解决", "沟通协作", "执行力", "学习成长", "文化匹配"]
WEIGHTS = {"专业能力": 0.3, "问题解决": 0.2, "沟通协作": 0.15,
           "执行力": 0.15, "学习成长": 0.1, "文化匹配": 0.1}
DIVERGENCE = 2  # 分差阈值


def check(data: dict):
    findings = []
    interviewers = data.get("interviewers") or []

    # 维度均分与分歧
    dim_avg = {}
    divergences = []
    for d in DIMS:
        scores = [i.get("scores", {}).get(d) for i in interviewers if i.get("scores", {}).get(d)]
        if scores:
            dim_avg[d] = round(sum(scores) / len(scores), 2)
            if max(scores) - min(scores) >= DIVERGENCE:
                divergences.append((d, min(scores), max(scores)))
                findings.append(("WARN", "Q1",
                                 f"维度「{d}」面试官分差 {max(scores) - min(scores)} 分"
                                 f"（{min(scores)}~{max(scores)}），建议校准"))

    # 加权总分
    total = sum(dim_avg.get(d, 0) * WEIGHTS[d] for d in DIMS)
    total_5 = total / 5 * 100  # 折算百分制

    # 红线项（先判定：一票否决，优先于一切分数结论）
    redline_issues = []
    for rl in data.get("redlines") or []:
        if rl.get("issue"):
            redline_issues.append(rl.get("issue"))
            findings.append(("FAIL", "Q2", f"红线问题: {rl.get('issue')}"))

    if redline_issues:
        rec = "不予录用（红线一票否决）"
    else:
        if total_5 >= 85:
            rec = "强烈推荐"
        elif total_5 >= 70:
            rec = "推荐"
        elif total_5 >= 55:
            rec = "待定（需补充面试或背调）"
        else:
            rec = "不推荐"
        if divergences:
            rec += "（先校准分歧维度）"

    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    passes = [f for f in findings if f[0] == "PASS"]
    summary = {"fail": len(fails), "warn": len(warns), "pass": len(passes),
               "加权总分(百分制)": round(total_5, 1),
               "维度均分": dim_avg, "录用建议": rec,
               "verdict": "有红线" if fails else ("需校准" if warns else "可决策")}
    return findings, summary


def render_md(findings, summary):
    lines = ["# 面试评分汇总报告", ""]
    lines.append(f"**结论：{summary['verdict']}**｜加权总分 **{summary['加权总分(百分制)']}**｜建议：{summary['录用建议']}")
    lines.append("")
    lines.append("| 维度 | 权重 | 均分 |")
    lines.append("|---|---|---|")
    for d in DIMS:
        lines.append(f"| {d} | {int(WEIGHTS[d] * 100)}% | {summary['维度均分'].get(d, '-')} |")
    lines.append("")
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    for lv, code, msg in findings:
        lines.append(f"- {icon[lv]} **[{code}]** {msg}")
    lines.append("")
    lines.append("> 脚本只做汇总与分歧提示，不替代用人决策。")
    return "\n".join(lines)


SAMPLE = {
    "interviewers": [
        {"name": "HR", "scores": {"专业能力": 3, "问题解决": 4, "沟通协作": 4,
                                  "执行力": 4, "学习成长": 4, "文化匹配": 3}},
        {"name": "用人经理", "scores": {"专业能力": 4, "问题解决": 2, "沟通协作": 4,
                                        "执行力": 4, "学习成长": 4, "文化匹配": 4}},
        {"name": "交叉面试官", "scores": {"专业能力": 4, "问题解决": 4, "沟通协作": 3,
                                          "执行力": 3, "学习成长": 3, "文化匹配": 4}},
    ],
    "redlines": [],
}


def selftest():
    findings, summary = check(SAMPLE)
    print(render_md(findings, summary))
    codes = [(lv, c) for lv, c, _ in findings]
    assert ("WARN", "Q1") in codes, "应检出问题解决维度分歧 4 vs 2"
    # 专业能力均分 (3+4+4)/3=3.67; 问题解决 (4+2+4)/3=3.33...
    total = summary["加权总分(百分制)"]
    expected = ((3.6667 * 0.3 + 3.3333 * 0.2 + 3.6667 * 0.15 + 3.6667 * 0.15
                 + 3.6667 * 0.1 + 3.6667 * 0.1) / 5) * 100
    assert abs(total - round(expected, 1)) < 0.5, f"加权总分错: {total} vs {expected:.1f}"
    # 红线场景
    rl = {"interviewers": SAMPLE["interviewers"], "redlines": [{"issue": "履历时间断层未说明"}]}
    f2, s2 = check(rl)
    assert s2["verdict"] == "有红线" and "先校准" not in s2["录用建议"]
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="结构化面试评分汇总")
    ap.add_argument("--file", help="评分 JSON 文件")
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
