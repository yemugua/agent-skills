# -*- coding: utf-8 -*-
"""backup_321_audit: 3-2-1 \u5907\u4efd\u539f\u5219\u9010\u9879\u6838\u67e5\u3002

\u7528\u6cd5:
    python backup_321_audit.py --file backup.json --out result.md
    python backup_321_audit.py --text "copies=2;media=1;offsite=no;auto=no;tested=no"
    python backup_321_audit.py --selftest
"""
import argparse
import json
import os

RULES = [
    ("copies", 3, "\u526f\u672c\u6570", "\u539f\u59cb\u6570\u636e\u7b97\u4e00\u4efd\uff0c\u53e6\u9700\u4e24\u4efd\u72ec\u7acb\u526f\u672c", 3),
    ("media", 2, "\u4ecb\u8d28\u79cd\u7c7b", "\u526f\u672c\u4e0d\u80fd\u5168\u90e8\u5728\u540c\u4e00\u53f0\u8bbe\u5907\u6216\u540c\u4e00\u4e2a\u670d\u52a1", 3),
    ("offsite", 1, "\u5f02\u5730\u526f\u672c", "\u81f3\u5c11\u4e00\u4efd\u4e0d\u5728\u540c\u5730\u4e14\u4e0d\u540c\u8d26\u53f7\u4f53\u7cfb", 2),
    ("auto", 1, "\u81ea\u52a8\u5907\u4efd", "\u5907\u4efd\u4efb\u52a1\u5fc5\u987b\u81ea\u52a8\u89e6\u53d1\uff0c\u624b\u52a8\u4e00\u6b21\u6027\u590d\u5236\u4e0d\u7b97", 2),
    ("tested", 1, "\u6062\u590d\u6f14\u7ec3", "\u6ca1\u6709\u771f\u7684\u53d6\u56de\u6765\u6253\u5f00\u8fc7\uff0c\u5c31\u4e0d\u80fd\u7b97\u6709\u6548\u5907\u4efd", 3),
    ("encrypted", 0, "\u52a0\u5bc6", "\u8bc1\u4ef6\u3001\u5408\u540c\u3001\u8d22\u52a1\u4e0e\u4ed6\u4eba\u9690\u79c1\u7c7b\u6570\u636e\u5e94\u52a0\u5bc6", 1),
]

PIT_ORDER = [
    "\u540c\u6b65\u5f53\u5907\u4efd\uff1a\u5728\u56de\u6536\u7ad9\u91cc\u80fd\u4e0d\u80fd\u627e\u5230\u53e6\u4e00\u4e2a\u65f6\u95f4\u70b9\u7684\u7248\u672c\u3002",
    "\u79fb\u52a8\u786c\u76d8\u6ca1\u8dd1\u5b8c\uff1a\u4efb\u52a1\u72b6\u6001\u662f\u4e0d\u662f\u5b8c\u6210\uff0c\u6587\u4ef6\u6570\u4e0e\u5927\u5c0f\u662f\u5426\u4e00\u81f4\u3002",
    "\u5386\u53f2\u7248\u672c\u88ab\u8986\u76d6\uff1a\u7248\u672c\u4fdd\u7559\u8bbe\u7f6e\u662f\u591a\u5c11\u5929\u3002",
    "\u5907\u4efd\u88ab\u6e05\u7406\u89c4\u5219\u5220\u6389\uff1a\u5b9a\u671f\u6e05\u7406\u811a\u672c\u662f\u5426\u8986\u76d6\u5907\u4efd\u76ee\u5f55\u3002",
    "\u5907\u4efd\u653e\u5728\u540c\u4e00\u8bbe\u5907\u7684\u4e24\u4e2a\u76ee\u5f55\uff1a\u8bbe\u5907\u574f\u4e86\u4f1a\u4e00\u8d77\u6ca1\u3002",
    "\u53e3\u4ee4\u4e0e\u6570\u636e\u540c\u653e\uff1a\u52a0\u5bc6\u7b49\u4e8e\u81ea\u9501\u3002",
]


def load_json(path):
    """Read JSON, tolerating the UTF-8 BOM written by PowerShell."""
    raw = open(path, "r", encoding="utf-8-sig").read().strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise ValueError("json parse failed: %s" % exc)


def to_int(value, default=0):
    """Coerce bool / number / yes-no string / list length into an int."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        return len(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("y", "yes", "true", "1"):
            return 1
        if v in ("n", "no", "false", "0"):
            return 0
        try:
            return int(float(v))
        except ValueError:
            return default
    return default


def parse_text(text):
    data = {}
    for chunk in str(text).replace(",", ";").split(";"):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        data[key.strip().lower()] = value.strip()
    return data


def audit(data):
    """Return (rows, gaps). rows carry pass/fail; gaps sorted by severity."""
    rows = []
    for key, need, cn, note, sev in RULES:
        got = to_int(data.get(key, 0))
        ok = got >= need
        rows.append(dict(key=key, cn=cn, note=note, need=need, got=got,
                         ok=ok, sev=0 if ok else sev))
    gaps = [r for r in rows if not r["ok"]]
    gaps.sort(key=lambda r: -r["sev"])
    return rows, gaps


def build_report(data):
    rows, gaps = audit(data)
    out = ["# 3-2-1 \u5907\u4efd\u6838\u67e5\u7ed3\u8bba", ""]
    out.append("| \u6838\u67e5\u9879 | \u8981\u6c42 | \u73b0\u72b6 | \u5224\u5b9a | \u8bf4\u660e |")
    out.append("|---|---|---|---|---|")
    for r in rows:
        out.append("| %s | >=%d | %d | %s | %s |" % (
            r["cn"], r["need"], r["got"], "PASS" if r["ok"] else "GAP", r["note"]))
    passed = len([r for r in rows if r["ok"]])
    out.append("")
    out.append("\u901a\u8fc7 %d/%d \u9879\u3002" % (passed, len(rows)))
    out.append("")
    if gaps:
        out.append("## \u7f3a\u53e3\uff08\u6309\u4e25\u91cd\u5ea6\u6392\u5e8f\uff09")
        out.append("")
        for i, r in enumerate(gaps, 1):
            out.append("%d. %s\uff08\u4e25\u91cd\u5ea6 %d\uff09\uff1a\u5f53\u524d %d\uff0c\u8981\u6c42 >=%d\u3002%s" % (
                i, r["cn"], r["sev"], r["got"], r["need"], r["note"]))
        out.append("")
        out.append("## \u8865\u9f50\u987a\u5e8f\u5efa\u8bae")
        out.append("")
        out.append("1. \u5148\u8865\u6700\u8981\u547d\u7684\u4e00\u9879\uff1a\u526f\u672c\u6570\u3001\u4ecb\u8d28\u79cd\u7c7b\u3001\u6062\u590d\u6f14\u7ec3\u4e09\u9879\u91cc\u7f3a\u7684\u4f18\u5148\u3002")
        out.append("2. \u989d\u5ea6\u6709\u9650\u65f6\u6309\u4e0d\u53ef\u518d\u751f\u8d44\u6599\u4f18\u5148\uff1a\u8bc1\u4ef6\u5408\u540c\u3001\u8d26\u76ee\u3001\u5bb6\u5ead\u5f71\u50cf\u5728\u524d\u3002")
        out.append("3. \u8865\u5b8c\u505a\u4e00\u6b21\u771f\u6062\u590d\u6f14\u7ec3\uff0c\u53d6\u56de\u6587\u4ef6\u9010\u4e2a\u6253\u5f00\u5e76\u8bb0\u5f55\u7ed3\u679c\u3002")
        out.append("4. \u8bbe\u5b9a\u5b63\u5ea6\u590d\u67e5\u8282\u594f\uff0c\u5199\u6210\u68c0\u67e5\u8868\u3002")
    else:
        out.append("\u516d\u9879\u5168\u90e8\u8fbe\u6807\u3002\u4e0b\u4e00\u6b65\u662f\u5b89\u6392\u6062\u590d\u6f14\u7ec3\u8282\u594f\uff0c\u5e76\u5199\u6210\u5b63\u5ea6\u68c0\u67e5\u8868\u3002")
    out.append("")
    out.append("## \u5e38\u89c1\u5047\u5907\u4efd\u5751\u5bf9\u7167")
    out.append("")
    for line in PIT_ORDER:
        out.append("- " + line)
    out.append("")
    out.append("## \u8fb9\u754c")
    out.append("")
    out.append("- \u672c\u811a\u672c\u53ea\u505a\u89c4\u5219\u5224\u5b9a\uff0c\u4e0d\u8bbf\u95ee\u4e5f\u4e0d\u4f20\u8f93\u4efb\u4f55\u6570\u636e")
    out.append("- \u6062\u590d\u80fd\u529b\u4f1a\u968f\u7248\u672c\u66f4\u65b0\u4e0e\u4ecb\u8d28\u8001\u5316\u53d8\u5316\uff0c\u6f14\u7ec3\u7ed3\u679c\u53ea\u53cd\u6620\u5f53\u65f6\u72b6\u6001")
    return "\n".join(out) + "\n"


def selftest():
    cases = []
    good = {"copies": 3, "media": 2, "offsite": "yes", "auto": "yes",
            "tested": "yes", "encrypted": "yes"}
    rows, gaps = audit(good)
    cases.append(("all_pass", len(gaps) == 0 and len(rows) == 6))
    cases.append(("all_gap", len(audit({"copies": 2, "media": 1})[1]) == 5))
    cases.append(("list_len", to_int(["a", "b"]) == 2))
    cases.append(("dict_len", to_int({"a": 1, "b": 2}) == 2))
    cases.append(("bool_true", to_int(True) == 1))
    cases.append(("bool_false", to_int(False) == 0))
    cases.append(("str_yes", to_int("YES") == 1))
    cases.append(("str_no", to_int("no") == 0))
    cases.append(("str_bad", to_int("abc", 3) == 3))
    cases.append(("num_float", to_int(2.9) == 2))
    cases.append(("none", to_int(None) == 0))
    gaps = audit({"copies": 1})[1]
    sevs = [r["sev"] for r in gaps]
    cases.append(("sev_sorted", sevs == sorted(sevs, reverse=True)))
    cases.append(("tested_high_sev",
                  [r["sev"] for r in audit({"tested": 0})[1] if r["key"] == "tested"][0] == 3))
    rep = build_report(good)
    cases.append(("rep_all_pass", "6/6" in rep and "GAP" not in rep))
    cases.append(("rep_done", "\u5168\u90e8\u8fbe\u6807" in rep))
    rep2 = build_report({"copies": 2})
    cases.append(("rep_gap", "GAP" in rep2 and "\u7f3a\u53e3" in rep2))
    cases.append(("rep_order", rep2.index("\u526f\u672c\u6570") < rep2.index("\u4ecb\u8d28\u79cd\u7c7b")))
    cases.append(("parse_text", parse_text("copies=3;media=2")["media"] == "2"))
    cases.append(("parse_comma", parse_text("copies=1,media=1")["media"] == "1"))
    bom = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_probe.json")
    with open(bom, "w", encoding="utf-8-sig") as f:
        f.write('{"copies": 3}')
    try:
        cases.append(("bom_ok", load_json(bom).get("copies") == 3))
    finally:
        if os.path.exists(bom):
            os.remove(bom)
    lines = []
    for i, (name, ok) in enumerate(cases, 1):
        lines.append("case %02d %-18s %s" % (i, name, "PASS" if ok else "FAIL"))
    bad = [n for n, ok in cases if not ok]
    lines.append("")
    lines.append("SELFTEST %s (%d/%d)" % ("OK" if not bad else "FAILED",
                                         len(cases) - len(bad), len(cases)))
    if bad:
        lines.append("failed: " + ", ".join(bad))
    text = "\n".join(lines) + "\n"
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "_selftest_result.txt"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(text)
    return 0 if not bad else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="3-2-1 backup audit")
    ap.add_argument("--file", default=None)
    ap.add_argument("--text", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--format", default="md")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    data = {}
    if a.file:
        try:
            data = load_json(a.file)
        except Exception as exc:
            print(str(exc))
            return 2
    elif a.text:
        data = parse_text(a.text)
    report = build_report(data)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "backup_321_result.md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
