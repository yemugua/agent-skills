# -*- coding: utf-8 -*-
"""恋爱避坑与关系健康核查。

输入：templates/关系信息采集表.md 填好的表单（字段：值）。
输出：结构化核查报告（关系健康度 / 红旗清单 / 安全建议 / 待办补正 / 边界）。
"""
import sys, os, re

REQ = [
    ("相识渠道", "channel"), ("是否已视频或线下见面", "met"),
    ("对方身份是否可核实", "identity"), ("是否索要或诱导转账消费", "ask_money"),
    ("是否推荐投资理财博彩平台", "ask_invest"), ("情感推进节奏", "pace"),
    ("是否出现贬低打压言行", "belittle"), ("是否冷热交替制造焦虑", "hotcold"),
    ("是否限制社交或要求隐私", "isolate"), ("是否查岗控制行踪", "control"),
    ("是否有共同好友或第三方可验证", "third"), ("交往时长(天)", "days"),
    ("你当前感受", "feeling"), ("其他情况说明", "note"),
]

# 红旗关键词
FLAG_MONEY = ("是", "有", "曾", "让", "要", "已转", "要求")
FLAG_PUA = ("是", "有", "常", "经常", "总", "总是", "会")
PACE_FAST = ("几天", "一周", "很快", "迅速", "刚认识", "当天", "次日")


def get_text(fs, key):
    return (fs.get(key) or "").strip()


def parse_md(text):
    fs = {}
    for line in text.splitlines():
        # 容忍行首的列表符号（- / * / 数字.）
        m = re.match(r"^\s*(?:[-*]\s+|\d+[.、]\s*)?([\u4e00-\u9fa5A-Za-z0-9（）()／/ ]+?)\s*[:：]\s*(.*)$", line)
        if m:
            fs[m.group(1).strip()] = m.group(2).strip()
    return fs


def yes(s):
    return any(w in s for w in ("是", "有", "已", "会", "常", "经", "总", "让", "要", "曾"))


def judge(fs):
    risks = []
    flags = []  # 命中红旗明细
    advice = []
    todos = []
    missing = [k for k, _ in REQ if not get_text(fs, k)]
    if missing:
        risks.append("缺字段：" + "、".join(missing))
        todos.append("补全缺失字段：" + "、".join(missing))

    met = yes(get_text(fs, "是否已视频或线下见面"))
    identity = yes(get_text(fs, "对方身份是否可核实"))
    ask_money = yes(get_text(fs, "是否索要或诱导转账消费"))
    ask_invest = yes(get_text(fs, "是否推荐投资理财博彩平台"))
    belittle = yes(get_text(fs, "是否出现贬低打压言行"))
    hotcold = yes(get_text(fs, "是否冷热交替制造焦虑"))
    isolate = yes(get_text(fs, "是否限制社交或要求隐私"))
    control = yes(get_text(fs, "是否查岗控制行踪"))
    third = yes(get_text(fs, "是否有共同好友或第三方可验证"))
    pace = get_text(fs, "情感推进节奏")

    # 骗财红旗（杀猪盘 / 情感投资诈骗）
    if ask_money or ask_invest:
        flags.append("骗财红旗：对方存在索要/诱导转账或推荐投资理财博彩平台——典型杀猪盘特征")
        advice.append("立刻停止一切转账、充值、投资；保留聊天与转账记录截图")
        advice.append("通过官方渠道核实对方身份；如已转账，尽快联系银行/平台并尝试止付，同时报警")
        todos.append("整理：对方账号、平台名称、转账凭证、聊天记录，作为报案与止付证据")

    # 情感操控红旗（PUA / 控制）
    puas = []
    if belittle:
        puas.append("系统性贬低打压")
    if hotcold:
        puas.append("冷热交替制造焦虑与依赖")
    if isolate:
        puas.append("限制社交圈/索要隐私")
    if control:
        puas.append("查岗控制行踪")
    if puas:
        flags.append("情感操控红旗（PUA/控制）：" + "、".join(puas))
        advice.append("记录对方言行时间线；与可信亲友同步情况，避免被孤立")
        advice.append("设定底线：任何让你长期自我怀疑、恐惧或孤立的关系都应暂停接触")
        todos.append("记录具体事件（时间/原话/场景），作为自我判断与求助依据")

    # 闪恋索财风险
    if any(w in pace for w in PACE_FAST) and (ask_money or ask_invest):
        flags.append("闪恋索财风险：极短时间确认关系后随即出现财物/投资要求")

    # 身份不透明红旗
    if (not met) and (not identity):
        flags.append("身份不透明红旗：未见面且身份无法核实，人设完美需警惕")
        todos.append("要求一次真实视频或线下公共场所见面，拒绝则高度存疑")

    # 健康度判定
    if ask_money or ask_invest or len(puas) >= 2:
        level = "高风险"
        if not flags:
            pass
        risks.append("存在高危红旗，建议立即提高警惕并采取自我保护")
    elif flags:
        level = "需警惕"
        risks.append("存在风险红旗，建议放慢节奏、多方核实")
    elif met and identity and third:
        level = "相对健康"
        advice.append("继续保持理性沟通；涉及大额财物往来前仍建议与亲友商量")
    else:
        level = "信息不足，暂判存疑"
        todos.append("补全见面/身份/第三方验证等信息后重核")

    # 通用安全建议
    if flags or risks:
        advice.append("保留全部聊天记录、转账凭证、对方信息，必要时作为证据")
        advice.append("不要向对方透露银行卡密码、验证码、身份证号等敏感信息")
        advice.append("感觉被操控或财产损失，及时向亲友求助或拨打 110 / 反诈专线 96110")

    return level, flags, risks, advice, todos


def main():
    if len(sys.argv) < 2:
        print("用法: relationship_safety_check.py <输入md>")
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
        print("# 恋爱避坑与关系健康核查报告\n\n## 结论摘要")
        print("关系健康度：待补正（输入为空，未提供任何关系信息）")
        print("\n## 边界与纪律")
        print("- 请提供至少一项关系信息后再核查。")
        return 2
    level, flags, risks, advice, todos = judge(fs)
    print("# 恋爱避坑与关系健康核查报告\n")
    print("## 结论摘要")
    print("关系健康度：**%s**" % level)
    print("\n## 红旗清单")
    if flags:
        for fl in flags:
            print("- %s" % fl)
    else:
        print("- 未发现明确红旗（仍请以官方认定与自身感受为准）")
    print("\n## 风险提示")
    if risks:
        for r in risks:
            print("- %s" % r)
    else:
        print("- 无")
    print("\n## 安全与理智建议")
    if advice:
        for a in advice:
            print("- %s" % a)
    else:
        print("- 保持理性沟通，涉及财物往来前与亲友商量")
    print("\n## 待办补正动作")
    if todos:
        for t in todos:
            print("- %s" % t)
    else:
        print("- 无")
    print("\n## 边界与纪律")
    print("- 本技能不替代心理咨询、公安或司法意见，最终以官方认定为准。")
    print("- 不提供心理咨询诊断、约会撮合或情感代理服务，只做识别指引与自我保护提示。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
