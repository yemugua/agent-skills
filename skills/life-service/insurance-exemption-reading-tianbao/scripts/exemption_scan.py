# -*- coding: utf-8 -*-
"""Insurance exclusion clause scanning and structuring helper.

Classifies exclusion clauses into seven categories by matching Chinese
keywords, summarises the quantitative terms, and lists the points that must
be confirmed with the insurer. It never decides whether a specific case is
covered.

Usage:
  python exemption_scan.py --file case.json [--out result.md] [--format json]
  python exemption_scan.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Chinese keywords are written as \\uXXXX escapes so the source stays ASCII.
K_GUJI = '\u65e2\u5f80'          # pre-existing
K_YOUYOU = '\u5df2\u6709'  # already has
K_JIBING = '\u75be\u75c5'  # illness
K_ZHENGZHUANG = '\u75c7\u72b6'                # symptom
K_TIJIAN = '\u4f53\u68c0'                # physical exam
K_YICHANG = '\u5f02\u5e38'                # abnormal
K_JIUZHEN = '\u5c31\u8bca'                # consultation
K_JILU = '\u8bb0\u5f55'                        # record
K_XIANTIAN = '\u5148\u5929'                # congenital
K_YICHUAN = '\u9057\u4f20'                # hereditary
K_JIAZU = '\u5bb6\u65cf'                        # family
K_TEDING_JIBING = '\u7279\u5b9a\u75be\u75c5'  # specific illness
K_ZHIDING_JIBING = '\u6307\u5b9a\u75be\u75c5'  # designated illness
K_XINGWEI = '\u884c\u4e3a'                # behaviour
K_WEIXIAN = '\u5371\u9669'                # danger
K_JIU = '\u9152'                                # alcohol
K_JIUJIA = '\u9152\u9a7e'                # drunk driving
K_SHIDUAN = '\u65f6\u6bb5'                # period
K_QIYUE = '\u671f\u95f4'                        # term
K_WEITONGYI = '\u672a\u7ea6\u5b9a'  # not agreed
K_FEITONGYI = '\u975e\u7ea6\u5b9a'  # not an agreed one
K_BUSHUYU = '\u4e0d\u5c5e\u4e8e'  # does not belong to
K_YUYUE_JIBING = '\u7ea6\u5b9a\u75be\u75c5'  # agreed illness
K_GUYI = '\u6545\u610f'                        # intentional
K_QIZHA = '\u6b5a\u8bc8'                        # fraud
K_FANZUI = '\u72af\u7f6a'                        # crime
K_JUJUE = '\u62d2\u7edd'                        # resist
K_QIANGZHI = '\u5f3a\u5236'                # compulsory
K_WEIAN = '\u672a\u6309\u7ea6'                # not as agreed
K_ZHONGDUAN = '\u4e2d\u65ad'                # interrupt
K_SHANZI = '\u64c5\u81ea'                        # without authorisation
K_ZIXING = '\u81ea\u884c'                        # by oneself
K_WEIJING = '\u672a\u7ecf'                        # without going through
K_JIUYI = '\u5c31\u533b'                        # seek treatment
K_ZHILIAO = '\u6cbb\u7597'                # treatment
K_CHUWU = '\u4e0d\u627f\u62c5'                # does not bear
K_ZEREN = '\u8d23\u4efb'                        # liability
K_CHUWAIRENZE = '\u9664\u5916\u8d23\u4efb'  # excluded liability

CATS = {
    'PREEXISTING': [K_GUJI, K_YOUYOU, K_JIBING, K_ZHENGZHUANG, K_TIJIAN,
                    K_YICHANG, K_JIUZHEN, K_JILU],
    'CONGENITAL': [K_XIANTIAN, K_YICHUAN, K_JIAZU],
    'SPECIFIC_ILLNESS': [K_TEDING_JIBING, K_ZHIDING_JIBING],
    'SPECIFIC_BEHAVIOUR': [K_XINGWEI, K_WEIXIAN, K_JIU, K_JIUJIA, K_SHIDUAN,
                           K_QIYUE],
    'NON_AGREED_CAUSE': [K_WEITONGYI, K_FEITONGYI, K_BUSHUYU, K_YUYUE_JIBING],
    'INTENTIONAL': [K_GUYI, K_QIZHA, K_FANZUI, K_JUJUE, K_QIANGZHI],
    'NOT_AS_AGREED_CARE': [K_WEIAN, K_ZHONGDUAN, K_SHANZI, K_ZIXING,
                           K_WEIJING, K_JIUYI, K_ZHILIAO],
}

CAT_LABELS = {
    'PREEXISTING': 'pre-existing condition category',
    'CONGENITAL': 'congenital and hereditary category',
    'SPECIFIC_ILLNESS': 'named specific illness category',
    'SPECIFIC_BEHAVIOUR': 'specific behaviour and time-window category',
    'NON_AGREED_CAUSE': 'cause outside the agreed scope category',
    'INTENTIONAL': 'intentional or fraudulent act category',
    'NOT_AS_AGREED_CARE': 'care not taken as agreed category',
}

PROFILE_TESTS = {
    'has_preexisting': (['PREEXISTING'],
                        'you reported a pre-existing condition; the '
                        'pre-existing category clauses matter most'),
    'family_history': (['CONGENITAL'],
                       'you reported a family history; the congenital and '
                       'hereditary category clauses matter most'),
    'high_job_risk': (['SPECIFIC_BEHAVIOUR', 'INTENTIONAL'],
                      'your work or activities carry higher risk; behaviour '
                      'and time-window clauses matter most'),
}


def money(x):
    return round(float(x) + 1e-9, 2)


def classify(text):
    hits = []
    for cat in sorted(CATS):
        found = [k for k in CATS[cat] if k in text]
        if found:
            hits.append((cat, found))
    return hits


def calc(data):
    clauses = data.get('clauses', []) or []
    quant = data.get('quantitative', {}) or {}
    riders = data.get('riders', []) or []
    endorsements = data.get('endorsements', []) or []
    profile = data.get('profile', {}) or {}

    rows = []
    classified = {c: [] for c in CATS}
    unclassified = []
    for i, c in enumerate(clauses):
        text = str(c.get('text', ''))
        if not text.strip():
            raise ValueError('clause %d has empty text' % (i + 1))
        page = c.get('page', '')
        hits = classify(text)
        cats = [h[0] for h in hits]
        for cname in cats:
            classified[cname].append(i + 1)
        if not cats:
            unclassified.append(i + 1)
        rows.append({
            'no': i + 1,
            'page': page,
            'text': text,
            'categories': cats,
            'matched_count': len(hits),
        })

    notes = []
    notes.append('Categories are a locating framework, NOT a decision rule. '
                 'Whether a specific case falls inside an exclusion is '
                 'decided on the contract wording by the insurer.')
    notes.append('Copy the clause text verbatim. Summarising drops the '
                 'qualifiers such as day counts, hospital lists, amount caps '
                 'and diagnostic standards, and those qualifiers decide the '
                 'outcome.')
    if unclassified:
        notes.append('Clauses not matched to any category: numbers %s. Read '
                     'them by hand; do NOT assume they are unimportant.'
                     % ', '.join(str(x) for x in unclassified))

    matched_profile = []
    for key, (cats, msg) in sorted(PROFILE_TESTS.items()):
        if profile.get(key):
            relevant = []
            for cname in cats:
                relevant.extend(classified.get(cname, []))
            matched_profile.append({'flag': key, 'clause_numbers': relevant,
                                    'note': msg})
            if not relevant:
                notes.append('Flag %s is set but no clause in the supplied '
                             'text falls into the matching categories. The '
                             'contract may simply not list them; confirm with '
                             'the insurer. Do NOT conclude that nothing '
                             'applies.' % key)

    # Quantitative terms.
    q = {
        'deductible': float(quant.get('deductible', 0) or 0),
        'deductible_rate': float(quant.get('deductible_rate', 0) or 0),
        'payout_ratio': float(quant.get('payout_ratio', 1.0)
                              if quant.get('payout_ratio') is not None else 1.0),
        'payout_cap': float(quant.get('payout_cap', 0) or 0),
        'waiting_days': int(quant.get('waiting_days', 0) or 0),
    }
    for k in ('deductible', 'deductible_rate', 'payout_ratio', 'payout_cap'):
        if q[k] < 0:
            raise ValueError('%s must be >= 0' % k)
    if q['waiting_days'] < 0:
        raise ValueError('waiting_days must be >= 0')
    if q['deductible_rate'] >= 1 or q['payout_ratio'] > 1:
        raise ValueError('deductible_rate must be < 1 and payout_ratio <= 1')

    base = float(data.get('assessed_amount', 0) or 0)
    if base < 0:
        raise ValueError('assessed_amount must be >= 0')
    rough = None
    if base > 0:
        after_rate = base * (1.0 - q['deductible_rate'])
        after_ratio = after_rate * q['payout_ratio']
        after_ded = after_rate * q['payout_ratio'] - q['deductible']
        rough = money(max(0.0, after_ded))
        if q['payout_cap'] > 0:
            rough = money(min(rough, q['payout_cap']))
        notes.append(
            'Rough order of payout: assessed amount %.2f, less deductible '
            'rate, times the payout ratio, less the deductible, capped at the '
            'payout cap, gives about %.2f. The real calculation order '
            'follows the contract wording.' % (base, rough))
        notes.append(
            'This rough figure is arithmetic only. It does NOT decide '
            'eligibility, and it does NOT mean the insurer will pay this '
            'amount.')

    if q['waiting_days'] > 0:
        notes.append(
            'Waiting period is %d days. Handling of an incident inside the '
            'waiting period follows the contract wording. Do NOT state that '
            'it is either payable or not payable.' % q['waiting_days'])
    if riders:
        notes.append('Riders supplied: %s. Check them together with the main '
                     'clause; a rider can change the scope of cover.'
                     % '; '.join(str(x) for x in riders))
    if endorsements:
        notes.append('Endorsements supplied: %s. An endorsement normally '
                     'takes priority over a general clause.'
                     % '; '.join(str(x) for x in endorsements))
    else:
        notes.append('No endorsement was supplied. Confirm whether one '
                     'exists, because it may change the terms.')

    notes.append('An exclusion clause being met does NOT automatically mean '
                 'a refusal. It is the insurer that decides, and a disputed '
                 'exclusion can go to a court.')
    notes.append('Non-disclosure is a different mechanism from an exclusion: '
                 'one is about what was said at application time, the other '
                 'is about what the contract says. Do NOT mix them up.')
    notes.append('For a disputed format clause, the courts may interpret it '
                 'against the party that supplied it, but that applies only '
                 'when two or more readings are possible, and the outcome is '
                 'decided by the court, not by either party.')
    notes.append('This script classifies and summarises only. It gives no '
                 'opinion on whether a claim will be paid and promises no '
                 'claim outcome.')

    return {
        'clause_count': len(rows),
        'rows': rows,
        'category_counts': {c: len(v) for c, v in sorted(classified.items())},
        'category_labels': CAT_LABELS,
        'unclassified_numbers': unclassified,
        'profile_flags': matched_profile,
        'quantitative': q,
        'rough_payout': rough,
        'riders': [str(x) for x in riders],
        'endorsements': [str(x) for x in endorsements],
        'notes': notes,
        'must_confirm': [
            'complete contract text including riders, endorsements and any '
            'endorsement sheet, not only the first page',
            'every exclusion clause located with chapter name and page number',
            'every clause copied verbatim, never summarised',
            'qualifiers recorded: time window, count, amount, hospital list, '
            'diagnostic standard',
            'exclusion clauses cross-checked against the benefit clauses',
            'deductible, deductible rate, payout ratio, payout cap and '
            'waiting days written down as actual numbers',
            'hospital list, drug scope and diagnostic standard checked',
            'riders, endorsements and the health questionnaire checked, not '
            'the main clause alone',
            'who wrote what on the health questionnaire, compared against '
            'medical records',
            'sales conversation records kept together with the contract',
        ],
        'dispute_path': [
            'send a written review request to the insurer and keep the record',
            'check the clause text and quantitative terms cited in the '
            'refusal notice',
            'use the formal complaint channel and mediation if the review '
            'fails',
            'consult a lawyer for a large dispute or anything already in court',
            'interpretation of a disputed format clause is decided by a court',
        ],
    }


def to_md(r):
    L = []
    L.append('# Insurance Exclusion Clause Check')
    L.append('')
    L.append('- Clause count: %d' % r['clause_count'])
    L.append('- Riders: %s' % (', '.join(r['riders']) or 'none supplied'))
    L.append('- Endorsements: %s' % (', '.join(r['endorsements']) or 'none supplied'))
    L.append('')
    L.append('## Clauses by location')
    L.append('')
    L.append('| No | Page | Categories matched | Text |')
    L.append('|---|---|---|---|')
    for row in r['rows']:
        L.append('| %d | %s | %s | %s |'
                 % (row['no'], row['page'],
                    ', '.join(CAT_LABELS.get(c, c) for c in row['categories'])
                    or 'UNCLASSIFIED', row['text']))
    L.append('')
    L.append('## Category counts')
    L.append('')
    L.append('| Category | Clauses |')
    L.append('|---|---|')
    for c, n in r['category_counts'].items():
        L.append('| %s | %d |' % (CAT_LABELS.get(c, c), n))
    L.append('')
    L.append('- Unclassified clause numbers: %s'
             % (', '.join(str(x) for x in r['unclassified_numbers']) or 'none'))
    L.append('')
    if r['profile_flags']:
        L.append('## Flags relevant to the applicant')
        L.append('')
        for f in r['profile_flags']:
            L.append('- %s: clauses %s. %s'
                     % (f['flag'],
                        ', '.join(str(x) for x in f['clause_numbers']) or 'none',
                        f['note']))
        L.append('')
    L.append('## Quantitative terms')
    L.append('')
    L.append('| Term | Value |')
    L.append('|---|---|')
    L.append('| Deductible | %.2f |' % r['quantitative']['deductible'])
    L.append('| Deductible rate | %.4f |'
             % r['quantitative']['deductible_rate'])
    L.append('| Payout ratio | %.4f |' % r['quantitative']['payout_ratio'])
    L.append('| Payout cap | %.2f |' % r['quantitative']['payout_cap'])
    L.append('| Waiting days | %d |' % r['quantitative']['waiting_days'])
    L.append('')
    L.append('- Rough payout: %s'
             % ('%.2f' % r['rough_payout']
                if r['rough_payout'] is not None else 'N/A'))
    L.append('')
    L.append('## Notes')
    L.append('')
    for n in r['notes']:
        L.append('- %s' % n)
    L.append('')
    L.append('## Must be confirmed against the contract')
    L.append('')
    for m in r['must_confirm']:
        L.append('- [ ] %s' % m)
    L.append('')
    L.append('## Dispute path')
    L.append('')
    for s in r['dispute_path']:
        L.append('1. %s' % s)
    L.append('')
    L.append('Exclusions, deductibles, payout ratios, caps and waiting periods '
             'follow the insurance contract. Whether a specific case is '
             'covered is decided by the insurer on the contract wording. '
             'Interpretation of a disputed format clause follows the law and '
             'the courts in force. This script gives no opinion on any claim '
             'and promises no claim outcome.')
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

    GJ = K_GUJI          # pre-existing
    XT = K_XIANTIAN      # congenital
    YC = K_YICHUAN       # hereditary
    GY = K_GUYI          # intentional
    XW = K_XINGWEI       # behaviour
    SZ = K_SHIDUAN       # period

    clauses = [
        {'text': '\u6295\u4fdd\u524d' + GJ + '\u5df2\u6709\u7684'
                 + K_JIBING + '\u6216' + K_ZHENGZHUANG
                 + '\uff0c\u672c\u516c\u53f8' + K_CHUWU
                 + '\u7ed9\u4ed8\u8d23\u4efb', 'page': 12},
        {'text': XT + '\u6027\u3001' + YC + K_CHUWU
                 + K_YUYUE_JIBING + '\u8303\u56f4\u5185', 'page': 12},
        {'text': '\u88ab\u4fdd\u9669\u4eba' + GJ + SZ
                 + '\u5185\u786e\u8bca\u7684\uff0c\u672c\u516c\u53f8'
                 + K_CHUWU + K_ZEREN, 'page': 12},
        {'text': '\u88ab\u4fdd\u9669\u4eba' + GY + K_FANZUI
                 + '\u6216' + K_JUJUE + K_QIANGZHI + K_ZEREN
                 + '\u81f4\u6b7b\u7684\uff0c\u672c\u516c\u53f8'
                 + K_CHUWU + K_ZEREN, 'page': 13},
        {'text': '\u4e00\u822c\u81ea\u4e3b\u884c\u4e3a\u9020\u6210\u7684'
                 + K_WEIXIAN + '\u4e0d' + K_YUYUE_JIBING
                 + '\u7684\uff0c\u5f02\u5e38', 'page': 13},
    ]

    # 1: category detection, Chinese keyword matching works
    r = calc({'clauses': clauses})
    check(r['clause_count'] == 5, 'all five clauses must be read')
    cc = r['category_counts']
    check(cc['PREEXISTING'] >= 2, 'pre-existing clauses should be found, got %d'
          % cc['PREEXISTING'])
    check(cc['CONGENITAL'] == 1, 'congenital clause should be found once')
    check(cc['INTENTIONAL'] == 1, 'intentional clause should be found once')
    check(any('UNCLASSIFIED' not in r['rows'][i]['categories']
              for i in range(5)),
          'every sample clause should match at least one category')

    # 2: framework disclaimer always present
    joined = ' '.join(r['notes'])
    check('NOT a decision rule' in joined,
          'the framework must be flagged as not a decision rule')
    check('decided on the contract wording by the insurer' in joined,
          'the decision holder must be named')
    check('Copies the clause text verbatim' in joined
          or 'Copy the clause text verbatim' in joined,
          'the verbatim-copy rule must be stated')

    # 3: unclassified clauses are listed, not silently dropped
    r2 = calc({'clauses': [{'text': '\u4e00\u4e2a\u6cd5\u901a\u7528\u8868\u8ff0',
                            'page': 20}]})
    check(r2['unclassified_numbers'] == [1],
          'an unmatched clause must be listed, got %s'
          % r2['unclassified_numbers'])
    check(any('do NOT assume they are unimportant' in n for n in r2['notes']),
          'unmatched clauses must be flagged as still needing manual reading')

    # 4: profile flags
    r3 = calc({'clauses': clauses,
               'profile': {'has_preexisting': True}})
    check(len(r3['profile_flags']) == 1,
          'one profile flag expected, got %d' % len(r3['profile_flags']))
    check(r3['profile_flags'][0]['clause_numbers'],
          'pre-existing flag must point at concrete clauses')
    r4 = calc({'clauses': [], 'profile': {'has_preexisting': True}})
    check(any('Do NOT conclude that nothing applies' in n for n in r4['notes']),
          'a flag with no matching clause must not be read as no exclusion')

    # 5: rough payout arithmetic
    r5 = calc({'clauses': clauses,
               'quantitative': {'deductible': 10000, 'deductible_rate': 0.0,
                                'payout_ratio': 0.8, 'payout_cap': 500000,
                                'waiting_days': 90},
               'assessed_amount': 200000})
    # 200000 * 1.0 * 0.8 - 10000 = 150000, below the cap
    check(abs(r5['rough_payout'] - 150000.0) < 0.01,
          'rough payout should be 150000, got %s' % r5['rough_payout'])
    r6 = calc({'clauses': [],
               'quantitative': {'deductible': 0, 'payout_ratio': 1.0,
                                'payout_cap': 100000},
               'assessed_amount': 200000})
    check(abs(r6['rough_payout'] - 100000.0) < 0.01,
          'the payout cap must bind, got %s' % r6['rough_payout'])
    r7 = calc({'clauses': [], 'quantitative': {'deductible': 500000},
               'assessed_amount': 100000})
    check(r7['rough_payout'] == 0.0,
          'a deductible larger than the amount must clamp at zero')

    # 6: rough payout never decides eligibility
    r8 = calc({'clauses': clauses, 'assessed_amount': 200000})
    check(any('does NOT decide eligibility' in n for n in r8['notes']),
          'the rough figure must not be presented as a decision')
    check(r8['rough_payout'] is not None,
          'the rough figure must still be produced')

    # 7: no assessed amount -> no figure, no fabrication
    r9 = calc({'clauses': clauses})
    check(r9['rough_payout'] is None,
          'without an assessed amount no payout figure may be produced')

    # 8: waiting period wording guard
    check(any('Do NOT state that it is either payable or not payable' in n
              for n in r5['notes']),
          'waiting-period cases must not be resolved by the script')

    # 9: endorsement absence is flagged
    r10 = calc({'clauses': clauses})
    check(any('No endorsement was supplied' in n for n in r10['notes']),
          'a missing endorsement must be flagged')
    r11 = calc({'clauses': [], 'endorsements': ['X'],
                'riders': ['Y']})
    check(any('takes priority over a general clause' in n for n in r11['notes']),
          'endorsement priority must be stated')
    check(any('a rider can change the scope of cover' in n for n in r11['notes']),
          'riders must be flagged as changing scope')

    # 10: exclusion vs non-disclosure must be distinguished
    check(any('different mechanism from an exclusion' in n for n in r['notes']),
          'exclusion and non-disclosure must be distinguished')

    # 11: format clause guard
    check(any('two or more readings are possible' in n for n in r['notes']),
          'the two-readings precondition must be stated')
    check(any('decided by the court, not by either party' in n
              for n in r['notes']),
          'the court must be named as the decision holder')
    low = joined.lower()
    check('clause is invalid' not in low, 'no blanket invalidity claim')

    # 12: no claim guarantee
    check(any('promises no claim outcome' in n for n in r['notes']),
          'the no-guarantee statement must be present')
    check('guaranteed payout' not in low, 'no payout guarantee may appear')

    # 13: bad inputs rejected
    for bad in ({'clauses': [{'text': '   '}]},
                {'clauses': clauses, 'assessed_amount': -1},
                {'clauses': clauses,
                 'quantitative': {'deductible_rate': 1.5}},
                {'clauses': clauses, 'quantitative': {'payout_ratio': 2}},
                {'clauses': clauses, 'quantitative': {'deductible': -1}},
                {'clauses': clauses, 'quantitative': {'waiting_days': -1}}):
        try:
            calc(bad)
            check(False, 'bad input must be rejected: %s' % bad)
        except ValueError:
            check(True, 'bad input rejected')

    # 14: empty clause list is allowed and handled
    r12 = calc({'clauses': []})
    check(r12['clause_count'] == 0 and r12['rows'] == [],
          'an empty clause list must not crash')

    # 15: markdown rendering
    md = to_md(calc({'clauses': clauses,
                     'quantitative': {'deductible': 1000, 'waiting_days': 90},
                     'assessed_amount': 100000, 'riders': ['R'],
                     'endorsements': ['E']}))
    check('Category counts' in md and 'Dispute path' in md
          and 'Must be confirmed against the contract' in md,
          'markdown output must carry categories, dispute path and checklist')

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
