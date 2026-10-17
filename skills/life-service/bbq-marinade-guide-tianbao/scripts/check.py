# -*- coding: utf-8 -*-
"""\u70e7\u70e4\u814c\u5236\u65b9\u6848\u6821\u9a8c\u811a\u672c\u3002

\u7528\u6cd5:
  python check.py --file \u814c\u5236\u65b9\u6848.json
  python check.py --selftest

JSON \u5b57\u6bb5:
  meat_type      \u98df\u6750: beef/mutton/pork/chicken/seafood/vegetable
  marinade_minutes \u814c\u5236\u5206\u949f\u6570 (\u6570\u5b57)
  tenderizer_g_per_kg \u5ae9\u8089\u7c89\u514b\u6bcf\u516c\u65a4 (\u6570\u5b57, 0 \u8868\u793a\u4e0d\u7528)
  refrigerated   \u662f\u5426\u51b7\u85cf (true/false)
"""
import argparse
import json
import os
import sys

# \u5404\u98df\u6750\u814c\u5236\u65f6\u95f4\u4e0a\u9650\uff08\u5206\u949f\uff09\uff0c\u4e0b\u9650\u7edf\u4e00\u7eb3\u5165\u5224\u65ad
TIME_LIMIT = {
    "beef": 24 * 60, "mutton": 24 * 60, "pork": 12 * 60,
    "chicken": 4 * 60, "seafood": 60, "vegetable": 2 * 60,
}
TENDERIZER_LIMIT = 3.0
TENDERIZER_OVER = 5.0
VALID_TYPES = list(TIME_LIMIT.keys())


def evaluate(data):
    reasons = []
    ok = True

    mtype = data.get("meat_type")
    if mtype is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u98df\u6750\u7c7b\u578b(meat_type), \u65e0\u6cd5\u5339\u914d\u65f6\u95f4\u533a\u95f4")
    elif mtype not in VALID_TYPES:
        ok = False
        reasons.append("meat_type \u53d6\u503c\u975e\u6cd5(\u5e94\u4e3a beef/mutton/pork/chicken/seafood/vegetable)")

    minutes = data.get("marinade_minutes")
    if minutes is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u814c\u5236\u65f6\u95f4(marinade_minutes)")
    else:
        try:
            m = float(minutes)
        except (TypeError, ValueError):
            ok = False
            reasons.append("marinade_minutes \u4e0d\u662f\u6570\u5b57")
        else:
            if mtype in TIME_LIMIT and m > TIME_LIMIT[mtype]:
                ok = False
                reasons.append("%s \u814c\u5236 %.0f \u5206\u949f\u8d85\u8fc7\u4e0a\u9650 %d \u5206\u949f, \u4f1a\u51fa\u6c34\u53d8\u5473\u53d1\u67f4" % (
                    mtype, m, TIME_LIMIT[mtype]))

    tender = data.get("tenderizer_g_per_kg")
    if tender is not None:
        try:
            t = float(tender)
        except (TypeError, ValueError):
            ok = False
            reasons.append("tenderizer_g_per_kg \u4e0d\u662f\u6570\u5b57")
        else:
            if t > TENDERIZER_OVER:
                ok = False
                reasons.append("\u5ae9\u8089\u7c89 %.1fg/kg \u8d85\u8fc7\u8fc7\u91cf\u7ebf 5g/kg, \u8089\u8d28\u7c89\u70c2\u5982\u6e23" % t)
            elif t > TENDERIZER_LIMIT:
                ok = False
                reasons.append("\u5ae9\u8089\u7c89 %.1fg/kg \u8d85\u8fc7\u5b89\u5168\u4e0a\u9650 3g/kg" % t)

    refrig = data.get("refrigerated")
    if refrig is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u662f\u5426\u51b7\u85cf(refrigerated)")
    elif refrig is not True:
        ok = False
        reasons.append("\u672a\u51b7\u85cf\u814c\u5236, \u5e38\u6e29\u5c24\u5176\u590f\u5b63\u7ec6\u83cc\u7e41\u6b96\u98ce\u9669\u9ad8, \u5fc5\u987b\u51b7\u85cf")

    if ok:
        reasons.append("\u814c\u5236\u65b9\u6848\u901a\u8fc7: \u65f6\u95f4/\u5ae9\u8089\u7c89/\u51b7\u85cf\u5747\u5408\u89c4")
    return ok, reasons


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def selftest():
    passed = 0

    # 1. \u6b63\u4f8b: \u725b\u8089\u51b7\u85cf\u814c 6h, \u5ae9\u8089\u7c89 2g/kg -> \u901a\u8fc7
    ok, rs = evaluate({
        "meat_type": "beef", "marinade_minutes": 360,
        "tenderizer_g_per_kg": 2.0, "refrigerated": True,
    })
    assert ok is True, "\u6b63\u4f8b\u5e94\u901a\u8fc7: %s" % rs
    passed += 1

    # 2. \u53cd\u4f8b: \u5ae9\u8089\u7c89\u8fc7\u91cf 8g/kg -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "meat_type": "beef", "marinade_minutes": 360,
        "tenderizer_g_per_kg": 8.0, "refrigerated": True,
    })
    assert ok is False, "\u5ae9\u8089\u7c89\u8fc7\u91cf\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u7c89\u70c2" in r for r in rs), "\u8fc7\u91cf\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 3. \u53cd\u4f8b: \u9e21\u8089\u5e38\u6e29\u814c -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "meat_type": "chicken", "marinade_minutes": 120,
        "tenderizer_g_per_kg": 0, "refrigerated": False,
    })
    assert ok is False, "\u5e38\u6e29\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u51b7\u85cf" in r for r in rs), "\u51b7\u85cf\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 4. \u53cd\u4f8b: \u6d77\u9c9c\u814c 120 \u5206\u949f\u8d85\u4e0a\u9650 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "meat_type": "seafood", "marinade_minutes": 120,
        "tenderizer_g_per_kg": 0, "refrigerated": True,
    })
    assert ok is False, "\u6d77\u9c9c\u8d85\u65f6\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 5. \u53cd\u4f8b: \u7f3a meat_type -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "marinade_minutes": 360, "tenderizer_g_per_kg": 0, "refrigerated": True,
    })
    assert ok is False, "\u7f3a\u98df\u6750\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 6. \u53cd\u4f8b: \u7f3a\u65f6\u95f4 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "meat_type": "beef", "tenderizer_g_per_kg": 0, "refrigerated": True,
    })
    assert ok is False, "\u7f3a\u65f6\u95f4\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 7. \u53cd\u4f8b: meat_type \u975e\u6cd5 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "meat_type": "fish", "marinade_minutes": 30,
        "tenderizer_g_per_kg": 0, "refrigerated": True,
    })
    assert ok is False, "\u975e\u6cd5\u98df\u6750\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 8. \u53cd\u4f8b: \u5ae9\u8089\u7c89 4g/kg \u8d85\u5b89\u5168\u4e0a\u9650 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "meat_type": "pork", "marinade_minutes": 300,
        "tenderizer_g_per_kg": 4.0, "refrigerated": True,
    })
    assert ok is False, "\u8d85\u5b89\u5168\u4e0a\u9650\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 9. BOM \u5904\u7406
    here = os.path.dirname(os.path.abspath(__file__))
    bom_path = os.path.join(here, "_bom_sample.json")
    payload = json.dumps({
        "meat_type": "beef", "marinade_minutes": 360,
        "tenderizer_g_per_kg": 2.0, "refrigerated": True,
    }, ensure_ascii=False)
    with open(bom_path, "wb") as f:
        f.write(b"\xef\xbb\xbf" + payload.encode("utf-8"))
    d = load_json(bom_path)
    assert d.get("meat_type") == "beef", "BOM \u8f93\u5165 key \u4e0d\u5e94\u5e26 \\ufeff"
    assert "marinade_minutes" in d, "BOM \u8f93\u5165 key \u5fc5\u987b\u5e72\u51c0"
    os.remove(bom_path)
    passed += 1

    # 10. \u8fb9\u754c: \u9e21\u8089\u51b7\u85cf\u814c 2h, \u65e0\u5ae9\u8089\u7c89 -> \u901a\u8fc7
    ok, rs = evaluate({
        "meat_type": "chicken", "marinade_minutes": 120,
        "tenderizer_g_per_kg": 0, "refrigerated": True,
    })
    assert ok is True, "\u9e21\u8089\u5408\u89c4\u5e94\u901a\u8fc7: %s" % rs
    passed += 1

    line = "SELFTEST OK (%d assertions)" % passed
    return line, passed


def main():
    ap = argparse.ArgumentParser(description="\u70e7\u70e4\u814c\u5236\u65b9\u6848\u6821\u9a8c")
    ap.add_argument("--file", help="\u814c\u5236\u65b9\u6848 JSON")
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
