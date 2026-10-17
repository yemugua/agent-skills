#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u538b\u529b\u5bb9\u5668\u4f7f\u7528\u767b\u8bb0\u4e0e\u5b9a\u671f\u68c0\u9a8c\u5230\u671f\u6838\u67e5\u3002

\u8f93\u5165 JSON \u53f0\u8d26, \u9010\u53f0\u8ba1\u7b97: \u5168\u9762\u68c0\u9a8c\u5230\u671f\u65e5 / \u5e74\u5ea6\u68c0\u67e5\u5230\u671f\u65e5 / \u8010\u538b\u8bd5\u9a8c\u5230\u671f\u65e5 /
\u5b89\u5168\u9600\u6821\u9a8c\u5230\u671f\u65e5 / \u538b\u529b\u8868\u68c0\u5b9a\u5230\u671f\u65e5, \u5e76\u7ed9\u51fa\u5269\u4f59\u5929\u6570\u4e0e\u9884\u8b66\u7b49\u7ea7\u3002

\u7528\u6cd5:
  python vessel_check.py --file \u53f0\u8d26.json --as-of 2026-10-08
  python vessel_check.py --file \u53f0\u8d26.json --out \u6838\u67e5\u7ed3\u679c.md
  python vessel_check.py --selftest

JSON \u7ed3\u6784:
{
  "as_of": "2026-10-08",
  "vessels": [
    {
      "name": "R101 \u53cd\u5e94\u91dc",
      "code": "R101",
      "commission": "2018-06-01",
      "last_full": "2021-05-20",
      "grade": 2,
      "next_full": "2027-05-20",
      "last_annual": "2026-03-01",
      "last_hydro": "2018-05-01",
      "safety_valve": "2026-01-10",
      "gauge": "2026-06-01"
    }
  ]
}
\u5b57\u6bb5\u8bf4\u660e: grade \u4e3a\u4e0a\u6b21\u5168\u9762\u68c0\u9a8c\u62a5\u544a\u8f7d\u660e\u7684\u5b89\u5168\u72b6\u51b5\u7b49\u7ea7(1~5);
next_full \u82e5\u68c0\u9a8c\u62a5\u544a\u5df2\u5199\u660e\u4e0b\u6b21\u68c0\u9a8c\u65e5\u671f\u5219\u586b, \u4f18\u5148\u4e8e\u6309\u7b49\u7ea7\u63a8\u7b97; \u5176\u4f59\u65e5\u671f\u53ef\u7701\u7565\u3002
"""
import argparse
import json
import os
import re
import sys
from datetime import date

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

CYCLE_BY_GRADE = {1: 6, 2: 6, 3: 3, 4: 1, 5: 0}
FIRST_INSPECTION_YEARS = 3
DEFAULT_HYDRO_YEARS = 10
ANNUAL_YEARS = 1
VALVE_YEARS = 1
GAUGE_MONTHS = 6
LEVEL_ORDER = ['\u6b63\u5e38', '\u5173\u6ce8', '\u9884\u8b66', '\u7d27\u6025',
               '\u5df2\u8d85\u671f', '\u7981\u6b62\u4f7f\u7528']


def parse_date(s):
    s = str(s).strip()
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', s)
    if not m:
        raise ValueError('\u65e5\u671f\u683c\u5f0f\u4e0d\u5bf9: %s' % s)
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def is_leap(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def days_in_month(y, m):
    if m == 2:
        return 29 if is_leap(y) else 28
    return [31, 0, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]


def add_months(d, months):
    total = d.month - 1 + months
    y = d.year + total // 12
    m = total % 12 + 1
    return date(y, m, min(d.day, days_in_month(y, m)))


def add_years(d, n):
    return add_months(d, 12 * n)


def fmt(d):
    return d.strftime('%Y-%m-%d') if d else '-'


def level_of(days_left):
    if days_left <= 0:
        return '\u5df2\u8d85\u671f'
    if days_left <= 30:
        return '\u7d27\u6025'
    if days_left <= 90:
        return '\u9884\u8b66'
    if days_left <= 180:
        return '\u5173\u6ce8'
    return '\u6b63\u5e38'


def worst(a, b):
    return a if LEVEL_ORDER.index(a) >= LEVEL_ORDER.index(b) else b


def check_vessel(v, as_of):
    name = v.get('name') or v.get('code') or '\u672a\u547d\u540d'
    grade = int(v.get('grade') or 0)
    items = []

    # \u5168\u9762\u68c0\u9a8c
    if v.get('next_full'):
        dl = parse_date(v['next_full'])
        src = '\u68c0\u9a8c\u62a5\u544a\u8f7d\u660e\u7684\u4e0b\u6b21\u68c0\u9a8c\u65e5\u671f'
    elif v.get('last_full'):
        cyc = CYCLE_BY_GRADE.get(grade, 3)
        dl = add_years(parse_date(v['last_full']), cyc)
        src = '\u5b89\u5168\u72b6\u51b5\u7b49\u7ea7 %s \u7ea7\uff0c\u6309 %d \u5e74\u5468\u671f\u63a8\u7b97' % (grade, cyc)
    elif v.get('commission'):
        dl = add_years(parse_date(v['commission']), FIRST_INSPECTION_YEARS)
        src = '\u6295\u7528\u540e %d \u5e74\u5185\u9996\u6b21\u5168\u9762\u68c0\u9a8c' % FIRST_INSPECTION_YEARS
    else:
        dl = None
        src = '\u7f3a\u4e0a\u6b21\u68c0\u9a8c\u65e5\u671f\u4e0e\u6295\u7528\u65e5\u671f\uff0c\u65e0\u6cd5\u63a8\u7b97'
    if dl:
        days = (dl - as_of).days
        items.append({'name': '\u5168\u9762\u68c0\u9a8c\uff08\u5b9a\u671f\u68c0\u9a8c\uff09',
                      'deadline': fmt(dl), 'days_left': days,
                      'level': '\u7981\u6b62\u4f7f\u7528' if grade == 5 else level_of(days),
                      'note': src})
    else:
        items.append({'name': '\u5168\u9762\u68c0\u9a8c\uff08\u5b9a\u671f\u68c0\u9a8c\uff09',
                      'deadline': '-', 'days_left': None,
                      'level': '\u7f3a\u5931\u6570\u636e', 'note': src})

    # \u5e74\u5ea6\u68c0\u67e5
    if v.get('last_annual'):
        dl = add_years(parse_date(v['last_annual']), ANNUAL_YEARS)
        days = (dl - as_of).days
        items.append({'name': '\u5e74\u5ea6\u68c0\u67e5', 'deadline': fmt(dl),
                      'days_left': days, 'level': level_of(days),
                      'note': '\u6bcf\u5e74\u81f3\u5c11\u4e00\u6b21\uff0c\u4e0d\u80fd\u66ff\u4ee3\u5b9a\u671f\u68c0\u9a8c'})
    else:
        items.append({'name': '\u5e74\u5ea6\u68c0\u67e5', 'deadline': '-', 'days_left': None,
                      'level': '\u7f3a\u5931\u6570\u636e',
                      'note': '\u53f0\u8d26\u672a\u586b\u5199\u4e0a\u6b21\u5e74\u5ea6\u68c0\u67e5\u65e5\u671f'})

    # \u8010\u538b\u8bd5\u9a8c
    if v.get('last_hydro'):
        dl = add_years(parse_date(v['last_hydro']), DEFAULT_HYDRO_YEARS)
        days = (dl - as_of).days
        items.append({'name': '\u8010\u538b\u8bd5\u9a8c', 'deadline': fmt(dl),
                      'days_left': days, 'level': level_of(days),
                      'note': '\u9ed8\u8ba4\u6309 %d \u5e74\u6838\u7b97\uff0c\u5177\u4f53\u4ee5\u73b0\u884c\u89c4\u7a0b\u4e0e\u68c0\u9a8c\u673a\u6784\u8981\u6c42\u4e3a\u51c6' % DEFAULT_HYDRO_YEARS})
    else:
        items.append({'name': '\u8010\u538b\u8bd5\u9a8c', 'deadline': '-', 'days_left': None,
                      'level': '\u7f3a\u5931\u6570\u636e',
                      'note': '\u672a\u586b\u5199\u4e0a\u6b21\u8010\u538b\u8bd5\u9a8c\u65e5\u671f\uff0c\u9700\u6838\u5b9e'})

    # \u5b89\u5168\u9600
    if v.get('safety_valve'):
        dl = add_years(parse_date(v['safety_valve']), VALVE_YEARS)
        days = (dl - as_of).days
        items.append({'name': '\u5b89\u5168\u9600\u6821\u9a8c', 'deadline': fmt(dl),
                      'days_left': days, 'level': level_of(days),
                      'note': '\u6bcf\u5e74\u81f3\u5c11\u6821\u9a8c\u4e00\u6b21'})
    else:
        items.append({'name': '\u5b89\u5168\u9600\u6821\u9a8c', 'deadline': '-', 'days_left': None,
                      'level': '\u7f3a\u5931\u6570\u636e', 'note': '\u672a\u586b\u5199\u6821\u9a8c\u65e5\u671f'})

    # \u538b\u529b\u8868
    if v.get('gauge'):
        dl = add_months(parse_date(v['gauge']), GAUGE_MONTHS)
        days = (dl - as_of).days
        items.append({'name': '\u538b\u529b\u8868\u68c0\u5b9a', 'deadline': fmt(dl),
                      'days_left': days, 'level': level_of(days),
                      'note': '\u6bcf\u534a\u5e74\u81f3\u5c11\u68c0\u5b9a\u4e00\u6b21'})
    else:
        items.append({'name': '\u538b\u529b\u8868\u68c0\u5b9a', 'deadline': '-', 'days_left': None,
                      'level': '\u7f3a\u5931\u6570\u636e', 'note': '\u672a\u586b\u5199\u68c0\u5b9a\u65e5\u671f'})

    overall = '\u6b63\u5e38'
    for it in items:
        if it['level'] in LEVEL_ORDER:
            overall = worst(overall, it['level'])
        else:
            overall = worst(overall, '\u9884\u8b66')

    return {'name': name, 'code': v.get('code', ''), 'grade': grade,
            'items': items, 'overall': overall}


def render_md(results, as_of):
    out = []
    out.append('# \u538b\u529b\u5bb9\u5668\u5b9a\u671f\u68c0\u9a8c\u5230\u671f\u6838\u67e5\u7ed3\u679c')
    out.append('')
    out.append('- \u6838\u67e5\u57fa\u51c6\u65e5\uff1a%s' % fmt(as_of))
    out.append('- \u8bbe\u5907\u53f0\u6570\uff1a%d' % len(results))
    cnt = {}
    for r in results:
        cnt[r['overall']] = cnt.get(r['overall'], 0) + 1
    out.append('- \u6c47\u603b\uff1a' + '\u3001'.join('%s %d \u53f0' % (k, v) for k, v in cnt.items()))
    out.append('')
    for r in results:
        out.append('## %s%s\uff08\u5b89\u5168\u72b6\u51b5\u7b49\u7ea7 %s \u7ea7\uff09' % (
            r['name'], (' / ' + r['code']) if r['code'] else '', r['grade'] if r['grade'] else '-'))
        out.append('')
        out.append('- \u6574\u4f53\u72b6\u6001\uff1a%s' % r['overall'])
        out.append('')
        out.append('| \u9879\u76ee | \u5230\u671f\u65e5 | \u5269\u4f59\u5929\u6570 | \u7b49\u7ea7 | \u8bf4\u660e |')
        out.append('|---|---|---|---|---|')
        for it in r['items']:
            d = it['days_left']
            dtxt = '-' if d is None else (str(d) if d > 0 else ('\u5df2\u8d85\u671f %d \u5929' % (-d)))
            out.append('| %s | %s | %s | %s | %s |' % (
                it['name'], it['deadline'], dtxt, it['level'], it['note']))
        out.append('')
    out.append('## \u5904\u7f6e\u8981\u6c42')
    out.append('')
    out.append('1. \u5df2\u8d85\u671f\u7684\u8bbe\u5907\u5e94\u7acb\u5373\u505c\u7528\u3001\u6302\u724c\u6807\u8bc6\uff0c\u5e76\u5411\u68c0\u9a8c\u673a\u6784\u7533\u62a5\u68c0\u9a8c\uff0c\u68c0\u9a8c\u5408\u683c\u540e\u65b9\u53ef\u6062\u590d\u4f7f\u7528\u3002')
    out.append('2. \u5b89\u5168\u72b6\u51b5\u7b49\u7ea7 5 \u7ea7\u7684\u8bbe\u5907\u4e0d\u5f97\u7ee7\u7eed\u4f7f\u7528\uff0c\u5e94\u5904\u7406\u7f3a\u9677\u540e\u91cd\u65b0\u68c0\u9a8c\u5b9a\u7ea7\u3002')
    out.append('3. \u5e74\u5ea6\u68c0\u67e5\u4e0d\u80fd\u66ff\u4ee3\u5b9a\u671f\u68c0\u9a8c\uff0c\u4e24\u9879\u5206\u522b\u8003\u6838\u3002')
    out.append('4. \u68c0\u9a8c\u62a5\u544a\u5199\u660e\u4e0b\u6b21\u68c0\u9a8c\u65e5\u671f\u7684\uff0c\u4ee5\u62a5\u544a\u4e3a\u51c6\uff1b\u672c\u811a\u672c\u4ec5\u6309\u7b49\u7ea7\u63a8\u7b97\u4f9b\u53c2\u8003\u3002')
    out.append('')
    return '\n'.join(out)


def selftest():
    errors = []

    def eq(name, got, want):
        if got != want:
            errors.append('%s: got=%r want=%r' % (name, got, want))

    as_of = date(2026, 10, 8)

    v1 = {'name': 'R101', 'code': 'R101', 'commission': '2018-06-01',
          'last_full': '2021-05-20', 'grade': 2, 'last_annual': '2026-03-01',
          'last_hydro': '2018-05-01', 'safety_valve': '2026-01-10', 'gauge': '2026-06-01'}
    r1 = check_vessel(v1, as_of)
    m1 = {i['name']: i for i in r1['items']}
    eq('case1 \u5168\u9762\u68c0\u9a8c\u5230\u671f\u65e5', m1['\u5168\u9762\u68c0\u9a8c\uff08\u5b9a\u671f\u68c0\u9a8c\uff09']['deadline'], '2027-05-20')
    eq('case1 \u5168\u9762\u68c0\u9a8c\u7b49\u7ea7', m1['\u5168\u9762\u68c0\u9a8c\uff08\u5b9a\u671f\u68c0\u9a8c\uff09']['level'], '\u6b63\u5e38')
    eq('case1 \u538b\u529b\u8868\u5230\u671f\u65e5', m1['\u538b\u529b\u8868\u68c0\u5b9a']['deadline'], '2026-12-01')
    eq('case1 \u538b\u529b\u8868\u7b49\u7ea7', m1['\u538b\u529b\u8868\u68c0\u5b9a']['level'], '\u9884\u8b66')
    eq('case1 \u5b89\u5168\u9600\u7b49\u7ea7', m1['\u5b89\u5168\u9600\u6821\u9a8c']['level'], '\u5173\u6ce8')
    eq('case1 \u6574\u4f53\u72b6\u6001', r1['overall'], '\u9884\u8b66')

    v2 = {'name': 'V202', 'last_full': '2021-05-20', 'grade': 3, 'last_annual': '2026-03-01'}
    r2 = check_vessel(v2, as_of)
    m2 = {i['name']: i for i in r2['items']}
    eq('case2 \u4e09\u7ea7\u5468\u671f3\u5e74', m2['\u5168\u9762\u68c0\u9a8c\uff08\u5b9a\u671f\u68c0\u9a8c\uff09']['deadline'], '2024-05-20')
    eq('case2 \u5df2\u8d85\u671f', m2['\u5168\u9762\u68c0\u9a8c\uff08\u5b9a\u671f\u68c0\u9a8c\uff09']['level'], '\u5df2\u8d85\u671f')
    eq('case2 \u6574\u4f53', r2['overall'], '\u5df2\u8d85\u671f')

    v3 = {'name': 'V303', 'last_full': '2024-01-10', 'grade': 5, 'last_annual': '2026-03-01'}
    r3 = check_vessel(v3, as_of)
    eq('case3 \u4e94\u7ea7\u7981\u6b62\u4f7f\u7528', r3['overall'], '\u7981\u6b62\u4f7f\u7528')

    v4 = {'name': 'V404', 'commission': '2024-01-15'}
    r4 = check_vessel(v4, as_of)
    m4 = {i['name']: i for i in r4['items']}
    eq('case4 \u9996\u6b21\u68c0\u9a8c3\u5e74', m4['\u5168\u9762\u68c0\u9a8c\uff08\u5b9a\u671f\u68c0\u9a8c\uff09']['deadline'], '2027-01-15')
    eq('case4 \u7f3a\u6570\u636e\u9879', m4['\u5e74\u5ea6\u68c0\u67e5']['level'], '\u7f3a\u5931\u6570\u636e')
    eq('case4 \u6574\u4f53', r4['overall'], '\u9884\u8b66')

    v5 = {'name': 'V505', 'last_full': '2020-02-29', 'grade': 1, 'last_annual': '2026-03-01'}
    r5 = check_vessel(v5, as_of)
    m5 = {i['name']: i for i in r5['items']}
    eq('case5 \u95f0\u65e5\u8fdb\u4f4d', m5['\u5168\u9762\u68c0\u9a8c\uff08\u5b9a\u671f\u68c0\u9a8c\uff09']['deadline'], '2026-02-28')

    v6 = {'name': 'V606', 'last_full': '2021-05-20', 'grade': 2, 'next_full': '2026-11-30'}
    r6 = check_vessel(v6, as_of)
    m6 = {i['name']: i for i in r6['items']}
    eq('case6 \u4ee5\u62a5\u544a\u8f7d\u660e\u4e3a\u51c6', m6['\u5168\u9762\u68c0\u9a8c\uff08\u5b9a\u671f\u68c0\u9a8c\uff09']['deadline'], '2026-11-30')
    eq('case6 \u9884\u8b66', m6['\u5168\u9762\u68c0\u9a8c\uff08\u5b9a\u671f\u68c0\u9a8c\uff09']['level'], '\u9884\u8b66')
    eq('case6 \u5269\u4f59\u5929\u6570', m6['\u5168\u9762\u68c0\u9a8c\uff08\u5b9a\u671f\u68c0\u9a8c\uff09']['days_left'], 53)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 15\n\u8986\u76d6: \u5468\u671f\u63a8\u7b97/\u5b89\u5168\u9644\u4ef6\u5230\u671f/'
               '3\u7ea7\u4e0e5\u7ea7\u5904\u7f6e/\u9996\u6b21\u68c0\u9a8c/\u95f0\u65e5\u8fdb\u4f4d/\u62a5\u544a\u8f7d\u660e\u4f18\u5148')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u538b\u529b\u5bb9\u5668\u5b9a\u671f\u68c0\u9a8c\u5230\u671f\u6838\u67e5')
    ap.add_argument('--file', help='\u53f0\u8d26 JSON \u6587\u4ef6\u8def\u5f84')
    ap.add_argument('--as-of', dest='as_of', help='\u6838\u67e5\u57fa\u51c6\u65e5 YYYY-MM-DD\uff0c\u9ed8\u8ba4\u4eca\u5929')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'], help='\u8f93\u51fa\u683c\u5f0f')
    ap.add_argument('--selftest', action='store_true', help='\u8fd0\u884c\u5185\u7f6e\u81ea\u68c0')
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if not args.file or not os.path.exists(args.file):
        print('\u7f3a\u5c11\u6216\u627e\u4e0d\u5230 --file')
        return 2
    with open(args.file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    vessels = data.get('vessels', [])
    as_of = parse_date(args.as_of) if args.as_of else (
        parse_date(data['as_of']) if data.get('as_of') else date.today())

    results = [check_vessel(v, as_of) for v in vessels]
    out = render_md(results, as_of) if args.format == 'md' else json.dumps(
        results, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % args.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
