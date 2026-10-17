# -*- coding: utf-8 -*-
"""快递丢失赔偿核算 —— 回归测试（断言 >= 40 条）

跑法（在本目录执行）：
  python 回归测试.py
结果写入 _reg_result.txt（utf-8，调用脚本自带函数 + 子进程实跑）。
"""
import json
import os
import re
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, os.pardir, "scripts", "express_lost_check.py")
sys.path.insert(0, os.path.join(HERE, os.pardir, "scripts"))
import express_lost_check as E  # noqa: E402

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
    base = dict(company="顺达速运", waybill="SF7788990011", item="单反相机机身",
                ship_date=date(2026, 9, 28), postage=18.0, insured=None,
                insured_amt=None, item_value=2600.0, extra_loss=None,
                heavy=None, ecommerce=None, scene=("普通件丢失", "plain"),
                police=None, consent=None, confirmed=None, evidence_rows=[])
    base.update(kw)
    return base


def store(text, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ------------------------------------------------------------------ 解析
kv_sample = E.build_kv(open(SAMPLE, encoding="utf-8").read())

ck("P01", "norm 去空格", E.norm("  顺达 速运 ") == "顺达速运")
ck("P02", "norm 全角冒号括号转半角",
   E.norm("收件人与地址：杭州市西湖区") == "收件人与地址:杭州市西湖区")
ck("P03", "filled 空为假", E.filled("") is False)
ck("P04", "filled 斜杠提示串为假", E.filled("有 / 无") is False)
ck("P05", "filled 待填开头为假", E.filled("待填") is False)
ck("P06", "filled 真值为真", E.filled("有") is True)
ck("P07", "parse_num 整数", E.parse_num("2600") == 2600.0)
ck("P08", "parse_num 带符号千分位", E.parse_num("¥12,800") == 12800.0)
ck("P09", "parse_num 文字取 None", E.parse_num("不清楚") is None)
ck("P10", "fmt_num 去 .0", E.fmt_num(2600.0) == "2600")
ck("P11", "fmt_num None", E.fmt_num(None) == "—")
ck("P12", "money 前缀与去零", E.money(18.0) == "¥18")
ck("P13", "yes 是", E.yes("是") is True)
ck("P14", "no 否", E.no("否") is True)
ck("P15", "no 未做", E.no("没有") is True)
ck("P16", "yes 不认带竖条目的值", E.yes("有|") is False)
ck("P17", "parse_date ISO", str(E.parse_date("2026-09-28")) == "2026-09-28")
ck("P18", "parse_date 中文", str(E.parse_date("2026年9月28日")) == "2026-09-28")
ck("P19", "parse_date 坏值取 None", E.parse_date("上周") is None)
ck("P20", "base_date 空取今天", E.base_date("") == date.today())
ck("P21", "base_date 指定值", E.base_date("2026-10-05") == BASE)
ck("P22", "build_kv 表格行", kv_sample.get("运单号") == "SF7788990011")
ck("P23", "build_kv 保留表头列", "字段" in kv_sample)
ck("P24", "build_kv 冒号行可解析",
   E.get_text(E.build_kv("交寄日期: 2026-09-28\n"), ["交寄日期", "寄件日期"]) == "2026-09-28")
ck("P25", "get_text 最长别名优先",
   E.get_text(kv_sample, ["内件实际价值", "内件价值"]) == "2600")
ck("P26", "get_text 未命中空串", E.get_text(kv_sample, ["不存在的字段"]) == "")
ck("P27", "get_text 不被更短 key 抢先",
   E.get_text(kv_sample, ["其他直接损失金额", "附带损失金额"]) == "300")

# ------------------------------------------------------------------ 场景识别
ck("S01", "场景 代收点", E.detect_scene("快递柜代收，未征得同意")[1] == "locker")
ck("S02", "场景 驿站", E.detect_scene("放在小区驿站了")[1] == "locker")
ck("S03", "场景 冒领", E.detect_scene("被别人冒领走了")[1] == "steal")
ck("S04", "场景 违禁", E.detect_scene("里面是管制刀具")[1] == "prohibit")
ck("S05", "场景 生鲜", E.detect_scene("冷链水果化了")[1] == "fresh")
ck("S06", "场景 国际件", E.detect_scene("国际件在中转场丢了")[1] == "international")
ck("S07", "场景 普通件", E.detect_scene("寄的衣服一直没到")[1] == "plain")
ck("S08", "场景 未填", E.detect_scene("")[1] is None)
ck("S09", "has_any 命中生鲜", E.has_any("冷链车厘子", E.FRESH_KEYS) is True)
ck("S10", "has_any 不误判普通内件", E.has_any("男士衬衫", E.FRESH_KEYS) is False)
ck("S11", "has_any 命中邮政渠道", E.has_any("挂号信", E.POSTAL_SERVICE) is True)
ck("S12", "has_any 不误判普通件", E.has_any("塑料积木", E.PROHIBIT_KEYS) is False)

# ------------------------------------------------------------------ 双口径测算
a = E.calc_compensation(mkf())
ck("C01", "未保价有资费：企业口径三倍资费", a[0] == 54.0)
ck("C02", "未保价有资费：可主张按实际价值", a[1] == 2600.0)
ck("C03", "未保价时企业口径说明含三倍", "三倍" in a[2])

b = E.calc_compensation(mkf(insured=False, postage=20.0))
ck("C04", "显式未保价也按三倍给企业口径", b[0] == 60.0)

c = E.calc_compensation(mkf(insured=True, insured_amt=3000.0))
ck("C05", "保价件企业口径封顶到实际价值", c[0] == 2600.0)

d = E.calc_compensation(mkf(insured=True, insured_amt=1000.0))
ck("C07", "保价低于实际价值按保价额", d[1] == 2600.0 and d[0] == 1000.0)

e = E.calc_compensation(mkf(insured=True, insured_amt=None))
ck("C08", "保价件缺保价金额算不出企业口径", e[0] is None)
ck("C09", "保价件缺金额说明提示补填", "补填保价金额" in e[2])

g = E.calc_compensation(mkf(insured=False, postage=None))
ck("C10", "未保价缺资费企业口径 None", g[0] is None)
ck("C11", "未保价缺资费可主张仍按价值", g[1] == 2600.0)

h = E.calc_compensation(mkf(item_value=None, postage=None))
ck("C12", "无价值无资费两口径都 None", h[0] is None and h[1] is None)

i = E.calc_compensation(mkf(heavy=True, extra_loss=300.0))
ck("C13", "有直接损失时加计", i[1] == 2900.0)
ck("C14", "加计说明含直接损失金额", "300" in i[3])

j = E.calc_compensation(mkf(item_value=None, postage=18.0))
ck("C15", "无价值时退到三倍资费兜底", j[1] == 54.0)

# ------------------------------------------------------------------ 路径与待办
steps = E.path_order(mkf(ecommerce=True), "plain")
ck("T01", "电商件第 0 步优先找卖家", any("第 0 步" in s for s, _t in steps))
ck("T02", "普通件无第 0 步",
   not any("第 0 步" in s for s, _t in E.path_order(mkf(ecommerce=False), "plain")))
ck("T03", "含客服留单步骤", any("工单号" in t for _s, t in steps))
ck("T04", "含 12305 步骤", any("12305" in t for _s, t in steps))
ck("T05", "含 12315 步骤", any("12315" in t for _s, t in steps))
ck("T06", "含小额诉讼", any("小额诉讼" in t for _s, t in steps))
ck("T07", "代收点场景给分支提示",
   any("分支提示" in s and "同意" in t for s, t in E.path_order(mkf(), "locker")))
ck("T08", "冒领场景要报警", any("报警" in t for _s, t in E.path_order(mkf(), "steal")))
ck("T09", "国际件给渠道提示",
   any("国际" in t or "邮政" in t for _s, t in E.path_order(mkf(), "international")))

t1 = E.todo_list(mkf(), [("段", [("x", "不通过", "m"), ("y", "有风险", "m"),
                                ("z", "待补正", "m")])], "locker", 54.0, 2900.0)
names1 = [n for n, _s in t1]
ck("T10", "待办含不通过与待补正项", "x" in names1 and "z" in names1)
ck("T11", "代收点未获同意进待办", any("同意" in n for n in names1))
ck("T12", "待办含一年期限", any("一年" in n for n in names1))
ck("T13", "待办去重复一项", len(names1) == len(set(names1)))

# ------------------------------------------------------------------ 证据
ev = E.evidence_rows(kv_sample)
st = {n: s for n, s in ev}
ck("V01", "证据 运单 有", st["快递运单（底单或电子面单截图）"] == "是")
ck("V02", "证据 保价凭证 无", st["保价凭证 / 保价协议"] == "否")
ck("V03", "证据 价值凭证 有", st["内件价值凭证（发票、订单、付款记录）"] == "是")
ck("V04", "证据 报警回执 无", st["报警回执（疑似冒领时）"] == "否")
ck("V05", "证据项共八项", len(ev) == 8)
ck("V06", "证据状态只四态", all(s in ("是", "否", "待确认", "未填") for _n, s in ev))

# ------------------------------------------------------------------ 样例实跑
rc, out, err = run([SAMPLE, "--base", "2026-10-05"])
ck("R01", "样例退出码 0", rc == 0, err[:200])
ck("R02", "样例无异常输出", "Traceback" not in err)
sec = len(re.findall(r"^## ", out, flags=re.M))
ck("R03", "样例段数 >= 9", sec >= 9, "sections=%d" % sec)
ck("R04", "样例含企业口径 54", "¥54" in out)
ck("R05", "样例含可主张口径 2900", "¥2900" in out)
ck("R06", "样例含差额 2846", "¥2846" in out)
ck("R07", "样例含三倍算式", "× 3" in out)
ck("R08", "样例含可主张口径更优提示", "优先按可主张口径主张" in out)
ck("R09", "样例含一年期限", "一年" in out)
ck("R10", "样例含诉讼时效 3 年", "3 年" in out)
ck("R11", "样例含 12305", "12305" in out)
ck("R12", "样例含代收点分支", "快递柜" in out or "代收点" in out)
ck("R13", "样例含未保价风险", "未保价" in out)
ck("R14", "样例含举证责任提示", "举证责任提示" in out)
ck("R15", "样例含证据缺口段", "证据缺口与清单核对" in out)
ck("R16", "样例含待办补正动作段", "待办补正动作" in out)
ck("R17", "样例含边界与纪律段", "边界与纪律" in out)
ck("R18", "样例不替代律师意见", "不替代" in out)
ck("R19", "样例未填不通过", "未填的一律不算通过" in out)
ck("R20", "样例结论段给出判定", "判定：" in out)
ck("R21", "样例报告以中文标题开头", out.startswith("# 快递丢失赔偿核算报告"))
ck("R22", "样例无乱码字符", "\ufffd" not in out)

# ------------------------------------------------------------------ json
rc2, out2, err2 = run([SAMPLE, "--json", "--base", "2026-10-05"])
ck("J01", "json 退出码 0", rc2 == 0, err2[:200])
try:
    dj = json.loads(out2)
    ok = True
except Exception:  # noqa: BLE001
    dj = {}
    ok = False
ck("J02", "json 可被 json.loads 解析", ok)
for key in ("结论", "风险项", "待办"):
    ck("J03-%s" % key, "json 含 %s" % key, key in dj)
ck("J04", "json 含企业口径", "企业口径" in dj and dj["企业口径"] == 54.0)
ck("J05", "json 含可主张口径", dj.get("可主张口径") == 2900.0)
ck("J06", "json 标出可主张口径更优", dj.get("口径孰优") == "可主张口径")
ck("J07", "json 记录丢失场景", dj.get("丢失场景") == "代收点 / 快递柜投递导致丢失")
ck("J08", "json 待办为列表", isinstance(dj.get("待办"), list))
ck("J09", "json 风险项为列表", isinstance(dj.get("风险项"), list))

# ------------------------------------------------------------------ 空输入
rc3, out3, err3 = run([EMPTY, "--base", "2026-10-05"])
ck("E01", "空输入退出码 2", rc3 == 2)
ck("E02", "空输入不崩无 Traceback", "Traceback" not in err3)
ck("E03", "空输入不产生任何金额", "¥" not in out3)
ck("E04", "空输入段数 >= 5", len(re.findall(r"^## ", out3, flags=re.M)) >= 5)
ck("E05", "空输入提示关键信息缺失", "关键信息缺失" in out3)
ck("E06", "空输入算不出判定", "暂时算不出赔偿金额" in out3)
ck("E07", "空输入有表格行", len(re.findall(r"^\| .+ \| .+ \|", out3, flags=re.M)) > 1)
ck("E08", "空输入有边界与纪律", "边界与纪律" in out3)

# ------------------------------------------------------------------ 落盘
tmp = os.path.join(HERE, "_tmp_out.md")
rc4, out4, err4 = run([SAMPLE, "--base", "2026-10-05", "--out", tmp])
ck("D01", "落盘退出码 0", rc4 == 0, err4[:200])
ck("D02", "落盘后打印已写出", "已写出" in out4)
ck("D03", "落盘文件非空", os.path.exists(tmp) and os.path.getsize(tmp) > 1000)
if os.path.exists(tmp):
    body = open(tmp, encoding="utf-8").read()
    ck("D04", "落盘内容与 stdout 一致", body.strip() == out.strip())
    os.remove(tmp)

# ------------------------------------------------------------------ 汇总
total = len(P)
passed = sum(1 for _c, _n, ok in P if ok)
lines = ["=== 快递丢失赔偿核算 回归结果 ===",
         "TOTAL PASS=%d FAIL=%d" % (passed, total - passed)]
for code, name, ok in P:
    lines.append("%s %s %s" % ("PASS" if ok else "FAIL", code, name))
if FAILED:
    lines.append("---- FAILED ----")
    lines += FAILED
store("\n".join(lines), os.path.join(HERE, "_reg_result.txt"))
print("=== TOTAL PASS=%d FAIL=%d ===" % (passed, total - passed))
for code, name, ok in P:
    if not ok:
        print("FAIL %s %s" % (code, name))
