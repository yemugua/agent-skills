# -*- coding: utf-8 -*-
"""DNS \u89e3\u6790\u6545\u969c\u4e94\u5c42\u5b9a\u4f4d\u5224\u5b9a\u4e0e\u6392\u67e5\u51b3\u7b56\u6811\u751f\u6210\u3002

\u7528\u6cd5:
  python dns_diagnose.py --file obs.txt --domain example.com
  python dns_diagnose.py --file obs.txt --domain example.com --json
  python dns_diagnose.py --selftest
"""
import argparse
import json
import os
import re
import sys

OK = "\u6b63\u5e38"
INFO = "\u9700\u786e\u8ba4"
ISSUE = "\u6709\u95ee\u9898"
BLOCKED = "\u88ab\u963b\u65ad"

LEVEL_ORDER = {OK: 0, INFO: 1, ISSUE: 2, BLOCKED: 3}

STATUS_CN = {
    "NOERROR": "\u67e5\u8be2\u6210\u529f\uff08\u6ce8\u610f ANSWER \u662f\u5426\u4e3a 0 \u6761\uff09",
    "NXDOMAIN": "\u57df\u540d\u4e0d\u5b58\u5728\u3002DNS \u5de5\u4f5c\u6b63\u5e38\uff0c\u901a\u5e38\u662f\u8bb0\u5f55\u5df2\u5220\u3001\u62fc\u5199\u9519\u8bef"
                "\u6216\u57df\u540d\u8fc7\u671f\u672a\u7eed\u8d39",
    "SERVFAIL": "\u670d\u52a1\u5668\u5185\u90e8\u9519\u8bef\u3002\u6743\u5a01\u4fa7\u914d\u7f6e\u9519\u8bef\u3001DNSSEC \u9a8c\u8bc1\u5931\u8d25\u6216\u6743\u5a01\u4e0d\u53ef\u8fbe",
    "REFUSED": "\u88ab\u62d2\u7edd\u67e5\u8be2\u3002\u65e0\u9012\u5f52\u6743\u9650\u6216\u88ab ACL \u62d2\u7edd",
    "NOTIMP": "\u4e0d\u652f\u6301\u8be5\u67e5\u8be2\u7c7b\u578b",
    "TIMEOUT": "\u65e0\u5e94\u7b54\u300253 \u7aef\u53e3\u88ab\u963b\u65ad\u3001\u8def\u7531\u4e0d\u901a\u6216\u670d\u52a1\u5668\u5b95\u673a",
    "TIMEDOUT": "\u65e0\u5e94\u7b54\u3002\u540c TIMEOUT",
}

LAYERS = [
    ("hosts", "L1 \u672c\u5730 hosts \u4e0e\u7f13\u5b58",
     "grep -v '^#' /etc/hosts ; dig +short <\u57df\u540d> ; resolvectl flush-caches"),
    ("config", "L2 \u5ba2\u6237\u7aef DNS \u914d\u7f6e",
     "cat /etc/resolv.conf ; nc -zv <dns> 53 ; \u770b dig \u8f93\u51fa flags \u662f\u5426\u542b ra"),
    ("resolver", "L3 \u9012\u5f52\u89e3\u6790\u5668",
     "dig +short @223.5.5.5 <\u57df\u540d> ; dig +short @8.8.8.8 <\u57df\u540d>"),
    ("auth", "L4 \u6743\u5a01 DNS \u8bb0\u5f55",
     "dig +trace <\u57df\u540d> ; dig +trace <\u57df\u540d> NS"),
    ("transport", "L5 \u4f20\u8f93\u4e0e\u52ab\u6301",
     "nc -zv <dns> 53 ; dig +tcp @<dns> <\u57df\u540d> ; \u6279\u91cf\u89e3\u6790\u68c0\u6d4b\u6c61\u67d3"),
]

BOOL_KEYS = (
    "local_hosts_hit", "local_cache_stale", "resolve_conf_ok",
    "dns_reachable", "port53_ok", "ip_consistent", "suspect_pollution",
    "ra_flag",
)

INT_KEYS = ("ttl", "current_dns_answer_count", "public_dns_answer_count",
            "auth_answer_count")

STATUS_KEYS = ("current_dns_status", "public_dns_status", "auth_status")

IP_KEYS = ("current_dns_answer", "public_dns_answer", "auth_answer")

DEFAULTS = {
    "local_hosts_hit": 0,
    "local_cache_stale": 0,
    "resolve_conf_ok": 1,
    "dns_reachable": 1,
    "port53_ok": 1,
    "ip_consistent": 1,
    "suspect_pollution": 0,
}


def to_int(v):
    m = re.match(r"^(-?\d+)", (v or "").strip())
    return int(m.group(1)) if m else None


def parse(text):
    got = {}
    for ln in (text or "").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or ln.startswith("//"):
            continue
        parts = re.split(r"[|\t,;=]", ln, maxsplit=1)
        if len(parts) < 2:
            continue
        k = parts[0].strip().lower()
        v = parts[1].strip()
        if k in BOOL_KEYS or k in INT_KEYS:
            n = to_int(v)
            if n is not None:
                got[k] = n
        elif k in STATUS_KEYS:
            got[k] = v.upper()
        elif k in IP_KEYS:
            got[k] = v
    return got


def ip_of(s):
    return (s or "").strip().split(",")[0].strip()


def check_local(d):
    rows = []
    if d.get("local_hosts_hit"):
        rows.append(("hosts", ISSUE,
                     "hosts \u6587\u4ef6\u4e2d\u5b58\u5728\u76f8\u5173\u8bb0\u5f55\u3002hosts \u4f18\u5148\u7ea7\u9ad8\u4e8e DNS\uff0c"
                     "\u5fc5\u987b\u5148\u786e\u8ba4\u8fd9\u4e9b\u8bb0\u5f55\u662f\u4e0d\u662f\u4e34\u65f6\u6d4b\u8bd5\u7559\u4e0b\u7684\uff0c"
                     "\u7528 grep -v '^#' /etc/hosts \u5b9a\u4f4d\u540e\u5220\u9664\u6216\u6ce8\u91ca"))
    if d.get("local_cache_stale"):
        rows.append(("hosts", ISSUE,
                     "\u672c\u5730 DNS \u7f13\u5b58\u672a\u5237\u65b0\u3002\u6e05\u7406\u65b9\u5f0f\u56e0\u7cfb\u7edf\u800c\u5f02: "
                     "systemd-resolved \u7528 resolvectl flush-caches\uff0c"
                     "dnsmasq \u91cd\u542f\u670d\u52a1\uff0cmacOS \u7528 dscacheutil -flushcache\uff0c"
                     "Windows \u7528 ipconfig /flushdns\uff0c"
                     "\u6d4f\u89c8\u5668\u8fd8\u9700\u5355\u72ec\u6e05 DNS \u7f13\u5b58"))
    cur = d.get("current_dns_status")
    if cur in ("TIMEOUT", "TIMEDOUT"):
        rows.append(("hosts", BLOCKED,
                     "\u672c\u5730\u67e5\u8be2\u8d85\u65f6\u3002\u8fd9\u4e0d\u662f\u7f13\u5b58\u95ee\u9898\uff0c"
                     "\u5e94\u8f6c\u67e5 DNS \u53ef\u8fbe\u6027\u4e0e\u914d\u7f6e"))
    elif cur == "NXDOMAIN":
        rows.append(("hosts", INFO,
                     "\u672c\u5730\u8fd4\u56de NXDOMAIN\u3002NXDOMAIN \u8bf4\u660e DNS \u5de5\u4f5c\u6b63\u5e38\uff0c"
                     "\u542b\u4e49\u662f\u57df\u540d\u4e0d\u5b58\u5728\uff0c\u901a\u5e38\u662f\u8bb0\u5f55\u5df2\u5220\u3001\u62fc\u5199\u9519\u8bef"
                     "\u6216\u57df\u540d\u8fc7\u671f\u672a\u7eed\u8d39"))
    elif cur == "SERVFAIL":
        rows.append(("hosts", INFO,
                     "\u672c\u5730\u8fd4\u56de SERVFAIL\uff0c\u8bf4\u660e\u67e5\u8be2\u5df2\u5230\u8fbe\u67d0\u53f0 DNS "
                     "\u4f46\u5176\u5185\u90e8\u51fa\u9519\uff0c\u5e94\u8f6c\u67e5 L3 \u4e0e L4"))
    return rows


def check_config(d):
    rows = []
    if not d.get("resolve_conf_ok", 1):
        rows.append(("config", ISSUE,
                     "resolv.conf \u914d\u7f6e\u5f02\u5e38\u3002\u786e\u8ba4 nameserver \u6307\u5411\u7684\u5730\u5740\u53ef\u8fbe\uff0c"
                     "\u5185\u7f51\u573a\u666f\u8fd8\u9700\u914d\u7f6e search \u57df"))
    if not d.get("dns_reachable", 1):
        rows.append(("config", ISSUE,
                     "\u914d\u7f6e\u7684 DNS \u670d\u52a1\u5668\u4e0d\u53ef\u8fbe\u3002\u7528 nc -zv <dns> 53 \u9a8c\u8bc1\uff0c"
                     "\u5e76\u68c0\u67e5\u8def\u7531\u4e0e\u9632\u706b\u5899"))
    if d.get("ra_flag") == 0:
        rows.append(("config", ISSUE,
                     "dig \u8f93\u51fa\u7f3a\u5c11 ra \u6807\u5fd7\uff0c\u8bf4\u660e\u8be5\u670d\u52a1\u5668\u4e0d\u505a\u9012\u5f52\u89e3\u6790\uff0c"
                     "\u4e0d\u80fd\u5f53\u4f5c\u9012\u5f52 DNS \u4f7f\u7528"))
    return rows


def check_resolver(d):
    rows = []
    cs = d.get("current_dns_status")
    ps = d.get("public_dns_status")
    cip = ip_of(d.get("current_dns_answer"))
    pip = ip_of(d.get("public_dns_answer"))
    if cs and ps:
        if cs != ps:
            rows.append(("resolver", ISSUE,
                         "\u672c\u5730 DNS \u8fd4\u56de %s\uff0c\u516c\u5171 DNS \u8fd4\u56de %s\uff0c\u4e24\u8005\u4e0d\u4e00\u81f4\u3002"
                         "\u5e38\u89c1\u539f\u56e0\u662f\u672c\u5730 DNS \u7f13\u5b58\u8fc7\u671f\u3001\u6545\u969c\u6216\u9650\u6d41\uff0c"
                         "\u5e94\u91cd\u70b9\u67e5\u8fd9\u4e00\u5c42" % (cs, ps)))
        else:
            rows.append(("resolver", OK,
                         "\u672c\u5730\u4e0e\u516c\u5171 DNS \u7684 status \u4e00\u81f4\uff08%s\uff09\uff0c"
                         "\u9012\u5f52\u89e3\u6790\u5668\u5c42\u57fa\u672c\u6b63\u5e38" % cs))
    if cip and pip:
        if cip != pip:
            rows.append(("resolver", ISSUE,
                         "\u672c\u5730\u89e3\u6790\u5230 %s\uff0c\u516c\u5171 DNS \u89e3\u6790\u5230 %s\u3002"
                         "\u53ef\u80fd\u662f\u7f13\u5b58\u672a\u8fc7\u671f\uff0c\u4e5f\u53ef\u80fd\u662f\u672c\u5730\u914d\u7f6e\u4e86\u79c1\u6709\u89e3\u6790"
                         "\uff08split-horizon\uff09\u3002\u7528 dig +trace \u786e\u8ba4\u6743\u5a01\u8bb0\u5f55"
                         % (cip, pip)))
        else:
            rows.append(("resolver", OK,
                         "\u672c\u5730\u4e0e\u516c\u5171 DNS \u8fd4\u56de\u76f8\u540c IP\uff08%s\uff09" % cip))
    return rows


def check_auth(d):
    rows = []
    ast = (d.get("auth_status") or "").upper()
    aip = ip_of(d.get("auth_answer"))
    cip = ip_of(d.get("current_dns_answer"))
    if ast == "NXDOMAIN":
        rows.append(("auth", ISSUE,
                     "\u6743\u5a01 DNS \u4e5f\u8fd4\u56de NXDOMAIN\uff0c\u8bf4\u660e\u8bb0\u5f55\u4e0d\u5b58\u5728\u6216\u57df\u540d\u5df2\u8fc7\u671f\u3002"
                     "\u8fd9\u4e00\u5c42\u4e0d\u662f\u672c\u5730\u95ee\u9898\uff0c\u5e94\u627e\u57df\u540d\u670d\u52a1\u5546\u6838\u5b9e"))
    elif ast == "SERVFAIL":
        rows.append(("auth", ISSUE,
                     "\u6743\u5a01\u8fd4\u56de SERVFAIL\u3002\u5e38\u89c1\u4e8e NS \u8bb0\u5f55\u7f3a\u5931\u3001CAA \u51b2\u7a81\u3001"
                     "\u533a\u57df\u4f20\u9001\u914d\u7f6e\u9519\u8bef\uff0c\u5c5e\u57df\u540d\u670d\u52a1\u5546\u4fa7\u95ee\u9898"))
    elif ast and aip:
        if cip and cip != aip:
            rows.append(("auth", INFO,
                         "\u672c\u5730\u89e3\u6790\u5230 %s \u4f46\u6743\u5a01\u4e3a %s\u3002"
                         "\u82e5\u6743\u5a01\u8bb0\u5f55\u6b63\u786e\uff0c\u8bf4\u660e\u662f\u7f13\u5b58\u6216\u4e2d\u95f4\u94fe\u8def\u95ee\u9898\uff1b"
                         "\u82e5\u6743\u5a01\u672c\u8eab\u662f\u9519\u7684\uff0c\u9700\u8981\u57df\u540d\u670d\u52a1\u5546\u6539\u8bb0\u5f55"
                         % (cip, aip)))
        else:
            rows.append(("auth", OK, "\u6743\u5a01\u8bb0\u5f55\u6b63\u786e\uff08%s\uff09" % aip))
    elif aip:
        rows.append(("auth", OK, "\u6743\u5a01\u8bb0\u5f55\u4e3a %s" % aip))
    return rows


def check_transport(d):
    rows = []
    if not d.get("port53_ok", 1):
        rows.append(("transport", BLOCKED,
                     "53 \u7aef\u53e3\u4e0d\u53ef\u8fbe\uff0cUDP \u88ab\u963b\u65ad\u6216\u8def\u7531\u4e0d\u901a\u3002"
                     "\u7528 dig +tcp @<dns> <\u57df\u540d> \u9a8c\u8bc1 TCP \u662f\u5426\u53ef\u7528"))
    for key in ("current_dns_answer", "public_dns_answer", "auth_answer"):
        v = ip_of(d.get(key))
        if v and v.split(".")[0] in ("0", "127", "255"):
            rows.append(("transport", BLOCKED,
                         "\u89e3\u6790\u7ed3\u679c\u4e3a %s\uff0c\u8fd9\u662f\u5178\u578b\u7684 sinkhole \u6216\u5360\u4f4d\u8fd4\u56de\uff0c"
                         "\u5c5e\u4e8e DNS \u52ab\u6301\u6216\u6c61\u67d3\u7279\u5f81" % v))
    if d.get("suspect_pollution"):
        rows.append(("transport", BLOCKED,
                     "\u547d\u4e2d\u6c61\u67d3\u7279\u5f81: \u968f\u673a\u4e0d\u5b58\u5728\u7684\u57df\u540d\u4e5f\u80fd\u89e3\u6790\u51fa\u7ed3\u679c\uff0c"
                     "\u6216\u591a\u4e2a\u65e0\u5173\u57df\u540d\u8fd4\u56de\u540c\u4e00 IP\u3002"
                     "\u4e0d\u8981\u53ea\u5728\u5ba2\u6237\u7aef\u7ed5\u8fc7\uff0c\u95ee\u9898\u5728\u94fe\u8def\u4e0a\uff0c"
                     "\u5e94\u8f6c\u7f51\u7edc\u7ba1\u7406\u4e0e\u5b89\u5168\u56e2\u961f\u5904\u7406"))
    return rows


def check_ttl(d):
    rows = []
    ttl = d.get("ttl")
    if ttl is None:
        rows.append(("auth", INFO,
                     "\u672a\u63d0\u4f9b TTL\u3002\u5224\u65ad\u300c\u6539\u4e86\u8bb0\u5f55\u4e0d\u751f\u6548\u300d\u5fc5\u987b\u770b TTL"))
        return rows
    if ttl <= 60:
        rows.append(("auth", INFO,
                     "TTL \u4e3a %d \u79d2\uff0c\u5207\u6362\u4f1a\u5f88\u5feb\u751f\u6548\uff0c"
                     "\u4f46\u9891\u7e41\u53d8\u66f4\u65f6\u89e3\u6790\u5668\u538b\u529b\u5927" % ttl))
    elif ttl >= 86400:
        rows.append(("auth", ISSUE,
                     "TTL \u4e3a %d \u79d2\uff08\u22651 \u5929\uff09\u3002\u53d8\u66f4\u8bb0\u5f55\u540e\u4f1a\u957f\u65f6\u95f4\u4e0d\u751f\u6548\uff0c"
                     "\u53d8\u66f4\u524d\u5e94\u5148\u628a TTL \u964d\u5230 300 \u5e76\u7b49\u65e7 TTL \u8fc7\u671f" % ttl))
    else:
        rows.append(("auth", OK,
                     "TTL \u4e3a %d \u79d2\uff0c\u5728\u5e38\u89c4\u533a\u95f4\u3002"
                     "\u53d8\u66f4\u540e\u9700\u7b49\u5f85\u8be5\u65f6\u95f4\u624d\u80fd\u5168\u7f51\u751f\u6548" % ttl))
    return rows


def _norm(rows, name):
    out = []
    for r in rows:
        if len(r) == 4:
            out.append(r)
        else:
            out.append((r[0], name, r[1], r[2]))
    return out


def worst(levels):
    lv = OK
    for x in levels:
        if LEVEL_ORDER.get(x, 0) > LEVEL_ORDER.get(lv, 0):
            lv = x
    return lv


def build(text, domain):
    raw = parse(text)
    d = dict(DEFAULTS)
    d.update(raw)
    rows = []
    rows += _norm(check_local(d), "\u672c\u5730\u5c42")
    rows += _norm(check_config(d), "\u5ba2\u6237\u7aef\u914d\u7f6e")
    rows += _norm(check_resolver(d), "\u9012\u5f52\u89e3\u6790\u5668")
    rows += _norm(check_auth(d), "\u6743\u5a01 DNS")
    rows += _norm(check_transport(d), "\u4f20\u8f93\u4e0e\u52ab\u6301")
    rows += _norm(check_ttl(d), "TTL")
    if not raw:
        rows.append(("hosts", "\u8f93\u5165", ISSUE,
                     "\u672a\u63d0\u4f9b\u4efb\u4f55\u89c2\u6d4b\u6570\u636e\u3002\u6392\u67e5\u5fc5\u987b\u4ece L1 \u672c\u5730\u5c42\u5f00\u59cb\uff0c"
                     "\u8df3\u8fc7 hosts \u4e0e\u7f13\u5b58\u5c31\u76f4\u63a5\u6000\u7591\u57df\u540d\u670d\u52a1\u5546\u662f\u6700\u5e38\u89c1\u5f2f\u8def"))
    elif not rows:
        rows.append(("hosts", "\u6c47\u603b", OK,
                     "\u672a\u53d1\u73b0\u5f02\u5e38\u3002\u82e5\u4e1a\u52a1\u4ecd\u6709\u95ee\u9898\uff0c"
                     "\u5e94\u8f6c\u67e5 HTTP\u3001TLS \u4e0e\u5e94\u7528\u5c42"))
    return {
        "domain": domain or "\u672a\u6307\u5b9a",
        "overall": worst([r[2] for r in rows]),
        "observed": d,
        "rows": [{"layer": k, "name": n, "level": lv, "note": note}
                 for k, n, lv, note in rows],
        "layers": [{"key": k, "name": n, "cmds": c} for k, n, c in LAYERS],
        "status_cn": STATUS_CN,
    }


CMD_TREE = [
    ("L1 \u672c\u5730", [
        "grep -v '^#' /etc/hosts | grep -i <\u57df\u540d\u5173\u952e\u8bcd>",
        "dig +short <\u57df\u540d>",
        "dig +short @8.8.8.8 <\u57df\u540d>",
        "resolvectl flush-caches",
    ]),
    ("L2 \u914d\u7f6e", [
        "cat /etc/resolv.conf",
        "nc -zv <dns \u670d\u52a1\u5668> 53",
        "dig <\u57df\u540d> | grep -E '^;; flags'",
    ]),
    ("L3 \u9012\u5f52\u89e3\u6790\u5668", [
        "dig +short @223.5.5.5 <\u57df\u540d>",
        "dig +short @8.8.8.8 <\u57df\u540d>",
        "dig +short @1.1.1.1 <\u57df\u540d>",
    ]),
    ("L4 \u6743\u5a01", [
        "dig +trace <\u57df\u540d>",
        "dig +trace <\u57df\u540d> NS",
        "dig <\u57df\u540d> | grep -A3 'ANSWER SECTION'",
    ]),
    ("L5 \u4f20\u8f93\u4e0e\u52ab\u6301", [
        "nc -zv <dns \u670d\u52a1\u5668> 53",
        "dig +tcp @<dns \u670d\u52a1\u5668> <\u57df\u540d>",
        "dig +short asdfjkl1234567890.example",
    ]),
]

MANUAL = [
    "\u73b0\u8c61\u662f\u5728\u54ea\u53f0\u673a\u5668\u4e0a\u51fa\u73b0\u7684\uff0c\u6362\u673a\u5668\u8fd8\u80fd\u590d\u73b0\u5417",
    "\u662f\u89e3\u6790\u5931\u8d25\uff08\u62a5\u9519\uff09\u8fd8\u662f\u89e3\u6790\u5230\u9519\u8bef\u5730\u5740\uff08\u80fd\u901a\u4f46\u8d70\u9519\u5730\u65b9\uff09",
    "dig \u8f93\u51fa\u7684 SERVER \u5b57\u6bb5\u662f\u4e0d\u662f\u4f60\u4ee5\u4e3a\u7684\u90a3\u4e2a DNS",
    "hosts \u6587\u4ef6\u662f\u5426\u88ab\u6539\u8fc7\uff08\u4e34\u65f6\u6d4b\u8bd5\u8bb0\u5f55\u5fd8\u4e86\u5220\u662f\u5e38\u89c1\u539f\u56e0\uff09",
    "\u8bb0\u5f55\u6539\u52a8\u65f6\u95f4\u52a0 TTL \u662f\u5426\u4ecd\u5927\u4e8e\u5f53\u524d\u65f6\u95f4\uff08\u662f\u5219\u8fd8\u6ca1\u751f\u6548\uff09",
    "\u662f\u5426\u5df2\u8fde\u5185\u7f51\u6216 VPN\uff08\u516c\u7f51 DNS \u89e3\u6790\u4e0d\u4e86\u5185\u7f51\u57df\u540d\uff09",
    "\u662f\u5426\u4e3a\u57df\u540d\u8fc7\u671f\u6216\u7eed\u8d39\u95ee\u9898",
]


def render_md(r):
    L = []
    L.append("# DNS \u89e3\u6790\u6545\u969c\u5b9a\u4f4d\u62a5\u544a")
    L.append("")
    L.append("- \u57df\u540d: %s" % r["domain"])
    L.append("- \u7efc\u5408\u7ed3\u8bba: **%s**" % r["overall"])
    L.append("")
    L.append("## \u4e00 \u9010\u5c42\u5224\u5b9a")
    L.append("")
    L.append("| \u5c42 | \u5224\u5b9a | \u8bf4\u660e |")
    L.append("|---|---|---|")
    for it in r["rows"]:
        L.append("| %s | %s | %s |" % (it["name"], it["level"], it["note"]))
    L.append("")
    L.append("## \u4e8c status \u72b6\u6001\u7801\u5bf9\u7167")
    L.append("")
    L.append("| status | \u542b\u4e49 |")
    L.append("|---|---|")
    for k, v in r["status_cn"].items():
        L.append("| `%s` | %s |" % (k, v))
    L.append("")
    L.append("## \u4e09 \u6392\u67e5\u547d\u4ee4\uff08\u6309\u987a\u5e8f\u6267\u884c\uff0c\u4e0d\u8981\u8df3\u6b65\uff09")
    L.append("")
    for name, cmds in CMD_TREE:
        L.append("### %s" % name)
        L.append("")
        for c in cmds:
            L.append("```bash\n%s\n```" % c)
        L.append("")
    L.append("## \u56db \u5fc5\u987b\u4eba\u5de5\u786e\u8ba4")
    L.append("")
    for t in MANUAL:
        L.append("- [ ] %s" % t)
    L.append("")
    L.append("---")
    L.append("")
    L.append("> \u811a\u672c\u4e0d\u53d1\u8d77\u4efb\u4f55 DNS \u67e5\u8be2\uff0c\u53ea\u5f52\u62e2\u5df2\u91c7\u96c6\u5230\u7684\u89c2\u6d4b\u7ed3\u679c\u3002")
    L.append("> \u7f3a\u4efb\u4f55\u4e00\u5c42\u7684\u89c2\u6d4b\u6570\u636e\u65f6\uff0c\u7ed3\u8bba\u53ea\u80fd\u5b9a\u4f4d\u5230\u5df2\u6709\u6570\u636e\u7684\u8fb9\u754c\u3002")
    return "\n".join(L) + "\n"


SAMPLE_HOSTS = """local_hosts_hit=1
local_cache_stale=1
current_dns_status=NOERROR
current_dns_answer=10.0.0.99
public_dns_status=NOERROR
public_dns_answer=1.2.3.4
auth_status=NOERROR
auth_answer=1.2.3.4
ttl=86400
"""

SAMPLE_AUTH = """local_hosts_hit=0
local_cache_stale=0
resolve_conf_ok=1
dns_reachable=1
current_dns_status=NXDOMAIN
public_dns_status=NXDOMAIN
auth_status=NXDOMAIN
ttl=3600
"""

SAMPLE_TIMEOUT = """local_hosts_hit=0
resolve_conf_ok=0
dns_reachable=0
port53_ok=0
current_dns_status=TIMEOUT
ttl=300
"""

SAMPLE_POLLUTION = """local_hosts_hit=0
resolve_conf_ok=1
dns_reachable=1
port53_ok=1
current_dns_status=NOERROR
current_dns_answer=0.0.0.0
public_dns_status=NOERROR
public_dns_answer=0.0.0.0
auth_status=NOERROR
auth_answer=1.2.3.4
suspect_pollution=1
ttl=300
"""

SAMPLE_ALL_OK = """local_hosts_hit=0
local_cache_stale=0
resolve_conf_ok=1
dns_reachable=1
port53_ok=1
current_dns_status=NOERROR
current_dns_answer=1.2.3.4
public_dns_status=NOERROR
public_dns_answer=1.2.3.4
auth_status=NOERROR
auth_answer=1.2.3.4
ip_consistent=1
ttl=300
"""

SAMPLE_RA = """resolve_conf_ok=1
dns_reachable=1
ra_flag=0
current_dns_status=NOERROR
ttl=300
"""

SAMPLE_EMPTY = "# \u53ea\u6709\u6ce8\u91ca\n"

SAMPLE_JUNK = """\u8fd9\u4e00\u884c\u6ca1\u6709\u5206\u9694\u7b26
random_key|1
current_dns_status|noerror
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

    p = parse(SAMPLE_HOSTS)
    ck("parse_hosts", p.get("local_hosts_hit"), 1)
    ck("parse_ip", p.get("current_dns_answer"), "10.0.0.99")
    ck("parse_status", p.get("current_dns_status"), "NOERROR")
    ck("parse_ttl", p.get("ttl"), 86400)
    ck("parse_junk_unknown", parse(SAMPLE_JUNK).get("random_key"), None)
    ck("parse_junk_status", parse(SAMPLE_JUNK).get("current_dns_status"),
       "NOERROR")
    ck("parse_empty", parse(SAMPLE_EMPTY), {})
    ck("parse_none_text", parse(None), {})

    r1 = build(SAMPLE_HOSTS, "example.com")
    ck("l1_issue", any(it["layer"] == "hosts" and it["level"] == ISSUE
                       for it in r1["rows"]), True)
    ck("l1_overall", r1["overall"], ISSUE)
    ck("ttl_high", "TTL \u964d\u5230 300" in " ".join(
        it["note"] for it in r1["rows"]), True)
    j8 = " ".join(it["note"] for it in r1["rows"])
    ck("resolver_mismatch", "\u516c\u5171 DNS \u89e3\u6790\u5230" in j8, True)
    ck("resolver_note", "\u9012\u5f52\u89e3\u6790\u5668\u5c42" in j8, True)

    r_ok = build(SAMPLE_ALL_OK, "example.com")
    ck("all_ok_overall", r_ok["overall"], OK)
    ck("all_ok_ttl", "TTL \u4e3a 300 \u79d2" in " ".join(
        it["note"] for it in r_ok["rows"]), True)

    r4 = build(SAMPLE_AUTH, "example.com")
    j4 = " ".join(it["note"] for it in r4["rows"])
    ck("auth_nxdomain", "\u5e94\u627e\u57df\u540d\u670d\u52a1\u5546\u6838\u5b9e" in j4, True)
    ck("auth_overall", r4["overall"], ISSUE)

    r5 = build(SAMPLE_TIMEOUT, "example.com")
    ck("timeout_overall", r5["overall"], BLOCKED)
    ck("timeout_not_cache", "\u8fd9\u4e0d\u662f\u7f13\u5b58\u95ee\u9898" in " ".join(
        it["note"] for it in r5["rows"]), True)

    r6 = build(SAMPLE_POLLUTION, "evil.example")
    j6 = " ".join(it["note"] for it in r6["rows"])
    ck("pollution_overall", r6["overall"], BLOCKED)
    ck("pollution_sinkhole", "sinkhole" in j6, True)
    ck("pollution_no_bypass", "\u4e0d\u8981\u53ea\u5728\u5ba2\u6237\u7aef\u7ed5\u8fc7" in j6, True)

    r7 = build(SAMPLE_EMPTY, "example.com")
    ck("empty_overall", r7["overall"], ISSUE)
    ck("empty_note", "\u4ece L1 \u672c\u5730\u5c42\u5f00\u59cb" in " ".join(
        it["note"] for it in r7["rows"]), True)

    r9 = build(SAMPLE_RA, "example.com")
    ck("ra_flag", any("\u4e0d\u505a\u9012\u5f52\u89e3\u6790" in it["note"] for it in r9["rows"]),
       True)
    ck("ra_overall", r9["overall"], ISSUE)

    ck("status_nxdomain_meaning",
       "DNS \u5de5\u4f5c\u6b63\u5e38" in STATUS_CN["NXDOMAIN"], True)
    ck("status_servfail_meaning", "\u6743\u5a01" in STATUS_CN["SERVFAIL"], True)
    ck("status_len", len(STATUS_CN) >= 6, True)

    md = render_md(r1)
    ck("md_header", md.startswith("# "), True)
    ck("md_layers", "\u9010\u5c42\u5224\u5b9a" in md, True)
    ck("md_status", "status \u72b6\u6001\u7801\u5bf9\u7167" in md, True)
    ck("md_tree", "\u6392\u67e5\u547d\u4ee4" in md, True)
    ck("md_manual", "\u5fc5\u987b\u4eba\u5de5\u786e\u8ba4" in md, True)
    js = json.loads(json.dumps(r_ok, ensure_ascii=False))
    ck("json_keys", sorted(js.keys()),
       ["domain", "layers", "observed", "overall", "rows", "status_cn"])
    ck("json_layers_len", len(js["layers"]), 5)
    ck("json_rows_ok", js["rows"][0]["level"] in (OK, INFO, ISSUE, BLOCKED),
       True)

    ck("layers_len", len(LAYERS), 5)
    ck("cmd_tree_len", len(CMD_TREE), 5)
    ck("manual_len", len(MANUAL) >= 7, True)
    ck("level_order", LEVEL_ORDER[BLOCKED] > LEVEL_ORDER[ISSUE], True)
    ck("worst_fn", worst([OK, INFO, ISSUE]), ISSUE)
    ck("ip_of", ip_of("1.2.3.4, 5.6.7.8"), "1.2.3.4")
    ck("ip_of_empty", ip_of(None), "")
    ck("norm_len", len(_norm([("a", OK, "n")], "N")), 1)
    ck("norm_4tuple", _norm([("a", "N", OK, "n")], "N")[0][1], "N")

    for line in res:
        print(line)
    print("SELFTEST %s (%d assertions)" % ("OK" if ok else "FAILED", len(res)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--domain", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--format", default="md", choices=["md", "json"])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        rc = selftest()
        outp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "_selftest_result.txt")
        open(outp, "w", encoding="utf-8").write(
            "SELFTEST %s\nresult: %s\n"
            % ("OK" if rc == 0 else "FAILED", "OK" if rc == 0 else "FAILED"))
        return rc

    if not a.file or not os.path.exists(a.file):
        print("ERROR --file does not exist")
        return 2
    text = open(a.file, "r", encoding="utf-8", errors="replace").read()
    r = build(text, a.domain)
    body = (render_md(r) if a.format == "md"
            else json.dumps(r, ensure_ascii=False, indent=2))
    if a.out:
        open(a.out, "w", encoding="utf-8").write(body)
        print("WROTE %s" % a.out)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())