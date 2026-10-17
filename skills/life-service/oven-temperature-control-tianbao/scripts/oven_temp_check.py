# -*- coding: utf-8 -*-
"""\u70e4\u7bb1\u6e29\u63a7\u4e0e\u70d8\u70e4\u65f6\u95f4\u6838\u67e5\uff1a\u6e29\u5ea6\u6362\u7b97\u3001\u4e0a\u4e0b\u706b\u8c03\u6574\u3001\u98df\u6750\u65f6\u95f4\u5bf9\u7167\u4e0e\u6613\u7126\u4e0d\u719f\u6210\u56e0\u5224\u5b9a\u3002

\u7528\u6cd5:
  python oven_temp_check.py --file oven.json [--out result.md] [--format json]
  python oven_temp_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u98df\u6750 -> (\u4e2d\u6587\u540d, \u5efa\u8bae\u6e29\u5ea6, \u5efa\u8bae\u65f6\u95f4\u5206\u949f, \u539a\u5ea6\u6216\u6279\u91cf\u5f71\u54cd, \u6613\u7126\u6210\u56e0, \u4e0d\u719f\u6210\u56e0)
FOODS = {
    'whole_chicken': ('\u6574\u9e21', 190, 70, 6,
                  '\u8868\u76ae\u4e0a\u8272\u8fc7\u5feb\u800c\u4e2d\u5fc3\u672a\u719f\uff0c\u5efa\u8bae\u964d\u6e29\u6216\u52a0\u76d6\u9521\u7eb8',
                  '\u4e2d\u5fc3\u6e29\u5ea6\u4e0d\u8db3\uff0c\u89e3\u51bb\u4e0d\u5f7b\u5e95\u6216\u6e29\u5ea6\u504f\u4f4e'),
    'chicken_wing': ('\u9e21\u7fc5', 200, 25, 3,
                 '\u7cd6\u5206\u6216\u9171\u6599\u76f4\u63a5\u63a5\u89e6\u4e0a\u706b\u6613\u7126\uff0c\u4e2d\u9014\u5237\u6cb9\u7ffb\u9762',
                 '\u7fc5\u6839\u672a\u719f\u900f\uff0c\u6446\u653e\u8fc7\u5bc6'),
    'beef_steak': ('\u725b\u6392', 200, 8, 3,
               '\u9ad8\u6e29\u957f\u65f6\u95f4\u4f7f\u8868\u9762\u78b3\u5316\uff0c\u5185\u90e8\u4ecd\u504f\u751f',
               '\u539a\u5ea6\u4e0d\u591f\u6216\u9884\u70ed\u4e0d\u8db3'),
    'pork_rib': ('\u6392\u9aa8', 190, 45, 5,
             '\u9171\u6c41\u542b\u7cd6\u6613\u7126\uff0c\u4e2d\u9014\u7ffb\u9762\u5e76\u964d\u6e29',
             '\u808b\u6392\u8d34\u8fd1\u70e4\u76d8\u53d7\u70ed\u4e0d\u8db3'),
    'fish': ('\u6574\u6761\u9c7c', 190, 25, 4,
           '\u9c7c\u76ae\u76f4\u63a5\u66b4\u9732\u6613\u7126\uff0c\u9700\u57ab\u9521\u7eb8\u6216\u63d0\u524d\u5237\u6cb9',
           '\u9c7c\u8089\u539a\u8584\u4e0d\u5747\uff0c\u9760\u9c7c\u5c3e\u5904\u6613\u751f'),
    'roast_vegetable': ('\u70e4\u852c\u83dc', 200, 30, 3,
                   '\u6c34\u5206\u591a\u6613\u51fa\u6c34\u540e\u7126\u8fb9\uff0c\u6e29\u5ea6\u8fc7\u9ad8',
                   '\u5757\u592a\u5927\u6216\u94fa\u6ee1\u70e4\u76d8\uff0c\u95f4\u8ddd\u4e0d\u8db3'),
    'bread': ('\u9762\u5305\u4e0e\u5410\u53f8', 180, 30, 4,
             '\u7cd6\u6d46\u4e0e\u5976\u5236\u54c1\u6613\u7126\uff0c\u4e0a\u706b\u8fc7\u9ad8',
             '\u53d1\u9175\u4e0d\u8db3\u6216\u70e4\u7bb1\u6e29\u5ea6\u504f\u4f4e'),
    'cake': ('\u86cb\u7cd5', 170, 40, 5,
           '\u8868\u9762\u7cd6\u5206\u9ad8\u6613\u7126\uff0c\u9700\u8981\u57ab\u70d8\u7119\u7eb8',
           '\u86cb\u767d\u672a\u6253\u53d1\u6216\u5f00\u88c2\u5bfc\u81f4\u672a\u719f'),
    'cookie': ('\u66f2\u5947\u997c\u5e72', 170, 15, 3,
             '\u7cd6\u6d46\u6613\u7126\uff0c\u9700\u76ef\u89c6\u989c\u8272\u53d8\u5316',
             '\u9762\u56e2\u8fc7\u539a\u6216\u7089\u6e29\u504f\u4f4e'),
    'pizza': ('\u62ab\u8428', 220, 12, 3,
            '\u829d\u58eb\u4e0e\u756a\u8304\u9171\u6613\u7126\uff0c\u4e0a\u706b\u8fc7\u9ad8\u65f6\u51e0\u5206\u949f\u5c31\u4e0a\u8272',
            '\u997c\u5e95\u592a\u539a\u6216\u6c34\u5206\u8fc7\u591a'),
    'roast_roots': ('\u70e4\u6839\u830e', 200, 40, 5,
                '\u7cd6\u5206\u8868\u9762\u6613\u7126\uff0c\u4e2d\u9014\u7ffb\u9762',
                '\u5757\u592a\u539a\u6216\u70e4\u76d8\u8fc7\u5bc6'),
    'chestnut': ('\u6817\u5b50', 200, 25, 4,
             '\u58f3\u6613\u7126\uff0c\u9700\u5f00\u53e3\u540e\u518d\u70e4',
             '\u5f00\u53e3\u4e0d\u8db3\u5bfc\u81f4\u65e0\u6cd5\u53d7\u70ed\u5747\u5300'),
    'tofu': ('\u70e4\u8c46\u8150', 200, 25, 4,
           '\u8868\u9762\u6c34\u5206\u591a\u6613\u7126\u8fb9\uff0c\u9700\u5148\u714e\u6216\u6ca5\u5e72',
           '\u8c46\u8150\u592a\u5ae9\u6613\u788e\uff0c\u7ffb\u52a8\u8fc7\u65e9'),
    'sweet_potato': ('\u70e4\u7ea2\u85af', 200, 45, 6,
                 '\u7cd6\u5206\u6e17\u51fa\u6613\u7126\uff0c\u4e2d\u9014\u7ffb\u9762',
                 '\u7ea2\u85af\u592a\u5927\u6216\u6e29\u5ea6\u4e0d\u8db3'),
}

# \u534e\u6c0f\u6444\u6c0f\u6362\u7b97\u8868
FAHRENHEIT = [100, 120, 140, 150, 160, 170, 180, 190, 200, 220,
              230, 240, 250, 260, 280, 300, 320, 350]

# \u4e0a\u706b\u4e0e\u4e0b\u706b\u7684\u5e38\u89c1\u8c03\u6574
HEAT_SPLIT = {
    'top_heavy': ('\u4e0a\u706b\u504f\u9ad8', '\u4e0a\u706b\u8c03\u4f4e 20 \u81f3 30 \u6444\u6c0f\u5ea6\u6216\u5ef6\u957f\u603b\u65f6\u95f4\uff0c\u907f\u514d\u8868\u9762\u78b3\u5316'),
    'bottom_heavy': ('\u4e0b\u706b\u504f\u9ad8', '\u4e0b\u706b\u8c03\u4f4e 20 \u81f3 30 \u6444\u6c0f\u5ea6\u6216\u57ab\u7a7a\u70e4\u76d8\uff0c\u907f\u514d\u5e95\u90e8\u7126\u8fb9'),
    'even': ('\u4e0a\u4e0b\u706b\u57fa\u672c\u5e73\u8861', '\u7ef4\u6301\u5f53\u524d\u8bbe\u5b9a\uff0c\u6309\u5efa\u8bae\u65f6\u95f4\u6267\u884c'),
    'too_low': ('\u7089\u6e29\u4e0d\u8db3', '\u63d0\u9ad8\u8bbe\u5b9a\u6e29\u5ea6 10 \u81f3 20 \u6444\u6c0f\u5ea6\uff0c\u6216\u5ef6\u957f 20 \u5206\u949f\u5e76\u63d0\u524d 5 \u5206\u949f\u590d\u68c0'),
    'too_high': ('\u7089\u6e29\u8fc7\u9ad8', '\u964d\u4f4e\u8bbe\u5b9a\u6e29\u5ea6 10 \u81f3 20 \u6444\u6c0f\u5ea6\uff0c\u6216\u52a0\u76d6\u9521\u7eb8\u5ef6\u7f13\u4e0a\u8272'),
}

# \u98ce\u6247\u6a21\u5f0f\u4e0e\u975e\u98ce\u6247\u6a21\u5f0f\u5dee\u5f02
FAN_NOTE = (
    '\u98ce\u6247\u6a21\u5f0f\uff08\u70ed\u98ce\u5faa\u73af\uff09\u4f7f\u70ed\u91cf\u5206\u5e03\u66f4\u5747\u5300\uff0c\u540c\u6e29\u5ea6\u4e0b\u901a\u5e38\u6bd4\u975e\u98ce\u6247\u6a21\u5f0f\u5feb\u7ea6 20%%\uff0c'
    '\u9700\u76f8\u5e94\u7f29\u77ed\u65f6\u95f4\u3002\u86cb\u7cd5\u4e0e\u90e8\u5206\u9165\u7c7b\u70b9\u5fc3\u5728\u98ce\u6247\u6a21\u5f0f\u4e0b\u8868\u9762\u53ef\u80fd\u63d0\u524d\u4e0a\u8272\uff0c'
    '\u5efa\u8bae\u8c03\u4f4e\u6e29\u5ea6 10 \u81f3 20 \u6444\u6c0f\u5ea6\u3002\u975e\u98ce\u6247\u6a21\u5f0f\u4ee5\u4e0a\u4e0b\u53d1\u70ed\u7ba1\u76f4\u63a5\u52a0\u70ed\uff0c'
    '\u9760\u8fd1\u4e0a\u7ba1\u7684\u98df\u6750\u5bb9\u6613\u5148\u7126\u3002'
)

# \u9884\u70ed\u5fc5\u8981\u6027
PREHEAT_NOTE = (
    '\u9884\u70ed\u4e0d\u53ef\u7701\u7565\u3002\u5145\u5206\u9884\u70ed\u540e\u70e4\u7bb1\u5185\u5b9e\u9645\u6e29\u5ea6\u624d\u8fbe\u5230\u8bbe\u5b9a\u503c\u3002'
    '\u672a\u5145\u5206\u9884\u70ed\u65f6\uff0c\u6295\u5165\u98df\u6750\u4f1a\u5438\u6536\u5927\u91cf\u70ed\u91cf\u5bfc\u81f4\u5b9e\u9645\u6e29\u5ea6\u9aa4\u964d\uff0c'
    '\u7ed3\u679c\u662f\u9700\u8981\u66f4\u957f\u65f6\u95f4\u624d\u80fd\u4e0a\u8272\uff0c\u540c\u65f6\u5185\u90e8\u53ef\u80fd\u4ecd\u672a\u719f\u900f\u3002'
    '\u5bb6\u7528\u70e4\u7bb1\u5efa\u8bae\u9884\u70ed 10 \u81f3 15 \u5206\u949f\uff0c\u53ef\u7a7a\u7bb1\u6216\u653e\u7a7a\u70e4\u76d8\u3002'
)

# \u5f00\u95e8\u5bf9\u6e29\u573a\u7684\u5f71\u54cd
DOOR_NOTE = (
    '\u5f00\u95e8\u4f1a\u5bfc\u81f4\u70e4\u7bb1\u5185\u6e29\u5ea6\u5728\u77ed\u65f6\u95f4\u5185\u660e\u663e\u4e0b\u964d\u3002'
    '\u77ed\u65f6\u95f4\u5f00\u95e8\u53d6\u51fa\u68c0\u67e5\u5f71\u54cd\u76f8\u5bf9\u6709\u9650\uff1b\u957f\u65f6\u95f4\u5f00\u95e8\u6216\u8fde\u7eed\u591a\u6b21\u5f00\u95e8\uff0c'
    '\u4f1a\u663e\u8457\u5ef6\u957f\u70d8\u70e4\u65f6\u95f4\u5e76\u9020\u6210\u6e29\u573a\u4e0d\u5747\u3002'
    '\u5efa\u8bae\u4e00\u6b21\u5f00\u95e8\u5b8c\u6210\u89c2\u5bdf\u4e0e\u8c03\u6574\uff0c\u5173\u95e8\u540e\u6309\u539f\u65f6\u95f4\u7ee7\u7eed\u3002'
    '\u70e4\u7bb1\u9884\u70ed\u671f\u95f4\u4e0d\u5b9c\u9891\u7e41\u5f00\u95e8\u3002'
)

# \u63a2\u9488\u6e29\u5ea6\u8ba1\u4f7f\u7528\u8981\u70b9
PROBE_NOTE = [
    '\u63a2\u9488\u63d2\u5165\u98df\u7269\u6700\u539a\u5904\u4e2d\u5fc3\uff0c\u4e0d\u80fd\u89e6\u5230\u70e4\u76d8\u6216\u70e4\u67b6',
    '\u8089\u7c7b\u79bd\u7c7b\u4e2d\u5fc3\u6e29\u5ea6\u8fbe\u5230 75 \u6444\u6c0f\u5ea6\u5e76\u4fdd\u6301\uff0c\u53ef\u9760\u6027\u660e\u663e\u63d0\u9ad8',
    '\u8584\u7247\u4e0e\u5c0f\u5757\u4e0d\u9002\u5408\u63a2\u9488\u6d4b\u91cf\uff0c\u5e94\u6309\u65f6\u95f4\u4e0e\u5916\u89c2\u7efc\u5408\u5224\u65ad',
    '\u63a2\u9488\u6bcf\u6b21\u7528\u5b8c\u8981\u6e05\u6d01\u6d88\u6bd2\uff0c\u4e0d\u540c\u98df\u6750\u4e4b\u95f4\u4e0d\u8981\u6df7\u7528',
    '\u63d2\u62d4\u63a2\u9488\u65f6\u5148\u5f00\u95e8\u964d\u6e29\uff0c\u907f\u514d\u84b8\u6c7d\u70eb\u4f24',
]


def norm(k):
    return str(k or '').strip().lower().replace(' ', '')


def f_to_c(f):
    return (float(f) - 32.0) * 5.0 / 9.0


def c_to_f(c):
    return float(c) * 9.0 / 5.0 + 32.0


def c_to_f_table():
    return [(f, round(f_to_c(f))) for f in FAHRENHEIT]


def food_of(key):
    k = norm(key)
    if k not in FOODS:
        raise ValueError('\u672a\u77e5\u98df\u6750\u952e: %s\uff0c\u53ef\u9009\u952e\u89c1 FOODS \u8868' % key)
    return k, FOODS[k]


def scaled_minutes(minutes, temp, base_temp, fan):
    """\u65f6\u95f4 = \u539f\u65f6\u95f4 \u00d7 (\u57fa\u51c6\u6e29\u5ea6 / \u5b9e\u9645\u6e29\u5ea6), \u98ce\u6247\u6a21\u5f0f\u518d\u4e58 0.8\u3002"""
    if temp <= 0:
        raise ValueError('\u6e29\u5ea6\u5fc5\u987b\u4e3a\u6b63\u6570')
    m = (float(minutes) * (float(base_temp) / float(temp)))
    if fan:
        m *= 0.8
    return max(1.0, round(m))


def calc(data):
    temp_c = data.get('temp_c')
    if temp_c is not None and float(temp_c) <= 0:
        raise ValueError('temp_c \u5fc5\u987b\u4e3a\u6b63\u6570')
    fan = bool(data.get('fan_mode'))
    preheat = data.get('preheat_done')
    heat_state = norm(data.get('heat_state') or 'even')
    if heat_state not in HEAT_SPLIT:
        raise ValueError('heat_state \u53ea\u80fd\u586b %s \u4e4b\u4e00\uff0c\u5b9e\u4e3a: %s'
                         % ('/'.join(HEAT_SPLIT), heat_state))

    rows = []
    for it in data.get('items') or []:
        key, (name, rec_temp, rec_min, thick, burn, raw) = food_of(it.get('food'))
        actual = it.get('temp_c')
        if actual is not None and float(actual) <= 0:
            raise ValueError('item \u7684 temp_c \u5fc5\u987b\u4e3a\u6b63\u6570')
        use_temp = float(actual) if actual is not None else float(rec_temp)
        use_min = scaled_minutes(rec_min, use_temp, rec_temp, fan)
        rows.append({
            'name': it.get('name', name),
            'food': key,
            'food_name': name,
            'rec_temp': rec_temp,
            'rec_minutes': rec_min,
            'temp_used': use_temp,
            'minutes_used': use_min,
            'delta_minutes': use_min - rec_min,
            'thick': thick,
            'burn_cause': burn,
            'raw_cause': raw,
            'probe': it.get('probe'),
        })
    rows.sort(key=lambda r: -abs(r['delta_minutes']))

    warns = []
    for r in rows:
        if r['temp_used'] > r['rec_temp'] + 10:
            warns.append('%s \u5b9e\u9645\u6e29\u5ea6 %d \u6444\u6c0f\u5ea6\u9ad8\u4e8e\u5efa\u8bae %d \u6444\u6c0f\u5ea6\uff0c\u65f6\u95f4\u867d\u7f29\u77ed\u4f46\u6613\u7126\uff0c'
                         '\u6613\u7126\u6210\u56e0\uff1a%s'
                         % (r['name'], r['temp_used'], r['rec_temp'], r['burn_cause']))
        if r['temp_used'] < r['rec_temp'] - 10:
            warns.append('%s \u5b9e\u9645\u6e29\u5ea6 %d \u6444\u6c0f\u5ea6\u4f4e\u4e8e\u5efa\u8bae %d \u6444\u6c0f\u5ea6\uff0c\u5185\u90e8\u6613\u4e0d\u719f\uff0c'
                         '\u4e0d\u719f\u6210\u56e0\uff1a%s'
                         % (r['name'], r['temp_used'], r['rec_temp'], r['raw_cause']))
        if r['probe'] is False and r['thick'] >= 4:
            warns.append('%s \u539a\u5ea6\u8f83\u5927\uff0c\u672a\u4f7f\u7528\u63a2\u9488\u6e29\u5ea6\u8ba1\u65f6\u5b58\u5728\u4e2d\u5fc3\u672a\u719f\u98ce\u9669' % r['name'])
    if preheat is False:
        warns.append('\u672a\u5145\u5206\u9884\u70ed\uff0c\u5b9e\u9645\u7089\u6e29\u672a\u8fbe\u8bbe\u5b9a\u503c\uff0c\u70d8\u70e4\u65f6\u95f4\u4f1a\u660e\u663e\u5ef6\u957f')
    if heat_state in ('too_low', 'too_high', 'top_heavy', 'bottom_heavy'):
        label, adj = HEAT_SPLIT[heat_state]
        warns.append('%s\uff1a%s' % (label, adj))
    if fan:
        warns.append('\u98ce\u6247\u6a21\u5f0f\u540c\u6e29\u5ea6\u4e0b\u901a\u5e38\u5feb\u7ea6 20%\uff0c\u811a\u672c\u5df2\u6309 0.8 \u6298\u7b97\uff0c'
                     '\u86cb\u7cd5\u4e0e\u9165\u7c7b\u70b9\u5fc3\u5efa\u8bae\u964d\u6e29 10 \u81f3 20 \u6444\u6c0f\u5ea6')

    return {
        'temp_c': temp_c,
        'temp_f': None if temp_c is None else round(c_to_f(float(temp_c))),
        'fan_mode': fan,
        'preheat_done': preheat,
        'heat_state': heat_state,
        'heat_advice': HEAT_SPLIT[heat_state][1],
        'rows': rows,
        'warns': warns,
        'table': c_to_f_table(),
        'fan_note': FAN_NOTE,
        'preheat_note': PREHEAT_NOTE,
        'door_note': DOOR_NOTE,
        'probe_notes': PROBE_NOTE,
    }


def render_md(r):
    L = []
    L.append('# \u70e4\u7bb1\u6e29\u63a7\u4e0e\u70d8\u70e4\u65f6\u95f4\u6838\u67e5')
    L.append('')
    L.append('## \u4e00\u3001\u57fa\u672c\u6761\u4ef6')
    L.append('')
    L.append('| \u9879 | \u503c |')
    L.append('|---|---|')
    L.append('| \u6444\u6c0f\u8bbe\u5b9a\u6e29\u5ea6 | %s |' % (r['temp_c'] if r['temp_c'] is not None else '\u672a\u586b\u5199'))
    L.append('| \u5bf9\u5e94\u534e\u6c0f\u6e29\u5ea6 | %s |' % (r['temp_f'] if r['temp_f'] is not None else '\u672a\u586b\u5199'))
    L.append('| \u98ce\u6247\u6a21\u5f0f | %s |' % ('\u662f' if r['fan_mode'] else '\u5426'))
    L.append('| \u5df2\u5145\u5206\u9884\u70ed | %s |' % ('\u662f' if r['preheat_done'] else
                                       ('\u5426' if r['preheat_done'] is False else '\u672a\u586b\u5199')))
    L.append('| \u6e29\u573a\u72b6\u6001 | %s |' % r['heat_advice'])
    L.append('')
    L.append('## \u4e8c\u3001\u6e29\u5ea6\u6362\u7b97\u8868\uff08\u534e\u6c0f\u4e0e\u6444\u6c0f\uff09')
    L.append('')
    L.append('| \u534e\u6c0f | \u6444\u6c0f |')
    L.append('|---|---|')
    for f, c in r['table']:
        L.append('| %d | %d |' % (f, c))
    L.append('')
    L.append('## \u4e09\u3001\u9010\u9879\u70d8\u70e4\u53c2\u6570')
    L.append('')
    if r['rows']:
        L.append('| \u98df\u6750 | \u5efa\u8bae\u6e29\u5ea6 | \u5efa\u8bae\u5206\u949f | \u5b9e\u9645\u6e29\u5ea6 | \u5b9e\u9645\u5206\u949f | \u65f6\u95f4\u5dee | \u6613\u7126\u6210\u56e0 | \u4e0d\u719f\u6210\u56e0 |')
        L.append('|---|---|---|---|---|---|---|---|')
        for x in r['rows']:
            L.append('| %s | %d\u2103 | %d | %d\u2103 | %d | %+d | %s | %s |'
                     % (x['name'], x['rec_temp'], x['rec_minutes'], x['temp_used'],
                        x['minutes_used'], x['delta_minutes'],
                        x['burn_cause'], x['raw_cause']))
    else:
        L.append('- \u672a\u586b\u5199\u98df\u6750\u8bb0\u5f55')
    L.append('')
    L.append('## \u56db\u3001\u98ce\u6247\u6a21\u5f0f\u4e0e\u975e\u98ce\u6247\u6a21\u5f0f')
    L.append('')
    L.append('- %s' % r['fan_note'])
    L.append('')
    L.append('## \u4e94\u3001\u9884\u70ed\u7684\u5fc5\u8981\u6027')
    L.append('')
    L.append('- %s' % r['preheat_note'])
    L.append('')
    L.append('## \u516d\u3001\u5f00\u95e8\u5bf9\u6e29\u573a\u7684\u5f71\u54cd')
    L.append('')
    L.append('- %s' % r['door_note'])
    L.append('')
    L.append('## \u4e03\u3001\u63a2\u9488\u6e29\u5ea6\u8ba1\u4f7f\u7528\u8981\u70b9')
    L.append('')
    for p in r['probe_notes']:
        L.append('- %s' % p)
    L.append('')
    L.append('## \u516b\u3001\u63d0\u793a')
    L.append('')
    if r['warns']:
        for w in r['warns']:
            L.append('- %s' % w)
    else:
        L.append('- \u53c2\u6570\u5728\u5efa\u8bae\u8303\u56f4\u5185\uff0c\u6309\u5efa\u8bae\u65f6\u95f4\u6267\u884c\u5e76\u590d\u89c6\u989c\u8272\u4e0e\u72b6\u6001')
    L.append('')
    L.append('## \u4e5d\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] \u5df2\u5145\u5206\u9884\u70ed 10 \u81f3 15 \u5206\u949f')
    L.append('- [ ] \u70e4\u76d8\u4f4d\u7f6e\u4e0e\u98df\u6750\u6446\u653e\u95f4\u8ddd\u5408\u9002\uff0c\u672a\u94fa\u6ee1')
    L.append('- [ ] \u5df2\u5728\u9884\u8ba1\u5b8c\u6210\u65f6\u95f4\u524d\u590d\u89c6\u989c\u8272\u4e0e\u72b6\u6001')
    L.append('- [ ] \u8089\u7c7b\u79bd\u7c7b\u5df2\u7528\u63a2\u9488\u786e\u8ba4\u4e2d\u5fc3\u6e29\u5ea6\u6216\u6309\u53ef\u9760\u65f6\u95f4\u6267\u884c')
    L.append('- [ ] \u672a\u9891\u7e41\u5f00\u95e8')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    # 1 \u534e\u6c0f\u6444\u6c0f\u6362\u7b97
    ck(abs(f_to_c(212) - 100.0) < 0.001, '212 \u534e\u6c0f\u5e94\u4e3a 100 \u6444\u6c0f\uff0c\u5b9e\u4e3a %s' % f_to_c(212))
    ck(abs(f_to_c(350) - 176.6666666) < 0.01, '350 \u534e\u6c0f\u6362\u7b97\u6709\u8bef: %s' % f_to_c(350))
    ck(abs(c_to_f(100) - 212.0) < 0.001, '100 \u6444\u6c0f\u5e94\u4e3a 212 \u534e\u6c0f\uff0c\u5b9e\u4e3a %s' % c_to_f(100))
    ck(abs(c_to_f(180) - 356.0) < 0.001, '180 \u6444\u6c0f\u5e94\u4e3a 356 \u534e\u6c0f\uff0c\u5b9e\u4e3a %s' % c_to_f(180))
    ck(abs(f_to_c(c_to_f(175)) - 175.0) < 0.001, '\u5f80\u8fd4\u6362\u7b97\u5e94\u4e00\u81f4')

    # 2 \u6362\u7b97\u8868\u8986\u76d6\u5e38\u89c1\u70d8\u70e4\u6e29\u5ea6
    tbl = dict(c_to_f_table())
    ck(tbl[180] == 82 and tbl[200] == 93 and tbl[220] == 104,
       '\u6362\u7b97\u8868\u53d6\u503c\u6709\u8bef: 180->%s 200->%s 220->%s' % (tbl[180], tbl[200], tbl[220]))

    # 3 \u6e29\u5ea6\u964d\u4f4e\u65f6\u95f4\u5ef6\u957f
    ck(scaled_minutes(20, 200, 200, False) == 20, '\u540c\u6e29\u540c\u6a21\u5f0f\u5e94\u4e0d\u53d8\uff0c\u5b9e\u4e3a %s' % scaled_minutes(20, 200, 200, False))
    ck(scaled_minutes(20, 180, 200, False) == 22, '\u964d\u6e29 20 \u5ea6\u65f6\u95f4\u5e94\u5ef6\u957f\u5230 22\uff0c\u5b9e\u4e3a %s' % scaled_minutes(20, 180, 200, False))
    ck(scaled_minutes(20, 200, 200, True) == 16, '\u98ce\u6247\u6a21\u5f0f\u5e94\u4e58 0.8\uff0c\u5b9e\u4e3a %s' % scaled_minutes(20, 200, 200, True))

    # 4 \u98ce\u6247\u6a21\u5f0f\u786e\u5b9e\u66f4\u5feb
    ck(scaled_minutes(30, 200, 200, True) < scaled_minutes(30, 200, 200, False),
       '\u98ce\u6247\u6a21\u5f0f\u65f6\u95f4\u5e94\u77ed\u4e8e\u975e\u98ce\u6247\u6a21\u5f0f')

    # 5 \u6574\u9e21\u6570\u636e
    r5 = calc({'temp_c': 190, 'items': [{'food': 'whole_chicken'}]})
    ck(r5['rows'][0]['rec_temp'] == 190, '\u6574\u9e21\u5efa\u8bae\u6e29\u5ea6\u5e94\u4e3a 190\uff0c\u5b9e\u4e3a %s' % r5['rows'][0]['rec_temp'])
    ck(r5['rows'][0]['rec_minutes'] == 70, '\u6574\u9e21\u5efa\u8bae\u65f6\u95f4\u5e94\u4e3a 70 \u5206\u949f\uff0c\u5b9e\u4e3a %s' % r5['rows'][0]['rec_minutes'])
    ck(r5['temp_f'] == 374, '190 \u6444\u6c0f\u5e94\u4e3a 374 \u534e\u6c0f\uff0c\u5b9e\u4e3a %s' % r5['temp_f'])

    # 6 \u6e29\u5ea6\u8fc7\u9ad8\u6613\u7126\u544a\u8b66
    r6 = calc({'temp_c': 200, 'items': [
        {'food': 'whole_chicken', 'temp_c': 240}]})
    ck(any('\u6613\u7126' in w for w in r6['warns']), '\u6e29\u5ea6\u8fc7\u9ad8\u5e94\u63d0\u793a\u6613\u7126\uff0c\u5b9e\u4e3a %s' % r6['warns'])

    # 7 \u6e29\u5ea6\u8fc7\u4f4e\u4e0d\u719f\u544a\u8b66
    r7 = calc({'temp_c': 160, 'items': [
        {'food': 'whole_chicken', 'temp_c': 150}]})
    ck(any('\u4e0d\u719f' in w for w in r7['warns']), '\u6e29\u5ea6\u8fc7\u4f4e\u5e94\u63d0\u793a\u4e0d\u719f\uff0c\u5b9e\u4e3a %s' % r7['warns'])

    # 8 \u672a\u9884\u70ed\u544a\u8b66
    r8 = calc({'preheat_done': False, 'items': [{'food': 'cookie'}]})
    ck(any('\u9884\u70ed' in w for w in r8['warns']), '\u672a\u9884\u70ed\u5e94\u544a\u8b66\uff0c\u5b9e\u4e3a %s' % r8['warns'])

    # 9 \u98ce\u6247\u6a21\u5f0f\u6298\u7b97\u5df2\u5e94\u7528
    r9 = calc({'temp_c': 200, 'fan_mode': True, 'items': [{'food': 'pizza'}]})
    ck(r9['rows'][0]['minutes_used'] == 10,
       '\u62ab\u8428 12 \u5206\u949f\u5728 200 \u5ea6\u98ce\u6247\u6a21\u5f0f\u5e94\u6298\u7b97\u4e3a 10 \u5206\u949f\uff0c\u5b9e\u4e3a %s' % r9['rows'][0]['minutes_used'])

    # 10 \u539a\u98df\u6750\u65e0\u63a2\u9488\u544a\u8b66
    r10 = calc({'temp_c': 190, 'items': [
        {'food': 'whole_chicken', 'probe': False}]})
    ck(any('\u63a2\u9488' in w for w in r10['warns']), '\u539a\u98df\u6750\u672a\u7528\u63a2\u9488\u5e94\u544a\u8b66\uff0c\u5b9e\u4e3a %s' % r10['warns'])

    # 11 \u6392\u5e8f\uff1a\u65f6\u95f4\u53d8\u5316\u5927\u7684\u5728\u524d
    r11 = calc({'temp_c': 200, 'items': [
        {'food': 'cookie', 'name': '\u66f2\u5947'},
        {'food': 'beef_steak', 'name': '\u725b\u6392', 'temp_c': 150}]})
    ck(r11['rows'][0]['name'] == '\u725b\u6392', '\u65f6\u95f4\u5ef6\u957f\u6700\u591a\u5e94\u6392\u6700\u524d\uff0c\u5b9e\u4e3a %s' % r11['rows'][0]['name'])

    # 12 BOM \u4e24\u6761\u8def\u5f84
    bom = '\ufeff{"temp_c": 180, "items": [{"food": "bread"}]}'
    r12 = calc(json.loads(bom.lstrip('\ufeff')))
    ck(r12['rows'][0]['rec_temp'] == 180, 'BOM \u8f93\u5165\u5e94\u6b63\u786e\u89e3\u6790\uff0c\u5b9e\u4e3a %s' % r12['rows'][0]['rec_temp'])
    ck(r12['temp_f'] == 356, '180 \u6444\u6c0f\u5e94\u4e3a 356 \u534e\u6c0f\uff0c\u5b9e\u4e3a %s' % r12['temp_f'])
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe5.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps({'temp_c': 220, 'items': [{'food': 'pizza'}]}))
    try:
        r12b = calc(json.loads(open(tmp, 'r', encoding='utf-8-sig').read()))
        ck(r12b['rows'][0]['rec_temp'] == 220, 'utf-8-sig \u8bfb\u53d6\u5e94\u6b63\u5e38\uff0c\u5b9e\u4e3a %s' % r12b['rows'][0]['rec_temp'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 13 \u975e\u6cd5\u8f93\u5165
    for bad, why in (
        ({'temp_c': 0}, '\u6e29\u5ea6\u4e3a 0'),
        ({'heat_state': '\u4e0d\u5b58\u5728\u7684\u72b6\u6001'}, '\u975e\u6cd5 heat_state'),
        ({'items': [{'food': '\u4e0d\u5b58\u5728\u7684\u98df\u6750'}]}, '\u672a\u77e5\u98df\u6750'),
        ({'temp_c': 180, 'items': [{'food': 'bread', 'temp_c': -5}]}, '\u8d1f\u6e29\u5ea6'),
    ):
        try:
            calc(bad)
            ck(False, '\u7528\u4f8b13 %s \u5e94\u629b\u9519' % why)
        except ValueError:
            ck(True, '')

    # 14 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r5)
    for key in ('\u6e29\u5ea6\u6362\u7b97\u8868', '\u98ce\u6247\u6a21\u5f0f', '\u9884\u70ed', '\u5f00\u95e8', '\u63a2\u9488\u6e29\u5ea6\u8ba1', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355'):
        ck(key in md, 'Markdown \u8f93\u51fa\u5e94\u542b\u7ae0\u8282 %s' % key)
    ck(len(r5['probe_notes']) == 5, '\u63a2\u9488\u8981\u70b9\u5e94\u4e3a 5 \u6761\uff0c\u5b9e\u4e3a %d' % len(r5['probe_notes']))
    ck(len(md.split('| 100 |')[0].splitlines()) > 0, '\u6362\u7b97\u8868\u5e94\u5df2\u751f\u6210')

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    msg = 'SELFTEST FAIL\n' + '\n'.join(errs) if errs else (
        'SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u534e\u6c0f\u6444\u6c0f\u53cc\u5411\u6362\u7b97/\u6362\u7b97\u8868\u53d6\u503c/\u5f80\u8fd4\u4e00\u81f4/\u65f6\u95f4\u6309\u6e29\u5ea6\u6298\u7b97/'
        '\u98ce\u6247\u6a21\u5f0f\u6298\u7b97/\u6613\u7126\u544a\u8b66/\u4e0d\u719f\u544a\u8b66/\u672a\u9884\u70ed\u544a\u8b66/\u539a\u98df\u6750\u65e0\u63a2\u9488\u544a\u8b66/\u6392\u5e8f/'
        'BOM \u4e24\u6761\u8def\u5f84/\u975e\u6cd5\u8f93\u5165/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u70e4\u7bb1\u6e29\u63a7\u4e0e\u70d8\u70e4\u65f6\u95f4\u6838\u67e5')
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