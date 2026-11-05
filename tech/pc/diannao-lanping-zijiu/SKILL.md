---
name: diannao-lanping-zijiu
description: 电脑蓝屏排查修复：步骤、要点与避坑。实操指南。
---

电脑蓝屏自救五步。
## 记录错误码
- 蓝屏页的 STOP 代码（如 CRITICAL_PROCESS_DIED / 0x0000007B）——搜索定位原因
## 按概率排查
1. **内存条**：重新插拔/橡皮擦金手指；Windows内存诊断工具（mdsched）
2. **硬盘**：SMART 状态检查（CrystalDiskInfo），坏道前兆频繁蓝屏
3. **驱动**：进安全模式，卸载最近更新的显卡/驱动（设备管理器回退）
4. **系统文件**：管理员CMD跑 sfc /scannow + DISM /Online /Cleanup-Image /RestoreHealth
5. **超频/新硬件**：BIOS恢复默认
## 数据优先
- 反复蓝屏进不了系统：PE启动盘/U盘系统救数据再修
## 送修判据
- 硬盘SMART异常/异响：别再通电，直接送（数据>电脑）
## 红线
> ⚠️ **提醒：不明来源的"蓝屏修复软件"多为捆绑垃圾；本篇为参考。**