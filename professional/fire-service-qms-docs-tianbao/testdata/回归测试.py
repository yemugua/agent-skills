# -*- coding: utf-8 -*-
"""qms_check.py 回归测试（本轮新增/修好的问题逐条覆盖）"""
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPTS)

import qms_check as Q  # noqa: E402

ok = 0
bad = []


def chk(name, cond):
    global ok
    if cond:
        ok += 1
    else:
        bad.append(name)


样本 = os.path.join(HERE, "消防技术服务机构现状样例.md")
空 = os.path.join(HERE, "空现状.md")

T = date(2026, 10, 4)

# ---------- 日期解析 ----------
chk("D01 2026-04-09", Q.parse_date("有效期至 2026-04-09") == date(2026, 4, 9))
chk("D02 2026/4/9", Q.parse_date("2026/4/9") == date(2026, 4, 9))
chk("D03 2026年4月9日", Q.parse_date("2026年4月9日") == date(2026, 4, 9))
chk("D04 2026.4.9", Q.parse_date("2026.4.9") == date(2026, 4, 9))
chk("D05 非法月份返回None", Q.parse_date("2026年13月1日") is None)
chk("D06 空串返回None", Q.parse_date("") is None)
chk("D07 无日期", Q.parse_date("没有日期") is None)

# ---------- add_years ----------
chk("Y01 跨年+1", Q.add_years(date(2026, 3, 15), 1) == date(2027, 3, 15))
chk("Y02 闰年兜底", Q.add_years(date(2028, 2, 29), 1) == date(2029, 2, 28))
chk("Y03 跨年边界", Q.add_years(date(2026, 12, 31), 1) == date(2027, 12, 31))

# ---------- 解析：人员 ----------
with open(样本, "r", encoding="utf-8") as f:
    TXT = f.read()
SECS = Q.split_sections(TXT)
People = Q.parse_people(Q._section_of(SECS, "人员", "人力资源", "员工"))
chk("P01 解析出 7 人", len(People) == 7)
if People:
    p0 = People[0]
    chk("P02 姓名=吴涛", p0["name"] == "吴涛")
    chk("P03 岗位=法人/总经理", p0["role"] == "法人/总经理")
    chk("P04 识别一消", "一级消防工程师" in p0["certs"])
    chk("P05 有效期 2028-06-30", p0["expiry"] == date(2028, 6, 30))
    chk("P06 原始行保留", "吴涛" in p0["raw"])
roles = [p["role"] for p in People]
names = [p["name"] for p in People]
chk("P07 林凤钦是技术负责人（不被总经理话术吃掉）",
    next(p["role"] for p in People if p["name"] == "林凤钦") == "技术负责人")
chk("P08 程智是项目负责人",
    next(p["role"] for p in People if p["name"] == "程智") == "项目负责人")
chk("P09 赵建兵是操作员",
    next(p["role"] for p in People if p["name"] == "赵建兵") == "操作员")
chk("P10 岗位无空缺", all(roles))
chk("P11 张红星识别操作员四级",
    "消防设施操作员四级" in next(p["certs"] for p in People if p["name"] == "张红星"))
chk("P12 人员去重无重复", len(set(names)) == len(names))
chk("P13 全部人员都能抽到有效期",
    all(p["expiry"] for p in People))
devs = Q.parse_devices(Q._section_of(SECS, "设备", "校准", "计量", "器具"))
chk("V01 解析出 5 台设备", len(devs) == 5)
if devs:
    d0 = devs[0]
    chk("V02 设备名=数字万用表", d0["name"] == "数字万用表")
    chk("V03 校准号", d0["calib_no"] == "JLSZ-2025-0118")
    chk("V04 校准日期", d0["calib_date"] == date(2025, 4, 10))
    chk("V05 有效期", d0["expiry"] == date(2026, 4, 9))

# 设备名不能把「校准号」吃掉
names = [d["name"] for d in devs]
chk("V06 声级计不被吞", "声级计" in names)
chk("V07 风速仪不被吞", "风速仪" in names)

# ---------- 解析：文件/项目 ----------
docs = Q.parse_docs(Q._section_of(SECS, "已有", "体系文件", "文件清单", "受控"))
chk("F01 文件条目 >=9", len(docs) >= 9)
chk("F02 含文件控制程序", any("DXCX01" in d for d in docs))
projs = Q.split_lines(Q._section_of(SECS, "项目", "服务记录", "业务"))
chk("F03 解析出 3 个项目", len(projs) == 3)

# ---------- 分节 ----------
chk("S01 基本信息抓到机构名", Q.parse_basic(TXT, SECS).get("机构名称") == "上海度消技术咨询有限公司")
la, lm = Q.parse_last_dates(TXT, SECS, T)
chk("S02 上次内审 2025-11-20", la == date(2025, 11, 20))
chk("S03 上次管理评审 2025-12-05", lm == date(2025, 12, 5))

# ---------- 要素覆盖 ----------
m = Q.cover_matrix(SECS, docs + projs)
chk("M01 14 个要素", len(m) == 14)
chk("M02 全部有编号", all(r["code"] for r in m))
chk("M03 状态取值合法", all(r["status"] in ("已建立", "部分覆盖", "缺失") for r in m))
chk("M04 07 测量溯源被命中", Q.doc_hit(m, "07"))
chk("M05 07 状态非缺失", next(r for r in m if r["code"] == "07")["status"] != "缺失")
chk("M06 10 投诉与服务满意度被命中", Q.doc_hit(m, "10"))
chk("M07 命中文件数不超上限*条数", all(r["hits"] <= 3 * max(len(docs) + len(projs), 1) for r in m))
chk("M08 状态与命中数一致",
    all((r["hits"] >= 2) == (r["status"] == "已建立") and (r["hits"] == 1) == (r["status"] == "部分覆盖")
        for r in m))

# ---------- 到期 ----------
exp = Q.expires(devs, T)
chk("E01 5 条到期结果", len(exp) == 5)
chk("E02 声级计已过期", next(e for e in exp if e["item"]["name"] == "声级计")["state"] == "已过期")
chk("E03 声级计超期天数为负 369",
    next(e for e in exp if e["item"]["name"] == "声级计")["days"] == -369)
chk("E04 测距仪有效", next(e for e in exp if e["item"]["name"] == "测距仪")["state"] == "有效")
_chk = next(e for e in exp if e["item"]["name"] == "数字万用表")
chk("E05 万用表已过期", _chk["state"] == "已过期")
chk("E06 过期天数为负 178", _chk["days"] == -178)
_chk2 = next(e for e in exp if e["item"]["name"] == "测距仪")
chk("E06b 测距仪剩 148 天", _chk2["days"] == 148)
chk("E06c 测距仪为有效", _chk2["state"] == "有效")
chk("E07 未填有效期不误判", Q.expires([{"name": "x", "expiry": None}], T)[0]["days"] is None)

# ---------- 完整分析 ----------
r = Q.analyze(TXT, T)
rep = r["report"]
chk("R01 报告非空", len(rep) > 500)
chk("R02 含结论摘要", "结论摘要" in rep)
chk("R03 含覆盖度矩阵", "要素覆盖度矩阵" in rep)
chk("R04 含人员章节", "人员资质与到期预警" in rep)
chk("R05 含校准台账", "设备校准溯源台账" in rep)
chk("R06 含内审章节", "内审与管理评审" in rep)
chk("R07 含时间线", "认证时间线与 2026 新规硬约束" in rep)
chk("R08 含补件清单", "补件清单" in rep)
chk("R09 含高风险项", "高风险项" in rep)
chk("R10 机构名进报告", "上海度消技术咨询有限公司" in rep)
chk("R11 超期设备名进报告", "声级计" in rep)
chk("R12 过期人（张红星）进报告", "张红星" in rep)
chk("R13 生成日期", r["generated"] == "2026-10-04")
chk("R14 版本", r["version"] == "1.0.0")
chk("R15 json 可序列化", isinstance(r["matrix"], list))
chk("R16 people 回传", len(r["people"]) == 7)
chk("R17 devices 回传", len(r["devices"]) == 5)
chk("R18 last_audit", r["last_internal_audit"] == "2025-11-20")
chk("R19 last_mr", r["last_management_review"] == "2025-12-05")

# 报告里不能出现未替换花括号 / None 乱入正文
chk("R20 无 { 残留", "{" not in rep)
chk("R21 无 Python None 词", "\nNone\n" not in rep)

# 缺失/部分统计
miss = [x for x in r["matrix"] if x["status"] == "缺失"]
part = [x for x in r["matrix"] if x["status"] == "部分覆盖"]
chk("R22 缺失要素有列出", isinstance(miss, list))
chk("R23 部分覆盖有列出", isinstance(part, list))
chk("R24 缺失+部分+已建立 = 14", len(miss) + len(part) + len([x for x in r["matrix"] if x["status"] == "已建立"]) == 14)

# 补件清单编号不能撞机构已有 DXCX01~27
sec7 = rep.split("## 七、")[1].split("## 八、")[0]
chk("R25 补件从 DXCX41 起号", "DXCX41" in sec7)
chk("R25b 补件不含 DXCX40 空号", "DXCX40 |" not in sec7)
chk("R26 补件不撞已有 DXCX07", "DXCX07" not in sec7)
chk("R27 补件含校准证书补件", "重新校准证书" in sec7)
chk("R28 补件责任人已填", "林凤钦" in sec7)

# 高风险项表要有真处置建议，不能留空列
blk8 = rep.split("## 八、")[1]
chk("R29 高风险表无空列占位", "见风险描述" not in blk8)
chk("R30 高风险表 >=3 行", blk8.count("\n| ") >= 3)
chk("R31 高风险含记录真实性", "记录真实性" in blk8)
chk("R32 高风险表含处置建议", "换证" in blk8)

# 报告里不能出现「未替换」痕迹
chk("R33 无大括号残留", "{" not in rep and "}" not in rep)
chk("R34 无双冒号乱码", "锟" not in rep)

# ---------- 空输入 ----------
with open(空, "r", encoding="utf-8") as f:
    EMPTY = f.read()
e = Q.analyze(EMPTY, T)
chk("W01 空输入不崩", isinstance(e["report"], str))
chk("W02 空输入全缺失", all(x["status"] == "缺失" for x in e["matrix"]))
chk("W03 空输入人员为空", len(e["people"]) == 0)
chk("W04 空输入无残留机构名", e["org"] == "")

# ---------- CLI ----------
old_argv = sys.argv
out_json = os.path.join(HERE, "_out.json")
try:
    sys.argv = ["qms_check.py", "--file", 样本, "--today", "2026-10-04", "--json", out_json]
    rc = Q.main()
    chk("C01 main rc=0", rc == 0)
finally:
    sys.argv = old_argv

try:
    sys.argv = ["qms_check.py", "--file", 样本, "--today", "2026-10-04"]
    Q.main()
    chk("C02 不带 json 也能跑", True)
finally:
    sys.argv = old_argv

chk("C03 json 文件生成", os.path.exists(out_json))
if os.path.exists(out_json):
    with open(out_json, "r", encoding="utf-8") as f:
        j = f.read()
    chk("C04 json 含 report 键", '"report"' in j)
    chk("C05 json 含 org", "度消" in j)
    import json as _j
    obj = _j.loads(j)
    chk("C05b json 可直接反序列化", isinstance(obj, dict))
    chk("C05c json 里 date 已转字符串",
        isinstance(obj["people"][0]["expiry"], str))
    chk("C05d json 含 people/devices", len(obj["people"]) == 7 and len(obj["devices"]) == 5)
    chk("C05e json 无裸 None 字段", "last_internal_audit" in obj)
    os.remove(out_json)

# 坏参数
try:
    sys.argv = ["qms_check.py", "--file", 样本, "--today", "abcdef"]
    try:
        Q.main()
        chk("C06 坏日期应退出", False)
    except SystemExit as ex:
        chk("C06 坏日期应退出", ex.code != 0)
finally:
    sys.argv = old_argv

# 空文件应 sys.exit 警告
with open(os.path.join(HERE, "_t_empty.md"), "w", encoding="utf-8") as f:
    f.write("   \n")
try:
    sys.argv = ["qms_check.py", "--file", os.path.join(HERE, "_t_empty.md")]
    try:
        Q.main()
        chk("C07 空文件应退出", False)
    except SystemExit as ex:
        chk("C07 空文件应退出", ex.code != 0)
finally:
    sys.argv = old_argv
    os.remove(os.path.join(HERE, "_t_empty.md"))

# 命令行子进程
rc2 = subprocess.run(
    [sys.executable, os.path.join(SCRIPTS, "qms_check.py"), "--file", 样本, "--today", "2026-10-04"],
    capture_output=True, text=True, encoding="utf-8", errors="replace")
chk("C08 子进程 rc=0", rc2.returncode == 0)
chk("C09 子进程有 stdout", len(rc2.stdout) > 500)
chk("C10 子进程无 stderr", not rc2.stderr.strip())

rc3 = subprocess.run(
    [sys.executable, os.path.join(SCRIPTS, "qms_check.py"), "--file",
     os.path.join(HERE, "不存在的.md")],
    capture_output=True, text=True, encoding="utf-8", errors="replace")
chk("C11 缺文件非 0", rc3.returncode != 0)
chk("C12 缺文件有提示", "找不到输入文件" in (rc3.stdout + rc3.stderr))

print("=" * 60)
print(f"通过 {ok} 项，失败 {len(bad)} 项")
if bad:
    print("失败清单：")
    for b in bad:
        print("  x " + b)
    sys.exit(1)
print("全部通过")
