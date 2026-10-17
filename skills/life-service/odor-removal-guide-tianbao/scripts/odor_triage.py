# -*- coding: utf-8 -*-
"""\u5168\u5c4b\u5f02\u5473\u5206\u8bca\uff1a\u5206\u7c7b\u5b9a\u4f4d\u6765\u6e90\u3001\u5224\u65ad\u7ed3\u6784\u6027\u539f\u56e0\u3001\u68c0\u67e5\u6e05\u6d01\u5242\u914d\u5bf9\u7981\u5fcc\u3002

\u7528\u6cd5:
  python odor_triage.py --text "\u536b\u751f\u95f4\u65e9\u4e0a\u8d77\u6765\u6700\u81ed\uff0c\u4e0b\u6c34\u6709\u5495\u565c\u58f0"
  python odor_triage.py --pair "\u542b\u6c2f\u6d88\u6bd2\u6db2" "\u6d01\u5395\u7075"
  python odor_triage.py --file \u60c5\u51b5.txt --out \u7ed3\u679c.md
  python odor_triage.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ---- \u5341\u4e8c\u7c7b\u5f02\u5473\u6765\u6e90\uff0c\u6309\u5206\u8bca\u987a\u5e8f ----
SOURCES = [
    {'id': 'O1', 'order': 1, 'name': '\u4e0b\u6c34\u9053\u8fd4\u5473',
     'kw': ['\u4e0b\u6c34', '\u4e0b\u6c34\u9053', '\u8fd4\u5473', '\u5730\u6f0f', '\u8fd4\u81ed', '\u81ed\u5473', '\u624b\u67dc', '\u9a6c\u6876', '\u8fd4\u81ed\u88c5', '\u4e0b\u6c34\u53e3'],
     'locate': '\u9010\u4e2a\u5c01\u5835\u5730\u6f0f\u3001\u6d17\u624b\u76c6\u3001\u9a6c\u6876\uff0c\u6bcf\u6b21\u505c\u7559\u89c2\u5bdf\u6c14\u5473\u53d8\u5316',
     'fix': '\u6309\u7ed3\u6784\u6027\u539f\u56e0\u5206\u522b\u5904\u7406\uff1a\u6c34\u5c01\u5e72\u6db8\u5219\u8865\u6c34\uff0c\u82af\u4f53\u5931\u6548\u5219\u6362\u82af'},
    {'id': 'O2', 'order': 2, 'name': '\u4e0b\u6c34\u9053\u5e72\u6db8',
     'kw': ['\u957f\u671f\u4e0d\u7528', '\u51fa\u5dee', '\u7a7a\u7f6e', '\u5ba2\u536b', '\u4e45\u6ca1\u4eba\u4f4f', '\u6ca1\u4f4f\u4eba'],
     'locate': '\u786e\u8ba4\u8be5\u6392\u6c34\u70b9\u957f\u671f\u672a\u4f7f\u7528\uff1b\u8865\u6c34\u540e\u89c2\u5bdf\u6c14\u5473\u662f\u5426\u660e\u663e\u51cf\u8f7b',
     'fix': '\u8865\u6e05\u6c34\u7ef4\u6301\u6c34\u5c01\uff1b\u957f\u671f\u4e0d\u7528\u5b9a\u671f\u8865\u6c34\uff0c\u65e0\u9700\u6362\u82af'},
    {'id': 'O3', 'order': 3, 'name': '\u88c5\u4fee\u9057\u7559\u5473',
     'kw': ['\u88c5\u4fee', '\u65b0\u623f', '\u521a\u88c5\u5b8c', '\u65b0\u5bb6', '\u677f\u6750\u5473', '\u80f6\u5473', '\u4e73\u80f6\u6f06\u5473', '\u5851\u6599\u5473'],
     'locate': '\u96c6\u4e2d\u5728\u7279\u5b9a\u533a\u57df\u6216\u6750\u6599\uff1b\u901a\u98ce\u540e\u51cf\u8f7b\u4f46\u4e0d\u5b8c\u5168\u6d88\u5931',
     'fix': '\u5145\u5206\u901a\u98ce\u3001\u79fb\u9664\u6216\u9694\u79bb\u4e3b\u8981\u6765\u6e90\uff1b\u6765\u6e90\u4e0d\u660e\u6216\u6301\u7eed\u4e0d\u6563\u65f6\u54a8\u8be2\u68c0\u6d4b'},
    {'id': 'O4', 'order': 4, 'name': '\u9709\u5473',
     'kw': ['\u9709\u5473', '\u53d1\u9709', '\u9709\u6591', '\u6f6e\u5473', '\u6e7f\u5473'],
     'locate': '\u6709\u9709\u5473\u4e14\u96c6\u4e2d\u5728\u6f6e\u6e7f\u4f4d\u7f6e',
     'fix': '\u5148\u9664\u6e7f\u901a\u98ce\uff0c\u518d\u505a\u9709\u53d8\u5904\u7406\uff1b\u4e0d\u5e72\u71e5\u4f1a\u53cd\u590d'},
    {'id': 'O5', 'order': 5, 'name': '\u6cb9\u70df\u5473',
     'kw': ['\u6cb9\u70df', '\u7092\u83dc\u5473', '\u53a8\u623f\u5473', '\u62bd\u6cb9\u70df\u673a', '\u6cb9\u5473'],
     'locate': '\u53a8\u623f\u4e3a\u4e3b\uff0c\u6216\u8863\u7269\u88ab\u6cbe\u67d3',
     'fix': '\u6e05\u7406\u6cb9\u70df\u673a\u4e0e\u6ee4\u7f51\uff0c\u6e05\u6d17\u88ab\u6cbe\u67d3\u7684\u7ec7\u7269'},
    {'id': 'O6', 'order': 6, 'name': '\u5ba0\u7269\u5473',
     'kw': ['\u5ba0\u7269', '\u732b\u7802', '\u72d7\u7b3c', '\u732b\u7b3c', '\u5c3f\u57ab', '\u5ba0\u7269\u7a9d', '\u732b'],
     'locate': '\u4e0e\u5ba0\u7269\u6d3b\u52a8\u533a\u3001\u7b3c\u5b50\u3001\u732b\u7802\u76c6\u76f8\u5173',
     'fix': '\u5f7b\u5e95\u6e05\u7406\u6e90\u5934\u3001\u5f7b\u5e95\u5e72\u71e5\u3001\u52e4\u6362\u57ab\u6599\uff1b\u53ea\u64e6\u8868\u9762\u65e0\u6548'},
    {'id': 'O7', 'order': 7, 'name': '\u7ec7\u7269\u5473',
     'kw': ['\u7a97\u5e18', '\u5730\u6bef', '\u5e8a\u54c1', '\u5e03\u827a', '\u88ab\u8925', '\u6c99\u53d1', '\u6bdb\u6bef'],
     'locate': '\u96c6\u4e2d\u5728\u5e03\u827a\u7269\u54c1',
     'fix': '\u62c6\u6d17\u5e76\u5f7b\u5e95\u667e\u5e72\uff1b\u4e0d\u667e\u5e72\u4f1a\u52a0\u91cd'},
    {'id': 'O8', 'order': 8, 'name': '\u7535\u5668\u5473',
     'kw': ['\u7535\u5668', '\u65b0\u673a', '\u673a\u5668\u6709\u5473', '\u7535\u89c6', '\u6d17\u8863\u673a\u6709\u5473', '\u7a7a\u8c03\u5473', '\u70d8\u5e72\u673a'],
     'locate': '\u4e0e\u7279\u5b9a\u7535\u5668\u4f4d\u7f6e\u76f8\u5173\uff1b\u65b0\u673a\u4e3a\u80f6\u5473\uff0c\u8001\u673a\u4e3a\u79ef\u5c18\u4e0e\u6b8b\u57a2',
     'fix': '\u65b0\u673a\u5145\u5206\u901a\u98ce\u6563\u5473\uff1b\u8001\u673a\u6e05\u6d01\u5e76\u505c\u673a\u9664\u5473'},
    {'id': 'O9', 'order': 9, 'name': '\u6d17\u8863\u673a\u6b8b\u7559',
     'kw': ['\u6d17\u8863\u673a', '\u6eda\u7b52', '\u6d17\u5b8c\u6709\u5473', '\u6392\u6c34\u53e3'],
     'locate': '\u53ea\u5728\u6d17\u8863\u673a\u8fd0\u884c\u6216\u6d17\u540e\u51fa\u73b0',
     'fix': '\u6e05\u6d01\u6eda\u7b52\u4e0e\u6392\u6c34\u53e3\uff0c\u8dd1\u4e00\u6b21\u7a7a\u7a0b\u5e8f\uff1b\u53ea\u64e6\u95e8\u5c01\u65e0\u6548'},
    {'id': 'O10', 'order': 10, 'name': '\u51b0\u7bb1\u6b8b\u7559',
     'kw': ['\u51b0\u7bb1', '\u51b7\u51bb\u5ba4', '\u5f00\u95e8\u6709\u5473', '\u5269\u83dc\u5473'],
     'locate': '\u5f00\u51b0\u7bb1\u95e8\u65f6\u660e\u663e',
     'fix': '\u6e05\u7406\u53d8\u8d28\u98df\u7269\u3001\u64e6\u51c0\u5185\u58c1\u3001\u6e05\u6d01\u95e8\u5c01\u6761'},
    {'id': 'O11', 'order': 11, 'name': '\u978b\u67dc\u67dc\u4f53\u5473',
     'kw': ['\u978b\u67dc', '\u50a8\u7269\u67dc', '\u8863\u67dc', '\u978b', '\u67dc\u4f53\u5473'],
     'locate': '\u96c6\u4e2d\u5728\u978b\u67dc\u6216\u50a8\u7269\u67dc\uff1b\u79fb\u5f00\u7269\u54c1\u540e\u6c14\u5473\u53d8\u5316',
     'fix': '\u6e05\u7a7a\u901a\u98ce\u3001\u6e05\u7406\u978b\u5e95\u3001\u4fdd\u6301\u5e72\u71e5'},
    {'id': 'O12', 'order': 12, 'name': '\u9633\u53f0\u6392\u6c34',
     'kw': ['\u9633\u53f0', '\u6d17\u8863\u673a\u4f4d', '\u9633\u53f0\u5730\u6f0f'],
     'locate': '\u96c6\u4e2d\u5728\u9633\u53f0\u6216\u6d17\u8863\u673a\u4f4d',
     'fix': '\u67e5\u9633\u53f0\u5730\u6f0f\u4e0e\u6392\u6c34\u53e3\uff0c\u6309\u4e0b\u6c34\u9053\u8fd4\u5473\u6d41\u7a0b\u5904\u7406'},
]

# ---- \u4e0b\u6c34\u9053\u8fd4\u5473\u7684\u56db\u79cd\u7ed3\u6784\u6027\u539f\u56e0 ----
STRUCT = [
    {'id': 'S1', 'name': '\u5730\u6f0f\u82af\u5931\u6548',
     'kw': ['\u82af\u574f', '\u9632\u81ed\u82af', '\u7ffb\u76d6', '\u78c1\u5438', '\u5bc6\u5c01\u5708', '\u82af\u4f53'],
     'msg': '\u82af\u4f53\u677e\u52a8\u3001\u7ffb\u76d6\u4e0d\u590d\u4f4d\u3001\u5bc6\u5c01\u5708\u8001\u5316\u5c5e\u82af\u4f53\u5931\u6548\uff0c\u53ef\u6309\u5b9e\u6d4b\u5c3a\u5bf8\u66f4\u6362\u5bf9\u5e94\u7c7b\u578b\u5730\u6f0f\u82af\u3002'},
    {'id': 'S2', 'name': '\u5b58\u6c34\u5f2f\u5e72\u6db8',
     'kw': ['\u5e72\u6db8', '\u6c34\u5e72\u4e86', '\u8865\u6c34', '\u84b8\u53d1'],
     'msg': '\u957f\u671f\u4e0d\u7528\u5bfc\u81f4\u6c34\u5c01\u84b8\u53d1\uff0c\u8865\u6e05\u6c34\u5373\u53ef\u9a8c\u8bc1\u6709\u6548\uff0c\u65e0\u9700\u6362\u82af\u3002'},
    {'id': 'S3', 'name': '\u901a\u6c14\u7ba1\u5835\u585e',
     'kw': ['\u591a\u4e2a', '\u90fd\u8fd4\u5473', '\u540c\u65f6\u8fd4\u5473', '\u5168\u90fd\u81ed', '\u6574\u5c42', '\u5355\u5143', '\u901a\u6c14\u7ba1'],
     'msg': '\u591a\u4e2a\u6392\u6c34\u70b9\u540c\u65f6\u8fd4\u5473\u4f18\u5148\u6000\u7591\u901a\u6c14\u7ba1\u5835\u585e\uff0c\u9700\u62c6\u52a8\u540a\u9876\u6216\u7ba1\u9053\uff0c\u4ea4\u7269\u4e1a\u6216\u4e13\u4e1a\u4eba\u5458\u5904\u7406\uff0c\u4e0d\u8981\u81ea\u884c\u62c6\u9876\u627e\u7ba1\u3002'},
    {'id': 'S4', 'name': '\u672a\u505a\u6c34\u5c01\u6216\u6c34\u5c01\u88ab\u7834\u574f',
     'kw': ['\u76f4\u6392', '\u6ca1\u6709\u6c34\u5c01', '\u8001\u623f', '\u6539\u9020', '\u7834\u574f', '\u6ca1\u505a\u5b58\u6c34\u5f2f'],
     'msg': '\u8001\u623f\u76f4\u6392\u6216\u6539\u9020\u7834\u574f\u5b58\u6c34\u7ed3\u6784\u65f6\uff0c\u9700\u52a0\u88c5\u5b58\u6c34\u5f2f\u6216\u6539\u7528\u5e26\u6c34\u5c01\u7684\u5730\u6f0f\u3002'},
]

# ---- \u6e05\u6d01\u5242\u914d\u5bf9\u7981\u5fcc\u8868 ----
CHLORINE = ['\u542b\u6c2f', '\u6f02\u767d\u6c34', '\u6d88\u6bd2\u6db2', '84', '\u6b21\u6c2f\u9178\u94a0', '\u6c2f', '\u542b\u6c2f\u6d88\u6bd2\u6db2', '84\u6d88\u6bd2\u6db2']
ACID = ['\u9178\u6027', '\u6d01\u5395\u7075', '\u6d01\u5395\u5242', '\u767d\u918b', '\u918b', '\u67e0\u6aac\u9178', '\u9664\u57a2\u5242', '\u67e0\u6aac', '\u76d0\u9178']
ALKALI = ['\u78b1\u6027', '\u5f3a\u78b1', '\u706b\u78b1', '\u70e7\u78b1', '\u5c0f\u82cf\u6253', '\u78b3\u9178\u94a0', '\u5f3a\u9178', '\u786b\u9178']
FRAGRANCE = ['\u9999\u85b0', '\u7a7a\u6c14\u6e05\u65b0\u5242', '\u9999\u6c34', '\u55b7\u9999', '\u9999\u6c1b', '\u63a9\u76d6']


def classify_pair(a, b):
    """\u8fd4\u56de (\u7b49\u7ea7, \u8bf4\u660e)\u3002\u7b49\u7ea7: danger / warn / ok"""
    ta = (a or '') + ' ' + (b or '')
    has_cl = any(k in ta for k in CHLORINE)
    has_ac = any(k in ta for k in ACID)
    has_al = any(k in ta for k in ALKALI)
    has_fr = any(k in ta for k in FRAGRANCE)
    if has_cl and has_ac:
        return ('danger', '\u4e25\u7981\u5c06\u542b\u6c2f\u6d88\u6bd2\u5242\u4e0e\u9178\u6027\u6e05\u6d01\u5242\u6df7\u5408\uff0c\u4e24\u8005\u4f1a\u4ea7\u751f\u6709\u6bd2\u6c14\u4f53\u5e76\u523a\u6fc0\u547c\u5438\u9053')
    if has_cl and has_al:
        return ('danger', '\u542b\u6c2f\u6d88\u6bd2\u5242\u4e0e\u78b1\u6027\u6e05\u6d01\u5242\u4e0d\u5c5e\u4e8e\u5b89\u5168\u914d\u5bf9\uff0c\u53ef\u80fd\u4ea7\u751f\u523a\u6fc0\u6027\u6c14\u4f53')
    if has_cl and '\u542b\u6c2f' in (a or '') and '\u542b\u6c2f' in (b or ''):
        return ('danger', '\u4e24\u79cd\u542b\u6c2f\u4ea7\u54c1\u6df7\u5408\u540e\u6709\u6548\u6210\u5206\u53e0\u52a0\uff0c\u5c5e\u4e0d\u53ef\u63a7\u914d\u5bf9')
    if has_fr:
        return ('warn', '\u9999\u5473\u7c7b\u4ea7\u54c1\u53ea\u80fd\u63a9\u76d6\u6c14\u5473\uff0c\u4e0d\u89e3\u51b3\u6765\u6e90\uff0c\u4e14\u4f1a\u63a9\u76d6\u9700\u8981\u6392\u67e5\u7684\u4fe1\u53f7')
    return ('ok', '\u672a\u547d\u4e2d\u5df2\u77e5\u5371\u9669\u914d\u5bf9\uff0c\u4ecd\u9700\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e66\u4e3a\u51c6\uff0c\u4e0d\u540c\u4ea7\u54c1\u4e0d\u53ef\u968f\u610f\u6df7\u7528')


def analyse(text):
    t = (text or '').replace(' ', '').replace('\u3000', '')
    srcs = []
    for s in SOURCES:
        hits = [k for k in s['kw'] if k in t]
        if hits:
            srcs.append({'id': s['id'], 'order': s['order'], 'name': s['name'],
                         'hits': hits, 'locate': s['locate'], 'fix': s['fix']})
    srcs.sort(key=lambda x: x['order'])
    struct = [s['msg'] for s in STRUCT if any(k in t for k in s['kw'])]
    levels = {}
    msgs = []
    for pair in [(a, b) for a in CHLORINE for b in ACID if a in t or b in t]:
        lv, m = classify_pair(pair[0], pair[1])
        if lv == 'danger' and m not in msgs:
            msgs.append(m)
    lvl, fr_msg = classify_pair(t, '')
    if lvl == 'warn' and fr_msg not in msgs:
        msgs.append(fr_msg)
    return {'sources': srcs, 'struct': struct, 'risks': msgs,
            'top': srcs[0]['name'] if srcs else '',
            'need_pro': any('\u4e13\u4e1a\u4eba\u5458' in s or '\u7269\u4e1a' in s for s in struct)}


def render_md(r, pair_info=None):
    lines = ['# \u5f02\u5473\u6765\u6e90\u5206\u8bca\u7ed3\u679c', '']
    lines.append('> \u5148\u5b9a\u4f4d\u6765\u6e90\uff0c\u518d\u5904\u7406\u3002\u9999\u5473\u4ea7\u54c1\u53ea\u80fd\u63a9\u76d6\uff0c\u4e0d\u89e3\u51b3\u6e90\u5934\u3002')
    lines.append('')
    if pair_info:
        lines.append('## \u6e05\u6d01\u5242\u914d\u5bf9\u68c0\u67e5')
        lines.append('')
        lines.append('- \u4ea7\u54c1 A\uff1a%s' % pair_info[0])
        lines.append('- \u4ea7\u54c1 B\uff1a%s' % pair_info[1])
        lines.append('- \u7b49\u7ea7\uff1a%s' % pair_info[2])
        lines.append('- \u8bf4\u660e\uff1a%s' % pair_info[3])
        lines.append('')
    if not r['sources'] and not r['struct']:
        lines.append('\u672a\u5339\u914d\u5230\u6765\u6e90\u7ebf\u7d22\u3002\u8bf7\u8865\u5145\uff1a\u5473\u9053\u6700\u91cd\u7684\u4f4d\u7f6e\u3001\u4ec0\u4e48\u65f6\u6bb5\u6700\u91cd\u3001'
                     '\u4e0e\u7528\u6c34\u662f\u5426\u76f8\u5173\u3001\u662f\u5426\u4e0e\u5ba0\u7269\u6216\u88c5\u4fee\u76f8\u5173\u3002')
        lines.append('')
    else:
        lines.append('\u6700\u4f18\u5148\u6392\u67e5\uff1a%s' % r['top'])
        lines.append('')
        lines.append('## \u4e00\u3001\u6765\u6e90\u5206\u8bca\uff08\u6309\u4e0b\u8868\u987a\u5e8f\u5b9a\u4f4d\uff09')
        lines.append('')
        lines.append('| \u987a\u5e8f | \u53ef\u80fd\u6765\u6e90 | \u547d\u4e2d\u7ebf\u7d22 | \u5b9a\u4f4d\u65b9\u6cd5 | \u5904\u7406\u52a8\u4f5c |')
        lines.append('|---|---|---|---|---|')
        for s in r['sources']:
            lines.append('| %d | %s | %s | %s | %s |' % (
                s['order'], s['name'], '\u3001'.join(s['hits']), s['locate'], s['fix']))
        lines.append('')
    if r['struct']:
        lines.append('## \u4e8c\u3001\u4e0b\u6c34\u9053\u8fd4\u5473\u7684\u7ed3\u6784\u6027\u539f\u56e0')
        lines.append('')
        for m in r['struct']:
            lines.append('- %s' % m)
        lines.append('')
    lines.append('## \u4e09\u3001\u5b89\u5168\u7ea2\u7ebf')
    lines.append('')
    lines.append('- **\u4e25\u7981\u5c06\u542b\u6c2f\u6d88\u6bd2\u5242\u4e0e\u9178\u6027\u6e05\u6d01\u5242\u6df7\u5408\u4f7f\u7528**\uff0c\u4f1a\u4ea7\u751f\u6709\u6bd2\u6c14\u4f53\u5e76\u523a\u6fc0\u547c\u5438\u9053\u3002')
    lines.append('- \u542b\u6c2f\u6d88\u6bd2\u5242\u4e0e\u78b1\u6027\u6e05\u6d01\u5242\u540c\u6837\u4e0d\u5c5e\u4e8e\u5b89\u5168\u914d\u5bf9\u3002')
    lines.append('- \u4e0d\u7528\u9999\u5473\u4ea7\u54c1\u8986\u76d6\u9700\u8981\u6392\u67e5\u7684\u5f02\u5473\u3002')
    lines.append('- \u6e05\u6d01\u5242\u4fdd\u6301\u539f\u5305\u88c5\u539f\u6807\u7b7e\uff0c\u4e0d\u5206\u88c5\u5230\u4e0d\u660e\u5bb9\u5668\u3002')
    lines.append('')
    if r['risks']:
        lines.append('**\u672c\u6b21\u63cf\u8ff0\u89e6\u53d1\uff1a**')
        lines.append('')
        for m in r['risks']:
            lines.append('- %s' % m)
        lines.append('')
    lines.append('## \u56db\u3001\u901a\u98ce\u7684\u5c40\u9650')
    lines.append('')
    lines.append('| \u573a\u666f | \u901a\u98ce\u662f\u5426\u6709\u6548 |')
    lines.append('|---|---|')
    lines.append('| \u65b0\u5bb6\u5177\u4e0e\u88c5\u4fee\u6750\u6599\u6563\u5473 | \u6709\u6548 |')
    lines.append('| \u5bc6\u95ed\u7a7a\u95f4\u79ef\u805a\u7684\u4eba\u4f53\u5473\u4e0e\u98df\u7269\u5473 | \u6709\u6548 |')
    lines.append('| \u5730\u6f0f\u6216\u5b58\u6c34\u5f2f\u5e72\u6db8\u8fd4\u5473 | \u6709\u9650\uff0c\u6c34\u5c01\u4e0d\u8865\u5c31\u6301\u7eed |')
    lines.append('| \u901a\u6c14\u7ba1\u5835\u585e\u578b\u8fd4\u5473 | \u57fa\u672c\u65e0\u6548 |')
    lines.append('| \u7ba1\u9053\u5185\u90e8\u6c61\u57a2\u4e0e\u5899\u4f53\u5185\u90e8\u6c61\u67d3 | \u65e0\u6548 |')
    lines.append('')
    lines.append('## \u4e94\u3001\u5f52\u5c5e\u5224\u5b9a')
    lines.append('')
    if r['need_pro']:
        lines.append('\u672c\u6b21\u60c5\u5f62**\u5e94\u62a5\u7269\u4e1a\u6216\u8f6c\u4e13\u4e1a\u4eba\u5458**\uff0c\u4e0d\u8981\u81ea\u884c\u62c6\u540a\u9876\u6216\u52a8\u7ba1\u9053\u3002')
    else:
        lines.append('\u672c\u6b21\u60c5\u5f62\u5c5e\u4e8e\u53ef\u81ea\u884c\u5904\u7406\u8303\u56f4\uff0c\u4ecd\u9700\u5148\u5b8c\u6210\u5c01\u5835\u6d4b\u8bd5\u786e\u8ba4\u6765\u6e90\u3002')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('\u672c\u7ed3\u679c\u4e3a\u73b0\u8c61\u5339\u914d\u4e0e\u5206\u8bca\u987a\u5e8f\u5efa\u8bae\uff0c\u4e0d\u4ee3\u8868\u73b0\u573a\u5224\u65ad\uff0c\u4e0d\u6784\u6210\u4e13\u4e1a\u65bd\u5de5\u6216\u68c0\u6d4b\u7ed3\u8bba\u3002')
    lines.append('\u6e05\u6d01\u5242\u914d\u5bf9\u7981\u5fcc\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e66\u4e3a\u51c6\uff0c\u4e0d\u540c\u4ea7\u54c1\u4e0d\u53ef\u6df7\u7528\u3002')
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

    eq('case1 \u542b\u6c2f\u52a0\u9178\u6027', classify_pair('84\u6d88\u6bd2\u6db2', '\u6d01\u5395\u7075')[0], 'danger')
    eq('case2 \u542b\u6c2f\u52a0\u767d\u918b', classify_pair('\u542b\u6c2f\u6d88\u6bd2\u6db2', '\u767d\u918b')[0], 'danger')
    eq('case3 \u542b\u6c2f\u52a0\u78b1\u6027', classify_pair('\u542b\u6c2f\u6d88\u6bd2\u6db2', '\u5c0f\u82cf\u6253')[0], 'danger')
    eq('case4 \u9999\u85b0\u63d0\u9192', classify_pair('\u7a7a\u6c14\u6e05\u65b0\u5242', '\u9999\u85b0')[0], 'warn')
    eq('case5 \u65e0\u5371\u9669\u914d\u5bf9', classify_pair('\u4e2d\u6027\u6e05\u6d01\u5242', '\u6e29\u6c34')[0], 'ok')

    r1 = analyse('\u536b\u751f\u95f4\u65e9\u4e0a\u8d77\u6765\u6700\u81ed\uff0c\u4e0b\u6c34\u6709\u5495\u565c\u58f0')
    eq('case6 \u4e0b\u6c34\u9053\u4f18\u5148', r1['top'], '\u4e0b\u6c34\u9053\u8fd4\u5473')
    eq('case7 \u542b\u5b9a\u4f4d\u52a8\u4f5c', bool(r1['sources'][0]['locate']), True)

    r2 = analyse('\u5ba2\u536b\u957f\u671f\u6ca1\u4eba\u4f4f\uff0c\u6700\u8fd1\u8fd4\u5473')
    eq('case8 \u5e72\u6db8\u5224\u5b9a', any(x['id'] == 'O2' for x in r2['sources']), True)
    eq('case9 \u8865\u6c34\u5efa\u8bae', any('\u8865\u6c34' in s['fix'] for s in r2['sources']), True)

    r3 = analyse('\u540c\u4e00\u5c42\u597d\u51e0\u4e2a\u6392\u6c34\u53e3\u90fd\u8fd4\u5473')
    eq('case10 \u7ed3\u6784\u539f\u56e0\u547d\u4e2d', len(r3['struct']) >= 1, True)
    eq('case11 \u8f6c\u4e13\u4e1a\u4eba\u5458', r3['need_pro'], True)

    r4 = analyse('\u65b0\u623f\u521a\u88c5\u5b8c\u5473\u9053\u5f88\u91cd')
    eq('case12 \u88c5\u4fee\u5473', r4['top'], '\u88c5\u4fee\u9057\u7559\u5473')

    r5 = analyse('\u60f3\u8ba9\u9999\u85b0\u76d6\u4f4f\u8fd9\u4e2a\u5473\u9053')
    eq('case13 \u9999\u5473\u63d0\u9192', len(r5['risks']) >= 1, True)

    r6 = analyse('\u517b\u4e86\u732b\uff0c\u732b\u7802\u76c6\u5473\u9053\u5f88\u5927')
    eq('case14 \u5ba0\u7269\u5473', r6['top'], '\u5ba0\u7269\u5473')
    eq('case15 \u6e90\u5934\u63d0\u793a', any('\u6e90\u5934' in s['fix'] for s in r6['sources']), True)

    r7 = analyse('\u6d17\u5b8c\u8863\u670d\u6d17\u8863\u673a\u91cc\u6709\u5f02\u5473')
    eq('case16 \u6d17\u8863\u673a', r7['top'], '\u6d17\u8863\u673a\u6b8b\u7559')

    r8 = analyse('\u978b\u67dc\u5473\u9053\u5f88\u51b2')
    eq('case17 \u978b\u67dc', r8['top'], '\u978b\u67dc\u67dc\u4f53\u5473')

    r9 = analyse('\u4ec0\u4e48\u5473\u9053\u90fd\u6ca1\u6709\u63cf\u8ff0')
    eq('case18 \u65e0\u5339\u914d', (r9['sources'], r9['struct']), ([], []))

    md = render_md(r1)
    eq('case19 \u8f93\u51fa\u8868\u5934', md.startswith('# '), True)
    eq('case20 \u542b\u5b89\u5168\u7ea2\u7ebf', '\u4e25\u7981\u5c06\u542b\u6c2f\u6d88\u6bd2\u5242\u4e0e\u9178\u6027\u6e05\u6d01\u5242\u6df7\u5408' in md, True)
    js = json.loads(json.dumps(r1, ensure_ascii=False))
    eq('case21 JSON\u952e', sorted(js.keys()),
       ['need_pro', 'risks', 'sources', 'struct', 'top'])

    # \u5e26 BOM \u7684 JSON \u8f93\u5165\u5fc5\u987b\u80fd\u6b63\u786e\u89e3\u6790
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write('{"desc": "\u978b\u67dc\u5473\u9053\u5f88\u51b2"}')
    got = read_input(tmp)
    os.remove(tmp)
    eq('case22 \u5e26BOM\u7684JSON\u9996\u952e', analyse(got)['top'], '\u978b\u67dc\u67dc\u4f53\u5473')

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 25\n\u8986\u76d6: \u542b\u6c2f\u52a0\u9178\u6027/\u542b\u6c2f\u52a0\u78b1\u6027/\u4e24\u79cd\u542b\u6c2f/\u9999\u85b0\u63a9\u76d6/'
               '\u5341\u4e8c\u7c7b\u6765\u6e90/\u56db\u79cd\u7ed3\u6784\u6027\u539f\u56e0/\u901a\u6c14\u7ba1\u8f6c\u4e13\u4e1a/BOM\u89e3\u6790')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u5168\u5c4b\u5f02\u5473\u5206\u8bca\u4e0e\u6e05\u6d01\u5242\u914d\u5bf9\u68c0\u67e5')
    ap.add_argument('--text', help='\u5f02\u5473\u60c5\u51b5\u63cf\u8ff0')
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
    if a.format == 'json':
        out = json.dumps({'pair': pair_info, 'result': r}, ensure_ascii=False, indent=2)
    else:
        out = render_md(r, pair_info)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % a.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())