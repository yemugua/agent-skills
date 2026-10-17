# -*- coding: utf-8 -*-
"""ev_charge_calc: \u7535\u52a8\u8f66\u5145\u7535\u65f6\u957f\u4e0e\u89c4\u5212\u91cc\u7a0b\u4f30\u7b97\u3002

\u7528\u6cd5:
    python ev_charge_calc.py --pack 75 --current 25 --target 80 --power 60 --type ac
    python ev_charge_calc.py --file plan.json --out result.md
    python ev_charge_calc.py --selftest
"""
import argparse
import json
import os

TYPE_CN = {"ac": "\u4ea4\u6d41\u6162\u5145", "dc": "\u76f4\u6d41\u5feb\u5145"}

POWER_HINT = {
    "ac": "\u4ea4\u6d41\u6162\u5145\u7684\u901f\u5ea6\u53d7\u8f66\u8f86\u7aef\u5145\u7535\u673a\u9650\u5236\uff0c\u529f\u7387\u53d6\u8f66\u8f86\u4e0e\u6869\u4e2d\u8f83\u5c0f\u7684\u503c",
    "dc": "\u76f4\u6d41\u5feb\u5145\u7531\u6869\u63d0\u4f9b\u529f\u7387\uff0c\u540c\u65f6\u53d7\u8f66\u8f86\u63a5\u53d7\u4e0a\u9650\u9650\u5236",
}

# \u6536\u5c3e\u4f59\u91cf\u6bd4\u4f8b\uff1a\u5145\u7535\u672b\u671f\u529f\u7387\u4e0b\u964d\uff0c\u9ad8\u7535\u91cf\u533a\u95f4\u5c24\u5176\u660e\u663e
TAIL_RATIO = {"ac": 0.18, "dc": 0.12}

CURVE_NOTE = "\u5145\u7535\u540e\u671f\u529f\u7387\u4f1a\u4e0b\u964d\uff0c\u4ece\u4f4e\u7535\u91cf\u5230\u9ad8\u7535\u91cf\u901a\u5e38\u6bd4\u7ebf\u6027\u4f30\u7b97\u66f4\u4e45"


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


def clamp_pct(value):
    if value < 0:
        return 0.0
    if value > 100:
        return 100.0
    return float(value)


def charge_plan(pack, current, target, power, ctype, loss):
    """Return (need_kwh, ideal_h, est_h, tail_h)."""
    pack = max(0.0, pack)
    current = clamp_pct(current)
    target = clamp_pct(target)
    power = max(0.1, power)
    loss = min(max(loss, 0.1), 1.0)
    eff = 1.0 - loss
    need = max(0.0, (target - current) / 100.0 * pack)
    if target <= current:
        need = 0.0
    ideal = need / power
    tail = ideal * TAIL_RATIO.get(ctype, 0.15)
    return need, ideal, ideal + tail, tail


def plan_range(display_km, loss):
    """Apply a planning discount to a displayed range figure."""
    loss = min(max(loss, 0.1), 1.0)
    return max(0.0, display_km * loss)


def build_report(d):
    pack = to_float(d.get("pack"), 60.0)
    current = to_float(d.get("current"), 20.0)
    target = to_float(d.get("target"), 80.0)
    power = to_float(d.get("power"), 50.0)
    ctype = str(d.get("type", "ac")).lower()
    if ctype not in TYPE_CN:
        ctype = "ac"
    loss = to_float(d.get("loss"), 0.75)
    display_km = to_float(d.get("display_km"), 0.0)

    need, ideal, est, tail = charge_plan(pack, current, target, power, ctype, loss)
    out = ["# \u5145\u7535\u65f6\u957f\u4e0e\u7eed\u822a\u4f30\u7b97", ""]
    out.append("| \u9879\u76ee | \u8f93\u5165 |")
    out.append("|---|---|")
    out.append("| \u7535\u6c60\u5bb9\u91cf | %.0f \u5343\u74e6\u65f6 |" % pack)
    out.append("| \u5f53\u524d\u7535\u91cf | %.0f%% |" % current)
    out.append("| \u76ee\u6807\u7535\u91cf | %.0f%% |" % target)
    out.append("| \u5145\u7535\u529f\u7387 | %.0f \u5343\u74e6 |" % power)
    out.append("| \u5145\u7535\u7c7b\u578b | %s |" % TYPE_CN[ctype])
    out.append("| \u89c4\u5212\u6298\u635f\u7cfb\u6570 | %.2f |" % loss)
    out.append("")
    out.append("## \u5145\u7535\u65f6\u957f\u4f30\u7b97")
    out.append("")
    out.append("- \u9700\u8981\u8865\u5145\u7684\u7535\u91cf\uff1a**%.1f \u5343\u74e6\u65f6**" % need)
    out.append("- \u7406\u60f3\u65f6\u957f\uff08\u4e0d\u542b\u6536\u5c3e\uff09\uff1a\u7ea6 **%.1f \u5c0f\u65f6**" % ideal)
    out.append("- \u6536\u5c3e\u4f59\u91cf\uff1a\u7ea6 **%.1f \u5c0f\u65f6**" % tail)
    out.append("- \u4f30\u7b97\u603b\u65f6\u957f\uff1a\u7ea6 **%.1f \u5c0f\u65f6**\uff08\u7ea6 %.0f \u5206\u949f\uff09" % (est, est * 60.0))
    out.append("")
    out.append("- %s" % CURVE_NOTE)
    out.append("- \u529f\u7387\u53d6\u503c\u8bf4\u660e\uff1a%s" % POWER_HINT[ctype])
    out.append("- \u7528\u9700\u8981\u8865\u5145\u7684\u7535\u91cf\u7b97\uff0c\u4e0d\u8981\u62ff\u6ee1\u5bb9\u91cf\u53bb\u9664")
    out.append("")
    if display_km:
        out.append("## \u89c4\u5212\u91cc\u7a0b")
        out.append("")
        out.append("- \u8868\u663e\u91cc\u7a0b\uff1a%.0f \u516c\u91cc" % display_km)
        out.append("- \u6309\u6298\u635f\u7cfb\u6570 %.2f \u89c4\u5212\uff1a\u7ea6 **%.0f \u516c\u91cc**" % (
            loss, plan_range(display_km, loss)))
        out.append("- \u8868\u663e\u662f\u4f30\u7b97\u503c\uff0c\u4e0d\u662f\u7cbe\u786e\u5269\u4f59\u7535\u91cf")
        out.append("- \u9ad8\u901f\u884c\u9a76\u4e0e\u4f4e\u901f\u5f00\u6696\u98ce\u4f1a\u660e\u663e\u589e\u52a0\u6d88\u8017")
        out.append("- \u4f4e\u6e29\u73af\u5883\u4e0b\u53ef\u7528\u5bb9\u91cf\u4e0b\u964d\uff0c\u5b9e\u9645\u53ef\u80fd\u8dd1\u4e0d\u5230\u8868\u663e\u91cc\u7a0b")
        out.append("- \u76ee\u7684\u5730\u5145\u7535\u6869\u4f4d\u7f6e\u4e0d\u786e\u5b9a\u65f6\u8981\u518d\u7559\u4f59\u91cf")
        out.append("")
    out.append("## \u5e38\u89c1\u6545\u969c\u5904\u7f6e")
    out.append("")
    out.append("| \u73b0\u8c61 | \u5904\u7f6e\u987a\u5e8f |")
    out.append("|---|---|")
    out.append("| \u8df3\u67aa | \u5148\u786e\u8ba4\u662f\u5426\u5df2\u8fbe\u76ee\u6807\u7535\u91cf\uff1b\u53cd\u590d\u8df3\u67aa\u8054\u7cfb\u8fd0\u8425\u65b9 |")
    out.append("| \u67aa\u62d4\u4e0d\u4e0b\u6765 | \u4e0d\u8981\u786c\u62c9\uff1b\u8f66\u8f86\u7aef\u7ed3\u675f\u5145\u7535\uff0c\u7b49\u9501\u6b62\u91ca\u653e\u540e\u518d\u62d4 |")
    out.append("| \u542f\u52a8\u5931\u8d25 | \u7ed3\u675f\u5145\u7535\u540e\u518d\u8bd5\uff1b\u4ecd\u5931\u8d25\u5219\u68c0\u67e5\u8f66\u8f86\u72b6\u6001 |")
    out.append("| \u65e0\u6cd5\u5f00\u59cb\u5145\u7535 | \u91cd\u65b0\u63d2\u67aa\u3001\u68c0\u67e5\u652f\u4ed8\u65b9\u5f0f\u3001\u6362\u6869\u8bd5\u8bd5 |")
    out.append("| \u5145\u7535\u7279\u522b\u6162 | \u786e\u8ba4\u6869\u529f\u7387\u4e0e\u8f66\u8f86\u5145\u7535\u4e0a\u9650 |")
    out.append("| \u4e2d\u9014\u505c\u6b62\u5e76\u62a5\u9519 | \u8bb0\u5f55\u62a5\u9519\u4fe1\u606f\uff0c\u8054\u7cfb\u8fd0\u8425\u65b9\u4e0e\u552e\u540e |")
    out.append("")
    out.append("## \u5b89\u5168\u6ce8\u610f")
    out.append("")
    out.append("- \u96e8\u5929\u4f7f\u7528\u6b63\u89c4\u8fd0\u8425\u7684\u5145\u7535\u8bbe\u65bd\uff0c\u907f\u514d\u5728\u79ef\u6c34\u4e0e\u7834\u635f\u6869\u4f53\u9644\u8fd1\u5145\u7535")
    out.append("- \u9ad8\u6e29\u65f6\u907f\u514d\u957f\u65f6\u95f4\u66b4\u6652\u540e\u7acb\u5373\u5927\u529f\u7387\u5145\u7535")
    out.append("- \u957f\u65f6\u95f4\u505c\u653e\u907f\u514d\u957f\u671f\u5904\u4e8e\u6781\u4f4e\u7535\u91cf\u6216\u6ee1\u7535\u72b6\u6001")
    out.append("- \u51fa\u73b0\u5f02\u5473\u3001\u5192\u70df\u3001\u5f02\u5e38\u53d1\u70ed\u7acb\u5373\u505c\u6b62\u5e76\u8fdc\u79bb\uff0c\u540c\u65f6\u8054\u7cfb\u76f8\u5173\u65b9")
    out.append("")
    out.append("## \u8fb9\u754c")
    out.append("")
    out.append("- \u8d39\u7528\u3001\u7535\u4ef7\u4e0e\u8ba1\u8d39\u65b9\u5f0f\u4ee5\u8fd0\u8425\u65b9\u73b0\u884c\u89c4\u5219\u4e0e\u516c\u793a\u4e3a\u51c6")
    out.append("- \u5b89\u5168\u8981\u6c42\u4ee5\u73b0\u884c\u89c4\u5b9a\u4e0e\u8fd0\u8425\u65b9\u8bf4\u660e\u4e3a\u51c6")
    out.append("- \u672c\u811a\u672c\u53ea\u505a\u7b97\u672f\u4f30\u7b97\uff0c\u4e0d\u4ee3\u8868\u5b9e\u9645\u6d4b\u91cf\u503c")
    return "\n".join(out) + "\n"


def selftest():
    cases = []
    cases.append(("need_basic", abs(charge_plan(60, 20, 80, 50, "ac", 0.0)[0] - 36.0) < 1e-6))
    cases.append(("need_zero", charge_plan(60, 80, 80, 50, "ac", 0.0)[0] == 0.0))
    cases.append(("need_reverse", charge_plan(60, 90, 20, 50, "ac", 0.0)[0] == 0.0))
    cases.append(("need_full", abs(charge_plan(75, 0, 100, 60, "dc", 0.0)[0] - 75.0) < 1e-6))
    cases.append(("ideal", abs(charge_plan(60, 20, 80, 50, "ac", 0.0)[1] - 0.72) < 1e-6))
    cases.append(("tail_positive", charge_plan(60, 20, 80, 50, "ac", 0.0)[3] > 0))
    cases.append(("dc_tail_less", charge_plan(60, 20, 80, 50, "dc", 0.0)[3]
                   < charge_plan(60, 20, 80, 50, "ac", 0.0)[3]))
    cases.append(("clamp_high", clamp_pct(150) == 100.0))
    cases.append(("clamp_low", clamp_pct(-5) == 0.0))
    cases.append(("range_loss", abs(plan_range(100, 0.75) - 75.0) < 1e-9))
    cases.append(("range_zero", plan_range(0, 0.75) == 0.0))
    cases.append(("float_str", to_float("60", 0.0) == 60.0))
    cases.append(("float_bad", to_float("abc", 1.0) == 1.0))
    rep = build_report({"pack": 75, "current": 25, "target": 80,
                        "power": 60, "type": "ac", "loss": 0.75,
                        "display_km": 300})
    cases.append(("rep_need", "\u9700\u8981\u8865\u5145\u7684\u7535\u91cf" in rep))
    cases.append(("rep_minutes", "\u5206\u949f" in rep))
    cases.append(("rep_range", "\u6309\u6298\u635f\u7cfb\u6570" in rep))
    cases.append(("rep_fault", "\u4e0d\u8981\u786c\u62c9" in rep))
    cases.append(("rep_safety", "\u5f02\u5473" in rep))
    rep2 = build_report({"type": "bad", "pack": 60})
    cases.append(("rep_type_fallback", "\u4ea4\u6d41\u6162\u5145" in rep2))
    bom = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bom_probe.json")
    with open(bom, "w", encoding="utf-8-sig") as f:
        f.write('{"pack": 60}')
    try:
        cases.append(("bom_ok", to_float(load_json(bom).get("pack")) == 60.0))
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
    ap = argparse.ArgumentParser(description="ev charging estimate")
    ap.add_argument("--pack", default=None)
    ap.add_argument("--current", default=None)
    ap.add_argument("--target", default=None)
    ap.add_argument("--power", default=None)
    ap.add_argument("--type", default=None)
    ap.add_argument("--loss", default=None)
    ap.add_argument("--display-km", dest="display_km", default=None)
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
    for key, val in (("pack", a.pack), ("current", a.current), ("target", a.target),
                     ("power", a.power), ("type", a.type), ("loss", a.loss),
                     ("display_km", a.display_km)):
        if val is not None:
            data[key] = val
    if not data:
        data = {"pack": 60, "current": 20, "target": 80, "power": 50, "type": "ac"}
    report = build_report(data)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "ev_charge_result.md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
