# -*- coding: utf-8 -*-
"""\u571f\u58e4\u677f\u7ed3\u6539\u826f\u65b9\u6848\u6821\u9a8c\u811a\u672c\u3002

\u7528\u6cd5:
  python soil_fix_plan.py --selftest
  python soil_fix_plan.py --file soil.json

\u8f93\u5165\u4e3a JSON\uff0c\u5b57\u6bb5\u89c1 SKILL.md \u7b2c\u4e94\u7ae0\u3002\u8bfb\u53d6\u7edf\u4e00\u7528 utf-8-sig \u5265 BOM\u3002
\u519c\u4e1a\u7c7b\u53ea\u505a\u5224\u65ad\u6d41\u7a0b\u4e0e\u8bb0\u5f55\u6838\u5bf9\uff0c\u4e0d\u5904\u7406\u519c\u836f\u6d53\u5ea6\u3002
"""
import argparse
import json
import os
import sys

AREA_TYPES = ['\u82b1\u76c6', '\u83dc\u5730', '\u5ead\u9662']
CORRECT_ORDER = ['\u505c\u8df5\u8e0f', '\u6d45\u677e\u571f', '\u589e\u65bd\u6709\u673a\u8d28', '\u8986\u76d6', '\u8f6e\u4f5c\u7eff\u80a5']
RAW_MARK = ['\u751f', '\u672a\u8150\u719f', '\u6ca1\u8150\u719f']


def load_plan(path):
    raw = open(path, 'rb').read()
    text = raw.decode('utf-8-sig')
    return json.loads(text)


def validate(data):
    findings = []

    def add(level, item, why):
        findings.append({'level': level, 'item': item, 'why': why})

    area = data.get('area_type')
    symptoms = data.get('symptoms') or []
    cause_checked = data.get('cause_checked')
    steps = data.get('steps') or []
    organic_added = data.get('organic_added')
    organic_type = data.get('organic_type')
    till = data.get('till_depth_cm')
    cover = data.get('cover_used')
    record = data.get('record_kept')

    if area not in AREA_TYPES:
        add('\u5148\u5904\u7406', '\u5730\u5757\u8bc6\u522b', 'area_type \u4e0d\u662f\u82b1\u76c6/\u83dc\u5730/\u5ead\u9662\uff0c\u65e0\u6cd5\u6821\u9a8c')
        valid = False
    else:
        valid = True

    # \u75c7\u72b6
    if not symptoms:
        add('\u5f85\u786e\u8ba4', '\u677f\u7ed3\u75c7\u72b6', '\u672a\u63cf\u8ff0\u677f\u7ed3\u75c7\u72b6\uff0c\u65e0\u6cd5\u5224\u65ad\u662f\u4e0d\u662f\u677f\u7ed3')

    # \u6210\u56e0\u6392\u67e5\uff08\u5f3a\u8c03\u5224\u65ad\u6d41\u7a0b\uff0c\u4fe1\u606f\u7f3a\u53e3\u5224\u5f85\u786e\u8ba4\uff09
    if cause_checked is not True:
        add('\u5f85\u786e\u8ba4', '\u6210\u56e0\u6392\u67e5', '\u672a\u6392\u67e5\u6210\u56e0\uff0c\u5e94\u5148\u5224\u65ad\u518d\u6539\u826f')

    # \u64cd\u4f5c\u987a\u5e8f\uff08\u6309\u8f93\u5165\u539f\u5e8f\u53d6\u7d22\u5f15\uff0c\u4e0d\u91cd\u65b0\u6392\u5e8f\uff09
    norm_steps = [s for s in steps if s in CORRECT_ORDER]
    idx = [CORRECT_ORDER.index(s) for s in norm_steps]
    if idx != sorted(idx):
        add('\u5148\u5904\u7406', '\u64cd\u4f5c\u987a\u5e8f', '\u6539\u826f\u64cd\u4f5c\u987a\u5e8f\u9519\u8bef\uff1a\u5e94\u5148\u505c\u8df5\u8e0f\u3001\u6d45\u677e\u571f\uff0c\u518d\u589e\u65bd\u6709\u673a\u8d28\u7b49')

    # \u589e\u65bd\u6709\u673a\u8d28\uff08\u6839\u672c\u63aa\u65bd\uff09
    if organic_added is not True:
        add('\u5148\u5904\u7406', '\u589e\u65bd\u6709\u673a\u8d28', '\u672a\u589e\u65bd\u8150\u719f\u6709\u673a\u8d28\uff0c\u677f\u7ed3\u96be\u6839\u672c\u6539\u5584')

    # \u751f\u80a5\u7981\u7528\uff08\u7528 any \u5339\u914d\uff0c\u4e0d\u80fd\u7528 in RAW_MARK\uff09
    if organic_type and any(m in organic_type for m in RAW_MARK):
        add('\u5148\u5904\u7406', '\u6709\u673a\u8d28\u8150\u719f', '\u4f7f\u7528\u4e86\u672a\u8150\u719f\u6709\u673a\u80a5\uff08%s\uff09\uff0c\u4f1a\u70e7\u6839\u5e76\u52a0\u91cd\u677f\u7ed3' % organic_type)

    # \u82b1\u76c6\u6df1\u7ffb
    if area == '\u82b1\u76c6' and isinstance(till, (int, float)) and till > 15:
        add('\u5148\u5904\u7406', '\u677e\u571f\u6df1\u5ea6', '\u82b1\u76c6\u677e\u571f %s cm \u8fc7\u6df1\uff0c\u5e94\u6d45\u677e\u4e0d\u4f24\u6839' % till)

    # \u8986\u76d6\uff08\u9f13\u52b1\u9879\uff0c\u7f3a\u5931\u5224\u5f85\u786e\u8ba4\uff09
    if cover is not True:
        add('\u5f85\u786e\u8ba4', '\u8986\u76d6', '\u672a\u505a\u8986\u76d6\uff0c\u8868\u571f\u6613\u518d\u6b21\u7ed3\u76ae')

    # \u8bb0\u5f55\u6838\u5bf9
    if record is not True:
        add('\u5f85\u786e\u8ba4', '\u6539\u826f\u8bb0\u5f55', '\u672a\u505a\u6539\u826f\u524d\u540e\u8bb0\u5f55\uff0c\u65e0\u6cd5\u6838\u5bf9\u6548\u679c')

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
        'area_type': '\u83dc\u5730', 'symptoms': ['\u6d47\u6c34\u4e0b\u6e17\u6162', '\u571f\u8868\u7ed3\u76ae'],
        'cause_checked': True,
        'steps': ['\u505c\u8df5\u8e0f', '\u6d45\u677e\u571f', '\u589e\u65bd\u6709\u673a\u8d28', '\u8986\u76d6', '\u8f6e\u4f5c\u7eff\u80a5'],
        'organic_added': True, 'organic_type': '\u8150\u719f\u5806\u80a5', 'till_depth_cm': 12,
        'cover_used': True, 'record_kept': True,
    }
    r = validate(good)
    assert r['overall'] == '\u53ef\u7167\u6b64\u6267\u884c', '\u826f\u597d\u65b9\u6848\u5e94\u5224\u53ef\u7167\u6b64\u6267\u884c\uff0c\u5b9e\u9645=%s' % r['overall']
    passed += 1

    # \u53cd\u4f8b1\uff1a\u82b1\u76c6\u6df1\u7ffb
    bad = dict(good); bad['area_type'] = '\u82b1\u76c6'; bad['till_depth_cm'] = 25
    r = validate(bad)
    assert any(f['item'] == '\u677e\u571f\u6df1\u5ea6' for f in r['findings']), '\u82b1\u76c6\u6df1\u7ffb\u5e94\u5224\u5148\u5904\u7406'
    assert r['overall'] == '\u5148\u5904\u7406', '\u53cd\u4f8b\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b2\uff1a\u751f\u80a5
    bad = dict(good); bad['organic_type'] = '\u751f\u9e21\u7caa'
    r = validate(bad)
    assert any(f['item'] == '\u6709\u673a\u8d28\u8150\u719f' for f in r['findings']), '\u751f\u80a5\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b3\uff1a\u987a\u5e8f\u9519\uff08\u5148\u589e\u65bd\u518d\u505c\u8df5\u8e0f\uff09
    bad = dict(good); bad['steps'] = ['\u589e\u65bd\u6709\u673a\u8d28', '\u505c\u8df5\u8e0f', '\u6d45\u677e\u571f', '\u8986\u76d6', '\u8f6e\u4f5c\u7eff\u80a5']
    r = validate(bad)
    assert any(f['item'] == '\u64cd\u4f5c\u987a\u5e8f' for f in r['findings']), '\u64cd\u4f5c\u987a\u5e8f\u9519\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b4\uff1a\u672a\u589e\u65bd\u6709\u673a\u8d28
    bad = dict(good); bad['organic_added'] = False
    r = validate(bad)
    assert any(f['item'] == '\u589e\u65bd\u6709\u673a\u8d28' for f in r['findings']), '\u672a\u589e\u65bd\u6709\u673a\u8d28\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b5\uff1a\u6210\u56e0\u672a\u6392\u67e5 \u2192 \u5f85\u786e\u8ba4
    bad = dict(good); bad['cause_checked'] = False
    r = validate(bad)
    assert any(f['item'] == '\u6210\u56e0\u6392\u67e5' for f in r['findings']), '\u672a\u6392\u67e5\u6210\u56e0\u5e94\u5224\u5f85\u786e\u8ba4'
    passed += 1

    # \u53cd\u4f8b6\uff1a\u65e0\u8bb0\u5f55 \u2192 \u5f85\u786e\u8ba4
    bad = dict(good); bad['record_kept'] = False
    r = validate(bad)
    assert any(f['item'] == '\u6539\u826f\u8bb0\u5f55' for f in r['findings']), '\u65e0\u8bb0\u5f55\u5e94\u5224\u5f85\u786e\u8ba4'
    passed += 1

    # \u53cd\u4f8b\u62a4\u680f\uff1a\u7528\u751f\u80a5\u7684\u53cd\u4f8b\u4e0d\u5f97\u5224\u53ef\u7167\u6b64\u6267\u884c
    bad = dict(good); bad['organic_type'] = '\u672a\u8150\u719f\u5806\u80a5'
    r = validate(bad)
    assert r['overall'] != '\u53ef\u7167\u6b64\u6267\u884c', '\u7528\u751f\u80a5\u7684\u53cd\u4f8b\u4e0d\u5f97\u5224\u53ef\u7167\u6b64\u6267\u884c'
    passed += 1

    # \u75c7\u72b6\u4e3a\u7a7a \u2192 \u5f85\u786e\u8ba4
    bad = dict(good); bad['symptoms'] = []
    r = validate(bad)
    assert any(f['item'] == '\u677f\u7ed3\u75c7\u72b6' for f in r['findings']), '\u65e0\u75c7\u72b6\u5e94\u5224\u5f85\u786e\u8ba4'
    passed += 1

    # BOM \u5904\u7406
    bom_json = ('\ufeff' + json.dumps(good, ensure_ascii=False)).encode('utf-8')
    text = bom_json.decode('utf-8-sig')
    assert '\ufeff' not in text, 'BOM \u672a\u88ab\u5265\u9664'
    data = json.loads(text)
    assert data['organic_added'] is True, 'BOM \u89e3\u6790\u540e\u5b57\u6bb5\u9519\u4f4d'
    r = validate(data)
    assert r['overall'] == '\u53ef\u7167\u6b64\u6267\u884c', 'BOM \u8f93\u5165\u7ecf\u89e3\u6790\u540e\u6821\u9a8c\u5e94\u6b63\u5e38\u901a\u8fc7'
    passed += 1

    msg = 'SELFTEST OK (%d passed, %d failed)' % (passed, failed)
    return msg, passed, failed


def main():
    ap = argparse.ArgumentParser(description='\u571f\u58e4\u677f\u7ed3\u6539\u826f\u65b9\u6848\u6821\u9a8c')
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

    print('\u7528\u6cd5: python soil_fix_plan.py --selftest | --file soil.json')
    sys.exit(2)


if __name__ == '__main__':
    main()
