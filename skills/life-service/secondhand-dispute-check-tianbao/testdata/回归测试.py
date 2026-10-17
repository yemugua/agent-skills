# -*- coding: utf-8 -*-
"""闲鱼二手交易纠纷取证与维权 —— 回归测试（>=40 断言）。

针对 scripts/secondhand_check.py 的公开函数逐项断言，并真跑子进程与 --json。
"""
import json
import os
import re
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPTS)

import secondhand_check as M  # noqa: E402

PASS = []
FAIL = []


def chk(name, cond):
    (PASS if cond else FAIL).append(name)


BASE = date(2026, 10, 4)

# ---------------------------------------------------------------- 基础工具
chk("norm 归一", M.norm(" 未 填写 ") == "未填写")
chk("filled 正常", M.filled("3200元") is True)
chk("unknown 待填", M.unknown("待填") is True)
chk("unknown 待补", M.unknown("待补") is True)
chk("unknown 待确认", M.unknown("待确认") is True)
chk("unknown 斜杠", M.unknown("/") is True)
chk("unknown 未填写", M.unknown("未填写") is True)
chk("unknown None", M.unknown(None) is True)
chk("unknown 占位提示语", M.unknown("有/无") is True)
chk("fmt_num 去 .0", M.fmt_num(7.0) == "7")
chk("fmt_num 小数", M.fmt_num(12.5) == "12.5")
chk("money", M.money(3200) == "¥3200")
chk("parse_num 带单位", M.parse_num("3200元") == 3200.0)
chk("parse_num 无数字", M.parse_num("不清楚") is None)
chk("parse_date 标准", M.parse_date("2026-09-22") == date(2026, 9, 22))
chk("parse_date 中文", M.parse_date("2026年9月22日") == date(2026, 9, 22))
chk("days_between", M.days_between(date(2026, 9, 22), BASE) == 12)

# ---------------------------------------------------------------- yesno
chk("yesno 否", M.yesno("否") is False)
chk("yesno 没有", M.yesno("没有") is False)
chk("yesno 未", M.yesno("未录制") is False)
chk("yesno 是", M.yesno("是") is True)
chk("yesno 已", M.yesno("已申请") is True)
chk("yesno 空值", M.yesno("未填写") is None)

# ---------------------------------------------------------------- 解析
f1 = {"商品描述摘录": "99新无拆无修", "实物差异描述": "有明显拆修痕迹"}
chk("get_text 精确取", M.get_text(f1, "商品描述摘录") == "99新无拆无修")
chk("get_text 不串字段", M.get_text(f1, "实物差异描述") == "有明显拆修痕迹")
chk("get_text 已付不串已退",
    M.get_text({"已付金额": "3200", "已退金额": "0"}, "已退金额") == "0")
chk("get_text 缺字段返空", M.get_text(f1, "平台") == "")
parts = re.split(r"[:：]", "成交价格：3200", 1)
chk("re.split 两元组", len(parts) == 2 and parts[1] == "3200")

# ---------------------------------------------------------------- 类型识别
t1, _ = M.classify_issue("买到假货", "", "", "")
chk("类型 假货", t1 == "假货/仿冒")
t2, _ = M.classify_issue("", "成色与描述严重不符", "", "")
chk("类型 描述不符", t2 == "描述不符")
t3, _ = M.classify_issue("收到就开不了机", "", "", "")
chk("类型 损坏", t3 == "商品损坏")
t4, _ = M.classify_issue("配件少了一个", "", "", "")
chk("类型 少件", t4 == "少件/缺件")
t5, _ = M.classify_issue("卖家收钱后一直不发货", "", "", "")
chk("类型 不发货", t5 == "卖家收款不发货")
t6, _ = M.classify_issue("", "", "", "")
chk("类型 空为未识别", t6 == "未识别")
t7, r7 = M.classify_issue("假货且与描述不符", "", "", "")
chk("类型 复合命中", "命中问题类型" in r7[0])

# ---------------------------------------------------------------- 交易方式
c8, r8, i8 = M.check_channel("卖家让微信直转给他", "否", "否")
chk("渠道 站外直转为高危", any("站外直接转账" in x for x in c8))
c9, r9, i9 = M.check_channel("平台担保交易", "否", "否")
chk("渠道 平台担保无高危", c9 == [])
c10, r10, i10 = M.check_channel("平台担保交易", "是", "否")
chk("渠道 当面交易为风险", any("当面交易" in x for x in r10))
c11, r11, i11 = M.check_channel("平台担保交易", "否", "是")
chk("渠道 卖家失联为高危", any("失联" in x for x in c11))
c12, r12, i12 = M.check_channel("", "", "")
chk("渠道 空表提示无法判断", any("无法判断" in x for x in i12))
chk("渠道 空表无高危", c12 == [])

# ---------------------------------------------------------------- 七天无理由
s13, i13 = M.check_seven(date(2026, 10, 1), BASE, False, True, True)
chk("七天 职业卖家三日内适用", s13 == "适用")
s14, i14 = M.check_seven(date(2026, 9, 1), BASE, False, True, True)
chk("七天 超期", s14 == "已超期")
s15, i15 = M.check_seven(date(2026, 10, 1), BASE, True, True, True)
chk("七天 定制不适用", s15 == "不适用")
s16, i16 = M.check_seven(None, BASE, False, True, True)
chk("七天 无收货日待补正", s16 == "待补正")
s17, i17 = M.check_seven(date(2026, 10, 1), BASE, False, True, False)
chk("七天 个人闲置有争议", s17 == "有争议")

# ---------------------------------------------------------------- 举证
g18, gs18 = M.check_evidence("否", "否", "否")
chk("举证 无开箱视频为缺口", any("开箱视频" in x for x in gs18))
chk("举证 无聊天记录为缺口", any("聊天记录" in x for x in gs18))
g19, gs19 = M.check_evidence("是", "是", "是")
chk("举证 齐备无缺口", g19 == 0)
g20, gs20 = M.check_evidence("", "", "")
chk("举证 空表有缺口", g20 >= 1)

# ---------------------------------------------------------------- 退款
v21, i21 = M.calc_refund(3200.0, 0.0, "30")
chk("退款 计算正确", v21 == 3200.0)
chk("退款 含运费说明", any("运费" in x for x in i21))
v22, i22 = M.calc_refund(None, 0.0, "")
chk("退款 无已付无法测算", v22 is None)
v23, i23 = M.calc_refund(1000.0, 1500.0, "")
chk("退款 已退大于已付不崩", v23 == 0.0)

# ---------------------------------------------------------------- 平台路径
a24 = M.check_platform("是", "平台驳回了我的申诉", "否")
chk("路径 已介入提示保留工单", any("工单" in x for x in a24))
chk("路径 驳回提示升级", any(("12315" in x or "复核" in x) for x in a24))
a25 = M.check_platform("否", "", "否")
chk("路径 未介入提示先占位", any("平台介入" in x for x in a25))

# ---------------------------------------------------------------- 整表
sample = M.parse_md(os.path.join(HERE, "样例.md"))
chk("样例解析非空", len(sample) > 10)
rep, verdict, issues, todo = M.build_report(sample, BASE)
chk("样例结论不通过", verdict == "不通过")
chk("样例高危项多", len(issues) >= 4)
chk("样例有待办", len(todo) >= 3)
chk("报告含结论摘要", "## 结论摘要" in rep)
chk("报告含待办补正动作", "## 待办补正动作" in rep)
chk("报告含边界与纪律", "## 边界与纪律" in rep)
chk("报告章节 >= 9", rep.count("## ") >= 9)
chk("样例已识别问题类型", "未识别" not in rep.split("## 结论摘要")[1].split("##")[0])
chk("样例提示开箱视频", "开箱视频" in rep)

empty = M.parse_md(os.path.join(HERE, "空输入.md"))
chk("空输入解析非空", len(empty) > 10)
rep2, v2, iss2, t2 = M.build_report(empty, BASE)
chk("空输入结论待补正", v2 == "待补正")
chk("空输入无风险项", iss2 == [])
chk("空输入仍出报告", len(rep2) > 500)
chk("空输入含待办", len(t2) >= 1)
chk("空输入不下不通过", "不通过" not in rep2.split("## 结论摘要")[1].split("##")[0])

# ---------------------------------------------------------------- 子进程
env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"
sp = os.path.join(SCRIPTS, "secondhand_check.py")
p1 = subprocess.run([sys.executable, sp, os.path.join(HERE, "样例.md"), "--base", "2026-10-04"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=120, env=env)
chk("子进程样例 rc=0", p1.returncode == 0)
chk("子进程样例有输出", len(p1.stdout) > 800)
p2 = subprocess.run([sys.executable, sp, os.path.join(HERE, "样例.md"), "--json"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=120, env=env)
try:
    d = json.loads(p2.stdout)
    chk("json 可解析", True)
    chk("json 含结论", "结论" in d)
    chk("json 含风险项", "风险项" in d)
    chk("json 含待办", "待办" in d)
    chk("json 结论一致", d["结论"] == "不通过")
except Exception:
    for n in ("json 可解析", "json 含结论", "json 含风险项", "json 含待办", "json 结论一致"):
        chk(n, False)
p3 = subprocess.run([sys.executable, sp, os.path.join(HERE, "空输入.md")],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=120, env=env)
chk("空输入 rc=2", p3.returncode == 2)
chk("空输入有输出", len(p3.stdout) > 200)
chk("空输入不崩", "Traceback" not in p3.stderr)

lines = ["回归测试 闲鱼二手交易", "PASS=%d FAIL=%d" % (len(PASS), len(FAIL)), ""]
if FAIL:
    lines.append("失败项：")
    lines += ["  - %s" % x for x in FAIL]
else:
    lines.append("失败项：无")
lines += ["", "通过明细："]
lines += ["  %2d. %s" % (i, x) for i, x in enumerate(PASS, 1)]
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print("PASS=%d FAIL=%d" % (len(PASS), len(FAIL)))
for x in FAIL:
    print("FAIL:", x)
sys.exit(1 if FAIL else 0)
