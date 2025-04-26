"""
基於 PyStoreX 的選擇器定義模組。

此模組提供創建具有記憶功能的選擇器，可以從 Store 狀態中高效地選擇資料。
選擇器會記住上次的計算結果，只有當輸入變化時才重新計算，避免不必要的性能損耗。
"""

import time
import copy
from typing import Callable, Any, List, Optional, Tuple, cast, overload
from .types import (
    Input, Output, R, StateSelector, ResultSelector, 
    MemoizedSelector, SelectorCreator1, SelectorCreatorN
)

@overload
def create_selector(selector: StateSelector[Input, Output], *, deep: bool = False, ttl: Optional[float] = None) -> StateSelector[Input, Output]:
    """單一選擇器重載"""
    ...

@overload
def create_selector(*selectors: StateSelector[Input, Any], result_fn: ResultSelector[R], deep: bool = False, ttl: Optional[float] = None) -> StateSelector[Input, R]:
    """組合多個選擇器重載"""
    ...

def create_selector(*selectors: Callable[[Any], Any], result_fn: Optional[Callable[..., Any]] = None, deep: bool = False, ttl: Optional[float] = None) -> MemoizedSelector:
    """
    創建一個複合選擇器，支援 shallow/deep 比較與 TTL 快取控制

    Args:
        *selectors: 多個輸入選擇器，這些函數會從 state 中提取對應的值
        result_fn: 處理輸出結果的函數，將多個選擇器的輸出進行處理
        deep: 是否進行深度比較（預設為 False），深度比較會檢查值的內容是否相等
        ttl: 快取有效時間（秒），若超過此時間則重新計算，預設為無限

    Returns:
        經過快取優化的 selector 函數
        
    範例:
        ```python
        # 簡單選擇器，從狀態中選擇計數器值
        get_counter = lambda state: state["counter"]
        
        # 衍生選擇器，計算計數器的平方
        get_counter_squared = create_selector(
            get_counter,
            result_fn=lambda counter: counter ** 2
        )
        
        # 組合多個選擇器
        get_user = lambda state: state["user"]
        get_items = lambda state: state["items"]
        
        # 計算用戶權限內的項目
        get_allowed_items = create_selector(
            get_user,
            get_items,
            result_fn=lambda user, items: [
                item for item in items 
                if user["role"] in item["allowed_roles"]
            ]
        )
        
        # 使用深度比較和快取超時
        expensive_selector = create_selector(
            get_complex_data,
            result_fn=lambda data: perform_expensive_calculation(data),
            deep=True,  # 對象內容變化時重新計算
            ttl=300  # 最多 5 分鐘快取
        )
        ```
    """
    # 如果沒有 result_fn 且只有一個選擇器，直接返回該選擇器
    if not result_fn and len(selectors) == 1:
        return selectors[0]

    # 如果沒有提供 result_fn，預設為返回所有輸入值的函數
    if not result_fn:
        result_fn = lambda *args: args

    # 初始化快取相關變數
    last_inputs: Any = None  # 上一次的輸入值
    last_output: Any = None  # 上一次的輸出結果
    last_time: Optional[float] = None    # 上一次計算的時間

    def selector(state: Any) -> Any:
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