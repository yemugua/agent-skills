# -*- coding: utf-8 -*-
"""\u74f7\u7816\u7a7a\u9f13\u8bb0\u5f55\u6821\u9a8c\u811a\u672c\u3002

\u7528\u6cd5:
  python check.py --file \u7a7a\u9f13\u8bb0\u5f55.json
  python check.py --selftest

JSON \u5b57\u6bb5:
  total_tiles      \u603b\u7816\u6570 (\u6574\u6570)
  hollow_tiles     \u6574\u7816/\u7a7a\u9f13\u7816\u6570 (\u6574\u6570)
  edge_hollow      \u662f\u5426\u5b58\u5728\u8fb9\u89d2\u7a7a\u9f13 (true/false)
  hollow_ratio     \u6574\u4f53\u7a7a\u9f13\u7387\u767e\u5206\u6bd4 (\u6570\u5b57)
  sampled          \u662f\u5426\u4ec5\u62bd\u6837\u672a\u9010\u7816 (true/false)
"""
import argparse
import json
import os
import sys

SINGLE_LIMIT = 5.0
OVERALL_LIMIT = 5.0


def evaluate(data):
    reasons = []
    ok = True

    sampled = data.get("sampled")
    if sampled is True:
        ok = False
        reasons.append("\u4ec5\u62bd\u6837\u672a\u9010\u7816\u6572\u51fb, \u68c0\u67e5\u4e0d\u5b8c\u6574, \u4e0d\u80fd\u5224\u5b9a\u5408\u683c")

    edge = data.get("edge_hollow")
    if edge is True:
        ok = False
        reasons.append("\u5b58\u5728\u8fb9\u89d2\u7a7a\u9f13(\u8fb9\u89d2\u7981\u7a7a\u9f13), \u6613\u6389\u7816, \u987b\u5904\u7406")

    total = data.get("total_tiles")
    hollow = data.get("hollow_tiles")
    if total is None or hollow is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u603b\u7816\u6570\u6216\u7a7a\u9f13\u7816\u6570, \u65e0\u6cd5\u7b97\u6574\u4f53\u7a7a\u9f13\u7387")
    else:
        try:
            t = int(total)
            h = int(hollow)
        except (TypeError, ValueError):
            ok = False
            reasons.append("\u603b\u7816\u6570/\u7a7a\u9f13\u7816\u6570\u4e0d\u662f\u6574\u6570")
        else:
            if t <= 0:
                ok = False
                reasons.append("\u603b\u7816\u6570\u5fc5\u987b\u5927\u4e8e 0")
            else:
                ratio = h * 100.0 / t
                if ratio > OVERALL_LIMIT:
                    ok = False
                    reasons.append("\u6574\u4f53\u7a7a\u9f13\u7387 %.1f%% \u8d85\u8fc7 5%% \u4e0a\u9650, \u7cfb\u7edf\u6027\u95ee\u9898\u987b\u8f6c\u4e13\u4e1a\u6574\u6539" % ratio)

    rr = data.get("hollow_ratio")
    if rr is not None:
        try:
            r = float(rr)
        except (TypeError, ValueError):
            ok = False
            reasons.append("hollow_ratio \u4e0d\u662f\u6570\u5b57")
        else:
            if r > SINGLE_LIMIT:
                ok = False
                reasons.append("\u5355\u7816/\u6574\u4f53\u7a7a\u9f13\u7387 %.1f%% \u8d85\u8fc7 5%% \u4e0a\u9650" % r)

    if ok:
        reasons.append("\u7a7a\u9f13\u8bb0\u5f55\u901a\u8fc7: \u9010\u7816\u68c0\u67e5\u3001\u65e0\u8fb9\u89d2\u7a7a\u9f13\u3001\u7a7a\u9f13\u7387\u5408\u89c4")
    return ok, reasons


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def selftest():
    passed = 0

    # 1. \u6b63\u4f8b: \u9010\u7816, \u65e0\u8fb9\u89d2, 100\u78162\u7a7a, \u6574\u4f532% -> \u901a\u8fc7
    ok, rs = evaluate({
        "total_tiles": 100, "hollow_tiles": 2, "edge_hollow": False,
        "hollow_ratio": 2.0, "sampled": False,
    })
    assert ok is True, "\u6b63\u4f8b\u5e94\u901a\u8fc7: %s" % rs
    passed += 1

    # 2. \u53cd\u4f8b: \u8fb9\u89d2\u7a7a\u9f13 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "total_tiles": 100, "hollow_tiles": 2, "edge_hollow": True,
        "hollow_ratio": 2.0, "sampled": False,
    })
    assert ok is False, "\u8fb9\u89d2\u7a7a\u9f13\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u8fb9\u89d2" in r for r in rs), "\u8fb9\u89d2\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 3. \u53cd\u4f8b: \u6574\u4f53\u7a7a\u9f13\u7387 10% -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "total_tiles": 100, "hollow_tiles": 10, "edge_hollow": False,
        "hollow_ratio": 10.0, "sampled": False,
    })
    assert ok is False, "\u6574\u4f53\u8d85\u7387\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("5%" in r for r in rs), "\u8d85\u7387\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 4. \u53cd\u4f8b: \u4ec5\u62bd\u6837 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "total_tiles": 100, "hollow_tiles": 2, "edge_hollow": False,
        "hollow_ratio": 2.0, "sampled": True,
    })
    assert ok is False, "\u62bd\u6837\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u62bd\u6837" in r for r in rs), "\u62bd\u6837\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 5. \u53cd\u4f8b: \u7f3a\u603b\u7816\u6570 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "hollow_tiles": 2, "edge_hollow": False,
        "hollow_ratio": 2.0, "sampled": False,
    })
    assert ok is False, "\u7f3a\u603b\u7816\u6570\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 6. \u53cd\u4f8b: \u5355\u7816\u7387 8% -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "total_tiles": 100, "hollow_tiles": 2, "edge_hollow": False,
        "hollow_ratio": 8.0, "sampled": False,
    })
    assert ok is False, "\u5355\u7816\u8d85\u7387\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 7. \u53cd\u4f8b: \u603b\u7816\u6570 0 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "total_tiles": 0, "hollow_tiles": 0, "edge_hollow": False,
        "hollow_ratio": 0.0, "sampled": False,
    })
    assert ok is False, "\u603b\u7816\u65700\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 8. \u53cd\u4f8b: \u8fb9\u6570\u7a7a\u9f13+\u8d85\u7387\u53e0\u52a0 -> \u5fc5\u987b\u4e0d\u5408\u683c\u4e14\u542b\u4e24\u9879
    ok, rs = evaluate({
        "total_tiles": 100, "hollow_tiles": 10, "edge_hollow": True,
        "hollow_ratio": 10.0, "sampled": False,
    })
    assert ok is False, "\u591a\u91cd\u4e0d\u5408\u683c\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u8fb9\u89d2" in r for r in rs) and any("5%" in r for r in rs), "\u5e94\u542b\u4e24\u9879: %s" % rs
    passed += 1

    # 9. BOM \u5904\u7406
    here = os.path.dirname(os.path.abspath(__file__))
    bom_path = os.path.join(here, "_bom_sample.json")
    payload = json.dumps({
        "total_tiles": 100, "hollow_tiles": 2, "edge_hollow": False,
        "hollow_ratio": 2.0, "sampled": False,
    }, ensure_ascii=False)
    with open(bom_path, "wb") as f:
        f.write(b"\xef\xbb\xbf" + payload.encode("utf-8"))
    d = load_json(bom_path)
    assert d.get("edge_hollow") is False, "BOM \u8f93\u5165 key \u4e0d\u5e94\u5e26 \\ufeff"
    assert "total_tiles" in d, "BOM \u8f93\u5165 key \u5fc5\u987b\u5e72\u51c0"
    os.remove(bom_path)
    passed += 1

    # 10. \u8fb9\u754c: \u6574\u4f53\u6070\u597d 5% -> \u901a\u8fc7(<=)
    ok, rs = evaluate({
        "total_tiles": 100, "hollow_tiles": 5, "edge_hollow": False,
        "hollow_ratio": 5.0, "sampled": False,
    })
    assert ok is True, "5%\u8fb9\u754c\u5e94\u901a\u8fc7: %s" % rs
    passed += 1

    line = "SELFTEST OK (%d assertions)" % passed
    return line, passed


def main():
    ap = argparse.ArgumentParser(description="\u74f7\u7816\u7a7a\u9f13\u8bb0\u5f55\u6821\u9a8c")
    ap.add_argument("--file", help="\u7a7a\u9f13\u8bb0\u5f55 JSON")
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
