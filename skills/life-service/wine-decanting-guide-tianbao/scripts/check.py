# -*- coding: utf-8 -*-
"""\u7ea2\u9152\u9192\u9152\u65b9\u6848\u6821\u9a8c\u811a\u672c\u3002

\u7528\u6cd5:
  python check.py --file \u9192\u9152\u65b9\u6848.json
  python check.py --selftest

JSON \u5b57\u6bb5:
  wine_age_years  \u9152\u9f84\u5e74\u6570 (\u6570\u5b57)
  tannin_level    \u5355\u5b81: heavy/medium/light
  decant_method   \u65b9\u5f0f: decanter(\u9192\u9152\u5668)/bottle(\u74f6\u9192)/none
  decant_minutes  \u9192\u9152\u5206\u949f\u6570 (\u6570\u5b57)
  already_oxidized \u662f\u5426\u5df2\u6c27\u5316(\u6709\u918b\u5473) (true/false)
"""
import argparse
import json
import os
import sys

DECANTER_MAX_YOUNG = 120
DECANTER_MAX_OLD = 60
BOTTLE_MAX = 180
VALID_TANNIN = ["heavy", "medium", "light"]
VALID_METHOD = ["decanter", "bottle", "none"]


def evaluate(data):
    reasons = []
    ok = True

    oxidized = data.get("already_oxidized")
    if oxidized is True:
        ok = False
        reasons.append("\u9152\u5df2\u51fa\u73b0\u6c27\u5316/\u918b\u5473, \u4e0d\u518d\u9192\u9152, \u7ee7\u7eed\u9192\u4f1a\u96ea\u4e0a\u52a0\u971c")
        return ok, reasons

    tmethod = data.get("decant_method")
    if tmethod is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u9192\u9152\u65b9\u5f0f(decant_method)")
    elif tmethod not in VALID_METHOD:
        ok = False
        reasons.append("decant_method \u53d6\u503c\u975e\u6cd5(\u5e94\u4e3a decanter/bottle/none)")

    tannin = data.get("tannin_level")
    if tannin is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u5355\u5b81\u6c34\u5e73(tannin_level)")
    elif tannin not in VALID_TANNIN:
        ok = False
        reasons.append("tannin_level \u53d6\u503c\u975e\u6cd5(\u5e94\u4e3a heavy/medium/light)")

    age = data.get("wine_age_years")
    minutes = data.get("decant_minutes")

    if age is not None and minutes is not None:
        try:
            a = float(age)
            m = float(minutes)
        except (TypeError, ValueError):
            ok = False
            reasons.append("\u9152\u9f84\u6216\u65f6\u957f\u4e0d\u662f\u6570\u5b57")
        else:
            if tmethod == "decanter":
                cap = DECANTER_MAX_OLD if a > 15 else DECANTER_MAX_YOUNG
                if m > cap:
                    ok = False
                    reasons.append("\u9192\u9152\u5668\u9192 %.0f \u5206\u949f\u8d85\u8fc7%s\u9152\u4e0a\u9650 %d \u5206\u949f, \u6613\u6c27\u5316\u8fc7\u5934\u51fa\u918b\u5473" % (
                        m, "\u8001" if a > 15 else "\u5e74\u8f7b", cap))
            elif tmethod == "bottle":
                if m > BOTTLE_MAX:
                    ok = False
                    reasons.append("\u74f6\u9192 %.0f \u5206\u949f\u8d85\u8fc7\u4e0a\u9650 %d \u5206\u949f" % (m, BOTTLE_MAX))

    # \u8001\u9152\u7528\u9192\u9152\u5668\u4e14\u8d85 60 \u5206\u949f\u5df2\u5728\u4e0a\u9762\u8986\u76d6; \u8fd9\u91cc\u8865: \u6e05\u6de1\u9152\u4e0d\u8be5\u731b\u9192
    if tannin == "light" and tmethod == "decanter":
        ok = False
        reasons.append("\u6e05\u6de1\u578b\u9152\u7528\u9192\u9152\u5668\u731b\u9192, \u9999\u6c14\u66f4\u6de1\u5be1, \u5efa\u8bae\u4e0d\u9192\u6216\u77ed\u65f6\u74f6\u9192")

    if ok:
        reasons.append("\u9192\u9152\u65b9\u6848\u901a\u8fc7: \u65b9\u5f0f/\u65f6\u957f/\u9152\u9f84/\u5355\u5b81\u5747\u5339\u914d")
    return ok, reasons


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def selftest():
    passed = 0

    # 1. \u6b63\u4f8b: \u5e74\u8f7b\u91cd\u5355\u5b81, \u9192\u9152\u5668 90 \u5206\u949f -> \u901a\u8fc7
    ok, rs = evaluate({
        "wine_age_years": 3, "tannin_level": "heavy",
        "decant_method": "decanter", "decant_minutes": 90, "already_oxidized": False,
    })
    assert ok is True, "\u6b63\u4f8b\u5e94\u901a\u8fc7: %s" % rs
    passed += 1

    # 2. \u53cd\u4f8b: \u5df2\u6c27\u5316\u8fd8\u9192 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "wine_age_years": 3, "tannin_level": "heavy",
        "decant_method": "decanter", "decant_minutes": 90, "already_oxidized": True,
    })
    assert ok is False, "\u5df2\u6c27\u5316\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u4e0d\u518d\u9192" in r for r in rs), "\u6c27\u5316\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 3. \u53cd\u4f8b: \u8001\u9152\u9192\u9152\u5668 120 \u5206\u949f\u8d85\u4e0a\u9650 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "wine_age_years": 20, "tannin_level": "medium",
        "decant_method": "decanter", "decant_minutes": 120, "already_oxidized": False,
    })
    assert ok is False, "\u8001\u9152\u8d85\u65f6\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u6c27\u5316" in r for r in rs), "\u8001\u9152\u8d85\u65f6\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 4. \u53cd\u4f8b: \u6e05\u6de1\u9152\u7528\u9192\u9152\u5668 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "wine_age_years": 4, "tannin_level": "light",
        "decant_method": "decanter", "decant_minutes": 30, "already_oxidized": False,
    })
    assert ok is False, "\u6e05\u6de1\u9152\u731b\u9192\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u6de1\u5be1" in r for r in rs), "\u6e05\u6de1\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 5. \u53cd\u4f8b: \u7f3a\u65b9\u5f0f -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "wine_age_years": 3, "tannin_level": "heavy",
        "decant_minutes": 90, "already_oxidized": False,
    })
    assert ok is False, "\u7f3a\u65b9\u5f0f\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 6. \u53cd\u4f8b: \u7f3a\u5355\u5b81 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "wine_age_years": 3, "decant_method": "decanter",
        "decant_minutes": 90, "already_oxidized": False,
    })
    assert ok is False, "\u7f3a\u5355\u5b81\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 7. \u53cd\u4f8b: \u74f6\u9192 300 \u5206\u949f\u8d85\u4e0a\u9650 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "wine_age_years": 3, "tannin_level": "heavy",
        "decant_method": "bottle", "decant_minutes": 300, "already_oxidized": False,
    })
    assert ok is False, "\u74f6\u9192\u8d85\u65f6\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 8. \u53cd\u4f8b: \u65b9\u5f0f\u975e\u6cd5 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "wine_age_years": 3, "tannin_level": "heavy",
        "decant_method": "cup", "decant_minutes": 90, "already_oxidized": False,
    })
    assert ok is False, "\u975e\u6cd5\u65b9\u5f0f\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 9. BOM \u5904\u7406
    here = os.path.dirname(os.path.abspath(__file__))
    bom_path = os.path.join(here, "_bom_sample.json")
    payload = json.dumps({
        "wine_age_years": 3, "tannin_level": "heavy",
        "decant_method": "decanter", "decant_minutes": 90, "already_oxidized": False,
    }, ensure_ascii=False)
    with open(bom_path, "wb") as f:
        f.write(b"\xef\xbb\xbf" + payload.encode("utf-8"))
    d = load_json(bom_path)
    assert d.get("decant_method") == "decanter", "BOM \u8f93\u5165 key \u4e0d\u5e94\u5e26 \\ufeff"
    assert "wine_age_years" in d, "BOM \u8f93\u5165 key \u5fc5\u987b\u5e72\u51c0"
    os.remove(bom_path)
    passed += 1

    # 10. \u8fb9\u754c: \u8001\u9152\u74f6\u9192 60 \u5206\u949f -> \u901a\u8fc7
    ok, rs = evaluate({
        "wine_age_years": 20, "tannin_level": "medium",
        "decant_method": "bottle", "decant_minutes": 60, "already_oxidized": False,
    })
    assert ok is True, "\u8001\u9152\u74f6\u9192\u5408\u89c4\u5e94\u901a\u8fc7: %s" % rs
    passed += 1

    line = "SELFTEST OK (%d assertions)" % passed
    return line, passed


def main():
    ap = argparse.ArgumentParser(description="\u7ea2\u9152\u9192\u9152\u65b9\u6848\u6821\u9a8c")
    ap.add_argument("--file", help="\u9192\u9152\u65b9\u6848 JSON")
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
