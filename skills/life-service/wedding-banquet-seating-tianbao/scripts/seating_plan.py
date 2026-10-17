# -*- coding: utf-8 -*-
"""\u5a5a\u5bb4\u684c\u6b21\u4e0e\u5e2d\u4f4d\u6392\u5e03\u6838\u7b97\uff1a\u6309\u4eba\u6570\u7b97\u684c\u6570\uff0c\u6309\u5206\u533a\u6392\u684c\u53f7\uff0c\u8f93\u51fa\u684c\u6b21\u65b9\u6848\u6e05\u5355\u3002

\u7528\u6cd5:
  python seating_plan.py --file guests.json [--out \u684c\u6b21\u65b9\u6848.md] [--format json]
  python seating_plan.py --selftest
"""
import argparse
import json
import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u5206\u533a\u987a\u5e8f\u5373\u684c\u53f7\u987a\u5e8f\uff1a\u4e3b\u684c\u4e4b\u540e\u4f9d\u6b21\u6392\u5f00
ZONE_ORDER = [
    ('groom_family', '\u7537\u65b9\u4eb2\u5c5e', '\u4e3b\u684c\u5de6\u4fa7\u9760\u524d'),
    ('bride_family', '\u5973\u65b9\u4eb2\u5c5e', '\u4e3b\u684c\u53f3\u4fa7\u9760\u524d'),
    ('colleague', '\u540c\u4e8b', '\u4e2d\u6bb5\uff0c\u9886\u5bfc\u684c\u76f8\u5bf9\u9760\u524d'),
    ('classmate', '\u540c\u5b66', '\u4e2d\u6bb5\u504f\u540e'),
    ('friend', '\u670b\u53cb', '\u9760\u540e\uff0c\u8fd1\u51fa\u53e3\u4e0e\u97f3\u54cd'),
    ('other', '\u5176\u4ed6', '\u673a\u52a8\u533a'),
]

ZONE_KEYS = [z[0] for z in ZONE_ORDER]
ZONE_NAME = dict((z[0], z[1]) for z in ZONE_ORDER)
ZONE_POS = dict((z[0], z[2]) for z in ZONE_ORDER)


def ceil_div(a, b):
    """\u5411\u4e0a\u53d6\u6574\u9664\u6cd5\uff0cb \u5fc5\u987b\u4e3a\u6b63\u6574\u6570\u3002"""
    if b <= 0:
        raise ValueError('\u6bcf\u684c\u5ea7\u6570\u5fc5\u987b\u4e3a\u6b63\u6574\u6570')
    return int(math.ceil(float(a) / float(b)))


def buffer_tables(base, rate):
    """\u5907\u7528\u684c\uff1a\u6309\u57fa\u7840\u684c\u6570\u7684\u6bd4\u4f8b\u7b97\uff0c\u4e0b\u9650 1 \u684c\uff0c\u4e0a\u9650 2 \u684c\u3002

    \u89c4\u5219\u53e3\u5f84\uff1a\u603b\u684c\u6570 10 \u684c\u4ee5\u4e0b\u52a0 1 \u684c\uff0c10-25 \u684c\u52a0 1-2 \u684c\uff0c25 \u684c\u4ee5\u4e0a\u4e0d\u8d85\u8fc7 2 \u684c\u3002
    """
    n = int(math.ceil(base * rate))
    if n < 1:
        n = 1
    if n > 2:
        n = 2
    return n


def plan(data):
    total = int(data.get('total', 0))
    seats = int(data.get('seats_per_table', 10))
    main_seats = int(data.get('main_table_seats', seats))
    main_people = int(data.get('main_table_people', main_seats))
    rate = float(data.get('buffer_rate', 0.06))
    children = int(data.get('children', 0))
    zones_in = data.get('zones', {}) or {}

    if seats <= 0:
        raise ValueError('\u6bcf\u684c\u5ea7\u6570\u5fc5\u987b\u4e3a\u6b63\u6574\u6570')
    if total <= 0:
        raise ValueError('\u603b\u4eba\u6570\u5fc5\u987b\u4e3a\u6b63\u6574\u6570')

    warns = []
    if main_people > main_seats:
        warns.append('\u4e3b\u684c\u4eba\u6570 %d \u8d85\u8fc7\u4e3b\u684c\u5ea7\u6570 %d\uff0c\u8bf7\u51cf\u5c11\u4e3b\u684c\u4eba\u6570\u6216\u6539\u7528\u66f4\u5927\u684c\u578b' % (main_people, main_seats))
        main_people = main_seats
    if children > total:
        warns.append('\u513f\u7ae5\u4eba\u6570\u5927\u4e8e\u603b\u4eba\u6570\uff0c\u6570\u636e\u53ef\u80fd\u6709\u8bef')

    rest = total - main_people
    if rest < 0:
        warns.append('\u603b\u4eba\u6570\u5c0f\u4e8e\u4e3b\u684c\u4eba\u6570\uff0c\u8bf7\u6838\u5bf9\u4eba\u6570')
        rest = 0

    zone_sum = 0
    for k in zones_in:
        zone_sum += int(zones_in[k])
    if zone_sum != rest:
        warns.append('\u5404\u5206\u533a\u4eba\u6570\u5408\u8ba1 %d \u4e0e\u300c\u603b\u4eba\u6570 - \u4e3b\u684c\u4eba\u6570\u300d%d \u4e0d\u4e00\u81f4\uff0c\u5dee %d \u4eba\uff0c\u8bf7\u6838\u5bf9\u540d\u5355'
                     % (zone_sum, rest, zone_sum - rest))

    # \u9010\u533a\u8ba1\u7b97\u684c\u6570\u5e76\u5206\u914d\u684c\u53f7
    rows = []
    num = 1
    main_row = {
        'no': '1',
        'zone': '\u4e3b\u684c',
        'zone_key': 'main',
        'people': main_people,
        'seats': main_seats,
        'tables': 1,
        'range': '1',
        'pos': '\u5c45\u4e2d\u6b63\u5bf9\u821e\u53f0',
        'note': '\u65b0\u4eba\u3001\u53cc\u65b9\u7236\u6bcd\u3001\u7956\u8f88\u3001\u8bc1\u5a5a\u4eba',
    }
    rows.append(main_row)
    num = 2

    zone_tables = 0
    for k in ZONE_ORDER:
        key = k[0]
        n = int(zones_in.get(key, 0))
        if n <= 0:
            continue
        t = ceil_div(n, seats)
        start = num
        end = num + t - 1
        rng = str(start) if t == 1 else '%d-%d' % (start, end)
        rem = n % seats
        if rem == 0:
            note = '\u6574\u684c\u6392\u6ee1'
        else:
            note = '\u6700\u540e\u4e00\u684c %d \u4eba\u6709\u7a7a\u4f4d\uff0c\u5efa\u8bae\u5e76\u5165\u540c\u533a\u4f59\u6570\u6216\u5355\u8bbe\u673a\u52a8\u684c' % rem
        rows.append({
            'no': rng,
            'zone': ZONE_NAME[key],
            'zone_key': key,
            'people': n,
            'seats': seats,
            'tables': t,
            'range': rng,
            'pos': ZONE_POS[key],
            'note': note,
        })
        zone_tables += t
        num = end + 1

    unknown = [k for k in zones_in if k not in ZONE_KEYS]
    if unknown:
        warns.append('\u672a\u8bc6\u522b\u7684\u5206\u533a\u5b57\u6bb5: %s\uff08\u53ef\u7528\u5206\u533a: %s\uff09' % ('\u3001'.join(unknown), '\u3001'.join(ZONE_KEYS)))

    base_tables = 1 + zone_tables
    buf = buffer_tables(base_tables, rate)
    total_tables = base_tables + buf

    # \u4ea4\u53c9\u6821\u9a8c\uff1a\u76f4\u63a5\u6309\u603b\u4eba\u6570\u4f30\u7b97\u7684\u684c\u6570
    rough = ceil_div(total, seats)
    if rough > base_tables:
        warns.append('\u6309\u603b\u4eba\u6570\u76f4\u63a5\u4f30\u7b97\u9700 %d \u684c\uff0c\u5206\u533a\u6392\u5e03\u4e3a %d \u684c\uff0c\u8bf4\u660e\u5b58\u5728\u7a7a\u4f4d\u672a\u6d88\u5316\uff0c\u5efa\u8bae\u6838\u5bf9\u4f59\u6570\u5904\u7406'
                     % (rough, base_tables))

    return {
        'total': total,
        'children': children,
        'seats_per_table': seats,
        'main_table_seats': main_seats,
        'main_table_people': main_people,
        'zone_sum': zone_sum,
        'rest': rest,
        'base_tables': base_tables,
        'buffer_tables': buf,
        'total_tables': total_tables,
        'rows': rows,
        'warns': warns,
    }


def render_md(r):
    L = []
    L.append('# \u5a5a\u5bb4\u684c\u6b21\u65b9\u6848')
    L.append('')
    L.append('## \u4e00\u3001\u6570\u91cf\u6838\u7b97')
    L.append('')
    L.append('| \u9879 | \u6570\u503c |')
    L.append('|---|---|')
    L.append('| \u5bbe\u5ba2\u603b\u4eba\u6570 | %d \u4eba |' % r['total'])
    L.append('| \u5176\u4e2d\u513f\u7ae5 | %d \u4eba |' % r['children'])
    L.append('| \u6bcf\u684c\u5ea7\u6570 | %d \u4eba |' % r['seats_per_table'])
    L.append('| \u4e3b\u684c\u5ea7\u6570 | %d \u4eba |' % r['main_table_seats'])
    L.append('| \u4e3b\u684c\u4eba\u6570 | %d \u4eba |' % r['main_table_people'])
    L.append('| \u5206\u533a\u4eba\u6570\u5408\u8ba1 | %d \u4eba |' % r['zone_sum'])
    L.append('| \u57fa\u7840\u684c\u6570 | %d \u684c |' % r['base_tables'])
    L.append('| \u5907\u7528\u684c | %d \u684c |' % r['buffer_tables'])
    L.append('| \u5efa\u8bae\u62a5\u9152\u5e97\u684c\u6570 | **%d \u684c** |' % r['total_tables'])
    L.append('')
    L.append('## \u4e8c\u3001\u684c\u6b21\u6392\u5e03')
    L.append('')
    L.append('| \u684c\u53f7 | \u533a\u57df | \u4eba\u6570 | \u684c\u6570 | \u4f4d\u7f6e | \u5907\u6ce8 |')
    L.append('|---|---|---|---|---|---|')
    for row in r['rows']:
        L.append('| %s | %s | %d | %d | %s | %s |'
                 % (row['range'], row['zone'], row['people'], row['tables'], row['pos'], row['note']))
    L.append('')
    L.append('## \u4e09\u3001\u63d0\u9192')
    L.append('')
    if r['warns']:
        for w in r['warns']:
            L.append('- %s' % w)
    else:
        L.append('- \u5206\u533a\u4eba\u6570\u4e0e\u603b\u4eba\u6570\u4e00\u81f4\uff0c\u672a\u53d1\u73b0\u6570\u91cf\u51b2\u7a81')
    L.append('')
    L.append('## \u56db\u3001\u4eba\u5de5\u786e\u8ba4\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] \u5360\u5ea7\u4eba\u6570\u5df2\u6309 3 \u5c81\u4ee5\u4e0a\u5360\u5ea7\u53e3\u5f84\u6838\u51c6\uff0c\u5e76\u63d0\u524d 3 \u5929\u4e8c\u6b21\u786e\u8ba4')
    L.append('- [ ] \u6bcf\u684c\u5ea7\u6570\u4e0e\u9152\u5e97\u684c\u578b\u6838\u5bf9\u8fc7')
    L.append('- [ ] \u5907\u7528\u684c\u4e0d\u5360\u7528\u6d88\u9632\u901a\u9053\uff08\u4ee5\u9152\u5e97\u73b0\u573a\u6761\u4ef6\u4e0e\u6d88\u9632\u8981\u6c42\u4e3a\u51c6\uff09')
    L.append('- [ ] \u957f\u8f88\u3001\u9886\u5bfc\u672a\u5b89\u6392\u5728\u6700\u540e\u4e00\u684c\u3001\u95e8\u53e3\u3001\u4e0a\u83dc\u53e3')
    L.append('- [ ] \u5173\u7cfb\u4e0d\u548c\u7684\u4eba\u5458\u672a\u540c\u684c\uff08\u7531\u65b0\u4eba\u53ca\u53cc\u65b9\u5bb6\u5ead\u786e\u8ba4\uff09')
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

    # 1 \u57fa\u7840\u684c\u6570\u4e0e\u5206\u533a\u6392\u5e03
    r1 = plan({'total': 168, 'seats_per_table': 10, 'main_table_seats': 12, 'main_table_people': 10,
               'zones': {'groom_family': 46, 'bride_family': 42, 'colleague': 38,
                         'classmate': 22, 'friend': 10}})
    ck(r1['rest'] == 158, '\u7528\u4f8b1 \u5206\u533a\u5e94\u5269 158 \u4eba\uff0c\u5b9e\u4e3a %d' % r1['rest'])
    ck(r1['zone_sum'] == 158, '\u7528\u4f8b1 \u5206\u533a\u5408\u8ba1\u5e94\u4e3a 158\uff0c\u5b9e\u4e3a %d' % r1['zone_sum'])
    ck(r1['base_tables'] == 19, '\u7528\u4f8b1 \u57fa\u7840\u684c\u6570\u5e94\u4e3a 19\uff0c\u5b9e\u4e3a %d' % r1['base_tables'])
    ck(r1['total_tables'] == r1['base_tables'] + r1['buffer_tables'], '\u7528\u4f8b1 \u603b\u684c\u6570\u4e0d\u7b49\u4e8e\u57fa\u7840+\u5907\u7528')

    # 2 \u5206\u533a\u684c\u6570\u5411\u4e0a\u53d6\u6574
    z = dict((row['zone_key'], row['tables']) for row in r1['rows'])
    ck(z.get('groom_family') == 5, '46 \u4eba 10 \u4eba\u4e00\u684c\u5e94\u4e3a 5 \u684c\uff0c\u5b9e\u4e3a %s' % z.get('groom_family'))
    ck(z.get('bride_family') == 5, '42 \u4eba 10 \u4eba\u4e00\u684c\u5e94\u4e3a 5 \u684c\uff0c\u5b9e\u4e3a %s' % z.get('bride_family'))
    ck(z.get('colleague') == 4, '38 \u4eba 10 \u4eba\u4e00\u684c\u5e94\u4e3a 4 \u684c\uff0c\u5b9e\u4e3a %s' % z.get('colleague'))
    ck(z.get('classmate') == 3, '22 \u4eba 10 \u4eba\u4e00\u684c\u5e94\u4e3a 3 \u684c\uff0c\u5b9e\u4e3a %s' % z.get('classmate'))
    ck(z.get('friend') == 1, '10 \u4eba 10 \u4eba\u4e00\u684c\u5e94\u4e3a 1 \u684c\uff0c\u5b9e\u4e3a %s' % z.get('friend'))

    # 3 \u684c\u53f7\u533a\u95f4\u8fde\u7eed\u4e14\u4e0d\u91cd\u53e0
    nums = [row['range'] for row in r1['rows']]
    ck(nums[0] == '1', '\u4e3b\u684c\u684c\u53f7\u5e94\u4e3a 1\uff0c\u5b9e\u4e3a %s' % nums[0])
    ck(nums[1].startswith('2'), '\u7b2c\u4e8c\u533a\u5e94\u4ece 2 \u53f7\u5f00\u59cb\uff0c\u5b9e\u4e3a %s' % nums[1])
    last = r1['rows'][-1]['range']
    ck(last.endswith('19'), '\u6700\u540e\u4e00\u533a\u5e94\u6392\u5230 19 \u53f7\uff0c\u5b9e\u4e3a %s' % last)

    # 4 \u5907\u7528\u684c\u4e0a\u9650 2 \u684c
    r2 = plan({'total': 400, 'seats_per_table': 10, 'buffer_rate': 0.5,
               'zones': {'other': 388}})
    ck(r2['buffer_tables'] == 2, '\u5907\u7528\u684c\u6bd4\u4f8b\u518d\u9ad8\u4e5f\u5e94\u5c01\u9876 2 \u684c\uff0c\u5b9e\u4e3a %d' % r2['buffer_tables'])

    # 5 \u5907\u7528\u684c\u4e0b\u9650 1 \u684c
    r3 = plan({'total': 20, 'seats_per_table': 10, 'buffer_rate': 0.0,
               'zones': {'friend': 10}})
    ck(r3['buffer_tables'] == 1, '\u5907\u7528\u684c\u6bd4\u4f8b\u6781\u4f4e\u65f6\u4e5f\u5e94\u81f3\u5c11 1 \u684c\uff0c\u5b9e\u4e3a %d' % r3['buffer_tables'])

    # 6 \u4eba\u6570\u4e0e\u5206\u533a\u4e0d\u4e00\u81f4\u65f6\u62a5\u8b66
    r4 = plan({'total': 100, 'seats_per_table': 10, 'zones': {'friend': 50}})
    ck(any('\u4e0d\u4e00\u81f4' in w for w in r4['warns']), '\u4eba\u6570\u4e0e\u5206\u533a\u4e0d\u4e00\u81f4\u65f6\u5e94\u62a5\u8b66\uff0c\u5b9e\u4e3a %s' % r4['warns'])

    # 7 \u4e3b\u684c\u8d85\u5458\u62a5\u8b66
    r5 = plan({'total': 60, 'seats_per_table': 10, 'main_table_seats': 10,
               'main_table_people': 14, 'zones': {'friend': 50}})
    ck(any('\u4e3b\u684c\u4eba\u6570' in w for w in r5['warns']), '\u4e3b\u684c\u8d85\u5458\u65f6\u5e94\u62a5\u8b66\uff0c\u5b9e\u4e3a %s' % r5['warns'])
    ck(r5['main_table_people'] == 10, '\u4e3b\u684c\u8d85\u5458\u65f6\u5e94\u88ab\u4fee\u6b63\u4e3a\u5ea7\u6570\u4e0a\u9650\uff0c\u5b9e\u4e3a %d' % r5['main_table_people'])

    # 8 \u7a7a\u5206\u533a\u4e0d\u751f\u6210\u684c
    r6 = plan({'total': 30, 'seats_per_table': 10, 'main_table_people': 10,
               'zones': {'groom_family': 20, 'colleague': 0}})
    ck(len(r6['rows']) == 2, '\u7a7a\u5206\u533a\u4e0d\u5e94\u751f\u6210\u684c\uff0c\u884c\u6570\u5b9e\u4e3a %d' % len(r6['rows']))

    # 9 \u975e\u6cd5\u6bcf\u684c\u5ea7\u6570\u5e94\u62a5\u9519
    try:
        plan({'total': 30, 'seats_per_table': 0, 'zones': {'friend': 20}})
        ck(False, '\u6bcf\u684c\u5ea7\u6570\u4e3a 0 \u65f6\u5e94\u629b\u9519')
    except ValueError:
        ck(True, '\u6bcf\u684c\u5ea7\u6570\u4e3a 0 \u65f6\u5e94\u629b\u9519')

    # 10 \u672a\u8bc6\u522b\u5206\u533a\u5b57\u6bb5\u62a5\u8b66
    r7 = plan({'total': 30, 'seats_per_table': 10, 'main_table_people': 10,
               'zones': {'friend': 10, 'xyz': 10}})
    ck(any('\u672a\u8bc6\u522b' in w for w in r7['warns']), '\u672a\u8bc6\u522b\u5206\u533a\u5b57\u6bb5\u65f6\u5e94\u62a5\u8b66\uff0c\u5b9e\u4e3a %s' % r7['warns'])

    # 11 JSON \u4e0e md \u8f93\u51fa\u7ed3\u6784
    j = json.loads(render_json(r1))
    ck(j['total_tables'] == r1['total_tables'], 'JSON \u8f93\u51fa\u7684\u603b\u684c\u6570\u5e94\u4e0e\u8ba1\u7b97\u7ed3\u679c\u4e00\u81f4')
    md = render_md(r1)
    ck('\u5efa\u8bae\u62a5\u9152\u5e97\u684c\u6570' in md, 'Markdown \u8f93\u51fa\u5e94\u5305\u542b\u5efa\u8bae\u62a5\u9152\u5e97\u684c\u6570')
    ck('\u4eba\u5de5\u786e\u8ba4' in md, 'Markdown \u8f93\u51fa\u5e94\u5305\u542b\u4eba\u5de5\u786e\u8ba4\u6e05\u5355')

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u57fa\u7840\u684c\u6570/\u5206\u533a\u53d6\u6574/\u684c\u53f7\u8fde\u7eed\u6027/\u5907\u7528\u684c\u4e0a\u4e0b\u9650/\u4eba\u6570\u4e0d\u4e00\u81f4\u62a5\u8b66/\u4e3b\u684c\u8d85\u5458/\u7a7a\u5206\u533a/\u975e\u6cd5\u5ea7\u6570/\u672a\u77e5\u5206\u533a/\u8f93\u51fa\u7ed3\u6784'
               % checks)
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u5a5a\u5bb4\u684c\u6b21\u4e0e\u5e2d\u4f4d\u6392\u5e03\u6838\u7b97')
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
        r = plan(data)
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
