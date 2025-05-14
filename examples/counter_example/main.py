from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json
import time
from counter_store import store
from counter_actions import (
    increment,
    increment_by,
    decrement,
    reset,
    load_count_request,
    count_warning,
)
from counter_selectors import get_count, get_counter_info
from counter_reducers import CounterState
from pystorex.actions import update_reducer
from pystorex.immutable_utils import to_dict, to_pydantic

if __name__ == "__main__":

    # store._action_subject.subscribe(
    #     on_next=lambda action: print(
    #         f"分發動作: {action.type} - 负载: {action.payload}"
    #     )
    # )
    # 新增 selector 監控 count 並在超過閾值時發出警告
    def count_warning_monitor(value_tuple):
        old_value, new_value = value_tuple
        print(f"计数变化: {old_value} -> {new_value}")
        # if new_value > 8 and (old_value <= 8 or old_value is None):
        if new_value > 8 and old_value != new_value:
            store.dispatch(count_warning(new_value))

    # 訂閱狀態變化
    store.select(get_count).subscribe(count_warning_monitor)

    store.select(get_counter_info).subscribe(
        on_next=lambda info_tuple: print(f"計數器信息更新: {to_dict(info_tuple)}")
    )

    # 分發actions
    print("\n==== 開始測試基本操作 ====")
    store.dispatch(update_reducer())
    store.dispatch(increment())
    store.dispatch(increment_by(5))
    store.dispatch(decrement())
    store.dispatch(reset(10))
    store.dispatch(increment_by(99))
    store.dispatch(update_reducer())

    # 觸發異步action
    print("\n==== 開始測試異步操作 ====")
    store.dispatch(load_count_request())

    # 保持程序運行，以便觀察異步效果
    time.sleep(2)

    # 打印最終狀態
    print("\n==== 最終狀態 ====")
    counter_state_map = store.state["counter"]
    counter_state_dict = to_dict(counter_state_map)
    counter_state_pydantic = to_pydantic(counter_state_map, CounterState)
    print(f"Counter dict: {counter_state_dict}")
    print(f"Counter pydantic: {counter_state_pydantic}")
