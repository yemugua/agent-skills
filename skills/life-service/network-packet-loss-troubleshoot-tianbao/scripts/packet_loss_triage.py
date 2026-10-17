# -*- coding: utf-8 -*-
"""\u7f51\u7edc\u4e22\u5305\u5206\u5c42\u5b9a\u4f4d\u5224\u5b9a\u4e0e\u6392\u67e5\u51b3\u7b56\u6811\u751f\u6210\u3002

\u7528\u6cd5:
  python packet_loss_triage.py --file obs.txt --target example.com --gateway 192.168.1.1
  python packet_loss_triage.py --file obs.txt --json
  python packet_loss_triage.py --selftest
"""
import argparse
import json
import os
import re
import sys

OK = "\u6b63\u5e38"
WATCH = "\u5173\u6ce8"
ALERT = "\u544a\u8b66"
CRITICAL = "\u4e25\u91cd"
FAULT = "\u6545\u969c"

LEVEL_ORDER = {OK: 0, WATCH: 1, ALERT: 2, CRITICAL: 3, FAULT: 4}

# \u5206\u5c42\u952e -> (\u4e2d\u6587\u540d, \u547d\u4ee4)
WARN = "\u9700\u786e\u8ba4"

LAYERS = [
    ("loopback", "L0 \u672c\u673a\u534f\u8bae\u6808",
     "ping -c 100 -i 0.1 127.0.0.1"),
    ("gateway", "L1 \u672c\u673a\u5230\u9ed8\u8ba4\u7f51\u5173",
     "ping -c 100 -i 0.1 <GATEWAY>"),
    ("public", "L2 \u5230\u8fd0\u8425\u5546\u6216\u516c\u7f51\u53c2\u7167",
     "ping -c 100 -i 0.1 223.5.5.5"),
    ("target", "L3/L4 \u76ee\u6807\u4fa7",
     "ping -c 100 -i 0.1 <TARGET>"),
]

ALIAS = {
    "loopback": "loopback", "lo": "loopback", "\u672c\u673a": "loopback",
    "gateway": "gateway", "gw": "gateway", "\u7f51\u5173": "gateway",
    "public": "public", "isp": "public", "\u8fd0\u8425\u5546": "public", "\u516c\u7f51": "public",
    "target": "target", "dst": "target", "\u76ee\u6807": "target",
    "mtr_loss": "mtr_loss", "mtr": "mtr_loss",
    "jitter": "jitter", "stdev": "jitter", "\u6296\u52a8": "jitter",
    "txdrop": "txdrop", "\u4e0a\u884c\u4e22\u5305": "txdrop",
    "rxdropped": "rxdropped", "rx_dropped": "rxdropped",
    "mtu_fail": "mtu_fail", "mtu": "mtu_fail",
    "icmp_limited": "icmp_limited", "icmp\u9650\u901f": "icmp_limited",
    "business_ok": "business_ok", "\u4e1a\u52a1\u6b63\u5e38": "business_ok",
}

EXTRA = {
    "mtr_loss": ("mtr \u9996\u73b0\u4e22\u5305\u8df3\u7684\u4e22\u5305\u7387", "%"),
    "jitter": ("\u6296\u52a8(StDev \u6216 Wrst-Avg)", "ms"),
    "txdrop": ("\u4e0a\u884c\u961f\u5217\u4e22\u5f03\u901f\u7387", "\u4e2a/\u79d2"),
    "rxdropped": ("\u7f51\u5361 RX dropped \u589e\u901f", "\u4e2a/\u5206\u949f"),
    "mtu_fail": ("MTU \u63a2\u6d4b\u5931\u8d25", "0/1"),
    "icmp_limited": ("\u5df2\u786e\u8ba4\u8fd0\u8425\u5546\u9650\u901f ICMP", "0/1"),
    "business_ok": ("\u4e1a\u52a1\u4fa7\u5b9e\u6d4b\u6b63\u5e38", "0/1"),
}

# \u4e22\u5305\u7387\u9608\u503c\uff08\u8d8a\u5927\u8d8a\u5371\u9669\uff09
LOSS_THRESH = [(0.5, OK), (2, WATCH), (5, ALERT), (10, CRITICAL), (None, FAULT)]

ACTIONS = {
    "loopback": "\u672c\u673a\u534f\u8bae\u6808\u5f02\u5e38\u6781\u7f55\u89c1\uff0c\u5148\u770b\u7cfb\u7edf\u8d1f\u8f7d\u4e0e\u7f51\u5361\u9a71\u52a8\uff1b\u6301\u7eed\u5f02\u5e38\u9700\u67e5\u5185\u6838\u4e0e\u5bb9\u5668\u7f51\u7edc",
    "gateway": "\u4f18\u5148\u67e5\u672c\u673a: ip -br a \u67e5\u7f51\u5361\u72b6\u6001; ethtool -S eth0 \u67e5 dropped/crc; "
               "ip -s link show eth0; \u6362\u7f51\u7ebf\u6362\u7aef\u53e3\u5bf9\u6bd4",
    "public": "\u67e5\u672c\u5730\u51fa\u53e3\u8bbe\u5907(\u8def\u7531\u5668/\u9632\u706b\u5899); sar -n DEV 1 5 \u770b txdrop \u662f\u5426\u56e0\u4e0a\u884c\u6253\u6ee1; "
              "\u4e0a\u884c\u6253\u6ee1\u9700\u5347\u5e26\u5bbd\u6216\u9650\u901f",
    "target": "\u4ece\u76ee\u6807\u5185\u7f51\u53cd\u5411 ping \u9a8c\u8bc1; \u67e5\u76ee\u6807\u9632\u706b\u5899\u4e0e\u5b89\u5168\u7ec4; "
              "ss -s \u770b\u76ee\u6807\u8fde\u63a5\u6570\u662f\u5426\u6253\u6ee1",
}

EVIDENCE = [
    "\u53cc\u5411 mtr \u62a5\u544a\u5404\u4e00\u4efd, \u6bcf\u4efd\u6837\u672c\u4e0d\u5c11\u4e8e 100 \u5305",
    "\u6bcf\u5c42\u6d4b\u8bd5\u7684\u7cbe\u786e\u65f6\u95f4\u6233(\u7cbe\u786e\u5230\u5206\u949f)\u4e0e\u6d4b\u8bd5\u6e90 IP",
    "\u9996\u73b0\u4e22\u5305\u8df3\u7684\u5177\u4f53 IP \u4e0e\u6240\u5c5e AS \u53f7",
    "\u4e22\u5305\u7387\u6570\u503c\u4e0e\u6301\u7eed\u65f6\u957f(\u4e0d\u662f\u300c\u5076\u5c14\u300d)",
    "\u662f\u5426\u4e0e\u4e1a\u52a1\u91cf\u76f8\u5173(\u540c\u65f6\u6bb5\u5e26\u5bbd\u4e0e\u8fde\u63a5\u6570)",
    "\u590d\u73b0\u89c4\u5f8b: \u6bcf\u5929\u4ec0\u4e48\u65f6\u6bb5\u3001\u591a\u4e45\u4e00\u6b21",
    "\u672c\u4fa7\u4ea4\u6362\u673a\u7aef\u53e3\u65e0 CRC \u9519\u8bef\u3001\u65e0\u961f\u5217\u4e22\u5f03\u7684\u8bc1\u660e",
    "\u5df2\u5c1d\u8bd5\u8fc7\u7684\u5904\u7f6e\u4e0e\u5176\u7ed3\u679c",
    "\u4e1a\u52a1\u5f71\u54cd\u91cf\u5316: \u5f71\u54cd\u7528\u6237\u6570\u3001\u5931\u8d25\u7387",
]


def norm(s):
    return (s or "").strip().lower().replace(" ", "").replace("_", "")


ALIAS_N = dict((norm(k), v) for k, v in ALIAS.items())


def resolve(key):
    k = norm(key)
    if k in ALIAS_N:
        return ALIAS_N[k]
    for kk, vv in ALIAS_N.items():
        if kk == k:
            return vv
    return None


def to_float(v):
    v = (v or "").strip().replace("%", "").replace(",", "")
    m = re.match(r"^(-?\d+(?:\.\d+)?)", v)
    return float(m.group(1)) if m else None


def parse(text):
    """\u89e3\u6790\u89c2\u6d4b\u6587\u4ef6\uff0c\u8fd4\u56de dict\u3002"""
    got = {}
    for ln in (text or "").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or ln.startswith("//"):
            continue
        parts = re.split(r"[|\t,;=]", ln, maxsplit=1)
        if len(parts) < 2:
            continue
        raw_key = parts[0].strip()
        raw_val = parts[1].strip()
        key = resolve(raw_key)
        if key is None:
            continue
        val = to_float(raw_val)
        if val is None:
            # \u65e0\u6cd5\u89e3\u6790\u7684\u503c\u8bb0\u4e3a\u91c7\u96c6\u5931\u8d25\uff0c\u4e0d\u80fd\u5f53\u6210 0 \u53c2\u4e0e\u5224\u5b9a
            got.setdefault("_bad", []).append(raw_key)
            continue
        got[key] = val
    return got


def grade_loss(rate):
    if rate is None:
        return None
    for up, lv in LOSS_THRESH:
        if up is None or rate <= up:
            return lv
    return FAULT


def first_bad_layer(got):
    """\u8fd4\u56de\u7b2c\u4e00\u5c42\u4e22\u5305\u7387\u8d85\u8fc7 0.5% \u7684\u5c42\u540d\uff0c\u6ca1\u6709\u5219\u8fd4\u56de None\u3002"""
    for key in ("loopback", "gateway", "public", "target"):
        v = got.get(key)
        if v is not None and v > 0.5:
            return key
    return None


def locate(got):
    """\u5b9a\u4f4d\u4e22\u5305\u5c42\u3002\u8fd4\u56de (\u5c42\u540d or None, \u8bf4\u660e)\u3002"""
    bad = first_bad_layer(got)
    if bad is None:
        return None, ("\u56db\u5c42\u89c2\u6d4b\u4e2d\u672a\u53d1\u73b0\u8d85\u8fc7 0.5% \u7684\u4e22\u5305\u3002"
                      "\u82e5\u4e1a\u52a1\u4ecd\u5f02\u5e38\uff0c\u95ee\u9898\u4e0d\u5728 IP \u5c42\u4e22\u5305\uff0c"
                      "\u5e94\u8f6c\u67e5 DNS\u3001TCP \u5c42\u4e0e\u5e94\u7528\u4fa7")
    if bad == "loopback":
        return bad, "\u672c\u673a\u534f\u8bae\u6808\u5c31\u4e22\u5305: \u8be5\u73b0\u8c61\u6781\u7f55\u89c1\uff0c\u5148\u6392\u7cfb\u7edf\u8d1f\u8f7d\u3001\u7f51\u5361\u9a71\u52a8\u4e0e\u5bb9\u5668\u7f51\u7edc"
    if bad == "gateway":
        return bad, ("\u4e22\u5305\u5728 L1(\u672c\u673a\u5230\u7f51\u5173): \u95ee\u9898\u5728**\u672c\u673a\u4fa7**\uff0c"
                     "\u5305\u62ec\u7f51\u5361\u3001\u7ebf\u7f06\u3001\u4ea4\u6362\u673a\u7aef\u53e3\u3001\u7f51\u5361\u961f\u5217\u4e22\u5305\u3002"
                     "\u4e0d\u8981\u5f80\u540e\u731c\u8fd0\u8425\u5546")
    if bad == "public":
        if got.get("target") is None:
            return bad, ("\u4e22\u5305\u5728 L2(\u5230\u516c\u7f51\u53c2\u7167)\u4e14\u65e0\u76ee\u6807\u6570\u636e: "
                         "\u95ee\u9898\u5728\u672c\u5730\u51fa\u53e3\u8bbe\u5907\u6216\u4e0a\u884c\u94fe\u8def\uff0c\u5c1a\u672a\u9a8c\u8bc1\u5230\u76ee\u6807\u4fa7")
        tv = got.get("target")
        pv = got.get("public")
        if tv is not None and tv - (pv or 0) < 1:
            return bad, ("\u4e22\u5305\u5728 L2(\u672c\u5730\u51fa\u53e3\u6bb5)\uff0c\u76ee\u6807\u4e22\u5305\u4e0e\u516c\u7f51\u53c2\u7167\u63a5\u8fd1: "
                         "\u95ee\u9898\u5728\u672c\u5730\u51fa\u53e3\u8bbe\u5907\u6216\u8fd0\u8425\u5546\u63a5\u5165\u6bb5")
        return bad, ("\u4e22\u5305\u5728 L2: \u516c\u7f51\u53c2\u7167\u4e22\u5305\u4f4e\u4e8e\u76ee\u6807\uff0c"
                     "\u95ee\u9898\u66f4\u53ef\u80fd\u5728\u8fd0\u8425\u5546\u9aa8\u5e72\u6216\u76ee\u6807\u4fa7")
    tv = got.get("target")
    pv = got.get("public")
    if tv is not None and pv is not None:
        if tv - pv >= 1:
            return "target", ("\u4e22\u5305\u5728 L4(\u76ee\u6807\u4fa7): \u516c\u7f51\u53c2\u7167 %.1f%% \u6b63\u5e38\u800c\u76ee\u6807 %.1f%% \u4e22\u5305\uff0c"
                              "\u95ee\u9898\u5728\u76ee\u6807\u7f51\u7edc\u6216\u76ee\u6807\u4e3b\u673a"
                              % (pv, tv))
        return "target", ("\u4e22\u5305\u5728 L3/L4: \u516c\u7f51\u53c2\u7167 %.1f%% \u4e0e\u76ee\u6807 %.1f%% \u63a5\u8fd1\uff0c"
                          "\u95ee\u9898\u5728\u8fd0\u8425\u5546\u9aa8\u5e72\u6216\u672c\u5730\u51fa\u53e3" % (pv, tv))
    return bad, "\u76ee\u6807\u4fa7\u4e22\u5305\u4f46\u7f3a\u5c11\u516c\u7f51\u53c2\u7167\uff0c\u65e0\u6cd5\u533a\u5206 L3 \u4e0e L4"


def business_impact(rate, icmp_limited, business_ok):
    """\u4e1a\u52a1\u5f71\u54cd\u5224\u5b9a\u3002"""
    g = grade_loss(rate)
    if g is None:
        return OK, "\u65e0\u4e22\u5305\u6570\u636e"
    if icmp_limited and business_ok:
        return (OK,
                "\u5df2\u786e\u8ba4\u8fd0\u8425\u5546\u9650\u901f ICMP \u4e14\u4e1a\u52a1\u4fa7\u5b9e\u6d4b\u6b63\u5e38: "
                "ping \u4e22\u5305\u4e0d\u7b49\u4e8e\u4e1a\u52a1\u4e22\u5305\uff0c\u65e0\u9700\u5904\u7406")
    if icmp_limited:
        return (WATCH,
                "\u5df2\u786e\u8ba4 ICMP \u9650\u901f\uff0c\u4f46\u672a\u63d0\u4f9b\u4e1a\u52a1\u4fa7\u9a8c\u8bc1: "
                "\u5fc5\u987b\u8865\u4e1a\u52a1\u4fa7\u8bc1\u636e\u624d\u80fd\u4e0b\u7ed3\u8bba")
    return g, "\u4e1a\u52a1\u5f71\u54cd\u6309\u4e22\u5305\u7387 %s \u5224\u5b9a" % ("%.1f%%" % rate)


def extra_alerts(got):
    outs = []
    j = got.get("jitter")
    if j is not None and j >= 100:
        outs.append(("\u6296\u52a8 %.0f ms \u504f\u5927: \u4e1a\u52a1\u4f53\u611f\u5e38\u6765\u81ea\u5ef6\u8fdf\u5206\u5e03\u5c3e\u90e8\u800c\u975e\u5e73\u5747\u503c\uff0c"
                     "\u5373\u4f7f\u4e22\u5305\u7387\u4e0d\u9ad8\u4e5f\u53ef\u80fd\u5361" % j, ALERT))
    tx = got.get("txdrop")
    if tx is not None and tx > 0:
        outs.append(("\u4e0a\u884c\u961f\u5217\u4e22\u5f03 %s \u4e2a/\u79d2: \u4e0a\u884c\u5e26\u5bbd\u6253\u6ee1\u5bfc\u81f4\u961f\u5217\u4e22\u5305\uff0c"
                     "\u8868\u73b0\u4e3a TCP \u91cd\u4f20\u5360\u5e26\u5bbd\u3001\u541e\u5410\u4e0b\u964d" % tx, ALERT))
    rx = got.get("rxdropped")
    if rx is not None and rx > 0:
        outs.append(("\u7f51\u5361 RX dropped \u589e\u901f %s \u4e2a/\u5206\u949f: "
                     "\u8fd9\u662f**\u5e94\u7528\u6536\u5305\u6162\u4e8e\u5185\u6838\u7f13\u51b2**\uff0c\u5c5e\u4e3b\u673a\u4fa7\u95ee\u9898\u800c\u975e\u94fe\u8def\u95ee\u9898" % rx, ALERT))
    if got.get("mtu_fail"):
        outs.append(("MTU \u63a2\u6d4b\u5931\u8d25: \u5b58\u5728 MTU \u9ed1\u6d1e\uff0c"
                     "\u5927\u5305\u4e0d\u901a\u800c\u5c0f\u5305\u6b63\u5e38\uff0cping \u770b\u7740\u6ca1\u95ee\u9898\u4f46\u4e1a\u52a1\u4e22\u5305", ALERT))
    mtr = got.get("mtr_loss")
    if mtr is not None and mtr > 0:
        if got.get("icmp_limited") and mtr >= 100:
            outs.append(("mtr \u67d0\u8df3 100% \u4e22\u5305\u4f46\u4e1a\u52a1\u6b63\u5e38: \u5178\u578b ICMP \u9650\u901f\uff0c"
                         "**\u4e0d\u8981\u62a5\u969c**\uff0c\u9700\u786e\u8ba4\u540e\u7eed\u8df3\u4e22\u5305\u7387", WATCH))
        else:
            outs.append(("mtr \u9996\u73b0\u4e22\u5305 %.1f%%: \u5224\u8bfb\u89c4\u5219\u662f\u770b\u540e\u7eed\u8df3\u4e22\u5305\u7387\u662f\u5426"
                         "\u76f8\u540c\u6216\u66f4\u9ad8\uff0c\u9012\u589e\u5904\u624d\u662f\u4e22\u5305\u70b9" % mtr, ALERT))
    if got.get("icmp_limited") and not got.get("business_ok"):
        outs.append(("\u5df2\u786e\u8ba4 ICMP \u9650\u901f\u4f46\u7f3a\u5c11\u4e1a\u52a1\u4fa7\u6570\u636e: "
                     "\u8865\u4e1a\u52a1\u4fa7\u9a8c\u8bc1\u540e\u518d\u5b9a\u8bba\uff0c\u5426\u5219\u7ed3\u8bba\u4e0d\u53ef\u7528", WARN))
    if got.get("_bad"):
        outs.append(("\u6709 %d \u9879\u6570\u503c\u65e0\u6cd5\u89e3\u6790(\u8bb0\u4e3a\u91c7\u96c6\u5931\u8d25\uff0c\u4e0d\u80fd\u6309 0 \u5904\u7406): %s"
                     % (len(got["_bad"]), ", ".join(got["_bad"])), ALERT))
    if not [k for k in got if k != "_bad"]:
        outs.append(("\u672a\u63d0\u4f9b\u4efb\u4f55\u6709\u6548\u89c2\u6d4b\u6570\u636e: "
                     "\u6392\u67e5\u5fc5\u987b\u4ece L0 \u5f00\u59cb\uff0c"
                     "\u4e0d\u6d4b\u7f51\u5173\u5c31\u65e0\u6cd5\u533a\u5206"
                     "\u672c\u673a\u95ee\u9898\u4e0e\u8fd0\u8425\u5546\u95ee\u9898", ALERT))
    return outs


def next_steps(layer, target, gateway):
    g = gateway or "<GATEWAY>"
    t = target or "<TARGET>"
    cmds = []
    if layer == "loopback":
        cmds = ["ip -br a", "ip -s link show lo",
                "ethtool -S eth0 2>/dev/null | grep -i drop"]
    elif layer == "gateway":
        cmds = ["ip -s link show eth0",
                "ethtool -S eth0 | grep -iE 'drop|crc|error'",
                "cat /proc/net/dev | awk '/eth0/'",
                "ping -c 100 -i 0.1 %s" % g]
    elif layer == "public":
        cmds = ["ping -c 100 -i 0.1 223.5.5.5",
                "sar -n DEV 1 10",
                "iftop -i eth0 -n -c 30",
                "mtr -r -c 100 -n -b %s" % t]
    elif layer == "target":
        cmds = ["ping -c 100 -i 0.1 %s" % t,
                "mtr -r -c 100 -n -b %s" % t,
                "traceroute -n -T -p 443 %s" % t,
                "ping -M do -s 1472 -c 5 %s" % t]
    else:
        cmds = ["ping -c 100 -i 0.1 %s" % g,
                "ping -c 100 -i 0.1 %s" % t,
                "mtr -r -c 100 -n -b %s" % t]
    return cmds


def build(got, target, gateway):
    layer, why = locate(got)
    rate = None
    if layer:
        rate = got.get(layer)
    if rate is None:
        for k in ("gateway", "public", "target", "loopback"):
            if got.get(k) is not None:
                rate = got[k]
                break
    impact, impact_why = business_impact(
        rate, bool(got.get("icmp_limited")), bool(got.get("business_ok")))
    alerts = extra_alerts(got)
    worst = impact
    for _t, lv in alerts:
        if LEVEL_ORDER.get(lv, 0) > LEVEL_ORDER.get(worst, 0):
            worst = lv
    return {
        "layer": layer or "\u672a\u5b9a\u4f4d",
        "layer_why": why,
        "loss_rate": rate,
        "impact": impact,
        "impact_why": impact_why,
        "overall": worst,
        "alerts": [{"text": t, "level": lv} for t, lv in alerts],
        "next_cmds": next_steps(layer, target, gateway),
        "evidence": EVIDENCE,
        "observed": got,
    }


def render_md(r, target, gateway):
    L = []
    L.append("# \u7f51\u7edc\u4e22\u5305\u5206\u5c42\u5b9a\u4f4d\u62a5\u544a")
    L.append("")
    L.append("- \u76ee\u6807: %s" % (target or "\u672a\u6307\u5b9a"))
    L.append("- \u7f51\u5173: %s" % (gateway or "\u672a\u6307\u5b9a"))
    L.append("- \u7efc\u5408\u7b49\u7ea7: **%s**" % r["overall"])
    L.append("- \u5b9a\u4f4d\u5c42: **%s**" % r["layer"])
    L.append("")
    L.append("## \u4e00 \u89c2\u6d4b\u6570\u636e")
    L.append("")
    L.append("| \u5c42/\u9879 | \u540d\u79f0 | \u5b9e\u6d4b |")
    L.append("|---|---|---|")
    for key, cn, _c in LAYERS:
        v = r["observed"].get(key)
        L.append("| %s | %s | %s |" % (key, cn,
                 "\u672a\u91c7\u96c6" if v is None else "%.2f%%" % v))
    for key in sorted(EXTRA.keys()):
        if key in r["observed"]:
            v = r["observed"][key]
            cn, unit = EXTRA[key]
            L.append("| %s | %s | %s |" % (key, cn,
                     ("%.2f %s" % (v, unit)) if isinstance(v, float) else str(v)))
    if r["observed"].get("_bad"):
        L.append("| _bad | \u91c7\u96c6\u5931\u8d25\u9879 | %s |"
                 % ", ".join(r["observed"]["_bad"]))
    L.append("")
    L.append("## \u4e8c \u5b9a\u4f4d\u7ed3\u8bba")
    L.append("")
    L.append("- \u5b9a\u4f4d\u5c42: %s" % r["layer"])
    L.append("- \u5224\u5b9a: %s" % r["layer_why"])
    L.append("- \u4e1a\u52a1\u5f71\u54cd\u7b49\u7ea7: %s" % r["impact"])
    L.append("- \u5f71\u54cd\u8bf4\u660e: %s" % r["impact_why"])
    L.append("")
    if r["alerts"]:
        L.append("## \u4e09 \u9644\u52a0\u5224\u8bfb")
        L.append("")
        for a in r["alerts"]:
            L.append("- **[%s]** %s" % (a["level"], a["text"]))
        L.append("")
    L.append("## \u56db \u4e0b\u4e00\u6b65\u547d\u4ee4")
    L.append("")
    for c in r["next_cmds"]:
        L.append("```bash\n%s\n```" % c)
    L.append("")
    L.append("## \u4e94 \u62a5\u969c\u6216\u5347\u7ea7\u524d\u7684\u53d6\u8bc1\u6e05\u5355")
    L.append("")
    for e in r["evidence"]:
        L.append("- [ ] %s" % e)
    L.append("")
    L.append("---")
    L.append("")
    L.append("> \u811a\u672c\u53ea\u5f52\u62e2\u4f60\u5df2\u89c2\u6d4b\u5230\u7684\u6570\u636e\uff0c\u4e0d\u53d1\u8d77\u4efb\u4f55\u7f51\u7edc\u8bf7\u6c42\u3002"
             "\u7f3a\u4efb\u4f55\u4e00\u5c42\u7684\u89c2\u6d4b\u6570\u636e\u65f6\uff0c\u7ed3\u8bba\u53ea\u80fd\u5b9a\u4f4d\u5230\u5df2\u6709\u6570\u636e\u7684\u8fb9\u754c\u3002")
    return "\n".join(L) + "\n"


SAMPLE_ALL_OK = """# \u56db\u5c42\u5168\u90e8\u6b63\u5e38
loopback|0
gateway|0
public|0
target|0
"""

SAMPLE_L1 = """# \u672c\u673a\u5230\u7f51\u5173\u4e22\u5305
loopback|0
gateway|3.5
public|0
target|0
"""

SAMPLE_L4 = """# \u53ea\u6709\u76ee\u6807\u4e22\u5305
loopback|0
gateway|0
public|0.2
target|8
"""

SAMPLE_ICMP = """# \u8fd0\u8425\u5546\u9650\u901f ICMP \u4f46\u4e1a\u52a1\u6b63\u5e38
loopback|0
gateway|0
public|0
target|4
icmp_limited|1
business_ok|1
"""

SAMPLE_MIX = """# \u591a\u79cd\u53e0\u52a0
loopback|0
gateway|12
public|15
target|18
jitter|180
txdrop|50
mtu_fail|1
"""

SAMPLE_EMPTY = """# \u53ea\u6709\u6ce8\u91ca
# nothing here
"""

SAMPLE_JUNK = """\u8fd9\u884c\u6ca1\u6709\u5206\u9694\u7b26
foo|bar
gateway|abc
public|2.5
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

    # 1. \u522b\u540d\u89e3\u6790
    ck("alias_cn", resolve("\u7f51\u5173"), "gateway")
    ck("alias_en", resolve("gateway"), "gateway")
    ck("alias_unknown", resolve("\u4e0d\u5b58\u5728\u7684\u5c42"), None)
    ck("norm_underscore", resolve("rx_dropped"), "rxdropped")

    # 2. \u4e22\u5305\u7387\u5206\u7ea7
    ck("g_0", grade_loss(0), OK)
    ck("g_05", grade_loss(0.5), OK)
    ck("g_1", grade_loss(1), WATCH)
    ck("g_3", grade_loss(3), ALERT)
    ck("g_8", grade_loss(8), CRITICAL)
    ck("g_12", grade_loss(12), FAULT)
    ck("g_none", grade_loss(None), None)

    # 3. \u89e3\u6790
    g = parse(SAMPLE_L1)
    ck("parse_gateway", g.get("gateway"), 3.5)
    ck("parse_loopback", g.get("loopback"), 0.0)
    ck("parse_empty", parse(SAMPLE_EMPTY), {})
    gj = parse(SAMPLE_JUNK)
    ck("parse_junk_skip", gj.get("public"), 2.5)
    ck("parse_junk_badval", "gateway" in gj, False)

    # 4. \u5b9a\u4f4d\uff1a\u5168\u90e8\u6b63\u5e38
    gall = parse(SAMPLE_ALL_OK)
    lay, why = locate(gall)
    ck("loc_all_none", lay, None)
    ck("loc_all_why", "\u4e0d\u5728 IP \u5c42\u4e22\u5305" in why, True)

    # 5. \u5b9a\u4f4d\uff1aL1 \u4e22\u5305\uff08\u5173\u952e\uff1a\u4e0d\u5f97\u6307\u5411\u8fd0\u8425\u5546\uff09
    r1 = build(g, "example.com", "192.168.1.1")
    ck("loc_l1", r1["layer"], "gateway")
    ck("loc_l1_says_host", "\u672c\u673a\u4fa7" in r1["layer_why"], True)
    ck("loc_l1_not_isp", "\u4e0d\u8981\u5f80\u540e\u731c\u8fd0\u8425\u5546" in r1["layer_why"], True)
    ck("loc_l1_impact", r1["impact"], ALERT)
    ck("loc_l1_cmds_have_ethtool",
       any("ethtool" in c for c in r1["next_cmds"]), True)

    # 6. \u5b9a\u4f4d\uff1aL4 \u4e22\u5305
    r4 = build(parse(SAMPLE_L4), "example.com", "192.168.1.1")
    ck("loc_l4", r4["layer"], "target")
    ck("loc_l4_says_target", "\u76ee\u6807" in r4["layer_why"], True)
    ck("loc_l4_impact", r4["impact"], CRITICAL)
    ck("loc_l4_mtu_cmd", any("-M do" in c for c in r4["next_cmds"]), True)

    # 7. ICMP \u9650\u901f\u4e14\u4e1a\u52a1\u6b63\u5e38 -> \u4e0d\u5e94\u5224\u4e3a\u6545\u969c
    r3 = build(parse(SAMPLE_ICMP), "example.com", "192.168.1.1")
    ck("icmp_biz_ok", r3["impact"], OK)
    ck("icmp_note", "ping \u4e22\u5305\u4e0d\u7b49\u4e8e\u4e1a\u52a1\u4e22\u5305" in r3["impact_why"], True)

    # 8. ICMP \u9650\u901f\u4f46\u65e0\u4e1a\u52a1\u9a8c\u8bc1 -> \u53ea\u7ed9\u5173\u6ce8
    r3b = dict(parse(SAMPLE_ICMP))
    r3b.pop("business_ok")
    r3c = build(r3b, "example.com", "192.168.1.1")
    ck("icmp_no_biz", r3c["impact"], WATCH)
    ck("icmp_no_biz_note", "\u5fc5\u987b\u8865\u4e1a\u52a1\u4fa7\u8bc1\u636e" in r3c["impact_why"], True)

    # 9. \u591a\u56e0\u7d20\u53e0\u52a0 -> \u6545\u969c\u7ea7 + \u6296\u52a8/\u961f\u5217/MTU \u63d0\u793a
    r5 = build(parse(SAMPLE_MIX), "example.com", "192.168.1.1")
    ck("mix_overall", r5["overall"], FAULT)
    ck("mix_layer", r5["layer"], "gateway")
    texts = " ".join(a["text"] for a in r5["alerts"])
    ck("mix_jitter", "\u6296\u52a8" in texts, True)
    ck("mix_txdrop", "\u4e0a\u884c\u961f\u5217\u4e22\u5f03" in texts, True)
    ck("mix_mtu", "MTU \u9ed1\u6d1e" in texts, True)

    # 10. mtr 100% \u4e22\u5305 + ICMP \u9650\u901f -> \u4e0d\u8be5\u5224\u4e3a\u544a\u8b66
    gm = dict(parse(SAMPLE_ICMP))
    gm["mtr_loss"] = 100.0
    rm = build(gm, "example.com", None)
    mtexts = " ".join(a["text"] for a in rm["alerts"])
    ck("mtr_100_icmp", "\u4e0d\u8981\u62a5\u969c" in mtexts, True)

    # 11. RX dropped \u5224\u5b9a\u4e3a\u4e3b\u673a\u4fa7
    gr = dict(parse(SAMPLE_L4))
    gr["rxdropped"] = 300.0
    rr = build(gr, "example.com", None)
    ck("rx_host_side",
       "\u4e3b\u673a\u4fa7\u95ee\u9898" in " ".join(a["text"] for a in rr["alerts"]), True)

    # 12. \u7a7a\u6570\u636e\u5fc5\u987b\u544a\u8b66
    r0 = build(parse(SAMPLE_EMPTY), "example.com", None)
    ck("empty_layer", r0["layer"], "\u672a\u5b9a\u4f4d")
    ck("empty_alert", r0["overall"], ALERT)
    ck("empty_note", "\u4ece L0 \u5f00\u59cb" in " ".join(
        a["text"] for a in r0["alerts"]), True)

    # 13. \u6e32\u67d3\u4e0e\u53d6\u8bc1\u6e05\u5355
    md = render_md(r1, "example.com", "192.168.1.1")
    ck("md_header", md.startswith("# "), True)
    ck("md_has_evidence", "\u53d6\u8bc1\u6e05\u5355" in md, True)
    ck("md_evidence_len", len(EVIDENCE) >= 9, True)
    ck("md_has_cmds", "```bash" in md, True)
    js = json.loads(json.dumps(r1, ensure_ascii=False))
    ck("json_keys_min", "layer" in js and "next_cmds" in js, True)

    # 14. \u5206\u5c42\u987a\u5e8f\uff1aL1 \u7ea2\u65f6\u4e0d\u5f97\u8df3\u5230 L2 \u7ed3\u8bba
    g_both = dict(parse(SAMPLE_L1))
    g_both["target"] = 9.0
    r6 = build(g_both, "example.com", None)
    ck("priority_l1_first", r6["layer"], "gateway")

    for line in res:
        print(line)
    print("SELFTEST %s (%d assertions)" % ("OK" if ok else "FAILED", len(res)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--target", default="")
    ap.add_argument("--gateway", default="")
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
    got = parse(text)
    r = build(got, a.target, a.gateway)
    body = (render_md(r, a.target, a.gateway) if a.format == "md"
            else json.dumps(r, ensure_ascii=False, indent=2))
    if a.out:
        open(a.out, "w", encoding="utf-8").write(body)
        print("WROTE %s" % a.out)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())