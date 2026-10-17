# -*- coding: utf-8 -*-
"""装修报价核查技能回归测试。结果自己写 _reg_result.txt（PowerShell 管道会二次编码）。"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import quote_check as qc  # noqa: E402

SAMPLE = os.path.join(HERE, "装修报价样例.md")
EMPTY = os.path.join(HERE, "空报价信息.md")
lines = []
npass = 0
nfail = 0


def ck(name, got, want):
    global npass, nfail
    ok = (got == want)
    if ok:
        npass += 1
    else:
        nfail += 1
    lines.append("%s %-46s got=%r want=%r" % ("PASS" if ok else "FAIL", name, got, want))


def ck_true(name, cond, extra=""):
    global npass, nfail
    if cond:
        npass += 1
    else:
        nfail += 1
    lines.append("%s %-46s %s" % ("PASS" if cond else "FAIL", name, extra))


# ---------------- 工具函数
ck("U01 parse_money 纯数字", qc.parse_money("5000"), 5000.0)
ck("U02 parse_money 带千分位", qc.parse_money("96,800"), 96800.0)
ck("U03 parse_money 带元", qc.parse_money("8800元"), 8800.0)
ck("U04 parse_money 万", qc.parse_money("1.2万"), 12000.0)
ck("U05 parse_money 空", qc.parse_money("无"), None)
ck("U06 parse_pct", qc.parse_pct("60%"), 60.0)
ck("U07 parse_pct 带全角", qc.parse_pct("60％"), 60.0)
ck("U08 parse_pct 越界", qc.parse_pct("180%"), None)
ck("U09 fmt_money 整数", qc.fmt_money(96800.0), "96800")
ck("U10 fmt_money 小数", qc.fmt_money(1234.5), "1234.5")
ck("U11 fmt_money None", qc.fmt_money(None), "—")
ck("U12 norm 全角转半角", qc.norm("ＡＢＣ"), "abc")
ck("U13 is_placeholder 空", qc.is_placeholder(""), True)
ck("U14 is_placeholder 填什么", qc.is_placeholder("填什么"), True)
ck("U15 is_placeholder 有无", qc.is_placeholder("有 / 无"), True)
ck("U16 is_placeholder 正常值", qc.is_placeholder("60"), False)
ck("U17 is_sep 分隔行", qc.is_sep(qc.split_row("|---|---|")), True)
ck_true("U18 is_sep 非分隔", not qc.is_sep(qc.split_row("| 项目 | 金额 |")))

# ---------------- 表格解析
ck("T01 split_row", qc.split_row("| 拆除费 | 6800 |"), ["拆除费", "6800"])
ck("T02 col_index 命中", qc.col_index(["项目名称", "金额（元）"], ("金额",)), 1)
ck("T03 col_index 未命中", qc.col_index(["a", "b"], ("金额",)), None)

# ---------------- 样例解析
text = open(SAMPLE, encoding="utf-8").read()
items = qc.parse_quote_items(text)
ck_true("S01 抓到报价条目", len(items) >= 10, "n=%d" % len(items))
ck_true("S02 条目含金额", any(i["amount"] for i in items))
names = [i["name"] for i in items]
ck_true("S03 有水电改造项", any("水电" in n for n in names), str(names[:5]))
ck_true("S04 有防水项", any("防水" in n for n in names))
ck_true("S05 工程量列被抓到", any(i["qty"] for i in items))

total = qc.find_field(text, ("报价单总价", "总价"), "money")
ck("S06 总价解析", total, 96800.0)
mode = qc.find_field(text, ("装修方式",))
ck("S07 装修方式", mode, "半包")
days = qc.find_field(text, ("对方给的工期", "工期"), "int")
ck("S08 工期", days, 75)
rooms = qc.find_field(text, ("套内实测面积", "建筑面积", "房屋面积"), "int")
ck("S09 面积取第一个（89）", rooms, 89)

# 九项必看：样例缺 拆除费（报价条目里没有"拆除"）
req = qc.check_required(text, items)
d = dict(req)
ck("S10 九项必看共 9 项", len(req), 9)
ck_true("S11 缺拆除费", d.get("拆除费") is False)
ck_true("S12 有防水", d.get("防水") is True)
ck_true("S12b 有瓦工（地砖铺贴也算）", d.get("瓦工") is True, str(d))
ck_true("S12c 缺工期与付款节点", d.get("工期与付款节点") is False, str(d))

# 可疑表述：样例含"按实际结算""不含""按市价"
susp = qc.scan_suspicious(items, text)
ck_true("S13 命中可疑表述", len(susp) >= 3, "n=%d" % len(susp))
tags = set(x[1] for x in susp)
ck_true("S14 含按实际", "按实际结算" in tags, str(tags))
ck_true("S15 含不含", "不含" in tags, str(tags))

# 付款
pay_rows, early, allin, tail = qc.check_payment(text)
ck_true("S16 付款行抓到", len(pay_rows) >= 3, str(pay_rows))
ck("S17 开工前付比例", early, 60.0)
ck("S18 一次付清", allin, False)
ck("S19 有尾款", tail, True)

# 增项
already, stated, oral = qc.check_extra(text)
ck_true("S20 抓到已发生增项", len(already) == 1, str(already))
ck_true("S20b 已发生增项不含问句", all("口头说" not in x for x in already), str(already))
ck_true("S20c 抓到另计声明", len(stated) == 2, str(stated))
ck("S21 口头增项", oral, True)

# 合同
cg = qc.check_contract(text)
ck_true("S22 合同条款全判无（样例全填「无」）", len(cg) == 0, str(cg))

# ---------------- 报告
def table_cols_problems(body):
    """找出列数与表头不一致的数据行（表格撑裂的真正判据）。"""
    bad = []
    head_cols = None
    for ln in body.splitlines():
        if not ln.strip().startswith("|"):
            head_cols = None
            continue
        cells = qc.split_row(ln)
        if qc.is_sep(cells):
            continue
        n = len(cells)
        if head_cols is None:
            head_cols = n
        elif n != head_cols:
            bad.append((n, head_cols, ln[:50]))
    return bad


def table_cols_ok(body):
    return not table_cols_problems(body)


body, err, meta = qc.build_report(SAMPLE, None)
ck_true("R01 报告构建成功", body is not None and err is None, str(err))
ck_true("R02 九段齐全", body.count("## ") == 9, "sections=%d" % body.count("## "))
ck_true("R03 含摘要", "结论摘要" in body)
ck_true("R04 含三段话", "第一段" in body and "第二段" in body and "第三段" in body)
ck_true("R05 含六句话", "必须写进合同" in body)
ck_true("R06 含收手条件", "收手条件" in body)
ck_true("R07 无U盘残留", "\ufffd" not in body)
ck_true("R08 表格列数一致（各表列数自洽）", table_cols_ok(body),
        str(table_cols_problems(body)))
ck_true("R09 不写市场价", "市场价" in body)
ck_true("R10 meta 有总价", meta and meta.get("total") == 96800.0)
ck_true("R11 meta 风险数>0", meta and meta.get("risks", 0) > 0, str(meta))
ck_true("R12 合同六句多数判无", body.count("**无**") >= 5, str(body.count("**无**")))
ck_true("R13 隐蔽工程状态不出现半截模板语",
        "做没做" not in body, "found 做没做")
ck_true("R14 增项段不重复", body.count("拆除费、垃圾清运、拼花、柜子都说另计") <= 1,
        str(body.count("拆除费、垃圾清运、拼花、柜子都说另计")))

# 空表
body2, err2, meta2 = qc.build_report(EMPTY, None)
ck_true("E01 空表 -> 返回提示串", isinstance(err2, str) and "报价" in err2, str(err2))
ck_true("E02 空表 body 为 None", body2 is None)
rc = qc.main([EMPTY])
ck("E03 空表退出码", rc, 2)
rc2 = qc.main([SAMPLE, "--json"])
ck("E04 样例 json 退出码", rc2, 0)

# ---------------- 收尾
lines.append("")
lines.append("== TOTAL PASS=%d FAIL=%d ==" % (npass, nfail))
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("== TOTAL PASS=%d FAIL=%d ==" % (npass, nfail))
sys.exit(0 if nfail == 0 else 1)
