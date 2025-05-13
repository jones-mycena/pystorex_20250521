"""
PyStoreX 庫的主要入口點存根文件。
提供高精度的類型提示，無實際執行代碼。
"""

from .errors import (
    PyStoreXError, ActionError, ReducerError, EffectError, 
    SelectorError, StoreError, MiddlewareError, ValidationError,
    ConfigurationError, ErrorHandler, global_error_handler, handle_error
)
from .actions import Action, create_action
from .middleware import (
    BaseMiddleware, LoggerMiddleware, ThunkMiddleware,
    AwaitableMiddleware, ErrorMiddleware, ImmutableEnforceMiddleware,
    PersistMiddleware, DevToolsMiddleware, PerformanceMonitorMiddleware,
    DebounceMiddleware, BatchMiddleware, AnalyticsMiddleware
)
from .reducers import create_reducer, on, ReducerManager
from .effects import Effect, create_effect, EffectsManager
from .store import Store, create_store, StoreModule, EffectsModule
from .store_selectors import create_selector
from .immutable_utils import to_immutable, to_dict, to_pydantic
from .map_utils import update_in, batch_update

# 匯出所有公開 API
__all__ = [
    # Errors
    "PyStoreXError", "ActionError", "ReducerError", "EffectError",
    "SelectorError", "StoreError", "MiddlewareError", "ValidationError",
    "ConfigurationError", "ErrorHandler", "global_error_handler", "handle_error",
    
    # Actions
    "Action", "create_action",
    
    # Middleware
    "BaseMiddleware", "LoggerMiddleware", "ThunkMiddleware",
    "AwaitableMiddleware", "ErrorMiddleware", "ImmutableEnforceMiddleware",
    "PersistMiddleware", "DevToolsMiddleware", "PerformanceMonitorMiddleware",
    "DebounceMiddleware", "BatchMiddleware", "AnalyticsMiddleware",
    
    # Reducers
    "create_reducer", "on", "ReducerManager",
    
    # Effects
    "Effect", "create_effect", "EffectsManager",
    
    # Store
    "Store", "create_store", "StoreModule", "EffectsModule",
    
    # Selectors
    "create_selector"
    
    # Immutable Utils
    "to_immutable", "to_dict", "to_pydantic",
    
    # Map Utils
    "update_in", "batch_update"
]