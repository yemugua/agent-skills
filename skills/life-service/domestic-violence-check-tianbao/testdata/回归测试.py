# -*- coding: utf-8 -*-
"""家庭暴力取证核查脚本回归测试（断言 52 条）。用 python 直接跑本文件。"""
import json
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)
import domestic_violence_check as P  # noqa: E402

PASS = []
FAIL = []


def ck(name, cond):
    (PASS if cond else FAIL).append(name)


def mk(**kw):
    base = dict(
        relation="", last_time="", narrative="", left_site="", called_110="",
        police_note="", photo="", medical="", record_reason="", recording="",
        chat="", witness="", women_fed="", community="", shelter="", counsel="",
        protection_applied="", protection_status="", protection_order="",
        legal_aid="", divorce_intent="", divorce_evidence="",
        evidence_owned="", evidence_desc="",
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
ck("norm统一冒号", P.norm("关系：夫妻") == "关系:夫妻")
ck("norm去全角括号", P.norm("（有）") == "(有)")
ck("filled空串=False", P.filled("") is False)
ck("filled斜杠提示=False", P.filled("有/无/不清楚") is False)
ck("filled有=True", P.filled("有") is True)
ck("filled待填=False", P.filled("待填") is False)
ck("filled有斜杠=False", P.filled("有/无") is False)
ck("is_yesish已", P.is_yesish("已申请") is True)
ck("is_yesish否", P.is_yesish("否") is False)
ck("yes是", P.yes("是") is True)
ck("no否", P.no("否") is True)
ck("unknown不清楚", P.unknown("不清楚") is True)
ck("unknown空", P.unknown("") is True)
ck("unknown已填", P.unknown("有") is False)
ck("has_content空", P.has_content("|") is False)
ck("has_content有值", P.has_content("报警回执|") is True)
ck("parse_num元", P.parse_num("300元") == 300.0)
ck("parse_num空", P.parse_num("") is None)
ck("fmt_num去.0", P.fmt_num(15.0) == "15")
ck("fmt_num保留小数", P.fmt_num(15.5) == "15.5")
ck("parse_date", P.parse_date("2026-09-28") == date(2026, 9, 28))
ck("parse_date空", P.parse_date("") is None)
ck("parse_date非法不抛", P.parse_date("去年") is None)
ck("base_date兜底", isinstance(P.base_date(""), date))
ck("base_date取参", P.base_date("2026-10-05") == date(2026, 10, 5))

# ---------------------------------------------------------- 解析
txt = P.read_text(os.path.join(HERE, "样例.md"))
kv = P.build_kv(txt)
ck("build_kv表格取到关系", P.get_text(kv, ["与施暴方关系"]) == "前男友（曾同居两年，半年前分手但仍有往来）")
ck("build_kv取时间", P.get_text(kv, ["最近一次发生时间"]) == "2026-09-28")
ck("build_kv取勾选", "门诊病历" in P.get_text(kv, ["已有证据勾选"]))
ck("build_kv取法律依据空", P.get_text(kv, ["是否申请法律援助"]) == "否")
kv2 = P.build_kv("与施暴方关系：夫妻\n最近一次发生时间：2026-01-05\n")
ck("build_kv冒号行", P.get_text(kv2, ["与施暴方关系"]) == "夫妻")
ck("get_text最长别名优先",
   P.get_text({"与施暴方关系": "夫妻", "关系": "同居"}, ["与施暴方关系", "关系"]) == "夫妻")
ck("get_text兜底alias", P.get_text({"所在城市": "杭州"}, ["城市"]) == "杭州")
ck("get_text未命中为空", P.get_text({"a": "b"}, ["zzz"]) == "")
ff = P.build_fields(kv)
ck("build_fields取关系", "前男友" in ff["relation"])
ck("build_fields取经过", "撞" in ff["narrative"])
ck("build_fields取照片(无)", P.no(ff["photo"]) is True)
ck("build_fields取就诊(是)", P.is_yesish(ff["medical"]) is True)

# ---------------------------------------------------------- 形态识别
ck("form_match肢体", "肢体暴力" in P.form_match("他打我、扇耳光、拽头发"))
ck("form_match精神", "精神暴力" in P.form_match("他骂我、威胁我、恐吓"))
ck("form_match控制", "控制与跟踪" in P.form_match("限制我出门、没收手机、查岗"))
ck("form_match经济", "经济控制" in P.form_match("不给我生活费、掌握工资卡"))
ck("form_match空", P.form_match("") == [])
ck("cohab夫妻", P.cohab_type("夫妻")[0] == "家庭成员（夫妻）")
ck("cohab前男友适用", P.cohab_type("前男友")[0] == "共同生活或前伴侣（非夫妻）")
ck("cohab同居适用", "同样适用" in P.cohab_type("同居")[1])
ck("cohab亲属", P.cohab_type("公婆")[0] == "家庭成员（亲属）")
ck("cohab空", P.cohab_type("")[0] == "待确认")
ck("cohab不明", P.cohab_type("同事")[0] == "待确认")

# ---------------------------------------------------------- 安全段
rows = P.checks_safety(mk(left_site="否", called_110="否", police_note="还没做"))
chk1("未脱离现场不通过", rows, "是否已脱离现场", "不通过")
chk1("未报警不通过", rows, "是否拨打 110 报警", "不通过")
ck("未报警提示回执与笔录",
   any(("回执" in m and "笔录" in m) for _n, _s, m in rows))
rows2 = P.checks_safety(mk(left_site="是", called_110="已报警", police_note="已做笔录"))
chk1("已脱离通过", rows2, "是否已脱离现场", "通过")
chk1("已报警通过", rows2, "是否拨打 110 报警", "通过")
ck("报警提示索要回执", any("回执" in m for _n, _s, m in rows2))
rows3 = P.checks_safety(mk())
chk1("安全全未填待补正", rows3, "是否已脱离现场", "待补正")
rows4 = P.checks_safety(mk(narrative="他今晚又来了，还在家里，还没离开"))
chk1("危险进行中不通过", rows4, "当前是否仍处危险中", "不通过")
ck("危险提示先脱离", any("先离开现场" in m for _n, _s, m in rows4))

# ---------------------------------------------------------- 证据段
rows5 = P.checks_evidence(mk())
chk1("证据全未填出总览", rows5, "证据总览", "待补正")
ck("总览提示逐项勾选", any("勾选" in m for _n, _s, m in rows5))
rows6 = P.checks_evidence(mk(evidence_owned="报警回执、询问笔录、伤情照片、门诊病历、诊断证明、微信记录、损坏物品、现场照片、邻居、好友"))
chk1("报警类通过", rows6, "报警类证据", "通过")
chk1("影像类有风险", rows6, "影像类证据", "有风险")
ck("缺口提示尽快补齐", any("尽快补齐" in m for _n, _s, m in rows6))

# ---------------------------------------------------------- 报警与就医段
rows7 = P.checks_medical(mk(photo="无", medical="否"))
chk1("无照片不通过", rows7, "伤情照片规范", "不通过")
chk1("未就医不通过", rows7, "就医记录", "不通过")
ck("照片提示水印原图", any("水印" in m and "原图" in m for _n, _s, m in rows7))
rows8 = P.checks_medical(mk(photo="有", medical="已", record_reason="没写"))
chk1("有照片通过", rows8, "伤情照片规范", "通过")
chk1("病历未写致伤原因", rows8, "病历致伤原因表述", "有风险")
rows9 = P.checks_medical(mk(photo="有", medical="已", record_reason="已写明"))
chk1("病历已写明通过", rows9, "病历致伤原因表述", "通过")
rows10 = P.checks_medical(mk(photo="有", medical="已"))
chk1("病历未填待补正", rows10, "病历致伤原因表述", "待补正")

# ---------------------------------------------------------- 保护令段
rows11 = P.order_apply(mk(protection_applied="未申请"))
chk1("未申请待补正", rows11, "人身安全保护令（是否已申请）", "待补正")
ck("提示法院作出", any("人民法院" in m for _n, _s, m in rows11))
ck("提示可代为申请", any("代为申请" in m for _n, _s, m in rows11))
ck("含禁止暴力请求", any("禁止实施家庭暴力" in m for _n, _s, m in rows11))
rows12 = P.order_apply(mk(protection_applied="已申请", protection_order="已"))
chk1("已申请通过", rows12, "人身安全保护令（是否已申请）", "通过")
chk1("已取得裁定通过", rows12, "是否已取得裁定书", "通过")
ck("提示公安机关协助执行", any("公安机关协助执行" in m for _n, _s, m in rows12))
rows13 = P.order_apply(mk(protection_applied="已申请", protection_order="未"))
chk1("未取得裁定有风险", rows13, "是否已取得裁定书", "有风险")

# ---------------------------------------------------------- 其他渠道
rows14 = P.checks_other(mk(women_fed="是", community="否"))
chk1("妇联已联系通过", rows14, "妇联（12338）", "通过")
chk1("居委会未联系有风险", rows14, "居委会/村委会/社区", "有风险")
ck("含12338", any("12338" in m for _n, _s, m in rows14))
rows15 = P.checks_other(mk())
ck("其他渠道全未填为待补正",
   all(r[1] == "待补正" for r in rows15) and len(rows15) == 4)

# ---------------------------------------------------------- 离婚与时效
ck("离婚未填不产出", P.checks_divorce(mk()) == [])
rows16 = P.checks_divorce(mk(divorce_intent="是"))
chk1("打算离婚通过", rows16, "离婚与损害赔偿", "通过")
ck("提示损害赔偿", any("损害赔偿" in m for _n, _s, m in rows16))
rows17 = P.checks_time(mk(last_time="2026-09-28"), date(2026, 10, 5))
chk1("时效在期内", rows17, "民事诉讼时效", "通过")
ck("时效剩1088天", any("还剩 1088 天" in m for _n, _s, m in rows17))
rows18 = P.checks_time(mk(last_time="2020-01-01"), date(2026, 10, 5))
chk1("时效已过", rows18, "民事诉讼时效", "有风险")
ck("时效已过提示", any("已过" in m for _n, _s, m in rows18))
ck("未填时间待补正", P.checks_time(mk(), date(2026, 10, 5))[0][1] == "待补正")

# ---------------------------------------------------------- 路径与待办
st = P.path_order(mk(relation="前男友"))
ck("前男友路径第0步含不受关系限制", "不受关系限制" in st[0][1])
ck("路径第1步报案", "110" in st[1][1])
ck("路径第4步保护令", "人民法院" in st[4][1])
ck("路径第5步含12338", "12338" in st[5][1])
st2 = P.path_order(mk(relation="夫妻"))
ck("夫妻路径第0步简洁", "不受关系限制" not in st2[0][1])
todo = P.todo_list(mk(called_110="否", photo="无", medical="否"), [])
ck("待办含报警并索要回执", any(n == "报警并索要回执" for n, _s in todo))
ck("待办含拍伤情照片", any(n == "拍伤情照片" for n, _s in todo))
ck("待办含拨打12338", any(n == "拨打 12338" for n, _s in todo))
ck("待办含准备保护令申请", any(n == "准备保护令申请" for n, _s in todo))

# ---------------------------------------------------------- 端到端
sp = os.path.join(SCRIPTS, "domestic_violence_check.py")
env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"
sample = os.path.join(HERE, "样例.md")
empty = os.path.join(HERE, "空家庭暴力信息.md")
r1 = subprocess.run([sys.executable, sp, sample, "--base", "2026-10-05"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
ck("样例rc=0", r1.returncode == 0)
o1 = r1.stdout or ""
ck("样例含结论摘要", "一、结论摘要" in o1)
ck("样例含待办段", "十一、待办补正动作" in o1)
ck("样例含九段以上", o1.count("## ") >= 9)
ck("样例含不通过", "不通过" in o1)
ck("样例含边界与纪律", "边界与纪律" in o1)
ck("样例含证据缺口速查", "十、证据缺口速查" in o1)
ck("样例含安全段", "三、安全优先级动作" in o1)
ck("样例含保护令段", "六、人身安全保护令申请路径与材料" in o1)
ck("样例含12338", "12338" in o1)
ck("样例含人民法院", "人民法院" in o1)
r2 = subprocess.run([sys.executable, sp, sample, "--json"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
try:
    d = json.loads(r2.stdout or "{}")
    ck("json可解析含结论", "结论" in d and "待办" in d)
    ck("json含证据缺口", "证据缺口" in d and isinstance(d["证据缺口"], list))
    ck("json结论四态键齐全",
       set(["不通过", "有风险", "待补正"]) <= set(d["结论"]))
except Exception:
    ck("json可解析含结论", False)
r3 = subprocess.run([sys.executable, sp, empty],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
ck("空输入rc=2", r3.returncode == 2)
ck("空输入不崩有输出", len(r3.stdout or "") > 200)
ck("空输入提示中文缺失键", "关键信息缺失" in (r3.stdout or ""))
ck("空输入不出现英文键名", "relation" not in (r3.stdout or ""))
r4 = subprocess.run([sys.executable, sp, sample, "--out",
                     os.path.join(HERE, "_核查报告.md")],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
ck("落盘rc=0", r4.returncode == 0)
ck("落盘文件存在", os.path.exists(os.path.join(HERE, "_核查报告.md")))
if os.path.exists(os.path.join(HERE, "_核查报告.md")):
    with open(os.path.join(HERE, "_核查报告.md"), encoding="utf-8") as f:
        c = f.read()
    ck("落盘含结论摘要", "一、结论摘要" in c)
    ck("落盘无乱码", "\ufffd" not in c)
    os.remove(os.path.join(HERE, "_核查报告.md"))

# ---------------------------------------------------------- 汇总
total = len(PASS) + len(FAIL)
lines = ["=== 家庭暴力取证 回归测试 ===",
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
