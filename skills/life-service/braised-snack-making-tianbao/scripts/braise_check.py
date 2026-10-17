# -*- coding: utf-8 -*-
"""\u5364\u5473\u5236\u4f5c\u4e0e\u5364\u6c34\u517b\u62a4\u6838\u67e5\uff1a\u65f6\u95f4\u5339\u914d\u3001\u6e29\u5ea6\u7eaa\u5f8b\u3001\u542b\u76d0\u91cf\u3001\u8001\u5364\u517b\u62a4\u4e0e\u98df\u54c1\u5b89\u5168\u3002

\u7528\u6cd5:
  python braise_check.py --file braise.json [--out result.md] [--format json]
  python braise_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u98df\u6750: (\u952e, \u4e2d\u6587\u540d, \u5364\u5236\u4e0b\u9650\u5206\u949f, \u5364\u5236\u4e0a\u9650\u5206\u949f, \u6d78\u6ce1\u4e0b\u9650\u5206\u949f, \u5907\u6ce8)
ITEMS = [
    ('poultry_part', '\u9e21\u7fc5\u3001\u9e21\u722a', 15, 25, 30, '\u722a\u7c7b\u53ef\u5ef6\u957f\u65f6\u95f4\u66f4\u8f6f\u7cef'),
    ('whole_chicken', '\u6574\u9e21\u3001\u534a\u9e21', 30, 45, 30, '\u5173\u706b\u540e\u8fde\u540c\u6c64\u4e00\u8d77\u51b7\u5374\u66f4\u597d'),
    ('duck_part', '\u9e2d\u8116\u3001\u9e2d\u5934\u3001\u9e2d\u638c', 20, 30, 30, '\u8165\u5473\u91cd\uff0c\u712f\u6c34\u8981\u5f7b\u5e95'),
    ('pork_trotter', '\u732a\u8e44\u3001\u732a\u8098', 60, 90, 60, '\u80f6\u8d28\u91cd\uff0c\u5364\u6c34\u51b7\u5374\u4f1a\u7ed3\u51bb\u5c5e\u6b63\u5e38'),
    ('beef_shank', '\u725b\u8171', 60, 90, 60, '\u5fc5\u987b\u5f7b\u5e95\u51b7\u5374\u518d\u5207\uff0c\u5426\u5219\u6563\u788e'),
    ('pork_belly', '\u4e94\u82b1\u8089\u3001\u540e\u817f\u8089', 30, 45, 30, '\u5148\u714e\u4e00\u4e0b\u8868\u9762\u66f4\u9999\u5e76\u5b9a\u578b'),
    ('egg', '\u86cb\u7c7b', 8, 12, 240, '\u5265\u58f3\u540e\u4e0b\u9505\uff0c\u6ce1\u5f97\u8d8a\u4e45\u8272\u8d8a\u6df1'),
    ('tofu', '\u8c46\u5236\u54c1\uff08\u8c46\u5e72\u3001\u7d20\u9e21\uff09', 5, 10, 20, '\u6781\u6613\u5438\u54b8\uff0c\u65f6\u95f4\u77ed\u4e5f\u4e0d\u8981\u63d0\u9ad8\u542b\u76d0\u91cf'),
    ('root_veg', '\u6839\u830e\u7c7b\uff08\u85d5\u3001\u571f\u8c46\u3001\u6d77\u5e26\uff09', 3, 8, 10, '\u7d20\u83dc\u5355\u9505\u539f\u5219'),
]

ITEM_MAP = dict((r[0], r) for r in ITEMS)

# \u6e29\u5ea6\u7eaa\u5f8b\uff08\u6444\u6c0f\u5ea6\uff09
TEMP = {'min_ok': 85.0, 'max_ok': 95.0, 'low_fail': 80.0}

# \u542b\u76d0\u91cf\u533a\u95f4
SALT = {'min': 1.5, 'max': 2.5}

# \u5b58\u653e\u4e0e\u590d\u70ed\u53e3\u5f84
STORAGE = {'room_hours_max': 2.0, 'fridge_hours_max': 48.0, 'reheat_min': 70.0}

# \u53d8\u8d28\u56db\u9879\u4fe1\u53f7: (\u952e, \u4e2d\u6587\u540d, \u8bf4\u660e)
SPOILAGE = [
    ('white_film', '\u8868\u9762\u8d77\u767d\u819c', '\u610f\u5473\u7740\u4ea7\u819c\u9175\u6bcd\u5df2\u7ecf\u6210\u7fa4\u843d'),
    ('ropy', '\u62c9\u4e1d', '\u6311\u8d77\u6765\u80fd\u62c9\u4e1d'),
    ('sour', '\u9178\u5473\u6216\u998a\u5473', '\u51fa\u73b0\u9178\u5473\u3001\u998a\u5473\u3001\u8150\u8d25\u5473'),
    ('viscous', '\u53d1\u9ecf', '\u5364\u6c34\u89e6\u611f\u9ecf\u6ed1\u3001\u6302\u58c1\u53d1\u7a20'),
]

# \u516d\u6761\u660e\u786e\u7981\u6b62\u7684\u64cd\u4f5c
BANNED = [
    '\u5927\u706b\u6eda\u716e\u5364\u5236\uff08\u8089\u67f4\u3001\u5364\u6c34\u4e73\u5316\u53d1\u6d51\u53d1\u9178\u3001\u54b8\u5ea6\u5931\u63a7\uff09',
    '\u5364\u5b8c\u4e0d\u6d78\u6ce1\u76f4\u63a5\u5207\uff08\u5916\u9762\u54b8\u91cc\u9762\u6de1\uff09',
    '\u8001\u5364\u4f7f\u7528\u524d\u4e0d\u716e\u6cb8',
    '\u7d20\u83dc\u5c24\u5176\u662f\u8c46\u5236\u54c1\u8fdb\u4e3b\u9505\uff0c\u4e14\u7528\u5b8c\u7684\u5364\u6c34\u5012\u56de\u8001\u5364',
    '\u53d8\u8d28\u5364\u6c34\u6487\u6389\u8868\u5c42\u7ee7\u7eed\u7528',
    '\u4f7f\u7528\u4efb\u4f55\u785d\u76d0\u3001\u9632\u8150\u5242\u3001\u62a4\u8272\u5242',
]

LEVEL_DISCARD = '\u5fc5\u987b\u5f03\u7528'
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
        kind = raw.get('kind')
        row = get_item(kind)
        key, name, bmin, bmax, smin, note = row
        bm = num(raw.get('braise_minutes'), 'braise_minutes')
        sm = num(raw.get('soak_minutes'), 'soak_minutes')
        label = raw.get('name') or name
        rec = {'name': label, 'kind_name': name, 'note': note,
               'braise': bm, 'braise_range': '%d \u81f3 %d' % (bmin, bmax),
               'soak': sm, 'soak_min': smin}
        if bm is None or sm is None:
            rec['status'] = '\u672a\u68c0\u67e5'
            rec['why'] = '\u7f3a\u5c11\u5364\u5236\u5206\u949f\u6216\u6d78\u6ce1\u5206\u949f\uff0c\u65e0\u6cd5\u5224\u5b9a'
            rows.append(rec)
            continue
        problems = []
        if bm < bmin:
            problems.append('\u5364\u5236 %g \u5206\u949f\u4f4e\u4e8e\u8be5\u7c7b\u98df\u6750\u4e0b\u9650 %d \u5206\u949f\uff0c\u5185\u90e8\u672a\u719f\u900f' % (bm, bmin))
        elif bm > bmax:
            problems.append('\u5364\u5236 %g \u5206\u949f\u9ad8\u4e8e\u8be5\u7c7b\u98df\u6750\u4e0a\u9650 %d \u5206\u949f\uff0c\u8089\u8d28\u5bb9\u6613\u6563\u70c2' % (bm, bmax))
        # \u6d78\u6ce1\u4e0b\u9650: \u4e0d\u4f4e\u4e8e\u5364\u5236\u65f6\u95f4\u7684\u4e00\u534a, \u540c\u65f6\u4e0d\u4f4e\u4e8e\u8be5\u7c7b\u98df\u6750\u7684\u6d78\u6ce1\u4e0b\u9650
        need = max(smin, bm / 2.0)
        if sm < need:
            problems.append('\u6d78\u6ce1 %g \u5206\u949f\u4e0d\u8db3\uff08\u9700\u8981\u81f3\u5c11 %g \u5206\u949f\uff09\uff0c\u6210\u54c1\u53ea\u4f1a\u8868\u5c42\u54b8\u3001\u91cc\u9762\u6de1' % (sm, need))
        if problems:
            rec['status'] = '\u4e0d\u5408\u683c'
            rec['why'] = '\uff1b'.join(problems)
            rows.append(rec)
            if sm < bm / 2.0 or bm < bmin:
                hard.append(label)
            else:
                weak.append(label)
        else:
            rec['status'] = '\u5408\u683c'
            rec['why'] = '\u5364\u5236\u4e0e\u6d78\u6ce1\u90fd\u7b26\u5408\u8be5\u7c7b\u98df\u6750\u7684\u53e3\u5f84'
            rows.append(rec)
    return rows, hard, weak


def check_spoilage(flags):
    if flags is None:
        flags = {}
    if not isinstance(flags, dict):
        raise ValueError('spoilage \u5fc5\u987b\u662f\u5bf9\u8c61')
    keys = [s[0] for s in SPOILAGE]
    for k in flags:
        if str(k).strip().lower() not in keys:
            raise ValueError('\u672a\u77e5\u7684\u53d8\u8d28\u4fe1\u53f7: %s\uff0c\u53ef\u9009\u9879\u89c1 SPOILAGE \u8868' % k)
    hit = []
    rows = []
    unk = []
    for key, name, desc in SPOILAGE:
        v = flags.get(key)
        if v is True:
            hit.append(name)
            rows.append({'name': name, 'status': '\u51fa\u73b0', 'desc': desc})
        elif v is False:
            rows.append({'name': name, 'status': '\u672a\u51fa\u73b0', 'desc': desc})
        else:
            rows.append({'name': name, 'status': '\u672a\u68c0\u67e5', 'desc': desc})
            unk.append(name)
    return rows, hit, unk


def calc(data):
    if not isinstance(data, dict):
        raise ValueError('\u8f93\u5165\u5fc5\u987b\u662f JSON \u5bf9\u8c61')

    brine = data.get('brine') or {}
    if not isinstance(brine, dict):
        raise ValueError('brine \u5fc5\u987b\u662f\u5bf9\u8c61')

    rows, hard_items, weak_items = check_items(data.get('items'))
    spoil_rows, spoil_hit, spoil_unk = check_spoilage(data.get('spoilage'))

    # \u6e29\u5ea6\u6838\u67e5
    pot = num(data.get('pot_temp_c'), 'pot_temp_c')
    rolling = data.get('rolling_boil')
    temp_row = None
    temp_hard = False
    if pot is not None:
        if rolling is True:
            status = '\u4e0d\u5408\u683c'
            why = '\u5927\u706b\u6eda\u716e\u4f1a\u8ba9\u808c\u8089\u7ea4\u7ef4\u6536\u7f29\u53d8\u67f4\u3001\u8102\u80aa\u4e73\u5316\u4f7f\u5364\u6c34\u53d1\u6d51\u53d1\u9178\u3001\u6c64\u6c41\u84b8\u53d1\u5bfc\u81f4\u54b8\u5ea6\u5931\u63a7'
            temp_hard = True
        elif pot > TEMP['max_ok']:
            status = '\u504f\u9ad8'
            why = '\u9ad8\u4e8e 95 \u6444\u6c0f\u5ea6\uff0c\u63a5\u8fd1\u6cb8\u817e\uff0c\u5e94\u7acb\u5373\u8f6c\u6700\u5c0f\u706b\u4fdd\u6301\u867e\u773c\u6c34'
        elif pot < TEMP['low_fail']:
            status = '\u4e0d\u5408\u683c'
            why = '\u4f4e\u4e8e 80 \u6444\u6c0f\u5ea6\uff0c\u4fdd\u6e29\u4e0d\u8db3\uff0c\u5165\u5473\u6162\u4e14\u53d8\u8d28\u98ce\u9669\u4e0a\u5347'
            temp_hard = True
        elif pot < TEMP['min_ok']:
            status = '\u504f\u4f4e'
            why = '\u4f4e\u4e8e 85 \u6444\u6c0f\u5ea6\u76ee\u6807\u4e0b\u9650\uff0c\u53ef\u7565\u5fae\u8c03\u5927\u706b\u5230 85 \u81f3 95 \u6444\u6c0f\u5ea6\u533a\u95f4'
        else:
            status = '\u8fbe\u6807'
            why = '\u843d\u5728 85 \u81f3 95 \u6444\u6c0f\u5ea6\u7684\u5fae\u6cb8\u533a\u95f4'
        temp_row = {'value': pot, 'status': status, 'why': why,
                    'range': '%.0f \u81f3 %.0f' % (TEMP['min_ok'], TEMP['max_ok'])}

    # \u542b\u76d0\u91cf\u6838\u67e5
    sal = num(brine.get('salinity_pct'), 'salinity_pct')
    salt_row = None
    salt_bad = salt_missing = False
    if sal is not None:
        if sal < SALT['min']:
            status = '\u4e0d\u5408\u683c'
            why = '\u4f4e\u4e8e 1.5\uff0c\u5165\u5473\u4e0d\u8db3\u4e14\u6291\u83cc\u80fd\u529b\u4e0b\u964d\uff0c\u5e38\u6e29\u5b58\u653e\u98ce\u9669\u4e0a\u5347'
            salt_bad = True
        elif sal > SALT['max']:
            status = '\u4e0d\u5408\u683c'
            why = '\u9ad8\u4e8e 2.5\uff0c\u8fc7\u54b8\u4e14\u4f1a\u63a9\u76d6\u5364\u6c34\u5f00\u59cb\u53d8\u8d28\u7684\u9178\u5473\uff0c\u8ba9\u4eba\u9519\u8fc7\u5224\u5e9f\u7a97\u53e3'
            salt_bad = True
        else:
            status = '\u8fbe\u6807'
            why = '\u843d\u5728 1.5 \u81f3 2.5 \u533a\u95f4\uff0c\u6309\u5364\u6c34\u603b\u91cd\u8ba1\u5e76\u5df2\u6298\u7b97\u9171\u6cb9\u5e26\u5165\u7684\u76d0'
        salt_row = {'value': sal, 'status': status, 'why': why}
    else:
        salt_missing = True

    # \u517b\u62a4\u52a8\u4f5c
    care_rows = []
    care_hard = []
    care_weak = []
    bo = brine.get('boiled_before_use')
    if bo is None:
        care_rows.append({'name': '\u8001\u5364\u7528\u524d\u716e\u6cb8\u4e0d\u5c11\u4e8e 5 \u5206\u949f', 'status': '\u672a\u68c0\u67e5',
                          'why': '\u51b7\u85cf\u53ea\u662f\u5ef6\u7f13\u4e0d\u662f\u6740\u83cc'})
    elif bo:
        care_rows.append({'name': '\u8001\u5364\u7528\u524d\u716e\u6cb8\u4e0d\u5c11\u4e8e 5 \u5206\u949f', 'status': '\u5408\u683c',
                          'why': '\u65e2\u6740\u83cc\u4e5f\u5524\u9192\u9999\u5473'})
    else:
        care_rows.append({'name': '\u8001\u5364\u7528\u524d\u716e\u6cb8\u4e0d\u5c11\u4e8e 5 \u5206\u949f', 'status': '\u4e0d\u5408\u683c',
                          'why': '\u51b7\u85cf\u53ea\u662f\u5ef6\u7f13\u4e0d\u662f\u6740\u83cc\uff0c\u53d6\u51fa\u76f4\u63a5\u4f7f\u7528\u662f\u5b89\u5168\u7f3a\u9677'})
        care_hard.append('\u8001\u5364\u7528\u524d\u672a\u716e\u6cb8')
    fi = brine.get('filtered_after_use')
    if fi is None:
        care_rows.append({'name': '\u7528\u540e\u8fc7\u6ee4\u4e0e\u716e\u6cb8', 'status': '\u672a\u68c0\u67e5',
                          'why': '\u6b8b\u6e23\u662f\u4e0b\u6b21\u9178\u8d25\u7684\u79cd\u5b50'})
    elif fi:
        care_rows.append({'name': '\u7528\u540e\u8fc7\u6ee4\u4e0e\u716e\u6cb8', 'status': '\u5408\u683c',
                          'why': '\u5df2\u5b8c\u6210\u635e\u51fa\u3001\u7ec6\u7b5b\u3001\u716e\u6cb8\u6d41\u7a0b'})
    else:
        care_rows.append({'name': '\u7528\u540e\u8fc7\u6ee4\u4e0e\u716e\u6cb8', 'status': '\u4e0d\u5408\u683c',
                          'why': '\u672a\u8fc7\u6ee4\u6b8b\u6e23\uff0c\u4e0b\u4e00\u6b21\u9178\u8d25\u7684\u79cd\u5b50\u5df2\u7559\u5728\u9505\u91cc'})
        care_weak.append('\u7528\u540e\u672a\u8fc7\u6ee4')

    # \u7d20\u83dc\u5355\u9505
    veg_row = None
    veg_hard = False
    veg = data.get('veg_in_main_pot')
    if veg is None:
        veg_row = {'status': '\u672a\u68c0\u67e5', 'why': '\u9700\u8981\u786e\u8ba4\u672c\u6b21\u662f\u5426\u653e\u4e86\u8c46\u5236\u54c1\u3001\u6839\u830e\u6216\u83cc\u83c7'}
    elif veg is not True and veg is not False:
        raise ValueError('veg_in_main_pot \u5fc5\u987b\u662f\u5e03\u5c14\u503c\u6216\u7559\u7a7a')
    elif veg:
        veg_row = {'status': '\u4e0d\u5408\u683c',
                   'why': '\u7d20\u83dc\u5e26\u5165\u5927\u91cf\u6c34\u5206\u7a00\u91ca\u5364\u6c34\uff0c\u8c46\u5236\u54c1\u7684\u86cb\u767d\u8d28\u4e0e\u7cd6\u5206\u662f\u6742\u83cc\u57f9\u517b\u57fa\uff0c\u662f\u8001\u5364\u9178\u8d25\u7684\u5934\u53f7\u6210\u56e0'}
        veg_hard = True
    else:
        veg_row = {'status': '\u5408\u683c', 'why': '\u7d20\u83dc\u5355\u72ec\u8d77\u5c0f\u9505\uff0c\u7528\u5b8c\u7684\u5364\u6c34\u672a\u5012\u56de'}

    # \u5b58\u653e\u4e0e\u590d\u70ed
    cool = num(data.get('cool_hours'), 'cool_hours')
    cool_row = None
    cool_hard = False
    if cool is None:
        cool_row = {'status': '\u672a\u68c0\u67e5', 'why': '\u5ba4\u6e29\u653e\u7f6e\u65f6\u957f\u672a\u586b'}
    elif cool > STORAGE['room_hours_max']:
        cool_row = {'value': cool, 'status': '\u4e0d\u5408\u683c',
                    'why': '\u5ba4\u6e29\u653e\u7f6e %g \u5c0f\u65f6\u8d85\u8fc7 2 \u5c0f\u65f6\u4e0a\u9650\uff0c4 \u81f3 60 \u6444\u6c0f\u5ea6\u662f\u7ec6\u83cc\u5feb\u901f\u7e41\u6b96\u533a\u95f4' % cool}
        cool_hard = True
    else:
        cool_row = {'value': cool, 'status': '\u5408\u683c', 'why': '\u5728 2 \u5c0f\u65f6\u5185\u8fdb\u5165\u51b7\u85cf'}

    stored = num(data.get('stored_hours'), 'stored_hours')
    stored_row = None
    stored_hard = False
    if stored is None:
        stored_row = {'status': '\u672a\u68c0\u67e5', 'why': '\u51b7\u85cf\u5b58\u653e\u65f6\u957f\u672a\u586b'}
    elif stored > STORAGE['fridge_hours_max']:
        stored_row = {'value': stored, 'status': '\u4e0d\u5408\u683c',
                      'why': '\u51b7\u85cf %g \u5c0f\u65f6\u8d85\u8fc7 48 \u5c0f\u65f6\u4e0a\u9650\uff0c\u98ce\u5473\u4e0e\u5b89\u5168\u6027\u90fd\u4e0d\u53ef\u63a7' % stored}
        stored_hard = True
    else:
        stored_row = {'value': stored, 'status': '\u5408\u683c', 'why': '\u5728 48 \u5c0f\u65f6\u4ee5\u5185'}

    reheat = num(data.get('reheat_temp'), 'reheat_temp')
    reheat_row = None
    reheat_hard = False
    if reheat is None:
        reheat_row = {'status': '\u672a\u68c0\u67e5', 'why': '\u590d\u70ed\u6e29\u5ea6\u672a\u586b'}
    elif reheat < STORAGE['reheat_min']:
        reheat_row = {'value': reheat, 'status': '\u4e0d\u5408\u683c',
                      'why': '\u590d\u70ed\u5230 %g \u6444\u6c0f\u5ea6\uff0c\u4f4e\u4e8e 70 \u6444\u6c0f\u5ea6\u4e2d\u5fc3\u6e29\u5ea6\u8981\u6c42\uff0c\u7b49\u4e8e\u53ea\u52a0\u70ed\u4e86\u8868\u9762' % reheat}
        reheat_hard = True
    else:
        reheat_row = {'value': reheat, 'status': '\u5408\u683c', 'why': '\u8fbe\u5230 70 \u6444\u6c0f\u5ea6\u4ee5\u4e0a'}

    # \u5224\u5b9a: \u53d8\u8d28\u4fe1\u53f7\u6700\u9ad8\u4f18\u5148, \u5176\u6b21\u98df\u54c1\u5b89\u5168\u7c7b\u7f3a\u9677, \u518d\u6b21\u53e3\u5473\u4e0e\u65f6\u95f4\u9879,
    # \u6700\u540e\u624d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574\u3002
    if spoil_hit:
        level = LEVEL_DISCARD
    elif (temp_hard or care_hard or veg_hard or cool_hard or stored_hard
          or reheat_hard or (salt_bad and brine.get('storage') != 'fridge')):
        level = LEVEL_HARD
    elif hard_items or salt_bad:
        level = LEVEL_HARD
    elif weak_items or care_weak or (temp_row and temp_row['status'] == '\u504f\u9ad8'):
        level = LEVEL_WEAK
    elif (temp_row is None or spoil_unk
          or veg_row['status'] == '\u672a\u68c0\u67e5'
          or any(x['status'] == '\u672a\u68c0\u67e5' for x in (cool_row, stored_row, reheat_row))
          or any(x['status'] == '\u672a\u68c0\u67e5' for x in rows)
          or any(x['status'] == '\u672a\u68c0\u67e5' for x in care_rows)
          or salt_missing):
        level = LEVEL_UNKNOWN
    else:
        level = LEVEL_OK

    return {
        'items_rows': rows,
        'hard_items': hard_items,
        'weak_items': weak_items,
        'temp_row': temp_row,
        'salt_row': salt_row,
        'salt_missing': salt_missing,
        'care_rows': care_rows,
        'veg_row': veg_row,
        'cool_row': cool_row,
        'stored_row': stored_row,
        'reheat_row': reheat_row,
        'spoil_rows': spoil_rows,
        'spoil_hit': spoil_hit,
        'spoil_unk': spoil_unk,
        'level': level,
        'limits': {'temp': TEMP, 'salt': SALT, 'storage': STORAGE},
    }


def render_md(r):
    L = []
    L.append('# \u5364\u5473\u5236\u4f5c\u4e0e\u5364\u6c34\u517b\u62a4\u6838\u67e5\u7ed3\u679c')
    L.append('')
    L.append('**\u603b\u4f53\u5224\u5b9a\uff1a%s**' % r['level'])
    L.append('')
    L.append('## \u4e00\u3001\u53d8\u8d28\u4fe1\u53f7\uff08\u6700\u9ad8\u4f18\u5148\u7ea7\uff09')
    L.append('')
    L.append('| \u4fe1\u53f7 | \u72b6\u6001 | \u8bf4\u660e |')
    L.append('|---|---|---|')
    for row in r['spoil_rows']:
        L.append('| %s | %s | %s |' % (row['name'], row['status'], row['desc']))
    if r['spoil_hit']:
        L.append('')
        L.append('> \u51fa\u73b0\u300c%s\u300d\uff0c**\u6574\u9505\u5f03\u7528**\u3002\u638f\u6389\u8868\u5c42\u7ee7\u7eed\u7528\u4e0d\u7b97\u5904\u7406\uff0c\u9709\u83cc\u4ee3\u8c22\u4ea7\u7269\u5df2\u6269\u6563\u5230\u6574\u9505\u3002'
                 % '\u3001'.join(r['spoil_hit']))
    L.append('')
    L.append('## \u4e8c\u3001\u98df\u6750\u65f6\u95f4\u4e0e\u6d78\u6ce1')
    L.append('')
    if not r['items_rows']:
        L.append('\u672a\u63d0\u4f9b\u98df\u6750\u6e05\u5355\uff0c\u65e0\u6cd5\u6838\u67e5\u65f6\u95f4\u4e0e\u6d78\u6ce1\u3002')
    else:
        L.append('| \u98df\u6750 | \u79cd\u7c7b | \u5364\u5236\uff08\u5206\u949f\uff09 | \u63a8\u8350\u533a\u95f4 | \u6d78\u6ce1\uff08\u5206\u949f\uff09 | \u6d78\u6ce1\u4e0b\u9650 | \u72b6\u6001 |')
        L.append('|---|---|---|---|---|---|---|')
        for row in r['items_rows']:
            L.append('| %s | %s | %s | %s | %s | %d | %s |' % (
                row['name'], row['kind_name'],
                ('%g' % row['braise']) if row['braise'] is not None else '\u672a\u586b',
                row['braise_range'],
                ('%g' % row['soak']) if row['soak'] is not None else '\u672a\u586b',
                row['soak_min'], row['status']))
        bad = [x for x in r['items_rows'] if x['status'] == '\u4e0d\u5408\u683c']
        if bad:
            L.append('')
            L.append('\u4e0d\u5408\u683c\u9879\u53ca\u539f\u56e0\uff1a')
            for row in bad:
                L.append('- **%s**\uff1a%s' % (row['name'], row['why']))
    L.append('')
    L.append('## \u4e09\u3001\u6e29\u5ea6\u7eaa\u5f8b')
    L.append('')
    if r['temp_row'] is None:
        L.append('\u672a\u63d0\u4f9b\u9505\u6e29\u6570\u636e\uff0c\u65e0\u6cd5\u6838\u67e5\u3002\u76ee\u6807\u533a\u95f4 85 \u81f3 95 \u6444\u6c0f\u5ea6\uff0c\u7981\u6b62\u5927\u706b\u6eda\u716e\u3002')
    else:
        t = r['temp_row']
        L.append('| \u5b9e\u6d4b\uff08\u6444\u6c0f\u5ea6\uff09 | \u76ee\u6807\u533a\u95f4 | \u72b6\u6001 | \u8bf4\u660e |')
        L.append('|---|---|---|---|')
        L.append('| %.1f | %s | %s | %s |' % (t['value'], t['range'], t['status'], t['why']))
    L.append('')
    L.append('## \u56db\u3001\u5364\u6c34\u542b\u76d0\u91cf')
    L.append('')
    if r['salt_row'] is None:
        L.append('\u672a\u63d0\u4f9b\u542b\u76d0\u91cf\uff0c\u65e0\u6cd5\u6838\u67e5\u3002\u5efa\u8bae\u53e3\u5f84 1.5 \u81f3 2.5\uff08\u6309\u5364\u6c34\u603b\u91cd\uff0c\u542b\u9171\u6cb9\u6298\u7b97\uff09\u3002')
    else:
        s = r['salt_row']
        L.append('| \u5b9e\u6d4b | \u5efa\u8bae\u533a\u95f4 | \u72b6\u6001 | \u8bf4\u660e |')
        L.append('|---|---|---|---|')
        L.append('| %.2f | 1.5 \u81f3 2.5 | %s | %s |' % (s['value'], s['status'], s['why']))
    L.append('')
    L.append('## \u4e94\u3001\u8001\u5364\u517b\u62a4\u4e0e\u7d20\u83dc\u5355\u9505')
    L.append('')
    L.append('| \u9879\u76ee | \u72b6\u6001 | \u8bf4\u660e |')
    L.append('|---|---|---|')
    for row in r['care_rows']:
        L.append('| %s | %s | %s |' % (row['name'], row['status'], row['why']))
    L.append('| \u7d20\u83dc\u5355\u9505\u539f\u5219 | %s | %s |' % (r['veg_row']['status'], r['veg_row']['why']))
    L.append('')
    L.append('## \u516d\u3001\u5b58\u653e\u4e0e\u590d\u70ed')
    L.append('')
    L.append('| \u9879\u76ee | \u72b6\u6001 | \u8bf4\u660e |')
    L.append('|---|---|---|')
    L.append('| \u5ba4\u6e29\u653e\u7f6e | %s | %s |' % (r['cool_row']['status'], r['cool_row']['why']))
    L.append('| \u51b7\u85cf\u5b58\u653e | %s | %s |' % (r['stored_row']['status'], r['stored_row']['why']))
    L.append('| \u590d\u70ed\u6e29\u5ea6 | %s | %s |' % (r['reheat_row']['status'], r['reheat_row']['why']))
    L.append('')
    L.append('\u53e3\u5f84\uff1a\u5ba4\u6e29\u4e0d\u8d85\u8fc7 2 \u5c0f\u65f6\u3001\u51b7\u85cf\u4e0d\u8d85\u8fc7 48 \u5c0f\u65f6\u3001\u590d\u70ed\u4e2d\u5fc3\u6e29\u5ea6\u4e0d\u4f4e\u4e8e 70 \u6444\u6c0f\u5ea6\u3002')
    L.append('')
    L.append('## \u4e03\u3001\u516d\u6761\u660e\u786e\u7981\u6b62\u7684\u64cd\u4f5c')
    L.append('')
    for i, b in enumerate(BANNED, 1):
        L.append('%d. %s' % (i, b))
    L.append('')
    L.append('## \u516b\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355')
    L.append('')
    L.append('- [ ] \u5364\u6c34\u542b\u76d0\u91cf\u5728 1.5 \u81f3 2.5 \u4e4b\u95f4\uff08\u542b\u9171\u6cb9\u6298\u7b97\uff09')
    L.append('- [ ] \u5364\u5236\u5168\u7a0b\u4fdd\u6301 85 \u81f3 95 \u6444\u6c0f\u5ea6\uff0c\u6ca1\u6709\u5927\u706b\u6eda\u716e')
    L.append('- [ ] \u6bcf\u79cd\u98df\u6750\u7684\u6d78\u6ce1\u65f6\u95f4\u4e0d\u5c11\u4e8e\u5176\u5364\u5236\u65f6\u95f4\u7684\u4e00\u534a')
    L.append('- [ ] \u8001\u5364\u8fd9\u6b21\u4f7f\u7528\u524d\u716e\u6cb8\u4e86\u4e0d\u5c11\u4e8e 5 \u5206\u949f')
    L.append('- [ ] \u7528\u540e\u5df2\u5b8c\u6210\u8fc7\u6ee4\u3001\u716e\u6cb8\u3001\u6487\u6cb9')
    L.append('- [ ] \u7d20\u83dc\uff08\u5c24\u5176\u8c46\u5236\u54c1\uff09\u6ca1\u6709\u8fdb\u4e3b\u9505')
    L.append('- [ ] \u6210\u54c1\u51fa\u9505\u540e 2 \u5c0f\u65f6\u5185\u8fdb\u5165\u51b7\u85cf')
    L.append('- [ ] \u51b7\u85cf\u4e0d\u8d85\u8fc7 48 \u5c0f\u65f6\uff0c\u590d\u70ed\u5230\u4e2d\u5fc3\u6e29\u5ea6 70 \u6444\u6c0f\u5ea6\u4ee5\u4e0a')
    L.append('- [ ] \u5c1d\u8fc7\u4e00\u904d\uff1a\u6ca1\u6709\u9178\u3001\u998a\u3001\u9ecf\u6ed1\uff0c\u8868\u9762\u6ca1\u6709\u767d\u819c')
    L.append('')
    L.append('## \u4e5d\u3001\u514d\u8d23')
    L.append('')
    L.append('\u672c\u7ed3\u679c\u4e3a\u5bb6\u5ead\u53a8\u623f\u65b9\u6cd5\u8bba\u6574\u7406\uff0c\u4e0d\u68c0\u6d4b\u4e9a\u785d\u9178\u76d0\u4e0e\u81f4\u75c5\u83cc\uff0c\u4e0d\u6784\u6210\u98df\u54c1\u5b89\u5168\u5224\u5b9a\u7ed3\u8bba\u3002')
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
        'brine': {'salinity_pct': 1.8, 'boiled_before_use': True,
                  'filtered_after_use': True, 'storage': 'fridge', 'age_days': 40},
        'pot_temp_c': 93,
        'rolling_boil': False,
        'items': [{'name': '\u725b\u8171', 'kind': 'beef_shank', 'braise_minutes': 70, 'soak_minutes': 90}],
        'veg_in_main_pot': False,
        'cool_hours': 1.5,
        'stored_hours': 20,
        'reheat_temp': 72,
        'spoilage': {'white_film': False, 'ropy': False, 'sour': False, 'viscous': False},
    }

    # 1 \u6b63\u4f8b
    r1 = calc(base)
    ck(r1['level'] == LEVEL_OK, '\u6b63\u4f8b\u5e94\u4e3a\u64cd\u4f5c\u89c4\u8303\uff0c\u5b9e\u4e3a %s' % r1['level'])
    ck(r1['items_rows'][0]['status'] == '\u5408\u683c', '\u725b\u8171\u5e94\u5224\u5408\u683c\uff0c\u5b9e\u4e3a %s' % r1['items_rows'][0]['status'])

    # 2 \u53cd\u4f8b: \u53d8\u8d28\u4fe1\u53f7\u4f18\u5148\u4e8e\u4e00\u5207
    r2 = calc(dict(base, spoilage={'white_film': True, 'ropy': False, 'sour': False, 'viscous': False}))
    ck(r2['level'] == LEVEL_DISCARD, '\u51fa\u73b0\u767d\u819c\u5e94\u5224\u5fc5\u987b\u5f03\u7528\uff0c\u5b9e\u4e3a %s' % r2['level'])
    ck('\u8868\u9762\u8d77\u767d\u819c' in r2['spoil_hit'], '\u5e94\u70b9\u540d\u767d\u819c\uff0c\u5b9e\u4e3a %s' % r2['spoil_hit'])
    r2b = calc(dict(base, spoilage={'white_film': False, 'ropy': False, 'sour': False, 'viscous': True}))
    ck(r2b['level'] == LEVEL_DISCARD, '\u51fa\u73b0\u53d1\u9ecf\u5e94\u5224\u5fc5\u987b\u5f03\u7528\uff0c\u5b9e\u4e3a %s' % r2b['level'])

    # 3 \u53cd\u4f8b: \u5927\u706b\u6eda\u716e
    r3 = calc(dict(base, rolling_boil=True))
    ck(r3['level'] == LEVEL_HARD, '\u5927\u706b\u6eda\u716e\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r3['level'])
    ck('\u53d8\u67f4' in r3['temp_row']['why'], '\u5fc5\u987b\u5e26\u51fa\u4e3a\u4ec0\u4e48\uff0c\u5b9e\u4e3a %s' % r3['temp_row']['why'])

    # 4 \u53cd\u4f8b: \u6e29\u5ea6\u8fc7\u4f4e
    r4 = calc(dict(base, pot_temp_c=72))
    ck(r4['temp_row']['status'] == '\u4e0d\u5408\u683c', '\u4f4e\u4e8e 80 \u5ea6\u5e94\u5224\u4e0d\u5408\u683c\uff0c\u5b9e\u4e3a %s' % r4['temp_row']['status'])
    ck(r4['level'] == LEVEL_HARD, '\u4fdd\u6e29\u4e0d\u8db3\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r4['level'])

    # 5 \u53cd\u4f8b: \u5364\u5236\u65f6\u95f4\u4e0d\u8db3
    r5 = calc(dict(base, items=[{'name': '\u725b\u8171', 'kind': 'beef_shank',
                                 'braise_minutes': 25, 'soak_minutes': 90}]))
    ck(r5['items_rows'][0]['status'] == '\u4e0d\u5408\u683c', '\u725b\u8171\u5364 25 \u5206\u949f\u5e94\u5224\u4e0d\u5408\u683c')
    ck('\u672a\u719f\u900f' in r5['items_rows'][0]['why'], '\u65f6\u95f4\u4e0d\u8db3\u5fc5\u987b\u5e26\u51fa\u539f\u56e0\uff0c\u5b9e\u4e3a %s' % r5['items_rows'][0]['why'])
    ck(r5['level'] == LEVEL_HARD, '\u65f6\u95f4\u4e0d\u8db3\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r5['level'])

    # 6 \u53cd\u4f8b: \u6d78\u6ce1\u4e0d\u8db3(\u8fd9\u662f\u6700\u5e38\u89c1\u7684\u5751)
    r6 = calc(dict(base, items=[{'name': '\u725b\u8171', 'kind': 'beef_shank',
                                 'braise_minutes': 70, 'soak_minutes': 0}]))
    ck(r6['items_rows'][0]['status'] == '\u4e0d\u5408\u683c', '\u5b8c\u5168\u4e0d\u6d78\u6ce1\u5e94\u5224\u4e0d\u5408\u683c')
    ck('\u91cc\u9762\u6de1' in r6['items_rows'][0]['why'], '\u6d78\u6ce1\u4e0d\u8db3\u5fc5\u987b\u8bf4\u660e\u53ea\u4f1a\u8868\u5c42\u54b8\uff0c\u5b9e\u4e3a %s' % r6['items_rows'][0]['why'])
    r6b = calc(dict(base, items=[{'name': '\u725b\u8171', 'kind': 'beef_shank',
                                  'braise_minutes': 70, 'soak_minutes': 20}]))
    ck(r6b['items_rows'][0]['status'] == '\u4e0d\u5408\u683c', '\u6d78\u6ce1 20 \u5206\u949f\u5c11\u4e8e 35 \u5206\u949f\u5e94\u5224\u4e0d\u5408\u683c')

    # 7 \u53cd\u4f8b: \u542b\u76d0\u91cf\u504f\u4f4e
    r7 = calc(dict(base, brine={'salinity_pct': 1.0, 'boiled_before_use': True,
                                'filtered_after_use': True, 'storage': 'fridge'}))
    ck(r7['salt_row']['status'] == '\u4e0d\u5408\u683c', '\u542b\u76d0 1.0 \u5e94\u5224\u4e0d\u5408\u683c\uff0c\u5b9e\u4e3a %s' % r7['salt_row']['status'])
    ck(r7['level'] == LEVEL_HARD, '\u542b\u76d0\u504f\u4f4e\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r7['level'])

    # 8 \u53cd\u4f8b: \u542b\u76d0\u91cf\u504f\u9ad8\u4f1a\u63a9\u76d6\u9178\u5473
    r8 = calc(dict(base, brine={'salinity_pct': 3.2, 'boiled_before_use': True,
                                'filtered_after_use': True, 'storage': 'fridge'}))
    ck(r8['salt_row']['status'] == '\u4e0d\u5408\u683c', '\u542b\u76d0 3.2 \u5e94\u5224\u4e0d\u5408\u683c')
    ck('\u63a9\u76d6' in r8['salt_row']['why'], '\u542b\u76d0\u504f\u9ad8\u5fc5\u987b\u8bf4\u660e\u4f1a\u63a9\u76d6\u9178\u5473\uff0c\u5b9e\u4e3a %s' % r8['salt_row']['why'])

    # 9 \u53cd\u4f8b: \u8001\u5364\u672a\u716e\u6cb8
    r9 = calc(dict(base, brine={'salinity_pct': 1.8, 'boiled_before_use': False,
                                'filtered_after_use': True, 'storage': 'fridge'}))
    ck(r9['level'] == LEVEL_HARD, '\u8001\u5364\u672a\u716e\u6cb8\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r9['level'])
    ck(r9['care_rows'][0]['status'] == '\u4e0d\u5408\u683c', '\u5e94\u70b9\u540d\u8001\u5364\u716e\u6cb8\u9879\uff0c\u5b9e\u4e3a %s' % r9['care_rows'][0]['status'])

    # 10 \u53cd\u4f8b: \u7d20\u83dc\u8fdb\u4e3b\u9505
    r10 = calc(dict(base, veg_in_main_pot=True))
    ck(r10['level'] == LEVEL_HARD, '\u7d20\u83dc\u8fdb\u4e3b\u9505\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r10['level'])
    ck('\u9178\u8d25' in r10['veg_row']['why'], '\u5fc5\u987b\u8bf4\u660e\u662f\u9178\u8d25\u6210\u56e0\uff0c\u5b9e\u4e3a %s' % r10['veg_row']['why'])

    # 11 \u53cd\u4f8b: \u5b58\u653e\u8d85\u65f6\u4e0e\u590d\u70ed\u4e0d\u8db3
    r11 = calc(dict(base, cool_hours=4))
    ck(r11['level'] == LEVEL_HARD, '\u5ba4\u6e29\u653e\u7f6e 4 \u5c0f\u65f6\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r11['level'])
    r11b = calc(dict(base, stored_hours=72))
    ck(r11b['level'] == LEVEL_HARD, '\u51b7\u85cf 72 \u5c0f\u65f6\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r11b['level'])
    r11c = calc(dict(base, reheat_temp=60))
    ck(r11c['level'] == LEVEL_HARD, '\u590d\u70ed 60 \u5ea6\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r11c['level'])

    # 12 \u79cd\u7c7b\u8868\u4e0e\u86cb\u7c7b\u6d78\u6ce1
    ck(len(ITEMS) == 9, '\u98df\u6750\u79cd\u7c7b\u5e94 9 \u7c7b\uff0c\u5b9e\u4e3a %d' % len(ITEMS))
    r12 = calc(dict(base, items=[{'name': '\u5364\u86cb', 'kind': 'egg',
                                  'braise_minutes': 10, 'soak_minutes': 300}]))
    ck(r12['items_rows'][0]['status'] == '\u5408\u683c', '\u5364\u86cb\u6ce1 300 \u5206\u949f\u5e94\u5224\u5408\u683c')
    r12b = calc(dict(base, items=[{'name': '\u5364\u86cb', 'kind': 'egg',
                                   'braise_minutes': 10, 'soak_minutes': 120}]))
    ck(r12b['items_rows'][0]['status'] == '\u4e0d\u5408\u683c', '\u5364\u86cb\u6ce1 120 \u5206\u949f\u5e94\u5224\u4e0d\u5408\u683c')

    # 13 \u5224\u5b9a\u5206\u652f\u987a\u5e8f: \u771f\u5b9e\u7f3a\u9677\u4e0d\u80fd\u88ab\u4fe1\u606f\u4e0d\u5168\u538b\u6210\u5f85\u786e\u8ba4
    r13 = calc(dict(base, pot_temp_c=72, cool_hours=None))
    ck(r13['level'] == LEVEL_HARD, '\u6e29\u5ea6\u4e0d\u5408\u683c\u4e14\u4fe1\u606f\u4e0d\u5168\u4ecd\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r13['level'])
    r13b = calc(dict(base, reheat_temp=None, stored_hours=None))
    ck(r13b['level'] == LEVEL_UNKNOWN, '\u65e0\u7f3a\u9677\u4f46\u7f3a\u5b58\u653e\u6570\u636e\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r13b['level'])

    # 14 BOM \u4e24\u6761\u8def\u5f84
    bom_text = '\ufeff' + json.dumps(dict(base, rolling_boil=True))
    r14 = calc(json.loads(bom_text.lstrip('\ufeff')))
    ck(r14['level'] == LEVEL_HARD, 'BOM \u5b57\u7b26\u4e32\u5e94\u80fd\u6b63\u786e\u89e3\u6790\uff0c\u5b9e\u4e3a %s' % r14['level'])
    ck(r14['temp_row']['value'] == 93.0, 'BOM \u8f93\u5165\u9505\u6e29\u5e94\u4e3a 93\uff0c\u5b9e\u4e3a %s' % r14['temp_row']['value'])
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe_braise.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps(dict(base, items=[{'name': '\u9e21\u722a', 'kind': 'poultry_part',
                                              'braise_minutes': 20, 'soak_minutes': 40}])))
    try:
        loaded = json.loads(open(tmp, 'r', encoding='utf-8-sig').read())
        r14b = calc(loaded)
        ck(r14b['items_rows'][0]['kind_name'] == '\u9e21\u7fc5\u3001\u9e21\u722a',
           'utf-8-sig \u8bfb\u53d6\u5e94\u62ff\u5230\u9e21\u7fc5\u9e21\u722a\uff0c\u5b9e\u4e3a %s' % r14b['items_rows'][0]['kind_name'])
        ck(r14b['level'] == LEVEL_OK, '\u9e21\u722a\u5364 20 \u6ce1 40 \u5e94\u5224\u64cd\u4f5c\u89c4\u8303\uff0c\u5b9e\u4e3a %s' % r14b['level'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 15 \u975e\u6cd5\u8f93\u5165\u5fc5\u987b\u62a5\u9519
    for payload, why in (
        ({'items': [{'kind': 'unknown_kind', 'braise_minutes': 10, 'soak_minutes': 10}]}, '\u672a\u77e5\u79cd\u7c7b'),
        ({'items': '\u4e0d\u662f\u5217\u8868'}, '\u98df\u6750\u975e\u5217\u8868'),
        ({'spoilage': {'\u62fc\u9519\u7684\u4fe1\u53f7': True}}, '\u672a\u77e5\u53d8\u8d28\u4fe1\u53f7'),
        ({'pot_temp_c': '\u5f88\u70ed'}, '\u6e29\u5ea6\u975e\u6570\u5b57'),
        ({'brine': '\u4e0d\u662f\u5bf9\u8c61'}, '\u5364\u6c34\u975e\u5bf9\u8c61'),
        ({'veg_in_main_pot': '\u4e0d\u662f\u5e03\u5c14'}, '\u7d20\u83dc\u5b57\u6bb5\u975e\u5e03\u5c14'),
    ):
        try:
            calc(payload)
            ck(False, '\u7528\u4f8b15 %s \u5e94\u629b\u9519\u5374\u901a\u8fc7' % why)
        except ValueError:
            ck(True, '')
        except Exception as e:
            ck(False, '\u7528\u4f8b15 %s \u5e94\u629b ValueError\uff0c\u5b9e\u4e3a %s' % (why, e))

    # 16 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r2)
    for key in ('\u603b\u4f53\u5224\u5b9a', '\u53d8\u8d28\u4fe1\u53f7', '\u98df\u6750\u65f6\u95f4\u4e0e\u6d78\u6ce1', '\u6e29\u5ea6\u7eaa\u5f8b', '\u5364\u6c34\u542b\u76d0\u91cf',
                '\u8001\u5364\u517b\u62a4\u4e0e\u7d20\u83dc\u5355\u9505', '\u5b58\u653e\u4e0e\u590d\u70ed', '\u516d\u6761\u660e\u786e\u7981\u6b62\u7684\u64cd\u4f5c', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355', '\u514d\u8d23'):
        ck(key in md, 'Markdown \u8f93\u51fa\u5e94\u542b\u7ae0\u8282 %s' % key)
    ck(len(BANNED) == 6, '\u7981\u6b62\u9879\u5e94 6 \u6761\uff0c\u5b9e\u4e3a %d' % len(BANNED))
    ck(len(r1['spoil_rows']) == 4, '\u53d8\u8d28\u4fe1\u53f7\u5e94 4 \u6761\uff0c\u5b9e\u4e3a %d' % len(r1['spoil_rows']))

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u6b63\u4f8b/\u53d8\u8d28\u56db\u4fe1\u53f7/\u5927\u706b\u6eda\u716e/\u6e29\u5ea6\u8fc7\u4f4e/\u5364\u5236\u4e0d\u8db3/'
               '\u6d78\u6ce1\u4e0d\u8db3/\u542b\u76d0\u504f\u4f4e/\u542b\u76d0\u504f\u9ad8\u63a9\u76d6\u9178\u5473/\u8001\u5364\u672a\u716e\u6cb8/\u7d20\u83dc\u5165\u4e3b\u9505/\u5b58\u653e\u8d85\u65f6\u4e0e\u590d\u70ed\u4e0d\u8db3/'
               '\u79cd\u7c7b\u8868\u4e0e\u86cb\u7c7b\u6d78\u6ce1/\u5224\u5b9a\u5206\u652f\u987a\u5e8f/BOM \u4e24\u6761\u8def\u5f84/\u975e\u6cd5\u8f93\u5165/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u5364\u5473\u5236\u4f5c\u4e0e\u5364\u6c34\u517b\u62a4\u6838\u67e5')
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

