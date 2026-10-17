#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
supplier_score.py — 供应商绩效评分计算器

公式: 总分 = 质量×w1 + 交付×w2 + 服务×w3 (默认 0.5/0.3/0.2)
分级: A>=90 / B 75-89 / C 60-74 / D<60

用法:
  python supplier_score.py --quality 98 --delivery 92 --service 85
  python supplier_score.py --selftest
"""
import argparse
import sys

W = {"quality": 0.5, "delivery": 0.3, "service": 0.2}


def tier(score):
    if score >= 90:
        return "A（优秀）", "优先付款、加大份额、减少进货检验"
    if score >= 75:
        return "B（合格）", "维持份额、正常管理"
    if score >= 60:
        return "C（观察）", "限制新订单、要求改进计划、加密检验"
    return "D（不合格）", "停用淘汰、启动替代"


def calc(quality, delivery, service, redline=False):
    total = quality * W["quality"] + delivery * W["delivery"] + service * W["service"]
    if redline:
        total = min(total, 59.9)
    level, advice = tier(total)
    return {
        "质量分(50%)": quality,
        "交付分(30%)": delivery,
        "服务分(20%)": service,
        "加权总分": round(total, 1),
        "等级": level,
        "管理建议": advice,
        "红线": "触红线，直接 D 级" if redline else "无",
    }


def render(d):
    lines = ["# 供应商绩效评分结果", ""]
    lines.append("| 项目 | 数值 |")
    lines.append("|---|---|")
    for k, v in d.items():
        lines.append(f"| {k} | {v} |")
    return "\n".join(lines)


def selftest():
    r1 = calc(98, 92, 85)
    assert abs(r1["加权总分"] - 93.6) < 0.01, f"计算错: {r1}"
    assert r1["等级"].startswith("A")
    r2 = calc(80, 70, 60)
    assert abs(r2["加权总分"] - 73.0) < 0.01
    assert r2["等级"].startswith("C"), "73 分应为 C 级"
    r3 = calc(60, 50, 40)
    assert r3["等级"].startswith("D")
    r4 = calc(95, 95, 95, redline=True)
    assert r4["等级"].startswith("D"), "触红线应直接 D 级"
    print(render(r1))
    print(render(r2))
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="供应商绩效评分")
    ap.add_argument("--quality", type=float)
    ap.add_argument("--delivery", type=float)
    ap.add_argument("--service", type=float)
    ap.add_argument("--redline", action="store_true", help="触红线项")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.quality is None or args.delivery is None or args.service is None:
        ap.error("必须提供 --quality/--delivery/--service（或 --selftest）")
    print(render(calc(args.quality, args.delivery, args.service, args.redline)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
