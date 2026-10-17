#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lane_check.py — 消防车道、回车场、登高场地与消防救援口核算脚本

检查项:
  Q1 车道尺寸   净宽>=4m; 净空>=4m; 坡度<=8%
  Q2 回车场     尽头式长度>35m 需回车场; 尺寸按建筑类型(12x12/15x15/18x18)
  Q3 登高场地   宽度>=10m; 距建筑 5~10m; 坡度<=3%
  Q4 消防救援口 每防火分区>=2个; 间距<=20m; 净宽净高>=1.0m

用法:
  python lane_check.py --file 车道.json [--format md|json]
  python lane_check.py --selftest
"""
import argparse
import json
import sys


def check(data: dict):
    findings = []

    lanes = data.get("lanes") or []
    for i, ln in enumerate(lanes, 1):
        tag = f"车道{i}({ln.get('name') or '未命名'})"
        w, c, s = ln.get("width"), ln.get("clearance"), ln.get("slope")
        dead_end = ln.get("dead_end_length")
        if w is not None and w < 4:
            findings.append(("FAIL", "Q1", f"{tag} 净宽 {w}m < 4m"))
        if c is not None and c < 4:
            findings.append(("FAIL", "Q1", f"{tag} 净空 {c}m < 4m"))
        if s is not None and s > 8:
            findings.append(("FAIL", "Q1", f"{tag} 坡度 {s}% > 8%"))

        # Q2 回车场
        turn = ln.get("turnaround") or {}
        if dead_end is not None and dead_end > 35:
            tw, th = turn.get("width"), turn.get("depth")
            if not turn.get("exists"):
                findings.append(("FAIL", "Q2", f"{tag} 尽头式 {dead_end}m > 35m 但无回车场"))
            elif (tw or 0) < 12 or (th or 0) < 12:
                findings.append(("FAIL", "Q2",
                                 f"{tag} 回车场 {tw}×{th}m 小于下限（一般 12×12，高层 15×15）"))
            else:
                findings.append(("PASS", "Q2", f"{tag} 尽头式回车场合规"))

    # Q3 登高场地
    yards = data.get("aerial_yards") or []
    for i, y in enumerate(yards, 1):
        tag = f"登高场地{i}"
        width, dist, slope = y.get("width"), y.get("distance_to_building"), y.get("slope")
        if width is not None and width < 10:
            findings.append(("FAIL", "Q3", f"{tag} 宽度 {width}m < 10m"))
        if dist is not None and not (5 <= dist <= 10):
            findings.append(("FAIL", "Q3", f"{tag} 距建筑 {dist}m 超出 5~10m"))
        if slope is not None and slope > 3:
            findings.append(("FAIL", "Q3", f"{tag} 坡度 {slope}% > 3%"))

    # Q4 消防救援口
    openings = data.get("rescue_openings") or {}
    count = openings.get("count_per_zone")
    spacing = openings.get("max_spacing")
    size = openings.get("size") or {}
    if count is not None and count < 2:
        findings.append(("FAIL", "Q4", f"每防火分区消防救援口 {count} 个 < 2"))
    if spacing is not None and spacing > 20:
        findings.append(("FAIL", "Q4", f"消防救援口间距 {spacing}m > 20m"))
    if size and (size.get("width", 0) < 1.0 or size.get("height", 0) < 1.0):
        findings.append(("FAIL", "Q4",
                         f"消防救援口净宽净高 {size.get('width')}×{size.get('height')}m 小于 1.0m"))

    fails = [f for f in findings if f[0] == "FAIL"]
    passes = [f for f in findings if f[0] == "PASS"]
    return findings, {"fail": len(fails), "pass": len(passes),
                      "verdict": "不合格" if fails else "合格"}


def render_md(findings, summary):
    lines = ["# 消防车道与登高场地核算报告", ""]
    lines.append(f"**结论：{summary['verdict']}**（FAIL {summary['fail']} / PASS {summary['pass']}）")
    lines.append("")
    icon = {"PASS": "✅", "FAIL": "❌"}
    for lv, code, msg in findings:
        lines.append(f"- {icon[lv]} **[{code}]** {msg}")
    lines.append("")
    lines.append("> 脚本只做数值核算，不判定设计合规性。")
    return "\n".join(lines)


SAMPLE = {
    "lanes": [
        {"name": "小区主干道", "width": 4.2, "clearance": 4.5, "slope": 5,
         "dead_end_length": 40, "turnaround": {"exists": True, "width": 12, "depth": 12}},
        {"name": "北侧支路", "width": 3.6, "clearance": 4.2, "slope": 10,
         "dead_end_length": 50, "turnaround": {"exists": False}},
    ],
    "aerial_yards": [
        {"width": 12, "distance_to_building": 8, "slope": 2},
        {"width": 8, "distance_to_building": 14, "slope": 4},
    ],
    "rescue_openings": {"count_per_zone": 1, "max_spacing": 25, "size": {"width": 1.2, "height": 1.0}},
}


def selftest():
    findings, summary = check(SAMPLE)
    print(render_md(findings, summary))
    codes = [(lv, c) for lv, c, _ in findings]
    assert ("FAIL", "Q1") in codes, "应检出路宽/坡度不足"
    assert ("FAIL", "Q2") in codes, "应检出无回车场"
    assert ("FAIL", "Q3") in codes, "应检出登高场地宽度/距离/坡度"
    assert ("FAIL", "Q4") in codes, "应检出消防救援口数量/间距"
    good = {
        "lanes": [{"name": "主路", "width": 4.5, "clearance": 4.5, "slope": 5, "dead_end_length": 20}],
        "aerial_yards": [{"width": 12, "distance_to_building": 7, "slope": 2}],
        "rescue_openings": {"count_per_zone": 2, "max_spacing": 15, "size": {"width": 1.2, "height": 1.1}},
    }
    f2, s2 = check(good)
    assert s2["fail"] == 0, f"全合规样本不应 FAIL，实际 {s2}"
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="消防车道与登高场地核算")
    ap.add_argument("--file", help="车道 JSON 文件")
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
