# -*- coding: utf-8 -*-
"""\u51b0\u7bb1\u9664\u971c\u4e0e\u5316\u971c\u5468\u671f\u6838\u67e5\uff1a\u6309\u7ed3\u971c\u539a\u5ea6\u7ed9\u51fa\u5316\u971c\u5fc5\u8981\u6027\u3001\u5468\u671f\u5efa\u8bae\u4e0e\u5b89\u5168\u505a\u6cd5\u6821\u9a8c\u3002

\u7528\u6cd5:
  python defrost_check.py --file defrost.json [--out result.md] [--format json]
  python defrost_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u7ed3\u971c\u539a\u5ea6\u5206\u6863: (\u952e, \u4e2d\u6587\u540d, \u4e0b\u9650\u6beb\u7c73, \u4e0a\u9650\u6beb\u7c73, \u7b49\u7ea7, \u5f71\u54cd, \u5904\u7f6e)
ICE_TIERS = [
    ('light', '\u8f7b\u5ea6\u7ed3\u971c', 0, 5, '\u6b63\u5e38', '\u5236\u51b7\u6548\u7387\u57fa\u672c\u4e0d\u53d7\u5f71\u54cd\uff0c\u65e0\u9700\u5316\u971c',
     '\u4fdd\u6301\u73b0\u72b6\uff0c\u65e5\u5e38\u64e6\u62ed\u5373\u53ef'),
    ('moderate', '\u4e2d\u5ea6\u7ed3\u971c', 5, 10, '\u5f00\u59cb\u5f71\u54cd', '\u5236\u51b7\u6548\u7387\u4e0b\u964d\uff0c\u8017\u7535\u589e\u52a0\uff0c\u5236\u51b7\u901f\u5ea6\u53d8\u6162',
     '\u5b89\u6392\u5316\u971c\uff0c\u5efa\u8bae\u4e00\u5468\u5185\u5b8c\u6210'),
    ('heavy', '\u91cd\u5ea6\u7ed3\u971c', 10, 20, '\u660e\u663e\u5f71\u54cd', '\u8017\u7535\u663e\u8457\u589e\u52a0\uff0c\u538b\u7f29\u673a\u8d1f\u8377\u52a0\u91cd\uff0c\u6e29\u5dee\u52a0\u5927',
     '\u5c3d\u5feb\u5316\u971c\uff0c\u5efa\u8bae\u4e09\u5929\u5185\u5b8c\u6210'),
    ('severe', '\u4e25\u91cd\u7ed3\u971c', 20, 10000, '\u5fc5\u987b\u5316\u971c',
     '\u51b7\u51dd\u7ba1\u88ab\u51b0\u58f3\u5305\u8986\uff0c\u5236\u51b7\u80fd\u529b\u5927\u5e45\u4e0b\u964d\uff0c\u53ef\u80fd\u7f29\u77ed\u538b\u7f29\u673a\u5bff\u547d\u5e76\u589e\u52a0\u7528\u7535',
     '\u7acb\u5373\u5b89\u6392\u5316\u971c\uff0c\u4e0d\u8981\u7ee7\u7eed\u7d2f\u79ef'),
]

# \u5316\u971c\u5468\u671f\u5efa\u8bae: (\u4f7f\u7528\u5f3a\u5ea6\u952e, \u4e2d\u6587\u540d, \u5efa\u8bae\u5468\u671f\u6708, \u8bf4\u660e)
CYCLE = [
    ('light_use', '\u8f7b\u5ea6\u4f7f\u7528', 12,
     '\u4e00\u5230\u4e24\u4eba\u3001\u5f00\u95e8\u5c11\u3001\u51b7\u85cf\u4e3a\u4e3b\uff0c\u84b8\u53d1\u5668\u7ed3\u971c\u6162\uff0c\u53ef\u534a\u5e74\u5230\u4e00\u5e74\u5316\u4e00\u6b21'),
    ('normal_use', '\u4e00\u822c\u4f7f\u7528', 6,
     '\u4e09\u53e3\u4e4b\u5bb6\u3001\u6bcf\u65e5\u5f00\u95e8\u6570\u6b21\uff0c\u51b7\u51bb\u4e0e\u51b7\u85cf\u5e76\u7528\uff0c\u5efa\u8bae\u534a\u5e74\u5316\u4e00\u6b21'),
    ('heavy_use', '\u9ad8\u9891\u4f7f\u7528', 3,
     '\u56db\u4eba\u53ca\u4ee5\u4e0a\u3001\u9891\u7e41\u5f00\u5173\u3001\u5b58\u53d6\u5927\u91cf\u751f\u9c9c\uff0c\u5efa\u8bae\u6bcf\u5b63\u5ea6\u5316\u4e00\u6b21'),
    ('intensive', '\u6781\u9ad8\u9891\u4f7f\u7528', 2,
     '\u5546\u7528\u5f3a\u5ea6\u6216\u9891\u7e41\u5927\u91cf\u5b58\u53d6\uff0c\u5316\u971c\u5468\u671f\u5e94\u8fdb\u4e00\u6b65\u7f29\u77ed\u5e76\u8003\u8651\u589e\u52a0\u5316\u971c\u6b21\u6570'),
]

# \u7edd\u5bf9\u7981\u6b62\u7684\u64cd\u4f5c
FORBIDDEN = [
    ('\u51ff', '\u4e25\u7981\u7528\u5200\u51ff\u6216\u4efb\u4f55\u5c16\u9510\u5de5\u5177\u64ac\u522e\u51b7\u51bb\u5ba4\u7ed3\u51b0',
     '\u6781\u6613\u523a\u7a7f\u5185\u80c6\u6216\u5236\u51b7\u5242\u94dc\u7ba1\uff0c\u4e00\u65e6\u7834\u635f\u5236\u51b7\u5242\u6cc4\u6f0f\uff0c\u53ea\u80fd\u7531\u4e13\u4e1a\u7ef4\u4fee\u5904\u7406\uff0c\u4e14\u7ef4\u4fee\u8d39\u7528\u9ad8\u6602'),
    ('hot_water', '\u4e25\u7981\u7528\u70ed\u6c34\u6d47\u6dcb\u6216\u51b2\u6dcb\u51b7\u51bb\u5ba4',
     '\u5185\u5916\u6e29\u5dee\u8fc7\u5927\u4f1a\u5bfc\u81f4\u5185\u80c6\u5f00\u88c2\u3001\u5851\u6599\u4ef6\u53d8\u5f62\uff0c\u4e14\u4f1a\u4f7f\u51b7\u51bb\u5ba4\u98df\u54c1\u5c40\u90e8\u89e3\u51bb\u540e\u518d\u6b21\u51bb\u7ed3\uff0c'
     '\u52a0\u901f\u98df\u54c1\u53d8\u8d28'),
    ('hairdryer', '\u4e25\u7981\u7528\u70ed\u98ce\u67aa\u3001\u7535\u5439\u98ce\u7b49\u52a0\u70ed\u8bbe\u5907\u5bf9\u7740\u5185\u80c6\u5439',
     '\u5c40\u90e8\u9ad8\u6e29\u540c\u6837\u53ef\u80fd\u635f\u4f24\u5185\u80c6\u4e0e\u7ba1\u8def\uff0c\u4e14\u52a0\u70ed\u4e0d\u5747\u9020\u6210\u98ce\u9669'),
    ('pry', '\u4e25\u7981\u5f3a\u884c\u64ac\u5f00\u88ab\u51b0\u7c98\u4f4f\u7684\u62bd\u5c49\u6216\u95e8\u5c01',
     '\u7528\u529b\u64ac\u4f1a\u6495\u88c2\u95e8\u5c01\u6761\u4e0e\u5851\u6599\u5185\u80c6\uff0c\u5bfc\u81f4\u5bc6\u5c01\u5931\u6548\u4e0e\u6f0f\u51b7'),
    ('force_power', '\u4e25\u7981\u5728\u7ed3\u51b0\u672a\u6e05\u9664\u65f6\u53cd\u590d\u901a\u7535\u6d4b\u8bd5',
     '\u7ed3\u51b0\u4f1a\u8feb\u4f7f\u538b\u7f29\u673a\u9ad8\u8d1f\u8377\u6301\u7eed\u8fd0\u8f6c\uff0c\u7f29\u77ed\u538b\u7f29\u673a\u5bff\u547d\u5e76\u663e\u8457\u8017\u7535'),
    ('hot_water_food', '\u4e25\u7981\u7528\u70ed\u6c34\u76f4\u63a5\u51b2\u6dcb\u51b7\u51bb\u5ba4\u5185\u7684\u98df\u54c1',
     '\u5c40\u90e8\u5347\u6e29\u540e\u518d\u6b21\u51bb\u7ed3\uff0c\u7834\u574f\u98df\u54c1\u54c1\u8d28\u5e76\u589e\u52a0\u5fae\u751f\u7269\u7e41\u6b96\u98ce\u9669'),
]

# \u6b63\u786e\u7684\u5316\u971c\u505a\u6cd5\u6b65\u9aa4
CORRECT_STEPS = [
    '\u65ad\u7535\uff1a\u62d4\u6389\u63d2\u5934\u6216\u5173\u95ed\u7535\u6e90\u5f00\u5173\uff0c\u4e0d\u8981\u53ea\u8c03\u5236\u51b7\u5f00\u5173',
    '\u5f00\u95e8\u9759\u7f6e\uff1a\u6253\u5f00\u51b7\u51bb\u5ba4\u95e8\uff0c\u8ba9\u7a7a\u6c14\u81ea\u7136\u6d41\u901a\uff0c\u7b49\u5f85\u51b0\u5c42\u81ea\u7136\u878d\u5316',
    '\u653e\u7f6e\u63a5\u6c34\uff1a\u95e8\u4f53\u4e0b\u57ab\u6bdb\u5dfe\u6216\u653e\u7f6e\u63a5\u6c34\u76c6\uff0c\u9632\u6b62\u878d\u6c34\u6d41\u5165\u7535\u5668\u6216\u5730\u9762',
    '\u6e29\u6c34\u8f85\u52a9\uff1a\u53ef\u5728\u51b7\u51bb\u5ba4**\u5185\u80c6**\u5916\u4fa7\u6216\u95e8\u4f53\u653e\u7f6e\u6e29\u6c34\u5bb9\u5668\u8f85\u52a9\uff0c'
    '\u4f46**\u4e25\u7981\u76f4\u63a5\u6d47\u6dcb\u5185\u80c6\u6216\u7ba1\u8def**',
    '\u6e05\u7406\u5316\u971c\u6c34\uff1a\u878d\u5316\u540e\u7528\u5e72\u5e03\u64e6\u62ed\u5185\u58c1\u4e0e\u6392\u6c34\u53e3\uff0c\u4fdd\u6301\u6392\u6c34\u901a\u7545',
    '\u64e6\u5e72\u786e\u8ba4\uff1a\u5185\u80c6\u4e0e\u95e8\u5c01\u5f7b\u5e95\u64e6\u5e72\uff0c\u6392\u6c34\u5b54\u65e0\u5835\u585e',
    '\u56de\u6e29\u540e\u518d\u901a\u7535\uff1a\u9759\u7f6e 1 \u81f3 2 \u5c0f\u65f6\u8ba9\u5185\u90e8\u56de\u6e29\uff0c\u518d\u901a\u7535',
    '\u901a\u7535\u540e\u786e\u8ba4\uff1a\u653e\u7f6e\u6e29\u5ea6\u8ba1\uff0c\u786e\u8ba4\u6e29\u5ea6\u7a33\u5b9a\u56de\u843d\u5230\u6b63\u5e38\u8303\u56f4\u540e\u518d\u653e\u56de\u98df\u54c1',
    '\u8bb0\u5f55\uff1a\u8bb0\u4e0b\u5316\u971c\u65e5\u671f\uff0c\u4f5c\u4e3a\u4e0b\u4e00\u6b21\u5316\u971c\u7684\u57fa\u51c6',
]

# \u5316\u971c\u671f\u95f4\u98df\u54c1\u5904\u7406
FOOD_RULE = [
    '\u5316\u971c\u524d\u628a\u98df\u54c1**\u8f6c\u79fb\u5230\u4fdd\u6e29\u7bb1\u6216\u4fdd\u6e29\u888b**\u4e2d\uff0c\u5c3d\u91cf\u51cf\u5c11\u6e29\u5ea6\u6ce2\u52a8',
    '\u5316\u971c\u65f6\u95f4\u63a7\u5236\u5728**\u6570\u5c0f\u65f6\u5185\u5b8c\u6210**\uff0c\u4e0d\u8981\u4e00\u653e\u5c31\u662f\u4e00\u4e24\u5929',
    '\u5df2\u89e3\u51bb\u7684\u751f\u9c9c**\u4e0d\u8981\u518d\u6b21\u51b7\u51bb**\uff0c\u6309\u5f53\u6b21\u5403\u5b8c\u5904\u7406',
    '\u5df2\u89e3\u51bb\u4f46\u4ecd\u51b0\u51b7\u7684\u98df\u54c1\u53ef\u51b7\u85cf\uff0c\u4f46**\u4fdd\u5b58\u671f\u6309\u5df2\u89e3\u51bb\u53e3\u5f84\u7f29\u77ed**',
    '\u51b0\u5757\u53ef\u4fdd\u7559\uff0c\u7528\u4e8e\u540e\u7eed\u51b7\u85cf\u964d\u6e29',
    '\u5316\u971c\u7ed3\u675f\u540e**\u786e\u8ba4\u6e29\u5ea6\u6062\u590d**\u518d\u653e\u56de\u98df\u54c1\uff0c\u907f\u514d\u6e29\u5347\u5bfc\u81f4\u53d8\u8d28',
]

# \u56de\u6e29\u7b49\u5f85\u8981\u6c42
WAIT_NOTE = (
    '\u5316\u971c\u5b8c\u6210\u540e\u5efa\u8bae\u9759\u7f6e 1 \u81f3 2 \u5c0f\u65f6\u518d\u901a\u7535\uff0c\u8ba9\u5185\u90e8\u6e29\u5ea6\u56de\u6e29\uff0c'
    '\u907f\u514d\u521a\u653e\u56de\u7684\u98df\u54c1\u88ab\u9aa4\u51b7\u8868\u9762\u6fc0\u51b7\u3002'
    '\u66f4\u91cd\u8981\u7684\u662f\uff1a**\u901a\u7535\u540e\u5fc5\u987b\u786e\u8ba4\u6e29\u5ea6\u7a33\u5b9a\u56de\u843d\u5230\u6b63\u5e38\u8303\u56f4\uff0c\u624d\u80fd\u653e\u56de\u98df\u54c1**\u3002'
    '\u521a\u901a\u7535\u65f6\u5185\u90e8\u6e29\u5ea6\u5c1a\u672a\u4e0b\u964d\uff0c\u76f4\u63a5\u653e\u56de\u98df\u54c1\u4f1a\u8ba9\u6e29\u63a7\u7cfb\u7edf\u957f\u65f6\u95f4\u9ad8\u8d1f\u8377\u8fd0\u8f6c\u3002'
)

# \u8f6c\u4e13\u4e1a\u7ef4\u4fee\u7684\u60c5\u5f62
PROFESSIONAL = [
    '\u9664\u971c\u540e\u5236\u51b7\u6548\u679c**\u4ecd\u672a\u6062\u590d**\uff0c\u6216\u6062\u590d\u540e\u5f88\u5feb\u53c8\u7ed3\u539a\u971c',
    '\u51b7\u51bb\u5ba4\u5185\u80c6\u6709**\u88c2\u7eb9\u3001\u7834\u635f\u6216\u6e17\u6c34**',
    '\u53d1\u73b0\u5236\u51b7\u7ba1\u8def\u6709**\u6cb9\u6e0d\u6e17\u51fa**\uff0c\u53ef\u80fd\u5236\u51b7\u5242\u6cc4\u6f0f',
    '\u6392\u6c34\u5b54**\u5b8c\u5168\u5835\u585e**\u4e14\u65e0\u6cd5\u758f\u901a\uff0c\u878d\u6c34\u79ef\u5b58\u5728\u5185\u80c6',
    '\u538b\u7f29\u673a\u6709**\u5f02\u5e38\u566a\u97f3\u3001\u6301\u7eed\u9707\u52a8\u6216\u9891\u7e41\u542f\u505c**',
    '\u5316\u971c\u8fc7\u7a0b\u4e2d\u542c\u5230**\u5f02\u54cd\u6216\u95fb\u5230\u7126\u7cca\u5473**',
    '\u51b0\u7bb1\u6574\u4f53\u5f02\u5e38\u7ed3\u971c\uff08\u5982\u53ea\u6709\u4e00\u89d2\u7ed3\u971c\u4e25\u91cd\uff09\uff0c\u53ef\u80fd\u4e3a\u7cfb\u7edf\u95ee\u9898',
]


def norm(k):
    return str(k or '').strip().lower().replace(' ', '')


def tier_of(mm):
    if mm is None:
        raise ValueError('\u7f3a\u5c11 ice_mm\uff08\u7ed3\u971c\u539a\u5ea6\uff0c\u5355\u4f4d\u6beb\u7c73\uff09')
    v = float(mm)
    if v < 0:
        raise ValueError('ice_mm \u4e0d\u80fd\u4e3a\u8d1f\u6570')
    for key, name, lo, hi, level, effect, action in ICE_TIERS:
        if lo <= v < hi:
            return key, name, level, effect, action
    return ('severe', '\u4e25\u91cd\u7ed3\u971c', '\u5fc5\u987b\u5316\u971c', '\u5236\u51b7\u80fd\u529b\u5927\u5e45\u4e0b\u964d', '\u7acb\u5373\u5b89\u6392\u5316\u971c')


def cycle_of(use):
    u = norm(use)
    for key, name, months, note in CYCLE:
        if key == u:
            return key, name, months, note
    raise ValueError('usage \u53ea\u80fd\u586b %s \u4e4b\u4e00' % '/'.join(c[0] for c in CYCLE))


def calc(data):
    mm = data.get('ice_mm')
    key, name, level, effect, action = tier_of(mm)
    ckey, cname, months, cnote = cycle_of(data.get('usage') or 'normal_use')

    last = data.get('last_defrost')
    days_since = data.get('days_since')
    urgency = None
    if days_since is not None:
        d = float(days_since)
        if d < 0:
            raise ValueError('days_since \u4e0d\u80fd\u4e3a\u8d1f\u6570')
        ratio = d / (months * 30.0)
        if ratio >= 1.0:
            urgency = '\u5df2\u8d85\u51fa\u5efa\u8bae\u5468\u671f'
        elif ratio >= 0.7:
            urgency = '\u63a5\u8fd1\u5efa\u8bae\u5468\u671f'
        else:
            urgency = '\u5c1a\u5728\u5efa\u8bae\u5468\u671f\u5185'

    if level == '\u6b63\u5e38':
        verdict = '\u65e0\u9700\u5316\u971c'
    elif level == '\u5f00\u59cb\u5f71\u54cd':
        verdict = '\u5efa\u8bae\u5b89\u6392\u5316\u971c'
    elif level == '\u660e\u663e\u5f71\u54cd':
        verdict = '\u5e94\u5c3d\u5feb\u5316\u971c'
    else:
        verdict = '\u5fc5\u987b\u7acb\u5373\u5316\u971c'

    if urgency == '\u5df2\u8d85\u51fa\u5efa\u8bae\u5468\u671f':
        verdict = '\u5fc5\u987b\u7acb\u5373\u5316\u971c'

    warns = []
    if level != '\u6b63\u5e38':
        warns.append('%s\uff1a%s\uff0c%s' % (name, effect, action))
    if urgency == '\u5df2\u8d85\u51fa\u5efa\u8bae\u5468\u671f':
        warns.append('\u8ddd\u4e0a\u6b21\u5316\u971c\u5df2\u8d85\u8fc7%s\u7684\u5efa\u8bae\u5468\u671f %d \u4e2a\u6708\uff0c\u5e94\u5c3d\u5feb\u5b89\u6392' % (cname, months))
    elif urgency == '\u63a5\u8fd1\u5efa\u8bae\u5468\u671f':
        warns.append('\u8ddd\u4e0a\u6b21\u5316\u971c\u5df2\u63a5\u8fd1%s\u7684\u5efa\u8bae\u5468\u671f %d \u4e2a\u6708\uff0c\u53ef\u63d0\u524d\u5b89\u6392' % (cname, months))
    if level == '\u5fc5\u987b\u5316\u971c' or urgency == '\u5df2\u8d85\u51fa\u5efa\u8bae\u5468\u671f':
        warns.append('**\u4e25\u7981\u7528\u5200\u51ff\u3001\u70ed\u6c34\u6d47\u6dcb\u6216\u70ed\u98ce\u67aa\u52a0\u70ed\u5185\u80c6**\uff0c\u6b63\u786e\u505a\u6cd5\u662f\u65ad\u7535\u540e\u81ea\u7136\u5316\u971c')

    return {
        'ice_mm': mm,
        'tier': key,
        'tier_name': name,
        'level': level,
        'effect': effect,
        'action': action,
        'usage': ckey,
        'usage_name': cname,
        'cycle_months': months,
        'cycle_note': cnote,
        'last_defrost': last,
        'days_since': days_since,
        'urgency': urgency,
        'verdict': verdict,
        'warns': warns,
        'tiers': [{'key': k, 'name': n, 'lo': lo, 'hi': hi, 'level': lv,
                   'effect': e, 'action': a}
                  for k, n, lo, hi, lv, e, a in ICE_TIERS],
        'forbidden': [{'key': k, 'rule': r, 'why': w} for k, r, w in FORBIDDEN],
        'steps': CORRECT_STEPS,
        'food_rule': FOOD_RULE,
        'wait_note': WAIT_NOTE,
        'professional': PROFESSIONAL,
    }


def render_md(r):
    L = []
    L.append('# \u51b0\u7bb1\u9664\u971c\u4e0e\u5316\u971c\u5468\u671f\u6838\u67e5')
    L.append('')
    L.append('## \u4e00\u3001\u603b\u4f53\u5224\u5b9a')
    L.append('')
    L.append('**%s**' % r['verdict'])
    L.append('')
    L.append('| \u9879 | \u503c |')
    L.append('|---|---|')
    L.append('| \u7ed3\u971c\u539a\u5ea6 | %s \u6beb\u7c73 |' % r['ice_mm'])
    L.append('| \u539a\u5ea6\u5206\u6863 | %s\uff08%s\uff09 |' % (r['tier_name'], r['level']))
    L.append('| \u5bf9\u5236\u51b7\u7684\u5f71\u54cd | %s |' % r['effect'])
    L.append('| \u5904\u7f6e\u5efa\u8bae | %s |' % r['action'])
    L.append('| \u4f7f\u7528\u5f3a\u5ea6 | %s |' % r['usage_name'])
    L.append('| \u5efa\u8bae\u5316\u971c\u5468\u671f | %d \u4e2a\u6708 |' % r['cycle_months'])
    L.append('| \u5468\u671f\u4f9d\u636e | %s |' % r['cycle_note'])
    L.append('| \u8ddd\u4e0a\u6b21\u5316\u971c | %s \u5929 |' % (r['days_since'] if r['days_since'] is not None else '\u672a\u586b\u5199'))
    L.append('| \u5468\u671f\u72b6\u6001 | %s |' % (r['urgency'] if r['urgency'] else '\u672a\u586b\u5199'))
    L.append('')
    L.append('## \u4e8c\u3001\u7ed3\u971c\u539a\u5ea6\u5206\u6863\u8868')
    L.append('')
    L.append('| \u5206\u6863 | \u539a\u5ea6\u8303\u56f4\uff08\u6beb\u7c73\uff09 | \u7b49\u7ea7 | \u5bf9\u5236\u51b7\u7684\u5f71\u54cd | \u5904\u7f6e |')
    L.append('|---|---|---|---|---|')
    for t in r['tiers']:
        hi = t['hi'] if t['hi'] < 10000 else 10000
        L.append('| %s | %d \u81f3 %d | %s | %s | %s |'
                 % (t['name'], t['lo'], hi, t['level'], t['effect'], t['action']))
    L.append('')
    L.append('## \u4e09\u3001\u7edd\u5bf9\u7981\u6b62\u7684\u64cd\u4f5c')
    L.append('')
    for f in r['forbidden']:
        L.append('- **%s**' % f['rule'])
        L.append('  - \u4e3a\u4ec0\u4e48\uff1a%s' % f['why'])
    L.append('')
    L.append('## \u56db\u3001\u6b63\u786e\u7684\u5316\u971c\u505a\u6cd5')
    L.append('')
    for i, s in enumerate(r['steps'], 1):
        L.append('%d. %s' % (i, s))
    L.append('')
    L.append('## \u4e94\u3001\u5316\u971c\u671f\u95f4\u7684\u98df\u54c1\u5904\u7406')
    L.append('')
    for f in r['food_rule']:
        L.append('- %s' % f)
    L.append('')
    L.append('## \u516d\u3001\u56de\u6e29\u4e0e\u653e\u56de\u98df\u54c1')
    L.append('')
    L.append('- %s' % r['wait_note'])
    L.append('')
    L.append('## \u4e03\u3001\u63d0\u793a')
    L.append('')
    if r['warns']:
        for w in r['warns']:
            L.append('- %s' % w)
    else:
        L.append('- \u7ed3\u971c\u539a\u5ea6\u4e0e\u5468\u671f\u5747\u5728\u6b63\u5e38\u8303\u56f4\uff0c\u4fdd\u6301\u73b0\u72b6')
    L.append('')
    L.append('## \u516b\u3001\u9700\u8f6c\u4e13\u4e1a\u7ef4\u4fee\u7684\u60c5\u5f62')
    L.append('')
    for p in r['professional']:
        L.append('- %s' % p)
    L.append('')
    L.append('## \u4e5d\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] \u5316\u971c\u524d\u5df2\u65ad\u7535\uff0c\u4e0d\u662f\u53ea\u8c03\u5236\u51b7\u5f00\u5173')
    L.append('- [ ] \u672a\u4f7f\u7528\u5200\u51ff\u3001\u70ed\u6c34\u6d47\u6dcb\u6216\u70ed\u98ce\u67aa')
    L.append('- [ ] \u95e8\u4e0b\u5df2\u57ab\u6bdb\u5dfe\u6216\u653e\u63a5\u6c34\u76c6\uff0c\u878d\u6c34\u672a\u6d41\u5165\u7535\u5668')
    L.append('- [ ] \u5316\u971c\u540e\u5df2\u64e6\u5e72\u5185\u80c6\u5e76\u758f\u901a\u6392\u6c34\u5b54')
    L.append('- [ ] \u9759\u7f6e\u56de\u6e29 1 \u81f3 2 \u5c0f\u65f6\u540e\u624d\u901a\u7535')
    L.append('- [ ] \u901a\u7535\u540e\u786e\u8ba4\u6e29\u5ea6\u56de\u843d\uff0c\u624d\u653e\u56de\u98df\u54c1')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    # 1 \u539a\u5ea6\u5206\u6863\u8fb9\u754c
    k1, n1, l1, _, _ = tier_of(3)
    ck(k1 == 'light' and l1 == '\u6b63\u5e38', '3 \u6beb\u7c73\u5e94\u5c5e\u8f7b\u5ea6\uff0c\u5b9e\u4e3a %s/%s' % (k1, l1))
    k2, _, l2, _, _ = tier_of(5)
    ck(k2 == 'moderate', '5 \u6beb\u7c73\u5e94\u5c5e\u4e2d\u5ea6\uff0c\u5b9e\u4e3a %s' % k2)
    ck(l2 == '\u5f00\u59cb\u5f71\u54cd', '\u4e2d\u5ea6\u5e94\u4e3a\u5f00\u59cb\u5f71\u54cd\uff0c\u5b9e\u4e3a %s' % l2)
    k3, _, l3, _, _ = tier_of(15)
    ck(k3 == 'heavy' and l3 == '\u660e\u663e\u5f71\u54cd', '15 \u6beb\u7c73\u5e94\u5c5e\u91cd\u5ea6\uff0c\u5b9e\u4e3a %s/%s' % (k3, l3))
    k4, _, l4, _, _ = tier_of(25)
    ck(k4 == 'severe' and l4 == '\u5fc5\u987b\u5316\u971c', '25 \u6beb\u7c73\u5e94\u5c5e\u4e25\u91cd\uff0c\u5b9e\u4e3a %s/%s' % (k4, l4))

    # 2 \u6070\u597d\u8fb9\u754c\u503c
    ck(tier_of(10)[0] == 'heavy', '10 \u6beb\u7c73\u5e94\u8fdb\u5165\u91cd\u5ea6\u533a\u95f4\uff0c\u5b9e\u4e3a %s' % tier_of(10)[0])
    ck(tier_of(0)[0] == 'light', '0 \u6beb\u7c73\u5e94\u5c5e\u8f7b\u5ea6\uff0c\u5b9e\u4e3a %s' % tier_of(0)[0])

    # 3 \u5224\u5b9a\u7ed3\u8bba
    ck(calc({'ice_mm': 3})['verdict'] == '\u65e0\u9700\u5316\u971c', '\u8f7b\u5ea6\u5e94\u65e0\u9700\u5316\u971c')
    ck(calc({'ice_mm': 7})['verdict'] == '\u5efa\u8bae\u5b89\u6392\u5316\u971c', '\u4e2d\u5ea6\u5e94\u5efa\u8bae\u5316\u971c')
    ck(calc({'ice_mm': 15})['verdict'] == '\u5e94\u5c3d\u5feb\u5316\u971c', '\u91cd\u5ea6\u5e94\u5c3d\u5feb\u5316\u971c')
    ck(calc({'ice_mm': 30})['verdict'] == '\u5fc5\u987b\u7acb\u5373\u5316\u971c', '\u4e25\u91cd\u5e94\u7acb\u5373\u5316\u971c')

    # 4 5 \u6beb\u7c73\u662f\u5f71\u54cd\u5236\u51b7\u7684\u5173\u952e\u9608\u503c
    r4 = calc({'ice_mm': 5})
    ck('\u5236\u51b7' in r4['effect'], '\u4e2d\u5ea6\u5e94\u8bf4\u660e\u5bf9\u5236\u51b7\u7684\u5f71\u54cd\uff0c\u5b9e\u4e3a %s' % r4['effect'])
    ck(any('\u4e00\u5468\u5185' in w for w in r4['warns']),
       '\u4e2d\u5ea6\u5e94\u7ed9\u51fa\u4e00\u5468\u5185\u5b8c\u6210\u5efa\u8bae\uff0c\u5b9e\u4e3a %s' % r4['warns'])

    # 5 \u5316\u971c\u5468\u671f\u6309\u4f7f\u7528\u5f3a\u5ea6
    ck(calc({'ice_mm': 1, 'usage': 'light_use'})['cycle_months'] == 12, '\u8f7b\u5ea6\u4f7f\u7528\u5e94\u4e3a 12 \u4e2a\u6708')
    ck(calc({'ice_mm': 1, 'usage': 'normal_use'})['cycle_months'] == 6, '\u4e00\u822c\u4f7f\u7528\u5e94\u4e3a 6 \u4e2a\u6708')
    ck(calc({'ice_mm': 1, 'usage': 'heavy_use'})['cycle_months'] == 3, '\u9ad8\u9891\u4f7f\u7528\u5e94\u4e3a 3 \u4e2a\u6708')
    ck(calc({'ice_mm': 1})['usage'] == 'normal_use',
       '\u672a\u586b usage \u5e94\u9ed8\u8ba4\u4e00\u822c\u4f7f\u7528\uff0c\u5b9e\u4e3a %s' % calc({'ice_mm': 1})['usage'])

    # 6 \u5468\u671f\u72b6\u6001\u5224\u5b9a
    r6 = calc({'ice_mm': 1, 'usage': 'normal_use', 'days_since': 30})
    ck(r6['urgency'] == '\u5c1a\u5728\u5efa\u8bae\u5468\u671f\u5185', '30 \u5929\u5bf9 180 \u5929\u5e94\u5c5e\u5468\u671f\u5185\uff0c\u5b9e\u4e3a %s' % r6['urgency'])
    r6b = calc({'ice_mm': 1, 'usage': 'normal_use', 'days_since': 130})
    ck(r6b['urgency'] == '\u63a5\u8fd1\u5efa\u8bae\u5468\u671f', '130 \u5929\u5bf9 180 \u5929\u5e94\u63a5\u8fd1\u5468\u671f\uff0c\u5b9e\u4e3a %s' % r6b['urgency'])
    r6c = calc({'ice_mm': 1, 'usage': 'normal_use', 'days_since': 200})
    ck(r6c['urgency'] == '\u5df2\u8d85\u51fa\u5efa\u8bae\u5468\u671f', '200 \u5929\u5e94\u8d85\u5468\u671f\uff0c\u5b9e\u4e3a %s' % r6c['urgency'])
    ck(r6c['verdict'] == '\u5fc5\u987b\u7acb\u5373\u5316\u971c', '\u8d85\u5468\u671f\u5e94\u7acb\u5373\u5316\u971c\uff0c\u5b9e\u4e3a %s' % r6c['verdict'])

    # 7 \u8d85\u5468\u671f\u5373\u4f7f\u539a\u5ea6\u8f7b\u4e5f\u8981\u6c42\u5316\u971c
    ck(calc({'ice_mm': 2, 'usage': 'normal_use', 'days_since': 300})['verdict'] == '\u5fc5\u987b\u7acb\u5373\u5316\u971c',
       '\u8f7b\u5ea6\u4f46\u8d85\u5468\u671f\u4e5f\u5e94\u7acb\u5373\u5316\u971c')

    # 8 \u7981\u6b62\u64cd\u4f5c\u9f50\u5168
    ck(len(FORBIDDEN) >= 6, '\u7981\u6b62\u9879\u81f3\u5c11 6 \u6761\uff0c\u5b9e\u4e3a %d' % len(FORBIDDEN))
    fr = [f[1] for f in FORBIDDEN]
    ck(any('\u4e25\u7981\u7528\u5200\u51ff' in x for x in fr), '\u5fc5\u987b\u542b\u4e25\u7981\u7528\u5200\u51ff')
    ck(any('\u4e25\u7981\u7528\u70ed\u6c34\u6d47\u6dcb' in x for x in fr), '\u5fc5\u987b\u542b\u4e25\u7981\u70ed\u6c34\u6d47\u6dcb\u51b7\u51bb\u5ba4')
    ck(any('\u5185\u80c6' in f[2] for f in FORBIDDEN), '\u5e94\u8bf4\u660e\u5185\u80c6\u7834\u635f\u98ce\u9669')

    # 9 \u6b63\u786e\u6b65\u9aa4\u542b\u65ad\u7535\u4e0e\u56de\u6e29
    s = ' '.join(CORRECT_STEPS)
    ck('\u65ad\u7535' in s, '\u6b63\u786e\u505a\u6cd5\u5fc5\u987b\u542b\u65ad\u7535')
    ck('\u56de\u6e29' in s or '\u9759\u7f6e' in s, '\u6b63\u786e\u505a\u6cd5\u5fc5\u987b\u542b\u56de\u6e29\u9759\u7f6e')
    ck('\u786e\u8ba4\u6e29\u5ea6' in s, '\u6b63\u786e\u505a\u6cd5\u5fc5\u987b\u542b\u786e\u8ba4\u6e29\u5ea6\u6062\u590d')
    ck(len(CORRECT_STEPS) >= 8, '\u6b63\u786e\u6b65\u9aa4\u81f3\u5c11 8 \u6b65\uff0c\u5b9e\u4e3a %d' % len(CORRECT_STEPS))

    # 10 \u98df\u54c1\u5904\u7406\u89c4\u5219
    ft = ' '.join(FOOD_RULE)
    ck('\u4e0d\u8981\u518d\u6b21\u51b7\u51bb' in ft, '\u98df\u54c1\u89c4\u5219\u5fc5\u987b\u542b\u4e0d\u53ef\u518d\u6b21\u51b7\u51bb')
    ck('\u786e\u8ba4\u6e29\u5ea6\u7a33\u5b9a\u56de\u843d' in WAIT_NOTE, '\u5fc5\u987b\u542b\u786e\u8ba4\u6e29\u5ea6\u7a33\u5b9a\u56de\u843d\u540e\u518d\u653e\u56de\uff0c\u5b9e\u4e3a %s' % WAIT_NOTE)

    # 11 BOM \u4e24\u6761\u8def\u5f84
    bom = '\ufeff{"ice_mm": 12, "usage": "heavy_use", "days_since": 100}'
    r11 = calc(json.loads(bom.lstrip('\ufeff')))
    ck(r11['tier'] == 'heavy', 'BOM \u8f93\u5165\u5e94\u6b63\u786e\u89e3\u6790\uff0c\u5b9e\u4e3a %s' % r11['tier'])
    ck(r11['cycle_months'] == 3, '\u9ad8\u9891\u4f7f\u7528\u5e94 3 \u4e2a\u6708\uff0c\u5b9e\u4e3a %s' % r11['cycle_months'])
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe7.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps({'ice_mm': 22}))
    try:
        r11b = calc(json.loads(open(tmp, 'r', encoding='utf-8-sig').read()))
        ck(r11b['verdict'] == '\u5fc5\u987b\u7acb\u5373\u5316\u971c', 'utf-8-sig \u8bfb\u53d6\u5e94\u6b63\u5e38\uff0c\u5b9e\u4e3a %s' % r11b['verdict'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 12 \u975e\u6cd5\u8f93\u5165
    for bad, why in (
        ({}, '\u7f3a\u5c11 ice_mm'),
        ({'ice_mm': -3}, '\u8d1f\u539a\u5ea6'),
        ({'ice_mm': 5, 'usage': '\u4e0d\u5b58\u5728\u7684\u5f3a\u5ea6'}, '\u975e\u6cd5 usage'),
        ({'ice_mm': 5, 'days_since': -10}, '\u8d1f\u5929\u6570'),
    ):
        try:
            calc(bad)
            ck(False, '\u7528\u4f8b12 %s \u5e94\u629b\u9519' % why)
        except ValueError:
            ck(True, '')

    # 13 \u8f93\u51fa\u7ed3\u6784
    md = render_md(calc({'ice_mm': 15}))
    for key in ('\u7ed3\u971c\u539a\u5ea6\u5206\u6863', '\u7edd\u5bf9\u7981\u6b62', '\u6b63\u786e\u7684\u5316\u971c\u505a\u6cd5', '\u5316\u971c\u671f\u95f4\u7684\u98df\u54c1\u5904\u7406',
                '\u56de\u6e29\u4e0e\u653e\u56de\u98df\u54c1', '\u9700\u8f6c\u4e13\u4e1a\u7ef4\u4fee', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355'):
        ck(key in md, 'Markdown \u8f93\u51fa\u5e94\u542b\u7ae0\u8282 %s' % key)
    ck(len(ICE_TIERS) == 4, '\u539a\u5ea6\u5206\u6863\u5e94 4 \u6863\uff0c\u5b9e\u4e3a %d' % len(ICE_TIERS))
    ck(len(PROFESSIONAL) >= 7, '\u8f6c\u4e13\u4e1a\u60c5\u5f62\u81f3\u5c11 7 \u6761\uff0c\u5b9e\u4e3a %d' % len(PROFESSIONAL))

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    msg = 'SELFTEST FAIL\n' + '\n'.join(errs) if errs else (
        'SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u539a\u5ea6\u5206\u6863\u4e0e\u8fb9\u754c\u503c/\u56db\u7ea7\u5224\u5b9a/5 \u6beb\u7c73\u9608\u503c/\u5468\u671f\u6309\u4f7f\u7528\u5f3a\u5ea6/'
        '\u5468\u671f\u72b6\u6001\u4e09\u6863/\u8d85\u5468\u671f\u5f3a\u5236\u5316\u971c/\u7981\u6b62\u64cd\u4f5c\u5b8c\u6574\u6027/\u6b63\u786e\u6b65\u9aa4\u542b\u65ad\u7535\u4e0e\u56de\u6e29/\u98df\u54c1\u4e0d\u53ef\u590d\u51bb/'
        'BOM \u4e24\u6761\u8def\u5f84/\u975e\u6cd5\u8f93\u5165/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u51b0\u7bb1\u9664\u971c\u4e0e\u5316\u971c\u5468\u671f\u6838\u67e5')
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
