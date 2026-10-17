# React 重渲染定位与优化 · 能力概览

## 你会得到什么

**先量化再优化的强制顺序**。多数人一上来就加 memo，而正确顺序是：Profiler 录制 → 勾选 `Record why each component rendered` → 看 Ranked 面板找最贵的子树 → why-did-you-render 确认到底哪个 prop 变了 → 才动手改。附一条重要提醒：**dev 构建慢 2-5 倍，性能结论必须用生产构建复核**。

**四个触发源与两条被记反的规律**。触发源是自身 state 变化、父组件重渲染、Context value 引用变化、Hook 内部 state 变化。两条关键是：默认情况下**父组件渲染子节点无条件跟着渲染**（props 没变也渲染）；**Context 的变化不受中间层 memo 保护**（只有拆 Context 或选择器订阅能解决）。

**memo / useMemo / useCallback 的作用域讲清楚**。`useMemo` 只缓存计算结果不减少渲染，`useCallback` 只稳定函数引用不减少渲染，`React.memo` 只在 props 引用稳定时才拦得住。给出 memo 的三个失效场景：传了每次新建的引用（`data={{}}`、`fn={() => {}}`、`items={arr.filter()}`）、传了 children、以及组件本身就极轻。同时点出 `useCallback` 只在「传给 memo 子组件」和「作为其它 Hook 的 deps」两种情况才需要，其余写内联函数更可读；以及它的闭包陷阱——`useCallback(() => fetch({ q: filters }), [])` 永远用旧值，附 ref 兜底写法。

**key 的四种写法后果表**。`key={index}` 导致列表顺序变化时组件 state 串位，`key={Math.random()}` 导致整棵子树每次卸载重建，同时说明 `<Form key={userId} />` 这种刻意重建是合法用法。

**Context 全树重渲染四个解法**：按更新频率拆 Context、状态下沉到最小公共祖先、children 提升让重型子树引用稳定、`useSelector` / `useSyncExternalStore` 做选择器订阅。

**脚本**：`scripts/react_rerender_scan.py` 支持单文件与目录递归（跳过 `node_modules`/`build`/`dist`），扫描九类风险点并分级：`key={Math.random()}` 与内联对象 props 判严重；map 里用 index 做 key、`Provider value={{` 内联对象、`.map(` 渲染的列表项未 memo 判错误；渲染期非纯计算（`new Date()`、`Date.now()`、`JSON.parse` 直接进 JSX）、组件函数体内定义组件判警示；内联箭头函数传给疑似 memo 组件、空依赖数组的 Hook 闭包引用外部变量判提示。

## 典型用法

1. 页面卡：Profiler 录制找最贵子树，同时跑脚本把明显的高风险点先列出来。
2. 加了 memo 没效果：跑脚本看是不是有内联对象/函数 prop，或 children 传参。
3. 列表状态串位：直接查 index key 规则是否命中。
4. 上线前体检：`--dir src --json` 出结构化结果，接进 CI 做增量检查。

## 边界

- 静态扫描是模式匹配，对运行时动态组件、高阶组件、编译后代码有漏报误报
- 为什么重渲染必须用 Profiler 与 why-did-you-render 在运行时确认
- 基于 React 16.8+ Hooks 语义，React 18 并发特性会改变部分表现
- Context 拆分与状态提升属结构性变更，需要 owner 评审并补回归测试
