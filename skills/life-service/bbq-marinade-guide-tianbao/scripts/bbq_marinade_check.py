# -*- coding: utf-8 -*-
"""\u70e7\u70e4\u814c\u5236\u914d\u65b9\u4e0e\u65f6\u95f4\u6838\u67e5\uff1a\u65f6\u957f\u3001\u542b\u76d0\u91cf\u3001\u9178\u6027\u4e0e\u9176\u7c7b\u4e0a\u9650\u3001\u6e29\u5ea6\u4e0e\u536b\u751f\u7eaa\u5f8b\u3002

\u7528\u6cd5:
  python bbq_marinade_check.py --file marinade.json [--out result.md] [--format json]
  python bbq_marinade_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u98df\u6750: (\u952e, \u4e2d\u6587\u540d, \u814c\u5236\u4e0b\u9650\u5206\u949f, \u814c\u5236\u4e0a\u9650\u5206\u949f, \u5907\u6ce8)
ITEMS = [
    ('thin_slice', '\u8584\u8089\u7247\u3001\u8089\u4e32\u5c0f\u5757', 15, 30, '\u8d85\u8fc7\u4f1a\u8ba9\u8089\u51fa\u6c34\u53d8\u7d27'),
    ('poultry_bone', '\u9e21\u7fc5\u3001\u9e21\u817f\u3001\u9e21\u722a', 120, 240, '\u5e26\u9aa8\u5e26\u76ae\uff0c\u5473\u9053\u5230\u9aa8\u8fb9\u9700\u8981\u65f6\u95f4'),
    ('duck_part', '\u9e2d\u80f8\u3001\u9e2d\u817f', 120, 240, '\u8165\u5473\u91cd\uff0c\u53ef\u52a0\u5c11\u91cf\u6599\u9152\u4e0e\u59dc'),
    ('prawn_seafood', '\u867e\u3001\u8d1d\u3001\u9c7c\u7247', 10, 20, '\u8d85\u65f6\u51fa\u6c34\u53d8\u7d27\uff0c\u6d77\u9c9c\u5c24\u5176\u654f\u611f'),
    ('steak_lamb', '\u725b\u6392\u3001\u7f8a\u6392\u3001\u8089\u5757', 30, 120, '\u539a\u5207\u53d6\u4e0a\u9650\uff0c\u8584\u5207\u6309\u4e0b\u9650'),
    ('big_cut', '\u6574\u9e21\u817f\u3001\u6574\u6247\u6392\u9aa8\u3001\u5927\u5757\u732a\u9888\u80cc', 480, 1440, '\u957f\u65f6\u95f4\u814c\u5236\u8981\u628a\u542b\u76d0\u91cf\u538b\u5230 0.8 \u81f3 1.0'),
    ('veg', '\u852c\u83dc\u3001\u83cc\u83c7', 0, 10, '\u6492\u65e9\u4e86\u4f1a\u5927\u91cf\u51fa\u6c34\uff0c\u70e4\u51fa\u6765\u662f\u716e\u4e0d\u662f\u70e4'),
]

ITEM_MAP = dict((r[0], r) for r in ITEMS)

# \u542b\u76d0\u91cf\u533a\u95f4\uff08\u6309\u8089\u91cd\u767e\u5206\u6bd4\uff09
SALT = {'min': 0.8, 'max': 1.5, 'long_cut_max': 1.0}

# \u9178\u6027\u814c\u6599\u4e0a\u9650\u5206\u949f
ACID_LIMIT = {'default': 120, 'seafood': 30}
SEAFOOD_KINDS = ('prawn_seafood',)

# \u9176\u7c7b\u5ae9\u8089\u4e0a\u9650\u5206\u949f
ENZYME_LIMIT = 30

# \u51b7\u85cf\u4e0e\u5ba4\u6e29\u7eaa\u5f8b
FRIDGE = {'min': 0.0, 'max': 4.0}
ROOM_MINUTES_MAX = 30
REST_MIN = 15

# \u4e2d\u5fc3\u6e29\u5ea6\u8981\u6c42: (\u952e, \u4e2d\u6587\u540d, \u8981\u6c42\u6444\u6c0f\u5ea6)
MEAT_CLASS = [
    ('poultry', '\u79bd\u8089\u4e0e\u8089\u9985\u7c7b', 75.0),
    ('red', '\u732a\u725b\u7f8a\u8089\u5757\u4e0e\u8089\u997c', 71.0),
]

MEAT_CLASS_MAP = dict((m[0], m) for m in MEAT_CLASS)

# \u536b\u751f\u68c0\u67e5\u9879: (\u952e, \u4e2d\u6587\u540d, \u5408\u683c\u53e3\u5f84, \u4e0d\u5408\u683c\u539f\u56e0)
HYGIENE = [
    ('two_bowls', '\u814c\u751f\u8089\u4e0e\u5237\u9171\u5206\u4e24\u4e2a\u7897',
     '\u814c\u751f\u8089\u7684\u7897\u4e0d\u62ff\u6765\u5237\u9171',
     '\u62ff\u814c\u8fc7\u751f\u8089\u7684\u7897\u5237\u9171\u662f\u6700\u5178\u578b\u7684\u4ea4\u53c9\u6c61\u67d3\uff0c\u9171\u662f\u76f4\u63a5\u5165\u53e3\u7684\uff0c\u70e4\u591a\u9ad8\u7684\u6e29\u5ea6\u4e5f\u6551\u4e0d\u56de\u6765'),
    ('leftover_boiled', '\u5269\u4f59\u814c\u6599\u716e\u6cb8\u540e\u4f7f\u7528',
     '\u5269\u4e0b\u7684\u814c\u6599\u716e\u6cb8\u4e4b\u540e\u624d\u5f53\u9171',
     '\u814c\u6599\u91cc\u5df2\u6709\u751f\u8089\u6c41\u6db2\uff0c\u4e0d\u716e\u6cb8\u5c31\u662f\u751f\u7684'),
    ('skewer_soaked', '\u7af9\u7b7e\u5df2\u6d78\u6ce1\u4e0d\u5c11\u4e8e 30 \u5206\u949f',
     '\u7af9\u7b7e\u4e0b\u6c34\u6d78\u6ce1\u4e0d\u5c11\u4e8e 30 \u5206\u949f',
     '\u5e72\u7b7e\u5b50\u4f1a\u70e7\u65ad\uff0c\u8fd8\u4f1a\u8ba9\u4e32\u597d\u7684\u8089\u6389\u8fdb\u70ad\u91cc\u5e76\u8e7f\u8d77\u706b\u82d7\u628a\u8868\u9762\u70e4\u7126'),
]

# \u516d\u6761\u660e\u786e\u7981\u6b62\u7684\u64cd\u4f5c
BANNED = [
    '\u7528\u83e0\u841d\u3001\u6728\u74dc\u3001\u7315\u7334\u6843\u6c41\u814c\u5236\u8d85\u8fc7 30 \u5206\u949f',
    '\u62ff\u814c\u8fc7\u751f\u8089\u7684\u7897\u76f4\u63a5\u5237\u9171',
    '\u5728\u5ba4\u6e29\u4e0b\u814c\u5236\u8d85\u8fc7 30 \u5206\u949f',
    '\u5269\u4f59\u7684\u814c\u6599\u4e0d\u716e\u6cb8\u5c31\u5f53\u9171\u6dcb\u4e0a\u53bb',
    '\u542b\u76d0\u91cf\u8d85\u8fc7 1.5 \u53c8\u957f\u65f6\u95f4\u814c\u5236',
    '\u5e72\u7af9\u7b7e\u76f4\u63a5\u4e0a\u70e4\u7089',
]

LEVEL_HARD = '\u5fc5\u987b\u5904\u7406'
LEVEL_WEAK = '\u5b58\u5728\u8584\u5f31\u73af\u8282'
LEVEL_UNKNOWN = '\u5f85\u786e\u8ba4'
LEVEL_OK = '\u64cd\u4f5c\u89c4\u8303'


def num(v, name):
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        raise ValueError('%s \u5fc5\u987b\u662f\u6570\u5b57' % name)


def get_item(kind):
    key = str(kind or '').strip().lower()
    if key not in ITEM_MAP:
        raise ValueError('\u672a\u77e5\u7684\u98df\u6750\u79cd\u7c7b: %s\uff0c\u53ef\u9009 %s \u4e4b\u4e00' % (kind, '/'.join(ITEM_MAP.keys())))
    return ITEM_MAP[key]


def check_items(items):
    if items is None:
        items = []
    if not isinstance(items, list):
        raise ValueError('items \u5fc5\u987b\u662f\u5217\u8868')
    rows = []
    hard = []
    weak = []
    for raw in items:
        if not isinstance(raw, dict):
            raise ValueError('items \u7684\u6bcf\u4e00\u9879\u5fc5\u987b\u662f\u5bf9\u8c61')
        key, name, mn, mx, note = get_item(raw.get('kind'))
        minutes = num(raw.get('marinate_minutes'), 'marinate_minutes')
        salt = num(raw.get('salt_pct'), 'salt_pct')
        acid = raw.get('acid')
        enzyme = raw.get('enzyme')
        label = raw.get('name') or name
        rec = {'name': label, 'kind_name': name, 'note': note, 'minutes': minutes,
               'range': '%d \u81f3 %d' % (mn, mx), 'salt': salt}
        problems = []
        hard_p = False

        if minutes is None:
            rec['status'] = '\u672a\u68c0\u67e5'
            rec['why'] = '\u7f3a\u5c11\u814c\u5236\u5206\u949f\uff0c\u65e0\u6cd5\u5224\u5b9a'
            rows.append(rec)
            continue

        if minutes < mn:
            problems.append('\u814c\u5236 %g \u5206\u949f\u4f4e\u4e8e\u8be5\u7c7b\u98df\u6750\u4e0b\u9650 %d \u5206\u949f\uff0c\u4e2d\u5fc3\u4e0d\u5165\u5473' % (minutes, mn))
            weak.append(label)
        elif minutes > mx:
            problems.append('\u814c\u5236 %g \u5206\u949f\u9ad8\u4e8e\u8be5\u7c7b\u98df\u6750\u4e0a\u9650 %d \u5206\u949f\uff0c\u4f1a\u8ba9\u8089\u51fa\u6c34\u53d8\u7d27\u3001\u8868\u9762\u53d1\u67f4' % (minutes, mx))
            weak.append(label)

        if salt is None:
            rec['status'] = '\u672a\u68c0\u67e5'
            rec['why'] = '\u7f3a\u5c11\u542b\u76d0\u91cf\uff0c\u65e0\u6cd5\u5224\u5b9a\u54b8\u5ea6'
            rows.append(rec)
            continue
        if minutes > 240 and salt > SALT['long_cut_max']:
            problems.append('\u957f\u65f6\u95f4\u814c\u5236\u914d\u5408\u542b\u76d0 %g\uff0c\u5df2\u8d85\u8fc7\u957f\u65f6\u95f4\u814c\u5236\u7684 1.0 \u4e0a\u9650\uff0c\u6210\u54c1\u4f1a\u660e\u663e\u504f\u54b8' % salt)
            hard_p = True
        elif salt < SALT['min']:
            problems.append('\u542b\u76d0 %g \u4f4e\u4e8e 0.8 \u4e0b\u9650\uff0c\u5165\u5473\u4e0d\u8db3\u3001\u4e2d\u5fc3\u5be1\u6de1' % salt)
            weak.append(label)
        elif salt > SALT['max']:
            problems.append('\u542b\u76d0 %g \u9ad8\u4e8e 1.5 \u4e0a\u9650\uff0c\u504f\u54b8\u4e14\u814c\u5236\u65f6\u95f4\u8d8a\u957f\u8d8a\u54b8' % salt)
            hard_p = True

        if enzyme and str(enzyme).strip().lower() != 'none':
            if minutes > ENZYME_LIMIT:
                problems.append('\u4f7f\u7528\u9176\u7c7b\u5ae9\u8089\u5e76\u814c\u5236 %g \u5206\u949f\uff0c\u8d85\u8fc7 30 \u5206\u949f\u4e0a\u9650\uff0c\u808c\u8089\u7ea4\u7ef4\u4f1a\u88ab\u5206\u89e3\u5230\u53d1\u7c89\u53d1\u7cca' % minutes)
                hard_p = True

        if acid and str(acid).strip().lower() != 'none':
            limit = ACID_LIMIT['seafood'] if key in SEAFOOD_KINDS else ACID_LIMIT['default']
            if minutes > limit:
                problems.append('\u4f7f\u7528\u9178\u6027\u814c\u6599\u5e76\u814c\u5236 %g \u5206\u949f\uff0c\u8d85\u8fc7\u8be5\u7c7b %d \u5206\u949f\u4e0a\u9650\uff0c\u4f1a\u628a\u86cb\u767d\u8d28\u53d8\u6027\u5230\u53d1\u6e23\u677e\u6563'
                                % (minutes, limit))
                hard_p = True

        if problems:
            rec['status'] = '\u4e0d\u5408\u683c'
            rec['why'] = '\uff1b'.join(problems)
            if hard_p:
                hard.append(label)
        else:
            rec['status'] = '\u5408\u683c'
            rec['why'] = '\u65f6\u957f\u3001\u542b\u76d0\u91cf\u4e0e\u9178\u9176\u4e0a\u9650\u90fd\u7b26\u5408\u8be5\u7c7b\u98df\u6750\u7684\u53e3\u5f84'
        rows.append(rec)
    return rows, hard, weak


def check_hygiene(flags):
    if flags is None:
        flags = {}
    if not isinstance(flags, dict):
        raise ValueError('hygiene \u5fc5\u987b\u662f\u5bf9\u8c61')
    keys = [h[0] for h in HYGIENE]
    for k in flags:
        if str(k).strip().lower() not in keys:
            raise ValueError('\u672a\u77e5\u7684\u536b\u751f\u9879: %s\uff0c\u53ef\u9009\u9879\u89c1 HYGIENE \u8868' % k)
    rows = []
    hard = []
    unk = []
    for key, name, ok_desc, why in HYGIENE:
        v = flags.get(key)
        if v is None:
            rows.append({'name': name, 'status': '\u672a\u68c0\u67e5', 'desc': ok_desc, 'why': why})
            unk.append(name)
        elif v:
            rows.append({'name': name, 'status': '\u5408\u683c', 'desc': ok_desc, 'why': why})
        else:
            rows.append({'name': name, 'status': '\u4e0d\u5408\u683c', 'desc': ok_desc, 'why': why})
            hard.append(name)
    return rows, hard, unk


def calc(data):
    if not isinstance(data, dict):
        raise ValueError('\u8f93\u5165\u5fc5\u987b\u662f JSON \u5bf9\u8c61')

    rows, hard_items, weak_items = check_items(data.get('items'))
    hyg_rows, hyg_hard, hyg_unk = check_hygiene(data.get('hygiene'))

    fridge = num(data.get('fridge_temp'), 'fridge_temp')
    fridge_row = None
    fridge_hard = False
    if fridge is None:
        fridge_row = {'status': '\u672a\u68c0\u67e5', 'why': '\u672a\u63d0\u4f9b\u51b7\u85cf\u6e29\u5ea6'}
    elif fridge > FRIDGE['max']:
        fridge_row = {'value': fridge, 'status': '\u4e0d\u5408\u683c',
                      'why': '\u51b7\u85cf %.1f \u6444\u6c0f\u5ea6\u9ad8\u4e8e 4 \u6444\u6c0f\u5ea6\u4e0a\u9650\uff0c\u7ec6\u83cc\u7e41\u6b96\u901f\u5ea6\u660e\u663e\u4e0a\u5347' % fridge}
        fridge_hard = True
    elif fridge < FRIDGE['min']:
        fridge_row = {'value': fridge, 'status': '\u4e0d\u5408\u683c',
                      'why': '\u51b7\u85cf %.1f \u6444\u6c0f\u5ea6\u4f4e\u4e8e 0 \u6444\u6c0f\u5ea6\uff0c\u5df2\u51bb\u7ed3\u72b6\u6001\u4e0d\u9002\u5408\u814c\u5236\u5165\u5473' % fridge}
        fridge_hard = True
    else:
        fridge_row = {'value': fridge, 'status': '\u5408\u683c', 'why': '\u843d\u5728 0 \u81f3 4 \u6444\u6c0f\u5ea6\u533a\u95f4'}

    room = num(data.get('room_temp_minutes'), 'room_temp_minutes')
    room_row = None
    room_hard = False
    if room is None:
        room_row = {'status': '\u672a\u68c0\u67e5', 'why': '\u672a\u63d0\u4f9b\u5ba4\u6e29\u64cd\u4f5c\u65f6\u957f'}
    elif room > ROOM_MINUTES_MAX:
        room_row = {'value': room, 'status': '\u4e0d\u5408\u683c',
                    'why': '\u5ba4\u6e29\u64cd\u4f5c %g \u5206\u949f\u8d85\u8fc7 30 \u5206\u949f\u4e0a\u9650\uff0c\u8fd9\u662f\u814c\u5236\u73af\u8282\u6700\u5bb9\u6613\u5931\u5b88\u7684\u5730\u65b9' % room}
        room_hard = True
    else:
        room_row = {'value': room, 'status': '\u5408\u683c', 'why': '\u5ba4\u6e29\u64cd\u4f5c\u5728 30 \u5206\u949f\u4ee5\u5185'}

    cls = data.get('meat_class')
    center = num(data.get('target_center_temp'), 'target_center_temp')
    center_row = None
    center_hard = False
    if cls is not None and cls not in MEAT_CLASS_MAP:
        raise ValueError('\u672a\u77e5\u7684\u8089\u79cd\u7c7b\u522b: %s\uff0c\u53ef\u9009 %s \u4e4b\u4e00' % (cls, '/'.join(MEAT_CLASS_MAP.keys())))
    ckey, cname, creq = MEAT_CLASS_MAP.get(cls, (None, None, None))
    if center is None or cls is None:
        center_row = {'status': '\u672a\u68c0\u67e5', 'why': '\u7f3a\u5c11\u8089\u79cd\u7c7b\u522b\u6216\u4e2d\u5fc3\u6e29\u5ea6\u5b9e\u6d4b\u503c'}
    elif center < creq:
        center_row = {'value': center, 'status': '\u4e0d\u5408\u683c',
                      'why': '%s\u8981\u6c42\u4e2d\u5fc3\u6e29\u5ea6\u4e0d\u4f4e\u4e8e %.0f \u6444\u6c0f\u5ea6\uff0c\u5b9e\u6d4b %.1f \u6444\u6c0f\u5ea6\u5c5e\u4e8e\u672a\u719f\u900f'
                             % (cname, creq, center)}
        center_hard = True
    else:
        center_row = {'value': center, 'status': '\u5408\u683c',
                      'why': '%s\u8fbe\u5230 %.0f \u6444\u6c0f\u5ea6\u8981\u6c42' % (cname, creq)}

    rest = num(data.get('rest_minutes'), 'rest_minutes')
    rest_row = None
    rest_weak = False
    if rest is None:
        rest_row = {'status': '\u672a\u68c0\u67e5', 'why': '\u672a\u63d0\u4f9b\u70e4\u524d\u56de\u6e29\u65f6\u957f'}
    elif rest < REST_MIN:
        rest_row = {'value': rest, 'status': '\u504f\u4f4e',
                    'why': '\u56de\u6e29 %g \u5206\u949f\u5c11\u4e8e 15 \u5206\u949f\uff0c\u51b0\u8089\u76f4\u63a5\u4e0a\u706b\u5bb9\u6613\u5916\u7126\u91cc\u751f' % rest}
        rest_weak = True
    else:
        rest_row = {'value': rest, 'status': '\u5408\u683c', 'why': '\u5df2\u5b8c\u6210\u70e4\u524d\u56de\u6e29'}

    # \u5224\u5b9a: \u5148\u770b\u5b89\u5168\u7c7b\u771f\u5b9e\u7f3a\u9677, \u518d\u770b\u53e3\u5473\u7c7b\u7f3a\u9677, \u6700\u540e\u624d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574
    if fridge_hard or room_hard or center_hard or hyg_hard or hard_items:
        level = LEVEL_HARD
    elif weak_items or rest_weak:
        level = LEVEL_WEAK
    elif (fridge is None or room is None or center is None or rest is None
          or hyg_unk or any(x['status'] == '\u672a\u68c0\u67e5' for x in rows)):
        level = LEVEL_UNKNOWN
    else:
        level = LEVEL_OK

    return {
        'items_rows': rows,
        'hard_items': hard_items,
        'weak_items': weak_items,
        'hyg_rows': hyg_rows,
        'hyg_hard': hyg_hard,
        'fridge_row': fridge_row,
        'room_row': room_row,
        'center_row': center_row,
        'center_req': creq,
        'center_class': cname,
        'rest_row': rest_row,
        'level': level,
        'limits': {'salt': SALT, 'fridge': FRIDGE, 'room': ROOM_MINUTES_MAX,
                   'enzyme': ENZYME_LIMIT, 'acid': ACID_LIMIT},
    }


def render_md(r):
    L = []
    L.append('# \u70e7\u70e4\u814c\u5236\u6838\u67e5\u7ed3\u679c')
    L.append('')
    L.append('**\u603b\u4f53\u5224\u5b9a\uff1a%s**' % r['level'])
    L.append('')
    L.append('## \u4e00\u3001\u9010\u98df\u6750\u6838\u67e5')
    L.append('')
    if not r['items_rows']:
        L.append('\u672a\u63d0\u4f9b\u98df\u6750\u6e05\u5355\uff0c\u65e0\u6cd5\u6838\u67e5\u814c\u5236\u65f6\u957f\u4e0e\u542b\u76d0\u91cf\u3002')
    else:
        L.append('| \u98df\u6750 | \u79cd\u7c7b | \u814c\u5236\uff08\u5206\u949f\uff09 | \u63a8\u8350\u533a\u95f4 | \u542b\u76d0\u91cf | \u72b6\u6001 |')
        L.append('|---|---|---|---|---|---|')
        for row in r['items_rows']:
            L.append('| %s | %s | %s | %s | %s | %s |' % (
                row['name'], row['kind_name'],
                ('%g' % row['minutes']) if row['minutes'] is not None else '\u672a\u586b',
                row['range'],
                ('%g' % row['salt']) if row['salt'] is not None else '\u672a\u586b',
                row['status']))
        bad = [x for x in r['items_rows'] if x['status'] == '\u4e0d\u5408\u683c']
        if bad:
            L.append('')
            L.append('\u4e0d\u5408\u683c\u9879\u53ca\u539f\u56e0\uff1a')
            for row in bad:
                L.append('- **%s**\uff1a%s' % (row['name'], row['why']))
    L.append('')
    L.append('\u542b\u76d0\u91cf\u53e3\u5f84\uff1a0.8 \u81f3 1.5\uff08\u6309\u8089\u91cd\uff0c\u542b\u9171\u6cb9\u6298\u7b97\uff09\uff1b\u814c\u5236\u8d85\u8fc7 4 \u5c0f\u65f6\u7684\u5efa\u8bae\u538b\u5230 0.8 \u81f3 1.0\u3002')
    L.append('')
    L.append('## \u4e8c\u3001\u6e29\u5ea6\u4e0e\u5ba4\u6e29\u6838\u67e5')
    L.append('')
    L.append('| \u9879\u76ee | \u72b6\u6001 | \u8bf4\u660e |')
    L.append('|---|---|---|')
    if r['fridge_row'].get('value') is not None:
        L.append('| \u51b7\u85cf\u814c\u5236\u6e29\u5ea6\uff08\u6444\u6c0f\u5ea6\uff09 | %s | %s |' % (r['fridge_row']['status'], r['fridge_row']['why']))
    else:
        L.append('| \u51b7\u85cf\u814c\u5236\u6e29\u5ea6\uff08\u6444\u6c0f\u5ea6\uff09 | %s | %s |' % (r['fridge_row']['status'], r['fridge_row']['why']))
    if r['room_row'].get('value') is not None:
        L.append('| \u5ba4\u6e29\u64cd\u4f5c\uff08\u5206\u949f\uff09 | %s | %s |' % (r['room_row']['status'], r['room_row']['why']))
    else:
        L.append('| \u5ba4\u6e29\u64cd\u4f5c\uff08\u5206\u949f\uff09 | %s | %s |' % (r['room_row']['status'], r['room_row']['why']))
    L.append('')
    L.append('\u53e3\u5f84\uff1a\u51b7\u85cf 0 \u81f3 4 \u6444\u6c0f\u5ea6\uff0c\u5ba4\u6e29\u64cd\u4f5c\u7d2f\u8ba1\u4e0d\u8d85\u8fc7 30 \u5206\u949f\u3002')
    L.append('')
    L.append('## \u4e09\u3001\u4e2d\u5fc3\u6e29\u5ea6\u4e0e\u56de\u6e29')
    L.append('')
    L.append('| \u9879\u76ee | \u72b6\u6001 | \u8bf4\u660e |')
    L.append('|---|---|---|')
    L.append('| \u4e2d\u5fc3\u6e29\u5ea6 | %s | %s |' % (r['center_row']['status'], r['center_row']['why']))
    L.append('| \u70e4\u524d\u56de\u6e29 | %s | %s |' % (r['rest_row']['status'], r['rest_row']['why']))
    L.append('')
    L.append('\u4e2d\u5fc3\u6e29\u5ea6\u4ee5**\u63a2\u9488\u6e29\u5ea6\u8ba1\u63d2\u6700\u539a\u5904\u5b9e\u6d4b**\u4e3a\u51c6\uff0c\u5916\u89c2\u4e0e\u624b\u611f\u4e0d\u4f5c\u4e3a\u719f\u5ea6\u4f9d\u636e\u3002')
    L.append('')
    L.append('## \u56db\u3001\u536b\u751f\u68c0\u67e5\u9879')
    L.append('')
    L.append('| \u68c0\u67e5\u9879 | \u72b6\u6001 | \u5408\u683c\u53e3\u5f84 | \u4e0d\u5408\u683c\u7684\u539f\u56e0 |')
    L.append('|---|---|---|---|')
    for row in r['hyg_rows']:
        L.append('| %s | %s | %s | %s |' % (row['name'], row['status'], row['desc'], row['why']))
    if r['hyg_hard']:
        L.append('')
        L.append('\u4e0d\u5408\u683c\u9879\u53ca\u539f\u56e0\uff1a')
        for row in r['hyg_rows']:
            if row['status'] == '\u4e0d\u5408\u683c':
                L.append('- **%s**\uff1a%s' % (row['name'], row['why']))
    L.append('')
    L.append('## \u4e94\u3001\u516d\u6761\u660e\u786e\u7981\u6b62\u7684\u64cd\u4f5c')
    L.append('')
    for i, b in enumerate(BANNED, 1):
        L.append('%d. %s' % (i, b))
    L.append('')
    L.append('## \u516d\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355')
    L.append('')
    L.append('- [ ] \u6bcf\u79cd\u98df\u6750\u7684\u814c\u5236\u65f6\u957f\u90fd\u5728\u5bf9\u5e94\u533a\u95f4\u5185')
    L.append('- [ ] \u542b\u76d0\u91cf\uff08\u542b\u9171\u6cb9\u6298\u7b97\uff09\u5728 0.8 \u81f3 1.5 \u4e4b\u95f4')
    L.append('- [ ] \u4f7f\u7528\u9176\u7c7b\u5ae9\u8089\u7684\uff0c\u814c\u5236\u4e0d\u8d85\u8fc7 30 \u5206\u949f')
    L.append('- [ ] \u4f7f\u7528\u9178\u6027\u814c\u6599\u7684\uff0c\u814c\u5236\u672a\u8d85\u8fc7\u5bf9\u5e94\u4e0a\u9650')
    L.append('- [ ] \u814c\u5236\u5168\u7a0b\u5728 0 \u81f3 4 \u6444\u6c0f\u5ea6\u51b7\u85cf\uff0c\u5ba4\u6e29\u64cd\u4f5c\u4e0d\u8d85\u8fc7 30 \u5206\u949f')
    L.append('- [ ] \u814c\u751f\u8089\u7684\u7897\u548c\u5237\u9171\u7684\u7897\u662f\u4e24\u4e2a\u7897')
    L.append('- [ ] \u5269\u4f59\u814c\u6599\u5f53\u9171\u524d\u5df2\u716e\u6cb8')
    L.append('- [ ] \u7af9\u7b7e\u5df2\u6d78\u6ce1\u4e0d\u5c11\u4e8e 30 \u5206\u949f')
    L.append('- [ ] \u70e4\u524d\u56de\u6e29 15 \u81f3 20 \u5206\u949f')
    L.append('- [ ] \u63a2\u9488\u5b9e\u6d4b\u6700\u539a\u5904\u4e2d\u5fc3\u6e29\u5ea6\u8fbe\u5230\u8981\u6c42')
    L.append('')
    L.append('## \u4e03\u3001\u514d\u8d23')
    L.append('')
    L.append('\u672c\u7ed3\u679c\u4e3a\u5bb6\u5ead\u70e7\u70e4\u65b9\u6cd5\u8bba\u6574\u7406\uff0c\u4e0d\u68c0\u6d4b\u81f4\u75c5\u83cc\u3001\u4e0d\u5224\u65ad\u8089\u662f\u5426\u53d8\u8d28\uff0c\u4e0d\u6784\u6210\u98df\u54c1\u5b89\u5168\u5224\u5b9a\u7ed3\u8bba\u3002')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    base = {
        'items': [{'name': '\u9e21\u7fc5\u4e2d', 'kind': 'poultry_bone', 'marinate_minutes': 180,
                   'salt_pct': 1.2, 'acid': 'none', 'enzyme': 'none'}],
        'hygiene': {'two_bowls': True, 'leftover_boiled': True, 'skewer_soaked': True},
        'fridge_temp': 3,
        'room_temp_minutes': 20,
        'meat_class': 'poultry',
        'target_center_temp': 75,
        'rest_minutes': 15,
    }

    # 1 \u6b63\u4f8b
    r1 = calc(base)
    ck(r1['level'] == LEVEL_OK, '\u6b63\u4f8b\u5e94\u4e3a\u64cd\u4f5c\u89c4\u8303\uff0c\u5b9e\u4e3a %s' % r1['level'])
    ck(r1['items_rows'][0]['status'] == '\u5408\u683c', '\u9e21\u7fc5\u814c 180 \u5206\u949f\u542b\u76d0 1.2 \u5e94\u5224\u5408\u683c')

    # 2 \u53cd\u4f8b: \u51b7\u85cf\u6e29\u5ea6\u8d85\u6807
    r2 = calc(dict(base, fridge_temp=7))
    ck(r2['level'] == LEVEL_HARD, '\u51b7\u85cf 7 \u5ea6\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r2['level'])
    ck(r2['fridge_row']['status'] == '\u4e0d\u5408\u683c', '\u51b7\u85cf\u9879\u5e94\u5224\u4e0d\u5408\u683c')
    ck('\u7ec6\u83cc\u7e41\u6b96' in r2['fridge_row']['why'], '\u5fc5\u987b\u5e26\u51fa\u4e3a\u4ec0\u4e48\uff0c\u5b9e\u4e3a %s' % r2['fridge_row']['why'])

    # 3 \u53cd\u4f8b: \u5ba4\u6e29\u8d85\u65f6
    r3 = calc(dict(base, room_temp_minutes=45))
    ck(r3['level'] == LEVEL_HARD, '\u5ba4\u6e29 45 \u5206\u949f\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r3['level'])
    ck('\u6700\u5bb9\u6613\u5931\u5b88' in r3['room_row']['why'], '\u5fc5\u987b\u8bf4\u660e\u8fd9\u662f\u6700\u6613\u5931\u5b88\u9879\uff0c\u5b9e\u4e3a %s' % r3['room_row']['why'])

    # 4 \u53cd\u4f8b: \u9176\u7c7b\u8d85\u65f6
    r4 = calc(dict(base, items=[{'name': '\u725b\u8089', 'kind': 'steak_lamb',
                                 'marinate_minutes': 300, 'salt_pct': 1.0,
                                 'acid': 'none', 'enzyme': 'pineapple'}]))
    ck(r4['level'] == LEVEL_HARD, '\u83e0\u841d\u6c41\u814c 300 \u5206\u949f\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r4['level'])
    ck('\u53d1\u7c89\u53d1\u7cca' in r4['items_rows'][0]['why'], '\u5fc5\u987b\u8bf4\u660e\u4f1a\u53d1\u7c89\u53d1\u7cca\uff0c\u5b9e\u4e3a %s' % r4['items_rows'][0]['why'])

    # 5 \u9176\u7c7b\u5728\u9650\u5185\u5e94\u5408\u683c
    r5 = calc(dict(base, items=[{'name': '\u725b\u8089\u7247', 'kind': 'thin_slice',
                                 'marinate_minutes': 25, 'salt_pct': 1.0,
                                 'acid': 'none', 'enzyme': 'pineapple'}]))
    ck(r5['items_rows'][0]['status'] == '\u5408\u683c', '\u83e0\u841d\u6c41\u814c 25 \u5206\u949f\u5e94\u5224\u5408\u683c\uff0c\u5b9e\u4e3a %s' % r5['items_rows'][0]['status'])

    # 6 \u53cd\u4f8b: \u9178\u6027\u814c\u6599\u8d85\u65f6
    r6 = calc(dict(base, items=[{'name': '\u9e21\u7fc5', 'kind': 'poultry_bone',
                                 'marinate_minutes': 200, 'salt_pct': 1.0,
                                 'acid': 'vinegar', 'enzyme': 'none'}]))
    ck('\u53d1\u6e23' in r6['items_rows'][0]['why'], '\u9178\u6027\u8d85\u65f6\u5fc5\u987b\u8bf4\u660e\u53d1\u6e23\uff0c\u5b9e\u4e3a %s' % r6['items_rows'][0]['why'])
    ck(r6['level'] == LEVEL_HARD, '\u9178\u6027\u8d85\u65f6\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r6['level'])
    r6b = calc(dict(base, items=[{'name': '\u867e', 'kind': 'prawn_seafood',
                                  'marinate_minutes': 45, 'salt_pct': 1.0,
                                  'acid': 'lemon', 'enzyme': 'none'}]))
    ck('30 \u5206\u949f\u4e0a\u9650' in r6b['items_rows'][0]['why'], '\u6d77\u9c9c\u9178\u4e0a\u9650\u5e94\u4e3a 30 \u5206\u949f\uff0c\u5b9e\u4e3a %s' % r6b['items_rows'][0]['why'])

    # 7 \u53cd\u4f8b: \u6d77\u9c9c\u814c\u5236\u8fc7\u4e45
    r7 = calc(dict(base, items=[{'name': '\u867e', 'kind': 'prawn_seafood',
                                 'marinate_minutes': 300, 'salt_pct': 1.0,
                                 'acid': 'none', 'enzyme': 'none'}]))
    ck(r7['items_rows'][0]['status'] == '\u4e0d\u5408\u683c', '\u867e\u814c 300 \u5206\u949f\u5e94\u5224\u4e0d\u5408\u683c')
    ck('\u51fa\u6c34\u53d8\u7d27' in r7['items_rows'][0]['why'], '\u5fc5\u987b\u8bf4\u660e\u4f1a\u51fa\u6c34\u53d8\u7d27\uff0c\u5b9e\u4e3a %s' % r7['items_rows'][0]['why'])

    # 8 \u53cd\u4f8b: \u957f\u65f6\u95f4\u814c\u5236\u542b\u76d0\u504f\u9ad8
    r8 = calc(dict(base, items=[{'name': '\u5927\u6392', 'kind': 'big_cut',
                                 'marinate_minutes': 720, 'salt_pct': 1.4,
                                 'acid': 'none', 'enzyme': 'none'}]))
    ck(r8['level'] == LEVEL_HARD, '\u814c 12 \u5c0f\u65f6\u542b\u76d0 1.4 \u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r8['level'])
    ck('\u504f\u54b8' in r8['items_rows'][0]['why'], '\u5fc5\u987b\u8bf4\u660e\u504f\u54b8\uff0c\u5b9e\u4e3a %s' % r8['items_rows'][0]['why'])
    r8b = calc(dict(base, items=[{'name': '\u5927\u6392', 'kind': 'big_cut',
                                  'marinate_minutes': 720, 'salt_pct': 0.9,
                                  'acid': 'none', 'enzyme': 'none'}]))
    ck(r8b['items_rows'][0]['status'] == '\u5408\u683c', '\u957f\u65f6\u95f4\u814c\u542b\u76d0 0.9 \u5e94\u5224\u5408\u683c')

    # 9 \u53cd\u4f8b: \u542b\u76d0\u8fc7\u4f4e\u4e0e\u8fc7\u9ad8
    r9 = calc(dict(base, items=[{'name': '\u8089\u7247', 'kind': 'thin_slice',
                                 'marinate_minutes': 25, 'salt_pct': 0.5,
                                 'acid': 'none', 'enzyme': 'none'}]))
    ck('\u5165\u5473\u4e0d\u8db3' in r9['items_rows'][0]['why'], '\u542b\u76d0 0.5 \u5e94\u8bf4\u660e\u5165\u5473\u4e0d\u8db3')
    r9b = calc(dict(base, items=[{'name': '\u8089\u7247', 'kind': 'thin_slice',
                                  'marinate_minutes': 25, 'salt_pct': 2.0,
                                  'acid': 'none', 'enzyme': 'none'}]))
    ck('\u504f\u54b8' in r9b['items_rows'][0]['why'], '\u542b\u76d0 2.0 \u5e94\u8bf4\u660e\u504f\u54b8')

    # 10 \u53cd\u4f8b: \u4e2d\u5fc3\u6e29\u5ea6\u4e0d\u8db3
    r10 = calc(dict(base, target_center_temp=68))
    ck(r10['level'] == LEVEL_HARD, '\u79bd\u8089\u4e2d\u5fc3 68 \u5ea6\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r10['level'])
    ck('\u672a\u719f\u900f' in r10['center_row']['why'], '\u5fc5\u987b\u8bf4\u660e\u672a\u719f\u900f\uff0c\u5b9e\u4e3a %s' % r10['center_row']['why'])
    r10b = calc(dict(base, meat_class='red', target_center_temp=71))
    ck(r10b['center_row']['status'] == '\u5408\u683c', '\u732a\u725b\u7f8a\u8089\u997c 71 \u5ea6\u5e94\u5224\u5408\u683c')

    # 11 \u53cd\u4f8b: \u540c\u7897\u8638\u5237
    r11 = calc(dict(base, hygiene={'two_bowls': False, 'leftover_boiled': True, 'skewer_soaked': True}))
    ck(r11['level'] == LEVEL_HARD, '\u540c\u7897\u8638\u5237\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r11['level'])
    ck('\u814c\u751f\u8089\u4e0e\u5237\u9171\u5206\u4e24\u4e2a\u7897' in r11['hyg_hard'], '\u5e94\u70b9\u540d\u5206\u7897\u9879\uff0c\u5b9e\u4e3a %s' % r11['hyg_hard'])
    r11b = calc(dict(base, hygiene={'two_bowls': True, 'leftover_boiled': False, 'skewer_soaked': True}))
    ck('\u5269\u4f59\u814c\u6599\u716e\u6cb8\u540e\u4f7f\u7528' in r11b['hyg_hard'], '\u5e94\u70b9\u540d\u5269\u4f59\u814c\u6599\u9879\uff0c\u5b9e\u4e3a %s' % r11b['hyg_hard'])

    # 12 \u7af9\u7b7e\u672a\u6ce1
    r12 = calc(dict(base, hygiene={'two_bowls': True, 'leftover_boiled': True, 'skewer_soaked': False}))
    ck('\u7af9\u7b7e\u5df2\u6d78\u6ce1\u4e0d\u5c11\u4e8e 30 \u5206\u949f' in r12['hyg_hard'], '\u7af9\u7b7e\u672a\u6ce1\u5e94\u88ab\u70b9\u540d\uff0c\u5b9e\u4e3a %s' % r12['hyg_hard'])

    # 13 \u56de\u6e29\u4e0d\u8db3\u53ea\u7b97\u8584\u5f31\u73af\u8282
    r13 = calc(dict(base, rest_minutes=5))
    ck(r13['level'] == LEVEL_WEAK, '\u56de\u6e29\u4e0d\u8db3\u5e94\u5224\u8584\u5f31\u73af\u8282\uff0c\u5b9e\u4e3a %s' % r13['level'])

    # 14 \u5224\u5b9a\u5206\u652f\u987a\u5e8f: \u771f\u5b9e\u7f3a\u9677\u4e0d\u80fd\u88ab\u4fe1\u606f\u4e0d\u5168\u538b\u6210\u5f85\u786e\u8ba4
    r14 = calc(dict(base, room_temp_minutes=45, rest_minutes=None))
    ck(r14['level'] == LEVEL_HARD, '\u5ba4\u6e29\u8d85\u6807\u4e14\u7f3a\u56de\u6e29\u6570\u636e\u4ecd\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r14['level'])
    r14b = calc(dict(base, target_center_temp=None))
    ck(r14b['level'] == LEVEL_UNKNOWN, '\u65e0\u7f3a\u9677\u4f46\u7f3a\u4e2d\u5fc3\u6e29\u5ea6\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r14b['level'])

    # 15 BOM \u4e24\u6761\u8def\u5f84
    bom_text = '\ufeff' + json.dumps(dict(base, fridge_temp=8))
    r15 = calc(json.loads(bom_text.lstrip('\ufeff')))
    ck(r15['level'] == LEVEL_HARD, 'BOM \u5b57\u7b26\u4e32\u5e94\u80fd\u6b63\u786e\u89e3\u6790\uff0c\u5b9e\u4e3a %s' % r15['level'])
    ck(r15['fridge_row']['value'] == 8.0, 'BOM \u8f93\u5165\u51b7\u85cf\u5e94\u4e3a 8\uff0c\u5b9e\u4e3a %s' % r15['fridge_row']['value'])
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe_bbq.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps(dict(base, items=[{'name': '\u7f8a\u8089\u4e32', 'kind': 'steak_lamb',
                                              'marinate_minutes': 60, 'salt_pct': 1.0,
                                              'acid': 'none', 'enzyme': 'none'}])))
    try:
        loaded = json.loads(open(tmp, 'r', encoding='utf-8-sig').read())
        r15b = calc(loaded)
        ck(r15b['items_rows'][0]['kind_name'] == '\u725b\u6392\u3001\u7f8a\u6392\u3001\u8089\u5757',
           'utf-8-sig \u8bfb\u53d6\u5e94\u62ff\u5230\u725b\u6392\u7f8a\u6392\uff0c\u5b9e\u4e3a %s' % r15b['items_rows'][0]['kind_name'])
        ck(r15b['level'] == LEVEL_OK, '\u7f8a\u6392\u814c 60 \u5206\u949f\u542b\u76d0 1.0 \u5e94\u5224\u64cd\u4f5c\u89c4\u8303\uff0c\u5b9e\u4e3a %s' % r15b['level'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 16 \u975e\u6cd5\u8f93\u5165\u5fc5\u987b\u62a5\u9519
    for payload, why in (
        ({'items': [{'kind': 'unknown', 'marinate_minutes': 10, 'salt_pct': 1.0}]}, '\u672a\u77e5\u79cd\u7c7b'),
        ({'items': '\u4e0d\u662f\u5217\u8868'}, '\u98df\u6750\u975e\u5217\u8868'),
        ({'hygiene': {'\u62fc\u9519\u7684\u9879': True}}, '\u672a\u77e5\u536b\u751f\u9879'),
        ({'meat_class': 'fish'}, '\u672a\u77e5\u8089\u79cd\u7c7b\u522b'),
        ({'fridge_temp': '\u5f88\u51b7'}, '\u6e29\u5ea6\u975e\u6570\u5b57'),
        ({'hygiene': '\u4e0d\u662f\u5bf9\u8c61'}, '\u536b\u751f\u9879\u975e\u5bf9\u8c61'),
    ):
        try:
            calc(payload)
            ck(False, '\u7528\u4f8b16 %s \u5e94\u629b\u9519\u5374\u901a\u8fc7' % why)
        except ValueError:
            ck(True, '')
        except Exception as e:
            ck(False, '\u7528\u4f8b16 %s \u5e94\u629b ValueError\uff0c\u5b9e\u4e3a %s' % (why, e))

    # 17 \u8f93\u51fa\u7ed3\u6784\u4e0e\u8868\u89c4\u6a21
    md = render_md(r4)
    for key in ('\u603b\u4f53\u5224\u5b9a', '\u9010\u98df\u6750\u6838\u67e5', '\u6e29\u5ea6\u4e0e\u5ba4\u6e29\u6838\u67e5', '\u4e2d\u5fc3\u6e29\u5ea6\u4e0e\u56de\u6e29',
                '\u536b\u751f\u68c0\u67e5\u9879', '\u516d\u6761\u660e\u786e\u7981\u6b62\u7684\u64cd\u4f5c', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355', '\u514d\u8d23'):
        ck(key in md, 'Markdown \u8f93\u51fa\u5e94\u542b\u7ae0\u8282 %s' % key)
    ck(len(ITEMS) == 7, '\u98df\u6750\u79cd\u7c7b\u5e94 7 \u7c7b\uff0c\u5b9e\u4e3a %d' % len(ITEMS))
    ck(len(BANNED) == 6, '\u7981\u6b62\u9879\u5e94 6 \u6761\uff0c\u5b9e\u4e3a %d' % len(BANNED))
    ck(ENZYME_LIMIT == 30, '\u9176\u7c7b\u4e0a\u9650\u5e94\u4e3a 30 \u5206\u949f')
    ck(ACID_LIMIT['seafood'] == 30, '\u6d77\u9c9c\u9178\u4e0a\u9650\u5e94\u4e3a 30 \u5206\u949f')

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u6b63\u4f8b/\u51b7\u85cf\u8d85\u6807/\u5ba4\u6e29\u8d85\u65f6/\u9176\u7c7b\u8d85\u65f6\u4e0e\u5408\u683c/\u9178\u6027\u8d85\u65f6\u4e0e\u6d77\u9c9c\u4e0a\u9650/'
               '\u6d77\u9c9c\u814c\u5236\u8fc7\u4e45/\u957f\u65f6\u95f4\u814c\u542b\u76d0\u504f\u9ad8/\u542b\u76d0\u8fc7\u4f4e\u8fc7\u9ad8/\u4e2d\u5fc3\u6e29\u5ea6\u4e0d\u8db3\u4e0e\u533a\u5206/\u540c\u7897\u8638\u5237\u4e0e\u5269\u4f59\u814c\u6599/'
               '\u7af9\u7b7e\u672a\u6ce1/\u56de\u6e29\u4e0d\u8db3/\u5224\u5b9a\u5206\u652f\u987a\u5e8f/BOM \u4e24\u6761\u8def\u5f84/\u975e\u6cd5\u8f93\u5165/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u70e7\u70e4\u814c\u5236\u914d\u65b9\u4e0e\u65f6\u95f4\u6838\u67e5')
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
    target = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), '_last_result.txt')
    with open(target, 'w', encoding='utf-8') as f:
        f.write(out + '\n')
    print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % target)
    return 0


if __name__ == '__main__':
    sys.exit(main())

