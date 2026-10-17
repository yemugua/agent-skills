# Webpack 构建耗时分析与提速 · 能力概览

## 你会得到什么

**强制先看数据**。给出 speed-measure-webpack-plugin 的接入方式（`disable: !process.env.MEASURE` 让测量不污染日常构建）和 SMP 输出的读法：真正要盯的是 Loaders 段里的 `module count`——1500 个模块跑 babel 就说明 loader 范围没收窄或有巨型第三方库被打进来。同时给 `--profile --json` 出 stats.json 的原生方式（适合进 CI 做基线），并明确「冷构建」与「二次构建」必须分开记录，dev 增量编译时间波动太大不能当优化目标。

**九类提速手段按收益排了优先级**（每项都标注典型收益与风险）：exclude node_modules 缩小 loader 范围常有 2-5 倍；filesystem cache 让二次构建省 50-80%；thread-loader 在大模块量时 30-50% 但模块数小于 500 反而更慢；swc / esbuild-loader 替代 babel 常有三到十倍收益；resolve 精简减少文件探测；tree shaking 与分包减小体积间接提速；externals + CDN 适合超大且稳定的第三方库；devtool 降级影响调试体验。另外单独提示 `ts-loader` 的 `transpileOnly: true` 把类型检查挪给 fork-ts-checker 并行跑，通常省一半以上时间。

**持久化缓存的三个坑讲透**：CI 没挂载缓存目录导致每次冷启动、`buildDependencies` 没配导致改了配置不生效（这个最危险，表现为「改了没变化」）、容器镜像重建把绝对路径和时间戳全换了导致全量失效。给出配置文件失效排查的标准动作：`rm -rf .cache/webpack` 冷跑对比。

**tree shaking 三条件与 splitChunks 的经典坑**。tree shaking 要生效必须同时满足 ESM 语法（babel `modules: false`、TS `module: esnext`）、`sideEffects: false`、`mode: production`，缺一不可；同时警告「有副作用的模块盲目标 false 会删掉不该删的东西」。splitChunks 默认是 `chunks: 'async'`，不改就不会拆同步 chunk，这是「配了没效果」的头号原因。

**脚本**：`scripts/webpack_config_check.py` 两种模式。配置体检模式检查 `mode` 是否 production、`cache.type` 是否 filesystem、loader 是否缺 `include`/`exclude`、`cache.buildDependencies` 是否缺失、`TerserPlugin` 是否开 `parallel`、`resolve.extensions` 是否过长、`devtool` 是否用了 `eval-source-map`/`inline-source-map`、`splitChunks` 是否缺或 `chunks` 非 `all`、`thread-loader` 与 `transpileOnly` 是否缺失、是否引入 moment 却没配 `IgnorePlugin`，按严重/错误/警示/提示四级输出。stats.json 模式列出体积最大的 N 个模块，并按 node_modules 占比给出提示。

## 典型用法

1. 构建变慢：先跑 SMP 拿基线，再跑配置体检，按严重度从高到低改。
2. tree shaking / splitChunks 没效果：直接对照三条件与 `chunks: all` 排查。
3. CI 提速：重点看 cacheDirectory 持久化挂载与 buildDependencies 声明。
4. 产物体积异常：用 `--stats stats.json --top 20` 找出体积大户。

## 边界

- 静态检查看的是配置本身，实际收益依赖模块规模、机型、磁盘 IO 与 CI 环境
- webpack 4 与 webpack 5 在缓存、资源模块、默认行为上差异很大
- externals 引入 CDN、sideEffects 声明、生产配置修改均属高风险变更，需 owner 评审
- 任何优化都要同时记录耗时与产物体积，防止「构建变快但体积变大」
