# -*- coding: utf-8 -*-
"""home_mesh_planner: \u5bb6\u5ead\u7ec4\u7f51\u62d3\u6251\u9009\u578b\u4e0e\u8282\u70b9\u6570\u4f30\u7b97\u3002

\u7528\u6cd5:
    python home_mesh_planner.py --area 128 --walls 6 --floors 2 --devices 22
    python home_mesh_planner.py --file plan.json --out result.md
    python home_mesh_planner.py --selftest
"""
import argparse
import json
import os

TOPO_CN = {
    "single": "\u5355\u53f0\u65e0\u7ebf\u8def\u7531\u5668",
    "mesh": "\u8def\u7531\u5668 + Mesh \u5b50\u8282\u70b9",
    "wired-ap": "\u8def\u7531 + \u6709\u7ebf AP",
}

REASON_CN = {
    "size": "\u9762\u79ef\u5927\u6216\u627f\u91cd\u5899\u591a\u6216\u8de8\u5c42",
    "wire": "\u80fd\u5e03\u7f51\u7ebf",
    "devices": "\u65e0\u7ebf\u8bbe\u5907\u6570\u91cf\u504f\u591a",
    "small": "\u9762\u79ef\u4e0e\u627f\u91cd\u5899\u90fd\u5728\u5355\u53f0\u53ef\u8986\u76d6\u8303\u56f4\u5185",
}

BACKBAND = [
    (300.0, "100Mbps", True),
    (500.0, "200Mbps", True),
    (1000.0, "500Mbps", False),
    (float("inf"), "1000Mbps", False),
]

BAN_LINES = [
    "\u5f31\u7535\u7bb1\u5185\u90e8\uff1a\u91d1\u5c5e\u5c01\u95ed\u7a7a\u95f4\u628a\u5929\u7ebf\u5305\u4f4f\uff0c\u8986\u76d6\u660e\u663e\u53d8\u5dee",
    "\u7d27\u90bb\u91d1\u5c5e\u67dc\u3001\u9c7c\u7f38\u3001\u955c\u9762\uff1a\u53cd\u5c04\u4e0e\u906e\u6321\u9020\u6210\u4fe1\u53f7\u7a7a\u6d1e",
    "\u7d27\u90bb\u5fae\u6ce2\u7089\uff1a\u5de5\u4f5c\u65f6 2.4G \u660e\u663e\u53d7\u5e72\u6270",
    "\u5929\u82b1\u677f\u5939\u5c42\u6216\u540a\u9876\u5185\uff1a\u6563\u70ed\u5dee\u4e14\u4fe1\u53f7\u88ab\u538b\u5236",
]

BAN_OK = [
    "\u5c45\u4e2d\u5f00\u9614\u3001\u79bb\u5730 1-1.5 \u7c73",
    "\u8ddf\u7740\u7f51\u7ebf\u8d70\u7684\u6709\u7ebf AP",
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


def num(value, default):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return float(default)
    if f < 0:
        return float(default)
    return f


def estimate_units(area, walls, floors):
    """Rough coverage-unit count. Floors dominate; walls cut penetration."""
    base = area / 50.0
    wall_penalty = 0.18 * walls
    floor_bonus = 0.9 * max(0.0, floors - 1)
    units = base + wall_penalty + floor_bonus
    if units < 1.0:
        units = 1.0
    return units


def pick_topology(area, walls, floors, devices, wire):
    """Ordered decision table, mirroring rules/home_mesh_rules.md."""
    if wire:
        return "wired-ap", "wire"
    if floors > 1 or area > 90.0 or walls > 4:
        return "mesh", "size"
    if devices >= 25:
        return "mesh", "devices"
    return "single", "small"


def backband(link_mbps, wireless):
    """Return (minimum backhaul bandwidth string, wireless viable flag)."""
    for cap, floor, wireless_ok in BACKBAND:
        if link_mbps <= cap:
            if wireless and not wireless_ok:
                return floor, False
            return floor, wireless_ok
    return "1000Mbps", False


def build_report(p):
    area = num(p.get("area"), 100)
    walls = num(p.get("walls"), 3)
    floors = num(p.get("floors"), 1)
    devices = num(p.get("devices"), 10)
    link = num(p.get("link_mbps"), 500)
    wire = str(p.get("wire", "no")).lower() in ("yes", "y", "true", "1")

    key, reason = pick_topology(area, walls, floors, devices, wire)
    nodes = int(estimate_units(area, walls, floors))
    if nodes < 1:
        nodes = 1
    wireless = key == "mesh"
    floor_bw, wireless_ok = backband(link, wireless)

    out = []
    out.append("# \u5bb6\u5ead\u7ec4\u7f51\u9009\u578b\u4f30\u7b97")
    out.append("")
    out.append("| \u9879\u76ee | \u53c2\u6570 |")
    out.append("|---|---|")
    out.append("| \u5efa\u7b51\u9762\u79ef | %.0f \u5e73\u65b9\u7c73 |" % area)
    out.append("| \u4e3b\u8981\u627f\u91cd\u5899 | %.0f \u9053 |" % walls)
    out.append("| \u697c\u5c42 | %.0f |" % floors)
    out.append("| \u5728\u7ebf\u65e0\u7ebf\u8bbe\u5907 | %.0f \u53f0 |" % devices)
    out.append("| \u5165\u6237\u5b9e\u6d4b\u901f\u7387 | %.0fMbps |" % link)
    out.append("| \u80fd\u5426\u5e03\u7f51\u7ebf | %s |" % ("\u662f" if wire else "\u5426"))
    out.append("")
    out.append("## \u63a8\u8350\u62d3\u6251")
    out.append("")
    out.append("- \u62d3\u6251\uff1a**%s**" % TOPO_CN[key])
    out.append("- \u5224\u5b9a\u4f9d\u636e\uff1a%s" % REASON_CN[reason])
    out.append("- \u8282\u70b9\u6570\u4f30\u7b97\uff1a**%d \u4e2a**\uff08\u4f30\u7b97\u8d77\u70b9\uff0c\u6700\u7ec8\u4ee5\u9010\u70b9\u5b9e\u6d4b\u4e3a\u51c6\uff09" % nodes)
    out.append("- \u56de\u7a0b\u5e26\u5bbd\u4e0b\u9650\uff1a**%s**" % floor_bw)
    if wireless:
        if wireless_ok:
            out.append("- \u65e0\u7ebf\u56de\u7a0b\uff1a\u53ef\u7528\uff0c\u4f46\u5b9e\u6d4b\u901a\u5e38\u53ea\u6709\u76f4\u8fde\u901f\u7387\u7684\u4e00\u534a\u5de6\u53f3\uff0c\u8de8\u697c\u5c42\u8fd8\u8981\u518d\u6253\u6298")
        else:
            out.append("- \u65e0\u7ebf\u56de\u7a0b\uff1a**\u4e0d\u5efa\u8bae**\uff0c\u8bf7\u4f18\u5148\u6709\u7ebf\u56de\u7a0b\u6216\u964d\u4f4e\u63a5\u5165\u901f\u7387\u9884\u671f")
        out.append("- \u9891\u6bb5\u5206\u5de5\uff1a5G \u4f18\u5148\u7559\u7ed9\u56de\u7a0b\uff0c2.4G \u7559\u7ed9\u667a\u80fd\u5bb6\u5c45\u8bbe\u5907")
    else:
        out.append("- \u56de\u7a0b\u65b9\u5f0f\uff1a\u4f18\u5148\u6709\u7ebf\u56de\u7a0b\uff0c\u6bcf\u4e2a AP \u90fd\u8981\u6709\u7f51\u7ebf\u5230\u4f4d")
        out.append("- \u9891\u6bb5\u5206\u5de5\uff1a5G \u4f9b\u624b\u673a\u7535\u8111\uff0c2.4G \u4f9b\u667a\u80fd\u5bb6\u5c45\u8bbe\u5907")
    out.append("")
    out.append("## SSID \u7b56\u7565")
    out.append("")
    out.append("- \u5efa\u8bae 2.4G \u4e0e 5G \u5206\u5f00\u547d\u540d\uff0c\u65b9\u4fbf\u6309\u8bbe\u5907\u7c7b\u578b\u7ed1\u5b9a\uff0c\u4e5f\u4fbf\u4e8e\u5206\u9891\u6bb5\u6d4b\u901f")
    out.append("- \u53cc\u9891\u5408\u4e00\u4ec5\u5728\u8bbe\u5907\u4e0d\u652f\u6301\u624b\u52a8\u9009\u9891\u3001\u4e14\u6ca1\u6709\u667a\u80fd\u5bb6\u5c45\u8bbe\u5907\u65f6\u624d\u8003\u8651")
    out.append("")
    out.append("## \u6446\u653e\u7981\u5fcc")
    out.append("")
    for line in BAN_LINES:
        out.append("- \u7981\u6b62\uff1a" + line)
    for line in BAN_OK:
        out.append("- \u63a8\u8350\uff1a" + line)
    out.append("")
    out.append("## \u9a8c\u6536\u6e05\u5355")
    out.append("")
    out.append("1. \u6709\u7ebf\u76f4\u8fde\u6d4b\u901f\u4f5c\u4e3a\u57fa\u7ebf\uff0cWiFi \u4e0d\u53ef\u80fd\u8d85\u8fc7\u5b83")
    out.append("2. \u6bcf\u4e2a\u623f\u95f4\u5206\u522b\u6d4b 5G \u4e0e 2.4G \u5404\u4e09\u6b21\uff0c\u53d6\u4e2d\u4f4d\u6570")
    out.append("3. \u5206\u65f6\u6bb5\u6d4b\uff1a\u767d\u5929\u4e00\u6b21\uff0c\u665a\u9ad8\u5cf0\u4e00\u6b21")
    out.append("4. \u4e3b\u8282\u70b9\u4e0d\u8981\u585e\u5728\u5f31\u7535\u7bb1\u91cc")
    out.append("5. \u6f2b\u6e38\u8981\u9a8c\u8bc1\u8fde\u63a5\u771f\u7684\u5207\u6362\uff0c\u53ea\u6709\u4fe1\u53f7\u683c\u6570\u53d8\u5316\u4e0d\u7b97\u6f2b\u6e38")
    out.append("6. \u6ee1\u683c\u8fd8\u6162\u5c5e\u4e8e\u5e72\u6270\u95ee\u9898\uff0c\u8f6c\u5230\u4fe1\u9053\u6392\u67e5\u800c\u4e0d\u662f\u7ee7\u7eed\u52a0\u8282\u70b9")
    out.append("")
    out.append("## \u8fb9\u754c")
    out.append("")
    out.append("- \u8282\u70b9\u6570\u4e3a\u4f30\u7b97\u503c\uff0c\u4ee5\u73b0\u573a\u5b9e\u6d4b\u4e3a\u51c6")
    out.append("- \u9891\u6bb5\u4e0e\u529f\u7387\u7684\u5408\u89c4\u8981\u6c42\u4ee5\u5f53\u5730\u65e0\u7ebf\u7535\u7ba1\u7406\u89c4\u5b9a\u4e0e\u8bbe\u5907\u6838\u51c6\u4e3a\u51c6")
    out.append("- \u4e0d\u53d8\u66f4\u5149\u732b\u7684\u6ce8\u518c\u4e0e\u8ba4\u8bc1\u53c2\u6570")
    out.append("- \u5e03\u7ebf\u3001\u4f9b\u7535\u4e0e\u767b\u9ad8\u4f5c\u4e1a\u7531\u4e13\u4e1a\u4eba\u5458\u65bd\u5de5")
    return "\n".join(out) + "\n"


def selftest():
    cases = []
    cases.append(("single_small", pick_topology(70, 2, 1, 10, False)[0] == "single"))
    cases.append(("mesh_big", pick_topology(128, 6, 2, 22, False)[0] == "mesh"))
    cases.append(("wired_wins", pick_topology(128, 6, 2, 22, True)[0] == "wired-ap"))
    cases.append(("mesh_device", pick_topology(80, 2, 1, 30, False)[0] == "mesh"))
    cases.append(("mesh_floor", pick_topology(60, 1, 2, 8, False)[0] == "mesh"))
    cases.append(("mesh_wall", pick_topology(60, 5, 1, 8, False)[0] == "mesh"))
    cases.append(("units_min", estimate_units(10, 0, 1) == 1.0))
    cases.append(("units_monotonic", estimate_units(150, 8, 3) > estimate_units(60, 2, 1)))
    cases.append(("bw_500_wl", backband(500, True) == ("200Mbps", True)))
    cases.append(("bw_1000_wl", backband(1000, True)[1] is False))
    cases.append(("bw_1000_floor", backband(1000, False)[0] == "500Mbps"))
    cases.append(("bw_small", backband(200, True) == ("100Mbps", True)))
    cases.append(("bw_huge", backband(5000, False)[0] == "1000Mbps"))
    cases.append(("num_default", num("abc", 5) == 5.0))
    cases.append(("num_neg", num(-3, 7) == 7.0))
    rep = build_report({"area": 128, "walls": 6, "floors": 2,
                        "devices": 22, "wire": "no", "link_mbps": 1000})
    cases.append(("rep_topo", "Mesh" in rep))
    cases.append(("rep_nodes", "\u8282\u70b9\u6570\u4f30\u7b97" in rep))
    cases.append(("rep_bw", "500Mbps" in rep))
    cases.append(("rep_ban", "\u5f31\u7535\u7bb1" in rep))
    cases.append(("rep_wire", "\u6709\u7ebf\u56de\u7a0b" in rep))
    bom = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_probe.json")
    with open(bom, "w", encoding="utf-8-sig") as f:
        f.write('{"area": 90}')
    try:
        cases.append(("bom_ok", load_json(bom).get("area") == 90))
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
    ap = argparse.ArgumentParser(description="home mesh topology planner")
    ap.add_argument("--area", default=None)
    ap.add_argument("--walls", default=None)
    ap.add_argument("--floors", default=None)
    ap.add_argument("--devices", default=None)
    ap.add_argument("--link-mbps", dest="link_mbps", default=None)
    ap.add_argument("--wire", default=None)
    ap.add_argument("--file", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--format", default="md")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    params = {}
    if a.file:
        try:
            params = load_json(a.file)
        except Exception as exc:
            print(str(exc))
            return 2
    for key, val in (("area", a.area), ("walls", a.walls), ("floors", a.floors),
                     ("devices", a.devices), ("link_mbps", a.link_mbps), ("wire", a.wire)):
        if val is not None:
            params[key] = val
    if not params:
        params = {"area": 100, "walls": 3, "floors": 1, "devices": 10,
                  "wire": "no", "link_mbps": 500}
    report = build_report(params)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "home_mesh_result.md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
