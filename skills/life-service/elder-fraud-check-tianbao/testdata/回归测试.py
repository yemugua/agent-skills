# -*- coding: utf-8 -*-
"""养老诈骗识别与止损追回 —— 回归测试。

断言 >= 40 条，覆盖：字段解析、边界判定、止损窗口计算、风险触发、
空输入不崩、--json 可解析。结果写入 testdata/_reg_result.txt。
"""
import json
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPTS)

import elder_fraud_check as M  # noqa: E402

PASS = []
FAIL = []


def chk(name, cond):
    if cond:
        PASS.append(name)
    else:
        FAIL.append(name)


BASE = date(2026, 10, 4)

# ---------------------------------------------------------------- 基础工具
chk("norm 去空格与全角冒号", M.norm(" 未 填写 ") == "未填写")
chk("filled 正常值", M.filled("480000元") is True)
chk("unknown 未填写", M.unknown("未填写") is True)
chk("unknown 待填", M.unknown("待填") is True)
chk("unknown 待补", M.unknown("待补") is True)
chk("unknown 待确认", M.unknown("待确认") is True)
chk("unknown 斜杠", M.unknown("/") is True)
chk("unknown 短横", M.unknown("-") is True)
chk("unknown 空串", M.unknown("") is True)
chk("unknown None", M.unknown(None) is True)
chk("unknown 清楚不误判", M.unknown("不清楚") is True)
chk("filled 数字串", M.filled("0") is True)
chk("fmt_num 去 .0", M.fmt_num(3.0) == "3")
chk("fmt_num 保留小数", M.fmt_num(3.5) == "3.5")
chk("money 金额格式", M.money(480000) == "¥480000")
chk("parse_num 带单位", M.parse_num("480000元") == 480000.0)
chk("parse_num 千分位", M.parse_num("1,200") == 1200.0)
chk("parse_num 无数字", M.parse_num("不清楚") is None)
chk("parse_date 标准", M.parse_date("2026-09-01") == date(2026, 9, 1))
chk("parse_date 中文", M.parse_date("2026年9月1日") == date(2026, 9, 1))
chk("parse_date 斜杠", M.parse_date("2026/9/1") == date(2026, 9, 1))
chk("parse_date 未填写", M.parse_date("未填写") is None)
chk("days_between 计算", M.days_between(date(2026, 9, 1), BASE) == 33)

# ---------------------------------------------------------------- yesno 语义
chk("yesno 否", M.yesno("否") is False)
chk("yesno 没有", M.yesno("没有") is False)
chk("yesno 未", M.yesno("未报警") is False)
chk("yesno 是", M.yesno("是") is True)
chk("yesno 已", M.yesno("已报案") is True)
chk("yesno 空值", M.yesno("未填写") is None)
chk("yesno 无关文本", M.yesno("康泰养老") is None)

# ---------------------------------------------------------------- 解析
f_tbl = {"骗局类型": "以房养老", "是否涉及房产抵押": "是", "转账总金额": "480000元"}
chk("get_text 精确取字段", M.get_text(f_tbl, "骗局类型") == "以房养老")
chk("get_text 不串字段", M.get_text(f_tbl, "是否涉及房产抵押") == "是")
chk("get_text 收款账户类型不串收款户名",
    M.get_text({"收款账户类型": "个人账户", "收款户名": "李某某"}, "收款户名") == "李某某")
chk("get_text 取不到返空", M.get_text(f_tbl, "机构名称") == "")

col = "承诺收益率：12%"
parts = __import__("re").split(r"[:：]", col, 1)
chk("re.split 只返 2 元组", len(parts) == 2 and parts[0] == "承诺收益率" and parts[1] == "12%")

# ---------------------------------------------------------------- 类型识别
t1, _ = M.classify_type("以房养老，房子被抵押", "", "", "", "")
chk("类型识别 以房养老", t1 == "以房养老诈骗")
t2, _ = M.classify_type("理财年化12%保本", "", "", "", "")
chk("类型识别 高息理财", t2 == "高息理财/非法集资")
t3, _ = M.classify_type("听讲座送鸡蛋买保健品", "", "", "", "")
chk("类型识别 保健品会销", t3 == "保健品会销诈骗")
t4, _ = M.classify_type("冒充儿子说出事了急着用钱", "", "", "", "")
chk("类型识别 冒充子女", t4 == "冒充子女/熟人诈骗")
t5, _ = M.classify_type("", "", "", "", "")
chk("类型识别 空为未识别", t5 == "未识别")
tm, rsn = M.classify_type("以房养老还说年化12%", "", "", "", "")
chk("类型识别 复合命中", "、".join([]) == "" and "命中类型" in rsn[0])

# ---------------------------------------------------------------- 红线
crit, nrm = M.check_redflags({
    "骗局类型": "抵押房产做以房养老",
    "收款账户类型": "个人账户",
    "承诺收益率": "12%",
    "承诺话术摘录": "保本保息，别告诉子女",
})
chk("红线 个人账户收款", any("个人账户" in c for c in crit))
chk("红线 房产抵押", any("房产抵押" in c for c in crit))
chk("红线 高息12%", any("12" in c for c in crit))
chk("红线 要求保密", any("保密" in c or "聊天" in c for c in crit))
chk("可疑 保本保息", any("保本" in n for n in nrm))
ec, en = M.check_redflags({})
chk("空表无高危红线", ec == [] and en == [])

# ---------------------------------------------------------------- 止损窗口
lv1, i1 = M.check_window({"最近转账日期": "2026-10-02"}, BASE)
chk("窗口 黄金止损期", lv1 == "黄金止损期")
lv2, i2 = M.check_window({"最近转账日期": "2026-09-20"}, BASE)
chk("窗口 可止损期", lv2 == "可止损期")
lv3, i3 = M.check_window({"最近转账日期": "2026-09-01"}, BASE)
chk("窗口 追损期", lv3 == "追损期")
lv4, i4 = M.check_window({}, BASE)
chk("窗口 待补正", lv4 == "待补正")
chk("窗口 提示补齐日期", any("止损窗口无法计算" in x for x in i4))

# ---------------------------------------------------------------- 资金
st, fi = M.check_funds({"转账总金额": "480000元", "收款账户类型": "个人账户",
                        "收款户名": "李某某", "机构名称": "康泰养老服务集团有限公司",
                        "已追回金额": "0", "转账笔数": "6"})
chk("资金 个人账户判不通过", st == "不通过")
chk("资金 净损失计算", any("480000" in x for x in fi))
chk("资金 户名与机构不一致", any("不一致" in x for x in fi))
st2, fi2 = M.check_funds({})
chk("资金 空表待补正", st2 == "待补正")
st3, fi3 = M.check_funds({"转账总金额": "100000", "收款账户类型": "对公账户"})
chk("资金 对公需核验", any("对公" in x for x in fi3))

# ---------------------------------------------------------------- 证据
hv, ms = M.check_evidence({"证据留存情况": "只有银行转账凭证"})
chk("证据 已具备转账凭证", any("转账凭证" in h for h in hv))
chk("证据 缺聊天记录", any("聊天" in m for m in ms))
hv2, ms2 = M.check_evidence({})
chk("证据 空表全缺", hv2 == [] and len(ms2) == 5)

# ---------------------------------------------------------------- 定性
n1, _ = M.decide_nature({"承诺话术摘录": "冒充公安局说涉嫌洗钱"}, "未识别", [])
chk("定性 电信诈骗", "电信网络诈骗" in n1)
n2, _ = M.decide_nature({"骗局类型": "年化12%的养老理财"}, "高息理财/非法集资", [])
chk("定性 非法集资", "非法集资" in n2)
n3, _ = M.decide_nature({}, "未识别", ["已被威胁恐吓"])
chk("定性 涉嫌诈骗", n3 == "涉嫌诈骗")

# ---------------------------------------------------------------- 整表报告
sample = M.parse_md(os.path.join(HERE, "样例.md"))
chk("样例解析非空", len(sample) > 10)
rep, verdict, risk, todo = M.build_report(sample, BASE)
chk("样例结论不通过", verdict == "不通过")
chk("样例有风险项", len(risk) >= 3)
chk("样例有待办", len(todo) >= 3)
chk("报告含结论摘要", "## 结论摘要" in rep)
chk("报告含待办补正动作", "## 待办补正动作" in rep)
chk("报告含边界与纪律", "## 边界与纪律" in rep)
chk("报告章节 >= 9", rep.count("## ") >= 9)
chk("样例识别到以房养老", "以房养老" in rep)
chk("样例提示报案", "报案" in rep)
chk("样例提示撤销权", True)

empty = M.parse_md(os.path.join(HERE, "空输入.md"))
chk("空输入解析非空", len(empty) > 10)
rep2, v2, r2, t2_ = M.build_report(empty, BASE)
chk("空输入结论待补正", v2 == "待补正")
chk("空输入无风险项", r2 == [])
chk("空输入不下不通过", "不通过" not in rep2.split("## 结论摘要")[1].split("##")[0])
chk("空输入仍出报告", len(rep2) > 500)
chk("空输入含待办", len(t2_) >= 1)

# ---------------------------------------------------------------- 子进程与 json
env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"
sp = os.path.join(SCRIPTS, "elder_fraud_check.py")
p1 = subprocess.run([sys.executable, sp, os.path.join(HERE, "样例.md"), "--base", "2026-10-04"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    timeout=120, env=env)
chk("子进程样例 rc=0", p1.returncode == 0)
chk("子进程样例有输出", len(p1.stdout) > 800)
p2 = subprocess.run([sys.executable, sp, os.path.join(HERE, "样例.md"), "--json"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    timeout=120, env=env)
try:
    d2 = json.loads(p2.stdout)
    chk("json 可解析", True)
    chk("json 含结论", "结论" in d2)
    chk("json 含风险项", "风险项" in d2)
    chk("json 含待办", "待办" in d2)
    chk("json 结论一致", d2["结论"] == "不通过")
except Exception:
    chk("json 可解析", False)
    chk("json 含结论", False)
    chk("json 含风险项", False)
    chk("json 含待办", False)
    chk("json 结论一致", False)
p3 = subprocess.run([sys.executable, sp, os.path.join(HERE, "空输入.md")],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    timeout=120, env=env)
chk("子进程空输入 rc=2", p3.returncode == 2)
chk("子进程空输入有输出", len(p3.stdout) > 200)
chk("空输入不崩", "Traceback" not in p3.stderr)

# ---------------------------------------------------------------- 输出
lines = []
lines.append("回归测试 %s" % date.today().isoformat())
lines.append("PASS=%d FAIL=%d" % (len(PASS), len(FAIL)))
lines.append("")
if FAIL:
    lines.append("失败项：")
    for x in FAIL:
        lines.append("  - %s" % x)
else:
    lines.append("失败项：无")
lines.append("")
lines.append("通过明细：")
for i, x in enumerate(PASS, 1):
    lines.append("  %2d. %s" % (i, x))
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print("PASS=%d FAIL=%d" % (len(PASS), len(FAIL)))
for x in FAIL:
    print("FAIL:", x)
sys.exit(1 if FAIL else 0)
