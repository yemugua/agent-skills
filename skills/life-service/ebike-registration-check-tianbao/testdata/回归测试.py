# -*- coding: utf-8 -*-
"""电动车上牌资格核查 回归测试（自写 utf-8 结果文件）"""
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ebike_check as ec  # noqa: E402

SAMPLE = os.path.join(HERE, "样例.md")
EMPTY = os.path.join(HERE, "空输入.md")
BASE = dt.date(2026, 10, 5)
SCRIPT = os.path.join(ROOT, "scripts", "ebike_check.py")

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
    p = os.path.join(HERE, "_tmp_%s.md" % name)
    with open(p, "w", encoding="utf-8") as f:
        f.write("| 字段 | 值 |\n|---|---|\n")
        for k, v in pairs:
            f.write("| %s | %s |\n" % (k, v))
    return p


with open(SAMPLE, encoding="utf-8") as f:
    text = f.read()
with open(EMPTY, encoding="utf-8") as f:
    etext = f.read()

# ---------------- 基础解析
ck("P01 norm 去空格", ec.norm(" 杭 州市 "), "杭州市")
ck("P02 norm 去括号", ec.norm("车架号（车辆识别代号）"), "车架号(车辆识别代号)")
ck("P03 filled 待填", ec.filled("【待填】"), False)
ck("P04 filled 有/无", ec.filled("有/无"), False)
ck("P05 filled 有", ec.filled("有"), True)
ck("P06 filled 空", ec.filled(""), False)
ck("P07 表头不算值", "值" in ec.build_kv("| 字段 | 值 |\n|---|---|\n"), False)
ck("P08 样例字段数", len(ec.build_kv(text)) > 20, True)
ck("P09 冒号行解析", ec.get_text(ec.build_kv("常住城市：成都市"), ["常住城市"]), "成都市")

# ---------------- 字段解析
kv = ec.build_kv(text)
ck("F01 城市", ec.get_text(kv, ["常住城市", "所在城市", "城市"]), "杭州市")
ck("F02 车速", ec.get_text(kv, ["最高设计车速", "最高车速", "车速"]), "32")
ck("F03 电压", ec.get_text(kv, ["蓄电池标称电压", "电池电压", "标称电压"]), "60")
ck("F04 功率", ec.get_text(kv, ["电动机额定连续输出功率", "电机功率", "额定连续输出功率"]), "400")
ck("F05 质量", ec.get_text(kv, ["整车质量", "装配完整的整车质量"]), "61")
ck("F06 脚踏", ec.get_text(kv, ["是否有脚踏骑行能力", "脚踏", "有无脚踏"]), "有")
ck("F07 空表车速", ec.get_text(ec.build_kv(etext), ["最高设计车速", "车速"]), "")
ck("F08 空表脚踏是占位", ec.filled(ec.get_text(ec.build_kv(etext), ["是否有脚踏骑行能力"])), False)
ck("F09 最长别名优先", ec.get_text(
    ec.build_kv("| 最高车速 | 18 |\n| 最高设计车速 | 32 |\n"), ["最高设计车速", "最高车速"]), "32")
ck("F10 发票", ec.get_text(kv, ["购车发票", "发票"]), "无（只剩一张手写收据）")

# ---------------- 数值与格式
ck("N01 parse_num 整数", ec.parse_num("32"), 32.0)
ck("N02 parse_num 小数", ec.parse_num("48.5"), 48.5)
ck("N03 parse_num 空", ec.parse_num(""), None)
ck("N04 parse_num 带单位", ec.parse_num("55 kg"), 55.0)
ck("N05 fmt_num 去点零", ec.fmt_num(32.0), "32")
ck("N06 fmt_num 一位", ec.fmt_num(32.5), "32.5")
ck("N07 fmt_num None", ec.fmt_num(None), "—")
ck("N08 fmt_money", ec.fmt_money(10.0), "¥10")
ck("N09 parse_date", ec.parse_date("2023-05-18"), dt.date(2023, 5, 18))
ck("N10 parse_date 中文", ec.parse_date("2023年5月18日"), dt.date(2023, 5, 18))
ck("N11 parse_date 空", ec.parse_date(""), None)

# ---------------- 车种定性
fmotor = mk("fmotor", [
    ("是否有脚踏骑行能力", "有"), ("最高设计车速", "32"),
    ("整车质量", "61"), ("电动机额定连续输出功率", "400"),
    ("蓄电池标称电压", "60"), ("车辆类型", "电动轻便摩托车"),
])
okm = mk("okm", [
    ("是否有脚踏骑行能力", "有"), ("最高设计车速", "25"),
    ("整车质量", "52"), ("电动机额定连续输出功率", "350"),
    ("蓄电池标称电压", "48"),
])
q1, b1, r1, fail1 = ec.classify({"has_pedal": "有", "speed": "32", "weight": "61",
                                 "power": "400", "voltage": "60", "vtype": "电动轻便摩托车"})
ck("C01 超标定性=机动车", q1, "机动车（电动摩托车/电动轻便摩托车）")
ck_true("C02 超标列出不符合项", "最高设计车速" in b1 and "蓄电池标称电压" in b1, b1)
ck("C03 超标项数", len(fail1), 3)
q2, b2, r2, fail2 = ec.classify({"has_pedal": "有", "speed": "25", "weight": "52",
                                 "power": "350", "voltage": "48", "vtype": "电动自行车"})
ck("C04 达标定性=非机动车", q2, "非机动车（电动自行车）")
ck("C05 达标无不符合项", len(fail2), 0)
ck_true("C06 达标依据含 GB 17761", "GB 17761" in b2, b2)
q3, b3, r3, fail3 = ec.classify({"has_pedal": "无", "speed": "25", "weight": "52",
                                 "power": "350", "voltage": "48", "vtype": ""})
ck("C07 无脚踏=超标", q3, "机动车（电动摩托车/电动轻便摩托车）")
ck_true("C08 无脚踏被抓", "脚踏" in b3, b3)
q4, b4, r4, fail4 = ec.classify({"has_pedal": "有", "speed": "", "weight": "52",
                                 "power": "350", "voltage": "48", "vtype": ""})
ck("C09 缺车速=不判定超标", q4, "非机动车（电动自行车）")
ck_true("C10 缺车速列待补正", "待补正" in [x[3] for x in r4], str(r4))

# ---------------- 报告生成
b00, m00 = ec.build_report(SAMPLE, BASE)
ck_true("R01 生成成功", b00 is not None, str(m00))
ck_true("R02 九段", b00.count("## ") >= 8, str(b00.count("## ")))
ck_true("R03 结论摘要", "## 一、结论摘要" in b00)
ck_true("R04 车种定性段", "## 二、车种定性" in b00)
ck_true("R05 材料段", "## 三、能不能上牌" in b00)
ck_true("R06 卡点段", "## 四、卡点分支" in b00)
ck_true("R07 过渡期段", "## 五、超标车与过渡期" in b00)
ck_true("R08 资质段", "## 六、资质、保险与号牌状态" in b00)
ck_true("R09 待办段", "## 八、待办补正动作" in b00)
ck_true("R10 纪律段", "## 九、边界与纪律" in b00)
ck_true("R11 定性=机动车", "机动车" in b00)
ck_true("R12 改装被抓", "改装车" in b00 and "恢复原状" in b00)
ck_true("R13 发票卡点被抓", "不要买代开发票" in b00)
ck_true("R14 无证驾驶提示", "无证驾驶" in b00)
ck_true("R15 交强险提示", "交强险" in b00)
ck_true("R16 过渡期查询入口", "当地交警微信公众号" in b00)
ck_true("R17 12123 提示", "12123" in b00)
ck_true("R18 结论态四选一", m00.get("结论") in ("通过", "有风险", "不通过", "待补正"), str(m00.get("结论")))
ck_true("R19 风险项非空", len(m00.get("风险项", [])) >= 1, str(m00.get("风险项")))
ck_true("R20 待办非空", len(m00.get("待办", [])) >= 5, str(len(m00.get("待办", []))))
ck_true("R21 无待填泄漏", "【待填" not in b00)
ck_true("R22 无乱码", "\ufffd" not in b00)
bad = [ln for ln in b00.splitlines() if ln.count("|") > 8]
ck_true("R23 表格不裂", not bad, str(bad[:2]))
ck_true("R24 城市写入", "杭州市" in b00)
ck_true("R25 复议诉讼提示", "行政复议" in b00)

# 非机动车路径
bn, mn = ec.build_report(okm, BASE)
ck_true("R26 达标车可生成", bn is not None, str(mn))
ck_true("R27 达标车定性=非机动车", "非机动车" in bn)
ck_true("R28 达标车不出现无证驾驶提示", "无证驾驶" not in bn)

# 过渡期分支
tr1 = mk("tr1", [("最高设计车速", "35"), ("当地是否对超标车设过渡期（临时号牌）", "是"),
                 ("过渡期截止日", "2026-09-01")])
btr, mtr = ec.build_report(tr1, BASE)
ck_true("T01 过渡期过期被抓", "已过期" in btr, str(mtr))
ck_true("T02 过渡期过期计入风险项", any("过渡期" in str(x) for x in mtr.get("风险项", [])),
        str(mtr.get("风险项")))
tr2 = mk("tr2", [("最高设计车速", "35"), ("当地是否对超标车设过渡期（临时号牌）", "是"),
                 ("过渡期截止日", "2026-12-31")])
btr2, mtr2 = ec.build_report(tr2, BASE)
ck_true("T03 过渡期未到期", "还剩" in btr2)
tr3 = mk("tr3", [("最高设计车速", "35"), ("当地是否对超标车设过渡期（临时号牌）", "不清楚")])
btr3, mtr3 = ec.build_report(tr3, BASE)
ck_true("T04 不清楚转待补正", "待补正" in btr3)
tr4 = mk("tr4", [("最高设计车速", "35"), ("当地是否对超标车设过渡期（临时号牌）", "否")])
btr4, mtr4 = ec.build_report(tr4, BASE)
ck_true("T05 无过渡期提示", "直接按机动车管理" in btr4)

# 车架号与铭牌
fk = mk("fk", [("最高设计车速", "25"), ("整车质量", "52"), ("电动机额定连续输出功率", "350"),
               ("蓄电池标称电压", "48"), ("车架号是否清晰可辨", "磨损")])
bk, mk_ = ec.build_report(fk, BASE)
ck_true("U01 车架号磨损被抓", "车架号" in bk and "不予登记" in bk)
fk2 = mk("fk2", [("最高设计车速", "25"), ("整车质量", "52"), ("电动机额定连续输出功率", "350"),
                 ("蓄电池标称电压", "48"), ("车架号是否清晰可辨", "清晰"),
                 ("铭牌是否完整", "脱落")])
bk2, _ = ec.build_report(fk2, BASE)
ck_true("U02 铭牌脱落被抓", "铭牌脱落或缺失" in bk2)

# 二手车与合格证
uc = mk("uc", [("最高设计车速", "25"), ("整车质量", "52"), ("电动机额定连续输出功率", "350"),
               ("蓄电池标称电压", "48"), ("是否为二手车", "是"),
               ("二手车转让手续", "未填")])
buc, _ = ec.build_report(uc, BASE)
ck_true("V01 二手车被抓", "原车主失联" in buc)
ck_true("V02 二手车提示查状态", "抵押" in buc)
cm = mk("cm", [("最高设计车速", "25"), ("整车质量", "52"), ("电动机额定连续输出功率", "350"),
               ("蓄电池标称电压", "48"), ("合格证型号与实车是否一致", "不一致")])
bcm, _ = ec.build_report(cm, BASE)
ck_true("V03 合格证不符被抓", "不要拿去上牌" in bcm)

# 改装
mg = mk("mg", [("最高设计车速", "25"), ("整车质量", "52"), ("电动机额定连续输出功率", "350"),
               ("蓄电池标称电压", "48"), ("是否改装过", "是"), ("改装项目", "加装遮阳伞")])
bmg, _ = ec.build_report(mg, BASE)
ck_true("W01 改装被抓", "加装遮阳伞" in bmg)
ck_true("W02 改装提示恢复原状", "恢复原状" in bmg)
mg2 = mk("mg2", [("最高设计车速", "25"), ("整车质量", "52"), ("电动机额定连续输出功率", "350"),
                 ("蓄电池标称电压", "48"), ("是否改装过", "否")])
bmg2, _ = ec.build_report(mg2, BASE)
ck_true("W03 未改装不误报", "改装车" not in bmg2)

# 号牌状态
pl = mk("pl", [("最高设计车速", "25"), ("整车质量", "52"), ("电动机额定连续输出功率", "350"),
               ("蓄电池标称电压", "48"), ("号牌是否已办", "已上临时号牌")])
bpl, _ = ec.build_report(pl, BASE)
ck_true("X01 临时牌被抓", "过渡期临时号牌" in bpl)

# ---------------- 空表与缺文件
rr = ec.build_report(EMPTY, BASE)
ck_true("Y01 空表返回None", rr[0] is None, str(rr[0])[:60])
ck_true("Y02 空表有提示", isinstance(rr[1], str) and "未解析" in rr[1], str(rr[1])[:60])
rr2 = ec.build_report(os.path.join(HERE, "不存在的.md"), BASE)
ck_true("Y03 缺文件不崩", rr2[0] is None)

# ---------------- 子进程：退出码与 json
import subprocess  # noqa: E402

p1 = subprocess.run([sys.executable, SCRIPT, EMPTY, "--base", "2026-10-05"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
ck("Z01 空输入退出码", p1.returncode, 2)
ck_true("Z02 空输入有提示", "未解析到关键信息" in p1.stdout, p1.stdout[:80])
p2 = subprocess.run([sys.executable, SCRIPT, SAMPLE, "--base", "2026-10-05", "--json"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
ck("Z03 json 退出码", p2.returncode, 0)
try:
    jj = json.loads(p2.stdout)
    ck_true("Z04 json 是对象", isinstance(jj, dict), type(jj).__name__)
    ck_true("Z05 json 含结论", "结论" in jj)
    ck_true("Z06 json 含风险项", len(jj.get("风险项", [])) >= 1, str(jj.get("风险项")))
    ck_true("Z07 json 含待办", len(jj.get("待办", [])) >= 5, str(len(jj.get("待办", []))))
    ck_true("Z08 json 含定性", "车种定性" in jj)
except Exception as e:  # noqa: BLE001
    ck_true("Z04 json 可解析", False, str(e))
p3 = subprocess.run([sys.executable, SCRIPT, SAMPLE, "--base", "2026-10-05"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
ck("Z09 样例退出码", p3.returncode, 0)
ck_true("Z10 样例多段", p3.stdout.count("## ") >= 8, str(p3.stdout.count("## ")))

LINES.append("== TOTAL PASS=%d FAIL=%d ==" % (PASS, FAIL))
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(LINES) + "\n")
print("\n".join(LINES[-3:]))
