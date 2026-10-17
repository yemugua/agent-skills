# -*- coding: utf-8 -*-
"""\u5907\u4efd\u7b56\u7565\u5408\u89c4\u6821\u9a8c\uff1aRPO/RTO \u4e0e\u9891\u7387\u5339\u914d\u30013-2-1-1-0\u3001\u516d\u5c42\u6709\u6548\u6027\u3001\u6f14\u7ec3\u5468\u671f\u3002

\u7528\u6cd5:
  python backup_policy_check.py --file policy.txt --tier 1
  python backup_policy_check.py --file policy.txt --tier 3 --json
  python backup_policy_check.py --selftest
"""
import argparse
import json
import os
import re
import sys

PASS = "\u901a\u8fc7"
FAIL = "\u4e0d\u5408\u89c4"
WARN = "\u9700\u786e\u8ba4"

LEVEL_ORDER = {PASS: 0, WARN: 1, FAIL: 2}

# \u5206\u7ea7 -> (RPO \u4e0a\u754c\u5206\u949f, RTO \u4e0a\u754c\u5206\u949f, \u6f14\u7ec3\u5468\u671f\u5929\u6570, \u5206\u7ea7\u540d)
TIERS = {
    1: (5, 60, 90, "\u4e00\u7ea7 \u6838\u5fc3\u4ea4\u6613"),
    2: (60, 240, 180, "\u4e8c\u7ea7 \u91cd\u8981\u4e1a\u52a1"),
    3: (1440, 1440, 365, "\u4e09\u7ea7 \u4e00\u822c\u4e1a\u52a1"),
    4: (10080, 4320, 0, "\u56db\u7ea7 \u53ef\u91cd\u5efa"),
}

# \u9891\u7387 -> \u80fd\u8fbe\u5230\u7684\u6700\u5c0f RPO\uff08\u5206\u949f\uff09\u30020 \u8868\u793a\u53ef\u6ee1\u8db3 5 \u5206\u949f\u7ea7 RPO\u3002
FREQ_RPO = {
    "continuous": 0,
    "realtime": 0,
    "streaming": 0,
    "hourly": 60,
    "daily": 1440,
    "weekly": 10080,
    "monthly": 43200,
}

FREQ_CN = {
    "continuous": "\u5b9e\u65f6/\u8fde\u7eed",
    "realtime": "\u5b9e\u65f6",
    "streaming": "\u6d41\u5f0f",
    "hourly": "\u6bcf\u5c0f\u65f6",
    "daily": "\u6bcf\u65e5",
    "weekly": "\u6bcf\u5468",
    "monthly": "\u6bcf\u6708",
}

# \u516d\u5c42\u6709\u6548\u6027\u6821\u9a8c
VERIFY_LAYERS = [
    ("verify_l1", "L1 \u4efb\u52a1\u7ea7\u6821\u9a8c", "\u4efb\u52a1\u9000\u51fa\u7801\u4e0e\u8c03\u5ea6\u72b6\u6001"),
    ("verify_l2", "L2 \u5b58\u5728\u7ea7\u6821\u9a8c", "\u6587\u4ef6\u5b58\u5728\u3001\u5927\u5c0f\u5927\u4e8e 0\u3001\u65f6\u95f4\u6233\u6b63\u786e"),
    ("verify_l3", "L3 \u5b8c\u6574\u6027\u7ea7\u6821\u9a8c", "\u6821\u9a8c\u548c\u6bd4\u5bf9\u3001\u5f52\u6863\u53ef\u89e3\u5305"),
    ("verify_l4", "L4 \u903b\u8f91\u7ea7\u6821\u9a8c", "\u53ef\u5bfc\u5165\u7a7a\u5e93\u3001\u8868\u6570\u4e0e\u884c\u6570\u5408\u7406"),
    ("verify_l5", "L5 \u4e1a\u52a1\u7ea7\u6062\u590d\u9a8c\u8bc1", "\u6062\u590d\u6d4b\u8bd5\u73af\u5883\u5e76\u8dd1\u901a\u5173\u952e\u6d41\u7a0b"),
    ("verify_l6", "L6 \u5f02\u5730\u6062\u590d\u6f14\u7ec3", "\u5f02\u5730\u6062\u590d\u4e0e\u707e\u96be\u573a\u666f\u5207\u6362"),
]

BOOL_KEYS = ("copies", "media", "offsite", "immutable",
             "credential_isolated", "monitoring", "trend_monitor",
             "verify_l1", "verify_l2", "verify_l3", "verify_l4",
             "verify_l5", "verify_l6")

INT_KEYS = ("rpo_minutes", "rto_minutes", "last_drill_days")

DEFAULTS = {
    "copies": 1, "media": 1, "offsite": 0, "immutable": 0,
    "credential_isolated": 0, "monitoring": 0, "trend_monitor": 0,
    "verify_l1": 0, "verify_l2": 0, "verify_l3": 0, "verify_l4": 0,
    "verify_l5": 0, "verify_l6": 0,
    "rpo_minutes": 10080, "rto_minutes": 10080, "last_drill_days": 99999,
    "frequency": "weekly",
}


def parse(text):
    got = {}
    for ln in (text or "").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or ln.startswith("//"):
            continue
        parts = re.split(r"[|:=]", ln, maxsplit=1)
        if len(parts) < 2:
            continue
        k = parts[0].strip().lower()
        v = parts[1].strip()
        if k in BOOL_KEYS or k in INT_KEYS:
            try:
                got[k] = int(float(v))
            except (TypeError, ValueError):
                continue
        elif k == "frequency":
            f = v.lower()
            if f in FREQ_RPO:
                got[k] = f
    data = dict(DEFAULTS)
    data.update(got)
    return data, got


def check_32110(d):
    rows = []
    rows.append(("3 \u526f\u672c", d["copies"],
                 PASS if d["copies"] >= 3 else FAIL,
                 "\u526f\u672c\u6570 %d\uff0c\u8981\u6c42\u81f3\u5c11 3" % d["copies"]))
    rows.append(("2 \u4ecb\u8d28", d["media"],
                 PASS if d["media"] >= 2 else FAIL,
                 "\u5b58\u50a8\u7c7b\u578b\u6570 %d\uff0c\u8981\u6c42\u81f3\u5c11 2\uff0c\u4e14\u4e0d\u80fd\u662f\u540c\u76d8\u53cc RAID" % d["media"]))
    rows.append(("1 \u5f02\u5730", d["offsite"],
                 PASS if d["offsite"] >= 1 else FAIL,
                 "\u5f02\u5730\u526f\u672c\u6570 %d\uff0c\u8981\u6c42\u81f3\u5c11 1" % d["offsite"]))
    rows.append(("+1 \u4e0d\u53ef\u53d8", d["immutable"],
                 PASS if d["immutable"] >= 1 else FAIL,
                 "\u4e0d\u53ef\u53d8\u6216\u79bb\u7ebf\u526f\u672c\u6570 %d\u3002\u539f\u59cb 3-2-1 \u4e0d\u89e3\u51b3\u52d2\u7d22\u8f6f\u4ef6"
                 "\u540c\u6b65\u52a0\u5bc6\u5907\u4efd\u7684\u95ee\u9898\uff0c\u6b64\u9879\u7f3a\u5931\u5373\u4e3a\u9ad8\u98ce\u9669" % d["immutable"]))
    rows.append(("+0 \u96f6\u9519\u8bef", 1 if d["verify_l5"] or d["verify_l6"] else 0,
                 PASS if (d["verify_l5"] or d["verify_l6"]) else FAIL,
                 "\u53ea\u6709\u505a\u8fc7 L5 \u4e1a\u52a1\u7ea7\u6062\u590d\u9a8c\u8bc1\u6216 L6 \u5f02\u5730\u6f14\u7ec3\uff0c"
                 "\u624d\u8c08\u5f97\u4e0a\u5907\u4efd\u6709\u6548\uff1b\u4ec5 L1-L4 \u4e0d\u8db3\u4ee5\u652f\u6491\u300c\u5907\u4efd\u6709\u6548\u300d\u7684\u7ed3\u8bba"))
    rows.append(("\u51ed\u636e\u9694\u79bb", d["credential_isolated"],
                 PASS if d["credential_isolated"] else FAIL,
                 "\u5907\u4efd\u51ed\u636e\u672a\u4e0e\u751f\u4ea7\u9694\u79bb\u65f6\uff0c\u751f\u4ea7\u57df\u88ab\u5165\u4fb5\u4f1a\u540c\u6b65\u5220\u9664\u6216\u52a0\u5bc6\u5907\u4efd"))
    return rows


def check_rpo_frequency(d):
    """\u6838\u58f0\u660e RPO \u4e0e\u5907\u4efd\u9891\u7387\u662f\u5426\u81ea\u6d3d\u3002"""
    freq = d["frequency"]
    freq_rpo = FREQ_RPO.get(freq)
    rpo = d["rpo_minutes"]
    if freq_rpo is None:
        return FAIL, ("\u9891\u7387 %s \u672a\u8bc6\u522b\uff0c\u65e0\u6cd5\u5224\u5b9a RPO \u53ef\u8fbe\u6027" % freq)
    if freq_rpo == 0:
        return PASS, ("\u58f0\u660e RPO %d \u5206\u949f\uff0c\u5907\u4efd\u9891\u7387 %s"
                      "\uff08\u540c\u6b65\u590d\u5236\u6216\u5b9e\u65f6\u65e5\u5fd7\u5f52\u6863\uff09\uff0c"
                      "\u53ef\u8fbe\u5206\u949f\u7ea7 RPO" % (rpo, FREQ_CN[freq]))
    if freq_rpo <= rpo:
        return PASS, ("\u58f0\u660e RPO %d \u5206\u949f\uff0c\u5907\u4efd\u9891\u7387 %s"
                      "\uff08\u5b9e\u9645\u6700\u5dee\u4e22\u5931\u7a97\u53e3 %d \u5206\u949f\uff09\uff0c"
                      "\u5907\u4efd\u9891\u7387\u8db3\u4ee5\u652f\u6491\u8be5 RPO"
                      % (rpo, FREQ_CN[freq], freq_rpo))
    if freq_rpo <= rpo * 2:
        return WARN, ("\u58f0\u660e RPO %d \u5206\u949f\uff0c\u4f46\u5907\u4efd\u9891\u7387 %s"
                      "\u7684\u6700\u5dee\u4e22\u5931\u7a97\u53e3\u662f %d \u5206\u949f\uff0c"
                      "\u5b58\u5728\u7f3a\u53e3\u3002\u5efa\u8bae\u63d0\u9ad8\u9891\u7387"
                      "\u6216\u6539\u7528\u540c\u6b65\u590d\u5236/\u65e5\u5fd7\u5f52\u6863"
                      % (rpo, FREQ_CN[freq], freq_rpo))
    return FAIL, ("\u58f0\u660e RPO %d \u5206\u949f\uff0c\u4f46\u5907\u4efd\u9891\u7387\u53ea\u6709 %s"
                  "\uff08\u6700\u5dee\u4e22\u5931\u7a97\u53e3 %d \u5206\u949f\uff09\uff0c"
                  "**\u5b9a\u65f6\u5907\u4efd\u65e0\u6cd5\u7a81\u7834\u9891\u7387\u9650\u5236**\uff0c"
                  "\u8be5 RPO \u4e0d\u53ef\u8fbe"
                  % (rpo, FREQ_CN[freq], freq_rpo))


def check_tier(d, tier):
    rpo_max, rto_max, drill_days, tier_name = TIERS[tier]
    rows = []
    if d["rpo_minutes"] <= rpo_max:
        rows.append(("RPO", PASS,
                     "\u58f0\u660e %d \u5206\u949f\uff0c\u4e0a\u9650 %d \u5206\u949f"
                     % (d["rpo_minutes"], rpo_max)))
    else:
        rows.append(("RPO", FAIL,
                     "\u58f0\u660e %d \u5206\u949f\uff0c\u8d85\u51fa %s \u7684 %d \u5206\u949f\u4e0a\u9650"
                     % (d["rpo_minutes"], tier_name, rpo_max)))
    if d["rto_minutes"] <= rto_max:
        rows.append(("RTO", PASS,
                     "\u58f0\u660e %d \u5206\u949f\uff0c\u4e0a\u9650 %d \u5206\u949f"
                     % (d["rto_minutes"], rto_max)))
    else:
        rows.append(("RTO", FAIL,
                     "\u58f0\u660e %d \u5206\u949f\uff0c\u8d85\u51fa %s \u7684 %d \u5206\u949f\u4e0a\u9650"
                     % (d["rto_minutes"], tier_name, rto_max)))
    lv, note = check_rpo_frequency(d)
    rows.append(("RPO \u4e0e\u9891\u7387\u5339\u914d", lv, note))
    if drill_days == 0:
        rows.append(("\u6f14\u7ec3\u5468\u671f", PASS, "\u8be5\u5206\u7ea7\u53ef\u968f\u53d1\u5e03\u9a8c\u8bc1\uff0c\u4e0d\u5f3a\u5236\u5468\u671f"))
    elif d["last_drill_days"] <= drill_days:
        rows.append(("\u6f14\u7ec3\u5468\u671f", PASS,
                     "\u8ddd\u4e0a\u6b21\u6f14\u7ec3 %d \u5929\uff0c\u5468\u671f\u4e0a\u9650 %d \u5929"
                     % (d["last_drill_days"], drill_days)))
    else:
        rows.append(("\u6f14\u7ec3\u5468\u671f", FAIL,
                     "\u8ddd\u4e0a\u6b21\u6f14\u7ec3 %d \u5929\uff0c\u8d85\u8fc7 %d \u5929\u4e0a\u9650\u3002"
                     "\u4ece\u672a\u6062\u590d\u9a8c\u8bc1\u7684\u5907\u4efd\u5e94\u6309\u300c\u5907\u4efd\u4e0d\u53ef\u7528\u300d\u5904\u7406"
                     % (d["last_drill_days"], drill_days)))
    return rows


def check_layers(d):
    rows = []
    for key, cn, how in VERIFY_LAYERS:
        ok = bool(d[key])
        rows.append((cn, PASS if ok else WARN,
                     ("\u5df2\u914d\u7f6e: %s" % how) if ok
                     else ("\u672a\u914d\u7f6e: %s\u3002\u8fd9\u662f\u6700\u5e38\u89c1\u7684\u5047\u6709\u6548\u6765\u6e90\uff0c"
                           "\u53ea\u505a\u524d\u51e0\u5c42\u4e0d\u80fd\u8bc1\u660e\u5907\u4efd\u53ef\u6062\u590d" % how)))
    if not d["verify_l5"] and not d["verify_l6"]:
        rows.append(("\u6709\u6548\u6027\u7ed3\u8bba", FAIL,
                     "L5 \u4e0e L6 \u5747\u672a\u914d\u7f6e: \u5728\u6ca1\u6709\u505a\u8fc7\u4e00\u6b21\u6062\u590d\u9a8c\u8bc1\u4e4b\u524d\uff0c"
                     "\u4e0d\u5f97\u5bf9\u5916\u58f0\u79f0\u5907\u4efd\u6709\u6548"))
    return rows


def check_monitoring(d):
    rows = []
    if d["monitoring"]:
        rows.append(("\u5907\u4efd\u5931\u8d25\u544a\u8b66", PASS,
                     "\u5df2\u914d\u7f6e\u76d1\u63a7\u3002\u6ce8\u610f\uff1a\u914d\u7f6e\u4e86\u4e0d\u7b49\u4e8e\u6709\u6548\uff0c"
                     "\u5fc5\u987b\u6f14\u7ec3\u4e00\u6b21\u771f\u5b9e\u5931\u8d25\u9a8c\u8bc1\u80fd\u5426\u5230\u4eba"))
    else:
        rows.append(("\u5907\u4efd\u5931\u8d25\u544a\u8b66", FAIL, "\u672a\u914d\u7f6e\u5907\u4efd\u5931\u8d25\u544a\u8b66\u5230\u4eba"))
    if d["trend_monitor"]:
        rows.append(("\u5907\u4efd\u5927\u5c0f\u8d8b\u52bf", PASS,
                     "\u5df2\u914d\u7f6e\u8d8b\u52bf\u76d1\u63a7\uff0c\u5efa\u8bae\u5f02\u5e38\u9608\u503c\u8bbe\u4e3a\u65e5\u73af\u6bd4\u53d8\u5316\u8d85\u8fc7 20%%"))
    else:
        rows.append(("\u5907\u4efd\u5927\u5c0f\u8d8b\u52bf", FAIL,
                     "\u672a\u914d\u7f6e\u8d8b\u52bf\u76d1\u63a7\u3002\u8fde\u7eed\u4e09\u5929\u5927\u5c0f\u53d8\u5316\u8d85\u8fc7 20%% \u662f\u5f3a\u4fe1\u53f7\uff0c"
                     "\u5373\u4f7f\u6821\u9a8c\u548c\u901a\u8fc7\u4e5f\u5e94\u4eba\u5de5\u786e\u8ba4"))
    return rows


def build(text, tier):
    d, raw = parse(text)
    rows = []
    rows += [("\u843d\u5b9e 3-2-1-1-0", n, lv, note)
             for n, v, lv, note in check_32110(d)]
    rows += [("\u5206\u7ea7\u8981\u6c42", n, lv, note) for n, lv, note in check_tier(d, tier)]
    rows += [("\u6709\u6548\u6027\u6821\u9a8c", n, lv, note) for n, lv, note in check_layers(d)]
    rows += [("\u76d1\u63a7", n, lv, note) for n, lv, note in check_monitoring(d)]
    if not raw:
        rows.append(("\u8f93\u5165\u89e3\u6790", "\u8f93\u5165\u89e3\u6790", FAIL,
                     "\u7b56\u7565\u6587\u4ef6\u672a\u89e3\u6790\u5230\u4efb\u4f55\u6709\u6548\u952e\u503c\uff0c\u65e0\u6cd5\u6838\u67e5"))
    levels = [r[2] for r in rows]
    lv = PASS
    for x in levels:
        if LEVEL_ORDER.get(x, 0) > LEVEL_ORDER.get(lv, 0):
            lv = x
    rpo_max, rto_max, drill_days, tier_name = TIERS[tier]
    return {
        "tier": tier,
        "tier_name": tier_name,
        "overall": lv,
        "parsed_keys": len(raw),
        "data": d,
        "rows": [{"group": g, "name": n, "level": l, "note": note}
                 for g, n, l, note in rows],
        "tier_limits": {"rpo_max": rpo_max, "rto_max": rto_max,
                        "drill_days": drill_days},
    }


MANUAL = [
    "RPO/RTO \u662f\u5426\u5df2\u7ecf\u8fc7\u4e1a\u52a1\u65b9\u4e66\u9762\u786e\u8ba4\uff08\u6280\u672f\u4fa7\u4e0d\u80fd\u5355\u65b9\u9762\u51b3\u5b9a\uff09",
    "\u4e24\u7ea7\u4ecb\u8d28\u662f\u5426\u771f\u7684\u4e0d\u662f\u540c\u4e00\u5957\u7269\u7406\u76d8",
    "\u5f02\u5730\u526f\u672c\u7684\u7269\u7406\u4f4d\u7f6e\u662f\u5426\u4e66\u9762\u8bb0\u5f55\u4e14\u771f\u7684\u5f02\u5730",
    "\u4e0d\u53ef\u53d8\u526f\u672c\u662f\u5426\u88ab\u751f\u4ea7\u57df\u51ed\u636e\u8bbf\u95ee\u4e0d\u5230",
    "\u5907\u4efd\u544a\u8b66\u662f\u5426\u6f14\u7ec3\u8fc7\u771f\u5b9e\u5931\u8d25",
    "\u5907\u4efd\u5206\u533a\u5bb9\u91cf\u544a\u8b66\u662f\u5426\u751f\u6548",
    "L5 \u6062\u590d\u9a8c\u8bc1\u662f\u5426\u8986\u76d6\u4e86\u914d\u7f6e\u3001\u5bc6\u94a5\u4e0e\u4f9d\u8d56\u6e05\u5355",
    "\u7559\u5b58\u671f\u9650\u8981\u6c42\u6765\u6e90\uff08\u73b0\u884c\u89c4\u5b9a/\u884c\u4e1a\u89c4\u8303/\u672c\u5355\u4f4d\u5236\u5ea6\uff09",
]

CAVEAT = [
    "RPO/RTO \u5fc5\u987b\u7531\u4e1a\u52a1\u65b9\u4e66\u9762\u786e\u8ba4\uff0c\u811a\u672c\u53ea\u505a\u53e3\u5f84\u6838\u5bf9\uff0c\u4e0d\u4ee3\u66ff\u51b3\u7b56",
    "\u7559\u5b58\u671f\u9650\u4e0e\u6f14\u7ec3\u9891\u7387\u7684\u5177\u4f53\u8981\u6c42\u4ee5\u73b0\u884c\u89c4\u5b9a\u548c\u5f53\u5730\u4e3b\u7ba1\u90e8\u95e8\u8981\u6c42\u4e3a\u51c6",
    "\u53ea\u6709 L1-L4 \u901a\u8fc7\u4e0d\u80fd\u58f0\u79f0\u5907\u4efd\u6709\u6548\uff0c\u81f3\u5c11\u9700\u505a\u8fc7\u4e00\u6b21 L5 \u6062\u590d\u9a8c\u8bc1",
    "\u4efb\u4f55\u6062\u590d\u64cd\u4f5c\u5c24\u5176\u5728\u751f\u4ea7\u73af\u5883\u5fc5\u987b\u7ecf\u5ba1\u6279\u540e\u6267\u884c",
]


def render_md(r):
    L = []
    L.append("# \u5907\u4efd\u7b56\u7565\u6838\u67e5\u62a5\u544a")
    L.append("")
    L.append("- \u7cfb\u7edf\u5206\u7ea7: %s" % r["tier_name"])
    L.append("- \u7efc\u5408\u7ed3\u8bba: **%s**" % r["overall"])
    L.append("- \u89e3\u6790\u5230\u7684\u7b56\u7565\u9879: %d" % r["parsed_keys"])
    L.append("")
    L.append("## \u4e00 \u5206\u7ea7\u8981\u6c42\u5bf9\u7167")
    L.append("")
    tl = r["tier_limits"]
    L.append("| \u9879 | \u672c\u7ea7\u4e0a\u9650 |")
    L.append("|---|---|")
    L.append("| RPO | %d \u5206\u949f |" % tl["rpo_max"])
    L.append("| RTO | %d \u5206\u949f |" % tl["rto_max"])
    L.append("| \u6f14\u7ec3\u5468\u671f | %s |"
             % ("\u968f\u53d1\u5e03\u9a8c\u8bc1" if tl["drill_days"] == 0
                else "%d \u5929" % tl["drill_days"]))
    L.append("")
    L.append("## \u4e8c \u9010\u9879\u6838\u67e5")
    L.append("")
    L.append("| \u5206\u7ec4 | \u6838\u67e5\u9879 | \u5224\u5b9a | \u8bf4\u660e |")
    L.append("|---|---|---|---|")
    for it in r["rows"]:
        L.append("| %s | %s | %s | %s |"
                 % (it["group"], it["name"], it["level"], it["note"]))
    L.append("")
    L.append("## \u4e09 \u5fc5\u987b\u4eba\u5de5\u786e\u8ba4")
    L.append("")
    for t in MANUAL:
        L.append("- [ ] %s" % t)
    L.append("")
    L.append("## \u56db \u8fb9\u754c\u63d0\u793a")
    L.append("")
    for t in CAVEAT:
        L.append("- %s" % t)
    L.append("")
    L.append("---")
    L.append("")
    L.append("> \u811a\u672c\u53ea\u505a\u7b56\u7565\u6587\u672c\u7684\u53e3\u5f84\u6838\u5bf9\u3002\u5b83\u4e0d\u80fd\u9a8c\u8bc1\u5907\u4efd\u6587\u4ef6\u662f\u5426\u771f\u7684\u53ef\u7528\uff0c")
    L.append("> \u4e5f\u4e0d\u4f1a\u66ff\u4ee3\u771f\u5b9e\u7684\u6062\u590d\u6f14\u7ec3\u3002")
    return "\n".join(L) + "\n"


GOOD_T1 = """copies=3
media=2
offsite=1
immutable=1
credential_isolated=1
rpo_minutes=5
rto_minutes=60
frequency=continuous
verify_l1=1
verify_l2=1
verify_l3=1
verify_l4=1
verify_l5=1
verify_l6=1
last_drill_days=30
monitoring=1
trend_monitor=1
"""

BAD_RPO = """copies=3
media=2
offsite=1
immutable=1
rpo_minutes=5
rto_minutes=30
frequency=daily
verify_l1=1
verify_l2=1
verify_l3=1
verify_l4=1
"""

FAKE_BACKUP = """copies=2
media=1
offsite=0
immutable=0
credential_isolated=0
rpo_minutes=1440
rto_minutes=1440
frequency=daily
verify_l1=1
verify_l2=1
verify_l3=1
verify_l4=1
last_drill_days=400
monitoring=0
trend_monitor=0
"""

EDGE_GAP = """rpo_minutes=120
frequency=hourly
tier=2
"""

EMPTY = """# \u6ca1\u6709\u4efb\u4f55\u914d\u7f6e
"""

JUNK = """\u8fd9\u4e00\u884c\u6ca1\u6709\u5206\u9694\u7b26
foo|bar
copies=abc
rpo_minutes=xyz
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

    # 1. \u89e3\u6790\u4e0e\u9ed8\u8ba4\u503c
    d, raw = parse(GOOD_T1)
    ck("parse_copies", d["copies"], 3)
    ck("parse_freq", d["frequency"], "continuous")
    ck("parse_count", len(raw), 17)
    d2, raw2 = parse(EMPTY)
    ck("parse_empty_defaults", d2["copies"], 1)
    ck("parse_empty_raw", raw2, {})
    dj, rawj = parse(JUNK)
    ck("parse_junk_skip", "foo" in rawj, False)
    ck("parse_junk_bad_num_skipped", rawj, {})

    # 2. RPO \u4e0e\u9891\u7387\u5339\u914d\uff08\u6838\u5fc3\u77db\u76fe\u8bc6\u522b\uff09
    ck("freq_continuous_rpo5", check_rpo_frequency(d)[0], PASS)
    bad, _r = parse(BAD_RPO)
    lv, note = check_rpo_frequency(bad)
    ck("freq_daily_rpo5", lv, FAIL)
    ck("freq_daily_note", "\u5b9a\u65f6\u5907\u4efd\u65e0\u6cd5\u7a81\u7834\u9891\u7387\u9650\u5236" in note, True)
    gap = dict(bad)
    gap["rpo_minutes"] = 45
    gap["frequency"] = "hourly"
    ck("freq_gap_warn", check_rpo_frequency(gap)[0], WARN)
    ck("freq_unknown", check_rpo_frequency(
        dict(bad, frequency="\u6bcf\u534a\u5c0f\u65f6"))[0], FAIL)

    # 3. 3-2-1-1-0
    rows = dict((n, lv2) for n, v, lv2, note2 in check_32110(d))
    ck("p321_3", rows.get("3 \u526f\u672c"), PASS)
    ck("p321_2", rows.get("2 \u4ecb\u8d28"), PASS)
    ck("p321_1", rows.get("1 \u5f02\u5730"), PASS)
    ck("p321_immutable", rows.get("+1 \u4e0d\u53ef\u53d8"), PASS)
    ck("p321_zero", rows.get("+0 \u96f6\u9519\u8bef"), PASS)
    ck("p321_cred", rows.get("\u51ed\u636e\u9694\u79bb"), PASS)
    fb, _r2 = parse(FAKE_BACKUP)
    frows = dict((n, lv2) for n, v, lv2, note2 in check_32110(fb))
    ck("fake_copies", frows.get("3 \u526f\u672c"), FAIL)
    ck("fake_media", frows.get("2 \u4ecb\u8d28"), FAIL)
    ck("fake_offsite", frows.get("1 \u5f02\u5730"), FAIL)
    ck("fake_immutable", frows.get("+1 \u4e0d\u53ef\u53d8"), FAIL)
    ck("fake_zero", frows.get("+0 \u96f6\u9519\u8bef"), FAIL)
    ck("fake_cred", frows.get("\u51ed\u636e\u9694\u79bb"), FAIL)
    ck("fake_ransom_note",
       "\u52d2\u7d22\u8f6f\u4ef6" in dict((n, note2) for n, v, lv2, note2
                        in check_32110(fb)).get("+1 \u4e0d\u53ef\u53d8"), True)

    # 4. \u5206\u7ea7\u5bf9\u9f50
    t1 = build(GOOD_T1, 1)
    ck("tier1_good", t1["overall"], PASS)
    ck("tier1_name", t1["tier_name"], "\u4e00\u7ea7 \u6838\u5fc3\u4ea4\u6613")
    ck("tier1_limits", t1["tier_limits"]["rpo_max"], 5)
    t4 = build(GOOD_T1, 4)
    ck("tier4_good", t4["overall"], PASS)
    ck("tier4_drill_free",
       any("\u968f\u53d1\u5e03" in r["note"] for r in t4["rows"]), True)
    tf = build(FAKE_BACKUP, 3)
    ck("tier3_fake_fail", tf["overall"], FAIL)
    ck("tier3_drill_fail",
       any(r["name"] == "\u6f14\u7ec3\u5468\u671f" and r["level"] == FAIL
           for r in tf["rows"]), True)

    # 5. \u516d\u5c42\u6709\u6548\u6027
    lay = build(GOOD_T1, 1)
    ck("layers_all", len([r for r in lay["rows"] if r["group"] == "\u6709\u6548\u6027\u6821\u9a8c"]),
       6)
    cf = build(FAKE_BACKUP, 3)
    ck("fake_no_l5",
       any("\u4e0d\u5f97\u5bf9\u5916\u58f0\u79f0\u5907\u4efd\u6709\u6548" in r["note"] for r in cf["rows"]), True)

    # 6. \u76d1\u63a7
    mon = build(FAKE_BACKUP, 3)
    ck("fake_no_monitor",
       any(r["name"] == "\u5907\u4efd\u5931\u8d25\u544a\u8b66" and r["level"] == FAIL
           for r in mon["rows"]), True)
    ck("fake_no_trend",
       any(r["name"] == "\u5907\u4efd\u5927\u5c0f\u8d8b\u52bf" and r["level"] == FAIL
           for r in mon["rows"]), True)

    # 7. \u7a7a\u8f93\u5165\u4e0e\u5783\u573e\u8f93\u5165
    te = build(EMPTY, 2)
    ck("empty_fail", te["overall"], FAIL)
    ck("empty_keys", te["parsed_keys"], 0)
    ck("empty_parse_note",
       any(r["name"] == "\u8f93\u5165\u89e3\u6790" for r in te["rows"]), True)

    # 8. \u6e32\u67d3
    md = render_md(t1)
    ck("md_header", md.startswith("# "), True)
    ck("md_manual", "\u5fc5\u987b\u4eba\u5de5\u786e\u8ba4" in md, True)
    ck("md_caveat", "\u8fb9\u754c\u63d0\u793a" in md, True)
    ck("md_limits", "| RPO | 5 \u5206\u949f |" in md, True)
    js = json.loads(json.dumps(t1, ensure_ascii=False))
    ck("json_keys", sorted(js.keys()),
       ["data", "overall", "parsed_keys", "rows", "tier", "tier_limits",
        "tier_name"])

    # 9. \u5206\u7ea7\u8868\u5b8c\u6574\u6027
    ck("tiers_len", len(TIERS), 4)
    ck("freq_len", len(FREQ_RPO), 7)
    ck("verify_len", len(VERIFY_LAYERS), 6)
    ck("manual_len", len(MANUAL) >= 8, True)
    ck("worst_order", LEVEL_ORDER[FAIL] > LEVEL_ORDER[WARN], True)

    for line in res:
        print(line)
    print("SELFTEST %s (%d assertions)" % ("OK" if ok else "FAILED", len(res)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--tier", type=int, default=3, choices=[1, 2, 3, 4])
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
    r = build(text, a.tier)
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