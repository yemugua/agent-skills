# -*- coding: utf-8 -*-
"""\u6295\u5f71\u753b\u9762\u5f02\u5e38\u6545\u969c\u6811\u5224\u65ad\u4e0e\u6295\u5c04\u8ddd\u79bb\u6362\u7b97\u3002

\u7528\u6cd5:
  python projector_setup_check.py --text "\u753b\u9762\u4e0a\u4e0b\u4e0d\u7b49\u5bbd\uff0c\u673a\u5668\u53ea\u80fd\u653e\u4fa7\u9762\uff0c\u4e00\u8fb9\u6a21\u7cca"
  python projector_setup_check.py --throw-ratio 1.2 --width 2.21
  python projector_setup_check.py --file \u63cf\u8ff0.txt [--out \u7ed3\u679c.md] [--format json]
  python projector_setup_check.py --selftest
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
    {'id': 'P1', 'order': 1, 'name': '\u5782\u76f4\u68af\u5f62\uff08\u4e0a\u4e0b\u4e0d\u7b49\u5bbd\uff09',
     'kw': ['\u4e0a\u4e0b\u4e0d\u7b49\u5bbd', '\u4e0a\u5bbd\u4e0b\u7a84', '\u4e0b\u5bbd\u4e0a\u7a84', '\u4e0a\u4e0b\u4e0d\u4e00', '\u5782\u76f4\u68af\u5f62', '\u4fef\u4ef0'],
     'test': '\u6c34\u5e73\u4eea\u770b\u673a\u8eab\u662f\u5426\u6c34\u5e73\uff0c\u5173\u6389\u6821\u6b63\u770b\u539f\u56fe\u5f62\u72b6',
     'fix': '\u8c03\u8c03\u8282\u811a\u6216\u7528\u5149\u5b66\u955c\u5934\u4f4d\u79fb\uff0c\u6700\u540e\u624d\u7528\u5782\u76f4\u6821\u6b63'},
    {'id': 'P2', 'order': 2, 'name': '\u6c34\u5e73\u68af\u5f62\uff08\u5de6\u53f3\u4e0d\u7b49\u5bbd\uff09',
     'kw': ['\u5de6\u53f3\u4e0d\u7b49\u5bbd', '\u5de6\u53f3\u4e0d\u4e00', '\u4fa7\u6295', '\u653e\u4fa7\u9762', '\u659c\u7740\u6295', '\u6c34\u5e73\u68af\u5f62'],
     'test': '\u770b\u673a\u5668\u662f\u5426\u6b63\u5bf9\u5e55\u5e03\u4e2d\u5fc3',
     'fix': '\u632a\u673a\u5668\u4f4d\u7f6e\u51cf\u5c11\u4fa7\u6295\u89d2\uff0c\u800c\u4e0d\u662f\u52a0\u5927\u6c34\u5e73\u6821\u6b63'},
    {'id': 'P3', 'order': 3, 'name': '\u4fa7\u6295\u5bfc\u81f4\u5355\u4fa7\u5931\u7126',
     'kw': ['\u4e00\u8fb9\u6a21\u7cca', '\u4e00\u8fb9\u6e05\u695a', '\u4e00\u4fa7\u865a', '\u534a\u8fb9\u7cca', '\u5bf9\u4e0d\u4e0a\u7126'],
     'test': '\u5173\u6389\u4fa7\u6295\u6821\u6b63\uff0c\u6b63\u6295\u5bf9\u7126\u540e\u518d\u6bd4\u8f83\u4e24\u4fa7\u6e05\u6670\u5ea6',
     'fix': '\u51cf\u5c0f\u4fa7\u6295\u89d2\uff0c\u805a\u7126\u5e73\u9762\u503e\u659c\u662f\u7269\u7406\u5fc5\u7136'},
    {'id': 'P4', 'order': 4, 'name': '\u5e55\u5e03\u6216\u5899\u9762\u4e0d\u5e73',
     'kw': ['\u56db\u89d2', '\u5e55\u5e03\u76b1', '\u4e0d\u5e73', '\u5899\u4e0d\u5e73', '\u6ce2\u6d6a'],
     'test': '\u4fa7\u5149\u7167\u5c04\u5e55\u9762\u770b\u662f\u5426\u6709\u8d77\u4f0f',
     'fix': '\u6574\u5e73\u5e55\u5e03\u6216\u66f4\u6362\u5e55\u9762'},
    {'id': 'P5', 'order': 5, 'name': '\u955c\u5934\u4f4d\u79fb\u8d85\u8303\u56f4\u6216\u955c\u5934\u810f',
     'kw': ['\u8fb9\u7f18\u53d1\u865a', '\u8272\u8fb9', '\u8fb9\u7f18\u7cca', '\u955c\u5934\u810f', '\u4f4d\u79fb'],
     'test': '\u628a\u955c\u5934\u4f4d\u79fb\u56de\u5230\u4e2d\u5fc3\uff0c\u6e05\u6d01\u955c\u5934\u540e\u91cd\u8bd5',
     'fix': '\u56de\u5230\u4f4d\u79fb\u4e2d\u5fc3\uff0c\u6e05\u6d01\u955c\u5934'},
    {'id': 'P6', 'order': 6, 'name': '\u6570\u7801\u6821\u6b63\u91cd\u91c7\u6837',
     'kw': ['\u9ed1\u8fb9', '\u952f\u9f7f', '\u6bdb\u8fb9', '\u91cd\u5f71', '\u81ea\u52a8\u6821\u6b63'],
     'test': '\u51cf\u5c0f\u6821\u6b63\u91cf\u540e\u770b\u9ed1\u8fb9\u4e0e\u952f\u9f7f\u662f\u5426\u6d88\u5931',
     'fix': '\u51cf\u5c0f\u6570\u7801\u6821\u6b63\u91cf\uff0c\u4f18\u5148\u7269\u7406\u6446\u4f4d'},
    {'id': 'P7', 'order': 7, 'name': '\u4eae\u5ea6\u4e0d\u8db3\u6216\u73af\u5883\u5149\u8fc7\u5f3a',
     'kw': ['\u4eae\u5ea6\u4e0d\u591f', '\u53d1\u7070', '\u770b\u4e0d\u6e05', '\u592a\u6697', '\u73af\u5883\u5149', '\u767d\u5929'],
     'test': '\u5173\u706f\u62c9\u5e18\u540e\u5bf9\u6bd4\uff0c\u7f29\u5c0f\u753b\u5e45\u518d\u770b',
     'fix': '\u7f29\u5c0f\u753b\u5e45\u3001\u51cf\u5c11\u6821\u6b63\u3001\u906e\u5149\uff0c\u4e0d\u8981\u5148\u6000\u7591\u706f\u6ce1'},
    {'id': 'P8', 'order': 8, 'name': '\u540a\u88c5\u6a21\u5f0f\u672a\u5207\u6362',
     'kw': ['\u98a0\u5012', '\u5012\u8fc7\u6765', '\u4e0a\u4e0b\u53cd', '\u540a\u88c5', '\u955c\u50cf'],
     'test': '\u67e5\u770b\u8bbe\u7f6e\u91cc\u7684\u6295\u5f71\u65b9\u5f0f\u9009\u9879',
     'fix': '\u5207\u6362\u540a\u88c5\u6a21\u5f0f\u6216\u6295\u5f71\u65b9\u5f0f'},
    {'id': 'P9', 'order': 9, 'name': '\u673a\u5668\u5185\u90e8\u6545\u969c',
     'kw': ['\u9ed1\u70b9', '\u8272\u6591', '\u5f02\u54cd', '\u5f02\u5473', '\u5192\u70df', '\u8fc7\u70ed'],
     'test': '\u6295\u7eaf\u8272\u753b\u9762\u770b\u6709\u65e0\u56fa\u5b9a\u9ed1\u70b9\u6216\u8272\u6591',
     'fix': '\u505c\u7528\u5e76\u62a5\u552e\u540e'},
]

RED = [
    {'kw': ['\u540a\u88c5', '\u6253\u5b54', '\u540a\u9876', '\u9f99\u9aa8'],
     'msg': '\u540a\u9876\u6263\u677f\u4e0e\u8f7b\u94a2\u9f99\u9aa8\u4e0d\u627f\u91cd\uff1a\u540a\u67b6\u5fc5\u987b\u56fa\u5b9a\u5728\u697c\u677f\u6216\u627f\u91cd\u7ed3\u6784\u5e76\u52a0\u88c5\u9632\u5760\u7ef3\uff0c\u8f6c\u4e13\u4e1a\u4eba\u5458\u3002'},
    {'kw': ['\u6697\u7ebf', '\u7a7f\u5899', '\u7535\u6e90\u7ebf', '\u63d2\u5ea7', '\u5e03\u7ebf'],
     'msg': '\u8d70\u6697\u7ebf\u3001\u6539\u9020\u7535\u6e90\u63d2\u5ea7\u5c5e\u7535\u5de5\u4f5c\u4e1a\uff0c\u8f6c\u4e13\u4e1a\u7535\u5de5\u3002'},
    {'kw': ['\u5f02\u54cd', '\u5f02\u5473', '\u5192\u70df', '\u9ed1\u70b9', '\u8272\u6591'],
     'msg': '\u673a\u5668\u5185\u90e8\u5f02\u54cd\u3001\u5f02\u5473\u3001\u5192\u70df\u6216\u56fa\u5b9a\u9ed1\u70b9\uff1a\u7acb\u5373\u505c\u7528\u5e76\u8054\u7cfb\u552e\u540e\u3002'},
    {'kw': ['\u9ad8\u5904', '\u68af\u5b50', '\u4e24\u7c73', '2\u7c73'],
     'msg': '\u8d85\u8fc7 2 \u7c73\u6216\u9700\u7ad9\u68af\u5b50\u6700\u9ad8\u4e24\u6863\u7684\u4f5c\u4e1a\uff1a\u8f6c\u4e13\u4e1a\u4eba\u5458\uff0c\u7981\u6b62\u5355\u4eba\u767b\u9ad8\u3002'},
]

MISREAD = [
    {'kw': ['\u68af\u5f62', '\u4e0d\u7b49\u5bbd', '\u6b6a'],
     'msg': '\u753b\u9762\u6b6a\u4e0d\u7b49\u4e8e\u8981\u5f00\u6821\u6b63\uff0c\u5148\u632a\u673a\u5668\u548c\u7528\u5149\u5b66\u4f4d\u79fb\uff0c\u6570\u7801\u6821\u6b63\u635f\u753b\u8d28\u3002'},
    {'kw': ['\u4e00\u8fb9\u6a21\u7cca', '\u4e00\u4fa7\u865a', '\u534a\u8fb9\u7cca'],
     'msg': '\u4fa7\u6295\u65f6\u805a\u7126\u5e73\u9762\u503e\u659c\uff0c\u5355\u4fa7\u5931\u7126\u662f\u7269\u7406\u5fc5\u7136\uff0c\u4e0d\u662f\u673a\u5668\u574f\u4e86\u3002'},
    {'kw': ['\u4eae\u5ea6\u4e0d\u591f', '\u53d1\u7070', '\u592a\u6697'],
     'msg': '\u4eae\u5ea6\u4e0d\u8db3\u5148\u67e5\u753b\u5e45\u8fc7\u5927\u3001\u4fa7\u6295\u6821\u6b63\u91cf\u4e0e\u73af\u5883\u5149\uff0c\u4e0d\u8981\u5148\u6000\u7591\u706f\u6ce1\u8001\u5316\u3002'},
    {'kw': ['\u98a0\u5012', '\u5012\u8fc7\u6765', '\u4e0a\u4e0b\u53cd'],
     'msg': '\u540a\u88c5\u753b\u9762\u98a0\u5012\u662f\u8bbe\u7f6e\u95ee\u9898\uff0c\u5207\u6362\u540a\u88c5\u6a21\u5f0f\u6216\u6295\u5f71\u65b9\u5f0f\u5373\u53ef\u3002'},
    {'kw': ['\u9ed1\u8fb9', '\u952f\u9f7f'],
     'msg': '\u9ed1\u8fb9\u4e0e\u952f\u9f7f\u6765\u81ea\u6570\u7801\u6821\u6b63\u7684\u50cf\u7d20\u91cd\u91c7\u6837\uff0c\u51cf\u5c0f\u6821\u6b63\u91cf\u624d\u80fd\u6d88\u9664\u3002'},
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


def distance(throw_ratio, width):
    return round(throw_ratio * width, 2)


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
    return {'rules': rules, 'reds': reds, 'misread': miss,
            'top': rules[0]['name'] if rules else ''}


def render_md(text, r, dist=None):
    lines = ['# \u6295\u5f71\u753b\u9762\u8c03\u6821\u5224\u65ad\u7ed3\u679c', '']
    if dist:
        lines.append('\u6295\u5c04\u8ddd\u79bb\uff1a\u6295\u5c04\u6bd4 %.2f \u00d7 \u753b\u9762\u5bbd %.2f m = **%.2f m**\uff08\u955c\u5934\u5230\u5e55\u9762\uff09' % (
            dist[0], dist[1], dist[2]))
        lines.append('')
    if not r['rules']:
        lines.append('\u672a\u5339\u914d\u5230\u6545\u969c\u6811\u6761\u76ee\u3002\u8bf7\u8865\u5145\uff1a\u662f\u4e0a\u4e0b\u4e0d\u7b49\u5bbd\u8fd8\u662f\u5de6\u53f3\u4e0d\u7b49\u5bbd\u3001\u6709\u6ca1\u6709\u4fa7\u6295\u3001\u540a\u88c5\u8fd8\u662f\u6b63\u6295\u3002')
        lines.append('')
    else:
        lines.append('\u6700\u4f18\u5148\u6392\u67e5\uff1a%s' % r['top'])
        lines.append('')
        lines.append('## \u4e00\u3001\u6392\u67e5\u987a\u5e8f\uff08\u6309\u6b64\u987a\u5e8f\u6267\u884c\uff09')
        lines.append('')
        lines.append('| \u987a\u5e8f | \u73b0\u8c61\u539f\u56e0 | \u53ef\u80fd\u6027 | \u9a8c\u8bc1\u52a8\u4f5c | \u5904\u7f6e |')
        lines.append('|---|---|---|---|---|')
        for x in r['rules']:
            lines.append('| %d | %s | %s | %s | %s |' % (
                x['order'], x['name'], x['level'], x['test'], x['fix']))
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
    lines.append('## \u56db\u3001\u8c03\u6821\u56fa\u5b9a\u987a\u5e8f')
    lines.append('')
    lines.append('1. \u5148\u5173\u6389\u6240\u6709\u68af\u5f62\u6821\u6b63\uff0c\u770b\u539f\u59cb\u753b\u9762\u5f62\u72b6')
    lines.append('2. \u80fd\u632a\u673a\u5668\u5c31\u632a\uff0c\u7269\u7406\u6d88\u9664\u504f\u5dee')
    lines.append('3. \u6709\u5149\u5b66\u4f4d\u79fb\u5c31\u7528\u5149\u5b66\u4f4d\u79fb')
    lines.append('4. \u6700\u540e\u624d\u5f00\u6570\u7801\u6821\u6b63\uff0c\u4e14\u91cf\u5c3d\u91cf\u5c0f')
    lines.append('')
    lines.append('---')
    lines.append('\u672c\u7ed3\u679c\u4e3a\u73b0\u8c61\u5339\u914d\u4e0e\u6362\u7b97\u5efa\u8bae\uff0c\u4e0d\u4ee3\u8868\u73b0\u573a\u5224\u65ad\uff0c\u4e0d\u6784\u6210\u5b89\u88c5\u65bd\u5de5\u7ed3\u8bba\u3002')
    return '\n'.join(lines)


def render_json(r, dist=None):
    obj = dict(r)
    obj['distance'] = {'throw_ratio': dist[0], 'width': dist[1],
                       'distance': dist[2]} if dist else None
    return json.dumps(obj, ensure_ascii=False, indent=2)


def selftest():
    errs = []

    def eq(name, got, want):
        if got != want:
            errs.append('%s got=%r want=%r' % (name, got, want))

    r1 = analyse('\u753b\u9762\u4e0a\u4e0b\u4e0d\u7b49\u5bbd\uff0c\u673a\u5668\u53ea\u80fd\u653e\u4fa7\u9762\uff0c\u4e00\u8fb9\u6a21\u7cca')
    eq('case1 \u5782\u76f4\u68af\u5f62\u4f18\u5148', r1['rules'][0]['id'], 'P1')
    eq('case1 \u4fa7\u6295\u547d\u4e2d', any(x['id'] == 'P2' for x in r1['rules']), True)
    eq('case1 \u5931\u7126\u547d\u4e2d', any(x['id'] == 'P3' for x in r1['rules']), True)

    r2 = analyse('\u540a\u88c5\u540e\u753b\u9762\u4e0a\u4e0b\u98a0\u5012')
    eq('case2 \u540a\u88c5\u6a21\u5f0f\u4f18\u5148', r2['rules'][0]['id'], 'P8')
    eq('case2 \u8bef\u5224\u63d0\u9192', any('\u540a\u88c5\u753b\u9762\u98a0\u5012' in m for m in r2['misread']), True)

    r3 = analyse('\u4eae\u5ea6\u4e0d\u591f\uff0c\u767d\u5929\u770b\u4e0d\u6e05')
    eq('case3 \u4eae\u5ea6\u547d\u4e2d', r3['rules'][0]['id'], 'P7')

    r4 = analyse('\u673a\u5668\u6709\u5f02\u54cd\uff0c\u753b\u9762\u6709\u56fa\u5b9a\u9ed1\u70b9')
    eq('case4 \u6545\u969c\u547d\u4e2d', r4['rules'][0]['id'], 'P9')
    eq('case4 \u7ea2\u7ebf\u547d\u4e2d', len(r4['reds']) >= 1, True)

    r5 = analyse('\u60f3\u5728\u540a\u9876\u4e0a\u6253\u5b54\u88c5\u540a\u67b6')
    eq('case5 \u540a\u88c5\u7ea2\u7ebf', any('\u4e0d\u627f\u91cd' in m for m in r5['reds']), True)

    eq('case6 \u8ddd\u79bb\u6362\u7b97', distance(1.2, 2.21), 2.65)
    eq('case7 \u8ddd\u79bb\u6362\u7b97\u77ed\u7126', distance(0.47, 2.21), 1.04)

    r8 = analyse('\u6295\u5f71\u753b\u9762\u6709\u70b9\u95ee\u9898')
    eq('case8 \u65e0\u5339\u914d', r8['rules'], [])

    md = render_md('\u753b\u9762\u662f\u68af\u5f62\u7684', r1, (1.2, 2.21, 2.65))
    eq('case9 \u542b\u8ddd\u79bb\u884c', '\u6295\u5c04\u8ddd\u79bb' in md, True)
    js = json.loads(render_json(r1, (1.2, 2.21, 2.65)))
    eq('case10 \u8f93\u51fa\u952e', sorted(js.keys()),
       ['distance', 'misread', 'reds', 'rules', 'top'])

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 13\n\u8986\u76d6: \u5782\u76f4\u68af\u5f62/\u6c34\u5e73\u68af\u5f62/\u5355\u4fa7\u5931\u7126/\u5e55\u9762\u4e0d\u5e73/\u955c\u5934\u4f4d\u79fb/\u91cd\u91c7\u6837/\u4eae\u5ea6\u4e0d\u8db3/\u540a\u88c5\u6a21\u5f0f/\u673a\u5668\u6545\u969c/\u8ddd\u79bb\u6362\u7b97')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u6295\u5f71\u753b\u9762\u5f02\u5e38\u5224\u65ad\u4e0e\u6295\u5c04\u8ddd\u79bb\u6362\u7b97')
    ap.add_argument('--text', help='\u73b0\u8c61\u63cf\u8ff0')
    ap.add_argument('--file', help='\u4ece\u6587\u4ef6\u8bfb\u73b0\u8c61\u63cf\u8ff0')
    ap.add_argument('--throw-ratio', dest='throw_ratio', type=float, help='\u6295\u5c04\u6bd4\uff0c\u4f8b\u5982 1.2')
    ap.add_argument('--width', type=float, help='\u753b\u9762\u5bbd\u5ea6\uff08\u7c73\uff09\uff0c\u4f8b\u5982 2.21')
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

    dist = None
    if a.throw_ratio and a.width:
        dist = (a.throw_ratio, a.width, distance(a.throw_ratio, a.width))

    if not text.strip() and dist is None:
        print('ERROR \u9700\u8981 --text\u3001--file \u6216\u540c\u65f6\u7ed9 --throw-ratio \u4e0e --width')
        return 2

    r = analyse(text)
    out = render_md(text, r, dist) if a.format == 'md' else render_json(r, dist)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % a.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
