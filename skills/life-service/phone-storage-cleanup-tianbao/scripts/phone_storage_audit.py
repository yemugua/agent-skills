# -*- coding: utf-8 -*-
"""phone_storage_audit: \u624b\u673a\u5b58\u50a8\u5360\u7528\u5206\u7c7b\u4e0e\u6e05\u7406\u98ce\u9669\u6392\u5e8f\u3002

\u7528\u6cd5:
    python phone_storage_audit.py --file usage.json --out result.md
    python phone_storage_audit.py --text "wechat:20G photo:30G other:12G"
    python phone_storage_audit.py --selftest
"""
import argparse
import json
import os
import re

SIZE_RE = re.compile(r"^([0-9]+(?:[.][0-9]+)?)\s*([a-zA-Z]*)$")

UNIT_TO_GB = {
    "": 1.0 / 1024.0 / 1024.0 / 1024.0,
    "k": 1.0 / 1024.0 / 1024.0,
    "kb": 1.0 / 1024.0 / 1024.0,
    "m": 1.0 / 1024.0,
    "mb": 1.0 / 1024.0,
    "g": 1.0,
    "gb": 1.0,
    "t": 1024.0,
    "tb": 1024.0,
}

ALIAS = {
    "photo": "photos", "photos": "photos", "camera": "photos",
    "wechat": "chatmedia", "qq": "chatmedia", "chat": "chatmedia",
    "chatmedia": "chatmedia",
    "cache": "cache", "app_cache": "cache",
    "download": "downloads", "downloads": "downloads",
    "app": "apps", "apps": "apps",
    "data": "appdata", "appdata": "appdata",
    "sys": "syslog", "syslog": "syslog",
    "other": "other", "misc": "other",
}

PROFILE = {
    "cache": dict(cn="\u5e94\u7528\u7f13\u5b58", risk="\u4f4e", ratio=0.7,
                  backup="\u4e0d\u9700\u8981", regen="\u4f1a\u91cd\u65b0\u751f\u6210", order=1),
    "syslog": dict(cn="\u7cfb\u7edf\u65e5\u5fd7\u4e0e\u4e34\u65f6\u6587\u4ef6", risk="\u4f4e", ratio=0.6,
                   backup="\u4e0d\u9700\u8981", regen="\u7cfb\u7edf\u4f1a\u81ea\u884c\u6e05\u7406", order=2),
    "downloads": dict(cn="\u4e0b\u8f7d\u76ee\u5f55", risk="\u4f4e", ratio=0.7,
                      backup="\u786e\u8ba4\u65e0\u672a\u5907\u4efd\u7684\u91cd\u8981\u6587\u4ef6", regen="\u4e0d\u4f1a", order=3),
    "apps": dict(cn="\u5e94\u7528\u672c\u4f53", risk="\u4f4e", ratio=1.0,
                 backup="\u786e\u8ba4\u8d26\u53f7\u6570\u636e\u4e0e\u8fdb\u5ea6\u53ef\u63a5\u53d7\u4e22\u5931", regen="\u4e0d\u4f1a", order=4),
    "chatmedia": dict(cn="\u804a\u5929\u8bb0\u5f55\u4e0e\u5a92\u4f53", risk="\u4e2d", ratio=0.6,
                      backup="\u5148\u5907\u4efd\u91cd\u8981\u8bb0\u5f55\u4e0e\u6587\u4ef6", regen="\u7ee7\u7eed\u804a\u5929\u4f1a\u518d\u6da8", order=5),
    "other": dict(cn="\u5176\u4ed6\u4e0d\u660e\u5360\u7528", risk="\u4e2d", ratio=0.0,
                  backup="\u5148\u770b\u6e05\u91cc\u9762\u662f\u4ec0\u4e48", regen="\u89c6\u60c5\u51b5\u800c\u5b9a", order=6),
    "photos": dict(cn="\u7167\u7247\u4e0e\u89c6\u9891", risk="\u9ad8", ratio=0.6,
                   backup="\u5148\u590d\u5236\u51fa\u7167\u7247\u5e76\u53e6\u5b58", regen="\u7ee7\u7eed\u62cd\u6444\u4f1a\u518d\u6da8", order=7),
    "appdata": dict(cn="\u5e94\u7528\u6570\u636e", risk="\u9ad8", ratio=0.3,
                    backup="\u5148\u5907\u4efd\u5185\u5bb9", regen="\u4e0d\u4f1a", order=8),
}

IRRECOVERABLE = ["photos", "chatmedia", "appdata"]

SIZE_KEYS = ("size_gb", "size_mb", "gb", "mb", "size", "bytes")

EMPTY_REPORT = "# \u624b\u673a\u5b58\u50a8\u5360\u7528\u8bca\u65ad\n\n\u672a\u8bfb\u5230\u6709\u6548\u5360\u7528\u6570\u636e\uff0c\u8bf7\u68c0\u67e5\u8f93\u5165\u683c\u5f0f\u3002\n"


def load_json(path):
    """Read JSON, tolerating the UTF-8 BOM written by PowerShell."""
    raw = open(path, "r", encoding="utf-8-sig").read().strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise ValueError("json parse failed: %s" % exc)


def parse_size(token):
    """Parse '30G' / '2048MB' / '5' into gigabytes. Returns 0.0 on failure."""
    m = SIZE_RE.match(str(token).strip().lower())
    if not m:
        return 0.0
    return float(m.group(1)) * UNIT_TO_GB.get(m.group(2), 0.0)


def parse_entry(key, value):
    """Return (canonical_key, size_gb). Accepts 30, '30G', {'size_gb': 30}."""
    k = ALIAS.get(str(key).strip().lower(), "other")
    if isinstance(value, bool):
        return k, 0.0
    if isinstance(value, (int, float)):
        return k, float(value)
    if isinstance(value, dict):
        for kk in SIZE_KEYS:
            if kk in value:
                try:
                    return k, float(value[kk])
                except (TypeError, ValueError):
                    return k, 0.0
        return k, 0.0
    return k, parse_size(value)


def collect(source):
    """Normalise dict / list / 'key:size' tokens into {canonical_key: gb}."""
    out = {}
    if isinstance(source, str):
        toks = source.replace(":", " ").split()
        pairs_txt = [(toks[i], " ".join(toks[i + 1:]))
                     for i in range(0, len(toks) - 1, 2)]
        source = [{k: v} for k, v in pairs_txt]
    if isinstance(source, list):
        items = []
        for it in source:
            if isinstance(it, dict):
                items.append(it)
            elif isinstance(it, str):
                parts = it.replace(":", " ").split()
                if len(parts) >= 2:
                    items.append({parts[0]: " ".join(parts[1:])})
        source = items
    if not isinstance(source, (dict, list)):
        return {}
    if isinstance(source, dict):
        for wrap in ("usage", "data", "categories", "items"):
            inner = source.get(wrap)
            if isinstance(inner, (dict, list)):
                source = inner
                break
    if isinstance(source, list):
        pairs = []
        for it in source:
            if isinstance(it, dict):
                key = it.get("key") or it.get("name") or it.get("category")
                if key is not None:
                    val = it.get("size", it.get("value", it))
                    pairs.append((key, val))
                elif len(it) == 1:
                    pairs.extend(it.items())
                else:
                    pairs.append(("other", 0.0))
            else:
                k, v = parse_entry("other", it)
                pairs.append((k, v))
    else:
        pairs = list(source.items())
    for key, value in pairs:
        k, v = parse_entry(key, value)
        if v > 0:
            out[k] = round(out.get(k, 0.0) + v, 3)
    return out


def build_report(usage, total_gb=None):
    data = collect(usage)
    if not data:
        return EMPTY_REPORT
    items = sorted(data.items(), key=lambda kv: kv[1], reverse=True)
    total = float(total_gb) if total_gb else sum(v for _, v in items)
    if total <= 0:
        total = sum(v for _, v in items)
    out = ["# \u624b\u673a\u5b58\u50a8\u5360\u7528\u8bca\u65ad", ""]
    out.append("| \u7c7b\u522b | \u5360\u7528 | \u5360\u6bd4 | \u98ce\u9669 | \u53ef\u6e05\u6bd4\u4f8b | \u6e05\u7406\u524d\u5fc5\u987b\u786e\u8ba4 | \u6e05\u5b8c\u662f\u5426\u518d\u957f |")
    out.append("|---|---|---|---|---|---|---|")
    for k, v in items:
        p = PROFILE[k]
        share = (v / total * 100.0) if total else 0.0
        out.append("| %s | %.1f GB | %.0f%% | %s | %d%% | %s | %s |" % (
            p["cn"], v, share, p["risk"], int(p["ratio"] * 100),
            p["backup"], p["regen"]))
    out.append("")
    out.append("\u5408\u8ba1 %.1f GB" % total)
    out.append("")
    out.append("## \u4e0d\u53ef\u6062\u590d\u9879\uff08\u5148\u5907\u4efd\u518d\u52a8\uff09")
    out.append("")
    for k in IRRECOVERABLE:
        if k in data:
            out.append("- %s\uff1a%s" % (PROFILE[k]["cn"], PROFILE[k]["backup"]))
    out.append("- \u7cfb\u7edf\u56de\u6536\u7ad9\u901a\u5e38\u53ea\u7559\u51e0\u5929\uff0c\u90e8\u5206\u673a\u578b\u4e0d\u7559\uff0c\u5907\u4efd\u6ca1\u505a\u5c31\u5220\u7b49\u4e8e\u8d4c\u3002")
    out.append("")
    out.append("## \u5efa\u8bae\u6267\u884c\u987a\u5e8f\uff08\u98ce\u9669\u4ece\u4f4e\u5230\u9ad8\uff09")
    out.append("")
    for k, p in sorted(PROFILE.items(), key=lambda kv: kv[1]["order"]):
        if k in data:
            out.append("%d. %s \u2014\u2014 \u98ce\u9669%s\uff0c\u6e05\u7406\u540e%s" % (
                p["order"], p["cn"], p["risk"], p["regen"]))
    out.append("")
    if "other" in data:
        out.append("## \u6ce8\u610f")
        out.append("")
        out.append("- \u5176\u4ed6\u662f\u4e0d\u660e\u5360\u7528\uff1a\u5148\u6253\u5f00\u770b\u6e05\u5185\u5bb9\uff0c\u4e0d\u8981\u6574\u7c7b\u6e05\u7a7a\u3002")
    out.append("- \u6bcf\u6e05\u4e00\u7c7b\uff0c\u9694\u4e00\u5929\u518d\u770b\u5360\u7528\u53d8\u5316\uff1b\u6301\u7eed\u589e\u957f\u7684\u7c7b\u522b\u624d\u662f\u771f\u95ee\u9898\u3002")
    out.append("- \u7cfb\u7edf\u6838\u5fc3\u6587\u4ef6\u4e0d\u8981\u6e05\u7406\u3002")
    out.append("- \u7ed9\u8001\u4eba\u5b69\u5b50\u6e05\u7406\u65f6\uff0c\u5148\u51fa\u62a5\u544a\u8ba9\u5176\u77e5\u60c5\uff0c\u4e0d\u52a8\u901a\u8baf\u5f55\u3001\u7167\u7247\u4e0e\u5b89\u5168\u8bbe\u7f6e\u3002")
    return "\n".join(out) + "\n"


def selftest():
    cases = []
    cases.append(("parse_g", abs(parse_size("30G") - 30.0) < 1e-9))
    cases.append(("parse_mb", abs(parse_size("2048MB") - 2.0) < 1e-6))
    cases.append(("parse_unit", abs(parse_size("1024MB") - 1.0) < 1e-9))
    cases.append(("parse_plain", parse_size("5") > 0))
    cases.append(("parse_bad", parse_size("abc") == 0.0))
    cases.append(("alias_photo", parse_entry("photo", "30G")[0] == "photos"))
    cases.append(("alias_wechat", parse_entry("wechat", 1)[0] == "chatmedia"))
    cases.append(("alias_unknown", parse_entry("zzz", 1)[0] == "other"))
    cases.append(("dict_value", parse_entry("cache", {"size_gb": 4})[1] == 4.0))
    cases.append(("dict_miss", parse_entry("cache", {"x": 1})[1] == 0.0))
    cases.append(("collect_sum", abs(collect(
        {"photo": "10G", "wechat": "5G"})["photos"] - 10.0) < 1e-9))
    cases.append(("collect_merge", abs(collect(
        {"photo": "10G", "camera": "5G"})["photos"] - 15.0) < 1e-9))
    data = collect({"photo": "30G", "wechat": "20G", "other": "12G",
                    "cache": "6G"})
    rep = build_report(data)
    cases.append(("rep_sorted", rep.index("\u7167\u7247") < rep.index("\u804a\u5929\u8bb0\u5f55")))
    cases.append(("rep_total", "68.0 GB" in rep))
    cases.append(("rep_other_flag", "\u4e0d\u8981\u6574\u7c7b\u6e05\u7a7a" in rep))
    order_part = rep.split("## \u5efa\u8bae\u6267\u884c\u987a\u5e8f")[-1]
    cases.append(("rep_order",
                  order_part.index("\u5e94\u7528\u7f13\u5b58") < order_part.index("\u7167\u7247")))
    cases.append(("rep_empty", "\u672a\u8bfb\u5230\u6709\u6548\u5360\u7528\u6570\u636e" in build_report({})))
    cases.append(("rep_str_input", "\u7167\u7247" in build_report("photo:3G")))
    cases.append(("total_share", "25%" in build_report({"photo": "30G",
                                                         "other": "30G"}, 120)))
    bom = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_probe.json")
    with open(bom, "w", encoding="utf-8-sig") as f:
        f.write('{"photo": "1G"}')
    try:
        cases.append(("bom_ok", load_json(bom).get("photo") == "1G"))
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
    ap = argparse.ArgumentParser(description="phone storage audit")
    ap.add_argument("--file", default=None)
    ap.add_argument("--text", default=None)
    ap.add_argument("--total", default=None, help="device total capacity in GB")
    ap.add_argument("--out", default=None)
    ap.add_argument("--format", default="md")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    usage = None
    if a.file:
        try:
            usage = load_json(a.file)
        except Exception as exc:
            print(str(exc))
            return 2
    elif a.text:
        usage = a.text
    if usage is None:
        usage = []
    report = build_report(usage, a.total)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "phone_storage_result.md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
