import sys
sys.path.append(r"c:\work\pystorex")
import time
from typing import Optional
from pydantic import BaseModel
from reactivex import operators as ops

from pystorex.actions import create_action
from pystorex import create_store, create_reducer, on, create_effect
from pystorex.store_selectors import create_selector
from pystorex.middleware import LoggerMiddleware  # 假設已實作

# ====== 1. 定義狀態模型 ======
class CounterState(BaseModel):
    count: int = 0
    loading: bool = False
    error: Optional[str] = None
    last_updated: Optional[float] = None

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
def counter_handler(state: CounterState, action) -> CounterState:
    # 使用 Pydantic deep copy 確保 immutable。
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

# ====== 4. 定義 Effects ======
class CounterEffects:
    @create_effect
    def load_count(self, action_stream):
        """模擬從 API 載入數據的副作用，成功後 dispatch load_count_success"""
        return action_stream.pipe(
            ops.filter(lambda action: action.type == load_count_request.type),
            ops.do_action(lambda _: print("Effect: Loading counter...")),
            ops.delay(1.0),  # 延遲 1 秒
            ops.map(lambda _: load_count_success(42))  # 假設 API 回傳 42
        )

    @create_effect(dispatch=False)
    def log_actions(self, action_stream):
        """只做日誌，不 dispatch 新 action"""
        return action_stream.pipe(
            ops.do_action(lambda action: print(f"[Log] Action: {action.type}")),
            ops.filter(lambda _: False)
        )
        
    @create_effect(dispatch=False)
    def handle_count_warning(self, action_stream):
        """處理計數器過高的警告"""
        return action_stream.pipe(
            ops.filter(lambda action: action.type == count_warning.type),
            ops.do_action(lambda action: print(f"[Warning] 計數器超過閾值! 目前值: {action.payload}")),
            ops.filter(lambda _: False)
        )

# ====== 5. 建立 Store、註冊模組 ======
storage = create_store()
storage.apply_middleware(LoggerMiddleware)
storage.register_root({"counter": counter_reducer})
storage.register_effects(CounterEffects)

# ====== 6. 訂閱狀態與測試 ======
# 監聽完整 state
storage.select().subscribe(lambda s: print(f"State changed: {s[1]}"))
# 監聽 count 值
get_counter_state = lambda state: state["counter"]
get_count = create_selector(
    get_counter_state, result_fn=lambda counter: counter.count or 0
)
storage.select(get_count).subscribe(lambda c: print(f"Count: {c}"))

# 新增 selector 監控 count 並在超過閾值時發出警告
def count_warning_monitor(value_tuple):
    old_value, new_value = value_tuple
    if new_value > 8 and (old_value <= 8 or old_value is None):
        storage.dispatch(count_warning(new_value))

storage.select(get_count).subscribe(count_warning_monitor)

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