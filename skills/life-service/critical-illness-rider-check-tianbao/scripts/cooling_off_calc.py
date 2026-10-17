# -*- coding: utf-8 -*-
"""Cooling-off period and surrender loss calculator for critical illness riders.

Usage:
  python cooling_off_calc.py --file case.json [--out result.md] [--format json]
  python cooling_off_calc.py --selftest
"""
import argparse
import datetime
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Fallback only. The real cooling-off length MUST come from the contract.
DEFAULT_COOLING_DAYS = 20


def money(x):
    return round(float(x) + 1e-9, 2)


def parse_date(s):
    if isinstance(s, str):
        return datetime.date.fromisoformat(s)
    raise ValueError('contract_date must be YYYY-MM-DD')


def calc(data):
    contract_date = parse_date(data.get('contract_date', '2026-01-01'))
    cooling_days = int(data.get('cooling_off_days', DEFAULT_COOLING_DAYS))
    waiting_days = int(data.get('waiting_days', 0))
    if cooling_days < 0:
        raise ValueError('cooling_off_days must be >= 0')
    if waiting_days < 0:
        raise ValueError('waiting_days must be >= 0')

    as_of = data.get('as_of_date')
    as_of_date = parse_date(as_of) if as_of else datetime.date.today()

    paid = float(data.get('paid_premium', 0))
    cash_value = float(data.get('cash_value', 0))
    if paid < 0:
        raise ValueError('paid_premium must be >= 0')
    if cash_value < 0:
        raise ValueError('cash_value must be >= 0')

    declared_in = data.get('in_cooling_off')
    end_date = contract_date + datetime.timedelta(days=cooling_days)
    waiting_end = contract_date + datetime.timedelta(days=waiting_days)
    elapsed = (as_of_date - contract_date).days

    if elapsed < 0:
        in_cooling = False
    else:
        in_cooling = elapsed <= cooling_days

    if declared_in is not None and bool(declared_in) != in_cooling:
        notes = [
            'Declared cooling-off flag conflicts with the computed result. '
            'Computed value from contract_date + contract cooling_off_days is '
            'authoritative for arithmetic only; the binding answer is what the '
            'insurer confirms in writing.'
        ]
    else:
        notes = []

    # Inside cooling-off: refund scope is whatever the contract stipulates.
    # We only compute the two theoretical ceilings here.
    refund_if_in = float(data.get('contract_refund_if_in', paid))
    refund_if_out = cash_value
    if refund_if_in < 0:
        raise ValueError('contract_refund_if_in must be >= 0')

    loss_in = money(max(0.0, paid - refund_if_in))
    loss_out = money(max(0.0, paid - refund_if_out))
    loss_rate = 0.0 if paid <= 0 else money(loss_out / paid * 100.0)

    status = 'IN_COOLING_OFF' if in_cooling else 'AFTER_COOLING_OFF'
    if elapsed < 0:
        status = 'BEFORE_CONTRACT_DATE'

    if cash_value >= paid and paid > 0:
        notes.append(
            'cash_value >= paid_premium. Verify the cash value table row for '
            'this policy year before drawing any conclusion.')

    if in_cooling:
        notes.append(
            'Still inside cooling-off. Refund scope and any deduction are '
            'stipulated by the contract; this script cannot read the contract.')
        notes.append(
            'Boundary handling for the end date (inclusive or exclusive of the '
            'end day) follows the contract wording. Confirm with the insurer.')
    else:
        notes.append(
            'Cooling-off has expired. Surrender value follows the cash value '
            'table row for this policy year, which is usually much lower than '
            'total premiums paid.')
        notes.append(
            'Unpaid future premiums are not refunded on surrender.')

    notes.append(
        'Waiting-period claim handling is stipulated by the policy wording. '
        'Do NOT state that a waiting-period claim is either payable or '
        'not payable; confirm with the insurer in writing.')
    notes.append(
        'Disclosure duty: an unanswered or understated health question is an '
        'untruthful disclosure, which may lead to non-payment under the '
        'contract. Do NOT state that non-disclosure always means rejection.')

    res = {
        'contract_date': contract_date.isoformat(),
        'as_of_date': as_of_date.isoformat(),
        'cooling_off_days': cooling_days,
        'cooling_off_end_date': end_date.isoformat(),
        'elapsed_days': elapsed,
        'status': status,
        'in_cooling_off': in_cooling,
        'waiting_days': waiting_days,
        'waiting_period_end_date': waiting_end.isoformat(),
        'waiting_period_days_left': max(0, (waiting_end - as_of_date).days),
        'paid_premium': money(paid),
        'cash_value': money(cash_value),
        'refund_if_in_cooling_off': money(refund_if_in),
        'refund_if_after_cooling_off': money(refund_if_out),
        'surrender_loss_in_cooling_off': loss_in,
        'surrender_loss_after_cooling_off': loss_out,
        'surrender_loss_rate_pct': loss_rate,
        'notes': notes,
        'must_confirm': [
            'cooling_off_days value from the policy wording, not from sales talk',
            'contract_date printed in the policy, not the payment date',
            'refund scope and deduction items inside cooling-off, per contract',
            'cash value row for this policy year from the cash value table',
            'waiting-period start point and length per the policy wording',
            'handling of any incident occurring inside the waiting period',
            'underwriting conclusion type if a health issue was disclosed',
        ],
    }
    return res


def to_md(r):
    L = []
    L.append('# Critical Illness Rider: Cooling-off and Surrender Estimate')
    L.append('')
    L.append('| Item | Value |')
    L.append('|---|---|')
    L.append('| Contract date | %s |' % r['contract_date'])
    L.append('| As-of date | %s |' % r['as_of_date'])
    L.append('| Cooling-off days (per contract) | %d |' % r['cooling_off_days'])
    L.append('| Cooling-off end date | %s |' % r['cooling_off_end_date'])
    L.append('| Elapsed days | %d |' % r['elapsed_days'])
    L.append('| Status | %s |' % r['status'])
    L.append('| Waiting-period days (per contract) | %d |' % r['waiting_days'])
    L.append('| Waiting-period end date | %s |' % r['waiting_period_end_date'])
    L.append('| Waiting-period days left | %d |' % r['waiting_period_days_left'])
    L.append('| Premiums paid | %.2f |' % r['paid_premium'])
    L.append('| Cash value (table row) | %.2f |' % r['cash_value'])
    L.append('')
    L.append('## Surrender loss = paid premium - refundable amount')
    L.append('')
    L.append('| Scenario | Refundable | Surrender loss |')
    L.append('|---|---|---|')
    L.append('| Inside cooling-off (contract scope) | %.2f | %.2f |'
             % (r['refund_if_in_cooling_off'], r['surrender_loss_in_cooling_off']))
    L.append('| After cooling-off (cash value) | %.2f | %.2f |'
             % (r['refund_if_after_cooling_off'], r['surrender_loss_after_cooling_off']))
    L.append('')
    L.append('- Loss rate after cooling-off: %.2f%% of premiums paid'
             % r['surrender_loss_rate_pct'])
    L.append('- Cash value is NOT premiums paid. Always read the cash value '
             'table row for the current policy year.')
    L.append('')
    L.append('## Notes')
    L.append('')
    for n in r['notes']:
        L.append('- %s' % n)
    L.append('')
    L.append('## Must be confirmed against contract / insurer')
    L.append('')
    for m in r['must_confirm']:
        L.append('- [ ] %s' % m)
    L.append('')
    L.append('Static estimate only. Cooling-off length, refund scope, cash '
             'value, waiting-period length and claim handling are stipulated by '
             'the insurance contract. Claim decisions rest with the insurer. '
             'This script does not recommend whether to surrender, and it does '
             'not give any medical conclusion.')
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

    # 1: end date arithmetic
    r = calc({'contract_date': '2026-03-01', 'cooling_off_days': 20,
              'as_of_date': '2026-03-10', 'paid_premium': 3000,
              'in_cooling_off': True})
    check(r['cooling_off_end_date'] == '2026-03-21',
          '2026-03-01 + 20 days should be 2026-03-21, got %s'
          % r['cooling_off_end_date'])
    check(r['elapsed_days'] == 9 and r['in_cooling_off'] is True,
          'elapsed 9 days should still be inside cooling-off')
    check(r['status'] == 'IN_COOLING_OFF', 'status should be IN_COOLING_OFF')

    # 2: exactly on the end date, inclusive reading
    r = calc({'contract_date': '2026-03-01', 'cooling_off_days': 20,
              'as_of_date': '2026-03-21', 'paid_premium': 3000})
    check(r['elapsed_days'] == 20 and r['in_cooling_off'] is True,
          'day 20 should be inside cooling-off under the inclusive reading')
    check(any('Boundary handling' in n for n in r['notes']),
          'boundary wording note must be present on the end date')

    # 3: one day after the end date
    r = calc({'contract_date': '2026-03-01', 'cooling_off_days': 20,
              'as_of_date': '2026-03-22', 'paid_premium': 6000,
              'cash_value': 800})
    check(r['in_cooling_off'] is False and r['status'] == 'AFTER_COOLING_OFF',
          'day 21 must be after cooling-off')
    check(abs(r['surrender_loss_after_cooling_off'] - 5200.0) < 0.01,
          'loss after cooling-off should be 6000-800=5200, got %s'
          % r['surrender_loss_after_cooling_off'])
    check(abs(r['surrender_loss_rate_pct'] - (5200.0 / 6000.0 * 100)) < 0.01,
          'loss rate should be 86.67%%')

    # 4: cash value is not premiums paid
    r = calc({'contract_date': '2020-01-01', 'cooling_off_days': 20,
              'as_of_date': '2026-10-01', 'paid_premium': 120000,
              'cash_value': 25000})
    check(r['refund_if_after_cooling_off'] == 25000.0
          and r['paid_premium'] == 120000.0,
          'cash value must stay distinct from premiums paid')
    check(abs(r['surrender_loss_after_cooling_off'] - 95000.0) < 0.01,
          'loss should be 120000-25000=95000')

    # 5: refund inside cooling-off with a contract deduction
    r = calc({'contract_date': '2026-06-01', 'cooling_off_days': 15,
              'as_of_date': '2026-06-05', 'paid_premium': 5000,
              'cash_value': 0, 'contract_refund_if_in': 4800,
              'in_cooling_off': True})
    check(abs(r['surrender_loss_in_cooling_off'] - 200.0) < 0.01,
          'cooling-off loss should be 5000-4800=200')
    check(r['refund_if_after_cooling_off'] == 0.0,
          'cash value 0 means nothing refunded after cooling-off')

    # 6: declared flag conflicts with computed value -> must warn, not silently pass
    r = calc({'contract_date': '2026-03-01', 'cooling_off_days': 20,
              'as_of_date': '2026-06-01', 'paid_premium': 3000,
              'in_cooling_off': True})
    check(r['in_cooling_off'] is False, 'computed status wins over a wrong flag')
    check(any('conflicts' in n for n in r['notes']),
          'a conflict between declared and computed cooling-off must be noted')

    # 7: waiting period
    r = calc({'contract_date': '2026-03-01', 'cooling_off_days': 20,
              'waiting_days': 90, 'as_of_date': '2026-04-01'})
    check(r['waiting_period_end_date'] == '2026-05-30',
          '2026-03-01 + 90 days should be 2026-05-30, got %s'
          % r['waiting_period_end_date'])
    check(r['waiting_period_days_left'] == 59,
          'days left should be 59, got %d' % r['waiting_period_days_left'])
    check(any('not payable' in n for n in r['notes']),
          'waiting-period note must forbid a pay / not-pay conclusion')

    # 8: before the contract date
    r = calc({'contract_date': '2026-05-01', 'cooling_off_days': 20,
              'as_of_date': '2026-04-01', 'paid_premium': 0})
    check(r['elapsed_days'] == -30 and r['status'] == 'BEFORE_CONTRACT_DATE',
          'negative elapsed days must be flagged')

    # 9: negative inputs rejected
    for bad in ({'contract_date': '2026-01-01', 'cooling_off_days': -1},
                {'contract_date': '2026-01-01', 'paid_premium': -100},
                {'contract_date': '2026-01-01', 'cash_value': -5},
                {'contract_date': '2026-01-01', 'waiting_days': -3}):
        try:
            calc(bad)
            check(False, 'negative input must be rejected: %s' % bad)
        except ValueError:
            check(True, 'negative input rejected')

    # 10: cash value above premiums paid is flagged, not accepted silently
    r = calc({'contract_date': '2010-01-01', 'cooling_off_days': 20,
              'as_of_date': '2026-10-01', 'paid_premium': 1000,
              'cash_value': 1500})
    check(any('cash_value >= paid_premium' in n for n in r['notes']),
          'cash value above premiums paid must be flagged')

    # 11: non-guaranteed wording guard
    r = calc({'contract_date': '2026-01-01', 'cooling_off_days': 20,
              'as_of_date': '2026-01-10', 'paid_premium': 10000})
    joined = ' '.join(r['notes'])
    check('guaranteed return' not in joined.lower(),
          'no guaranteed-return wording may appear')

    # 12: markdown rendering does not crash
    md = to_md(calc({'contract_date': '2026-03-01', 'cooling_off_days': 20,
                     'as_of_date': '2026-04-01', 'paid_premium': 4000,
                     'cash_value': 500, 'waiting_days': 90}))
    check('Surrender loss' in md and 'Must be confirmed' in md,
          'markdown output must contain the loss table and the confirm list')

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
