# -*- coding: utf-8 -*-
"""Social security contribution years and retroactive payment calculator.

用法:
  python contribution_years.py --file case.json [--out result.md] [--format json]
  python contribution_years.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

PENSION_REQUIRED_MONTHS = 180      # 15 years
DEFAULT_MEDICAL_YEARS = {'male': 25, 'female': 20}   # local rules vary
DEFAULT_LATE_DAILY_RATE = 0.0005   # local rules vary


def money(x):
    return round(float(x) + 1e-9, 2)


def months_text(m):
    y = int(m) // 12
    r = int(m) % 12
    return '%d years %d months' % (y, r)


def assess(total_months, required_months):
    """Strict month-level judgement."""
    gap = required_months - total_months
    if gap <= 0:
        return 'MET', 0
    return 'NOT_MET', gap


def calc(data):
    gender = str(data.get('gender', 'male')).lower()
    if gender not in ('male', 'female'):
        raise ValueError('gender must be male or female')
    pension_actual = float(data.get('pension_actual_months', 0))
    pension_deemed = float(data.get('pension_deemed_months', 0))
    deemed_confirmed = bool(data.get('deemed_confirmed', False))
    medical_actual = float(data.get('medical_actual_months', 0))
    medical_required_years = float(data.get('medical_required_years',
                                            DEFAULT_MEDICAL_YEARS[gender]))
    retro_months = float(data.get('retro_months', 0))
    base = float(data.get('monthly_base', 0))
    rate = float(data.get('total_rate', 0))
    late_rate = float(data.get('late_daily_rate', DEFAULT_LATE_DAILY_RATE))
    late_days = float(data.get('late_days', 0))

    for k, v in (('pension_actual_months', pension_actual),
                 ('pension_deemed_months', pension_deemed),
                 ('medical_actual_months', medical_actual),
                 ('retro_months', retro_months),
                 ('monthly_base', base),
                 ('total_rate', rate),
                 ('late_days', late_days)):
        if v < 0:
            raise ValueError('%s must be >= 0' % k)
    if medical_required_years <= 0:
        raise ValueError('medical_required_years must be positive')
    if rate < 0 or rate > 1:
        raise ValueError('total_rate should be between 0 and 1')
    if late_rate < 0 or late_rate > 0.01:
        raise ValueError('late_daily_rate looks out of range')

    # Deemed years count ONLY when confirmed by archive / authority.
    deemed_counted = pension_deemed if deemed_confirmed else 0.0
    pension_total = pension_actual + deemed_counted
    pension_state, pension_gap = assess(pension_total, PENSION_REQUIRED_MONTHS)

    medical_required_months = medical_required_years * 12
    medical_state, medical_gap = assess(medical_actual, medical_required_months)

    principal = retro_months * base * rate
    late_fee = principal * late_rate * late_days
    total = principal + late_fee

    pension_after = pension_total + retro_months
    pension_state_after, pension_gap_after = assess(pension_after,
                                                    PENSION_REQUIRED_MONTHS)

    return {
        'gender': gender,
        'pension_actual_months': pension_actual,
        'pension_deemed_months': pension_deemed,
        'deemed_confirmed': deemed_confirmed,
        'deemed_counted_months': deemed_counted,
        'pension_total_months': pension_total,
        'pension_total_text': months_text(pension_total),
        'pension_required_months': PENSION_REQUIRED_MONTHS,
        'pension_state': pension_state,
        'pension_gap_months': pension_gap,
        'pension_state_after_retro': pension_state_after,
        'pension_gap_after_retro': pension_gap_after,
        'medical_actual_months': medical_actual,
        'medical_required_years': medical_required_years,
        'medical_required_months': medical_required_months,
        'medical_state': medical_state,
        'medical_gap_months': medical_gap,
        'retro_months': retro_months,
        'monthly_base': money(base),
        'total_rate': rate,
        'principal': money(principal),
        'late_daily_rate': late_rate,
        'late_days': late_days,
        'late_fee': money(late_fee),
        'total_cost': money(total),
    }


def warnings_of(r):
    w = []
    if r['pension_state'] == 'NOT_MET':
        w.append('Pension: NOT MET. Gap %d months. Do NOT report as met.'
                 % r['pension_gap_months'])
    else:
        w.append('Pension: accumulated contribution reaches 15 years.')
    if r['pension_deemed_months'] > 0 and not r['deemed_confirmed']:
        w.append('Deemed years NOT confirmed: counted as 0 in this estimate.')
    if r['medical_state'] == 'NOT_MET':
        w.append('Medical insurance: NOT MET. Gap %d months (local rule: %g years).'
                 % (r['medical_gap_months'], r['medical_required_years']))
    if r['pension_state_after_retro'] == 'NOT_MET':
        w.append('Even after retro payment, pension still NOT MET (%d months short).'
                 % r['pension_gap_after_retro'])
    if r['late_fee'] > 0:
        w.append('Late fee is an estimate at daily rate %g; confirm start date '
                 'and days with the local agency.' % r['late_daily_rate'])
    w.append('Static estimate only. Base, rate and late fee are subject to '
             'the local social security agency.')
    return w


def to_md(r):
    L = []
    L.append('# Social Security Contribution Years and Retroactive Payment Estimate')
    L.append('')
    L.append('| Item | Value |')
    L.append('|---|---|')
    L.append('| Pension actual months | %g |' % r['pension_actual_months'])
    L.append('| Pension deemed months (input) | %g |' % r['pension_deemed_months'])
    L.append('| Deemed confirmed | %s |' % r['deemed_confirmed'])
    L.append('| Deemed months counted | %g |' % r['deemed_counted_months'])
    L.append('| Pension accumulated | %s (%g months) |'
             % (r['pension_total_text'], r['pension_total_months']))
    L.append('| Pension required | 180 months (15 years) |')
    L.append('| Pension status | %s (gap %d months) |'
             % (r['pension_state'], r['pension_gap_months']))
    L.append('| Medical accumulated | %g months |' % r['medical_actual_months'])
    L.append('| Medical required | %g years (%g months, LOCAL RULE) |'
             % (r['medical_required_years'], r['medical_required_months']))
    L.append('| Medical status | %s (gap %d months) |'
             % (r['medical_state'], r['medical_gap_months']))
    L.append('')
    L.append('## Retroactive Payment Cost')
    L.append('')
    L.append('| Item | Value |')
    L.append('|---|---|')
    L.append('| Retro months | %g |' % r['retro_months'])
    L.append('| Monthly base | %.2f |' % r['monthly_base'])
    L.append('| Total rate | %g |' % r['total_rate'])
    L.append('| Principal | %.2f |' % r['principal'])
    L.append('| Late fee (rate %g x %g days) | %.2f |'
             % (r['late_daily_rate'], r['late_days'], r['late_fee']))
    L.append('| Total | %.2f |' % r['total_cost'])
    L.append('| Pension status after retro | %s (gap %d months) |'
             % (r['pension_state_after_retro'], r['pension_gap_after_retro']))
    L.append('')
    L.append('## Notes')
    L.append('')
    for w in warnings_of(r):
        L.append('- %s' % w)
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

    # 1: 179 months is NOT met
    r = calc({'gender': 'male', 'pension_actual_months': 179,
              'pension_deemed_months': 0, 'medical_actual_months': 300,
              'retro_months': 0, 'monthly_base': 4000, 'total_rate': 0.2,
              'late_days': 0})
    check(r['pension_state'] == 'NOT_MET' and r['pension_gap_months'] == 1,
          '179 months must be NOT_MET with gap 1')

    # 2: exactly 180 months is met
    r = calc({'gender': 'male', 'pension_actual_months': 180,
              'medical_actual_months': 300})
    check(r['pension_state'] == 'MET' and r['pension_gap_months'] == 0,
          '180 months must be MET')

    # 3: deemed years not confirmed must count as 0
    r = calc({'gender': 'male', 'pension_actual_months': 100,
              'pension_deemed_months': 80, 'deemed_confirmed': False,
              'medical_actual_months': 300})
    check(r['deemed_counted_months'] == 0 and r['pension_state'] == 'NOT_MET',
          'unconfirmed deemed years must not be counted')

    # 4: confirmed deemed years are counted
    r = calc({'gender': 'male', 'pension_actual_months': 100,
              'pension_deemed_months': 80, 'deemed_confirmed': True,
              'medical_actual_months': 300})
    check(r['deemed_counted_months'] == 80 and r['pension_state'] == 'MET',
          'confirmed deemed years must be counted')

    # 5: principal math
    r = calc({'gender': 'male', 'pension_actual_months': 200,
              'medical_actual_months': 300, 'retro_months': 12,
              'monthly_base': 5000, 'total_rate': 0.2, 'late_days': 0})
    check(abs(r['principal'] - 12000.0) < 0.01,
          'principal should be 12*5000*0.2=12000, got %s' % r['principal'])

    # 6: late fee math
    r = calc({'gender': 'male', 'pension_actual_months': 200,
              'medical_actual_months': 300, 'retro_months': 12,
              'monthly_base': 5000, 'total_rate': 0.2,
              'late_daily_rate': 0.0005, 'late_days': 1000})
    check(abs(r['late_fee'] - 6000.0) < 0.01,
          'late fee should be 12000*0.0005*1000=6000, got %s' % r['late_fee'])
    check(abs(r['total_cost'] - 18000.0) < 0.01, 'total should be 18000')

    # 7: medical gap default female 20 years
    r = calc({'gender': 'female', 'pension_actual_months': 200,
              'medical_actual_months': 200})
    check(r['medical_required_months'] == 240 and r['medical_gap_months'] == 40,
          'female default medical required 240 months, gap 40')

    # 8: medical gap default male 25 years
    r = calc({'gender': 'male', 'pension_actual_months': 200,
              'medical_actual_months': 200})
    check(r['medical_required_months'] == 300 and r['medical_gap_months'] == 100,
          'male default medical required 300 months, gap 100')

    # 9: retro fills the gap
    r = calc({'gender': 'male', 'pension_actual_months': 172,
              'medical_actual_months': 300, 'retro_months': 8,
              'monthly_base': 4500, 'total_rate': 0.2, 'late_days': 0})
    check(r['pension_state'] == 'NOT_MET' and r['pension_state_after_retro'] == 'MET',
          'retro of 8 months should fill an 8-month gap')

    # 10: invalid input rejected
    try:
        calc({'gender': 'other', 'pension_actual_months': 100})
        check(False, 'invalid gender must be rejected')
    except ValueError:
        check(True, 'invalid gender rejected')

    # 11: negative months rejected
    try:
        calc({'gender': 'male', 'pension_actual_months': -5})
        check(False, 'negative months must be rejected')
    except ValueError:
        check(True, 'negative months rejected')

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
