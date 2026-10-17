# -*- coding: utf-8 -*-
"""小程序 ICP 代备案流程与操作指引核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：多段报告，含结论摘要、前置条件、流程进度与下一步、特殊类目资质、
      代备案风险、常见驳回原因、备案后事项、操作指引、边界。

只做流程指引与核查，不替代管局与微信公众平台官方审核结论。
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
    "主体类型": ["主体类型", "备案主体类型", "账号主体", "主体"],
    "是否持有营业执照": ["是否持有营业执照", "有无营业执照", "营业执照", "是否有执照", "执照"],
    "统一社会信用代码": ["统一社会信用代码", "信用代码", "执照编号", "社会信用代码"],
    "小程序是否已注册并认证": ["小程序是否已注册并认证", "小程序是否注册", "小程序是否认证",
                              "是否完成注册认证", "小程序状态"],
    "小程序名称": ["小程序名称", "小程序名字", "名称"],
    "服务类目": ["服务类目", "类目", "小程序类目", "经营类目"],
    "是否涉及特殊类目": ["是否涉及特殊类目", "是否特殊类目", "是否需特殊资质类目"],
    "特殊类目资质是否齐备": ["特殊类目资质是否齐备", "资质是否齐备", "特殊资质是否齐全",
                            "类目资质是否齐备"],
    "域名是否已注册并实名": ["域名是否已注册并实名", "域名是否实名", "域名实名", "域名是否已实名"],
    "域名是否已完成ICP备案": ["域名是否已完成ICP备案", "域名备案状态", "域名是否已备案", "ICP备案"],
    "接入商/服务器": ["接入商/服务器", "接入商", "服务器", "云服务商", "接入服务商"],
    "当前备案状态": ["当前备案状态", "备案状态", "备案进度", "备案阶段"],
    "是否委托第三方代备案": ["是否委托第三方代备案", "是否代备案", "是否委托代理备案",
                            "代备案", "是否代理备案"],
    "负责人/法人信息是否齐全": ["负责人/法人信息是否齐全", "负责人信息是否齐全",
                              "法人信息是否齐全", "主体负责人信息"],
    "是否完成人脸核验": ["是否完成人脸核验", "人脸核验", "是否人脸核验", "核验状态"],
    "是否完成管局短信核验": ["是否完成管局短信核验", "短信核验", "管局短信核验", "短信验证"],
    "是否需要前置审批文件": ["是否需要前置审批文件", "前置审批", "前置审批文件", "是否需要前置审批"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)

# 特殊类目 → 资质/红线提示（与 icp-check 保持一致口径）
SPECIAL_CAT = {
    "医疗": "须《医疗机构执业许可证》；互联网诊疗须另行审批",
    "药品": "须《药品经营许可证》（线上售药另有严格规定）",
    "医疗器械": "须《医疗器械经营许可证》或备案凭证（按类别区分）",
    "食品": "须《食品经营许可证》或《食品生产许可证》（仅预包装食品需备案）",
    "餐饮": "须《食品经营许可证》",
    "金融": "须金融业务许可或备案，须持牌，个人不得从事",
    "理财": "须金融业务许可或备案，须持牌",
    "借贷": "须金融业务许可或备案，须持牌",
    "证券": "须《证券投资咨询》或《经营证券期货业务许可证》",
    "基金": "须基金销售业务资格",
    "保险": "须《经营保险业务许可证》或《保险中介许可证》",
    "支付": "须《支付业务许可证》（第三方支付牌照）",
    "直播": "须《网络文化经营许可证》《信息网络传播视听节目许可证》",
    "游戏": "须游戏版号、ISBN",
    "出版": "须《出版物经营许可证》",
    "网络出版": "须《出版物经营许可证》",
    "新闻": "须《互联网新闻信息服务许可》（个人不得采编）",
    "教育培训": "学科类须《办学许可证》（另有规定，须谨慎）",
    "学科": "学科类培训须《办学许可证》",
    "招聘": "须《人力资源服务许可证》",
    "人力资源": "须《人力资源服务许可证》",
    "婚恋": "相关经营资质与实名认证机制",
    "宗教": "宗教活动场所/主管部门材料（限制严格）",
    "危化品": "须危险化学品经营/《安全生产许可证》",
    "网约车": "须《网络预约出租汽车经营许可》",
    "拍卖": "须《拍卖经营批准证书》",
}

# 常见需《增值电信业务经营许可证》（ICP 证/EDI 证）场景
VAT_SCENES = ("电商", "商家入驻", "交易撮合", "在线交易", "收费信息", "会员付费",
              "有偿信息", "saas", "SaaS", "对外收费")

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


def parse_num(text):
    if unknown(text):
        return None
    m = re.search(r"-?\d+(\.\d+)?", str(text))
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def has_special_cat(text):
    if unknown(text):
        return None
    n = norm(text)
    best = None
    for w in sorted(SPECIAL_CAT, key=len, reverse=True):
        if w in n:
            best = w
            break
    return best


def classify_subject(text):
    if unknown(text):
        return None
    n = norm(text)
    if any(k in n for k in ("企业", "公司", "企业")):
        return "enterprise"
    if any(k in n for k in ("个体", "工商户", "个体户")):
        return "individual"
    if any(k in n for k in ("个人", "自然人")):
        return "personal"
    return "other"


def check_prereq(f):
    items = []
    crit = []
    risk = []
    subj = classify_subject(get_text(f, "主体类型"))
    items.append("- 主体类型：%s" % (get_text(f, "主体类型") if filled(get_text(f, "主体类型")) else "未填"))

    lic = yesno(get_text(f, "是否持有营业执照"))
    if subj in ("enterprise", "individual"):
        if lic is False:
            crit.append("企业/个体工商户主体必须持有营业执照方可备案：请先办理营业执照，"
                        "且备案主体须与营业执照一致，否则管局驳回")
            items.append("- 营业执照：无（阻断）")
        elif lic is True:
            code = get_text(f, "统一社会信用代码")
            if not filled(code):
                risk.append("已持营业执照但未填写统一社会信用代码：备案须填与执照一致的信用代码，请补齐")
                items.append("- 统一社会信用代码：未填（风险）")
            else:
                items.append("- 营业执照：有；信用代码：已填")
        else:
            risk.append("未确认是否持有营业执照：企业/个体主体备案必须具备，请确认并上传")
            items.append("- 营业执照：未确认（风险）")
    elif subj == "personal":
        items.append("- 营业执照：个人主体无需营业执照，使用身份证备案")
    else:
        if lic is False:
            crit.append("主体类型未确认且未持营业执照：若为企/个体必须补执照；"
                        "请先明确主体类型与证件")
            items.append("- 营业执照：无（阻断-主体不明）")
        else:
            risk.append("未确认主体类型：个人用身份证、企业/个体用营业执照，主体须与后续信息一致")
            items.append("- 营业执照：待确认主体类型")

    reg = yesno(get_text(f, "小程序是否已注册并认证"))
    if reg is False:
        crit.append("小程序尚未完成注册与认证：备案前须先在微信公众平台注册小程序并完成认证，"
                    "否则无备案入口")
        items.append("- 小程序注册认证：否（阻断）")
    elif reg is True:
        items.append("- 小程序注册认证：是")
    else:
        risk.append("未确认小程序是否已注册并认证：备案须先完成，请确认")
        items.append("- 小程序注册认证：未确认（风险）")

    domain_real = yesno(get_text(f, "域名是否已注册并实名"))
    if domain_real is False:
        crit.append("域名未完成注册与实名：备案域名须已完成实名认证（实名满一定天数依管局要求），"
                    "请先注册并实名域名")
        items.append("- 域名实名：否（阻断）")
    elif domain_real is True:
        items.append("- 域名实名：是")
    else:
        risk.append("未确认域名是否已实名：备案域名须实名，请确认")
        items.append("- 域名实名：未确认（风险）")

    access = get_text(f, "接入商/服务器")
    if not filled(access):
        risk.append("未填写接入商/服务器：备案须由接入服务商（云厂商）提交，"
                    "请确认已购大陆节点服务器并获取接入信息")
        items.append("- 接入商/服务器：未填（风险）")
    else:
        items.append("- 接入商/服务器：已填")

    dom_icp = get_text(f, "域名是否已完成ICP备案")
    if filled(dom_icp) and any(k in norm(dom_icp) for k in ("未备案", "待备案", "本次待办", "需要备案")):
        risk.append("域名尚未完成 ICP 备案：若解析到大陆服务器必须备案，"
                    "本流程即为此项；按步骤提交即可")
        items.append("- 域名 ICP 备案：%s（待办）" % dom_icp)
    elif filled(dom_icp) and any(k in norm(dom_icp) for k in ("已备案", "完成", "有备案")):
        items.append("- 域名 ICP 备案：%s" % dom_icp)
    else:
        items.append("- 域名 ICP 备案：%s" % (dom_icp if filled(dom_icp) else "未确认"))
    return items, crit, risk


def check_process(f):
    items = []
    risk = []
    status = get_text(f, "当前备案状态")
    face = yesno(get_text(f, "是否完成人脸核验"))
    sms = yesno(get_text(f, "是否完成管局短信核验"))
    n = norm(status) if filled(status) else ""

    stage = None
    if not filled(status):
        stage = "准备阶段"
        items.append("- 当前阶段：未确认备案状态 → 视为「准备阶段」")
        risk.append("未确认备案状态：若尚未开始，请按准备阶段逐项落实前置条件后再提交")
    elif any(k in n for k in ("未备案", "待备案", "准备", "未提交", "未开始")):
        stage = "准备阶段"
        items.append("- 当前阶段：准备阶段（尚未提交）")
    elif any(k in n for k in ("已提交", "平台审核", "待审", "微信审核")):
        stage = "平台审核"
        items.append("- 当前阶段：平台（微信）审核中")
        if face is not True:
            risk.append("已提交但人脸核验未完成：须小程序管理员在公众平台完成人脸核验，否则无法上报管局")
            items.append("  - 人脸核验：未完成（待办）")
        else:
            items.append("  - 人脸核验：已完成")
    elif any(k in n for k in ("管局", "通信管理局", "省级", "审核中")):
        stage = "管局审核"
        items.append("- 当前阶段：管局（通信管理局）审核中（约 20 个工作日内）")
        if sms is not True:
            risk.append("管局审核期内会下发短信核验：须在 24 小时内完成短信核验，"
                        "超时订单将被退回，须重新提交")
            items.append("  - 短信核验：未完成（务必 24h 内处理）")
        else:
            items.append("  - 短信核验：已完成")
    elif any(k in n for k in ("已备案", "完成", "通过", "成功")):
        stage = "完成"
        items.append("- 当前阶段：已完成备案")
    elif any(k in n for k in ("驳回", "退回", "不通过", "失败")):
        stage = "被驳回"
        items.append("- 当前阶段：被驳回/退回（需按驳回原因整改后重新提交）")
        risk.append("备案被驳回：请查看驳回原因（主体信息、类目与页面不符、资料模糊等），"
                    "整改后重新提交，不必重复缴费")
    else:
        stage = "其他"
        items.append("- 当前阶段：%s（未识别，请对照平台状态）" % status)

    # 下一步建议
    steps = {
        "准备阶段": "落实营业执照/实名域名/接入商，在公众平台填写主体与小程序信息后提交。",
        "平台审核": "平台审核通过后完成人脸核验，等待上报管局。",
        "管局审核": "留意管局短信，24 小时内完成短信核验，耐心等待审核结果。",
        "完成": "在小程序前端悬挂备案号，后续信息变更须及时变更备案。",
        "被驳回": "按驳回原因整改，重新提交备案（无需重复缴费）。",
        "其他": "对照平台当前状态，补齐缺失节点。",
    }
    items.append("- 下一步：%s" % steps.get(stage, steps["其他"]))
    return items, risk


def check_category(f):
    items = []
    crit = []
    risk = []
    cat = get_text(f, "服务类目")
    special_flag = yesno(get_text(f, "是否涉及特殊类目"))
    if filled(cat):
        items.append("- 服务类目：%s" % cat)
        hit = has_special_cat(cat)
        if hit or special_flag is True:
            key = hit or "特殊"
            tip = SPECIAL_CAT.get(hit, "须对应主管部门许可或资质")
            items.append("  - 命中特殊类目：%s" % key)
            items.append("  - 所需资质：%s" % tip)
            lic_ok = yesno(get_text(f, "特殊类目资质是否齐备"))
            if lic_ok is False:
                crit.append("服务类目涉及特殊类目（%s）但资质未齐备：须先取得 %s，"
                            "否则备案不予通过且上线后被下架" % (key, tip))
                items.append("  - 类目资质：未齐备（阻断）")
            elif lic_ok is True:
                items.append("  - 类目资质：已齐备")
            else:
                risk.append("涉及特殊类目但未确认资质是否齐备：请上传有效期内对应许可，主体须一致")
                items.append("  - 类目资质：未确认（风险）")
        else:
            items.append("  - 类目性质：常规类目（非特殊，一般无需额外许可）")
        # 增值电信判断
        if any(k in norm(cat) for k in VAT_SCENES):
            risk.append("类目涉及电商/收费服务：可能还需《增值电信业务经营许可证》（ICP 证/EDI 证），"
                        "请按平台与主管部门要求确认")
            items.append("  - 增值电信：可能涉及 ICP/EDI 证（提示）")
    else:
        if special_flag is True:
            risk.append("勾选涉及特殊类目但未填具体类目：请明确类目名称以便映射所需资质")
            items.append("- 服务类目：未填（已勾选特殊类目-风险）")
        else:
            risk.append("未填服务类目：无法确定是否涉及特殊类目与增值电信要求，请补齐")
            items.append("- 服务类目：未填（风险）")
    return items, crit, risk


def check_agent(f):
    items = []
    risk = []
    agent = yesno(get_text(f, "是否委托第三方代备案"))
    if agent is True:
        items.append("- 是否委托第三方代备案：是")
        risk.append("委托第三方代备案须注意：① 备案主体必须为你自己的企业/个体/个人，"
                    "不得由代理买卖或套用他人主体；② 提供真实材料，虚假信息将被驳回乃至列入黑名单；"
                    "③ 选择有资质的接入商/代理机构，警惕「包过」「免材料」等夸大承诺与额外收费；"
                    "④ 备案成功后账号与域名控制权须归你，避免被代理绑定。")
        items.append("  - 代备案风险提示：见下方「代备案风险」")
    elif agent is False:
        items.append("- 是否委托第三方代备案：否（自行备案）")
    else:
        items.append("- 是否委托第三方代备案：未确认")
    return items, risk


def check_reject(f):
    items = []
    risk = []
    pre = get_text(f, "负责人/法人信息是否齐全")
    if yesno(pre) is False:
        risk.append("负责人/法人信息不齐：备案须填真实有效的负责人与法人信息，"
                    "信息不符或缺失是常见驳回原因")
        items.append("- 负责人/法人信息：不齐（驳回风险）")
    elif yesno(pre) is True:
        items.append("- 负责人/法人信息：齐全")
    else:
        items.append("- 负责人/法人信息：未确认")

    preapp = yesno(get_text(f, "是否需要前置审批文件"))
    if preapp is True:
        risk.append("该类目涉及需前置审批（如新闻、出版、药品、医疗、宗教等）："
                    "须先取得主管部门前置审批文件并提交，否则备案驳回")
        items.append("- 前置审批文件：需要（须先取得并提交）")
    elif preapp is False:
        items.append("- 前置审批文件：不需要")
    else:
        items.append("- 前置审批文件：未确认")
    return items, risk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="")
    args = ap.parse_args()
    f = parse_md(args.path)
    if not f or not any(filled(v) for v in f.values()):
        print("# 待补正\n\n未读取到任何有效字段，请填写采集表后再核查。")
        return 2

    crit = []
    risk = []
    sections = []

    subj_txt = get_text(f, "主体类型")
    header = "# 小程序 ICP 代备案流程与操作指引报告"
    if filled(subj_txt):
        header += "（%s）" % subj_txt
    sections.append(header)
    sections.append("")

    pre_items, pre_c, pre_r = check_prereq(f)
    crit += pre_c
    risk += pre_r
    proc_items, proc_r = check_process(f)
    risk += proc_r
    cat_items, cat_c, cat_r = check_category(f)
    crit += cat_c
    risk += cat_r
    ag_items, ag_r = check_agent(f)
    risk += ag_r
    rej_items, rej_r = check_reject(f)
    risk += rej_r

    if crit:
        verdict = "不通过"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "通过"
    summary = "## 一、结论摘要\n\n"
    summary += "- 总体结论：**%s**（阻断项 %d / 风险与待办项 %d）\n" % (verdict, len(crit), len(risk))
    if filled(subj_txt):
        summary += "- 主体类型：%s\n" % subj_txt
    summary += "- 处置建议：先消除全部阻断项（主体/资质硬门槛），再按流程推进备案各节点。\n"
    sections.append(summary)

    body = "## 二、分项核查\n\n"
    body += "### 前置条件核查\n" + "\n".join(pre_items) + "\n\n"
    body += "### 备案流程进度与下一步\n" + "\n".join(proc_items) + "\n\n"
    body += "### 特殊类目资质\n" + "\n".join(cat_items) + "\n\n"
    body += "### 代备案风险\n" + "\n".join(ag_items) + "\n\n"
    body += "### 常见驳回风险\n" + "\n".join(rej_items) + "\n"
    sections.append(body)

    rb = "## 三、阻断项与风险/待办\n\n"
    if crit:
        rb += "### 阻断项（必须处理，否则无法提交/不予通过）\n"
        for i, c in enumerate(crit, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if risk:
        rb += "### 风险/待办项（建议处理）\n"
        for i, c in enumerate(risk, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if not crit and not risk:
        rb += "前置条件与资质齐备，可按流程提交备案。\n\n"
    sections.append(rb)

    post = ("## 四、备案后事项\n\n"
            "1. 悬挂备案号：小程序前端须展示 ICP 备案号（如 沪ICP备XXXXXXXX号-X）。\n"
            "2. 变更备案：主体、名称、域名、接入商等信息变更须及时提交变更，避免被注销。\n"
            "3. 注销备案：小程序停用或域名不再解析到大陆服务器时，应办理注销，释放主体配额。\n"
            "4. 年审/核查：保持证件在有效期内，管局可能随机核查，虚假备案将被列入黑名单。\n\n")
    sections.append(post)

    adv = ("## 五、操作指引（标准备案流程）\n\n"
           "1. 准备：营业执照/身份证、实名域名、大陆节点服务器（接入商）。\n"
           "2. 注册认证：在微信公众平台注册小程序并完成认证，开通备案入口。\n"
           "3. 填写：主体信息、小程序信息、服务类目、负责人信息，上传资质（特殊类目）。\n"
           "4. 提交：确认信息无误后提交，平台（微信）初审。\n"
           "5. 人脸核验：小程序管理员在公众平台完成人脸核验。\n"
           "6. 管局审核：上报通信管理局，约 20 个工作日内出结果。\n"
           "7. 短信核验：收到管局短信后 24 小时内完成核验，否则退回。\n"
           "8. 完成：备案通过，悬挂备案号，按需办理变更/注销。\n\n")
    sections.append(adv)

    boundary = ("## 六、边界与纪律\n\n"
                "- 本指引依据通用流程与公开参考整理，不替代管局与微信公众平台官方审核结论。\n"
                "- 备案主体、资质与流程最终以工业和信息化部备案系统、省级通信管理局与微信公众平台为准。\n"
                "- 不得买卖、套用备案主体或提交虚假材料，违者将被驳回乃至列入黑名单。\n")
    sections.append(boundary)

    print("\n".join(sections))
    return 0


if __name__ == "__main__":
    sys.exit(main())
