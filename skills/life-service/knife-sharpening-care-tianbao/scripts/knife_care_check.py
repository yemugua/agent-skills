# -*- coding: utf-8 -*-
"""\u5200\u5177\u4fdd\u517b\u4e0e\u78e8\u5200\u6838\u67e5\uff1a\u6309\u5200\u578b\u7ed9\u51fa\u5203\u53e3\u89d2\u5ea6\u3001\u78e8\u5200\u65b9\u5f0f\u3001\u7981\u5fcc\u4e0e\u4fdd\u517b\u68c0\u67e5\u9879\u3002

\u7528\u6cd5:
  python knife_care_check.py --file knife.json [--out result.md] [--format json]
  python knife_care_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u5200\u578b -> (\u4e2d\u6587\u540d, \u5203\u53e3\u89d2\u5ea6, \u63a8\u8350\u78e8\u5200\u65b9\u5f0f, \u63a8\u8350\u78e8\u6599, \u78e8\u5200\u6ce8\u610f\u4e8b\u9879)
KNIVES = {
    'chinese_cleaver': ('\u4e2d\u5f0f\u7247\u5200', 15, '\u78e8\u5200\u77f3', '\u7ec6\u76ee\u4e0e\u7c97\u76ee\u914d\u5408',
                   '\u5203\u53e3\u8584\uff0c\u5e73\u63a8\u8f7b\u78e8\uff1b\u53ea\u7528\u78e8\u5200\u77f3\uff0c\u5fcc\u7528\u78e8\u5200\u68d2\u786c\u522e'),
    'japanese_gyuto': ('\u65e5\u5f0f\u4e3b\u53a8\u5200', 15, '\u78e8\u5200\u77f3', '\u7ec6\u76ee 1000 \u81f3 3000',
                  '\u5355\u5203\u7ed3\u6784\uff0c\u53ea\u78e8\u4e3b\u5203\uff0c\u51f9\u5203\u4fa7\u4e0d\u8981\u78e8\u51fa\u659c\u9762'),
    'gyuto_alt': ('\u65e5\u5f0f\u4e3b\u53a8\u5200\uff0815 \u5ea6\u578b\uff09', 15, '\u78e8\u5200\u77f3', '\u7ec6\u76ee 1000 \u81f3 3000',
                  '\u5355\u5203\u7ed3\u6784\uff0c\u53ea\u78e8\u4e3b\u5203\uff0c\u6ce8\u610f\u4fdd\u6301\u539f\u6709\u5f27\u5ea6'),
    'beef_knife': ('\u4e2d\u5f0f\u7247\u5200\uff08\u539a\u80cc\u578b\uff09', 20, '\u78e8\u5200\u77f3', '\u7c97\u7ec6\u76ee\u914d\u5408',
                '\u5203\u89d2\u8f83\u539a\uff0c\u5148\u7c97\u78e8\u5b9a\u578b\u518d\u7ec6\u78e8\uff0c\u63e1\u6301\u4f4d\u7f6e\u9760\u8fd1\u5200\u8ddf'),
    'boning_knife': ('\u5254\u9aa8\u5200', 20, '\u78e8\u5200\u77f3', '\u7ec6\u76ee\u4e3a\u4e3b',
                '\u5203\u8584\u9700\u8f7b\u78e8\uff0c\u63e1\u6301\u9760\u8fd1\u5200\u5c16\u4fbf\u4e8e\u7cbe\u7ec6\u63a7\u5236'),
    'utility_knife': ('\u897f\u5f0f\u53a8\u5200', 20, '\u78e8\u5200\u5668\u6216\u78e8\u5200\u77f3', '\u4e2d\u7ec6\u76ee',
                 '\u9002\u7528\u78e8\u5200\u5668\uff0c\u6ce8\u610f\u78e8\u6599\u69fd\u4e0e\u5200\u8eab\u89d2\u5ea6\u8d34\u5408'),
    'kitchen_scissors': ('\u53a8\u623f\u526a\u5200', 20, '\u78e8\u5200\u5668\u4e13\u7528\u526a\u5200\u4f4d', '\u4e13\u7528\u7ec6\u76ee',
                   '\u526a\u5200\u4e0d\u53ef\u6574\u4f53\u538b\u4e0a\u78e8\u5200\u5668\uff0c\u7528\u4e13\u7528\u526a\u5200\u4f4d\u9010\u5203\u78e8'),
    'bread_knife': ('\u9762\u5305\u5200', 20, '\u78e8\u5200\u77f3', '\u7ec6\u76ee 400 \u81f3 600',
                '\u952f\u9f7f\u5203\uff0c\u6309\u539f\u6709\u952f\u9f7f\u5f62\u6001\u9010\u9f7f\u4fee\u6574\uff0c\u4e0d\u78e8\u6210\u5e73\u5203'),
    'serrated_bread': ('\u952f\u9f7f\u9762\u5305\u5200', 20, '\u4e13\u7528\u952f\u9f7f\u78e8\u5177', '\u4e13\u7528\u7ec6\u76ee',
                  '\u952f\u9f7f\u5200\u4e0d\u53ef\u78e8\u6210\u5e73\u5203\uff0c\u4f1a\u5931\u53bb\u952f\u5207\u80fd\u529b'),
    'paring_knife': ('\u524a\u76ae\u5200\u4e0e\u9910\u5200', 20, '\u78e8\u5200\u77f3', '\u7ec6\u76ee 1000 \u4ee5\u4e0a',
                 '\u5c0f\u5200\u5203\u77ed\uff0c\u63e1\u6301\u9760\u8fd1\u5200\u5c16\u63a7\u5236\u529b\u5ea6'),
    'cleaver_hatchet': ('\u4e2d\u5f0f\u65a9\u5207\u5200', 20, '\u78e8\u5200\u77f3', '\u7c97\u76ee\u4e3a\u4e3b',
                  '\u5203\u89d2\u8f83\u539a\uff0c\u78e8\u9664\u91cf\u8f83\u5927\uff0c\u5206\u591a\u6b21\u8fdb\u884c\u907f\u514d\u8fc7\u70ed'),
}

# \u78e8\u5200\u5668\u4e0e\u78e8\u5200\u77f3\u5bf9\u6bd4
TOOL_COMPARE = [
    ('\u78e8\u5200\u5668', '\u65e5\u5e38\u5feb\u901f\u4fee\u6574\uff0c\u6548\u7387\u9ad8\uff0c\u5bf9\u64cd\u4f5c\u8981\u6c42\u4f4e',
     '\u63a7\u5236\u529b\u5ea6\u4e0d\u5f53\u65f6\u6781\u6613\u78e8\u51fa\u300cV \u5f62\u51f9\u53e3\u300d\uff0c\u4e14\u4f1a\u660e\u663e\u6d88\u8017\u5200\u5203',
     '\u4e0d\u8ffd\u6c42\u5203\u53e3\u7cbe\u7ec6\u5ea6\u65f6\u9996\u9009'),
    ('\u78e8\u5200\u77f3', '\u5203\u53e3\u53ef\u63a7\u6027\u597d\uff0c\u53ef\u78e8\u51fa\u7406\u60f3\u7684\u5e73\u76f4\u5203\u7ebf\u4e0e\u5f27\u5ea6',
     '\u9700\u8981\u4e00\u5b9a\u624b\u6cd5\u4e0e\u7ec3\u4e60\uff0c\u5b66\u4e60\u6210\u672c\u8f83\u9ad8',
     '\u8ffd\u6c42\u950b\u5229\u5ea6\u4e0e\u5203\u53e3\u51e0\u4f55\u5f62\u72b6\u65f6\u4f7f\u7528'),
    ('\u78e8\u5200\u68d2\uff08\u9676\u74f7\u6216\u94a2\uff09', '\u5feb\u901f\u6062\u590d\u5203\u53e3\u950b\u5229\uff0c\u5ef6\u7f13\u949d\u5316',
     '**\u53ea\u80fd\u4fee\u6574\u4e0d\u80fd\u771f\u6b63\u78e8\u51fa\u950b\u5229\u5203\u53e3**\uff0c\u4e14\u4f1a\u6539\u53d8\u5203\u89d2',
     '\u65e5\u5e38\u7ef4\u62a4\uff0c\u4e0d\u4f5c\u4e3a\u4e3b\u8981\u78e8\u5200\u65b9\u5f0f'),
]

# \u78e8\u5200\u65b9\u5411\u4e0e\u529b\u5ea6\uff08\u6838\u5fc3\u64cd\u4f5c\u53e3\u5f84\uff09
GRIND_RULE = (
    '\u78e8\u5200\u7684\u6838\u5fc3\u662f**\u9006\u5203\u63a8\u78e8\uff0c\u4e0d\u662f\u6765\u56de\u62c9\u952f**\u3002'
    '\u5200\u5203\u653e\u5728\u78e8\u6599\u4e0a\uff0c**\u7531\u5200\u8ddf\u5411\u5200\u5c16\u5355\u5411\u63a8\u52a8**\uff0c\u6bcf\u4e00\u4e0b\u90fd\u4ece\u540c\u4e00\u4e2a\u65b9\u5411\u3002'
    '\u6765\u56de\u62c9\u952f\u4f1a\u5728\u5203\u53e3\u78e8\u51fa\u9ad8\u4f4e\u4e0d\u5e73\u7684\u6ce2\u6d6a\u7ebf\uff0c\u5f62\u6210\u952f\u9f7f\u72b6\u7f3a\u9677\u3002'
    '\u529b\u5ea6\u8981**\u5747\u5300\u800c\u8f7b**\uff0c\u9760\u78e8\u6599\u81ea\u8eab\u7684\u78e8\u524a\u4f5c\u7528\u53bb\u9664\u91d1\u5c5e\uff0c\u800c\u4e0d\u662f\u9760\u538b\u3002'
    '\u6bcf\u78e8\u51e0\u4e0b\u89c2\u5bdf\u4e00\u6b21\u5203\u53e3\u7ebf\u662f\u5426\u5e73\u76f4\uff0c\u4e0d\u8981\u76f2\u78e8\u3002'
)

# \u53bb\u6bdb\u523a\u8981\u6c42
BURRS_NOTE = (
    '\u78e8\u5b8c\u5fc5\u987b**\u53bb\u6bdb\u523a**\uff1a\u7528\u4e00\u6839\u7ec6\u9ebb\u7ef3\u6216\u76ae\u9769\u6761\uff0c'
    '\u987a\u7740\u4e0e\u5203\u53e3\u5782\u76f4\u7684\u65b9\u5411**\u8f7b\u8f7b\u62c9\u8fc7\u6574\u4e2a\u5203\u53e3**\uff0c\u628a\u5411\u4e00\u4fa7\u5012\u4f0f\u7684\u6bdb\u8fb9\u6273\u5012\u56de\u53bb\uff0c'
    '\u518d\u987a\u7740\u5207\u524a\u65b9\u5411\u8f7b\u62c9\u4e00\u6b21\u3002'
    '\u4e0d\u53bb\u6bdb\u523a\u7684\u5200\u4f1a\u300c\u6302\u6bdb\u300d\u300c\u6495\u7ea4\u7ef4\u300d\uff0c\u5207\u51fa\u6765\u7684\u65ad\u9762\u4e0d\u5e72\u51c0\uff0c'
    '\u800c\u4e14\u6bdb\u8fb9\u4f1a\u8ba9\u5200\u5203\u66f4\u5feb\u518d\u6b21\u949d\u5316\u3002'
)

# \u6536\u7eb3\u8981\u6c42
STORAGE_RULE = (
    '\u6536\u7eb3\u56db\u6761\uff1a'
    '\u2460 **\u5200\u5177\u4e0d\u53ef\u53e0\u653e**\uff0c\u5203\u53e3\u4e92\u76f8\u78b0\u649e\u4f1a\u77ac\u95f4\u5d29\u5203\uff1b'
    '\u2461 **\u7ad6\u653e\u6216\u7528\u5200\u67b6\u3001\u5200\u5757**\uff0c\u5203\u53e3\u671d\u4e0b\u6216\u63d2\u5165\u69fd\u4f4d\uff1b'
    '\u2462 **\u5203\u53e3\u4e0d\u78b0\u91d1\u5c5e**\uff0c\u6728\u8d28\u6216\u5851\u6599\u5200\u67b6\u66f4\u5b89\u5168\uff1b'
    '\u2463 \u6d17\u540e**\u7acb\u523b\u64e6\u5e72**\uff0c\u6f6e\u6e7f\u4f1a\u9508\u8680\u5e76\u4f7f\u5200\u53e3\u8fb9\u7f18\u53d1\u9ed1\u3002'
)

# \u660e\u786e\u7981\u6b62\u7684\u64cd\u4f5c
BANNED = [
    '\u6728\u5934\u67c4\u4e0e\u7af9\u67c4\u5200\u5177\u4e0d\u53ef\u8fdb\u6d17\u7897\u673a\uff0c\u9ad8\u6e29\u4e0e\u957f\u65f6\u95f4\u6d78\u6c34\u4f1a\u4f7f\u67c4\u90e8\u5f00\u88c2\u53d8\u5f62',
    '\u6728\u5934\u67c4\u4e0e\u7af9\u67c4\u5200\u5177\u4e0d\u53ef\u957f\u65f6\u95f4\u6ce1\u6c34\uff0c\u6d78\u6c34\u540e\u67c4\u90e8\u4f1a\u81a8\u80c0\u677e\u52a8',
    '\u4e0d\u53ef\u7528\u6d17\u7897\u673a\u6e05\u6d17\u4efb\u4f55\u4f18\u8d28\u5200\u5177\uff0c\u6d17\u7897\u673a\u7684\u9ad8\u6e29\u4e0e\u6d17\u6da4\u5242\u4f1a\u635f\u4f24\u5203\u53e3',
    '\u4e0d\u53ef\u7528\u78e8\u5200\u68d2\u5f53\u4e3b\u8981\u78e8\u5200\u65b9\u5f0f\uff0c\u78e8\u5200\u68d2\u53ea\u80fd\u4fee\u6574\u4e0d\u80fd\u78e8\u51fa\u950b\u5229\u5203\u53e3',
    '\u4e0d\u53ef\u7528\u9676\u74f7\u5200\u78e8\u73bb\u7483\u6216\u5927\u7406\u77f3\u53f0\u9762\uff0c\u4f1a\u5267\u70c8\u78e8\u635f\u5200\u5203',
    '\u4e0d\u53ef\u628a\u5200\u4e22\u8fdb\u6c34\u69fd\u5e95\u90e8\uff0c\u5bb9\u6613\u7f3a\u53e3\u4e14\u96be\u4ee5\u53d1\u73b0',
    '\u4e0d\u53ef\u7528\u529b\u8fc7\u731b\u5355\u4fa7\u4e0b\u538b\uff0c\u4f1a\u78e8\u51fa\u51f9\u53e3\u5e76\u4f7f\u5203\u7ebf\u4e0d\u518d\u5e73\u76f4',
    '\u526a\u5200\u4e0d\u53ef\u6574\u4f53\u538b\u4e0a\u78e8\u5200\u5668\uff0c\u987b\u7528\u4e13\u7528\u526a\u5200\u4f4d\u9010\u5203\u4fee\u78e8',
]

# \u751f\u719f\u5206\u79bb\u8981\u6c42
COLOR_SEPARATION = (
    '\u751f\u719f\u5200\u5fc5\u987b\u5206\u79bb\uff1a'
    '\u7ea2\u8272\u6216\u7c89\u8272\u6807\u8bc6\u5200\u7528\u4e8e\u751f\u8089\uff0c\u84dd\u8272\u6216\u7eff\u8272\u6807\u8bc6\u5200\u7528\u4e8e\u852c\u83dc\u4e0e\u719f\u98df\uff0c'
    '\u9ec4\u8272\u6807\u8bc6\u5200\u7528\u4e8e\u4e00\u822c\u7528\u9014\u3002'
    '\u540c\u4e00\u628a\u5200\u5207\u8fc7\u751f\u8089\u540e**\u4e0d\u5e94\u76f4\u63a5\u63a5\u89e6\u5373\u98df\u6216\u5373\u5165\u53e3\u98df\u54c1**\uff0c'
    '\u751f\u8089\u8868\u9762\u53ef\u80fd\u5e26\u6709\u6c99\u95e8\u6c0f\u83cc\u3001\u5f2f\u66f2\u83cc\u7b49\u81f4\u75c5\u83cc\u3002'
    '\u82e5\u53ea\u6709\u4e00\u628a\u5200\uff0c\u5207\u5b8c\u751f\u8089\u540e\u5fc5\u987b**\u5f7b\u5e95\u51b2\u6d17\u5e76\u7528\u7682\u6db2\u6e05\u6d01\u5200\u9762**\uff0c'
    '\u4e14\u4e0d\u8981\u7528\u64e6\u5200\u5e03\u53ea\u64e6\u5e72\u8868\u9762\u5c31\u6536\u8d77\u6765\u3002'
)

# \u68c0\u67e5\u9879: (\u952e, \u4e2d\u6587\u540d, \u8bf4\u660e, \u4e0d\u5408\u683c\u540e\u679c)
CHECK_ITEMS = [
    ('sharpness', '\u950b\u5229\u5ea6', '\u80fd\u8f7b\u677e\u5207\u5f00\u7eb8\u5f20\u6216\u9ec4\u74dc\u7247\u800c\u4e0d\u62d6\u6ce5\u5e26\u6c34',
     '\u949d\u5200\u5207\u83dc\u9700\u52a0\u5927\u529b\u5ea6\uff0c\u66f4\u5bb9\u6613\u6ed1\u5200\u5272\u4f24'),
    ('edge_line', '\u5203\u7ebf\u5e73\u76f4', '\u5203\u53e3\u7ebf\u5e73\u76f4\u65e0\u9ad8\u4f4e\u6ce2\u6d6a\uff0c\u65e0 V \u5f62\u51f9\u53e3',
     '\u51f9\u53e3\u4e0e\u6ce2\u6d6a\u7ebf\u4f7f\u5207\u5272\u4e0d\u5e72\u51c0\uff0c\u4e14\u96be\u4ee5\u6062\u590d'),
    ('burr', '\u6bdb\u523a\u5df2\u6e05\u9664', '\u5203\u53e3\u8fce\u5149\u89c2\u5bdf\u65e0\u5012\u4f0f\u6bdb\u8fb9\uff0c\u5207\u5272\u4e0d\u6302\u6bdb',
     '\u6302\u6bdb\u6495\u7ea4\u7ef4\uff0c\u65ad\u9762\u4e0d\u5e72\u51c0\uff0c\u4e14\u52a0\u901f\u518d\u6b21\u949d\u5316'),
    ('handle', '\u67c4\u90e8\u5b8c\u597d', '\u6728\u67c4\u7af9\u67c4\u65e0\u5f00\u88c2\u677e\u52a8\uff0c\u91d1\u5c5e\u67c4\u65e0\u677e\u52a8\u9508\u8680',
     '\u67c4\u90e8\u677e\u52a8\u65f6\u5200\u8eab\u53d7\u529b\u5f02\u5e38\uff0c\u5203\u53e3\u6613\u5d29'),
    ('corrosion', '\u65e0\u9508\u8680', '\u5203\u9762\u65e0\u9508\u70b9\uff0c\u5203\u53e3\u8fb9\u7f18\u65e0\u53d1\u9ed1',
     '\u9508\u8680\u6d88\u8017\u5203\u53e3\u6750\u6599\uff0c\u949d\u5316\u901f\u5ea6\u660e\u663e\u52a0\u5feb'),
    ('dry', '\u5df2\u5b8c\u5168\u64e6\u5e72', '\u5200\u8eab\u4e0e\u67c4\u90e8\u5b8c\u5168\u5e72\u71e5\u65e0\u6b8b\u7559\u6c34\u6e0d',
     '\u6f6e\u6e7f\u5bfc\u81f4\u9508\u8680\u4e0e\u67c4\u90e8\u5f00\u88c2'),
    ('storage', '\u6536\u7eb3\u5408\u89c4', '\u672a\u53e0\u653e\uff0c\u7ad6\u653e\u6216\u7528\u5200\u67b6\uff0c\u5203\u53e3\u4e0d\u78b0\u91d1\u5c5e',
     '\u53e0\u653e\u78b0\u649e\u4f1a\u77ac\u95f4\u5d29\u5203'),
    ('clean', '\u6e05\u6d01\u5230\u4f4d', '\u5200\u9762\u5df2\u7528\u7682\u6db2\u6e05\u6d01\u5e76\u51b2\u51c0\uff0c\u65e0\u6b8b\u7559',
     '\u6b8b\u7559\u7269\u4e0e\u6f6e\u6e7f\u5171\u540c\u5bfc\u81f4\u5f02\u5473\u4e0e\u9508\u8680'),
    ('separation', '\u751f\u719f\u5206\u79bb', '\u751f\u8089\u5200\u4e0e\u5373\u98df\u5200\u5206\u7528\uff0c\u5206\u8272\u7ba1\u7406',
     '\u751f\u8089\u4ea4\u53c9\u6c61\u67d3\u5373\u98df\u98df\u54c1'),
]


def norm(k):
    return str(k or '').strip().lower().replace(' ', '')


def knife_of(key):
    k = norm(key)
    if k not in KNIVES:
        raise ValueError('\u672a\u77e5\u5200\u578b\u952e: %s\uff0c\u53ef\u9009\u952e\u89c1 KNIVES \u8868' % key)
    return k, KNIVES[k]


def angle_tier(a):
    if a <= 15:
        return '\u8584\u5203\uff08\u9002\u5408\u7cbe\u7ec6\u5207\u5272\uff0c\u6613\u5d29\u9700\u8c28\u614e\uff09'
    if a <= 20:
        return '\u6807\u51c6\u5203\uff08\u517c\u987e\u950b\u5229\u4e0e\u8010\u7528\uff09'
    return '\u539a\u5203\uff08\u8010\u7528\uff0c\u9002\u5408\u5288\u780d\u4e0e\u91cd\u6d3b\uff09'


def angle_valid(a):
    try:
        v = float(a)
    except (TypeError, ValueError):
        return False
    return 0 < v <= 30


def calc(data):
    items = data.get('items') or []
    checks = data.get('checks') or {}
    if not isinstance(checks, dict):
        raise ValueError('checks \u5fc5\u987b\u662f\u5bf9\u8c61')
    for k in checks:
        if not any(norm(c[0]) == norm(k) for c in CHECK_ITEMS):
            raise ValueError('\u672a\u77e5\u7684\u68c0\u67e5\u9879: %s\uff0c\u53ef\u9009\u9879\u89c1 CHECK_ITEMS \u8868' % k)

    if items:
        rows = []
        for it in items:
            key, (name, angle, tool, grit, note) = knife_of(it.get('knife'))
            use_angle = it.get('angle')
            if use_angle is not None and not angle_valid(use_angle):
                raise ValueError('angle \u5fc5\u987b\u5728 0 \u5230 30 \u4e4b\u95f4\uff0c\u5b9e\u4e3a: %s' % use_angle)
            rows.append({
                'name': it.get('name', name),
                'knife': key,
                'knife_name': name,
                'rec_angle': angle,
                'use_angle': use_angle,
                'angle_tier': angle_tier(angle),
                'tool': tool,
                'grit': grit,
                'note': note,
                'serrated': key in ('bread_knife', 'serrated_bread', 'kitchen_scissors'),
                'wood_handle': key in ('chinese_cleaver', 'beef_knife', 'chopping_hachet'),
            })
        rows.sort(key=lambda r: r['knife_name'])
    else:
        rows = []

    ck_rows = []
    bad = []
    unk = []
    for ckey, cname, cdesc, cwhy in CHECK_ITEMS:
        v = checks.get(ckey)
        if v is None:
            ck_rows.append({'name': cname, 'status': '\u672a\u68c0\u67e5', 'desc': cdesc, 'why': cwhy})
            unk.append(cname)
        elif v:
            ck_rows.append({'name': cname, 'status': '\u5408\u683c', 'desc': cdesc, 'why': cwhy})
        else:
            ck_rows.append({'name': cname, 'status': '\u4e0d\u5408\u683c', 'desc': cdesc, 'why': cwhy})
            bad.append(cname)

    warns = []
    for r in rows:
        if r['serrated']:
            warns.append('%s \u5c5e\u952f\u9f7f\u6216\u526a\u5200\u7c7b\uff0c**\u4e0d\u53ef\u78e8\u6210\u5e73\u5203**\uff0c\u5426\u5219\u5931\u53bb\u952f\u5207\u80fd\u529b' % r['name'])
        if r['wood_handle']:
            warns.append('%s \u4e3a\u6728\u8d28\u67c4\u7c7b\uff0c**\u4e0d\u53ef\u8fdb\u6d17\u7897\u673a\u3001\u4e0d\u53ef\u957f\u65f6\u95f4\u6ce1\u6c34**\uff0c'
                         '\u5426\u5219\u67c4\u90e8\u5f00\u88c2\u53d8\u5f62\u4e14\u5200\u8eab\u9508\u8680' % r['name'])
        if r['use_angle'] is not None and abs(float(r['use_angle']) - r['rec_angle']) >= 5:
            warns.append('%s \u5efa\u8bae\u5203\u89d2 %d \u5ea6\uff0c\u5f53\u524d\u6309 %s \u5ea6\uff0c\u504f\u5dee\u8f83\u5927\uff0c\u5203\u7ebf\u51e0\u4f55\u4f1a\u6539\u53d8'
                         % (r['name'], r['rec_angle'], r['use_angle']))
    for b in bad:
        warns.append('\u68c0\u67e5\u4e0d\u5408\u683c\uff1a%s\uff0c%s' % (b, next(c[3] for c in CHECK_ITEMS if c[1] == b)))
    for u in unk:
        warns.append('\u68c0\u67e5\u672a\u5b8c\u6210\uff1a%s\uff0c\u5efa\u8bae\u9010\u9879\u786e\u8ba4\u540e\u518d\u7ee7\u7eed\u4f7f\u7528' % u)

    if len(bad) >= 1:
        level = '\u9700\u5904\u7406\u540e\u4f7f\u7528'
    elif unk:
        level = '\u5f85\u786e\u8ba4'
    else:
        level = '\u72b6\u6001\u826f\u597d'

    return {
        'level': level,
        'items': rows,
        'check_rows': ck_rows,
        'bad': bad,
        'unchecked': unk,
        'warns': warns,
        'tool_compare': [{'name': a, 'good': b, 'bad': c, 'use': d}
                         for a, b, c, d in TOOL_COMPARE],
        'grind_rule': GRIND_RULE,
        'burrs_note': BURRS_NOTE,
        'storage_rule': STORAGE_RULE,
        'banned': BANNED,
        'separation': COLOR_SEPARATION,
    }


def render_md(r):
    L = []
    L.append('# \u5200\u5177\u4fdd\u517b\u4e0e\u78e8\u5200\u6838\u67e5')
    L.append('')
    L.append('## \u4e00\u3001\u603b\u4f53\u5224\u5b9a')
    L.append('')
    L.append('**%s**' % r['level'])
    L.append('')
    L.append('## \u4e8c\u3001\u6309\u5200\u578b\u7684\u78e8\u5200\u53c2\u6570')
    L.append('')
    if r['items']:
        L.append('| \u5200\u5177 | \u5200\u578b | \u5efa\u8bae\u5203\u89d2 | \u5203\u89d2\u6863\u4f4d | \u63a8\u8350\u5de5\u5177 | \u78e8\u6599 | \u6ce8\u610f |')
        L.append('|---|---|---|---|---|---|---|')
        for x in r['items']:
            L.append('| %s | %s | %d \u5ea6 | %s | %s | %s | %s |'
                     % (x['name'], x['knife_name'], x['rec_angle'], x['angle_tier'],
                        x['tool'], x['grit'], x['note']))
    else:
        L.append('- \u672a\u586b\u5199\u5200\u5177\u8bb0\u5f55')
    L.append('')
    L.append('## \u4e09\u3001\u78e8\u5200\u5668\u4e0e\u78e8\u5200\u77f3\u5bf9\u6bd4')
    L.append('')
    L.append('| \u5de5\u5177 | \u4f18\u70b9 | \u7f3a\u70b9 | \u9002\u7528 |')
    L.append('|---|---|---|---|')
    for t in r['tool_compare']:
        L.append('| %s | %s | %s | %s |' % (t['name'], t['good'], t['bad'], t['use']))
    L.append('')
    L.append('## \u56db\u3001\u78e8\u5200\u7684\u65b9\u5411\u4e0e\u529b\u5ea6\uff08\u6838\u5fc3\uff09')
    L.append('')
    L.append('- %s' % r['grind_rule'])
    L.append('')
    L.append('## \u4e94\u3001\u53bb\u6bdb\u523a')
    L.append('')
    L.append('- %s' % r['burrs_note'])
    L.append('')
    L.append('## \u516d\u3001\u6536\u7eb3')
    L.append('')
    L.append('- %s' % r['storage_rule'])
    L.append('')
    L.append('## \u4e03\u3001\u660e\u786e\u7981\u6b62\u7684\u64cd\u4f5c')
    L.append('')
    for b in r['banned']:
        L.append('- %s' % b)
    L.append('')
    L.append('## \u516b\u3001\u751f\u719f\u5200\u5206\u79bb')
    L.append('')
    L.append('- %s' % r['separation'])
    L.append('')
    L.append('## \u4e5d\u3001\u68c0\u67e5\u9879')
    L.append('')
    L.append('| \u68c0\u67e5\u9879 | \u72b6\u6001 | \u600e\u4e48\u5224\u65ad | \u4e0d\u5408\u683c\u540e\u679c |')
    L.append('|---|---|---|---|')
    for c in r['check_rows']:
        L.append('| %s | %s | %s | %s |' % (c['name'], c['status'], c['desc'], c['why']))
    L.append('')
    L.append('## \u5341\u3001\u63d0\u793a')
    L.append('')
    if r['warns']:
        for w in r['warns']:
            L.append('- %s' % w)
    else:
        L.append('- \u672a\u53d1\u73b0\u4e0d\u5408\u683c\u9879\uff0c\u6309\u65e5\u5e38\u4fdd\u517b\u8981\u70b9\u7ef4\u62a4\u5373\u53ef')
    L.append('')
    L.append('## \u5341\u4e00\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] \u5203\u53e3\u7ebf\u5e73\u76f4\uff0c\u65e0 V \u5f62\u51f9\u53e3\u4e0e\u6ce2\u6d6a\u7ebf')
    L.append('- [ ] \u5df2\u5b8c\u6210\u53bb\u6bdb\u523a\uff0c\u5207\u5272\u4e0d\u6302\u6bdb')
    L.append('- [ ] \u6728\u67c4\u7af9\u67c4\u5200\u5177\u672a\u8fdb\u8fc7\u6d17\u7897\u673a\u3001\u672a\u957f\u65f6\u95f4\u6ce1\u6c34')
    L.append('- [ ] \u5200\u5177\u5df2\u5b8c\u5168\u64e6\u5e72\u5e76\u5408\u89c4\u6536\u7eb3\uff0c\u672a\u53e0\u653e')
    L.append('- [ ] \u751f\u719f\u5200\u5206\u79bb\uff0c\u5206\u8272\u7ba1\u7406')
    L.append('- [ ] \u78e8\u5200\u4e3a\u9006\u5203\u5355\u5411\u63a8\u78e8\uff0c\u529b\u5ea6\u5747\u5300\u800c\u8f7b')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    # 1 \u5203\u89d2\u6863\u4f4d
    ck(angle_tier(15) == '\u8584\u5203\uff08\u9002\u5408\u7cbe\u7ec6\u5207\u5272\uff0c\u6613\u5d29\u9700\u8c28\u614e\uff09', '15 \u5ea6\u6863\u4f4d\u6709\u8bef: %s' % angle_tier(15))
    ck(angle_tier(20) == '\u6807\u51c6\u5203\uff08\u517c\u987e\u950b\u5229\u4e0e\u8010\u7528\uff09', '20 \u5ea6\u6863\u4f4d\u6709\u8bef: %s' % angle_tier(20))
    ck(angle_tier(25) == '\u539a\u5203\uff08\u8010\u7528\uff0c\u9002\u5408\u5288\u780d\u4e0e\u91cd\u6d3b\uff09', '25 \u5ea6\u6863\u4f4d\u6709\u8bef: %s' % angle_tier(25))

    # 2 \u5203\u89d2\u5408\u6cd5\u6027
    ck(angle_valid(15) is True, '15 \u5ea6\u5e94\u5408\u6cd5')
    ck(angle_valid(0) is False, '0 \u5ea6\u5e94\u975e\u6cd5')
    ck(angle_valid(31) is False, '31 \u5ea6\u5e94\u975e\u6cd5')

    # 3 \u4e2d\u5f0f\u7247\u5200\u53c2\u6570
    r3 = calc({'items': [{'knife': 'chinese_cleaver'}]})
    ck(r3['items'][0]['rec_angle'] == 15, '\u4e2d\u5f0f\u7247\u5200\u5e94\u4e3a 15 \u5ea6\uff0c\u5b9e\u4e3a %s' % r3['items'][0]['rec_angle'])
    ck(r3['items'][0]['wood_handle'] is True, '\u4e2d\u5f0f\u7247\u5200\u5e94\u6807\u6728\u67c4\u7c7b')
    ck(any('\u6d17\u7897\u673a' in w for w in r3['warns']), '\u6728\u67c4\u7c7b\u5e94\u63d0\u793a\u4e0d\u53ef\u8fdb\u6d17\u7897\u673a\uff0c\u5b9e\u4e3a %s' % r3['warns'])

    # 4 \u65e5\u5f0f\u4e3b\u53a8\u5200
    r4 = calc({'items': [{'knife': 'japanese_gyuto'}]})
    ck(r4['items'][0]['knife_name'] == '\u65e5\u5f0f\u4e3b\u53a8\u5200', '\u5200\u578b\u540d\u6709\u8bef: %s' % r4['items'][0]['knife_name'])
    ck('\u53ea\u78e8\u4e3b\u5203' in r4['items'][0]['note'], '\u65e5\u5f0f\u5200\u5e94\u8bf4\u660e\u53ea\u78e8\u4e3b\u5203\uff0c\u5b9e\u4e3a %s' % r4['items'][0]['note'])

    # 5 \u952f\u9f7f\u5200\u4e0d\u53ef\u78e8\u5e73
    r5 = calc({'items': [{'knife': 'serrated_bread'}]})
    ck(r5['items'][0]['serrated'] is True, '\u952f\u9f7f\u5200\u5e94\u6807\u952f\u9f7f\u7c7b')
    ck(any('\u4e0d\u53ef\u78e8\u6210\u5e73\u5203' in w for w in r5['warns']), '\u952f\u9f7f\u5200\u5e94\u63d0\u793a\u4e0d\u53ef\u78e8\u5e73\uff0c\u5b9e\u4e3a %s' % r5['warns'])

    # 6 \u526a\u5200\u4e0d\u53ef\u6574\u4f53\u4e0a\u78e8\u5200\u5668
    ck(any('\u526a\u5200\u4e0d\u53ef\u6574\u4f53\u538b\u4e0a\u78e8\u5200\u5668' in b for b in BANNED), '\u5fc5\u987b\u542b\u526a\u5200\u4e0d\u53ef\u6574\u4f53\u4e0a\u78e8\u5200\u5668')
    ck(any('\u78e8\u5200\u68d2\u53ea\u80fd\u4fee\u6574\u4e0d\u80fd\u78e8\u51fa\u950b\u5229\u5203\u53e3' in b for b in BANNED), '\u5fc5\u987b\u542b\u78e8\u5200\u68d2\u7684\u9650\u5236\u8bf4\u660e')

    # 7 \u78e8\u5200\u65b9\u5411\u53e3\u5f84
    ck('\u9006\u5203\u63a8\u78e8' in GRIND_RULE, '\u5fc5\u987b\u542b\u9006\u5203\u63a8\u78e8')
    ck('\u4e0d\u662f\u6765\u56de\u62c9\u952f' in GRIND_RULE, '\u5fc5\u987b\u660e\u786e\u4e0d\u662f\u6765\u56de\u62c9\u952f')
    ck('\u7531\u5200\u8ddf\u5411\u5200\u5c16' in GRIND_RULE, '\u5fc5\u987b\u542b\u5355\u5411\u63a8\u52a8\u65b9\u5411')

    # 8 \u53bb\u6bdb\u523a\u8981\u6c42
    ck('\u53bb\u6bdb\u523a' in BURRS_NOTE, '\u5fc5\u987b\u542b\u53bb\u6bdb\u523a\u8981\u6c42')
    ck('\u6302\u6bdb' in BURRS_NOTE, '\u53bb\u6bdb\u523a\u5e94\u8bf4\u660e\u6302\u6bdb\u540e\u679c')

    # 9 \u6536\u7eb3\u56db\u6761
    ck('\u4e0d\u53ef\u53e0\u653e' in STORAGE_RULE, '\u6536\u7eb3\u5fc5\u987b\u542b\u4e0d\u53ef\u53e0\u653e')
    ck('\u5203\u53e3\u4e0d\u78b0\u91d1\u5c5e' in STORAGE_RULE, '\u6536\u7eb3\u5fc5\u987b\u542b\u5203\u53e3\u4e0d\u78b0\u91d1\u5c5e')
    ck('\u7ad6\u653e' in STORAGE_RULE, '\u6536\u7eb3\u5fc5\u987b\u542b\u7ad6\u653e\u6216\u5200\u67b6')

    # 10 \u68c0\u67e5\u9879\u4e09\u7ea7\u5224\u5b9a
    allok = {k: True for k, _, _, _ in CHECK_ITEMS}
    r10 = calc({'checks': allok})
    ck(r10['level'] == '\u72b6\u6001\u826f\u597d', '\u5168\u5408\u683c\u5e94\u72b6\u6001\u826f\u597d\uff0c\u5b9e\u4e3a %s' % r10['level'])
    ck(len(r10['check_rows']) == 9, '\u68c0\u67e5\u9879\u5e94 9 \u6761\uff0c\u5b9e\u4e3a %d' % len(r10['check_rows']))
    r10b = calc({'checks': dict(allok, burr=False)})
    ck(r10b['level'] == '\u9700\u5904\u7406\u540e\u4f7f\u7528', '\u6bdb\u523a\u4e0d\u5408\u683c\u5e94\u9700\u5904\u7406\uff0c\u5b9e\u4e3a %s' % r10b['level'])
    ck('\u6bdb\u523a\u5df2\u6e05\u9664' in r10b['bad'], '\u5e94\u70b9\u540d\u6bdb\u523a\u9879\uff0c\u5b9e\u4e3a %s' % r10b['bad'])
    r10c = calc({'checks': {k: True for k, _, _, _ in CHECK_ITEMS if k != 'corrosion'}})
    ck(r10c['level'] == '\u5f85\u786e\u8ba4', '\u7f3a\u9879\u5e94\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r10c['level'])
    ck('\u65e0\u9508\u8680' in r10c['unchecked'], '\u5e94\u5217\u51fa\u672a\u786e\u8ba4\u7684\u65e0\u9508\u8680\uff0c\u5b9e\u4e3a %s' % r10c['unchecked'])

    # 11 \u89d2\u5ea6\u504f\u5dee\u544a\u8b66
    r11 = calc({'items': [{'knife': 'japanese_gyuto', 'angle': 25}]})
    ck(any('\u504f\u5dee\u8f83\u5927' in w for w in r11['warns']), '\u89d2\u5ea6\u504f\u5dee\u5e94\u544a\u8b66\uff0c\u5b9e\u4e3a %s' % r11['warns'])

    # 12 \u751f\u719f\u5206\u79bb\u8981\u6c42
    ck('\u751f\u719f\u5200\u5fc5\u987b\u5206\u79bb' in COLOR_SEPARATION, '\u5fc5\u987b\u542b\u751f\u719f\u5200\u5206\u79bb')
    ck('\u6c99\u95e8\u6c0f\u83cc' in COLOR_SEPARATION, '\u751f\u719f\u5206\u79bb\u5e94\u8bf4\u660e\u81f4\u75c5\u83cc')

    # 13 BOM \u4e24\u6761\u8def\u5f84
    bom = '\ufeff{"items": [{"knife": "boning_knife"}]}'
    r13 = calc(json.loads(bom.lstrip('\ufeff')))
    ck(r13['items'][0]['rec_angle'] == 20, 'BOM \u8f93\u5165\u5e94\u89e3\u6790\uff0c\u5254\u9aa8\u5200\u5e94\u4e3a 20 \u5ea6\uff0c\u5b9e\u4e3a %s' % r13['items'][0]['rec_angle'])
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe6.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps({'checks': dict(allok, storage=False)}))
    try:
        r13b = calc(json.loads(open(tmp, 'r', encoding='utf-8-sig').read()))
        ck(r13b['level'] == '\u9700\u5904\u7406\u540e\u4f7f\u7528', 'utf-8-sig \u8bfb\u53d6\u5e94\u6b63\u5e38\uff0c\u5b9e\u4e3a %s' % r13b['level'])
        ck('\u6536\u7eb3\u5408\u89c4' in r13b['bad'], '\u5e94\u70b9\u540d\u6536\u7eb3\u9879\uff0c\u5b9e\u4e3a %s' % r13b['bad'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 14 \u975e\u6cd5\u8f93\u5165
    for bad, why in (
        ({'items': [{'knife': '\u4e0d\u5b58\u5728\u7684\u5200'}]}, '\u672a\u77e5\u5200\u578b'),
        ({'checks': {'\u4e0d\u5b58\u5728\u7684\u9879': True}}, '\u672a\u77e5\u68c0\u67e5\u9879'),
        ({'checks': '\u4e0d\u662f\u5bf9\u8c61'}, 'checks \u975e\u5bf9\u8c61'),
        ({'items': [{'knife': 'chinese_cleaver', 'angle': 45}]}, '\u89d2\u5ea6\u8d85\u8303\u56f4'),
    ):
        try:
            calc(bad)
            ck(False, '\u7528\u4f8b14 %s \u5e94\u629b\u9519' % why)
        except ValueError:
            ck(True, '')

    # 15 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r3)
    for key in ('\u78e8\u5200\u5668\u4e0e\u78e8\u5200\u77f3', '\u9006\u5203\u63a8\u78e8', '\u53bb\u6bdb\u523a', '\u6536\u7eb3', '\u7981\u6b62', '\u751f\u719f\u5200\u5206\u79bb', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355'):
        ck(key in md, 'Markdown \u8f93\u51fa\u5e94\u542b %s' % key)
    ck(len(r3['banned']) >= 7, '\u7981\u6b62\u9879\u81f3\u5c11 7 \u6761\uff0c\u5b9e\u4e3a %d' % len(r3['banned']))

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    msg = 'SELFTEST FAIL\n' + '\n'.join(errs) if errs else (
        'SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u5203\u89d2\u6863\u4f4d/\u5203\u89d2\u5408\u6cd5\u6027/\u4e2d\u5f0f\u7247\u5200\u6728\u67c4\u7981\u5fcc/\u65e5\u5f0f\u5355\u5203/\u952f\u9f7f\u4e0d\u53ef\u78e8\u5e73/'
        '\u526a\u5200\u4e0e\u78e8\u5200\u68d2\u9650\u5236/\u9006\u5203\u63a8\u78e8\u53e3\u5f84/\u53bb\u6bdb\u523a/\u6536\u7eb3\u56db\u6761/\u68c0\u67e5\u9879\u4e09\u7ea7\u5224\u5b9a/\u89d2\u5ea6\u504f\u5dee\u544a\u8b66/'
        '\u751f\u719f\u5206\u79bb/BOM \u4e24\u6761\u8def\u5f84/\u975e\u6cd5\u8f93\u5165/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u5200\u5177\u4fdd\u517b\u4e0e\u78e8\u5200\u6838\u67e5')
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
            print('ERROR --file \u4e0d\u5b58\u5728: %s' % a.file)
            return 2
        raw = open(a.file, 'r', encoding='utf-8-sig', errors='replace').read()
    if not raw.strip():
        print('ERROR \u9700\u8981 --file \u6216 --text')
        return 2
    try:
        data = json.loads(raw.lstrip('\ufeff'))
    except ValueError as e:
        print('ERROR JSON \u89e3\u6790\u5931\u8d25: %s' % e)
        return 2
    try:
        r = calc(data)
    except ValueError as e:
        print('ERROR %s' % e)
        return 2

    out = render_md(r) if a.format == 'md' else json.dumps(r, ensure_ascii=False, indent=2)
    d = os.path.dirname(os.path.abspath(__file__))
    target = a.out or os.path.join(d, '_last_result.txt')
    with open(target, 'w', encoding='utf-8') as f:
        f.write(out + '\n')
    print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % target)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())

