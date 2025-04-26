"""
PyStoreX Middleware 模組的類型存根文件。
提供高精度的類型提示，無實際執行代碼。
"""

from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from threading import Lock, Timer
from .actions import Action, create_action
from .types import (
    NextDispatch, MiddlewareFactory, MiddlewareFunction, DispatchFunction, 
    Store, ThunkFunction, GetState, Middleware as MiddlewareProtocol
)

# ———— Base Middleware ————
class BaseMiddleware:
    """基礎中介類，定義所有中介可能實現的鉤子。"""
    
    def on_next(self, action: Action[Any], prev_state: Any) -> None: ...
    def on_complete(self, next_state: Any, action: Action[Any]) -> None: ...
    def on_error(self, error: Exception, action: Action[Any]) -> None: ...

# ———— LoggerMiddleware ————
class LoggerMiddleware(BaseMiddleware, MiddlewareProtocol):
    """日誌中介，打印每個 action 發送前和發送後的 state。"""
    
    def on_next(self, action: Action[Any], prev_state: Any) -> None: ...
    def on_complete(self, next_state: Any, action: Action[Any]) -> None: ...
    def on_error(self, error: Exception, action: Action[Any]) -> None: ...

# ———— ThunkMiddleware ————
class ThunkMiddleware(BaseMiddleware, MiddlewareProtocol):
    """支援 dispatch 函數 (thunk)，可以在 thunk 內執行非同步邏輯或多次 dispatch。"""
    
    def __call__(self, store: Store[Any]) -> MiddlewareFunction: ...

# ———— AwaitableMiddleware ————
class AwaitableMiddleware(BaseMiddleware, MiddlewareProtocol):
    """支援 dispatch coroutine/awaitable，完成後自動 dispatch 返回值。"""
    
    def __call__(self, store: Store[Any]) -> MiddlewareFunction: ...

# ———— ErrorMiddleware ————
global_error: Callable[[Dict[str, Any]], Action[Dict[str, Any]]]

class ErrorMiddleware(BaseMiddleware, MiddlewareProtocol):
    """捕獲 dispatch 過程中的異常，dispatch 全域錯誤 Action。"""
    
    def __call__(self, store: Store[Any]) -> MiddlewareFunction: ...

# ———— ImmutableEnforceMiddleware ————
def _deep_freeze(obj: Any) -> Any: ...

class ImmutableEnforceMiddleware(BaseMiddleware, MiddlewareProtocol):
    """在 on_complete 時深度凍結 next_state。"""
    
    def on_complete(self, next_state: Any, action: Action[Any]) -> None: ...

# ———— PersistMiddleware ————
class PersistMiddleware(BaseMiddleware, MiddlewareProtocol):
    """自動持久化指定 keys 的子 state 到檔案，支援重啟恢復。"""
    
    filepath: str
    keys: List[str]
    
    def __init__(self, filepath: str, keys: List[str]) -> None: ...
    def on_complete(self, next_state: Dict[str, Any], action: Action[Any]) -> None: ...

# ———— DevToolsMiddleware ————
class DevToolsMiddleware(BaseMiddleware, MiddlewareProtocol):
    """記錄每次 action 與 state 快照，支援時間旅行調試。"""
    
    history: List[Tuple[Any, Action[Any], Any]]
    _prev_state: Any
    
    def __init__(self) -> None: ...
    def on_next(self, action: Action[Any], prev_state: Any) -> None: ...
    def on_complete(self, next_state: Any, action: Action[Any]) -> None: ...
    def get_history(self) -> List[Tuple[Any, Action[Any], Any]]: ...

# ———— PerformanceMonitorMiddleware ————
class PerformanceMonitorMiddleware(BaseMiddleware, MiddlewareProtocol):
    """統計每次 dispatch 到 reducer 完成所耗時間，單位毫秒。"""
    
    _start: float
    
    def __init__(self) -> None: ...
    def on_next(self, action: Action[Any], prev_state: Any) -> None: ...
    def on_complete(self, next_state: Any, action: Action[Any]) -> None: ...

# ———— DebounceMiddleware ————
class DebounceMiddleware(BaseMiddleware, MiddlewareProtocol):
    """對同一 action type 做防抖，interval 秒內只 dispatch 最後一條。"""
    
    interval: float
    _timers: Dict[str, Timer]
    
    def __init__(self, interval: float = 0.3) -> None: ...
    def __call__(self, store: Store[Any]) -> MiddlewareFunction: ...

# ———— BatchMiddleware ————
batch_action: Callable[[List[Action[Any]]], Action[List[Action[Any]]]]

class BatchMiddleware(BaseMiddleware, MiddlewareProtocol):
    """收集短時間窗內的 actions，合併成一個 BatchAction 一次性 dispatch。"""
    
    window: float
    buffer: List[Action[Any]]
    _lock: Lock
    
    def __init__(self, window: float = 0.1) -> None: ...
    def __call__(self, store: Store[Any]) -> MiddlewareFunction: ...
    def _flush(self, store: Store[Any]) -> None: ...

# ———— AnalyticsMiddleware ————
class AnalyticsMiddleware(BaseMiddleware, MiddlewareProtocol):
    """行為埋點中介，前後都會調用 callback(action, prev_state, next_state)。"""
    
    callback: Callable[[Action[Any], Any, Any], None]
    
    def __init__(self, callback: Callable[[Action[Any], Any, Any], None]) -> None: ...
    def on_next(self, action: Action[Any], prev_state: Any) -> None: ...
    def on_complete(self, next_state: Any, action: Action[Any]) -> None: ...