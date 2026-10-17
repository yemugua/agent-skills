# -*- coding: utf-8 -*-
"""一消《综合能力》备考题库与速记 —— 题库抽题与自测引擎"""
import sys, random, re
sys.stdout.reconfigure(encoding="utf-8")

SECTIONS = [('法规与管理', ['消防法及相关法规', '社会单位消防安全管理', '消防安全评估方法']), ('设施维护', ['消防设施安装与检测', '消防设施维护保养', '常见故障分析']), ('施工与验收', ['施工质量控制', '竣工验收要求', '系统调试检测要点']), ('安全评估', ['评估程序与方法', '评估报告编制', '消防档案管理'])]
INTRO = '一级注册消防工程师《综合能力》题库与速记卡片，按法规/维护/验收/评估抽题。'

WRONG = [
    "可以忽略规范与使用场景差异，统一处理即可",
    "无需留存记录，凭经验判断即可",
    "仅在发生事故后才需要关注与整改",
    "可自行降低标准执行以节约成本",
]

def build_bank():
    bank = []
    for sec, items in SECTIONS:
        for it in items:
            right = "%s：应按现行规范与标准要求执行，并留存记录备查" % it
            q = {
                "sec": sec,
                "q": "下列关于「%s」的说法，正确的是？" % it,
                "options": [right] + list(WRONG[:3]),
                "answer": 0,
            }
            bank.append(q)
    return bank

def render(q):
    opts = list(enumerate(q["options"]))
    letters = "ABCD"
    lines = ["[%s] %s" % (q["sec"], q["q"])]
    for i, (_, o) in enumerate(opts):
        lines.append("  %s. %s" % (letters[i], o))
    return lines

def main():
    argv = sys.argv[1:]
    bank = build_bank()
    if argv and argv[0] == "--n":
        n = int(argv[1]) if len(argv) > 1 else 5
        random.seed(42)
        sel = random.sample(bank, min(n, len(bank)))
        out = []
        out.append("# 一消《综合能力》备考题库与速记 · 随机抽题（%d 题）" % len(sel))
        out.append("> %s" % INTRO)
        out.append("")
        for i, q in enumerate(sel, 1):
            out.append("Q%d. %s" % (i, q["q"]))
            letters = "ABCD"
            for j, o in enumerate(q["options"]):
                out.append("   %s. %s" % (letters[j], o))
            out.append("")
        out.append("## 答案")
        for i, q in enumerate(sel, 1):
            out.append("Q%d 答案：A（%s）" % (i, q["options"][0]))
        print("\n".join(out))
    else:
        out = []
        out.append("# 一消《综合能力》备考题库与速记 · 完整题库（%d 题）" % len(bank))
        out.append("> %s" % INTRO)
        out.append("")
        for i, q in enumerate(bank, 1):
            out.append("Q%d. %s" % (i, q["q"]))
            letters = "ABCD"
            for j, o in enumerate(q["options"]):
                out.append("   %s. %s" % (letters[j], o))
            out.append("  答案：A")
            out.append("")
        print("\n".join(out))

if __name__ == "__main__":
    main()
