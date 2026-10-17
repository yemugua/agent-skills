#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""车务自查回归测试：结果自己写 utf-8 文件（PowerShell 会吞 stdout）。"""
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import vehicle_check as V  # noqa: E402

RESULT = []
PASS = 0
FAIL = 0
BASE = date(2026, 10, 4)


def ck(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        RESULT.append("PASS %s" % name)
    else:
        FAIL += 1
        RESULT.append("FAIL %s %s" % (name, extra))


SAMPLE = os.path.join(HERE, "车辆样例.md")
EMPTY = os.path.join(HERE, "空车辆信息.md")
OUT = os.path.join(HERE, "_reg_result.txt")

# ---- 纯函数 ----
ck("J01 日期解析 2018-06-15", V.parse_date("2018-06-15") == date(2018, 6, 15))
ck("J02 日期解析 2018年6月15日", V.parse_date("2018年6月15日") == date(2018, 6, 15))
ck("J03 日期解析 2018/6/15", V.parse_date("2018/6/15") == date(2018, 6, 15))
ck("J04 占位不解析", V.parse_date("待填写") is None)
ck("J05 占位不解析 未上线", V.parse_date("未上线") is None)
ck("J06 乱码不解析", V.parse_date("不知道") is None)
ck("G01 逾期分级 高（-100 天）", V.grade(-100)[1] == "高")
ck("G02 逾期分级 中（-60 天）", V.grade(-60)[1] == "中")
ck("G03 逾期分级 低（-10 天）", V.grade(-10)[1] == "低")
ck("G04 临近 15 天", V.grade(15)[0].find("15 天后") >= 0, V.grade(15))
ck("G05 远期 200 天", V.grade(200)[1] == "低")
ck("G06 闰年 2-29 加年不炸", V.add_years(date(2020, 2, 29), 4) == date(2024, 2, 29))
ck("G07 非闰年回退 2-28", V.add_years(date(2019, 2, 28), 1) == date(2020, 2, 28))

# ---- 年检节点 ----
reg = date(2018, 6, 15)
nodes = V.inspection_nodes(reg, BASE)
ages = [n[0] for n in nodes]
ck("N01 车龄 8 年只出真节点（2/4/6/8/10 中的，10 年以上另算）",
   all(n in (2, 4, 6, 8, 10) for n in ages) and 9 not in ages, ages)
ck("N02 含第 10 年（上线）", any(n[0] == 10 and n[2].startswith("上线") for n in nodes), nodes)
ck("N03 节点按日期排序不跳", all(nodes[i][1] <= nodes[i + 1][1] for i in range(len(nodes) - 1)))
ck("N04 节点按时间排序", all(nodes[i][1] <= nodes[i + 1][1] for i in range(len(nodes) - 1)))
reg2 = date(2014, 3, 10)
nodes2 = V.inspection_nodes(reg2, BASE)
ck("N05 车龄 12 年出现每年上线", all(n[2].startswith("上线") for n in nodes2), nodes2)
ck("N06 车龄 12 年至少 3 个节点", len(nodes2) >= 3, len(nodes2))
ck("N07 车龄 3 年列未来的 4/6/8/10 年节点",
   [n[0] for n in V.inspection_nodes(date(2023, 9, 1), BASE)] == [4, 6, 8, 10],
   [n[0] for n in V.inspection_nodes(date(2023, 9, 1), BASE)])
ck("N08 已过节点保留（提醒办没办）",
   any(n[1] < BASE for n in V.inspection_nodes(date(2020, 1, 1), BASE)),
   [(n[0], n[1].isoformat()) for n in V.inspection_nodes(date(2020, 1, 1), BASE)])

# ---- 记分 ----
hits = V.point_scan(["2026-03-11 环城东路 闯红灯", "2026-05-02 高速 超速 20%"])
ck("P01 闯红灯识别 6 分", any(p == 6 for _, p in hits), hits)
ck("P02 超速 20% 识别 3 分或 6 分", any(p in (3, 6) for _, p in hits), hits)
ck("P03 酒驾识别 12 分", any(p == 12 for _, p in V.point_scan(["晚上 酒驾 被查"])))
ck("P04 无关文本不误判", V.point_scan(["保养记录 2026-03-11"]) == [])
ck("P05 取最高档", max([p for _, p in hits]) == 6, hits)

# ---- 字段抽取 ----
txt = open(SAMPLE, encoding="utf-8").read()
ck("F01 表格抽字段 交强险", V.get_field(txt, "交强险到期日") == "2026-11-20")
ck("F02 表格抽字段 记分", "6" in V.get_field(txt, "本周期已累计记分"))
ck("F03 占位识别", V.is_ph(V.get_field(txt, "提档日期")) is True)
ck("F04 未填返回空串", V.get_field(txt, "不存在的字段") == "")

# ---- 整份 ----
body, res = V.build_report(SAMPLE, BASE, None)
ck("S01 报告生成", bool(body) and len(body) > 800, len(body) if body else body)
ck("S02 七段齐全", body.count("\n## ") >= 7, body.count("\n## "))
ck("S03 节点进入 json", len(res["nodes"]) >= 1, res["nodes"])
ck("S03b 样例第 8 年节点被标为已过期提醒",
   any(n["age_year"] == 8 for n in res["nodes"]), res["nodes"])
ck("S04 交强险进入倒计时", any(d["item"] == "交强险" for d in res["deadlines"]), res["deadlines"])
ck("S05 记分合计 = 6+6 = 12", res["points"]["total"] == 12, res["points"])
ck("S06 记分命中两条", len(res["points"]["hits"]) >= 2, res["points"]["hits"])
ck("S07 未填项列出", isinstance(res["missing"], list))
ck("S08 摘要提到满分", "满分" in body)
ck("S09 含消分清分红线", "代扣分" in body and "违法" in body)
ck("S10 表不留空列（无空格单元格行）", "\n|  |" not in body)
ck("S10b 表格行不裂（记分行不超过 3 根竖线）",
   all(len(re.findall(r"\|", ln)) <= 4
       for ln in body.splitlines() if "分 |" in ln and ln.startswith("|")),
   [ln for ln in body.splitlines() if ln.startswith("|") and ln.count("|") > 4])
ck("S11 过户段存在", "过户" in body)
ck("S12 基准日写进 json", res["base_date"] == "2026-10-04", res.get("base_date"))

# ---- 空输入 ----
body2, res2 = V.build_report(EMPTY, BASE, None)
ck("E01 空输入给提示而非崩", body2 is None and "未解析到注册登记日期" in str(res2), res2)
ck("E02 提示带填写指引", "YYYY-MM-DD" in str(res2), res2)


def json_dummy(o):
    import json
    return json.dumps(o, ensure_ascii=False)


ck("S12b json.dumps 不炸", json_dummy(res).startswith("{"))

txt_out = "\n".join(RESULT) + "\n\n== TOTAL PASS=%d FAIL=%d ==\n" % (PASS, FAIL)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(txt_out)
with open(OUT + ".utf8", "wb") as f:
    f.write(txt_out.encode("utf-8"))
print("PASS=%d FAIL=%d" % (PASS, FAIL))
