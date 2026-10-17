# -*- coding: utf-8 -*-
"""演出门票退换核查脚本回归测试（断言 58 条）。用 python 直接跑本文件。"""
import json
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)
import ticket_check as P  # noqa: E402

PASS = []
FAIL = []


def ck(name, cond):
    (PASS if cond else FAIL).append(name)


def mk(**kw):
    base = dict(
        event_name="", channel="", event_date="", status="", notice_date="",
        change_note="", cutoff=None, realname="", transfer="",
        face=None, paid=None, fee_rate=None, applied="", contact="",
        scalper="", bound="", offline="", scale_rec="", report="",
        ev_order="", ev_id="", ev_notice="", ev_rule="", ev_chat="",
        ev_scale="", ev_refused="",
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
ck("norm去空格", P.norm("  强实名  ") == "强实名")
ck("norm统一冒号", P.norm("演出状态：已延期") == "演出状态:已延期")
ck("filled空串", P.filled("") is False)
ck("filled斜杠提示", P.filled("有/无/不清楚") is False)
ck("filled有", P.filled("有") is True)
ck("filled待填", P.filled("待填") is False)
ck("yes是", P.yes("是") is True)
ck("yes已提交", P.yes("已提交") is True)
ck("no否", P.no("否") is True)
ck("no未提交", P.no("未提交") is True)
ck("unknown不清楚", P.unknown("不清楚") is True)
ck("unknown空", P.unknown("") is True)
ck("parse_num元", P.parse_num("1280元") == 1280.0)
ck("parse_num百分号", P.parse_num("20%") == 20.0)
ck("parse_num空", P.parse_num("") is None)
ck("fmt_num去.0", P.fmt_num(1280.0) == "1280")
ck("fmt_num保留小数", P.fmt_num(15.5) == "15.5")
ck("money前缀", P.money(1280.0) == "¥1280")
ck("parse_date", P.parse_date("2026-11-15") == date(2026, 11, 15))
ck("parse_date空", P.parse_date("") is None)
ck("base_date兜底", isinstance(P.base_date(""), date))

# ---------------------------------------------------------- 解析
txt = P.read_text(os.path.join(HERE, "样例.md"))
kv = P.build_kv(txt)
ck("build_kv表格取到演出名称", P.get_text(kv, ["演出名称"]) == "某歌手 2026 巡回演唱会（上海站）")
ck("build_kv取票面金额", P.get_text(kv, ["票面金额"]) == "1280")
ck("build_kv取是否实名票", P.get_text(kv, ["是否实名票"]) == "强实名")
ck("build_kv取演出状态", P.get_text(kv, ["演出状态"]) == "已延期")
ck("build_kv取公告日期", P.get_text(kv, ["取消或延期公告日期"]) == "2026-09-28")
ck("build_kv取退票截止", P.get_text(kv, ["退票申请截止（演出前多少小时截止）"]) == "48")
ck("build_kv取黄牛交易方式", P.get_text(kv, ["黄牛交易方式"]) == "微信转账")
kv2 = P.build_kv("演出名称：话剧茶馆\n演出状态：正常\n")
ck("build_kv冒号行", P.get_text(kv2, ["演出名称"]) == "话剧茶馆")
ck("get_text最长别名优先",
   P.get_text({"演出名称": "A", "演出项目": "B"}, ["演出名称", "演出项目"]) == "A")
ck("get_text兜底alias", P.get_text({"所在城市": "上海"}, ["城市"]) == "上海")
ck("build_kv空值行跳过", "演出名称" not in P.build_kv("| 字段 | 值 |\n|---|---|\n| 演出名称 |  |\n"))
ck("build_kv表头行被保留索引",
   P.build_kv("| 字段 | 值 |\n|---|---|\n| 演出名称 | 演唱会 |\n")["字段"] == "值")

# ---------------------------------------------------------- 状态词表
ck("status_kind取消", P.status_kind("演出已取消") == "已取消")
ck("status_kind延期", P.status_kind("已延期") == "已延期")
ck("status_kind变更", P.status_kind("场馆已变更") == "已变更")
ck("status_kind正常", P.status_kind("正常") == "正常")
ck("status_kind空", P.status_kind("") is None)
ck("status_kind未知词", P.status_kind("票已售罄") is None)
ck("status_kind未取消不误判为取消", P.status_kind("正常未取消") == "已取消")
ck("is_realname强实名", P.is_realname("强实名") is True)
ck("is_realname非实名", P.is_realname("非实名") is False)
ck("is_realname空", P.is_realname("") is None)
ck("is_scalper黄牛", P.is_scalper("是") is True)
ck("is_scalper二手平台", P.is_scalper("二手平台") is True)
ck("is_scalper官网渠道", P.is_scalper("大麦") is False)
ck("is_scalper空", P.is_scalper("") is False)

# ---------------------------------------------------------- 二 票种
rows_t = P.checks_type(mk(realname="强实名", transfer="否"))
chk1("强实名票种通过", rows_t, "票种（是否实名）", "通过")
chk1("不可转赠有风险", rows_t, "是否支持转赠", "有风险")
rows_t2 = P.checks_type(mk(realname="非实名", transfer="是"))
chk1("非实名票种通过", rows_t2, "票种（是否实名）", "通过")
chk1("可转赠通过", rows_t2, "是否支持转赠", "通过")
rows_t3 = P.checks_type(mk())
chk1("票种未填待补正", rows_t3, "票种（是否实名）", "待补正")
chk1("转赠未填待补正", rows_t3, "是否支持转赠", "待补正")

# ---------------------------------------------------------- 三 定性
rows_c = P.checks_cause(mk(status="已取消"))
chk1("取消定性为主办方原因", rows_c, "退改定性（谁的原因）", "通过")
chk1("取消提示全额退", rows_c, "演出状态", "通过")
rows_c2 = P.checks_cause(mk(status="正常"))
chk1("正常定性为观众原因", rows_c2, "退改定性（谁的原因）", "通过")
rows_c3 = P.checks_cause(mk())
chk1("状态缺失待补正", rows_c3, "演出状态", "待补正")
rows_c4 = P.checks_cause(mk(status="已变更"))
chk1("变更需补说明", rows_c4, "变更内容说明", "待补正")
chk1("变更已定性", rows_c4, "退改定性（谁的原因）", "通过")

# ---------------------------------------------------------- 四 金额
lo, hi, fee, why, st = P.calc_amount(mk(status="已取消", paid=1000.0), None)
ck("取消全额退下限", lo == 1000.0)
ck("取消全额退无手续费", fee == 0.0)
ck("取消全额退判定", st == "通过")
lo2, hi2, fee2, why2, st2 = P.calc_amount(
    mk(status="已延期", paid=3800.0, face=1280.0, scalper="是"), None)
ck("黄牛延期只退票面", lo2 == 1280.0)
ck("黄牛延期提示溢价自担", "只能自己扛" in why2)
ck("黄牛延期判定不通过", st2 == "不通过")
lo3, hi3, fee3, why3, st3 = P.calc_amount(mk(status="正常", paid=1000.0), 0)
ck("临近开场退0", lo3 == 0.0)
ck("临近开场判定不通过", st3 == "不通过")
lo4, hi4, fee4, why4, st4 = P.calc_amount(mk(status="正常", paid=1000.0, fee_rate=20.0), 5)
ck("按费率可退800", lo4 == 800.0)
ck("按费率算出手续费", fee4 == 200.0)
ck("按费率判定有风险", st4 == "有风险")
lo5, hi5, fee5, why5, st5 = P.calc_amount(mk(status="正常", paid=1000.0), 5)
ck("未填费率给下限700", lo5 == 700.0)
ck("未填费率给上限900", hi5 == 900.0)
ck("未填费率不给单值", str(lo5) != str(hi5))
rows_a = P.checks_amount(mk(status="已取消", paid=3800.0, face=1280.0, scalper="是"), 41)
chk1("溢价部分不通过", rows_a, "溢价部分", "不通过")
ck("溢价含差额", any("2520" in m for _n, _s, m in rows_a))
rows_a2 = P.checks_amount(mk(status="正常", paid=1000.0, face=1000.0), 5)
chk1("无溢价不产出溢价项", rows_a2, "溢价部分", None)
ck("手续费率未填待补正", any(r[0] == "退票手续费率" and r[1] == "待补正" for r in rows_a2))

# ---------------------------------------------------------- 五 转手与黄牛
rows_tr = P.checks_transfer(mk(scalper="是", bound="否", offline="微信转账",
                               scale_rec="无", realname="强实名", transfer="否"))
chk1("黄牛来源不通过", rows_tr, "购票来源", "不通过")
chk1("人票不一致不通过", rows_tr, "人票是否一致", "不通过")
chk1("线下交易不通过", rows_tr, "交易保障", "不通过")
chk1("缺黄牛记录待补正", rows_tr, "黄牛交易记录", "待补正")
chk1("强实名不可转手不通过", rows_tr, "转手可行性", "不通过")
rows_tr2 = P.checks_transfer(mk(scalper="否", realname="非实名", transfer="是"))
chk1("非实名可转手通过", rows_tr2, "转手可行性", "通过")
chk1("官网来源通过", rows_tr2, "购票来源", "通过")
rows_tr3 = P.checks_transfer(mk(scalper=""))
chk1("购票来源未填待补正", rows_tr3, "购票来源", "待补正")
rows_tr4 = P.checks_transfer(mk(scalper="是", bound="是"))
chk1("人票一致有风险", rows_tr4, "人票是否一致", "有风险")
ck("未填交易方式待补正", any(r[0] == "交易方式" and r[1] == "待补正" for r in
                           P.checks_transfer(mk(scalper="是", bound="是", offline=""))))

# ---------------------------------------------------------- 六 证据
rows_e = P.checks_evidence(mk(ev_order="有", ev_id="有", ev_notice="有",
                              ev_rule="有", ev_chat="有", ev_scale="有", ev_refused="有"))
ck("证据全有全通过", all(r[1] == "通过" for r in rows_e))
rows_e2 = P.checks_evidence(mk(ev_order="无"))
chk1("订单缺失不通过", rows_e2, "购票订单与票面截图", "不通过")
rows_e3 = P.checks_evidence(mk())
chk1("证据未填待补正", rows_e3, "平台退改规则页面", "待补正")
ck("证据项共7条", len(P.checks_evidence(mk())) == 7)

# ---------------------------------------------------------- 八 时限
rows_d = P.checks_deadline(mk(event_date="2026-11-15", cutoff=48), date(2026, 10, 5))
chk1("远期演出通过", rows_d, "距演出时间", "通过")
chk1("远期窗口通过", rows_d, "退票窗口剩余", "通过")
rows_d2 = P.checks_deadline(mk(event_date="2026-10-06", cutoff=48), date(2026, 10, 5))
chk1("临近开场不通过", rows_d2, "距演出时间", "不通过")
rows_d3 = P.checks_deadline(mk(event_date="2026-10-03", cutoff=48), date(2026, 10, 5))
chk1("窗口已关不通过", rows_d3, "退票窗口剩余", "不通过")
rows_d4 = P.checks_deadline(mk(event_date="2026-10-08", cutoff=48), date(2026, 10, 5))
chk1("窗口将关有风险", rows_d4, "退票窗口剩余", "有风险")
rows_d5 = P.checks_deadline(mk(event_date="2026-10-01", cutoff=0), date(2026, 10, 5))
chk1("演出已过不通过", rows_d5, "距演出时间", "不通过")
rows_d6 = P.checks_deadline(mk(event_date="", notice_date="2026-05-01"), date(2026, 10, 5))
chk1("缺演出日期待补正", rows_d6, "演出日期", "待补正")
chk1("公告较久有风险", rows_d6, "公告日起算", "有风险")
rows_d6b = P.checks_deadline(mk(event_date="", notice_date="2026-09-20"), date(2026, 10, 5))
chk1("公告15天内通过", rows_d6b, "公告日起算", "通过")
rows_d6c = P.checks_deadline(mk(event_date="", notice_date="2026-05-01"), date(2026, 10, 5))
chk1("公告超30天有风险", rows_d6c, "公告日起算", "有风险")
rows_d7 = P.checks_deadline(mk(event_date="2026-11-15"), date(2026, 10, 5))
chk1("无截止不产出窗口项", rows_d7, "退票窗口剩余", None)

# ---------------------------------------------------------- 七 阶梯与待办
stp = P.path_order(mk(scalper="是", status="已延期"))
ck("黄牛路径第1步", "人票" in stp[0][1])
ck("黄牛路径含报案", any("报案" in t for _s, t in stp))
stp2 = P.path_order(mk(scalper="否", status="已取消"))
ck("取消路径含文旅", any("文旅" in t for _s, t in stp2))
ck("取消路径第1步全额退", "全额退" in stp2[0][1])
stp3 = P.path_order(mk(scalper="否", status="正常"))
ck("正常路径第1步改签", "改签" in stp3[0][1])
todo = P.todo_list(mk(applied="否", contact="否", ev_rule="无"), [])
ck("待办含提交退改申请", any(n == "提交退改申请" for n, _s in todo))
ck("待办含截图规则页", any(n == "截图退改规则页" for n, _s in todo))
ck("待办去重", len([n for n, _s in todo]) == len(set(n for n, _s in todo)))

# ---------------------------------------------------------- 端到端
sp = os.path.join(SCRIPTS, "ticket_check.py")
env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"
sample = os.path.join(HERE, "样例.md")
empty = os.path.join(HERE, "空输入.md")
r1 = subprocess.run([sys.executable, sp, sample, "--base", "2026-10-05"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
ck("样例rc=0", r1.returncode == 0)
o1 = r1.stdout or ""
ck("样例含结论摘要", "一、结论摘要" in o1)
ck("样例含九段", o1.count("## ") >= 9)
ck("样例含待办段", "九、待办补正动作" in o1)
ck("样例含票种段", "二、票种与是否强实名" in o1)
ck("样例含定性段", "三、退还是改的定性" in o1)
ck("样例含金额段", "四、可退金额与手续费测算" in o1)
ck("样例含黄牛段", "五、转手与黄牛风险" in o1)
ck("样例含证据段", "六、证据缺口与取证" in o1)
ck("样例含阶梯段", "七、处理阶梯" in o1)
ck("样例含时限段", "八、时限倒计时" in o1)
ck("样例含无SECTION标题", "边界与纪律" in o1)
ck("样例含票价回执", "¥1280" in o1)
r2 = subprocess.run([sys.executable, sp, sample, "--json"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
try:
    d = json.loads(r2.stdout or "{}")
    ck("json可解析含结论", "结论" in d and "待办" in d)
    ck("json风险项非空", len(d.get("风险项", [])) > 0)
except Exception:
    ck("json可解析含结论", False)
r3 = subprocess.run([sys.executable, sp, empty],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
ck("空输入rc=2", r3.returncode == 2)
ck("空输入不崩有输出", len(r3.stdout or "") > 200)
ck("空输入提示缺失", "关键信息缺失" in (r3.stdout or ""))
ck("空输入不崩无异常串", "Traceback" not in (r3.stderr or ""))

# ---------------------------------------------------------- 汇总
total = len(PASS) + len(FAIL)
lines = ["=== 演出门票退换 回归测试 ===",
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
