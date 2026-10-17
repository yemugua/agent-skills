# -*- coding: utf-8 -*-
"""网购退货七天无理由核查 —— 回归测试（断言 >= 40 条）

跑法（在本目录执行）：
  python 回归测试.py
结果写入 _reg_result.txt（utf-8，直接调用主脚本函数 + 子进程实跑）。
"""
import json
import os
import re
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, os.pardir, "scripts", "return_check.py")
sys.path.insert(0, os.path.join(HERE, os.pardir, "scripts"))
import return_check as R  # noqa: E402

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


# ------------------------------------------------------------------ 解析
src = open(SAMPLE, encoding="utf-8").read()

ck("P01", "norm 去空格", R.norm(" 商品 名称 ") == "商品名称")
ck("P02", "norm 全角括号", R.norm("某牌（数码）") == "某牌(数码)")
ck("P03", "norm 竖线转空格防串列", R.norm("a|b") == "a b")
ck("P04", "is_ph 待填", R.is_ph("待填") is True)
ck("P05", "is_ph 有/无 提示串", R.is_ph("有 / 无") is True)
ck("P06", "is_ph 真值", R.is_ph("是") is False)
ck("P07", "is_row 表格行", R.is_row("| 商品名称 | 耳机 |") is True)
ck("P08", "is_row 普通行", R.is_row("前面一段话") is False)
ck("P09", "split_row 拆两列", R.split_row("| 商品名称 | 耳机 |") == ["商品名称", "耳机"])
ck("P10", "parse_fields 表格行", ("商品名称", "某牌无线降噪耳机 Pro") in R.parse_fields(src))
ck("P11", "parse_fields 冒号行", ("退货理由", "收到就开不了机，质量问题") in R.parse_fields(src + "\n退货理由：屏幕有划痕\n"))
ck("P12", "parse_fields 保留表头行", ("字段", "值") in R.parse_fields(src))

ck("P13", "get_text 最长别名优先",
   R.get_text(src, "商品类别/性质", "商品类别", "商品性质") == "普通实体商品（数码配件）")
ck("P14", "get_text 未命中空串", R.get_text(src, "不存在的字段") == "")
ck("P15", "get_text 过滤占位", R.get_text(src, "商品名称") == "某牌无线降噪耳机 Pro")
ck("P16", "get_int 取数字", R.get_int(src, "发现瑕疵距签收天数") == 2)
ck("P17", "get_int 无数字 None", R.get_int(src, "退货理由") is None)
ck("P18", "parse_num 去符号", R.parse_num("¥2,499") == 2499.0)
ck("P19", "parse_num 文字取 None", R.parse_num("不符合") is None)
ck("P20", "parse_date ISO", str(R.parse_date("2026-10-04")) == "2026-10-04")
ck("P21", "parse_date 中文", str(R.parse_date("2026年10月4日")) == "2026-10-04")
ck("P22", "parse_date 短写法补年份",
   str(R.parse_date("10-04", BASE)) == "2026-10-04")
ck("P23", "parse_date 空 None", R.parse_date("", BASE) is None)
ck("P24", "yes 是", R.yes("商品是否完好：是\n", "商品是否完好") is True)
ck("P25", "yes 否返回 False", R.yes("商家是否拒绝：否\n", "商家是否拒绝") is False)
ck("P26", "yes 未填返回 None", R.yes("", "商品是否完好") is None)
ck("P27", "has_cat 定制命中", R.has_cat("定制家具", "定制") is True)
ck("P28", "has_cat 非定制不命中", R.has_cat("非定制商品", "定制") is False)
ck("P29", "ovr 显式优先", R.ovr(True, False) is False)
ck("P30", "ovr 显式缺省用推断", R.ovr(True, None) is True)
ck("P31", "fmt_num 去 .0", R.fmt_num(2499.0) == "2499")
ck("P32", "fmt_num None", R.fmt_num(None) == "未填")
ck("P33", "money 前缀", R.money(10.0) == "¥10")
ck("P34", "fmt_flag True", R.fmt_flag(True) == "是")
ck("P35", "fmt_flag False", R.fmt_flag(False) == "**否**")
ck("P36", "fmt_flag None", R.fmt_flag(None) == "未填")
ck("P37", "add_days", str(R.add_days(BASE, 7)) == "2026-10-12")
ck("P38", "days_left", R.days_left(date(2026, 10, 12), BASE) == 7)

# ------------------------------------------------------------------ 报告
body, meta = R.build_report(SAMPLE, BASE)
ck("R01", "样例生成报告", isinstance(body, str) and len(body) > 1000, len(body) if body else 0)
ck("R02", "样例 meta 结论", meta["结论"] == "通过", meta["结论"])
ck("R03", "样例无理由路径", meta["无理由路径"] == "通过", meta["无理由路径"])
ck("R04", "样例质量路径", meta["质量路径"] == "通过", meta["质量路径"])
ck("R05", "样例举证倒置适用", meta["举证责任倒置"] is True)
ck("R06", "样例运费归属经营者", meta["运费归属"] == "经营者", meta["运费归属"])
ck("R07", "样例待承担运费=2", meta["待承担运费"] == 2.0, meta["待承担运费"])
ck("R08", "样例九个章节", body.count("## ") >= 9, body.count("## "))
ck("R09", "样例含结论摘要", "## 一、结论摘要" in body)
ck("R10", "样例含待办补正动作", "## 九、待办补正动作与边界纪律" in body)
ck("R12", "样例含拆封段", "## 四、拆封与商品完好判定" in body)
ck("R13", "样例含运费段", "## 六、运费谁出（含算式）" in body)
ck("R14", "样例含证据缺口段", "## 八、证据缺口与平台介入路径" in body)
ck("R15", "样例标注购买时确认不成立", "购买时未经你单独确认" in body)
ck("R16", "样例点出拆封不能退是错的", "拆封了就不能退\"是错的" in body)
ck("R17", "样例点出激活不是法定除外", "以此排除七天无理由缺少法律依据" in body)
ck("R17b", "样例列出激活拒退风险点", "已联网激活\"为由拒退" in body)
ck("R18", "样例提示未申请平台介入", "申请平台介入" in body)
ck("R19", "样例运费算式", "¥12" in body and "¥10" in body)
ck("R20", "样例无【待填】泄漏", "【待填】" not in body)
ck("R21", "样例无乱码", "\ufffd" not in body)
ck("R22", "样例表格不裂", "|---|" in body and body.count("|---|") >= 3)
ck("R23", "样例结尾免责", "最终以主管部门 / 平台 / 司法机关认定为准" in body)
ck("R24", "样例时效 3 年", "3 年" in body)
ck("R25", "样例金额无 .0 尾巴", "¥2499.0" not in body)
ck("R26", "样例距窗口剩 6 天", "还剩 6 天" in body, body[:0])
ck("R27", "样例举证倒置期日期", "举证责任倒置期（六个月）" in body)
ck("R28", "样例证据缺口列出两项", "物流称重记录" in body and "商品页面快照" in body)

# ------------------------------------------------------------------ 边界
nb, nmeta = R.build_report(EMPTY, BASE)
ck("R29", "样例边界纪律含不替代律师意见", "不替代" in body)
_todo_sec = body.split("## 九、待办补正动作与边界纪律")[1]
ck("R30", "样例第九段待办条数>=5",
   len([l for l in _todo_sec.splitlines() if re.match(r"^\d+\. ", l)]) >= 5)
ck("B01", "空输入返回 None", nb is None)
ck("B02", "空输入给提示串", isinstance(nmeta, str) and "关键信息" in nmeta, str(nmeta)[:60])
nb2, n2 = R.build_report(os.path.join(HERE, "不存在的样例文件.md"), BASE)
ck("B03", "缺文件不崩", nb2 is None and "读不了文件" in str(n2), str(n2)[:60])

# ------------------------------------------------------------------ 子进程
rc, so, se = run([SAMPLE, "--base", "2026-10-05"])
ck("S01", "样例 rc=0", rc == 0, "rc=%s %s" % (rc, se[:120]))
ck("S02", "样例无异常", "Traceback" not in se, se[:120])
ck("S03", "样例章节数>=9", so.count("## ") >= 9, so.count("## "))
ck("S04", "空输入 rc=2", run([EMPTY])[0] == 2, run([EMPTY])[0])
ck("S05", "空输入不崩", "Traceback" not in run([EMPTY])[2])
ck("S06", "空输入有输出", len(run([EMPTY])[1]) > 20)

rcj, soj, _ = run([SAMPLE, "--json"])
ok = False
dj = None
try:
    dj = json.loads(soj)
    ok = True
except Exception as e:
    ok = False
ck("S07", "json 可解析", ok)
if dj:
    ck("S08", "json 含结论", "结论" in dj)
    ck("S09", "json 含风险项", "风险项" in dj and isinstance(dj["风险项"], list))
    ck("S10", "json 含待办", "待办" in dj and len(dj["待办"]) > 0)
    ck("S11", "json 无理由路径=通过", dj.get("无理由路径") == "通过")
    ck("S12", "json 举证倒置", dj.get("举证责任倒置") is True)
    ck("S13", "json 待办非空", len(dj["待办"]) >= 3)

# ------------------------------------------------------------------ 落盘
out = os.path.join(HERE, "_tmpout_样例_核查报告.md")
rco, soo, _ = run([SAMPLE, "--base", "2026-10-05", "--out", out])
content = ""
if os.path.exists(out):
    content = open(out, encoding="utf-8").read()
ck("T01", "--out 落盘", os.path.exists(out) and len(content) > 1000, len(content))
ck("T02", "落盘含九段", content.count("## ") >= 9)
ck("T03", "落盘无乱码", "\ufffd" not in content)
ck("T04", "落盘无【待填】", "【待填】" not in content)
if os.path.exists(out):
    os.remove(out)

# ------------------------------------------------------------------ 汇总
buf = []
for code, name, okk in P:
    buf.append("%s %s %s" % ("PASS" if okk else "FAIL", code, name))
buf.append("== TOTAL PASS=%d FAIL=%d ==" % (len(P), len(FAILED)))
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(buf) + "\n")
print("\n".join(buf))
sys.exit(1 if FAILED else 0)
