# -*- coding: utf-8 -*-
"""\u4e73\u80f6\u6f06\u9009\u578b\u4e0e\u65bd\u5de5\u6838\u67e5\uff1a\u5931\u8d25\u539f\u56e0\u5339\u914d\u3001\u6750\u6599\u5efa\u8bae\u3001\u6307\u6807\u53e3\u5f84\u63d0\u793a\u4e0e\u5b89\u5168\u7ea2\u7ebf\u3002

\u7528\u6cd5:
  python paint_check.py --text "\u5899\u9762\u8d77\u76ae\u4e86\uff0c\u5b55\u5987\u5728\u5bb6"
  python paint_check.py --file \u60c5\u51b5.txt --out \u7ed3\u679c.md
  python paint_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ---- \u56db\u7c7b\u6d82\u6599\u7279\u6027 ----
PAINT_TYPES = [
    {'id': 'T1', 'name': '\u4e73\u80f6\u6f06',
     'kw': ['\u4e73\u80f6\u6f06', '\u5899\u6f06', '\u4e73\u80f6', '\u666e\u901a\u6f06'],
     'pro': '\u65bd\u5de5\u5feb\u3001\u6210\u672c\u4f4e\u3001\u4fee\u8865\u5bb9\u6613\u3001\u989c\u8272\u9009\u62e9\u591a',
     'con': '\u8d28\u611f\u5355\u4e00\uff0c\u906e\u76d6\u529b\u53d7\u57fa\u5c42\u5f71\u54cd\u5927',
     'fit': '\u5927\u9762\u79ef\u5899\u9762\u4e0e\u9876\u9762'},
    {'id': 'T2', 'name': '\u827a\u672f\u6f06',
     'kw': ['\u827a\u672f\u6f06', '\u808c\u7406', '\u8d28\u611f\u6f06', '\u522e\u6d82'],
     'pro': '\u8d28\u611f\u5f3a\u3001\u88c5\u9970\u6027\u9ad8\u3001\u8010\u810f\u6027\u8f83\u597d',
     'con': '\u6210\u672c\u9ad8\u3001\u624b\u6cd5\u8981\u6c42\u9ad8\u3001\u4fee\u8865\u56f0\u96be\uff0c\u5c40\u90e8\u8865\u8272\u75d5\u8ff9\u660e\u663e',
     'fit': '\u80cc\u666f\u5899\u3001\u5c40\u90e8\u9020\u578b\u5899'},
    {'id': 'T3', 'name': '\u7845\u85fb\u6ce5',
     'kw': ['\u7845\u85fb\u6ce5', '\u7845\u85fb'],
     'pro': '\u900f\u6c14\u3001\u8c03\u6e7f\u3001\u65e0\u660e\u663e\u5149\u6cfd',
     'con': '\u6015\u6c34\u3001\u8010\u64e6\u6d17\u5dee\u3001\u9047\u6c34\u6613\u7c89\u5316',
     'fit': '\u5367\u5ba4\u3001\u8ffd\u6c42\u8d28\u611f\u4e14\u4e0d\u5e38\u64e6\u62ed\u7684\u5899\u9762'},
    {'id': 'T4', 'name': '\u8d1d\u58f3\u7c89',
     'kw': ['\u8d1d\u58f3\u7c89', '\u8d1d\u58f3'],
     'pro': '\u8d28\u611f\u7ec6\u817b\u3001\u900f\u6c14',
     'con': '\u8010\u64e6\u6d17\u5dee\u3001\u6015\u6c34\u3001\u90e8\u5206\u4ea7\u54c1\u6613\u6389\u7c89',
     'fit': '\u5c40\u90e8\u9020\u578b\u3001\u513f\u7ae5\u623f\uff08\u9700\u786e\u8ba4\u4ea7\u54c1\u8bf4\u660e\uff09'},
]

# ---- \u5e38\u89c1\u5931\u8d25\u73b0\u8c61\u4e0e\u539f\u56e0 ----
FAILURES = [
    {'id': 'F1', 'name': '\u8d77\u76ae',
     'kw': ['\u8d77\u76ae', '\u7fd8\u76ae', '\u8131\u76ae', '\u5265\u843d'],
     'cause': '\u57fa\u5c42\u4e0d\u7262\u3001\u6709\u6e17\u6c34\u3001\u65e7\u6f06\u7c89\u5316\u672a\u94f2\u9664\u3001\u5e72\u71e5\u4e0d\u8db3',
     'duty': '\u89c6\u60c5\u51b5\u5c5e\u57fa\u5c42\u5904\u7406\u6216\u65bd\u5de5\u65b9\u8d23\u4efb'},
    {'id': 'F2', 'name': '\u5f00\u88c2',
     'kw': ['\u5f00\u88c2', '\u88c2\u7f1d', '\u88c2\u7eb9'],
     'cause': '\u57fa\u5c42\u88c2\u7f1d\u672a\u5904\u7406\u3001\u6750\u6599\u6536\u7f29\u3001\u5e72\u71e5\u8fc7\u5feb',
     'duty': '\u88c2\u7f1d\u672a\u5904\u7406\u5c5e\u65bd\u5de5\u65b9\u8d23\u4efb'},
    {'id': 'F3', 'name': '\u6d41\u6302',
     'kw': ['\u6d41\u6302', '\u6d41\u4e0b\u6765', '\u6302\u4e0b\u6765', '\u5237\u75d5'],
     'cause': '\u4e00\u6b21\u6d82\u5237\u8fc7\u539a\u6216\u672a\u6309\u8bf4\u660e\u4e66\u914d\u6bd4',
     'duty': '\u65bd\u5de5\u65b9\u8d23\u4efb'},
    {'id': 'F4', 'name': '\u900f\u5e95',
     'kw': ['\u900f\u5e95', '\u9732\u5e95', '\u5e95\u8272', '\u76d6\u4e0d\u4f4f'],
     'cause': '\u906e\u76d6\u529b\u4e0d\u8db3\u6216\u5e95\u8272\u4e0e\u9762\u8272\u5dee\u5f02\u5927\u3001\u672a\u6309\u8bf4\u660e\u4e66\u914d\u6bd4\u4f7f\u7528',
     'duty': '\u65bd\u5de5\u65b9\u6216\u9009\u578b\u95ee\u9898'},
    {'id': 'F5', 'name': '\u8272\u5dee',
     'kw': ['\u8272\u5dee', '\u989c\u8272\u4e0d\u4e00\u6837', '\u8272\u5757', '\u63a5\u832c'],
     'cause': '\u4e0d\u540c\u6279\u6b21\u6df7\u7528\u3001\u6d82\u5237\u4e0d\u5747\u3001\u5149\u7ebf\u4e0d\u540c',
     'duty': '\u6279\u6b21\u6df7\u7528\u5c5e\u65bd\u5de5\u65b9\uff1b\u540c\u6279\u53f7\u8f7b\u5fae\u8272\u5dee\u5c5e\u5e38\u89c1\u73b0\u8c61'},
    {'id': 'F6', 'name': '\u53d1\u82b1',
     'kw': ['\u53d1\u82b1', '\u4e0d\u5747\u5300', '\u6df1\u6d45\u4e0d\u4e00'],
     'cause': '\u6c34\u5206\u6216\u52a9\u5242\u5206\u5e03\u4e0d\u5747\u3001\u65bd\u5de5\u73af\u5883\u6e7f\u5ea6\u8fc7\u9ad8',
     'duty': '\u65bd\u5de5\u65b9\u8d23\u4efb'},
    {'id': 'F7', 'name': '\u6389\u7c89',
     'kw': ['\u6389\u7c89', '\u4e00\u64e6\u4e00\u624b\u767d', '\u7c89\u5316'],
     'cause': '\u57fa\u5c42\u7c89\u5316\u672a\u5904\u7406\u3001\u4ea7\u54c1\u9644\u7740\u8981\u6c42\u4e0d\u6ee1\u8db3',
     'duty': '\u57fa\u5c42\u95ee\u9898\u6216\u9009\u578b\u95ee\u9898'},
]

# ---- \u5b89\u5168\u7ea2\u7ebf\u4eba\u7fa4 ----
SAFETY = [
    {'id': 'R1', 'kw': ['\u5b55\u5987', '\u6000\u5b55', '\u5907\u5b55'],
     'msg': '\u5b55\u5987\u5e94\u907f\u514d\u63a5\u89e6\u6d82\u6599\u4e0e\u65bd\u5de5\u533a\u57df\uff1a\u65bd\u5de5\u671f\u95f4\u79bb\u5f00\u8be5\u623f\u95f4\uff0c\u5145\u5206\u901a\u98ce\u540e\u518d\u8fdb\u5165'},
    {'id': 'R2', 'kw': ['\u5a74\u513f', '\u5b9d\u5b9d', '\u5c0f\u5b69', '\u513f\u7ae5'],
     'msg': '\u6709\u5a74\u5e7c\u513f\u7684\u5bb6\u5ead\uff1a\u65bd\u5de5\u671f\u95f4\u4e0d\u5728\u8be5\u623f\u95f4\u6d3b\u52a8\uff0c\u5b8c\u5de5\u540e\u5145\u5206\u901a\u98ce\u518d\u8fdb\u5165'},
    {'id': 'R3', 'kw': ['\u8fc7\u654f', '\u54ee\u5598', '\u547c\u5438\u9053', '\u654f\u611f'],
     'msg': '\u547c\u5438\u9053\u654f\u611f\u8005\u4e0e\u54ee\u5598\u60a3\u8005\u4e0d\u53c2\u4e0e\u65bd\u5de5\uff1b\u65bd\u5de5\u671f\u95f4\u4e0d\u8fdb\u5165\u8be5\u623f\u95f4'},
    {'id': 'R4', 'kw': ['\u9ad8\u5904', '\u68af\u5b50', '\u9ad8\u5899', '\u7ad9\u6905\u5b50', '\u642d\u67b6\u5b50', '\u540a\u9876\u4f5c\u4e1a'],
     'msg': '\u9ad8\u5904\u4f5c\u4e1a\u5c5e\u4e8e\u4e13\u4e1a\u65bd\u5de5\u8303\u56f4\uff0c\u8bf7\u52ff\u81ea\u884c\u642d\u68af\u6216\u7ad9\u5728\u5bb6\u5177\u4e0a\u4f5c\u4e1a'},
    {'id': 'R5', 'kw': ['\u5bc6\u95ed', '\u4e0d\u901a\u98ce', '\u6ca1\u7a97'],
     'msg': '\u901a\u98ce\u6761\u4ef6\u5dee\u7684\u5bc6\u95ed\u7a7a\u95f4\u4e0d\u5b9c\u65bd\u5de5\uff0c\u5e94\u5148\u6539\u5584\u901a\u98ce\u6761\u4ef6'},
]

# ---- \u73af\u4fdd\u6307\u6807\u53e3\u5f84\u63d0\u793a ----
INDEX_NOTE = [
    ('VOC', '\u770b\u68c0\u6d4b\u62a5\u544a\u4e2d\u7684\u5b9e\u6d4b\u503c\u4e0e\u68c0\u6d4b\u65b9\u6cd5\u3001\u5355\u4f4d\u4e0e\u9650\u503c\u53e3\u5f84', '\u628a\u4f4e VOC \u5f53\u6210\u65e0 VOC'),
    ('\u7532\u919b\u4e0e\u7532\u919b\u91ca\u653e', '\u533a\u5206\u7532\u919b\u542b\u91cf\u4e0e\u7532\u919b\u91ca\u653e\u91cf\uff0c\u4e24\u8005\u68c0\u6d4b\u65b9\u6cd5\u4e0d\u540c', '\u628a\u672a\u68c0\u51fa\u5f53\u6210\u96f6\u6dfb\u52a0'),
    ('\u6709\u5bb3\u7269\u8d28\u9650\u91cf', '\u662f\u5426\u5c5e\u4e8e\u73b0\u884c\u56fd\u5bb6\u6807\u51c6\u89c4\u5b9a\u7684\u6307\u6807\u9879\u76ee', '\u7528\u67d0\u56fd\u6807\u51c6\u6697\u793a\u9ad8\u4e8e\u56fd\u6807'),
    ('\u8010\u64e6\u6d17\u6b21\u6570', '\u6b21\u6570\u5bf9\u5e94\u7279\u5b9a\u6d4b\u8bd5\u65b9\u6cd5\u4e0b\u7684\u7ed3\u679c', '\u628a\u6b21\u6570\u5f53\u4f5c\u65e5\u5e38\u8010\u64e6\u80fd\u529b'),
    ('\u6297\u9709\u83cc', '\u662f\u5426\u6709\u5bf9\u5e94\u68c0\u6d4b\u4e0e\u7b49\u7ea7', '\u628a\u6dfb\u52a0\u9632\u9709\u6210\u5206\u5f53\u6210\u7ecf\u8fc7\u68c0\u6d4b'),
]

# ---- \u57fa\u5c42\u5904\u7406\u8981\u6c42 ----
SUBSTRATE = [
    ('\u7a7a\u9f13', '\u6572\u51fb\u542c\u7a7a\u97f3', '\u6709\u7a7a\u9f13\u5fc5\u987b\u5148\u5904\u7406'),
    ('\u88c2\u7f1d', '\u76ee\u89c6\uff0c\u91cd\u70b9\u770b\u65b0\u65e7\u88c2\u7f1d', '\u5148\u6309\u88c2\u7f1d\u6027\u8d28\u5904\u7406\uff0c\u672a\u5904\u7406\u7684\u88c2\u7f1d\u4f1a\u7ee7\u7eed\u5f00\u88c2'),
    ('\u6e17\u6c34\u75d5\u8ff9', '\u68c0\u67e5\u6c34\u6e0d\u3001\u6cdb\u78b1\u3001\u8fd4\u6f6e', '\u6709\u6e17\u6c34\u5fc5\u987b\u5148\u89e3\u51b3\u6f0f\u6e90'),
    ('\u65e7\u6f06\u72b6\u51b5', '\u68c0\u67e5\u662f\u5426\u8d77\u58f3\u3001\u7c89\u5316\u3001\u7a7a\u9f13', '\u7c89\u5316\u5c42\u9700\u94f2\u9664\u81f3\u575a\u5b9e\u57fa\u5c42'),
    ('\u5e73\u6574\u5ea6', '\u4fa7\u5149\u89c2\u5bdf', '\u660e\u663e\u51f9\u51f8\u9700\u5148\u7528\u817b\u5b50\u627e\u5e73'),
    ('\u6e05\u6d01\u5ea6', '\u68c0\u67e5\u6cb9\u6c61\u3001\u7070\u5c18', '\u6709\u6cb9\u6c61\u7684\u57fa\u5c42\u9700\u5148\u5904\u7406'),
]

# ---- DIY \u5224\u65ad ----
DIY_OK = ['\u5c40\u90e8\u4fee\u8865\uff08\u78d5\u78b0\u3001\u6c61\u6e0d\u3001\u5c0f\u9762\u79ef\u8d77\u76ae\uff09',
          '\u5355\u4e2a\u5899\u9762\u3001\u9762\u79ef\u4e0d\u5927\u3001\u57fa\u5c42\u72b6\u51b5\u826f\u597d']
DIY_NO = [
    {'kw': ['\u94f2\u9664', '\u94f2\u6389', '\u94f2\u6f06', '\u6253\u78e8\u5230\u57fa\u5c42', '\u65e7\u6f06\u5168\u94f2'],
     'msg': '\u9700\u8981\u94f2\u9664\u65e7\u6f06\u81f3\u57fa\u5c42\u65f6\u8f6c\u4e13\u4e1a\u65bd\u5de5'},
    {'kw': ['\u6574\u6237', '\u5168\u5c4b', '\u5927\u9762\u79ef', '\u6574\u680b'],
     'msg': '\u6574\u6237\u7ffb\u65b0\u6216\u9762\u79ef\u5f88\u5927\u65f6\u8f6c\u4e13\u4e1a\u65bd\u5de5'},
    {'kw': ['\u7a7a\u9f13', '\u6e17\u6c34', '\u7ed3\u6784\u88c2\u7f1d'],
     'msg': '\u57fa\u5c42\u6709\u7a7a\u9f13\u3001\u6e17\u6c34\u75d5\u8ff9\u6216\u7ed3\u6784\u88c2\u7f1d\u65f6\uff0c\u5148\u5904\u7406\u57fa\u5c42\uff0c\u5fc5\u8981\u65f6\u8f6c\u4e13\u4e1a\u65bd\u5de5'},
    {'kw': ['\u9876\u9762', '\u540a\u9876', '\u5929\u82b1'],
     'msg': '\u542b\u9876\u9762\u6216\u540a\u9876\u4f5c\u4e1a\u65f6\u5de5\u7a0b\u91cf\u4e0e\u96be\u5ea6\u660e\u663e\u4e0a\u5347\uff0c\u5efa\u8bae\u8f6c\u4e13\u4e1a\u65bd\u5de5'},
]

MISREAD = [
    {'kw': ['\u96f6\u7532\u919b', '\u96f6VOC', '\u96f6voc', '\u65e0\u7532\u919b', '\u4e0d\u542b\u7532\u919b'],
     'msg': '\u672a\u68c0\u51fa\u4e0d\u7b49\u4e8e\u96f6\u6dfb\u52a0\u3002\u770b\u5230\u8fd9\u7c7b\u5ba3\u4f20\u65f6\u76f4\u63a5\u95ee\u68c0\u6d4b\u62a5\u544a\uff0c\u5e76\u786e\u8ba4\u62a5\u544a\u5bf9\u5e94\u5177\u4f53\u578b\u53f7\u4e0e\u6279\u6b21\u3002'},
    {'kw': ['\u4e00\u4e2a\u6708\u5c31\u4f4f', '\u4e24\u5468', '\u51b7\u51bb', '\u901a\u51e0\u5929\u98ce', '\u6ca1\u5473\u4e86', '\u53ef\u4ee5\u4f4f', '\u4f4f\u8fdb\u53bb', '\u5165\u4f4f', '\u642c\u8fdb\u53bb'],
     'msg': '\u6c14\u5473\u5f3a\u5f31\u4e0d\u7b49\u4e8e\u662f\u5426\u8fbe\u6807\u3002\u662f\u5426\u8fbe\u6807\u6d89\u53ca\u68c0\u6d4b\uff0c\u7ed3\u8bba\u4ee5\u6709\u8d44\u8d28\u7684\u68c0\u6d4b\u4e3a\u51c6\u3002'},
    {'kw': ['\u817b\u5b50\u6ca1\u5e72', '\u6ca1\u5e72\u900f\u5c31\u5237', '\u8d76\u8fdb\u5ea6', '\u5feb\u70b9\u5e72'],
     'msg': '\u817b\u5b50\u6ca1\u5e72\u900f\u5c31\u5237\u6f06\u662f\u8d77\u76ae\u5e38\u89c1\u539f\u56e0\uff0c\u6bcf\u904d\u5e72\u71e5\u65f6\u95f4\u6309\u4ea7\u54c1\u8bf4\u660e\u4e66\uff0c\u4e0d\u8981\u538b\u7f29\u3002'},
    {'kw': ['\u6f0f\u4e86', '\u76d6\u4f4f\u5c31\u884c', '\u5148\u5237\u4e0a\u518d\u8bf4'],
     'msg': '\u5899\u4e0a\u6709\u6e17\u6c34\u8fd8\u5237\u6f06\uff0c\u6e7f\u57fa\u5c42\u5fc5\u7136\u8d77\u76ae\u3002\u5148\u89e3\u51b3\u6f0f\u6e90\u518d\u505a\u5899\u9762\u3002'},
    {'kw': ['\u6df7\u7740\u7528', '\u5269\u7684\u4e5f\u5237', '\u4e24\u6876\u4e00\u8d77'],
     'msg': '\u4e0d\u540c\u6279\u6b21\u7684\u6f06\u6df7\u7528\u4f1a\u5728\u540c\u623f\u95f4\u4ea7\u751f\u660e\u663e\u8272\u5dee\uff0c\u540c\u4e00\u533a\u57df\u5c3d\u91cf\u7528\u540c\u4e00\u6279\u6b21\u3002'},
]


def analyse(text):
    t = (text or '').replace(' ', '').replace('\u3000', '')
    types = []
    for p in PAINT_TYPES:
        hits = [k for k in p['kw'] if k in t]
        if hits:
            types.append({'name': p['name'], 'hits': hits, 'pro': p['pro'],
                          'con': p['con'], 'fit': p['fit']})
    fails = []
    for f in FAILURES:
        hits = [k for k in f['kw'] if k in t]
        if hits:
            fails.append({'name': f['name'], 'hits': hits, 'cause': f['cause'],
                          'duty': f['duty']})
    reds = [r['msg'] for r in SAFETY if any(k in t for k in r['kw'])]
    diy_no = [d['msg'] for d in DIY_NO if any(k in t for k in d['kw'])]
    miss = [m['msg'] for m in MISREAD if any(k in t for k in m['kw'])]
    return {'types': types, 'failures': fails, 'reds': reds, 'diy_no': diy_no,
            'misread': miss, 'diy_ok': not reds and not diy_no,
            'top_type': types[0]['name'] if types else '',
            'top_fail': fails[0]['name'] if fails else ''}


def render_md(r):
    lines = ['# \u4e73\u80f6\u6f06\u9009\u578b\u4e0e\u65bd\u5de5\u6838\u67e5\u7ed3\u679c', '']
    lines.append('> \u6210\u54c1\u597d\u4e0d\u597d\uff0c\u516b\u6210\u53d6\u51b3\u4e8e\u57fa\u5c42\u4e0e\u65bd\u5de5\u6761\u4ef6\uff0c\u4e0d\u53d6\u51b3\u4e8e\u54c1\u724c\u3002')
    lines.append('')

    lines.append('## \u4e00\u3001\u6d82\u6599\u7c7b\u578b')
    lines.append('')
    if not r['types']:
        lines.append('\u672a\u8bc6\u522b\u6d82\u6599\u7c7b\u578b\u3002\u5e38\u89c1\u56db\u7c7b\u4e3a\u4e73\u80f6\u6f06\u3001\u827a\u672f\u6f06\u3001\u7845\u85fb\u6ce5\u3001\u8d1d\u58f3\u7c89\u3002')
    else:
        lines.append('| \u7c7b\u578b | \u547d\u4e2d\u7ebf\u7d22 | \u4e3b\u8981\u4f18\u52bf | \u4e3b\u8981\u9650\u5236 | \u9002\u5408\u4f4d\u7f6e |')
        lines.append('|---|---|---|---|---|')
        for p in r['types']:
            lines.append('| %s | %s | %s | %s | %s |' % (
                p['name'], '\u3001'.join(p['hits']), p['pro'], p['con'], p['fit']))
    lines.append('')

    lines.append('## \u4e8c\u3001\u73af\u4fdd\u6307\u6807\u600e\u4e48\u770b\u53e3\u5f84')
    lines.append('')
    lines.append('**\u6570\u503c\u968f\u73b0\u884c\u56fd\u5bb6\u6807\u51c6\u4e0e\u4ea7\u54c1\u5b9e\u9645\u53d8\u5316\uff0c\u4ee5\u73b0\u884c\u56fd\u5bb6\u6807\u51c6\u548c\u68c0\u6d4b\u62a5\u544a\u4e3a\u51c6\u3002**')
    lines.append('')
    lines.append('| \u6307\u6807 | \u8be5\u770b\u4ec0\u4e48 | \u5e38\u89c1\u8bef\u533a |')
    lines.append('|---|---|---|')
    for a, b, c in INDEX_NOTE:
        lines.append('| %s | %s | %s |' % (a, b, c))
    lines.append('')
    lines.append('**\u770b\u62a5\u544a\u7684\u56db\u4e2a\u52a8\u4f5c**\uff1a\u786e\u8ba4\u62a5\u544a\u5bf9\u5e94\u578b\u53f7\u4e0e\u6279\u6b21\uff1b\u786e\u8ba4\u4f9d\u636e\u73b0\u884c\u56fd\u5bb6\u6807\u51c6\uff1b\u786e\u8ba4\u5355\u4f4d\u4e0e\u68c0\u6d4b\u65b9\u6cd5\uff1b')
    lines.append('\u770b\u62a5\u544a\u51fa\u5177\u673a\u6784\uff0c\u4e0d\u63a5\u53d7\u53ea\u6709\u4ea7\u54c1\u5ba3\u4f20\u9875\u7684\u8bf4\u6cd5\u3002')
    lines.append('')
    lines.append('**\u672a\u68c0\u51fa\u4e0d\u7b49\u4e8e\u96f6\u6dfb\u52a0**\uff1a\u672a\u68c0\u51fa\u53ea\u8868\u793a\u4f4e\u4e8e\u68c0\u6d4b\u65b9\u6cd5\u4e0b\u9650\uff0c\u4e0d\u8868\u793a\u914d\u65b9\u91cc\u5b8c\u5168\u6ca1\u6709\u3002')
    lines.append('')

    lines.append('## \u4e09\u3001\u57fa\u5c42\u5904\u7406\u8981\u6c42')
    lines.append('')
    lines.append('| \u68c0\u67e5\u9879 | \u65b9\u6cd5 | \u8981\u6c42 |')
    lines.append('|---|---|---|')
    for a, b, c in SUBSTRATE:
        lines.append('| %s | %s | %s |' % (a, b, c))
    lines.append('')

    lines.append('## \u56db\u3001\u5e38\u89c1\u5931\u8d25\u73b0\u8c61\u4e0e\u8d23\u4efb\u5f52\u5c5e\u53c2\u8003')
    lines.append('')
    if not r['failures']:
        lines.append('\u672a\u8bc6\u522b\u5931\u8d25\u73b0\u8c61\u3002\u82e5\u5df2\u6709\u5f02\u5e38\uff0c\u8bf7\u63cf\u8ff0\u662f\u8d77\u76ae\u3001\u5f00\u88c2\u3001\u6d41\u6302\u3001\u900f\u5e95\u3001\u8272\u5dee\u3001\u53d1\u82b1\u8fd8\u662f\u6389\u7c89\u3002')
    else:
        lines.append('| \u73b0\u8c61 | \u547d\u4e2d\u7ebf\u7d22 | \u5e38\u89c1\u539f\u56e0 | \u8d23\u4efb\u5f52\u5c5e\u53c2\u8003 |')
        lines.append('|---|---|---|---|')
        for f in r['failures']:
            lines.append('| %s | %s | %s | %s |' % (
                f['name'], '\u3001'.join(f['hits']), f['cause'], f['duty']))
    lines.append('')
    lines.append('\u8d23\u4efb\u5f52\u5c5e\u7684\u6700\u7ec8\u8ba4\u5b9a\u4ee5\u65bd\u5de5\u5408\u540c\u7ea6\u5b9a\u3001\u73b0\u573a\u8bb0\u5f55\u3001\u4ea7\u54c1\u68c0\u6d4b\u62a5\u544a\u4e0e\u4e13\u4e1a\u68c0\u6d4b\u7ed3\u8bba\u4e3a\u51c6\u3002')
    lines.append('')

    lines.append('## \u4e94\u3001\u65bd\u5de5\u5b89\u5168\u7ea2\u7ebf')
    lines.append('')
    if r['reds']:
        for m in r['reds']:
            lines.append('- %s' % m)
    else:
        lines.append('- \u672c\u6b21\u672a\u547d\u4e2d\u5b89\u5168\u7ea2\u7ebf\u3002\u4ecd\u9700\u81ea\u67e5\uff1a\u662f\u5426\u6709\u5b55\u5987\u3001\u5a74\u5e7c\u513f\u3001\u547c\u5438\u9053\u654f\u611f\u8005\u5c45\u4f4f\uff1b'
                     '\u662f\u5426\u9700\u8981\u9ad8\u5904\u4f5c\u4e1a\uff1b\u901a\u98ce\u6761\u4ef6\u662f\u5426\u8db3\u591f\u3002')
    lines.append('')

    lines.append('## \u516d\u3001DIY \u8303\u56f4\u5224\u65ad')
    lines.append('')
    lines.append('**\u53ef\u81ea\u884c\u5904\u7406\uff1a**')
    lines.append('')
    for d in DIY_OK:
        lines.append('- %s' % d)
    lines.append('')
    if r['diy_no']:
        lines.append('**\u672c\u6b21\u547d\u4e2d\u8f6c\u4e13\u4e1a\u65bd\u5de5\u7684\u60c5\u5f62\uff1a**')
        lines.append('')
        for d in r['diy_no']:
            lines.append('- %s' % d)
        lines.append('')
    else:
        lines.append('\u4ecd\u9700\u81ea\u67e5\uff1a\u662f\u5426\u9700\u8981\u94f2\u9664\u65e7\u6f06\u3001\u9762\u79ef\u662f\u5426\u5f88\u5927\u3001\u57fa\u5c42\u662f\u5426\u6709\u7a7a\u9f13\u6e17\u6c34\u3001\u662f\u5426\u9ad8\u5904\u4f5c\u4e1a\u3002')
        lines.append('')

    if r['misread']:
        lines.append('## \u4e03\u3001\u5e38\u89c1\u8bef\u5224\u63d0\u9192')
        lines.append('')
        for m in r['misread']:
            lines.append('- %s' % m)
        lines.append('')

    lines.append('---')
    lines.append('')
    lines.append('\u672c\u7ed3\u679c\u4e3a\u73b0\u8c61\u5339\u914d\u4e0e\u9009\u578b\u5efa\u8bae\uff0c\u4e0d\u4ee3\u8868\u73b0\u573a\u5224\u65ad\uff0c\u4e0d\u6784\u6210\u4e13\u4e1a\u65bd\u5de5\u6216\u68c0\u6d4b\u7ed3\u8bba\u3002')
    lines.append('\u73af\u4fdd\u6307\u6807\u9650\u503c\u4ee5\u73b0\u884c\u56fd\u5bb6\u6807\u51c6\u548c\u4ea7\u54c1\u68c0\u6d4b\u62a5\u544a\u4e3a\u51c6\uff0c\u65bd\u5de5\u53c2\u6570\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e66\u4e3a\u51c6\u3002')
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

    r1 = analyse('\u5899\u9762\u8d77\u76ae\u4e86\uff0c\u5b55\u5987\u5728\u5bb6')
    eq('case1 \u8d77\u76ae\u8bc6\u522b', r1['top_fail'], '\u8d77\u76ae')
    eq('case2 \u5b55\u5987\u7ea2\u7ebf', any('\u5b55\u5987' in m for m in r1['reds']), True)
    eq('case3 \u4e0d\u53efDIY', r1['diy_ok'], False)

    r2 = analyse('\u5237\u5b8c\u989c\u8272\u4e0d\u4e00\u6837\uff0c\u6709\u8272\u5757')
    eq('case4 \u8272\u5dee\u8bc6\u522b', r2['top_fail'], '\u8272\u5dee')

    r3 = analyse('\u5899\u9762\u5f00\u88c2\u4e86')
    eq('case5 \u5f00\u88c2\u8bc6\u522b', r3['top_fail'], '\u5f00\u88c2')

    r4 = analyse('\u60f3\u7528\u7845\u85fb\u6ce5')
    eq('case6 \u7845\u85fb\u6ce5\u8bc6\u522b', r4['top_type'], '\u7845\u85fb\u6ce5')
    eq('case7 \u8010\u64e6\u6d17\u63d0\u793a', any('\u8010\u64e6\u6d17' in p['con'] for p in r4['types']), True)

    r5 = analyse('\u827a\u672f\u6f06\u597d\u770b\uff0c\u60f3\u7528\u827a\u672f\u6f06')
    eq('case8 \u827a\u672f\u6f06\u8bc6\u522b', r5['top_type'], '\u827a\u672f\u6f06')
    eq('case9 \u4fee\u8865\u63d0\u793a', any('\u4fee\u8865' in p['con'] for p in r5['types']), True)

    r6 = analyse('\u5ba3\u4f20\u8bf4\u662f\u96f6\u7532\u919b')
    eq('case10 \u672a\u68c0\u51fa\u63d0\u9192', any('\u672a\u68c0\u51fa' in m for m in r6['misread']), True)

    r7 = analyse('\u901a\u98ce\u4e00\u4e2a\u6708\u5c31\u6253\u7b97\u4f4f\u8fdb\u53bb')
    eq('case11 \u8fbe\u6807\u63d0\u9192', any('\u68c0\u6d4b' in m for m in r7['misread']), True)

    r8 = analyse('\u8981\u5148\u94f2\u6389\u65e7\u6f06\u518d\u5237')
    eq('case12 \u94f2\u6f06\u8f6c\u4e13\u4e1a', any('\u94f2\u9664' in m for m in r8['diy_no']), True)

    r9 = analyse('\u60f3\u7ad9\u6905\u5b50\u5237\u9ad8\u5899')
    eq('case13 \u9ad8\u5904\u4f5c\u4e1a\u7ea2\u7ebf', any('\u9ad8\u5904' in m for m in r9['reds']), True)

    r10 = analyse('\u5899\u9762\u4e00\u64e6\u4e00\u624b\u767d\uff0c\u6389\u7c89')
    eq('case14 \u6389\u7c89\u8bc6\u522b', r10['top_fail'], '\u6389\u7c89')

    r11 = analyse('\u4ec0\u4e48\u90fd\u6ca1\u6709')
    eq('case15 \u65e0\u5339\u914d', (r11['types'], r11['failures']), ([], []))

    md = render_md(r1)
    eq('case16 \u8f93\u51fa\u8868\u5934', md.startswith('# '), True)
    eq('case17 \u542b\u6307\u6807\u53e3\u5f84', '\u672a\u68c0\u51fa\u4e0d\u7b49\u4e8e\u96f6\u6dfb\u52a0' in md, True)
    eq('case18 \u542b\u57fa\u5c42\u8981\u6c42', '\u57fa\u5c42\u5904\u7406\u8981\u6c42' in md, True)
    js = json.loads(json.dumps(r1, ensure_ascii=False))
    eq('case19 JSON\u952e', sorted(js.keys()),
       ['diy_no', 'diy_ok', 'failures', 'misread', 'reds', 'top_fail', 'top_type', 'types'])

    # \u5e26 BOM \u7684 JSON \u8f93\u5165\u5fc5\u987b\u80fd\u6b63\u786e\u89e3\u6790
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write('{"desc": "\u5899\u9762\u8d77\u76ae\u4e86"}')
    got = read_input(tmp)
    os.remove(tmp)
    eq('case20 \u5e26BOM\u7684JSON\u9996\u952e', analyse(got)['top_fail'], '\u8d77\u76ae')

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 23\n\u8986\u76d6: \u8d77\u76ae/\u8272\u5dee/\u5f00\u88c2/\u6389\u7c89/\u56db\u7c7b\u6d82\u6599/\u6307\u6807\u53e3\u5f84/'
               '\u672a\u68c0\u51fa\u63d0\u9192/\u8fbe\u6807\u63d0\u9192/\u94f2\u6f06\u8f6c\u4e13\u4e1a/\u9ad8\u5904\u4f5c\u4e1a/\u4eba\u7fa4\u7ea2\u7ebf/BOM\u89e3\u6790')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u4e73\u80f6\u6f06\u9009\u578b\u4e0e\u65bd\u5de5\u6838\u67e5')
    ap.add_argument('--text', help='\u5899\u9762\u72b6\u51b5\u4e0e\u5c45\u4f4f\u60c5\u51b5\u63cf\u8ff0')
    ap.add_argument('--file', help='\u4ece\u6587\u4ef6\u8bfb\uff0c\u652f\u6301 txt / md / json')
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
        text = read_input(a.file)
    if not text.strip():
        print('ERROR \u9700\u8981 --text \u6216 --file')
        return 2

    r = analyse(text)
    out = render_md(r) if a.format == 'md' else json.dumps(r, ensure_ascii=False, indent=2)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % a.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())