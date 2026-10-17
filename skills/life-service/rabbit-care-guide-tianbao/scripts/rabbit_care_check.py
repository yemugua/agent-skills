# -*- coding: utf-8 -*-
"""\u5154\u5b50\u9972\u517b\u914d\u7f6e\u6821\u9a8c\u811a\u672c\u3002

\u7528\u6cd5:
  python rabbit_care_check.py --selftest
  python rabbit_care_check.py --file rabbit.json

\u8f93\u5165\u4e3a JSON\uff0c\u5b57\u6bb5\u89c1 SKILL.md \u7b2c\u4e94\u7ae0\u3002\u8bfb\u53d6\u7edf\u4e00\u7528 utf-8-sig \u5265 BOM\u3002
"""
import argparse
import json
import os
import sys

BANNED_VEG = ['\u8471', '\u849c', '\u97ed\u83dc', '\u6d0b\u8471', '\u9a6c\u94c3\u85af', '\u571f\u8c46', '\u5de7\u514b\u529b', '\u725b\u5976', '\u9762\u5305', '\u997c\u5e72', '\u7cd6\u679c']
VET_SYMPTOM = ['\u4e0d\u98df', '\u6d41\u6d8e', '\u8f6f\u4fbf', '\u4fbf\u8840', '\u8179\u80c0', '\u762b\u8f6f', '\u62bd\u6410', '\u547c\u5438', '\u55b7\u568f', '\u4fbf\u8840']


def load_plan(path):
    raw = open(path, 'rb').read()
    text = raw.decode('utf-8-sig')
    return json.loads(text)


def validate(data):
    findings = []

    def add(level, item, why):
        findings.append({'level': level, 'item': item, 'why': why})

    clen = data.get('cage_length_cm')
    cwid = data.get('cage_width_cm')
    litter = data.get('litter_trained')
    hay_pct = data.get('hay_pct')
    pellet = data.get('pellet_g_per_kg')
    water = data.get('water_available')
    veg = data.get('veg_items') or []
    chew = data.get('chew_toys')
    weight = data.get('weight_kg')
    symptoms = data.get('symptoms') or []

    # \u7b3c\u5177\u7a7a\u95f4
    if isinstance(clen, (int, float)) and isinstance(cwid, (int, float)) and clen > 0 and cwid > 0:
        area = clen * cwid
        min_area = 5400
        if weight is not None and isinstance(weight, (int, float)):
            if weight > 3:
                min_area = 7500
            elif weight < 1.5:
                min_area = 3600
        if area < min_area:
            add('\u5148\u5904\u7406', '\u7b3c\u5177\u7a7a\u95f4', '\u7b3c\u5e95\u9762\u79ef %d cm\u00b2 \u4f4e\u4e8e\u8be5\u4f53\u91cd\u6700\u5c0f\u8981\u6c42 %d cm\u00b2' % (area, min_area))
    else:
        add('\u5f85\u786e\u8ba4', '\u7b3c\u5177\u7a7a\u95f4', '\u672a\u63d0\u4f9b\u6709\u6548\u7b3c\u957f\u7b3c\u5bbd\uff0c\u65e0\u6cd5\u6362\u7b97\u5e95\u9762\u79ef')

    # \u5b9a\u70b9\u6392\u4fbf\u8bad\u7ec3
    if litter is not True:
        add('\u5f85\u786e\u8ba4', '\u5b9a\u70b9\u6392\u4fbf', '\u672a\u505a\u5b9a\u70b9\u6392\u4fbf\u8bad\u7ec3\uff0c\u7b3c\u5185\u6613\u810f\u4e14\u5f02\u5473\u91cd')

    # \u7267\u8349\u5360\u6bd4
    if isinstance(hay_pct, (int, float)):
        if hay_pct < 60:
            add('\u5148\u5904\u7406', '\u7267\u8349\u5360\u6bd4', '\u7267\u8349\u5360\u65e5\u7cae %s%% \u4f4e\u4e8e 60%%\uff0c\u5e94\u4ee5\u7267\u8349\u4e3a\u4e3b\u98df' % hay_pct)
        elif hay_pct > 100:
            add('\u5148\u5904\u7406', '\u7267\u8349\u5360\u6bd4', '\u7267\u8349\u5360\u6bd4 %s%% \u8d85\u8fc7 100%%\uff0c\u53d6\u503c\u9519\u8bef' % hay_pct)
    else:
        add('\u5f85\u786e\u8ba4', '\u7267\u8349\u5360\u6bd4', '\u672a\u63d0\u4f9b\u7267\u8349\u5360\u6bd4')

    # \u996e\u6c34
    if water is not True:
        add('\u5148\u5904\u7406', '\u5e38\u5907\u996e\u6c34', '\u672a\u63d0\u4f9b\u5e38\u5907\u6e05\u6d01\u996e\u6c34\uff0c\u5154\u5b50\u5fc5\u987b\u968f\u65f6\u80fd\u559d\u5230\u6c34')

    # \u9897\u7c92\u7cae\u63a7\u91cf
    if isinstance(pellet, (int, float)):
        if pellet > 50:
            add('\u5148\u5904\u7406', '\u9897\u7c92\u7cae', '\u9897\u7c92\u7cae %s \u514b/\u516c\u65a4/\u5929\u8d85\u8fc7 50\uff0c\u6613\u80a5\u80d6\u4e0e\u80a0\u9053\u8d1f\u62c5' % pellet)
        elif pellet < 10:
            add('\u5f85\u786e\u8ba4', '\u9897\u7c92\u7cae', '\u9897\u7c92\u7cae %s \u514b/\u516c\u65a4/\u5929\u504f\u5c11\uff0c\u786e\u8ba4\u7267\u8349\u662f\u5426\u5145\u8db3' % pellet)

    # \u7981\u5fcc\u852c\u83dc\uff08\u7528 any \u5339\u914d\uff0c\u4e0d\u80fd\u7528 in BANNED_VEG\uff09
    for v in veg:
        if any(b in v for b in BANNED_VEG):
            add('\u5148\u5904\u7406', '\u7981\u5fcc\u98df\u7269', '\u852c\u83dc\u542b\u7981\u5fcc\u9879\uff1a%s' % v)

    # \u78e8\u7259\u7269
    if chew is not True:
        add('\u5f85\u786e\u8ba4', '\u78e8\u7259\u7269', '\u672a\u914d\u78e8\u7259\u7269\uff0c\u957f\u671f\u7f3a\u78e8\u7259\u7259\u9f7f\u6613\u8fc7\u957f')

    # \u4f53\u91cd
    if not isinstance(weight, (int, float)) or weight <= 0:
        add('\u5f85\u786e\u8ba4', '\u4f53\u91cd', '\u672a\u63d0\u4f9b\u6709\u6548\u4f53\u91cd\uff0c\u7a7a\u95f4\u4e0e\u9897\u7c92\u7cae\u65e0\u6cd5\u6362\u7b97')

    # \u5c31\u533b\u75c7\u72b6\uff08\u7528 any \u5339\u914d\uff09
    for s in symptoms:
        if any(v in s for v in VET_SYMPTOM):
            add('\u5148\u5904\u7406', '\u5c31\u533b\u75c7\u72b6', '\u89c2\u5bdf\u5230\u9700\u5c31\u533b\u75c7\u72b6\uff1a%s' % s)
            break

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
        'cage_length_cm': 100, 'cage_width_cm': 60, 'litter_trained': True,
        'hay_pct': 80, 'pellet_g_per_kg': 30, 'water_available': True,
        'veg_items': ['\u6cb9\u9ea6\u83dc', '\u80e1\u841d\u535c'], 'chew_toys': True,
        'weight_kg': 2.0, 'symptoms': [],
    }
    r = validate(good)
    assert r['overall'] == '\u53ef\u7167\u6b64\u6267\u884c', '\u826f\u597d\u914d\u7f6e\u5e94\u5224\u53ef\u7167\u6b64\u6267\u884c\uff0c\u5b9e\u9645=%s' % r['overall']
    passed += 1

    # \u53cd\u4f8b1\uff1a\u7b3c\u592a\u5c0f
    bad = dict(good); bad['cage_length_cm'] = 50; bad['cage_width_cm'] = 40
    r = validate(bad)
    assert any(f['item'] == '\u7b3c\u5177\u7a7a\u95f4' for f in r['findings']), '\u7b3c\u592a\u5c0f\u5e94\u5224\u5148\u5904\u7406'
    assert r['overall'] == '\u5148\u5904\u7406', '\u53cd\u4f8b\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b2\uff1a\u7267\u8349\u8fc7\u4f4e
    bad = dict(good); bad['hay_pct'] = 30
    r = validate(bad)
    assert any(f['item'] == '\u7267\u8349\u5360\u6bd4' for f in r['findings']), '\u7267\u8349\u8fc7\u4f4e\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b3\uff1a\u65e0\u996e\u6c34
    bad = dict(good); bad['water_available'] = False
    r = validate(bad)
    assert any(f['item'] == '\u5e38\u5907\u996e\u6c34' for f in r['findings']), '\u65e0\u996e\u6c34\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b4\uff1a\u7981\u5fcc\u852c\u83dc
    bad = dict(good); bad['veg_items'] = ['\u6cb9\u9ea6\u83dc', '\u6d0b\u8471']
    r = validate(bad)
    assert any(f['item'] == '\u7981\u5fcc\u98df\u7269' for f in r['findings']), '\u7981\u5fcc\u852c\u83dc\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b5\uff1a\u9897\u7c92\u7cae\u8fc7\u91cf
    bad = dict(good); bad['pellet_g_per_kg'] = 80
    r = validate(bad)
    assert any(f['item'] == '\u9897\u7c92\u7cae' for f in r['findings']), '\u9897\u7c92\u7cae\u8fc7\u91cf\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b6\uff1a\u5c31\u533b\u75c7\u72b6
    bad = dict(good); bad['symptoms'] = ['\u4eca\u5929\u4e0d\u98df\u8d85\u8fc7\u534a\u5929']
    r = validate(bad)
    assert any(f['item'] == '\u5c31\u533b\u75c7\u72b6' for f in r['findings']), '\u5c31\u533b\u75c7\u72b6\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b\u62a4\u680f\uff1a\u542b\u7981\u5fcc\u98df\u7269\u7684\u53cd\u4f8b\u4e0d\u5f97\u5224\u53ef\u7167\u6b64\u6267\u884c
    bad = dict(good); bad['veg_items'] = ['\u80e1\u841d\u535c', '\u5de7\u514b\u529b']
    r = validate(bad)
    assert r['overall'] != '\u53ef\u7167\u6b64\u6267\u884c', '\u542b\u7981\u5fcc\u98df\u7269\u7684\u53cd\u4f8b\u4e0d\u5f97\u5224\u53ef\u7167\u6b64\u6267\u884c'
    passed += 1

    # BOM \u5904\u7406\uff1a\u5e26 BOM \u7684 JSON \u5fc5\u987b\u80fd\u6b63\u786e\u89e3\u6790
    bom_json = ('\ufeff' + json.dumps(good, ensure_ascii=False)).encode('utf-8')
    text = bom_json.decode('utf-8-sig')
    assert '\ufeff' not in text, 'BOM \u672a\u88ab\u5265\u9664'
    data = json.loads(text)
    assert data['hay_pct'] == 80, 'BOM \u89e3\u6790\u540e\u5b57\u6bb5\u9519\u4f4d'
    r = validate(data)
    assert r['overall'] == '\u53ef\u7167\u6b64\u6267\u884c', 'BOM \u8f93\u5165\u7ecf\u89e3\u6790\u540e\u6821\u9a8c\u5e94\u6b63\u5e38\u901a\u8fc7'
    passed += 1

    msg = 'SELFTEST OK (%d passed, %d failed)' % (passed, failed)
    return msg, passed, failed


def main():
    ap = argparse.ArgumentParser(description='\u5154\u5b50\u9972\u517b\u914d\u7f6e\u6821\u9a8c')
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

    print('\u7528\u6cd5: python rabbit_care_check.py --selftest | --file rabbit.json')
    sys.exit(2)


if __name__ == '__main__':
    main()
