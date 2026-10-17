# -*- coding: utf-8 -*-
"""road_trip_calc: \u81ea\u9a7e\u6e38\u91cc\u7a0b\u3001\u6cb9\u8017\u3001\u8d39\u7528\u4e0e\u8017\u65f6\u6d4b\u7b97\u3002

\u53ea\u505a\u7b97\u672f\u4f30\u7b97\uff0c\u4e0d\u63d0\u4f9b\u5b9e\u65f6\u8def\u51b5\u4e0e\u9650\u884c\u4fe1\u606f\u3002
"""
import argparse
import json
import os

DEFAULT_SPEED = 70.0

# \u5e02\u533a\u4e0e\u9ad8\u901f\u7684\u6cb9\u8017\u5dee\u5f02\u662f\u7ed3\u6784\u6027\u7684\uff0c\u4f46\u5177\u4f53\u6570\u503c\u4ee5\u81ea\u5df1\u8f66\u7684\u5b9e\u9645\u6570\u636e\u4e3a\u51c6
MODE_NOTE = [
    ("\u9ad8\u901f\u5300\u901f\u5de1\u822a", "\u6cb9\u8017\u5f80\u5f80\u63a5\u8fd1\u751a\u81f3\u4f18\u4e8e\u5e02\u533a", "\u4f46\u9700\u8981\u8fc7\u8def\u8d39"),
    ("\u5e02\u533a\u8d70\u8d70\u505c\u505c", "\u6cb9\u8017\u660e\u663e\u66f4\u9ad8", "\u65e0\u8fc7\u8def\u8d39"),
    ("\u56fd\u9053\u4e0e\u7701\u9053", "\u53d6\u51b3\u4e8e\u8def\u51b5\u4e0e\u8f66\u901f", "\u901a\u5e38\u65e0\u8fc7\u8def\u8d39"),
    ("\u9ad8\u539f\u8def\u6bb5", "\u7a7a\u6c14\u7a00\u8584\uff0c\u6cb9\u8017\u901a\u5e38\u4e0a\u5347", "\u52a8\u529b\u4e5f\u4f1a\u53d7\u5f71\u54cd"),
    ("\u51ac\u5b63\u5f00\u6696\u98ce", "\u6cb9\u8017\u589e\u52a0\u8f83\u660e\u663e", "\u89c4\u5212\u8981\u7559\u4f59\u91cf"),
]

REST_RULE = [
    "\u6bcf\u8fde\u7eed\u9a7e\u9a76\u4e00\u6bb5\u65f6\u95f4\u5c31\u5b89\u6392\u4f11\u606f\uff0c\u4e0d\u8981\u957f\u65f6\u95f4\u4e0d\u95f4\u65ad",
    "\u4f11\u606f\u8981\u771f\u6b63\u79bb\u5f00\u9a7e\u9a76\u4f4d\uff0c\u6d3b\u52a8\u4e00\u4e0b",
    "\u75b2\u52b3\u4fe1\u53f7\uff1a\u6253\u54c8\u6b20\u3001\u6ce8\u610f\u529b\u6da3\u6563\u3001\u53cd\u5e94\u53d8\u6162\u3001\u9891\u7e41\u7728\u773c",
    "\u51fa\u73b0\u75b2\u52b3\u4fe1\u53f7\u7acb\u5373\u505c\u8f66\u4f11\u606f\uff0c\u4e0d\u8981\u9760\u559d\u5496\u5561\u786c\u6491",
    "\u8fde\u7eed\u9a7e\u9a76\u7684\u5177\u4f53\u65f6\u957f\u9650\u5236\u4ee5\u73b0\u884c\u89c4\u5b9a\u548c\u5f53\u5730\u4e3b\u7ba1\u90e8\u95e8\u8981\u6c42\u4e3a\u51c6",
]

CHECK_VEHICLE = [
    "\u673a\u6cb9\u3001\u51b7\u5374\u6db2\u3001\u73bb\u7483\u6c34\u6db2\u4f4d\u6b63\u5e38",
    "\u56db\u6761\u80ce\u7684\u80ce\u538b\u4e0e\u80ce\u7eb9\u90fd\u770b\u8fc7",
    "\u5239\u8f66\u72b6\u6001\u6b63\u5e38",
    "\u706f\u5149\u6b63\u5e38\uff0c\u542b\u5239\u8f66\u706f\u4e0e\u8f6c\u5411\u706f",
    "\u96e8\u5237\u5de5\u4f5c\u6b63\u5e38",
    "\u5907\u80ce\u53ef\u7528\u4e14\u6c14\u538b\u6b63\u5e38",
    "\u968f\u8f66\u5de5\u5177\u4e0e\u4e09\u89d2\u8b66\u793a\u724c\u9f50\u5168",
    "\u71c3\u6cb9\u6216\u7535\u91cf\u8db3\u591f\u5230\u8fbe\u76ee\u7684\u5730",
]

CHECK_DOC = [
    "\u9a7e\u9a76\u8bc1\u3001\u884c\u9a76\u8bc1\u3001\u8eab\u4efd\u8bc1\u4ef6\u9f50\u5168\u6709\u6548",
    "\u5e38\u7528\u836f\u54c1\u3001\u996e\u7528\u6c34\u3001\u5c11\u91cf\u98df\u54c1",
    "\u624b\u673a\u3001\u5145\u7535\u7ebf\u3001\u8f66\u5145",
    "\u5bfc\u822a\u8bbe\u5907\u6216\u79bb\u7ebf\u5730\u56fe\uff0c\u4fe1\u53f7\u4e0d\u597d\u7684\u8def\u6bb5\u9700\u8981\u79bb\u7ebf\u5730\u56fe",
    "\u5e94\u6025\u8054\u7cfb\u65b9\u5f0f\u5df2\u4fdd\u5b58",
    "\u8def\u7ebf\u4e0e\u5907\u7528\u8def\u7ebf\u5df2\u89c4\u5212\uff0c\u4f4f\u5bbf\u9884\u8ba2\u4fe1\u606f\u5df2\u786e\u8ba4",
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


def fuel_cost(km, consumption, price):
    """Return fuel cost; km and consumption are validated non-negative."""
    km = max(0.0, km)
    consumption = max(0.0, consumption)
    price = max(0.0, price)
    if consumption <= 0:
        return 0.0
    return km / 100.0 * consumption * price


def total_cost(km, consumption, price, toll, park):
    return fuel_cost(km, consumption, price) + max(0.0, toll) + max(0.0, park)


def hours_for(km, speed):
    speed = max(1.0, speed)
    return max(0.0, km) / speed


def build_report(d):
    km = to_float(d.get("km"), 0.0)
    cons = to_float(d.get("consumption"), 0.0)
    price = to_float(d.get("price"), 0.0)
    toll = to_float(d.get("toll"), 0.0)
    park = to_float(d.get("park"), 0.0)
    speed = to_float(d.get("speed"), DEFAULT_SPEED)
    if speed <= 0:
        speed = DEFAULT_SPEED

    fuel = fuel_cost(km, cons, price)
    total = total_cost(km, cons, price, toll, park)
    hours = hours_for(km, speed)

    out = ["# \u81ea\u9a7e\u6e38\u8d39\u7528\u4e0e\u8017\u65f6\u6d4b\u7b97", ""]
    out.append("| \u9879\u76ee | \u6570\u503c |")
    out.append("|---|---|")
    out.append("| \u603b\u91cc\u7a0b | %.0f \u516c\u91cc |" % km)
    out.append("| \u767e\u516c\u91cc\u6cb9\u8017 | %.1f \u5347 |" % cons)
    out.append("| \u6cb9\u4ef7 | %.2f \u5143\u6bcf\u5347 |" % price)
    out.append("| \u8fc7\u8def\u8d39 | %.0f \u5143 |" % toll)
    out.append("| \u505c\u8f66\u8d39 | %.0f \u5143 |" % park)
    out.append("| \u89c4\u5212\u5e73\u5747\u8f66\u901f | %.0f \u516c\u91cc\u6bcf\u5c0f\u65f6 |" % speed)
    out.append("")
    out.append("## \u8d39\u7528")
    out.append("")
    out.append("- \u6cb9\u8d39\uff1a**%.0f \u5143**" % fuel)
    out.append("- \u8fc7\u8def\u8d39\uff1a%.0f \u5143" % toll)
    out.append("- \u505c\u8f66\u8d39\uff1a%.0f \u5143" % park)
    out.append("- **\u5408\u8ba1\uff1a%.0f \u5143**" % total)
    out.append("")
    out.append("- \u6d4b\u7b97\u53e3\u5f84\uff1a\u6cb9\u8d39\u7b49\u4e8e\u603b\u91cc\u7a0b\u9664\u4ee5\u767e\u516c\u91cc\u6cb9\u8017\u518d\u4e58\u6cb9\u4ef7")
    out.append("- \u5b9e\u9645\u91cc\u7a0b\u901a\u5e38\u5927\u4e8e\u5bfc\u822a\u91cc\u7a0b\uff0c\u627e\u8def\u3001\u7ed5\u884c\u3001\u7b49\u7ea2\u706f\u90fd\u4f1a\u589e\u52a0")
    out.append("- \u6cb9\u8017\u8bf7\u7528\u81ea\u5df1\u8f66\u7684\u5b9e\u9645\u6570\u636e\uff0c\u4e0d\u540c\u8f66\u578b\u4e0e\u8def\u51b5\u5dee\u5f02\u5f88\u5927")
    out.append("- \u8fc7\u8def\u8d39\u6807\u51c6\u4ee5\u73b0\u884c\u89c4\u5b9a\u548c\u5b9e\u9645\u516c\u5e03\u4e3a\u51c6")
    out.append("")
    out.append("## \u8017\u65f6")
    out.append("")
    out.append("- \u6309\u89c4\u5212\u8f66\u901f\u4f30\u7b97\uff1a\u7ea6 **%.1f \u5c0f\u65f6**\uff08\u7ea6 %.0f \u5206\u949f\uff09" % (
        hours, hours * 60.0))
    out.append("- \u89c4\u5212\u8f66\u901f\u5df2\u542b\u5835\u8f66\u4e0e\u627e\u8def\u7684\u4f59\u91cf\uff0c\u4f46\u4ecd\u5efa\u8bae\u518d\u7559\u4f59\u91cf")
    out.append("- \u4e0d\u8981\u7528\u7406\u8bba\u65f6\u901f\u76f4\u63a5\u9664\u8ddd\u79bb\uff0c\u7ea2\u7eff\u706f\u3001\u670d\u52a1\u533a\u3001\u7528\u9910\u90fd\u8981\u7b97\u8fdb\u53bb")
    out.append("")
    out.append("## \u9ad8\u901f\u4e0e\u666e\u901a\u9053\u8def\u7684\u7ed3\u6784\u5dee\u5f02")
    out.append("")
    out.append("| \u573a\u666f | \u6cb9\u8017 | \u8d39\u7528 |")
    out.append("|---|---|---|")
    for scene, fuel_note, fee_note in MODE_NOTE:
        out.append("| %s | %s | %s |" % (scene, fuel_note, fee_note))
    out.append("")
    out.append("\u9ad8\u901f\u672a\u5fc5\u6bd4\u56fd\u9053\u66f4\u8d39\u6cb9\uff0c\u5300\u901f\u5de1\u822a\u65f6\u6cb9\u8017\u5f80\u5f80\u63a5\u8fd1\u751a\u81f3\u66f4\u4f18\uff1b"
               "\u4f46\u9ad8\u901f\u7684\u8fc7\u8def\u8d39\u901a\u5e38\u663e\u8457\u9ad8\u4e8e\u666e\u901a\u9053\u8def\uff0c\u603b\u8d39\u7528\u8981\u4e00\u8d77\u7b97\u3002")
    out.append("")
    out.append("## \u4f11\u606f\u5b89\u6392")
    out.append("")
    for r in REST_RULE:
        out.append("- %s" % r)
    out.append("")
    out.append("## \u51fa\u53d1\u524d\u8f66\u8f86\u68c0\u67e5")
    out.append("")
    for c in CHECK_VEHICLE:
        out.append("- [ ] %s" % c)
    out.append("")
    out.append("## \u51fa\u53d1\u524d\u8bc1\u4ef6\u4e0e\u7269\u8d44")
    out.append("")
    for c in CHECK_DOC:
        out.append("- [ ] %s" % c)
    out.append("")
    out.append("## \u8fb9\u754c")
    out.append("")
    out.append("- \u8def\u51b5\u3001\u9650\u884c\u3001\u65bd\u5de5\u4e0e\u4e34\u65f6\u7ba1\u5236\u4fe1\u606f\u4ee5\u5b9e\u65f6\u4ea4\u901a\u4fe1\u606f\u548c\u5f53\u5730\u4e3b\u7ba1\u90e8\u95e8\u516c\u5e03\u4e3a\u51c6")
    out.append("- \u672c\u811a\u672c\u4e0d\u63d0\u4f9b\u4e5f\u4e0d\u63a8\u6d4b\u5b9e\u65f6\u8def\u51b5")
    out.append("- \u6cb9\u8017\u4e0e\u8017\u65f6\u7684\u4f30\u7b97\u4e0d\u4ee3\u8868\u5b9e\u9645\u6d4b\u91cf\u503c")
    out.append("- \u8fc7\u8def\u8d39\u4e0e\u505c\u8f66\u8d39\u6807\u51c6\u4ee5\u73b0\u884c\u89c4\u5b9a\u548c\u5b9e\u9645\u516c\u5e03\u4e3a\u51c6")
    return "\n".join(out) + "\n"


def selftest():
    cases = []
    cases.append(("fuel_basic", abs(fuel_cost(520, 8.0, 8.0) - 332.8) < 1e-6))
    cases.append(("fuel_zero_km", fuel_cost(0, 8.0, 8.0) == 0.0))
    cases.append(("fuel_zero_cons", fuel_cost(500, 0, 8.0) == 0.0))
    cases.append(("fuel_neg", fuel_cost(-100, 8.0, 8.0) == 0.0))
    cases.append(("total_sum", abs(total_cost(100, 8.0, 8.0, 50, 30) - 144.0) < 1e-6))
    cases.append(("total_neg_park", total_cost(100, 8.0, 8.0, 50, -10) == 114.0))
    cases.append(("hours", abs(hours_for(700, 70.0) - 10.0) < 1e-9))
    cases.append(("hours_zero_speed", hours_for(700, 0) > 0))
    cases.append(("float_str", to_float("8.5", 0.0) == 8.5))
    cases.append(("float_bad", to_float("abc", 1.0) == 1.0))
    rep = build_report({"km": 520, "consumption": 8.5, "price": 7.8,
                        "toll": 240, "park": 60, "speed": 70})
    cases.append(("rep_fuel", "\u6cb9\u8d39" in rep))
    cases.append(("rep_total", "\u5408\u8ba1" in rep))
    cases.append(("rep_hours", "\u8017\u65f6" in rep))
    cases.append(("rep_mode", "\u9ad8\u901f\u4e0e\u666e\u901a\u9053\u8def\u7684\u7ed3\u6784\u5dee\u5f02" in rep))
    cases.append(("rep_rest", "\u75b2\u52b3\u4fe1\u53f7" in rep))
    cases.append(("rep_check", "\u5907\u80ce\u53ef\u7528\u4e14\u6c14\u538b\u6b63\u5e38" in rep))
    cases.append(("rep_offline", "\u79bb\u7ebf\u5730\u56fe" in rep))
    cases.append(("rep_traffic", "\u5b9e\u65f6\u4ea4\u901a\u4fe1\u606f" in rep))
    cases.append(("rep_cost_formula", "\u6cb9\u8d39\u7b49\u4e8e\u603b\u91cc\u7a0b" in rep))
    rep2 = build_report({"km": 100, "consumption": 0, "price": 0,
                         "toll": 0, "park": 0})
    cases.append(("rep_zero_cost", "\u5408\u8ba1\uff1a0 \u5143" in rep2))
    bom = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_probe.json")
    with open(bom, "w", encoding="utf-8-sig") as f:
        f.write('{"km": 520, "consumption": 8.5}')
    try:
        cases.append(("bom_ok", to_float(load_json(bom).get("km")) == 520.0))
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
    ap = argparse.ArgumentParser(description="road trip cost and time estimate")
    ap.add_argument("--km", default=None)
    ap.add_argument("--consumption", default=None)
    ap.add_argument("--price", default=None)
    ap.add_argument("--toll", default=None)
    ap.add_argument("--park", default=None)
    ap.add_argument("--speed", default=None)
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
    for key, val in (("km", a.km), ("consumption", a.consumption),
                     ("price", a.price), ("toll", a.toll), ("park", a.park),
                     ("speed", a.speed)):
        if val is not None:
            data[key] = val
    if not data:
        data = {"km": 300, "consumption": 8.0, "price": 8.0, "toll": 150, "park": 40}
    report = build_report(data)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "road_trip_result.md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
