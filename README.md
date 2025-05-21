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
</p>

A lightweight Python state management library inspired by NgRx/Redux patterns and ReactiveX for Python (`reactivex`). Manage application state with reducers, handle side effects with effects, compose middleware, and select state slices efficiently.

---

## Features

* **Typed State**: Define your root state using `typing_extensions.TypedDict` and store it in `immutables.Map`, fully generic.
* **Reducers**: Pure functions to update state in response to actions.
* **Effects**: Handle side effects by listening to action streams and optionally dispatching actions.
* **Middleware**: Insert custom logic (logging, thunks, error handling) into the dispatch pipeline.
* **Selectors**: Memoized and configurable (deep compare, TTL) state accessors.
* **Immutable Updates**: Use shallow copy at the feature level or integrate with `immutables.Map` and utility functions (`to_immutable`, `to_dict`, `to_pydantic`).
* **Hot Module Management**: Register/unregister feature reducers and effects at runtime.

---

## Installation

```bash
pip install pystorex
```
> Requires Python 3.9+ support.

---

## Quick Start

This example demonstrates how to define state using `TypedDict` and handle state updates with `immutables.Map` for better performance and clarity.

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

# 1. Define state model (TypedDict)
class CounterState(TypedDict):
    count: int
    loading: bool
    error: Optional[str]
    last_updated: Optional[float]

counter_initial_state = CounterState(
    count=0, loading=False, error=None, last_updated=None
)

# 2. Define Actions
increment = create_action("increment")
decrement = create_action("decrement")
reset = create_action("reset", lambda value: value)
increment_by = create_action("incrementBy", lambda amount: amount)
load_count_request = create_action("loadCountRequest")
load_count_success = create_action("loadCountSuccess", lambda value: value)
load_count_failure = create_action("loadCountFailure", lambda error: error)

# 3. Define Reducer

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

# 4. Define Effects
class CounterEffects:
    @create_effect
    def load_count(self, action_stream):
        return action_stream.pipe(
            ops.filter(lambda action: action.type == load_count_request.type),
            ops.do_action(lambda _: print("Effect: Loading counter...")),
            ops.delay(1.0),
            ops.map(lambda _: load_count_success(42))
        )

# 5. Create Store and Register Modules
store = create_store()
store.apply_middleware(LoggerMiddleware)
store.register_root({"counter": counter_reducer})
store.register_effects(CounterEffects)

# 6. Use Selector to Subscribe to State
get_counter_state = lambda state: state["counter"]
get_count = create_selector(
    get_counter_state,
    result_fn=lambda counter: counter.get("count", 0)
)
store.select(get_count).subscribe(
    lambda c: print(f"Count: {c[1]}")
)

# 7. Execute Example Operations
if __name__ == "__main__":
    store.dispatch(increment())
    store.dispatch(increment_by(5))
    store.dispatch(decrement())
    store.dispatch(reset(10))
    store.dispatch(load_count_request())
    # Give Effects some time
    time.sleep(2)
```

### Notes

* State management has been updated to use `TypedDict` and `immutables.Map`, avoiding the performance overhead of Pydantic models during frequent state updates.
* Use `batch_update` and built-in methods of `immutables.Map` to ensure immutability of state updates.
* Pydantic models can be dynamically converted as needed using utility functions. See the example source code for details.

---

## Examples

This project includes example scripts demonstrating monolithic and modular usage patterns:

* `examples/counter_example/counter_example_monolithic.py`: Monolithic Counter example using TypedDict + Map.
* `examples/counter_example/main.py`: Modular Counter example.
* `examples/detection_example/...`: Detection examples.

Run them with:

```bash
python examples/counter_example/counter_example_monolithic.py
python examples/counter_example/main.py
```

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
   twine upload dist/*
   ```

---

## Contributing

* Fork the repo
* Create a feature branch
* Write tests (pytest) and update docs
* Submit a Pull Request

---

## License

[MIT](LICENSE)
