# -*- coding: utf-8 -*-
"""遗嘱效力自查与订立核查 v1.0.0

输入：按 templates/遗嘱信息采集表.md 填写的 Markdown
输出：九段式核查报告（或 --json 摘要）

判定纪律：
- 依《民法典》继承编通用条文做形式要件核对，不替代律师意见
- 不代拟遗嘱正文、不代办公证、不预测诉讼结果
- 用户填什么就用什么，未填的一律标「未填」，不算通过
"""
import argparse
import datetime as dt
import json
import os
import sys

VERSION = "1.0.0"

PLACEHOLDER = (
    "【待填】",
    "填什么",
    "是 / 否",
    "有 / 无",
    "___",
)

FORMS = ("自书", "代书", "打印", "录音录像", "口头", "公证")


def norm(s):
    if s is None:
        return ""
    t = str(s)
    t = t.replace("\u3000", " ").replace(" ", "")
    t = t.replace("\uff08", "(").replace("\uff09", ")")
    t = t.replace("|", " ").strip()
    return t


def clean(s):
    if s is None:
        return ""
    return str(s).strip().strip("|").strip()


def is_ph(v):
    t = norm(v)
    if not t:
        return True
    for w in PLACEHOLDER:
        if norm(w) in t:
            return True
    if t in ("-", "--", "/", "\u2014"):
        return True
    if t and set(t) <= set("-\u2014:=/"):
        return True
    return False


def is_row(ln):
    s = ln.strip()
    return s.startswith("|") and s.count("|") >= 2


def split_row(ln):
    s = ln.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def get_text(text, *labels):
    for line in text.splitlines():
        if not is_row(line):
            continue
        c = split_row(line)
        if len(c) < 2:
            continue
        for lb in labels:
            if norm(lb) in norm(c[0]) and not is_ph(c[1]):
                return clean(c[1])
    return ""


def get_int(text, *labels):
    v = get_text(text, *labels)
    if not v:
        return None
    dig = ""
    for ch in norm(v):
        if ch.isdigit():
            dig += ch
        elif dig:
            break
    if not dig:
        return None
    try:
        return int(dig)
    except Exception:
        return None


def yes(text, *labels):
    v = get_text(text, *labels)
    if not v:
        return None
    t = norm(v)
    if "否" in t or "无" in t or "没" in t:
        return False
    if "是" in t or "有" in t:
        return True
    return None


def pick_form(text):
    for line in text.splitlines():
        if not is_row(line):
            continue
        c = split_row(line)
        if len(c) < 2 or "遗嘱形式" not in norm(c[0]) or "填什么" in norm(c[1]):
            continue
        v = norm(c[1])
        for f in FORMS:
            if f in v:
                return f
    return ""


# ---------------------------------------------------------------- 要件表
# 形式 -> [(要件说明, 取值函数键, 不适用时怎么显示)]
REQUIREMENTS = {
    "自书": [
        ("全文由遗嘱人亲笔书写", "handwrite", "打印出来签名的，不成立自书遗嘱"),
        ("遗嘱人签名", "sign", "缺签名"),
        ("注明年、月、日", "date", "缺日期"),
        ("不需要见证人", None, "—"),
    ],
    "代书": [
        ("两个以上见证人在场见证", "witness_n", "人数不足"),
        ("其中一人代书", None, "由见证人之一执笔"),
        ("遗嘱人、代书人、其他见证人签名", "sign", "缺签名"),
        ("注明年、月、日", "date", "缺日期"),
    ],
    "打印": [
        ("两个以上见证人在场见证", "witness_n", "人数不足"),
        ("遗嘱人和见证人在**每一页**签名", "each_page", "只在最后一页签名 = 要件不全"),
        ("注明年、月、日", "date", "缺日期"),
    ],
    "录音录像": [
        ("两个以上见证人在场见证", "witness_n", "人数不足"),
        ("遗嘱人和见证人在录音录像中记录姓名或者肖像", "av_name", "未记录姓名/肖像"),
        ("录音录像中说明年、月、日", "av_date", "未说明日期"),
    ],
    "口头": [
        ("处于危急情况", "urgent", "非危急情况所立的口头遗嘱无效"),
        ("两个以上见证人在场见证", "witness_n", "人数不足"),
        ("危急情况消除后须重立其他形式", "urgent_over", "危急消除后未重立 = 口头遗嘱无效"),
    ],
    "公证": [
        ("经公证机构办理", None, "由公证机构按程序办理，形式要件由公证处把关"),
        ("建议同步做行为能力留证", "capacity_proof", "不是强制要件，但能大幅降低争议"),
    ],
}


def build_report(path, base=None):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        return None, "读不了文件：%s" % e

    if base is None:
        base = dt.date.today()
    L = []
    A = L.append

    form = pick_form(text)
    name = get_text(text, "立遗嘱人姓名", "姓名")
    age = get_int(text, "年龄")
    sane = get_text(text, "神志清楚")
    disorder = get_text(text, "认知障碍", "精神疾病")
    coerced = get_text(text, "欺诈", "胁迫")

    wdate = get_text(text, "订立日期")
    handwrite = yes(text, "是否亲笔书写", "亲笔书写")
    sign = yes(text, "是否逐页签名")  # 逐页签名也算有签名
    sign_any = yes(text, "是否有遗嘱人签名", "遗嘱人签名")
    has_date = yes(text, "是否注明年月日", "注明年月日")
    pages = get_int(text, "遗嘱页数", "页数")
    each_page = yes(text, "是否逐页签名", "逐页签名")
    av_name = yes(text, "是否记录姓名或肖像", "姓名或肖像")
    av_date = yes(text, "是否说明年月日", "录音录像")

    w_n = get_int(text, "见证人数量")
    w_rel = get_text(text, "见证人与继承人是否亲属关系", "亲属关系")
    w_bene = yes(text, "见证人是否为受益人", "受益人")
    w_all = yes(text, "是否全程在场", "全程在场")
    w_cap = yes(text, "是否有完全民事行为能力", "完全民事行为能力")

    joint = yes(text, "是否处分夫妻共同财产", "夫妻共同财产")
    own_share = yes(text, "是否只处分本人份额", "本人份额")
    sold = yes(text, "是否处分已出售", "已出售")
    inv = yes(text, "是否有财产清单", "财产清单")
    bene_full = yes(text, "受益人是否写全姓名", "写全姓名")

    need_part = yes(text, "缺乏劳动能力又无生活来源", "缺乏劳动能力")
    keep_part = yes(text, "是否为该继承人保留份额", "保留份额")
    multi = yes(text, "是否立有数份遗嘱", "数份遗嘱")
    conflict = yes(text, "数份遗嘱内容是否抵触", "抵触")
    notarized = yes(text, "是否有公证遗嘱", "公证遗嘱")

    executor = yes(text, "是否指定遗嘱执行人", "遗嘱执行人")
    keeper = get_text(text, "遗嘱由谁保管", "保管")
    known = yes(text, "是否有人知道遗嘱在哪", "知道遗嘱在哪")
    cap_proof = yes(text, "行为能力留证", "留证")

    if not form and not any([name, sign_any is not None, w_n is not None]):
        return None, ("未解析到关键信息。至少填写「遗嘱形式」或「是否有遗嘱人签名」"
                      "中的一项，否则无法判断。")

    # ---- 形式要件逐条
    reqs = REQUIREMENTS.get(form, [])
    rows = []
    miss_cnt = 0
    for desc, key, hint in reqs:
        if key is None:
            rows.append((desc, "—", hint))
            continue
        if key == "witness_n":
            v = w_n
            if v is None:
                rows.append((desc, "未填", hint))
                miss_cnt += 1
            elif v >= 2:
                rows.append((desc, "%d 人" % v, "人数满足"))
            else:
                rows.append((desc, "**%d 人（不足）**" % v, hint))
                miss_cnt += 1
        elif key == "sign":
            ok = True if (sign_any or sign) else (False if (sign_any is False and sign is not True) else None)
            rows.append((desc, fmt_flag(ok), hint if ok is not True else "已签"))
            if ok is not True:
                miss_cnt += 1
        elif key == "date":
            rows.append((desc, fmt_flag(has_date), hint if has_date is not True else "已注明"))
            if has_date is not True:
                miss_cnt += 1
        elif key == "handwrite":
            rows.append((desc, fmt_flag(handwrite), hint if handwrite is not True else "是"))
            if handwrite is not True:
                miss_cnt += 1
        elif key == "each_page":
            rows.append((desc, fmt_flag(each_page), hint if each_page is not True else "逐页已签"))
            if each_page is not True:
                miss_cnt += 1
        elif key == "av_name":
            rows.append((desc, fmt_flag(av_name), hint if av_name is not True else "已记录"))
            if av_name is not True:
                miss_cnt += 1
        elif key == "av_date":
            rows.append((desc, fmt_flag(av_date), hint if av_date is not True else "已说明"))
            if av_date is not True:
                miss_cnt += 1
        elif key == "urgent":
            u = yes(text, "危急")
            rows.append((desc, fmt_flag(u), hint if u is not True else "是"))
            if u is not True:
                miss_cnt += 1
        elif key == "urgent_over":
            rows.append((desc, "需人工确认",
                         "危急情况消除后能用书面或录音录像形式立遗嘱的，"
                         "口头遗嘱无效——情况稳定后必须重立"))
        elif key == "capacity_proof":
            rows.append((desc, fmt_flag(cap_proof), "建议补做录像与见证说明"))

    # ---- 见证人资格
    w_issues = []
    if form in ("代书", "打印", "录音录像", "口头"):
        if w_n is None:
            w_issues.append(("见证人数量未填", "填了才能判断"))
        elif w_n < 2:
            w_issues.append(("见证人不足 2 人", "该形式要求两个以上见证人在场"))
        if w_rel and "有" in norm(w_rel):
            w_issues.append(("见证人与继承人有亲属关系",
                             "继承人、受遗赠人及其有利害关系的人不能做见证人 → 该遗嘱可能无效"))
        if w_bene:
            w_issues.append(("见证人是受益人",
                             "继承人、受遗赠人不能做见证人 → 该遗嘱可能无效"))
        if w_all is False:
            w_issues.append(("见证人未全程在场", "必须全程在场见证，中途离开的不算"))
        if w_cap is False:
            w_issues.append(("见证人不具备完全民事行为能力", "无/限制民事行为能力人不能做见证人"))
    else:
        w_issues.append(("%s遗嘱不需要见证人" % form if form else "所选形式不需要见证人",
                         "本项不适用"))

    # ---- 无效与撤回风险
    risks = []
    if sane and ("否" in norm(sane) or "不确定" in norm(sane)):
        risks.append(("立遗嘱时神志存疑",
                      "无/限制民事行为能力人所立遗嘱无效——判断时点是**立遗嘱时**",
                      "补做行为能力留证：录像 + 见证说明 + 近期医疗记录"))
    if disorder and "有" in norm(disorder):
        risks.append(("有认知障碍 / 精神疾病诊断",
                      "事后极易被质疑行为能力",
                      "立遗嘱全过程录像，开头说明姓名、日期、神志状态"))
    if coerced and ("有" in norm(coerced) or "不确定" in norm(coerced)):
        risks.append(("可能存在欺诈或胁迫",
                      "受欺诈、胁迫所立遗嘱无效",
                      "找两位无利害关系见证人全程见证并录像；必要时咨询律师"))
    if sold:
        risks.append(("处分了已出售或已过户的财产",
                      "属于实施了相反民事法律行为，视为撤回该部分；该部分落空",
                      "重立遗嘱，按现有财产重新列清单"))
    if multi and conflict:
        risks.append(("立有数份遗嘱且内容抵触",
                      "以**最后的**为准——《民法典》已取消公证遗嘱优先",
                      "确认哪份时间最晚；重立时在文中写明此前抵触的以本遗嘱为准"))
    if multi and notarized and conflict:
        risks.append(("误以为公证遗嘱优先",
                      "公证不再最优先，只看时间先后",
                      "别依赖公证效力，看重立时间"))
    if not risks:
        risks.append(("未发现无效或撤回风险", "未填的不算通过", "—"))

    # ---- 处分范围
    scope = []
    if joint:
        if own_share is True:
            scope.append(("涉及夫妻共同财产", "已只处分本人份额", "写清权证号与份额"))
        else:
            scope.append(("涉及夫妻共同财产，未明确只处分本人份额",
                          "**超出本人份额的部分无效**",
                          "改写为「本人名下××房产中属于本人的份额」，并附权证号"))
    if sold:
        scope.append(("处分了已出售或已过户的财产", "该部分落空", "重立并按现有财产列"))
    if inv is False:
        scope.append(("没有财产清单", "财产描述不清会在执行时扯皮",
                      "附清单：房产坐落与权证号、银行账户、股权、车辆"))
    if bene_full is False:
        scope.append(("受益人未写全姓名与身份证号", "身份指向不清，可能引发争议",
                      "改成身份证姓名 + 身份证号"))
    if not scope:
        scope.append(("未发现处分范围问题", "未填的不算通过", "—"))

    # ---- 必留份
    reserve = []
    if need_part:
        if keep_part is True:
            reserve.append(("存在需保留份额的继承人", "已保留", "份额是否足够仍可能被争议"))
        else:
            reserve.append(("存在缺乏劳动能力又无生活来源的继承人",
                            "**未保留必要份额的，该部分无效**",
                            "为该继承人保留必要份额，或咨询律师测算"))
    else:
        reserve.append(("未发现需保留份额的继承人", "未填的不算通过",
                        "如有未成年子女、重度残疾无收入子女、无收入无劳动能力父母，要重新核"))
    reserve.append(("胎儿预留份", "如有胎儿，遗产分割时应保留其份额",
                    "胎儿出生为死体的，保留份额按法定继承办理"))

    # ---------------- 报告
    A("# 遗嘱效力自查报告")
    A("")
    A("> 生成日期：%s；脚本版本 v%s" % (base.isoformat(), VERSION))
    A("")

    A("## 一、结论摘要")
    A("")
    if not form:
        A("- **未识别到遗嘱形式**，没法逐条核要件。先填「遗嘱形式」。")
    elif miss_cnt:
        A("- %s遗嘱的形式要件有 **%d 项不齐**，这是最要紧的问题。" % (form, miss_cnt))
    else:
        A("- %s遗嘱的形式要件**已填项全部齐备**（未填的不算通过）。" % form)
    hard = [x for x in w_issues if "无效" in x[1] or "不能做见证人" in x[1]]
    if hard:
        A("- ⚠️ 见证人资格有硬伤：%s。" % "、".join(x[0] for x in hard))
    real_risks = [r for r in risks if r[0] != "未发现无效或撤回风险"]
    if real_risks:
        A("- 扫到 %d 项无效 / 撤回风险：%s。" % (len(real_risks), "、".join(r[0] for r in real_risks)))
    A("- 最大风险点见第二、三段；补正动作见第八段。")
    A("- **未填的一律不算通过**，只按你填了的判断——补填后重跑一次。")
    A("")

    A("## 二、形式要件逐条核查")
    A("")
    if form:
        A("所选形式：**%s遗嘱**%s" % (form, "，订立日期 %s" % wdate if wdate else ""))
        A("")
        A("| 要件 | 实际情况 | 说明 |")
        A("|---|---|---|")
        for d, s, h in rows:
            A("| %s | %s | %s |" % (d, s, h))
    else:
        A("未识别到遗嘱形式，无法逐条核。可选：%s。" % " / ".join(FORMS))
    A("")
    if pages:
        A("遗嘱页数：%d 页%s" % (pages, "（打印遗嘱须逐页签名）" if form == "打印" else ""))
        A("")

    A("## 三、见证人资格审查")
    A("")
    A("| 项 | 结论 |")
    A("|---|---|")
    for k, v in w_issues:
        A("| %s | %s |" % (k, v))
    A("")
    A("资格底线：完全民事行为能力人、不是继承人或受遗赠人、与其无利害关系、"
      "具备见证能力、全程在场、**至少 2 人**。")
    A("")

    A("## 四、无效与撤回风险扫描")
    A("")
    A("| 风险 | 后果 | 怎么办 |")
    A("|---|---|---|")
    for a_, b_, c_ in risks:
        A("| %s | %s | %s |" % (a_, b_, c_))
    A("")

    A("## 五、处分范围核查")
    A("")
    A("| 项 | 后果 | 怎么办 |")
    A("|---|---|---|")
    for a_, b_, c_ in scope:
        A("| %s | %s | %s |" % (a_, b_, c_))
    A("")
    A("不属于遗产、遗嘱处分布了的：指定了受益人的人身保险金、死亡赔偿金、抚恤金。")
    A("")

    A("## 六、必留份与胎儿预留份")
    A("")
    A("| 项 | 结论 | 怎么办 |")
    A("|---|---|---|")
    for a_, b_, c_ in reserve:
        A("| %s | %s | %s |" % (a_, b_, c_))
    A("")

    A("## 七、保管与执行")
    A("")
    A("| 项 | 情况 |")
    A("|---|---|")
    A("| 是否指定遗嘱执行人 | %s |" % fmt_flag(executor))
    A("| 保管人 | %s |" % (keeper or "未填"))
    A("| 是否有人知道遗嘱在哪 | %s |" % fmt_flag(known))
    A("| 是否做过行为能力留证 | %s |" % fmt_flag(cap_proof))
    A("")
    if known is False:
        A("⚠️ 没人知道遗嘱在哪，等于没立——死后找不到，就按法定继承走了。")
        A("")

    A("## 八、待办补正动作")
    A("")
    todo = []
    for d, s, h in rows:
        if "未填" in s or "不足" in s or "缺" in s:
            todo.append("补齐形式要件「%s」：%s" % (d, h))
    for k, v in w_issues:
        if "无效" in v or "不能做见证人" in v or "不算" in v:
            todo.append("处理见证人问题「%s」：%s" % (k, v))
    for a_, b_, c_ in risks:
        if a_ != "未发现无效或撤回风险":
            todo.append("处理风险「%s」：%s" % (a_, c_))
    for a_, b_, c_ in scope:
        if a_ != "未发现处分范围问题":
            todo.append("处理处分范围「%s」：%s" % (a_, c_))
    for a_, b_, c_ in reserve:
        if "未保留" in b_ or "重新核" in c_:
            todo.append("核必留份「%s」：%s" % (a_, c_))
    if known is False:
        todo.append("告诉至少一位可信的人：遗嘱放在哪里")
    if cap_proof is False and (age or 0) >= 70:
        todo.append("做行为能力留证：立遗嘱全过程录像 + 两位见证人的书面见证说明")
    todo.append("附一份财产清单（坐落、权证号、账号、股权），与遗嘱一起保管")
    todo.append("家庭 / 财产 / 意愿重大变化后及时重立，重立时写明此前抵触的以本遗嘱为准")
    for i, t in enumerate(todo, 1):
        A("%d. %s" % (i, t))
    A("")

    A("## 九、输出纪律与免责")
    A("")
    A("- 依《中华人民共和国民法典》继承编通用条文整理，**不替代律师意见**；")
    A("- 不代拟遗嘱正文、不代办公证、不预测诉讼结果；")
    A("- 是否被认定有效，最终以司法机关认定为准；")
    A("- 涉港澳台、涉外、遗嘱信托、宅基地与股权继承等，需另行查证。")
    A("")

    body = "\n".join(L)
    meta = {
        "version": VERSION,
        "form": form,
        "missing_form_items": miss_cnt,
        "witness_issues": len([x for x in w_issues if "无效" in x[1] or "不能做见证人" in x[1]]),
        "risks": len([r for r in risks if r[0] != "未发现无效或撤回风险"]),
        "todo": len(todo),
    }
    return body, meta


def fmt_flag(v):
    if v is True:
        return "是"
    if v is False:
        return "**否**"
    return "未填"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--base", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    base = None
    if a.base:
        try:
            base = dt.date(*[int(x) for x in a.base.split("-")])
        except Exception:
            base = None

    body, meta = build_report(a.input, base)
    if body is None:
        print(meta if isinstance(meta, str) else "未能生成报告")
        if a.out:
            with open(a.out, "w", encoding="utf-8") as f:
                f.write(str(meta))
        return 2

    txt = json.dumps(meta, ensure_ascii=False, indent=2) if a.json else body
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(txt)
        print("written %s" % a.out)
    else:
        print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
