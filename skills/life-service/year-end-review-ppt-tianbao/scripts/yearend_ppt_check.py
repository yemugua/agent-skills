# -*- coding: utf-8 -*-
"""\u8ff0\u804c PPT \u6838\u67e5\uff1a\u9875\u5e8f\u5b8c\u6574\u5ea6\u3001\u7ed3\u8bba\u53e5\u8986\u76d6\u3001\u91cf\u5316\u6838\u7b97\u3001\u5806\u5de5\u4f5c\u91cf\u4e0e\u7529\u9505\u626b\u63cf\u3002

\u7528\u6cd5:
  python yearend_ppt_check.py --file ppt.json [--out result.md] [--format json]
  python yearend_ppt_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

SECTIONS = ('conclusion', 'data', 'highlight', 'problem', 'plan')
SEC_CN = {
    'conclusion': '\u7ed3\u8bba', 'data': '\u6570\u636e', 'highlight': '\u4eae\u70b9',
    'problem': '\u95ee\u9898', 'plan': '\u8ba1\u5212',
}
DIRECTIONS = ('up', 'down')

# \u8986\u76d6\u7387\u7ea2\u7ebf
ORDER_RED = 80.0
CONCL_RED = 80.0
SOURCE_RED = 80.0
QUANT_RED = 70.0
# \u6307\u6807\u6570\u533a\u95f4
N_MIN = 3
N_BEST_LO = 5
N_BEST_HI = 8
N_MAX = 12
WEIGHT_TOL = 0.001
# \u5355\u9875\u8bb2\u8ff0\u79d2\u6570\u4e0a\u9650
PAGE_SEC_MAX = 90

# \u9875\u6570\u4e0e\u65f6\u957f\u914d\u6bd4\uff08\u4e0b\u9650, \u4e0a\u9650\uff09
PAGES_BY_MIN = ((0, 12, 8), (12, 18, 14), (18, 30, 22))

# \u5806\u5de5\u4f5c\u91cf\u8868\u8ff0
WORKLOAD = ('\u79ef\u6781\u53c2\u4e0e', '\u8ba4\u771f\u8d1f\u8d23', '\u52a0\u73ed\u52a0\u70b9', '\u5706\u6ee1\u5b8c\u6210\u5404\u9879\u4efb\u52a1',
            '\u5168\u529b\u4ee5\u8d74', '\u4fdd\u8d28\u4fdd\u91cf\u5b8c\u6210', '\u670d\u4ece\u5b89\u6392', '\u4efb\u52b3\u4efb\u6028',
            '\u5b8c\u6210\u5404\u7c7b\u9879\u76ee', '\u627f\u62c5\u4e86', '\u5404\u9879\u4efb\u52a1')

# \u7591\u4f3c\u7529\u9505\u53e5
BLAME = ('\u56e0\u4ea7\u54c1\u9700\u6c42', '\u56e0\u4e3a\u9700\u6c42\u53d8\u66f4', '\u7531\u4e8e\u8d44\u6e90\u4e0d\u8db3', '\u522b\u7684\u90e8\u95e8',
         '\u5176\u4ed6\u90e8\u95e8\u4e0d\u914d\u5408', '\u4ed6\u4eec\u4e0d\u914d\u5408', '\u7531\u4e8e\u65f6\u95f4\u7d27', '\u53d7\u9650\u4e8e',
         '\u5ba2\u89c2\u539f\u56e0', '\u4e0d\u662f\u6211\u7684\u95ee\u9898')

# \u7ed3\u8bba\u53e5\u56db\u7c7b\u5199\u6cd5\u4fe1\u53f7
CONCLUSION_HINTS = ('\u4ece', '\u964d\u5230', '\u63d0\u5347\u5230', '\u8fbe\u5230', '\u8fbe\u6210', '\u540c\u6bd4',
                     '\u73af\u6bd4', '\u5b8c\u6210', '\u4ea4\u4ed8', '\u540c\u6bd4\u4e0b\u964d', '\u672a\u8fbe\u6210')


def load(text=None, path=None):
    if text:
        return json.loads(text)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def pct(x, nd=1):
    if x is None:
        return None
    return round(x * 100.0, nd)


def order_check(data):
    pages = data.get('pages') or []
    present = set()
    rows = []
    for p in pages:
        s = p.get('section')
        if s in SECTIONS:
            present.add(s)
    order_issues = []
    if 'conclusion' in present:
        first_sec = None
        for p in sorted(pages, key=lambda x: num(x.get('no')) or 0):
            first_sec = p.get('section')
            break
        if first_sec != 'conclusion':
            order_issues.append('\u7b2c 1 \u9875\u4e0d\u662f\u7ed3\u8bba\u9875\uff08\u5f53\u524d\u4e3a %s\uff09\uff0c\u7ed3\u8bba\u5fc5\u987b\u5148\u884c'
                                % SEC_CN.get(first_sec, first_sec))
    else:
        order_issues.append('\u7f3a\u5c11\u7ed3\u8bba\u9875')
    if 'plan' in present:
        last_sec = None
        for p in sorted(pages, key=lambda x: num(x.get('no')) or 0):
            last_sec = p.get('section')
        if last_sec != 'plan':
            order_issues.append('\u6700\u540e\u4e00\u9875\u4e0d\u662f\u8ba1\u5212\u9875\uff08\u5f53\u524d\u4e3a %s\uff09'
                                % SEC_CN.get(last_sec, last_sec))
    for s in SECTIONS:
        if s not in present:
            order_issues.append('\u7f3a\u5c11\u300c%s\u300d\u6bb5' % SEC_CN[s])
    cov = round(len(present) * 100.0 / len(SECTIONS), 1)
    return present, cov, order_issues, rows


def page_quality(data):
    pages = data.get('pages') or []
    rows = []
    conc_ok = 0
    src_ok = 0
    num_ok = 0
    for p in pages:
        no = p.get('no')
        sec = SEC_CN.get(p.get('section'), p.get('section') or '')
        cs = bool(p.get('has_conclusion_sentence'))
        hn = bool(p.get('has_number'))
        hs = bool(p.get('has_source'))
        conc_ok += 1 if cs else 0
        num_ok += 1 if hn else 0
        src_ok += 1 if hs else 0
        rows.append({'no': no, 'section': sec, 'conclusion': cs,
                     'has_number': hn, 'has_source': hs,
                     'state': '\u5408\u683c' if (cs and hn and hs) else '\u5f85\u8865'})
    n = len(pages)
    conc_rate = round(conc_ok * 100.0 / n, 1) if n else 0.0
    num_rate = round(num_ok * 100.0 / n, 1) if n else 0.0
    src_rate = round(src_ok * 100.0 / n, 1) if n else 0.0
    return rows, conc_rate, num_rate, src_rate


def metric_check(data):
    ms = data.get('metrics') or []
    rows = []
    wsum = 0.0
    w = 0.0
    acc = 0.0
    quant_ok = 0
    no_baseline = []
    upside_down = []
    quadrant_bad = []
    for m in ms:
        name = m.get('name') or '\uff08\u672a\u547d\u540d\uff09'
        cur = num(m.get('current'))
        base = num(m.get('baseline'))
        prev = num(m.get('previous'))
        tgt = num(m.get('target'))
        d = m.get('direction') or 'up'
        wt = num(m.get('weight'))
        head = num(m.get('headcount'))

        if wt is None or wt < 0:
            wt = 0.0
        wsum += wt

        yoy = None
        if cur is not None and base not in (None, 0):
            yoy = (cur - base) / base
        mom = None
        if cur is not None and prev not in (None, 0):
            mom = (cur - prev) / prev
        ach = None
        if d == 'up':
            if cur is not None and tgt not in (None, 0):
                ach = cur / tgt
        else:
            if tgt is not None and cur not in (None, 0):
                ach = tgt / cur
        per = None
        if cur is not None and head not in (None, 0):
            per = cur / head

        has_quant = cur is not None
        if has_quant:
            quant_ok += 1
        if cur is not None and base is None:
            no_baseline.append(name)
        if d not in DIRECTIONS:
            upside_down.append(name)
        if ach is not None and yoy is not None:
            if yoy < 0 and ach >= 1.0:
                quadrant_bad.append(name)
            elif yoy > 0 and ach < 1.0:
                quadrant_bad.append(name)

        if ach is not None and wt > 0:
            acc += ach * wt
            w += wt

        rows.append({'name': name, 'unit': m.get('unit') or '',
                     'current': cur, 'baseline': base, 'previous': prev,
                     'target': tgt, 'direction': d, 'weight': wt,
                     'yoy': pct(yoy), 'mom': pct(mom), 'achieve': pct(ach),
                     'per_capita': round(per, 2) if per is not None else None,
                     'state': '\u8fbe\u6807' if (ach is not None and ach >= 1.0) else '\u672a\u8fbe\u6807'})
    n = len(ms)
    quant_rate = round(quant_ok * 100.0 / n, 1) if n else 0.0
    weighted = round(acc * 100.0, 1) if w > 0 else None
    return (rows, quant_rate, wsum, weighted, no_baseline,
            upside_down, quadrant_bad, n)


def ratio_check(data):
    pages = data.get('pages') or []
    minutes = num(data.get('minutes'))
    n = len(pages)
    if not minutes or not n:
        return {'state': '\u6570\u636e\u4e0d\u5168', 'sec_per_page': None, 'suggested': None,
                'note': ''}
    sec_per_page = round(minutes * 60.0 / n, 1)
    suggested = None
    for lo, hi, mid in PAGES_BY_MIN:
        if lo <= minutes < hi:
            suggested = mid
            break
    notes = []
    if sec_per_page > PAGE_SEC_MAX:
        notes.append('\u5e73\u5747\u6bcf\u9875 %.1f \u79d2\uff0c\u8d85\u8fc7 %d \u79d2\u4e0a\u9650\uff0c\u8003\u8651\u62c6\u9875\u6216\u5220\u51cf'
                     % (sec_per_page, PAGE_SEC_MAX))
    if suggested is not None and n > suggested * 1.3:
        notes.append('\u8bb2\u8ff0 %s \u5206\u949f\u7528 %d \u9875\u504f\u591a\uff0c\u5efa\u8bae\u538b\u5230 %d \u9875\u5de6\u53f3'
                     % (minutes, n, suggested))
    if suggested is not None and n < suggested * 0.7:
        notes.append('\u8bb2\u8ff0 %s \u5206\u949f\u53ea\u7528 %d \u9875\u504f\u5c11\uff0c\u53ef\u80fd\u8bb2\u4e0d\u6ee1\u6216\u4fe1\u606f\u5bc6\u5ea6\u8fc7\u9ad8'
                     % (minutes, n))
    return {'state': 'OK', 'sec_per_page': sec_per_page,
            'suggested': suggested, 'note': '\uff1b'.join(notes)}


def wording_check(data):
    wl = [w for w in (data.get('workload_wording') or [])]
    wl_hits = []
    for s in wl:
        for w in WORKLOAD:
            if w in s:
                wl_hits.append({'sentence': s, 'word': w})
                break
    bl = data.get('blame_sentences') or []
    bl_hits = []
    for s in bl:
        for w in BLAME:
            if w in s:
                bl_hits.append({'sentence': s, 'word': w})
                break
    return wl_hits, bl_hits


def build(data, fmt='md'):
    title = data.get('title') or '\u8ff0\u804c PPT \u4f53\u68c0'
    present, order_cov, order_issues, _ = order_check(data)
    pages, conc_rate, num_rate, src_rate = page_quality(data)
    (m_rows, quant_rate, wsum, weighted, no_baseline, bad_dir, quadrant,
     n_metric) = metric_check(data)
    ratio = ratio_check(data)
    wl_hits, bl_hits = wording_check(data)

    if fmt == 'json':
        return {'title': title, 'page_count': len(pages),
                'order_coverage': order_cov, 'order_issues': order_issues,
                'conclusion_rate': conc_rate, 'number_rate': num_rate,
                'source_rate': src_rate,
                'quant_rate': quant_rate, 'weight_sum': wsum,
                'weighted_achieve': weighted,
                'no_baseline': no_baseline, 'bad_direction': bad_dir,
                'quadrant_alert': quadrant,
                'metrics': m_rows, 'metric_count': n_metric,
                'ratio': ratio, 'workload_hits': wl_hits,
                'blame_hits': bl_hits}

    out = []
    out.append('# %s' % title)
    out.append('')
    out.append('- \u603b\u9875\u6570\uff1a%d' % len(pages))
    out.append('- \u9875\u5e8f\u5b8c\u6574\u7387\uff1a%.1f%%\uff08\u7ea2\u7ebf %.0f%%\uff09' % (order_cov, ORDER_RED))
    out.append('- \u7ed3\u8bba\u53e5\u8986\u76d6\u7387\uff1a%.1f%%\uff08\u7ea2\u7ebf %.0f%%\uff09' % (conc_rate, CONCL_RED))
    out.append('- \u7ed3\u8bba\u53e5\u542b\u6570\u6bd4\u4f8b\uff1a%.1f%%' % num_rate)
    out.append('- \u6570\u636e\u6709\u6765\u6e90\u6bd4\u4f8b\uff1a%.1f%%\uff08\u7ea2\u7ebf %.0f%%\uff09' % (src_rate, SOURCE_RED))
    out.append('- \u91cf\u5316\u8986\u76d6\u7387\uff1a%.1f%%\uff08\u7ea2\u7ebf %.0f%%\uff09' % (quant_rate, QUANT_RED))
    out.append('- \u6307\u6807\u6570\uff1a%d' % n_metric)
    out.append('- \u6743\u91cd\u5408\u8ba1\uff1a%s' % ('%.2f\uff08\u6b63\u5e38\uff09' % wsum
                                   if abs(wsum - 1.0) <= WEIGHT_TOL
                                   else '%.2f\uff08\u4e0d\u7b49\u4e8e 1\uff09' % wsum))
    out.append('- \u52a0\u6743\u8fbe\u6210\u7387\uff1a%s' % ('%.1f%%' % weighted if weighted is not None else '\u65e0\u6570\u636e'))
    out.append('- \u5e73\u5747\u6bcf\u9875\u8bb2\u8ff0\uff1a%s \u79d2' % ratio['sec_per_page'])
    out.append('- \u5806\u5de5\u4f5c\u91cf\u8868\u8ff0\uff1a%d \u5904' % len(wl_hits))
    out.append('- \u7591\u4f3c\u7529\u9505\u53e5\uff1a%d \u5904' % len(bl_hits))
    out.append('')
    out.append('## \u4e00\u3001\u9875\u5e8f\u4f53\u68c0')
    out.append('')
    if not order_issues:
        out.append('\u4e94\u6bb5\u9f50\u5168\u4e14\u7ed3\u8bba\u5728\u7b2c 1 \u9875\u3001\u8ba1\u5212\u5728\u6700\u540e\u4e00\u9875\u3002')
    else:
        for i, it in enumerate(order_issues, 1):
            out.append('%d. %s' % (i, it))
    out.append('')
    out.append('## \u4e8c\u3001\u9010\u9875\u8d28\u68c0')
    out.append('')
    out.append('| \u9875 | \u6bb5\u843d | \u7ed3\u8bba\u53e5 | \u542b\u6570 | \u6709\u6765\u6e90 | \u5224\u5b9a |')
    out.append('|---|---|---|---|---|---|')
    for r in pages:
        out.append('| %s | %s | %s | %s | %s | %s |' % (
            r['no'], r['section'], 'Y' if r['conclusion'] else '-',
            'Y' if r['has_number'] else '-', 'Y' if r['has_source'] else '-',
            r['state']))
    out.append('')
    out.append('## \u4e09\u3001\u91cf\u5316\u6838\u7b97')
    out.append('')
    out.append('| \u6307\u6807 | \u672c\u671f | \u540c\u6bd4 | \u73af\u6bd4 | \u76ee\u6807 | \u8fbe\u6210\u7387 | \u65b9\u5411 | \u4eba\u5747\u6548\u80fd | \u5224\u5b9a |')
    out.append('|---|---|---|---|---|---|---|---|---|')
    for r in m_rows:
        out.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            r['name'], r['current'],
            ('%.1f%%' % r['yoy']) if r['yoy'] is not None else '-',
            ('%.1f%%' % r['mom']) if r['mom'] is not None else '-',
            r['target'],
            ('%.1f%%' % r['achieve']) if r['achieve'] is not None else '\u65e0\u76ee\u6807',
            'up' if r['direction'] == 'up' else 'down',
            r['per_capita'] if r['per_capita'] is not None else '-',
            r['state']))
    if not m_rows:
        out.append('| \uff08\u672a\u586b\u6307\u6807\uff09 | - | - | - | - | - | - | - | - |')
    out.append('')
    if quadrant:
        out.append('\u56db\u8c61\u9650\u63d0\u793a\uff08\u540c\u6bd4\u4e0e\u8fbe\u6210\u7387\u65b9\u5411\u4e0d\u4e00\u81f4\uff0c\u9700\u4e3b\u52a8\u8bf4\u660e\uff09\uff1a%s' % '\u3001'.join(quadrant))
        out.append('')
    if no_baseline:
        out.append('\u7f3a\u4e0a\u5e74\u540c\u671f\u57fa\u7ebf\uff08\u65e0\u6cd5\u7b97\u540c\u6bd4\uff09\uff1a%s' % '\u3001'.join(no_baseline))
        out.append('')
    if bad_dir:
        out.append('\u65b9\u5411\u6807\u6ce8\u5f02\u5e38\uff1a%s' % '\u3001'.join(bad_dir))
        out.append('')
    out.append('## \u56db\u3001\u9875\u6570\u4e0e\u65f6\u957f')
    out.append('')
    if ratio['state'] != 'OK':
        out.append('%s\u3002' % ratio['note'])
    else:
        out.append('- \u5e73\u5747\u6bcf\u9875 %.1f \u79d2\uff08\u4e0a\u9650 %d \u79d2\uff09' % (ratio['sec_per_page'],
                                                  PAGE_SEC_MAX))
        if ratio['suggested']:
            out.append('- \u8bb2\u8ff0 %s \u5206\u949f\u5efa\u8bae\u9875\u6570\uff1a%d \u9875\u5de6\u53f3'
                       % (data.get('minutes'), ratio['suggested']))
        if ratio['note']:
            out.append('- \u63d0\u9192\uff1a%s' % ratio['note'])
    out.append('')
    out.append('## \u4e94\u3001\u8868\u8ff0\u95ee\u9898')
    out.append('')
    if not wl_hits and not bl_hits:
        out.append('\u672a\u547d\u4e2d\u5806\u5de5\u4f5c\u91cf\u4e0e\u7529\u9505\u53e5\u8bcd\u8868\u3002\u4ecd\u9700\u4eba\u5de5\u786e\u8ba4\u6bcf\u6761\u8868\u8ff0\u90fd\u5e26\u7ed3\u679c\u3002')
    else:
        out.append('| \u7c7b\u578b | \u547d\u4e2d\u8bcd | \u539f\u53e5 | \u6539\u6cd5 |')
        out.append('|---|---|---|---|')
        for h in wl_hits:
            out.append('| \u5806\u5de5\u4f5c\u91cf | %s | %s | \u6362\u6210\u300c\u505a\u4e86\u4ec0\u4e48 \u2192 \u53d8\u6210\u4ec0\u4e48\u300d |' % (h['word'], h['sentence']))
        for h in bl_hits:
            out.append('| \u7591\u4f3c\u7529\u9505 | %s | %s | \u7ed3\u8bba\u53e5\u4e3b\u8bed\u6539\u6210\u81ea\u5df1\u7684\u52a8\u4f5c |' % (h['word'], h['sentence']))
    out.append('')
    out.append('## \u516d\u3001\u6574\u6539\u5efa\u8bae')
    out.append('')
    idx = 0
    if order_issues:
        idx += 1
        out.append('%d. \u9875\u5e8f\u95ee\u9898 %d \u5904\uff1a\u7ed3\u8bba\u5fc5\u987b\u653e\u7b2c 1 \u9875\uff0c\u8ba1\u5212\u653e\u6700\u540e\u4e00\u9875\uff0c\u4e94\u6bb5\u4e0d\u80fd\u7f3a\u3002'
                   % (idx, len(order_issues)))
    if conc_rate < CONCL_RED:
        idx += 1
        out.append('%d. \u7ed3\u8bba\u53e5\u8986\u76d6\u7387 %.1f%% \u504f\u4f4e\uff1a\u6bcf\u9875\u6807\u9898\u5c31\u662f\u7ed3\u8bba\u53e5\uff0c\u4e0d\u53e6\u5199\u6807\u9898\u3002'
                   % (idx, conc_rate))
    if num_rate < CONCL_RED:
        idx += 1
        out.append('%d. \u7ed3\u8bba\u53e5\u542b\u6570\u6bd4\u4f8b %.1f%% \u504f\u4f4e\uff1a\u6bcf\u4e2a\u7ed3\u8bba\u53e5\u91cc\u8981\u6709\u4e00\u4e2a\u6570\u3002'
                   % (idx, num_rate))
    if src_rate < SOURCE_RED:
        idx += 1
        out.append('%d. \u6570\u636e\u6709\u6765\u6e90\u6bd4\u4f8b %.1f%% \u504f\u4f4e\uff1a\u6ce8\u660e\u7cfb\u7edf/\u53f0\u8d26/\u62bd\u6837\uff0c\u62bd\u6837\u5199\u6837\u672c\u91cf\u4e0e\u533a\u95f4\u3002'
                   % (idx, src_rate))
    if quant_rate < QUANT_RED:
        idx += 1
        out.append('%d. \u91cf\u5316\u8986\u76d6\u7387 %.1f%% \u504f\u4f4e\uff1a\u7b97\u4e0d\u51fa\u6570\u7684\u6307\u6807\u672c\u6765\u5c31\u4e0d\u8be5\u8fdb\u8ff0\u804c\u3002' % (idx, quant_rate))
    if n_metric and (n_metric < N_MIN or n_metric > N_BEST_HI):
        idx += 1
        out.append('%d. \u6307\u6807\u6570 %d \u6761\uff1a\u5efa\u8bae\u63a7\u5236\u5728 %d-%d \u6761\uff0c\u5b81\u6df1\u4e0d\u5bbd\u3002'
                   % (idx, n_metric, N_BEST_LO, N_BEST_HI))
    if abs(wsum - 1.0) > WEIGHT_TOL and wsum > 0:
        idx += 1
        out.append('%d. \u6743\u91cd\u5408\u8ba1 %.2f \u4e0d\u7b49\u4e8e 1\uff1a\u6309\u516c\u53f8\u8003\u6838\u53e3\u5f84\u6838\u5bf9\u6743\u91cd\u8868\u3002' % (idx, wsum))
    if quadrant:
        idx += 1
        out.append('%d. %d \u9879\u6307\u6807\u540c\u6bd4\u4e0e\u8fbe\u6210\u7387\u65b9\u5411\u4e0d\u4e00\u81f4\uff1a\u4e3b\u52a8\u8bf4\u660e\u76ee\u6807\u9ad8\u4f4e\uff0c'
                   '\u522b\u7b49\u8bc4\u59d4\u95ee\u51fa\u6765\u3002' % (idx, len(quadrant)))
    if no_baseline:
        idx += 1
        out.append('%d. %d \u9879\u6307\u6807\u7f3a\u4e0a\u5e74\u540c\u671f\u57fa\u7ebf\uff1a\u65e0\u6cd5\u7b97\u540c\u6bd4\u3002' % (idx, len(no_baseline)))
    if ratio['note']:
        idx += 1
        out.append('%d. %s' % (idx, ratio['note']))
    if wl_hits:
        idx += 1
        out.append('%d. \u5806\u5de5\u4f5c\u91cf\u8868\u8ff0 %d \u5904\uff1a\u6570\u91cf\u4e0d\u662f\u6210\u679c\uff0c\u6539\u6210\u300c\u505a\u4e86\u4ec0\u4e48 \u2192 \u53d8\u6210\u4ec0\u4e48\u300d\u3002'
                   % (idx, len(wl_hits)))
    if bl_hits:
        idx += 1
        out.append('%d. \u7591\u4f3c\u7529\u9505\u53e5 %d \u5904\uff1a\u7ed3\u8bba\u53e5\u4e3b\u8bed\u843d\u5728\u81ea\u5df1\u80fd\u6539\u7684\u52a8\u4f5c\u4e0a\u3002' % (idx, len(bl_hits)))
    if not idx:
        out.append('\u9875\u5e8f\u3001\u7ed3\u8bba\u53e5\u3001\u91cf\u5316\u4e0e\u8868\u8ff0\u5747\u672a\u53d1\u73b0\u660e\u663e\u95ee\u9898\u3002'
                   '\u5b9a\u7a3f\u524d\u4ea4\u76f4\u5c5e\u4e0a\u7ea7\u6838\u4e00\u904d\u6570\u5b57\u53e3\u5f84\uff0c\u5e76\u6309\u516c\u53f8\u62ab\u9732\u8981\u6c42\u8131\u654f\u3002')
    out.append('')
    return '\n'.join(out)


def selftest():
    ok = 0
    fails = []

    def chk(cond, name):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(name)

    def mk_pages(spec):
        out = []
        for i, (sec, cs, hn, hs) in enumerate(spec, 1):
            out.append({'no': i, 'section': sec, 'has_conclusion_sentence': cs,
                        'has_number': hn, 'has_source': hs})
        return out

    good_pages = mk_pages([
        ('conclusion', True, True, True),
        ('data', True, True, True),
        ('data', True, True, True),
        ('highlight', True, True, True),
        ('problem', True, True, True),
        ('plan', True, True, True),
    ])
    good_metrics = [
        {'name': '\u9500\u552e\u989d', 'unit': '\u4e07\u5143', 'current': 1200, 'baseline': 950,
         'previous': 1110, 'target': 1150, 'direction': 'up', 'weight': 0.4,
         'headcount': 12},
        {'name': '\u7ebf\u4e0a\u6545\u969c\u6b21\u6570', 'current': 18, 'baseline': 25, 'previous': 22,
         'target': 20, 'direction': 'down', 'weight': 0.3, 'headcount': 12},
        {'name': '\u4ea4\u4ed8\u5468\u671f', 'current': 15, 'baseline': 18, 'previous': 16,
         'target': 12, 'direction': 'down', 'weight': 0.3, 'headcount': 12},
    ]
    r = build({'pages': good_pages, 'metrics': good_metrics, 'minutes': 12},
              'json')
    chk(r['order_coverage'] == 100.0, '\u4e94\u6bb5\u9f50\u5168\u5b8c\u6574\u7387\u5e94\u4e3a 100')
    chk(r['order_issues'] == [], '\u89c4\u8303\u9875\u5e8f\u4e0d\u5e94\u6709\u95ee\u9898')
    chk(r['conclusion_rate'] == 100.0, '\u5168\u90e8\u6709\u7ed3\u8bba\u53e5\u5e94\u4e3a 100')
    chk(r['quant_rate'] == 100.0, '\u5168\u90e8\u6709\u6570\u503c\u5e94\u4e3a 100')
    chk(abs(r['weight_sum'] - 1.0) < 0.001, '\u6743\u91cd\u5408\u8ba1\u5e94\u4e3a 1')
    chk(abs(r['weighted_achieve'] - ((1200/1150*0.4) + (20/18*0.3) + (12/15*0.3))*100) < 0.5,
        '\u52a0\u6743\u8fbe\u6210\u7387\u5e94\u6309\u65b9\u5411\u516c\u5f0f\u6838\u7b97')
    chk(r['quadrant_alert'] == ['\u7ebf\u4e0a\u6545\u969c\u6b21\u6570'], 'yoy down but over 100 should alert')
    chk(r['no_baseline'] == [], '\u57fa\u7ebf\u9f50\u5168\u4e0d\u5e94\u63d0\u793a')
    chk(r['ratio']['sec_per_page'] == 120.0, '12 \u5206\u949f 6 \u9875\u5e94\u4e3a 120 \u79d2\u6bcf\u9875')

    up = build({'metrics': [good_metrics[0]]}, 'json')['metrics'][0]
    chk(up['yoy'] is not None and up['yoy'] > 26, '\u9500\u552e\u989d\u540c\u6bd4\u5e94\u7ea6 26%')
    chk(up['achieve'] is not None and abs(up['achieve'] - 104.3) < 0.3,
        '\u9500\u552e\u989d\u8fbe\u6210\u7387\u5e94\u7ea6 104%')
    dn = build({'metrics': [good_metrics[1]]}, 'json')['metrics'][0]
    chk(dn['achieve'] is not None and abs(dn['achieve'] - 111.1) < 0.3,
        '\u8d8a\u5c0f\u8d8a\u597d\u7c7b\u5e94\u6309\u76ee\u6807\u9664\u5b9e\u9645\u7b97\u51fa\u7ea6 111%')

    no_pg = build({'pages': [], 'metrics': []}, 'json')
    chk(no_pg['order_coverage'] == 0.0, '\u65e0\u9875\u9762\u5b8c\u6574\u7387\u4e3a 0')
    chk(no_pg['conclusion_rate'] == 0.0, '\u65e0\u9875\u9762\u7ed3\u8bba\u53e5\u8986\u76d6\u7387\u4e3a 0')
    chk(len(no_pg['order_issues']) >= 5, '\u65e0\u9875\u9762\u5e94\u62a5\u4e94\u6bb5\u7f3a\u5931')

    late_conc = mk_pages([
        ('data', True, True, True),
        ('highlight', True, True, True),
        ('problem', True, True, True),
        ('plan', True, True, True),
        ('conclusion', True, True, True),
    ])
    r = build({'pages': late_conc}, 'json')
    chk(any('\u7b2c 1 \u9875\u4e0d\u662f\u7ed3\u8bba\u9875' in i for i in r['order_issues']),
        '\u7ed3\u8bba\u4e0d\u5728\u9996\u5c4f\u5e94\u63d0\u793a')
    chk(any('\u6700\u540e\u4e00\u9875\u4e0d\u662f\u8ba1\u5212\u9875' in i for i in r['order_issues']),
        '\u8ba1\u5212\u4e0d\u5728\u672b\u9875\u5e94\u63d0\u793a')

    part = mk_pages([
        ('conclusion', True, True, True),
        ('data', True, True, True),
        ('data', False, True, False),
        ('highlight', True, True, True),
        ('problem', True, True, True),
        ('plan', True, True, True),
    ])
    r = build({'pages': part}, 'json')
    chk(abs(r['conclusion_rate'] - (100.0 * 5 / 6)) < 0.2, '5/6 \u6709\u7ed3\u8bba\u53e5\u7ea6 83%')
    chk(abs(r['source_rate'] - (100.0 * 5 / 6)) < 0.2, '5/6 \u6709\u6765\u6e90\u7ea6 83%')

    no_base = [{'name': 'A', 'current': 100, 'target': 90, 'direction': 'up',
                'weight': 1.0}]
    r = build({'metrics': no_base}, 'json')
    chk(r['no_baseline'] == ['A'], '\u7f3a\u57fa\u7ebf\u5e94\u63d0\u793a\u6307\u6807\u540d')
    chk(r['metrics'][0]['yoy'] is None, '\u7f3a\u57fa\u7ebf\u540c\u6bd4\u5e94\u4e3a None')

    bad_dir = [{'name': 'B', 'current': 100, 'target': 90, 'direction': 'flat',
                'weight': 1.0}]
    r = build({'metrics': bad_dir}, 'json')
    chk(r['bad_direction'] == ['B'], '\u975e\u6cd5\u65b9\u5411\u5e94\u63d0\u793a')

    quad = [{'name': 'C', 'current': 90, 'baseline': 100, 'target': 85,
             'direction': 'up', 'weight': 1.0}]
    r = build({'metrics': quad}, 'json')
    chk(r['quadrant_alert'] == ['C'], '\u540c\u6bd4\u8dcc\u4f46\u8fbe\u6807\u5e94\u63d0\u793a\u4e3b\u52a8\u8bf4\u660e')

    zero_base = [{'name': 'D', 'current': 100, 'baseline': 0, 'target': 90,
                  'direction': 'up', 'weight': 1.0}]
    r = build({'metrics': zero_base}, 'json')
    chk(r['metrics'][0]['yoy'] is None, '\u57fa\u7ebf\u4e3a 0 \u65f6\u540c\u6bd4\u5e94\u4e3a None \u800c\u975e\u62a5\u9519')

    zero_tgt = [{'name': 'E', 'current': 100, 'direction': 'up', 'weight': 1.0}]
    r = build({'metrics': zero_tgt}, 'json')
    chk(r['metrics'][0]['achieve'] is None, '\u7f3a\u76ee\u6807\u503c\u8fbe\u6210\u7387\u5e94\u4e3a None')

    per = [{'name': 'F', 'current': 1200, 'target': 1000, 'direction': 'up',
            'weight': 1.0, 'headcount': 0}]
    r = build({'metrics': per}, 'json')
    chk(r['metrics'][0]['per_capita'] is None, '\u4eba\u6570\u4e3a 0 \u65f6\u4eba\u5747\u6548\u80fd\u5e94\u4e3a None')

    slow = build({'pages': good_pages, 'minutes': 5}, 'json')
    chk(slow['ratio']['sec_per_page'] == 50.0, '5 \u5206\u949f 6 \u9875\u5e94\u4e3a 50 \u79d2\u6bcf\u9875')
    no_ratio = build({'pages': good_pages}, 'json')
    chk(no_ratio['ratio']['state'] == '\u6570\u636e\u4e0d\u5168', '\u7f3a\u65f6\u957f\u5e94\u5224\u6570\u636e\u4e0d\u5168')

    wl = {'workload_wording': ['\u672c\u5e74\u5ea6\u79ef\u6781\u53c2\u4e0e\u9879\u76ee\u5efa\u8bbe\uff0c\u8ba4\u771f\u8d1f\u8d23',
                               '\u9879\u76ee A \u6309\u671f\u4ea4\u4ed8\uff0c\u8fd4\u5de5\u7387\u4e0b\u964d 12%']}
    r = build(wl, 'json')
    chk(len(r['workload_hits']) == 1, '\u5806\u5de5\u4f5c\u91cf\u5e94\u53ea\u547d\u4e2d 1 \u5904')
    chk(r['workload_hits'][0]['word'] == '\u79ef\u6781\u53c2\u4e0e', '\u5e94\u547d\u4e2d\u79ef\u6781\u53c2\u4e0e')

    bl = {'blame_sentences': ['\u56e0\u4ea7\u54c1\u9700\u6c42\u9891\u7e41\u53d8\u66f4\uff0c\u5bfc\u81f4\u4e0a\u7ebf\u5ef6\u671f',
                              '\u9700\u6c42\u53d8\u66f4 3 \u6b21\u540e\u6211\u5f15\u5165\u8bc4\u5ba1\u673a\u5236']}
    r = build(bl, 'json')
    chk(len(r['blame_hits']) == 1, '\u7529\u9505\u53e5\u5e94\u53ea\u547d\u4e2d 1 \u5904')
    chk(r['blame_hits'][0]['word'] == '\u56e0\u4ea7\u54c1\u9700\u6c42', '\u5e94\u547d\u4e2d\u56e0\u4ea7\u54c1\u9700\u6c42')

    txt = build({'pages': good_pages, 'metrics': good_metrics,
                 'minutes': 12}, 'md')
    chk('\u9875\u5e8f\u4f53\u68c0' in txt, 'md \u5e94\u542b\u9875\u5e8f\u4f53\u68c0')
    chk('\u91cf\u5316\u6838\u7b97' in txt, 'md \u5e94\u542b\u91cf\u5316\u6838\u7b97')
    chk('\u6574\u6539\u5efa\u8bae' in txt, 'md \u5e94\u542b\u6574\u6539\u5efa\u8bae')

    if fails:
        lines = ['SELFTEST FAIL: %d/%d passed' % (ok, ok + len(fails))]
        for f in fails:
            lines.append('  - %s' % f)
        text = '\n'.join(lines)
    else:
        text = 'SELFTEST OK: %d assertions passed' % ok
    return text


def write_out(text, out):
    if not out:
        base = os.path.dirname(os.path.abspath(__file__))
        out = os.path.join(base, '_last_result.txt')
    d = os.path.dirname(os.path.abspath(out))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(text + '\n')
    return out


def main():
    ap = argparse.ArgumentParser(description='\u8ff0\u804c PPT \u7ed3\u6784\u4e0e\u91cf\u5316\u6838\u67e5')
    ap.add_argument('--file', help='\u8f93\u5165 JSON \u8def\u5f84')
    ap.add_argument('--text', help='\u76f4\u63a5\u7ed9 JSON \u5b57\u7b26\u4e32')
    ap.add_argument('--out', help='\u8f93\u51fa\u6587\u4ef6\u8def\u5f84')
    ap.add_argument('--format', choices=['md', 'json'], default='md')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    if a.selftest:
        res = selftest()
        write_out(res, os.path.join(here, '_selftest_result.txt'))
        print(res)
        return 0 if res.startswith('SELFTEST OK') else 1
    if not a.file and not a.text:
        ap.print_help()
        return 2
    data = load(a.text, a.file)
    if a.format == 'json':
        out = json.dumps(build(data, 'json'), ensure_ascii=False, indent=2)
    else:
        out = build(data, 'md')
    p = write_out(out, a.out)
    print('written: %s' % p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
