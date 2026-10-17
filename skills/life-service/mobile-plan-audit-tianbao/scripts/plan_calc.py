#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mobile plan cost audit helper.

Reads a JSON case file, computes average monthly / annual spend, unit cost per GB,
utilisation of the plan allowance, and lists downgrade or number portability
obstacles. Writes a markdown report. Use --selftest to run built-in assertions.
"""

import argparse
import json
import os
import sys

# 套餐月费 / 超额 / 增值业务 / 一次性费用
KEY_BASE = "\u5957\u9910\u6708\u8d39"
KEY_VOICE = "\u8bed\u97f3\u8d85\u989d"
KEY_DATA = "\u6d41\u91cf\u8d85\u989d"
KEY_VAS = "\u589e\u503c\u4e1a\u52a1"
KEY_OTHER = "\u5176\u4ed6"

# 合约 / 宽带 / 副卡 / 亲情网 / 集团 / 增值业务 / 欠费 / 实名
OBSTACLES = (
    ("\u5408\u7ea6", "\u5408\u7ea6\u672a\u5230\u671f", "\u6838\u7b97\u8fdd\u7ea6\u91d1\u4e0e\u5df2\u4eab\u4f18\u60e0\u540e\u9009\u62e9\u7b49\u5f85\u6216\u89e3\u7ea6"),
    ("\u5bbd\u5e26", "\u878d\u5408\u5957\u9910\u7ed1\u5b9a", "\u5148\u786e\u8ba4\u80fd\u5426\u89e3\u7ed1\u3001\u79fb\u673a\u6216\u8bbe\u5907\u8fd4\u8fd8"),
    ("\u526f\u5361", "\u526f\u5361\u6216\u4eb2\u60c5\u7f51", "\u5148\u8fc1\u79fb\u6216\u6ce8\u9500\u5173\u8054\u53f7\u7801"),
    ("\u96c6\u56e2", "\u96c6\u56e2\u6216\u6821\u56ed\u5957\u9910", "\u5411\u96c6\u56e2\u7ecf\u529e\u4eba\u6216\u8425\u4e1a\u5385\u786e\u8ba4\u9000\u51fa\u89c4\u5219"),
    ("\u589e\u503c\u4e1a\u52a1", "\u672a\u786e\u8ba4\u5f00\u901a\u4e1a\u52a1", "\u8981\u6c42\u63d0\u4f9b\u5f00\u901a\u51ed\u8bc1\u5e76\u4e3b\u5f20\u9000\u8ba2\u4e0e\u9000\u8d39"),
    ("\u6b20\u8d39", "\u6b20\u8d39\u6216\u505c\u673a", "\u5148\u7ed3\u6e05\u6b20\u8d39\u6062\u590d\u6b63\u5e38\u72b6\u6001"),
    ("\u5b9e\u540d", "\u5b9e\u540d\u4fe1\u606f\u5f02\u5e38", "\u5148\u5b8c\u6210\u5b9e\u540d\u6838\u9a8c"),
)

DEFAULT_CASE = {
    "\u53f7\u7801": "138****0000",
    "\u8fd0\u8425\u5546": "\u672a\u586b\u5199",
    "\u5957\u9910\u540d\u79f0": "\u672a\u586b\u5199",
    "\u5957\u9910\u6708\u8d39": 99.0,
    "\u5957\u9910\u5185\u6d41\u91cfGB": 40.0,
    "\u5957\u9910\u5185\u8bed\u97f3\u5206\u949f": 500.0,
    "\u5408\u7ea6": "\u5408\u7ea6\u672a\u5230\u671f",
    "\u5bbd\u5e26\u7ed1\u5b9a": "\u5df2\u7ed1\u5b9a",
    "\u526f\u5361\u6570\u91cf": 1,
    "\u6708\u4efd\u8d26\u5355": [],
}

MONTH_KEYS = (
    ("month", "\u6708\u4efd"),
    (KEY_BASE, KEY_BASE),
    (KEY_VOICE, KEY_VOICE),
    (KEY_DATA, KEY_DATA),
    (KEY_VAS, KEY_VAS),
    (KEY_OTHER, KEY_OTHER),
    ("data_gb", "\u5b9e\u7528\u6d41\u91cfGB"),
    ("voice_minutes", "\u5b9e\u7528\u8bed\u97f3\u5206\u949f"),
)


def _num(value):
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _get(item, keys, default=0.0):
    for key in keys:
        if key in item:
            return _num(item[key])
    return default


def _text(item, keys, default=""):
    for key in keys:
        if key in item and item[key] not in (None, ""):
            return str(item[key])
    return default


def load_case(path):
    if not path:
        return dict(DEFAULT_CASE)
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    case = dict(DEFAULT_CASE)
    case.update(data)
    return case


def normalise_months(case):
    raw = case.get("\u6708\u4efd\u8d26\u5355") or []
    rows = []
    base_fee = _num(case.get(KEY_BASE))
    for index, item in enumerate(raw, start=1):
        row = {
            "month": _text(item, ("month", "\u6708\u4efd"), "M%d" % index),
            KEY_BASE: _get(item, (KEY_BASE, "base")),
            KEY_VOICE: _get(item, (KEY_VOICE, "voice_over")),
            KEY_DATA: _get(item, (KEY_DATA, "data_over")),
            KEY_VAS: _get(item, (KEY_VAS, "vas")),
            KEY_OTHER: _get(item, (KEY_OTHER, "other")),
            "data_gb": _get(item, ("data_gb", "\u5b9e\u7528\u6d41\u91cfGB")),
            "voice_minutes": _get(item, ("voice_minutes", "\u5b9e\u7528\u8bed\u97f3\u5206\u949f")),
        }
        if row[KEY_BASE] == 0.0:
            row[KEY_BASE] = base_fee
        row["total"] = row[KEY_BASE] + row[KEY_VOICE] + row[KEY_DATA] + row[KEY_VAS] + row[KEY_OTHER]
        rows.append(row)
    return rows


def summarise(case, rows):
    months = len(rows)
    total = sum(row["total"] for row in rows)
    avg = total / months if months else 0.0
    data_gb = sum(row["data_gb"] for row in rows)
    voice = sum(row["voice_minutes"] for row in rows)
    vas = sum(row[KEY_VAS] for row in rows)
    over = sum(row[KEY_VOICE] + row[KEY_DATA] for row in rows)
    one_off = _num(case.get("\u4e00\u6b21\u6027\u8d39\u7528"))
    annual = avg * 12 + one_off
    unit = avg / data_gb if data_gb > 0 else 0.0
    allowance = _num(case.get("\u5957\u9910\u5185\u6d41\u91cfGB"))
    voice_allowance = _num(case.get("\u5957\u9910\u5185\u8bed\u97f3\u5206\u949f"))
    data_rate = (data_gb / months) / allowance if months and allowance > 0 else 0.0
    voice_rate = (voice / months) / voice_allowance if months and voice_allowance > 0 else 0.0
    return {
        "months": months,
        "total": total,
        "avg": avg,
        "annual": annual,
        "data_gb": data_gb,
        "voice": voice,
        "vas": vas,
        "over": over,
        "one_off": one_off,
        "unit_cost": unit,
        "data_rate": data_rate,
        "voice_rate": voice_rate,
    }


def build_obstacles(case):
    blob = json.dumps(case, ensure_ascii=False)
    found = []
    for token, name, action in OBSTACLES:
        if token in blob:
            found.append((name, action))
    if not found:
        found.append(("\u672a\u53d1\u73b0\u660e\u786e\u969c\u788d", "\u4ecd\u9700\u5728\u8425\u4e1a\u5385\u6216\u5b98\u65b9\u67e5\u8be2\u643a\u8f6c\u8d44\u683c"))
    return found


def suggestions(summary, obstacle_count):
    tips = []
    if summary["data_rate"] and summary["data_rate"] < 0.5:
        tips.append("\u5957\u9910\u5185\u6d41\u91cf\u5229\u7528\u7387\u4f4e\uff0c\u4f18\u5148\u8003\u8651\u964d\u5957\u6216\u4fdd\u53f7\u4f4e\u6708\u79df")
    else:
        tips.append("\u5957\u9910\u5185\u6d41\u91cf\u5229\u7528\u7387\u8f83\u9ad8\uff0c\u964d\u5957\u524d\u5148\u6838\u7b97\u8d85\u989d\u6210\u672c")
    if summary["vas"] > 0:
        tips.append("\u589e\u503c\u4e1a\u52a1\u6709\u6301\u7eed\u6263\u8d39\uff0c\u5148\u8981\u6c42\u9000\u8ba2\u5e76\u4e3b\u5f20\u672a\u786e\u8ba4\u5f00\u901a\u90e8\u5206\u7684\u9000\u8d39")
    if summary["over"] > 0:
        tips.append("\u5b58\u5728\u8d85\u989d\u8d39\uff0c\u5148\u786e\u8ba4\u662f\u8d85\u989d\u8d44\u8d39\u8fd8\u662f\u5957\u9910\u4e0d\u5339\u914d")
    if obstacle_count >= 3:
        tips.append("\u969c\u788d\u8f83\u591a\uff0c\u5efa\u8bae\u6309\u5148\u89e3\u7ed1\u3001\u518d\u5904\u7406\u5408\u7ea6\u3001\u6700\u540e\u529e\u7406\u964d\u5957\u6216\u643a\u8f6c\u7684\u987a\u5e8f")
    return tips


def render_report(case, rows, summary, obstacles, tips):
    lines = []
    lines.append("# \u624b\u673a\u5957\u9910\u8d44\u8d39\u6838\u67e5\u62a5\u544a")
    lines.append("")
    lines.append("## \u4e00\u3001\u53f7\u7801\u6863\u6848")
    lines.append("")
    lines.append("| \u9879\u76ee | \u5185\u5bb9 |")
    lines.append("|---|---|")
    for label in ("\u53f7\u7801", "\u8fd0\u8425\u5546", "\u5957\u9910\u540d\u79f0", "\u5957\u9910\u6708\u8d39", "\u5957\u9910\u5185\u6d41\u91cfGB", "\u5957\u9910\u5185\u8bed\u97f3\u5206\u949f"):
        lines.append("| %s | %s |" % (label, case.get(label, "")))
    lines.append("")
    lines.append("## \u4e8c\u3001\u652f\u51fa\u6838\u7b97")
    lines.append("")
    lines.append("| \u6708\u4efd | \u5957\u9910\u6708\u8d39 | \u8bed\u97f3\u8d85\u989d | \u6d41\u91cf\u8d85\u989d | \u589e\u503c\u4e1a\u52a1 | \u5176\u4ed6 | \u5408\u8ba1 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        lines.append("| %s | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f |" % (
            row["month"], row[KEY_BASE], row[KEY_VOICE], row[KEY_DATA], row[KEY_VAS], row[KEY_OTHER], row["total"]))
    lines.append("")
    lines.append("- \u6708\u5747\u652f\u51fa\uff1a%.2f" % summary["avg"])
    lines.append("- \u5e74\u5ea6\u4f30\u7b97\uff1a%.2f\uff08\u542b\u4e00\u6b21\u6027\u8d39\u7528 %.2f\uff09" % (summary["annual"], summary["one_off"]))
    lines.append("- \u5355\u4f4d\u6d41\u91cf\u6210\u672c\uff1a%s" % ("%.2f \u5143/GB" % summary["unit_cost"] if summary["unit_cost"] else "\u65e0\u6d41\u91cf\u6570\u636e"))
    lines.append("- \u5957\u9910\u5229\u7528\u7387\uff1a\u6d41\u91cf %.0f%%\uff0c\u8bed\u97f3 %.0f%%" % (summary["data_rate"] * 100, summary["voice_rate"] * 100))
    lines.append("")
    lines.append("## \u4e09\u3001\u964d\u5957\u4e0e\u643a\u53f7\u8f6c\u7f51\u969c\u788d")
    lines.append("")
    lines.append("| \u969c\u788d | \u5904\u7406\u65b9\u5411 |")
    lines.append("|---|---|")
    for name, action in obstacles:
        lines.append("| %s | %s |" % (name, action))
    lines.append("")
    lines.append("## \u56db\u3001\u5efa\u8bae")
    lines.append("")
    for tip in tips:
        lines.append("- %s" % tip)
    lines.append("")
    lines.append("> \u672c\u62a5\u544a\u4e3a\u4e2a\u4eba\u6574\u7406\u5de5\u5177\uff0c\u6700\u7ec8\u8d44\u8d39\u3001\u5408\u7ea6\u4e0e\u529e\u7406\u7ed3\u679c\u4ee5\u8fd0\u8425\u5546\u548c\u884c\u4e1a\u4e3b\u7ba1\u90e8\u95e8\u6838\u5b9a\u4e3a\u51c6\u3002")
    return "\n".join(lines)


def write_text(path, text):
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def build_report(case):
    rows = normalise_months(case)
    summary = summarise(case, rows)
    obstacles = build_obstacles(case)
    tips = suggestions(summary, len(obstacles))
    return render_report(case, rows, summary, obstacles, tips), summary


def run_selftest(script_dir):
    results = []
    case_a = {
        "\u5957\u9910\u6708\u8d39": 100.0,
        "\u5957\u9910\u5185\u6d41\u91cfGB": 40.0,
        "\u5957\u9910\u5185\u8bed\u97f3\u5206\u949f": 500.0,
        "\u4e00\u6b21\u6027\u8d39\u7528": 200.0,
        "\u6708\u4efd\u8d26\u5355": [
            {"month": "M1", KEY_BASE: 100.0, KEY_VOICE: 10.0, KEY_DATA: 20.0, KEY_VAS: 30.0, KEY_OTHER: 0.0, "data_gb": 20.0, "voice_minutes": 300.0},
            {"month": "M2", KEY_BASE: 100.0, KEY_VOICE: 0.0, KEY_DATA: 0.0, KEY_VAS: 30.0, KEY_OTHER: 0.0, "data_gb": 20.0, "voice_minutes": 300.0},
        ],
    }
    report_a, summary_a = build_report(case_a)
    results.append(("avg is 145", abs(summary_a["avg"] - 145.0) < 1e-6))
    results.append(("annual is 1940", abs(summary_a["annual"] - 1940.0) < 1e-6))
    results.append(("unit cost is 3.625", abs(summary_a["unit_cost"] - 3.625) < 1e-6))

    case_b = {"\u5957\u9910\u6708\u8d39": 50.0, "\u6708\u4efd\u8d26\u5355": [{"month": "M1"}, {"month": "M2"}]}
    _, summary_b = build_report(case_b)
    results.append(("missing months fall back to plan fee", abs(summary_b["avg"] - 50.0) < 1e-6))
    results.append(("no data means zero unit cost", summary_b["unit_cost"] == 0.0))

    case_c = {"\u5408\u7ea6": "\u5408\u7ea6\u672a\u5230\u671f", "\u5bbd\u5e26\u7ed1\u5b9a": "\u5df2\u7ed1\u5b9a", "\u6708\u4efd\u8d26\u5355": [{"month": "M1"}]}
    report_c, _ = build_report(case_c)
    results.append(("contract obstacle detected", "\u5408\u7ea6\u672a\u5230\u671f" in report_c))
    results.append(("broadband obstacle detected", "\u878d\u5408\u5957\u9910\u7ed1\u5b9a" in report_c))

    report_d, _ = build_report(dict(DEFAULT_CASE))
    results.append(("bound broadband is flagged even when positive", "\u878d\u5408\u5957\u9910\u7ed1\u5b9a" in report_d))

    case_e = {"\u5957\u9910\u6708\u8d39": 39.0, "\u6708\u4efd\u8d26\u5355": [{"month": "M1"}]}
    report_e, _ = build_report(case_e)
    results.append(("clean case reports no obstacle", "\u672a\u53d1\u73b0\u660e\u786e\u969c\u788d" in report_e))
    results.append(("clean case has no sub card line", "\u526f\u5361\u6216\u4eb2\u60c5\u7f51" not in report_e))

    probe = os.path.join(script_dir, "_selftest_sample.md")
    write_text(probe, report_a)
    results.append(("report file written", os.path.isfile(probe)))

    failed = [name for name, ok in results if not ok]
    lines = ["selftest cases: %d, passed: %d, failed: %d" % (len(results), len(results) - len(failed), len(failed))]
    for name, ok in results:
        lines.append("%s %s" % ("PASS" if ok else "FAIL", name))
    if failed:
        lines.append("SELFTEST FAILED")
    else:
        lines.append("SELFTEST OK")
    text = "\n".join(lines) + "\n"
    write_text(os.path.join(script_dir, "_selftest_result.txt"), text)
    return 0 if not failed else 1


def main():
    parser = argparse.ArgumentParser(description="Mobile plan cost audit helper")
    parser.add_argument("--file", help="case json file")
    parser.add_argument("--out", default="out", help="output directory")
    parser.add_argument("--selftest", action="store_true", help="run built-in self test")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    if args.selftest:
        return run_selftest(script_dir)

    case = load_case(args.file)
    report, summary = build_report(case)
    out_dir = args.out if os.path.isabs(args.out) else os.path.join(script_dir, args.out)
    report_path = os.path.join(out_dir, "\u8d44\u8d39\u6838\u67e5\u62a5\u544a.md")
    write_text(report_path, report)
    summary_path = os.path.join(out_dir, "_summary.txt")
    write_text(summary_path, "avg=%.2f\nannual=%.2f\nunit_cost=%.2f\n" % (
        summary["avg"], summary["annual"], summary["unit_cost"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
