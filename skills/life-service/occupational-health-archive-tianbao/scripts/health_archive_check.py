#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
health_archive_check.py — 职业健康监护档案与体检合规体检脚本

检查项（按劳动者逐人核对）:
  Q1 档案内容   九项档案内容完整性
  Q2 上岗前体检 有危害接触者必须有岗前检查且早于上岗
  Q3 在岗周期   按危害因素周期; 超期未体检
  Q4 离岗体检   离岗者需离岗时检查(或离岗前90天在岗检查视同)
  Q5 异常闭环   结果"复查/异常/疑似职业病"需有随访记录
  Q6 检查签章   机构与主检医师非空

用法:
  python health_archive_check.py --file 监护档案.json [--today 2026-10-13] [--format md|json]
  python health_archive_check.py --selftest
"""
import argparse
import json
import sys
from datetime import date

ARCHIVE_KEYS = ["职业史", "接触史", "既往史", "家族史", "个人生活史", "检查结果及处理", "职业病诊疗"]
HAZARD_PERIOD_MONTHS = {
    "噪声": 12, "矽尘": 12, "煤尘": 24, "其他粉尘": 24, "化学毒物": 12,
    "高温": 12, "手传振动": 12, "紫外辐射": 12,
}
DEFAULT_PERIOD = 12
ABNORMAL_RESULTS = {"复查", "异常", "疑似职业病", "职业禁忌"}


def parse_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def days_between(d1: date, d2: date) -> int:
    return (d2 - d1).days


def check(data: dict, today: date):
    findings = []
    workers = data.get("workers") or []
    if not workers:
        findings.append(("FAIL", "Q1", "档案中没有任何劳动者记录"))

    for i, w in enumerate(workers, 1):
        name = w.get("name") or f"劳动者{i}"
        hazards = w.get("hazards") or []

        # Q1 档案内容
        arch = w.get("archive") or {}
        missing = [k for k in ARCHIVE_KEYS if not arch.get(k)]
        if missing:
            findings.append(("WARN", "Q1", f"{name} 档案缺项: {', '.join(missing)}"))

        # Q2 上岗前体检
        hire = parse_date(w.get("hire_date"))
        pre = parse_date(w.get("pre_exam_date"))
        if hazards:
            if not pre:
                findings.append(("FAIL", "Q2", f"{name} 有危害接触作业但无上岗前体检记录"))
            elif hire and pre > hire:
                findings.append(("FAIL", "Q2",
                                 f"{name} 岗前体检({pre})晚于上岗日期({hire})"))

        # Q3 在岗周期
        periodic = sorted((p for p in (w.get("periodic") or []) if parse_date(p.get("date"))),
                          key=lambda p: parse_date(p["date"]))
        if not periodic:
            findings.append(("FAIL", "Q3", f"{name} 无任何在岗期间体检记录"))
        else:
            last = parse_date(periodic[-1]["date"])
            for hz in hazards:
                months = HAZARD_PERIOD_MONTHS.get(hz, DEFAULT_PERIOD)
                gap_days = days_between(last, today)
                if gap_days > months * 31:
                    findings.append(("FAIL", "Q3",
                                     f"{name} {hz}在岗体检距今 {gap_days} 天，超过 {months} 个月周期"))

        # Q4 离岗体检
        left = parse_date(w.get("left_date"))
        if left:
            exit_exam = parse_date(w.get("exit_exam_date"))
            if exit_exam and exit_exam <= left and days_between(exit_exam, left) <= 90:
                pass  # 合规
            elif periodic and days_between(parse_date(periodic[-1]["date"]), left) <= 90:
                pass  # 视同离岗检查
            else:
                findings.append(("FAIL", "Q4", f"{name} 已离岗({left})但无合规的离岗时体检"))

        # Q5 异常闭环
        for p in periodic:
            if p.get("result") in ABNORMAL_RESULTS and not w.get("abnormal_followup"):
                findings.append(("FAIL", "Q5",
                                 f"{name} {p.get('date')} 检查结果「{p.get('result')}」但无随访/复查记录"))
                break

        # Q6 检查签章
        for p in periodic:
            if not p.get("agency") or not p.get("physician"):
                findings.append(("WARN", "Q6",
                                 f"{name} {p.get('date')} 检查记录缺机构或主检医师签章"))
                break

    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    passes = [f for f in findings if f[0] == "PASS"]
    summary = {"fail": len(fails), "warn": len(warns), "pass": len(passes),
               "verdict": "不合格" if fails else ("有瑕疵" if warns else "合格")}
    return findings, summary


def render_md(findings, summary, worker_count):
    lines = ["# 职业健康监护档案体检报告", ""]
    lines.append(f"**覆盖劳动者：{worker_count} 人**")
    lines.append(f"**结论：{summary['verdict']}**（FAIL {summary['fail']} / WARN {summary['warn']}）")
    lines.append("")
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    for lv, code, msg in findings:
        lines.append(f"- {icon[lv]} **[{code}]** {msg}")
    lines.append("")
    lines.append("> 脚本只做结构与逻辑检查，不判定健康状况、不替代检查机构与诊断机构结论。")
    return "\n".join(lines)


SAMPLE = {
    "workers": [
        {
            "name": "张三", "hazards": ["噪声"], "hire_date": "2025-03-01",
            "pre_exam_date": "2025-02-20",
            "periodic": [{"date": "2026-03-05", "result": "正常",
                          "agency": "市职防院", "physician": "李某"}],
            "left_date": None, "abnormal_followup": None,
            "archive": {k: True for k in ARCHIVE_KEYS},
        },
        {
            "name": "李四", "hazards": ["矽尘"], "hire_date": "2026-06-01",
            "pre_exam_date": None,
            "periodic": [{"date": "2025-01-10", "result": "复查",
                          "agency": "", "physician": ""}],
            "left_date": "2026-09-30", "abnormal_followup": None,
            "archive": {"职业史": True, "接触史": True, "既往史": False,
                        "家族史": True, "个人生活史": False,
                        "检查结果及处理": True, "职业病诊疗": True},
        },
    ],
}


def selftest():
    data = json.loads(json.dumps(SAMPLE))
    findings, summary = check(data, date(2026, 10, 13))
    print(render_md(findings, summary, len(data["workers"])))
    codes = [(lv, c) for lv, c, _ in findings]
    assert ("FAIL", "Q2") in codes, "应检出李四无岗前体检"
    assert ("FAIL", "Q3") in codes, "应检出矽尘体检超期"
    assert ("FAIL", "Q4") in codes, "应检出离岗无体检"
    assert ("FAIL", "Q5") in codes, "应检出异常无随访"
    assert ("WARN", "Q1") in codes, "应检出档案缺项"
    assert ("WARN", "Q6") in codes, "应检出缺签章"
    # 全合规场景
    good = json.loads(json.dumps(SAMPLE))
    w2 = good["workers"][1]
    w2["pre_exam_date"] = "2026-05-20"
    w2["periodic"] = [{"date": "2026-06-20", "result": "复查",
                       "agency": "市职防院", "physician": "李某"}]
    w2["abnormal_followup"] = "2026-07-15 复查正常"
    w2["left_date"] = None
    w2["archive"] = {k: True for k in ARCHIVE_KEYS}
    f2, s2 = check(good, date(2026, 10, 13))
    assert s2["fail"] == 0, f"全合规样本不应 FAIL，实际: {s2}"
    # 离岗检查合规场景（离岗前90天在岗检查视同）
    ok_exit = json.loads(json.dumps(good))
    ok_exit["workers"][0]["left_date"] = "2026-09-20"  # 3-05 距 9-20 超 90 天 → FAIL
    f3, s3 = check(ok_exit, date(2026, 10, 13))
    assert ("FAIL", "Q4") in [(lv, c) for lv, c, _ in f3], "离岗前无90天内检查应 FAIL"
    ok_exit2 = json.loads(json.dumps(good))
    ok_exit2["workers"][0]["left_date"] = "2026-05-20"  # 3-05 距 5-20 = 76 天 → 视同
    f4, s4 = check(ok_exit2, date(2026, 10, 13))
    assert ("FAIL", "Q4") not in [(lv, c) for lv, c, _ in f4], "90天内检查应视同离岗检查"
    print("\n自检断言全部通过 ✅")
    return 0


def main():
    ap = argparse.ArgumentParser(description="职业健康监护档案与体检合规体检")
    ap.add_argument("--file", help="监护档案 JSON 文件")
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
        print(render_md(findings, summary, len(data.get("workers") or [])))
    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
