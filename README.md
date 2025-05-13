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

A lightweight Python state management library inspired by NgRx/Redux patterns and ReactiveX for Python (`reactivex`). Manage application state with reducers, handle side effects with effects, compose middleware, and select state slices efficiently.


---

## Features

- **Typed State**: Define your root state using Pydantic or any Python object, fully generic.
- **Reducers**: Pure functions to update state in response to actions.
- **Effects**: Handle side effects by listening to action streams and optionally dispatching actions.
- **Middleware**: Insert custom logic (logging, thunks, error handling) into dispatch pipeline.
- **Selectors**: Memoized and configurable (deep compare, TTL) state accessors.
- **Immutable Updates**: Shallow copy at feature level or integrate with `immutables.Map`.
- **Hot Module Management**: Register/unregister feature reducers and effects at runtime.

---

## Installation

```bash
pip install pystorex
```

> Requires Python 3.7+

---

## Quick Start

```python
import time
from typing import Optional
from pydantic import BaseModel
from reactivex import operators as ops

from pystorex.actions import create_action
from pystorex import create_store, create_reducer, on, create_effect
from pystorex.store_selectors import create_selector
from pystorex.middleware import LoggerMiddleware

# 1. 定義狀態模型
class CounterState(BaseModel):
    count: int = 0
    loading: bool = False
    error: Optional[str] = None
    last_updated: Optional[float] = None

# 2. 定義 Actions
increment = create_action("increment")
decrement = create_action("decrement")
reset = create_action("reset", lambda value: value)
increment_by = create_action("incrementBy", lambda amount: amount)

load_count_request = create_action("loadCountRequest")
load_count_success = create_action("loadCountSuccess", lambda value: value)
load_count_failure = create_action("loadCountFailure", lambda error: error)

# 3. 定義 Reducer
def counter_handler(state: CounterState, action) -> CounterState:
    new_state = state.copy(deep=True)
    now = time.time()

    if action.type == increment.type:
        new_state.count += 1
        new_state.last_updated = now
    elif action.type == decrement.type:
        new_state.count -= 1
        new_state.last_updated = now
    elif action.type == reset.type:
        new_state.count = action.payload
        new_state.last_updated = now
    elif action.type == increment_by.type:
        new_state.count += action.payload
        new_state.last_updated = now
    elif action.type == load_count_request.type:
        new_state.loading = True
        new_state.error = None
    elif action.type == load_count_success.type:
        new_state.loading = False
        new_state.count = action.payload
        new_state.last_updated = now
    elif action.type == load_count_failure.type:
        new_state.loading = False
        new_state.error = action.payload

    return new_state

counter_reducer = create_reducer(
    CounterState(),
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


# 5. 建立 Store、註冊模組
store = create_store()
store.apply_middleware(LoggerMiddleware)
store.register_root({"counter": counter_reducer})
store.register_effects(CounterEffects)

# 6. 訂閱狀態與測試
get_counter_state = lambda state: state["counter"]
get_count = create_selector(
    get_counter_state,
    result_fn=lambda counter: counter.count or 0
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

---

## Examples

This project includes the following example scripts to demonstrate both the modular and monolithic usage patterns:

**Counter Example**

- `examples/counter_example/main.py`: Entry point for the modular Counter example.
- `examples/counter_example/counter_example_monolithic.py`: Monolithic Counter example.

**Detection Example**

- `examples/detection_example/main.py`: Entry point for the modular Detection example.
- `examples/detection_example/detection_example_monolithic.py`: Monolithic Detection example.

You can run them from the project root:

```bash
python examples/counter_example/main.py
python examples/counter_example/counter_example_monolithic.py
python examples/detection_example/main.py
python examples/detection_example/detection_example_monolithic.py
```

## Core Concepts

### Store
Manages application state, dispatches actions, and notifies subscribers.

```python
store = create_store(MyRootState())
store.register_root({
    "feature_key": feature_reducer,
    # ... more reducers
})
store.register_effects(FeatureEffects)
```

### Actions
Use `create_action(type, prepare_fn)` to define action creators.

```python
from pystorex.actions import create_action
my_action = create_action("myAction", lambda data: {"payload": data})
```

### Reducers
Pure functions taking `(state, action)` and returning new state.

```python
from pystorex import create_reducer, on
reducer = create_reducer(
    InitialState(),
    on(my_action, my_handler)
)
```

### Effects
Side-effect handlers listening to action streams via ReactiveX.

```python
from pystorex import create_effect
from reactivex import operators as ops

class FeatureEffects:
    @create_effect
    def log_actions(action$):
        return action$.pipe(
            ops.filter(lambda a: a.type == my_action.type),
            ops.map(lambda _: another_action())
        )
```

### Middleware
Insert custom dispatch logic. Example: Logger

```python
class LoggerMiddleware:
    def on_next(self, action): print("▶️", action.type)
    def on_complete(self, result, action): print("✅", action)
    def on_error(self, err, action): print("❌", err)

store.apply_middleware(LoggerMiddleware)
```

### Selectors
Memoized accessors with optional `deep=True` or `ttl`.

```python
from pystorex.selectors import create_selector
get_items = create_selector(
    lambda s: s.feature.items,
    result_fn=lambda items: [i.value for i in items],
    deep=True, ttl=5.0
)
```

---

## Advanced Topics

- **Hot Module DnD**: `store.register_feature` / `store.unregister_feature` to add/remove features at runtime.
- **Immutable State**: Integrate `immutables.Map` for structural sharing.
- **DevTools**: Capture action/state history for time-travel debugging.

---

## Publishing to PyPI

1. Ensure `pyproject.toml` & `setup.cfg` are configured.
2. Install build tools:
   ```bash
   pip install --upgrade build twine
   ```
3. Build distributions:
   ```bash
   python -m build
   ```
4. Upload:
   ```bash
   python -m twine upload dist/*
   ```

---

## Contributing

- Fork the repo
- Create a feature branch
- Write tests (pytest) and update docs
- Submit a Pull Request

---

## License

[MIT](LICENSE)

