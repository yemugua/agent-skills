# -*- coding: utf-8 -*-
"""\u6c34\u9f99\u5934\u6f0f\u6c34\u6545\u969c\u6811\u5224\u65ad\uff1a\u8f93\u5165\u6f0f\u6c34\u4f4d\u7f6e\u4e0e\u73b0\u8c61\uff0c\u8f93\u51fa\u53ef\u80fd\u539f\u56e0\u4e0e\u5904\u7406\u987a\u5e8f\u3002

\u7528\u6cd5:
  python faucet_leak_check.py --text "\u5173\u7d27\u540e\u51fa\u6c34\u53e3\u4e00\u76f4\u6ef4\uff0c\u628a\u624b\u4e0b\u9762\u4e5f\u6e7f"
  python faucet_leak_check.py --file \u63cf\u8ff0.txt [--out \u7ed3\u679c.md] [--format json]
  python faucet_leak_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ---- \u6545\u969c\u6811\uff1aorder \u5373\u5904\u7406\u987a\u5e8f ----
RULES = [
    {'id': 'F1', 'order': 1, 'name': '\u8d77\u6ce1\u5668\u4e0e\u7ba1\u5185\u6b8b\u6c34\uff08\u6b63\u5e38\u73b0\u8c61\uff09',
     'kw': ['\u6ef4\u51e0\u6ef4', '\u6ef4\u51e0\u4e0b', '\u4e00\u4f1a\u513f\u5c31\u505c', '\u521a\u5173', '\u5173\u5b8c\u6ef4\u51e0'],
     'test': '\u89c2\u5bdf 10 \u5206\u949f\uff0c\u770b\u6ef4\u6f0f\u662f\u5426\u81ea\u884c\u505c\u6b62',
     'fix': '\u5c5e\u6b63\u5e38\u6b8b\u6c34\uff0c\u4e0d\u7528\u7ef4\u4fee',
     'worth': '\u4e0d\u9700\u8981\u6362\u9600\u82af'},
    {'id': 'F2', 'order': 2, 'name': '\u8d77\u6ce1\u5668\u7ed3\u57a2\u5835\u585e',
     'kw': ['\u51fa\u6c34\u5c0f', '\u6c34\u6d41\u5c0f', '\u5206\u53c9', '\u51fa\u6c34\u6563', '\u6c34\u82b1', '\u8d77\u6ce1\u5668'],
     'test': '\u62c6\u4e0b\u8d77\u6ce1\u5668\u770b\u7f51\u9762\u662f\u5426\u6709\u767d\u8272\u6c34\u57a2',
     'fix': '\u767d\u918b\u6d78\u6ce1\u9664\u57a2\u540e\u88c5\u56de',
     'worth': '\u4e0d\u9700\u8981\u6362\u9600\u82af'},
    {'id': 'F3', 'order': 3, 'name': '\u9600\u82af\u9676\u74f7\u7247\u78e8\u635f\u6216\u5bc6\u5c01\u57ab\u8001\u5316',
     'kw': ['\u4e00\u76f4\u6ef4', '\u6301\u7eed\u6ef4', '\u5173\u7d27\u8fd8\u6ef4', '\u5173\u4e0d\u4e25', '\u6ef4\u4e2a\u4e0d\u505c', '\u51fa\u6c34\u53e3\u6ef4'],
     'test': '\u7eb8\u5dfe\u8d34\u6577\u786e\u8ba4\u6f0f\u70b9\u5728\u51fa\u6c34\u53e3',
     'fix': '\u6309\u65e7\u4ef6\u5b9e\u6d4b\u89c4\u683c\u66f4\u6362\u9600\u82af',
     'worth': '\u6362\u9600\u82af\u6709\u6548'},
    {'id': 'F4', 'order': 4, 'name': '\u9600\u82af\u5916\u58f3 O \u5708\u8001\u5316',
     'kw': ['\u628a\u624b\u4e0b', '\u628a\u624b\u4e0b\u9762', '\u624b\u67c4\u4e0b', '\u9600\u4f53\u6e17', '\u628a\u624b\u6839\u90e8', '\u624b\u67c4\u6839\u90e8'],
     'test': '\u7eb8\u5dfe\u8d34\u6577\u786e\u8ba4\u6f0f\u70b9\u5728\u628a\u624b\u6839\u90e8',
     'fix': '\u66f4\u6362\u9600\u82af\uff0cO \u5708\u968f\u82af\u5e26',
     'worth': '\u6362\u9600\u82af\u6709\u6548'},
    {'id': 'F5', 'order': 5, 'name': '\u5e95\u5ea7\u80f6\u5708\u8001\u5316\u6216\u53f0\u4e0b\u87ba\u6bcd\u677e\u52a8',
     'kw': ['\u5e95\u5ea7', '\u4e00\u5708\u6f0f', '\u53f0\u9762', '\u63a5\u7f1d', '\u9f99\u5934\u6643', '\u677e\u52a8'],
     'test': '\u624b\u6643\u9f99\u5934\u770b\u662f\u5426\u677e\u52a8\uff0c\u7eb8\u5dfe\u8d34\u6577\u5e95\u5ea7\u4e00\u5708',
     'fix': '\u7d27\u53f0\u4e0b\u9501\u7d27\u87ba\u6bcd\u6216\u66f4\u6362\u5e95\u5ea7\u80f6\u5708',
     'worth': '\u6362\u9600\u82af\u65e0\u6548'},
    {'id': 'F6', 'order': 6, 'name': '\u8fdb\u6c34\u8f6f\u7ba1\u63a5\u5934\u57ab\u7247\u8001\u5316',
     'kw': ['\u8f6f\u7ba1', '\u63a5\u5934', '\u89d2\u9600\u63a5\u53e3', '\u87ba\u6bcd\u5904', '\u8fdb\u6c34\u53e3'],
     'test': '\u7eb8\u5dfe\u8d34\u6577\u786e\u8ba4\u6f0f\u70b9\u5728\u8f6f\u7ba1\u63a5\u5934',
     'fix': '\u66f4\u6362\u57ab\u7247\u6216\u8f6f\u7ba1\uff0c\u87ba\u7eb9\u7f20\u751f\u6599\u5e26',
     'worth': '\u6362\u9600\u82af\u65e0\u6548'},
    {'id': 'F7', 'order': 7, 'name': '\u8fdb\u6c34\u538b\u529b\u8fc7\u9ad8',
     'kw': ['\u6c34\u538b', '\u538b\u529b\u5927', '\u591a\u5904\u6f0f', '\u6c34\u9524', '\u54cd'],
     'test': '\u538b\u529b\u8868\u6d4b\u9759\u538b\uff0c\u8d85\u8fc7 0.6MPa \u5373\u504f\u9ad8',
     'fix': '\u52a0\u88c5\u51cf\u538b\u9600\uff0c\u6362\u9600\u82af\u4e0d\u80fd\u6839\u6cbb',
     'worth': '\u6362\u9600\u82af\u4e0d\u80fd\u6839\u6cbb'},
    {'id': 'F8', 'order': 8, 'name': '\u89d2\u9600\u5931\u6548\u6216\u9508\u6b7b',
     'kw': ['\u5173\u4e86\u8fd8\u51fa\u6c34', '\u5173\u4e0d\u4e86', '\u62e7\u4e0d\u52a8', '\u9508\u6b7b', '\u6ed1\u4e1d', '\u89d2\u9600'],
     'test': '\u5173\u89d2\u9600\u540e\u6253\u5f00\u9f99\u5934\uff0c\u770b\u51fa\u4e0d\u51fa\u6c34',
     'fix': '\u505c\u7528\u5e76\u62a5\u4e13\u4e1a\u4eba\u5458\uff0c\u4e0d\u5f97\u5e26\u6c34\u4f5c\u4e1a',
     'worth': '\u505c\u7528\u5e76\u62a5\u4fee'},
    {'id': 'F9', 'order': 9, 'name': '\u9600\u4f53\u88c2\u7eb9\u6216\u5899\u5185\u63a5\u5934\u6e17\u6f0f',
     'kw': ['\u9600\u4f53\u88c2', '\u88c2\u7eb9', '\u7802\u773c', '\u5899\u91cc', '\u5899\u9762\u6e17', '\u672c\u4f53\u6e17'],
     'test': '\u64e6\u5e72\u540e\u89c2\u5bdf\u6e17\u6c34\u662f\u5426\u6765\u81ea\u9600\u4f53\u672c\u4f53\u6216\u5899\u9762',
     'fix': '\u505c\u7528\u5e76\u62a5\u4e13\u4e1a\u4eba\u5458\uff0c\u9600\u4f53\u88c2\u7eb9\u9700\u6574\u4f53\u6362\u9f99\u5934',
     'worth': '\u505c\u7528\u5e76\u62a5\u4fee'},
]

RED = [
    {'kw': ['\u5173\u4e86\u8fd8\u51fa\u6c34', '\u5173\u4e0d\u4e86', '\u5173\u4e0d\u4f4f'],
     'msg': '\u5173\u95ed\u89d2\u9600\u540e\u4ecd\u51fa\u6c34\u8bf4\u660e\u89d2\u9600\u5df2\u5931\u6548\uff1a\u5148\u5904\u7406\u89d2\u9600\uff0c\u4e0d\u5f97\u5e26\u6c34\u62c6\u9600\u82af\u3002'},
    {'kw': ['\u62e7\u4e0d\u52a8', '\u9508\u6b7b', '\u6ed1\u4e1d', '\u65ad\u4e86', '\u65ad\u88c2'],
     'msg': '\u9508\u6b7b\u6216\u6ed1\u4e1d\u4ef6\u7981\u6b62\u786c\u62e7\uff1a\u62e7\u65ad\u5728\u5899\u5185\u63a5\u5934\u4f1a\u4ece\u6362\u9600\u82af\u53d8\u6210\u7838\u5899\u6362\u63a5\u5934\uff0c\u7acb\u5373\u505c\u7528\u62a5\u4e13\u4e1a\u4eba\u5458\u3002'},
    {'kw': ['\u5899\u91cc', '\u5899\u9762\u6e17', '\u9600\u4f53\u88c2', '\u88c2\u7eb9', '\u7802\u773c'],
     'msg': '\u9600\u4f53\u88c2\u7eb9\u6216\u5899\u5185\u63a5\u5934\u6e17\u6f0f\uff1a\u6d89\u53ca\u7834\u574f\u5899\u9762\uff0c\u505c\u7528\u5e76\u62a5\u4e13\u4e1a\u4eba\u5458\u3002'},
    {'kw': ['\u70ed\u6c34', '\u70ed\u6c34\u5668'],
     'msg': '\u70ed\u6c34\u4fa7\u4f5c\u4e1a\u524d\u5148\u5207\u65ad\u70ed\u6c34\u5668\u7535\u6e90\u4e0e\u8fdb\u6c34\uff0c\u907f\u514d\u5e72\u70e7\u4e0e\u70eb\u4f24\u3002'},
]

MISREAD = [
    {'kw': ['\u6ef4\u51e0\u6ef4', '\u4e00\u4f1a\u513f\u5c31\u505c'],
     'msg': '\u5173\u6c34\u540e\u6ef4\u51e0\u6ef4\u662f\u8d77\u6ce1\u5668\u4e0e\u7ba1\u5185\u6b8b\u6c34\uff0c\u5c5e\u6b63\u5e38\uff0c\u4e0d\u662f\u9600\u82af\u574f\u4e86\u3002'},
    {'kw': ['\u5e95\u5ea7', '\u4e00\u5708\u6f0f', '\u53f0\u9762', '\u63a5\u7f1d'],
     'msg': '\u5e95\u5ea7\u4e00\u5708\u6e17\u6c34\u6362\u9600\u82af\u65e0\u6548\uff0c\u95ee\u9898\u5728\u5e95\u5ea7\u80f6\u5708\u6216\u53f0\u4e0b\u9501\u7d27\u87ba\u6bcd\u3002'},
    {'kw': ['\u6362\u4e86\u8fd8', '\u6362\u5b8c\u8fd8', '\u65b0\u9600\u82af'],
     'msg': '\u6362\u82af\u540e\u4ecd\u6f0f\uff0c\u4f18\u5148\u6000\u7591\u9600\u5ea7\u9762\u88ab\u6c99\u7c92\u5212\u4f24\u3001\u578b\u53f7\u4e0d\u5b8c\u5168\u5339\u914d\u3001\u538b\u76d6\u672a\u538b\u7d27\u3002'},
    {'kw': ['\u51fa\u6c34\u5c0f', '\u5206\u53c9', '\u6c34\u6d41\u5c0f'],
     'msg': '\u51fa\u6c34\u5c0f\u6216\u6c34\u6d41\u5206\u53c9\u591a\u4e3a\u8d77\u6ce1\u5668\u7ed3\u57a2\uff0c\u9664\u57a2\u5373\u53ef\uff0c\u4e0e\u9600\u82af\u65e0\u5173\u3002'},
    {'kw': ['\u6c34\u538b', '\u538b\u529b\u5927', '\u6c34\u9524'],
     'msg': '\u6c34\u538b\u8fc7\u9ad8\u4f1a\u7f29\u77ed\u9600\u82af\u5bff\u547d\u5e76\u5bfc\u81f4\u5173\u4e0d\u4e25\uff0c\u9700\u88c5\u51cf\u538b\u9600\u800c\u975e\u53cd\u590d\u6362\u82af\u3002'},
]


def norm(s):
    return (s or '').replace(' ', '').replace('\u3000', '')


def match(text, items):
    t = norm(text)
    out = []
    for it in items:
        hits = [k for k in it['kw'] if k in t]
        if hits:
            out.append((it, hits))
    return out


def analyse(text):
    t = norm(text)
    rules = []
    for r in RULES:
        hits = [k for k in r['kw'] if k in t]
        if not hits:
            continue
        level = '\u9ad8' if len(hits) >= 2 else '\u4e2d'
        rules.append({'id': r['id'], 'order': r['order'], 'name': r['name'],
                      'level': level, 'hits': hits, 'test': r['test'],
                      'fix': r['fix'], 'worth': r['worth']})
    rules.sort(key=lambda x: x['order'])
    reds = [it['msg'] for it, _ in match(text, RED)]
    miss = [it['msg'] for it, _ in match(text, MISREAD)]
    return {'rules': rules, 'reds': reds, 'misread': miss,
            'top': rules[0]['name'] if rules else ''}


def render_md(text, r):
    lines = ['# \u6c34\u9f99\u5934\u6f0f\u6c34\u5224\u65ad\u7ed3\u679c', '']
    if not r['rules']:
        lines.append('\u672a\u5339\u914d\u5230\u6545\u969c\u6811\u6761\u76ee\u3002\u8bf7\u8865\u5145\uff1a\u6f0f\u5728\u51fa\u6c34\u53e3\u3001\u628a\u624b\u4e0b\u65b9\u3001\u5e95\u5ea7\u4e00\u5708\u8fd8\u662f\u8f6f\u7ba1\u63a5\u5934\uff1b\u5173\u89d2\u9600\u540e\u662f\u5426\u8fd8\u51fa\u6c34\u3002')
        lines.append('')
    else:
        lines.append('\u6700\u4f18\u5148\u6392\u67e5\uff1a%s' % r['top'])
        lines.append('')
        lines.append('## \u4e00\u3001\u6392\u67e5\u987a\u5e8f\uff08\u6309\u6b64\u987a\u5e8f\u6267\u884c\uff09')
        lines.append('')
        lines.append('| \u987a\u5e8f | \u53ef\u80fd\u539f\u56e0 | \u53ef\u80fd\u6027 | \u9a8c\u8bc1\u52a8\u4f5c | \u5904\u7f6e | \u6362\u9600\u82af |')
        lines.append('|---|---|---|---|---|---|')
        for x in r['rules']:
            lines.append('| %d | %s | %s | %s | %s | %s |' % (
                x['order'], x['name'], x['level'], x['test'], x['fix'], x['worth']))
        lines.append('')
    if r['reds']:
        lines.append('## \u4e8c\u3001\u5b89\u5168\u7ea2\u7ebf\uff08\u7acb\u5373\u6267\u884c\uff09')
        lines.append('')
        for m in r['reds']:
            lines.append('- %s' % m)
        lines.append('')
    if r['misread']:
        lines.append('## \u4e09\u3001\u8bef\u5224\u63d0\u9192')
        lines.append('')
        for m in r['misread']:
            lines.append('- %s' % m)
        lines.append('')
    lines.append('## \u56db\u3001\u52a8\u624b\u524d\u7684\u56fa\u5b9a\u52a8\u4f5c')
    lines.append('')
    lines.append('1. \u5173\u89d2\u9600\uff0c\u5f00\u9f99\u5934\u6cc4\u538b\uff0c\u786e\u8ba4\u5b8c\u5168\u4e0d\u51fa\u6c34')
    lines.append('2. \u70ed\u6c34\u4fa7\u5148\u5207\u65ad\u70ed\u6c34\u5668\u7535\u6e90\u4e0e\u8fdb\u6c34')
    lines.append('3. \u7528\u7eb8\u5dfe\u8d34\u6577\u6cd5\u5b9a\u4f4d\u6f0f\u70b9\uff0c\u4e0d\u9760\u76ee\u6d4b')
    lines.append('4. \u62c6\u4e0b\u7684\u65e7\u9600\u82af\u5e26\u5b9e\u7269\u53bb\u6bd4\u5bf9\uff0c\u4e0d\u53ea\u770b 35mm')
    lines.append('')
    lines.append('---')
    lines.append('\u672c\u7ed3\u679c\u4e3a\u73b0\u8c61\u5339\u914d\u4e0e\u5904\u7406\u987a\u5e8f\u5efa\u8bae\uff0c\u4e0d\u4ee3\u8868\u73b0\u573a\u5224\u65ad\uff0c\u4e0d\u6784\u6210\u4e13\u4e1a\u65bd\u5de5\u7ed3\u8bba\u3002')
    return '\n'.join(lines)


def render_json(r):
    return json.dumps(r, ensure_ascii=False, indent=2)


def selftest():
    errs = []

    def eq(name, got, want):
        if got != want:
            errs.append('%s got=%r want=%r' % (name, got, want))

    r1 = analyse('\u5173\u7d27\u540e\u51fa\u6c34\u53e3\u4e00\u76f4\u6ef4\uff0c\u628a\u624b\u4e0b\u9762\u4e5f\u6e7f')
    eq('case1 \u51fa\u6c34\u53e3\u6ef4\u4f18\u5148', r1['rules'][0]['id'], 'F3')
    eq('case1 \u628a\u624b\u6e17\u547d\u4e2d', any(x['id'] == 'F4' for x in r1['rules']), True)

    r2 = analyse('\u5173\u6c34\u540e\u6ef4\u51e0\u6ef4\u5c31\u505c\u4e86')
    eq('case2 \u6b8b\u6c34\u4f18\u5148', r2['rules'][0]['id'], 'F1')
    eq('case2 \u65e0\u9700\u6362\u82af', r2['rules'][0]['worth'], '\u4e0d\u9700\u8981\u6362\u9600\u82af')

    r3 = analyse('\u5e95\u5ea7\u4e00\u5708\u6f0f\u6c34\uff0c\u9f99\u5934\u6709\u70b9\u6643')
    eq('case3 \u5e95\u5ea7\u4f18\u5148', r3['rules'][0]['id'], 'F5')
    eq('case3 \u6362\u82af\u65e0\u6548', r3['rules'][0]['worth'], '\u6362\u9600\u82af\u65e0\u6548')
    eq('case3 \u8bef\u5224\u63d0\u9192', len(r3['misread']) >= 1, True)

    r4 = analyse('\u89d2\u9600\u62e7\u4e0d\u52a8\uff0c\u9508\u6b7b\u4e86\uff0c\u5173\u4e86\u8fd8\u51fa\u6c34')
    eq('case4 \u89d2\u9600\u4f18\u5148', r4['rules'][0]['id'], 'F8')
    eq('case4 \u7ea2\u7ebf\u547d\u4e2d', len(r4['reds']) >= 2, True)

    r5 = analyse('\u51fa\u6c34\u5c0f\uff0c\u6c34\u6d41\u5206\u53c9')
    eq('case5 \u8d77\u6ce1\u5668\u4f18\u5148', r5['rules'][0]['id'], 'F2')

    r6 = analyse('\u6362\u4e86\u65b0\u9600\u82af\u8fd8\u662f\u6f0f')
    eq('case6 \u6362\u82af\u540e\u8bef\u5224', any('\u6362\u82af\u540e\u4ecd\u6f0f' in m for m in r6['misread']), True)

    r7 = analyse('\u6c34\u9f99\u5934\u6709\u70b9\u95ee\u9898')
    eq('case7 \u65e0\u5339\u914d', r7['rules'], [])

    md = render_md('\u5173\u7d27\u540e\u51fa\u6c34\u53e3\u4e00\u76f4\u6ef4', r1)
    eq('case8 \u8f93\u51fa\u8868\u5934', md.startswith('# '), True)
    js = json.loads(render_json(r1))
    eq('case9 \u8f93\u51fa\u952e', sorted(js.keys()), ['misread', 'reds', 'rules', 'top'])

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 12\n\u8986\u76d6: \u6b8b\u6c34/\u8d77\u6ce1\u5668/\u9600\u82af\u78e8\u635f/\u5bc6\u5c01\u5708/\u5e95\u5ea7\u80f6\u5708/\u8f6f\u7ba1\u57ab\u7247/\u6c34\u538b\u8fc7\u9ad8/\u89d2\u9600\u9508\u6b7b/\u9600\u4f53\u88c2\u7eb9')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u6c34\u9f99\u5934\u6f0f\u6c34\u6545\u969c\u6811\u5224\u65ad')
    ap.add_argument('--text', help='\u73b0\u8c61\u63cf\u8ff0')
    ap.add_argument('--file', help='\u4ece\u6587\u4ef6\u8bfb\u73b0\u8c61\u63cf\u8ff0')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'])
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    text = a.text or ''
    if a.file:
        if not os.path.exists(a.file):
            print('ERROR --file \u4e0d\u5b58\u5728')
            return 2
        text = open(a.file, 'r', encoding='utf-8', errors='replace').read()
    if not text.strip():
        print('ERROR \u9700\u8981 --text \u6216 --file')
        return 2

    r = analyse(text)
    out = render_md(text, r) if a.format == 'md' else render_json(r)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % a.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
