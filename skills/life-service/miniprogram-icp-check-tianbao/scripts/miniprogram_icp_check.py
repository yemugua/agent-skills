# -*- coding: utf-8 -*-
"""小程序备案与类目资质核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：多段报告，含结论摘要、ICP备案核查、特殊类目资质、类目一致性、
      隐私合规、风险与整改、待办动作、边界与纪律。

只做核查指引，不替代管局与平台审核结论。
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
    "小程序名称": ["小程序名称", "名称", "app名称"],
    "小程序主体类型": ["小程序主体类型", "主体类型", "主体性质", "主体"],
    "小程序APPID": ["小程序appid", "appid", "appid"],
    "是否对外提供服务": ["是否对外提供服务", "是否上线", "是否对外服务", "是否已发布"],
    "是否已完成ICP备案": ["是否已完成icp备案", "是否备案", "备案情况", "icp备案", "是否完成备案"],
    "备案号": ["备案号", "icp备案号", "备案许可号"],
    "备案主体名称": ["备案主体名称", "备案主体", "备案单位"],
    "备案主体与小程序主体是否一致": ["备案主体与小程序主体是否一致", "主体是否一致",
                           "备案主体与小程主体一致", "主体一致性"],
    "备案状态": ["备案状态", "备案状态正常", "备案是否正常"],
    "主营服务类目": ["主营服务类目", "服务类目", "主营类目", "所选类目"],
    "是否涉及特殊类目": ["是否涉及特殊类目", "是否特殊类目", "特殊行业", "是否需资质"],
    "特殊类目名称": ["特殊类目名称", "特殊类目", "所属行业", "具体行业"],
    "是否已上传资质证件": ["是否已上传资质证件", "是否上传资质", "资质上传情况", "是否有资质"],
    "资质是否在有效期内": ["资质是否在有效期内", "资质有效期", "资质是否过期"],
    "类目与页面内容是否一致": ["类目与页面内容是否一致", "类目是否一致", "页面内容是否一致",
                         "类目与内容一致性"],
    "是否已配置隐私保护指引": ["是否已配置隐私保护指引", "隐私保护指引", "是否配置隐私",
                         "隐私协议", "隐私声明"],
    "是否收集用户个人信息": ["是否收集用户个人信息", "是否收集用户信息", "是否收集个人信息",
                         "收集用户信息"],
    "收集信息类型": ["收集信息类型", "收集信息", "个人信息类型", "采集字段"],
    "是否最小必要": ["是否最小必要", "是否最小必要收集", "收集是否必要", "是否过度收集"],
    "是否有用户个人信息收集使用说明": ["是否有用户个人信息收集使用说明", "收集使用说明",
                             "个人信息收集说明", "隐私说明文档"],
    "缺失项": ["缺失项", "还差什么", "待补材料"],
    "期望结果": ["期望结果", "诉求", "希望怎么解决"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)

# 特殊类目 → 所需资质提示
SPECIAL_CATS = {
    "医疗": "医疗机构执业许可证等医疗卫生相关资质（互联网诊疗/药品需另行审批）",
    "药品": "药品经营许可证或医疗器械经营许可证（线上售药另有严格规定）",
    "医疗器械": "医疗器械经营许可证或备案凭证（按类别区分许可/备案）",
    "食品": "食品经营许可证或食品生产许可证（仅销售预包装食品需备案）",
    "金融": "金融业务相关许可或备案（借贷、理财、保险、征信等须持牌，个人不得从事）",
    "证券": "证券投资咨询/经营证券期货业务许可证（须持牌机构）",
    "基金": "基金销售业务资格或公募基金托管/销售许可",
    "保险": "经营保险业务许可证、保险中介许可证",
    "支付": "支付业务许可证（第三方支付牌照，个人/一般企业无资质）",
    "直播": "网络文化经营许可证、信息网络传播视听节目许可证等",
    "游戏": "游戏版号、ISBN 等游戏出版与运营相关材料",
    "出版": "出版物经营许可证（网络出版需相应许可）",
    "新闻": "互联网新闻信息服务许可（须资质，个人不得采编新闻）",
    "教育培训": "办学许可证或教育相关资质（学科类培训另有规定，须谨慎）",
    "招聘": "人力资源服务许可证",
    "婚恋": "相关经营资质与用户实名认证机制",
    "宗教": "宗教活动场所或主管部门相关材料（宗教内容限制严格）",
    "危化": "危险化学品经营/安全生产许可证",
    "网约车": "网络预约出租汽车经营许可",
    "拍卖": "拍卖经营批准证书",
    "公证": "公证机构资质（非商事主体可办）",
}

# 需增值电信业务许可证(ICP证/EDI证)的典型场景
VALUE_ADDED_TELECOM = ["电商平台", "在线交易", "收费信息服务", "信息发布收费", "saas",
                    "会员付费", "有偿信息", "二方交易", "交易市场", "商家入驻"]


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
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
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
            parts = re.split(r"[:：]", line, 1)
            if len(parts) == 2:
                k = parts[0].strip().lstrip("-*# ").strip()
                v = parts[1].strip()
                if k and v:
                    data[norm(k)] = v
    return data


def get_text(f, key):
    """先对输入建 norm 索引，兼容已 norm 与未 norm 两种 key。"""
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


NEG_WORDS = ("否", "没有", "未", "不", "无", "否认", "拒绝", "不知情", "没做", "无法")
POS_WORDS = ("是", "已", "有", "承认", "确认", "同意", "认可", "已做", "可以")


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


def has_cat(text):
    if unknown(text):
        return None
    n = norm(text)
    # 取最长匹配，避免「医疗」误匹配「医疗器械」
    best = None
    for w in sorted(SPECIAL_CATS, key=len, reverse=True):
        if w in n:
            best = w
            break
    return best


def check_icp(f):
    items = []
    crit = []
    risk = []
    filed = yesno(get_text(f, "是否已完成ICP备案"))
    status = get_text(f, "备案状态")
    if filed is None:
        risk.append("未确认是否完成 ICP 备案：2023 年起小程序需完成备案方可对外提供服务，"
                    "请先到管局备案系统或公众平台确认备案状态")
        items.append("- ICP 备案：**未确认**")
    elif filed is False:
        crit.append("未完成 ICP 备案：未备案小程序不能上线对外服务，须先完成主体备案与小程序备案"
                    "（备案号格式如 沪ICP备XXXXXXXX号-X）")
        items.append("- ICP 备案：**未完成（阻断）**")
    else:
        items.append("- ICP 备案：已完成")
        bh = get_text(f, "备案号")
        if not filled(bh):
            risk.append("已备案但未提供备案号：请补充完整备案号，格式通常为"
                        "「省份简称 + ICP备 + 编号 + 号 - 序号」")
        else:
            items.append("  - 备案号：%s" % bh)
        consistent = yesno(get_text(f, "备案主体与小程序主体是否一致"))
        if consistent is False:
            crit.append("备案主体与小程序主体不一致：备案主体须与小程序注册主体一致，"
                        "主体不一致需变更备案或重新注册主体，否则无法通过")
            items.append("  - 备案主体一致性：**不一致（阻断）**")
        elif consistent is None:
            risk.append("未确认备案主体与小程序主体是否一致：请核对备案单位名称与小程序主体名称")
            items.append("  - 备案主体一致性：未确认")
        else:
            items.append("  - 备案主体一致性：一致")
        if filled(status):
            sn = norm(status)
            if "注销" in sn or "未接入" in sn or "未备案" in sn:
                crit.append("备案状态异常（%s）：注销/未接入/未备案状态下小程序无法正常对外服务，"
                            "需重新接入或补备案" % status)
                items.append("  - 备案状态：**%s（异常）**" % status)
            else:
                items.append("  - 备案状态：%s" % status)
    return items, crit, risk


def check_special(f):
    items = []
    crit = []
    risk = []
    involve = yesno(get_text(f, "是否涉及特殊类目"))
    cat_name = get_text(f, "特殊类目名称")
    hit = has_cat(cat_name) if filled(cat_name) else None
    if involve is True or hit is not None:
        cat = hit or (cat_name if filled(cat_name) else "特殊类目")
        req = SPECIAL_CATS.get(hit) if hit else "对应行业主管部门的许可或资质证件"
        items.append("- 特殊类目：%s" % cat)
        items.append("  - 所需资质：%s" % req)
        uploaded = yesno(get_text(f, "是否已上传资质证件"))
        if uploaded is False:
            crit.append("%s 类目缺少资质证件：须先在「资质管理」上传有效期内的%s，"
                        "否则类目审核不通过" % (cat, req))
            items.append("  - 资质上传：**未上传（阻断）**")
        elif uploaded is None:
            risk.append("未确认是否已上传%s类目资质：请上传并在有效期内" % cat)
            items.append("  - 资质上传：未确认")
        else:
            items.append("  - 资质上传：已上传")
            exp = yesno(get_text(f, "资质是否在有效期内"))
            if exp is False:
                crit.append("%s 资质已过期：须更新有效期内的资质证件，过期资质等同于无资质" % cat)
                items.append("  - 资质有效期：**已过期（阻断）**")
            elif exp is None:
                risk.append("未确认资质是否在有效期内：请核对有效期")
                items.append("  - 资质有效期：未确认")
            else:
                items.append("  - 资质有效期：有效")
    else:
        if involve is None and not filled(cat_name):
            risk.append("未确认是否涉及特殊类目：若经营医疗/食品/金融/直播/出版/新闻等，"
                        "需对应主管部门资质，请确认类目")
        items.append("- 特殊类目：未涉及或无需特殊资质")
    # 增值电信业务许可证（在线交易/平台类）
    need_vat = yesno(get_text(f, "是否需增值电信业务许可证"))
    cat_lower = norm(cat_name)
    if need_vat is True or any(k in cat_lower for k in ("电商", "平台", "交易", "saas", "商家入驻")):
        risk.append("涉及在线交易/平台类服务，通常还需《增值电信业务经营许可证》（ICP 证 / EDI 证），"
                    "请确认是否已取得并在资质管理上传")
        items.append("- 增值电信业务许可证：需确认")
    return items, crit, risk


def check_cat_consistency(f):
    items = []
    risk = []
    consistent = yesno(get_text(f, "类目与页面内容是否一致"))
    cat = get_text(f, "主营服务类目")
    if filled(cat):
        items.append("- 主营服务类目：%s" % cat)
    if consistent is False:
        risk.append("服务类目与页面实际内容不一致：类目须与实际提供的服务一致，"
                    "否则审核会被驳回，请修改类目或调整页面内容")
        items.append("  - 一致性：**不一致（风险）**")
    elif consistent is None:
        risk.append("未确认类目与页面内容一致性：请核对所选类目是否覆盖全部页面功能")
        items.append("  - 一致性：未确认")
    else:
        items.append("  - 一致性：一致")
    return items, risk


def check_privacy(f):
    items = []
    risk = []
    has_guide = yesno(get_text(f, "是否已配置隐私保护指引"))
    collects = yesno(get_text(f, "是否收集用户个人信息"))
    if collects is True or (collects is None and filled(get_text(f, "收集信息类型"))):
        items.append("- 收集用户个人信息：是")
        if has_guide is False:
            crit = None
            risk.append("收集用户信息但未配置隐私保护指引：须配置并同步到代码，"
                        "且只在必要时申请授权，不得强制授权")
            items.append("  - 隐私保护指引：**未配置（风险）**")
        elif has_guide is None:
            risk.append("未确认是否配置隐私保护指引：收集个人信息必须配置")
            items.append("  - 隐私保护指引：未确认")
        else:
            items.append("  - 隐私保护指引：已配置")
        min_nec = yesno(get_text(f, "是否最小必要"))
        if min_nec is False:
            risk.append("收集可能非最小必要：仅收集业务必需的个人信息，明确告知用途与范围")
            items.append("  - 最小必要：**否（风险）**")
        elif min_nec is None:
            risk.append("未确认是否最小必要收集：请评估收集字段必要性")
            items.append("  - 最小必要：未确认")
        else:
            items.append("  - 最小必要：是")
        info_desc = get_text(f, "是否有用户个人信息收集使用说明")
        if not filled(info_desc):
            risk.append("未提供个人信息收集使用说明：应在指引中说明收集类型、用途、期限与第三方共享")
            items.append("  - 收集使用说明：未填写")
    else:
        items.append("- 收集用户个人信息：否/未确认")
        if has_guide is True:
            items.append("  - 已配置隐私保护指引")
    return items, risk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="")
    args = ap.parse_args()
    f = parse_md(args.path)
    if not f or not any(filled(v) for v in f.values()):
        # 全空：退出码 2，不崩
        print("# 待补正\n\n未读取到任何有效字段，请填写采集表后再核查。")
        return 2

    crit = []
    risk = []
    sections = []

    name = get_text(f, "小程序名称")
    header = "# 小程序备案与类目资质核查报告"
    if filled(name):
        header += "：%s" % name
    sections.append(header)
    sections.append("")

    icp_items, icp_c, icp_r = check_icp(f)
    crit += icp_c
    risk += icp_r
    sec_items, sec_c, sec_r = check_special(f)
    crit += sec_c
    risk += sec_r
    cons_items, cons_r = check_cat_consistency(f)
    risk += cons_r
    priv_items, priv_r = check_privacy(f)
    risk += priv_r

    # 结论摘要
    if crit:
        verdict = "不通过"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "通过"
    summary = "## 一、结论摘要\n\n"
    summary += "- 总体结论：**%s**（阻断项 %d / 风险项 %d）\n" % (verdict, len(crit), len(risk))
    if filled(name):
        summary += "- 小程序：%s\n" % name
    summary += "- 处置建议：先解决全部必须处理项，再处理风险项后提审或上线。\n"
    sections.append(summary)

    # 分项核查
    body = "## 二、分项核查\n\n"
    body += "### ICP 备案\n" + "\n".join(icp_items) + "\n\n"
    body += "### 特殊类目与资质\n" + "\n".join(sec_items) + "\n\n"
    body += "### 类目与页面一致性\n" + "\n".join(cons_items) + "\n\n"
    body += "### 隐私与用户合规\n" + "\n".join(priv_items) + "\n"
    sections.append(body)

    # 风险与整改
    rb = "## 三、风险与整改\n\n"
    if crit:
        rb += "### 阻断项（必须解决）\n"
        for i, c in enumerate(crit, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if risk:
        rb += "### 风险项（建议处理）\n"
        for i, c in enumerate(risk, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if not crit and not risk:
        rb += "未发现明显阻断或风险项，可进入提审/上线流程。\n\n"
    sections.append(rb)

    # 待办动作
    todo = "## 四、待办动作\n\n"
    order = 1
    for c in crit:
        todo += "%d. 【必办】%s\n" % (order, c.split("：")[0] if "：" in c else c[:20])
        order += 1
    for c in risk:
        todo += "%d. 【建议】%s\n" % (order, c.split("：")[0] if "：" in c else c[:20])
        order += 1
    if order == 1:
        todo += "暂无可登记待办。\n"
    todo += "\n"
    sections.append(todo)

    # 边界
    boundary = ("## 五、边界与纪律\n\n"
                "- 本核查依据通用规则与公开参考整理，不替代管局与企业微信公众平台审核结论。\n"
                "- 备案、类目与资质最终以管局备案系统、微信公众平台审核为准。\n"
                "- 不承诺备案或资质一定通过；最终以官方结果为准。\n")
    sections.append(boundary)

    print("\n".join(sections))
    return 0


if __name__ == "__main__":
    sys.exit(main())
