# -*- coding: utf-8 -*-
"""\u9ad8\u538b\u9505\u4f7f\u7528\u4e0e\u5b89\u5168\u6838\u67e5\uff1a\u6309\u98df\u6750\u5339\u914d\u538b\u529b\u6863\u4f4d\uff0c\u8f93\u51fa\u5b89\u5168\u7ea2\u7ebf\u81ea\u68c0\u4e0e\u5f02\u5e38\u505c\u7528\u5224\u5b9a\u3002

\u7528\u6cd5:
  python pressure_cooker_check.py --file cooker.json [--out result.md] [--format json]
  python pressure_cooker_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u98df\u6750 -> (\u4e2d\u6587\u540d, \u5efa\u8bae\u538b\u529b\u6863\u4f4d, \u662f\u5426\u6613\u5835\u53e3, \u662f\u5426\u9700\u8981\u9884\u6cc4\u538b, \u5173\u952e\u7981\u5fcc)
# \u538b\u529b\u6863\u4f4d: \u4f4e\u538b / \u4e2d\u538b / \u9ad8\u538b
FOODS = {
    'leafy_veg': ('\u7eff\u53f6\u852c\u83dc', '\u4f4e\u538b', True, False,
                '\u4f53\u79ef\u5927\u6613\u5835\u9650\u538b\u9600\uff0c\u9700\u4e0b\u538b\u91cf\u63a7\u5236\uff0c\u52ff\u88c5\u6ee1'),
    'potato': ('\u571f\u8c46\u4e0e\u6839\u830e', '\u4e2d\u538b', True, False,
              '\u6dc0\u7c89\u7c7b\u6613\u7cca\u5e95\u5835\u585e\uff0c\u6392\u6c14\u53e3\u987b\u7545\u901a'),
    'beans': ('\u8c46\u7c7b\u4e0e\u8c46\u5236\u54c1', '\u4e2d\u538b', True, False,
              '\u8c46\u7c7b\u6613\u4ea7\u751f\u6ce1\u6cab\u9876\u8d77\u9650\u538b\u9600\uff0c\u9700\u7559\u8db3\u7a7a\u95f4\u5e76\u5206\u6279'),
    'meat': ('\u8089\u7c7b', '\u9ad8\u538b', False, True,
             '\u9700\u5b8c\u5168\u53bb\u9664\u538b\u529b\u540e\u624d\u80fd\u5f00\u76d6'),
    'bones': ('\u6392\u9aa8\u4e0e\u5e26\u9aa8\u8089', '\u9ad8\u538b', False, True,
              '\u9aa8\u6e23\u53ef\u80fd\u5835\u585e\u6392\u6c14\u53e3\uff0c\u52ff\u8d85\u91cf'),
    'seafood': ('\u6d77\u9c9c\u4e0e\u8d1d\u7c7b', '\u4e2d\u538b', True, True,
                '\u6d77\u9c9c\u6613\u8d77\u6ce1\u9876\u9600\uff0c\u5347\u6e29\u9636\u6bb5\u987b\u76ef\u7740\u9650\u538b\u9600'),
    'whole_fish': ('\u6574\u9c7c', '\u4e2d\u538b', True, True,
                   '\u6574\u9c7c\u6613\u5835\u585e\uff0c\u5347\u6e29\u65f6\u987b\u5168\u7a0b\u770b\u7ba1'),
    'noodle': ('\u9762\u6761\u4e0e\u7c73\u7ebf', '\u4f4e\u538b', True, False,
               '\u6613\u7cca\u5e95\uff0c\u5347\u6e29\u5feb\u9700\u5c0f\u706b'),
    'rice_water': ('\u7c73\u996d\u4e0e\u7ca5', '\u4f4e\u538b', False, False,
                   '\u6613\u6ea2\u9505\uff0c\u52ff\u8d85\u8fc7\u5185\u9505\u5bb9\u79ef\u4e0a\u9650\u7ebf'),
    'egg': ('\u9e21\u86cb', '\u9ad8\u538b', False, True,
            '\u5e26\u58f3\u9e21\u86cb\u9700\u5b8c\u5168\u6cc4\u538b\uff0c\u9aa4\u7136\u5f00\u76d6\u4f1a\u7206\u88c2'),
    'corn': ('\u7389\u7c73\u4e0e\u6839\u830e\u7c7b', '\u4e2d\u538b', False, False,
             '\u7389\u7c73\u6613\u81a8\u80c0\u9876\u9600\uff0c\u88c5\u91cf\u4e0d\u5b9c\u8fc7\u591a'),
    'noodle_dumpling': ('\u901f\u51bb\u6c34\u997a', '\u4f4e\u538b', True, False,
                        '\u6613\u5835\u53e3\uff0c\u4e14\u901f\u98df\u672c\u8eab\u65e0\u9700\u9ad8\u538b'),
}

# \u538b\u529b\u6863\u4f4d\u4e0e\u98df\u6750\u5339\u914d\u8bf4\u660e
PRESSURE_NOTE = {
    '\u4f4e\u538b': '\u7ea6 80 \u5343\u5e15\uff0c\u9002\u7528\u4e8e\u53f6\u83dc\u3001\u9762\u6761\u3001\u7c73\u996d\u7ca5\u7c7b\u7b49\u6613\u719f\u6216\u6613\u7cca\u98df\u6750',
    '\u4e2d\u538b': '\u7ea6 100 \u5343\u5e15\uff0c\u9002\u7528\u4e8e\u6839\u830e\u3001\u8c46\u7c7b\u3001\u6d77\u9c9c\u7b49\u9700\u8981\u9002\u4e2d\u538b\u529b\u7684\u98df\u6750',
    '\u9ad8\u538b': '\u7ea6 120 \u5343\u5e15\uff0c\u9002\u7528\u4e8e\u8089\u7c7b\u3001\u5e26\u9aa8\u8089\u3001\u5e26\u58f3\u86cb\u7b49\u9700\u8981\u5feb\u901f\u719f\u900f\u7684\u98df\u6750',
}

# \u5b89\u5168\u7ea2\u7ebf\u81ea\u68c0\u9879: (\u9879\u76ee, \u8bf4\u660e, \u4e0d\u5408\u683c\u65f6\u7684\u5904\u7f6e)
RED_LINES = [
    ('limit_valve', '\u9650\u538b\u9600\u901a\u7545',
     '\u9650\u538b\u9600\u5835\u585e\u662f\u9ad8\u538b\u9505\u6700\u5371\u9669\u7684\u6545\u969c\u4e4b\u4e00\uff0c\u4f1a\u5bfc\u81f4\u9505\u5185\u538b\u529b\u65e0\u6cd5\u91ca\u653e'),
    ('safety_valve', '\u5b89\u5168\u9600\u901a\u7545\u4e14\u672a\u6539\u52a8',
     '\u5b89\u5168\u9600\u88ab\u66ff\u6362\u3001\u62c6\u9664\u6216\u6539\u52a8\u4f5c\u4e1a\u4f1a\u5bfc\u81f4\u538b\u529b\u65e0\u6cd5\u91ca\u653e\uff0c\u5c5e\u4e25\u91cd\u5b89\u5168\u9690\u60a3'),
    ('gasket', '\u5bc6\u5c01\u5708\u5b8c\u597d\u65e0\u8001\u5316',
     '\u5bc6\u5c01\u5708\u8001\u5316\u3001\u53d8\u5f62\u6216\u88c2\u7eb9\u4f1a\u5bfc\u81f4\u5c01\u53e3\u4e0d\u4e25\uff0c\u538b\u529b\u6cc4\u6f0f\u6216\u84b8\u6c7d\u5916\u6ea2\u70eb\u4f24'),
    ('weight', '\u914d\u91cd\u5757\u9f50\u5168\u4e14\u672a\u53d8\u5f62',
     '\u914d\u91cd\u5757\u7f3a\u5931\u6216\u53d8\u5f62\u4f1a\u5bfc\u81f4\u538b\u529b\u6863\u4f4d\u4e0d\u51c6\uff0c\u84b8\u6c7d\u6cc4\u6f0f\u6216\u538b\u529b\u5931\u63a7'),
    ('vent_clear', '\u6392\u6c14\u53e3\u65e0\u906e\u6321',
     '\u6392\u6c14\u53e3\u88ab\u6bdb\u5dfe\u3001\u9505\u5177\u6216\u98df\u7269\u6b8b\u6e23\u5835\u585e\u4f1a\u5bfc\u81f4\u538b\u529b\u65e0\u6cd5\u91ca\u653e'),
    ('fill_level', '\u88c5\u91cf\u672a\u8d85\u8fc7\u4e0a\u9650\u7ebf',
     '\u8d85\u8fc7\u5185\u9505\u5bb9\u79ef\u4e0a\u9650\u7ebf\u4f1a\u5bfc\u81f4\u6cb8\u817e\u65f6\u6ce1\u6cab\u9876\u8d77\u9650\u538b\u9600\uff0c\u538b\u529b\u5931\u63a7'),
    ('seal_clean', '\u9505\u76d6\u4e0e\u9505\u53e3\u5df2\u6e05\u6d01',
     '\u9505\u53e3\u6709\u98df\u7269\u6b8b\u6e23\u4f1a\u5bfc\u81f4\u5bc6\u5c01\u4e0d\u4e25\uff0c\u84b8\u6c7d\u4ece\u7f1d\u9699\u55b7\u51fa\u70eb\u4f24'),
    ('valve_clean', '\u9650\u538b\u9600\u4e0e\u5b89\u5168\u9600\u5df2\u5b9a\u671f\u6e05\u6d17',
     '\u9600\u5b54\u79ef\u57a2\u4f1a\u5bfc\u81f4\u538b\u529b\u91ca\u653e\u4e0d\u7545\uff0c\u662f\u538b\u529b\u8868\u5f02\u5e38\u7684\u5e38\u89c1\u539f\u56e0'),
    ('age', '\u4f7f\u7528\u5e74\u9650\u5728\u4ea7\u54c1\u8bf4\u660e\u8303\u56f4\u5185',
     '\u8d85\u671f\u670d\u5f79\u7684\u8001\u5316\u90e8\u4ef6\u53ef\u80fd\u5931\u6548\uff0c\u5e94\u6309\u4ea7\u54c1\u8bf4\u660e\u66f4\u6362\u6574\u673a\u6216\u90e8\u4ef6'),
    ('base_flat', '\u9505\u4f53\u5e95\u5ea7\u4e0e\u7076\u9762\u8d34\u5408\u7a33\u5b9a',
     '\u5e95\u5ea7\u53d8\u5f62\u6216\u60ac\u7a7a\u4f1a\u5bfc\u81f4\u53d7\u70ed\u4e0d\u5747\uff0c\u538b\u529b\u6ce2\u52a8\u5f02\u5e38'),
]

# \u5fc5\u987b\u7acb\u5373\u505c\u7528\u5e76\u8f6c\u4e13\u4e1a\u7ef4\u4fee\u7684\u60c5\u5f62
STOP_USE = [
    '\u542c\u5230\u5f02\u5e38\u566a\u97f3\u3001\u5c16\u9510\u5578\u53eb\u6216\u9505\u4f53\u5267\u70c8\u9707\u52a8',
    '\u538b\u529b\u8868\u6307\u9488\u4e0d\u5f52\u96f6\u3001\u4e0d\u6446\u52a8\u6216\u660e\u663e\u6296\u52a8',
    '\u9650\u538b\u9600\u6216\u5b89\u5168\u9600\u5835\u585e\u3001\u9508\u6b7b\u3001\u5361\u6ede',
    '\u5bc6\u5c01\u5708\u8001\u5316\u5f00\u88c2\u3001\u53d8\u5f62\u6216\u7f3a\u5931',
    '\u9505\u4f53\u53d8\u5f62\u3001\u5e95\u90e8\u51f9\u9677\u3001\u710a\u70b9\u6e17\u6f0f',
    '\u6392\u6c14\u53e3\u5835\u585e\u6216\u84b8\u6c7d\u4ece\u975e\u6392\u6c14\u53e3\u4f4d\u7f6e\u55b7\u51fa',
    '\u4f7f\u7528\u65f6\u9505\u76d6\u65e0\u6cd5\u9501\u7d27\u6216\u6709\u660e\u663e\u7f1d\u9699',
]

# \u660e\u786e\u7981\u6b62\u7684\u64cd\u4f5c
BANNED = [
    '\u4e25\u7981\u5728\u538b\u529b\u672a\u5b8c\u5168\u91ca\u653e\u65f6\u5f3a\u884c\u5f00\u76d6',
    '\u4e25\u7981\u5e26\u538b\u5f00\u76d6\u6216\u7528\u5de5\u5177\u5f3a\u884c\u6273\u52a8\u9505\u76d6',
    '\u4e25\u7981\u5835\u585e\u6392\u6c14\u53e3\u6216\u5728\u5176\u4e0a\u8986\u76d6\u4efb\u4f55\u7269\u54c1',
    '\u4e25\u7981\u6539\u88c5\u3001\u62c6\u9664\u6216\u66ff\u6362\u5b89\u5168\u9600\u4e0e\u9650\u538b\u9600',
    '\u4e25\u7981\u8d85\u8fc7\u7ea2\u7ebf\u88c5\u91cf\u6216\u8d85\u8fc7\u5185\u9505\u4e0a\u9650\u7ebf',
    '\u4e25\u7981\u4f7f\u7528\u8d85\u8fc7\u4ea7\u54c1\u8bf4\u660e\u5e74\u9650\u7684\u9505\u5177\u7ee7\u7eed\u4f5c\u4e1a',
    '\u4e25\u7981\u5728\u65e0\u4eba\u770b\u7ba1\u72b6\u6001\u4e0b\u52a0\u70ed',
    '\u4e25\u7981\u7528\u9ad8\u538b\u9505\u70f9\u716e\u6613\u4ea7\u751f\u5927\u91cf\u6ce1\u6cab\u800c\u4e0d\u7559\u6392\u6c14\u7684\u98df\u6750',
]

# \u505c\u706b\u540e\u51b7\u5374\u8981\u6c42
COOLING = (
    '\u542c\u5230\u5f02\u5e38\u566a\u97f3\u6216\u51fa\u73b0\u538b\u529b\u5f02\u5e38\u65f6\uff0c\u5e94\u7acb\u5373\u505c\u706b\u5e76\u81ea\u7136\u51b7\u5374\u3002'
    '\u4e25\u7981\u5f3a\u884c\u5f00\u76d6\u3001\u4e25\u7981\u7528\u51b7\u6c34\u6d47\u6dcb\u9505\u4f53\u52a0\u901f\u51b7\u5374\u3002'
    '\u81ea\u7136\u51b7\u5374\u8fc7\u7a0b\u4e2d\u9650\u538b\u9600\u4ecd\u53ef\u80fd\u55b7\u51fa\u84b8\u6c7d\uff0c\u5e94\u4fdd\u6301\u4eba\u5458\u5728\u573a\u5e76\u907f\u5f00\u6392\u6c14\u53e3\u65b9\u5411\u3002'
    '\u786e\u8ba4\u538b\u529b\u8868\u6307\u9488\u5b8c\u5168\u5f52\u96f6\u3001\u9650\u538b\u9600\u4e0d\u518d\u55b7\u6c14\u540e\uff0c\u65b9\u53ef\u6309\u8bf4\u660e\u4e66\u5f00\u76d6\u3002'
)


def norm(k):
    return str(k or '').strip().lower().replace(' ', '')


def food_of(key):
    k = norm(key)
    if k not in FOODS:
        raise ValueError('\u672a\u77e5\u98df\u6750\u952e: %s\uff0c\u53ef\u9009\u952e\u89c1 FOODS \u8868' % key)
    return k, FOODS[k]


def check_redlines(checks):
    """checks: {\u9879\u76ee\u952e: True/False/None}; None \u89c6\u4e3a\u672a\u68c0\u67e5\u3002"""
    rows = []
    bad = []
    unk = []
    for key, name, why in RED_LINES:
        v = checks.get(key)
        if v is None:
            rows.append((name, '\u672a\u68c0\u67e5', why))
            unk.append(name)
        elif v:
            rows.append((name, '\u5408\u683c', why))
        else:
            rows.append((name, '\u4e0d\u5408\u683c', why))
            bad.append(name)
    return rows, bad, unk


def calc(data):
    checks = data.get('checks') or {}
    if not isinstance(checks, dict):
        raise ValueError('checks \u5fc5\u987b\u662f\u5bf9\u8c61')
    for k in checks:
        if not any(norm(r[0]) == norm(k) for r in RED_LINES):
            raise ValueError('\u672a\u77e5\u7684\u81ea\u68c0\u9879: %s\uff0c\u53ef\u9009\u9879\u89c1 RED_LINES \u8868' % k)

    rows, bad, unk = check_redlines(checks)

    items = data.get('items') or []
    food_rows = []
    if items:
        for it in items:
            key, (name, press, clog, deflate, ban) = food_of(it.get('food'))
            used = it.get('pressure') or press
            if used not in ('\u4f4e\u538b', '\u4e2d\u538b', '\u9ad8\u538b'):
                raise ValueError('pressure \u53ea\u80fd\u586b \u4f4e\u538b/\u4e2d\u538b/\u9ad8\u538b\uff0c\u5b9e\u4e3a: %s' % used)
            food_rows.append({
                'name': it.get('name', name),
                'food': key,
                'food_name': name,
                'recommended': press,
                'used': used,
                'match': used == press,
                'clog_risk': clog,
                'deflate_needed': deflate,
                'ban': ban,
                'pressure_note': PRESSURE_NOTE[press],
            })
        food_rows.sort(key=lambda r: (0 if not r['match'] else 1, 0 if r['clog_risk'] else 1))

    if len(bad) >= 1:
        level = '\u7981\u6b62\u4f7f\u7528'
    elif unk:
        level = '\u5f85\u786e\u8ba4'
    else:
        level = '\u53ef\u6b63\u5e38\u4f7f\u7528'

    warns = []
    why_map = {r[1]: (r[0], r[2]) for r in RED_LINES}
    for b in bad:
        key, why = why_map[b]
        warns.append('\u81ea\u68c0\u4e0d\u5408\u683c\uff1a%s\uff08%s\uff09\uff0c\u5fc5\u987b\u5148\u5904\u7406\u518d\u4f7f\u7528\uff1a%s' % (key, b, why))
    for u in unk:
        warns.append('\u81ea\u68c0\u672a\u5b8c\u6210\uff1a%s\uff0c\u672a\u786e\u8ba4\u524d\u4e0d\u8981\u5f00\u59cb\u52a0\u70ed' % u)
    for r in food_rows:
        if not r['match']:
            warns.append('%s \u4f7f\u7528%s\uff0c\u5efa\u8bae\u4e3a%s\uff1a%s'
                         % (r['name'], r['used'], r['recommended'],
                            PRESSURE_NOTE[r['recommended']]))
        if r['clog_risk']:
            warns.append('%s \u5c5e\u6613\u5835\u53e3\u98df\u6750\uff0c\u5347\u6e29\u9636\u6bb5\u987b\u5168\u7a0b\u770b\u7ba1\u9650\u538b\u9600' % r['name'])
        if r['deflate_needed']:
            warns.append('%s \u5fc5\u987b\u5b8c\u5168\u91ca\u653e\u538b\u529b\u540e\u624d\u80fd\u5f00\u76d6\uff0c\u4e25\u7981\u5e26\u538b\u5f00\u76d6' % r['name'])

    return {
        'level': level,
        'redline_rows': [{'name': n, 'status': s, 'why': w} for n, s, w in rows],
        'bad': bad,
        'unchecked': unk,
        'items': food_rows,
        'warns': warns,
        'banned': BANNED,
        'stop_use': STOP_USE,
        'cooling': COOLING,
    }


def render_md(r):
    L = []
    L.append('# \u9ad8\u538b\u9505\u4f7f\u7528\u4e0e\u5b89\u5168\u6838\u67e5')
    L.append('')
    L.append('## \u4e00\u3001\u603b\u4f53\u5224\u5b9a')
    L.append('')
    L.append('**%s**' % r['level'])
    L.append('')
    if r['level'] == '\u7981\u6b62\u4f7f\u7528':
        L.append('\u5b58\u5728\u81ea\u68c0\u4e0d\u5408\u683c\u9879\uff0c**\u5148\u5904\u7406\u518d\u4f7f\u7528**\uff0c\u4e0d\u8981\u5f00\u59cb\u52a0\u70ed\u3002')
    elif r['level'] == '\u5f85\u786e\u8ba4':
        L.append('\u5b58\u5728\u672a\u5b8c\u6210\u7684\u81ea\u68c0\u9879\uff0c\u672a\u786e\u8ba4\u524d\u4e0d\u8981\u5f00\u59cb\u52a0\u70ed\u3002')
    else:
        L.append('\u5341\u9879\u81ea\u68c0\u5168\u90e8\u5408\u683c\uff0c\u53ef\u6309\u98df\u6750\u5339\u914d\u7684\u538b\u529b\u6863\u4f4d\u6b63\u5e38\u4f7f\u7528\u3002')
    L.append('')
    L.append('## \u4e8c\u3001\u5b89\u5168\u7ea2\u7ebf\u81ea\u68c0\uff08\u5341\u9879\uff09')
    L.append('')
    L.append('| \u81ea\u68c0\u9879 | \u72b6\u6001 | \u4e3a\u4ec0\u4e48\u91cd\u8981 |')
    L.append('|---|---|---|')
    for x in r['redline_rows']:
        L.append('| %s | %s | %s |' % (x['name'], x['status'], x['why']))
    L.append('')
    L.append('## \u4e09\u3001\u98df\u6750\u4e0e\u538b\u529b\u6863\u4f4d\u5339\u914d')
    L.append('')
    if r['items']:
        L.append('| \u98df\u6750 | \u5efa\u8bae\u6863\u4f4d | \u5b9e\u9645\u6863\u4f4d | \u5339\u914d | \u6613\u5835\u53e3 | \u9700\u5b8c\u5168\u6cc4\u538b | \u5173\u952e\u7981\u5fcc |')
        L.append('|---|---|---|---|---|---|---|')
        for x in r['items']:
            L.append('| %s | %s | %s | %s | %s | %s | %s |'
                     % (x['name'], x['recommended'], x['used'],
                        '\u662f' if x['match'] else '**\u5426**',
                        '\u662f' if x['clog_risk'] else '\u5426',
                        '\u662f' if x['deflate_needed'] else '\u5426', x['ban']))
        L.append('')
        L.append('\u538b\u529b\u6863\u4f4d\u8bf4\u660e\uff1a')
        L.append('')
        for k in ('\u4f4e\u538b', '\u4e2d\u538b', '\u9ad8\u538b'):
            L.append('- %s\uff1a%s' % (k, PRESSURE_NOTE[k]))
    else:
        L.append('- \u672a\u586b\u5199\u98df\u6750\u8bb0\u5f55')
    L.append('')
    L.append('## \u56db\u3001\u5fc5\u987b\u7acb\u5373\u505c\u7528\u5e76\u8f6c\u4e13\u4e1a\u7ef4\u4fee\u7684\u60c5\u5f62')
    L.append('')
    for s in r['stop_use']:
        L.append('- %s' % s)
    L.append('')
    L.append('## \u4e94\u3001\u660e\u786e\u7981\u6b62\u7684\u64cd\u4f5c')
    L.append('')
    for b in r['banned']:
        L.append('- %s' % b)
    L.append('')
    L.append('## \u516d\u3001\u505c\u706b\u540e\u51b7\u5374\u8981\u6c42')
    L.append('')
    L.append('- %s' % r['cooling'])
    L.append('')
    L.append('## \u4e03\u3001\u63d0\u793a')
    L.append('')
    if r['warns']:
        for w in r['warns']:
            L.append('- %s' % w)
    else:
        L.append('- \u672a\u53d1\u73b0\u81ea\u68c0\u4e0d\u5408\u683c\u9879\uff0c\u6309\u538b\u529b\u6863\u4f4d\u5339\u914d\u8868\u4f7f\u7528\u5373\u53ef')
    L.append('')
    L.append('## \u516b\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] \u5341\u9879\u5b89\u5168\u7ea2\u7ebf\u81ea\u68c0\u5df2\u9010\u9879\u786e\u8ba4')
    L.append('- [ ] \u9505\u5177\u672a\u8d85\u8fc7\u4ea7\u54c1\u8bf4\u660e\u7684\u4f7f\u7528\u5e74\u9650')
    L.append('- [ ] \u88c5\u91cf\u672a\u8d85\u8fc7\u5185\u9505\u4e0a\u9650\u7ebf\uff0c\u7559\u6709\u4f59\u91cf')
    L.append('- [ ] \u6392\u6c14\u53e3\u4e0e\u9650\u538b\u9600\u65b9\u5411\u65e0\u906e\u6321\uff0c\u4e14\u5df2\u907f\u5f00\u9762\u90e8\u4e0e\u8eab\u4f53')
    L.append('- [ ] \u52a0\u70ed\u5168\u7a0b\u6709\u4eba\u770b\u7ba1\uff0c\u672a\u79bb\u5f00\u73b0\u573a')
    L.append('- [ ] \u672a\u51fa\u73b0\u5f02\u5e38\u566a\u97f3\u5373\u5df2\u505c\u706b\uff0c\u672a\u5f3a\u884c\u5f00\u76d6')
    L.append('- [ ] \u5f00\u76d6\u524d\u538b\u529b\u5df2\u5b8c\u5168\u5f52\u96f6')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    # 1 \u5168\u90e8\u5408\u683c -> \u53ef\u6b63\u5e38\u4f7f\u7528
    allok = {k: True for k, _, _ in RED_LINES}
    r1 = calc({'checks': allok})
    ck(r1['level'] == '\u53ef\u6b63\u5e38\u4f7f\u7528', '\u5341\u9879\u5168\u5408\u683c\u5e94\u53ef\u6b63\u5e38\u4f7f\u7528\uff0c\u5b9e\u4e3a %s' % r1['level'])
    ck(len(r1['redline_rows']) == 10, '\u7ea2\u7ebf\u5e94 10 \u9879\uff0c\u5b9e\u4e3a %d' % len(r1['redline_rows']))

    # 2 \u9650\u538b\u9600\u4e0d\u5408\u683c -> \u7981\u6b62\u4f7f\u7528
    r2 = calc({'checks': dict(allok, limit_valve=False)})
    ck(r2['level'] == '\u7981\u6b62\u4f7f\u7528', '\u9650\u538b\u9600\u4e0d\u5408\u683c\u5e94\u7981\u6b62\u4f7f\u7528\uff0c\u5b9e\u4e3a %s' % r2['level'])
    ck('\u9650\u538b\u9600\u901a\u7545' in r2['bad'], '\u5e94\u70b9\u540d\u9650\u538b\u9600\uff0c\u5b9e\u4e3a %s' % r2['bad'])
    ck(any('\u5835\u585e' in w for w in r2['warns']), '\u5e94\u8bf4\u660e\u9650\u538b\u9600\u5835\u585e\u98ce\u9669\uff0c\u5b9e\u4e3a %s' % r2['warns'])

    # 3 \u672a\u68c0\u67e5 -> \u5f85\u786e\u8ba4
    r3 = calc({'checks': {k: True for k, _, _ in RED_LINES if k != 'gasket'}})
    ck(r3['level'] == '\u5f85\u786e\u8ba4', '\u7f3a\u9879\u5e94\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r3['level'])
    ck('\u5bc6\u5c01\u5708\u5b8c\u597d\u65e0\u8001\u5316' in r3['unchecked'], '\u5e94\u5217\u51fa\u672a\u786e\u8ba4\u7684\u5bc6\u5c01\u5708\uff0c\u5b9e\u4e3a %s' % r3['unchecked'])

    # 4 \u5bc6\u5c01\u5708\u8001\u5316\u7981\u6b62
    r4 = calc({'checks': dict(allok, gasket=False)})
    ck(r4['level'] == '\u7981\u6b62\u4f7f\u7528', '\u5bc6\u5c01\u5708\u4e0d\u5408\u683c\u5e94\u7981\u6b62\u4f7f\u7528')
    ck(any('\u8001\u5316' in w or '\u53d8\u5f62' in w for w in r4['warns']), '\u5e94\u8bf4\u660e\u5bc6\u5c01\u5708\u8001\u5316\u98ce\u9669\uff0c\u5b9e\u4e3a %s' % r4['warns'])

    # 5 \u98df\u6750\u538b\u529b\u5339\u914d
    r5 = calc({'checks': allok, 'items': [
        {'food': 'meat'}, {'food': 'leafy_veg'}, {'food': 'beans'}]})
    byname = {x['name']: x for x in r5['items']}
    ck(byname['\u8089\u7c7b']['recommended'] == '\u9ad8\u538b', '\u8089\u7c7b\u5e94\u9ad8\u538b\uff0c\u5b9e\u4e3a %s' % byname['\u8089\u7c7b']['recommended'])
    ck(byname['\u7eff\u53f6\u852c\u83dc']['recommended'] == '\u4f4e\u538b', '\u7eff\u53f6\u852c\u83dc\u5e94\u4f4e\u538b\uff0c\u5b9e\u4e3a %s' % byname['\u7eff\u53f6\u852c\u83dc']['recommended'])
    ck(byname['\u8c46\u7c7b\u4e0e\u8c46\u5236\u54c1']['recommended'] == '\u4e2d\u538b', '\u8c46\u7c7b\u5e94\u4e2d\u538b\uff0c\u5b9e\u4e3a %s' % byname['\u8c46\u7c7b\u4e0e\u8c46\u5236\u54c1']['recommended'])
    ck(byname['\u8089\u7c7b']['deflate_needed'] is True, '\u8089\u7c7b\u987b\u5b8c\u5168\u6cc4\u538b')
    ck(byname['\u8c46\u7c7b\u4e0e\u8c46\u5236\u54c1']['clog_risk'] is True, '\u8c46\u7c7b\u5e94\u6807\u6613\u5835\u53e3')

    # 6 \u538b\u529b\u4e0d\u5339\u914d\u544a\u8b66
    r6 = calc({'checks': allok, 'items': [{'food': 'meat', 'pressure': '\u4f4e\u538b'}]})
    ck(r6['items'][0]['match'] is False, '\u8089\u7c7b\u7528\u4f4e\u538b\u5e94\u5224\u4e0d\u5339\u914d')
    ck(any('\u5efa\u8bae\u4e3a\u9ad8\u538b' in w for w in r6['warns']), '\u5e94\u7ed9\u51fa\u5efa\u8bae\u6863\u4f4d\uff0c\u5b9e\u4e3a %s' % r6['warns'])

    # 7 \u7981\u6b62\u5f3a\u884c\u5f00\u76d6\u5fc5\u987b\u5728\u8f93\u51fa\u4e2d
    md = render_md(r2)
    ck('\u4e25\u7981' in md and '\u5f00\u76d6' in md, '\u8f93\u51fa\u5e94\u5305\u542b\u7981\u6b62\u5f3a\u884c\u5f00\u76d6\u7684\u7ea2\u7ebf')
    ck('\u505c\u706b\u540e\u51b7\u5374\u8981\u6c42' in md, '\u8f93\u51fa\u5e94\u542b\u505c\u706b\u540e\u51b7\u5374\u8981\u6c42\u7ae0\u8282')

    # 8 \u6392\u5e8f\uff1a\u4e0d\u5339\u914d\u5728\u524d
    r8 = calc({'checks': allok, 'items': [
        {'food': 'meat'}, {'food': 'beans', 'name': '\u7ea2\u8c46', 'pressure': '\u9ad8\u538b'}]})
    ck(r8['items'][0]['match'] is False, '\u4e0d\u5339\u914d\u9879\u5e94\u6392\u6700\u524d\uff0c\u5b9e\u4e3a %s' % r8['items'][0]['match'])

    # 9 BOM \u4e24\u6761\u8def\u5f84
    bom = '\ufeff{"checks": {"limit_valve": true, "safety_valve": true, "gasket": true, "weight": true, "vent_clear": true, "fill_level": true, "seal_clean": true, "valve_clean": true, "age": true, "base_flat": true}, "items": [{"food": "egg"}]}'
    r9 = calc(json.loads(bom.lstrip('\ufeff')))
    ck(r9['level'] == '\u53ef\u6b63\u5e38\u4f7f\u7528', 'BOM \u8f93\u5165\u5e94\u89e3\u6790\u51fa\u5341\u9879\uff0c\u5b9e\u4e3a\u7b49\u7ea7 %s' % r9['level'])
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe4.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps({'checks': dict(allok, base_flat=False)}))
    try:
        r9b = calc(json.loads(open(tmp, 'r', encoding='utf-8-sig').read()))
        ck(r9b['level'] == '\u7981\u6b62\u4f7f\u7528', 'utf-8-sig \u8bfb\u53d6\u5e94\u6b63\u5e38\uff0c\u5b9e\u4e3a %s' % r9b['level'])
        ck('\u9505\u4f53\u5e95\u5ea7\u4e0e\u7076\u9762\u8d34\u5408\u7a33\u5b9a' in r9b['bad'], '\u5e94\u70b9\u540d\u5e95\u5ea7\u9879\uff0c\u5b9e\u4e3a %s' % r9b['bad'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 10 \u975e\u6cd5\u8f93\u5165
    for bad, why in (
        ({'checks': {'\u4e0d\u5b58\u5728\u7684\u9879': True}}, '\u672a\u77e5\u81ea\u68c0\u9879'),
        ({'checks': allok, 'items': [{'food': '\u4e0d\u5b58\u5728\u7684\u98df\u6750'}]}, '\u672a\u77e5\u98df\u6750'),
        ({'checks': allok, 'items': [{'food': 'meat', 'pressure': '\u8d85\u9ad8\u538b'}]}, '\u975e\u6cd5\u6863\u4f4d'),
        ({'checks': '\u4e0d\u662f\u5bf9\u8c61'}, 'checks \u975e\u5bf9\u8c61'),
    ):
        try:
            calc(bad)
            ck(False, '\u7528\u4f8b10 %s \u5e94\u629b\u9519' % why)
        except ValueError:
            ck(True, '')

    # 11 \u505c\u7528\u60c5\u5f62\u4e0e\u7981\u6b62\u9879\u9f50\u5168
    ck(len(STOP_USE) >= 7, '\u505c\u7528\u60c5\u5f62\u81f3\u5c11 7 \u6761\uff0c\u5b9e\u4e3a %d' % len(STOP_USE))
    ck(len(BANNED) >= 8, '\u7981\u6b62\u64cd\u4f5c\u81f3\u5c11 8 \u6761\uff0c\u5b9e\u4e3a %d' % len(BANNED))
    ck(any('\u5f3a\u884c\u5f00\u76d6' in b for b in BANNED), '\u5fc5\u987b\u542b\u7981\u6b62\u5f3a\u884c\u5f00\u76d6')
    ck(any('\u5835\u585e\u6392\u6c14\u53e3' in b for b in BANNED), '\u5fc5\u987b\u542b\u7981\u6b62\u5835\u585e\u6392\u6c14\u53e3')
    ck('\u4e25\u7981\u7528\u51b7\u6c34\u6d47\u6dcb' in COOLING, '\u5fc5\u987b\u542b\u7981\u6b62\u51b7\u6c34\u6d47\u6dcb\u52a0\u901f\u51b7\u5374')

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    msg = 'SELFTEST FAIL\n' + '\n'.join(errs) if errs else (
        'SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u5341\u9879\u7ea2\u7ebf/\u4e0d\u5408\u683c\u7981\u6b62\u4f7f\u7528/\u672a\u68c0\u67e5\u5f85\u786e\u8ba4/\u5bc6\u5c01\u5708\u8001\u5316/'
        '\u538b\u529b\u6863\u4f4d\u5339\u914d/\u4e0d\u5339\u914d\u544a\u8b66/\u7981\u6b62\u5f3a\u884c\u5f00\u76d6\u8f93\u51fa/\u6392\u5e8f/BOM \u4e24\u6761\u8def\u5f84/\u975e\u6cd5\u8f93\u5165/\u505c\u7528\u4e0e\u7981\u6b62\u6e05\u5355\u5b8c\u6574\u6027' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u9ad8\u538b\u9505\u4f7f\u7528\u4e0e\u5b89\u5168\u6838\u67e5')
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
