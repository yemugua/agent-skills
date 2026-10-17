# -*- coding: utf-8 -*-
"""\u6c34\u7535\u9a8c\u6536\u8bb0\u5f55\u6821\u9a8c\u811a\u672c\u3002

\u7528\u6cd5:
  python check.py --file \u6c34\u7535\u9a8c\u6536.json
  python check.py --selftest

JSON \u5b57\u6bb5:
  pressure_mpa      \u6253\u538b\u8bd5\u9a8c\u538b\u529b (\u6570\u5b57)
  pressure_drop      \u7a33\u538b30\u5206\u949f\u538b\u964d MPa (\u6570\u5b57)
  insulation_mohm    \u7edd\u7f18\u7535\u963b M\u03a9 (\u6570\u5b57)
  grounded           \u63a5\u5730\u53ef\u9760 (true/false)
  circuits_ok        \u56de\u8def\u6807\u8bc6\u6b63\u786e (true/false)
  wire_ok            \u7ebf\u5f84\u7b26\u5408\u8981\u6c42 (true/false)
"""
import argparse
import json
import os
import sys

PRESSURE_TARGET = 0.8
DROP_LIMIT = 0.05
INSULATION_MIN = 0.5


def evaluate(data):
    reasons = []
    ok = True

    pressure = data.get("pressure_mpa")
    if pressure is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u6253\u538b\u538b\u529b(pressure_mpa), \u65e0\u6cd5\u786e\u8ba4\u8bd5\u9a8c\u662f\u5426\u5230\u4f4d")
    else:
        try:
            p = float(pressure)
        except (TypeError, ValueError):
            ok = False
            reasons.append("pressure_mpa \u4e0d\u662f\u6570\u5b57")
        else:
            if p < PRESSURE_TARGET:
                ok = False
                reasons.append("\u6253\u538b\u538b\u529b %.2fMPa \u4f4e\u4e8e 0.8MPa \u6807\u51c6, \u8bd5\u9a8c\u4e0d\u5145\u5206" % p)

    drop = data.get("pressure_drop")
    if drop is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u538b\u964d(pressure_drop), \u65e0\u6cd5\u5224\u65ad\u662f\u5426\u6e17\u6f0f")
    else:
        try:
            d = float(drop)
        except (TypeError, ValueError):
            ok = False
            reasons.append("pressure_drop \u4e0d\u662f\u6570\u5b57")
        else:
            if d > DROP_LIMIT:
                ok = False
                reasons.append("\u538b\u964d %.3fMPa \u8d85\u8fc7 0.05MPa \u4e0a\u9650, \u7591\u6e17\u6f0f\u6216\u63a5\u53e3\u4e0d\u5b9e, \u987b\u6574\u6539" % d)

    ins = data.get("insulation_mohm")
    if ins is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u7edd\u7f18\u7535\u963b(insulation_mohm)")
    else:
        try:
            i = float(ins)
        except (TypeError, ValueError):
            ok = False
            reasons.append("insulation_mohm \u4e0d\u662f\u6570\u5b57")
        else:
            if i < INSULATION_MIN:
                ok = False
                reasons.append("\u7edd\u7f18\u7535\u963b %.2fM\u03a9 \u4f4e\u4e8e 0.5M\u03a9 \u5408\u683c\u7ebf, \u89e6\u7535/\u77ed\u8def\u9690\u60a3, \u987b\u8f6c\u4e13\u4e1a" % i)

    grounded = data.get("grounded")
    if grounded is not True:
        ok = False
        reasons.append("\u63a5\u5730\u4e0d\u53ef\u9760(grounded \u975e true), \u6f0f\u4fdd\u53ef\u80fd\u4e0d\u8df3, \u987b\u8f6c\u4e13\u4e1a\u786e\u8ba4")

    circuits = data.get("circuits_ok")
    if circuits is not True:
        ok = False
        reasons.append("\u56de\u8def\u6807\u8bc6\u4e0d\u6b63\u786e\u6216\u672a\u786e\u8ba4(circuits_ok \u975e true), \u7ef4\u4fee\u9690\u60a3")

    wire = data.get("wire_ok")
    if wire is not True:
        ok = False
        reasons.append("\u7ebf\u5f84\u4e0d\u7b26\u5408\u8981\u6c42(wire_ok \u975e true), \u53d1\u70ed\u98ce\u9669")

    if ok:
        reasons.append("\u6c34\u7535\u9a8c\u6536\u901a\u8fc7: \u6253\u538b/\u7edd\u7f18/\u63a5\u5730/\u56de\u8def/\u7ebf\u5f84\u5747\u5408\u89c4")
    return ok, reasons


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def selftest():
    passed = 0

    # 1. \u6b63\u4f8b: \u5168\u5408\u89c4 -> \u901a\u8fc7
    ok, rs = evaluate({
        "pressure_mpa": 0.8, "pressure_drop": 0.02, "insulation_mohm": 1.2,
        "grounded": True, "circuits_ok": True, "wire_ok": True,
    })
    assert ok is True, "\u6b63\u4f8b\u5e94\u901a\u8fc7: %s" % rs
    passed += 1

    # 2. \u53cd\u4f8b: \u538b\u964d 0.1 \u8d85\u4e0a\u9650 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "pressure_mpa": 0.8, "pressure_drop": 0.1, "insulation_mohm": 1.2,
        "grounded": True, "circuits_ok": True, "wire_ok": True,
    })
    assert ok is False, "\u538b\u964d\u8d85\u6807\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u6e17\u6f0f" in r for r in rs), "\u538b\u964d\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 3. \u53cd\u4f8b: \u7edd\u7f18 0.3 \u4e0d\u5408\u683c -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "pressure_mpa": 0.8, "pressure_drop": 0.02, "insulation_mohm": 0.3,
        "grounded": True, "circuits_ok": True, "wire_ok": True,
    })
    assert ok is False, "\u7edd\u7f18\u4e0d\u5408\u683c\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("0.5M\u03a9" in r for r in rs), "\u7edd\u7f18\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 4. \u53cd\u4f8b: \u63a5\u5730\u4e0d\u53ef\u9760 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "pressure_mpa": 0.8, "pressure_drop": 0.02, "insulation_mohm": 1.2,
        "grounded": False, "circuits_ok": True, "wire_ok": True,
    })
    assert ok is False, "\u63a5\u5730\u4e0d\u53ef\u9760\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u63a5\u5730" in r for r in rs), "\u63a5\u5730\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 5. \u53cd\u4f8b: \u7f3a\u538b\u529b -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "pressure_drop": 0.02, "insulation_mohm": 1.2,
        "grounded": True, "circuits_ok": True, "wire_ok": True,
    })
    assert ok is False, "\u7f3a\u538b\u529b\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 6. \u53cd\u4f8b: \u56de\u8def\u6807\u8bc6\u9519 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "pressure_mpa": 0.8, "pressure_drop": 0.02, "insulation_mohm": 1.2,
        "grounded": True, "circuits_ok": False, "wire_ok": True,
    })
    assert ok is False, "\u56de\u8def\u9519\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 7. \u53cd\u4f8b: \u7ebf\u5f84\u4e0d\u7b26 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "pressure_mpa": 0.8, "pressure_drop": 0.02, "insulation_mohm": 1.2,
        "grounded": True, "circuits_ok": True, "wire_ok": False,
    })
    assert ok is False, "\u7ebf\u5f84\u4e0d\u7b26\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 8. \u53cd\u4f8b: \u538b\u529b 0.5 \u4e0d\u8db3 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "pressure_mpa": 0.5, "pressure_drop": 0.02, "insulation_mohm": 1.2,
        "grounded": True, "circuits_ok": True, "wire_ok": True,
    })
    assert ok is False, "\u538b\u529b\u4e0d\u8db3\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 9. BOM \u5904\u7406
    here = os.path.dirname(os.path.abspath(__file__))
    bom_path = os.path.join(here, "_bom_sample.json")
    payload = json.dumps({
        "pressure_mpa": 0.8, "pressure_drop": 0.02, "insulation_mohm": 1.2,
        "grounded": True, "circuits_ok": True, "wire_ok": True,
    }, ensure_ascii=False)
    with open(bom_path, "wb") as f:
        f.write(b"\xef\xbb\xbf" + payload.encode("utf-8"))
    d = load_json(bom_path)
    assert d.get("grounded") is True, "BOM \u8f93\u5165 key \u4e0d\u5e94\u5e26 \\ufeff"
    assert "insulation_mohm" in d, "BOM \u8f93\u5165 key \u5fc5\u987b\u5e72\u51c0"
    os.remove(bom_path)
    passed += 1

    # 10. \u8fb9\u754c: \u7edd\u7f18\u6070\u597d 0.5 \u5408\u683c\u7ebf -> \u901a\u8fc7(>=)
    ok, rs = evaluate({
        "pressure_mpa": 0.8, "pressure_drop": 0.05, "insulation_mohm": 0.5,
        "grounded": True, "circuits_ok": True, "wire_ok": True,
    })
    assert ok is True, "\u5408\u683c\u7ebf\u8fb9\u754c\u5e94\u901a\u8fc7: %s" % rs
    passed += 1

    line = "SELFTEST OK (%d assertions)" % passed
    return line, passed


def main():
    ap = argparse.ArgumentParser(description="\u6c34\u7535\u9a8c\u6536\u8bb0\u5f55\u6821\u9a8c")
    ap.add_argument("--file", help="\u6c34\u7535\u9a8c\u6536 JSON")
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
