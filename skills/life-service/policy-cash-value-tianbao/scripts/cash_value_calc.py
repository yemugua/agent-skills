# -*- coding: utf-8 -*-
"""Policy cash value and surrender loss calculator.

Usage:
  python cash_value_calc.py --file case.json [--out result.md] [--format json]
  python cash_value_calc.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def money(x):
    return round(float(x) + 1e-9, 2)


def pct(x):
    return round(float(x) * 100.0 + 1e-9, 4)


def calc(data):
    years = data.get('policy_years', []) or []
    if not years:
        raise ValueError('policy_years must not be empty')
    rows = []
    seen = set()
    for y in years:
        yv = int(y.get('year'))
        cv = float(y.get('cash_value', 0))
        paid = float(y.get('paid_cumulative', 0))
        if yv <= 0:
            raise ValueError('policy year must be > 0')
        if yv in seen:
            raise ValueError('duplicate policy year %d' % yv)
        seen.add(yv)
        if cv < 0:
            raise ValueError('cash_value must be >= 0 for year %d' % yv)
        if paid < 0:
            raise ValueError('paid_cumulative must be >= 0 for year %d' % yv)
        loss = money(max(0.0, paid - cv))
        rate = None if paid <= 0 else pct(loss / paid)
        rows.append({
            'year': yv,
            'cash_value': money(cv),
            'paid_cumulative': money(paid),
            'surrender_loss': loss,
            'loss_rate_pct': rate,
            'recovered': cv >= paid,
        })
    rows.sort(key=lambda r: r['year'])

    current = int(data.get('current_year', rows[-1]['year']))
    if current not in seen:
        raise ValueError('current_year %d is not in the table' % current)

    in_cooling = bool(data.get('in_cooling_off', False))
    cur = [r for r in rows if r['year'] == current][0]

    if in_cooling:
        refund = cur['paid_cumulative']
        loss = 0.0
        rate = 0.0
        basis = ('Inside cooling-off. The refund scope and any deduction are '
                 'stipulated by the contract. The figures below show the '
                 'paid-premium ceiling only, NOT a promise of a full refund.')
    else:
        refund = cur['cash_value']
        loss = cur['surrender_loss']
        rate = cur['loss_rate_pct'] if cur['loss_rate_pct'] is not None else 0.0
        basis = ('After cooling-off. Refundable is the cash value row for '
                 'policy year %d taken from the contract cash value table.'
                 % current)

    recovered_years = [r['year'] for r in rows if r['recovered']]
    first_recovered = recovered_years[0] if recovered_years else None

    notes = []
    notes.append('Cash value is read from the contract cash value table. It is '
                 'NOT the same as premiums paid.')
    notes.append('Surrender loss = premiums paid - refundable amount. Formula '
                 'per policy year is shown above.')
    if in_cooling:
        notes.append('Cooling-off length follows the contract. Do NOT state '
                     'that the whole premium is refunded; the refund scope and '
                     'any deduction are stipulated by the contract wording.')
    else:
        notes.append('Cooling-off has expired. Surrendering during the '
                     'premium-paying period returns the cash value row only. '
                     'Future unpaid premiums are NOT refunded.')
    if first_recovered is None:
        notes.append('No policy year on the supplied table has recovered yet. '
                     'Do NOT say a break-even year exists.')
    else:
        notes.append('First break-even year on the supplied table: %d. Note '
                     'that break-even does NOT mean surrendering is the right '
                     'choice; it is only a data point.' % first_recovered)
    notes.append('Partial withdrawal keeps the policy in force, but the '
                 'remaining cash value and later benefits change. Do NOT treat '
                 'it as surrender.')
    notes.append('Reduced paid-up keeps the policy in force with a LOWER sum '
                 'insured. Do NOT treat it as surrender.')
    notes.append('Policy loan is not a withdrawal: it must be repaid with '
                 'interest, and failing to repay may affect the policy status.')
    notes.append('This script does not recommend surrendering and does not '
                 'recommend keeping the policy. It reports figures only.')

    return {
        'current_year': current,
        'in_cooling_off': in_cooling,
        'cash_value_current': cur['cash_value'],
        'paid_cumulative_current': cur['paid_cumulative'],
        'refundable': money(refund),
        'surrender_loss': money(loss),
        'loss_rate_pct': money(rate) if rate is not None else None,
        'recovered_current': cur['recovered'],
        'first_break_even_year': first_recovered,
        'basis': basis,
        'rows': rows,
        'notes': notes,
        'must_confirm': [
            'cash value table taken from the policy or its attachment, not '
            'from a marketing chart',
            'policy year numbering starts on the contract start date, not on '
            'the number of premiums paid',
            'the row for the current policy year, not the latest available row',
            'multiple benefits or tiers read separately and then added up',
            'premiums paid taken from actual payment records, unpaid instalments '
            'excluded',
            'policy status checked: in force, lapsed, or reinstated',
            'cooling-off length taken from the contract wording',
            'inside cooling-off: refund scope and deduction items per contract',
            'partial withdrawal: limit, cap and count per contract, and the '
            'change to remaining benefits',
            'reduced paid-up: the new sum insured after the change',
            'policy loan: interest rate and repayment term',
        ],
    }


def to_md(r):
    L = []
    L.append('# Policy Cash Value and Surrender Loss')
    L.append('')
    L.append('| Item | Value |')
    L.append('|---|---|')
    L.append('| Current policy year | %d |' % r['current_year'])
    L.append('| Inside cooling-off | %s |'
             % ('YES' if r['in_cooling_off'] else 'NO'))
    L.append('| Cash value (table row) | %.2f |' % r['cash_value_current'])
    L.append('| Premiums paid (cumulative) | %.2f |' % r['paid_cumulative_current'])
    L.append('| Refundable | %.2f |' % r['refundable'])
    L.append('| Surrender loss | %.2f |' % r['surrender_loss'])
    L.append('| Loss rate | %s |'
             % ('%.4f%%' % r['loss_rate_pct'] if r['loss_rate_pct'] is not None
                else 'N/A'))
    L.append('| Break-even at this year | %s |'
             % ('YES' if r['recovered_current'] else 'NO'))
    L.append('| First break-even year on the table | %s |'
             % (r['first_break_even_year']
                if r['first_break_even_year'] is not None else 'none'))
    L.append('')
    L.append('- Basis: %s' % r['basis'])
    L.append('')
    L.append('## Year by year')
    L.append('')
    L.append('| Policy year | Cash value | Premiums paid | Surrender loss | '
             'Loss rate | Break-even |')
    L.append('|---|---|---|---|---|---|')
    for y in r['rows']:
        L.append('| %d | %.2f | %.2f | %.2f | %s | %s |'
                 % (y['year'], y['cash_value'], y['paid_cumulative'],
                    y['surrender_loss'],
                    '%.4f%%' % y['loss_rate_pct']
                    if y['loss_rate_pct'] is not None else 'N/A',
                    'yes' if y['recovered'] else 'no'))
    L.append('')
    L.append('## Notes')
    L.append('')
    for n in r['notes']:
        L.append('- %s' % n)
    L.append('')
    L.append('## Must be confirmed against the contract')
    L.append('')
    for m in r['must_confirm']:
        L.append('- [ ] %s' % m)
    L.append('')
    L.append('Static computation on the supplied cash value table. Cash value '
             'follows the contract table; cooling-off length and the refund '
             'scope follow the contract wording; surrender, partial '
             'withdrawal, reduced paid-up and policy loans follow the contract '
             'and the actual process of the insurer. No product is recommended. '
             'This script does not advise whether to surrender.')
    return '\n'.join(L)


def run_selftest():
    ok = 0
    fail = []

    def check(cond, msg):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fail.append(msg)

    table = [
        {'year': 1, 'cash_value': 800, 'paid_cumulative': 5000},
        {'year': 2, 'cash_value': 1800, 'paid_cumulative': 10000},
        {'year': 3, 'cash_value': 3200, 'paid_cumulative': 15000},
        {'year': 4, 'cash_value': 5000, 'paid_cumulative': 20000},
        {'year': 5, 'cash_value': 7200, 'paid_cumulative': 20000},
    ]

    # 1: surrender loss arithmetic on the current row
    r = calc({'policy_years': table, 'current_year': 3})
    check(abs(r['cash_value_current'] - 3200.0) < 0.01,
          'year 3 cash value should be 3200, got %s' % r['cash_value_current'])
    check(abs(r['surrender_loss'] - 11800.0) < 0.01,
          'loss should be 15000-3200=11800, got %s' % r['surrender_loss'])
    check(abs(r['loss_rate_pct'] - (11800.0 / 15000.0 * 100)) < 0.01,
          'loss rate should be 78.6667%%, got %s' % r['loss_rate_pct'])
    check(r['recovered_current'] is False, 'year 3 has not recovered')

    # 2: break-even detection, on a table that actually reaches break-even
    check(r['first_break_even_year'] is None,
          'the base table never reaches break-even, got %s'
          % r['first_break_even_year'])
    t_be = [dict(x) for x in table]
    t_be[3] = {'year': 4, 'cash_value': 21000, 'paid_cumulative': 20000}
    r_be = calc({'policy_years': t_be, 'current_year': 4})
    check(r_be['first_break_even_year'] == 4,
          'first break-even should be year 4, got %s'
          % r_be['first_break_even_year'])
    check(r_be['recovered_current'] is True,
          'year 4 with 21000 cash value against 20000 paid is break-even')
    check(any('does NOT mean surrendering is the right choice' in n
              for n in r_be['notes']),
          'break-even must not be turned into advice')

    # 3: no break-even row -> must not fabricate a year
    t2 = [dict(x) for x in table]
    t2[3] = {'year': 4, 'cash_value': 1500, 'paid_cumulative': 20000}
    t2[4] = {'year': 5, 'cash_value': 2000, 'paid_cumulative': 20000}
    r2 = calc({'policy_years': t2})
    check(r2['first_break_even_year'] is None,
          'no break-even row must yield None')
    check(any('Do NOT say a break-even year exists' in n for n in r2['notes']),
          'missing break-even must be stated, not invented')

    # 4: cooling-off branch uses the paid-premium ceiling and refuses the promise
    r3 = calc({'policy_years': table, 'current_year': 1, 'in_cooling_off': True})
    check(abs(r3['refundable'] - 5000.0) < 0.01,
          'inside cooling-off the ceiling shown is premiums paid')
    check(r3['surrender_loss'] == 0.0,
          'the ceiling itself shows no loss')
    check('NOT a promise of a full refund' in r3['basis'],
          'cooling-off basis must refuse the full-refund promise')
    check(any('Do NOT state that the whole premium is refunded' in n
              for n in r3['notes']),
          'cooling-off note must refuse the full-refund promise')

    # 5: loss is never negative even with excess cash value
    t3 = [{'year': 1, 'cash_value': 9000, 'paid_cumulative': 5000}]
    r4 = calc({'policy_years': t3, 'current_year': 1})
    check(r4['surrender_loss'] == 0.0, 'excess cover must clamp loss at 0')
    check(r4['recovered_current'] is True, 'excess cover means recovered')

    # 6: current_year must exist in the table
    try:
        calc({'policy_years': table, 'current_year': 9})
        check(False, 'a missing current_year must be rejected')
    except ValueError:
        check(True, 'missing current_year rejected')

    # 7: rows are sorted, and default current_year is the last row
    t4 = list(reversed(table))
    r5 = calc({'policy_years': t4})
    check([y['year'] for y in r5['rows']] == [1, 2, 3, 4, 5],
          'rows must be sorted by policy year')
    check(r5['current_year'] == 5, 'default current_year should be the last row')

    # 8: cash value is never treated as premiums paid
    r6 = calc({'policy_years': table, 'current_year': 5})
    check(r6['cash_value_current'] == 7200.0
          and r6['paid_cumulative_current'] == 20000.0,
          'cash value and premiums paid must stay separate values')
    check(r6['refundable'] == 7200.0,
          'after cooling-off the refundable amount is the cash value row')

    # 9: wording guards
    joined = ' '.join(r['notes']).lower()
    check('not the same as premiums paid' in joined,
          'the core distinction must be stated in the notes')
    check('do not treat it as surrender' in joined,
          'partial withdrawal and reduced paid-up must not be called surrender')
    check('is not a withdrawal' in joined,
          'policy loan must not be called a withdrawal')
    check('full refund' not in joined.replace(
        'do not state that the whole premium is refunded', ''),
        'no full-refund promise may appear')
    check('guaranteed' not in joined, 'no guarantee wording may appear')

    # 10: bad inputs rejected
    for bad in ({'policy_years': []},
                {'policy_years': [{'year': 0, 'cash_value': 1,
                                   'paid_cumulative': 1}]},
                {'policy_years': [{'year': 1, 'cash_value': -1,
                                   'paid_cumulative': 1}]},
                {'policy_years': [{'year': 1, 'cash_value': 1,
                                   'paid_cumulative': -1}]},
                {'policy_years': [{'year': 1, 'cash_value': 1,
                                   'paid_cumulative': 1},
                                  {'year': 1, 'cash_value': 2,
                                   'paid_cumulative': 2}]}):
        try:
            calc(bad)
            check(False, 'bad input must be rejected: %s' % bad)
        except ValueError:
            check(True, 'bad input rejected')

    # 11: markdown rendering
    md = to_md(calc({'policy_years': table, 'current_year': 3}))
    check('Year by year' in md and 'Must be confirmed' in md,
          'markdown output must carry the year table and the confirm list')

    lines = ['SELFTEST %s (%d passed, %d failed)'
             % ('OK' if not fail else 'FAIL', ok, len(fail))]
    for f in fail:
        lines.append('FAILED: %s' % f)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '_selftest_result.txt')
    open(out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    return 0 if not fail else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file')
    ap.add_argument('--text')
    ap.add_argument('--out')
    ap.add_argument('--format', default='md')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        return run_selftest()
    if a.file:
        data = json.load(open(a.file, 'r', encoding='utf-8'))
    elif a.text:
        data = json.loads(a.text)
    else:
        ap.error('--file or --text required')
    r = calc(data)
    txt = json.dumps(r, ensure_ascii=False, indent=2) if a.format == 'json' else to_md(r)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '_last_result.txt')
    open(out, 'w', encoding='utf-8').write(txt + '\n')
    print(txt)
    return 0


if __name__ == '__main__':
    sys.exit(main())
