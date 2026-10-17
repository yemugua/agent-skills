# -*- coding: utf-8 -*-
"""WiFi \u6162\u7f51\u6545\u969c\u6811\u5224\u65ad\uff1a\u8f93\u5165\u73b0\u8c61\uff0c\u8f93\u51fa\u6392\u67e5\u987a\u5e8f\u4e0e\u5904\u7f6e\u5efa\u8bae\u3002

\u7528\u6cd5:
  python wifi_channel_check.py --text "\u4fe1\u53f7\u6ee1\u683c\u4f46\u7f51\u901f\u6162\uff0c\u665a\u4e0a\u7279\u522b\u5361\uff0c\u6709\u5fae\u6ce2\u7089"
  python wifi_channel_check.py --file \u63cf\u8ff0.txt [--out \u7ed3\u679c.md] [--format json]
  python wifi_channel_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

RULES = [
    {'id': 'W1', 'order': 1, 'name': '\u5bbd\u5e26\u6216\u7ebf\u8def\u95ee\u9898',
     'kw': ['\u6709\u7ebf\u4e5f\u6162', '\u76f4\u8fde\u4e5f\u6162', '\u63d2\u7f51\u7ebf\u4e5f', '\u5bbd\u5e26\u6162', '\u5149\u732b', '\u7ea2\u706f', '\u6389\u7ebf\u9891\u7e41'],
     'test': '\u7f51\u7ebf\u76f4\u8fde\u5149\u732b\u6216\u8def\u7531\u5668 LAN \u53e3\u6d4b\u901f',
     'fix': '\u6709\u7ebf\u4e5f\u6162\u5c5e\u5bbd\u5e26\u6216\u7ebf\u8def\u95ee\u9898\uff0c\u62a5\u8fd0\u8425\u5546\u88c5\u7ef4'},
    {'id': 'W2', 'order': 2, 'name': '\u8986\u76d6\u4e0d\u8db3',
     'kw': ['\u4fe1\u53f7\u5f31', '\u4e00\u683c', '\u4e24\u683c', '\u8fdc\u5904', '\u9694\u5899', '\u7a7f\u5899', '\u5367\u5ba4\u6ca1\u4fe1\u53f7', '\u8986\u76d6'],
     'test': '\u8fd1\u573a\u4e0e\u8fdc\u573a\u5404\u6d4b\u4e09\u6b21\u5bf9\u6bd4',
     'fix': '\u9760 Mesh \u6216\u6709\u7ebf AP \u89e3\u51b3\uff0c\u6362\u4fe1\u9053\u65e0\u6548'},
    {'id': 'W3', 'order': 3, 'name': '2.4G \u9891\u6bb5\u62e5\u585e',
     'kw': ['2.4', '2.4G', '\u8fde\u4e0d\u4e0a', '\u5f88\u5361', '\u6162'],
     'test': '2.4G \u4e0e 5G \u5206\u522b\u6d4b\u901f\u5bf9\u6bd4',
     'fix': '\u8fc1\u5230 5G \u9891\u6bb5'},
    {'id': 'W4', 'order': 4, 'name': '\u4fe1\u9053\u91cd\u53e0\u5e72\u6270',
     'kw': ['\u6ee1\u683c', '\u4fe1\u53f7\u6ee1', '\u665a\u4e0a', '\u9ad8\u5cf0', '\u90bb\u5c45', '\u4fe1\u9053', '\u5e72\u6270'],
     'test': '\u626b\u63cf\u5468\u8fb9\u4fe1\u9053\u5360\u7528\u60c5\u51b5',
     'fix': '2.4G \u5728 1\u30016\u300111 \u4e2d\u9009\u6700\u7a7a\u95f2\u7684\u5e76\u56fa\u5b9a'},
    {'id': 'W5', 'order': 5, 'name': '\u4fe1\u9053\u5bbd\u5ea6\u8bbe\u7f6e\u4e0d\u5f53',
     'kw': ['40MHz', '40\u5146', '\u5bbd\u5ea6', '\u9891\u5bbd', '20MHz', '20\u5146', '80'],
     'test': '\u67e5\u770b\u65e0\u7ebf\u8bbe\u7f6e\u7684\u4fe1\u9053\u5bbd\u5ea6',
     'fix': '2.4G \u6539\u56de 20MHz\uff0c5G \u7528 80MHz\uff0c\u62e5\u6324\u65f6\u964d 40MHz'},
    {'id': 'W6', 'order': 6, 'name': '\u975e WiFi \u5e72\u6270\u6e90',
     'kw': ['\u5fae\u6ce2\u7089', '\u65e0\u7ef3\u7535\u8bdd', '\u6444\u50cf\u5934', '\u84dd\u7259', '\u5a74\u513f', 'zigbee', '\u70ed\u996d'],
     'test': '\u5173\u6389\u53ef\u7591\u7535\u5668\u540e\u5bf9\u6bd4\u6d4b\u901f',
     'fix': '\u8def\u7531\u5668\u8fdc\u79bb\u5e72\u6270\u6e90\u6216\u6539\u7528 5G'},
    {'id': 'W7', 'order': 7, 'name': '\u53cc\u9891\u5408\u4e00\u51b2\u7a81',
     'kw': ['\u53cc\u9891\u5408\u4e00', '\u5408\u4e00', '\u667a\u80fd\u8bbe\u5907', '\u7269\u8054\u7f51', '\u63d2\u5ea7', '\u603b\u6389\u7ebf', '\u627e\u4e0d\u5230'],
     'test': '\u62c6\u5206\u4e3a\u4e24\u4e2a SSID \u540e\u89c2\u5bdf',
     'fix': '\u5206\u5f00 SSID\uff0c\u7269\u8054\u7f51\u8bbe\u5907\u7ed1\u5b9a 2.4G'},
    {'id': 'W8', 'order': 8, 'name': '\u7ec8\u7aef\u80fd\u529b\u8001\u65e7',
     'kw': ['\u53ea\u6709\u8fd9\u4e2a', '\u4e2a\u522b\u8bbe\u5907', '\u624b\u673a\u8001', '\u7b14\u8bb0\u672c\u6162', '\u7f51\u5361'],
     'test': '\u6362\u4e00\u53f0\u8bbe\u5907\u5bf9\u6bd4\u6d4b\u901f',
     'fix': '\u5347\u7ea7\u7ec8\u7aef\u7f51\u5361\u6216\u66f4\u6362\u8bbe\u5907'},
    {'id': 'W9', 'order': 9, 'name': '\u8def\u7531\u5668\u6446\u653e\u4e0d\u5f53',
     'kw': ['\u5f31\u7535\u7bb1', '\u91d1\u5c5e', '\u9c7c\u7f38', '\u67dc\u5b50\u91cc', '\u89d2\u843d', '\u955c'],
     'test': '\u632a\u5230\u5f00\u9614\u5c45\u4e2d\u4f4d\u7f6e\u540e\u5bf9\u6bd4\u6d4b\u901f',
     'fix': '\u5c45\u4e2d\u3001\u79bb\u5730 1-1.5 \u7c73\u3001\u907f\u5f00\u91d1\u5c5e\u4e0e\u6c34\u4f53'},
    {'id': 'W10', 'order': 10, 'name': '\u591a AP \u6216\u4f01\u4e1a\u73af\u5883',
     'kw': ['\u591a\u4e2aAP', '\u591a\u4e2a\u8def\u7531\u5668', '\u516c\u53f8', '\u5546\u94fa', '\u6f2b\u6e38', '\u5341\u51e0\u4e2a'],
     'test': '\u7edf\u8ba1 AP \u4e0e\u7ec8\u7aef\u6570\u91cf',
     'fix': '\u8bf7\u4e13\u4e1a\u7f51\u89c4\u505a\u7edf\u4e00\u4fe1\u9053\u89c4\u5212'},
]

RED = [
    {'kw': ['\u6709\u7ebf\u4e5f\u6162', '\u76f4\u8fde\u4e5f\u6162', '\u63d2\u7f51\u7ebf\u4e5f', '\u5bbd\u5e26\u6162'],
     'msg': '\u6709\u7ebf\u76f4\u8fde\u4e5f\u6162\u8bf4\u660e\u662f\u5bbd\u5e26\u6216\u7ebf\u8def\u95ee\u9898\uff1a\u6362\u4fe1\u9053\u65e0\u6cd5\u89e3\u51b3\uff0c\u62a5\u8fd0\u8425\u5546\u88c5\u7ef4\u3002'},
    {'kw': ['\u5149\u732b', '\u7ea2\u706f', '\u6ce8\u518c', '\u6865\u63a5', 'vlan'],
     'msg': '\u7981\u6b62\u81ea\u884c\u4fee\u6539\u5149\u732b\u6ce8\u518c\u4e0e\u8ba4\u8bc1\u53c2\u6570\uff1a\u6539\u9519\u4f1a\u76f4\u63a5\u65ad\u7f51\uff0c\u9700\u88c5\u7ef4\u4e0a\u95e8\u91cd\u65b0\u4e0b\u53d1\u6570\u636e\u3002'},
    {'kw': ['\u5237\u673a', '\u7b2c\u4e09\u65b9\u56fa\u4ef6', '\u6885\u6797', 'padavan'],
     'msg': '\u5237\u5165\u7b2c\u4e09\u65b9\u56fa\u4ef6\u5b58\u5728\u53d8\u7816\u3001\u5931\u4fdd\u4e0e\u5408\u89c4\u98ce\u9669\uff0c\u4e0d\u5efa\u8bae\u81ea\u884c\u64cd\u4f5c\u3002'},
    {'kw': ['\u591a\u4e2aAP', '\u516c\u53f8', '\u5546\u94fa', '\u6f2b\u6e38', '\u5341\u51e0\u4e2a'],
     'msg': '\u591a AP \u4e0e\u4f01\u4e1a\u9ad8\u5bc6\u5ea6\u573a\u666f\u9700\u4e13\u4e1a\u7f51\u89c4\u4e0e\u7edf\u4e00\u4fe1\u9053\u89c4\u5212\uff0c\u8bf7\u4e13\u4e1a\u4eba\u5458\u5904\u7406\u3002'},
    {'kw': ['POE', '\u5e03\u7ebf', '\u5929\u82b1\u677f', '\u767b\u9ad8', '\u5f3a\u7535'],
     'msg': '\u7f51\u7ebf\u5e03\u8bbe\u3001POE \u4f9b\u7535\u3001\u5929\u82b1\u677f\u5185\u4f5c\u4e1a\u4e0e\u767b\u9ad8\u5b89\u88c5\u6d89\u53ca\u5f3a\u7535\u4e0e\u9ad8\u7a7a\uff0c\u8bf7\u4e13\u4e1a\u4eba\u5458\u65bd\u5de5\u3002'},
]

MISREAD = [
    {'kw': ['\u6162', '\u5361', '\u7f51\u901f'],
     'msg': '\u7f51\u901f\u6162\u4e0d\u7b49\u4e8e\u4fe1\u9053\u95ee\u9898\uff0c\u5148\u505a\u6709\u7ebf\u76f4\u8fde\u6d4b\u901f\u6392\u9664\u5bbd\u5e26\u4e0e\u7ebf\u8def\u3002'},
    {'kw': ['\u6ee1\u683c', '\u4fe1\u53f7\u6ee1'],
     'msg': '\u4fe1\u53f7\u6ee1\u683c\u53ea\u4ee3\u8868\u5f3a\u5ea6\uff0c\u4e0d\u4ee3\u8868\u4fe1\u9053\u5e72\u51c0\uff0c\u6ee1\u683c\u5374\u6162\u6070\u6070\u662f\u5e72\u6270\u6216\u62e5\u585e\u7684\u5178\u578b\u8868\u73b0\u3002'},
    {'kw': ['40MHz', '40\u5146', '\u9891\u5bbd'],
     'msg': '2.4G \u8bbe 40MHz \u51e0\u4e4e\u5fc5\u7136\u4e0e\u90bb\u5c45\u91cd\u53e0\uff0c\u5b9e\u6d4b\u901a\u5e38\u66f4\u6162\u66f4\u4e0d\u7a33\uff0c\u5e94\u6539\u56de 20MHz\u3002'},
    {'kw': ['\u6362\u4fe1\u9053', '\u4fe1\u9053\u6ca1\u7528', '\u6ca1\u6548\u679c'],
     'msg': '\u6362\u4fe1\u9053\u6ca1\u6548\u679c\u53ef\u80fd\u662f\u975e WiFi \u5e72\u6270\u6e90\uff0c\u5fae\u6ce2\u7089\u4e0e\u65e0\u7ef3\u7535\u8bdd\u7684\u5e72\u6270\u626b\u63cf\u8f6f\u4ef6\u770b\u4e0d\u5230\u3002'},
    {'kw': ['\u665a\u4e0a', '\u9ad8\u5cf0'],
     'msg': '\u665a\u9ad8\u5cf0\u53d8\u6162\u662f\u62e5\u585e\u7684\u76f4\u63a5\u8bc1\u636e\uff0c\u4e0e\u90bb\u5c45\u4f7f\u7528\u65f6\u6bb5\u76f8\u5173\u3002'},
    {'kw': ['\u53cc\u9891\u5408\u4e00', '\u5408\u4e00'],
     'msg': '\u53cc\u9891\u5408\u4e00\u5e38\u5bfc\u81f4\u7269\u8054\u7f51\u4e0e\u8001\u8bbe\u5907\u627e\u4e0d\u5230\u7f51\u6216\u9891\u7e41\u6389\u7ebf\uff0c\u5efa\u8bae\u5206\u5f00 SSID\u3002'},
]


def norm(s):
    return (s or '').replace(' ', '').replace('\u3000', '')


def match(text, items):
    t = norm(text)
    out = []
    for it in items:
        hits = [k for k in it['kw'] if k in t]
        if hits:
            out.append((it, hits))
    return out


def analyse(text):
    t = norm(text)
    rules = []
    for r in RULES:
        hits = [k for k in r['kw'] if k in t]
        if not hits:
            continue
        level = '\u9ad8' if len(hits) >= 2 else '\u4e2d'
        rules.append({'id': r['id'], 'order': r['order'], 'name': r['name'],
                      'level': level, 'hits': hits, 'test': r['test'], 'fix': r['fix']})
    rules.sort(key=lambda x: x['order'])
    reds = [it['msg'] for it, _ in match(text, RED)]
    miss = [it['msg'] for it, _ in match(text, MISREAD)]
    return {'rules': rules, 'reds': reds, 'misread': miss,
            'top': rules[0]['name'] if rules else ''}


def render_md(text, r):
    lines = ['# WiFi \u6162\u7f51\u5224\u65ad\u7ed3\u679c', '']
    if not r['rules']:
        lines.append('\u672a\u5339\u914d\u5230\u6545\u969c\u6811\u6761\u76ee\u3002\u8bf7\u8865\u5145\uff1a\u6709\u7ebf\u76f4\u8fde\u5feb\u4e0d\u5feb\u3001\u4fe1\u53f7\u51e0\u683c\u3001\u662f\u5168\u5929\u6162\u8fd8\u662f\u665a\u9ad8\u5cf0\u6162\u3002')
        lines.append('')
    else:
        lines.append('\u6700\u4f18\u5148\u6392\u67e5\uff1a%s' % r['top'])
        lines.append('')
        lines.append('## \u4e00\u3001\u6392\u67e5\u987a\u5e8f\uff08\u6309\u6b64\u987a\u5e8f\u6267\u884c\uff09')
        lines.append('')
        lines.append('| \u987a\u5e8f | \u53ef\u80fd\u539f\u56e0 | \u53ef\u80fd\u6027 | \u9a8c\u8bc1\u52a8\u4f5c | \u5904\u7f6e |')
        lines.append('|---|---|---|---|---|')
        for x in r['rules']:
            lines.append('| %d | %s | %s | %s | %s |' % (
                x['order'], x['name'], x['level'], x['test'], x['fix']))
        lines.append('')
    if r['reds']:
        lines.append('## \u4e8c\u3001\u5b89\u5168\u7ea2\u7ebf\uff08\u7acb\u5373\u6267\u884c\uff09')
        lines.append('')
        for m in r['reds']:
            lines.append('- %s' % m)
        lines.append('')
    if r['misread']:
        lines.append('## \u4e09\u3001\u8bef\u5224\u63d0\u9192')
        lines.append('')
        for m in r['misread']:
            lines.append('- %s' % m)
        lines.append('')
    lines.append('## \u56db\u3001\u56db\u6b65\u5b9a\u6027\uff08\u6539\u8bbe\u7f6e\u524d\u5fc5\u505a\uff09')
    lines.append('')
    lines.append('1. \u6709\u7ebf\u76f4\u8fde\u6d4b\u901f\uff1a\u6392\u9664\u5bbd\u5e26\u4e0e\u7ebf\u8def\u95ee\u9898')
    lines.append('2. \u8fd1\u573a\u6d4b\u901f\uff1a\u533a\u5206\u8986\u76d6\u4e0e\u5e72\u6270')
    lines.append('3. \u5206\u65f6\u6bb5\u6d4b\u901f\uff1a\u767d\u5929\u4e0e\u665a\u9ad8\u5cf0\u5404\u4e09\u6b21')
    lines.append('4. \u5206\u9891\u6bb5\u6d4b\u901f\uff1a2.4G \u4e0e 5G \u5404\u4e09\u6b21')
    lines.append('')
    lines.append('---')
    lines.append('\u672c\u7ed3\u679c\u4e3a\u73b0\u8c61\u5339\u914d\u4e0e\u6392\u67e5\u987a\u5e8f\u5efa\u8bae\uff0c\u4e0d\u4ee3\u8868\u73b0\u573a\u5224\u65ad\uff0c\u4e0d\u6784\u6210\u7f51\u7edc\u5de5\u7a0b\u7ed3\u8bba\u3002')
    return '\n'.join(lines)


def render_json(r):
    return json.dumps(r, ensure_ascii=False, indent=2)


def selftest():
    errs = []

    def eq(name, got, want):
        if got != want:
            errs.append('%s got=%r want=%r' % (name, got, want))

    r1 = analyse('\u6709\u7ebf\u4e5f\u6162\uff0c\u63d2\u7f51\u7ebf\u4e5f\u662f\u8fd9\u4e2a\u901f\u5ea6')
    eq('case1 \u7ebf\u8def\u4f18\u5148', r1['rules'][0]['id'], 'W1')
    eq('case1 \u7ea2\u7ebf\u547d\u4e2d', len(r1['reds']) >= 1, True)

    r2 = analyse('\u4fe1\u53f7\u6ee1\u683c\u4f46\u7f51\u901f\u6162\uff0c\u665a\u4e0a\u7279\u522b\u5361')
    eq('case2 \u4fe1\u9053\u5e72\u6270\u547d\u4e2d', any(x['id'] == 'W4' for x in r2['rules']), True)
    eq('case2 \u6ee1\u683c\u8bef\u5224', any('\u6ee1\u683c' in m for m in r2['misread']), True)

    r3 = analyse('2.4G \u8bbe\u4e86 40MHz\uff0c\u9891\u5bbd\u8981\u6539\u5417')
    eq('case3 \u5bbd\u5ea6\u547d\u4e2d', any(x['id'] == 'W5' for x in r3['rules']), True)
    eq('case3 \u5bbd\u5ea6\u8bef\u5224', any('40MHz' in m for m in r3['misread']), True)

    r4 = analyse('\u667a\u80fd\u63d2\u5ea7\u603b\u6389\u7ebf\uff0c\u5f00\u4e86\u53cc\u9891\u5408\u4e00')
    eq('case4 \u5408\u4e00\u547d\u4e2d', any(x['id'] == 'W7' for x in r4['rules']), True)

    r5 = analyse('\u8def\u7531\u5668\u5728\u5f31\u7535\u7bb1\u91cc\uff0c\u9c7c\u7f38\u65c1\u8fb9')
    eq('case5 \u6446\u653e\u547d\u4e2d', any(x['id'] == 'W9' for x in r5['rules']), True)

    r6 = analyse('\u5149\u732b\u4eae\u7ea2\u706f\uff0c\u60f3\u6539\u6865\u63a5')
    eq('case6 \u5149\u732b\u7ea2\u7ebf', any('\u5149\u732b\u6ce8\u518c\u4e0e\u8ba4\u8bc1\u53c2\u6570' in m for m in r6['reds']), True)

    r7 = analyse('\u5367\u5ba4\u9694\u5899\u6ca1\u4fe1\u53f7\uff0c\u53ea\u6709\u4e00\u683c')
    eq('case7 \u8986\u76d6\u4f18\u5148', r7['rules'][0]['id'], 'W2')

    r8 = analyse('\u7f51\u7edc\u6709\u70b9\u95ee\u9898')
    eq('case8 \u65e0\u5339\u914d', r8['rules'], [])

    md = render_md('\u4fe1\u53f7\u6ee1\u683c\u4f46\u7f51\u901f\u6162', r2)
    eq('case9 \u8f93\u51fa\u8868\u5934', md.startswith('# '), True)
    js = json.loads(render_json(r1))
    eq('case10 \u8f93\u51fa\u952e', sorted(js.keys()), ['misread', 'reds', 'rules', 'top'])

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 13\n\u8986\u76d6: \u7ebf\u8def\u95ee\u9898/\u8986\u76d6\u4e0d\u8db3/2.4G\u62e5\u585e/\u4fe1\u9053\u91cd\u53e0/\u9891\u5bbd\u8bbe\u7f6e/\u975eWiFi\u5e72\u6270/\u53cc\u9891\u5408\u4e00/\u7ec8\u7aef\u8001\u65e7/\u6446\u653e\u4e0d\u5f53/\u591aAP')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='WiFi \u6162\u7f51\u6545\u969c\u6811\u5224\u65ad')
    ap.add_argument('--text', help='\u73b0\u8c61\u63cf\u8ff0')
    ap.add_argument('--file', help='\u4ece\u6587\u4ef6\u8bfb\u73b0\u8c61\u63cf\u8ff0')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'])
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    text = a.text or ''
    if a.file:
        if not os.path.exists(a.file):
            print('ERROR --file \u4e0d\u5b58\u5728')
            return 2
        text = open(a.file, 'r', encoding='utf-8', errors='replace').read()
    if not text.strip():
        print('ERROR \u9700\u8981 --text \u6216 --file')
        return 2

    r = analyse(text)
    out = render_md(text, r) if a.format == 'md' else render_json(r)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % a.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
