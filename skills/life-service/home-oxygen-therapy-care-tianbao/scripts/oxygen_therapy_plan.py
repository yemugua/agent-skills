# -*- coding: utf-8 -*-
"""\u5c45\u5bb6\u6c27\u7597\u8017\u6750\u5468\u671f\u4e0e\u5b89\u5168\u6838\u67e5\u5de5\u5177\u3002

\u7528\u6cd5:
  python oxygen_therapy_plan.py --file case.json [--cost] [--json]
  python oxygen_therapy_plan.py --selftest

\u672c\u5de5\u5177\u4e0d\u7ed9\u9002\u5e94\u8bc1\u6570\u5b57\u3001\u4e0d\u7ed9\u6c27\u6d41\u91cf\u6570\u503c\u3001\u4e0d\u7ed9\u5438\u75f0\u53c2\u6570\u3002
"""
import argparse
import io
import json
import os
import sys

DEVICES = [
    ("molecular", "\u5206\u5b50\u7b5b\u5236\u6c27\u673a", "\u7269\u7406\u5206\u5b50\u7b5b\u5438\u9644\u5206\u79bb",
     "\u76f8\u5bf9\u8f83\u9ad8", "\u8f83\u4f4e",
     "\u4f9b\u6c27\u91cf\u968f\u65f6\u95f4\u8870\u51cf\uff0c\u9700\u5b9a\u671f\u66f4\u6362\u6ee4\u82af",
     "\u51fa\u6c14\u91cf\u662f\u5426\u6ee1\u8db3\u533b\u5631\u3001\u8870\u51cf\u540e\u5982\u4f55\u5904\u7406\u3001\u7ef4\u4fee\u6210\u672c"),
    ("concentrator", "\u6d53\u7f29\u5f0f\u5236\u6c27\u673a", "\u819c\u5206\u79bb",
     "\u76f8\u5bf9\u8f83\u4f4e", "\u4e2d\u7b49",
     "\u4f53\u79ef\u5c0f\u3001\u566a\u97f3\u4f4e\u3001\u4fbf\u4e8e\u79fb\u52a8",
     "\u5b9e\u9645\u4f9b\u6c27\u91cf\u662f\u5426\u6ee1\u8db3\u3001\u8fde\u7eed\u5de5\u4f5c\u65f6\u95f4"),
    ("liquid", "\u6db2\u6c27", "\u4f4e\u6e29\u6db2\u6001\u6c14\u6e90",
     "\u65e0", "\u65e0",
     "\u9700\u5b9a\u671f\u6362\u7f38\u6216\u914d\u9001\uff0c\u7f38\u4f53\u642c\u8fd0\u6709\u5b89\u5168\u8981\u6c42",
     "\u914d\u9001\u7a33\u5b9a\u6027\u3001\u7f38\u4f53\u5b58\u653e\u4e0e\u56fa\u5b9a"),
    ("piston", "\u6d3b\u585e\u5f0f\u538b\u7f29\u673a", "\u538b\u7f29\u540e\u5206\u79bb",
     "\u76f8\u5bf9\u8f83\u9ad8", "\u8f83\u9ad8",
     "\u7ed3\u6784\u8f83\u7b80\u5355",
     "\u6301\u7eed\u4f9b\u6c27\u80fd\u529b\u3001\u566a\u97f3\u3001\u80fd\u8017"),
]

DEVICE_NOTE = "\u4e0d\u63a8\u8350\u5177\u4f53\u54c1\u724c\u3001\u578b\u53f7\u4e0e\u5546\u5bb6\uff1b\u9009\u578b\u5e94\u57fa\u4e8e\u533b\u5631\u8981\u6c42\u7684\u4f9b\u6c27\u91cf\u4e0e\u4f7f\u7528\u65f6\u957f\uff0c\u4e0e\u533b\u62a4\u548c\u4e13\u4e1a\u673a\u6784\u786e\u8ba4\u540e\u9009\u62e9\u3002"

CONS_SAFETY = [
    ("1", "\u4e25\u7981\u660e\u706b\u4e0e\u6cb9\u70df", "\u4e25\u7981\u9760\u8fd1\u660e\u706b\u53d6\u6696\u3001\u505a\u996d\u3001\u4f7f\u7528\u71c3\u6c14\u7076\uff1b\u53a8\u623f\u6cb9\u70df\u73af\u5883\u7981\u6b62\u4f7f\u7528"),
    ("2", "\u4e25\u7981\u5438\u70df", "\u6c27\u7597\u671f\u95f4\u4e25\u7981\u5438\u70df\uff0c\u6c27\u6d53\u5ea6\u9ad8\u7684\u73af\u5883\u4f1a\u52a9\u71c3"),
    ("3", "\u4e25\u7981\u4f7f\u7528\u6253\u706b\u673a\u4e0e\u660e\u706b\u7269\u54c1", "\u6253\u706b\u673a\u3001\u9999\u70db\u3001\u82b1\u70b8\u3001\u660e\u706b\u53d6\u6696\u8bbe\u5907\u4e00\u5f8b\u8fdc\u79bb"),
    ("4", "\u6c27\u6c14\u74f6\u56fa\u5b9a\u9632\u503e\u5012", "\u4f7f\u7528\u74f6\u88c5\u6c27\u987b\u56fa\u5b9a\u6216\u4f7f\u7528\u5e26\u8f6e\u5e95\u5ea7\uff0c\u8f6c\u8fd0\u65f6\u4fdd\u6301\u76f4\u7acb"),
    ("5", "\u5236\u6c27\u673a\u653e\u5728\u901a\u98ce\u5904", "\u4e0d\u653e\u5728\u72ed\u5c0f\u4e0d\u901a\u98ce\u7684\u7a7a\u95f4\uff0c\u4fdd\u6301\u6392\u98ce\u53e3\u901a\u7545\u4e0d\u906e\u6321"),
    ("6", "\u7981\u6b62\u6cb9\u8102\u6e05\u6ed1\u7ba1\u8def", "\u4e0d\u5f97\u7528\u98df\u7528\u6cb9\u3001\u6e05\u6ed1\u8102\u5904\u7406\u6c27\u6c14\u7ba1\u8def\u4e0e\u63a5\u5934"),
    ("7", "\u8c28\u614e\u4f7f\u7528\u6613\u53d1\u70ed\u7535\u5668", "\u7535\u70ed\u6bef\u3001\u53d6\u6696\u5668\u7b49\u9700\u6c27\u73af\u5883\u4e0b\u957f\u65f6\u95f4\u4f7f\u7528\u98ce\u9669\u9ad8\uff0c\u8c28\u614e\u4f7f\u7528"),
    ("8", "\u6ce8\u610f\u9759\u7535", "\u5e72\u71e5\u5b63\u8282\u6ce8\u610f\u9759\u7535\u79ef\u805a\uff0c\u89e6\u53ca\u8bbe\u5907\u524d\u53ef\u5148\u89e6\u78b0\u63a5\u5730\u91d1\u5c5e"),
    ("9", "\u8fdc\u79bb\u706b\u6e90\u7269\u54c1", "\u706b\u70b7\u3001\u9152\u7cbe\u706f\u3001\u6c34\u70df\u3001\u9b3c\u9999\u7b49\u4e00\u5f8b\u8fdc\u79bb"),
    ("10", "\u7ba1\u8def\u4e0d\u5f2f\u6298\u4e0d\u538b\u6298", "\u7ba1\u8def\u6253\u6298\u4f1a\u4f7f\u5b9e\u9645\u8fdb\u5165\u91cf\u8fdc\u4f4e\u4e8e\u8bbe\u5b9a\u503c\uff0c\u7761\u89c9\u65f6\u5c24\u5176\u6ce8\u610f"),
]

RED_LINE = "\u7ea2\u7ebf\u672c\u8eab\u4e0d\u53ef\u534f\u5546\uff1a\u5c0f\u5fc3\u4e00\u70b9\u4e0d\u662f\u53ef\u63a5\u53d7\u7684\u6267\u884c\u65b9\u5f0f\u3002"

FLOW_RULES = [
    ("\u89c9\u5f97\u6c14\u4e0d\u591f\u3001\u60f3\u8c03\u5927\u6d41\u91cf", "\u4e0d\u81ea\u884c\u8c03\u6574\uff0c\u8bb0\u5f55\u75c7\u72b6\u4e0e\u5b9e\u9645\u4f7f\u7528\u60c5\u51b5\uff0c\u8054\u7cfb\u533b\u751f"),
    ("\u89c9\u5f97\u6d41\u91cf\u592a\u5927\u3001\u4e0d\u8212\u670d", "\u4e0d\u81ea\u884c\u8c03\u6574\uff0c\u8bb0\u5f55\u540e\u8054\u7cfb\u533b\u751f"),
    ("\u8bbe\u5907\u663e\u793a\u4e0e\u8bbe\u5b9a\u4e0d\u7b26", "\u505c\u6b62\u4f7f\u7528\u5e76\u8054\u7cfb\u7ef4\u4fee\uff0c\u4e0d\u81ea\u884c\u6821\u51c6"),
    ("\u6362\u7528\u5176\u4ed6\u8bbe\u5907\u540e\u611f\u89c9\u4e0d\u540c", "\u4e0d\u81ea\u884c\u6539\u4e3a\u65e7\u6d41\u91cf\uff0c\u8054\u7cfb\u533b\u751f\u91cd\u65b0\u8bc4\u4f30"),
    ("\u533b\u751f\u8c03\u6574\u4e86\u6d41\u91cf", "\u6309\u65b0\u533b\u5631\u6267\u884c\uff0c\u5e76\u66f4\u65b0\u8bb0\u5f55\u8868"),
]

FLOW_GATE = "\u6c27\u6c14\u6d41\u91cf\u5fc5\u987b\u9075\u533b\u5631\uff0c\u4efb\u4f55\u4eba\u4e0d\u5f97\u81ea\u884c\u8c03\u6574\uff0c\u5305\u62ec\u5bb6\u5c5e\u3002"

FLOW_WHY = "\u6d41\u91cf\u4e0e\u662f\u5426\u9700\u8981\u6c27\u7597\u3001\u76ee\u6807\u6c27\u5408\u6c34\u5e73\u76f8\u5173\uff0c\u90e8\u5206\u60a3\u8005\u5728\u6d41\u91cf\u8fc7\u5927\u65f6\u53ef\u80fd\u51fa\u73b0\u4e8c\u6c27\u5316\u78b3\u6e0f\u7559\u52a0\u91cd\u3002\u662f\u5426\u9700\u8981\u5438\u6c27\u3001\u9700\u8981\u591a\u5c11\uff0c\u5c5e\u4e8e\u533b\u7597\u5224\u65ad\u3002"

ATOMIZER = [
    "\u662f\u5426\u53ef\u4ee5\u540c\u65f6\u8fdb\u884c\u3001\u88c5\u7f6e\u5982\u4f55\u8fde\u63a5\uff0c\u5fc5\u987b\u7531\u533b\u62a4\u6307\u5bfc\u4e0e\u786e\u8ba4",
    "\u4e0d\u6309\u5382\u5546\u8bf4\u660e\u4e4b\u5916\u7684\u65b9\u5f0f\u81ea\u884c\u6539\u88c5\u8fde\u63a5",
    "\u4f7f\u7528\u4e2d\u6301\u7eed\u89c2\u5bdf\u547c\u5438\u4e0e\u9762\u8272\uff0c\u51fa\u73b0\u5f02\u5e38\u7acb\u5373\u505c\u6b62\u5e76\u8054\u7cfb\u533b\u62a4",
    "\u6309\u533b\u5631\u5b89\u6392\u65f6\u95f4\uff0c\u4e0d\u81ea\u884c\u53e0\u52a0\u65f6\u957f",
    "\u4e25\u7981\u5728\u6c27\u6c14\u9644\u8fd1\u8fdb\u884c\u4efb\u4f55\u4ea7\u751f\u706b\u82b1\u7684\u64cd\u4f5c",
]

SUCTION_BOUNDARY = [
    "\u5438\u75f0\u662f\u4fb5\u5165\u6027\u64cd\u4f5c\uff0c\u5fc5\u987b\u7531\u533b\u62a4\u6307\u5bfc\uff0c\u5bb6\u5ead\u4e0d\u5f97\u5728\u65e0\u4eba\u6307\u5bfc\u7684\u60c5\u51b5\u4e0b\u81ea\u884c\u5b9e\u65bd\u3002",
]

SUCTION_RISK = [
    "\u4f4e\u6c27\uff1a\u5438\u75f0\u8fc7\u7a0b\u4e2d\u53ef\u80fd\u5f15\u8d77\u8840\u6c27\u4e0b\u964d",
    "\u5fc3\u5f8b\u5931\u5e38\uff1a\u8ff7\u8d70\u53cd\u5c04\u53ef\u80fd\u5f15\u8d77\u5fc3\u7387\u53d8\u5316",
    "\u6c14\u9053\u9ecf\u819c\u635f\u4f24\uff1a\u53cd\u590d\u6216\u7c97\u66b4\u64cd\u4f5c\u53ef\u635f\u4f24\u9ecf\u819c",
    "\u611f\u67d3\uff1a\u65e0\u83cc\u64cd\u4f5c\u5230\u4f4d\u4e0d\u5230\u4f4d\u53ef\u5e26\u5165\u611f\u67d3",
    "\u6c14\u9053\u75db\u5236\uff1a\u654f\u611f\u6c14\u9053\u8005\u53ef\u80fd\u53d1\u751f\u75db\u5236",
]

SUCTION_CAN = [
    "\u9700\u8981\u5438\u75f0\u7684\u6307\u5f81\u7531\u533b\u751f\u5224\u65ad\uff0c\u4e0d\u81ea\u884c\u5224\u65ad\u75bd\u591a\u5c31\u8be5\u5438",
    "\u5b66\u4e60\u5224\u65ad\u75bd\u7684\u6027\u72b6\u5e76\u8bb0\u5f55\uff0c\u4f9b\u533b\u751f\u53c2\u8003",
    "\u4fdd\u6301\u547c\u5438\u9053\u6e7f\u5316\u4e0e\u4f53\u4f4d\u6446\u653e\u5f53\u4e39\uff0c\u51cf\u5c11\u75bd\u6db2\u79ef\u805a",
    "\u5907\u597d\u5438\u5f15\u88c5\u7f6e\u4e0e\u65e0\u83cc\u7528\u54c1\uff08\u7531\u533b\u62a4\u6307\u5bfc\u578b\u53f7\u4e0e\u51c6\u5907\u65b9\u5f0f\uff09",
    "\u51fa\u73b0\u7ea2\u7ebf\u60c5\u5f62\u7acb\u5373\u505c\u6b62\u5e76\u5c31\u533b",
]

SUCTION_STOP = [
    "\u5438\u75f0\u65f6\u51fa\u73b0\u5267\u70c8\u541d\u55fd",
    "\u51fa\u73b0\u8840\u6c27\u4e0b\u964d\u8868\u73b0",
    "\u5fc3\u7387\u660e\u663e\u589e\u5feb",
    "\u5438\u75f0\u7ba1\u63d2\u5165\u65f6\u9047\u5230\u660e\u663e\u963b\u529b\uff08\u4e0d\u5f3a\u884c\u63d2\u5165\uff09",
]

SUCTION_ABSOLUTE = [
    "\u4e0d\u81ea\u884c\u52a8\u4f5c\u89c4\u8303",
    "\u4e0d\u7ed9\u51fa\u5438\u75f0\u6df1\u5ea6",
    "\u4e0d\u7ed9\u51fa\u8d1f\u538b\u6570\u503c",
    "\u4e0d\u7ed9\u51fa\u5355\u6b21\u5438\u75f0\u65f6\u95f4\u4e0a\u9650",
    "\u4e0d\u7ed9\u51fa\u6bcf\u65e5\u5438\u75f0\u6b21\u6570\u4e0a\u9650",
]

INFECTION = [
    "\u624b\u536b\u751f\uff1a\u63a5\u89e6\u7ba1\u8def\u3001\u6e7f\u5316\u74f6\u3001\u9f3b\u6c27\u7ba1\u524d\u540e\u6d17\u624b\uff1b\u5e74\u8f83\u5927\u5bb6\u5c5e\u534f\u52a9\u8005\u540c\u6837\u6267\u884c",
    "\u53e3\u8154\u62a4\u7406\uff1a\u6bcf\u65e5\u53e3\u8154\u6e05\u6d01\uff0c\u51cf\u5c11\u53e3\u54bd\u90e8\u5b9a\u690d\u83cc\u8fdb\u5165\u6c14\u9053",
    "\u7ba1\u8def\u7ba1\u7406\uff1a\u4e0d\u591a\u4eba\u5171\u7528\uff0c\u4e0d\u968f\u610f\u6539\u88c5\uff0c\u4e0d\u5171\u7528\u6e7f\u5316\u74f6",
    "\u73af\u5883\uff1a\u6bcf\u65e5\u901a\u98ce\uff0c\u5ba4\u5185\u907f\u514d\u7c89\u5c18\u3001\u70df\u96fe\u3001\u9999\u85b0\u4e0e\u6e05\u6d01\u5242\u55b7\u96fe",
    "\u5b58\u653e\uff1a\u7ba1\u8def\u4e0e\u8017\u6750\u5e72\u71e5\u6e05\u6d01\u4fdd\u5b58\uff0c\u907f\u5f00\u6f6e\u6e7f\u6216\u9633\u5149\u76f4\u5c04",
    "\u8bbe\u5907\u5916\u90e8\uff1a\u5236\u6c27\u673a\u5916\u90e8\u5b9a\u671f\u64e6\u62ed\uff0c\u6ee4\u7f51\u6e05\u6d01\u6309\u8bf4\u660e\u6267\u884c",
    "\u611f\u67d3\u5f81\u8c61\uff1a\u75bd\u91cf\u7a81\u7136\u589e\u591a\u3001\u53d8\u9ec4\u53d8\u7a20\u3001\u51fa\u73b0\u81ed\u5473\u3001\u53d1\u70ed\u5f53\u5929\u5c31\u533b",
]

EMERGENCY = [
    "dyspnea_worse", "cyanosis", "consciousness_change", "co2_retention",
    "chest_pain", "breath_rate_abnormal", "apnea", "pink_sputum", "hemoptysis",
]

EMERGENCY_TEXT = {
    "dyspnea_worse": "\u547c\u5438\u56f0\u96be\u52a0\u91cd\uff1a\u5b89\u9759\u72b6\u6001\u4e0b\u4e5f\u6c14\u4fc3\u3001\u8bf4\u8bdd\u4e0d\u80fd\u6210\u53e5",
    "cyanosis": "\u53e3\u5507\u7532\u5e8a\u53d1\u7d2b\uff08\u53d1\u7d2b\uff09",
    "consciousness_change": "\u610f\u8bc6\u6539\u53d8\uff1a\u5609\u7761\u53eb\u4e0d\u9192\u3001\u70e6\u8e81\u3001\u610f\u8bc6\u6a21\u7cca\u3001\u53cd\u5e94\u8fdf\u949d",
    "co2_retention": "\u4e8c\u6c27\u5316\u78b3\u6e0f\u7559\u8868\u73b0\uff1a\u6668\u8d77\u5934\u75db\u3001\u5609\u7761\u3001\u6251\u7ffc\u6837\u9707\u98a4\u3001\u76ae\u80a4\u6e7f\u51b7",
    "chest_pain": "\u7a81\u53d1\u5267\u70c8\u80f8\u75db\u3001\u80f8\u95f7\u4f34\u5927\u6c57",
    "breath_rate_abnormal": "\u547c\u5438\u9891\u7387\u660e\u663e\u589e\u5feb\u6216\u51cf\u6162\u3001\u8282\u5f8b\u4e0d\u89c4\u5219",
    "apnea": "\u610f\u8bc6\u4e22\u5931\u540e\u4ecd\u6709\u547c\u5438\u4f46\u51fa\u73b0\u547c\u5438\u6682\u505c",
    "pink_sputum": "\u5499\u5927\u91cf\u7c89\u7ea2\u8272\u6d6a\u6cab\u75c5",
    "hemoptysis": "\u5499\u8840\u6216\u75c0\u4e2d\u5e26\u8840",
}

SAME_DAY = [
    "fever_sputum_change", "fever", "new_discomfort", "usage_mismatch", "device_failure",
]

SAME_DAY_TEXT = {
    "fever_sputum_change": "\u53d1\u70ed\u4f34\u75bd\u91cf\u7a81\u7136\u589e\u591a\u3001\u53d8\u9ec4\u53d8\u7a20\u3001\u51fa\u73b0\u81ed\u5473",
    "fever": "\u53d1\u70ed",
    "new_discomfort": "\u65b0\u51fa\u73b0\u7684\u4e0d\u9002\uff1a\u5934\u6655\u3001\u529b\u7aed\u3001\u5fc3\u6162\u3001\u660e\u663e\u5609\u7761",
    "usage_mismatch": "\u5b9e\u9645\u4f7f\u7528\u91cf\u4e0e\u533b\u5631\u4e0d\u7b26",
    "device_failure": "\u8bbe\u5907\u6545\u969c\u5f71\u54cd\u5438\u6c27",
}

ASK_DOCTOR = [
    "\u80fd\u5426\u79bb\u9662\u3001\u5916\u51fa\u3001\u957f\u9014\u51fa\u884c",
    "\u80fd\u5426\u4e58\u5750\u98de\u673a",
    "\u80fd\u5426\u8fdb\u884c\u624b\u672f\u3001\u6709\u65e0\u7279\u6b8a\u60c5\u51b5",
    "\u6d41\u91cf\u4e0e\u6bcf\u65e5\u4f7f\u7528\u65f6\u957f\u8c03\u6574",
    "\u96fe\u5316\u4e0e\u5438\u6c27\u80fd\u5426\u540c\u65f6\u8fdb\u884c",
    "\u662f\u5426\u9700\u8981\u589e\u52a0\u5176\u4ed6\u76d1\u62a4\u6216\u8bbe\u5907",
    "\u505c\u7535\u65f6\u5907\u7528\u6c27\u6e90\u662f\u5426\u5fc5\u8981",
]

ASK_DOCTOR_NOTE = "\u4e0a\u8ff0\u4e8b\u9879\u5747\u5c5e\u533b\u7597\u51b3\u7b56\uff0c\u4e0d\u5f97\u81ea\u884c\u51b3\u5b9a\u3002"

FORBIDDEN = [
    "\u7981\u6b62\u81ea\u884c\u52a0\u5927\u6c27\u6c14\u6d41\u91cf",
    "\u7981\u6b62\u9760\u8fd1\u660e\u706b\u53d6\u6696\u6216\u505a\u996d",
    "\u7981\u6b62\u5728\u6c27\u6c14\u65c1\u5438\u70df\u6216\u4f7f\u7528\u6253\u706b\u673a",
    "\u7981\u6b62\u7528\u98df\u7528\u6cb9\u6e05\u6ed1\u6c27\u6c14\u7ba1\u8def",
    "\u7981\u6b62\u6c27\u6c14\u74f6\u4e0d\u56fa\u5b9a",
    "\u7981\u6b62\u628a\u5236\u6c27\u673a\u653e\u5728\u901a\u98ce\u4e0d\u826f\u7684\u72ed\u5c0f\u7a7a\u95f4",
    "\u7981\u6b62\u5835\u585e\u5236\u6c27\u673a\u6392\u98ce\u53e3",
    "\u7981\u6b62\u81ea\u884c\u5728\u5bb6\u5b9e\u65bd\u5438\u75f0",
    "\u7981\u6b62\u81ea\u884c\u6539\u88c5\u7ba1\u8def\u6216\u8bbe\u5907\u53c2\u6570",
]


def device_meta(key):
    for k, name, way, noise, power, feature, focus in DEVICES:
        if k == key:
            return name, way, noise, power, feature, focus
    return key, "", "", "", "", ""


def validate_list(raw, valid_keys):
    good, bad = [], []
    for k in list(raw or []):
        if k in valid_keys:
            good.append(k)
        else:
            bad.append(k)
    return good, bad


def per_year(days):
    d = float(days or 0)
    if d <= 0:
        return 0.0
    return round(365.0 / d, 2)


def yearly_cost(unit_price, days):
    return round(float(unit_price or 0) * per_year(days), 2)


def usage_days(hours_per_day, days_per_month, months):
    return round(float(hours_per_day or 0) * float(days_per_month or 0) * float(months or 0), 2)


def build_cost(items):
    lines = []
    lines.append("\u8017\u6750\u5468\u671f\u4e0e\u5e74\u8017\u6750\u6210\u672c\u4f30\u7b97\uff1a")
    total = 0.0
    for it in items or []:
        label = str(it.get("name", "") or "")
        days = it.get("days", 0)
        price = it.get("unit_price", 0)
        times = per_year(days)
        cost = yearly_cost(price, days)
        total += cost
        lines.append("  - %s\uff1a\u66f4\u6362\u5468\u671f %g \u5929\uff0c\u5e74\u66f4\u6362 %.2f \u6b21\uff0c\u5e74\u6210\u672c %.2f \u5143"
                     % (label, float(days or 0), times, cost))
        if float(days or 0) <= 0:
            lines.append("      \u5468\u671f\u975e\u6cd5\uff0c\u8bf7\u6838\u5b9e\u540e\u91cd\u7b97")
    lines.append("  \u5e74\u8017\u6750\u6210\u672c\u5408\u8ba1\uff1a%.2f \u5143" % round(total, 2))
    lines.append("  \u53e3\u5f84\uff1a\u5468\u671f\u4ee5\u4ea7\u54c1\u8bf4\u660e\u4e0e\u533b\u62a4\u5efa\u8bae\u4e3a\u51c6\uff0c\u4e0d\u540c\u4ea7\u54c1\u5dee\u5f02\u5f88\u5927\u3002")
    lines.append("  \u9f3b\u6c27\u7ba1\u4e0e\u6e7f\u5316\u74f6\u5c5e\u9ad8\u9891\u63a5\u89e6\u6c14\u9053\u7684\u8017\u6750\uff0c\u6309\u8bf4\u660e\u4e0e\u533b\u62a4\u5efa\u8bae\u6267\u884c\uff0c\u4e0d\u8981\u4e3a\u7701\u94b1\u5ef6\u957f\u4f7f\u7528\u3002")
    return lines, round(total, 2)


def build_safety():
    lines = []
    lines.append("\u5341\u6761\u6c27\u6c14\u5b89\u5168\u7ea2\u7ebf\uff1a")
    for no, name, req in CONS_SAFETY:
        lines.append("  %s %s" % (no, name))
        lines.append("      \u8981\u6c42\uff1a" + req)
    lines.append("  " + RED_LINE)
    lines.append("")
    lines.append("\u6c27\u6c14\u6d41\u91cf\u8c03\u6574\u53e3\u5f84\uff1a")
    lines.append("  " + FLOW_GATE)
    for scene, action in FLOW_RULES:
        lines.append("  - %s\uff1a%s" % (scene, action))
    lines.append("  \u539f\u56e0\uff1a" + FLOW_WHY)
    lines.append("  \u53e3\u5f84\uff1a\u672c\u5de5\u5177\u4e0d\u63d0\u4f9b\u4efb\u4f55\u6d41\u91cf\u6570\u503c\u3002")
    lines.append("")
    lines.append("\u96fe\u5316\u4e0e\u5438\u6c27\u540c\u65f6\u8fdb\u884c\u65f6\u7684\u6ce8\u610f\uff1a")
    for a in ATOMIZER:
        lines.append("  - " + a)
    lines.append("  \u53e3\u5f84\uff1a\u4e0d\u63d0\u4f9b\u96fe\u5316\u836f\u7269\u3001\u96fe\u5316\u5242\u91cf\u4e0e\u8fde\u63a5\u65b9\u6848\uff0c\u53ef\u884c\u6027\u7531\u533b\u751f\u5224\u65ad\u3002")
    lines.append("")
    lines.append("\u5438\u75f0\u5b89\u5168\u8fb9\u754c\uff1a")
    for b in SUCTION_BOUNDARY:
        lines.append("  " + b)
    lines.append("  \u98ce\u9669\uff1a")
    for r in SUCTION_RISK:
        lines.append("    - " + r)
    lines.append("  \u5bb6\u5ead\u53ef\u505a\u7684\u51c6\u5907\uff1a")
    for c in SUCTION_CAN:
        lines.append("    - " + c)
    lines.append("  \u5fc5\u987b\u7acb\u5373\u505c\u6b62\u5e76\u5c31\u533b\u7684\u5438\u75f0\u76f8\u5173\u60c5\u5f62\uff1a")
    for s in SUCTION_STOP:
        lines.append("    - " + s)
    lines.append("  \u7edd\u5bf9\u7981\u6b62\uff1a")
    for a in SUCTION_ABSOLUTE:
        lines.append("    - " + a)
    return lines


def build_report(data):
    dkey = data.get("device", "concentrator")
    hpd = data.get("hours_per_day", 0)
    dpm = data.get("days_per_month", 0)
    months = data.get("months", 12)
    flags = list(data.get("red_flags", []))
    cost_only = bool(data.get("cost_only", False))

    lines = []
    lines.append("=" * 66)
    lines.append("\u5c45\u5bb6\u6c27\u7597\u8017\u6750\u5468\u671f\u4e0e\u5b89\u5168\u6838\u67e5")
    lines.append("=" * 66)
    lines.append("\u6bcf\u65e5\u4f7f\u7528\u5c0f\u65f6\u6570\uff1a%g   \u6bcf\u6708\u4f7f\u7528\u5929\u6570\uff1a%g   \u8ba1\u7b97\u6708\u6570\uff1a%g"
                 % (float(hpd or 0), float(dpm or 0), float(months or 0)))
    lines.append("")

    hit = [f for f in flags if f in EMERGENCY]
    sd = [f for f in flags if f in SAME_DAY]
    unknown = [f for f in flags if f not in EMERGENCY and f not in SAME_DAY]
    if hit or sd:
        lines.append("[\u7ea2\u7ebf] \u5df2\u547d\u4e2d\u4ee5\u4e0b\u60c5\u5f62\uff0c\u5148\u5904\u7f6e\u518d\u8c08\u5176\u4ed6\uff1a")
        for f in hit:
            lines.append("  ! \u7acb\u5373\u6025\u8bca\uff1a" + EMERGENCY_TEXT[f])
        for f in sd:
            lines.append("  ! \u5f53\u5929\u5c31\u533b\uff1a" + SAME_DAY_TEXT[f])
        lines.append("")
        lines.append("  \u672c\u5de5\u5177\u4e0d\u7ed9\u9002\u5e94\u8bc1\u6570\u5b57\uff0c\u4e0d\u7ed9\u6d41\u91cf\u6570\u503c\uff0c\u4e0d\u7ed9\u5438\u75f0\u53c2\u6570\u3002")
        lines.append("=" * 66)
        return "\n".join(lines), {
            "blocked": True,
            "emergency": hit,
            "same_day": sd,
            "unknown_flags": unknown,
            "indication_number_provided": False,
            "flow_value_provided": False,
            "suction_params_provided": False,
        }

    name, way, noise, power, feature, focus = device_meta(dkey)
    lines.append("[\u4e00] \u8bbe\u5907\u7c7b\u578b\u5bf9\u7167")
    for k, nm, w, ns, pw, ft, fc in DEVICES:
        mark = "[\u5f53\u524d]" if k == dkey else ""
        lines.append("  %s %s\uff5c\u65b9\u5f0f\uff1a%s" % (mark, nm, w))
        lines.append("      \u566a\u97f3\uff1a%s   \u8017\u7535\uff1a%s" % (ns, pw))
        lines.append("      \u7279\u70b9\uff1a" + ft)
        lines.append("      \u9009\u578b\u5173\u6ce8\uff1a" + fc)
    lines.append("  " + DEVICE_NOTE)
    lines.append("")

    lines.append("[\u4e8c] \u4f7f\u7528\u91cf\u4e0e\u8017\u6750\u5468\u671f")
    ud = usage_days(hpd, dpm, months)
    lines.append("  \u6309\u5f53\u524d\u8f93\u5165\u4f30\u7b97\u7684\u603b\u4f7f\u7528\u5c0f\u65f6\u6570\uff1a%.2f \u5c0f\u65f6" % ud)
    lines.append("  \u53e3\u5f84\uff1a\u4ec5\u4f9b\u89c4\u6a21\u611f\u77e5\uff0c\u4e0d\u4ee3\u8868\u533b\u5631\u3002\u6bcf\u65e5\u4f7f\u7528\u65f6\u957f\u7531\u533b\u751f\u89c4\u5b9a\u3002")
    cost_lines, total_cost = build_cost(data.get("items", []))
    for line in cost_lines:
        lines.append("  " + line if line else "")
    lines.append("")

    lines.append("[\u4e09] \u611f\u67d3\u9884\u9632")
    for i in INFECTION:
        lines.append("  - " + i)
    lines.append("")

    lines.append("[\u56db] \u6c27\u6c14\u5b89\u5168\u4e0e\u5438\u75f0\u8fb9\u754c")
    for line in build_safety():
        lines.append("  " + line if line else "")
    lines.append("")

    lines.append("[\u4e94] \u5fc5\u987b\u7acb\u5373\u5c31\u533b\u6216\u5f53\u5929\u5c31\u533b\u7684\u60c5\u5f62")
    for k in EMERGENCY:
        lines.append("  ! \u7acb\u5373\u6025\u8bca\uff1a" + EMERGENCY_TEXT[k])
    for k in SAME_DAY:
        lines.append("  - \u5f53\u5929\u5c31\u533b\uff1a" + SAME_DAY_TEXT[k])
    lines.append("")
    lines.append("[\u516d] \u5fc5\u987b\u5411\u533b\u751f\u786e\u8ba4\u7684\u4e8b\u9879")
    for q in ASK_DOCTOR:
        lines.append("  - " + q)
    lines.append("  " + ASK_DOCTOR_NOTE)
    lines.append("")
    lines.append("[\u4e03] \u660e\u786e\u7981\u6b62\u7684\u5c45\u5bb6\u64cd\u4f5c")
    for f in FORBIDDEN:
        lines.append("  - " + f)
    lines.append("")
    lines.append("\u514d\u8d23\uff1a\u672c\u7ed3\u679c\u4e3a\u8017\u6750\u5468\u671f\u4e0e\u5b89\u5168\u6838\u67e5\u53c2\u8003\uff0c\u4e0d\u6784\u6210\u533b\u7597\u610f\u89c1\u3002")
    lines.append("\u6c27\u7597\u9002\u5e94\u8bc1\u4e0e\u6c27\u6c14\u6d41\u91cf\u5fc5\u987b\u7531\u533b\u751f\u8bc4\u4f30\u786e\u5b9a\uff0c\u5438\u75f0\u7cfb\u4fb5\u5165\u6027\u64cd\u4f5c\u5fc5\u987b\u7531\u533b\u62a4\u6307\u5bfc\u3002")
    lines.append("\u5168\u90e8\u533b\u5b66\u53e3\u5f84\u4ee5\u6700\u65b0\u7248\u76f8\u5173\u6307\u5357\u548c\u4e3b\u6cbb\u533b\u751f\u5224\u65ad\u4e3a\u51c6\u3002")
    lines.append("=" * 66)

    summary = {
        "blocked": False,
        "unknown_flags": unknown,
        "device_name": name,
        "usage_hours_estimate": ud,
        "yearly_consumable_cost": total_cost,
        "device_recommended": False,
        "indication_number_provided": False,
        "flow_value_provided": False,
        "suction_params_provided": False,
        "medication_provided": False,
        "safety_items": len(CONS_SAFETY),
    }
    return "\n".join(lines), summary


def _run_checks():
    r = []
    r.append(("\u8bbe\u5907\u7c7b\u578b\u4e3a 4 \u7c7b", len(DEVICES) == 4))
    r.append(("\u5b89\u5168\u7ea2\u7ebf\u4e3a 10 \u6761", len(CONS_SAFETY) == 10))
    r.append(("\u6d41\u91cf\u8c03\u6574\u60c5\u5f62\u4e0d\u5c11\u4e8e 5 \u79cd", len(FLOW_RULES) >= 5))
    r.append(("\u96fe\u5316\u6ce8\u610f\u4e0d\u5c11\u4e8e 5 \u9879", len(ATOMIZER) >= 5))
    r.append(("\u5438\u75f0\u98ce\u9669\u4e3a 5 \u7c7b", len(SUCTION_RISK) == 5))
    r.append(("\u5438\u75f0\u4e25\u7981\u6b62\u4e3a 5 \u6761", len(SUCTION_ABSOLUTE) == 5))
    r.append(("\u611f\u67d3\u9884\u9632\u4e0d\u5c11\u4e8e 7 \u9879", len(INFECTION) >= 7))
    r.append(("\u6025\u8bca\u60c5\u5f62\u4e3a 9 \u9879", len(EMERGENCY) == 9))
    r.append(("\u5f53\u5929\u60c5\u5f62\u4e3a 5 \u9879", len(SAME_DAY) == 5))
    r.append(("\u5f85\u533b\u751f\u786e\u8ba4\u4e0d\u5c11\u4e8e 7 \u9879", len(ASK_DOCTOR) >= 7))
    r.append(("\u7981\u6b62\u64cd\u4f5c\u4e0d\u5c11\u4e8e 9 \u6761", len(FORBIDDEN) >= 9))
    r.append(("\u6240\u6709\u533b\u62a4\u53e3\u5f84\u5747\u5b58\u5728", bool(FLOW_GATE) and bool(FLOW_WHY) and bool(RED_LINE)))

    all_dev = [k for k, _n, _w, _ns, _p, _f, _fc in DEVICES]
    good, bad = validate_list(["liquid", "zzz"], all_dev)
    r.append(("\u5df2\u8bc6\u522b\u8bbe\u5907\u7c7b\u578b\u8ba1\u6570\u6b63\u786e", good == ["liquid"]))
    r.append(("\u672a\u8bc6\u522b\u8bbe\u5907\u7c7b\u578b\u88ab\u8fc7\u6ee4", bad == ["zzz"]))
    r.append(("\u6db2\u6c27\u7c7b\u578b\u53ef\u67e5\u5230\u566a\u97f3\u4e0e\u8017\u7535", device_meta("liquid")[2] == "\u65e0"))
    r.append(("\u672a\u77e5\u8bbe\u5907\u8fd4\u56de\u7a7a\u5173\u6ce8", device_meta("zzz")[5] == ""))
    r.append(("\u56db\u7c7b\u8bbe\u5907\u5747\u6709\u9009\u578b\u5173\u6ce8\u70b9", all(len(t[6]) >= 5 for t in DEVICES)))

    r.append(("\u5468\u671f 30 \u5929\u5e74\u66f4\u6362 12.17 \u6b21", abs(per_year(30) - 12.17) < 0.01))
    r.append(("\u5468\u671f 365 \u5929\u5e74\u66f4\u6362 1 \u6b21", per_year(365) == 1.0))
    r.append(("\u5468\u671f 0 \u5929\u8fd4\u56de 0", per_year(0) == 0.0))
    r.append(("\u5468\u671f\u4e3a\u8d1f\u65f6\u8fd4\u56de 0", per_year(-5) == 0.0))
    r.append(("\u5e74\u8017\u6750\u6210\u672c\u8ba1\u7b97\u6b63\u786e", yearly_cost(10, 365) == 10.0))
    r.append(("\u5468\u671f 30 \u5929\u65f6\u5e74\u6210\u672c\u6b63\u786e", abs(yearly_cost(30, 30) - 365.1) < 0.05))
    r.append(("\u5355\u4ef7\u4e3a\u96f6\u65f6\u5e74\u6210\u672c\u4e3a\u96f6", yearly_cost(0, 30) == 0.0))

    r.append(("\u4f7f\u7528\u91cf\u4f30\u7b97\u6b63\u786e", usage_days(2, 30, 12) == 720.0))
    r.append(("\u4f7f\u7528\u91cf\u6bcf\u65e5\u96f6\u5c0f\u65f6\u4e3a\u96f6", usage_days(0, 30, 12) == 0.0))

    c1, tot = build_cost([{"name": "\u9f3b\u6c27\u7ba1", "days": 30, "unit_price": 10},
                           {"name": "\u6e7f\u5316\u74f6", "days": 7, "unit_price": 5}])
    r.append(("\u8017\u6750\u5217\u8868\u884c\u6570\u6b63\u786e", len(c1) == 6))
    r.append(("\u5e74\u8017\u6750\u6210\u672c\u5408\u8ba1\u5927\u4e8e\u96f6", tot > 0))
    r.append(("\u5468\u671f\u975e\u6cd5\u65f6\u7ed9\u51fa\u63d0\u793a",
              "\u5468\u671f\u975e\u6cd5" in "\n".join(build_cost([{"name": "x", "days": 0}])[0])))
    r.append(("\u7a7a\u5217\u8868\u4ecd\u80fd\u8f93\u51fa\u5408\u8ba1", build_cost([])[1] == 0.0))

    _, s = build_report({"device": "concentrator", "hours_per_day": 2, "days_per_month": 30,
                         "items": [{"name": "\u9f3b\u6c27\u7ba1", "days": 30, "unit_price": 10}]})
    r.append(("\u5b8c\u6574\u6837\u4f8b\u4e0d\u963b\u65ad", s["blocked"] is False))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u8bbe\u5907\u540d\u6b63\u786e", s["device_name"] == "\u6d53\u7f29\u5f0f\u5236\u6c27\u673a"))
    r.append(("\u5b8c\u6574\u6837\u4f8b\u4f7f\u7528\u91cf\u4e3a 720", s["usage_hours_estimate"] == 720.0))
    r.append(("\u4e0d\u7ed9\u9002\u5e94\u8bc1\u6570\u5b57", s["indication_number_provided"] is False))
    r.append(("\u4e0d\u7ed9\u6d41\u91cf\u6570\u503c", s["flow_value_provided"] is False))
    r.append(("\u4e0d\u7ed9\u5438\u75f0\u53c2\u6570", s["suction_params_provided"] is False))
    r.append(("\u4e0d\u7ed9\u836f\u7269", s["medication_provided"] is False))
    r.append(("\u4e0d\u63a8\u8350\u5177\u4f53\u578b\u53f7", s["device_recommended"] is False))
    r.append(("\u5b89\u5168\u9879\u6570\u4e3a 10", s["safety_items"] == 10))

    _, s2 = build_report({"red_flags": ["cyanosis"]})
    r.append(("\u53d1\u7d2b\u76f4\u63a5\u963b\u65ad", s2["blocked"] is True))
    r.append(("\u963b\u65ad\u65f6\u4e0d\u7ed9\u6d41\u91cf\u6570\u503c", s2["flow_value_provided"] is False))
    r.append(("\u963b\u65ad\u65f6\u533a\u5206\u6025\u8bca\u4e0e\u5f53\u5929", s2["same_day"] == []))

    _, s3 = build_report({"red_flags": ["fever_sputum_change"]})
    r.append(("\u5f53\u5929\u5c31\u533b\u4e5f\u963b\u65ad", s3["blocked"] is True))
    r.append(("\u963b\u65ad\u65f6\u5f53\u5929\u60c5\u5f62\u975e\u7a7a", len(s3["same_day"]) == 1))

    txt, _ = build_report({"device": "liquid"})
    r.append(("\u8f93\u51fa\u542b\u6d41\u91cf\u9075\u533b\u5631\u53e3\u5f84", FLOW_GATE in txt))
    r.append(("\u8f93\u51fa\u542b\u5438\u75f0\u4fb5\u5165\u6027\u8fb9\u754c", SUCTION_BOUNDARY[0] in txt))
    r.append(("\u8f93\u51fa\u542b\u4e0d\u7ed9\u5438\u75f0\u6df1\u5ea6", "\u4e0d\u7ed9\u51fa\u5438\u75f0\u6df1\u5ea6" in txt))
    return r


def selftest():
    results = _run_checks()
    failed = [name for name, ok in results if not ok]
    ok = len(failed) == 0
    lines = ["SELFTEST %s" % ("OK" if ok else "FAILED")]
    lines.append("checks=%d passed=%d failed=%d" % (len(results), len(results) - len(failed), len(failed)))
    for name in failed:
        lines.append("FAILED: %s" % name)
    with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_selftest_result.txt"),
                 "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    return ok


def main():
    parser = argparse.ArgumentParser(
        description="\u5c45\u5bb6\u6c27\u7597\u8017\u6750\u5468\u671f\u4e0e\u5b89\u5168\u6838\u67e5\u5de5\u5177")
    parser.add_argument("--file", help="\u8f93\u5165 JSON \u6587\u4ef6\u8def\u5f84\uff08UTF-8\uff09")
    parser.add_argument("--cost", action="store_true", help="\u53ea\u8f93\u51fa\u8017\u6750\u5468\u671f\u4e0e\u5e74\u8017\u6750\u6210\u672c\u4f30\u7b97")
    parser.add_argument("--json", action="store_true", help="\u4ee5 JSON \u8f93\u51fa")
    parser.add_argument("--out", help="\u7ed3\u679c\u5199\u5165\u6307\u5b9a\u6587\u4ef6")
    parser.add_argument("--selftest", action="store_true", help="\u8fd0\u884c\u81ea\u68c0")
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))

    if args.selftest:
        sys.exit(0 if selftest() else 1)

    if not args.file:
        parser.error("\u9700\u8981 --file \u6216 --selftest")

    with io.open(args.file, "r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)
    if args.cost:
        data["cost_only"] = True

    report, summary = build_report(data)
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else report
    out_path = args.out or os.path.join(here, "_last_result.txt")
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write(body)
    print(body)
    print("")
    print("\u7ed3\u679c\u5df2\u5199\u5165\uff1a%s" % out_path)


if __name__ == "__main__":
    main()
