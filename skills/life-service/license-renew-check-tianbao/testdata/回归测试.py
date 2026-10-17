# -*- coding: utf-8 -*-
"""驾驶证换证办理核查 回归测试（自写 utf-8 结果文件）"""
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import license_check as lc  # noqa: E402

SAMPLE = os.path.join(HERE, "样例.md")
EMPTY = os.path.join(HERE, "空输入.md")
BASE = dt.date(2026, 10, 5)

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


def mk(name, pairs):
    """造一张临时采集表"""
    p = os.path.join(HERE, "_tmp_%s.md" % name)
    with open(p, "w", encoding="utf-8") as f:
        f.write("| 项 | 填什么 |\n|---|---|\n")
        for k, v in pairs:
            f.write("| %s | %s |\n" % (k, v))
    return p


with open(SAMPLE, encoding="utf-8") as f:
    text = f.read()
with open(EMPTY, encoding="utf-8") as f:
    etext = f.read()

# ---------------- 基础解析
ck("P01 norm 去空格", lc.norm(" 成 都 市 "), "成都市")
ck("P02 norm 去竖线", lc.norm("|B2|"), "B2")
ck("P03 is_ph 待填", lc.is_ph("【待填】"), True)
ck("P04 is_ph 待填带说明", lc.is_ph("【待填，如 42】"), True)
ck("P05 is_ph 是/否", lc.is_ph("是 / 否"), True)
ck("P06 is_ph 真值", lc.is_ph("B2"), False)
ck("P07 is_ph 日期", lc.is_ph("2026-06-18"), False)
ck("P08 is_ph 不清蜇", lc.is_ph("不清楚"), True)
ck("P09 get_text 姓名", lc.get_text(text, "驾驶人姓名", "姓名"), "周建国")
ck("P10 get_int 年龄", lc.get_text(text, "年龄"), "58")
ck("P11 get_int 分数", lc.get_int(text, "当前记分周期内已记分数"), 3)
ck("P12 表头不算值", lc.get_text(text, "项"), "")
ck("P13 parse_date", lc.parse_date("2026-06-18"), dt.date(2026, 6, 18))
ck("P14 parse_date 中文", lc.parse_date("2026年6月18日"), dt.date(2026, 6, 18))
ck("P15 parse_date 空", lc.parse_date("未填"), None)
ck("P16 fmt_num 去点零", lc.fmt_num(109.0), "109")
ck("P17 money", lc.money(10), "¥10")
ck("P18 add_years", lc.add_years(dt.date(2026, 6, 18), 1), dt.date(2027, 6, 18))
ck("P19 add_years 闰日", lc.add_years(dt.date(2024, 2, 29), 1), dt.date(2025, 2, 28))

# ---------------- yes 判定（防子串误判）
ck("Y01 未处理违法=有（含未缴款不误判）",
   lc.yes(text, "是否有未处理的道路交通安全违法行为"), True)
ck("Y02 未结案事故=无", lc.yes(text, "是否有未结案的交通事故"), False)
ck("Y03 每个周期均未满12分=否",
   lc.yes(text, "本证期间是否每个记分周期均未记满12分"), False)
ck("Y04 有无记满12分周期=有", lc.yes(text, "有无记满12分的记分周期"), True)
ck("Y05 异地=是", lc.yes(text, "是否异地办理"), True)
ck("Y06 已登录12123=否", lc.yes(text, "是否已安装并登录交管12123"), False)
ck("Y07 年满70=否", lc.yes(text, "是否年满70周岁"), False)
ck("Y08 不适用→None", lc.yes(text, "年满70周岁的是否已按年提交身体条件证明"), None)
ck("Y09 空表 None", lc.yes(etext, "是否年满70周岁"), None)
ck("Y10 A/B类有记分=是", lc.yes(text, "A/B类本周期是否有记分"), True)
ck("Y11 空表档位=空", lc.pick_level(etext), "")

# ---------------- 最长别名优先
ck("L01 准驾车型不被A/B类字段抢", lc.pick_type(text), "B2")
ck("L02 体检证明不被70岁字段抢",
   lc.get_text(text, "是否已取得《机动车驾驶人身体条件证明》",
               "是否已取得身体条件证明"), "未取得")
ck("L03 年满70不被按年提交抢",
   lc.get_text(text, "是否年满70周岁"), "否")
ck("L04 按年提交证明取到不适用",
   lc.get_text(text, "年满70周岁的是否已按年提交身体条件证明",
               "是否已按年提交身体条件证明"), "不适用")
ck("L05 有效期止不被起始日抢",
   lc.parse_date(lc.get_text(text, "本证有效期截止日", "本证有效期截止日", "有效期止")),
   dt.date(2026, 6, 18))
ck("L06 起始日正确",
   lc.parse_date(lc.get_text(text, "本证有效期起始日", "有效期起始日")),
   dt.date(2020, 6, 18))

# ---------------- 档位：当前有效期档位
ck("V01 档位识别6年", lc.pick_level(text), "6年")
ck("V02 档位推断6年", lc.infer_level(dt.date(2020, 6, 18), dt.date(2026, 6, 18)), "6年")
ck("V03 档位推断10年", lc.infer_level(dt.date(2014, 3, 1), dt.date(2024, 3, 1)), "10年")
ck("V04 档位推断长期", lc.infer_level(dt.date(2000, 1, 1), dt.date(2030, 1, 1)), "长期")
ck("V05 缺日期推断空", lc.infer_level(None, None), "")

# ---------------- 逾期档位四档
ck("O01 未逾期→1", lc.judge_overdue(dt.date(2026, 6, 18), dt.date(2026, 3, 1))[0], 1)
ck("O02 逾期109天→2", lc.judge_overdue(dt.date(2026, 6, 18), dt.date(2026, 10, 5))[0], 2)
ck("O03 逾期天数", lc.judge_overdue(dt.date(2026, 6, 18), dt.date(2026, 10, 5))[2], 109)
ck("O04 恰好差一天满1年→2",
   lc.judge_overdue(dt.date(2025, 6, 18), dt.date(2026, 6, 17))[0], 2)
ck("O05 恰好满1年→3", lc.judge_overdue(dt.date(2025, 6, 18), dt.date(2026, 6, 18))[0], 3)
ck("O06 满2年→3", lc.judge_overdue(dt.date(2024, 6, 18), dt.date(2026, 6, 18))[0], 3)
ck("O07 恰好满3年→4", lc.judge_overdue(dt.date(2023, 6, 18), dt.date(2026, 6, 18))[0], 4)
ck("O08 逾期5年→4", lc.judge_overdue(dt.date(2021, 1, 1), dt.date(2026, 1, 1))[0], 4)
ck("O09 缺日期→0", lc.judge_overdue(None, BASE)[0], 0)
ck("O10 档位名", lc.judge_overdue(dt.date(2026, 6, 18), dt.date(2026, 10, 5))[1],
   "逾期不满 1 年")

# ---------------- 下次能换几年
ck("N01 6年且全清→10年", lc.judge_next_validity("6年", True, 1)[0], "10 年")
ck("N02 6年且有满分→6年不升档",
   lc.judge_next_validity("6年", False, 1)[0], "6 年（不能升档）")
ck("N03 10年且全清→长期", lc.judge_next_validity("10年", True, 1)[0], "长期有效")
ck("N04 10年且有满分→10年不升档",
   lc.judge_next_validity("10年", False, 2)[0], "10 年（不能升档）")
ck("N05 长期→无需换证", lc.judge_next_validity("长期", True, 1)[0],
   "长期有效，无需期满换证")
ck("N06 未填→待补正", lc.judge_next_validity("", True, 1)[0], "待补正")
ck("N07 记分全清未填→待补正", lc.judge_next_validity("6年", None, 1)[0], "待补正")
ck("N08 逾期3档→先恢复", lc.judge_next_validity("6年", True, 3)[0],
   "先恢复驾驶资格，暂不适用升档")

# ---------------- A/B 类识别
ck("A01 B2识别", lc.is_ab("B2", "")[0], True)
ck("A02 A2识别", lc.is_ab("A2", "")[0], True)
ck("A03 C1不识别", lc.is_ab("C1", "")[0], False)
ck("A04 空不识别", lc.is_ab("", "")[0], False)

# ---------------- 完整报告
body, meta = lc.build_report(SAMPLE, BASE)
ck_true("R01 生成成功", body is not None, str(meta))
ck_true("R02 九段", body.count("## ") >= 9, str(body.count("## ")))
ck_true("R03 结论摘要", "结论摘要" in body)
ck_true("R04 有效期档位", "有效期档位判定" in body)
ck_true("R05 逾期档位", "逾期档位判定" in body)
ck_true("R06 下次能换", "下次能换几年" in body)
ck_true("R07 材料清单", "材料清单" in body)
ck_true("R08 办理路径", "办理路径" in body)
ck_true("R09 特殊分支", "特殊分支与阻断项" in body)
ck_true("R10 待办", "待办补正动作" in body)
ck_true("R11 纪律", "边界与纪律" in body)
ck("R12 结论=有风险", meta.get("结论"), "有风险")
ck("R13 逾期档位=2", meta.get("逾期档位"), 2)
ck("R14 下次能换", meta.get("下次能换几年"), "6 年（不能升档）")
ck_true("R15 逾期驾车警示", "不得驾驶机动车" in body)
ck_true("R16 无证驾驶性质", "无证驾驶性质" in body)
ck_true("R17 科目一提示", "科目一" in body)
ck_true("R18 异地通办", "全国通办" in body)
ck_true("R19 12123", "12123" in body)
ck_true("R20 提前90日", "提前90日" in body)
ck_true("R21 体检机构层级", "县级或者部队团级以上医疗机构" in body)
ck_true("R22 工本费", "¥10" in body)
ck_true("R23 A/B类30日审验", "30 日内" in body)
ck_true("R24 未处理违法被抓", "有未处理的道路交通安全违法行为" in body)
ck_true("R25 居住证明被抓", "异地办理但无居住证明" in body)
ck_true("R26 体检缺失被抓", "未取得《机动车驾驶人身体条件证明》" in body)
ck_true("R27 不予换证条款", "不予换证" in body)
ck_true("R28 未填不算通过", "未填的一律不算通过" in body)
ck_true("R29 无待填泄漏", "【待填" not in body)
ck_true("R30 无乱码", "\ufffd" not in body)
ck_true("R31 风险项>=6", len(meta.get("风险项", [])) >= 6, str(len(meta.get("风险项", []))))
ck_true("R32 待办>=8", len(meta.get("待办", [])) >= 8, str(len(meta.get("待办", []))))
ck_true("R33 无阻断项", len(meta.get("阻断项", [])) == 0)
bad = [ln for ln in body.splitlines() if ln.count("|") > 7]
ck_true("R34 表格不裂", not bad, str(bad[:2]))

# ---------------- 场景：正常临期 + 材料齐
OK = mk("ok", [
    ("准驾车型", "C1"),
    ("初次领证日期", "2014-09-01"),
    ("本证有效期起始日", "2020-09-01"),
    ("本证有效期截止日", "2026-11-01"),
    ("当前有效期档位", "6年"),
    ("驾驶证当前状态", "正常"),
    ("本证期间是否每个记分周期均未记满12分", "是"),
    ("有无记满12分的记分周期", "无"),
    ("当前记分周期内已记分数", "0"),
    ("是否有未处理的道路交通安全违法行为", "无"),
    ("是否有未结案的交通事故", "无"),
    ("是否异地办理", "否"),
    ("是否希望线上办理（交管12123）", "是"),
    ("是否已安装并登录交管12123", "是"),
    ("是否已取得《机动车驾驶人身体条件证明》", "已取得"),
    ("是否存在影响安全驾驶的疾病", "无"),
    ("身份证明（身份证原件）是否具备", "有"),
    ("机动车驾驶证原件是否具备", "有"),
    ("照片是否具备", "当地免提交"),
    ("是否已了解工本费（一般10元）", "是"),
    ("是否年满70周岁", "否"),
    ("是否持有A/B类准驾车型（A1/A2/A3/B1/B2）", "否"),
    ("驾驶证是否被扣押/扣留/暂扣", "无"),
    ("是否属于补证/变更换证/降级换证", "都不是（期满换证）"),
])
b2, m2 = lc.build_report(OK, BASE)
ck_true("C01 生成", b2 is not None, str(m2))
ck("C02 逾期档位=1", m2.get("逾期档位"), 1)
ck("C03 结论=通过", m2.get("结论"), "通过")
ck("C04 下次换10年", m2.get("下次能换几年"), "10 年")
ck_true("C05 已可办理", "已可办理" in b2, str(m2.get("风险项")))

# ---------------- 场景：逾期 2 年（需重考科目一）
O3 = mk("o3", [
    ("准驾车型", "C1"),
    ("本证有效期截止日", "2024-06-01"),
    ("当前有效期档位", "6年"),
    ("本证期间是否每个记分周期均未记满12分", "是"),
    ("是否有未处理的道路交通安全违法行为", "无"),
    ("是否有未结案的交通事故", "无"),
    ("是否异地办理", "否"),
    ("是否已取得《机动车驾驶人身体条件证明》", "已取得"),
    ("身份证明（身份证原件）是否具备", "有"),
    ("机动车驾驶证原件是否具备", "有"),
    ("照片是否具备", "有"),
    ("是否年满70周岁", "否"),
    ("是否持有A/B类准驾车型（A1/A2/A3/B1/B2）", "否"),
    ("驾驶证是否被扣押/扣留/暂扣", "无"),
    ("是否属于补证/变更换证/降级换证", "都不是（期满换证）"),
])
b3, m3 = lc.build_report(O3, BASE)
ck("D01 逾期档位=3", m3.get("逾期档位"), 3)
ck("D02 结论=不通过", m3.get("结论"), "不通过")
ck_true("D03 提示重考科目一", "重考**科目一**" in b3)
ck_true("D04 提示恢复驾驶资格", "恢复驾驶资格" in b3)

# ---------------- 场景：逾期 5 年（重报全部科目）
O4 = mk("o4", [
    ("准驾车型", "C1"),
    ("本证有效期截止日", "2021-01-01"),
    ("当前有效期档位", "6年"),
    ("本证期间是否每个记分周期均未记满12分", "是"),
    ("是否有未处理的道路交通安全违法行为", "无"),
    ("是否有未结案的交通事故", "无"),
    ("是否异地办理", "否"),
    ("是否已取得《机动车驾驶人身体条件证明》", "已取得"),
    ("身份证明（身份证原件）是否具备", "有"),
    ("机动车驾驶证原件是否具备", "有"),
    ("照片是否具备", "有"),
    ("是否年满70周岁", "否"),
    ("是否持有A/B类准驾车型（A1/A2/A3/B1/B2）", "否"),
    ("驾驶证是否被扣押/扣留/暂扣", "无"),
    ("是否属于补证/变更换证/降级换证", "都不是（期满换证）"),
])
b4, m4 = lc.build_report(O4, BASE)
ck("E01 逾期档位=4", m4.get("逾期档位"), 4)
ck("E02 结论=不通过", m4.get("结论"), "不通过")
ck_true("E03 提示重新报考全部科目", "重新报考全部科目" in b4)
ck_true("E04 阻断项>=1", len(m4.get("阻断项", [])) >= 1)

# ---------------- 场景：70 周岁 + 扣押扣留
O5 = mk("o5", [
    ("准驾车型", "E"),
    ("本证有效期截止日", "2026-12-01"),
    ("当前有效期档位", "长期"),
    ("本证期间是否每个记分周期均未记满12分", "是"),
    ("是否有未处理的道路交通安全违法行为", "无"),
    ("是否有未结案的交通事故", "无"),
    ("是否异地办理", "否"),
    ("是否已取得《机动车驾驶人身体条件证明》", "已取得"),
    ("身份证明（身份证原件）是否具备", "有"),
    ("机动车驾驶证原件是否具备", "有"),
    ("照片是否具备", "有"),
    ("是否年满70周岁", "是"),
    ("年满70周岁的是否已按年提交身体条件证明", "否"),
    ("是否持有A/B类准驾车型（A1/A2/A3/B1/B2）", "否"),
    ("驾驶证是否被扣押/扣留/暂扣", "有"),
    ("是否属于补证/变更换证/降级换证", "都不是（期满换证）"),
])
b5, m5 = lc.build_report(O5, BASE)
ck_true("F01 70岁分支", "年满 70 周岁" in b5)
ck_true("F02 70岁未提交证明", "未按年提交身体条件证明" in b5)
ck_true("F03 D/E降级F", "降级为 F" in b5)
ck_true("F04 扣押阻断", "扣押" in b5)
ck("F05 结论=不通过", m5.get("结论"), "不通过")
ck_true("F06 阻断项>=1", len(m5.get("阻断项", [])) >= 1)

# ---------------- 场景：证已丢失 → 应办补证
O6 = mk("o6", [
    ("准驾车型", "C1"),
    ("本证有效期截止日", "2026-12-01"),
    ("当前有效期档位", "6年"),
    ("本证期间是否每个记分周期均未记满12分", "是"),
    ("是否有未处理的道路交通安全违法行为", "无"),
    ("是否有未结案的交通事故", "无"),
    ("是否异地办理", "否"),
    ("是否已取得《机动车驾驶人身体条件证明》", "已取得"),
    ("身份证明（身份证原件）是否具备", "有"),
    ("机动车驾驶证原件是否具备", "已丢失"),
    ("照片是否具备", "有"),
    ("是否年满70周岁", "否"),
    ("是否持有A/B类准驾车型（A1/A2/A3/B1/B2）", "否"),
    ("驾驶证是否被扣押/扣留/暂扣", "无"),
    ("是否属于补证/变更换证/降级换证", "补证"),
])
b6, m6 = lc.build_report(O6, BASE)
ck_true("G01 丢失提示", "已丢失" in b6)
ck_true("G02 提示补证", "补证" in b6)
ck_true("G03 补证不是换证", "不是期满换证" in b6 or "丢失应办**补证**" in b6)

# ---------------- 空表与缺文件
r2 = lc.build_report(EMPTY, BASE)
ck_true("H01 空表返回None", r2[0] is None, str(r2[0])[:60])
ck_true("H02 空表有提示", isinstance(r2[1], str) and "未解析" in r2[1], str(r2[1])[:60])
r3 = lc.build_report(os.path.join(HERE, "不存在的文件.md"), BASE)
ck_true("H03 缺文件不崩", r3[0] is None)

# 缺有效期止但有准驾车型 → 返回 None（无法判档）
O7 = mk("o7", [("准驾车型", "C1"), ("当前有效期档位", "6年")])
r4 = lc.build_report(O7, BASE)
ck_true("H04 缺有效期止返回None", r4[0] is None, str(r4[0])[:60])
ck_true("H05 提示有效期止", "本证有效期截止日" in str(r4[1]))

# ---------------- 冒号行写法
O8 = os.path.join(HERE, "_tmp_colon.md")
with open(O8, "w", encoding="utf-8") as f:
    f.write("准驾车型：C1\n")
    f.write("本证有效期截止日：2026-12-01\n")
    f.write("当前有效期档位：6年\n")
    f.write("本证期间是否每个记分周期均未记满12分：是\n")
    f.write("是否有未处理的道路交通安全违法行为：无\n")
    f.write("是否有未结案的交通事故：无\n")
    f.write("是否已取得《机动车驾驶人身体条件证明》：已取得\n")
    f.write("身份证明（身份证原件）是否具备：有\n")
    f.write("机动车驾驶证原件是否具备：有\n")
    f.write("照片是否具备：无\n")
    f.write("是否年满70周岁：否\n")
    f.write("驾驶证是否被扣押/扣留/暂扣：无\n")
b8, m8 = lc.build_report(O8, BASE)
ck_true("I01 冒号行可解析", b8 is not None, str(m8))
ck("I02 冒号行档位", m8.get("当前有效期档位"), "6年")
ck("I03 冒号行结论", m8.get("结论"), "有风险")
ck_true("I04 冒号行未逾期", m8.get("逾期档位") == 1)
ck_true("I05 冒号行抓到照片缺失", "照片缺失" in b8)
ck_true("I06 冒号行体检已备未报错", "未取得《机动车驾驶人身体条件证明》" not in b8)

# ---------------- json 可解析
try:
    J = os.path.join(HERE, "_tmp_json.md")
    js = lc.build_report(SAMPLE, BASE)[1]
    s = json.dumps(js, ensure_ascii=False)
    d = json.loads(s)
    ck_true("J01 json 可解析", isinstance(d, dict))
    ck_true("J02 含结论", "结论" in d)
    ck_true("J03 含风险项", "风险项" in d)
    ck_true("J04 含待办", "待办" in d)
    ck_true("J05 结论四态", d["结论"] in ("通过", "有风险", "不通过", "待补正"))
except Exception as e:
    ck_true("J01 json 可解析", False, str(e))

for p in (OK, O3, O4, O5, O6, O7, O8):
    try:
        os.remove(p)
    except Exception:
        pass

LINES.append("== TOTAL PASS=%d FAIL=%d ==" % (PASS, FAIL))
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(LINES) + "\n")
print("PASS=%d FAIL=%d" % (PASS, FAIL))
