---
name: react-rerender-optimize
slug: react-rerender-optimize-tianbao
displayName: React 重渲染定位与优化
display_name: "React 重渲染定位与优化"
display_name_en: "React Re-render Diagnosis and Optimization"
version: "1.0.0"
summary: 先量化再优化：Profiler 的 Flamegraph 与 Ranked 面板配合 Record why each component rendered 定位到具体那棵子树、why-did-you-render 直接报出哪个 prop 从什么值变成什么值；讲清四个触发源（自身 state、父<｜hy_place▁holder▁no▁813｜>渲染、Context value 引用变化、Hook 内部 state）以及「父渲染子必渲染」「memo 挡不住 Context」两条最容易误解的规律；memo/useMemo/useCallback 逐个给出适用与无效场景（useCallback 只在传给 memo 子组件或作为 deps 时才有用、useMemo 不减少渲染只缓存计算、children 会让 memo 失效）；key 用 index 导致列表状态串位、key 用 Math.random 导致全树重建；Context 全树重渲染的四种解法（拆 Context、状态下沉、children 提升、useSelector 选择器订阅），每条规则配错误写法与正确写法对照，配脚本静态扫描 JSX 中的重渲染风险点。
description: 页面卡、输入延迟、列表滚动掉帧、加了 memo 却完全没效果、不知道该不该用 useCallback、切换 tab 时表单状态串了、输入框每敲一个字整棵树都在重渲染时使用。当用户说"为什么卡""这个组件为什么一直在渲染""memo 为什么没用""要不要包 useMemo""useCallback 什么时候需要""Context 更新为什么全树都渲染""列表 key 用 index 会怎样""怎么找出真正在重渲染的组件"时使用。内置重渲染四触发源表、Profiler 真实耗时读法与 dev 构建慢 2-5 倍的坑、why-did-you-render 接入方式、浅比较与引用相等判定表、memo 有效与无效的六种场景、useMemo 该用与不该用的对照、useCallback 的闭包陷阱与 ref 兜底、key 的四种写法后果表、Context 广播四条规律与四个解法、状态提升到最小公共祖先的准则，配 scripts/react_rerender_scan.py 扫描源码中的内联对象 props、箭头函数传给 memo 组件、key 用索引、Provider value 内联对象、组件内定义组件、渲染期非纯计算等风险点。适用于前端研发与性能专项优化。
license: Apache-2.0
author: 刘天宝｜墨燊
category: dev-programming
subCategories:
  - dev-frontend
icon: icon.svg
tags: [React, 重渲染, React.memo, useMemo, useCallback, Context, Profiler, key串联, 前端性能优化, 渲染性能]
language: zh-CN
visibility: public
---

# React 重渲染定位与优化（react-rerender-optimize）

**90% 的 React 卡顿不是渲染慢，是重渲染的范围没控住。**

这个技能做三件事：**先量化** → **再定位** → **最后才优化**。

---

## 硬边界（先看这条）

| 能做 | 不能做 |
|---|---|
| 判断重渲染范围与触发原因 | ❌ 替代真实性能采样（必须用 Profiler 实测） |
| 指出 memo/useMemo/useCallback 的有效与无效场景 | ❌ 保证加完之后一定变快 |
| 静态扫描源码中的高风险写法 | ❌ 理解运行时动态拼接、高阶组件、AST 变换后的结构 |
| 给出 Context / key / 状态提升的结构性改法 | ❌ 直接替你拆分组件树（属结构变更，需 owner 评审） |

**以下情况必须停下来先做人工确认：**
- **没跑 Profiler 就说哪里慢** → 先录制再谈优化，凭直觉优化几乎必错
- 还想用 `shouldComponentUpdate` 手工比较深层对象 → 先想能不能改成扁平 props
- 涉及 `useContext` 的全局重构 → 属于结构变更，需要 owner 评审

---

## 一、什么时候用这个技能

| 用户这样说 | 就用 |
|---|---|
| "这个组件为什么一直渲染" | ✅ |
| "加了 memo 为什么没效果" | ✅ |
| "要不要给这个函数包 useCallback" | ✅ |
| "Context 一更新整棵树都在渲染" | ✅ |
| "列表里输入框内容串位了" | ✅ |
| "输入一个字整页卡一下" | ✅ |
| "怎么找出真正在重渲染的组件" | ✅ |
| "帮我直接把所有组件都加 memo" | ❌ 先定位 |

---

## 二、完整工作流

```
第 1 步  读规则文件 rules/rerender_diagnosis.md 与 rules/optimize_patterns.md
第 2 步  量化：DevTools Profiler 录制，勾选
         Settings → Profiler → Record why each component rendered
         看 Ranked 面板找最贵的子树（注意：dev 构建慢 2-5 倍，要用生产构建复核）
第 3 步  静态摸底
         python scripts/react_rerender_scan.py --dir src --json
第 4 步  按输出的 严重/警示/提示 逐条改
第 5 步  改完再录一次 Profiler，对比 actualDuration
第 6 步  仍需细化时用 why-did-you-render 拿到「哪个 prop 变了」
```

---

## 三、四个触发源（决定了排查方向）

| 触发源 | 影响范围 |
|---|---|
| 组件自身 state 变化 | 该组件及其所有后代（除非被 memo 挡住） |
| 父组件重渲染 | **props 变没变都会重渲染**（无 memo 时） |
| Context value 引用变化 | 所有消费者，**中间层加 memo 也没用** |
| Hook 内部 state 变化 | 使用该 Hook 的每个组件各自重渲染（Hook 不共享 state） |

**两条最容易被记反的：**

1. **父组件重渲染，子节点无条件跟着重渲染。** props 没变也照渲染。
2. **Context 的变化不受中间层 memo 保护。** 只有拆 Context 或选择器订阅能解决。

---

## 四、memo / useMemo / useCallback：别乱加

| 手段 | 真实作用 | 什么时候有用 |
|---|---|---|
| `React.memo` | 阻断「父渲染导致子渲染」 | props 稳定且子组件渲染贵的时候 |
| `useMemo` | **只缓存计算结果**，不减少渲染 | 昂贵计算 / 稳定对象引用 |
| `useCallback` | **只稳定函数引用**，不减少渲染 | 传给 memo 子组件 / 作为其它 Hook 的 deps |

**memo 的三个失效场景：**

```jsx
// 1) 传了每次新建的引用
<Child data={{ a: 1 }} />                 // 新对象
<Child fn={() => handle()} />             // 新函数
<Child items={data.filter(x => x.ok)} />  // 新数组

// 2) 传了 children（children 每次都是新 element）
const Card = memo(({ children }) => <div>{children}</div>);

// 3) 组件太轻，浅比较成本还不如直接渲染
```

**useCallback 只在两种情况下需要**：传给 memo 子组件、作为其它 Hook 的依赖。其它场景写内联函数更可读。

```jsx
// 错误：memo 子组件 + 每次新函数 = memo 完全失效
<HeavyList onItemClick={(id) => console.log(id)} />

// 正确：引用稳定 + 子组件 memo，两者成对才有意义
const handleClick = useCallback((id) => { /* ... */ }, []);
<HeavyListMemo onItemClick={handleClick} />
```

完整的适用/场景对照表（含 `useMemo` 改原数组、`useCallback` 闭包捕获旧值的陷阱）在 `rules/optimize_patterns.md`。

---

## 五、key 的四种写法

| 写法 | 后果 |
|---|---|
| `key={index}` | 顺序变化时**组件 state 串位**（输入内容错位、选中态错位） |
| `key={item.id}` | 正确 |
| `key={Math.random()}` | 每次都是新 key，**整棵子树卸载重建** |
| 无 key | React 报警告，行为等同 index |

合法的特例：`<Form key={userId} />` **故意**用 key 让组件在切换用户时重建，这是刻意重置组件状态的常用手段——但要注意它会丢弃子树状态与 DOM，成本不低。

---

## 六、Context 全树重渲染：四个解法

```jsx
// 根因：value 每次都是新对象
<Ctx.Provider value={{ theme, toggle }}>        // ❌
const value = useMemo(() => ({ theme, toggle }), [theme, toggle]);  // ✅
```

按优先级：

1. **拆 Context**：按更新频率分，`UserContext` 与 `ThemeContext` 分开
2. **状态下沉**：state 放在「所有需要它的组件的最小公共祖先」，别习惯性提到 App 顶层
3. **children 提升**：`<Provider><ExpensiveTree /></Provider>`，`children` 引用稳定就不参与重建
4. **选择器订阅**：`useSelector` / `useSyncExternalStore`，只有用到的字段变了才渲染

---

## 七、脚本用法

```bash
python scripts/react_rerender_scan.py --selftest
python scripts/react_rerender_scan.py --file src/components/List.jsx
python scripts/react_rerender_scan.py --dir src --json
```

| 参数 | 说明 |
|---|---|
| `--file` | 单个 `.jsx` / `.js` / `.tsx` / `.ts` 文件 |
| `--dir` | 目录递归扫描（跳过 `node_modules`、`build`、`dist`） |
| `--json` / `--out` | JSON 输出 / 指定输出文件 |
| `--selftest` | 跑内置自检 |

**扫描的九类风险点（按严重度）：**

| 级别 | 规则 |
|---|---|
| 严重 | `key={Math.random()}` / `key={Date.now()}`；JSX 属性内联对象传给疑似组件（`<X prop={{`） |
| 错误 | `map` 里用 index/`i` 做 key；`Provider value={{` 内联对象；`.map(` 渲染的列表项组件未 memo |
| 警示 | 渲染期非纯计算（`new Date()`、`Date.now()`、`JSON.parse` 直接进 JSX 表达式）；组件函数体内定义组件；`<Component key={index}` |
| 提示 | 内联箭头函数传给疑似 memo 组件；`useCallback`/`useMemo` 依赖数组为空且闭包引用了外部变量；`<>` 在 map 里没带 key |

> 静态扫描只能发现**模式**，`为什么重渲染`必须用 Profiler / why-did-you-render 在运行时确认。

---

## 八、人工确认清单（这步不能省）

- [ ] 用 **生产构建**跑过 Profiler（dev 慢 2-5 倍，别拿 dev 数据下结论）
- [ ] 勾了 `Record why each component rendered`
- [ ] 确认过最贵的子树是**渲染**贵还是**渲染里的计算**贵
- [ ] 加 memo 前确认 props 引用是否稳定
- [ ] `useMemo` 的依赖数组包含了所有参与计算的变量
- [ ] `useCallback` 的闭包没有捕获过期 state/props
- [ ] 列表 key 用的是稳定 id，不是 index
- [ ] Context 的 value 用了 useMemo，或已按频率拆分
- [ ] 改完再用 Profiler 复核一遍，而不是「感觉快了」

---

## 九、最常见的坑

**坑一：没定位就到处加 memo。**
memo 用浅比较，本身就是成本；props 每次都是新引用的话，加了也白加，还让代码难读。**先用 Profiler 找出真正贵的子树。**

**坑二：以为 props 没变子组件就不渲染。**
默认行为是父渲染子必渲染。`<Child name="a" />` 里的 `name` 从头到尾没变，父组件 setState 一次它照样渲染一次。

**坑三：`useCallback` 包了一切。**
它的唯一作用是稳定引用。若子组件没有 `memo`，或它不是其它 Hook 的依赖，包了完全没用。**适用场景只有两个。**

**坑四：`useMemo` 的依赖数组写错。**
`useMemo(() => list.sort(...), [])` 有两个问题：永远返回第一次的结果，而且 `sort` 原地改了原数组。依赖数组必须包含所有参与计算的量。

**坑五：`useCallback` 闭包捕获旧值。**
`useCallback(() => fetch({ q: filters }), [])` 永远用最初的 `filters`。要么把 `filters` 写进依赖，要么用 ref 持有最新值。

**坑六：key 用 index。**
在带输入框的列表头部插入一项，输入内容会留在原来的位置而不是跟着数据走。**这是「看起来玄学、其实是 key 错了」的经典现象。**

**坑七：`Provider value={{ theme, toggle }}`。**
每次渲染都是新对象，所有消费者无条件重渲染，且中间层加 memo 完全没用。**必须 `useMemo`，或者按频率拆 Context。**

**坑八：在组件内部定义组件。**
```jsx
function Parent() {
  const Inner = () => <span>x</span>;   // 每次渲染都是新组件类型
  return <Inner />;
}
```
React 看到的是「旧的 Inner 卸载、新的 Inner 挂载」，子树状态全丢、性能极差。提到组件外。

**坑九：渲染期做非纯计算。**
`new Date()`、`Date.now()`、`Math.random()`、`JSON.parse(大字符串)` 放在渲染里，每次都是新值/新开销，memo 与引用比较全部失效。

**坑十：把所有 state 提到最顶层。**
一个搜索框的 `text` 提到 App，输入一个字就让 500 行的表格跟着重渲染。**state 应该放在最小公共祖先，不是最顶层。**

---

## 十、边界与免责

- 本技能基于 **React 16.8+ Hooks 语义**；React 18 的并发特性（`useDeferredValue`、`startTransition`、自动批处理）会改变部分性能表现，**请结合版本实测**
- 静态扫描是**模式匹配**，对运行时动态生成的组件、高阶组件、编译转换后的代码存在漏报与误报
- 性能优化结论必须以**生产构建下的 Profiler 数据**为准，dev 构建不具备参考价值
- 涉及 Context 拆分、状态提升重构属于结构性变更，**需要 owner 评审并补回归测试**

---

## 十一、许可

本技能由 **刘天宝｜墨燊** 原创，采用 **Apache License 2.0**。

`rules/` 中的优化模式基于 React 官方文档与社区实践整理，不同 React 版本行为存在差异，请以官方文档与实测为准。
