#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jd_check.py — JD 体检与招聘漏斗计算脚本

JD 体检:
  Q1 七段完整   名称/汇报线/职责/资格/薪酬/地点/团队
  Q2 职责质量   动词开头; "参与/协助"占比
  Q3 资格拆分   硬性/加分分开; 硬性项<=5
  Q4 合规       歧视性表述关键词
漏斗计算:
  --funnel 模式: 曝光→沟通→简历→面试→offer→入职 各环节转化率

用法:
  python jd_check.py --file JD.json
  python jd_check.py --funnel --impressions 5000 --chats 800 --resumes 120 --interviews 20 --offers 5 --onboard 4
  python jd_check.py --selftest
"""
import argparse
import json
import sys

SECTIONS = ["title", "reporting", "responsibilities", "requirements",
            "compensation", "location", "team"]
PASSIVE_WORDS = ["参与", "协助"]
DISCRIM_WORDS = ["男性优先", "女性优先", "年龄不超过", "限本地户籍", "婚育", "只招"]


def check_jd(jd: dict):
    findings = []

    miss = [s for s in SECTIONS if not jd.get(s)]
    if miss:
        findings.append(("FAIL", "Q1", f"JD 缺段: {', '.join(miss)}"))

    resp = jd.get("responsibilities") or []
    passive = sum(1 for r in resp if any(w in str(r) for w in PASSIVE_WORDS))
    if resp and passive / len(resp) >= 0.5:
        findings.append(("WARN", "Q2", f"{passive}/{len(resp)} 条职责含'参与/协助'，请改为动词主导"))

    reqs = jd.get("requirements") or {}
    hard = reqs.get("hard") or []
    if not reqs.get("preferred") and hard:
        findings.append(("WARN", "Q3", "只有硬性要求没有加分项，可能过度收紧"))
    if len(hard) > 5:
        findings.append(("WARN", "Q3", f"硬性项 {len(hard)} 条 > 5，将显著压低简历量"))

    text = json.dumps(jd, ensure_ascii=False)
    hits = [w for w in DISCRIM_WORDS if w in text]
    if hits:
        findings.append(("FAIL", "Q4", f"涉嫌歧视/违法表述: {', '.join(hits)}"))

    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    passes = [f for f in findings if f[0] == "PASS"]
    return findings, {"fail": len(fails), "warn": len(warns), "pass": len(passes),
                      "verdict": "不合格" if fails else ("有瑕疵" if warns else "合格")}


def funnel(impressions, chats, resumes, interviews, offers, onboard):
    def pct(a, b):
        return f"{(a / b * 100):.1f}%" if b else "-"
    stages = [
        ("曝光", impressions), ("沟通", chats), ("简历", resumes),
        ("面试", interviews), ("Offer", offers), ("入职", onboard),
    ]
    lines = ["# 招聘漏斗分析", "", "| 环节 | 数量 | 上一环节转化率 |", "|---|---|---|"]
    prev = None
    for name, n in stages:
        lines.append(f"| {name} | {n} | {pct(n, prev) if prev else '-'} |")
        prev = n
    lines.append("")
    # 瓶颈诊断
    rates = {"沟通/曝光": chats / impressions if impressions else 0,
             "简历/沟通": resumes / chats if chats else 0,
             "面试/简历": interviews / resumes if resumes else 0,
             "Offer/面试": offers / interviews if interviews else 0,
             "入职/Offer": onboard / offers if offers else 0}
    advice = {
        "沟通/曝光": "薪酬区间或 JD 开头不吸引，优先改这两处",
        "简历/沟通": "需求不匹配或回复太慢，检查硬性项与响应时效",
        "面试/简历": "邀约话术或时间安排问题，优化邀约与确认",
        "Offer/面试": "薪酬竞争力或面试体验问题，复盘面试官反馈",
        "入职/Offer": "薪酬谈判或入职跟进问题，提前锁定候选人意向",
    }
    bottleneck = min(rates, key=lambda k: rates[k])
    lines.append(f"**最大瓶颈：{bottleneck}（{rates[bottleneck] * 100:.1f}%）** → {advice[bottleneck]}")
    return "\n".join(lines)


def render_md(findings, summary):
    lines = ["# JD 体检报告", ""]
    lines.append(f"**结论：{summary['verdict']}**（FAIL {summary['fail']} / WARN {summary['warn']}）")
    lines.append("")
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    for lv, code, msg in findings:
        lines.append(f"- {icon[lv]} **[{code}]** {msg}")
    return "\n".join(lines)


SAMPLE_JD = {
    "title": "消防维保工程师",
    "reporting": "向工程部经理汇报",
    "responsibilities": ["负责消防设施月度维保", "参与消防检测报告编制",
                         "协助客户现场排查", "负责维保记录归档"],
    "requirements": {"hard": ["大专及以上", "一级注册消防工程师", "3年以上维保经验",
                              "熟练操作检测仪器", "能适应高空作业"],
                     "preferred": []},
    "compensation": "",
    "location": "上海（含驻场）",
    "team": "工程部 8 人",
}


def selftest():
    findings, summary = check_jd(SAMPLE_JD)
    print(render_md(findings, summary))
    codes = [(lv, c) for lv, c, _ in findings]
    assert ("FAIL", "Q1") in codes, "应检出缺薪酬段"
    assert ("WARN", "Q2") in codes, "应检出被动动词占比过高(2/4)"
    assert ("WARN", "Q3") in codes, "应检出硬性 5 条+无加分项"
    good = dict(SAMPLE_JD)
    good["compensation"] = "10-15K·13薪"
    good["requirements"] = {"hard": ["大专及以上", "一级注册消防工程师", "3年以上经验"],
                            "preferred": ["有商场项目经验", "持电工证"]}
    good["responsibilities"] = ["负责消防设施月度维保", "编制消防检测报告",
                                "组织客户现场排查", "归档维保记录"]
    f2, s2 = check_jd(good)
    assert s2["fail"] == 0 and s2["warn"] == 0, f"全合规 JD 应无 FAIL/WARN，实际 {s2}"
    out = funnel(5000, 800, 120, 20, 5, 4)
    assert "最大瓶颈" in out
    print(out)
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="JD 体检与招聘漏斗")
    ap.add_argument("--file", help="JD JSON 文件")
    ap.add_argument("--funnel", action="store_true", help="漏斗计算模式")
    ap.add_argument("--impressions", type=int)
    ap.add_argument("--chats", type=int)
    ap.add_argument("--resumes", type=int)
    ap.add_argument("--interviews", type=int)
    ap.add_argument("--offers", type=int)
    ap.add_argument("--onboard", type=int)
    ap.add_argument("--format", choices=["md", "json"], default="md")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.funnel:
        vals = [args.impressions, args.chats, args.resumes, args.interviews, args.offers, args.onboard]
        if any(v is None for v in vals):
            ap.error("漏斗模式需提供全部六级数量")
        print(funnel(*vals))
        return 0
    if not args.file:
        ap.error("必须提供 --file / --funnel / --selftest")
    try:
        with open(args.file, encoding="utf-8") as f:
            jd = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"读取失败: {e}", file=sys.stderr)
        return 2
    findings, summary = check_jd(jd)
    if args.format == "json":
        print(json.dumps({"summary": summary,
                          "findings": [{"level": l, "code": c, "msg": m} for l, c, m in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print(render_md(findings, summary))
    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
