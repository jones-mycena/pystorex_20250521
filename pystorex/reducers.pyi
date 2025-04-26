"""
PyStoreX Reducers 模組的類型存根文件。
提供高精度的類型提示，無實際執行代碼。
"""

from typing import Dict, Any, Callable, Union, Tuple, Optional, overload
from .actions import Action
from .types import (
    S, P, ActionHandler, HandlerMap, ReducerFunction, 
    Reducer as ReducerProtocol
)

# 使用類型模組中定義的 ReducerFunction 類型
Reducer = ReducerFunction

def create_reducer(initial_state: S, *handlers: Union[Tuple[str, ActionHandler], Dict[str, ActionHandler]]) -> ReducerFunction[S]: ...

@overload
def on(action_creator: Callable[..., Action[P]], handler: Callable[[S, Action[P]], S]) -> Dict[str, ActionHandler]: ...

@overload
def on(action_type: str, handler: Callable[[S, Action[Any]], S]) -> Dict[str, ActionHandler]: ...

def on(action_creator_or_type: Union[Callable[..., Action[Any]], str], handler: Callable[[S, Action[Any]], S]) -> Dict[str, ActionHandler]: ...

class ReducerManager:
    """管理所有 reducers 的類。"""
    
    _feature_reducers: Dict[str, ReducerFunction]
    _state: Dict[str, Any]
    
    def __init__(self) -> None: ...
    
    def add_reducer(self, feature_key: str, reducer: ReducerFunction) -> None: ...
    
    def add_reducers(self, reducers: Dict[str, ReducerFunction]) -> None: ...
    
    def remove_reducer(self, feature_key: str) -> None: ...
    
    def get_reducers(self) -> Dict[str, ReducerFunction]: ...
    
    def reduce(self, state: Optional[Dict[str, Any]] = None, action: Optional[Action[Any]] = None) -> Dict[str, Any]: ...