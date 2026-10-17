# -*- coding: utf-8 -*-
"""\u9762\u5305\u63c9\u9762\u72b6\u6001\u5224\u65ad\u4e0e\u624b\u6cd5\u6838\u67e5\uff1a\u9762\u7b4b\u9636\u6bb5\u3001\u9762\u56e2\u6e29\u5ea6\u3001\u542b\u6db2\u91cf\u4e0e\u540e\u6cb9\u6cd5\u987a\u5e8f\u3002

\u7528\u6cd5:
  python bread_knead_check.py --file dough.json [--out result.md] [--format json]
  python bread_knead_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u9762\u7c89: (\u952e, \u4e2d\u6587\u540d, \u542b\u6db2\u91cf\u4e0b\u9650\u767e\u5206\u6bd4, \u542b\u6db2\u91cf\u4e0a\u9650\u767e\u5206\u6bd4, \u9002\u7528, \u76ee\u6807\u9636\u6bb5)
FLOUR = [
    ('high_gluten', '\u9ad8\u7b4b\u9762\u7c89', 60.0, 65.0, '\u5410\u53f8\u3001\u8d1d\u679c\u3001\u53ef\u9882\u7b49\u9700\u8981\u5f3a\u97e7\u9762\u7b4b\u7684\u9762\u5305', 'full'),
    ('all_purpose', '\u4e2d\u7b4b\u9762\u7c89', 55.0, 60.0, '\u9910\u5305\u3001\u8f6f\u6b27\u3001\u4e2d\u5f0f\u9762\u70b9', 'near'),
    ('whole_wheat', '\u5168\u9ea6\u9762\u7c89', 65.0, 72.0, '\u5168\u9ea6\u9762\u5305\uff0c\u9eb8\u76ae\u4f1a\u5207\u65ad\u9762\u7b4b', 'expansion'),
    ('low_gluten', '\u4f4e\u7b4b\u9762\u7c89', 50.0, 55.0, '\u86cb\u7cd5\u4e3a\u4e3b\uff0c\u505a\u9762\u5305\u9762\u7b4b\u504f\u5f31', 'expansion'),
]

# \u9762\u7b4b\u9636\u6bb5: (\u952e, \u4e2d\u6587\u540d, \u7279\u5f81, \u8be5\u505a\u7684\u4e8b)
STAGES = [
    ('mixed', '\u6df7\u5408\u671f', '\u6750\u6599\u6df7\u5408\u6210\u7c97\u7cd9\u9762\u56e2\uff0c\u8868\u9762\u5df2\u65e0\u7247\u72b6\u5e72\u7c89', '\u5f00\u59cb\u6b63\u5f0f\u63c9\u9762\uff0c\u6b64\u65f6\u4e0d\u8981\u52a0\u9ec4\u6cb9'),
    ('forming', '\u9762\u7b4b\u521d\u6b65\u5f62\u6210', '\u9762\u56e2\u5f00\u59cb\u62b1\u56e2\uff0c\u62c9\u626f\u6613\u65ad\uff0c\u8868\u9762\u4ecd\u7c97\u7cd9', '\u7ee7\u7eed\u63c9\uff0c\u4e0d\u8981\u56e0\u4e3a\u770b\u7740\u4e0d\u5149\u6ed1\u5c31\u52a0\u6c34'),
    ('expansion', '\u6269\u5c55\u9636\u6bb5', '\u80fd\u62c9\u51fa\u8f83\u539a\u7684\u819c\uff0c\u4e0d\u900f\u5149\uff0c\u7834\u53e3\u6709\u952f\u9f7f', '\u9ec4\u6cb9\u7684\u52a0\u5165\u5206\u754c\u7ebf\uff0c\u8f6f\u5316\u9ec4\u6cb9\u4ece\u6b64\u9636\u6bb5\u5f00\u59cb\u5206\u6b21\u52a0'),
    ('near', '\u63a5\u8fd1\u5b8c\u5168\u6269\u5c55', '\u80fd\u62c9\u51fa\u534a\u900f\u660e\u8584\u819c\uff0c\u7834\u53e3\u6709\u7ec6\u952f\u9f7f', '\u518d\u63c9 1 \u81f3 2 \u5206\u949f\u7acb\u5373\u590d\u68c0'),
    ('full', '\u5b8c\u5168\u6269\u5c55', '\u80fd\u62c9\u51fa\u900f\u5149\u8584\u819c\uff0c\u7834\u53e3\u8fb9\u7f18\u5149\u6ed1', '\u7acb\u523b\u505c\u624b\uff0c\u6eda\u5706\u653e\u677e 15 \u81f3 20 \u5206\u949f'),
]

STAGE_ORDER = ['mixed', 'forming', 'expansion', 'near', 'full']
STAGE_NAME = dict((k, v) for k, v, _c, _d in STAGES)
STAGE_FEATURE = dict((k, c) for k, _v, c, _d in STAGES)
STAGE_ACTION = dict((k, d) for k, _v, _c, d in STAGES)

# \u9762\u56e2\u6e29\u5ea6\uff08\u6444\u6c0f\u5ea6\uff09
DOUGH_TEMP = {
    'target_min': 24.0,
    'target_max': 26.0,
    'slow_min': 22.0,
    'warn_max': 28.0,
    'broken_max': 32.0,
}

# \u6469\u64e6\u5347\u6e29\u53c2\u8003: (\u952e, \u4e2d\u6587\u540d, \u4e0b\u9650, \u4e0a\u9650)
FRICTION = [
    ('hand', '\u624b\u63c9', 2.0, 4.0),
    ('mixer_low', '\u53a8\u5e08\u673a\u4f4e\u901f', 5.0, 8.0),
    ('mixer_high', '\u53a8\u5e08\u673a\u4e2d\u9ad8\u901f\u957f\u65f6\u95f4', 8.0, 12.0),
]

FRICTION_NAME = dict((k, v) for k, v, _a, _b in FRICTION)

# \u7a97\u73bb\u7483\u819c\u8f93\u5165\u5b57\u6bb5
WINDOWPANE_FIELDS = ('can_stretch', 'translucent', 'edge_smooth', 'breaks_at_once')

# \u516b\u9879\u64cd\u4f5c\u68c0\u67e5: (\u952e, \u4e2d\u6587\u540d, \u5408\u683c\u53e3\u5f84, \u4e0d\u5408\u683c\u7684\u539f\u56e0)
CHECKS = [
    ('weighed', '\u6750\u6599\u5df2\u79f0\u91cd',
     '\u9762\u7c89\u4e0e\u6db2\u4f53\u90fd\u6309\u91cd\u91cf\u79f0\u8fc7\uff0c\u4e0d\u7528\u91cf\u676f\u4f30',
     '\u91cf\u676f\u4f30\u7b97\u7684\u8bef\u5dee\u53ef\u8fbe\u4e24\u6210\uff0c\u9636\u6bb5\u5224\u5b9a\u7684\u8d77\u70b9\u5c31\u4e0d\u51c6'),
    ('hydration_ok', '\u542b\u6db2\u91cf\u5728\u533a\u95f4\u5185',
     '\u542b\u6db2\u91cf\u843d\u5728\u8be5\u9762\u7c89\u7684\u63a8\u8350\u533a\u95f4',
     '\u504f\u79bb\u533a\u95f4\u540e\uff0c\u7a97\u73bb\u7483\u819c\u7684\u5224\u5b9a\u6807\u51c6\u672c\u8eab\u5931\u6548'),
    ('autolyse_done', '\u5df2\u505a\u81ea\u89e3\u9759\u7f6e',
     '\u7c89\u6c34\u6df7\u5408\u540e\u9759\u7f6e 20 \u81f3 30 \u5206\u949f',
     '\u7701\u4e0b\u7684\u63c9\u9762\u65f6\u95f4\u8fdc\u591a\u4e8e\u9759\u7f6e\u65f6\u95f4'),
    ('salt_yeast_apart', '\u76d0\u4e0e\u9175\u6bcd\u672a\u76f4\u63a5\u63a5\u89e6',
     '\u76d0\u4e0e\u9175\u6bcd\u5206\u4e24\u4fa7\u653e\u7f6e\uff0c\u5404\u81ea\u62cc\u5f00\u518d\u63c9\u5300',
     '\u76f4\u63a5\u63a5\u89e6\u4f1a\u6291\u5236\u9175\u6bcd\u6d3b\u6027\uff0c\u5c0f\u4efd\u91cf\u5c24\u5176\u660e\u663e'),
    ('butter_after_expansion', '\u9ec4\u6cb9\u5728\u6269\u5c55\u9636\u6bb5\u540e\u52a0\u5165',
     '\u8f6f\u5316\u9ec4\u6cb9\u5728\u80fd\u62c9\u51fa\u8f83\u539a\u7684\u819c\u4e4b\u540e\u5206\u6b21\u52a0\u5165',
     '\u63d0\u524d\u52a0\u6cb9\u4f1a\u628a\u9762\u7b4b\u6cb9\u65ad\uff0c\u540e\u9762\u600e\u4e48\u63c9\u90fd\u62c9\u4e0d\u51fa\u819c'),
    ('windowpane_tested', '\u5df2\u505a\u7a97\u73bb\u7483\u819c\u6d4b\u8bd5',
     '\u6bcf\u63c9 3 \u81f3 5 \u5206\u949f\u590d\u68c0\u4e00\u6b21',
     '\u65f6\u95f4\u53ea\u662f\u53c2\u8003\uff0c\u9636\u6bb5\u624d\u662f\u5224\u5b9a\u4f9d\u636e'),
    ('temp_measured', '\u9762\u56e2\u6e29\u5ea6\u5df2\u5b9e\u6d4b',
     '\u7528\u63a2\u9488\u6e29\u5ea6\u8ba1\u6d4b\u9762\u56e2\u4e2d\u5fc3\u6e29\u5ea6',
     '\u624b\u611f\u4f30\u5dee\u4e24\u5ea6\u5c31\u662f\u4e24\u79cd\u7ed3\u679c'),
    ('no_extra_flour', '\u672a\u6492\u5e72\u7c89\u8865\u6551\u53d1\u9ecf',
     '\u53d1\u9ecf\u5148\u627e\u539f\u56e0\uff0c\u4e0d\u6492\u624b\u7c89',
     '\u6492\u7c89\u6539\u53d8\u914d\u65b9\u6bd4\u4f8b\uff0c\u9762\u56e2\u8d8a\u63c9\u8d8a\u5e72'),
]

CHECK_WHY = dict((k, why) for k, _n, _o, why in CHECKS)

# \u63c9\u8fc7\u5934\u4fe1\u53f7: (\u952e, \u4e2d\u6587\u540d, \u8bf4\u660e)
OVERDONE = [
    ('weeping', '\u8868\u9762\u6e17\u6c34\u53d1\u9ecf', '\u624b\u4e0a\u4f1a\u5e26\u4e0b\u4e00\u5c42\u7a00\u7cca'),
    ('lost_elasticity', '\u5931\u53bb\u5f39\u6027', '\u6309\u4e0b\u53bb\u4e0d\u7559\u5f39'),
    ('film_collapses', '\u819c\u4e00\u78b0\u5c31\u5316', '\u62c9\u51fa\u7684\u8584\u819c\u7acb\u523b\u584c\u6389'),
    ('cannot_round', '\u6eda\u4e0d\u5706', '\u8d8a\u63c9\u8d8a\u6e7f\u8d8a\u644a\uff0c\u65e0\u6cd5\u6536\u5706'),
]

# \u516d\u6761\u660e\u786e\u7981\u6b62\u7684\u64cd\u4f5c
BANNED = [
    '\u7528\u65b9\u5b50\u5199\u4e86\u51e0\u5206\u949f\u5f53\u505c\u624b\u4f9d\u636e\uff0c\u4e0d\u770b\u9636\u6bb5',
    '\u9762\u56e2\u53d1\u9ecf\u65f6\u53cd\u590d\u6492\u5e72\u7c89\u8865\u6551',
    '\u4e00\u5f00\u59cb\u5c31\u628a\u8f6f\u5316\u9ec4\u6cb9\u548c\u6240\u6709\u6750\u6599\u4e00\u8d77\u6295\u8fdb\u53bb',
    '\u5bf9\u5168\u9ea6\u3001\u9ed1\u9ea6\u9762\u56e2\u8ffd\u6c42\u900f\u5149\u624b\u5957\u819c',
    '\u51ed\u624b\u611f\u4f30\u8ba1\u9762\u56e2\u6e29\u5ea6\u800c\u4e0d\u5b9e\u6d4b',
    '\u628a\u8d8a\u63c9\u8d8a\u6e7f\u9ecf\u5f53\u6210\u8fd8\u6ca1\u63c9\u5230\u7ee7\u7eed\u52a0\u65f6\u95f4',
]

LEVEL_HARD = '\u5fc5\u987b\u5904\u7406'
LEVEL_CONTINUE = '\u8fd8\u9700\u7ee7\u7eed'
LEVEL_WEAK = '\u5b58\u5728\u8584\u5f31\u73af\u8282'
LEVEL_UNKNOWN = '\u5f85\u786e\u8ba4'
LEVEL_OK = '\u53ef\u4ee5\u7ee7\u7eed'


def get_flour(key):
    for row in FLOUR:
        if row[0] == str(key or '').strip().lower():
            return row
    raise ValueError('\u672a\u77e5\u7684\u9762\u7c89\u79cd\u7c7b: %s\uff0c\u53ef\u9009 %s \u4e4b\u4e00' % (key, '/'.join(r[0] for r in FLOUR)))


def judge_stage(w):
    """\u6309\u7a97\u73bb\u7483\u819c\u56db\u6863\u73b0\u8c61\u5224\u5b9a\u9762\u7b4b\u9636\u6bb5\u3002\u8fd4\u56de\u9636\u6bb5\u952e\u3002"""
    if w is None:
        w = {}
    if not isinstance(w, dict):
        raise ValueError('windowpane \u5fc5\u987b\u662f\u5bf9\u8c61')
    for k in w:
        if k not in WINDOWPANE_FIELDS:
            raise ValueError('\u672a\u77e5\u7684\u7a97\u73bb\u7483\u819c\u5b57\u6bb5: %s\uff0c\u53ef\u9009 %s \u4e4b\u4e00' % (k, '/'.join(WINDOWPANE_FIELDS)))
    # \u4e25\u683c\u6309\u73b0\u8c61\u5224\u5b9a\uff0c\u4e0d\u8981\u7ed9\u4efb\u4f55\u300c\u89c6\u4e3a\u5408\u683c\u300d\u7684\u5bbd\u5bb9\u5206\u652f\u3002
    if not w.get('can_stretch'):
        return 'mixed'
    if w.get('breaks_at_once'):
        return 'forming'
    if not w.get('translucent'):
        return 'expansion'
    if not w.get('edge_smooth'):
        return 'near'
    return 'full'


def check_items(flags):
    if flags is None:
        flags = {}
    if not isinstance(flags, dict):
        raise ValueError('checks \u5fc5\u987b\u662f\u5bf9\u8c61')
    keys = [c[0] for c in CHECKS]
    for k in flags:
        if str(k).strip().lower() not in keys:
            raise ValueError('\u672a\u77e5\u7684\u68c0\u67e5\u9879: %s\uff0c\u53ef\u9009\u9879\u89c1 CHECKS \u8868' % k)
    rows = []
    bad = []
    unk = []
    for key, name, ok_desc, why in CHECKS:
        v = flags.get(key)
        if v is None:
            rows.append({'name': name, 'status': '\u672a\u68c0\u67e5', 'desc': ok_desc, 'why': why})
            unk.append(name)
        elif v:
            rows.append({'name': name, 'status': '\u5408\u683c', 'desc': ok_desc, 'why': why})
        else:
            rows.append({'name': name, 'status': '\u4e0d\u5408\u683c', 'desc': ok_desc, 'why': why})
            bad.append(name)
    return rows, bad, unk


def water_temp(target, room, flour_t, friction):
    """\u52a0\u6c34\u6c34\u6e29\u6362\u7b97: \u76ee\u6807\u9762\u56e2\u6e29\u5ea6\u4e58\u4ee5 3 \u51cf\u53bb\u5ba4\u6e29\u3001\u7c89\u6e29\u4e0e\u6469\u64e6\u5347\u6e29\u3002"""
    return target * 3.0 - room - flour_t - friction


def water_advise(temp):
    if temp < 0:
        return '\u7b97\u51fa\u7684\u6c34\u6e29\u4f4e\u4e8e 0 \u6444\u6c0f\u5ea6\uff0c\u5149\u8c03\u6c34\u6e29\u4e0d\u591f\uff0c\u9700\u8981\u540c\u65f6\u51b7\u85cf\u9762\u7c89\u548c\u6405\u62cc\u7f38\u5e76\u964d\u4f4e\u5ba4\u6e29'
    if temp < 4:
        return '\u7b97\u51fa\u7684\u6c34\u6e29\u4f4e\u4e8e 4 \u6444\u6c0f\u5ea6\uff0c\u76f4\u63a5\u4f7f\u7528\u51b0\u6c34'
    return '\u6309 %.1f \u6444\u6c0f\u5ea6\u8c03\u6c34\u5373\u53ef' % temp


def check_overdone(signs):
    if signs is None:
        signs = {}
    if not isinstance(signs, dict):
        raise ValueError('overdone_signs \u5fc5\u987b\u662f\u5bf9\u8c61')
    keys = [o[0] for o in OVERDONE]
    for k in signs:
        if str(k).strip().lower() not in keys:
            raise ValueError('\u672a\u77e5\u7684\u63c9\u8fc7\u5934\u4fe1\u53f7: %s\uff0c\u53ef\u9009\u9879\u89c1 OVERDONE \u8868' % k)
    hit = []
    rows = []
    for key, name, desc in OVERDONE:
        v = signs.get(key)
        if v is True:
            hit.append(name)
            rows.append({'name': name, 'status': '\u51fa\u73b0', 'desc': desc})
        elif v is False:
            rows.append({'name': name, 'status': '\u672a\u51fa\u73b0', 'desc': desc})
        else:
            rows.append({'name': name, 'status': '\u672a\u68c0\u67e5', 'desc': desc})
    return rows, hit


def calc(data):
    if not isinstance(data, dict):
        raise ValueError('\u8f93\u5165\u5fc5\u987b\u662f JSON \u5bf9\u8c61')
    row = get_flour(data.get('flour'))
    fkey, fname, hmin, hmax, fusage, ftarget = row

    stage = judge_stage(data.get('windowpane'))

    hyd = data.get('hydration_pct')
    hyd_row = None
    hyd_bad = False
    if hyd is not None:
        try:
            hyd = float(hyd)
        except (TypeError, ValueError):
            raise ValueError('hydration_pct \u5fc5\u987b\u662f\u6570\u5b57')
        ok = hmin <= hyd <= hmax
        hyd_row = {'flour': fname, 'value': hyd, 'min': hmin, 'max': hmax,
                   'status': '\u5728\u533a\u95f4\u5185' if ok else '\u8d85\u51fa\u533a\u95f4', 'usage': fusage}
        hyd_bad = not ok

    rows, bad, unk = check_items(data.get('checks'))
    od_rows, od_hit = check_overdone(data.get('overdone_signs'))

    dtemp = data.get('dough_temp')
    temp_row = None
    temp_hard = False
    temp_missing = dtemp is None
    if dtemp is not None:
        try:
            dtemp = float(dtemp)
        except (TypeError, ValueError):
            raise ValueError('dough_temp \u5fc5\u987b\u662f\u6570\u5b57')
        if dtemp > DOUGH_TEMP['broken_max']:
            status = '\u5df2\u53d7\u635f'
            why = '\u9ad8\u4e8e 32 \u6444\u6c0f\u5ea6\uff0c\u9762\u7b4b\u5df2\u88ab\u7834\u574f\uff0c\u4e0d\u8981\u518d\u8ffd\u6c42\u5410\u53f8\uff0c\u6539\u505a\u62ab\u8428\u3001\u997c\u7c7b\u6216\u4f5b\u5361\u590f'
            temp_hard = True
        elif dtemp > DOUGH_TEMP['warn_max']:
            status = '\u8d85\u6807'
            why = '\u8d85\u8fc7 28 \u6444\u6c0f\u5ea6\u8b66\u6212\u4e0a\u9650\uff0c\u53d1\u9175\u4f1a\u5931\u63a7\u3001\u9762\u7b4b\u6613\u65ad\uff0c\u5148\u644a\u5e73\u51b7\u85cf\u964d\u6e29 10 \u81f3 15 \u5206\u949f'
            temp_hard = True
        elif dtemp > DOUGH_TEMP['target_max']:
            status = '\u7565\u9ad8'
            why = '\u7565\u9ad8\u4e8e 26 \u6444\u6c0f\u5ea6\u76ee\u6807\u4e0a\u9650\uff0c\u6ce8\u610f\u540e\u7eed\u53d1\u9175\u901f\u5ea6\u4f1a\u504f\u5feb'
        elif dtemp < DOUGH_TEMP['slow_min']:
            status = '\u504f\u4f4e'
            why = '\u4f4e\u4e8e 22 \u6444\u6c0f\u5ea6\uff0c\u6269\u5c55\u4e0e\u53d1\u9175\u660e\u663e\u53d8\u6162\uff0c\u9700\u7528\u6e29\u6c34\u76c6\u6216\u53d1\u9175\u7bb1\u56de\u6e29'
        else:
            status = '\u8fbe\u6807'
            why = '\u843d\u5728 24 \u81f3 26 \u6444\u6c0f\u5ea6\u76ee\u6807\u533a\u95f4\u5185'
        temp_row = {'value': dtemp, 'status': status, 'why': why}

    target_t = data.get('target_dough_temp')
    room = data.get('room_temp')
    flour_t = data.get('flour_temp')
    friction = data.get('friction')
    water = None
    if None not in (target_t, room, flour_t, friction):
        try:
            water = water_temp(float(target_t), float(room), float(flour_t), float(friction))
        except (TypeError, ValueError):
            raise ValueError('\u6c34\u6e29\u6362\u7b97\u7684\u56db\u4e2a\u53c2\u6570\u90fd\u5fc5\u987b\u662f\u6570\u5b57')

    sidx = STAGE_ORDER.index(stage)
    tidx = STAGE_ORDER.index(ftarget)
    gap = tidx - sidx
    knead_done = bool(data.get('knead_done'))
    short_stop = knead_done and gap > 0
    over_stage = None
    if fkey in ('whole_wheat', 'low_gluten') and gap < 0:
        over_stage = '\u8be5\u9762\u7c89\u4e0d\u9700\u8981\u505a\u5230\u6b64\u9636\u6bb5\uff0c\u9eb8\u76ae\u6216\u4f4e\u86cb\u767d\u542b\u91cf\u4f1a\u5207\u65ad\u9762\u7b4b\uff0c\u786c\u62c9\u53ea\u4f1a\u628a\u819c\u62c9\u7834'

    # \u5224\u5b9a\u987a\u5e8f: \u5148\u770b\u771f\u5b9e\u7f3a\u9677(\u6e29\u5ea6\u53d7\u635f/\u8d85\u6807\u3001\u63c9\u8fc7\u5934\u3001\u672a\u5230\u76ee\u6807\u9636\u6bb5\u5c31\u505c\u624b),
    # \u518d\u770b\u68c0\u67e5\u9879\u662f\u5426\u4e0d\u5408\u683c, \u6700\u540e\u624d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574\u3002
    if temp_hard:
        level = LEVEL_HARD
    elif od_hit:
        level = LEVEL_HARD
    elif short_stop:
        level = LEVEL_CONTINUE
    elif bad or hyd_bad:
        level = LEVEL_WEAK
    elif temp_missing or unk or data.get('windowpane') is None:
        level = LEVEL_UNKNOWN
    else:
        level = LEVEL_OK

    return {
        'flour': {'key': fkey, 'name': fname, 'usage': fusage,
                  'target_stage': STAGE_NAME[ftarget], 'hyd_min': hmin, 'hyd_max': hmax},
        'stage': {'key': stage, 'name': STAGE_NAME[stage],
                  'feature': STAGE_FEATURE[stage], 'action': STAGE_ACTION[stage]},
        'gap': gap,
        'target_stage_name': STAGE_NAME[ftarget],
        'short_stop': short_stop,
        'over_stage_note': over_stage,
        'hyd_row': hyd_row,
        'temp_row': temp_row,
        'temp_missing': temp_missing,
        'check_rows': rows,
        'bad': bad,
        'unk': unk,
        'overdone_rows': od_rows,
        'overdone_hit': od_hit,
        'water_temp': water,
        'water_advise': water_advise(water) if water is not None else None,
        'level': level,
        'temp_limits': DOUGH_TEMP,
    }


def render_md(r):
    L = []
    L.append('# \u9762\u5305\u63c9\u9762\u72b6\u6001\u5224\u5b9a\u7ed3\u679c')
    L.append('')
    L.append('**\u603b\u4f53\u5224\u5b9a\uff1a%s**' % r['level'])
    L.append('')
    L.append('## \u4e00\u3001\u9762\u7c89\u4e0e\u76ee\u6807\u9636\u6bb5')
    L.append('')
    L.append('| \u9879\u76ee | \u5185\u5bb9 |')
    L.append('|---|---|')
    L.append('| \u9762\u7c89 | %s |' % r['flour']['name'])
    L.append('| \u9002\u7528 | %s |' % r['flour']['usage'])
    L.append('| \u63a8\u8350\u542b\u6db2\u91cf\uff08\u767e\u5206\u6bd4\uff09 | %.0f \u81f3 %.0f |' % (r['flour']['hyd_min'], r['flour']['hyd_max']))
    L.append('| \u76ee\u6807\u9636\u6bb5 | %s |' % r['target_stage_name'])
    L.append('')
    L.append('## \u4e8c\u3001\u5f53\u524d\u9762\u7b4b\u9636\u6bb5')
    L.append('')
    L.append('| \u9879\u76ee | \u5185\u5bb9 |')
    L.append('|---|---|')
    L.append('| \u5224\u5b9a\u9636\u6bb5 | %s |' % r['stage']['name'])
    L.append('| \u7279\u5f81 | %s |' % r['stage']['feature'])
    L.append('| \u4e0b\u4e00\u6b65 | %s |' % r['stage']['action'])
    L.append('| \u8ddd\u79bb\u76ee\u6807\u9636\u6bb5 | %s |' % (('\u8fd8\u5dee %d \u6863' % r['gap']) if r['gap'] > 0 else (
        '\u5df2\u8fbe\u5230' if r['gap'] == 0 else '\u5df2\u8d85\u51fa\u76ee\u6807\u9636\u6bb5')))
    if r['short_stop']:
        L.append('')
        L.append('> **\u672a\u8fbe\u5230\u76ee\u6807\u9636\u6bb5\u5c31\u505c\u624b**\uff1a\u5e94\u5728\u5230\u8fbe\u300c%s\u300d\u540e\u518d\u505c\uff0c\u5426\u5219\u6210\u54c1\u4f53\u79ef\u5c0f\u3001\u7ec4\u7ec7\u7c97\u7cd9\u3002' % r['target_stage_name'])
    if r['over_stage_note']:
        L.append('')
        L.append('> %s' % r['over_stage_note'])
    L.append('')
    L.append('## \u4e09\u3001\u9762\u56e2\u6e29\u5ea6\u6838\u67e5')
    L.append('')
    if r['temp_row'] is None:
        L.append('\u672a\u63d0\u4f9b\u9762\u56e2\u6e29\u5ea6\u3002**\u7f3a\u5c11\u5b9e\u6d4b\u6e29\u5ea6\u65e0\u6cd5\u7ed9\u51fa\u6700\u7ec8\u5224\u5b9a**\uff0c\u8bf7\u7528\u63a2\u9488\u6e29\u5ea6\u8ba1\u6d4b\u4e2d\u5fc3\u6e29\u5ea6\u3002')
    else:
        t = r['temp_row']
        L.append('| \u5b9e\u6d4b\u503c\uff08\u6444\u6c0f\u5ea6\uff09 | \u72b6\u6001 | \u8bf4\u660e |')
        L.append('|---|---|---|')
        L.append('| %.1f | %s | %s |' % (t['value'], t['status'], t['why']))
        L.append('')
        L.append('\u76ee\u6807\u533a\u95f4 %.0f \u81f3 %.0f\uff0c\u8b66\u6212\u4e0a\u9650 %.0f\u3002' % (
            r['temp_limits']['target_min'], r['temp_limits']['target_max'], r['temp_limits']['warn_max']))
    L.append('')
    L.append('## \u56db\u3001\u52a0\u6c34\u6c34\u6e29\u6362\u7b97')
    L.append('')
    if r['water_temp'] is None:
        L.append('\u672a\u63d0\u4f9b target_dough_temp\u3001room_temp\u3001flour_temp\u3001friction \u56db\u9879\uff0c\u65e0\u6cd5\u6362\u7b97\u3002')
    else:
        L.append('\u5efa\u8bae\u52a0\u6c34\u6e29\u5ea6\uff1a**%.1f \u6444\u6c0f\u5ea6**\u3002%s' % (r['water_temp'], r['water_advise']))
    L.append('')
    L.append('## \u4e94\u3001\u542b\u6db2\u91cf\u6838\u67e5')
    L.append('')
    if r['hyd_row'] is None:
        L.append('\u672a\u63d0\u4f9b hydration_pct\uff0c\u65e0\u6cd5\u6838\u67e5\u542b\u6db2\u91cf\u3002')
    else:
        h = r['hyd_row']
        L.append('| \u9762\u7c89 | \u5b9e\u6d4b\uff08\u767e\u5206\u6bd4\uff09 | \u63a8\u8350\u533a\u95f4 | \u72b6\u6001 |')
        L.append('|---|---|---|---|')
        L.append('| %s | %.1f | %.0f \u81f3 %.0f | %s |' % (h['flour'], h['value'], h['min'], h['max'], h['status']))
    L.append('')
    L.append('## \u516d\u3001\u63c9\u8fc7\u5934\u4fe1\u53f7')
    L.append('')
    L.append('| \u4fe1\u53f7 | \u72b6\u6001 | \u8bf4\u660e |')
    L.append('|---|---|---|')
    for row in r['overdone_rows']:
        L.append('| %s | %s | %s |' % (row['name'], row['status'], row['desc']))
    if r['overdone_hit']:
        L.append('')
        L.append('> \u51fa\u73b0\u300c%s\u300d\uff0c\u8bf7\u7acb\u5373\u505c\u624b\u5e76\u6539\u505a\u62ab\u8428\u3001\u4f5b\u5361\u590f\u3001\u70d9\u997c\u6216\u997c\u5e72\u3002' % '\u3001'.join(r['overdone_hit']))
    L.append('')
    L.append('## \u4e03\u3001\u516b\u9879\u64cd\u4f5c\u68c0\u67e5')
    L.append('')
    L.append('| \u68c0\u67e5\u9879 | \u72b6\u6001 | \u5408\u683c\u53e3\u5f84 | \u4e0d\u5408\u683c\u7684\u539f\u56e0 |')
    L.append('|---|---|---|---|')
    for row in r['check_rows']:
        L.append('| %s | %s | %s | %s |' % (row['name'], row['status'], row['desc'], row['why']))
    if r['bad']:
        L.append('')
        L.append('\u4e0d\u5408\u683c\u9879\u53ca\u539f\u56e0\uff1a')
        for row in r['check_rows']:
            if row['status'] == '\u4e0d\u5408\u683c':
                L.append('- **%s**\uff1a%s' % (row['name'], row['why']))
    if r['unk']:
        L.append('')
        L.append('\u672a\u68c0\u67e5\u9879\uff1a%s' % '\u3001'.join(r['unk']))
    L.append('')
    L.append('## \u516b\u3001\u660e\u786e\u7981\u6b62\u7684\u64cd\u4f5c')
    L.append('')
    for i, b in enumerate(BANNED, 1):
        L.append('%d. %s' % (i, b))
    L.append('')
    L.append('## \u4e5d\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355')
    L.append('')
    L.append('- [ ] \u9762\u7c89\u4e0e\u6db2\u4f53\u90fd\u6309\u91cd\u91cf\u79f0\u8fc7')
    L.append('- [ ] \u542b\u6db2\u91cf\u5728\u8be5\u9762\u7c89\u7684\u63a8\u8350\u533a\u95f4\u5185')
    L.append('- [ ] \u7c89\u6c34\u6df7\u5408\u540e\u505a\u8fc7 20 \u81f3 30 \u5206\u949f\u81ea\u89e3')
    L.append('- [ ] \u76d0\u4e0e\u9175\u6bcd\u6ca1\u6709\u76f4\u63a5\u5806\u5728\u4e00\u8d77')
    L.append('- [ ] \u9ec4\u6cb9\u5728\u80fd\u62c9\u51fa\u8f83\u539a\u7684\u819c\u4e4b\u540e\u52a0\u5165')
    L.append('- [ ] \u505c\u624b\u524d\u521a\u505a\u8fc7\u7a97\u73bb\u7483\u819c\u6d4b\u8bd5')
    L.append('- [ ] \u63a2\u9488\u6e29\u5ea6\u8ba1\u5b9e\u6d4b\u4e2d\u5fc3\u6e29\u5ea6\u5728 24 \u81f3 26 \u6444\u6c0f\u5ea6')
    L.append('- [ ] \u9762\u56e2\u8868\u9762\u4e0d\u9ecf\u624b\uff0c\u6233\u6d1e\u80fd\u56de\u5f39')
    L.append('')
    L.append('## \u5341\u3001\u514d\u8d23')
    L.append('')
    L.append('\u672c\u7ed3\u679c\u4e3a\u5bb6\u5ead\u70d8\u7119\u65b9\u6cd5\u8bba\u6574\u7406\uff0c\u4e0d\u6784\u6210\u6210\u54c1\u6548\u679c\u627f\u8bfa\uff0c\u4e5f\u4e0d\u4f5c\u4efb\u4f55\u98df\u54c1\u5b89\u5168\u6027\u5224\u65ad\u3002')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    allok = dict((c[0], True) for c in CHECKS)
    base = {
        'flour': 'high_gluten',
        'hydration_pct': 62,
        'knead_done': True,
        'windowpane': {'can_stretch': True, 'translucent': True, 'edge_smooth': True},
        'dough_temp': 25,
        'room_temp': 26,
        'flour_temp': 26,
        'friction': 3,
        'target_dough_temp': 25,
        'checks': dict(allok),
        'overdone_signs': {'weeping': False, 'lost_elasticity': False,
                           'film_collapses': False, 'cannot_round': False},
    }

    # 1 \u6b63\u4f8b
    r1 = calc(base)
    ck(r1['level'] == LEVEL_OK, '\u6b63\u4f8b\u5e94\u4e3a\u53ef\u4ee5\u7ee7\u7eed\uff0c\u5b9e\u4e3a %s' % r1['level'])
    ck(r1['stage']['key'] == 'full', '\u6b63\u4f8b\u5e94\u5224\u5b8c\u5168\u6269\u5c55\uff0c\u5b9e\u4e3a %s' % r1['stage']['key'])
    ck(r1['gap'] == 0, '\u6b63\u4f8b\u8ddd\u79bb\u76ee\u6807\u5e94\u4e3a 0\uff0c\u5b9e\u4e3a %s' % r1['gap'])

    # 2 \u53cd\u4f8b: \u4e00\u62c9\u5c31\u65ad\u5374\u5df2\u505c\u624b
    r2 = calc(dict(base, windowpane={'can_stretch': True, 'breaks_at_once': True}))
    ck(r2['level'] == LEVEL_CONTINUE, '\u672a\u5230\u76ee\u6807\u9636\u6bb5\u5c31\u505c\u624b\u5e94\u5224\u8fd8\u9700\u7ee7\u7eed\uff0c\u5b9e\u4e3a %s' % r2['level'])
    ck(r2['stage']['key'] == 'forming', '\u4e00\u62c9\u5c31\u65ad\u5e94\u5224\u9762\u7b4b\u521d\u6b65\u5f62\u6210\uff0c\u5b9e\u4e3a %s' % r2['stage']['key'])
    ck(r2['short_stop'] is True, 'short_stop \u5e94\u4e3a True')

    # 3 \u53cd\u4f8b: \u62c9\u4e0d\u5f00\u4e5f\u4e0d\u900f\u5149
    r3 = calc(dict(base, knead_done=False, windowpane={'can_stretch': True, 'translucent': False}))
    ck(r3['stage']['key'] == 'expansion', '\u80fd\u62c9\u6210\u819c\u4e0d\u900f\u5149\u5e94\u5224\u6269\u5c55\u9636\u6bb5\uff0c\u5b9e\u4e3a %s' % r3['stage']['key'])

    # 4 \u53cd\u4f8b: \u6e29\u5ea6\u8d85\u6807\u5fc5\u987b\u4f18\u5148\u5904\u7406
    r4 = calc(dict(base, dough_temp=30))
    ck(r4['level'] == LEVEL_HARD, '\u6e29\u5ea6\u8d85\u8fc7\u8b66\u6212\u4e0a\u9650\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r4['level'])
    ck(r4['temp_row']['status'] == '\u8d85\u6807', '\u6e29\u5ea6\u72b6\u6001\u5e94\u4e3a\u8d85\u6807\uff0c\u5b9e\u4e3a %s' % r4['temp_row']['status'])
    ck('\u9762\u7b4b\u6613\u65ad' in r4['temp_row']['why'], '\u6e29\u5ea6\u8d85\u6807\u5fc5\u987b\u5e26\u51fa\u539f\u56e0\uff0c\u5b9e\u4e3a %s' % r4['temp_row']['why'])

    # 5 \u6e29\u5ea6\u5df2\u53d7\u635f
    r5 = calc(dict(base, dough_temp=34))
    ck(r5['temp_row']['status'] == '\u5df2\u53d7\u635f', '\u9ad8\u4e8e 32 \u5ea6\u5e94\u5224\u5df2\u53d7\u635f\uff0c\u5b9e\u4e3a %s' % r5['temp_row']['status'])
    ck(r5['level'] == LEVEL_HARD, '\u5df2\u53d7\u635f\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r5['level'])

    # 6 \u53cd\u4f8b: \u63c9\u8fc7\u5934\u4fe1\u53f7
    r6 = calc(dict(base, overdone_signs={'weeping': True, 'lost_elasticity': True}))
    ck(r6['level'] == LEVEL_HARD, '\u51fa\u73b0\u63c9\u8fc7\u5934\u4fe1\u53f7\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r6['level'])
    ck('\u8868\u9762\u6e17\u6c34\u53d1\u9ecf' in r6['overdone_hit'], '\u5e94\u70b9\u540d\u6e17\u6c34\u4fe1\u53f7\uff0c\u5b9e\u4e3a %s' % r6['overdone_hit'])

    # 7 \u53cd\u4f8b: \u9ec4\u6cb9\u63d0\u524d\u52a0
    r7 = calc(dict(base, checks=dict(allok, butter_after_expansion=False)))
    ck(r7['level'] == LEVEL_WEAK, '\u9ec4\u6cb9\u63d0\u524d\u52a0\u5e94\u5224\u8584\u5f31\u73af\u8282\uff0c\u5b9e\u4e3a %s' % r7['level'])
    ck('\u9ec4\u6cb9\u5728\u6269\u5c55\u9636\u6bb5\u540e\u52a0\u5165' in r7['bad'], '\u5e94\u70b9\u540d\u9ec4\u6cb9\u9879\uff0c\u5b9e\u4e3a %s' % r7['bad'])
    ck(CHECK_WHY['butter_after_expansion'] == '\u63d0\u524d\u52a0\u6cb9\u4f1a\u628a\u9762\u7b4b\u6cb9\u65ad\uff0c\u540e\u9762\u600e\u4e48\u63c9\u90fd\u62c9\u4e0d\u51fa\u819c',
       '\u9ec4\u6cb9\u9879\u5fc5\u987b\u5e26\u51fa\u4e3a\u4ec0\u4e48')

    # 8 \u53cd\u4f8b: \u76d0\u4e0e\u9175\u6bcd\u76f4\u63a5\u63a5\u89e6
    r8 = calc(dict(base, checks=dict(allok, salt_yeast_apart=False)))
    ck(r8['level'] == LEVEL_WEAK, '\u76d0\u9175\u6bcd\u672a\u9694\u79bb\u5e94\u5224\u8584\u5f31\u73af\u8282\uff0c\u5b9e\u4e3a %s' % r8['level'])
    ck('\u76d0\u4e0e\u9175\u6bcd\u672a\u76f4\u63a5\u63a5\u89e6' in r8['bad'], '\u5e94\u70b9\u540d\u76d0\u9175\u6bcd\u9879\uff0c\u5b9e\u4e3a %s' % r8['bad'])

    # 9 \u53cd\u4f8b: \u542b\u6db2\u91cf\u8d85\u51fa\u533a\u95f4
    r9 = calc(dict(base, hydration_pct=72))
    ck(r9['hyd_row']['status'] == '\u8d85\u51fa\u533a\u95f4', '\u542b\u6db2\u91cf 72 \u5bf9\u9ad8\u7b4b\u5e94\u5224\u8d85\u51fa\uff0c\u5b9e\u4e3a %s' % r9['hyd_row']['status'])
    ck(r9['level'] == LEVEL_WEAK, '\u542b\u6db2\u91cf\u8d85\u6807\u5e94\u5224\u8584\u5f31\u73af\u8282\uff0c\u5b9e\u4e3a %s' % r9['level'])

    # 10 \u5168\u9ea6\u4e0d\u9700\u8981\u8ffd\u6c42\u5b8c\u5168\u6269\u5c55
    r10 = calc(dict(base, flour='whole_wheat', hydration_pct=68,
                    checks=dict(allok), windowpane={'can_stretch': True, 'translucent': True, 'edge_smooth': True}))
    ck(r10['flour']['target_stage'] == STAGE_NAME['expansion'], '\u5168\u9ea6\u76ee\u6807\u5e94\u4e3a\u6269\u5c55\u9636\u6bb5')
    ck(r10['over_stage_note'] is not None, '\u5168\u9ea6\u505a\u5230\u5b8c\u5168\u6269\u5c55\u5e94\u7ed9\u51fa\u4e0d\u5fc5\u8ffd\u6c42\u7684\u63d0\u793a')

    # 11 \u6c34\u6e29\u6362\u7b97
    ck(water_temp(25, 28, 28, 3) == 16.0, '\u6c34\u6e29\u6362\u7b97\u5e94\u4e3a 16\uff0c\u5b9e\u4e3a %s' % water_temp(25, 28, 28, 3))
    ck(water_temp(25, 30, 30, 2) == 13.0, '\u6c34\u6e29\u6362\u7b97\u5e94\u4e3a 13\uff0c\u5b9e\u4e3a %s' % water_temp(25, 30, 30, 2))
    ck(water_advise(-1.0).startswith('\u7b97\u51fa\u7684\u6c34\u6e29\u4f4e\u4e8e 0'), '\u8d1f\u6c34\u6e29\u5e94\u63d0\u793a\u51b7\u85cf\u7c89\u7f38')
    ck(water_advise(2.0).startswith('\u7b97\u51fa\u7684\u6c34\u6e29\u4f4e\u4e8e 4'), '\u4f4e\u6c34\u6e29\u5e94\u63d0\u793a\u7528\u51b0\u6c34')

    # 12 \u7f3a\u5173\u952e\u4fe1\u606f\u5e94\u5224\u5f85\u786e\u8ba4(\u4e14\u4e0d\u80fd\u88ab\u300c\u5176\u4ed6\u90fd\u597d\u300d\u63a9\u76d6\u901a\u8fc7)
    r12 = calc(dict(base, dough_temp=None))
    ck(r12['level'] == LEVEL_UNKNOWN, '\u672a\u6d4b\u6e29\u5ea6\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r12['level'])
    r12b = calc(dict(base, checks=dict(allok, weighed=None)))
    ck(r12b['level'] == LEVEL_UNKNOWN, '\u68c0\u67e5\u9879\u672a\u586b\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r12b['level'])

    # 13 \u5224\u5b9a\u5206\u652f\u987a\u5e8f: \u771f\u5b9e\u7f3a\u9677\u4e0d\u80fd\u88ab\u300c\u4fe1\u606f\u4e0d\u5168\u300d\u538b\u6210\u5f85\u786e\u8ba4
    r13 = calc(dict(base, dough_temp=30, checks=dict(allok, weighed=None)))
    ck(r13['level'] == LEVEL_HARD, '\u6e29\u5ea6\u8d85\u6807\u4e14\u4fe1\u606f\u4e0d\u5168\u4ecd\u5e94\u5224\u5fc5\u987b\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r13['level'])
    r13b = calc(dict(base, windowpane={'can_stretch': True, 'breaks_at_once': True},
                     dough_temp=None, checks=dict(allok, weighed=None)))
    ck(r13b['level'] == LEVEL_CONTINUE, '\u9636\u6bb5\u672a\u5230\u4e14\u4fe1\u606f\u4e0d\u5168\u4ecd\u5e94\u5224\u8fd8\u9700\u7ee7\u7eed\uff0c\u5b9e\u4e3a %s' % r13b['level'])

    # 14 BOM \u4e24\u6761\u8def\u5f84
    bom_text = '\ufeff' + json.dumps({'flour': 'high_gluten', 'dough_temp': 30})
    r14 = calc(json.loads(bom_text.lstrip('\ufeff')))
    ck(r14['level'] == LEVEL_HARD, 'BOM \u5b57\u7b26\u4e32\u5e94\u80fd\u6b63\u786e\u89e3\u6790\uff0c\u5b9e\u4e3a %s' % r14['level'])
    ck(r14['temp_row']['value'] == 30.0, 'BOM \u8f93\u5165\u6e29\u5ea6\u5e94\u4e3a 30\uff0c\u5b9e\u4e3a %s' % r14['temp_row']['value'])
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe_bread.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps(dict(base, flour='all_purpose', hydration_pct=58)))
    try:
        loaded = json.loads(open(tmp, 'r', encoding='utf-8-sig').read())
        r14b = calc(loaded)
        ck(r14b['flour']['name'] == '\u4e2d\u7b4b\u9762\u7c89', 'utf-8-sig \u8bfb\u53d6\u5e94\u62ff\u5230\u4e2d\u7b4b\u9762\u7c89\uff0c\u5b9e\u4e3a %s' % r14b['flour']['name'])
        ck(r14b['flour']['target_stage'] == STAGE_NAME['near'], '\u4e2d\u7b4b\u9762\u7c89\u76ee\u6807\u5e94\u4e3a\u63a5\u8fd1\u5b8c\u5168\u6269\u5c55')
        ck(r14b['level'] == LEVEL_OK, '\u4e2d\u7b4b\u9762\u7c89\u542b\u6db2\u91cf 58 \u4e14\u505a\u5230\u5b8c\u5168\u6269\u5c55\u5e94\u5224\u53ef\u4ee5\u7ee7\u7eed\uff0c\u5b9e\u4e3a %s' % r14b['level'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 15 \u975e\u6cd5\u8f93\u5165\u5fc5\u987b\u62a5\u9519
    for payload, why in (
        ({'flour': 'rye'}, '\u672a\u77e5\u9762\u7c89'),
        ({'flour': 'high_gluten', 'checks': {'weighed': True, '\u62fc\u9519\u7684\u9879': True}}, '\u672a\u77e5\u68c0\u67e5\u9879'),
        ({'flour': 'high_gluten', 'windowpane': {'\u62fc\u9519\u7684\u5b57\u6bb5': True}}, '\u672a\u77e5\u819c\u5b57\u6bb5'),
        ({'flour': 'high_gluten', 'overdone_signs': {'\u62fc\u9519\u7684\u4fe1\u53f7': True}}, '\u672a\u77e5\u8fc7\u5934\u4fe1\u53f7'),
        ({'flour': 'high_gluten', 'dough_temp': '\u5f88\u70ed'}, '\u6e29\u5ea6\u975e\u6570\u5b57'),
        ({'flour': 'high_gluten', 'windowpane': '\u4e0d\u662f\u5bf9\u8c61'}, '\u819c\u975e\u5bf9\u8c61'),
        ({'flour': 'high_gluten', 'checks': '\u4e0d\u662f\u5bf9\u8c61'}, '\u68c0\u67e5\u9879\u975e\u5bf9\u8c61'),
        ('\u4e0d\u662f\u5bf9\u8c61', '\u8f93\u5165\u975e\u5bf9\u8c61'),
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
    for key in ('\u603b\u4f53\u5224\u5b9a', '\u9762\u7c89\u4e0e\u76ee\u6807\u9636\u6bb5', '\u5f53\u524d\u9762\u7b4b\u9636\u6bb5', '\u9762\u56e2\u6e29\u5ea6\u6838\u67e5',
                '\u52a0\u6c34\u6c34\u6e29\u6362\u7b97', '\u516b\u9879\u64cd\u4f5c\u68c0\u67e5', '\u660e\u786e\u7981\u6b62\u7684\u64cd\u4f5c', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355', '\u514d\u8d23'):
        ck(key in md, 'Markdown \u8f93\u51fa\u5e94\u542b\u7ae0\u8282 %s' % key)
    ck(len(r2['check_rows']) == 8, '\u68c0\u67e5\u9879\u5e94 8 \u6761\uff0c\u5b9e\u4e3a %d' % len(r2['check_rows']))
    ck(len(BANNED) == 6, '\u7981\u6b62\u9879\u5e94 6 \u6761\uff0c\u5b9e\u4e3a %d' % len(BANNED))
    ck(len(FLOUR) == 4, '\u9762\u7c89\u79cd\u7c7b\u5e94 4 \u79cd\uff0c\u5b9e\u4e3a %d' % len(FLOUR))

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u6b63\u4f8b/\u4e00\u62c9\u5c31\u65ad/\u6269\u5c55\u9636\u6bb5/\u6e29\u5ea6\u8d85\u6807/\u6e29\u5ea6\u53d7\u635f/'
               '\u63c9\u8fc7\u5934\u4fe1\u53f7/\u9ec4\u6cb9\u63d0\u524d/\u76d0\u9175\u6bcd\u672a\u9694\u79bb/\u542b\u6db2\u91cf\u8d85\u6807/\u5168\u9ea6\u76ee\u6807\u9636\u6bb5/\u6c34\u6e29\u6362\u7b97\u4e0e\u51b0\u6c34\u63d0\u9192/'
               '\u5f85\u786e\u8ba4/\u5224\u5b9a\u5206\u652f\u987a\u5e8f/\u672a\u77e5\u9762\u7c89\u4e0e\u672a\u77e5\u5b57\u6bb5/BOM \u4e24\u6761\u8def\u5f84/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u9762\u5305\u63c9\u9762\u72b6\u6001\u5224\u65ad\u4e0e\u624b\u6cd5\u6838\u67e5')
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
