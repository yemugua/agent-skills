# -*- coding: utf-8 -*-
"""\u526f\u4e1a\u6295\u5165\u4ea7\u51fa\u6838\u7b97\uff1a\u6bcf\u5468\u53ef\u7528\u5c0f\u65f6 -> \u4ea7\u80fd -> \u5355\u4f4d\u65f6\u95f4\u6536\u76ca -> \u56de\u672c\u5468\u671f -> \u8bd5\u9519\u4e0a\u9650\u4e0e\u6b62\u635f\u7ebf\u3002

\u7528\u6cd5:
  python side_hustle_calc.py --file hustle.json [--out \u526f\u4e1a\u6295\u5165\u4ea7\u51fa\u6838\u7b97.md] [--format json]
  python side_hustle_calc.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

WEEKS_PER_MONTH = 4.33      # \u6bcf\u6708\u5468\u6570\uff0c\u7528\u4e8e\u6708\u56fa\u5b9a\u6210\u672c\u6298\u7b97\u4e0e\u6708\u51c0\u6536\u5165
CONSERVATIVE = 0.70         # \u4fdd\u5b88\u7cfb\u6570\uff1a\u6263\u6389\u52a0\u73ed\u3001\u5e94\u916c\u3001\u5bb6\u5ead\u7a81\u53d1
RISK_COEF = 0.30            # \u8bd5\u9519\u8d44\u91d1\u98ce\u9669\u7cfb\u6570
H_MIN = 5.0                 # \u6bcf\u5468\u53ef\u7528\u5c0f\u65f6\u4e0b\u9650
H_MAX = 20.0                # \u6bcf\u5468\u53ef\u7528\u5c0f\u65f6\u4e0a\u9650
RATIO_GO = 1.5              # \u53ef\u542f\u52a8\u9608\u503c\uff08\u76f8\u5bf9\u672c\u804c\u65f6\u85aa\uff09
RATIO_CARE = 1.0            # \u8c28\u614e\u542f\u52a8\u9608\u503c
RATIO_BAD = 0.6             # \u4e0d\u5212\u7b97\u9608\u503c
STOPCARE = 0.30             # \u6536\u5165\u6b62\u635f\uff1a\u4f4e\u4e8e\u76ee\u6807 30%


def money(x):
    return round(float(x) + 1e-9, 2)


def as_float(v, default=0.0):
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def calc(data):
    name = data.get('name', '\u672a\u547d\u540d\u526f\u4e1a')
    weekday_hours = as_float(data.get('weekday_hours'))
    workdays = as_float(data.get('workdays', 5))
    weekend_hours = as_float(data.get('weekend_hours'))
    ops_hours = as_float(data.get('ops_hours_per_week'))
    price = as_float(data.get('price'))
    unit_cost = as_float(data.get('unit_cost'))
    delivery_hours = as_float(data.get('delivery_hours'))
    monthly_fixed = as_float(data.get('monthly_fixed_cost'))
    startup = as_float(data.get('startup_cost'))
    surplus = as_float(data.get('monthly_surplus'))
    trial_months = as_float(data.get('trial_months', 3))
    job_hourly = data.get('day_job_hourly')
    job_hourly = None if job_hourly is None else as_float(job_hourly, 0.0)
    target = data.get('target_monthly_income')
    target = None if target is None else as_float(target, 0.0)
    conservative = as_float(data.get('conservative'), CONSERVATIVE)

    if weekday_hours < 0 or weekend_hours < 0 or workdays < 0:
        raise ValueError('\u65f6\u95f4\u53c2\u6570\u4e0d\u80fd\u4e3a\u8d1f\u6570')
    if price <= 0:
        raise ValueError('\u5355\u4ef7\u5fc5\u987b\u4e3a\u6b63\u6570')
    if delivery_hours <= 0:
        raise ValueError('\u5355\u5747\u4ea4\u4ed8\u8017\u65f6\u5fc5\u987b\u4e3a\u6b63\u6570')
    if conservative <= 0 or conservative > 1:
        raise ValueError('\u4fdd\u5b88\u7cfb\u6570\u5e94\u5728 0 \u5230 1 \u4e4b\u95f4')
    if trial_months <= 0:
        raise ValueError('\u8bd5\u9519\u6708\u6570\u5fc5\u987b\u4e3a\u6b63\u6570')

    raw_hours = weekday_hours * workdays + weekend_hours * 2
    usable_hours = raw_hours * conservative
    deliver_hours = usable_hours - ops_hours
    cap_raw = (deliver_hours / delivery_hours) if deliver_hours > 0 else 0.0
    capacity = cap_raw

    weekly_gross = cap_raw * price
    weekly_var = cap_raw * unit_cost
    weekly_fixed = monthly_fixed / WEEKS_PER_MONTH
    weekly_net = weekly_gross - weekly_var - weekly_fixed
    monthly_net = weekly_net * WEEKS_PER_MONTH
    hourly_yield = (weekly_net / usable_hours) if usable_hours > 0 else 0.0

    ratio = None
    if job_hourly and job_hourly > 0:
        ratio = hourly_yield / job_hourly

    breakeven = None
    if monthly_net > 0:
        breakeven = startup / monthly_net

    trial_cap = surplus * trial_months * RISK_COEF
    invest_ratio = (startup / trial_cap) if trial_cap > 0 else None

    if monthly_net <= 0:
        verdict = '\u4e0d\u542f\u52a8'
        verdict_text = '\u6a21\u578b\u672c\u8eab\u4e0d\u6210\u7acb\uff1a\u6708\u51c0\u6536\u5165\u4e3a\u96f6\u6216\u4e3a\u8d1f\uff0c\u5148\u8c03\u5355\u4ef7\u3001\u964d\u4ea4\u4ed8\u8017\u65f6\u6216\u6362\u8d5b\u9053'
    elif ratio is None:
        verdict = '\u5f85\u5bf9\u6bd4'
        verdict_text = '\u672a\u586b\u672c\u804c\u65f6\u85aa\uff0c\u65e0\u6cd5\u5224\u65ad\u662f\u5426\u5212\u7b97\uff0c\u8bf7\u8865\u4e0a day_job_hourly \u518d\u5224'
    elif ratio >= RATIO_GO:
        verdict = '\u53ef\u542f\u52a8'
        verdict_text = '\u5355\u4f4d\u65f6\u95f4\u6536\u76ca\u8fbe\u5230\u672c\u804c\u65f6\u85aa\u7684 %.2f \u500d\uff0c\u503c\u5f97\u6295\u5165\uff0c\u5148\u505a\u4e09\u5355\u9a8c\u8bc1' % ratio
    elif ratio >= RATIO_CARE:
        verdict = '\u8c28\u614e\u542f\u52a8'
        verdict_text = '\u7565\u9ad8\u4e8e\u672c\u804c\u65f6\u85aa\uff08%.2f \u500d\uff09\uff0c\u5148\u5c0f\u6b65\u8bd5\u5e76\u63a7\u5236\u6295\u5165' % ratio
    elif ratio >= RATIO_BAD:
        verdict = '\u4e0d\u5212\u7b97'
        verdict_text = '\u4ec5\u4e3a\u672c\u804c\u65f6\u85aa\u7684 %.2f \u500d\uff0c\u9664\u975e\u6709\u6280\u80fd\u6c89\u6dc0\u6216\u8f6c\u884c\u4ef7\u503c\uff0c\u5426\u5219\u4e0d\u5efa\u8bae' % ratio
    else:
        verdict = '\u4e0d\u542f\u52a8'
        verdict_text = '\u5355\u4f4d\u65f6\u95f4\u6536\u76ca\u4ec5\u4e3a\u672c\u804c\u65f6\u85aa\u7684 %.2f \u500d\uff0c\u5c5e\u4e8e\u8d31\u5356\u65f6\u95f4' % ratio

    stops = []
    warns = []

    if invest_ratio is not None and invest_ratio > 1.0:
        stops.append('\u6295\u5165\u6b62\u635f\uff1a\u5df2\u6295 %.0f%% \u8bd5\u9519\u4e0a\u9650\uff0c\u7acb\u5373\u505c\u624b\u5e76\u590d\u76d8\uff0c\u4e0d\u518d\u8ffd\u52a0'
                     % (invest_ratio * 100))
    elif invest_ratio is not None and invest_ratio > 0.5:
        warns.append('\u5df2\u6295\u8fbe\u5230\u8bd5\u9519\u4e0a\u9650\u7684 %.0f%%\uff0c\u6682\u505c\u65b0\u589e\u6295\u5165\uff0c\u53ea\u770b\u6570\u636e' % (invest_ratio * 100))

    if breakeven is None:
        if monthly_net <= 0:
            stops.append('\u56de\u672c\u6b62\u635f\uff1a\u6708\u51c0\u6536\u5165\u4e3a\u96f6\u6216\u4e3a\u8d1f\uff0c\u65e0\u6cd5\u56de\u672c')
    elif breakeven > trial_months * 1.5:
        stops.append('\u56de\u672c\u6b62\u635f\uff1a\u56de\u672c %.1f \u4e2a\u6708\uff0c\u8d85\u8fc7\u8bd5\u9519\u7a97\u53e3 %.1f \u4e2a\u6708\u7684 1.5 \u500d\uff0c\u505c\u6295'
                     % (breakeven, trial_months))
    elif breakeven > trial_months:
        warns.append('\u56de\u672c %.1f \u4e2a\u6708\uff0c\u8d85\u51fa\u8bd5\u9519\u7a97\u53e3 %.1f \u4e2a\u6708\uff0c\u9700\u91cd\u4f30' % (breakeven, trial_months))

    if target is not None and target > 0 and monthly_net < target * STOPCARE:
        stops.append('\u6536\u5165\u6b62\u635f\uff1a\u6708\u51c0\u6536\u5165 %.0f \u5143\u4f4e\u4e8e\u76ee\u6807 %.0f \u5143\u7684 %d%%\uff0c\u8fde\u7eed\u4e09\u4e2a\u6708\u5982\u6b64\u5373\u505c\u6295'
                     % (monthly_net, target, round(STOPCARE * 100)))

    if usable_hours < H_MIN:
        warns.append('\u6bcf\u5468\u53ef\u7528\u5c0f\u65f6 %.1f \u4f4e\u4e8e %.0f \u5c0f\u65f6\uff0c\u4ea7\u80fd\u592a\u4f4e\uff0c\u8fde\u83b7\u5ba2\u90fd\u8dd1\u4e0d\u901a'
                     % (usable_hours, H_MIN))
    if usable_hours > H_MAX:
        warns.append('\u6bcf\u5468\u53ef\u7528\u5c0f\u65f6 %.1f \u8d85\u8fc7 %.0f \u5c0f\u65f6\uff0c\u4e3b\u4e1a\u4e0e\u5065\u5eb7\u5927\u6982\u7387\u5148\u51fa\u95ee\u9898'
                     % (usable_hours, H_MAX))
    if ops_hours <= 0:
        warns.append('\u6bcf\u5468\u8fd0\u8425\u5c0f\u65f6\u4e3a 0\uff0c\u83b7\u5ba2\u4e0e\u552e\u540e\u65f6\u95f4\u672a\u8ba1\u5165\uff0c\u4ea7\u80fd\u4f1a\u88ab\u9ad8\u4f30')
    if deliver_hours <= 0:
        warnings_msg = '\u8fd0\u8425\u65f6\u95f4\u541e\u566c\u4e86\u5168\u90e8\u53ef\u7528\u65f6\u95f4\uff0c\u6bcf\u5468\u4ea4\u4ed8\u5c0f\u65f6\u4e3a %.1f\uff0c\u65e0\u6cd5\u4ea7\u51fa' % deliver_hours
        warns.append(warnings_msg)
        stops.append('\u65f6\u95f4\u6b62\u635f\uff1a\u65e0\u53ef\u7528\u4ea4\u4ed8\u65f6\u95f4\uff0c\u8bf4\u660e\u8fd9\u4e2a\u9879\u76ee\u6392\u4e0d\u8fdb\u53bb')
    if trial_cap <= 0:
        warns.append('\u6708\u53ef\u652f\u914d\u7ed3\u4f59\u4e3a 0 \u6216\u8d1f\u6570\uff0c\u4e0d\u5177\u5907\u8bd5\u9519\u6761\u4ef6\uff1a\u5148\u5907 3-6 \u4e2a\u6708\u751f\u6d3b\u8d39')

    return {
        'name': name,
        'raw_hours': round(raw_hours, 2),
        'conservative': conservative,
        'usable_hours': round(usable_hours, 2),
        'ops_hours': ops_hours,
        'deliver_hours': round(deliver_hours, 2),
        'capacity': round(capacity, 4),
        'price': money(price),
        'unit_cost': money(unit_cost),
        'delivery_hours': delivery_hours,
        'weekly_gross': money(weekly_gross),
        'weekly_var': money(weekly_var),
        'weekly_fixed': money(weekly_fixed),
        'weekly_net': money(weekly_net),
        'monthly_net': money(monthly_net),
        'hourly_yield': money(hourly_yield),
        'job_hourly': None if job_hourly is None else money(job_hourly),
        'ratio': None if ratio is None else round(ratio, 3),
        'startup_cost': money(startup),
        'monthly_surplus': money(surplus),
        'trial_months': trial_months,
        'trial_cap': money(trial_cap),
        'invest_ratio': None if invest_ratio is None else round(invest_ratio, 3),
        'breakeven_months': None if breakeven is None else round(breakeven, 2),
        'target_monthly_income': None if target is None else money(target),
        'verdict': verdict,
        'verdict_text': verdict_text,
        'stops': stops,
        'warns': warns,
    }


def render_md(r):
    L = []
    L.append('# \u526f\u4e1a\u6295\u5165\u4ea7\u51fa\u6838\u7b97\uff1a%s' % r['name'])
    L.append('')
    L.append('## \u4e00\u3001\u65f6\u95f4\u9884\u7b97')
    L.append('')
    L.append('| \u9879 | \u503c |')
    L.append('|---|---|')
    L.append('| \u6bcf\u5468\u540d\u4e49\u53ef\u7528\u5c0f\u65f6 | %.2f \u5c0f\u65f6 |' % r['raw_hours'])
    L.append('| \u4fdd\u5b88\u7cfb\u6570 | %.2f |' % r['conservative'])
    L.append('| \u6bcf\u5468\u53ef\u7528\u5c0f\u65f6 | **%.2f \u5c0f\u65f6** |' % r['usable_hours'])
    L.append('| \u6bcf\u5468\u8fd0\u8425\u5c0f\u65f6\uff08\u83b7\u5ba2/\u5185\u5bb9/\u552e\u540e\uff09 | %.2f \u5c0f\u65f6 |' % r['ops_hours'])
    L.append('| \u6bcf\u5468\u4ea4\u4ed8\u5c0f\u65f6 | **%.2f \u5c0f\u65f6** |' % r['deliver_hours'])
    L.append('| \u6bcf\u5468\u4ea7\u80fd | **%.2f \u5355** |' % r['capacity'])
    L.append('')
    L.append('## \u4e8c\u3001\u5355\u4f4d\u7ecf\u6d4e\u4e0e\u6536\u76ca')
    L.append('')
    L.append('| \u9879 | \u503c | \u53e3\u5f84 |')
    L.append('|---|---|---|')
    L.append('| \u5355\u4ef7 / \u5355\u5747\u6210\u672c | %.2f / %.2f \u5143 | |' % (r['price'], r['unit_cost']))
    L.append('| \u6bcf\u5468\u6bdb\u6536\u5165 | %.2f \u5143 | \u4ea7\u80fd \u00d7 \u5355\u4ef7 |' % r['weekly_gross'])
    L.append('| \u6bcf\u5468\u53d8\u52a8\u6210\u672c | %.2f \u5143 | \u4ea7\u80fd \u00d7 \u5355\u5747\u6210\u672c |' % r['weekly_var'])
    L.append('| \u6bcf\u5468\u56fa\u5b9a\u6210\u672c\u644a\u9500 | %.2f \u5143 | \u6708\u56fa\u5b9a \u00f7 4.33 |' % r['weekly_fixed'])
    L.append('| \u6bcf\u5468\u51c0\u6536\u5165 | **%.2f \u5143** | |' % r['weekly_net'])
    L.append('| \u6708\u51c0\u6536\u5165 | **%.2f \u5143** | \u5468\u51c0 \u00d7 4.33 |' % r['monthly_net'])
    L.append('| \u5355\u4f4d\u65f6\u95f4\u6536\u76ca | **%.2f \u5143/\u5c0f\u65f6** | \u5468\u51c0 \u00f7 \u6bcf\u5468\u53ef\u7528\u5c0f\u65f6 |' % r['hourly_yield'])
    L.append('| \u672c\u804c\u65f6\u85aa | %s \u5143/\u5c0f\u65f6 | \u5bf9\u6bd4\u57fa\u51c6 |' % ('\u672a\u586b' if r['job_hourly'] is None else '%.2f' % r['job_hourly']))
    L.append('| \u6bd4\u503c | **%s** | \u5355\u4f4d\u65f6\u95f4\u6536\u76ca \u00f7 \u672c\u804c\u65f6\u85aa |'
             % ('\u4e0d\u9002\u7528' if r['ratio'] is None else '%.2f \u500d' % r['ratio']))
    L.append('')
    L.append('## \u4e09\u3001\u6295\u5165\u4e0e\u56de\u672c')
    L.append('')
    L.append('| \u9879 | \u503c | \u53e3\u5f84 |')
    L.append('|---|---|---|')
    L.append('| \u7d2f\u8ba1\u5df2\u6295\u6210\u672c | %.2f \u5143 | |' % r['startup_cost'])
    L.append('| \u6708\u53ef\u652f\u914d\u7ed3\u4f59 | %.2f \u5143 | |' % r['monthly_surplus'])
    L.append('| \u8bd5\u9519\u6708\u6570 | %.1f \u6708 | |' % r['trial_months'])
    L.append('| \u8bd5\u9519\u6210\u672c\u4e0a\u9650 | **%.2f \u5143** | \u7ed3\u4f59 \u00d7 \u6708\u6570 \u00d7 0.3 |' % r['trial_cap'])
    L.append('| \u6295\u5165\u5360\u6bd4 | **%s** | \u5df2\u6295 \u00f7 \u4e0a\u9650 |'
             % ('\u4e0d\u9002\u7528' if r['invest_ratio'] is None else '%.1f%%' % (r['invest_ratio'] * 100)))
    L.append('| \u56de\u672c\u5468\u671f | **%s** | \u5df2\u6295 \u00f7 \u6708\u51c0\u6536\u5165 |'
             % ('\u65e0\u6cd5\u56de\u672c' if r['breakeven_months'] is None else '%.2f \u4e2a\u6708' % r['breakeven_months']))
    L.append('')
    L.append('## \u56db\u3001\u5224\u5b9a')
    L.append('')
    L.append('- \u7ed3\u8bba\uff1a**%s** \u2014\u2014 %s' % (r['verdict'], r['verdict_text']))
    L.append('- \u6863\u4f4d\u53e3\u5f84\uff1a\u22651.5 \u500d\u53ef\u542f\u52a8\uff1b1.0-1.5 \u500d\u8c28\u614e\u542f\u52a8\uff1b0.6-1.0 \u500d\u4e0d\u5212\u7b97\uff1b<0.6 \u500d\u4e0d\u542f\u52a8\uff1b\u6708\u51c0\u6536\u5165 \u2264 0 \u4e0d\u542f\u52a8')
    L.append('')
    L.append('## \u4e94\u3001\u6b62\u635f\u68c0\u67e5')
    L.append('')
    if r['stops']:
        for s in r['stops']:
            L.append('- **\u89e6\u53d1**\uff1a%s' % s)
    else:
        L.append('- \u5f53\u524d\u53c2\u6570\u4e0b\u672a\u89e6\u53d1\u6b62\u635f\u7ebf')
    L.append('')
    L.append('## \u516d\u3001\u63d0\u9192')
    L.append('')
    if r['warns']:
        for w in r['warns']:
            L.append('- %s' % w)
    else:
        L.append('- \u5f53\u524d\u53c2\u6570\u4e0b\u672a\u89e6\u53d1\u63d0\u9192')
    L.append('')
    L.append('## \u4e03\u3001\u4eba\u5de5\u786e\u8ba4\uff08\u811a\u672c\u4e0d\u4ee3\u66ff\uff09')
    L.append('')
    L.append('- [ ] \u7ade\u4e1a\u9650\u5236\u4e0e\u8d44\u8d28\u8981\u6c42\u5df2\u786e\u8ba4')
    L.append('- [ ] \u4e0d\u4f7f\u7528\u516c\u53f8\u8bbe\u5907\u3001\u5de5\u4f5c\u65f6\u95f4\u3001\u5ba2\u6237\u540d\u5355')
    L.append('- [ ] \u8bd5\u9519\u8d44\u91d1\u4e0d\u6765\u81ea\u5e94\u6025\u91d1\u3001\u501f\u6b3e\u6216\u4fe1\u7528\u5361')
    L.append('- [ ] \u4e94\u6761\u6b62\u635f\u7ebf\u5df2\u5199\u6210\u6570\u5b57\uff08\u65f6\u95f4/\u6536\u5165/\u56de\u672c/\u4e3b\u4e1a/\u5065\u5eb7\uff09')
    L.append('- [ ] \u5df2\u505a\u4e09\u5355\u6700\u5c0f\u9a8c\u8bc1\uff0c\u5b9e\u9645\u8017\u65f6\u901a\u5e38\u6bd4\u9884\u4f30\u9ad8 30%-50%')
    return '\n'.join(L)


def render_json(r):
    return json.dumps(r, ensure_ascii=False, indent=2)


def selftest():
    errs = []
    checks = 0

    def ck(cond, msg):
        nonlocal checks
        checks += 1
        if not cond:
            errs.append(msg)

    base = {'name': '\u5468\u672b\u7ea6\u62cd', 'weekday_hours': 1.5, 'workdays': 5, 'weekend_hours': 4,
            'ops_hours_per_week': 3, 'price': 300, 'unit_cost': 40, 'delivery_hours': 3,
            'monthly_fixed_cost': 200, 'startup_cost': 1500, 'monthly_surplus': 3000,
            'trial_months': 3, 'day_job_hourly': 80, 'target_monthly_income': 2000}

    # 1 \u65f6\u95f4\u9884\u7b97
    r1 = calc(base)
    ck(abs(r1['raw_hours'] - 15.5) < 1e-6, '\u7528\u4f8b1 \u540d\u4e49\u53ef\u7528\u5e94\u4e3a 15.50\uff0c\u5b9e\u4e3a %s' % r1['raw_hours'])
    ck(abs(r1['usable_hours'] - 10.85) < 1e-6, '\u7528\u4f8b1 \u53ef\u7528\u5c0f\u65f6\u5e94\u4e3a 10.85\uff0c\u5b9e\u4e3a %s' % r1['usable_hours'])
    ck(abs(r1['deliver_hours'] - 7.85) < 1e-6, '\u7528\u4f8b1 \u4ea4\u4ed8\u5c0f\u65f6\u5e94\u4e3a 7.85\uff0c\u5b9e\u4e3a %s' % r1['deliver_hours'])

    # 2 \u4ea7\u80fd\u4e0e\u5468\u51c0\u6536\u5165
    cap = 7.85 / 3.0
    ck(abs(r1['capacity'] - cap) < 1e-3, '\u7528\u4f8b2 \u4ea7\u80fd\u5e94\u7ea6 %.4f\uff0c\u5b9e\u4e3a %s' % (cap, r1['capacity']))
    wn = cap * 260.0 - 200.0 / 4.33
    ck(abs(r1['weekly_net'] - wn) < 0.02, '\u7528\u4f8b2 \u5468\u51c0\u6536\u5165\u5e94\u7ea6 %.2f\uff0c\u5b9e\u4e3a %s' % (wn, r1['weekly_net']))
    ck(abs(r1['monthly_net'] - wn * 4.33) < 0.02, '\u7528\u4f8b2 \u6708\u51c0\u6536\u5165\u5e94\u7ea6 %.2f\uff0c\u5b9e\u4e3a %s'
       % (wn * 4.33, r1['monthly_net']))

    # 3 \u5355\u4f4d\u65f6\u95f4\u6536\u76ca\u4e0e\u6bd4\u503c
    hy = wn / 10.85
    ck(abs(r1['hourly_yield'] - hy) < 0.02, '\u7528\u4f8b3 \u5355\u4f4d\u65f6\u95f4\u6536\u76ca\u5e94\u7ea6 %.2f\uff0c\u5b9e\u4e3a %s' % (hy, r1['hourly_yield']))
    ck(abs(r1['ratio'] - hy / 80.0) < 1e-3, '\u7528\u4f8b3 \u6bd4\u503c\u5e94\u7ea6 %.3f\uff0c\u5b9e\u4e3a %s' % (hy / 80.0, r1['ratio']))
    ck(r1['verdict'] in ('\u4e0d\u5212\u7b97', '\u8c28\u614e\u542f\u52a8'), '\u7528\u4f8b3 0.73 \u500d\u5e94\u5224\u4e3a\u4e0d\u5212\u7b97\uff0c\u5b9e\u4e3a %s' % r1['verdict'])

    # 4 \u8bd5\u9519\u4e0a\u9650\u4e0e\u6295\u5165\u5360\u6bd4
    ck(abs(r1['trial_cap'] - 2700.0) < 1e-6, '\u7528\u4f8b4 \u8bd5\u9519\u4e0a\u9650\u5e94\u4e3a 2700.00\uff0c\u5b9e\u4e3a %s' % r1['trial_cap'])
    ck(abs(r1['invest_ratio'] - 1500.0 / 2700.0) < 1e-3,
       '\u7528\u4f8b4 \u6295\u5165\u5360\u6bd4\u5e94\u7ea6 0.556\uff0c\u5b9e\u4e3a %s' % r1['invest_ratio'])
    ck(any('\u8bd5\u9519\u4e0a\u9650' in w for w in r1['warns']), '\u7528\u4f8b4 \u6295\u5165\u8d85 50%% \u5e94\u63d0\u9192\uff0c\u5b9e\u4e3a %s' % r1['warns'])

    # 5 \u56de\u672c\u5468\u671f
    ck(abs(r1['breakeven_months'] - 1500.0 / (wn * 4.33)) < 0.01,
       '\u7528\u4f8b5 \u56de\u672c\u5468\u671f\u5e94\u7ea6 %.2f \u4e2a\u6708\uff0c\u5b9e\u4e3a %s' % (1500.0 / (wn * 4.33), r1['breakeven_months']))

    # 6 \u5224\u5b9a\u6863\u4f4d\u56db\u6863
    r6a = calc(dict(base, price=900, day_job_hourly=80))
    ck(r6a['verdict'] == '\u53ef\u542f\u52a8', '\u7528\u4f8b6 \u9ad8\u4ef7\u5e94\u5224\u4e3a\u53ef\u542f\u52a8\uff0c\u5b9e\u4e3a %s' % r6a['verdict'])
    r6b = calc(dict(base, price=120, day_job_hourly=80))
    ck(r6b['verdict'] in ('\u4e0d\u5212\u7b97', '\u4e0d\u542f\u52a8'), '\u7528\u4f8b6 \u4f4e\u4ef7\u4e0d\u5e94\u5224\u4e3a\u53ef\u542f\u52a8\uff0c\u5b9e\u4e3a %s' % r6b['verdict'])
    r6c = calc(dict(base, price=300, unit_cost=900))
    ck(r6c['verdict'] == '\u4e0d\u542f\u52a8' and r6c['monthly_net'] <= 0,
       '\u7528\u4f8b6 \u6708\u51c0\u4e3a\u8d1f\u5e94\u5224\u4e3a\u4e0d\u542f\u52a8\uff0c\u5b9e\u4e3a %s / %s' % (r6c['verdict'], r6c['monthly_net']))
    ck(any('\u65e0\u6cd5\u56de\u672c' in s for s in r6c['stops']), '\u7528\u4f8b6 \u6708\u51c0\u4e3a\u8d1f\u5e94\u89e6\u53d1\u56de\u672c\u6b62\u635f\uff0c\u5b9e\u4e3a %s' % r6c['stops'])

    # 7 \u6295\u5165\u8d85\u4e0a\u9650\u89e6\u53d1\u6b62\u635f
    r7 = calc(dict(base, startup_cost=5000))
    ck(any('\u6295\u5165\u6b62\u635f' in s for s in r7['stops']), '\u7528\u4f8b7 \u8d85\u4e0a\u9650\u5e94\u89e6\u53d1\u6295\u5165\u6b62\u635f\uff0c\u5b9e\u4e3a %s' % r7['stops'])

    # 8 \u6536\u5165\u6b62\u635f
    r8 = calc(dict(base, price=200, target_monthly_income=20000))
    ck(any('\u6536\u5165\u6b62\u635f' in s for s in r8['stops']), '\u7528\u4f8b8 \u8fdc\u4f4e\u4e8e\u76ee\u6807\u5e94\u89e6\u53d1\u6536\u5165\u6b62\u635f\uff0c\u5b9e\u4e3a %s' % r8['stops'])

    # 9 \u65f6\u95f4\u8fc7\u8f7d\u4e0e\u4e0d\u8db3
    r9a = calc(dict(base, weekday_hours=4, weekend_hours=10))
    ck(any('\u8d85\u8fc7' in w for w in r9a['warns']), '\u7528\u4f8b9 \u65f6\u95f4\u8fc7\u8f7d\u5e94\u63d0\u9192\uff0c\u5b9e\u4e3a %s' % r9a['warns'])
    r9b = calc(dict(base, weekday_hours=0.2, weekend_hours=0.5))
    ck(any('\u4f4e\u4e8e' in w for w in r9b['warns']), '\u7528\u4f8b9 \u65f6\u95f4\u4e0d\u8db3\u5e94\u63d0\u9192\uff0c\u5b9e\u4e3a %s' % r9b['warns'])

    # 10 \u8fd0\u8425\u65f6\u95f4\u541e\u566c\u5168\u90e8\u53ef\u7528\u65f6\u95f4
    r10 = calc(dict(base, ops_hours_per_week=20))
    ck(any('\u65e0\u53ef\u7528\u4ea4\u4ed8\u65f6\u95f4' in s for s in r10['stops']), '\u7528\u4f8b10 \u5e94\u89e6\u53d1\u65f6\u95f4\u6b62\u635f\uff0c\u5b9e\u4e3a %s' % r10['stops'])
    ck(r10['capacity'] == 0.0, '\u7528\u4f8b10 \u4ea7\u80fd\u5e94\u4e3a 0\uff0c\u5b9e\u4e3a %s' % r10['capacity'])

    # 11 \u672a\u8ba1\u83b7\u5ba2\u65f6\u95f4
    r11 = calc(dict(base, ops_hours_per_week=0))
    ck(any('\u83b7\u5ba2' in w for w in r11['warns']), '\u7528\u4f8b11 \u8fd0\u8425\u5c0f\u65f6\u4e3a 0 \u5e94\u63d0\u9192\uff0c\u5b9e\u4e3a %s' % r11['warns'])

    # 12 \u65e0\u7ed3\u4f59\u4e0d\u5177\u5907\u8bd5\u9519\u6761\u4ef6
    r12 = calc(dict(base, monthly_surplus=0))
    ck(any('\u8bd5\u9519\u6761\u4ef6' in w for w in r12['warns']), '\u7528\u4f8b12 \u65e0\u7ed3\u4f59\u5e94\u63d0\u9192\uff0c\u5b9e\u4e3a %s' % r12['warns'])

    # 13 \u672a\u586b\u672c\u804c\u65f6\u85aa
    r13 = calc(dict(base, day_job_hourly=None))
    ck(r13['verdict'] == '\u5f85\u5bf9\u6bd4', '\u7528\u4f8b13 \u672a\u586b\u672c\u804c\u65f6\u85aa\u5e94\u4e3a\u5f85\u5bf9\u6bd4\uff0c\u5b9e\u4e3a %s' % r13['verdict'])

    # 14 \u975e\u6cd5\u53c2\u6570\u5e94\u62a5\u9519
    for bad in ({'price': 0}, {'delivery_hours': 0}, {'trial_months': 0}, {'conservative': 1.5},
                {'weekday_hours': -1}):
        d = dict(base)
        d.update(bad)
        try:
            calc(d)
            ck(False, '\u7528\u4f8b14 \u975e\u6cd5\u53c2\u6570 %s \u5e94\u629b\u9519' % bad)
        except ValueError:
            ck(True, '\u7528\u4f8b14 \u975e\u6cd5\u53c2\u6570 %s \u5e94\u629b\u9519' % bad)

    # 15 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r1)
    for kw in ('\u8bd5\u9519\u6210\u672c\u4e0a\u9650', '\u5355\u4f4d\u65f6\u95f4\u6536\u76ca', '\u6b62\u635f\u68c0\u67e5', '\u4eba\u5de5\u786e\u8ba4'):
        ck(kw in md, '\u7528\u4f8b15 Markdown \u5e94\u5305\u542b %s' % kw)
    j = json.loads(render_json(r1))
    ck(j['verdict'] == r1['verdict'], '\u7528\u4f8b15 JSON \u5224\u5b9a\u5e94\u4e0e\u8ba1\u7b97\u7ed3\u679c\u4e00\u81f4')

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u65f6\u95f4\u9884\u7b97/\u4ea7\u80fd/\u5468\u51c0/\u6708\u51c0/\u5355\u4f4d\u65f6\u95f4\u6536\u76ca/\u6bd4\u503c/\u8bd5\u9519\u4e0a\u9650/'
               '\u6295\u5165\u5360\u6bd4/\u56de\u672c\u5468\u671f/\u5224\u5b9a\u6863\u4f4d/\u6295\u5165\u6b62\u635f/\u6536\u5165\u6b62\u635f/\u65f6\u95f4\u8fc7\u8f7d/\u8fd0\u8425\u541e\u566c/\u65e0\u7ed3\u4f59/\u975e\u6cd5\u53c2\u6570/\u8f93\u51fa\u7ed3\u6784'
               % checks)
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u526f\u4e1a\u6295\u5165\u4ea7\u51fa\u6838\u7b97')
    ap.add_argument('--file', help='\u8f93\u5165 JSON \u6587\u4ef6')
    ap.add_argument('--text', help='\u8f93\u5165 JSON \u5b57\u7b26\u4e32')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'])
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    raw = a.text or ''
    if a.file:
        if not os.path.exists(a.file):
            print('ERROR --file \u4e0d\u5b58\u5728')
            return 2
        raw = open(a.file, 'r', encoding='utf-8', errors='replace').read()
    if not raw.strip():
        print('ERROR \u9700\u8981 --file \u6216 --text')
        return 2
    try:
        data = json.loads(raw)
    except ValueError:
        print('ERROR JSON \u89e3\u6790\u5931\u8d25')
        return 2
    try:
        r = calc(data)
    except ValueError as e:
        print('ERROR %s' % e)
        return 2

    out = render_md(r) if a.format == 'md' else render_json(r)
    out_dir = os.path.dirname(os.path.abspath(__file__))
    target = a.out or os.path.join(out_dir, '_last_result.txt')
    with open(target, 'w', encoding='utf-8') as f:
        f.write(out + '\n')
    print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % target)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
