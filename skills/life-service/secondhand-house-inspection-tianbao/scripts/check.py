# -*- coding: utf-8 -*-
"""\u4e8c\u624b\u623f\u9a8c\u623f\u8bb0\u5f55\u6821\u9a8c\u811a\u672c\u3002

\u7528\u6cd5:
  python check.py --file \u9a8c\u623f\u8bb0\u5f55.json
  python check.py --selftest

JSON \u5b57\u6bb5:
  checked_zones    \u5df2\u68c0\u67e5\u5206\u533a\u5217\u8868, \u5982 ["door","wall","window","kitchen","electric","plumbing"]
  defects          \u7f3a\u9677\u9879\u5217\u8868, \u6bcf\u9879 {"zone":..., "level":"minor/general/major", "red_line":false}
  red_line_found   \u662f\u5426\u53d1\u73b0\u7ea2\u7ebf\u9879 (true/false)
"""
import argparse
import json
import os
import sys

ALL_ZONES = ["door", "wall", "window", "kitchen", "electric", "plumbing"]
RED_LINE_ZONES = {"electric", "structure"}


def evaluate(data):
    reasons = []
    ok = True

    zones = data.get("checked_zones") or []
    missing = [z for z in ALL_ZONES if z not in zones]
    if missing:
        ok = False
        reasons.append("\u672a\u68c0\u67e5\u5206\u533a %s, \u9a8c\u623f\u4e0d\u5b8c\u6574, \u4e0d\u80fd\u5224\u5b9a\u53ef\u6536\u623f" % "/".join(missing))

    defects = data.get("defects") or []
    major = [d for d in defects if isinstance(d, dict) and d.get("level") == "major"]
    if major:
        ok = False
        reasons.append("\u5b58\u5728 %d \u5904\u4e25\u91cd\u7f3a\u9677(\u5f71\u54cd\u5b89\u5168/\u91cd\u5927\u4f7f\u7528), \u987b\u6574\u6539\u540e\u518d\u6536\u623f" % len(major))

    red = data.get("red_line_found")
    if red is True:
        ok = False
        reasons.append("\u53d1\u73b0\u7ea2\u7ebf\u9879(\u7ed3\u6784/\u7535\u8def\u9690\u853d/\u6e17\u6f0f\u8d23\u4efb\u4e0d\u6e05\u7b49), \u987b\u8f6c\u4ea4\u6301\u8bc1\u4e13\u4e1a\u4eba\u58eb\u786e\u8ba4, \u52ff\u81ea\u884c\u4e0b\u7ed3\u8bba")

    if not defects and not red and not missing:
        reasons.append("\u672a\u53d1\u73b0\u7f3a\u9677\u4e14\u5206\u533a\u9f50\u5168, \u8bb0\u5f55\u53ef\u4f5c\u4e3a\u53ef\u6536\u623f\u53c2\u8003(\u4ecd\u5efa\u8bae\u4e13\u4e1a\u590d\u6838)")

    if ok:
        reasons.append("\u9a8c\u623f\u8bb0\u5f55\u901a\u8fc7: \u5206\u533a\u9f50\u5168\u4e14\u65e0\u4e25\u91cd\u7f3a\u9677/\u7ea2\u7ebf\u9879")
    return ok, reasons


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def selftest():
    passed = 0

    # 1. \u6b63\u4f8b: \u516d\u533a\u9f50\u5168, \u4ec5 1 \u8f7b\u5fae\u7f3a\u9677 -> \u901a\u8fc7
    ok, rs = evaluate({
        "checked_zones": ALL_ZONES, "red_line_found": False,
        "defects": [{"zone": "wall", "level": "minor", "red_line": False}],
    })
    assert ok is True, "\u6b63\u4f8b\u5e94\u901a\u8fc7: %s" % rs
    passed += 1

    # 2. \u53cd\u4f8b: \u6f0f\u67e5\u5206\u533a -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "checked_zones": ["door", "wall"], "red_line_found": False, "defects": [],
    })
    assert ok is False, "\u6f0f\u67e5\u5206\u533a\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u672a\u68c0\u67e5\u5206\u533a" in r for r in rs), "\u6f0f\u67e5\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 3. \u53cd\u4f8b: \u4e25\u91cd\u7f3a\u9677 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "checked_zones": ALL_ZONES, "red_line_found": False,
        "defects": [{"zone": "electric", "level": "major", "red_line": False}],
    })
    assert ok is False, "\u4e25\u91cd\u7f3a\u9677\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u4e25\u91cd\u7f3a\u9677" in r for r in rs), "\u4e25\u91cd\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 4. \u53cd\u4f8b: \u7ea2\u7ebf\u9879 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "checked_zones": ALL_ZONES, "red_line_found": True, "defects": [],
    })
    assert ok is False, "\u7ea2\u7ebf\u9879\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u8f6c\u4ea4" in r for r in rs), "\u7ea2\u7ebf\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 5. \u53cd\u4f8b: \u65e2\u6f0f\u67e5\u53c8\u6709\u4e25\u91cd -> \u5fc5\u987b\u4e0d\u5408\u683c\u4e14\u542b\u4e24\u9879
    ok, rs = evaluate({
        "checked_zones": ["door"], "red_line_found": False,
        "defects": [{"zone": "wall", "level": "major", "red_line": False}],
    })
    assert ok is False, "\u591a\u91cd\u7f3a\u9677\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u672a\u68c0\u67e5\u5206\u533a" in r for r in rs) and any("\u4e25\u91cd\u7f3a\u9677" in r for r in rs), "\u5e94\u542b\u4e24\u9879: %s" % rs
    passed += 1

    # 6. \u53cd\u4f8b: \u7a7a\u8bb0\u5f55(\u65e0\u5206\u533a) -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({})
    assert ok is False, "\u7a7a\u8bb0\u5f55\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 7. \u53cd\u4f8b: \u4e25\u91cd\u7f3a\u9677\u88ab\u9519\u6807\u4e3a minor \u4ecd\u5e94\u88ab\u8bc6\u522b -> \u8fd9\u91cc\u6545\u610f\u6807 general \u4e0d\u7b97 major
    ok, rs = evaluate({
        "checked_zones": ALL_ZONES, "red_line_found": False,
        "defects": [{"zone": "wall", "level": "general", "red_line": False}],
    })
    # general \u4e0d\u89e6\u53d1\u4e25\u91cd, \u4f46\u5206\u533a\u9f50\u5168\u65e0\u7ea2\u7ebf -> \u901a\u8fc7
    assert ok is True, "\u4e00\u822c\u7f3a\u9677\u4e0d\u5e94\u963b\u65ad\u6536\u623f: %s" % rs
    passed += 1

    # 8. \u53cd\u4f8b: red_line_found \u975e\u5e03\u5c14 True -> \u4e0d\u89e6\u53d1\u7ea2\u7ebf
    ok, rs = evaluate({
        "checked_zones": ALL_ZONES, "red_line_found": "yes", "defects": [],
    })
    assert ok is True, "\u975e True \u7ea2\u7ebf\u4e0d\u89e6\u53d1: %s" % rs
    passed += 1

    # 9. BOM \u5904\u7406
    here = os.path.dirname(os.path.abspath(__file__))
    bom_path = os.path.join(here, "_bom_sample.json")
    payload = json.dumps({
        "checked_zones": ALL_ZONES, "red_line_found": False, "defects": [],
    }, ensure_ascii=False)
    with open(bom_path, "wb") as f:
        f.write(b"\xef\xbb\xbf" + payload.encode("utf-8"))
    d = load_json(bom_path)
    assert d.get("red_line_found") is False, "BOM \u8f93\u5165 key \u4e0d\u5e94\u5e26 \\ufeff"
    assert "checked_zones" in d, "BOM \u8f93\u5165 key \u5fc5\u987b\u5e72\u51c0"
    os.remove(bom_path)
    passed += 1

    # 10. \u8fb9\u754c: \u516d\u533a\u9f50\u5168\u65e0\u7f3a\u9677\u65e0\u7ea2\u7ebf -> \u901a\u8fc7
    ok, rs = evaluate({
        "checked_zones": ALL_ZONES, "red_line_found": False, "defects": [],
    })
    assert ok is True, "\u9f50\u5168\u65e0\u7f3a\u9677\u5e94\u901a\u8fc7: %s" % rs
    passed += 1

    line = "SELFTEST OK (%d assertions)" % passed
    return line, passed


def main():
    ap = argparse.ArgumentParser(description="\u4e8c\u624b\u623f\u9a8c\u623f\u8bb0\u5f55\u6821\u9a8c")
    ap.add_argument("--file", help="\u9a8c\u623f\u8bb0\u5f55 JSON")
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
