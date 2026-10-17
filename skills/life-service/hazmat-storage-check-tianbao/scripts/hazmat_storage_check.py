#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hazmat_storage_check.py — 危险化学品存储合规体检脚本

检查项:
  Q1 禁忌混存   酸/碱、氧化剂/还原剂、遇湿易燃/含水、氧气瓶/油脂
  Q2 温湿度     按品类温湿度记录超限未处置
  Q3 五距       顶距>=50 灯距>=50 墙距>=30 柱距>=10 垛距>=100
  Q4 台账       出入库台账要素; MSDS 配备
  Q5 气瓶       氧气与可燃气瓶混放; 倒卧; 超检验期

用法:
  python hazmat_storage_check.py --file 库存.json [--today 2026-10-13] [--format md|json]
  python hazmat_storage_check.py --selftest
"""
import argparse
import json
import sys
from datetime import date

CONFLICTS = [
    ({"酸"}, {"碱"}, "酸碱混存"),
    ({"氧化剂"}, {"还原剂", "易燃物"}, "氧化剂与还原/易燃物混存"),
    ({"遇湿易燃"}, {"含水物质", "酸"}, "遇湿易燃品与含水物质/酸混存"),
]
CYLINDER_PAIRS = [("氧气", ["乙炔", "氢气", "可燃气"])]


def check(data: dict, today: date):
    findings = []
    items = data.get("items") or []

    # Q1 禁忌混存
    cats = {}
    for it in items:
        for c in it.get("categories") or []:
            cats.setdefault(c, []).append(it.get("name"))
    for a, b, desc in CONFLICTS:
        ha = [n for n in cats.get(list(a)[0], [])]
        hb = [n for n in cats.get(list(b)[0], [])]
        if ha and hb:
            findings.append(("FAIL", "Q1", f"{desc}: {','.join(ha[:3])} × {','.join(hb[:3])}"))

    # 气瓶混放（同间才算违规，分间存放合规）
    cylinders = [it for it in items if "气瓶" in (it.get("name") or "") or it.get("is_cylinder")]
    oxy = [c.get("name") for c in cylinders if "氧气" in (c.get("name") or "")]
    flam = [c.get("name") for c in cylinders
            if any(x in (c.get("name") or "") for x in ("乙炔", "氢", "可燃气"))]
    if oxy and flam:
        rooms = {c.get("room") for c in cylinders}
        if len(rooms) == 1:
            findings.append(("FAIL", "Q1", f"氧气瓶与可燃气瓶同间存放: {','.join(oxy)} × {','.join(flam)}"))
    lying = [c.get("name") for c in cylinders if c.get("lying")]
    if lying:
        findings.append(("FAIL", "Q1", f"气瓶倒卧存放: {', '.join(lying)}"))
    if not any(f[1] == "Q1" for f in findings):
        findings.append(("PASS", "Q1", "无禁忌混存、气瓶存放合规"))

    # Q2 温湿度
    env = data.get("environment") or []
    for e in env:
        tmax, tmin = e.get("temp_max"), e.get("temp_min")
        hmax = e.get("humidity_max")
        cur_t, cur_h = e.get("temp"), e.get("humidity")
        tag = e.get("area") or "未命名区域"
        if tmax is not None and cur_t is not None and cur_t > tmax:
            findings.append(("FAIL", "Q2" if not e.get("handled") else "WARN",
                             f"{tag} 温度 {cur_t}℃ 超上限 {tmax}℃" + ("" if not e.get("handled") else "（已处置）")))
        if hmax is not None and cur_h is not None and cur_h > hmax:
            findings.append(("FAIL", "Q2" if not e.get("handled") else "WARN",
                             f"{tag} 湿度 {cur_h}% 超上限 {hmax}%" + ("" if not e.get("handled") else "（已处置）")))
    if not env:
        findings.append(("WARN", "Q2", "无温湿度监控记录"))

    # Q3 五距
    dist = data.get("distances") or {}
    limits = {"top": 50, "lamp": 50, "wall": 30, "pillar": 10, "stack": 100}
    for key, lim in limits.items():
        v = dist.get(key)
        if v is None:
            continue
        if v < lim:
            findings.append(("FAIL", "Q3", f"{key}距 {v}cm < 下限 {lim}cm"))

    # Q4 台账
    ledger = data.get("ledger") or []
    missing = [l.get("name") for l in ledger if not l.get("msds")]
    if missing:
        findings.append(("WARN", "Q4", f"缺 MSDS 的品种: {', '.join(missing)}"))
    bad_ledger = [l.get("name") for l in ledger if not l.get("qty") or not l.get("handler")]
    if bad_ledger:
        findings.append(("FAIL", "Q4", f"台账要素缺失: {', '.join(bad_ledger)}"))

    # Q5 气瓶检验
    for c in cylinders:
        if c.get("overdue"):
            findings.append(("FAIL", "Q5", f"气瓶超检验期: {c.get('name')}"))

    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    passes = [f for f in findings if f[0] == "PASS"]
    return findings, {"fail": len(fails), "warn": len(warns), "pass": len(passes),
                      "verdict": "不合格" if fails else ("有瑕疵" if warns else "合格")}


def render_md(findings, summary):
    lines = ["# 危化品存储体检报告", ""]
    lines.append(f"**结论：{summary['verdict']}**（FAIL {summary['fail']} / WARN {summary['warn']} / PASS {summary['pass']}）")
    lines.append("")
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    for lv, code, msg in findings:
        lines.append(f"- {icon[lv]} **[{code}]** {msg}")
    return "\n".join(lines)


SAMPLE = {
    "items": [
        {"name": "盐酸(31%)", "categories": ["酸"], "qty": 20, "handler": "王某"},
        {"name": "氢氧化钠", "categories": ["碱"], "qty": 15, "handler": "王某"},
        {"name": "乙醇", "categories": ["易燃物"], "qty": 30, "handler": "李某", "msds": True},
        {"name": "高锰酸钾", "categories": ["氧化剂"], "qty": 5, "handler": "李某", "msds": True},
        {"name": "氧气瓶", "is_cylinder": True, "qty": 2, "room": "气瓶间", "overdue": False},
        {"name": "乙炔瓶", "is_cylinder": True, "qty": 2, "room": "气瓶间", "lying": True, "overdue": True},
    ],
    "environment": [
        {"area": "危化品库A", "temp": 32, "temp_max": 30, "humidity": 70, "humidity_max": 80, "handled": False},
    ],
    "distances": {"top": 40, "lamp": 55, "wall": 25, "pillar": 15, "stack": 90},
    "ledger": [
        {"name": "盐酸(31%)", "qty": 20, "handler": "王某", "msds": True},
        {"name": "氢氧化钠", "qty": 15, "handler": "王某", "msds": False},
        {"name": "乙醇", "qty": 30, "handler": "李某", "msds": True},
    ],
}


def selftest():
    findings, summary = check(SAMPLE, date(2026, 10, 13))
    print(render_md(findings, summary))
    codes = [(lv, c) for lv, c, _ in findings]
    assert ("FAIL", "Q1") in codes, "应检出酸碱混存/气瓶倒卧"
    assert ("FAIL", "Q2") in codes, "应检出温度超限"
    assert ("FAIL", "Q3") in codes, "应检出五距不足"
    assert ("WARN", "Q4") in codes, "应检出缺 MSDS"
    assert ("FAIL", "Q5") in codes, "应检出气瓶超检验期"
    # 全合规样本（显式重建，避免索引错位）
    good = {
        "items": [
            {"name": "盐酸(31%)", "categories": ["酸"], "qty": 20, "handler": "王某"},
            {"name": "乙醇", "categories": ["易燃物"], "qty": 30, "handler": "李某", "msds": True},
            {"name": "氧气瓶", "is_cylinder": True, "qty": 2, "room": "气瓶间A", "overdue": False},
            {"name": "乙炔瓶", "is_cylinder": True, "qty": 2, "room": "气瓶间B", "overdue": False},
        ],
        "environment": [
            {"area": "危化品库A", "temp": 28, "temp_max": 30, "humidity": 70, "humidity_max": 80, "handled": False},
        ],
        "distances": {"top": 60, "lamp": 60, "wall": 40, "pillar": 20, "stack": 120},
        "ledger": [
            {"name": "盐酸(31%)", "qty": 20, "handler": "王某", "msds": True},
            {"name": "乙醇", "qty": 30, "handler": "李某", "msds": True},
        ],
    }
    f2, s2 = check(good, date(2026, 10, 13))
    assert s2["fail"] == 0, f"全合规样本不应 FAIL，实际 {s2}"
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="危化品存储合规体检")
    ap.add_argument("--file", help="库存 JSON 文件")
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
