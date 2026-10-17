# -*- coding: utf-8 -*-
"""一消《技术实务》备考题库与速记 —— 题库抽题与自测引擎"""
import sys, random, re
sys.stdout.reconfigure(encoding="utf-8")

SECTIONS = [('建筑防火', ['建筑分类与耐火等级判定', '总平面布局与防火间距', '防火分区与防火分隔', '安全疏散距离计算']), ('各类建筑防火', ['民用建筑防火', '厂房与仓库防火', '加油加气站防火', '地铁与城市隧道防火']), ('消防设施', ['消火栓系统', '自动喷水系统', '火灾自动报警系统', '其他灭火设施']), ('安全管理', ['消防安全管理基础', '易燃易爆场所防火', '灭火救援设施', '消防法律法规'])]
INTRO = '一级注册消防工程师《技术实务》题库与速记卡片，按四大考点域抽题训练。'

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
        out.append("# 一消《技术实务》备考题库与速记 · 随机抽题（%d 题）" % len(sel))
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
        out.append("# 一消《技术实务》备考题库与速记 · 完整题库（%d 题）" % len(bank))
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
