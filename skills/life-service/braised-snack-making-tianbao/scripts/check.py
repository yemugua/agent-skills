# -*- coding: utf-8 -*-
"""\u5364\u5473\u5364\u5236\u8bb0\u5f55\u6821\u9a8c\u811a\u672c\u3002

\u7528\u6cd5:
  python check.py --file \u5364\u5236\u8bb0\u5f55.json
  python check.py --selftest

JSON \u5b57\u6bb5:
  blanched      \u8089\u7c7b\u662f\u5426\u712f\u6c34 (true/false, \u7d20\u83dc\u53ef\u7701\u7565)
  braise_minutes \u5364\u5236\u5206\u949f\u6570 (\u6570\u5b57)
  is_meat       \u662f\u5426\u8364\u83dc (true/false)
  broth_uses    \u5364\u6c34\u5df2\u4f7f\u7528\u6b21\u6570 (\u6574\u6570)
  stored        \u4fdd\u5b58\u65b9\u5f0f: fridge(\u51b7\u85cf)/room(\u5e38\u6e29)/none(\u672a\u4fdd\u5b58)
  spoiled       \u662f\u5426\u89c2\u5bdf\u5230\u53d8\u8d28\u4fe1\u53f7 (true/false)
"""
import argparse
import json
import os
import sys

# \u5364\u5236\u65f6\u95f4\u5b89\u5168\u533a\u95f4\uff08\u5206\u949f\uff09\uff0ckey \u7531\u8c03\u7528\u65b9\u6309\u98df\u6750\u7ed9\u5b9a\u4e0a\u4e0b\u9650\u4e0d\u4fbf\uff0c\u8fd9\u91cc\u7528\u901a\u7528\u9608\u503c
MEAT_MIN = 10
MEAT_MAX = 90
VEG_MAX = 30
BROTH_USE_LIMIT = 3


def evaluate(data):
    reasons = []
    ok = True

    spoiled = data.get("spoiled")
    if spoiled is True:
        ok = False
        reasons.append("\u89c2\u5bdf\u5230\u53d8\u8d28\u4fe1\u53f7(\u9178\u998a/\u53d1\u9ecf/\u4ea7\u6c14), \u5364\u6c34\u5fc5\u987b\u6574\u9505\u5e9f\u5f03, \u4e0d\u53ef\u7ee7\u7eed\u98df\u7528")
        # \u53d8\u8d28\u662f\u6700\u9ad8\u4f18\u5148, \u76f4\u63a5\u8fd4\u56de
        return ok, reasons

    is_meat = data.get("is_meat")
    blanched = data.get("blanched")
    if is_meat is True and blanched is not True:
        ok = False
        reasons.append("\u8364\u83dc\u672a\u712f\u6c34\u76f4\u63a5\u5364, \u8840\u6cab\u8165\u5473\u91cd\u4e14\u5364\u6c34\u6613\u6d51, \u5fc5\u987b\u5148\u712f\u6c34\u53bb\u6cab")

    minutes = data.get("braise_minutes")
    if minutes is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u5364\u5236\u65f6\u95f4(braise_minutes), \u65e0\u6cd5\u5224\u65ad\u662f\u5426\u5939\u751f\u6216\u8fc7\u5934")
    else:
        try:
            m = float(minutes)
        except (TypeError, ValueError):
            ok = False
            reasons.append("braise_minutes \u4e0d\u662f\u6570\u5b57")
        else:
            if is_meat is True and (m < MEAT_MIN or m > MEAT_MAX):
                ok = False
                reasons.append("\u8364\u83dc\u5364\u5236 %.0f \u5206\u949f\u8d85\u51fa\u5b89\u5168\u533a\u95f4(10\u201390), \u53ef\u80fd\u5939\u751f\u6216\u8fc7\u5ea6\u8f6f\u70c2" % m)
            if is_meat is False and m > VEG_MAX:
                ok = False
                reasons.append("\u7d20\u83dc\u5364\u5236 %.0f \u5206\u949f\u8d85\u8fc7 30 \u5206\u949f\u4e0a\u9650, \u6613\u8fc7\u54b8\u8fc7\u70c2" % m)

    uses = data.get("broth_uses")
    if uses is not None:
        try:
            u = int(uses)
        except (TypeError, ValueError):
            ok = False
            reasons.append("broth_uses \u4e0d\u662f\u6574\u6570")
        else:
            if u > BROTH_USE_LIMIT:
                ok = False
                reasons.append("\u5364\u6c34\u5df2\u4f7f\u7528 %d \u6b21\u8d85\u8fc7\u4e0a\u9650 3 \u6b21, \u6742\u83cc\u79ef\u7d2f\u98ce\u5473\u52a3\u5316, \u5efa\u8bae\u5e9f\u5f03" % u)

    stored = data.get("stored")
    if stored is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u4fdd\u5b58\u65b9\u5f0f(stored), \u5364\u6c34\u4fdd\u5b58\u72b6\u6001\u672a\u77e5")
    elif stored == "room":
        ok = False
        reasons.append("\u5364\u6c34\u5e38\u6e29\u4fdd\u5b58, \u590f\u5b63\u6570\u5c0f\u65f6\u5373\u9178\u8d25, \u5fc5\u987b\u716e\u6cb8\u540e\u51b7\u85cf")
    elif stored not in ("fridge", "none"):
        ok = False
        reasons.append("stored \u53d6\u503c\u975e\u6cd5(\u5e94\u4e3a fridge/room/none)")

    if ok:
        reasons.append("\u5364\u5236\u8bb0\u5f55\u901a\u8fc7: \u712f\u6c34/\u65f6\u95f4/\u5364\u6c34\u6b21\u6570/\u4fdd\u5b58\u5747\u5408\u89c4")
    return ok, reasons


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def selftest():
    passed = 0

    # 1. \u6b63\u4f8b: \u8364\u83dc\u712f\u6c34+\u65f6\u95f4\u5408\u89c4+\u5364\u6c342\u6b21+\u51b7\u85cf -> \u901a\u8fc7
    ok, rs = evaluate({
        "is_meat": True, "blanched": True, "braise_minutes": 60,
        "broth_uses": 2, "stored": "fridge", "spoiled": False,
    })
    assert ok is True, "\u6b63\u4f8b\u5e94\u901a\u8fc7: %s" % rs
    passed += 1

    # 2. \u53cd\u4f8b: \u53d8\u8d28\u4fe1\u53f7 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({"spoiled": True})
    assert ok is False, "\u53d8\u8d28\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u5e9f\u5f03" in r for r in rs), "\u53d8\u8d28\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 3. \u53cd\u4f8b: \u8364\u83dc\u672a\u712f\u6c34 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "is_meat": True, "blanched": False, "braise_minutes": 60,
        "broth_uses": 1, "stored": "fridge", "spoiled": False,
    })
    assert ok is False, "\u8364\u83dc\u672a\u712f\u6c34\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u712f\u6c34" in r for r in rs), "\u712f\u6c34\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 4. \u53cd\u4f8b: \u5364\u5236\u65f6\u95f4\u7f3a\u5931 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "is_meat": True, "blanched": True, "broth_uses": 1,
        "stored": "fridge", "spoiled": False,
    })
    assert ok is False, "\u7f3a\u65f6\u95f4\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 5. \u53cd\u4f8b: \u5364\u6c34\u8d85 3 \u6b21 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "is_meat": True, "blanched": True, "braise_minutes": 60,
        "broth_uses": 5, "stored": "fridge", "spoiled": False,
    })
    assert ok is False, "\u8d85\u6b21\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("3 \u6b21" in r for r in rs), "\u8d85\u6b21\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 6. \u53cd\u4f8b: \u5e38\u6e29\u4fdd\u5b58 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "is_meat": True, "blanched": True, "braise_minutes": 60,
        "broth_uses": 1, "stored": "room", "spoiled": False,
    })
    assert ok is False, "\u5e38\u6e29\u4fdd\u5b58\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u51b7\u85cf" in r for r in rs), "\u4fdd\u5b58\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 7. \u53cd\u4f8b: \u7d20\u83dc\u5364 60 \u5206\u949f -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "is_meat": False, "braise_minutes": 60,
        "broth_uses": 1, "stored": "fridge", "spoiled": False,
    })
    assert ok is False, "\u7d20\u83dc\u8d85\u65f6\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 8. \u53cd\u4f8b: \u8364\u83dc\u65f6\u95f4 5 \u5206\u949f\u5939\u751f -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "is_meat": True, "blanched": True, "braise_minutes": 5,
        "broth_uses": 1, "stored": "fridge", "spoiled": False,
    })
    assert ok is False, "\u5939\u751f\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 9. BOM \u5904\u7406
    here = os.path.dirname(os.path.abspath(__file__))
    bom_path = os.path.join(here, "_bom_sample.json")
    payload = json.dumps({
        "is_meat": True, "blanched": True, "braise_minutes": 60,
        "broth_uses": 1, "stored": "fridge", "spoiled": False,
    }, ensure_ascii=False)
    with open(bom_path, "wb") as f:
        f.write(b"\xef\xbb\xbf" + payload.encode("utf-8"))
    d = load_json(bom_path)
    assert d.get("stored") == "fridge", "BOM \u8f93\u5165\u89e3\u6790\u540e key \u4e0d\u5e94\u5e26 \\ufeff"
    assert "braise_minutes" in d, "BOM \u8f93\u5165 key \u5fc5\u987b\u5e72\u51c0"
    os.remove(bom_path)
    passed += 1

    # 10. \u8fb9\u754c: \u7d20\u83dc\u5408\u89c4 -> \u901a\u8fc7
    ok, rs = evaluate({
        "is_meat": False, "braise_minutes": 8,
        "broth_uses": 1, "stored": "fridge", "spoiled": False,
    })
    assert ok is True, "\u7d20\u83dc\u5408\u89c4\u5e94\u901a\u8fc7: %s" % rs
    passed += 1

    line = "SELFTEST OK (%d assertions)" % passed
    return line, passed


def main():
    ap = argparse.ArgumentParser(description="\u5364\u5473\u5364\u5236\u8bb0\u5f55\u6821\u9a8c")
    ap.add_argument("--file", help="\u5364\u5236\u8bb0\u5f55 JSON")
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
