# -*- coding: utf-8 -*-
"""手机维修防骗与套路核查 — 回归测试。

运行：python 回归测试.py
把结果写入同目录 _reg_result.txt（真跑读回，不允许只看断言计数）。
"""
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "phone_repair_check.py")
PY = sys.executable
FAILED = []
PASSED = [0]


def run(md_text=None, use_empty=False, extra=None):
    """跑主脚本，返回 (rc, stdout)。"""
    if use_empty:
        path = os.path.join(HERE, "空输入.md")
    else:
        fd, path = tempfile.mkstemp(suffix=".md")
        with io.open(fd, "w", encoding="utf-8") as f:
            f.write(md_text)
    args = [PY, SCRIPT, path]
    if extra:
        args += extra
    p = subprocess.run(args, capture_output=True)
    out = p.stdout.decode("utf-8", "replace")
    if not use_empty:
        try:
            os.remove(path)
        except OSError:
            pass
    return p.returncode, out


def chk(name, cond):
    if cond:
        PASSED[0] += 1
    else:
        FAILED.append(name)


def check_json(name, md_text, verdict, rc=0):
    rc2, out = run(md_text, extra=["--json"])
    try:
        d = json.loads(out)
    except Exception:
        chk(name + " json可解析", False)
        return None
    chk(name + " 结论=" + verdict, d.get("结论") == verdict)
    chk(name + " rc=" + str(rc), rc2 == rc)
    chk(name + " 报告非空", bool(d.get("报告")))
    return d


SECTIONS = ["## 结论摘要", "## 故障诊断与报价核查", "## 骗局手法与维修方核查",
            "## 费用与收款核查", "## 维修结果与质保",
            "## 法律后果、合规取证路径与举报入口", "## 证据清单与固定要点",
            "## 待办补正动作", "## 边界与纪律"]

# ---------- 1. 样例：小病大修 → 不通过 ----------
# 样例用 subprocess 直接跑真实文件，避免临时文件路径问题
out_s = ""
p = subprocess.run([PY, SCRIPT, os.path.join(HERE, "样例.md")],
                   capture_output=True)
out_s = p.stdout.decode("utf-8", "replace")
chk("样例 rc=0", p.returncode == 0)
for s in SECTIONS:
    chk("样例含段 " + s, s in out_s)
chk("样例命中小病大修", "小病大修" in out_s)
chk("样例判不通过", "**总体结论：不通过**" in out_s)
chk("样例退一赔三", "退一赔三" in out_s)
chk("样例提12315", "12315" in out_s)
chk("样例不提供维修服务", "不提供任何维修" in out_s)

# 样例的 json 形态
pj = subprocess.run([PY, SCRIPT, os.path.join(HERE, "样例.md"), "--json"],
                    capture_output=True)
try:
    djs = json.loads(pj.stdout.decode("utf-8", "replace"))
    chk("样例 json 结论不通过", djs.get("结论") == "不通过")
    chk("样例 json 风险项非空", bool(djs.get("风险项")))
    chk("样例 json 待办非空", bool(djs.get("待办")))
except Exception:
    chk("样例 json 可解析", False)

# ---------- 2. 空输入 → rc=2 待补正 ----------
rc, out = run(use_empty=True)
chk("空输入 rc=2", rc == 2)
chk("空输入 待补正", "待补正" in out)
rcj, outj = run(use_empty=True, extra=["--json"])
chk("空输入 json rc=2", rcj == 2)
try:
    dj = json.loads(outj)
    chk("空输入 json 结论待补正", dj.get("结论") == "待补正")
except Exception:
    chk("空输入 json 可解析", False)

# ---------- 3. 文件不存在 → rc=2 ----------
p = subprocess.run([PY, SCRIPT, "不存在的文件.md"], capture_output=True)
chk("文件不存在 rc=2", p.returncode == 2)
chk("文件不存在 提示", "不存在" in p.stdout.decode("utf-8", "replace"))

# ---------- 4. 四态结论覆盖 ----------
BASE = """
维修方：某某维修店
维修渠道：线下
设备品牌型号：某品牌 X1
是否官方售后：%s
故障自述：屏幕不亮
对方诊断结论：屏幕总成损坏
是否提前报价确认：是
报价金额：300
是否更换零件：是
更换零件明细：更换屏幕总成
更换零件是否原装正品：是
旧零件是否归还：是
已付金额：300
已退金额：0
付款方式：微信
收款主体：某某维修店
是否出具维修单据：是
维修后原故障是否解决：是
是否出现新故障：否
有无保修承诺：一年
证据留存情况：付款截图、维修单据、照片、聊天记录、旧件照片、营业执照
是否已举报：否
诉求：要求退款
"""

d = check_json("官方售后通过", BASE % "是", "通过")
if d:
    chk("官方售后 报告提到已解决", "原故障已解决" in d["报告"])

d = check_json("非官方有风险", BASE % "否", "有风险")
if d:
    chk("非官方 提示谨慎", "第三方" in d["报告"] or "授权" in d["报告"])

# 5. 核心三字段全缺 → 待补正 rc=2
MIN = """
维修方：
故障自述：
对方诊断结论：
报价金额：100
"""
d = check_json("核心缺失待补正", MIN, "待补正", rc=2)
if d:
    chk("核心缺失 报告非空", bool(d.get("报告")))

# 6. 冒号行格式（无表格）
COLON = "维修方：某某店\n故障自述：充电慢\n对方诊断结论：电池老化\n已付金额：80\n"
d = check_json("冒号格式", COLON, "有风险")

# ---------- 7. 金额计算 ----------
MONEY = BASE % "否" + "\n已付金额：500\n报价金额：300\n"
d = check_json("超报价", MONEY, "有风险")
if d:
    chk("超报价 提示追回差价", "超过报价" in d["报告"] or "追回差价" in d["报告"])

MONEY2 = BASE % "否" + "\n已退金额：100\n"
d = check_json("部分退款", MONEY2, "有风险")
if d:
    chk("部分退款 显示未退", "未退" in d["报告"])

# ---------- 8. yesno 否定词不误判 ----------
NO = BASE % "否" + "\n是否出现新故障：是\n维修后原故障是否解决：否\n"
d = check_json("原故障未解决", NO, "不通过")
if d:
    chk("未解决 提示重做或退款", "重做" in d["报告"] or "退款" in d["报告"])

# yesno：值里含「有」但是否定
chkv = check_json("否定词没有", BASE % "没有", "有风险")

# ---------- 9. 收款主体不一致 ----------
PAYEE = BASE % "否" + "\n收款主体：某某店（个体）\n"
d = check_json("收款不一致", PAYEE, "有风险")

# ---------- 10. 证据缺失提示 ----------
NOEV = BASE % "否" + "\n证据留存情况：无\n"
d = check_json("证据全缺", NOEV, "有风险")
if d:
    chk("证据全缺 仍列缺失", "仍缺失" in d["报告"] or "未填写" in d["报告"])

# ---------- 11. 是否已举报=True ----------
REP = BASE % "否" + "\n是否已举报：是\n"
d = check_json("已举报", REP, "有风险")
if d:
    chk("已举报 提示留编号", "受理编号" in d["报告"])

# ---------- 12. 空值词表（待填/待确认）视为未填 ----------
TBD = "维修方：待确认\n故障自述：待填\n对方诊断结论：待补\n"
d = check_json("待填待确认", TBD, "待补正", rc=2)

# ---------- 13. --out 写文件 ----------
fd, op = tempfile.mkstemp(suffix=".md")
os.close(fd)
with io.open(op, "w", encoding="utf-8") as f:
    f.write(BASE % "是")
outp = op + ".report"
p = subprocess.run([PY, SCRIPT, op, "--out", outp], capture_output=True)
chk("--out rc=0", p.returncode == 0)
chk("--out 文件已生成", os.path.exists(outp))
if os.path.exists(outp):
    chk("--out 内容非空", os.path.getsize(outp) > 200)
    os.remove(outp)
os.remove(op)

# ---------- 14. 边界：不提供维修服务 ----------
chk("边界声明不含维修引流", "不提供任何维修、代修或介绍维修渠道" in out_s)
chk("报告含边界与纪律", "## 边界与纪律" in out_s)
chk("报告含待办段", "## 待办补正动作" in out_s)
chk("报告含证据段", "## 证据清单与固定要点" in out_s)
chk("报告含法律段", "## 法律后果、合规取证路径与举报入口" in out_s)

# ---------- 15. 报告不出现未定义结论词 ----------
for bad in ("结论：合规", "结论：违规", "结论：未知"):
    chk("无非法结论词 " + bad, bad not in out_s)

# ---------- 16. 表格 + 冒号混排 ----------
MIX = """
| 维修方 | 某某店 |
| 故障自述 | 听筒无声 |
| 对方诊断结论 | 听筒排线脱落 |
| 报价金额 | 120 |
已付金额：120
是否官方售后：否
"""
d = check_json("混排格式", MIX, "有风险")

# ---------- 输出 ----------
lines = []
lines.append("手机维修防骗与套路核查 — 回归测试结果")
lines.append("PASS=%d" % PASSED[0])
lines.append("FAIL=%d" % len(FAILED))
if FAILED:
    lines.append("失败项：")
    for x in FAILED:
        lines.append("  - " + x)
else:
    lines.append("全部通过")
txt = "\n".join(lines)
print(txt)
with io.open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as f:
    f.write(txt)
sys.exit(1 if FAILED else 0)
