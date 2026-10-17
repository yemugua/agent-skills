#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u98df\u54c1\u7ecf\u8425\u8bb8\u53ef\u7533\u529e\u6750\u6599\u6838\u67e5\u3001\u73b0\u573a\u6838\u67e5\u9884\u68c0\u4e0e\u6709\u6548\u671f\u5ef6\u7eed\u6d4b\u7b97\u3002

\u7528\u6cd5:
  python food_permit_check.py --mode apply --business-type catering --staff 8 --health-certs 8 \
      --manager yes --license-biz yes --address-match yes --layout yes --rules yes \
      --facility pest,cold,disinfection,separate,handwash
  python food_permit_check.py --mode apply --business-type special --staff 2 --health-certs 1 \
      --manager no --license-biz yes --address-match no --layout no --rules no --facility pest
  python food_permit_check.py --mode renew --permit-date 2022-03-01 --as-of 2026-10-08
  python food_permit_check.py --selftest

\u53c2\u6570:
  --mode            apply \u7533\u529e\u6838\u67e5 / renew \u5ef6\u7eed\u4e0e\u53d8\u66f4\u6838\u67e5
  --business-type   prepackaged \u9884\u5305\u88c5\u98df\u54c1\u9500\u552e / bulk \u6563\u88c5\u98df\u54c1\u9500\u552e / special \u7279\u6b8a\u98df\u54c1\u9500\u552e /
                    catering \u9910\u996e\u670d\u52a1 / canteen \u5355\u4f4d\u98df\u5802 / online \u7f51\u7edc\u9910\u996e
  --staff           \u4ece\u4e1a\u4eba\u5458\u6570
  --health-certs    \u5df2\u53d6\u5f97\u5065\u5eb7\u8bc1\u660e\u7684\u4eba\u5458\u6570
  --manager         yes/no \u662f\u5426\u914d\u5907\u98df\u54c1\u5b89\u5168\u7ba1\u7406\u4eba\u5458
  --license-biz     yes/no \u662f\u5426\u5df2\u53d6\u5f97\u8425\u4e1a\u6267\u7167
  --address-match   yes/no \u8425\u4e1a\u6267\u7167\u3001\u573a\u6240\u4f7f\u7528\u8bc1\u660e\u3001\u7533\u8bf7\u4e66\u4e09\u5904\u5730\u5740\u662f\u5426\u4e00\u81f4
  --layout          yes/no \u662f\u5426\u5df2\u7ed8\u5236\u7ecf\u8425\u573a\u6240\u5e03\u5c40\u56fe\u4e0e\u64cd\u4f5c\u6d41\u7a0b\u6587\u4ef6
  --rules           yes/no \u662f\u5426\u5df2\u5236\u5b9a\u98df\u54c1\u5b89\u5168\u89c4\u7ae0\u5236\u5ea6
  --facility        \u5df2\u5177\u5907\u7684\u8bbe\u65bd\uff0c\u9017\u53f7\u5206\u9694\uff1apest \u4e09\u9632 / cold \u51b7\u85cf\u51b7\u51bb / disinfection \u6e05\u6d17\u6d88\u6bd2 /
                    handwash \u66f4\u8863\u6d17\u624b / separate \u751f\u719f\u5206\u5f00 / counter \u7279\u6b8a\u98df\u54c1\u4e13\u533a\u4e13\u67dc
  --cold-food       yes/no \u662f\u5426\u7ecf\u8425\u51b7\u85cf\u51b7\u51bb\u98df\u54c1
  --online          yes/no \u662f\u5426\u901a\u8fc7\u7f51\u7edc\u7ecf\u8425
  --permit-date     \u8bb8\u53ef\u8bc1\u53d1\u8bc1\u65e5\u671f YYYY-MM-DD
  --relocated       yes/no \u7ecf\u8425\u573a\u6240\u662f\u5426\u5df2\u642c\u8fc1
  --changed         yes/no \u540d\u79f0\u3001\u6cd5\u5b9a\u4ee3\u8868\u4eba\u3001\u7ecf\u8425\u9879\u76ee\u7b49\u662f\u5426\u53d1\u751f\u53d8\u5316
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

TYPE_NAME = {
    'prepackaged': '\u9884\u5305\u88c5\u98df\u54c1\u9500\u552e',
    'bulk': '\u6563\u88c5\u98df\u54c1\u9500\u552e',
    'special': '\u7279\u6b8a\u98df\u54c1\u9500\u552e',
    'catering': '\u9910\u996e\u670d\u52a1',
    'canteen': '\u5355\u4f4d\u98df\u5802',
    'online': '\u7f51\u7edc\u9910\u996e',
}
FACILITY_NAME = {
    'pest': '\u4e09\u9632\u8bbe\u65bd\uff08\u9632\u8747\u9632\u9f20\u9632\u866b\uff09',
    'cold': '\u51b7\u85cf\u51b7\u51bb\u8bbe\u65bd',
    'disinfection': '\u6e05\u6d17\u6d88\u6bd2\u8bbe\u65bd',
    'handwash': '\u66f4\u8863\u4e0e\u6d17\u624b\u8bbe\u65bd',
    'separate': '\u751f\u719f\u5206\u5f00\u8bbe\u65bd\uff08\u5bb9\u5668\u3001\u5200\u5177\u3001\u7827\u677f\u5206\u5f00\uff09',
    'counter': '\u7279\u6b8a\u98df\u54c1\u4e13\u533a\u6216\u4e13\u67dc',
}
REQUIRED_FACILITY = {
    'prepackaged': ['pest'],
    'bulk': ['pest'],
    'special': ['pest', 'counter'],
    'catering': ['pest', 'cold', 'disinfection', 'handwash', 'separate'],
    'canteen': ['pest', 'cold', 'disinfection', 'handwash', 'separate'],
    'online': ['pest', 'cold', 'disinfection', 'handwash', 'separate'],
}
VALID_YEARS = 5
RENEW_BUSINESS_DAYS = 30


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


def minus_business_days(d, n):
    """\u5411\u524d\u63a8 n \u4e2a\u5de5\u4f5c\u65e5\uff08\u4ec5\u6263\u9664\u5468\u672b\uff0c\u4e0d\u6263\u6cd5\u5b9a\u8282\u5047\u65e5\uff09\u3002"""
    cur = d
    cnt = 0
    while cnt < n:
        cur = cur - timedelta(days=1)
        if cur.weekday() < 5:
            cnt += 1
    return cur


def check_apply(args):
    btype = args.business_type
    items = []

    def add(name, ok, detail):
        items.append({'name': name, 'result': ok, 'detail': detail})

    add('\u4e3b\u4f53\u4e1a\u6001', '\u7b26\u5408', TYPE_NAME.get(btype, btype) + '\uff0c\u7ecf\u8425\u9879\u76ee\u5e94\u6309\u5b9e\u9645\u7ecf\u8425\u52fe\u5168\uff0c\u4e0d\u5f97\u8d85\u8303\u56f4\u7ecf\u8425')

    if args.license_biz == 'yes':
        add('\u8425\u4e1a\u6267\u7167', '\u7b26\u5408', '\u5df2\u53d6\u5f97\u8425\u4e1a\u6267\u7167\u7b49\u4e3b\u4f53\u8d44\u683c\u8bc1\u660e')
    else:
        add('\u8425\u4e1a\u6267\u7167', '\u4e0d\u7b26\u5408', '\u672a\u53d6\u5f97\u8425\u4e1a\u6267\u7167\uff0c\u5e94\u5148\u529e\u7406\u4e3b\u4f53\u8d44\u683c\u767b\u8bb0\u518d\u7533\u8bf7\u98df\u54c1\u7ecf\u8425\u8bb8\u53ef')

    if args.address_match == 'yes':
        add('\u573a\u6240\u4f7f\u7528\u8bc1\u660e', '\u7b26\u5408', '\u8425\u4e1a\u6267\u7167\u3001\u573a\u6240\u4f7f\u7528\u8bc1\u660e\u3001\u7533\u8bf7\u4e66\u4e09\u5904\u5730\u5740\u4e00\u81f4')
    else:
        add('\u573a\u6240\u4f7f\u7528\u8bc1\u660e', '\u4e0d\u7b26\u5408', '\u4e09\u5904\u5730\u5740\u4e0d\u4e00\u81f4\u662f\u6750\u6599\u88ab\u9000\u56de\u7684\u7b2c\u4e00\u539f\u56e0\uff0c\u9700\u5148\u7edf\u4e00')

    if args.layout == 'yes':
        add('\u5e03\u5c40\u56fe\u4e0e\u6d41\u7a0b\u6587\u4ef6', '\u7b26\u5408', '\u5df2\u7ed8\u5236\u7ecf\u8425\u573a\u6240\u5e03\u5c40\u56fe\u4e0e\u64cd\u4f5c\u6d41\u7a0b\u6587\u4ef6')
    else:
        add('\u5e03\u5c40\u56fe\u4e0e\u6d41\u7a0b\u6587\u4ef6', '\u9700\u8865\u5145', '\u7f3a\u5c11\u5e03\u5c40\u56fe\u4e0e\u64cd\u4f5c\u6d41\u7a0b\u6587\u4ef6\uff0c\u5e94\u6807\u6ce8\u529f\u80fd\u533a\u3001\u8bbe\u5907\u4f4d\u7f6e\u4e0e\u6d41\u5411')

    if args.rules == 'yes':
        add('\u98df\u54c1\u5b89\u5168\u89c4\u7ae0\u5236\u5ea6', '\u7b26\u5408', '\u5df2\u5236\u5b9a\u98df\u54c1\u5b89\u5168\u89c4\u7ae0\u5236\u5ea6')
    else:
        add('\u98df\u54c1\u5b89\u5168\u89c4\u7ae0\u5236\u5ea6', '\u9700\u8865\u5145', '\u7f3a\u5c11\u98df\u54c1\u5b89\u5168\u81ea\u67e5\u3001\u4ece\u4e1a\u4eba\u5458\u5065\u5eb7\u7ba1\u7406\u3001\u8fdb\u8d27\u67e5\u9a8c\u8bb0\u5f55\u7b49\u89c4\u7ae0\u5236\u5ea6')

    if args.manager == 'yes':
        add('\u98df\u54c1\u5b89\u5168\u7ba1\u7406\u4eba\u5458', '\u7b26\u5408', '\u5df2\u914d\u5907\u98df\u54c1\u5b89\u5168\u7ba1\u7406\u4eba\u5458')
    else:
        add('\u98df\u54c1\u5b89\u5168\u7ba1\u7406\u4eba\u5458', '\u4e0d\u7b26\u5408', '\u672a\u914d\u5907\u98df\u54c1\u5b89\u5168\u7ba1\u7406\u4eba\u5458\u5c5e\u4e8e\u4e0d\u4e88\u8bb8\u53ef\u60c5\u5f62')

    staff = args.staff
    certs = args.health_certs
    if staff is None or certs is None:
        add('\u4ece\u4e1a\u4eba\u5458\u5065\u5eb7\u8bc1\u660e', '\u9700\u8865\u5145', '\u672a\u586b\u5199\u4ece\u4e1a\u4eba\u5458\u6570\u6216\u5065\u5eb7\u8bc1\u660e\u4eba\u6570')
    elif certs >= staff:
        add('\u4ece\u4e1a\u4eba\u5458\u5065\u5eb7\u8bc1\u660e', '\u7b26\u5408', '\u4ece\u4e1a\u4eba\u5458 {} \u4eba\uff0c\u5065\u5eb7\u8bc1\u660e {} \u4efd\uff0c\u5df2\u8986\u76d6'.format(staff, certs))
    else:
        add('\u4ece\u4e1a\u4eba\u5458\u5065\u5eb7\u8bc1\u660e', '\u4e0d\u7b26\u5408',
            '\u4ece\u4e1a\u4eba\u5458 {} \u4eba\uff0c\u5065\u5eb7\u8bc1\u660e\u4ec5 {} \u4efd\uff0c\u8fd8\u5dee {} \u4efd\uff1b\u63a5\u89e6\u76f4\u63a5\u5165\u53e3\u98df\u54c1\u5c97\u4f4d\u5fc5\u987b\u5168\u5458\u6301\u8bc1'.format(
                staff, certs, staff - certs))

    need = list(REQUIRED_FACILITY.get(btype, ['pest']))
    if args.cold_food == 'yes' and 'cold' not in need:
        need.append('cold')
    have = [x.strip() for x in (args.facility or '').split(',') if x.strip()]
    missing_f = [f for f in need if f not in have]
    if not missing_f:
        add('\u8bbe\u65bd\u8bbe\u5907', '\u7b26\u5408', '\u5df2\u5177\u5907\uff1a' + '\u3001'.join(FACILITY_NAME.get(f, f) for f in need))
    else:
        add('\u8bbe\u65bd\u8bbe\u5907', '\u4e0d\u7b26\u5408',
            '\u672c\u4e1a\u6001\u5fc5\u9700\u4f46\u7f3a\u5931\uff1a' + '\u3001'.join(FACILITY_NAME.get(f, f) for f in missing_f))

    if btype == 'special':
        add('\u7279\u6b8a\u98df\u54c1\u4e13\u533a\u4e13\u67dc', '\u7b26\u5408' if 'counter' in have else '\u4e0d\u7b26\u5408',
            '\u7279\u6b8a\u98df\u54c1\u5e94\u4e13\u533a\u6216\u4e13\u67dc\u9500\u552e\u5e76\u8bbe\u7f6e\u663e\u8457\u63d0\u793a\uff0c\u4e0e\u666e\u901a\u98df\u54c1\u6df7\u653e\u662f\u9ad8\u9891\u5904\u7f5a\u70b9')

    if args.online == 'yes':
        add('\u7f51\u7edc\u7ecf\u8425', '\u9700\u8865\u5145',
            '\u901a\u8fc7\u7f51\u7edc\u7ecf\u8425\u7684\u5e94\u6309\u5c5e\u5730\u8981\u6c42\u586b\u62a5\u5e76\u516c\u793a\u771f\u5b9e\u8bb8\u53ef\u4fe1\u606f\uff0c\u5165\u7f51\u4fe1\u606f\u53d8\u66f4\u987b\u53ca\u65f6\u66f4\u65b0')
    else:
        add('\u7f51\u7edc\u7ecf\u8425', '\u7b26\u5408', '\u4e0d\u6d89\u53ca\u7f51\u7edc\u7ecf\u8425')

    blocked = [i for i in items if i['result'] == '\u4e0d\u7b26\u5408']
    todo = [i for i in items if i['result'] == '\u9700\u8865\u5145']
    if blocked:
        verdict = '\u5b58\u5728\u4e0d\u4e88\u8bb8\u53ef\u60c5\u5f62\uff0c\u4e0d\u80fd\u63d0\u4ea4'
    elif todo:
        verdict = '\u9700\u8865\u5145\u6750\u6599\u540e\u63d0\u4ea4'
    else:
        verdict = '\u6750\u6599\u4e0e\u573a\u6240\u6761\u4ef6\u57fa\u672c\u5177\u5907\uff0c\u53ef\u63d0\u4ea4\u7533\u8bf7'
    return {
        'mode': 'apply',
        'business_type': TYPE_NAME.get(btype, btype),
        'items': items,
        'blocked': [i['name'] + '\uff1a' + i['detail'] for i in blocked],
        'todo': [i['name'] + '\uff1a' + i['detail'] for i in todo],
        'verdict': verdict,
    }


def check_renew(args):
    as_of = parse_date(args.as_of) if args.as_of else date.today()
    items = []

    def add(name, ok, detail):
        items.append({'name': name, 'result': ok, 'detail': detail})

    reg = parse_date(args.permit_date) if args.permit_date else None
    expiry = ''
    deadline = ''
    remain = ''
    if reg:
        exp = add_year(reg, VALID_YEARS)
        dl = minus_business_days(exp, RENEW_BUSINESS_DAYS)
        rm = (exp - as_of).days
        expiry, deadline, remain = fmt(exp), fmt(dl), str(rm)
        if rm < 0:
            add('\u8bb8\u53ef\u8bc1\u6709\u6548\u671f', '\u4e0d\u7b26\u5408',
                '\u6709\u6548\u671f\u5df2\u4e8e {} \u5c4a\u6ee1\uff0c\u5c4a\u6ee1\u672a\u5ef6\u7eed\u4ecd\u7ee7\u7eed\u7ecf\u8425\u7684\u6309\u65e0\u8bc1\u7ecf\u8425\u5904\u7406'.format(expiry))
        elif as_of >= dl:
            add('\u8bb8\u53ef\u8bc1\u6709\u6548\u671f', '\u9700\u8865\u5145',
                '\u6709\u6548\u671f\u81f3 {}\uff0c\u5df2\u8d85\u8fc7\u5e94\u5728\u5c4a\u6ee1 30 \u4e2a\u5de5\u4f5c\u65e5\u524d\u63d0\u51fa\u5ef6\u7eed\u7533\u8bf7\u7684\u65f6\u70b9\uff08\u6700\u8fdf {}\uff09'.format(expiry, deadline))
        else:
            add('\u8bb8\u53ef\u8bc1\u6709\u6548\u671f', '\u7b26\u5408',
                '\u6709\u6548\u671f\u81f3 {}\uff0c\u5269\u4f59 {} \u5929\uff1b\u6700\u8fdf\u5e94\u5728 {} \u524d\u63d0\u51fa\u5ef6\u7eed\u7533\u8bf7'.format(expiry, remain, deadline))
    else:
        add('\u8bb8\u53ef\u8bc1\u6709\u6548\u671f', '\u9700\u8865\u5145', '\u672a\u586b\u5199\u53d1\u8bc1\u65e5\u671f')

    if args.relocated == 'yes':
        add('\u7ecf\u8425\u573a\u6240\u53d8\u5316', '\u4e0d\u7b26\u5408', '\u7ecf\u8425\u573a\u6240\u53d1\u751f\u53d8\u5316\u7684\u4e00\u822c\u5e94\u91cd\u65b0\u7533\u8bf7\u8bb8\u53ef\uff0c\u4e0d\u80fd\u6309\u5ef6\u7eed\u6216\u53d8\u66f4\u529e\u7406')
    else:
        add('\u7ecf\u8425\u573a\u6240\u53d8\u5316', '\u7b26\u5408', '\u7ecf\u8425\u573a\u6240\u672a\u53d8\u5316')

    if args.changed == 'yes':
        add('\u8bb8\u53ef\u4e8b\u9879\u53d8\u5316', '\u9700\u8865\u5145',
            '\u540d\u79f0\u3001\u6cd5\u5b9a\u4ee3\u8868\u4eba\u3001\u7ecf\u8425\u9879\u76ee\u7b49\u53d1\u751f\u53d8\u5316\u7684\u5e94\u540c\u6b65\u7533\u8bf7\u53d8\u66f4\uff0c\u52ff\u53ea\u529e\u5ef6\u7eed')
    else:
        add('\u8bb8\u53ef\u4e8b\u9879\u53d8\u5316', '\u7b26\u5408', '\u65e0\u540d\u79f0\u3001\u6cd5\u5b9a\u4ee3\u8868\u4eba\u3001\u7ecf\u8425\u9879\u76ee\u53d8\u5316')

    add('\u4eae\u8bc1\u4e0e\u7ecf\u8425\u8303\u56f4', '\u63d0\u793a',
        '\u8bb8\u53ef\u8bc1\u6b63\u672c\u5e94\u5728\u7ecf\u8425\u573a\u6240\u663e\u8457\u4f4d\u7f6e\u516c\u793a\uff0c\u4e14\u4e0d\u5f97\u8d85\u8bb8\u53ef\u7ecf\u8425\u9879\u76ee\u7ecf\u8425')

    blocked = [i for i in items if i['result'] == '\u4e0d\u7b26\u5408']
    todo = [i for i in items if i['result'] == '\u9700\u8865\u5145']
    if blocked:
        verdict = '\u4e0d\u80fd\u6309\u5ef6\u7eed\u529e\u7406'
    elif todo:
        verdict = '\u9700\u8865\u5145\u6750\u6599\u6216\u540c\u6b65\u529e\u7406\u53d8\u66f4\u540e\u63d0\u4ea4'
    else:
        verdict = '\u53ef\u63d0\u4ea4\u5ef6\u7eed\u7533\u8bf7'
    return {
        'mode': 'renew',
        'business_type': '',
        'expiry': expiry,
        'renew_deadline': deadline,
        'remain_days': remain,
        'items': items,
        'blocked': [i['name'] + '\uff1a' + i['detail'] for i in blocked],
        'todo': [i['name'] + '\uff1a' + i['detail'] for i in todo],
        'verdict': verdict,
    }


def render_md(r):
    out = []
    out.append('# \u98df\u54c1\u7ecf\u8425\u8bb8\u53ef\u6838\u67e5\u7ed3\u679c')
    out.append('')
    if r['mode'] == 'apply':
        out.append('- \u6838\u67e5\u6a21\u5f0f\uff1a\u7533\u529e\u6750\u6599\u4e0e\u573a\u6240\u6761\u4ef6\u6838\u67e5')
        out.append('- \u4e3b\u4f53\u4e1a\u6001\uff1a{}'.format(r['business_type']))
    else:
        out.append('- \u6838\u67e5\u6a21\u5f0f\uff1a\u6709\u6548\u671f\u5ef6\u7eed\u4e0e\u53d8\u66f4\u6838\u67e5')
        if r['expiry']:
            out.append('- \u6709\u6548\u671f\u81f3\uff1a{}'.format(r['expiry']))
            out.append('- \u5ef6\u7eed\u7533\u8bf7\u6700\u8fdf\u65f6\u70b9\uff1a{}\uff08\u5c4a\u6ee1 30 \u4e2a\u5de5\u4f5c\u65e5\u524d\uff09'.format(r['renew_deadline']))
            out.append('- \u5269\u4f59\u5929\u6570\uff1a{} \u5929'.format(r['remain_days']))
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
        out.append('## \u9700\u8865\u5145\u9879')
        out.append('')
        for t in r['todo']:
            out.append('- {}'.format(t))
        out.append('')
    out.append('## \u63d0\u9192')
    out.append('')
    out.append('1. \u7533\u8bf7\u6761\u4ef6\u3001\u6750\u6599\u7ec6\u9879\u3001\u73b0\u573a\u6838\u67e5\u6807\u51c6\u4e0e\u529e\u7406\u65f6\u9650\u4ee5\u5c5e\u5730\u5e02\u573a\u76d1\u7763\u7ba1\u7406\u90e8\u95e8\u73b0\u884c\u8981\u6c42\u4e3a\u51c6\u3002')
    out.append('2. \u5df2\u63d0\u4ea4\u7533\u8bf7\u4e0d\u7b49\u4e8e\u5df2\u53d7\u7406\uff0c\u5df2\u53d7\u7406\u4e0d\u7b49\u4e8e\u5df2\u8bb8\u53ef\uff0c\u62ff\u5230\u8bb8\u53ef\u8bc1\u624d\u80fd\u5f00\u5c55\u7ecf\u8425\u3002')
    out.append('3. \u4e09\u9632\u8bbe\u65bd\u88c5\u4e86\u4f46\u672a\u6b63\u5e38\u4f7f\u7528\u7684\uff0c\u7b49\u540c\u6ca1\u6709\uff0c\u73b0\u573a\u6838\u67e5\u5fc5\u6302\u3002')
    out.append('4. \u6709\u6548\u671f\u4e00\u822c\u4e3a 5 \u5e74\uff0c\u5ef6\u7eed\u5e94\u5728\u5c4a\u6ee1 30 \u4e2a\u5de5\u4f5c\u65e5\u524d\u63d0\u51fa\uff0c30 \u4e2a\u5de5\u4f5c\u65e5\u7ea6\u7b49\u4e8e 42 \u4e2a\u81ea\u7136\u65e5\u3002')
    out.append('5. \u4e00\u5730\u4e00\u8bc1\uff0c\u8fde\u9501\u95e8\u5e97\u987b\u9010\u5e97\u7533\u8bf7\uff0c\u8fc1\u5740\u4e00\u822c\u6309\u91cd\u65b0\u7533\u8bf7\u529e\u7406\u3002')
    out.append('')
    return '\n'.join(out)


def selftest():
    errors = []

    def eq(name, got, want):
        if got != want:
            errors.append('%s: got=%r want=%r' % (name, got, want))

    class A(object):
        pass

    def mk_apply(**kw):
        a = A()
        a.business_type = kw.get('business_type', 'catering')
        a.staff = kw.get('staff', 8)
        a.health_certs = kw.get('health_certs', 8)
        a.manager = kw.get('manager', 'yes')
        a.license_biz = kw.get('license_biz', 'yes')
        a.address_match = kw.get('address_match', 'yes')
        a.layout = kw.get('layout', 'yes')
        a.rules = kw.get('rules', 'yes')
        a.facility = kw.get('facility', 'pest,cold,disinfection,handwash,separate')
        a.cold_food = kw.get('cold_food', 'no')
        a.online = kw.get('online', 'no')
        return a

    def mk_renew(**kw):
        a = A()
        a.permit_date = kw.get('permit_date', '2022-03-01')
        a.relocated = kw.get('relocated', 'no')
        a.changed = kw.get('changed', 'no')
        a.as_of = kw.get('as_of', '2026-10-08')
        return a

    allf = 'pest,cold,disinfection,handwash,separate'
    r1 = check_apply(mk_apply())
    eq('case1 \u9910\u996e\u5168\u9879\u7b26\u5408', r1['verdict'], '\u6750\u6599\u4e0e\u573a\u6240\u6761\u4ef6\u57fa\u672c\u5177\u5907\uff0c\u53ef\u63d0\u4ea4\u7533\u8bf7')

    r2 = check_apply(mk_apply(health_certs=5))
    eq('case2 \u5065\u5eb7\u8bc1\u4e0d\u8db3\u4e0d\u4e88\u8bb8\u53ef', r2['verdict'], '\u5b58\u5728\u4e0d\u4e88\u8bb8\u53ef\u60c5\u5f62\uff0c\u4e0d\u80fd\u63d0\u4ea4')

    r3 = check_apply(mk_apply(manager='no'))
    eq('case3 \u65e0\u98df\u54c1\u5b89\u5168\u7ba1\u7406\u4eba\u5458', r3['verdict'], '\u5b58\u5728\u4e0d\u4e88\u8bb8\u53ef\u60c5\u5f62\uff0c\u4e0d\u80fd\u63d0\u4ea4')

    r4 = check_apply(mk_apply(address_match='no'))
    eq('case4 \u5730\u5740\u4e0d\u4e00\u81f4', r4['verdict'], '\u5b58\u5728\u4e0d\u4e88\u8bb8\u53ef\u60c5\u5f62\uff0c\u4e0d\u80fd\u63d0\u4ea4')

    r5 = check_apply(mk_apply(layout='no', rules='no'))
    eq('case5 \u7f3a\u5e03\u5c40\u56fe\u4e0e\u5236\u5ea6\u9700\u8865\u5145', r5['verdict'], '\u9700\u8865\u5145\u6750\u6599\u540e\u63d0\u4ea4')

    r6 = check_apply(mk_apply(facility='pest,cold,disinfection'))
    eq('case6 \u7f3a\u751f\u719f\u5206\u5f00\u4e0e\u6d17\u624b\u8bbe\u65bd', r6['verdict'], '\u5b58\u5728\u4e0d\u4e88\u8bb8\u53ef\u60c5\u5f62\uff0c\u4e0d\u80fd\u63d0\u4ea4')

    r7 = check_apply(mk_apply(business_type='prepackaged', facility='pest',
                              staff=2, health_certs=2))
    eq('case7 \u9884\u5305\u88c5\u98df\u54c1\u4e09\u9632\u5373\u53ef', r7['verdict'], '\u6750\u6599\u4e0e\u573a\u6240\u6761\u4ef6\u57fa\u672c\u5177\u5907\uff0c\u53ef\u63d0\u4ea4\u7533\u8bf7')

    r8 = check_apply(mk_apply(business_type='prepackaged', facility='pest',
                              staff=2, health_certs=2, cold_food='yes'))
    eq('case8 \u542b\u51b7\u85cf\u51b7\u51bb\u9700\u51b7\u5e93', r8['verdict'], '\u5b58\u5728\u4e0d\u4e88\u8bb8\u53ef\u60c5\u5f62\uff0c\u4e0d\u80fd\u63d0\u4ea4')

    r9 = check_apply(mk_apply(business_type='special', facility='pest,counter',
                              staff=2, health_certs=2))
    eq('case9 \u7279\u6b8a\u98df\u54c1\u9700\u4e13\u533a\u4e13\u67dc', r9['verdict'], '\u6750\u6599\u4e0e\u573a\u6240\u6761\u4ef6\u57fa\u672c\u5177\u5907\uff0c\u53ef\u63d0\u4ea4\u7533\u8bf7')

    r10 = check_apply(mk_apply(business_type='special', facility='pest',
                               staff=2, health_certs=2))
    eq('case10 \u7279\u6b8a\u98df\u54c1\u7f3a\u4e13\u533a\u4e13\u67dc', r10['verdict'], '\u5b58\u5728\u4e0d\u4e88\u8bb8\u53ef\u60c5\u5f62\uff0c\u4e0d\u80fd\u63d0\u4ea4')

    r11 = check_apply(mk_apply(online='yes'))
    eq('case11 \u7f51\u7edc\u7ecf\u8425\u9700\u8865\u5145', r11['verdict'], '\u9700\u8865\u5145\u6750\u6599\u540e\u63d0\u4ea4')

    s1 = check_renew(mk_renew())
    eq('case12 \u5ef6\u7eed\u6b63\u5e38', s1['verdict'], '\u53ef\u63d0\u4ea4\u5ef6\u7eed\u7533\u8bf7')
    eq('case12 \u5230\u671f\u65e5', s1['expiry'], '2027-03-01')
    eq('case12 \u5de5\u4f5c\u65e5\u6362\u7b97', (parse_date(s1['expiry']) - parse_date(s1['renew_deadline'])).days in (41, 42), True)

    s2 = check_renew(mk_renew(relocated='yes'))
    eq('case13 \u8fc1\u5740\u5e94\u91cd\u65b0\u7533\u8bf7', s2['verdict'], '\u4e0d\u80fd\u6309\u5ef6\u7eed\u529e\u7406')

    s3 = check_renew(mk_renew(changed='yes'))
    eq('case14 \u4e8b\u9879\u53d8\u5316\u9700\u53d8\u66f4', s3['verdict'], '\u9700\u8865\u5145\u6750\u6599\u6216\u540c\u6b65\u529e\u7406\u53d8\u66f4\u540e\u63d0\u4ea4')

    s4 = check_renew(mk_renew(permit_date='2020-01-01'))
    eq('case15 \u8bb8\u53ef\u5df2\u8fc7\u671f', s4['verdict'], '\u4e0d\u80fd\u6309\u5ef6\u7eed\u529e\u7406')

    s5 = check_renew(mk_renew(permit_date='2021-10-20'))
    eq('case16 \u5df2\u8fc7\u5ef6\u7eed\u7a97\u53e3', s5['verdict'], '\u9700\u8865\u5145\u6750\u6599\u6216\u540c\u6b65\u529e\u7406\u53d8\u66f4\u540e\u63d0\u4ea4')

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 16\n\u8986\u76d6: \u9910\u996e/\u9884\u5305\u88c5/\u7279\u6b8a\u98df\u54c1\u4e1a\u6001\u8bbe\u65bd\u8981\u6c42/\u5065\u5eb7\u8bc1\u8986\u76d6/'
               '\u98df\u54c1\u5b89\u5168\u7ba1\u7406\u4eba\u5458/\u5730\u5740\u4e00\u81f4\u6027/\u5e03\u5c40\u56fe\u4e0e\u5236\u5ea6/\u7f51\u7edc\u7ecf\u8425/\u6709\u6548\u671f\u4e0e\u5ef6\u7eed\u7a97\u53e3\u5de5\u4f5c\u65e5\u6362\u7b97/\u8fc1\u5740\u4e0e\u53d8\u66f4')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u98df\u54c1\u7ecf\u8425\u8bb8\u53ef\u7533\u529e\u6838\u67e5\u4e0e\u5ef6\u7eed\u6d4b\u7b97')
    ap.add_argument('--mode', default='apply', choices=['apply', 'renew'])
    ap.add_argument('--business-type', dest='business_type', default='catering',
                    choices=['prepackaged', 'bulk', 'special', 'catering', 'canteen', 'online'])
    ap.add_argument('--staff', type=int)
    ap.add_argument('--health-certs', dest='health_certs', type=int)
    ap.add_argument('--manager', default='yes', choices=['yes', 'no'])
    ap.add_argument('--license-biz', dest='license_biz', default='yes', choices=['yes', 'no'])
    ap.add_argument('--address-match', dest='address_match', default='yes', choices=['yes', 'no'])
    ap.add_argument('--layout', default='yes', choices=['yes', 'no'])
    ap.add_argument('--rules', default='yes', choices=['yes', 'no'])
    ap.add_argument('--facility', default='', help='\u5df2\u5177\u5907\u8bbe\u65bd\uff0c\u9017\u53f7\u5206\u9694')
    ap.add_argument('--cold-food', dest='cold_food', default='no', choices=['yes', 'no'])
    ap.add_argument('--online', default='no', choices=['yes', 'no'])
    ap.add_argument('--permit-date', dest='permit_date', help='\u8bb8\u53ef\u8bc1\u53d1\u8bc1\u65e5\u671f YYYY-MM-DD')
    ap.add_argument('--relocated', default='no', choices=['yes', 'no'])
    ap.add_argument('--changed', default='no', choices=['yes', 'no'])
    ap.add_argument('--as-of', dest='as_of', help='\u6838\u67e5\u57fa\u51c6\u65e5\uff0c\u9ed8\u8ba4\u4eca\u5929')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'])
    ap.add_argument('--selftest', action='store_true', help='\u8fd0\u884c\u5185\u7f6e\u81ea\u68c0')
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    r = check_apply(args) if args.mode == 'apply' else check_renew(args)
    out = render_md(r) if args.format == 'md' else json.dumps(r, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % args.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
