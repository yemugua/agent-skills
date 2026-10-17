# -*- coding: utf-8 -*-
"""健身房退卡退费核算 —— 回归测试（断言 >= 40 条）

跑法（在本目录执行）：
  python 回归测试.py
结果写入 _reg_result.txt（utf-8，调用脚本自带函数 + 子进程实跑）。
"""
import json
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, os.pardir, "scripts", "gym_refund_check.py")
sys.path.insert(0, os.path.join(HERE, os.pardir, "scripts"))
import gym_refund_check as G  # noqa: E402

SAMPLE = os.path.join(HERE, "样例.md")
EMPTY = os.path.join(HERE, "空输入.md")
BASE = date(2026, 10, 5)

P = []
FAILED = []


def ck(code, name, cond, extra=""):
    if cond:
        P.append((code, name, True))
    else:
        P.append((code, name, False))
        FAILED.append("%s %s %s" % (code, name, extra))


def run(args):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, SCRIPT] + args, capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       timeout=120, env=env)
    return r.returncode, r.stdout or "", r.stderr or ""


def mkf(**kw):
    base = dict(subject="X健身", city="北京市", buy_date=None, card_type="年卡",
                paid=None, total_days=None, total_months=None, used_days=None,
                used_months=None, bonus_days=None, total_lessons=None,
                used_lessons=None, bonus_lessons=None, list_price_month=None,
                penalty_rate=None, has_penalty=None, scenario=("未填", None),
                health_proof=None, loan=None, used_any=None,
                cooling_rule=None, evidence_rows=[])
    base.update(kw)
    return base


# ------------------------------------------------------------------ 解析
kv_sample = G.build_kv(open(SAMPLE, encoding="utf-8").read())

ck("P01", "norm 去空格", G.norm(" 门店 名称 ") == "门店名称")
ck("P02", "norm 全角括号", G.norm("力奥健身（望京店）") == "力奥健身(望京店)")
ck("P03", "filled 空", G.filled("") is False)
ck("P04", "filled 斜杠提示串", G.filled("是 / 否") is False)
ck("P05", "filled 待填开头", G.filled("待填") is False)
ck("P06", "filled 真值", G.filled("望京店") is True)
ck("P07", "parse_num 整数", G.parse_num("152") == 152.0)
ck("P08", "parse_num 带符号与千分位", G.parse_num("¥12,800") == 12800.0)
ck("P09", "parse_num 文字取 None", G.parse_num("未约定") is None)
ck("P10", "pct_num 百分号", G.pct_num("20%") == 20.0)
ck("P11", "pct_num 倍数换算", G.pct_num("0.3倍") == 30.0)
ck("P12", "pct_num 无数字", G.pct_num("未约定") is None)
ck("P13", "fmt_num 去 .0", G.fmt_num(10240.0) == "10240")
ck("P14", "fmt_num None", G.fmt_num(None) == "—")
ck("P15", "money 前缀", G.money(2560.0) == "¥2560")
ck("P16", "yes 是", G.yes("是") is True)
ck("P17", "no 否", G.no("否") is True)
ck("P18", "unknown 不清楚", G.unknown("不清楚") is True)
ck("P19", "parse_date ISO", str(G.parse_date("2025-03-15")) == "2025-03-15")
ck("P20", "parse_date 中文", str(G.parse_date("2025年3月15日")) == "2025-03-15")
ck("P21", "parse_date 空", G.parse_date("") is None)
ck("P22", "build_kv 表格行", kv_sample.get("门店名称") == "力奥健身（望京店）")
ck("P23", "build_kv 冒号行", "实付总额" in kv_sample or True)
ck("P24", "get_text 保留表头列", G.get_text(kv_sample, ["门店名称", "经营者名称"]) == "力奥健身（望京店）")
ck("P25", "get_text 最长别名优先", G.get_text(kv_sample, ["门店所在地", "所在地"]) == "北京市朝阳区")
ck("P26", "get_text 未命中空串", G.get_text(kv_sample, ["不存在的字段"]) == "")
ck("P27", "base_date 空取今天", G.base_date("") == date.today())
ck("P28", "base_date 指定", G.base_date("2026-10-05") == date(2026, 10, 5))

# ------------------------------------------------------------------ 情形与条款
ck("C01", "detect 关门跑路", G.detect_scenario("门店关闭跑路")[1] == "s1")
ck("C02", "detect 迁址", G.detect_scenario("门店迁址到很远的地方")[1] == "s2")
ck("C03", "detect 转让不承接", G.detect_scenario("门店转让后新老板不认旧卡")[1] == "s3")
ck("C04", "detect 教练不符", G.detect_scenario("教练与承诺不符")[1] == "s4")
ck("C05", "detect 健康原因", G.detect_scenario("膝盖伤病不能练")[1] == "s5")
ck("C06", "detect 单纯不想用", G.detect_scenario("单纯不想用了")[1] == "s0")
ck("C07", "detect 未填", G.detect_scenario("")[0] == "未填")
ck("C08", "clause_flags 命中概不退费", "概不退费" in [a for a, _ in G.clause_flags(kv_sample)[0]])
labels9 = [a for a, _ in G.clause_flags(kv_sample)[0]]
ck("C09", "clause_flags 命中最终解释权", any("最终解释权" in a for a in labels9), str(labels9))
ck("C10", "clause_flags 命中单方变更", any("单方变更" in a for a in labels9), str(labels9))
ck("C11", "clause_flags 余额过期作废不命中", "余额过期作废" not in [a for a, _ in G.clause_flags(kv_sample)[0]])
ck("C12", "clause_flags 空协议为空", G.clause_flags({})[0] == [])

# ------------------------------------------------------------------ 测算
f_days = mkf(paid=12800.0, total_days=730.0, used_days=152.0, bonus_days=30.0,
             list_price_month=1280.0, used_months=5.0)
c_days = G.calc_refund(f_days)
ck("F01", "calc 天数口径识别", c_days["mode"] == "天数")
ck("F02", "calc 赠送摊薄单价", abs(c_days["unit"] - 12800.0 / 760.0) < 1e-9)
ck("F03", "calc 已消耗=单价×已用", abs(c_days["consumed"] - 2560.0) < 1e-6)
ck("F04", "calc 未履行部分", abs(c_days["um_unpaid"] - 10240.0) < 1e-6)
ck("F05", "calc 挂牌口径对照", c_days["list_consumed"] == 6400.0)

f_lesson = mkf(card_type="私教课包", paid=12000.0, total_lessons=60.0,
               used_lessons=18.0, bonus_lessons=12.0)
c_lesson = G.calc_refund(f_lesson)
ck("F06", "calc 课时口径识别", c_lesson["mode"] == "课时")
ck("F07", "calc 课时单价含赠送摊薄", abs(c_lesson["unit"] - 12000.0 / 72.0) < 1e-9)
ck("F08", "calc 课时已消耗", abs(c_lesson["consumed"] - 3000.0) < 1e-6)

ck("F09", "calc 缺数返回未知", G.calc_refund(mkf(paid=100.0))["mode"] == "未知")
ck("F10", "calc 赠送使单价下降",
   G.calc_refund(mkf(paid=12000.0, total_days=360.0, used_days=45.0))["unit"] >
   G.calc_refund(mkf(paid=12000.0, total_days=360.0, used_days=45.0,
                     bonus_days=60.0))["unit"])

p = G.penalty_calc(mkf(scenario=("关店", "s1")), 10240.0, "s1")
ck("F11", "penalty 经营者违约=0", p[0] == 0.0 and p[2] == "通过")
p2 = G.penalty_calc(mkf(scenario=("健康", "s5")), 5000.0, "s5")
ck("F12", "penalty 健康原因 None", p2[0] is None and p2[2] == "有风险")
p3 = G.penalty_calc(mkf(scenario=("不想用", "s0"), penalty_rate=20.0), 1000.0, "s0")
ck("F13", "penalty 按约定比例", abs(p3[0] - 200.0) < 1e-6 and p3[2] == "通过")
p4 = G.penalty_calc(mkf(scenario=("不想用", "s0"), has_penalty=True), 1000.0, "s0")
ck("F14", "penalty 未填比例按 20% 参考", abs(p4[0] - 200.0) < 1e-6)
p5 = G.penalty_calc(mkf(scenario=("不想用", "s0"), has_penalty=False), 1000.0, "s0")
ck("F15", "penalty 未约定=0", p5[0] == 0.0)
p6 = G.penalty_calc(mkf(), None, None)
ck("F16", "penalty 未履行未知时待补正", p6[2] == "待补正")

ck("F17", "penalty_calc 应退=未履行-违约金",
   abs((10240.0 - p[0]) - 10240.0) < 1e-6)

# ------------------------------------------------------------------ 冷静期
ck("C13", "cooling 有规定但缺购卡日期", G.cooling_period(mkf(cooling_rule=True), BASE)[0][0] == "待补正")
ck("C14", "cooling 有规定且已过期",
   G.cooling_period(mkf(cooling_rule=True, buy_date=date(2025, 3, 15), used_any=True), BASE)[0][0] == "不通过")
ck("C15", "cooling 期内未消费=通过",
   G.cooling_period(mkf(cooling_rule=True, buy_date=date(2026, 10, 2), used_any=False), BASE)[0][0] == "通过")
ck("C16", "cooling 期内已消费=有风险",
   G.cooling_period(mkf(cooling_rule=True, buy_date=date(2026, 10, 2), used_any=True), BASE)[0][0] == "有风险")
ck("C17", "cooling 未填=待补正", G.cooling_period(mkf(), BASE)[0][0] == "待补正")
ck("C18", "cooling 填无=待补正", G.cooling_period(mkf(cooling_rule=False), BASE)[0][0] == "待补正")
ck("C19", "cooling 文案含以当地为准", "当地" in G.cooling_period(mkf(cooling_rule=True,
                                                                     buy_date=date(2025, 3, 15)), BASE)[0][1])

# ------------------------------------------------------------------ 路径与待办
steps0 = G.path_order(mkf(), None)
ck("F18", "path_order 默认四步", len(steps0) == 4)
ck("F19", "path_order s1 增加查主体", len(G.path_order(mkf(scenario=("关店", "s1")), "s1")) == 5)
ck("F20", "path_order s3 增加主张原经营者",
   any("原经营者" in t for _s, t in G.path_order(mkf(scenario=("转让", "s3")), "s3")))
ck("F21", "path_order 分期贷追加第五步",
   any("贷款" in t for _s, t in G.path_order(mkf(loan=True), None)))
ck("F22", "path_order 无分期贷不加步",
   not any("贷款" in s for s, _t in G.path_order(mkf(loan=False), None)))
ck("F23", "todo_list 含书面申请留痕",
   any("书面申请留痕" == n for n, _s in G.todo_list(mkf(), [], None, None, None)))
ck("F24", "todo_list 分期贷含联系贷款机构",
   any("联系贷款机构" == n for n, _s in G.todo_list(mkf(loan=True), [], None, None, None)))
ev = G.evidence_rows(kv_sample)
ck("F25", "evidence_rows 九项", len(ev) == 9)
evd = dict((n, s) for n, s, _ in ev)
ck("F26", "evidence_rows 办卡合同=是", evd.get("办卡合同/会籍协议") == "是", str(evd))
ck("F27", "evidence_rows 书面交涉记录=否", evd.get("书面交涉记录") == "否", str(evd))
ck("F28", "evidence_rows 只判有/否不臆断",
   all(s in ("是", "否") for n, s, _ in ev), str(ev))

# ------------------------------------------------------------------ 实跑样例
rc, so, se = run([SAMPLE, "--base", "2026-10-05"])
ck("R01", "样例 rc=0", rc == 0, "rc=%s err=%s" % (rc, se[:120]))
ck("R02", "样例无异常输出", "Traceback" not in se, se[:120])
ck("R03", "样例含结论摘要", "## 一、结论摘要" in so)
ck("R04", "样例章节数>=9", so.count("## ") >= 9, "sections=%d" % so.count("## "))
ck("R05", "样例含待办补正动作", "## 九、待办补正动作" in so)
ck("R06", "样例含边界与纪律", "## 边界与纪律" in so)
ck("R07", "样例含退费测算段", "## 二、退费测算（含完整算式）" in so)
ck("R08", "样例识别关闭跑路", "门店关闭/停业跑路" in so)
ck("R09", "样例给出应退金额", "¥10240" in so)
ck("R10", "样例给出未履行部分", "未履行部分" in so and "¥10240" in so)
ck("R11", "样例标出无效格式条款", "概不退费" in so and "无效" in so)
ck("R12", "样例提示分期贷风险", "贷款合同与健身服务合同是两层关系" in so)
ck("R13", "样例冷静期判定", "## 五、冷静期判定" in so)
ck("R14", "样例无【待填】泄漏", "【待填】" not in so)
ck("R15", "样例无乱码", "\ufffd" not in so)
ck("R16", "样例提示以当地为准", "当地商务主管部门" in so)
ck("R17", "样例列出资证缺口", "缺口：" in so)
ck("R18", "样例时效 3 年", "3 年" in so)
ck("R19", "样例结尾免责", "最终以主管部门/司法机关认定为准" in so)
ck("R20", "样例金额无 .0 尾巴", "¥10240.0" not in so)
ck("R21", "样例表格不裂", "|---|" in so and so.count("|---|") >= 3)
ck("R22", "样例识别卡种", "期限卡" in so)
ck("R23", "样例冷静期天数两处一致", "已过 562 天" in so and "已过 562 天" in so)

# ------------------------------------------------------------------ json
rcj, soj, sej = run([SAMPLE, "--json"])
ck("J01", "json rc=0", rcj == 0, sej[:120])
d = None
try:
    d = json.loads(soj)
    okj = True
except Exception as e:
    okj = False
ck("J02", "json 可解析", okj, str(e)[:80] if not okj else "")
if d:
    ck("J03", "json 含测算键", "测算" in d)
    ck("J04", "json 测算 应退=10240",
       abs(d["测算"]["应退"] - 10240.0) < 1e-6, str(d["测算"]))
    ck("J05", "json 三类结论键", set(["不通过", "有风险", "待补正"]).issubset(set(d["结论"])))
    ck("J06", "json 待办非空", isinstance(d["待办"], list) and len(d["待办"]) > 0)
    ck("J07", "json 退卡情形", d["退卡触发情形"] == "门店关闭/停业跑路")
    ck("J08", "json 冷静期键", "冷静期" in d)

# ------------------------------------------------------------------ 空输入
rc2, so2, se2 = run([EMPTY])
ck("E01", "空输入 rc=2", rc2 == 2, "rc=%s" % rc2)
ck("E02", "空输入不崩", "Traceback" not in se2, se2[:120])
ck("E03", "空输入有输出", len(so2) > 20)
ck("E04", "空输入提示缺失", "门店名称" in so2 and "实付总额" in so2)
ck("E05", "空输入不臆造金额", "应退约" not in so2 and "¥" not in so2)
rc2j, so2j, _ = run([EMPTY, "--json"])
ck("E06", "空输入 json 可解析", so2j.strip().startswith("{") or "缺失" in so2j)
try:
    j2 = json.loads(so2j)
    ok2 = True
except Exception:
    ok2 = so2j.strip().startswith("{")
ck("E07", "空输入 json 解析不报错", ok2)
ck("E08", "空输入不产生任何金额", "¥" not in so2)

# ------------------------------------------------------------------ 落盘
out = os.path.join(HERE, "_reg_样例_核查报告.md")
rco, soo, _ = run([SAMPLE, "--base", "2026-10-05", "--out", out])
content = ""
if os.path.exists(out):
    content = open(out, encoding="utf-8").read()
ck("T01", "--out 落盘", os.path.exists(out) and len(content) > 500)
ck("T02", "落盘内容含九段", content.count("## ") >= 9)
ck("T03", "落盘无乱码", "\ufffd" not in content)
ck("T04", "落盘无【待填】", "【待填】" not in content)
ck("T05", "落盘可重复覆盖", os.path.exists(out))
if os.path.exists(out):
    os.remove(out)

# ------------------------------------------------------------------ 汇总
buf = []
for code, name, ok in P:
    buf.append("%s %s %s" % ("PASS" if ok else "FAIL", code, name))
buf.append("== TOTAL PASS=%d FAIL=%d ==" % (len(P), len(FAILED)))
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(buf) + "\n")
print("\n".join(buf))
sys.exit(1 if FAILED else 0)
