# -*- coding: utf-8 -*-
"""Family life insurance allocation order and coverage gap calculator.

Usage:
  python allocation_budget.py --file case.json [--out result.md] [--format json]
  python allocation_budget.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Reference bands only. Not regulatory standards and not mandatory thresholds.
BAND_SINGLE = (0.05, 0.10)
BAND_DUAL = (0.08, 0.12)
CRITICAL_YEARS_LOW = 3.0
CRITICAL_YEARS_HIGH = 5.0

DUTY = {
    'critical': 'Treats treatment cost loss plus income interruption. Benefit '
                'is paid as a lump sum on diagnosis meeting the contract '
                'definition; the money may be used for anything.',
    'medical': 'Reimburses medical expenses above the social insurance scope. '
               'Needs invoices and has a deductible; it is NOT a lump sum.',
    'accident': 'Covers death, disability and accidental medical costs caused '
                'by an accident. Illness-caused losses are not covered.',
    'term_life': 'Pays a fixed sum on death or total disability, mainly to '
                 'cover debts and the family expenses that continue.',
}

SOCIAL_LINK = [
    'Medical expenses inside the social insurance catalogue: reimbursed by '
    'social insurance under the catalogue and settlement rules in force.',
    'Expenses outside the social insurance catalogue: partly self-paid; a '
    'commercial medical plan covers them only if its wording says so.',
    'Large hospital bills and income interruption after a critical illness: '
    'not covered by social insurance; paid by the critical illness benefit.',
    'Accidental death or disability: not covered by social insurance; paid by '
    'the accident plan.',
    'Debts and living expenses after a death: not covered by social '
    'insurance; paid by the term life benefit.',
    'Tax treatment of death benefits is a tax matter and follows the rules '
    'in force and the regulator; do not treat it as a tax avoidance scheme.',
]


def money(x):
    return round(float(x) + 1e-9, 2)


def pct(x):
    return round(float(x) * 100.0 + 1e-9, 4)


def calc(data):
    income = float(data.get('family_income', 0))
    debt = float(data.get('debt', 0))
    expense = float(data.get('annual_expense', 0))
    years = float(data.get('support_years', 0))
    liquid = float(data.get('liquid_assets', 0))
    members = data.get('members', []) or []

    for k, v in (('family_income', income), ('debt', debt),
                 ('annual_expense', expense), ('support_years', years),
                 ('liquid_assets', liquid)):
        if v < 0:
            raise ValueError('%s must be >= 0' % k)

    notes = []
    life_base = debt + expense * years
    rows = []
    for m in members:
        name = str(m.get('name', '?'))
        inc = float(m.get('income', 0) or 0)
        bw = bool(m.get('breadwinner', False))
        ex = m.get('existing', {}) or {}
        crit = float(ex.get('critical', 0) or 0)
        med = float(ex.get('medical', 0) or 0)
        acc = float(ex.get('accident', 0) or 0)
        term = float(ex.get('term_life', 0) or 0)
        for k, v in (('critical', crit), ('medical', med),
                     ('accident', acc), ('term_life', term)):
            if v < 0:
                raise ValueError('existing %s must be >= 0 for member %s' % (k, name))

        crit_low = inc * CRITICAL_YEARS_LOW
        crit_high = inc * CRITICAL_YEARS_HIGH
        crit_gap_low = max(0.0, crit_low - crit)
        term_need = life_base - term - liquid
        term_gap = max(0.0, term_need)
        rows.append({
            'name': name,
            'age': m.get('age', ''),
            'income': money(inc),
            'breadwinner': bw,
            'critical_existing': money(crit),
            'critical_need_low': money(crit_low),
            'critical_need_high': money(crit_high),
            'critical_gap_low': money(crit_gap_low),
            'medical_existing': money(med),
            'medical_note': ('No medical plan recorded. Confirm deductible, '
                             'reimbursement ratio, renewal condition and '
                             'whether out-of-catalog expenses are covered.'),
            'accident_existing': money(acc),
            'accident_need': money(life_base),
            'accident_gap': money(max(0.0, life_base - acc)),
            'term_existing': money(term),
            'term_need': money(max(0.0, term_need)),
            'term_gap': money(term_gap),
        })

    # Priority order: breadwinner first, then other earners, then non-earners.
    ordered = sorted(
        rows,
        key=lambda r: (0 if r['breadwinner'] else (1 if r['income'] > 0 else 2),
                       -r['income']))

    for i, r in enumerate(ordered):
        if r['breadwinner']:
            r['priority_reason'] = ('Breadwinner: protects the main family '
                                    'income first.')
        elif r['income'] > 0:
            r['priority_reason'] = ('Other income earner: also faces income '
                                    'interruption risk.')
        else:
            r['priority_reason'] = ('Non-earner: low premium but does not '
                                    'carry family income responsibility, so it '
                                    'ranks after the adults.')
        r['priority_rank'] = i + 1

    total_crit_gap = sum(r['critical_gap_low'] for r in rows)
    total_term_gap = sum(r['term_gap'] for r in rows)
    total_acc_gap = sum(r['accident_gap'] for r in rows)
    med_gaps = [r['name'] for r in rows if r['medical_existing'] <= 0]

    plan = data.get('annual_premium_plan', {}) or {}
    premium_total = 0.0
    premium_rows = []
    for k, v in plan.items():
        fv = float(v)
        if fv < 0:
            raise ValueError('premium for %s must be >= 0' % k)
        premium_total += fv
        premium_rows.append({'name': k, 'premium': money(fv)})

    ratio = None
    band = None
    if income > 0:
        ratio = premium_total / income
        earners = len([m for m in members if float(m.get('income', 0) or 0) > 0])
        kids = len([m for m in members
                    if float(m.get('income', 0) or 0) <= 0
                    and int(m.get('age', 99) or 99) < 18])
        band = BAND_DUAL if (earners >= 2 or kids >= 1) else BAND_SINGLE

    notes.append('Order rule 1: adults before children. A child policy is '
                 'cheap, but the adult premium is the one that keeps the '
                 'family going.')
    notes.append('Order rule 2: protection before savings. A savings-type '
                 'policy has agreed payment terms; it does NOT promise a '
                 'return, and it does not pay a large benefit on a claim.')
    notes.append('Order rule 3: adequate coverage before large coverage. Fill '
                 'the gap first; do not chase a coverage multiple while the '
                 'gap is still open.')
    notes.append('Order rule 4: core members first, ranked by income '
                 'contribution and responsibility, not by age or gender.')
    if med_gaps:
        notes.append('Members with no medical plan recorded: %s. A medical '
                     'plan is a reimbursement plan with a deductible and a '
                     'renewal condition, not a lump sum.'
                     % ', '.join(med_gaps))
    notes.append('A medical plan reimburses invoices; a critical illness plan '
                 'pays a lump sum without invoices. They solve different '
                 'problems.')
    notes.append('Accident plans cover accident-caused loss only. Illness '
                 'loss needs a critical illness plan and a medical plan.')
    if ratio is not None and band is not None:
        notes.append('Premium ratio is %.4f%%. The reference band for this '
                     'family shape is %.2f%% to %.2f%%. This is a reference '
                     'band, NOT a regulatory standard, and NOT a pass mark: '
                     'what matters is whether the coverage gaps are closed.'
                     % (pct(ratio), band[0] * 100, band[1] * 100))
    else:
        notes.append('Family income was not supplied, so the premium ratio '
                     'cannot be computed. Do NOT invent a number.')
    notes.append('Social insurance covers part of the medical cost only. It '
                 'does not cover income interruption and does not cover debts '
                 'and living expenses after a death.')
    notes.append('Group insurance from an employer counts toward existing '
                 'coverage, but it usually ends when employment ends.')
    notes.append('If a waiting period has not elapsed, or a previous policy '
                 'limits a certain responsibility, existing coverage does NOT '
                 'mean the protection is already in force today.')
    notes.append('This script does not recommend any product, does not '
                 'predict any claim outcome, and does not promise any return.')

    return {
        'family_income': money(income),
        'debt': money(debt),
        'annual_expense': money(expense),
        'support_years': years,
        'liquid_assets': money(liquid),
        'life_insurance_base': money(life_base),
        'formula': ('sum insured = debt + annual expense * support years - '
                    'existing sum insured - liquid assets'),
        'priority_order': ordered,
        'total_critical_gap_low': money(total_crit_gap),
        'total_term_gap': money(total_term_gap),
        'total_accident_gap': money(total_acc_gap),
        'medical_gap_members': med_gaps,
        'premium_rows': premium_rows,
        'premium_total': money(premium_total),
        'premium_ratio_pct': pct(ratio) if ratio is not None else None,
        'premium_band_pct': ([band[0] * 100, band[1] * 100]
                             if band is not None else None),
        'band_is_reference_not_standard': True,
        'duty_map': DUTY,
        'social_link': SOCIAL_LINK,
        'notes': notes,
        'must_confirm': [
            'every family member listed, with age and income checked one by one',
            'every existing policy counted, including employer group cover',
            'debt taken as the current balance, not the original loan amount',
            'annual expense basis stated, whether mortgage instalments included',
            'support years estimated to the point the children are independent',
            'liquid assets limited to what can be realised quickly',
            'adults ranked before children in the priority list',
            'protection and savings type plans recorded separately',
            'medical plan deductible, ratio, renewal condition and catalog '
            'coverage confirmed',
            'social insurance benefits taken from the rules currently in force',
        ],
    }


def to_md(r):
    L = []
    L.append('# Family Insurance Allocation Check')
    L.append('')
    L.append('| Item | Value |')
    L.append('|---|---|')
    L.append('| Family income | %.2f |' % r['family_income'])
    L.append('| Debt balance | %.2f |' % r['debt'])
    L.append('| Annual expense | %.2f |' % r['annual_expense'])
    L.append('| Support years | %.2f |' % r['support_years'])
    L.append('| Liquid assets | %.2f |' % r['liquid_assets'])
    L.append('| Life insurance base | %.2f |' % r['life_insurance_base'])
    L.append('')
    L.append('- Formula: %s' % r['formula'])
    L.append('')
    L.append('## Priority order')
    L.append('')
    L.append('| Rank | Member | Age | Income | Breadwinner | Reason |')
    L.append('|---|---|---|---|---|---|')
    for m in r['priority_order']:
        L.append('| %d | %s | %s | %.2f | %s | %s |'
                 % (m['priority_rank'], m['name'], m['age'], m['income'],
                    'yes' if m['breadwinner'] else 'no', m['priority_reason']))
    L.append('')
    L.append('## Coverage gaps by member')
    L.append('')
    L.append('| Member | Critical need (3y-5y income) | Critical existing | '
             'Critical gap | Medical existing | Accident gap | Term gap |')
    L.append('|---|---|---|---|---|---|---|')
    for m in r['priority_order']:
        L.append('| %s | %.2f - %.2f | %.2f | %.2f | %.2f | %.2f | %.2f |'
                 % (m['name'], m['critical_need_low'], m['critical_need_high'],
                    m['critical_existing'], m['critical_gap_low'],
                    m['medical_existing'], m['accident_gap'], m['term_gap']))
    L.append('')
    L.append('- Total critical gap (at 3x income): %.2f'
             % r['total_critical_gap_low'])
    L.append('- Total term life gap: %.2f' % r['total_term_gap'])
    L.append('- Total accident gap: %.2f' % r['total_accident_gap'])
    L.append('- Members with no medical plan: %s'
             % (', '.join(r['medical_gap_members']) or 'none'))
    L.append('')
    L.append('## Premium budget')
    L.append('')
    L.append('| Member | Annual premium |')
    L.append('|---|---|')
    for p in r['premium_rows']:
        L.append('| %s | %.2f |' % (p['name'], p['premium']))
    L.append('')
    L.append('- Total annual premium: %.2f' % r['premium_total'])
    if r['premium_ratio_pct'] is not None:
        L.append('- Ratio of income: %.4f%%' % r['premium_ratio_pct'])
        L.append('- Reference band for this family shape: %.2f%% to %.2f%% '
                 '(reference only, NOT a regulatory standard)'
                 % (r['premium_band_pct'][0], r['premium_band_pct'][1]))
    else:
        L.append('- Ratio of income: N/A')
    L.append('')
    L.append('## What each plan solves')
    L.append('')
    for k, v in r['duty_map'].items():
        L.append('- **%s**: %s' % (k, v))
    L.append('')
    L.append('## Social insurance link')
    L.append('')
    for s in r['social_link']:
        L.append('- %s' % s)
    L.append('')
    L.append('## Notes')
    L.append('')
    for n in r['notes']:
        L.append('- %s' % n)
    L.append('')
    L.append('## Must be confirmed manually')
    L.append('')
    for m in r['must_confirm']:
        L.append('- [ ] %s' % m)
    L.append('')
    L.append('Static estimate on the supplied data. Coverage terms, '
             'deductibles, waiting periods and payment conditions follow the '
             'insurance contract. Social insurance benefits follow the rules '
             'currently in force and the social insurance authority. The '
             'premium band is a reference range, not a standard. No product '
             'is recommended, no claim outcome is predicted and no return is '
             'promised.')
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
        'family_income': 400000, 'debt': 1200000, 'annual_expense': 240000,
        'support_years': 15, 'liquid_assets': 400000,
        'members': [
            {'name': 'A', 'age': 38, 'income': 280000, 'breadwinner': True,
             'existing': {'critical': 300000, 'medical': 0,
                          'accident': 500000, 'term_life': 200000}},
            {'name': 'B', 'age': 36, 'income': 120000, 'breadwinner': False,
             'existing': {'critical': 0, 'medical': 0,
                          'accident': 0, 'term_life': 0}},
            {'name': 'C', 'age': 8, 'income': 0, 'breadwinner': False,
             'existing': {'critical': 0, 'medical': 0,
                          'accident': 0, 'term_life': 0}},
        ],
        'annual_premium_plan': {'A': 9600, 'B': 2400, 'C': 1200},
    }

    # 1: the documented worked example
    r = calc(base)
    check(abs(r['life_insurance_base'] - (1200000 + 240000 * 15)) < 0.01,
          'base should be 1200000+3600000=4800000, got %s'
          % r['life_insurance_base'])
    a = r['priority_order'][0]
    check(a['name'] == 'A', 'breadwinner must rank first')
    check(abs(a['term_need'] - (4800000 - 200000 - 400000)) < 0.01,
          'member A term need should be 4200000, got %s' % a['term_need'])

    # 2: children rank after adults
    names = [m['name'] for m in r['priority_order']]
    check(names.index('C') > names.index('A') and names.index('C') > names.index('B'),
          'child must rank after both adults, got order %s' % names)
    child = [m for m in r['priority_order'] if m['name'] == 'C'][0]
    check('ranks after the adults' in child['priority_reason'],
          'child reason must state it ranks after adults')

    # 3: critical need is 3x to 5x of own income
    check(abs(a['critical_need_low'] - 840000) < 0.01,
          'critical need low should be 3*280000=840000')
    check(abs(a['critical_need_high'] - 1400000) < 0.01,
          'critical need high should be 5*280000=1400000')
    check(abs(a['critical_gap_low'] - 540000) < 0.01,
          'critical gap should be 840000-300000=540000')

    # 4: premium ratio and reference band
    check(abs(r['premium_total'] - 13200.0) < 0.01,
          'premium total should be 13200')
    check(abs(r['premium_ratio_pct'] - 3.3) < 0.01,
          'ratio should be 13200/400000=3.3%%, got %s' % r['premium_ratio_pct'])
    check(r['premium_band_pct'] == [8.0, 12.0],
          'dual-earner family should use the 8-12%% band, got %s'
          % r['premium_band_pct'])
    check(r['band_is_reference_not_standard'] is True,
          'the band must be flagged as a reference, not a standard')
    check(any('NOT a regulatory standard' in n for n in r['notes']),
          'notes must state the band is not a standard')

    # 5: below the band is not automatically a failure
    check(any('is a reference' in n or 'NOT a regulatory' in n
              for n in r['notes']),
          'notes must warn against reading the band as a pass mark')

    # 6: medical gap members
    check(set(r['medical_gap_members']) == {'A', 'B', 'C'},
          'all three members lack a medical plan, got %s'
          % r['medical_gap_members'])
    check(any('not a lump sum' in n for n in r['notes']),
          'medical plan must be described as reimbursement, not lump sum')

    # 7: zero income -> ratio not computed, no fabrication
    r2 = dict(base)
    r2['family_income'] = 0
    r2['members'] = [dict(base['members'][0])]
    r2['members'][0] = dict(base['members'][0])
    r2['members'][0]['income'] = 0
    r2['annual_premium_plan'] = {'A': 9600}
    r2b = calc(r2)
    check(r2b['premium_ratio_pct'] is None,
          'zero income must yield no ratio')
    check(any('Do NOT invent a number' in n for n in r2b['notes']),
          'missing ratio must be stated explicitly')

    # 8: single earner family uses the lower band
    r3 = dict(base)
    r3['members'] = [{'name': 'A', 'age': 38, 'income': 300000,
                      'breadwinner': True, 'existing': {}}]
    r3['annual_premium_plan'] = {'A': 12000}
    r3b = calc(r3)
    check(r3b['premium_band_pct'] == [5.0, 10.0],
          'single-earner family should use the 5-10%% band, got %s'
          % r3b['premium_band_pct'])

    # 9: existing coverage above the need gives zero gap, never negative
    r4 = dict(base)
    r4['debt'] = 0
    r4['annual_expense'] = 0
    r4['support_years'] = 0
    r4['liquid_assets'] = 0
    r4['members'] = [{'name': 'A', 'age': 38, 'income': 100000,
                      'breadwinner': True,
                      'existing': {'critical': 900000, 'accident': 5000000,
                                   'term_life': 100000}}]
    r4b = calc(r4)
    m = r4b['priority_order'][0]
    check(m['term_gap'] == 0.0, 'excess coverage must give a zero gap')
    check(m['critical_gap_low'] == 0.0, 'excess critical cover must give 0 gap')
    check(m['accident_gap'] == 0.0, 'excess accident cover must give 0 gap')

    # 10: social link and duty map present
    joined = ' '.join(r['social_link'])
    check('income interruption after a critical illness: not covered by social '
          'insurance' in joined,
          'social link must state income interruption is not covered')
    check('do not treat it as a tax avoidance scheme' in joined,
          'tax matter must not be framed as tax avoidance')
    dm = r['duty_map']
    check(set(dm.keys()) == {'critical', 'medical', 'accident', 'term_life'},
          'duty map must cover the four plan types')
    check('Accident-caused loss only' in dm['accident'] or
          'accident' in dm['accident'],
          'accident duty must describe accident-caused loss')
    check('NOT a lump sum' in dm['medical'],
          'medical duty must state it is not a lump sum')

    # 11: waiting-period and group-cover warnings
    notes = ' '.join(r['notes'])
    check('NOT mean the protection is already in force' in notes,
          'waiting-period warning must be present')
    check('ends when employment ends' in notes,
          'group insurance expiry warning must be present')
    check('does NOT promise a return' in notes
          or 'does NOT promise a return' in notes,
          'savings-type plan must not be tied to a return promise')

    # 12: wording guards
    low = notes.lower()
    check('guaranteed return' not in low, 'no guaranteed-return claim allowed')
    check('will be paid' not in low, 'no guaranteed claim outcome allowed')

    # 13: bad inputs rejected
    for bad in ({'family_income': -1},
                {'debt': -5},
                {'annual_expense': -1},
                {'support_years': -1},
                {'liquid_assets': -1},
                {'family_income': 100, 'members': [
                    {'name': 'A', 'income': 100,
                     'existing': {'critical': -1}}]}):
        try:
            calc(bad)
            check(False, 'bad input must be rejected: %s' % bad)
        except ValueError:
            check(True, 'bad input rejected')

    # 14: markdown rendering
    md = to_md(base and r)
    check('Priority order' in md and 'Social insurance link' in md
          and 'Must be confirmed manually' in md,
          'markdown output must carry priority, social link and confirm list')

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
