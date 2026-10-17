# -*- coding: utf-8 -*-
"""\u6708\u5b63\u4fee\u526a\u65b9\u6848\u6821\u9a8c\u811a\u672c\u3002

\u7528\u6cd5:
  python rose_prune_plan.py --selftest
  python rose_prune_plan.py --file rose.json

\u8f93\u5165\u4e3a JSON\uff0c\u5b57\u6bb5\u89c1 SKILL.md \u7b2c\u4e94\u7ae0\u3002\u8bfb\u53d6\u7edf\u4e00\u7528 utf-8-sig \u5265 BOM\u3002
"""
import argparse
import json
import os
import sys

PLANT_TYPES = ['\u704c\u6728\u6708\u5b63', '\u5fae\u578b\u6708\u5b63', '\u85e4\u672c\u6708\u5b63', '\u8001\u6869\u6708\u5b63']
CORRECT_ORDER = ['\u6e05\u75c5\u679d\u67af\u679d', '\u758f\u5220\u8fc7\u5bc6\u679d', '\u77ed\u622a\u58ee\u679d', '\u62b9\u7827\u6728\u82bd', '\u4f24\u53e3\u5904\u7406']


def load_plan(path):
    raw = open(path, 'rb').read()
    text = raw.decode('utf-8-sig')
    return json.loads(text)


def validate(data):
    findings = []

    def add(level, item, why):
        findings.append({'level': level, 'item': item, 'why': why})

    ptype = data.get('plant_type')
    ptime = data.get('pruning_time')
    strength = data.get('prune_strength')
    sanitized = data.get('tool_sanitized')
    angle = data.get('cut_angle')
    bud = data.get('bud_direction')
    has_disease = data.get('has_disease')
    dispose = data.get('dispose_diseased')
    steps = data.get('steps') or []

    if ptype not in PLANT_TYPES:
        add('\u5148\u5904\u7406', '\u54c1\u79cd\u8bc6\u522b', 'plant_type \u4e0d\u662f\u5df2\u77e5\u54c1\u79cd\uff0c\u65e0\u6cd5\u6821\u9a8c\u5f3a\u5ea6')
        valid = False
    else:
        valid = True

    # \u5f3a\u5ea6\u9519\u914d\uff08\u85e4\u672c\u51ac\u5b63\u91cd\u526a\u3001\u5fae\u578b\u91cd\u526a\uff09
    if valid and ptime == '\u51ac\u5b63\u4f11\u7720\u671f' and strength == '\u91cd\u526a':
        if ptype == '\u85e4\u672c\u6708\u5b63':
            add('\u5148\u5904\u7406', '\u4fee\u526a\u5f3a\u5ea6', '\u85e4\u672c\u6708\u5b63\u51ac\u5b63\u91cd\u526a\u4f1a\u526a\u6389\u82b1\u82bd\uff0c\u5e94\u8f7b\u526a\u53ea\u758f\u8001\u679d')
        elif ptype == '\u5fae\u578b\u6708\u5b63':
            add('\u5148\u5904\u7406', '\u4fee\u526a\u5f3a\u5ea6', '\u5fae\u578b\u6708\u5b63\u682a\u5c0f\uff0c\u91cd\u526a\u6613\u4f24\uff0c\u5e94\u8f7b\u526a')

    # \u5de5\u5177\u6d88\u6bd2
    if sanitized is not True:
        add('\u5148\u5904\u7406', '\u5de5\u5177\u6d88\u6bd2', '\u5de5\u5177\u672a\u6d88\u6bd2\uff0c\u526a\u75c5\u679d\u6613\u4f20\u64ad\u75c5\u5bb3')

    # \u526a\u53e3\u89d2\u5ea6
    if isinstance(angle, (int, float)):
        if angle < 30 or angle > 60:
            add('\u5148\u5904\u7406', '\u526a\u53e3\u89d2\u5ea6', '\u526a\u53e3\u89d2\u5ea6 %s \u5ea6\u4e0d\u5728 30-60 \u5ea6\u533a\u95f4\uff08\u5e38\u7528 45\uff09' % angle)
    else:
        add('\u5f85\u786e\u8ba4', '\u526a\u53e3\u89d2\u5ea6', '\u672a\u63d0\u4f9b\u526a\u53e3\u89d2\u5ea6')

    # \u7559\u82bd\u65b9\u5411
    if bud == '\u5185\u82bd':
        add('\u5148\u5904\u7406', '\u7559\u82bd\u65b9\u5411', '\u526a\u53e3\u7559\u5185\u82bd\u4f1a\u4f7f\u65b0\u679d\u5411\u5185\u4ea4\u53c9\uff0c\u5e94\u7559\u5916\u82bd')
    elif bud not in ('\u5916\u82bd',):
        add('\u5f85\u786e\u8ba4', '\u7559\u82bd\u65b9\u5411', '\u672a\u660e\u786e\u7559\u5916\u82bd')

    # \u75c5\u679d\u5904\u7f6e
    if has_disease is True and dispose is not True:
        add('\u5148\u5904\u7406', '\u75c5\u679d\u5904\u7f6e', '\u6709\u75c5\u679d\u4f46\u672a\u9500\u6bc1\uff0c\u4e0d\u5f97\u8fdb\u5806\u80a5')

    # \u64cd\u4f5c\u987a\u5e8f\uff08\u6309\u8f93\u5165\u539f\u5e8f\u53d6\u7d22\u5f15\uff0c\u4e0d\u91cd\u65b0\u6392\u5e8f\uff09
    norm_steps = [s for s in steps if s in CORRECT_ORDER]
    idx = [CORRECT_ORDER.index(s) for s in norm_steps]
    if idx != sorted(idx):
        add('\u5148\u5904\u7406', '\u64cd\u4f5c\u987a\u5e8f', '\u64cd\u4f5c\u987a\u5e8f\u9519\u8bef\uff1a\u5e94\u5148\u6e05\u75c5\u679d\u67af\u679d\u518d\u6574\u5f62\u77ed\u622a')

    # \u5b8c\u6574\u6027
    if ptime is None:
        add('\u5f85\u786e\u8ba4', '\u4fee\u526a\u65f6\u673a', '\u672a\u63d0\u4f9b\u4fee\u526a\u65f6\u673a')

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
        'plant_type': '\u704c\u6728\u6708\u5b63', 'pruning_time': '\u51ac\u5b63\u4f11\u7720\u671f', 'prune_strength': '\u4e2d\u526a',
        'tool_sanitized': True, 'cut_angle': 45, 'bud_direction': '\u5916\u82bd',
        'has_disease': False, 'dispose_diseased': True,
        'steps': ['\u6e05\u75c5\u679d\u67af\u679d', '\u758f\u5220\u8fc7\u5bc6\u679d', '\u77ed\u622a\u58ee\u679d', '\u62b9\u7827\u6728\u82bd', '\u4f24\u53e3\u5904\u7406'],
    }
    r = validate(good)
    assert r['overall'] == '\u53ef\u7167\u6b64\u6267\u884c', '\u826f\u597d\u65b9\u6848\u5e94\u5224\u53ef\u7167\u6b64\u6267\u884c\uff0c\u5b9e\u9645=%s' % r['overall']
    passed += 1

    # \u53cd\u4f8b1\uff1a\u85e4\u672c\u51ac\u5b63\u91cd\u526a
    bad = dict(good); bad['plant_type'] = '\u85e4\u672c\u6708\u5b63'; bad['prune_strength'] = '\u91cd\u526a'
    r = validate(bad)
    assert any(f['item'] == '\u4fee\u526a\u5f3a\u5ea6' for f in r['findings']), '\u85e4\u672c\u91cd\u526a\u5e94\u5224\u5148\u5904\u7406'
    assert r['overall'] == '\u5148\u5904\u7406', '\u53cd\u4f8b\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b2\uff1a\u672a\u6d88\u6bd2
    bad = dict(good); bad['tool_sanitized'] = False
    r = validate(bad)
    assert any(f['item'] == '\u5de5\u5177\u6d88\u6bd2' for f in r['findings']), '\u672a\u6d88\u6bd2\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b3\uff1a\u89d2\u5ea6\u9519
    bad = dict(good); bad['cut_angle'] = 90
    r = validate(bad)
    assert any(f['item'] == '\u526a\u53e3\u89d2\u5ea6' for f in r['findings']), '\u526a\u53e3\u89d2\u5ea6\u9519\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b4\uff1a\u7559\u5185\u82bd
    bad = dict(good); bad['bud_direction'] = '\u5185\u82bd'
    r = validate(bad)
    assert any(f['item'] == '\u7559\u82bd\u65b9\u5411' for f in r['findings']), '\u7559\u5185\u82bd\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b5\uff1a\u987a\u5e8f\u9519\uff08\u5148\u77ed\u622a\u518d\u6e05\u75c5\u679d\uff09
    bad = dict(good); bad['steps'] = ['\u77ed\u622a\u58ee\u679d', '\u6e05\u75c5\u679d\u67af\u679d', '\u758f\u5220\u8fc7\u5bc6\u679d']
    r = validate(bad)
    assert any(f['item'] == '\u64cd\u4f5c\u987a\u5e8f' for f in r['findings']), '\u64cd\u4f5c\u987a\u5e8f\u9519\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b6\uff1a\u75c5\u679d\u672a\u9500\u6bc1
    bad = dict(good); bad['has_disease'] = True; bad['dispose_diseased'] = False
    r = validate(bad)
    assert any(f['item'] == '\u75c5\u679d\u5904\u7f6e' for f in r['findings']), '\u75c5\u679d\u672a\u9500\u6bc1\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b7\uff1a\u5fae\u578b\u91cd\u526a
    bad = dict(good); bad['plant_type'] = '\u5fae\u578b\u6708\u5b63'; bad['prune_strength'] = '\u91cd\u526a'
    r = validate(bad)
    assert any(f['item'] == '\u4fee\u526a\u5f3a\u5ea6' for f in r['findings']), '\u5fae\u578b\u91cd\u526a\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b\u62a4\u680f\uff1a\u672a\u6d88\u6bd2\u7684\u53cd\u4f8b\u4e0d\u5f97\u5224\u53ef\u7167\u6b64\u6267\u884c
    bad = dict(good); bad['tool_sanitized'] = False
    r = validate(bad)
    assert r['overall'] != '\u53ef\u7167\u6b64\u6267\u884c', '\u672a\u6d88\u6bd2\u7684\u53cd\u4f8b\u4e0d\u5f97\u5224\u53ef\u7167\u6b64\u6267\u884c'
    passed += 1

    # BOM \u5904\u7406
    bom_json = ('\ufeff' + json.dumps(good, ensure_ascii=False)).encode('utf-8')
    text = bom_json.decode('utf-8-sig')
    assert '\ufeff' not in text, 'BOM \u672a\u88ab\u5265\u9664'
    data = json.loads(text)
    assert data['cut_angle'] == 45, 'BOM \u89e3\u6790\u540e\u5b57\u6bb5\u9519\u4f4d'
    r = validate(data)
    assert r['overall'] == '\u53ef\u7167\u6b64\u6267\u884c', 'BOM \u8f93\u5165\u7ecf\u89e3\u6790\u540e\u6821\u9a8c\u5e94\u6b63\u5e38\u901a\u8fc7'
    passed += 1

    msg = 'SELFTEST OK (%d passed, %d failed)' % (passed, failed)
    return msg, passed, failed


def main():
    ap = argparse.ArgumentParser(description='\u6708\u5b63\u4fee\u526a\u65b9\u6848\u6821\u9a8c')
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

    print('\u7528\u6cd5: python rose_prune_plan.py --selftest | --file rose.json')
    sys.exit(2)


if __name__ == '__main__':
    main()
