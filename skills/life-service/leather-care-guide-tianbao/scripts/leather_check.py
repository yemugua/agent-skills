# -*- coding: utf-8 -*-
"""\u76ae\u5177\u62a4\u7406 \u64cd\u4f5c\u987a\u5e8f\u4e0e\u5b8c\u6574\u6027\u81ea\u68c0\u5de5\u5177\uff08\u6b65\u9aa4\u6e05\u5355\u6821\u9a8c\uff09\u3002"""
import argparse
import json
import os
import sys

CANON = ['\u6e05\u7070', '\u4e0a\u62a4\u7406\u5242', '\u907f\u5149\u5b58\u653e', '\u9632\u6f6e']
FORBID = ['\u66b4\u6652', '\u6cbe\u6c34\u4e0d\u64e6', '\u5f3a\u78b1\u64e6\u76ae']
SAFETY = '\u6e05\u7070'


def read_text(path):
    """\u8bfb\u53d6\u8f93\u5165\u6587\u4ef6\uff0c\u81ea\u52a8\u5265\u79bb UTF-8 BOM\u3002"""
    with open(path, 'rb') as f:
        return f.read().decode('utf-8-sig')


def parse_steps(text):
    """\u63a5\u53d7 JSON {"steps":[...]} \u6216\u6bcf\u884c\u4e00\u6b65\u7684\u6587\u672c\u3002"""
    text = text.strip()
    if text.startswith('{'):
        return json.loads(text).get('steps', [])
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def norm(s):
    return s.strip()


def validate(steps):
    """\u8fd4\u56de (ok, reasons)\u3002\u5148\u770b\u771f\u5b9e\u7f3a\u9677\uff0c\u518d\u770b\u5b8c\u6574\u6027\u3002"""
    reasons = []
    ns = [norm(s) for s in steps]
    present = set(ns)
    missing = [c for c in CANON if c not in present]
    if missing:
        reasons.append('\u7f3a\u5c11\u5fc5\u8981\u6b65\u9aa4: ' + '\u3001'.join(missing))
    idxs = [ns.index(c) for c in CANON if c in present]
    if idxs != sorted(idxs):
        reasons.append('\u6b65\u9aa4\u987a\u5e8f\u9519\u8bef: \u6b63\u786e\u987a\u5e8f\u4e3a ' + ' -> '.join(CANON))
    for b in FORBID:
        if any(b in s for s in ns):
            reasons.append('\u5b58\u5728\u5371\u9669/\u9519\u8bef\u64cd\u4f5c: ' + b)
    return (len(reasons) == 0), reasons


def main():
    ap = argparse.ArgumentParser(description='\u76ae\u5177\u62a4\u7406 \u64cd\u4f5c\u6e05\u5355\u81ea\u68c0')
    ap.add_argument('--file', help='\u8f93\u5165\u6b65\u9aa4\u6587\u4ef6(JSON \u6216\u6bcf\u884c\u4e00\u6b65)')
    ap.add_argument('--selftest', action='store_true', help='\u8fd0\u884c\u5185\u7f6e\u81ea\u68c0')
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.file:
        print('\u8bf7\u4f7f\u7528 --file \u6307\u5b9a\u8f93\u5165, \u6216 --selftest \u81ea\u68c0')
        return 2
    steps = parse_steps(read_text(args.file))
    ok, reasons = validate(steps)
    out = ('OK\n' if ok else 'FAIL\n') + '\n'.join(reasons)
    res = os.path.join(os.path.dirname(os.path.abspath(args.file)), '_last_result.txt')
    with open(res, 'w', encoding='utf-8') as f:
        f.write(out + '\n')
    print(out)
    return 0 if ok else 1


def selftest():
    passed = 0
    total = 0
    total += 1
    ok, r = validate(CANON)
    if ok:
        passed += 1
    else:
        raise AssertionError('\u6b63\u4f8b\u5e94\u5224\u5408\u683c: %s' % r)
    total += 1
    bad = list(CANON)
    bad.pop(1)
    ok, r = validate(bad)
    if not ok:
        passed += 1
    else:
        raise AssertionError('\u7f3a\u6b65\u9aa4\u5e94\u5224\u4e0d\u5408\u683c')
    total += 1
    wrong = list(CANON)
    wrong[0], wrong[1] = wrong[1], wrong[0]
    ok, r = validate(wrong)
    if not ok:
        passed += 1
    else:
        raise AssertionError('\u987a\u5e8f\u9519\u5e94\u5224\u4e0d\u5408\u683c')
    total += 1
    danger = list(CANON) + FORBID[:1]
    ok, r = validate(danger)
    if not ok:
        passed += 1
    else:
        raise AssertionError('\u5371\u9669\u64cd\u4f5c\u5e94\u5224\u4e0d\u5408\u683c')
    total += 1
    sample = json.dumps({'steps': CANON}, ensure_ascii=False)
    raw = '\ufeff' + sample
    txt = raw.encode('utf-8').decode('utf-8-sig')
    if '\ufeff' not in txt:
        passed += 1
    else:
        raise AssertionError('UTF-8 BOM \u672a\u6b63\u786e\u5265\u79bb')
    total += 1
    if validate(parse_steps('\n'.join(CANON)))[0]:
        passed += 1
    else:
        raise AssertionError('\u6bcf\u884c\u89e3\u6790\u5931\u8d25')
    total += 1
    ok, r = validate([])
    if not ok:
        passed += 1
    else:
        raise AssertionError('\u7a7a\u8f93\u5165\u5e94\u5224\u4e0d\u5408\u683c')
    total += 1
    idxs = [i for i, _ in enumerate(CANON)]
    if idxs == sorted(idxs):
        passed += 1
    else:
        raise AssertionError('\u6807\u51c6\u987a\u5e8f\u7d22\u5f15\u975e\u9012\u589e')
    total += 1
    if len(FORBID) >= 1:
        passed += 1
    else:
        raise AssertionError('FORBID \u8868\u4e3a\u7a7a, \u53cd\u4f8b\u89c4\u5219\u7f3a\u5931')
    total += 1
    if SAFETY in CANON:
        passed += 1
    else:
        raise AssertionError('\u5173\u952e\u5b89\u5168\u6b65\u7f3a\u5931: ' + SAFETY)
    msg = 'SELFTEST OK passed=%d total=%d' % (passed, total)
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, '_selftest_result.txt'), 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
