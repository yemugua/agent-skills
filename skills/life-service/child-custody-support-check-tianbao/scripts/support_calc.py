#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u5b50\u5973\u629a\u517b\u8d39\u533a\u95f4\u6d4b\u7b97\u4e0e\u7ed9\u4ed8\u671f\u9650\u6298\u7b97\u3002

\u7528\u6cd5:
  python support_calc.py --income 10000 --children 1
  python support_calc.py --income-type none --income-year 180000 --children 2
  python support_calc.py --income 12000 --children 1 --child-birth 2015-06-01 --as-of 2026-10-08 --out \u7ed3\u679c.md
  python support_calc.py --selftest

\u53e3\u5f84: \u6709\u56fa\u5b9a\u6536\u5165\u7684, \u4e00\u822c\u6309\u6708\u603b\u6536\u5165\u7684 20%~30% \u7ed9\u4ed8(1 \u4e2a\u5b50\u5973);
\u8d1f\u62c5 2 \u4e2a\u53ca\u4ee5\u4e0a\u5b50\u5973\u7684, \u6bd4\u4f8b\u53ef\u9002\u5f53\u63d0\u9ad8, \u4e00\u822c\u4e0d\u8d85\u8fc7\u6708\u603b\u6536\u5165\u7684 50%(\u5b9e\u52a1\u6309 30%~50% \u6d4b\u7b97)\u3002
\u65e0\u56fa\u5b9a\u6536\u5165\u7684, \u6309\u5f53\u5e74\u603b\u6536\u5165\u6216\u540c\u884c\u4e1a\u5e73\u5747\u6536\u5165\u6298\u7b97\u6708\u6536\u5165\u540e\u53c2\u7167\u4e0a\u8ff0\u6bd4\u4f8b\u3002
\u5177\u4f53\u6570\u989d\u4ee5\u53cc\u65b9\u534f\u5546\u6216\u4eba\u6c11\u6cd5\u9662\u8ba4\u5b9a\u4e3a\u51c6\u3002
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

RATIO_ONE = (0.20, 0.30)
RATIO_MULTI = (0.30, 0.50)
ADULT_AGE = 18


def parse_date(s):
    s = str(s).strip()
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', s)
    if not m:
        raise ValueError('\u65e5\u671f\u683c\u5f0f\u4e0d\u5bf9: %s' % s)
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def monthly_income(args):
    """\u8fd4\u56de (\u6708\u6536\u5165, \u53e3\u5f84\u8bf4\u660e)\u3002"""
    if args.income_type == 'fixed':
        return float(args.income), '\u6708\u603b\u6536\u5165\uff08\u56fa\u5b9a\u6536\u5165\uff09'
    if args.income_year:
        return float(args.income_year) / 12.0, '\u5e74\u603b\u6536\u5165\u6298\u7b97\u6708\u5747'
    if args.industry_avg:
        return float(args.industry_avg), '\u540c\u884c\u4e1a\u5e73\u5747\u6536\u5165\u53c2\u7167'
    if args.income:
        return float(args.income), '\u8f93\u5165\u7684\u6708\u6536\u5165'
    raise ValueError('\u65e0\u6cd5\u786e\u5b9a\u6708\u6536\u5165\uff0c\u8bf7\u63d0\u4f9b --income / --income-year / --industry-avg')


def ratio_of(children):
    return RATIO_ONE if children <= 1 else RATIO_MULTI


def months_until_18(birth, as_of):
    """\u6309\u6574\u6708\u6298\u7b97\u81f3 18 \u5468\u5c81\u7684\u5269\u4f59\u6708\u6570\u3002"""
    end_y = birth.year + ADULT_AGE
    months = (end_y - as_of.year) * 12 + (birth.month - as_of.month)
    if birth.day < as_of.day:
        months -= 1
    return max(months, 0)


def money(x):
    return round(x + 1e-9, 2)


def calc(args):
    monthly, src = monthly_income(args)
    children = max(int(args.children), 1)
    lo_r, hi_r = ratio_of(children)
    lo = money(monthly * lo_r)
    mid = money(monthly * (lo_r + hi_r) / 2)
    hi = money(monthly * hi_r)

    out = {
        'monthly_income': money(monthly),
        'income_source': src,
        'children': children,
        'ratio': '%.0f%% ~ %.0f%%' % (lo_r * 100, hi_r * 100),
        'conservative': lo,
        'reasonable': mid,
        'target': hi,
        'yearly_low': money(lo * 12),
        'yearly_high': money(hi * 12),
        'per_child_low': money(lo / children),
        'per_child_high': money(hi / children),
    }

    if args.child_birth:
        birth = parse_date(args.child_birth)
        as_of = parse_date(args.as_of) if args.as_of else date.today()
        m = months_until_18(birth, as_of)
        out['child_birth'] = birth.strftime('%Y-%m-%d')
        out['as_of'] = as_of.strftime('%Y-%m-%d')
        out['months_remaining'] = m
        out['total_low'] = money(lo * m)
        out['total_high'] = money(hi * m)
        out['adult_date'] = date(birth.year + ADULT_AGE, birth.month, birth.day).strftime('%Y-%m-%d')
    return out


def render_md(r):
    out = []
    out.append('# \u5b50\u5973\u629a\u517b\u8d39\u6d4b\u7b97\u7ed3\u679c')
    out.append('')
    out.append('- \u6708\u6536\u5165\u8ba4\u5b9a\uff1a%.2f \u5143\uff08%s\uff09' % (r['monthly_income'], r['income_source']))
    out.append('- \u5b50\u5973\u4eba\u6570\uff1a%d' % r['children'])
    out.append('- \u9002\u7528\u6bd4\u4f8b\uff1a%s' % r['ratio'])
    out.append('')
    out.append('## \u6bcf\u6708\u7ed9\u4ed8\u533a\u95f4')
    out.append('')
    out.append('| \u6863\u4f4d | \u6bcf\u6708\u91d1\u989d\uff08\u5143\uff09 | \u6bcf\u5e74\u91d1\u989d\uff08\u5143\uff09 | \u8bf4\u660e |')
    out.append('|---|---|---|---|')
    out.append('| \u4fdd\u5b88\u6863 | %.2f | %.2f | \u6bd4\u4f8b\u4e0b\u9650\uff0c\u5bf9\u65b9\u6536\u5165\u4e3e\u8bc1\u4e0d\u8db3\u65f6\u7684\u9884\u671f\u4e0b\u9650 |'
               % (r['conservative'], r['yearly_low']))
    out.append('| \u5408\u7406\u6863 | %.2f | %.2f | \u534f\u5546\u8c08\u5224\u7684\u4e3b\u62a5\u4ef7 |'
               % (r['reasonable'], r['reasonable'] * 12))
    out.append('| \u4e89\u53d6\u6863 | %.2f | %.2f | \u591a\u4e2a\u5b50\u5973\u6216\u5b9e\u9645\u652f\u51fa\u660e\u663e\u504f\u9ad8\u65f6\u7684\u76ee\u6807 |'
               % (r['target'], r['yearly_high']))
    out.append('')
    out.append('- \u6309\u5b50\u5973\u4eba\u6570\u6446\u5e73\uff1a\u6bcf\u4eba\u6bcf\u6708 %.2f ~ %.2f \u5143' % (r['per_child_low'], r['per_child_high']))
    out.append('')
    if r.get('months_remaining') is not None:
        out.append('## \u7ed9\u4ed8\u671f\u9650\u6298\u7b97')
        out.append('')
        out.append('- \u5b50\u5973\u51fa\u751f\u65e5\uff1a%s' % r['child_birth'])
        out.append('- \u81f3 18 \u5468\u5c81\uff1a%s' % r['adult_date'])
        out.append('- \u5269\u4f59\u6708\u6570\uff1a%d \u4e2a\u6708' % r['months_remaining'])
        out.append('- \u5408\u8ba1\u533a\u95f4\uff1a%.2f ~ %.2f \u5143' % (r['total_low'], r['total_high']))
        out.append('')
        out.append('> \u6298\u7b97\u4ec5\u4f9b\u53c2\u8003\uff1a\u5b9e\u9645\u7ed9\u4ed8\u4e00\u822c\u81f3\u5b50\u5973 18 \u5468\u5c81\u4e3a\u6b62\uff1b'
                   '16 \u5468\u5c81\u4ee5\u4e0a\u4e0d\u6ee118 \u5468\u5c81\u3001\u4ee5\u52b3\u52a8\u6536\u5165\u4e3a\u4e3b\u8981\u751f\u6d3b\u6765\u6e90\u7684\u53ef\u505c\u6b62\uff1b'
                   '\u5c1a\u5728\u6821\u63a5\u53d7\u9ad8\u4e2d\u53ca\u5176\u4ee5\u4e0b\u5b66\u5386\u6559\u80b2\u3001\u6216\u4e27\u5931/\u90e8\u5206\u4e27\u5931\u52b3\u52a8\u80fd\u529b\u7b49'
                   '\u975e\u56e0\u4e3b\u89c2\u539f\u56e0\u65e0\u6cd5\u7ef4\u6301\u6b63\u5e38\u751f\u6d3b\u7684\uff0c\u53ef\u7ee7\u7eed\u7ed9\u4ed8\u3002')
        out.append('')
    out.append('## \u63d0\u9192')
    out.append('')
    out.append('1. \u6bd4\u4f8b\u53e3\u5f84\u4e3a\u901a\u884c\u5b9e\u52a1\u6807\u51c6\uff0c\u5177\u4f53\u6570\u989d\u4ee5\u53cc\u65b9\u534f\u5546\u6216\u4eba\u6c11\u6cd5\u9662\u8ba4\u5b9a\u4e3a\u51c6\u3002')
    out.append('2. \u6708\u603b\u6536\u5165\u4e00\u822c\u5305\u62ec\u5de5\u8d44\u3001\u5956\u91d1\u3001\u6d25\u8d34\u3001\u8865\u8d34\u7b49\uff0c\u4e0d\u4ec5\u4ec5\u662f\u57fa\u672c\u5de5\u8d44\u3002')
    out.append('3. \u5927\u989d\u62e9\u6821\u8d39\u3001\u79c1\u7acb\u5b66\u6821\u5b66\u8d39\u3001\u91cd\u5927\u75be\u75c5\u81ea\u8d39\u90e8\u5206\uff0c\u901a\u5e38\u9700\u53e6\u884c\u534f\u5546\u6216\u5355\u72ec\u4e3b\u5f20\u3002')
    out.append('4. \u7269\u4ef7\u4e0a\u6da8\u3001\u5b50\u5973\u60a3\u75c5\u4e0a\u5b66\u3001\u7ed9\u4ed8\u65b9\u6536\u5165\u663e\u8457\u53d8\u5316\u7684\uff0c\u53ef\u4ee5\u8bf7\u6c42\u8c03\u6574\u6570\u989d\u3002')
    out.append('')
    return '\n'.join(out)


def selftest():
    errors = []

    def eq(name, got, want):
        if got != want:
            errors.append('%s: got=%r want=%r' % (name, got, want))

    class A(object):
        pass

    a = A()
    a.income = 10000
    a.income_type = 'fixed'
    a.income_year = None
    a.industry_avg = None
    a.children = 1
    a.child_birth = None
    a.as_of = None
    r1 = calc(a)
    eq('case1 \u4e0b\u9650', r1['conservative'], 2000.0)
    eq('case1 \u4e0a\u9650', r1['target'], 3000.0)
    eq('case1 \u5408\u7406\u6863', r1['reasonable'], 2500.0)

    b = A()
    b.income = 10000
    b.income_type = 'fixed'
    b.income_year = None
    b.industry_avg = None
    b.children = 2
    b.child_birth = None
    b.as_of = None
    r2 = calc(b)
    eq('case2 \u4e0b\u9650', r2['conservative'], 3000.0)
    eq('case2 \u4e0a\u9650', r2['target'], 5000.0)
    eq('case2 \u4eba\u5747\u4e0b\u9650', r2['per_child_low'], 1500.0)

    c = A()
    c.income = None
    c.income_type = 'none'
    c.income_year = 180000
    c.industry_avg = None
    c.children = 1
    c.child_birth = '2015-06-01'
    c.as_of = '2026-10-08'
    r3 = calc(c)
    eq('case3 \u6708\u5747\u6536\u5165', r3['monthly_income'], 15000.0)
    eq('case3 \u4e0b\u9650', r3['conservative'], 3000.0)
    eq('case3 \u5269\u4f59\u6708\u6570', r3['months_remaining'], 79)
    eq('case3 \u5408\u8ba1\u4e0b\u9650', r3['total_low'], 3000.0 * 79)

    d = A()
    d.income = None
    d.income_type = 'none'
    d.income_year = None
    d.industry_avg = 8000
    d.children = 3
    d.child_birth = None
    d.as_of = None
    r4 = calc(d)
    eq('case4 \u884c\u4e1a\u5e73\u5747', r4['monthly_income'], 8000.0)
    eq('case4 \u4e09\u5b69\u4e0a\u9650\u4e0d\u8d8550%', r4['target'], 4000.0)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 12\n\u8986\u76d6: \u5355\u5b50\u597320-30%/\u591a\u5b50\u597330-50%/'
               '\u65e0\u56fa\u5b9a\u6536\u5165\u6298\u7b97/\u884c\u4e1a\u5e73\u5747\u53c2\u7167/\u7ed9\u4ed8\u671f\u9650\u6708\u6570')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u5b50\u5973\u629a\u517b\u8d39\u533a\u95f4\u6d4b\u7b97')
    ap.add_argument('--income', type=float, help='\u6708\u603b\u6536\u5165\uff08\u5143\uff09\uff0c\u56fa\u5b9a\u6536\u5165\u65f6\u586b')
    ap.add_argument('--income-type', dest='income_type', default='fixed',
                    choices=['fixed', 'none'], help='fixed \u6709\u56fa\u5b9a\u6536\u5165 / none \u65e0\u56fa\u5b9a\u6536\u5165')
    ap.add_argument('--income-year', dest='income_year', type=float, help='\u5f53\u5e74\u603b\u6536\u5165\uff08\u5143\uff09')
    ap.add_argument('--industry-avg', dest='industry_avg', type=float, help='\u540c\u884c\u4e1a\u5e73\u5747\u6708\u6536\u5165\uff08\u5143\uff09')
    ap.add_argument('--children', type=int, default=1, help='\u5b50\u5973\u4eba\u6570\uff0c\u9ed8\u8ba4 1')
    ap.add_argument('--child-birth', dest='child_birth', help='\u5b50\u5973\u51fa\u751f\u65e5\u671f YYYY-MM-DD\uff0c\u7528\u4e8e\u6298\u7b97\u7ed9\u4ed8\u671f\u9650')
    ap.add_argument('--as-of', dest='as_of', help='\u6d4b\u7b97\u57fa\u51c6\u65e5\uff0c\u9ed8\u8ba4\u4eca\u5929')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'], help='\u8f93\u51fa\u683c\u5f0f')
    ap.add_argument('--selftest', action='store_true', help='\u8fd0\u884c\u5185\u7f6e\u81ea\u68c0')
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    try:
        r = calc(args)
    except ValueError as e:
        print(str(e))
        return 2

    out = render_md(r) if args.format == 'md' else json.dumps(r, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % args.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
