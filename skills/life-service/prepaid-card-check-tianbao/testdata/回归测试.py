# -*- coding: utf-8 -*-
import sys, pathlib, importlib.util, json, subprocess

HERE = pathlib.Path(__file__).parent
SCR = HERE.parent / "scripts" / "prepaid_card_check.py"
spec = importlib.util.spec_from_file_location("pc", str(SCR))
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)

rc = 0
total = 0
fails = []
def chk(name, cond):
    global rc, total
    total += 1
    if not cond:
        fails.append(name); rc += 1

def has(items, name, state):
    return any(n == name and s == state for n, s, m in items)

def has_not(items, name, state):
    return not has(items, name, state)

def mk(**kw):
    f = {k: "" for k, _ in T.build_fields()}
    f.update(kw)
    return f

sample = (HERE / "样例.md").read_text(encoding="utf-8")
empty = (HERE / "空输入.md").read_text(encoding="utf-8")

# ---- 解析 ----
d = T.parse_md(sample)
chk("解析商家名", d.get("商家/发卡方名称", "") == "锐健身（上海杨浦店）")
chk("解析总额", d.get("预付总额（元）", "") == "8000")
chk("解析状态", "门店已转让" in d.get("商家当前经营状态", ""))
e = T.parse_md(empty)
chk("空输入解析无残留", all(v == "" for v in e.values()))

# extract 集成
f_all = T.extract({"_raw": sample})
for k, v in d.items():
    for key, alias in T.FIELD_ALIAS.items():
        if T.norm(k) in [T.norm(a) for a in alias] or T.norm(k) == T.norm(key):
            f_all[key] = v
chk("extract行业", f_all["industry"] == "健身私教")
chk("extract总额", f_all["total_paid"] == "8000")
chk("extract状态含失联", "失联" in f_all["merchant_status"])
chk("extract条款含概不退款", "概不退款" in f_all["refund_clause"])
chk("extract投诉未投诉", "还没投诉" in f_all["complaint_tried"])

# ---- classify ----
chk("分类健身", "健身私教预付" in T.classify(f_all))
chk("分类跑路", "商家跑路/失联" in T.classify(f_all))
chk("分类格式条款", "格式条款不退" in T.classify(f_all))
chk("分类空=空列表", T.classify(mk()) == [])

# ---- checks_status ----
st_run = T.checks_status(mk(merchant_status="老板跑路失联"))
chk("状态跑路不通过", has(st_run, "商家经营状态", "不通过"))
st_norm = T.checks_status(mk(merchant_status="正常营业照常"))
chk("状态正常有风险", has(st_norm, "商家经营状态", "有风险"))
chk("状态正常不通过", has_not(st_norm, "商家经营状态", "不通过"))
st_unk = T.checks_status(mk(merchant_status=""))
chk("状态未填待补正", has(st_unk, "商家经营状态", "待补正"))
st_trans = T.checks_status(mk(merchant_status="门店转让换老板"))
chk("状态转让有风险", has(st_trans, "商家经营状态", "有风险"))

# ---- checks_contract ----
ct_none = T.checks_contract(mk(contract="无"))
chk("无合同有风险", has(ct_none, "合同与条款", "有风险"))
ct_bad = T.checks_contract(mk(refund_clause="会员卡一经售出概不退款"))
chk("概不退款不通过", has(ct_bad, "退款条款效力", "不通过"))
ct_ok = T.checks_contract(mk(refund_clause="未消费余额随时退"))
chk("随时退通过", has(ct_ok, "退款条款效力", "通过"))
ct_unk = T.checks_contract(mk(contract="", refund_clause=""))
chk("合同未填待补正", has(ct_unk, "合同与条款", "待补正"))
ct_ratio = T.checks_contract(mk(refund_clause="按已消费比例扣除手续费退"))
chk("按比例有风险", has(ct_ratio, "退款条款效力", "有风险"))

# ---- calc_balance ----
chk("余额计算", T.calc_balance(mk(total_paid="8000", consumed="2000")) == (8000.0, 2000.0, 6000.0))
chk("余额无总额", T.calc_balance(mk(total_paid="", consumed="2000")) == (None, None, None))
chk("余额用应退", T.calc_balance(mk(total_paid="8000", consumed="2000", remain_should="5500"))[2] == 5500.0)
chk("余额消费解析", T.calc_balance(mk(total_paid="8000元", consumed="2,000")) == (8000.0, 2000.0, 6000.0))

# ---- checks_balance ----
bl_zero = T.checks_balance(mk(total_paid="8000", consumed="8000"))
chk("余额耗尽有风险", has(bl_zero, "应退金额核算", "有风险"))
bl_pos = T.checks_balance(mk(total_paid="8000", consumed="2000"))
chk("余额为正有风险", has(bl_pos, "应退金额核算", "有风险"))
bl_unk = T.checks_balance(mk(total_paid=""))
chk("余额未填待补正", has(bl_unk, "应退金额核算", "待补正"))

# ---- checks_filed ----
fl_no = T.checks_filed(mk(filed="没有备案"))
chk("未备案有风险", has(fl_no, "备案与监管", "有风险"))
fl_yes = T.checks_filed(mk(filed="已备案"))
chk("已备案通过", has(fl_yes, "备案与监管", "通过"))
fl_unk = T.checks_filed(mk(filed=""))
chk("备案未填待补正", has(fl_unk, "备案与监管", "待补正"))

# ---- checks_evidence ----
ev_many = T.checks_evidence(mk(has_receipt="有合同、转账记录、收据发票、聊天截图、会员卡"))
chk("证据齐全通过", has(ev_many, "证据齐全度", "通过"))
ev_few = T.checks_evidence(mk(has_receipt="只有微信转账"))
chk("证据极少不通过", has(ev_few, "证据齐全度", "不通过"))
ev_mid = T.checks_evidence(mk(has_receipt="合同和转账记录"))
chk("证据中等有风险", has(ev_mid, "证据齐全度", "有风险"))
ev_unk = T.checks_evidence(mk(has_receipt=""))
chk("证据未填待补正", has(ev_unk, "证据齐全度", "待补正"))
chk("证据缺口非空", isinstance(T.evidence_gap(mk(has_receipt="只有转账")), list))

# ---- checks_promise ----
pr_ok = T.checks_promise(mk(promise="随时退不绑定"))
chk("承诺随时退通过", has(pr_ok, "销售承诺", "通过"))
pr_unk = T.checks_promise(mk(promise=""))
chk("承诺未填待补正", has(pr_unk, "销售承诺", "待补正"))

# ---- checks_delay ----
dl_long = T.checks_delay(mk(delay="已拖三个月不回消息拉黑"))
chk("拖延有风险", has(dl_long, "拖延与拒退", "有风险"))
dl_law = T.checks_delay(mk(delay="已经法院起诉立案"))
chk("已立案有风险", has(dl_law, "拖延与拒退", "有风险"))
dl_unk = T.checks_delay(mk(delay=""))
chk("拖延未填待补正", has(dl_unk, "拖延与拒退", "待补正"))

# ---- checks_complaint ----
cp_no = T.checks_complaint(mk(complaint_tried="还没投诉"))
chk("未投诉有风险", has(cp_no, "已尝试渠道", "有风险"))
cp_yes = T.checks_complaint(mk(complaint_tried="打过12315投诉了"))
chk("已投诉通过", has(cp_yes, "已尝试渠道", "通过"))
cp_unk = T.checks_complaint(mk(complaint_tried=""))
chk("投诉未填待补正", has(cp_unk, "已尝试渠道", "待补正"))

# ---- todo / path ----
chk("待办非空", len(T.todo_list(f_all)) >= 3)
chk("路径七步", len(T.path_steps(f_all)) == 7)
chk("跑路触发报警待办", any("报案" in t or "公安机关" in t for t in T.todo_list(mk(merchant_status="老板跑路"))))

# ---- render ----
rep = T.render(f_all)
chk("报告含十二段", rep.count("## ") >= 12)
chk("报告有结论摘要", "## 一、结论摘要" in rep)
chk("报告有边界", "## 十二、边界与纪律" in rep)
chk("样例报告含不通过", "不通过" in rep)
chk("样例报告含应退金额", "6000" in rep or "¥6,000" in rep or "6000.00" in rep)
rep_empty = T.render(mk())
chk("空报告不崩", isinstance(rep_empty, str) and rep_empty.count("## ") >= 12)

# ---- to_json ----
jj = T.to_json(f_all)
chk("json有结论", "结论" in jj)
chk("json有类型", isinstance(jj["类型"], list) and len(jj["类型"]) > 0)
chk("json有风险项", isinstance(jj["风险项"], list) and len(jj["风险项"]) > 0)
chk("json有待办", isinstance(jj["待办"], list))
chk("json应退余额", jj["应退余额"] == 6000.0)

# ---- 端到端跑脚本 ----
py = sys.executable
SAMPLE_PATH = str(HERE / "样例.md")
EMPTY_PATH = str(HERE / "空输入.md")
r1 = subprocess.run([py, str(SCR), SAMPLE_PATH], capture_output=True, text=True, encoding="utf-8")
chk("端到端退出0", r1.returncode == 0)
chk("端到端有摘要", "## 一、结论摘要" in r1.stdout)
chk("端到端有失联不通过", "不通过" in r1.stdout)
r2 = subprocess.run([py, str(SCR), EMPTY_PATH], capture_output=True, text=True, encoding="utf-8")
chk("空输入退出0", r2.returncode == 0)
chk("空输入不崩", "## 一、结论摘要" in r2.stdout)
rj = subprocess.run([py, str(SCR), SAMPLE_PATH, "--json"], capture_output=True, text=True, encoding="utf-8")
chk("json模式退出0", rj.returncode == 0)
try:
    parsed = json.loads(rj.stdout)
    chk("json可解析", isinstance(parsed, dict))
except Exception:
    chk("json可解析", False)

# ---- bug 规则专项 ----
no_contract_states = [s for _, s, _ in T.checks_contract(mk(contract="没有合同协议"))]
chk("无合同绝不通过", "通过" not in no_contract_states)
filed_states = [s for _, s, _ in T.checks_filed(mk(filed="未备案"))]
chk("未备案绝不通过", "通过" not in filed_states)
run_states = [s for _, s, _ in T.checks_status(mk(merchant_status="人去楼空卷款跑路"))]
chk("失联必不通过", "不通过" in run_states)

# ---- 结案 ----
out = "PASS=%d FAIL=%d\n" % (total - rc, rc)
if fails:
    out += "FAIL_LIST:\n" + "\n".join(fails[:40])
HERE.joinpath("_reg_result.txt").write_text(out, encoding="utf-8")
print(out)
sys.exit(1 if rc else 0)
