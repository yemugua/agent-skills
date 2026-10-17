# -*- coding: utf-8 -*-
"""社保转移核查 回归测试（自写 utf-8 结果文件，避免 PowerShell 二次编码）"""
import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import transfer_check as tc  # noqa: E402

SAMPLE = os.path.join(HERE, "社保转移样例.md")
EMPTY = os.path.join(HERE, "空社保信息.md")
BASE = dt.date(2026, 10, 4)

PASS = 0
FAIL = 0
LINES = []


def ck(name, got, want):
    global PASS, FAIL
    if got == want:
        PASS += 1
        LINES.append("PASS %s" % name)
    else:
        FAIL += 1
        LINES.append("FAIL %s  got=%r want=%r" % (name, got, want))


def ck_true(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        LINES.append("PASS %s" % name)
    else:
        FAIL += 1
        LINES.append("FAIL %s  %s" % (name, extra))


with open(SAMPLE, encoding="utf-8") as f:
    text = f.read()
with open(EMPTY, encoding="utf-8") as f:
    etext = f.read()

# ---------------- 基础解析
ck("P01 norm 去空格", tc.norm(" 上 海 市 "), "上海市")
ck("P02 is_ph 待填", tc.is_ph("【待填】"), True)
ck("P03 is_ph 真实值", tc.is_ph("上海市"), False)
ck("P04 is_ph 选项串", tc.is_ph("是 / 否"), True)
ck("P05 is_ph 空", tc.is_ph(""), True)
ck("P06 split_row", tc.split_row("| a | b | c |"), ["a", "b", "c"])
ck("P07 is_row", tc.is_row("| a | b |"), True)
ck("P08 is_row 非表", tc.is_row("普通一行"), False)
ck("P09 parse_year 年份月", tc.parse_year("1983-03"), 1983)
ck("P10 parse_year 城市串", tc.parse_year("上海市"), None)
ck("P11 parse_year 四位数", tc.parse_year("2010 年"), 2010)

# ---------------- get_text
ck("T01 性别", tc.get_text(text, "性别"), "男")
ck("T02 出生年月", tc.get_text(text, "出生年月"), "1983-03")
ck("T03 户籍地", tc.get_text(text, "户籍地"), "河南省商丘市")
ck("T04 原参保地", tc.get_text(text, "原参保地"), "上海市")
ck("T05 新参保地", tc.get_text(text, "新参保地"), "广东省深圳市")
ck("T06 参保身份", tc.get_text(text, "参保身份"), "单位职工")
ck("T07 空表取不到", tc.get_text(etext, "性别"), "")
ck("T08 标题行不算", tc.get_text(text, "项"), "")

# ---------------- yes/no
ck("Y01 是", tc.yes(text, "新参保地是否已参保缴费"), True)
ck("Y02 否", tc.yes(text, "是否已在领取基本养老金"), False)
ck("Y03 有", tc.yes(text, "重复缴费"), True)
ck("Y04 无", tc.yes(text, "欠费"), False)
ck("Y05 空表 None", tc.yes(etext, "重复缴费"), None)

# ---------------- get_int
ck("N01 断缴月数", tc.get_int(text, "医保断缴"), 2)
ck("N02 距退休", tc.get_int(text, "距退休", "距离预计退休"), 20)
ck("N03 空表 None", tc.get_int(etext, "医保断缴"), None)

# ---------------- 年限表
yrs = tc.parse_years(text)
ck("S01 年限条数", len(yrs), 3)
ck("S02 首条城市", yrs[0][0], "广东省深圳市")
ck("S03 首条年限", yrs[0][2], 12.0)
ck("S04 首条首次参保", yrs[0][3], 2010)
ck("S05 户籍地行", yrs[2][1], True)
ck("S06 空表无年限", len(tc.parse_years(etext)), 0)

# ---------------- 完整报告
body, meta = tc.build_report(SAMPLE, BASE)
ck_true("R01 报告生成", body is not None, str(meta))
ck_true("R02 meta 有版本", isinstance(meta, dict) and meta.get("version") == "1.0.0", str(meta))
ck_true("R03 十段", body.count("## ") >= 10, str(body.count("## ")))
ck_true("R04 结论摘要", "结论摘要" in body)
ck_true("R05 账户性质", "临时账户" in body)
ck_true("R06 待遇领取地推演", "待遇领取地推演" in body)
ck_true("R07 45 工作日", "45 个工作日" in body)
ck_true("R08 待办动作", "待办动作" in body)
ck_true("R09 输出纪律", "输出纪律" in body)
ck_true("R10 推演出深圳", "广东省深圳市" in body.split("## 四")[1].split("## 五")[0])
ck_true("R11 非临时账户", meta.get("temporary_account") is False, str(meta))
ck_true("R12 年龄 43", meta.get("age") == 43, str(meta))
ck_true("R13 有一个卡点", meta.get("blockers") == 1, str(meta))
ck_true("R14 重复缴费进阻断", "重复缴费" in body)
ck_true("R15 工伤不转", "不转" in body)
ck("R19 户籍地年限0不算参保→推到深圳", meta.get("pension_place"), "广东省深圳市")
ck_true("R20 未命中的说明不吓人", "不构成阻断" in body, str(body.count("不构成阻断")))
ck_true("R21 无错字郣", "郣" not in body)

# ---------------- 临时账户场景（女 1975 年生，2020 年首次在非户籍地参保）
TMP = os.path.join(HERE, "_tmp_account.md")
with open(TMP, "w", encoding="utf-8") as f:
    f.write("# 采集表\n\n## 一、本人情况\n\n")
    f.write("| 项 | 填什么 |\n|---|---|\n")
    f.write("| 性别 | 女 |\n")
    f.write("| 出生年月 | 1975-06 |\n")
    f.write("| 户籍地（省市区） | 河南省商丘市 |\n")
    f.write("| 是否已在领取基本养老金 | 否 |\n\n")
    f.write("## 二、参保地情况\n\n")
    f.write("| 项 | 填什么 |\n|---|---|\n")
    f.write("| 原参保地（要转出的城市） | 河南省郑州市 |\n")
    f.write("| 新参保地（要转入的城市） | 广东省深圳市 |\n")
    f.write("| 新参保地是否已参保缴费 | 是 |\n")
    f.write("| 原参保地是否已停保 | 是 |\n\n")
    f.write("## 三、养老缴费年限\n\n")
    f.write("| 参保城市 | 是否户籍地 | 养老累计缴费年限（年） | 首次参保年份 |\n|---|---|---|---|\n")
    f.write("| 河南省郑州市 | 否 | 15 | 2005 |\n")
    f.write("| 广东省深圳市 | 否 | 6 | 2020 |\n\n")
    f.write("## 五、卡点自查\n\n")
    f.write("| 问题 | 填什么 |\n|---|---|\n")
    f.write("| 有没有同一时段在两地同时缴费（重复缴费） | 无 |\n")
    f.write("| 原参保地有没有欠费 | 无 |\n")
    f.write("| 是否正在领取失业金 | 否 |\n")
b2, m2 = tc.build_report(TMP, BASE)
ck_true("A01 临时账户生成", b2 is not None, str(m2))
ck_true("A02 判为临时账户", m2.get("temporary_account") is True, str(m2))
ck_true("A03 报告写临时账户", "**临时账户**" in b2)
ck_true("A04 说明转不进", "转不进" in b2 or "转不进来" in b2)
ck_true("A05 待遇地推到郑州", m2.get("pension_place") == "河南省郑州市", str(m2))
ck_true("A06 无硬性阻断之外", m2.get("blockers") == 1, str(m2))

# ---------------- 空表
r2 = tc.build_report(EMPTY, BASE)
ck_true("E01 空表返回 None", r2[0] is None, str(r2[0])[:60])
ck_true("E02 空表给提示串", isinstance(r2[1], str) and "未解析" in r2[1], str(r2[1])[:60])

# ---------------- 缺文件
r3 = tc.build_report(os.path.join(HERE, "不存在.md"), BASE)
ck_true("E03 缺文件不崩", r3[0] is None, str(r3[1])[:60])

# ---------------- 表格不裂
bad = [ln for ln in body.splitlines() if ln.count("|") > 6]
ck_true("R16 表格不裂", not bad, str(bad[:2]))

# ---------------- 无占位符泄漏
ck_true("R17 无【待填】泄漏", "【待填】" not in body)
ck_true("R18 无乱码", "\ufffd" not in body)

try:
    os.remove(TMP)
except Exception:
    pass

LINES.append("== TOTAL PASS=%d FAIL=%d ==" % (PASS, FAIL))
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(LINES) + "\n")
print("PASS=%d FAIL=%d" % (PASS, FAIL))
