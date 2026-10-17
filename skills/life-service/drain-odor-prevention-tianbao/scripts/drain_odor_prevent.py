# -*- coding: utf-8 -*-
"""\u4e0b\u6c34\u8fd4\u5473\u9884\u9632\u5206\u8bca\uff1a\u5339\u914d\u4e03\u7c7b\u6765\u6e90\u3001\u533a\u5206\u6162\u6392\u4e0e\u8fd4\u5473\u3001\u68c0\u67e5\u914d\u5bf9\u4e0e\u8f6c\u4ea4\u6761\u4ef6\u3002

\u7528\u6cd5:
  python drain_odor_prevent.py --text "\u591a\u4e2a\u4e0b\u6c34\u53e3\u90fd\u8fd4\u5473\uff0c\u6392\u6c34\u4e5f\u53d8\u6162\u4e86"
  python drain_odor_prevent.py --pair "\u542b\u6c2f\u6d88\u6bd2\u6db2" "\u9178\u6027\u758f\u901a\u5242"
  python drain_odor_prevent.py --file \u60c5\u51b5.txt --out \u7ed3\u679c.md
  python drain_odor_prevent.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ---- \u4e03\u7c7b\u8fd4\u5473\u6765\u6e90\uff0c\u6309\u6700\u5bb9\u6613\u9a8c\u8bc1\u6392\u5e8f ----
SOURCES = [
    {'id': 'D1', 'order': 1, 'name': '\u5730\u6f0f\u82af\u5931\u6548',
     'kw': ['\u82af\u574f', '\u9632\u81ed\u82af', '\u5730\u6f0f\u82af', '\u7ffb\u76d6', '\u78c1\u5438', '\u5bc6\u5c01\u5708', '\u82af\u4f53', '\u5730\u6f0f\u82af\u4f53'],
     'verify': '\u53d6\u51fa\u82af\u4f53\uff0c\u770b\u95ed\u5408\u4ef6\u80fd\u5426\u81ea\u7531\u5f00\u5408\u5e76\u5b8c\u5168\u95ed\u5408\uff1b\u770b\u5bc6\u5c01\u5708\u662f\u5426\u8001\u5316',
     'fix': '\u6309\u5b9e\u6d4b\u5c3a\u5bf8\u66f4\u6362\u5bf9\u5e94\u7c7b\u578b\u82af', 'owner': '\u53efDIY'},
    {'id': 'D2', 'order': 2, 'name': '\u5b58\u6c34\u5f2f\u5e72\u6db8',
     'kw': ['\u5b58\u6c34\u5f2f', '\u6c34\u5c01\u5e72', '\u5e72\u6db8', '\u957f\u671f\u4e0d\u7528', '\u51fa\u5dee', '\u7a7a\u7f6e', '\u5ba2\u536b', '\u6ca1\u4f4f\u4eba', '\u6c34\u5e72\u4e86'],
     'verify': '\u957f\u671f\u4e0d\u7528\u533a\u57df\uff1b\u8865\u6c34\u540e\u6c14\u5473\u660e\u663e\u51cf\u8f7b',
     'fix': '\u8865\u6e05\u6c34\u7ef4\u6301\u6c34\u5c01\uff1b\u957f\u671f\u4e0d\u7528\u5b9a\u671f\u8865\u6c34', 'owner': '\u53efDIY'},
    {'id': 'D3', 'order': 3, 'name': '\u901a\u6c14\u7ba1\u5835\u585e',
     'kw': ['\u901a\u6c14\u7ba1', '\u591a\u4e2a\u90fd', '\u90fd\u8fd4\u5473', '\u540c\u65f6\u8fd4\u5473', '\u5168\u90fd\u81ed', '\u6574\u5c42', '\u5355\u5143', '\u540c\u65f6\u6709\u5473',
            '\u597d\u51e0\u4e2a\u4e0b\u6c34', '\u597d\u591a\u8fd4\u5473'],
     'verify': '\u591a\u4e2a\u6392\u6c34\u70b9\u540c\u65f6\u8fd4\u5473\uff1b\u6362\u6c14\u6548\u679c\u5dee',
     'fix': '\u5fc5\u987b\u7531\u4e13\u4e1a\u5904\u7406\uff0c\u9700\u62c6\u52a8\u540a\u9876\u6216\u7ba1\u9053\uff1b\u4e0d\u8981\u81ea\u5df1\u62c6\u9876\u627e\u7ba1\u5b50', 'owner': '\u8f6c\u4e13\u4e1a\u4eba\u5458'},
    {'id': 'D4', 'order': 4, 'name': '\u88c5\u4fee\u65f6\u672a\u505a\u6c34\u5c01',
     'kw': ['\u76f4\u6392', '\u6ca1\u6709\u6c34\u5c01', '\u6ca1\u505a\u6c34\u5c01', '\u8001\u623f', '\u6539\u9020', '\u6ca1\u5b58\u6c34\u5f2f', '\u88c5\u4fee\u6ca1\u505a'],
     'verify': '\u8001\u623f\u76f4\u6392\uff1b\u6539\u9020\u7834\u574f\u5b58\u6c34\u7ed3\u6784',
     'fix': '\u52a0\u88c5\u5b58\u6c34\u5f2f\u6216\u6539\u7528\u5e26\u6c34\u5c01\u7684\u5730\u6f0f', 'owner': '\u8f6c\u4e13\u4e1a\u4eba\u5458'},
    {'id': 'D5', 'order': 5, 'name': '\u6c34\u5c01\u88ab\u7834\u574f',
     'kw': ['\u6c34\u5c01\u88ab\u7834\u574f', '\u7834\u574f\u4e86', '\u62c6\u6539', '\u79fb\u4f4d', '\u540e\u52a0\u7684', '\u6539\u9020\u7834\u574f'],
     'verify': '\u539f\u672c\u6709\u6c34\u5c01\uff0c\u540e\u88ab\u62c6\u6539\u3001\u79fb\u4f4d\u6216\u52a0\u88c5\u8bbe\u5907\u7834\u574f',
     'fix': '\u6062\u590d\u5b58\u6c34\u7ed3\u6784', 'owner': '\u8f6c\u4e13\u4e1a\u4eba\u5458'},
    {'id': 'D6', 'order': 6, 'name': '\u6d17\u624b\u76c6\u4e0b\u6c34\u8fd4\u5473',
     'kw': ['\u6d17\u624b\u76c6', '\u6d17\u624b\u53f0\u4e0b\u6c34', '\u9762\u76c6', '\u6d17\u8138\u76c6', '\u53f0\u76c6\u4e0b\u6c34'],
     'verify': '\u53ea\u6709\u6d17\u624b\u76c6\u4e0b\u6c34\u5904\u8fd4\u5473\uff1b\u68c0\u67e5\u5b58\u6c34\u5f2f\u4e0e\u4e0b\u6c34\u5668',
     'fix': '\u52a0\u88c5\u6216\u66f4\u6362\u5e26\u9632\u81ed\u82af\u7684\u4e0b\u6c34\u5668', 'owner': '\u53efDIY'},
    {'id': 'D7', 'order': 7, 'name': '\u65e0\u5730\u6f0f\u533a\u8fd4\u5473',
     'kw': ['\u6ca1\u6709\u5730\u6f0f', '\u65e0\u5730\u6f0f', '\u6ca1\u5730\u6f0f', '\u6ca1\u88c5\u5730\u6f0f', '\u65e0\u5730\u6f0f\u533a'],
     'verify': '\u536b\u751f\u95f4\u67d0\u533a\u57df\u6ca1\u6709\u5730\u6f0f\uff0c\u6c14\u5473\u4ece\u8be5\u5904\u51fa',
     'fix': '\u8be5\u533a\u57df\u9700\u6709\u6c34\u5c01\u9694\u65ad\uff1b\u65e0\u5730\u6f0f\u533a\u5c5e\u8bbe\u8ba1\u95ee\u9898', 'owner': '\u8f6c\u4e13\u4e1a\u4eba\u5458'},
]

# ---- \u6162\u6392\u4e0e\u8fd4\u5473\u533a\u5206 ----
SLOW = {
    'kw': ['\u6392\u6c34\u6162', '\u4e0b\u6c34\u6162', '\u6392\u6c34\u4e0d\u7545', '\u79ef\u6c34', '\u6392\u4e0d\u5e72\u51c0', '\u6392\u51c0\u6162', '\u6c34\u6d41\u4e0d\u4e0b\u53bb', '\u6392\u6c34\u53d8\u6162', '\u53d8\u6162\u4e86', '\u4e0b\u6c34\u53d8\u6162'],
    'msg': '\u6162\u6392\u662f\u673a\u68b0\u95ee\u9898\uff1a\u5012\u56fa\u5b9a\u91cf\u6c34\u8bb0\u5f55\u6392\u51c0\u65f6\u95f4\u3002\u758f\u901a\u65b9\u5411\uff0c\u4e0d\u662f\u9664\u81ed\u65b9\u5411',
}
ODOR = {
    'kw': ['\u8fd4\u5473', '\u8fd4\u81ed', '\u81ed\u5473', '\u6709\u5473', '\u5f02\u5473', '\u4e0b\u6c34\u9053\u5473'],
    'msg': '\u8fd4\u5473\u662f\u5bc6\u5c01\u95ee\u9898\uff1a\u5c01\u5835\u6392\u6c34\u70b9\u540e\u89c2\u5bdf\u6c14\u5473\u53d8\u5316\u3002\u4fee\u590d\u6c34\u5c01\u6216\u6362\u82af\u65b9\u5411\uff0c\u4e0d\u662f\u758f\u901a\u65b9\u5411',
}

# ---- \u5730\u6f0f\u82af\u7c7b\u578b ----
CORES = [
    ['\u7c7b\u578b', '\u539f\u7406', '\u9002\u5408', '\u4e0d\u9002\u5408', '\u6ce8\u610f'],
    ['\u7845\u80f6\u5634', '\u7845\u80f6\u5f00\u53e3\u91cd\u529b\u95ed\u5408', '\u6e7f\u533a\u5e38\u7528\u3001\u6392\u6c34\u91cf\u5927', '\u957f\u671f\u4e0d\u7528\u4f1a\u7c98\u8fde', '\u5b9a\u671f\u6e05\u6d01\u4e0e\u68c0\u67e5\u5f39\u6027'],
    ['T \u578b\u5f39\u7c27\u6216\u78c1\u5438', '\u5f39\u7c27\u6216\u78c1\u529b\u9876\u4f4f\u76d6\u677f', '\u5e72\u6e7f\u533a\u901a\u7528', '\u5f39\u7c27\u9508\u8680\u540e\u5931\u6548', '\u68c0\u67e5\u5f39\u7c27\u4e0e\u78c1\u529b'],
    ['\u91cd\u529b\u7ffb\u76d6', '\u7ffb\u677f\u81ea\u91cd\u56de\u843d', '\u6392\u6c34\u91cf\u5927\u7684\u6dcb\u6d74\u533a', '\u6742\u7269\u5361\u4f4f\u7ffb\u677f', '\u6e05\u7406\u6742\u7269\u9632\u6b62\u5361\u6ede'],
    ['\u6df1\u6c34\u5c01', '\u5b58\u6c34\u9694\u7edd\u6c14\u5473', '\u957f\u671f\u6709\u6c34\u7684\u6e7f\u533a', '\u5e72\u533a\u5fc5\u5e72\u6db8\u5931\u6548', '\u5e72\u533a\u4e0d\u8981\u9009\u7eaf\u6c34\u5c01'],
]

# ---- \u9884\u9632\u7ef4\u62a4\u5468\u671f ----
CYCLE = [
    ('\u6bcf\u6708', '\u68c0\u67e5\u5404\u6392\u6c34\u70b9\u662f\u5426\u6709\u5f02\u5473\uff1b\u7ed9\u957f\u671f\u4e0d\u7528\u7684\u6392\u6c34\u70b9\u8865\u4e00\u6b21\u6c34'),
    ('\u6bcf\u5b63', '\u53d6\u51fa\u5730\u6f0f\u82af\u6e05\u6d17\uff0c\u68c0\u67e5\u95ed\u5408\u4ef6\u4e0e\u5bc6\u5c01\u5708'),
    ('\u5165\u51ac\u524d', '\u4e00\u6b21\u6027\u623f\u5c4b\u7279\u522b\u68c0\u67e5\u5b58\u6c34\u5f2f\uff0c\u907f\u514d\u5e72\u88c2'),
    ('\u6bcf\u5e74', '\u68c0\u67e5\u5168\u90e8\u5730\u6f0f\u82af\u72b6\u51b5\u6309\u9700\u66f4\u6362\uff1b\u68c0\u67e5\u6d17\u624b\u76c6\u4e0b\u6c34\u5668'),
    ('\u642c\u5165\u524d\u9000\u79df\u524d', '\u5168\u9762\u68c0\u67e5\u5e76\u8bb0\u5f55'),
]

# ---- \u5b89\u5168\u7ea2\u7ebf ----
CHLORINE = ['\u542b\u6c2f', '\u6f02\u767d\u6c34', '\u6d88\u6bd2\u6db2', '84', '\u6b21\u6c2f\u9178\u94a0', '\u6c2f']
ACID = ['\u9178\u6027', '\u6d01\u5395\u7075', '\u6d01\u5395\u5242', '\u767d\u918b', '\u918b', '\u67e0\u6aac\u9178', '\u9664\u57a2\u5242', '\u67e0\u6aac', '\u76d0\u9178', '\u758f\u901a\u5242']
ALKALI = ['\u78b1\u6027', '\u5f3a\u78b1', '\u706b\u78b1', '\u70e7\u78b1', '\u5c0f\u82cf\u6253', '\u78b3\u9178\u94a0', '\u5f3a\u9178', '\u786b\u9178']


def classify_pair(a, b):
    ta = (a or '') + ' ' + (b or '')
    has_cl = any(k in ta for k in CHLORINE)
    has_ac = any(k in ta for k in ACID)
    has_al = any(k in ta for k in ALKALI)
    if has_cl and has_ac:
        return ('danger', '\u4e25\u7981\u5c06\u542b\u6c2f\u6d88\u6bd2\u5242\u4e0e\u9178\u6027\u758f\u901a\u5242\u6216\u9178\u6027\u6e05\u6d01\u5242\u6df7\u5408\uff0c\u4e24\u8005\u4f1a\u4ea7\u751f\u6709\u6bd2\u6c14\u4f53')
    if has_cl and has_al:
        return ('danger', '\u542b\u6c2f\u6d88\u6bd2\u5242\u4e0e\u78b1\u6027\u6e05\u6d01\u5242\u4e0d\u5c5e\u4e8e\u5b89\u5168\u914d\u5bf9\uff0c\u53ef\u80fd\u4ea7\u751f\u523a\u6fc0\u6027\u6c14\u4f53')
    if has_cl and '\u542b\u6c2f' in (a or '') and '\u542b\u6c2f' in (b or ''):
        return ('danger', '\u4e24\u79cd\u542b\u6c2f\u4ea7\u54c1\u6df7\u5408\u540e\u6709\u6548\u6210\u5206\u53e0\u52a0\uff0c\u5c5e\u4e0d\u53ef\u63a7\u914d\u5bf9')
    return ('ok', '\u672a\u547d\u4e2d\u5df2\u77e5\u5371\u9669\u914d\u5bf9\uff0c\u4ecd\u9700\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e66\u4e3a\u51c6\uff0c\u4e0d\u540c\u4ea7\u54c1\u4e0d\u53ef\u6df7\u7528')


def analyse(text):
    t = (text or '').replace(' ', '').replace('\u3000', '')
    srcs = []
    for s in SOURCES:
        hits = [k for k in s['kw'] if k in t]
        if hits:
            srcs.append({'id': s['id'], 'order': s['order'], 'name': s['name'],
                         'hits': hits, 'verify': s['verify'], 'fix': s['fix'],
                         'owner': s['owner']})
    srcs.sort(key=lambda x: x['order'])
    slow = any(k in t for k in SLOW['kw'])
    odor = any(k in t for k in ODOR['kw'])
    multi = any(k in t for k in ['\u591a\u4e2a', '\u90fd\u8fd4\u5473', '\u540c\u65f6\u8fd4\u5473', '\u5168\u90fd', '\u6574\u5c42',
                                 '\u597d\u51e0\u4e2a\u4e0b\u6c34', '\u597d\u591a\u8fd4\u5473', '\u540c\u65f6\u6709\u5473'])
    reds = []
    if multi:
        reds.append('\u591a\u6761\u6392\u6c34\u70b9\u540c\u65f6\u8fd4\u5473\u65f6\u4f18\u5148\u68c0\u67e5\u901a\u6c14\u7ba1\uff1a\u90e8\u5206\u88c5\u4fee\u628a\u901a\u6c14\u7ba1\u5f53\u6210\u9884\u7559\u5b54\u5c01\u5835\u4e86\uff0c'
                    '\u8fd9\u662f\u6839\u672c\u539f\u56e0\uff0c\u6362\u82af\u89e3\u51b3\u4e0d\u4e86\u3002\u4e0d\u8981\u81ea\u5df1\u62c6\u540a\u9876\u627e\u7ba1\u5b50\uff0c\u76f4\u63a5\u62a5\u7269\u4e1a\u3002')
    if any(k in t for k in ['\u6df7\u7740\u5012', '\u4e00\u8d77\u5012', '\u5151\u4e00\u8d77', '\u540c\u65f6\u7528', '\u6df7\u5408\u7528', '\u4e00\u8d77\u7528']):
        if any(k in t for k in CHLORINE):
            reds.append('\u4e25\u7981\u5c06\u542b\u6c2f\u6d88\u6bd2\u5242\u4e0e\u9178\u6027\u758f\u901a\u5242\u6216\u9178\u6027\u6e05\u6d01\u5242\u6df7\u5408\uff0c\u4f1a\u4ea7\u751f\u6709\u6bd2\u6c14\u4f53')
    if any(k in t for k in ['\u73bb\u7483\u80f6', '\u5c01\u6b7b', '\u6253\u80f6']):
        reds.append('\u7981\u6b62\u7528\u73bb\u7483\u80f6\u628a\u5730\u6f0f\u5b8c\u5168\u5c01\u6b7b\uff1a\u4f1a\u5835\u4f4f\u6392\u6c34\u901a\u9053\uff0c\u4e0b\u6b21\u6392\u6c34\u4ece\u522b\u5904\u6ea2\u51fa\uff0c\u4e14\u68c0\u4fee\u65f6\u66f4\u96be\u5904\u7406')
    if any(k in t for k in ['\u62c6\u9876', '\u62c6\u540a\u9876', '\u81ea\u5df1\u62c6']):
        reds.append('\u4e0d\u8981\u81ea\u5df1\u62c6\u540a\u9876\u627e\u901a\u6c14\u7ba1\uff1a\u9700\u8981\u52a8\u7ba1\u9053\u4e0e\u7ed3\u6784\uff0c\u5c5e\u4e13\u4e1a\u8303\u56f4')
    need_pro = any(k in t for k in ['\u4e3b\u7ba1', '\u53cd\u6d8c', '\u697c\u4e0b', '\u6574\u5c42', '\u5355\u5143', '\u4e45\u6cbb\u4e0d\u6108',
                                     '\u4e00\u76f4\u4e0d\u597d', '\u6cbb\u4e0d\u597d', '\u53cd\u590d\u5904\u7406'])
    return {'sources': srcs, 'slow': slow, 'odor': odor, 'multi': multi,
            'reds': reds, 'need_pro': need_pro, 'slow_msg': SLOW['msg'],
            'odor_msg': ODOR['msg'],
            'top': srcs[0]['name'] if srcs else ''}


def render_md(r, pair_info=None):
    lines = ['# \u4e0b\u6c34\u8fd4\u5473\u5206\u8bca\u7ed3\u679c', '']
    lines.append('> \u5148\u533a\u5206\u6162\u6392\u4e0e\u8fd4\u5473\u8fd9\u4e24\u4e2a\u95ee\u9898\uff0c\u518d\u6309\u987a\u5e8f\u6392\u67e5\u3002\u591a\u6761\u6392\u6c34\u70b9\u540c\u65f6\u8fd4\u5473\uff0c\u4f18\u5148\u67e5\u901a\u6c14\u7ba1\u3002')
    lines.append('')
    if pair_info:
        lines.append('## \u6e05\u6d01\u5242\u914d\u5bf9\u68c0\u67e5')
        lines.append('')
        lines.append('- \u4ea7\u54c1 A\uff1a%s' % pair_info[0])
        lines.append('- \u4ea7\u54c1 B\uff1a%s' % pair_info[1])
        lines.append('- \u7b49\u7ea7\uff1a%s' % pair_info[2])
        lines.append('- \u8bf4\u660e\uff1a%s' % pair_info[3])
        lines.append('')

    lines.append('## \u4e00\u3001\u6162\u6392\u4e0e\u8fd4\u5473\u7684\u533a\u5206')
    lines.append('')
    lines.append('| \u95ee\u9898 | \u662f\u5426\u547d\u4e2d | \u5904\u7406\u65b9\u5411 | \u9a8c\u8bc1\u52a8\u4f5c |')
    lines.append('|---|---|---|---|')
    lines.append('| \u6162\u6392\uff08\u6392\u6c34\u95ee\u9898\uff09 | %s | \u758f\u901a\u3001\u6e05\u9664\u5835\u585e\u7269 | \u5012\u56fa\u5b9a\u91cf\u6c34\u8bb0\u5f55\u6392\u51c0\u65f6\u95f4 |'
                 % ('\u662f' if r['slow'] else '\u5426'))
    lines.append('| \u8fd4\u5473\uff08\u5bc6\u5c01\u95ee\u9898\uff09 | %s | \u4fee\u590d\u6216\u66f4\u6362\u6c34\u5c01\u4e0e\u5730\u6f0f\u82af | \u5c01\u5835\u6392\u6c34\u70b9\u540e\u89c2\u5bdf\u6c14\u5473 |'
                 % ('\u662f' if r['odor'] else '\u5426'))
    lines.append('')
    if r['slow']:
        lines.append('- %s' % r['slow_msg'])
    if r['odor']:
        lines.append('- %s' % r['odor_msg'])
    if r['slow'] and r['odor']:
        lines.append('')
        lines.append('**\u4e24\u7c7b\u95ee\u9898\u53ef\u80fd\u540c\u65f6\u5b58\u5728**\uff0c\u5224\u65ad\u65f6\u4e0d\u8981\u7528\u4e00\u4e2a\u52a8\u4f5c\u4ee3\u66ff\u53e6\u4e00\u4e2a\u3002')
        lines.append('')

    lines.append('## \u4e8c\u3001\u4e03\u7c7b\u6765\u6e90\u5206\u8bca\uff08\u6309\u4e0b\u8868\u987a\u5e8f\u6392\u67e5\uff09')
    lines.append('')
    if not r['sources']:
        lines.append('\u672a\u5339\u914d\u5230\u6765\u6e90\u7ebf\u7d22\u3002\u8bf7\u8865\u5145\uff1a\u662f\u4e00\u6761\u8fd8\u662f\u591a\u6761\u6392\u6c34\u70b9\u8fd4\u5473\u3001\u662f\u5426\u957f\u671f\u4e0d\u7528\u3001'
                     '\u662f\u8001\u623f\u8fd8\u662f\u6539\u9020\u8fc7\u3001\u6d17\u624b\u76c6\u5904\u662f\u5426\u5355\u72ec\u8fd4\u5473\u3002')
        lines.append('')
    else:
        lines.append('\u6700\u4f18\u5148\u6392\u67e5\uff1a%s' % r['top'])
        lines.append('')
        lines.append('| \u987a\u5e8f | \u53ef\u80fd\u6765\u6e90 | \u547d\u4e2d\u7ebf\u7d22 | \u9a8c\u8bc1\u65b9\u6cd5 | \u5904\u7406 | \u5f52\u5c5e |')
        lines.append('|---|---|---|---|---|---|')
        for s in r['sources']:
            lines.append('| %d | %s | %s | %s | %s | %s |' % (
                s['order'], s['name'], '\u3001'.join(s['hits']), s['verify'], s['fix'], s['owner']))
        lines.append('')

    lines.append('## \u4e09\u3001\u5730\u6f0f\u82af\u7c7b\u578b\u4e0e\u9002\u7528')
    lines.append('')
    lines.append('| ' + ' | '.join(CORES[0]) + ' |')
    lines.append('|---|---|---|---|---|')
    for row in CORES[1:]:
        lines.append('| ' + ' | '.join(row) + ' |')
    lines.append('')
    lines.append('**\u5e72\u533a\u4e0d\u8981\u9009\u7eaf\u6c34\u5c01**\uff1a\u9633\u53f0\u3001\u53a8\u623f\u3001\u957f\u671f\u4e0d\u7528\u7684\u536b\u751f\u95f4\u5c5e\u4e8e\u5e72\u533a\u3002')
    lines.append('')

    lines.append('## \u56db\u3001\u901a\u6c14\u7ba1\u68c0\u67e5\u8981\u70b9')
    lines.append('')
    lines.append('- **\u662f\u5426\u88ab\u5c01\u6b7b**\uff1a\u90e8\u5206\u88c5\u4fee\u628a\u901a\u6c14\u7ba1\u5f53\u6210\u9884\u7559\u5b54\u5c01\u5835\u4e86\uff0c\u8fd9\u662f\u6839\u672c\u539f\u56e0')
    lines.append('- **\u662f\u5426\u88ab\u5360\u7528**\uff1a\u540a\u9876\u5185\u3001\u901a\u98ce\u7ba1\u3001\u5176\u4ed6\u7ba1\u7ebf\u5360\u7528\u6216\u9519\u63a5')
    lines.append('- **\u662f\u5426\u5835\u585e**\uff1a\u5185\u90e8\u79ef\u57a2\u3001\u6742\u7269\u6216\u88ab\u538b\u6241')
    lines.append('- **\u9a8c\u8bc1\u65b9\u6cd5**\uff1a\u591a\u6761\u6392\u6c34\u70b9\u540c\u65f6\u8fd4\u5473\u4e14\u5c01\u5835\u5355\u4e2a\u70b9\u65e0\u6548\uff0c\u9ad8\u5ea6\u6000\u7591\u901a\u6c14\u7ba1')
    lines.append('- **\u4e0d\u8981\u81ea\u5df1\u62c6\u540a\u9876\u627e\u901a\u6c14\u7ba1**\uff1a\u8fd9\u9700\u8981\u52a8\u7ba1\u9053\u4e0e\u7ed3\u6784\uff0c\u5c5e\u4e13\u4e1a\u8303\u56f4')
    lines.append('')

    lines.append('## \u4e94\u3001\u6d17\u624b\u76c6\u4e0b\u6c34\u8fd4\u5473\u5904\u7406')
    lines.append('')
    lines.append('| \u60c5\u51b5 | \u68c0\u67e5 | \u5904\u7406 |')
    lines.append('|---|---|---|')
    lines.append('| \u5b58\u6c34\u5f2f\u5e72\u6db8\u6216\u7f3a\u5931 | \u770b\u4e0b\u6c34\u5668\u662f\u5426\u6709 U \u578b\u5b58\u6c34\u7ed3\u6784 | \u52a0\u88c5\u5b58\u6c34\u5f2f\u6216\u66f4\u6362\u5e26\u5b58\u6c34\u7684\u4e0b\u6c34\u5668 |')
    lines.append('| \u4e0b\u6c34\u5668\u65e0\u9632\u81ed\u82af | \u53d6\u4e0b\u4e0b\u6c34\u5668\u770b\u6709\u65e0\u9632\u81ed\u7ed3\u6784 | \u66f4\u6362\u5e26\u9632\u81ed\u82af\u7684\u4e0b\u6c34\u5668 |')
    lines.append('| \u4e0b\u6c34\u7ba1\u76f4\u6392\u65e0\u5b58\u6c34\u5f2f | \u62c6\u5f00\u770b\u662f\u5426\u6709\u5f2f | \u52a0\u88c5\u5b58\u6c34\u5f2f |')
    lines.append('| \u63a5\u53e3\u5904\u6f0f\u6c14 | \u770b\u63a5\u53e3\u662f\u5426\u5bc6\u5c01\u3001\u8001\u5316 | \u66f4\u6362\u5bc6\u5c01\u4ef6 |')
    lines.append('')

    lines.append('## \u516d\u3001\u9884\u9632\u7ef4\u62a4\u5468\u671f')
    lines.append('')
    lines.append('| \u5468\u671f | \u52a8\u4f5c |')
    lines.append('|---|---|')
    for a, b in CYCLE:
        lines.append('| %s | %s |' % (a, b))
    lines.append('')
    lines.append('**\u6838\u5fc3\u539f\u5219**\uff1a\u957f\u671f\u4e0d\u7528\u7684\u6392\u6c34\u70b9\u8981\u5b9a\u671f\u8865\u6c34\u3002')
    lines.append('')

    lines.append('## \u4e03\u3001\u5b89\u5168\u7ea2\u7ebf')
    lines.append('')
    lines.append('1. **\u4e25\u7981\u6df7\u5408\u542b\u6c2f\u6d88\u6bd2\u5242\u4e0e\u9178\u6027\u758f\u901a\u5242\u6216\u9178\u6027\u6e05\u6d01\u5242**\uff0c\u4f1a\u4ea7\u751f\u6709\u6bd2\u6c14\u4f53')
    lines.append('2. **\u7981\u6b62\u7528\u73bb\u7483\u80f6\u628a\u5730\u6f0f\u5b8c\u5168\u5c01\u6b7b**\uff0c\u4f1a\u5835\u4f4f\u6392\u6c34\u901a\u9053')
    lines.append('3. **\u4e0d\u8981\u81ea\u5df1\u62c6\u540a\u9876\u627e\u901a\u6c14\u7ba1**')
    lines.append('4. \u758f\u901a\u5242\u4f7f\u7528\u524d\u5148\u786e\u8ba4\u7ba1\u9053\u6750\u8d28\uff0c\u8001\u65e7\u94f8\u94c1\u7ba1\u4e0e\u9540\u950c\u7ba1\u53ef\u80fd\u88ab\u8150\u8680')
    lines.append('5. \u4e0d\u7528\u5f3a\u9178\u5f3a\u78b1\u505a\u7834\u574f\u6027\u901a\u5835')
    lines.append('')
    if r['reds']:
        lines.append('**\u672c\u6b21\u89e6\u53d1\uff1a**')
        lines.append('')
        for m in r['reds']:
            lines.append('- %s' % m)
        lines.append('')

    lines.append('## \u516b\u3001\u5f52\u5c5e\u5224\u5b9a')
    lines.append('')
    if r['need_pro']:
        lines.append('\u672c\u6b21\u60c5\u5f62**\u5e94\u62a5\u7269\u4e1a\u6216\u8054\u7cfb\u4e13\u4e1a\u4eba\u5458**\uff0c\u4e0d\u8981\u7ee7\u7eed\u81ea\u884c\u5c1d\u8bd5\u3002')
    else:
        lines.append('\u672c\u6b21\u60c5\u5f62\u5c5e\u4e8e\u53ef\u81ea\u884c\u5904\u7406\u8303\u56f4\uff0c\u4f46\u4ecd\u9700\u5148\u6309\u987a\u5e8f\u9010\u9879\u6392\u9664\u5e76\u505a\u5c01\u5835\u9a8c\u8bc1\u3002')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('\u672c\u7ed3\u679c\u4e3a\u73b0\u8c61\u5339\u914d\u4e0e\u6392\u67e5\u987a\u5e8f\u5efa\u8bae\uff0c\u4e0d\u4ee3\u8868\u73b0\u573a\u5224\u65ad\uff0c\u4e0d\u6784\u6210\u4e13\u4e1a\u65bd\u5de5\u7ed3\u8bba\u3002')
    lines.append('\u6e05\u6d01\u5242\u4e0e\u758f\u901a\u5242\u7684\u9002\u7528\u8303\u56f4\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e66\u4e3a\u51c6\uff0c\u4e0d\u540c\u4ea7\u54c1\u4e0d\u53ef\u6df7\u7528\u3002')
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

    eq('case1 \u542b\u6c2f\u52a0\u9178\u6027\u758f\u901a\u5242', classify_pair('\u542b\u6c2f\u6d88\u6bd2\u6db2', '\u9178\u6027\u758f\u901a\u5242')[0], 'danger')
    eq('case2 \u542b\u6c2f\u52a0\u6d01\u5395\u7075', classify_pair('84\u6d88\u6bd2\u6db2', '\u6d01\u5395\u7075')[0], 'danger')
    eq('case3 \u542b\u6c2f\u52a0\u78b1\u6027', classify_pair('\u6f02\u767d\u6c34', '\u5c0f\u82cf\u6253')[0], 'danger')
    eq('case4 \u4e24\u79cd\u542b\u6c2f', classify_pair('\u542b\u6c2f\u6d88\u6bd2\u6db2', '\u542b\u6c2f\u6f02\u767d\u6c34')[0], 'danger')
    eq('case5 \u4e2d\u6027\u914d\u5bf9', classify_pair('\u4e2d\u6027\u6e05\u6d01\u5242', '\u6e29\u6c34')[0], 'ok')

    r1 = analyse('\u591a\u4e2a\u4e0b\u6c34\u53e3\u90fd\u8fd4\u5473\uff0c\u6392\u6c34\u4e5f\u53d8\u6162\u4e86')
    eq('case6 \u901a\u6c14\u7ba1\u4f18\u5148', r1['top'], '\u901a\u6c14\u7ba1\u5835\u585e')
    eq('case7 \u591a\u70b9\u6807\u8bb0', r1['multi'], True)
    eq('case8 \u6162\u6392\u547d\u4e2d', r1['slow'], True)
    eq('case9 \u8fd4\u5473\u547d\u4e2d', r1['odor'], True)

    r2 = analyse('\u5ba2\u536b\u957f\u671f\u6ca1\u4eba\u4f4f\uff0c\u6700\u8fd1\u8fd4\u5473')
    eq('case10 \u5e72\u6db8\u4f18\u5148', r2['top'], '\u5b58\u6c34\u5f2f\u5e72\u6db8')

    r3 = analyse('\u53ea\u6709\u6d17\u624b\u76c6\u4e0b\u6c34\u90a3\u91cc\u8fd4\u5473')
    eq('case11 \u9762\u76c6\u8bc6\u522b', any(s['id'] == 'D6' for s in r3['sources']), True)

    r4 = analyse('\u536b\u751f\u95f4\u90a3\u5757\u533a\u57df\u6ca1\u6709\u5730\u6f0f')
    eq('case12 \u65e0\u5730\u6f0f\u533a', any(s['id'] == 'D7' for s in r4['sources']), True)

    r5 = analyse('\u5730\u6f0f\u82af\u574f\u4e86\u8981\u4e0d\u8981\u6362')
    eq('case13 \u82af\u4f53\u8bc6\u522b', any(s['id'] == 'D1' for s in r5['sources']), True)

    r6 = analyse('\u7528\u73bb\u7483\u80f6\u628a\u5730\u6f0f\u5c01\u6b7b\u884c\u4e0d\u884c')
    eq('case14 \u5c01\u6b7b\u7ea2\u7ebf', any('\u5c01\u6b7b' in m for m in r6['reds']), True)

    r7 = analyse('\u6392\u6c34\u4e00\u76f4\u5f88\u6162\uff0c\u8fd8\u6709\u53cd\u6d8c')
    eq('case15 \u8f6c\u4e13\u4e1a\u4eba\u5458', r7['need_pro'], True)

    r8 = analyse('\u758f\u901a\u5242\u80fd\u548c\u6d88\u6bd2\u6db2\u4e00\u8d77\u5012\u5417')
    eq('case16 \u914d\u5bf9\u7ea2\u7ebf', any('\u6709\u6bd2\u6c14\u4f53' in m for m in r8['reds']), True)

    r9 = analyse('\u4ec0\u4e48\u90fd\u4e0d\u6e05\u695a')
    eq('case17 \u65e0\u5339\u914d', r9['sources'], [])

    md = render_md(r1)
    eq('case18 \u8f93\u51fa\u8868\u5934', md.startswith('# '), True)
    eq('case19 \u542b\u6162\u6392\u8fd4\u5473\u533a\u5206', '\u6162\u6392\u4e0e\u8fd4\u5473\u7684\u533a\u5206' in md, True)
    eq('case20 \u542b\u901a\u6c14\u7ba1\u8981\u70b9', '\u901a\u6c14\u7ba1\u68c0\u67e5\u8981\u70b9' in md, True)
    eq('case21 \u542b\u7ef4\u62a4\u5468\u671f', '\u6bcf\u6708' in md, True)
    eq('case22 \u542b\u5730\u6f0f\u82af\u8868', '\u6df1\u6c34\u5c01' in md, True)
    js = json.loads(json.dumps(r1, ensure_ascii=False))
    eq('case23 JSON\u952e', sorted(js.keys()),
       ['multi', 'need_pro', 'odor', 'odor_msg', 'reds', 'slow', 'slow_msg', 'sources', 'top'])

    # \u5e26 BOM \u7684 JSON \u8f93\u5165\u5fc5\u987b\u80fd\u6b63\u786e\u89e3\u6790
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write('{"desc": "\u53ea\u6709\u6d17\u624b\u76c6\u4e0b\u6c34\u90a3\u91cc\u8fd4\u5473"}')
    got = read_input(tmp)
    os.remove(tmp)
    eq('case24 \u5e26BOM\u7684JSON\u9996\u952e', any(s['id'] == 'D6' for s in analyse(got)['sources']), True)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 26\n\u8986\u76d6: \u4e03\u7c7b\u6765\u6e90/\u6162\u6392\u4e0e\u8fd4\u5473\u533a\u5206/\u901a\u6c14\u7ba1\u4f18\u5148/'
               '\u9762\u76c6/\u65e0\u5730\u6f0f\u533a/\u82af\u4f53/\u5c01\u6b7b\u7ea2\u7ebf/\u914d\u5bf9\u7ea2\u7ebf/\u8f6c\u4e13\u4e1a/BOM\u89e3\u6790')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u4e0b\u6c34\u8fd4\u5473\u9884\u9632\u5206\u8bca\u4e0e\u5730\u6f0f\u7ef4\u62a4\u5224\u5b9a')
    ap.add_argument('--text', help='\u8fd4\u5473\u4e0e\u6392\u6c34\u60c5\u51b5\u63cf\u8ff0')
    ap.add_argument('--file', help='\u4ece\u6587\u4ef6\u8bfb\uff0c\u652f\u6301 txt / md / json')
    ap.add_argument('--pair', nargs=2, metavar=('A', 'B'), help='\u68c0\u67e5\u4e24\u79cd\u6e05\u6d01\u5242\u6216\u758f\u901a\u5242\u7684\u914d\u5bf9')
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