"""
PyStoreX 庫的主要入口點存根文件。
提供高精度的類型提示，無實際執行代碼。
"""

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

# 匯出所有公開 API
__all__ = [
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
]