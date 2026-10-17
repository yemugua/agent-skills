# -*- coding: utf-8 -*-
"""消防设施检测报告核查。

用法:
  python fire_check.py --file 报告.txt --as-of 2026-10-08 [--out out.md] [--format json]
  python fire_check.py --selftest
"""
import argparse
import datetime
import json
import os
import re
import sys

# ---- 要素库：12 项必备要素 ----
ELEMENTS = [
    ("机构名称", "\u673a\u6784|\u516c\u53f8|\u4e2d\u5fc3|\u6709\u9650\u516c\u53f8"),
    ("项目负责人与检测人员", "\u8d1f\u8d23\u4eba|\u9879\u76ee\u8d1f\u8d23\u4eba|\u68c0\u6d4b\u4eba|\u7b7e\u5b57|\u7b7e\u540d"),
    ("检测日期与报告编号", "\u68c0\u6d4b\u65e5\u671f|\u7f16\u53f7|\u62a5\u544a\u7f16\u53f7|No\."),
    ("建筑名称地址使用性质", "\u5efa\u7b51\u540d\u79f0|\u5730\u5740|\u4f7f\u7528\u6027\u8d28|\u573a\u6240"),
    ("建筑面积层数高度", "\u5efa\u7b51\u9762\u79ef|\u5c42\u6570|\u9ad8\u5ea6|m2|\u5e73\u65b9\u7c73"),
    ("检测范围与系统清单", "\u68c0\u6d4b\u8303\u56f4|\u7cfb\u7edf|\u6e05\u5355|\u5305\u542b"),
    ("依据标准", "GB|\u6807\u51c6|\u89c4\u8303|\u4f9d\u636e"),
    ("主要检测仪器设备", "\u4eea\u5668|\u8bbe\u5907|\u6d4b\u8bd5\u4eea|\u98ce\u901f\u4eea|\u7167\u5ea6\u8ba1"),
    ("各系统检测记录", "\u62a5\u8b66|\u55b7\u6dcb|\u6d88\u706b\u6813|\u9632\u6392\u70df|\u5e94\u6025\u7167\u660e"),
    ("不合格项清单与分级", "\u4e0d\u5408\u683c|\u7f3a\u9677|A\u7c7b|B\u7c7b|C\u7c7b|\u95ee\u9898"),
    ("综合判定结论", "\u7ed3\u8bba|\u5408\u683c|\u5224\u5b9a"),
    ("整改建议与复检要求", "\u6574\u6539|\u5efa\u8bae|\u590d\u68c0|\u590d\u67e5"),
]

# ---- 八类应检系统 ----
SYSTEMS = [
    ("火灾自动报警系统", "\u62a5\u8b66|\u63a2\u6d4b\u5668|\u63a7\u5236\u5668|\u624b\u62a5"),
    ("自动喷水灭火系统", "\u55b7\u6dcb|\u55b7\u5934|\u62a5\u8b66\u9600|\u672b\u7aef\u8bd5\u6c34"),
    ("消火栓系统", "\u6d88\u706b\u6813|\u6813\u53e3|\u6c34\u67aa|\u6cf5\u63a5\u5408\u5668"),
    ("防排烟系统", "\u9632\u6392\u70df|\u98ce\u673a|\u98ce\u91cf|\u6b63\u538b\u9001\u98ce|\u9632\u706b\u9600"),
    ("应急照明与疏散指示", "\u5e94\u6025\u7167\u660e|\u758f\u6563\u6307\u793a|\u7167\u5ea6|\u5b89\u5168\u51fa\u53e3"),
    ("消防电源与配电", "\u6d88\u9632\u7535\u6e90|\u53cc\u7535\u6e90|\u914d\u7535|\u672b\u7aef\u5207\u6362"),
    ("灭火器配置", "\u706d\u706b\u5668|\u914d\u7f6e|\u538b\u529b|\u6709\u6548\u671f"),
    ("防火分隔与疏散", "\u9632\u706b\u95e8|\u9632\u706b\u5377\u5e18|\u95ed\u95e8\u5668|\u758f\u6563\u901a\u9053"),
]

# ---- 缺陷分级关键词（A 最严重）----
A_KEYS = [
    "\u63a7\u5236\u5668\u6545\u969c", "\u4e3b\u5907\u7535\u65e0\u6cd5\u5207\u6362", "\u6cf5\u65e0\u6cd5\u542f\u52a8",
    "\u6c60\u65e0\u6c34", "\u6c34\u4f4d\u4e0d\u8db3", "\u98ce\u673a\u65e0\u6cd5\u542f\u52a8",
    "\u901a\u9053\u5835\u585e", "\u51fa\u53e3\u5835\u585e", "\u5377\u5e18\u65e0\u6cd5\u4e0b\u964d",
    "\u5e94\u6025\u7167\u660e\u5168\u90e8\u4e0d\u4eae", "\u505c\u7528", "\u624b\u52a8\u72b6\u6001",
]
B_KEYS = [
    "\u63a2\u6d4b\u5668\u6545\u969c", "\u8bef\u62a5", "\u55b7\u5934\u88ab\u906e\u6321", "\u8150\u8680",
    "\u538b\u529b\u4e0d\u8db3", "\u95ed\u95e8\u5668\u5931\u6548", "\u539f\u538b\u4e0d\u8db3",
    "\u8d85\u671f", "\u4e2a\u522b\u4e0d\u4eae", "\u7535\u8bdd\u4e0d\u901a", "\u9600\u95e8\u88ab\u5173",
    "\u65e0\u6807\u8bc6",
]
C_KEYS = [
    "\u6807\u8bc6\u7f3a\u5931", "\u6807\u8bc6\u6a21\u7cca", "\u79ef\u5c18", "\u751f\u9508",
    "\u53f0\u8d26\u586b\u5199\u4e0d\u89c4\u8303", "\u6863\u6848\u4e0d\u5b8c\u6574",
    "\u6577\u8bbe\u4e0d\u6574\u9f50", "\u4e0d\u4fbf\u53d6\u7528",
]

DONE_PAT = re.compile("\u5df2\u6574\u6539|\u5df2\u4fee\u590d|\u5df2\u66f4\u6362|\u5df2\u5904\u7406")
NEG_PAT = re.compile("\u672a\u6574\u6539|\u672a\u4fee\u590d|\u672a\u590d\u4f4d|\u672a\u66f4\u6362|\u5c1a\u672a")
CLOSED_PAT = re.compile("\u590d\u68c0|\u590d\u67e5")

DATE_PAT = re.compile(r"(20\d{2})[\-\./\u5e74](\d{1,2})[\-\./\u6708](\d{1,2})")
SPLIT_RE = re.compile("[\u3002\uff1b\uff0c\uff01\uff1f\uff0c,;\n]")


def norm(s):
    return (s or "").replace(" ", "").replace("\u3000", "")


def has(pattern, text):
    return re.search(pattern, text) is not None


def check_elements(text):
    t = norm(text)
    out = []
    for name, pat in ELEMENTS:
        out.append((name, "\u6709" if has(pat, t) else "\u7f3a"))
    return out


def check_systems(text):
    t = norm(text)
    out = []
    for name, pat in SYSTEMS:
        out.append((name, "\u5df2\u68c0" if has(pat, t) else "\u672a\u63d0\u53ca"))
    return out


def grade_defects(text):
    items = []
    for seg in SPLIT_RE.split(text):
        seg = seg.strip()
        if len(seg) < 4:
            continue
        level = None
        for k in A_KEYS:
            if k in seg:
                level = "A"
                break
        if level is None:
            for k in B_KEYS:
                if k in seg:
                    level = "B"
                    break
        if level is None:
            for k in C_KEYS:
                if k in seg:
                    level = "C"
                    break
        if level is None:
            continue
        if NEG_PAT.search(seg) or not DONE_PAT.search(seg):
            status = "\u672a\u6574\u6539"
        elif CLOSED_PAT.search(seg):
            status = "\u5df2\u95ed\u73af"
        else:
            status = "\u95ed\u73af\u5b58\u7591"
        items.append((level, seg[:60], status))
    order = {"A": 0, "B": 1, "C": 2}
    items.sort(key=lambda x: order[x[0]])
    return items


def find_dates(text):
    out = []
    for m in DATE_PAT.finditer(text):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            out.append(datetime.date(y, mo, d))
        except ValueError:
            continue
    return sorted(out)


def validity(text, as_of):
    dates = find_dates(text)
    if not dates:
        return None
    base = dates[0]
    expire = datetime.date(base.year + 1, base.month, base.day)
    remain = (expire - as_of).days
    return base, expire, remain


def render_md(text, as_of):
    lines = ["# \u6d88\u9632\u8bbe\u65bd\u68c0\u6d4b\u62a5\u544a\u6838\u67e5\u7ed3\u679c", ""]
    lines.append("\u6838\u67e5\u57fa\u51c6\u65e5\uff1a%s" % as_of.isoformat())
    lines.append("")
    lines.append("## \u4e00\u3001\u8981\u7d20\u6838\u67e5\u8868")
    lines.append("")
    lines.append("| # | \u8981\u7d20 | \u72b6\u6001 |")
    lines.append("|---|---|---|")
    for i, (n, st) in enumerate(check_elements(text), 1):
        lines.append("| %d | %s | %s |" % (i, n, st))
    miss = [n for n, st in check_elements(text) if st == "\u7f3a"]
    lines.append("")
    if miss:
        lines.append("\u7f3a\u5931\u8981\u7d20\uff1a%s" % "\u3001".join(miss))
    else:
        lines.append("12 \u9879\u8981\u7d20\u5747\u547d\u4e2d\u3002")
    lines.append("")
    lines.append("## \u4e8c\u3001\u7cfb\u7edf\u8986\u76d6")
    lines.append("")
    lines.append("| # | \u7cfb\u7edf | \u72b6\u6001 |")
    lines.append("|---|---|---|")
    for i, (n, st) in enumerate(check_systems(text), 1):
        lines.append("| %d | %s | %s |" % (i, n, st))
    covered = sum(1 for _, st in check_systems(text) if st == "\u5df2\u68c0")
    lines.append("")
    lines.append("\u5df2\u8986\u76d6 %d / 8 \u7c7b\u3002" % covered)
    lines.append("")
    lines.append("## \u4e09\u3001\u4e0d\u5408\u683c\u9879\u5206\u7ea7")
    lines.append("")
    items = grade_defects(text)
    if not items:
        lines.append("\u672a\u62bd\u53d6\u5230\u4e0d\u5408\u683c\u9879\u63cf\u8ff0\uff08\u6216\u62a5\u544a\u672a\u5217\u51fa\uff09\u3002")
        lines.append("\u82e5\u5b9e\u9645\u5b58\u5728\u7f3a\u9677\uff0c\u5c5e\u4e8e\u91cd\u5927\u5f02\u5e38\uff0c\u5e94\u8981\u6c42\u8865\u68c0\u3002")
    else:
        lines.append("| # | \u7b49\u7ea7 | \u63cf\u8ff0 | \u6574\u6539\u671f\u9650 | \u95ed\u73af\u72b6\u6001 |")
        lines.append("|---|---|---|---|---|")
        ddl = {"A": "\u7acb\u5373", "B": "30 \u65e5\u5185", "C": "90 \u65e5\u5185"}
        for i, (lv, seg, st) in enumerate(items, 1):
            lines.append("| %d | %s | %s | %s | %s |" % (i, lv, seg, ddl[lv], st))
        na = sum(1 for x in items if x[0] == "A")
        if na:
            lines.append("")
            lines.append("\u5b58\u5728 %d \u9879 A \u7c7b\u4e0d\u5408\u683c\u9879\uff0c\u6574\u6539\u524d\u8be5\u573a\u6240\u4e0d\u5177\u5907\u6d88\u9632\u5b89\u5168\u6761\u4ef6\u3002" % na)
    lines.append("")
    lines.append("## \u56db\u3001\u6709\u6548\u671f\u4e0e\u590d\u68c0")
    lines.append("")
    v = validity(text, as_of)
    if v is None:
        lines.append("\u672a\u8bc6\u522b\u5230\u68c0\u6d4b\u65e5\u671f\uff0c\u65e0\u6cd5\u7b97\u6709\u6548\u671f\u3002")
    else:
        base, expire, remain = v
        lines.append("- \u68c0\u6d4b\u65e5\u671f\uff1a%s" % base.isoformat())
        lines.append("- \u9884\u8ba1\u6709\u6548\u671f\u81f3\uff1a%s" % expire.isoformat())
        if remain < 0:
            lines.append("- \u5df2\u8d85\u671f %d \u5929\uff0c\u9700\u91cd\u65b0\u68c0\u6d4b\u3002" % abs(remain))
        elif remain <= 30:
            lines.append("- \u4ec5\u5269 %d \u5929\uff0c\u5efa\u8bae\u7acb\u5373\u5b89\u6392\u590d\u68c0\u3002" % remain)
        else:
            lines.append("- \u5269\u4f59 %d \u5929\uff0c\u5efa\u8bae\u5728\u5230\u671f\u524d 30 \u65e5\u5b8c\u6210\u590d\u68c0\u3002" % remain)
    lines.append("")
    lines.append("---")
    lines.append("\u672c\u7ed3\u679c\u4e3a\u62a5\u544a\u8981\u7d20\u6838\u67e5\u4e0e\u6750\u6599\u6574\u7406\u4ea7\u7269\uff0c\u4e0d\u6784\u6210\u6d88\u9632\u8bbe\u65bd\u68c0\u6d4b\u7ed3\u8bba\u3002")
    return "\n".join(lines)


def render_json(text, as_of):
    v = validity(text, as_of)
    obj = {
        "as_of": as_of.isoformat(),
        "elements": [{"name": n, "status": s} for n, s in check_elements(text)],
        "systems": [{"name": n, "status": s} for n, s in check_systems(text)],
        "defects": [{"level": lv, "desc": seg, "status": st}
                    for lv, seg, st in grade_defects(text)],
        "validity": None,
    }
    if v:
        base, expire, remain = v
        obj["validity"] = {"inspect_date": base.isoformat(),
                           "expire": expire.isoformat(), "remain_days": remain}
    return json.dumps(obj, ensure_ascii=False, indent=2)


SAMPLE_FULL = """
\u6d88\u9632\u8bbe\u65bd\u68c0\u6d4b\u62a5\u544a
\u673a\u6784\u540d\u79f0\uff1a\u67d0\u5e02\u6d88\u9632\u6280\u672f\u670d\u52a1\u6709\u9650\u516c\u53f8
\u9879\u76ee\u8d1f\u8d23\u4eba\uff1a\u5f20\u67d0\uff08\u7b7e\u5b57\uff09
\u68c0\u6d4b\u65e5\u671f\uff1a2025-10-08  \u62a5\u544a\u7f16\u53f7\uff1aXF-2025-0817
\u5efa\u7b51\u540d\u79f0\uff1a\u67d0\u5546\u52a1\u5927\u53a6  \u5730\u5740\uff1a\u67d0\u8def 100 \u53f7  \u4f7f\u7528\u6027\u8d28\uff1a\u516c\u5171\u5efa\u7b51
\u5efa\u7b51\u9762\u79ef\uff1a32000 \u5e73\u65b9\u7c73  \u5c42\u6570\uff1a28 \u5c42  \u9ad8\u5ea6\uff1a99 \u7c73
\u68c0\u6d4b\u8303\u56f4\uff1a\u672c\u62a5\u544a\u5305\u542b\u4ee5\u4e0b\u7cfb\u7edf\u6e05\u5355
\u4f9d\u636e\u6807\u51c6\uff1aGB 50116-2013\u3001GB 50084-2017\u3001GB 50974-2014
\u4e3b\u8981\u4eea\u5668\u8bbe\u5907\uff1a\u98ce\u901f\u4eea\u3001\u7167\u5ea6\u8ba1\u3001\u58f0\u7ea7\u8ba1
\u62a5\u8b66\u7cfb\u7edf\uff1a\u63a2\u6d4b\u5668\u62bd\u68c0\u6bd4\u4f8b\u7b26\u5408\u3002\u63a7\u5236\u5668\u6545\u969c\uff0c\u4e3b\u5907\u7535\u65e0\u6cd5\u5207\u6362\u3002
\u55b7\u6dcb\u7cfb\u7edf\uff1a\u672b\u7aef\u8bd5\u6c34\u538b\u529b\u4e0d\u8db3\u3002
\u6d88\u706b\u6813\u7cfb\u7edf\uff1a\u6813\u53e3\u538b\u529b\u6b63\u5e38\u3002
\u4e0d\u5408\u683c\u9879\uff1aA \u7c7b 1 \u9879\uff0cB \u7c7b 2 \u9879\u3002
\u7efc\u5408\u7ed3\u8bba\uff1a\u5b58\u5728 A \u7c7b\u4e0d\u5408\u683c\u9879\uff0c\u5224\u5b9a\u4e3a\u4e0d\u5408\u683c\u3002
\u6574\u6539\u5efa\u8bae\uff1a\u7acb\u5373\u66f4\u6362\u63a7\u5236\u5668\uff0c\u590d\u68c0\u540e\u518d\u884c\u5224\u5b9a\u3002
\u6813\u53e3\u538b\u529b\u4e0d\u8db3\uff0c\u5df2\u6574\u6539\u5e76\u590d\u68c0\u3002
"""

SAMPLE_POOR = """
\u68c0\u6d4b\u8bb0\u5f55
\u516c\u53f8\u6765\u4eba\u770b\u4e86\u4e00\u4e0b\uff0c\u90fd\u633a\u597d\u3002
\u7ed3\u8bba\uff1a\u5408\u683c\u3002
"""

SAMPLE_NEG = """
\u62a5\u8b66\u63a7\u5236\u5668\u6d88\u97f3\u540e\u672a\u590d\u4f4d\uff0c\u5df2\u62a5\u7ef4\u4fdd\u3002
\u55b7\u5934\u88ab\u906e\u6321\uff0c\u672a\u6574\u6539\u3002
\u6807\u8bc6\u7f3a\u5931\u3002
"""


def selftest():
    ok = True
    res = []

    def ck(name, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        res.append("%s %s got=%s want=%s" % ("PASS" if good else "FAIL", name, got, want))

    as_of = datetime.date(2026, 10, 8)
    els = check_elements(SAMPLE_FULL)
    ck("full_elements_all_present", all(s == "\u6709" for _, s in els), True)
    ck("poor_elements_missing", all(s == "\u6709" for _, s in check_elements(SAMPLE_POOR)), False)

    syss = check_systems(SAMPLE_FULL)
    cov = sum(1 for _, s in syss if s == "\u5df2\u68c0")
    ck("full_systems_covered_ge5", cov >= 5, True)

    ds = grade_defects(SAMPLE_FULL)
    ck("full_has_A_defect", any(x[0] == "A" for x in ds), True)
    ck("A_sorted_first", ds[0][0] if ds else None, "A")

    v = validity(SAMPLE_FULL, as_of)
    ck("inspect_date", v[0].isoformat(), "2025-10-08")
    ck("expire_date", v[1].isoformat(), "2026-10-08")
    ck("remain_days", v[2], 0)

    dn = grade_defects(SAMPLE_NEG)
    ck("neg_not_closed", all(x[2] != "\u5df2\u95ed\u73af" for x in dn), True)
    ck("neg_has_defects", len(dn) >= 2, True)

    ck("poor_no_defects", len(grade_defects(SAMPLE_POOR)), 0)

    md = render_md(SAMPLE_FULL, as_of)
    ck("md_has_header", md.startswith("# "), True)
    js = json.loads(render_json(SAMPLE_FULL, as_of))
    ck("json_keys", sorted(js.keys()), ["as_of", "defects", "elements", "systems", "validity"])

    for line in res:
        print(line)
    print("SELFTEST %s" % ("OK" if ok else "FAILED"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--as-of", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--format", default="md", choices=["md", "json"])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    if not a.file or not os.path.exists(a.file):
        print("ERROR --file \u4e0d\u5b58\u5728")
        return 2

    text = open(a.file, "r", encoding="utf-8", errors="replace").read()
    if a.as_of:
        y, m, d = [int(x) for x in re.split(r"[\-/]", a.as_of)[:3]]
        as_of = datetime.date(y, m, d)
    else:
        as_of = datetime.date.today()

    body = render_md(text, as_of) if a.format == "md" else render_json(text, as_of)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(body)
        print("WROTE %s" % a.out)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
