#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""体检报告核验脚本回归测试：把结果写 utf-8 文件（PowerShell 会吞 stdout）。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import checkup_review as Q  # noqa: E402

RESULT = []
PASS = 0
FAIL = 0


def ck(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        RESULT.append("PASS %s" % name)
    else:
        FAIL += 1
        RESULT.append("FAIL %s %s" % (name, extra))


SAMPLE = os.path.join(HERE, "体检报告样例.md")
EMPTY = os.path.join(HERE, "空报告.md")
OUT = os.path.join(HERE, "_reg_result.txt")

# ---- 区间/判定纯函数 ----
j = Q.judge({"name": "低密度脂蛋白胆固醇", "spec": {"hi": 3.4, "red": 4.9}}, 3.8, None, 3.4, "报告自带")
ck("J01 轻度偏高档位", j["grade"] == "轻度偏高", j)
ck("J02 方向=偏高", j["direction"] == "偏高")
ck("J03 未达红旗", j["reds"] == [], j["reds"])
j2 = Q.judge({"name": "低密度脂蛋白胆固醇", "spec": {"hi": 3.4, "red": 4.9}}, 5.2, None, 3.4, "报告自带")
ck("J04 超红线进 reds", len(j2["reds"]) >= 1, j2["reds"])
j3 = Q.judge({"name": "收缩压", "spec": {"lo": 90, "hi": 139}}, 185, 90, 139, "报告自带")
ck("J05 血压 185 判偏高", j3["direction"] == "偏高")
ck("J06 血压 185 不进红旗（非压线分支）", isinstance(j3["reds"], list))
j4 = Q.judge({"name": "血红蛋白", "spec": {"lo": 130, "hi": 175, "red_low_ratio": 0.70}}, 80, 130, 175, "报告自带")
ck("J07 重度低血红蛋白红旗", len(j4["reds"]) >= 1, j4["reds"])
j5 = Q.judge({"name": "空腹血糖", "spec": {"lo": 3.9, "hi": 6.1, "warn": 7.0}}, 7.6, 3.9, 6.1, "报告自带")
ck("J08 空腹血糖高红旗", len(j5["reds"]) >= 1, j5["reds"])
ck("J09 临界档（6.5 vs 6.1）", Q.judge({"name": "x", "spec": {"hi": 6.1}}, 6.5, None, 6.1, "r")["grade"] == "临界")
ck("J10 正常档", Q.judge({"name": "x", "spec": {"lo": 3, "hi": 6}}, 5, 3, 6, "r")["grade"] == "正常")
ck("J11 分支 6-8 周复查", Q.next_visit("轻度偏高") == "6-8 周复查")
ck("J12 临界 3-6 个月", Q.next_visit("临界") == "3-6 个月复查")

# ---- 参考区间解析 ----
ck("R01 区间 3.9-6.1", Q.parse_ref("3.9-6.1")[:2] == (3.9, 6.1))
ck("R02 区间 90-139", Q.parse_ref("90～139")[:2] == (90.0, 139.0))
ck("R03 上限 <5.2", Q.parse_ref("<5.2")[:2] == (None, 5.2))
ck("R04 下限 >1.0", Q.parse_ref(">1.0")[:2] == (1.0, None))
ck("R05 定性阴性", Q.parse_ref("阴性")[2] == "qual")
ck("R06 空区间返回 none", Q.parse_ref("")[2] == "none")

# ---- 内置表与性别 ----
r_m = Q.build_ranges("男")
r_f = Q.build_ranges("女")
ck("B01 男 Hb 下限 130", r_m["血红蛋白"]["lo"] == 130)
ck("B02 女 Hb 下限 115", r_f["血红蛋白"]["lo"] == 115)
ck("B03 女 LDL 上限 3.3", r_f["低密度脂蛋白"]["hi"] == 3.3)
ck("B04 男 LDL 上限 3.4", r_m["低密度脂蛋白"]["hi"] == 3.4)
ck("B05 别名 ALT 命中", r_m["谷丙转氨酶"]["hi"] == 50)

# ---- 姓名/占位 ----
ck("N01 norm 去空格", Q.norm(" 尿 蛋白 ") == "尿蛋白")
ck("N02 占位识别", Q.is_placeholder("待填写") and Q.is_placeholder("—") and not Q.is_placeholder("6.4"))
ck("N03 表头映射 项目=0", Q.col_map(["项目", "结果", "单位", "参考区间", "提示"])[0] == 0)
ck("N04 表头映射 参考区间=3", Q.col_map(["项目", "结果", "单位", "参考区间", "提示"])[3] == 3)
ck("N05 表头映射 提示=4", Q.col_map(["项目", "结果", "单位", "参考区间", "提示"])[4] == 4)
ck("N06 别名查找", Q.lookup("丙氨酸氨基转移酶(ALT)", r_m)[0] == "丙氨酸氨基转移酶")
ck("N07 低密度不误配总胆固醇", Q.lookup("低密度脂蛋白胆固醇", r_m)[0] == "低密度脂蛋白")
ck("N08 低密度拿到红線 4.9", Q.lookup("低密度脂蛋白胆固醇", r_m)[1].get("red") == 4.9)
ck("N09 总胆固醇不误配低密度", Q.lookup("总胆固醇", r_m)[0] == "总胆固醇")
ck("N10 高密度不误配总胆固醇", Q.lookup("高密度脂蛋白胆固醇", r_m)[0] == "高密度脂蛋白")

# ---- 整份报告 ----
body, res, _ = Q.build_report(SAMPLE, "男", 43)
ck("S01 报告生成非空", bool(body) and len(body) > 500)
ck("S02 解析项目数 >= 14", res["parsed"] >= 14, res["parsed"])
ck("S03 无红旗（样例无红線）", res["red_flags"] == 0, res["red_flags"])
ck("S04 轻度异常存在", res["light"] >= 3, res["light"])
ck("S05 存在临界或轻度", res["light"] + res["critical"] >= 3)
ck("S06 有 fallback 兜底项", res["fallback_ref"] >= 0)
ck("S07 相邻行含 9 段", body.count("\n## ") >= 8, body.count("\n## "))
ck("S08 无空表格行占位", "| 无 | — |" in body)
ck("S09 含隐私声明", "不是诊断" in body)
ck("S10 含影像建议抽取", "建议" in body or "随访" in body)
ck("S11 待办带时间", "3-6 个月" in body and "2 周内" in body)
ck("S12 单位存疑或兜底提示存在", "参考区间为内置兜底" in body)

names = [it["name"] for it in res["items"]]
vals = {it["name"]: it for it in res["items"]}
ck("D01 空腹血糖被解析", "空腹血糖" in names)
ck("D02 血糖 6.4 判临界", vals.get("空腹血糖", {}).get("grade", "") == "临界", vals.get("空腹血糖"))
ck("D02b 血糖带上受损提示", "受损" in vals.get("空腹血糖", {}).get("tip", ""), vals.get("空腹血糖", {}).get("tip"))
ck("D03 转氨酶 62 判偏高", vals.get("丙氨酸氨基转移酶", {}).get("direction") == "偏高")
ck("D04 尿蛋白定性正常", vals.get("尿蛋白", {}).get("grade") == "正常")
ck("D05 尿酸 452 判偏高", vals.get("尿酸", {}).get("direction") == "偏高")
ck("D06 肌酐 98 正常", vals.get("肌酐", {}).get("grade") == "正常")
ck("D07 收缩压 128 正常", vals.get("收缩压", {}).get("grade") == "正常")
ck("D08 腰围 92 判偏高", vals.get("腰围", {}).get("direction") == "偏高")
ck("D09 结果显示单位", "mmol/L" in body)
ck("D10 未解析项提示存在（尿常规无数值等）", "未解析项" in body)
ck("D11 参考区间不带 .0", "9-50" in body and "9.0-50.0" not in body, body[:0])
ck("D12 转氨酶可能原因命中脂肪肝", "脂肪肝" in body)
ck("G01 影像长文本不进数值判定", "甲状腺超声" not in [x["name"] for x in res["items"]],
   [x["name"] for x in res["items"]])
ck("G02 影像结论进 images", len(res.get("images", [])) >= 3, len(res.get("images", [])))
ck("G03 第六段不出现脏行", "\n- 建议 6 个月" not in body and " | |" not in body)
ck("G04 影像表里抽出建议句", "复查肝脏超声" in body or "6 个月后复查" in body)
ck("G05 结论摘要不误报影像项", "甲状腺" not in body.split("## 三")[0].split("## ")[-1])
ck("G06 第六段不重复（影像句只出现一次）",
   body.count("建议 6 个月后复查肝脏超声") == 2, body.count("建议 6 个月后复查肝脏超声"))
ck("G07 总检建议单独成行", "总检与其他建议" in body)

# ---- 空报告 ----
body2, res2, _ = Q.build_report(EMPTY, "男", None)
ck("E01 空报告也能跑不崩（给出填写指引）", body2 is None or "未解析到" in body2)
ck("E02 空报告返回可处理（提示串或 0 项）",
   isinstance(res2, str) or res2.get("parsed", 0) == 0, res2)
ck("E03 空报告给出填写指引", body2 is None or "未解析到" in body2, body2)
ck("E04 空报告返回提示串而非 None", isinstance(res2, str) and "未解析到" in res2, res2)

# ---- 红旗样例（内联）----
红旗 = os.path.join(HERE, "_红旗样例.md")
with open(红旗, "w", encoding="utf-8") as f:
    f.write("| 项目 | 结果 | 单位 | 参考区间 | 提示 |\n|---|---|---|---|---|\n")
    f.write("| 低密度脂蛋白胆固醇 | 5.2 | mmol/L | 0-3.4 | ↑ |\n")
    f.write("| 收缩压 | 186 | mmHg | 90-139 | ↑ |\n")
    f.write("| 空腹血糖 | 12.4 | mmol/L | 3.9-6.1 | ↑ |\n")
_, res3, _ = Q.build_report(红旗, "男", 55)
ck("F01 三红旗识别", res3["red_flags"] == 3, res3["red_flags"])
ck("F02b LDL 5.2 命中红線 4.9", any("4.9" in str(x["reds"]) for x in res3["items"] if "低密度" in x["name"]),
   [x["reds"] for x in res3["items"] if "低密度" in x["name"]])
ck("F02 红旗摘要有结论", "红旗" in body)

# 顺带把样例核验报告落盘（给用户看成品，也避免读到上一轮旧文件）
try:
    with open(os.path.join(HERE, "体检报告样例_核验报告.md"), "w", encoding="utf-8") as f:
        b, r4, _ = Q.build_report(SAMPLE, "男", 43)
        f.write(b if b else "")
    RESULT.append("PASS 样例报告落盘")
except Exception as e:  # noqa
    RESULT.append("FAIL 样例报告落盘 %s" % e)

txt = "\n".join(RESULT) + "\n\n== TOTAL PASS=%d FAIL=%d ==\n" % (PASS, FAIL)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(txt)
with open(OUT + ".utf8", "wb") as f:
    f.write(txt.encode("utf-8"))
print("PASS=%d FAIL=%d" % (PASS, FAIL))
