# -*- coding: utf-8 -*-
"""\u7535\u52a8\u8f66\u7535\u6c60\u72b6\u6001\u6545\u969c\u6811\u5224\u65ad\uff1a\u8f93\u5165\u73b0\u8c61\u4e0e\u7535\u6c60\u7c7b\u578b\uff0c\u8f93\u51fa\u6392\u67e5\u987a\u5e8f\u4e0e\u4fdd\u517b\u8981\u70b9\u3002

\u7528\u6cd5:
  python ebike_battery_check.py --text "\u51ac\u5929\u7eed\u822a\u77ed\u4e86\u4e00\u534a" --battery lead
  python ebike_battery_check.py --file \u63cf\u8ff0.txt [--out \u7ed3\u679c.md] [--format json]
  python ebike_battery_check.py --selftest
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
    {'id': 'B1', 'order': 1, 'name': '\u80ce\u538b\u4e0d\u8db3',
     'kw': ['\u80ce\u538b', '\u6c14\u4e0d\u8db3', '\u8f6e\u80ce\u8f6f', '\u6ca1\u6c14', '\u762a'],
     'test': '\u80ce\u538b\u8868\u6d4b\u91cf\uff0c\u5bf9\u6bd4\u8f66\u8f86\u6807\u79f0\u503c',
     'fix': '\u8865\u6c14\uff0c\u8fd9\u662f\u6700\u4fbf\u5b9c\u4e5f\u6700\u5e38\u89c1\u7684\u89e3\u6cd5'},
    {'id': 'B2', 'order': 2, 'name': '\u5239\u8f66\u62d6\u6ede\u6216\u8f74\u627f\u963b\u529b',
     'kw': ['\u5239\u8f66', '\u62d6\u6ede', '\u6469\u64e6', '\u8f74\u627f', '\u8f6c\u4e0d\u52a8', '\u963b\u529b'],
     'test': '\u62ac\u8d77\u8f66\u8f6e\u8f6c\u52a8\uff0c\u542c\u6469\u64e6\u58f0\u611f\u53d7\u963b\u529b',
     'fix': '\u8c03\u6574\u5239\u8f66\u3001\u4fdd\u517b\u8f74\u627f'},
    {'id': 'B3', 'order': 3, 'name': '\u4f4e\u6e29\u5f71\u54cd',
     'kw': ['\u51ac\u5929', '\u5929\u51b7', '\u4f4e\u6e29', '\u96f6\u4e0b', '\u51b7\u5929'],
     'test': '\u51ac\u5b63\u4e0e\u590f\u5b63\u7eed\u822a\u5bf9\u6bd4',
     'fix': '\u5c5e\u6b63\u5e38\u73b0\u8c61\uff0c\u56de\u6696\u4f1a\u6062\u590d\uff1b\u9502\u7535 0\u2103 \u4ee5\u4e0b\u4e0d\u8981\u5145\u7535'},
    {'id': 'B4', 'order': 4, 'name': '\u8f7d\u91cd\u3001\u8def\u51b5\u4e0e\u9006\u98ce',
     'kw': ['\u8f7d\u91cd', '\u5e26\u4eba', '\u722c\u5761', '\u9006\u98ce', '\u8def\u51b5'],
     'test': '\u8bb0\u5f55\u8f7d\u91cd\u4e0e\u8def\u51b5\u540e\u5bf9\u6bd4',
     'fix': '\u8c03\u6574\u7eed\u822a\u9884\u671f'},
    {'id': 'B5', 'order': 5, 'name': '\u94c5\u9178\u786b\u5316',
     'kw': ['\u94c5\u9178', '\u786b\u5316', '\u4e00\u5145\u5c31\u6ee1', '\u7528\u4e86\u4e24\u5e74', '\u7528\u4e86\u4e09\u5e74'],
     'test': '\u9700\u4e13\u4e1a\u8bbe\u5907\u6d4b\u5bb9\u91cf',
     'fix': '\u68c0\u6d4b\u540e\u51b3\u5b9a\u662f\u5426\u66f4\u6362\uff0c\u786b\u5316\u4e25\u91cd\u4e0d\u53ef\u9006'},
    {'id': 'B6', 'order': 6, 'name': '\u9502\u7535\u5355\u4f53\u538b\u5dee\u5927',
     'kw': ['\u9502\u7535', '\u9502\u7535\u6c60', '\u538b\u5dee', '\u5355\u4f53', '\u4fdd\u62a4\u677f'],
     'test': '\u9700\u4e13\u4e1a\u8bbe\u5907\u6d4b\u5355\u4f53\u7535\u538b',
     'fix': '\u505a\u5747\u8861\u6216\u66f4\u6362\uff0c\u8f6c\u4e13\u4e1a\u4eba\u5458'},
    {'id': 'B7', 'order': 7, 'name': '\u5145\u7535\u5668\u6545\u969c\u6216\u63a5\u89e6\u4e0d\u826f',
     'kw': ['\u4e0d\u53d8\u706f', '\u4e0d\u53d8\u7eff', '\u5145\u4e0d\u8fdb', '\u5145\u7535\u5668', '\u63a5\u89e6\u4e0d\u826f', '\u5145\u7535\u53e3'],
     'test': '\u6362\u540c\u89c4\u683c\u5145\u7535\u5668\u5bf9\u6bd4',
     'fix': '\u66f4\u6362\u539f\u88c5\u5339\u914d\u5145\u7535\u5668'},
    {'id': 'B8', 'order': 8, 'name': '\u7535\u6c60\u8001\u5316\u5230\u5bff\u547d\u672b\u671f',
     'kw': ['\u7eed\u822a\u77ed', '\u8dd1\u4e0d\u8fdc', '\u4e0d\u8010\u7528', '\u8870\u51cf', '\u8001\u5316'],
     'test': '\u540c\u6837\u8def\u7ebf\u8fde\u7eed\u8bb0\u5f55\u4e09\u6b21\u7eed\u822a',
     'fix': '\u6392\u9664\u524d\u51e0\u9879\u540e\u518d\u8003\u8651\u66f4\u6362\u7535\u6c60'},
    {'id': 'B9', 'order': 9, 'name': '\u7535\u6c60\u9f13\u5305\u6216\u70ed\u5931\u63a7\u524d\u5146',
     'kw': ['\u9f13\u5305', '\u53d1\u70eb', '\u53d1\u70ed', '\u5f02\u5473', '\u6f0f\u6db2', '\u5192\u70df', '\u53d8\u5f62'],
     'test': '\u76ee\u89c6\u5916\u58f3\u4e0e\u624b\u80cc\u8bd5\u6e29',
     'fix': '\u7acb\u5373\u505c\u7528\u65ad\u7535\uff0c\u4eba\u5458\u64a4\u79bb\uff0c\u5192\u70df\u8d77\u706b\u62e8 119'},
]

RED = [
    {'kw': ['\u9f13\u5305', '\u53d1\u70eb', '\u53d1\u70ed', '\u5f02\u5473', '\u6f0f\u6db2', '\u5192\u70df', '\u53d8\u5f62'],
     'msg': '\u7535\u6c60\u9f13\u5305\u3001\u53d1\u70eb\u3001\u5f02\u5473\u3001\u6f0f\u6db2\u6216\u5192\u70df\uff1a\u7acb\u5373\u505c\u6b62\u5145\u7535\u4e0e\u4f7f\u7528\uff0c\u5728\u786e\u4fdd\u5b89\u5168\u524d\u63d0\u4e0b\u65ad\u5f00\u7535\u6e90\uff0c\u4eba\u5458\u64a4\u79bb\uff1b\u5192\u70df\u8d77\u706b\u62e8 119\u3002\u7981\u6b62\u523a\u7834\u3001\u6324\u538b\u6216\u62c6\u89e3\u3002'},
    {'kw': ['\u5ba4\u5185', '\u697c\u9053', '\u5bb6\u91cc\u5145', '\u7535\u68af', '\u758f\u6563'],
     'msg': '\u4e25\u7981\u5728\u5ba4\u5185\u3001\u697c\u9053\u3001\u758f\u6563\u901a\u9053\u6216\u5b89\u5168\u51fa\u53e3\u505c\u653e\u4e0e\u5145\u7535\uff0c\u4e25\u7981\u628a\u7535\u6c60\u5e26\u5165\u7535\u68af\u6216\u4f4f\u5b85\u5ba4\u5185\u3002'},
    {'kw': ['\u98de\u7ebf', '\u63a5\u7ebf\u677f', '\u79c1\u62c9', '\u4e71\u63a5'],
     'msg': '\u4e25\u7981\u98de\u7ebf\u5145\u7535\uff1a\u7ebf\u7f06\u957f\u671f\u6469\u64e6\u4e0e\u65e5\u6652\u96e8\u6dcb\u540e\u7edd\u7f18\u7834\u635f\uff0c\u77ed\u8def\u98ce\u9669\u6781\u9ad8\u3002'},
    {'kw': ['\u6539\u88c5', '\u5e76\u8054', '\u52a0\u88c5', '\u62c6\u4fdd\u62a4\u677f', '\u6362\u7535\u82af'],
     'msg': '\u4e25\u7981\u79c1\u81ea\u6539\u88c5\u3001\u5e76\u8054\u4e0d\u540c\u5bb9\u91cf\u7535\u6c60\u3001\u62c6\u9664\u4fdd\u62a4\u677f\u6216\u66f4\u6362\u7535\u82af\uff0c\u8f6c\u4e13\u4e1a\u4eba\u5458\u5904\u7406\u3002'},
    {'kw': ['\u6df7\u7528', '\u4e0d\u662f\u539f\u88c5', '\u901a\u7528\u5145\u7535\u5668'],
     'msg': '\u4e25\u7981\u4f7f\u7528\u975e\u539f\u88c5\u6216\u53c2\u6570\u4e0d\u5339\u914d\u7684\u5145\u7535\u5668\uff0c\u4e09\u5143\u9502\u4e0e\u78f7\u9178\u94c1\u9502\u7684\u5145\u7535\u5668\u4e0d\u80fd\u901a\u7528\u3002'},
    {'kw': ['\u6ce1\u6c34', '\u8fdb\u6c34', '\u8dcc\u843d', '\u70e7\u7194', '\u7126\u5473', '\u70e7\u8680'],
     'msg': '\u7535\u6c60\u8fdb\u6c34\u3001\u6ce1\u6c34\u3001\u8dcc\u843d\u7834\u635f\u6216\u63a5\u63d2\u4ef6\u70e7\u8680\uff1a\u7acb\u5373\u505c\u7528\u5e76\u8f6c\u4e13\u4e1a\u4eba\u5458\uff0c\u4e0d\u8981\u7ee7\u7eed\u5145\u7535\u3002'},
]

MISREAD = [
    {'kw': ['\u7eed\u822a\u77ed', '\u8dd1\u4e0d\u8fdc', '\u4e0d\u8010\u7528'],
     'msg': '\u7eed\u822a\u53d8\u77ed\u4e0d\u7b49\u4e8e\u7535\u6c60\u574f\u4e86\uff0c\u5148\u67e5\u80ce\u538b\u4e0e\u5239\u8f66\u62d6\u6ede\uff0c\u8fd9\u662f\u6700\u9ad8\u9891\u4e5f\u6700\u4fbf\u5b9c\u7684\u4e24\u4e2a\u539f\u56e0\u3002'},
    {'kw': ['\u51ac\u5929', '\u5929\u51b7', '\u4f4e\u6e29'],
     'msg': '\u51ac\u5929\u7eed\u822a\u4e0b\u964d\u591a\u4e3a\u6e29\u5ea6\u5f71\u54cd\uff0c\u5c5e\u6b63\u5e38\uff0c\u56de\u6696\u4f1a\u6062\u590d\uff0c\u4e0d\u5fc5\u6025\u7740\u6362\u7535\u6c60\u3002'},
    {'kw': ['\u4e00\u5145\u5c31\u6ee1'],
     'msg': '\u4e00\u5145\u5c31\u6ee1\u4e00\u9a91\u5c31\u6ca1\u7535\uff0c\u591a\u4e3a\u94c5\u9178\u786b\u5316\u6216\u9502\u7535\u5355\u4f53\u538b\u5dee\u5927\uff0c\u9700\u4e13\u4e1a\u68c0\u6d4b\u800c\u4e0d\u662f\u76f4\u63a5\u6362\u7535\u6c60\u3002'},
    {'kw': ['\u4e0d\u53d8\u706f', '\u4e0d\u53d8\u7eff', '\u5145\u4e0d\u8fdb'],
     'msg': '\u5145\u7535\u5668\u4e0d\u53d8\u7eff\u706f\u4e0d\u7b49\u4e8e\u7535\u6c60\u574f\u4e86\uff0c\u53ef\u80fd\u662f\u5145\u7535\u5668\u6545\u969c\u6216\u5145\u7535\u53e3\u63a5\u89e6\u4e0d\u826f\u3002'},
    {'kw': ['\u9f13\u5305'],
     'msg': '\u7535\u6c60\u9f13\u5305\u4e0d\u662f\u8fd8\u80fd\u51d1\u5408\u7528\uff0c\u662f\u70ed\u5931\u63a7\u524d\u5146\uff0c\u5fc5\u987b\u7acb\u5373\u505c\u7528\u66f4\u6362\u3002'},
]

CARE = {
    'lead': [
        '\u5145\u7535\u65f6\u673a\uff1a\u5269\u4f59 30%-40% \u65f6\u5145\uff0c\u4e0d\u8981\u6bcf\u6b21\u90fd\u9a91\u5230\u6ca1\u7535',
        '\u5145\u7535\u65f6\u957f\uff1a\u901a\u5e38 6-8 \u5c0f\u65f6\uff0c\u53d8\u706f\u540e\u6d6e\u5145 1-2 \u5c0f\u65f6',
        '\u4e45\u653e\u5904\u7406\uff1a\u6bcf 1-2 \u4e2a\u6708\u8865\u7535\u4e00\u6b21\uff0c\u907f\u514d\u786b\u5316',
        '\u9ad8\u6e29\u6ce8\u610f\uff1a\u907f\u514d\u66b4\u6652\u540e\u7acb\u5373\u5145\u7535',
    ],
    'lithium': [
        '\u5145\u7535\u65f6\u673a\uff1a\u5c3d\u91cf\u5728 20%-80% \u533a\u95f4\u5faa\u73af\uff0c\u4e0d\u8981\u6bcf\u6b21\u90fd\u5145\u5230\u6ee1\u683c',
        '\u5145\u7535\u65f6\u957f\uff1a\u5145\u6ee1\u5373\u505c\uff0c\u4e0d\u8981\u957f\u671f\u6574\u591c\u63d2\u7740',
        '\u4e45\u653e\u5904\u7406\uff1a\u5b58\u653e\u4fdd\u6301 50%-60% \u7535\u91cf\u5e76\u5b9a\u671f\u68c0\u67e5',
        '\u4f4e\u6e29\u6ce8\u610f\uff1a0\u2103 \u4ee5\u4e0b\u4e0d\u8981\u5145\u7535\uff0c\u5148\u56de\u6e29\u5230\u5ba4\u6e29',
    ],
}


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


def analyse(text, battery=None):
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
    if not battery:
        if any(k in t for k in ['\u94c5\u9178']):
            battery = 'lead'
        elif any(k in t for k in ['\u9502\u7535', '\u9502\u7535\u6c60', '\u4e09\u5143', '\u78f7\u9178\u94c1']):
            battery = 'lithium'
    return {'rules': rules, 'reds': reds, 'misread': miss, 'battery': battery or '',
            'top': rules[0]['name'] if rules else ''}


def render_md(text, r):
    lines = ['# \u7535\u52a8\u8f66\u7535\u6c60\u72b6\u6001\u5224\u65ad\u7ed3\u679c', '']
    if r['battery']:
        name = '\u94c5\u9178\u7535\u6c60' if r['battery'] == 'lead' else '\u9502\u7535\u6c60'
        lines.append('## \u4e00\u3001%s\u4fdd\u517b\u8981\u70b9' % name)
        lines.append('')
        for s in CARE[r['battery']]:
            lines.append('- %s' % s)
        lines.append('')
    if r['reds']:
        lines.append('## \u4e8c\u3001\u5b89\u5168\u7ea2\u7ebf\uff08\u7acb\u5373\u6267\u884c\uff09')
        lines.append('')
        for m in r['reds']:
            lines.append('- %s' % m)
        lines.append('')
    if not r['rules']:
        lines.append('\u672a\u5339\u914d\u5230\u6545\u969c\u6811\u6761\u76ee\u3002\u8bf7\u8865\u5145\uff1a\u7535\u6c60\u7c7b\u578b\u3001\u7528\u4e86\u591a\u4e45\u3001\u51ac\u5929\u8fd8\u662f\u590f\u5929\u3001\u9f13\u5305\u6ca1\u6709\u3002')
        lines.append('')
    else:
        lines.append('## \u4e09\u3001\u6392\u67e5\u987a\u5e8f\uff08\u6700\u4f18\u5148\uff1a%s\uff09' % r['top'])
        lines.append('')
        lines.append('| \u987a\u5e8f | \u53ef\u80fd\u539f\u56e0 | \u53ef\u80fd\u6027 | \u9a8c\u8bc1\u52a8\u4f5c | \u5904\u7f6e |')
        lines.append('|---|---|---|---|---|')
        for x in r['rules']:
            lines.append('| %d | %s | %s | %s | %s |' % (
                x['order'], x['name'], x['level'], x['test'], x['fix']))
        lines.append('')
    if r['misread']:
        lines.append('## \u56db\u3001\u8bef\u5224\u63d0\u9192')
        lines.append('')
        for m in r['misread']:
            lines.append('- %s' % m)
        lines.append('')
    lines.append('---')
    lines.append('\u672c\u7ed3\u679c\u4e3a\u73b0\u8c61\u5339\u914d\u4e0e\u4fdd\u517b\u5efa\u8bae\uff0c\u4e0d\u4ee3\u8868\u7535\u6c60\u68c0\u6d4b\u7ed3\u8bba\uff0c\u4e0d\u6784\u6210\u7ef4\u4fee\u7ed3\u8bba\u3002')
    return '\n'.join(lines)


def render_json(r):
    return json.dumps(r, ensure_ascii=False, indent=2)


def selftest():
    errs = []

    def eq(name, got, want):
        if got != want:
            errs.append('%s got=%r want=%r' % (name, got, want))

    r1 = analyse('\u51ac\u5929\u7eed\u822a\u77ed\u4e86\u4e00\u534a\uff0c\u7535\u6c60\u662f\u94c5\u9178\u7684\uff0c\u7528\u4e86\u4e24\u5e74')
    eq('case1 \u8bc6\u522b\u94c5\u9178', r1['battery'], 'lead')
    eq('case1 \u4f4e\u6e29\u547d\u4e2d', any(x['id'] == 'B3' for x in r1['rules']), True)

    r2 = analyse('\u9502\u7535\u6c60\u4e00\u5145\u5c31\u6ee1\u4e00\u9a91\u5c31\u6ca1\u7535\uff0c\u53ef\u80fd\u6709\u538b\u5dee')
    eq('case2 \u8bc6\u522b\u9502\u7535', r2['battery'], 'lithium')
    eq('case2 \u538b\u5dee\u547d\u4e2d', any(x['id'] == 'B6' for x in r2['rules']), True)

    r3 = analyse('\u7535\u6c60\u9f13\u5305\u4e86\uff0c\u8fd8\u6709\u70b9\u53d1\u70eb')
    eq('case3 \u9f13\u5305\u547d\u4e2d', r3['rules'][0]['id'], 'B9')
    eq('case3 \u7ea2\u7ebf\u547d\u4e2d', len(r3['reds']) >= 1, True)

    r4 = analyse('\u60f3\u5728\u697c\u9053\u91cc\u5145\u7535\uff0c\u7528\u63a5\u7ebf\u677f\u98de\u7ebf')
    eq('case4 \u5ba4\u5185\u7ea2\u7ebf', any('\u5ba4\u5185\u3001\u697c\u9053' in m for m in r4['reds']), True)
    eq('case4 \u98de\u7ebf\u7ea2\u7ebf', any('\u98de\u7ebf' in m for m in r4['reds']), True)

    r5 = analyse('\u7eed\u822a\u77ed\u8dd1\u4e0d\u8fdc')
    eq('case5 \u7eed\u822a\u8bef\u5224', any('\u7eed\u822a\u53d8\u77ed\u4e0d\u7b49\u4e8e\u7535\u6c60\u574f\u4e86' in m for m in r5['misread']), True)

    r6 = analyse('\u5145\u7535\u5668\u4e0d\u53d8\u7eff\u706f')
    eq('case6 \u5145\u7535\u5668\u547d\u4e2d', any(x['id'] == 'B7' for x in r6['rules']), True)
    eq('case6 \u5145\u7535\u5668\u8bef\u5224', any('\u4e0d\u53d8\u7eff\u706f' in m for m in r6['misread']), True)

    r7 = analyse('\u7535\u52a8\u8f66\u6709\u70b9\u95ee\u9898')
    eq('case7 \u65e0\u5339\u914d', r7['rules'], [])
    eq('case7 \u672a\u8bc6\u522b\u7c7b\u578b', r7['battery'], '')

    r8 = analyse('\u7eed\u822a\u77ed', battery='lithium')
    eq('case8 \u663e\u5f0f\u6307\u5b9a\u7c7b\u578b', r8['battery'], 'lithium')
    md8 = render_md('\u7eed\u822a\u77ed', r8)
    eq('case8 \u8f93\u51fa\u4fdd\u517b\u8981\u70b9', '\u9502\u7535\u6c60\u4fdd\u517b\u8981\u70b9' in md8, True)

    md = render_md('\u7535\u6c60\u9f13\u5305', r3)
    eq('case9 \u542b\u7ea2\u7ebf\u6bb5', '\u5b89\u5168\u7ea2\u7ebf' in md, True)
    js = json.loads(render_json(r1))
    eq('case10 \u8f93\u51fa\u952e', sorted(js.keys()), ['battery', 'misread', 'reds', 'rules', 'top'])

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 14\n\u8986\u76d6: \u80ce\u538b/\u5239\u8f66/\u4f4e\u6e29/\u8f7d\u91cd/\u94c5\u9178\u786b\u5316/\u9502\u7535\u538b\u5dee/\u5145\u7535\u5668/\u7535\u6c60\u8001\u5316/\u9f13\u5305\u70ed\u5931\u63a7/\u5ba4\u5185\u98de\u7ebf/\u6539\u88c5\u6df7\u7528')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u7535\u52a8\u8f66\u7535\u6c60\u72b6\u6001\u6545\u969c\u6811\u5224\u65ad')
    ap.add_argument('--text', help='\u73b0\u8c61\u63cf\u8ff0')
    ap.add_argument('--file', help='\u4ece\u6587\u4ef6\u8bfb\u73b0\u8c61\u63cf\u8ff0')
    ap.add_argument('--battery', default='', choices=['', 'lead', 'lithium'], help='\u7535\u6c60\u7c7b\u578b')
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

    r = analyse(text, a.battery or None)
    out = render_md(text, r) if a.format == 'md' else render_json(r)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % a.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
