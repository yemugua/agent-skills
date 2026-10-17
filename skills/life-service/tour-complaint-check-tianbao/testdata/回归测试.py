#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""旅游投诉维权与退款核算 —— 回归测试。

用法：python testdata/回归测试.py
结果写 testdata/_reg_result.txt
"""
import json
import os
import re
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPT_DIR)

import tour_check as tc  # noqa: E402

PASS = [0]
FAIL = [0]
FAILED = []


def ck(cond, name):
    if cond:
        PASS[0] += 1
    else:
        FAIL[0] += 1
        FAILED.append(name)


def ck_eq(actual, expect, name):
    ck(actual == expect, "%s (期望 %r，实际 %r)" % (name, expect, actual))


def ck_in(sub, big, name):
    ck(sub in big, "%s (期望含「%s」)" % (name, sub))


def ck_not(sub, big, name):
    ck(sub not in big, "%s (期望不含「%s」)" % (name, sub))


# ------------------------------------------------------------------ 解析
kv = tc.build_kv("| 团号 / 合同号 | KL-2026 |\n| 合同总价（元） | 5680 |")
ck_eq(kv.get("团号 / 合同号"), "KL-2026", "A01 表格行解析")
ck_eq(kv.get("合同总价（元）"), "5680", "A02 表格长字段名")

kv2 = tc.build_kv("投诉人：张明\n行程结束日期：2026-08-05")
ck_eq(kv2.get("投诉人"), "张明", "A03 冒号行解析")
ck_eq(kv2.get("行程结束日期"), "2026-08-05", "A04 冒号行日期字段")

ck_eq(tc.get_text(kv2, ["投诉人", "投诉人姓名"]), "张明", "A05 别名命中")
kv3 = tc.build_kv("| 投诉人姓名 | 王五 |\n| 投诉人 | 张三 |")
ck_eq(tc.get_text(kv3, ["投诉人", "投诉人姓名"]), "王五", "A06 最长别名优先")
ck_eq(tc.get_text(kv3, ["投诉人"]), "张三", "A06b 短别名仍可取到")
ck_eq(tc.get_text(kv3, ["投诉人姓名"]), "王五", "A07 精确别名可取到")
ck_eq(tc.get_text({}, ["不存在"]), "", "A08 空 k v 取不到返回空串")

ck(tc.filled("是"), "A09 filled 有值")
ck(not tc.filled(""), "A10 filled 空串")
ck(not tc.filled("   "), "A11 filled 纯空格")
ck(not tc.filled("有/无"), "A12 filled 斜杠占位")
ck(not tc.filled("【待填】"), "A13 filled 待填占位")
ck(not tc.filled("例如四星"), "A14 filled 示例占位")
ck(tc.filled(5680.0), "A15 filled 数值不报错")
ck(tc.filled(None) is False, "A16 filled None")

ck(tc.yes("是"), "B01 yes 是")
ck(tc.yes("有"), "B02 yes 有")
ck(tc.yes("已申请"), "B03 yes 已申请")
ck(not tc.yes("否"), "B04 yes 否为假")
ck(not tc.yes(""), "B05 yes 空为假")
ck(tc.no("否"), "B06 no 否")
ck(tc.no("没有"), "B07 no 没有")
ck(tc.no("未"), "B08 no 未")
ck(not tc.no("是"), "B09 no 是为假")
ck(not tc.no("不确定"), "B10 no 不确定为假")

ck_eq(tc.norm("四星（准四）: 有"), "四星(准四):有", "B11 norm 全半角归一")
ck_eq(tc.norm(None), "", "B12 norm None")

ck_eq(tc.parse_num("¥3,800"), 3800.0, "B13 parse_num 带¥与逗号")
ck_eq(tc.parse_num("5680 元"), 5680.0, "B14 parse_num 带单位")
ck_eq(tc.parse_num(""), None, "B15 parse_num 空")
ck_eq(tc.parse_num("无"), None, "B16 parse_num 无")
ck_eq(tc.parse_num(None), None, "B17 parse_num None")

ck_eq(tc.fmt_num(5680.0), "5680", "B18 fmt_num 去 .0")
ck_eq(tc.fmt_num(5680.5), "5680.5", "B19 fmt_num 保留小数")
ck_eq(tc.fmt_num(None), "—", "B20 fmt_num 空")
ck_eq(tc.fmt_money(3800.0), "¥3800", "B21 fmt_money 整数")
ck_eq(tc.fmt_money(None), "¥—", "B22 fmt_money 空")

ck_eq(tc.parse_date("2026-08-05"), date(2026, 8, 5), "B23 parse_date 横杠")
ck_eq(tc.parse_date("2026年8月5日"), date(2026, 8, 5), "B24 parse_date 中文")
ck_eq(tc.parse_date("没有"), None, "B25 parse_date 无日期")
ck_eq(tc.base_date("2026-10-05"), date(2026, 10, 5), "B26 base_date")
ck_eq(tc.base_date(""), date.today(), "B27 base_date 空取今天")


def mkf(**kw):
    f = {
        "complainant": "", "target": "", "group_no": "", "form": "",
        "dep_date": "", "end_date": "", "total": None, "paid": None,
        "refunded": None, "deduct_items": "", "personal_cancel": "",
        "notice_date": "", "days_left": None, "clause": "", "irrevocable": "",
        "shop_amt": None, "shop_problem": "", "shop_return": "",
        "change_plan": "", "force_shop": "", "extra_pay": "",
        "extra_pay_known_txt": "", "hotel_std": "", "hotel_actual": "",
        "meal_std": "", "meal_actual": "", "guide_mismatch": "",
        "major_break": "", "force_majeure": "", "ma_announce": "",
        "ma_report": "", "written_complain": "", "reply": "",
        "platform_appeal": "", "d12345": "", "cultur": "", "d12315": "",
        "waiver": "", "claim": "",
        "ev_contract": "", "ev_itinerary": "", "ev_pay": "", "ev_ad": "",
        "ev_photo": "", "ev_chat": "", "ev_ticket": "", "ev_shop_ticket": "",
        "ev_witness": "", "ev_announce": "",
        "hotel_down": False, "meal_down": False,
        "extra_pay_known": False, "on_platform": False, "disagree": False,
    }
    f.update(kw)
    # 与 build_report 里的派生逻辑保持一致
    f["hotel_down"] = bool(f["hotel_std"]) and bool(f["hotel_actual"]) \
        and f["hotel_std"] != f["hotel_actual"]
    f["meal_down"] = bool(f["meal_std"]) and bool(f["meal_actual"]) \
        and f["meal_std"] != f["meal_actual"]
    f["extra_pay_known"] = bool(f["extra_pay_known_txt"]) or bool(f["extra_pay"])
    f["on_platform"] = bool(f["platform_appeal"]) and tc.yes(f["platform_appeal"])
    f["disagree"] = bool(f["ev_ad"]) or bool(f["ev_chat"])
    return f


# ------------------------------------------------------------------ 定性
t, _b = tc.classify_type(mkf())
ck_eq(t, "待补正", "C01 全空定性为待补正")

t, _b = tc.classify_type(mkf(force_shop="是"))
ck_in("旅行社违约：强迫或变相强迫购物", t, "C02 强迫购物定性")

t, _b = tc.classify_type(mkf(force_shop="是", total=5680.0))
ck_not("个人原因退团", t, "C03 个人退团填否不误加")

t, _b = tc.classify_type(mkf(personal_cancel="否"))
ck_not("个人原因退团", t, "C04 填否不出现个人退团行")

t, _b = tc.classify_type(mkf(personal_cancel="是"))
ck_in("个人原因退团", t, "C05 填是出现个人退团行")

t, _b = tc.classify_type(mkf(change_plan="擅自把玉龙雪山换成珠宝店"))
ck_in("擅自变更行程", t, "C06 擅自变更定性")

t, _b = tc.classify_type(mkf(force_majeure="台风"))
ck_in("不可抗力", t, "C07 不可抗力关键词命中")

t, _b = tc.classify_type(mkf(force_majeure="天气不太好"))
ck_not("不可抗力/已尽合理注意仍不能避免", t, "C08 非关键词不误判不可抗力")

t, _b = tc.classify_type(mkf(force_majeure="台风", hotel_std="四星",
                             hotel_actual="三星"))
ck_in("混合情形", t, "C09 不可抗力叠加降标走混合情形")

t, _b = tc.classify_type(mkf(platform_appeal="是", ev_ad="宣传页截图"))
ck_in("平台（OTA）责任", t, "C10 平台责任定性")

t, _b = tc.classify_type(mkf(major_break="甩团，没人管返程"))
ck_in("甩团", t, "C11 甩团定性")


# ------------------------------------------------------------------ 退款
def r_calc(**kw):
    lo, hi, _n = tc.refund_calc(mkf(**kw))
    return lo, hi


lo, hi, note_nonp = tc.refund_calc(mkf(personal_cancel="否",
                                       total=5680.0, days_left=20))
ck_eq(lo, None, "D01 非个人原因不给比例值")
ck_eq(hi, None, "D02 非个人原因上限空")
ck_in("非个人原因", note_nonp, "D04 给出非个人原因全额退口径")
ck_not("扣费阶梯", note_nonp, "D04b 非个人原因不套扣费阶梯")
lo, hi = r_calc(personal_cancel="是")
ck_eq((lo, hi), (None, None), "D05 个人退团缺总价不出区间")
lo, hi = r_calc(personal_cancel="是", total=5680.0)
ck_eq(lo, None, "D06 个人退团缺天数不出区间")
lo, hi = r_calc(personal_cancel="是", total=5680.0, days_left=20)
ck_eq((lo, hi), (95, 100), "D07 15 日以上可退 95~100")
lo, hi = r_calc(personal_cancel="是", total=5680.0, days_left=10)
ck_eq((lo, hi), (80, 90), "D08 7~15 日可退 80~90")
lo, hi = r_calc(personal_cancel="是", total=5680.0, days_left=5)
ck_eq((lo, hi), (60, 80), "D09 4~7 日可退 60~80")
lo, hi = r_calc(personal_cancel="是", total=5680.0, days_left=2)
ck_eq((lo, hi), (40, 60), "D10 1~3 日可退 40~60")
lo, hi = r_calc(personal_cancel="是", total=5680.0, days_left=0)
ck_eq((lo, hi), (20, 40), "D11 当日可退 20~40")

lo, hi, note = tc.refund_calc(mkf(personal_cancel="是", total=5680.0, days_left=20))
ck_in("¥5396", note, "D12 15 日以上折算下限金额")
ck_in("¥5680", note, "D13 15 日以上折算上限金额")
ck_in("当地示范文本", note, "D14 口径提示当地口径")
ck_in("举证", note, "D15 提示旅行社举证")

# ------------------------------------------------------------------ 违约核查
rows = tc.checks_breach(mkf())
names = [r[0] for r in rows]
ck_eq("擅自变更行程/减少景点" in names, True, "E01 全空仍出变更行程行")
ck_eq(names[-1] == "降低服务标准", True, "E02 全空出降标行")
ck_eq([r[1] for r in rows if r[0] == "擅自变更行程/减少景点"][0], "待补正",
      "E03 未填=待补正不是通过")

rows = tc.checks_breach(mkf(change_plan="否"))
ck_eq([r[1] for r in rows if r[0] == "擅自变更行程/减少景点"][0], "通过",
      "E04 填否=通过")

rows = tc.checks_breach(mkf(change_plan="是的，改了两个景点"))
ck_eq([r[1] for r in rows if r[0] == "擅自变更行程/减少景点"][0], "不通过",
      "E05 填是=不通过")

rows = tc.checks_breach(mkf(change_plan="是的，改了两个景点"))
ck_eq([r[1] for r in rows if r[0] == "擅自变更行程/减少景点"][0], "不通过",
      "E05b 「是的，…」写法也能识别为不通过")
ck(tc.yes_soft("是的，改了两个景点"), "E05c yes_soft 宽松识别")
ck(not tc.yes_soft("不是我改的"), "E05d yes_soft 不误判否定句")

rows = tc.checks_breach(mkf(change_plan="好像改了"))
ck_eq([r[1] for r in rows if r[0] == "擅自变更行程/减少景点"][0], "待补正",
      "E06 模糊表述=待补正")

rows = tc.checks_breach(mkf(change_plan="否"))
ck_in("行程未发生擅自变更", "".join(r[2] for r in rows), "E07 填否文案正确")

rows = tc.checks_breach(mkf(force_shop="是", change_plan="否",
                            extra_pay="否", extra_pay_known=False,
                            hotel_std="四星", hotel_actual="三星",
                            meal_std="", meal_actual=""))
ck_eq([r[1] for r in rows if r[0] == "强迫或变相强迫购物"][0], "不通过",
      "E08 强迫购物=不通过")
ck_eq([r[1] for r in rows if r[0] == "降低服务标准"][0], "不通过",
      "E09 住宿降标=不通过")
ck_in("四星", "".join(r[2] for r in rows), "E10 住宿对比写出约定标准")
ck_in("三星", "".join(r[2] for r in rows), "E11 住宿对比写出现实标准")

rows = tc.checks_breach(mkf(hotel_std="四星", hotel_actual="四星",
                            meal_std="30", meal_actual="30"))
ck_eq([r[1] for r in rows if r[0] == "降低服务标准"][0], "通过",
      "E12 标准一致=通过")

rows = tc.checks_breach(mkf(meal_std="30 元", meal_actual="10 元"))
ck_eq([r[1] for r in rows if r[0] == "降低服务标准"][0], "不通过",
      "E13 餐标降=不通过")

rows = tc.checks_breach(mkf(extra_pay="是", extra_pay_known_txt="否",
                            extra_pay_known=True))
ck_eq([r[1] for r in rows if r[0] == "另行付费项目未事先说明"][0], "不通过",
      "E14 另付费且未事先说明=不通过")

rows = tc.checks_breach(mkf(extra_pay="是", extra_pay_known_txt="是",
                            extra_pay_known=True))
ck_eq([r[1] for r in rows if r[0] == "另行付费项目"][0], "通过",
      "E15 另付费已事先说明=通过")

rows = tc.checks_breach(mkf(extra_pay="是", extra_pay_known_txt="记不清",
                            extra_pay_known=True))
ck_eq([r[1] for r in rows if r[0] == "另行付费项目是否事先说明"][0], "待补正",
      "E16 另付费说明未知=待补正")

rows = tc.checks_breach(mkf(waiver="签了免责协议"))
ck_eq([r[1] for r in rows if r[0] == "已签免责/放弃索赔协议"][0], "有风险",
      "E17 签免责=有风险")
ck_in("效力有争议", "".join(r[2] for r in rows), "E18 免责风险给出提示")

rows = tc.checks_breach(mkf(major_break="否"))
ck_eq([r[1] for r in rows if r[0] == "甩团/拒载返程"][0], "通过",
      "E19 无甩团=通过")

# ------------------------------------------------------------------ 证据
rows = tc.checks_evidence(mkf())
ck_eq(len(rows), 10, "F01 证据 10 项")
ck_eq([r[1] for r in rows if r[0] == "同行证言"][0], "待补正", "F02 未填=待补正")
rows = tc.checks_evidence(mkf(ev_witness="是"))
ck_eq([r[1] for r in rows if r[0] == "同行证言"][0], "通过", "F03 有=通过")
rows = tc.checks_evidence(mkf(ev_witness="无"))
ck_eq([r[1] for r in rows if r[0] == "同行证言"][0], "不通过", "F04 无=不通过")

# ------------------------------------------------------------------ 渠道
rows = tc.checks_channel(mkf(d12345="否"))
det = [r[2] for r in rows if r[0] == "12345 政务服务热线"][0]
ck_in("派单到属地文旅部门", det, "G01 12345 待办写清动作")
ck_not("工单号s", det, "G02 待办文案无多余字母")
ck_in("12345", det, "G03 待办给出顺位提示")
rows = tc.checks_channel(mkf(d12345="是"))
ck_eq([r[1] for r in rows if r[0] == "12345 政务服务热线"][0], "通过",
      "G04 已打 12345=通过")
rows = tc.checks_channel(mkf(written_complain="否"))
ck_eq([r[1] for r in rows if r[0] == "已向旅行社书面投诉"][0], "待补正",
      "G05 未书面交涉=待补正")
rows = tc.checks_channel(mkf(written_complain="是", written_detail="2026-09-01"))
ck_eq([r[1] for r in rows if r[0] == "已向旅行社书面投诉"][0], "通过",
      "G06 已书面=通过")

# ------------------------------------------------------------------ 购物与 30 日
rows = tc.shopping_checks(mkf(shop_amt=3800.0), -31)
ck_eq([r[1] for r in rows if r[0] == "30 日退货期限"][0], "有风险",
      "H01 超 30 日=有风险")
ck_in("30 日规则已过", "".join(r[2] for r in rows), "H02 超期文案出现")
rows = tc.shopping_checks(mkf(shop_amt=3800.0), 10)
ck_eq([r[1] for r in rows if r[0] == "30 日退货期限"][0], "通过", "H03 未超 30 日=通过")
rows = tc.shopping_checks(mkf(shop_amt=3800.0, shop_problem="证书与实物不符"), None)
ck_eq([r[1] for r in rows if r[0] == "商品问题"][0], "不通过", "H04 商品有问题=不通过")
ck_in("先行垫付", "".join(r[2] for r in rows), "H05 提示先行垫付")
rows = tc.shopping_checks(mkf(shop_amt=3800.0, shop_return="否"), None)
ck_eq([r[1] for r in rows if r[0] == "退货申请"][0], "不通过", "H06 未申请退货=不通过")
rows = tc.shopping_checks(mkf(), None)
ck_eq([r[1] for r in rows if r[0] == "购物退货"][0], "待补正", "H07 全空=待补正")


# ------------------------------------------------------------------ 报告
SAMPLE = os.path.join(HERE, "样例.md")
EMPTY = os.path.join(HERE, "空输入.md")

rep, meta = tc.build_report(SAMPLE, date(2026, 10, 5))
ck(rep is not None, "J01 样例能出报告")
ck(meta is not None and meta.get("结论"), "J02 meta 有结论字段")
ck_eq(meta.get("结论"), "不通过", "J03 样例结论为不通过")
ck_eq(meta.get("纠纷定性").startswith("旅行社违约"), True, "J04 样例定性为旅行社违约")
ck_in("强迫或变相强迫购物", meta.get("结论明细", {}).get("不通过", []), "J05 不通过项含强迫购物")
ck_eq(meta.get("风险项"), ["30 日退货期限"], "J06 风险项名单")

sec = re.findall(r"^## ", rep, flags=re.M)
ck(len(sec) >= 9, "J07 报告至少 9 段（实际 %d）" % len(sec))
ck_in("## 一、结论摘要", rep, "J08 含结论摘要")
ck_in("## 八、待办补正动作", rep, "J09 含待办")
ck_in("## 九、边界与纪律", rep, "J10 含边界与纪律")
ck_in("待办", rep, "J11 正文有待办字样")
ck_not("纠纷定性**：旅行社违约：个人原因退团", rep, "J12 样例不出现个人退团错判")
ck_eq(rep.count("- **纠纷定性**"), 1, "J13 纠纷定性 bullet 不重复")
ck_not("工单号s", rep, "J14 报告渠道文案无多余字母")
ck_in("以当地", rep, "J15 报告提示以当地口径为准")
ck_in("不替代律师意见", rep, "J16 报告有免责表述")
ck_not("�", rep, "J17 报告无乱码")
ck_in("¥5680", rep, "J18 报告写出合同总价")

rep2, meta2 = tc.build_report(EMPTY, date(2026, 10, 5))
ck(rep2 is None, "J19 空输入不出报告")
ck("未解析到关键信息" in "".join(meta2), "J20 空输入给提示串")

json.loads(json.dumps(meta, ensure_ascii=False))
ck(True, "J21 meta 可序列化")


# ------------------------------------------------------------------ 子进程
proc = os.path.join(SCRIPT_DIR, "tour_check.py")


def run_cli(args):
    p = subprocess.run([sys.executable, proc] + args,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode, p.stdout.decode("utf-8", "replace")


rc, _out = run_cli([SAMPLE, "--base", "2026-10-05",
                    "--out", os.path.join(HERE, "_样例报告.md")])
ck_eq(rc, 0, "K01 样例子进程 rc=0")

rc, _out = run_cli([EMPTY, "--base", "2026-10-05"])
ck_eq(rc, 2, "K02 空输入子进程 rc=2")

rc, txt = run_cli([SAMPLE, "--json"])
ck_eq(rc, 0, "K03 子进程 --json rc=0")
try:
    obj = json.loads(txt)
    ck(True, "K04 --json 可解析")
    ck(obj.get("结论") == "不通过", "K05 子进程 json 结论一致")
    ck("待办" in obj and isinstance(obj["待办"], list), "K06 子进程 json 有待办")
    ck("可退比例" in obj, "K07 子进程 json 有可退比例")
except Exception as e:
    ck(False, "K04 --json 可解析 (%s)" % e)

# ------------------------------------------------------------------ 汇总
lines = []
lines.append("== TOUR 回归 %d 条 ==" % (PASS[0] + FAIL[0]))
lines.append("PASS=%d FAIL=%d" % (PASS[0], FAIL[0]))
if FAILED:
    lines.append("--- FAIL LIST ---")
    for n in FAILED:
        lines.append("FAIL: " + n)
lines.append("== TOTAL PASS=%d FAIL=%d ==" % (PASS[0], FAIL[0]))
out = "\n".join(lines) + "\n"
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as fh:
    fh.write(out)
sys.stdout.write(out)
sys.exit(1 if FAIL[0] else 0)
