# -*- coding: utf-8 -*-
"""\u670d\u52a1\u5668\u65e5\u5e38\u5de1\u68c0\u9608\u503c\u5224\u5b9a\u4e0e\u5de1\u68c0\u8868\u751f\u6210\u3002

\u7528\u6cd5:
  python server_inspection_check.py --file collect.txt --role web --cores 4
  python server_inspection_check.py --file collect.txt --role db --out report.md
  python server_inspection_check.py --template
  python server_inspection_check.py --selftest
"""
import argparse
import datetime
import json
import os
import re
import sys

# ---- \u7b49\u7ea7\u5e38\u91cf ----
OK = "\u6b63\u5e38"
WARN = "\u5173\u6ce8"
ALERT = "\u544a\u8b66"
FAIL = "\u91c7\u96c6\u5931\u8d25"

# \u6307\u6807\u5b9a\u4e49: key, \u4e2d\u6587\u540d, \u5355\u4f4d, {\u89d2\u8272: (\u5173\u6ce8\u7ebf, \u544a\u8b66\u7ebf)}
# \u8bed\u4e49: \u9ed8\u8ba4\u300c\u8d8a\u5927\u8d8a\u5371\u9669\u300d\uff0cINVERT \u4e2d\u7684\u300c\u8d8a\u5c0f\u8d8a\u5371\u9669\u300d\uff0c
#       STRICT_WARN \u4e2d\u7684\u300c\u7b49\u4e8e\u5173\u6ce8\u7ebf\u4ecd\u7b97\u6b63\u5e38\u300d\uff08\u7528\u4e8e 0 \u5373\u6b63\u5e38\u7684\u8ba1\u6570\u9879\uff09
METRICS = [
    ("cpu_used", "CPU \u4f7f\u7528\u7387", "%", {
        "generic": (70, 85), "web": (70, 80), "db": (70, 85),
        "middleware": (70, 80), "batch": (999, 999)}),
    ("cpu_sys", "CPU \u7cfb\u7edf\u6001\u5360\u6bd4", "%", {
        "generic": (15, 25), "web": (15, 25), "db": (15, 25),
        "middleware": (15, 25), "batch": (999, 999)}),
    ("load_ratio", "load1 / \u6838\u6570", "", {
        "generic": (0.7, 1.0), "web": (0.7, 1.0), "db": (0.6, 0.9),
        "middleware": (0.7, 1.0), "batch": (2.0, 3.0)}),
    ("run_queue", "\u8fd0\u884c\u961f\u5217 r", "", {
        "generic": (2, 4), "web": (2, 4), "db": (2, 4),
        "middleware": (2, 4), "batch": (8, 16)}),
    ("block_queue", "\u963b\u585e\u961f\u5217 b", "", {
        "generic": (0, 3), "web": (0, 3), "db": (0, 2),
        "middleware": (0, 3), "batch": (2, 5)}),
    ("mem_available_pct", "\u5185\u5b58 available \u5360\u6bd4(\u8d8a\u9ad8\u8d8a\u5b89\u5168)", "%", {
        "generic": (25, 10), "web": (25, 15), "db": (20, 10),
        "middleware": (20, 15), "batch": (10, 5)}),
    ("swap_used_pct", "swap \u4f7f\u7528\u7387", "%", {
        "generic": (0.1, 30), "web": (0.1, 30), "db": (0.1, 20),
        "middleware": (0.1, 20), "batch": (5, 30)}),
    ("swap_io_kbs", "swap in/out \u901f\u7387", "KB/s", {
        "generic": (1, 100), "web": (1, 100), "db": (1, 50),
        "middleware": (1, 50), "batch": (10, 200)}),
    ("oom_count", "24h OOM \u6b21\u6570", "\u6b21", {
        "generic": (0.1, 0.5), "web": (0.1, 0.5), "db": (0.1, 0.5),
        "middleware": (0.1, 0.5), "batch": (0.1, 0.5)}),
    ("disk_used_pct", "\u78c1\u76d8\u5206\u533a\u4f7f\u7528\u7387", "%", {
        "generic": (70, 85), "web": (70, 85), "db": (70, 80),
        "middleware": (70, 80), "batch": (70, 80)}),
    ("inode_used_pct", "inode \u4f7f\u7528\u7387", "%", {
        "generic": (60, 80), "web": (60, 80), "db": (50, 75),
        "middleware": (50, 75), "batch": (60, 80)}),
    ("io_await_ms", "\u78c1\u76d8 IO await", "ms", {
        "generic": (10, 30), "web": (10, 30), "db": (8, 20),
        "middleware": (8, 20), "batch": (20, 50)}),
    ("io_util_pct", "\u78c1\u76d8 %util", "%", {
        "generic": (70, 90), "web": (70, 90), "db": (70, 85),
        "middleware": (70, 85), "batch": (90, 98)}),
    ("tcp_established", "ESTABLISHED \u8fde\u63a5\u6570", "", {
        "generic": (5000, 10000), "web": (5000, 10000), "db": (2000, 6000),
        "middleware": (3000, 8000), "batch": (1000, 3000)}),
    ("tcp_timewait", "TIME-WAIT \u8fde\u63a5\u6570", "", {
        "generic": (2000, 5000), "web": (3000, 8000), "db": (1000, 3000),
        "middleware": (2000, 5000), "batch": (5000, 10000)}),
    ("nic_dropped", "\u7f51\u5361 dropped(\u6bcf\u5206\u949f)", "\u4e2a", {
        "generic": (0.1, 0.5), "web": (0.1, 0.5), "db": (0.1, 0.5),
        "middleware": (0.1, 0.5), "batch": (10, 200)}),
    ("clock_skew_s", "\u65f6\u949f\u504f\u79fb", "\u79d2", {
        "generic": (1, 120), "web": (1, 120), "db": (1, 60),
        "middleware": (1, 60), "batch": (5, 180)}),
    ("err_count_24h", "24h ERROR \u65e5\u5fd7\u6761\u6570", "\u6761", {
        "generic": (20, 100), "web": (20, 100), "db": (10, 50),
        "middleware": (10, 50), "batch": (50, 200)}),
    ("failed_units", "\u5931\u8d25\u7684 systemd \u5355\u5143", "\u4e2a", {
        "generic": (0.1, 0.5), "web": (0.1, 0.5), "db": (0.1, 0.5),
        "middleware": (0.1, 0.5), "batch": (0.1, 0.5)}),
    ("critical_hits", "\u81f4\u547d\u5173\u952e\u5b57\u547d\u4e2d(OOM/IO error/segfault)", "\u6761", {
        "generic": (0.1, 0.5), "web": (0.1, 0.5), "db": (0.1, 0.5),
        "middleware": (0.1, 0.5), "batch": (0.1, 0.5)}),
]

INVERT = ("mem_available_pct",)
STRICT_WARN = ("run_queue", "block_queue")

METRIC_BY_KEY = dict((m[0], m) for m in METRICS)

ALIAS_RAW = {
    "cpu": "cpu_used", "cpu_used": "cpu_used", "cpu\u4f7f\u7528\u7387": "cpu_used",
    "cpu_util": "cpu_used", "cpu\u4f7f\u7528": "cpu_used",
    "cpu_sys": "cpu_sys", "\u7cfb\u7edf\u6001": "cpu_sys",
    "load": "load_ratio", "load_ratio": "load_ratio", "load1": "load_ratio",
    "loadavg": "load_ratio", "\u8d1f\u8f7d": "load_ratio",
    "r": "run_queue", "run_queue": "run_queue",
    "b": "block_queue", "block_queue": "block_queue",
    "mem": "mem_available_pct", "mem_available_pct": "mem_available_pct",
    "mem_available": "mem_available_pct", "memory": "mem_available_pct",
    "\u5185\u5b58": "mem_available_pct",
    "swap": "swap_used_pct", "swap_used_pct": "swap_used_pct",
    "swapio": "swap_io_kbs", "swap_io_kbs": "swap_io_kbs",
    "swap_io": "swap_io_kbs",
    "oom": "oom_count", "oom_count": "oom_count",
    "disk": "disk_used_pct", "disk_used_pct": "disk_used_pct",
    "df": "disk_used_pct",
    "inode": "inode_used_pct", "inode_used_pct": "inode_used_pct",
    "await": "io_await_ms", "io_await_ms": "io_await_ms", "iowait": "io_await_ms",
    "util": "io_util_pct", "io_util_pct": "io_util_pct",
    "established": "tcp_established", "tcp_established": "tcp_established",
    "estab": "tcp_established",
    "timewait": "tcp_timewait", "tcp_timewait": "tcp_timewait",
    "dropped": "nic_dropped", "nic_dropped": "nic_dropped",
    "skew": "clock_skew_s", "clock_skew_s": "clock_skew_s",
    "clock": "clock_skew_s", "ntp": "clock_skew_s",
    "err": "err_count_24h", "err_count_24h": "err_count_24h",
    "error": "err_count_24h",
    "failed": "failed_units", "failed_units": "failed_units",
    "critical": "critical_hits", "critical_hits": "critical_hits",
}


def norm_key(s):
    return (s or "").strip().lower().replace(" ", "").replace("_", "")


ALIAS = dict((norm_key(k), v) for k, v in ALIAS_RAW.items())
METRIC_NORM = dict((norm_key(m[0]), m[0]) for m in METRICS)

FATAL_PATTERN = re.compile(
    r"I/O error|EXT4-fs error|XFS metadata corruption|lost page|"
    r"kernel panic|Out of memory|Reallocated_Sector_Ct|"
    r"SMART.*Failed|Array.*degrad", re.I)

ROLES = ("generic", "web", "db", "middleware", "batch")

BAD_TOKENS = ("na", "n/a", "-", "--", "fail", "failed", "error", "none",
              "null", "?", "x", "\u65e0", "\u672a\u91c7", "\u672a\u91c7\u96c6", "\u7a7a", "\u672a\u83b7\u53d6", "\u6743\u9650\u4e0d\u8db3")


def resolve_key(raw):
    k = norm_key(raw)
    if k in ALIAS:
        return ALIAS[k]
    return METRIC_NORM.get(k)


def to_float(v):
    v = (v or "").strip().replace("%", "").replace(",", "")
    m = re.match(r"^(-?\d+(?:\.\d+)?)", v)
    return float(m.group(1)) if m else None


def parse_collect(text):
    """\u89e3\u6790\u91c7\u96c6\u6587\u4ef6\uff0c\u8fd4\u56de [(key, float|None, \u663e\u793a\u540d, \u5907\u6ce8)]\uff1bvalue \u4e3a None \u8868\u793a\u91c7\u96c6\u5931\u8d25\u3002"""
    out = []
    seen = set()
    for ln in (text or "").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or ln.startswith("//"):
            continue
        parts = re.split(r"[|\t,;=]", ln, maxsplit=1)
        if len(parts) < 2:
            out.append((None, None, parts[0].strip(),
                        "\u683c\u5f0f\u4e0d\u5b8c\u6574: \u7f3a\u5c11\u6570\u503c\u5217\uff08\u5e94\u4e3a \u6307\u6807|\u6570\u503c\uff09"))
            continue
        raw_name = parts[0].strip()
        raw_val = parts[1].strip()
        note = ""
        if raw_val.lower() in BAD_TOKENS or raw_val in BAD_TOKENS:
            val = None
            note = "\u91c7\u96c6\u5931\u8d25: \u539f\u59cb\u503c\u4e3a\u300c%s\u300d" % (raw_val if raw_val else "\u7a7a")
        else:
            val = to_float(raw_val)
            if val is None:
                note = "\u91c7\u96c6\u5931\u8d25: \u65e0\u6cd5\u4ece\u300c%s\u300d\u89e3\u6790\u51fa\u6570\u503c" % raw_val
        key = resolve_key(raw_name)
        if key is None:
            out.append((None, val, raw_name,
                        note if val is None
                        else "\u672a\u77e5\u6307\u6807\u540d\uff0c\u672a\u53c2\u4e0e\u9608\u503c\u5224\u5b9a\uff08\u8bf7\u6838\u5bf9\u522b\u540d\u8868\uff09"))
            continue
        if key in seen:
            out.append((None, val, METRIC_BY_KEY[key][1],
                        "\u6307\u6807\u300c%s\u300d\u91cd\u590d\u51fa\u73b0\uff0c\u4ee5\u9996\u6b21\u91c7\u96c6\u503c\u4e3a\u51c6" % METRIC_BY_KEY[key][1]))
            continue
        seen.add(key)
        out.append((key, val, METRIC_BY_KEY[key][1], note))
    return out


def grade(key, val, role):
    """\u8fd4\u56de (\u7b49\u7ea7, \u8bf4\u660e)\u3002"""
    m = METRIC_BY_KEY.get(key)
    if not m:
        return None, ""
    cn, unit, roles = m[1], m[2], m[3]
    warn_at, alert_at = roles.get(role) or roles["generic"]
    if key in INVERT:
        if val >= warn_at:
            return OK, "%.1f%s \u4e0d\u4f4e\u4e8e\u6b63\u5e38\u7ebf %.0f" % (val, unit, warn_at)
        if val < alert_at:
            return ALERT, "%.1f%s \u4f4e\u4e8e\u544a\u8b66\u7ebf %.0f" % (val, unit, alert_at)
        return WARN, "%.1f%s \u4ecb\u4e8e\u544a\u8b66\u7ebf %.0f \u4e0e\u6b63\u5e38\u7ebf %.0f" % (val, unit, alert_at, warn_at)
    hit_warn = val > warn_at if key in STRICT_WARN else val >= warn_at
    if val > alert_at:
        return ALERT, "%.2f%s \u8d85\u8fc7\u544a\u8b66\u7ebf %.0f" % (val, unit, alert_at)
    if hit_warn:
        return WARN, "%.2f%s \u8fbe\u5230\u5173\u6ce8\u7ebf %.0f" % (val, unit, warn_at)
    return OK, "%.2f%s \u4f4e\u4e8e\u5173\u6ce8\u7ebf %.0f" % (val, unit, warn_at)


DISPOSAL = {
    "cpu_used": "mpstat -P ALL 1 3 \u5224\u65ad\u5355\u6838\u8fd8\u662f\u6574\u4f53\uff1btop -H -p <pid> \u770b\u7ebf\u7a0b",
    "cpu_sys": "\u67e5\u4e2d\u65ad\u4e0e\u4e0a\u4e0b\u6587\u5207\u6362\uff1avmstat 1 5 \u770b in/cs \u5217",
    "load_ratio": "vmstat 1 5 \u770b b \u5217\uff1bb>0 \u67e5\u78c1\u76d8 await \u4e0e NFS \u6302\u8f7d",
    "run_queue": "ps -eo stat,pid,comm | awk '$1 ~ /D/' \u627e\u4e0d\u53ef\u4e2d\u65ad\u8fdb\u7a0b",
    "block_queue": "iostat -x 1 3 \u770b await\uff1b\u67e5 NFS\u3001\u8fdc\u7aef\u5b58\u50a8\u4e0e\u961f\u5217\u6df1\u5ea6",
    "mem_available_pct": "ps -eo pid,rss,comm --sort=-rss | head -20 \u6309 RSS \u627e\u6cc4\u6f0f",
    "swap_used_pct": "smem -s swap -r \u627e\u5403 swap \u7684\u8fdb\u7a0b\uff1b\u7d2f\u8ba1\u503c\u9ad8\u4e0d\u4ee3\u8868\u5f53\u524d\u6709\u538b\u529b",
    "swap_io_kbs": "vmstat 1 5 \u770b si/so \u901f\u7387\uff1b\u6301\u7eed\u6296\u52a8\u9700\u964d\u5e76\u53d1\u6216\u52a0\u5185\u5b58",
    "oom_count": "journalctl -k | grep -i 'killed process' \u8bb0\u5f55\u8fdb\u7a0b\u540d\u4e0e cgroup",
    "disk_used_pct": "du -xh --max-depth=1 / | sort -h | tail\uff1bfind / -xdev -size +500M",
    "inode_used_pct": "\u5206\u76ee\u5f55\u7edf\u8ba1\u6587\u4ef6\u6570\u5b9a\u4f4d\u5c0f\u6587\u4ef6\u5806\u79ef\u70b9\uff0c\u518d\u5b9a\u4fdd\u7559\u7b56\u7565",
    "io_await_ms": "iostat -x 1 3\uff1bawait \u9ad8\u800c util \u4e0d\u9ad8\u65f6\uff0c\u8c03\u5927\u961f\u5217\u6df1\u5ea6\u5f80\u5f80\u66f4\u6709\u6548",
    "io_util_pct": "\u8bbe\u5907\u5df2\u9971\u548c\uff0c\u5148\u786e\u8ba4\u662f\u5426\u53ef\u5f52\u6863\u6216\u51b7\u6570\u636e\u4e0b\u6c89",
    "tcp_established": "ss -tan | awk '{print $5}' | sort | uniq -c | sort -rn | head",
    "tcp_timewait": "\u68c0\u67e5\u5ba2\u6237\u7aef\u662f\u5426\u672a\u590d\u7528\u8fde\u63a5\uff1b\u670d\u52a1\u7aef\u8003\u8651 tcp_tw_reuse",
    "nic_dropped": "\u5e94\u7528\u6536\u5305\u6162\u4e8e\u5185\u6838\u7f13\u51b2\uff0c\u67e5 GC \u505c\u987f\u4e0e\u7f51\u5361\u961f\u5217\u957f\u5ea6",
    "clock_skew_s": "chronyc sources -v \u68c0\u67e5\u6e90\u53ef\u8fbe\u6027\uff1b\u5bb9\u5668\u5185\u68c0\u67e5 TZ \u4e0e\u5bbf\u4e3b\u673a\u4e00\u81f4",
    "err_count_24h": "journalctl -p err --since -24h \u6309 unit \u805a\u5408\uff0c\u540c\u6e90\u591a\u6761\u4e0d\u7b49\u4e8e\u591a\u4e2a\u95ee\u9898",
    "failed_units": "systemctl --failed \u540e journalctl -u <unit> -n 100 \u770b\u539f\u56e0",
    "critical_hits": "\u8f6c\u5b58\u50a8/\u5185\u6838\u5904\u7406\uff1b\u5148\u5907\u4efd\uff0c\u7981\u6b62\u5728\u7ebf fsck",
}


def build_items(text, role):
    out = []
    for key, val, name, note in parse_collect(text):
        if key is None:
            out.append({"key": None, "name": name, "value": val,
                        "grade": FAIL if val is None else OK, "note": note})
            continue
        if val is None:
            out.append({"key": key, "name": name, "value": None,
                        "grade": FAIL, "note": note})
            continue
        g, why = grade(key, val, role)
        it = {"key": key, "name": name, "value": val, "grade": g, "note": why}
        if g in (WARN, ALERT) and key in DISPOSAL:
            it["disposal"] = DISPOSAL[key]
        out.append(it)
    return out


def check_combos(items, role):
    got = dict((i["key"], i["value"]) for i in items
               if i.get("key") and i.get("value") is not None)
    outs = []

    load = got.get("load_ratio")
    cpu = got.get("cpu_used")
    blk = got.get("block_queue")
    util = got.get("io_util_pct")
    if load is not None and cpu is not None and load >= 1.0 and cpu < 50:
        tag = "\u8d1f\u8f7d\u9ad8\u4f46 CPU \u4f4e\uff08load \u6bd4\u503c %.2f\uff0cCPU \u4ec5 %.1f%%\uff09" % (load, cpu)
        if blk is not None and blk > 0:
            tag += "\uff0c\u4e14\u963b\u585e\u961f\u5217 b=%d \u5927\u4e8e 0" % blk
        if util is not None and util >= 90:
            tag += "\uff0c%%util=%.0f" % util
        outs.append((tag + "\uff1a\u74f6\u9888\u4e0d\u5728 CPU\uff0c\u4f18\u5148\u67e5\u78c1\u76d8 IO / NFS / \u7f51\u7edc\u9a71\u52a8\uff0c"
                     "\u5148\u52a0 CPU \u662f\u9519\u7684\u65b9\u5411\u3002", ALERT))
    elif load is not None and cpu is not None and load >= 1.0 and cpu >= 85:
        outs.append(("\u8d1f\u8f7d\u9ad8\uff08%.2f\uff09\u4e14 CPU \u9ad8\uff08%.1f%%\uff09\uff1a\u5c5e CPU \u74f6\u9888\uff0c"
                     "\u627e Top \u8fdb\u7a0b\u4e0e\u706b\u7130\u56fe\u3002" % (load, cpu), WARN))

    mem = got.get("mem_available_pct")
    swap = got.get("swap_used_pct")
    sio = got.get("swap_io_kbs")
    if (mem is not None and swap is not None and swap >= 30
            and sio is not None and sio >= 100):
        outs.append(("swap \u5df2\u7528 %.0f%% \u4e14\u6362\u9875\u901f\u7387 %.0f KB/s\uff1a\u6b63\u5728\u6362\u9875\u6296\u52a8\uff0c"
                     "\u5373\u4f7f CPU \u5f88\u7a7a\uff0c\u5ef6\u8fdf\u4e5f\u4f1a\u663e\u8457\u4e0a\u5347\u3002" % (swap, sio), ALERT))
    elif mem is not None and mem < 15 and swap is not None and swap == 0:
        outs.append(("\u5185\u5b58 available \u504f\u4f4e\u4f46 swap \u672a\u4f7f\u7528\uff1a\u4f18\u5148\u67e5\u5185\u5b58\u6cc4\u6f0f\u6216\u8fdb\u7a0b\u4e0a\u9650\uff0c"
                     "\u4e0d\u8981\u56e0 swap \u4e3a 0 \u5c31\u5224\u5b9a\u5185\u5b58\u6b63\u5e38\u3002", WARN))

    disk = got.get("disk_used_pct")
    inode = got.get("inode_used_pct")
    if disk is not None and inode is not None and disk < 70 and inode >= 80:
        outs.append(("\u78c1\u76d8\u5bb9\u91cf\u4ec5 %.0f%% \u4f46 inode \u5df2 %.0f%%\uff1a\u5bb9\u91cf\u6ca1\u6ee1\u5374\u5199\u4e0d\u8fdb\uff0c"
                     "\u5178\u578b\u5c0f\u6587\u4ef6\u8fc7\u591a\uff0c\u62a5\u9519\u5e38\u663e\u793a\u4e3a No space left on device\u3002"
                     % (disk, inode), ALERT))
    if disk is not None and disk >= 90:
        outs.append(("\u78c1\u76d8 %.0f%% \u5df2\u8fbe 90%%\uff1a\u5fc5\u987b\u5f53\u65e5\u5904\u7406\u3002\u5148\u5b9a\u4f4d\u5927\u6587\u4ef6\u4e0e\u53ef\u5220\u76ee\u5f55\uff0c"
                     "\u4e0d\u8981\u76f4\u63a5\u5220 /var/log \u4e0b\u7684\u6587\u4ef6\u3002" % disk, ALERT))

    fail_n = len([1 for i in items
                  if i.get("grade") == FAIL])
    if fail_n:
        outs.append(("\u5b58\u5728 %d \u9879\u91c7\u96c6\u5931\u8d25\uff1a\u91c7\u96c6\u5931\u8d25\u4e0d\u7b49\u4e8e\u6b63\u5e38\uff0c\u5fc5\u987b\u8865\u91c7\u540e\u518d\u5224\uff0c"
                     "\u4e0d\u80fd\u586b 0 \u5145\u6570\u3002" % fail_n, WARN))

    skew = got.get("clock_skew_s")
    if skew is not None and skew > 120:
        outs.append(("\u65f6\u949f\u504f\u79fb %.0f \u79d2\u8d85\u8fc7 120\uff1a\u6240\u6709\u65e5\u5fd7\u65f6\u95f4\u7ebf\u4e0d\u53ef\u4fe1\uff0c"
                     "\u5fc5\u987b\u5148\u4fee NTP \u518d\u505a\u8de8\u4e3b\u673a\u65e5\u5fd7\u5206\u6790\u3002" % skew, ALERT))

    crit = got.get("critical_hits")
    if crit is not None and crit >= 1:
        outs.append(("\u81f4\u547d\u5173\u952e\u5b57\u547d\u4e2d %d \u6761\uff1a\u8f6c\u5b58\u50a8/\u5185\u6838\u6392\u67e5\uff0c"
                     "\u4e0d\u8981\u5728\u7ebf fsck \u6216\u91cd\u542f\u4e86\u4e8b\u3002" % crit, ALERT))

    oom = got.get("oom_count")
    if oom is not None and oom >= 1:
        outs.append(("24h \u5185\u53d1\u751f %d \u6b21 OOM\uff1a\u5fc5\u987b\u5728\u65e5\u5fd7\u4e2d\u5b9a\u4f4d\u88ab kill \u7684\u8fdb\u7a0b\u540d\u4e0e cgroup\uff0c"
                     "\u8fd9\u662f OOM \u5b9a\u6027\u7684\u5173\u952e\u3002" % oom, ALERT))

    fu = got.get("failed_units")
    if fu is not None and fu >= 1:
        outs.append(("\u6709 %d \u4e2a\u5931\u8d25\u7684 systemd \u5355\u5143\uff1a\u786e\u8ba4\u662f\u5426\u5173\u952e\u670d\u52a1\uff0c"
                     "\u5173\u952e\u670d\u52a1\u5931\u8d25\u6309\u4e8b\u6545\u5904\u7406\u3002" % fu, WARN))

    td = got.get("tcp_timewait")
    est = got.get("tcp_established")
    if td is not None and est is not None and est > 0 and td > est:
        outs.append(("TIME-WAIT(%.0f) \u591a\u4e8e ESTABLISHED(%.0f)\uff1a\u5178\u578b\u77ed\u8fde\u63a5\u9ad8\u9891\u6216"
                     "\u672a\u4f7f\u7528\u8fde\u63a5\u6c60\uff0c\u4e0d\u662f\u8fde\u63a5\u6cc4\u6f0f\u3002" % (td, est), WARN))
    return outs


def scan_fatal(text):
    hits = []
    for i, ln in enumerate((text or "").splitlines(), 1):
        if FATAL_PATTERN.search(ln):
            hits.append((i, ln.strip()[:160]))
    return hits


def render_md(items, combos, fatals, role, as_of, cores):
    cnt = {}
    for it in items:
        cnt[it["grade"]] = cnt.get(it["grade"], 0) + 1
    L = []
    L.append("# \u670d\u52a1\u5668\u5de1\u68c0\u5224\u5b9a\u62a5\u544a")
    L.append("")
    L.append("- \u5de1\u68c0\u65e5\u671f: %s" % as_of.isoformat())
    L.append("- \u89d2\u8272\u53e3\u5f84: %s\uff08\u6838\u6570 %s\uff09" % (role, cores))
    L.append("- \u7edf\u8ba1: \u6b63\u5e38 %d / \u5173\u6ce8 %d / \u544a\u8b66 %d / \u91c7\u96c6\u5931\u8d25 %d"
             % (cnt.get(OK, 0), cnt.get(WARN, 0),
                cnt.get(ALERT, 0), cnt.get(FAIL, 0)))
    L.append("")
    if fatals:
        L.append("## \u81f4\u547d\u9879\uff08\u7acb\u5373\u8f6c\u4e13\u4e1a\u5904\u7406\uff09")
        L.append("")
        for i, ln in fatals:
            L.append("- \u7b2c %d \u884c: %s" % (i, ln))
        L.append("")
    L.append("## \u9010\u9879\u5224\u5b9a")
    L.append("")
    L.append("| \u6307\u6807 | \u5b9e\u6d4b | \u5224\u5b9a | \u4f9d\u636e / \u8bf4\u660e | \u5904\u7f6e\u52a8\u4f5c |")
    L.append("|---|---|---|---|---|")
    for it in items:
        v = "-" if it["value"] is None else ("%.2f" % it["value"])
        L.append("| %s | %s | %s | %s | %s |"
                 % (it["name"], v, it["grade"], it["note"],
                    it.get("disposal", "")))
    L.append("")
    if combos:
        L.append("## \u7ec4\u5408\u578b\u5f02\u5e38\uff08\u5355\u9879\u770b\u8d77\u6765\u90fd\u6b63\u5e38\u65f6\u4e5f\u8981\u770b\u8fd9\u91cc\uff09")
        L.append("")
        for txt, g in combos:
            L.append("- **[%s]** %s" % (g, txt))
        L.append("")
    L.append("## \u5fc5\u505a\u7684\u4eba\u5de5\u786e\u8ba4")
    L.append("")
    for t in ("\u6bcf\u9879\u662f\u771f\u7684\u91c7\u5230\u4e86\u5417\uff1f\u91c7\u96c6\u5931\u8d25\u9879\u4e0d\u80fd\u586b 0 \u5145\u6570",
              "\u5185\u5b58\u770b\u7684\u662f available \u800c\u4e0d\u662f free",
              "\u78c1\u76d8\u662f\u5426\u540c\u65f6\u67e5\u4e86 df -i",
              "load \u9ad8\u65f6 vmstat \u7684 b \u5217\u662f\u5426\u4e3a 0",
              "\u544a\u8b66\u9879\u662f\u5426\u5199\u4e86\u300c\u52a8\u4f5c + \u9a8c\u8bc1\u7ed3\u679c\u300d",
              "\u65f6\u949f\u504f\u79fb\u8d85\u8fc7 120 \u79d2\u65f6\u662f\u5426\u5148\u4fee NTP",
              "\u5408\u89c4\u9879\uff08\u7279\u6743\u8d26\u53f7 / \u53e3\u4ee4\u57fa\u7ebf / \u8fdc\u7a0b\u63a5\u5165 / \u8ba1\u5212\u4efb\u52a1 / \u5f00\u653e\u7aef\u53e3\uff09\u662f\u5426\u9010\u6761\u5bf9\u7167\u8fc7\u53f0\u8d26"):
        L.append("- [ ] %s" % t)
    L.append("")
    L.append("---")
    L.append("")
    L.append("> \u9608\u503c\u4e3a\u901a\u7528\u8d77\u70b9\u3002\u540c\u4e00\u53f0\u673a\u5668\u51cc\u6668 3 \u70b9\u7684 30 \u767e\u5206\u6bd4 CPU \u6b63\u5e38\u3001"
             "\u65e9\u4e0a 9 \u70b9\u7684 30 \u767e\u5206\u6bd4\u5f02\u5e38\uff0c\u7edd\u5bf9\u9608\u503c\u53ea\u9002\u5408\u515c\u5e95\uff0c")
    L.append("> \u544a\u8b66\u6700\u7ec8\u5e94\u57fa\u4e8e\u540c\u673a\u540c\u65f6\u6bb5\u7684\u57fa\u7ebf\u3002")
    return "\n".join(L) + "\n"


def render_json(items, combos, fatals, role, as_of, cores):
    cnt = {}
    for it in items:
        cnt[it["grade"]] = cnt.get(it["grade"], 0) + 1
    return json.dumps({
        "as_of": as_of.isoformat(),
        "role": role,
        "cores": cores,
        "counts": cnt,
        "items": items,
        "combos": [{"text": t, "grade": g} for t, g in combos],
        "fatals": [{"line": i, "text": s} for i, s in fatals],
    }, ensure_ascii=False, indent=2)


CHECKLIST_TEMPLATE = """# \u670d\u52a1\u5668\u65e5\u5e38\u5de1\u68c0\u8bb0\u5f55\u8868

- \u4e3b\u673a\u540d: ____________  IP: ____________  \u89d2\u8272: ____________
- \u7cfb\u7edf\u4e0e\u5185\u6838: ____________  \u6838\u6570/\u5185\u5b58: ____________
- \u5de1\u68c0\u4eba: ____________  \u65f6\u95f4: 2026-__-__ __:__\uff08\u65f6\u533a ____\uff09
- \u5224\u5b9a\u53e3\u5f84: \u6b63\u5e38 / \u5173\u6ce8 / \u544a\u8b66 / \u91c7\u96c6\u5931\u8d25\uff08\u56db\u9009\u4e00\uff0c\u4e0d\u7559\u7a7a\uff09

## \u4e00 \u6027\u80fd\u4e0e\u5bb9\u91cf

| # | \u5de1\u68c0\u9879 | \u91c7\u96c6\u547d\u4ee4 | \u5b9e\u6d4b\u503c | \u5224\u5b9a | \u8bc1\u636e | \u5904\u7f6e\u52a8\u4f5c/\u8d23\u4efb\u4eba |
|---|---|---|---|---|---|---|
| 1 | CPU \u4f7f\u7528\u7387 | top -bn1 | | | | |
| 2 | load1/\u6838\u6570 | cat /proc/loadavg | | | | |
| 3 | \u963b\u585e\u961f\u5217 b | vmstat 1 5 | | | | |
| 4 | \u5185\u5b58 available | free -m | | | | |
| 5 | swap \u4f7f\u7528\u7387 | free -m | | | | |
| 6 | \u78c1\u76d8\u4f7f\u7528\u7387 | df -h | | | | |
| 7 | inode \u4f7f\u7528\u7387 | df -i | | | | |
| 8 | IO await \u4e0e %util | iostat -x 1 3 | | | | |
| 9 | ESTABLISHED \u4e0e TIME-WAIT | ss -s | | | | |
| 10 | \u7f51\u5361 errors \u4e0e dropped | ip -s link show eth0 | | | | |

## \u4e8c \u670d\u52a1\u4e0e\u65e5\u5fd7

| # | \u5de1\u68c0\u9879 | \u91c7\u96c6\u547d\u4ee4 | \u5b9e\u6d4b\u503c | \u5224\u5b9a | \u8bc1\u636e | \u5904\u7f6e\u52a8\u4f5c/\u8d23\u4efb\u4eba |
|---|---|---|---|---|---|---|
| 11 | \u5931\u8d25\u7684 systemd \u5355\u5143 | systemctl --failed | | | | |
| 12 | 24h ERROR \u6761\u6570\uff08\u6309\u6765\u6e90\u805a\u5408\uff09 | journalctl -p err | | | | |
| 13 | \u81f4\u547d\u5173\u952e\u5b57\u626b\u63cf | grep -iE \u81f4\u547d\u5173\u952e\u5b57 | | | | |
| 14 | \u8ba1\u5212\u4efb\u52a1\u6267\u884c\u7ed3\u679c | journalctl -u crond | | | | |

## \u4e09 \u65f6\u95f4\u4e0e\u5408\u89c4

| # | \u6838\u5bf9\u9879 | \u5bf9\u7167\u53f0\u8d26 | \u5b9e\u6d4b\u503c | \u5224\u5b9a | \u8bc1\u636e | \u5904\u7f6e\u52a8\u4f5c/\u8d23\u4efb\u4eba |
|---|---|---|---|---|---|---|
| 15 | NTP \u540c\u6b65\u72b6\u6001 | timedatectl | | | | |
| 16 | \u65f6\u949f\u504f\u79fb | chronyc tracking | | | | |
| 17 | \u7279\u6743\u8d26\u53f7\u6e05\u5355 | \u7279\u6743\u8d26\u53f7\u6388\u6743\u53f0\u8d26 | | | | |
| 18 | \u8d26\u53f7\u53e3\u4ee4\u7b56\u7565 | \u53e3\u4ee4\u57fa\u7ebf\u6587\u6863 | | | | |
| 19 | \u8fdc\u7a0b\u63a5\u5165\u7b56\u7565 | \u8fdc\u7a0b\u63a5\u5165\u57fa\u7ebf\u6587\u6863 | | | | |
| 20 | \u8fd1\u671f\u767b\u5f55\u8bb0\u5f55 | \u6388\u6743\u6765\u6e90\u5730\u4e0e\u8d26\u53f7\u6e05\u5355 | | | | |
| 21 | \u8ba1\u5212\u4efb\u52a1\u6e05\u5355 | \u53d8\u66f4\u5355 / \u53d1\u5e03\u8bb0\u5f55 | | | | |
| 22 | \u5bf9\u5916\u76d1\u542c\u7aef\u53e3 | \u5f00\u653e\u7aef\u53e3\u53f0\u8d26 | | | | |

> 17-22 \u6838\u5bf9\u7684\u662f\u300c\u73b0\u72b6 == \u53f0\u8d26\u300d\uff0c\u53d1\u73b0\u5dee\u5f02\u4e0d\u8d70\u5206\u7ea7\uff0c\u76f4\u63a5\u8f6c\u5b89\u5168\u4e8b\u4ef6\u6d41\u7a0b\uff1b
> \u8d26\u53f7\u4e0e\u63a5\u5165\u7b56\u7565\u7684\u5b9e\u9645\u53d8\u66f4\u7edf\u4e00\u8d70\u65e2\u6709\u5ba1\u6279\u6d41\u7a0b\uff0c\u5de1\u68c0\u73af\u8282\u53ea\u6838\u5bf9\u3001\u4e0d\u53d8\u66f4\u3002

## \u56db \u5907\u4efd\u4e0e\u6062\u590d

| # | \u5de1\u68c0\u9879 | \u5b9e\u6d4b\u503c | \u5224\u5b9a | \u8bf4\u660e |
|---|---|---|---|---|
| 22 | \u6628\u591c\u5907\u4efd\u4efb\u52a1\u662f\u5426\u6210\u529f | | | \u5931\u8d25\u5f53\u65e5\u91cd\u8dd1 |
| 23 | \u5907\u4efd\u6587\u4ef6\u65f6\u95f4\u4e0e\u5927\u5c0f | | | \u4e3a 0 \u6216\u9aa4\u964d\u8981\u67e5 |
| 24 | \u79bb\u7fa4\u5907\u4efd\u662f\u5426\u53ef\u8bfb | | | \u62bd\u6837\u6302\u8f7d |
| 25 | \u8ddd\u4e0a\u6b21\u6062\u590d\u6f14\u7ec3\u5929\u6570 | | | \u6838\u5fc3\u7cfb\u7edf\u4e0d\u8d85\u8fc7 90 \u5929 |

## \u4e94 \u544a\u8b66\u9879\u5904\u7f6e\u6c47\u603b

| \u5e8f | \u5173\u8054\u9879 | \u73b0\u8c61 | \u6839\u56e0 | \u5904\u7f6e\u52a8\u4f5c | \u9a8c\u8bc1\u7ed3\u679c | \u8d23\u4efb\u4eba | \u72b6\u6001 | \u5173\u95ed\u65f6\u95f4 |
|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | |

> \u9a8c\u8bc1\u7ed3\u679c\u4e3a\u7a7a\u7b49\u4e8e\u672a\u95ed\u73af\u3002\u53ea\u5199\u300c\u5df2\u5904\u7406\u300d\u4e0d\u7b97\u3002

## \u516d \u91c7\u96c6\u5931\u8d25\u9879\uff08\u5fc5\u987b\u8865\u91c7\uff0c\u4e0d\u80fd\u586b 0\uff09

| \u5de1\u68c0\u9879 | \u5931\u8d25\u539f\u56e0 | \u8865\u91c7\u65f6\u95f4 | \u8865\u91c7\u7ed3\u679c |
|---|---|---|---|
| | | | |

## \u4e03 \u503c\u73ed\u4ea4\u63a5

- \u9057\u7559\u8ddf\u8fdb\u9879: ____________
- \u660e\u65e5\u91cd\u70b9\u89c2\u5bdf: ____________
- \u9700\u5347\u7ea7\u4e8b\u9879: ____________
"""

SAMPLE_GOOD = """# \u91c7\u96c6\u7ed3\u679c\uff1a\u5065\u5eb7\u673a\u5668
cpu|32
load_ratio|0.45
b|0
mem_available|41.2
swap|0
disk|55
inode|18
await|3.1
util|22
established|812
timewait|240
err|4
skew|0.4
"""

SAMPLE_ALERT = """# \u91c7\u96c6\u7ed3\u679c\uff1a\u5168\u9762\u544a\u8b66\u673a\u5668
cpu|92.5
cpu_sys|31
load_ratio|3.8
b|7
mem_available|6.1
swap|45
swap_io|260
oom|1
disk|93
inode|91
await|48
util|97
established|15230
timewait|8800
err|340
skew|260
critical|2
failed|2
"""

SAMPLE_IO = """# \u91c7\u96c6\u7ed3\u679c\uff1a\u8d1f\u8f7d\u9ad8\u4f46 CPU \u4f4e\uff08IO \u74f6\u9888\uff09
cpu|12.5
load_ratio|2.6
b|9
util|96
await|61
disk|44
inode|20
"""

SAMPLE_INODE = """# \u91c7\u96c6\u7ed3\u679c\uff1a\u5bb9\u91cf\u6ca1\u6ee1\u4f46 inode \u5feb\u6ee1
cpu|30
load_ratio|0.5
b|0
mem_available|55
swap|0
disk|38
inode|93
await|2
util|10
established|300
timewait|100
err|0
skew|0.2
"""

SAMPLE_MISSING = """cpu|NA
b|\u6743\u9650\u4e0d\u8db3
foobar|12
cpu|99
"""


def selftest():
    res = []
    ok = True

    def ck(name, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        res.append("%s %s got=%r want=%r"
                   % ("PASS" if good else "FAIL", name, got, want))

    ck("alias_cn", resolve_key("CPU\u4f7f\u7528\u7387"), "cpu_used")
    ck("alias_df", resolve_key("df"), "disk_used_pct")
    ck("alias_exact", resolve_key("load_ratio"), "load_ratio")
    ck("alias_unknown", resolve_key("\u5b8c\u5168\u4e0d\u5b58\u5728\u7684\u9879"), None)

    ck("grade_cpu_ok", grade("cpu_used", 32, "web")[0], OK)
    ck("grade_cpu_warn", grade("cpu_used", 75, "web")[0], WARN)
    ck("grade_cpu_alert", grade("cpu_used", 95, "web")[0], ALERT)
    ck("role_db_looser", grade("cpu_used", 82, "db")[0], WARN)
    ck("role_web_stricter", grade("cpu_used", 82, "web")[0], ALERT)

    ck("grade_mem_ok", grade("mem_available_pct", 41.2, "web")[0], OK)
    ck("grade_mem_warn", grade("mem_available_pct", 18, "web")[0], WARN)
    ck("grade_mem_alert", grade("mem_available_pct", 8, "web")[0], ALERT)

    ck("grade_b_zero", grade("block_queue", 0, "web")[0], OK)
    ck("grade_b_alert", grade("block_queue", 7, "web")[0], ALERT)
    ck("grade_batch_load_ok", grade("load_ratio", 1.5, "batch")[0], OK)
    ck("grade_batch_load_alert", grade("load_ratio", 3.5, "batch")[0], ALERT)
    ck("grade_oom_zero", grade("oom_count", 0, "generic")[0], OK)
    ck("grade_oom_alert", grade("oom_count", 1, "generic")[0], ALERT)

    good = build_items(SAMPLE_GOOD, "web")
    ck("good_count", len(good), 13)
    ck("good_all_ok", [i["grade"] for i in good], [OK] * 13)
    ck("good_no_combo", check_combos(good, "web"), [])

    bad = build_items(SAMPLE_ALERT, "web")
    alerts = [i for i in bad if i["grade"] == ALERT]
    ck("alert_count_ge10", len(alerts) >= 10, True)
    ck("alert_has_failed_units",
       any(i["key"] == "failed_units" for i in alerts), True)
    cb = check_combos(bad, "web")
    j = " ".join(t for t, _g in cb)
    ck("combo_swap_thrash", "\u6362\u9875\u6296\u52a8" in j, True)
    ck("combo_disk90", "\u5f53\u65e5\u5904\u7406" in j, True)
    ck("combo_clock", "\u65f6\u95f4\u7ebf\u4e0d\u53ef\u4fe1" in j, True)
    ck("combo_oom", "\u88ab kill \u7684\u8fdb\u7a0b\u540d" in j, True)
    ck("combo_count_ge5", len(cb) >= 5, True)

    io = build_items(SAMPLE_IO, "web")
    cbio = check_combos(io, "web")
    jio = " ".join(t for t, _g in cbio)
    ck("combo_io_not_cpu", "\u74f6\u9888\u4e0d\u5728 CPU" in jio, True)
    ck("combo_io_mentions_b", "\u963b\u585e\u961f\u5217" in jio, True)
    ck("combo_io_alert", cbio[0][1], ALERT)

    ino = build_items(SAMPLE_INODE, "web")
    jino = " ".join(t for t, _g in check_combos(ino, "web"))
    ck("combo_inode", "No space left on device" in jino, True)

    miss = build_items(SAMPLE_MISSING, "web")
    fails = [i for i in miss if i["grade"] == FAIL]
    ck("miss_fail_ge2", len(fails) >= 2, True)
    ck("miss_dup_taken_first",
       [i["value"] for i in miss if i["key"] == "cpu_used"], [None])
    jm = " ".join(t for t, _g in check_combos(miss, "web"))
    ck("combo_collect_fail", "\u91c7\u96c6\u5931\u8d25\u4e0d\u7b49\u4e8e\u6b63\u5e38" in jm, True)

    fat = scan_fatal("Aug 1 kernel: EXT4-fs error (device sda1)\n"
                     "Aug 2 Out of memory: Killed process 991")
    ck("fatal_two", len(fat), 2)
    ck("fatal_none", scan_fatal("all good"), [])

    md = render_md(bad, cb, fat, "web", datetime.date(2026, 10, 11), 4)
    ck("md_header", md.startswith("# "), True)
    ck("md_table", "| \u6307\u6807 | \u5b9e\u6d4b | \u5224\u5b9a |" in md, True)
    ck("md_fatal", "\u81f4\u547d\u9879" in md, True)
    js = json.loads(render_json(good, [], [], "web", datetime.date(2026, 10, 11), 4))
    ck("json_keys", sorted(js.keys()),
       ["as_of", "combos", "cores", "counts", "fatals", "items", "role"])
    ck("json_counts", js["counts"].get(OK), 13)

    ck("tpl_head", CHECKLIST_TEMPLATE.startswith("# "), True)
    ck("tpl_inode", "inode \u4f7f\u7528\u7387" in CHECKLIST_TEMPLATE, True)
    ck("tpl_no_close_loop", "\u9a8c\u8bc1\u7ed3\u679c\u4e3a\u7a7a\u7b49\u4e8e\u672a\u95ed\u73af" in CHECKLIST_TEMPLATE, True)

    for line in res:
        print(line)
    print("SELFTEST %s (%d assertions)" % ("OK" if ok else "FAILED", len(res)))
    return (0 if ok else 1), len(res)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--role", default="generic", choices=list(ROLES))
    ap.add_argument("--cores", type=int, default=0)
    ap.add_argument("--as-of", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--format", default="md", choices=["md", "json"])
    ap.add_argument("--template", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        rc, n = selftest()
        outp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "_selftest_result.txt")
        open(outp, "w", encoding="utf-8").write(
            "SELFTEST %s\nresult: %s\nassertions: %d\n"
            % ("OK" if rc == 0 else "FAILED",
               "OK" if rc == 0 else "FAILED", n))
        return rc

    if a.template:
        body = CHECKLIST_TEMPLATE
        if a.out:
            open(a.out, "w", encoding="utf-8").write(body)
            print("WROTE %s" % a.out)
        else:
            print(body)
        return 0

    if not a.file or not os.path.exists(a.file):
        print("ERROR --file does not exist")
        return 2

    text = open(a.file, "r", encoding="utf-8", errors="replace").read()
    as_of = datetime.date.today()
    if a.as_of:
        m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", a.as_of.strip())
        if m:
            as_of = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    cores = a.cores if a.cores > 0 else (os.cpu_count() or 1)

    items = build_items(text, a.role)
    combos = check_combos(items, a.role)
    fatals = scan_fatal(text)
    body = (render_md(items, combos, fatals, a.role, as_of, cores)
            if a.format == "md"
            else render_json(items, combos, fatals, a.role, as_of, cores))
    if a.out:
        open(a.out, "w", encoding="utf-8").write(body)
        print("WROTE %s" % a.out)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())