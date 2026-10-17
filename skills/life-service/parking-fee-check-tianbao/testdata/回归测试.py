# -*- coding: utf-8 -*-
"""停车收费核查脚本回归测试（断言 45 条）。用 python 直接跑本文件。"""
import json
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)
import parking_check as P  # noqa: E402

PASS = []
FAIL = []


def ck(name, cond):
    (PASS if cond else FAIL).append(name)


def mk(**kw):
    base = dict(
        scene="", subject="", space_type="", paid=None, std=None,
        rent_old=None, rent_new=None, has_board="", board_tel="",
        vote="", vote_public="", damaged="", damage_type="", ticket="",
        camera="", police="", claim="", ticket_penalty="", penalty_body="",
        towed="", tow_fee="", tow_fee_amt=None, penalty_date="", contact="", evidence="",
    )
    base.update(kw)
    return base


def chk1(name, rows, item, state=None):
    for r in rows:
        if r[0] == item:
            if state is None:
                ck(name + "被触发", True)
            else:
                ck(name + "=" + state, r[1] == state)
            return
    ck(name + "(未出现)", state is None)


# ---------------------------------------------------------- 基础工具
ck("norm去空格", P.norm("  有  ") == "有")
ck("norm统一冒号", P.norm("停车场景：小区") == "停车场景:小区")
ck("filled空串=False", P.filled("") is False)
ck("filled斜杠提示=False", P.filled("有/无/不清楚") is False)
ck("filled有=True", P.filled("有") is True)
ck("filled待填=False", P.filled("待填") is False)
ck("yes有", P.yes("有") is True)
ck("yes是", P.yes("是") is True)
ck("no无", P.no("无") is True)
ck("no否", P.no("否") is True)
ck("unknown不清楚", P.unknown("不清楚") is True)
ck("unknown空", P.unknown("") is True)
ck("unknown已填", P.unknown("有") is False)
ck("parse_num元", P.parse_num("15元") == 15.0)
ck("parse_num逗号", P.parse_num("1,200") == 1200.0)
ck("parse_num空", P.parse_num("") is None)
ck("fmt_num去.0", P.fmt_num(15.0) == "15")
ck("fmt_num保留小数", P.fmt_num(15.5) == "15.5")
ck("parse_date", P.parse_date("2026-09-25") == date(2026, 9, 25))
ck("parse_date空", P.parse_date("") is None)
ck("base_date兜底", isinstance(P.base_date(""), date))

# ---------------------------------------------------------- 解析
txt = P.read_text(os.path.join(HERE, "样例.md"))
kv = P.build_kv(txt)
ck("build_kv表格取到场景", P.get_text(kv, ["停车场景"]) == "小区")
ck("build_kv取月租金额", P.get_text(kv, ["月租金额"]) == "600")
ck("build_kv取公示牌", P.get_text(kv, ["现场有无收费公示牌"]) == "无")
kv2 = P.build_kv("停车场景：城市道路泊位\n收费主体：市政\n")
ck("build_kv冒号行", P.get_text(kv2, ["停车场景"]) == "城市道路泊位")
ck("get_text最长别名优先",
    P.get_text({"停车场景": "小区", "场景": "商场"}, ["停车场景", "场景"]) == "小区")
ck("get_text兜底alias", P.get_text({"所在城市": "上海"}, ["城市"]) == "上海")

# ---------------------------------------------------------- 定价与明码标价
ck("pricing小区", P.pricing_type("小区")[0] == "市场调节价")
ck("pricing道路", P.pricing_type("城市道路泊位")[0] == "政府定价或政府指导价")
ck("pricing医院", P.pricing_type("医院")[0] == "政府定价或政府指导价")
ck("pricing空", P.pricing_type("")[0] == "需确认")
rows, _pt = P.checks_pricing(mk(scene="小区", paid=15.0, std=10.0))
chk1("超标准收费", rows, "超标准收费", "有风险")
ck("超标准含差额", any("5" in m and "差额" in m for _n, _s, m in rows))
rows2, _ = P.checks_pricing(mk(scene="小区", paid=10.0, std=10.0))
chk1("实缴未超标准", rows2, "实缴与公示标准", "通过")
rows3, _ = P.checks_pricing(mk(scene="小区", paid=15.0))
chk1("缺公示标准", rows3, "公示标准", "待补正")

ck("无公示牌不通过", P.checks_posting(mk(has_board="无"))[0][1] == "不通过")
rows4 = P.checks_posting(mk(has_board="有", board_tel="是"))
chk1("有牌含电话", rows4, "公示含投诉电话", "通过")
rows5 = P.checks_posting(mk(has_board="有", board_tel="否"))
chk1("有牌无电话", rows5, "公示含投诉电话", "有风险")
ck("公示未填待补正", P.checks_posting(mk())[0][1] == "待补正")

# ---------------------------------------------------------- 小区
rows6 = P.checks_community(mk(scene="小区", space_type="业主共有车位",
                              vote="否", vote_public="无", rent_old=300.0, rent_new=600.0))
chk1("共有车位风险", rows6, "车位性质", "有风险")
chk1("未表决不通过", rows6, "涨价程序", "不通过")
ck("涨幅含100%", any("100" in m for _n, _s, m in rows6))
rows7 = P.checks_community(mk(scene="小区", space_type="人防车位"))
chk1("人防车位", rows7, "车位性质", "有风险")
rows8 = P.checks_community(mk(scene="小区", space_type="产权车位", vote="是", vote_public="有"))
chk1("产权车位程序完整", rows8, "涨价程序", "通过")
ck("非小区不产出小区项", P.checks_community(mk(scene="商场", space_type="产权车位")) == [])
ck("车位性质未填", P.checks_community(mk(scene="小区", space_type=""))[0][0] == "车位性质")

# ---------------------------------------------------------- 车损
rows9 = P.checks_damage(mk(damaged="是", damage_type="刮擦", ticket="有",
                           camera="未调取", police="否", claim="否"))
chk1("无凭证通过", rows9, "停车凭证", "通过")
chk1("未调监控不通过", rows9, "监控保全", "不通过")
ck("监控提示7~30天", any("7~30" in m for _n, _s, m in rows9))
chk1("未报警", rows9, "报警记录", "有风险")
chk1("未书面索赔", rows9, "索赔主张", "待补正")
rows10 = P.checks_damage(mk(damaged="是", camera="已调取", claim="是"))
chk1("已调监控", rows10, "监控保全", "通过")
ck("未受损不产出车损项", P.checks_damage(mk(damaged="否", damaged_=None)) == [])
_d = P.checks_damage(mk(damaged="是", camera="超过保存期"))
ck("监控超保存期", any(r[0] == "监控保全" and r[1] == "不通过" for r in _d))
ck("超保存期提示取证链条", any("取证链条断裂" in r[2] for r in _d))

# ---------------------------------------------------------- 违停与拖车
rows11 = P.checks_penalty(mk(ticket_penalty="是", penalty_body="物业", towed="是",
                             tow_fee="是", tow_fee_amt=300.0, penalty_date="2026-09-25"),
                          date(2026, 10, 5))
chk1("拖车费不得收", rows11, "拖车费", "不通过")
ck("拖车费含不得向当事人收取拖车费",
   any("不得向当事人收取拖车费" in m for _n, _s, m in rows11))
chk1("复议时限在期", rows11, "行政复议时限", "通过")
ck("复议剩50天", any("还剩 50 天" in m for _n, _s, m in rows11))
rows12 = P.checks_penalty(mk(ticket_penalty="是", penalty_date="2026-01-01"),
                          date(2026, 10, 5))
chk1("复议超时", rows12, "行政复议时限", "有风险")
ck("复议已过", any("已过" in m for _n, _s, m in rows12))
ck("无处罚不产出", P.checks_penalty(mk(ticket_penalty="否"), date(2026, 10, 5)) == [])

# ---------------------------------------------------------- 路径与待办
st = P.path_order(mk(scene="小区"))
ck("小区路径第1步", "业主大会决议" in st[0][1])
st2 = P.path_order(mk(scene="城市道路泊位"))
ck("道路路径含市场监管",
   ("市场监督" in " ".join(str(t) for _s, t in st2))
   and ("12345" in " ".join(str(t) for _s, t in st2)))
todo = P.todo_list(mk(scene="小区", has_board="无", damaged="是", camera="未调取"), [])
ck("待办含保全监控", any(n == "保全监控" for n, _s in todo))
ck("待办含索要决议", any(n == "索要决议" for n, _s in todo))

# ---------------------------------------------------------- 端到端
sp = os.path.join(SCRIPTS, "parking_check.py")
env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"
sample = os.path.join(HERE, "样例.md")
empty = os.path.join(HERE, "空停车信息.md")
r1 = subprocess.run([sys.executable, sp, sample, "--base", "2026-10-05"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
ck("样例rc=0", r1.returncode == 0)
o1 = r1.stdout or ""
ck("样例含结论摘要", "一、结论摘要" in o1)
ck("样例含待办段", "九、待办补正动作" in o1)
ck("样例含九段", o1.count("## ") >= 9)
ck("样例含不通过", "不通过" in o1)
ck("样例含定价性质段", "二、定价性质与收费依据" in o1)
ck("样例含小区段", "四、小区车位与涨价程序" in o1)
ck("样例含车损段", "五、车辆受损责任" in o1)
ck("样例含路径段", "七、投诉路径排序" in o1)
r2 = subprocess.run([sys.executable, sp, sample, "--json"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
try:
    d = json.loads(r2.stdout or "{}")
    ck("json可解析含结论", "结论" in d and "待办" in d)
except Exception:
    ck("json可解析含结论", False)
r3 = subprocess.run([sys.executable, sp, empty],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
ck("空输入rc=2", r3.returncode == 2)
ck("空输入不崩有输出", len(r3.stdout or "") > 200)
ck("空输入提示缺失", "关键信息缺失" in (r3.stdout or ""))

# ---------------------------------------------------------- 汇总
total = len(PASS) + len(FAIL)
lines = ["=== 停车收费 回归测试 ===",
         "PASS=%d FAIL=%d TOTAL=%d" % (len(PASS), len(FAIL), total), ""]
for n in PASS:
    lines.append("  ok  " + n)
for n in FAIL:
    lines.append("  FAIL " + n)
lines.append("")
lines.append("RESULT: %s" % ("ALL PASS" if not FAIL else "FAILED"))
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\n".join(lines[:3]))
sys.exit(1 if FAIL else 0)
