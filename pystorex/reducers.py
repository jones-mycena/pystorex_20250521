"""
基於 PyStoreX 的 Reducer 定義模組。

此模組提供建立和管理 Reducer 的功能。Reducers 是純函數，
負責根據接收到的 Action 將當前狀態轉換為新狀態。
"""

from typing import Dict, Any, Callable, Union, Tuple, Optional, overload, cast

import collections
from immutables import Map
from pydantic import BaseModel

from pystorex.immutable_utils import to_immutable
from .actions import Action,init_store, update_reducer
from .types import (
    S,
    P,
    ActionHandler,
    HandlerMap,
    ReducerFunction,
    Reducer as ReducerProtocol,
)

from .action_handlers import FunctionActionHandler

# 使用類型模組中定義的 ReducerFunction 類型
Reducer = ReducerFunction

def create_reducer_from_function_handler(handler: FunctionActionHandler[S]) -> ReducerFunction[S]:
    """
    從 FunctionActionHandler 創建一個 reducer 函數。
    
    Args:
        handler: FunctionActionHandler 實例
        
    Returns:
        一個符合 ReducerFunction 接口的 reducer 函數
        
    範例:
        ```python
        # 創建 FunctionActionHandler
        handler = create_handler(initial_state)
        
        @handler.register("increment")
        def handle_increment(state, action):
            return state.set("count", state["count"] + 1)
            
        @handler.register("decrement")
        def handle_decrement(state, action):
            return state.set("count", state["count"] - 1)
            
        # 從 handler 創建 reducer
        counter_reducer = create_reducer_from_function_handler(handler)
        ```
    """
    def reducer(state: S = handler.initial_state, action: Optional[Action[Any]] = None) -> S:
        if action is None:
            return state
            
        # 檢查是否為未知的 action type，且不在忽略清單中
        if (hasattr(handler, "has_handler") and 
            not handler.has_handler(action.type) and 
            hasattr(reducer, "_log_unknown") and 
            action.type not in [a.type for a in reducer._ignored_actions]):
            print(f"Warning: Handling unknown action type: {action.type}")
            
        result = handler(state, action)
        
        # 如果結果和輸入相同，直接返回，避免不必要的轉換
        if result is state:
            return state
            
        # 確保結果是不可變的 Map
        if isinstance(result, Map):
            return result
        else:
            # 如果 handler 返回了非 Map 對象，統一轉換
            return to_immutable(result)
    
    # 設定 reducer 的元資料
    reducer.initial_state = handler.initial_state  # type: ignore
    reducer.original_type = None  # type: ignore
    reducer.handlers = {}  # type: ignore  # 我們不再使用 handlers 字典
    # 添加日誌控制標誌
    reducer._log_unknown = False  # type: ignore
    reducer._ignored_actions = [init_store, update_reducer]  # type: ignore
    
    return reducer


def create_reducer(
    initial_state: S,
    *handlers: Union[Tuple[str, ActionHandler], Dict[str, ActionHandler]],
) -> ReducerFunction[S]:
    """
    創建一個 reducer 函式，使用 defaultdict 簡化狀態管理。

    Args:
        initial_state: 初始狀態。
        *handlers: 一系列 (action_type, handler_fn) 元組或使用 on 函式創建的處理器。

    Returns:
        一個 reducer 函式，根據 action 的類型執行對應的處理邏輯。

    範例:
        >>> # 創建一個計數器 reducer
        >>> increment = create_action("[Counter] Increment")
        >>> decrement = create_action("[Counter] Decrement")
        >>> reset = create_action("[Counter] Reset")
        >>>
        >>> counter_reducer = create_reducer(
        ...     0,  # 初始狀態
        ...     on(increment, lambda state, action: state + 1),
        ...     on(decrement, lambda state, action: state - 1),
        ...     on(reset, lambda state, action: 0)
        ... )
    """
    # 使用 defaultdict 處理未知的 action 類型，預設返回原始狀態
    action_handlers = collections.defaultdict(
        # 預設處理器，當找不到對應的 action.type 時使用
        lambda: lambda state, _: state
    )

    # 記錄原始類型以便在需要時轉換回來
    original_type = (
        initial_state.__class__ if isinstance(initial_state, BaseModel) else None
    )

    # 轉換初始狀態為不可變 Map
    immutable_initial_state = to_immutable(initial_state)

    # 處理傳入的 handlers
    for handler in handlers:
        if isinstance(handler, tuple) and len(handler) == 2:
            action_type, handler_fn = handler
            action_handlers[action_type] = handler_fn
        else:
            action_handlers.update(cast(Dict[str, ActionHandler], handler))

    def reducer(state: S = initial_state, action: Optional[Action[Any]] = None) -> S:
        """
        Reducer 函式，根據 action 處理狀態變更。

        Args:
            state: 當前狀態，默認為初始狀態。
            action: 要處理的 action，默認為 None。

        Returns:
            新的狀態，如果沒有對應的處理器則返回原狀態。
        """
        if action is None:
            return state
        # 檢查是否為未知的 action type，且不在忽略清單中
        if (action.type not in action_handlers.keys() and 
            hasattr(reducer, "_log_unknown") and 
            action.type not in [a.type for a in reducer._ignored_actions]):
            print(f"Warning: Handling unknown action type: {action.type}")

        # 使用 defaultdict 直接獲取處理器，不需要額外的檢查
        handler = action_handlers[action.type]

        # 調用 handler 獲取結果
        result = handler(state, action)

        # 如果結果和輸入相同，直接返回，避免不必要的轉換
        if result is state:
            return state
        # 確保結果是不可變的 Map
        if isinstance(result, Map):
            return result
        else:
            # 如果 handler 返回了非 Map 對象 (例如 Pydantic 或字典)，統一轉換
            return to_immutable(result)

    # 設定 reducer 的元資料
    reducer.initial_state = immutable_initial_state  # type: ignore
    reducer.original_type = original_type  # type: ignore
    reducer.handlers = dict(action_handlers)  # type: ignore 轉換為普通字典以保持兼容性
    reducer._ignored_actions = [init_store, update_reducer]  # type: ignore

    return reducer


@overload
def on(
    action_creator: Callable[..., Action[P]], handler: Callable[[S, Action[P]], S]
) -> Dict[str, ActionHandler]: ...


@overload
def on(
    action_type: str, handler: Callable[[S, Action[Any]], S]
) -> Dict[str, ActionHandler]: ...


def on(
    action_creator_or_type: Union[Callable[..., Action[Any]], str],
    handler: Callable[[S, Action[Any]], S],
) -> Dict[str, ActionHandler]:
    """
    創建一個 action 類型與處理函式的映射，同時包裝 handler 以只處理特定類型的 action。

    Args:
        action_creator_or_type: Action 創建器函式或 Action 類型字串。
        handler: 處理該 Action 的函式，接收 (state, action) 並返回新狀態。

    Returns:
        一個包含 {action_type: wrapped_handler} 的字典。
    """
    if callable(action_creator_or_type) and hasattr(action_creator_or_type, "type"):
        # 如果是 action 創建器函式，則提取其類型
        action_type = action_creator_or_type.type
    else:
        # 否則直接將其轉為字串作為類型
        action_type = str(action_creator_or_type)

    # 包裝 handler 以便它只處理特定類型的 action
    def wrapped_handler(state: S, action: Action[Any]) -> S:
        # 由於 reducer 已經檢查了 action.type，這裡其實可以不再檢查
        # 但為了安全起見，再檢查一次也無妨
        if action.type == action_type:
            return handler(state, action)
        return state

    return {action_type: wrapped_handler}


class ReducerManager:
    """
    管理應用中的所有 reducers，類似於 NgRx 的 MetaReducer。

    Attributes:
        _feature_reducers: 儲存每個功能模組的 reducer。
        _state: 儲存最新的整個 root state。
    """

    def __init__(self) -> None:
        """
        初始化 ReducerManager，創建空的 reducers 和狀態儲存。
        """
        self._feature_reducers: Dict[str, ReducerFunction] = (
            {}
        )  # 儲存功能模組的 reducers
        self._state: Dict[str, Any] = {}  # 儲存最新的 root state

    def add_reducer(self, feature_key: str, reducer: ReducerFunction) -> None:
        """
        添加一個 reducer 到指定的功能模組。

        Args:
            feature_key: 功能模組的鍵。
            reducer: 要添加的 reducer 函式。
        """
        self._feature_reducers[feature_key] = reducer
        self._state[feature_key] = reducer.initial_state  # type: ignore  # 初始化該功能模組的狀態

    def add_reducers(self, reducers: Dict[str, ReducerFunction]) -> None:
        """
        批量添加 reducers。

        Args:
            reducers: 包含功能模組鍵與 reducer 的字典。
        """
        for key, r in reducers.items():
            self.add_reducer(key, r)

    def remove_reducer(self, feature_key: str) -> None:
        """
        移除指定功能模組的 reducer。

        Args:
            feature_key: 要移除的功能模組鍵。
        """
        if feature_key in self._feature_reducers:
            del self._feature_reducers[feature_key]
            del self._state[feature_key]

    def get_reducers(self) -> Dict[str, ReducerFunction]:
        """
        獲取當前所有的 reducers。

        Returns:
            一個包含所有功能模組鍵與 reducer 的字典。
        """
        return self._feature_reducers.copy()

    def reduce(
        self,
        state: Optional[Union[Dict[str, Any], Map]] = None,
        action: Optional[Action[Any]] = None,
    ) -> Map:
        """
        使用所有註冊的 reducers 處理 action 並返回新狀態。

        Args:
            state: 當前的 root state，默認為 None。
            action: 要處理的 action，默認為 None。

        Returns:
            新的 root state (Map)。
        """
        if state is None:
            state = self._state  # 如果 state 為 None，使用內部的 _state

        # 確保 state 是 Map
        if not isinstance(state, Map):
            # 如果不是 Map，則轉換為 Map
            state_map = Map(state)
        else:
            state_map = state

        # 創建 Map 的可變 evolver
        evolver = state_map.mutate()

        for feature_key, reducer in self._feature_reducers.items():
            # 獲取當前功能模組的狀態，若不存在則使用初始狀態
            prev_substate = state_map.get(feature_key, reducer.initial_state)  # type: ignore
            next_substate = reducer(prev_substate, action)  # 使用 reducer 處理 action

            if next_substate is not prev_substate:
                # 如果狀態有變化，更新到 evolver
                evolver[feature_key] = next_substate

        # 完成所有更改並生成新的 Map
        result_map = evolver.finish()
        self._state = result_map  # 保存最新的 root state
        return result_map
