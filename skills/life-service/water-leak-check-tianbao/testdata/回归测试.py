#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""water_leak_check 回归测试。运行：python 回归测试.py"""
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "water_leak_check.py")
SAMPLE = os.path.join(HERE, "样例.md")
EMPTY = os.path.join(HERE, "空输入.md")

spec = importlib.util.spec_from_file_location("wlc", SCRIPT)
wlc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wlc)

PASS = 0
FAIL = 0
FAILED = []
LOG = open(os.path.join(HERE, "_reg_fail.txt"), "w", encoding="utf-8")


def ok(cond, name):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILED.append(name)
        LOG.write("FAIL: %s\n" % name)


def chk1(name, rows, item, state=None):
    """rows 为 (名称, 判定, 说明) 列表。"""
    r = None
    for x in rows:
        if x[0] == item:
            r = x
            break
    ok(r is not None, "%s 存在项「%s」" % (name, item))
    if r is None:
        return
    if state is not None:
        ok(r[1] == state, "%s 项「%s」判定应为 %s（实际 %s）" % (name, item, state, r[1]))


def state_of(rows, item):
    for x in rows:
        if x[0] == item:
            return x[1]
    return None


def msg_of(rows, item):
    for x in rows:
        if x[0] == item:
            return x[2]
    return ""


def base_f():
    return {
        "part": "卫生间及相邻客厅天花板",
        "scene": "自有商品住宅",
        "found_date": "2025-06-18",
        "completion_date": "2016-08-25",
        "upstairs_reason": "楼上住户装修时破坏卫生间防水层",
        "public_part": "否（属户内楼板渗漏）",
        "public_kw": "",
        "cause_clear": "否",
        "cause_desc": "",
        "appraised": "否",
        "appraisal_fee": 8000.0,
        "repair_cost": 12000.0,
        "property_loss": 3200.0,
        "other_cost": 500.0,
        "rent_loss": 6000.0,
        "repair_done": "未修复",
        "scope_expanded": "是（顺手翻新客厅）",
        "policy_reported": "是（电话报修）",
        "policy_on_site": "否",
        "notified": "否",
        "notify_to": "",
        "community": "否",
        "fund_possible": "否",
        "vote_done": "不涉及",
        "rental": "否",
        "tenant_notified": "",
        "fee_owed": "是（欠物业费想抵扣）",
        "claim": "否",
        "evidence": "照片与工单",
    }


# ------------------------------------------------------------------ 1 基础工具
ok(wlc.norm("漏水：部位（A）") == "漏水:部位(A)", "norm 全角转半角并去空白")
ok(wlc.norm(None) == "", "norm None 返回空串")
ok(wlc.filled("是") is True, "filled 有值")
ok(wlc.filled("是/否") is False, "filled 斜杠视为未填")
ok(wlc.filled("待填") is False, "filled 占位词")
ok(wlc.filled("") is False, "filled 空串")
ok(wlc.filled(None) is False, "filled None")
ok(wlc.filled(3.0) is True, "filled 数字转字符串")
ok(wlc.yes("是（附现场照片）") is True, "yes 去括号识别")
ok(wlc.yes("已经有工单号") is True, "yes 前缀匹配")
ok(wlc.yes("否") is False, "yes 不误判为否")
ok(wlc.no("没有到场记录") is True, "no 前缀匹配")
ok(wlc.no("已到场") is False, "no 不误判")
ok(wlc.unknown("不清楚") is True, "unknown 识别未知")
ok(wlc.unknown("") is True, "unknown 空值")
ok(wlc.parse_num("¥12,000.00") == 12000.0, "parse_num 货币与千分位")
ok(wlc.parse_num("无") is None, "parse_num 无数字")
ok(wlc.fmt_num(12000.0) == "12000", "fmt_num 去 .0")
ok(wlc.fmt_num(15200.5) == "15200.5", "fmt_num 保留两位小数")
ok(wlc.fmt_num(3.0) == "3", "fmt_num 小整数")
ok(wlc.fmt_num(None) == "—", "fmt_num 空值")
d = wlc.parse_date("2016年8月25日")
ok(d is not None and d.month == 8 and d.day == 25, "parse_date 中文日期")
ok(wlc.parse_date("无") is None, "parse_date 无日期")
ok(wlc.add_years(d, 5).year == 2021, "add_years 正常")
ok(str(wlc.add_years(wlc.date(2020, 2, 29), 5)) == "2025-02-01", "add_years 闰年兜底")

# ------------------------------------------------------------------ 2 保修期
ok(wlc.warranty_years("卫生间防水")[0] == 5, "防水部位 5 年")
ok(wlc.warranty_years("屋面")[0] == 5, "屋面 5 年")
ok(wlc.warranty_years("外墙")[0] == 5, "外墙 5 年")
ok(wlc.warranty_years("给排水管道")[0] == 2, "给排水 2 年")
ok(wlc.warranty_years("装修工程")[0] == 2, "装修 2 年")
ok(wlc.warranty_years("地基基础")[0] is None, "其他部位无年限")

f0 = base_f()
f0["completion_date"] = ""
_, _, ws, wm = wlc.warranty_check(f0, wlc.date(2026, 10, 5))
ok(ws == "待补正", "缺竣工日期 → 待补正")
ok("竣工验收合格之日" in wm, "缺竣工日期提示起算日")

f1 = base_f()
f1["completion_date"] = "2016-08-25"
y, dl, ws, wm = wlc.warranty_check(f1, wlc.date(2026, 10, 5))
ok(y == 5 and str(dl) == "2021-08-25", "5 年保修期到期日")
ok(ws == "有风险", "超期 → 有风险")
ok("原始施工缺陷" in wm, "超期仍提示原始施工缺陷")

f2 = base_f()
f2["completion_date"] = "2024-03-01"
y2, _dl2, ws2, wm2 = wlc.warranty_check(f2, wlc.date(2026, 10, 5))
ok(ws2 == "通过", "在保 → 通过")
ok("开发商" in wm2, "在保提示开发商承担保修")

# ------------------------------------------------------------------ 3 责任归属
rows = wlc.responsibility(f1, "保修期外")
chk1("责任归属", rows, "责任归属", "不通过")
ok("楼上业主" in msg_of(rows, "责任归属"), "楼上原因指向楼上业主")
chk1("责任归属", rows, "楼上住户原因", "通过")
chk1("责任归属", rows, "公共部位判定", "通过")
ok("非公共部位" in msg_of(rows, "公共部位判定"), "公共部位判定走非公共分支")

f3 = base_f()
f3["upstairs_reason"] = ""
f3["public_part"] = "是（下水立管渗漏）"
rows3 = wlc.responsibility(f3, "保修期外")
chk1("责任归属", rows3, "责任归属", "有风险")
ok("住宅专项维修资金" in msg_of(rows3, "责任归属"), "公共部位指向维修资金")

f4 = base_f()
f4["upstairs_reason"] = ""
f4["public_part"] = "否"
f4["completion_date"] = "2024-03-01"
rows4 = wlc.responsibility(f4, "保修期内")
chk1("责任归属", rows4, "责任归属", "不通过")
ok("开发商" in msg_of(rows4, "责任归属"), "保修期内归开发商")

f5 = base_f()
f5["upstairs_reason"] = ""
f5["public_part"] = ""
f5["completion_date"] = ""
rows5 = wlc.responsibility(f5, "待定")
chk1("责任归属", rows5, "责任归属", "待补正")

f6 = base_f()
f6["upstairs_reason"] = "原因不详，待现场查勘定责"
rows6 = wlc.responsibility(f6, "保修期外")
chk1("责任归属", rows6, "楼上住户原因", "待补正")
ok("地漏堵塞" in msg_of(rows6, "楼上住户原因"), "楼上原因不明确给常见行为提示")

# ------------------------------------------------------------------ 4 取证与鉴定
rows = wlc.checks_evidence(f1)
chk1("取证", rows, "物业报修", "通过")
chk1("取证", rows, "物业到场记录", "待补正")
ok("签到记录" in msg_of(rows, "物业到场记录"), "到场记录要求留书面凭证")
chk1("取证", rows, "书面通知", "有风险")
chk1("取证", rows, "渗漏原因鉴定", "有风险")
ok("先评估是否值得鉴定" in msg_of(rows, "渗漏原因鉴定"), "未鉴定提示性价比")
chk1("取证", rows, "维修范围", "不通过")
ok("扩大部分" in msg_of(rows, "维修范围"), "扩大维修范围不给支持")

f7 = base_f()
f7["appraised"] = "是（已出具渗漏原因鉴定报告，认定楼上装修破坏防水层）"
rows7 = wlc.checks_evidence(f7)
chk1("取证", rows7, "渗漏原因鉴定", "通过")

f8 = base_f()
f8["policy_reported"] = "否"
rows8 = wlc.checks_evidence(f8)
chk1("取证", rows8, "物业报修", "不通过")
ok("立刻止损" in msg_of(rows8, "物业报修") or "现在马上书面报修" in msg_of(rows8, "物业报修"),
   "未报修提示立即补报修")

# ------------------------------------------------------------------ 5 损失核算
rows = wlc.checks_loss(f1)
ok("15700" in msg_of(rows, "直接损失合计"), "直接损失合计 15700")
chk1("损失", rows, "直接损失合计", "通过")
ok("23700" in msg_of(rows, "可主张赔偿范围"), "可主张口径含鉴定费 23700")
chk1("损失", rows, "租金与住宿损失", "有风险")
ok("难以获得全额支持" in msg_of(rows, "租金与住宿损失"), "租金损失如实提示")
chk1("损失", rows, "鉴定费占比", "有风险")
chk1("损失", rows, "修复费用", "通过")
chk1("损失", rows, "财产损失", "通过")

f9 = base_f()
f9["appraisal_fee"] = None
f9["repair_cost"] = None
f9["property_loss"] = None
f9["rent_loss"] = None
rows9 = wlc.checks_loss(f9)
ok(msg_of(rows9, "直接损失合计").startswith("修复费 0 元"), "缺费用按 0 计并明示")
chk1("损失", rows9, "修复费用", "待补正")
chk1("损失", rows9, "财产损失", "待补正")
chk1("损失", rows9, "租金与住宿损失", "待补正")

# ------------------------------------------------------------------ 6 特殊情形
rows = wlc.checks_special(f1)
chk1("特殊", rows, "住宅专项维修资金", "通过")
ok("不适用住宅专项维修资金" in msg_of(rows, "住宅专项维修资金"), "非公共部位不适用维修资金")
chk1("特殊", rows, "房屋性质", "通过")
chk1("特殊", rows, "以拒交物业费对抗", "不通过")
ok("两个独立的法律关系" in msg_of(rows, "以拒交物业费对抗"), "物业费与漏水是两个法律关系")

f10 = base_f()
f10["rental"] = "是（承租）"
f10["tenant_notified"] = "否"
rows10 = wlc.checks_special(f10)
chk1("特殊", rows10, "承租人通知义务", "不通过")
ok("扩大部分可能由承租人自担" in msg_of(rows10, "承租人通知义务"), "承租人未及时通知提示自担")
chk1("特殊", rows10, "出租人维修义务", "有风险")

f11 = base_f()
f11["rental"] = "是"
f11["tenant_notified"] = "是（微信已发房东）"
f11["fund_possible"] = "是"
f11["vote_done"] = "是"
rows11 = wlc.checks_special(f11)
chk1("特殊", rows11, "承租人通知义务", "通过")
ok("及时通知" in msg_of(rows11, "承租人通知义务"), "承租人及时通知通过")
chk1("特殊", rows11, "住宅专项维修资金", "通过")

# ------------------------------------------------------------------ 7 路径与待办
steps = wlc.path_order(f1)
ok(len(steps) == 6, "业主路径 6 步")
ok("12345" in steps[4][1], "业主路径含 12345")
ok("先予执行" in steps[5][1], "业主路径末步含先予执行")
steps_r = wlc.path_order(f10)
ok(len(steps_r) == 5, "租房路径 5 步")
ok("房东" in steps_r[1][1], "租房路径向房东主张")

todos = wlc.todo_list(f1, [("t", wlc.checks_evidence(f1))])
ok("立即止损" in [t[0] for t in todos], "待办含立即止损")
ok("物业报修养工单" in [t[0] for t in todos], "待办含物业报修养工单")
ok("别拿物业费对冲" in [t[0] for t in todos], "待办含别拿物业费对冲")
ok("修复前留报价" in [t[0] for t in todos], "待办含修复前留报价")
ok(len(todos) == len(set(t[0] for t in todos)), "待办去重")
ok(wlc.todo_list(f1, [])[0][0] == "立即止损", "无风险项也有基础待办")

# ------------------------------------------------------------------ 8 报告渲染
y, dl, ws, wm = wlc.warranty_check(f1, wlc.date(2026, 10, 5))
res = [("责任归属判定", wlc.responsibility(f1, "保修期外")),
       ("保修期与开发商责任", [("保修期核查", ws, wm)]),
       ("取证与鉴定", wlc.checks_evidence(f1)),
       ("损失核算与赔偿范围", wlc.checks_loss(f1)),
       ("租房与特殊情形", wlc.checks_special(f1))]
td = wlc.todo_list(f1, res)
rep = wlc.render(f1, res, wlc.path_order(f1), td, wlc.date(2026, 10, 5),
                 "时效还剩 1000 天", "楼上住户")
ok(rep.count("\n## ") >= 9, "报告至少 9 个 ## 段（实际 %d）" % rep.count("\n## "))
for sec in ["一、结论摘要", "二、责任归属判定", "三、保修期与开发商责任",
            "四、取证与鉴定", "五、损失核算与赔偿范围", "六、交涉路径与时效",
            "七、租房与特殊情形", "八、待办补正动作", "九、边界与纪律"]:
    ok(("## " + sec) in rep, "报告含段「%s」" % sec)
ok("责任相对明确，存在必须补正的取证缺口" in rep, "有不通过时的结论文案")
ok("楼上住户（相邻关系/侵权责任）" in wlc.responsibility_text(f1, "保修期外"), "责任初判文案")
ok("开发商（建设工程质量保修责任）" in wlc.responsibility_text(f4, "保修期内"), "在保责任初判")
ok("未填的一律不算通过" in rep, "边界段说明未填不算通过")
ok("不替代律师意见" in rep, "边界段声明不替代律师意见")
ok("\ufffd" not in rep, "报告无乱码")

j = wlc.to_json(f1, res, td, wlc.date(2026, 10, 5), "楼上住户")
ok(j["结论"] == "有风险", "json 结论为有风险")
ok("以拒交物业费对抗" in j["风险项"], "json 风险项含物业费问题")
ok("物业到场记录" in j["待办"], "json 待办含待补正事项")
ok("以拒交物业费对抗" in j["风险项"], "json 风险项含物业费事后")
ok(json.dumps(j, ensure_ascii=False) != "", "json 可序列化")

# ------------------------------------------------------------------ 9 端到端
cmd = [sys.executable, SCRIPT, SAMPLE, "--base", "2026-10-05", "--json"]
p = subprocess.run(cmd, capture_output=True, encoding="utf-8")
ok(p.returncode == 0, "样例端到端退出码 0（实际 %s）" % p.returncode)
try:
    data = json.loads(p.stdout)
    ok(data["结论"] == "有风险", "样例 json 结论 有风险")
    ok("漏水部位" in data, "样例 json 含漏水部位")
    ok(len(data["待办动作"]) >= 5, "样例待办动作不少于 5 条")
except Exception as e:
    ok(False, "样例 json 可解析（%s）" % e)

out = os.path.join(HERE, "_核查报告.md")
if os.path.exists(out):
    os.remove(out)
p2 = subprocess.run([sys.executable, SCRIPT, SAMPLE, "--base", "2026-10-05",
                     "--out", out], capture_output=True, encoding="utf-8")
ok(p2.returncode == 0, "样例 --out 退出码 0")
txt = ""
if os.path.exists(out):
    with open(out, encoding="utf-8") as fh:
        txt = fh.read()
    ok(txt.count("\n## ") >= 9, "落盘报告 9 段（实际 %d）" % txt.count("\n## "))
ok("2021-08-25" in txt, "报告写出保修期到期日")
ok("15200" in txt, "报告写出直接损失合计")
ok("已欠物业费想抵扣" not in txt, "报告不含未解析的原文堆砌")

p3 = subprocess.run([sys.executable, SCRIPT, EMPTY, "--base", "2026-10-05"],
                    capture_output=True, encoding="utf-8")
ok(p3.returncode == 2, "空输入退出码 2（实际 %s）" % p3.returncode)
ok("漏水部位" in p3.stdout, "空输入给出缺失提示")

S = "PASS=%d FAIL=%d TOTAL=%d" % (PASS, FAIL, PASS + FAIL)
LOG.write(S + "\n")
LOG.close()
print(S)
sys.exit(0 if FAIL == 0 else 1)
