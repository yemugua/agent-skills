#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""deposit_check 回归测试 —— 结果自写 utf-8 文件（PowerShell 会吞 python stdout）"""
import os
import re
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import deposit_check as dc  # noqa: E402

PASS = [0]
FAIL = []


def ck(name, got, want):
    ok = got == want
    if ok:
        PASS[0] += 1
    else:
        FAIL.append("%s → got=%r want=%r" % (name, got, want))


def ck_true(name, cond):
    if cond:
        PASS[0] += 1
    else:
        FAIL.append("%s → 断言不成立" % name)


# ---------- 1. 金额/日期/天数解析 ----------
ck("P01 纯数字", dc.parse_money("5000"), 5000)
ck("P02 千分位", dc.parse_money("1,000"), 1000)
ck("P03 带元", dc.parse_money("800元"), 800)
ck("P04 破折号", dc.parse_money("—"), None)
ck("P05 占位", dc.parse_money("待填写"), None)
ck("P06 空串", dc.parse_money(""), None)
DAYS_LABELS = ("约定的退还时限", "退还时限", "退还期限")
ck("P07 天数纯数字", dc.get_days("| 退还时限 | 7 |", *DAYS_LABELS), 7)
ck("P08 天数带天", dc.get_days("| 退还时限 | 15 天 |", *DAYS_LABELS), 15)
ck("P09 模板说明里的 7 不算", dc.get_days("| 退还时限 | 天数（如 7）；没写就留空 |"), None)
ck("P10 空串天数", dc.get_days("| 退还时限 |  |"), None)
ck("P11 日期标准", dc.parse_date("2026-04-30"), date(2026, 4, 30))
ck("P12 日期斜杠", dc.parse_date("2026/05/07"), date(2026, 5, 7))
ck("P13 日期占位", dc.parse_date("待填写"), None)

# ---------- 2. 取第一个可解析值（说明行在前） ----------
tpl = """## 一、合同与押金

| 项 | 填什么 |
|---|---|
| 押金金额 | 数字（元） |
| 押金金额 | 5000 |
| 押金名称 | 押金 / 保证金 / 定金 / 订金 |
| 押金名称 | 押金 |
| 退租交接日期（合同终止日） | YYYY-MM-DD |
| 退租交接日期（合同终止日） | 2026-04-30 |
| 押金与租金付款凭证 | 有 |
"""
ck("P14 金额跳过说明行", dc.get_amount(tpl, "押金金额", "押金"), 5000)
ck("P15 日期跳过说明行", dc.get_date(tpl, "退租交接日期", "合同终止日"), date(2026, 4, 30))
ck("P16 押金名称", dc.get_text(tpl, "押金名称", "押金性质"), "押金")
ck("P17 付款凭证行的「有」不会被当金额", dc.get_amount(tpl, "押金金额", "押金"), 5000)

# ---------- 3. 欠费隔离（after） ----------
owe_doc = """## 三、我这边的结算与欠费

| 项 | 填什么 |
|---|---|
| 欠房租 | 无 |
| 欠水电燃气物业 | 无 |
"""
ck("P18 无欠租不取扣款表里的 500", dc.get_amount(owe_doc, "欠房租", "欠租"), None)
ck("P19 无欠费不取 200", dc.get_amount(owe_doc, "欠水电燃气物业", "欠水电"), None)
owe_has = """## 三、我这边的结算与欠费

| 项 | 填什么 |
|---|---|
| 欠房租 | 1200 |
"""
ck("P20 第三节有欠租取到 1200", dc.get_amount(owe_has, "欠房租", "欠租"), 1200)

# ---------- 4. 扣款分类 ----------
def cls(s):
    return dc.classify(s)[0]


ck("C01 欠租", cls("欠租 500 拖欠房租"), "正当")
ck("C02 欠水电", cls("欠水费 200"), "正当")
ck("C03 故意损坏", cls("打碎马桶 属故意"), "正当")
ck("C04 违约金", cls("提前退租违约金"), "存疑")
ck("C05 换锁", cls("换锁 30 元"), "存疑")
ck("C06 深度清洁", cls("深度清洁 300"), "存疑")
ck("C07 刷漆+掉漆", cls("墙面刷漆 墙面掉漆、墙纸起翘"), "不成立")
ck("C08 空置期", cls("空置期损失 找不到下家"), "不成立")
ck("C09 折旧", cls("折旧 200"), "不成立")
ck("C10 上一位租客", cls("上一位租客弄的"), "不成立")
ck("C11 无关键词", cls("莫名其妙的费用"), "存疑")
ck("C12 空串", cls(""), "存疑")

# ---------- 5. 扣款表解析 ----------
SAMPLE = os.path.join(HERE, "租赁信息样例.md")
sample_text = open(SAMPLE, "r", encoding="utf-8").read()
rows = dc.parse_deductions(sample_text)
ck("D01 解析出 4 条扣款", len(rows), 4)
ck("D02 没把押金金额当扣款", [r["name"] for r in rows].count("押金金额"), 0)
ck("D03 没把证据表首行当扣款", [r["name"] for r in rows].count("合同签字页 + 押金支付页"), 0)
ck("D04 金额合计", sum(r["amount"] for r in rows), 3600)
ck("D05 理由列取对", rows[0]["reason"], "墙面掉漆、墙纸起翘，说要重刷")
ck("D06 票据列取对", rows[3]["ticket"], "有")
ck("D07 票据无时取到「无」", rows[0]["ticket"], "无")
empty_rows = dc.parse_deductions("| # | 扣什么 | 金额（元） | 理由 | 票据 |\n|---|---|---|---|---|\n| 1 | 待填写 | 待填写 | 待填写 | 待填写 |")
ck("D08 空表不产出", empty_rows, [])

# ---------- 6. 主体报告 ----------
base = date(2026, 6, 10)
body, res = dc.build_report(SAMPLE, base, 3.0)
ck_true("R01 body 非空", body is not None)
ck("R02 押金", res["deposit"], 5000)
ck("R03 扣款合计", res["deducted"], 3600)
ck("R04 正当扣款", res["legit"], 500)
ck("R05 应退日", res["refund_due"], "2026-05-07")
ck("R06 逾期天数", res["overdue_days"], 34)
ck("R07 资金占用", res["interest"], 12.58)
ck("R08 可主张", res["claimable"], 4512.58)
ck("R09 证据有 5 类", res["evidence"]["have"], 5)
ck("R10 证据缺 3 类", len(res["evidence"]["lack"]), 3)
ck_true("R11 缺入住现状", "入住时现状照片或视频" in res["evidence"]["lack"])
ck("R12 时效届满", res["tickets"]["limit_end"], "2029-05-07")
ck_true("R13 时效剩 1000 天以上", res["tickets"]["days_left"] > 1000)
ck("R14 性质判定", res["kind_rule"], "押金/保证金")
ck_true("R15 摘要写明无双倍返还", "押金没有双倍返还规则" in body)
ck_true("R16 摘要写明逾期 34 天", "逾期 34 天" in body)
ck_true("R17 证据段计数正确", "八类证据：有 **5** 类 / 8" in body)
ck_true("R18 无乱码", "�" not in body)
ck_true("R19 三段话术齐全", all(k in body for k in ("① 亮事实", "② 逐条反驳", "③ 期限与后果")))

# 表格列数：扣款段表头必须 8 列
lines = body.splitlines()
hdr = [i for i, l in enumerate(lines) if l.startswith("| # | 扣什么")][0]
ck("R20 扣款表头 8 列", lines[hdr].count("|") - 1, 8)
data_cols = set()
for l in lines[hdr + 2:hdr + 6]:
    if l.startswith("|"):
        data_cols.add(l.count("|") - 1)
ck_true("R21 扣款数据行列数=表头列数（不撑裂）", data_cols == {8})
ck_true("R22 每条扣款都判了档位", all(r["verdict"] in ("正当", "存疑", "不成立") for r in res["rows"]))
ck_true("R23 正当的只有欠租 500",
        [r["amount"] for r in res["rows"] if r["verdict"] == "正当"] == [500])
ck_true("R24 可争条目有 3 条", "整理可争议 3 条" in body)

# ---------- 7. 空输入 ----------
EMPTY = os.path.join(HERE, "空租赁信息.md")
b2, r2 = dc.build_report(EMPTY, base, 3.0)
ck("E01 空表 → body 为 None", b2, None)
ck_true("E02 空表 → 返回提示串", isinstance(r2, str) and "押金金额" in r2)

# ---------- 8. 性质辨析 ----------
def kind_of(kind_raw):
    d = sample_text.replace("| 押金名称 | 押金 |", "| 押金名称 | %s |" % kind_raw)
    p = os.path.join(HERE, "_kind_tmp.md")
    open(p, "w", encoding="utf-8").write(d)
    _, rr = dc.build_report(p, base, 3.0)
    os.remove(p)
    return rr["kind_rule"]


ck("F01 写定金 → 定金罚则", kind_of("定金"), "定金罚则")
ck("F02 押金里夹带「定金」仍按押金", kind_of("押金（定金）"), "押金/保证金")
ck("F03 写订金 → 预付款", kind_of("订金"), "预付款")

# ---------- 9. CLI ----------
py = sys.executable
out_md = os.path.join(HERE, "_tmpout_样例_核查报告.md")
r1 = subprocess.run([py, os.path.join(HERE, "..", "scripts", "deposit_check.py"), SAMPLE,
                     "--base", "2026-06-10", "--out", out_md], capture_output=True, text=True, encoding="utf-8")
ck("T01 样例 CLI rc=0", r1.returncode, 0)
ck_true("T02 CLI 打印 OUT", "OUT=" in (r1.stdout or ""))
ck_true("T03 产物落盘", os.path.exists(out_md))
r2b = subprocess.run([py, os.path.join(HERE, "..", "scripts", "deposit_check.py"), EMPTY,
                      "--base", "2026-06-10", "--out", os.path.join(HERE, "_tmpout_空_核查报告.md")],
                     capture_output=True, text=True, encoding="utf-8")
ck("T04 空表 CLI rc=2", r2b.returncode, 2)
r3 = subprocess.run([py, os.path.join(HERE, "..", "scripts", "deposit_check.py"),
                     os.path.join(HERE, "不存在.md")], capture_output=True, text=True, encoding="utf-8")
ck("T05 文件不存在 rc=2", r3.returncode, 2)

# ---------- 汇总 ----------
res_txt = "== TOTAL PASS=%d FAIL=%d ==\n" % (PASS[0], len(FAIL))
for f in FAIL:
    res_txt += "  FAIL " + f + "\n"
open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8").write(res_txt)
print(res_txt)
sys.exit(0 if not FAIL else 1)
