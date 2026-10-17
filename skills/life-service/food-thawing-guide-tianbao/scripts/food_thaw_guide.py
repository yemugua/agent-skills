# -*- coding: utf-8 -*-
"""\u98df\u7269\u89e3\u51bb\u65b9\u5f0f\u4e0e\u5b89\u5168\u6838\u67e5\uff1a\u6309\u98df\u6750\u7ed9\u51fa\u53ef\u7528\u89e3\u51bb\u65b9\u5f0f\u3001\u7981\u6b62\u65b9\u5f0f\u3001\u8017\u65f6\u4f30\u7b97\u4e0e\u590d\u51bb\u5224\u5b9a\u3002

\u7528\u6cd5:
  python food_thaw_guide.py --file thaw.json [--out result.md] [--format json]
  python food_thaw_guide.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u56db\u7c7b\u89e3\u51bb\u65b9\u5f0f\u4ee3\u53f7
METHODS = ('\u51b7\u85cf\u6162\u89e3', '\u5ba4\u6e29', '\u5fae\u6ce2', '\u70ed\u6c34')

# \u98df\u6750 -> (\u4e2d\u6587\u540d, \u63a8\u8350\u65b9\u5f0f, \u7981\u6b62\u65b9\u5f0f, \u539a\u5ea6\u5398\u7c73, \u5907\u6ce8)
# \u539a\u5ea6\u7528\u4e8e\u4f30\u7b97\u51b7\u85cf\u89e3\u51bb\u8017\u65f6: \u6bcf 2.5 \u5398\u7c73\u7ea6\u9700 12 \u5230 24 \u5c0f\u65f6
FOODS = {
    'whole_fish': ('\u6574\u6761\u9c7c', '\u51b7\u85cf\u6162\u89e3', '\u70ed\u6c34', 6,
                   '\u6574\u5757\u9c7c\u8089\u4e25\u7981\u70ed\u6c34\u6216\u5fae\u6ce2\uff0c\u89e3\u51bb\u5373\u5d29\u6563\u5e76\u5927\u91cf\u6d41\u5931\u6c41\u6db2'),
    'fish_fillet': ('\u9c7c\u7247\u9c7c\u67f3', '\u51b7\u85cf\u6162\u89e3', '\u70ed\u6c34', 3,
                    '\u8584\u7247\u53ef\u5fae\u6ce2\u77ed\u65f6\u6bb5\u89e3\u51bb\uff0c\u4f46\u4ecd\u4ee5\u51b7\u85cf\u4e3a\u9996\u9009'),
    'shrimp': ('\u867e\u4ec1\u867e', '\u51b7\u85cf\u6162\u89e3', '\u70ed\u6c34', 3,
               '\u5e26\u58f3\u867e\u53ef\u7528\u76d0\u6c34\u6d78\u89e3\uff0c\u4f46\u4e0d\u5e94\u957f\u65f6\u95f4\u5ba4\u6e29\u653e\u7f6e'),
    'beef_roast': ('\u6574\u5757\u725b\u8089', '\u51b7\u85cf\u6162\u89e3', '\u5ba4\u6e29', 8,
                   '\u5927\u5757\u5fc5\u987b\u51b7\u85cf\u89e3\u51bb\uff0c\u5ba4\u6e29\u89e3\u51bb\u8868\u9762\u5df2\u8fdb\u5371\u9669\u6e29\u5ea6\u533a\u800c\u5185\u90e8\u8fd8\u51bb\u7740'),
    'beef_slice': ('\u725b\u8089\u7247', '\u5fae\u6ce2', '\u70ed\u6c34', 2,
                   '\u8584\u7247\u53ef\u5fae\u6ce2\u6216\u51b7\u85cf\uff0c\u89e3\u51bb\u540e\u4e0d\u8981\u653e\u56de\u51b7\u51bb\u5ba4'),
    'pork_roast': ('\u6574\u5757\u732a\u8089', '\u51b7\u85cf\u6162\u89e3', '\u5ba4\u6e29', 7,
                   '\u540c\u725b\u8089\uff0c\u9700\u6309\u539a\u5ea6\u7ed9\u8db3\u51b7\u85cf\u65f6\u95f4'),
    'chicken_whole': ('\u6574\u9e21', '\u51b7\u85cf\u6162\u89e3', '\u5ba4\u6e29', 10,
                      '\u5e26\u9aa8\u6574\u79bd\u5fc5\u987b\u51b7\u85cf\u89e3\u51bb\uff0c\u5fae\u6ce2\u89e3\u51bb\u6613\u719f\u5728\u5c40\u90e8\u800c\u4e2d\u5fc3\u4ecd\u51bb'),
    'chicken_part': ('\u9e21\u7fc5\u9e21\u817f', '\u51b7\u85cf\u6162\u89e3', '\u70ed\u6c34', 4,
                     '\u5c0f\u5757\u53ef\u5fae\u6ce2\uff0c\u4f46\u987b\u7acb\u5373\u70f9\u8c03'),
    'ground_meat': ('\u8089\u9985\u8089\u7cdc', '\u51b7\u85cf\u6162\u89e3', '\u5ba4\u6e29', 4,
                    '\u8089\u9985\u8868\u9762\u79ef\u5927\uff0c\u5ba4\u6e29\u89e3\u51bb\u98ce\u9669\u9ad8\uff0c\u53ea\u80fd\u51b7\u85cf'),
    'frozen_dumpling': ('\u51b7\u51bb\u6c34\u997a\u5305\u5b50', '\u51b7\u85cf\u6162\u89e3', '\u70ed\u6c34', 3,
                        '\u901f\u98df\u7c7b\u5efa\u8bae\u76f4\u63a5\u4e0b\u9505\u716e\uff0c\u4e0d\u5efa\u8bae\u89e3\u51bb'),
    'frozen_bread': ('\u51b7\u51bb\u9762\u5305', '\u5ba4\u6e29', '\u70ed\u6c34', 6,
                     '\u70d8\u7119\u7c7b\u5ba4\u6e29\u56de\u6e29\u5373\u53ef\uff0c\u4e0d\u9700\u51b7\u85cf\u89e3\u51bb'),
    'ice_cream': ('\u51b0\u6dc7\u6dcb', '\u51b7\u85cf\u6162\u89e3', '\u5ba4\u6e29', 8,
                  '\u4ec5\u51b7\u85cf\u5ba4\u56de\u6e29\uff0c\u4e25\u7981\u5ba4\u6e29\u4e0e\u70ed\u6c34\uff0c\u878d\u5316\u540e\u4e0d\u53ef\u518d\u51bb'),
    'butter': ('\u9ec4\u6cb9', '\u5ba4\u6e29', '\u70ed\u6c34', 6,
               '\u70d8\u7119\u7528\u9ec4\u6cb9\u53ef\u5ba4\u6e29\u56de\u8f6f\uff0c\u9700\u9694\u6c34\u878d\u5316\u65f6\u6c34\u6e29\u4e0d\u8d85\u8fc7 40 \u6444\u6c0f\u5ea6'),
    'frozen_vegetable': ('\u51b7\u51bb\u852c\u83dc', '\u51b7\u85cf\u6162\u89e3', '\u70ed\u6c34', 4,
                         '\u4e0d\u89e3\u51bb\u76f4\u63a5\u70f9\u8c03\u66f4\u4f73\uff0c\u53e3\u611f\u4e0e\u8425\u517b\u635f\u5931\u90fd\u66f4\u5c0f'),
    'frozen_rice': ('\u51b7\u51bb\u7c73\u996d', '\u51b7\u85cf\u6162\u89e3', '\u70ed\u6c34', 4,
                    '\u4f18\u5148\u76f4\u63a5\u52a0\u70ed\u6c34\u590d\u70ed\uff0c\u65e0\u9700\u89e3\u51bb'),
    'potato': ('\u6574\u571f\u8c46', '\u5ba4\u6e29', '\u70ed\u6c34', 8,
               '\u571f\u8c46\u53ef\u5ba4\u6e29\u56de\u6e29\uff0c\u4e0d\u53ef\u6574\u5757\u70ed\u6c34\u716e\uff0c\u5185\u5916\u53d7\u70ed\u4e0d\u5747\u6613\u5916\u719f\u5185\u751f'),
    'whole_egg': ('\u6574\u51b7\u51bb\u86cb', '\u51b7\u85cf\u6162\u89e3', '\u70ed\u6c34', 6,
                  '\u65e0\u58f3\u86cb\u53ef\u51b7\u85cf\u89e3\u51bb\uff0c\u5e26\u58f3\u51b7\u51bb\u86cb\u672c\u5c31\u4e0d\u5e94\u4ea7\u751f'),
    'butter_cookie': ('\u51b7\u51bb\u997c\u5e72\u7cd5\u70b9', '\u5ba4\u6e29', '\u5fae\u6ce2', 5,
                      '\u997c\u5e72\u7c7b\u5ba4\u6e29\u56de\u6e29\u5373\u53ef\uff0c\u5fae\u6ce2\u4f1a\u4f7f\u9ec4\u6cb9\u878d\u5316\u53e3\u611f\u53d1\u7802'),
}

# \u7edd\u5bf9\u7981\u6b62\u70ed\u6c34\u89e3\u51bb\u7684\u54c1\u7c7b\uff08\u786c\u7ea2\u7ebf\uff09
FORBID_HOT = {
    'whole_fish': '\u6574\u5757\u9c7c\u8089\u70ed\u6c34\u89e3\u51bb\uff0c\u8868\u5c42\u77ac\u95f4\u719f\u5316\u800c\u4e2d\u5fc3\u4ecd\u51b0\u51bb\uff0c\u7ec6\u80de\u7834\u88c2\u540e\u6c41\u6db2\u6d41\u5931\u3001\u8089\u8d28\u53d1\u67f4',
    'shrimp': '\u867e\u7c7b\u70ed\u6c34\u89e3\u51bb\u5916\u58f3\u7c98\u8fde\u3001\u867e\u8089\u53d8\u9762\uff0c\u98ce\u5473\u4e0e\u53e3\u611f\u4e0d\u53ef\u63a5\u53d7',
    'chicken_whole': '\u5e26\u9aa8\u6574\u79bd\u70ed\u6c34\u89e3\u51bb\uff0c\u5c40\u90e8\u53d7\u70ed\u719f\u5316\uff0c\u4e2d\u5fc3\u4ecd\u51bb\uff0c\u89e3\u51bb\u540e\u6781\u6613\u6ecb\u751f\u7ec6\u83cc',
    'pork_roast': '\u6574\u5757\u732a\u8089\u70ed\u6c34\u89e3\u51bb\uff0c\u5916\u5c42\u6e17\u51fa\u5927\u91cf\u6c41\u6db2\uff0c\u8425\u517b\u6d41\u5931\u4e14\u6613\u6c61\u67d3\u53f0\u9762',
    'beef_roast': '\u6574\u5757\u725b\u8089\u70ed\u6c34\u89e3\u51bb\uff0c\u6c41\u6db2\u6d41\u5931\u4e25\u91cd\uff0c\u8868\u9762\u6b8b\u7559\u751f\u719f\u4e0d\u5747',
    'frozen_dumpling': '\u901f\u98df\u7c7b\u70ed\u6c34\u6ce1\u89e3\u51bb\u4f1a\u5916\u76ae\u6ce1\u70c2\u7834\u53e3\uff0c\u4e14\u901f\u98df\u672c\u8eab\u65e0\u9700\u89e3\u51bb',
    'ice_cream': '\u51b0\u6dc7\u6dcb\u70ed\u6c34\u63a5\u89e6\u5373\u5927\u91cf\u878d\u5316\uff0c\u4e0d\u53ef\u518d\u51bb\u6210\u539f\u8d28\u5730',
}

# \u4e0d\u53ef\u590d\u51bb\uff08\u4e00\u6b21\u6027\u89e3\u51bb\u7528\u5b8c\uff09\u7684\u54c1\u7c7b
NO_REFREEZE = {
    'whole_fish': '\u6574\u9c7c\u89e3\u51bb\u540e\u7ec6\u83cc\u5927\u91cf\u7e41\u6b96\uff0c\u4e0d\u53ef\u590d\u51bb',
    'fish_fillet': '\u9c7c\u7247\u89e3\u51bb\u540e\u8d28\u5730\u5df2\u53d8\uff0c\u4e0d\u53ef\u590d\u51bb',
    'shrimp': '\u867e\u7c7b\u89e3\u51bb\u540e\u4e0d\u53ef\u590d\u51bb',
    'beef_roast': '\u6574\u5757\u8089\u89e3\u51bb\u540e\u8868\u9762\u7ec6\u83cc\u7e41\u6b96\uff0c\u590d\u51bb\u4e0d\u80fd\u9006\u8f6c',
    'beef_slice': '\u8089\u7247\u89e3\u51bb\u540e\u4e0d\u53ef\u590d\u51bb',
    'pork_roast': '\u6574\u5757\u732a\u8089\u89e3\u51bb\u540e\u4e0d\u53ef\u590d\u51bb',
    'chicken_whole': '\u6574\u9e21\u89e3\u51bb\u540e\u4e0d\u53ef\u590d\u51bb',
    'chicken_part': '\u9e21\u7fc5\u9e21\u817f\u89e3\u51bb\u540e\u4e0d\u53ef\u590d\u51bb',
    'ground_meat': '\u8089\u9985\u89e3\u51bb\u540e\u4e0d\u53ef\u590d\u51bb',
    'whole_egg': '\u86cb\u6db2\u89e3\u51bb\u540e\u4e0d\u53ef\u590d\u51bb',
}

# \u5ba4\u6e29\u89e3\u51bb\u7684\u65f6\u95f4\u4e0a\u9650\uff08\u5c0f\u65f6\uff09\uff0c\u8d85\u8fc7\u5373\u8fdb\u5165\u5371\u9669\u6e29\u5ea6\u533a\u7d2f\u79ef\u98ce\u9669
ROOM_LIMIT_H = {
    'frozen_bread': 4,
    'butter': 3,
    'butter_cookie': 4,
    'potato': 6,
}


def norm(k):
    return str(k or '').strip().lower().replace(' ', '')


def food_of(key):
    k = norm(key)
    if k not in FOODS:
        raise ValueError('\u672a\u77e5\u98df\u6750\u952e: %s\uff0c\u53ef\u9009\u952e\u89c1 FOODS \u8868' % key)
    return FOODS[k]


def hours_refrigerated(thick_cm):
    """\u51b7\u85cf\u89e3\u51bb\u8017\u65f6\u4f30\u7b97: \u6bcf 2.5 \u5398\u7c73\u7ea6 12 \u5230 24 \u5c0f\u65f6, \u53d6\u533a\u95f4\u4e0b\u9650\u4f5c\u53c2\u8003\u3002"""
    t = float(thick_cm)
    if t <= 0:
        raise ValueError('\u539a\u5ea6\u5fc5\u987b\u4e3a\u6b63\u6570')
    return t / 2.5 * 12.0


def transfer_plan(hours):
    """\u4ece\u51b7\u51bb\u5ba4\u63d0\u524d\u8f6c\u79fb\u5230\u51b7\u85cf\u5ba4\u7684\u65f6\u70b9\u5efa\u8bae\u3002"""
    h = float(hours)
    if h <= 12:
        return '\u5f53\u5929\u5c3d\u65e9\u8f6c\u5165\u51b7\u85cf\u5ba4\uff0c\u5e76\u5728\u5f53\u65e5\u5185\u5b8c\u6210\u89e3\u51bb'
    return '\u9700\u63d0\u524d\u4e00\u5929\u8f6c\u5165\u51b7\u85cf\u5ba4\uff1b\u6309\u4f30\u7b97\u8017\u65f6 %.0f \u5c0f\u65f6\u5012\u63a8\uff0c\u591c\u95f4\u5165\u7761\u524d\u8f6c\u5165\u6700\u5408\u9002' % h


def allow(method, ban, key):
    if method not in METHODS:
        raise ValueError('\u65b9\u5f0f\u53ea\u80fd\u586b %s \u4e4b\u4e00\uff0c\u5b9e\u4e3a: %s' % ('/'.join(METHODS), method))
    if method == ban:
        return False
    if method == '\u70ed\u6c34' and key in FORBID_HOT:
        return False
    if method == '\u5ba4\u6e29' and key in ('whole_fish', 'shrimp', 'chicken_whole',
                                    'pork_roast', 'beef_roast', 'ground_meat'):
        return False
    return True


def calc(data):
    items = data.get('items') or []
    if not items:
        raise ValueError('\u81f3\u5c11\u9700\u8981\u4e00\u9879\u5f85\u89e3\u51bb\u98df\u6750')
    plan_from = data.get('plan_from', '\u4eca\u5929')
    if plan_from not in ('\u4eca\u5929', '\u660e\u5929', '\u540e\u5929'):
        raise ValueError('plan_from \u53ea\u80fd\u586b \u4eca\u5929 / \u660e\u5929 / \u540e\u5929')

    rows = []
    for it in items:
        key = norm(it.get('food'))
        name, rec, ban, thick, note = food_of(key)
        chosen = it.get('method') or rec
        ok = allow(chosen, ban, key)
        hrs = hours_refrigerated(thick)
        if chosen == '\u51b7\u85cf\u6162\u89e3':
            need = hrs
        elif chosen == '\u5ba4\u6e29':
            need = max(2.0, hrs / 3.0)
        elif chosen == '\u5fae\u6ce2':
            need = max(1.0, hrs / 6.0)
        else:
            need = 1.0
        rows.append({
            'name': it.get('name', name),
            'food': key,
            'food_name': name,
            'chosen': chosen,
            'recommended': rec,
            'banned': ban,
            'ok': ok,
            'verdict': '\u65b9\u5f0f\u53ef\u884c' if ok else '\u65b9\u5f0f\u7981\u6b62',
            'hours': round(need, 1),
            'thick': thick,
            'refreeze': '\u53ef\u590d\u51bb' if key not in NO_REFREEZE else '\u4e0d\u53ef\u590d\u51bb',
            'transfer': transfer_plan(hrs) if ok else '\u65b9\u5f0f\u7981\u6b62\uff0c\u4e0d\u505a\u8f6c\u79fb\u5b89\u6392',
            'note': note,
        })

    rows.sort(key=lambda r: 0 if not r['ok'] else 1)
    warns = []
    for r in rows:
        if not r['ok']:
            warns.append('%s \u9009\u7528\u300c%s\u300d\u4e3a\u7981\u6b62\u65b9\u5f0f\uff0c\u5e94\u6539\u7528\u300c%s\u300d\u3002%s'
                         % (r['name'], r['chosen'], r['recommended'],
                            FORBID_HOT.get(r['food'], '\u8be5\u65b9\u5f0f\u4e0d\u9002\u7528\u4e8e\u6b64\u7c7b\u98df\u6750')))
        if r['refreeze'] == '\u4e0d\u53ef\u590d\u51bb':
            warns.append('%s \u89e3\u51bb\u540e\u4e0d\u53ef\u590d\u51bb\uff0c\u89e3\u51bb\u5f53\u6b21\u5fc5\u987b\u5403\u5b8c' % r['name'])
    slow = [r for r in rows if r['ok'] and r['hours'] >= 12]
    if slow:
        warns.append('\u4ee5\u4e0b\u98df\u6750\u51b7\u85cf\u89e3\u51bb\u8017\u65f6\u8f83\u957f\uff0c\u9700\u6309\u8f6c\u79fb\u65f6\u70b9\u5b89\u6392\uff1a%s' % '\u3001'.join(
            r['name'] for r in slow))
    long_room = [r for r in rows if r['ok'] and r['chosen'] == '\u5ba4\u6e29'
                 and r['hours'] > ROOM_LIMIT_H.get(r['food'], 4)]
    if long_room:
        warns.append('\u4ee5\u4e0b\u98df\u6750\u5ba4\u6e29\u89e3\u51bb\u8017\u65f6\u8d85\u8fc7\u5b89\u5168\u4e0a\u9650\uff0c\u5efa\u8bae\u6539\u7528\u51b7\u85cf\u6162\u89e3\uff1a%s' % '\u3001'.join(
            r['name'] for r in long_room))
    if plan_from == '\u4eca\u5929' and any(r['ok'] and r['hours'] > 8 for r in rows):
        warns.append('\u8ba1\u5212\u4eca\u5929\u5f00\u59cb\uff0c\u4f46\u5b58\u5728\u8017\u65f6\u8d85\u8fc7 8 \u5c0f\u65f6\u7684\u98df\u6750\uff0c\u4eca\u5929\u624d\u8f6c\u79fb\u6765\u4e0d\u53ca\uff0c\u8bf7\u6539\u7528\u5176\u4ed6\u65b9\u5f0f')

    return {
        'plan_from': plan_from,
        'rows': rows,
        'warns': warns,
        'cross_contamination': [
            '\u89e3\u51bb\u76d8\u5fc5\u987b\u5355\u72ec\u4f7f\u7528\uff0c\u4e0d\u4e0e\u76f4\u63a5\u5165\u53e3\u6216\u5373\u98df\u98df\u54c1\u63a5\u89e6',
            '\u751f\u79bd\u4e0e\u751f\u8089\u7684\u89e3\u51bb\u6db2\u5fc5\u987b\u5012\u6389\uff0c\u7edd\u4e0d\u7528\u4e8e\u5176\u4ed6\u98df\u6750',
            '\u89e3\u51bb\u5b8c\u6210\u540e\u7acb\u5373\u6e05\u6d17\u89e3\u51bb\u76d8\u4e0e\u64cd\u4f5c\u53f0\u9762\uff0c\u518d\u5904\u7406\u5373\u98df\u98df\u54c1',
            '\u89e3\u51bb\u6c34\u4e0d\u5f97\u5012\u5165\u6c34\u69fd\u6c61\u67d3\u5176\u4ed6\u7269\u54c1\uff0c\u63a5\u89e6\u4e0b\u5c42\u98df\u6750\u7684\u6ef4\u6db2\u8981\u63d0\u524d\u9632\u6b62',
            '\u5904\u7406\u5b8c\u751f\u8089\u540e\u5fc5\u987b\u6d17\u624b\uff0c\u518d\u63a5\u89e6\u719f\u98df\u4e0e\u5373\u98df\u98df\u54c1',
        ],
    }


def render_md(r):
    L = []
    L.append('# \u98df\u7269\u89e3\u51bb\u65b9\u5f0f\u4e0e\u5b89\u5168\u6838\u67e5')
    L.append('')
    L.append('\u8ba1\u5212\u8d77\u59cb\uff1a%s' % r['plan_from'])
    L.append('')
    L.append('## \u4e00\u3001\u9010\u9879\u6838\u67e5\uff08\u7981\u6b62\u65b9\u5f0f\u6392\u6700\u524d\uff09')
    L.append('')
    L.append('| \u98df\u6750 | \u91c7\u7528\u65b9\u5f0f | \u63a8\u8350\u65b9\u5f0f | \u7981\u6b62\u65b9\u5f0f | \u5224\u5b9a | \u9884\u8ba1\u8017\u65f6\uff08\u5c0f\u65f6\uff09 | \u53ef\u5426\u590d\u51bb | \u8bf4\u660e |')
    L.append('|---|---|---|---|---|---|---|---|')
    for x in r['rows']:
        L.append('| %s | %s | %s | %s | %s | %.1f | %s | %s |'
                 % (x['name'], x['chosen'], x['recommended'], x['banned'],
                    x['verdict'], x['hours'], x['refreeze'], x['note']))
    L.append('')
    L.append('## \u4e8c\u3001\u8f6c\u79fb\u65f6\u70b9')
    L.append('')
    for x in r['rows']:
        L.append('- %s\uff1a%s' % (x['name'], x['transfer']))
    L.append('')
    L.append('## \u4e09\u3001\u89e3\u51bb\u73af\u8282\u4ea4\u53c9\u6c61\u67d3\u9632\u63a7')
    L.append('')
    for c in r['cross_contamination']:
        L.append('- %s' % c)
    L.append('')
    L.append('## \u56db\u3001\u63d0\u793a')
    L.append('')
    if r['warns']:
        for w in r['warns']:
            L.append('- %s' % w)
    else:
        L.append('- \u65b9\u5f0f\u9009\u62e9\u5747\u5728\u5141\u8bb8\u8303\u56f4\u5185\uff0c\u6309\u4f30\u7b97\u8017\u65f6\u4e0e\u8f6c\u79fb\u65f6\u70b9\u6267\u884c')
    L.append('')
    L.append('## \u4e94\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] \u5df2\u5728\u51b7\u51bb\u5ba4\u5185\u5b8c\u6210\u89e3\u51bb\uff0c\u672a\u7528\u70ed\u6c34\u6216\u5ba4\u6e29\u957f\u65f6\u95f4\u653e\u7f6e')
    L.append('- [ ] \u89e3\u51bb\u76d8\u5355\u72ec\u4f7f\u7528\uff0c\u89e3\u51bb\u6db2\u5df2\u5012\u6389\u5e76\u6e05\u6d17')
    L.append('- [ ] \u5904\u7406\u5b8c\u751f\u8089\u751f\u79bd\u540e\u5df2\u6d17\u624b\uff0c\u518d\u63a5\u89e6\u719f\u98df\u4e0e\u5373\u98df\u98df\u54c1')
    L.append('- [ ] \u89e3\u51bb\u540e\u5f53\u6b21\u5403\u5b8c\uff0c\u672a\u590d\u51bb\u653e\u56de')
    L.append('- [ ] \u4e2d\u5fc3\u5df2\u5f7b\u5e95\u89e3\u51bb\uff0c\u672a\u6309\u300c\u5916\u9762\u5316\u4e86\u5c31\u662f\u5316\u4e86\u300d\u5224\u65ad')
    L.append('- [ ] \u51b7\u85cf\u89e3\u51bb\u671f\u95f4\u672a\u4e0e\u751f\u9c9c\u5373\u98df\u98df\u54c1\u540c\u5c42\u4ea4\u53c9\u6c61\u67d3')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    # 1 \u6574\u9c7c\u7981\u6b62\u70ed\u6c34
    r1 = calc({'items': [{'food': 'whole_fish', 'method': '\u70ed\u6c34'}]})
    ck(r1['rows'][0]['ok'] is False, '\u6574\u9c7c\u70ed\u6c34\u89e3\u51bb\u5e94\u88ab\u7981\u6b62\uff0c\u5b9e\u4e3a %s' % r1['rows'][0]['ok'])
    ck(r1['rows'][0]['verdict'] == '\u65b9\u5f0f\u7981\u6b62', '\u6574\u9c7c\u70ed\u6c34\u5e94\u5224\u65b9\u5f0f\u7981\u6b62\uff0c\u5b9e\u4e3a %s' % r1['rows'][0]['verdict'])
    ck(any('\u7981\u6b62\u65b9\u5f0f' in w for w in r1['warns']), '\u5e94\u4ea7\u751f\u7981\u6b62\u65b9\u5f0f\u63d0\u793a\uff0c\u5b9e\u4e3a %s' % r1['warns'])
    ck('\u6d41\u5931' in FORBID_HOT['whole_fish'] or '\u6d41\u5931' in r1['rows'][0]['note'],
       '\u6574\u9c7c\u5e94\u8bf4\u660e\u6c41\u6db2\u6d41\u5931\u98ce\u9669')

    # 2 \u6574\u9e21\u7981\u6b62\u5ba4\u6e29
    r2 = calc({'items': [{'food': 'chicken_whole', 'method': '\u5ba4\u6e29'}]})
    ck(r2['rows'][0]['ok'] is False, '\u6574\u9e21\u5ba4\u6e29\u89e3\u51bb\u5e94\u88ab\u7981\u6b62\uff0c\u5b9e\u4e3a %s' % r2['rows'][0]['ok'])

    # 3 \u51b7\u85cf\u8017\u65f6\u6309\u539a\u5ea6\u4f30\u7b97
    ck(abs(hours_refrigerated(2.5) - 12.0) < 0.01, '2.5 \u5398\u7c73\u5e94\u4e3a 12 \u5c0f\u65f6\uff0c\u5b9e\u4e3a %s' % hours_refrigerated(2.5))
    ck(abs(hours_refrigerated(6.0) - 28.8) < 0.01, '6 \u5398\u7c73\u5e94\u4e3a 28.8 \u5c0f\u65f6\uff0c\u5b9e\u4e3a %s' % hours_refrigerated(6.0))
    ck(abs(hours_refrigerated(10.0) - 48.0) < 0.01, '10 \u5398\u7c73\u5e94\u4e3a 48 \u5c0f\u65f6\uff0c\u5b9e\u4e3a %s' % hours_refrigerated(10.0))

    # 4 \u8017\u65f6\u957f\u9700\u63d0\u524d\u4e00\u5929\u8f6c\u79fb
    r4 = calc({'items': [{'food': 'chicken_whole', 'method': '\u51b7\u85cf\u6162\u89e3'}]})
    ck(r4['rows'][0]['hours'] > 40, '\u6574\u9e21\u51b7\u85cf\u89e3\u51bb\u5e94\u8d85 40 \u5c0f\u65f6\uff0c\u5b9e\u4e3a %s' % r4['rows'][0]['hours'])
    ck('\u63d0\u524d\u4e00\u5929' in r4['rows'][0]['transfer'], '\u8d85 12 \u5c0f\u65f6\u5e94\u63d0\u793a\u63d0\u524d\u4e00\u5929\u8f6c\u79fb\uff0c\u5b9e\u4e3a %s' % r4['rows'][0]['transfer'])

    # 5 \u4e0d\u53ef\u590d\u51bb
    r5 = calc({'items': [{'food': 'beef_slice'}, {'food': 'frozen_bread'}]})
    names = {x['name']: x['refreeze'] for x in r5['rows']}
    ck(names['\u725b\u8089\u7247'] == '\u4e0d\u53ef\u590d\u51bb', '\u725b\u8089\u7247\u5e94\u4e0d\u53ef\u590d\u51bb\uff0c\u5b9e\u4e3a %s' % names['\u725b\u8089\u7247'])
    ck(names['\u51b7\u51bb\u9762\u5305'] == '\u53ef\u590d\u51bb', '\u51b7\u51bb\u9762\u5305\u5e94\u53ef\u590d\u51bb\uff0c\u5b9e\u4e3a %s' % names['\u51b7\u51bb\u9762\u5305'])

    # 6 \u9ed8\u8ba4\u65b9\u5f0f\u5373\u63a8\u8350\u65b9\u5f0f
    r6 = calc({'items': [{'food': 'pork_roast'}]})
    ck(r6['rows'][0]['chosen'] == '\u51b7\u85cf\u6162\u89e3', '\u6574\u5757\u732a\u8089\u9ed8\u8ba4\u5e94\u4e3a\u51b7\u85cf\u6162\u89e3\uff0c\u5b9e\u4e3a %s' % r6['rows'][0]['chosen'])
    ck(r6['rows'][0]['ok'] is True, '\u6574\u5757\u732a\u8089\u51b7\u85cf\u6162\u89e3\u5e94\u53ef\u884c\uff0c\u5b9e\u4e3a %s' % r6['rows'][0]['ok'])

    # 7 \u901f\u98df\u4e0d\u89e3\u51bb\u63d0\u793a
    ck('\u65e0\u9700\u89e3\u51bb' in FOODS['frozen_dumpling'][4] or '\u4e0d\u5efa\u8bae\u89e3\u51bb' in FOODS['frozen_dumpling'][4],
       '\u901f\u98df\u7c7b\u5e94\u63d0\u793a\u65e0\u9700\u89e3\u51bb')

    # 8 \u6392\u5e8f\uff1a\u7981\u6b62\u65b9\u5f0f\u5728\u524d
    r8 = calc({'items': [
        {'food': 'frozen_bread', 'name': '\u9762\u5305'},
        {'food': 'whole_fish', 'name': '\u6574\u9c7c', 'method': '\u70ed\u6c34'}]})
    ck(r8['rows'][0]['name'] == '\u6574\u9c7c', '\u7981\u6b62\u65b9\u5f0f\u5e94\u6392\u6700\u524d\uff0c\u5b9e\u4e3a %s' % r8['rows'][0]['name'])

    # 9 \u4eca\u5929\u5f00\u59cb\u4f46\u8017\u65f6\u957f\u5e94\u544a\u8b66
    r9 = calc({'plan_from': '\u4eca\u5929', 'items': [{'food': 'beef_roast', 'method': '\u51b7\u85cf\u6162\u89e3'}]})
    ck(any('\u6765\u4e0d\u53ca' in w for w in r9['warns']), '\u4eca\u5929\u5f00\u59cb+\u8017\u65f6\u957f\u5e94\u544a\u8b66\uff0c\u5b9e\u4e3a %s' % r9['warns'])

    # 10 BOM \u8f93\u5165\u4e24\u6761\u8def\u5f84
    bom = '\ufeff{"items": [{"food": "shrimp", "method": "\u70ed\u6c34"}]}'
    d10 = json.loads(bom.lstrip('\ufeff'))
    r10 = calc(d10)
    ck(r10['rows'][0]['name'] == '\u867e\u4ec1\u867e', 'BOM \u8f93\u5165\u5e94\u6b63\u786e\u89e3\u6790\uff0c\u5b9e\u4e3a %s' % r10['rows'][0]['name'])
    ck(r10['rows'][0]['ok'] is False, '\u867e\u7c7b\u70ed\u6c34\u89e3\u51bb\u5e94\u88ab\u7981\u6b62')
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe2.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps({'items': [{'food': 'ground_meat', 'method': '\u5ba4\u6e29'}]}))
    try:
        r10b = calc(json.loads(open(tmp, 'r', encoding='utf-8-sig').read()))
        ck(r10b['rows'][0]['ok'] is False, '\u8089\u9985\u5ba4\u6e29\u89e3\u51bb\u5e94\u88ab\u7981\u6b62')
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 11 \u975e\u6cd5\u8f93\u5165
    for bad, why in (
        ({'items': []}, '\u7a7a\u5217\u8868'),
        ({'items': [{'food': '\u4e0d\u5b58\u5728\u7684\u98df\u6750'}]}, '\u672a\u77e5\u98df\u6750\u952e'),
        ({'items': [{'food': 'shrimp', 'method': '\u5f00\u6c34\u70eb'}]}, '\u975e\u6cd5\u65b9\u5f0f\u540d'),
        ({'plan_from': '\u4e0b\u5468', 'items': [{'food': 'shrimp'}]}, '\u975e\u6cd5 plan_from'),
    ):
        try:
            calc(bad)
            ck(False, '\u7528\u4f8b11 %s \u5e94\u629b\u9519' % why)
        except ValueError:
            ck(True, '')

    # 12 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r1)
    for key in ('\u8f6c\u79fb\u65f6\u70b9', '\u4ea4\u53c9\u6c61\u67d3\u9632\u63a7', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355'):
        ck(key in md, 'Markdown \u8f93\u51fa\u5e94\u542b\u7ae0\u8282 %s' % key)
    ck(len(r1['cross_contamination']) == 5, '\u4ea4\u53c9\u6c61\u67d3\u9632\u63a7\u5e94\u4e3a 5 \u6761\uff0c\u5b9e\u4e3a %d' % len(r1['cross_contamination']))

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    msg = 'SELFTEST FAIL\n' + '\n'.join(errs) if errs else (
        'SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u70ed\u6c34\u7981\u6b62/\u5ba4\u6e29\u7981\u6b62/\u51b7\u85cf\u8017\u65f6\u4f30\u7b97/\u63d0\u524d\u4e00\u5929\u8f6c\u79fb/\u4e0d\u53ef\u590d\u51bb/'
        '\u9ed8\u8ba4\u65b9\u5f0f/\u901f\u98df\u4e0d\u89e3\u51bb/\u7981\u6b62\u9879\u6392\u5e8f/\u65f6\u95f4\u51b2\u7a81\u544a\u8b66/BOM \u4e24\u6761\u8def\u5f84/\u975e\u6cd5\u8f93\u5165/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u98df\u7269\u89e3\u51bb\u65b9\u5f0f\u4e0e\u5b89\u5168\u6838\u67e5')
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