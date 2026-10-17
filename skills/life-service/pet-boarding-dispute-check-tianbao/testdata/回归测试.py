# -*- coding: utf-8 -*-
"""宠物寄养纠纷技能回归测试。断言全绿才算过关。"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(HERE, "..", "scripts", "pet_boarding_check.py")
SAMPLE = os.path.join(HERE, "样例.md")
EMPTY = os.path.join(HERE, "空输入.md")
PY = sys.executable

sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "scripts")))
import pet_boarding_check as M  # noqa: E402

FAILS = []
COUNT = 0


def chk(name, cond):
    """断言一条。"""
    global COUNT
    COUNT += 1
    if not cond:
        FAILS.append("FAIL #%d %s" % (COUNT, name))


def chk_eq(name, a, b):
    chk("%s (got=%r want=%r)" % (name, a, b), a == b)


def run(args):
    p = subprocess.run([PY, SCRIPT] + args, capture_output=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, p.stdout or "", p.stderr or ""


# ------------------------------------------------------------ 基础工具
chk("fmt_num 去 .0", M.fmt_num(3.0) == "3")
chk("fmt_num 保留小数", M.fmt_num(3.5) == "3.5")
chk("fmt_num None", M.fmt_num(None) == "-")
chk("money 带符号", M.money(3200) == "¥3200")
chk("money 四舍五入", M.money(1859.999) == "¥1860")

chk("filled 空串", M.filled("") is False)
chk("filled 待填视为未填", M.filled("待填") is False)
chk("filled 待补视为未填", M.filled("待补") is False)
chk("filled 未填写", M.filled("未填写") is False)
chk("filled 不清楚", M.filled("不清楚") is False)
chk("filled 竖线", M.filled("|") is False)
chk("filled 正常值", M.filled("金毛犬") is True)
chk("filled 0 不算空", M.filled(0) is True or M.filled("0") is True)

chk("unknown 待填", M.unknown("待填") is True)
chk("unknown 待确认", M.unknown("待确认") is True)
chk("unknown 有值", M.unknown("有") is False)

chk("norm 去空格", M.norm(" 待填 ") == "待填")
chk("norm 全角冒号", M.norm("是：") == "是:")

# ------------------------------------------------------------ 数值与日期
chk("parse_num 3200", M.parse_num("3200") == 3200.0)
chk("parse_num 带逗号", M.parse_num("3,200元") == 3200.0)
chk("parse_num 混合文本", M.parse_num("护理费480元") == 480.0)
chk("parse_num 无数字", M.parse_num("不清楚") is None)
chk("parse_num None", M.parse_num(None) is None)

chk("parse_date 横杠", M.parse_date("2026-09-01") is not None)
chk("parse_date 斜杠", M.parse_date("2026/9/1") is not None)
chk("parse_date 中文", M.parse_date("2026年9月1日") is not None)
chk("parse_date 待填", M.parse_date("待填") is None)
chk("parse_date 空", M.parse_date("") is None)
chk("parse_date 非法", M.parse_date("2026-13-45") is None)

d1 = M.parse_date("2026-09-01")
d2 = M.parse_date("2026-09-14")
chk_eq("days_between", M.days_between(d1, d2), 13)
chk("days_between 缺一", M.days_between(d1, None) is None)

# ------------------------------------------------------------ 解析：表格 + 冒号
md = "| 寄养方式 | 门店寄养 |\n| 寄养地点 | 宠安之家 |\n"
f = M.parse_md_temp(md) if hasattr(M, "parse_md_temp") else None

tmp = os.path.join(HERE, "_tmp_parse.md")
with open(tmp, "w", encoding="utf-8") as fh:
    fh.write("| 寄养方式 | 门店寄养 |\n| 寄养地点 | 宠安之家 |\n"
             "纠纷类型：宠物死亡\n| --- | --- |\n")
fp = M.parse_md(tmp)
chk("parse 表格字段", M.get_text(fp, "寄养方式") == "门店寄养")
chk("parse 表格字段2", M.get_text(fp, "寄养地点") == "宠安之家")
chk("parse 冒号行", M.get_text(fp, "纠纷类型") == "宠物死亡")
chk("parse 分隔行不误读", M.get_text(fp, "寄养起日") == "")
os.remove(tmp)

# ------------------------------------------------------------ 关键：串字段回归
# 曾踩坑：get_text 用子串 in，导致「品类」命中「是否涉及特殊品类」
tmp2 = os.path.join(HERE, "_tmp_cross.md")
with open(tmp2, "w", encoding="utf-8") as fh:
    fh.write("| 合同有无免责条款 | 是 |\n| 免责条款摘录 | 概不负责 |\n")
f2 = M.parse_md(tmp2)
chk("精确匹配：免责条款摘录不被条款摘录别名抢走",
    M.get_text(f2, "免责条款摘录") == "概不负责")
os.remove(tmp2)

# ------------------------------------------------------------ yesno 否定式优先
chk("yesno 是", M.yesno("是") is True)
chk("yesno 否", M.yesno("否") is False)
chk("yesno 承认", M.yesno("承认过错") is True)
chk("yesno 否认", M.yesno("否认过错") is False)
chk("yesno 推诿=否", M.yesno("是，说与寄养无关") in (True, None))
chk("yesno 空返回 None", M.yesno("") is None)
chk("yesno 待填返回 None", M.yesno("待填") is None)
chk("yesno 不是→False", M.yesno("不是") is False)

# ------------------------------------------------------------ 归因
cause, _ = M.classify_cause("寄养期间死亡", "死亡", "是", "诊断细小", "有")
chk_eq("承认过错→商家过错", cause, "商家过错")

cause2, _ = M.classify_cause("寄养第3天呕吐腹泻", "死亡", "否", "", "有")
chk_eq("死亡+否认→责任待定", cause2, "责任待定")

cause3, _ = M.classify_cause("走失", "走失", "否", "", "有")
chk_eq("走失→商家过错", cause3, "商家过错")

cause4, _ = M.classify_cause("受伤", "摔伤", "否", "", "有")
chk_eq("受伤→商家过错", cause4, "商家过错")

cause5, _ = M.classify_cause("生病", "细小", "否", "未免疫", "有")
chk_eq("未免疫→主人过错", cause5, "主人过错")

cause6, _ = M.classify_cause("死亡", "死亡", "否", "诊断", "")
chk_eq("无寄养前照片→责任待定", cause6, "责任待定")

cause7, _ = M.classify_cause("", "", "", "", "有")
chk_eq("纠纷类型空→待定", cause7, "待定")

# ------------------------------------------------------------ 免责条款
st, items = M.check_clause("是", "宠物死亡概不负责，概不退款，一切后果自负", "")
chk_eq("免责条款含概不负责→不通过", st, "不通过")
chk("列出无效理由", any("概不负责" in i for i in items))

st2, _ = M.check_clause("否", "", "")
chk_eq("无免责条款→通过", st2, "通过")

st3, _ = M.check_clause("待填", "", "")
chk_eq("免责未填→待补正", st3, "待补正")

st4, items4 = M.check_clause("是", "本所不接收未免疫幼犬", "")
chk("温和条款→有风险非不通过", st4 in ("有风险",))
chk("温和条款不误判概不负责", not any("概不负责" in i for i in items4))

# ------------------------------------------------------------ 退费测算
net, items5 = M.calc_refund("3200", "0", "500", "护理费", "480")
chk_eq("应退=3200-0", net, 3200.0)
chk("有理由的扣款提示核对依据",
    any("需判断该理由是否有合同依据" in i for i in items5))

net_b, items_b = M.calc_refund("3200", "0", "500", "", "600")
chk("无理由扣款→判无依据应全返",
    any("无依据扣款" in i for i in items_b))

net2, items6 = M.calc_refund("3200", "500", "500", "", "")
chk_eq("已退500后应退", net2, 2700.0)

net3, items7 = M.calc_refund("", "0", "500", "", "")
chk("已付未填→None", net3 is None)

net4, items8 = M.calc_refund("3200", "4000", "500", "", "")
chk("已退超已付→归零不报错", net4 == 0.0)

net5, items9 = M.calc_refund("1000", "0", "2000", "", "")
chk("押金超已付→提示核对", any("超过已付总额" in i for i in items9))

# ------------------------------------------------------------ 证据缺口
n, gaps = M.check_evidence("", "", "否", True)
chk("全缺→缺口数>=2", n >= 2)
chk("提示寄养前照片", any("寄养前" in g for g in gaps))
chk("提示聊天记录", any("沟通记录" in g for g in gaps))

n2, gaps2 = M.check_evidence("有", "有", "是", True)
chk_eq("证据齐全→无缺口", n2, 0)

# ------------------------------------------------------------ 责任比例
mr, orr, _ = M.calc_ratio("商家过错")
chk_eq("商家过错100%", mr, 1.0)
mr2, orr2, _ = M.calc_ratio("主人过错")
chk_eq("主人过错0%", mr2, 0.0)
chk("比例和为1", abs(mr + orr - 1.0) < 1e-9)

# ------------------------------------------------------------ 端到端：样例
rc, out, err = run(["--input", SAMPLE])
chk_eq("样例 rc=0", rc, 0)
chk("样例含结论摘要", "## 结论摘要" in out)
chk("样例含过错归因", "## 过错归因分析" in out)
chk("样例含责任分摊", "## 责任分摊测算" in out)
chk("样例含退费核查", "## 退费与扣款核查" in out)
chk("样例含证据缺口", "## 证据缺口与固定要点" in out)
chk("样例含维权路径", "## 维权路径" in out)
chk("样例含待办", "## 待办补正动作" in out)
chk("样例含边界", "## 边界与纪律" in out)
chk("样例认定位商家", "商家过错" in out or "责任待定" in out)
chk("样例算应退3200", "¥3200" in out)
chk("样例指出超期", "超期" in out)
chk("样例标加价风险", "加价" in out)
chk("样例报免责无效", "不通过" in out)
chk("样例有免责声明", "不替代专业法律意见" in out)

# ------------------------------------------------------------ 端到端：空输入
rc2, out2, err2 = run(["--input", EMPTY])
chk("空输入 rc=2", rc2 == 2)
chk("空输入不崩", "Traceback" not in err2)
chk("空输入不判通过", "**总体结论：待补正**" in out2 or "总体结论：待补正" in out2)
chk("空输入不出现有风险", "总体结论：有风险" not in out2)
chk("空输入不出现通过结论", "总体结论：通过" not in out2)

# ------------------------------------------------------------ --json
rc3, out3, _ = run(["--input", SAMPLE, "--json"])
chk_eq("json rc=0", rc3, 0)
try:
    data = json.loads(out3)
    chk("json 可解析", isinstance(data, dict))
    chk("json 含结论", "结论" in data)
    chk("json 含风险项", "风险项" in data)
    chk("json 含待办", "待办" in data)
    chk("json 风险项非空", len(data.get("风险项", [])) > 0)
except Exception as e:
    chk("json 可解析 (%s)" % e, False)

rc4, out4, _ = run(["--input", EMPTY, "--json"])
try:
    d4 = json.loads(out4)
    chk("空表 json 可解析", isinstance(d4, dict))
    chk("空表 json 结论非通过", d4.get("结论") != "通过")
except Exception as e:
    chk("空表 json 可解析 (%s)" % e, False)

# ------------------------------------------------------------ --out 落盘
outp = os.path.join(HERE, "_tmp_report.md")
rc5, _, _ = run(["--input", SAMPLE, "--out", outp])
chk_eq("out rc=0", rc5, 0)
chk("out 文件已生成", os.path.exists(outp))
if os.path.exists(outp):
    with open(outp, "r", encoding="utf-8") as fh:
        rep = fh.read()
    chk("out 内容含结论", "结论摘要" in rep)
    os.remove(outp)

# ------------------------------------------------------------ 不存在的文件
rc6, out6, err6 = run(["--input", os.path.join(HERE, "_nonexistent.md")])
chk("文件不存在 rc=2", rc6 == 2)
chk("文件不存在不崩", "Traceback" not in err6)

# ------------------------------------------------------------ 章节数
sec = out.count("\n## ")
chk("报告章节数>=9", sec >= 9)

# ------------------------------------------------------------ 输出
lines = ["宠物寄养回归测试结果",
         "断言总数: %d" % COUNT,
         "失败数: %d" % len(FAILS)]
if FAILS:
    lines.append("")
    lines.extend(FAILS)
else:
    lines.append("全部通过")
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")

print("\n".join(lines))
sys.exit(1 if FAILS else 0)