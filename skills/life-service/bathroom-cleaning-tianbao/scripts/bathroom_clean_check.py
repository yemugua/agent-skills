# -*- coding: utf-8 -*-
"""\u536b\u751f\u95f4\u6e05\u6d01\u5224\u5b9a\uff1a\u5339\u914d\u516d\u7c7b\u6c61\u6e0d\u3001\u6309\u6750\u8d28\u7ed9\u51fa\u7981\u5fcc\u3001\u68c0\u67e5\u6e05\u6d01\u5242\u914d\u5bf9\u4e0e\u8f6c\u4ea4\u6761\u4ef6\u3002

\u7528\u6cd5:
  python bathroom_clean_check.py --text "\u9a6c\u6876\u6709\u9ec4\u6e0d\uff0c\u6dcb\u6d74\u73bb\u7483\u6709\u6c34\u57a2"
  python bathroom_clean_check.py --pair "\u542b\u6c2f\u6d88\u6bd2\u6db2" "\u6d01\u5395\u7075"
  python bathroom_clean_check.py --file \u60c5\u51b5.txt --out \u7ed3\u679c.md
  python bathroom_clean_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ---- \u516d\u7c7b\u6c61\u6e0d ----
STAINS = [
    {'id': 'T1', 'name': '\u6c34\u57a2',
     'kw': ['\u6c34\u57a2', '\u6c34\u6e0d', '\u6c34\u78b1', '\u767d\u8272\u6c89\u79ef', '\u6c34\u9f99\u5934\u53d1\u767d', '\u77ff\u7269'],
     'sign': '\u767d\u8272\u6216\u7070\u767d\u8272\u786c\u8d28\u6c89\u79ef\uff0c\u80fd\u522e\u4e0b\uff0c\u96c6\u4e2d\u5728\u6c34\u9f99\u5934\u4e0e\u6dcb\u6d74\u73bb\u7483\u4e0e\u74f7\u7816\u7f1d',
     'cause': '\u6c34\u4e2d\u77ff\u7269\u8d28\u6790\u51fa',
     'fix': '\u9700\u9178\u6027\u6216\u4e13\u7528\u9664\u57a2\u5242\uff0c\u4f7f\u7528\u524d\u5fc5\u987b\u5148\u67e5\u8868\u9762\u6750\u8d28'},
    {'id': 'T2', 'name': '\u7682\u57a2',
     'kw': ['\u7682\u57a2', '\u6ed1\u817b', '\u7682\u818f', '\u767d\u8272\u6ed1', '\u817b'],
     'sign': '\u767d\u8272\u6216\u6de1\u9ec4\u6ed1\u817b\u6c89\u79ef\uff0c\u96c6\u4e2d\u5728\u53f0\u9762\u8fb9\u7f18\u4e0e\u6d74\u7f38\u8fb9',
     'cause': '\u8102\u80aa\u9178\u4e0e\u6c34\u4e2d\u77ff\u7269\u8d28\u7ed3\u5408',
     'fix': '\u4e2d\u6027\u6e05\u6d01\u5242\u52a0\u6e29\u6c34\u8f6f\u5316\uff1b\u4e25\u91cd\u65f6\u7528\u4e13\u7528\u7682\u57a2\u6e05\u6d01\u5242'},
    {'id': 'T3', 'name': '\u9709\u6591',
     'kw': ['\u9709\u6591', '\u53d1\u9ed1', '\u9ed1\u6591', '\u7eff\u6591', '\u9709\u70b9', '\u53d1\u9709', '\u7f1d\u91cc\u9ed1'],
     'sign': '\u9ed1\u8272\u3001\u7eff\u8272\u6216\u7070\u9ed1\u6591\uff0c\u96c6\u4e2d\u5728\u74f7\u7816\u7f1d\u3001\u5899\u89d2\u3001\u5bc6\u5c01\u80f6\u5904',
     'cause': '\u957f\u671f\u6f6e\u6e7f\u4e0e\u4e0d\u901a\u98ce',
     'fix': '\u9664\u9709\u5904\u7406\u5e76\u89e3\u51b3\u6f6e\u6e7f\u6765\u6e90\uff0c\u6e05\u6d01\u672c\u8eab\u53ea\u662f\u6536\u5c3e'},
    {'id': 'T4', 'name': '\u9508\u6e0d',
     'kw': ['\u9508', '\u9508\u6591', '\u6a59\u8272', '\u8910\u6591', '\u6c27\u5316', '\u91d1\u5c5e\u4ef6\u6709\u6591'],
     'sign': '\u6a59\u8910\u8272\u6216\u6df1\u8910\u8272\u6591\u70b9\uff0c\u96c6\u4e2d\u5728\u91d1\u5c5e\u4ef6\u4e0e\u6c34\u9f99\u5934\u4e0e\u87ba\u6813\u5904',
     'cause': '\u94c1\u4ef6\u6c27\u5316',
     'fix': '\u8f7b\u8005\u7528\u4e2d\u6027\u9664\u9508\uff1b\u4e25\u91cd\u65f6\u66f4\u6362\u4ef6'},
    {'id': 'T5', 'name': '\u5c3f\u78b1',
     'kw': ['\u5c3f\u78b1', '\u9ec4\u6e0d', '\u9ec4\u8272', '\u5c0f\u4fbf\u6597', '\u9a6c\u6876\u91cc\u9ec4', '\u7ed3\u6676'],
     'sign': '\u9ec4\u8272\u6216\u9ec4\u8910\u8272\u7ed3\u6676\uff0c\u4e3b\u8981\u5728\u9a6c\u6876\u5185\u58c1\u4e0e\u5c0f\u4fbf\u6597',
     'cause': '\u5c3f\u6db2\u4e2d\u7684\u7269\u8d28\u6c89\u79ef',
     'fix': '\u9178\u6027\u6e05\u6d01\u5242\u4e3a\u4e3b\uff0c\u5fc5\u987b\u907f\u5f00\u94dd\u5408\u91d1\u4e0e\u5f69\u8272\u91d1\u5c5e\u4ef6'},
    {'id': 'T6', 'name': '\u6cb9\u6c61',
     'kw': ['\u6cb9\u6c61', '\u6cb9\u819c', '\u6cb9\u817b', '\u9ecf\u817b', '\u6cb9\u4eae'],
     'sign': '\u9ecf\u817b\u6cb9\u819c\uff0c\u96c6\u4e2d\u5728\u6d17\u624b\u53f0\u5468\u8fb9\u4e0e\u955c\u5b50\u8fb9\u7f18',
     'cause': '\u6d17\u624b\u4e0e\u70f9\u996a\u5e26\u5165',
     'fix': '\u4e2d\u6027\u53bb\u6cb9\u6e05\u6d01\u5242'},
]

# ---- \u6750\u8d28\u7981\u5fcc ----
MATERIALS = [
    {'id': 'M1', 'name': '\u5927\u7406\u77f3\u3001\u5929\u7136\u77f3',
     'kw': ['\u5927\u7406\u77f3', '\u5929\u7136\u77f3', '\u77f3\u6750', '\u7389\u77f3'],
     'ban': '\u4e25\u7981\u4f7f\u7528\u9178\u6027\u6e05\u6d01\u5242',
     'why': '\u9178\u6027\u4f1a\u8150\u8680\u77f3\u6750\u8868\u9762\uff0c\u9020\u6210\u6c38\u4e45\u5931\u53bb\u5149\u6cfd\u4e0e\u8d28\u611f\u635f\u4f24'},
    {'id': 'M2', 'name': '\u5f69\u8272\u91d1\u5c5e\u4ef6',
     'kw': ['\u5f69\u8272', '\u70e4\u6f06', '\u7535\u9540', '\u5f69\u8272\u4ef6', '\u55b7\u6f06'],
     'ban': '\u7981\u6b62\u5f3a\u9178\u5f3a\u78b1',
     'why': '\u8868\u9762\u9540\u5c42\u4f1a\u88ab\u8150\u8680\u53d8\u8272'},
    {'id': 'M3', 'name': '\u4e9a\u514b\u529b\u3001\u6709\u673a\u73bb\u7483',
     'kw': ['\u4e9a\u514b\u529b', '\u6709\u673a\u73bb\u7483', '\u6d74\u7f38', '\u6dcb\u6d74\u623f', '\u6321\u6c34\u677f'],
     'ban': '\u7981\u6b62\u94a2\u4e1d\u7403\u4e0e\u786c\u8d28\u5237\u5177',
     'why': '\u4f1a\u5212\u4f24\u8868\u9762\u4ea7\u751f\u6c38\u4e45\u5212\u75d5'},
    {'id': 'M4', 'name': '\u94dd\u5236\u54c1',
     'kw': ['\u94dd\u5408\u91d1', '\u94dd\u5236', '\u94dd\u4ef6', '\u6302\u4ef6\u94dd'],
     'ban': '\u7981\u6b62\u6d01\u5395\u5242\u4e0e\u5f3a\u9178',
     'why': '\u4f1a\u88ab\u8150\u8680\u53d1\u767d\u8d77\u6591'},
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
    stains = []
    for s in STAINS:
        hits = [k for k in s['kw'] if k in t]
        if hits:
            stains.append({'name': s['name'], 'hits': hits, 'sign': s['sign'],
                           'cause': s['cause'], 'fix': s['fix']})
    mats = []
    for m in MATERIALS:
        hits = [k for k in m['kw'] if k in t]
        if hits:
            mats.append({'name': m['name'], 'hits': hits, 'ban': m['ban'], 'why': m['why']})
    reds = []
    if any(k in t for k in ['\u94a2\u4e1d\u7403']):
        reds.append('\u94a2\u4e1d\u7403\u4f1a\u5212\u4f24\u4e9a\u514b\u529b\u3001\u6709\u673a\u73bb\u7483\u4e0e\u6dcb\u6d74\u623f\u8868\u9762\uff0c\u4ea7\u751f\u6c38\u4e45\u5212\u75d5')
    if any(k in t for k in ['\u6df7', '\u4e00\u8d77\u5012', '\u5151', '\u540c\u65f6\u7528', '\u6df7\u5408\u7528']):
        if any(k in t for k in CHLORINE):
            reds.append('\u542b\u6c2f\u6d88\u6bd2\u5242\u4e0d\u5f97\u4e0e\u9178\u6027\u6216\u78b1\u6027\u6e05\u6d01\u5242\u6df7\u5408\u4f7f\u7528')
    need_pro = any(k in t for k in ['\u6392\u6c34\u6162', '\u6392\u6c34\u8d8a', '\u6392\u4e0d\u5feb', '\u6d41\u4e0d\u5feb',
                                 '\u5835\u585e', '\u8fd4\u6c34', '\u6c34\u6d0d', '\u4e0b\u6c34\u6162',
                                 '\u9632\u6c34', '\u697c\u4e0b\u6709\u6c34', '\u6e17\u6c34', '\u6f0f\u6c34',
                                 '\u62c6\u6d01\u5177', '\u62c6\u9a6c\u6876', '\u62c6\u9762\u76c6', '\u9690\u853d\u7ba1\u9053'])
    return {'stains': stains, 'mats': mats, 'reds': reds, 'need_pro': need_pro}


def render_md(r, pair_info=None):
    lines = ['# \u536b\u751f\u95f4\u6e05\u6d01\u5224\u5b9a\u7ed3\u679c', '']
    lines.append('> \u5148\u5224\u6c61\u6e0d\u7c7b\u578b\uff0c\u518d\u67e5\u6750\u8d28\u7981\u5fcc\u3002\u7c7b\u578b\u5224\u9519\u4f1a\u635f\u4f24\u8868\u9762\uff0c\u914d\u5bf9\u9519\u8bef\u4f1a\u4f24\u5bb3\u4eba\u3002')
    lines.append('')
    if pair_info:
        lines.append('## \u6e05\u6d01\u5242\u914d\u5bf9\u68c0\u67e5')
        lines.append('')
        lines.append('- \u4ea7\u54c1 A\uff1a%s' % pair_info[0])
        lines.append('- \u4ea7\u54c1 B\uff1a%s' % pair_info[1])
        lines.append('- \u7b49\u7ea7\uff1a%s' % pair_info[2])
        lines.append('- \u8bf4\u660e\uff1a%s' % pair_info[3])
        lines.append('')

    lines.append('## \u4e00\u3001\u6c61\u6e0d\u7c7b\u578b\u5224\u5b9a\uff08\u547d\u4e2d %d \u7c7b\uff09' % len(r['stains']))
    lines.append('')
    if not r['stains']:
        lines.append('\u672a\u8bc6\u522b\u6c61\u6e0d\u7c7b\u578b\u3002\u53ef\u63cf\u8ff0\uff1a\u767d\u4e14\u786c\u3001\u767d\u4e14\u6ed1\u817b\u3001\u9ed1\u7eff\u3001\u6a59\u8910\u3001\u9ec4\u8272\u7ed3\u6676\uff0c\u8fd8\u662f\u9ecf\u817b\u6210\u819c\u3002')
    else:
        lines.append('| \u7c7b\u578b | \u547d\u4e2d\u7ebf\u7d22 | \u8bc6\u522b\u7279\u5f81 | \u4e3b\u8981\u6210\u56e0 | \u5904\u7406\u65b9\u5411 |')
        lines.append('|---|---|---|---|---|')
        for s in r['stains']:
            lines.append('| %s | %s | %s | %s | %s |' % (
                s['name'], '\u3001'.join(s['hits']), s['sign'], s['cause'], s['fix']))
        lines.append('')

    lines.append('## \u4e8c\u3001\u6750\u8d28\u7981\u5fcc\uff08\u672c\u6b21\u6d89\u53ca %d \u7c7b\uff09' % len(r['mats']))
    lines.append('')
    if r['mats']:
        lines.append('| \u6750\u8d28 | \u547d\u4e2d\u7ebf\u7d22 | \u7981\u5fcc | \u539f\u56e0 |')
        lines.append('|---|---|---|---|')
        for m in r['mats']:
            lines.append('| %s | %s | %s | %s | ' % (
                m['name'], '\u3001'.join(m['hits']), m['ban'], m['why']))
        lines.append('')
    else:
        lines.append('\u672c\u6b21\u672a\u8bc6\u522b\u5177\u4f53\u6750\u8d28\u3002**\u4f7f\u7528\u4efb\u4f55\u9178\u6027\u6e05\u6d01\u5242\u524d\uff0c\u5148\u786e\u8ba4\u8868\u9762\u4e0d\u662f\u5927\u7406\u77f3\u3001\u5929\u7136\u77f3\u3001\u5f69\u8272\u91d1\u5c5e\u4ef6\u6216\u94dd\u5236\u54c1\u3002**')
        lines.append('')
    lines.append('| \u6750\u8d28\u6216\u90e8\u4f4d | \u7981\u5fcc | \u539f\u56e0 |')
    lines.append('|---|---|---|')
    lines.append('| \u5927\u7406\u77f3\u3001\u5929\u7136\u77f3 | \u4e25\u7981\u9178\u6027\u6e05\u6d01\u5242 | \u8150\u8680\u8868\u9762\uff0c\u6c38\u4e45\u5931\u53bb\u5149\u6cfd |')
    lines.append('| \u5f69\u8272\u91d1\u5c5e\u4ef6\uff08\u70e4\u6f06\u3001\u5f69\u8272\u7535\u9540\uff09 | \u5f3a\u9178\u5f3a\u78b1 | \u9540\u5c42\u88ab\u8150\u8680\u53d8\u8272 |')
    lines.append('| \u4e9a\u514b\u529b\u3001\u6709\u673a\u73bb\u7483 | \u94a2\u4e1d\u7403\u3001\u786c\u8d28\u5237\u5177 | \u6c38\u4e45\u5212\u75d5 |')
    lines.append('| \u94dd\u5236\u54c1 | \u6d01\u5395\u5242\u3001\u5f3a\u9178 | \u8150\u8680\u53d1\u767d\u8d77\u6591 |')
    lines.append('| \u4efb\u4f55\u8868\u9762 | \u542b\u6c2f\u6d88\u6bd2\u5242\u4e0e\u9178\u6027\u6e05\u6d01\u5242\u6df7\u5408 | \u4ea7\u751f\u6709\u6bd2\u6c14\u4f53 |')
    lines.append('| \u542b\u6c2f\u6d88\u6bd2\u5242 | \u4e0e\u78b1\u6027\u6e05\u6d01\u5242\u6df7\u5408 | \u540c\u6837\u4e0d\u5c5e\u4e8e\u5b89\u5168\u914d\u5bf9 |')
    lines.append('| \u4e0d\u9508\u94a2 | \u5f3a\u9178\u540e\u53ca\u65f6\u51b2\u51c0 | \u957f\u65f6\u95f4\u63a5\u89e6\u4ea7\u751f\u9508\u6591 |')
    lines.append('')

    lines.append('## \u4e09\u3001\u6309\u533a\u57df\u5206\u9891\u6b21')
    lines.append('')
    lines.append('| \u533a\u57df | \u5efa\u8bae\u9891\u6b21 | \u91cd\u70b9 |')
    lines.append('|---|---|---|')
    lines.append('| \u53f0\u9762 | \u6bcf\u65e5\u6216\u6bcf\u6b21\u4f7f\u7528\u540e | \u6c34\u6e0d\u4e0e\u7682\u57a2\uff0c\u53ca\u65f6\u64e6\u6700\u7701\u529b |')
    lines.append('| \u955c\u9762 | \u6bcf\u5468 | \u6c34\u6e0d\u4e0e\u624b\u5370 |')
    lines.append('| \u9a6c\u6876 | \u6bcf\u5468\uff1b\u5c3f\u78b1\u4e25\u91cd\u65f6\u589e\u52a0 | \u5237\u6d17\u4e0e\u9664\u57a2\u5206\u5f00 |')
    lines.append('| \u6d74\u7f38 | \u6bcf\u5468 | \u7682\u57a2\u4e0e\u6c34\u57a2 |')
    lines.append('| \u5730\u6f0f | \u6bcf\u5468 | \u6bdb\u53d1\u4e0e\u6c61\u57a2 |')
    lines.append('| \u74f7\u7816\u7f1d | \u6bcf\u6708\uff1b\u9709\u53d8\u540e\u589e\u52a0 | \u53d1\u9ed1\u4e0e\u9709\u6591 |')
    lines.append('| \u6dcb\u6d74\u73bb\u7483 | \u6bcf\u5468 | \u6c34\u57a2\uff0c\u9700\u4e13\u7528\u9664\u57a2 |')
    lines.append('| \u6392\u6c14\u6247 | \u6bcf\u5b63\u5ea6 | \u6cb9\u6c61\u4e0e\u7070\u5c18 |')
    lines.append('')
    lines.append('**\u6c34\u6e0d\u53ca\u65f6\u64e6\u6bd4\u5b9a\u671f\u9664\u57a2\u7701\u529b\u5f97\u591a\u3002**')
    lines.append('')

    lines.append('## \u56db\u3001\u9664\u57a2\u7684\u539f\u7406\u4e0e\u7b49\u5f85\u65f6\u95f4')
    lines.append('')
    lines.append('\u9664\u57a2\u5242\u9700\u8981\u4fdd\u6301\u6e7f\u6da6\u63a5\u89e6\u624d\u80fd\u4e0e\u6c34\u57a2\u53cd\u5e94\u3002\u55b7\u4e0a\u7acb\u523b\u64e6\u6389\uff0c\u6548\u679c\u4f1a\u5927\u5e45\u4e0b\u964d\u3002')
    lines.append('')
    lines.append('1. \u5148\u51b2\u6c34\u53bb\u6389\u8868\u9762\u6d6e\u5c42')
    lines.append('2. \u6309\u8bf4\u660e\u4e66\u55b7\u6d12\u6216\u6d82\u62b9')
    lines.append('3. **\u4fdd\u6301\u6e7f\u6da6\u63a5\u89e6\uff0c\u6309\u8bf4\u660e\u4e66\u89c4\u5b9a\u65f6\u95f4\u7b49\u5f85**')
    lines.append('4. \u7528\u8f6f\u5e03\u6216\u5237\u5177\u5904\u7406')
    lines.append('5. \u7528\u6e05\u6c34\u5f7b\u5e95\u51b2\u51c0')
    lines.append('')
    lines.append('> \u5177\u4f53\u7b49\u5f85\u65f6\u95f4\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e66\u4e3a\u51c6\uff0c\u4e0d\u540c\u4ea7\u54c1\u914d\u65b9\u5dee\u5f02\u5f88\u5927\uff0c\u4e0d\u8981\u5957\u7528\u522b\u5bb6\u7684\u6570\u503c\u3002')
    lines.append('')

    lines.append('## \u4e94\u3001\u5b89\u5168\u63d0\u9192')
    lines.append('')
    if r['reds']:
        for m in r['reds']:
            lines.append('- %s' % m)
    else:
        lines.append('- **\u4e25\u7981\u5c06\u542b\u6c2f\u6d88\u6bd2\u5242\u4e0e\u9178\u6027\u6e05\u6d01\u5242\u6df7\u5408\u4f7f\u7528**\uff0c\u4f1a\u4ea7\u751f\u6709\u6bd2\u6c14\u4f53\u3002')
        lines.append('- \u4e00\u6b21\u53ea\u7528\u4e00\u79cd\u6e05\u6d01\u5242\uff0c\u7528\u5b8c\u51b2\u51c0\u518d\u6362\u4e0b\u4e00\u79cd\u3002')
        lines.append('- \u6e05\u6d01\u5242\u4fdd\u6301\u539f\u5305\u88c5\uff0c\u4e0d\u5206\u88c5\u5230\u4e0d\u660e\u5bb9\u5668\u3002')
        lines.append('- \u5728\u4e0d\u663e\u773c\u5904\u5148\u8bd5\u7528\uff0c\u89c2\u5bdf\u6709\u65e0\u53d8\u8272\u6216\u635f\u4f24\u3002')
    lines.append('')

    lines.append('## \u516d\u3001\u5f52\u5c5e\u5224\u5b9a')
    lines.append('')
    if r['need_pro']:
        lines.append('\u672c\u6b21\u60c5\u5f62**\u5e94\u8054\u7cfb\u4e13\u4e1a\u4eba\u5458**\uff1a\u6d89\u53ca\u6392\u6c34\u5835\u585e\u3001\u9632\u6c34\u5c42\u95ee\u9898\u3001\u9690\u853d\u7ba1\u9053\u6e17\u6f0f\u6216\u9700\u62c6\u88c5\u6d01\u5177\u3002')
    else:
        lines.append('\u672c\u6b21\u60c5\u5f62\u5c5e\u4e8e\u53ef\u81ea\u884c\u6e05\u6d01\u8303\u56f4\uff0c\u4f46\u4ecd\u9700\u5148\u786e\u8ba4\u6c61\u6e0d\u7c7b\u578b\u4e0e\u8868\u9762\u6750\u8d28\u3002')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('\u672c\u7ed3\u679c\u4e3a\u73b0\u8c61\u5339\u914d\u4e0e\u6750\u8d28\u63d0\u793a\uff0c\u4e0d\u4ee3\u8868\u73b0\u573a\u5224\u65ad\uff0c\u4e0d\u6784\u6210\u4e13\u4e1a\u65bd\u5de5\u7ed3\u8bba\u3002')
    lines.append('\u6e05\u6d01\u5242\u9002\u7528\u8303\u56f4\u4e0e\u7b49\u5f85\u65f6\u95f4\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e66\u4e3a\u51c6\uff0c\u4e0d\u540c\u4ea7\u54c1\u4e0d\u53ef\u6df7\u7528\u3002')
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

    eq('case1 \u542b\u6c2f\u52a0\u9178\u6027', classify_pair('\u542b\u6c2f\u6d88\u6bd2\u6db2', '\u6d01\u5395\u7075')[0], 'danger')
    eq('case2 \u542b\u6c2f\u52a0\u767d\u918b', classify_pair('\u6f02\u767d\u6c34', '\u767d\u918b')[0], 'danger')
    eq('case3 \u542b\u6c2f\u52a0\u78b1\u6027', classify_pair('84\u6d88\u6bd2\u6db2', '\u5c0f\u82cf\u6253')[0], 'danger')
    eq('case4 \u4e2d\u6027\u914d\u5bf9', classify_pair('\u4e2d\u6027\u6e05\u6d01\u5242', '\u6e29\u6c34')[0], 'ok')

    r1 = analyse('\u9a6c\u6876\u6709\u9ec4\u6e0d\uff0c\u6dcb\u6d74\u73bb\u7483\u6709\u6c34\u57a2')
    eq('case5 \u9ec4\u6e0d\u547d\u4e2d', any(s['name'] == '\u5c3f\u78b1' for s in r1['stains']), True)
    eq('case6 \u6c34\u57a2\u547d\u4e2d', any(s['name'] == '\u6c34\u57a2' for s in r1['stains']), True)

    r2 = analyse('\u5927\u7406\u77f3\u53f0\u9762\u60f3\u7528\u6d01\u5395\u5242\u6e05\u4e00\u4e0b')
    eq('case7 \u5927\u7406\u77f3\u7981\u5fcc', any('\u5927\u7406\u77f3' in m['name'] for m in r2['mats']), True)
    eq('case8 \u9178\u6027\u63d0\u793a', any('\u9178\u6027' in m['ban'] for m in r2['mats']), True)

    r3 = analyse('\u4e9a\u514b\u529b\u6d74\u7f38\u7528\u94a2\u4e1d\u7403\u5237')
    eq('case9 \u4e9a\u514b\u529b\u7981\u5fcc', any('\u4e9a\u514b\u529b' in m['name'] for m in r3['mats']), True)
    eq('case10 \u94a2\u4e1d\u7403\u7ea2\u7ebf', len(r3['reds']) >= 1, True)

    r4 = analyse('\u74f7\u7816\u7f1d\u53d1\u9ed1\u4e86')
    eq('case11 \u9709\u6591\u547d\u4e2d', any(s['name'] == '\u9709\u6591' for s in r4['stains']), True)

    r5 = analyse('\u6c34\u9f99\u5934\u6709\u9508\u6591')
    eq('case12 \u9508\u6e0d\u547d\u4e2d', any(s['name'] == '\u9508\u6e0d' for s in r5['stains']), True)

    r6 = analyse('\u6392\u6c34\u8d8a\u6765\u8d8a\u6162')
    eq('case13 \u8f6c\u4e13\u4e1a\u4eba\u5458', r6['need_pro'], True)

    r7 = analyse('\u94dd\u5408\u91d1\u6302\u4ef6\u80fd\u7528\u6d01\u5395\u5242\u5417')
    eq('case14 \u94dd\u5236\u54c1\u7981\u5fcc', any('\u94dd' in m['name'] for m in r7['mats']), True)

    r8 = analyse('\u53f0\u9762\u6709\u70b9\u9ecf\u817b\u7684\u6cb9\u819c')
    eq('case15 \u6cb9\u6c61\u547d\u4e2d', any(s['name'] == '\u6cb9\u6c61' for s in r8['stains']), True)

    r9 = analyse('\u4ec0\u4e48\u90fd\u6ca1\u6709')
    eq('case16 \u65e0\u5339\u914d', (r9['stains'], r9['mats']), ([], []))

    md = render_md(r1)
    eq('case17 \u8f93\u51fa\u8868\u5934', md.startswith('# '), True)
    eq('case18 \u542b\u7981\u5fcc\u6e05\u5355', '\u5929\u7136\u77f3' in md and '\u4e9a\u514b\u529b' in md, True)
    eq('case19 \u542b\u5206\u9891\u6b21', '\u6392\u6c14\u6247' in md, True)
    eq('case20 \u542b\u7b49\u5f85\u65f6\u95f4', '\u7b49\u5f85' in md, True)
    js = json.loads(json.dumps(r1, ensure_ascii=False))
    eq('case21 JSON\u952e', sorted(js.keys()), ['mats', 'need_pro', 'reds', 'stains'])

    # \u5e26 BOM \u7684 JSON \u8f93\u5165\u5fc5\u987b\u80fd\u6b63\u786e\u89e3\u6790
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write('{"desc": "\u6c34\u9f99\u5934\u6709\u9508\u6591"}')
    got = read_input(tmp)
    os.remove(tmp)
    eq('case22 \u5e26BOM\u7684JSON\u9996\u952e', any(s['name'] == '\u9508\u6e0d' for s in analyse(got)['stains']), True)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 24\n\u8986\u76d6: \u6e05\u6d01\u5242\u56db\u79cd\u914d\u5bf9/\u516d\u7c7b\u6c61\u6e0d/\u5927\u7406\u77f3\u7981\u5fcc/'
               '\u4e9a\u514b\u529b\u94a2\u4e1d\u7403/\u9709\u6591/\u9508\u6e0d/\u94dd\u5236\u54c1/\u6cb9\u6c61/\u6392\u6c34\u8f6c\u4e13\u4e1a/BOM\u89e3\u6790')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u536b\u751f\u95f4\u6e05\u6d01\u4e0e\u9664\u57a2\u5224\u5b9a')
    ap.add_argument('--text', help='\u536b\u751f\u95f4\u6c61\u6e0d\u60c5\u51b5\u63cf\u8ff0')
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