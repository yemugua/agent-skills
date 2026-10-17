# -*- coding: utf-8 -*-
"""\u814c\u83dc\u8bb0\u5f55\u6821\u9a8c\u811a\u672c\u3002

\u7528\u6cd5:
  python check.py --file \u814c\u83dc\u8bb0\u5f55.json
  python check.py --selftest

JSON \u5b57\u6bb5:
  salt_percent        \u76d0\u5360\u83dc\u91cd\u767e\u5206\u6bd4 (\u6570\u5b57)
  fully_submerged     \u76d0\u6c34\u662f\u5426\u5b8c\u5168\u6ca1\u8fc7\u83dc (true/false)
  oil_free_container  \u5bb9\u5668\u662f\u5426\u65e0\u6cb9\u65e0\u751f\u6c34 (true/false)
  temp_c              \u53d1\u9175\u6e29\u5ea6\u6444\u6c0f\u5ea6 (\u6570\u5b57)
  ferment_days        \u5df2\u814c\u5929\u6570 (\u6570\u5b57)
  signs               \u5f02\u5e38\u4fe1\u53f7\u5217\u8868, \u5982 ["sticky","smelly","mold"]
"""
import argparse
import json
import os
import sys

SALT_MIN = 2.0
SALT_MAX_PICKLE = 5.0
SALT_MAX_SALTED = 15.0
TEMP_LOW = 10.0
TEMP_HIGH = 25.0
SAFE_DAYS = 20
PEAK_LOW = 3
PEAK_HIGH = 8

# \u81f4\u547d\u4fe1\u53f7: \u51fa\u73b0\u4efb\u4e00\u9879\u6574\u575b\u5e9f\u5f03
FATAL_SIGNS = ["sticky", "smelly", "rot"]


def evaluate(data):
    reasons = []
    ok = True

    signs = data.get("signs") or []
    for s in signs:
        if s in FATAL_SIGNS:
            ok = False
            reasons.append("\u68c0\u6d4b\u5230\u81f4\u547d\u4fe1\u53f7(%s), \u814c\u83dc\u5df2\u8150\u8d25, \u5fc5\u987b\u6574\u575b\u5e9f\u5f03" % s)
    if not ok:
        return ok, reasons

    salt = data.get("salt_percent")
    if salt is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u76d0\u5360\u83dc\u91cd\u767e\u5206\u6bd4(salt_percent), \u65e0\u6cd5\u5224\u65ad\u9632\u8150\u662f\u5426\u8db3\u591f")
    else:
        try:
            sp = float(salt)
        except (TypeError, ValueError):
            ok = False
            reasons.append("salt_percent \u4e0d\u662f\u6570\u5b57")
        else:
            if sp < SALT_MIN:
                ok = False
                reasons.append("\u76d0\u5360\u83dc\u91cd %.1f%% \u4f4e\u4e8e 2%% \u4e0b\u9650, \u6742\u83cc\u6291\u5236\u4e0d\u8db3\u6613\u81ed\u575b\u8f6f\u70c2" % sp)

    submerged = data.get("fully_submerged")
    if submerged is not True:
        ok = False
        reasons.append("\u76d0\u6c34\u672a\u5b8c\u5168\u6ca1\u8fc7\u83dc, \u9732\u7a7a\u90e8\u5206\u63a5\u89e6\u7a7a\u6c14\u6613\u53d1\u9709\u957f\u767d\u6bdb")

    oil_free = data.get("oil_free_container")
    if oil_free is not True:
        ok = False
        reasons.append("\u5bb9\u5668\u672a\u505a\u5230\u65e0\u6cb9\u65e0\u751f\u6c34, \u6613\u6574\u575b\u6c61\u67d3")

    temp = data.get("temp_c")
    if temp is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u53d1\u9175\u6e29\u5ea6(temp_c)")
    else:
        try:
            t = float(temp)
        except (TypeError, ValueError):
            ok = False
            reasons.append("temp_c \u4e0d\u662f\u6570\u5b57")
        else:
            if t > TEMP_HIGH:
                ok = False
                reasons.append("\u53d1\u9175\u6e29\u5ea6 %.1f\u2103 \u8d85\u8fc7 25\u2103 \u4e0a\u9650, \u8fc7\u5feb\u4ea7\u9178\u83dc\u6613\u8f6f" % t)
            elif t < TEMP_LOW:
                ok = False
                reasons.append("\u53d1\u9175\u6e29\u5ea6 %.1f\u2103 \u4f4e\u4e8e 10\u2103, \u8fc7\u6162\u6613\u751f\u82b1" % t)

    days = data.get("ferment_days")
    if days is not None:
        try:
            d = float(days)
        except (TypeError, ValueError):
            ok = False
            reasons.append("ferment_days \u4e0d\u662f\u6570\u5b57")
        else:
            if PEAK_LOW <= d <= PEAK_HIGH:
                ok = False
                reasons.append("\u5df2\u814c %.0f \u5929\u6b63\u5904\u4e8e\u4e9a\u785d\u9178\u76d0\u5cf0\u503c\u671f(3\u20138\u5929), \u5efa\u8bae\u5ef6\u81f3 20 \u5929\u540e\u98df\u7528" % d)
            elif d < SAFE_DAYS and d > PEAK_HIGH:
                reasons.append("\u63d0\u793a: \u672a\u5230 20 \u5929\u5b89\u5168\u7ebf, \u4ecd\u5728\u4e0b\u964d\u671f, \u5efa\u8bae\u518d\u7b49\u7b49")

    if ok:
        reasons.append("\u814c\u83dc\u8bb0\u5f55\u901a\u8fc7: \u76d0\u91cf/\u6ca1\u8fc7/\u5bb9\u5668/\u6e29\u5ea6/\u5929\u6570\u5747\u5408\u89c4")
    return ok, reasons


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def selftest():
    passed = 0

    # 1. \u6b63\u4f8b: \u76d0 3%, \u6ca1\u8fc7, \u65e0\u6cb9, 18\u2103, 25 \u5929 -> \u901a\u8fc7
    ok, rs = evaluate({
        "salt_percent": 3.0, "fully_submerged": True, "oil_free_container": True,
        "temp_c": 18.0, "ferment_days": 25, "signs": [],
    })
    assert ok is True, "\u6b63\u4f8b\u5e94\u901a\u8fc7: %s" % rs
    passed += 1

    # 2. \u53cd\u4f8b: \u81f4\u547d\u4fe1\u53f7 smelly -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "salt_percent": 3.0, "fully_submerged": True, "oil_free_container": True,
        "temp_c": 18.0, "ferment_days": 25, "signs": ["smelly"],
    })
    assert ok is False, "\u53d1\u81ed\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u5e9f\u5f03" in r for r in rs), "\u5e9f\u5f03\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 3. \u53cd\u4f8b: \u76d0 1% \u4e0d\u8db3 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "salt_percent": 1.0, "fully_submerged": True, "oil_free_container": True,
        "temp_c": 18.0, "ferment_days": 25, "signs": [],
    })
    assert ok is False, "\u76d0\u4e0d\u8db3\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("2%" in r for r in rs), "\u76d0\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 4. \u53cd\u4f8b: \u672a\u6ca1\u8fc7 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "salt_percent": 3.0, "fully_submerged": False, "oil_free_container": True,
        "temp_c": 18.0, "ferment_days": 25, "signs": [],
    })
    assert ok is False, "\u672a\u6ca1\u8fc7\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u6ca1\u8fc7" in r for r in rs), "\u6ca1\u8fc7\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 5. \u53cd\u4f8b: \u5cf0\u503c\u671f\u7b2c 5 \u5929 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "salt_percent": 3.0, "fully_submerged": True, "oil_free_container": True,
        "temp_c": 18.0, "ferment_days": 5, "signs": [],
    })
    assert ok is False, "\u5cf0\u503c\u671f\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u5cf0\u503c" in r for r in rs), "\u5cf0\u503c\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 6. \u53cd\u4f8b: \u6e29\u5ea6 30\u2103 \u8d85\u4e0a\u9650 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "salt_percent": 3.0, "fully_submerged": True, "oil_free_container": True,
        "temp_c": 30.0, "ferment_days": 25, "signs": [],
    })
    assert ok is False, "\u8d85\u6e29\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 7. \u53cd\u4f8b: \u5bb9\u5668\u5e26\u6cb9 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "salt_percent": 3.0, "fully_submerged": True, "oil_free_container": False,
        "temp_c": 18.0, "ferment_days": 25, "signs": [],
    })
    assert ok is False, "\u5e26\u6cb9\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 8. \u53cd\u4f8b: \u81f4\u547d\u4fe1\u53f7 sticky -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "salt_percent": 3.0, "fully_submerged": True, "oil_free_container": True,
        "temp_c": 18.0, "ferment_days": 25, "signs": ["sticky"],
    })
    assert ok is False, "\u53d8\u9ecf\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 9. BOM \u5904\u7406
    here = os.path.dirname(os.path.abspath(__file__))
    bom_path = os.path.join(here, "_bom_sample.json")
    payload = json.dumps({
        "salt_percent": 3.0, "fully_submerged": True, "oil_free_container": True,
        "temp_c": 18.0, "ferment_days": 25, "signs": [],
    }, ensure_ascii=False)
    with open(bom_path, "wb") as f:
        f.write(b"\xef\xbb\xbf" + payload.encode("utf-8"))
    d = load_json(bom_path)
    assert d.get("salt_percent") == 3.0, "BOM \u8f93\u5165 key \u4e0d\u5e94\u5e26 \\ufeff"
    assert "fully_submerged" in d, "BOM \u8f93\u5165 key \u5fc5\u987b\u5e72\u51c0"
    os.remove(bom_path)
    passed += 1

    # 10. \u8fb9\u754c: \u53d8\u9ecf\u4fe1\u53f7\u4f18\u5148\u4e8e\u5176\u4ed6 -> \u81f4\u547d\u4fe1\u53f7\u5148\u8fd4\u56de
    ok, rs = evaluate({
        "salt_percent": 1.0, "fully_submerged": False, "oil_free_container": False,
        "temp_c": 30.0, "ferment_days": 5, "signs": ["sticky"],
    })
    assert ok is False, "\u81f4\u547d\u4fe1\u53f7\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u5e9f\u5f03" in r for r in rs), "\u81f4\u547d\u4fe1\u53f7\u5e94\u4f18\u5148: %s" % rs
    passed += 1

    line = "SELFTEST OK (%d assertions)" % passed
    return line, passed


def main():
    ap = argparse.ArgumentParser(description="\u814c\u83dc\u8bb0\u5f55\u6821\u9a8c")
    ap.add_argument("--file", help="\u814c\u83dc\u8bb0\u5f55 JSON")
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
