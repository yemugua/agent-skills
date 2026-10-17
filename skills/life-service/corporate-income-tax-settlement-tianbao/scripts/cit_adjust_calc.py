# -*- coding: utf-8 -*-
"""Corporate income tax annual settlement adjustment calculator.

用法:
  python cit_adjust_calc.py --file case.json [--out result.md] [--format json]
  python cit_adjust_calc.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ENT_60 = 0.60
ENT_REV = 0.005      # 5 per mille of revenue
AD_RATE = 0.15
WELFARE = 0.14
UNION = 0.02
EDU = 0.08
DONATION = 0.12
DEFAULT_RATE = 0.25
SMALL_LOW_RATE = 0.20
SMALL_LOW_INCLUDE = 0.25   # effectively 5% burden
HIGH_TECH_RATE = 0.15
SMALL_LOW_CAP = 3000000.0
LOSS_CARRY_YEARS = 5


def money(x):
    return round(float(x) + 1e-9, 2)


def calc(data):
    profit = float(data.get('accounting_profit', 0))
    revenue = float(data.get('revenue', 0))
    wage = float(data.get('wage_total', 0))
    ent = float(data.get('entertainment', 0))
    ad = float(data.get('advertising', 0))
    welfare = float(data.get('welfare', 0))
    union = float(data.get('union_fee', 0))
    edu = float(data.get('education_fee', 0))
    donation = float(data.get('donation', 0))
    rd = float(data.get('rd_expense', 0))
    rd_rate = float(data.get('rd_add_rate', 0.0))
    penalty = float(data.get('penalty', 0))
    sponsorship = float(data.get('sponsorship', 0))
    other_nondeduct = float(data.get('other_nondeductible', 0))
    prior_loss = float(data.get('prior_loss', 0))
    rate = float(data.get('tax_rate', DEFAULT_RATE))
    small = bool(data.get('small_low_profit', False))
    hitech = bool(data.get('high_tech', False))
    ad_rate = float(data.get('advertising_rate', AD_RATE))

    for k, v in (('revenue', revenue), ('wage_total', wage),
                 ('entertainment', ent), ('advertising', ad),
                 ('welfare', welfare), ('union_fee', union),
                 ('education_fee', edu), ('donation', donation),
                 ('rd_expense', rd), ('penalty', penalty),
                 ('sponsorship', sponsorship),
                 ('other_nondeductible', other_nondeduct),
                 ('prior_loss', prior_loss)):
        if v < 0:
            raise ValueError('%s must be >= 0' % k)
    if rate <= 0 or rate > 0.5:
        raise ValueError('tax_rate looks out of range')
    if rd_rate < 0 or rd_rate > 2:
        raise ValueError('rd_add_rate looks out of range')

    items = []

    def add(name, amount, limit, allowed, addback, carry, note):
        items.append({'item': name, 'amount': money(amount),
                      'limit': money(limit), 'allowed': money(allowed),
                      'adjust': money(addback), 'carry_forward': money(carry),
                      'note': note})

    # entertainment: min(60% of expense, 0.5% of revenue)
    ent_limit = min(ent * ENT_60, revenue * ENT_REV)
    add('entertainment', ent, ent_limit, ent_limit, ent - ent_limit, 0.0,
        'min(60%% of expense, 0.5%% of revenue); excess never carries forward')

    # advertising: 15% of revenue, excess carries forward
    ad_limit = revenue * ad_rate
    ad_allowed = min(ad, ad_limit)
    ad_carry = max(0.0, ad - ad_limit)
    add('advertising', ad, ad_limit, ad_allowed, ad - ad_allowed, ad_carry,
        'rate %g of revenue; excess carries forward' % ad_rate)

    # welfare 14% of wage
    w_limit = wage * WELFARE
    add('welfare', welfare, w_limit, min(welfare, w_limit),
        max(0.0, welfare - w_limit), 0.0, '14% of total wages')

    # union 2%
    u_limit = wage * UNION
    add('union_fee', union, u_limit, min(union, u_limit),
        max(0.0, union - u_limit), 0.0, '2% of total wages')

    # education 8%
    e_limit = wage * EDU
    e_carry = max(0.0, edu - e_limit)
    add('education_fee', edu, e_limit, min(edu, e_limit), e_carry, e_carry,
        '8% of total wages; excess carries forward')

    # donation 12% of accounting profit (positive profit only)
    d_base = max(profit, 0.0)
    d_limit = d_base * DONATION
    d_carry = max(0.0, donation - d_limit)
    add('donation', donation, d_limit, min(donation, d_limit), d_carry,
        d_carry, '12% of accounting profit; excess carries forward 3 years')

    # R&D super deduction -> reduction
    rd_cut = rd * rd_rate
    items.append({'item': 'rd_super_deduction', 'amount': money(rd),
                  'limit': money(rd), 'allowed': money(rd),
                  'adjust': money(-rd_cut), 'carry_forward': 0.0,
                  'note': 'extra deduction at rate %g (subject to rules '
                          'in force and proper cost allocation)' % rd_rate})

    # non-deductible items
    nondeduct = penalty + sponsorship + other_nondeduct
    items.append({'item': 'non_deductible', 'amount': money(nondeduct),
                  'limit': 0.0, 'allowed': 0.0, 'adjust': money(nondeduct),
                  'carry_forward': 0.0,
                  'note': 'late fee, fines, sponsorship, unapproved reserves'})

    add_total = sum(i['adjust'] for i in items)          # positive = add back
    taxable_before_loss = max(profit + add_total, -10 ** 12)
    loss_used = min(max(prior_loss, 0.0), max(taxable_before_loss, 0.0))
    taxable = taxable_before_loss - loss_used
    loss_remaining = max(prior_loss, 0.0) - loss_used
    taxable_for_tax = max(taxable, 0.0)

    if taxable_for_tax <= 0:
        applied_rate = 0.0
        rate_basis = 'no tax payable (taxable income <= 0)'
        tax = 0.0
    elif hitech:
        applied_rate = HIGH_TECH_RATE
        rate_basis = 'high-tech preferential rate (qualification must be valid)'
        tax = taxable_for_tax * HIGH_TECH_RATE
    elif small and taxable_for_tax <= SMALL_LOW_CAP:
        applied_rate = SMALL_LOW_RATE * SMALL_LOW_INCLUDE
        rate_basis = 'small low-profit enterprise preferential computation'
        tax = taxable_for_tax * SMALL_LOW_INCLUDE * SMALL_LOW_RATE
    else:
        applied_rate = rate
        rate_basis = 'statutory / specified rate'
        tax = taxable_for_tax * rate

    burden = (tax / money(profit)) if profit > 0 else 0.0

    return {
        'accounting_profit': money(profit),
        'items': items,
        'total_adjustment': money(add_total),
        'taxable_before_loss': money(taxable_before_loss),
        'prior_loss': money(prior_loss),
        'loss_used': money(loss_used),
        'loss_remaining': money(loss_remaining),
        'loss_carry_years': LOSS_CARRY_YEARS,
        'taxable_income': money(taxable),
        'applied_rate': applied_rate,
        'rate_basis': rate_basis,
        'tax_payable': money(tax),
        'effective_burden_on_profit': round(burden, 4),
        'advertising_carry_forward': money(ad_carry),
        'education_carry_forward': money(e_carry),
        'donation_carry_forward': money(d_carry),
    }


def to_md(r):
    L = []
    L.append('# Corporate Income Tax Adjustment Estimate')
    L.append('')
    L.append('| Item | Amount | Limit | Allowed | Adjustment | Carry forward |')
    L.append('|---|---|---|---|---|---|')
    for i in r['items']:
        L.append('| %s | %.2f | %.2f | %.2f | %.2f | %.2f |'
                 % (i['item'], i['amount'], i['limit'], i['allowed'],
                    i['adjust'], i['carry_forward']))
    L.append('')
    L.append('| Step | Amount |')
    L.append('|---|---|')
    L.append('| Accounting profit | %.2f |' % r['accounting_profit'])
    L.append('| Total adjustment | %.2f |' % r['total_adjustment'])
    L.append('| Before loss relief | %.2f |' % r['taxable_before_loss'])
    L.append('| Loss used | %.2f |' % r['loss_used'])
    L.append('| Taxable income | %.2f |' % r['taxable_income'])
    L.append('| Applied rate | %g (%s) |' % (r['applied_rate'], r['rate_basis']))
    L.append('| Tax payable | %.2f |' % r['tax_payable'])
    L.append('')
    L.append('## Notes')
    L.append('')
    L.append('- Loss remaining to carry forward: %.2f (carry years %d, '
             'subject to rules in force)'
             % (r['loss_remaining'], r['loss_carry_years']))
    L.append('- Advertising carry forward: %.2f' % r['advertising_carry_forward'])
    L.append('- Education carry forward: %.2f' % r['education_carry_forward'])
    L.append('- Donation carry forward: %.2f' % r['donation_carry_forward'])
    if r['taxable_income'] <= 0:
        L.append('- Taxable income <= 0: no corporate income tax payable '
                 'this year.')
    L.append('- Settlement due within 5 months from year end (31 May); '
             'late filing accrues late fees daily.')
    L.append('- Static estimate. Ratios and conditions are subject to the '
             'tax law and tax authority in force.')
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

    base = {'accounting_profit': 1000000, 'revenue': 10000000,
            'wage_total': 2000000, 'entertainment': 100000,
            'advertising': 1000000, 'welfare': 300000, 'union_fee': 50000,
            'education_fee': 200000, 'donation': 100000, 'rd_expense': 0,
            'rd_add_rate': 0.0, 'penalty': 0, 'sponsorship': 0,
            'prior_loss': 0, 'tax_rate': 0.25}

    # 1: entertainment capped by 0.5% of revenue
    r = calc(dict(base))
    ent = [i for i in r['items'] if i['item'] == 'entertainment'][0]
    # 100000*0.6 = 60000; 10000000*0.005 = 50000 -> limit 50000, addback 50000
    check(abs(ent['limit'] - 50000.0) < 0.01 and abs(ent['adjust'] - 50000.0) < 0.01,
          'entertainment limited to 50000 (0.5%% of revenue), got %s'
          % ent['limit'])

    # 2: entertainment capped by 60% when revenue is large
    b = dict(base)
    b['revenue'] = 100000000
    r2 = calc(b)
    ent2 = [i for i in r2['items'] if i['item'] == 'entertainment'][0]
    check(abs(ent2['limit'] - 60000.0) < 0.01,
          'entertainment limited to 60000 (60%% of expense)')

    # 3: advertising within limit
    ad = [i for i in r['items'] if i['item'] == 'advertising'][0]
    check(abs(ad['limit'] - 1500000.0) < 0.01 and ad['adjust'] == 0.0,
          'advertising 1,000,000 within 15%% limit')

    # 4: advertising excess carries forward
    b = dict(base)
    b['advertising'] = 3000000
    r3 = calc(b)
    ad3 = [i for i in r3['items'] if i['item'] == 'advertising'][0]
    check(abs(ad3['adjust'] - 1500000.0) < 0.01
          and abs(ad3['carry_forward'] - 1500000.0) < 0.01,
          'advertising excess 1,500,000 carries forward')

    # 5: welfare 14%
    w = [i for i in r['items'] if i['item'] == 'welfare'][0]
    check(abs(w['limit'] - 280000.0) < 0.01 and abs(w['adjust'] - 20000.0) < 0.01,
          'welfare limit 280000, addback 20000')

    # 6: union 2%
    u = [i for i in r['items'] if i['item'] == 'union_fee'][0]
    check(abs(u['limit'] - 40000.0) < 0.01 and abs(u['adjust'] - 10000.0) < 0.01,
          'union limit 40000, addback 10000')

    # 7: education 8% with carry forward
    e = [i for i in r['items'] if i['item'] == 'education_fee'][0]
    check(abs(e['limit'] - 160000.0) < 0.01
          and abs(e['carry_forward'] - 40000.0) < 0.01,
          'education limit 160000, carry 40000')

    # 8: donation 12% of profit
    d = [i for i in r['items'] if i['item'] == 'donation'][0]
    check(abs(d['limit'] - 120000.0) < 0.01 and d['adjust'] == 0.0,
          'donation 100000 within 12%% of 1000000')

    # 9: R&D super deduction reduces
    b = dict(base)
    b['rd_expense'] = 500000
    b['rd_add_rate'] = 1.0
    r4 = calc(b)
    rd = [i for i in r4['items'] if i['item'] == 'rd_super_deduction'][0]
    check(abs(rd['adjust'] + 500000.0) < 0.01, 'R&D 500000 x 100% reduction')

    # 10: non-deductible fully added back
    b = dict(base)
    b['penalty'] = 20000
    b['sponsorship'] = 30000
    r5 = calc(b)
    nd = [i for i in r5['items'] if i['item'] == 'non_deductible'][0]
    check(abs(nd['adjust'] - 50000.0) < 0.01, 'penalty + sponsorship added back')

    # 11: loss relief
    b = dict(base)
    b['prior_loss'] = 300000
    r6 = calc(b)
    check(abs(r6['loss_used'] - 300000.0) < 0.01, 'loss of 300000 fully used')

    # 12: loss capped by taxable income
    b = dict(base)
    b['prior_loss'] = 99999999
    r7 = calc(b)
    check(r7['loss_used'] <= r7['taxable_before_loss'] + 0.01,
          'loss used cannot exceed taxable income before relief')
    check(r7['taxable_income'] <= 0.0, 'taxable income floors at 0')

    # 13: high-tech rate
    b = dict(base)
    b['high_tech'] = True
    r8 = calc(b)
    check(abs(r8['applied_rate'] - 0.15) < 1e-9, 'high-tech rate 15%')

    # 14: small low-profit computation
    b = dict(base)
    b['small_low_profit'] = True
    r9 = calc(b)
    check(abs(r9['applied_rate'] - 0.05) < 1e-9, 'small low-profit = 5% burden')

    # 15: statutory rate default
    check(abs(r['applied_rate'] - 0.25) < 1e-9, 'default statutory rate 25%')

    # 16: negative taxable income -> no tax
    b = dict(base)
    b['accounting_profit'] = -500000
    r10 = calc(b)
    check(r10['tax_payable'] == 0.0 and r10['taxable_income'] < 0,
          'loss year -> no tax payable')

    # 17: negative input rejected
    try:
        b = dict(base)
        b['revenue'] = -1
        calc(b)
        check(False, 'negative revenue must be rejected')
    except ValueError:
        check(True, 'negative revenue rejected')

    # 18: bad tax rate rejected
    try:
        b = dict(base)
        b['tax_rate'] = 2.0
        calc(b)
        check(False, 'tax_rate out of range must be rejected')
    except ValueError:
        check(True, 'bad tax_rate rejected')

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
