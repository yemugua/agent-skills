# -*- coding: utf-8 -*-
"""Annuity cash flow and internal rate of return calculator.

Usage:
  python annuity_irr_calc.py --file case.json [--out result.md] [--format json]
  python annuity_irr_calc.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

RATE_LO = -0.9
RATE_HI = 5.0
DENOM_LIMIT = 1e100


def money(x):
    return round(float(x) + 1e-9, 2)


def pct(x):
    return round(float(x) * 100.0 + 1e-9, 4)


def npv(rate, flows):
    """flows: list of (t, cash). Negative cash = premium paid."""
    if rate <= -1.0:
        return float('inf')
    total = 0.0
    for t, c in flows:
        d = (1.0 + rate) ** t
        if d == 0 or d > DENOM_LIMIT:
            return float('inf')
        total += c / d
    return total


def sign_changes(flows):
    s = 0
    prev = 0
    for _t, c in flows:
        if c == 0:
            continue
        cur = 1 if c > 0 else -1
        if prev != 0 and cur != prev:
            s += 1
        prev = cur
    return s


def irr(flows):
    """Return (rate, status). status in ('OK', 'NO_SIGN_CHANGE', 'NO_ROOT')."""
    if sign_changes(flows) == 0:
        return None, 'NO_SIGN_CHANGE'
    lo, hi = RATE_LO, RATE_HI
    flo = npv(lo, flows)
    fhi = npv(hi, flows)
    if flo == 0:
        return lo, 'OK'
    if fhi == 0:
        return hi, 'OK'
    if flo * fhi > 0:
        return None, 'NO_ROOT'
    for _ in range(300):
        mid = (lo + hi) / 2.0
        fm = npv(mid, flows)
        if flo * fm <= 0:
            hi = mid
        else:
            lo = mid
            flo = fm
    return (lo + hi) / 2.0, 'OK'


def build_flows(pay_years, annual_premium, single_premium, start, years, payout):
    flows = []
    if single_premium > 0:
        flows.append((0, -float(single_premium)))
    else:
        for t in range(1, int(pay_years) + 1):
            flows.append((t, -float(annual_premium)))
    for k in range(int(years)):
        flows.append((int(start) + k, float(payout)))
    return flows


def scenario(name, flows, notes):
    rate, status = irr(flows)
    paid = -sum(c for _t, c in flows if c < 0)
    received = sum(c for _t, c in flows if c > 0)
    if status == 'OK':
        irrv = pct(rate)
        irrs = '%.4f%%' % irrv
        multi = 'POSSIBLE_MULTI_ROOT'
        if sign_changes(flows) > 1:
            notes.append(
                'Scenario %s: cash flow signs change more than once, so more '
                'than one IRR may exist. Report the economically meaningful '
                'root and state the convention used.' % name)
        else:
            multi = 'UNIQUE_ROOT'
    else:
        irrv = None
        irrs = 'N/A (%s)' % status
        multi = 'NOT_APPLICABLE'
        notes.append(
            'Scenario %s: no IRR (%s). Cash flows never turn around, so no '
            'discount rate makes the present value zero. Do NOT invent a '
            'number.' % (name, status))
    return {
        'name': name,
        'irr_pct': irrv,
        'irr_display': irrs,
        'root_kind': multi,
        'total_paid': money(paid),
        'total_received': money(received),
        'net': money(received - paid),
        'flows': len(flows),
    }


def calc(data):
    pay_years = int(data.get('pay_years', 10))
    annual_premium = float(data.get('annual_premium', 0))
    single_premium = float(data.get('single_premium', 0))
    payout_years = int(data.get('payout_years', 20))
    start = int(data.get('payout_start_year', pay_years + 1))
    guaranteed = float(data.get('guaranteed_annual_payout', 0))
    illustrated = float(data.get('illustrated_annual_payout', guaranteed))
    stress = float(data.get('stress_annual_payout', guaranteed))

    if pay_years < 0 or payout_years < 0:
        raise ValueError('pay_years and payout_years must be >= 0')
    if annual_premium < 0 or single_premium < 0:
        raise ValueError('premium must be >= 0')
    if guaranteed < 0 or illustrated < 0 or stress < 0:
        raise ValueError('payout must be >= 0')
    if pay_years == 0 and single_premium <= 0:
        raise ValueError('either pay_years > 0 or single_premium > 0 required')
    if payout_years == 0:
        raise ValueError('payout_years must be > 0 to compute an IRR')

    notes = []
    scen = []
    scen.append(scenario('guaranteed', build_flows(pay_years, annual_premium,
                         single_premium, start, payout_years, guaranteed), notes))
    scen.append(scenario('illustrated', build_flows(pay_years, annual_premium,
                         single_premium, start, payout_years, illustrated), notes))
    scen.append(scenario('stress', build_flows(pay_years, annual_premium,
                         single_premium, start, payout_years, stress), notes))

    # Elasticity: 10% cut on the illustrated payout.
    el = None
    if illustrated > 0:
        cut = build_flows(pay_years, annual_premium, single_premium, start,
                          payout_years, illustrated * 0.9)
        r0, s0 = irr(build_flows(pay_years, annual_premium, single_premium,
                                 start, payout_years, illustrated))
        r1, s1 = irr(cut)
        if s0 == 'OK' and s1 == 'OK':
            el = round(pct(r1) - pct(r0), 4)
            notes.append(
                'Cutting the payout by 10%% moves the IRR by %.4f percentage '
                'points. A larger absolute value means the structure is more '
                'sensitive to the illustration assumption.' % el)

    ill_irr = scen[1]['irr_pct']
    guar_irr = scen[0]['irr_pct']
    gap = None
    if ill_irr is not None and guar_irr is not None:
        gap = round(ill_irr - guar_irr, 4)
        notes.append(
            'Illustration gap: %.4f percentage points between the illustrated '
            'IRR and the guaranteed-only IRR. This gap is NOT guaranteed '
            'return.' % gap)

    if illustrated > 0 and guaranteed > 0 and illustrated < guaranteed:
        notes.append(
            'Illustrated payout is lower than the guaranteed payout. Check the '
            'figures against the contract wording.')

    notes.append(
        'The illustration rate is an ASSUMED investment return, NOT a '
        'guaranteed return. Guaranteed benefits are whatever the policy '
        'wording states. Actual credited results may be lower than the '
        'illustration.')
    notes.append(
        'Do not compare this IRR against deposits or bonds without aligning '
        'term, liquidity and tax treatment.')
    notes.append(
        'Surrendering during the premium-paying period returns the cash value '
        'stated in the contract cash value table, usually far below premiums '
        'paid.')

    return {
        'pay_years': pay_years,
        'annual_premium': money(annual_premium),
        'single_premium': money(single_premium),
        'payout_start_year': start,
        'payout_years': payout_years,
        'scenarios': scen,
        'elasticity_irr_delta_pct_points_for_10pct_cut': el,
        'illustration_gap_pct_points': gap,
        'notes': notes,
        'must_confirm': [
            'premium amount is the actual amount debited, not a label',
            'premium paying period and payment frequency from the contract',
            'payout start year and payout years from the contract wording',
            'guaranteed payout amount stated in the contract, not the '
            'illustration',
            'what happens after the guaranteed payout period ends',
            'cash value for the current policy year from the contract table',
            'cooling-off days from the contract, surrender loss per contract',
        ],
    }


def to_md(r):
    L = []
    L.append('# Annuity IRR Scenarios')
    L.append('')
    L.append('- Premium paying years: %d' % r['pay_years'])
    L.append('- Annual premium: %.2f' % r['annual_premium'])
    L.append('- Single premium: %.2f' % r['single_premium'])
    L.append('- Payout start year: %d' % r['payout_start_year'])
    L.append('- Payout years: %d' % r['payout_years'])
    L.append('')
    L.append('| Scenario | IRR | Total paid | Total received | Net | Root kind |')
    L.append('|---|---|---|---|---|---|')
    for s in r['scenarios']:
        L.append('| %s | %s | %.2f | %.2f | %.2f | %s |'
                 % (s['name'], s['irr_display'], s['total_paid'],
                    s['total_received'], s['net'], s['root_kind']))
    L.append('')
    e = r['elasticity_irr_delta_pct_points_for_10pct_cut']
    L.append('- IRR change for a 10%% payout cut: %s'
             % ('%.4f pct points' % e if e is not None else 'N/A'))
    g = r['illustration_gap_pct_points']
    L.append('- Illustration gap (illustrated IRR minus guaranteed IRR): %s'
             % ('%.4f pct points' % g if g is not None else 'N/A'))
    L.append('')
    L.append('IRR definition: the discount rate that makes the present value '
             'of all future cash flows equal to the current amount paid in. '
             'Sign convention: premium paid is negative, payout received is '
             'positive.')
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
    L.append('Static estimate only. The illustration rate is an assumed '
             'investment return, not a guaranteed return. Guaranteed benefits, '
             'payout terms and cash value are stipulated by the insurance '
             'contract. This script does not forecast dividends, does not '
             'recommend products, and gives no investment advice.')
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

    # 1: single in / single out
    r = irr([(0, -1000.0), (1, 1100.0)])
    check(r[1] == 'OK' and abs(pct(r[0]) - 10.0) < 0.001,
          'one-year 1000 to 1100 must be 10%%, got %s' % (r[0],))

    # 2: reference case A -> 3.5%
    d = {'pay_years': 10, 'annual_premium': 20000, 'payout_start_year': 11,
         'payout_years': 20, 'guaranteed_annual_payout': 16508.67,
         'illustrated_annual_payout': 16508.67, 'stress_annual_payout': 16508.67}
    r = calc(d)
    g = r['scenarios'][0]
    check(g['irr_pct'] is not None and abs(g['irr_pct'] - 3.5) < 0.01,
          'reference case IRR should be about 3.5%%, got %s' % g['irr_pct'])
    check(abs(g['total_paid'] - 200000.0) < 0.01, 'total paid should be 200000')
    check(g['root_kind'] == 'UNIQUE_ROOT', 'single sign change -> unique root')

    # 3: reference case B -> 2.0%
    d2 = dict(d)
    d2['guaranteed_annual_payout'] = 13392.98
    d2['illustrated_annual_payout'] = 13392.98
    d2['stress_annual_payout'] = 13392.98
    r2 = calc(d2)
    g2 = r2['scenarios'][0]
    check(g2['irr_pct'] is not None and abs(g2['irr_pct'] - 2.0) < 0.01,
          'reference case B IRR should be about 2.0%%, got %s' % g2['irr_pct'])
    check(abs(r['scenarios'][0]['total_paid']
              - r2['scenarios'][0]['total_paid']) < 0.01,
          'same premiums in both cases')

    # 4: guaranteed-only, 10 payout years -> negative IRR
    d3 = {'pay_years': 10, 'annual_premium': 20000, 'payout_start_year': 11,
          'payout_years': 10, 'guaranteed_annual_payout': 13392.98,
          'illustrated_annual_payout': 13392.98, 'stress_annual_payout': 13392.98}
    r3 = calc(d3)
    g3 = r3['scenarios'][0]
    check(g3['irr_pct'] is not None and g3['irr_pct'] < 0,
          '10 payout years must produce a negative IRR, got %s' % g3['irr_pct'])
    check(g3['net'] < 0, 'received less than paid, net must be negative')

    # 5: no sign change -> no IRR, must not fabricate
    flows = [(1, -1000.0), (2, -1000.0), (3, -1000.0)]
    rr, st = irr(flows)
    check(rr is None and st == 'NO_SIGN_CHANGE',
          'premium only must give NO_SIGN_CHANGE, got %s' % st)

    # 6: too small a payout -> no root in the search range
    d4 = {'pay_years': 5, 'annual_premium': 100000, 'payout_start_year': 6,
          'payout_years': 2, 'guaranteed_annual_payout': 1}
    r4 = calc(d4)
    g4 = r4['scenarios'][0]
    check(g4['irr_pct'] is None,
          'a payout far below the premium must have no IRR, got %s' % g4['irr_pct'])
    check(any('no IRR' in n for n in r4['notes']),
          'no-IRR cases must be stated explicitly in the notes')

    # 7: elasticity sign and direction
    d5 = {'pay_years': 10, 'annual_premium': 20000, 'payout_start_year': 11,
          'payout_years': 20, 'guaranteed_annual_payout': 12000,
          'illustrated_annual_payout': 16509, 'stress_annual_payout': 12000}
    r5 = calc(d5)
    el = r5['elasticity_irr_delta_pct_points_for_10pct_cut']
    check(el is not None and el < 0,
          'a payout cut must lower the IRR, got %s' % el)
    gp = r5['illustration_gap_pct_points']
    check(gp is not None and gp > 0,
          'illustrated IRR must exceed guaranteed IRR here, got %s' % gp)

    # 8: single premium path
    d6 = {'pay_years': 0, 'single_premium': 100000, 'payout_start_year': 1,
          'payout_years': 1, 'guaranteed_annual_payout': 110000,
          'illustrated_annual_payout': 110000, 'stress_annual_payout': 110000}
    r6 = calc(d6)
    g6 = r6['scenarios'][0]
    check(abs(g6['irr_pct'] - 10.0) < 0.001,
          'single premium case IRR should be 10%%, got %s' % g6['irr_pct'])

    # 9: multiple sign changes must be flagged, single-turn must not be
    flows_multi = [(1, -1000.0), (2, 1200.0), (3, -1000.0), (4, 1200.0)]
    check(sign_changes(flows_multi) == 3, 'sign change count should be 3')
    notes_multi = []
    s_multi = scenario('multi', flows_multi, notes_multi)
    check(s_multi['root_kind'] == 'POSSIBLE_MULTI_ROOT',
          'multi-turn cash flow must be reported as multi-root')
    check(any('more than one IRR' in n for n in notes_multi),
          'multi-root case must state that more than one IRR may exist')
    notes_single = []
    s_single = scenario('single', [(1, -1000.0), (2, 1100.0)], notes_single)
    check(s_single['root_kind'] == 'UNIQUE_ROOT',
          'single sign change must be reported as unique root')
    check(not any('more than one IRR' in n for n in notes_single),
          'single-turn case must not claim multiple roots')

    # 10: guaranteed above illustrated -> flag
    d8 = {'pay_years': 5, 'annual_premium': 10000, 'payout_start_year': 6,
          'payout_years': 10, 'guaranteed_annual_payout': 12000,
          'illustrated_annual_payout': 9000, 'stress_annual_payout': 9000}
    r8 = calc(d8)
    check(any('lower than the guaranteed' in n for n in r8['notes']),
          'illustrated below guaranteed must be flagged')

    # 11: guaranteed-return wording guard
    d9 = {'pay_years': 10, 'annual_premium': 20000, 'payout_start_year': 11,
          'payout_years': 20, 'guaranteed_annual_payout': 13000,
          'illustrated_annual_payout': 16509, 'stress_annual_payout': 12000}
    r9 = calc(d9)
    joined = ' '.join(r9['notes'])
    check('NOT a guaranteed return' in joined,
          'the assumed-vs-guaranteed disclaimer must be present')
    low = joined.lower()
    check('guaranteed return is 3.5' not in low and 'guaranteed yield' not in low,
          'no guaranteed-return claim may appear')

    # 12: bad inputs rejected
    for bad in ({'pay_years': -1, 'annual_premium': 100},
                {'pay_years': 5, 'annual_premium': -100},
                {'pay_years': 5, 'annual_premium': 100, 'payout_years': 0},
                {'pay_years': 0, 'single_premium': 0, 'payout_years': 5},
                {'pay_years': 5, 'annual_premium': 100, 'guaranteed_annual_payout': -1}):
        try:
            calc(bad)
            check(False, 'bad input must be rejected: %s' % bad)
        except ValueError:
            check(True, 'bad input rejected')

    # 13: markdown rendering
    md = to_md(calc(d9))
    check('IRR definition' in md and 'Must be confirmed' in md,
          'markdown output must carry the definition and the confirm list')

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
