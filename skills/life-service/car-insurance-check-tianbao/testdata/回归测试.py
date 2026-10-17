# -*- coding: utf-8 -*-
"""车险投保与理赔核查 回归测试（自写 utf-8 结果文件）"""
import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import insurance_check as ic  # noqa: E402

SAMPLE = os.path.join(HERE, "车险样例.md")
EMPTY = os.path.join(HERE, "空车险信息.md")
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

# ---------------- 基础
ck("P01 norm", ic.norm(" 大众 朗逸 "), "大众朗逸")
ck("P02 is_ph 待填", ic.is_ph("【待填】"), True)
ck("P03 is_ph 分隔行", ic.is_ph("---"), True)
ck("P04 is_ph 真值", ic.is_ph("非营运"), False)
ck("P05 split_row", ic.split_row("| a | b |"), ["a", "b"])
ck("P06 parse_date", ic.parse_date("2026-12-20"), dt.date(2026, 12, 20))
ck("P07 parse_date 空", ic.parse_date(""), None)
ck("P08 get_int 带单位", ic.get_int(text, "三者险保额"), 100)
ck("P09 get_int 保费", ic.get_int(text, "上年商业险保费"), 3200)
ck("P10 get_money 维修费", ic.get_money(text, "预估维修费"), 1500)

# ---------------- 取值
ck("T01 车型", ic.get_text(text, "车型"), "大众朗逸")
ck("T02 使用性质", ic.get_text(text, "车辆使用性质"), "非营运")
ck("T03 责任比例", ic.get_text(text, "我方责任比例"), "次责")
ck("T04 空表", ic.get_text(etext, "车型"), "")
ck("T05 标题不算", ic.get_text(text, "项"), "")

# ---------------- yes/no
ck("Y01 交强险是", ic.yes(text, "交强险是否投保"), True)
ck("Y02 座位险否", ic.yes(text, "是否投保座位险"), False)
ck("Y03 医保外否", ic.yes(text, "医保外用药"), False)
ck("Y04 车损是", ic.yes(text, "是否投保车损险"), True)
ck("Y05 过户否", ic.yes(text, "是否过户"), False)
ck("Y06 空表 None", ic.yes(etext, "交强险是否投保"), None)
ck("Y07 酒驾否", ic.yes(text, "酒驾"), False)
ck("Y08 驾驶证有效", ic.yes(text, "驾驶证是否有效"), True)

# ---------------- 完整报告
body, meta = ic.build_report(SAMPLE, BASE)
ck_true("R01 生成", body is not None, str(meta))
ck_true("R02 九段", body.count("## ") >= 9, str(body.count("## ")))
ck_true("R03 结论摘要", "结论摘要" in body)
ck_true("R04 保障缺口", "保障缺口核查" in body)
ck_true("R05 保费与 NCD", "保费与 NCD" in body)
ck_true("R06 报不报", "报不报保险" in body)
ck_true("R07 拒赔扫描", "拒赔风险扫描" in body)
ck_true("R08 待办", "待办动作" in body)
ck_true("R09 纪律", "输出纪律" in body)
ck_true("R10 两个缺口", meta.get("gaps") == 2, str(meta))
ck_true("R11 座位险缺", "**缺**" in body, str(body.count("**缺**")))
ck_true("R12 无拒赔", meta.get("denies") == 0, str(meta))
ck_true("R13 涨费估算 800", meta.get("estimated_premium_up") == 800, str(meta))
ck_true("R14 结论报保险", meta.get("advice_report") is True, str(meta))
ck_true("R15 1500>800 文案", "报保险更划算" in body)
ck_true("R16 未填不算通过", "未填的不算" in body)
ck_true("R17 三者 100 万不算低", "额度偏低" not in body)
ck_true("R18 无【待填】泄漏", "【待填】" not in body)
ck_true("R19 无乱码", "\ufffd" not in body)
ck_true("R21 48小时取到否", "是否超 48 小时 | 否" in body,
        [ln for ln in body.splitlines() if "48 小时 |" in ln])
ck_true("R22 材料区分有缺", "已有" in body, str(body.count("已有")))
ck_true("R23 建议不嵌套加粗",
        "报保险更划算" in body and "元，**报" not in body and "**维修费" in body)

bad = [ln for ln in body.splitlines() if ln.count("|") > 6]
ck_true("R20 表格不裂", not bad, str(bad[:2]))

# ---------------- 三者 50 万场景
LOW = os.path.join(HERE, "_tmp_low.md")
with open(LOW, "w", encoding="utf-8") as f:
    f.write("## 二、现有保单\n\n| 项 | 填什么 |\n|---|---|\n")
    f.write("| 车型 | 别克英朗 |\n")
    f.write("| 交强险是否投保 | 是 |\n")
    f.write("| 是否投保车损险 | 是 |\n")
    f.write("| 是否投保第三者责任险 | 是 |\n")
    f.write("| 三者险保额（万元） | 50 |\n")
    f.write("| 是否投保座位险 | 否 |\n")
    f.write("| 上年商业险保费（元） | 4000 |\n")
    f.write("| 预估维修费（元） | 300 |\n")
b3, m3 = ic.build_report(LOW, BASE)
ck_true("L01 低三者生成", b3 is not None, str(m3))
ck_true("L02 提示额度偏低", "额度偏低" in b3)
ck_true("L03 300<1000 自费", "自费更划算" in b3, str(m3))
ck_true("L04 涨费 1000", m3.get("estimated_premium_up") == 1000, str(m3))

# ---------------- 拒赔场景（营运 + 逾期未报案）
DENY = os.path.join(HERE, "_tmp_deny.md")
with open(DENY, "w", encoding="utf-8") as f:
    f.write("## 一、车辆情况\n\n| 项 | 填什么 |\n|---|---|\n")
    f.write("| 车型 | 丰田卡罗拉 |\n")
    f.write("| 车辆使用性质 | 非营运 |\n\n")
    f.write("## 二、现有保单\n\n| 项 | 填什么 |\n|---|---|\n")
    f.write("| 交强险是否投保 | 是 |\n")
    f.write("| 是否投保第三者责任险 | 是 |\n")
    f.write("| 三者险保额（万元） | 200 |\n")
    f.write("| 上年商业险保费（元） | 3500 |\n\n")
    f.write("## 三、本次事故情况\n\n| 项 | 填什么 |\n|---|---|\n")
    f.write("| 是否有人伤 | 有 |\n")
    f.write("| 距事发是否超 48 小时 | 是 |\n\n")
    f.write("## 四、拒赔风险自查\n\n| 问题 | 填什么 |\n|---|---|\n")
    f.write("| 是否实际从事营运（跑网约车等） | 是 |\n")
    f.write("| 车辆是否按期年检 | 否 |\n")
    f.write("| 改装是否告知保险公司 | 未告知 |\n")
b4, m4 = ic.build_report(DENY, BASE)
ck_true("D01 拒赔生成", b4 is not None, str(m4))
ck_true("D02 命中营运", "营运" in b4.split("## 五")[1].split("## 六")[0])
ck_true("D03 命中未年检", "未按期年检" in b4)
ck_true("D04 命中超48", "48 小时" in b4)
ck_true("D05 人伤一律报", "有人伤一律报保险" in b4)
ck_true("D06 denies>=3", m4.get("denies", 0) >= 3, str(m4))

# ---------------- 空表
r2 = ic.build_report(EMPTY, BASE)
ck_true("E01 空表 None", r2[0] is None, str(r2[0])[:60])
ck_true("E02 空表提示", isinstance(r2[1], str) and "未解析" in r2[1], str(r2[1])[:60])
r3 = ic.build_report(os.path.join(HERE, "不存在.md"), BASE)
ck_true("E03 缺文件不崩", r3[0] is None)

for p in (LOW, DENY):
    try:
        os.remove(p)
    except Exception:
        pass

LINES.append("== TOTAL PASS=%d FAIL=%d ==" % (PASS, FAIL))
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(LINES) + "\n")
print("PASS=%d FAIL=%d" % (PASS, FAIL))
