"""
基於 functools.singledispatch 的 Action 處理模塊。

此模塊提供更優雅的 Action 處理方式，使用 Python 的多分派機制根據 Action 類型
自動選擇正確的處理函數，簡化 reducer 的編寫和維護。
"""

import functools
from typing import Any, Dict, Callable, Optional, Type, TypeVar, Generic, get_type_hints, Set
from typing_extensions import TypedDict
from immutables import Map
from .actions import Action
from .immutable_utils import to_immutable

S = TypeVar('S', bound=TypedDict)  # type: ignore  狀態類型，限制為 TypedDict
P = TypeVar('P')  # 負載類型

class FunctionActionHandler(Generic[S]):
    """
    基於 singledispatch 的 Action 處理器類。
    
    使用 Python 的多分派機制，根據 Action 類型自動選擇正確的處理函數。
    這允許您以更直觀的方式為每種 Action 類型定義專門的處理邏輯。
    """
    
    def __init__(self, initial_state: S):
        """
        初始化 ActionHandler。
        
        Args:
            initial_state: 初始狀態
        """
        self.initial_state = to_immutable(initial_state)
        self._handler = functools.singledispatch(self._default_handler)
        self._registered_types: Set[str] = set()  # 記錄已註冊的 action 類型
    
    def _default_handler(self, state: S, action: Action[Any]) -> S:
        """
        默認的 Action 處理函數，當沒有找到匹配的處理器時調用。
        
        Args:
            state: 當前狀態
            action: 要處理的 Action
            
        Returns:
            不變的原始狀態
        """
        return state
    
    def register(self, action_type: str):
        """
        裝飾器：註冊特定 Action 類型的處理函數。
        
        Args:
            action_type: Action 的類型字符串
            
        Returns:
            裝飾器函數
            
        用法:
            ```python
            handler = FunctionActionHandler(initial_state)
            
            @handler.register("increment")
            def handle_increment(state, action):
                return state.set("count", state["count"] + 1)
            ```
        """
        def decorator(func: Callable[[S, Action[P]], S]):
            # 記錄已註冊的 action 類型
            self._registered_types.add(action_type)
            
            # 創建 Action 類型的子類，以便 singledispatch 能夠基於類型分派
            action_class = type(f"Action_{action_type}", (Action,), {"__slots__": ()})
            
            # 包裝處理函數，確保只有在 action.type 匹配時才調用
            @functools.wraps(func)
            def wrapper(state: S, action: Action[P]) -> S:
                if action.type == action_type:
                    result = func(state, action)
                    # 確保結果是不可變的 Map
                    if result is state:
                        return state
                    if isinstance(result, Map):
                        return result
                    return to_immutable(result)
                return state
            
            # 註冊到 singledispatch
            self._handler.register(action_class, wrapper)
            return func
        return decorator
    
    def has_handler(self, action_type: str) -> bool:
        """
        檢查是否註冊了特定 action type 的處理函數。
        
        Args:
            action_type: 要檢查的 action 類型
            
        Returns:
            如果註冊了處理函數則返回 True，否則返回 False
        """
        return action_type in self._registered_types
    
    def __call__(self, state: S, action: Action[P]) -> S:
        """
        處理 Action，調用匹配的處理函數。
        
        Args:
            state: 當前狀態
            action: 要處理的 Action
            
        Returns:
            新的狀態
        """
        # 使用 has_handler 快速檢查是否有匹配的處理函數
        if self.has_handler(action.type):
            action_class = next(
                cls for cls in self._handler.registry.keys()
                if isinstance(cls, type) and issubclass(cls, Action) and cls.__name__ == f"Action_{action.type}"
            )
            result = self._handler.dispatch(action_class)(state, action)
        else:
            # 沒有找到匹配的處理函數，使用默認處理器
            result = self._default_handler(state, action)
            
        # 確保結果是不可變的 Map
        if result is state:
            return state
        if isinstance(result, Map):
            return result
        return to_immutable(result)

def create_function_handler(initial_state: S) -> FunctionActionHandler[S]:
    """
    創建一個 FunctionActionHandler 實例。
    
    Args:
        initial_state: 初始狀態
        
    Returns:
        新的 FunctionActionHandler 實例
    """
    return FunctionActionHandler(initial_state)


class TypedActionHandler(Generic[S]):
    """
    支持強類型的 Action 處理器，專為 TypedDict 設計。
    提供類型安全和更好的 IDE 支持。
    """
    
    def __init__(self, state_type: Type[S], initial_values: Optional[Dict[str, Any]] = None):
        """
        初始化 TypedActionHandler。
        
        Args:
            state_type: 狀態的 TypedDict 類型
            initial_values: 初始值字典，可選
        """
        self._state_type = state_type
        initial_values = initial_values or {}
        
        # 從 TypedDict 中獲取所有字段
        type_hints = get_type_hints(state_type)
        
        # 創建初始狀態
        self._initial_state = {}
        for field in type_hints:
            # 優先使用提供的初始值，否則使用 None
            self._initial_state[field] = initial_values.get(field, None)
        
        # 轉為不可變 Map
        self._initial_state_map = to_immutable(self._initial_state)
        
        # 初始化處理器
        self._handlers = {}
    
    def register(self, action_type: str):
        """
        裝飾器：註冊特定 Action 類型的處理函數。
        
        Args:
            action_type: Action 的類型字符串
            
        Returns:
            裝飾器函數
        """
        def decorator(handler_fn):
            self._handlers[action_type] = handler_fn
            return handler_fn
        return decorator
    
    def has_handler(self, action_type: str) -> bool:
        """
        檢查是否註冊了特定 action type 的處理函數。
        
        Args:
            action_type: 要檢查的 action 類型
            
        Returns:
            如果註冊了處理函數則返回 True，否則返回 False
        """
        return action_type in self._handlers
    
    def __call__(self, state: Map, action: Action[P]) -> Map:
        """
        處理 Action，調用匹配的處理函數。
        
        Args:
            state: 當前狀態 (Map)
            action: 要處理的 Action
            
        Returns:
            新的狀態 (Map)
        """
        handler = self._handlers.get(action.type)
        if handler:
            result = handler(state, action)
            # 確保結果是不可變的 Map
            if result is state:
                return state
            if isinstance(result, Map):
                return result
            return to_immutable(result)
        return state
    
    @property
    def initial_state(self) -> Map:
        """獲取初始狀態 (Map)。"""
        return self._initial_state_map
    
    @property
    def handlers(self) -> Dict[str, Any]:
        """獲取所有註冊的處理函數。"""
        return self._handlers.copy()


def create_typed_handler(state_type: Type[S], initial_values: Optional[Dict[str, Any]] = None) -> TypedActionHandler[S]:
    """
    創建一個 TypedActionHandler 實例。
    
    Args:
        state_type: 狀態的 TypedDict 類型
        initial_values: 初始值字典，可選
        
    Returns:
        新的 TypedActionHandler 實例
    """
    return TypedActionHandler(state_type, initial_values)