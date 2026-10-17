# -*- coding: utf-8 -*-
"""驾驶证换证办理核查 v1.0.0

输入：按 templates/驾驶证换证信息采集表.md 填写的 Markdown
输出：九段式核查报告（或 --json 摘要）

判定纪律：
- 依《机动车驾驶证申领和使用规定》等通用规则做档位与材料核对，
  最终以当地公安交管部门与交管 12123 显示为准
- 不代办、不承诺办结时限、不替代公安交管部门认定
- 用户填什么就用什么，未填的一律标「未填」，不算通过
"""
import argparse
import datetime as dt
import json
import sys

VERSION = "1.0.0"

PLACEHOLDER = (
    "【待填",
    "填什么",
    "是/否",
    "有/无",
    "不清楚",
    "YYYY-MM-DD",
    "___",
)

AB_TYPES = ("A1", "A2", "A3", "B1", "B2")


# ---------------------------------------------------------------- 基础工具
def norm(s):
    if s is None:
        return ""
    t = str(s)
    t = t.replace("\u3000", " ")
    t = t.replace(" ", "")
    t = t.replace("\uff08", "(").replace("\uff09", ")")
    t = t.replace("|", " ")
    return t.strip()


def clean(s):
    if s is None:
        return ""
    return str(s).strip().strip("|").strip()


def is_ph(v):
    """提示语视为未填，不能判成"已具备"。"""
    t = norm(v)
    if not t:
        return True
    for w in PLACEHOLDER:
        if norm(w) and norm(w) in t:
            return True
    if t in ("-", "--", "/", "\u2014", "—"):
        return True
    if t and set(t) <= set("-—:=/"):
        return True
    return False


def split_row(ln):
    s = ln.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def load_rows(text):
    """支持 | 字段 | 值 | 表格行 与 字段：值 冒号行两种写法。"""
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("|"):
            c = split_row(s)
            if len(c) >= 2:
                rows.append((c[0], c[1]))
            continue
        for sep in ("\uff1a", ":"):
            if sep in s:
                k, v = s.split(sep, 1)
                k = k.strip().lstrip("-*#>").strip()
                if 0 < len(k) <= 40:
                    rows.append((k, v.strip()))
                break
    return rows


def get_text(text, *labels):
    """最长别名优先 + 别名主序：先拿长别名扫全表，再拿短别名。"""
    rows = load_rows(text)
    for lb in sorted(labels, key=lambda x: -len(norm(x))):
        nlb = norm(lb)
        if not nlb:
            continue
        for k, v in rows:
            if nlb in norm(k) and not is_ph(v):
                return clean(v)
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
    """先判开头字（避免「有 X 未缴款」被"未"抢判成否），再退化为子串。"""
    v = get_text(text, *labels)
    if not v:
        return None
    t = norm(v)
    h = t[0] if t else ""
    if h in ("是", "有", "已"):
        return True
    if h in ("否", "无", "没", "未"):
        return False
    if "否" in t or "没有" in t or "无此" in t or "无需" in t:
        return False
    if "是" in t or "有" in t or "已" in t:
        return True
    return None


def fmt_num(v):
    """数值输出去掉 .0"""
    if v is None:
        return "未填"
    if isinstance(v, float) and abs(v - int(v)) < 1e-9:
        return str(int(v))
    if isinstance(v, float):
        return ("%.2f" % v).rstrip("0").rstrip(".")
    return str(v)


def money(v):
    return "¥%s" % fmt_num(v)


def parse_date(v):
    if not v:
        return None
    t = norm(v)
    for sep in ("-", "/", ".", "年", "月"):
        t = t.replace(sep, "-")
    t = t.replace("日", "")
    parts = [p for p in t.split("-") if p]
    if len(parts) < 3:
        return None
    try:
        return dt.date(int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:
        return None


def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:  # 2 月 29 日
        return d.replace(year=d.year + n, day=28)


# ---------------------------------------------------------------- 档位判定
def judge_overdue(expiry, base):
    """按「应换证日期 + 今天」判逾期档位。

    返回 (档号, 档名, 逾期天数, 满1年日, 满3年日)
    档号：1 正常 / 2 逾期不满1年 / 3 逾期1年以上不满3年 / 4 逾期3年以上
    """
    if expiry is None or base is None:
        return (0, "未填", None, None, None)
    d1 = add_years(expiry, 1)
    d3 = add_years(expiry, 3)
    days = (base - expiry).days
    if days < 0:
        return (1, "正常（仍在有效期内）", days, d1, d3)
    if base < d1:
        return (2, "逾期不满 1 年", days, d1, d3)
    if base < d3:
        return (3, "逾期 1 年以上不满 3 年", days, d1, d3)
    return (4, "逾期 3 年以上", days, d1, d3)


def judge_next_validity(cur_level, all_clean, overdue_level):
    """推算下次能换到几年。返回 (结论串, 依据串)。"""
    if overdue_level in (3, 4):
        return ("先恢复驾驶资格，暂不适用升档",
                "当前处于逾期第 %d 档，须先按规定恢复资格再谈升档" % overdue_level)
    if not cur_level:
        return ("待补正", "「当前有效期档位」未填，无法推算")
    if cur_level == "长期":
        return ("长期有效，无需期满换证",
                "长期有效的机动车驾驶证不再因有效期满换证（70 周岁以上仍须按年提交身体条件证明）")
    if all_clean is None:
        return ("待补正", "「本证期间是否每个记分周期均未记满 12 分」未填，无法判断是否满足升档条件")
    if cur_level == "6年":
        if all_clean:
            return ("10 年",
                    "6 年有效期内每个记分周期均未记满 12 分 → 换发 10 年有效期")
        return ("6 年（不能升档）",
                "6 年有效期内存在记满 12 分的记分周期 → 不满足升档条件，换发 6 年有效期")
    if cur_level == "10年":
        if all_clean:
            return ("长期有效",
                    "10 年有效期内每个记分周期均未记满 12 分 → 换发长期有效的机动车驾驶证")
        return ("10 年（不能升档）",
                "10 年有效期内存在记满 12 分的记分周期 → 不满足升档条件，换发 10 年有效期")
    return ("待补正", "当前有效期档位填写为「%s」，暂无法识别" % cur_level)


def pick_level(text):
    v = get_text(text, "当前有效期档位")
    if not v:
        return ""
    t = norm(v)
    if "长期" in t:
        return "长期"
    if "10" in t or "十" in t:
        return "10年"
    if "6" in t or "六" in t:
        return "6年"
    return ""


def infer_level(start, expiry):
    """未填档位时按起止日期推断（仅作参考，标注为推断）。"""
    if not start or not expiry:
        return ""
    days = (expiry - start).days
    if days <= 0:
        return ""
    if days <= 2500:      # 约 6 年 ~ 6.8 年
        return "6年"
    if days <= 4200:      # 约 10 年 ~ 11.5 年
        return "10年"
    return "长期"


def pick_type(text):
    """准驾车型"""
    v = get_text(text, "当前准驾车型", "准驾车型")
    return clean(v)


def is_ab(q_type, text):
    t = norm(q_type)
    has = False
    for a in AB_TYPES:
        if a.lower() in t.lower():
            has = True
            break
    flag = yes(text, "是否持有A/B类准驾车型", "是否持有A/B类")
    if has:
        return True, "准驾车型含 A/B 类（%s）" % q_type
    if flag is True:
        return True, "已勾选持有 A/B 类准驾车型"
    if flag is False:
        return False, "未持有 A/B 类准驾车型"
    return False, "准驾车型未填 or 不含 A/B 类"


INFO_ITEMS = ("已可办理", "未发现明显风险")


def real_risks(risks):
    """只算真风险，提示性条目（已可办理 / 未发现明显风险）不影响结论。"""
    return [r for r in risks if r[0] not in INFO_ITEMS]


def fmt_flag(v):
    if v is True:
        return "是"
    if v is False:
        return "**否**"
    return "未填"


def fmt_have(v):
    """材料是否具备：有→已备，无→**缺失**，其他→未填"""
    t = norm(v)
    if not t:
        return "未填"
    if "丢失" in t or "遗失" in t:
        return "**已丢失**"
    if "免提交" in t or "免于提交" in t:
        return "当地免提交"
    if "无" in t or "缺" in t or "未" in t:
        return "**缺失**"
    if "有" in t or "已" in t:
        return "已备"
    return "未填"


# ---------------------------------------------------------------- 报告
def build_report(path, base=None):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        return None, "读不了文件：%s" % e

    if base is None:
        base = dt.date.today()

    name = get_text(text, "驾驶人姓名", "姓名")
    age = get_int(text, "年龄")
    city = get_text(text, "常住城市")
    q_type = pick_type(text)
    first_date = parse_date(get_text(text, "初次领证日期"))
    start = parse_date(get_text(text, "本证有效期起始日", "有效期起始日"))
    expiry = parse_date(get_text(text, "本证有效期截止日", "本证有效期截止日", "有效期止"))
    state = get_text(text, "驾驶证当前状态")
    level = pick_level(text)
    level_inferred = False
    if not level:
        level = infer_level(start, expiry)
        level_inferred = True

    all_clean = yes(text, "本证期间是否每个记分周期均未记满12分",
                    "是否每个记分周期均未记满12分")
    full12 = yes(text, "有无记满12分的记分周期")
    cur_points = get_int(text, "当前记分周期内已记分数")
    unhandled = yes(text, "是否有未处理的道路交通安全违法行为")
    accident = yes(text, "是否有未结案的交通事故")

    remote = yes(text, "是否异地办理")
    residence = get_text(text, "是否有当地居住证明")
    online = yes(text, "是否希望线上办理")
    transfer = yes(text, "是否需同时办理转入换证")
    app12123 = yes(text, "是否已安装并登录交管12123")

    medical = get_text(text, "是否已取得《机动车驾驶人身体条件证明》",
                       "是否已取得身体条件证明")
    med_org = get_text(text, "体检机构类型")
    med_date = parse_date(get_text(text, "体检证明出具日期"))
    disease = yes(text, "是否存在影响安全驾驶的疾病")

    idcard = get_text(text, "身份证明（身份证原件）是否具备", "身份证明")
    lic_orig = get_text(text, "机动车驾驶证原件是否具备")
    photo = get_text(text, "照片是否具备")
    fee_known = yes(text, "是否已了解工本费")

    age70 = yes(text, "是否年满70周岁")
    age70_proof = yes(text, "年满70周岁的是否已按年提交身体条件证明",
                      "是否已按年提交身体条件证明")
    ab_flag, ab_why = is_ab(q_type, text)
    ab_points = yes(text, "A/B类本周期是否有记分")
    ab_review = get_text(text, "A/B类是否已在周期结束后30日内审验")
    seized = yes(text, "驾驶证是否被扣押/扣留/暂扣")
    biz = get_text(text, "是否属于补证/变更换证/降级换证")
    note = get_text(text, "补充说明")

    if expiry is None and not any([q_type, state, level, first_date]):
        return None, ("未解析到关键信息。至少填写「本证有效期截止日」或「准驾车型」"
                      "中的一项，否则无法判定档位。")

    olevel, oname, odays, d1, d3 = judge_overdue(expiry, base)
    if olevel == 0:
        return None, ("缺少「本证有效期截止日」，无法判定逾期档位。"
                      "请填写 YYYY-MM-DD 格式的日期后重跑。")

    next_v, next_why = judge_next_validity(level, all_clean, olevel)

    # ---------------- 风险项
    risks = []
    blocks = []   # 硬阻断 → 不通过

    if olevel == 1 and odays is not None and odays > -91:
        risks.append(("已可办理", "距有效期满不足 90 日，处于可申请期满换证的窗口内",
                      "尽快办，别拖到逾期"))
    if olevel == 1 and odays is not None and odays <= -91:
        risks.append(("尚未到办理窗口",
                      "只能在有效期满前 90 日内申请换证，现在还早",
                      "到期前 90 日内再办；先记下日期设提醒"))
    if olevel == 2:
        risks.append(("驾驶证已逾期（不满 1 年）",
                      "可正常换证，但**逾期期间不得驾驶机动车**",
                      "先把车停下，尽快申请期满换证"))
    if olevel == 3:
        risks.append(("逾期 1 年以上不满 3 年",
                      "驾驶证已被注销但未完全失效，须重考**科目一**合格后恢复",
                      "先在 12123 查状态 → 预约科目一 → 合格后办理恢复驾驶资格"))
    if olevel == 4:
        blocks.append(("逾期 3 年以上",
                       "驾驶证已被注销，须**重新报考全部科目**",
                       "重新报名，从科目一开始考全部科目"))
    if seized:
        blocks.append(("驾驶证处于扣押/扣留/暂扣期间",
                       "不予换证",
                       "先处理完毕扣押扣留事由，再申请换证"))
    if unhandled:
        risks.append(("有未处理的道路交通安全违法行为",
                      "违法未处理完毕的，不予换证",
                      "先在 12123 缴清罚款、处理完违法，再申请换证"))
    if accident:
        risks.append(("有未结案的交通事故",
                      "事故未处理完毕的，不予换证",
                      "先配合处理完事故结案，再申请换证"))
    if disease:
        risks.append(("存在影响安全驾驶的疾病",
                      "身体条件不符合驾驶许可条件的，不予换证",
                      "先做体检并由医疗机构出具身体条件证明，按结论处理"))
    if norm(lic_orig) and ("丢失" in norm(lic_orig) or "遗失" in norm(lic_orig)):
        risks.append(("驾驶证已丢失",
                      "丢失应办**补证**，不是期满换证",
                      "走补领机动车驾驶证流程（可线上办理）"))
    if biz and ("补证" in norm(biz) or "变更" in norm(biz) or "降级" in norm(biz)):
        risks.append(("本次业务不是期满换证",
                      "填报的业务类型为「%s」，与前几段的期满换证口径不同" % clean(biz),
                      "按对应业务准备材料；如主要是有效期满，仍须同时办期满换证"))
    if remote and norm(residence) and ("无" in norm(residence)):
        risks.append(("异地办理但无居住证明",
                      "异地申请换证通常需居住证或当地认可的暂住登记凭证",
                      "先办居住证明，或回核发地办理"))
    if fmt_have(photo) == "**缺失**":
        risks.append(("照片缺失",
                      "当地未实行联网采集合格照片的，仍需提交符合规格的照片",
                      "先到车管所自助机采集或按 12123 提示上传电子版"))
    if fmt_have(medical) != "已备":
        risks.append(("未取得《机动车驾驶人身体条件证明》",
                      "期满换证需提交县级或者部队团级以上医疗机构出具的证明",
                      "去自助体检机或有资质的医疗机构体检；体检证明有有效期，别提前太久"))
    if age70:
        if age70_proof is False:
            risks.append(("年满 70 周岁未按年提交身体条件证明",
                          "70 周岁以上驾驶人应当每年提交一次身体条件证明",
                          "立即补做体检并提交；设成每年一次的日历提醒"))
        risks.append(("年满 70 周岁准驾车型受限",
                      "不得驾驶普通三轮/二轮摩托车等；原持 D、E 的应降级为 F",
                      "确认准驾车型，如需降级同步办理降级换证"))
    if ab_flag:
        if ab_points:
            risks.append(("A/B 类本周期有记分",
                          "应在记分周期结束后 30 日内接受审验",
                          "尽快补办审验；连续三个周期不审验将注销最高准驾车型"))
            if norm(ab_review) and ("否" in norm(ab_review)):
                risks.append(("A/B 类审验未完成",
                              "连续三个记分周期不参加审验的，注销最高准驾车型驾驶资格",
                              "立即到车管所或 12123 办理审验，别再拖"))
        else:
            risks.append(("A/B 类准驾车型",
                          "本周期无记分可免予审验；有记分的须在周期结束后 30 日内审验",
                          "每个记分周期结束后核一次有无记分"))
    if cur_points is not None and cur_points >= 9:
        risks.append(("当前记分周期已记 %s 分" % fmt_num(cur_points),
                      "接近 12 分，再记分将影响本次及后续升档",
                      "谨慎驾驶；已满 12 分须先按规定学习考试清除记分再换证"))
    if full12:
        risks.append(("存在记满 12 分的记分周期",
                      "存在记满 12 分周期的，本次换证不能升档",
                      "接受当前推算结果；下一个有效期周期内保持零满分记录"))
    if not risks and not blocks:
        risks.append(("未发现明显风险", "未填的不算通过", "—"))

    # ---------------- 结论四态
    mat_ready = (fmt_have(idcard) == "已备" and fmt_have(lic_orig) == "已备"
                 and fmt_have(medical) == "已备")
    if blocks:
        verdict = "不通过"
    elif olevel in (3, 4):
        verdict = "不通过"
    elif olevel == 2:
        verdict = "有风险"
    elif not (idcard and lic_orig and medical):
        verdict = "待补正"
    elif not mat_ready:
        verdict = "待补正"
    elif real_risks(risks):
        verdict = "有风险"
    else:
        verdict = "通过"

    L = []
    A = L.append

    A("# 驾驶证换证办理核查报告")
    A("")
    A("> 生成日期：%s；脚本版本 v%s；驾驶人：%s" % (base.isoformat(), VERSION, name or "未填"))
    A("")

    # 一、结论摘要
    A("## 一、结论摘要")
    A("")
    A("| 项 | 结论 |")
    A("|---|---|")
    A("| 综合结论 | **%s** |" % verdict)
    A("| 现在处于哪一档 | **%s** |" % oname)
    A("| 下次能换几年 | **%s** |" % next_v)
    A("| 当前有效期档位 | %s%s |" % (level or "未填", "（按起止日期推断）" if level_inferred and level else ""))
    A("| 准驾车型 | %s |" % (q_type or "未填"))
    A("| 风险项 | %d 项 |" % len(real_risks(risks)))
    A("| 阻断项 | %d 项 |" % len(blocks))
    A("")
    if olevel >= 2:
        A("⚠️ **现在不要再开车**。驾驶证超过有效期后不得驾驶机动车，"
          "逾期驾车属无证驾驶性质，除处罚外，一旦发生交通事故责任与理赔都会往不利方向走。")
        A("")
    if blocks:
        A("🚫 存在阻断项：%s —— 先解决这些，再谈换证。" % "、".join(b[0] for b in blocks))
        A("")
    A("**未填的一律不算通过**，只按你填了的判断——补填后重跑一次。")
    A("")

    # 二、有效期档位
    A("## 二、有效期档位判定")
    A("")
    A("| 项 | 情况 |")
    A("|---|---|")
    A("| 初次领证日期 | %s |" % (first_date.isoformat() if first_date else "未填"))
    A("| 本证有效期 | %s ~ %s |" % (start.isoformat() if start else "未填",
                                    expiry.isoformat() if expiry else "未填"))
    A("| 当前有效期档位 | %s%s |" % (level or "未填", "（推断）" if level_inferred and level else ""))
    A("| 驾驶证当前状态 | %s |" % (state or "未填"))
    A("| 本证期间每个周期均未记满12分 | %s |" % fmt_flag(all_clean))
    A("| 有无记满12分的周期 | %s |" % fmt_flag(full12))
    A("| 当前周期已记分 | %s 分 |" % fmt_num(cur_points))
    A("")
    A("档位规则：初次取得 **6 年**；6 年有效期内每个记分周期均未记满 12 分的换发 **10 年**；"
      "10 年有效期内每个记分周期均未记满 12 分的换发**长期有效**。"
      "只要有一个周期被记满 12 分，本次就升不了档。")
    A("")
    A("记分周期从**初次领证之日**起算，每 12 个月一个周期，不是自然年。")
    A("")

    # 三、逾期档位
    A("## 三、逾期档位判定（现在处于哪一档）")
    A("")
    A("| 项 | 情况 |")
    A("|---|---|")
    A("| 应换证日期（有效期止） | %s |" % (expiry.isoformat() if expiry else "未填"))
    A("| 今天 | %s |" % base.isoformat())
    if odays is not None and odays >= 0:
        A("| 已逾期 | %s 天 |" % fmt_num(odays))
    elif odays is not None:
        A("| 距有效期满 | 还剩 %s 天 |" % fmt_num(-odays))
    A("| **当前档位** | **%s** |" % oname)
    A("| 满 1 年的日子 | %s |" % (d1.isoformat() if d1 else "—"))
    A("| 满 3 年的日子 | %s |" % (d3.isoformat() if d3 else "—"))
    if expiry:
        A("| 最早可办理日（提前90日） | %s |" % (expiry - dt.timedelta(days=90)).isoformat())
    A("")
    A("| 档位 | 逾期时长 | 状态 | 怎么办 |")
    A("|---|---|---|---|")
    A("| ① 正常 | 未逾期 | 有效 | 直接申请期满换证%s |" % (" ← 你在这" if olevel == 1 else ""))
    A("| ② 逾期不满 1 年 | < 1 年 | 逾期未换证 | 可正常换证%s |" % (" ← 你在这" if olevel == 2 else ""))
    A("| ③ 逾期 1 年以上不满 3 年 | ≥1 年 且 <3 年 | 注销但未完全失效 | 重考**科目一**合格后恢复%s |" % (" ← 你在这" if olevel == 3 else ""))
    A("| ④ 逾期 3 年以上 | ≥ 3 年 | 注销 | **重新报考全部科目**%s |" % (" ← 你在这" if olevel == 4 else ""))
    A("")
    A("### 逾期驾车风险")
    A("")
    if olevel >= 2:
        A("- **逾期期间一律不得驾驶机动车**。这不是「小心点开」的问题。")
        A("- 性质：驾驶证逾期后驾车，属**无证驾驶性质**的处理范畴，面临罚款、可并处拘留"
          "（具体幅度按当地执法口径）。")
        A("- 事故：逾期期间发生交通事故，责任认定与后续理赔均处于明显不利地位，"
          "保险公司常以此主张商业险拒赔。")
        A("- 正确做法：**先把车停下**，办完换证再上路；确需出行改用其他交通方式。")
    else:
        A("- 当前仍在有效期内，不存在逾期驾车风险。办完换证前，请确认新证到手再驾车。")
    A("")

    # 四、下次能换几年
    A("## 四、下次能换几年（升档推算）")
    A("")
    A("| 项 | 结论 |")
    A("|---|---|")
    A("| 当前档位 | %s |" % (level or "未填"))
    A("| 每个周期均未记满12分 | %s |" % fmt_flag(all_clean))
    A("| **换发后有效期** | **%s** |" % next_v)
    A("| 推算依据 | %s |" % next_why)
    A("")
    if next_v == "6 年（不能升档）" or next_v == "10 年（不能升档）":
        A("卡在哪：本证期间有记分周期被记满 12 分，升档条件不满足。"
          "下一个有效期内保持每个记分周期都零满分记录，下次换证才能往上走。")
        A("")
    A("提示：升档看的是**每个**记分周期，一个周期满 12 分就升不上去。"
      "长期有效的驾驶证不再因期满换证，但 70 周岁以上仍须按年提交身体条件证明。")
    A("")

    # 五、材料清单
    A("## 五、材料清单")
    A("")
    A("| # | 材料 | 状态 | 要求 |")
    A("|---|---|---|---|")
    A("| 1 | 身份证明（居民身份证原件） | %s | 异地办理另需居住证明 |" % fmt_have(idcard))
    A("| 2 | 机动车驾驶证原件 | %s | 丢失应办补证，不是换证 |" % fmt_have(lic_orig))
    A("| 3 | 《机动车驾驶人身体条件证明》 | %s | 县级或者部队团级以上医疗机构出具，"
      "或经认可的体检机构/自助体检机 |" % fmt_have(medical))
    A("| 4 | 照片 | %s | 部分地区联网采集合格照片可免提交，以当地为准 |" % fmt_have(photo))
    A("| 5 | 工本费 | %s | 一般 %s，以当地为准；体检费另付 |" % (
        "已知" if fee_known else "未确认", money(10)))
    A("")
    A("| 补充项 | 情况 |")
    A("|---|---|")
    A("| 体检机构类型 | %s |" % (med_org or "未填"))
    A("| 体检证明出具日期 | %s |" % (med_date.isoformat() if med_date else "未填"))
    A("| 居住证明（异地办理） | %s |" % (residence or "未填"))
    A("")
    A("体检证明有**有效期**（自出具之日起算，各地口径不同，常见为 6 个月内），"
      "过期要重新体检——别提前太久做。")
    A("")

    # 六、办理路径
    A("## 六、办理路径（线上 12123 / 车管所 / 异地）")
    A("")
    A("| 项 | 情况 |")
    A("|---|---|")
    A("| 是否异地办理 | %s |" % fmt_flag(remote))
    A("| 是否希望线上办理 | %s |" % fmt_flag(online))
    A("| 是否已登录交管12123 | %s |" % fmt_flag(app12123))
    A("| 是否需同时办理转入换证 | %s |" % fmt_flag(transfer))
    A("")
    if olevel == 4:
        A("**当前路径**：驾驶证已注销满 3 年以上 → **重新报名，从科目一开始考全部科目**，"
          "不适用线上换证流程。")
    elif olevel == 3:
        A("**当前路径**：12123 查状态 → 预约**科目一** → 合格后办理恢复驾驶资格 → 再办期满换证。")
    else:
        if online is False:
            A("**推荐路径 B：车管所 / 交警服务大厅窗口办**——带齐材料取号，"
              "提交体检证明与照片，缴费后当场或当日领证。")
        elif app12123 is False and online is True:
            A("**推荐路径 A，但先补一步**：先安装并登录**交管 12123** 完成实名认证与驾驶证绑定，"
              "再走线上期满换证。")
        else:
            A("**推荐路径 A：交管 12123 线上办**——首页 → 更多 → 驾驶证业务 → 期满换证，"
              "按提示提交体检信息、上传照片，选邮寄到家，在线缴费。")
    A("")
    A("| 路径 | 适用 | 步骤要点 |")
    A("|---|---|---|")
    A("| A 交管12123线上 | 状态正常、逾期不满1年 | 登录12123 → 期满换证 → 提交体检 → 上传照片 → 邮寄到家 |")
    A("| B 车管所窗口 | 线上办不了、需现场核验 | 带齐材料 → 取号 → 提交 → 缴费 → 领证 |")
    A("| C 异地通办 | 长期在非核发地居住 | 在居住地/暂住地直接申请，无需回核发地；需居住证明 |")
    A("")
    if remote:
        A("**异地通办**：期满换证**已全国通办**，可在居住地、暂住地直接申请，"
          "不用回核发地。长期在当地居住的，建议「转入换证 + 期满换证」一次办完，"
          "此后审验、换证都在当地办。")
        A("")
    A("查询入口：**交管 12123 APP**、当地公安交管微信公众号、车管所咨询电话。")
    A("")

    # 七、特殊分支与阻断项
    A("## 七、特殊分支与阻断项")
    A("")
    A("| 分支 | 是否命中 | 结论 |")
    A("|---|---|---|")
    A("| 年满 70 周岁 | %s | %s |" % (
        fmt_flag(age70),
        "每年须提交身体条件证明；D、E 应降级为 F，不得驾驶普通三轮/二轮摩托车等"
        if age70 else "不适用"))
    A("| 年满70周岁按年提交证明 | %s | %s |" % (
        (fmt_flag(age70_proof) if age70 else "不适用"),
        ("已按年提交" if age70_proof else "未提交或未填，须补做") if age70 else "未满 70 周岁，本项不适用"))
    A("| A/B 类准驾车型 | %s | %s |" % ("是" if ab_flag else "否", ab_why))
    A("| A/B 类本周期有记分 | %s | %s |" % (
        fmt_flag(ab_points),
        "须在记分周期结束后 30 日内审验" if ab_points else "无记分可免予本周期审验"))
    A("| A/B 类审验情况 | %s | 连续三个周期不审验将注销最高准驾车型 |" % (ab_review or "未填"))
    A("| 扣押/扣留/暂扣 | %s | %s |" % (
        fmt_flag(seized), "不予换证，先处理完毕" if seized else "无，可继续办理"))
    A("| 本次业务类型 | %s | %s |" % (
        biz or "未填",
        "期满换证" if (biz and "都不是" in norm(biz)) else "需按对应业务准备材料"))
    A("")
    A("**不予换证的情形**（命中任一条都会被挡下）：未处理完毕的道路交通安全违法行为、"
      "未处理完毕的交通事故、驾驶证被扣押/扣留/暂扣期间、被吊销或撤销期间、"
      "身体条件不符合驾驶许可条件。")
    A("")
    A("**别办错了**：有效期满→期满换证；丢失/损毁→**补证**；姓名住址等信息变更→**变更换证**；"
      "自愿降低准驾车型→**降级换证**；迁到现居住地→**转入换证**。")
    A("")
    if note:
        A("补充说明：%s" % note)
        A("")

    # 八、待办
    A("## 八、待办补正动作")
    A("")
    todo = []
    for b in blocks:
        todo.append("先解决阻断项「%s」：%s" % (b[0], b[2]))
    for r in risks:
        if r[0] != "未发现明显风险":
            todo.append("处理风险「%s」：%s" % (r[0], r[2]))
    if not idcard:
        todo.append("备齐身份证明：居民身份证原件（过期先补办身份证）")
    if not lic_orig:
        todo.append("确认机动车驾驶证原件在手；已丢失的改走补领流程")
    if fmt_have(medical) != "已备":
        todo.append("做驾驶人体检：县级或者部队团级以上医疗机构，或车管所自助体检机，"
                    "取得《机动车驾驶人身体条件证明》")
    if fmt_have(photo) == "**缺失**":
        todo.append("准备照片：先确认当地是否免提交，不免则备一寸白底彩照或按12123提示上传电子版")
    if remote and norm(residence) and ("无" in norm(residence)):
        todo.append("异地办理：先办居住证明（居住证或当地认可的暂住登记凭证）")
    if online and app12123 is False:
        todo.append("安装并登录交管 12123，完成实名认证并绑定本人驾驶证")
    if olevel == 1 and odays is not None and odays <= -91:
        todo.append("设提醒：%s（有效期满前90日的首日）之后再申请换证"
                    % (expiry - dt.timedelta(days=90)).isoformat())
    if olevel == 3:
        todo.append("12123 查驾驶证状态 → 预约科目一 → 合格后办理恢复驾驶资格")
    if olevel == 4:
        todo.append("重新报名：从科目一开始考全部科目")
    if age70 and age70_proof is not True:
        todo.append("70 周岁以上：补做并每年提交一次身体条件证明，设成年度日历提醒")
    if ab_flag and ab_points:
        todo.append("A/B 类：记分周期结束后 30 日内接受审验（12123 或车管所）")
    if unhandled:
        todo.append("处理未处理的道路交通安全违法行为（缴清罚款）后再申请")
    if accident:
        todo.append("配合处理未结案的交通事故，结案后再申请")
    todo.append("打开交管 12123 核对记分、违法与驾驶证状态，与本报告对照")
    todo.append("办完后确认新证有效期与准驾车型，旧证按提示处理")
    for i, t in enumerate(todo, 1):
        A("%d. %s" % (i, t))
    A("")

    # 九、纪律
    A("## 九、边界与纪律")
    A("")
    A("- 依《中华人民共和国道路交通安全法》《机动车驾驶证申领和使用规定》等**通用规则**整理，"
      "**最终以当地公安交管部门与交管 12123 显示为准**；")
    A("- **不代办、不承诺**办结时限，不预测能否免体检、免照片（各地差异大）；")
    A("- 自助体检机布点、可上传体检结果的机构名单、是否支持邮寄、异地居住证明形式等，"
      "各地执行口径不同，请以当地为准；")
    A("- 军警驾驶证换领、境外驾驶证换领、校车驾驶资格等另有规定，需另行查证；")
    A("- 本结果依通用规则整理，不替代专业意见，最终以主管部门认定为准。")
    A("")

    body = "\n".join(L)
    meta = {
        "version": VERSION,
        "姓名": name or "",
        "准驾车型": q_type or "",
        "当前有效期档位": level or "",
        "逾期档位": olevel,
        "逾期档位名称": oname,
        "逾期天数": odays,
        "下次能换几年": next_v,
        "结论": verdict,
        "风险项": [{"项": r[0], "后果": r[1], "怎么办": r[2]}
                   for r in risks if r[0] != "未发现明显风险"],
        "阻断项": [{"项": b[0], "后果": b[1], "怎么办": b[2]} for b in blocks],
        "待办": todo,
    }
    return body, meta


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
