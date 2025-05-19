"""
基於 PyStoreX 的中介軟體定義模組。

此模組提供各種中介軟體，用於在動作分發過程中插入自定義邏輯，
實現日誌記錄、錯誤處理、性能監控等功能。
"""

import contextlib
import datetime
import threading
import asyncio
import json
import time
import traceback
from typing import (
    Any, Callable, Dict, Generator, List, Optional, Tuple, Union, cast
)
import uuid

from immutables import Map

from .immutable_utils import to_dict

from .errors import ActionError, PyStoreXError, global_error_handler
from .actions import create_action, Action
from .types import (
    ActionContext, NextDispatch, MiddlewareFactory, MiddlewareFunction, DispatchFunction, 
    Store, ThunkFunction, GetState, Middleware as MiddlewareProtocol
)


# ———— Base Middleware ————
class BaseMiddleware:
    """
    基礎中介類，定義所有中介可能實現的鉤子。
    
    中介軟體可以介入動作分發的流程，在動作到達 Reducer 前、
    動作處理完成後或出現錯誤時執行自定義邏輯。
    """
    
    def on_next(self, action: Any, prev_state: Any) -> None:
        """
        在 action 發送給 reducer 之前調用。

        Args:
            action: 正在 dispatch 的 Action
            prev_state: dispatch 之前的 store.state
        """
        pass

    def on_complete(self, next_state: Any, action: Any) -> None:
        """
        在 reducer 和 effects 處理完 action 之後調用。

        Args:
            next_state: dispatch 之後的最新 store.state
            action: 剛剛 dispatch 的 Action
        """
        pass

    def on_error(self, error: Exception, action: Any) -> None:
        """
        如果 dispatch 過程中拋出異常，則調用此鉤子。

        Args:
            error: 拋出的異常
            action: 導致異常的 Action
        """
        pass
    
    def teardown(self) -> None:
        """
        當 Store 清理資源時調用，用於清理中間件持有的資源。
        """
        pass
    
    @contextlib.contextmanager
    def action_context(self, action: Any, prev_state: Any) -> Generator[ActionContext, None, None]:
        """
        提供一個上下文管理器來處理 action 分發的生命週期。
        
        這個方法使用現有的 on_next、on_complete 和 on_error 鉤子，
        但以更優雅的上下文管理器形式提供。
        
        子類可以覆蓋此方法，但應負責呼叫適當的 hook 方法，
        或使用 super().action_context() 來確保 hook 被呼叫。
        
        Args:
            action: 要分發的 Action
            prev_state: 分發前的狀態
            
        Yields:
            Dict[str, Any]: 包含上下文數據的字典，可用於在上下文內部與外部之間傳遞數據
        """
        # 初始化上下文數據
        context: ActionContext = {
            'action': action,
            'prev_state': prev_state,
            'next_state': None,
            'result': None,
            'error': None
        }
        
        # 前置處理
        self.on_next(action, prev_state)
        
        try:
            # 讓出控制權，讓實際的 dispatch 發生
            yield context
            
            # 如果上下文中已經設置了 next_state，使用它調用 on_complete
            if 'next_state' in context and context['next_state'] is not None:
                self.on_complete(context['next_state'], action)
                
        except Exception as err:
            # 錯誤處理
            context['error'] = err
            self.on_error(err, action)
            raise


# ———— LoggerMiddleware ————
class LoggerMiddleware(BaseMiddleware, MiddlewareProtocol):
    """
    日誌中介，打印每個 action 發送前和發送後的 state。

    使用場景:
    - 偵錯時需要觀察每次 state 的變化。
    - 確保 action 的執行順序正確。
    """
    def __init__(self):
        self._current_context = None  # 用於臨時存儲 context
        
    @contextlib.contextmanager
    def action_context(self, action: Any, prev_state: Any) -> Generator[ActionContext, None, None]:
        context: ActionContext = {
            'action': action,
            'prev_state': prev_state,
            'next_state': None,
            'result': None,
            'error': None,
            'timestamp': datetime.datetime.now()  # 添加時間戳
        }
        self._current_context = context  # 存儲 context
        self.on_next(action, prev_state)
        try:
            yield context
            if context['next_state'] is not None:
                self.on_complete(context['next_state'], action)
        except Exception as err:
            context['error'] = err
            self.on_error(err, action)
            raise
        finally:
            self._current_context = None  # 清理 context    
        
    def on_next(self, action: Action[Any], prev_state: Any) -> None:
        """
        在 action 發送給 reducer 之前打印日誌。
        
        Args:
            action: 正在 dispatch 的 Action
            prev_state: dispatch 之前的 store.state
        """
        if self._current_context:
            print(f"[{self._current_context['timestamp']}] ▶️ dispatching {action.type}")
            print(f"[{self._current_context['timestamp']}] 🔄 state before {action.type}: {prev_state}")
        else:
            print(f"▶️ dispatching {action.type}")
            print(f"🔄 state before {action.type}: {prev_state}")

    def on_complete(self, next_state: Any, action: Action[Any]) -> None:
        """
        在 reducer 和 effects 處理完 action 之後打印日誌。
        
        Args:
            next_state: dispatch 之後的最新 store.state
            action: 剛剛 dispatch 的 Action
        """
        if self._current_context:
            print(f"[{self._current_context['timestamp']}] ✅ state after {action.type}: {next_state}")
        else:
            print(f"✅ state after {action.type}: {next_state}")

    def on_error(self, error: Exception, action: Action[Any]) -> None:
        """
        如果 dispatch 過程中拋出異常，則打印錯誤日誌。
        
        Args:
            error: 拋出的異常
            action: 導致異常的 Action
        """
        print(f"❌ error in {action.type}: {error}")
        
        


# ———— ThunkMiddleware ————
class ThunkMiddleware(BaseMiddleware, MiddlewareProtocol):
    """
    支援 dispatch 函數 (thunk)，可以在 thunk 內執行非同步邏輯或多次 dispatch。

    使用場景:
    - 當需要執行非同步操作（例如 API 請求）並根據結果 dispatch 不同行為時。
    - 在一個 action 中執行多個子 action。
    
    範例:
        ```python
        # 定義一個簡單的 thunk
        def fetch_user(user_id):
            def thunk(dispatch, get_state):
                # 發送開始請求的 action
                dispatch(request_user(user_id))
                
                # 執行非同步請求
                try:
                    user = api.fetch_user(user_id)
                    # 成功時發送成功 action
                    dispatch(request_user_success(user))
                except Exception as e:
                    # 失敗時發送失敗 action
                    dispatch(request_user_failure(str(e)))
                    
            return thunk
            
        # 使用 thunk
        store.dispatch(fetch_user("user123"))
        ```
    """
    def __call__(self, store: Store[Any]) -> MiddlewareFunction:
        """
        配置 Thunk 中介軟體。
        
        Args:
            store: Store 實例
            
        Returns:
            配置函數，接收 next_dispatch 並返回新的 dispatch 函數
        """
        def middleware(next_dispatch: NextDispatch) -> DispatchFunction:
            def dispatch(action: Union[ThunkFunction, Action[Any]]) -> Any:
                if callable(action):
                    return cast(ThunkFunction, action)(store.dispatch, lambda: store.state)
                return next_dispatch(cast(Action[Any], action))
            return dispatch
        return middleware


# ———— AwaitableMiddleware ————
class AwaitableMiddleware(BaseMiddleware, MiddlewareProtocol):
    """
    支援 dispatch coroutine/awaitable，完成後自動 dispatch 返回值。

    使用場景:
    - 當需要直接 dispatch 非同步函數並希望自動處理其結果時。
    
    範例:
        ```python
        # 定義一個 async 函數
        async def fetch_data():
            # 模擬非同步操作
            await asyncio.sleep(1)
            # 返回 Action
            return data_loaded({"result": "success"})
            
        # 直接 dispatch 非同步函數
        store.dispatch(fetch_data())  # 完成後會自動 dispatch 返回的 Action
        ```
    """
    def __call__(self, store: Store[Any]) -> MiddlewareFunction:
        """
        配置 Awaitable 中介軟體。
        
        Args:
            store: Store 實例
            
        Returns:
            配置函數，接收 next_dispatch 並返回新的 dispatch 函數
        """
        def middleware(next_dispatch: NextDispatch) -> DispatchFunction:
            def dispatch(action: Any) -> Any:
                if asyncio.iscoroutine(action) or asyncio.isfuture(action):
                    task = asyncio.ensure_future(action)
                    task.add_done_callback(lambda fut: store.dispatch(fut.result()))
                    return task
                return next_dispatch(action)
            return dispatch
        return middleware
    


# ———— ErrorMiddleware ————
global_error = create_action("[Error] GlobalError", lambda info: info)

class ErrorMiddleware(BaseMiddleware, MiddlewareProtocol):
    """
    捕獲 dispatch 過程中的異常，dispatch 全域錯誤 Action，可擴展為上報到 Sentry 等。

    使用場景:
    - 當需要統一處理所有異常並記錄或上報時。
    """
    def __init__(self):
        self._current_context = None
        self.store = None  # 假設 store 在某處設置
    
    def __call__(self, store: Store[Any]) -> MiddlewareFunction:
        """
        配置 Error 中介軟體。
        
        Args:
            store: Store 實例
            
        Returns:
            配置函數，接收 next_dispatch 並返回新的 dispatch 函數
        """
        self.store = store
        def middleware(next_dispatch: NextDispatch) -> DispatchFunction:
                def dispatch(action: Action[Any]) -> Any:
                    with self.action_context(action, store.state) as context:
                        return next_dispatch(action)
                return dispatch
        return middleware

    @contextlib.contextmanager
    def action_context(self, action: Any, prev_state: Any) -> Generator[ActionContext, None, None]:
        context: ActionContext = {
            'action': action,
            'prev_state': prev_state,
            'next_state': None,
            'result': None,
            'error': None,
            'error_timestamp': time.time()
        }
        self._current_context = context
        self.on_next(action, prev_state)
        try:
            yield context
            if context['next_state'] is not None:
                self.on_complete(context['next_state'], action)
        except Exception as err:
            context['error'] = err
            self.on_error(err, action)
            raise
        finally:
            self._current_context = None

    def on_error(self, error: Exception, action: Action[Any]) -> None:
        error_info = {
            "error": str(error),
            "action": action.type,
            "timestamp": self._current_context['error_timestamp'] if self._current_context else time.time()
        }
        self.store.dispatch(global_error(error_info))



# ———— PersistMiddleware ————
class PersistMiddleware(BaseMiddleware, MiddlewareProtocol):
    """
    自動持久化指定 keys 的子 state 到檔案，支援重啟恢復。

    使用場景:
    - 當需要在應用重啟後恢復部分重要的 state 時，例如用戶偏好設定或緩存數據。
    """
    def __init__(self, filepath: str, keys: List[str]) -> None:
        """
        初始化 PersistMiddleware。
        
        Args:
            filepath: 持久化的檔案路徑
            keys: 需要持久化的 state 子鍵列表
        """
        self.filepath = filepath
        self.keys = keys
        self._current_context = None
        
    @contextlib.contextmanager
    def action_context(self, action: Any, prev_state: Any) -> Generator[ActionContext, None, None]:
        context: ActionContext = {
            'action': action,
            'prev_state': prev_state,
            'next_state': None,
            'result': None,
            'error': None,
            'persist_timestamp': time.time()
        }
        self._current_context = context
        self.on_next(action, prev_state)
        try:
            yield context
            if context['next_state'] is not None:
                self.on_complete(context['next_state'], action)
        except Exception as err:
            context['error'] = err
            self.on_error(err, action)
            raise
        finally:
            self._current_context = None

    def on_complete(self, next_state: Dict[str, Any], action: Action[Any]) -> None:
        new_state_dict = to_dict(next_state)
        data = {k: new_state_dict.get(k) for k in self.keys if k in new_state_dict}
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, default=lambda o: 
                    o.dict() if hasattr(o, "dict") else
                    dict(o) if isinstance(o, Map) else o)
        except Exception as err:
            timestamp = self._current_context['persist_timestamp'] if self._current_context else time.time()
            print(f"[PersistMiddleware] Write failed at {timestamp}: {err}")
    


# ———— DevToolsMiddleware ————
class DevToolsMiddleware(BaseMiddleware, MiddlewareProtocol):
    """
    記錄每次 action 與 state 快照，支援時間旅行調試。

    使用場景:
    - 當需要回溯 state 的變化歷史以進行調試時。
    """
    def __init__(self) -> None:
        """初始化 DevToolsMiddleware。"""
        self.history: List[Tuple[Any, Action[Any], Any]] = []
        self._current_context = None

    @contextlib.contextmanager
    def action_context(self, action: Any, prev_state: Any) -> Generator[ActionContext, None, None]:
        context: ActionContext = {
            'action': action,
            'prev_state': prev_state,
            'next_state': None,
            'result': None,
            'error': None
        }
        self._current_context = context
        self.on_next(action, prev_state)
        try:
            yield context
            if context['next_state'] is not None:
                self.on_complete(context['next_state'], action)
        except Exception as err:
            context['error'] = err
            self.on_error(err, action)
            raise
        finally:
            self._current_context = None

    def on_next(self, action: Action[Any], prev_state: Any) -> None:
        pass  # 移除手動記錄 prev_state 的邏輯

    def on_complete(self, next_state: Any, action: Action[Any]) -> None:
        """
        在 reducer 和 effects 處理完 action 之後，記錄歷史。
        """
        if self._current_context:
            self.history.append((self._current_context['prev_state'], action, next_state))

    def get_history(self) -> List[Tuple[Any, Action[Any], Any]]:
        """
        返回整個歷史快照列表。
        
        Returns:
            歷史快照列表，每項為 (prev_state, action, next_state)
        """
        return list(self.history)


# ———— PerformanceMonitorMiddleware ————
class PerformanceMonitorMiddleware(BaseMiddleware):
    """
    性能監控中間件，記錄 action 處理時間。
    """
    
    def __init__(self, threshold_ms: float = 100, log_all: bool = False):
        """
        初始化 PerformanceMonitorMiddleware。
        
        Args:
            threshold_ms: 性能警告閾值，單位為毫秒，預設為 100 毫秒
            log_all: 是否記錄所有 action 的性能指標，預設為 False (只記錄超過閾值的)
        """
        self.threshold_ms = threshold_ms
        self.log_all = log_all
        self.metrics = {}
        self._current_context = None
    
    @contextlib.contextmanager
    def action_context(self, action: Any, prev_state: Any) -> Generator[Dict[str, Any], None, None]:
        context = {
            'action': action,
            'prev_state': prev_state,
            'next_state': None,
            'result': None,
            'error': None,
            'action_priority': getattr(action, 'priority', 'normal')
        }
        self._current_context = context
        self.on_next(action, prev_state)
        start_time = time.perf_counter()
        try:
            yield context
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            action_type = getattr(action, 'type', str(action))
            if action_type not in self.metrics:
                self.metrics[action_type] = []
            self.metrics[action_type].append(elapsed_ms)
            # 確保在訪問 _current_context 前檢查是否為 None
            priority = self._current_context['action_priority'] if self._current_context else 'normal'
            if self.log_all or elapsed_ms > self.threshold_ms:
                print(f"⏱️ Performance: Action {action_type} (Priority: {priority}) took {elapsed_ms:.2f}ms")
                if elapsed_ms > self.threshold_ms:
                    print(f"⚠️ Warning: Action {action_type} exceeded threshold ({self.threshold_ms}ms)")
            if context['next_state']:
                self.on_complete(context['next_state'], action)
        except Exception as err:
            context['error'] = err
            self.on_error(err, action)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            # 在異常情況下也確保 priority 可訪問
            priority = self._current_context['action_priority'] if self._current_context else 'normal'
            print(f"❌ Action {getattr(action, 'type', str(action))} failed after {elapsed_ms:.2f}ms: {err}")
            raise
        finally:
            self._current_context = None
    
    def get_metrics(self) -> Dict[str, Dict[str, float]]:
        """
        獲取性能指標統計信息。
        """
        result = {}
        for action_type, times in self.metrics.items():
            if not times:
                continue
            avg_time = sum(times) / len(times)
            max_time = max(times)
            min_time = min(times)
            result[action_type] = {
                'avg': avg_time,
                'max': max_time,
                'min': min_time,
                'count': len(times)
            }
        return result


# ———— DebounceMiddleware ————
class DebounceMiddleware(BaseMiddleware, MiddlewareProtocol):
    """
    對同一 action type 做防抖，interval 秒內只 dispatch 最後一條。

    使用場景:
    - 當需要限制高頻率的 action，例如用戶快速點擊按鈕或輸入框事件。
    """
    def __init__(self, interval: float = 0.3) -> None:
        """
        初始化 DebounceMiddleware。
        
        Args:
            interval: 防抖間隔，單位秒，預設 0.3 秒
        """
        self.interval = interval
        self._timers: Dict[str, threading.Timer] = {}

    def __call__(self, store: Store[Any]) -> MiddlewareFunction:
        """
        配置 Debounce 中介軟體。
        
        Args:
            store: Store 實例
            
        Returns:
            配置函數，接收 next_dispatch 並返回新的 dispatch 函數
        """
        def middleware(next_dispatch: NextDispatch) -> DispatchFunction:
            def dispatch(action: Action[Any]) -> None:
                key = action.type
                # 取消上一次定時
                if key in self._timers:
                    self._timers[key].cancel()
                # 延遲 dispatch
                timer = threading.Timer(self.interval, lambda: next_dispatch(action))
                self._timers[key] = timer
                timer.start()
            return dispatch
        return middleware
    def teardown(self) -> None:
        """
        清理所有計時器。
        """
        for timer in self._timers.values():
            timer.cancel()
        self._timers.clear()


# ———— BatchMiddleware ————
batch_action = create_action("[Batch] BatchAction", lambda items: items)

class BatchMiddleware(BaseMiddleware, MiddlewareProtocol):
    """
    收集短時間窗內的 actions，合併成一個 BatchAction 一次性 dispatch。

    使用場景:
    - 當需要減少高頻 action 對性能的影響時，例如批量更新數據。
    """
    def __init__(self, window: float = 0.1) -> None:
        """
        初始化 BatchMiddleware。
        
        Args:
            window: 批處理時間窗口，單位秒，預設 0.1 秒
        """
        self.window = window
        self.buffer: List[Action[Any]] = []
        self._lock = threading.Lock()

    def __call__(self, store: Store[Any]) -> MiddlewareFunction:
        """
        配置 Batch 中介軟體。
        
        Args:
            store: Store 實例
            
        Returns:
            配置函數，接收 next_dispatch 並返回新的 dispatch 函數
        """
        def middleware(next_dispatch: NextDispatch) -> DispatchFunction:
            def dispatch(action: Action[Any]) -> None:
                with self._lock:
                    self.buffer.append(action)
                    if len(self.buffer) == 1:
                        threading.Timer(self.window, self._flush, args=(store,)).start()
            return dispatch
        return middleware

    def _flush(self, store: Store[Any]) -> None:
        """
        將緩衝區中的 actions 批量發送。
        
        Args:
            store: Store 實例
        """
        with self._lock:
            items = list(self.buffer)
            self.buffer.clear()
        store.dispatch(batch_action(items))


# ———— AnalyticsMiddleware ————
class AnalyticsMiddleware(BaseMiddleware, MiddlewareProtocol):
    """
    行為埋點中介，前後都會調用 callback(action, prev_state, next_state)。

    使用場景:
    - 當需要記錄用戶行為數據以進行分析時，例如埋點統計。
    """
    def __init__(self, callback: Callable[[Action[Any], Any, Any], None]) -> None:
        """
        初始化 AnalyticsMiddleware。
        
        Args:
            callback: 分析回調函數，接收 (action, prev_state, next_state)
        """
        self.callback = callback
        
    @contextlib.contextmanager
    def action_context(self, action: Any, prev_state: Any) -> Generator[ActionContext, None, None]:
        context: ActionContext = {
            'action': action,
            'prev_state': prev_state,
            'next_state': None,
            'result': None,
            'error': None,
            'session_id': uuid.uuid4().hex
        }
        self.on_next(action, prev_state, context)
        try:
            yield context
            if context['next_state'] is not None:
                self.on_complete(context['next_state'], action, context)
        except Exception as err:
            context['error'] = err
            self.on_error(err, action)
            raise
        
    def on_next(self, action: Action[Any], prev_state: Any, context: ActionContext = None) -> None:
        """
        在 action 發送給 reducer 之前調用分析回調。
        
        Args:
            action: 正在 dispatch 的 Action
            prev_state: dispatch 之前的 store.state
            context: 上下文數據
        """
        session_id = context['session_id'] if context else None
        self.callback(action, prev_state, None, session_id=session_id)
        
    def on_complete(self, next_state: Any, action: Action[Any], context: ActionContext = None) -> None:
        """
        在 reducer 和 effects 處理完 action 之後調用分析回調。
        
        Args:
            next_state: dispatch 之後的最新 store.state
            action: 剛剛 dispatch 的 Action
            context: 上下文數據
        """
        session_id = context['session_id'] if context else None
        self.callback(action, None, next_state, session_id=session_id)
        

# ———— ErrorReportMiddleware ————
class ErrorReportMiddleware(BaseMiddleware, MiddlewareProtocol):
    """記錄錯誤並提供開發時的詳細錯誤報告。"""
    
    def __init__(self, report_file: str = "pystorex_error_report.html"):
        """
        初始化錯誤報告中介軟體。
        
        Args:
            report_file: 錯誤報告輸出文件路徑
        """
        self.report_file = report_file
        self.error_history: List[Dict[str, Any]] = []
        self._current_context = None
        # 註冊到全局錯誤處理器
        global_error_handler.register_handler(self._log_error)
    
    @contextlib.contextmanager
    def action_context(self, action: Any, prev_state: Any) -> Generator[ActionContext, None, None]:
        context: ActionContext = {
            'action': action,
            'prev_state': prev_state,
            'next_state': None,
            'result': None,
            'error': None,
            'error_category': None
        }
        self._current_context = context
        self.on_next(action, prev_state)
        try:
            yield context
            if context['next_state'] is not None:
                self.on_complete(context['next_state'], action)
        except Exception as err:
            context['error'] = err
            context['error_category'] = 'PyStoreXError' if isinstance(err, PyStoreXError) else 'GenericError'
            self.on_error(err, action)
            raise
        finally:
            self._current_context = None       
            
    def on_error(self, error: Exception, action: Action[Any]) -> None:
        error_info = {
            "timestamp": time.time(),
            "error_type": error.__class__.__name__,
            "message": str(error),
            "action": action.type if hasattr(action, "type") else str(action),
            "stacktrace": traceback.format_exc(),
            "category": self._current_context['error_category'] if self._current_context else 'Unknown'
        }
        self.error_history.append(error_info)
        self._generate_report()
    
    def _log_error(self, error: PyStoreXError, action: Optional[Action[Any]] = None) -> None:
        """記錄結構化錯誤。"""
        error_info = error.to_dict()
        error_info["timestamp"] = time.time()
        if action:
            error_info["action"] = action.type
        self.error_history.append(error_info)
        self._generate_report()
    
    def _generate_report(self) -> None:
        """生成HTML錯誤報告。"""
        try:
            with open(self.report_file, "w") as f:
                f.write("<html><head><title>PyStoreX Error Report</title>")
                f.write("<style>/* CSS styles */</style></head><body>")
                f.write("<h1>PyStoreX Error Report</h1>")
                for error in self.error_history:
                    f.write(f"<div class='error'>")
                    f.write(f"<h2>{error['error_type']}: {error['message']}</h2>")
                    f.write(f"<p>Time: {datetime.fromtimestamp(error['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}</p>")
                    if 'action' in error:
                        f.write(f"<p>Triggered Action: {error['action']}</p>")
                    f.write("<h3>Details:</h3><ul>")
                    for k, v in error.get('details', {}).items():
                        f.write(f"<li><strong>{k}:</strong> {v}</li>")
                    f.write("</ul>")
                    if 'traceback' in error:
                        f.write(f"<h3>Stacktrace:</h3><pre>{error['traceback']}</pre>")
                    f.write("</div><hr>")
                f.write("</body></html>")
        except Exception as e:
            print(f"Failed to generate error report: {e}")