import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import time
from typing import Optional
from typing_extensions import TypedDict

from pydantic import BaseModel
from reactivex import operators as ops
from immutables import Map

from pystorex.actions import create_action, Action
from pystorex import create_store, create_reducer, on, create_effect
from pystorex.store_selectors import create_selector
from pystorex.middleware import LoggerMiddleware

# 導入新的工具函數
from pystorex.immutable_utils import to_dict, to_pydantic, to_immutable
from pystorex.map_utils import batch_update, update_in


# ====== 1. 定義狀態模型 ======
# class CounterStateModel(BaseModel):
#     count: int = 0
#     # loading: bool = False
#     error: Optional[str] = None
#     last_updated: Optional[float] = None

class CounterState(TypedDict):
    count: int
    loading: bool
    error: Optional[str]
    last_updated: Optional[float]


counter_initial_state = CounterState(
    count=0, loading=False,  error=None, last_updated=None
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
def counter_handler(state: CounterState, action: Action) -> CounterState:  # type: ignore
    """
    處理計數器相關 action，接收 Map 狀態並返回新的 Map 狀態
    注意: 不再返回 Pydantic 模型，而是直接操作 Map
    """

    now = time.time()
    print(f"counter_handler:")
    print(f"get_action: {action.type} & {action.payload}")
    print(f"state: {state['count']} & {state.get('last_updated')}")
    if action.type == increment.type:
        # 使用 Map.set() 或 batch_update() 創建新的 Map
        new_state = state.set("count",state["count"] + 1)
        new_state = new_state.set("last_updated",now)
        return new_state
        # return batch_update(state, {"count": state["count"] + 1, "last_updated": now})
    elif action.type == decrement.type:
        return batch_update(state, {"count": state["count"] - 1, "last_updated": now})
    elif action.type == reset.type:
        return batch_update(state, {"count": action.payload, "last_updated": now})
    elif action.type == increment_by.type:
        return batch_update(
            state, {"count": state["count"] + action.payload, "last_updated": now}
        )
    elif action.type == load_count_request.type:
        return batch_update(state, {"loading": True, "error": None})
    elif action.type == load_count_success.type:
        return batch_update(
            state, {"loading": False, "count": action.payload, "last_updated": now}
        )
    elif action.type == load_count_failure.type:
        return batch_update(state, {"loading": False, "error": action.payload})
    return state


# 創建 reducer，允許傳入 Pydantic 模型作為初始狀態
# 庫內部會自動轉換為 Map
counter_reducer = create_reducer(
    # CounterStateModel(),  # Pydantic 模型作為初始狀態
    counter_initial_state,
    on(increment, counter_handler),
    on(decrement, counter_handler),
    on(reset, counter_handler),
    on(increment_by, counter_handler),
    on(load_count_request, counter_handler),
    on(load_count_success, counter_handler),
    on(load_count_failure, counter_handler),
)


# ====== 4. 定義 Effects ======
class CounterEffects:
    @create_effect
    def load_count(self, action_stream):
        """模擬從 API 載入數據的副作用，成功後 dispatch load_count_success"""
        return action_stream.pipe(
            ops.filter(lambda action: action.type == load_count_request.type),
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
            ops.filter(lambda action: action.type == count_warning.type),
            ops.do_action(
                lambda action: print(
                    f"[Warning] 計數器超過閾值! 目前值: {action.payload}"
                )
            ),
            ops.filter(lambda _: False),
        )


# ====== 5. 建立 Store、註冊模組 ======
storage = create_store()
storage.apply_middleware(LoggerMiddleware)
storage.register_root({"counter": counter_reducer})
storage.register_effects(CounterEffects)

# ====== 6. 訂閱狀態與測試 ======
# 監聽完整 state
storage.select().subscribe(lambda s: print(f"State changed: {s[1]}"))

# 監聽 count 值 (使用 Map 的 get 方法)
get_counter_state = lambda state: state["counter"]
get_count = create_selector(
    get_counter_state,
    result_fn=lambda counter: counter.get("count", 0),  # 使用 Map.get() 而非屬性訪問
)
storage.select(get_count).subscribe(
    lambda c: print(f"Count: {c[1]}")  # 現在拿到的是 (old_value, new_value) 元組
)


# 新增 selector 監控 count 並在超過閾值時發出警告
def count_warning_monitor(value_tuple):
    old_value, new_value = value_tuple
    if new_value > 8 and (old_value <= 8 or old_value is None):
        storage.dispatch(count_warning(new_value))


storage.select(get_count).subscribe(count_warning_monitor)


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
storage.select().subscribe(print_pydantic_when_needed)

# ====== 7. 執行操作示例 ======
if __name__ == "__main__":
    # 基本操作
    storage.dispatch(increment())
    storage.dispatch(increment_by(5))
    storage.dispatch(decrement())
    storage.dispatch(reset(10))  # 應該觸發警告，因為 count > 8

    # 模擬 API 加載
    storage.dispatch(load_count_request())
    # 給 effect buffer 一些時間
    time.sleep(2)

    # 展示如何在需要時轉換回 Pydantic
    print("\n示範按需轉換為 Pydantic:")
    counter_map = storage.state["counter"]
    counter_pydantic = to_pydantic(counter_map, CounterState)
    # counter_pydantic = to_pydantic(counter_map, CounterStateModel)
    print(f"最終 Pydantic 狀態: {counter_pydantic}")
    print(f"count: {counter_pydantic.count}")
