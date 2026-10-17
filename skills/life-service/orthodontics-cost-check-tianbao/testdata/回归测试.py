# -*- coding: utf-8 -*-
"""牙齿矫正正畸花费与套路核查 —— 回归测试（>=40 断言）。"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPTS)

import orthodontics_check as M  # noqa: E402

PASS = []
FAIL = []


def chk(name, cond):
    (PASS if cond else FAIL).append(name)


# 基础工具
chk("norm 归一", M.norm(" 未 填写 ") == "未填写")
chk("filled 正常", M.filled("29800元") is True)
chk("unknown 待填", M.unknown("待填") is True)
chk("unknown 待补", M.unknown("待补") is True)
chk("unknown 待确认", M.unknown("待确认") is True)
chk("unknown 斜杠", M.unknown("/") is True)
chk("unknown 未填写", M.unknown("未填写") is True)
chk("unknown None", M.unknown(None) is True)
chk("fmt_num 去 .0", M.fmt_num(24.0) == "24")
chk("fmt_num 小数", M.fmt_num(23.4) == "23.4")
chk("money", M.money(29800) == "¥29800")
chk("parse_num 带单位", M.parse_num("29800元") == 29800.0)
chk("parse_num 百分比", M.parse_num("23.4%") == 23.4)
chk("parse_num 无数字", M.parse_num("未填写") is None)

# yesno
chk("yesno 否", M.yesno("否") is False)
chk("yesno 没有", M.yesno("没有") is False)
chk("yesno 是", M.yesno("是") is True)
chk("yesno 已", M.yesno("已核实") is True)
chk("yesno 空", M.yesno("未填写") is None)

# 解析
f1 = {"是否核对医师执业地点": "否", "矫治方式": "隐形矫正"}
chk("get_text 精确取", M.get_text(f1, "矫治方式") == "隐形矫正")
chk("get_text 不串字段", M.get_text(f1, "是否核对医师执业地点") == "否")
chk("get_text 报价不串已付",
    M.get_text({"报价总金额": "29800", "已付金额": "20000"}, "已付金额") == "20000")
chk("get_text 缺字段返空", M.get_text(f1, "机构名称") == "")
parts = re.split(r"[:：]", "约定疗程月数：24", 1)
chk("re.split 两元组", len(parts) == 2 and parts[1] == "24")

# 资质
s1, i1 = M.check_qual({"是否核对机构执业许可": "是", "是否核对医师执业地点": "否"})
chk("资质 未核执业地点不通过", s1 == "不通过")
chk("资质 提示卫健查询", any("执业地点" in x for x in i1))
s2, i2 = M.check_qual({})
chk("资质 空表待补正", s2 == "待补正")
s3, i3 = M.check_qual({"是否核对机构执业许可": "是", "是否核对医师执业地点": "是"})
chk("资质 已核实不判不通过", s3 != "不通过")

# 报价与增项
c4, r4, i4 = M.check_quote({"报价总金额": "29800", "已付金额": "29800",
                            "增项情况": "拔牙与支抗钉", "增项金额": "8600",
                            "增项是否事前告知": "否", "保持器是否含在报价内": "否",
                            "矫治方式": "隐形矫正", "是否拿到品牌授权卡": "否"})
chk("增项 未告知为高危", any("未事前告知" in x for x in c4))
chk("增项 保持器不含为风险", any("保持器" in x for x in r4))
chk("品牌 无授权卡为高危", any("授权卡" in x for x in c4))
c5, r5, i5 = M.check_quote({"报价总金额": "20000", "已付金额": "26000"})
chk("超额 已付超报价为高危", any("超过报价" in x for x in c5))
c6, r6, i6 = M.check_quote({})
chk("报价 空表无高危", c6 == [])
chk("报价 空表提示无法开展", any("无法开展" in x for x in i6))

# 金融
c7, r7, i7 = M.check_finance({"付款方式": "医美分期", "分期年化利率": "23.4%",
                              "机构是否已停业": "否"})
chk("分期 独立性风险", any("独立" in x for x in r7))
chk("分期 利率偏高提示", any("23.4" in x for x in i7))
c8, r8, i8 = M.check_finance({"付款方式": "医美分期", "机构是否已停业": "是"})
chk("停业 仍在还款为高危", any("已停业" in x for x in c8))
c9, r9, i9 = M.check_finance({"付款方式": "一次性付清"})
chk("全款 无分期高危", c9 == [])
c10, r10, i10 = M.check_finance({})
chk("付款 空表无高危", c10 == [])

# 疗程
r11, i11 = M.check_progress({"约定疗程月数": "24", "实际已进行月数": "10",
                             "是否中途更换医生": "是", "换医生是否事前告知": "否",
                             "是否存在效果争议": "是", "是否签知情同意书": "否"})
chk("进度 计算占比", any("41" in x or "42" in x for x in i11))
chk("换医生 未告知为风险", any("更换主治医生" in x for x in r11))
chk("无知情同意书为风险", any("知情同意书" in x for x in r11))
r12, i12 = M.check_progress({})
chk("疗程 空表提示无法核算", any("无法核算" in x for x in i12))

# 条款
c13, r13 = M.check_terms("本方案一经开始概不退费，最终解释权归本机构所有", "终身免费调整，保证效果")
chk("条款 概不退费", any("概不退费" in x for x in c13))
chk("条款 最终解释权", any("最终解释权" in x for x in c13))
chk("宣传 保证效果", any("保证效果" in x for x in r13))
c14, r14 = M.check_terms("", "")
chk("条款 空表无高危", c14 == [] and r14 == [])

# 退费测算
v15, i15 = M.calc_refund({"已付金额": "29800", "已退金额": "0",
                          "约定疗程月数": "24", "实际已进行月数": "10"}, False)
chk("退费 按比例测算", v15 is not None and v15 > 10000)
chk("退费 说明余额", any("未退余额" in x for x in i15))
v16, i16 = M.calc_refund({"已付金额": "29800", "已退金额": "0",
                          "约定疗程月数": "24", "实际已进行月数": "10"}, True)
chk("退费 机构原因按80%", v16 is not None and abs(v16 - 29800 * 0.8) < 1)
v17, i17 = M.calc_refund({}, False)
chk("退费 空表无法测算", v17 is None)

# 证据
h18, m18 = M.check_evidence({"证据留存情况": "只有付款记录和几张聊天截图"})
chk("证据 已具备付款凭证", any("付款凭证" in x for x in h18))
chk("证据 缺方案书", any("方案书" in x for x in m18))
h19, m19 = M.check_evidence({})
chk("证据 空表全缺", h19 == [] and len(m19) == 7)

# 整表
sample = M.parse_md(os.path.join(HERE, "样例.md"))
chk("样例解析非空", len(sample) > 10)
rep, verdict, issues, todo = M.build_report(sample)
chk("样例结论不通过", verdict == "不通过")
chk("样例高危项多", len(issues) >= 5)
chk("样例有待办", len(todo) >= 4)
chk("报告含结论摘要", "## 结论摘要" in rep)
chk("报告含待办补正动作", "## 待办补正动作" in rep)
chk("报告含边界与纪律", "## 边界与纪律" in rep)
chk("报告章节 >= 9", rep.count("## ") >= 9)
chk("样例提示授权卡", "授权卡" in rep)
chk("样例提示卫健", "卫生健康" in rep)
chk("样例提示12315", "12315" in rep)

empty = M.parse_md(os.path.join(HERE, "空输入.md"))
chk("空输入解析非空", len(empty) > 10)
rep2, v2, iss2, t2 = M.build_report(empty)
chk("空输入结论待补正", v2 == "待补正")
chk("空输入无风险项", iss2 == [])
chk("空输入仍出报告", len(rep2) > 500)
chk("空输入含待办", len(t2) >= 1)

# 子进程
env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"
sp = os.path.join(SCRIPTS, "orthodontics_check.py")
p1 = subprocess.run([sys.executable, sp, os.path.join(HERE, "样例.md")],
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

lines = ["回归测试 正畸", "PASS=%d FAIL=%d" % (len(PASS), len(FAIL)), ""]
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
