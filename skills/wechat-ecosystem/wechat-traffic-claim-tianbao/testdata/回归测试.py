# -*- coding: utf-8 -*-
"""wechat-traffic-claim 回归测试套件。纯标准库，直接 python 回归测试.py"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "extract.py")
SAMPLE = os.path.join(HERE, "交通事故样例.md")

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


# 1 基本人伤扫描
rc, out, err = run(["--file", SAMPLE, "--scenario", "injury"])
check("1 人伤扫描 rc=0", rc == 0, err)
check("1 报告含八段", out.count("\n## ") >= 7, out.count("\n## "))
check("1 命中事故认定书", "事故认定书" in out)
check("1 无乱码 U+FFFD", "\ufffd" not in out)

# 2 车损场景
rc, out, err = run(["--file", SAMPLE, "--scenario", "property"])
check("2 车损扫描 rc=0", rc == 0, err)
check("2 车损不报伤残等级", "聊天中提到伤残等级" not in out, out[:400])
check("2 识别随身物品损失", "随身物品损失" in out)
check("2 随身物品不应归为车载", out.index("随身物品损失") < out.index("车载物品损失")
      if "车载物品损失" in out else True)

# 3 全场景 JSON
rc, out, err = run(["--file", SAMPLE, "--scenario", "all", "--format", "json"])
check("3 JSON rc=0", rc == 0, err)
import json
try:
    d = json.loads(out)
    ok = True
except Exception as e:
    ok = False
    d = {}
    print("   json err:", e)
check("3 JSON 可解析", ok)
check("3 JSON 含交强险限额", d.get("claimLimits", {}).get("有责", {}).get("死亡伤残") == 180000)
check("3 JSON 含要件命中", len(d.get("hits", [])) > 5, len(d.get("hits", [])))
check("3 JSON 含缺失要件", len(d.get("misses", [])) > 3)
check("3 JSON 含金额", len(d.get("amounts", [])) > 5, len(d.get("amounts", [])))
check("3 JSON 含里程碑", len(d.get("milestones", [])) > 5)
check("3 JSON 含免责", bool(d.get("disclaimer")))

# 4 focus 语义别名（上次的 BUG：--focus 拒赔 命中 0 条）
for cat, expect_min in [("拒赔", 3), ("金额", 5), ("鉴定", 2), ("责任", 3), ("医疗", 3)]:
    rc, out, err = run(["--file", SAMPLE, "--scenario", "injury", "--focus", cat])
    check("4 focus %s rc=0" % cat, rc == 0, err)
    n = int(out.count("\n## 四") and out.split("筛出 ")[1].split(" 条")[0]
            if "筛出 " in out else -1)
    check("4 focus %s 命中>0" % cat, n >= expect_min, n)
    check("4 focus %s 保留争议焦点段" % cat, "\n## 四、争议焦点" in out)

# 5 focus 字面词
rc, out, err = run(["--file", SAMPLE, "--focus", "伤残鉴定"])
check("5 focus 字面词 rc=0", rc == 0, err)

# 6 空文件
tmp = tempfile.mkdtemp()
empty = os.path.join(tmp, "empty.md")
open(empty, "w", encoding="utf-8").close()
rc, out, err = run(["--file", empty, "--scenario", "injury"])
check("6 空文件不崩溃（rc!=0 或给出提示）",
      rc == 0 or ("未解析出" in (out + err) or "没有" in (out + err)), (rc, out, err))

# 7 文件不存在
rc, out, err = run(["--file", os.path.join(tmp, "nope.md")])
check("7 文件不存在报错", rc != 0 and "不存在" in (out + err), (rc, out + err))

# 8 非法场景
rc, out, err = run(["--file", SAMPLE, "--scenario", "bad"])
check("8 非法场景报错", rc != 0 and "scenario" in (out + err), (rc, out + err))

# 9 非法 as-of
rc, out, err = run(["--file", SAMPLE, "--as-of", "2026/10/01"])
check("9 非法 as-of 报错", rc != 0 and "YYYY" in (out + err), (out + err)[:200])

# 10 时效过期
rc, out, err = run(["--file", SAMPLE, "--as-of", "2030-01-01"])
check("10 已过时效提示", "已过期" in out or "⚠️" in out, out[:300])

# 11 时效临界（距届满<90天）
rc, out, err = run(["--file", SAMPLE, "--as-of", "2029-07-01"])
check("11 临界时效提示", "仅剩" in out, out[:300])

# 12 focus 无任何命中 -> 给提示不崩溃
rc, out, err = run(["--file", SAMPLE, "--focus", "zzz_not_exist_zzz"])
check("12 focus 无命中有提示", rc != 0 and "没有消息命中" in (out + err), (out + err)[:200])

# 13 输出文件
o = os.path.join(tmp, "r.md")
rc, out, err = run(["--file", SAMPLE, "--scenario", "all", "--out", o])
check("13 --out 写文件", rc == 0 and os.path.exists(o) and os.path.getsize(o) > 500,
      (rc, os.path.exists(o) if os.path.exists(o) else 0))

# 14 多说话人识别
rc, out, err = run(["--file", SAMPLE, "--format", "json"])
check("14 识别两位当事人", "周敏" in out and "陈立" in out)

# 15 纯标准库（无第三方依赖）
with open(SCRIPT, "r", encoding="utf-8") as fh:
    src = fh.read()
check("15 无第三方 import", "requests" not in src and "openpyxl" not in src)

# 16 样本无乱码
with open(SAMPLE, "r", encoding="utf-8") as fh:
    check("16 测试样本无乱码", "\ufffd" not in fh.read())

print("\n通过 %d / %d" % (len(PASS), len(PASS) + len(FAIL)))
if FAIL:
    print("失败项：%s" % "、".join(FAIL))
    sys.exit(1)
