"""
基於 Python 和 ReactiveX (RxPy) 的 NgRx 風格狀態管理架構

PyStoreX 是一個狀態管理庫，基於 NgRx 的架構理念，
使用 ReactiveX (RxPy) 實現了響應式資料流管理。

主要組件:
- Action: 描述狀態變更的意圖
- Reducer: 定義狀態如何變更的純函數
- Effect: 處理副作用（如 API 請求）的機制
- Store: 統一的狀態容器
- Selector: 高效率的狀態選擇器
- Middleware: 實現日誌記錄、非同步處理等功能

基本用法範例:
```python
from pystorex import create_store, create_reducer, create_action, on

# 定義 actions
increment = create_action("[Counter] Increment")
decrement = create_action("[Counter] Decrement")

# 定義 reducer
counter_reducer = create_reducer(
    0,  # 初始狀態
    on(increment, lambda state, action: state + 1),
    on(decrement, lambda state, action: state - 1)
)

# 創建 store
store = create_store()
store.register_root({"counter": counter_reducer})

# 使用 store
print(store.state)  # {"counter": 0}
store.dispatch(increment())
print(store.state)  # {"counter": 1}

# 監聽狀態變化
store.select(lambda state: state["counter"]).subscribe(
    on_next=lambda value_tuple: print(f"計數器從 {value_tuple[0]} 變為 {value_tuple[1]}")
)
```
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
]