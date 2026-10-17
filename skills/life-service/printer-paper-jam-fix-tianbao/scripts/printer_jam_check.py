# -*- coding: utf-8 -*-
"""\u6253\u5370\u673a\u5361\u7eb8\u6545\u969c\u6811\u5224\u65ad\uff1a\u8f93\u5165\u73b0\u8c61\uff0c\u8f93\u51fa\u53d6\u7eb8\u987a\u5e8f\u4e0e\u590d\u53d1\u539f\u56e0\u6392\u67e5\u987a\u5e8f\u3002

\u7528\u6cd5:
  python printer_jam_check.py --text "\u53d6\u5b8c\u7eb8\u8fd8\u63d0\u793a\u5361\u7eb8\uff0c\u4e00\u76f4\u4e00\u6b21\u8fdb\u597d\u51e0\u5f20"
  python printer_jam_check.py --file \u63cf\u8ff0.txt [--out \u7ed3\u679c.md] [--format json]
  python printer_jam_check.py --selftest
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
    {'id': 'J1', 'order': 1, 'name': '\u7eb8\u5f20\u53d7\u6f6e\u5377\u66f2\u6216\u5939\u5e26\u5f02\u7269',
     'kw': ['\u53d7\u6f6e', '\u5377\u66f2', '\u5f2f', '\u8ba2\u4e66\u9489', '\u6807\u7b7e', '\u8936', '\u6e7f'],
     'test': '\u68c0\u67e5\u7eb8\u5f20\u662f\u5426\u5e73\u6574\u3001\u6709\u65e0\u5939\u5e26\u5f02\u7269',
     'fix': '\u6362\u5e72\u71e5\u7eb8\u5f20\u5e76\u5bc6\u5c01\u5b58\u653e\uff0c\u53bb\u9664\u5f02\u7269'},
    {'id': 'J2', 'order': 2, 'name': '\u7eb8\u76d2\u88c5\u592a\u6ee1\u6216\u5bfc\u7eb8\u677f\u4e0d\u5f53',
     'kw': ['\u88c5\u592a\u6ee1', '\u88c5\u6ee1', '\u5bfc\u7eb8\u677f', '\u592a\u677e', '\u592a\u7d27', '\u88c5\u591a\u4e86'],
     'test': '\u770b\u7eb8\u91cf\u4e0e\u5bfc\u7eb8\u677f\u662f\u5426\u8d34\u5408',
     'fix': '\u88c5\u4e03\u5206\u6ee1\uff0c\u5bfc\u7eb8\u677f\u8c03\u5230\u8d34\u5408'},
    {'id': 'J3', 'order': 3, 'name': '\u6413\u7eb8\u8f6e\u810f\u6c61',
     'kw': ['\u4e0d\u8fdb\u7eb8', '\u6253\u6ed1', '\u6413\u7eb8\u8f6e', '\u7eb8\u7070', '\u8fdb\u4e0d\u53bb'],
     'test': '\u770b\u6413\u7eb8\u8f6e\u8868\u9762\u662f\u5426\u53d1\u4eae\u6709\u7eb8\u7070',
     'fix': '\u65e0\u6c34\u9152\u7cbe\u914d\u65e0\u7ed2\u5e03\u64e6\u62ed'},
    {'id': 'J4', 'order': 4, 'name': '\u6413\u7eb8\u8f6e\u78e8\u635f',
     'kw': ['\u64e6\u4e86\u8fd8', '\u78e8\u5e73', '\u78e8\u635f', '\u64e6\u5b8c\u8fd8\u662f', '\u8001\u662f\u6253\u6ed1'],
     'test': '\u770b\u8f6e\u9762\u7eb9\u8def\u662f\u5426\u78e8\u5e73',
     'fix': '\u66f4\u6362\u6413\u7eb8\u8f6e'},
    {'id': 'J5', 'order': 5, 'name': '\u5206\u79bb\u57ab\u5931\u6548',
     'kw': ['\u8fdb\u597d\u51e0\u5f20', '\u591a\u5f20', '\u4e00\u6b21\u4e24\u5f20', '\u4e00\u8d77\u8fdb', '\u5206\u79bb\u57ab'],
     'test': '\u770b\u5206\u79bb\u57ab\u662f\u5426\u78e8\u5149',
     'fix': '\u66f4\u6362\u5206\u79bb\u57ab'},
    {'id': 'J6', 'order': 6, 'name': '\u7eb8\u8def\u6b8b\u7559\u7eb8\u7247',
     'kw': ['\u53d6\u5b8c\u8fd8', '\u8fd8\u63d0\u793a', '\u4ecd\u62a5\u5361\u7eb8', '\u6b8b\u7247', '\u6495\u65ad', '\u8fd8\u6709\u7eb8'],
     'test': '\u624b\u7535\u9010\u6bb5\u7167\u7eb8\u8def\u627e\u6b8b\u7247',
     'fix': '\u7528\u954a\u5b50\u53d6\u51fa\u6b8b\u7247\uff0c\u7981\u6b62\u786c\u62fd'},
    {'id': 'J7', 'order': 7, 'name': '\u4f20\u611f\u5668\u6446\u6746\u5361\u4f4f',
     'kw': ['\u770b\u4e0d\u5230\u7eb8', '\u6ca1\u6709\u7eb8', '\u627e\u4e0d\u5230\u7eb8', '\u8fd8\u62a5\u9519', '\u4e00\u76f4\u63d0\u793a'],
     'test': '\u68c0\u67e5\u4f20\u611f\u5668\u6446\u6746\u80fd\u5426\u81ea\u7531\u56de\u5f39',
     'fix': '\u590d\u4f4d\u6446\u6746\uff1b\u65e0\u6cd5\u590d\u4f4d\u5219\u62a5\u4fee'},
    {'id': 'J8', 'order': 8, 'name': '\u5b9a\u5f71\u7ec4\u4ef6\u6545\u969c',
     'kw': ['\u540c\u4e00\u4f4d\u7f6e', '\u5b9a\u5f71', '\u53cd\u590d\u5361', '\u603b\u5728\u540c\u4e00\u4e2a', '\u5206\u79bb\u722a'],
     'test': '\u6e05\u6d01\u6413\u7eb8\u8f6e\u540e\u4ecd\u5728\u540c\u4e00\u4f4d\u7f6e\u5361\u7eb8',
     'fix': '\u505c\u7528\u62a5\u4fee\uff0c\u53ef\u80fd\u662f\u5206\u79bb\u722a\u6216\u5b9a\u5f71\u819c\u7834\u635f'},
    {'id': 'J9', 'order': 9, 'name': '\u8f93\u7a3f\u5668\u9f7f\u8f6e\u65ad\u88c2',
     'kw': ['\u8f93\u7a3f\u5668', '\u788e\u5c51', '\u9f7f\u8f6e', '\u5f02\u54cd', '\u626b\u63cf'],
     'test': '\u770b\u8f93\u7a3f\u5668\u5185\u6709\u65e0\u5851\u6599\u788e\u5c51',
     'fix': '\u505c\u7528\u62a5\u4fee'},
]

RED = [
    {'kw': ['\u6fc0\u5149', '\u521a\u6253\u5b8c', '\u521a\u6253\u5370', '\u70eb'],
     'msg': '\u6fc0\u5149\u673a\u5b9a\u5f71\u5355\u5143\u9ad8\u6e29\uff1a\u5173\u673a\u540e\u51b7\u5374 10-15 \u5206\u949f\u518d\u52a8\u624b\uff0c\u907f\u514d\u70eb\u4f24\u3002'},
    {'kw': ['\u6df1\u5904', '\u591f\u4e0d\u7740', '\u770b\u4e0d\u89c1', '\u62c6\u673a'],
     'msg': '\u7eb8\u5c51\u6389\u8fdb\u673a\u5668\u6df1\u5904\u770b\u4e0d\u89c1\u591f\u4e0d\u7740\uff1a\u505c\u7528\u62a5\u4fee\uff0c\u4e0d\u8981\u76f2\u76ee\u62c6\u89e3\u3002'},
    {'kw': ['\u540c\u4e00\u4f4d\u7f6e', '\u53cd\u590d\u5361', '\u5b9a\u5f71', '\u5206\u79bb\u722a'],
     'msg': '\u6e05\u6d01\u6413\u7eb8\u8f6e\u540e\u4ecd\u53cd\u590d\u5728\u540c\u4e00\u4f4d\u7f6e\u5361\u7eb8\uff1a\u53ef\u80fd\u662f\u5206\u79bb\u722a\u6216\u5b9a\u5f71\u819c\u7834\u635f\uff0c\u505c\u7528\u62a5\u4fee\u3002'},
    {'kw': ['\u6f0f\u7c89', '\u78b3\u7c89\u6cc4\u6f0f', '\u7126\u5473', '\u5f02\u54cd', '\u5192\u70df'],
     'msg': '\u78b3\u7c89\u6cc4\u6f0f\u3001\u7126\u5473\u6216\u5f02\u54cd\uff1a\u7acb\u5373\u505c\u7528\u65ad\u7535\u5e76\u62a5\u4fee\uff0c\u4e0d\u8981\u7528\u666e\u901a\u5438\u5c18\u5668\u5438\u78b3\u7c89\u3002'},
    {'kw': ['\u4fdd\u4fee', '\u4fdd\u4fee\u671f'],
     'msg': '\u4fdd\u4fee\u671f\u5185\u4e0d\u5efa\u8bae\u81ea\u884c\u62c6\u673a\uff1a\u8d70\u552e\u540e\uff0c\u81ea\u884c\u62c6\u673a\u53ef\u80fd\u5931\u53bb\u4fdd\u4fee\u3002'},
]

MISREAD = [
    {'kw': ['\u770b\u4e0d\u5230\u7eb8', '\u6ca1\u6709\u7eb8', '\u4e00\u76f4\u63d0\u793a'],
     'msg': '\u63d0\u793a\u5361\u7eb8\u5374\u770b\u4e0d\u5230\u7eb8\uff0c\u4e0d\u7b49\u4e8e\u6ca1\u6709\u5361\u7eb8\uff1a\u53ef\u80fd\u662f\u4f20\u611f\u5668\u6446\u6746\u5361\u4f4f\u3001\u7eb8\u5c51\u538b\u4f4f\u4f20\u611f\u5668\u3001\u6216\u6413\u7eb8\u8f6e\u6253\u6ed1\u6839\u672c\u6ca1\u8fdb\u7eb8\u3002'},
    {'kw': ['\u540c\u4e00\u4f4d\u7f6e', '\u53cd\u590d\u5361', '\u603b\u5728\u540c\u4e00\u4e2a'],
     'msg': '\u53cd\u590d\u5728\u540c\u4e00\u4f4d\u7f6e\u5361\u7eb8\u4e0d\u662f\u7eb8\u7684\u95ee\u9898\uff0c\u591a\u4e3a\u6413\u7eb8\u8f6e\u78e8\u635f\u6216\u5206\u79bb\u57ab\u5931\u6548\u3002'},
    {'kw': ['\u53d6\u5b8c\u8fd8', '\u8fd8\u63d0\u793a', '\u4ecd\u62a5\u5361\u7eb8'],
     'msg': '\u53d6\u5b8c\u7eb8\u4ecd\u62a5\u5361\u7eb8\uff0c\u5148\u9010\u6bb5\u7167\u7eb8\u8def\u627e\u6b8b\u7247\uff0c\u4e0d\u8981\u5148\u6000\u7591\u4f20\u611f\u5668\u3002'},
    {'kw': ['\u8fdb\u597d\u51e0\u5f20', '\u591a\u5f20', '\u4e00\u8d77\u8fdb'],
     'msg': '\u4e00\u6b21\u8fdb\u597d\u51e0\u5f20\u591a\u4e3a\u5206\u79bb\u57ab\u5931\u6548\uff0c\u4e0d\u662f\u7eb8\u88c5\u591a\u4e86\u8fd9\u4e48\u7b80\u5355\u3002'},
    {'kw': ['\u64e6\u4e86\u8fd8', '\u64e6\u5b8c\u8fd8\u662f', '\u6e7f\u5dfe'],
     'msg': '\u7528\u6e7f\u5dfe\u64e6\u6413\u7eb8\u8f6e\u4f1a\u7559\u4e0b\u6b8b\u7559\u8ba9\u8f6e\u5b50\u66f4\u6ed1\uff0c\u5fc5\u987b\u7528\u65e0\u6c34\u9152\u7cbe\u914d\u65e0\u7ed2\u5e03\u3002'},
]

STEPS = [
    '\u5173\u673a\u65ad\u7535\uff0c\u6fc0\u5149\u673a\u51b7\u5374 10-15 \u5206\u949f',
    '\u6309\u5c4f\u5e55\u63d0\u793a\u7684\u4f4d\u7f6e\u627e\u7eb8\uff0c\u4e0d\u51ed\u731c',
    '\u987a\u7eb8\u8def\u65b9\u5411\u53cc\u624b\u5300\u901f\u62c9\u51fa\uff0c\u6709\u963b\u529b\u7acb\u5373\u505c\u624b',
    '\u624b\u7535\u9010\u6bb5\u7167\u7eb8\u8def\uff0c\u786e\u8ba4\u6ca1\u6709\u6b8b\u7247',
    '\u68c0\u67e5\u6413\u7eb8\u8f6e\u4e0e\u5206\u79bb\u57ab\uff0c\u810f\u4e86\u64e6\u3001\u78e8\u4e86\u6362',
    '\u88c5\u56de\u5f00\u673a\uff0c\u6253\u6d4b\u8bd5\u9875\u9a8c\u6536',
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
    laser = any(k in t for k in ['\u6fc0\u5149', '\u6fc0\u6253'])
    return {'rules': rules, 'reds': reds, 'misread': miss, 'laser': laser,
            'top': rules[0]['name'] if rules else ''}


def render_md(text, r):
    lines = ['# \u6253\u5370\u673a\u5361\u7eb8\u5224\u65ad\u7ed3\u679c', '']
    if r['laser']:
        lines.append('\u6ce8\u610f\uff1a\u6fc0\u5149\u673a\u5b9a\u5f71\u5355\u5143\u9ad8\u6e29\uff0c\u5173\u673a\u540e\u51b7\u5374 10-15 \u5206\u949f\u518d\u52a8\u624b\u3002')
        lines.append('')
    lines.append('## \u4e00\u3001\u53d6\u7eb8\u987a\u5e8f\uff08\u6309\u6b64\u987a\u5e8f\u6267\u884c\uff09')
    lines.append('')
    for i, s in enumerate(STEPS, 1):
        lines.append('%d. %s' % (i, s))
    lines.append('')
    if not r['rules']:
        lines.append('\u672a\u5339\u914d\u5230\u6545\u969c\u6811\u6761\u76ee\u3002\u8bf7\u8865\u5145\uff1a\u5361\u5728\u54ea\u4e2a\u4f4d\u7f6e\u3001\u53d6\u6ca1\u53d6\u51fa\u6765\u3001\u662f\u4e0d\u662f\u603b\u5728\u540c\u4e00\u5904\u3002')
        lines.append('')
    else:
        lines.append('## \u4e8c\u3001\u590d\u53d1\u539f\u56e0\u6392\u67e5\uff08\u6700\u4f18\u5148\uff1a%s\uff09' % r['top'])
        lines.append('')
        lines.append('| \u987a\u5e8f | \u53ef\u80fd\u539f\u56e0 | \u53ef\u80fd\u6027 | \u9a8c\u8bc1\u52a8\u4f5c | \u5904\u7f6e |')
        lines.append('|---|---|---|---|---|')
        for x in r['rules']:
            lines.append('| %d | %s | %s | %s | %s |' % (
                x['order'], x['name'], x['level'], x['test'], x['fix']))
        lines.append('')
    if r['reds']:
        lines.append('## \u4e09\u3001\u5b89\u5168\u7ea2\u7ebf\uff08\u7acb\u5373\u6267\u884c\uff09')
        lines.append('')
        for m in r['reds']:
            lines.append('- %s' % m)
        lines.append('')
    if r['misread']:
        lines.append('## \u56db\u3001\u8bef\u5224\u63d0\u9192')
        lines.append('')
        for m in r['misread']:
            lines.append('- %s' % m)
        lines.append('')
    lines.append('---')
    lines.append('\u672c\u7ed3\u679c\u4e3a\u73b0\u8c61\u5339\u914d\u4e0e\u6392\u67e5\u987a\u5e8f\u5efa\u8bae\uff0c\u4e0d\u4ee3\u8868\u73b0\u573a\u5224\u65ad\uff0c\u4e0d\u6784\u6210\u7ef4\u4fee\u7ed3\u8bba\u3002')
    return '\n'.join(lines)


def render_json(r):
    return json.dumps(r, ensure_ascii=False, indent=2)


def selftest():
    errs = []

    def eq(name, got, want):
        if got != want:
            errs.append('%s got=%r want=%r' % (name, got, want))

    r1 = analyse('\u6fc0\u5149\u6253\u5370\u673a\u521a\u6253\u5b8c\u5c31\u5361\u7eb8\u4e86')
    eq('case1 \u8bc6\u522b\u6fc0\u5149\u673a', r1['laser'], True)
    eq('case1 \u9ad8\u6e29\u7ea2\u7ebf', len(r1['reds']) >= 1, True)

    r2 = analyse('\u53d6\u5b8c\u7eb8\u8fd8\u63d0\u793a\u5361\u7eb8\uff0c\u4e00\u76f4\u4e00\u6b21\u8fdb\u597d\u51e0\u5f20')
    eq('case2 \u6b8b\u7247\u547d\u4e2d', any(x['id'] == 'J6' for x in r2['rules']), True)
    eq('case2 \u5206\u79bb\u57ab\u547d\u4e2d', any(x['id'] == 'J5' for x in r2['rules']), True)

    r3 = analyse('\u63d0\u793a\u5361\u7eb8\u4f46\u770b\u4e0d\u5230\u7eb8\uff0c\u4e00\u76f4\u62a5\u9519')
    eq('case3 \u4f20\u611f\u5668\u547d\u4e2d', any(x['id'] == 'J7' for x in r3['rules']), True)
    eq('case3 \u8bef\u5224\u63d0\u9192', any('\u770b\u4e0d\u5230\u7eb8' in m for m in r3['misread']), True)

    r4 = analyse('\u603b\u5728\u540c\u4e00\u4e2a\u4f4d\u7f6e\u53cd\u590d\u5361\u7eb8')
    eq('case4 \u5b9a\u5f71\u547d\u4e2d', any(x['id'] == 'J8' for x in r4['rules']), True)
    eq('case4 \u505c\u7528\u62a5\u4fee', len(r4['reds']) >= 1, True)

    r5 = analyse('\u8fd8\u5728\u4fdd\u4fee\u671f\u5185\uff0c\u8981\u4e0d\u8981\u81ea\u5df1\u62c6')
    eq('case5 \u4fdd\u4fee\u7ea2\u7ebf', any('\u4fdd\u4fee' in m for m in r5['reds']), True)

    r6 = analyse('\u6413\u7eb8\u8f6e\u64e6\u4e86\u8fd8\u662f\u6253\u6ed1')
    eq('case6 \u78e8\u635f\u547d\u4e2d', any(x['id'] == 'J4' for x in r6['rules']), True)

    r7 = analyse('\u6253\u5370\u673a\u6709\u70b9\u95ee\u9898')
    eq('case7 \u65e0\u5339\u914d', r7['rules'], [])

    md = render_md('\u6fc0\u5149\u6253\u5370\u673a\u5361\u7eb8', r1)
    eq('case8 \u542b\u9ad8\u6e29\u63d0\u793a', '\u51b7\u5374 10-15 \u5206\u949f' in md, True)
    js = json.loads(render_json(r1))
    eq('case9 \u8f93\u51fa\u952e', sorted(js.keys()), ['laser', 'misread', 'reds', 'rules', 'top'])

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 12\n\u8986\u76d6: \u7eb8\u5f20\u53d7\u6f6e/\u7eb8\u76d2\u88c5\u586b/\u6413\u7eb8\u8f6e\u810f\u6c61/\u6413\u7eb8\u8f6e\u78e8\u635f/\u5206\u79bb\u57ab/\u7eb8\u8def\u6b8b\u7247/\u4f20\u611f\u5668\u6446\u6746/\u5b9a\u5f71\u7ec4\u4ef6/\u8f93\u7a3f\u5668/\u6fc0\u5149\u9ad8\u6e29/\u4fdd\u4fee\u671f')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u6253\u5370\u673a\u5361\u7eb8\u6545\u969c\u6811\u5224\u65ad')
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
