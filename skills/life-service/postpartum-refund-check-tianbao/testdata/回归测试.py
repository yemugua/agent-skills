# -*- coding: utf-8 -*-
import os, sys, io, subprocess, tempfile, json

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
SCRIPT = os.path.join(SKILL_DIR, "scripts", "postpartum_refund_check.py")
PY = r"C:\Users\Ti'an'bao\.workbuddy\binaries\python\versions\3.13.12\python.exe"

n_pass = 0
n_fail = 0
fail_msgs = []


def chk(name, cond):
    global n_pass, n_fail
    if cond:
        n_pass += 1
    else:
        n_fail += 1
        fail_msgs.append(name)


def run(md, extra=None):
    cmd = [PY, SCRIPT, md] + (extra or [])
    p = subprocess.run(cmd, capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def write_tmp(text):
    fd, path = tempfile.mkstemp(suffix=".md", dir=HERE)
    os.close(fd)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


SECTIONS = ["一、结论摘要", "二、服务类型与机构", "三、合同与主体一致性",
            "四、付款与预付费退费口径", "五、产妇与新生儿健康损害识别",
            "六、证据清单与固定要点", "七、维权与投诉路径", "八、待办补正动作",
            "九、边界与纪律"]

sample = os.path.join(HERE, "样例.md")
empty = os.path.join(HERE, "空输入.md")

# --- 空输入 ---
rc_e, out_e = run(empty)
chk("空输入 rc==2", rc_e == 2)
chk("空输入 含 待补正", "待补正" in out_e)
chk("空输入 提 核心信息缺失", "核心信息缺失" in out_e)

# --- 样例：护理不当致住院 + 主体不一致 ---
rc_s, out_s = run(sample)
chk("样例 rc==0", rc_s == 0)
for s in SECTIONS:
    chk("样例 含段 " + s, s in out_s)
chk("样例 结论 不通过", "**不通过**" in out_s)
chk("样例 命中母婴损害识别", "涉及产妇或新生儿健康损害" in out_s)
chk("样例 命中合同主体", "上海某健康管理有限公司" in out_s)
chk("样例 命中收款个人", "张某" in out_s)
chk("样例 命中微信直转", "微信直转" in out_s)
chk("样例 命中主体不一致", "合同主体与收款主体不一致" in out_s)
chk("样例 含 风险项", "风险项" in out_s)
chk("样例 含 高危项", "高危项" in out_s)
chk("样例 含 12315", "12315" in out_s)
chk("样例 含 卫健", "卫健" in out_s)
chk("样例 含 病历", "病历" in out_s)
chk("样例 含 ¥88000", "¥88000" in out_s)
chk("样例 含 预付费", "预付费" in out_s)
chk("样例 含 对公凭证提示", "对公凭证" in out_s)
chk("样例 含 立即就医封存", "立即就医并封存病历票据" in out_s)
chk("样例 含 市场监管", "市场监管" in out_s)
chk("样例 含 公安", "公安" in out_s)
chk("样例 含 人民法院", "人民法院" in out_s)
chk("样例 含 证据已具备", "已具备" in out_s)
chk("样例 含 按未履约部分比例退费", "按未履约部分比例退费" in out_s)

# --- 样例 JSON ---
rc_j, out_j = run(sample, ["--json"])
try:
    dj = json.loads(out_j)
    chk("样例 json 可解析", True)
    chk("样例 json 含 结论", "结论" in dj)
    chk("样例 json 结论 不通过", "不通过" in dj.get("结论", ""))
    chk("样例 json 含 合同主体状态", "合同主体状态" in dj)
    chk("样例 json 含 付款状态", "付款状态" in dj)
    chk("样例 json 含 损害状态", "损害状态" in dj)
    chk("样例 json 损害状态 不通过", dj.get("损害状态") == "不通过")
    chk("样例 json 含 证据已具备", "证据已具备" in dj)
    chk("样例 json 含 证据缺失", "证据缺失" in dj)
except Exception as e:
    chk("样例 json 可解析", False)

# --- 边界：无合同(否)+对公+无损害 → 有风险 ---
p1 = write_tmp("# t1\n| 字段 | 值 |\n| 服务类型 | 月子中心 |\n| 问题描述 | 服务缩水 |\n| 已付金额 | 30000 |\n| 有无合同 | 否 |\n| 付款方式 | 对公转账 |\n| 是否预付费 | 是 |\n| 损害情况 | 无 |\n")
rc1, o1 = run(p1)
chk("t1 rc==0", rc1 == 0)
chk("t1 含 未签订书面合同", "未签订书面合同" in o1)
chk("t1 结论 有风险", "**有风险**" in o1)
chk("t1 含 部分环节存在风险", "部分环节存在风险" in o1)
os.remove(p1)

# --- 边界：yesno 否定（没有合同） ---
p2 = write_tmp("# t2\n| 字段 | 值 |\n| 服务类型 | 月子中心 |\n| 问题描述 | x |\n| 已付金额 | 10000 |\n| 有无合同 | 没有 |\n| 付款方式 | 对公 |\n| 是否预付费 | 否 |\n| 损害情况 | 无 |\n")
rc2, o2 = run(p2)
chk("t2 含 未签订书面合同(没有→否)", "未签订书面合同" in o2)
os.remove(p2)

# --- 边界：已付金额=待填 视为缺失 → rc2 待补正 ---
p3 = write_tmp("# t3\n| 字段 | 值 |\n| 服务类型 | 月子中心 |\n| 问题描述 | x |\n| 已付金额 | 待填 |\n| 有无合同 | 是 |\n| 付款方式 | 对公 |\n| 是否预付费 | 否 |\n| 损害情况 | 无 |\n")
rc3, o3 = run(p3)
chk("t3 rc==2(已付金额缺失)", rc3 == 2)
chk("t3 含 待补正", "待补正" in o3)
os.remove(p3)

# --- 边界：全填且非预付无损害 → 通过 ---
p4 = write_tmp("# t4\n| 字段 | 值 |\n| 服务类型 | 月子中心 |\n| 问题描述 | 正常履约，申请部分退费 |\n| 已付金额 | 50000 |\n| 有无合同 | 是 |\n| 合同主体 | 甲公司 |\n| 收款主体 | 甲公司 |\n| 付款方式 | 对公转账 |\n| 是否预付费 | 否 |\n| 损害情况 | 无 |\n| 证据留存 | 合同、付款记录、聊天记录 |\n")
rc4, o4 = run(p4)
chk("t4 rc==0", rc4 == 0)
chk("t4 结论 通过", "**通过**" in o4)
chk("t4 含 核心环节未见重大风险", "核心环节未见重大风险" in o4)
chk("t4 含 证据已具备", "已具备" in o4)
os.remove(p4)

# --- 边界：空文件 ---
p5 = write_tmp("")
rc5, o5 = run(p5)
chk("空文件 rc==2", rc5 == 2)

# --- 边界：不存在文件 ---
rc6, o6 = run(os.path.join(HERE, "不存在.md"))
chk("不存在文件 rc==2", rc6 == 2)

summary = "PASS=%d FAIL=%d" % (n_pass, n_fail)
with io.open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as f:
    f.write(summary + "\n")
    for m in fail_msgs:
        f.write("FAIL: " + m + "\n")

print(summary)
for m in fail_msgs:
    print("FAIL:", m)
sys.exit(0 if n_fail == 0 else 1)
