#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Event tracking plan auditor.

Checks a tracking list for required elements, naming convention, reporting
timing sanity, dedup rules and priority coverage, then grades findings as
ERROR / WARN / INFO.

Usage
  python tracking_check.py --file events.csv
  python tracking_check.py --file events.csv --check-naming --check-timing
  python tracking_check.py --file events.csv --check-dedup
  python tracking_check.py --selftest

CSV header (required: event, trigger)
  event,trigger,report_timing,properties,priority,dedup_rule,owner,platform
"""
import argparse
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RESULT = os.path.join(HERE, '_selftest_result.txt')

REQUIRED = ('event', 'trigger', 'report_timing', 'properties', 'priority',
            'dedup_rule')

NAME_RE = re.compile(r'^[a-z][a-z0-9]*(_[a-z0-9]+){2,}$')
PRIORITIES = ('p0', 'p1', 'p2')
PLATFORMS = ('ios', 'android', 'web', 'h5', 'mini', 'server', 'api', 'all')

REPEATABLE = ('impression', 'exposure', 'expose', 'view', 'play', 'scroll',
              'appear', 'visible', 'show')
CLICKY = ('click', 'tap', 'submit', 'press')
RESULTY = ('success', 'success_rate', 'result', 'result_rate', 'finish',
           'complete', 'done', 'rate')

IMMEDIATE = ('immediate', 'instant', 'realtime', 'now', 'real_time')
BATCH = ('batch', 'buffer', 'flush_later', 'queued')

R_TIMING_FIRE = ('result-type event must be reported in the success callback, '
                 'not when the request is sent')
R_TIMING_IMPRESSION = ('impression-type event must define a minimum dwell '
                       'time (e.g. 500ms) and a viewport threshold')
R_TIMING_UNKNOWN = 'report timing is not one of immediate/batch/on-exit'
R_IMPRESSION_DEDUP = 'impression-type event needs a dedup key'
R_CLICK_DEDUP = 'click-type event needs an explicit dedup rule'
R_P0_DEDUP = 'P0 event without a dedup rule is a release blocker'
R_NAME_STYLE = ('event name is not lower_snake_case with at least three parts')
R_NAME_UPPER = 'event name contains upper-case characters'
R_NAME_CN = 'event name must not contain spaces or non-ascii characters'
R_DUP = 'duplicate event name'
R_TRIGGER_VAGUE = 'trigger description is too vague to implement'
R_PLATFORM_BAD = 'platform is not recognized'

VAGUE_TRIGGER = ('when', 'somewhere', 'user action', 'later', 'unspecified',
                 'as needed', 'tbd')

# ASCII-only wording; the human-facing guidance is kept in the .md rules file.
MSG_R_TIMING_FIRE = R_TIMING_FIRE
MSG_R_IMPRESSION = R_TIMING_IMPRESSION


def read_rows(path):
    if path == '-':
        data = sys.stdin.read()
    else:
        with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
            data = fh.read()
    return [dict(r) for r in csv.DictReader(io.StringIO(data))]


def g(row, key):
    return (row.get(key) or '').strip()


def kind_of(event, trigger):
    """Classify the event as impression / click / result / plain."""
    e = (event or '').lower()
    t = (trigger or '').lower()
    blob = e + ' ' + t
    if any(k in blob for k in RESULTY):
        return 'result'
    if any(k in blob for k in REPEATABLE):
        return 'impression'
    if any(k in blob for k in CLICKY):
        return 'click'
    return 'plain'


def audit(rows, check_naming=False, check_timing=False, check_dedup=False):
    findings = []
    seen = {}
    for idx, row in enumerate(rows, 1):
        event = g(row, 'event')
        trigger = g(row, 'trigger')
        label = event or ('#%d' % idx)
        if not event:
            findings.append(('ERROR', label, 'missing event name'))
            continue
        low = event.lower()
        if low in seen:
            findings.append(('ERROR', label,
                             '%s (also row #%d)' % (R_DUP, seen[low])))
        else:
            seen[low] = idx
        for field in REQUIRED:
            if not g(row, field):
                findings.append(('ERROR', label, 'missing %s' % field))
        kind = kind_of(event, trigger)
        timing = g(row, 'report_timing').lower()
        dedup = g(row, 'dedup_rule').lower()
        prio = g(row, 'priority').lower()
        if prio and prio not in PRIORITIES:
            findings.append(('WARN', label,
                             'priority should be P0/P1/P2, got %r' % prio))
        plat = g(row, 'platform').lower()
        if plat and plat not in PLATFORMS:
            findings.append(('WARN', label,
                             '%s: %r' % (R_PLATFORM_BAD, plat)))
        if check_timing and timing:
            if kind == 'result' and any(w in timing for w in
                                        ('request', 'send', 'fire', 'start',
                                         'initiate', 'begin')):
                findings.append(('ERROR', label, MSG_R_TIMING_FIRE))
            if kind == 'impression':
                has_dwell = bool(re.search(r'\d+\s*ms|millisecond|dwell',
                                           g(row, 'trigger') + timing,
                                           re.I))
                if not has_dwell:
                    findings.append(('WARN', label, MSG_R_IMPRESSION))
            if not (any(w in timing for w in IMMEDIATE)
                    or any(w in timing for w in BATCH)
                    or 'exit' in timing or 'end' in timing):
                findings.append(('WARN', label, R_TIMING_UNKNOWN))
        if check_dedup and kind == 'impression' and not dedup:
            findings.append(('WARN', label, R_IMPRESSION_DEDUP))
        if check_dedup and kind == 'click' and not dedup:
            findings.append(('WARN', label, R_CLICK_DEDUP))
        if prio == 'p0' and not dedup:
            findings.append(('ERROR', label, R_P0_DEDUP))
        if check_naming:
            if any(ch.isupper() for ch in event):
                findings.append(('WARN', label, R_NAME_UPPER))
            if any(ord(ch) > 127 or ch.isspace() for ch in event):
                findings.append(('WARN', label, R_NAME_CN))
            if not NAME_RE.match(event):
                findings.append(('WARN', label,
                                 '%s: %s' % (R_NAME_STYLE, event)))
        t = g(row, 'trigger').lower()
        if t and any(w in t for w in VAGUE_TRIGGER):
            findings.append(('INFO', label, R_TRIGGER_VAGUE))
    return findings


def render(rows, findings, lines):
    lines.append('== TRACKING PLAN AUDIT ==')
    lines.append('events: %d' % len(rows))
    kinds = {}
    for row in rows:
        k = kind_of(g(row, 'event'), g(row, 'trigger'))
        kinds[k] = kinds.get(k, 0) + 1
    if kinds:
        lines.append('by kind: %s' % ', '.join(
            '%s=%d' % (k, kinds[k]) for k in sorted(kinds)))
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
        lines.append('VERDICT: BLOCKED (errors=%d)' % err)
    else:
        lines.append('VERDICT: PASS (errors=0, warns=%d)'
                     % len(grouped.get('WARN', [])))


def good_rows():
    base = {
        'event': 'trade_order_submit_cart_button',
        'trigger': 'user taps the submit button in cart page',
        'report_timing': 'immediate',
        'properties': 'user_id, channel, app_version, cart_size',
        'priority': 'P0',
        'dedup_rule': 'no dedup: every tap counts as a click',
        'owner': 'client-li / data-wang',
        'platform': 'ios',
    }
    rows = [dict(base)]
    r2 = dict(base)
    r2.update({
        'event': 'content_feed_impression_item',
        'trigger': 'item visible >= 50 percent and dwell >= 500 ms',
        'report_timing': 'immediate',
        'properties': 'item_id, feed_id, session_id, channel',
        'priority': 'P0',
        'dedup_rule': 'dedup by item_id + session_id',
        'platform': 'all',
    })
    rows.append(r2)
    r3 = dict(base)
    r3.update({
        'event': 'trade_pay_result_rate',
        'trigger': 'reported in pay interface success callback',
        'report_timing': 'immediate',
        'properties': 'order_id, amount, channel, fail_reason',
        'priority': 'P0',
        'dedup_rule': 'server side unique by order_id',
        'platform': 'server',
    })
    rows.append(r3)
    r4 = dict(base)
    r4.update({
        'event': 'user_profile_click_avatar',
        'trigger': 'user taps avatar in profile page',
        'report_timing': 'immediate',
        'properties': 'user_id, channel',
        'priority': 'P1',
        'dedup_rule': 'no dedup: every tap counts',
        'platform': 'android',
    })
    rows.append(r4)
    return rows


def selftest():
    checks = []

    def ck(name, cond, info=''):
        checks.append((name, bool(cond), info))

    rows = good_rows()

    # 1 clean plan
    f = audit(rows, True, True, True)
    errs = [x for x in f if x[0] == 'ERROR']
    ck('clean plan has no errors', not errs, str([x[2] for x in errs][:2]))

    # 2 no naming warnings
    nw = [x for x in f if 'event name' in x[2]]
    ck('naming convention satisfied', not nw, str([x[2] for x in nw][:2]))

    # 3 duplicate event name errors
    f2 = audit(rows + [dict(rows[0])])
    ck('duplicate event name errors',
       any(x[0] == 'ERROR' and 'duplicate' in x[2] for x in f2))

    # 4 missing required element errors
    bad = [dict(r) for r in rows]
    bad[0] = dict(bad[0], trigger='')
    f3 = audit(bad)
    ck('missing trigger errors',
       any(x[0] == 'ERROR' and 'missing trigger' in x[2] for x in f3))

    # 5 P0 without dedup is an error
    bad = [dict(r) for r in rows]
    bad[0] = dict(bad[0], dedup_rule='')
    f4 = audit(bad)
    ck('P0 without dedup errors',
       any(x[0] == 'ERROR' and 'P0' in x[2] for x in f4))

    # 6 result event reported on request send errors
    bad = [dict(r) for r in rows]
    bad[2] = dict(bad[2], report_timing='when the request is sent')
    f5 = audit(bad, False, True, False)
    ck('result event on request send errors',
       any(x[0] == 'ERROR' and 'success callback' in x[2] for x in f5))

    # 7 impression without dwell time warns
    bad = [dict(r) for r in rows]
    bad[1] = dict(bad[1], trigger='item visible in viewport')
    f6 = audit(bad, False, True, False)
    ck('impression without dwell warns',
       any(x[0] == 'WARN' and 'dwell' in x[2] for x in f6))

    # 8 impression with dwell passes
    ck('impression with dwell is clean',
       not any('dwell' in x[2] for x in f if 'feed' in x[1]))

    # 9 impression without dedup warns
    bad = [dict(r) for r in rows]
    bad[1] = dict(bad[1], dedup_rule='', priority='P1')
    f7 = audit(bad, False, False, True)
    ck('impression without dedup warns',
       any(x[0] == 'WARN' and 'impression' in x[2] for x in f7))

    # 10 upper-case event name warns
    bad = [dict(r) for r in rows]
    bad[0] = dict(bad[0], event='Trade_Order_Submit')
    f8 = audit(bad, True, False, False)
    ck('upper-case name warns',
       any(x[0] == 'WARN' and 'upper-case' in x[2] for x in f8))

    # 11 non-ascii name warns
    bad = [dict(r) for r in rows]
    bad[0] = dict(bad[0], event=u'trade_order_\u70b9\u51fb_button')
    f9 = audit(bad, True, False, False)
    ck('non-ascii name warns',
       any(x[0] == 'WARN' and 'non-ascii' in x[2] for x in f9))

    # 12 too-short name warns
    bad = [dict(r) for r in rows]
    bad[0] = dict(bad[0], event='submit')
    f10 = audit(bad, True, False, False)
    ck('short name warns',
       any(x[0] == 'WARN' and 'three parts' in x[2] for x in f10))

    # 13 unknown report timing warns
    bad = [dict(r) for r in rows]
    bad[0] = dict(bad[0], report_timing='some point later')
    f11 = audit(bad, False, True, False)
    ck('unknown timing warns',
       any(x[0] == 'WARN' and 'not one of' in x[2] for x in f11))

    # 14 vague trigger gives INFO
    bad = [dict(r) for r in rows]
    bad[3] = dict(bad[3], trigger='when user does something')
    f12 = audit(bad)
    ck('vague trigger gives INFO',
       any(x[0] == 'INFO' and 'vague' in x[2] for x in f12))

    # 15 kind classification
    ck('classification result/impression/click',
       kind_of('trade_pay_result_rate', 'in success callback') == 'result'
       and kind_of('feed_impression_item', 'dwell 500 ms') == 'impression'
       and kind_of('profile_click_avatar', 'taps avatar') == 'click')

    # 16 bad priority warns
    bad = [dict(r) for r in rows]
    bad[0] = dict(bad[0], priority='high')
    f13 = audit(bad)
    ck('bad priority warns',
       any(x[0] == 'WARN' and 'P0/P1/P2' in x[2] for x in f13))

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
    p = argparse.ArgumentParser(description='Event tracking plan auditor')
    p.add_argument('--file', type=str, default=None,
                   help='CSV event list, or - for stdin')
    p.add_argument('--check-naming', dest='check_naming', action='store_true')
    p.add_argument('--check-timing', dest='check_timing', action='store_true')
    p.add_argument('--check-dedup', dest='check_dedup', action='store_true')
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
    if not rows:
        text = '[ERROR] no rows in %s\n' % args.file
        with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(text)
        return 2
    findings = audit(rows, args.check_naming, args.check_timing,
                     args.check_dedup)
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