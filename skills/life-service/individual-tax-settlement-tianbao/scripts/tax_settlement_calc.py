# -*- coding: utf-8 -*-
"""Individual income tax annual settlement calculator.

用法:
  python tax_settlement_calc.py --file case.json [--out result.md] [--format json]
  python tax_settlement_calc.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASIC = 60000.0
# annual brackets: (upper bound, rate, quick deduction)
ANNUAL = [
    (36000.0, 0.03, 0.0),
    (144000.0, 0.10, 2520.0),
    (300000.0, 0.20, 16920.0),
    (420000.0, 0.25, 31920.0),
    (660000.0, 0.30, 52920.0),
    (960000.0, 0.35, 85920.0),
    (float('inf'), 0.45, 181920.0),
]
# monthly-converted brackets for lump-sum bonus taxed separately
MONTHLY = [
    (3000.0, 0.03, 0.0),
    (12000.0, 0.10, 210.0),
    (25000.0, 0.20, 1410.0),
    (35000.0, 0.25, 2660.0),
    (55000.0, 0.30, 4410.0),
    (80000.0, 0.35, 7160.0),
    (float('inf'), 0.45, 15160.0),
]
LOW_INCOME_NO_FILING = 120000.0
SMALL_TOP_UP = 400.0


def money(x):
    return round(float(x) + 1e-9, 2)


def tax_by(taxable, table):
    if taxable <= 0:
        return 0.0, table[0][1], table[0][2]
    for cap, rate, quick in table:
        if taxable <= cap:
            return taxable * rate - quick, rate, quick
    return taxable * 0.45 - 181920.0, 0.45, 181920.0


def annual_tax(taxable):
    return tax_by(taxable, ANNUAL)


def bonus_tax_separate(bonus):
    if bonus <= 0:
        return 0.0, 0.0, 0.0
    base = bonus / 12.0
    for cap, rate, quick in MONTHLY:
        if base <= cap:
            return bonus * rate - quick, rate, quick
    return bonus * 0.45 - 15160.0, 0.45, 15160.0


def calc(data):
    year = data.get('year', '')
    income = float(data.get('annual_income', 0))
    special = float(data.get('special_deduction', 0))
    additional = float(data.get('additional_deduction', 0))
    other = float(data.get('other_deduction', 0))
    prepaid = float(data.get('prepaid_tax', 0))
    bonus = float(data.get('bonus', 0) or 0)
    apply_refund = bool(data.get('apply_refund', True))

    for k, v in (('annual_income', income), ('special_deduction', special),
                 ('additional_deduction', additional),
                 ('other_deduction', other), ('prepaid_tax', prepaid),
                 ('bonus', bonus)):
        if v < 0:
            raise ValueError('%s must be >= 0' % k)

    taxable = income - BASIC - special - additional - other
    tax, rate, quick = annual_tax(max(taxable, 0.0))
    tax = max(tax, 0.0)
    diff = tax - prepaid

    if diff > 0.5:
        direction = 'TOP_UP'
    elif diff < -0.5:
        direction = 'REFUND'
    else:
        direction = 'EVEN'

    notes = []
    need_file = None
    if direction == 'TOP_UP':
        if income <= LOW_INCOME_NO_FILING or abs(diff) <= SMALL_TOP_UP:
            need_file = 'MAY_BE_EXEMPT'
            notes.append('Top-up amount is %s and annual income is %s; the '
                         'filing may be exempt under current rules. This is '
                         'NOT an absolute conclusion: confirm with the tax '
                         'authority.' % (money(abs(diff)), money(income)))
        else:
            need_file = 'REQUIRED'
            notes.append('Top-up required: file within the annual settlement '
                         'period. Late payment accrues late fees daily.')
    elif direction == 'REFUND':
        if apply_refund:
            need_file = 'REQUIRED'
            notes.append('Refund available: filing is required to claim it.')
        else:
            need_file = 'OPTIONAL'
            notes.append('Refund available but not claimed: filing can be '
                         'skipped, and the refund is then not obtained.')
    else:
        need_file = 'NOT_REQUIRED'
        notes.append('Prepaid equals tax payable: no filing needed.')

    if taxable <= 0:
        notes.append('Taxable income is %s (<= 0). Tax payable is 0; the '
                     'prepaid amount may be refunded.' % money(taxable))

    res = {
        'year': year,
        'annual_income': money(income),
        'basic_deduction': money(BASIC),
        'special_deduction': money(special),
        'additional_deduction': money(additional),
        'other_deduction': money(other),
        'taxable_income': money(taxable),
        'tax_rate': rate,
        'quick_deduction': money(quick),
        'tax_payable': money(tax),
        'prepaid_tax': money(prepaid),
        'difference': money(diff),
        'direction': direction,
        'filing': need_file,
        'notes': notes,
    }

    if bonus > 0:
        bt, brate, bquick = bonus_tax_separate(bonus)
        sep_total = tax + bt
        combined_taxable = max(taxable + bonus, 0.0)
        ct, crate, cquick = annual_tax(combined_taxable)
        ct = max(ct, 0.0)
        res['bonus'] = {
            'bonus': money(bonus),
            'separate_bonus_tax': money(bt),
            'separate_rate': brate,
            'separate_quick': money(bquick),
            'separate_total_tax': money(sep_total),
            'combined_taxable': money(combined_taxable),
            'combined_rate': crate,
            'combined_total_tax': money(ct),
            'better': 'SEPARATE' if sep_total < ct - 0.5 else (
                'COMBINED' if ct < sep_total - 0.5 else 'SAME'),
            'saving': money(abs(sep_total - ct)),
        }
        res['notes'].append('Bonus: compare both methods before choosing. '
                            'The choice is made by the taxpayer at filing.')
    return res


def to_md(r):
    L = []
    L.append('# Individual Income Tax Annual Settlement Estimate')
    L.append('')
    L.append('| Item | Amount |')
    L.append('|---|---|')
    L.append('| Annual comprehensive income | %.2f |' % r['annual_income'])
    L.append('| Basic deduction | -%.2f |' % r['basic_deduction'])
    L.append('| Special deduction | -%.2f |' % r['special_deduction'])
    L.append('| Additional deduction | -%.2f |' % r['additional_deduction'])
    L.append('| Other deduction | -%.2f |' % r['other_deduction'])
    L.append('| Taxable income | %.2f |' % r['taxable_income'])
    L.append('| Rate / quick deduction | %g / %.2f |'
             % (r['tax_rate'], r['quick_deduction']))
    L.append('| Tax payable | %.2f |' % r['tax_payable'])
    L.append('| Prepaid tax | %.2f |' % r['prepaid_tax'])
    L.append('| Difference | %.2f |' % r['difference'])
    L.append('')
    L.append('## Result: %s (filing: %s)'
             % (r['direction'], r['filing']))
    L.append('')
    for n in r['notes']:
        L.append('- %s' % n)
    b = r.get('bonus')
    if b:
        L.append('')
        L.append('## Lump-sum bonus: two methods')
        L.append('')
        L.append('| Method | Bonus tax | Total tax |')
        L.append('|---|---|---|')
        L.append('| Separate | %.2f | %.2f |'
                 % (b['separate_bonus_tax'], b['separate_total_tax']))
        L.append('| Combined | (included) | %.2f |' % b['combined_total_tax'])
        L.append('')
        L.append('- Lower tax method: **%s**, difference %.2f'
                 % (b['better'], b['saving']))
    L.append('')
    L.append('## Timing')
    L.append('')
    L.append('- Annual settlement period: generally 1 March to 30 June of the '
             'following year, subject to the tax authority announcement.')
    L.append('- Late top-up: late payment fee accrues daily; file early.')
    L.append('')
    L.append('Static estimate only. Prepaid tax must come from the official '
             'app or the withholding agent. Subject to the tax law and tax '
             'authority in force.')
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

    # 1: basic computation
    r = calc({'annual_income': 240000, 'special_deduction': 30000,
              'additional_deduction': 36000, 'other_deduction': 12000,
              'prepaid_tax': 9000})
    check(abs(r['taxable_income'] - 102000.0) < 0.01,
          'taxable income should be 240000-60000-30000-36000-12000=102000')
    # 102000 * 0.10 - 2520 = 7680
    check(abs(r['tax_payable'] - 7680.0) < 0.01,
          'tax payable should be 102000*0.1-2520=7680, got %s' % r['tax_payable'])
    check(r['direction'] == 'REFUND' and abs(r['difference'] - (-1320.0)) < 0.01,
          'should be a refund of 1320')

    # 2: refund not claimed -> optional filing
    r = calc({'annual_income': 240000, 'special_deduction': 30000,
              'additional_deduction': 36000, 'other_deduction': 12000,
              'prepaid_tax': 9000, 'apply_refund': False})
    check(r['filing'] == 'OPTIONAL', 'unclaimed refund -> optional filing')

    # 3: negative taxable income still refundable
    r = calc({'annual_income': 60000, 'prepaid_tax': 500})
    check(r['taxable_income'] <= 0 and r['tax_payable'] == 0.0
          and r['direction'] == 'REFUND',
          'negative taxable income: tax 0, prepaid refundable')

    # 4: taxable 0 with 0 prepaid -> even
    r = calc({'annual_income': 50000, 'prepaid_tax': 0})
    check(r['direction'] == 'EVEN' and r['filing'] == 'NOT_REQUIRED',
          'no prepaid, no tax -> no filing')

    # 5: small top-up exempt wording
    r = calc({'annual_income': 100000, 'prepaid_tax': 0, 'apply_refund': True})
    check(r['direction'] == 'TOP_UP', 'income above 60000 -> top up')
    r = calc({'annual_income': 80000, 'prepaid_tax': 300, 'apply_refund': True})
    check(r['filing'] in ('MAY_BE_EXEMPT', 'REQUIRED'),
          'small top-up gets a filing judgement')

    # 6: large income top-up required
    r = calc({'annual_income': 500000, 'prepaid_tax': 0})
    check(r['filing'] == 'REQUIRED' and r['direction'] == 'TOP_UP',
          'large income with no prepaid -> required top-up')

    # 7: bracket boundary 36000
    t, rate, quick = annual_tax(36000)
    check(abs(t - 1080.0) < 0.01 and rate == 0.03, '36000 -> 1080 at 3%')

    # 8: bracket boundary 36001
    t, rate, quick = annual_tax(36001)
    check(abs(t - (36001 * 0.10 - 2520)) < 0.01 and rate == 0.10,
          '36001 -> 10% bracket')

    # 9: bracket boundary 144000
    t, rate, _q = annual_tax(144000)
    check(abs(t - (144000 * 0.10 - 2520)) < 0.01, '144000 -> 11880')

    # 10: top bracket
    t, rate, _q = annual_tax(1000000)
    check(abs(t - (1000000 * 0.45 - 181920)) < 0.01, '1000000 -> 268080')

    # 11: bonus separate vs combined
    r = calc({'annual_income': 150000, 'special_deduction': 20000,
              'prepaid_tax': 5000, 'bonus': 60000})
    b = r['bonus']
    # bonus 60000 -> /12 = 5000 -> 10% bracket, quick 210 -> 60000*0.1-210 = 5790
    check(abs(b['separate_bonus_tax'] - 5790.0) < 0.01,
          'bonus separate tax should be 5790, got %s' % b['separate_bonus_tax'])
    check(b['better'] in ('SEPARATE', 'COMBINED', 'SAME'), 'bonus comparison done')

    # 12: bonus monthly bracket boundary (3000 is still in the 3% band)
    t, rate, _q = bonus_tax_separate(36000)
    check(abs(t - 1080.0) < 0.01 and rate == 0.03,
          'bonus 36000 -> /12=3000 -> 3% band, tax 1080')
    t, rate, _q = bonus_tax_separate(36012)
    check(abs(t - (36012 * 0.10 - 210)) < 0.01 and rate == 0.10,
          'bonus 36012 -> /12=3001 -> 10% band with quick 210')

    # 13: zero bonus skipped
    r = calc({'annual_income': 100000, 'prepaid_tax': 1000, 'bonus': 0})
    check('bonus' not in r, 'zero bonus should not create bonus section')

    # 14: negative input rejected
    try:
        calc({'annual_income': -1})
        check(False, 'negative income must be rejected')
    except ValueError:
        check(True, 'negative income rejected')

    # 15: no prepaid and no income
    r = calc({'annual_income': 0, 'prepaid_tax': 0})
    check(r['taxable_income'] == -60000.0 and r['tax_payable'] == 0.0,
          'zero income -> taxable -60000, tax 0')

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
