# -*- coding: utf-8 -*-
"""\u6cb9\u70df\u673a\u6e05\u6d17\u5224\u5b9a\uff1a\u6309\u4e09\u4fe1\u53f7\u5224\u65ad\u662f\u5426\u8be5\u6d17\u3001\u7ed9\u5206\u90e8\u4f4d\u8981\u70b9\u3001\u68c0\u67e5\u6e05\u6d01\u5242\u914d\u5bf9\u4e0e\u5b89\u5168\u7ea2\u7ebf\u3002

\u7528\u6cd5:
  python hood_clean_check.py --text "\u5438\u529b\u53d8\u5c0f\u4e86\uff0c\u8fd8\u6709\u5f02\u54cd"
  python hood_clean_check.py --pair "\u542b\u6c2f\u6d88\u6bd2\u6db2" "\u767d\u918b"
  python hood_clean_check.py --file \u60c5\u51b5.txt --out \u7ed3\u679c.md
  python hood_clean_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ---- \u6e05\u6d17\u89e6\u53d1\u4e09\u4fe1\u53f7 ----
SIGNALS = [
    {'id': 'S1', 'name': '\u6cb9\u57a2\u539a\u5ea6',
     'kw': ['\u6cb9\u57a2', '\u6cb9\u819c', '\u6cb9\u817b', '\u6cb9\u7f51\u5f88\u810f', '\u6cb9\u7f51\u900f\u5149', '\u5f88\u810f', '\u6cb9\u539a'],
     'judge': '\u53d6\u51fa\u6cb9\u7f51\u76ee\u89c6\uff0c\u6709\u660e\u663e\u6cb9\u819c\u6216\u6cb9\u57a2\u5806\u79ef\uff1b\u6cb9\u7f51\u900f\u5149\u660e\u663e\u53d8\u5dee\u5373\u9700\u6e05\u6d17'},
    {'id': 'S2', 'name': '\u5438\u529b\u4e0b\u964d',
     'kw': ['\u5438\u529b', '\u5438\u529b\u5dee', '\u5438\u529b\u5c0f', '\u5438\u70df\u5dee', '\u62bd\u4e0d\u52a8', '\u8dd1\u70df', '\u5438\u4e0d\u52a8'],
     'judge': '\u540c\u6837\u706b\u529b\u4e0e\u9505\u5177\u4e0b\uff0c\u611f\u89c9\u5438\u529b\u4e0d\u5982\u4ee5\u524d'},
    {'id': 'S3', 'name': '\u566a\u97f3\u53d8\u5316',
     'kw': ['\u5f02\u54cd', '\u566a\u97f3', '\u58f0\u97f3\u53d8', '\u6469\u64e6\u58f0', '\u54cd\u5f97', '\u58f0\u97f3\u5927'],
     'judge': '\u8fd0\u884c\u58f0\u97f3\u53d8\u9ad8\u3001\u53d8\u5c16\u3001\u51fa\u73b0\u6469\u64e6\u58f0'},
]

# ---- \u8f85\u52a9\u4fe1\u53f7 ----
AUX = [
    {'kw': ['\u6cb9\u676f\u5feb\u6ee1', '\u79ef\u6cb9\u5feb', '\u6cb9\u676f\u6ee1', '\u79ef\u6cb9\u7279\u522b\u5feb', '\u6cb9\u676f\u51e0\u5929\u6ee1'], 'msg': '\u6cb9\u676f\u79ef\u6cb9\u901f\u5ea6\u660e\u663e\u53d8\u5feb\uff0c\u662f\u6e05\u6d17\u65f6\u673a\u5df2\u5230\u7684\u8f85\u52a9\u4fe1\u53f7'},
    {'kw': ['\u9762\u677f', '\u73bb\u7483', '\u6cb9\u96fe', '\u8499', '\u8d77\u96fe'],
     'msg': '\u73bb\u7483\u9762\u677f\u6cb9\u96fe\u8986\u76d6\u8303\u56f4\u6269\u5927\uff0c\u5c5e\u8f85\u52a9\u4fe1\u53f7'},
    {'kw': ['\u7076\u53f0\u6cb9', '\u7076\u53f0\u810f', '\u6cb9\u6c61'],
     'msg': '\u7076\u53f0\u9644\u8fd1\u6cb9\u6c61\u589e\u52a0\uff0c\u5c5e\u8f85\u52a9\u4fe1\u53f7'},
]

# ---- \u4e0d\u6e05\u6d01\u7684\u4e94\u79cd\u540e\u679c ----
CONSEQ = [
    ('\u5438\u529b\u4e0b\u964d', '\u98ce\u8f6e\u4e0e\u98ce\u9053\u88ab\u6cb9\u57a2\u5360\u636e\uff0c\u6c14\u6d41\u53d7\u963b'),
    ('\u6cb9\u70df\u5012\u704c', '\u6392\u98ce\u4e0d\u7545\uff0c\u538b\u529b\u53d8\u5316\u5bfc\u81f4\u6cb9\u70df\u56de\u6d41'),
    ('\u5f02\u54cd', '\u6cb9\u57a2\u5bfc\u81f4\u52a8\u5e73\u8861\u6539\u53d8\uff0c\u6216\u90e8\u4ef6\u677e\u52a8'),
    ('\u8017\u7535\u589e\u52a0', '\u98ce\u91cf\u4e0b\u964d\u65f6\u673a\u5668\u53ef\u80fd\u4ee5\u66f4\u9ad8\u529f\u7387\u8fd0\u884c'),
    ('\u706b\u707e\u9690\u60a3', '\u957f\u671f\u6cb9\u57a2\u79ef\u805a\u9047\u9ad8\u6e29\u5b58\u5728\u8d77\u706b\u98ce\u9669'),
]

# ---- \u5206\u90e8\u4f4d\u6e05\u6d17\u8981\u70b9 ----
PARTS = [
    ('\u6cb9\u676f', '\u53ef\u53d6\u4e0b\u76f4\u63a5\u6e05\u6d17\uff0c\u7528\u6e29\u6c34\u914d\u4e2d\u6027\u6e05\u6d01\u5242\u6d78\u6ce1\u540e\u5237\u6d17', '\u53d6\u4e0b\u65f6\u53ef\u80fd\u6709\u6b8b\u6cb9\uff0c\u7528\u5bb9\u5668\u63a5\u4f4f'),
    ('\u6cb9\u7f51', '\u53ef\u53d6\u4e0b\uff0c\u7528\u6e29\u6c34\u914d\u4e2d\u6027\u6e05\u6d01\u5242\u6d78\u6ce1\u540e\u5237\u6d17', '\u51b2\u51c0\u540e\u5f7b\u5e95\u667e\u5e72\u518d\u88c5\u56de'),
    ('\u957f\u6761\u5f62\u6321\u677f\u6216\u6ee4\u677f', '\u53d6\u4e0b\u6e05\u6d17\uff0c\u52a8\u4f5c\u8f7b\uff0c\u907f\u514d\u53d8\u5f62', '\u88c5\u56de\u65f6\u786e\u8ba4\u5361\u5230\u4f4d'),
    ('\u98ce\u8f6e', '\u9700\u8c28\u614e\uff0c\u4e00\u822c\u53ea\u505a\u8868\u9762\u64e6\u62ed', '\u62c6\u98ce\u8f6e\u5c5e\u4e8e\u7ef4\u4fee\u8303\u56f4\uff1b\u91cd\u6cb9\u7ed3\u57a2\u786c\u5316\u65f6\u8f6c\u4e13\u4e1a'),
    ('\u5916\u58f3\u4e0e\u73bb\u7483\u9762\u677f', '\u5fae\u6e7f\u8f6f\u5e03\u914d\u4e2d\u6027\u6e05\u6d01\u5242\u64e6\u62ed', '\u907f\u514d\u6db2\u4f53\u6d41\u5165\u7f1d\u9699\u4e0e\u7535\u8def\u533a'),
    ('\u53f6\u8f6e\u4e0e\u7535\u673a\u8868\u9762', '\u53ea\u505a\u76ee\u89c6\u4e0e\u8f7b\u5fae\u64e6\u62ed', '\u4e0d\u5f97\u55b7\u6dcb\u3001\u4e0d\u5f97\u62c6\u89e3\uff1b\u6cb9\u6c61\u591a\u65f6\u8f6c\u4e13\u4e1a'),
]

# ---- \u7c7b\u578b\u5dee\u5f02 ----
TYPES = [
    ('\u9876\u5438\u5f0f', '\u4f4d\u7f6e\u9ad8\uff0c\u6e05\u6d17\u9700\u68af\u5177', '\u6cb9\u7f51\u6cb9\u676f\u53ef\u81ea\u884c\u6e05\u6d17\uff1b\u9ad8\u5904\u4f5c\u4e1a\u6ce8\u610f\u9632\u5760\u843d\uff1b\u5916\u58f3\u64e6\u62ed\u5efa\u8bae\u4e24\u4eba\u914d\u5408'),
    ('\u4fa7\u5438\u5f0f', '\u4f4d\u7f6e\u4f4e\uff0c\u8f83\u5b89\u5168', '\u81ea\u884c\u6e05\u6d17\u76f8\u5bf9\u5bb9\u6613\uff1b\u73bb\u7483\u9762\u677f\u6cb9\u96fe\u9700\u91cd\u70b9\u6e05\u7406'),
    ('\u96c6\u6210\u7076', '\u7ed3\u6784\u7d27\u51d1\uff0c\u6cb9\u8def\u4e0e\u7076\u4f53\u4e00\u4f53', '\u6df1\u5ea6\u62c6\u6d17\u5c5e\u4e13\u4e1a\u8303\u56f4\uff1b\u65e5\u5e38\u53ea\u505a\u8868\u9762\u4e0e\u53ef\u53d6\u4e0b\u90e8\u4ef6\u6e05\u6d01'),
    ('\u6b27\u5f0f\u5185\u5d4c\u5f0f', '\u90e8\u4ef6\u591a\uff0c\u62c6\u88c5\u590d\u6742', '\u62c6\u88c5\u590d\u6742\u5ea6\u9ad8\uff0c\u5efa\u8bae\u4ea4\u4e13\u4e1a\u4eba\u5458'),
]

# ---- \u6e05\u6d01\u5242\u7c7b\u522b ----
CHLORINE = ['\u542b\u6c2f', '\u6f02\u767d\u6c34', '\u6d88\u6bd2\u6db2', '84', '\u6b21\u6c2f\u9178\u94a0', '\u6c2f']
ACID = ['\u9178\u6027', '\u6d01\u5395\u7075', '\u6d01\u5395\u5242', '\u767d\u918b', '\u918b', '\u67e0\u6aac\u9178', '\u9664\u57a2\u5242', '\u67e0\u6aac', '\u76d0\u9178']
ALKALI = ['\u78b1\u6027', '\u5f3a\u78b1', '\u706b\u78b1', '\u70e7\u78b1', '\u5c0f\u82cf\u6253', '\u78b3\u9178\u94a0', '\u5f3a\u9178', '\u786b\u9178']


def classify_pair(a, b):
    ta = (a or '') + ' ' + (b or '')
    has_cl = any(k in ta for k in CHLORINE)
    has_ac = any(k in ta for k in ACID)
    has_al = any(k in ta for k in ALKALI)
    if has_cl and has_ac:
        return ('danger', '\u4e25\u7981\u5c06\u542b\u6c2f\u6d88\u6bd2\u5242\u4e0e\u9178\u6027\u6e05\u6d01\u5242\u6df7\u5408\uff0c\u4e24\u8005\u4f1a\u4ea7\u751f\u6709\u6bd2\u6c14\u4f53\u5e76\u523a\u6fc0\u547c\u5438\u9053')
    if has_cl and has_al:
        return ('danger', '\u542b\u6c2f\u6d88\u6bd2\u5242\u4e0e\u78b1\u6027\u6e05\u6d01\u5242\u4e0d\u5c5e\u4e8e\u5b89\u5168\u914d\u5bf9\uff0c\u53ef\u80fd\u4ea7\u751f\u523a\u6fc0\u6027\u6c14\u4f53')
    if has_cl and '\u542b\u6c2f' in (a or '') and '\u542b\u6c2f' in (b or ''):
        return ('danger', '\u4e24\u79cd\u542b\u6c2f\u4ea7\u54c1\u6df7\u5408\u540e\u6709\u6548\u6210\u5206\u53e0\u52a0\uff0c\u5c5e\u4e0d\u53ef\u63a7\u914d\u5bf9')
    return ('ok', '\u672a\u547d\u4e2d\u5df2\u77e5\u5371\u9669\u914d\u5bf9\uff0c\u4ecd\u9700\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e66\u4e3a\u51c6\uff0c\u4e0d\u540c\u4ea7\u54c1\u4e0d\u53ef\u6df7\u7528')


def analyse(text):
    t = (text or '').replace(' ', '').replace('\u3000', '')
    sigs = []
    for s in SIGNALS:
        hits = [k for k in s['kw'] if k in t]
        if hits:
            sigs.append({'name': s['name'], 'hits': hits, 'judge': s['judge']})
    aux = [a['msg'] for a in AUX if any(k in t for k in a['kw'])]
    types = [t0[0] for t0 in TYPES if t0[0] in t]
    need_pro = any(k in t for k in ['\u96c6\u6210\u7076', '\u7ed3\u57a2\u786c\u5316', '\u786c\u5316', '\u7535\u673a', '\u7535\u8def', '\u62c6\u673a', '\u9707\u52a8', '\u4f4d\u79fb', '\u91cd\u65b0\u56fa\u5b9a'])
    return {'signals': sigs, 'aux': aux, 'types': types, 'need_pro': need_pro,
            'n_signal': len(sigs), 'should_clean': len(sigs) >= 1}


def render_md(r, pair_info=None):
    lines = ['# \u6cb9\u70df\u673a\u6e05\u6d17\u5224\u5b9a\u7ed3\u679c', '']
    lines.append('> \u7528\u4e09\u4e2a\u4fe1\u53f7\u5224\u65ad\u6e05\u6d17\u65f6\u673a\uff0c\u4e0d\u6309\u56fa\u5b9a\u6708\u6570\u3002\u6e05\u6d17\u524d\u5fc5\u987b\u65ad\u7535\u3002')
    lines.append('')
    if pair_info:
        lines.append('## \u6e05\u6d01\u5242\u914d\u5bf9\u68c0\u67e5')
        lines.append('')
        lines.append('- \u4ea7\u54c1 A\uff1a%s' % pair_info[0])
        lines.append('- \u4ea7\u54c1 B\uff1a%s' % pair_info[1])
        lines.append('- \u7b49\u7ea7\uff1a%s' % pair_info[2])
        lines.append('- \u8bf4\u660e\uff1a%s' % pair_info[3])
        lines.append('')

    lines.append('## \u4e00\u3001\u6e05\u6d17\u89e6\u53d1\u4fe1\u53f7\uff08\u547d\u4e2d %d \u9879\uff09' % r['n_signal'])
    lines.append('')
    if not r['signals']:
        lines.append('\u672a\u8bc6\u522b\u5230\u89e6\u53d1\u4fe1\u53f7\u3002\u53ef\u63cf\u8ff0\uff1a\u6cb9\u7f51\u662f\u5426\u6cb9\u817b\u3001\u5438\u529b\u662f\u5426\u4e0b\u964d\u3001\u58f0\u97f3\u662f\u5426\u6709\u53d8\u5316\u3002')
    else:
        lines.append('| \u4fe1\u53f7 | \u547d\u4e2d\u7ebf\u7d22 | \u5224\u65ad\u65b9\u6cd5 |')
        lines.append('|---|---|---|')
        for s in r['signals']:
            lines.append('| %s | %s | %s |' % (s['name'], '\u3001'.join(s['hits']), s['judge']))
    lines.append('')
    if r['aux']:
        lines.append('**\u8f85\u52a9\u4fe1\u53f7\uff1a**')
        lines.append('')
        for m in r['aux']:
            lines.append('- %s' % m)
        lines.append('')
    lines.append('**\u5224\u5b9a**\uff1a%s' % ('\u8be5\u5b89\u6392\u6e05\u6d17\u4e86\u3002\u4e09\u4e2a\u4fe1\u53f7\u4efb\u4e00\u547d\u4e2d\u5373\u9700\u6e05\u6d17\u3002'
                                     if r['should_clean'] else '\u6682\u672a\u547d\u4e2d\u89e6\u53d1\u4fe1\u53f7\uff0c\u53ef\u7ee7\u7eed\u89c2\u5bdf\u3002'))
    lines.append('')

    lines.append('## \u4e8c\u3001\u5206\u90e8\u4f4d\u6e05\u6d17\u8981\u70b9')
    lines.append('')
    lines.append('| \u90e8\u4f4d | \u6e05\u6d17\u8981\u70b9 | \u6ce8\u610f |')
    lines.append('|---|---|---|')
    for a, b, c in PARTS:
        lines.append('| %s | %s | %s |' % (a, b, c))
    lines.append('')
    lines.append('**\u987a\u5e8f**\uff1a\u6cb9\u676f\u4e0e\u6cb9\u7f51 \u2192 \u6321\u677f\u6ee4\u677f \u2192 \u5916\u58f3\u9762\u677f \u2192 \u98ce\u8f6e\u8868\u9762\u76ee\u89c6\u3002\u5148\u53d6\u4e0b\u7684\u5148\u6d17\uff0c\u5e72\u71e5\u540e\u6700\u540e\u88c5\u3002')
    lines.append('')

    lines.append('## \u4e09\u3001\u4e0d\u540c\u7c7b\u578b\u7684\u6e05\u6d17\u5dee\u5f02')
    lines.append('')
    if r['types']:
        lines.append('\u672c\u6b21\u6d89\u53ca\uff1a%s' % '\u3001'.join(r['types']))
        lines.append('')
    lines.append('| \u7c7b\u578b | \u6e05\u6d17\u96be\u70b9 | \u5efa\u8bae |')
    lines.append('|---|---|---|')
    for a, b, c in TYPES:
        lines.append('| %s | %s | %s |' % (a, b, c))
    lines.append('')

    lines.append('## \u56db\u3001\u5b89\u5168\u7ea2\u7ebf')
    lines.append('')
    lines.append('1. **\u6e05\u6d17\u524d\u5fc5\u987b\u65ad\u7535**\uff1a\u62d4\u63d2\u5934\u6216\u5173\u914d\u7535\u7bb1\u5bf9\u5e94\u56de\u8def\uff0c\u4e0d\u8981\u53ea\u5173\u9762\u677f\u6309\u94ae\uff1b\u624b\u90e8\u4fdd\u6301\u5e72\u71e5\u3002')
    lines.append('2. **\u9ad8\u5904\u4e0e\u62c6\u673a\u6709\u89e6\u7535\u4e0e\u5760\u843d\u98ce\u9669**\uff1a\u4e0d\u8981\u7ad9\u5728\u51f3\u5b50\u6216\u6905\u5b50\u4e0a\u505a\u4e0d\u53ef\u63a7\u52a8\u4f5c\uff1b\u62c6\u673a\u524d\u786e\u8ba4\u673a\u5668\u7a33\u56fa\u3002')
    lines.append('3. **\u6e05\u6d17\u5242\u4e25\u7981\u6df7\u5408\u4f7f\u7528**\uff1a\u542b\u6c2f\u6d88\u6bd2\u5242\u4e0e\u9178\u6027\u6e05\u6d01\u5242\u6df7\u5408\u4f1a\u4ea7\u751f\u6709\u6bd2\u6c14\u4f53\uff1b\u4e00\u6b21\u53ea\u7528\u4e00\u79cd\u3002')
    lines.append('4. **\u62c6\u88c5\u540e\u5fc5\u987b\u786e\u8ba4\u6240\u6709\u90e8\u4ef6\u88c5\u56de\u4e14\u65e0\u6f0f\u88c5**\uff1a\u9010\u4ef6\u6838\u5bf9\u6cb9\u676f\u3001\u6cb9\u7f51\u3001\u6321\u677f\u3001\u76d6\u677f\u3001\u87ba\u4e1d\u3002')
    lines.append('5. **\u6e05\u6d01\u5242\u4e0d\u5f97\u55b7\u5165\u7535\u673a\u4e0e\u7535\u8def\u90e8\u4f4d**\uff1a\u53ea\u80fd\u5fae\u6e7f\u5e03\u64e6\u62ed\uff0c\u55b7\u6dcb\u540e\u5fc5\u987b\u5145\u5206\u5e72\u71e5\u518d\u901a\u7535\u3002')
    lines.append('')

    lines.append('## \u4e94\u3001\u4e0d\u6e05\u6d01\u7684\u4e94\u79cd\u540e\u679c')
    lines.append('')
    lines.append('| \u540e\u679c | \u8868\u73b0\u673a\u5236 |')
    lines.append('|---|---|')
    for a, b in CONSEQ:
        lines.append('| %s | %s |' % (a, b))
    lines.append('')

    lines.append('## \u516d\u3001\u5f52\u5c5e\u5224\u5b9a')
    lines.append('')
    if r['need_pro']:
        lines.append('\u672c\u6b21\u60c5\u5f62**\u5e94\u8f6c\u4ea4\u6cb9\u70df\u673a\u7ef4\u4fee\u6216\u4e13\u4e1a\u4eba\u5458**\uff1a\u6d89\u53ca\u96c6\u6210\u7076\u3001\u7ed3\u57a2\u786c\u5316\u3001\u7535\u673a\u7535\u8def\u3001\u62c6\u673a\u9ad8\u5904\u4f5c\u4e1a\u6216\u4f4d\u79fb\u56fa\u5b9a\u3002')
    else:
        lines.append('\u672c\u6b21\u60c5\u5f62\u5c5e\u4e8e\u53ef\u81ea\u884c\u6e05\u6d17\u8303\u56f4\uff1a\u53ea\u505a\u53ef\u53d6\u4e0b\u90e8\u4ef6\u4e0e\u5916\u58f3\u7684\u6e05\u6d17\uff0c\u4e0d\u62c6\u98ce\u8f6e\u3001\u4e0d\u89e6\u78b0\u7535\u8def\u3002')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('\u672c\u7ed3\u679c\u4e3a\u73b0\u8c61\u5339\u914d\u4e0e\u6e05\u6d17\u65f6\u673a\u5efa\u8bae\uff0c\u4e0d\u4ee3\u8868\u73b0\u573a\u5224\u65ad\uff0c\u4e0d\u6784\u6210\u4e13\u4e1a\u7ef4\u4fee\u7ed3\u8bba\u3002')
    lines.append('\u6e05\u6d01\u5242\u9002\u7528\u8303\u56f4\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e66\u4e3a\u51c6\uff0c\u4e0d\u540c\u4ea7\u54c1\u4e0d\u53ef\u6df7\u7528\u3002')
    return '\n'.join(lines)


def read_input(path):
    raw = open(path, 'rb').read().decode('utf-8', 'replace')
    if raw.lstrip('\ufeff').strip().startswith('{'):
        try:
            data = json.loads(raw.lstrip('\ufeff'))
        except ValueError:
            return raw
        if isinstance(data, dict):
            for k in ('desc', 'text', 'description', '\u60c5\u51b5', '\u63cf\u8ff0'):
                if k in data and isinstance(data[k], str):
                    return data[k]
        return raw
    return raw


def selftest():
    errs = []

    def eq(name, got, want):
        if got != want:
            errs.append('%s got=%r want=%r' % (name, got, want))

    eq('case1 \u542b\u6c2f\u52a0\u9178\u6027', classify_pair('\u542b\u6c2f\u6d88\u6bd2\u6db2', '\u767d\u918b')[0], 'danger')
    eq('case2 \u542b\u6c2f\u52a0\u6d01\u5395\u7075', classify_pair('\u6f02\u767d\u6c34', '\u6d01\u5395\u7075')[0], 'danger')
    eq('case3 \u542b\u6c2f\u52a0\u78b1\u6027', classify_pair('\u542b\u6c2f\u6d88\u6bd2\u6db2', '\u5c0f\u82cf\u6253')[0], 'danger')
    eq('case4 \u4e24\u79cd\u542b\u6c2f', classify_pair('\u542b\u6c2f\u6d88\u6bd2\u6db2', '\u542b\u6c2f\u6f02\u767d\u6c34')[0], 'danger')
    eq('case5 \u4e2d\u6027\u914d\u5bf9', classify_pair('\u4e2d\u6027\u6e05\u6d01\u5242', '\u6e29\u6c34')[0], 'ok')

    r1 = analyse('\u5438\u529b\u53d8\u5c0f\u4e86\uff0c\u8fd8\u6709\u5f02\u54cd')
    eq('case6 \u5438\u529b\u547d\u4e2d', any(s['name'] == '\u5438\u529b\u4e0b\u964d' for s in r1['signals']), True)
    eq('case7 \u566a\u97f3\u547d\u4e2d', any(s['name'] == '\u566a\u97f3\u53d8\u5316' for s in r1['signals']), True)
    eq('case8 \u547d\u4e2d\u4e24\u9879', r1['n_signal'], 2)
    eq('case9 \u5e94\u6e05\u6d17', r1['should_clean'], True)

    r2 = analyse('\u6cb9\u7f51\u5f88\u810f\uff0c\u6cb9\u676f\u79ef\u6cb9\u7279\u522b\u5feb')
    eq('case10 \u6cb9\u57a2\u547d\u4e2d', any(s['name'] == '\u6cb9\u57a2\u539a\u5ea6' for s in r2['signals']), True)
    eq('case11 \u8f85\u52a9\u4fe1\u53f7', len(r2['aux']) >= 1, True)

    r3 = analyse('\u96c6\u6210\u7076\u6cb9\u57a2\u7ed3\u57a2\u5df2\u7ecf\u786c\u5316\u4e86')
    eq('case12 \u8f6c\u4e13\u4e1a', r3['need_pro'], True)

    r4 = analyse('\u53a8\u623f\u6709\u70b9\u5473\u9053')
    eq('case13 \u65e0\u4fe1\u53f7', r4['n_signal'], 0)
    eq('case14 \u6682\u4e0d\u6e05\u6d17', r4['should_clean'], False)

    r5 = analyse('\u9876\u5438\u5f0f\u7684\u6cb9\u7f51\u6cb9\u676f\u80fd\u81ea\u5df1\u6d17\u5417')
    eq('case15 \u8bc6\u522b\u9876\u5438', r5['types'], ['\u9876\u5438\u5f0f'])

    md = render_md(r1)
    eq('case16 \u8f93\u51fa\u8868\u5934', md.startswith('# '), True)
    eq('case17 \u542b\u5b89\u5168\u7ea2\u7ebf', '\u5fc5\u987b\u65ad\u7535' in md, True)
    eq('case18 \u542b\u5206\u90e8\u4f4d', '\u98ce\u8f6e' in md and '\u7535\u673a' in md, True)
    eq('case19 \u542b\u4e94\u79cd\u540e\u679c', '\u706b\u707e\u9690\u60a3' in md, True)
    js = json.loads(json.dumps(r1, ensure_ascii=False))
    eq('case20 JSON\u952e', sorted(js.keys()),
       ['aux', 'n_signal', 'need_pro', 'should_clean', 'signals', 'types'])

    # \u5e26 BOM \u7684 JSON \u8f93\u5165\u5fc5\u987b\u80fd\u6b63\u786e\u89e3\u6790
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write('{"desc": "\u6cb9\u7f51\u5f88\u810f"}')
    got = read_input(tmp)
    os.remove(tmp)
    eq('case21 \u5e26BOM\u7684JSON\u9996\u952e', analyse(got)['n_signal'], 1)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 23\n\u8986\u76d6: \u4e09\u4fe1\u53f7/\u6e05\u6d01\u5242\u56db\u79cd\u914d\u5bf9/\u8f85\u52a9\u4fe1\u53f7/'
               '\u96c6\u6210\u7076\u8f6c\u4e13\u4e1a/\u7c7b\u578b\u8bc6\u522b/\u5b89\u5168\u7ea2\u7ebf/BOM\u89e3\u6790')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u6cb9\u70df\u673a\u6e05\u6d17\u65f6\u673a\u5224\u5b9a\u4e0e\u5b89\u5168\u7ea2\u7ebf')
    ap.add_argument('--text', help='\u6cb9\u70df\u673a\u72b6\u51b5\u63cf\u8ff0')
    ap.add_argument('--file', help='\u4ece\u6587\u4ef6\u8bfb\uff0c\u652f\u6301 txt / md / json')
    ap.add_argument('--pair', nargs=2, metavar=('A', 'B'), help='\u68c0\u67e5\u4e24\u79cd\u6e05\u6d01\u5242\u7684\u914d\u5bf9')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'])
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    pair_info = None
    if a.pair:
        lv, m = classify_pair(a.pair[0], a.pair[1])
        pair_info = (a.pair[0], a.pair[1], lv, m)

    text = a.text or ''
    if a.file:
        if not os.path.exists(a.file):
            print('ERROR --file \u4e0d\u5b58\u5728')
            return 2
        text = read_input(a.file)
    if not text.strip() and pair_info is None:
        print('ERROR \u9700\u8981 --text \u6216 --file \u6216 --pair')
        return 2

    r = analyse(text)
    out = render_md(r, pair_info) if a.format == 'md' else \
        json.dumps({'pair': pair_info, 'result': r}, ensure_ascii=False, indent=2)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % a.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())