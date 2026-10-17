#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Metric dictionary completeness and naming auditor.

Checks required fields, naming convention, formula self-consistency,
duplicate detection and deprecation completeness, then grades findings as
ERROR / WARN / INFO.

Usage
  python metric_dict_check.py --file metrics.csv
  python metric_dict_check.py --file metrics.csv --check-naming --check-duplicates
  python metric_dict_check.py --file metrics.csv --check-deprecated
  python metric_dict_check.py --selftest

CSV header
  metric_id,metric_name,name_en,business_def,formula,dimensions,time_window,
  source,biz_owner,data_owner,freq,change_log,status,replacement,notify_date
"""
import argparse
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RESULT = os.path.join(HERE, '_selftest_result.txt')

REQUIRED = ('metric_id', 'metric_name', 'business_def', 'formula',
            'dimensions', 'time_window', 'source', 'biz_owner',
            'data_owner', 'freq', 'change_log', 'status')

# naming: domain_object_action[_modifier]_period
NAME_RE = re.compile(r'^[a-z][a-z0-9]*(_[a-z0-9]+){2,}$')
RATIO_HINT = ('ratio', 'rate', 'pct', 'percent')
RATIO_TOKENS = ('ratio', 'rate')
COUNT_HINTS = ('cnt', 'count', 'num')
TIME_TOKENS = ('1d', '7d', '30d', 'mtd', 'ytd', 'lifetime', 'lifetime')
DEPT_HINT = ('dept', 'team', 'department', 'bu', 'group_dept', 'division')
ORG_HINT = ('business', 'product', 'tech', 'data', 'ops', 'growth')

R_NAMING = 'name does not follow domain_object_action_period'
R_NO_DOMAIN = 'name is missing a business-domain prefix'
R_RATIO_MARK = 'ratio metric: name should contain ratio or rate'
R_TIME_MARK = 'name is missing the time period token'
R_ORG_LIKE = 'name looks like an org/dept name, not a metric'
R_DUP_ID = 'duplicate metric_id'
R_NO_NUM_DEN = 'ratio metric: formula must state numerator and denominator'
R_NO_TIME = 'formula does not reference any time boundary'
R_OWNER_DEPT = 'owner is written as a department, not a person or role'
R_NO_CHANGE_LOG = 'no change-log entry: cannot tell whether history was recomputed'
R_DEP_NO_REPL = 'deprecated metric must point to a replacement metric'
R_DEP_NO_NOTIFY = 'deprecated metric must record a notify date'
R_DEP_STILL_OK = 'deprecated metric still has blank replacement or notify date'
R_STATUS_BAD = 'status must be active or deprecated'
R_NO_SCENARIO = 'business_def does not state what question the metric answers'

# business-def markers meaning "answers a question" (ASCII words allowed)
SCENARIO_HINT = ('answer', 'question', 'used to', 'purpose', 'for',
                 'measure', 'track', 'monitor', 'evaluate')


def read_rows(path):
    if path == '-':
        data = sys.stdin.read()
    else:
        with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
            data = fh.read()
    return [dict(r) for r in csv.DictReader(io.StringIO(data))]


def g(row, key):
    return (row.get(key) or '').strip()


def is_ratio(row):
    name = g(row, 'name_en').lower()
    if any(t in name for t in RATIO_TOKENS):
        return True
    if name.endswith('pct'):
        return True
    if any(h in g(row, 'metric_name').lower() for h in RATIO_HINT):
        return True
    return False


def audit(rows, check_naming=False, check_duplicates=False,
          check_deprecated=False):
    findings = []
    seen_ids = {}
    seen_pairs = {}
    for idx, row in enumerate(rows, 1):
        mid = g(row, 'metric_id')
        name = g(row, 'metric_name')
        label = mid or name or ('#%d' % idx)
        if not mid:
            findings.append(('ERROR', label, 'missing metric_id'))
        else:
            if mid in seen_ids:
                findings.append(('ERROR', label,
                                 '%s (also row #%d)' % (R_DUP_ID,
                                                         seen_ids[mid])))
            else:
                seen_ids[mid] = idx
        for field in REQUIRED:
            if field == 'metric_id':
                continue
            if not g(row, field):
                findings.append(('ERROR', label, 'missing %s' % field))
        status = g(row, 'status').lower()
        if status and status not in ('active', 'deprecated'):
            findings.append(('ERROR', label, '%s: %r' % (R_STATUS_BAD,
                                                         status)))
        formula = g(row, 'formula')
        ratio = is_ratio(row)
        if ratio and formula:
            if not re.search(r'\b(numerator|denominator|molecule|denom)\b',
                             formula, re.I):
                findings.append(('ERROR', label, R_NO_NUM_DEN))
        if formula and not re.search(r'\b(20\d\d|stat_date|>=|<|between|between)\b',
                                     formula, re.I):
            findings.append(('WARN', label, R_NO_TIME))
        for owner_key in ('biz_owner', 'data_owner'):
            owner = g(row, owner_key)
            if owner and re.search(r'\b(%s)\b' % '|'.join(DEPT_HINT), owner,
                                   re.I):
                findings.append(('WARN', label,
                                 '%s (%s=%s)' % (R_OWNER_DEPT, owner_key,
                                                 owner)))
        bdef = g(row, 'business_def').lower()
        if bdef and not any(h in bdef for h in SCENARIO_HINT):
            findings.append(('INFO', label, R_NO_SCENARIO))
        if not g(row, 'change_log'):
            findings.append(('WARN', label, R_NO_CHANGE_LOG))
        name_en = g(row, 'name_en').lower()
        if check_naming and name_en:
            parts = name_en.split('_')
            if len(parts) < 3:
                findings.append(('WARN', label,
                                 '%s (%s)' % (R_NAMING, name_en)))
            elif not NAME_RE.match(name_en):
                findings.append(('WARN', label,
                                 '%s (%s)' % (R_NAMING, name_en)))
            else:
                if any(org in parts[0] for org in ORG_HINT):
                    findings.append(('WARN', label, R_ORG_LIKE))
                if ratio and not any(t in name_en for t in RATIO_TOKENS):
                    findings.append(('WARN', label, R_RATIO_MARK))
                if not any(t in parts[-1] for t in TIME_TOKENS):
                    findings.append(('WARN', label,
                                     '%s (%s)' % (R_TIME_MARK, parts[-1])))
        if check_duplicates:
            pair = (name.lower(), g(row, 'formula').lower()[:60])
            if name:
                if pair in seen_pairs:
                    findings.append(('WARN', label,
                                     'duplicate name+formula (also #%d)'
                                     % seen_pairs[pair]))
                else:
                    seen_pairs[pair] = idx
        if check_deprecated and status == 'deprecated':
            if not g(row, 'replacement') or not g(row, 'notify_date'):
                findings.append(('ERROR', label, R_DEP_STILL_OK))
    names = {}
    for row in rows:
        n = g(row, 'metric_name')
        if n:
            names.setdefault(n, []).append(g(row, 'metric_id'))
    for n, ids in names.items():
        if len(ids) > 1:
            findings.append(('ERROR', n,
                             'same metric_name used by %d ids: %s'
                             % (len(ids), ', '.join(ids))))
    return findings


def render(rows, findings, lines):
    lines.append('== METRIC DICTIONARY AUDIT ==')
    lines.append('entries: %d' % len(rows))
    grouped = {}
    for level, who, msg in findings:
        grouped.setdefault(level, []).append((who, msg))
    for level in ('ERROR', 'WARN', 'INFO'):
        items = grouped.get(level, [])
        lines.append('')
        lines.append('[%s] %d' % (level, len(items)))
        for who, msg in items:
            lines.append('  %s: %s' % (who, msg))
    err = len(grouped.get('ERROR', []))
    lines.append('')
    if err:
        lines.append('VERDICT: NOT READY FOR RELEASE (errors=%d)' % err)
    else:
        lines.append('VERDICT: READY (errors=0, warns=%d)'
                     % len(grouped.get('WARN', [])))


def good_rows():
    base = {
        'metric_id': 'trade_order_paid_cnt_1d',
        'metric_name': 'Paid order count (day)',
        'name_en': 'trade_order_paid_cnt_1d',
        'business_def': 'used to answer how many paid orders happen per day',
        'formula': ("COUNT(DISTINCT order_id) WHERE pay_status='PAID' "
                    "AND stat_date = '2026-09-01'"),
        'dimensions': 'channel, terminal, new_old_user',
        'time_window': 'natural day 00:00-24:00 Asia/Shanghai',
        'source': 'dwd.order_detail',
        'biz_owner': 'trade product owner',
        'data_owner': 'trade data steward',
        'freq': 'T+1, ready by 09:00',
        'change_log': 'v1.0 2025-01-01 initial',
        'status': 'active',
        'replacement': '',
        'notify_date': '',
    }
    rows = [dict(base)]
    r2 = dict(base)
    r2.update({'metric_id': 'trade_order_paid_ratio_1d',
               'metric_name': 'Paid order ratio (day)',
               'name_en': 'trade_order_paid_ratio_1d',
               'formula': ('numerator / denominator; numerator = paid orders, '
                           'denominator = checkout page uv, stat_date >= start'),
               'change_log': 'v1.0 2025-01-01 initial'})
    r2.pop('replacement', None)
    rows.append(r2)
    r3 = dict(base)
    r3.update({'metric_id': 'user_active_device_dau_1d',
               'metric_name': 'Daily active devices',
               'name_en': 'user_active_device_dau_1d',
               'formula': "COUNT(DISTINCT device_id) WHERE stat_date = '2026-09-01'",
               'change_log': 'v2.0 2026-03-15 excluded internal devices; '
                             'history recomputed from 2025-01-01'})
    rows.append(r3)
    return rows


def selftest():
    checks = []

    def ck(name, cond, info=''):
        checks.append((name, bool(cond), info))

    rows = good_rows()

    # 1 clean dictionary
    f = audit(rows, True, True, True)
    errs = [x for x in f if x[0] == 'ERROR']
    ck('clean dict has no errors', not errs, str([x[2] for x in errs][:2]))

    # 2 no naming warnings
    nwarn = [x for x in f if x[0] == 'WARN' and 'name does not follow' in x[2]]
    ck('naming follows convention', not nwarn, str(len(nwarn)))

    # 3 ratio metric needs num/den
    bad = [dict(r) for r in rows]
    bad[1] = dict(bad[1], formula="ratio of paid orders to visits")
    f2 = audit(bad, True, True, True)
    ck('ratio without numerator/denominator errors',
       any(x[0] == 'ERROR' and 'numerator' in x[2] for x in f2))

    # 4 duplicate metric_id errors
    bad = [dict(r) for r in rows] + [dict(rows[0])]
    f3 = audit(bad)
    ck('duplicate metric_id errors',
       any(x[0] == 'ERROR' and 'duplicate metric_id' in x[2] for x in f3))

    # 5 duplicate metric_name across ids errors
    bad = [dict(r) for r in rows]
    bad[1] = dict(bad[1], metric_name=rows[0]['metric_name'])
    f4 = audit(bad)
    ck('same metric_name on two ids errors',
       any(x[0] == 'ERROR' and 'same metric_name' in x[2] for x in f4))

    # 6 missing required field errors
    bad = [dict(r) for r in rows]
    bad[0] = dict(bad[0], time_window='')
    f5 = audit(bad)
    ck('missing time_window errors',
       any(x[0] == 'ERROR' and 'missing time_window' in x[2] for x in f5))

    # 7 change log missing warns
    bad = [dict(r) for r in rows]
    bad[0] = dict(bad[0], change_log='')
    f6 = audit(bad)
    ck('missing change_log warns',
       any(x[0] == 'WARN' and 'change-log' in x[2] for x in f6))

    # 8 deprecated without replacement errors
    bad = [dict(r) for r in rows]
    bad[0] = dict(bad[0], status='deprecated')
    f7 = audit(bad, False, False, True)
    ck('deprecated without replacement errors',
       any(x[0] == 'ERROR' and 'replacement' in x[2] for x in f7))

    # 9 deprecated complete is fine
    bad = [dict(r) for r in rows]
    bad[0] = dict(bad[0], status='deprecated',
                  replacement='trade_order_valid_cnt_1d',
                  notify_date='2026-05-20')
    f8 = audit(bad, False, False, True)
    ck('fully deprecated entry is clean',
       not any(x[0] == 'ERROR' for x in f8))

    # 10 bad status errors
    bad = [dict(r) for r in rows]
    bad[0] = dict(bad[0], status='retired')
    f9 = audit(bad)
    ck('bad status errors',
       any(x[0] == 'ERROR' and 'status must be' in x[2] for x in f9))

    # 11 owner written as a department warns
    bad = [dict(r) for r in rows]
    bad[0] = dict(bad[0], biz_owner='growth dept')
    f10 = audit(bad)
    ck('department owner warns',
       any(x[0] == 'WARN' and 'department' in x[2] for x in f10))

    # 12 ratio naming must contain ratio token
    bad = [dict(r) for r in rows]
    bad[1] = dict(bad[1], name_en='trade_order_paid_cnt_1d')
    f11 = audit(bad, True, False, False)
    ck('ratio name missing token warns',
       any(x[0] == 'WARN' and 'ratio or rate' in x[2] for x in f11))

    # 13 time period token missing warns
    bad = [dict(r) for r in rows]
    bad[0] = dict(bad[0], name_en='trade_order_paid_cnt')
    f12 = audit(bad, True, False, False)
    ck('missing period token warns',
       any(x[0] == 'WARN' and 'time period' in x[2] for x in f12))

    # 14 business_def without a purpose sentence gives INFO
    bad = [dict(r) for r in rows]
    bad[0] = dict(bad[0], business_def='a number computed every day')
    f13 = audit(bad)
    ck('purpose-less business_def gives INFO',
       any(x[0] == 'INFO' and 'what question' in x[2] for x in f13))

    # 15 formula without a time boundary warns
    bad = [dict(r) for r in rows]
    bad[0] = dict(bad[0], formula='SUM(amount)')
    f14 = audit(bad)
    ck('formula without time boundary warns',
       any(x[0] == 'WARN' and 'time boundary' in x[2] for x in f14))

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


def build_parser():
    p = argparse.ArgumentParser(
        description='Metric dictionary completeness auditor')
    p.add_argument('--file', type=str, default=None,
                   help='CSV metric dictionary, or - for stdin')
    p.add_argument('--check-naming', dest='check_naming', action='store_true')
    p.add_argument('--check-duplicates', dest='check_duplicates',
                   action='store_true')
    p.add_argument('--check-deprecated', dest='check_deprecated',
                   action='store_true')
    p.add_argument('--out', type=str, default=None)
    p.add_argument('--selftest', action='store_true')
    return p


def main():
    args = build_parser().parse_args()
    if args.selftest:
        return selftest()
    if not args.file:
        text = '[ERROR] --file is required (use - for stdin)\n'
        with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(text)
        return 2
    try:
        rows = read_rows(args.file)
    except Exception as exc:
        text = '[ERROR] cannot read %s: %s\n' % (args.file, exc)
        with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(text)
        return 2
    findings = audit(rows, args.check_naming, args.check_duplicates,
                     args.check_deprecated)
    lines = []
    render(rows, findings, lines)
    text = '\n'.join(lines) + '\n'
    path = args.out or RESULT
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    print(text)
    print('written: %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())