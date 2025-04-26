import time
from typing import Optional

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

# ====== Model Definition ======
class CounterState(BaseModel):
    count: int = 0
    loading: bool = False
    error: Optional[str] = None
    last_updated: Optional[float] = None

# ====== Utility Functions ======
def state_copy(state: CounterState):
    new_state = state.model_copy()
    now = time.time()
    return new_state, now

# ====== Handlers ======
def increment_handler(state: CounterState, action) -> CounterState:
    if action.type == increment.type:
        new_state, now = state_copy(state)
        new_state.count += 1
        new_state.last_updated = now
        return new_state
    return state  # 如果不是 increment action，返回原狀態

def decrement_handler(state: CounterState, action) -> CounterState:
    if action.type == decrement.type:
        new_state, now = state_copy(state)
        new_state.count -= 1
        new_state.last_updated = now
        return new_state
    return state  # 如果不是 decrement action，返回原狀態

def reset_handler(state: CounterState, action) -> CounterState:
    if action.type == reset.type:
        new_state, now = state_copy(state)
        new_state.count = action.payload
        new_state.last_updated = now
        return new_state
    return state  # 如果不是 reset action，返回原狀態

def increment_by_handler(state: CounterState, action) -> CounterState:
    if action.type == increment_by.type:
        new_state, now = state_copy(state)
        new_state.count += action.payload
        new_state.last_updated = now
        return new_state
    return state  # 如果不是 increment_by action，返回原狀態

def load_count_request_handler(state: CounterState, action) -> CounterState:
    if action.type == load_count_request.type:
        new_state, now = state_copy(state)
        new_state.loading = True
        new_state.error = None
        return new_state
    return state  # 如果不是 load_count_request action，返回原狀態

def load_count_success_handler(state: CounterState, action) -> CounterState:
    if action.type == load_count_success.type:
        new_state, now = state_copy(state)
        new_state.loading = False
        new_state.count = action.payload
        new_state.last_updated = now
        return new_state
    return state  # 如果不是 load_count_success action，返回原狀態

def load_count_failure_handler(state: CounterState, action) -> CounterState:
    if action.type == load_count_failure.type:
        new_state, now = state_copy(state)
        new_state.loading = False
        new_state.error = action.payload
        return new_state
    return state  # 如果不是 load_count_failure action，返回原狀態
    
    
# ====== Reducer ======
counter_reducer = create_reducer(
    CounterState(),
    on(increment, increment_handler),
    on(decrement, decrement_handler),
    on(reset, reset_handler),
    on(increment_by, increment_by_handler),
    on(load_count_request, load_count_request_handler),
    on(load_count_success, load_count_success_handler),
    on(load_count_failure, load_count_failure_handler),
)