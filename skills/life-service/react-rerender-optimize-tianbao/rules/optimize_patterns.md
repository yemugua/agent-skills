# React 重渲染优化 · 写法规则库

> 每条规则都配了「错误写法 vs 正确写法」。
> 原则：**先定位再优化**（见 `rules/rerender_diagnosis.md`），没数据支撑的优化都是负优化。

---

## 一、React.memo：什么时候有用，什么时候白写

```jsx
// 基础用法
const Row = React.memo(function Row({ user, onSelect }) {
  return <li onClick={() => onSelect(user.id)}>{user.name}</li>;
});

// 需要自定义比较时（能返回 true 才是不渲染）
const Chart = React.memo(
  function Chart({ data }) { /* ... */ },
  (prev, next) => prev.data.id === next.data.id && prev.data.version === next.data.version
);
```

| 场景 | 结论 |
|---|---|
| 纯展示组件 + props 基本稳定 | ✅ 有用 |
| 每次都收到新对象/数组/函数 prop | ❌ 白写，先把引用稳定下来 |
| 组件渲染成本极低（几个 div） | ❌ 得不偿失，浅比较本身也有成本 |
| children 来自父组件的 JSX | ❌ 几乎必然失效（children 每次都是新 element） |

**接收 children 的组件，memo 基本无效：**

```jsx
// 错误：这样包一层，children 每次都是新的 React element
const Card = memo(({ children }) => <div className="card">{children}</div>);
<Card><HeavyTable /></Card>   // HeavyTable 每次重建 → memo 挡不住

// 正确：让重型组件自己 memo，Card 不用包
const HeavyTableMemo = memo(HeavyTable);
```

---

## 二、useMemo：缓存昂贵计算，不是万能药

```jsx
// 正确：依赖真实参与计算的量
const sorted = useMemo(() => {
  return [...list].sort((a, b) => a.score - b.score);
}, [list]);

// 错误：依赖数组写错，缓存反而有害
const sorted = useMemo(() => list.sort(...), []);   // 永远用第一次的结果（还改了原数组）
```

| 应该用 | 不该用 |
|---|---|
| 大数组排序 / 过滤 / 聚合 | 简单字符串拼接 |
| 复杂对象用于其他 Hook 的依赖 | 每个渲染都要新值的场景 |
| 作为 memo 子组件 prop 的引用稳定 | 一次性、渲染一次的组件 |

**昂贵的不是渲染本身，而是渲染里的计算：**

```jsx
// 错误：每次渲染都算一遍
function Dashboard({ rows }) {
  const stats = expensiveAggregate(rows);
  return <Chart data={stats} />;
}

// 正确
function Dashboard({ rows }) {
  const stats = useMemo(() => expensiveAggregate(rows), [rows]);
  return <Chart data={stats} />;
}
```

---

## 三、useCallback：只解决「函数引用」

```jsx
// 错误：memo 了子组件，但每次传新函数 → memo 完全失效
const Parent = () => {
  const [text, setText] = useState('');
  return <HeavyList onItemClick={(id) => console.log(id)} />;
};

// 正确：引用稳定 + 子组件 memo，两者缺一不可
const Parent = () => {
  const [text, setText] = useState('');
  const handleClick = useCallback((id) => { /* ... */ }, []);
  return <HeavyList onItemClick={handleClick} />;
};
const HeavyList = memo(HeavyListRaw);
```

**只在两种情况下需要 useCallback：**
1. 传给了 `memo` 子组件作为 prop
2. 作为其它 Hook 的依赖项（如 `useEffect` 的 deps）

其它场景直接写内联函数，**可读性和 diff 都更好**：

```jsx
// 没必要 wrapped：Button 没被 memo
<Button onClick={() => submit(form)} />
```

**依赖陷阱：**

```jsx
// 错误：闭包捕获了旧的 filters，回调永远用旧值
const load = useCallback(() => fetch({ q: filters }), []);

// 正确：把用到的值写进依赖
const load = useCallback(() => fetch({ q: filters }), [filters]);

// 或者用 ref 持有最新值（当依赖会导致下游连锁更新时）
const filtersRef = useRef(filters);
useEffect(() => { filtersRef.current = filters; });
const load = useCallback(() => fetch({ q: filtersRef.current }), []);
```

---

## 四、key：决定复用还是重建

| 写法 | 后果 |
|---|---|
| `key={index}` | 列表顺序变化时，React 按位置复用 DOM，**组件 state 串位**（输入内容错位、选中态错位） |
| `key={item.id}` | 正确：按身份识别 |
| `key={Math.random()}` | 每次渲染都是新 key，**整棵子树卸载重建**，性能与状态双输 |
| 无 key（map 里） | React 报警告，且行为等同 index |
| 用作「重置组件」 | ✅ 合法用法：`<Form key={userId} />` 故意让表单在切换用户时重建 |

```jsx
// 错误
{items.map((item, i) => <Row key={i} data={item} />)}

// 正确
{items.map(item => <Row key={item.id} data={item} />)}
```

> 验证方法：在一组带输入框的列表头部插入一项，看输入内容是否跟着数据走，而不是留在原来的位置。

---

## 五、Context：最容易让整棵树重渲染的东西

```jsx
// 错误：value 每次都是新对象，Provider 下所有消费者全部重渲染
<ThemeContext.Provider value={{ theme, toggleTheme }}>

// 正确：把 value 用 useMemo 稳住
const value = useMemo(() => ({ theme, toggleTheme }), [theme, toggleTheme]);
<ThemeContext.Provider value={value}>
```

**Context 的三条规律：**
1. `value` 引用一变，**所有消费者无条件重渲染**（中间层加 memo 也没用）
2. 消费者越深，重渲染路径越长
3. 一个巨型 Context（塞了用户、权限、主题、配置）会让任何一次小改动广播给所有人

**四个解法（按优先级）：**

```jsx
// 1) 拆分 Context：按更新频率分
const UserContext = createContext();
const ThemeContext = createContext();

// 2) 状态下沉：把 state 放在真正需要它的那层，而不是全局提到顶层
function SearchBox() {
  const [q, setQ] = useState('');   // 只有这里用，别提到 App
  return <input value={q} onChange={e => setQ(e.target.value)} />;
}

// 3) children 提升：Provider 包裹的是「已经存在的 children」，不参与重渲染
function Provider({ children }) {
  const [state, setState] = useState();
  return <Ctx.Provider value={state}>{children}</Ctx.Provider>;
}
// <Provider><ExpensiveTree /></Provider> —— ExpensiveTree 作为 children 传入，
// 引用稳定，state 变化时它不会重建

// 4) 选择器式订阅：react-redux useSelector / useSyncExternalStore
const theme = useSelector(s => s.theme);   // 只有 theme 变了才重渲染
```

---

## 六、状态下沉与组件拆分

```jsx
// 错误：输入框每敲一个字，整个 App（含 500 行表格）重渲染
function App() {
  const [text, setText] = useState('');
  return (
    <>
      <input value={text} onChange={e => setText(e.target.value)} />
      <ExpensiveTable />
    </>
  );
}

// 正确一：把 state 与 input 抽到子组件
function App() {
  return (<><SearchInput /><ExpensiveTable /></>);
}
function SearchInput() {
  const [text, setText] = useState('');
  return <input value={text} onChange={e => setText(e.target.value)} />;
}

// 正确二：state 提升到足够高的最小祖先，不要习惯性提到 App 顶层
```

**判断准则：state 放在「所有需要它的组件的最小公共祖先」，而不是「最顶层」。**

---

## 七、渲染期间不要做的事

| 反模式 | 问题 | 修法 |
|---|---|---|
| 在组件函数体内定义另一个组件 | 每次渲染都是一个**新的组件类型**，React 卸载旧子树重建新的 | 提到外层，或用 `useMemo` 缓存组件 |
| `new Date()` / `Date.now()` 参与渲染 | 每次都是新值，破坏 memo 与比较 | 用 state 或 `useMemo` 缓存到有意义的时间点 |
| `Math.random()` 当 key 或 id | 每次都变，全树重建 | 用稳定 id 生成（`useId` / 后端 id） |
| `JSON.parse` 大字符串在渲染里 | 每次渲染都解析 | `useMemo` 或放到数据流里 |
| 直接改 state 对象 `obj.a = 1; setObj(obj)` | 引用没变 → 不渲染；变了却不知道变了啥 | 返回新对象 |
| `setState` 传同一个值 | React 会 bail out（同引用不渲染） | 若用了 `Object/Array`，必须新引用 |

```jsx
// 错误：内嵌组件导致每次重建
function Parent() {
  const Inner = () => <span>{Math.random()}</span>;   // 每次渲染都是新类型
  return <Inner />;
}

// 正确
const Inner = () => <span>x</span>;
function Parent() { return <Inner />; }
```

---

## 八、其它有用手段

| 手段 | 适用 |
|---|---|
| 虚拟滚动（react-window / react-virtuoso） | 长列表几千项以上 |
| `useDeferredValue` / `startTransition` (React 18) | 输入联动的重计算，让它不阻塞输入 |
| 惰性初始化 `useState(() => heavy())` | 初始值昂贵时 |
| 按需引入重型第三方组件 | 编辑器、图表、地图：用 `lazy` + `Suspense` |
| 避免 `<>…</>` 里塞上千个节点 | 拆组件，缩小 diff 范围 |

```jsx
// React 18：输入不卡
function Search({ query }) {
  const deferred = useDeferredValue(query);
  const results = useMemo(() => search(deferred), [deferred]);
  return <ResultList data={results} />;
}
```

---

## 九、优化顺序决策树

```
重渲染很贵？
├─ 瓶颈是渲染内的昂贵计算 → useMemo（或把计算移出渲染）
├─ 瓶颈是重渲染层级太深 → 状态下沉 / 拆组件 / children 提升
├─ 是 Context 广播 → 拆 Context / 选择器订阅
├─ 是 props 引用重建 → useCallback + memo（两者成对）
├─ 是列表太长 → memo 行组件 + 虚拟滚动
└─ 都不是 → 别优化，先补测试
```

> **memo / useMemo / useCallback 不是免费的。** 它们用「内存 + 比较成本」换「渲染成本」。用在不必要的地方是纯亏。
