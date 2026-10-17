#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
archive_check.py — 消防档案记录体检脚本

检查项:
  Q1 档案覆盖   基本情况 9 项 + 管理情况 9 项
  Q2 更新频次   巡查/检查/培训/演练/全面检测/电气检测 近12(或6)个月覆盖
  Q3 签字完整   记录有检查人且已签字; 有被检查负责人
  Q4 整改闭环   隐患有责任人+期限; 已整改有复查人和复查日期
  Q5 日期逻辑   整改日期不早于发现日期; 期限不早于发现日期

用法:
  python archive_check.py --file 档案记录.json [--today 2026-10-13] [--format md|json]
  python archive_check.py --selftest
"""
import argparse
import json
import sys
from datetime import date, timedelta

BASIC_FILES = ["单位概况与重点部位", "消防审核验收备案文书", "消防组织与责任人",
               "消防安全制度", "消防设施器材台账", "专职/义务消防队",
               "重点工种人员", "新产品防火材料合格证明", "灭火和应急疏散预案"]
MANAGEMENT_FILES = ["法律文书", "设施定期检查记录", "全面检测报告",
                    "隐患整改情况记录", "防火检查记录", "防火巡查记录",
                    "电气燃气检测记录", "培训记录", "演练记录"]

# type -> (月数上限, 最少条数, 说明)
FREQ_RULES = {
    "防火巡查": (1, 25, "每日/每班"),
    "防火检查": (12, 1, "每月至少一次"),
    "消防安全培训": (12, 1, "每年至少一次"),
    "预案演练": (6, 1, "重点单位每半年一次"),
    "建筑消防设施全面检测": (12, 1, "每年至少一次"),
    "电气检测": (12, 1, "每年至少一次"),
    "燃气检测": (12, 1, "每年至少一次"),
}


def months_between(d1: date, d2: date) -> int:
    m = (d2.year - d1.year) * 12 + (d2.month - d1.month)
    if d2.day < d1.day:
        m -= 1
    return max(m, 0)


def parse_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def check(data: dict, today: date):
    findings = []

    # ---- Q1 覆盖 ----
    have_basic = set(data.get("basic_files") or [])
    have_mgmt = set(data.get("management_files") or [])
    miss_b = [x for x in BASIC_FILES if x not in have_basic]
    miss_m = [x for x in MANAGEMENT_FILES if x not in have_mgmt]
    if miss_b:
        findings.append(("FAIL", "Q1", f"基本情况档案缺项: {', '.join(miss_b)}"))
    if miss_m:
        findings.append(("FAIL", "Q1", f"管理情况档案缺项: {', '.join(miss_m)}"))
    if not miss_b and not miss_m:
        findings.append(("PASS", "Q1", "两类档案 18 项全覆盖"))

    # ---- Q2 频次 ----
    records = data.get("records") or []
    by_type = {}
    for r in records:
        by_type.setdefault(r.get("type"), []).append(r)
    for rtype, (months, min_count, desc) in FREQ_RULES.items():
        recs = [r for r in by_type.get(rtype, []) if parse_date(r.get("date"))]
        recent = [r for r in recs
                  if months_between(parse_date(r["date"]), today) <= months]
        if len(recent) < min_count:
            findings.append(("FAIL", "Q2",
                             f"{rtype}近 {months} 个月仅 {len(recent)} 条，低于下限（{desc}）"))
        else:
            findings.append(("PASS", "Q2",
                             f"{rtype}近 {months} 个月 {len(recent)} 条，达标（{desc}）"))

    # ---- Q3 签字 ----
    for r in records:
        d = r.get("date")
        tag = f"{r.get('type')}({d})"
        if not r.get("checker"):
            findings.append(("WARN", "Q3", f"{tag} 缺检查人"))
        if not r.get("signed"):
            findings.append(("WARN", "Q3", f"{tag} 未签字（或未标注已签字）"))

    # ---- Q4 整改闭环 ----
    rects = data.get("rectifications") or []
    for rc in rects:
        item = (rc.get("hazard") or "未命名隐患")[:20]
        if not rc.get("owner") or not rc.get("deadline"):
            findings.append(("FAIL", "Q4", f"隐患「{item}」缺责任人或完成期限"))
        rd = parse_date(rc.get("rectified_date"))
        if rd and not rc.get("reviewer"):
            findings.append(("WARN", "Q4", f"隐患「{item}」已整改但缺复查人"))

    # ---- Q5 日期逻辑 ----
    for rc in rects:
        found = parse_date(rc.get("found_date"))
        item = (rc.get("hazard") or "未命名隐患")[:20]
        rd = parse_date(rc.get("rectified_date"))
        dl = parse_date(rc.get("deadline"))
        if found and rd and rd < found:
            findings.append(("FAIL", "Q5", f"隐患「{item}」整改日期早于发现日期"))
        if found and dl and dl < found:
            findings.append(("WARN", "Q5", f"隐患「{item}」完成期限早于发现日期"))

    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    passes = [f for f in findings if f[0] == "PASS"]
    summary = {"fail": len(fails), "warn": len(warns), "pass": len(passes),
               "verdict": "不合格" if fails else ("有瑕疵" if warns else "合格")}
    return findings, summary


def render_md(findings, summary):
    lines = ["# 消防档案记录体检报告", ""]
    lines.append(f"**结论：{summary['verdict']}**（FAIL {summary['fail']} / WARN {summary['warn']} / PASS {summary['pass']}）")
    lines.append("")
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    for lv, code, msg in findings:
        lines.append(f"- {icon[lv]} **[{code}]** {msg}")
    lines.append("")
    lines.append("> 脚本只做结构与逻辑检查，不判定记录内容真伪。")
    return "\n".join(lines)


SAMPLE = {
    "basic_files": BASIC_FILES,
    "management_files": [x for x in MANAGEMENT_FILES if x != "电气燃气检测记录"],
    "records": [
        {"type": "防火巡查", "date": "2026-10-10", "checker": "张三", "signed": True},
        {"type": "防火巡查", "date": "2026-10-09", "checker": "张三", "signed": True},
        {"type": "防火巡查", "date": "2026-10-08", "checker": "", "signed": False},
        {"type": "防火检查", "date": "2026-10-05", "checker": "李四", "signed": True},
        {"type": "防火检查", "date": "2026-09-05", "checker": "李四", "signed": True},
        {"type": "消防安全培训", "date": "2026-05-20", "checker": "王五", "signed": True},
        {"type": "预案演练", "date": "2026-06-18", "checker": "赵六", "signed": True},
        {"type": "建筑消防设施全面检测", "date": "2026-01-25", "checker": "检测机构", "signed": True},
    ],
    "rectifications": [
        {"hazard": "二层防火门闭门器损坏", "found_date": "2026-09-05", "owner": "工程部",
         "deadline": "2026-09-30", "rectified_date": "2026-09-28", "reviewer": "李四"},
        {"hazard": "车库出口堵塞", "found_date": "2026-10-06", "owner": "物业",
         "deadline": "", "rectified_date": "2026-10-08", "reviewer": ""},
    ],
}


def selftest():
    data = json.loads(json.dumps(SAMPLE))
    findings, summary = check(data, date(2026, 10, 13))
    print(render_md(findings, summary))
    codes = [(lv, c) for lv, c, _ in findings]
    assert ("FAIL", "Q1") in codes, "应检出缺档案项"
    assert ("FAIL", "Q2") in codes, "应检出电气检测断档"
    assert ("WARN", "Q3") in codes, "应检出未签字记录"
    assert ("FAIL", "Q4") in codes, "应检出隐患无期限"
    assert ("WARN", "Q4") in codes, "应检出已整改无复查人"
    # 全合规场景
    good = json.loads(json.dumps(SAMPLE))
    good["management_files"] = MANAGEMENT_FILES
    patrol = []
    for i in range(30):
        ds = (date(2026, 9, 14) + timedelta(days=i)).isoformat()
        patrol.append({"type": "防火巡查", "date": ds, "checker": "张三", "signed": True})
        patrol.append({"type": "防火巡查", "date": ds, "checker": "李四", "signed": True})
    good["records"] = [r for r in good["records"] if r["type"] != "防火巡查"] + patrol
    good["records"].append({"type": "电气检测", "date": "2026-03-11", "checker": "检测机构", "signed": True})
    good["records"].append({"type": "燃气检测", "date": "2026-03-11", "checker": "检测机构", "signed": True})
    good["rectifications"][1]["deadline"] = "2026-10-20"
    good["rectifications"][1]["reviewer"] = "李四"
    f2, s2 = check(good, date(2026, 10, 13))
    assert s2["verdict"] == "合格", f"全合规样本应判合格，实际: {s2}"
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="消防档案记录体检")
    ap.add_argument("--file", help="档案记录 JSON 文件")
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
    if args.format == "json":
        print(json.dumps({"summary": summary,
                          "findings": [{"level": l, "code": c, "msg": m} for l, c, m in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print(render_md(findings, summary))
    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
