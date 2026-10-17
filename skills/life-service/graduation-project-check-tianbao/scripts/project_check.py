#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u6bd5\u4e1a\u8bbe\u8ba1\uff08\u8bba\u6587\uff09\u8fdb\u5ea6\u8282\u70b9\u6838\u67e5\u4e0e\u5012\u6392\u8868\u751f\u6210\u3002

\u7528\u6cd5:
  python project_check.py --file \u8fdb\u5ea6.json --as-of 2026-10-08
  python project_check.py --defense-date 2027-05-20 --milestone "\u5f00\u9898=2027-03-11:1" --milestone "\u4e2d\u671f=2027-03-25"
  python project_check.py --selftest

JSON \u7ed3\u6784:
{
  "as_of": "2026-10-08",
  "defense_date": "2027-05-20",
  "milestones": [
    {"name": "\u5f00\u9898\u62a5\u544a", "due": "2026-11-20", "done": true},
    {"name": "\u4e2d\u671f\u68c0\u67e5", "due": "2027-03-25", "done": false}
  ]
}
--milestone \u683c\u5f0f: <\u540d\u79f0>=<\u622a\u6b62\u65e5>[:1]  \u672b\u5c3e :1 \u8868\u793a\u5df2\u5b8c\u6210
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

# \u4ece\u7b54\u8fa9\u65e5\u5012\u6392\u7684\u9ed8\u8ba4\u5468\u6570
BACKWARD = [
    ('\u5f00\u9898', 70),
    ('\u4e2d\u671f\u68c0\u67e5', 56),
    ('\u521d\u7a3f', 42),
    ('\u67e5\u91cd', 28),
    ('\u5b9a\u7a3f', 14),
]
ORDER = ['\u5df2\u5b8c\u6210', '\u6b63\u5e38', '\u5173\u6ce8', '\u9884\u8b66', '\u7d27\u6025', '\u5df2\u903e\u671f']


def parse_date(s):
    s = str(s).strip()
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', s)
    if not m:
        raise ValueError('\u65e5\u671f\u683c\u5f0f\u4e0d\u5bf9: %s' % s)
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def fmt(d):
    return d.strftime('%Y-%m-%d') if d else '-'


def status_of(done, days_left):
    if done:
        return '\u5df2\u5b8c\u6210'
    if days_left <= 0:
        return '\u5df2\u903e\u671f'
    if days_left <= 2:
        return '\u7d27\u6025'
    if days_left <= 7:
        return '\u9884\u8b66'
    if days_left <= 14:
        return '\u5173\u6ce8'
    return '\u6b63\u5e38'


def parse_milestone(text):
    if '=' not in text:
        raise ValueError('\u8282\u70b9\u683c\u5f0f\u4e0d\u5bf9: %s' % text)
    name, rest = text.split('=', 1)
    done = False
    if rest.endswith(':1'):
        done = True
        rest = rest[:-2]
    return {'name': name.strip(), 'due': parse_date(rest), 'done': done}


def check(milestones, as_of, defense_date=None):
    rows = []
    for m in milestones:
        due = m['due'] if isinstance(m['due'], date) else parse_date(m['due'])
        days = (due - as_of).days
        st = status_of(bool(m.get('done')), days)
        rows.append({'name': m['name'], 'due': fmt(due), 'days_left': days,
                     'done': bool(m.get('done')), 'status': st})
    done_n = sum(1 for r in rows if r['done'])
    total = len(rows)
    rate = int(round(done_n * 100.0 / total)) if total else 0

    worst = '\u5df2\u5b8c\u6210'
    for r in rows:
        if ORDER.index(r['status']) > ORDER.index(worst):
            worst = r['status']

    plan = []
    if defense_date:
        dd = defense_date if isinstance(defense_date, date) else parse_date(defense_date)
        for name, days in BACKWARD:
            plan.append({'name': name, 'suggest': fmt(dd - timedelta(days=days)),
                         'days_before': days})
        plan.append({'name': '\u7b54\u8fa9', 'suggest': fmt(dd), 'days_before': 0})

    return {'rows': rows, 'done_count': done_n, 'total': total, 'rate': rate,
            'overall': worst, 'plan': plan,
            'defense': fmt(defense_date) if defense_date else '-'}


def render_md(r):
    out = []
    out.append('# \u6bd5\u4e1a\u8bbe\u8ba1\uff08\u8bba\u6587\uff09\u8fdb\u5ea6\u6838\u67e5\u7ed3\u679c')
    out.append('')
    out.append('- \u8282\u70b9\u5b8c\u6210\u7387\uff1a%d%%\uff08%d/%d\uff09' % (r['rate'], r['done_count'], r['total']))
    out.append('- \u6574\u4f53\u72b6\u6001\uff1a%s' % r['overall'])
    if r['defense'] != '-':
        out.append('- \u7b54\u8fa9\u65e5\uff1a%s' % r['defense'])
    out.append('')
    out.append('| \u8282\u70b9 | \u622a\u6b62\u65e5 | \u5269\u4f59\u5929\u6570 | \u662f\u5426\u5b8c\u6210 | \u72b6\u6001 |')
    out.append('|---|---|---|---|---|')
    for row in r['rows']:
        out.append('| %s | %s | %d | %s | %s |' % (
            row['name'], row['due'], row['days_left'],
            '\u662f' if row['done'] else '\u5426', row['status']))
    out.append('')
    if r['plan']:
        out.append('## \u4ece\u7b54\u8fa9\u65e5\u5012\u6392\u7684\u5efa\u8bae\u65f6\u95f4')
        out.append('')
        out.append('| \u8282\u70b9 | \u5efa\u8bae\u65e5\u671f | \u8ddd\u7b54\u8fa9\u5929\u6570 |')
        out.append('|---|---|---|')
        for p in r['plan']:
            out.append('| %s | %s | %d |' % (p['name'], p['suggest'], p['days_before']))
        out.append('')
    out.append('## \u63d0\u9192')
    out.append('')
    out.append('1. \u5b8c\u6210\u7387\u6309\u8282\u70b9\u4e2a\u6570\u7b97\uff0c\u4e0d\u4ee3\u8868\u5b9e\u9645\u5199\u4f5c\u8fdb\u5ea6\uff1b\u5224\u65ad\u5b8c\u6210\u5ea6\u7684\u552f\u4e00\u6807\u51c6\u662f\u6709\u6ca1\u6709\u53ef\u4ea4\u4ed8\u7684\u6210\u7a3f\u3002')
    out.append('2. \u5012\u6392\u8868\u4e3a\u901a\u884c\u53e3\u5f84\uff08\u5f00\u9898\u63d0\u524d 70 \u5929\u3001\u4e2d\u671f 56 \u5929\u3001\u521d\u7a3f 42 \u5929\u3001\u67e5\u91cd 28 \u5929\u3001\u5b9a\u7a3f 14 \u5929\uff09\uff0c\u4ee5\u672c\u6821\u5de5\u4f5c\u65e5\u7a0b\u4e3a\u51c6\u3002')
    out.append('3. \u67e5\u91cd\u5fc5\u987b\u7559\u51fa\u4fee\u6539\u65f6\u95f4\uff0c\u5361\u5728\u622a\u6b62\u524d\u4e00\u5929\u51e0\u4e4e\u5fc5\u7136\u51fa\u95ee\u9898\u3002')
    out.append('4. \u8fdb\u5ea6\u843d\u540e\u65f6\uff1a\u5148\u6536\u7a84\u9898\u76ee\u8fb9\u754c\u4fdd\u4f4f\u5b8c\u6574\u6027\uff0c\u518d\u8c08\u4f18\u5316\uff1b\u7edd\u5bf9\u4e0d\u8981\u4f2a\u9020\u6570\u636e\u6216\u627e\u4eba\u4ee3\u5199\u3002')
    out.append('')
    return '\n'.join(out)


def selftest():
    errors = []

    def eq(name, got, want):
        if got != want:
            errors.append('%s: got=%r want=%r' % (name, got, want))

    as_of = date(2026, 10, 8)

    ms = [
        {'name': '\u5f00\u9898\u62a5\u544a', 'due': date(2026, 11, 20), 'done': True},
        {'name': '\u4e2d\u671f\u68c0\u67e5', 'due': date(2026, 9, 30), 'done': False},
        {'name': '\u521d\u7a3f', 'due': date(2026, 10, 20), 'done': False},
    ]
    r1 = check(ms, as_of)
    eq('case1 \u5b8c\u6210\u7387', r1['rate'], 33)
    eq('case1 \u5df2\u903e\u671f', r1['rows'][1]['status'], '\u5df2\u903e\u671f')
    eq('case1 \u5173\u6ce8', r1['rows'][2]['status'], '\u5173\u6ce8')
    eq('case1 \u5269\u4f59\u5929\u6570', r1['rows'][2]['days_left'], 12)
    eq('case1 \u6574\u4f53', r1['overall'], '\u5df2\u903e\u671f')

    r2 = check([{'name': 'A', 'due': date(2027, 1, 1), 'done': False},
                {'name': 'B', 'due': date(2027, 1, 1), 'done': True},
                {'name': 'C', 'due': date(2027, 1, 1), 'done': True},
                {'name': 'D', 'due': date(2027, 1, 1), 'done': True}], as_of)
    eq('case2 \u5b8c\u6210\u7387', r2['rate'], 75)
    eq('case2 \u6b63\u5e38', r2['rows'][0]['status'], '\u6b63\u5e38')
    eq('case2 \u6574\u4f53', r2['overall'], '\u6b63\u5e38')

    r3 = check([{'name': '\u5f00\u9898', 'due': date(2027, 3, 11), 'done': False}],
               as_of, defense_date=date(2027, 5, 20))
    plan = {p['name']: p['suggest'] for p in r3['plan']}
    eq('case3 \u5f00\u9898\u5efa\u8bae\u65e5', plan['\u5f00\u9898'], '2027-03-11')
    eq('case3 \u5b9a\u7a3f\u5efa\u8bae\u65e5', plan['\u5b9a\u7a3f'], '2027-05-06')
    eq('case3 \u67e5\u91cd\u5efa\u8bae\u65e5', plan['\u67e5\u91cd'], '2027-04-22')
    eq('case3 \u7b54\u8fa9\u65e5', plan['\u7b54\u8fa9'], '2027-05-20')

    m = parse_milestone('\u4e2d\u671f=2027-03-25:1')
    eq('case4 \u89e3\u6790\u5df2\u5b8c\u6210', m['done'], True)
    eq('case4 \u89e3\u6790\u65e5\u671f', m['due'], date(2027, 3, 25))
    m2 = parse_milestone('\u521d\u7a3f=2027-04-10')
    eq('case4 \u672a\u5b8c\u6210\u9ed8\u8ba4', m2['done'], False)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 13\n\u8986\u76d6: \u5b8c\u6210\u7387\u8ba1\u7b97/\u5df2\u903e\u671f\u4e0e\u7d27\u6025\u5206\u7ea7/'
               '\u5012\u6392\u8868\u65e5\u671f/\u8282\u70b9\u53c2\u6570\u89e3\u6790')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u6bd5\u4e1a\u8bbe\u8ba1\uff08\u8bba\u6587\uff09\u8fdb\u5ea6\u8282\u70b9\u6838\u67e5')
    ap.add_argument('--file', help='\u8fdb\u5ea6 JSON \u6587\u4ef6')
    ap.add_argument('--defense-date', dest='defense_date', help='\u7b54\u8fa9\u65e5\u671f YYYY-MM-DD')
    ap.add_argument('--milestone', action='append', default=[], help='\u8282\u70b9 "<\u540d\u79f0>=<\u622a\u6b62\u65e5>[:1]"\uff0c\u53ef\u91cd\u590d')
    ap.add_argument('--as-of', dest='as_of', help='\u6838\u67e5\u57fa\u51c6\u65e5\uff0c\u9ed8\u8ba4\u4eca\u5929')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'], help='\u8f93\u51fa\u683c\u5f0f')
    ap.add_argument('--selftest', action='store_true', help='\u8fd0\u884c\u5185\u7f6e\u81ea\u68c0')
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    milestones = []
    as_of = parse_date(args.as_of) if args.as_of else date.today()
    defense = None
    if args.file:
        if not os.path.exists(args.file):
            print('\u6587\u4ef6\u4e0d\u5b58\u5728: %s' % args.file)
            return 2
        with open(args.file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        milestones = data.get('milestones', [])
        if data.get('as_of') and not args.as_of:
            as_of = parse_date(data['as_of'])
        if data.get('defense_date'):
            defense = parse_date(data['defense_date'])
    if args.defense_date:
        defense = parse_date(args.defense_date)
    for t in args.milestone:
        milestones.append(parse_milestone(t))

    if not milestones:
        print('\u6ca1\u6709\u8282\u70b9\u6570\u636e\uff0c\u8bf7\u7528 --file \u6216 --milestone \u63d0\u4f9b')
        return 2

    r = check(milestones, as_of, defense)
    out = render_md(r) if args.format == 'md' else json.dumps(r, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % args.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
