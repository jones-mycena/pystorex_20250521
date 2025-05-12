"""
PyStoreX 錯誤處理模組的類型存根文件。
提供高精度的類型提示，無實際執行代碼。
"""

from typing import Dict, Any, Optional, List, Callable, Union, ClassVar, Type, TypeVar

T = TypeVar('T', bound='PyStoreXError')

class PyStoreXError(Exception):
    """所有 PyStoreX 異常的基礎類。"""
    
    message: str
    details: Dict[str, Any]
    traceback: str
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None: ...
    
    def to_dict(self) -> Dict[str, Any]: ...
    
    def __str__(self) -> str: ...


class ActionError(PyStoreXError):
    """與 Action 相關的錯誤。"""
    
    def __init__(self, message: str, action_type: str, payload: Any = None, **kwargs: Any) -> None: ...


class ReducerError(PyStoreXError):
    """與 Reducer 相關的錯誤。"""
    
    def __init__(self, message: str, reducer_name: str, action_type: str, state: Any = None, **kwargs: Any) -> None: ...


class EffectError(PyStoreXError):
    """與 Effect 相關的錯誤。"""
    
    def __init__(self, message: str, effect_name: str, module_name: str, action_type: Optional[str] = None, **kwargs: Any) -> None: ...


class SelectorError(PyStoreXError):
    """與 Selector 相關的錯誤。"""
    
    def __init__(self, message: str, selector_name: Optional[str] = None, input_state: Any = None, **kwargs: Any) -> None: ...


class StoreError(PyStoreXError):
    """與 Store 相關的錯誤。"""
    
    def __init__(self, message: str, operation: str, **kwargs: Any) -> None: ...


class MiddlewareError(PyStoreXError):
    """與 Middleware 相關的錯誤。"""
    
    def __init__(self, message: str, middleware_name: str, action_type: Optional[str] = None, **kwargs: Any) -> None: ...


class ValidationError(PyStoreXError):
    """資料驗證錯誤。"""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None, expected_type: Optional[str] = None, **kwargs: Any) -> None: ...


class ConfigurationError(PyStoreXError):
    """配置相關的錯誤。"""
    
    def __init__(self, message: str, component: str, config_key: Optional[str] = None, **kwargs: Any) -> None: ...


class ErrorHandler:
    """集中式錯誤處理器，用於捕獲、日誌記錄和錯誤報告。"""
    
    log_to_console: bool
    log_to_file: bool
    log_file: Optional[str]
    handlers: List[Callable[[PyStoreXError], None]]
    
    def __init__(self, log_to_console: bool = True, log_to_file: bool = False, log_file: Optional[str] = None) -> None: ...
    
    def register_handler(self, handler: Callable[[PyStoreXError], None]) -> None: ...
    
    def handle(self, error: Union[PyStoreXError, Exception]) -> None: ...


# 單例錯誤處理器
global_error_handler: ErrorHandler


def handle_error(func: Callable[..., T]) -> Callable[..., T]: ...