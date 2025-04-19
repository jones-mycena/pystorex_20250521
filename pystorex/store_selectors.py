import time
import copy
from typing import Callable, Any

def create_selector(*selectors: Callable[[Any], Any], result_fn: Callable = None, deep: bool = False, ttl: float = None):
    """
    創建一個複合選擇器，支援 shallow/deep 比較與 TTL 快取控制

    Args:
        *selectors: 多個輸入選擇器，這些函數會從 state 中提取對應的值
        result_fn: 處理輸出結果的函數，將多個選擇器的輸出進行處理
        deep: 是否進行深度比較（預設為 False），深度比較會檢查值的內容是否相等
        ttl: 快取有效時間（秒），若超過此時間則重新計算，預設為無限

    Returns:
        經過快取優化的 selector 函數
    """
    # 如果沒有 result_fn 且只有一個選擇器，直接返回該選擇器
    if not result_fn and len(selectors) == 1:
        return selectors[0]

    # 如果沒有提供 result_fn，預設為返回所有輸入值的函數
    if not result_fn:
        result_fn = lambda *args: args

    # 初始化快取相關變數
    last_inputs = None  # 上一次的輸入值
    last_output = None  # 上一次的輸出結果
    last_time = None    # 上一次計算的時間

    def selector(state):
        """
        經過快取優化的選擇器函數

        Args:
            state: 當前的狀態，可以是單一狀態或 (old, new) 的元組

        Returns:
            計算結果，可能來自快取或重新計算
        """
        nonlocal last_inputs, last_output, last_time

        # 處理 state 為 (old, new) 的元組情況，僅使用新狀態
        if isinstance(state, tuple) and len(state) == 2:
            _, new_state = state
        else:
            new_state = state

        # 執行所有選擇器，提取輸入值
        inputs = tuple(select(new_state) for select in selectors)

        # 時間控制：檢查快取是否過期
        now = time.time()
        expired = (ttl is not None and last_time is not None and (now - last_time) > ttl)

        # 比較輸入值是否與上次相同
        if not expired and last_inputs is not None:
            if deep:
                # 深度比較：檢查值的內容是否相等
                same = inputs == last_inputs
            else:
                # 淺層比較：檢查是否為同一物件
                same = all(i is j for i, j in zip(inputs, last_inputs))
            if same:
                # 如果輸入值相同且未過期，直接返回快取的輸出結果
                return last_output

        # 執行計算
        # 如果是深度比較，複製輸入值以避免修改原始資料
        computed_inputs = copy.deepcopy(inputs) if deep else inputs
        # 使用 result_fn 計算輸出結果
        last_output = result_fn(*computed_inputs)
        # 更新快取
        last_inputs = copy.deepcopy(inputs) if deep else inputs
        last_time = now
        return last_output

    return selector
