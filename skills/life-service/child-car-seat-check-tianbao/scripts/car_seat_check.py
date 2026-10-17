# -*- coding: utf-8 -*-
"""car_seat_check: \u513f\u7ae5\u5b89\u5168\u5ea7\u6905\u9636\u6bb5\u5224\u5b9a\u4e0e\u5b89\u88c5\u6838\u67e5\u3002

\u7528\u6cd5:
    python car_seat_check.py --age 3 --height 102 --weight 16 --position rear
    python car_seat_check.py --file child.json --out result.md
    python car_seat_check.py --selftest
"""
import argparse
import json
import os

BANDS = [
    (0.0, 1.0, "1 \u5c81\u4ee5\u4e0b", "\u540e\u5411\u5b89\u88c5"),
    (1.0, 4.0, "1 \u5230 4 \u5c81", "\u540e\u5411\u4f18\u5148"),
    (4.0, 7.0, "4 \u5230 7 \u5c81", "\u6ee1\u8db3\u6761\u4ef6\u540e\u53ef\u8f6c\u524d\u5411"),
    (7.0, 200.0, "7 \u5c81\u4ee5\u4e0a", "\u524d\u5411\uff0c\u591a\u6570\u9700\u7528\u589e\u9ad8\u57ab\u6216\u5b89\u5168\u5e26"),
]

METHOD_CN = {
    "isofix": "ISOFIX \u63a5\u53e3\u56fa\u5b9a",
    "belt": "\u5b89\u5168\u5e26\u56fa\u5b9a",
    "anchor": "\u8f66\u8f7d\u951a\u70b9\uff08\u4e0a\u62c9\u5e26\uff09",
    "builtin": "\u8f66\u8f86\u5185\u7f6e\u5ea7\u6905",
}

METHOD_NOTE = {
    "isofix": "\u7a33\u5b9a\u6027\u597d\u3001\u8bef\u88c5\u6982\u7387\u4f4e\uff0c\u80fd\u7528\u5c31\u4f18\u5148\u7528",
    "belt": "\u901a\u7528\uff0c\u4f46\u88c5\u677e\u662f\u6700\u5e38\u89c1\u95ee\u9898\uff0c\u5fc5\u987b\u6309\u8bf4\u660e\u4e66\u89c4\u5b9a\u7684\u7d27\u5ea6\u6536\u7d27",
    "anchor": "\u914d\u5408\u5176\u4ed6\u65b9\u5f0f\u9650\u5236\u503e\u89d2\uff0c\u672a\u6309\u8bf4\u660e\u4e66\u4f7f\u7528\u4f1a\u9002\u5f97\u5176\u53cd",
    "builtin": "\u514d\u5b89\u88c5\uff0c\u4f46\u9002\u914d\u8f66\u578b\u8303\u56f4\u6709\u9650",
}

DIR_CN = {"rearward": "\u540e\u5411\u5b89\u88c5", "forward": "\u524d\u5411\u5b89\u88c5"}

POST_CHECKS = [
    ("\u677e\u7d27", "\u5728\u80a9\u5e26\u6216\u56fa\u5b9a\u70b9\u5904\u634f\u4e00\u4e0b\uff0c\u634f\u8d77\u91cf\u4e0d\u8d85\u8fc7\u8bf4\u660e\u4e66\u89c4\u5b9a\u7684\u539a\u5ea6"),
    ("\u503e\u89d2", "\u786e\u8ba4\u843d\u5728\u4ea7\u54c1\u8bf4\u660e\u4e66\u89c4\u5b9a\u7684\u503e\u89d2\u8303\u56f4\u5185"),
    ("\u9501\u6b62", "\u6643\u52a8\u5ea7\u6905\u4e0e\u5e95\u5ea7\u8fde\u63a5\u5904\u65e0\u677e\u52a8\u3001\u65e0\u4f4d\u79fb"),
    ("\u8d34\u5408", "\u68c0\u67e5\u4e0e\u8f66\u8f86\u5ea7\u6905\u65e0\u660e\u663e\u7a7a\u9699\uff0c\u5b69\u5b50\u80cc\u90e8\u8d34\u5408"),
]

TRIP_CHECKS = [
    "\u5ea7\u6905\u4e0e\u5e95\u5ea7\u8fde\u63a5\u7262\u56fa\uff0c\u6309\u8bf4\u660e\u4e66\u6307\u5b9a\u7684\u9501\u6b62\u6307\u793a\u786e\u8ba4\u5230\u4f4d",
    "\u80a9\u5e26\u6216\u56fa\u5b9a\u5e26\u677e\u7d27\u7b26\u5408\u8bf4\u660e\u4e66\u8981\u6c42",
    "\u503e\u89d2\u4e0e\u5b89\u88c5\u65b9\u5411\u548c\u5b69\u5b50\u7684\u8eab\u9ad8\u4f53\u91cd\u5339\u914d",
    "\u5b69\u5b50\u5165\u5ea7\u540e\u8d34\u5408\u826f\u597d\uff0c\u80a9\u5e26\u9ad8\u5ea6\u6b63\u786e",
    "\u8f66\u4e0a\u6ca1\u6709\u677e\u6563\u7269\u54c1\u80fd\u98de\u51fa\u6216\u5361\u5230\u5b69\u5b50",
    "\u5b69\u5b50\u8863\u7269\u6ca1\u6709\u5377\u5165\u56fa\u5b9a\u5e26",
    "\u5ea7\u6905\u672a\u88ab\u957f\u65f6\u95f4\u66b4\u6652\u540e\u53d8\u5f62",
    "\u8f66\u94a5\u5319\u672a\u7559\u5728\u5b69\u5b50\u53ef\u53ca\u8303\u56f4\u5185",
]

STOP_CASES = [
    ("\u5b69\u5b50\u8d85\u51fa\u8bf4\u660e\u4e66\u89c4\u5b9a\u7684\u8eab\u9ad8\u4f53\u91cd\u8303\u56f4", "\u66f4\u6362\u5230\u9002\u7528\u578b\u53f7"),
    ("\u7ecf\u5386\u8fc7\u4e8b\u6545\uff0c\u5373\u4f7f\u5916\u89c2\u770b\u4e0d\u51fa\u95ee\u9898", "\u505c\u7528\u5e76\u66f4\u6362\u6216\u9001\u68c0"),
    ("\u4f7f\u7528\u5e74\u9650\u5df2\u5230", "\u505c\u7528\u66f4\u6362\uff0c\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e66\u6807\u6ce8\u4e3a\u51c6"),
    ("\u957f\u671f\u66b4\u6652\u540e\u5916\u58f3\u53d8\u5f62\u6216\u7ec7\u5e26\u78e8\u635f", "\u505c\u7528\u66f4\u6362"),
    ("\u5e95\u5ea7\u6216\u8fde\u63a5\u4ef6\u6709\u88c2\u7eb9\u3001\u53d8\u5f62", "\u7acb\u5373\u505c\u7528"),
]

SWITCH_RULES = [
    "\u8eab\u9ad8\u8fbe\u5230\u8bf4\u660e\u4e66\u89c4\u5b9a\u503c",
    "\u4f53\u91cd\u8fbe\u5230\u8bf4\u660e\u4e66\u89c4\u5b9a\u503c",
    "\u540e\u5411\u5b89\u88c5\u5df2\u4e0d\u9002\u7528",
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


def to_float(value, default=0.0):
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return default
    return default


def band_of(age):
    for lo, hi, label, direction in BANDS:
        if lo <= age < hi:
            return label, direction
    return "\u8d85\u51fa\u5e38\u89c1\u8303\u56f4", "\u6309\u4ea7\u54c1\u8bf4\u660e\u4e66\u9002\u7528\u8303\u56f4\u5224\u65ad"


def assess(d):
    age = to_float(d.get("age"), 0.0)
    height = to_float(d.get("height"), 0.0)
    weight = to_float(d.get("weight"), 0.0)
    position = str(d.get("position", "rear")).lower()
    method = str(d.get("method", "isofix")).lower()
    direction = str(d.get("direction", "")).lower()
    return age, height, weight, position, method, direction


def build_report(d):
    age, height, weight, position, method, direction = assess(d)
    label, suggest = band_of(age)
    out = ["# \u513f\u7ae5\u5b89\u5168\u5ea7\u6905\u6838\u67e5\u7ed3\u8bba", ""]
    out.append("| \u9879\u76ee | \u8f93\u5165 |")
    out.append("|---|---|")
    out.append("| \u5e74\u9f84 | %.0f \u5c81 |" % age)
    if height:
        out.append("| \u8eab\u9ad8 | %.0f \u5398\u7c73 |" % height)
    if weight:
        out.append("| \u4f53\u91cd | %.0f \u5343\u514b |" % weight)
    out.append("| \u5b89\u88c5\u4f4d\u7f6e | %s |" % ("\u540e\u6392" if position == "rear" else "\u524d\u6392"))
    out.append("")
    out.append("## \u9636\u6bb5\u5224\u5b9a")
    out.append("")
    out.append("- \u9636\u6bb5\uff1a**%s**" % label)
    out.append("- \u5e38\u89c1\u5b89\u88c5\u65b9\u5411\uff1a%s" % suggest)
    out.append("- \u540e\u5411\u80fd\u7528\u591a\u4e45\u53d6\u51b3\u4e8e\u8eab\u9ad8\u4f53\u91cd\u662f\u5426\u4ecd\u5728\u8bf4\u660e\u4e66\u89c4\u5b9a\u7684\u540e\u5411\u9002\u7528\u8303\u56f4\u5185\uff0c\u4e0d\u53d6\u51b3\u4e8e\u5e74\u9f84")
    out.append("- \u8eab\u9ad8\u4f53\u91cd\u987b\u4e0e\u4ea7\u54c1\u8bf4\u660e\u4e66\u7684\u9002\u7528\u8303\u56f4\u9010\u9879\u6838\u5bf9")
    out.append("")
    out.append("## \u5b89\u88c5\u65b9\u5f0f")
    out.append("")
    out.append("- \u65b9\u5f0f\uff1a**%s**" % METHOD_CN.get(method, "\u672a\u8bc6\u522b\u7684\u65b9\u5f0f"))
    out.append("- \u8bf4\u660e\uff1a%s" % METHOD_NOTE.get(
        method, "\u8bf7\u6309\u4ea7\u54c1\u8bf4\u660e\u4e66\u786e\u8ba4\u5b89\u88c5\u65b9\u5f0f"))
    out.append("- \u5b89\u88c5\u65b9\u5f0f\u7684\u5dee\u5f02\u4e0d\u5982\u5b89\u88c5\u662f\u5426\u5230\u4f4d\u91cd\u8981")
    out.append("")
    out.append("## \u4f4d\u7f6e\u5408\u89c4\u63d0\u793a")
    out.append("")
    if position == "rear":
        out.append("- \u4f4d\u7f6e\u5408\u89c4\uff1a\u540e\u6392\u662f\u63a8\u8350\u4f4d\u7f6e")
    else:
        out.append("- **\u4e0d\u53ef\u628a\u513f\u7ae5\u5ea7\u6905\u88c5\u5728\u6709\u5b89\u5168\u6c14\u56ca\u7684\u524d\u6392**\uff0c\u524d\u5411\u5ea7\u6905\u53ef\u80fd\u88ab\u6c14\u56ca\u5f39\u51fa\u76f4\u63a5\u649e\u51fb\u5b69\u5b50")
        out.append("- \u5373\u4f7f\u80fd\u5173\u95ed\u6c14\u56ca\u4e5f\u4e0d\u5efa\u8bae\uff0c\u5173\u95ed\u72b6\u6001\u53ef\u80fd\u56e0\u6545\u88ab\u8bef\u5f00\u6216\u88ab\u7cfb\u7edf\u81ea\u52a8\u542f\u7528")
        out.append("- \u4f18\u5148\u8c03\u6574\u5ea7\u4f4d\u5b89\u6392\u5230\u540e\u6392\uff0c\u800c\u4e0d\u662f\u5728\u524d\u6392\u51d1\u5408")
    out.append("")
    if direction:
        out.append("## \u5b89\u88c5\u65b9\u5411")
        out.append("")
        out.append("- \u5f53\u524d\u65b9\u5411\uff1a**%s**" % DIR_CN.get(direction, "\u672a\u8bc6\u522b"))
        if direction == "rearward" and age >= 4.0:
            out.append("- \u5e74\u9f84\u5df2\u8fc7 4 \u5c81\uff0c\u4ecd\u540e\u5411\u5c5e\u6b63\u5e38\u505a\u6cd5\uff0c\u4e0d\u8981\u6309\u5e74\u9f84\u786c\u6027\u5207\u6362")
        if direction == "forward" and age < 4.0:
            out.append("- **\u5e74\u9f84\u504f\u5c0f\u65f6\u524d\u5411\u5b89\u88c5\u4e0d\u7b26\u5408\u901a\u7528\u505a\u6cd5\uff0c\u8bf7\u6838\u5bf9\u540e\u5411\u9002\u7528\u8303\u56f4\u7684\u4e09\u4e2a\u6761\u4ef6**")
            for r in SWITCH_RULES:
                out.append("  - %s" % r)
            out.append("- \u4e09\u6761\u90fd\u6ee1\u8db3\u624d\u80fd\u8f6c\u524d\u5411\uff0c\u5177\u4f53\u6570\u503c\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e66\u4e3a\u51c6")
        out.append("")
    out.append("## \u5b89\u88c5\u540e\u56db\u9879\u5fc5\u68c0")
    out.append("")
    for name, how in POST_CHECKS:
        out.append("- **%s**\uff1a%s" % (name, how))
    out.append("")
    out.append("- \u6700\u5e38\u89c1\u7684\u4e24\u4e2a\u95ee\u9898\u662f\u88c5\u677e\u548c\u88c5\u9519\u4f4d\u7f6e")
    out.append("- \u7d27\u5ea6\u4ee5\u8bf4\u660e\u4e66\u8981\u6c42\u4e3a\u51c6\uff0c\u4e0d\u662f\u8d8a\u7d27\u8d8a\u597d\uff0c\u4e5f\u4e0d\u662f\u5dee\u4e0d\u591a\u5c31\u884c")
    out.append("")
    out.append("## \u51fa\u884c\u524d\u68c0\u67e5\u6e05\u5355")
    out.append("")
    for i, item in enumerate(TRIP_CHECKS, 1):
        out.append("%d. %s" % (i, item))
    out.append("")
    out.append("## \u66f4\u6362\u4e0e\u505c\u7528\u5224\u5b9a")
    out.append("")
    out.append("| \u60c5\u51b5 | \u5efa\u8bae |")
    out.append("|---|---|")
    for case, advice in STOP_CASES:
        out.append("| %s | %s |" % (case, advice))
    out.append("")
    out.append("## \u8fb9\u754c")
    out.append("")
    out.append("- \u6d89\u53ca\u6cd5\u89c4\u4e0e\u5b89\u5168\u6807\u51c6\u7684\u90e8\u5206\u4ee5\u73b0\u884c\u89c4\u5b9a\u3001\u8f66\u8f86\u8bf4\u660e\u4e66\u4e0e\u4ea7\u54c1\u8bf4\u660e\u4e66\u8981\u6c42\u4e3a\u51c6")
    out.append("- \u5177\u4f53\u8eab\u9ad8\u4f53\u91cd\u3001\u503e\u89d2\u8303\u56f4\u4e0e\u5e74\u9650\u8981\u6c42\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e66\u4e3a\u51c6")
    out.append("- \u672c\u811a\u672c\u53ea\u505a\u901a\u7528\u9636\u6bb5\u5224\u65ad\uff0c\u4e0d\u66ff\u4ee3\u8bf4\u660e\u4e66\u7684\u5177\u4f53\u8981\u6c42")
    return "\n".join(out) + "\n"


def selftest():
    cases = []
    cases.append(("band_0", band_of(0.5)[0] == "1 \u5c81\u4ee5\u4e0b"))
    cases.append(("band_3", band_of(3.0)[0] == "1 \u5230 4 \u5c81"))
    cases.append(("band_5", band_of(5.0)[0] == "4 \u5230 7 \u5c81"))
    cases.append(("band_9", band_of(9.0)[0] == "7 \u5c81\u4ee5\u4e0a"))
    cases.append(("float_str", to_float("3.5", 0.0) == 3.5))
    cases.append(("float_bad", to_float("abc", 1.0) == 1.0))
    cases.append(("method_belt", METHOD_CN["belt"].startswith("\u5b89\u5168\u5e26")))
    rep = build_report({"age": 3, "height": 102, "weight": 16,
                        "position": "rear", "method": "isofix"})
    cases.append(("rep_stage", "1 \u5230 4 \u5c81" in rep))
    cases.append(("rep_ok_pos", "\u4f4d\u7f6e\u5408\u89c4\uff1a\u540e\u6392\u662f\u63a8\u8350\u4f4d\u7f6e" in rep))
    cases.append(("rep_post", "\u5b89\u88c5\u540e\u56db\u9879\u5fc5\u68c0" in rep))
    cases.append(("rep_trip", "\u51fa\u884c\u524d\u68c0\u67e5\u6e05\u5355" in rep))
    cases.append(("rep_four", rep.count("**") >= 8))
    rep2 = build_report({"age": 2, "position": "front", "method": "belt",
                         "direction": "forward"})
    cases.append(("rep_front_ban", "\u4e0d\u53ef\u628a\u513f\u7ae5\u5ea7\u6905\u88c5\u5728\u6709\u5b89\u5168\u6c14\u56ca\u7684\u524d\u6392" in rep2))
    cases.append(("rep_early_fwd", "\u8bf7\u6838\u5bf9\u540e\u5411\u9002\u7528\u8303\u56f4\u7684\u4e09\u4e2a\u6761\u4ef6" in rep2))
    cases.append(("rep_three_rules", "\u8fbe\u5230\u8bf4\u660e\u4e66\u89c4\u5b9a\u503c" in rep2))
    rep3 = build_report({"age": 6, "position": "rear", "direction": "rearward"})
    cases.append(("rep_late_rear_ok", "\u4ecd\u540e\u5411\u5c5e\u6b63\u5e38\u505a\u6cd5" in rep3))
    cases.append(("rep_stop_case", "\u7ecf\u5386\u8fc7\u4e8b\u6545" in rep2))
    cases.append(("rep_boundary", "\u4ee5\u73b0\u884c\u89c4\u5b9a" in rep))
    cases.append(("rep_method_note", "\u88c5\u677e\u662f\u6700\u5e38\u89c1\u95ee\u9898" in rep2))
    bom = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_probe.json")
    with open(bom, "w", encoding="utf-8-sig") as f:
        f.write('{"age": 2}')
    try:
        cases.append(("bom_ok", to_float(load_json(bom).get("age")) == 2.0))
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
    ap = argparse.ArgumentParser(description="child car seat audit")
    ap.add_argument("--age", default=None)
    ap.add_argument("--height", default=None)
    ap.add_argument("--weight", default=None)
    ap.add_argument("--position", default=None)
    ap.add_argument("--method", default=None)
    ap.add_argument("--direction", default=None)
    ap.add_argument("--file", default=None)
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
    for key, val in (("age", a.age), ("height", a.height), ("weight", a.weight),
                     ("position", a.position), ("method", a.method),
                     ("direction", a.direction)):
        if val is not None:
            data[key] = val
    report = build_report(data)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "car_seat_result.md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
