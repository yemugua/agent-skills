# -*- coding: utf-8 -*-
"""\u4e70\u5230\u5047\u8d27\u53d6\u8bc1\u4e0e\u9000\u4e00\u8d54\u4e09\u6838\u67e5\u5de5\u5177\u3002

\u7528\u6cd5:
  python fake_check.py --file case.txt --price 1299 [--qty 1] [--category general|food]
                       [--platform-pledge 10] [--loss 0] [--out out.md] [--format md|json]
  python fake_check.py --selftest
"""
import argparse
import datetime
import json
import os
import re
import sys

# ---- 12 \u9879\u8bc1\u636e\u8981\u4ef6 ----
EVIDENCE = [
    ("\u7ecf\u8425\u8005\u4e3b\u4f53\u8eab\u4efd", "\u8425\u4e1a\u6267\u7167|\u5e97\u94fa\u4e3b\u4f53|\u7ecf\u8425\u8005|\u4f01\u4e1a\u540d\u79f0|\u7edf\u4e00\u793e\u4f1a\u4fe1\u7528\u4ee3\u7801|\u5e73\u53f0\u516c\u793a"),
    ("\u5546\u54c1\u63cf\u8ff0\u5feb\u7167", "\u8be6\u60c5\u9875|\u5546\u54c1\u8be6\u60c5|\u6807\u9898|\u5ba3\u4f20|\u53c2\u6570|\u76f4\u64ad|\u56de\u653e"),
    ("\u8ba2\u5355\u8bb0\u5f55", "\u8ba2\u5355\u53f7|\u8ba2\u5355\u7f16\u53f7|\u4e0b\u5355\u65f6\u95f4|\u8ba2\u5355"),
    ("\u652f\u4ed8\u51ed\u8bc1", "\u652f\u4ed8|\u4ed8\u6b3e|\u6d41\u6c34|\u8f6c\u8d26|\u5b9e\u4ed8|\u5fae\u4fe1\u652f\u4ed8|\u652f\u4ed8\u5b9d|\u94f6\u884c\u5361"),
    ("\u7269\u6d41\u4fe1\u606f", "\u5feb\u9012|\u7269\u6d41|\u8fd0\u5355|\u7b7e\u6536|\u5355\u53f7|\u914d\u9001"),
    ("\u5f00\u7bb1\u4e0e\u5b9e\u6536\u8bb0\u5f55", "\u5f00\u7bb1|\u89c6\u9891|\u5f55\u50cf|\u7167\u7247|\u5916\u5305\u88c5|\u79f0\u91cd"),
    ("\u5b9e\u7269\u4e0e\u6807\u8bc6", "\u5b9e\u7269|\u6807\u7b7e|\u5e8f\u5217\u53f7|\u9632\u4f2a|\u7f16\u7801|\u5305\u88c5|\u914d\u4ef6"),
    ("\u771f\u4f2a\u6bd4\u5bf9\u6750\u6599", "\u6bd4\u5bf9|\u6b63\u54c1\u5bf9\u6bd4|\u9632\u4f2a\u67e5|\u5b98\u65b9\u5ba2\u670d|\u5b98\u65b9\u67e5\u8be2|\u67e5\u8be2\u7ed3\u679c\u4e3a|\u9274\u5b9a"),
    ("\u6c9f\u901a\u8bb0\u5f55", "\u804a\u5929|\u5ba2\u670d|\u6c9f\u901a|\u56de\u590d|\u901a\u8bdd|\u7b54\u590d"),
    ("\u9274\u5b9a\u610f\u89c1", "\u9274\u5b9a|\u68c0\u6d4b\u62a5\u544a|\u9274\u5b9a\u610f\u89c1|\u8d28\u68c0|\u68c0\u9a8c|\u552e\u540e\u68c0\u6d4b"),
    ("\u635f\u5931\u51ed\u8bc1", "\u8fd0\u8d39|\u53d1\u7968|\u7968\u636e|\u9274\u5b9a\u8d39|\u516c\u8bc1\u8d39|\u6536\u636e"),
    ("\u65f6\u95f4\u7ebf", "\u7b7e\u6536\u65e5|\u6536\u8d27\u65e5|\u53cd\u9988|\u53d1\u73b0|\u6295\u8bc9|\u7533\u8bf7"),
]

# ---- \u5426\u4ecb\u8bcd\uff1a\u4e0d\u5f97\u628a\u8fd9\u7c7b\u8868\u8ff0\u5f53\u6210\u80af\u5b9a\u7ed3\u8bba ----
DEGRADE_WORDS = [
    "\u672a\u9274\u5b9a", "\u6682\u672a\u9274\u5b9a", "\u5c1a\u672a\u9001\u68c0", "\u672a\u9001\u68c0", "\u7591\u4f3c", "\u7591\u4f3c\u5047\u8d27", "\u7591\u4f3c\u5047\u5192",
    "\u65e0\u6cd5\u786e\u8ba4", "\u4e0d\u80fd\u786e\u8ba4", "\u5c1a\u4e0d\u80fd", "\u5f85\u8ba4\u5b9a", "\u611f\u89c9\u50cf\u5047", "\u53ef\u80fd\u662f\u5047",
    "\u672a\u786e\u8ba4", "\u96be\u4ee5\u786e\u8ba4",
]
CONFIRM_WORDS = [
    "\u9274\u5b9a\u4e3a\u5047", "\u9274\u5b9a\u7ed3\u8bba\u4e3a\u5047", "\u786e\u4e3a\u5047\u5192", "\u8ba4\u5b9a\u4e3a\u5047\u5192", "\u68c0\u6d4b\u7ed3\u679c\u4e3a\u4e0d\u5408\u683c",
    "\u786e\u8ba4\u4e3a\u975e\u6b63\u54c1", "\u7cfb\u5047\u5192",
]
DISPUTE_WORDS = [
    "\u672a\u53d6\u5f97\u6388\u6743", "\u6ca1\u6709\u6388\u6743", "\u6388\u6743\u5b58\u7591", "\u4e32\u8d27", "\u6e20\u9053\u4e0d\u660e",
]
UNPAID_WORDS = ["\u672a\u4ed8\u6b3e", "\u672a\u5b8c\u6210\u652f\u4ed8", "\u5c1a\u672a\u652f\u4ed8", "\u4ed8\u6b3e\u5931\u8d25"]
PAID_WORDS = ["\u5df2\u4ed8\u6b3e", "\u5df2\u652f\u4ed8", "\u5df2\u652f\u4ed8\u5b8c\u6210", "\u5b9e\u4ed8"]

DATE_PAT = re.compile(r"(20\d{2})[-\./\u5e74](\d{1,2})[-\./\u6708](\d{1,2})")
SPLIT_RE = re.compile("[\u3002\uff1b\uff0c\uff01\uff1f\uff1b,;\uff01\n]")

GENERAL_TIMES = 3
GENERAL_FLOOR = 500
FOOD_TIMES = 10
FOOD_LOSS_TIMES = 3
FOOD_FLOOR = 1000


def norm(s):
    return (s or "").replace(" ", "").replace("\u3000", "")


def has(pat, text):
    return re.search(pat, text) is not None


def scan_evidence(text):
    t = norm(text)
    out = []
    for name, pat in EVIDENCE:
        out.append((name, "\u6709" if has(pat, t) else "\u7f3a"))
    return out


def scan_condition(text):
    """\u5224\u5b9a\u8ba4\u5b9a\u72b6\u6001\uff1aconfirmed / pending / dispute\u3002\u5426\u5b9a\u8bcd\u4f18\u5148\u3002"""
    t = norm(text)
    hits = {"degrade": [], "confirm": [], "dispute": []}
    for w in DEGRADE_WORDS:
        if w in t:
            hits["degrade"].append(w)
    for w in CONFIRM_WORDS:
        if w in t:
            hits["confirm"].append(w)
    for w in DISPUTE_WORDS:
        if w in t:
            hits["dispute"].append(w)
    if hits["degrade"]:
        status = "pending"
    elif hits["confirm"]:
        status = "confirmed"
    else:
        status = "pending"
    return status, hits


def scan_payment(text):
    """\u652f\u4ed8\u72b6\u6001\u3002\u672a\u4ed8\u6b3e\u7c7b\u8868\u8ff0\u4f18\u5148\uff0c\u9632\u6b62\u8bef\u5224\u4e3a\u5df2\u4ed8\u6b3e\u3002"""
    t = norm(text)
    unpaid = [w for w in UNPAID_WORDS if w in t]
    paid = [w for w in PAID_WORDS if w in t]
    if unpaid and not paid:
        return "unpaid", unpaid, paid
    if paid and not unpaid:
        return "paid", unpaid, paid
    if unpaid and paid:
        return "ambiguous", unpaid, paid
    return "unknown", unpaid, paid


def calc(price, qty, category, pledge, loss):
    price = float(price)
    qty = int(qty)
    loss = float(loss or 0)
    refund = price * qty
    if category == "food":
        times = FOOD_TIMES
        floor = FOOD_FLOOR
        statutory = refund * times
        alternative = loss * FOOD_LOSS_TIMES
        note_alt = "\u4ea6\u53ef\u4e3b\u5f20\u635f\u5931\u4e09\u500d = %.2f \u5143\uff0c\u4e8c\u8005\u62e9\u9ad8" % alternative
    else:
        times = GENERAL_TIMES
        floor = GENERAL_FLOOR
        statutory = refund * times
        alternative = 0.0
        note_alt = ""
    base_add = max(statutory, alternative, floor)
    conservative = refund + base_add
    reasonable = conservative + loss
    pledge_val = 0.0
    if pledge and float(pledge) > 0:
        pledge_val = refund * float(pledge)
    aggressive = max(reasonable, refund + max(base_add, pledge_val) + loss)
    return {
        "refund": refund,
        "statutory_times": times,
        "statutory_amount": statutory,
        "alt_amount": alternative,
        "alt_note": note_alt,
        "floor": floor,
        "add_amount": base_add,
        "conservative": conservative,
        "reasonable": reasonable,
        "pledge_amount": pledge_val,
        "aggressive": aggressive,
        "loss": loss,
    }


def find_dates(text):
    out = []
    for m in DATE_PAT.finditer(text):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            out.append(datetime.date(y, mo, d))
        except ValueError:
            continue
    return sorted(out)


def money(x):
    return "%.2f" % x


def render_md(text, calcres, status, pay_status, hits):
    lines = ["# \u4e70\u5230\u5047\u8d27\u53d6\u8bc1\u4e0e\u9000\u4e00\u8d54\u4e09\u6838\u67e5\u7ed3\u679c", ""]
    lines.append("## \u4e00\u3001\u7ed3\u8bba\u5148\u884c")
    lines.append("")
    if pay_status == "unpaid":
        lines.append("- \u652f\u4ed8\u72b6\u6001\uff1a**\u4ef7\u6b3e\u5f85\u6838\u5b9e**\uff08\u68c0\u51fa\u672a\u4ed8\u6b3e\u7c7b\u8868\u8ff0\uff0c\u5b9e\u4ed8\u91d1\u989d\u987b\u91cd\u65b0\u786e\u8ba4\uff09")
    elif pay_status == "ambiguous":
        lines.append("- \u652f\u4ed8\u72b6\u6001\uff1a**\u5b58\u7591**\uff08\u540c\u4e00\u6750\u6599\u540c\u65f6\u51fa\u73b0\u5df2\u4ed8\u4e0e\u672a\u4ed8\u8868\u8ff0\uff0c\u987b\u56de\u539f\u6587\u6838\u5bf9\uff09")
    label = {"confirmed": "\u5df2\u5177\u5907\u8ba4\u5b9a\u6750\u6599", "pending": "\u5f85\u8ba4\u5b9a"}[status]
    lines.append("- \u771f\u4f2a\u8ba4\u5b9a\u72b6\u6001\uff1a**%s**" % label)
    if hits["degrade"]:
        lines.append("- \u68c0\u51fa\u964d\u7ea7\u8868\u8ff0\uff1a%s\uff08\u4e0d\u5f97\u76f4\u63a5\u6309\u5df2\u786e\u8ba4\u4e3a\u5047\u5904\u7406\uff09" % "\u3001".join(hits["degrade"]))
    if hits["dispute"]:
        lines.append("- \u68c0\u51fa\u6388\u6743\u7c7b\u4e89\u8bae\uff1a%s\uff08\u5c5e\u6388\u6743\u5b58\u7591\uff0c\u4e0d\u7b49\u540c\u4e8e\u5047\u5192\uff09" % "\u3001".join(hits["dispute"]))
    lines.append("")
    lines.append("## \u4e8c\u3001\u8bc1\u636e\u8981\u4ef6\u6838\u67e5\u8868")
    lines.append("")
    lines.append("| # | \u8981\u4ef6 | \u72b6\u6001 |")
    lines.append("|---|---|---|")
    missing = []
    for i, (n, st) in enumerate(scan_evidence(text), 1):
        lines.append("| %d | %s | %s |" % (i, n, st))
        if st == "\u7f3a":
            missing.append(n)
    have = 12 - len(missing)
    lines.append("")
    lines.append("\u5df2\u5177\u5907 %d / 12 \u9879\u3002" % have)
    if missing:
        lines.append("")
        lines.append("\u7f3a\u5931\u8981\u4ef6\uff1a%s" % "\u3001".join(missing))
    lines.append("")
    lines.append("## \u4e09\u3001\u91d1\u989d\u6838\u7b97")
    lines.append("")
    c = calcres
    lines.append("| \u9879\u76ee | \u91d1\u989d\uff08\u5143\uff09 | \u8bf4\u660e |")
    lines.append("|---|---|---|")
    lines.append("| \u9000\u6b3e\u989d\uff08\u9000\u4e00\uff09 | %s | \u5b9e\u4ed8\u4ef7\u6b3e\u5408\u8ba1 |" % money(c["refund"]))
    lines.append("| \u6cd5\u5b9a\u589e\u52a0\u8d54\u507f | %s | \u4ef7\u6b3e \u00d7 %d |" % (money(c["statutory_amount"]), c["statutory_times"]))
    if c["alt_amount"]:
        lines.append("| \u5907\u9009\u53e3\u5f84 | %s | %s |" % (money(c["alt_amount"]), c["alt_note"]))
    lines.append("| \u515c\u5e95\u7ebf | %s | %s |" % (money(c["floor"]),
                                          "\u4e0d\u8db3\u5219\u6309\u515c\u5e95\u8ba1" if c["add_amount"] == c["floor"] else "\u672a\u89e6\u53d1\u515c\u5e95"))
    lines.append("| \u5b9e\u9645\u53d6\u5b9a\u589e\u52a0\u8d54\u507f | %s | \u6cd5\u5b9a\u503c\u3001\u5907\u9009\u9879\u3001\u515c\u5e95\u4e09\u8005\u53d6\u9ad8 |" % money(c["add_amount"]))
    lines.append("| \u76f4\u63a5\u635f\u5931 | %s | \u9700\u6709\u7968\u636e\uff0c\u5355\u5217\u4e3b\u5f20 |" % money(c["loss"]))
    lines.append("")
    lines.append("**\u4e09\u6863\u533a\u95f4**")
    lines.append("")
    lines.append("| \u6863\u4f4d | \u5408\u8ba1\uff08\u5143\uff09 | \u6784\u6210 |")
    lines.append("|---|---|---|")
    lines.append("| \u4fdd\u5b88 | %s | \u9000\u6b3e\u989d + \u589e\u52a0\u8d54\u507f |" % money(c["conservative"]))
    lines.append("| \u5408\u7406 | %s | \u4fdd\u5b88 + \u6709\u7968\u636e\u7684\u76f4\u63a5\u635f\u5931 |" % money(c["reasonable"]))
    if c["pledge_amount"]:
        lines.append("| \u4e89\u53d6 | %s | \u53e0\u52a0\u5e73\u53f0\u627f\u8bfa\u8d54\u507f %s \u5143 |" % (money(c["aggressive"]), money(c["pledge_amount"])))
    else:
        lines.append("| \u4e89\u53d6 | %s | \u65e0\u66f4\u9ad8\u5e73\u53f0\u627f\u8bfa\uff0c\u4e0e\u5408\u7406\u6863\u4e00\u81f4 |" % money(c["aggressive"]))
    lines.append("")
    lines.append("## \u56db\u3001\u65f6\u95f4\u8282\u70b9")
    lines.append("")
    ds = find_dates(text)
    if not ds:
        lines.append("\u672a\u8bc6\u522b\u5230\u65e5\u671f\uff0c\u65e0\u6cd5\u6821\u9a8c\u7b7e\u6536\u65e5\u4e0e\u53cd\u9988\u65e5\u95f4\u9694\u3002\u8bf7\u624b\u8865\u5173\u952e\u65f6\u95f4\u8282\u70b9\u3002")
    else:
        for d in ds:
            lines.append("- %s" % d.isoformat())
        if len(ds) >= 2:
            gap = (ds[-1] - ds[0]).days
            lines.append("")
            lines.append("\u9996\u672b\u8282\u70b9\u95f4\u9694 %d \u5929\u3002\u7b7e\u6536\u65e5\u4ee5\u7269\u6d41\u7b7e\u6536\u4e3a\u51c6\uff0c\u975e\u5f00\u7bb1\u65e5\u3002" % gap)
            if gap > 7:
                lines.append("**\u63d0\u793a\uff1a** \u82e5\u9996\u4e2a\u8282\u70b9\u4e3a\u7b7e\u6536\u65e5\u4e14\u95f4\u9694\u8d85\u8fc7 7 \u5929\uff0c\u65e0\u7406\u7531\u9000\u8d27\u671f\u53ef\u80fd\u5df2\u8fc7\uff0c\u9700\u6539\u7528\u8d28\u91cf\u95ee\u9898\u6216\u6b3a\u8bc8\u8def\u5f84\u3002")
    lines.append("")
    lines.append("## \u4e94\u3001\u5b9a\u91cf\u8868\u8ff0\u5b88\u5219")
    lines.append("")
    lines.append("- \u65e0\u9274\u5b9a\u610f\u89c1\u7684\u6750\u6599\uff0c\u5b9a\u6027\u7edf\u79f0\u300c\u6d89\u5acc\u4e0e\u6b63\u54c1\u4e0d\u7b26\uff0c\u4ee5\u9274\u5b9a\u610f\u89c1\u4e3a\u51c6\u300d")
    lines.append("- \u5426\u5b9a\u7c7b\u8868\u8ff0\u4e0d\u5f97\u6539\u5199\u4e3a\u80af\u5b9a\u7ed3\u8bba")
    lines.append("- \u8d54\u507f\u53e3\u5f84\u4ee5\u73b0\u884c\u89c4\u5b9a\u548c\u5f53\u5730\u5e02\u573a\u76d1\u7ba1\u90e8\u95e8\u8981\u6c42\u4e3a\u51c6")
    lines.append("")
    lines.append("---")
    lines.append("\u672c\u7ed3\u679c\u4e3a\u6750\u6599\u6574\u7406\u4e0e\u91d1\u989d\u6838\u7b97\u4ea7\u7269\uff0c\u4e0d\u6784\u6210\u771f\u4f2a\u8ba4\u5b9a\u6216\u6cd5\u5f8b\u610f\u89c1\u3002")
    return "\n".join(lines)


def render_json(text, calcres, status, pay_status, hits):
    obj = {
        "status": status,
        "pay_status": pay_status,
        "hits": hits,
        "evidence": [{"name": n, "status": s} for n, s in scan_evidence(text)],
        "calc": calcres,
        "dates": [d.isoformat() for d in find_dates(text)],
    }
    return json.dumps(obj, ensure_ascii=False, indent=2)


SAMPLE_OK = """
\u7ecf\u8425\u8005\uff1a\u67d0\u67d0\u7535\u5b50\u5546\u52a1\u6709\u9650\u516c\u53f8\uff08\u5e73\u53f0\u516c\u793a\u4e3b\u4f53\uff09
\u8ba2\u5355\u53f7\uff1a20250417-88991  \u4e0b\u5355\u65f6\u95f4\uff1a2025-04-17
\u5546\u54c1\u8be6\u60c5\u9875\u622a\u56fe\u5df2\u4fdd\u5b58\uff0c\u9875\u9762\u6807\u9898\u5199\u660e\u5b98\u65b9\u6388\u6743\u6b63\u54c1
\u5fae\u4fe1\u652f\u4ed8\u6d41\u6c34\u663e\u793a\u5df2\u4ed8\u6b3e\uff0c\u5b9e\u4ed8\u91d1\u989d 1299 \u5143\uff0c\u6536\u6b3e\u65b9\u67d0\u67d0\u7535\u5b50\u5546\u52a1\u6709\u9650\u516c\u53f8
\u7269\u6d41\uff1a\u97f5\u8fbe\u5feb\u9012 \u5355\u53f7 3102xxxx\uff0c\u7b7e\u6536\u65e5 2025-04-20
\u5f00\u7bb1\u89c6\u9891\u4ece\u5feb\u9012\u5916\u5305\u88c5\u516d\u9762\u8d77\u62cd\uff0c\u4e00\u955c\u5230\u5e95\u672a\u526a\u8f91\uff0c\u4fdd\u7559\u539f\u59cb\u6807\u7b7e\u4e0e\u9632\u4f2a\u7801
2025-04-21 \u5411\u5e73\u53f0\u5ba2\u670d\u63d0\u4ea4\u6c9f\u901a\u8bb0\u5f55\uff0c\u5ba2\u670d\u56de\u590d\u79f0\u652f\u6301\u4e13\u67dc\u9a8c\u8d27
\u7ecf\u7b2c\u4e09\u65b9\u673a\u6784\u9274\u5b9a\uff0c\u9274\u5b9a\u7ed3\u8bba\u4e3a\u5047\u5192\u4ea7\u54c1\uff0c\u9274\u5b9a\u8d39 300 \u5143\u6709\u53d1\u7968
2025-05-06 \u5411 12315 \u63d0\u4ea4\u6295\u8bc9
"""

SAMPLE_WEAK = """
\u6211\u5728\u76f4\u64ad\u95f4\u4e70\u4e86\u4e2a\u5305\uff0c\u611f\u89c9\u50cf\u662f\u5047\u7684\uff0c\u5c1a\u672a\u9001\u68c0\u3002
\u80fd\u4e0d\u80fd\u8ba9\u4ed6\u8d54\u4e09\u500d\uff1f
"""

SAMPLE_NEG = """
\u8be5\u5546\u54c1\u7591\u4f3c\u5047\u8d27\uff0c\u672a\u9274\u5b9a\u3002
\u5546\u5bb6\u672a\u63d0\u4f9b\u6388\u6743\uff0c\u6388\u6743\u5b58\u7591\u3002
\u4e70\u5bb6\u5c1a\u672a\u652f\u4ed8\u5c3e\u6b3e\u3002
"""


def selftest():
    ok = True
    res = []

    def ck(name, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        res.append("%s %s got=%s want=%s" % ("PASS" if good else "FAIL", name, got, want))

    # 1. \u8981\u4ef6\u626b\u63cf
    ev = scan_evidence(SAMPLE_OK)
    ck("ok_evidence_all_present", all(s == "\u6709" for _, s in ev), True)
    ev2 = scan_evidence(SAMPLE_WEAK)
    ck("weak_evidence_missing", all(s == "\u6709" for _, s in ev2), False)

    # 2. \u91d1\u989d\u6838\u7b97\uff1a\u4e00\u822c\u5546\u54c1 1299 \u5143
    c = calc(1299, 1, "general", 0, 300)
    ck("general_refund", money(c["refund"]), "1299.00")
    ck("general_statutory", money(c["statutory_amount"]), "3897.00")
    ck("general_add_no_floor", money(c["add_amount"]), "3897.00")
    ck("general_conservative", money(c["conservative"]), "5196.00")
    ck("general_reasonable", money(c["reasonable"]), "5496.00")

    # 3. \u515c\u5e95\u7ebf\uff1a\u5c0f\u989d\u89e6\u53d1 500
    c2 = calc(100, 1, "general", 0, 0)
    ck("floor_triggered", money(c2["add_amount"]), "500.00")
    ck("floor_conservative", money(c2["conservative"]), "600.00")

    # 4. \u98df\u54c1\u7c7b\uff1a\u5341\u500d\u4e0e 1000 \u515c\u5e95
    c3 = calc(50, 1, "food", 0, 0)
    ck("food_add", money(c3["add_amount"]), "1000.00")
    ck("food_conservative", money(c3["conservative"]), "1050.00")

    # 5. \u5e73\u53f0\u627f\u8bfa\u53d6\u9ad8
    c4 = calc(1299, 1, "general", 10, 0)
    ck("pledge_times_ten", money(c4["pledge_amount"]), "12990.00")
    ck("pledge_aggressive", money(c4["aggressive"]), "14289.00")

    # 6. \u5426\u5b9a\u8bcd\u9632\u8bef\u4f24
    st, hits = scan_condition(SAMPLE_WEAK)
    ck("weak_status_pending", st, "pending")
    ck("weak_has_degrade", len(hits["degrade"]) > 0, True)
    st2, hits2 = scan_condition(SAMPLE_OK)
    ck("ok_status_confirmed", st2, "confirmed")
    ck("ok_no_degrade", len(hits2["degrade"]), 0)

    st3, hits3 = scan_condition(SAMPLE_NEG)
    ck("neg_status_pending", st3, "pending")
    ck("neg_dispute_hit", len(hits3["dispute"]) > 0, True)

    # 7. \u652f\u4ed8\u72b6\u6001
    ck("neg_pay_unpaid", scan_payment(SAMPLE_NEG)[0], "unpaid")
    ck("ok_pay_paid", scan_payment(SAMPLE_OK)[0], "paid")

    # 8. \u65e5\u671f\u63d0\u53d6
    ds = find_dates(SAMPLE_OK)
    ck("date_count_ge3", len(ds) >= 3, True)
    ck("first_date", ds[0].isoformat(), "2025-04-17")

    # 9. \u6e32\u67d3
    md = render_md(SAMPLE_OK, c, "confirmed", "paid", {"degrade": [], "confirm": [], "dispute": []})
    ck("md_has_header", md.startswith("# "), True)
    js = json.loads(render_json(SAMPLE_OK, c, "confirmed", "paid", {"degrade": [], "confirm": [], "dispute": []}))
    ck("json_keys", sorted(js.keys()), ["calc", "dates", "evidence", "hits", "pay_status", "status"])

    for line in res:
        print(line)
    print("SELFTEST %s" % ("OK" if ok else "FAILED"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--price", type=float, default=0.0)
    ap.add_argument("--qty", type=int, default=1)
    ap.add_argument("--category", default="general", choices=["general", "food"])
    ap.add_argument("--platform-pledge", type=float, default=0.0)
    ap.add_argument("--loss", type=float, default=0.0)
    ap.add_argument("--out", default="")
    ap.add_argument("--format", default="md", choices=["md", "json"])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    if not a.file or not os.path.exists(a.file):
        print("ERROR --file not found")
        return 2
    if a.price <= 0:
        print("ERROR --price must be positive")
        return 2

    text = open(a.file, "r", encoding="utf-8", errors="replace").read()
    status, hits = scan_condition(text)
    pay_status, _, _ = scan_payment(text)
    calcres = calc(a.price, a.qty, a.category, a.platform_pledge, a.loss)

    if a.format == "json":
        body = render_json(text, calcres, status, pay_status, hits)
    else:
        body = render_md(text, calcres, status, pay_status, hits)

    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(body)
        print("WROTE %s" % a.out)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
