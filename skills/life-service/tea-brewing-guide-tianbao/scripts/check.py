# -*- coding: utf-8 -*-
"""\u8336\u827a\u51b2\u6ce1\u53c2\u6570\u6821\u9a8c\u811a\u672c\u3002

\u7528\u6cd5:
  python check.py --file \u51b2\u6ce1\u53c2\u6570.json
  python check.py --selftest

JSON \u5b57\u6bb5:
  tea_type      \u8336\u7c7b: green/yellow/white_new/white_old/oolong/black_tea/dark
  water_temp    \u6c34\u6e29\u6444\u6c0f\u5ea6 (\u6570\u5b57)
  tea_g         \u8336\u53f6\u514b\u6570 (\u6570\u5b57)
  water_ml      \u6c34\u91cf\u6beb\u5347 (\u6570\u5b57)
  steep_seconds \u9996\u6ce1\u51fa\u6c64\u79d2\u6570 (\u6570\u5b57)
"""
import argparse
import json
import os
import sys

# \u5404\u8336\u7c7b\u6c34\u6e29\u533a\u95f4
TEMP_RANGE = {
    "green": (80, 85), "yellow": (80, 85), "white_new": (85, 90),
    "white_old": (95, 100), "oolong": (95, 100), "black_tea": (90, 95),
    "dark": (95, 100),
}
VALID_TYPES = list(TEMP_RANGE.keys())
GREEN_OVER_TEMP = 90
OOLONG_UNDER_TEMP = 85


def evaluate(data):
    reasons = []
    ok = True

    ttype = data.get("tea_type")
    if ttype is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u8336\u7c7b(tea_type), \u65e0\u6cd5\u5339\u914d\u6c34\u6e29\u533a\u95f4")
    elif ttype not in VALID_TYPES:
        ok = False
        reasons.append("tea_type \u53d6\u503c\u975e\u6cd5(\u5e94\u4e3a green/yellow/white_new/white_old/oolong/black_tea/dark)")

    temp = data.get("water_temp")
    if temp is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u6c34\u6e29(water_temp)")
    else:
        try:
            t = float(temp)
        except (TypeError, ValueError):
            ok = False
            reasons.append("water_temp \u4e0d\u662f\u6570\u5b57")
        else:
            if ttype in TEMP_RANGE:
                lo, hi = TEMP_RANGE[ttype]
                if t < lo or t > hi:
                    ok = False
                    reasons.append("%s \u6c34\u6e29 %.0f\u2103 \u4e0d\u5728\u533a\u95f4 %d\u2013%d\u2103, \u6613\u70eb\u719f\u6216\u6ce1\u4e0d\u5f00" % (
                        ttype, t, lo, hi))

    tea = data.get("tea_g")
    water = data.get("water_ml")
    if tea is None or water is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u8336\u53f6\u514b\u6570\u6216\u6c34\u91cf, \u65e0\u6cd5\u7b97\u8336\u6c34\u6bd4")
    else:
        try:
            ratio = float(water) / float(tea)
        except (TypeError, ValueError, ZeroDivisionError):
            ok = False
            reasons.append("\u8336\u6c34\u6bd4\u53c2\u6570\u975e\u6cd5")
        else:
            if ratio < 10:
                ok = False
                reasons.append("\u8336\u6c34\u6bd4 1:%.0f \u8fc7\u6d53(\u8336\u591a\u6c34\u5c11), \u6613\u82e6\u6da9" % ratio)
            elif ratio > 60:
                ok = False
                reasons.append("\u8336\u6c34\u6bd4 1:%.0f \u8fc7\u6de1(\u8336\u5c11\u6c34\u591a), \u6ecb\u5473\u5be1\u6de1" % ratio)

    steep = data.get("steep_seconds")
    if steep is not None and ttype == "green":
        try:
            s = float(steep)
        except (TypeError, ValueError):
            ok = False
            reasons.append("steep_seconds \u4e0d\u662f\u6570\u5b57")
        else:
            if s > 180:
                ok = False
                reasons.append("\u7eff\u8336\u9996\u6ce1\u51fa\u6c64 %.0f \u79d2\u8d85\u8fc7 3 \u5206\u949f, \u95f7\u574f\u6c64\u6697\u82e6" % s)

    if ok:
        reasons.append("\u51b2\u6ce1\u53c2\u6570\u901a\u8fc7: \u6c34\u6e29/\u8336\u6c34\u6bd4/\u51fa\u6c64\u5747\u5408\u89c4")
    return ok, reasons


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def selftest():
    passed = 0

    # 1. \u6b63\u4f8b: \u7eff\u8336 85\u2103, 3g/150ml, 40s -> \u901a\u8fc7
    ok, rs = evaluate({
        "tea_type": "green", "water_temp": 85, "tea_g": 3, "water_ml": 150, "steep_seconds": 40,
    })
    assert ok is True, "\u6b63\u4f8b\u5e94\u901a\u8fc7: %s" % rs
    passed += 1

    # 2. \u53cd\u4f8b: \u7eff\u8336 100\u2103 \u70eb\u719f -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "tea_type": "green", "water_temp": 100, "tea_g": 3, "water_ml": 150, "steep_seconds": 40,
    })
    assert ok is False, "\u7eff\u8336\u6cb8\u6c34\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u70eb\u719f" in r for r in rs), "\u70eb\u719f\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 3. \u53cd\u4f8b: \u4e4c\u9f99 80\u2103 \u6ce1\u4e0d\u5f00 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "tea_type": "oolong", "water_temp": 80, "tea_g": 5, "water_ml": 100, "steep_seconds": 15,
    })
    assert ok is False, "\u4e4c\u9f99\u4f4e\u6e29\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u6ce1\u4e0d\u5f00" in r for r in rs), "\u6ce1\u4e0d\u5f00\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 4. \u53cd\u4f8b: \u8336\u6c34\u6bd4\u8fc7\u6d53 1:5 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "tea_type": "green", "water_temp": 85, "tea_g": 10, "water_ml": 50, "steep_seconds": 40,
    })
    assert ok is False, "\u8fc7\u6d53\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u8fc7\u6d53" in r for r in rs), "\u8fc7\u6d53\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 5. \u53cd\u4f8b: \u7f3a tea_type -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "water_temp": 85, "tea_g": 3, "water_ml": 150, "steep_seconds": 40,
    })
    assert ok is False, "\u7f3a\u8336\u7c7b\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 6. \u53cd\u4f8b: \u7eff\u8336\u95f7 300 \u79d2 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "tea_type": "green", "water_temp": 85, "tea_g": 3, "water_ml": 150, "steep_seconds": 300,
    })
    assert ok is False, "\u95f7\u574f\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 7. \u53cd\u4f8b: tea_type \u975e\u6cd5 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "tea_type": "herbal", "water_temp": 85, "tea_g": 3, "water_ml": 150, "steep_seconds": 40,
    })
    assert ok is False, "\u975e\u6cd5\u8336\u7c7b\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 8. \u53cd\u4f8b: \u8336\u6c34\u6bd4\u8fc7\u6de1 1:80 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "tea_type": "green", "water_temp": 85, "tea_g": 2, "water_ml": 160, "steep_seconds": 40,
    })
    assert ok is False, "\u8fc7\u6de1\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 9. BOM \u5904\u7406
    here = os.path.dirname(os.path.abspath(__file__))
    bom_path = os.path.join(here, "_bom_sample.json")
    payload = json.dumps({
        "tea_type": "green", "water_temp": 85, "tea_g": 3, "water_ml": 150, "steep_seconds": 40,
    }, ensure_ascii=False)
    with open(bom_path, "wb") as f:
        f.write(b"\xef\xbb\xbf" + payload.encode("utf-8"))
    d = load_json(bom_path)
    assert d.get("tea_type") == "green", "BOM \u8f93\u5165 key \u4e0d\u5e94\u5e26 \\ufeff"
    assert "water_temp" in d, "BOM \u8f93\u5165 key \u5fc5\u987b\u5e72\u51c0"
    os.remove(bom_path)
    passed += 1

    # 10. \u8fb9\u754c: \u4e4c\u9f99 100\u2103, 5g/100ml, 15s -> \u901a\u8fc7
    ok, rs = evaluate({
        "tea_type": "oolong", "water_temp": 100, "tea_g": 5, "water_ml": 100, "steep_seconds": 15,
    })
    assert ok is True, "\u4e4c\u9f99\u5408\u89c4\u5e94\u901a\u8fc7: %s" % rs
    passed += 1

    line = "SELFTEST OK (%d assertions)" % passed
    return line, passed


def main():
    ap = argparse.ArgumentParser(description="\u8336\u827a\u51b2\u6ce1\u53c2\u6570\u6821\u9a8c")
    ap.add_argument("--file", help="\u51b2\u6ce1\u53c2\u6570 JSON")
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
