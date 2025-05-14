from typing import Optional
from examples.counter_example.counter_reducers import CounterState
from pystorex.store_selectors import create_selector

# 定義 Selectors
def get_counter_state(state: dict) -> CounterState:
    return state.get('counter', {})  # 使用 get 提供默認值

def get_count_handler(counter: CounterState) -> int:
    return counter.get('count', 0)

def get_loading_handler(counter: CounterState) -> bool:
    return counter.get('loading', False)

def get_error_handler(counter: CounterState) -> Optional[str]:
    return counter.get('error', None)

def get_last_updated_handler(counter: CounterState) -> Optional[str]:
    return counter.get('last_updated', None)

def combine_counter_info_handler(count: int, last_updated: Optional[str]) -> dict:
    return {"count": count, "last_updated": last_updated}


# 定義Selectors
get_count = create_selector(
    get_counter_state, result_fn=get_count_handler
)
get_loading = create_selector(
    get_counter_state, result_fn=get_loading_handler
)
get_error = create_selector(
    get_counter_state, result_fn=get_error_handler
)
get_last_updated = create_selector(
    get_counter_state, get_last_updated_handler
)
# 创建一个复合选择器
get_counter_info = create_selector(
    get_count,
    get_last_updated,
    result_fn=combine_counter_info_handler
)
