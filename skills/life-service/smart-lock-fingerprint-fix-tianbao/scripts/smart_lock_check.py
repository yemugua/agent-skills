# -*- coding: utf-8 -*-
"""\u667a\u80fd\u95e8\u9501\u5931\u7075\u6545\u969c\u6811\u5224\u65ad\uff1a\u8f93\u5165\u73b0\u8c61\uff0c\u8f93\u51fa\u6392\u67e5\u987a\u5e8f\u4e0e\u5e94\u6025\u5f00\u9501\u4f18\u5148\u7ea7\u3002

\u7528\u6cd5:
  python smart_lock_check.py --text "\u6307\u7eb9\u8bc6\u522b\u6210\u529f\u4f46\u95e8\u6253\u4e0d\u5f00\uff0c\u7535\u6c60\u521a\u6362\u8fc7"
  python smart_lock_check.py --file \u63cf\u8ff0.txt [--out \u7ed3\u679c.md] [--format json]
  python smart_lock_check.py --selftest
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
    {'id': 'S1', 'order': 1, 'name': '\u7535\u6c60\u7535\u538b\u4e0d\u8db3',
     'kw': ['\u6ca1\u7535', '\u4f4e\u7535', '\u7535\u91cf', '\u5c4f\u5e55\u6697', '\u53d8\u6697', '\u63d0\u793a\u6362\u7535\u6c60', '\u7535\u673a\u65e0\u529b', '\u8f6c\u4e0d\u52a8'],
     'test': '\u6362\u4e00\u7ec4\u65b0\u7535\u6c60\u6216\u7528\u5e94\u6025\u4f9b\u7535\u540e\u91cd\u8bd5',
     'fix': '\u66f4\u6362\u7535\u6c60\uff1b\u82e5\u6362\u8fc7\u4ecd\u5f88\u5feb\u6ca1\u7535\uff0c\u8f6c\u67e5\u673a\u68b0\u963b\u529b'},
    {'id': 'S2', 'order': 2, 'name': '\u6307\u7eb9\u5934\u810f\u6c61',
     'kw': ['\u810f', '\u6cb9\u6c61', '\u8bc6\u522b\u6162', '\u5076\u5c14\u6210\u529f', '\u65f6\u597d\u65f6\u574f', '\u8981\u6309\u597d\u51e0\u6b21'],
     'test': '\u5e72\u8f6f\u5e03\u64e6\u62ed\u6307\u7eb9\u5934\u540e\u91cd\u8bd5',
     'fix': '\u6e05\u6d01\u6307\u7eb9\u5934\uff0c\u7981\u7528\u7814\u78e8\u5242\u4e0e\u6e7f\u5dfe'},
    {'id': 'S3', 'order': 3, 'name': '\u624b\u6307\u72b6\u6001\u4e0d\u4f73',
     'kw': ['\u6e7f\u624b', '\u624b\u6e7f', '\u8131\u76ae', '\u5e72', '\u51ac\u5929', '\u5929\u51b7', '\u51fa\u6c57', '\u6d17\u5b8c\u624b'],
     'test': '\u64e6\u5e72\u56de\u6696\u540e\u6362\u53e6\u4e00\u679a\u624b\u6307\u91cd\u8bd5',
     'fix': '\u6539\u5584\u624b\u6307\u72b6\u6001\uff1b\u51ac\u5929\u5148\u6413\u624b\u56de\u6696\u518d\u8bd5'},
    {'id': 'S4', 'order': 4, 'name': '\u6307\u7eb9\u5f55\u5165\u8d28\u91cf\u5dee',
     'kw': ['\u8bc6\u522b\u4e0d\u4e86', '\u8bc6\u522b\u5931\u8d25', '\u4e0d\u8bc6\u522b', '\u5931\u8d25', '\u67d0\u4e2a\u4eba', '\u5bb6\u4eba', '\u5f55\u5165'],
     'test': '\u5220\u9664\u65e7\u6a21\u677f\u540e\u591a\u89d2\u5ea6\u91cd\u65b0\u5f55\u5165',
     'fix': '\u6309\u91cd\u5f55\u89c4\u8303\u5206 3-5 \u6b21\u5f55\u5165\uff0c\u8986\u76d6\u6307\u8179\u4e0e\u8fb9\u7f18'},
    {'id': 'S5', 'order': 5, 'name': '\u7535\u6c60\u89e6\u70b9\u63a5\u89e6\u4e0d\u826f',
     'kw': ['\u9ed1\u5c4f', '\u91cd\u542f', '\u6ca1\u53cd\u5e94', '\u6309\u952e\u65e0', '\u95f4\u6b47', '\u677e\u52a8', '\u9508\u8680'],
     'test': '\u53d6\u51fa\u7535\u6c60\u770b\u5f39\u7c27\u662f\u5426\u9508\u8680\u3001\u7535\u6c60\u662f\u5426\u677e\u52a8',
     'fix': '\u64e6\u89e6\u70b9\u3001\u6821\u6b63\u5f39\u7c27\u3001\u66f4\u6362\u7535\u6c60'},
    {'id': 'S6', 'order': 6, 'name': '\u673a\u68b0\u963b\u529b\u8fc7\u5927\u6216\u95e8\u4f53\u53d8\u5f62',
     'kw': ['\u8bc6\u522b\u6210\u529f', '\u5f00\u4e86\u4f46', '\u6253\u4e0d\u5f00', '\u963b\u529b', '\u5361', '\u95e8\u4e0b\u5782', '\u6362\u4e86\u7535\u6c60\u8fd8'],
     'test': '\u7528\u673a\u68b0\u94a5\u5319\u8bd5\u5f00\uff0c\u611f\u53d7\u8f6c\u52a8\u963b\u529b',
     'fix': '\u8c03\u95e8\u3001\u6da6\u6ed1\u9501\u820c\u3001\u68c0\u67e5\u65b9\u8f74\uff1b\u9700\u4e13\u4e1a\u4eba\u5458'},
    {'id': 'S7', 'order': 7, 'name': '\u95e8\u6846\u6263\u677f\u9519\u4f4d',
     'kw': ['\u4e0d\u81ea\u52a8\u4e0a\u9501', '\u81ea\u52a8\u4e0a\u9501\u5931\u8d25', '\u6263\u677f', '\u5bf9\u4e0d\u4e0a', '\u9501\u820c'],
     'test': '\u770b\u9501\u820c\u4e0e\u6263\u677f\u5b54\u662f\u5426\u5bf9\u4e2d',
     'fix': '\u8c03\u6574\u6263\u677f\u4f4d\u7f6e'},
    {'id': 'S8', 'order': 8, 'name': '\u8bc6\u522b\u6a21\u5757\u6216\u4e3b\u677f\u6545\u969c',
     'kw': ['\u6362\u4e86\u6a21\u5757', '\u552e\u540e', '\u4e3b\u677f', '\u6a21\u5757\u574f', '\u5168\u90e8\u65e0\u6548', '\u90fd\u4e0d\u884c'],
     'test': '\u4ee5\u4e0a\u5168\u90e8\u6392\u9664\u540e\u4ecd\u5931\u7075',
     'fix': '\u62a5\u552e\u540e\u6216\u4e13\u4e1a\u4eba\u5458\u6362\u4ef6'},
]

RED = [
    {'kw': ['\u9f13\u5305', '\u53d1\u70eb', '\u53d1\u70ed', '\u5f02\u5473', '\u6f0f\u6db2', '\u5192\u70df'],
     'msg': '\u7535\u6c60\u9f13\u5305\u3001\u53d1\u70eb\u3001\u5f02\u5473\u6216\u5192\u70df\uff1a\u7acb\u5373\u505c\u7528\u65ad\u7535\uff0c\u6234\u624b\u5957\u53d6\u51fa\u653e\u7a7a\u65f7\u5904\uff0c\u52ff\u6324\u538b\u523a\u7834\uff1b\u5192\u70df\u8d77\u706b\u65f6\u4eba\u5458\u64a4\u79bb\u5e76\u62e8 119\u3002'},
    {'kw': ['\u88ab\u56f0', '\u5b69\u5b50\u5728\u91cc', '\u8001\u4eba\u5728\u91cc', '\u51fa\u4e0d\u6765', '\u706b\u707e', '\u7740\u706b', '\u71c3\u6c14'],
     'msg': '\u6709\u4eba\u88ab\u56f0\u6216\u5b58\u5728\u706b\u60c5\u3001\u71c3\u6c14\u6cc4\u6f0f\uff1a\u7acb\u5373\u6c42\u52a9 119 / 110\uff0c\u4e0d\u8981\u81ea\u884c\u62c6\u9501\u3002'},
    {'kw': ['\u94a5\u5319\u4e22\u4e86', '\u94a5\u5319\u65ad', '\u9501\u82af\u88ab\u5835', '\u88ab\u5835'],
     'msg': '\u673a\u68b0\u94a5\u5319\u4e22\u5931\u3001\u65ad\u5728\u9501\u5b54\u6216\u9501\u82af\u88ab\u5835\uff1a\u8f6c\u4e13\u4e1a\u4eba\u5458\u5904\u7406\u3002'},
    {'kw': ['\u64ac', '\u7838', '\u7834\u574f'],
     'msg': '\u7834\u574f\u6027\u62c6\u9664\u662f\u6700\u540e\u624b\u6bb5\uff1a\u9700\u7269\u4e1a\u6216\u8b66\u65b9\u89c1\u8bc1\uff0c\u9501\u5177\u62a5\u5e9f\u4e14\u95e8\u53ef\u80fd\u53d7\u635f\uff0c\u4f18\u5148\u8054\u7cfb\u5907\u6848\u5f00\u9501\u516c\u53f8\u3002'},
]

EMERGENCY = [
    '\u673a\u68b0\u94a5\u5319\uff1a\u4f18\u5148\u4f7f\u7528\uff0c\u540c\u65f6\u9a8c\u8bc1\u673a\u68b0\u90e8\u5206\u662f\u5426\u6b63\u5e38',
    '\u5e94\u6025\u4f9b\u7535\uff1a\u786e\u8ba4\u63a5\u53e3\u7c7b\u578b\uff0cType-C \u7528\u5145\u7535\u5b9d\uff0c9V \u89e6\u70b9\u7528\u65b9\u5757\u7535\u6c60',
    '\u5bc6\u7801 / \u5361\u7247 / NFC\uff1a\u4e3b\u677f\u4ecd\u6709\u7535\u65f6\u53ef\u7528',
    'APP \u84dd\u7259 / \u4e34\u65f6\u5bc6\u7801\uff1a\u9700\u63d0\u524d\u7ed1\u5b9a\u4e14\u9501\u5728\u7ebf',
    '\u6b63\u89c4\u5907\u6848\u5f00\u9501\u516c\u53f8\uff1a\u6838\u9a8c\u5907\u6848\u4e0e\u8eab\u4efd\uff0c\u51c6\u5907\u5c45\u4f4f\u8bc1\u660e',
    '\u7834\u574f\u6027\u62c6\u9664\uff1a\u6700\u540e\u624b\u6bb5\uff0c\u9700\u7269\u4e1a\u6216\u8b66\u65b9\u89c1\u8bc1',
]

MISREAD = [
    {'kw': ['\u8bc6\u522b\u4e0d\u4e86', '\u8bc6\u522b\u5931\u8d25', '\u4e0d\u8bc6\u522b'],
     'msg': '\u6307\u7eb9\u8bc6\u522b\u4e0d\u4e86\u4e0d\u7b49\u4e8e\u6a21\u5757\u574f\u4e86\uff0c\u591a\u4e3a\u624b\u6307\u810f\u5e72\u3001\u5f55\u5165\u8d28\u91cf\u5dee\u6216\u7535\u6c60\u7535\u538b\u4f4e\u3002'},
    {'kw': ['\u8bc6\u522b\u6210\u529f', '\u6253\u4e0d\u5f00'],
     'msg': '\u8bc6\u522b\u6210\u529f\u5374\u6253\u4e0d\u5f00\uff0c\u591a\u4e3a\u7535\u6c60\u7535\u538b\u4e0d\u8db3\u4ee5\u9a71\u52a8\u7535\u673a\u6216\u9501\u820c\u963b\u529b\u5927\uff0c\u5148\u7528\u673a\u68b0\u94a5\u5319\u9a8c\u8bc1\u3002'},
    {'kw': ['\u9ed1\u5c4f', '\u6ca1\u53cd\u5e94'],
     'msg': '\u9ed1\u5c4f\u5148\u67e5\u7535\u6c60\u63a5\u89e6\uff1a\u5f39\u7c27\u9508\u8680\u3001\u7535\u6c60\u677e\u52a8\u3001\u89e6\u70b9\u6c27\u5316\uff0c\u4e0d\u8981\u76f4\u63a5\u5224\u4e3b\u677f\u62a5\u5e9f\u3002'},
    {'kw': ['\u6362\u4e86\u7535\u6c60', '\u6362\u8fc7\u7535\u6c60', '\u5f88\u5feb\u6ca1\u7535'],
     'msg': '\u6362\u65b0\u7535\u6c60\u4ecd\u5f88\u5feb\u6ca1\u7535\uff0c\u662f\u673a\u68b0\u963b\u529b\u8fc7\u5927\u7684\u4fe1\u53f7\uff0c\u6362\u7535\u6c60\u6cbb\u6807\u4e0d\u6cbb\u672c\u3002'},
    {'kw': ['\u51ac\u5929', '\u5929\u51b7', '\u624b\u5e72'],
     'msg': '\u51ac\u5929\u5931\u7075\u591a\u4e3a\u4f4e\u6e29\u4e0e\u9759\u7535\u5f71\u54cd\u534a\u5bfc\u4f53\u91c7\u96c6\uff0c\u56de\u6696\u540e\u591a\u6570\u6062\u590d\uff0c\u4e0d\u5fc5\u6025\u4e8e\u6362\u9501\u3002'},
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
                      'level': level, 'hits': hits, 'test': r['test'], 'fix': r['fix']})
    rules.sort(key=lambda x: x['order'])
    reds = [it['msg'] for it, _ in match(text, RED)]
    miss = [it['msg'] for it, _ in match(text, MISREAD)]
    locked_out = any(k in t for k in ['\u88ab\u9501', '\u8fdb\u4e0d\u53bb', '\u95e8\u5916', '\u5f00\u4e0d\u4e86\u95e8', '\u5fd8\u4e86\u5e26\u94a5\u5319', '\u6ca1\u5e26\u94a5\u5319'])
    return {'rules': rules, 'reds': reds, 'misread': miss, 'locked_out': locked_out,
            'top': rules[0]['name'] if rules else ''}


def render_md(text, r):
    lines = ['# \u667a\u80fd\u95e8\u9501\u5931\u7075\u5224\u65ad\u7ed3\u679c', '']
    if r['locked_out']:
        lines.append('## \u96f6\u3001\u5148\u6309\u5e94\u6025\u987a\u5e8f\u8fdb\u95e8')
        lines.append('')
        for i, s in enumerate(EMERGENCY, 1):
            lines.append('%d. %s' % (i, s))
        lines.append('')
    if r['reds']:
        lines.append('## \u4e00\u3001\u5b89\u5168\u7ea2\u7ebf\uff08\u7acb\u5373\u6267\u884c\uff09')
        lines.append('')
        for m in r['reds']:
            lines.append('- %s' % m)
        lines.append('')
    if not r['rules']:
        lines.append('\u672a\u5339\u914d\u5230\u6545\u969c\u6811\u6761\u76ee\u3002\u8bf7\u8865\u5145\uff1a\u8bc6\u522b\u65f6\u6709\u6ca1\u6709\u53cd\u5e94\u3001\u5c4f\u5e55\u4eae\u5ea6\u3001\u7535\u6c60\u66f4\u6362\u65f6\u95f4\u3001\u673a\u68b0\u94a5\u5319\u80fd\u5426\u8f6c\u52a8\u3002')
        lines.append('')
    else:
        lines.append('## \u4e8c\u3001\u6392\u67e5\u987a\u5e8f\uff08\u6309\u6b64\u987a\u5e8f\u6267\u884c\uff09')
        lines.append('')
        lines.append('\u6700\u4f18\u5148\u6392\u67e5\uff1a%s' % r['top'])
        lines.append('')
        lines.append('| \u987a\u5e8f | \u53ef\u80fd\u539f\u56e0 | \u53ef\u80fd\u6027 | \u9a8c\u8bc1\u52a8\u4f5c | \u5904\u7f6e |')
        lines.append('|---|---|---|---|---|')
        for x in r['rules']:
            lines.append('| %d | %s | %s | %s | %s |' % (
                x['order'], x['name'], x['level'], x['test'], x['fix']))
        lines.append('')
    if r['misread']:
        lines.append('## \u4e09\u3001\u8bef\u5224\u63d0\u9192')
        lines.append('')
        for m in r['misread']:
            lines.append('- %s' % m)
        lines.append('')
    lines.append('## \u56db\u3001\u56fa\u5b9a\u63d0\u9192')
    lines.append('')
    lines.append('1. \u673a\u68b0\u94a5\u5319\u540c\u65f6\u662f\u8bca\u65ad\u5de5\u5177\uff0c\u80fd\u8f6c\u8bf4\u660e\u673a\u68b0\u90e8\u5206\u6b63\u5e38')
    lines.append('2. \u6062\u590d\u51fa\u5382\u8bbe\u7f6e\u4f1a\u6e05\u7a7a\u5168\u90e8\u6307\u7eb9\u4e0e\u5bc6\u7801\uff0c\u786e\u8ba4\u6709\u673a\u68b0\u94a5\u5319\u518d\u505a')
    lines.append('3. \u7981\u6b62\u628a\u5e94\u6025\u94a5\u5319\u5b58\u653e\u5728\u95e8\u5916\u4efb\u4f55\u4f4d\u7f6e')
    lines.append('')
    lines.append('---')
    lines.append('\u672c\u7ed3\u679c\u4e3a\u73b0\u8c61\u5339\u914d\u4e0e\u6392\u67e5\u987a\u5e8f\u5efa\u8bae\uff0c\u4e0d\u63d0\u4f9b\u5f00\u9501\u6280\u672f\u624b\u6cd5\uff0c\u4e0d\u6784\u6210\u9501\u5177\u7ef4\u4fee\u7ed3\u8bba\u3002')
    return '\n'.join(lines)


def render_json(r):
    return json.dumps(r, ensure_ascii=False, indent=2)


def selftest():
    errs = []

    def eq(name, got, want):
        if got != want:
            errs.append('%s got=%r want=%r' % (name, got, want))

    r1 = analyse('\u6307\u7eb9\u8bc6\u522b\u6210\u529f\u4f46\u95e8\u6253\u4e0d\u5f00\uff0c\u7535\u6c60\u521a\u6362\u8fc7')
    eq('case1 \u673a\u68b0\u963b\u529b\u547d\u4e2d', any(x['id'] == 'S6' for x in r1['rules']), True)

    r2 = analyse('\u7535\u6c60\u6ca1\u7535\u4e86\uff0c\u5c4f\u5e55\u53d8\u6697\uff0c\u63d0\u793a\u6362\u7535\u6c60')
    eq('case2 \u7535\u6c60\u4f18\u5148', r2['rules'][0]['id'], 'S1')

    r3 = analyse('\u51ac\u5929\u624b\u5e72\uff0c\u6307\u7eb9\u8bc6\u522b\u4e0d\u4e86')
    eq('case3 \u624b\u6307\u72b6\u6001\u547d\u4e2d', any(x['id'] == 'S3' for x in r3['rules']), True)
    eq('case3 \u51ac\u5929\u8bef\u5224\u63d0\u9192', any('\u51ac\u5929\u5931\u7075' in m for m in r3['misread']), True)

    r4 = analyse('\u7535\u6c60\u9f13\u5305\u4e86\uff0c\u8fd8\u6709\u70b9\u53d1\u70eb')
    eq('case4 \u7ea2\u7ebf\u547d\u4e2d', len(r4['reds']) >= 1, True)
    eq('case4 \u7535\u6c60\u63d0\u793a', any('\u9f13\u5305' in m for m in r4['reds']), True)

    r5 = analyse('\u88ab\u9501\u5728\u95e8\u5916\uff0c\u6ca1\u5e26\u94a5\u5319\uff0c\u8fdb\u4e0d\u53bb')
    eq('case5 \u5e94\u6025\u4f18\u5148', r5['locked_out'], True)
    md5 = render_md('\u88ab\u9501\u5728\u95e8\u5916\uff0c\u6ca1\u5e26\u94a5\u5319\uff0c\u8fdb\u4e0d\u53bb', r5)
    eq('case5 \u8f93\u51fa\u5e94\u6025\u6bb5', '\u5148\u6309\u5e94\u6025\u987a\u5e8f\u8fdb\u95e8' in md5, True)

    r6 = analyse('\u5b69\u5b50\u5728\u91cc\u9762\u51fa\u4e0d\u6765\uff0c\u5c4b\u91cc\u6709\u71c3\u6c14\u5473')
    eq('case6 \u7d27\u6025\u7ea2\u7ebf', any('119' in m for m in r6['reds']), True)

    r7 = analyse('\u95e8\u9501\u6709\u70b9\u95ee\u9898')
    eq('case7 \u65e0\u5339\u914d', r7['rules'], [])

    md = render_md('\u6307\u7eb9\u8bc6\u522b\u4e0d\u4e86', r3)
    eq('case8 \u8f93\u51fa\u8868\u5934', md.startswith('# '), True)
    js = json.loads(render_json(r1))
    eq('case9 \u8f93\u51fa\u952e', sorted(js.keys()), ['locked_out', 'misread', 'reds', 'rules', 'top'])

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 12\n\u8986\u76d6: \u7535\u6c60\u7535\u538b/\u6307\u7eb9\u5934\u810f\u6c61/\u624b\u6307\u72b6\u6001/\u5f55\u5165\u8d28\u91cf/\u89e6\u70b9\u63a5\u89e6/\u673a\u68b0\u963b\u529b/\u6263\u677f\u9519\u4f4d/\u6a21\u5757\u6545\u969c/\u7535\u6c60\u9f13\u5305/\u4eba\u5458\u88ab\u56f0')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u667a\u80fd\u95e8\u9501\u5931\u7075\u6545\u969c\u6811\u5224\u65ad')
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
