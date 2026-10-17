# -*- coding: utf-8 -*-
"""Individual income tax special additional deduction checker.

用法:
  python deduction_check.py --file case.json [--out result.md] [--format json]
  python deduction_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

STD_INFANT = 2000.0        # per infant per month
STD_CHILD_EDU = 2000.0     # per child per month
STD_EDU_DEGREE = 400.0     # per month
STD_EDU_CERT = 3600.0      # one-off in the year of obtaining certificate
STD_LOAN = 1000.0          # per month
STD_RENT = {1: 1500.0, 2: 1100.0, 3: 800.0}
STD_ELDERLY_ONLY = 3000.0
STD_ELDERLY_TOTAL = 3000.0
STD_ELDERLY_CAP = 1500.0   # per person cap for non-only-child
MED_THRESHOLD = 15000.0
MED_CAP = 80000.0
LOAN_MAX_MONTHS = 240
DEGREE_MAX_MONTHS = 48
ELDERLY_AGE = 60

BRACKETS = [
    (36000.0, 0.03, 0.0),
    (144000.0, 0.10, 2520.0),
    (300000.0, 0.20, 16920.0),
    (420000.0, 0.25, 31920.0),
    (660000.0, 0.30, 52920.0),
    (960000.0, 0.35, 85920.0),
    (float('inf'), 0.45, 181920.0),
]


def money(x):
    return round(float(x) + 1e-9, 2)


def tax_of(taxable):
    if taxable <= 0:
        return 0.0
    prev = 0.0
    for cap, rate, quick in BRACKETS:
        if taxable <= cap:
            return taxable * rate - quick
        prev = cap
    return taxable * 0.45 - 181920.0


def marginal_rate_of(taxable):
    for cap, rate, _q in BRACKETS:
        if taxable <= cap:
            return rate
    return 0.45


def _months(v, label):
    m = float(v)
    if m < 0 or m > 12:
        raise ValueError('%s months must be between 0 and 12' % label)
    return m


def calc(data):
    items = []
    flags = []
    docs = []

    # 3岁以下婴幼儿照护
    for i, inf in enumerate(data.get('infants', [])):
        m = _months(inf.get('months', 0), 'infant')
        share = float(inf.get('share', 1.0))
        if share <= 0 or share > 1:
            raise ValueError('infant share must be in (0, 1]')
        amt = STD_INFANT * m * share
        items.append({'item': 'infant_care_%d' % i, 'standard': STD_INFANT,
                      'months': m, 'share': share, 'amount': money(amt),
                      'status': 'OK'})
        docs.append('infant_care: birth certificate / child info')
        if share > 0.5:
            flags.append('infant_care_%d: share %g exceeds 0.5, both parents '
                         'cannot each claim 100%%' % (i, share))

    # 子女教育
    for i, ch in enumerate(data.get('children', [])):
        if str(ch.get('type', 'education')) != 'education':
            continue
        m = _months(ch.get('months', 0), 'child_education')
        share = float(ch.get('share', 1.0))
        if share <= 0 or share > 1:
            raise ValueError('child share must be in (0, 1]')
        amt = STD_CHILD_EDU * m * share
        items.append({'item': 'child_education_%d' % i, 'standard': STD_CHILD_EDU,
                      'months': m, 'share': share, 'amount': money(amt),
                      'status': 'OK'})
        docs.append('child_education: school enrolment / study record; '
                    'overseas study: admission letter and visa')
        if share > 0.5:
            flags.append('child_education_%d: share %g exceeds 0.5, both parents '
                         'cannot each claim 100%%' % (i, share))

    # 赡养老人
    el = data.get('elderly')
    if el:
        age = float(el.get('parent_age', 0))
        only = bool(el.get('only_child', False))
        share = float(el.get('share', 1.0))
        m = _months(el.get('months', 0), 'elderly')
        if age < ELDERLY_AGE:
            items.append({'item': 'elderly_support', 'standard': STD_ELDERLY_TOTAL,
                          'months': m, 'share': 0.0, 'amount': 0.0,
                          'status': 'NOT_ELIGIBLE_AGE'})
            flags.append('elderly_support: supported person is %g years old, '
                         'below %d, NOT eligible' % (age, ELDERLY_AGE))
        elif only:
            amt = STD_ELDERLY_ONLY * m
            items.append({'item': 'elderly_support', 'standard': STD_ELDERLY_ONLY,
                          'months': m, 'share': 1.0, 'amount': money(amt),
                          'status': 'OK_ONLY_CHILD'})
        else:
            amt = STD_ELDERLY_TOTAL * m * share
            cap = STD_ELDERLY_CAP * m
            st = 'OK_SHARED'
            if amt > cap + 1e-9:
                st = 'EXCEEDS_CAP'
                flags.append('elderly_support: non-only-child share %g gives %.2f, '
                             'exceeds per-person cap %.2f' % (share, amt, cap))
                amt = cap
            items.append({'item': 'elderly_support', 'standard': STD_ELDERLY_TOTAL,
                          'months': m, 'share': share, 'amount': money(amt),
                          'status': st})
        docs.append('elderly_support: ID of supported person; non-only-child '
                    'needs a written sharing agreement')

    # 住房贷款利息
    loan = data.get('housing_loan')
    rent = data.get('housing_rent')
    if loan and loan.get('months', 0) > 0:
        first = bool(loan.get('first_home', False))
        m = _months(loan.get('months', 0), 'housing_loan')
        used = float(loan.get('used_months', 0))
        if used + m > LOAN_MAX_MONTHS:
            months_ok = max(0.0, LOAN_MAX_MONTHS - used)
            flags.append('housing_loan: total months %g exceeds %d cap, '
                         'only %g months allowed'
                         % (used + m, LOAN_MAX_MONTHS, months_ok))
        else:
            months_ok = m
        if not first:
            items.append({'item': 'housing_loan_interest', 'standard': STD_LOAN,
                          'months': m, 'share': 0.0, 'amount': 0.0,
                          'status': 'NOT_FIRST_HOME'})
            flags.append('housing_loan: not a first-home loan, NOT eligible')
        else:
            items.append({'item': 'housing_loan_interest', 'standard': STD_LOAN,
                          'months': months_ok, 'share': 1.0,
                          'amount': money(STD_LOAN * months_ok), 'status': 'OK'})
        docs.append('housing_loan: loan contract and repayment vouchers; '
                    'first-home loan proof')

    # 住房租金
    if rent and rent.get('months', 0) > 0:
        tier = int(rent.get('city_tier', 1))
        if tier not in STD_RENT:
            raise ValueError('city_tier must be 1, 2 or 3')
        m = _months(rent.get('months', 0), 'housing_rent')
        own = bool(rent.get('own_house_in_city', False))
        if own:
            items.append({'item': 'housing_rent', 'standard': STD_RENT[tier],
                          'months': m, 'share': 0.0, 'amount': 0.0,
                          'status': 'OWN_HOUSE_IN_CITY'})
            flags.append('housing_rent: own housing in the main working city, '
                         'NOT eligible')
        else:
            items.append({'item': 'housing_rent', 'standard': STD_RENT[tier],
                          'months': m, 'share': 1.0,
                          'amount': money(STD_RENT[tier] * m), 'status': 'OK'})
        docs.append('housing_rent: lease contract and payment proof')

    # 房贷与租金不可同时享受
    if loan and rent and float(loan.get('months', 0)) > 0 \
            and float(rent.get('months', 0)) > 0:
        flags.append('housing_loan and housing_rent claimed in the same year: '
                     'generally NOT allowed simultaneously, choose one')

    # 继续教育
    ce = data.get('continuing_education')
    if ce:
        dm = _months(ce.get('degree_months', 0), 'degree')
        if dm > 0:
            months_ok = min(dm, float(DEGREE_MAX_MONTHS))
            if dm > DEGREE_MAX_MONTHS:
                flags.append('continuing_education: %g months exceeds %d month cap'
                             % (dm, DEGREE_MAX_MONTHS))
            items.append({'item': 'education_degree', 'standard': STD_EDU_DEGREE,
                          'months': months_ok, 'share': 1.0,
                          'amount': money(STD_EDU_DEGREE * months_ok),
                          'status': 'OK'})
            docs.append('education_degree: student status / tuition record')
        if ce.get('certificate_obtained'):
            items.append({'item': 'education_certificate', 'standard': STD_EDU_CERT,
                          'months': 0, 'share': 1.0, 'amount': money(STD_EDU_CERT),
                          'status': 'OK'})
            docs.append('education_certificate: the vocational qualification '
                        'certificate itself')
        elif ce.get('exam_registered'):
            items.append({'item': 'education_certificate', 'standard': STD_EDU_CERT,
                          'months': 0, 'share': 0.0, 'amount': 0.0,
                          'status': 'CERT_NOT_OBTAINED'})
            flags.append('education_certificate: registered for exam but '
                         'certificate not obtained, NOT eligible')

    # 大病医疗
    med = data.get('medical')
    if med:
        pay = float(med.get('self_pay_total', 0))
        if pay < 0:
            raise ValueError('self_pay_total must be >= 0')
        over = max(0.0, pay - MED_THRESHOLD)
        amt = min(over, MED_CAP)
        st = 'OK' if amt > 0 else 'BELOW_THRESHOLD'
        if amt == 0:
            flags.append('medical: self-paid %.2f does not exceed %.2f '
                         'threshold, deductible amount is 0' % (pay, MED_THRESHOLD))
        items.append({'item': 'serious_medical', 'standard': MED_CAP,
                      'months': 0, 'share': 1.0, 'amount': money(amt),
                      'status': st})
        docs.append('serious_medical: medical bills and medical insurance '
                    'settlement records')

    total = money(sum(x['amount'] for x in items))
    rate = float(data.get('marginal_rate', 0.0))
    if rate <= 0:
        taxable = float(data.get('taxable_income', 0.0))
        rate = marginal_rate_of(taxable) if taxable > 0 else 0.0
    if rate < 0 or rate > 0.45:
        raise ValueError('marginal_rate must be between 0 and 0.45')
    tax_effect = money(total * rate)

    return {
        'year': data.get('year', ''),
        'items': items,
        'flags': flags,
        'documents': sorted(set(docs)),
        'total_deduction': total,
        'marginal_rate': rate,
        'estimated_tax_effect': tax_effect,
        'taxable_income_if_any': float(data.get('taxable_income', 0.0)),
    }


def to_md(r):
    L = []
    L.append('# Special Additional Deduction Check')
    L.append('')
    L.append('| Item | Standard | Months | Share | Amount | Status |')
    L.append('|---|---|---|---|---|---|')
    for it in r['items']:
        L.append('| %s | %.0f | %g | %g | %.2f | %s |'
                 % (it['item'], it['standard'], it['months'], it['share'],
                    it['amount'], it['status']))
    L.append('| **Total** | | | | **%.2f** | |' % r['total_deduction'])
    L.append('')
    L.append('## Tax effect')
    L.append('')
    L.append('- Total annual deduction: %.2f' % r['total_deduction'])
    L.append('- Marginal rate applied: %g' % r['marginal_rate'])
    L.append('- Estimated tax reduction: %.2f' % r['estimated_tax_effect'])
    L.append('- Reminder: deduction amount is NOT the tax saved.')
    L.append('')
    L.append('## Issues')
    L.append('')
    if r['flags']:
        for f in r['flags']:
            L.append('- %s' % f)
    else:
        L.append('- No blocking issue detected from the provided facts.')
    L.append('')
    L.append('## Documents to keep')
    L.append('')
    for d in r['documents']:
        L.append('- %s' % d)
    L.append('')
    L.append('Standards are subject to the tax law and tax authority in force.')
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

    # 1: one child full year at 100%
    r = calc({'year': 2026, 'children': [{'type': 'education', 'months': 12,
                                          'share': 1.0}]})
    check(abs(r['total_deduction'] - 24000.0) < 0.01, 'child education 12 months = 24000')

    # 2: half share
    r = calc({'children': [{'type': 'education', 'months': 12, 'share': 0.5}]})
    check(abs(r['total_deduction'] - 12000.0) < 0.01, 'half share = 12000')

    # 3: both parents 100% flagged
    r = calc({'children': [{'type': 'education', 'months': 12, 'share': 1.0}],
              'infants': [{'months': 12, 'share': 1.0}]})
    check(any('both parents' in f for f in r['flags']), 'duplicate 100% claim flagged')

    # 4: elderly below 60 not eligible
    r = calc({'elderly': {'parent_age': 58, 'only_child': True, 'months': 12}})
    check(r['items'][0]['status'] == 'NOT_ELIGIBLE_AGE'
          and r['items'][0]['amount'] == 0.0, 'age 58 not eligible')

    # 5: only child 3000/month
    r = calc({'elderly': {'parent_age': 65, 'only_child': True, 'months': 12}})
    check(abs(r['items'][0]['amount'] - 36000.0) < 0.01, 'only child = 36000')

    # 6: non-only-child capped at 1500/month
    r = calc({'elderly': {'parent_age': 65, 'only_child': False, 'share': 1.0,
                          'months': 12}})
    check(abs(r['items'][0]['amount'] - 18000.0) < 0.01
          and r['items'][0]['status'] == 'EXCEEDS_CAP',
          'non-only-child capped at 1500/month')

    # 7: non-only-child half share ok
    r = calc({'elderly': {'parent_age': 65, 'only_child': False, 'share': 0.5,
                          'months': 12}})
    check(abs(r['items'][0]['amount'] - 18000.0) < 0.01
          and r['items'][0]['status'] == 'OK_SHARED', 'half share ok')

    # 8: loan + rent conflict flagged
    r = calc({'housing_loan': {'first_home': True, 'months': 12, 'used_months': 0},
              'housing_rent': {'city_tier': 1, 'months': 12,
                               'own_house_in_city': False}})
    check(any('simultaneously' in f for f in r['flags']),
          'loan+rent conflict flagged')

    # 9: not first home not eligible
    r = calc({'housing_loan': {'first_home': False, 'months': 12}})
    check(r['items'][0]['status'] == 'NOT_FIRST_HOME', 'non-first-home rejected')

    # 10: loan 240 month cap
    r = calc({'housing_loan': {'first_home': True, 'months': 12,
                               'used_months': 236}})
    check(abs(r['items'][0]['months'] - 4.0) < 1e-9, 'loan capped at 240 months')

    # 11: medical below threshold
    r = calc({'medical': {'self_pay_total': 14000}})
    check(r['items'][0]['amount'] == 0.0
          and r['items'][0]['status'] == 'BELOW_THRESHOLD', 'medical 14000 -> 0')

    # 12: medical above threshold
    r = calc({'medical': {'self_pay_total': 30000}})
    check(abs(r['items'][0]['amount'] - 15000.0) < 0.01, 'medical 30000 -> 15000')

    # 13: medical cap
    r = calc({'medical': {'self_pay_total': 200000}})
    check(abs(r['items'][0]['amount'] - 80000.0) < 0.01, 'medical capped at 80000')

    # 14: certificate only when obtained
    r = calc({'continuing_education': {'exam_registered': True}})
    check(r['items'][0]['status'] == 'CERT_NOT_OBTAINED', 'exam only not eligible')
    r = calc({'continuing_education': {'certificate_obtained': True}})
    check(abs(r['items'][0]['amount'] - 3600.0) < 0.01, 'certificate = 3600')

    # 15: degree 48 month cap
    r = calc({'continuing_education': {'degree_months': 12}})
    check(abs(r['items'][0]['amount'] - 4800.0) < 0.01, 'degree 12 months = 4800')

    # 16: tax effect uses marginal rate
    r = calc({'children': [{'type': 'education', 'months': 12, 'share': 1.0}],
              'marginal_rate': 0.1})
    check(abs(r['estimated_tax_effect'] - 2400.0) < 0.01,
          '24000 x 10% = 2400, not 24000')

    # 17: rent own house rejected
    r = calc({'housing_rent': {'city_tier': 1, 'months': 12,
                               'own_house_in_city': True}})
    check(r['items'][0]['status'] == 'OWN_HOUSE_IN_CITY', 'own house rejects rent')

    # 18: invalid share rejected
    try:
        calc({'children': [{'months': 12, 'share': 2.0}]})
        check(False, 'share > 1 must be rejected')
    except ValueError:
        check(True, 'share > 1 rejected')

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
