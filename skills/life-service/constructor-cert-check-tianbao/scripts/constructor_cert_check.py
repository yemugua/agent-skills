#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u5efa\u9020\u5e08\u62a5\u8003\u6761\u4ef6\u6838\u67e5\u4e0e\u6ce8\u518c\u7ee7\u7eed\u6559\u80b2\u5230\u671f\u6d4b\u7b97\u3002

\u7528\u6cd5:
  python constructor_cert_check.py --mode exam --level yiji --education zhuanke --major relevant --work-years 8 --manage-years 5
  python constructor_cert_check.py --mode exam --level erji --education zhongzhuan --major relevant --manage-years 2
  python constructor_cert_check.py --mode reg --level yiji --reg-date 2024-06-01 --ce-hours 80 --age 42
  python constructor_cert_check.py --mode reg --level yiji --reg-date 2024-06-01 --ce-hours 120 --units 2
  python constructor_cert_check.py --selftest

\u53c2\u6570:
  --mode            exam \u62a5\u8003\u6761\u4ef6\u6838\u67e5 / reg \u6ce8\u518c\u4e0e\u7ee7\u7eed\u6559\u80b2\u6838\u67e5
  --level           yiji \u4e00\u7ea7\u5efa\u9020\u5e08 / erji \u4e8c\u7ea7\u5efa\u9020\u5e08
  --education       chuzhong \u521d\u4e2d / zhongzhuan \u4e2d\u4e13 / zhuanke \u5927\u4e13 / benke \u672c\u79d1 / shuoshi \u7855\u58eb / boshi \u535a\u58eb
  --major           relevant \u5de5\u7a0b\u7c7b\u6216\u5de5\u7a0b\u7ecf\u6d4e\u7c7b / near \u76f8\u8fd1\u4e13\u4e1a / other \u5176\u4ed6\u4e13\u4e1a
  --work-years      \u53c2\u52a0\u5de5\u4f5c\u603b\u5e74\u9650
  --manage-years    \u4ece\u4e8b\u5efa\u8bbe\u5de5\u7a0b\u9879\u76ee\u65bd\u5de5\u7ba1\u7406\u5de5\u4f5c\u5e74\u9650
  --senior-title    yes/no \u662f\u5426\u53d7\u8058\u62c5\u4efb\u5de5\u7a0b\u6216\u5de5\u7a0b\u7ecf\u6d4e\u7c7b\u9ad8\u7ea7\u4e13\u4e1a\u6280\u672f\u804c\u52a1
  --manage-20       yes/no \u5927\u4e13\u4ee5\u4e0a\u5b66\u5386\u4e14\u65bd\u5de5\u7ba1\u7406\u5de5\u4f5c\u662f\u5426\u6ee1 20 \u5e74\uff08\u4e00\u7ea7\u514d\u8bd5\u5224\u65ad\uff09
  --reg-date        \u672c\u6b21\u6ce8\u518c\u8d77\u59cb\u65e5\u6216\u4e0a\u6b21\u5ef6\u7eed\u6ce8\u518c\u65e5 YYYY-MM-DD
  --ce-hours        \u672c\u6ce8\u518c\u6709\u6548\u671f\u5185\u5df2\u5b8c\u6210\u7684\u7ee7\u7eed\u6559\u80b2\u5b66\u65f6
  --age             \u7533\u8bf7\u4eba\u5e74\u9f84
  --units           \u540c\u65f6\u53d7\u8058\uff08\u7533\u8bf7\u6ce8\u518c\uff09\u7684\u5355\u4f4d\u6570
  --accident        yes/no \u7533\u8bf7\u4e4b\u65e5\u524d 3 \u5e74\u5185\u62c5\u4efb\u9879\u76ee\u8d1f\u8d23\u4eba\u671f\u95f4\u9879\u76ee\u662f\u5426\u53d1\u751f\u8fc7\u91cd\u5927\u8d28\u91cf\u5b89\u5168\u4e8b\u6545
  --criminal        yes/no \u662f\u5426\u56e0\u6267\u4e1a\u6d3b\u52a8\u53d7\u5211\u4e8b\u5904\u7f5a\u4e14\u81ea\u5904\u7f5a\u51b3\u5b9a\u4e4b\u65e5\u8d77\u672a\u6ee1 5 \u5e74
  --revoked         yes/no \u662f\u5426\u88ab\u540a\u9500\u6ce8\u518c\u8bc1\u4e66\u4e14\u81ea\u5904\u7f5a\u51b3\u5b9a\u4e4b\u65e5\u8d77\u672a\u6ee1 2 \u5e74
  --as-of           \u6838\u67e5\u57fa\u51c6\u65e5\uff0c\u9ed8\u8ba4\u4eca\u5929
"""
import argparse
import json
import os
import re
import sys
from datetime import date, timedelta

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

LEVEL_NAME = {
    'yiji': '\u4e00\u7ea7\u5efa\u9020\u5e08',
    'erji': '\u4e8c\u7ea7\u5efa\u9020\u5e08',
}
EDU_NAME = {
    'chuzhong': '\u521d\u4e2d',
    'zhongzhuan': '\u4e2d\u7b49\u4e13\u79d1',
    'zhuanke': '\u5927\u5b66\u4e13\u79d1',
    'benke': '\u5927\u5b66\u672c\u79d1',
    'shuoshi': '\u7855\u58eb/\u53cc\u5b66\u58eb/\u7814\u7a76\u751f\u73ed',
    'boshi': '\u535a\u58eb',
}
EDU_RANK = {
    'chuzhong': 0,
    'zhongzhuan': 1,
    'zhuanke': 2,
    'benke': 3,
    'shuoshi': 4,
    'boshi': 5,
}
MAJOR_NAME = {
    'relevant': '\u5de5\u7a0b\u7c7b\u6216\u5de5\u7a0b\u7ecf\u6d4e\u7c7b',
    'near': '\u76f8\u8fd1\u4e13\u4e1a',
    'other': '\u5176\u4ed6\u4e13\u4e1a',
}
# \u4e00\u7ea7\u5efa\u9020\u5e08\uff1a\u5b66\u5386 -> (\u65bd\u5de5\u7ba1\u7406\u5e74\u9650\u8981\u6c42, \u5de5\u4f5c\u5e74\u9650\u8981\u6c42)
YIJI_REQ = {
    'zhuanke': (4, 6),
    'benke': (3, 4),
    'shuoshi': (2, 3),
    'boshi': (1, 1),
}
ERJI_MANAGE = 2
REG_VALID_YEARS = 3
CE_HOURS_REQUIRED = 120
RENEW_LEAD_DAYS = 30
MAX_AGE = 65


def parse_date(s):
    s = str(s).strip()
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', s)
    if not m:
        raise ValueError('\u65e5\u671f\u683c\u5f0f\u4e0d\u5bf9: %s' % s)
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def add_year(d, years):
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(year=d.year + years, day=28)


def fmt(d):
    return d.strftime('%Y-%m-%d')


def check_exam(args):
    level = args.level
    edu = args.education
    items = []

    def add(name, ok, detail):
        items.append({'name': name, 'result': ok, 'detail': detail})

    add('\u62a5\u8003\u7b49\u7ea7', '\u7b26\u5408', LEVEL_NAME.get(level, level) + '\uff0c\u4ee5\u6240\u5728\u7701\u4efd\u5f53\u5e74\u8003\u52a1\u516c\u544a\u4e3a\u51c6')

    rank = EDU_RANK.get(edu, -1)
    if level == 'yiji':
        if rank >= EDU_RANK['zhuanke']:
            add('\u5b66\u5386\u5c42\u6b21', '\u7b26\u5408', EDU_NAME.get(edu, edu) + '\uff0c\u6ee1\u8db3\u4e00\u7ea7\u5efa\u9020\u5e08\u6700\u4f4e\u5b66\u5386\u8981\u6c42')
        else:
            add('\u5b66\u5386\u5c42\u6b21', '\u4e0d\u7b26\u5408', '\u4e00\u7ea7\u5efa\u9020\u5e08\u8981\u6c42\u5de5\u7a0b\u7c7b\u6216\u5de5\u7a0b\u7ecf\u6d4e\u7c7b\u5927\u5b66\u4e13\u79d1\u53ca\u4ee5\u4e0a\uff0c\u5f53\u524d\u4e3a' + EDU_NAME.get(edu, edu))
    else:
        if rank >= EDU_RANK['zhongzhuan']:
            add('\u5b66\u5386\u5c42\u6b21', '\u7b26\u5408', EDU_NAME.get(edu, edu) + '\uff0c\u6ee1\u8db3\u4e8c\u7ea7\u5efa\u9020\u5e08\u6700\u4f4e\u5b66\u5386\u8981\u6c42')
        else:
            add('\u5b66\u5386\u5c42\u6b21', '\u4e0d\u7b26\u5408', '\u4e8c\u7ea7\u5efa\u9020\u5e08\u8981\u6c42\u4e2d\u7b49\u4e13\u79d1\u53ca\u4ee5\u4e0a\u5b66\u5386\uff0c\u5f53\u524d\u4e3a' + EDU_NAME.get(edu, edu))

    if args.major == 'relevant':
        add('\u4e13\u4e1a\u7c7b\u522b', '\u7b26\u5408', MAJOR_NAME['relevant'])
    elif args.major == 'near':
        add('\u4e13\u4e1a\u7c7b\u522b', '\u9700\u6838\u5b9e', '\u76f8\u8fd1\u4e13\u4e1a\u662f\u5426\u88ab\u8ba4\u53ef\u7531\u5404\u7701\u5f53\u5e74\u516c\u544a\u89c4\u5b9a\uff0c\u9700\u9010\u7701\u6838\u5bf9')
    else:
        add('\u4e13\u4e1a\u7c7b\u522b', '\u4e0d\u7b26\u5408', '\u5176\u4ed6\u4e13\u4e1a\u4e00\u822c\u4e0d\u7b26\u5408\u5de5\u7a0b\u7c7b\u6216\u5de5\u7a0b\u7ecf\u6d4e\u7c7b\u4e13\u4e1a\u8981\u6c42')

    my = args.manage_years
    wy = args.work_years
    if level == 'yiji':
        req = YIJI_REQ.get(edu)
        if req is None:
            add('\u65bd\u5de5\u7ba1\u7406\u5e74\u9650', '\u9700\u6838\u5b9e', '\u5f53\u524d\u5b66\u5386\u4e0d\u6ee1\u8db3\u4e00\u7ea7\u5efa\u9020\u5e08\u6700\u4f4e\u5b66\u5386\uff0c\u5e74\u9650\u53e3\u5f84\u4e0d\u518d\u9002\u7528')
        else:
            need_m, need_w = req
            if my is None:
                add('\u65bd\u5de5\u7ba1\u7406\u5e74\u9650', '\u9700\u6838\u5b9e', '\u672a\u586b\u5199\u4ece\u4e8b\u5efa\u8bbe\u5de5\u7a0b\u9879\u76ee\u65bd\u5de5\u7ba1\u7406\u5de5\u4f5c\u5e74\u9650')
            elif my >= need_m:
                add('\u65bd\u5de5\u7ba1\u7406\u5e74\u9650', '\u7b26\u5408', '\u65bd\u5de5\u7ba1\u7406 {} \u5e74\uff0c\u8981\u6c42\u6ee1 {} \u5e74'.format(my, need_m))
            else:
                add('\u65bd\u5de5\u7ba1\u7406\u5e74\u9650', '\u4e0d\u7b26\u5408', '\u65bd\u5de5\u7ba1\u7406 {} \u5e74\uff0c\u8981\u6c42\u6ee1 {} \u5e74\uff0c\u8fd8\u5dee {} \u5e74'.format(my, need_m, need_m - my))
            if wy is None:
                add('\u5de5\u4f5c\u5e74\u9650', '\u9700\u6838\u5b9e', '\u672a\u586b\u5199\u53c2\u52a0\u5de5\u4f5c\u603b\u5e74\u9650')
            elif wy >= need_w:
                add('\u5de5\u4f5c\u5e74\u9650', '\u7b26\u5408', '\u5de5\u4f5c {} \u5e74\uff0c\u53e3\u5f84\u8981\u6c42\u6ee1 {} \u5e74'.format(wy, need_w))
            else:
                add('\u5de5\u4f5c\u5e74\u9650', '\u9700\u6838\u5b9e', '\u5de5\u4f5c {} \u5e74\uff0c\u901a\u884c\u53e3\u5f84\u8981\u6c42\u6ee1 {} \u5e74\uff0c\u5404\u7701\u8868\u8ff0\u4e0d\u540c\u9700\u6838\u5bf9'.format(wy, need_w))
    else:
        if my is None:
            add('\u65bd\u5de5\u7ba1\u7406\u5e74\u9650', '\u9700\u6838\u5b9e', '\u672a\u586b\u5199\u4ece\u4e8b\u5efa\u8bbe\u5de5\u7a0b\u9879\u76ee\u65bd\u5de5\u7ba1\u7406\u5de5\u4f5c\u5e74\u9650')
        elif my >= ERJI_MANAGE:
            add('\u65bd\u5de5\u7ba1\u7406\u5e74\u9650', '\u7b26\u5408', '\u65bd\u5de5\u7ba1\u7406 {} \u5e74\uff0c\u901a\u884c\u53e3\u5f84\u8981\u6c42\u6ee1 {} \u5e74'.format(my, ERJI_MANAGE))
        else:
            add('\u65bd\u5de5\u7ba1\u7406\u5e74\u9650', '\u4e0d\u7b26\u5408', '\u65bd\u5de5\u7ba1\u7406 {} \u5e74\uff0c\u901a\u884c\u53e3\u5f84\u8981\u6c42\u6ee1 {} \u5e74\uff0c\u8fd8\u5dee {} \u5e74'.format(my, ERJI_MANAGE, ERJI_MANAGE - my))

    if level == 'yiji':
        if args.senior_title == 'yes' or args.manage_20 == 'yes':
            add('\u514d\u8bd5\u79d1\u76ee\u5224\u65ad', '\u9700\u6838\u5b9e',
                '\u7b26\u5408\u514d\u8bd5\u60c5\u5f62\u7684\uff0c\u53ef\u6309\u89c4\u5b9a\u7533\u8bf7\u514d\u8003\u300a\u5efa\u8bbe\u5de5\u7a0b\u7ecf\u6d4e\u300b\u4e0e\u300a\u5efa\u8bbe\u5de5\u7a0b\u9879\u76ee\u7ba1\u7406\u300b\uff0c'
                '\u4f46\u5fc5\u987b\u4e3b\u52a8\u63d0\u4ea4\u8bc1\u660e\u6750\u6599\u5e76\u901a\u8fc7\u5ba1\u6838\uff0c\u4e0d\u81ea\u52a8\u751f\u6548')
        else:
            add('\u514d\u8bd5\u79d1\u76ee\u5224\u65ad', '\u7b26\u5408', '\u672a\u7533\u62a5\u514d\u8bd5\uff0c\u6309\u5168\u90e8\u79d1\u76ee\u62a5\u8003')

    blocked = [i for i in items if i['result'] == '\u4e0d\u7b26\u5408']
    todo = [i for i in items if i['result'] == '\u9700\u6838\u5b9e']
    if blocked:
        verdict = '\u4e0d\u7b26\u5408\u62a5\u8003\u6761\u4ef6'
    elif todo:
        verdict = '\u9700\u8865\u5145\u6750\u6599\u6216\u6838\u5b9e\u540e\u786e\u8ba4'
    else:
        verdict = '\u7b26\u5408\u62a5\u8003\u6761\u4ef6\uff08\u901a\u884c\u53e3\u5f84\uff09'
    return {
        'mode': 'exam',
        'level': LEVEL_NAME.get(level, level),
        'items': items,
        'blocked': [i['name'] + '\uff1a' + i['detail'] for i in blocked],
        'todo': [i['name'] + '\uff1a' + i['detail'] for i in todo],
        'verdict': verdict,
    }


def check_reg(args):
    level = args.level
    as_of = parse_date(args.as_of) if args.as_of else date.today()
    items = []

    def add(name, ok, detail):
        items.append({'name': name, 'result': ok, 'detail': detail})

    reg = parse_date(args.reg_date) if args.reg_date else None
    if reg:
        expiry = add_year(reg, REG_VALID_YEARS)
        remain = (expiry - as_of).days
        renew_deadline = expiry - timedelta(days=RENEW_LEAD_DAYS)
        if remain < 0:
            add('\u6ce8\u518c\u6709\u6548\u671f', '\u4e0d\u7b26\u5408',
                '\u6ce8\u518c\u6709\u6548\u671f\u5df2\u4e8e {} \u5c4a\u6ee1\uff0c\u6ce8\u518c\u8bc1\u4e66\u5931\u6548\uff0c\u4e0d\u5f97\u4ee5\u6ce8\u518c\u5efa\u9020\u5e08\u540d\u4e49\u6267\u4e1a'.format(fmt(expiry)))
        elif remain <= RENEW_LEAD_DAYS:
            add('\u6ce8\u518c\u6709\u6548\u671f', '\u9700\u6838\u5b9e',
                '\u8ddd {} \u5c4a\u6ee1\u4ec5\u5269 {} \u5929\uff0c\u5df2\u8fc7\u5e94\u5728\u5c4a\u6ee1 30 \u65e5\u524d\u63d0\u51fa\u5ef6\u7eed\u7533\u8bf7\u7684\u7a97\u53e3'.format(fmt(expiry), remain))
        else:
            add('\u6ce8\u518c\u6709\u6548\u671f', '\u7b26\u5408',
                '\u6709\u6548\u671f\u81f3 {}\uff0c\u5269\u4f59 {} \u5929\uff1b\u5efa\u8bae\u6700\u8fdf {} \u524d\u63d0\u4ea4\u5ef6\u7eed\u6ce8\u518c\u7533\u8bf7'.format(fmt(expiry), remain, fmt(renew_deadline)))
        expiry_txt = fmt(expiry)
        renew_txt = fmt(renew_deadline)
        remain_txt = str(remain)
    else:
        add('\u6ce8\u518c\u6709\u6548\u671f', '\u9700\u6838\u5b9e', '\u672a\u586b\u5199\u6ce8\u518c\u8d77\u59cb\u65e5\u6216\u4e0a\u6b21\u5ef6\u7eed\u6ce8\u518c\u65e5')
        expiry_txt = ''
        renew_txt = ''
        remain_txt = ''

    hours = args.ce_hours
    if hours is None:
        add('\u7ee7\u7eed\u6559\u80b2', '\u9700\u6838\u5b9e', '\u672a\u586b\u5199\u672c\u6ce8\u518c\u6709\u6548\u671f\u5185\u5df2\u5b8c\u6210\u7684\u7ee7\u7eed\u6559\u80b2\u5b66\u65f6')
    elif hours >= CE_HOURS_REQUIRED:
        add('\u7ee7\u7eed\u6559\u80b2', '\u7b26\u5408',
            '\u5df2\u5b8c\u6210 {} \u5b66\u65f6\uff0c\u8fbe\u5230\u6bcf\u4e00\u6ce8\u518c\u6709\u6548\u671f\u4e0d\u5c11\u4e8e {} \u5b66\u65f6\u7684\u901a\u884c\u8981\u6c42'.format(hours, CE_HOURS_REQUIRED))
    else:
        add('\u7ee7\u7eed\u6559\u80b2', '\u4e0d\u7b26\u5408',
            '\u5df2\u5b8c\u6210 {} \u5b66\u65f6\uff0c\u8fd8\u5dee {} \u5b66\u65f6\uff1b\u672a\u8fbe\u5230\u7ee7\u7eed\u6559\u80b2\u8981\u6c42\u7684\u4e0d\u4e88\u6ce8\u518c\u6216\u4e0d\u4e88\u5ef6\u7eed'.format(hours, CE_HOURS_REQUIRED - hours))

    if args.age is None:
        add('\u5e74\u9f84\u6761\u4ef6', '\u9700\u6838\u5b9e', '\u672a\u586b\u5199\u5e74\u9f84')
    elif args.age > MAX_AGE:
        add('\u5e74\u9f84\u6761\u4ef6', '\u4e0d\u7b26\u5408', '\u5e74\u9f84 {} \u5468\u5c81\uff0c\u8d85\u8fc7 65 \u5468\u5c81\u4e0d\u4e88\u6ce8\u518c'.format(args.age))
    else:
        add('\u5e74\u9f84\u6761\u4ef6', '\u7b26\u5408', '\u5e74\u9f84 {} \u5468\u5c81\uff0c\u672a\u8d85\u8fc7 65 \u5468\u5c81'.format(args.age))

    units = args.units or 1
    if units >= 2:
        add('\u8058\u7528\u5355\u4f4d', '\u4e0d\u7b26\u5408', '\u7533\u8bf7\u5728\u4e24\u4e2a\u53ca\u4ee5\u4e0a\u5355\u4f4d\u6ce8\u518c\u5c5e\u4e8e\u4e0d\u4e88\u6ce8\u518c\u60c5\u5f62')
    else:
        add('\u8058\u7528\u5355\u4f4d', '\u7b26\u5408', '\u53d7\u8058\u4e8e 1 \u4e2a\u5355\u4f4d\uff0c\u9700\u63d0\u4f9b\u52b3\u52a8\u5408\u540c\u4e0e\u8058\u7528\u5173\u7cfb\u8bc1\u660e')

    if args.accident == 'yes':
        add('\u8d28\u91cf\u5b89\u5168\u4e8b\u6545', '\u4e0d\u7b26\u5408',
            '\u7533\u8bf7\u4e4b\u65e5\u524d 3 \u5e74\u5185\u62c5\u4efb\u9879\u76ee\u8d1f\u8d23\u4eba\u671f\u95f4\u9879\u76ee\u53d1\u751f\u8fc7\u91cd\u5927\u8d28\u91cf\u5b89\u5168\u4e8b\u6545\uff0c\u5c5e\u4e8e\u4e0d\u4e88\u6ce8\u518c\u60c5\u5f62')
    else:
        add('\u8d28\u91cf\u5b89\u5168\u4e8b\u6545', '\u7b26\u5408', '\u8fd1 3 \u5e74\u62c5\u4efb\u9879\u76ee\u8d1f\u8d23\u4eba\u671f\u95f4\u65e0\u91cd\u5927\u8d28\u91cf\u5b89\u5168\u4e8b\u6545\u8bb0\u5f55')

    if args.criminal == 'yes':
        add('\u5211\u4e8b\u5904\u7f5a', '\u4e0d\u7b26\u5408', '\u56e0\u6267\u4e1a\u6d3b\u52a8\u53d7\u5211\u4e8b\u5904\u7f5a\u4e14\u672a\u6ee1\u89c4\u5b9a\u5e74\u9650\uff0c\u5c5e\u4e8e\u4e0d\u4e88\u6ce8\u518c\u60c5\u5f62')
    else:
        add('\u5211\u4e8b\u5904\u7f5a', '\u7b26\u5408', '\u65e0\u76f8\u5173\u5211\u4e8b\u5904\u7f5a\u672a\u671f\u6ee1\u8bb0\u5f55')

    if args.revoked == 'yes':
        add('\u540a\u9500\u6ce8\u518c\u8bc1\u4e66', '\u4e0d\u7b26\u5408', '\u88ab\u540a\u9500\u6ce8\u518c\u8bc1\u4e66\u4e14\u81ea\u5904\u7f5a\u51b3\u5b9a\u4e4b\u65e5\u8d77\u672a\u6ee1 2 \u5e74\uff0c\u4e0d\u4e88\u6ce8\u518c')
    else:
        add('\u540a\u9500\u6ce8\u518c\u8bc1\u4e66', '\u7b26\u5408', '\u65e0\u540a\u9500\u6ce8\u518c\u8bc1\u4e66\u672a\u671f\u6ee1\u8bb0\u5f55')

    blocked = [i for i in items if i['result'] == '\u4e0d\u7b26\u5408']
    todo = [i for i in items if i['result'] == '\u9700\u6838\u5b9e']
    if blocked:
        verdict = '\u5b58\u5728\u4e0d\u4e88\u6ce8\u518c\u60c5\u5f62\uff0c\u4e0d\u80fd\u529e\u7406'
    elif todo:
        verdict = '\u9700\u8865\u5145\u6750\u6599\u6216\u6838\u5b9e\u540e\u786e\u8ba4'
    else:
        verdict = '\u672a\u53d1\u73b0\u4e0d\u4e88\u6ce8\u518c\u60c5\u5f62\uff0c\u53ef\u53d7\u7406'
    return {
        'mode': 'reg',
        'level': LEVEL_NAME.get(level, level),
        'expiry': expiry_txt,
        'renew_deadline': renew_txt,
        'remain_days': remain_txt,
        'ce_required': CE_HOURS_REQUIRED,
        'ce_done': args.ce_hours,
        'items': items,
        'blocked': [i['name'] + '\uff1a' + i['detail'] for i in blocked],
        'todo': [i['name'] + '\uff1a' + i['detail'] for i in todo],
        'verdict': verdict,
    }


def render_md(r):
    out = []
    out.append('# \u5efa\u9020\u5e08\u6838\u67e5\u7ed3\u679c\uff08{})'.format(r['level']))
    out.append('')
    out.append('- \u6838\u67e5\u6a21\u5f0f\uff1a{}'.format('\u62a5\u8003\u6761\u4ef6\u6838\u67e5' if r['mode'] == 'exam' else '\u6ce8\u518c\u4e0e\u7ee7\u7eed\u6559\u80b2\u6838\u67e5'))
    if r['mode'] == 'reg':
        if r['expiry']:
            out.append('- \u6ce8\u518c\u6709\u6548\u671f\u81f3\uff1a{}'.format(r['expiry']))
            out.append('- \u5efa\u8bae\u5ef6\u7eed\u7533\u8bf7\u622a\u6b62\uff1a{}'.format(r['renew_deadline']))
            out.append('- \u5269\u4f59\u5929\u6570\uff1a{} \u5929'.format(r['remain_days']))
        out.append('- \u7ee7\u7eed\u6559\u80b2\u5b66\u65f6\uff1a\u5df2\u5b8c\u6210 {} / \u8981\u6c42 {}'.format(r['ce_done'], r['ce_required']))
    out.append('- \u7ed3\u8bba\uff1a{}'.format(r['verdict']))
    out.append('')
    out.append('| \u6838\u67e5\u9879 | \u7ed3\u679c | \u8bf4\u660e |')
    out.append('|---|---|---|')
    for i in r['items']:
        out.append('| {} | {} | {} |'.format(i['name'], i['result'], i['detail']))
    out.append('')
    if r['blocked']:
        out.append('## \u4e0d\u7b26\u5408\u9879')
        out.append('')
        for b in r['blocked']:
            out.append('- {}'.format(b))
        out.append('')
    if r['todo']:
        out.append('## \u9700\u8865\u5145\u6216\u6838\u5b9e\u9879')
        out.append('')
        for t in r['todo']:
            out.append('- {}'.format(t))
        out.append('')
    out.append('## \u63d0\u9192')
    out.append('')
    out.append('1. \u62a5\u8003\u6761\u4ef6\u3001\u514d\u8bd5\u79d1\u76ee\u3001\u5408\u683c\u6807\u51c6\u4e0e\u62a5\u540d\u65f6\u95f4\u4ee5\u6240\u5728\u7701\u4efd\u5f53\u5e74\u8003\u52a1\u516c\u544a\u4e3a\u51c6\uff0c\u672c\u811a\u672c\u53ea\u505a\u901a\u884c\u53e3\u5f84\u6838\u67e5\u3002')
    out.append('2. \u5de5\u4f5c\u5e74\u9650\u4e0d\u7b49\u4e8e\u65bd\u5de5\u7ba1\u7406\u5de5\u4f5c\u5e74\u9650\uff0c\u5361\u7684\u662f\u540e\u8005\u3002')
    out.append('3. \u4e8c\u7ea7\u5efa\u9020\u5e08\u5404\u7701\u81ea\u884c\u547d\u9898\u5e76\u7ec4\u7ec7\uff0c\u5408\u683c\u6807\u51c6\u4e0e\u6267\u4e1a\u5730\u57df\u8303\u56f4\u7531\u5404\u7701\u89c4\u5b9a\uff0c\u8de8\u7701\u4e00\u822c\u4e0d\u901a\u7528\u3002')
    out.append('4. \u7ee7\u7eed\u6559\u80b2\u662f\u5ef6\u7eed\u6ce8\u518c\u7684\u524d\u7f6e\u6761\u4ef6\uff0c\u5b66\u65f6\u4e0d\u591f\u5ef6\u7eed\u529e\u4e0d\u4e0b\u6765\u3002')
    out.append('5. \u5728\u4e24\u4e2a\u5355\u4f4d\u6ce8\u518c\u3001\u7ee7\u7eed\u6559\u80b2\u672a\u8fbe\u6807\u3001\u5e74\u9f84\u8d85 65 \u5468\u5c81\u5747\u4e3a\u4e0d\u4e88\u6ce8\u518c\u60c5\u5f62\uff0c\u4e0d\u662f\u8865\u6750\u6599\u5c31\u80fd\u89e3\u51b3\u3002')
    out.append('')
    return '\n'.join(out)


def selftest():
    errors = []

    def eq(name, got, want):
        if got != want:
            errors.append('%s: got=%r want=%r' % (name, got, want))

    class A(object):
        pass

    def mk_exam(**kw):
        a = A()
        a.level = kw.get('level', 'yiji')
        a.education = kw.get('education', 'zhuanke')
        a.major = kw.get('major', 'relevant')
        a.work_years = kw.get('work_years', 8)
        a.manage_years = kw.get('manage_years', 4)
        a.senior_title = kw.get('senior_title', 'no')
        a.manage_20 = kw.get('manage_20', 'no')
        return a

    def mk_reg(**kw):
        a = A()
        a.level = kw.get('level', 'yiji')
        a.reg_date = kw.get('reg_date', '2024-06-01')
        a.ce_hours = kw.get('ce_hours', 120)
        a.age = kw.get('age', 42)
        a.units = kw.get('units', 1)
        a.accident = kw.get('accident', 'no')
        a.criminal = kw.get('criminal', 'no')
        a.revoked = kw.get('revoked', 'no')
        a.as_of = kw.get('as_of', '2026-10-08')
        return a

    r1 = check_exam(mk_exam())
    eq('case1 \u4e00\u7ea7\u5927\u4e13\u7b26\u5408', r1['verdict'], '\u7b26\u5408\u62a5\u8003\u6761\u4ef6\uff08\u901a\u884c\u53e3\u5f84\uff09')

    r2 = check_exam(mk_exam(manage_years=3))
    eq('case2 \u4e00\u7ea7\u65bd\u5de5\u7ba1\u7406\u5e74\u9650\u4e0d\u8db3', r2['verdict'], '\u4e0d\u7b26\u5408\u62a5\u8003\u6761\u4ef6')

    r3 = check_exam(mk_exam(education='zhongzhuan'))
    eq('case3 \u4e00\u7ea7\u4e2d\u4e13\u5b66\u5386\u4e0d\u8db3', r3['verdict'], '\u4e0d\u7b26\u5408\u62a5\u8003\u6761\u4ef6')

    r4 = check_exam(mk_exam(level='erji', education='zhongzhuan', manage_years=2))
    eq('case4 \u4e8c\u7ea7\u4e2d\u4e13\u6ee12\u5e74\u7b26\u5408', r4['verdict'], '\u7b26\u5408\u62a5\u8003\u6761\u4ef6\uff08\u901a\u884c\u53e3\u5f84\uff09')

    r5 = check_exam(mk_exam(level='erji', education='zhongzhuan', manage_years=1))
    eq('case5 \u4e8c\u7ea7\u5e74\u9650\u4e0d\u8db3', r5['verdict'], '\u4e0d\u7b26\u5408\u62a5\u8003\u6761\u4ef6')

    r6 = check_exam(mk_exam(major='near'))
    eq('case6 \u76f8\u8fd1\u4e13\u4e1a\u9700\u6838\u5b9e', r6['verdict'], '\u9700\u8865\u5145\u6750\u6599\u6216\u6838\u5b9e\u540e\u786e\u8ba4')

    r7 = check_exam(mk_exam(major='other'))
    eq('case7 \u5176\u4ed6\u4e13\u4e1a\u4e0d\u7b26\u5408', r7['verdict'], '\u4e0d\u7b26\u5408\u62a5\u8003\u6761\u4ef6')

    r8 = check_exam(mk_exam(senior_title='yes'))
    eq('case8 \u9ad8\u7ea7\u804c\u79f0\u514d\u8bd5\u9700\u6838\u5b9e', r8['verdict'], '\u9700\u8865\u5145\u6750\u6599\u6216\u6838\u5b9e\u540e\u786e\u8ba4')

    r9 = check_exam(mk_exam(level='yiji', education='boshi', manage_years=1, work_years=1))
    eq('case9 \u535a\u58eb\u6ee11\u5e74\u7b26\u5408', r9['verdict'], '\u7b26\u5408\u62a5\u8003\u6761\u4ef6\uff08\u901a\u884c\u53e3\u5f84\uff09')

    s1 = check_reg(mk_reg())
    eq('case10 \u6ce8\u518c\u6b63\u5e38', s1['verdict'], '\u672a\u53d1\u73b0\u4e0d\u4e88\u6ce8\u518c\u60c5\u5f62\uff0c\u53ef\u53d7\u7406')
    eq('case10 \u5230\u671f\u65e5', s1['expiry'], '2027-06-01')
    eq('case10 \u5efa\u8bae\u5ef6\u7eed\u622a\u6b62', s1['renew_deadline'], '2027-05-02')

    s2 = check_reg(mk_reg(ce_hours=80))
    eq('case11 \u7ee7\u7eed\u6559\u80b2\u5b66\u65f6\u4e0d\u8db3\u4e0d\u4e88\u6ce8\u518c', s2['verdict'], '\u5b58\u5728\u4e0d\u4e88\u6ce8\u518c\u60c5\u5f62\uff0c\u4e0d\u80fd\u529e\u7406')

    s3 = check_reg(mk_reg(age=66))
    eq('case12 \u5e74\u9f84\u8d8565', s3['verdict'], '\u5b58\u5728\u4e0d\u4e88\u6ce8\u518c\u60c5\u5f62\uff0c\u4e0d\u80fd\u529e\u7406')

    s4 = check_reg(mk_reg(units=2))
    eq('case13 \u4e24\u4e2a\u5355\u4f4d\u6ce8\u518c', s4['verdict'], '\u5b58\u5728\u4e0d\u4e88\u6ce8\u518c\u60c5\u5f62\uff0c\u4e0d\u80fd\u529e\u7406')

    s5 = check_reg(mk_reg(accident='yes'))
    eq('case14 \u91cd\u5927\u4e8b\u6545', s5['verdict'], '\u5b58\u5728\u4e0d\u4e88\u6ce8\u518c\u60c5\u5f62\uff0c\u4e0d\u80fd\u529e\u7406')

    s6 = check_reg(mk_reg(reg_date='2022-01-01'))
    eq('case15 \u6ce8\u518c\u5df2\u5931\u6548', s6['verdict'], '\u5b58\u5728\u4e0d\u4e88\u6ce8\u518c\u60c5\u5f62\uff0c\u4e0d\u80fd\u529e\u7406')

    s7 = check_reg(mk_reg(reg_date='2023-10-15'))
    eq('case16 \u4e34\u8fd1\u5230\u671f\u9700\u6838\u5b9e', s7['verdict'], '\u9700\u8865\u5145\u6750\u6599\u6216\u6838\u5b9e\u540e\u786e\u8ba4')
    eq('case16 \u5269\u4f59\u5929\u6570', s7['remain_days'], '7')

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 16\n\u8986\u76d6: \u4e00\u7ea7/\u4e8c\u7ea7\u5b66\u5386\u4e0e\u5e74\u9650/\u4e13\u4e1a\u7c7b\u522b/\u514d\u8bd5\u5224\u65ad/'
               '\u6ce8\u518c\u6709\u6548\u671f/\u7ee7\u7eed\u6559\u80b2\u5b66\u65f6/\u5e74\u9f84/\u591a\u5355\u4f4d\u6ce8\u518c/\u4e8b\u6545\u4e0e\u5904\u7f5a/\u5230\u671f\u5931\u6548')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u5efa\u9020\u5e08\u62a5\u8003\u6761\u4ef6\u6838\u67e5\u4e0e\u6ce8\u518c\u7ee7\u7eed\u6559\u80b2\u6d4b\u7b97')
    ap.add_argument('--mode', default='exam', choices=['exam', 'reg'])
    ap.add_argument('--level', default='yiji', choices=['yiji', 'erji'])
    ap.add_argument('--education', default='zhuanke',
                    choices=['chuzhong', 'zhongzhuan', 'zhuanke', 'benke', 'shuoshi', 'boshi'])
    ap.add_argument('--major', default='relevant', choices=['relevant', 'near', 'other'])
    ap.add_argument('--work-years', dest='work_years', type=float)
    ap.add_argument('--manage-years', dest='manage_years', type=float)
    ap.add_argument('--senior-title', dest='senior_title', default='no', choices=['yes', 'no'])
    ap.add_argument('--manage-20', dest='manage_20', default='no', choices=['yes', 'no'])
    ap.add_argument('--reg-date', dest='reg_date', help='\u6ce8\u518c\u8d77\u59cb\u65e5\u6216\u4e0a\u6b21\u5ef6\u7eed\u6ce8\u518c\u65e5 YYYY-MM-DD')
    ap.add_argument('--ce-hours', dest='ce_hours', type=int, help='\u672c\u6ce8\u518c\u6709\u6548\u671f\u5185\u5df2\u5b8c\u6210\u7ee7\u7eed\u6559\u80b2\u5b66\u65f6')
    ap.add_argument('--age', type=int, help='\u7533\u8bf7\u4eba\u5e74\u9f84')
    ap.add_argument('--units', type=int, default=1, help='\u540c\u65f6\u53d7\u8058\uff08\u7533\u8bf7\u6ce8\u518c\uff09\u7684\u5355\u4f4d\u6570')
    ap.add_argument('--accident', default='no', choices=['yes', 'no'])
    ap.add_argument('--criminal', default='no', choices=['yes', 'no'])
    ap.add_argument('--revoked', default='no', choices=['yes', 'no'])
    ap.add_argument('--as-of', dest='as_of', help='\u6838\u67e5\u57fa\u51c6\u65e5\uff0c\u9ed8\u8ba4\u4eca\u5929')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'])
    ap.add_argument('--selftest', action='store_true', help='\u8fd0\u884c\u5185\u7f6e\u81ea\u68c0')
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    r = check_exam(args) if args.mode == 'exam' else check_reg(args)
    out = render_md(r) if args.format == 'md' else json.dumps(r, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % args.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
