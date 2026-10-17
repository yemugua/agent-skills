#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fire_duty_check.py — 消防控制室值班/火警记录体检脚本
用法:
    python fire_duty_check.py --file 记录.csv [--as-of 2026-10-13] [--out out.md] [--format md|json] [--selftest]

输入 CSV 需含表头，兼容 UTF-8 / GBK。建议列（缺列自动跳过对应检查）:
    date        值班日期        (YYYY-MM-DD)
    shift       班次            (早班/中班/晚班)
    on_duty     值班人
    off_duty    接班人
    start       接班时间        (HH:MM)
    end         交班时间        (HH:MM)
    handover_signed 是否双方签字  (是/否)
    alarm_type  报警类型        (火警/误报/故障)
    alarm_time  报警时间        (HH:MM)
    confirm_time 确认时间       (HH:MM)
    call119     是否拨打119     (是/否)
    fault_status 故障处理状态    (未处理/处理中/已闭环)
    note        备注

检查项:
    D1 断档     日期序列中的值守空白
    D2 签名缺失 交接无双方签字
    D3 时长异常 单班值守超过 max_shift_hours (默认12)
    D4 火警未闭环 火警缺确认时间或缺119记录
    D5 时间倒挂 处置时间早于报警时间
    D6 故障超期 故障记录超过 fault_overdue_days (默认7) 未闭环

仅做结构与逻辑检查, 不判定内容真伪。
"""
import argparse
import csv
import datetime as dt
import io
import json
import sys
from pathlib import Path

DEFAULT_MAX_SHIFT_HOURS = 12
DEFAULT_FAULT_OVERDUE_DAYS = 7


def read_rows(path: Path):
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "gbk"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return [dict(r) for r in reader]


def norm(v):
    return (v or "").strip()


def truthy(v):
    return norm(v) in ("是", "y", "yes", "Y", "true", "1", "√")


def parse_date(v):
    v = norm(v)
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return dt.datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    return None


def parse_time(v):
    v = norm(v)
    if not v:
        return None
    for fmt in ("%H:%M", "%H:%M:%S", "%H点%M分", "%H时%M分"):
        try:
            return dt.datetime.strptime(v, fmt).time()
        except ValueError:
            continue
    return None


def check(rows, as_of: dt.date, max_shift_hours=DEFAULT_MAX_SHIFT_HOURS,
          fault_overdue_days=DEFAULT_FAULT_OVERDUE_DAYS):
    issues = []
    stats = {"rows": len(rows), "days": set(), "alarms": 0, "faults": 0}

    # ---- D1 断档 ----
    dates = set()
    for r in rows:
        d = parse_date(r.get("date", ""))
        if d:
            dates.add(d)
    stats["days"] = len(dates)
    if dates:
        cur = min(dates)
        gaps = []
        while cur <= max(dates):
            if cur not in dates:
                gaps.append(cur.isoformat())
            cur += dt.timedelta(days=1)
        for g in gaps:
            issues.append({"code": "D1", "level": "高", "date": g,
                           "msg": f"{g} 无值守记录（断档）", "fix": "补齐该日值班记录或说明停用报备"})

    for idx, r in enumerate(rows, start=2):
        d = parse_date(r.get("date", ""))
        ds = d.isoformat() if d else norm(r.get("date", ""))
        who = norm(r.get("on_duty", "")) or norm(r.get("off_duty", "")) or "?"

        # ---- D2 签名缺失 ----
        if "handover_signed" in r and r.get("handover_signed") is not None:
            if not truthy(r.get("handover_signed")):
                issues.append({"code": "D2", "level": "高", "date": ds,
                               "msg": f"第{idx}行 交接无双方签字（值班人:{who}）",
                               "fix": "补双签；严禁代签，确需更正要划改签名"})

        # ---- D3 时长异常 ----
        st, en = parse_time(r.get("start", "")), parse_time(r.get("end", ""))
        if st and en:
            span = (dt.datetime.combine(d or as_of, en) - dt.datetime.combine(d or as_of, st)).total_seconds() / 3600
            if span < 0:
                span += 24  # 跨零点班
            if span > max_shift_hours:
                issues.append({"code": "D3", "level": "中", "date": ds,
                               "msg": f"第{idx}行 单班时长 {span:.1f}h 超过 {max_shift_hours}h（{st.strftime('%H:%M')}→{en.strftime('%H:%M')}）",
                               "fix": "核对是否跨班登记错误；超长班次应有轮换安排"})

        # ---- D4 火警未闭环 ----
        at = norm(r.get("alarm_type", ""))
        if "火警" in at or truthy(r.get("call119")) or truthy(r.get("is_real_alarm")):
            stats["alarms"] += 1
            ct = parse_time(r.get("confirm_time", ""))
            at_t = parse_time(r.get("alarm_time", ""))
            if at_t and not ct:
                issues.append({"code": "D4", "level": "高", "date": ds,
                               "msg": f"第{idx}行 火警记录缺确认时间（部位:{norm(r.get('location', '')) or '?'}）",
                               "fix": "补齐确认时间与确认方式；真火警必须有119拨打记录"})
            if at_t and ct and not truthy(r.get("call119")) and truthy(r.get("is_real_alarm")):
                issues.append({"code": "D4", "level": "高", "date": ds,
                               "msg": f"第{idx}行 判定真火警但无 119 拨打记录",
                               "fix": "核实是否拨打；未拨打属重大流程缺失"})

        # ---- D5 时间倒挂 ----
        at_t = parse_time(r.get("alarm_time", ""))
        ct = parse_time(r.get("confirm_time", ""))
        rt = parse_time(r.get("reset_time", ""))
        if at_t and ct and ct < at_t:
            issues.append({"code": "D5", "level": "高", "date": ds,
                           "msg": f"第{idx}行 确认时间({ct.strftime('%H:%M')})早于报警时间({at_t.strftime('%H:%M')})",
                           "fix": "核对控制器存储记录，更正须划改签名"})
        if at_t and rt and rt < at_t:
            issues.append({"code": "D5", "level": "高", "date": ds,
                           "msg": f"第{idx}行 复位时间早于报警时间",
                           "fix": "核对控制器存储记录"})

        # ---- D6 故障超期 ----
        fs = norm(r.get("fault_status", ""))
        if fs and fs not in ("已闭环", "已处理", "已修复"):
            stats["faults"] += 1
            fd = d
            if fd and (as_of - fd).days > fault_overdue_days:
                issues.append({"code": "D6", "level": "中", "date": ds,
                               "msg": f"第{idx}行 故障记录 {fd.isoformat()} 至今 {(as_of - fd).days} 天未闭环（状态:{fs}）",
                               "fix": "联系维保单位限期处理，留存工单与复检记录"})

    return issues, stats


def render_md(issues, stats, as_of):
    lines = ["# 控制室值班记录体检报告", "",
             f"- 核查基准日：{as_of.isoformat()}",
             f"- 记录行数：{stats['rows']}，覆盖天数：{stats['days']}，火警记录：{stats['alarms']}，未闭环故障：{stats['faults']}",
             f"- 发现问题：**{len(issues)}** 项", ""]
    if not issues:
        lines += ["✅ 未发现结构性与逻辑性问题（不代表内容真实合规）。", ""]
        return "\n".join(lines)
    lines += ["| # | 代码 | 等级 | 日期 | 问题 | 整改建议 |", "|---|---|---|---|---|---|"]
    for i, x in enumerate(issues, 1):
        lines.append(f"| {i} | {x['code']} | {x['level']} | {x['date']} | {x['msg']} | {x['fix']} |")
    lines += ["", "> ⚠️ 本报告仅基于记录的结构与逻辑检查，不判定内容真伪；执法口径以消防救援机构为准。", ""]
    return "\n".join(lines)


def selftest():
    sample = [
        {"date": "2026-10-01", "shift": "早班", "on_duty": "张三", "off_duty": "李四",
         "start": "08:00", "end": "18:00", "handover_signed": "是", "alarm_type": "误报"},
        {"date": "2026-10-03", "shift": "早班", "on_duty": "张三", "off_duty": "李四",
         "start": "08:00", "end": "20:30", "handover_signed": "否",
         "alarm_type": "火警", "alarm_time": "14:00", "confirm_time": "13:50", "call119": "是"},
        {"date": "2026-10-04", "shift": "晚班", "on_duty": "王五", "off_duty": "赵六",
         "start": "18:00", "end": "06:00", "handover_signed": "是",
         "alarm_type": "火警", "alarm_time": "20:15", "call119": "是", "is_real_alarm": "是"},
        {"date": "2026-10-05", "shift": "早班", "on_duty": "李四", "off_duty": "张三",
         "start": "08:00", "end": "16:00", "handover_signed": "是", "fault_status": "未处理"},
    ]
    issues, stats = check(sample, as_of=dt.date(2026, 10, 13))
    codes = sorted({x["code"] for x in issues})
    ok = set(codes) >= {"D1", "D2", "D3", "D4", "D5", "D6"}
    print(render_md(issues, stats, dt.date(2026, 10, 13)))
    print("SELFTEST:", "PASS" if ok else f"FAIL (got {codes})")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="消防控制室值班记录体检")
    ap.add_argument("--file", help="值班/火警记录 CSV")
    ap.add_argument("--as-of", default=None, help="核查基准日 YYYY-MM-DD，默认今天")
    ap.add_argument("--out", default=None, help="输出文件路径")
    ap.add_argument("--format", default="md", choices=["md", "json"])
    ap.add_argument("--max-shift-hours", type=float, default=DEFAULT_MAX_SHIFT_HOURS)
    ap.add_argument("--fault-overdue-days", type=int, default=DEFAULT_FAULT_OVERDUE_DAYS)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if not args.file:
        ap.error("--file 必填（或使用 --selftest）")

    as_of = parse_date(args.as_of) or dt.date.today()
    rows = read_rows(Path(args.file))
    if not rows:
        print("未读到数据行，请检查 CSV 表头与编码（UTF-8/GBK）")
        return 2
    issues, stats = check(rows, as_of, args.max_shift_hours, args.fault_overdue_days)

    if args.format == "json":
        out = json.dumps({"as_of": as_of.isoformat(), "stats": stats, "issues": issues},
                         ensure_ascii=False, indent=2)
    else:
        out = render_md(issues, stats, as_of)

    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
        print(f"已写入 {args.out}")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
