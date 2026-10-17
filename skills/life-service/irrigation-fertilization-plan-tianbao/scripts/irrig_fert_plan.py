# -*- coding: utf-8 -*-
"""\u704c\u6e89\u65bd\u80a5\u8ba1\u5212\u6821\u9a8c\u811a\u672c\u3002

\u7528\u6cd5:
  python irrig_fert_plan.py --selftest
  python irrig_fert_plan.py --file plan.json

\u8f93\u5165\u4e3a JSON\uff0c\u5b57\u6bb5\u89c1 SKILL.md \u7b2c\u4e94\u7ae0\u3002\u8bfb\u53d6\u7edf\u4e00\u7528 utf-8-sig \u5265 BOM\u3002
\u519c\u4e1a\u7c7b\u53ea\u505a\u9891\u6b21/\u65b9\u5f0f/\u65f6\u6bb5\u7684\u5224\u65ad\u4e0e\u8bb0\u5f55\u6838\u5bf9\uff0c\u4e0d\u6d89\u53ca\u519c\u836f\u6d53\u5ea6\u3002
"""
import argparse
import json
import os
import sys

METHODS = ['\u6ef4\u704c', '\u6f2b\u704c', '\u55b7\u704c', '\u4eba\u5de5', '\u6c9f\u704c']
BAD_TIME = '\u4e2d\u5348'


def load_plan(path):
    raw = open(path, 'rb').read()
    text = raw.decode('utf-8-sig')
    return json.loads(text)


def validate(data):
    findings = []

    def add(level, item, why):
        findings.append({'level': level, 'item': item, 'why': why})

    crop = data.get('crop_type')
    area = data.get('area_type')
    method = data.get('irrigation_method')
    freq = data.get('frequency_per_week')
    tod = data.get('time_of_day')
    mulch = data.get('mulch')
    stages = data.get('fert_stages') or []
    npk = data.get('npk_recorded')
    records = data.get('records_kept')

    # \u704c\u6e89\u65b9\u5f0f\u5408\u6cd5
    if method not in METHODS:
        add('\u5148\u5904\u7406', '\u704c\u6e89\u65b9\u5f0f', 'irrigation_method \u4e0d\u5728\u5df2\u77e5\u65b9\u5f0f\uff08\u6ef4\u704c/\u6f2b\u704c/\u55b7\u704c/\u4eba\u5de5/\u6c9f\u704c\uff09\u5185')

    # \u6d47\u6c34\u65f6\u6bb5
    if tod == BAD_TIME:
        add('\u5148\u5904\u7406', '\u6d47\u6c34\u65f6\u6bb5', '\u4e2d\u5348\u6d47\u6c34\u84b8\u53d1\u5927\u4e14\u6613\u707c\u53f6\uff0c\u5e94\u6539\u6e05\u6668\u6216\u4e0a\u5348')
    elif tod is None:
        add('\u5f85\u786e\u8ba4', '\u6d47\u6c34\u65f6\u6bb5', '\u672a\u63d0\u4f9b\u6d47\u6c34\u65f6\u6bb5')

    # \u9891\u6b21\u533a\u95f4
    if isinstance(freq, (int, float)):
        if freq < 1 or freq > 21:
            add('\u5148\u5904\u7406', '\u704c\u6e89\u9891\u6b21', '\u6bcf\u5468\u704c\u6e89 %s \u6b21\u8d85\u51fa\u5408\u7406\u533a\u95f4 1-21' % freq)
    else:
        add('\u5f85\u786e\u8ba4', '\u704c\u6e89\u9891\u6b21', '\u672a\u63d0\u4f9b\u704c\u6e89\u9891\u6b21')

    # \u5e95\u80a5
    if '\u5e95\u80a5' not in stages:
        add('\u5f85\u786e\u8ba4', '\u5e95\u80a5\u5b89\u6392', '\u672a\u5b89\u6392\u8150\u719f\u5e95\u80a5\uff0c\u6839\u57fa\u4e0d\u7262')

    # N-P-K \u8bb0\u5f55
    if npk is not True:
        add('\u5f85\u786e\u8ba4', 'N-P-K\u8bb0\u5f55', '\u672a\u8bb0\u5f55\u80a5\u6599 N-P-K \u7c7b\u578b\uff0c\u65e0\u6cd5\u6838\u5bf9\u7ed3\u6784')

    # \u65bd\u80a5\u8bb0\u5f55
    if records is not True:
        add('\u5f85\u786e\u8ba4', '\u65bd\u80a5\u8bb0\u5f55', '\u672a\u505a\u704c\u6e89\u65bd\u80a5\u8bb0\u5f55\uff0c\u65e0\u6cd5\u6838\u5bf9\u7528\u91cf\u4e0e\u6548\u679c')

    # \u8986\u76d6\u4fdd\u5892\uff08\u83dc\u5730/\u5927\u68da\u9f13\u52b1\uff09
    if mulch is not True and area in ('\u83dc\u5730', '\u5927\u68da'):
        add('\u5f85\u786e\u8ba4', '\u8986\u76d6\u4fdd\u5892', '\u672a\u8986\u76d6\u4fdd\u5892\uff0c\u65e0\u6548\u84b8\u817e\u5927\u3001\u9700\u6c34\u66f4\u591a')

    # \u4f5c\u7269/\u5730\u5757\u5b8c\u6574\u6027
    if crop is None:
        add('\u5f85\u786e\u8ba4', '\u4f5c\u7269\u7c7b\u578b', '\u672a\u63d0\u4f9b\u4f5c\u7269\u7c7b\u578b\uff0c\u9891\u6b21\u65e0\u6cd5\u7ec6\u5316')
    if area is None:
        add('\u5f85\u786e\u8ba4', '\u5730\u5757\u7c7b\u578b', '\u672a\u63d0\u4f9b\u5730\u5757\u7c7b\u578b')

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
        'crop_type': '\u53f6\u83dc', 'area_type': '\u83dc\u5730', 'irrigation_method': '\u6ef4\u704c',
        'frequency_per_week': 4, 'time_of_day': '\u6e05\u6668', 'mulch': True,
        'fert_stages': ['\u5e95\u80a5', '\u82d7\u671f', '\u82b1\u679c\u671f'], 'npk_recorded': True,
        'records_kept': True,
    }
    r = validate(good)
    assert r['overall'] == '\u53ef\u7167\u6b64\u6267\u884c', '\u826f\u597d\u65b9\u6848\u5e94\u5224\u53ef\u7167\u6b64\u6267\u884c\uff0c\u5b9e\u9645=%s' % r['overall']
    passed += 1

    # \u53cd\u4f8b1\uff1a\u4e2d\u5348\u6d47\u6c34
    bad = dict(good); bad['time_of_day'] = '\u4e2d\u5348'
    r = validate(bad)
    assert any(f['item'] == '\u6d47\u6c34\u65f6\u6bb5' for f in r['findings']), '\u4e2d\u5348\u6d47\u6c34\u5e94\u5224\u5148\u5904\u7406'
    assert r['overall'] == '\u5148\u5904\u7406', '\u53cd\u4f8b\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b2\uff1a\u65b9\u5f0f\u975e\u6cd5
    bad = dict(good); bad['irrigation_method'] = '\u6d2a\u6c34'
    r = validate(bad)
    assert any(f['item'] == '\u704c\u6e89\u65b9\u5f0f' for f in r['findings']), '\u65b9\u5f0f\u975e\u6cd5\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b3\uff1a\u9891\u6b21\u8d8a\u754c
    bad = dict(good); bad['frequency_per_week'] = 0
    r = validate(bad)
    assert any(f['item'] == '\u704c\u6e89\u9891\u6b21' for f in r['findings']), '\u9891\u6b21\u8d8a\u754c\u5e94\u5224\u5148\u5904\u7406'
    passed += 1

    # \u53cd\u4f8b4\uff1a\u6f0f\u5e95\u80a5 \u2192 \u5f85\u786e\u8ba4
    bad = dict(good); bad['fert_stages'] = ['\u82d7\u671f', '\u82b1\u679c\u671f']
    r = validate(bad)
    assert any(f['item'] == '\u5e95\u80a5\u5b89\u6392' for f in r['findings']), '\u6f0f\u5e95\u80a5\u5e94\u5224\u5f85\u786e\u8ba4'
    passed += 1

    # \u53cd\u4f8b5\uff1a\u65e0\u8bb0\u5f55 \u2192 \u5f85\u786e\u8ba4
    bad = dict(good); bad['records_kept'] = False
    r = validate(bad)
    assert any(f['item'] == '\u65bd\u80a5\u8bb0\u5f55' for f in r['findings']), '\u65e0\u8bb0\u5f55\u5e94\u5224\u5f85\u786e\u8ba4'
    passed += 1

    # \u53cd\u4f8b6\uff1aN-P-K \u672a\u8bb0\u5f55 \u2192 \u5f85\u786e\u8ba4
    bad = dict(good); bad['npk_recorded'] = False
    r = validate(bad)
    assert any(f['item'] == 'N-P-K\u8bb0\u5f55' for f in r['findings']), 'N-P-K \u672a\u8bb0\u5f55\u5e94\u5224\u5f85\u786e\u8ba4'
    passed += 1

    # \u53cd\u4f8b7\uff1a\u83dc\u5730\u672a\u8986\u76d6 \u2192 \u5f85\u786e\u8ba4
    bad = dict(good); bad['mulch'] = False
    r = validate(bad)
    assert any(f['item'] == '\u8986\u76d6\u4fdd\u5892' for f in r['findings']), '\u83dc\u5730\u672a\u8986\u76d6\u5e94\u5224\u5f85\u786e\u8ba4'
    passed += 1

    # \u53cd\u4f8b\u62a4\u680f\uff1a\u4e2d\u5348\u6d47\u6c34\u7684\u53cd\u4f8b\u4e0d\u5f97\u5224\u53ef\u7167\u6b64\u6267\u884c
    bad = dict(good); bad['time_of_day'] = '\u4e2d\u5348'
    r = validate(bad)
    assert r['overall'] != '\u53ef\u7167\u6b64\u6267\u884c', '\u4e2d\u5348\u6d47\u6c34\u7684\u53cd\u4f8b\u4e0d\u5f97\u5224\u53ef\u7167\u6b64\u6267\u884c'
    passed += 1

    # BOM \u5904\u7406
    bom_json = ('\ufeff' + json.dumps(good, ensure_ascii=False)).encode('utf-8')
    text = bom_json.decode('utf-8-sig')
    assert '\ufeff' not in text, 'BOM \u672a\u88ab\u5265\u9664'
    data = json.loads(text)
    assert data['irrigation_method'] == '\u6ef4\u704c', 'BOM \u89e3\u6790\u540e\u5b57\u6bb5\u9519\u4f4d'
    r = validate(data)
    assert r['overall'] == '\u53ef\u7167\u6b64\u6267\u884c', 'BOM \u8f93\u5165\u7ecf\u89e3\u6790\u540e\u6821\u9a8c\u5e94\u6b63\u5e38\u901a\u8fc7'
    passed += 1

    msg = 'SELFTEST OK (%d passed, %d failed)' % (passed, failed)
    return msg, passed, failed


def main():
    ap = argparse.ArgumentParser(description='\u704c\u6e89\u65bd\u80a5\u8ba1\u5212\u6821\u9a8c')
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

    print('\u7528\u6cd5: python irrig_fert_plan.py --selftest | --file plan.json')
    sys.exit(2)


if __name__ == '__main__':
    main()
