# -*- coding: utf-8 -*-
"""Commercial third party liability coverage and exposure calculator.

Estimates the needed sum insured from three angles, breaks down the limit
structure, computes the self-paid exposure per scenario, and compares tiers.
It does not recommend products and promises no claim outcome.

Usage:
  python liability_limit_calc.py --file case.json [--out result.md] [--format json]
  python liability_limit_calc.py --selftest
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


def calc(data):
    revenue = float(data.get('annual_revenue', 0))
    prop = float(data.get('property_value', 0))
    staff = float(data.get('staff_count', 0))
    for k, v in (('annual_revenue', revenue), ('property_value', prop),
                 ('staff_count', staff)):
        if v < 0:
            raise ValueError('%s must be >= 0' % k)

    mr = data.get('multiple_range', [1.0, 2.0])
    if not isinstance(mr, (list, tuple)) or len(mr) != 2:
        raise ValueError('multiple_range must be a two-item list')
    lo, hi = float(mr[0]), float(mr[1])
    if lo < 0 or hi < lo:
        raise ValueError('multiple_range must satisfy 0 <= low <= high')

    per_staff = float(data.get('per_staff_reference', 0))
    if per_staff < 0:
        raise ValueError('per_staff_reference must be >= 0')

    ang_a = (revenue * lo, revenue * hi)
    ang_b = (prop * lo, prop * hi)
    ang_c = (staff * per_staff, staff * per_staff)
    need_low = max(ang_a[0], ang_b[0], ang_c[0])
    need_high = max(ang_a[1], ang_b[1], ang_c[1])
    binding = []
    if need_high == ang_a[1] and need_high > 0:
        binding.append('revenue')
    if need_high == ang_b[1] and need_high > 0:
        binding.append('property value')
    if need_high == ang_c[1] and need_high > 0:
        binding.append('staff count')

    social = float(data.get('social_cover_ratio', 0.0))
    if social < 0 or social > 1:
        raise ValueError('social_cover_ratio must be between 0 and 1')
    ratio = float(data.get('liability_ratio', 1.0))
    if ratio < 0 or ratio > 1:
        raise ValueError('liability_ratio must be between 0 and 1')

    tiers = data.get('tiers', []) or []
    scenarios = data.get('scenarios', []) or []
    if not tiers:
        raise ValueError('tiers must not be empty')

    tier_rows = []
    for t in tiers:
        name = str(t.get('name', '?'))
        prem = float(t.get('premium', 0))
        pal = float(t.get('per_accident_limit', 0))
        agg = float(t.get('aggregate_limit', 0))
        ded = float(t.get('deductible', 0))
        dr = float(t.get('deductible_rate', 0.0))
        inj = t.get('injury_limit')
        prp = t.get('property_limit')
        for k, v in (('premium', prem), ('per_accident_limit', pal),
                     ('aggregate_limit', agg), ('deductible', ded)):
            if v < 0:
                raise ValueError('%s of tier %s must be >= 0' % (k, name))
        if dr < 0 or dr >= 1:
            raise ValueError('deductible_rate of tier %s must be in [0,1)'
                             % name)
        if pal <= 0:
            raise ValueError('per_accident_limit of tier %s must be > 0' % name)
        if agg > 0 and agg < pal:
            raise ValueError('aggregate_limit of tier %s is below the per '
                             'accident limit; check the figures' % name)
        cap = pal
        if agg > 0:
            cap = min(cap, agg)
        # Injury and property limits are SEPARATE pools, so they are NOT
        # combined into one smaller cap here; the applicable one is applied
        # per scenario below.
        tier_rows.append({
            'name': name,
            'premium': money(prem),
            'per_accident_limit': money(pal),
            'aggregate_limit': money(agg),
            'deductible': money(ded),
            'deductible_rate': dr,
            'injury_limit': money(float(inj)) if inj is not None else None,
            'property_limit': money(float(prp)) if prp is not None else None,
            'effective_cap': money(cap),
            'split_limits': bool(inj is not None and prp is not None),
        })

    sc_rows = []
    for s in scenarios:
        name = str(s.get('name', '?'))
        stype = str(s.get('type', 'injury')).lower()
        if stype not in ('injury', 'property'):
            raise ValueError('scenario type must be injury or property')
        loss = float(s.get('loss', 0))
        if loss < 0:
            raise ValueError('scenario loss must be >= 0')
        for t in tier_rows:
            cap = t['effective_cap']
            if stype == 'injury' and t['injury_limit'] is not None:
                cap = min(cap, t['injury_limit'])
            if stype == 'property' and t['property_limit'] is not None:
                cap = min(cap, t['property_limit'])
            after_rate = loss * (1.0 - t['deductible_rate'])
            after_ded = after_rate - t['deductible']
            by_liability = after_ded * ratio
            insurable = min(max(0.0, by_liability), cap)
            social_part = min(loss * social, max(0.0, loss - insurable))
            exposure = max(0.0, loss - social_part - insurable)
            sc_rows.append({
                'scenario': name,
                'type': stype,
                'tier': t['name'],
                'loss': money(loss),
                'after_rate': money(after_rate),
                'after_deductible': money(after_ded),
                'by_liability_ratio': money(by_liability),
                'capped_payout': money(insurable),
                'social_part': money(social_part),
                'self_paid_exposure': money(exposure),
                'cap_binding': insurable >= cap - 1e-6 and by_liability > cap,
            })

    # Tier comparison on a reference scenario.
    cmp_rows = []
    ref = None
    for s in scenarios:
        if ref is None or float(s.get('loss', 0)) > float(ref.get('loss', 0)):
            ref = s
    if ref is not None:
        ref_name = str(ref.get('name', '?'))
        ref_loss = float(ref.get('loss', 0))
        base = None
        for t in tier_rows:
            e = [x for x in sc_rows if x['scenario'] == ref_name
                 and x['tier'] == t['name']]
            exp = e[0]['self_paid_exposure'] if e else None
            if base is None:
                base = {'premium': t['premium'], 'exposure': exp}
            cmp_rows.append({
                'tier': t['name'],
                'premium': t['premium'],
                'exposure': exp,
                'premium_delta': money(t['premium'] - base['premium']),
                'exposure_reduction': (money(base['exposure'] - exp)
                                       if exp is not None and
                                       base['exposure'] is not None else None),
            })
        for c in cmp_rows:
            red = c['exposure_reduction']
            if red and red > 0 and c['premium_delta'] > 0:
                c['cost_per_10k_reduction'] = money(
                    c['premium_delta'] / (red / 10000.0))
            else:
                c['cost_per_10k_reduction'] = None

    notes = []
    notes.append('Three angles were computed and the largest was taken. The '
                 'multiples are REFERENCE BANDS, not a standard, not a '
                 'regulatory requirement and not a recommendation.')
    notes.append('Binding angle at the upper bound: %s. Base the decision on '
                 'the tightest angle, not on the cheapest premium.'
                 % (', '.join(binding) or 'not determinable'))
    notes.append('Per-accident limit, aggregate limit and the actual payout '
                 'are three different numbers. Read all three.')
    for t in tier_rows:
        if t['split_limits']:
            notes.append('Tier %s has SEPARATE injury and property limits, '
                         'so the two do not share one pool. Once one is used '
                         'up, the other is gone.' % t['name'])
        if t['aggregate_limit'] and t['aggregate_limit'] > 0:
            notes.append('Tier %s: aggregate limit %.2f against per-accident '
                         'limit %.2f. The aggregate limit may be far below '
                         'per-accident limit times the number of claims.'
                         % (t['name'], t['aggregate_limit'],
                            t['per_accident_limit']))
    notes.append('Employee injury caused by work is handled by WORK INJURY '
                 'INSURANCE through the labour authority, not by a third '
                 'party liability plan.')
    notes.append('Damage to the insured own equipment or premises belongs to '
                 'PROPERTY insurance, not to a liability plan.')
    notes.append('Compulsory motor liability insurance pays first within its '
                 'own limits, and the commercial plan covers the remainder, '
                 'subject to the rules in force and the contract wording.')
    notes.append('Compensation amounts follow the law in force and the actual '
                 'assessment. Do NOT quote figures from memory.')
    notes.append('This script does not recommend a product, does not predict '
                 'the compensation amount and promises no claim outcome.')

    return {
        'angle_revenue': [money(ang_a[0]), money(ang_a[1])],
        'angle_property': [money(ang_b[0]), money(ang_b[1])],
        'angle_staff': [money(ang_c[0]), money(ang_c[1])],
        'need_low': money(need_low),
        'need_high': money(need_high),
        'binding_angles': binding,
        'multiple_range': [lo, hi],
        'per_staff_reference': money(per_staff),
        'social_cover_ratio': social,
        'liability_ratio': ratio,
        'tiers': tier_rows,
        'scenarios': sc_rows,
        'tier_comparison': cmp_rows,
        'reference_scenario': ref.get('name') if ref is not None else None,
        'notes': notes,
        'must_confirm': [
            'annual revenue from actual operating records, not an estimate',
            'property and equipment value from the asset list',
            'staff count and the employment type, including outsourced staff',
            'per-accident limit and aggregate limit written down separately',
            'whether injury and property limits are separate items',
            'deductible and deductible rate written down, and whether they '
            'stack or are alternatives',
            'how the liability ratio is set, taken from the contract wording',
            'compensation order taken from the contract, not assumed',
            'work injury insurance status confirmed',
            'social insurance benefits taken from the rules currently in force',
            'every exclusion clause read, especially those relevant to the '
            'business',
            'a liability plan does not cover the insured own property',
        ],
    }


def to_md(r):
    L = []
    L.append('# Commercial Liability Coverage and Exposure')
    L.append('')
    L.append('## Three angles for the needed sum insured')
    L.append('')
    L.append('| Angle | Low | High |')
    L.append('|---|---|---|')
    L.append('| By revenue | %.2f | %.2f |'
             % (r['angle_revenue'][0], r['angle_revenue'][1]))
    L.append('| By property value | %.2f | %.2f |'
             % (r['angle_property'][0], r['angle_property'][1]))
    L.append('| By staff count | %.2f | %.2f |'
             % (r['angle_staff'][0], r['angle_staff'][1]))
    L.append('')
    L.append('- Reference multiple range: %.2f to %.2f (reference band only, '
             'NOT a standard)' % (r['multiple_range'][0], r['multiple_range'][1]))
    L.append('- Per staff reference: %.2f' % r['per_staff_reference'])
    L.append('- Take the largest: low %.2f, high %.2f'
             % (r['need_low'], r['need_high']))
    L.append('- Binding angle: %s'
             % (', '.join(r['binding_angles']) or 'not determinable'))
    L.append('')
    L.append('## Limit structure by tier')
    L.append('')
    L.append('| Tier | Premium | Per accident | Aggregate | Deductible | '
             'Deductible rate | Injury | Property | Effective cap |')
    L.append('|---|---|---|---|---|---|---|---|---|')
    for t in r['tiers']:
        L.append('| %s | %.2f | %.2f | %.2f | %.2f | %.4f | %s | %s | %.2f |'
                 % (t['name'], t['premium'], t['per_accident_limit'],
                    t['aggregate_limit'], t['deductible'],
                    t['deductible_rate'],
                    '%.2f' % t['injury_limit']
                    if t['injury_limit'] is not None else 'N/A',
                    '%.2f' % t['property_limit']
                    if t['property_limit'] is not None else 'N/A',
                    t['effective_cap']))
    L.append('')
    L.append('## Self-paid exposure per scenario')
    L.append('')
    L.append('| Scenario | Type | Tier | Loss | After rate | After '
             'deductible | By ratio | Capped payout | Social part | '
             'Self-paid | Cap binding |')
    L.append('|---|---|---|---|---|---|---|---|---|---|---|')
    for s in r['scenarios']:
        L.append('| %s | %s | %s | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | '
                 '%.2f | %s |'
                 % (s['scenario'], s['type'], s['tier'], s['loss'],
                    s['after_rate'], s['after_deductible'],
                    s['by_liability_ratio'], s['capped_payout'],
                    s['social_part'], s['self_paid_exposure'],
                    'yes' if s['cap_binding'] else 'no'))
    L.append('')
    if r['tier_comparison']:
        L.append('## Tier comparison on scenario %s' % r['reference_scenario'])
        L.append('')
        L.append('| Tier | Premium | Premium delta | Exposure | Exposure '
                 'reduction | Cost per 10k reduction |')
        L.append('|---|---|---|---|---|---|')
        for c in r['tier_comparison']:
            L.append('| %s | %.2f | %.2f | %s | %s | %s |'
                     % (c['tier'], c['premium'], c['premium_delta'],
                        '%.2f' % c['exposure']
                        if c['exposure'] is not None else 'N/A',
                        '%.2f' % c['exposure_reduction']
                        if c['exposure_reduction'] is not None else 'N/A',
                        '%.2f' % c['cost_per_10k_reduction']
                        if c['cost_per_10k_reduction'] is not None else 'N/A'))
        L.append('')
    L.append('## Notes')
    L.append('')
    for n in r['notes']:
        L.append('- %s' % n)
    L.append('')
    L.append('## Must be confirmed')
    L.append('')
    for m in r['must_confirm']:
        L.append('- [ ] %s' % m)
    L.append('')
    L.append('Static estimate on the supplied data. Limits, deductibles and '
             'the liability ratio follow the insurance contract. Compensation '
             'amounts follow the law in force and the actual assessment. '
             'Social insurance benefits follow the rules currently in force. '
             'No product is recommended, no compensation amount is predicted '
             'and no claim outcome is promised.')
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

    base = {
        'annual_revenue': 3000000,
        'property_value': 2000000,
        'staff_count': 20,
        'multiple_range': [1.0, 2.0],
        'per_staff_reference': 100000,
        'social_cover_ratio': 0.3,
        'liability_ratio': 1.0,
        'tiers': [
            {'name': 'low', 'premium': 3000, 'per_accident_limit': 500000,
             'aggregate_limit': 1000000, 'deductible': 5000,
             'deductible_rate': 0.1, 'injury_limit': 300000,
             'property_limit': 200000},
            {'name': 'high', 'premium': 4200, 'per_accident_limit': 2000000,
             'aggregate_limit': 4000000, 'deductible': 2000,
             'deductible_rate': 0.05, 'injury_limit': 1500000,
             'property_limit': 500000},
        ],
        'scenarios': [
            {'name': 'injury', 'type': 'injury', 'loss': 800000},
            {'name': 'damage', 'type': 'property', 'loss': 300000},
        ],
    }

    # 1: three angles and taking the largest
    r = calc(base)
    check(r['angle_revenue'] == [3000000.0, 6000000.0],
          'revenue angle should be 3M-6M, got %s' % r['angle_revenue'])
    check(r['angle_property'] == [2000000.0, 4000000.0],
          'property angle should be 2M-4M, got %s' % r['angle_property'])
    check(r['angle_staff'] == [2000000.0, 2000000.0],
          'staff angle should be 20*100000, got %s' % r['angle_staff'])
    check(abs(r['need_high'] - 6000000.0) < 0.01,
          'the largest upper bound should be 6000000, got %s' % r['need_high'])
    check('revenue' in r['binding_angles'],
          'revenue should be the binding angle, got %s' % r['binding_angles'])

    # 2: split limits are separate pools, not one smaller combined cap
    tl = {t['name']: t for t in r['tiers']}
    check(abs(tl['low']['effective_cap'] - 500000.0) < 0.01,
          'low tier effective cap is min(500000, 1000000) = 500000, got %s'
          % tl['low']['effective_cap'])
    check(abs(tl['high']['effective_cap'] - 2000000.0) < 0.01,
          'high tier effective cap is min(2000000, 4000000) = 2000000, got %s'
          % tl['high']['effective_cap'])
    check(tl['low']['split_limits'] is True and tl['high']['split_limits'],
          'both tiers must be reported as having split limits')

    # 3: exposure arithmetic, low tier injury scenario
    e = [x for x in r['scenarios']
         if x['scenario'] == 'injury' and x['tier'] == 'low'][0]
    # 800000 * 0.9 = 720000; -5000 = 715000; ratio 1.0 -> 715000;
    # cap by injury limit 300000 -> 300000
    check(abs(e['after_rate'] - 720000.0) < 0.01,
          'after rate should be 720000, got %s' % e['after_rate'])
    check(abs(e['after_deductible'] - 715000.0) < 0.01,
          'after deductible should be 715000, got %s' % e['after_deductible'])
    check(abs(e['capped_payout'] - 300000.0) < 0.01,
          'payout should be capped at 300000, got %s' % e['capped_payout'])
    check(e['cap_binding'] is True, 'the cap must be reported as binding')
    # social part: min(800000*0.3, 800000-300000) = min(240000,500000) = 240000
    check(abs(e['social_part'] - 240000.0) < 0.01,
          'social part should be 240000, got %s' % e['social_part'])
    check(abs(e['self_paid_exposure'] - 260000.0) < 0.01,
          'exposure should be 800000-240000-300000=260000, got %s'
          % e['self_paid_exposure'])

    # 4: property scenario uses the property limit
    e2 = [x for x in r['scenarios']
          if x['scenario'] == 'damage' and x['tier'] == 'high'][0]
    # 300000*0.95 = 285000; -2000 = 283000; capped at property limit 500000 -> 283000
    check(abs(e2['capped_payout'] - 283000.0) < 0.01,
          'property payout should be 283000, got %s' % e2['capped_payout'])
    check(e2['cap_binding'] is False, 'the cap must not bind here')

    # 5: liability ratio scales the payout
    base_r = dict(base)
    base_r['liability_ratio'] = 0.3
    r5 = calc(base_r)
    e5 = [x for x in r5['scenarios']
          if x['scenario'] == 'damage' and x['tier'] == 'high'][0]
    # 283000 * 0.3 = 84900
    check(abs(e5['capped_payout'] - 84900.0) < 0.01,
          'a 30%% ratio should give 84900, got %s' % e5['capped_payout'])
    e_ref = [x for x in r['scenarios']
             if x['scenario'] == 'damage' and x['tier'] == 'high'][0]
    check(abs(e5['self_paid_exposure']
              - (300000 - 90000 - 84900)) < 0.01,
          'social absorbs at most 30%% of the loss, so exposure should be '
          '300000-90000-84900=126100, got %s' % e5['self_paid_exposure'])
    check(e5['self_paid_exposure'] > e_ref['self_paid_exposure'],
          'a lower liability ratio must raise the exposure')

    # 6: tier comparison and cost per 10k reduction
    cmp_rows = {c['tier']: c for c in r['tier_comparison']}
    check(cmp_rows['low']['premium_delta'] == 0.0,
          'the first tier has no delta')
    check(abs(cmp_rows['high']['premium_delta'] - 1200.0) < 0.01,
          'high tier premium delta should be 1200')
    check(cmp_rows['high']['exposure_reduction'] is not None
          and cmp_rows['high']['exposure_reduction'] > 0,
          'the high tier must reduce exposure')
    check(cmp_rows['high']['cost_per_10k_reduction'] is not None
          and cmp_rows['high']['cost_per_10k_reduction'] > 0,
          'cost per 10k reduction must be computed')

    # 7: reference scenario is the largest loss
    check(r['reference_scenario'] == 'injury',
          'the reference scenario should be the largest loss, got %s'
          % r['reference_scenario'])

    # 8: exposure can never go negative
    base_z = dict(base)
    base_z['social_cover_ratio'] = 1.0
    r8 = calc(base_z)
    check(all(x['self_paid_exposure'] == 0.0 for x in r8['scenarios']),
          'full social cover must leave zero exposure')

    # 9: zero loss scenario
    base_0 = dict(base)
    base_0['scenarios'] = [{'name': 'none', 'type': 'injury', 'loss': 0}]
    r9 = calc(base_0)
    check(r9['scenarios'][0]['self_paid_exposure'] == 0.0,
          'a zero loss must leave zero exposure')

    # 10: wording guards
    joined = ' '.join(r['notes'])
    check('REFERENCE BANDS, not a standard' in joined,
          'the multiple band must be flagged as a reference')
    check('three different numbers' in joined,
          'limit structure must be stated as three different numbers')
    check('SEPARATE injury and property limits' in joined,
          'split limits must be flagged')
    check('WORK INJURY INSURANCE' in joined,
          'the work injury boundary must be stated')
    check('PROPERTY insurance' in joined,
          'the own-property boundary must be stated')
    check('Do NOT quote figures from memory' in joined,
          'compensation figures must not be quoted from memory')
    check('promises no claim outcome' in joined,
          'the no-guarantee statement must be present')
    low = joined.lower()
    check('will be paid' not in low and 'guaranteed to pay' not in low,
          'no claim guarantee may appear')

    # 11: bad inputs rejected
    for bad in ({'annual_revenue': -1},
                {'property_value': -1},
                {'staff_count': -1},
                {'annual_revenue': 100, 'multiple_range': [2, 1]},
                {'annual_revenue': 100, 'multiple_range': [-1, 1]},
                {'annual_revenue': 100, 'multiple_range': [1]},
                dict(base, social_cover_ratio=1.5),
                dict(base, liability_ratio=-0.1),
                dict(base, tiers=[]),
                dict(base, tiers=[{'name': 'x', 'premium': 1,
                                   'per_accident_limit': 0}]),
                dict(base, tiers=[{'name': 'x', 'premium': 1,
                                   'per_accident_limit': 100,
                                   'aggregate_limit': 50}]),
                dict(base, scenarios=[{'name': 'x', 'type': 'alien',
                                       'loss': 1}]),
                dict(base, scenarios=[{'name': 'x', 'type': 'injury',
                                       'loss': -1}]),
                dict(base, per_staff_reference=-1)):
        try:
            calc(bad)
            check(False, 'bad input must be rejected')
        except ValueError:
            check(True, 'bad input rejected')

    # 12: markdown rendering
    md = to_md(r)
    check('Three angles' in md and 'Limit structure by tier' in md
          and 'Self-paid exposure per scenario' in md,
          'markdown output must carry angles, tiers and exposures')

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
