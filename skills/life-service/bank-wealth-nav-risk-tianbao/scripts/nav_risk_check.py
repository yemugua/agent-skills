# -*- coding: utf-8 -*-
"""Bank wealth management NAV, drawdown and risk level checker.

Usage:
  python nav_risk_check.py --file case.json [--out result.md] [--format json]
  python nav_risk_check.py --selftest
"""
import argparse
import json
import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

RISK_LEVELS = {
    'R1': ('low', 'Can accept that the principal is basically unaffected and '
                  'that small short-term NAV moves do not matter.'),
    'R2': ('low-medium', 'Can accept small principal fluctuations while '
                         'expecting the overall outcome to be positive.'),
    'R3': ('medium', 'Can accept NAV declines at times and may hold an '
                     'unrealised loss during the holding period.'),
    'R4': ('medium-high', 'Can accept sizeable NAV drawdowns and understands '
                          'that the cost may not be recovered soon.'),
    'R5': ('high', 'Can accept a large loss of principal, possibly losing '
                   'the whole principal.'),
}


def pct(x):
    return round(float(x) * 100.0 + 1e-9, 4)


def returns_from_navs(navs):
    rs = []
    for i in range(1, len(navs)):
        prev = navs[i - 1]
        if prev <= 0:
            raise ValueError('nav values must be > 0')
        rs.append(navs[i] / prev - 1.0)
    return rs


def std(xs):
    n = len(xs)
    if n < 2:
        return None
    m = sum(xs) / n
    var = sum((x - m) ** 2 for x in xs) / (n - 1)
    return math.sqrt(var)


def max_drawdown(navs):
    peak = navs[0]
    worst = 0.0
    peak_i = 0
    trough_i = 0
    cur_peak_i = 0
    for i, v in enumerate(navs):
        if v > peak:
            peak = v
            cur_peak_i = i
        dd = (peak - v) / peak
        if dd > worst:
            worst = dd
            peak_i = cur_peak_i
            trough_i = i
    return worst, peak_i, trough_i


def calc(data):
    navs = [float(x) for x in data.get('navs', [])]
    if len(navs) < 2:
        raise ValueError('navs must contain at least two values')
    if any(v <= 0 for v in navs):
        raise ValueError('nav values must be > 0')
    initial = float(data.get('initial_nav', navs[0]))
    if initial <= 0:
        raise ValueError('initial_nav must be > 0')
    level = str(data.get('risk_level', '')).upper()
    if level and level not in RISK_LEVELS:
        raise ValueError('risk_level must be one of R1 R2 R3 R4 R5')
    redemption = str(data.get('redemption_rule', '')) or 'UNKNOWN'
    ppy = int(data.get('periods_per_year', 252))
    if ppy <= 0:
        raise ValueError('periods_per_year must be > 0')
    hold_days = int(data.get('hold_days', 0))

    notes = []
    current = navs[-1]
    first = navs[0]
    holding_ret = current / first - 1.0
    nav_ret = current / initial - 1.0
    mdd, pi, ti = max_drawdown(navs)
    rs = returns_from_navs(navs)
    sd = std(rs)
    sd_ann = None if sd is None else sd * math.sqrt(ppy)

    below = current < initial
    drawdown_amp = (initial - current) / initial

    if below:
        notes.append(
            'Current NAV %s is below the initial NAV %s, so the product is in '
            'the below-par state. This is an unrealised position loss. The '
            'realised result is the NAV confirmed on the redemption date.'
            % (round(current, 6), round(initial, 6)))
        notes.append(
            'Being below par does NOT mean the principal is already lost, and '
            'it does NOT mean the product will return to par. Do NOT state '
            'either.')
    else:
        notes.append(
            'Current NAV %s is at or above the initial NAV %s, so the product '
            'is not below par. NOT being below par does NOT mean the '
            'principal is safe.' % (round(current, 6), round(initial, 6)))
        notes.append(
            'Do NOT state that the principal is safe. A net-value product '
            'does not promise principal protection.')

    notes.append(
        'The performance benchmark is a reference standard, NOT a promised '
        'return. Net-value products do not promise principal protection.')
    notes.append(
        'Max drawdown %.4f%% is measured on the supplied history only. Past '
        'volatility is NOT an upper bound for future volatility.'
        % pct(mdd))
    if sd_ann is not None:
        notes.append(
            'Annualised volatility %.4f%% uses %d periods per year. Changing '
            'the period convention changes this number.' % (pct(sd_ann), ppy))
    else:
        notes.append(
            'Only one period of returns is available, so volatility cannot be '
            'computed. Do NOT invent a number.')

    if hold_days > 0:
        notes.append(
            'Holding for %d days means the product value depends on the NAV on '
            'that redemption date, which is unknown in advance.' % hold_days)

    if redemption == 'T+0':
        notes.append(
            'T+0 means same-day arrival of funds, but the redemption is priced '
            'at that day NAV, which may already have fallen. Fast money is '
            'not the same as no volatility.')
    elif redemption in ('T+1', 'T+2', 'T+3'):
        notes.append(
            '%s means funds arrive %s. Weekends and public holidays may push '
            'the arrival further out.' % (redemption, redemption))
    elif redemption == 'UNKNOWN':
        notes.append(
            'Redemption rule was not supplied. Confirm T+0 / T+1 / closed '
            'period from the product documents.')

    level_name, level_desc = RISK_LEVELS.get(
        level, ('UNKNOWN', 'Risk level was not supplied. Confirm it from the '
                          'product page, not from sales talk.'))
    notes.append(
        'Risk level %s is a risk ranking, NOT a return ranking. A higher '
        'level means higher risk, not higher return.' % (level or 'UNKNOWN'))

    return {
        'observations': len(navs),
        'first_nav': round(first, 6),
        'current_nav': round(current, 6),
        'initial_nav': round(initial, 6),
        'holding_period_return_pct': pct(holding_ret),
        'nav_vs_initial_pct': pct(nav_ret),
        'below_initial_nav': below,
        'below_initial_drawdown_pct': pct(drawdown_amp) if below else 0.0,
        'max_drawdown_pct': pct(mdd),
        'max_drawdown_peak_index': pi,
        'max_drawdown_trough_index': ti,
        'period_volatility_pct': pct(sd) if sd is not None else None,
        'annualised_volatility_pct': pct(sd_ann) if sd_ann is not None else None,
        'periods_per_year': ppy,
        'risk_level': level or 'UNKNOWN',
        'risk_level_name': level_name,
        'risk_level_audience': level_desc,
        'redemption_rule': redemption,
        'notes': notes,
        'must_confirm': [
            'product type from the product documents, not from sales talk',
            'performance benchmark is a reference standard, not a promised '
            'return',
            'actual risk level R1 to R5 shown on the product page',
            'own risk assessment result and whether it matches the level',
            'NAV history taken from official disclosure channels',
            'redemption rule and arrival time from the product documents',
            'large-redemption clause and suspension conditions',
            'fee items such as subscription, redemption and management fees',
        ],
    }


def to_md(r):
    L = []
    L.append('# Bank Wealth NAV and Risk Check')
    L.append('')
    L.append('| Item | Value |')
    L.append('|---|---|')
    L.append('| Observations | %d |' % r['observations'])
    L.append('| First NAV | %.6f |' % r['first_nav'])
    L.append('| Current NAV | %.6f |' % r['current_nav'])
    L.append('| Initial NAV | %.6f |' % r['initial_nav'])
    L.append('| Holding period return | %.4f%% |'
             % r['holding_period_return_pct'])
    L.append('| NAV vs initial | %.4f%% |' % r['nav_vs_initial_pct'])
    L.append('| Below initial NAV | %s |'
             % ('YES' if r['below_initial_nav'] else 'NO'))
    L.append('| Below-initial drawdown | %.4f%% |'
             % r['below_initial_drawdown_pct'])
    L.append('| Max drawdown (history) | %.4f%% |' % r['max_drawdown_pct'])
    L.append('| Max drawdown peak / trough index | %d / %d |'
             % (r['max_drawdown_peak_index'], r['max_drawdown_trough_index']))
    L.append('| Period volatility | %s |'
             % ('%.4f%%' % r['period_volatility_pct']
                if r['period_volatility_pct'] is not None else 'N/A'))
    L.append('| Annualised volatility | %s |'
             % ('%.4f%%' % r['annualised_volatility_pct']
                if r['annualised_volatility_pct'] is not None else 'N/A'))
    L.append('| Periods per year | %d |' % r['periods_per_year'])
    L.append('| Risk level | %s (%s) |' % (r['risk_level'], r['risk_level_name']))
    L.append('| Redemption rule | %s |' % r['redemption_rule'])
    L.append('')
    L.append('## Risk level audience')
    L.append('')
    L.append('- %s' % r['risk_level_audience'])
    L.append('')
    L.append('## Notes')
    L.append('')
    for n in r['notes']:
        L.append('- %s' % n)
    L.append('')
    L.append('## Must be confirmed against product documents')
    L.append('')
    for m in r['must_confirm']:
        L.append('- [ ] %s' % m)
    L.append('')
    L.append('Static historical computation on the supplied NAV series. Past '
             'volatility is NOT a future bound. The performance benchmark is '
             'NOT a promised return. Product type, risk level and redemption '
             'rules follow the product documents and the disclosures of the '
             'selling institution. This script gives no forecast and no '
             'recommendation.')
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

    # 1: rising series, no drawdown
    r = calc({'navs': [1.0, 1.01, 1.02, 1.03], 'risk_level': 'R2'})
    check(abs(r['holding_period_return_pct'] - 3.0) < 0.01,
          '1.0 to 1.03 is +3%%, got %s' % r['holding_period_return_pct'])
    check(abs(r['max_drawdown_pct']) < 1e-9,
          'a strictly rising series has zero max drawdown, got %s'
          % r['max_drawdown_pct'])
    check(r['below_initial_nav'] is False, 'rising series is not below par')

    # 2: peak-to-trough drawdown, not an arbitrary window
    r = calc({'navs': [1.0, 1.10, 0.88, 1.05]})
    check(abs(r['max_drawdown_pct'] - 20.0) < 0.01,
          '1.10 peak to 0.88 trough is 20%%, got %s' % r['max_drawdown_pct'])
    check(r['max_drawdown_peak_index'] == 1 and r['max_drawdown_trough_index'] == 2,
          'peak/trough indices should be 1 and 2, got %d and %d'
          % (r['max_drawdown_peak_index'], r['max_drawdown_trough_index']))

    # 3: below par, drawdown amount is a ratio not an amount
    r = calc({'navs': [1.0, 0.98, 1.0], 'initial_nav': 1.0})
    check(r['below_initial_nav'] is False,
          'NAV back at 1.0 is not below par')
    r = calc({'navs': [1.0, 0.98], 'initial_nav': 1.0})
    check(r['below_initial_nav'] is True, '0.98 is below par')
    check(abs(r['below_initial_drawdown_pct'] - 2.0) < 0.01,
          'below-par amplitude should be 2%%, got %s'
          % r['below_initial_drawdown_pct'])
    check(any('does NOT mean the principal is already lost' in n
              for n in r['notes']),
          'below-par must not be equated with a realised principal loss')
    check(any('does NOT mean the product will return to par' in n
              for n in r['notes']),
          'must warn against assuming recovery to par')

    # 4: above par must NOT be called safe
    r = calc({'navs': [1.0, 1.05], 'initial_nav': 1.0})
    check(any('does NOT mean the' in n and 'safe' in n for n in r['notes']),
          'not-below-par must not be reported as principal safety')

    # 5: initial_nav above the first observation
    r = calc({'navs': [1.0, 1.02], 'initial_nav': 1.05})
    check(r['below_initial_nav'] is True,
          'NAV 1.02 against initial 1.05 must be below par')

    # 6: volatility computation
    r = calc({'navs': [1.0, 1.01, 1.0, 1.01], 'periods_per_year': 252})
    check(r['period_volatility_pct'] is not None
          and r['annualised_volatility_pct'] > r['period_volatility_pct'],
          'annualised volatility must exceed period volatility')
    r2 = calc({'navs': [1.0, 1.01, 1.0, 1.01], 'periods_per_year': 12})
    check(r2['annualised_volatility_pct'] < r['annualised_volatility_pct'],
          'fewer periods per year must lower the annualised figure')
    check(any('periods per year' in n for n in r['notes']),
          'period convention must be stated in the notes')

    # 7: only two NAV points -> no volatility, no fabrication
    r = calc({'navs': [1.0, 1.01]})
    check(r['period_volatility_pct'] is None
          and r['annualised_volatility_pct'] is None,
          'a single return has no volatility')
    check(any('cannot be computed' in n for n in r['notes']),
          'missing volatility must be stated, not invented')

    # 8: risk level mapping
    for lv, nm in (('R1', 'low'), ('R3', 'medium'), ('R5', 'high')):
        r = calc({'navs': [1.0, 1.01], 'risk_level': lv})
        check(r['risk_level'] == lv and r['risk_level_name'] == nm,
              '%s should map to %s' % (lv, nm))
        check(len(r['risk_level_audience']) > 20,
              '%s must carry an audience description' % lv)
    r = calc({'navs': [1.0, 1.01]})
    check(r['risk_level'] == 'UNKNOWN'
          and 'not supplied' in r['risk_level_audience'],
          'missing risk level must be reported as unknown')
    check(any('NOT a return ranking' in n for n in r['notes']),
          'risk level must be flagged as not a return ranking')

    # 9: redemption rules
    r = calc({'navs': [1.0, 1.01], 'redemption_rule': 'T+0'})
    check(any('Fast money is' in n for n in r['notes']),
          'T+0 must be qualified by same-day pricing')
    r = calc({'navs': [1.0, 1.01], 'redemption_rule': 'T+1'})
    check(any('holidays' in n for n in r['notes']),
          'T+1 must mention holiday shift')
    r = calc({'navs': [1.0, 1.01]})
    check(r['redemption_rule'] == 'UNKNOWN'
          and any('not supplied' in n for n in r['notes']),
          'missing redemption rule must be reported as unknown')

    # 10: benchmark disclaimer always present
    r = calc({'navs': [1.0, 1.02]})
    joined = ' '.join(r['notes'])
    check('NOT a promised return' in joined,
          'benchmark disclaimer must always be present')
    check('does not promise principal protection' in joined.lower()
          or 'does not promise principal protection' in joined,
          'no-principal-protection wording must always be present')
    low = joined.lower()
    check('guaranteed return' not in low, 'no guaranteed-return claim may appear')
    check('does not mean the principal is safe' in low,
          'the only mention of principal safety must be a negation')
    check('principal is guaranteed' not in low,
          'no principal-guarantee claim may appear')

    # 11: past volatility disclaimer
    r = calc({'navs': [1.0, 1.10, 0.88]})
    check(any('NOT an upper bound' in n for n in r['notes']),
          'past drawdown must be flagged as not a future bound')

    # 12: hold days note
    r = calc({'navs': [1.0, 1.01], 'hold_days': 30})
    check(any('unknown in advance' in n for n in r['notes']),
          'hold days note must say the future NAV is unknown')

    # 13: bad inputs rejected
    for bad in ({'navs': [1.0]},
                {'navs': [1.0, 0.0]},
                {'navs': [1.0, -1.0]},
                {'navs': [1.0, 1.01], 'risk_level': 'R9'},
                {'navs': [1.0, 1.01], 'periods_per_year': 0},
                {'navs': [1.0, 1.01], 'initial_nav': 0}):
        try:
            calc(bad)
            check(False, 'bad input must be rejected: %s' % bad)
        except ValueError:
            check(True, 'bad input rejected')

    # 14: markdown rendering
    md = to_md(calc({'navs': [1.0, 1.01, 0.99], 'risk_level': 'R3',
                     'redemption_rule': 'T+1'}))
    check('Max drawdown' in md and 'Must be confirmed' in md,
          'markdown output must carry the drawdown table and confirm list')

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
