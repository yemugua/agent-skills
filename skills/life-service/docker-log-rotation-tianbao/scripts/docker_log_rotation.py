# -*- coding: utf-8 -*-
"""容器日志治理与轮转 —— 操作清单生成引擎"""
import sys, re
sys.stdout.reconfigure(encoding="utf-8")

STAGES = [('采集规划', ['日志驱动选型', '标签规范', '采集频率', '落盘位置']), ('轮转配置', ['json-file 上限', 'logrotate 策略', '压缩与保留期', '异地转发']), ('磁盘防护', ['分区隔离', '水位告警', '清理预案', '写入限速']), ('排障与验证', ['日志连续性', '丢日志定位', '时区统一', '检索验证'])]

def norm(s):
    return re.sub(r"[\s_\-—－・:：]+", "", str(s or "")).lower()

def parse(path):
    fields = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line.startswith("- ") and ":" in line[2:]:
            k, _, v = line[2:].partition(":")
            fields[norm(k)] = v.strip()
    return fields

def get_text(fields, label):
    key = norm(label)
    if key in fields:
        return fields[key]
    for k, v in fields.items():
        if key and (key in k or k in key):
            return v
    return ""

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "testdata/样例.md"
    fields = parse(path)
    scene = get_text(fields, "适用场景") or "通用场景"
    level = get_text(fields, "问题程度") or "常规"
    tool = get_text(fields, "可用工具") or "常规工具"
    limit = get_text(fields, "特殊约束") or "无"
    out = []
    out.append("# 容器日志治理与轮转 · 操作清单")
    out.append("- 场景：%s ｜ 程度：%s" % (scene, level))
    out.append("- 可用工具：%s" % tool)
    out.append("- 特殊约束：%s" % limit)
    out.append("")
    total = 0
    for stage, items in STAGES:
        out.append("## %s" % stage)
        for it in items:
            total += 1
            out.append("- [ ] %s" % it)
        out.append("- [ ] 阶段验收：确认本阶段目标达成后再进入下一阶段")
        total += 1
        out.append("- [ ] 阶段禁忌：按 SKILL.md「规则要点」执行，禁止跳步")
        total += 1
        out.append("")
    out.append("## 总体验收")
    out.append("- [ ] 全部 %d 个步骤已完成并打勾" % total)
    out.append("- [ ] 结果符合验收标准，异常已记录")
    out.append("")
    out.append("> 本清单由操作引擎按 STAGES 模板生成，可按场景删减。")
    print("\n".join(out))

if __name__ == "__main__":
    main()
