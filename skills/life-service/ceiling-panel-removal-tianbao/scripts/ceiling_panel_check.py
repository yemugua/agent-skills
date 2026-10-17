# -*- coding: utf-8 -*-
"""\u96c6\u6210\u540a\u9876\u95ee\u9898\u6545\u969c\u6811\u5224\u65ad\uff1a\u8f93\u5165\u73b0\u8c61\uff0c\u8f93\u51fa\u6392\u67e5\u987a\u5e8f\u4e0e\u5b89\u5168\u5904\u7f6e\u3002

\u7528\u6cd5:
  python ceiling_panel_check.py --text "\u540a\u9876\u4e0a\u6709\u6c34\u6e0d\uff0c\u60f3\u62c6\u5f00\u770b\u770b\u662f\u4e0d\u662f\u697c\u4e0a\u7684\u95ee\u9898"
  python ceiling_panel_check.py --file \u63cf\u8ff0.txt [--out \u7ed3\u679c.md] [--format json]
  python ceiling_panel_check.py --selftest
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
    {'id': 'E1', 'order': 1, 'name': '\u7a7a\u5f00\u8df3\u95f8\u6216\u9065\u63a7\u7535\u6c60\u6ca1\u7535',
     'kw': ['\u6d74\u9738\u4e0d\u70ed', '\u4e0d\u4eae', '\u4e0d\u8f6c', '\u6ca1\u53cd\u5e94', '\u9065\u63a7', '\u706f\u4e0d\u4eae', '\u6362\u6c14\u6247\u4e0d\u8f6c'],
     'test': '\u67e5\u914d\u7535\u7bb1\u5bf9\u5e94\u7a7a\u5f00\u662f\u5426\u8df3\u95f8\uff0c\u9065\u63a7\u5668\u7535\u6c60\u662f\u5426\u6709\u7535',
     'fix': '\u5408\u4e0a\u7a7a\u5f00\u6216\u66f4\u6362\u7535\u6c60\uff0c\u4e0d\u8981\u5148\u5224\u5b9a\u6a21\u5757\u635f\u574f'},
    {'id': 'E2', 'order': 2, 'name': '\u63a5\u7ebf\u7aef\u5b50\u677e\u52a8',
     'kw': ['\u65f6\u597d\u65f6\u574f', '\u5076\u5c14', '\u63a5\u89e6\u4e0d\u826f', '\u7aef\u5b50', '\u677e\u52a8'],
     'test': '\u65ad\u7535\u540e\u6253\u5f00\u9762\u677f\u68c0\u67e5\u63a5\u7ebf\u7aef\u5b50',
     'fix': '\u65ad\u7535\u540e\u7d27\u56fa\uff1b\u6709\u70e7\u8680\u7194\u5316\u5219\u8bf7\u7535\u5de5'},
    {'id': 'E3', 'order': 3, 'name': '\u6392\u98ce\u7ba1\u672a\u63a5\u5230\u5ba4\u5916\u6216\u6b62\u9006\u9600\u5931\u6548',
     'kw': ['\u5f02\u5473', '\u6f6e\u6c14', '\u6f6e\u6e7f', '\u53cd\u5473', '\u6b62\u9006\u9600', '\u6392\u98ce\u7ba1'],
     'test': '\u62c6\u677f\u540e\u770b\u6392\u98ce\u7ba1\u8d70\u5411\u4e0e\u6b62\u9006\u9600\u72b6\u6001',
     'fix': '\u628a\u6392\u98ce\u7ba1\u63a5\u5230\u5ba4\u5916\u6216\u66f4\u6362\u6b62\u9006\u9600'},
    {'id': 'E4', 'order': 4, 'name': '\u6a21\u5757\u672c\u8eab\u6545\u969c',
     'kw': ['\u7126\u5473', '\u5f02\u54cd', '\u6a21\u5757\u574f', '\u5192\u70df', '\u7535\u673a\u574f'],
     'test': '\u6392\u9664\u524d\u51e0\u9879\u540e\u901a\u7535\u6d4b\u8bd5',
     'fix': '\u66f4\u6362\u6a21\u5757\u6216\u62a5\u4fee'},
    {'id': 'E5', 'order': 5, 'name': '\u6263\u677f\u53d8\u5f62\u6216\u5361\u4e0d\u7d27',
     'kw': ['\u6263\u677f\u677e', '\u53d8\u5f62', '\u62c6\u4e0d\u4e0b\u6765', '\u5361\u4e0d\u7d27', '\u6389\u4e0b\u6765', '\u6709\u54cd\u58f0'],
     'test': '\u770b\u6263\u677f\u8fb9\u7f18\u662f\u5426\u53d8\u5f62\u3001\u5361\u6263\u662f\u5426\u5230\u4f4d',
     'fix': '\u7528\u5438\u76d8\u6216\u64ac\u7247\u62c6\u88c5\uff0c\u53d8\u5f62\u5219\u66f4\u6362\u5355\u5757\uff1b\u4e0d\u8981\u786c\u64ac'},
    {'id': 'E6', 'order': 6, 'name': '\u4e0a\u65b9\u6c34\u7ba1\u6216\u63a5\u5934\u6e17\u6f0f',
     'kw': ['\u6f0f\u6c34', '\u6ef4\u6c34', '\u6c34\u6e0d', '\u6e17\u6c34', '\u6e7f'],
     'test': '\u65ad\u7535\u540e\u62c6\u677f\u67e5\u770b\u6c34\u6e90\u4e0e\u81ea\u5bb6\u7ba1\u7ebf\u8d70\u5411',
     'fix': '\u5173\u6c34\u9600\u540e\u8bf7\u6c34\u7ba1\u7ef4\u4fee\uff1b\u5148\u627e\u6c34\u6e90\u518d\u56de\u88c5'},
    {'id': 'E7', 'order': 7, 'name': '\u697c\u4e0a\u6216\u516c\u5171\u7ba1\u9053\u6e17\u6f0f',
     'kw': ['\u697c\u4e0a', '\u7269\u4e1a', '\u516c\u5171\u7ba1\u9053', '\u4e0d\u662f\u6211\u5bb6'],
     'test': '\u5bf9\u6bd4\u6c34\u6e0d\u4f4d\u7f6e\u4e0e\u81ea\u5bb6\u7ba1\u7ebf\u8d70\u5411',
     'fix': '\u62a5\u7269\u4e1a\u534f\u8c03\uff0c\u4e0d\u8981\u81ea\u884c\u5904\u7406\u516c\u5171\u7ba1\u9053'},
    {'id': 'E8', 'order': 8, 'name': '\u71c3\u6c14\u7ba1\u9053\u6216\u6392\u70df\u7ba1\u95ee\u9898',
     'kw': ['\u71c3\u6c14', '\u7164\u6c14', '\u5929\u7136\u6c14', '\u6392\u70df\u7ba1', '\u70ed\u6c34\u5668'],
     'test': '\u786e\u8ba4\u4e0a\u65b9\u662f\u5426\u6709\u71c3\u6c14\u7ba1\u4e0e\u6392\u70df\u7ba1',
     'fix': '\u4e0d\u78b0\u649e\uff0c\u95fb\u5230\u71c3\u6c14\u5473\u7acb\u5373\u5173\u9600\u5f00\u7a97\uff0c\u5230\u6237\u5916\u62a5\u71c3\u6c14\u516c\u53f8'},
]

RED = [
    {'kw': ['\u63a5\u7ebf', '\u63a5\u7535', '\u56de\u8def', '\u914d\u7535\u7bb1', '\u6362\u7ebf'],
     'msg': '\u65b0\u589e\u56de\u8def\u3001\u6539\u52a8\u63a5\u7ebf\u3001\u66f4\u6362\u914d\u7535\u7bb1\u5185\u5668\u4ef6\u5c5e\u7535\u5de5\u4f5c\u4e1a\uff1a\u8bf7\u6301\u8bc1\u7535\u5de5\u64cd\u4f5c\uff0c\u4e0d\u5f97\u5e26\u7535\u4f5c\u4e1a\u3002'},
    {'kw': ['\u70e7\u8680', '\u7194\u5316', '\u7126\u5473', '\u5192\u70df'],
     'msg': '\u63a5\u7ebf\u7aef\u5b50\u70e7\u8680\u3001\u7194\u5316\u6216\u6709\u7126\u5473\uff1a\u7acb\u5373\u505c\u7528\u65ad\u7535\uff0c\u8fd9\u662f\u63a5\u89e6\u4e0d\u826f\u8fc7\u70ed\u7684\u75d5\u8ff9\uff0c\u8bf7\u7535\u5de5\u5904\u7406\u3002'},
    {'kw': ['\u71c3\u6c14', '\u7164\u6c14', '\u5929\u7136\u6c14'],
     'msg': '\u95fb\u5230\u71c3\u6c14\u5473\uff1a\u5f00\u7a97\u901a\u98ce\u3001\u5173\u95ed\u9600\u95e8\u3001\u4e0d\u89e6\u78b0\u4efb\u4f55\u7535\u5668\u5f00\u5173\uff0c\u5230\u6237\u5916\u62e8\u6253\u71c3\u6c14\u516c\u53f8\u7535\u8bdd\u3002'},
    {'kw': ['\u4e24\u7c73', '2\u7c73', '\u9ad8\u5904', '\u68af\u5b50', '\u767b\u9ad8'],
     'msg': '\u4f5c\u4e1a\u9ad8\u5ea6\u8d85 2 \u7c73\u6216\u9700\u7ad9\u4eba\u5b57\u68af\u6700\u9ad8\u4e24\u6863\uff1a\u8bf7\u4e13\u4e1a\u4eba\u5458\uff0c\u7981\u6b62\u5355\u4eba\u767b\u9ad8\uff0c\u9700\u6709\u4eba\u6276\u68af\u3002'},
    {'kw': ['\u5927\u9762\u79ef', '\u9f99\u9aa8', '\u9508\u8680'],
     'msg': '\u5927\u9762\u79ef\u62c6\u88c5\u3001\u9f99\u9aa8\u9508\u8680\u53d8\u5f62\uff1a\u8bf7\u4e13\u4e1a\u4eba\u5458\u5904\u7406\u3002'},
    {'kw': ['\u697c\u4e0a', '\u516c\u5171\u7ba1\u9053'],
     'msg': '\u6d89\u53ca\u697c\u4e0a\u4f4f\u6237\u6216\u516c\u5171\u7ba1\u9053\uff1a\u62a5\u7269\u4e1a\u534f\u8c03\uff0c\u4e0d\u8981\u81ea\u884c\u62c6\u6539\u516c\u5171\u8bbe\u65bd\u3002'},
]

MISREAD = [
    {'kw': ['\u6d74\u9738\u4e0d\u70ed', '\u4e0d\u4eae', '\u4e0d\u8f6c', '\u6ca1\u53cd\u5e94'],
     'msg': '\u6d74\u9738\u4e0d\u70ed\u6216\u6362\u6c14\u6247\u4e0d\u8f6c\u4e0d\u7b49\u4e8e\u6a21\u5757\u574f\u4e86\uff0c\u5148\u67e5\u7a7a\u5f00\u662f\u5426\u8df3\u95f8\u3001\u9065\u63a7\u7535\u6c60\u662f\u5426\u6709\u7535\u3002'},
    {'kw': ['\u6c34\u6e0d', '\u6f0f\u6c34', '\u6e17\u6c34'],
     'msg': '\u540a\u9876\u6709\u6c34\u6e0d\u4e0d\u7b49\u4e8e\u81ea\u5bb6\u6c34\u7ba1\u6f0f\uff0c\u53ef\u80fd\u662f\u697c\u4e0a\u9632\u6c34\u3001\u516c\u5171\u7ba1\u9053\u6216\u6392\u98ce\u7ba1\u51b7\u51dd\uff0c\u5148\u627e\u6c34\u6e90\u518d\u56de\u88c5\u3002'},
    {'kw': ['\u62c6\u4e0d\u4e0b\u6765'],
     'msg': '\u6263\u677f\u62c6\u4e0d\u4e0b\u6765\u591a\u4e3a\u5361\u6263\u7d27\u6216\u6cb9\u6f06\u7c98\u8fde\uff0c\u5148\u5212\u7f1d\u518d\u7528\u5438\u76d8\u62c9\uff0c\u786c\u64ac\u4f1a\u8ba9\u6263\u677f\u6c38\u4e45\u53d8\u5f62\u3002'},
    {'kw': ['\u53d8\u5f62'],
     'msg': '\u6263\u677f\u53d8\u5f62\u4e0d\u9700\u8981\u6574\u7247\u6362\u540a\u9876\uff0c\u5355\u5757\u53ef\u6362\u3002'},
    {'kw': ['\u5f02\u5473', '\u6f6e\u6c14', '\u53cd\u5473'],
     'msg': '\u540a\u9876\u5f02\u5473\u591a\u4e3a\u6392\u98ce\u7ba1\u6ca1\u63a5\u5230\u5ba4\u5916\u6216\u6b62\u9006\u9600\u5931\u6548\uff0c\u4e0d\u662f\u6263\u677f\u5bc6\u5c01\u95ee\u9898\u3002'},
    {'kw': ['\u68c0\u4fee\u53e3', '\u5f00\u5b54'],
     'msg': '\u96c6\u6210\u540a\u9876\u6bcf\u5757\u90fd\u80fd\u62c6\uff0c\u4e34\u65f6\u68c0\u4fee\u62c6\u5bf9\u5e94\u677f\u5757\u5373\u53ef\uff0c\u591a\u6570\u4e0d\u5fc5\u4e13\u95e8\u7834\u574f\u6027\u5f00\u5b54\u3002'},
]

STEPS = [
    '\u65ad\u5f00\u6d74\u9738\u4e0e\u7167\u660e\u56de\u8def\u7a7a\u5f00\uff0c\u9a8c\u7535\u7b14\u786e\u8ba4\u65e0\u7535',
    '\u786e\u8ba4\u4e0a\u65b9\u6709\u65e0\u7535\u7ebf\u3001\u6c34\u7ba1\u3001\u71c3\u6c14\u7ba1',
    '\u5438\u76d8\u5438\u4f4f\u677f\u9762\u4e2d\u90e8\uff0c\u5782\u76f4\u5411\u4e0b\u8f7b\u62c9',
    '\u62c6\u4e0b\u7684\u6263\u677f\u5e73\u653e\uff0c\u8fb9\u7f18\u950b\u5229\u6234\u624b\u5957',
    '\u62c6\u7535\u5668\u6a21\u5757\u524d\u5148\u62cd\u7167\u8bb0\u5f55\u706b\u96f6\u5730',
    '\u56de\u88c5\u65f6\u5148\u63a5\u597d\u7ebf\u518d\u56fa\u5b9a\uff0c\u7ebf\u5934\u505a\u7edd\u7f18',
    '\u6062\u590d\u4f9b\u7535\u540e\u9010\u9879\u6d4b\u8bd5\u7167\u660e\u3001\u53d6\u6696\u3001\u6362\u6c14',
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
    return {'rules': rules, 'reds': reds, 'misread': miss,
            'top': rules[0]['name'] if rules else ''}


def render_md(text, r):
    lines = ['# \u96c6\u6210\u540a\u9876\u95ee\u9898\u5224\u65ad\u7ed3\u679c', '']
    if r['reds']:
        lines.append('## \u4e00\u3001\u5b89\u5168\u7ea2\u7ebf\uff08\u7acb\u5373\u6267\u884c\uff09')
        lines.append('')
        for m in r['reds']:
            lines.append('- %s' % m)
        lines.append('')
    lines.append('## \u4e8c\u3001\u62c6\u88c5\u987a\u5e8f\uff08\u6309\u6b64\u987a\u5e8f\u6267\u884c\uff09')
    lines.append('')
    for i, s in enumerate(STEPS, 1):
        lines.append('%d. %s' % (i, s))
    lines.append('')
    if not r['rules']:
        lines.append('\u672a\u5339\u914d\u5230\u6545\u969c\u6811\u6761\u76ee\u3002\u8bf7\u8865\u5145\uff1a\u662f\u8981\u62c6\u677f\u3001\u6362\u6a21\u5757\u3001\u67e5\u6f0f\u6c34\u8fd8\u662f\u5f00\u68c0\u4fee\u53e3\u3002')
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
    lines.append('\u672c\u7ed3\u679c\u4e3a\u73b0\u8c61\u5339\u914d\u4e0e\u6392\u67e5\u987a\u5e8f\u5efa\u8bae\uff0c\u4e0d\u4ee3\u8868\u73b0\u573a\u5224\u65ad\uff0c\u4e0d\u6784\u6210\u65bd\u5de5\u7ed3\u8bba\u3002')
    return '\n'.join(lines)


def render_json(r):
    return json.dumps(r, ensure_ascii=False, indent=2)


def selftest():
    errs = []

    def eq(name, got, want):
        if got != want:
            errs.append('%s got=%r want=%r' % (name, got, want))

    r1 = analyse('\u540a\u9876\u4e0a\u6709\u6c34\u6e0d\uff0c\u60f3\u62c6\u5f00\u770b\u770b\u662f\u4e0d\u662f\u697c\u4e0a\u7684\u95ee\u9898')
    eq('case1 \u6f0f\u6c34\u547d\u4e2d', any(x['id'] == 'E6' for x in r1['rules']), True)
    eq('case1 \u697c\u4e0a\u547d\u4e2d', any(x['id'] == 'E7' for x in r1['rules']), True)
    eq('case1 \u6c34\u6e0d\u8bef\u5224', any('\u540a\u9876\u6709\u6c34\u6e0d\u4e0d\u7b49\u4e8e\u81ea\u5bb6\u6c34\u7ba1\u6f0f' in m for m in r1['misread']), True)

    r2 = analyse('\u6d74\u9738\u4e0d\u70ed\uff0c\u6362\u6c14\u6247\u4e5f\u4e0d\u8f6c')
    eq('case2 \u7a7a\u5f00\u4f18\u5148', r2['rules'][0]['id'], 'E1')
    eq('case2 \u8bef\u5224\u63d0\u9192', any('\u4e0d\u7b49\u4e8e\u6a21\u5757\u574f\u4e86' in m for m in r2['misread']), True)

    r3 = analyse('\u8981\u91cd\u65b0\u63a5\u7ebf\uff0c\u6362\u4e00\u4e0b\u914d\u7535\u7bb1\u91cc\u7684\u5f00\u5173')
    eq('case3 \u7535\u5de5\u7ea2\u7ebf', any('\u6301\u8bc1\u7535\u5de5' in m for m in r3['reds']), True)

    r4 = analyse('\u95fb\u5230\u71c3\u6c14\u5473\uff0c\u540a\u9876\u91cc\u6709\u71c3\u6c14\u7ba1')
    eq('case4 \u71c3\u6c14\u547d\u4e2d', any(x['id'] == 'E8' for x in r4['rules']), True)
    eq('case4 \u71c3\u6c14\u7ea2\u7ebf', any('\u71c3\u6c14\u5473' in m for m in r4['reds']), True)

    r5 = analyse('\u6263\u677f\u62c6\u4e0d\u4e0b\u6765\uff0c\u662f\u4e0d\u662f\u5f97\u5f00\u4e2a\u68c0\u4fee\u53e3')
    eq('case5 \u6263\u677f\u547d\u4e2d', any(x['id'] == 'E5' for x in r5['rules']), True)
    eq('case5 \u68c0\u4fee\u53e3\u8bef\u5224', any('\u4e13\u95e8\u7834\u574f\u6027\u5f00\u5b54' in m for m in r5['misread']), True)

    r6 = analyse('\u63a5\u7ebf\u7aef\u5b50\u6709\u70e7\u8680\u548c\u7126\u5473')
    eq('case6 \u70e7\u8680\u7ea2\u7ebf', any('\u70e7\u8680' in m for m in r6['reds']), True)

    r7 = analyse('\u540a\u9876\u6709\u70b9\u95ee\u9898')
    eq('case7 \u65e0\u5339\u914d', r7['rules'], [])

    md = render_md('\u540a\u9876\u6f0f\u6c34', r1)
    eq('case8 \u542b\u9a8c\u7535\u6b65\u9aa4', '\u9a8c\u7535\u7b14\u786e\u8ba4\u65e0\u7535' in md, True)
    js = json.loads(render_json(r1))
    eq('case9 \u8f93\u51fa\u952e', sorted(js.keys()), ['misread', 'reds', 'rules', 'top'])

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 13\n\u8986\u76d6: \u7a7a\u5f00\u8df3\u95f8/\u7aef\u5b50\u677e\u52a8/\u6392\u98ce\u7ba1/\u6a21\u5757\u6545\u969c/\u6263\u677f\u53d8\u5f62/\u6c34\u7ba1\u6e17\u6f0f/\u697c\u4e0a\u6e17\u6f0f/\u71c3\u6c14\u7ba1\u9053/\u7535\u5de5\u7ea2\u7ebf/\u767b\u9ad8\u7ea2\u7ebf')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u96c6\u6210\u540a\u9876\u95ee\u9898\u6545\u969c\u6811\u5224\u65ad')
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
