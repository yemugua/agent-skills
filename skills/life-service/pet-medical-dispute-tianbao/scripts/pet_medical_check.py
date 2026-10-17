#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u5ba0\u7269\u533b\u7597\u7ea0\u7eb7\u8bc1\u636e\u6838\u67e5\u3001\u8d39\u7528\u6838\u67e5\u4e0e\u8d54\u507f\u8303\u56f4\u6d4b\u7b97\u3002

\u7528\u6cd5:
  python pet_medical_check.py --mode evidence --records medical_record,prescription,lab,detail,invoice,chat --death yes --necropsy no
  python pet_medical_check.py --mode fee --records detail,invoice --itemized yes --price-posted no --charged 3800 --market 2200
  python pet_medical_check.py --mode evidence --pet-value 12000 --years 3 --extra-cost 5000 --funeral 800
  python pet_medical_check.py --selftest

\u53c2\u6570:
  --mode          evidence \u8bc1\u636e\u5b8c\u6574\u6027\u6838\u67e5 / fee \u8d39\u7528\u6838\u67e5
  --records       \u5df2\u53d6\u5f97\u7684\u6750\u6599\uff0c\u9017\u53f7\u5206\u9694\uff1amedical_record \u75c5\u5386 / prescription \u5904\u65b9 /
                  lab \u5316\u9a8c\u4e0e\u5f71\u50cf\u62a5\u544a / consent \u77e5\u60c5\u540c\u610f\u4e66 / detail \u6536\u8d39\u660e\u7ec6 /
                  invoice \u53d1\u7968 / chat \u6c9f\u901a\u8bb0\u5f55 / video \u76d1\u63a7\u6216\u89c6\u9891 / necropsy \u5c38\u68c0\u6216\u75c5\u7406 /
                  license \u673a\u6784\u8d44\u8d28 / value_proof \u5ba0\u7269\u4ef7\u503c\u8bc1\u660e
  --death         yes/no \u5ba0\u7269\u662f\u5426\u5df2\u6b7b\u4ea1
  --itemized      yes/no \u662f\u5426\u53d6\u5f97\u9010\u9879\u6536\u8d39\u660e\u7ec6
  --price-posted  yes/no \u673a\u6784\u662f\u5426\u660e\u7801\u6807\u4ef7
  --charged       \u5b9e\u9645\u6536\u53d6\u7684\u8d39\u7528\u603b\u989d
  --market        \u540c\u7c7b\u9879\u76ee\u5e02\u573a\u53c2\u8003\u4ef7
  --pet-value     \u5ba0\u7269\u8d2d\u4e70\u4ef7\u683c
  --years         \u5df2\u9972\u517b\u5e74\u9650
  --extra-cost    \u56e0\u7ea0\u7eb7\u989d\u5916\u652f\u51fa\u7684\u6cbb\u7597\u8d39
  --funeral       \u4e27\u846c\u6216\u65e0\u5bb3\u5316\u5904\u7406\u8d39
  --out           \u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84
  --format        md\uff08\u9ed8\u8ba4\uff09\u6216 json
  --selftest      \u8fd0\u884c\u5185\u7f6e\u81ea\u68c0
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

RECORD_NAME = {
    'medical_record': '\u95e8\u8bca\u6216\u4f4f\u9662\u75c5\u5386',
    'prescription': '\u5904\u65b9\u4e0e\u7528\u836f\u8bb0\u5f55',
    'lab': '\u5316\u9a8c\u5355\u4e0e\u5f71\u50cf\u62a5\u544a',
    'consent': '\u77e5\u60c5\u540c\u610f\u4e66',
    'detail': '\u9010\u9879\u6536\u8d39\u660e\u7ec6',
    'invoice': '\u53d1\u7968\u6216\u6b63\u89c4\u6536\u636e',
    'chat': '\u6c9f\u901a\u8bb0\u5f55\uff08\u539f\u59cb\u8f7d\u4f53\uff09',
    'video': '\u76d1\u63a7\u6216\u89c6\u9891\u8d44\u6599',
    'necropsy': '\u5c38\u68c0\u6216\u75c5\u7406\u62a5\u544a',
    'license': '\u673a\u6784\u8d44\u8d28\uff08\u52a8\u7269\u8bca\u7597\u8bb8\u53ef\u8bc1\u7b49\uff09',
    'value_proof': '\u5ba0\u7269\u4ef7\u503c\u8bc1\u660e\uff08\u8d2d\u4e70\u51ed\u8bc1\u7b49\uff09',
}
BASE_RECORDS = ['medical_record', 'prescription', 'lab', 'detail', 'invoice', 'chat']
DEATH_RECORDS = ['necropsy', 'video']
DEPRECIATION_YEARS = 10
RATIO_ABNORMAL = 1.5


def check_evidence(args):
    have = [x.strip() for x in (args.records or '').split(',') if x.strip()]
    need = list(BASE_RECORDS)
    if args.death == 'yes':
        need += DEATH_RECORDS
    items = []

    def add(name, ok, detail):
        items.append({'name': name, 'result': ok, 'detail': detail})

    for r in need:
        if r in have:
            add(RECORD_NAME.get(r, r), '\u7b26\u5408', '\u5df2\u53d6\u5f97')
        else:
            if r == 'necropsy':
                add(RECORD_NAME.get(r, r), '\u4e0d\u7b26\u5408',
                    '\u5ba0\u7269\u6b7b\u4ea1\u4f46\u65e0\u5c38\u68c0\u6216\u75c5\u7406\u62a5\u544a\uff0c\u6b7b\u56e0\u65e0\u6cd5\u67e5\u660e\uff0c\u56e0\u679c\u5173\u7cfb\u4e3e\u8bc1\u4f1a\u975e\u5e38\u56f0\u96be\uff1b'
                    '\u6b7b\u4ea1\u540e\u5e94\u5c3d\u5feb\u5c38\u68c0\uff0c\u52ff\u5148\u884c\u706b\u5316\u6216\u63a9\u57cb')
            elif r == 'video':
                add(RECORD_NAME.get(r, r), '\u4e0d\u7b26\u5408',
                    '\u672a\u53d6\u5f97\u76d1\u63a7\u6216\u89c6\u9891\u8d44\u6599\uff1b\u76d1\u63a7\u4e00\u822c\u6570\u5468\u5373\u8986\u76d6\uff0c\u5e94\u5c3d\u65e9\u4e66\u9762\u8981\u6c42\u673a\u6784\u4fdd\u5b58')
            elif r == 'detail':
                add(RECORD_NAME.get(r, r), '\u4e0d\u7b26\u5408',
                    '\u6ca1\u6709\u9010\u9879\u6536\u8d39\u660e\u7ec6\u5c31\u65e0\u6cd5\u6838\u67e5\u672a\u505a\u9879\u76ee\u6536\u8d39\u4e0e\u91cd\u590d\u6536\u8d39\uff0c\u5e94\u5411\u673a\u6784\u7d22\u8981')
            elif r == 'medical_record':
                add(RECORD_NAME.get(r, r), '\u4e0d\u7b26\u5408',
                    '\u75c5\u5386\u662f\u5224\u65ad\u8bca\u7597\u8fc7\u9519\u7684\u57fa\u7840\uff0c\u4e8b\u540e\u8865\u8981\u53ef\u80fd\u88ab\u62d2\uff0c\u5e94\u5c3d\u65e9\u7d22\u53d6\u5e76\u62cd\u7167\u7559\u5b58')
            else:
                add(RECORD_NAME.get(r, r), '\u4e0d\u7b26\u5408', '\u7f3a\u5931\uff0c\u9700\u8865\u5145')

    if args.death == 'yes':
        add('\u6b7b\u56e0\u67e5\u660e', '\u7b26\u5408' if 'necropsy' in have else '\u4e0d\u7b26\u5408',
            '\u5c38\u68c0\u662f\u67e5\u660e\u6b7b\u56e0\u6700\u53ef\u9760\u7684\u624b\u6bb5')
    else:
        add('\u6b7b\u56e0\u67e5\u660e', '\u7b26\u5408', '\u5ba0\u7269\u5b58\u6d3b\uff0c\u4e0d\u6d89\u53ca\u6b7b\u56e0\u67e5\u660e')

    add('\u673a\u6784\u8d44\u8d28\u6838\u9a8c', '\u7b26\u5408' if 'license' in have else '\u9700\u6838\u5b9e',
        '\u5e94\u6838\u5b9e\u52a8\u7269\u8bca\u7597\u8bb8\u53ef\u8bc1\u4e0e\u6267\u4e1a\u517d\u533b\u8d44\u683c\uff0c\u65e0\u8d44\u8d28\u673a\u6784\u51fa\u4e8b\u540e\u8fde\u8bca\u7597\u89c4\u8303\u90fd\u65e0\u4ece\u5bf9\u7167')

    blocked = [i for i in items if i['result'] == '\u4e0d\u7b26\u5408']
    if any(i['name'] == '\u5c38\u68c0\u6216\u75c5\u7406\u62a5\u544a' for i in blocked):
        verdict = '\u5173\u952e\u8bc1\u636e\u7f3a\u5931\uff0c\u56e0\u679c\u5173\u7cfb\u4e3e\u8bc1\u5b58\u5728\u91cd\u5927\u969c\u788d'
    elif blocked:
        verdict = '\u8bc1\u636e\u7f3a\u5931 {} \u9879\uff0c\u9700\u5c3d\u5feb\u8865\u5145'.format(len(blocked))
    else:
        verdict = '\u6838\u5fc3\u8bc1\u636e\u57fa\u672c\u9f50\u5907\uff0c\u53ef\u8fdb\u5165\u534f\u5546\u6216\u6295\u8bc9\u73af\u8282'
    return {
        'mode': 'evidence',
        'items': items,
        'blocked': [i['name'] + '\uff1a' + i['detail'] for i in blocked],
        'todo': [],
        'verdict': verdict,
    }


def check_fee(args):
    have = [x.strip() for x in (args.records or '').split(',') if x.strip()]
    items = []

    def add(name, ok, detail):
        items.append({'name': name, 'result': ok, 'detail': detail})

    if args.itemized == 'yes':
        add('\u6536\u8d39\u660e\u7ec6', '\u7b26\u5408', '\u5df2\u53d6\u5f97\u9010\u9879\u6536\u8d39\u660e\u7ec6\uff0c\u53ef\u9010\u9879\u4e0e\u62a5\u544a\u3001\u5904\u65b9\u5bf9\u8d26')
    else:
        add('\u6536\u8d39\u660e\u7ec6', '\u4e0d\u7b26\u5408',
            '\u53ea\u6709\u603b\u989d\u65e0\u6cd5\u6838\u67e5\u672a\u505a\u9879\u76ee\u6536\u8d39\u4e0e\u91cd\u590d\u6536\u8d39\uff1b\u5e94\u5411\u673a\u6784\u7d22\u8981\u542b\u9879\u76ee\u540d\u3001\u5355\u4ef7\u3001\u6570\u91cf\u3001\u65e5\u671f\u7684\u660e\u7ec6')

    if args.price_posted == 'yes':
        add('\u660e\u7801\u6807\u4ef7', '\u7b26\u5408', '\u5df2\u516c\u793a\u4ef7\u683c\uff0c\u5e94\u6bd4\u5bf9\u516c\u793a\u4ef7\u4e0e\u5b9e\u9645\u7ed3\u7b97\u4ef7\u662f\u5426\u4e00\u81f4')
    else:
        add('\u660e\u7801\u6807\u4ef7', '\u9700\u6838\u5b9e',
            '\u8bca\u7597\u670d\u52a1\u4e0e\u836f\u54c1\u8017\u6750\u5e94\u660e\u7801\u6807\u4ef7\uff1b\u672a\u6807\u4ef7\u6216\u7ed3\u7b97\u4ef7\u4e0e\u516c\u793a\u4ef7\u4e0d\u4e00\u81f4\u7684\uff0c'
            '\u53ef\u5411\u5e02\u573a\u76d1\u7763\u7ba1\u7406\u90e8\u95e8\u53cd\u6620')

    if 'invoice' in have:
        add('\u53d1\u7968\u6216\u6536\u636e', '\u7b26\u5408', '\u5df2\u53d6\u5f97\u53d1\u7968\u6216\u6b63\u89c4\u6536\u636e')
    else:
        add('\u53d1\u7968\u6216\u6536\u636e', '\u4e0d\u7b26\u5408', '\u5e94\u7d22\u8981\u53d1\u7968\uff1b\u624b\u5199\u6536\u636e\u8bc1\u660e\u529b\u5f31\uff0c\u652f\u4ed8\u51ed\u8bc1\u4e5f\u8981\u7559\u5b58')

    disputed = None
    if args.charged is not None and args.market is not None and args.market > 0:
        ratio = args.charged / args.market
        disputed = args.charged - args.market
        if ratio > RATIO_ABNORMAL:
            add('\u6536\u8d39\u4e0e\u5e02\u573a\u53c2\u8003\u4ef7\u5bf9\u6bd4', '\u5b58\u7591',
                '\u5b9e\u6536 {} \u5143\uff0c\u5e02\u573a\u53c2\u8003\u4ef7 {} \u5143\uff0c\u4e3a\u53c2\u8003\u4ef7\u7684 {:.1f} \u500d\uff0c'
                '\u5dee\u5f02\u91d1\u989d\u7ea6 {} \u5143\uff0c\u5efa\u8bae\u9010\u9879\u5bf9\u8d26\u540e\u5411\u673a\u6784\u4e66\u9762\u95ee\u8be2'.format(
                    fmt_num(args.charged), fmt_num(args.market), ratio, fmt_num(disputed)))
        else:
            add('\u6536\u8d39\u4e0e\u5e02\u573a\u53c2\u8003\u4ef7\u5bf9\u6bd4', '\u7b26\u5408',
                '\u5b9e\u6536 {} \u5143\uff0c\u5e02\u573a\u53c2\u8003\u4ef7 {} \u5143\uff0c\u4e3a\u53c2\u8003\u4ef7\u7684 {:.1f} \u500d\uff0c\u5904\u4e8e\u5e38\u89c1\u6ce2\u52a8\u533a\u95f4'.format(
                    fmt_num(args.charged), fmt_num(args.market), ratio))
    else:
        add('\u6536\u8d39\u4e0e\u5e02\u573a\u53c2\u8003\u4ef7\u5bf9\u6bd4', '\u9700\u6838\u5b9e', '\u672a\u63d0\u4f9b --charged \u6216 --market\uff0c\u672a\u505a\u5bf9\u6bd4')

    blocked = [i for i in items if i['result'] == '\u4e0d\u7b26\u5408']
    todo = [i for i in items if i['result'] in ('\u9700\u6838\u5b9e', '\u5b58\u7591')]
    if blocked:
        verdict = '\u8d39\u7528\u51ed\u8bc1\u4e0d\u5b8c\u6574\uff0c\u9700\u5148\u8865\u9f50\u660e\u7ec6\u4e0e\u53d1\u7968'
    elif todo:
        verdict = '\u51ed\u8bc1\u57fa\u672c\u9f50\u5168\uff0c\u5b58\u5728\u9700\u9010\u9879\u5bf9\u8d26\u7684\u7591\u70b9'
    else:
        verdict = '\u8d39\u7528\u51ed\u8bc1\u9f50\u5168\uff0c\u672a\u89c1\u660e\u663e\u5f02\u5e38'
    return {
        'mode': 'fee',
        'items': items,
        'blocked': [i['name'] + '\uff1a' + i['detail'] for i in blocked],
        'todo': [i['name'] + '\uff1a' + i['detail'] for i in todo],
        'disputed': disputed,
        'verdict': verdict,
    }


def compensation(pet_value, years, extra_cost, funeral):
    """\u8d54\u507f\u8303\u56f4\u53c2\u8003\u6d4b\u7b97\u3002"""
    if pet_value is None:
        return None
    y = years or 0
    life = max(DEPRECIATION_YEARS - y, 0)
    residual = pet_value * life / DEPRECIATION_YEARS
    extra = extra_cost or 0
    fun = funeral or 0
    total = residual + extra + fun
    return {
        'pet_value': pet_value,
        'years': y,
        'depreciation_years': DEPRECIATION_YEARS,
        'residual': residual,
        'extra_cost': extra,
        'funeral': fun,
        'total': total,
    }


def fmt_num(v):
    if v is None:
        return ''
    if float(v).is_integer():
        return '{:,.0f}'.format(float(v))
    return '{:,.2f}'.format(float(v))


def render_md(r, comp):
    out = []
    out.append('# \u5ba0\u7269\u533b\u7597\u7ea0\u7eb7\u6838\u67e5\u7ed3\u679c')
    out.append('')
    out.append('- \u6838\u67e5\u6a21\u5f0f\uff1a{}'.format('\u8bc1\u636e\u5b8c\u6574\u6027\u6838\u67e5' if r['mode'] == 'evidence' else '\u8d39\u7528\u6838\u67e5'))
    out.append('- \u7ed3\u8bba\uff1a{}'.format(r['verdict']))
    if r.get('disputed') is not None:
        out.append('- \u4e0e\u5e02\u573a\u53c2\u8003\u4ef7\u7684\u5dee\u5f02\u91d1\u989d\uff1a\u7ea6 {} \u5143'.format(fmt_num(r['disputed'])))
    out.append('')
    out.append('| \u6838\u67e5\u9879 | \u7ed3\u679c | \u8bf4\u660e |')
    out.append('|---|---|---|')
    for i in r['items']:
        out.append('| {} | {} | {} |'.format(i['name'], i['result'], i['detail']))
    out.append('')
    if r['blocked']:
        out.append('## \u7f3a\u5931\u6216\u4e0d\u5408\u89c4\u9879')
        out.append('')
        for b in r['blocked']:
            out.append('- {}'.format(b))
        out.append('')
    if comp:
        out.append('## \u8d54\u507f\u8303\u56f4\u53c2\u8003\u6d4b\u7b97')
        out.append('')
        out.append('| \u9879\u76ee | \u91d1\u989d\uff08\u5143\uff09 | \u8bf4\u660e |')
        out.append('|---|---|---|')
        out.append('| \u5ba0\u7269\u672c\u8eab\u4ef7\u503c\uff08\u6298\u51cf\u540e\uff09 | {} | \u8d2d\u4e70\u4ef7 {} \u5143\uff0c\u5df2\u9972\u517b {} \u5e74\uff0c'
                   '\u6309 {} \u5e74\u53c2\u8003\u9972\u517b\u5e74\u9650\u6298\u51cf |'.format(
                       fmt_num(comp['residual']), fmt_num(comp['pet_value']),
                       comp['years'], comp['depreciation_years']))
        out.append('| \u989d\u5916\u6cbb\u7597\u8d39 | {} | \u51ed\u7968\u636e |'.format(fmt_num(comp['extra_cost'])))
        out.append('| \u4e27\u846c\u6216\u65e0\u5bb3\u5316\u5904\u7406\u8d39 | {} | \u51ed\u7968\u636e |'.format(fmt_num(comp['funeral'])))
        out.append('| **\u5408\u8ba1\uff08\u53c2\u8003\uff09** | **{}** | \u4e0d\u542b\u7cbe\u795e\u635f\u5bb3\uff0c\u6700\u7ec8\u4ee5\u534f\u5546\u6216\u88c1\u5224\u8ba4\u5b9a\u4e3a\u51c6 |'.format(
            fmt_num(comp['total'])))
        out.append('')
        out.append('> \u5ba0\u7269\u5728\u6cd5\u5f8b\u4e0a\u4e00\u822c\u4f5c\u4e3a\u7269\uff08\u8d22\u4ea7\uff09\u5bf9\u5f85\uff0c\u7cbe\u795e\u635f\u5bb3\u8d54\u507f\u901a\u5e38\u4e0d\u4e88\u652f\u6301\uff1b'
                   '\u4e2a\u522b\u6848\u4f8b\u4e2d\u6cd5\u9662\u53ef\u80fd\u5c31\u5177\u6709\u4eba\u8eab\u610f\u4e49\u7684\u7279\u5b9a\u7269\u4f5c\u51fa\u4e0d\u540c\u5904\u7406\uff0c\u4ee5\u4e2a\u6848\u8ba4\u5b9a\u4e3a\u51c6\u3002')
        out.append('')
    out.append('## \u63d0\u9192')
    out.append('')
    out.append('1. \u5ba0\u7269\u6b7b\u4ea1\u540e\u5e94\u5c3d\u5feb\u5c38\u68c0\uff0c\u52ff\u5148\u884c\u706b\u5316\u6216\u63a9\u57cb\uff0c\u5426\u5219\u6b7b\u56e0\u65e0\u6cd5\u67e5\u660e\u3002')
    out.append('2. \u76d1\u63a7\u5f55\u50cf\u4f1a\u8986\u76d6\uff0c\u4e8b\u53d1\u540e\u5e94\u5c3d\u65e9\u4e66\u9762\u8981\u6c42\u673a\u6784\u4fdd\u5b58\u3002')
    out.append('3. \u6536\u8d39\u4e89\u8bae\u4e0e\u8bca\u7597\u8fc7\u9519\u662f\u4e24\u4ef6\u4e8b\uff0c\u5e94\u5206\u5f00\u4e3b\u5f20\u3001\u5206\u522b\u4e3e\u8bc1\u3002')
    out.append('4. \u6c9f\u901a\u8bb0\u5f55\u4fdd\u7559\u539f\u59cb\u8f7d\u4f53\uff0c\u4e0d\u8981\u53ea\u7528\u622a\u56fe\u3002')
    out.append('5. \u8d54\u507f\u6570\u989d\u4ee5\u534f\u5546\u6216\u4e89\u8bae\u5904\u7406\u673a\u6784\u7684\u8ba4\u5b9a\u4e3a\u51c6\uff0c\u672c\u6d4b\u7b97\u4ec5\u4e3a\u53c2\u8003\u53e3\u5f84\u3002')
    out.append('')
    return '\n'.join(out)


def selftest():
    errors = []

    def eq(name, got, want):
        if got != want:
            errors.append('%s: got=%r want=%r' % (name, got, want))

    class A(object):
        pass

    def mk(**kw):
        a = A()
        a.records = kw.get('records', '')
        a.death = kw.get('death', 'no')
        a.itemized = kw.get('itemized', 'yes')
        a.price_posted = kw.get('price_posted', 'yes')
        a.charged = kw.get('charged', None)
        a.market = kw.get('market', None)
        return a

    base = 'medical_record,prescription,lab,detail,invoice,chat'
    r1 = check_evidence(mk(records=base))
    eq('case1 \u672a\u6b7b\u4ea1\u8bc1\u636e\u9f50\u5907', r1['blocked'], [])
    eq('case1 \u7ed3\u8bba', r1['verdict'], '\u6838\u5fc3\u8bc1\u636e\u57fa\u672c\u9f50\u5907\uff0c\u53ef\u8fdb\u5165\u534f\u5546\u6216\u6295\u8bc9\u73af\u8282')

    r2 = check_evidence(mk(records='medical_record'))
    eq('case2 \u5927\u91cf\u8bc1\u636e\u7f3a\u5931', len(r2['blocked']) > 0, True)
    eq('case2 \u7ed3\u8bba\u542b\u7f3a\u5931', '\u8bc1\u636e\u7f3a\u5931' in r2['verdict'], True)

    r3 = check_evidence(mk(records=base, death='yes'))
    names3 = [i['name'] for i in r3['items'] if i['result'] == '\u4e0d\u7b26\u5408']
    eq('case3 \u6b7b\u4ea1\u9700\u5c38\u68c0', '\u5c38\u68c0\u6216\u75c5\u7406\u62a5\u544a' in names3, True)
    eq('case3 \u6b7b\u4ea1\u9700\u76d1\u63a7', '\u76d1\u63a7\u6216\u89c6\u9891\u8d44\u6599' in names3, True)
    eq('case3 \u7ed3\u8bba', r3['verdict'], '\u5173\u952e\u8bc1\u636e\u7f3a\u5931\uff0c\u56e0\u679c\u5173\u7cfb\u4e3e\u8bc1\u5b58\u5728\u91cd\u5927\u969c\u788d')

    r4 = check_evidence(mk(records=base + ',necropsy,video', death='yes'))
    eq('case4 \u6b7b\u4ea1\u8bc1\u636e\u9f50\u5907', r4['blocked'], [])
    eq('case4 \u7ed3\u8bba', r4['verdict'], '\u6838\u5fc3\u8bc1\u636e\u57fa\u672c\u9f50\u5907\uff0c\u53ef\u8fdb\u5165\u534f\u5546\u6216\u6295\u8bc9\u73af\u8282')

    r5 = check_evidence(mk(records=base))
    lic = [i for i in r5['items'] if i['name'] == '\u673a\u6784\u8d44\u8d28\u6838\u9a8c'][0]
    eq('case5 \u672a\u6838\u8d44\u8d28\u9700\u6838\u5b9e', lic['result'], '\u9700\u6838\u5b9e')

    s1 = check_fee(mk(records='detail,invoice', itemized='yes', price_posted='yes',
                      charged=3800, market=2200))
    eq('case6 \u6536\u8d39\u9ad8\u4e8e\u53c2\u8003\u4ef71.5\u500d', s1['verdict'], '\u51ed\u8bc1\u57fa\u672c\u9f50\u5168\uff0c\u5b58\u5728\u9700\u9010\u9879\u5bf9\u8d26\u7684\u7591\u70b9')
    eq('case6 \u5dee\u5f02\u91d1\u989d', s1['disputed'], 1600)

    s2 = check_fee(mk(records='detail,invoice', itemized='yes', price_posted='yes',
                      charged=2400, market=2200))
    eq('case7 \u6536\u8d39\u5728\u5408\u7406\u533a\u95f4', s2['verdict'], '\u8d39\u7528\u51ed\u8bc1\u9f50\u5168\uff0c\u672a\u89c1\u660e\u663e\u5f02\u5e38')

    s3 = check_fee(mk(records='invoice', itemized='no', price_posted='no'))
    eq('case8 \u65e0\u660e\u7ec6\u4e0e\u672a\u6807\u4ef7', s3['verdict'], '\u8d39\u7528\u51ed\u8bc1\u4e0d\u5b8c\u6574\uff0c\u9700\u5148\u8865\u9f50\u660e\u7ec6\u4e0e\u53d1\u7968')

    s4 = check_fee(mk(records='detail'))
    names4 = [i['name'] for i in s4['items'] if i['result'] == '\u4e0d\u7b26\u5408']
    eq('case9 \u7f3a\u53d1\u7968', '\u53d1\u7968\u6216\u6536\u636e' in names4, True)

    c1 = compensation(12000, 3, 5000, 800)
    eq('case10 \u6298\u51cf\u540e\u5ba0\u7269\u4ef7\u503c', round(c1['residual'], 2), 8400.0)
    eq('case10 \u5408\u8ba1', round(c1['total'], 2), 14200.0)

    c2 = compensation(12000, 12, 0, 0)
    eq('case11 \u8d85\u5e74\u9650\u6b8b\u503c\u4e3a\u96f6', round(c2['residual'], 2), 0.0)

    eq('case12 \u672a\u63d0\u4f9b\u8d2d\u4e70\u4ef7\u4e0d\u6d4b\u7b97', compensation(None, 3, 500, 0), None)

    s5 = check_fee(mk(records='detail,invoice', itemized='yes', price_posted='yes',
                      charged=3000, market=0))
    eq('case13 \u5e02\u573a\u4ef7\u4e3a0\u4e0d\u5bf9\u6bd4', s5['disputed'], None)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 13\n\u8986\u76d6: \u8bc1\u636e\u9f50\u5907\u4e0e\u7f3a\u5931/\u6b7b\u4ea1\u9700\u5c38\u68c0\u4e0e\u76d1\u63a7/\u673a\u6784\u8d44\u8d28\u6838\u9a8c/'
               '\u6536\u8d39\u660e\u7ec6\u4e0e\u53d1\u7968/\u660e\u7801\u6807\u4ef7/\u5e02\u573a\u4ef71.5\u500d\u5f02\u5e38\u5224\u5b9a/\u8d54\u507f\u6298\u51cf\u4e0e\u5408\u8ba1/\u8fb9\u754c\u503c')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u5ba0\u7269\u533b\u7597\u7ea0\u7eb7\u8bc1\u636e\u6838\u67e5\u4e0e\u8d39\u7528\u6d4b\u7b97')
    ap.add_argument('--mode', default='evidence', choices=['evidence', 'fee'])
    ap.add_argument('--records', default='', help='\u5df2\u53d6\u5f97\u7684\u6750\u6599\uff0c\u9017\u53f7\u5206\u9694')
    ap.add_argument('--death', default='no', choices=['yes', 'no'])
    ap.add_argument('--itemized', default='yes', choices=['yes', 'no'])
    ap.add_argument('--price-posted', dest='price_posted', default='yes', choices=['yes', 'no'])
    ap.add_argument('--charged', type=float, help='\u5b9e\u9645\u6536\u53d6\u7684\u8d39\u7528\u603b\u989d')
    ap.add_argument('--market', type=float, help='\u540c\u7c7b\u9879\u76ee\u5e02\u573a\u53c2\u8003\u4ef7')
    ap.add_argument('--pet-value', dest='pet_value', type=float, help='\u5ba0\u7269\u8d2d\u4e70\u4ef7\u683c')
    ap.add_argument('--years', type=float, default=0, help='\u5df2\u9972\u517b\u5e74\u9650')
    ap.add_argument('--extra-cost', dest='extra_cost', type=float, help='\u989d\u5916\u652f\u51fa\u7684\u6cbb\u7597\u8d39')
    ap.add_argument('--funeral', type=float, help='\u4e27\u846c\u6216\u65e0\u5bb3\u5316\u5904\u7406\u8d39')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'])
    ap.add_argument('--selftest', action='store_true', help='\u8fd0\u884c\u5185\u7f6e\u81ea\u68c0')
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    r = check_evidence(args) if args.mode == 'evidence' else check_fee(args)
    comp = compensation(args.pet_value, args.years, args.extra_cost, args.funeral)
    out = render_md(r, comp) if args.format == 'md' else json.dumps(
        {'result': r, 'compensation': comp}, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % args.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
