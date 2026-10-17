# -*- coding: utf-8 -*-
"""\u98df\u6750\u50a8\u5b58\u4fdd\u9c9c\u4e0e\u671f\u9650\u6838\u67e5\uff1a\u6309\u54c1\u7c7b\u7ed9\u51fa\u51b7\u85cf/\u51b7\u51bb\u4fdd\u5b58\u671f\u3001\u53d8\u8d28\u786c\u6307\u6807\u4e0e\u5904\u7f6e\u5efa\u8bae\u3002

\u7528\u6cd5:
  python food_storage_check.py --file store.json [--out result.md] [--format json]
  python food_storage_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u54c1\u7c7b -> (\u51b7\u85cf\u5929\u6570\u4e0a\u9650, \u51b7\u51bb\u5929\u6570\u4e0a\u9650, \u4fdd\u5b58\u8981\u70b9)
# \u5929\u6570\u4e0a\u9650\u4e3a\u5bb6\u5ead\u51b7\u85cf\u6761\u4ef6\u4e0b\u7684\u53c2\u8003\u503c\uff0c0 \u8868\u793a\u4e0d\u9002\u51b7\u51bb
SHELF = {
    'leafy': (3, 0, '\u53f6\u83dc\u7c7b\uff0c\u6d17\u51c0\u540e\u6781\u6613\u5438\u6c34\u70c2\u6839\uff0c\u5b9c\u64e6\u5e72\u6216\u57ab\u5438\u6c34\u7eb8\uff0c\u88c5\u900f\u6c14\u888b\u7559\u7f1d\u9699'),
    'root': (14, 120, '\u6839\u830e\u7c7b\uff08\u571f\u8c46\u6d0b\u8471\u7ea2\u85af\u5c71\u836f\uff09\uff0c\u9634\u51c9\u901a\u98ce\u4ea6\u53ef\u5b58\u653e\uff0c\u51b7\u85cf\u5ef6\u7f13\u53d1\u82bd'),
    'cabbage': (20, 60, '\u7ed3\u7403\u7c7b\u4e0e\u74dc\u7c7b\uff0c\u5b8c\u6574\u72b6\u6001\u8010\u5b58\uff0c\u5207\u5f00\u540e\u6309\u53f6\u83dc\u53e3\u5f84\u5904\u7406'),
    'mushroom': (3, 30, '\u83cc\u83c7\u7c7b\u6781\u6613\u5438\u6c34\uff0c\u98df\u7528\u524d\u624d\u6e05\u6d17\uff0c\u52ff\u4e0e\u5851\u6599\u819c\u957f\u65f6\u95f4\u5bc6\u5c01'),
    'meat': (3, 90, '\u751f\u8089\u79bd\uff0c\u51b7\u85cf\u4e0d\u8d85\u8fc7\u4e24\u5929\u66f4\u7a33\uff0c\u51b7\u51bb\u5206\u88c5\u5230\u7528\u5b8c\u4e3a\u6b62'),
    'poultry': (2, 90, '\u751f\u79bd\u8089\uff0c\u51b7\u85cf\u53e3\u5f84\u6bd4\u755c\u8089\u66f4\u77ed\uff0c\u52a1\u5fc5\u4e0e\u5373\u98df\u98df\u54c1\u5206\u683c'),
    'seafood_fish': (1, 90, '\u751f\u9c7c\uff0c\u51b7\u85cf\u4e00\u5929\u5185\u7528\u5b8c\u4e3a\u5b9c\uff0c\u51b7\u51bb\u524d\u5c3d\u91cf\u53bb\u5185\u810f\u8840\u6c34'),
    'seafood_shell': (1, 60, '\u8d1d\u7c7b\u6d77\u9c9c\uff0c\u5e26\u58f3\u9c9c\u6d3b\u4f18\u5148\u51b7\u85cf\uff0c\u5410\u6c99\u540e\u518d\u70f9\u8c03'),
    'egg': (30, 0, '\u5e26\u58f3\u51b7\u85cf\uff0c\u5c16\u7aef\u671d\u4e0b\uff0c\u4e0d\u6d17\u4e0d\u64e6\uff0c\u51b7\u51bb\u5e26\u58f3\u4f1a\u788e\u88c2'),
    'milk': (7, 30, '\u5df4\u6c0f\u5976\u5f00\u5c01\u540e\u6309\u6807\u7b7e\uff0c\u4e00\u822c\u4e09\u5230\u4e03\u5929\uff0c\u5f02\u5473\u7acb\u5373\u5f03'),
    'yogurt': (10, 60, '\u9178\u5976\u4e0e\u5976\u5236\u54c1\uff0c\u5f00\u5c01\u540e\u5c3d\u5feb\u5403\u5b8c\uff0c\u53d1\u9178\u6c14\u6ce1\u662f\u53d8\u8d28\u4fe1\u53f7'),
    'leftover': (3, 60, '\u719f\u98df\u5269\u83dc\uff0c\u7eff\u53f6\u83dc\u7c7b\u73b0\u7092\u73b0\u5403\u4f18\u5148\uff0c\u8be6\u89c1\u5269\u83dc\u5904\u7406\u53e3\u5f84'),
    'rice_noodle': (3, 60, '\u7c73\u996d\u9762\u6761\uff0c\u51c9\u900f\u540e\u5c3d\u5feb\u51b7\u85cf\uff0c\u5ba4\u6e29\u653e\u7f6e\u98ce\u9669\u9ad8'),
    'soup': (2, 60, '\u6c64\u7c7b\uff0c\u542b\u5976\u4e0e\u6dc0\u7c89\u7684\u6c64\u66f4\u6613\u574f\uff0c\u51b7\u5374\u8981\u5206\u6d45\u5bb9\u5668'),
    'opened_sauce': (30, 0, '\u5f00\u5c01\u9171\u6599\uff0c\u6309\u6807\u7b7e\u5f00\u5c01\u671f\uff0c\u51b7\u85cf\u907f\u5149\uff0c\u5f00\u5c01\u540e\u4e0d\u8fd4\u51b7\u85cf\u5ba4'),
    'opened_oil': (180, 0, '\u5f00\u5c01\u98df\u7528\u6cb9\uff0c\u907f\u5149\u5e38\u6e29\uff0c\u8fdc\u79bb\u7076\u53f0\uff0c\u51fa\u73b0\u54c8\u5587\u5473\u5f03\u7528'),
    'bakery': (5, 60, '\u9762\u5305\u7cd5\u70b9\uff0c\u542b\u5976\u6cb9\u7684\u66f4\u77ed\uff0c\u5bc6\u5c01\u4fdd\u5b58\u51cf\u7f13\u6c27\u5316'),
    'frozen_dumpling': (0, 120, '\u51b7\u51bb\u9762\u70b9\u4e0e\u901f\u98df\uff0c\u751f\u719f\u5206\u5f00\u5305\u88c5\uff0c\u9632\u6b62\u4e32\u5473\u4e0e\u7834\u635f'),
    'ice_cream': (0, 0, '\u51b0\u6dc7\u6dcb\uff0c\u6309\u5305\u88c5\u6807\u6ce8\uff0c\u878d\u5316\u540e\u4e0d\u5f97\u518d\u51bb'),
    'cut_fruit': (2, 0, '\u5207\u5f00\u7684\u6c34\u679c\u4e0e\u679c\u76d8\uff0c\u6c27\u5316\u5feb\u4e14\u6613\u88ab\u4e8c\u6b21\u6c61\u67d3'),
}

# \u54c1\u7c7b\u4e2d\u6587\u540d, \u4e0e SHELF \u7684\u952e\u4e00\u4e00\u5bf9\u5e94
CATS = {
    'leafy': '\u53f6\u83dc\u7c7b',
    'root': '\u6839\u830e\u7c7b',
    'cabbage': '\u7ed3\u7403\u4e0e\u74dc\u7c7b',
    'mushroom': '\u83cc\u83c7\u7c7b',
    'meat': '\u755c\u8089\u7c7b',
    'poultry': '\u79bd\u8089\u7c7b',
    'seafood_fish': '\u9c7c\u7c7b\u6d77\u9c9c',
    'seafood_shell': '\u8d1d\u7c7b\u6d77\u9c9c',
    'egg': '\u86cb\u7c7b',
    'milk': '\u725b\u5976',
    'yogurt': '\u9178\u5976\u4e0e\u5976\u5236\u54c1',
    'leftover': '\u719f\u98df\u5269\u83dc',
    'rice_noodle': '\u7c73\u996d\u9762\u6761',
    'soup': '\u6c64\u7c7b',
    'opened_sauce': '\u5f00\u5c01\u9171\u6599',
    'opened_oil': '\u5f00\u5c01\u98df\u7528\u6cb9',
    'bakery': '\u9762\u5305\u7cd5\u70b9',
    'frozen_dumpling': '\u51b7\u51bb\u9762\u70b9\u901f\u98df',
    'ice_cream': '\u51b0\u6dc7\u6dcb',
    'cut_fruit': '\u5207\u5f00\u7684\u6c34\u679c',
}

# \u611f\u5b98\u4e0d\u53ef\u9760\u7684\u573a\u666f\uff1a\u8fd9\u4e9b\u5fc5\u987b\u9760\u65f6\u95f4\u4e0e\u6e29\u5ea6\u7ba1\u7406\uff0c\u4e0d\u80fd\u9760\u95fb\u3001\u770b\u3001\u5c1d
UNRELIABLE = {
    'poultry': '\u6c99\u95e8\u6c0f\u83cc\u4e0e\u5f2f\u66f2\u83cc\u5728\u51bb\u85cf\u671f\u5185\u53ef\u589e\u6b96\uff0c\u8089\u773c\u4e0e\u55c5\u89c9\u5747\u65e0\u5f02\u5e38\uff0c\u5fc5\u987b\u9760\u65f6\u95f4\u4e0e\u6e29\u5ea6\u63a7\u5236',
    'meat': '\u674e\u65af\u7279\u83cc\u53ef\u5728\u51b7\u85cf\u6e29\u5ea6\u4e0b\u7f13\u6162\u589e\u6b96\uff0c\u5916\u89c2\u4e0e\u6c14\u5473\u5b8c\u5168\u6b63\u5e38\uff0c\u52a0\u70ed\u65f6\u987b\u786e\u4fdd\u4e2d\u5fc3\u719f\u900f',
    'seafood_fish': '\u7ec4\u80fa\u7b49\u964d\u89e3\u4ea7\u7269\u4e0d\u4ea7\u751f\u660e\u663e\u5f02\u5473\uff0c\u4f46\u53ef\u5f15\u8d77\u4e0d\u9002\uff0c\u53ea\u80fd\u9760\u4f4e\u6e29\u4e0e\u65f6\u9650\u7ba1\u7406',
    'leftover': '\u8721\u6837\u82bd\u5b62\u6746\u83cc\u6bd2\u7d20\u52a0\u70ed\u4e0d\u88ab\u7834\u574f\uff0c\u82e5\u5df2\u53d8\u8d28\u4ec5\u590d\u70ed\u4e0d\u80fd\u6d88\u9664\u98ce\u9669',
    'rice_noodle': '\u7c73\u996d\u5728\u5ba4\u6e29\u653e\u7f6e\u53ef\u4ea7\u751f\u8010\u70ed\u6bd2\u7d20\uff0c\u590d\u70ed\u65e0\u6cd5\u53bb\u9664\uff0c\u5fc5\u987b\u5c3d\u5feb\u51b7\u5374',
}

# \u4e09\u6761\u786c\u6307\u6807
HARD = [
    ('\u5f02\u5473', '\u51fa\u73b0\u9178\u998a\u5473\u3001\u8150\u8d25\u5473\u3001\u6c28\u5473\u3001\u54c8\u5587\u5473\uff08\u6cb9\u8102\u6c27\u5316\uff09\u6216\u4efb\u4f55\u4e0d\u8be5\u6709\u7684\u5473\u9053\uff0c\u7acb\u5373\u5f03\u7528'),
    ('\u8d28\u5730\u53d8\u5316', '\u53d1\u9ecf\u3001\u53d8\u6ed1\u3001\u62c9\u4e1d\u5f02\u5e38\u3001\u7ed3\u5757\u5206\u5c42\u3001\u6c64\u6c41\u53d8\u7a20\u53d1\u6d51\uff0c\u5747\u89c6\u4e3a\u53d8\u8d28'),
    ('\u5916\u89c2\u9709\u53d8', '\u51fa\u73b0\u767d\u8272\u6216\u5f69\u8272\u7ed2\u6bdb\u72b6\u9709\u83cc\u3001\u7eff\u6591\u3001\u53d1\u81ed\u6c34\u6ce1\u3001\u9f13\u5305\u80c0\u6c14\uff08\u7f50\u5934\u7c7b\uff09\uff0c\u7acb\u5373\u5f03\u7528'),
]

# \u4e0d\u5efa\u8bae\u51b7\u51bb\u7684\u54c1\u7c7b
NO_FREEZE = {
    'leafy': '\u53f6\u83dc\u51b7\u51bb\u540e\u89e3\u51bb\u6210\u7cca\u72b6\uff0c\u4e0d\u53ef\u9006',
    'milk': '\u725b\u5976\u51b7\u51bb\u540e\u5206\u5c42\uff0c\u86cb\u767d\u53d8\u6027\uff0c\u98ce\u5473\u4e0e\u8d28\u5730\u4e0d\u53ef\u63a5\u53d7',
    'egg': '\u5e26\u58f3\u9e21\u86cb\u51b7\u51bb\u4f1a\u7206\u88c2',
    'cut_fruit': '\u5207\u5f00\u7684\u6c34\u679c\u51b7\u51bb\u540e\u8d28\u5730\u5d29\u574f\uff0c\u53ea\u9002\u5408\u69a8\u6c41',
    'ice_cream': '\u878d\u5316\u540e\u4e0d\u53ef\u590d\u51bb\uff0c\u7ed3\u6676\u4e14\u53e3\u611f\u4e0d\u53ef\u63a5\u53d7',
    'opened_oil': '\u4f4e\u6e29\u4f1a\u4f7f\u6cb9\u8102\u51dd\u56fa\u7ed3\u5757\uff0c\u5f71\u54cd\u4f7f\u7528\u4e0e\u98ce\u5473',
}


def norm(k):
    return str(k or '').strip().lower().replace(' ', '')


def shelf_of(cat):
    c = norm(cat)
    if c not in SHELF:
        raise ValueError('\u672a\u77e5\u54c1\u7c7b: %s\uff0c\u53ef\u9009\u54c1\u7c7b\u89c1 SHELF \u8868' % cat)
    return SHELF[c]


def days_tier(d):
    if d is None:
        return '\u672a\u586b\u5199'
    if d <= 1:
        return '\u6781\u77ed\uff08\u5f53\u5929\u6216\u6b21\u65e5\u7528\u5b8c\uff09'
    if d <= 3:
        return '\u77ed\uff08\u4e0d\u5b9c\u8fc7\u591c\u5b58\u653e\uff09'
    if d <= 7:
        return '\u4e2d\uff08\u4e00\u5468\u5185\uff09'
    if d <= 30:
        return '\u8f83\u957f\uff08\u4e24\u5468\u5230\u4e00\u6708\uff09'
    return '\u957f\uff08\u4e00\u6708\u4ee5\u4e0a\uff09'


def grade(fresh_days, limit, mode):
    """fresh_days: \u5df2\u5728\u8be5\u51b7\u85cf/\u51b7\u51bb\u6761\u4ef6\u5b58\u653e\u7684\u5929\u6570; limit: \u8be5\u6761\u4ef6\u4fdd\u5b58\u671f\u4e0a\u9650"""
    if limit <= 0:
        return '\u4e0d\u9002\u7528'
    if fresh_days < 0:
        return '\u672a\u586b\u5199'
    pct = fresh_days / float(limit) * 100.0
    if pct >= 100:
        return '\u5df2\u8d85\u671f'
    if pct >= 70:
        return '\u4e34\u8fd1\u671f\u9650'
    return '\u6b63\u5e38'


def calc(data):
    today = data.get('today')
    if not today:
        raise ValueError('\u7f3a\u5c11 today\uff08\u6838\u67e5\u65e5\u671f\uff0c\u683c\u5f0f YYYY-MM-DD\uff09')
    items = data.get('items') or []
    if not items:
        raise ValueError('\u81f3\u5c11\u9700\u8981\u4e00\u9879\u98df\u6750\u8bb0\u5f55')

    rows = []
    for it in items:
        cat = it.get('category')
        key = norm(cat)
        if key not in SHELF:
            raise ValueError('\u672a\u77e5\u54c1\u7c7b: %s\uff0c\u53ef\u9009\u54c1\u7c7b\u89c1 CATS \u8868' % cat)
        cool, freeze, tip = shelf_of(cat)
        mode = norm(it.get('mode') or '\u51b7\u85cf')
        if mode not in ('\u51b7\u85cf', '\u51b7\u51bb'):
            raise ValueError('mode \u53ea\u80fd\u586b \u51b7\u85cf \u6216 \u51b7\u51bb\uff0c\u5b9e\u4e3a: %s' % mode)
        limit = cool if mode == '\u51b7\u85cf' else freeze
        if limit == 0:
            limit = None
        fd = it.get('fresh_days')
        fd = None if fd is None else float(fd)
        st = grade(fd, limit or 0, mode)
        q = it.get('quantity')
        rows.append({
            'name': it.get('name', '\u672a\u547d\u540d\u98df\u6750'),
            'category': cat,
            'category_name': CATS[key],
            'mode': mode,
            'cool_days': cool,
            'freeze_days': freeze,
            'limit_days': limit,
            'fresh_days': fd,
            'tier': days_tier(limit),
            'status': st,
            'tip': tip,
            'reliable_note': UNRELIABLE.get(norm(cat), '\u611f\u5b98\u6307\u6807\u57fa\u672c\u53ef\u7528\uff0c\u4f46\u65f6\u95f4\u4e0e\u6e29\u5ea6\u7ba1\u7406\u4ecd\u662f\u524d\u63d0'),
            'no_freeze': NO_FREEZE.get(norm(cat), ''),
            'quantity': q,
        })

    rows.sort(key=lambda r: (0 if r['status'] == '\u5df2\u8d85\u671f' else 1 if r['status'] == '\u4e34\u8fd1\u671f\u9650' else 2))
    warns = []
    for r in rows:
        if r['status'] == '\u5df2\u8d85\u671f':
            warns.append('%s \u5df2\u8d85\u671f\uff08%s\u6761\u4ef6\u4e0b\u5b58\u653e %.0f \u5929\uff0c\u671f\u9650\u4e3a %s\uff09\uff0c\u6309\u6700\u574f\u60c5\u51b5\u5f03\u7528\uff0c\u4e0d\u5efa\u8bae\u7ee7\u7eed\u98df\u7528'
                         % (r['name'], r['mode'], r['fresh_days'],
                            ('%d \u5929' % r['limit_days']) if r['limit_days'] else '\u4e0d\u53ef\u5b58\u653e'))
        elif r['status'] == '\u4e34\u8fd1\u671f\u9650':
            warns.append('%s \u5df2\u8fbe\u671f\u9650\u7684 %.0f%%\uff0c\u8bf7\u4f18\u5148\u5b89\u6392\u98df\u7528\u6216\u8f6c\u51b7\u51bb\uff0c\u4e0d\u8981\u518d\u5ef6\u957f\u5b58\u653e'
                         % (r['name'], r['fresh_days'] / float(r['limit_days'] or 1) * 100))
    hi = [r for r in rows if r['category'] in ('leafy', 'mushroom', 'cut_fruit')]
    if hi:
        warns.append('\u53f6\u83dc\u3001\u83cc\u83c7\u3001\u5207\u5f00\u7684\u6c34\u679c\u6613\u8150\u4e14\u611f\u5b98\u6ede\u540e\uff0c\u5efa\u8bae\u73b0\u4e70\u73b0\u5403\uff0c\u8d85\u8fc7\u4e00\u5929\u6309\u6700\u574f\u60c5\u51b5\u5904\u7406')
    risky = [r for r in rows if r['category'] in UNRELIABLE]
    if risky:
        warns.append('\u4ee5\u4e0b\u54c1\u7c7b\u611f\u5b98\u4e0d\u53ef\u9760\uff0c\u5fc5\u987b\u9760\u65f6\u95f4\u4e0e\u6e29\u5ea6\u7ba1\u7406\uff1a%s' % '\u3001'.join(
            r['name'] for r in risky))

    return {
        'today': today,
        'fridge_temp_ok': data.get('fridge_temp_ok'),
        'freezer_temp_ok': data.get('freezer_temp_ok'),
        'rows': rows,
        'warns': warns,
        'hard_metrics': [{'name': n, 'detail': d} for n, d in HARD],
    }


def render_md(r):
    L = []
    L.append('# \u98df\u6750\u50a8\u5b58\u4fdd\u9c9c\u4e0e\u671f\u9650\u6838\u67e5')
    L.append('')
    L.append('\u6838\u67e5\u65e5\u671f\uff1a%s' % r['today'])
    L.append('')
    L.append('\u51b7\u85cf\u6e29\u5ea6\u8fbe\u6807\u60c5\u51b5\uff1a%s\u3000\u3000\u51b7\u51bb\u6e29\u5ea6\u8fbe\u6807\u60c5\u51b5\uff1a%s'
             % (r['fridge_temp_ok'] if r['fridge_temp_ok'] is not None else '\u672a\u586b\u5199',
                r['freezer_temp_ok'] if r['freezer_temp_ok'] is not None else '\u672a\u586b\u5199'))
    L.append('')
    L.append('## \u4e00\u3001\u9010\u9879\u6838\u67e5\uff08\u6309\u7d27\u6025\u5ea6\u6392\u5e8f\uff09')
    L.append('')
    L.append('| \u98df\u6750 | \u54c1\u7c7b | \u5b58\u653e\u6761\u4ef6 | \u5df2\u653e\u5929\u6570 | \u4fdd\u5b58\u671f\u4e0a\u9650 | \u65f6\u957f\u6863\u4f4d | \u72b6\u6001 | \u4fdd\u5b58\u8981\u70b9 |')
    L.append('|---|---|---|---|---|---|---|---|')
    for row in r['rows']:
        lim = ('%d \u5929' % row['limit_days']) if row['limit_days'] else '\u4e0d\u9002\u7528'
        fd = ('%.0f \u5929' % row['fresh_days']) if row['fresh_days'] is not None else '\u672a\u586b\u5199'
        L.append('| %s | %s | %s | %s | %s | %s | %s | %s |'
                 % (row['name'], row['category_name'], row['mode'], fd, lim,
                    row['tier'], row['status'], row['tip']))
    L.append('')
    L.append('## \u4e8c\u3001\u611f\u5b98\u4e0d\u53ef\u9760\u63d0\u793a')
    L.append('')
    for row in r['rows']:
        if row['category'] in UNRELIABLE:
            L.append('- %s\uff08%s\uff09\uff1a%s' % (row['name'], row['category_name'], row['reliable_note']))
    if not any(row['category'] in UNRELIABLE for row in r['rows']):
        L.append('- \u672c\u6b21\u8bb0\u5f55\u4e2d\u65e0\u611f\u5b98\u4e0d\u53ef\u9760\u54c1\u7c7b\uff0c\u4ecd\u9700\u6309\u51b7\u85cf 4 \u6444\u6c0f\u5ea6\u4ee5\u4e0b\u3001\u51b7\u51bb\u8d1f 18 \u6444\u6c0f\u5ea6\u4ee5\u4e0b\u7ba1\u7406')
    L.append('')
    L.append('## \u4e09\u3001\u53d8\u8d28\u4e09\u6761\u786c\u6307\u6807')
    L.append('')
    L.append('| \u6307\u6807 | \u53e3\u5f84 |')
    L.append('|---|---|')
    for h in r['hard_metrics']:
        L.append('| %s | %s |' % (h['name'], h['detail']))
    L.append('')
    L.append('## \u56db\u3001\u4e0d\u5efa\u8bae\u51b7\u51bb\u7684\u54c1\u7c7b')
    L.append('')
    has_nf = False
    for row in r['rows']:
        if row['no_freeze']:
            L.append('- %s\uff1a%s' % (row['name'], row['no_freeze']))
            has_nf = True
    if not has_nf:
        L.append('- \u672c\u6b21\u8bb0\u5f55\u4e2d\u65e0\u4e0d\u53ef\u51b7\u51bb\u54c1\u7c7b')
    L.append('')
    L.append('## \u4e94\u3001\u5904\u7f6e\u63d0\u793a')
    L.append('')
    if r['warns']:
        for w in r['warns']:
            L.append('- %s' % w)
    else:
        L.append('- \u672a\u53d1\u73b0\u8d85\u671f\u9879\uff0c\u6309\u8ba1\u5212\u98df\u7528\u5e76\u4fdd\u6301\u6e29\u5ea6')
    L.append('')
    L.append('## \u516d\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] \u9010\u9879\u5b8c\u6210\u5f02\u5473\u3001\u8d28\u5730\u3001\u5916\u89c2\u4e09\u9879\u611f\u5b98\u6838\u5bf9')
    L.append('- [ ] \u51b7\u85cf\u5ba4\u6e29\u5ea6\u4e0d\u9ad8\u4e8e 4 \u6444\u6c0f\u5ea6\uff0c\u51b7\u51bb\u5ba4\u4e0d\u9ad8\u4e8e\u8d1f 18 \u6444\u6c0f\u5ea6')
    L.append('- [ ] \u751f\u8089\u751f\u79bd\u4e0e\u5373\u98df\u98df\u54c1\u5206\u683c\u5b58\u653e\uff0c\u5305\u88c5\u672a\u7834\u635f')
    L.append('- [ ] \u53f6\u83dc\u5df2\u6ca5\u5e72\uff0c\u672a\u5806\u538b\uff0c\u672a\u4e0e\u9ad8\u6c34\u5206\u679c\u852c\u540c\u888b')
    L.append('- [ ] \u5f00\u5c01\u9171\u6599\u5df2\u6807\u6ce8\u5f00\u5c01\u65e5\u671f')
    L.append('- [ ] \u5b58\u7591\u9879\u5df2\u6309\u6700\u574f\u60c5\u51b5\u5904\u7406\uff0c\u672a\u4ee5\u300c\u770b\u8d77\u6765\u8fd8\u884c\u300d\u653e\u884c')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    # 1 \u53f6\u83dc\u51b7\u85cf 3 \u5929\uff0c\u8d85\u671f
    r1 = calc({'today': '2026-05-10', 'items': [
        {'name': '\u5c0f\u767d\u83dc', 'category': 'leafy', 'mode': '\u51b7\u85cf', 'fresh_days': 4}]})
    ck(r1['rows'][0]['limit_days'] == 3, '\u53f6\u83dc\u51b7\u85cf\u671f\u9650\u5e94\u4e3a 3 \u5929\uff0c\u5b9e\u4e3a %s' % r1['rows'][0]['limit_days'])
    ck(r1['rows'][0]['status'] == '\u5df2\u8d85\u671f', '\u53f6\u83dc\u653e 4 \u5929\u5e94\u5224\u8d85\u671f\uff0c\u5b9e\u4e3a %s' % r1['rows'][0]['status'])
    ck(any('\u5df2\u8d85\u671f' in w for w in r1['warns']), '\u53f6\u83dc\u8d85\u671f\u5e94\u4ea7\u751f\u63d0\u793a\uff0c\u5b9e\u4e3a %s' % r1['warns'])

    # 2 \u6839\u830e\u7c7b\u957f\u6863 + \u51b7\u51bb
    r2 = calc({'today': '2026-05-10', 'items': [
        {'name': '\u571f\u8c46', 'category': 'root', 'mode': '\u51b7\u51bb', 'fresh_days': 100}]})
    ck(r2['rows'][0]['limit_days'] == 120, '\u6839\u830e\u51b7\u51bb\u671f\u9650\u5e94\u4e3a 120 \u5929\uff0c\u5b9e\u4e3a %s' % r2['rows'][0]['limit_days'])
    ck(r2['rows'][0]['tier'] == '\u957f\uff08\u4e00\u6708\u4ee5\u4e0a\uff09', '100 \u5929\u5e94\u843d\u957f\u6863\uff0c\u5b9e\u4e3a %s' % r2['rows'][0]['tier'])
    ck(r2['rows'][0]['status'] == '\u4e34\u8fd1\u671f\u9650', '\u6839\u830e\u51b7\u51bb 100 \u5929\u4e3a\u957f\u6863\u4f46\u8fdb\u5ea6 83%% \u5e94\u4e34\u8fd1\u671f\u9650\uff0c\u5b9e\u4e3a %s' % r2['rows'][0]['status'])

    # 3 \u79bd\u8089\u51b7\u85cf 2 \u5929\u4e0a\u9650
    r3 = calc({'today': '2026-05-10', 'items': [
        {'name': '\u9e21\u80f8\u8089', 'category': 'poultry', 'mode': '\u51b7\u85cf', 'fresh_days': 2}]})
    ck(r3['rows'][0]['limit_days'] == 2, '\u79bd\u8089\u51b7\u85cf\u671f\u9650\u5e94\u4e3a 2 \u5929\uff0c\u5b9e\u4e3a %s' % r3['rows'][0]['limit_days'])
    ck(r3['rows'][0]['status'] == '\u5df2\u8d85\u671f', '\u79bd\u8089\u653e\u6ee1 2 \u5929\u5e94\u5224\u8d85\u671f\uff0c\u5b9e\u4e3a %s' % r3['rows'][0]['status'])
    ck('\u5f2f\u66f2\u83cc' in r3['rows'][0]['reliable_note'], '\u79bd\u8089\u5e94\u5e26\u611f\u5b98\u4e0d\u53ef\u9760\u63d0\u793a\uff0c\u5b9e\u4e3a %s' % r3['rows'][0]['reliable_note'])

    # 4 \u9e21\u86cb\u51b7\u85cf 30 \u5929
    r4 = calc({'today': '2026-05-10', 'items': [
        {'name': '\u9e21\u86cb', 'category': 'egg', 'mode': '\u51b7\u85cf', 'fresh_days': 20}]})
    ck(r4['rows'][0]['limit_days'] == 30, '\u9e21\u86cb\u51b7\u85cf\u671f\u9650\u5e94\u4e3a 30 \u5929\uff0c\u5b9e\u4e3a %s' % r4['rows'][0]['limit_days'])
    ck(r4['rows'][0]['no_freeze'] != '', '\u9e21\u86cb\u5e94\u6807\u6ce8\u4e0d\u53ef\u51b7\u51bb')
    ck(NO_FREEZE['egg'].startswith('\u5e26\u58f3\u9e21\u86cb'), '\u9e21\u86cb\u4e0d\u53ef\u51b7\u51bb\u539f\u56e0\u63cf\u8ff0\u6709\u8bef: %s' % NO_FREEZE['egg'])

    # 5 \u4e34\u8fd1\u671f\u9650\u6863\uff0870%\uff09
    r5 = calc({'today': '2026-05-10', 'items': [
        {'name': '\u725b\u5976', 'category': 'milk', 'mode': '\u51b7\u85cf', 'fresh_days': 6}]})
    ck(r5['rows'][0]['limit_days'] == 7, '\u725b\u5976\u51b7\u85cf\u671f\u9650\u5e94\u4e3a 7 \u5929\uff0c\u5b9e\u4e3a %s' % r5['rows'][0]['limit_days'])
    ck(r5['rows'][0]['status'] == '\u4e34\u8fd1\u671f\u9650', '\u725b\u5976\u653e 6 \u5929\u5e94\u5224\u4e34\u8fd1\u671f\u9650\uff0c\u5b9e\u4e3a %s' % r5['rows'][0]['status'])

    # 6 \u4e0d\u53ef\u5b58\u653e\u54c1\u7c7b\uff1a\u51b0\u6dc7\u6dcb\u51b7\u51bb\u671f\u9650\u4e3a 0
    r6 = calc({'today': '2026-05-10', 'items': [
        {'name': '\u51b0\u6dc7\u6dcb', 'category': 'ice_cream', 'mode': '\u51b7\u51bb', 'fresh_days': 5}]})
    ck(r6['rows'][0]['limit_days'] is None, '\u51b0\u6dc7\u6dcb\u65e0\u7edf\u4e00\u671f\u9650\u5e94\u4e3a\u7a7a\uff0c\u5b9e\u4e3a %s' % r6['rows'][0]['limit_days'])
    ck(r6['rows'][0]['status'] == '\u4e0d\u9002\u7528', '\u65e0\u671f\u9650\u54c1\u7c7b\u72b6\u6001\u5e94\u4e3a\u4e0d\u9002\u7528\uff0c\u5b9e\u4e3a %s' % r6['rows'][0]['status'])

    # 7 \u6392\u5e8f\uff1a\u8d85\u671f\u5728\u524d
    r7 = calc({'today': '2026-05-10', 'items': [
        {'name': '\u6b63\u5e38\u83dc', 'category': 'root', 'mode': '\u51b7\u85cf', 'fresh_days': 2},
        {'name': '\u8fc7\u671f\u8089', 'category': 'meat', 'mode': '\u51b7\u85cf', 'fresh_days': 9}]})
    ck(r7['rows'][0]['name'] == '\u8fc7\u671f\u8089', '\u8d85\u671f\u9879\u5e94\u6392\u6700\u524d\uff0c\u5b9e\u4e3a %s' % r7['rows'][0]['name'])

    # 8 BOM \u8f93\u5165\uff1a\u5e26 BOM \u7684 JSON \u9996\u4e2a key \u4e0d\u5e94\u53d8\u6210\u4e71\u7801
    bom_raw = '\ufeff{"today": "2026-05-10", "items": [{"name": "\u7c73\u996d", "category": "rice_noodle", "mode": "\u51b7\u85cf", "fresh_days": 1}]}'
    d8 = json.loads(bom_raw.lstrip('\ufeff'))
    r8 = calc(d8)
    ck(r8['rows'][0]['name'] == '\u7c73\u996d', 'BOM \u8f93\u5165\u5e94\u6b63\u786e\u89e3\u6790\uff0c\u5b9e\u4e3a %s' % r8['rows'][0]['name'])
    ck(r8['rows'][0]['limit_days'] == 3, '\u7c73\u996d\u51b7\u85cf\u671f\u9650\u5e94\u4e3a 3 \u5929\uff0c\u5b9e\u4e3a %s' % r8['rows'][0]['limit_days'])

    # 9 utf-8-sig \u8bfb\u53d6\u8def\u5f84
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps({'today': '2026-05-10', 'items': [
            {'name': '\u9178\u5976', 'category': 'yogurt', 'mode': '\u51b7\u85cf', 'fresh_days': 9}]}))
    try:
        d9 = json.loads(open(tmp, 'r', encoding='utf-8-sig').read())
        r9 = calc(d9)
        ck(r9['rows'][0]['name'] == '\u9178\u5976', 'utf-8-sig \u8bfb\u53d6\u5e94\u6b63\u5e38\uff0c\u5b9e\u4e3a %s' % r9['rows'][0]['name'])
        ck(r9['rows'][0]['status'] == '\u4e34\u8fd1\u671f\u9650', '\u9178\u5976\u653e 9 \u5929\u5e94\u4e34\u8fd1\u671f\u9650\uff0c\u5b9e\u4e3a %s' % r9['rows'][0]['status'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 10 \u975e\u6cd5\u8f93\u5165
    for bad, why in (
        ({'today': '2026-05-10', 'items': []}, '\u7a7a\u5217\u8868'),
        ({'items': [{'name': 'x', 'category': 'leafy'}]}, '\u7f3a today'),
        ({'today': '2026-05-10', 'items': [{'category': '\u4e0d\u5b58\u5728\u7684\u54c1\u7c7b'}]}, '\u672a\u77e5\u54c1\u7c7b'),
        ({'today': '2026-05-10', 'items': [{'category': 'leafy', 'mode': '\u5e38\u6e29'}]}, '\u975e\u6cd5 mode'),
    ):
        try:
            calc(bad)
            ck(False, '\u7528\u4f8b10 %s \u5e94\u629b\u9519' % why)
        except ValueError:
            ck(True, '')

    # 11 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r1)
    for key in ('\u53d8\u8d28\u4e09\u6761\u786c\u6307\u6807', '\u611f\u5b98\u4e0d\u53ef\u9760', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355', '\u4e0d\u5efa\u8bae\u51b7\u51bb'):
        ck(key in md, 'Markdown \u8f93\u51fa\u5e94\u542b\u7ae0\u8282 %s' % key)
    ck(len(r1['hard_metrics']) == 3, '\u786c\u6307\u6807\u5e94\u4e3a 3 \u6761\uff0c\u5b9e\u4e3a %d' % len(r1['hard_metrics']))

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res = os.path.join(out_dir, '_selftest_result.txt')
    msg = 'SELFTEST FAIL\n' + '\n'.join(errs) if errs else (
        'SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u54c1\u7c7b\u671f\u9650/\u8d85\u671f\u5224\u5b9a/\u4e34\u8fd1\u671f\u9650\u6863/\u4e0d\u53ef\u5b58\u653e/\u611f\u5b98\u4e0d\u53ef\u9760\u63d0\u793a/'
        '\u6392\u5e8f/BOM \u8f93\u5165(lstrip)/BOM \u8f93\u5165(utf-8-sig)/\u975e\u6cd5\u8f93\u5165/\u8f93\u51fa\u7ed3\u6784/\u4e09\u6761\u786c\u6307\u6807' % n)
    with open(res, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u98df\u6750\u50a8\u5b58\u4fdd\u9c9c\u4e0e\u671f\u9650\u6838\u67e5')
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