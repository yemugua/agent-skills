#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
score_calc.py — 招聘简历筛选评分卡计算器
用法:
    python score_calc.py --file 评分明细.csv [--weights default|tech|mgmt|startup] [--min-grade B]
                          [--out out.md] [--format md|json] [--selftest]

输入 CSV 需含表头，兼容 UTF-8 / GBK。建议列（dim1..dim7 为 0-5 分，缺项按 0 记并标注）:
    name      候选人
    redline   是否触发红线 (是/否)
    dim1..dim7 七维度原始分 (0-5)
    note      备注（亮点/疑点）

七维度: 1 硬性资质 / 2 专业经验 / 3 能力证据 / 4 稳定性 / 5 动机匹配 / 6 沟通协作 / 7 成长潜力
分档: S>=90 A>=80 B>=70 C>=60 D<60
红线一票否决。
"""
import argparse
import csv
import io
import json
import sys
from pathlib import Path

WEIGHT_SETS = {
    "default": [15, 25, 20, 10, 10, 10, 10],
    "tech":    [10, 25, 30, 10, 5, 10, 10],
    "mgmt":    [10, 25, 15, 15, 15, 10, 10],
    "startup": [10, 20, 20, 10, 15, 5, 20],
}
DIM_NAMES = ["硬性资质", "专业经验", "能力证据", "稳定性", "动机匹配", "沟通协作", "成长潜力"]
GRADE_BANDS = [("S", 90), ("A", 80), ("B", 70), ("C", 60), ("D", 0)]


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


def truthy(v):
    return norm(v) in ("是", "y", "yes", "Y", "true", "1", "√", "红线")


def to_score(v):
    v = norm(v)
    if not v:
        return None
    try:
        f = float(v)
    except ValueError:
        return None
    if f < 0 or f > 5:
        return None
    return f


def grade_of(total):
    for g, lo in GRADE_BANDS:
        if total >= lo:
            return g
    return "D"


def evaluate(rows, weights):
    results = []
    for idx, r in enumerate(rows, start=2):
        name = norm(r.get("name", "")) or f"第{idx}行(无名)"
        if truthy(r.get("redline", "")):
            results.append({"name": name, "total": 0.0, "grade": "红线",
                            "dims": [], "note": norm(r.get("note", "")),
                            "flag": "触发一票否决红线"})
            continue
        dims, total, missing = [], 0.0, []
        for i, w in enumerate(weights, 1):
            s = to_score(r.get(f"dim{i}", ""))
            if s is None:
                missing.append(DIM_NAMES[i - 1])
                s = 0.0
            got = s / 5 * 100 * w / 100
            total += got
            dims.append({"dim": DIM_NAMES[i - 1], "raw": s, "weight": w, "got": round(got, 2)})
        results.append({"name": name, "total": round(total, 2), "grade": grade_of(total),
                        "dims": dims, "note": norm(r.get("note", "")),
                        "flag": ("缺评分维度: " + ", ".join(missing)) if missing else ""})
    results.sort(key=lambda x: (x["grade"] == "红线", -x["total"]))
    return results


def render_md(results, weights_name):
    w = WEIGHT_SETS[weights_name]
    lines = ["# 候选人评分排序表", "",
             f"- 权重方案：**{weights_name}**（{'/'.join(f'{x}%' for x in w)}）",
             f"- 候选人：{len(results)} 人", "",
             "| 排名 | 候选人 | 总分 | 分档 | 最低维度 | 亮点/疑点 | 标记 |",
             "|---|---|---|---|---|---|---|"]
    for i, x in enumerate(results, 1):
        if x["grade"] == "红线":
            lines.append(f"| {i} | {x['name']} | — | 红线 | — | {x['note']} | {x['flag']} |")
            continue
        dims = x["dims"]
        low = min(dims, key=lambda d: d["raw"]) if dims else None
        low_txt = f"{low['dim']}({low['raw']}/5)" if low else "—"
        lines.append(f"| {i} | {x['name']} | {x['total']} | {x['grade']} | {low_txt} | {x['note']} | {x['flag']} |")
    lines += ["",
              "> ⚠️ 评分仅基于简历材料；红线候选人按一票否决处理；最终用人决策需结合面试与合规核验。", ""]
    return "\n".join(lines)


def selftest():
    sample = [
        {"name": "张三", "dim1": "4", "dim2": "4", "dim3": "3", "dim4": "4", "dim5": "3", "dim6": "4", "dim7": "3",
         "note": "持证齐全，项目经历对口"},
        {"name": "李四", "dim1": "5", "dim2": "5", "dim3": "4", "dim4": "5", "dim5": "4", "dim6": "4", "dim7": "4",
         "note": "资深，薪酬预期高"},
        {"name": "王五", "dim1": "3", "dim2": "2", "dim3": "2", "dim4": "3", "dim5": "3", "dim6": "3", "dim7": "2",
         "note": "经验偏浅"},
        {"name": "赵六", "redline": "是", "dim1": "5", "dim2": "5", "dim3": "5", "dim4": "5", "dim5": "5", "dim6": "5", "dim7": "5",
         "note": "无上岗证"},
        {"name": "孙七", "dim1": "4", "dim2": "3", "dim4": "4", "note": "能力证据待补"},
    ]
    results = evaluate(sample, WEIGHT_SETS["default"])
    grades = [r["grade"] for r in results]
    ok = ("红线" in grades and grades[0] != "红线"
          and any("缺评分维度" in r["flag"] for r in results))
    print(render_md(results, "default"))
    print("SELFTEST:", "PASS" if ok else f"FAIL ({grades})")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="招聘评分卡计算器")
    ap.add_argument("--file", help="评分明细 CSV")
    ap.add_argument("--weights", default="default", choices=list(WEIGHT_SETS))
    ap.add_argument("--min-grade", default="B", choices=["S", "A", "B", "C", "D"])
    ap.add_argument("--out", default=None)
    ap.add_argument("--format", default="md", choices=["md", "json"])
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.file:
        ap.error("--file 必填（或使用 --selftest）")

    rows = read_rows(Path(args.file))
    if not rows:
        print("未读到数据行，请检查 CSV 表头与编码（UTF-8/GBK）")
        return 2
    results = evaluate(rows, WEIGHT_SETS[args.weights])

    order = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4, "红线": 5}
    threshold = order[args.min_grade]
    shown = [r for r in results if order[r["grade"]] <= threshold]

    if args.format == "json":
        out = json.dumps({"weights": args.weights, "min_grade": args.min_grade,
                          "shown": shown, "hidden": len(results) - len(shown)},
                         ensure_ascii=False, indent=2)
    else:
        out = render_md(shown, args.weights)
        if len(results) != len(shown):
            out += f"\n（已按 --min-grade {args.min_grade} 过滤，隐藏 {len(results) - len(shown)} 人）\n"

    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
        print(f"已写入 {args.out}")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
