import time
import copy
from typing import Callable, Any

def create_selector(*selectors: Callable[[Any], Any], result_fn: Callable = None, deep: bool = False, ttl: float = None):
    """
    創建一個複合選擇器，支援 shallow/deep 比較與 TTL 快取控制

    Args:
        *selectors: 多個輸入選擇器
        result_fn: 處理輸出結果的函數
        deep: 是否進行深度比較（預設為 False）
        ttl: 快取有效時間（秒），預設為無限

    Returns:
        經過快取優化的 selector 函數
    """
    if not result_fn and len(selectors) == 1:
        return selectors[0]

    if not result_fn:
        result_fn = lambda *args: args

    last_inputs = None
    last_output = None
    last_time = None

    def selector(state):
        nonlocal last_inputs, last_output, last_time

        # 處理 state 為 (old, new) 的元組情況
        if isinstance(state, tuple) and len(state) == 2:
            _, new_state = state
        else:
            new_state = state

        inputs = tuple(select(new_state) for select in selectors)

        # 時間控制
        now = time.time()
        expired = (ttl is not None and last_time is not None and (now - last_time) > ttl)

        # 比較
        if not expired and last_inputs is not None:
            if deep:
                same = inputs == last_inputs
            else:
                same = all(i is j for i, j in zip(inputs, last_inputs))
            if same:
                return last_output

        # 執行計算
        computed_inputs = copy.deepcopy(inputs) if deep else inputs
        last_output = result_fn(*computed_inputs)
        last_inputs = copy.deepcopy(inputs) if deep else inputs
        last_time = now
        return last_output

    return selector
