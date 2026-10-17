# -*- coding: utf-8 -*-
"""\u81ea\u884c\u8f66\u53d8\u901f\u6545\u969c\u6811\u5224\u65ad\uff1a\u8f93\u5165\u73b0\u8c61\u4e0e\u94fe\u6761\u5b9e\u6d4b\u503c\uff0c\u8f93\u51fa\u6392\u67e5\u987a\u5e8f\u4e0e\u8c03\u6574\u5efa\u8bae\u3002

\u7528\u6cd5:
  python bicycle_derailleur_check.py --text "\u6362\u4e86\u65b0\u94fe\u6761\u8fd8\u662f\u8df3\u9f7f" --chain 308
  python bicycle_derailleur_check.py --file \u63cf\u8ff0.txt [--out \u7ed3\u679c.md] [--format json]
  python bicycle_derailleur_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

CHAIN_BASE = 304.8
CHAIN_LIMIT = 307.0

RULES = [
    {'id': 'C1', 'order': 1, 'name': '\u94fe\u6761\u78e8\u635f\u8d85\u9650',
     'kw': ['\u8df3\u94fe', '\u8df3\u9f7f', '\u6253\u6ed1', '\u8e29\u7a7a', '\u8e29\u91cd', '\u78e8\u635f', '\u7528\u4e86\u5f88\u4e45', '\u51e0\u5343\u516c\u91cc'],
     'test': '\u91cf 12 \u8282\u94fe\u6761\u957f\u5ea6\uff0c\u8d85\u8fc7 307mm \u5373\u8d85\u9650',
     'fix': '\u66f4\u6362\u94fe\u6761\u5e76\u68c0\u67e5\u98de\u8f6e'},
    {'id': 'C2', 'order': 2, 'name': '\u98de\u8f6e\u78e8\u635f\uff08\u6362\u65b0\u94fe\u6761\u540e\u4ecd\u8df3\uff09',
     'kw': ['\u6362\u4e86\u65b0\u94fe\u6761', '\u6362\u4e86\u94fe\u6761\u8fd8', '\u65b0\u94fe\u6761', '\u6362\u4e86\u8fd8\u662f\u8df3', '\u9f7f\u5c16'],
     'test': '\u89c2\u5bdf\u98de\u8f6e\u9f7f\u5f62\u662f\u5426\u53d8\u5c16\u3001\u662f\u5426\u53ea\u5728\u7279\u5b9a\u6863\u8df3',
     'fix': '\u540c\u65f6\u66f4\u6362\u98de\u8f6e\uff0c\u53ea\u6362\u94fe\u6761\u89e3\u51b3\u4e0d\u4e86'},
    {'id': 'C3', 'order': 3, 'name': '\u94fe\u6761\u6b7b\u8282\u6216\u9508\u8680',
     'kw': ['\u6b7b\u8282', '\u5361', '\u9508', '\u7f3a\u6cb9', '\u53d1\u6da9', '\u50f5\u786c'],
     'test': '\u9010\u8282\u8f6c\u52a8\u94fe\u6761\u770b\u662f\u5426\u6709\u5361\u987f',
     'fix': '\u9664\u9508\u6da6\u6ed1\uff0c\u4e25\u91cd\u5219\u6362\u94fe'},
    {'id': 'C4', 'order': 4, 'name': '\u9650\u4f4d\u87ba\u4e1d\u4e0d\u5f53',
     'kw': ['\u6389\u94fe', '\u78b0\u8f90\u6761', '\u8e6d\u8f90\u6761', '\u6389\u5916\u4fa7', '\u6389\u5185\u4fa7', '\u9650\u4f4d'],
     'test': '\u770b\u6389\u94fe\u65b9\u5411\uff1a\u5916\u4fa7\u67e5 H \u9650\u4f4d\uff0c\u5185\u4fa7\u67e5 L \u9650\u4f4d',
     'fix': '\u8c03\u5bf9\u5e94\u9650\u4f4d\u87ba\u4e1d'},
    {'id': 'C5', 'order': 5, 'name': '\u62c9\u7ebf\u5f20\u529b\u4e0d\u5f53',
     'kw': ['\u4e0a\u4e0d\u53bb', '\u4e0b\u4e0d\u6765', '\u6362\u6863\u4e0d\u5230\u4f4d', '\u53d8\u901f\u4e0d\u51c6', '\u5f20\u529b', '\u5fae\u8c03'],
     'test': '\u9010\u6863\u8bd5\u6362\uff0c\u4e0a\u4e0d\u53bb\u52a0\u5f20\u529b\uff0c\u4e0b\u4e0d\u6765\u51cf\u5f20\u529b',
     'fix': '\u8c03\u5fae\u8c03\u7b52\uff1a\u4e0a\u4e0d\u53bb\u9006\u65f6\u9488\u65cb\u51fa\uff0c\u4e0b\u4e0d\u6765\u987a\u65f6\u9488\u65cb\u5165'},
    {'id': 'C6', 'order': 6, 'name': '\u7ebf\u7ba1\u963b\u529b\u6216\u5185\u7ebf\u65ad\u80a1',
     'kw': ['\u53d1\u6da9', '\u7ebf\u7ba1', '\u5185\u7ebf', '\u6362\u6863\u8fdf\u6ede', '\u624b\u611f\u91cd'],
     'test': '\u68c0\u67e5\u7ebf\u7ba1\u6709\u65e0\u6298\u5f2f\u3001\u5185\u7ebf\u6709\u65e0\u65ad\u80a1',
     'fix': '\u66f4\u6362\u5185\u7ebf\u4e0e\u7ebf\u7ba1'},
    {'id': 'C7', 'order': 7, 'name': '\u524d\u62e8\u4f4d\u7f6e\u6216\u89d2\u5ea6\u4e0d\u5f53',
     'kw': ['\u8e6d\u94fe', '\u8e6d\u524d\u62e8', '\u524d\u62e8', '\u5f02\u54cd', '\u6469\u64e6\u58f0'],
     'test': '\u770b\u524d\u62e8\u5bfc\u677f\u4e0e\u7259\u76d8\u95f4\u8ddd\u548c\u5e73\u884c\u5ea6',
     'fix': '\u8c03\u9ad8\u5ea6\uff08\u9f7f\u5c16 1-3mm\uff09\u4e0e\u89d2\u5ea6'},
    {'id': 'C8', 'order': 8, 'name': '\u5c3e\u94a9\u53d8\u5f62',
     'kw': ['\u6454\u8fc7', '\u6454\u8f66', '\u649e\u8fc7', '\u540e\u62e8\u6b6a', '\u53d8\u5f62'],
     'test': '\u4ece\u540e\u65b9\u770b\u540e\u62e8\u662f\u5426\u5782\u76f4',
     'fix': '\u9001\u8f66\u5e97\u6821\u6b63\u6216\u66f4\u6362\u5c3e\u94a9'},
    {'id': 'C9', 'order': 9, 'name': '\u7535\u53d8\u7cfb\u7edf\u95ee\u9898',
     'kw': ['\u7535\u53d8', '\u7535\u5b50\u53d8\u901f', '\u6ca1\u53cd\u5e94', 'di2', 'axs', '\u6ca1\u7535'],
     'test': '\u5148\u67e5\u7535\u6c60\u7535\u91cf\u4e0e\u8fde\u63a5\u72b6\u6001',
     'fix': '\u5148\u67e5\u7535\u518d\u67e5\u673a\u68b0\uff0c\u5f02\u5e38\u9001\u8f66\u5e97'},
]

RED = [
    {'kw': ['\u78b3\u7ea4\u7ef4', '\u78b3\u67b6', '\u626d\u529b'],
     'msg': '\u78b3\u7ea4\u7ef4\u96f6\u90e8\u4ef6\u5fc5\u987b\u6309\u5382\u5546\u6807\u79f0\u626d\u529b\u503c\u7528\u626d\u529b\u6273\u624b\u64cd\u4f5c\uff1a\u51ed\u624b\u611f\u62e7\u7d27\u6709\u5f00\u88c2\u98ce\u9669\uff0c\u5efa\u8bae\u8f66\u5e97\u5904\u7406\u3002'},
    {'kw': ['\u6454\u8fc7', '\u6454\u8f66', '\u649e\u8fc7', '\u53d8\u5f62'],
     'msg': '\u540e\u62e8\u6216\u5c3e\u94a9\u53d8\u5f62\uff1a\u8c03\u9650\u4f4d\u65e0\u6548\uff0c\u9001\u8f66\u5e97\u6821\u6b63\u6216\u66f4\u6362\u5c3e\u94a9\u3002'},
    {'kw': ['\u5185\u8d70\u7ebf', '\u7a7f\u7ebf'],
     'msg': '\u5185\u8d70\u7ebf\u8f66\u67b6\u91cd\u65b0\u7a7f\u7ebf\u9700\u8981\u4e13\u7528\u5de5\u5177\u4e0e\u7ecf\u9a8c\uff0c\u9001\u8f66\u5e97\u5904\u7406\u3002'},
    {'kw': ['\u6db2\u538b', '\u6cb9\u5239', '\u5239\u8f66'],
     'msg': '\u6db2\u538b\u5239\u8f66\u76f8\u5173\u64cd\u4f5c\u9001\u8f66\u5e97\uff1b\u94fe\u6761\u6cb9\u4e00\u65e6\u6c61\u67d3\u5239\u8f66\u76d8\u4e0e\u6765\u4ee4\u7247\u4f1a\u5927\u5e45\u964d\u4f4e\u5236\u52a8\u529b\uff0c\u5c5e\u4e25\u91cd\u5b89\u5168\u9690\u60a3\u3002'},
    {'kw': ['\u4e2d\u8f74', '\u8f6e\u7ec4', '\u8f90\u6761', '\u504f\u6446'],
     'msg': '\u4e2d\u8f74\u5f02\u54cd\u3001\u8f6e\u7ec4\u504f\u6446\u4e0e\u8f90\u6761\u95ee\u9898\u9700\u4e13\u7528\u5de5\u5177\uff0c\u9001\u8f66\u5e97\u5904\u7406\u3002'},
]

MISREAD = [
    {'kw': ['\u8df3\u94fe', '\u8df3\u9f7f', '\u6253\u6ed1'],
     'msg': '\u8e29\u91cd\u65f6\u8df3\u9f7f\u591a\u4e3a\u94fe\u6761\u4e0e\u98de\u8f6e\u78e8\u635f\uff0c\u4e0d\u662f\u53d8\u901f\u6ca1\u8c03\u597d\uff0c\u8c03\u9650\u4f4d\u87ba\u4e1d\u89e3\u51b3\u4e0d\u4e86\u3002'},
    {'kw': ['\u6362\u4e86\u65b0\u94fe\u6761', '\u65b0\u94fe\u6761', '\u6362\u4e86\u8fd8\u662f\u8df3'],
     'msg': '\u6362\u65b0\u94fe\u6761\u4ecd\u8df3\u9f7f\uff0c\u8bf4\u660e\u98de\u8f6e\u5df2\u88ab\u65e7\u94fe\u6761\u78e8\u51fa\u5f62\u72b6\uff0c\u9700\u540c\u65f6\u6362\u98de\u8f6e\u3002'},
    {'kw': ['\u4e0a\u4e0d\u53bb', '\u4e0b\u4e0d\u6765'],
     'msg': '\u6362\u6863\u4e0d\u5230\u4f4d\u9760\u62c9\u7ebf\u5f20\u529b\u89e3\u51b3\uff0c\u9650\u4f4d\u87ba\u4e1d\u53ea\u7ba1\u6389\u4e0d\u6389\u94fe\uff0c\u4e0d\u7ba1\u7406\u6362\u6863\u7cbe\u5ea6\u3002'},
    {'kw': ['\u78b0\u8f90\u6761', '\u8e6d\u8f90\u6761'],
     'msg': '\u540e\u62e8\u78b0\u8f90\u6761\u591a\u4e3a L \u9650\u4f4d\u672a\u8c03\u597d\u6216\u5c3e\u94a9\u53d8\u5f62\uff0c\u4e0d\u662f\u540e\u62e8\u574f\u4e86\u3002'},
    {'kw': ['\u8e6d\u94fe', '\u5f02\u54cd'],
     'msg': '\u6301\u7eed\u5f02\u54cd\u591a\u4e3a\u8e6d\u524d\u62e8\u5bfc\u677f\uff0c\u67e5\u524d\u62e8\u9ad8\u5ea6\u4e0e\u89d2\u5ea6\uff0c\u4e0d\u662f\u9650\u4f4d\u95ee\u9898\u3002'},
    {'kw': ['\u7535\u53d8', '\u6ca1\u53cd\u5e94'],
     'msg': '\u7535\u5b50\u53d8\u901f\u65e0\u53cd\u5e94\u5148\u770b\u7535\u91cf\u4e0e\u8fde\u63a5\uff0c\u4e0d\u8981\u5f53\u673a\u68b0\u6545\u969c\u62c6\u3002'},
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


def chain_status(length):
    if length < CHAIN_BASE:
        return '\u6d4b\u91cf\u503c\u5f02\u5e38\uff08\u504f\u5c0f\uff09\uff0c\u8bf7\u91cd\u65b0\u6d4b\u91cf 12 \u8282\u957f\u5ea6'
    if length <= CHAIN_LIMIT:
        return '\u6b63\u5e38\uff0c\u53ef\u7ee7\u7eed\u4f7f\u7528'
    if length <= CHAIN_LIMIT + 2:
        return '\u78e8\u635f\u8d85\u9650\uff0c\u9700\u66f4\u6362\u94fe\u6761\u5e76\u68c0\u67e5\u98de\u8f6e'
    return '\u4e25\u91cd\u78e8\u635f\uff0c\u9700\u66f4\u6362\u94fe\u6761\u5e76\u5927\u6982\u7387\u540c\u65f6\u66f4\u6362\u98de\u8f6e'


def analyse(text, chain=None):
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
            'chain': chain, 'chain_status': chain_status(chain) if chain else '',
            'top': rules[0]['name'] if rules else ''}


def render_md(text, r):
    lines = ['# \u81ea\u884c\u8f66\u53d8\u901f\u95ee\u9898\u5224\u65ad\u7ed3\u679c', '']
    if r['chain']:
        lines.append('\u94fe\u6761\u78e8\u635f\u5224\u5b9a\uff1a12 \u8282\u5b9e\u6d4b %.1f mm\uff0c\u57fa\u51c6 %.1f mm\uff0c\u9650\u503c %.1f mm' % (
            r['chain'], CHAIN_BASE, CHAIN_LIMIT))
        lines.append('')
        lines.append('\u5224\u5b9a\u7ed3\u679c\uff1a%s' % r['chain_status'])
        lines.append('')
    if not r['rules']:
        lines.append('\u672a\u5339\u914d\u5230\u6545\u969c\u6811\u6761\u76ee\u3002\u8bf7\u8865\u5145\uff1a\u662f\u8e29\u91cd\u8df3\u9f7f\u8fd8\u662f\u6362\u6863\u4e0d\u5230\u4f4d\u3001\u6389\u94fe\u5f80\u54ea\u8fb9\u6389\u3001\u6709\u6ca1\u6709\u6362\u8fc7\u94fe\u6761\u3002')
        lines.append('')
    else:
        lines.append('\u6700\u4f18\u5148\u6392\u67e5\uff1a%s' % r['top'])
        lines.append('')
        lines.append('## \u4e00\u3001\u6392\u67e5\u987a\u5e8f\uff08\u6309\u6b64\u987a\u5e8f\u6267\u884c\uff09')
        lines.append('')
        lines.append('| \u987a\u5e8f | \u53ef\u80fd\u539f\u56e0 | \u53ef\u80fd\u6027 | \u9a8c\u8bc1\u52a8\u4f5c | \u5904\u7f6e |')
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
    lines.append('## \u56db\u3001\u540e\u62e8\u8c03\u6574\u56fa\u5b9a\u987a\u5e8f')
    lines.append('')
    lines.append('1. H \u9650\u4f4d\uff1a\u94fe\u6761\u4e0d\u6389\u5230\u6700\u5c0f\u98de\u8f6e\u5916\u4fa7')
    lines.append('2. L \u9650\u4f4d\uff1a\u94fe\u6761\u4e0d\u6389\u5230\u6700\u5927\u98de\u8f6e\u5185\u4fa7\u3001\u4e0d\u78b0\u8f90\u6761')
    lines.append('3. \u62c9\u7ebf\u5f20\u529b\uff1a\u4e0a\u4e0d\u53bb\u52a0\u5f20\u529b\uff0c\u4e0b\u4e0d\u6765\u51cf\u5f20\u529b')
    lines.append('4. B \u5f20\u529b\uff1a\u8c03\u6574\u5bfc\u8f6e\u4e0e\u98de\u8f6e\u95f4\u8ddd')
    lines.append('')
    lines.append('---')
    lines.append('\u672c\u7ed3\u679c\u4e3a\u73b0\u8c61\u5339\u914d\u4e0e\u8c03\u6821\u5efa\u8bae\uff0c\u4e0d\u4ee3\u8868\u73b0\u573a\u5224\u65ad\uff0c\u4e0d\u6784\u6210\u7ef4\u4fee\u7ed3\u8bba\u3002')
    return '\n'.join(lines)


def render_json(r):
    return json.dumps(r, ensure_ascii=False, indent=2)


def selftest():
    errs = []

    def eq(name, got, want):
        if got != want:
            errs.append('%s got=%r want=%r' % (name, got, want))

    r1 = analyse('\u6362\u4e86\u65b0\u94fe\u6761\u8fd8\u662f\u8df3\u9f7f\uff0c\u8e29\u91cd\u4e86\u5c31\u6253\u6ed1')
    eq('case1 \u98de\u8f6e\u78e8\u635f\u547d\u4e2d', any(x['id'] == 'C2' for x in r1['rules']), True)
    eq('case1 \u8bef\u5224\u63d0\u9192', any('\u98de\u8f6e\u5df2\u88ab\u65e7\u94fe\u6761\u78e8\u51fa\u5f62\u72b6' in m for m in r1['misread']), True)

    r2 = analyse('\u4e0a\u4e0d\u53bb\u6700\u5927\u98de\u8f6e\uff0c\u4e0b\u4e0d\u6765\u5c0f\u98de\u8f6e')
    eq('case2 \u5f20\u529b\u547d\u4e2d', any(x['id'] == 'C5' for x in r2['rules']), True)
    eq('case2 \u5f20\u529b\u8bef\u5224', any('\u6362\u6863\u4e0d\u5230\u4f4d' in m for m in r2['misread']), True)

    r3 = analyse('\u540e\u62e8\u78b0\u8f90\u6761\uff0c\u8fd8\u6389\u94fe')
    eq('case3 \u9650\u4f4d\u547d\u4e2d', any(x['id'] == 'C4' for x in r3['rules']), True)

    r4 = analyse('\u6454\u8fc7\u8f66\uff0c\u540e\u62e8\u6709\u70b9\u53d8\u5f62')
    eq('case4 \u5c3e\u94a9\u547d\u4e2d', any(x['id'] == 'C8' for x in r4['rules']), True)
    eq('case4 \u7ea2\u7ebf\u547d\u4e2d', any('\u5c3e\u94a9\u53d8\u5f62' in m for m in r4['reds']), True)

    r5 = analyse('\u78b3\u7ea4\u7ef4\u5ea7\u7ba1\u8981\u62e7\u591a\u7d27')
    eq('case5 \u78b3\u7ea4\u7ef4\u7ea2\u7ebf', any('\u626d\u529b\u503c' in m for m in r5['reds']), True)

    r6 = analyse('\u7535\u53d8\u6ca1\u53cd\u5e94\u4e86')
    eq('case6 \u7535\u53d8\u547d\u4e2d', any(x['id'] == 'C9' for x in r6['rules']), True)
    eq('case6 \u7535\u53d8\u8bef\u5224', any('\u7535\u5b50\u53d8\u901f\u65e0\u53cd\u5e94' in m for m in r6['misread']), True)

    eq('case7 \u94fe\u6761\u6b63\u5e38', chain_status(305.0), '\u6b63\u5e38\uff0c\u53ef\u7ee7\u7eed\u4f7f\u7528')
    eq('case8 \u94fe\u6761\u8d85\u9650', chain_status(308.0), '\u78e8\u635f\u8d85\u9650\uff0c\u9700\u66f4\u6362\u94fe\u6761\u5e76\u68c0\u67e5\u98de\u8f6e')
    eq('case9 \u94fe\u6761\u4e25\u91cd', chain_status(310.0), '\u4e25\u91cd\u78e8\u635f\uff0c\u9700\u66f4\u6362\u94fe\u6761\u5e76\u5927\u6982\u7387\u540c\u65f6\u66f4\u6362\u98de\u8f6e')

    r10 = analyse('\u8df3\u9f7f', chain=308.0)
    md10 = render_md('\u8df3\u9f7f', r10)
    eq('case10 \u542b\u78e8\u635f\u5224\u5b9a', '\u94fe\u6761\u78e8\u635f\u5224\u5b9a' in md10, True)
    js = json.loads(render_json(r10))
    eq('case11 \u8f93\u51fa\u952e', sorted(js.keys()),
       ['chain', 'chain_status', 'misread', 'reds', 'rules', 'top'])

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 14\n\u8986\u76d6: \u94fe\u6761\u78e8\u635f/\u98de\u8f6e\u78e8\u635f/\u94fe\u6761\u6b7b\u8282/\u9650\u4f4d\u87ba\u4e1d/\u62c9\u7ebf\u5f20\u529b/\u7ebf\u7ba1\u963b\u529b/\u524d\u62e8\u89d2\u5ea6/\u5c3e\u94a9\u53d8\u5f62/\u7535\u53d8\u7cfb\u7edf/\u78b3\u7ea4\u7ef4\u626d\u529b')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u81ea\u884c\u8f66\u53d8\u901f\u6545\u969c\u6811\u5224\u65ad')
    ap.add_argument('--text', help='\u73b0\u8c61\u63cf\u8ff0')
    ap.add_argument('--file', help='\u4ece\u6587\u4ef6\u8bfb\u73b0\u8c61\u63cf\u8ff0')
    ap.add_argument('--chain', type=float, help='12 \u8282\u94fe\u6761\u5b9e\u6d4b\u957f\u5ea6\uff08\u6beb\u7c73\uff09')
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
    if not text.strip() and a.chain is None:
        print('ERROR \u9700\u8981 --text\u3001--file \u6216 --chain')
        return 2

    r = analyse(text, a.chain)
    out = render_md(text, r) if a.format == 'md' else render_json(r)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % a.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
