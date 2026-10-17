# -*- coding: utf-8 -*-
"""Prometheus \u6307\u6807\u547d\u540d\u4e0e\u544a\u8b66\u89c4\u5219\u9759\u6001\u68c0\u67e5\u3002

\u7528\u6cd5:
  python prometheus_rules_check.py --selftest
  python prometheus_rules_check.py --kind metrics --file scrape.txt
  python prometheus_rules_check.py --kind rules --file alerts.yml --scrape-interval 15
"""
import argparse
import io
import json
import os
import re
import sys

FAILS = []

LEVELS = ["\u4e25\u91cd", "\u9519\u8bef", "\u8b66\u793a", "\u63d0\u793a", "\u597d"]

UNIT_BAD_SUFFIX = ("_ms", "_milliseconds", "_mb", "_kb", "_gb", "_tb", "_us", "_nanoseconds")
GAUGE_SUFFIX = ("_bytes", "_ratio", "_celsius", "_kelvin", "_timestamp_seconds")
RESERVED_LABELS = ("le", "quantile", "__name__", "job", "instance")
BLACKLIST_LABELS = (
    "user_id", "uid", "order_id", "request_id", "trace_id", "session_id",
    "uuid", "guid", "email", "phone", "ip", "mac", "url", "uri", "referer",
    "cookie", "timestamp", "date", "error_message", "message", "stacktrace",
    "pod_name", "container_id", "hostname",
)
NAME_RE = re.compile(r"^[a-z][a-z0-9_:]*$")
KEY_RE = re.compile(r"^(- )?([A-Za-z_][\w.-]*):\s*(.*)$")
DUR_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([smhdwyMS])")
RATE_RE = re.compile(r"\b(rate|irate|increase|delta|deriv)\(\s*([^\[\]]*?)\[([^\]]+)\]")
METRIC_NAME_RE = re.compile(r"([a-zA-Z_:][a-zA-Z0-9_:]*)")

DEFAULT_MIN_RATE_WINDOW_MULTI = 4


def ck(label, cond):
    if not cond:
        FAILS.append(label)
    return bool(cond)


def write_result(path):
    lines = ["SELFTEST %s" % ("OK" if not FAILS else "FAILED")]
    for f in FAILS:
        lines.append("  FAILED: %s" % f)
    io.open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))


def parse_duration(text):
    """\u628a 5m / 2m30s / 1h \u7edf\u4e00\u6362\u7b97\u6210\u79d2\u3002"""
    if not text:
        return 0
    s = str(text).strip().lower()
    unit = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "y": 31536000}
    total = 0
    for num, u in DUR_RE.findall(s):
        total += float(num) * unit.get(u, 1)
    if total == 0:
        try:
            total = float(s)
        except ValueError:
            total = 0
    return total


def balanced_segment(text, start):
    """\u4ece text[start] \u5904\u7684\u51fd\u6570\u540d\u5f00\u59cb\uff0c\u8fd4\u56de\u8986\u76d6\u6574\u4e2a\u8c03\u7528\u7684\u5e73\u8861\u62ec\u53f7\u7247\u6bb5\u3002"""
    i = text.find("(", start)
    if i < 0:
        return ""
    return text[start:i] + paren_span(text, i)


def paren_span(text, open_idx):
    depth = 0
    for j in range(open_idx, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return text[open_idx:j + 1]
    return text[open_idx:]


def find_calls(text, func):
    """\u517c\u5bb9 sum by (x) (...) \u4e0e sum(...) by (x) \u4e24\u79cd\u5199\u6cd5\u3002"""
    out = []
    pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(func)
                     + r"\s*(?:(?:by|without)\s*\([^)]*\)\s*)?\(")
    for m in pat.finditer(text):
        out.append(text[m.start():m.end() - 1] + paren_span(text, m.end() - 1))
    return out


# ---------------------------------------------------------------- rule yaml

def parse_rules(text):
    """\u7b80\u6613 YAML \u89e3\u6790\u5668\uff1a\u591f\u7528\u8303\u56f4\u8986\u76d6 Prometheus rule \u6587\u4ef6\u7684\u5e38\u89c1\u5199\u6cd5\u3002"""
    prepared = []
    for raw in text.splitlines():
        s = raw.replace("\t", "  ").rstrip()
        if not s.strip() or s.strip().startswith("#"):
            continue
        prepared.append((len(s) - len(s.lstrip(" ")), s.strip()))

    groups = []
    group = None
    cur = None
    field = None
    field_indent = 0
    buf = []

    def flush():
        if cur is not None and field is not None:
            val = " ".join(x.strip() for x in buf if x.strip()).strip()
            if field in ("labels", "annotations"):
                return
            if field == "expr":
                cur["expr"] = val
            else:
                cur[field] = val

    for indent, content in prepared:
        m = KEY_RE.match(content)
        if m and cur is not None and field in ("labels", "annotations") \
                and indent > cur.get("_map_indent", 0):
            flush()
            key = m.group(2)
            val = m.group(3).strip().strip("'\"")
            cur.setdefault(field, {})[key] = val
            continue
        if field in ("labels", "annotations"):
            flush()
            field = None
            field_indent = 0
            buf = []
        m = KEY_RE.match(content)
        if not m:
            if field is not None and indent > field_indent:
                buf.append(content)
            continue
        flush()
        dash, key, val = m.group(1), m.group(2), m.group(3)
        if key == "name" and dash:
            group = val.strip().strip("'\"")
            cur = None
            field = None
            field_indent = 0
            buf = []
            continue
        if key in ("alert", "record") and dash:
            cur = {"group": group, "type": "alert" if key == "alert" else "record",
                   key: val.strip().strip("'\""), "expr": "", "for": "",
                   "labels": {}, "annotations": {}}
            groups.append(cur)
            field = None
            field_indent = 0
            buf = []
            continue
        if cur is None:
            continue
        if key in ("labels", "annotations"):
            field = key
            field_indent = indent
            cur["_map_indent"] = indent
            cur.setdefault(key, {})
            buf = []
            continue
        field = key
        field_indent = indent
        buf = [val]
    flush()
    for g in groups:
        g.pop("_map_indent", None)
    return groups


def check_expr(rule, scrape_interval):
    issues = []
    expr = rule.get("expr", "") or ""
    if not expr.strip():
        issues.append(("\u9519\u8bef", "expr \u4e3a\u7a7a"))
        return issues

    lower = expr.lower()
    if lower.startswith("sum(") and " by " not in lower and " without " not in lower:
        issues.append(("\u4e25\u91cd", "expr \u8fd4\u56de\u6807\u91cf\u800c\u4e0d\u662f\u77ac\u65f6\u5411\u91cf\uff08promtool \u4f1a\u76f4\u63a5\u62a5\u9519\uff09\uff1a\u9876\u5c42\u805a\u5408\u6ca1\u6709 by/without"))

    for m in RATE_RE.finditer(expr):
        fn = m.group(1)
        metric = m.group(2).strip()
        window = parse_duration(m.group(3))
        need = scrape_interval * DEFAULT_MIN_RATE_WINDOW_MULTI
        if fn in ("rate", "increase", "irate") and window > 0 and window < need:
            issues.append(("\u9519\u8bef", "%s \u7a97\u53e3 %s \u79d2\u5c0f\u4e8e\u63a8\u8350\u7684 %d \u79d2\uff084 \u500d\u6293\u53d6\u95f4\u9694 %d \u79d2\uff09" % (
                fn, int(window), int(need), scrape_interval)))
        if fn == "irate":
            issues.append(("\u8b66\u793a", "irate \u53ea\u770b\u6700\u540e\u4e24\u4e2a\u6837\u672c\u70b9\uff0c\u6781\u5176\u6296\u52a8\uff0c\u544a\u8b66\u8bf7\u6539\u7528 rate"))
        base = metric.split("{")[0].strip()
        if base and base.endswith(GAUGE_SUFFIX) and not base.endswith("_total"):
            issues.append(("\u9519\u8bef", "%s \u662f Gauge\uff0c\u4e0d\u80fd\u7528 %s \u8ba1\u7b97\u901f\u7387" % (base, fn)))

    if re.search(r"rate\s*\(\s*sum\s*\(", expr):
        issues.append(("\u9519\u8bef", "\u5148 sum \u518d rate\uff1a\u591a\u4e2a series \u6c42\u548c\u540e\u88ab\u5f53\u6210\u5355\u4e2a Counter\uff0ccounter reset \u4f1a\u6c61\u67d3\u6574\u6bb5\u7ed3\u679c"))

    for seg in find_calls(expr, "sum"):
        if " by " in seg or " without " in seg:
            continue
        idx = expr.find(seg)
        tail_raw = expr[idx + len(seg):]
        cut = re.search(r"\s(?:and|or|unless|==|!=|>=|<=|>|<)\s|[/*]", tail_raw)
        tail = tail_raw[:cut.start()] if cut else tail_raw[:80]
        if " by " not in tail and " without " not in tail:
            issues.append(("\u8b66\u793a", "sum \u672a\u6307\u5b9a by/without\uff0c\u7ed3\u679c\u4e0e\u7ef4\u5ea6\u4e0d\u53ef\u63a7\uff1a%s" % seg[:40]))
            break

    for seg in find_calls(expr, "histogram_quantile"):
        has_le = False
        for grp in re.findall(r"(?:by|without)\s*\(([^)]*)\)", seg):
            if "le" in [x.strip() for x in grp.split(",")]:
                has_le = True
        if not has_le:
            issues.append(("\u9519\u8bef", "histogram_quantile \u7684\u805a\u5408\u6ca1\u6709\u4fdd\u7559 le \u6807\u7b7e\uff0c\u5206\u4f4d\u6570\u65e0\u6cd5\u8ba1\u7b97"))
            break

    if " up " in expr or expr.strip().startswith("up") or "up==" in expr.replace(" ", ""):
        if "== 0" in expr and "absent" not in expr:
            issues.append(("\u63d0\u793a", "up == 0 \u53ea\u80fd\u53d1\u73b0\u5df2\u5b58\u5728\u7684\u76ee\u6807\uff0c\u5b9e\u4f8b\u88ab\u6458\u6389\u65f6 series \u6d88\u5931\uff0c\u5efa\u8bae\u8865\u5145 absent() \u68c0\u6d4b"))
    if "/" in expr and "and " not in expr.lower() and "rate(" in lower:
        issues.append(("\u63d0\u793a", "\u6bd4\u503c\u7c7b\u544a\u8b66\u5efa\u8bae\u53e0\u52a0\u6700\u5c0f\u6837\u672c\u91cf\u6761\u4ef6\uff0c\u907f\u514d\u4f4e\u6d41\u91cf\u65f6\u6bb5\u8bef\u62a5"))
    return issues


def check_rule(rule, scrape_interval):
    issues = []
    name = rule.get("alert") or rule.get("record")
    if rule["type"] == "alert":
        if not rule.get("for"):
            issues.append(("\u9519\u8bef", "\u7f3a\u5c11 for\uff1a\u77ac\u65f6\u6296\u52a8\u5373\u53ef\u89e6\u53d1\u544a\u8b66\uff0c\u5fc5\u7136\u4ea7\u751f\u544a\u8b66\u98ce\u66b4"))
        else:
            sec = parse_duration(rule["for"])
            if sec < 60:
                issues.append(("\u8b66\u793a", "for=%s \u4e0d\u8db3 1 \u5206\u949f\uff0c\u4ecd\u4f1a\u660e\u663e\u6296\u52a8" % rule["for"]))
            elif sec > 3600:
                issues.append(("\u63d0\u793a", "for=%s \u8d85\u8fc7 1 \u5c0f\u65f6\uff0c\u771f\u5b9e\u6545\u969c\u53ef\u80fd\u957f\u671f\u4e0d\u88ab\u901a\u77e5" % rule["for"]))
        labels = rule.get("labels", {}) or {}
        if "severity" not in labels:
            issues.append(("\u9519\u8bef", "\u7f3a\u5c11 severity \u6807\u7b7e\uff1a\u65e0\u6cd5\u5206\u7ea7\u8def\u7531\uff0c\u6240\u6709\u544a\u8b66\u7b49\u4ef7\u5904\u7406"))
        elif labels["severity"] not in ("critical", "warning", "info"):
            issues.append(("\u63d0\u793a", "severity=%s \u4e0d\u5728\u5efa\u8bae\u7684\u4e09\u6863\u4e4b\u5185" % labels["severity"]))
        ann = rule.get("annotations", {}) or {}
        if "summary" not in ann:
            issues.append(("\u63d0\u793a", "\u7f3a\u5c11 annotations.summary\uff1a\u503c\u73ed\u540c\u5b66\u770b\u4e0d\u51fa\u8fd9\u6761\u544a\u8b66\u5728\u8bf4\u4ec0\u4e48"))
        if "description" not in ann:
            issues.append(("\u63d0\u793a", "\u7f3a\u5c11 annotations.description\uff1a\u6ca1\u6709\u5f53\u524d\u503c\u4e0e\u5224\u65ad\u4f9d\u636e"))
        if "runbook_url" not in ann and "runbook" not in ann:
            issues.append(("\u63d0\u793a", "\u7f3a\u5c11 runbook_url\uff1a\u63a5\u624b\u7684\u4eba\u4e0d\u77e5\u9053\u4e0b\u4e00\u6b65\u505a\u4ec0\u4e48"))
        issues.extend(check_expr(rule, scrape_interval))
    else:
        if name.count(":") != 2:
            issues.append(("\u9519\u8bef", "recording rule %s \u4e0d\u7b26\u5408 level:metric:operation \u4e09\u6bb5\u5f0f\u547d\u540d" % name))
        else:
            parts = name.split(":")
            if parts[1].endswith("_total"):
                issues.append(("\u63d0\u793a", "recording rule %s \u7684 metric \u6bb5\u4fdd\u7559\u4e86 _total\uff0c\u5efa\u8bae\u53bb\u6389" % name))
            if not parts[2]:
                issues.append(("\u9519\u8bef", "recording rule %s \u7f3a\u5c11 operation \u6bb5" % name))
        if name.endswith("_total"):
            issues.append(("\u8b66\u793a", "recording rule \u8f93\u51fa %s \u5e26\u4e86 _total \u540e\u7f00\uff0c\u8f93\u51fa\u8d70 Gauge \u8bed\u4e49\u4e0d\u8be5\u7528" % name))
        issues.extend(check_expr(rule, scrape_interval))
    return issues


# ---------------------------------------------------------------- /metrics

def parse_metrics(text):
    """\u89e3\u6790 /metrics \u6587\u672c\uff0c\u8fd4\u56de {name: {type, labels: {label: set(values)}, combos}}\u3002"""
    info = {}
    order = []

    def get(name):
        if name not in info:
            info[name] = {"name": name, "type": "", "labels": {}, "samples": 0, "combos": set()}
            order.append(name)
        return info[name]

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            m = re.match(r"#\s*TYPE\s+(\S+)\s+(\S+)", line)
            if m:
                get(m.group(1))["type"] = m.group(2).lower()
            continue
        parts = line.split(None, 1)
        head = parts[0]
        if "{" in head:
            name = head.split("{", 1)[0]
            labels_src = head.split("{", 1)[1].rstrip("}")
        else:
            name = head
            labels_src = ""
        rec = get(name)
        rec["samples"] += 1
        labels = {}
        for kv in re.findall(r'([A-Za-z_][\w]*)\s*=\s*"([^"]*)"', labels_src):
            labels[kv[0]] = kv[1]
        combo = tuple(sorted(labels.items()))
        rec["combos"].add(combo)
        for k, v in labels.items():
            rec["labels"].setdefault(k, set()).add(v)
    return [info[n] for n in order]


def estimate_series(rec):
    n = 1
    for k, vals in rec["labels"].items():
        n *= max(1, len(vals))
    return n


def check_metric(rec, max_series):
    issues = []
    name = rec["name"]
    typ = rec["type"]
    if not NAME_RE.match(name):
        issues.append(("\u9519\u8bef", "\u6307\u6807\u540d %s \u4e0d\u7b26\u5408\u547d\u540d\u89c4\u5219\uff08\u5e94\u5168\u5c0f\u5199\u3001\u4e0b\u5212\u7ebf\u5206\u8bcd\u3001\u65e0\u8fde\u5b57\u7b26\uff09" % name))
    for suf in UNIT_BAD_SUFFIX:
        if name.endswith(suf):
            issues.append(("\u9519\u8bef", "\u6307\u6807\u540d %s \u4f7f\u7528\u4e86\u975e\u57fa\u672c\u5355\u4f4d\u540e\u7f00 %s\uff0c\u8bf7\u6362\u6210 _seconds / _bytes" % (name, suf)))
            break
    if typ == "counter" and not name.endswith("_total"):
        issues.append(("\u9519\u8bef", "Counter %s \u7f3a\u5c11 _total \u540e\u7f00" % name))
    if typ == "gauge" and name.endswith("_total"):
        issues.append(("\u9519\u8bef", "Gauge %s \u5e26\u4e86 _total \u540e\u7f00\uff0c_total \u662f Counter \u4e13\u7528" % name))
    if typ == "gauge" and name.endswith("_count"):
        issues.append(("\u63d0\u793a", "Gauge %s \u7528\u4e86 _count \u540e\u7f00\uff0c\u5bb9\u6613\u4e0e histogram \u7684 _count \u6df7\u6dc6" % name))
    for lbl in rec["labels"]:
        if lbl in RESERVED_LABELS and lbl not in ("le", "quantile"):
            issues.append(("\u8b66\u793a", "\u6307\u6807 %s \u4f7f\u7528\u4e86\u4fdd\u7559\u6807\u7b7e %s\uff08Prometheus \u4f1a\u81ea\u52a8\u9644\u52a0\uff09" % (name, lbl)))
        low = lbl.lower()
        if low in BLACKLIST_LABELS:
            issues.append(("\u4e25\u91cd", "\u6307\u6807 %s \u4f7f\u7528\u4e86\u9ad8\u57fa\u6570\u6807\u7b7e %s\uff1aseries \u6570\u4f1a\u968f\u53d6\u503c\u7ebf\u6027\u81a8\u80c0" % (name, lbl)))
    series = estimate_series(rec)
    if series > max_series:
        issues.append(("\u4e25\u91cd", "\u6307\u6807 %s \u4f30\u7b97 series \u6570 %d \u8d85\u8fc7\u9608\u503c %d" % (name, series, max_series)))
    if len(rec["labels"]) > 8:
        issues.append(("\u63d0\u793a", "\u6307\u6807 %s \u6709 %d \u4e2a\u6807\u7b7e\uff0c\u57fa\u6570\u662f\u6307\u6570\u5173\u7cfb\uff0c\u5efa\u8bae\u7cbe\u7b80" % (name, len(rec["labels"]))))
    return issues


def check_metrics_all(metrics, max_series):
    issues = {}
    for rec in metrics:
        its = check_metric(rec, max_series)
        if its:
            issues[rec["name"]] = its
    for rec in metrics:
        name = rec["name"]
        if rec["type"] != "histogram":
            continue
        for suf in ("_bucket", "_sum", "_count"):
            missing = True
            for other in metrics:
                if other["name"] == name + suf:
                    missing = False
                    break
            if missing:
                issues.setdefault(name, []).append(
                    ("\u9519\u8bef", "histogram %s \u7f3a\u5c11 %s \u4e09\u4ef6\u5957\u6210\u5458" % (name, suf)))
        for other in metrics:
            if other["name"] == name + "_bucket":
                has_inf = False
                for vals in other["labels"].get("le", set()):
                    if vals in ("+Inf", "Inf"):
                        has_inf = True
                if not has_inf:
                    issues.setdefault(other["name"], []).append(
                        ("\u9519\u8bef", "histogram %s \u7f3a\u5c11 le=+Inf \u6876\uff0chistogram_quantile \u65e0\u6cd5\u6b63\u786e\u8ba1\u7b97" % other["name"]))
                break
    return issues


def build_report(text, kind, scrape_interval, max_series):
    lines = []
    summary = {"kind": kind}
    lines.append("=" * 62)
    lines.append("Prometheus \u547d\u540d\u4e0e\u89c4\u5219\u4f53\u68c0\u62a5\u544a")
    lines.append("=" * 62)

    if kind == "rules":
        rules = parse_rules(text)
        summary["rules"] = []
        lines.append("")
        lines.append("[\u89e3\u6790] \u5171 %d \u6761\u89c4\u5219" % len(rules))
        total = 0
        for r in rules:
            name = r.get("alert") or r.get("record")
            issues = check_rule(r, scrape_interval)
            issues.sort(key=lambda x: LEVELS.index(x[0]) if x[0] in LEVELS else 9)
            total += len(issues)
            summary["rules"].append({"name": name, "type": r["type"],
                                     "for": r.get("for", ""),
                                     "issues": [{"level": a, "msg": b} for a, b in issues]})
            lines.append("")
            lines.append("[%s] %s  group=%s  for=%s" % (
                "alert" if r["type"] == "alert" else "record", name,
                r.get("group") or "-", r.get("for") or "-"))
            if not issues:
                lines.append("  [\u597d] \u672a\u53d1\u73b0\u5f62\u5f0f\u95ee\u9898")
            for lv, msg in issues:
                lines.append("  [%s] %s" % (lv, msg))
        summary["problems"] = total
        lines.append("")
        lines.append("\u95ee\u9898\u9879\u5408\u8ba1: %d" % total)
    else:
        metrics = parse_metrics(text)
        summary["metrics"] = len(metrics)
        lines.append("")
        lines.append("[\u89e3\u6790] \u5171 %d \u4e2a\u6307\u6807\uff0c%d \u4e2a\u6837\u672c" % (
            len(metrics), sum(m["samples"] for m in metrics)))
        iss = check_metrics_all(metrics, max_series)
        summary["issues"] = []
        problem_count = 0
        for rec in metrics:
            its = iss.get(rec["name"], [])
            its.sort(key=lambda x: LEVELS.index(x[0]) if x[0] in LEVELS else 9)
            problem_count += len(its)
            lines.append("")
            lines.append("[\u6307\u6807] %s  type=%s  labels=%d  \u4f30\u7b97series=%d" % (
                rec["name"], rec["type"] or "unknown", len(rec["labels"]),
                estimate_series(rec)))
            if not its:
                lines.append("  [\u597d] \u672a\u53d1\u73b0\u5f62\u5f0f\u95ee\u9898")
            for lv, msg in its:
                lines.append("  [%s] %s" % (lv, msg))
                summary["issues"].append({"metric": rec["name"], "level": lv, "msg": msg})
        summary["problems"] = problem_count
        lines.append("")
        lines.append("\u95ee\u9898\u9879\u5408\u8ba1: %d" % problem_count)

    lines.append("")
    lines.append("\u514d\u8d23: \u9759\u6001\u68c0\u67e5\u4e0d\u80fd\u66ff\u4ee3 promtool check rules\uff0c\u4e0a\u7ebf\u524d\u5fc5\u987b\u8dd1\u5b98\u65b9\u6821\u9a8c\u3002")
    lines.append("=" * 62)
    return "\n".join(lines), summary


RULES_SAMPLE = """groups:
  - name: service_availability
    rules:
      - alert: ServiceHighErrorRate
        expr: sum(rate(http_requests_total{code=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "{{ $labels.job }} 5xx \u9519\u8bef\u7387\u8d85\u8fc7 5%"
          description: "\u5f53\u524d {{ $value }}"
      - alert: InstanceMemoryGrow
        expr: rate(process_resident_memory_bytes[30s]) > 100000000
        for: 0m
        labels:
          team: backend
      - alert: InstanceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
      - record: job_requests_rate5m
        expr: sum(rate(http_requests_total[5m])) by (job)
      - record: job:http_requests_total:rate5m
        expr: sum(rate(http_requests_total[5m])) by (job)
      - record: cluster:http_requests_total:sum
        expr: sum(job:http_requests_total:rate5m) by (cluster)
"""

METRICS_SAMPLE = """# HELP httpRequestCount Total http requests
# TYPE httpRequestCount counter
httpRequestCount{method="GET",code="200"} 1234
httpRequestCount{method="POST",code="200"} 56
# HELP request_latency_ms Request latency
# TYPE request_latency_ms histogram
request_latency_ms_bucket{le="0.1"} 10
request_latency_ms_bucket{le="0.5"} 20
request_latency_ms_sum 3.4
request_latency_ms_count 20
# HELP api_duration_seconds Api duration
# TYPE api_duration_seconds histogram
api_duration_seconds_bucket{le="0.1"} 5
api_duration_seconds_bucket{le="+Inf"} 10
api_duration_seconds_sum 1.2
api_duration_seconds_count 10
# HELP http_requests_errors_total Errors
# TYPE http_requests_errors_total counter
http_requests_errors_total{user_id="1",path="/a"} 3
http_requests_errors_total{user_id="2",path="/b"} 4
http_requests_errors_total{user_id="3",path="/c"} 5
# HELP node_memory_size_mb Memory MB
# TYPE node_memory_size_mb gauge
node_memory_size_mb 4096
# HELP process_up_total Up flag
# TYPE process_up_total gauge
process_up_total 1
"""

HISTO_BAD_SAMPLE = """# TYPE broken_duration_seconds histogram
broken_duration_seconds_bucket{le="0.1"} 1
broken_duration_seconds_bucket{le="+Inf"} 2
broken_duration_seconds_sum 3
"""


def selftest():
    ck("5m \u5e94\u89e3\u6790\u4e3a 300 \u79d2", parse_duration("5m") == 300)
    ck("1m30s \u5e94\u89e3\u6790\u4e3a 90 \u79d2", parse_duration("1m30s") == 90)
    ck("2h \u5e94\u89e3\u6790\u4e3a 7200 \u79d2", parse_duration("2h") == 7200)

    seg = balanced_segment("abc(sum(x[5m])) by (job)", 0)
    ck("\u5e73\u8861\u7247\u6bb5\u5e94\u8986\u76d6\u6574\u4e2a\u8c03\u7528", seg.startswith("abc(sum(x[5m]))"))

    calls = find_calls("histogram_quantile(0.99, sum(rate(x_bucket[5m])) by (le, job))", "sum")
    ck("\u5e94\u627e\u5230 1 \u4e2a sum \u8c03\u7528", len(calls) == 1)
    ck("sum \u7247\u6bb5\u5e94\u8986\u76d6\u5230\u5185\u5c42\u8c03\u7528", calls[0].startswith("sum(rate(x_bucket[5m]))"))
    calls2 = find_calls("sum by (le, job) (rate(x_bucket[5m]))", "sum")
    ck("\u524d\u7f6e by \u5199\u6cd5\u4e5f\u5e94\u53d6\u5230\u7247\u6bb5", len(calls2) == 1 and " by " in calls2[0])

    rules = parse_rules(RULES_SAMPLE)
    ck("\u5e94\u89e3\u6790\u51fa 6 \u6761\u89c4\u5219", len(rules) == 6)
    by_rule = dict((r.get("alert") or r.get("record"), r) for r in rules)
    ck("ServiceHighErrorRate \u5e94\u4e3a alert", by_rule["ServiceHighErrorRate"]["type"] == "alert")
    ck("\u6700\u540e\u4e00\u6761\u5e94\u4e3a record", rules[-1]["type"] == "record")
    ck("\u5e94\u89e3\u6790\u5230 for=5m", by_rule["ServiceHighErrorRate"]["for"] == "5m")
    ck("\u5e94\u89e3\u6790\u5230 severity", by_rule["ServiceHighErrorRate"]["labels"].get("severity") == "critical")
    ck("\u5e94\u89e3\u6790\u5230 annotations.summary", "summary" in by_rule["ServiceHighErrorRate"]["annotations"])
    ck("\u5e94\u89e3\u6790\u5230 group \u540d", by_rule["ServiceHighErrorRate"]["group"] == "service_availability")
    ck("\u5e94\u89e3\u6790\u5230 expr \u5185\u5bb9", "http_requests_total" in by_rule["ServiceHighErrorRate"]["expr"])

    i1 = [b for _, b in check_rule(by_rule["ServiceHighErrorRate"], 15)]
    ck("\u6bd4\u503c\u544a\u8b66\u5e94\u63d0\u793a\u6700\u5c0f\u6837\u672c\u91cf", any("\u6700\u5c0f\u6837\u672c\u91cf" in x for x in i1))
    ck("\u9876\u5c42 sum \u65e0 by \u5e94\u5224\u6807\u91cf\u8fd4\u56de", any("\u77ac\u65f6\u5411\u91cf" in x for x in i1))
    i2 = [b for _, b in check_rule(by_rule["InstanceMemoryGrow"], 15)]
    ck("Gauge \u8bef\u7528 rate \u5e94\u5224\u9519\u8bef", any("Gauge" in x for x in i2))
    ck("\u7f3a for \u5e94\u88ab\u68c0\u51fa", any("for" in x for x in i2))
    ck("\u7f3a severity \u5e94\u5224\u9519\u8bef", any("severity" in x for x in i2))
    i3 = [b for _, b in check_rule(by_rule["InstanceDown"], 15)]
    ck("up==0 \u5e94\u5efa\u8bae\u8865 absent", any("absent" in x for x in i3))
    i4 = [b for _, b in check_rule(by_rule["job_requests_rate5m"], 15)]
    ck("record \u547d\u540d\u975e\u4e09\u6bb5\u5f0f\u5e94\u5224\u9519\u8bef", any("\u4e09\u6bb5\u5f0f" in x for x in i4))
    i5 = [b for _, b in check_rule(by_rule["cluster:http_requests_total:sum"], 15)]
    ck("record \u5e26 _total \u5e94\u8b66\u793a", any("_total" in x for x in i5))

    short = {"type": "alert", "alert": "X",
             "expr": "rate(http_requests_total[30s]) > 1", "for": "5m",
             "labels": {"severity": "warning"}, "annotations": {}}
    short_issues = [b for _, b in check_rule(short, 15)]
    ck("rate \u7a97\u53e3\u5e94\u5224\u8fc7\u77ed", any("4 \u500d\u6293\u53d6\u95f4\u9694" in x for x in short_issues))

    ir = {"type": "alert", "alert": "Y", "expr": "irate(http_requests_total[5m]) > 1",
          "for": "5m", "labels": {"severity": "warning"}, "annotations": {}}
    ir_issues = [b for _, b in check_rule(ir, 15)]
    ck("irate \u5e94\u88ab\u63d0\u793a\u6539\u7528 rate", any("irate" in x for x in ir_issues))

    badsum = {"type": "alert", "alert": "Z", "expr": "sum(rate(http_requests_total[5m])) > 1",
              "for": "5m", "labels": {"severity": "warning"}, "annotations": {}}
    bs = [b for _, b in check_rule(badsum, 15)]
    ck("sum \u65e0 by \u5e94\u8b66\u793a", any("by/without" in x for x in bs))

    badhq = {"type": "alert", "alert": "Q",
             "expr": "histogram_quantile(0.99, sum(rate(x_bucket[5m])) by (job)) > 1",
             "for": "5m", "labels": {"severity": "warning"}, "annotations": {}}
    bh = [b for _, b in check_rule(badhq, 15)]
    ck("histogram_quantile \u4e22 le \u5e94\u5224\u9519\u8bef", any("le" in x for x in bh))

    metrics = parse_metrics(METRICS_SAMPLE)
    names = [m["name"] for m in metrics]
    ck("\u5e94\u89e3\u6790\u81f3\u5c11 8 \u4e2a\u6307\u6807", len(metrics) >= 8)
    ck("\u5e94\u89e3\u6790\u5230\u76f4\u65b9\u56fe\u7684 _bucket \u6210\u5458", "api_duration_seconds_bucket" in names)
    ck("\u5e94\u4ece TYPE \u884c\u8bc6\u522b\u51fa histogram \u57fa\u7840\u540d", "request_latency_ms" in names)
    by_type = dict((m["name"], m["type"]) for m in metrics)
    ck("\u5e94\u8bc6\u522b histogram \u7c7b\u578b", by_type.get("request_latency_ms") == "histogram")
    ck("\u5e94\u8bc6\u522b counter \u7c7b\u578b", by_type.get("httpRequestCount") == "counter")
    ck("\u5e94\u8bc6\u522b gauge \u7c7b\u578b", by_type.get("node_memory_size_mb") == "gauge")

    by = dict((m["name"], m) for m in metrics)
    m_issue = [b for _, b in check_metric(by["httpRequestCount"], 10)]
    ck("\u9a7c\u5cf0\u6307\u6807\u540d\u5e94\u5224\u9519\u8bef", any("\u547d\u540d\u89c4\u5219" in x for x in m_issue))
    ck("Counter \u7f3a _total \u5e94\u5224\u9519\u8bef", any("_total" in x for x in m_issue))

    ms = [b for _, b in check_metric(by["request_latency_ms"], 10)]
    ck("\u6beb\u79d2\u540e\u7f00\u5e94\u5224\u9519\u8bef", any("\u57fa\u672c\u5355\u4f4d" in x for x in ms))

    mb = [b for _, b in check_metric(by["node_memory_size_mb"], 10)]
    ck("MB \u540e\u7f00\u5e94\u5224\u9519\u8bef", any("\u57fa\u672c\u5355\u4f4d" in x for x in mb))

    up = [b for _, b in check_metric(by["process_up_total"], 10)]
    ck("Gauge \u5e26 _total \u5e94\u5224\u9519\u8bef", any("Counter \u4e13\u7528" in x for x in up))

    err = [b for _, b in check_metric(by["http_requests_errors_total"], 10)]
    ck("\u9ad8\u57fa\u6570\u6807\u7b7e\u5e94\u5224\u4e25\u91cd", any("\u9ad8\u57fa\u6570\u6807\u7b7e" in x for x in err))

    all_issue = check_metrics_all(metrics, 10)
    bucket_txt = " ".join(b for _, b in all_issue.get("request_latency_ms_bucket", []))
    ck("\u7f3a +Inf \u6876\u5e94\u88ab\u68c0\u67e5\u5230", "Inf" in bucket_txt)
    ck("api_duration_seconds \u4e09\u4ef6\u5957\u9f50\u5168\u4e0d\u5e94\u62a5\u9519", "api_duration_seconds" not in all_issue)
    ck("series \u6570\u4f30\u7b97\u5e94\u6309\u7b1b\u5361\u5c14\u79ef", estimate_series(by["http_requests_errors_total"]) == 9)

    bad = parse_metrics(HISTO_BAD_SAMPLE)
    bad_issue = check_metrics_all(bad, 10)
    bad_txt = " ".join(b for _, b in bad_issue.get("broken_duration_seconds", []))
    ck("histogram \u7f3a _count \u6210\u5458\u5e94\u88ab\u68c0\u67e5\u5230", "_count" in bad_txt)

    _, sm = build_report(RULES_SAMPLE, "rules", 15, 10)
    ck("rules \u6a21\u5f0f\u5e94\u7edf\u8ba1\u95ee\u9898\u9879", sm.get("problems", 0) > 0)
    _, sm2 = build_report(METRICS_SAMPLE, "metrics", 15, 10)
    ck("metrics \u6a21\u5f0f\u5e94\u7edf\u8ba1\u95ee\u9898\u9879", sm2.get("problems", 0) > 0)
    return not FAILS


def main():
    ap = argparse.ArgumentParser(description="Prometheus \u6307\u6807\u547d\u540d\u4e0e\u544a\u8b66\u89c4\u5219\u68c0\u67e5")
    ap.add_argument("--kind", default="auto", choices=["auto", "metrics", "rules"])
    ap.add_argument("--file", help="\u5f85\u68c0\u67e5\u6587\u4ef6\uff1arule yaml \u6216 /metrics \u6587\u672c")
    ap.add_argument("--scrape-interval", type=int, default=15, help="\u6293\u53d6\u95f4\u9694\u79d2\u6570")
    ap.add_argument("--max-series", type=int, default=10000, help="\u5355\u6307\u6807 series \u544a\u8b66\u9608\u503c")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", help="\u7ed3\u679c\u5199\u5165\u6587\u4ef6")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    if args.selftest:
        ok = selftest()
        write_result(os.path.join(here, "_selftest_result.txt"))
        sys.exit(0 if ok else 1)

    if not args.file:
        ap.error("\u9700\u8981 --file \u6216 --selftest")

    text = io.open(args.file, "r", encoding="utf-8", errors="ignore").read()
    kind = args.kind
    if kind == "auto":
        kind = "rules" if re.search(r"^\s*-?\s*(alert|record):", text, re.M) else "metrics"

    report, summary = build_report(text, kind, args.scrape_interval, args.max_series)
    out_path = args.out or os.path.join(here, "_last_result.txt")
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else report
    io.open(out_path, "w", encoding="utf-8").write(body)
    print(body)
    print("")
    print("\u7ed3\u679c\u5df2\u5199\u5165: %s" % out_path)


if __name__ == "__main__":
    main()
