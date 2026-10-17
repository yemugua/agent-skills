# -*- coding: utf-8 -*-
"""消费者投诉维权路径核查 回归测试（自写 utf-8 结果文件）"""
import datetime as dt
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import complaint_check as cc  # noqa: E402

SAMPLE = os.path.join(HERE, "样例.md")
EMPTY = os.path.join(HERE, "空输入.md")
SCRIPT = os.path.join(ROOT, "scripts", "complaint_check.py")
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


def tmp(name, body):
    p = os.path.join(HERE, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    return p


with open(SAMPLE, encoding="utf-8") as f:
    text = f.read()
with open(EMPTY, encoding="utf-8") as f:
    etext = f.read()

# ---------------- 基础工具
ck("P01 norm 去空格", cc.norm(" 微 信 支 付 "), "微信支付")
ck("P02 norm 全角括号", cc.norm("金额（元）"), "金额(元)")
ck("P03 is_ph 待填", cc.is_ph("【待填】"), True)
ck("P04 is_ph 有/无", cc.is_ph("有 / 无"), True)
ck("P05 is_ph 分隔", cc.is_ph("---"), True)
ck("P06 is_ph 真值", cc.is_ph("平台内商家"), False)
ck("P07 split_row", cc.split_row("| a | b |"), ["a", "b"])
ck("P08 is_row", cc.is_row("| a | b |"), True)
ck("P09 is_row 否", cc.is_row("普通一句话"), False)
ck("P10 fmt_num 整数", cc.fmt_num(3280.0), "3280")
ck("P11 fmt_num None", cc.fmt_num(None), "未填")
ck("P12 money", cc.money(13120.0), "\u00a513120")
ck("P13 fmt_flag 是", cc.fmt_flag(True), "是")
ck("P14 fmt_flag 否", cc.fmt_flag(False), "**否**")
ck("P15 fmt_flag NA", cc.fmt_flag("NA"), "不适用")
ck("P16 have 缺", cc.have(False), "**缺**")

# ---------------- 冒号行也能解析
COLON = tmp("_tmp_colon.md", "商品或服务名称：健身年卡\n消费金额（元）：5980\n争议类型：预付跑路\n")
with open(COLON, encoding="utf-8") as f:
    ctext = f.read()
ck("C01 冒号行 商品", cc.get_text(ctext, "商品或服务名称"), "健身年卡")
ck("C02 冒号行 金额", cc.get_num(ctext, "消费金额"), 5980.0)
ck("C03 冒号行 争议", cc.pick_dispute(ctext)[0], "预付跑路")

# ---------------- 字段解析（样例）
ck("F01 消费者姓名", cc.get_text(text, "消费者姓名"), "陈明远")
ck("F02 经营者名称", cc.get_text(text, "经营者名称"), "宁波清岚环境科技有限公司")
ck("F03 争议类型", cc.pick_dispute(text)[0], "虚假宣传")
ck("F04 消费金额", cc.get_num(text, "消费金额"), 3280.0)
ck("F05 订单号", cc.get_text(text, "订单号"), "XB20260618004471")
ck("F06 损失金额", cc.get_num(text, "已发生损失金额"), 0.0)
ck("F07 自测金额", cc.get_num(text, "自行测算的诉求金额"), 13120.0)
ck("F08 表头不算值", cc.get_text(text, "字段"), "")
ck("F09 是否有平台", cc.yes(text, "是否有电商平台"), True)
ck("F10 是否食品", cc.yes(text, "是否属于食品"), False)
ck("F11 是否主张欺诈", cc.yes(text, "是否主张欺诈"), True)
ck("F12 食品标准不适用", cc.yes(text, "是否主张不符合食品安全标准"), "NA")
ck("F13 是否已协商", cc.yes(text, "是否已与商家协商"), False)
ck("F14 平台介入否", cc.yes(text, "是否已申请平台介入"), False)
ck("F15 空表 None", cc.yes(etext, "是否主张欺诈"), None)

# ---------------- 日期解析
ck("D01 parse_date", cc.parse_date("2026-06-18"), dt.date(2026, 6, 18))
ck("D02 parse_date 中文", cc.parse_date("2026年6月18日"), dt.date(2026, 6, 18))
ck("D03 parse_date 空", cc.parse_date(""), None)
ck("D04 add_years", cc.add_years(dt.date(2026, 6, 28), 3), dt.date(2029, 6, 28))
ck("D05 add_years 闰日", cc.add_years(dt.date(2024, 2, 29), 3), dt.date(2027, 2, 28))

# ---------------- 完整报告（样例）
body, meta = cc.build_report(SAMPLE, BASE)
ck_true("R01 生成", body is not None, str(meta)[:80])
ck("R02 九段", body.count("## "), 9)
ck_true("R03 结论摘要", "结论摘要" in body)
ck_true("R04 路径排序", "维权路径排序" in body)
ck_true("R05 投诉举报定性", "投诉与举报定性" in body)
ck_true("R06 管辖", "管辖与受理口径" in body)
ck_true("R07 证据缺口", "证据清单与缺口" in body)
ck_true("R08 金额测算", "诉求金额测算" in body)
ck_true("R09 时效", "时效与期限倒计时" in body)
ck_true("R10 话术", "话术模板" in body)
ck_true("R11 待办", "待办补正动作" in body)
ck_true("R12 纪律", "边界与纪律" in body)
ck("R13 结论=有风险", meta["结论"], "有风险")
ck("R14 争议类型", meta["争议类型"], "虚假宣传")
ck("R15 诉求合计", meta["诉求合计"], 13120.0)
ck("R16 惩罚性赔偿", meta["惩罚性赔偿"], 9840.0)
ck_true("R17 三倍算式", "x 3 = \u00a59840" in body)
ck("R18 缺口3项", len(meta["证据缺口"]), 3)
ck_true("R19 宣传截图缺口", "宣传页面截图" in "".join(meta["证据缺口"]))
ck_true("R20 检测报告缺口", "检测报告" in "".join(meta["证据缺口"]))
ck_true("R21 当前第1步", "第 1 步" in meta["当前步骤"], meta["当前步骤"])
ck_true("R22 未协商提示", "书面**交涉" in body)
ck_true("R23 平台跳步提示", "跳步" in body)
ck_true("R24 七天已过", "已过 99 天" in body, [x for x in body.splitlines() if "七天" in x])
ck_true("R25 诉讼时效剩余", "还剩 997 天" in body, [x for x in body.splitlines() if "诉讼时效" in x])
ck_true("R26 格式条款无效", "该条款无效" in body)
ck_true("R27 举报不解决退赔", "不解决个人退赔" in body)
ck_true("R28 12315办结60日", "60 日内" in body)
ck_true("R29 7日内受理", "7 日内决定是否受理" in body)
ck_true("R30 管辖平台住所地", "平台住所地" in body)
ck_true("R31 证据编号连续", "1. 订单或合同凭证\n2. 支付凭证\n3. 商品照片或视频" in body)
ck_true("R32 无双句号", "。。" not in body)
ck_true("R33 无【待填】泄漏", "【待填】" not in body)
ck_true("R34 无乱码", "\ufffd" not in body)
bad = [ln for ln in body.splitlines() if ln.count("|") > 6 and not ln.startswith("|")]
ck_true("R35 表格不裂", not bad, str(bad[:2]))
ck_true("R36 待办非空", len(meta["待办"]) >= 5, str(len(meta["待办"])))
ck_true("R37 风险项非空", len(meta["风险项"]) >= 3, str(len(meta["风险项"])))
ck_true("R38 结尾免责", "最终以主管部门或司法机关认定为准" in body)

# ---------------- 场景 A：食品十倍（小额，触发 1000 保底）
FOOD = tmp("_tmp_food.md", """## 二、交易情况
| 字段 | 值 |
|---|---|
| 商品或服务名称 | 某品牌坚果礼盒 |
| 消费金额（元） | 68 |
| 交易日期 | 2026-09-20 |
| 签收日期 | 2026-09-22 |
| 是否属于食品 | 是 |

## 三、争议情况
| 字段 | 值 |
|---|---|
| 争议类型 | 食品安全 |
| 争议发现日期 | 2026-09-25 |
| 已发生损失金额（元） | 200 |

## 五、诉求与时限
| 字段 | 值 |
|---|---|
| 是否主张不符合食品安全标准 | 是 |
""")
b1, m1 = cc.build_report(FOOD, BASE)
ck_true("S01 食品生成", b1 is not None, str(m1)[:80])
ck("S02 食品十倍保底", m1["惩罚性赔偿"], 1000.0)   # max(680, 600)=680 < 1000
ck("S03 食品合计", m1["诉求合计"], 1268.0)          # 68 + 1000 + 200
ck_true("S04 保底提示", "1000 元保底" in b1)
ck_true("S05 商务/食品分支", "食品安全" in b1)

# ---------------- 场景 B：合规齐全 -> 通过
OK = tmp("_tmp_ok.md", """## 一、消费者与经营者
| 字段 | 值 |
|---|---|
| 经营者名称 | 杭州某某家居有限公司 |
| 经营者实际经营地 | 浙江省杭州市西湖区文三路 100 号 |
| 是否有电商平台 | 无 |

## 二、交易情况
| 字段 | 值 |
|---|---|
| 商品或服务名称 | 实木餐桌 |
| 消费金额（元） | 1200 |
| 交易日期 | 2026-09-01 |
| 签收日期 | 2026-09-05 |
| 是否属于食品 | 否 |

## 三、争议情况
| 字段 | 值 |
|---|---|
| 争议类型 | 质量问题 |
| 争议发现日期 | 2026-09-10 |
| 是否已与商家协商 | 是 |
| 协商是否有书面记录 | 有 |
| 是否已向12315投诉 | 是 |
| 是否造成人身伤害 | 否 |
| 已发生损失金额（元） | 0 |

## 四、证据持有情况
| 字段 | 值 |
|---|---|
| 订单或合同凭证 | 有 |
| 支付凭证 | 有 |
| 发票凭证 | 有 |
| 商品照片或视频 | 有 |
| 快递外包装证据 | 有 |
| 聊天记录 | 有 |
| 通话录音 | 有 |
| 检测报告 | 有 |
| 快递单号与签收记录 | 有 |
| 宣传页面截图 | 不适用 |

## 五、诉求与时限
| 字段 | 值 |
|---|---|
| 主要诉求 | 修理更换 |
| 是否主张欺诈 | 否 |
| 是否主张不符合食品安全标准 | 不适用 |
| 是否已过七天无理由期 | 否 |
""")
b2, m2 = cc.build_report(OK, BASE)
ck_true("O01 合规生成", b2 is not None, str(m2)[:80])
ck("O02 结论=通过", m2["结论"], "通过")
ck("O03 无缺口", m2["证据缺口"], [])
ck("O04 无惩罚性赔偿", m2["惩罚性赔偿"], None)
ck("O05 合计=实付", m2["诉求合计"], 1200.0)
ck_true("O06 无平台不适用", "本步不适用" in b2)
ck_true("O07 未填不算通过提示", "未填的一律不算通过" in b2)

# ---------------- 场景 C：时效届满 -> 不通过
OLD = tmp("_tmp_old.md", """## 二、交易情况
| 字段 | 值 |
|---|---|
| 商品或服务名称 | 老式洗衣机 |
| 消费金额（元） | 800 |
| 交易日期 | 2020-01-10 |
| 签收日期 | 2020-01-15 |

## 三、争议情况
| 字段 | 值 |
|---|---|
| 争议类型 | 质量问题 |
| 争议发现日期 | 2020-02-01 |
| 是否已与商家协商 | 是 |
| 协商是否有书面记录 | 有 |
| 是否造成人身伤害 | 否 |
| 已发生损失金额（元） | 0 |

## 四、证据持有情况
| 字段 | 值 |
|---|---|
| 订单或合同凭证 | 有 |
| 支付凭证 | 有 |
| 发票凭证 | 有 |
| 商品照片或视频 | 有 |
| 快递外包装证据 | 有 |
| 聊天记录 | 有 |
| 通话录音 | 有 |
| 检测报告 | 有 |
| 快递单号与签收记录 | 有 |
| 宣传页面截图 | 有 |

## 五、诉求与时限
| 字段 | 值 |
|---|---|
| 是否主张欺诈 | 否 |
| 是否已自行发过书面催告 | 否 |
""")
b3, m3 = cc.build_report(OLD, BASE)
ck_true("T01 过期生成", b3 is not None, str(m3)[:80])
ck("T02 结论=不通过", m3["结论"], "不通过")
ck("T03 时效届满标记", m3["诉讼时效是否届满"], True)
ck_true("T04 时效届满提示", "诉讼时效**可能已届满**" in b3)
ck_true("T05 建议书面催告", "中断诉讼时效" in b3)

# ---------------- 空表与缺文件
r2 = cc.build_report(EMPTY, BASE)
ck_true("E01 空表 None", r2[0] is None)
ck_true("E02 空表提示", isinstance(r2[1], str) and "未解析到关键信息" in r2[1], str(r2[1])[:60])
r3 = cc.build_report(os.path.join(HERE, "不存在.md"), BASE)
ck_true("E03 缺文件不崩", r3[0] is None)
ck_true("E04 缺文件提示", "读不了文件" in str(r3[1]))

# ---------------- 缺金额 -> rc=2
NOAMT = tmp("_tmp_noamt.md", """## 三、争议情况
| 字段 | 值 |
|---|---|
| 争议类型 | 质量问题 |
""")
r4 = cc.build_report(NOAMT, BASE)
ck_true("E05 缺金额 None", r4[0] is None)
ck_true("E06 缺金额提示", "消费金额" in str(r4[1]), str(r4[1])[:60])

# ---------------- 子进程：退出码与 --json
env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"
p1 = subprocess.run([sys.executable, SCRIPT, SAMPLE, "--base", "2026-10-05", "--json"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=120, env=env)
ck("J01 json rc", p1.returncode, 0)
try:
    j = json.loads(p1.stdout)
    ck("J02 json 可解析", isinstance(j, dict), True)
    ck("J03 json 结论", j.get("结论"), "有风险")
    ck_true("J04 json 风险项", isinstance(j.get("风险项"), list) and len(j["风险项"]) >= 3)
    ck_true("J05 json 待办", isinstance(j.get("待办"), list) and len(j["待办"]) >= 5)
except Exception as e:
    ck("J02 json 可解析", False, True)
    LINES.append("   json err %s" % e)

p2 = subprocess.run([sys.executable, SCRIPT, EMPTY],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=120, env=env)
ck("J06 空表 rc=2", p2.returncode, 2)
ck_true("J07 空表有输出", len(p2.stdout) > 20, p2.stdout[:60])

for p in (COLON, FOOD, OK, OLD, NOAMT):
    try:
        os.remove(p)
    except Exception:
        pass

LINES.append("== TOTAL PASS=%d FAIL=%d ==" % (PASS, FAIL))
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(LINES) + "\n")
print("PASS=%d FAIL=%d" % (PASS, FAIL))
