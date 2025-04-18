# Pystorex

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
from pystorex import create_store, create_reducer, on, create_effect, create_selector
from pydantic import BaseModel

# 1. Define your state models
class CounterState(BaseModel):
    count: int = 0

# 2. Create actions
from pystorex.actions import create_action
increment = create_action("increment")
decrement = create_action("decrement")

# 3. Create reducer
def counter_handler(state: CounterState, action):
    if action.type == increment.type:
        state.count += 1
    elif action.type == decrement.type:
        state.count -= 1
    return state

counter_reducer = create_reducer(CounterState(), on(increment, counter_handler), on(decrement, counter_handler))

# 4. Create store
store = create_store(CounterState())
store.register_root({"counter": counter_reducer})

# 5. Subscribe to state changes
store.select(lambda s: s.counter.count).subscribe(lambda new: print("Count:", new))

# 6. Dispatch actions
store.dispatch(increment())  # Count: 1
store.dispatch(increment())  # Count: 2
store.dispatch(decrement())  # Count: 1
```

---

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

