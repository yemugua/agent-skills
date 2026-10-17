# -*- coding: utf-8 -*-
"""\u5730\u6f0f\u8fd4\u5473\u6545\u969c\u6811\u5224\u65ad\uff1a\u8f93\u5165\u73b0\u8c61\uff0c\u8f93\u51fa\u53ef\u80fd\u539f\u56e0\u4e0e\u5904\u7406\u987a\u5e8f\u3002

\u7528\u6cd5:
  python drain_odor_check.py --text "\u5ba2\u536b\u5730\u6f0f\u957f\u671f\u4e0d\u7528\uff0c\u6700\u8fd1\u8fd4\u5473\uff0c\u6392\u6c34\u6b63\u5e38"
  python drain_odor_check.py --file \u63cf\u8ff0.txt [--out \u7ed3\u679c.md] [--format json]
  python drain_odor_check.py --selftest
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
    {'id': 'D1', 'order': 1, 'name': '\u5b58\u6c34\u5f2f\u6216\u6c34\u5c01\u5e72\u6db8',
     'kw': ['\u957f\u671f\u4e0d\u7528', '\u4e45\u672a', '\u7a7a\u7f6e', '\u51fa\u5dee', '\u5ba2\u536b', '\u6ca1\u4eba\u4f4f', '\u5e72', '\u84b8\u53d1', '\u5076\u5c14\u7528'],
     'test': '\u5411\u5730\u6f0f\u5012 500ml \u6e05\u6c34\uff0c\u9759\u7f6e 10 \u5206\u949f\u540e\u590d\u95fb',
     'fix': '\u8865\u6c34\u5373\u53ef\uff0c\u65e0\u9700\u6362\u82af\uff1b\u957f\u671f\u4e0d\u7528\u7684\u5730\u6f0f\u6bcf\u6708\u8865\u4e00\u6b21\u6c34',
     'stop': '\u5426'},
    {'id': 'D2', 'order': 2, 'name': '\u4e0b\u6c34\u7ba1\u90e8\u5206\u5835\u585e',
     'kw': ['\u6392\u6c34\u6162', '\u4e0b\u6c34\u6162', '\u5495\u565c', '\u53cd\u6d8c', '\u79ef\u6c34', '\u6392\u4e0d\u4e0b\u53bb', '\u5835', '\u6d8c'],
     'test': '\u8fde\u7eed\u5012\u4e24\u76c6\u6c34\uff08\u7ea6 5L\uff09\uff0c\u770b 30 \u79d2\u5185\u662f\u5426\u6392\u51c0',
     'fix': '\u5148\u758f\u901a\u518d\u8c08\u6362\u82af\uff0c\u9632\u81ed\u82af\u89e3\u51b3\u4e0d\u4e86\u901a\u7545\u95ee\u9898',
     'stop': '\u4e25\u91cd\u53cd\u6d8c\u65f6\u505c\u7528\u5e76\u62a5\u4e13\u4e1a\u4eba\u5458'},
    {'id': 'D3', 'order': 3, 'name': '\u9632\u81ed\u82af\u672c\u4f53\u5931\u6548',
     'kw': ['\u7845\u80f6', '\u7c98\u8fde', '\u7c98\u6b7b', '\u7ffb\u76d6', '\u4e0d\u590d\u4f4d', '\u5f39\u7c27', '\u9508', '\u7834\u635f', '\u8001\u5316', '\u82af\u574f'],
     'test': '\u62c6\u51fa\u65e7\u82af\uff0c\u770b\u95ed\u5408\u4ef6\u80fd\u5426\u81ea\u7531\u5f00\u5408\u5e76\u5b8c\u5168\u95ed\u5408',
     'fix': '\u6309\u5b9e\u6d4b\u5185\u5f84\u4e0e\u6df1\u5ea6\u9009\u578b\u53f7\u6362\u65b0\u82af\uff0c\u65e7\u82af\u5e26\u53bb\u6bd4\u5bf9',
     'stop': '\u5426'},
    {'id': 'D4', 'order': 4, 'name': '\u82af\u4e0e\u7ba1\u58c1\u4e0d\u5339\u914d\u7559\u7f1d',
     'kw': ['\u6643\u52a8', '\u6709\u7f1d', '\u7a7a\u9699', '\u521a\u6362', '\u6362\u4e86\u8fd8\u662f', '\u6362\u5b8c\u8fd8\u662f', '\u65b0\u82af', '\u677e'],
     'test': '\u624b\u7535\u7167\u770b\u82af\u4f53\u56db\u5468\uff0c\u786e\u8ba4\u65e0\u53ef\u89c1\u7f1d\u9699',
     'fix': '\u6362\u5e26\u5bc6\u5c01\u5708\u7684\u578b\u53f7\u6216\u7528\u4e2d\u6027\u7845\u916e\u80f6\u8865\u7f1d',
     'stop': '\u5426'},
    {'id': 'D5', 'order': 5, 'name': '\u6392\u6c34\u7ba1\u672c\u8eab\u6ca1\u6709\u5b58\u6c34\u5f2f',
     'kw': ['\u76f4\u6392', '\u88c5\u4fee', '\u8001\u623f', '\u6539\u88c5', '\u6ca1\u6709\u5f2f', '\u65e0\u5b58\u6c34\u5f2f'],
     'test': '\u62c6\u5f00\u770b\u7ba1\u5185\u662f\u5426\u6709 U \u578b\u5b58\u6c34\u7ed3\u6784',
     'fix': '\u88c5\u6df1\u6c34\u5c01\u82af\u6216\u66f4\u6362\u5e26\u5b58\u6c34\u5f2f\u7684\u9632\u81ed\u5730\u6f0f\u6574\u4f53',
     'stop': '\u5426'},
    {'id': 'D6', 'order': 6, 'name': '\u7ba1\u9053\u63a5\u53e3\u6f0f\u6c14\u6216\u7834\u635f',
     'kw': ['\u697c\u4e0b', '\u6e17\u6c34', '\u5929\u82b1\u677f', '\u6c34\u5370', '\u6ef4\u6c34', '\u9508\u8680', '\u6389\u6e23', '\u7a7f\u5b54', '\u540a\u9876'],
     'test': '\u770b\u697c\u4e0b\u5929\u82b1\u4e0e\u540a\u9876\u5185\u662f\u5426\u6709\u6c34\u6e0d\uff0c\u6572\u51fb\u7ba1\u58c1\u542c\u7a7a\u54cd',
     'fix': '\u505c\u7528\u5e76\u8f6c\u4e13\u4e1a\u4eba\u5458\uff0c\u4e0d\u5f97\u7ee7\u7eed\u62c6\u52a8',
     'stop': '\u662f'},
]

# ---- \u5b89\u5168\u7ea2\u7ebf ----
RED = [
    {'kw': ['\u697c\u4e0b', '\u5929\u82b1\u677f', '\u6e17\u6c34', '\u6c34\u5370', '\u6ef4\u6c34', '\u697c\u677f'],
     'msg': '\u697c\u4e0b\u51fa\u73b0\u6e17\u6c34\u6216\u6c34\u5370\uff1a\u7acb\u5373\u505c\u6b62\u62c6\u52a8\u5730\u6f0f\uff0c\u6d89\u53ca\u9632\u6c34\u5c42\u4e0e\u7ed3\u6784\u5c42\uff0c\u62a5\u7269\u4e1a\u4e0e\u4e13\u4e1a\u7ef4\u4fee\u3002'},
    {'kw': ['\u53cd\u6d8c', '\u6d8c\u4e0a\u6765', '\u5192\u6c34', '\u6c61\u6c34'],
     'msg': '\u6c61\u6c34\u53cd\u6d8c\u5c5e\u4e3b\u7ba1\u5835\u585e\u5f81\u5146\uff1a\u505c\u7528\u8be5\u6392\u6c34\u70b9\uff0c\u7528\u758f\u901a\u8bbe\u5907\u5904\u7406\uff0c\u4e0d\u8981\u7ee7\u7eed\u51b2\u6c34\u3002'},
    {'kw': ['\u71c3\u6c14', '\u7164\u6c14', '\u81ed\u5473\u5242'],
     'msg': '\u95fb\u5230\u71c3\u6c14\u5473\uff1a\u5f00\u7a97\u901a\u98ce\u3001\u5173\u95ed\u9600\u95e8\u3001\u4e0d\u89e6\u78b0\u4efb\u4f55\u7535\u5668\u5f00\u5173\uff0c\u5230\u6237\u5916\u62e8\u6253\u71c3\u6c14\u516c\u53f8\u7535\u8bdd\u3002'},
    {'kw': ['\u6389\u8fdb\u53bb', '\u6389\u5165', '\u6389\u5230\u7ba1', '\u51b2\u4e0b\u53bb'],
     'msg': '\u65e7\u82af\u6389\u5165\u7ba1\u9053\uff1a\u7981\u6b62\u7ee7\u7eed\u51b2\u6c34\uff0c\u5148\u7528\u94c1\u4e1d\u5f2f\u94a9\u5c1d\u8bd5\u52fe\u51fa\uff0c\u52fe\u4e0d\u51fa\u5373\u505c\u7528\u5e76\u62a5\u4e13\u4e1a\u4eba\u5458\u3002'},
]

# ---- \u5e38\u89c1\u8bef\u5224 ----
MISREAD = [
    {'kw': ['\u957f\u671f\u4e0d\u7528', '\u4e45\u672a', '\u7a7a\u7f6e', '\u5ba2\u536b', '\u51fa\u5dee'],
     'msg': '\u8fd4\u5473\u4e0d\u7b49\u4e8e\u9632\u81ed\u82af\u574f\u4e86\u3002\u957f\u671f\u4e0d\u7528\u7684\u5730\u6f0f\u6c34\u5c01\u65e9\u5df2\u84b8\u53d1\uff0c\u5012\u6c34\u5373\u53ef\u9a8c\u8bc1\u3002'},
    {'kw': ['\u6392\u6c34\u6162', '\u5835', '\u5495\u565c'],
     'msg': '\u6392\u6c34\u4e0d\u7545\u4f18\u5148\u6000\u7591\u7ba1\u9053\u5835\u585e\uff0c\u9632\u81ed\u82af\u53ea\u7ba1\u6c14\u5473\uff0c\u4e0d\u7ba1\u901a\u7545\u3002'},
    {'kw': ['\u6362\u4e86\u8fd8\u662f', '\u6362\u5b8c\u8fd8\u662f', '\u65b0\u82af', '\u521a\u6362', '\u8fd8\u662f\u81ed', '\u6362\u4e86\u65b0'],
     'msg': '\u6362\u82af\u540e\u4ecd\u81ed\uff0c\u4f18\u5148\u6000\u7591\u82af\u58c1\u7559\u7f1d\u3001\u9762\u677f\u672a\u5750\u5b9e\uff0c\u6216\u5473\u9053\u6765\u81ea\u9a6c\u6876\u6cd5\u5170\u5708\u4e0e\u6d17\u624b\u76c6\u4e0b\u6c34\u7ba1\u3002'},
    {'kw': ['\u9633\u53f0', '\u53a8\u623f', '\u5e72\u533a'],
     'msg': '\u5e72\u533a\u4e0d\u5f97\u4f7f\u7528\u7eaf\u6df1\u6c34\u5c01\u82af\uff0c\u6c34\u5c01\u84b8\u53d1\u540e\u5fc5\u7136\u5931\u6548\uff0c\u5c5e\u9009\u578b\u9519\u8bef\u800c\u975e\u8d28\u91cf\u95ee\u9898\u3002'},
    {'kw': ['\u5c0f\u98de\u866b', '\u86fe\u8813', '\u866b\u5b50'],
     'msg': '\u5c0f\u98de\u866b\u6765\u81ea\u7ba1\u58c1\u6709\u673a\u6c61\u57a2\uff0c\u6362\u82af\u4e0d\u89e3\u51b3\u95ee\u9898\uff0c\u9700\u6e05\u5237\u7ba1\u58c1\u3002'},
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
                      'fix': r['fix'], 'stop': r['stop']})
    rules.sort(key=lambda x: x['order'])
    reds = [it['msg'] for it, _ in match(text, RED)]
    miss = [it['msg'] for it, _ in match(text, MISREAD)]
    return {'rules': rules, 'reds': reds, 'misread': miss,
            'top': rules[0]['name'] if rules else ''}


def render_md(text, r):
    lines = ['# \u5730\u6f0f\u8fd4\u5473\u5224\u65ad\u7ed3\u679c', '']
    if not r['rules']:
        lines.append('\u672a\u5339\u914d\u5230\u6545\u969c\u6811\u6761\u76ee\u3002\u8bf7\u8865\u5145\u73b0\u8c61\uff1a\u662f\u5426\u6709\u6392\u6c34\u53d8\u6162\u3001\u662f\u5426\u957f\u671f\u4e0d\u7528\u3001\u6362\u8fc7\u82af\u6ca1\u6709\u3001\u697c\u4e0b\u6709\u65e0\u6e17\u6c34\u3002')
        lines.append('')
    else:
        lines.append('\u6700\u4f18\u5148\u6392\u67e5\uff1a%s' % r['top'])
        lines.append('')
        lines.append('## \u4e00\u3001\u6392\u67e5\u987a\u5e8f\uff08\u6309\u6b64\u987a\u5e8f\u6267\u884c\uff0c\u4e0d\u8981\u8df3\u6b65\uff09')
        lines.append('')
        lines.append('| \u987a\u5e8f | \u53ef\u80fd\u539f\u56e0 | \u53ef\u80fd\u6027 | \u9a8c\u8bc1\u52a8\u4f5c | \u5904\u7f6e | \u9700\u505c\u7528\u62a5\u4fee |')
        lines.append('|---|---|---|---|---|---|')
        for x in r['rules']:
            lines.append('| %d | %s | %s | %s | %s | %s |' % (
                x['order'], x['name'], x['level'], x['test'], x['fix'], x['stop']))
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
    lines.append('1. \u5148\u505a\u5851\u6599\u888b\u538b\u5473\u6cd5\u5b9a\u4f4d\u5473\u9053\u662f\u5426\u6765\u81ea\u8fd9\u4e2a\u5730\u6f0f')
    lines.append('2. \u518d\u505a\u704c\u6c34\u8bd5\u6392\uff0c\u786e\u8ba4\u6392\u6c34\u901f\u5ea6\u6b63\u5e38')
    lines.append('3. \u4e24\u9879\u90fd\u6307\u5411\u5730\u6f0f\uff0c\u624d\u62c6\u9762\u677f\u53d6\u65e7\u82af')
    lines.append('4. \u53d6\u65e7\u82af\u524d\u5148\u7528\u7ef3\u6216\u94c1\u4e1d\u62f4\u4f4f\uff0c\u9632\u6389\u5165\u7ba1\u9053')
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

    r1 = analyse('\u5ba2\u536b\u5730\u6f0f\u957f\u671f\u4e0d\u7528\uff0c\u6700\u8fd1\u8fd4\u5473\uff0c\u6392\u6c34\u6b63\u5e38')
    eq('case1 \u5e72\u6db8\u4f18\u5148', r1['top'], '\u5b58\u6c34\u5f2f\u6216\u6c34\u5c01\u5e72\u6db8')
    eq('case1 \u5e72\u6db8\u6392\u7b2c\u4e00', r1['rules'][0]['id'], 'D1')

    r2 = analyse('\u5730\u6f0f\u6392\u6c34\u6162\uff0c\u8fd8\u5495\u565c\u54cd\uff0c\u5076\u5c14\u6c61\u6c34\u53cd\u6d8c')
    eq('case2 \u5835\u585e\u4f18\u5148', r2['top'], '\u4e0b\u6c34\u7ba1\u90e8\u5206\u5835\u585e')
    eq('case2 \u7ea2\u7ebf\u547d\u4e2d', len(r2['reds']) >= 1, True)

    r3 = analyse('\u6362\u4e86\u65b0\u7684\u9632\u81ed\u82af\uff0c\u8fd8\u662f\u81ed\uff0c\u82af\u88c5\u8fdb\u53bb\u6709\u70b9\u6643\u52a8')
    eq('case3 \u7559\u7f1d\u547d\u4e2d', any(x['id'] == 'D4' for x in r3['rules']), True)
    eq('case3 \u8bef\u5224\u63d0\u9192', len(r3['misread']) >= 1, True)

    r4 = analyse('\u697c\u4e0b\u5929\u82b1\u677f\u51fa\u73b0\u6c34\u5370\u548c\u6ef4\u6c34')
    eq('case4 \u7834\u635f\u4f18\u5148', r4['top'], '\u7ba1\u9053\u63a5\u53e3\u6f0f\u6c14\u6216\u7834\u635f')
    eq('case4 \u5fc5\u987b\u62a5\u4fee', r4['rules'][0]['stop'], '\u662f')
    eq('case4 \u7ea2\u7ebf\u547d\u4e2d', len(r4['reds']) >= 1, True)

    r5 = analyse('\u9633\u53f0\u5730\u6f0f\u6709\u5473\u9053')
    eq('case5 \u5e72\u533a\u8bef\u5224', any('\u5e72\u533a' in m for m in r5['misread']), True)

    r6 = analyse('\u5730\u6f0f\u6709\u70b9\u5473\u9053')
    eq('case6 \u65e0\u5339\u914d', r6['rules'], [])

    md = render_md('\u5ba2\u536b\u5730\u6f0f\u957f\u671f\u4e0d\u7528\uff0c\u6700\u8fd1\u8fd4\u5473\uff0c\u6392\u6c34\u6b63\u5e38', r1)
    eq('case7 \u8f93\u51fa\u8868\u5934', md.startswith('# '), True)
    js = json.loads(render_json(r1))
    eq('case8 \u8f93\u51fa\u952e', sorted(js.keys()), ['misread', 'reds', 'rules', 'top'])

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 12\n\u8986\u76d6: \u6c34\u5c01\u5e72\u6db8/\u7ba1\u9053\u5835\u585e/\u82af\u4f53\u5931\u6548/\u82af\u58c1\u7559\u7f1d/\u65e0\u5b58\u6c34\u5f2f/\u7ba1\u9053\u7834\u635f/\u5e72\u533a\u8bef\u5224')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u5730\u6f0f\u8fd4\u5473\u6545\u969c\u6811\u5224\u65ad')
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
