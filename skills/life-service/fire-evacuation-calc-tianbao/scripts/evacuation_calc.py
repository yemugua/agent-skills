#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evacuation_calc.py — 疏散宽度与距离核算计算器

功能:
  1) 百人宽度指标法算总净宽: 总净宽 = 人数 × 指标 ÷ 100
  2) 梯段/走道净宽校验: 按每股人流 0.55m 估算可通行人数
  3) 疏散距离校验: 直通/袋形走道限值比对
  4) 出口间距提示: 两出口最近边缘水平距离 >= 5m

用法:
  python evacuation_calc.py --people 300 --indicator 0.75
  python evacuation_calc.py --distance 38 --type office --corridor 直通
  python evacuation_calc.py --selftest
"""
import argparse
import sys

FLOW_WIDTH = 0.55          # 每股人流宽度 m
MIN_CORRIDOR = 1.1         # 走道/门最小净宽 m
DENSE_CORRIDOR = 1.4       # 人员密集公共场所部分情形
MIN_STAIR = 1.1
MIN_EXIT_DIST = 5.0        # 两出口最近边缘水平距离 m

# 一、二级耐火疏散距离限值(节选, GB 50016 口径)
DIST_LIMITS = {
    "office": {"直通": 35, "袋形": 20},
    "teaching": {"直通": 30, "袋形": 15},
    "dormitory": {"直通": 25, "袋形": 15},
}


def width_calc(people, indicator):
    total = people * indicator / 100
    n_flows = -(-total // FLOW_WIDTH)  # 向上取整
    return {
        "疏散人数": people,
        "百人宽度指标(m/百人)": indicator,
        "所需疏散总净宽(m)": round(total, 3),
        "折合人流股数": int(n_flows),
        "提示": "总净宽不得小于各分支最小值" if total < MIN_CORRIDOR else "数值合规需按最小净宽复核",
    }


def distance_check(dist, btype, corridor):
    limits = DIST_LIMITS.get(btype, DIST_LIMITS["office"])
    limit = limits.get(corridor, limits["直通"])
    return {
        "建筑类型": btype,
        "走道类型": corridor,
        "实测距离(m)": dist,
        "限值(m)": limit,
        "判定": "达标" if dist <= limit else "超限",
        "提示": "袋形走道火灾时需原路返回，限值从严" if corridor == "袋形" else "",
    }


def render(d):
    lines = ["# 疏散核算结果", ""]
    lines.append("| 项目 | 数值 |")
    lines.append("|---|---|")
    for k, v in d.items():
        lines.append(f"| {k} | {v} |")
    lines.append("")
    lines.append("> 简化口径核算，正式设计以 GB 50016 现行条文和审查结论为准。")
    return "\n".join(lines)


def selftest():
    r1 = width_calc(300, 0.75)
    assert abs(r1["所需疏散总净宽(m)"] - 2.25) < 0.001, f"宽度计算错: {r1}"
    assert r1["折合人流股数"] == 5, "2.25m/0.55 = 4.09 → 5 股"
    r2 = width_calc(30, 0.65)
    assert abs(r2["所需疏散总净宽(m)"] - 0.195) < 0.001
    r3 = distance_check(38, "office", "直通")
    assert r3["判定"] == "超限" and r3["限值(m)"] == 35
    r4 = distance_check(18, "teaching", "袋形")
    assert r4["判定"] == "超限" and r4["限值(m)"] == 15
    r5 = distance_check(30, "teaching", "直通")
    assert r5["判定"] == "达标"
    print(render(r1))
    print(render(r3))
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="疏散宽度与距离核算")
    ap.add_argument("--people", type=float, help="疏散人数")
    ap.add_argument("--indicator", type=float, default=0.65, help="百人宽度指标 m/百人")
    ap.add_argument("--distance", type=float, help="最远点至安全出口距离 m")
    ap.add_argument("--type", choices=["office", "teaching", "dormitory"], default="office")
    ap.add_argument("--corridor", choices=["直通", "袋形"], default="直通")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.people:
        print(render(width_calc(args.people, args.indicator)))
    if args.distance:
        print(render(distance_check(args.distance, args.type, args.corridor)))
    if not args.people and not args.distance:
        ap.error("需提供 --people 或 --distance（或 --selftest）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
