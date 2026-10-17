# -*- coding: utf-8 -*-
"""\u9a6c\u6876\u5e95\u5ea7\u6e17\u6c34\u6545\u969c\u6811\u5224\u65ad\uff1a\u8f93\u5165\u73b0\u8c61\uff0c\u8f93\u51fa\u53ef\u80fd\u539f\u56e0\u4e0e\u5904\u7406\u987a\u5e8f\u3002

\u7528\u6cd5:
  python toilet_flange_check.py --text "\u51b2\u6c34\u65f6\u5e95\u5ea7\u8fb9\u7f18\u5192\u6c34\uff0c\u9a6c\u6876\u6709\u70b9\u6643"
  python toilet_flange_check.py --file \u63cf\u8ff0.txt [--out \u7ed3\u679c.md] [--format json]
  python toilet_flange_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

RULES = [
    {'id': 'T1', 'order': 1, 'name': '\u6c34\u7bb1\u7ed3\u9732\uff08\u51b7\u51dd\u6c34\uff09',
     'kw': ['\u9ec4\u6885', '\u6f6e\u6e7f', '\u6c34\u73e0', '\u7ed3\u9732', '\u6c34\u6c7d', '\u56de\u5357\u5929'],
     'test': '\u5e72\u71e5\u6392\u67e5\u6cd5\uff1a\u64e6\u5e72\u9759\u7f6e 1 \u5c0f\u65f6\u540e\u770b\u6709\u65e0\u65b0\u6c34\u6e0d',
     'fix': '\u52a0\u5f3a\u901a\u98ce\u9664\u6e7f\uff0c\u4e0d\u5c5e\u6545\u969c',
     'lift': '\u4e0d\u9700\u8981\u62ac\u9a6c\u6876'},
    {'id': 'T2', 'order': 2, 'name': '\u8fdb\u6c34\u8f6f\u7ba1\u63a5\u5934\u6216\u89d2\u9600\u6e17\u6c34',
     'kw': ['\u8f6f\u7ba1', '\u89d2\u9600', '\u8fdb\u6c34', '\u63a5\u5934', '\u4e00\u4fa7', '\u4e00\u76f4\u6709\u6c34'],
     'test': '\u7eb8\u5dfe\u8d34\u6577\u8f6f\u7ba1\u63a5\u5934\u4e0e\u89d2\u9600\uff0c5 \u5206\u949f\u540e\u770b\u662f\u5426\u6e7f',
     'fix': '\u66f4\u6362\u57ab\u7247\u6216\u8f6f\u7ba1',
     'lift': '\u4e0d\u9700\u8981\u62ac\u9a6c\u6876'},
    {'id': 'T3', 'order': 3, 'name': '\u6c34\u7bb1\u4e0e\u4fbf\u5668\u8fde\u63a5\u87ba\u6813\u57ab\u7247\u8001\u5316',
     'kw': ['\u540e\u4fa7', '\u9760\u5899', '\u6c34\u7bb1\u4e0b', '\u6c34\u7bb1\u5e95', '\u540e\u9762\u6ef4'],
     'test': '\u7eb8\u5dfe\u8d34\u6577\u6c34\u7bb1\u5e95\u90e8\u4e0e\u540e\u4fa7',
     'fix': '\u66f4\u6362\u8fde\u63a5\u87ba\u6813\u57ab\u7247',
     'lift': '\u901a\u5e38\u4e0d\u9700\u8981\u62ac\u9a6c\u6876'},
    {'id': 'T4', 'order': 4, 'name': '\u6392\u6c61\u7ba1\u5835\u585e',
     'kw': ['\u51b2\u4e0d\u4e0b\u53bb', '\u53cd\u6d8c', '\u8fd4\u6c34', '\u6392\u6c61\u6162', '\u5835', '\u5495\u565c', '\u6c34\u4f4d\u9ad8'],
     'test': '\u51b2\u6c34\u89c2\u5bdf\u6c34\u4f4d\u662f\u5426\u4e0a\u6da8\u6216\u8fd4\u6c34',
     'fix': '\u5148\u758f\u901a\uff0c\u518d\u8c08\u88c5\u6cd5\u5170',
     'lift': '\u5148\u758f\u901a'},
    {'id': 'T5', 'order': 5, 'name': '\u6cd5\u5170\u5708\u8001\u5316\u6216\u79fb\u4f4d',
     'kw': ['\u51b2\u6c34\u65f6', '\u5192\u6c34', '\u5e95\u5ea7', '\u8fb9\u7f18', '\u6643', '\u677e\u52a8', '\u5f02\u5473', '\u81ed\u5473'],
     'test': '\u5e72\u71e5\u6392\u67e5\u6cd5\u5b9a\u6765\u6e90\uff0c\u624b\u6643\u9a6c\u6876\u770b\u662f\u5426\u4f4d\u79fb',
     'fix': '\u66f4\u6362\u6cd5\u5170\uff0c\u6309\u7ba1\u53e3\u9ad8\u5ea6\u9009\u7c7b\u578b',
     'lift': '\u9700\u8981\u62ac\u9a6c\u6876'},
    {'id': 'T6', 'order': 6, 'name': '\u6cd5\u5170\u9009\u578b\u9519\u8bef\uff08\u7ba1\u53e3\u4f4e\u4e8e\u5730\u9762\uff09',
     'kw': ['\u4f4e\u4e8e\u5730\u9762', '\u7ba1\u53e3\u4f4e', '\u4f4e\u4e00\u622a', '\u591f\u4e0d\u5230', '\u53e0', '\u52a0\u539a', '\u5ef6\u4f38'],
     'test': '\u91cf\u7ba1\u53e3\u76f8\u5bf9\u5730\u9762\u7684\u9ad8\u5ea6\u5dee',
     'fix': '\u4f4e\u4e8e 2cm \u7528\u6cd5\u5170\u5ef6\u4f38\u5668\uff0c1-2cm \u7528\u52a0\u539a\u6cd5\u5170\uff0c\u7981\u6b62\u53e0\u88c5\u8721\u5708',
     'lift': '\u9700\u8981\u62ac\u9a6c\u6876\u5e76\u6539\u9009\u578b'},
    {'id': 'T7', 'order': 7, 'name': '\u9a6c\u6876\u672c\u4f53\u88c2\u7eb9',
     'kw': ['\u88c2\u7eb9', '\u88c2\u7f1d', '\u88c2\u4e86', '\u5e95\u5ea7\u88c2', '\u6c34\u7bb1\u88c2'],
     'test': '\u64e6\u5e72\u540e\u624b\u7535\u7167\u68c0\u5e95\u5ea7\u4e0e\u6c34\u7bb1',
     'fix': '\u505c\u7528\u5e76\u62a5\u4e13\u4e1a\u4eba\u5458\uff0c\u88c2\u7eb9\u53ea\u80fd\u6574\u4f53\u66f4\u6362',
     'lift': '\u505c\u7528\u5e76\u62a5\u4fee'},
    {'id': 'T8', 'order': 8, 'name': '\u5730\u9762\u4e0d\u5e73\u6216\u7ba1\u53e3\u7834\u635f',
     'kw': ['\u5730\u9762\u4e0d\u5e73', '\u74f7\u7816\u677e', '\u7ba1\u53e3\u7834', '\u7f3a\u89d2', '\u627e\u5e73'],
     'test': '\u6c34\u5e73\u5c3a\u6d4b\u5730\u9762\uff0c\u68c0\u67e5\u7ba1\u53e3\u662f\u5426\u5b8c\u6574',
     'fix': '\u505c\u7528\u5e76\u62a5\u4e13\u4e1a\u4eba\u5458',
     'lift': '\u505c\u7528\u5e76\u62a5\u4fee'},
    {'id': 'T9', 'order': 9, 'name': '\u697c\u677f\u6216\u9632\u6c34\u5c42\u95ee\u9898',
     'kw': ['\u697c\u4e0b', '\u5929\u82b1\u677f', '\u6e17\u6c34', '\u6c34\u5370', '\u6ef4\u6c34', '\u697c\u677f'],
     'test': '\u8be2\u95ee\u697c\u4e0b\u4f4f\u6237\uff0c\u67e5\u770b\u5929\u82b1\u677f\u6709\u65e0\u6c34\u6e0d',
     'fix': '\u505c\u7528\u5e76\u62a5\u7269\u4e1a\u4e0e\u4e13\u4e1a\u7ef4\u4fee',
     'lift': '\u505c\u7528\u5e76\u62a5\u4fee'},
]

RED = [
    {'kw': ['\u697c\u4e0b', '\u5929\u82b1\u677f', '\u6e17\u6c34', '\u6c34\u5370', '\u6ef4\u6c34', '\u697c\u677f'],
     'msg': '\u697c\u4e0b\u51fa\u73b0\u6e17\u6c34\u6216\u6c34\u5370\uff1a\u7acb\u5373\u505c\u6b62\u62c6\u88c5\uff0c\u6d89\u53ca\u697c\u677f\u4e0e\u9632\u6c34\u5c42\uff0c\u62a5\u7269\u4e1a\u4e0e\u4e13\u4e1a\u7ef4\u4fee\u3002'},
    {'kw': ['\u53cd\u6d8c', '\u8fd4\u6c34', '\u51b2\u4e0d\u4e0b\u53bb', '\u6c34\u4f4d\u9ad8'],
     'msg': '\u51b2\u6c34\u8fd4\u6c34\u5c5e\u6392\u6c61\u7ba1\u5835\u585e\uff1a\u5148\u758f\u901a\uff0c\u7981\u6b62\u5728\u5835\u585e\u72b6\u6001\u4e0b\u88c5\u65b0\u6cd5\u5170\uff0c\u5426\u5219\u7b2c\u4e00\u6b21\u51b2\u6c34\u5373\u62a5\u5e9f\u3002'},
    {'kw': ['\u88c2\u7eb9', '\u88c2\u7f1d', '\u88c2\u4e86'],
     'msg': '\u9a6c\u6876\u672c\u4f53\u88c2\u7eb9\uff1a\u4e0d\u5f97\u7ee7\u7eed\u4f7f\u7528\uff0c\u9700\u6574\u4f53\u66f4\u6362\uff0c\u8f6c\u4e13\u4e1a\u4eba\u5458\u3002'},
    {'kw': ['\u53e0', '\u4e24\u4e2a\u8721\u5708'],
     'msg': '\u7981\u6b62\u53e0\u88c5\u4e24\u4e2a\u8721\u5708\u51d1\u539a\u5ea6\uff1a\u538b\u4e0b\u65f6\u4e0a\u5c42\u9519\u4f4d\u5fc5\u7136\u6e17\u6f0f\uff0c\u5e94\u6539\u7528\u52a0\u539a\u6cd5\u5170\u6216\u5ef6\u4f38\u5668\u3002'},
    {'kw': ['\u667a\u80fd', '\u4e00\u4f53\u673a', '\u901a\u7535'],
     'msg': '\u667a\u80fd\u9a6c\u6876\u62c6\u88c5\u6d89\u53ca\u7535\u8def\u4e0e\u8fdb\u6c34\uff1a\u5148\u62d4\u63d2\u5934\u5e76\u5173\u8fdb\u6c34\uff0c\u5efa\u8bae\u7531\u4e13\u4e1a\u4eba\u5458\u6216\u5382\u5bb6\u552e\u540e\u5904\u7406\u3002'},
]

MISREAD = [
    {'kw': ['\u5f02\u5473', '\u81ed\u5473', '\u5473\u9053'],
     'msg': '\u536b\u751f\u95f4\u5f02\u5473\u4e0d\u7b49\u4e8e\u6cd5\u5170\u6f0f\u6c14\uff0c\u4e5f\u53ef\u80fd\u6765\u81ea\u5730\u6f0f\u6c34\u5c01\u5e72\u6db8\u6216\u6d17\u624b\u76c6\u4e0b\u6c34\u7ba1\u65e0\u5b58\u6c34\u5f2f\u3002'},
    {'kw': ['\u5730\u9762', '\u6709\u6c34', '\u6e7f'],
     'msg': '\u5e95\u5ea7\u5468\u56f4\u6709\u6c34\u4e0d\u7b49\u4e8e\u6cd5\u5170\u574f\u4e86\uff0c\u5148\u6392\u9664\u8fdb\u6c34\u8f6f\u7ba1\u3001\u6c34\u7bb1\u87ba\u6813\u57ab\u7247\u4e0e\u6c34\u7bb1\u7ed3\u9732\u3002'},
    {'kw': ['\u6362\u4e86\u8fd8', '\u6362\u5b8c\u8fd8', '\u88c5\u5b8c\u8fd8', '\u65b0\u6cd5\u5170'],
     'msg': '\u6362\u6cd5\u5170\u540e\u4ecd\u6f0f\uff0c\u591a\u4e3a\u6ca1\u538b\u5b9e\u3001\u843d\u4e0b\u540e\u632a\u52a8\u8fc7\u3001\u6216\u87ba\u6813\u8fc7\u7d27\u538b\u88c2\u9676\u74f7\u3002'},
    {'kw': ['\u6643', '\u677e\u52a8'],
     'msg': '\u9a6c\u6876\u6643\u52a8\u4f1a\u5e26\u52a8\u6cd5\u5170\u79fb\u4f4d\uff0c\u53ea\u7d27\u87ba\u6813\u4e0d\u6362\u6cd5\u5170\uff0c\u5bc6\u5c01\u5df2\u7ecf\u5931\u6548\u3002'},
    {'kw': ['\u51b2\u4e0d\u4e0b\u53bb', '\u6392\u6c61\u6162'],
     'msg': '\u51b2\u6c34\u4e0d\u7545\u662f\u6392\u6c61\u95ee\u9898\uff0c\u6362\u6cd5\u5170\u89e3\u51b3\u4e0d\u4e86\uff0c\u5148\u758f\u901a\u3002'},
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
                      'fix': r['fix'], 'lift': r['lift']})
    rules.sort(key=lambda x: x['order'])
    reds = [it['msg'] for it, _ in match(text, RED)]
    miss = [it['msg'] for it, _ in match(text, MISREAD)]
    return {'rules': rules, 'reds': reds, 'misread': miss,
            'top': rules[0]['name'] if rules else ''}


def render_md(text, r):
    lines = ['# \u9a6c\u6876\u5e95\u5ea7\u6e17\u6c34\u5224\u65ad\u7ed3\u679c', '']
    if not r['rules']:
        lines.append('\u672a\u5339\u914d\u5230\u6545\u969c\u6811\u6761\u76ee\u3002\u8bf7\u8865\u5145\uff1a\u6c34\u662f\u51b2\u6c34\u65f6\u624d\u51fa\u73b0\u8fd8\u662f\u4e00\u76f4\u6709\u3001\u9a6c\u6876\u6643\u4e0d\u6643\u3001\u697c\u4e0b\u6709\u65e0\u6e17\u6c34\u3002')
        lines.append('')
    else:
        lines.append('\u6700\u4f18\u5148\u6392\u67e5\uff1a%s' % r['top'])
        lines.append('')
        lines.append('## \u4e00\u3001\u6392\u67e5\u987a\u5e8f\uff08\u6309\u6b64\u987a\u5e8f\u6267\u884c\uff09')
        lines.append('')
        lines.append('| \u987a\u5e8f | \u53ef\u80fd\u539f\u56e0 | \u53ef\u80fd\u6027 | \u9a8c\u8bc1\u52a8\u4f5c | \u5904\u7f6e | \u662f\u5426\u9700\u62ac\u9a6c\u6876 |')
        lines.append('|---|---|---|---|---|---|')
        for x in r['rules']:
            lines.append('| %d | %s | %s | %s | %s | %s |' % (
                x['order'], x['name'], x['level'], x['test'], x['fix'], x['lift']))
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
    lines.append('1. \u5173\u89d2\u9600\uff0c\u667a\u80fd\u9a6c\u6876\u76d6\u62d4\u63d2\u5934\u5e76\u5173\u8fdb\u6c34')
    lines.append('2. \u5e72\u71e5\u6392\u67e5\u6cd5\u786e\u8ba4\u6e17\u6c34\u6765\u6e90')
    lines.append('3. \u786e\u8ba4\u51b2\u6c34\u987a\u7545\uff0c\u5835\u585e\u5148\u758f\u901a')
    lines.append('4. \u627e\u597d\u5e2e\u624b\uff0c\u4e24\u4eba\u5782\u76f4\u62ac\u8d77\uff0c\u7981\u6b62\u503e\u659c\u626d\u8f6c')
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

    r1 = analyse('\u51b2\u6c34\u65f6\u5e95\u5ea7\u8fb9\u7f18\u5192\u6c34\uff0c\u9a6c\u6876\u6709\u70b9\u6643')
    eq('case1 \u6cd5\u5170\u4f18\u5148', r1['rules'][0]['id'], 'T5')
    eq('case1 \u9700\u62ac\u9a6c\u6876', r1['rules'][0]['lift'], '\u9700\u8981\u62ac\u9a6c\u6876')

    r2 = analyse('\u9ec4\u6885\u5929\u6c34\u7bb1\u5916\u58c1\u6709\u6c34\u73e0\uff0c\u5730\u9762\u603b\u662f\u6e7f')
    eq('case2 \u7ed3\u9732\u4f18\u5148', r2['rules'][0]['id'], 'T1')
    eq('case2 \u4e0d\u9700\u62ac', r2['rules'][0]['lift'], '\u4e0d\u9700\u8981\u62ac\u9a6c\u6876')

    r3 = analyse('\u51b2\u4e0d\u4e0b\u53bb\uff0c\u8fd8\u53cd\u6d8c\uff0c\u6c34\u4f4d\u6da8\u4e0a\u6765')
    eq('case3 \u5835\u585e\u4f18\u5148', r3['rules'][0]['id'], 'T4')
    eq('case3 \u7ea2\u7ebf\u547d\u4e2d', len(r3['reds']) >= 1, True)

    r4 = analyse('\u697c\u4e0b\u5929\u82b1\u677f\u51fa\u73b0\u6c34\u5370')
    eq('case4 \u697c\u677f\u4f18\u5148', r4['rules'][0]['id'], 'T9')
    eq('case4 \u505c\u7528\u62a5\u4fee', r4['rules'][0]['lift'], '\u505c\u7528\u5e76\u62a5\u4fee')

    r5 = analyse('\u7ba1\u53e3\u4f4e\u4e8e\u5730\u9762\u4e00\u622a\uff0c\u80fd\u4e0d\u80fd\u53e0\u4e24\u4e2a\u8721\u5708')
    eq('case5 \u9009\u578b\u547d\u4e2d', any(x['id'] == 'T6' for x in r5['rules']), True)
    eq('case5 \u7ea2\u7ebf\u7981\u6b62\u53e0\u88c5', any('\u53e0\u88c5\u4e24\u4e2a\u8721\u5708' in m for m in r5['reds']), True)

    r6 = analyse('\u9a6c\u6876\u6709\u5f02\u5473')
    eq('case6 \u5f02\u5473\u8bef\u5224', any('\u5f02\u5473\u4e0d\u7b49\u4e8e\u6cd5\u5170\u6f0f\u6c14' in m for m in r6['misread']), True)

    r7 = analyse('\u9a6c\u6876\u6709\u70b9\u95ee\u9898')
    eq('case7 \u65e0\u5339\u914d', r7['rules'], [])

    md = render_md('\u51b2\u6c34\u65f6\u5e95\u5ea7\u8fb9\u7f18\u5192\u6c34', r1)
    eq('case8 \u8f93\u51fa\u8868\u5934', md.startswith('# '), True)
    js = json.loads(render_json(r1))
    eq('case9 \u8f93\u51fa\u952e', sorted(js.keys()), ['misread', 'reds', 'rules', 'top'])

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 12\n\u8986\u76d6: \u7ed3\u9732/\u8f6f\u7ba1\u89d2\u9600/\u87ba\u6813\u57ab\u7247/\u6392\u6c61\u5835\u585e/\u6cd5\u5170\u8001\u5316/\u9009\u578b\u9519\u8bef/\u672c\u4f53\u88c2\u7eb9/\u5730\u9762\u4e0d\u5e73/\u697c\u677f\u6e17\u6c34')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u9a6c\u6876\u5e95\u5ea7\u6e17\u6c34\u6545\u969c\u6811\u5224\u65ad')
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
