import time
import copy
import functools
from typing import Callable, Any, List, Optional, Tuple, cast, overload
from .types import (
    Input, Output, R, StateSelector, ResultSelector, 
    MemoizedSelector, SelectorCreator1, SelectorCreatorN
)

@overload
def create_selector(selector: StateSelector[Input, Output], *, deep: bool = False, ttl: Optional[float] = None, maxsize: int = 128) -> StateSelector[Input, Output]:
    """單一選擇器重載"""
    ...

@overload
def create_selector(*selectors: StateSelector[Input, Any], result_fn: ResultSelector[R], deep: bool = False, ttl: Optional[float] = None, maxsize: int = 128) -> StateSelector[Input, R]:
    """組合多個選擇器重載"""
    ...

def create_selector(*selectors: Callable[[Any], Any], result_fn: Optional[Callable[..., Any]] = None, deep: bool = False, ttl: Optional[float] = None, maxsize: int = 128) -> MemoizedSelector:
    """
    創建一個複合選擇器，支援記憶化、深淺比較與TTL控制

    Args:
        *selectors: 多個輸入選擇器，這些函數會從 state 中提取對應的值
        result_fn: 處理輸出結果的函數，將多個選擇器的輸出進行處理
        deep: 是否進行深度比較（預設為 False）
        ttl: 快取有效時間（秒），若超過此時間則重新計算，預設為無限
        maxsize: 緩存的最大條目數，預設為128

    Returns:
        經過快取優化的 selector 函數
    """
    # 如果沒有 result_fn 且只有一個選擇器，直接返回該選擇器
    if not result_fn and len(selectors) == 1:
        return selectors[0]

    # 如果沒有提供 result_fn，預設為返回所有輸入值的函數
    if not result_fn:
        result_fn = lambda *args: args
    
    # 使用簡單的緩存列表
    cache = []
    last_result = None
    
    def selector(state: Any) -> Any:
        """
        經過快取優化的選擇器函數

        Args:
            state: 當前的狀態，可以是單一狀態或 (old, new) 的元組

        Returns:
            計算結果，可能來自快取或重新計算
        """
        nonlocal cache, last_result
        
        try:
            # 處理 state 為 (old, new) 的元組情況，僅使用新狀態
            if isinstance(state, tuple) and len(state) == 2:
                _, new_state = state
            else:
                new_state = state

            # 執行所有選擇器，提取輸入值
            try:
                inputs = []
                for select in selectors:
                    try:
                        result = select(new_state)
                        inputs.append(result)
                    except Exception as e:
                        print(f"選擇器輸入錯誤: {e}")
                        inputs.append(None)
                inputs = tuple(inputs)
            except Exception as e:
                print(f"選擇器輸入處理錯誤: {e}")
                return last_result if last_result is not None else None
            
            now = time.time()
            
            # 管理緩存
            if ttl is not None:
                # 清除過期項
                cache = [item for item in cache if now - item[0] <= ttl]
            
            # 維護緩存大小
            while len(cache) >= maxsize:
                cache.pop(0)
            
            # 尋找緩存匹配
            for timestamp, cached_inputs, cached_result in cache:
                matched = False
                try:
                    if deep:
                        # 嘗試深度比較,使用安全的方法
                        matched = _safe_deep_equals(inputs, cached_inputs)
                    else:
                        # 標準淺比較
                        matched = all(a is b for a, b in zip(inputs, cached_inputs))
                except Exception:
                    matched = False
                
                if matched:
                    return cached_result
            
            # 緩存未命中，計算新結果
            try:
                result = result_fn(*inputs)
                cache.append((now, inputs, result))
                last_result = result
                return result
            except Exception as e:
                print(f"選擇器計算錯誤: {e}")
                return last_result if last_result is not None else None
                
        except Exception as e:
            print(f"選擇器執行總體錯誤: {e}")
            return last_result if last_result is not None else None
    
    # 添加緩存管理方法
    def cache_info():
        return (0, 0, maxsize, len(cache))
    
    def cache_clear():
        nonlocal cache
        cache.clear()
    
    selector.cache_info = cache_info  # type: ignore
    selector.cache_clear = cache_clear  # type: ignore
    
    return selector

def _safe_deep_equals(a: Any, b: Any) -> bool:
    """安全的深度比較，出錯時返回False"""
    try:
        if a is b:
            return True
        if type(a) != type(b):
            return False
        if isinstance(a, (str, int, float, bool, type(None))):
            return a == b
        if isinstance(a, dict):
            if len(a) != len(b):
                return False
            for key in a:
                if key not in b or not _safe_deep_equals(a[key], b[key]):
                    return False
            return True
        if isinstance(a, (list, tuple)):
            if len(a) != len(b):
                return False
            return all(_safe_deep_equals(x, y) for x, y in zip(a, b))
        return a == b
    except Exception:
        return False