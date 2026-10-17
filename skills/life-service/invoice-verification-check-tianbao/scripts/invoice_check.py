# -*- coding: utf-8 -*-
"""发票报销合规自查与真伪识别。

输入：templates/发票信息采集表.md 填好的表单（字段：值 或 两列表）。
输出：结构化核查报告（结论 / 待办补正 / 风险提示 / 边界）。
"""
import sys, os, re

REQ = [
    ("发票代码", "invoice_code"), ("发票号码", "invoice_no"), ("开票日期", "date"),
    ("销售方名称", "seller"), ("销售方税号", "seller_tax"),
    ("购买方名称", "buyer"), ("购买方税号", "buyer_tax"),
    ("价税合计", "total"), ("货物或应税劳务名称", "item"),
]


def get_text(fs, key):
    return (fs.get(key) or "").strip()


def parse_md(text):
    fs = {}
    # 字段：值
    for line in text.splitlines():
        m = re.match(r"^\s*([\u4e00-\u9fa5A-Za-z0-9（）()／/ ]+?)\s*[:：]\s*(.*)$", line)
        if m:
            fs[m.group(1).strip()] = m.group(2).strip()
    return fs


def judge(fs):
    """返回 (结论, 风险点列表, 待办列表)。"""
    missing = [k for k, _ in REQ if not get_text(fs, k)]
    risks = []
    todos = []

    buyer = get_text(fs, "购买方名称")
    buyer_tax = get_text(fs, "购买方税号")
    seller_tax = get_text(fs, "销售方税号")
    verified = get_text(fs, "是否已查验").lower()
    dup = get_text(fs, "是否重复报销").lower()
    real = get_text(fs, "是否真实交易").lower()
    total = get_text(fs, "价税合计")
    item = get_text(fs, "货物或应税劳务名称")
    note = get_text(fs, "备注")

    # 缺失字段
    if missing:
        risks.append("缺字段：" + "、".join(missing))
        todos.append("补全缺失字段：" + "、".join(missing))

    # 抬头税号相符
    if buyer and ("公司" in buyer or "企业" in buyer or "工作室" in buyer) and buyer_tax:
        if not re.search(r"^[A-Z0-9]{15,20}$", buyer_tax.replace(" ", "")):
            risks.append("购买方税号格式异常")
            todos.append("核对购买方税号是否为有效统一社会信用代码")

    # 真伪查验
    if "是" not in verified and "已" not in verified:
        risks.append("尚未完成官方真伪查验，无法确认真伪")
        todos.append("登录「国家税务总局全国增值税发票查验平台」输入发票代码/号码/日期/金额完成查验")

    # 重复报销
    if "是" in dup or "重复" in dup:
        risks.append("存在重复报销风险（同一张票已报过）")
        todos.append("立即从报销流程中剔除，避免重复入账")

    # 真实交易 / 虚开
    if "否" in real or "不" in real or "假" in real:
        risks.append("非真实交易——虚开发票高风险，绝对不可报销/入账")
        todos.append("拒收并保留证据，必要时向税务机关举报")

    # 骗局信号
    if seller_tax and not re.search(r"^[A-Z0-9]{15,20}$", seller_tax.replace(" ", "")):
        risks.append("销售方税号异常，疑似虚假发票")
        todos.append("核验销售方税号真实性")
    if ("个人" in buyer) and ("公司" in seller_tax or "企业" in get_text(fs, "销售方名称")):
        risks.append("个人抬头却开公司发票，抬头不符")
        todos.append("要求重开为单位抬头发票")
    if total and ("万" in total) and (not item or len(item) < 4):
        risks.append("大额但无明细，疑似不合规发票")
        todos.append("补充货物明细清单")

    if any("虚开" in r or "重复报销" in r for r in risks):
        return "不建议报销", risks, todos
    if missing or any("尚未完成" in r or "异常" in r or "不符" in r for r in risks):
        return "需补正后再报", risks, todos
    return "可以报销（请完成官方查验后留存）", risks, todos


def main():
    if len(sys.argv) < 2:
        print("用法: invoice_check.py <输入md>")
        return 2
    p = sys.argv[1]
    if not os.path.exists(p):
        print("文件不存在: %s" % p)
        return 2
    with open(p, encoding="utf-8") as f:
        text = f.read()
    fs = parse_md(text)
    filled = sum(1 for k, _ in REQ if get_text(fs, k))
    if filled == 0:
        print("# 发票报销合规自查报告\n\n## 结论摘要")
        print("能否报销：待补正（输入为空，未提供任何发票信息）")
        print("\n## 边界与纪律")
        print("- 请提供至少一项发票要素后再核查。")
        return 2
    concl, risks, todos = judge(fs)
    print("# 发票报销合规自查报告\n")
    print("## 结论摘要")
    print("能否报销：%s" % concl)
    print("\n## 风险提示")
    if risks:
        for r in risks:
            print("- %s" % r)
    else:
        print("- 未发现明显风险点（仍以官方查验为准）")
    print("\n## 待办补正动作")
    if todos:
        for t in todos:
            print("- %s" % t)
    else:
        print("- 无")
    print("\n## 边界与纪律")
    print("- 本技能不联网查验，真伪以国家税务总局全国增值税发票查验平台结果为准。")
    print("- 不提供任何避税、虚开发票或财务造假的方法与指导。")
    print("- 不替代财务/税务专业意见，最终以税务机关与本单位财务制度认定为准。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
