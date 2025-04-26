import sys
sys.path.append(r"c:\work\pystorex")

import json
import time
from counter_store import store
from counter_actions import increment, increment_by, decrement, reset, load_count_request
from counter_selectors import get_count, get_counter_info

if __name__ == "__main__":
    # 訂閱狀態變化
    store.select(get_count).subscribe(
        on_next=lambda t: print(f"计数变化: {t[0]} -> {t[1]}")
    )


    store.select(get_counter_info).subscribe(
        on_next=lambda info_tuple: print(
            f"計數器信息更新: {json.dumps(info_tuple[1], ensure_ascii=False, indent=2)}"
        )
    )

    # 分發actions
    print("\n==== 開始測試基本操作 ====")
    store.dispatch(increment())  
    store.dispatch(increment_by(5))
    store.dispatch(decrement())  
    store.dispatch(reset(10))
    store.dispatch(increment_by(99))  

    # 觸發異步action
    print("\n==== 開始測試異步操作 ====")
    store.dispatch(load_count_request())

    # 保持程序運行，以便觀察異步效果
    time.sleep(2)

    # 打印最終狀態
    print("\n==== 最終狀態 ====")
    print(store.state)
