import json
from pathlib import Path
import sys



sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import time
from typing import List, Optional, Tuple
from typing_extensions import TypedDict

from pydantic import BaseModel
from reactivex import operators as ops
from immutables import Map

from pystorex.rx_operators import ofType
from pystorex.actions import create_action, Action, update_reducer
from pystorex import create_store, create_reducer, on, create_effect
from pystorex.store_selectors import create_selector
from pystorex.middleware import LoggerMiddleware, PerformanceMonitorMiddleware

# 導入新的工具函數
from pystorex.immutable_utils import to_dict, to_pydantic, to_immutable
from pystorex.map_utils import batch_update, update_in

from pystorex.reducers import create_reducer_from_function_handler
from pystorex.action_handlers import TypedActionHandler

# ====== 1. 定義狀態模型 ======
# class CounterStateModel(BaseModel):
#     count: int = 0
#     # loading: bool = False
#     error: Optional[str] = None
#     last_updated: Optional[float] = None

class CounterState(TypedDict):
    count: int
    loading: Optional[bool]  # 修改為 Optional[bool] 而不是 bool
    error: Optional[str]
    last_updated: Optional[float]
    history: Tuple[int, ...]  # 使用 Tuple 而不是 List
    max_value: int      # 新增
    min_value: int      # 新增


counter_initial_state = CounterState(
    count=0, loading=False,  error=None, last_updated=None,history=(), max_value=100, min_value=0
)
# ====== 2. 定義 Actions ======
increment = create_action("increment")
decrement = create_action("decrement")
reset = create_action("reset", lambda value: value)
increment_by = create_action("incrementBy", lambda amount: amount)

load_count_request = create_action("loadCountRequest")
load_count_success = create_action("loadCountSuccess", lambda value: value)
load_count_failure = create_action("loadCountFailure", lambda error: error)

# 新增警告 action
count_warning = create_action("countWarning", lambda count: count)


# ====== 3. 定義 Reducer ======
# def counter_handler(state: CounterState, action: Action) -> CounterState:  # type: ignore
#     """
#     處理計數器相關 action，接收 Map 狀態並返回新的 Map 狀態
#     注意: 不再返回 Pydantic 模型，而是直接操作 Map
#     """

#     now = time.time()
#     print(f"counter_handler:")
#     print(f"get_action: {action.type} & {action.payload}")
#     print(f"state: {state['count']} & {state.get('last_updated')}")
#     if action.type == increment.type:
#         # 使用 Map.set() 或 batch_update() 創建新的 Map
#         new_state = state.set("count",state["count"] + 1)
#         new_state = new_state.set("last_updated",now)
#         return new_state
#         # return batch_update(state, {"count": state["count"] + 1, "last_updated": now})
#     elif action.type == decrement.type:
#         return batch_update(state, {"count": state["count"] - 1, "last_updated": now})
#     elif action.type == reset.type:
#         return batch_update(state, {"count": action.payload, "last_updated": now})
#     elif action.type == increment_by.type:
#         return batch_update(
#             state, {"count": state["count"] + action.payload, "last_updated": now}
#         )
#     elif action.type == load_count_request.type:
#         return batch_update(state, {"loading": True, "error": None})
#     elif action.type == load_count_success.type:
#         return batch_update(
#             state, {"loading": False, "count": action.payload, "last_updated": now}
#         )
#     elif action.type == load_count_failure.type:
#         return batch_update(state, {"loading": False, "error": action.payload})
#     return state


# 創建 reducer，允許傳入 Pydantic 模型作為初始狀態
# 庫內部會自動轉換為 Map
# counter_reducer = create_reducer(
#     # CounterStateModel(),  # Pydantic 模型作為初始狀態
#     counter_initial_state,
#     on(increment, counter_handler),
#     on(decrement, counter_handler),
#     on(reset, counter_handler),
#     on(increment_by, counter_handler),
#     on(load_count_request, counter_handler),
#     on(load_count_success, counter_handler),
#     on(load_count_failure, counter_handler),
# )

# 創建 TypedActionHandler
handler = TypedActionHandler(
    CounterState,
    initial_values={
        "count": 0,
        "last_updated": None,
        "history": [],
        "max_value": 100,
        "min_value": 0
    }
)

# 註冊處理函數，現在 IDE 可以提供字段自動完成和類型檢查
@handler.register("increment")
def handle_increment(state, action):
    new_count = state["count"] + 1
    # 將 [new_count] 改為 (new_count,)
    return (state
            .set("count", new_count)
            .set("last_updated", time.time())
            .set("history", state["history"] + (new_count,)))  # 使用元組而不是列表

@handler.register("decrement")
def handle_decrement(state, action):
    new_count = max(state["min_value"], state["count"] - 1)
    return (state
            .set("count", new_count)
            .set("last_updated", time.time())
            .set("history", state["history"] + (new_count,)))  # 使用元組而不是列表

@handler.register("reset")
def handle_reset(state, action):
    new_count = action.payload
    return (state
            .set("count", new_count)
            .set("last_updated", time.time())
            .set("history", state["history"] + (new_count,)))  # 使用元組而不是列表
# 為 "incrementBy" 註冊處理函數
@handler.register("incrementBy")
def handle_increment_by(state, action):
    new_count = min(state["max_value"], state["count"] + action.payload)
    return (state
            .set("count", new_count)
            .set("last_updated", time.time())
            .set("history", state["history"] + (new_count,)))

# 為 "loadCountRequest" 註冊處理函數
@handler.register("loadCountRequest")
def handle_load_count_request(state, action):
    return (state
            .set("loading", True)
            .set("error", None))

# 為 "loadCountSuccess" 註冊處理函數
@handler.register("loadCountSuccess")
def handle_load_count_success(state, action):
    new_count = action.payload
    return (state
            .set("loading", False)
            .set("count", new_count)
            .set("last_updated", time.time())
            .set("history", state["history"] + (new_count,)))

# 為 "loadCountFailure" 註冊處理函數
@handler.register("loadCountFailure")
def handle_load_count_failure(state, action):
    return (state
            .set("loading", False)
            .set("error", action.payload))

# 創建 reducer
counter_reducer = create_reducer_from_function_handler(handler)

# ====== 4. 定義 Effects ======
class CounterEffects:
    @create_effect
    def load_count(self, action_stream):
        """模擬從 API 載入數據的副作用，成功後 dispatch load_count_success"""
        return action_stream.pipe(
            ofType(load_count_request),
            ops.do_action(lambda _: print("Effect: Loading counter...")),
            ops.delay(1.0),  # 延遲 1 秒
            ops.map(lambda _: load_count_success(42)),  # 假設 API 回傳 42
        )

    @create_effect(dispatch=False)
    def log_actions(self, action_stream):
        """只做日誌，不 dispatch 新 action"""
        return action_stream.pipe(
            ops.do_action(lambda action: print(f"[Log] Action: {action.type}")),
            ops.filter(lambda _: False),
        )

    @create_effect(dispatch=False)
    def handle_count_warning(self, action_stream):
        """處理計數器過高的警告"""
        return action_stream.pipe(
            # ops.filter(lambda action: action.type == count_warning.type),
            ofType(count_warning),
            ops.do_action(
                lambda action: print(
                    f"[Warning] 計數器超過閾值! 目前值: {action.payload}"
                )
            ),
            ops.filter(lambda _: False),
        )


# ====== 5. 建立 Store、註冊模組 ======
store = create_store()
store.apply_middleware(LoggerMiddleware)
store.apply_middleware(PerformanceMonitorMiddleware(log_all=True))
store.register_root({"counter": counter_reducer})
store.register_effects(CounterEffects)

# ====== 6. 訂閱狀態與測試 ======
# 監聽完整 state
store.select().subscribe(lambda s: print(f"State changed: {s[1]}"))

# 監聽 count 值 (使用 Map 的 get 方法)
get_counter_state = lambda state: state["counter"]
get_count = create_selector(
    get_counter_state,
    result_fn=lambda counter: counter.get("count", 0),  # 使用 Map.get() 而非屬性訪問
)
store.select(get_count).subscribe(
    lambda c: print(f"Count: {c[1]}")  # 現在拿到的是 (old_value, new_value) 元組
)


# 新增 selector 監控 count 並在超過閾值時發出警告
def count_warning_monitor(value_tuple):
    old_value, new_value = value_tuple
    # if new_value > 8 and (old_value <= 8 or old_value is None):
    if new_value > 8 and old_value != new_value:
        store.dispatch(count_warning(new_value))


store.select(get_count).subscribe(count_warning_monitor)


# 示範使用者決定何時轉換回 Pydantic
def print_pydantic_when_needed(value_tuple):
    _, new_state = value_tuple
    counter_map = new_state["counter"]

    # 只在特定條件下才轉換回 Pydantic (使用者決定)
    if counter_map.get("count", 0) > 5:
        # 按需轉換為 Pydantic 模型
        # counter_pydantic = to_pydantic(counter_map, CounterStateModel)
        # print(f"Pydantic model: {counter_pydantic}")
        # 可以使用 Pydantic 的方法和屬性
        # print(f"JSON: {counter_pydantic.model_dump_json()}")
        
        # counter_dict = to_dict(counter_map)
        # print(f"Dict model: {counter_dict}")
        # print(f"JSON: {json.dumps(counter_dict,ensure_ascii=False,indent=2)}")

        # 使用 TypedDict 動態生成 Pydantic 模型
        counter_pydantic = to_pydantic(counter_map, CounterState)
        print(f"Pydantic model: {counter_pydantic}")
        print(f"JSON: {counter_pydantic.model_dump_json()}")


# 只有在需要時才轉換為 Pydantic
store.select().subscribe(print_pydantic_when_needed)

# ====== 7. 執行操作示例 ======
if __name__ == "__main__":
    # 基本操作
    store.dispatch(update_reducer())
    store.dispatch(increment())
    store.dispatch(increment_by(5))
    store.dispatch(decrement())
    store.dispatch(reset(10))  # 應該觸發警告，因為 count > 8
    store.dispatch(increment_by(99))
    store.dispatch(update_reducer())

    # 模擬 API 加載
    store.dispatch(load_count_request())
    # 給 effect buffer 一些時間
    time.sleep(2)

    # 打印最終狀態
    print("\n==== 最終狀態 ====")
    counter_state_map = store.state["counter"]
    counter_state_dict = to_dict(counter_state_map)
    counter_state_pydantic = to_pydantic(counter_state_map, CounterState)
    print(f"Counter dict: {counter_state_dict}")
    print(f"Counter pydantic: {counter_state_pydantic}")

