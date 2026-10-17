# React 重渲染触发条件与定位 · 核心规则库

> 优化之前先定位。**90% 的「React 卡顿」是重渲染范围没控制住，而不是渲染本身慢。**
> 本文件解决「到底是谁在重渲染、为什么重渲染」。

---

## 一、重渲染的四个触发源

| 触发源 | 说明 | 影响范围 |
|---|---|---|
| 组件自身 state 变化 | `setState` / `useState` 返回新值 | 该组件**及其所有后代**（除非后代被 memo 挡住） |
| 父组件重渲染 | props 引用变化 或 父就是重渲染了 | 同上，**与 props 是否变化无关**（无 memo 时） |
| Context 值变化 | `Provider` 的 `value` 引用变了 | 所有 `useContext` 的消费者，**无视中间层有没有 memo** |
| 自定义 Hook 内部 state 变化 | 使用该 Hook 的每个组件各自重渲染（Hook 不共享 state） |

**必须记住的一条**：默认情况下，**父组件重渲染，所有子节点无条件跟着重渲染**。props 没变也会重渲染，因为 React 只是重新执行了子组件函数。

```
setState(A)
  → A 重渲染
    → <B /> 重渲染（即使 props 完全没变）
      → <C /> 重渲染
        → ...整棵子树
```

---

## 二、判断是否真的有问题：先量化

不是所有重渲染都要管。**渲染 ≠ 提交 DOM。**

| 情况 | 要不要管 |
|---|---|
| 轻量叶子节点重渲染（几十个 div） | 不管，React 协调本身很快 |
| 渲染里有昂贵计算（大数组排序、JSON.parse、正则回溯） | 管：`useMemo` 或移出渲染 |
| 列表几百项整体重渲染 | 管：拆分 + `memo` |
| 每次输入都在重渲染整棵树 | 管：状态下沉 / Context 拆分 |
| 重渲染导致副作用重复执行 | 管：先看是不是 deps 写错 |

**量化方法：**

```js
// 1) 最土但最快：加计数
const renderCount = useRef(0);
renderCount.current++;
console.log('Header render', renderCount.current);

// 2) Profiler API 拿真实耗时
<Profiler id="Navigation" onRender={(id, phase, actualDuration) => {
  console.log(id, phase, actualDuration.toFixed(2), 'ms');
}}>
  <Navigation />
</Profiler>
```

`phase` 为 `mount` 或 `update`；`actualDuration` 是该子树本次渲染的实际耗时（生产构建下才准，**开发模式本身慢 2-5 倍**）。

---

## 三、定位工具

### 1. React DevTools Profiler

```
打开 Profiler 面板 → 勾选 Record why each component rendered
→ 点击交互 → Stop
→ 看 Flamegraph：灰色=没重渲染，彩色=重渲染（越黄/红越耗时）
→ 点某个组件看右侧 Why did this render
```

| 面板 | 用途 |
|---|---|
| Flamegraph | 看谁渲染了、耗时多少 |
| Ranked | 按耗时排序，直接找最贵的那棵子树 |
| Interactions | 把渲染归因到具体交互（输入第 3 个字符） |

**必勾选项**：设置 → Profiler → `Record why each component rendered while profiling`。

### 2. why-did-you-render

```js
// wdyr.js（必须在 import react 之前引入）
import React from 'react';
if (process.env.NODE_ENV === 'development') {
  const whyDidYouRender = require('@welldone-software/why-did-you-render');
  whyDidYouRender(React, {
    trackAllPureComponents: true,
    trackExtraHooks: [[require('react-redux/lib'), 'useSelector']],
  });
}
// 在入口文件第一行：import './wdyr';
```

```jsx
// 只盯某个组件
function HeavyList() { /* ... */ }
HeavyList.whyDidYouRender = true;
```

它会直接告诉你：**哪个 prop 变了、从什么值变成什么值、是不是引用变了但内容一样**。

### 3. highlight 重渲染（临时）

```jsx
function useHighlightOnUpdate(ref) {
  const old = useRef(0);
  old.current++;
  useEffect(() => {
    if (!ref.current) return;
    ref.current.style.transition = 'none';
    ref.current.style.outline = '3px solid red';
    const t = setTimeout(() => { if (ref.current) ref.current.style.outline = ''; }, 200);
    return () => clearTimeout(t);
  });
}
```

---

## 四、不可变数据与浅比较（理解 memo 的前提）

`React.memo` 默认是**浅比较**（`Object.is` 逐个 prop 比较）。

```js
const a = { list: [1, 2, 3] };
const b = { list: [1, 2, 3] };
a === b            // false —— 内容一样，引用不同
Object.is([], [])  // false
```

所以：

| 写法 | 是否导致 memo 失效 |
|---|---|
| `<Child data={{ a: 1 }} />` | ❌ 每次新对象 |
| `<Child fn={() => handle()} />` | ❌ 每次新函数 |
| `<Child items={data.filter(x => x.ok)} />` | ❌ 每次新数组 |
| `<Child style={{ color: 'red' }} />` | ❌ 每次新对象 |
| `<Child count={items.length} />` | ✅ 基本类型，稳定 |
| `<Child user={user} />`（user 来自 state） | ✅ 引用不变则稳定 |

**判断口诀：传给 memo 组件的 prop，只要它是「这次新造出来的」，memo 就白写了。**

---

## 五、常见错觉

| 错觉 | 真相 |
|---|---|
| 「props 没变子组件就不会重渲染」 | 错。没有 memo 时，父渲染子必渲染 |
| 「加了 memo 子组件就不渲染了」 | 错。只要有任意一个 prop 是每次新建的引用，memo 立即失效 |
| 「useMemo 能减少渲染」 | 错。它只缓存**计算结果**，渲染照样发生 |
| 「useCallback 能让组件不重渲染」 | 错。它只让函数引用稳定，**配合 memo 才有用** |
| 「useState 存对象，改属性不 set 也能渲染」 | 错。引用没变就不渲染；变了才渲染 |
| 「Context 只影响用了它的那一层」 | 错。Provider 下所有消费者都被触发，且不受中间 memo 保护 |
| 「key 只是消除控制台警告」 | 错。key 决定复用还是重建 DOM 与组件状态 |

---

## 六、诊断流水线（照这个顺序做）

```
1. 确认现象：卡顿发生在什么操作（输入第几个字 / 打开弹窗 / 滚动）
2. Profiler 录制 → Ranked 面板找最贵的组件
3. 勾选 Record why each component rendered → 看 Id 的来源
4. why-did-you-render → 确认是「props 变了」还是「引用重建」
5. 分类处理：
   - 引用重建   → useCallback / useMemo / 提到组件外 / 状态下沉
   - Context 广播 → 拆 Context / 状态局部化 / useSyncExternalStore
   - 结构问题   → children 传递 / 组件拆分
   - 该渲染却在算 → 把昂贵计算移出渲染或 useMemo
6. 再录一次 Profiler 对比 actualDuration
```

**永远不要一上来就到处加 memo/useMemo。** 没定位就加，只会让代码更难读，而性能没变。
