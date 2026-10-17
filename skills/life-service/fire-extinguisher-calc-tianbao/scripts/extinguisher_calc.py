#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extinguisher_calc.py — 灭火器配置设计核算计算器

公式: Q = K·S/U; 每点 Qe = Q/N; 单具按 2A 折算具数
参数:
  --area S(㎡)  --level 严重/中/轻  --has-hydrant  --has-system
  --underground/--entertainment/--mall  (K×1.3 场景)
  --points N  设置点数量
示例:
  python extinguisher_calc.py --area 1200 --level 中 --has-hydrant --points 4
  python extinguisher_calc.py --selftest
"""
import argparse
import sys

U_TABLE = {"严重": 50, "中": 75, "轻": 100}
MIN_POINT = {"严重": 3, "中": 2, "轻": 1}          # A 类单点最低灭火级别(A)
MAX_DIST = {"严重": 15, "中": 20, "轻": 25}         # 手提式最大保护距离(m)


def calc(area, level, has_hydrant=False, has_system=False,
         k13=False, points=1, per_unit_a=2):
    u = U_TABLE[level]
    k = 1.0
    if has_hydrant and has_system:
        k = 0.5
    elif has_hydrant:
        k = 0.9
    elif has_system:
        k = 0.7
    if k13:
        k *= 1.3
    q = k * area / u
    qe = q / max(points, 1)
    min_qe = MIN_POINT[level]
    units_needed = max(-(-qe // 1), min_qe)  # 每点不低于最低级别
    units_total = q
    total_extinguishers = -(-units_total // per_unit_a)
    return {
        "S": area, "level": level, "U": u, "K": round(k, 3),
        "Q(总灭火级别)": round(q, 2),
        "设置点": points,
        "每点级别Qe": round(qe, 2),
        "每点最低级别": min_qe,
        "每点判定": "达标" if qe >= min_qe else f"不足(需≥{min_qe}A)",
        "建议具数(每点,按{0}A折算)".format(per_unit_a): int(-(-units_needed // per_unit_a)),
        "总建议具数": int(total_extinguishers),
        "最大保护距离(m)": MAX_DIST[level],
    }


def render(d):
    lines = ["# 灭火器配置核算结果", ""]
    lines.append("| 项目 | 数值 |")
    lines.append("|---|---|")
    for k, v in d.items():
        lines.append(f"| {k} | {v} |")
    lines.append("")
    lines.append("> 简化口径核算，正式配置以 GB 50140 现行条文和设计文件为准。")
    return "\n".join(lines)


def selftest():
    # 场景1: 中危险级 1200㎡, 有消火栓+灭火系统, 4 个点 → Q=0.5*1200/75=8, Qe=2
    r1 = calc(1200, "中", has_hydrant=True, has_system=True, points=4)
    assert abs(r1["Q(总灭火级别)"] - 8.0) < 0.01, f"Q 计算错: {r1}"
    assert r1["每点级别Qe"] == 2.0 and r1["每点判定"] == "达标", "每点 2A 应达标"
    assert r1["总建议具数"] == 4, "总具数应为 4"
    # 场景2: 同面积地下场所 K=0.5*1.3=0.65 → Q=10.4, Qe=2.6
    r2 = calc(1200, "中", has_hydrant=True, has_system=True, k13=True, points=4)
    assert abs(r2["Q(总灭火级别)"] - 10.4) < 0.01, f"地下 K 计算错: {r2}"
    assert r2["每点判定"] == "达标" and r2["K"] == 0.65
    # 场景3: 严重危险级 500㎡ 无设施 → Q=10, Qe=5, 每点最低 3A
    r3 = calc(500, "严重", points=2)
    assert abs(r3["Q(总灭火级别)"] - 10.0) < 0.01, f"严重级 Q 计算错: {r3}"
    assert r3["每点最低级别"] == 3 and r3["每点级别Qe"] == 5.0
    print(render(r1))
    print(render(r2))
    print(render(r3))
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="灭火器配置核算计算器")
    ap.add_argument("--area", type=float, help="计算单元面积 ㎡")
    ap.add_argument("--level", choices=["严重", "中", "轻"], default="中")
    ap.add_argument("--has-hydrant", action="store_true")
    ap.add_argument("--has-system", action="store_true")
    ap.add_argument("--underground", action="store_true")
    ap.add_argument("--entertainment", action="store_true")
    ap.add_argument("--mall", action="store_true")
    ap.add_argument("--points", type=int, default=1)
    ap.add_argument("--per-unit-a", type=float, default=2, help="单具灭火级别(A)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.area:
        ap.error("必须提供 --area 或 --selftest")
    k13 = args.underground or args.entertainment or args.mall
    print(render(calc(args.area, args.level, args.has_hydrant, args.has_system,
                      k13, args.points, args.per_unit_a)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
