#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A/B test sample size calculator and SRM (sampling ratio mismatch) checker.

Modes
  size : required sample size per arm, duration, achieved power
  mde  : reverse-solve the minimum detectable effect for a given n per arm
  srm  : chi-square goodness-of-fit test on observed per-arm user counts

Usage
  python ab_sample_size.py --p1 0.10 --mde 10 --relative --alpha 0.05 \
      --power 0.8 --arms 2 --daily 100000 --traffic 0.5
  python ab_sample_size.py --p1 0.10 --mde 1
  python ab_sample_size.py --mode mde --p1 0.10 --n-per-arm 14730
  python ab_sample_size.py --mode srm --observed 4902,5011 --ratio 1
  python ab_sample_size.py --mode srm --observed 4902,5011,9904 --ratio 5,5,10
  python ab_sample_size.py --file plan.json
  python ab_sample_size.py --selftest

All output is written to a file (stdout is unreliable in some shells).
"""
import argparse
import json
import math
import os
import sys
from statistics import NormalDist

ND = NormalDist()
HERE = os.path.dirname(os.path.abspath(__file__))
RESULT = os.path.join(HERE, '_selftest_result.txt')

ALPHA_DEFAULT = 0.05
POWER_DEFAULT = 0.80
DEFAULT_MIN_DAYS = 7
SRM_REJECT_P = 0.001
SRM_WARN_P = 0.05
CHI2_TABLE = {
    1: (3.841, 6.635, 10.828),
    2: (5.991, 9.210, 13.816),
    3: (7.815, 11.345, 16.266),
    4: (9.488, 13.277, 18.467),
    5: (11.070, 15.086, 20.515),
    6: (12.592, 16.812, 22.458),
    7: (14.067, 18.475, 24.322),
    8: (15.507, 20.090, 26.124),
    9: (16.919, 21.666, 27.877),
    10: (18.307, 23.209, 29.588),
}


# ---------------------------------------------------------------- chi-square
def _gser(a, x):
    ap = a
    summ = 1.0 / a
    delta = summ
    for _ in range(1000):
        ap += 1.0
        delta *= x / ap
        summ += delta
        if abs(delta) < abs(summ) * 1e-15:
            break
    return summ * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gcf(a, x):
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def gammq(a, x):
    """Regularized upper incomplete gamma Q(a, x)."""
    if x <= 0.0:
        return 1.0
    if x < a + 1.0:
        return 1.0 - _gser(a, x)
    return _gcf(a, x)


def chi2_sf(x, df):
    """Upper tail probability of chi-square distribution."""
    if df < 1:
        return float('nan')
    if x <= 0.0:
        return 1.0
    return gammq(df / 2.0, x / 2.0)


def chi2_crit(df, p):
    """Upper critical value; only exact for the tabulated common df."""
    if df in CHI2_TABLE:
        tbl = CHI2_TABLE[df]
        return tbl[0] if p == 0.05 else (tbl[1] if p == 0.01 else tbl[2])
    lo, hi = 0.0, 1e6
    for _ in range(300):
        mid = (lo + hi) / 2.0
        if chi2_sf(mid, df) > p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


# ---------------------------------------------------------------- core math
def z_alpha(alpha, two_sided=True):
    if not two_sided:
        return ND.inv_cdf(1.0 - alpha)
    return ND.inv_cdf(1.0 - alpha / 2.0)


def z_beta(power):
    return ND.inv_cdf(power)


def sample_size(p1, p2, alpha=ALPHA_DEFAULT, power=POWER_DEFAULT,
                two_sided=True, sigma=None, delta=None):
    """Per-arm sample size. Proportion metric if sigma is None."""
    if sigma is None:
        v = p1 * (1.0 - p1) + p2 * (1.0 - p2)
        d = p2 - p1
    else:
        v = 2.0 * sigma * sigma
        d = delta
    if d == 0:
        raise ValueError('effect size is zero')
    za = z_alpha(alpha, two_sided)
    zb = z_beta(power)
    return (za + zb) ** 2 * v / (d * d)


def achieved_power(n_per_arm, p1, p2, alpha=ALPHA_DEFAULT, two_sided=True,
                   sigma=None, delta=None):
    """Approximate power of a two-sample test with n per arm."""
    if sigma is None:
        pbar = (p1 + p2) / 2.0
        se_null = math.sqrt(pbar * (1.0 - pbar) * 2.0 / n_per_arm)
        se_alt = math.sqrt(p1 * (1.0 - p1) / n_per_arm + p2 * (1.0 - p2) / n_per_arm)
        eff = p2 - p1
    else:
        se_null = math.sqrt(2.0 * sigma * sigma / n_per_arm)
        se_alt = se_null
        eff = delta
    za = z_alpha(alpha, two_sided)
    z_stat = eff / se_alt
    if two_sided:
        return ND.cdf(z_stat - za) + ND.cdf(-z_stat - za)
    return ND.cdf(z_stat - za)


def solve_mde(p1, n_per_arm, alpha=ALPHA_DEFAULT, power=POWER_DEFAULT,
              two_sided=True, cap=1.0):
    """Smallest absolute delta reaching target power at n_per_arm."""
    lo, hi = 1e-9, min(cap - p1, 0.999) if p1 < 1.0 else 1e-9
    if hi <= lo:
        raise ValueError('baseline rate out of range')
    for _ in range(200):
        mid = (lo + hi) / 2.0
        p2 = p1 + mid
        if p2 >= 1.0:
            hi = mid
            continue
        pw = achieved_power(n_per_arm, p1, p2, alpha, two_sided)
        if pw < power:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def plan_days(n_per_arm, arms, daily, traffic):
    if daily <= 0:
        return None
    per_day_total = daily * traffic
    if per_day_total <= 0:
        return None
    raw = n_per_arm * arms / per_day_total
    return max(1, int(math.ceil(raw)))


# ---------------------------------------------------------------- srm
def srm_test(observed, ratio):
    total = float(sum(observed))
    rsum = float(sum(ratio))
    stat = 0.0
    rows = []
    small = False
    for o, r in zip(observed, ratio):
        e = total * r / rsum
        rows.append({'observed': o, 'expected': round(e, 2), 'ratio': r})
        if e < 5:
            small = True
        stat += (o - e) ** 2 / e
    df = len(observed) - 1
    p = chi2_sf(stat, df)
    if p < SRM_REJECT_P:
        verdict = 'SRM'
    elif p < SRM_WARN_P:
        verdict = 'SUSPECT'
    else:
        verdict = 'PASS'
    return {'stat': stat, 'df': df, 'p': p, 'verdict': verdict,
            'rows': rows, 'small_expected': small}


# ---------------------------------------------------------------- report
def render_size(cfg, lines):
    p1 = cfg['p1']
    mde = cfg['mde']
    alpha = cfg['alpha']
    power = cfg['power']
    two = cfg['two_sided']
    arms = cfg['arms']
    if p1 < 0.0 or p1 >= 1.0:
        lines.append('[ERROR] baseline rate out of range: p1=%r' % p1)
        return
    if mde == 0.0:
        lines.append('[ERROR] mde must not be zero')
        return
    if cfg['relative']:
        p2 = p1 * (1.0 + mde / 100.0)
    else:
        p2 = p1 + mde / 100.0
    if p2 >= 1.0:
        lines.append('[ERROR] target rate >= 1: p1=%r p2=%r' % (p1, p2))
        return
    try:
        n = sample_size(p1, p2, alpha, power, two)
    except ValueError as exc:
        lines.append('[ERROR] %s' % exc)
        return
    n_ceil = int(math.ceil(n))
    pw = achieved_power(n_ceil, p1, p2, alpha, two)
    za = z_alpha(alpha, two)
    zb = z_beta(power)
    lines.append('== SAMPLE SIZE ==')
    lines.append('baseline p1            : %.4f' % p1)
    lines.append('target p2              : %.4f' % p2)
    lines.append('abs lift / rel lift    : %.4f pp / %.2f%%' % ((p2 - p1) * 100,
                                                             (p2 - p1) / p1 * 100))
    lines.append('alpha                  : %g (%s)' % (alpha,
                                                    'two-sided' if two else 'one-sided'))
    lines.append('power                  : %g' % power)
    lines.append('z terms                : z_a=%.4f z_b=%.4f coef=%.4f'
                 % (za, zb, (za + zb) ** 2))
    lines.append('required per arm       : %d' % n_ceil)
    lines.append('required total         : %d' % (n_ceil * arms))
    lines.append('achieved power @ n     : %.4f %s' % (
        pw, 'OK' if pw >= power - 1e-6 else 'BELOW TARGET'))
    lines.append('re-absolute mde @ n    : %.4f pp' % (solve_mde(p1, n_ceil, alpha,
                                                                 power, two) * 100))
    daily = cfg.get('daily')
    if daily:
        traffic = cfg.get('traffic')
        if traffic is None:
            traffic = 1.0
        days = plan_days(n_ceil, arms, daily, traffic)
        md = cfg.get('min_days', DEFAULT_MIN_DAYS)
        final = days
        if final < md:
            final = md
        final = int(math.ceil(final / md) * md)
        lines.append('')
        lines.append('== DURATION ==')
        lines.append('daily traffic          : %d' % daily)
        lines.append('experiment traffic     : %g' % traffic)
        lines.append('raw days needed       : %d' % days)
        lines.append('final days (>= %d, rounded to full weeks): %d' % (md, final))
        per_arm_day = daily * traffic / arms
        lines.append('per arm per day       : %.1f' % per_arm_day)
        if final > 60:
            lines.append('[WARN] over 60 days: usually infeasible, relax MDE or merge variants')
    else:
        lines.append('')
        lines.append('[INFO] pass --daily and --traffic to estimate duration')


def render_mde(cfg, lines):
    p1 = cfg['p1']
    n = cfg['n_per_arm']
    if n <= 0:
        lines.append('[ERROR] n-per-arm must be positive')
        return
    if p1 < 0.0 or p1 >= 1.0:
        lines.append('[ERROR] baseline rate out of range')
        return
    d = solve_mde(p1, n, cfg['alpha'], cfg['power'], cfg['two_sided'])
    p2 = p1 + d
    rel = d / p1 * 100 if p1 > 0 else float('nan')
    lines.append('== MINIMUM DETECTABLE EFFECT ==')
    lines.append('baseline p1            : %.4f' % p1)
    lines.append('n per arm              : %d' % n)
    lines.append('detectable p2          : %.6f' % p2)
    lines.append('absolute mde           : %.4f pp' % (d * 100))
    lines.append('relative mde           : %.3f%%' % rel)
    lines.append('[NOTE] effect below business MME means this run is inconclusive')


def render_srm(cfg, lines):
    obs = cfg.get('observed') or []
    ratio = cfg.get('ratio') or [1] * len(obs)
    if len(obs) < 2:
        lines.append('[ERROR] need at least two arms')
        return
    if len(ratio) != len(obs):
        lines.append('[ERROR] ratio length does not match observed length')
        return
    if any(v < 0 for v in obs):
        lines.append('[ERROR] observed counts must be non-negative')
        return
    res = srm_test(obs, ratio)
    lines.append('== SRM CHECK (chi-square goodness of fit) ==')
    for row in res['rows']:
        lines.append('  arm ratio %s : observed %d, expected %.2f'
                     % (row['ratio'], row['observed'], row['expected']))
    lines.append('chi-square             : %.4f' % res['stat'])
    lines.append('degrees of freedom     : %d' % res['df'])
    lines.append('p-value                : %.6g' % res['p'])
    lines.append('critical @ p=0.001     : %.3f' % chi2_crit(res['df'], 0.001))
    lines.append('verdict                : %s' % res['verdict'])
    if res['verdict'] == 'SRM':
        lines.append('[ACTION] split is broken: invalidate the test, check hash, '
                     'redirects, dedup and tracking loss. Do not read metrics.')
    elif res['verdict'] == 'SUSPECT':
        lines.append('[ACTION] pause conclusions and inspect split code')
    else:
        lines.append('[OK] sampling ratio is consistent')
    if res['small_expected']:
        lines.append('[WARN] some expected counts < 5: chi-square approximation invalid, '
                     'run longer or use an exact test')


# ---------------------------------------------------------------- config
def build_parser():
    p = argparse.ArgumentParser(
        description='A/B test sample size, MDE and SRM calculator')
    p.add_argument('--mode', choices=['size', 'mde', 'srm'], default='size')
    p.add_argument('--p1', type=float, default=None, help='baseline rate, e.g. 0.10')
    p.add_argument('--mde', type=float, default=None,
                   help='minimum detectable effect: absolute percentage points by '
                        'default, percent when --relative is set')
    p.add_argument('--relative', action='store_true',
                   help='treat --mde as a relative percent change')
    p.add_argument('--alpha', type=float, default=ALPHA_DEFAULT)
    p.add_argument('--power', type=float, default=POWER_DEFAULT)
    p.add_argument('--two-sided', dest='two_sided', action='store_true', default=True)
    p.add_argument('--one-sided', dest='two_sided', action='store_false')
    p.add_argument('--arms', type=int, default=2)
    p.add_argument('--daily', type=float, default=None, help='daily eligible traffic')
    p.add_argument('--traffic', type=float, default=None, help='experiment traffic share')
    p.add_argument('--min-days', dest='min_days', type=int, default=DEFAULT_MIN_DAYS)
    p.add_argument('--n-per-arm', dest='n_per_arm', type=int, default=None)
    p.add_argument('--observed', type=str, default=None,
                   help='comma separated actual user counts, e.g. 4902,5011')
    p.add_argument('--ratio', type=str, default=None,
                   help='comma separated expected split ratio, e.g. 5,5,10')
    p.add_argument('--file', type=str, default=None, help='JSON config file')
    p.add_argument('--out', type=str, default=None, help='output file path')
    p.add_argument('--selftest', action='store_true')
    return p


def config_from_args(args):
    cfg = {
        'mode': args.mode, 'p1': args.p1, 'mde': args.mde,
        'relative': args.relative, 'alpha': args.alpha, 'power': args.power,
        'two_sided': args.two_sided, 'arms': args.arms, 'daily': args.daily,
        'traffic': args.traffic, 'min_days': args.min_days,
        'n_per_arm': args.n_per_arm,
    }
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as fh:
            extra = json.load(fh)
        for k, v in extra.items():
            k = k.replace('-', '_')
            if k == 'observed' or k == 'ratio':
                if isinstance(v, str):
                    cfg[k] = [float(x) for x in v.split(',') if x.strip()]
                else:
                    cfg[k] = [float(x) for x in v]
            elif k == 'two_sided':
                cfg[k] = bool(v)
            else:
                cfg[k] = v
    if args.observed:
        cfg['observed'] = [float(x) for x in args.observed.split(',') if x.strip()]
    if args.ratio:
        cfg['ratio'] = [float(x) for x in args.ratio.split(',') if x.strip()]
    if cfg['mode'] == 'size':
        if cfg['p1'] is None or cfg['mde'] is None:
            raise ValueError('size mode needs --p1 and --mde (or --file)')
        if cfg['traffic'] is None and cfg['daily']:
            cfg['traffic'] = 1.0
    if cfg['mode'] == 'mde':
        if cfg['p1'] is None or cfg['n_per_arm'] is None:
            raise ValueError('mde mode needs --p1 and --n-per-arm (or --file)')
    if cfg['mode'] == 'srm':
        if not cfg.get('observed'):
            raise ValueError('srm mode needs --observed (or --file)')
    return cfg


def run(cfg):
    lines = []
    if cfg['mode'] == 'size':
        render_size(cfg, lines)
    elif cfg['mode'] == 'mde':
        render_mde(cfg, lines)
    else:
        render_srm(cfg, lines)
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------- selftest
def selftest():
    checks = []

    def ck(name, cond, info=''):
        checks.append((name, bool(cond), info))

    # 1 normal quantiles
    ck('z_alpha two-sided 0.05 = 1.96',
       abs(z_alpha(0.05, True) - 1.959964) < 1e-5, '%.6f' % z_alpha(0.05, True))
    ck('z_beta 0.8 = 0.8416', abs(z_beta(0.80) - 0.841621) < 1e-5,
       '%.6f' % z_beta(0.80))

    # 2 sample size: 50% -> 55%
    n50 = sample_size(0.50, 0.55)
    ck('p1=0.5 lift 10% -> per-arm ~1560', 1500 < n50 < 1650, '%.1f' % n50)

    # 3 sample size: 10% -> 11%
    n10 = sample_size(0.10, 0.11)
    ck('p1=0.1 lift 10% -> per-arm ~14730', 14000 < n10 < 15200, '%.1f' % n10)

    # 4 symmetry: same absolute lift, p and 1-p give identical variance
    n_low = sample_size(0.20, 0.22)
    n_high = sample_size(0.78, 0.80)
    ck('variance symmetry 20% vs 78% at +2pp', abs(n_low - n_high) < 1e-6,
       '%.4f vs %.4f' % (n_low, n_high))

    # 5 achieved power at the required n
    pwr = achieved_power(int(math.ceil(n10)), 0.10, 0.11)
    ck('achieved power >= 0.8', pwr >= 0.799, '%.5f' % pwr)

    # 6 reverse MDE round trip
    mde = solve_mde(0.10, int(math.ceil(n10)))
    back = sample_size(0.10, 0.10 + mde)
    ck('mde round trip within 2%',
       abs(back - int(math.ceil(n10))) / n10 < 0.02,
       'mde=%.6f back=%.1f' % (mde, back))

    # 7 chi-square upper tail
    ck('chi2_sf(10.828, df=1) ~= 0.001', abs(chi2_sf(10.828, 1) - 0.001) < 2e-4,
       '%.6f' % chi2_sf(10.828, 1))

    # 8 SRM pass
    good = srm_test([10000, 10000], [1, 1])
    ck('srm equal split passes', good['verdict'] == 'PASS',
       'p=%.4f' % good['p'])

    # 9 SRM detect
    bad = srm_test([9000, 10100], [1, 1])
    ck('srm 9000/10100 rejected', bad['verdict'] == 'SRM',
       'stat=%.2f p=%.3g' % (bad['stat'], bad['p']))

    # 10 three arms ratio
    tri = srm_test([5000, 5000, 10000], [5, 5, 10])
    ck('srm 5:5:10 exact ratio passes', tri['verdict'] == 'PASS',
       'p=%.4f' % tri['p'])

    # 11 duration rounding to full weeks
    d = plan_days(14730, 2, 100000, 0.5)
    ck('plan_days 14730@100k/50% = 1', d == 1, str(d))
    d2 = plan_days(14730, 2, 20000, 0.5)
    ck('plan_days 14730@20k/50% = 3', d2 == 3, str(d2))

    # 12 zero effect rejected
    try:
        sample_size(0.10, 0.10)
        ok = False
    except ValueError:
        ok = True
    ck('zero effect raises ValueError', ok)

    out = []
    failed = 0
    for name, ok, info in checks:
        if not ok:
            failed += 1
        out.append('%s  %-44s %s' % ('PASS' if ok else 'FAIL', name, info))
    out.append('total=%d failed=%d' % (len(checks), failed))
    out.append('SELFTEST OK' if failed == 0 else 'SELFTEST FAILED')
    text = '\n'.join(out) + '\n'
    with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    print(text)
    return 0 if failed == 0 else 1


def main():
    args = build_parser().parse_args()
    if args.selftest:
        return selftest()
    try:
        cfg = config_from_args(args)
    except Exception as exc:
        text = '[ERROR] %s\n' % exc
        with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(text)
        return 2
    text = run(cfg)
    path = args.out or RESULT
    try:
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
    except OSError:
        path = RESULT
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
    print(text)
    print('written: %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())