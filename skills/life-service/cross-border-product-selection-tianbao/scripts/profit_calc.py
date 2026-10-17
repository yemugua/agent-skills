# -*- coding: utf-8 -*-
"""\u8de8\u5883\u7535\u5546\u5355\u54c1\u5229\u6da6\u6838\u7b97\uff1a\u91c7\u8d2d\u4ef7\u3001\u5934\u7a0b\u3001\u5e73\u53f0\u4f63\u91d1\u3001FBA \u914d\u9001\u8d39\u3001\u5e7f\u544a\u3001\u9000\u8d27 -> \u6bdb\u5229\u7387\u4e0e\u4fdd\u672c ROI\u3002

\u7528\u6cd5:
  python profit_calc.py --file product.json [--out \u5229\u6da6\u6838\u7b97.md] [--format json]
  python profit_calc.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u5934\u7a0b\u5355\u4ef7\u9ed8\u8ba4\u503c\uff08\u5143/\u516c\u65a4\uff0c\u6309\u8ba1\u8d39\u91cd\uff09\uff0c\u5b9e\u9645\u4ee5\u8d27\u4ee3\u62a5\u4ef7\u4e3a\u51c6
FREIGHT_DEFAULT = {'sea': 12.0, 'air': 35.0, 'express': 55.0, 'self': 0.0}
FREIGHT_LABEL = {'sea': '\u6d77\u8fd0', 'air': '\u7a7a\u8fd0',
                 'express': '\u5feb\u9012', 'self': '\u81ea\u9001'}

# \u6bdb\u5229\u7387\u5224\u5b9a\u6863\u4f4d
GOOD = 0.25
WARN = 0.15


def money(x):
    return round(float(x) + 1e-9, 2)


def verdict_of(margin):
    if margin >= GOOD:
        return '\u53ef\u505a'
    if margin >= WARN:
        return '\u8c28\u614e'
    if margin > 0:
        return '\u4e0d\u5efa\u8bae'
    return '\u4e8f\u635f'


def verdict_text(v):
    return {
        '\u53ef\u505a': '\u6bdb\u5229\u7387\u8fbe\u6807\uff0c\u53ef\u4ee5\u6309\u8ba1\u5212\u63a8\u8fdb\uff1b\u4ecd\u9700\u5148\u505a\u5408\u89c4\u4e0e\u4fb5\u6743\u6392\u67e5',
        '\u8c28\u614e': '\u8584\u5229\u533a\u95f4\uff0c\u9700\u538b\u91c7\u8d2d\u4ef7\u6216\u63d0\u4ef7\uff0c\u6216\u964d\u4f4e\u5e7f\u544a\u5360\u6bd4\u540e\u518d\u8bc4\u4f30',
        '\u4e0d\u5efa\u8bae': '\u6bdb\u5229\u7387\u8fc7\u4f4e\uff0c\u6297\u98ce\u9669\u80fd\u529b\u5dee\uff0c\u5e7f\u544a\u6216\u9000\u8d27\u4e00\u6ce2\u52a8\u5c31\u4e8f\u635f',
        '\u4e8f\u635f': '\u6309\u5f53\u524d\u53c2\u6570\u5df2\u7ecf\u4e8f\u635f\uff0c\u4e0d\u8981\u4e0a\u67b6',
    }[v]


def calc(data):
    price = float(data.get('price_usd', 0))
    fx = float(data.get('fx', 7.0))
    cost = float(data.get('cost_cny', 0))
    weight = float(data.get('weight_kg', 0))
    length = float(data.get('length_cm', 0))
    width = float(data.get('width_cm', 0))
    height = float(data.get('height_cm', 0))
    divisor = float(data.get('vol_divisor', 6000))
    mode = str(data.get('freight_mode', 'air')).lower()
    rate = data.get('freight_rate_cny_per_kg')
    fba_usd = float(data.get('fba_fee_usd', 0))
    commission = float(data.get('commission_rate', 0.15))
    storage = float(data.get('storage_cny', 0))
    acos = float(data.get('acos', 0.0))
    ret_rate = float(data.get('return_rate', 0.0))
    ret_loss = float(data.get('return_loss_rate', 0.5))
    ret_handle = float(data.get('return_handling_cny', 0.0))
    other = float(data.get('other_cny', 0.0))

    if price <= 0:
        raise ValueError('\u552e\u4ef7\u5fc5\u987b\u4e3a\u6b63\u6570')
    if fx <= 0:
        raise ValueError('\u6c47\u7387\u5fc5\u987b\u4e3a\u6b63\u6570')
    if divisor <= 0:
        raise ValueError('\u4f53\u79ef\u91cd\u9664\u6570\u5fc5\u987b\u4e3a\u6b63\u6570')
    if commission < 0 or commission >= 1:
        raise ValueError('\u5e73\u53f0\u4f63\u91d1\u7387\u5e94\u5728 0 \u5230 1 \u4e4b\u95f4')
    if acos < 0 or acos >= 1:
        raise ValueError('\u5e7f\u544a\u5360\u6bd4\u5e94\u5728 0 \u5230 1 \u4e4b\u95f4')
    if mode not in FREIGHT_DEFAULT:
        raise ValueError('\u672a\u8bc6\u522b\u7684\u5934\u7a0b\u65b9\u5f0f: %s\uff08\u53ef\u9009 sea/air/express/self\uff09' % mode)
    if rate is None:
        rate = FREIGHT_DEFAULT[mode]
    rate = float(rate)

    vol_weight = length * width * height / divisor
    charge_weight = max(weight, vol_weight)
    freight = charge_weight * rate

    revenue = price * fx
    fba = fba_usd * fx
    commission_fee = revenue * commission
    ads = revenue * acos
    goods_cost = cost + freight + fba
    return_cost = ret_rate * (goods_cost * ret_loss + ret_handle)

    total = cost + freight + fba + commission_fee + ads + storage + other + return_cost
    profit = revenue - total
    margin = profit / revenue if revenue > 0 else 0.0

    # \u4e0d\u542b\u5e7f\u544a\u7684\u6bdb\u5229\u989d\u4e0e\u6bdb\u5229\u7387
    total_no_ads = total - ads
    profit_no_ads = revenue - total_no_ads
    margin_no_ads = profit_no_ads / revenue if revenue > 0 else 0.0

    # \u4fdd\u672c ACOS\uff1a\u5e7f\u544a\u5360\u6bd4\u8fbe\u5230\u8be5\u503c\u65f6\u5229\u6da6\u5f52\u96f6
    breakeven_acos = margin_no_ads
    breakeven_roi = (1.0 / breakeven_acos) if breakeven_acos > 0 else None

    # \u4fdd\u672c\u552e\u4ef7\uff1a\u53ea\u6263\u9664\u968f\u552e\u4ef7\u53d8\u52a8\u7684\u4f63\u91d1\u4e0e\u5e7f\u544a
    fixed = cost + freight + fba + storage + other + return_cost
    denom = 1.0 - commission - acos
    if denom <= 0:
        breakeven_price = None
    else:
        breakeven_price = fixed / denom / fx

    actual_roi = (1.0 / acos) if acos > 0 else None

    v = verdict_of(margin)
    warns = []
    if v in ('\u4e0d\u5efa\u8bae', '\u4e8f\u635f'):
        warns.append('\u6bdb\u5229\u7387 %.1f%%\uff0c%s' % (margin * 100, verdict_text(v)))
    if breakeven_roi is not None and actual_roi is not None and actual_roi < breakeven_roi:
        warns.append('\u5b9e\u9645\u5e7f\u544a ROI %.2f \u4f4e\u4e8e\u4fdd\u672c ROI %.2f\uff0c\u5e7f\u544a\u6295\u5165\u6b63\u5728\u5403\u6389\u5229\u6da6'
                     % (actual_roi, breakeven_roi))
    if breakeven_roi is not None and breakeven_roi > 4:
        warns.append('\u4fdd\u672c ROI %.2f \u504f\u9ad8\uff0c\u8bf4\u660e\u6bdb\u5229\u7a7a\u95f4\u5bf9\u5e7f\u544a\u654f\u611f\uff0c\u9700\u8c28\u614e\u653e\u91cf' % breakeven_roi)
    if vol_weight > weight:
        warns.append('\u4f53\u79ef\u91cd %.2f kg \u5927\u4e8e\u5b9e\u91cd %.2f kg\uff0c\u6309\u4f53\u79ef\u91cd\u8ba1\u8d39\uff0c\u5efa\u8bae\u4f18\u5316\u5305\u88c5\u5c3a\u5bf8'
                     % (vol_weight, weight))
    if ret_rate >= 0.15:
        warns.append('\u9000\u8d27\u7387 %.0f%% \u504f\u9ad8\uff0c\u9700\u6838\u5b9e\u7c7b\u76ee\u5b9e\u9645\u9000\u8d27\u6c34\u5e73\u5e76\u8ba1\u5165\u4e8c\u6b21\u9500\u552e\u635f\u8017' % (ret_rate * 100))

    return {
        'title': data.get('title', '\u672a\u547d\u540d\u4ea7\u54c1'),
        'price_usd': money(price),
        'fx': fx,
        'revenue_cny': money(revenue),
        'cost_cny': money(cost),
        'vol_weight_kg': round(vol_weight, 2),
        'charge_weight_kg': round(charge_weight, 2),
        'freight_mode': mode,
        'freight_mode_label': FREIGHT_LABEL.get(mode, mode),
        'freight_rate': money(rate),
        'freight_cny': money(freight),
        'fba_cny': money(fba),
        'commission_rate': commission,
        'commission_cny': money(commission_fee),
        'acos': acos,
        'ads_cny': money(ads),
        'storage_cny': money(storage),
        'return_rate': ret_rate,
        'return_cny': money(return_cost),
        'other_cny': money(other),
        'total_cny': money(total),
        'profit_cny': money(profit),
        'margin': round(margin, 4),
        'margin_no_ads': round(margin_no_ads, 4),
        'breakeven_acos': round(breakeven_acos, 4),
        'breakeven_roi': None if breakeven_roi is None else round(breakeven_roi, 2),
        'actual_roi': None if actual_roi is None else round(actual_roi, 2),
        'breakeven_price_usd': None if breakeven_price is None else money(breakeven_price),
        'verdict': v,
        'verdict_text': verdict_text(v),
        'warns': warns,
    }


def render_md(r):
    L = []
    L.append('# \u8de8\u5883\u5355\u54c1\u5229\u6da6\u6838\u7b97\uff1a%s' % r['title'])
    L.append('')
    L.append('## \u4e00\u3001\u6536\u5165\u4e0e\u6210\u672c\u660e\u7ec6\uff08\u4eba\u6c11\u5e01\uff09')
    L.append('')
    L.append('| \u9879 | \u91d1\u989d | \u8bf4\u660e |')
    L.append('|---|---|---|')
    L.append('| \u552e\u4ef7 | %.2f \u7f8e\u5143 | \u6c47\u7387 %.2f |' % (r['price_usd'], r['fx']))
    L.append('| \u9500\u552e\u6536\u5165 | %.2f | \u552e\u4ef7 \u00d7 \u6c47\u7387 |' % r['revenue_cny'])
    L.append('| \u91c7\u8d2d\u6210\u672c | %.2f | \u542b\u7a0e\u5230\u624b\u4ef7 |' % r['cost_cny'])
    L.append('| \u5934\u7a0b\u8fd0\u8d39 | %.2f | %s\uff0c%.2f \u5143/kg \u00d7 \u8ba1\u8d39\u91cd %.2f kg |'
             % (r['freight_cny'], r['freight_mode_label'], r['freight_rate'], r['charge_weight_kg']))
    L.append('| FBA \u914d\u9001\u8d39 | %.2f | \u6309\u5e73\u53f0\u8d39\u7387\u6863\u4f4d |' % r['fba_cny'])
    L.append('| \u5e73\u53f0\u4f63\u91d1 | %.2f | \u4f63\u91d1\u7387 %.0f%% |' % (r['commission_cny'], r['commission_rate'] * 100))
    L.append('| \u5e7f\u544a\u8d39 | %.2f | \u5e7f\u544a\u5360\u6bd4 %.0f%% |' % (r['ads_cny'], r['acos'] * 100))
    L.append('| \u4ed3\u50a8\u8d39 | %.2f | \u6708\u5ea6\u5206\u644a |' % r['storage_cny'])
    L.append('| \u9000\u8d27\u635f\u8017 | %.2f | \u9000\u8d27\u7387 %.0f%% |' % (r['return_cny'], r['return_rate'] * 100))
    L.append('| \u5176\u4ed6 | %.2f | \u5305\u88c5\u3001\u6536\u6b3e\u624b\u7eed\u8d39\u3001\u4eba\u5de5\u5206\u644a |' % r['other_cny'])
    L.append('| **\u6210\u672c\u5408\u8ba1** | **%.2f** | |' % r['total_cny'])
    L.append('| **\u51c0\u5229\u6da6** | **%.2f** | |' % r['profit_cny'])
    L.append('')
    L.append('## \u4e8c\u3001\u5229\u6da6\u7387\u4e0e\u4fdd\u672c\u7ebf')
    L.append('')
    L.append('| \u6307\u6807 | \u503c | \u8bf4\u660e |')
    L.append('|---|---|---|')
    L.append('| \u6bdb\u5229\u7387 | %.2f%% | \u51c0\u5229\u6da6 \u00f7 \u9500\u552e\u6536\u5165 |' % (r['margin'] * 100))
    L.append('| \u4e0d\u542b\u5e7f\u544a\u6bdb\u5229\u7387 | %.2f%% | \u5254\u9664\u5e7f\u544a\u540e\u7684\u6bdb\u5229\u7a7a\u95f4 |' % (r['margin_no_ads'] * 100))
    L.append('| \u4fdd\u672c\u5e7f\u544a\u5360\u6bd4 | %.2f%% | \u5e7f\u544a\u5360\u6bd4\u8fbe\u5230\u6b64\u503c\u65f6\u5229\u6da6\u5f52\u96f6 |' % (r['breakeven_acos'] * 100))
    L.append('| \u4fdd\u672c ROI | %s | \u5e7f\u544a ROI \u4f4e\u4e8e\u6b64\u503c\u5373\u4e8f\u635f |' % (r['breakeven_roi'] if r['breakeven_roi'] else '\u4e0d\u9002\u7528'))
    L.append('| \u5b9e\u9645 ROI | %s | 1 \u00f7 \u5e7f\u544a\u5360\u6bd4 |' % (r['actual_roi'] if r['actual_roi'] else '\u672a\u6295\u5e7f\u544a'))
    L.append('| \u4fdd\u672c\u552e\u4ef7 | %s \u7f8e\u5143 | \u552e\u4ef7\u4f4e\u4e8e\u6b64\u503c\u5373\u4e8f\u635f |'
             % (r['breakeven_price_usd'] if r['breakeven_price_usd'] else '\u4e0d\u9002\u7528'))
    L.append('')
    L.append('## \u4e09\u3001\u7ed3\u8bba')
    L.append('')
    L.append('- \u5224\u5b9a\uff1a**%s** \u2014\u2014 %s' % (r['verdict'], r['verdict_text']))
    L.append('- \u5224\u5b9a\u53e3\u5f84\uff1a\u6bdb\u5229\u7387 \u2265 25% \u53ef\u505a\uff1b15%-25% \u8c28\u614e\uff1b\u4f4e\u4e8e 15% \u4e0d\u5efa\u8bae\uff1b\u5c0f\u4e8e\u7b49\u4e8e 0 \u5373\u4e8f\u635f')
    L.append('')
    L.append('## \u56db\u3001\u63d0\u9192')
    L.append('')
    if r['warns']:
        for w in r['warns']:
            L.append('- %s' % w)
    else:
        L.append('- \u5f53\u524d\u53c2\u6570\u4e0b\u672a\u89e6\u53d1\u98ce\u9669\u63d0\u9192')
    L.append('')
    L.append('## \u4e94\u3001\u4eba\u5de5\u786e\u8ba4\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] \u5934\u7a0b\u5355\u4ef7\u4ee5\u8d27\u4ee3\u5b9e\u65f6\u62a5\u4ef7\u4e3a\u51c6\uff0c\u4e0d\u8981\u957f\u671f\u4f7f\u7528\u65e7\u4ef7')
    L.append('- [ ] FBA \u914d\u9001\u8d39\u6863\u4f4d\u4ee5\u5e73\u53f0\u6700\u65b0\u8d39\u7387\u8868\u4e3a\u51c6\uff0c\u5c3a\u5bf8\u6bb5\u53d8\u5316\u4f1a\u8df3\u6863')
    L.append('- [ ] \u9000\u8d27\u7387\u6309\u7c7b\u76ee\u5b9e\u9645\u6c34\u5e73\u53d6\u503c\uff0c\u670d\u88c5\u7c7b\u901a\u5e38\u9ad8\u4e8e 3C \u7c7b')
    L.append('- [ ] \u5df2\u505a\u4fb5\u6743\u4e0e\u5408\u89c4\u6392\u67e5\uff08\u5916\u89c2\u4e13\u5229\u3001\u5546\u6807\u3001\u8ba4\u8bc1\u8981\u6c42\u3001\u5e73\u53f0\u7981\u552e\u6e05\u5355\uff09')
    L.append('- [ ] \u6c47\u7387\u6309\u7ed3\u7b97\u5468\u671f\u7684\u5b9e\u9645\u6c47\u7387\u590d\u6838\uff0c\u6c47\u7387\u6ce2\u52a8\u4f1a\u76f4\u63a5\u5403\u6389\u6bdb\u5229')
    L.append('- [ ] \u672c\u6838\u7b97\u4e3a\u5355\u4ef6\u9759\u6001\u53e3\u5f84\uff0c\u672a\u542b\u9000\u4ed3\u3001\u9500\u6bc1\u3001\u957f\u671f\u4ed3\u50a8\u4e0e\u4fc3\u9500\u6298\u8ba9')
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

    base = {'title': '\u6d4b\u8bd5\u54c1A', 'price_usd': 20, 'fx': 7, 'cost_cny': 30,
            'weight_kg': 1.0, 'length_cm': 10, 'width_cm': 10, 'height_cm': 10,
            'freight_rate_cny_per_kg': 10, 'fba_fee_usd': 2, 'commission_rate': 0.15,
            'storage_cny': 2, 'acos': 0.10, 'other_cny': 1}

    # 1 \u6536\u5165\u4e0e\u660e\u7ec6\u9879
    r1 = calc(base)
    ck(r1['revenue_cny'] == 140.0, '\u7528\u4f8b1 \u6536\u5165\u5e94\u4e3a 140.00\uff0c\u5b9e\u4e3a %s' % r1['revenue_cny'])
    ck(r1['freight_cny'] == 10.0, '\u7528\u4f8b1 \u5934\u7a0b\u5e94\u4e3a 10.00\uff0c\u5b9e\u4e3a %s' % r1['freight_cny'])
    ck(r1['fba_cny'] == 14.0, '\u7528\u4f8b1 FBA \u8d39\u5e94\u4e3a 14.00\uff0c\u5b9e\u4e3a %s' % r1['fba_cny'])
    ck(r1['commission_cny'] == 21.0, '\u7528\u4f8b1 \u4f63\u91d1\u5e94\u4e3a 21.00\uff0c\u5b9e\u4e3a %s' % r1['commission_cny'])
    ck(r1['ads_cny'] == 14.0, '\u7528\u4f8b1 \u5e7f\u544a\u8d39\u5e94\u4e3a 14.00\uff0c\u5b9e\u4e3a %s' % r1['ads_cny'])

    # 2 \u51c0\u5229\u4e0e\u6bdb\u5229\u7387
    ck(r1['total_cny'] == 92.0, '\u7528\u4f8b2 \u6210\u672c\u5408\u8ba1\u5e94\u4e3a 92.00\uff0c\u5b9e\u4e3a %s' % r1['total_cny'])
    ck(r1['profit_cny'] == 48.0, '\u7528\u4f8b2 \u51c0\u5229\u5e94\u4e3a 48.00\uff0c\u5b9e\u4e3a %s' % r1['profit_cny'])
    ck(abs(r1['margin'] - 0.3429) < 0.001, '\u7528\u4f8b2 \u6bdb\u5229\u7387\u5e94\u7ea6 34.29%%\uff0c\u5b9e\u4e3a %s' % r1['margin'])
    ck(r1['verdict'] == '\u53ef\u505a', '\u7528\u4f8b2 \u5224\u5b9a\u5e94\u4e3a\u53ef\u505a\uff0c\u5b9e\u4e3a %s' % r1['verdict'])

    # 3 \u4fdd\u672c\u5e7f\u544a\u5360\u6bd4\u4e0e\u4fdd\u672c ROI
    ck(abs(r1['margin_no_ads'] - 0.4429) < 0.001, '\u7528\u4f8b3 \u4e0d\u542b\u5e7f\u544a\u6bdb\u5229\u7387\u5e94\u7ea6 44.29%%\uff0c\u5b9e\u4e3a %s' % r1['margin_no_ads'])
    ck(abs(r1['breakeven_acos'] - 0.4429) < 0.001, '\u7528\u4f8b3 \u4fdd\u672c\u5e7f\u544a\u5360\u6bd4\u5e94\u7ea6 44.29%%\uff0c\u5b9e\u4e3a %s' % r1['breakeven_acos'])
    ck(abs(r1['breakeven_roi'] - 2.26) < 0.01, '\u7528\u4f8b3 \u4fdd\u672c ROI \u5e94\u7ea6 2.26\uff0c\u5b9e\u4e3a %s' % r1['breakeven_roi'])
    ck(abs(r1['actual_roi'] - 10.0) < 0.01, '\u7528\u4f8b3 \u5b9e\u9645 ROI \u5e94\u4e3a 10.00\uff0c\u5b9e\u4e3a %s' % r1['actual_roi'])

    # 4 \u6309\u4fdd\u672c\u5e7f\u544a\u5360\u6bd4\u4ee3\u5165\uff0c\u5229\u6da6\u5e94\u5f52\u96f6
    r4 = calc(dict(base, acos=r1['breakeven_acos']))
    ck(abs(r4['profit_cny']) < 0.02, '\u7528\u4f8b4 \u4fdd\u672c\u5e7f\u544a\u5360\u6bd4\u4e0b\u5229\u6da6\u5e94\u7ea6\u7b49\u4e8e 0\uff0c\u5b9e\u4e3a %s' % r4['profit_cny'])

    # 5 \u6309\u4fdd\u672c\u552e\u4ef7\u4ee3\u5165\uff0c\u5229\u6da6\u5e94\u5f52\u96f6
    r5 = calc(dict(base, price_usd=r1['breakeven_price_usd']))
    ck(abs(r5['profit_cny']) < 0.05, '\u7528\u4f8b5 \u4fdd\u672c\u552e\u4ef7\u4e0b\u5229\u6da6\u5e94\u7ea6\u7b49\u4e8e 0\uff0c\u5b9e\u4e3a %s' % r5['profit_cny'])
    ck(abs(r1['breakeven_price_usd'] - 10.86) < 0.02, '\u7528\u4f8b5 \u4fdd\u672c\u552e\u4ef7\u5e94\u7ea6 10.86 \u7f8e\u5143\uff0c\u5b9e\u4e3a %s' % r1['breakeven_price_usd'])

    # 6 \u5224\u5b9a\u6863\u4f4d
    r6a = calc(dict(base, acos=0.30))
    ck(r6a['verdict'] in ('\u8c28\u614e', '\u4e0d\u5efa\u8bae'), '\u7528\u4f8b6 \u9ad8\u5e7f\u544a\u5360\u6bd4\u4e0d\u5e94\u5224\u5b9a\u4e3a\u53ef\u505a\uff0c\u5b9e\u4e3a %s' % r6a['verdict'])
    r6b = calc(dict(base, price_usd=11.5))
    ck(r6b['verdict'] in ('\u8c28\u614e', '\u4e0d\u5efa\u8bae', '\u4e8f\u635f'), '\u7528\u4f8b6 \u63a5\u8fd1\u4fdd\u672c\u552e\u4ef7\u4e0d\u5e94\u5224\u5b9a\u4e3a\u53ef\u505a\uff0c\u5b9e\u4e3a %s' % r6b['verdict'])
    r6c = calc(dict(base, price_usd=8))
    ck(r6c['verdict'] == '\u4e8f\u635f', '\u7528\u4f8b6 \u4f4e\u4e8e\u4fdd\u672c\u552e\u4ef7\u5e94\u5224\u5b9a\u4e3a\u4e8f\u635f\uff0c\u5b9e\u4e3a %s' % r6c['verdict'])
    ck(any('\u4e8f\u635f' in w or '\u6bdb\u5229\u7387' in w for w in r6c['warns']), '\u7528\u4f8b6 \u4e8f\u635f\u5e94\u6709\u63d0\u9192\uff0c\u5b9e\u4e3a %s' % r6c['warns'])

    # 7 \u4f53\u79ef\u91cd\u5927\u4e8e\u5b9e\u91cd\u65f6\u6309\u4f53\u79ef\u91cd\u8ba1\u8d39
    r7 = calc(dict(base, weight_kg=1.0, length_cm=30, width_cm=30, height_cm=30))
    ck(abs(r7['vol_weight_kg'] - 4.5) < 0.01, '\u7528\u4f8b7 \u4f53\u79ef\u91cd\u5e94\u4e3a 4.50 kg\uff0c\u5b9e\u4e3a %s' % r7['vol_weight_kg'])
    ck(abs(r7['charge_weight_kg'] - 4.5) < 0.01, '\u7528\u4f8b7 \u8ba1\u8d39\u91cd\u5e94\u53d6 4.50 kg\uff0c\u5b9e\u4e3a %s' % r7['charge_weight_kg'])
    ck(any('\u4f53\u79ef\u91cd' in w for w in r7['warns']), '\u7528\u4f8b7 \u6ce1\u8d27\u5e94\u6709\u63d0\u9192\uff0c\u5b9e\u4e3a %s' % r7['warns'])

    # 8 \u5934\u7a0b\u65b9\u5f0f\u9ed8\u8ba4\u8d39\u7387
    r8 = calc({'title': '\u6d77\u8fd0\u54c1', 'price_usd': 20, 'fx': 7, 'cost_cny': 30, 'weight_kg': 2,
               'freight_mode': 'sea', 'fba_fee_usd': 2, 'commission_rate': 0.15, 'acos': 0.1})
    ck(r8['freight_rate'] == 12.0, '\u7528\u4f8b8 \u6d77\u8fd0\u9ed8\u8ba4\u5e94\u4e3a 12.00 \u5143/kg\uff0c\u5b9e\u4e3a %s' % r8['freight_rate'])
    ck(r8['freight_cny'] == 24.0, '\u7528\u4f8b8 \u6d77\u8fd0\u5934\u7a0b\u5e94\u4e3a 24.00\uff0c\u5b9e\u4e3a %s' % r8['freight_cny'])

    # 9 \u9000\u8d27\u635f\u8017\u8ba1\u5165
    r9 = calc(dict(base, return_rate=0.2, return_loss_rate=0.5))
    expect = 0.2 * ((30 + 10 + 14) * 0.5)
    ck(abs(r9['return_cny'] - round(expect, 2)) < 0.02, '\u7528\u4f8b9 \u9000\u8d27\u635f\u8017\u5e94\u4e3a %.2f\uff0c\u5b9e\u4e3a %s' % (expect, r9['return_cny']))
    ck(r9['profit_cny'] < r1['profit_cny'], '\u7528\u4f8b9 \u8ba1\u5165\u9000\u8d27\u540e\u51c0\u5229\u5e94\u4e0b\u964d')

    # 10 \u975e\u6cd5\u53c2\u6570\u5e94\u62a5\u9519
    for bad in ({'price_usd': 0}, {'fx': 0}, {'commission_rate': 1.2}, {'acos': -0.1},
                {'freight_mode': 'rocket'}):
        d = dict(base)
        d.update(bad)
        try:
            calc(d)
            ck(False, '\u7528\u4f8b10 \u975e\u6cd5\u53c2\u6570 %s \u5e94\u629b\u9519' % bad)
        except ValueError:
            ck(True, '\u7528\u4f8b10 \u975e\u6cd5\u53c2\u6570 %s \u5e94\u629b\u9519' % bad)

    # 11 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r1)
    ck('\u4fdd\u672c ROI' in md, 'Markdown \u8f93\u51fa\u5e94\u5305\u542b\u4fdd\u672c ROI')
    ck('\u4eba\u5de5\u786e\u8ba4' in md, 'Markdown \u8f93\u51fa\u5e94\u5305\u542b\u4eba\u5de5\u786e\u8ba4\u6e05\u5355')
    j = json.loads(render_json(r1))
    ck(j['verdict'] == '\u53ef\u505a', 'JSON \u8f93\u51fa\u5224\u5b9a\u5e94\u4e0e\u8ba1\u7b97\u7ed3\u679c\u4e00\u81f4')

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u6536\u5165/\u5934\u7a0b/FBA/\u4f63\u91d1/\u5e7f\u544a/\u9000\u8d27\u635f\u8017/\u6bdb\u5229\u7387/\u4fdd\u672c\u5e7f\u544a\u5360\u6bd4/\u4fdd\u672cROI/\u4fdd\u672c\u552e\u4ef7/\u5224\u5b9a\u6863\u4f4d/\u4f53\u79ef\u91cd/\u6d77\u8fd0\u9ed8\u8ba4\u8d39\u7387/\u975e\u6cd5\u53c2\u6570/\u8f93\u51fa\u7ed3\u6784'
               % checks)
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u8de8\u5883\u7535\u5546\u5355\u54c1\u5229\u6da6\u6838\u7b97')
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
