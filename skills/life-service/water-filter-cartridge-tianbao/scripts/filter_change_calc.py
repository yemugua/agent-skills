# -*- coding: utf-8 -*-
"""\u51c0\u6c34\u5668\u6ee4\u82af\u66f4\u6362\u5468\u671f\u6838\u67e5\uff1a\u6309\u65f6\u95f4\u4e0e\u7d2f\u8ba1\u51c0\u6c34\u91cf\u53cc\u6307\u6807\u7b97\u5bff\u547d\uff0c\u8f93\u51fa\u66f4\u6362\u987a\u5e8f\u4e0e\u6c34\u8d28\u63d0\u793a\u3002

\u7528\u6cd5:
  python filter_change_calc.py --file filter.json [--out \u6ee4\u82af\u6838\u67e5.md] [--format json]
  python filter_change_calc.py --selftest
"""
import argparse
import json
import os
import sys
from datetime import date

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

DAYS_PER_MONTH = 30
NORMAL = 70.0
WATCH = 100.0
SALT_OK = 90.0
SALT_BAD = 85.0


def parse_date(s):
    """\u89e3\u6790 YYYY-MM-DD\uff0c\u5931\u8d25\u5219\u629b ValueError\u3002"""
    if not s:
        raise ValueError('\u65e5\u671f\u4e0d\u80fd\u4e3a\u7a7a')
    parts = str(s).strip().split('-')
    if len(parts) != 3:
        raise ValueError('\u65e5\u671f\u683c\u5f0f\u5e94\u4e3a YYYY-MM-DD\uff0c\u5b9e\u4e3a %s' % s)
    try:
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        raise ValueError('\u65e5\u671f\u4e0d\u5408\u6cd5: %s' % s)


def status_of(pct):
    if pct >= WATCH:
        return '\u8d85\u671f'
    if pct >= NORMAL:
        return '\u5173\u6ce8'
    return '\u6b63\u5e38'


def suggestion_of(status):
    if status == '\u8d85\u671f':
        return '\u89c6\u4e3a\u5931\u6548\uff0c\u53ca\u65f6\u66f4\u6362\uff1b\u66f4\u6362\u524d\u505c\u6b62\u76f4\u996e\uff0c\u6539\u716e\u6cb8'
    if status == '\u5173\u6ce8':
        return '\u5907\u597d\u65b0\u6ee4\u82af\uff0c\u5b89\u6392\u66f4\u6362'
    return '\u7ee7\u7eed\u4f7f\u7528\uff0c\u8bb0\u5f55\u51c0\u6c34\u91cf\u8bfb\u6570'


def flux_by_people(n):
    """\u6309\u4eba\u6570\u7ed9\u901a\u91cf\u5efa\u8bae\u6863\u4f4d\u3002"""
    if n <= 2:
        return '400G'
    if n <= 4:
        return '600G'
    return '800G \u53ca\u4ee5\u4e0a'


def salt_rate(tds_in, tds_out):
    """RO \u8131\u76d0\u7387\uff0c\u8fdb\u6c34 TDS \u5fc5\u987b\u4e3a\u6b63\u3002"""
    if tds_in is None or tds_in <= 0:
        return None
    if tds_out is None:
        return None
    return (1.0 - float(tds_out) / float(tds_in)) * 100.0


def salt_advice(rate):
    if rate is None:
        return '\u672a\u586b\u5199\u8fdb\u51fa\u6c34 TDS\uff0c\u8df3\u8fc7\u8131\u76d0\u7387\u5224\u65ad'
    if rate >= SALT_OK:
        return '\u819c\u72b6\u6001\u826f\u597d'
    if rate >= SALT_BAD:
        return '\u5f00\u59cb\u8870\u51cf\uff0c\u5efa\u8bae\u590d\u6d4b\u5e76\u5173\u6ce8'
    return '\u660e\u663e\u8870\u51cf\uff0c\u5efa\u8bae\u66f4\u6362 RO \u819c\uff08\u5148\u6392\u9664\u8fdb\u6c34 TDS \u53d8\u5316\u4e0e\u50a8\u6c34\u6876\u56e0\u7d20\uff09'


def calc(data):
    today = parse_date(data.get('today'))
    daily = float(data.get('daily_liters', 10))
    people = int(data.get('people', 3))
    tds_in = data.get('tds_in')
    tds_out = data.get('tds_out')
    carts = data.get('cartridges', []) or []

    if not carts:
        raise ValueError('\u81f3\u5c11\u9700\u8981\u4e00\u7ea7\u6ee4\u82af\u6570\u636e')
    if daily < 0:
        raise ValueError('\u65e5\u5747\u7528\u6c34\u91cf\u4e0d\u80fd\u4e3a\u8d1f')

    rows = []
    for c in carts:
        name = c.get('name', '\u672a\u547d\u540d\u6ee4\u82af')
        last = parse_date(c.get('last_change'))
        months = float(c.get('rated_months', 0))
        rated_l = float(c.get('rated_liters', 0))
        if months <= 0:
            raise ValueError('\u6ee4\u82af %s \u7684\u989d\u5b9a\u6708\u6570\u5fc5\u987b\u4e3a\u6b63\u6570' % name)

        days = (today - last).days
        if days < 0:
            raise ValueError('\u6ee4\u82af %s \u7684\u4e0a\u6b21\u66f4\u6362\u65e5\u671f\u665a\u4e8e\u4eca\u65e5' % name)

        rated_days = months * DAYS_PER_MONTH
        time_pct = days / rated_days * 100.0
        liters = daily * days
        if rated_l > 0:
            vol_pct = liters / rated_l * 100.0
        else:
            vol_pct = 0.0
        pct = max(time_pct, vol_pct)
        st = status_of(pct)
        rows.append({
            'name': name,
            'last_change': str(last),
            'days': days,
            'rated_months': months,
            'rated_liters': rated_l,
            'time_pct': round(time_pct, 1),
            'vol_pct': round(vol_pct, 1),
            'pct': round(pct, 1),
            'liters': round(liters, 1),
            'remain_days': int(rated_days - days),
            'status': st,
            'advice': suggestion_of(st),
        })

    rows.sort(key=lambda r: r['pct'], reverse=True)
    rate = salt_rate(tds_in, tds_out)
    over = [r for r in rows if r['status'] == '\u8d85\u671f']

    warns = []
    if over:
        warns.append('\u5b58\u5728\u8d85\u671f\u6ee4\u82af\uff1a%s\u3002\u8d85\u671f\u5373\u89c6\u4e3a\u5931\u6548\uff0c\u66f4\u6362\u524d\u505c\u6b62\u76f4\u996e\uff0c\u6539\u716e\u6cb8\u540e\u996e\u7528'
                     % '\u3001'.join(r['name'] for r in over))
    if rate is not None and rate < SALT_BAD:
        warns.append('RO \u8131\u76d0\u7387 %.1f%% \u4f4e\u4e8e %.0f%%\uff0c\u5efa\u8bae\u66f4\u6362 RO \u819c' % (rate, SALT_BAD))
    if daily * 30 > 3000:
        warns.append('\u6708\u7528\u6c34\u91cf\u504f\u5927\uff08\u7ea6 %.0f L/\u6708\uff09\uff0c\u8bf7\u6309\u6c34\u91cf\u8fdb\u5ea6\u800c\u975e\u65f6\u95f4\u8fdb\u5ea6\u5224\u65ad\u66f4\u6362\u65f6\u673a'
                     % (daily * 30))

    return {
        'today': str(today),
        'people': people,
        'daily_liters': daily,
        'flux_advice': flux_by_people(people),
        'tds_in': tds_in,
        'tds_out': tds_out,
        'salt_rate': None if rate is None else round(rate, 2),
        'salt_advice': salt_advice(rate),
        'rows': rows,
        'warns': warns,
        'overdue': [r['name'] for r in over],
    }


def render_md(r):
    L = []
    L.append('# \u51c0\u6c34\u5668\u6ee4\u82af\u66f4\u6362\u5468\u671f\u6838\u67e5')
    L.append('')
    L.append('## \u4e00\u3001\u57fa\u7840\u4fe1\u606f')
    L.append('')
    L.append('| \u9879 | \u503c |')
    L.append('|---|---|')
    L.append('| \u6838\u67e5\u65e5\u671f | %s |' % r['today'])
    L.append('| \u5bb6\u5ead\u4eba\u6570 | %d \u4eba |' % r['people'])
    L.append('| \u65e5\u5747\u7528\u6c34\u91cf | %.1f L |' % r['daily_liters'])
    L.append('| \u901a\u91cf\u5efa\u8bae | %s |' % r['flux_advice'])
    if r['salt_rate'] is not None:
        L.append('| \u8fdb\u6c34 TDS | %s |' % r['tds_in'])
        L.append('| \u51fa\u6c34 TDS | %s |' % r['tds_out'])
        L.append('| RO \u8131\u76d0\u7387 | %.2f%% |' % r['salt_rate'])
        L.append('| \u8131\u76d0\u7387\u5224\u65ad | %s |' % r['salt_advice'])
    else:
        L.append('| \u8131\u76d0\u7387\u5224\u65ad | %s |' % r['salt_advice'])
    L.append('')
    L.append('## \u4e8c\u3001\u5404\u7ea7\u6ee4\u82af\u5bff\u547d\uff08\u6309\u5bff\u547d\u767e\u5206\u6bd4\u4ece\u9ad8\u5230\u4f4e\uff0c\u5373\u66f4\u6362\u987a\u5e8f\uff09')
    L.append('')
    L.append('| \u987a\u5e8f | \u6ee4\u82af | \u4e0a\u6b21\u66f4\u6362 | \u5df2\u7528\u5929\u6570 | \u65f6\u95f4\u8fdb\u5ea6 | \u6c34\u91cf\u8fdb\u5ea6 | \u5bff\u547d\u767e\u5206\u6bd4 | \u5269\u4f59\u5929\u6570 | \u72b6\u6001 | \u5efa\u8bae |')
    L.append('|---|---|---|---|---|---|---|---|---|---|')
    for i, row in enumerate(r['rows'], 1):
        L.append('| %d | %s | %s | %d | %.1f%% | %.1f%% | %.1f%% | %d | %s | %s |'
                 % (i, row['name'], row['last_change'], row['days'], row['time_pct'],
                    row['vol_pct'], row['pct'], row['remain_days'], row['status'], row['advice']))
    L.append('')
    L.append('## \u4e09\u3001\u63d0\u9192')
    L.append('')
    if r['warns']:
        for w in r['warns']:
            L.append('- %s' % w)
    else:
        L.append('- \u672a\u53d1\u73b0\u8d85\u671f\u6ee4\u82af\uff0c\u6309\u8ba1\u5212\u4f7f\u7528\u5e76\u8bb0\u5f55\u51c0\u6c34\u91cf\u8bfb\u6570')
    L.append('')
    L.append('## \u56db\u3001\u4eba\u5de5\u786e\u8ba4\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] \u51fa\u6c34\u662f\u5426\u6d51\u6d4a\u3001\u6709\u5f02\u5473\u3001\u6709\u53ef\u89c1\u6742\u8d28\uff08\u6709\u5219\u505c\u6b62\u76f4\u996e\uff09')
    L.append('- [ ] \u989d\u5b9a\u5468\u671f\u4e0e\u989d\u5b9a\u603b\u51c0\u6c34\u91cf\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e66\u4e3a\u51c6')
    L.append('- [ ] \u66f4\u6362\u524d\u65ad\u7535\u3001\u5173\u8fdb\u6c34\u9600\u3001\u6cc4\u538b')
    L.append('- [ ] \u5bc6\u5c01\u5708\u672a\u6f0f\u88c5\u672a\u7ffb\u8fb9\uff0c\u6ee4\u74f6\u672a\u6b7b\u62e7')
    L.append('- [ ] \u5df2\u5145\u5206\u51b2\u6d17\uff08RO \u819c 20-30 \u5206\u949f\uff0c\u6d3b\u6027\u70ad 5-10 \u5206\u949f\uff09')
    L.append('- [ ] \u524d\u51e0\u7bb1\u6c34\u672a\u76f4\u63a5\u996e\u7528\uff0cTDS \u5df2\u590d\u6d4b')
    return '\n'.join(L)


def render_json(r):
    return json.dumps(r, ensure_ascii=False, indent=2)


def selftest():
    errs = []
    checks = 0

    def ck(cond, msg):
        nonlocal checks
        checks += 1
        if not cond:
            errs.append(msg)

    # 1 \u65f6\u95f4\u8fdb\u5ea6\u4e3b\u5bfc
    r1 = calc({'today': '2026-03-01', 'people': 4, 'daily_liters': 12,
               'cartridges': [{'name': 'PP\u68c9', 'last_change': '2025-12-01',
                               'rated_months': 6, 'rated_liters': 3000}]})
    ck(r1['rows'][0]['days'] == 90, '\u7528\u4f8b1 \u5df2\u7528\u5929\u6570\u5e94\u4e3a 90\uff0c\u5b9e\u4e3a %s' % r1['rows'][0]['days'])
    ck(r1['rows'][0]['time_pct'] == 50.0, '\u7528\u4f8b1 \u65f6\u95f4\u8fdb\u5ea6\u5e94\u4e3a 50.0\uff0c\u5b9e\u4e3a %s' % r1['rows'][0]['time_pct'])
    ck(r1['rows'][0]['pct'] == 50.0, '\u7528\u4f8b1 \u5bff\u547d\u5e94\u53d6\u65f6\u95f4\u8fdb\u5ea6 50.0\uff0c\u5b9e\u4e3a %s' % r1['rows'][0]['pct'])
    ck(r1['rows'][0]['remain_days'] == 90, '\u7528\u4f8b1 \u5269\u4f59\u5929\u6570\u5e94\u4e3a 90\uff0c\u5b9e\u4e3a %s' % r1['rows'][0]['remain_days'])
    ck(r1['rows'][0]['status'] == '\u6b63\u5e38', '\u7528\u4f8b1 \u72b6\u6001\u5e94\u4e3a\u6b63\u5e38\uff0c\u5b9e\u4e3a %s' % r1['rows'][0]['status'])

    # 2 \u6c34\u91cf\u8fdb\u5ea6\u4e3b\u5bfc\uff08\u53d6\u5148\u5230\u8005\uff09
    r2 = calc({'today': '2026-03-01', 'people': 6, 'daily_liters': 40,
               'cartridges': [{'name': '\u524d\u7f6e\u6d3b\u6027\u70ad', 'last_change': '2025-09-01',
                               'rated_months': 12, 'rated_liters': 6000}]})
    ck(abs(r2['rows'][0]['vol_pct'] - 120.7) < 0.2, '\u7528\u4f8b2 \u6c34\u91cf\u8fdb\u5ea6\u5e94\u7ea6 120.7\uff0c\u5b9e\u4e3a %s' % r2['rows'][0]['vol_pct'])
    ck(abs(r2['rows'][0]['pct'] - 120.7) < 0.2, '\u7528\u4f8b2 \u5e94\u53d6\u6c34\u91cf\u8fdb\u5ea6\u7ea6 120.7\uff0c\u5b9e\u4e3a %s' % r2['rows'][0]['pct'])
    ck(r2['rows'][0]['pct'] > r2['rows'][0]['time_pct'], '\u7528\u4f8b2 \u5bff\u547d\u5e94\u53d6\u4e24\u4e2a\u8fdb\u5ea6\u4e2d\u7684\u8f83\u5927\u8005')
    ck(r2['rows'][0]['status'] == '\u8d85\u671f', '\u7528\u4f8b2 \u72b6\u6001\u5e94\u4e3a\u8d85\u671f\uff0c\u5b9e\u4e3a %s' % r2['rows'][0]['status'])
    ck('\u505c\u6b62\u76f4\u996e' in r2['warns'][0], '\u7528\u4f8b2 \u8d85\u671f\u5e94\u63d0\u793a\u505c\u6b62\u76f4\u996e\uff0c\u5b9e\u4e3a %s' % r2['warns'])

    # 3 \u5173\u6ce8\u6863\u4f4d
    r3 = calc({'today': '2026-03-01', 'daily_liters': 10,
               'cartridges': [{'name': '\u540e\u7f6e\u6d3b\u6027\u70ad', 'last_change': '2025-06-01',
                               'rated_months': 12, 'rated_liters': 6000}]})
    ck(r3['rows'][0]['pct'] >= 70.0 and r3['rows'][0]['pct'] < 100.0,
       '\u7528\u4f8b3 \u5bff\u547d\u5e94\u843d\u5728 70 \u5230 100 \u4e4b\u95f4\uff0c\u5b9e\u4e3a %s' % r3['rows'][0]['pct'])
    ck(r3['rows'][0]['status'] == '\u5173\u6ce8', '\u7528\u4f8b3 \u72b6\u6001\u5e94\u4e3a\u5173\u6ce8\uff0c\u5b9e\u4e3a %s' % r3['rows'][0]['status'])

    # 4 \u8131\u76d0\u7387\u826f\u597d
    r4 = calc({'today': '2026-03-01', 'daily_liters': 10, 'tds_in': 260, 'tds_out': 18,
               'cartridges': [{'name': 'RO\u819c', 'last_change': '2024-03-01',
                               'rated_months': 24, 'rated_liters': 12000}]})
    ck(abs(r4['salt_rate'] - 93.08) < 0.05, '\u7528\u4f8b4 \u8131\u76d0\u7387\u5e94\u7ea6 93.08\uff0c\u5b9e\u4e3a %s' % r4['salt_rate'])
    ck('\u826f\u597d' in r4['salt_advice'], '\u7528\u4f8b4 \u8131\u76d0\u7387\u826f\u597d\u5224\u65ad\u9519\u8bef\uff0c\u5b9e\u4e3a %s' % r4['salt_advice'])

    # 5 \u8131\u76d0\u7387\u8fc7\u4f4e\u89e6\u53d1\u6362\u819c\u63d0\u793a
    r5 = calc({'today': '2026-03-01', 'daily_liters': 10, 'tds_in': 200, 'tds_out': 40,
               'cartridges': [{'name': 'RO\u819c', 'last_change': '2024-03-01',
                               'rated_months': 24, 'rated_liters': 12000}]})
    ck(abs(r5['salt_rate'] - 80.0) < 0.05, '\u7528\u4f8b5 \u8131\u76d0\u7387\u5e94\u4e3a 80.0\uff0c\u5b9e\u4e3a %s' % r5['salt_rate'])
    ck(any('\u66f4\u6362 RO \u819c' in w for w in r5['warns']), '\u7528\u4f8b5 \u5e94\u63d0\u793a\u66f4\u6362 RO \u819c\uff0c\u5b9e\u4e3a %s' % r5['warns'])

    # 6 \u901a\u91cf\u6863\u4f4d
    ck(flux_by_people(2) == '400G', '2 \u4eba\u5e94\u5efa\u8bae 400G\uff0c\u5b9e\u4e3a %s' % flux_by_people(2))
    ck(flux_by_people(4) == '600G', '4 \u4eba\u5e94\u5efa\u8bae 600G\uff0c\u5b9e\u4e3a %s' % flux_by_people(4))
    ck(flux_by_people(6) == '800G \u53ca\u4ee5\u4e0a', '6 \u4eba\u5e94\u5efa\u8bae 800G \u53ca\u4ee5\u4e0a\uff0c\u5b9e\u4e3a %s' % flux_by_people(6))

    # 7 \u591a\u7ea7\u6392\u5e8f\u6309\u5bff\u547d\u964d\u5e8f
    r7 = calc({'today': '2026-03-01', 'daily_liters': 12,
               'cartridges': [
                   {'name': '\u65b0\u6362PP\u68c9', 'last_change': '2026-02-01', 'rated_months': 6, 'rated_liters': 3000},
                   {'name': '\u65e7RO\u819c', 'last_change': '2024-03-01', 'rated_months': 24, 'rated_liters': 12000}]})
    ck(r7['rows'][0]['name'] == '\u65e7RO\u819c', '\u7528\u4f8b7 \u5bff\u547d\u9ad8\u7684\u5e94\u6392\u7b2c\u4e00\uff0c\u5b9e\u4e3a %s' % r7['rows'][0]['name'])
    ck(r7['rows'][0]['pct'] >= r7['rows'][1]['pct'], '\u7528\u4f8b7 \u6392\u5e8f\u5e94\u4e3a\u5bff\u547d\u964d\u5e8f')

    # 8 \u672a\u586b\u989d\u5b9a\u603b\u51c0\u6c34\u91cf\u65f6\u53ea\u6309\u65f6\u95f4\u7b97
    r8 = calc({'today': '2026-03-01', 'daily_liters': 12,
               'cartridges': [{'name': 'PP\u68c9', 'last_change': '2025-12-01', 'rated_months': 6}]})
    ck(r8['rows'][0]['vol_pct'] == 0.0, '\u7528\u4f8b8 \u65e0\u989d\u5b9a\u6c34\u91cf\u65f6\u6c34\u91cf\u8fdb\u5ea6\u5e94\u4e3a 0\uff0c\u5b9e\u4e3a %s' % r8['rows'][0]['vol_pct'])
    ck(r8['rows'][0]['pct'] == 50.0, '\u7528\u4f8b8 \u65e0\u989d\u5b9a\u6c34\u91cf\u65f6\u5bff\u547d\u5e94\u7b49\u4e8e\u65f6\u95f4\u8fdb\u5ea6\uff0c\u5b9e\u4e3a %s' % r8['rows'][0]['pct'])

    # 9 \u975e\u6cd5\u8f93\u5165\u5e94\u62a5\u9519
    try:
        calc({'today': '2026-03-01', 'cartridges': []})
        ck(False, '\u7528\u4f8b9 \u7a7a\u6ee4\u82af\u5217\u8868\u5e94\u629b\u9519')
    except ValueError:
        ck(True, '\u7528\u4f8b9 \u7a7a\u6ee4\u82af\u5217\u8868\u5e94\u629b\u9519')
    try:
        calc({'today': '20260301', 'cartridges': [{'name': 'PP\u68c9', 'last_change': '2025-12-01', 'rated_months': 6}]})
        ck(False, '\u7528\u4f8b9 \u975e\u6cd5\u65e5\u671f\u5e94\u629b\u9519')
    except ValueError:
        ck(True, '\u7528\u4f8b9 \u975e\u6cd5\u65e5\u671f\u5e94\u629b\u9519')
    try:
        calc({'today': '2026-03-01',
              'cartridges': [{'name': 'PP\u68c9', 'last_change': '2026-06-01', 'rated_months': 6}]})
        ck(False, '\u7528\u4f8b9 \u4e0a\u6b21\u66f4\u6362\u65e5\u671f\u665a\u4e8e\u4eca\u65e5\u5e94\u629b\u9519')
    except ValueError:
        ck(True, '\u7528\u4f8b9 \u4e0a\u6b21\u66f4\u6362\u65e5\u671f\u665a\u4e8e\u4eca\u65e5\u5e94\u629b\u9519')

    # 10 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r2)
    ck('\u66f4\u6362\u987a\u5e8f' in md, 'Markdown \u8f93\u51fa\u5e94\u5305\u542b\u66f4\u6362\u987a\u5e8f\u8868')
    ck('\u4eba\u5de5\u786e\u8ba4' in md, 'Markdown \u8f93\u51fa\u5e94\u5305\u542b\u4eba\u5de5\u786e\u8ba4\u6e05\u5355')
    j = json.loads(render_json(r2))
    ck(j['overdue'] == ['\u524d\u7f6e\u6d3b\u6027\u70ad'], 'JSON \u8f93\u51fa\u7684\u8d85\u671f\u5217\u8868\u5e94\u5305\u542b\u524d\u7f6e\u6d3b\u6027\u70ad\uff0c\u5b9e\u4e3a %s' % j['overdue'])

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u65f6\u95f4\u8fdb\u5ea6/\u6c34\u91cf\u8fdb\u5ea6/\u53d6\u5148\u5230\u8005/\u72b6\u6001\u4e09\u6863/\u5269\u4f59\u5929\u6570/\u8131\u76d0\u7387/\u6362\u819c\u63d0\u793a/\u901a\u91cf\u6863\u4f4d/\u591a\u7ea7\u6392\u5e8f/\u7f3a\u6c34\u91cf\u5bb9\u9519/\u975e\u6cd5\u8f93\u5165/\u8f93\u51fa\u7ed3\u6784'
               % checks)
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u51c0\u6c34\u5668\u6ee4\u82af\u66f4\u6362\u5468\u671f\u6838\u67e5')
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
            print('ERROR --file \u4e0d\u5b58\u5728')
            return 2
        raw = open(a.file, 'r', encoding='utf-8', errors='replace').read()
    if not raw.strip():
        print('ERROR \u9700\u8981 --file \u6216 --text')
        return 2

    try:
        data = json.loads(raw)
    except ValueError:
        print('ERROR JSON \u89e3\u6790\u5931\u8d25')
        return 2

    try:
        r = calc(data)
    except ValueError as e:
        print('ERROR %s' % e)
        return 2

    out = render_md(r) if a.format == 'md' else render_json(r)
    out_dir = os.path.dirname(os.path.abspath(__file__))
    target = a.out or os.path.join(out_dir, '_last_result.txt')
    with open(target, 'w', encoding='utf-8') as f:
        f.write(out + '\n')
    print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % target)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
