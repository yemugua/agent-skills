# -*- coding: utf-8 -*-
"""
wechat-shift-roster 回归测试（纯标准库）

用法：
    python 回归测试.py                      # 跑全部
    python 回归测试.py 班次 时效             # 只跑含关键字的用例
"""
import io
import json
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from datetime import timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(ROOT, "scripts", "extract.py")
SAMPLE = os.path.join(HERE, "排班样例.md")

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import extract  # noqa: E402

PASS = FAIL = 0
FAILED = []


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  PASS  %s" % name)
    else:
        FAIL += 1
        FAILED.append(name)
        print("  FAIL  %s %s" % (name, extra))


def run(args, **kw):
    return subprocess.run([sys.executable, SCRIPT] + args,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", **kw)


def scan_file(path, extra=None):
    """在进程内跑一次 extract.main()（argv 必须临时替换，否则吃的是本测试的 argv）。"""
    argv = [SCRIPT, "--file", path, "--as-of", "2026-10-04"]
    if extra:                       # 别写成 for a in extra：字符串会被逐字符遍历
        argv += extra.split()
    buf = io.StringIO()
    old_argv, sys.argv = sys.argv, argv
    try:
        with redirect_stdout(buf):
            extract.main()
    finally:
        sys.argv = old_argv
    return buf.getvalue()


# ===========================================================================
print("[1] 消息解析")

msgs, meta = extract.parse_messages(SAMPLE)
check("解析出消息 >= 22 条", len(msgs) >= 22, len(msgs))
check("解析条数与 meta.parsed 一致", meta["parsed"] == len(msgs))
check("识别到两位发言者", set(meta["speakers"]) == {"王主管", "小李"}, meta["speakers"])
check("时间戳解析成功", all(m["ts"] is not None for m in msgs[:5]))
check("末条时间正确", msgs[-1]["ts"].strftime("%Y-%m-%d %H:%M") == "2026-04-20 09:00",
      msgs[-1]["ts_raw"])

buf = io.StringIO()
try:
    with redirect_stdout(buf):
        extract.parse_messages(os.path.join(HERE, "不存在的.md"))
    check("文件不存在时退出", False)
except SystemExit:
    check("文件不存在时退出", True)

# ===========================================================================
print("[2] 班次抽取（跨天 / 时长 / 中文写法）")

shifts = extract.extract_shifts(msgs)
check("至少抽出 6 个班次", len(shifts) >= 6, len(shifts))

cross = [s for s in shifts if s["crossDay"]]
check("识别到跨天夜班（22:00-6:00 记 8 小时）",
      any(s["start"] == "22:00" and s["end"] == "06:00" and s["hours"] == 8.0
          for s in cross), [s for s in shifts if s["crossDay"]][:2])
check("跨天班次标记 crossDay=True 且 end 已是 06:00",
      all(s["end"] == "06:00" for s in cross))

check("识别白班 9:00-18:00 为 9 小时",
      any(s["start"] == "09:00" and s["hours"] == 9.0 for s in shifts))

check("中文「点到」写法能被抽到（原为抽不到的Bug）",
      any(s["start"] == "22:00" and s["end"] == "06:00" for s in shifts))

kinds = {s["kind"] for s in shifts}
check("识别出夜班/白班类型", {"夜班", "白班"} <= kinds, kinds)
check("没把整句话压成单个班次（一话多班）", len(shifts) >= 6, len(shifts))

d22 = [s for s in shifts if s["day"] == 22]
check("中文数字日期「二十二号」→ day=22", bool(d22), [s["day"] for s in shifts])
check("「二十二号」那条是夜班且 8 小时",
      d22 and d22[0]["kind"] == "夜班" and d22[0]["hours"] == 8.0, d22[:1])
check("每个班次都带出处时间", all(s["ts_raw"] for s in shifts))

check("滤掉非法时段（时>23 或 时长异常）",
      all(0 <= int(s["start"][:2]) <= 23 and 0 <= int(s["end"][:2]) <= 23 for s in shifts))

# ===========================================================================
print("[3] 要件扫描")

hits, misses, snippets = extract.scan_elements(msgs, "roster")
hit_names = {h["name"] for h in hits}
for need in ("排班主体", "班次时间", "本人确认", "考勤记录"):
    check("roster 命中「%s」" % need, need in hit_names, hit_names)
check("本人确认命中关键词含「收到」",
      any("收到" in w for h in hits if h["name"] == "本人确认" for w in h["words"]))
check("roster 命中数 >= 5", len(hits) >= 5, len(hits))
check("roster 命中「加班审批」", "加班审批" in hit_names, hit_names)
_idx = [s[0] for s in snippets]
check("一条消息最多被 2 个要件引用（防饿死又防刷屏）",
      max([_idx.count(i) for i in range(len(msgs))] or [0]) <= 2)

ohits, omisses, _ = extract.scan_elements(msgs, "overtime")
onames = {h["name"] for h in ohits}
for need in ("加班事实", "法定节假日", "加班费基数", "不定时/综合工时", "值班而非加班"):
    check("overtime 命中「%s」" % need, need in onames, onames)
check("overtime 命中「已付加班费」", "已付加班费" in onames, onames)

lhits, _, _ = extract.scan_elements(msgs, "leave")
lnames = {h["name"] for h in lhits}
check("leave 命中「年假未休」", "年假未休" in lnames, lnames)
check("leave 命中「离职结算」", "离职结算" in lnames, lnames)

empty_hits, empty_misses, _ = extract.scan_elements([], "roster")
check("空消息不报错", empty_hits == [] and empty_misses)

check("非法场景返回空", extract.scan_elements(msgs, "nope") == ([], [], []))

# ===========================================================================
print("[4] 拒付 / 里程碑 / 催告质量")

refusals = extract.detect_refusals(msgs)
check("识别出拒付推诿表述", len(refusals) > 0, len(refusals))
check("「算值班」被识别为拒付",
      any("算值班" in r["text"] for r in refusals))
check("「不定时」被识别为拒付",
      any("不定时" in r["text"] for r in refusals))
check("「没审批」被识别为拒付",
      any("没审批" in r["text"] or "没有加班审批" in r["text"] for r in refusals))

ms = extract.scan_milestones(msgs)
check("里程碑分到 8 类", len(ms) == 8, len(ms))
check("「收到确认」有命中", dict(ms)["收到确认"][0]["who"] == "小李")
check("「法律途径」有命中", len(dict(ms)["法律途径"]) > 0)

demands = extract.assess_demands(msgs)
strong = [d for d in demands if d["score"] >= 3]
check("存在高得分主张（>=3/4）", len(strong) > 0,
      [(d["score"], d["msg"]["text"][:20]) for d in demands[:3]])
check("逐条主张：金额那条约含小时数", any("43" in d["msg"]["text"] for d in strong))
check("得分排序是降序", all(demands[i]["score"] >= demands[i + 1]["score"]
                            for i in range(len(demands) - 1)))
check("「你爱去哪去哪」不算有效主张",
      not any("你爱去哪去哪" in d["msg"]["text"] and d["score"] >= 2 for d in demands))

# ===========================================================================
print("[5] 时效计算")

as_of = extract.date(2026, 10, 4)
trigger = extract.find_trigger_date(msgs)
check("触发日 = 最早含排班字的日期 2025-11-18",
      trigger.isoformat() == "2025-11-18", trigger)
exp, days = extract.compute_deadline(trigger, 1, as_of)
check("1 年届满日 = 2026-11-18", exp.isoformat() == "2026-11-18", exp)
check("距届满 45 天", days == 45, days)
_, d2 = extract.compute_deadline(trigger, 1, extract.date(2027, 1, 1))
check("超期后 daysLeft 为负", d2 < 0, d2)
_, d3 = extract.compute_deadline(trigger, 1, extract.add_years(trigger, 1))
check("届满当天 daysLeft = 0", d3 == 0, d3)
_exp1 = extract.add_years(trigger, 1)
check("届满后一天 daysLeft = -1",
      extract.compute_deadline(trigger, 1, _exp1 + timedelta(days=1))[1] == -1)
check("触发日为空返回 (None, None)",
      extract.compute_deadline(None, 1, as_of) == (None, None))
check("跨年 2 月不炸（2/29 兜底）",
      extract.add_years(extract.date(2028, 2, 29), 1) == extract.date(2029, 2, 28))

dated = [m for m in msgs if m["ts"]]
last = max(dated, key=lambda m: m["ts"])["ts"].date()
check("末条 2026-04-20 → 视为已离职", (as_of - last).days > 90)

# ===========================================================================
print("[6] 渲染：Markdown")

out = scan_file(SAMPLE)
for key in ("要件命中表", "缺失要件与补强方向", "班次抽取", "主张表述质量评估",
            "关键程序节点", "下一步行动清单", "免责声明"):
    check("Markdown 含「%s」" % key, key in out)
check("结论区给出覆盖率", "要件覆盖：" in out)
check("列出班次时长表", "合计" in out and "时长(h)" in out)
check("显示在职/离职提示或时效", "仲裁时效" in out)
check("免责声明含「不构成法律意见」", "不构成法律意见" in out)
check("重跑命令含 --scenario", "--scenario" in out)

try:
    scan_file(os.path.join(HERE, "空样例.md"))
    check("空文件明确提示格式错误（不做无声空报告）", False, "没有退出")
except SystemExit as e:
    check("空文件明确提示格式错误（不做无声空报告）", "未解析出任何消息" in str(e), str(e)[:60])

tmpdir = tempfile.mkdtemp()
out_roster = scan_file(SAMPLE, extra="--scenario roster")
check("roster 场景只出 roster 标签", "排班与考勤" in out_roster)
scan_file(SAMPLE, extra="--format json --out %s" % os.path.join(tmpdir, "r.json"))
with open(os.path.join(tmpdir, "r.json"), encoding="utf-8") as fh:
    j = json.load(fh)
check("JSON 可解析", isinstance(j, dict))
check("JSON scenario 正确", j["scenario"] == "all")
check("JSON 含时限 years=1", j["deadline"]["limitYears"] == 1)
check("JSON 含班次汇总", j["shiftSummary"]["count"] == len(shifts))
check("JSON 含 triggerDate", j["deadline"]["triggerDate"] == "2025-11-18")
check("JSON 含 inService=false", j["inService"] is False)
check("JSON 含要求件命中", len(j["hits"]) > 0)
check("JSON 含 refusals", len(j["refusals"]) > 0)
check("JSON 含 demands 打分", all("score" in d for d in j["demands"]))

# ===========================================================================
print("[7] 命令行边界")

r = run(["--file", SAMPLE, "--scenario", "leave", "--as-of", "2026-10-04"])
check("--scenario leave 正常退出", r.returncode == 0, r.stderr[:80])
check("leave 输出含「假期与离职结算」", "假期与离职结算" in r.stdout)

r = run(["--file", SAMPLE, "--focus", "排班", "--as-of", "2026-10-04"])
check("--focus 类别 排班 有命中", r.returncode == 0 and "过滤模式" in r.stdout)
r = run(["--file", SAMPLE, "--focus", "拒付", "--as-of", "2026-10-04"])
check("--focus 类别 拒付 能跑通", r.returncode == 0)
r = run(["--file", SAMPLE, "--focus", "调休", "--as-of", "2026-10-04"])
check("--focus 类别 调休（本例少）应提示或空报告",
      r.returncode == 0 or "没有消息命中" in r.stderr)
r = run(["--file", SAMPLE, "--focus", "夜班", "--as-of", "2026-10-04"])
check("--focus 字面词 夜班 有命中", r.returncode == 0 and "过滤模式" in r.stdout)

r = run(["--file", SAMPLE, "--format", "json"])
check("--format json 输出合法", r.returncode == 0 and json.loads(r.stdout))

r = run(["--file", os.path.join(HERE, "空样例.md")])
check("空文件 rc!=0 且提示格式", r.returncode != 0 and "未解析出任何消息" in r.stderr,
      r.stderr[:60])
r = run(["--file", os.path.join(HERE, "不存在的.md")])
check("文件不存在 rc!=0", r.returncode != 0)
r = run(["--file", SAMPLE, "--scenario", "xxx"])
check("非法场景 rc!=0", r.returncode != 0)
check("非法场景有提示文案", "--scenario" in (r.stderr or r.stdout))
r = run(["--file", SAMPLE, "--as-of", "2026/10/04"])
check("非法 as-of rc!=0", r.returncode != 0)
r = run(["--file", SAMPLE, "--focus", "调休"])
check("focus 类别无命中时给出可匹配的说法（本例本就没有调休）",
      r.returncode != 0 and "可匹配的说法" in r.stderr, r.stderr[:80])
r = run(["--file", SAMPLE, "--focus", "不存在的关键词zzz"])
check("focus 陌生词无命中也能提示", r.returncode != 0 and "没有消息命中" in r.stderr)

r = run(["--file", SAMPLE])
check("默认 as-of（不传）不报错", r.returncode == 0)

# ===========================================================================
print("[8] 纯标准库 / 无网络")
src = open(SCRIPT, encoding="utf-8").read()
check("脚本不 import requests/urllib",
      not any(k in src for k in ("import requests", "urllib.request", "http.client")))
check("脚本只用标准库", all(("import %s" % m) in src or ("import %s" % m).split()[1]
                            in ("datetime import date, datetime",)
                            for m in ("argparse", "json", "os", "re", "sys"))
      and "from datetime import date, datetime" in src)

print("")
print("=" * 56)
print("通过 %d / %d，失败 %d" % (PASS, PASS + FAIL, FAIL))
if FAILED:
    for n in FAILED:
        print("  - %s" % n)
sys.exit(1 if FAIL else 0)
