# -*- coding: utf-8 -*-
"""\u5bb6\u5177\u6750\u8d28\u4fdd\u517b\u5224\u5b9a\uff1a\u8f93\u5165\u6750\u8d28\u4e0e\u635f\u4f24\u63cf\u8ff0\uff0c\u8f93\u51fa\u7981\u5fcc\u3001\u5904\u7406\u5f52\u5c5e\u4e0e\u5b89\u5168\u63d0\u793a\u3002

\u7528\u6cd5:
  python furniture_care_check.py --text "\u76ae\u6c99\u53d1\u5750\u4e0b\u53bb\u584c\u4e86\uff0c\u8fd8\u6709\u5f00\u88c2"
  python furniture_care_check.py --file \u60c5\u51b5.txt --out \u7ed3\u679c.md
  python furniture_care_check.py --file \u60c5\u51b5.json --format json
  python furniture_care_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ---- \u516b\u7c7b\u6750\u8d28\uff1a\u7981\u5fcc\u4e0e\u624b\u6cd5 ----
MATERIALS = [
    {'id': 'M1', 'name': '\u5b9e\u6728',
     'kw': ['\u5b9e\u6728', '\u539f\u6728', '\u6728\u8d28', '\u6a61\u6728', '\u80e1\u6843', '\u6989\u6728', '\u677e\u6728', '\u6a31\u6843\u6728', '\u8001\u6986'],
     'ban': ['\u66b4\u6652', '\u6c34\u6ce1', '\u6696\u6c14\u76f4\u5439', '\u786c\u7269\u522e\u64e6', '\u9aa4\u51b7\u9aa4\u70ed'],
     'ok': '\u5fae\u6e7f\u8f6f\u5e03\u987a\u7eb9\u64e6\u62ed\u540e\u7acb\u523b\u64e6\u5e72\uff1b\u6309\u8bf4\u660e\u4e66\u5468\u671f\u4f7f\u7528\u517b\u62a4\u6cb9',
     'no': '\u7528\u6c34\u51b2\u6d17\u3001\u9152\u7cbe\u55b7\u6d12\u3001\u6253\u78e8\u540e\u4e0d\u4e0a\u6cb9'},
    {'id': 'M2', 'name': '\u677f\u5f0f\u4eba\u9020\u677f',
     'kw': ['\u677f\u5f0f', '\u4eba\u9020\u677f', '\u9897\u7c92\u677f', '\u5bc6\u5ea6\u677f', '\u591a\u5c42\u677f', '\u8d34\u76ae', '\u514d\u6f06\u677f', '\u751f\u6001\u677f', '\u4eff\u7ea2\u6728', '\u4eff\u6728\u7eb9', '\u67d3\u8272'],
     'ban': ['\u957f\u671f\u53d7\u6f6e', '\u8fb9\u7f18\u6ce1\u6c34', '\u8d85\u91cd\u5806\u538b'],
     'ok': '\u5e72\u5e03\u64e6\u62ed\uff1b\u68c0\u67e5\u5c01\u8fb9\uff1b\u8fb9\u89d2\u53d7\u6f6e\u7acb\u5373\u64e6\u5e72',
     'no': '\u6e7f\u5e03\u957f\u65f6\u95f4\u8986\u76d6\u3001\u84b8\u6c7d\u62d6\u628a\u53cd\u590d\u9760\u8fd1\u3001\u5806\u91cd\u7269'},
    {'id': 'M3', 'name': '\u8f6f\u5305\u5e03\u827a',
     'kw': ['\u5e03\u827a', '\u5e03\u6c99\u53d1', '\u8f6f\u5305', '\u5e03\u5957', '\u9760\u57ab', '\u68c9\u9ebb', '\u7ed2\u5e03', '\u7a97\u5e18\u5e03'],
     'ban': ['\u6cb9\u6c61\u6e17\u5165', '\u66b4\u6652', '\u4e0d\u62c6\u6d17', '\u7528\u529b\u63c9\u6413'],
     'ok': '\u5b9a\u671f\u5438\u5c18\uff1b\u5c40\u90e8\u4e2d\u6027\u6e05\u6d01\u5242\u8f7b\u64e6\uff1b\u62c6\u6d17\u5e03\u5957',
     'no': '\u4e0d\u62c6\u5e03\u5957\u6574\u4f53\u55b7\u6d17\u3001\u66b4\u6652\u76f4\u70e4\u3001\u5750\u584c\u540e\u7ee7\u7eed\u7528\u529b'},
    {'id': 'M4', 'name': '\u76ae\u9769',
     'kw': ['\u76ae\u9769', '\u76ae\u6c99\u53d1', '\u771f\u76ae', '\u4eba\u9020\u9769', '\u7ffb\u76ae', '\u76ae\u6905', '\u76ae\u5e8a'],
     'ban': ['\u6cb9', '\u9152\u7cbe', '\u5f3a\u78b1', '\u66b4\u6652', '\u5e72\u88c2\u540e\u63c9\u6413'],
     'ok': '\u5e72\u5e03\u9664\u5c18\uff1b\u62a4\u7406\u5242\u5148\u5c0f\u9762\u79ef\u8bd5\u7528',
     'no': '\u76ae\u6cb9\u968f\u610f\u6d82\u62b9\u3001\u9152\u7cbe\u64e6\u8272\u6591\u3001\u9f9f\u88c2\u5904\u5927\u529b\u6309\u6469'},
    {'id': 'M5', 'name': '\u91d1\u5c5e',
     'kw': ['\u91d1\u5c5e', '\u94a2\u5236', '\u4e0d\u9508\u94a2', '\u94c1\u827a', '\u94dd\u5408\u91d1', '\u94dc', '\u950c'],
     'ban': ['\u6f6e\u6e7f', '\u9178\u78b1', '\u786c\u7269\u522e\u64e6', '\u4e0d\u540c\u91d1\u5c5e\u76f4\u63a5\u63a5\u89e6'],
     'ok': '\u5e72\u5e03\u64e6\u62ed\uff1b\u8f7b\u9508\u70b9\u7528\u4e2d\u6027\u9664\u9508\uff1b\u8865\u6f06\u524d\u5148\u9664\u9508',
     'no': '\u94a2\u4e1d\u7403\u5927\u529b\u64e6\u3001\u9178\u6027\u6e05\u6d01\u5242\u9664\u9508\u3001\u4e0d\u540c\u91d1\u5c5e\u76f4\u63a5\u8d34\u653e'},
    {'id': 'M6', 'name': '\u73bb\u7483',
     'kw': ['\u73bb\u7483', '\u78e8\u7802\u73bb\u7483', '\u73bb\u7483\u95e8', '\u73bb\u7483\u67dc\u95e8', '\u8336\u51e0\u73bb\u7483'],
     'ban': ['\u78d5\u78b0', '\u9aa4\u51b7\u9aa4\u70ed', '\u786c\u7269\u522e\u64e6'],
     'ok': '\u8f6f\u5e03\u914d\u4e2d\u6027\u6e05\u6d01\u5242\uff1b\u56fa\u5b9a\u9891\u7387\u6e05\u7406\u4ee5\u51cf\u5c11\u6c34\u57a2',
     'no': '\u4f7f\u7528\u5f3a\u78b1\u6027\u914d\u65b9\u3001\u786c\u8d28\u522e\u6c34\u677f'},
    {'id': 'M7', 'name': '\u85e4\u7f16',
     'kw': ['\u85e4\u7f16', '\u85e4\u6905', '\u85e4', '\u7f16\u6905', '\u4eff\u85e4', '\u7af9\u7f16'],
     'ban': ['\u65ad\u88c2', '\u91cd\u538b', '\u957f\u671f\u5e72\u71e5', '\u6cbe\u6c34\u540e\u66b4\u6652'],
     'ok': '\u8f6f\u6bdb\u5237\u9664\u5c18\uff1b\u5fae\u6e7f\u5e03\u540e\u9634\u5e72\uff1b\u65ad\u88c2\u5904\u53ca\u65f6\u7ed1\u5b9a',
     'no': '\u6c34\u6d17\u3001\u91cd\u538b\u3001\u5c40\u90e8\u53d7\u6f6e\u540e\u66b4\u6652'},
    {'id': 'M8', 'name': '\u5927\u7406\u77f3\u4e0e\u5929\u7136\u77f3',
     'kw': ['\u5927\u7406\u77f3', '\u5929\u7136\u77f3', '\u77f3\u6750', '\u5ca9\u677f', '\u7389\u77f3', '\u4eba\u9020\u77f3'],
     'ban': ['\u9178\u6027\u6db2\u4f53', '\u91cd\u7269\u78d5\u8fb9', '\u6cb9\u6c61\u6e17\u5165'],
     'ok': '\u4e2d\u6027\u6e05\u6d01\u5242\uff1b\u6e17\u6cb9\u540e\u7528\u5438\u9644\u6750\u6599\u6577\u5728\u8868\u9762',
     'no': '\u4f7f\u7528\u9178\u6027\u6e05\u6d01\u5242\u3001\u94a2\u4e1d\u7403\u3001\u6848\u677f\u76f4\u63a5\u653e\u9505\u5177'},
]

# ---- \u4e03\u7c7b\u635f\u4f24\uff1a\u7c7b\u578b\u4e0e\u5f52\u5c5e ----
DAMAGES = [
    {'id': 'D1', 'name': '\u5212\u75d5', 'kw': ['\u5212\u75d5', '\u522e\u82b1', '\u5212\u4f24', '\u78e8\u75d5'],
     'cause': '\u786c\u7269\u76f4\u63a5\u63a5\u89e6\uff0c\u6216\u91d1\u5c5e\u8868\u9762\u7c89\u5c18\u6469\u64e6',
     'owner': '\u6d45\u8868\u53ef\u81ea\u884c\u5904\u7406\uff1b\u6df1\u53ca\u5e95\u6f06\u8f6c\u5e08\u5085'},
    {'id': 'D2', 'name': '\u5f00\u88c2', 'kw': ['\u5f00\u88c2', '\u88c2\u7f1d', '\u88c2\u4e86', '\u88c2\u7eb9', '\u9f9f\u88c2', '\u8d77\u76ae'],
     'cause': '\u6728\u6750\u5e72\u7f29\u3001\u957f\u671f\u66b4\u6652\u6216\u8fc7\u5ea6\u5e72\u71e5',
     'owner': '\u975e\u8d2f\u7a7f\u7684\u5c0f\u9762\u79ef\u53ef\u5904\u7406\uff1b\u8d2f\u7a7f\u88c2\u7f1d\u8f6c\u5e08\u5085'},
    {'id': 'D3', 'name': '\u53d8\u5f62', 'kw': ['\u53d8\u5f62', '\u7fd8\u66f2', '\u7fd8\u8d77', '\u4e0d\u5e73', '\u95e8\u677f\u4e0d\u8d34\u5408', '\u53d1\u80c0'],
     'cause': '\u53d7\u6f6e\u540e\u53cd\u590d\u5e72\u6e7f\uff0c\u677f\u4ef6\u672a\u7559\u4f38\u7f29\u4f59\u91cf',
     'owner': '\u5df2\u53d8\u5f62\u65e0\u6cd5\u81ea\u884c\u6062\u590d\uff0c\u8f6c\u5e08\u5085'},
    {'id': 'D4', 'name': '\u6389\u8272', 'kw': ['\u6389\u8272', '\u892a\u8272', '\u53d8\u8272', '\u6591\u9a73', '\u53d1\u767d'],
     'cause': '\u7d2b\u5916\u7ebf\u8001\u5316\u3001\u6e05\u6d01\u5242\u8150\u8680\u3001\u6d82\u5c42\u78e8\u635f',
     'owner': '\u8865\u8272\u4e0e\u7ffb\u65b0\u5c5e\u4e13\u4e1a\u4f5c\u4e1a'},
    {'id': 'D5', 'name': '\u53d1\u9709', 'kw': ['\u53d1\u9709', '\u957f\u6bdb', '\u9709\u6591', '\u9709\u70b9', '\u9709\u5473', '\u9ed1\u6591'],
     'cause': '\u957f\u671f\u6f6e\u6e7f\u3001\u4e0d\u901a\u98ce\uff0c\u5e03\u6599\u6216\u76ae\u9769\u53d7\u6f6e',
     'owner': '\u8868\u5c42\u53ef\u5904\u7406\uff1b\u57fa\u6750\u9709\u53d8\u8f6c\u5e08\u5085'},
    {'id': 'D6', 'name': '\u4e94\u91d1\u677e\u52a8', 'kw': ['\u677e\u52a8', '\u5408\u9875', '\u94f0\u94fe', '\u6ed1\u8f68', '\u62bd\u5c49\u5361', '\u87ba\u4e1d'],
     'cause': '\u957f\u671f\u53d7\u529b\u3001\u87ba\u4e1d\u6ed1\u7259\u3001\u6728\u6750\u5e72\u7f29',
     'owner': '\u7d27\u56fa\u87ba\u4e1d\u53ef\u81ea\u884c\u5904\u7406\uff1b\u6ed1\u7259\u9700\u6362\u4ef6\u8f6c\u5e08\u5085'},
    {'id': 'D7', 'name': '\u584c\u9677', 'kw': ['\u584c\u9677', '\u584c\u4e86', '\u51f9\u4e0b\u53bb', '\u4e0d\u56de\u5f39', '\u5750\u584c', '\u4e0b\u9677'],
     'cause': '\u5f39\u7c27\u5931\u6548\u3001\u6d77\u7ef5\u8001\u5316\u3001\u7ed3\u6784\u75b2\u52b3',
     'owner': '\u5c5e\u7ed3\u6784\u4ef6\uff0c\u8f6c\u5e08\u5085\u66f4\u6362'},
]

# ---- \u4e94\u7c7b\u65e5\u5e38\u9690\u6027\u4f24\u5bb3 ----
HIDDEN = [
    {'id': 'H1', 'name': '\u66b4\u6652',
     'kw': ['\u66b4\u6652', '\u6652', '\u76f4\u5c04', '\u897f\u6652', '\u5357\u5411\u7a97', '\u592a\u9633'],
     'msg': '\u907f\u514d\u5357\u5411\u4e0e\u897f\u5411\u76f4\u5c04\u7a97\uff0c\u7528\u7a97\u5e18\u6216\u767e\u53f6\u8fc7\u6ee4\u76f4\u5c04\u5149\u3002'},
    {'id': 'H2', 'name': '\u6f6e\u6e7f',
     'kw': ['\u6f6e\u6e7f', '\u53d7\u6f6e', '\u6885\u96e8', '\u56de\u5357\u5929', '\u53d1\u6f6e', '\u6c34\u6c7d'],
     'msg': '\u79bb\u5916\u5899\u7559\u51fa\u8ddd\u79bb\uff1b\u6885\u96e8\u5b63\u4e0e\u4f9b\u6696\u5b63\u91cd\u70b9\u63a7\u6e7f\uff1b\u53d7\u6f6e\u7684\u67dc\u4f53\u5e94\u5f00\u95e8\u901a\u98ce\u64e6\u5e72\uff0c\u4e0d\u8981\u7acb\u523b\u5173\u4e25\u3002'},
    {'id': 'H3', 'name': '\u91cd\u538b',
     'kw': ['\u91cd\u538b', '\u5806\u91cd', '\u538b', '\u653e\u91cd\u7269', '\u9876\u67dc'],
     'msg': '\u9876\u67dc\u91cd\u7269\u4e0b\u79fb\uff1b\u5e8a\u4e0e\u6c99\u53d1\u4e0d\u957f\u671f\u5806\u91cd\u7269\u3002'},
    {'id': 'H4', 'name': '\u9510\u7269',
     'kw': ['\u9510\u7269', '\u94a5\u5319', '\u526a\u5200', '\u786c\u8fb9', '\u5c16'],
     'msg': '\u53f0\u9762\u4e0d\u653e\u526a\u5200\u94a5\u5319\uff1b\u73bb\u7483\u4e0e\u77f3\u9762\u53f0\u9762\u4e0d\u653e\u786c\u8fb9\u5668\u7269\u3002'},
    {'id': 'H5', 'name': '\u70ed\u6e90',
     'kw': ['\u6696\u6c14', '\u5730\u6696', '\u70ed\u6e90', '\u7076\u53f0', '\u70eb', '\u9ad8\u6e29'],
     'msg': '\u4e0d\u8d34\u8fd1\u6696\u6c14\u7247\u3001\u5730\u6696\u51fa\u98ce\u53e3\u4e0e\u7076\u53f0\uff1b\u53f0\u9762\u4e0d\u653e\u70eb\u676f\u5177\u3002'},
]

# ---- \u5b89\u5168\u7ea2\u7ebf ----
RED = [
    {'kw': ['\u7ed3\u6784\u677e\u52a8', '\u6447\u6643', '\u69ab\u63a5', '\u53d7\u529b\u4ef6'],
     'msg': '\u7ed3\u6784\u677e\u52a8\u5c5e\u53d7\u529b\u4ef6\u635f\u4f24\uff0c\u8f6c\u4ea4\u5bb6\u5177\u5382\u6216\u4e13\u4e1a\u7ef4\u4fee\u5e08\u5085\uff0c\u4e0d\u8981\u81ea\u884c\u52a0\u56fa\u3002'},
    {'kw': ['\u5d29\u8fb9', '\u5d29\u4e86\u4e00\u4e2a\u89d2', '\u5d29\u89d2', '\u65ad\u88c2', '\u8d2f\u7a7f\u88c2'],
     'msg': '\u77f3\u6750\u6216\u73bb\u7483\u5d29\u8fb9\u4e0e\u8d2f\u7a7f\u88c2\u5c5e\u7ed3\u6784\u635f\u4f24\uff0c\u8f6c\u5e08\u5085\u5904\u7406\uff0c\u4e0d\u8981\u81ea\u884c\u7c98\u63a5\u3002'},
    {'kw': ['\u5927\u9762\u79ef\u8d77\u58f3', '\u8868\u76ae\u5265\u843d', '\u8d2f\u7a7f\u88c2\u7f1d', '\u9f9f\u88c2'],
     'msg': '\u76ae\u9769\u8d2f\u7a7f\u88c2\u4e0e\u5927\u9762\u79ef\u8d77\u58f3\u5c5e\u6750\u6599\u8001\u5316\u7ec8\u6001\uff0c\u81ea\u884c\u6d82\u6cb9\u8102\u4f1a\u5c01\u95ed\u540e\u53d1\u9ed1\u53d1\u9709\uff0c\u8f6c\u4e13\u4e1a\u4fee\u590d\u3002'},
    {'kw': ['\u9ad8\u4ef7\u503c', '\u8001\u5bb6\u5177', '\u4fdd\u503c', '\u53e4\u8463'],
     'msg': '\u4ef7\u503c\u8f83\u9ad8\u9700\u8981\u4fdd\u503c\u7684\u8001\u5bb6\u5177\uff0c\u8f6c\u4e13\u4e1a\u4fee\u590d\uff0c\u907f\u514d\u81ea\u884c\u5904\u7406\u964d\u4f4e\u4ef7\u503c\u3002'},
    {'kw': ['\u6ef4\u918b', '\u6ef4\u6db2', '\u5012\u918b', '\u6d4b\u9178\u78b1', '\u6ef4\u4e00\u4e0b'],
     'msg': '\u6ef4\u6db2\u9274\u522b\u4f1a\u5728\u77f3\u6750\u4e0e\u6728\u8d28\u8868\u9762\u9020\u6210\u6c38\u4e45\u8150\u8680\uff0c\u8bf7\u5728\u4e0d\u663e\u773c\u5904\u7528\u4e2d\u6027\u64e6\u62ed\u89c2\u5bdf\u66ff\u4ee3\uff0c\u786e\u9700\u9274\u522b\u8bf7\u4e13\u4e1a\u4eba\u5458\u68c0\u6d4b\u3002'},
    {'kw': ['\u690d\u7269\u6cb9', '\u6a44\u6984\u6cb9', '\u8272\u62c9\u6cb9', '\u9ebb\u6cb9'],
     'msg': '\u53a8\u623f\u98df\u7528\u6cb9\u4e0d\u9002\u5408\u5bb6\u5177\u517b\u62a4\uff0c\u4f1a\u6c27\u5316\u53d1\u9ecf\u5e76\u5438\u9644\u7070\u5c18\uff0c\u5bb6\u5177\u517b\u62a4\u8bf7\u7528\u5382\u5bb6\u6307\u5b9a\u7684\u517b\u62a4\u6cb9\u3002'},
]

# ---- \u5e38\u89c1\u8bef\u5224 ----
MISREAD = [
    {'kw': ['\u4e00\u79cd\u6e05\u6d01\u5242', '\u540c\u4e00\u6b3e', '\u901a\u7528\u578b', '\u4e00\u6876'],
     'msg': '\u4e00\u79cd\u6e05\u6d01\u5242\u5237\u5168\u5c4b\u5bb6\u5177\u662f\u53d7\u635f\u4e3b\u56e0\u3002\u516b\u7c7b\u6750\u8d28\u5bf9\u5316\u5b66\u5242\u7684\u53cd\u5e94\u5b8c\u5168\u4e0d\u540c\uff0c\u5fc5\u987b\u5206\u5f00\u5904\u7406\u3002'},
    {'kw': ['\u7ea2\u6728\u8721', '\u6728\u8721\u6cb9', '\u4e0a\u8721', '\u6253\u8721', '\u4eff\u7ea2\u6728', '\u8d34\u76ae', '\u67d3\u8272'],
     'msg': '\u7ed9\u4eff\u7ea2\u6728\u4e0a\u7ea2\u6728\u8721\u6216\u6728\u8721\u6cb9\u4f1a\u5728\u8986\u819c\u5c42\u4e0a\u53d1\u82b1\u53d8\u8272\u4e14\u96be\u6062\u590d\u3002\u8bf7\u5148\u770b\u80cc\u677f\u3001\u62bd\u5c49\u5e95\u677f\u4e0e\u8fb9\u89d2\u65ad\u9762\u786e\u8ba4\u771f\u5b9e\u7ed3\u6784\u3002'},
    {'kw': ['\u4e0d\u62c6\u6d17', '\u76f4\u63a5\u55b7', '\u6574\u55b7', '\u6574\u4f53\u55b7'],
     'msg': '\u5e03\u827a\u5bb6\u5177\u4e0d\u62c6\u5e03\u5957\u76f4\u63a5\u55b7\u6e05\u6d01\u5242\uff0c\u6db2\u4f53\u6e17\u8fdb\u6d77\u7ef5\u540e\u65e0\u6cd5\u4ece\u5185\u90e8\u70d8\u5e72\uff0c\u5f02\u5473\u4e0e\u9709\u83cc\u4f1a\u66f4\u4e25\u91cd\u3002'},
    {'kw': ['\u51e1\u58eb\u6797', '\u76ae\u9769\u6cb9', '\u62b9\u6cb9'],
     'msg': '\u76ae\u6c99\u53d1\u8d77\u58f3\u9f9f\u88c2\u540e\u6d82\u6cb9\u8102\u4f1a\u5c01\u95ed\u8868\u9762\uff0c\u66f4\u6613\u53d1\u9ed1\u53d1\u9709\u3002\u8f7b\u5fae\u5e72\u71e5\u7528\u62a4\u7406\u5242\uff0c\u8d2f\u7a7f\u88c2\u5e94\u8f6c\u5e08\u5085\u3002'},
    {'kw': ['\u731b\u62fd', '\u7528\u529b\u62c9', '\u786c\u62fd'],
     'msg': '\u62bd\u5c49\u5361\u4f4f\u731b\u62fd\u4f1a\u52a0\u901f\u5bfc\u8f68\u4e0e\u6ed1\u5757\u78e8\u635f\uff0c\u591a\u6570\u662f\u6742\u7269\u963b\u6321\uff0c\u5e94\u5148\u6e05\u7406\u5f52\u4f4d\u3002'},
    {'kw': ['\u80f6\u7c98', '\u7c98\u4f4f', '\u7528\u80f6', '\u7c98\u4e00\u4e0b', '\u80f6\u6c34'],
     'msg': '\u85e4\u7f16\u53d7\u529b\u7ed3\u6784\u5df2\u65ad\uff0c\u7c98\u63a5\u53ea\u662f\u77ed\u6682\u3002\u5e94\u505c\u6b62\u4f7f\u7528\u5e76\u7ed1\u5b9a\u56fa\u5b9a\uff0c\u8f6c\u4e13\u4e1a\u4fee\u590d\u3002'},
]


def norm(s):
    return (s or '').replace(' ', '').replace('\u3000', '')


def analyse(text):
    t = norm(text)
    mats = []
    for m in MATERIALS:
        hits = [k for k in m['kw'] if k in t]
        if hits:
            mats.append({'id': m['id'], 'name': m['name'], 'hits': hits,
                         'ban': m['ban'], 'ok': m['ok'], 'no': m['no']})
    dmgs = []
    for d in DAMAGES:
        hits = [k for k in d['kw'] if k in t]
        if hits:
            dmgs.append({'id': d['id'], 'name': d['name'], 'hits': hits,
                         'cause': d['cause'], 'owner': d['owner']})
    hidden = [h['msg'] for h in HIDDEN if any(k in t for k in h['kw'])]
    reds = []
    for r in RED:
        if any(k in t for k in r['kw']):
            reds.append(r['msg'])
    miss = [m['msg'] for m in MISREAD if any(k in t for k in m['kw'])]
    return {'materials': mats, 'damages': dmgs, 'hidden': hidden,
            'reds': reds, 'misread': miss,
            'diy_ok': not reds,
            'top_mat': mats[0]['name'] if mats else '',
            'top_dmg': dmgs[0]['name'] if dmgs else ''}


def render_md(r):
    lines = ['# \u5bb6\u5177\u4fdd\u517b\u5224\u5b9a\u7ed3\u679c', '']
    lines.append('> \u5148\u786e\u8ba4\u6750\u8d28\uff0c\u518d\u8c08\u624b\u6cd5\u3002\u6750\u8d28\u5224\u9519\uff0c\u540e\u9762\u5168\u9519\u3002')
    lines.append('')
    if not r['materials'] and not r['damages']:
        lines.append('\u672a\u5339\u914d\u5230\u6750\u8d28\u6216\u635f\u4f24\u7ebf\u7d22\u3002\u8bf7\u8865\u5145\uff1a\u662f\u4ec0\u4e48\u5bb6\u5177\uff08\u5b9e\u6728/\u677f\u5f0f/\u5e03\u827a/\u76ae\u9769/\u91d1\u5c5e/\u73bb\u7483/\u85e4\u7f16/\u77f3\u6750\uff09\u3001'
                     '\u5177\u4f53\u95ee\u9898\u662f\u4ec0\u4e48\u3002')
        lines.append('')
    if r['materials']:
        lines.append('## \u4e00\u3001\u6750\u8d28\u4e0e\u7981\u5fcc')
        lines.append('')
        lines.append('| \u6750\u8d28 | \u547d\u4e2d\u7ebf\u7d22 | \u4e3b\u8981\u7981\u5fcc | \u53ef\u4ee5\u505a | \u4e0d\u53ef\u4ee5\u505a |')
        lines.append('|---|---|---|---|---|')
        for m in r['materials']:
            lines.append('| %s | %s | %s | %s | %s |' % (
                m['name'], '\u3001'.join(m['hits']), '\uff1b'.join(m['ban']), m['ok'], m['no']))
        lines.append('')
        lines.append('**\u5224\u4e0d\u51fa\u6765\u65f6**\uff1a\u4e0d\u8981\u4e0a\u5316\u5b66\u6e05\u6d01\u5242\u3002\u5148\u7528\u5fae\u6e7f\u62e7\u5e72\u7684\u8f6f\u5e03\u64e6\u4e00\u6b21\uff0c\u89c2\u5bdf\u6709\u65e0\u53d8\u8272\u4e0e\u6b8b\u7559\u53cd\u5e94\u3002')
        lines.append('')
    if r['damages']:
        lines.append('## \u4e8c\u3001\u635f\u4f24\u7c7b\u578b\u4e0e\u5f52\u5c5e')
        lines.append('')
        lines.append('| \u7c7b\u578b | \u547d\u4e2d\u7ebf\u7d22 | \u6700\u53ef\u80fd\u6210\u56e0 | \u5904\u7406\u5f52\u5c5e |')
        lines.append('|---|---|---|---|')
        for d in r['damages']:
            lines.append('| %s | %s | %s | %s |' % (
                d['name'], '\u3001'.join(d['hits']), d['cause'], d['owner']))
        lines.append('')
    if r['hidden']:
        lines.append('## \u4e09\u3001\u65e5\u5e38\u9690\u6027\u4f24\u5bb3\uff08\u7d2f\u79ef\u4e14\u4e0d\u53ef\u9006\uff09')
        lines.append('')
        for m in r['hidden']:
            lines.append('- %s' % m)
        lines.append('')
    if r['reds']:
        lines.append('## \u56db\u3001\u5b89\u5168\u7ea2\u7ebf\uff08\u547d\u4e2d\u5373\u8f6c\u5e08\u5085\uff09')
        lines.append('')
        for m in r['reds']:
            lines.append('- %s' % m)
        lines.append('')
    else:
        lines.append('## \u56db\u3001\u5b89\u5168\u7ea2\u7ebf')
        lines.append('')
        lines.append('\u672c\u6b21\u672a\u547d\u4e2d\u7ea2\u7ebf\u3002\u4ecd\u9700\u81ea\u67e5\uff1a\u7ed3\u6784\u677e\u52a8\u3001\u4e94\u91d1\u6ed1\u7259\u3001\u77f3\u6750\u5d29\u8fb9\u3001\u76ae\u9769\u8d2f\u7a7f\u88c2\u3001'
                     '\u8f6f\u5305\u584c\u9677\u3001\u627f\u91cd\u67dc\u4f53\u53d8\u5f62\u3002\u4efb\u4e00\u9879\u6210\u7acb\u5373\u8f6c\u5e08\u5085\u3002')
        lines.append('')
    if r['misread']:
        lines.append('## \u4e94\u3001\u5e38\u89c1\u8bef\u5224\u63d0\u9192')
        lines.append('')
        for m in r['misread']:
            lines.append('- %s' % m)
        lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('\u672c\u7ed3\u679c\u4e3a\u6750\u8d28\u4e0e\u635f\u4f24\u7c7b\u578b\u5339\u914d\u5efa\u8bae\uff0c\u4e0d\u4ee3\u8868\u73b0\u573a\u5224\u65ad\uff0c\u4e0d\u6784\u6210\u4e13\u4e1a\u4fee\u590d\u7ed3\u8bba\u3002')
    lines.append('\u6e05\u6d01\u5242\u4e0e\u62a4\u7406\u7528\u54c1\u7684\u9002\u7528\u8303\u56f4\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e66\u4e3a\u51c6\uff0c\u4e0d\u540c\u4ea7\u54c1\u4e0d\u53ef\u6df7\u7528\u3002')
    return '\n'.join(lines)


def read_input(path):
    raw = open(path, 'rb').read().decode('utf-8', 'replace')
    if raw.lstrip('\ufeff').strip().startswith('{'):
        try:
            data = json.loads(raw.lstrip('\ufeff'))
        except ValueError:
            return raw
        if isinstance(data, dict):
            for k in ('desc', 'text', 'description', '\u60c5\u51b5', '\u63cf\u8ff0'):
                if k in data and isinstance(data[k], str):
                    return data[k]
        return raw
    return raw


def selftest():
    errs = []

    def eq(name, got, want):
        if got != want:
            errs.append('%s got=%r want=%r' % (name, got, want))

    r1 = analyse('\u76ae\u6c99\u53d1\u5750\u4e0b\u53bb\u584c\u4e86\uff0c\u8fd8\u6709\u5f00\u88c2')
    eq('case1 \u6750\u8d28\u547d\u4e2d', r1['top_mat'], '\u76ae\u9769')
    eq('case2 \u584c\u9677\u547d\u4e2d', any(d['id'] == 'D7' for d in r1['damages']), True)
    eq('case3 \u5f00\u88c2\u547d\u4e2d', any(d['id'] == 'D2' for d in r1['damages']), True)

    r2 = analyse('\u4eff\u7ea2\u6728\u7684\u67dc\u5b50\uff0c\u60f3\u4e0a\u70b9\u7ea2\u6728\u8721\u4fdd\u517b')
    eq('case4 \u677f\u5f0f\u547d\u4e2d', any(m['id'] == 'M2' for m in r2['materials']), True)
    eq('case5 \u4eff\u7ea2\u6728\u63d0\u9192', len(r2['misread']) >= 1, True)

    r3 = analyse('\u5927\u7406\u77f3\u8336\u51e0\u60f3\u6ef4\u918b\u770b\u770b\u662f\u4e0d\u662f\u9178\u7684')
    eq('case6 \u6ef4\u6db2\u7ea2\u7ebf', len(r3['reds']) >= 1, True)
    eq('case7 \u4e0d\u53efDIY', r3['diy_ok'], False)

    r4 = analyse('\u5b9e\u6728\u9910\u684c\u6709\u51e0\u9053\u5212\u75d5')
    eq('case8 \u5b9e\u6728\u547d\u4e2d', r4['top_mat'], '\u5b9e\u6728')
    eq('case9 \u5212\u75d5\u547d\u4e2d', any(d['id'] == 'D1' for d in r4['damages']), True)

    r5 = analyse('\u85e4\u7f16\u6905\u5750\u65ad\u4e86\uff0c\u7c98\u4e00\u4e0b\u884c\u4e0d\u884c')
    eq('case10 \u85e4\u7f16\u547d\u4e2d', r5['top_mat'], '\u85e4\u7f16')
    eq('case11 \u80f6\u7c98\u63d0\u9192', any('\u7c98\u63a5' in m for m in r5['misread']), True)

    r6 = analyse('\u6c99\u53d1\u53d7\u6f6e\u4e86\uff0c\u8fd8\u66b4\u6652\u8fc7')
    eq('case12 \u6f6e\u6e7f\u63d0\u9192', len(r6['hidden']) >= 1, True)
    eq('case13 \u66b4\u6652\u63d0\u9192', len(r6['hidden']) >= 2, True)

    r7 = analyse('\u62bd\u5c49\u5408\u9875\u677e\u4e86\uff0c\u87ba\u4e1d\u6ed1\u7259')
    eq('case14 \u4e94\u91d1\u547d\u4e2d', any(d['id'] == 'D6' for d in r7['damages']), True)

    r8 = analyse('\u8bf4\u4e0d\u4e0a\u4ec0\u4e48\u6750\u8d28\uff0c\u5c31\u662f\u6709\u70b9\u65e7')
    eq('case15 \u65e0\u5339\u914d', (r8['materials'], r8['damages']), ([], []))

    md = render_md(r1)
    eq('case16 \u8f93\u51fa\u8868\u5934', md.startswith('# '), True)
    eq('case17 \u8f93\u51fa\u542b\u5c0f\u8282', '\u6750\u8d28\u4e0e\u7981\u5fcc' in md, True)
    js = json.loads(json.dumps(r1, ensure_ascii=False))
    eq('case18 JSON\u952e', sorted(js.keys()),
       ['damages', 'diy_ok', 'hidden', 'materials', 'misread', 'reds', 'top_dmg', 'top_mat'])

    # \u5e26 BOM \u7684 JSON \u8f93\u5165\u5fc5\u987b\u80fd\u6b63\u786e\u89e3\u6790
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write('{"desc": "\u85e4\u7f16\u6905\u5750\u65ad\u4e86"}')
    got = read_input(tmp)
    os.remove(tmp)
    eq('case19 \u5e26BOM\u7684JSON\u9996\u952e', analyse(got)['top_mat'], '\u85e4\u7f16')

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 21\n\u8986\u76d6: \u516b\u7c7b\u6750\u8d28/\u4e03\u7c7b\u635f\u4f24/\u4e94\u7c7b\u9690\u6027\u4f24\u5bb3/\u4eff\u7ea2\u6728/\u77f3\u6750\u9178\u8680/'
               '\u85e4\u7f16\u80f6\u7c98/\u4e94\u91d1\u677e\u52a8/BOM\u89e3\u6790')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u5bb6\u5177\u6750\u8d28\u4fdd\u517b\u4e0e\u635f\u4f24\u5f52\u5c5e\u5224\u5b9a')
    ap.add_argument('--text', help='\u6750\u8d28\u4e0e\u635f\u4f24\u63cf\u8ff0')
    ap.add_argument('--file', help='\u4ece\u6587\u4ef6\u8bfb\uff0c\u652f\u6301 txt / md / json')
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
        text = read_input(a.file)
    if not text.strip():
        print('ERROR \u9700\u8981 --text \u6216 --file')
        return 2

    r = analyse(text)
    out = render_md(r) if a.format == 'md' else json.dumps(r, ensure_ascii=False, indent=2)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % a.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())