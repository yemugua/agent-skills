# -*- coding: utf-8 -*-
"""\u5899\u9762\u88c2\u7f1d\u8bb0\u5f55\u6821\u9a8c\u811a\u672c\u3002

\u7528\u6cd5:
  python check.py --file \u88c2\u7f1d\u8bb0\u5f55.json
  python check.py --selftest

JSON \u5b57\u6bb5:
  location          \u4f4d\u7f6e: load_bearing(\u627f\u91cd)/non_bearing/beam/column/top_floor
  width_mm          \u88c2\u7f1d\u5bbd\u5ea6\u6beb\u7c73 (\u6570\u5b57)
  through           \u662f\u5426\u8d2f\u901a (true/false)
  extends_structure \u662f\u5426\u968f\u7ed3\u6784\u5ef6\u4f38 (true/false)
  growing           \u662f\u5426\u5728\u53d1\u5c55 (true/false)
"""
import argparse
import json
import os
import sys

WIDTH_SERIOUS = 0.3
WIDTH_GENERAL = 0.2
RED_LOCATIONS = {"load_bearing", "beam", "column"}


def evaluate(data):
    reasons = []
    ok = True

    loc = data.get("location")
    if loc is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u88c2\u7f1d\u4f4d\u7f6e(location), \u65e0\u6cd5\u5224\u65ad\u662f\u5426\u4e3a\u7ed3\u6784\u6027")
    elif loc not in RED_LOCATIONS and loc != "non_bearing" and loc != "top_floor":
        ok = False
        reasons.append("location \u53d6\u503c\u975e\u6cd5(\u5e94\u4e3a load_bearing/non_bearing/beam/column/top_floor)")

    width = data.get("width_mm")
    if width is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u88c2\u7f1d\u5bbd\u5ea6(width_mm), \u65e0\u6cd5\u5206\u7ea7")
    else:
        try:
            w = float(width)
        except (TypeError, ValueError):
            ok = False
            reasons.append("width_mm \u4e0d\u662f\u6570\u5b57")
        else:
            if w > WIDTH_SERIOUS:
                ok = False
                reasons.append("\u88c2\u7f1d\u5bbd\u5ea6 %.2fmm \u8d85\u8fc7 0.3mm, \u8d85\u51fa\u8868\u5c42\u4fee\u8865\u8303\u56f4, \u987b\u8f6c\u7ed3\u6784\u5de5\u7a0b\u5e08" % w)

    # \u7ea2\u7ebf: \u627f\u91cd/\u6881\u67f1\u4f4d\u7f6e, \u6216\u8d2f\u901a, \u6216\u968f\u7ed3\u6784\u5ef6\u4f38, \u6216\u6301\u7eed\u53d1\u5c55
    red = False
    if loc in RED_LOCATIONS:
        red = True
        reasons.append("\u88c2\u7f1d\u4f4d\u4e8e\u627f\u91cd\u5899/\u6881/\u67f1, \u5c5e\u7ea2\u7ebf, \u987b\u8f6c\u4ea4\u6301\u8bc1\u7ed3\u6784\u5de5\u7a0b\u5e08\u786e\u8ba4")
    through = data.get("through")
    if through is True:
        red = True
        reasons.append("\u88c2\u7f1d\u8d2f\u901a, \u5c5e\u7ea2\u7ebf, \u987b\u8f6c\u4ea4\u7ed3\u6784\u5de5\u7a0b\u5e08\u786e\u8ba4")
    ext = data.get("extends_structure")
    if ext is True:
        red = True
        reasons.append("\u88c2\u7f1d\u968f\u7ed3\u6784\u5ef6\u4f38, \u5c5e\u7ea2\u7ebf, \u987b\u8f6c\u4ea4\u7ed3\u6784\u5de5\u7a0b\u5e08\u786e\u8ba4")
    growing = data.get("growing")
    if growing is True:
        red = True
        reasons.append("\u88c2\u7f1d\u6301\u7eed\u53d1\u5c55(\u53d8\u957f\u53d8\u5bbd), \u5c5e\u7ea2\u7ebf, \u987b\u7acb\u5373\u8f6c\u4e13\u4e1a\u786e\u8ba4")

    if red:
        ok = False

    if ok:
        reasons.append("\u88c2\u7f1d\u8bb0\u5f55\u901a\u8fc7: \u975e\u7ed3\u6784\u6027\u3001\u5bbd\u5ea6\u5408\u89c4\u3001\u65e0\u7ea2\u7ebf\u9879, \u53ef\u6309\u5de5\u827a\u4fee\u8865")
    return ok, reasons


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def selftest():
    passed = 0

    # 1. \u6b63\u4f8b: \u975e\u627f\u91cd, 0.1mm, \u4e0d\u8d2f\u901a\u4e0d\u5ef6\u4f38\u4e0d\u53d1\u5c55 -> \u901a\u8fc7
    ok, rs = evaluate({
        "location": "non_bearing", "width_mm": 0.1,
        "through": False, "extends_structure": False, "growing": False,
    })
    assert ok is True, "\u6b63\u4f8b\u5e94\u901a\u8fc7: %s" % rs
    passed += 1

    # 2. \u53cd\u4f8b: \u627f\u91cd\u5899\u88c2\u7f1d -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "location": "load_bearing", "width_mm": 0.1,
        "through": False, "extends_structure": False, "growing": False,
    })
    assert ok is False, "\u627f\u91cd\u5899\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u7ed3\u6784\u5de5\u7a0b\u5e08" in r for r in rs), "\u7ea2\u7ebf\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 3. \u53cd\u4f8b: \u5bbd\u5ea6 0.5mm -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "location": "non_bearing", "width_mm": 0.5,
        "through": False, "extends_structure": False, "growing": False,
    })
    assert ok is False, "\u8d85\u5bbd\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("0.3mm" in r for r in rs), "\u8d85\u5bbd\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 4. \u53cd\u4f8b: \u8d2f\u901a -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "location": "non_bearing", "width_mm": 0.1,
        "through": True, "extends_structure": False, "growing": False,
    })
    assert ok is False, "\u8d2f\u901a\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 5. \u53cd\u4f8b: \u968f\u7ed3\u6784\u5ef6\u4f38 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "location": "non_bearing", "width_mm": 0.1,
        "through": False, "extends_structure": True, "growing": False,
    })
    assert ok is False, "\u5ef6\u4f38\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 6. \u53cd\u4f8b: \u6301\u7eed\u53d1\u5c55 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "location": "non_bearing", "width_mm": 0.1,
        "through": False, "extends_structure": False, "growing": True,
    })
    assert ok is False, "\u53d1\u5c55\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 7. \u53cd\u4f8b: \u7f3a\u4f4d\u7f6e -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "width_mm": 0.1, "through": False, "extends_structure": False, "growing": False,
    })
    assert ok is False, "\u7f3a\u4f4d\u7f6e\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 8. \u53cd\u4f8b: location \u975e\u6cd5 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "location": "floor", "width_mm": 0.1,
        "through": False, "extends_structure": False, "growing": False,
    })
    assert ok is False, "\u975e\u6cd5\u4f4d\u7f6e\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 9. BOM \u5904\u7406
    here = os.path.dirname(os.path.abspath(__file__))
    bom_path = os.path.join(here, "_bom_sample.json")
    payload = json.dumps({
        "location": "non_bearing", "width_mm": 0.1,
        "through": False, "extends_structure": False, "growing": False,
    }, ensure_ascii=False)
    with open(bom_path, "wb") as f:
        f.write(b"\xef\xbb\xbf" + payload.encode("utf-8"))
    d = load_json(bom_path)
    assert d.get("location") == "non_bearing", "BOM \u8f93\u5165 key \u4e0d\u5e94\u5e26 \\ufeff"
    assert "width_mm" in d, "BOM \u8f93\u5165 key \u5fc5\u987b\u5e72\u51c0"
    os.remove(bom_path)
    passed += 1

    # 10. \u8fb9\u754c: \u9876\u5c42 0.25mm \u975e\u7ea2\u7ebf -> \u901a\u8fc7(\u4e00\u822c\u7ea7\u4f46\u975e\u7ea2\u7ebf)
    ok, rs = evaluate({
        "location": "top_floor", "width_mm": 0.25,
        "through": False, "extends_structure": False, "growing": False,
    })
    assert ok is True, "\u9876\u5c42\u4e00\u822c\u7f1d\u5e94\u901a\u8fc7: %s" % rs
    passed += 1

    line = "SELFTEST OK (%d assertions)" % passed
    return line, passed


def main():
    ap = argparse.ArgumentParser(description="\u5899\u9762\u88c2\u7f1d\u8bb0\u5f55\u6821\u9a8c")
    ap.add_argument("--file", help="\u88c2\u7f1d\u8bb0\u5f55 JSON")
    ap.add_argument("--selftest", action="store_true", help="\u5185\u7f6e\u81ea\u68c0")
    args = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))

    if args.selftest:
        line, total = selftest()
        with open(os.path.join(here, "_selftest_result.txt"), "w", encoding="utf-8") as f:
            f.write(line + "\n")
        print(line)
        return 0 if line.startswith("SELFTEST OK") else 1

    if args.file:
        try:
            data = load_json(args.file)
        except Exception as e:  # noqa: BLE001
            msg = "\u8bfb\u53d6\u5931\u8d25: %s" % e
            with open(os.path.join(here, "_last_result.txt"), "w", encoding="utf-8") as f:
                f.write(msg + "\n")
            print(msg)
            return 1
        ok, reasons = evaluate(data)
        out = ("PASS " if ok else "FAIL ") + "\uff1b".join(reasons)
        with open(os.path.join(here, "_last_result.txt"), "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print(out)
        return 0 if ok else 1

    print("\u9700\u8981 --file \u6216 --selftest")
    return 2


if __name__ == "__main__":
    sys.exit(main())
