---
name: webpack-build-speedup
slug: webpack-build-speedup-tianbao
displayName: Webpack 构建耗时分析与提速
display_name: "Webpack 构建耗时分析与提速"
display_name_en: "Webpack Build Time Analysis and Speed Optimization"
version: "1.0.0"
summary: 一切提速从测量开始：speed-measure-webpack-plugin 的 SMP 输出怎么读（先看 Loaders 段的 module count，1500 个模块跑 babel 说明 loader 范围没收窄）、webpack --profile --json 出 stats.json 做 CI 基线、冷构建与二次构建要分开算；提速手段按收益排优先级：exclude node_modules 缩小 loader 范围常有 2-5 倍、cache.type filesystem 让二次构建省 50-80%（含 CI 没挂载缓存目录、buildDependencies 没配导致改了不生效、容器镜像重建导致全量失效三个坑）、thread-loader 在模块数小于 500 时反而更慢、swc/esbuild-loader 替代 babel 常有三到十倍收益、resolve.extensions 与 modules 减少探测、ts-loader 的 transpileOnly 把类型检查挪给 fork-ts-checker；附 devtool 选型表、tree shaking 生效三条件与 sideEffects 误配事故、splitChunks 的 chunks: all 陷阱、externals 与 CDN 的取舍，每条配错误写法与正确写法对照，配脚本静态检查 webpack 配置并分析 stats.json 找出最大模块。
description: 构建越来越慢、CI 打包要十几分钟、改一行代码热更新等半天、不知道时间花在哪、加了很多配置却没效果时使用。当用户说"webpack 构建太慢怎么办""怎么知道是哪一步慢""optimized 和 include 该怎么配""持久化缓存为什么没效果""thread-loader 要用吗""为什么 tree shaking 没删掉代码""splitChunks 配了为什么没分包""生产 sourcemap 太慢怎么办""怎么把 moment 语言包去掉"时使用。内置 SMP 输出读法与 stats.json 自分析方法、九类提速手段的收益与风险对照表、loader 范围收窄写法、filesystem cache 配置与三个失效坑、并行化适用边界与替代方案、resolve 精简五项、devtool 速度对照表、tree shaking 三条件与 sideEffects 副作用风险、splitChunks 的 chunks all 与 runtimeChunk 配置、按需加载与 IgnorePlugin 处理巨型第三方库，配 scripts/webpack_config_check.py 检查配置文件并按严重/错误/警示/提示分级输出，同时支持读取 stats.json 列出体积最大的模块。适用于前端研发与 CI/CD 效能优化。
license: Apache-2.0
author: 刘天宝｜墨燊
category: dev-programming
subCategories:
  - dev-code-quality
icon: icon.svg
tags: [Webpack, 构建提速, 持久化缓存, thread-loader, tree shaking, 代码分割, SMP, stats.json, 前端工程化, CI构建优化]
language: zh-CN
visibility: public
---

# Webpack 构建耗时分析与提速（webpack-build-speedup）

**没测量就改配置，等于用猜测换风险。**

这个技能做三件事：**先测出耗时分布** → **按收益顺序改** → **避开那些「看起来会变快」的坑**。

---

## 硬边界（先看这条）

| 能做 | 不能做 |
|---|---|
| 读取 SMP / stats.json 给出耗时归属 | ❌ 预测你项目的具体加速倍数（依赖模块规模与机型） |
| 静态检查 webpack 配置的高风险写法 | ❌ 直接修改 CI 流水线或生产配置 |
| 指出 tree shaking / 分包为什么没生效 | ❌ 保证改完构建产物行为完全一致 |
| 给出 devtool、缓存、并行的取舍 | ❌ 承担 CDN 外置、sideEffects 误配引入的运行时风险 |

**以下情况必须停下来先做人工确认：**
- 准备把核心框架（`react` / `vue`）外置到外部 CDN → 需评估可用性与 SRI
- 准备写 `"sideEffects": false` → 必须先确认有没有全局副作用模块
- 准备在生产关掉 source map → 确认线上报错是否能定位

---

## 一、什么时候用这个技能

| 用户这样说 | 就用 |
|---|---|
| "构建太慢了，怎么优化" | ✅ |
| "怎么知道时间花在哪" | ✅ |
| "include / exclude 该怎么配" | ✅ |
| "持久化缓存为什么没效果" | ✅ |
| "thread-loader 要不要用" | ✅ |
| "为什么 tree shaking 没删掉代码" | ✅ |
| "splitChunks 配了为什么没分包" | ✅ |
| "生产 sourcemap 太慢怎么办" | ✅ |
| "怎么把 moment 的语言包去掉" | ✅ |
| "直接帮我把 CI 流水线改了吧" | ❌ 出方案，由 owner 评审 |

---

## 二、完整工作流

```
第 1 步  读规则文件 rules/build_analysis.md
第 2 步  测量：装 speed-measure-webpack-plugin，跑一次记录基线
         MEASURE=1 webpack
         同时出一份 stats.json 留作 CI 基线：webpack --profile --json > stats.json
第 3 步  静态体检配置
         python scripts/webpack_config_check.py --file webpack.config.js
第 4 步  看体积大户
         python scripts/webpack_config_check.py --stats stats.json --top 20
第 5 步  按收益顺序改：loader 范围 → 持久化缓存 → 并行/换工具链 → resolve → devtool → 分包
第 6 步  每改一项重测一次，记录 SMP 输出对比（一次只改一项）
第 7 步  固化：CI 挂 cacheDirectory + 构建耗时超阈值告警
```

---

## 三、先测量：两个必装工具

```js
const SpeedMeasurePlugin = require('speed-measure-webpack-plugin');
const smp = new SpeedMeasurePlugin({ disable: !process.env.MEASURE });
module.exports = smp.wrap({ mode: 'production', /* 原配置 */ });
```

**SMP 输出读法（重点）：**

```
 SMP  ⏱  Loaders
 babel-loader took 8.21 secs
   module count = 1543          ← 这个数字才是问题所在
```

`module count` 说明有多少模块过了这个 loader。**1500 个模块意味着 loader 范围没收窄**（很可能把 `node_modules` 也扫了），或者有巨型第三方库被打进来。

```bash
webpack --profile --json > stats.json   # 原生统计，不影响构建，适合进 CI
webpack-bundle-analyzer stats.json      # 看体积分布
```

时间基准要分开记：**冷构建**（CI 无 cache，最坏值）与**二次构建**（有 filesystem cache）。别拿 dev 的增量编译时间当优化目标，波动太大。

---

## 四、提速手段：按收益排序

| # | 手段 | 典型收益 | 风险 |
|---|---|---|---|
| 1 | **缩小 loader 范围**（`include` / `exclude`） | 常有 2-5 倍 | 无 |
| 2 | **持久化缓存**（`cache.type: filesystem`） | 二次构建 50-80% | 有三个常见失效坑 |
| 3 | **`thread-loader` / `parallelism`** | 大模块量 30-50% | 小项目反而更慢 |
| 4 | **换工具链**（swc / esbuild-loader） | 常 3-10 倍 | 兼容性需验证 |
| 5 | **减少解析**（`resolve` 精简） | 中 | alias 配错会找不到模块 |
| 6 | **分包与 tree shaking** | 减小体积间接提速 | 需 `sideEffects` 配合 |
| 7 | **`externals` + CDN** | 中（超大第三方库） | 引入运行时依赖 |
| 8 | **`devtool` 降级** | dev 明显 | 调试体验下降 |

### 1. loader 范围（第一优先级，最容易被忽略的一行）

```js
// 错误：对整个项目含 node_modules 全跑一遍
{ test: /\.js$/, use: ['babel-loader'] }

// 正确
{
  test: /\.jsx?$/,
  include: path.resolve(__dirname, 'src'),
  exclude: /node_modules/,
  use: ['babel-loader'],
}
```

顺带一提：`ts-loader` 加 `transpileOnly: true`，把类型检查挪给 `fork-ts-checker-webpack-plugin` 并行跑，通常能省一半时间。

### 2. 持久化缓存

```js
cache: {
  type: 'filesystem',
  cacheDirectory: path.resolve(__dirname, '.cache/webpack'),
  buildDependencies: { config: [__filename] },   // 不写会导致改了配置不生效
}
```

三个坑：**CI 没挂载缓存目录**（每次冷启动）、**`buildDependencies` 没配**（改了不生效，排查成本极高）、**容器镜像重建导致全量失效**（先 `rm -rf .cache/webpack` 验证）。

### 3. 并行化

小项目（模块数 < 500）别用 `thread-loader`，worker 启动开销会盖过收益。dev 模式还要留意 `poolRespawn`。更划算的路线是直接把 `babel-loader` 换成 `esbuild-loader` / `swc-loader`。

### 4. tree shaking 生效三条件

1. 必须是 **ESM 语法**（`babel-loader` 的 `modules: false`、TS 的 `"module": "esnext"`）
2. `package.json` 声明 `"sideEffects": false`
3. `mode: 'production'`

> 有副作用的模块（polyfill、全局样式 import）盲目标 false，会造成「删了不该删的」事故。

### 5. splitChunks 最常见的坑

```js
splitChunks: {
  chunks: 'all',        // 默认是 'async'，不改的话同步 chunk 根本不拆
  runtimeChunk: 'single',
}
```

---

## 五、脚本用法

```bash
python scripts/webpack_config_check.py --selftest
python scripts/webpack_config_check.py --file webpack.config.js
python scripts/webpack_config_check.py --stats stats.json --top 20
```

| 参数 | 说明 |
|---|---|
| `--file` | `webpack.config.js` 文本（也支持 `.prod.js` 之类） |
| `--stats` | `webpack --profile --json` 产出的 stats.json，进入体积分析模式 |
| `--top` | 体积分析模式下输出的模块数，默认 20 |
| `--prod` | 声明这是生产配置，用于 devtool 与 mode 的判定 |
| `--json` / `--out` | JSON 输出 / 指定输出文件 |
| `--selftest` | 跑内置自检 |

**配置体检覆盖：**
- 严重：`mode` 未设为 production（生产配置）；`cache.type` 未启用 filesystem
- 错误：`rules` 里的 loader 既没有 `include` 也没有 `exclude`；`TerserPlugin` 未开 `parallel`；`cache.buildDependencies` 缺失
- 警示：`resolve.extensions` 项过多或含 `.vue` 之类未使用后缀；`devtool` 用了 `eval-source-map` / `inline-source-map`；缺少 `splitChunks` 或 `chunks` 非 `all`；生产环境 devtool 用了 `eval*`
- 提示：未配 `thread-loader`；`ts-loader` 未开 `transpileOnly`；未配 `IgnorePlugin` 而项目里有 `moment`；未配 `externals`

**stats.json 模式：** 列出体积最大的 N 个模块，并按 `node_modules` 占比给出提示（如命中 `moment/locale`、`lodash`、`echarts` 等已知大户会单独标注）。

> 静态检查看的是**配置本身**，真实耗时必须以 SMP 输出与 CI 基线为准。

---

## 六、人工确认清单（这步不能省）

- [ ] 有冷构建与二次构建**两份**基线数据
- [ ] 每次只改一项，改完立刻重测并留记录
- [ ] CI 的 `cacheDirectory` 已做持久化挂载
- [ ] `cache.buildDependencies` 声明了 webpack 配置文件
- [ ] `sideEffects` 修改前确认过没有全局副作用模块
- [ ] `externals` 的依赖在 HTML 里有确定的加载来源（含 SRI）
- [ ] 生产构建产物做过一次**功能验证**，不只是「构建成功」

---

## 七、最常见的坑

**坑一：没测就开始改。**
优化前必须有一份 SMP 基线。否则你无法判断「加了 thread-loader」到底是快了 40% 还是慢了 10%。

**坑二：`rules` 里没写 `exclude: /node_modules/`。**
这是收益最大、成本最低的一行。很多项目 `module count` 上千，就是因为这一行没写。

**坑三：配了 filesystem cache 却没效果。**
三个原因：CI 没挂载缓存目录；`buildDependencies` 没配导致改了配置也不失效（其实是更危险）；容器镜像重建把绝对路径和时间戳全换了。**先 `rm -rf .cache/webpack` 冷跑一次对比。**

**坑四：小项目上 thread-loader。**
模块数不到 500 时，worker 池的启动与进程通信开销会盖过并行收益，**实测会更慢**。

**坑五：`splitChunks` 没改 `chunks: 'all'`。**
默认是 `async`，只对动态 import 生效。所以同步引入的第三方库永远不会被拆出来，「配了没效果」基本是这个原因。

**坑六：tree shaking 没删代码，怀疑 webpack 有问题。**
先看三个条件：有没有被编译成 CJS（babel `modules: false` 了吗）、有没有声明 `sideEffects`、`mode` 是不是 production。三个缺一就不摇。

**坑七：`sideEffects: false` 一把梭。**
polyfill、全局 CSS import、带副作用注册的模块被误删，构建成功但线上报错。**应该只对确定无副作用的子目录声明，或用数组列出例外文件。**

**坑八：`devtool: 'eval-source-map'` 用在生产。**
每个模块都内联完整 sourcemap，产物体积暴涨，浏览器解析也慢。生产用 `source-map` 或 `hidden-source-map` 就够了；开发用 `eval-cheap-module-source-map`。

**坑九：把 moment 的几百个语言包全打进去。**
moment 默认打包所有 locale。用 `IgnorePlugin` 干掉，或直接换 `dayjs`。这一项常常就是几 MB。

**坑十：只看构建时间，不看产物体积。**
有时「构建变快了」是因为少抽了 sourcemap 或少做了压缩，代价转嫁给了用户。**每次优化都要同时记录耗时与产物体积两个指标。**

---

## 八、边界与免责

- 本技能给出的是**静态配置检查与通用提速路径**，不构成对具体项目加速倍数的承诺
- 实际收益高度依赖模块规模、依赖树、CPU 核数、磁盘 IO 与 CI 环境，**以 SMP 与 CI 基线实测为准**
- webpack 4 与 webpack 5 在缓存、资源模块、默认行为上差异很大，**操作前确认版本**
- 生产构建配置的修改、`externals` 引入 CDN、`sideEffects` 声明均属高风险变更，**必须由 owner 评审并做产物验证**

---

## 九、许可

本技能由 **刘天宝｜墨燊** 原创，采用 **Apache License 2.0**。

`rules/build_analysis.md` 中的配置项与收益区间基于 webpack 官方文档与常见工程实践整理，不同版本存在行为差异，请以官方文档与实测为准。
