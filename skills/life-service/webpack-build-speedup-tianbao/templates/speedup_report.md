# Webpack 构建提速报告 · 模板

> 填写前先读 `rules/build_analysis.md`；所有「优化后」的数字都必须来自实测，不允许估算。

---

## 一、基线数据（优化前必填）

| 指标 | 冷构建（CI 无缓存） | 二次构建（本地有缓存） | dev 冷启动 | HMR 增量 |
|---|---|---|---|---|
| 耗时 | | | | |
| 产物体积（含 gzip） | | | | |
| 模块数（SMP / stats） | | | | |

采集命令：

```bash
MEASURE=1 webpack
webpack --profile --json > stats-before.json
python scripts/webpack_config_check.py --stats stats-before.json --top 20
```

SMP 关键输出（粘贴 Loaders 与 Plugins 段）：

```
 SMP  ⏱  Loaders
   ...
 SMP  ⏱  Plugins
   ...
```

---

## 二、耗时归因

| 环节 | 归属 | 占比 | 判定 |
|---|---|---|---|
| loader 处理 | | | module count = ? |
| 压缩 / Terser | | | |
| 插件（Plugin） | | | |
| 模块解析 resolve | | | |
| source map 生成 | | | |

结论：主要瓶颈在 _______，优先级最高的三项动作是 _______。

---

## 三、改动清单（一次一项，逐项复测）

| # | 改动项 | 改前 | 改后 | 耗时变化 | 体积变化 | 是否保留 |
|---|---|---|---|---|---|---|
| 1 | loader 加 `include` / `exclude` | | | | | |
| 2 | `cache.type = filesystem` | | | | | |
| 3 | `thread-loader` | | | | | |
| 4 | `esbuild-loader` / `swc-loader` 替代 babel | | | | | |
| 5 | `ts-loader` 开 `transpileOnly` | | | | | |
| 6 | `resolve` 精简 | | | | | |
| 7 | `devtool` 调整 | | | | | |
| 8 | `splitChunks` 补 `chunks: all` | | | | | |
| 9 | `IgnorePlugin` 干掉多余 locale | | | | | |
| 10 | tree shaking 三条件核对 | | | | | |

> 每改一项立刻重测并记录。**不要一次改五项然后说「不知道哪个有用」。**

---

## 四、配置体检结果

```
python scripts/webpack_config_check.py --file webpack.config.js
```

| 级别 | 条目 | 处置 |
|---|---|---|
| 严重 | | |
| 错误 | | |
| 警示 | | |
| 提示 | | |

---

## 五、高风险变更确认（涉及时必须逐项签字）

| 检查项 | 结论 |
|---|---|
| `"sideEffects": false` 是否覆盖了有副作用的模块（polyfill / 全局样式） | |
| `externals` 的 CDN 是否可控，是否配了 SRI | |
| 生产 devtool 是否还能满足线上报错定位 | |
| 产物是否做过功能验证（不只是构建成功） | |
| 老浏览器/目标环境的语法兼容是否验证（换 esbuild/swc 时） | |

---

## 六、CI 固化清单

- [ ] `cacheDirectory` 做了持久化挂载
- [ ] `cache.buildDependencies` 声明了 webpack 配置文件
- [ ] CI 产出 `stats.json` 并能回溯历史耗时
- [ ] 构建耗时超阈值失败/告警已配置
- [ ] 产物体积同时也被记录（防止「构建变快但体积变大」）

---

## 七、最终结论

| 项 | 结果 |
|---|---|
| 冷构建 | __ s → __ s（降低 __%） |
| 二次构建 | __ s → __ s（降低 __%） |
| 产物 gzip 体积 | __ KB → __ KB |
| 保留的改动 | |
| 回滚的改动及原因 | |
| 遗留 TODO | |

> 本报告是工程改进记录，不构成对线上产物行为的保证；任何构建配置变更都必须以实际产物验证为准。
