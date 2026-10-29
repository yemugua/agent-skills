---
name: pdf-tuyahe
description: PDF压缩与合并操作：流程、材料与避坑。tools精品指南。
---

PDF文件太大发不出去、多份文件要合成一份，都是高频需求。
## 免费方案（优先用）
1. WPS/Adobe 官方自带：打开PDF→输出为PDF→压缩质量选"标准"
2. 浏览器在线工具：iLovePDF、Smallpdf（免费有次数限制，敏感文件慎传）
3. PDF24（桌面版，完全免费无上传，适合隐私文件）
## 手机端
- iOS：文件App→快速操作→创建PDF
- 安卓：WPS Office→PDF工具箱
## 合并操作
1. WPS：PDF工具→合并→拖入多个文件→调整顺序→导出
2. 命令行（进阶）：`pdftk a.pdf b.pdf cat output merged.pdf`
## 压缩技巧
- 图片型PDF（扫描件）：降分辨率至150dpi，体积减70%+
- 文字型PDF：压缩率有限，别反复压，画质会崩
## 红线
> ⚠️ **隐私提醒：含身份证、合同、病历的PDF勿用在线工具上传；在线服务可能留存文件。本篇为工具参考。**