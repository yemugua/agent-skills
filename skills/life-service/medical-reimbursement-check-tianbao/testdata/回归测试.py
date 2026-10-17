#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""reimburse_check 回归测试 —— 结果自写 utf-8 文件（PowerShell 会吞 python stdout）"""
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import reimburse_check as rc  # noqa: E402

PASS = [0]
FAIL = []


def ck(name, got, want):
    if got == want:
        PASS[0] += 1
    else:
        FAIL.append("%s → got=%r want=%r" % (name, got, want))


def ck_true(name, cond):
    if cond:
        PASS[0] += 1
    else:
        FAIL.append("%s → 断言不成立" % name)


# ---------- 1. 解析 ----------
ck("P01 金额", rc.parse_money("26800"), 26800.0)
ck("P02 千分位", rc.parse_money("12,800"), 12800.0)
ck("P03 占位", rc.parse_money("待填写"), None)
ck("P04 破折号", rc.parse_money("—"), None)
ck("P05 百分比", rc.parse_pct("10"), 10.0)
ck("P06 百分比带%", rc.parse_pct("70%"), 70.0)
ck("P07 百分比占位", rc.parse_pct("待填写"), None)
ck("P08 日期", rc.parse_date("2026-05-15"), date(2026, 5, 15))
ck("P09 日期占位", rc.parse_date("待填写"), None)

# 取第一个可解析（说明行在前）
tpl = """## 一、这次费用本身

| 项 | 填什么 |
|---|---|
| 医疗总费用（发票合计） | 数字（元） |
| 医疗总费用（发票合计） | 26800 |
| 其中目录外自费 | 数字（元） |
| 其中目录外自费 | 4800 |
"""
ck("P10 金额跳过说明行", rc.get_money(tpl, "医疗总费用", "总费用", "发票合计"), 26800.0)
ck("P11 自费跳过说明行", rc.get_money(tpl, "目录外自费", "自费"), 4800.0)
ck("P12 中文变量名占位无副作用", rc.get_text(tpl, "就医类型", "本次就医类型"), "")

# ---------- 2. 硬拒只认勾选，不扫全文 ----------
doc = """## 四、被拒/异常情形

| 项 | 填什么 |
|---|---|
| 涉及第三方责任（车祸/打架/他人侵权） | 无 |
| 是否工伤或职业病 | 无 |
| 是否含美容整形/体检/境外就医 | 无 |
"""
ck("P13 勾了「无」不算硬拒", rc.yes_no(doc, ("涉及第三方责任", "第三方责任")), False)
ck("P14 没填返回 None", rc.yes_no("| a | b |", ("压根没有",)), None)
doc2 = doc.replace("| 涉及第三方责任（车祸/打架/他人侵权） | 无 |",
                   "| 涉及第三方责任（车祸/打架/他人侵权） | 有 |")
ck("P15 勾了「有」= 硬拒命中", rc.yes_no(doc2, ("涉及第三方责任", "第三方责任")), True)

# 自由文本里出现「车祸」不算硬拒（只有第四节勾选才算）
probe = doc + "\n（补充说明：以前出过车祸，但这次是阑尾炎，与第三方无关。\n"
ck("P16 正文提车祸不误判", rc.yes_no(probe, ("涉及第三方责任", "第三方责任")), False)

# ---------- 3. 金额四层 ----------
SAMPLE = os.path.join(HERE, "费用报销样例.md")
base = date(2026, 6, 10)
body, res = rc.build_report(SAMPLE, base)
ck_true("R01 body 非空", body is not None)
ck("R02 总费用", res["total"], 26800.0)
ck("R03 目录内", res["inner"], 22000.0)
ck("R04 先行自付", res["pre"], 2200.0)
ck("R05 可报基数", res["base_amount"], 22000.0 - 2200.0 - 1500.0)
ck("R06 估算可报", res["estimate"], round((22000 - 2200 - 1500) * 0.7, 2))
ck("R07 材料有 5 项", res["materials"]["have"], 5)
ck("R08 材料缺 5 项", len(res["materials"]["lack"]), 5)
ck_true("R09 缺「费用明细清单」", any("明细清单" in x for x in res["materials"]["lack"]))
ck("R10 硬拒 0 项", res["hard_deny"], [])
ck_true("R11 软性命中（清单未盖章）", any("清单" in x for x in res["soft_issues"]))
ck("R12 已直结", res["direct_settled"], True)
ck("R13 未走手工报销", res["manual_done"], False)
ck_true("R14 无乱码", "�" not in body)
ck_true("R15 摘要写明目录外自费", "其中：目录外自费 4800" in body)
ck_true("R16 算式写在报告里", "可报基数 = 总费用 − 目录外自费" in body)
ck_true("R17 三段话术齐全", all(k in body for k in ("书面复核结论", "工号", "行政复议")))
ck_true("R18 硬拒段没渲染成空表", "第三方责任" in body)

# 材料表必须是 5 列且不撑裂
lines = body.splitlines()
hdr = [i for i, l in enumerate(lines) if l.startswith("| # | 材料")][0]
ck("R19 材料表头 5 列", lines[hdr].count("|") - 1, 5)
cols = {l.count("|") - 1 for l in lines[hdr + 2:hdr + 12] if l.startswith("|")}
ck_true("R20 材料数据行列数不撑裂", cols <= {5})

# ---------- 4. 空输入 ----------
EMPTY = os.path.join(HERE, "空报销信息.md")
b2, r2 = rc.build_report(EMPTY, base)
ck("E01 空表 → body 为 None", b2, None)
ck_true("E02 空表 → 返回提示串", isinstance(r2, str) and "医疗总费用" in r2)

# ---------- 5. 缺比例时不硬算 ----------
tmp = os.path.join(HERE, "_noprop.md")
with open(tmp, "w", encoding="utf-8") as f:
    f.write("| 项 | 填什么 |\n|---|---|\n")
    f.write("| 医疗总费用（发票合计） | 10000 |\n")
    f.write("| 其中目录外自费 | 0 |\n")
    f.write("| 报销比例（本次适用） | 待填写 |\n")
b3, r3 = rc.build_report(tmp, base)
ck("E03 缺比例时 est=None", r3["estimate"], None)
ck_true("E04 提示补填比例", "没填「报销比例」" in (b3 or ""))
os.remove(tmp)

# ---------- 6. CLI ----------
py = sys.executable
out_md = os.path.join(HERE, "_tmpout_样例_核查报告.md")
r1 = subprocess.run([py, os.path.join(HERE, "..", "scripts", "reimburse_check.py"), SAMPLE,
                     "--base", "2026-06-10", "--out", out_md],
                    capture_output=True, text=True, encoding="utf-8")
ck("T01 样例 CLI rc=0", r1.returncode, 0)
ck_true("T02 CLI 打印 OUT", "OUT=" in (r1.stdout or ""))
ck_true("T03 产物落盘", os.path.exists(out_md))
r2b = subprocess.run([py, os.path.join(HERE, "..", "scripts", "reimburse_check.py"), EMPTY,
                      "--base", "2026-06-10", "--out", os.path.join(HERE, "_tmpout_空_核查报告.md")],
                     capture_output=True, text=True, encoding="utf-8")
ck("T04 空表 CLI rc=2", r2b.returncode, 2)
r3b = subprocess.run([py, os.path.join(HERE, "..", "scripts", "reimburse_check.py"),
                      os.path.join(HERE, "不存在.md")],
                     capture_output=True, text=True, encoding="utf-8")
ck("T05 文件不存在 rc=2", r3b.returncode, 2)

res_txt = "== TOTAL PASS=%d FAIL=%d ==\n" % (PASS[0], len(FAIL))
for f in FAIL:
    res_txt += "  FAIL " + f + "\n"
open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8").write(res_txt)
print(res_txt)
sys.exit(0 if not FAIL else 1)
