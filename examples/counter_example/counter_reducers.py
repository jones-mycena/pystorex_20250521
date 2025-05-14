import time
from typing import Optional, TypedDict

from pydantic import BaseModel
from pystorex import create_reducer, on
from pystorex.actions import create_action
from counter_actions import (
    increment,
    decrement,
    reset,
    increment_by,
    load_count_request,
    load_count_success,
    load_count_failure,
)
from pystorex.map_utils import batch_update


# ====== Model Definition ======
class CounterState(TypedDict):
    count: int
    loading: bool
    error: Optional[str]
    last_updated: Optional[float]


counter_initial_state = CounterState(
    count=0, loading=False, error=None, last_updated=None
)


# ====== Handlers ======
def increment_handler(state: CounterState, action) -> CounterState:
    return batch_update(
        state, {"count": state["count"] + 1, "last_updated": time.time()}
    )


def decrement_handler(state: CounterState, action) -> CounterState:
    return batch_update(
        state, {"count": state["count"] - 1, "last_updated": time.time()}
    )


def reset_handler(state: CounterState, action) -> CounterState:
    return batch_update(state, {"count": action.payload, "last_updated": time.time()})


def increment_by_handler(state: CounterState, action) -> CounterState:
    return batch_update(
        state, {"count": state["count"] + action.payload, "last_updated": time.time()}
    )


def load_count_request_handler(state: CounterState, action) -> CounterState:
    return batch_update(
        state, {"loading": True, "error": None, "last_updated": time.time()}
    )


def load_count_success_handler(state: CounterState, action) -> CounterState:
    return batch_update(
        state, {"count": action.payload, "loading": False, "last_updated": time.time()}
    )


def load_count_failure_handler(state: CounterState, action) -> CounterState:
    return batch_update(
        state, {"loading": False, "error": action.payload, "last_updated": time.time()}
    )


# ====== Reducer ======
counter_reducer = create_reducer(
    # CounterState(),
    counter_initial_state,
    on(increment, increment_handler),
    on(decrement, decrement_handler),
    on(reset, reset_handler),
    on(increment_by, increment_by_handler),
    on(load_count_request, load_count_request_handler),
    on(load_count_success, load_count_success_handler),
    on(load_count_failure, load_count_failure_handler),
)
