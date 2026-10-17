#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doc_number_check.py — 质量管理体系受控文件台账体检脚本
用法:
    python doc_number_check.py --file 受控台账.csv [--as-of 2026-10-13] [--out out.md] [--format md|json] [--selftest]

输入 CSV 需含表头，兼容 UTF-8 / GBK。建议列（缺列自动跳过对应检查）:
    doc_no      文件编号        (如 QP-08-02)
    title       文件名称
    layer       文件层          (QM/QP/WI/QR)
    version     版本号          (如 A / 1.0 / 2026)
    status      状态            (有效/作废/换版中)
    owner       归口部门
    issue_date  发布日期        (YYYY-MM-DD)
    next_review 下次评审日期    (YYYY-MM-DD)
    approver    批准人

检查项:
    Q1 编号格式违规   不符合 类型码-过程码-序号 规则
    Q2 编号重复       同一编号多行
    Q3 版本断档       同编号版本序列跳号（如 A→C）
    Q4 审批人缺失     有效文件无批准人
    Q5 超期未评审     超过 next_review 未更新
    Q6 作废仍有效     状态为作废但无回收记录字段为空
    Q7 记录无对应程序 QR 编号在台账中无对应 QP 过程码

仅做结构与逻辑检查, 不判定内容真伪。
"""
import argparse
import csv
import datetime as dt
import io
import json
import re
import sys
from pathlib import Path

DOC_RE = re.compile(r"^(QM|QP|WI|QR)(?:-(\d{1,4}))?(?:-(\d{1,4}))?(?:-(\d{1,4}))?$", re.IGNORECASE)


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
    return [dict(r) for r in csv.DictReader(io.StringIO(text))]


def norm(v):
    return (v or "").strip()


def parse_date(v):
    v = norm(v)
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
        try:
            return dt.datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    return None


def version_rank(v):
    """粗粒度版本序号: 1.0->10, A->1, B->2 ... 用于断档检测"""
    v = norm(v).upper()
    if not v:
        return None
    m = re.match(r"^V?(\d+)(?:\.(\d+))?$", v)
    if m:
        major = int(m.group(1))
        minor = int(m.group(2) or 0)
        return major * 100 + minor
    if len(v) == 1 and "A" <= v <= "Z":
        return ord(v) - ord("A") + 1
    return None


def check(rows, as_of: dt.date):
    issues = []
    stats = {"rows": len(rows), "docs": 0, "forms": 0}

    by_no = {}
    versions = {}
    qp_codes = set()
    qr_codes = set()

    for idx, r in enumerate(rows, start=2):
        no = norm(r.get("doc_no", ""))
        if not no:
            continue
        stats["docs"] += 1
        layer = norm(r.get("layer", "")).upper()
        up = no.upper()

        # 收集 QP/QR 过程码
        m = DOC_RE.match(up)
        if m:
            typ, p1, p2 = m.group(1), m.group(2), m.group(3)
            if typ == "QP" and p1:
                qp_codes.add(p1)
            if typ == "QR" and p1:
                qr_codes.add(p1)

        # Q1 编号格式
        if not m:
            issues.append({"code": "Q1", "level": "中", "doc": no,
                           "msg": f"第{idx}行 编号「{no}」不符合 类型码[-过程码[-序号]] 规则",
                           "fix": "按编号规则重新赋号，历史编号备注对应关系"})

        # Q2 编号重复
        by_no.setdefault(up, []).append(idx)

        # 版本收集
        vr = version_rank(r.get("version", ""))
        if vr is not None:
            versions.setdefault(up, []).append((vr, norm(r.get("version"))))

        # Q4 审批人缺失
        status = norm(r.get("status", ""))
        if status in ("有效", "") and not norm(r.get("approver", "")):
            issues.append({"code": "Q4", "level": "高", "doc": no,
                           "msg": f"第{idx}行 文件「{no}」无批准人",
                           "fix": "补齐三级审批签字并在台账登记"})

        # Q5 超期未评审
        nr = parse_date(r.get("next_review", ""))
        if nr and nr < as_of and status not in ("作废",):
            issues.append({"code": "Q5", "level": "中", "doc": no,
                           "msg": f"第{idx}行 文件「{no}」评审到期 {nr.isoformat()} 已逾期 {(as_of - nr).days} 天",
                           "fix": "组织文件适用性评审并更新 next_review"})

        # Q6 作废仍有效
        if status == "作废" and norm(r.get("owner", "")) == "" and not norm(r.get("note", "")):
            issues.append({"code": "Q6", "level": "中", "doc": no,
                           "msg": f"第{idx}行 文件「{no}」已作废但无回收/留存记录",
                           "fix": "登记回收份数与留存样本标识，留存样本加盖'作废留存'"})

    # Q2 输出
    for up, idxs in by_no.items():
        if len(idxs) > 1:
            issues.append({"code": "Q2", "level": "高", "doc": up,
                           "msg": f"编号「{up}」重复出现在第 {idxs} 行",
                           "fix": "一编号一文件；确为多版本应只保留有效版在台账"})

    # Q3 版本断档
    for up, vs in versions.items():
        vs_sorted = sorted(set(vs))
        if len(vs_sorted) >= 2:
            ranks = [v for v, _ in vs_sorted]
            gaps = [vs_sorted[i + 1][1] for i in range(len(ranks) - 1)
                    if ranks[i + 1] - ranks[i] > 1]
            if gaps:
                issues.append({"code": "Q3", "level": "中", "doc": up,
                               "msg": f"编号「{up}」版本序列疑似跳号（缺失段落: {', '.join(gaps)}）",
                               "fix": "核对换版履历，补登中间版本或说明跳版原因"})

    # Q7 记录表单无对应程序
    for code in sorted(qr_codes):
        if code not in qp_codes:
            issues.append({"code": "Q7", "level": "中", "doc": f"QR-{code}-*",
                           "msg": f"过程码 {code} 有记录表单但无对应程序文件",
                           "fix": "补齐该过程的程序文件，或说明记录依据（法规/客户要求）"})

    stats["forms"] = len(qr_codes)
    return issues, stats


def render_md(issues, stats, as_of):
    lines = ["# 受控文件台账体检报告", "",
             f"- 核查基准日：{as_of.isoformat()}",
             f"- 台账行数：{stats['rows']}，文件数：{stats['docs']}，记录表单过程码：{stats['forms']}",
             f"- 发现问题：**{len(issues)}** 项", ""]
    if not issues:
        lines += ["✅ 未发现结构性与逻辑性问题（不代表内容真实合规）。", ""]
        return "\n".join(lines)
    lines += ["| # | 代码 | 等级 | 文件 | 问题 | 整改建议 |", "|---|---|---|---|---|---|"]
    for i, x in enumerate(issues, 1):
        lines.append(f"| {i} | {x['code']} | {x['level']} | {x['doc']} | {x['msg']} | {x['fix']} |")
    lines += ["", "> ⚠️ 本报告仅基于台账的结构与逻辑检查，不判定内容真伪；认证口径以认证机构为准。", ""]
    return "\n".join(lines)


def selftest():
    sample = [
        {"doc_no": "QM-2026", "title": "质量手册", "layer": "QM", "version": "2026",
         "status": "有效", "owner": "管代", "approver": "总经理"},
        {"doc_no": "QP-08-02", "title": "采购控制程序", "layer": "QP", "version": "A",
         "status": "有效", "owner": "采购部", "approver": "管代",
         "issue_date": "2024-01-10", "next_review": "2026-10-01"},
        {"doc_no": "QP-08-02", "title": "采购控制程序", "layer": "QP", "version": "C",
         "status": "有效", "owner": "采购部", "approver": ""},
        {"doc_no": "QP-12", "title": "来料检验程序", "layer": "QP", "version": "1.0",
         "status": "有效", "owner": "质量部", "approver": "管代"},
        {"doc_no": "QR-08-02-01", "title": "供方调查表", "layer": "QR", "version": "A",
         "status": "有效", "owner": "采购部", "approver": "管代"},
        {"doc_no": "QR-15-01-01", "title": "培训记录表", "layer": "QR", "version": "A",
         "status": "有效", "owner": "人事", "approver": "管代"},
        {"doc_no": "WI-6-3", "title": "装配作业指导书", "layer": "WI", "version": "A",
         "status": "作废", "owner": "", "approver": "管代"},
        {"doc_no": "程序文件-01", "title": "格式错误样例", "layer": "QP", "version": "A",
         "status": "有效", "owner": "质量部", "approver": "管代"},
    ]
    issues, stats = check(sample, as_of=dt.date(2026, 10, 13))
    codes = sorted({x["code"] for x in issues})
    ok = set(codes) >= {"Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7"}
    print(render_md(issues, stats, dt.date(2026, 10, 13)))
    print("SELFTEST:", "PASS" if ok else f"FAIL (got {codes})")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="受控文件台账体检")
    ap.add_argument("--file", help="受控台账 CSV")
    ap.add_argument("--as-of", default=None, help="核查基准日 YYYY-MM-DD，默认今天")
    ap.add_argument("--out", default=None, help="输出文件路径")
    ap.add_argument("--format", default="md", choices=["md", "json"])
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
    issues, stats = check(rows, as_of)

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
