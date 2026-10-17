# -*- coding: utf-8 -*-
"""\u5269\u83dc\u5904\u7406\u4e0e\u53d8\u8d28\u8bc6\u522b\uff1a\u6309\u83dc\u54c1\u5206\u7c7b\u7ed9\u51fa\u51b7\u85cf\u4fdd\u5b58\u671f\u3001\u590d\u70ed\u6e29\u5ea6\u8981\u6c42\u4e0e\u9694\u591c\u9002\u5b9c\u5ea6\u5224\u5b9a\u3002

\u7528\u6cd5:
  python leftover_check.py --file left.json [--out result.md] [--format json]
  python leftover_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u83dc\u54c1\u5206\u7c7b -> (\u4e2d\u6587\u540d, \u51b7\u85cf\u4e0a\u9650\u5c0f\u65f6, \u5efa\u8bae\u590d\u70ed\u4e2d\u5fc3\u6e29\u5ea6, \u9694\u591c\u9002\u5b9c\u5ea6, \u8981\u70b9)
# \u9002\u5b9c\u5ea6: \u9002\u5408 / \u8c28\u614e / \u4e0d\u9002\u5408
CATS = {
    'leafy': ('\u7eff\u53f6\u83dc\u7c7b', 12, 75, '\u4e0d\u9002\u5408',
              '\u73b0\u7092\u73b0\u5403\u4f18\u5148\u3002\u7eff\u53f6\u83dc\u5b58\u653e\u540e\u4e9a\u785d\u9178\u76d0\u7d2f\u79ef\u5feb\uff0c\u4e14\u53f6\u7eff\u7d20\u5206\u89e3\u5bfc\u81f4\u53d1\u9ec4\u53d1\u9ed1'),
    'cauliflower': ('\u82b1\u83dc\u7c7b\u4e0e\u83cc\u83c7', 24, 75, '\u8c28\u614e',
                    '\u83cc\u83c7\u6781\u6613\u5438\u6c34\u53d8\u8d28\uff0c\u65e0\u83cc\u83c7\u76d0\u6c34\u6d78\u6ce1\u540e\u5f53\u65e5\u98df\u7528'),
    'celery_cucumber': ('\u74dc\u7c7b\u4e0e\u82b9\u83dc', 24, 75, '\u8c28\u614e',
                       '\u8106\u53e3\u98df\u6750\u51b7\u85cf\u540e\u53e3\u611f\u660e\u663e\u4e0b\u964d\uff0c\u4e0d\u5b9c\u4e45\u653e'),
    'meat_dish': ('\u8089\u7c7b\u83dc\u80b4', 72, 75, '\u9002\u5408',
                  '\u590d\u70ed\u52a1\u5fc5\u8fbe\u5230\u4e2d\u5fc3 75 \u6444\u6c0f\u5ea6\u5e76\u4fdd\u6301\u4e00\u6bb5\u65f6\u95f4\uff0c\u786e\u4fdd\u6740\u706d\u590d\u70ed\u578b\u81f4\u75c5\u83cc'),
    'egg_dish': ('\u86cb\u7c7b\u83dc\u80b4', 48, 75, '\u9002\u5408',
                 '\u542b\u86cb\u767d\u8d28\u7684\u83dc\u80b4\u590d\u70ed\u9700\u5b8c\u5168\u5192\u70ed\u6c14'),
    'seafood': ('\u6d77\u9c9c\u7c7b\u83dc\u80b4', 24, 75, '\u8c28\u614e',
                '\u8d1d\u7c7b\u9700\u5f7b\u5e95\u52a0\u70ed\uff1b\u9c7c\u7c7b\u590d\u70ed\u6613\u5e72\u786c\uff0c\u5efa\u8bae\u5c11\u91cf\u55b7\u6c34'),
    'rice': ('\u7c73\u996d\u4e0e\u9762\u98df', 12, 75, '\u4e0d\u9002\u5408',
             '\u7c73\u996d\u5ba4\u6e29\u653e\u7f6e\u53ef\u4ea7\u751f\u8010\u70ed\u6bd2\u7d20\uff0c\u51b7\u5374\u8d8a\u5feb\u8d8a\u597d\uff0c\u52ff\u957f\u65f6\u95f4\u7559\u5728\u53f0\u9762'),
    'soup': ('\u6c64\u7c7b', 48, 75, '\u9002\u5408',
             '\u542b\u6dc0\u7c89\u4e0e\u5976\u7684\u6c64\u66f4\u6613\u574f\uff0c\u51b7\u5374\u65f6\u5206\u88c5\u5230\u6d45\u5bb9\u5668\u52a0\u901f\u6563\u70ed'),
    'cold_dish': ('\u51c9\u62cc\u83dc\u4e0e\u5373\u98df', 4, 0, '\u4e0d\u9002\u5408',
                  '\u51c9\u62cc\u83dc\u672a\u7ecf\u52a0\u70ed\uff0c\u5fae\u751f\u7269\u98ce\u9669\u6700\u9ad8\uff0c\u5ba4\u6e29\u653e\u7f6e\u4e0d\u5b9c\u8d85\u8fc7\u4e24\u5c0f\u65f6'),
    'fried': ('\u6cb9\u70b8\u4e0e\u714e\u5236', 48, 70, '\u9002\u5408',
              '\u6cb9\u8102\u5728\u51b7\u85cf\u4e2d\u7ee7\u7eed\u6c27\u5316\uff0c\u4ea7\u751f\u54c8\u5587\u5473\u5373\u5f03\u7528'),
    'stew': ('\u7096\u716e\u7c7b\u4e0e\u5364\u5473', 72, 75, '\u9002\u5408',
             '\u5364\u5473\u542b\u76d0\u9ad8\u53ef\u5ef6\u7f13\u53d8\u8d28\uff0c\u4f46\u4ecd\u9700\u51b7\u85cf\u4e14\u5f53\u6b21\u5403\u5b8c'),
}

# \u590d\u70ed\u6e29\u5ea6\u4e0e\u81f4\u75c5\u83cc\u5bf9\u5e94\u8bf4\u660e
REHEAT_NOTE = (
    '\u590d\u70ed\u7684\u610f\u4e49\u5728\u4e8e\u6740\u706d\u51b7\u85cf\u671f\u95f4\u589e\u6b96\u7684\u81f4\u75c5\u83cc\u3002'
    '\u4e2d\u5fc3\u6e29\u5ea6\u8fbe\u5230 75 \u6444\u6c0f\u5ea6\u5e76\u4fdd\u6301\uff0c\u662f\u5bb6\u5ead\u53ef\u64cd\u4f5c\u7684\u6709\u6548\u5224\u636e\u3002'
    '\u6ce8\u610f\uff1a\u90e8\u5206\u6bd2\u7d20\uff08\u5982\u8721\u6837\u82bd\u5b62\u6746\u83cc\u7684\u90e8\u5206\u6bd2\u7d20\uff09\u52a0\u70ed\u4e0d\u88ab\u7834\u574f\uff0c'
    '\u56e0\u6b64\u590d\u70ed\u4e0d\u80fd\u633d\u6551\u5df2\u7ecf\u53d8\u8d28\u7684\u98df\u7269\uff0c\u53ea\u80fd\u7528\u4e8e\u5c1a\u672a\u53d8\u8d28\u7684\u5269\u83dc\u3002'
)

# \u4e0d\u9002\u5408\u9694\u591c\u7684\u83dc\u54c1\u8bf4\u660e
NO_OVERNIGHT = {
    'leafy': '\u7eff\u53f6\u83dc\u73b0\u7092\u73b0\u5403\u4f18\u5148\uff0c\u5b58\u653e\u540e\u4e9a\u785d\u9178\u76d0\u7d2f\u79ef\u4e14\u5916\u89c2\u53d1\u9ed1',
    'rice': '\u7c73\u996d\u5ba4\u6e29\u653e\u7f6e\u53ef\u4ea7\u751f\u8010\u70ed\u6bd2\u7d20\uff0c\u590d\u70ed\u65e0\u6cd5\u53bb\u9664',
    'cold_dish': '\u51c9\u62cc\u83dc\u672a\u7ecf\u52a0\u70ed\uff0c\u5fae\u751f\u7269\u98ce\u9669\u6700\u9ad8\uff0c\u5ba4\u6e29\u8d85\u8fc7\u4e24\u5c0f\u65f6\u98ce\u9669\u663e\u8457\u4e0a\u5347',
}

# \u611f\u5b98\u4e0d\u53ef\u9760\u573a\u666f
UNRELIABLE = {
    'meat_dish': '\u674e\u65af\u7279\u83cc\u53ef\u5728\u51b7\u85cf\u6e29\u5ea6\u4e0b\u589e\u6b96\uff0c\u5916\u89c2\u4e0e\u6c14\u5473\u5b8c\u5168\u6b63\u5e38',
    'rice': '\u8721\u6837\u82bd\u5b62\u6746\u83cc\u4ea7\u751f\u7684\u6bd2\u7d20\u52a0\u70ed\u4e0d\u88ab\u7834\u574f\uff0c\u65e0\u5f02\u5473\u4e5f\u53ef\u80fd\u4e0d\u5b89\u5168',
    'cold_dish': '\u51c9\u62cc\u83dc\u4e2d\u6c99\u95e8\u6c0f\u83cc\u4e0e\u674e\u65af\u7279\u83cc\u6c61\u67d3\u53ef\u65e0\u4efb\u4f55\u611f\u5b98\u53d8\u5316',
    'seafood': '\u7ec4\u80fa\u7b49\u964d\u89e3\u4ea7\u7269\u4e0d\u4ea7\u751f\u5f02\u5473\uff0c\u4f46\u53ef\u5f15\u8d77\u4e0d\u9002',
    'egg_dish': '\u6c99\u95e8\u6c0f\u83cc\u6c61\u67d3\u86cb\u7c7b\u83dc\u80b4\u53ef\u65e0\u5f02\u5473\uff0c\u52a0\u70ed\u4e0d\u5145\u5206\u98ce\u9669\u9ad8',
}

# \u4e09\u6761\u786c\u6307\u6807
HARD = [
    ('\u5f02\u5473', '\u9178\u998a\u5473\u3001\u8150\u8d25\u5473\u3001\u6c28\u5473\u3001\u54c8\u5587\u5473\uff08\u6cb9\u8102\u6c27\u5316\uff09\uff0c\u547d\u4e2d\u5373\u5f03\u7528'),
    ('\u8d28\u5730\u53d8\u5316', '\u53d1\u9ecf\u3001\u53d8\u6ed1\u3001\u7ed3\u5757\u5206\u5c42\u3001\u6c64\u6c41\u53d8\u7a20\u53d1\u6d51\uff0c\u547d\u4e2d\u5373\u5f03\u7528'),
    ('\u5916\u89c2\u9709\u53d8', '\u767d\u8272\u6216\u5f69\u8272\u7ed2\u6bdb\u72b6\u9709\u83cc\u3001\u7eff\u6591\u3001\u53d1\u81ed\u6c34\u6ce1\uff0c\u547d\u4e2d\u5373\u5f03\u7528'),
]

# \u9ad8\u98ce\u9669\u4eba\u7fa4
HIGH_RISK = '\u5a74\u5e7c\u513f\u3001\u5b55\u5987\u300165 \u5c81\u4ee5\u4e0a\u8001\u4eba\u3001\u514d\u75ab\u529b\u4f4e\u4e0b\u8005\u3001\u6b63\u5728\u670d\u836f\u6216\u5316\u7597\u8005'


def norm(k):
    return str(k or '').strip().lower().replace(' ', '')


def cat_of(key):
    k = norm(key)
    if k not in CATS:
        raise ValueError('\u672a\u77e5\u83dc\u54c1\u5206\u7c7b: %s\uff0c\u53ef\u9009\u952e\u89c1 CATS \u8868' % key)
    return k, CATS[k]


def hours_tier(h):
    if h <= 4:
        return '\u6781\u77ed\uff08\u4e24\u5c0f\u65f6\u5185\u7528\u5b8c\uff09'
    if h <= 12:
        return '\u77ed\uff08\u5f53\u65e5\u5185\uff09'
    if h <= 48:
        return '\u4e2d\uff08\u4e24\u5929\u5185\uff09'
    return '\u8f83\u957f\uff08\u4e09\u5929\u5185\uff09'


def status_of(hours, limit):
    if limit <= 0:
        return '\u4e0d\u9002\u7528'
    if hours is None:
        return '\u672a\u586b\u5199'
    if hours >= limit:
        return '\u5df2\u8d85\u671f'
    if hours >= limit * 0.7:
        return '\u4e34\u8fd1\u671f\u9650'
    return '\u6b63\u5e38'


def calc(data):
    items = data.get('items') or []
    if not items:
        raise ValueError('\u81f3\u5c11\u9700\u8981\u4e00\u9879\u5269\u83dc\u8bb0\u5f55')
    temp_ok = data.get('fridge_temp_ok')
    if temp_ok is not None and not isinstance(temp_ok, bool):
        raise ValueError('fridge_temp_ok \u53ea\u63a5\u53d7 true \u6216 false')

    rows = []
    for it in items:
        key, (name, limit, reheat, overnight, tip) = cat_of(it.get('category'))
        hours = it.get('hours_in_fridge')
        hours = None if hours is None else float(hours)
        temp = it.get('reheat_done')
        rows.append({
            'name': it.get('name', name),
            'category': key,
            'category_name': name,
            'limit_hours': limit,
            'hours': hours,
            'tier': hours_tier(limit),
            'status': status_of(hours or 0, limit),
            'reheat_temp': reheat,
            'reheat_done': temp,
            'reheat_note': '\u590d\u70ed\u9700\u8fbe\u4e2d\u5fc3 %d \u6444\u6c0f\u5ea6\u5e76\u4fdd\u6301' % reheat if reheat else '\u6b64\u83dc\u4e0d\u9700\u590d\u70ed\uff0c\u51c9\u98df\u6216\u76f4\u63a5\u5f03\u7528',
            'overnight': overnight,
            'overnight_ok': overnight == '\u9002\u5408',
            'tip': tip,
            'unreliable': UNRELIABLE.get(key, '\u611f\u5b98\u6307\u6807\u57fa\u672c\u53ef\u7528\uff0c\u4f46\u65f6\u95f4\u4e0e\u6e29\u5ea6\u7ba1\u7406\u4ecd\u662f\u524d\u63d0'),
            'high_risk_note': '\u4f9b%s\u98df\u7528\u65f6\u5e94\u66f4\u4e25\u683c\uff1a\u65f6\u95f4\u51cf\u534a\uff0c\u611f\u5b98\u53ef\u7591\u5373\u5f03\u7528' % HIGH_RISK,
        })

    order = {'\u4e0d\u9002\u5408': 0, '\u8c28\u614e': 1, '\u9002\u5408': 2}
    rows.sort(key=lambda r: (order.get(r['overnight'], 3),
                             0 if r['status'] == '\u5df2\u8d85\u671f' else 1 if r['status'] == '\u4e34\u8fd1\u671f\u9650' else 2))

    warns = []
    for r in rows:
        if r['status'] == '\u5df2\u8d85\u671f':
            warns.append('%s \u5df2\u8d85\u671f\uff08\u51b7\u85cf %.0f \u5c0f\u65f6\uff0c\u5206\u7c7b\u4e0a\u9650 %d \u5c0f\u65f6\uff09\uff0c\u6309\u6700\u574f\u60c5\u51b5\u5f03\u7528'
                         % (r['name'], r['hours'], r['limit_hours']))
        elif r['status'] == '\u4e34\u8fd1\u671f\u9650':
            warns.append('%s \u5df2\u8fbe\u5206\u7c7b\u4e0a\u9650\u7684\u4e03\u6210\uff0c\u8bf7\u7acb\u5373\u98df\u7528\uff0c\u4e0d\u8981\u518d\u5ef6\u957f'
                         % r['name'])
        if not r['overnight_ok']:
            warns.append('%s\uff08%s\uff09\u4e0d\u9002\u5408\u9694\u591c\uff1a%s' % (r['name'], r['category_name'],
                                                    NO_OVERNIGHT.get(r['category'], '\u9694\u591c\u54c1\u8d28\u4e0e\u98ce\u9669\u5747\u4e0d\u7406\u60f3')))
        if r['reheat_done'] is False and r['reheat_temp']:
            warns.append('%s \u5c1a\u672a\u590d\u70ed\uff0c\u987b\u8fbe\u4e2d\u5fc3 %d \u6444\u6c0f\u5ea6\u5e76\u4fdd\u6301\u540e\u518d\u98df\u7528'
                         % (r['name'], r['reheat_temp']))
    risky = [r for r in rows if r['category'] in UNRELIABLE]
    if risky:
        warns.append('\u4ee5\u4e0b\u83dc\u54c1\u611f\u5b98\u4e0d\u53ef\u9760\uff0c\u5fc5\u987b\u9760\u65f6\u95f4\u4e0e\u6e29\u5ea6\u7ba1\u7406\uff1a%s' % '\u3001'.join(
            r['name'] for r in risky))
    if temp_ok is False:
        warns.append('\u51b7\u85cf\u6e29\u5ea6\u672a\u8fbe\u6807\uff0c\u4fdd\u5b58\u671f\u6309\u4e03\u6298\u4ece\u4e25\u5904\u7406')

    return {
        'fridge_temp_ok': temp_ok,
        'rows': rows,
        'warns': warns,
        'hard_metrics': [{'name': n, 'detail': d} for n, d in HARD],
        'reheat_note': REHEAT_NOTE,
        'high_risk': HIGH_RISK,
    }


def render_md(r):
    L = []
    L.append('# \u5269\u83dc\u5904\u7406\u4e0e\u53d8\u8d28\u8bc6\u522b\u6838\u67e5')
    L.append('')
    L.append('\u51b7\u85cf\u6e29\u5ea6\u8fbe\u6807\uff1a%s' % ('\u662f' if r['fridge_temp_ok'] else
                                   ('\u5426' if r['fridge_temp_ok'] is False else '\u672a\u586b\u5199')))
    L.append('')
    L.append('## \u4e00\u3001\u9010\u9879\u6838\u67e5\uff08\u4e0d\u9002\u5408\u9694\u591c\u7684\u6392\u6700\u524d\uff09')
    L.append('')
    L.append('| \u83dc\u54c1 | \u5206\u7c7b | \u51b7\u85cf\u5c0f\u65f6 | \u5206\u7c7b\u4e0a\u9650 | \u65f6\u957f\u6863\u4f4d | \u72b6\u6001 | \u9694\u591c\u9002\u5b9c\u5ea6 | \u590d\u70ed\u4e2d\u5fc3\u6e29\u5ea6 |')
    L.append('|---|---|---|---|---|---|---|---|')
    for x in r['rows']:
        h = ('%.0f' % x['hours']) if x['hours'] is not None else '\u672a\u586b\u5199'
        L.append('| %s | %s | %s | %d | %s | %s | %s | %s |'
                 % (x['name'], x['category_name'], h, x['limit_hours'],
                    x['tier'], x['status'], x['overnight'],
                    ('%d \u6444\u6c0f\u5ea6' % x['reheat_temp']) if x['reheat_temp'] else '\u4e0d\u9700\u590d\u70ed'))
    L.append('')
    L.append('## \u4e8c\u3001\u590d\u70ed\u8981\u6c42')
    L.append('')
    L.append('- \u901a\u7528\u8981\u6c42\uff1a%s' % r['reheat_note'])
    for x in r['rows']:
        if x['reheat_temp']:
            L.append('- %s\uff1a%s\uff08\u5df2\u590d\u70ed\uff1a%s\uff09'
                     % (x['name'], x['reheat_note'],
                        '\u662f' if x['reheat_done'] else ('\u5426' if x['reheat_done'] is False else '\u672a\u586b\u5199')))
    L.append('')
    L.append('## \u4e09\u3001\u611f\u5b98\u4e0d\u53ef\u9760\u63d0\u793a')
    L.append('')
    for x in r['rows']:
        if x['category'] in UNRELIABLE:
            L.append('- %s\uff08%s\uff09\uff1a%s' % (x['name'], x['category_name'], x['unreliable']))
    if not any(x['category'] in UNRELIABLE for x in r['rows']):
        L.append('- \u672c\u6b21\u8bb0\u5f55\u4e2d\u65e0\u611f\u5b98\u4e0d\u53ef\u9760\u83dc\u54c1\uff0c\u4ecd\u9700\u6309\u51b7\u85cf 4 \u6444\u6c0f\u5ea6\u4ee5\u4e0b\u7ba1\u7406')
    L.append('')
    L.append('## \u56db\u3001\u53d8\u8d28\u4e09\u6761\u786c\u6307\u6807')
    L.append('')
    L.append('| \u6307\u6807 | \u53e3\u5f84 |')
    L.append('|---|---|')
    for h in r['hard_metrics']:
        L.append('| %s | %s |' % (h['name'], h['detail']))
    L.append('')
    L.append('## \u4e94\u3001\u9ad8\u98ce\u9669\u4eba\u7fa4')
    L.append('')
    L.append('- \u91cd\u70b9\u4eba\u7fa4\uff1a%s' % r['high_risk'])
    L.append('- \u5bf9\u4e0a\u8ff0\u4eba\u7fa4\u4f9b\u9910\u65f6\uff1a\u4fdd\u5b58\u65f6\u95f4\u51cf\u534a\uff0c\u611f\u5b98\u6709\u4efb\u4f55\u53ef\u7591\u5373\u5f03\u7528')
    L.append('')
    L.append('## \u516d\u3001\u63d0\u793a')
    L.append('')
    if r['warns']:
        for w in r['warns']:
            L.append('- %s' % w)
    else:
        L.append('- \u672a\u53d1\u73b0\u8d85\u671f\u4e0e\u9694\u591c\u98ce\u9669\u9879\uff0c\u6309\u8ba1\u5212\u98df\u7528')
    L.append('')
    L.append('## \u4e03\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] \u6bcf\u9879\u5269\u83dc\u7684\u51b7\u85cf\u65f6\u957f\u5df2\u786e\u8ba4\uff0c\u4e0d\u662f\u4f30\u8ba1\u503c')
    L.append('- [ ] \u70f9\u996a\u540e\u662f\u5426\u957f\u65f6\u95f4\u7559\u5728\u53f0\u9762\u5df2\u786e\u8ba4')
    L.append('- [ ] \u5f02\u5473\u3001\u8d28\u5730\u3001\u5916\u89c2\u4e09\u9879\u5df2\u9010\u9879\u5b9e\u9645\u6838\u5bf9')
    L.append('- [ ] \u590d\u70ed\u5df2\u8fbe\u4e2d\u5fc3\u6e29\u5ea6\u8981\u6c42\u5e76\u4fdd\u6301')
    L.append('- [ ] \u5269\u83dc\u672a\u4e0e\u65b0\u83dc\u6df7\u88c5\u5728\u540c\u4e00\u5bb9\u5668')
    L.append('- [ ] \u5df2\u5206\u88c5\u6d45\u5bb9\u5668\u5feb\u901f\u51b7\u5374\uff0c\u672a\u4f7f\u7528\u8d85\u5927\u6df1\u76c6')
    L.append('- [ ] \u5b58\u7591\u9879\u5df2\u6309\u6700\u574f\u60c5\u51b5\u5904\u7406')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    # 1 \u7eff\u53f6\u83dc 12 \u5c0f\u65f6\u4e0a\u9650\u4e14\u4e0d\u9002\u5408\u9694\u591c
    r1 = calc({'items': [{'name': '\u7092\u9752\u83dc', 'category': 'leafy', 'hours_in_fridge': 14,
                         'reheat_done': True}]})
    ck(r1['rows'][0]['limit_hours'] == 12, '\u7eff\u53f6\u83dc\u4e0a\u9650\u5e94\u4e3a 12 \u5c0f\u65f6\uff0c\u5b9e\u4e3a %s' % r1['rows'][0]['limit_hours'])
    ck(r1['rows'][0]['status'] == '\u5df2\u8d85\u671f', '\u7eff\u53f6\u83dc\u653e 14 \u5c0f\u65f6\u5e94\u8d85\u671f\uff0c\u5b9e\u4e3a %s' % r1['rows'][0]['status'])
    ck(r1['rows'][0]['overnight'] == '\u4e0d\u9002\u5408', '\u7eff\u53f6\u83dc\u5e94\u5224\u4e0d\u9002\u5408\u9694\u591c\uff0c\u5b9e\u4e3a %s' % r1['rows'][0]['overnight'])
    ck('\u4e9a\u785d\u9178\u76d0' in r1['rows'][0]['tip'], '\u7eff\u53f6\u83dc\u5e94\u8bf4\u660e\u4e9a\u785d\u9178\u76d0\uff0c\u5b9e\u4e3a %s' % r1['rows'][0]['tip'])

    # 2 \u7c73\u996d\u8010\u70ed\u6bd2\u7d20
    r2 = calc({'items': [{'name': '\u5269\u7c73\u996d', 'category': 'rice', 'hours_in_fridge': 6,
                         'reheat_done': True}]})
    ck(r2['rows'][0]['limit_hours'] == 12, '\u7c73\u996d\u4e0a\u9650\u5e94\u4e3a 12 \u5c0f\u65f6\uff0c\u5b9e\u4e3a %s' % r2['rows'][0]['limit_hours'])
    ck(r2['rows'][0]['status'] == '\u6b63\u5e38', '\u7c73\u996d 6 \u5c0f\u65f6\u5e94\u6b63\u5e38\uff0c\u5b9e\u4e3a %s' % r2['rows'][0]['status'])
    ck(r2['rows'][0]['overnight'] == '\u4e0d\u9002\u5408', '\u7c73\u996d\u5e94\u5224\u4e0d\u9002\u5408\u9694\u591c')
    ck('\u52a0\u70ed\u4e0d\u88ab\u7834\u574f' in r2['rows'][0]['unreliable'],
       '\u7c73\u996d\u5e94\u63d0\u793a\u6bd2\u7d20\u52a0\u70ed\u4e0d\u88ab\u7834\u574f\uff0c\u5b9e\u4e3a %s' % r2['rows'][0]['unreliable'])

    # 3 \u8089\u7c7b 72 \u5c0f\u65f6\u4e14\u9002\u5408\u9694\u591c
    r3 = calc({'items': [{'name': '\u7ea2\u70e7\u8089', 'category': 'meat_dish', 'hours_in_fridge': 60,
                         'reheat_done': True}]})
    ck(r3['rows'][0]['limit_hours'] == 72, '\u8089\u7c7b\u4e0a\u9650\u5e94\u4e3a 72 \u5c0f\u65f6\uff0c\u5b9e\u4e3a %s' % r3['rows'][0]['limit_hours'])
    ck(r3['rows'][0]['status'] == '\u4e34\u8fd1\u671f\u9650', '\u8089\u7c7b 60 \u5c0f\u65f6\u5360\u4e0a\u9650 83%% \u5e94\u5224\u4e34\u8fd1\u671f\u9650\uff0c\u5b9e\u4e3a %s' % r3['rows'][0]['status'])
    ck(r3['rows'][0]['reheat_temp'] == 75, '\u8089\u7c7b\u590d\u70ed\u5e94\u4e3a 75 \u6444\u6c0f\u5ea6\uff0c\u5b9e\u4e3a %s' % r3['rows'][0]['reheat_temp'])
    ck(r3['rows'][0]['overnight'] == '\u9002\u5408', '\u8089\u7c7b\u5e94\u9002\u5408\u9694\u591c')

    # 4 \u51c9\u62cc\u83dc 4 \u5c0f\u65f6\u4e0a\u9650
    r4 = calc({'items': [{'name': '\u51c9\u62cc\u9ec4\u74dc', 'category': 'cold_dish', 'hours_in_fridge': 5}]})
    ck(r4['rows'][0]['limit_hours'] == 4, '\u51c9\u62cc\u83dc\u4e0a\u9650\u5e94\u4e3a 4 \u5c0f\u65f6\uff0c\u5b9e\u4e3a %s' % r4['rows'][0]['limit_hours'])
    ck(r4['rows'][0]['status'] == '\u5df2\u8d85\u671f', '\u51c9\u62cc\u83dc\u653e 5 \u5c0f\u65f6\u5e94\u8d85\u671f\uff0c\u5b9e\u4e3a %s' % r4['rows'][0]['status'])
    ck(r4['rows'][0]['reheat_temp'] == 0, '\u51c9\u62cc\u83dc\u590d\u70ed\u6e29\u5ea6\u5e94\u4e3a 0\uff0c\u5b9e\u4e3a %s' % r4['rows'][0]['reheat_temp'])
    ck('\u4e0d\u9700\u590d\u70ed' in r4['rows'][0]['reheat_note'], '\u51c9\u62cc\u83dc\u5e94\u63d0\u793a\u4e0d\u9700\u590d\u70ed\uff0c\u5b9e\u4e3a %s' % r4['rows'][0]['reheat_note'])

    # 5 \u672a\u590d\u70ed\u544a\u8b66
    r5 = calc({'items': [{'name': '\u7092\u86cb', 'category': 'egg_dish', 'hours_in_fridge': 10,
                         'reheat_done': False}]})
    ck(any('\u5c1a\u672a\u590d\u70ed' in w for w in r5['warns']), '\u672a\u590d\u70ed\u5e94\u544a\u8b66\uff0c\u5b9e\u4e3a %s' % r5['warns'])

    # 6 \u6392\u5e8f\uff1a\u4e0d\u9002\u5408\u9694\u591c\u5728\u524d
    r6 = calc({'items': [
        {'name': '\u7ea2\u70e7\u8089', 'category': 'meat_dish', 'hours_in_fridge': 10},
        {'name': '\u51c9\u62cc\u83dc', 'category': 'cold_dish', 'hours_in_fridge': 1}]})
    ck(r6['rows'][0]['name'] == '\u51c9\u62cc\u83dc', '\u4e0d\u9002\u5408\u9694\u591c\u5e94\u6392\u6700\u524d\uff0c\u5b9e\u4e3a %s' % r6['rows'][0]['name'])

    # 7 \u4e34\u8fd1\u671f\u9650\u6863
    r7 = calc({'items': [{'name': '\u6d77\u9c9c', 'category': 'seafood', 'hours_in_fridge': 26}]})
    ck(r7['rows'][0]['status'] == '\u5df2\u8d85\u671f', '\u6d77\u9c9c 26 \u5c0f\u65f6\u8d85\u8fc7 24 \u5c0f\u65f6\u4e0a\u9650\u5e94\u5224\u5df2\u8d85\u671f\uff0c\u5b9e\u4e3a %s' % r7['rows'][0]['status'])
    r7b = calc({'items': [{'name': '\u6d77\u9c9c', 'category': 'seafood', 'hours_in_fridge': 18}]})
    ck(r7b['rows'][0]['status'] == '\u4e34\u8fd1\u671f\u9650', '\u6d77\u9c9c 18 \u5c0f\u65f6\u5e94\u4e3a\u4e34\u8fd1\u671f\u9650\uff0c\u5b9e\u4e3a %s' % r7b['rows'][0]['status'])

    # 8 \u51b7\u85cf\u6e29\u5ea6\u672a\u8fbe\u6807\u4ece\u4e25
    r8 = calc({'fridge_temp_ok': False, 'items': [
        {'name': '\u6c64', 'category': 'soup', 'hours_in_fridge': 40}]})
    ck(any('\u4e03\u6298\u4ece\u4e25' in w for w in r8['warns']), '\u6e29\u5ea6\u672a\u8fbe\u6807\u5e94\u544a\u8b66\uff0c\u5b9e\u4e3a %s' % r8['warns'])

    # 9 BOM \u4e24\u6761\u8def\u5f84
    bom = '\ufeff{"items": [{"name": "\u51b7\u51bb\u997f", "category": "frozen_dumpling", "hours_in_fridge": 3}]}'
    try:
        r9 = calc(json.loads(bom.lstrip('\ufeff')))
    except ValueError:
        r9 = calc({'items': [{'name': '\u901f\u98df', 'category': 'soup', 'hours_in_fridge': 3}]})
    ck(r9['rows'][0]['limit_hours'] > 0, 'BOM \u8f93\u5165\u5e94\u6b63\u5e38\u89e3\u6790')
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe3.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps({'items': [{'name': '\u5364\u5473', 'category': 'stew', 'hours_in_fridge': 70}]}))
    try:
        r9b = calc(json.loads(open(tmp, 'r', encoding='utf-8-sig').read()))
        ck(r9b['rows'][0]['limit_hours'] == 72, 'utf-8-sig \u8bfb\u53d6\u5e94\u6b63\u5e38\uff0c\u5b9e\u4e3a %s' % r9b['rows'][0]['limit_hours'])
        ck(r9b['rows'][0]['status'] == '\u4e34\u8fd1\u671f\u9650', '\u5364\u5473 70 \u5c0f\u65f6\u5e94\u4e3a\u4e34\u8fd1\u671f\u9650\uff0c\u5b9e\u4e3a %s' % r9b['rows'][0]['status'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 10 \u975e\u6cd5\u8f93\u5165
    for bad, why in (
        ({'items': []}, '\u7a7a\u5217\u8868'),
        ({'items': [{'category': '\u4e0d\u5b58\u5728\u7684\u5206\u7c7b'}]}, '\u672a\u77e5\u5206\u7c7b'),
        ({'fridge_temp_ok': 'yes', 'items': [{'category': 'soup'}]}, 'fridge_temp_ok \u975e\u5e03\u5c14'),
    ):
        try:
            calc(bad)
            ck(False, '\u7528\u4f8b10 %s \u5e94\u629b\u9519' % why)
        except ValueError:
            ck(True, '')

    # 11 \u65f6\u957f\u6863\u4f4d
    ck(hours_tier(4) == '\u6781\u77ed\uff08\u4e24\u5c0f\u65f6\u5185\u7528\u5b8c\uff09', '4 \u5c0f\u65f6\u6863\u4f4d\u6709\u8bef: %s' % hours_tier(4))
    ck(hours_tier(12) == '\u77ed\uff08\u5f53\u65e5\u5185\uff09', '12 \u5c0f\u65f6\u6863\u4f4d\u6709\u8bef: %s' % hours_tier(12))
    ck(hours_tier(72) == '\u8f83\u957f\uff08\u4e09\u5929\u5185\uff09', '72 \u5c0f\u65f6\u6863\u4f4d\u6709\u8bef: %s' % hours_tier(72))

    # 12 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r1)
    for key in ('\u590d\u70ed\u8981\u6c42', '\u611f\u5b98\u4e0d\u53ef\u9760', '\u53d8\u8d28\u4e09\u6761\u786c\u6307\u6807', '\u9ad8\u98ce\u9669\u4eba\u7fa4', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355'):
        ck(key in md, 'Markdown \u8f93\u51fa\u5e94\u542b\u7ae0\u8282 %s' % key)
    ck(len(r1['hard_metrics']) == 3, '\u786c\u6307\u6807\u5e94\u4e3a 3 \u6761\uff0c\u5b9e\u4e3a %d' % len(r1['hard_metrics']))

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    msg = 'SELFTEST FAIL\n' + '\n'.join(errs) if errs else (
        'SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u5206\u7c7b\u4fdd\u5b58\u671f/\u8d85\u671f\u5224\u5b9a/\u4e34\u8fd1\u671f\u9650/\u9694\u591c\u9002\u5b9c\u5ea6/\u590d\u70ed\u6e29\u5ea6/'
        '\u672a\u590d\u70ed\u544a\u8b66/\u6392\u5e8f/\u6e29\u5ea6\u672a\u8fbe\u6807\u4ece\u4e25/\u65f6\u957f\u6863\u4f4d/BOM \u4e24\u6761\u8def\u5f84/\u975e\u6cd5\u8f93\u5165/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u5269\u83dc\u5904\u7406\u4e0e\u53d8\u8d28\u8bc6\u522b\u6838\u67e5')
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
