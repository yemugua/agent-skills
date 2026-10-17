# -*- coding: utf-8 -*-
"""\u4e4c\u9f9f\u9972\u517b\u914d\u7f6e\u6821\u9a8c\u811a\u672c\u3002

\u7528\u6cd5:
  python turtle_care_check.py --selftest
  python turtle_care_check.py --file plan.json

\u8f93\u5165\u4e3a JSON\uff0c\u5b57\u6bb5\u89c1 SKILL.md \u7b2c\u4e94\u7ae0\u3002\u8bfb\u53d6\u65f6\u7edf\u4e00\u7528 utf-8-sig \u5265 BOM\uff0c
\u907f\u514d PowerShell \u5199\u51fa\u5e26 BOM \u7684\u6587\u4ef6\u5bfc\u81f4\u9996 key \u53d8\u6210 \ufeffspecies_type \u800c\u53d6\u4e0d\u5230\u503c\u3002
"""
import argparse
import json
import os
import sys

VALID_SPECIES = ['\u6c34\u9f9f', '\u534a\u6c34\u9f9f', '\u9646\u9f9f']
BANNED_FOOD = ['\u706b\u817f\u80a0', '\u54b8\u5473', '\u9762\u5305\u5c51', '\u5de7\u514b\u529b', '\u6d0b\u8471', '\u5927\u849c', '\u5927\u8471', '\u4e73\u5236\u54c1', '\u751f\u732a\u8089', '\u725b\u5976']
CORRECT_ORDER = ['\u5148\u5b9a\u79cd\u7c7b', '\u6d4b\u80cc\u7532\u957f\u5ea6', '\u914d\u6c34\u4f53\u4e0e\u6652\u53f0', '\u914d\u6e29\u63a7\u4e0e\u5149\u7167',
                 '\u5b9a\u5582\u517b\u65b9\u6848', '\u6392\u6362\u6c34\u4e0e\u6e05\u7406', '\u5224\u51ac\u7720\u5fc5\u8981\u6027']


def load_plan(path):
    raw = open(path, 'rb').read()
    text = raw.decode('utf-8-sig')
    return json.loads(text)


def validate(data):
    findings = []

    def add(level, item, why):
        findings.append({'level': level, 'item': item, 'why': why})

    species = data.get('species_type')
    carapace = data.get('carapace_cm')
    water_depth = data.get('water_depth_cm')
    basking = data.get('basking_exists')
    basking_temp = data.get('basking_temp_c')
    water_temp = data.get('water_temp_c')
    uvb = data.get('uvb_provided')
    uvb_age = data.get('uvb_age_months')
    feed_times = data.get('feed_times_per_week')
    foods = data.get('food_items') or []
    hibernate = data.get('hibernate')
    hib_temp = data.get('hibernate_temp_c')
    weight_checked = data.get('weight_checked')
    steps = data.get('steps') or []

    valid = species in VALID_SPECIES
    if not valid:
        add('\u5148\u5904\u7406', '\u79cd\u7c7b\u8bc6\u522b', 'species_type \u4e0d\u662f\u6c34\u9f9f/\u534a\u6c34\u9f9f/\u9646\u9f9f\uff0c\u65e0\u6cd5\u6821\u9a8c\u914d\u7f6e')

    # \u786c\u9700\u6c42\uff1a\u5b8c\u5168\u79bb\u6c34\u7684\u6652\u53f0/\u5e72\u71e5\u6652\u80cc\u533a
    if basking is not True:
        add('\u5148\u5904\u7406', '\u6652\u53f0', '\u7f3a\u5c11\u5b8c\u5168\u79bb\u6c34\u7684\u6652\u53f0/\u5e72\u71e5\u6652\u80cc\u533a\uff0c\u9f9f\u65e0\u6cd5\u79bb\u6c34\u6652\u80cc')
    # \u786c\u9700\u6c42\uff1aUVB \u5149\u6e90\u4e0e\u66f4\u6362\u5468\u671f
    if uvb is not True:
        add('\u5148\u5904\u7406', 'UVB', '\u672a\u914d\u5907 UVB \u5149\u6e90\uff0c\u7a97\u8fb9\u76f4\u5c04\u4e0d\u80fd\u66ff\u4ee3')
    elif isinstance(uvb_age, (int, float)) and uvb_age > 12:
        add('\u5148\u5904\u7406', 'UVB', 'UVB \u706f\u5177\u5df2\u7528 %s \u4e2a\u6708\uff0c\u8d85\u8fc7 12 \u4e2a\u6708\u66f4\u6362\u5468\u671f' % uvb_age)

    # \u6e29\u5ea6\u533a\u95f4\uff08\u6309\u79cd\u7c7b\uff09
    if species == '\u6c34\u9f9f':
        if isinstance(water_temp, (int, float)) and (water_temp < 20 or water_temp > 32):
            add('\u5148\u5904\u7406', '\u6c34\u6e29', '\u6c34\u6e29 %s \u6444\u6c0f\u5ea6\u8d85\u51fa\u5b89\u5168\u533a\u95f4 20-32' % water_temp)
        if isinstance(basking_temp, (int, float)) and (basking_temp < 28 or basking_temp > 38):
            add('\u5148\u5904\u7406', '\u6652\u80cc\u6e29\u5ea6', '\u6652\u80cc\u533a\u6e29\u5ea6 %s \u6444\u6c0f\u5ea6\u8d85\u51fa 28-38' % basking_temp)
    elif species == '\u534a\u6c34\u9f9f':
        if isinstance(basking_temp, (int, float)) and (basking_temp < 28 or basking_temp > 38):
            add('\u5148\u5904\u7406', '\u6652\u80cc\u6e29\u5ea6', '\u6652\u80cc\u533a\u6e29\u5ea6 %s \u6444\u6c0f\u5ea6\u8d85\u51fa 28-38' % basking_temp)
    elif species == '\u9646\u9f9f':
        if isinstance(basking_temp, (int, float)) and (basking_temp < 30 or basking_temp > 40):
            add('\u5148\u5904\u7406', '\u6652\u80cc\u6e29\u5ea6', '\u6652\u80cc\u533a\u6e29\u5ea6 %s \u6444\u6c0f\u5ea6\u8d85\u51fa 30-40' % basking_temp)

    # \u6c34\u6df1\u6309\u80cc\u7532\u6362\u7b97
    if valid and isinstance(carapace, (int, float)) and isinstance(water_depth, (int, float)):
        if species == '\u9646\u9f9f':
            if water_depth > carapace * 0.5:
                add('\u5148\u5904\u7406', '\u6c34\u6df1', '\u9646\u9f9f\u6c34\u6df1 %s cm \u8fc7\u6df1\uff0c\u5e94\u4ec5\u653e\u6d45\u6c34\u76c6(<=\u80cc\u7532*0.5)' % water_depth)
        else:
            if water_depth < carapace * 1.0:
                add('\u5148\u5904\u7406', '\u6c34\u6df1', '\u6c34\u6df1 %s cm \u6d45\u4e8e\u80cc\u7532 %s cm\uff0c\u9f9f\u65e0\u6cd5\u81ea\u7531\u6f5c\u6c34\u4e0e\u7ad9\u7acb' % (water_depth, carapace))
            elif water_depth > carapace * 3.0:
                add('\u5148\u5904\u7406', '\u6c34\u6df1', '\u6c34\u6df1 %s cm \u8d85\u8fc7\u80cc\u7532 3 \u500d\uff0c\u5f31\u6cf3\u8005\u6613\u6eba\u6c34' % water_depth)
            if species == '\u534a\u6c34\u9f9f' and water_depth > carapace * 2.0:
                add('\u5148\u5904\u7406', '\u6c34\u6df1', '\u534a\u6c34\u9f9f\u6c34\u6df1 %s cm \u8fc7\u6df1\uff0c\u5e94\u6d45\u6c34+\u5927\u7247\u9646\u5730' % water_depth)
        if carapace < 5 and water_depth > carapace:
            add('\u5148\u5904\u7406', '\u9f9f\u82d7\u6d45\u6c34', '\u9f9f\u82d7\u80cc\u7532 %s cm \u6c34\u6df1 %s cm \u8d85\u80cc\u7532\uff0c\u9700\u6d45\u6c34\u533a+\u7f13\u5761' % (carapace, water_depth))

    # \u7981\u5fcc\u98df\u7269\uff08\u7528 any \u5339\u914d\uff0c\u4e0d\u80fd\u7528 in BANNED\uff09
    for f in foods:
        if any(b in f for b in BANNED_FOOD):
            add('\u5148\u5904\u7406', '\u7981\u5fcc\u98df\u7269', '\u98df\u7269\u542b\u7981\u5fcc\u9879\uff1a%s' % f)

    # \u6295\u5582\u9891\u6b21
    if isinstance(feed_times, (int, float)):
        if valid and isinstance(carapace, (int, float)) and carapace < 5:
            if feed_times < 5:
                add('\u5f85\u786e\u8ba4', '\u6295\u5582\u9891\u6b21', '\u9f9f\u82d7\u5efa\u8bae\u6bcf\u59291\u6b21(\u6bcf\u5468>=5)\uff0c\u5f53\u524d %s \u6b21/\u5468\u504f\u5c11' % feed_times)
        elif feed_times < 1 or feed_times > 7:
            add('\u5148\u5904\u7406', '\u6295\u5582\u9891\u6b21', '\u6bcf\u5468\u6295\u5582 %s \u6b21\u8d85\u51fa\u5408\u7406\u533a\u95f4 1-7' % feed_times)

    # \u4f53\u91cd\u8bb0\u5f55
    if weight_checked is not True:
        add('\u5148\u5904\u7406', '\u4f53\u91cd\u8bb0\u5f55', '\u672a\u505a\u4f53\u91cd\u8bb0\u5f55\uff0c\u65e0\u6cd5\u5224\u65ad\u5065\u5eb7\u8d8b\u52bf')

    # \u51ac\u7720\u7b5b\u67e5
    if hibernate is True:
        if not isinstance(hib_temp, (int, float)):
            add('\u5148\u5904\u7406', '\u51ac\u7720\u63a7\u6e29', '\u8ba1\u5212\u51ac\u7720\u4f46\u672a\u7ed9\u51fa\u63a7\u6e29\u6e29\u5ea6')
        elif hib_temp < 2 or hib_temp > 15:
            add('\u5148\u5904\u7406', '\u51ac\u7720\u63a7\u6e29', '\u51ac\u7720\u63a7\u6e29 %s \u6444\u6c0f\u5ea6\u8d85\u51fa\u5b89\u5168\u533a\u95f4 2-15' % hib_temp)
        if valid and isinstance(carapace, (int, float)) and carapace < 5:
            add('\u5148\u5904\u7406', '\u9f9f\u82d7\u51ac\u7720', '\u9f9f\u82d7\u80cc\u7532 %s cm \u4e0d\u5efa\u8bae\u51ac\u7720\uff0c\u5e94\u52a0\u6e29\u8fc7\u51ac' % carapace)
        if weight_checked is not True:
            add('\u5148\u5904\u7406', '\u51ac\u7720\u79f0\u91cd', '\u51ac\u7720\u671f\u95f4\u672a\u5b9a\u671f\u79f0\u91cd\uff0c\u65e0\u6cd5\u53d1\u73b0\u6389\u79e4')

    # \u64cd\u4f5c\u987a\u5e8f\uff08\u6309\u8f93\u5165\u539f\u5e8f\u53d6\u7d22\u5f15\uff0c\u4e0d\u91cd\u65b0\u6392\u5e8f\uff09
    norm_steps = [s for s in steps if s in CORRECT_ORDER]
    idx = [CORRECT_ORDER.index(s) for s in norm_steps]
    if idx != sorted(idx):
        add('\u5148\u5904\u7406', '\u64cd\u4f5c\u987a\u5e8f', '\u73af\u5883\u5e03\u7f6e\u64cd\u4f5c\u987a\u5e8f\u9519\u8bef\uff1a\u5e94\u5148\u5b9a\u79cd\u7c7b\u518d\u914d\u6c34\u4f53\u7b49\u540e\u7eed\u6b65\u9aa4')

    # \u5b8c\u6574\u6027\u63d0\u793a\uff08\u771f\u5b9e\u7f3a\u9677\u4f18\u5148\uff0c\u65e0\u7f3a\u9677\u624d\u843d\u5230\u5f85\u786e\u8ba4\uff09
    if valid and not isinstance(carapace, (int, float)):
        add('\u5f85\u786e\u8ba4', '\u80cc\u7532\u957f\u5ea6', '\u672a\u63d0\u4f9b\u80cc\u7532\u957f\u5ea6\uff0c\u6c34\u6df1\u7b49\u65e0\u6cd5\u6362\u7b97')
    if species in ('\u6c34\u9f9f', '\u534a\u6c34\u9f9f') and not isinstance(water_depth, (int, float)):
        add('\u5f85\u786e\u8ba4', '\u6c34\u6df1', '\u672a\u63d0\u4f9b\u6c34\u6df1')
    if valid and not isinstance(basking_temp, (int, float)):
        add('\u5f85\u786e\u8ba4', '\u6652\u80cc\u6e29\u5ea6', '\u672a\u63d0\u4f9b\u6652\u80cc\u533a\u6e29\u5ea6')
    if uvb is True and not isinstance(uvb_age, (int, float)):
        add('\u5f85\u786e\u8ba4', 'UVB\u5468\u671f', 'UVB \u706f\u5177\u5df2\u7528\u6708\u6570\u672a\u63d0\u4f9b')

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
        'species_type': '\u6c34\u9f9f', 'carapace_cm': 10, 'water_depth_cm': 18,
        'basking_exists': True, 'basking_temp_c': 32, 'water_temp_c': 26,
        'uvb_provided': True, 'uvb_age_months': 6, 'feed_times_per_week': 3,
        'food_items': ['\u9f9f\u7cae', '\u5c0f\u9c7c\u867e'], 'hibernate': False, 'weight_checked': True,
        'steps': ['\u5148\u5b9a\u79cd\u7c7b', '\u6d4b\u80cc\u7532\u957f\u5ea6', '\u914d\u6c34\u4f53\u4e0e\u6652\u53f0', '\u914d\u6e29\u63a7\u4e0e\u5149\u7167', '\u5b9a\u5582\u517b\u65b9\u6848'],
    }
    r = validate(good)
    assert r['overall'] == '\u53ef\u7167\u6b64\u6267\u884c', '\u826f\u597d\u914d\u7f6e\u5e94\u5224\u53ef\u7167\u6b64\u6267\u884c\uff0c\u5b9e\u9645=%s' % r['overall']
    passed += 1

    # \u53cd\u4f8b1\uff1a\u7f3a\u6652\u53f0
    bad = dict(good); bad['basking_exists'] = False
    r = validate(bad)
    assert any(f['item'] == '\u6652\u53f0' for f in r['findings']), '\u7f3a\u6652\u53f0\u5e94\u5224\u5148\u5904\u7406'
    assert r['overall'] == '\u5148\u5904\u7406', '\u53cd\u4f8b\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b2\uff1a\u7981\u5fcc\u98df\u7269
    bad = dict(good); bad['food_items'] = ['\u9f9f\u7cae', '\u706b\u817f\u80a0']
    r = validate(bad)
    assert any(f['item'] == '\u7981\u5fcc\u98df\u7269' for f in r['findings']), '\u7981\u5fcc\u98df\u7269\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b3\uff1a\u9f9f\u82d7\u51ac\u7720
    bad = dict(good); bad['carapace_cm'] = 4; bad['water_depth_cm'] = 3
    bad['hibernate'] = True; bad['hibernate_temp_c'] = 7
    r = validate(bad)
    assert any(f['item'] == '\u9f9f\u82d7\u51ac\u7720' for f in r['findings']), '\u9f9f\u82d7\u51ac\u7720\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b4\uff1a\u51ac\u7720\u63a7\u6e29\u8d8a\u754c
    bad = dict(good); bad['hibernate'] = True; bad['hibernate_temp_c'] = 20
    r = validate(bad)
    assert any(f['item'] == '\u51ac\u7720\u63a7\u6e29' for f in r['findings']), '\u51ac\u7720\u63a7\u6e29\u8d8a\u754c\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b5\uff1aUVB \u8d85\u671f
    bad = dict(good); bad['uvb_age_months'] = 18
    r = validate(bad)
    assert any(f['item'] == 'UVB' for f in r['findings']), 'UVB \u8d85\u671f\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b6\uff1a\u64cd\u4f5c\u987a\u5e8f\u9519\u8bef\uff08\u5148\u914d\u6c34\u4f53\u518d\u5b9a\u79cd\u7c7b\uff09
    bad = dict(good); bad['steps'] = ['\u914d\u6c34\u4f53\u4e0e\u6652\u53f0', '\u5148\u5b9a\u79cd\u7c7b']
    r = validate(bad)
    assert any(f['item'] == '\u64cd\u4f5c\u987a\u5e8f' for f in r['findings']), '\u64cd\u4f5c\u987a\u5e8f\u9519\u8bef\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b7\uff1a\u9646\u9f9f\u6df1\u6c34
    bad = {'species_type': '\u9646\u9f9f', 'carapace_cm': 15, 'water_depth_cm': 20,
           'basking_exists': True, 'basking_temp_c': 34, 'uvb_provided': True,
           'uvb_age_months': 5, 'feed_times_per_week': 3, 'food_items': ['\u9f9f\u7cae'],
           'hibernate': False, 'weight_checked': True,
           'steps': ['\u5148\u5b9a\u79cd\u7c7b', '\u6d4b\u80cc\u7532\u957f\u5ea6', '\u914d\u6c34\u4f53\u4e0e\u6652\u53f0', '\u914d\u6e29\u63a7\u4e0e\u5149\u7167']}
    r = validate(bad)
    assert any(f['item'] == '\u6c34\u6df1' for f in r['findings']), '\u9646\u9f9f\u6df1\u6c34\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b\u62a4\u680f\uff1a\u4efb\u4f55\u542b\u771f\u5b9e\u7f3a\u9677\u7684\u914d\u7f6e\u90fd\u4e0d\u5f97\u5224\u6210\u53ef\u7167\u6b64\u6267\u884c
    bad = dict(good); bad['food_items'] = ['\u9f9f\u7cae', '\u5de7\u514b\u529b']
    r = validate(bad)
    assert r['overall'] != '\u53ef\u7167\u6b64\u6267\u884c', '\u542b\u7981\u5fcc\u98df\u7269\u7684\u53cd\u4f8b\u4e0d\u5f97\u5224\u53ef\u7167\u6b64\u6267\u884c'
    passed += 1

    # BOM \u5904\u7406\uff1a\u5e26 BOM \u7684 JSON \u5fc5\u987b\u80fd\u6b63\u786e\u89e3\u6790
    bom_json = ('\ufeff' + json.dumps(good, ensure_ascii=False)).encode('utf-8')
    text = bom_json.decode('utf-8-sig')
    assert '\ufeff' not in text, 'BOM \u672a\u88ab\u5265\u9664'
    data = json.loads(text)
    assert data['species_type'] == '\u6c34\u9f9f', 'BOM \u89e3\u6790\u540e\u9996 key \u9519\u4f4d'
    r = validate(data)
    assert r['overall'] == '\u53ef\u7167\u6b64\u6267\u884c', 'BOM \u8f93\u5165\u7ecf\u89e3\u6790\u540e\u6821\u9a8c\u5e94\u6b63\u5e38\u901a\u8fc7'
    passed += 1

    msg = 'SELFTEST OK (%d passed, %d failed)' % (passed, failed)
    return msg, passed, failed


def main():
    ap = argparse.ArgumentParser(description='\u4e4c\u9f9f\u9972\u517b\u914d\u7f6e\u6821\u9a8c')
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

    print('\u7528\u6cd5: python turtle_care_check.py --selftest | --file plan.json')
    sys.exit(2)


if __name__ == '__main__':
    main()
