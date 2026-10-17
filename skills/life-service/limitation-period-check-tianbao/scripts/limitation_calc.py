#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u8bc9\u8bbc\u65f6\u6548\u8d77\u7b97\u3001\u4e2d\u65ad\u3001\u4e2d\u6b62\u4e0e\u5269\u4f59\u5929\u6570\u8ba1\u7b97\u3002

\u7528\u6cd5\u793a\u4f8b:
  python limitation_calc.py --start 2020-01-01 --period 3 --as-of 2026-10-08
  python limitation_calc.py --start 2020-01-01 --event "2022-06-01,demand" --event "2023-01-05,sue,2023-08-10"
  python limitation_calc.py --selftest

--event \u683c\u5f0f: <\u65e5\u671f>,<\u7c7b\u578b>[,<\u7a0b\u5e8f\u7ec8\u7ed3\u65e5>]
  \u7c7b\u578b: sue \u8d77\u8bc9 / arb \u4ef2\u88c1 / pay \u652f\u4ed8\u4ee4 / exec \u7533\u8bf7\u6267\u884c / med \u8c03\u89e3\u6295\u8bc9\u53d7\u7406 / demand \u50ac\u544a\u5230\u8fbe / ack \u4e49\u52a1\u4eba\u8ba4\u53ef
  sue/arb/pay/exec \u5c5e\u7a0b\u5e8f\u7c7b, \u4ece"\u7a0b\u5e8f\u7ec8\u7ed3\u65e5"\u91cd\u65b0\u8d77\u7b97; \u672a\u7ed9\u7ec8\u7ed3\u65e5\u5219\u6309\u63d0\u51fa\u65e5\u91cd\u65b0\u8d77\u7b97(\u4fdd\u5b88\u53e3\u5f84)
  demand/ack/med \u5c5e\u975e\u7a0b\u5e8f\u7c7b, \u4ece\u4e8b\u4ef6\u65e5\u672c\u8eab\u91cd\u65b0\u8d77\u7b97
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

DEFAULT_PERIOD_YEARS = 3
MAX_PROTECT_YEARS = 20

EVENT_LABEL = {
    'sue': '\u63d0\u8d77\u8bc9\u8bbc',
    'arb': '\u7533\u8bf7\u4ef2\u88c1',
    'pay': '\u7533\u8bf7\u652f\u4ed8\u4ee4',
    'exec': '\u7533\u8bf7\u6267\u884c',
    'med': '\u8c03\u89e3/\u6295\u8bc9\u53d7\u7406',
    'demand': '\u50ac\u544a\u5230\u8fbe',
    'ack': '\u4e49\u52a1\u4eba\u8ba4\u53ef',
}
PROC_EVENTS = ('sue', 'arb', 'pay', 'exec')


def parse_date(s):
    s = str(s).strip()
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', s)
    if not m:
        raise ValueError('\u65e5\u671f\u683c\u5f0f\u4e0d\u5bf9: %s (\u5e94\u4e3a YYYY-MM-DD)' % s)
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
    return d.strftime('%Y-%m-%d')


def risk_level(days_left):
    if days_left <= 0:
        return '\u5df2\u5c4a\u6ee1', '\u6838\u67e5\u662f\u5426\u5b58\u5728\u6709\u6548\u4e2d\u65ad/\u4e2d\u6b62\uff1b\u6838\u67e5\u6700\u957f\u4fdd\u62a4\u671f\uff1b\u8bc4\u4f30\u5bf9\u65b9\u662f\u5426\u91cd\u65b0\u786e\u8ba4\u503a\u52a1'
    if days_left <= 30:
        return '\u7d27\u6025', '\u4f18\u5148\u5b8c\u6210\u7acb\u6848\uff08\u7f51\u4e0a\u7acb\u6848\u4e0e\u90ae\u5bc4\u7acb\u6848\u540c\u6b65\uff09\uff0c\u4e0d\u8981\u53ea\u53d1\u50ac\u544a'
    if days_left <= 90:
        return '\u9884\u8b66', '\u542f\u52a8\u8d77\u8bc9\u6216\u4ef2\u88c1\u7acb\u6848\u51c6\u5907\uff0c\u540c\u6b65\u53d1\u51fa\u4e66\u9762\u50ac\u544a\u51fd'
    if days_left <= 180:
        return '\u5173\u6ce8', '\u5c3d\u5feb\u53d1\u51fa\u4e66\u9762\u50ac\u544a\u5e76\u53d6\u5f97\u9001\u8fbe\u51ed\u8bc1\uff0c\u6216\u542f\u52a8\u8c03\u89e3'
    return '\u5b89\u5168', '\u6b63\u5e38\u51c6\u5907\u8bc1\u636e\uff0c\u6ce8\u610f\u4fdd\u7559\u6240\u6709\u9001\u8fbe\u51ed\u8bc1'


def parse_event(text):
    parts = [p.strip() for p in text.split(',')]
    if len(parts) < 2:
        raise ValueError('\u4e8b\u4ef6\u683c\u5f0f\u4e0d\u5bf9: %s' % text)
    etype = parts[1].lower()
    if etype not in EVENT_LABEL:
        raise ValueError('\u4e8b\u4ef6\u7c7b\u578b\u4e0d\u5bf9: %s' % parts[1])
    ev = {'date': parse_date(parts[0]), 'type': etype}
    if len(parts) >= 3 and parts[2]:
        ev['end'] = parse_date(parts[2])
    else:
        ev['end'] = ev['date']
    if etype in PROC_EVENTS:
        ev['kind'] = '\u7a0b\u5e8f\u7c7b'
    else:
        ev['kind'] = '\u975e\u7a0b\u5e8f\u7c7b'
    return ev


def compute(start, period_years, events, as_of, damage_date=None,
            suspend_start=None, suspend_end=None):
    """\u8fd4\u56de\u8ba1\u7b97\u7ed3\u679c dict\u3002"""
    events = sorted(events, key=lambda e: e['date'])
    chain = []
    cur_start = start
    cur_deadline = add_years(cur_start, period_years)
    chain.append({
        'seq': 0,
        'event': '\u8d77\u7b97',
        'date': fmt(cur_start),
        'base': fmt(cur_start),
        'deadline': fmt(cur_deadline),
        'note': '\u539f\u59cb\u8d77\u7b97\uff0c\u671f\u95f4 %d \u5e74' % period_years,
    })

    for i, ev in enumerate(events, start=1):
        if ev['date'] > cur_deadline:
            chain.append({
                'seq': i,
                'event': EVENT_LABEL[ev['type']],
                'date': fmt(ev['date']),
                'base': '-',
                'deadline': '-',
                'note': '\u53d1\u751f\u5728\u539f\u5c4a\u6ee1\u65e5\u4e4b\u540e\uff0c\u5bf9\u671f\u95f4\u65e0\u5f71\u54cd\uff08\u671f\u95f4\u5df2\u5c4a\u6ee1\uff09',
            })
            continue
        base = ev['end'] if ev['kind'] == '\u7a0b\u5e8f\u7c7b' else ev['date']
        cur_start = base
        cur_deadline = add_years(cur_start, period_years)
        note = '\u91cd\u65b0\u8d77\u7b97' + ('\uff08\u7a0b\u5e8f\u7ec8\u7ed3\u65e5\uff09' if ev['kind'] == '\u7a0b\u5e8f\u7c7b' else '\uff08\u4e8b\u4ef6\u53d1\u751f\u65e5\uff09')
        chain.append({
            'seq': i,
            'event': EVENT_LABEL[ev['type']],
            'date': fmt(ev['date']),
            'base': fmt(base),
            'deadline': fmt(cur_deadline),
            'note': note,
        })

    suspend_note = ''
    if suspend_start and suspend_end:
        last6 = add_months(cur_deadline, -6)
        eff_start = max(suspend_start, last6)
        if suspend_end > last6:
            new_deadline = add_months(suspend_end, 6)
            if new_deadline > cur_deadline:
                suspend_note = '\u969c\u788d\u81ea %s \u8d77\u5f71\u54cd\u65f6\u6548\uff0c%s \u6d88\u9664\uff0c\u6309\u8865\u8db3 6 \u4e2a\u6708\u89c4\u5219\u987a\u5ef6\u81f3 %s' % (
                    fmt(eff_start), fmt(suspend_end), fmt(new_deadline))
                cur_deadline = new_deadline
        else:
            suspend_note = '\u969c\u788d\u5728\u65f6\u6548\u6700\u540e 6 \u4e2a\u6708\u4e4b\u524d\u5df2\u6d88\u9664\uff0c\u4e0d\u4ea7\u751f\u4e2d\u6b62\u6548\u679c'

    cap_note = ''
    if damage_date:
        cap = add_years(damage_date, MAX_PROTECT_YEARS)
        if cap < cur_deadline:
            cap_note = '\u6700\u957f\u6743\u5229\u4fdd\u62a4\u671f\u81ea\u635f\u5bb3\u65e5 %s \u8d77 20 \u5e74\uff0c\u5373 %s \u5c4a\u6ee1\uff0c\u65e9\u4e8e\u666e\u901a\u65f6\u6548\u5c4a\u6ee1\u65e5\uff0c\u4ee5\u8be5\u65e5\u4e3a\u51c6' % (
                fmt(damage_date), fmt(cap))
            cur_deadline = cap

    days_left = (cur_deadline - as_of).days
    level, advice = risk_level(days_left)

    return {
        'start': fmt(start),
        'period_years': period_years,
        'as_of': fmt(as_of),
        'chain': chain,
        'final_start': fmt(cur_start),
        'deadline': fmt(cur_deadline),
        'days_left': days_left,
        'risk_level': level,
        'advice': advice,
        'suspend_note': suspend_note,
        'cap_note': cap_note,
        'max_protect': fmt(add_years(damage_date, MAX_PROTECT_YEARS)) if damage_date else '',
    }


def render_md(r):
    lines = []
    lines.append('# \u8bc9\u8bbc\u65f6\u6548\u6838\u67e5\u7ed3\u679c')
    lines.append('')
    lines.append('- \u8d77\u7b97\u65e5\uff1a%s' % r['start'])
    lines.append('- \u9002\u7528\u671f\u95f4\uff1a%d \u5e74' % r['period_years'])
    lines.append('- \u6838\u67e5\u57fa\u51c6\u65e5\uff1a%s' % r['as_of'])
    lines.append('- \u6700\u540e\u91cd\u65b0\u8d77\u7b97\u65e5\uff1a%s' % r['final_start'])
    lines.append('- \u65f6\u6548\u5c4a\u6ee1\u65e5\uff1a%s' % r['deadline'])
    if r['days_left'] > 0:
        lines.append('- \u5269\u4f59\u5929\u6570\uff1a%d \u5929' % r['days_left'])
    elif r['days_left'] == 0:
        lines.append('- \u5269\u4f59\u5929\u6570\uff1a0 \u5929\uff08\u5f53\u65e5 24 \u65f6\u524d\u5c4a\u6ee1\uff0c\u987b\u7acb\u5373\u884c\u52a8\uff09')
    else:
        lines.append('- \u5df2\u8fc7\u5929\u6570\uff1a%d \u5929\uff08\u671f\u95f4\u5df2\u5c4a\u6ee1\uff09' % (-r['days_left']))
    lines.append('- \u98ce\u9669\u7b49\u7ea7\uff1a%s' % r['risk_level'])
    lines.append('- \u5efa\u8bae\u52a8\u4f5c\uff1a%s' % r['advice'])
    lines.append('')
    lines.append('## \u4e2d\u65ad\u94fe\u6761')
    lines.append('')
    lines.append('| # | \u4e8b\u7531 | \u53d1\u751f\u65e5 | \u91cd\u65b0\u8d77\u7b97\u57fa\u51c6\u65e5 | \u5c4a\u6ee1\u65e5 | \u8bf4\u660e |')
    lines.append('|---|---|---|---|---|---|')
    for c in r['chain']:
        lines.append('| %s | %s | %s | %s | %s | %s |' % (
            c['seq'], c['event'], c['date'], c['base'], c['deadline'], c['note']))
    lines.append('')
    if r['suspend_note']:
        lines.append('## \u4e2d\u6b62')
        lines.append('')
        lines.append('- ' + r['suspend_note'])
        lines.append('')
    if r['cap_note']:
        lines.append('## \u6700\u957f\u6743\u5229\u4fdd\u62a4\u671f')
        lines.append('')
        lines.append('- ' + r['cap_note'])
        lines.append('')
    lines.append('## \u9632\u8bef\u4f24\u63d0\u9192')
    lines.append('')
    lines.append('1. \u50ac\u544a\u7c7b\u4e8b\u4ef6\u6309\u300c\u5230\u8fbe\u4e49\u52a1\u4eba\u4e4b\u65e5\u300d\u8ba1\u7b97\uff0c\u4e0d\u662f\u53d1\u51fa\u65e5\uff1b\u672a\u59a5\u6295\u7684\u4e0d\u7b97\u6709\u6548\u4e2d\u65ad\u3002')
    lines.append('2. \u8d77\u8bc9\u540e\u64a4\u8bc9\u3001\u8d77\u8bc9\u88ab\u88c1\u5b9a\u4e0d\u4e88\u53d7\u7406\u6216\u88ab\u9a73\u56de\u7684\uff0c\u6309\u4fdd\u5b88\u53e3\u5f84\u4e0d\u4ea7\u751f\u4e2d\u65ad\u6548\u679c\u3002')
    lines.append('3. \u5c4a\u6ee1\u65e5\u9047\u8282\u5047\u65e5\u7684\u987a\u5ef6\u3001\u4ee5\u53ca\u5177\u4f53\u671f\u95f4\u957f\u5ea6\uff0c\u4ee5\u73b0\u884c\u89c4\u5b9a\u548c\u53d7\u8bc9\u6cd5\u9662\u8ba4\u5b9a\u4e3a\u51c6\u3002')
    lines.append('4. \u671f\u95f4\u5c4a\u6ee1\u4e0d\u5bfc\u81f4\u6743\u5229\u6d88\u706d\uff0c\u4e49\u52a1\u4eba\u4ecd\u53ef\u81ea\u613f\u5c65\u884c\uff0c\u4e14\u5c65\u884c\u540e\u4e0d\u5f97\u8bf7\u6c42\u8fd4\u8fd8\u3002')
    lines.append('')
    return '\n'.join(lines)


def selftest():
    errors = []

    def eq(name, got, want):
        if got != want:
            errors.append('%s: got=%r want=%r' % (name, got, want))

    # 1) \u57fa\u672c 3 \u5e74\uff0c\u65e0\u4e2d\u65ad
    r1 = compute(date(2020, 1, 1), 3, [], date(2022, 12, 31))
    eq('case1 deadline', r1['deadline'], '2023-01-01')
    eq('case1 days_left', r1['days_left'], 1)
    eq('case1 level', r1['risk_level'], '\u7d27\u6025')

    # 2) \u50ac\u544a\u4e2d\u65ad\u540e\u91cd\u65b0\u8d77\u7b97
    evs = [parse_event('2022-06-01,demand')]
    r2 = compute(date(2020, 1, 1), 3, evs, date(2024, 1, 1))
    eq('case2 deadline', r2['deadline'], '2025-06-01')
    eq('case2 days_left', r2['days_left'], (date(2025, 6, 1) - date(2024, 1, 1)).days)
    eq('case2 level', r2['risk_level'], '\u5b89\u5168')

    # 3) \u8d77\u8bc9\u7a0b\u5e8f\u7c7b\uff0c\u4ece\u7a0b\u5e8f\u7ec8\u7ed3\u65e5\u91cd\u65b0\u8d77\u7b97
    evs3 = [parse_event('2022-06-01,sue,2023-08-10')]
    r3 = compute(date(2020, 1, 1), 3, evs3, date(2026, 10, 8))
    eq('case3 deadline', r3['deadline'], '2026-08-10')
    eq('case3 overdue', r3['days_left'] < 0, True)

    # 4) \u6700\u957f\u6743\u5229\u4fdd\u62a4\u671f 20 \u5e74\u4f18\u5148
    r4 = compute(date(2019, 1, 1), 3, [], date(2022, 1, 1), damage_date=date(2000, 1, 1))
    eq('case4 deadline', r4['deadline'], '2020-01-01')
    eq('case4 level', r4['risk_level'], '\u5df2\u5c4a\u6ee1')

    # 5) \u4e2d\u6b62\uff1a\u6700\u540e 6 \u4e2a\u6708\u5185\u969c\u788d\uff0c\u8865\u8db3 6 \u4e2a\u6708
    r5 = compute(date(2020, 1, 1), 3, [], date(2023, 1, 1),
                 suspend_start=date(2022, 12, 1), suspend_end=date(2024, 1, 10))
    eq('case5 deadline', r5['deadline'], '2024-07-10')

    # 6) \u95f0\u65e5\u8fdb\u4f4d
    r6 = compute(date(2020, 2, 29), 3, [], date(2023, 1, 1))
    eq('case6 deadline', r6['deadline'], '2023-02-28')

    # 7) \u5c4a\u6ee1\u540e\u53d1\u751f\u7684\u4e8b\u4ef6\u4e0d\u5f71\u54cd\u671f\u95f4
    evs7 = [parse_event('2024-01-01,demand')]
    r7 = compute(date(2020, 1, 1), 3, evs7, date(2026, 10, 8))
    eq('case7 deadline', r7['deadline'], '2023-01-01')

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = 'SELFTEST OK\n\u65ad\u8a00\u6570: 13\n\u8986\u76d6: \u57fa\u672c\u671f\u95f4/\u50ac\u544a\u4e2d\u65ad/\u7a0b\u5e8f\u7c7b\u4e2d\u65ad/20\u5e74\u6700\u957f\u4fdd\u62a4\u671f/\u4e2d\u6b62\u8865\u8db3/\u95f0\u65e5\u8fdb\u4f4d/\u5c4a\u6ee1\u540e\u4e8b\u4ef6'
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u8bc9\u8bbc\u65f6\u6548\u8d77\u7b97\u3001\u4e2d\u65ad\u4e0e\u5269\u4f59\u5929\u6570\u8ba1\u7b97')
    ap.add_argument('--start', help='\u8d77\u7b97\u65e5 YYYY-MM-DD\uff08\u77e5\u9053\u6216\u5e94\u5f53\u77e5\u9053\u6743\u5229\u53d7\u635f\u4e14\u77e5\u9053\u4e49\u52a1\u4eba\u4e4b\u65e5\uff09')
    ap.add_argument('--period', type=int, default=DEFAULT_PERIOD_YEARS, help='\u671f\u95f4\u5e74\u6570\uff0c\u9ed8\u8ba4 3')
    ap.add_argument('--as-of', dest='as_of', help='\u6838\u67e5\u57fa\u51c6\u65e5\uff0c\u9ed8\u8ba4\u4eca\u5929')
    ap.add_argument('--damage-date', dest='damage_date', help='\u6743\u5229\u53d7\u635f\u5bb3\u4e4b\u65e5\uff0c\u7528\u4e8e\u7b97 20 \u5e74\u6700\u957f\u4fdd\u62a4\u671f')
    ap.add_argument('--event', action='append', default=[], help='\u4e2d\u65ad\u4e8b\u4ef6 "<\u65e5\u671f>,<\u7c7b\u578b>[,<\u7ec8\u7ed3\u65e5>]"\uff0c\u53ef\u91cd\u590d')
    ap.add_argument('--suspend-start', dest='suspend_start', help='\u4e2d\u6b62\u969c\u788d\u5f00\u59cb\u65e5')
    ap.add_argument('--suspend-end', dest='suspend_end', help='\u4e2d\u6b62\u969c\u788d\u6d88\u9664\u65e5')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84\uff08\u9ed8\u8ba4\u53ea\u6253\u5370\uff09')
    ap.add_argument('--format', default='md', choices=['md', 'json'], help='\u8f93\u51fa\u683c\u5f0f')
    ap.add_argument('--selftest', action='store_true', help='\u8fd0\u884c\u5185\u7f6e\u81ea\u68c0')
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if not args.start:
        print('\u7f3a\u5c11 --start\uff0c\u53ef\u7528 --selftest \u67e5\u770b\u793a\u4f8b')
        return 2

    start = parse_date(args.start)
    as_of = parse_date(args.as_of) if args.as_of else date.today()
    events = [parse_event(e) for e in args.event]
    damage = parse_date(args.damage_date) if args.damage_date else None
    ss = parse_date(args.suspend_start) if args.suspend_start else None
    se = parse_date(args.suspend_end) if args.suspend_end else None

    r = compute(start, args.period, events, as_of, damage, ss, se)
    text = render_md(r) if args.format == 'md' else json.dumps(r, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % args.out)
    print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
