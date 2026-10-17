# -*- coding: utf-8 -*-
"""wechat-debt-claim 回归测试套件。纯标准库，直接 python 回归测试.py"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "extract.py")
SAMPLE = os.path.join(HERE, "催款样例.md")

PASS, FAIL = [], []


def run(args):
    p = subprocess.run([sys.executable, SCRIPT] + args,
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, p.stdout, p.stderr


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print("%s  %s%s" % ("PASS" if cond else "FAIL", name,
                        ("" if cond else "  <- " + str(extra))))


# 1 基本扫描
rc, out, err = run(["--file", SAMPLE])
check("1 默认扫描 rc=0", rc == 0, err)
check("1 报告含九段", out.count("\n## ") >= 8, out.count("\n## "))
check("1 无乱码 U+FFFD", "\ufffd" not in out)

# 2 借贷场景
rc, out, err = run(["--file", SAMPLE, "--scenario", "loan"])
check("2 借贷扫描 rc=0", rc == 0, err)
check("2 命中借贷合意", "借贷合意" in out)
check("2 命中催告质量评估", "催告质量评估" in out)

# 3 货款场景
rc, out, err = run(["--file", SAMPLE, "--scenario", "goods"])
check("3 货款扫描 rc=0", rc == 0, err)
check("3 货款场景有要件表", "要件命中表" in out)

# 4 全场景 JSON
rc, out, err = run(["--file", SAMPLE, "--scenario", "all", "--format", "json"])
check("4 JSON rc=0", rc == 0, err)
try:
    d = json.loads(out)
    ok = True
except Exception as e:
    ok = False
    d = {}
    print("   json err:", e)
check("4 JSON 可解析", ok)
check("4 JSON 含要件命中", len(d.get("hits", [])) > 4, len(d.get("hits", [])))
check("4 JSON 含金额", len(d.get("amounts", [])) > 3, len(d.get("amounts", [])))
check("4 JSON 含催告评估", len(d.get("demands", [])) > 2, len(d.get("demands", [])))
check("4 JSON 含拒付", len(d.get("refusals", [])) >= 2, len(d.get("refusals", [])))
check("4 JSON 含免责", bool(d.get("disclaimer")))

# 5 金额抽取准确性
rc, out, err = run(["--file", SAMPLE, "--format", "json"])
nums = [a["amount"] for a in json.loads(out)["amounts"]]
for want in (20000.0, 22000.0, 5000.0, 17000.0, 8000.0):
    check("5 抽到金额 %s" % want, any(abs(n - want) < 1 for n in nums), nums)

# 6 focus 类别
for cat, exp in [("催告", 3), ("金额", 5), ("拒付", 2), ("承诺", 2), ("时效", 2)]:
    rc, out, err = run(["--file", SAMPLE, "--focus", cat])
    check("6 focus %s rc=0" % cat, rc == 0, err)
    n = int(out.split("筛出 ")[1].split(" 条")[0]) if "筛出 " in out else -1
    check("6 focus %s 命中>0" % cat, n >= exp, n)

# 7 focus 字面词
rc, out, err = run(["--file", SAMPLE, "--focus", "支付令"])
check("7 focus 字面词 rc=0", rc == 0, err)

# 8 空文件
tmp = tempfile.mkdtemp()
empty = os.path.join(tmp, "empty.md")
open(empty, "w", encoding="utf-8").close()
rc, out, err = run(["--file", empty, "--scenario", "loan"])
check("8 空文件不崩溃", rc == 0 or ("未解析出" in (out + err)), (rc, out + err))

# 9 文件不存在
rc, out, err = run(["--file", os.path.join(tmp, "nope.md")])
check("9 文件不存在报错", rc != 0 and "不存在" in (out + err), (rc, out + err))

# 10 非法场景
rc, out, err = run(["--file", SAMPLE, "--scenario", "bad"])
check("10 非法场景报错", rc != 0 and "scenario" in (out + err), (rc, out + err))

# 11 非法 as-of
rc, out, err = run(["--file", SAMPLE, "--as-of", "2026/10/01"])
check("11 非法 as-of 报错", rc != 0 and "YYYY" in (out + err), (out + err)[:200])

# 12 时效过期
rc, out, err = run(["--file", SAMPLE, "--as-of", "2030-01-01"])
check("12 已过时效提示", "已过期" in out, out[:300])

# 13 时效临界
rc, out, err = run(["--file", SAMPLE, "--as-of", "2028-03-11"])
check("13 临界时效提示", "仅剩" in out, out[:300])

# 14 focus 无命中
rc, out, err = run(["--file", SAMPLE, "--focus", "zzz_不存在_zzz"])
check("14 focus 无命中有提示", rc != 0 and "没有消息命中" in (out + err), (out + err)[:200])

# 15 --out
o = os.path.join(tmp, "r.md")
rc, out, err = run(["--file", SAMPLE, "--out", o])
check("15 --out 写文件", rc == 0 and os.path.exists(o) and os.path.getsize(o) > 500)

# 16 纯标准库
with open(SCRIPT, "r", encoding="utf-8") as fh:
    src = fh.read()
check("16 无第三方 import", "requests" not in src and "openpyxl" not in src)
check("17 样本无乱码", "\ufffd" not in open(SAMPLE, encoding="utf-8").read())

# 18 弱催告识别
rc, out, err = run(["--file", SAMPLE, "--format", "json"])
weak = [x for x in json.loads(out)["demands"] if x["score"] <= 2]
check("18 能识别弱催告", len(weak) >= 1, len(weak))

print("\n通过 %d / %d" % (len(PASS), len(PASS) + len(FAIL)))
if FAIL:
    print("失败项：%s" % "、".join(FAIL))
    sys.exit(1)
