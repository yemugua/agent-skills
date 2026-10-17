# -*- coding: utf-8 -*-
"""\u9c7c\u5858\u589e\u6c27\u65b9\u6848\u6821\u9a8c\u811a\u672c\u3002

\u7528\u6cd5:
  python pond_aeration_plan.py --selftest
  python pond_aeration_plan.py --file pond.json

\u8f93\u5165\u4e3a JSON\uff0c\u5b57\u6bb5\u89c1 SKILL.md \u7b2c\u4e94\u7ae0\u3002\u8bfb\u53d6\u7edf\u4e00\u7528 utf-8-sig \u5265 BOM\u3002
"""
import argparse
import json
import os
import sys

AERATOR_TYPES = ['\u53f6\u8f6e\u5f0f', '\u5fae\u5b54', '\u6c34\u8f66\u5f0f', '\u5c04\u6d41\u5f0f']
HYPOX_SYM = ['\u6d6e\u5934', '\u6c34\u9762\u805a\u96c6', '\u5403\u98df\u5dee', '\u6e38\u8fb9', '\u5f20\u53e3']
DENSITY_LEVELS = ['\u9ad8', '\u4e2d', '\u4f4e']


def load_plan(path):
    raw = open(path, 'rb').read()
    text = raw.decode('utf-8-sig')
    return json.loads(text)


def validate(data):
    findings = []

    def add(level, item, why):
        findings.append({'level': level, 'item': item, 'why': why})

    area = data.get('pond_area_m2')
    density = data.get('density_level')
    do = data.get('do_value_mg')
    symptoms = data.get('symptoms') or []
    atype = data.get('aerator_type')
    acount = data.get('aerator_count')
    windows = data.get('run_windows') or []
    placement = data.get('placement_ok')
    emergency = data.get('emergency_ready')

    # \u8bbe\u5907\u7c7b\u578b
    if atype not in AERATOR_TYPES:
        add('\u5148\u5904\u7406', '\u589e\u6c27\u673a\u7c7b\u578b', 'aerator_type \u4e0d\u5728\u5df2\u77e5\u7c7b\u578b\uff08\u53f6\u8f6e\u5f0f/\u5fae\u5b54/\u6c34\u8f66\u5f0f/\u5c04\u6d41\u5f0f\uff09\u5185')

    # \u53f0\u6570
    if not isinstance(acount, (int, float)) or acount < 1:
        add('\u5148\u5904\u7406', '\u589e\u6c27\u673a\u914d\u7f6e', '\u672a\u914d\u7f6e\u4efb\u4f55\u589e\u6c27\u673a\uff0c\u65e0\u589e\u6c27\u4fdd\u969c')

    # \u6eb6\u6c27
    if isinstance(do, (int, float)) and do < 3:
        add('\u5148\u5904\u7406', '\u6eb6\u6c27\u8fc7\u4f4e', '\u6eb6\u6c27 %s mg/L \u4f4e\u4e8e 3\uff0c\u9700\u7acb\u5373\u589e\u6c27' % do)

    # \u7f3a\u6c27\u4fe1\u53f7\uff08\u7528 any \u5339\u914d\uff0c\u4e0d\u80fd\u7528 in HYPOX_SYM\uff09
    for s in symptoms:
        if any(v in s for v in HYPOX_SYM):
            add('\u5148\u5904\u7406', '\u7f3a\u6c27\u4fe1\u53f7', '\u51fa\u73b0\u7f3a\u6c27\u4fe1\u53f7\uff1a%s' % s)
            break

    # \u9ad8\u5bc6\u5ea6\u53f0\u6570\u504f\u5f31
    if density == '\u9ad8' and isinstance(acount, (int, float)) and acount < 2:
        add('\u5f85\u786e\u8ba4', '\u9ad8\u5bc6\u5ea6\u53f0\u6570', '\u9ad8\u5bc6\u5ea6\u5efa\u8bae\u81f3\u5c11 2 \u53f0\uff0c\u5f53\u524d %s \u53f0\u6b7b\u89d2\u6613\u7f3a\u6c27' % acount)

    # \u51cc\u6668\u8986\u76d6
    if '\u51cc\u6668' not in windows:
        add('\u5f85\u786e\u8ba4', '\u51cc\u6668\u65f6\u6bb5', '\u672a\u8986\u76d6\u51cc\u6668\u4f4e\u6c27\u65f6\u6bb5\uff0c\u8fd9\u662f\u6700\u6613\u7f3a\u6c27\u7684\u7a97\u53e3')

    # \u6446\u653e
    if placement is not True:
        add('\u5f85\u786e\u8ba4', '\u6446\u653e\u8986\u76d6', '\u589e\u6c27\u673a\u6446\u653e\u672a\u8986\u76d6\u6b7b\u89d2\uff0c\u5b58\u5728\u9759\u6c34\u7f3a\u6c27\u533a')

    # \u5e94\u6025
    if emergency is not True:
        add('\u5f85\u786e\u8ba4', '\u5e94\u6025\u51c6\u5907', '\u65e0\u5907\u7528\u7535\u6e90/\u5907\u6c34\uff0c\u534a\u591c\u8df3\u95f8\u5c06\u5168\u5858\u7f3a\u6c27')

    # \u5b8c\u6574\u6027
    if not isinstance(area, (int, float)) or area <= 0:
        add('\u5f85\u786e\u8ba4', '\u5858\u9762\u79ef', '\u672a\u63d0\u4f9b\u6709\u6548\u5858\u9762\u79ef\uff0c\u53f0\u6570\u65e0\u6cd5\u7ec6\u5316')
    if density not in DENSITY_LEVELS:
        add('\u5f85\u786e\u8ba4', '\u653e\u517b\u5bc6\u5ea6', '\u672a\u63d0\u4f9b\u653e\u517b\u5bc6\u5ea6\uff08\u9ad8/\u4e2d/\u4f4e\uff09')

    real = [f for f in findings if f['level'] == '\u5148\u5904\u7406']
    if real:
        overall = '\u5148\u5904\u7406'
    elif any(f['level'] == '\u5f85\u786e\u8ba4' for f in findings):
        overall = '\u5f85\u786e\u8ba4'
    else:
        overall = '\u53ef\u7167\u6b64\u6267\u884c'
    return {'overall': overall, 'findings': findings}


def render(result):
    lines = ['\u7ed3\u8bba\uff1a%s' % result['overall'], '']
    if not result['findings']:
        lines.append('\u672a\u53d1\u73b0\u95ee\u9898\uff0c\u53ef\u7167\u6b64\u6267\u884c\u3002')
    for f in result['findings']:
        lines.append('[%s] %s\uff1a%s' % (f['level'], f['item'], f['why']))
    return '\n'.join(lines) + '\n'


def selftest():
    passed = 0
    failed = 0

    good = {
        'pond_area_m2': 200, 'density_level': '\u4e2d', 'do_value_mg': 5,
        'symptoms': [], 'aerator_type': '\u53f6\u8f6e\u5f0f', 'aerator_count': 2,
        'run_windows': ['\u51cc\u6668', '\u9ad8\u6e29\u5348\u540e', '\u6295\u5582\u540e'], 'placement_ok': True,
        'emergency_ready': True,
    }
    r = validate(good)
    assert r['overall'] == '\u53ef\u7167\u6b64\u6267\u884c', '\u826f\u597d\u65b9\u6848\u5e94\u5224\u53ef\u7167\u6b64\u6267\u884c\uff0c\u5b9e\u9645=%s' % r['overall']
    passed += 1

    # \u53cd\u4f8b1\uff1a\u6eb6\u6c27\u8fc7\u4f4e
    bad = dict(good); bad['do_value_mg'] = 1.5
    r = validate(bad)
    assert any(f['item'] == '\u6eb6\u6c27\u8fc7\u4f4e' for f in r['findings']), '\u6eb6\u6c27\u8fc7\u4f4e\u5e94\u5224\u5148\u5904\u7406'
    assert r['overall'] == '\u5148\u5904\u7406', '\u53cd\u4f8b\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b2\uff1a\u7f3a\u6c27\u4fe1\u53f7
    bad = dict(good); bad['symptoms'] = ['\u6e05\u6668\u9c7c\u6d6e\u5934']
    r = validate(bad)
    assert any(f['item'] == '\u7f3a\u6c27\u4fe1\u53f7' for f in r['findings']), '\u7f3a\u6c27\u4fe1\u53f7\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b3\uff1a\u7c7b\u578b\u975e\u6cd5
    bad = dict(good); bad['aerator_type'] = '\u4e0d\u660e\u673a\u578b'
    r = validate(bad)
    assert any(f['item'] == '\u589e\u6c27\u673a\u7c7b\u578b' for f in r['findings']), '\u7c7b\u578b\u975e\u6cd5\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b4\uff1a\u65e0\u589e\u6c27\u673a
    bad = dict(good); bad['aerator_count'] = 0
    r = validate(bad)
    assert any(f['item'] == '\u589e\u6c27\u673a\u914d\u7f6e' for f in r['findings']), '\u65e0\u589e\u6c27\u673a\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b5\uff1a\u672a\u8986\u76d6\u51cc\u6668 \u2192 \u5f85\u786e\u8ba4
    bad = dict(good); bad['run_windows'] = ['\u9ad8\u6e29\u5348\u540e', '\u6295\u5582\u540e']
    r = validate(bad)
    assert any(f['item'] == '\u51cc\u6668\u65f6\u6bb5' for f in r['findings']), '\u672a\u8986\u76d6\u51cc\u6668\u5e94\u5224\u5f85\u786e\u8ba4'
    passed += 1

    # \u53cd\u4f8b6\uff1a\u9ad8\u5bc6\u5ea6\u4ec51\u53f0 \u2192 \u5f85\u786e\u8ba4
    bad = dict(good); bad['density_level'] = '\u9ad8'; bad['aerator_count'] = 1
    r = validate(bad)
    assert any(f['item'] == '\u9ad8\u5bc6\u5ea6\u53f0\u6570' for f in r['findings']), '\u9ad8\u5bc6\u5ea61\u53f0\u5e94\u5224\u5f85\u786e\u8ba4'
    passed += 1

    # \u53cd\u4f8b7\uff1a\u65e0\u5e94\u6025 \u2192 \u5f85\u786e\u8ba4
    bad = dict(good); bad['emergency_ready'] = False
    r = validate(bad)
    assert any(f['item'] == '\u5e94\u6025\u51c6\u5907' for f in r['findings']), '\u65e0\u5e94\u6025\u5e94\u5224\u5f85\u786e\u8ba4'
    passed += 1

    # \u53cd\u4f8b\u62a4\u680f\uff1a\u6eb6\u6c27\u8fc7\u4f4e\u53cd\u4f8b\u4e0d\u5f97\u5224\u53ef\u7167\u6b64\u6267\u884c
    bad = dict(good); bad['do_value_mg'] = 2.0
    r = validate(bad)
    assert r['overall'] != '\u53ef\u7167\u6b64\u6267\u884c', '\u6eb6\u6c27\u8fc7\u4f4e\u53cd\u4f8b\u4e0d\u5f97\u5224\u53ef\u7167\u6b64\u6267\u884c'
    passed += 1

    # BOM \u5904\u7406
    bom_json = ('\ufeff' + json.dumps(good, ensure_ascii=False)).encode('utf-8')
    text = bom_json.decode('utf-8-sig')
    assert '\ufeff' not in text, 'BOM \u672a\u88ab\u5265\u9664'
    data = json.loads(text)
    assert data['aerator_type'] == '\u53f6\u8f6e\u5f0f', 'BOM \u89e3\u6790\u540e\u5b57\u6bb5\u9519\u4f4d'
    r = validate(data)
    assert r['overall'] == '\u53ef\u7167\u6b64\u6267\u884c', 'BOM \u8f93\u5165\u7ecf\u89e3\u6790\u540e\u6821\u9a8c\u5e94\u6b63\u5e38\u901a\u8fc7'
    passed += 1

    msg = 'SELFTEST OK (%d passed, %d failed)' % (passed, failed)
    return msg, passed, failed


def main():
    ap = argparse.ArgumentParser(description='\u9c7c\u5858\u589e\u6c27\u65b9\u6848\u6821\u9a8c')
    ap.add_argument('--file', help='\u8f93\u5165 JSON \u914d\u7f6e\u6587\u4ef6\u8def\u5f84')
    ap.add_argument('--selftest', action='store_true', help='\u8fd0\u884c\u5185\u7f6e\u81ea\u68c0')
    args = ap.parse_args()

    if args.selftest:
        msg, passed, failed = selftest()
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, '_selftest_result.txt'), 'w', encoding='utf-8', newline='\n') as f:
            f.write(msg + '\n')
        print(msg)
        sys.exit(1 if failed else 0)

    if args.file:
        data = load_plan(args.file)
        result = validate(data)
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, '_last_result.txt'), 'w', encoding='utf-8', newline='\n') as f:
            f.write(render(result))
        print(render(result))
        sys.exit(0)

    print('\u7528\u6cd5: python pond_aeration_plan.py --selftest | --file pond.json')
    sys.exit(2)


if __name__ == '__main__':
    main()
