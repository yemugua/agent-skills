# -*- coding: utf-8 -*-
"""遗嘱效力核查 回归测试（自写 utf-8 结果文件）"""
import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import will_check as wc  # noqa: E402

SAMPLE = os.path.join(HERE, "遗嘱样例.md")
EMPTY = os.path.join(HERE, "空遗嘱信息.md")
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
ck("P01 norm", wc.norm(" 打 印 "), "打印")
ck("P02 is_ph 待填", wc.is_ph("【待填】"), True)
ck("P03 is_ph 分隔", wc.is_ph("---"), True)
ck("P04 is_ph 真值", wc.is_ph("打印"), False)
ck("P05 pick_form", wc.pick_form(text), "打印")
ck("P06 pick_form 空表", wc.pick_form(etext), "")
ck("P07 get_int 页数", wc.get_int(text, "遗嘱页数"), 3)
ck("P08 get_int 年龄", wc.get_int(text, "年龄"), 78)
ck("P09 标题不算", wc.get_text(text, "项"), "")

# ---------------- yes/no
ck("Y01 逐页签名否", wc.yes(text, "是否逐页签名"), False)
ck("Y02 注明日期是", wc.yes(text, "是否注明年月日"), True)
ck("Y03 夫妻共同是", wc.yes(text, "是否处分夫妻共同财产"), True)
ck("Y04 只处分本人份额否", wc.yes(text, "是否只处分本人份额"), False)
ck("Y05 有人知道否", wc.yes(text, "是否有人知道遗嘱在哪"), False)
ck("Y06 空表 None", wc.yes(etext, "是否注明年月日"), None)

# ---------------- 完整报告
body, meta = wc.build_report(SAMPLE, BASE)
ck_true("R01 生成", body is not None, str(meta))
ck_true("R02 九段", body.count("## ") >= 9, str(body.count("## ")))
ck_true("R03 结论摘要", "结论摘要" in body)
ck_true("R04 形式要件", "形式要件逐条核查" in body)
ck_true("R05 见证人", "见证人资格审查" in body)
ck_true("R06 无效撤回", "无效与撤回风险扫描" in body)
ck_true("R07 处分范围", "处分范围核查" in body)
ck_true("R08 必留份", "必留份" in body)
ck_true("R09 待办", "待办补正动作" in body)
ck_true("R10 纪律", "输出纪律" in body)
ck("R11 形式=打印", meta.get("form"), "打印")
ck_true("R12 逐页签名缺失被抓", "每一页" in body and "**否**" in body)
ck_true("R13 见证人亲属硬伤", "亲属关系" in body and "不能做见证人" in body)
ck_true("R14 夫妻共同份额", "超出本人份额的部分无效" in body)
ck_true("R15 必留份未保留", "未保留必要份额" in body)
ck_true("R16 多份抵触以最后为准", "以**最后的**为准" in body)
ck_true("R17 没人知道遗嘱在哪", "等于没立" in body)
ck_true("R18 未填不算通过", "未填的一律不算通过" in body)
ck_true("R19 无【待填】泄漏", "【待填】" not in body)
ck_true("R20 无乱码", "\ufffd" not in body)
ck_true("R21 见证人硬伤计数", meta.get("witness_issues", 0) >= 1, str(meta))

bad = [ln for ln in body.splitlines() if ln.count("|") > 6]
ck_true("R22 表格不裂", not bad, str(bad[:2]))

# ---------------- 自书遗嘱合格场景
OK = os.path.join(HERE, "_tmp_ok.md")
with open(OK, "w", encoding="utf-8") as f:
    f.write("## 二、遗嘱形式\n\n| 项 | 填什么 |\n|---|---|\n")
    f.write("| 遗嘱形式 | 自书 |\n")
    f.write("| 是否亲笔书写全文 | 是 |\n")
    f.write("| 是否有遗嘱人签名 | 有 |\n")
    f.write("| 是否注明年月日 | 是 |\n\n")
    f.write("## 六、保管与执行\n\n| 项 | 填什么 |\n|---|---|\n")
    f.write("| 是否有人知道遗嘱在哪 | 是 |\n")
b2, m2 = wc.build_report(OK, BASE)
ck_true("O01 自书生成", b2 is not None, str(m2))
ck_true("O02 形式=自书", m2.get("form") == "自书", str(m2))
ck_true("O03 无缺失", m2.get("missing_form_items") == 0, str(m2))
ck_true("O04 不需要见证人", "不需要见证人" in b2)
ck_true("O05 已填项齐备", "已填项全部齐备" in b2)

# ---------------- 口头遗嘱场景
ORAL = os.path.join(HERE, "_tmp_oral.md")
with open(ORAL, "w", encoding="utf-8") as f:
    f.write("## 二、遗嘱形式\n\n| 项 | 填什么 |\n|---|---|\n")
    f.write("| 遗嘱形式 | 口头 |\n")
    f.write("| 是否有遗嘱人签名 | 无 |\n\n")
    f.write("## 三、见证人情况\n\n| 项 | 填什么 |\n|---|---|\n")
    f.write("| 见证人数量 | 2 |\n")
    f.write("| 见证人与继承人是否亲属关系 | 无 |\n")
b3, m3 = wc.build_report(ORAL, BASE)
ck_true("V01 口头生成", b3 is not None, str(m3))
ck_true("V02 口头提示危急", "危急" in b3)
ck_true("V03 口头提示重立", "重立" in b3)

# ---------------- 空表
r2 = wc.build_report(EMPTY, BASE)
ck_true("E01 空表 None", r2[0] is None, str(r2[0])[:60])
ck_true("E02 空表提示", isinstance(r2[1], str) and "未解析" in r2[1], str(r2[1])[:60])
r3 = wc.build_report(os.path.join(HERE, "不存在.md"), BASE)
ck_true("E03 缺文件不崩", r3[0] is None)

for p in (OK, ORAL):
    try:
        os.remove(p)
    except Exception:
        pass

LINES.append("== TOTAL PASS=%d FAIL=%d ==" % (PASS, FAIL))
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(LINES) + "\n")
print("PASS=%d FAIL=%d" % (PASS, FAIL))
