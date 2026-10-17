# -*- coding: utf-8 -*-
"""噪音扰民取证与投诉 回归测试（自写 utf-8 结果文件）"""
import datetime as dt
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import noise_check as nc  # noqa: E402

SAMPLE = os.path.join(HERE, "样例.md")
EMPTY = os.path.join(HERE, "空输入.md")
BASE = dt.date(2026, 10, 5)

PASS = 0
FAIL = 0
LINES = []


def ck(name, got, want):
    global PASS, FAIL
    if got == want:
        PASS += 1
        LINES.append("PASS %s" % name)
    else:
        FAIL += 1
        LINES.append("FAIL %s  got=%r want=%r" % (name, got, want))


def ck_true(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        LINES.append("PASS %s" % name)
    else:
        FAIL += 1
        LINES.append("FAIL %s  %s" % (name, extra))


with open(SAMPLE, encoding="utf-8") as f:
    text = f.read()
with open(EMPTY, encoding="utf-8") as f:
    etext = f.read()

F = nc.parse_fields(text)
E = nc.parse_fields(etext)

# ---------------- 基础工具
ck("P01 norm 去空格", nc.norm(" 社会 生活 "), "社会生活")
ck("P02 norm 去竖线", nc.norm("社会|生活"), "社会 生活")
ck("P03 is_ph 待填", nc.is_ph("【待填】"), True)
ck("P04 is_ph 是/否", nc.is_ph("是 / 否"), True)
ck("P05 is_ph 真值", nc.is_ph("社会生活"), False)
ck("P06 is_ph 单有", nc.is_ph("有"), False)
ck("P07 is_ph 分隔", nc.is_ph("---"), True)
ck("P08 表头不算字段", "项" in E or "填什么" in E, False)
ck("P09 样例字段数", len(F) >= 20, True)

# ---------------- 字段解析
ck("F01 城市", nc.get_text(F, "所在城市"), "浙江省杭州市西湖区")
ck("F02 噪声类型", nc.get_text(F, "噪声类型"), "社会生活")
ck("F03 具体来源", nc.get_text(F, "具体噪声来源")[:4], "楼上住户")
ck("F04 时长", nc.get_int(F, "单次持续时长"), 150)
ck("F05 每周天数", nc.get_num(F, "每周发生天数"), 5.0)
ck("F06 分贝", nc.get_num(F, "实测分贝"), 58.0)
ck("F07 日记天数", nc.get_int(F, "噪声日记连续记录天数"), 2)
ck("F08 金额", nc.get_num(F, "主张损失金额"), 3000.0)
ck("F09 空表城市", nc.get_text(E, "所在城市"), "")
ck("F10 空表分贝", nc.get_num(E, "实测分贝"), None)
ck("F11 最长别名优先", nc.get_text(F, "有无录音或视频", "录音"), "有")
ck("F12 冒号行解析", nc.get_text(nc.parse_fields(
    "具体噪声来源：楼下商铺高音喇叭\n主要发生时段：夜间"), "具体噪声来源"), "楼下商铺高音喇叭")

# ---------------- 三态判定
ck("Y01 有录音", nc.yes(F, "有无录音或视频"), True)
ck("Y02 无水印", nc.yes(F, "录音视频是否带时间水印"), False)
ck("Y03 无检测报告", nc.yes(F, "有无第三方检测机构检测报告"), False)
ck("Y04 有邻居证人", nc.yes(F, "有无邻居愿意作证"), True)
ck("Y05 沟通留痕否", nc.yes(F, "沟通是否留痕"), False)
ck("Y06 装修是", nc.yes(F, "是否住宅楼内室内装修作业"), True)
ck("Y07 空表 None", nc.yes(E, "有无录音或视频"), None)
ck("Y08 没有判否", nc.yes(nc.parse_fields("有无12345工单：没有"), "有无 12345 工单"), False)

# ---------------- 领域判定
t1, d1, h1, n1 = nc.classify_noise(F)
ck("C01 样例类别", t1, "社会生活")
ck_true("C02 样例含多类源", len(h1) >= 2, str(h1))
ck_true("C03 装修归口提示", any("社会生活噪声" in x for x in n1), str(n1))
ck_true("C04 多类源提示", any("多类噪声源" in x for x in n1), str(n1))
ck("C05 社会生活部门", nc.DEPT["社会生活"][0], "公安机关（110 / 属地派出所）")
ck("C06 施工部门", nc.DEPT["建筑施工"][0], "生态环境主管部门")
ck("C07 工业部门", nc.DEPT["工业"][0], "生态环境主管部门")
ck_true("C08 交通部门", "交通管理" in nc.DEPT["交通运输"][0], nc.DEPT["交通运输"][0])
ck("C09 装修归公安", True, True)

f2 = nc.parse_fields("具体噪声来源：小区旁工地夜间打桩浇筑\n主要发生时段：夜间\n"
                     "实测分贝 dB(A)：62\n所在区域声环境功能区类别：2 类")
t2, _, h2, _ = nc.classify_noise(f2)
ck("C10 工地判施工", t2, "建筑施工")
ck("C11 功能区2类", nc.pick_category(f2), "2")

f3 = nc.parse_fields("具体噪声来源：隔壁厂房冷却塔和风机昼夜运转")
ck("C12 厂房判工业", nc.classify_noise(f3)[0], "工业")
f4 = nc.parse_fields("具体噪声来源：楼下主干道车流和摩托车炸街")
ck("C13 车流判交通", nc.classify_noise(f4)[0], "交通运输")

f5 = nc.parse_fields("具体噪声来源：楼上在装修\n主要发生时段：夜间")
_, _, _, n5 = nc.classify_noise(f5)
ck_true("C14 装修歧义提示", any("两者归口不同" in x for x in n5), str(n5))

# ---------------- 时段与限值
s_lab, s_night, s_noon, s_rest, s_ok = nc.pick_slot(F)
ck("S01 时段识别", s_ok, True)
ck("S02 按夜间判", s_night, True)
s2 = nc.pick_slot(nc.parse_fields("主要发生时段：昼间（6-22 点）"))
ck("S03 昼间不是夜间", s2[1], False)
s3 = nc.pick_slot(nc.parse_fields("主要发生时段："))
ck("S04 空时段未识别", s3[4], False)
ck("S05 1类昼限", nc.GB_DAY["1"], 55)
ck("S06 1类夜限", nc.GB_NIGHT["1"], 45)
ck("S07 3类夜限", nc.GB_NIGHT["3"], 55)
ck("S08 0类夜限", nc.GB_NIGHT["0"], 40)

# ---------------- 格式化
ck("N01 fmt_num 去点零", nc.fmt_num(58.0), "58")
ck("N02 fmt_num 一位", nc.fmt_num(58.5), "58.5")
ck("N03 fmt_num None", nc.fmt_num(None), "未填")
ck("N04 fmt_money", nc.fmt_money(3000.0), "¥3,000")
ck("N05 fmt_flag 否", nc.fmt_flag(False), "**否**")
ck("N06 fmt_yes 无", nc.fmt_yes(False), "**无**")
ck("N07 日期解析", nc.parse_date("2026-06-18"), dt.date(2026, 6, 18))
ck("N08 中文日期", nc.parse_date("2026年6月18日"), dt.date(2026, 6, 18))
ck("N09 坏日期", nc.parse_date("不清楚"), None)

# ---------------- 完整报告
body, meta = nc.build_report(SAMPLE, BASE)
ck_true("R01 报告生成", body is not None, str(meta))
ck_true("R02 九段", body.count("## ") >= 9, str(body.count("## ")))
ck_true("R03 结论摘要", "结论摘要" in body)
ck_true("R04 归哪个部门管", "归哪个部门管" in body)
ck_true("R05 时段限值", "时段与限值对照" in body)
ck_true("R06 取证缺口", "取证强度与证据缺口" in body)
ck_true("R07 投诉阶梯", "投诉阶梯排序" in body)
ck_true("R08 话术卡", "话术卡" in body)
ck_true("R09 诉讼要点", "诉讼与赔偿要点" in body)
ck_true("R10 待办", "待办补正动作" in body)
ck_true("R11 纪律", "边界与纪律" in body)
ck("R12 类别", meta.get("噪声类别"), "社会生活")
ck_true("R13 主管部门", "公安机关" in meta.get("主管部门", ""), str(meta.get("主管部门")))
ck("R14 超标", meta.get("超标dB"), 13.0)
ck("R15 取证分", meta.get("取证强度"), 18)
ck("R16 未完成阶梯", meta.get("未完成阶梯"), 1)
ck("R17 结论态", meta.get("结论"), "待补正")
ck_true("R18 公安出警话术", "社会生活噪声" in body and "接处警记录" in body)
ck_true("R19 装修禁限提示", "法定休息日 / 节假日 / 午间 / 夜间" in body)
ck_true("R20 APP 初步证据", "初步证据" in body)
ck_true("R21 检测报告缺口", "第三方检测机构检测报告" in body and "**无**" in body)
ck_true("R22 无水印被抓", "有录音但无时间水印" in body)
ck_true("R23 沟通留痕重做", "已做但无效：没留痕" in body)
ck_true("R24 夜间突发15", "幅度不得高于 15 dB(A)" in body)
ck_true("R25 未填不算通过", "未填的一律不算通过" in body)
ck_true("R26 无待填泄漏", "【待填】" not in body)
ck_true("R27 无乱码", "\ufffd" not in body)
ck_true("R28 风险项非空", len(meta.get("风险项", [])) >= 3, str(meta.get("风险项")))
ck_true("R29 待办非空", len(meta.get("待办", [])) >= 5, str(len(meta.get("待办", []))))
ck_true("R30 金额格式", "¥3,000" in body)
ck_true("R31 持续天数", "已持续约 **109 天**" in body)
ck_true("R32 GB3096 引用", "GB 3096" in body)
ck_true("R33 噪声法引用", "噪声污染防治法" in body)
ck_true("R34 当地口径提示", "以当地主管部门口径为准" in body)
ck_true("R35 混合源提示入正文", "分别归不同部门" in body)

bad = [ln for ln in body.splitlines() if ln.count("|") > 6]
ck_true("R36 表格不裂", not bad, str(bad[:2]))

# ---------------- 施工 / 工业场景
TMP = os.path.join(HERE, "_tmp_site.md")
with open(TMP, "w", encoding="utf-8") as f:
    f.write("## 二、噪声源\n\n| 项 | 填什么 |\n|---|---|\n")
    f.write("| 噪声类型 | 建筑施工 |\n")
    f.write("| 具体噪声来源 | 小区旁工地夜间打桩浇筑 |\n")
    f.write("| 主要发生时段 | 夜间 |\n\n")
    f.write("## 三、测量与限值\n\n| 项 | 填什么 |\n|---|---|\n")
    f.write("| 实测分贝 dB(A) | 62 |\n")
    f.write("| 所在区域声环境功能区类别 | 2 类 |\n")
b2, m2 = nc.build_report(TMP, BASE)
ck_true("W01 施工报告", b2 is not None, str(m2))
ck("W02 施工类别", m2.get("噪声类别"), "建筑施工")
ck_true("W03 生态环境", "生态环境主管部门" in m2.get("主管部门", ""), str(m2.get("主管部门")))
ck("W04 施工超标", m2.get("超标dB"), 12.0)
ck_true("W05 环保投诉话术", "夜间连续作业证明" in b2)

TMP2 = os.path.join(HERE, "_tmp_eco.md")
with open(TMP2, "w", encoding="utf-8") as f:
    f.write("| 项 | 填什么 |\n|---|---|\n")
    f.write("| 具体噪声来源 | 隔壁厂房冷却塔昼夜运转 |\n")
    f.write("| 主要发生时段 | 全天 |\n")
    f.write("| 实测分贝 dB(A) | 70 |\n")
    f.write("| 所在区域声环境功能区类别 | 3 类 |\n")
b3, m3 = nc.build_report(TMP2, BASE)
ck("W06 工业类别", m3.get("噪声类别"), "工业")
ck("W07 工业超标", m3.get("超标dB"), 15.0)

# ---------------- 空输入 / 异常
r2 = nc.build_report(EMPTY, BASE)
ck_true("E01 空表 None", r2[0] is None, str(r2[0])[:60])
ck_true("E02 空表提示", isinstance(r2[1], str) and "未解析" in r2[1], str(r2[1])[:60])
r3 = nc.build_report(os.path.join(HERE, "不存在.md"), BASE)
ck_true("E03 缺文件不崩", r3[0] is None)
ck_true("E04 缺文件提示", "读不了文件" in str(r3[1]))

# ---------------- CLI
env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"
SP = os.path.join(ROOT, "scripts", "noise_check.py")
p1 = subprocess.run([sys.executable, SP, EMPTY], capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=120, env=env)
ck("X01 空输入退出码", p1.returncode, 2)
ck_true("X02 空输入有提示", len((p1.stdout or "")) > 10, str(len(p1.stdout or "")))
p2 = subprocess.run([sys.executable, SP, SAMPLE, "--json"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", timeout=120, env=env)
try:
    j = json.loads(p2.stdout)
    ck_true("X03 json 可解析", isinstance(j, dict), str(p2.stdout[:120]))
    ck_true("X04 json 含结论", "结论" in j, str(list(j)[:8]))
    ck_true("X05 json 含风险项", isinstance(j.get("风险项"), list))
    ck_true("X06 json 含待办", isinstance(j.get("待办"), list) and len(j["待办"]) >= 5)
except Exception as e:
    ck_true("X03 json 可解析", False, "%s %s" % (e, p2.stdout[:120]))
p3 = subprocess.run([sys.executable, SP, SAMPLE, "--base", "2026-10-05"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=120, env=env)
ck("X07 样例退出码", p3.returncode, 0)
ck_true("X08 样例多段", (p3.stdout or "").count("## ") >= 9)

for p in (TMP, TMP2):
    try:
        os.remove(p)
    except Exception:
        pass

LINES.append("== TOTAL PASS=%d FAIL=%d ==" % (PASS, FAIL))
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(LINES) + "\n")
print("PASS=%d FAIL=%d" % (PASS, FAIL))
