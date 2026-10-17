# -*- coding: utf-8 -*-
"""Flexible employment social insurance contribution and pension estimator.

用法:
  python flexible_insurance_calc.py --file case.json [--out result.md] [--format json]
  python flexible_insurance_calc.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

PENSION_REQUIRED_YEARS = 15.0
DEFAULT_MEDICAL_YEARS = {'male': 25.0, 'female': 20.0}
# common account divisor by retirement age (subject to local rules)
DIVISOR = {50: 195.0, 55: 170.0, 60: 139.0}
DEFAULT_DIVISOR = 139.0


def money(x):
    return round(float(x) + 1e-9, 2)


def divisor_of(age):
    return DIVISOR.get(int(age), DEFAULT_DIVISOR)


def calc(data):
    gender = str(data.get('gender', 'male')).lower()
    if gender not in ('male', 'female'):
        raise ValueError('gender must be male or female')
    age = float(data.get('current_age', 0))
    retire_age = float(data.get('retire_age', 60))
    contributed = float(data.get('contributed_years', 0))
    ratio = float(data.get('base_ratio', 0.6))
    avg_wage = float(data.get('local_avg_wage', 0))
    pension_rate = float(data.get('pension_rate', 0.20))
    account_rate = float(data.get('account_rate', 0.08))
    medical_on = bool(data.get('medical_enabled', False))
    medical_rate = float(data.get('medical_rate', 0.0))
    retire_wage = float(data.get('retire_avg_wage', avg_wage))
    interest = float(data.get('account_interest', 0.0))
    medical_required = float(data.get('medical_required_years',
                                      DEFAULT_MEDICAL_YEARS[gender]))
    medical_done = float(data.get('medical_contributed_years', contributed))

    for k, v in (('current_age', age), ('retire_age', retire_age),
                 ('contributed_years', contributed), ('base_ratio', ratio),
                 ('local_avg_wage', avg_wage), ('pension_rate', pension_rate),
                 ('account_rate', account_rate), ('medical_rate', medical_rate),
                 ('retire_avg_wage', retire_wage)):
        if v < 0:
            raise ValueError('%s must be >= 0' % k)
    if retire_age <= age:
        raise ValueError('retire_age must be greater than current_age')
    if not (0 < ratio <= 3):
        raise ValueError('base_ratio should be between 0 and 3')
    if pension_rate <= 0 or pension_rate > 1:
        raise ValueError('pension_rate should be between 0 and 1')
    if account_rate < 0 or account_rate > pension_rate:
        raise ValueError('account_rate must be between 0 and pension_rate')
    if interest < 0 or interest > 0.2:
        raise ValueError('account_interest looks out of range')

    base = avg_wage * ratio
    pension_monthly = base * pension_rate
    account_monthly = base * account_rate
    medical_monthly = base * medical_rate if medical_on else 0.0
    monthly = pension_monthly + medical_monthly
    yearly = monthly * 12

    years_to_retire = retire_age - age
    future_years = max(years_to_retire, 0.0)
    total_at_retire = contributed + future_years
    pension_gap_before = max(0.0, PENSION_REQUIRED_YEARS - contributed)
    pension_gap_at_retire = max(0.0, PENSION_REQUIRED_YEARS - total_at_retire)
    pension_state = 'MET' if pension_gap_at_retire <= 0 else 'NOT_MET'

    medical_gap = max(0.0, medical_required - medical_done)
    medical_state = 'MET' if medical_gap <= 0 else 'NOT_MET'

    # personal account balance estimate with simple annual interest
    bal = 0.0
    for _ in range(int(round(future_years))):
        bal = (bal + account_monthly * 12) * (1 + interest)
    balance = money(bal)

    # basic pension
    index = ratio
    indexed_wage = retire_wage * index
    basic = (retire_wage + indexed_wage) / 2.0 * total_at_retire * 0.01
    account_pension = balance / divisor_of(retire_age)
    monthly_pension = basic + account_pension

    total_contribution = yearly * future_years

    return {
        'gender': gender,
        'current_age': age,
        'retire_age': retire_age,
        'years_to_retire': money(years_to_retire),
        'contributed_years': contributed,
        'total_years_at_retirement': money(total_at_retire),
        'base_ratio': ratio,
        'monthly_base': money(base),
        'pension_rate': pension_rate,
        'account_rate': account_rate,
        'pension_monthly': money(pension_monthly),
        'account_monthly_credit': money(account_monthly),
        'medical_enabled': medical_on,
        'medical_monthly': money(medical_monthly),
        'total_monthly': money(monthly),
        'total_yearly': money(yearly),
        'future_total_contribution': money(total_contribution),
        'pension_gap_now': money(pension_gap_before),
        'pension_gap_at_retirement': money(pension_gap_at_retire),
        'pension_state': pension_state,
        'medical_required_years': medical_required,
        'medical_contributed_years': medical_done,
        'medical_gap_years': money(medical_gap),
        'medical_state': medical_state,
        'account_balance_estimate': balance,
        'account_divisor': divisor_of(retire_age),
        'basic_pension_estimate': money(basic),
        'account_pension_estimate': money(account_pension),
        'monthly_pension_estimate': money(monthly_pension),
    }


def to_md(r):
    L = []
    L.append('# Flexible Employment Insurance Contribution and Pension Estimate')
    L.append('')
    L.append('| Item | Value |')
    L.append('|---|---|')
    L.append('| Years to retirement | %g |' % r['years_to_retire'])
    L.append('| Contributed years | %g |' % r['contributed_years'])
    L.append('| Total years at retirement | %g |' % r['total_years_at_retirement'])
    L.append('| Base ratio | %g |' % r['base_ratio'])
    L.append('| Monthly base | %.2f |' % r['monthly_base'])
    L.append('| Pension monthly | %.2f |' % r['pension_monthly'])
    L.append('| Personal account monthly credit | %.2f |' % r['account_monthly_credit'])
    L.append('| Medical monthly | %.2f |' % r['medical_monthly'])
    L.append('| Total monthly | %.2f |' % r['total_monthly'])
    L.append('| Total yearly | %.2f |' % r['total_yearly'])
    L.append('| Total until retirement | %.2f |' % r['future_total_contribution'])
    L.append('')
    L.append('## Years status')
    L.append('')
    L.append('- Pension: %s (gap now %g years, gap at retirement %g years)'
             % (r['pension_state'], r['pension_gap_now'],
                r['pension_gap_at_retirement']))
    L.append('- Medical: %s (local rule %g years, gap %g years)'
             % (r['medical_state'], r['medical_required_years'],
                r['medical_gap_years']))
    L.append('')
    L.append('## Pension estimate (NOT a benefit promise)')
    L.append('')
    L.append('| Item | Value |')
    L.append('|---|---|')
    L.append('| Account balance estimate | %.2f |' % r['account_balance_estimate'])
    L.append('| Account divisor | %g |' % r['account_divisor'])
    L.append('| Basic pension estimate | %.2f |' % r['basic_pension_estimate'])
    L.append('| Account pension estimate | %.2f |' % r['account_pension_estimate'])
    L.append('| Monthly pension estimate | %.2f |' % r['monthly_pension_estimate'])
    L.append('')
    L.append('## Notes')
    L.append('')
    if r['pension_state'] == 'NOT_MET':
        L.append('- Pension: NOT MET at retirement. Do NOT report as met.')
    if r['medical_state'] == 'NOT_MET':
        L.append('- Medical: NOT MET. Confirm local top-up or continuation rules.')
    L.append('- Estimate only. Excludes transitional pension, policy changes, '
             'real wage growth path and interest rate changes.')
    L.append('- Actual benefit is subject to the local social security agency.')
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

    base = {'gender': 'male', 'current_age': 38, 'retire_age': 60,
            'contributed_years': 6, 'base_ratio': 0.6, 'local_avg_wage': 8000,
            'pension_rate': 0.20, 'account_rate': 0.08,
            'medical_enabled': True, 'medical_rate': 0.09,
            'retire_avg_wage': 12000, 'account_interest': 0.0}

    # 1: monthly base
    r = calc(dict(base))
    check(abs(r['monthly_base'] - 4800.0) < 0.01, 'base = 8000 x 0.6 = 4800')

    # 2: pension monthly
    check(abs(r['pension_monthly'] - 960.0) < 0.01, 'pension = 4800 x 0.20 = 960')

    # 3: account credit
    check(abs(r['account_monthly_credit'] - 384.0) < 0.01,
          'account credit = 4800 x 0.08 = 384')

    # 4: medical monthly
    check(abs(r['medical_monthly'] - 432.0) < 0.01, 'medical = 4800 x 0.09 = 432')

    # 5: total monthly and yearly
    check(abs(r['total_monthly'] - 1392.0) < 0.01, 'total monthly = 1392')
    check(abs(r['total_yearly'] - 16704.0) < 0.01, 'total yearly = 16704')

    # 6: years at retirement
    check(abs(r['total_years_at_retirement'] - 28.0) < 0.01,
          '6 + 22 = 28 years at retirement')

    # 7: pension met
    check(r['pension_state'] == 'MET', '28 years >= 15 -> MET')

    # 8: pension not met when short
    b = dict(base)
    b['contributed_years'] = 0
    b['current_age'] = 59
    r2 = calc(b)
    check(r2['pension_state'] == 'NOT_MET'
          and abs(r2['pension_gap_at_retirement'] - 14.0) < 0.01,
          '1 year contributed -> NOT MET, gap 14')

    # 9: account balance with no interest
    r = calc(dict(base))
    check(abs(r['account_balance_estimate'] - 384 * 12 * 22) < 1.0,
          'balance = 384 x 12 x 22 without interest')

    # 10: balance with interest is larger
    b = dict(base)
    b['account_interest'] = 0.02
    r3 = calc(b)
    check(r3['account_balance_estimate'] > r['account_balance_estimate'],
          'positive interest increases the balance')

    # 11: basic pension formula
    # (12000 + 12000*0.6)/2 * 28 * 1% = 9600*28*0.01 = 2688
    check(abs(r['basic_pension_estimate'] - 2688.0) < 0.01,
          'basic pension = (12000+7200)/2 x 28 x 1%% = 2688, got %s'
          % r['basic_pension_estimate'])

    # 12: divisor by retirement age
    check(divisor_of(60) == 139.0 and divisor_of(55) == 170.0
          and divisor_of(50) == 195.0, 'divisors 60/55/50 = 139/170/195')

    # 13: account pension = balance / divisor
    check(abs(r['account_pension_estimate']
              - r['account_balance_estimate'] / 139.0) < 0.01,
          'account pension = balance / 139')

    # 14: medical gap default male
    check(abs(r['medical_gap_years'] - (25 - 6)) < 0.01,
          'male medical gap = 25 - 6 = 19')

    # 15: medical gap default female
    b = dict(base)
    b['gender'] = 'female'
    r4 = calc(b)
    check(abs(r4['medical_gap_years'] - (20 - 6)) < 0.01,
          'female medical gap = 20 - 6 = 14')

    # 16: medical disabled -> zero medical fee
    b = dict(base)
    b['medical_enabled'] = False
    r5 = calc(b)
    check(r5['medical_monthly'] == 0.0
          and abs(r5['total_monthly'] - 960.0) < 0.01,
          'medical disabled -> only pension fee')

    # 17: invalid retire age rejected
    try:
        b = dict(base)
        b['retire_age'] = 30
        calc(b)
        check(False, 'retire_age <= current_age must be rejected')
    except ValueError:
        check(True, 'invalid retire_age rejected')

    # 18: invalid base ratio rejected
    try:
        b = dict(base)
        b['base_ratio'] = 5
        calc(b)
        check(False, 'base_ratio > 3 must be rejected')
    except ValueError:
        check(True, 'invalid base_ratio rejected')

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
