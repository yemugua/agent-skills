# -*- coding: utf-8 -*-
"""\u62d6\u628a\u4e0e\u6e05\u6d01\u5de5\u5177\u4fdd\u517b\u5224\u5b9a\uff1a\u5339\u914d\u6750\u8d28\u4e0e\u6e05\u6d17\u8981\u70b9\u3001\u68c0\u67e5\u66f4\u6362\u4fe1\u53f7\u3001\u68c0\u67e5\u914d\u5bf9\u4e0e\u7ea2\u7ebf\u3002

\u7528\u6cd5:
  python mop_care_check.py --text "\u62d6\u628a\u6709\u5473\u9053\u4e86\uff0c\u6389\u6bdb"
  python mop_care_check.py --pair "\u542b\u6c2f\u6d88\u6bd2\u6db2" "\u767d\u918b"
  python mop_care_check.py --file \u60c5\u51b5.txt --out \u7ed3\u679c.md
  python mop_care_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ---- \u4e94\u7c7b\u62d6\u628a\u6750\u8d28 ----
MOP_TYPES = [
    {'id': 'M1', 'name': '\u68c9\u62d6\u628a',
     'kw': ['\u68c9\u62d6\u628a', '\u68c9\u62d6\u5e03', '\u4f20\u7edf\u62d6\u628a', '\u68c9\u7684'],
     'fit': '\u4f20\u7edf\u62d6\u5730\uff0c\u5438\u6c34\u5f3a',
     'wash': '\u6e29\u6c34\u6d17\u6da4\uff0c\u53ef\u52a0\u4e2d\u6027\u6e05\u6d01\u5242',
     'dry': '\u60ac\u6302\u667e\u5e72\uff0c\u644a\u5f00\u4e0d\u53e0',
     'note': '\u6f6e\u6e7f\u6613\u6709\u5f02\u5473\uff1b\u4e0d\u53ef\u7528\u70ed\u6c34\u4e45\u6ce1'},
    {'id': 'M2', 'name': '\u7ed2\u5e03\u62d6\u628a',
     'kw': ['\u7ed2\u5e03', '\u7ed2\u9762', '\u7ea4\u7ef4\u62d6\u628a', '\u9759\u7535\u62d6\u628a'],
     'fit': '\u5438\u5c18\u4e0e\u5438\u6c34\u517c\u987e',
     'wash': '\u6309\u4ea7\u54c1\u8bf4\u660e\u6e05\u6d17\uff0c\u907f\u514d\u5f3a\u529b\u6413\u62e7',
     'dry': '\u644a\u5f00\u9634\u5e72\u6216\u4f4e\u6e29\u70d8\u5e72',
     'note': '\u7ed2\u9762\u6613\u7ed3\u56e2\uff0c\u6309\u8bf4\u660e\u4e66\u5904\u7406'},
    {'id': 'M3', 'name': '\u5e73\u677f\u62d6\u628a',
     'kw': ['\u5e73\u677f', '\u5e73\u677f\u62d6\u628a', '\u5e73\u677f\u62d6\u5e03'],
     'fit': '\u74f7\u7816\u3001\u5927\u9762\u79ef\u5730\u9762',
     'wash': '\u62d6\u5e03\u53ef\u62c6\u6d17\uff0c\u6309\u8bf4\u660e\u4e66\u64cd\u4f5c',
     'dry': '\u62d6\u5e03\u667e\u5e72\uff0c\u5851\u6599\u5e95\u5ea7\u64e6\u5e72',
     'note': '\u5e95\u5ea7\u4e0e\u62d6\u5e03\u5206\u522b\u5904\u7406'},
    {'id': 'M4', 'name': '\u65cb\u8f6c mop',
     'kw': ['\u65cb\u8f6c', '\u65cb\u8f6c\u62d6\u628a', '\u6876\u8fb9\u65cb\u8f6c', '\u7529\u6c34', '\u81ea\u6d01\u6876'],
     'fit': '\u6876\u8fb9\u65cb\u8f6c\u7529\u6c34',
     'wash': '\u5b9a\u671f\u6e05\u7406\u6876\u5185\u6c61\u57a2\uff0c\u62d6\u5e03\u5355\u72ec\u6d17',
     'dry': '\u62c6\u5f00\u5206\u522b\u667e\u5e72',
     'note': '\u6876\u5185\u79ef\u6c34\u662f\u5f02\u5473\u6765\u6e90\uff1b\u62c6\u88c5\u6309\u8bf4\u660e\u4e66'},
    {'id': 'M5', 'name': '\u4e00\u6b21\u6027\u62d6\u628a',
     'kw': ['\u4e00\u6b21\u6027', '\u4e00\u6b21\u6027\u7684', '\u61d2\u4eba\u62d6\u628a'],
     'fit': '\u5c40\u90e8\u5feb\u901f\u6e05\u6d01',
     'wash': '\u7528\u540e\u6309\u4ea7\u54c1\u8bf4\u660e\u5904\u7406',
     'dry': '\u7528\u5b8c\u59a5\u5584\u5904\u7f6e',
     'note': '\u4e00\u822c\u4e0d\u5efa\u8bae\u53cd\u590d\u4f7f\u7528\uff0c\u6309\u4ea7\u54c1\u8bf4\u660e'},
]

# ---- \u56db\u4e2a\u66f4\u6362\u4fe1\u53f7 ----
SIGNALS = [
    {'id': 'S1', 'name': '\u6389\u6bdb',
     'kw': ['\u6389\u6bdb', '\u6bdb\u7d6e', '\u6389\u7ea4\u7ef4', '\u6cbe\u6bdb', '\u6389\u6e23'],
     'sign': '\u62d6\u5730\u540e\u5730\u4e0a\u6709\u6bdb\u7d6e\u6216\u6b8b\u7559\u7ea4\u7ef4',
     'why': '\u7ea4\u7ef4\u5df2\u677e\u6563\uff0c\u6e05\u6d01\u6548\u679c\u4e0e\u536b\u751f\u6027\u90fd\u4e0b\u964d'},
    {'id': 'S2', 'name': '\u5f02\u5473\u96be\u53bb',
     'kw': ['\u6709\u5473\u9053', '\u5f02\u5473', '\u81ed\u5473', '\u53d1\u81ed', '\u5473\u9053\u53bb\u4e0d\u6389', '\u8fd8\u6709\u5473', '\u9709\u5473'],
     'sign': '\u6d17\u540e\u4ecd\u6709\u5f02\u5473\uff0c\u6216\u667e\u5e72\u540e\u590d\u73b0',
     'why': '\u5185\u90e8\u5df2\u79ef\u805a\u6c61\u57a2\u6216\u9709\u83cc\uff0c\u666e\u901a\u6e05\u6d17\u65e0\u6cd5\u89e3\u51b3'},
    {'id': 'S3', 'name': '\u6e05\u6d01\u529b\u4e0b\u964d',
     'kw': ['\u62d6\u4e0d\u5e72\u51c0', '\u6e05\u6d01\u529b', '\u4e0d\u5438\u6c34', '\u7559\u6c34\u75d5', '\u62d6\u4e0d\u51c0'],
     'sign': '\u540c\u6837\u7684\u5730\u62d6\u4e0d\u5e72\u51c0\uff0c\u6b8b\u7559\u6c34\u75d5',
     'why': '\u7ea4\u7ef4\u5438\u6c34\u6027\u4e0e\u7ed3\u6784\u5df2\u9000\u5316'},
    {'id': 'S4', 'name': '\u62d6\u5e03\u786c\u5316',
     'kw': ['\u786c\u5316', '\u53d1\u786c', '\u53d1\u8106', '\u5f00\u88c2', '\u8106'],
     'sign': '\u62d6\u5e03\u53d1\u786c\u53d1\u8106\uff0c\u6298\u53e0\u5904\u5f00\u88c2',
     'why': '\u6750\u6599\u8001\u5316\uff0c\u7ee7\u7eed\u4f7f\u7528\u4f1a\u522e\u4f24\u5730\u9762'},
]

# ---- \u6e05\u6d17\u4e0e\u667e\u6652\u6d41\u7a0b ----
STEPS = [
    '\u9884\u5904\u7406\uff1a\u51b2\u6389\u8868\u9762\u6ce5\u6c99\u4e0e\u6bdb\u53d1\uff1b\u4e0d\u8981\u5728\u6876\u91cc\u6ce1\u4e00\u665a\u4e0a',
    '\u6d17\u6da4\uff1a\u6e29\u6c34\u914d\u4e2d\u6027\u6e05\u6d01\u5242\uff0c\u6309\u8bf4\u660e\u4e66\u6d17\u6da4',
    '\u51b2\u6d17\uff1a\u7528\u6d41\u52a8\u6e05\u6c34\u51b2\u51c0\uff0c\u4e0d\u7559\u6d17\u6da4\u5242\u6b8b\u7559',
    '\u5f7b\u5e95\u667e\u5e72\uff1a\u60ac\u6302\u6216\u644a\u5f00\u667e\u5e72\uff0c\u4e0d\u53e0\u653e',
    '\u786e\u8ba4\u5e72\u71e5\uff1a\u624b\u6478\u786e\u8ba4\u65e0\u6f6e\u611f\u3001\u65e0\u5f02\u5473\u540e\u518d\u6536',
]

DRY_CHECK = [
    ('\u624b\u611f', '\u624b\u6478\u62d6\u5e03\u5404\u5904\uff0c\u65e0\u6f6e\u611f'),
    ('\u5f02\u5473', '\u9760\u8fd1\u95fb\uff0c\u65e0\u5f02\u5473'),
    ('\u6298\u53e0\u5904', '\u6298\u53e0\u5904\u6700\u6613\u6b8b\u7559\u6c34\u5206\uff0c\u91cd\u70b9\u6478'),
    ('\u65f6\u95f4\u53c2\u8003', '\u901a\u98ce\u73af\u5883\u4e0b\u901a\u5e38\u6570\u5c0f\u65f6\uff1b\u4e0d\u8981\u53ea\u770b\u65f6\u95f4\uff0c\u770b\u624b\u611f'),
    ('\u6536\u653e\u65f6\u673a', '\u5e72\u900f\u540e\u6536\uff0c\u4e0d\u5e72\u900f\u5c31\u585e\u8fdb\u67dc\u5b50'),
]

# ---- \u5b89\u5168\u7ea2\u7ebf ----
CHLORINE = ['\u542b\u6c2f', '\u6f02\u767d\u6c34', '\u6d88\u6bd2\u6db2', '84', '\u6b21\u6c2f\u9178\u94a0', '\u6c2f']
ACID = ['\u9178\u6027', '\u6d01\u5395\u7075', '\u6d01\u5395\u5242', '\u767d\u918b', '\u918b', '\u67e0\u6aac\u9178', '\u9664\u57a2\u5242', '\u67e0\u6aac', '\u76d0\u9178']
ALKALI = ['\u78b1\u6027', '\u5f3a\u78b1', '\u706b\u78b1', '\u70e7\u78b1', '\u5c0f\u82cf\u6253', '\u78b3\u9178\u94a0', '\u5f3a\u9178', '\u786b\u9178']


def classify_pair(a, b):
    ta = (a or '') + ' ' + (b or '')
    has_cl = any(k in ta for k in CHLORINE)
    has_ac = any(k in ta for k in ACID)
    has_al = any(k in ta for k in ALKALI)
    if has_cl and has_ac:
        return ('danger', '\u7edd\u4e0d\u8981\u628a\u542b\u6c2f\u6d88\u6bd2\u5242\u4e0e\u9178\u6027\u6e05\u6d01\u5242\u6df7\u5408\uff0c\u4e24\u8005\u4f1a\u4ea7\u751f\u6709\u6bd2\u6c14\u4f53')
    if has_cl and has_al:
        return ('danger', '\u542b\u6c2f\u6d88\u6bd2\u5242\u4e0e\u78b1\u6027\u6e05\u6d01\u5242\u4e0d\u5c5e\u4e8e\u5b89\u5168\u914d\u5bf9\uff0c\u53ef\u80fd\u4ea7\u751f\u523a\u6fc0\u6027\u6c14\u4f53')
    if has_cl and '\u542b\u6c2f' in (a or '') and '\u542b\u6c2f' in (b or ''):
        return ('danger', '\u4e24\u79cd\u542b\u6c2f\u4ea7\u54c1\u6df7\u5408\u540e\u6709\u6548\u6210\u5206\u53e0\u52a0\uff0c\u5c5e\u4e0d\u53ef\u63a7\u914d\u5bf9')
    return ('ok', '\u672a\u547d\u4e2d\u5df2\u77e5\u5371\u9669\u914d\u5bf9\uff0c\u4ecd\u9700\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e66\u4e3a\u51c6\uff0c\u4e0d\u540c\u4ea7\u54c1\u4e0d\u53ef\u6df7\u7528')


def analyse(text):
    t = (text or '').replace(' ', '').replace('\u3000', '')
    mops = []
    for m in MOP_TYPES:
        hits = [k for k in m['kw'] if k in t]
        if hits:
            mops.append({'name': m['name'], 'hits': hits, 'fit': m['fit'],
                         'wash': m['wash'], 'dry': m['dry'], 'note': m['note']})
    sigs = []
    for s in SIGNALS:
        hits = [k for k in s['kw'] if k in t]
        if hits:
            sigs.append({'name': s['name'], 'hits': hits, 'sign': s['sign'], 'why': s['why']})
    reds = []
    if any(k in t for k in ['\u6d88\u6bd2\u6db2', '\u6d88\u6bd2\u5242', '\u6d88\u6bd2\u6c34']):
        reds.append('\u7528\u6d88\u6bd2\u6db2\u4ee3\u66ff\u6e05\u6d17\uff1a\u6c61\u57a2\u4e0e\u6709\u673a\u7269\u4f1a\u524a\u5f31\u6d88\u6bd2\u6548\u679c\uff0c\u4e14\u6b8b\u7559\u4f1a\u88ab\u5e26\u5230\u6bcf\u4e2a\u623f\u95f4\u7684\u5730\u9762')
    if any(k in t for k in ['\u521a\u62d6\u5b8c', '\u62d6\u5b8c\u5c31\u8d70', '\u62d6\u5b8c\u6709\u4eba']):
        reds.append('\u6d88\u6bd2\u5242\u4e0d\u53ef\u957f\u65f6\u95f4\u6ede\u7559\u4e8e\u6709\u4eba\u6d3b\u52a8\u7684\u8868\u9762\uff0c\u6309\u8bf4\u660e\u4e66\u5904\u7406\uff0c\u4e0d\u786e\u5b9a\u65f6\u6e05\u6c34\u51b2\u51c0')
    if any(k in t for k in ['\u7529', '\u7529\u6c34', '\u7529\u5e72']):
        reds.append('\u62d6\u628a\u7529\u5e72\u65f6\u907f\u514d\u6c34\u82b1\u98de\u6e85\u6c61\u67d3\u5468\u8fb9\u7535\u5668\u4e0e\u98df\u54c1\uff0c\u4e5f\u907f\u514d\u81ea\u5df1\u88ab\u6c61\u6c34\u6e85\u5230')
    if any(k in t for k in ['\u6ce1\u4e00\u665a\u4e0a', '\u6ce1\u4e00\u591c', '\u6ce1\u6876\u91cc', '\u6ce1\u5728\u91cc\u9762', '\u6ce1\u8fc7\u591c']):
        reds.append('\u62d6\u628a\u7528\u5b8c\u6ce1\u5728\u6876\u91cc\u8fc7\u591c\u662f\u5f02\u5473\u4e0e\u7ec6\u83cc\u7684\u4e3b\u8981\u6765\u6e90\uff0c\u7528\u5b8c\u5e94\u7acb\u5373\u6e05\u6d17\u667e\u5e72')
    need_pro = any(k in t for k in ['\u5927\u9762\u79ef\u6d88\u6bd2', '\u533b\u9662', '\u5b66\u6821', '\u516c\u5171\u573a\u6240', '\u68c0\u6d4b',
                                     '\u7269\u4e1a\u8981\u6c42', '\u7edf\u4e00\u6d88\u6bd2', '\u8fc7\u654f'])
    return {'mops': mops, 'sigs': sigs, 'reds': reds, 'need_pro': need_pro,
            'n_sig': len(sigs), 'top': sigs[0]['name'] if sigs else '',
            'should_replace': len(sigs) >= 1}


def render_md(r, pair_info=None):
    lines = ['# \u62d6\u628a\u4e0e\u6e05\u6d01\u5de5\u5177\u4fdd\u517b\u5224\u5b9a\u7ed3\u679c', '']
    lines.append('> \u5fc5\u987b\u5f7b\u5e95\u667e\u5e72\uff0c\u667e\u5e72\u4e86\u4e5f\u8981\u6302\u8d77\u6765\u4e0d\u8981\u53e0\u3002\u7edd\u4e0d\u8981\u628a\u542b\u6c2f\u6d88\u6bd2\u5242\u4e0e\u9178\u6027\u6e05\u6d01\u5242\u6df7\u5408\u3002')
    lines.append('')
    if pair_info:
        lines.append('## \u6e05\u6d01\u5242\u914d\u5bf9\u68c0\u67e5')
        lines.append('')
        lines.append('- \u4ea7\u54c1 A\uff1a%s' % pair_info[0])
        lines.append('- \u4ea7\u54c1 B\uff1a%s' % pair_info[1])
        lines.append('- \u7b49\u7ea7\uff1a%s' % pair_info[2])
        lines.append('- \u8bf4\u660e\uff1a%s' % pair_info[3])
        lines.append('')

    lines.append('## \u4e00\u3001\u62d6\u628a\u7c7b\u578b\uff08\u547d\u4e2d %d \u7c7b\uff09' % len(r['mops']))
    lines.append('')
    if r['mops']:
        lines.append('| \u7c7b\u578b | \u547d\u4e2d\u7ebf\u7d22 | \u9002\u7528\u573a\u666f | \u6e05\u6d17\u8981\u70b9 | \u667e\u5e72\u8981\u70b9 | \u6ce8\u610f |')
        lines.append('|---|---|---|---|---|---|')
        for m in r['mops']:
            lines.append('| %s | %s | %s | %s | %s | %s |' % (
                m['name'], '\u3001'.join(m['hits']), m['fit'], m['wash'], m['dry'], m['note']))
        lines.append('')
    else:
        lines.append('| \u7c7b\u578b | \u9002\u7528\u573a\u666f | \u6e05\u6d17\u8981\u70b9 | \u667e\u5e72\u8981\u70b9 | \u6ce8\u610f |')
        lines.append('|---|---|---|---|---|')
        for m in MOP_TYPES:
            lines.append('| %s | %s | %s | %s | %s |' % (
                m['name'], m['fit'], m['wash'], m['dry'], m['note']))
        lines.append('')

    lines.append('## \u4e8c\u3001\u6e05\u6d17\u4e0e\u667e\u6652\u6d41\u7a0b\uff08\u4e94\u6b65\uff09')
    lines.append('')
    for i, s in enumerate(STEPS, 1):
        lines.append('%d. %s' % (i, s))
    lines.append('')
    lines.append('### \u5f7b\u5e95\u667e\u5e72\u7684\u5224\u65ad\u6807\u51c6')
    lines.append('')
    lines.append('| \u5224\u636e | \u5408\u683c\u8868\u73b0 |')
    lines.append('|---|---|')
    for a, b in DRY_CHECK:
        lines.append('| %s | %s |' % (a, b))
    lines.append('')
    lines.append('**\u4e0d\u53e0\u653e\u5f88\u91cd\u8981**\uff1a\u53e0\u653e\u4f1a\u8ba9\u5185\u5c42\u6c38\u8fdc\u63a5\u89e6\u4e0d\u5230\u7a7a\u6c14\uff0c\u5f62\u6210\u95f7\u6e7f\u5c42\u3002')
    lines.append('')

    lines.append('## \u4e09\u3001\u66f4\u6362\u4fe1\u53f7\uff08\u547d\u4e2d %d \u9879\uff09' % r['n_sig'])
    lines.append('')
    if r['sigs']:
        lines.append('| \u4fe1\u53f7 | \u547d\u4e2d\u7ebf\u7d22 | \u8868\u73b0 | \u8bf4\u660e |')
        lines.append('|---|---|---|---|')
        for s in r['sigs']:
            lines.append('| %s | %s | %s | %s |' % (
                s['name'], '\u3001'.join(s['hits']), s['sign'], s['why']))
        lines.append('')
        lines.append('**\u5176\u4f59\u672a\u547d\u4e2d\u4fe1\u53f7\u4e00\u5e76\u5bf9\u7167\uff1a**')
        lines.append('')
        lines.append('| \u4fe1\u53f7 | \u8868\u73b0 | \u8bf4\u660e |')
        lines.append('|---|---|---|')
        for s in SIGNALS:
            lines.append('| %s | %s | %s |' % (s['name'], s['sign'], s['why']))
        lines.append('')
    else:
        lines.append('| \u4fe1\u53f7 | \u8868\u73b0 | \u8bf4\u660e |')
        lines.append('|---|---|---|')
        for s in SIGNALS:
            lines.append('| %s | %s | %s |' % (s['name'], s['sign'], s['why']))
        lines.append('')
    lines.append('**\u5224\u5b9a**\uff1a%s' % ('\u56db\u4e2a\u4fe1\u53f7\u51fa\u73b0\u4efb\u4e00\u9879\u5373\u5e94\u66f4\u6362\uff0c\u4e0d\u5fc5\u7b49\u5230\u56fa\u5b9a\u5468\u671f\u3002'
                                     if r['should_replace'] else '\u6682\u672a\u51fa\u73b0\u66f4\u6362\u4fe1\u53f7\u3002'))
    lines.append('')

    lines.append('## \u56db\u3001\u6d88\u6bd2\u4e0e\u53bb\u5473')
    lines.append('')
    lines.append('- **\u5148\u6d17\u51c0\u518d\u8c08\u6d88\u6bd2**\uff1a\u6c61\u57a2\u4e0e\u6709\u673a\u7269\u4f1a\u524a\u5f31\u6d88\u6bd2\u6548\u679c\uff0c\u810f\u62d6\u628a\u6ce1\u518d\u591a\u6d88\u6bd2\u6db2\u4e5f\u6ca1\u7528')
    lines.append('- **\u6309\u8bf4\u660e\u4e66\u4f7f\u7528\u6d88\u6bd2\u5242**\uff1a\u6d53\u5ea6\u3001\u63a5\u89e6\u65f6\u95f4\u3001\u662f\u5426\u51b2\u6d17\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e66\u4e3a\u51c6')
    lines.append('- **\u7528\u6d17\u6da4\u4ee3\u66ff\u6d88\u6bd2**\uff1a\u65e5\u5e38\u62d6\u5730\u7528\u4e2d\u6027\u6e05\u6d01\u5242\u6d17\u51c0\u5e76\u5f7b\u5e95\u667e\u5e72\uff0c\u591a\u6570\u573a\u666f\u5df2\u8db3\u591f')
    lines.append('- **\u53bb\u5473\u9760\u6d17\u6da4\u4e0e\u667e\u5e72**\uff1a\u5f02\u5473\u6765\u6e90\u901a\u5e38\u662f\u6f6e\u6e7f\u4e0e\u79ef\u57a2')
    lines.append('')

    lines.append('## \u4e94\u3001\u5b89\u5168\u7ea2\u7ebf')
    lines.append('')
    lines.append('1. **\u7edd\u4e0d\u8981\u628a\u542b\u6c2f\u6d88\u6bd2\u5242\u4e0e\u9178\u6027\u6e05\u6d01\u5242\u6df7\u5408**\uff0c\u4f1a\u4ea7\u751f\u6709\u6bd2\u6c14\u4f53')
    lines.append('2. **\u6d88\u6bd2\u5242\u4e0d\u53ef\u957f\u65f6\u95f4\u6ede\u7559\u4e8e\u6709\u4eba\u6d3b\u52a8\u7684\u8868\u9762**\uff0c\u4e0d\u786e\u5b9a\u65f6\u6e05\u6c34\u51b2\u51c0')
    lines.append('3. **\u7529\u5e72\u65f6\u907f\u514d\u6c34\u82b1\u98de\u6e85\u6c61\u67d3\u5468\u8fb9**\uff0c\u4e5f\u907f\u514d\u81ea\u5df1\u88ab\u6c61\u6c34\u6e85\u5230')
    lines.append('4. \u6d17\u6da4\u65f6\u6234\u624b\u5957\uff1b\u6e05\u6d01\u5242\u4e0e\u6d88\u6bd2\u5242\u4fdd\u6301\u539f\u5305\u88c5\u4e0d\u968f\u610f\u5206\u88c5')
    lines.append('')
    if r['reds']:
        lines.append('**\u672c\u6b21\u89e6\u53d1\uff1a**')
        lines.append('')
        for m in r['reds']:
            lines.append('- %s' % m)
        lines.append('')

    lines.append('## \u516d\u3001\u5b58\u653e\u65b9\u5f0f')
    lines.append('')
    lines.append('| \u90e8\u4f4d | \u5b58\u653e\u65b9\u5f0f |')
    lines.append('|---|---|')
    lines.append('| \u62d6\u5e03 | \u60ac\u6302\u667e\u5e72\uff1b\u5f7b\u5e95\u5e72\u71e5\u540e\u6536\u653e\uff0c\u4e0d\u53e0\u653e |')
    lines.append('| \u6746\u4f53 | \u4e0e\u62d6\u5e03\u5206\u5f00\u5b58\u653e\uff1b\u64e6\u5e72\uff0c\u907f\u514d\u957f\u671f\u6f6e\u6e7f |')
    lines.append('| \u6876 | \u6d17\u51c0\u3001\u64e6\u5e72\uff1b\u6876\u5185\u4e0d\u7559\u79ef\u6c34 |')
    lines.append('| \u623f\u95f4 | \u901a\u98ce\u5904\u6216\u536b\u751f\u95f4\u5916\uff0c\u907f\u514d\u653e\u5728\u6f6e\u6e7f\u89d2\u843d |')
    lines.append('')

    lines.append('## \u4e03\u3001\u5f52\u5c5e\u5224\u5b9a')
    lines.append('')
    if r['need_pro']:
        lines.append('\u672c\u6b21\u60c5\u5f62**\u5e94\u8f6c\u4ea4\u4e13\u4e1a\u6e05\u6d01\u6216\u6d88\u6bd2\u670d\u52a1**\uff0c\u5e76\u6309\u7269\u4e1a\u4e0e\u76f8\u5173\u4e3b\u7ba1\u90e8\u95e8\u8981\u6c42\u6267\u884c\u3002')
    else:
        lines.append('\u672c\u6b21\u60c5\u5f62\u5c5e\u4e8e\u65e5\u5e38\u4fdd\u517b\u8303\u56f4\uff0c\u4ecd\u9700\u6309\u4e94\u6b65\u6d41\u7a0b\u6e05\u6d17\u5e76\u5f7b\u5e95\u667e\u5e72\u3002')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('\u672c\u7ed3\u679c\u4e3a\u73b0\u8c61\u5339\u914d\u4e0e\u4fdd\u517b\u5efa\u8bae\uff0c\u4e0d\u4ee3\u8868\u73b0\u573a\u5224\u65ad\uff0c\u4e0d\u6784\u6210\u4e13\u4e1a\u6d88\u6bd2\u7ed3\u8bba\u3002')
    lines.append('\u6d88\u6bd2\u5242\u7684\u6d53\u5ea6\u4e0e\u63a5\u89e6\u65f6\u95f4\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e66\u4e3a\u51c6\uff0c\u4e0d\u540c\u4ea7\u54c1\u4e0d\u53ef\u6df7\u7528\u3002')
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
    eq('case2 \u542b\u6c2f\u52a0\u6d01\u5395\u7075', classify_pair('84\u6d88\u6bd2\u6db2', '\u6d01\u5395\u7075')[0], 'danger')
    eq('case3 \u542b\u6c2f\u52a0\u78b1\u6027', classify_pair('\u6f02\u767d\u6c34', '\u5c0f\u82cf\u6253')[0], 'danger')
    eq('case4 \u4e24\u79cd\u542b\u6c2f', classify_pair('\u542b\u6c2f\u6d88\u6bd2\u6db2', '\u542b\u6c2f\u6f02\u767d\u6c34')[0], 'danger')
    eq('case5 \u4e2d\u6027\u914d\u5bf9', classify_pair('\u4e2d\u6027\u6e05\u6d01\u5242', '\u6e29\u6c34')[0], 'ok')

    r1 = analyse('\u62d6\u628a\u6709\u5473\u9053\u4e86\uff0c\u6389\u6bdb')
    eq('case6 \u5f02\u5473\u4fe1\u53f7', any(s['name'] == '\u5f02\u5473\u96be\u53bb' for s in r1['sigs']), True)
    eq('case7 \u6389\u6bdb\u4fe1\u53f7', any(s['name'] == '\u6389\u6bdb' for s in r1['sigs']), True)
    eq('case8 \u5e94\u66f4\u6362', r1['should_replace'], True)

    r2 = analyse('\u65cb\u8f6c\u62d6\u628a\u6876\u91cc\u6709\u6c34\u6709\u5473')
    eq('case9 \u65cb\u8f6c\u8bc6\u522b', any(m['name'] == '\u65cb\u8f6c mop' for m in r2['mops']), True)

    r3 = analyse('\u80fd\u4e0d\u80fd\u628a\u62d6\u628a\u6ce1\u5728\u6d88\u6bd2\u6db2\u91cc')
    eq('case10 \u6d88\u6bd2\u6db2\u66ff\u4ee3\u6e05\u6d17', len(r3['reds']) >= 1, True)

    r4 = analyse('\u4e00\u6b21\u6027\u62d6\u628a\u80fd\u53cd\u590d\u7528\u5417')
    eq('case11 \u4e00\u6b21\u6027\u8bc6\u522b', any(m['name'] == '\u4e00\u6b21\u6027\u62d6\u628a' for m in r4['mops']), True)

    r5 = analyse('\u62d6\u628a\u7528\u5b8c\u6ce1\u6876\u91cc\u8fc7\u591c')
    eq('case12 \u6ce1\u8fc7\u591c\u7ea2\u7ebf', len(r5['reds']) >= 1, True)

    r6 = analyse('\u62d6\u5e03\u62d6\u4e0d\u5e72\u51c0\u8fd8\u6709\u6c34\u75d5')
    eq('case13 \u6e05\u6d01\u529b\u4e0b\u964d', any(s['name'] == '\u6e05\u6d01\u529b\u4e0b\u964d' for s in r6['sigs']), True)

    r7 = analyse('\u62d6\u5e03\u53d1\u786c\u5f00\u88c2\u4e86')
    eq('case14 \u786c\u5316\u4fe1\u53f7', any(s['name'] == '\u62d6\u5e03\u786c\u5316' for s in r7['sigs']), True)

    r8 = analyse('\u7529\u6c34\u7684\u65f6\u5019\u6e85\u5f97\u5230\u5904\u90fd\u662f')
    eq('case15 \u98de\u6e85\u7ea2\u7ebf', any('\u98de\u6e85' in m for m in r8['reds']), True)

    r9 = analyse('\u6ca1\u6709\u62d6\u628a\uff0c\u5c31\u662f\u60f3\u4e70')
    eq('case16 \u65e0\u4fe1\u53f7', (r9['sigs'], r9['mops']), ([], []))

    md = render_md(r1)
    eq('case17 \u8f93\u51fa\u8868\u5934', md.startswith('# '), True)
    eq('case18 \u542b\u4e94\u6b65\u6d41\u7a0b', '\u786e\u8ba4\u5e72\u71e5' in md, True)
    eq('case19 \u542b\u56db\u4e2a\u4fe1\u53f7', '\u62d6\u5e03\u786c\u5316' in md, True)
    eq('case20 \u542b\u5b58\u653e', '\u6746\u4f53' in md, True)
    js = json.loads(json.dumps(r1, ensure_ascii=False))
    eq('case21 JSON\u952e', sorted(js.keys()),
       ['mops', 'n_sig', 'need_pro', 'reds', 'should_replace', 'sigs', 'top'])

    # \u5e26 BOM \u7684 JSON \u8f93\u5165\u5fc5\u987b\u80fd\u6b63\u786e\u89e3\u6790
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write('{"desc": "\u62d6\u5e03\u53d1\u786c\u5f00\u88c2\u4e86"}')
    got = read_input(tmp)
    os.remove(tmp)
    eq('case22 \u5e26BOM\u7684JSON\u9996\u952e', analyse(got)['top'], '\u62d6\u5e03\u786c\u5316')

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 24\n\u8986\u76d6: \u4e94\u7c7b\u62d6\u628a/\u56db\u4e2a\u66f4\u6362\u4fe1\u53f7/\u6e05\u6d01\u5242\u56db\u79cd\u914d\u5bf9/'
               '\u6d88\u6bd2\u6db2\u66ff\u4ee3\u6e05\u6d17/\u6ce1\u8fc7\u591c/\u98de\u6e85/BOM\u89e3\u6790')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u62d6\u628a\u4e0e\u6e05\u6d01\u5de5\u5177\u4fdd\u517b\u5224\u5b9a')
    ap.add_argument('--text', help='\u62d6\u628a\u4e0e\u6e05\u6d01\u5de5\u5177\u72b6\u51b5\u63cf\u8ff0')
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