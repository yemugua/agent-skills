#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u536b\u751f\u8bb8\u53ef\u8bc1\u6709\u6548\u671f\u3001\u5ef6\u7eed\u7a97\u53e3\u3001\u68c0\u6d4b\u62a5\u544a\u4e0e\u5065\u5eb7\u8bc1\u5230\u671f\u6838\u67e5\u3002

\u7528\u6cd5:
  python permit_check.py --file \u8bb8\u53ef\u53f0\u8d26.json --as-of 2026-10-08
  python permit_check.py --file \u8bb8\u53ef\u53f0\u8d26.json --out \u6838\u67e5\u7ed3\u679c.md
  python permit_check.py --selftest

JSON \u7ed3\u6784:
{
  "as_of": "2026-10-08",
  "lead_days": 30,
  "items": [
    {"name": "XX\u5bbe\u9986", "type": "public", "expiry": "2027-03-31",
     "last_test": "2025-09-01", "health_expiry": "2026-12-01"},
    {"name": "XX\u98df\u5802", "type": "food", "issue": "2022-01-01"}
  ]
}
type: public \u516c\u5171\u573a\u6240\u536b\u751f\u8bb8\u53ef\u8bc1 / food \u98df\u54c1\u7ecf\u8425\u8bb8\u53ef\u8bc1 / water \u996e\u7528\u6c34\u4f9b\u6c34\u5355\u4f4d\u536b\u751f\u8bb8\u53ef\u8bc1
expiry \u672a\u586b\u65f6, \u7528 issue + \u8be5\u7c7b\u8bb8\u53ef\u7684\u5e38\u89c4\u6709\u6548\u671f(4/5/4 \u5e74)\u63a8\u7b97, \u4ec5\u4f9b\u53c2\u7167\u3002
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
    'public': '\u516c\u5171\u573a\u6240\u536b\u751f\u8bb8\u53ef\u8bc1',
    'food': '\u98df\u54c1\u7ecf\u8425\u8bb8\u53ef\u8bc1',
    'water': '\u996e\u7528\u6c34\u4f9b\u6c34\u5355\u4f4d\u536b\u751f\u8bb8\u53ef\u8bc1',
}
VALIDITY_YEARS = {'public': 4, 'food': 5, 'water': 4}
DEFAULT_LEAD_DAYS = 30
DEFAULT_TEST_MONTHS = 12


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


def due_level(days_left, warn_days=90):
    if days_left is None:
        return '\u7f3a\u5931\u6570\u636e'
    if days_left < 0:
        return '\u5df2\u8d85\u671f'
    if days_left <= 30:
        return '\u7d27\u6025'
    if days_left <= warn_days:
        return '\u9884\u8b66'
    return '\u6b63\u5e38'


def check_item(it, as_of, lead_days):
    ptype = it.get('type', 'public')
    tname = TYPE_NAME.get(ptype, ptype)
    expiry = None
    expiry_src = ''
    if it.get('expiry'):
        expiry = parse_date(it['expiry'])
        expiry_src = '\u8bc1\u4ef6\u8f7d\u660e\u7684\u6709\u6548\u671f\u622a\u6b62\u65e5'
    elif it.get('issue'):
        yrs = VALIDITY_YEARS.get(ptype, 4)
        expiry = add_years(parse_date(it['issue']), yrs)
        expiry_src = '\u6309\u53d1\u8bc1\u65e5 + %d \u5e74\u5e38\u89c1\u6709\u6548\u671f\u63a8\u7b97\uff08\u4ec5\u4f9b\u53c2\u7167\uff09' % yrs

    result = {'name': it.get('name', ''), 'type': tname,
              'expiry': fmt(expiry), 'expiry_src': expiry_src}

    if expiry is None:
        result.update({'days_to_expiry': None, 'window_start': '-',
                       'days_to_window': None, 'status': '\u7f3a\u5931\u6570\u636e',
                       'action': '\u8865\u5f55\u8bc1\u4ef6\u6709\u6548\u671f\u6216\u53d1\u8bc1\u65e5\u671f'})
    else:
        days_to_expiry = (expiry - as_of).days
        window_start = expiry - timedelta(days=lead_days)
        days_to_window = (window_start - as_of).days
        if days_to_expiry < 0:
            status = '\u5df2\u5931\u6548'
            action = '\u8bb8\u53ef\u8bc1\u5df2\u8fc7\u671f\uff0c\u9700\u91cd\u65b0\u7533\u529e\uff0c\u672a\u53d6\u5f97\u65b0\u8bc1\u524d\u4e0d\u5f97\u7ecf\u8425'
        elif days_to_expiry == 0:
            status = '\u5c4a\u6ee1\u5f53\u65e5'
            action = '\u5f53\u65e5\u7acb\u5373\u63d0\u4ea4\u5ef6\u7eed\u7533\u8bf7\uff0c\u6b21\u65e5\u8bc1\u4ef6\u5931\u6548'
        elif days_to_window <= 0:
            status = '\u53ef\u7533\u8bf7\u5ef6\u7eed'
            action = '\u7acb\u5373\u63d0\u4ea4\u5ef6\u7eed\u7533\u8bf7\u5e76\u53d6\u5f97\u53d7\u7406\u51ed\u8bc1'
        else:
            status = '\u672a\u5230\u7533\u8bf7\u7a97\u53e3'
            action = '\u5148\u5b89\u6392\u536b\u751f\u68c0\u6d4b\u4e0e\u6750\u6599\u51c6\u5907\uff0c\u7a97\u53e3\u5f00\u542f\u540e\u518d\u63d0\u4ea4'
        result.update({'days_to_expiry': days_to_expiry, 'window_start': fmt(window_start),
                       'days_to_window': days_to_window, 'status': status, 'action': action})

    if it.get('last_test'):
        months = int(it.get('test_interval_months') or DEFAULT_TEST_MONTHS)
        dl = add_months(parse_date(it['last_test']), months)
        days = (dl - as_of).days
        result.update({'test_due': fmt(dl), 'test_days': days,
                       'test_level': due_level(days)})
    else:
        result.update({'test_due': '-', 'test_days': None, 'test_level': '\u7f3a\u5931\u6570\u636e'})

    if it.get('health_expiry'):
        dl = parse_date(it['health_expiry'])
        days = (dl - as_of).days
        result.update({'health_due': fmt(dl), 'health_days': days,
                       'health_level': due_level(days, warn_days=60)})
    else:
        result.update({'health_due': '-', 'health_days': None, 'health_level': '\u7f3a\u5931\u6570\u636e'})

    return result


def render_md(results, as_of, lead_days):
    out = []
    out.append('# \u536b\u751f\u8bb8\u53ef\u8bc1\u5230\u671f\u4e0e\u5ef6\u7eed\u6838\u67e5\u7ed3\u679c')
    out.append('')
    out.append('- \u6838\u67e5\u57fa\u51c6\u65e5\uff1a%s' % fmt(as_of))
    out.append('- \u5ef6\u7eed\u7533\u8bf7\u63d0\u524d\u5929\u6570\uff1a%d \u5929\uff08\u6309\u5f53\u5730\u4e3b\u7ba1\u90e8\u95e8\u8981\u6c42\u8c03\u6574\uff09' % lead_days)
    out.append('')
    out.append('| \u5355\u4f4d | \u8bb8\u53ef\u7c7b\u522b | \u6709\u6548\u671f\u622a\u6b62\u65e5 | \u5269\u4f59\u5929\u6570 | \u5ef6\u7eed\u7a97\u53e3\u8d77\u59cb | \u72b6\u6001 |')
    out.append('|---|---|---|---|---|---|')
    for r in results:
        d = r.get('days_to_expiry')
        dtxt = '-' if d is None else (str(d) if d >= 0 else ('\u5df2\u8fc7 %d \u5929' % (-d)))
        out.append('| %s | %s | %s | %s | %s | %s |' % (
            r['name'], r['type'], r['expiry'], dtxt, r['window_start'], r['status']))
    out.append('')
    for r in results:
        out.append('## %s' % r['name'])
        out.append('')
        out.append('- \u8bb8\u53ef\u7c7b\u522b\uff1a%s' % r['type'])
        if r['expiry_src']:
            out.append('- \u6709\u6548\u671f\u6765\u6e90\uff1a%s' % r['expiry_src'])
        out.append('- \u5904\u7f6e\u52a8\u4f5c\uff1a%s' % r['action'])
        out.append('- \u536b\u751f\u68c0\u6d4b\u62a5\u544a\u5230\u671f\uff1a%s\uff08%s\uff09' % (r['test_due'], r['test_level']))
        out.append('- \u4ece\u4e1a\u4eba\u5458\u5065\u5eb7\u8bc1\u5230\u671f\uff1a%s\uff08%s\uff09' % (r['health_due'], r['health_level']))
        out.append('')
    out.append('## \u63d0\u9192')
    out.append('')
    out.append('1. \u5ef6\u7eed\u7533\u8bf7\u7684\u63d0\u524d\u5929\u6570\u4e0e\u6750\u6599\u6e05\u5355\u4ee5\u5f53\u5730\u4e3b\u7ba1\u90e8\u95e8\u516c\u793a\u4e3a\u51c6\uff0c\u672c\u811a\u672c\u9ed8\u8ba4\u6309 %d \u5929\u6d4b\u7b97\u3002' % lead_days)
    out.append('2. \u6709\u6548\u671f\u5c4a\u6ee1\u672a\u5ef6\u7eed\u7684\uff0c\u8bb8\u53ef\u8bc1\u5931\u6548\uff0c\u9700\u91cd\u65b0\u7533\u529e\uff0c\u4e0d\u80fd\u201c\u8865\u529e\u5ef6\u7eed\u201d\u3002')
    out.append('3. \u7ecf\u8425\u5730\u5740\u53d8\u66f4\uff08\u8fc1\u5740\uff09\u4e00\u822c\u9700\u91cd\u65b0\u7533\u8bf7\u5e76\u91cd\u65b0\u73b0\u573a\u6838\u67e5\u3001\u91cd\u65b0\u68c0\u6d4b\uff0c\u4e0d\u80fd\u53ea\u529e\u53d8\u66f4\u3002')
    out.append('4. \u536b\u751f\u68c0\u6d4b\u4e0e\u5065\u5eb7\u8bc1\u8d85\u671f\u4f1a\u76f4\u63a5\u5361\u4f4f\u5ef6\u7eed\uff0c\u68c0\u6d4b\u51fa\u62a5\u544a\u9700\u8981\u65f6\u95f4\uff0c\u5fc5\u987b\u63d0\u524d\u6392\u3002')
    out.append('')
    return '\n'.join(out)


def selftest():
    errors = []

    def eq(name, got, want):
        if got != want:
            errors.append('%s: got=%r want=%r' % (name, got, want))

    as_of = date(2026, 10, 8)
    lead = 30

    r1 = check_item({'name': 'A\u5bbe\u9986', 'type': 'public', 'expiry': '2027-03-31',
                     'last_test': '2026-04-01', 'health_expiry': '2026-12-01'}, as_of, lead)
    eq('case1 \u7a97\u53e3\u8d77\u59cb', r1['window_start'], '2027-03-01')
    eq('case1 \u72b6\u6001', r1['status'], '\u672a\u5230\u7533\u8bf7\u7a97\u53e3')
    eq('case1 \u8ddd\u7a97\u53e3\u5929\u6570', r1['days_to_window'], 144)
    eq('case1 \u68c0\u6d4b\u6b63\u5e38', r1['test_level'], '\u6b63\u5e38')
    eq('case1 \u5065\u5eb7\u8bc1\u9884\u8b66', r1['health_level'], '\u9884\u8b66')

    r2 = check_item({'name': 'B\u98df\u5802', 'type': 'food', 'expiry': '2026-10-20'}, as_of, lead)
    eq('case2 \u72b6\u6001', r2['status'], '\u53ef\u7533\u8bf7\u5ef6\u7eed')
    eq('case2 \u5269\u4f59\u5929\u6570', r2['days_to_expiry'], 12)
    eq('case2 \u7c7b\u578b\u540d', r2['type'], '\u98df\u54c1\u7ecf\u8425\u8bb8\u53ef\u8bc1')

    r3 = check_item({'name': 'C\u6c34\u5382', 'type': 'water', 'expiry': '2026-09-30'}, as_of, lead)
    eq('case3 \u5df2\u5931\u6548', r3['status'], '\u5df2\u5931\u6548')
    eq('case3 \u52a8\u4f5c\u542b\u91cd\u65b0\u7533\u529e', '\u91cd\u65b0\u7533\u529e' in r3['action'], True)

    r4 = check_item({'name': 'D\u5e97', 'type': 'food', 'issue': '2022-01-01'}, as_of, lead)
    eq('case4 \u63095\u5e74\u63a8\u7b97', r4['expiry'], '2027-01-01')

    r5 = check_item({'name': 'E\u5e97', 'type': 'public', 'expiry': '2027-01-01',
                     'last_test': '2025-09-01'}, as_of, lead)
    eq('case5 \u68c0\u6d4b\u5df2\u8d85\u671f', r5['test_level'], '\u5df2\u8d85\u671f')
    eq('case5 \u68c0\u6d4b\u5230\u671f\u65e5', r5['test_due'], '2026-09-01')

    r6 = check_item({'name': 'F\u5e97', 'type': 'public', 'expiry': '2026-10-08'}, as_of, lead)
    eq('case6 \u5c4a\u6ee1\u5f53\u65e5', r6['status'], '\u5c4a\u6ee1\u5f53\u65e5')

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 14\n\u8986\u76d6: \u5ef6\u7eed\u7a97\u53e3/\u53ef\u7533\u8bf7\u5224\u5b9a/'
               '\u5df2\u5931\u6548\u91cd\u65b0\u7533\u529e/\u6709\u6548\u671f\u63a8\u7b97/\u68c0\u6d4b\u4e0e\u5065\u5eb7\u8bc1\u8d85\u671f')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u536b\u751f\u8bb8\u53ef\u8bc1\u5230\u671f\u4e0e\u5ef6\u7eed\u7a97\u53e3\u6838\u67e5')
    ap.add_argument('--file', help='\u8bb8\u53ef\u53f0\u8d26 JSON \u6587\u4ef6')
    ap.add_argument('--as-of', dest='as_of', help='\u6838\u67e5\u57fa\u51c6\u65e5 YYYY-MM-DD\uff0c\u9ed8\u8ba4\u4eca\u5929')
    ap.add_argument('--lead-days', dest='lead_days', type=int, default=DEFAULT_LEAD_DAYS,
                    help='\u5ef6\u7eed\u7533\u8bf7\u63d0\u524d\u5929\u6570\uff0c\u9ed8\u8ba4 30\uff08\u6309\u5f53\u5730\u8981\u6c42\u8c03\u6574\uff09')
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
    as_of = parse_date(args.as_of) if args.as_of else (
        parse_date(data['as_of']) if data.get('as_of') else date.today())
    lead = int(data.get('lead_days') or args.lead_days)
    items = data.get('items', [])
    results = [check_item(it, as_of, lead) for it in items]

    out = render_md(results, as_of, lead) if args.format == 'md' else json.dumps(
        results, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % args.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
