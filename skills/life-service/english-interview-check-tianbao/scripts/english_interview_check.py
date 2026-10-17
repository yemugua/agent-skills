#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u82f1\u6587\u9762\u8bd5\u81ea\u6211\u4ecb\u7ecd\u65f6\u957f\u8bcd\u6570\u8bed\u901f\u6838\u67e5\u4e0e STAR \u56db\u8981\u7d20\u7ed3\u6784\u6838\u67e5\u3002

\u7528\u6cd5:
  python english_interview_check.py --intro-words 165 --intro-seconds 75
  python english_interview_check.py --star-parts situation,task,action,result --action-ratio 0.6 --result-numbers 2
  python english_interview_check.py --intro-words 165 --intro-seconds 75 \
      --star-parts situation,task,action --action-ratio 0.35 --result-numbers 0
  python english_interview_check.py --selftest

\u53c2\u6570:
  --intro-words    \u81ea\u6211\u4ecb\u7ecd\u8bcd\u6570
  --intro-seconds  \u81ea\u6211\u4ecb\u7ecd\u79d2\u6570
  --star-parts     \u5df2\u8986\u76d6\u7684 STAR \u8981\u7d20\uff0c\u9017\u53f7\u5206\u9694\uff0c\u53d6\u503c situation/task/action/result
  --action-ratio   Action \u90e8\u5206\u5360\u6bd4 0~1
  --result-numbers Result \u90e8\u5206\u53ef\u91cf\u5316\u6570\u5b57\u4e2a\u6570
  --out            \u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84
  --format         md\uff08\u9ed8\u8ba4\uff09\u6216 json
  --selftest       \u8fd0\u884c\u5185\u7f6e\u81ea\u68c0
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

WORD_OK = (130, 180)
SECOND_OK = (60, 90)
WPM_OK = (120, 160)
STAR_PARTS = [('situation', 'Situation', '\u80cc\u666f\u662f\u4ec0\u4e48'),
              ('task', 'Task', '\u4f60\u8981\u89e3\u51b3\u4ec0\u4e48'),
              ('action', 'Action', '\u4f60\u5177\u4f53\u505a\u4e86\u4ec0\u4e48'),
              ('result', 'Result', '\u7ed3\u679c\u5982\u4f55')]
ACTION_OK = 0.5


def wpm_of(words, seconds):
    if not words or not seconds:
        return None
    return words * 60.0 / seconds


def word_check(n):
    lo, hi = WORD_OK
    if n is None:
        return '\u5f85\u8865\u5145', '\u672a\u586b\u8bcd\u6570', ''
    if n < 120:
        return '\u4e0d\u7b26\u5408', '%d \u8bcd\uff0c\u4f4e\u4e8e\u5efa\u8bae\u533a\u95f4 %d~%d' % (n, lo, hi), '\u4fe1\u606f\u91cf\u4e0d\u8db3\uff0c\u8865\u4e00\u4e2a\u76f8\u5173\u7ecf\u5386'
    if n < lo:
        return '\u9700\u5173\u6ce8', '%d \u8bcd\uff0c\u7565\u4f4e\u4e8e\u5efa\u8bae\u533a\u95f4 %d~%d' % (n, lo, hi), 'Past \u6bb5\u8865\u4e00\u53e5\u7ed3\u679c'
    if n > 220:
        return '\u4e0d\u7b26\u5408', '%d \u8bcd\uff0c\u8fdc\u9ad8\u4e8e\u5efa\u8bae\u533a\u95f4 %d~%d' % (n, lo, hi), '\u901a\u5e38\u5df2\u8d85\u65f6\uff0c\u780d\u6389\u4e0d\u76f8\u5173\u7ecf\u5386'
    if n > hi:
        return '\u9700\u5173\u6ce8', '%d \u8bcd\uff0c\u7565\u9ad8\u4e8e\u5efa\u8bae\u533a\u95f4 %d~%d' % (n, lo, hi), '\u63a7\u5236\u5728 %d \u8bcd\u4ee5\u5185' % hi
    return '\u7b26\u5408', '%d \u8bcd\uff0c\u5728\u5efa\u8bae\u533a\u95f4 %d~%d' % (n, lo, hi), '\u4fdd\u6301'


def second_check(n):
    lo, hi = SECOND_OK
    if n is None:
        return '\u5f85\u8865\u5145', '\u672a\u586b\u79d2\u6570', ''
    if n < 45:
        return '\u4e0d\u7b26\u5408', '%d \u79d2\uff0c\u4f4e\u4e8e\u5efa\u8bae\u533a\u95f4 %d~%d' % (n, lo, hi), '\u663e\u5f97\u5355\u8584\uff0c\u8865 Past \u6bb5\u5185\u5bb9'
    if n < lo:
        return '\u9700\u5173\u6ce8', '%d \u79d2\uff0c\u7565\u4f4e\u4e8e\u5efa\u8bae\u533a\u95f4 %d~%d' % (n, lo, hi), '\u8865\u5230 %d \u79d2\u5de6\u53f3' % lo
    if n > 120:
        return '\u4e0d\u7b26\u5408', '%d \u79d2\uff0c\u8fdc\u9ad8\u4e8e\u5efa\u8bae\u533a\u95f4 %d~%d' % (n, lo, hi), '\u9762\u8bd5\u5b98\u4f1a\u8d70\u795e\uff0c\u780d\u5185\u5bb9'
    if n > hi:
        return '\u9700\u5173\u6ce8', '%d \u79d2\uff0c\u7565\u9ad8\u4e8e\u5efa\u8bae\u533a\u95f4 %d~%d' % (n, lo, hi), '\u538b\u7f29\u5230 %d \u79d2\u4ee5\u5185' % hi
    return '\u7b26\u5408', '%d \u79d2\uff0c\u5728\u5efa\u8bae\u533a\u95f4 %d~%d' % (n, lo, hi), '\u4fdd\u6301'


def wpm_check(v):
    lo, hi = WPM_OK
    if v is None:
        return '\u5f85\u8865\u5145', '\u672a\u586b\u8bcd\u6570\u4e0e\u79d2\u6570\uff0c\u65e0\u6cd5\u7b97\u8bed\u901f', ''
    if v < 100:
        return '\u4e0d\u7b26\u5408', '\u8bed\u901f %.0f \u8bcd/\u5206\u949f\uff0c\u4f4e\u4e8e %d' % (v, lo), '\u5185\u5bb9\u4e0d\u719f\uff0c\u5148\u7ec3\u719f\u518d\u8ba1\u65f6'
    if v < lo:
        return '\u9700\u5173\u6ce8', '\u8bed\u901f %.0f \u8bcd/\u5206\u949f\uff0c\u7565\u6162\uff08\u5efa\u8bae %d~%d\uff09' % (v, lo, hi), '\u51cf\u5c11\u505c\u987f'
    if v > 180:
        return '\u4e0d\u7b26\u5408', '\u8bed\u901f %.0f \u8bcd/\u5206\u949f\uff0c\u5feb\u4e8e %d\uff0c\u542c\u4e0d\u6e05' % (v, hi), '\u7d27\u5f20\u5bfc\u81f4\uff0c\u5148\u7ec3\u6162\u901f\u7248\u672c'
    if v > hi:
        return '\u9700\u5173\u6ce8', '\u8bed\u901f %.0f \u8bcd/\u5206\u949f\uff0c\u7565\u5feb\uff08\u5efa\u8bae %d~%d\uff09' % (v, lo, hi), '\u5141\u8bb8\u77ed\u6682\u505c\u987f'
    return '\u7b26\u5408', '\u8bed\u901f %.0f \u8bcd/\u5206\u949f\uff0c\u5728\u5efa\u8bae\u533a\u95f4 %d~%d' % (v, lo, hi), '\u4fdd\u6301'


def action_check(v):
    if v is None:
        return '\u5f85\u8865\u5145', '\u672a\u586b Action \u5360\u6bd4', ''
    if v < 0.4:
        return '\u4e0d\u7b26\u5408', 'Action \u5360\u6bd4 %.0f%%\uff0c\u4f4e\u4e8e 40%%' % (v * 100), '\u5728\u8bb2\u80cc\u666f\u4e0d\u662f\u5728\u8bb2\u81ea\u5df1'
    if v < ACTION_OK:
        return '\u9700\u5173\u6ce8', 'Action \u5360\u6bd4 %.0f%%\uff0c\u4f4e\u4e8e\u5efa\u8bae %.0f%%' % (v * 100, ACTION_OK * 100), '\u538b\u7f29\u80cc\u666f\uff0c\u5c55\u5f00\u6211\u505a\u4e86\u4ec0\u4e48'
    if v > 0.8:
        return '\u9700\u5173\u6ce8', 'Action \u5360\u6bd4 %.0f%%\uff0c\u8fc7\u9ad8' % (v * 100), '\u8865\u4e00\u53e5\u80cc\u666f\u4e0e\u7ed3\u679c'
    return '\u7b26\u5408', 'Action \u5360\u6bd4 %.0f%%\uff0c\u5728\u5efa\u8bae\u533a\u95f4' % (v * 100), '\u4fdd\u6301'


def result_check(n):
    if n is None:
        return '\u5f85\u8865\u5145', '\u672a\u586b Result \u91cf\u5316\u6570\u5b57\u4e2a\u6570', ''
    if n <= 0:
        return '\u9700\u5173\u6ce8', 'Result \u65e0\u53ef\u91cf\u5316\u6570\u5b57', '\u8865\u4e00\u4e2a\u53ef\u6838\u9a8c\u7684\u91cf'
    if n == 1:
        return '\u7b26\u5408', 'Result \u6709 1 \u4e2a\u53ef\u91cf\u5316\u6570\u5b57', '\u4fdd\u6301'
    return '\u7b26\u5408', 'Result \u6709 %d \u4e2a\u53ef\u91cf\u5316\u6570\u5b57' % n, '\u4fdd\u6301'


def parse_parts(s):
    if not s:
        return []
    return [p.strip().lower() for p in s.replace('\uff0c', ',').split(',') if p.strip()]


def check(args):
    words, seconds = args.intro_words, args.intro_seconds
    wpm = wpm_of(words, seconds)
    items = []
    wr, wd, wa = word_check(words)
    sr, sd, sa = second_check(seconds)
    vr, vd, va = wpm_check(wpm)
    items.append({'name': '\u81ea\u6211\u4ecb\u7ecd\u8bcd\u6570', 'result': wr, 'detail': wd, 'advice': wa})
    items.append({'name': '\u81ea\u6211\u4ecb\u7ecd\u65f6\u957f', 'result': sr, 'detail': sd, 'advice': sa})
    items.append({'name': '\u8bed\u901f', 'result': vr, 'detail': vd, 'advice': va})

    parts = parse_parts(args.star_parts)
    star_items = []
    for key, label, desc in STAR_PARTS:
        ok = key in parts
        star_items.append({'part': label, 'desc': desc, 'result': '\u7b26\u5408' if ok else '\u4e0d\u7b26\u5408',
                           'detail': '\u5df2\u8986\u76d6' if ok else '\u7f3a\u5931',
                           'advice': '' if ok else '\u8865\u4e0a %s\uff1a%s' % (label, desc)})
    ar, ad, aa = action_check(args.action_ratio)
    rr, rd, ra = result_check(args.result_numbers)
    star_items.append({'part': 'Action \u5360\u6bd4', 'desc': '\u5efa\u8bae 50%~70%',
                       'result': ar, 'detail': ad, 'advice': aa})
    star_items.append({'part': 'Result \u91cf\u5316', 'desc': '\u5efa\u8bae\u81f3\u5c11 1 \u4e2a\u53ef\u6838\u9a8c\u7684\u91cf',
                       'result': rr, 'detail': rd, 'advice': ra})

    missing = [s['part'] for s in star_items
               if s['result'] == '\u4e0d\u7b26\u5408' and s['part'] in ('Situation', 'Task', 'Action', 'Result')]
    priority = []
    if 'Result' in missing:
        priority.append('STAR \u7f3a Result\uff0c\u7b49\u4e8e\u7ecf\u5386\u8bb2\u4e86\u4e00\u534a\uff0c\u5fc5\u987b\u8865\u7ed3\u679c')
    if 'Action' in missing:
        priority.append('STAR \u7f3a Action\uff0c\u7b49\u4e8e\u6ca1\u8bf4\u4f60\u505a\u4e86\u4ec0\u4e48')
    if args.action_ratio is not None and args.action_ratio < 0.4:
        priority.append('Action \u5360\u6bd4\u8fc7\u4f4e\uff0c\u628a\u80cc\u666f\u538b\u7f29\u5230\u4e00\u53e5\uff0c\u5c55\u5f00\u6211\u505a\u4e86\u4ec0\u4e48')
    if args.result_numbers is not None and args.result_numbers <= 0:
        priority.append('Result \u6ca1\u6709\u53ef\u6838\u9a8c\u7684\u91cf\uff0c\u8865\u4e00\u4e2a\u6570\u5b57')
    if wpm is not None and wpm > 180:
        priority.append('\u8bed\u901f\u8fc7\u5feb\uff0c\u5148\u7ec3\u6162\u901f\u7248\u672c\u518d\u63d0\u901f')
    if wpm is not None and wpm < 100:
        priority.append('\u8bed\u901f\u8fc7\u6162\uff0c\u5148\u628a\u5185\u5bb9\u7ec3\u719f\u518d\u8ba1\u65f6')

    known = [x for x in (words, seconds, args.action_ratio, args.result_numbers)
             if x is not None]
    if not parts and not known:
        verdict = '\u9700\u8865\u5145\u4fe1\u606f\u540e\u786e\u8ba4'
    elif any(s['result'] == '\u4e0d\u7b26\u5408' for s in star_items):
        verdict = '\u672a\u8fbe\u76ee\u6807'
    elif any(s['result'] == '\u9700\u5173\u6ce8' for s in star_items + items):
        verdict = '\u63a5\u8fd1\u76ee\u6807'
    else:
        verdict = '\u8fbe\u5230\u76ee\u6807'

    return {'words': words, 'seconds': seconds, 'wpm': wpm, 'items': items,
            'star_items': star_items, 'missing': missing, 'priority': priority,
            'verdict': verdict}


def render_md(r):
    lines = []
    lines.append('# \u82f1\u6587\u9762\u8bd5\u6838\u67e5\u7ed3\u679c')
    lines.append('')
    if r['wpm'] is not None:
        lines.append('- \u81ea\u6211\u4ecb\u7ecd\uff1a%d \u8bcd / %d \u79d2\uff0c\u8bed\u901f **%.0f \u8bcd/\u5206\u949f**'
                     % (r['words'], r['seconds'], r['wpm']))
    lines.append('- \u5224\u5b9a\uff1a**%s**' % r['verdict'])
    lines.append('')
    lines.append('| \u6838\u67e5\u9879 | \u5224\u5b9a | \u8bf4\u660e | \u6539\u8fdb\u52a8\u4f5c |')
    lines.append('|---|---|---|---|')
    for it in r['items']:
        lines.append('| %s | %s | %s | %s |' % (it['name'], it['result'], it['detail'],
                                                it['advice'] or '\u2014'))
    lines.append('')
    lines.append('## STAR \u7ed3\u6784\u6838\u67e5')
    lines.append('')
    lines.append('| \u8981\u7d20 | \u8bf4\u660e | \u5224\u5b9a | \u8be6\u60c5 | \u6539\u8fdb\u52a8\u4f5c |')
    lines.append('|---|---|---|---|---|')
    for s in r['star_items']:
        lines.append('| %s | %s | %s | %s | %s |' % (s['part'], s['desc'], s['result'],
                                                     s['detail'], s['advice'] or '\u2014'))
    lines.append('')
    if r['priority']:
        lines.append('## \u8bad\u7ec3\u65b9\u5411')
        lines.append('')
        for p in r['priority']:
            lines.append('- %s' % p)
        lines.append('')
    lines.append('> \u8bed\u901f\u4e0e\u914d\u6bd4\u662f\u7ec3\u4e60\u6307\u6807\uff0c\u4e0d\u662f\u9762\u8bd5\u8bc4\u5206\u6807\u51c6\uff1b\u9762\u8bd5\u5b98\u7684\u8bc4\u4ef7\u7ef4\u5ea6\u4ee5\u5b9e\u9645\u5c97\u4f4d\u8981\u6c42\u4e3a\u51c6\u3002')
    return '\n'.join(lines)


def selftest():
    errors = []

    def mk(**kw):
        a = argparse.Namespace(intro_words=None, intro_seconds=None, star_parts=None,
                               action_ratio=None, result_numbers=None, out=None, format='md')
        for k, v in kw.items():
            setattr(a, k, v)
        return a

    def eq(name, got, want):
        if got != want:
            errors.append('%s: got=%r want=%r' % (name, got, want))

    def item(r, name):
        for i in r['items']:
            if i['name'] == name:
                return i
        return None

    def sitem(r, name):
        for i in r['star_items']:
            if i['part'] == name:
                return i
        return None

    eq('case01 \u8bed\u901f 165/75*60=132',
       round(wpm_of(165, 75)), 132)
    eq('case02 \u8bed\u901f 132 \u5224\u7b26\u5408',
       item(check(mk(intro_words=165, intro_seconds=75)), '\u8bed\u901f')['result'], '\u7b26\u5408')
    eq('case03 \u8bed\u901f 240 \u5224\u4e0d\u7b26\u5408',
       item(check(mk(intro_words=240, intro_seconds=60)), '\u8bed\u901f')['result'], '\u4e0d\u7b26\u5408')
    eq('case04 \u8bed\u901f 110 \u5224\u9700\u5173\u6ce8',
       item(check(mk(intro_words=110, intro_seconds=60)), '\u8bed\u901f')['result'], '\u9700\u5173\u6ce8')
    eq('case05 \u8bed\u901f 170 \u5224\u9700\u5173\u6ce8',
       item(check(mk(intro_words=170, intro_seconds=60)), '\u8bed\u901f')['result'], '\u9700\u5173\u6ce8')
    eq('case06 \u8bcd\u6570 165 \u7b26\u5408',
       item(check(mk(intro_words=165)), '\u81ea\u6211\u4ecb\u7ecd\u8bcd\u6570')['result'], '\u7b26\u5408')
    eq('case07 \u8bcd\u6570 100 \u4e0d\u7b26\u5408',
       item(check(mk(intro_words=100)), '\u81ea\u6211\u4ecb\u7ecd\u8bcd\u6570')['result'], '\u4e0d\u7b26\u5408')
    eq('case08 \u8bcd\u6570 240 \u4e0d\u7b26\u5408',
       item(check(mk(intro_words=240)), '\u81ea\u6211\u4ecb\u7ecd\u8bcd\u6570')['result'], '\u4e0d\u7b26\u5408')
    eq('case09 \u65f6\u957f 75 \u79d2\u7b26\u5408',
       item(check(mk(intro_seconds=75)), '\u81ea\u6211\u4ecb\u7ecd\u65f6\u957f')['result'], '\u7b26\u5408')
    eq('case10 \u65f6\u957f 30 \u79d2\u4e0d\u7b26\u5408',
       item(check(mk(intro_seconds=30)), '\u81ea\u6211\u4ecb\u7ecd\u65f6\u957f')['result'], '\u4e0d\u7b26\u5408')
    eq('case11 \u65f6\u957f 130 \u79d2\u4e0d\u7b26\u5408',
       item(check(mk(intro_seconds=130)), '\u81ea\u6211\u4ecb\u7ecd\u65f6\u957f')['result'], '\u4e0d\u7b26\u5408')
    r12 = check(mk(star_parts='situation,task,action,result'))
    eq('case12 STAR \u56db\u8981\u7d20\u9f50\u5168', sitem(r12, 'Result')['result'], '\u7b26\u5408')
    r13 = check(mk(star_parts='situation,task,action'))
    eq('case13 \u7f3a Result \u5224\u4e0d\u7b26\u5408', sitem(r13, 'Result')['result'], '\u4e0d\u7b26\u5408')
    eq('case14 \u7f3a Result \u8fdb\u7f3a\u53e3\u5217\u8868', 'Result' in r13['missing'], True)
    eq('case15 \u7f3a Result \u4f18\u5148\u63d0\u793a',
       any('\u7f3a Result' in p for p in r13['priority']), True)
    r16 = check(mk(star_parts='situation,task,action,result', action_ratio=0.6))
    eq('case16 Action \u5360\u6bd4 0.6 \u7b26\u5408', sitem(r16, 'Action \u5360\u6bd4')['result'], '\u7b26\u5408')
    r17 = check(mk(star_parts='situation,task,action,result', action_ratio=0.35))
    eq('case17 Action \u5360\u6bd4 0.35 \u4e0d\u7b26\u5408', sitem(r17, 'Action \u5360\u6bd4')['result'], '\u4e0d\u7b26\u5408')
    r18 = check(mk(star_parts='situation,task,action,result', action_ratio=0.45))
    eq('case18 Action \u5360\u6bd4 0.45 \u9700\u5173\u6ce8', sitem(r18, 'Action \u5360\u6bd4')['result'], '\u9700\u5173\u6ce8')
    r19 = check(mk(star_parts='situation,task,action,result', result_numbers=0))
    eq('case19 Result \u65e0\u6570\u5b57\u5224\u9700\u5173\u6ce8', sitem(r19, 'Result \u91cf\u5316')['result'], '\u9700\u5173\u6ce8')
    r20 = check(mk(star_parts='situation,task,action,result', result_numbers=2))
    eq('case20 Result \u6709 2 \u4e2a\u6570\u5b57\u7b26\u5408', sitem(r20, 'Result \u91cf\u5316')['result'], '\u7b26\u5408')
    r21 = check(mk(intro_words=165, intro_seconds=75,
                   star_parts='situation,task,action,result',
                   action_ratio=0.6, result_numbers=2))
    eq('case21 \u5168\u90e8\u8fbe\u6807\u5224\u8fbe\u5230\u76ee\u6807', r21['verdict'], '\u8fbe\u5230\u76ee\u6807')
    r22 = check(mk(intro_words=165, intro_seconds=75,
                   star_parts='situation,task,action,result',
                   action_ratio=0.45, result_numbers=1))
    eq('case22 \u6709\u9700\u5173\u6ce8\u5224\u63a5\u8fd1\u76ee\u6807', r22['verdict'], '\u63a5\u8fd1\u76ee\u6807')
    eq('case23 \u65e0\u8f93\u5165\u5224\u9700\u8865\u5145\u4fe1\u606f', check(mk())['verdict'], '\u9700\u8865\u5145\u4fe1\u606f\u540e\u786e\u8ba4')
    eq('case24 \u4e2d\u6587\u9017\u53f7\u5206\u9694\u4e5f\u80fd\u89e3\u6790',
       len(parse_parts('situation\uff0ctask\uff0caction\uff0cresult')), 4)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 24\n\u8986\u76d6: \u8bcd\u6570\u4e09\u6863/\u65f6\u957f\u4e09\u6863/\u8bed\u901f\u4e94\u6863/STAR \u56db\u8981\u7d20\u7f3a\u5931/'
               'Action \u5360\u6bd4/Result \u91cf\u5316/\u7efc\u5408\u5224\u5b9a/\u4fe1\u606f\u7f3a\u5931')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u82f1\u6587\u9762\u8bd5\u81ea\u6211\u4ecb\u7ecd\u4e0e\u5e38\u89c1\u95ee\u9898\u6838\u67e5')
    ap.add_argument('--intro-words', dest='intro_words', type=int, help='\u81ea\u6211\u4ecb\u7ecd\u8bcd\u6570')
    ap.add_argument('--intro-seconds', dest='intro_seconds', type=int, help='\u81ea\u6211\u4ecb\u7ecd\u79d2\u6570')
    ap.add_argument('--star-parts', dest='star_parts',
                    help='\u5df2\u8986\u76d6\u7684 STAR \u8981\u7d20\uff0c\u9017\u53f7\u5206\u9694')
    ap.add_argument('--action-ratio', dest='action_ratio', type=float,
                    help='Action \u90e8\u5206\u5360\u6bd4 0~1')
    ap.add_argument('--result-numbers', dest='result_numbers', type=int,
                    help='Result \u90e8\u5206\u53ef\u91cf\u5316\u6570\u5b57\u4e2a\u6570')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'])
    ap.add_argument('--selftest', action='store_true', help='\u8fd0\u884c\u5185\u7f6e\u81ea\u68c0')
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    r = check(args)
    out = render_md(r) if args.format == 'md' else json.dumps(r, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % args.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
