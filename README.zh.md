# Pystorex

輕量級 Python 狀態管理函式庫，靈感來自 NgRx/Redux 模式及 ReactiveX for Python (`reactivex`)。使用 reducer 管理應用狀態，使用 effects 處理副作用，支援 middleware 組合以及高效選擇器。

---

## 功能特色

- **Typed State**：使用 Pydantic 或任何 Python 型別定義根狀態，支援泛型。
- **Reducers**：純函式，根據 action 更新狀態。
- **Effects**：訂閱 action 流並可選擇 dispatch action 以處理副作用。
- **Middleware**：在 dispatch 過程中插入自訂邏輯（例如日誌、thunk、錯誤處理）。
- **Selectors**：具備快取、深度比較與 TTL 等可配置選擇器。
- **Immutable Updates**：支援特性層級淺拷貝或整合 `immutables.Map`。
- **Hot Module Management**：在執行時新增/移除特性 reducers 與 effects。

---

## 安裝

```bash
pip install pystorex
```

> 需 Python 3.7+ 支援。

---

## 快速開始

```python
from pystorex import create_store, create_reducer, on, create_effect, create_selector
from pydantic import BaseModel

# 1. 定義狀態模型
class CounterState(BaseModel):
    count: int = 0

# 2. 建立 actions
from pystorex.actions import create_action
increment = create_action("increment")
decrement = create_action("decrement")

# 3. 建立 reducer
def counter_handler(state: CounterState, action):
    if action.type == increment.type:
        state.count += 1
    elif action.type == decrement.type:
        state.count -= 1
    return state

counter_reducer = create_reducer(
    CounterState(),
    on(increment, counter_handler),
    on(decrement, counter_handler)
)

# 4. 建立 store
store = create_store(CounterState())
store.register_root({"counter": counter_reducer})

# 5. 訂閱狀態變更
store.select(lambda s: s.counter.count).subscribe(lambda new: print("Count:", new))

# 6. 分發 actions
store.dispatch(increment())  # Count: 1
store.dispatch(increment())  # Count: 2
store.dispatch(decrement())  # Count: 1
```

---

## 核心概念

### Store
管理應用狀態、分發 action 並通知訂閱者。

```python
store = create_store(MyRootState())
store.register_root({
    "feature_key": feature_reducer,
})
store.register_effects(FeatureEffects)
```

### Actions
使用 `create_action(type, prepare_fn)` 定義 action 建造器。

```python
from pystorex.actions import create_action
my_action = create_action("myAction", lambda data: {"payload": data})
```

### Reducers
純函式，接收 `(state, action)` 並返回新狀態。

```python
from pystorex import create_reducer, on
reducer = create_reducer(
    InitialState(),
    on(my_action, my_handler)
)
```

### Effects
使用 ReactiveX 訂閱 action 流並可回傳 Action。

```python
from pystorex import create_effect
from reactivex import operators as ops

class FeatureEffects:
    @create_effect
    def log_actions(action_stream):
        return action_stream.pipe(
            ops.filter(lambda a: a.type == my_action.type),
            ops.map(lambda _: another_action())
        )
```

### Middleware
在 dispatch 鏈中插入自訂邏輯，例如日誌或 thunk。

```python
class LoggerMiddleware:
    def on_next(self, action): print("▶️", action.type)
    def on_complete(self, result, action): print("✅", action)
    def on_error(self, err, action): print("❌", err)

store.apply_middleware(LoggerMiddleware)
```

### Selectors
具備快取、深度比較與 TTL 控制的狀態選擇器。

```python
from pystorex.selectors import create_selector
get_items = create_selector(
    lambda s: s.feature.items,
    result_fn=lambda items: [i.value for i in items],
    deep=True, ttl=5.0
)
```

---

## 進階主題

- Hot Module DnD：`store.register_feature` / `store.unregister_feature` 動態新增/移除特性。
- Immutable State：整合 `immutables.Map` 實現結構共享。
- DevTools：捕捉 action 與 state 歷史進行時間旅行調試。

---

## 發佈到 PyPI

1. 確認 `pyproject.toml` 與 `setup.cfg` 已設定完畢。
2. 安裝打包工具：
   ```bash
   pip install --upgrade build twine
   ```
3. 生成分發包：
   ```bash
   python -m build
   ```
4. 上傳：
   ```bash
   python -m twine upload dist/*
   ```

---

## 參與貢獻

- Fork 本專案
- 建立功能分支
- 撰寫測試（pytest）並更新文件
- 提交 Pull Request

---

## 授權

[MIT](LICENSE)

