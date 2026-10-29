---
name: chazhang-chuangjian
description: Excel求和与常用函数：流程、要点与避坑。精品指南。
---

Excel高频操作，收藏这一篇够用80%场景。
## 求和家族
1. `=SUM(A1:A10)` 基础求和
2. `=SUMIF(A:A,"华东",B:B)` 条件求和（区域=华东的B列和）
3. `=SUMIFS(B:B,A:A,"华东",C:C,">100")` 多条件
## 统计
1. `=COUNTIF(A:A,"是")` 计数
2. `=AVERAGE(B2:B100)` 平均
3. `=MAX/MIN`
## 查找匹配
1. `=VLOOKUP(D2,A:B,2,0)` 按D2在A列找，返回B列对应值（0=精确）
2. 新版用 `=XLOOKUP(D2,A:A,B:B,"未找到")` 更灵活
## 文本与日期
1. `=CONCAT/TEXTJOIN` 合并；`=LEFT/MID/RIGHT` 截取
2. `=TEXT(A1,"yyyy-mm-dd")` 日期格式化
3. `=DATEDIF(A1,TODAY(),"Y")` 算年龄/工龄
## 快捷键
- Ctrl+方向键（跳边界）、Ctrl+Shift+L（筛选）、Alt+=（自动求和）、F4（锁引用）
## 数据透视表
- 插入→透视表→拖字段，10秒出汇总报表，比函数省事
## 红线
> ⚠️ **提醒：函数结果粘贴成值（选择性粘贴）再发别人，防链接错乱；本篇为参考。**