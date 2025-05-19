# Pystorex
<p align="center">
  <img src="https://raw.githubusercontent.com/JonesHong/pystorex/refs/heads/master/assets/images/logo.png" alt="pystorex icon" width="200"/>
</p>

<p align="center">
  <a href="https://pypi.org/project/pystorex/">
    <img alt="PyPI version" src="https://img.shields.io/pypi/v/pystorex.svg">
  </a>
  <a href="https://pypi.org/project/pystorex/">
    <img alt="Python versions" src="https://img.shields.io/pypi/pyversions/pystorex.svg">
  </a>
  <a href="https://joneshong.github.io/pystorex/en/index.html">
    <img alt="Documentation" src="https://img.shields.io/badge/docs-ghpages-blue.svg">
  </a>
  <a href="https://github.com/JonesHong/pystorex/blob/master/LICENSE">
    <img alt="License" src="https://img.shields.io/github/license/JonesHong/pystorex.svg">
  </a>
  <a href="https://deepwiki.com/JonesHong/pystorex"><img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki"></a>
</p>

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

> 需 Python 3.9+ 支援。

---

## 快速開始

此範例展示如何透過 TypedDict 定義狀態，並使用 immutables.Map 處理狀態更新，以獲得更好的效能與清晰度。

```python
import time
from typing import Optional
from typing_extensions import TypedDict
from reactivex import operators as ops
from immutables import Map

from pystorex.actions import create_action
from pystorex import create_store, create_reducer, on, create_effect
from pystorex.store_selectors import create_selector
from pystorex.middleware import LoggerMiddleware
from pystorex.map_utils import batch_update

# 1. 定義狀態模型 (TypedDict)
class CounterState(TypedDict):
    count: int
    loading: bool
    error: Optional[str]
    last_updated: Optional[float]

counter_initial_state = CounterState(
    count=0, loading=False, error=None, last_updated=None
)

# 2. 定義 Actions
increment = create_action("increment")
decrement = create_action("decrement")
reset = create_action("reset", lambda value: value)
increment_by = create_action("incrementBy", lambda amount: amount)
load_count_request = create_action("loadCountRequest")
load_count_success = create_action("loadCountSuccess", lambda value: value)
load_count_failure = create_action("loadCountFailure", lambda error: error)

# 3. 定義 Reducer

def counter_handler(state: Map, action) -> Map:
    now = time.time()
    if action.type == increment.type:
        return state.set("count", state["count"] + 1).set("last_updated", now)
    elif action.type == decrement.type:
        return batch_update(state, {"count": state["count"] - 1, "last_updated": now})
    elif action.type == reset.type:
        return batch_update(state, {"count": action.payload, "last_updated": now})
    elif action.type == increment_by.type:
        return batch_update(state, {"count": state["count"] + action.payload, "last_updated": now})
    elif action.type == load_count_request.type:
        return batch_update(state, {"loading": True, "error": None})
    elif action.type == load_count_success.type:
        return batch_update(state, {"loading": False, "count": action.payload, "last_updated": now})
    elif action.type == load_count_failure.type:
        return batch_update(state, {"loading": False, "error": action.payload})
    return state

counter_reducer = create_reducer(
    counter_initial_state,
    on(increment, counter_handler),
    on(decrement, counter_handler),
    on(reset, counter_handler),
    on(increment_by, counter_handler),
    on(load_count_request, counter_handler),
    on(load_count_success, counter_handler),
    on(load_count_failure, counter_handler),
)

# 4. 定義 Effects
class CounterEffects:
    @create_effect
    def load_count(self, action_stream):
        return action_stream.pipe(
            ops.filter(lambda action: action.type == load_count_request.type),
            ops.do_action(lambda _: print("Effect: Loading counter...")),
            ops.delay(1.0),
            ops.map(lambda _: load_count_success(42))
        )

# 5. 建立 Store 與註冊模組
store = create_store()
store.apply_middleware(LoggerMiddleware)
store.register_root({"counter": counter_reducer})
store.register_effects(CounterEffects)

# 6. 使用 Selector 訂閱狀態
get_counter_state = lambda state: state["counter"]
get_count = create_selector(
    get_counter_state,
    result_fn=lambda counter: counter.get("count", 0)
)
store.select(get_count).subscribe(
    lambda c: print(f"Count: {c[1]}")
)

# 7. 執行操作示例
if __name__ == "__main__":
    store.dispatch(increment())
    store.dispatch(increment_by(5))
    store.dispatch(decrement())
    store.dispatch(reset(10))
    store.dispatch(load_count_request())
    # 給 Effects 一些時間
    time.sleep(2)
```

### 注意事項

* 狀態管理已改為使用 `TypedDict` 和 `immutables.Map`，避免了 Pydantic 模型在頻繁狀態更新時的效能損耗。
* 使用 `batch_update` 及 `immutables.Map` 的內建方法，以確保狀態更新的不可變性。
* Pydantic 模型可視需求透過工具函數動態轉換使用，詳見範例原始碼。


---
## Examples

本專案附帶以下範例腳本，展示「拆分式 (modular)」與「一體化 (Monolithic)」的使用範例：

**Counter 範例**

- `examples/counter_example/main.py`：拆分式 Counter 範例入口程式。
- `examples/counter_example/counter_example_monolithic.py`：一體化 Counter 範例。

**Detection 範例**

- `examples/detection_example/main.py`：拆分式偵測範例入口程式。
- `examples/detection_example/detection_example_monolithic.py`：一體化偵測範例。

可以在專案根目錄執行：

```bash
python examples/counter_example/main.py
python examples/counter_example/counter_example_monolithic.py
python examples/detection_example/main.py
python examples/detection_example/detection_example_monolithic.py
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




