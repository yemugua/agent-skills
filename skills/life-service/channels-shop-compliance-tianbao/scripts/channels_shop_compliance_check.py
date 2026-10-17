# -*- coding: utf-8 -*-
"""视频号小店带货合规核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：多段报告，含结论摘要、店铺与保证金核查、类目准入与资质核查、商品信息合规核查、
      售后与物流核查、直播话术与场外交易核查、违规与品质记录核查、整改指引、边界。

只做核查与指引，不替代微信视频号小店官方规则与审核结论。
退出码：0 正常；2 关键信息缺失（打印提示，不崩）。
"""
import argparse
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

FIELD_ALIAS = {
    "账号主体类型": ["账号主体类型", "主体类型", "小店主体", "账号主体"],
    "是否开通视频号小店": ["是否开通视频号小店", "小店开通", "是否开通小店", "是否开店",
                        "是否开通橱窗"],
    "是否缴纳足额保证金": ["是否缴纳足额保证金", "保证金", "是否缴保证金", "保证金缴纳"],
    "带货类目": ["带货类目", "带货品类", "经营类目", "销售类目", "商品类目", "类目"],
    "类目资质是否已报备": ["类目资质是否已报备", "类目资质", "资质报备", "是否报白",
                        "定向准入资质", "资质是否上传"],
    "是否持有对应经营资质": ["是否持有对应经营资质", "经营资质", "许可证", "是否持牌",
                          "营业执照之外资质"],
    "商品标题主图是否夸大或虚假": ["商品标题主图是否夸大或虚假", "虚假宣传", "夸大宣传",
                            "标题党商品", "绝对化用语", "商品文案违规"],
    "是否存在价格违规": ["是否存在价格违规", "价格违规", "虚构原价", "虚假折扣", "先涨后降"],
    "是否执行7天无理由退货": ["是否执行7天无理由退货", "7天无理由", "七天无理由", "无理由退货"],
    "发货时效是否达标": ["发货时效是否达标", "发货时效", "是否按时发货", "发货超时"],
    "客服响应是否及时": ["客服响应是否及时", "客服响应", "售后客服", "客服处理"],
    "是否直播带货": ["是否直播带货", "是否直播", "直播带货"],
    "直播话术是否违规": ["直播话术是否违规", "话术违规", "直播违规", "虚假话术", "演戏炒作"],
    "是否引导站外或私下交易": ["是否引导站外或私下交易", "站外交易", "私下交易", "加微信下单",
                          "场外交易", "引导转账"],
    "是否销售禁售商品": ["是否销售禁售商品", "禁售商品", "是否卖禁售", "违禁品"],
    "是否收到过违规扣分或处罚": ["是否收到过违规扣分或处罚", "违规扣分", "扣分", "处罚记录",
                          "是否被罚", "违规处罚"],
    "品质退款率或投诉率是否偏高": ["品质退款率或投诉率是否偏高", "品质退款", "投诉率", "退货率",
                            "质量投诉"],
    "商品是否经过质检或资质备案": ["商品是否经过质检或资质备案", "质检报告", "商品质检", "备案",
                          "检测报告"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)

# 带货类目 → 准入资质要求（视频号小店定向准入/普通类目公开规则口径）
CATEGORY_QUAL = {
    "食品": "预包装/散装食品带货须食品经营许可证或预包装食品备案，保健食品须对应注册/备案凭证",
    "保健": "保健食品须食品经营资质 + 保健食品注册或备案凭证，不得宣称疾病预防治疗功效",
    "医疗": "医疗器械须经营备案（二类）或经营许可（三类），须有医疗器械广告审查，个人不得带货",
    "药品": "处方药/药品禁止带货推广，非处方药也须严格资质，个人不得带货",
    "美妆": "化妆品须产品注册/备案（普通或特殊化妆品），特殊化妆品须注册证，功效宣称需有依据",
    "图书": "图书须出版物经营许可证，进口出版物须相关批准",
    "教育": "课程类须办学许可或对应备案，不得承诺升学/提分/就业效果",
    "母婴": "婴幼儿配方食品须配方注册，儿童用品注意 3C 等强制认证",
    "珠宝": "珠宝玉石文玩部分为定向准入，须提供质检或来源证明，警惕假货与二次溢价炒作",
    "游戏": "游戏充值/道具为虚拟商品，注意平台虚拟商品规则与未成年人保护",
    "数码": "3C 数码须 3C 认证，二手数码注意来源与翻新标注",
    "农产品": "食用农产品须产地/合格证等追溯信息，不得虚假宣传有机/绿色（须对应认证）",
    "宠物": "宠物食品须饲料生产或经营资质，宠物药品须兽药经营许可",
}

# 禁售商品关键词
BANNED_WORDS = ("假货", "仿品", "处方药", "野生动物", "象牙", "公民信息", "走私",
                "代购", "作弊器材", "管制刀具", "枪支弹药", "迷药", "赌博", "洗钱")

# 绝对化/夸大宣传用语
EXAGGERATE_WORDS = ("最好", "第一", "最强", "国家级", "顶级", "绝对", "100%", "包治",
                    "根治", "特效", "秒杀全网", "永久", "无副作用", "零风险", "稳赚")

NEG_WORDS = ("否", "没有", "未", "不", "无", "否认", "拒绝", "不知情", "没做", "无法", "没")
POS_WORDS = ("是", "已", "有", "承认", "确认", "同意", "认可", "已做", "可以", "做过", "完成")


def norm(s):
    if s is None:
        return ""
    out = str(s).strip()
    out = out.replace("：", ":").replace("　", " ")
    out = out.replace("（", "(").replace("）", ")")
    out = re.sub(r"\s+", "", out)
    return out.lower()


def filled(v):
    if v is None:
        return False
    return norm(v) not in {norm(t) for t in EMPTY_TOKENS}


def unknown(v):
    return not filled(v)


def parse_md(path):
    data = {}
    if not path or not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            line = line.lstrip(">").strip()
        if not line:
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 2:
                continue
            key_raw = cells[0]
            if set(key_raw) <= set("-: "):
                continue
            if norm(key_raw) in ("字段", "field", "项目"):
                continue
            val = " ".join(c.strip() for c in cells[1:]).strip()
            if val:
                data[norm(key_raw)] = val
            continue
        if ":" in line or "：" in line:
            parts = re.split(r"[:：]", line, maxsplit=1)
            if len(parts) == 2:
                k = parts[0].strip().lstrip("-*# ").strip()
                v = parts[1].strip()
                if k and v:
                    data[norm(k)] = v
    return data


def get_text(f, key):
    aliases = sorted(FIELD_ALIAS.get(key, [key]), key=len, reverse=True)
    idx = {}
    for k, v in f.items():
        idx.setdefault(norm(k), v)
    for a in aliases:
        na = norm(a)
        if not na:
            continue
        if na in idx and filled(idx[na]):
            return idx[na]
    return ""


def yesno(text):
    if unknown(text):
        return None
    n = norm(text)
    for w in NEG_WORDS:
        if n.startswith(w):
            return False
    for w in POS_WORDS:
        if n.startswith(w):
            return True
    return None


def match_categories(text):
    """返回带货类目文本命中的资质类目 key 列表。"""
    if not filled(text):
        return []
    n = norm(text)
    hits = []
    for k in CATEGORY_QUAL:
        if k in n:
            hits.append(k)
    return hits


def check_shop(f):
    """店铺开通与保证金核查。"""
    items, crit, risk = [], [], []
    shop = yesno(get_text(f, "是否开通视频号小店"))
    deposit = yesno(get_text(f, "是否缴纳足额保证金"))

    if shop is False:
        crit.append("未开通视频号小店/橱窗即进行带货：带货须先完成小店入驻并通过类目审核、"
                    "缴纳保证金后方可上架商品，否则属于无证经营带货")
        items.append("- 视频号小店：未开通（阻断）")
    elif shop is True:
        items.append("- 视频号小店：已开通")
    else:
        crit.append("未确认是否开通视频号小店：带货前须完成小店入驻、类目准入与保证金缴纳，请确认")
        items.append("- 视频号小店：未确认（阻断）")

    if shop is not False:
        if deposit is False:
            crit.append("未缴纳足额保证金：视频号小店按类目要求缴纳保证金，未缴纳将无法上架商品、"
                        "无法使用带货功能，且可能被清退")
            items.append("- 保证金：未缴纳/不足额（阻断）")
        elif deposit is True:
            items.append("- 保证金：已足额缴纳")
        else:
            crit.append("未确认保证金缴纳情况：不同类目保证金标准不同，未缴足将无法上架，请确认")
            items.append("- 保证金：未确认（阻断）")
    return items, crit, risk


def check_category(f):
    """类目准入与资质核查。"""
    items, crit, risk = [], [], []
    cat_txt = get_text(f, "带货类目")
    declared = yesno(get_text(f, "类目资质是否已报备"))
    licensed = yesno(get_text(f, "是否持有对应经营资质"))

    hits = match_categories(cat_txt)
    if filled(cat_txt):
        items.append("- 带货类目：%s" % cat_txt)
    else:
        items.append("- 带货类目：未填")

    if hits:
        items.append("  - 命中定向准入/需资质类目：%s" % "、".join(hits))
        for h in hits:
            items.append("    - %s：%s" % (h, CATEGORY_QUAL[h]))
        if declared is False:
            crit.append("带货类目涉及资质准入（%s）但未报备类目资质：视频号小店对食品、保健食品、"
                        "医疗器械、化妆品、图书等类目实行定向准入，须上传对应资质通过审核后才能带货，"
                        "无资质带货将被下架商品并处罚" % "、".join(hits))
            items.append("  - 类目资质报备：未报备（阻断）")
        elif declared is True:
            items.append("  - 类目资质报备：已报备")
        else:
            crit.append("带货类目涉及资质准入（%s）但未确认类目资质是否报备：定向准入类目须"
                        "先报白/上传资质，请确认后再带货" % "、".join(hits))
            items.append("  - 类目资质报备：未确认（阻断）")
        if licensed is False:
            crit.append("未持有对应经营资质（%s）：带货商品须有合法来源与对应许可/备案，"
                        "无资质带货属违规经营" % "、".join(hits))
            items.append("  - 经营资质：未持有（阻断）")
    else:
        if declared is False:
            risk.append("未报备类目资质：即使普通类目也建议核对平台类目表，避免类目错放被处罚")
            items.append("  - 类目资质报备：未报备（风险）")
        else:
            items.append("  - 类目资质：未命中定向准入类目（普通类目，仍以平台类目表为准）")
    return items, crit, risk


def check_listing(f):
    """商品信息合规核查（标题/主图/价格）。"""
    items, crit, risk = [], [], []
    exag = yesno(get_text(f, "商品标题主图是否夸大或虚假"))
    price = yesno(get_text(f, "是否存在价格违规"))

    if exag is True:
        crit.append("商品标题/主图存在夸大或虚假宣传：绝对化用语（最好/第一/100%/根治/特效等）、"
                    "虚假功效、虚构使用效果均违反《广告法》与平台商品信息发布规范，将被下架并扣分")
        items.append("- 标题/主图文案：存在夸大或虚假（阻断）")
    elif exag is False:
        items.append("- 标题/主图文案：合规")
    else:
        risk.append("未确认商品标题/主图是否合规：建议自查绝对化用语与功效宣称依据（化妆品/食品功效宣称需有据）")
        items.append("- 标题/主图文案：未确认")

    if price is True:
        crit.append("存在价格违规（虚构原价/先涨后降/虚假折扣）：价格欺诈违反《价格法》"
                    "与明码标价规定，平台将下架商品并扣分处罚")
        items.append("- 价格合规：存在违规（阻断）")
    elif price is False:
        items.append("- 价格合规：无违规")
    else:
        items.append("- 价格合规：未确认")

    banned = yesno(get_text(f, "是否销售禁售商品"))
    if banned is True:
        crit.append("正在销售禁售商品：视频号小店禁售假货、处方药、野生动物制品、管制物品、"
                    "公民信息、走私代购等，销售禁售商品将被直接清退并可能追究法律责任")
        items.append("- 禁售商品：涉及（阻断，立即下架）")
    elif banned is False:
        items.append("- 禁售商品：不涉及")
    else:
        items.append("- 禁售商品：未确认（请对照平台禁售清单自查）")
    return items, crit, risk


def check_aftersale(f):
    """售后与物流核查。"""
    items, risk = [], []
    ret = yesno(get_text(f, "是否执行7天无理由退货"))
    deliver = yesno(get_text(f, "发货时效是否达标"))
    service = yesno(get_text(f, "客服响应是否及时"))

    if ret is False:
        risk.append("未执行 7 天无理由退货：除定制、鲜活、在线下载等法定例外商品外，"
                    "适用无理由退货的商品应支持 7 天无理由，否则将被平台处罚并影响体验分")
        items.append("- 7 天无理由退货：未执行（风险）")
    elif ret is True:
        items.append("- 7 天无理由退货：已执行")
    else:
        items.append("- 7 天无理由退货：未确认")

    if deliver is False:
        risk.append("发货时效不达标：现货应在承诺时效内发货（通常现货 48 小时内），"
                    "超时未发货将被赔付/扣分，影响店铺体验分与流量")
        items.append("- 发货时效：不达标（风险）")
    elif deliver is True:
        items.append("- 发货时效：达标")
    else:
        items.append("- 发货时效：未确认")

    if service is False:
        risk.append("客服响应不及时：售后响应慢将推高纠纷率与品质退款率，拉低店铺体验分，"
                    "影响带货口碑分与流量分发")
        items.append("- 客服响应：不及时（风险）")
    elif service is True:
        items.append("- 客服响应：及时")
    else:
        items.append("- 客服响应：未确认")
    return items, risk


def check_live(f):
    """直播话术与场外交易核查。"""
    items, crit, risk = [], [], []
    live = yesno(get_text(f, "是否直播带货"))
    script = yesno(get_text(f, "直播话术是否违规"))
    offsite = yesno(get_text(f, "是否引导站外或私下交易"))

    if live is False:
        items.append("- 直播带货：不做（直播相关项不适用）")
        return items, crit, risk

    if live is True:
        items.append("- 直播带货：是")
    else:
        items.append("- 直播带货：未确认")

    if script is True:
        crit.append("直播话术存在违规：虚假宣传、承诺收益/疗效、演戏炒作、诱导抢拍、"
                    "诋毁同行均违反平台直播规范，将被中断直播、扣分乃至取消带货权限")
        items.append("- 直播话术：违规（阻断）")
    elif script is False:
        items.append("- 直播话术：合规")
    else:
        items.append("- 直播话术：未确认")

    if offsite is True:
        crit.append("存在引导站外/私下交易行为（加微信下单、扫码转账、线下交易）："
                    "平台严禁绕开小店交易，将被下架商品、扣除保证金并限制带货功能")
        items.append("- 站外/私下交易：存在（阻断）")
    elif offsite is False:
        items.append("- 站外/私下交易：无")
    else:
        items.append("- 站外/私下交易：未确认")
    return items, crit, risk


def check_record(f):
    """违规与品质记录核查。"""
    items, risk = [], []
    punish = yesno(get_text(f, "是否收到过违规扣分或处罚"))
    quality = yesno(get_text(f, "品质退款率或投诉率是否偏高"))
    inspect = yesno(get_text(f, "商品是否经过质检或资质备案"))

    if punish is True:
        risk.append("有违规扣分/处罚记录：扣分将影响店铺体验分、流量分发与部分功能使用，"
                    "多次违规可能被清退；应先完成申诉/整改再复盘运营动作")
        items.append("- 违规与处罚记录：有（风险）")
    elif punish is False:
        items.append("- 违规与处罚记录：无")
    else:
        items.append("- 违规与处罚记录：未确认")

    if quality is True:
        risk.append("品质退款率/投诉率偏高：将拉低体验分与带货口碑分，直接影响流量；"
                    "应下架问题商品、整改供应链并加强质检与描述一致性")
        items.append("- 品质退款/投诉率：偏高（风险）")
    elif quality is False:
        items.append("- 品质退款/投诉率：正常")
    else:
        items.append("- 品质退款/投诉率：未确认")

    if inspect is True:
        items.append("- 商品质检/备案：已做")
    elif inspect is False:
        risk.append("商品未做质检或资质备案：食品、化妆品、儿童用品等应留存质检报告与资质，"
                    "应对平台抽检与监管检查")
        items.append("- 商品质检/备案：未做（风险）")
    else:
        items.append("- 商品质检/备案：未确认")
    return items, risk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="")
    args = ap.parse_args()
    f = parse_md(args.path)
    if not f or not any(filled(v) for v in f.values()):
        print("# 待补正\n\n未读取到任何有效字段，请填写采集表后再核查。")
        return 2

    crit, risk, sections = [], [], []
    subj = get_text(f, "账号主体类型")

    header = "# 视频号小店带货合规核查报告"
    if filled(subj):
        header += "（%s）" % subj
    sections.append(header)
    sections.append("")

    shop_items, shop_c, shop_r = check_shop(f)
    crit += shop_c; risk += shop_r
    cat_items, cat_c, cat_r = check_category(f)
    crit += cat_c; risk += cat_r
    lis_items, lis_c, lis_r = check_listing(f)
    crit += lis_c; risk += lis_r
    aft_items, aft_r = check_aftersale(f)
    risk += aft_r
    liv_items, liv_c, liv_r = check_live(f)
    crit += liv_c; risk += liv_r
    rec_items, rec_r = check_record(f)
    risk += rec_r

    if crit:
        verdict = "不通过"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "通过"
    summary = "## 一、结论摘要\n\n"
    summary += "- 总体结论：**%s**（阻断项 %d / 风险与待办项 %d）\n" % (verdict, len(crit), len(risk))
    if filled(subj):
        summary += "- 账号主体：%s\n" % subj
    summary += ("- 处置建议：先补齐类目准入资质与保证金，再清理商品文案与价格违规、"
                "杜绝站外交易，最后完善售后时效、质检留存与违规记录复盘。\n")
    sections.append(summary)

    body = "## 二、分项核查\n\n"
    body += "### 店铺与保证金核查\n" + "\n".join(shop_items) + "\n\n"
    body += "### 类目准入与资质核查\n" + "\n".join(cat_items) + "\n\n"
    body += "### 商品信息合规核查（标题/主图/价格/禁售）\n" + "\n".join(lis_items) + "\n\n"
    body += "### 售后与物流核查\n" + "\n".join(aft_items) + "\n\n"
    body += "### 直播话术与场外交易核查\n" + "\n".join(liv_items) + "\n\n"
    body += "### 违规与品质记录核查\n" + "\n".join(rec_items) + "\n"
    sections.append(body)

    rb = "## 三、阻断项与风险/待办\n\n"
    if crit:
        rb += "### 阻断项（必须处理，否则面临下架/扣分/清退）\n"
        for i, c in enumerate(crit, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if risk:
        rb += "### 风险/待办项（建议处理）\n"
        for i, c in enumerate(risk, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if not crit and not risk:
        rb += "各核查项均满足，建议定期对照平台最新规则自查。\n\n"
    sections.append(rb)

    adv = ("## 四、整改操作指引（带货合规清单）\n\n"
           "1. 完成小店入驻：主体认证 → 选择类目 → 缴纳足额保证金 → 类目资质报备（定向准入类目先报白）。\n"
           "2. 资质留档：营业执照、食品经营许可证、化妆品注册/备案、出版物许可等分类归档，随平台抽检备用。\n"
           "3. 商品信息：标题/主图/详情禁用绝对化用语与功效夸大，价格真实（禁虚构原价/先涨后降）。\n"
           "4. 禁售清单自查：假货、处方药、野生动物制品、管制物品、公民信息等一律不上架。\n"
           "5. 售后履约：现货承诺时效内发货（通常 48 小时），适用商品支持 7 天无理由，客服及时响应。\n"
           "6. 直播纪律：话术合规（不虚假宣传/不承诺收益疗效/不演戏炒作），严禁引导站外或私下交易。\n"
           "7. 品质管控：关键商品留存质检报告，监控品质退款率与投诉率，问题商品立即下架整改。\n"
           "8. 记录复盘：保存违规申诉与整改记录，定期对照《视频号小店违规管理规则》更新自查。\n\n")
    sections.append(adv)

    boundary = ("## 五、边界与纪律\n\n"
                "- 本核查依据《广告法》《价格法》《电子商务法》《消费者权益保护法》及微信视频号小店"
                "公开规则（商品信息发布规范、违规管理规则、直播带货规范）整理，"
                "**不替代平台官方规则与审核结论**，以平台最新规则为准。\n"
                "- 定向准入类目（食品、保健食品、医疗器械、化妆品、图书等）须先取得资质并报备，无资质不得带货。\n"
                "- 严禁销售禁售商品，严禁引导站外/私下交易，严禁虚假宣传与价格欺诈。\n"
                "- 本报告不构成法律意见；涉及广告合规与经营资质的重大事项请咨询律师或主管部门。\n")
    sections.append(boundary)

    print("\n".join(sections))
    return 0


if __name__ == "__main__":
    sys.exit(main())
