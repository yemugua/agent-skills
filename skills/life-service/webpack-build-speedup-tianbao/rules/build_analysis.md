# Webpack 构建耗时分析与提速 · 核心规则库

> **一切提速的前提是先测。** 没数据就改配置，等于用猜测换风险。
> 本文件给出：怎么测 → 按什么顺序改 → 哪些改动是坑。

---

## 一、先测量：拿到耗时分布

### 1. speed-measure-webpack-plugin（最常用）

```js
// webpack.config.js
const SpeedMeasurePlugin = require('speed-measure-webpack-plugin');
const smp = new SpeedMeasurePlugin({ disable: !process.env.MEASURE });

module.exports = smp.wrap({
  mode: 'production',
  // 原有配置
});
```

```json
// package.json
{ "scripts": { "build": "webpack", "measure": "MEASURE=1 webpack" } }
```

输出形如：

```
 SMP  ⏱
 General output time took 12.34 secs

 SMP  ⏱  Loaders
 babel-loader, and vue-loader took 8.21 secs
   module count = 1543
 css-loader, and vue-style-loader took 3.4 secs
   module count = 210

 SMP  ⏱  Plugins
 TerserPlugin took 4.1 secs
```

**读法：** 先看 Loaders 段的 module count。1500 个模块跑 babel，说明 loader 范围没收窄，或该用 `thread-loader` 了。

### 2. 原生 stats（不影响构建，可进 CI）

```bash
webpack --profile --json > stats.json
```

用 `webpack-bundle-analyzer stats.json` 看体积；也可以自己读 `modules[].size`。

```js
// 快速找出体积最大的 20 个模块
const stats = require('./stats.json');
stats.modules
  .filter(m => m.size > 0)
  .sort((a, b) => b.size - a.size)
  .slice(0, 20)
  .forEach(m => console.log((m.size / 1024).toFixed(1) + ' KB', m.name));
```

### 3. 时间基准怎么定

```
冷构建（CI 环境，无 cache）：这是最坏值，也是必须优化的目标
二次构建（有 filesystem cache）：看缓存命中带来的收益
devServer 冷启动与增量编译（HMR）：开发体验瓶颈通常在这
```

**不要用 dev 的增量编译时间当作优化目标**，它跟你改的文件有关，波动很大。

---

## 二、提速手段（按收益从大到小）

| # | 手段 | 典型收益 | 风险 |
|---|---|---|---|
| 1 | **缩小 loader 作用范围**（`include`/`exclude`） | 大，常有 2-5 倍 | 无 |
| 2 | **持久化缓存**（`cache.type = filesystem`） | 二次构建 50-80% | 缓存失效要排查 |
| 3 | **`thread-loader` / `parallelism`** | 大模块量时 30-50% | 小项目反而更慢 |
| 4 | **升级工具链**（swc / esbuild-loader 替代 babel/ts-loader） | 常有 3-10 倍 | 兼容性需验证 |
| 5 | **减少解析**（`resolve.extensions` / `alias` / `modules`） | 中 | 别名配错会找不到模块 |
| 6 | **代码分割与 tree shaking** | 减小体积，间接提速 | 需 `sideEffects` 配合 |
| 7 | **`externals` + CDN** | 中（对超大第三方库） | 引入运行时依赖风险 |
| 8 | **`devtool` 降级** | dev 明显 | 调试体验下降 |
| 9 | **`IgnorePlugin` / `ContextReplacementPlugin`** 干掉无用资源 | 视情况 | 配错会缺文件 |

---

## 三、收窄 loader 范围（第一优先级）

```js
// 错误：对整个项目（含 node_modules）跑一遍
module: {
  rules: [
    { test: /\.js$/, use: ['babel-loader'] },
  ],
}

// 正确：只处理自己的源码，且排除 node_modules
module: {
  rules: [
    {
      test: /\.jsx?$/,
      include: path.resolve(__dirname, 'src'),
      exclude: /node_modules/,
      use: ['babel-loader'],
    },
  ],
}
```

`exclude: /node_modules/` 是最容易被忽略、收益最大的一行。

**再细一层**：对每个 loader 单独声明范围，不要一个 `rules` 覆盖所有东西。

```js
{
  test: /\.tsx?$/,
  include: [path.resolve(__dirname, 'src'), path.resolve(__dirname, 'packages')],
  use: [{ loader: 'ts-loader', options: { transpileOnly: true } }],  // 关掉类型检查，交给 fork-ts-checker
}
```

> `transpileOnly: true` 让 ts-loader 只做转译不做类型检查（类型检查挪到 `fork-ts-checker-webpack-plugin` 并行跑），通常能省一半以上时间。

---

## 四、持久化缓存（第二优先级）

```js
// webpack 5
module.exports = {
  cache: {
    type: 'filesystem',
    cacheDirectory: path.resolve(__dirname, '.cache/webpack'),
    buildDependencies: {
      // 配置或 loader 变了就失效，必须声明
      config: [__filename],
    },
    compression: 'gzip',   // webpack 5 可选 false 换取更快的读写
  },
};
```

| 项 | 说明 |
|---|---|
| `cache.type: 'filesystem'` | webpack 5 默认只在 dev 开启 memory，**生产构建要显式开** |
| `buildDependencies.config` | 不写的话改了 webpack 配置不会失效，出现「改了没生效」的诡异现象 |
| `cacheDirectory` | CI 必须把这个目录做成持久化 volume，否则每次都是冷缓存 |
| `cache.name` | monorepo 多配置打包时建议给不同名字，避免互相覆盖 |
| babel-loader | 配 `cacheDirectory: true`（默认在 `node_modules/.cache/babel-loader`） |

**持久化缓存的三个坑：**

1. **CI 里缓存目录没挂载** → 每次都是冷构建，测出来「加了 cache 没效果」
2. **`buildDependencies` 没配** → 改 loader 配置后构建结果不更新，排查成本极高
3. **缓存依赖时间戳与绝对路径** → 容器镜像重建会导致全部失效；遇到「缓存加了没效果」先 `rm -rf .cache/webpack` 再验证

webpack 4 时代用 `cache-loader` / `hard-source-webpack-plugin`，webpack 5 直接用内置的。

---

## 五、并行化

```js
// 多核并行
module.exports = {
  parallelism: os.cpus().length - 1,
};

// thread-loader：给昂贵的 loader 配线程池
{
  test: /\.jsx?$/,
  include: path.resolve(__dirname, 'src'),
  use: [
    {
      loader: 'thread-loader',
      options: {
        workers: require('os').cpus().length - 1,
        poolRespawn: false,   // dev 下关掉，避免热更新时反复重建 worker
      },
    },
    'babel-loader',
  ],
}
```

**什么时候不该用 thread-loader：**
- 小项目（模块数 < 500）→ worker 启动开销盖过收益，**反而更慢**
- 单个大模块被单独处理时，线程帮不上忙
- dev 模式建议 `poolRespawn: false` 之外还要评估，因为每次保存都在搬 worker

替代方案（更快）：把 `babel-loader` 换成 `swc-loader` 或 `esbuild-loader`。

```js
{
  test: /\.m?js$/,
  use: [{ loader: 'esbuild-loader', options: { target: 'es2015' } }],
}
```

---

## 六、减少解析成本

```js
resolve: {
  extensions: ['.js', '.jsx', '.json'],   // 别写一堆，越少越好
  modules: [path.resolve(__dirname, 'src'), 'node_modules'],  // 绝对路径避免逐层向上找
  alias: {
    '@': path.resolve(__dirname, 'src'),
    react: path.resolve(__dirname, 'node_modules/react'),     // 锁定单实例
  },
  symlinks: false,        // 不用 npm link / monorepo 软链时，关掉可提速
  cacheWithContext: false,
}
```

| 配置 | 说明 |
|---|---|
| `extensions` | 每一项都会触发额外的文件探测，别贪多 |
| `modules` | 默认 `['node_modules']` 会逐层向上找；给绝对路径可省大量 IO |
| `alias` | 除了简化写法，还能避免同一依赖被解析出多个副本 |
| `module.noParse` | 对不依赖 import 的大库（如压缩后的 lodash）跳过解析：`noParse: /lodash|jquery/` |
| `module.rules[].oneOf` | 用 oneOf 让每个文件只匹配第一条规则，短路后续判断 |

---

## 七、devtool 与 source map

| devtool | 速度 | 适用 |
|---|---|---|
| `eval` | 最快 | 快速迭代，但报错定位到转译后的文件 |
| `eval-cheap-module-source-map` | 快 | **开发环境推荐** |
| `source-map` | 慢 | 生产完整的 sourcemap（CI 构建慢点可接受） |
| `hidden-source-map` | 慢 | 生产，不暴露给浏览器但可给监控平台 |
| `cheap-source-map` | 较快 | 不保留列信息 |

```js
module.exports = {
  devtool: isProd ? 'source-map' : 'eval-cheap-module-source-map',
};
```

> 不要用 `inline-source-map` 或 `eval-source-map`：它们要么让 bundle 体积暴涨（影响解析速度），要么每次重建都重算完整 sourcemap。

---

## 八、分包与 tree shaking

```js
optimization: {
  splitChunks: {
    chunks: 'all',            // 默认 'async'，改成 all 才会拆分同步 chunk
    cacheGroups: {
      vendors: {
        test: /[\\/]node_modules[\\/]/,
        name: 'vendors',
        priority: 10,
        reuseExistingChunk: true,
      },
      common: {
        minChunks: 2,
        name: 'common',
        priority: 5,
      },
    },
  },
  runtimeChunk: 'single',     // 抽出 runtime，利于长期缓存
  moduleIds: 'deterministic', // contenthash 稳定
  usedExports: true,          // 标记未使用导出
  minimize: true,
  minimizer: [new TerserPlugin({ parallel: true })],
}
```

**tree shaking 生效的三个条件：**

1. 用 **ESM 语法**（`import/export`），不要编译成 CJS（`babel-loader` 的 `modules: false`，TS 的 `"module": "esnext"`）
2. `package.json` 声明 `"sideEffects": false`（或对指定文件数组），否则 webpack 不敢删
3. `mode: 'production'`（自动开启 `usedExports` 与 terser 的去除死代码）

```json
{ "name": "my-lib", "sideEffects": false }
```

> 有副作用的模块别盲目标 false（比如 polyfill、全局样式 import），会造成「删了不该删的」事故。

---

## 九、externals 与 CDN

```js
externals: {
  react: 'React',
  'react-dom': 'ReactDOM',
  lodash: '_',
},
// html-webpack-plugin 里再注入对应的 CDN script（注意 integrity 与 SRI）
```

适用：超大且几乎不变的第三方库。**代价**是引入运行时依赖与 CDN 风险，**不要为了追求几秒的构建收益把核心框架外置到不可控的 CDN**。

---

## 十、处理第三方库的常见陷阱

| 现象 | 手段 |
|---|---|
| moment / dayjs 把上百种语言都打进去 | `new webpack.IgnorePlugin({ resourceRegExp: /^\.\/locale$/, contextRegExp: /moment$/ })` 或 `ContextReplacementPlugin` |
| antd / element 全量引入 | `babel-plugin-import` 按需加载 |
| lodash 整包引入 | 用 `lodash-es` 或 `lodash/get` 子路径 |
| 超大的静态资源反复处理 | `asset/resource` + CDN，别让 loader 逐字节过一遍 |

---

## 十一、CI 构建 Checklist

- [ ] `cacheDirectory` 做了持久化挂载
- [ ] `[cache] type: filesystem` 已开启且 `buildDependencies` 声明了配置文件
- [ ] CI 用的是 `--profile` 产出 stats，能回溯历史耗时
- [ ] 有「构建耗时超阈值就失败」的守卫
- [ ] 生产构建的 `devtool` 与 `minimize` 配置明确，不依赖默认值
