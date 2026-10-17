# -*- coding: utf-8 -*-
"""\u98df\u7269\u4ea4\u53c9\u6c61\u67d3\u4e0e\u751f\u719f\u5206\u5f00\u6838\u67e5\uff1a\u6309\u64cd\u4f5c\u987a\u5e8f\u6838\u67e5\u751f\u719f\u5206\u5f00\u3001\u81f4\u75c5\u83cc\u98ce\u9669\u4e0e\u51b7\u85cf\u6e29\u5ea6\u3002

\u7528\u6cd5:
  python cross_contamination_check.py --file kitchen.json [--out result.md] [--format json]
  python cross_contamination_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u6b63\u786e\u64cd\u4f5c\u987a\u5e8f: \u5148\u6d17\u83dc -> \u518d\u5207\u751f\u8089 -> \u6700\u540e\u5207\u719f\u98df
CORRECT_ORDER = ['wash_veg', 'cut_raw_meat', 'cut_cooked']

# \u987a\u5e8f\u8bf4\u660e: (\u952e, \u4e2d\u6587\u540d, \u8bf4\u660e, \u5e38\u89c1\u9519\u8bef)
ORDER_DETAIL = [
    ('wash_veg', '\u7b2c\u4e00\u6b65\uff1a\u5148\u6d17\u83dc\u5207\u83dc',
     '\u5148\u5904\u7406\u852c\u83dc\u4e0e\u6c34\u679c\uff0c\u6d17\u51c0\u6ca5\u5e72\u540e\u5207\u5206\u88c5\u76d2',
     '\u5148\u5207\u751f\u8089\u518d\u6d17\u83dc\uff0c\u751f\u8089\u6c41\u6db2\u6cbe\u5230\u6c34\u9f99\u5934\u4e0e\u83dc\u4e0a'),
    ('cut_raw_meat', '\u7b2c\u4e8c\u6b65\uff1a\u518d\u5207\u751f\u8089\u751f\u79bd',
     '\u751f\u8089\u79bd\u5355\u72ec\u7528\u5200\u4e0e\u7827\u677f\uff0c\u5207\u5b8c\u7acb\u5373\u6e05\u6d17\u5668\u5177\u4e0e\u53f0\u9762',
     '\u7528\u5207\u8fc7\u751f\u8089\u7684\u5200\u76f4\u63a5\u5207\u719f\u98df\u6216\u76f4\u63a5\u5165\u53e3\u98df\u54c1'),
    ('cut_cooked', '\u7b2c\u4e09\u6b65\uff1a\u6700\u540e\u5207\u719f\u98df',
     '\u751f\u719f\u5f7b\u5e95\u5206\u5f00\u540e\uff0c\u6700\u540e\u5904\u7406\u719f\u98df\u3001\u5373\u98df\u4e0e\u6c34\u679c',
     '\u628a\u751f\u719f\u98df\u653e\u5728\u540c\u4e00\u5757\u7827\u677f\u4e0a\u5207'),
]

# \u7827\u677f\u989c\u8272\u5206\u533a
BOARD_ZONES = [
    ('\u7ea2\u8272', '\u751f\u8089\u4e0e\u751f\u79bd', '\u5207\u751f\u8089\u79bd\u540e\u7684\u5200\u8981\u4e13\u7528\uff0c\u4e0d\u5207\u5176\u4ed6'),
    ('\u84dd\u8272', '\u751f\u6d77\u9c9c\u4e0e\u6c34\u4ea7', '\u6c34\u4ea7\u6613\u4ea4\u53c9\u6c61\u67d3\uff0c\u4e14\u6613\u6d41\u5931\u6c41\u6db2'),
    ('\u7eff\u8272', '\u852c\u83dc\u4e0e\u6c34\u679c', '\u852c\u83dc\u5e94\u5148\u6d17\u540e\u5207\uff0c\u6d17\u51c0\u5373\u98df\u53ef\u4e0d\u518d\u52a0\u70ed'),
    ('\u9ec4\u8272', '\u719f\u98df\u4e0e\u5373\u98df', '\u5207\u719f\u98df\u5373\u98df\u7684\u5200\u4e0e\u7827\u677f\uff0c\u4e0d\u78b0\u751f\u98df'),
    ('\u68d5\u8272', '\u751f\u98df\u975e\u8089\u7c7b', '\u5982\u751f\u8c46\u7c7b\u3001\u751f\u719f\u524d\u5904\u7406'),
]

# \u5e38\u89c1\u81f4\u75c5\u83cc: (\u952e, \u4e2d\u6587\u540d, \u4e3b\u8981\u6765\u6e90, \u6613\u88ab\u5ffd\u89c6\u4e4b\u5904)
PATHOGENS = [
    ('salmonella', '\u6c99\u95e8\u6c0f\u83cc', '\u751f\u79bd\u8089\u3001\u751f\u86cb\u3001\u4ea4\u53c9\u6c61\u67d3\u7684\u5373\u98df\u98df\u54c1',
     '\u6c61\u67d3\u7684\u86cb\u4e0e\u79bd\u8089**\u5916\u89c2\u4e0e\u6c14\u5473\u5b8c\u5168\u6b63\u5e38**\uff0c\u52a0\u70ed\u5145\u5206\u53ef\u6740\u706d\uff0c\u4f46\u751f\u98df\u9636\u6bb5\u65e0\u4efb\u4f55\u63d0\u793a'),
    ('listeria', '\u674e\u65af\u7279\u83cc', '\u51b7\u85cf\u5373\u98df\u98df\u54c1\u3001\u8f6f\u5976\u916a\u3001\u719f\u8089\u5236\u54c1\u3001\u5373\u98df\u719f\u98df',
     '\u53ef\u5728**\u51b7\u85cf\u6e29\u5ea6\u4e0b\u7f13\u6162\u589e\u6b96**\uff0c\u5ba4\u6e29\u4e0e\u51b7\u85cf\u521d\u671f\u611f\u5b98\u5747\u65e0\u5f02\u5e38'),
    ('campylobacter', '\u5f2f\u66f2\u83cc', '\u751f\u79bd\u8089\u3001\u672a\u7ecf\u5df4\u6c0f\u6740\u83cc\u7684\u5976',
     '\u751f\u79bd\u9636\u6bb5\u65e0\u611f\u5b98\u63d0\u793a\uff0c\u52a0\u70ed\u53ef\u6740\u706d\uff0c\u4f46**\u4ec5\u51b2\u6d17\u4e0d\u80fd\u6740\u706d**'),
    ('staph', '\u91d1\u9ec4\u8272\u8461\u8404\u7403\u83cc', '\u719f\u98df\u3001\u542b\u5976\u6cb9\u7684\u70b9\u5fc3\u3001\u957f\u65f6\u95f4\u5ba4\u6e29\u653e\u7f6e\u7684\u98df\u7269',
     '\u8010\u70ed\u6bd2\u7d20**\u52a0\u70ed\u4e0d\u80fd\u7834\u574f**\uff0c\u4e14\u53ef\u5728\u98df\u7269\u4e2d\u751f\u957f\u5e76\u4ea7\u6bd2'),
    ('bacillus', '\u8721\u6837\u82bd\u5b62\u6746\u83cc', '\u7c73\u996d\u3001\u9762\u6761\u7b49\u542b\u6dc0\u7c89\u98df\u7269\u7684\u5ba4\u6e29\u5b58\u653e',
     '\u90e8\u5206\u6bd2\u7d20**\u52a0\u70ed\u4e0d\u88ab\u7834\u574f**\uff0c\u56e0\u6b64\u51c9\u996d\u5269\u996d\u98ce\u9669\u9ad8\u4e8e\u5176\u4ed6'),
    ('e_coli', '\u5927\u80a0\u6746\u83cc', '\u672a\u6d17\u51c0\u7684\u751f\u852c\u3001\u6c61\u67d3\u7684\u5373\u98df\u98df\u54c1',
     '\u751f\u83dc\u6c99\u62c9\u98ce\u9669\u5e38\u88ab\u4f4e\u4f30\uff0c**\u4e0d\u7ecf\u8fc7\u52a0\u70ed\u5373\u88ab\u98df\u7528**'),
]

# \u51b7\u85cf\u6e29\u5ea6\u533a\u95f4
TEMP = {
    'fridge_max': 4.0,
    'freezer_max': -18.0,
    'danger_low': 4.0,
    'danger_high': 60.0,
}

# \u9ad8\u98ce\u9669\u4eba\u7fa4\u4e0e\u8b66\u793a
HIGH_RISK = [
    ('\u5a74\u5e7c\u513f', '\u5c24\u5176 6 \u4e2a\u6708\u4ee5\u4e0b\uff0c\u80a0\u9053\u83cc\u7fa4\u5c1a\u672a\u5efa\u7acb\uff0c\u611f\u67d3\u540e\u98ce\u9669\u6700\u9ad8'),
    ('\u5b55\u5987', '\u907f\u514d\u751f\u98df\u4e0e\u672a\u5f7b\u5e95\u52a0\u70ed\u7684\u8089\u86cb\u6c34\u4ea7'),
    ('65 \u5c81\u4ee5\u4e0a\u8001\u4eba', '\u514d\u75ab\u529f\u80fd\u4e0b\u964d\uff0c\u4e14\u5473\u89c9\u55c5\u89c9\u51cf\u9000\u5bfc\u81f4**\u611f\u5b98\u5224\u65ad\u672c\u8eab\u4e0d\u53ef\u9760**'),
    ('\u514d\u75ab\u529b\u4f4e\u4e0b\u8005', '\u5305\u62ec\u957f\u671f\u4f7f\u7528\u6fc0\u7d20\u3001\u5316\u7597\u3001\u5668\u5b98\u79fb\u690d\u540e\u670d\u836f\u4eba\u7fa4'),
    ('\u6b63\u5728\u670d\u836f\u8005', '\u90e8\u5206\u836f\u7269\u4e0e\u514d\u75ab\u529f\u80fd\u76f8\u5173\uff0c\u9700\u66f4\u4e25\u683c'),
    ('\u6162\u6027\u75c5\u60a3\u8005', '\u7cd6\u5c3f\u75c5\u7b49\u57fa\u7840\u75c5\u4f1a\u653e\u5927\u98df\u6e90\u6027\u75be\u75c5\u540e\u679c'),
]

# \u660e\u786e\u7981\u6b62\u7684\u64cd\u4f5c
BANNED = [
    '\u540c\u4e00\u5757\u7827\u677f\u5148\u5207\u751f\u8089\u518d\u5207\u719f\u98df',
    '\u7528\u5207\u8fc7\u751f\u8089\u7684\u5200\u5207\u719f\u98df\u6216\u5373\u98df\u98df\u54c1\uff0c\u4e0d\u6e05\u6d17',
    '\u5207\u5b8c\u751f\u8089\u4e0d\u6d17\u624b\u5c31\u63a5\u89e6\u719f\u98df\u4e0e\u5373\u98df\u98df\u54c1',
    '\u751f\u852c\u4e0e\u5373\u98df\u51c9\u83dc\u653e\u5728\u540c\u4e00\u5bb9\u5668\u6216\u540c\u4e00\u5c42\u51b0\u7bb1',
    '\u628a\u5df2\u7ecf\u5207\u597d\u7684\u751f\u8089\u4e0e\u719f\u98df\u6df7\u88c5\u5728\u4e00\u4e2a\u4fdd\u9c9c\u76d2',
    '\u5904\u7406\u751f\u8089\u540e\u4e0d\u5012\u6389\u89e3\u51bb\u6c34\u4e0e\u8840\u6c34',
    '\u751f\u79bd\u4e0e\u5373\u98df\u98df\u54c1\u653e\u5728\u51b0\u7bb1\u540c\u4e00\u5c42\u4e14\u4e0d\u505a\u9694\u79bb',
    '\u53ea\u7528\u64e6\u5200\u5e03\u64e6\u4e00\u4e0b\u5200\u5c31\u5f53\u4f5c\u6e05\u6d17\u5b8c\u6210',
]

# \u751f\u719f\u5206\u5f00\u7684\u5177\u4f53\u505a\u6cd5
PRACTICES = [
    '\u7827\u677f**\u6309\u989c\u8272\u5206\u533a**\uff1a\u7ea2\u8272\u751f\u8089\u79bd\u3001\u84dd\u8272\u6c34\u4ea7\u3001\u7eff\u8272\u852c\u679c\u3001\u9ec4\u8272\u719f\u98df\u5373\u98df',
    '\u751f\u8089\u4e13\u7528\u5200\u4e0e\u7827\u677f\uff0c**\u4e0d\u5207\u719f\u98df\u4e5f\u4e0d\u5207\u76f4\u63a5\u5165\u53e3\u7684\u852c\u679c**',
    '\u5207\u751f\u8089\u540e**\u7acb\u5373\u7528\u7682\u6db2\u6d17\u624b**\uff0c\u518d\u63a5\u89e6\u719f\u98df\u4e0e\u5373\u98df\u98df\u54c1',
    '\u751f\u79bd\u751f\u8089\u653e\u5165**\u5e95\u90e8\u6216\u4e13\u7528\u5bc6\u95ed\u5bb9\u5668**\uff0c\u6ef4\u6db2\u4e0d\u5f97\u6c61\u67d3\u4e0b\u5c42\u5373\u98df\u98df\u54c1',
    '\u89e3\u51bb\u6c34\u4e0e\u8840\u6c34**\u5fc5\u987b\u5012\u6389**\uff0c\u5bb9\u5668\u7528\u540e\u7acb\u5373\u6e05\u6d17',
    '\u751f\u719f\u98df**\u5206\u683c\u5b58\u653e**\uff0c\u751f\u98df\u5728\u4e0b\u3001\u5373\u98df\u5728\u4e0a',
    '\u51c9\u62cc\u83dc\u4e0e\u5373\u98df\u98df\u54c1**\u5236\u4f5c\u5b8c\u6210\u540e\u5c3d\u5feb\u98df\u7528**\uff0c\u4e0d\u4e0e\u751f\u98df\u4ea4\u53c9\u63a5\u89e6',
    '\u53ea\u6709\u4e00\u628a\u5200\u65f6\uff0c\u5207\u5b8c\u751f\u8089\u5fc5\u987b**\u5f7b\u5e95\u51b2\u6d17\u5e76\u7528\u7682\u6db2\u6e05\u6d01\u5200\u9762**',
]

# \u64cd\u4f5c\u987a\u5e8f\u68c0\u67e5\u9879: (\u952e, \u4e2d\u6587\u540d, \u8bf4\u660e)
ORDER_CHECKS = [
    ('board_separated', '\u7827\u677f\u751f\u719f\u5206\u5f00',
     '\u751f\u8089\u7827\u677f\u4e0e\u719f\u98df\u7827\u677f\u5206\u7528\uff0c\u672a\u6df7\u7528'),
    ('knife_dedicated', '\u5200\u5177\u4e13\u7528',
     '\u751f\u8089\u5200\u4e0d\u5207\u719f\u98df\u4e0e\u5373\u98df\u98df\u54c1'),
    ('hand_washed', '\u5904\u7406\u751f\u8089\u540e\u6d17\u624b',
     '\u5207\u5b8c\u751f\u8089\u5df2\u7528\u7682\u6db2\u6d17\u624b\uff0c\u518d\u63a5\u89e6\u719f\u98df'),
    ('store_order', '\u51b0\u7bb1\u751f\u719f\u5206\u683c',
     '\u751f\u98df\u653e\u4e0b\u5c42\uff0c\u5373\u98df\u653e\u4e0a\u5c42\uff0c\u6709\u6ef4\u6db2\u9694\u79bb'),
    ('juice_discarded', '\u89e3\u51bb\u6c34\u4e0e\u8840\u6c34\u5df2\u5012',
     '\u751f\u8089\u89e3\u51bb\u6db2\u4e0e\u8840\u6c34\u5df2\u5012\u6389\uff0c\u672a\u6c61\u67d3\u5176\u4ed6'),
    ('veg_washed_first', '\u852c\u83dc\u5148\u6d17\u540e\u5207',
     '\u852c\u83dc\u5df2\u6e05\u6d17\u5e76\u6ca5\u5e72\uff0c\u672a\u5148\u5207\u751f\u8089\u518d\u6d17\u83dc'),
    ('cold_food_protected', '\u5373\u98df\u4e0e\u51c9\u83dc\u9694\u79bb',
     '\u51c9\u62cc\u83dc\u4e0e\u5373\u98df\u98df\u54c1\u672a\u4e0e\u751f\u98df\u4ea4\u53c9\u63a5\u89e6'),
    ('equipment_cleaned', '\u5668\u5177\u5df2\u6e05\u6d17',
     '\u7827\u677f\u3001\u5200\u3001\u53f0\u9762\u5728\u5904\u7406\u751f\u8089\u540e\u5df2\u6e05\u6d17'),
]


def norm(k):
    return str(k or '').strip().lower().replace(' ', '')


def order_check(steps):
    """steps: \u5df2\u5b8c\u6210\u7684\u6b65\u9aa4\u5217\u8868(\u6309\u5b9e\u9645\u6267\u884c\u987a\u5e8f)\u3002\u8fd4\u56de\u5224\u5b9a\u4e0e\u8fdd\u89c4\u3002"""
    if steps is None:
        steps = []
    if not isinstance(steps, list):
        raise ValueError('steps \u5fc5\u987b\u662f\u5217\u8868')
    # \u4fdd\u7559\u7528\u6237\u63d0\u4ea4\u7684\u5b9e\u9645\u6267\u884c\u987a\u5e8f\uff08\u53bb\u91cd\u4f46\u4e0d\u6539\u987a\u5e8f\uff09\uff0c\u4e0d\u80fd\u6309 CORRECT_ORDER \u91cd\u6392\uff0c
    # \u5426\u5219\u65e0\u8bba\u7528\u6237\u600e\u4e48\u586b\uff0c\u987a\u5e8f\u90fd\u4f1a\u88ab\u89c4\u8303\u5316\u6210\u6b63\u5e8f\uff0c\u9519\u8bef\u987a\u5e8f\u6c38\u8fdc\u68c0\u6d4b\u4e0d\u51fa\u6765\u3002
    order = []
    for s in steps:
        n = norm(s)
        if n not in CORRECT_ORDER:
            raise ValueError('\u672a\u77e5\u7684\u6b65\u9aa4: %s\uff0c\u53ef\u9009 %s \u4e4b\u4e00' % (s, '/'.join(CORRECT_ORDER)))
        if n not in order:
            order.append(n)
    good = order == CORRECT_ORDER
    return order, good


def check_practices(flags):
    if flags is None:
        flags = {}
    if not isinstance(flags, dict):
        raise ValueError('practices \u5fc5\u987b\u662f\u5bf9\u8c61')
    for k in flags:
        if not any(norm(c[0]) == norm(k) for c in ORDER_CHECKS):
            raise ValueError('\u672a\u77e5\u7684\u68c0\u67e5\u9879: %s\uff0c\u53ef\u9009\u9879\u89c1 ORDER_CHECKS \u8868' % k)
    rows = []
    bad = []
    unk = []
    for key, name, desc in ORDER_CHECKS:
        v = flags.get(key)
        if v is None:
            rows.append({'name': name, 'status': '\u672a\u68c0\u67e5', 'desc': desc})
            unk.append(name)
        elif v:
            rows.append({'name': name, 'status': '\u5408\u683c', 'desc': desc})
        else:
            rows.append({'name': name, 'status': '\u4e0d\u5408\u683c', 'desc': desc})
            bad.append(name)
    return rows, bad, unk


def calc(data):
    steps = data.get('steps') or []
    order, order_ok = order_check(steps)
    rows_p, bad_p, unk_p = check_practices(data.get('practices'))

    fridge_t = data.get('fridge_temp')
    freezer_t = data.get('freezer_temp')
    temp_rows = []
    fridge_ok = None
    freezer_ok = None
    if fridge_t is not None:
        v = float(fridge_t)
        fridge_ok = v <= TEMP['fridge_max']
        temp_rows.append({'name': '\u51b7\u85cf\u5ba4', 'value': v, 'limit': TEMP['fridge_max'],
                          'status': '\u8fbe\u6807' if fridge_ok else '\u8d85\u6807',
                          'note': '\u4e0d\u9ad8\u4e8e 4 \u6444\u6c0f\u5ea6\u4e3a\u8fbe\u6807'})
    if freezer_t is not None:
        v = float(freezer_t)
        freezer_ok = v <= TEMP['freezer_max']
        temp_rows.append({'name': '\u51b7\u51bb\u5ba4', 'value': v, 'limit': TEMP['freezer_max'],
                          'status': '\u8fbe\u6807' if freezer_ok else '\u8d85\u6807',
                          'note': '\u4e0d\u9ad8\u4e8e\u8d1f 18 \u6444\u6c0f\u5ea6\u4e3a\u8fbe\u6807'})

    # \u5224\u5b9a\u987a\u5e8f: \u5148\u770b\u6709\u6ca1\u6709\u771f\u5b9e\u7f3a\u9677(\u987a\u5e8f\u9519/\u68c0\u67e5\u9879\u4e0d\u5408\u683c/\u6e29\u5ea6\u8d85\u6807), \u518d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574\u3002
    # \u300c\u672a\u586b steps\u300d\u53ea\u662f\u4fe1\u606f\u7f3a\u5931, \u4e0d\u80fd\u76d6\u8fc7\u5df2\u7ecf\u67e5\u51fa\u7684\u4e0d\u5408\u683c\u9879, \u5426\u5219\u4f1a\u51fa\u73b0
    # \u300c\u53ea\u586b\u4e86\u6e29\u5ea6\u8d85\u6807, \u5374\u56e0\u4e3a\u6ca1\u586b\u6b65\u9aa4\u800c\u88ab\u5224\u6210\u5f85\u786e\u8ba4\u300d\u8fd9\u79cd\u628a\u98ce\u9669\u8bf4\u8f7b\u4e86\u7684\u60c5\u51b5\u3002
    defect_temp = fridge_ok is False or freezer_ok is False
    if order and not order_ok:
        level = '\u5b58\u5728\u4ea4\u53c9\u6c61\u67d3\u98ce\u9669'
    elif bad_p or defect_temp:
        level = '\u5b58\u5728\u8584\u5f31\u73af\u8282'
    elif not order or unk_p:
        level = '\u5f85\u786e\u8ba4'
    else:
        level = '\u64cd\u4f5c\u89c4\u8303'

    warns = []
    if not order:
        warns.append('\u672a\u586b\u5199\u64cd\u4f5c\u6b65\u9aa4\uff0c\u65e0\u6cd5\u5224\u65ad\u987a\u5e8f\uff0c\u8bf7\u6309\u5148\u6d17\u83dc -> \u518d\u5207\u751f\u8089 -> \u6700\u540e\u5207\u719f\u98df\u6838\u5bf9')
    elif not order_ok:
        if len(order) < len(CORRECT_ORDER):
            warns.append('\u64cd\u4f5c\u987a\u5e8f\u4e0d\u5b8c\u6574\uff0c\u6b63\u786e\u987a\u5e8f\u5e94\u4e3a\uff1a\u5148\u6d17\u83dc -> \u518d\u5207\u751f\u8089 -> \u6700\u540e\u5207\u719f\u98df')
        else:
            warns.append('\u64cd\u4f5c\u987a\u5e8f\u9519\u8bef\uff0c\u6b63\u786e\u987a\u5e8f\u5e94\u4e3a\uff1a\u5148\u6d17\u83dc -> \u518d\u5207\u751f\u8089 -> \u6700\u540e\u5207\u719f\u98df\uff0c'
                         '\u5f53\u524d\u6267\u884c\u4e3a %s' % ' -> '.join(order))
    for b in bad_p:
        desc = next(c[2] for c in ORDER_CHECKS if c[1] == b)
        warns.append('\u4e0d\u5408\u683c\uff1a%s\uff08%s\uff09' % (b, desc))
    for u in unk_p:
        warns.append('\u672a\u68c0\u67e5\uff1a%s\uff0c\u5efa\u8bae\u9010\u9879\u786e\u8ba4' % u)
    if fridge_ok is False:
        warns.append('\u51b7\u85cf\u5ba4\u6e29\u5ea6\u8d85\u6807\uff08%.1f \u6444\u6c0f\u5ea6\uff0c\u9ad8\u4e8e 4 \u6444\u6c0f\u5ea6\uff09\uff0c'
                     '\u7ec6\u83cc\u5728 4 \u81f3 60 \u6444\u6c0f\u5ea6\u533a\u95f4\u4f1a\u5feb\u901f\u7e41\u6b96' % float(fridge_t))
    if freezer_ok is False:
        warns.append('\u51b7\u51bb\u5ba4\u6e29\u5ea6\u8d85\u6807\uff08%.1f \u6444\u6c0f\u5ea6\uff0c\u9ad8\u4e8e\u8d1f 18 \u6444\u6c0f\u5ea6\uff09\uff0c\u51b7\u51bb\u6548\u679c\u4e0b\u964d')

    if bad_p or not order_ok or fridge_ok is False or freezer_ok is False:
        advises = list(PRACTICES)
    else:
        advises = []

    return {
        'level': level,
        'order': order,
        'order_ok': order_ok,
        'practice_rows': rows_p,
        'bad': bad_p,
        'unchecked': unk_p,
        'temp_rows': temp_rows,
        'warns': warns,
        'advises': advises,
        'order_detail': [{'key': k, 'name': n, 'how': h, 'wrong': w}
                         for k, n, h, w in ORDER_DETAIL],
        'boards': [{'color': c, 'use': u, 'note': nt} for c, u, nt in BOARD_ZONES],
        'pathogens': [{'key': k, 'name': n, 'source': s, 'ignore': i}
                      for k, n, s, i in PATHOGENS],
        'high_risk': [{'group': g, 'note': nt} for g, nt in HIGH_RISK],
        'banned': BANNED,
    }


def render_md(r):
    L = []
    L.append('# \u98df\u7269\u4ea4\u53c9\u6c61\u67d3\u4e0e\u751f\u719f\u5206\u5f00\u6838\u67e5')
    L.append('')
    L.append('## \u4e00\u3001\u603b\u4f53\u5224\u5b9a')
    L.append('')
    L.append('**%s**' % r['level'])
    L.append('')
    L.append('## \u4e8c\u3001\u64cd\u4f5c\u987a\u5e8f\uff08\u6838\u5fc3\uff09')
    L.append('')
    L.append('**\u6b63\u786e\u987a\u5e8f\uff1a\u5148\u6d17\u83dc -> \u518d\u5207\u751f\u8089 -> \u6700\u540e\u5207\u719f\u98df**')
    L.append('')
    L.append('| \u6b65\u9aa4 | \u8bf4\u660e | \u5e38\u89c1\u9519\u8bef |')
    L.append('|---|---|---|')
    for o in r['order_detail']:
        L.append('| %s | %s | %s |' % (o['name'], o['how'], o['wrong']))
    L.append('')
    L.append('\u672c\u6b21\u5b9e\u9645\u64cd\u4f5c\u987a\u5e8f\uff1a%s\uff08%s\uff09'
             % (' -> '.join(r['order']) if r['order'] else '\u672a\u586b\u5199',
                '\u6b63\u786e' if r['order_ok'] else '**\u987a\u5e8f\u6709\u8bef\u6216\u6b65\u9aa4\u4e0d\u5b8c\u6574**'))
    L.append('')
    L.append('## \u4e09\u3001\u7827\u677f\u989c\u8272\u5206\u533a')
    L.append('')
    L.append('| \u989c\u8272 | \u7528\u9014 | \u6ce8\u610f |')
    L.append('|---|---|---|')
    for b in r['boards']:
        L.append('| %s | %s | %s |' % (b['color'], b['use'], b['note']))
    L.append('')
    L.append('## \u56db\u3001\u68c0\u67e5\u9879')
    L.append('')
    L.append('| \u68c0\u67e5\u9879 | \u72b6\u6001 | \u8bf4\u660e |')
    L.append('|---|---|---|')
    for p in r['practice_rows']:
        L.append('| %s | %s | %s |' % (p['name'], p['status'], p['desc']))
    L.append('')
    L.append('## \u4e94\u3001\u6e29\u5ea6\u6838\u67e5')
    L.append('')
    if r['temp_rows']:
        L.append('| \u90e8\u4f4d | \u5b9e\u6d4b | \u4e0a\u9650 | \u72b6\u6001 | \u8bf4\u660e |')
        L.append('|---|---|---|---|---|')
        for t in r['temp_rows']:
            L.append('| %s | %.1f \u6444\u6c0f\u5ea6 | %.1f \u6444\u6c0f\u5ea6 | %s | %s |'
                     % (t['name'], t['value'], t['limit'], t['status'], t['note']))
    else:
        L.append('- \u672a\u586b\u5199\u6e29\u5ea6\u6570\u636e')
    L.append('')
    L.append('## \u516d\u3001\u5e38\u89c1\u81f4\u75c5\u83cc')
    L.append('')
    L.append('| \u81f4\u75c5\u83cc | \u4e3b\u8981\u6765\u6e90 | \u6613\u88ab\u5ffd\u89c6\u4e4b\u5904 |')
    L.append('|---|---|---|')
    for p in r['pathogens']:
        L.append('| %s | %s | %s |' % (p['name'], p['source'], p['ignore']))
    L.append('')
    L.append('## \u4e03\u3001\u9ad8\u98ce\u9669\u4eba\u7fa4\u8b66\u793a')
    L.append('')
    L.append('| \u4eba\u7fa4 | \u6ce8\u610f |')
    L.append('|---|---|')
    for h in r['high_risk']:
        L.append('| %s | %s |' % (h['group'], h['note']))
    L.append('')
    L.append('## \u516b\u3001\u751f\u719f\u5206\u5f00\u7684\u5177\u4f53\u505a\u6cd5')
    L.append('')
    if r['advises']:
        for p in r['advises']:
            L.append('- %s' % p)
    else:
        L.append('- \u5f53\u524d\u672a\u53d1\u73b0\u660e\u663e\u98ce\u9669\uff0c\u6309\u4e0a\u8ff0\u505a\u6cd5\u4fdd\u6301\u5373\u53ef')
    L.append('')
    L.append('## \u4e5d\u3001\u660e\u786e\u7981\u6b62\u7684\u64cd\u4f5c')
    L.append('')
    for b in r['banned']:
        L.append('- %s' % b)
    L.append('')
    L.append('## \u5341\u3001\u63d0\u793a')
    L.append('')
    if r['warns']:
        for w in r['warns']:
            L.append('- %s' % w)
    else:
        L.append('- \u672a\u53d1\u73b0\u98ce\u9669\u9879\uff0c\u4fdd\u6301\u73b0\u6709\u64cd\u4f5c\u4e60\u60ef')
    L.append('')
    L.append('## \u5341\u4e00\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] \u64cd\u4f5c\u987a\u5e8f\u4e3a\u5148\u6d17\u83dc -> \u518d\u5207\u751f\u8089 -> \u6700\u540e\u5207\u719f\u98df')
    L.append('- [ ] \u7827\u677f\u6309\u989c\u8272\u5206\u533a\uff0c\u751f\u8089\u7827\u677f\u672a\u5207\u719f\u98df')
    L.append('- [ ] \u5904\u7406\u751f\u8089\u540e\u5df2\u7528\u7682\u6db2\u6d17\u624b')
    L.append('- [ ] \u751f\u98df\u653e\u4e0b\u5c42\uff0c\u5373\u98df\u653e\u4e0a\u5c42\uff0c\u6709\u6ef4\u6db2\u9694\u79bb')
    L.append('- [ ] \u89e3\u51bb\u6c34\u4e0e\u8840\u6c34\u5df2\u5012\u6389\uff0c\u5bb9\u5668\u5df2\u6e05\u6d17')
    L.append('- [ ] \u51c9\u62cc\u83dc\u4e0e\u5373\u98df\u98df\u54c1\u672a\u4e0e\u751f\u98df\u4ea4\u53c9\u63a5\u89e6')
    L.append('- [ ] \u51b7\u85cf\u4e0d\u9ad8\u4e8e 4 \u6444\u6c0f\u5ea6\uff0c\u51b7\u51bb\u4e0d\u9ad8\u4e8e\u8d1f 18 \u6444\u6c0f\u5ea6')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    # 1 \u6b63\u786e\u987a\u5e8f
    r1 = calc({'steps': ['wash_veg', 'cut_raw_meat', 'cut_cooked']})
    ck(r1['order_ok'] is True, '\u5148\u6d17\u83dc->\u5207\u751f\u8089->\u5207\u719f\u98df\u5e94\u6b63\u786e\uff0c\u5b9e\u4e3a %s' % r1['order_ok'])
    ck(r1['level'] == '\u5f85\u786e\u8ba4', '\u987a\u5e8f\u5bf9\u4f46\u672a\u586b\u68c0\u67e5\u9879\u5e94\u4e3a\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r1['level'])

    # 2 \u9519\u8bef\u987a\u5e8f: \u5148\u5207\u751f\u8089\u540e\u6d17\u83dc
    r2 = calc({'steps': ['cut_raw_meat', 'wash_veg', 'cut_cooked']})
    ck(r2['order_ok'] is False, '\u5148\u5207\u751f\u8089\u518d\u6d17\u83dc\u5e94\u5224\u9519\u8bef\uff0c\u5b9e\u4e3a %s' % r2['order_ok'])
    ck(r2['level'] == '\u5b58\u5728\u4ea4\u53c9\u6c61\u67d3\u98ce\u9669', '\u987a\u5e8f\u9519\u8bef\u5e94\u5224\u98ce\u9669\uff0c\u5b9e\u4e3a %s' % r2['level'])
    ck(any('\u64cd\u4f5c\u987a\u5e8f\u9519\u8bef' in w for w in r2['warns']), '\u5e94\u62a5\u987a\u5e8f\u9519\u8bef\uff0c\u5b9e\u4e3a %s' % r2['warns'])

    # 3 \u6b65\u9aa4\u4e0d\u5b8c\u6574
    r3 = calc({'steps': ['cut_cooked', 'wash_veg']})
    ck(r3['order_ok'] is False, '\u7f3a\u6b65\u9aa4\u5e94\u5224\u987a\u5e8f\u4e0d\u5b8c\u6574\uff0c\u5b9e\u4e3a %s' % r3['order_ok'])
    ck(any('\u4e0d\u5b8c\u6574' in w for w in r3['warns']), '\u5e94\u62a5\u987a\u5e8f\u4e0d\u5b8c\u6574\uff0c\u5b9e\u4e3a %s' % r3['warns'])

    # 4 \u5168\u5408\u683c
    allok = {k: True for k, _, _ in ORDER_CHECKS}
    r4 = calc({'steps': ['wash_veg', 'cut_raw_meat', 'cut_cooked'], 'practices': allok,
               'fridge_temp': 3, 'freezer_temp': -20})
    ck(r4['level'] == '\u64cd\u4f5c\u89c4\u8303', '\u5168\u90e8\u5408\u683c\u5e94\u5224\u64cd\u4f5c\u89c4\u8303\uff0c\u5b9e\u4e3a %s' % r4['level'])
    ck(len(r4['temp_rows']) == 2, '\u6e29\u5ea6\u5e94\u4e24\u884c\uff0c\u5b9e\u4e3a %d' % len(r4['temp_rows']))
    ck(all(t['status'] == '\u8fbe\u6807' for t in r4['temp_rows']), '\u6e29\u5ea6\u5e94\u5168\u90e8\u8fbe\u6807')

    # 5 \u51b7\u85cf\u8d85\u6807
    r5 = calc({'practices': allok, 'fridge_temp': 8})
    ck(r5['level'] == '\u5b58\u5728\u8584\u5f31\u73af\u8282', '\u51b7\u85cf\u8d85\u6807\u5e94\u5224\u8584\u5f31\u73af\u8282\uff0c\u5b9e\u4e3a %s' % r5['level'])
    ck(any('\u51b7\u85cf\u5ba4\u6e29\u5ea6\u8d85\u6807' in w for w in r5['warns']), '\u5e94\u62a5\u51b7\u85cf\u8d85\u6807\uff0c\u5b9e\u4e3a %s' % r5['warns'])

    # 6 \u6e29\u5ea6\u8fb9\u754c: 4 \u5ea6\u8fbe\u6807, 4.1 \u8d85\u6807
    ck(calc({'fridge_temp': 4})['temp_rows'][0]['status'] == '\u8fbe\u6807', '4 \u6444\u6c0f\u5ea6\u5e94\u8fbe\u6807')
    ck(calc({'fridge_temp': 4.5})['temp_rows'][0]['status'] == '\u8d85\u6807', '4.5 \u6444\u6c0f\u5ea6\u5e94\u8d85\u6807')
    ck(calc({'freezer_temp': -18})['temp_rows'][0]['status'] == '\u8fbe\u6807', '\u8d1f 18 \u6444\u6c0f\u5ea6\u5e94\u8fbe\u6807')
    ck(calc({'freezer_temp': -15})['temp_rows'][0]['status'] == '\u8d85\u6807', '\u8d1f 15 \u6444\u6c0f\u5ea6\u5e94\u8d85\u6807')

    # 7 \u68c0\u67e5\u9879\u4e0d\u5408\u683c
    r7 = calc({'practices': dict(allok, hand_washed=False)})
    ck(r7['level'] == '\u5b58\u5728\u8584\u5f31\u73af\u8282', '\u6d17\u624b\u4e0d\u5408\u683c\u5e94\u5224\u8584\u5f31\u73af\u8282\uff0c\u5b9e\u4e3a %s' % r7['level'])
    ck('\u5904\u7406\u751f\u8089\u540e\u6d17\u624b' in r7['bad'], '\u5e94\u70b9\u540d\u6d17\u624b\u9879\uff0c\u5b9e\u4e3a %s' % r7['bad'])
    ck(len(r7['advises']) == len(PRACTICES), '\u6709\u98ce\u9669\u65f6\u5e94\u7ed9\u51fa\u5168\u90e8\u505a\u6cd5\u5efa\u8bae')

    # 8 \u81f4\u75c5\u83cc\u8981\u70b9
    pnames = [p[1] for p in PATHOGENS]
    for nm in ('\u6c99\u95e8\u6c0f\u83cc', '\u674e\u65af\u7279\u83cc', '\u5f2f\u66f2\u83cc'):
        ck(nm in pnames, '\u5fc5\u987b\u542b%s' % nm)
    ck(any('\u52a0\u70ed\u4e0d\u80fd\u7834\u574f' in p[3] for p in PATHOGENS), '\u5fc5\u987b\u542b\u8010\u70ed\u6bd2\u7d20\u8bf4\u660e')
    ck(any('\u4ec5\u51b2\u6d17\u4e0d\u80fd\u6740\u706d' in p[3] for p in PATHOGENS), '\u5fc5\u987b\u542b\u51b2\u6d17\u4e0d\u80fd\u6740\u706d\u7684\u8bf4\u660e')

    # 9 \u7827\u677f\u5206\u533a\u4e0e\u751f\u719f\u505a\u6cd5
    ck(len(BOARD_ZONES) >= 5, '\u7827\u677f\u5206\u533a\u81f3\u5c11 5 \u6863\uff0c\u5b9e\u4e3a %d' % len(BOARD_ZONES))
    ck(any('\u6309\u989c\u8272\u5206\u533a' in p for p in PRACTICES), '\u505a\u6cd5\u5fc5\u987b\u542b\u6309\u989c\u8272\u5206\u533a')
    ck(any('\u7528\u7682\u6db2\u6d17\u624b' in p for p in PRACTICES), '\u505a\u6cd5\u5fc5\u987b\u542b\u6d17\u624b')
    ck(any('\u5e95\u90e8\u6216\u4e13\u7528\u5bc6\u95ed\u5bb9\u5668' in p for p in PRACTICES), '\u505a\u6cd5\u5fc5\u987b\u542b\u51b0\u7bb1\u9694\u79bb\u5b58\u653e')

    # 10 \u9ad8\u98ce\u9669\u4eba\u7fa4
    hgroups = [h[0] for h in HIGH_RISK]
    for g in ('\u5a74\u5e7c\u513f', '\u5b55\u5987', '65 \u5c81\u4ee5\u4e0a\u8001\u4eba', '\u514d\u75ab\u529b\u4f4e\u4e0b\u8005'):
        ck(g in hgroups, '\u9ad8\u98ce\u9669\u4eba\u7fa4\u5fc5\u987b\u542b%s' % g)

    # 11 \u7981\u6b62\u9879
    ck(len(BANNED) >= 8, '\u7981\u6b62\u9879\u81f3\u5c11 8 \u6761\uff0c\u5b9e\u4e3a %d' % len(BANNED))

    # 12 BOM \u4e24\u6761\u8def\u5f84
    bom = '\ufeff{"steps": ["wash_veg", "cut_cooked"], "fridge_temp": 6}'
    r12 = calc(json.loads(bom.lstrip('\ufeff')))
    ck(r12['order_ok'] is False, 'BOM \u8f93\u5165\u5e94\u6b63\u786e\u89e3\u6790\u4e14\u987a\u5e8f\u4e0d\u5b8c\u6574\uff0c\u5b9e\u4e3a %s' % r12['order_ok'])
    ck(r12['temp_rows'][0]['value'] == 6.0, '\u6e29\u5ea6\u5e94\u89e3\u6790\u4e3a 6\uff0c\u5b9e\u4e3a %s' % r12['temp_rows'][0]['value'])
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe8.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps({'steps': ['cut_cooked', 'cut_raw_meat', 'wash_veg']}))
    try:
        r12b = calc(json.loads(open(tmp, 'r', encoding='utf-8-sig').read()))
        ck(r12b['order_ok'] is False, 'utf-8-sig \u8bfb\u53d6\u5e94\u6b63\u5e38\uff0c\u53cd\u5e8f\u5e94\u5224\u9519\uff0c\u5b9e\u4e3a %s' % r12b['order_ok'])
        ck(r12b['order'][0] == 'cut_cooked', '\u5e94\u4fdd\u7559\u5b9e\u9645\u6267\u884c\u987a\u5e8f\uff0c\u5b9e\u4e3a %s' % r12b['order'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 13 \u975e\u6cd5\u8f93\u5165
    for bad, why in (
        ({'steps': ['\u4e0d\u5b58\u5728\u7684\u6b65\u9aa4']}, '\u672a\u77e5\u6b65\u9aa4'),
        ({'steps': '\u4e0d\u662f\u5217\u8868'}, 'steps \u975e\u5217\u8868'),
        ({'practices': '\u4e0d\u662f\u5bf9\u8c61'}, 'practices \u975e\u5bf9\u8c61'),
        ({'practices': {'\u4e0d\u5b58\u5728\u7684\u9879': True}}, '\u672a\u77e5\u68c0\u67e5\u9879'),
    ):
        try:
            calc(bad)
            ck(False, '\u7528\u4f8b13 %s \u5e94\u629b\u9519' % why)
        except ValueError:
            ck(True, '')

    # 14 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r2)
    for key in ('\u64cd\u4f5c\u987a\u5e8f', '\u7827\u677f\u989c\u8272\u5206\u533a', '\u5e38\u89c1\u81f4\u75c5\u83cc', '\u9ad8\u98ce\u9669\u4eba\u7fa4\u8b66\u793a',
                '\u751f\u719f\u5206\u5f00\u7684\u5177\u4f53\u505a\u6cd5', '\u660e\u786e\u7981\u6b62', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355'):
        ck(key in md, 'Markdown \u8f93\u51fa\u5e94\u542b\u7ae0\u8282 %s' % key)
    ck(len(r2['practice_rows']) == 8, '\u68c0\u67e5\u9879\u5e94 8 \u6761\uff0c\u5b9e\u4e3a %d' % len(r2['practice_rows']))

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    msg = 'SELFTEST FAIL\n' + '\n'.join(errs) if errs else (
        'SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u6b63\u786e\u987a\u5e8f/\u987a\u5e8f\u9519\u8bef/\u6b65\u9aa4\u4e0d\u5b8c\u6574/\u5168\u5408\u683c/\u51b7\u85cf\u8d85\u6807/'
        '\u6e29\u5ea6\u8fb9\u754c\u503c(4 \u4e0e 4.5\u3001\u8d1f 18 \u4e0e\u8d1f 15)/\u68c0\u67e5\u9879\u4e0d\u5408\u683c/\u81f4\u75c5\u83cc\u8981\u70b9/\u7827\u677f\u5206\u533a/'
        '\u751f\u719f\u505a\u6cd5/\u9ad8\u98ce\u9669\u4eba\u7fa4/\u7981\u6b62\u9879/BOM \u4e24\u6761\u8def\u5f84/\u975e\u6cd5\u8f93\u5165/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u98df\u7269\u4ea4\u53c9\u6c61\u67d3\u4e0e\u751f\u719f\u5206\u5f00\u6838\u67e5')
    ap.add_argument('--file', help='\u8f93\u5165 JSON \u6587\u4ef6')
    ap.add_argument('--text', help='\u8f93\u5165 JSON \u5b57\u7b26\u4e32')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'])
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    raw = a.text or ''
    if a.file:
        if not os.path.exists(a.file):
            print('ERROR --file \u4e0d\u5b58\u5728: %s' % a.file)
            return 2
        raw = open(a.file, 'r', encoding='utf-8-sig', errors='replace').read()
    if not raw.strip():
        print('ERROR \u9700\u8981 --file \u6216 --text')
        return 2
    try:
        data = json.loads(raw.lstrip('\ufeff'))
    except ValueError as e:
        print('ERROR JSON \u89e3\u6790\u5931\u8d25: %s' % e)
        return 2
    try:
        r = calc(data)
    except ValueError as e:
        print('ERROR %s' % e)
        return 2

    out = render_md(r) if a.format == 'md' else json.dumps(r, ensure_ascii=False, indent=2)
    d = os.path.dirname(os.path.abspath(__file__))
    target = a.out or os.path.join(d, '_last_result.txt')
    with open(target, 'w', encoding='utf-8') as f:
        f.write(out + '\n')
    print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % target)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())


