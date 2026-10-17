# -*- coding: utf-8 -*-
"""\u9762\u5305\u63c9\u9762\u81ea\u8bc4\u6821\u9a8c\u811a\u672c\u3002

\u7528\u6cd5:
  python check.py --file \u81ea\u8bc4.json
  python check.py --selftest

JSON \u5b57\u6bb5:
  stage         \u81ea\u8bc4\u9636\u6bb5: pick_up / extended / full
  window_test   \u7a97\u6237\u6d4b\u8bd5\u7834\u53e3: smooth(\u5149\u6ed1) / serrated(\u952f\u9f7f) / none(\u62c9\u4e0d\u51fa)
  knead_minutes \u63c9\u9762\u603b\u5206\u949f\u6570 (\u6570\u5b57)
  dough_temp    \u9762\u56e2\u4e2d\u5fc3\u6e29\u5ea6\u6444\u6c0f\u5ea6 (\u6570\u5b57)
  flour_protein \u9762\u7c89\u86cb\u767d\u8d28\u767e\u5206\u6bd4 (\u6570\u5b57, \u5982 12.5)
"""
import argparse
import json
import os
import sys

# \u5404\u9636\u6bb5\u5141\u8bb8\u7684\u6700\u9ad8\u6e29\u5ea6\u4e0e\u5efa\u8bae\u65f6\u957f\u533a\u95f4
TEMP_LIMIT = 28.0
TEMP_WARN = 30.0
FULL_STAGE = "full"
EXTENDED_STAGE = "extended"
PICK_UP_STAGE = "pick_up"

VALID_STAGES = [PICK_UP_STAGE, EXTENDED_STAGE, FULL_STAGE]
VALID_WINDOW = ["smooth", "serrated", "none"]


def evaluate(data):
    """\u8fd4\u56de (ok, reasons)\u3002ok \u4e3a False \u65f6 reasons \u5fc5\u987b\u5e26\u539f\u56e0\u3002"""
    reasons = []
    ok = True

    stage = data.get("stage")
    if stage is None:
        ok = False
        reasons.append("\u672a\u586b\u5199 stage(\u63c9\u9762\u9636\u6bb5), \u65e0\u6cd5\u5224\u5b9a\u662f\u5426\u5230\u4f4d")
    elif stage not in VALID_STAGES:
        ok = False
        reasons.append("stage \u53d6\u503c\u975e\u6cd5(\u5e94\u4e3a pick_up/extended/full), \u4e0d\u80fd\u636e\u6b64\u5224\u5b9a")

    window = data.get("window_test")
    if window is None:
        ok = False
        reasons.append("\u672a\u505a\u7a97\u6237\u6d4b\u8bd5(window_test \u7f3a\u5931), \u9762\u7b4b\u72b6\u6001\u65e0\u4f9d\u636e")
    elif window not in VALID_WINDOW:
        ok = False
        reasons.append("window_test \u53d6\u503c\u975e\u6cd5, \u65e0\u6cd5\u5224\u65ad\u8584\u819c\u72b6\u6001")

    # \u7a97\u6237\u6d4b\u8bd5\u4e0e\u9636\u6bb5\u4e00\u81f4\u6027: \u5b8c\u5168\u9636\u6bb5\u5fc5\u987b smooth, \u5426\u5219\u77db\u76fe
    if stage == FULL_STAGE and window not in (None, "smooth"):
        ok = False
        reasons.append("stage \u4e3a\u5b8c\u5168\u9636\u6bb5\u4f46\u7a97\u6237\u6d4b\u8bd5\u7834\u53e3\u975e\u5149\u6ed1, \u9762\u7b4b\u672a\u771f\u6b63\u8fbe\u6807(\u53ef\u80fd\u8bef\u5224)")
    if stage == PICK_UP_STAGE and window not in (None, "none"):
        ok = False
        reasons.append("stage \u4e3a\u62fe\u8d77\u9636\u6bb5\u5374\u62c9\u51fa\u819c, \u9636\u6bb5\u4e0e\u8584\u819c\u72b6\u6001\u77db\u76fe")

    # \u6e29\u5ea6: \u8d85\u4e0a\u9650\u5fc5\u987b\u5224\u4e0d\u5408\u683c
    temp = data.get("dough_temp")
    if temp is None:
        ok = False
        reasons.append("\u672a\u586b\u5199\u9762\u56e2\u6e29\u5ea6(dough_temp), \u65e0\u6cd5\u786e\u8ba4\u662f\u5426\u8d85\u6e29")
    else:
        try:
            t = float(temp)
        except (TypeError, ValueError):
            ok = False
            reasons.append("dough_temp \u4e0d\u662f\u6570\u5b57, \u65e0\u6cd5\u5224\u5b9a\u6e29\u5ea6")
        else:
            if t > TEMP_WARN:
                ok = False
                reasons.append("\u9762\u56e2\u6e29\u5ea6 %.1f\u2103 \u8d85\u8fc7 30\u2103 \u8b66\u6212\u7ebf, \u9762\u7b4b\u6613\u5316\u6c34\u3001\u53d1\u9175\u63d0\u524d" % t)
            elif t > TEMP_LIMIT:
                ok = False
                reasons.append("\u9762\u56e2\u6e29\u5ea6 %.1f\u2103 \u8d85\u8fc7 28\u2103 \u4e0a\u9650, \u5e94\u6362\u51b0\u6db2\u4f53\u63a7\u6e29" % t)

    # \u63c9\u9762\u65f6\u957f: \u5b8c\u5168\u9636\u6bb5\u624b\u63c9\u4f4e\u4e8e 15 \u5206\u949f\u89c6\u4e3a\u4e0d\u53ef\u4fe1
    minutes = data.get("knead_minutes")
    if minutes is not None:
        try:
            m = float(minutes)
        except (TypeError, ValueError):
            ok = False
            reasons.append("knead_minutes \u4e0d\u662f\u6570\u5b57")
        else:
            if stage == FULL_STAGE and m < 15:
                ok = False
                reasons.append("\u5b8c\u5168\u9636\u6bb5\u624b\u63c9\u4ec5 %.0f \u5206\u949f, \u65f6\u95f4\u8fc7\u77ed\u96be\u4ee5\u771f\u6b63\u51fa\u819c, \u9636\u6bb5\u7591\u4f3c\u8bef\u5224" % m)

    # \u4f4e\u7b4b\u7c89\u5f3a\u6c42\u5b8c\u5168\u9636\u6bb5
    protein = data.get("flour_protein")
    if protein is not None:
        try:
            p = float(protein)
        except (TypeError, ValueError):
            pass
        else:
            if stage == FULL_STAGE and p < 11.5:
                ok = False
                reasons.append("\u9762\u7c89\u86cb\u767d\u8d28 %.1f%% \u4f4e\u4e8e 11.5%%, \u4f4e\u7b4b\u7c89\u96be\u4ee5\u771f\u6b63\u51fa\u819c" % p)

    if ok:
        reasons.append("\u63c9\u9762\u72b6\u6001\u81ea\u8bc4\u901a\u8fc7: \u9636\u6bb5\u4e0e\u7a97\u6237\u6d4b\u8bd5\u4e00\u81f4\u3001\u6e29\u5ea6\u4e0e\u65f6\u957f\u5728\u533a\u95f4\u5185")
    return ok, reasons


def load_json(path):
    """\u7528 utf-8-sig \u8bfb\u53d6, \u540c\u65f6\u5904\u7406\u5e26 BOM \u4e0e\u4e0d\u5e26 BOM \u7684\u8f93\u5165\u3002"""
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def selftest():
    passed = 0
    failed = 0

    # 1. \u6b63\u4f8b: \u5b8c\u5168\u9636\u6bb5 + \u5149\u6ed1\u7834\u53e3 + \u6e29\u5ea6\u5408\u89c4 + \u65f6\u957f\u5145\u8db3 -> \u901a\u8fc7
    ok, rs = evaluate({
        "stage": "full", "window_test": "smooth",
        "knead_minutes": 30, "dough_temp": 26.0, "flour_protein": 13.0,
    })
    assert ok is True, "\u6b63\u4f8b\u5e94\u5224\u5b9a\u901a\u8fc7: %s" % rs
    passed += 1

    # 2. \u53cd\u4f8b: \u5b8c\u5168\u9636\u6bb5\u5374\u952f\u9f7f\u7834\u53e3 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "stage": "full", "window_test": "serrated",
        "knead_minutes": 30, "dough_temp": 26.0,
    })
    assert ok is False, "\u5b8c\u5168\u9636\u6bb5\u952f\u9f7f\u7834\u53e3\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u9762\u7b4b\u672a\u771f\u6b63\u8fbe\u6807" in r for r in rs), "\u53cd\u4f8b\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 3. \u53cd\u4f8b: \u6e29\u5ea6\u8d85 30 \u8b66\u6212\u7ebf -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "stage": "extended", "window_test": "serrated",
        "knead_minutes": 20, "dough_temp": 32.0,
    })
    assert ok is False, "\u8d85\u6e29\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("30\u2103" in r for r in rs), "\u8d85\u6e29\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 4. \u53cd\u4f8b: \u9636\u6bb5\u7f3a\u5931 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({"window_test": "smooth", "dough_temp": 26.0})
    assert ok is False, "\u7f3a\u9636\u6bb5\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u672a\u586b\u5199 stage" in r for r in rs), "\u7f3a\u9636\u6bb5\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 5. \u53cd\u4f8b: \u7a97\u6237\u6d4b\u8bd5\u7f3a\u5931 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({"stage": "extended", "dough_temp": 26.0})
    assert ok is False, "\u7f3a\u7a97\u6237\u6d4b\u8bd5\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u7a97\u6237\u6d4b\u8bd5" in r for r in rs), "\u7f3a\u7a97\u6237\u6d4b\u8bd5\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 6. \u53cd\u4f8b: \u4f4e\u7b4b\u7c89\u5f3a\u6c42\u5b8c\u5168\u9636\u6bb5 -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "stage": "full", "window_test": "smooth",
        "knead_minutes": 30, "dough_temp": 26.0, "flour_protein": 9.0,
    })
    assert ok is False, "\u4f4e\u7b4b\u7c89\u5b8c\u5168\u9636\u6bb5\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    assert any("\u4f4e\u7b4b" in r for r in rs), "\u4f4e\u7b4b\u539f\u56e0\u7f3a\u5931: %s" % rs
    passed += 1

    # 7. \u53cd\u4f8b: \u5b8c\u5168\u9636\u6bb5\u4f46\u65f6\u957f\u4ec5 5 \u5206\u949f -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({
        "stage": "full", "window_test": "smooth",
        "knead_minutes": 5, "dough_temp": 26.0,
    })
    assert ok is False, "\u5b8c\u5168\u9636\u6bb5\u65f6\u957f\u8fc7\u77ed\u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 8. \u53cd\u4f8b: stage \u975e\u6cd5\u53d6\u503c -> \u5fc5\u987b\u4e0d\u5408\u683c
    ok, rs = evaluate({"stage": "super", "window_test": "smooth", "dough_temp": 26.0})
    assert ok is False, "\u975e\u6cd5 stage \u5fc5\u987b\u5224\u4e0d\u5408\u683c"
    passed += 1

    # 9. BOM \u5904\u7406: \u5e26 UTF-8 BOM \u7684 JSON \u5fc5\u987b\u80fd\u88ab\u6b63\u786e\u89e3\u6790
    here = os.path.dirname(os.path.abspath(__file__))
    bom_path = os.path.join(here, "_bom_sample.json")
    payload = json.dumps({
        "stage": "extended", "window_test": "serrated",
        "knead_minutes": 20, "dough_temp": 26.0,
    }, ensure_ascii=False)
    with open(bom_path, "wb") as f:
        f.write(b"\xef\xbb\xbf" + payload.encode("utf-8"))
    d = load_json(bom_path)
    assert d.get("stage") == "extended", "BOM \u8f93\u5165\u89e3\u6790\u540e\u9996 key \u4e0d\u5e94\u5e26 \\ufeff \u524d\u7f00"
    assert "dough_temp" in d, "BOM \u8f93\u5165\u89e3\u6790\u540e key \u5fc5\u987b\u5e72\u51c0"
    os.remove(bom_path)
    passed += 1

    # 10. \u8fb9\u754c: \u6269\u5c55\u9636\u6bb5 + \u952f\u9f7f + \u6e29\u5ea6\u5408\u89c4 -> \u901a\u8fc7
    ok, rs = evaluate({
        "stage": "extended", "window_test": "serrated",
        "knead_minutes": 20, "dough_temp": 27.0,
    })
    assert ok is True, "\u6269\u5c55\u9636\u6bb5\u5408\u89c4\u5e94\u901a\u8fc7: %s" % rs
    passed += 1

    total = passed + failed
    line = "SELFTEST OK (%d assertions)" % total
    return line, total


def main():
    ap = argparse.ArgumentParser(description="\u9762\u5305\u63c9\u9762\u81ea\u8bc4\u6821\u9a8c")
    ap.add_argument("--file", help="\u81ea\u8bc4 JSON \u6587\u4ef6\u8def\u5f84")
    ap.add_argument("--selftest", action="store_true", help="\u8fd0\u884c\u5185\u7f6e\u81ea\u68c0")
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
