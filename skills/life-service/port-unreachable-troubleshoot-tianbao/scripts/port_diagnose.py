# -*- coding: utf-8 -*-
"""\u7aef\u53e3\u4e0d\u901a\u7684\u5206\u5c42\u5224\u5b9a\u4e0e\u5931\u8d25\u539f\u56e0\u5f52\u56e0\u3002

\u7528\u6cd5:
  python port_diagnose.py --file obs.txt --host example.com --port 8080
  python port_diagnose.py --file obs.txt --host db.internal --port 3306 --json
  python port_diagnose.py --selftest
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

# \u63a2\u6d4b\u7ed3\u679c\u5f52\u4e00\u5316
PROBE_CN = {
    "refused": "\u7acb\u5373\u5931\u8d25\u5e76\u6536\u5230 RST\u3002\u5305\u5230\u8fbe\u4e86\u76ee\u6807\uff0c\u4f46\u76ee\u6807\u6ca1\u6709\u76d1\u542c\u8be5\u7aef\u53e3"
               "\u6216\u88ab\u4e3b\u52a8\u62d2\u7edd\u3002**\u6392\u67e5\u8d77\u70b9\u662f\u76ee\u6807\u4fa7\u76d1\u542c\uff0c\u4e0d\u662f\u9632\u706b\u5899**",
    "refused_immediate": "\u7acb\u5373\u5931\u8d25\u5e76\u6536\u5230 RST\u3002\u5305\u5230\u8fbe\u4e86\u76ee\u6807\uff0c"
                         "\u95ee\u9898\u5728\u76ee\u6807\u4fa7\u76d1\u542c\u6216\u4e3b\u52a8\u62d2\u7edd",
    "timeout": "\u7b49\u5f85\u540e\u8d85\u65f6\u4e14\u65e0\u4efb\u4f55\u5e94\u7b54\u3002\u5305\u6ca1\u6709\u5230\u8fbe\u76ee\u6807\uff0c"
               "\u6216\u5230\u8fbe\u540e\u88ab\u9759\u9ed8\u4e22\u5f03\u3002**\u6392\u67e5\u8d77\u70b9\u662f\u9632\u706b\u5899\u4e0e\u5b89\u5168\u7ec4**",
    "timedout": "\u7b49\u5f85\u540e\u8d85\u65f6\u4e14\u65e0\u5e94\u7b54\u3002\u5305\u6ca1\u6709\u5230\u8fbe\u76ee\u6807\uff0c"
                "\u6216\u88ab\u9759\u9ed8\u4e22\u5f03\uff0c\u5e94\u67e5\u9632\u706b\u5899\u4e0e\u5b89\u5168\u7ec4",
    "reset": "\u8fde\u63a5\u5efa\u7acb\u540e\u88ab\u91cd\u7f6e\u3002\u8fde\u63a5\u5df2\u5efa\u7acb\uff0c"
             "\u88ab\u5bf9\u7aef\u5e94\u7528\u6216\u4e2d\u95f4\u8bbe\u5907\u91cd\u7f6e",
    "ok": "\u8fde\u63a5\u5efa\u7acb\u6210\u529f\uff0c\u7aef\u53e3\u4e0e\u94fe\u8def\u5747\u6b63\u5e38",
    "succeeded": "\u8fde\u63a5\u5efa\u7acb\u6210\u529f\uff0c\u7aef\u53e3\u4e0e\u94fe\u8def\u5747\u6b63\u5e38",
    "open": "\u8fde\u63a5\u5efa\u7acb\u6210\u529f\uff0c\u7aef\u53e3\u4e0e\u94fe\u8def\u5747\u6b63\u5e38",
    "closed": "\u7aef\u53e3\u5173\u95ed\uff0c\u7b49\u540c refused",
    "filtered": "\u88ab\u8fc7\u6ee4\uff0c\u7b49\u540c timeout",
}

BOOL_KEYS = (
    "listen_found", "service_running", "port_occupied", "route_ok",
    "ping_ok", "local_firewall_ok", "secgroup_ok", "target_firewall_ok",
    "proxy_env_hit", "ipv6_only", "no_port_mapping",
)

INT_KEYS = ("est_conn", "timewait_conn", "syn_recv", "port_range_size",
            "max_conn_limit")

STR_KEYS = ("probe_result", "listen_addr", "resolved_ip")

DEFAULTS = {
    "listen_found": 0,
    "service_running": 0,
    "port_occupied": 0,
    "route_ok": 1,
    "ping_ok": 1,
    "local_firewall_ok": 1,
    "secgroup_ok": 1,
    "target_firewall_ok": 1,
    "proxy_env_hit": 0,
    "ipv6_only": 0,
    "no_port_mapping": 0,
}

# \u53ea\u5bf9\u672c\u673a\u53ef\u8fbe\u7684\u76d1\u542c\u5730\u5740
LOOPBACK = ("127.0.0.1", "::1", "localhost")

# \u5e38\u89c1\u5e94\u7528\u7aef\u53e3
PORT_CN = {
    "22": "SSH", "80": "HTTP", "443": "HTTPS", "3306": "MySQL",
    "5432": "PostgreSQL", "6379": "Redis", "27017": "MongoDB",
    "9200": "Elasticsearch", "5672": "RabbitMQ", "15672": "RabbitMQ \u7ba1\u7406\u53f0",
    "9092": "Kafka", "2379": "etcd", "6443": "Kubernetes API",
    "8080": "HTTP \u5907\u7528/\u5e38\u89c1\u5e94\u7528\u7aef\u53e3", "8443": "HTTPS \u5907\u7528/\u5e38\u89c1\u5e94\u7528\u7aef\u53e3",
}


def to_int(v):
    m = re.match(r"^(-?\d+)", (v or "").strip())
    return int(m.group(1)) if m else None


def norm_probe(v):
    s = (v or "").strip().lower().replace("-", "_").replace(" ", "_")
    return s


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
        elif k in STR_KEYS:
            if k == "probe_result":
                got[k] = norm_probe(v)
            else:
                got[k] = v
    return got


def is_refused(p):
    return p in ("refused", "refused_immediate", "closed")


def is_timeout(p):
    return p in ("timeout", "timedout", "filtered")


def classify_probe(d):
    """\u7b2c\u4e00\u6b65\uff1a\u5148\u5206\u6e05 refused \u4e0e timeout\u3002"""
    p = d.get("probe_result")
    if not p:
        return "\u672a\u63a2\u6d4b", INFO, "\u672a\u63d0\u4f9b\u63a2\u6d4b\u7ed3\u679c\u3002**\u6392\u67e5\u7b2c\u4e00\u6b65\u5c31\u662f\u7528 "
        "nc \u6216 telnet \u5206\u6e05 refused \u4e0e timeout**\uff0c\u4e0d\u63a2\u6d4b\u5c31\u67e5\u9632\u706b\u5899\u65b9\u5411\u5fc5\u9519"
    if p in PROBE_CN:
        if is_refused(p):
            return "refused", ISSUE, "\u63a2\u6d4b\u7ed3\u679c: refused\u3002" + PROBE_CN[p]
        if is_timeout(p):
            return "timeout", BLOCKED, "\u63a2\u6d4b\u7ed3\u679c: timeout\u3002" + PROBE_CN[p]
        if p in ("ok", "succeeded", "open"):
            return "ok", OK, "\u63a2\u6d4b\u7ed3\u679c: \u8fde\u63a5\u5efa\u7acb\u6210\u529f\uff0c\u7aef\u53e3\u4e0e\u94fe\u8def\u5747\u6b63\u5e38"
        if p == "reset":
            return "reset", ISSUE, "\u63a2\u6d4b\u7ed3\u679c: reset\u3002" + PROBE_CN[p]
    return "\u672a\u77e5", INFO, "\u63a2\u6d4b\u7ed3\u679c %s \u65e0\u6cd5\u8bc6\u522b\uff0c\u8bf7\u7528 refused \u6216 timeout \u8868\u8ff0" % p


def check_listen(d, kind):
    """\u76d1\u542c\u5730\u5740\u7c7b\u95ee\u9898\uff1arefused \u573a\u666f\u7684\u91cd\u70b9\u3002"""
    rows = []
    addr = (d.get("listen_addr") or "").strip().lower()
    if not d.get("listen_found"):
        if kind == "refused":
            rows.append(("listen", ISSUE,
                         "\u76ee\u6807\u4fa7\u6ca1\u6709\u8be5\u7aef\u53e3\u7684\u76d1\u542c\u8bb0\u5f55\u3002"
                         "**\u8fd9\u6b63\u662f refused \u7684\u5178\u578b\u539f\u56e0**: "
                         "\u670d\u52a1\u6ca1\u542f\u52a8\u3001\u76d1\u542c\u5728\u522b\u7684\u7aef\u53e3\uff0c\u6216\u5df2\u5d29\u6e83\u3002"
                         "\u7528 systemctl status \u4e0e ps \u786e\u8ba4\u670d\u52a1\u72b6\u6001"))
        else:
            rows.append(("listen", INFO,
                         "\u76ee\u6807\u4fa7\u672a\u89c2\u5bdf\u5230\u76d1\u542c\u8bb0\u5f55\u3002"
                         "\u4f46 timeout \u66f4\u53ef\u80fd\u6765\u81ea\u8fc7\u6ee4\uff0c"
                         "\u4ecd\u9700\u5728\u76ee\u6807\u673a\u5668\u672c\u673a\u7528 ss -lntp \u590d\u6838"))
    elif addr:
        if addr in LOOPBACK:
            rows.append(("listen", ISSUE,
                         "\u76d1\u542c\u5730\u5740\u662f %s\uff0c**\u53ea\u5bf9\u672c\u673a\u53ef\u8fbe**\u3002"
                         "\u5916\u7f51\u4e0e\u5176\u4ed6\u7f51\u5361\u8bbf\u95ee\u5fc5\u7136 refused\uff0c"
                         "\u800c\u62a5\u9519\u4fe1\u606f\u5b8c\u5168\u770b\u4e0d\u51fa\u539f\u56e0\u3002"
                         "\u8fd9\u662f\u6700\u9ad8\u9891\u7684\u5751\uff0c\u6570\u636e\u5e93\u4e0e\u4e2d\u95f4\u4ef6\u5c24\u5176\u5e38\u89c1" % addr))
        elif addr.startswith("127.") or addr.startswith("172.1") \
                or addr.startswith("192.168.0") or addr.startswith("10.0.0"):
            rows.append(("listen", INFO,
                         "\u76d1\u542c\u5730\u5740\u662f %s\uff0c\u53ea\u7ed1\u5b9a\u4e86\u7279\u5b9a\u5185\u7f51\u5730\u5740\u3002"
                         "\u9700\u786e\u8ba4\u5ba2\u6237\u7aef\u662f\u5426\u8d70\u540c\u4e00\u7f51\u5361" % addr))
        elif addr in ("0.0.0.0", "*", "[::]"):
            rows.append(("listen", OK,
                         "\u76d1\u542c\u5730\u5740\u662f %s\uff0c\u8986\u76d6\u5168\u90e8\u7f51\u5361\uff0c\u76d1\u542c\u914d\u7f6e\u6b63\u5e38" % addr))
    if not d.get("service_running"):
        rows.append(("listen", ISSUE,
                     "\u76ee\u6807\u670d\u52a1\u672a\u5728\u8fd0\u884c\u3002refused \u7684\u6700\u5e38\u89c1\u76f4\u63a5\u539f\u56e0\uff0c"
                     "\u7528 systemctl status <\u670d\u52a1\u540d> \u4e0e ps -ef \u786e\u8ba4"))
    return rows


def check_occupied(d):
    rows = []
    if d.get("port_occupied"):
        rows.append(("occupied", ISSUE,
                     "\u7aef\u53e3\u88ab\u522b\u7684\u8fdb\u7a0b\u5360\u7528\uff0c\u5e38\u89c1\u62a5\u9519\u662f Address already in use\u3002"
                     "**\u5904\u7f6e\u524d\u5fc5\u987b\u786e\u8ba4\u5360\u7528\u8005**: "
                     "ss -lntp \u770b PID \u4e0e\u8fdb\u7a0b\u540d\uff0cps -p <PID> -o pid,cmd "
                     "\u786e\u8ba4\u4e3a\u4ec0\u4e48\u5728\u8dd1\uff0c\u518d\u51b3\u5b9a\u662f\u5426\u505c\u6b62\u3002"
                     "\u6ce8\u610f\u540c\u8fdb\u7a0b\u591a\u5b9e\u4f8b\u5c5e\u6b63\u5e38\uff0c\u4e0d\u8981\u8bef\u6740"))
    return rows


def check_filters(d, kind):
    rows = []
    if not d.get("secgroup_ok", 1):
        lv = BLOCKED if kind == "timeout" else INFO
        rows.append(("filter", lv,
                     "\u4e91\u5b89\u5168\u7ec4\u6216\u7f51\u7edc ACL \u672a\u653e\u884c\u3002\u5b89\u5168\u7ec4\u5728\u6d41\u91cf\u5230\u8fbe\u673a\u5668**\u4e4b\u524d**"
                     "\u62e6\u622a\uff0c\u8868\u73b0\u901a\u5e38\u4e3a timeout\u3002"
                     "**\u4e0e\u7cfb\u7edf\u9632\u706b\u5899\u662f\u4e24\u5c42\uff0c\u53ea\u6539\u4e00\u5c42\u4e0d\u751f\u6548**"))
    if not d.get("target_firewall_ok", 1):
        lv = BLOCKED if kind == "timeout" else INFO
        rows.append(("filter", lv,
                     "\u76ee\u6807\u673a\u5668\u7cfb\u7edf\u9632\u706b\u5899\u672a\u653e\u884c\u3002\u7528 "
                     "iptables -L INPUT -n -v --line-numbers \u67e5\u770b\u3002"
                     "DROP \u89c4\u5219\u8868\u73b0\u4e3a timeout\uff0cREJECT \u89c4\u5219\u8868\u73b0\u4e3a refused"))
    if not d.get("local_firewall_ok", 1):
        rows.append(("filter", INFO,
                     "\u672c\u673a\u9632\u706b\u5899\u672a\u653e\u884c\u51fa\u65b9\u5411\u3002\u7528 "
                     "iptables -L -n -v \u67e5\u770b OUTPUT \u94fe"))
    return rows


def check_route(d):
    rows = []
    if not d.get("route_ok", 1):
        rows.append(("route", ISSUE,
                     "\u8def\u7531\u4e0d\u6b63\u786e\u3002\u7528 ip route get <\u76ee\u6807IP> \u67e5\u770b\u5b9e\u9645\u8d70\u54ea\u5f20\u5361\u3002"
                     "\u591a\u7f51\u5361\u4e0e\u7b56\u7565\u8def\u7531\u573a\u666f\u5fc5\u67e5"))
    return rows


def check_hidden(d):
    """\u9690\u853d\u5e72\u6270\u56e0\u7d20\u3002"""
    rows = []
    if d.get("proxy_env_hit"):
        rows.append(("hidden", ISSUE,
                     "\u5b58\u5728\u4ee3\u7406\u73af\u5883\u53d8\u91cf\uff0ccurl \u7684\u5931\u8d25\u53ef\u80fd\u4e0e\u7aef\u53e3\u65e0\u5173\u3002"
                     "\u5148 env | grep -i proxy \u786e\u8ba4\uff0c"
                     "\u52a0 --noproxy '*' \u590d\u6d4b\u518d\u4e0b\u7ed3\u8bba"))
    if d.get("ipv6_only"):
        rows.append(("hidden", ISSUE,
                     "\u89e3\u6790\u6216\u670d\u52a1\u8d70\u7684\u662f IPv6\u3002\u82e5\u670d\u52a1\u53ea\u76d1\u542c IPv4 \u7684 "
                     "0.0.0.0 \u800c\u5ba2\u6237\u7aef\u8fde AAAA \u5730\u5740\uff0c\u4f1a\u5931\u8d25\u3002"
                     "\u7528 dig +short <\u57df\u540d> AAAA \u786e\u8ba4\uff0c"
                     "\u518d dig +short <\u57df\u540d> A \u5bf9\u6bd4"))
    if d.get("no_port_mapping"):
        rows.append(("hidden", ISSUE,
                     "\u5bb9\u5668\u672a\u505a\u7aef\u53e3\u6620\u5c04\u3002\u5bb9\u5668\u5185\u670d\u52a1\u6b63\u5e38\u4f46\u5bbf\u4e3b\u673a\u7aef\u53e3\u4e0d\u901a\uff0c"
                     "\u7528 docker ps \u770b Ports \u5217\u662f\u5426\u6709\u6620\u5c04"))
    ip = d.get("resolved_ip")
    if ip and ":" in ip:
        rows.append(("hidden", INFO,
                     "\u89e3\u6790\u7ed3\u679c %s \u662f IPv6 \u5730\u5740\u3002"
                     "\u5148 dig \u786e\u8ba4\u89e3\u6790\uff0c\u518d\u7528\u8be5 IP \u76f4\u63a5\u6d4b\u7aef\u53e3\u6392\u9664\u5e72\u6270" % ip))
    return rows


def check_conns(d):
    rows = []
    est = d.get("est_conn")
    lim = d.get("max_conn_limit")
    syn = d.get("syn_recv")
    tw = d.get("timewait_conn")
    if lim and est and est >= lim:
        rows.append(("conn", ISSUE,
                     "ESTABLISHED(%d) \u5df2\u8fbe\u5e94\u7528\u4e0a\u9650(%d)\u3002"
                     "\u73b0\u8c61\u662f**\u5076\u53d1 refused**\uff0c\u4f46\u6839\u56e0\u662f\u8fde\u63a5\u6570\u6253\u6ee1\u800c\u975e\u7aef\u53e3\u95ee\u9898\uff0c"
                     "\u4e0e\u7f51\u7edc\u6545\u969c\u8868\u73b0\u76f8\u4f3c\u5fc5\u987b\u5206\u5f00\u770b" % (est, lim)))
    elif lim and est and est >= lim * 0.8:
        rows.append(("conn", INFO,
                     "ESTABLISHED(%d) \u5df2\u8fbe\u4e0a\u9650(%d)\u7684\u516b\u6210\uff0c"
                     "\u9700\u5173\u6ce8\u8fde\u63a5\u6c60\u662f\u5426\u672a\u590d\u7528" % (est, lim)))
    if syn and syn > 1000:
        rows.append(("conn", ISSUE,
                     "SYN-RECV \u5806\u79ef %d\uff0c\u8bf4\u660e backlog \u6ee1\u6216\u5b58\u5728 SYN \u653b\u51fb\u3002"
                     "\u67e5 somaxconn \u4e0e\u5f02\u5e38\u6765\u6e90\uff0c**\u5148\u5b9a\u4f4d\u6839\u56e0\u518d\u8c03\u53c2**" % syn))
    if est and tw and est > 0 and tw > est:
        rows.append(("conn", INFO,
                     "TIME-WAIT(%d) \u591a\u4e8e ESTABLISHED(%d): "
                     "\u77ed\u8fde\u63a5\u9ad8\u9891\u6216\u672a\u4f7f\u7528\u8fde\u63a5\u6c60\uff0c"
                     "\u5e94\u7528\u8fde\u63a5\u6c60\u53ef\u89e3\u51b3\uff0c\u4e0d\u5fc5\u6539\u5185\u6838\u53c2\u6570" % (tw, est)))
    return rows


def worst(levels):
    lv = OK
    for x in levels:
        if LEVEL_ORDER.get(x, 0) > LEVEL_ORDER.get(lv, 0):
            lv = x
    return lv


def build(text, host, port):
    raw = parse(text)
    d = dict(DEFAULTS)
    d.update(raw)
    kind, plv, pnote = classify_probe(d)
    rows = [("probe", "\u63a2\u6d4b\u5224\u5b9a", plv, pnote)]
    if kind == "refused":
        rows += _norm(check_listen(d, kind), "\u76ee\u6807\u76d1\u542c")
        rows += _norm(check_occupied(d), "\u7aef\u53e3\u5360\u7528")
        rows += _norm(check_conns(d), "\u8fde\u63a5\u6570")
        rows += _norm(check_filters(d, kind), "\u8fc7\u6ee4")
    elif kind == "timeout":
        rows += _norm(check_filters(d, kind), "\u8fc7\u6ee4")
        rows += _norm(check_listen(d, kind), "\u76ee\u6807\u76d1\u542c")
        rows += _norm(check_occupied(d), "\u7aef\u53e3\u5360\u7528")
        rows += _norm(check_conns(d), "\u8fde\u63a5\u6570")
    else:
        rows += _norm(check_listen(d, kind), "\u76ee\u6807\u76d1\u542c")
        rows += _norm(check_occupied(d), "\u7aef\u53e3\u5360\u7528")
        rows += _norm(check_conns(d), "\u8fde\u63a5\u6570")
        rows += _norm(check_filters(d, kind), "\u8fc7\u6ee4")
    rows += _norm(check_route(d), "\u8def\u7531")
    rows += _norm(check_hidden(d), "\u9690\u853d\u56e0\u7d20")
    if not raw:
        rows.append(("input", "\u8f93\u5165", ISSUE,
                     "\u672a\u63d0\u4f9b\u4efb\u4f55\u89c2\u6d4b\u6570\u636e\u3002\u6392\u67e5\u7b2c\u4e00\u6b65\u662f\u7528 nc \u6216 telnet "
                     "\u5206\u6e05 refused \u4e0e timeout\uff0c\u4e0d\u63a2\u6d4b\u5c31\u67e5\u9632\u706b\u5899\u65b9\u5411\u5fc5\u9519"))
    return {
        "host": host or "\u672a\u6307\u5b9a",
        "port": port or "\u672a\u6307\u5b9a",
        "port_service": PORT_CN.get(str(port), "\u672a\u77e5\u670d\u52a1"),
        "kind": kind,
        "overall": worst([r[2] for r in rows]),
        "observed": d,
        "rows": [{"group": g, "name": n, "level": lv, "note": note}
                 for g, n, lv, note in rows],
    }


def _norm(rows, name):
    out = []
    for r in rows:
        if len(r) == 4:
            out.append(r)
        else:
            out.append((r[0], name, r[1], r[2]))
    return out


CMDS = [
    ("\u7b2c\u4e00\u6b65 \u5206\u6e05\u5931\u8d25\u7c7b\u578b", [
        "nc -zv -w 3 <host> <port>                      # refused \u7acb\u5373\u8fd4\u56de\uff0ctimeout \u7b49\u6ee1 -w",
        "curl -sv --connect-timeout 3 telnet://<host>:<port>",
        "curl --noproxy '*' -sv http://<host>:<port>/    # \u6392\u9664\u4ee3\u7406\u5e72\u6270",
    ]),
    ("\u7b2c\u4e8c\u6b65 \u76ee\u6807\u76d1\u542c", [
        "ss -lntp | grep :<port>                        # \u770b\u6709\u6ca1\u6709\u76d1\u542c\u3001\u7ed1\u5728\u54ea\u4e2a\u5730\u5740",
        "lsof -i :<port> ; fuser -n tcp <port>",
        "systemctl status <\u670d\u52a1\u540d> ; ps -ef | grep <\u670d\u52a1\u540d>",
        "curl -sv http://127.0.0.1:<port>/              # \u5728\u76ee\u6807\u673a\u672c\u673a\u81ea\u6d4b",
    ]),
    ("\u7b2c\u4e09\u6b65 \u4e24\u5c42\u8fc7\u6ee4", [
        "iptables -L INPUT -n -v --line-numbers",
        "iptables -S INPUT ; iptables -L -n | grep <port>",
        "nft list ruleset 2>/dev/null",
        "firewall-cmd --list-all 2>/dev/null ; ufw status 2>/dev/null",
        "\u4e91\u63a7\u5236\u53f0\u6838\u5bf9\u5b89\u5168\u7ec4\u5165\u65b9\u5411\u89c4\u5219\u3001\u6e90 IP \u6bb5\u4e0e\u4f18\u5148\u7ea7",
    ]),
    ("\u7b2c\u56db\u6b65 \u8def\u7531\u4e0e\u8fde\u63a5\u6570", [
        "ip route get <\u76ee\u6807IP>",
        "traceroute -n -T -p <port> <host>",
        "ss -s ; ss -tan state established | wc -l",
        "ss -tan | awk '{print $5}' | sort | uniq -c | sort -rn | head",
        "cat /proc/sys/net/core/somaxconn /proc/sys/net/ipv4/ip_local_port_range",
    ]),
]

MANUAL = [
    "\u5931\u8d25\u662f refused\uff08\u7acb\u5373\uff09\u8fd8\u662f timeout\uff08\u7b49\u5f85\u540e\uff09",
    "ss -lntp \u91cc\u6709\u6ca1\u6709\u8fd9\u4e2a\u7aef\u53e3",
    "\u76d1\u542c\u5730\u5740\u662f 127.0.0.1 \u8fd8\u662f 0.0.0.0",
    "\u670d\u52a1\u662f\u5426\u771f\u7684\u5728\u8fd0\u884c",
    "\u7aef\u53e3\u662f\u5426\u88ab\u522b\u7684\u8fdb\u7a0b\u5360\u7528",
    "\u4e91\u5b89\u5168\u7ec4\u4e0e\u7cfb\u7edf\u9632\u706b\u5899\u662f\u5426\u90fd\u67e5\u4e86",
    "\u662f\u5426\u5b58\u5728\u4ee3\u7406\u73af\u5883\u53d8\u91cf",
    "\u57df\u540d\u89e3\u6790\u5230 IPv4 \u8fd8\u662f IPv6",
    "\u662f\u5426\u771f\u8981\u5f00\u653e\u65b0\u7aef\u53e3\uff08\u9700\u5b89\u5168\u5ba1\u6279\u4e0e\u56de\u6536\u65f6\u95f4\uff09",
]


def render_md(r):
    L = []
    L.append("# \u7aef\u53e3\u4e0d\u901a\u5b9a\u4f4d\u62a5\u544a")
    L.append("")
    L.append("- \u76ee\u6807: %s:%s\uff08%s\uff09" % (r["host"], r["port"], r["port_service"]))
    L.append("- \u5931\u8d25\u7c7b\u578b: **%s**" % r["kind"])
    L.append("- \u7efc\u5408\u7ed3\u8bba: **%s**" % r["overall"])
    L.append("")
    L.append("## \u4e00 \u9010\u9879\u5224\u5b9a")
    L.append("")
    L.append("| \u5206\u7ec4 | \u5224\u5b9a | \u8bf4\u660e |")
    L.append("|---|---|---|")
    for it in r["rows"]:
        L.append("| %s | %s | %s |" % (it["name"], it["level"], it["note"]))
    L.append("")
    L.append("## \u4e8c \u6392\u67e5\u547d\u4ee4\uff08\u6309\u987a\u5e8f\u6267\u884c\uff09")
    L.append("")
    for name, cmds in CMDS:
        L.append("### %s" % name)
        L.append("")
        for c in cmds:
            L.append("```bash\n%s\n```" % c)
        L.append("")
    L.append("## \u4e09 \u5fc5\u987b\u4eba\u5de5\u786e\u8ba4")
    L.append("")
    for t in MANUAL:
        L.append("- [ ] %s" % t)
    L.append("")
    L.append("---")
    L.append("")
    L.append("> \u811a\u672c\u4e0d\u53d1\u8d77\u4efb\u4f55\u7f51\u7edc\u8fde\u63a5\uff0c\u53ea\u5f52\u62e2\u5df2\u91c7\u96c6\u7684\u89c2\u6d4b\u7ed3\u679c\u3002")
    L.append("> \u5f00\u653e\u7aef\u53e3\u5c5e\u4e8e\u5b89\u5168\u53d8\u66f4\uff0c\u5fc5\u987b\u7ecf\u5ba1\u6279\u5e76\u8bc4\u4f30\u66b4\u9732\u9762\u3002")
    return "\n".join(L) + "\n"


SAMPLE_REFUSED = """probe_result=refused
listen_found=0
service_running=0
route_ok=1
ping_ok=1
local_firewall_ok=1
secgroup_ok=1
target_firewall_ok=1
"""

SAMPLE_LOOPBACK = """probe_result=refused
listen_found=1
listen_addr=127.0.0.1
service_running=1
route_ok=1
"""

SAMPLE_TIMEOUT = """probe_result=timeout
listen_found=1
listen_addr=0.0.0.0
service_running=1
route_ok=1
secgroup_ok=0
target_firewall_ok=1
"""

SAMPLE_OCCUPIED = """probe_result=refused
listen_found=0
port_occupied=1
service_running=1
"""

SAMPLE_CONN_FULL = """probe_result=refused
listen_found=1
listen_addr=0.0.0.0
service_running=1
est_conn=1000
max_conn_limit=1000
timewait_conn=80
syn_recv=0
"""

SAMPLE_SYN = """probe_result=timeout
listen_found=1
listen_addr=0.0.0.0
service_running=1
syn_recv=4200
secgroup_ok=1
target_firewall_ok=1
"""

SAMPLE_PROXY = """probe_result=refused
listen_found=1
listen_addr=0.0.0.0
service_running=1
proxy_env_hit=1
"""

SAMPLE_IPV6 = """probe_result=timeout
listen_found=1
listen_addr=0.0.0.0
service_running=1
ipv6_only=1
resolved_ip=2400:3200::1
target_firewall_ok=1
secgroup_ok=1
"""

SAMPLE_OK = """probe_result=ok
listen_found=1
listen_addr=0.0.0.0
service_running=1
route_ok=1
"""

SAMPLE_EMPTY = "# \u53ea\u6709\u6ce8\u91ca\n"

SAMPLE_JUNK = """\u8fd9\u884c\u6ca1\u6709\u5206\u9694\u7b26
unknown_key|1
probe_result=Connection Refused
listen_found=abc
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

    p = parse(SAMPLE_REFUSED)
    ck("parse_probe", p.get("probe_result"), "refused")
    ck("parse_listen", p.get("listen_found"), 0)
    ck("parse_addr", parse(SAMPLE_LOOPBACK).get("listen_addr"), "127.0.0.1")
    ck("parse_junk_unknown", parse(SAMPLE_JUNK).get("unknown_key"), None)
    ck("parse_junk_num", parse(SAMPLE_JUNK).get("listen_found"), None)
    ck("parse_junk_probe",
       parse(SAMPLE_JUNK).get("probe_result"), "connection_refused")
    ck("parse_empty", parse(SAMPLE_EMPTY), {})
    ck("parse_none", parse(None), {})

    ck("is_refused", is_refused("refused"), True)
    ck("is_timeout", is_timeout("timeout"), True)
    ck("is_refused_neg", is_refused("timeout"), False)

    # refused -> \u76ee\u6807\u76d1\u542c\u4f18\u5148
    r1 = build(SAMPLE_REFUSED, "app.example.com", 8080)
    ck("refused_kind", r1["kind"], "refused")
    ck("refused_overall", r1["overall"], ISSUE)
    j1 = " ".join(it["note"] for it in r1["rows"])
    ck("refused_target", "\u76ee\u6807\u4fa7\u6ca1\u6709\u8be5\u7aef\u53e3\u7684\u76d1\u542c\u8bb0\u5f55" in j1, True)
    ck("refused_not_fw", "\u6392\u67e5\u8d77\u70b9\u662f\u76ee\u6807\u4fa7\u76d1\u542c\uff0c\u4e0d\u662f\u9632\u706b\u5899" in j1, True)
    ck("refused_service", "\u76ee\u6807\u670d\u52a1\u672a\u5728\u8fd0\u884c" in j1, True)
    ck("port_service", r1["port_service"], "HTTP \u5907\u7528/\u5e38\u89c1\u5e94\u7528\u7aef\u53e3")

    # \u76d1\u542c 127.0.0.1 \u8bc6\u522b
    r2 = build(SAMPLE_LOOPBACK, "db.example.com", 3306)
    j2 = " ".join(it["note"] for it in r2["rows"])
    ck("loopback_detect", "\u53ea\u5bf9\u672c\u673a\u53ef\u8fbe" in j2, True)
    ck("loopback_top", "\u6700\u9ad8\u9891\u7684\u5751" in j2, True)
    ck("mysql_service", r2["port_service"], "MySQL")

    # timeout -> \u8fc7\u6ee4\u4f18\u5148
    r3 = build(SAMPLE_TIMEOUT, "api.example.com", 443)
    ck("timeout_kind", r3["kind"], "timeout")
    ck("timeout_overall", r3["overall"], BLOCKED)
    j3 = " ".join(it["note"] for it in r3["rows"])
    ck("timeout_fw", "\u4e91\u5b89\u5168\u7ec4\u6216\u7f51\u7edc ACL \u672a\u653e\u884c" in j3, True)
    ck("timeout_two_layers", "\u4e0e\u7cfb\u7edf\u9632\u706b\u5899\u662f\u4e24\u5c42" in j3, True)

    # \u7aef\u53e3\u5360\u7528
    r4 = build(SAMPLE_OCCUPIED, "app.example.com", 9000)
    j4 = " ".join(it["note"] for it in r4["rows"])
    ck("occupied_detect", "Address already in use" in j4, True)
    ck("occupied_no_kill", "\u4e0d\u8981\u8bef\u6740" in j4, True)

    # \u8fde\u63a5\u6570\u6253\u6ee1\uff08\u8868\u73b0\u662f refused \u4f46\u6839\u56e0\u4e0d\u540c\uff09
    r5 = build(SAMPLE_CONN_FULL, "db.example.com", 5432)
    j5 = " ".join(it["note"] for it in r5["rows"])
    ck("conn_full", "\u5df2\u8fbe\u5e94\u7528\u4e0a\u9650" in j5, True)
    ck("conn_not_port", "\u6839\u56e0\u662f\u8fde\u63a5\u6570\u6253\u6ee1\u800c\u975e\u7aef\u53e3\u95ee\u9898" in j5, True)

    # SYN \u5806\u79ef
    r6 = build(SAMPLE_SYN, "app.example.com", 8080)
    j6 = " ".join(it["note"] for it in r6["rows"])
    ck("syn_detect", "SYN-RECV \u5806\u79ef" in j6, True)
    ck("syn_root_cause", "\u5148\u5b9a\u4f4d\u6839\u56e0\u518d\u8c03\u53c2" in j6, True)

    # \u4ee3\u7406\u4e0e IPv6
    r7 = build(SAMPLE_PROXY, "api.example.com", 8080)
    ck("proxy_detect", "\u4ee3\u7406\u73af\u5883\u53d8\u91cf" in " ".join(
        it["note"] for it in r7["rows"]), True)
    r8 = build(SAMPLE_IPV6, "api.example.com", 443)
    ck("ipv6_detect", "IPv6 \u5730\u5740" in " ".join(
        it["note"] for it in r8["rows"]), True)

    # \u6b63\u5e38
    r9 = build(SAMPLE_OK, "api.example.com", 443)
    ck("ok_kind", r9["kind"], "ok")
    ck("ok_overall", r9["overall"], OK)

    # \u7a7a\u8f93\u5165
    r10 = build(SAMPLE_EMPTY, "x", "80")
    ck("empty_overall", r10["overall"], ISSUE)
    ck("empty_note", "\u4e0d\u63a2\u6d4b\u5c31\u67e5\u9632\u706b\u5899\u65b9\u5411\u5fc5\u9519" in " ".join(
        it["note"] for it in r10["rows"]), True)

    # \u672a\u63a2\u6d4b
    d_nop = dict(DEFAULTS)
    r11 = build("listen_found=1\n", "x", "80")
    ck("no_probe_kind", r11["kind"], "\u672a\u63a2\u6d4b")
    ck("no_probe_note", "\u6392\u67e5\u7b2c\u4e00\u6b65" in " ".join(
        it["note"] for it in r11["rows"]), True)

    # \u6e32\u67d3
    md = render_md(r3)
    ck("md_header", md.startswith("# "), True)
    ck("md_kind", "\u5931\u8d25\u7c7b\u578b" in md, True)
    ck("md_cmds", "\u6392\u67e5\u547d\u4ee4" in md, True)
    ck("md_manual", "\u5fc5\u987b\u4eba\u5de5\u786e\u8ba4" in md, True)
    js = json.loads(json.dumps(r1, ensure_ascii=False))
    ck("json_keys", sorted(js.keys()),
       ["host", "kind", "observed", "overall", "port", "port_service", "rows"])
    ck("json_kind", js["kind"], "refused")

    ck("status_len", len(PROBE_CN) >= 8, True)
    ck("port_cn_len", len(PORT_CN) >= 10, True)
    ck("manual_len", len(MANUAL) >= 9, True)
    ck("cmd_groups", len(CMDS), 4)
    ck("level_order", LEVEL_ORDER[BLOCKED] > LEVEL_ORDER[ISSUE], True)
    ck("worst_fn", worst([OK, INFO, ISSUE]), ISSUE)
    ck("norm_fn", _norm([("a", OK, "n")], "N")[0][1], "N")

    for line in res:
        print(line)
    print("SELFTEST %s (%d assertions)" % ("OK" if ok else "FAILED", len(res)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--host", default="")
    ap.add_argument("--port", default="")
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
    r = build(text, a.host, a.port)
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