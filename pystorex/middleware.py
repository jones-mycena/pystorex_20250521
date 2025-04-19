import threading
import asyncio
import json
import time
from types import MappingProxyType
from copy import deepcopy
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .actions import create_action, Action

# ———— Base Middleware ————
class BaseMiddleware:
    """
    基礎中介類，定義所有中介可能實現的鉤子。
    """
    def on_next(self, action: Action, prev_state: Any) -> None:
        """
        在 action 發送給 reducer 之前調用。

        Args:
            action: 正在 dispatch 的 Action
            prev_state: dispatch 之前的 store.state
        """
        pass

    def on_complete(self, next_state: Any, action: Action) -> None:
        """
        在 reducer 和 effects 處理完 action 之後調用。

        Args:
            next_state: dispatch 之後的最新 store.state
            action: 剛剛 dispatch 的 Action
        """
        pass

    def on_error(self, error: Exception, action: Action) -> None:
        """
        如果 dispatch 過程中拋出異常，則調用此鉤子。

        Args:
            error: 拋出的異常
            action: 導致異常的 Action
        """
        pass


# ———— LoggerMiddleware ————
class LoggerMiddleware(BaseMiddleware):
    """
    日誌中介，打印每個 action 發送前和發送後的 state。

    使用場景:
    - 偵錯時需要觀察每次 state 的變化。
    - 確保 action 的執行順序正確。
    """
    def on_next(self, action: Action, prev_state: Any) -> None:
        print(f"▶️ dispatching {action.type}")
        print(f"🔄 state before {action.type}: {prev_state}")

    def on_complete(self, next_state: Any, action: Action) -> None:
        print(f"✅ state after {action.type}: {next_state}")

    def on_error(self, error: Exception, action: Action) -> None:
        print(f"❌ error in {action.type}: {error}")


# ———— ThunkMiddleware ————
class ThunkMiddleware(BaseMiddleware):
    """
    支援 dispatch 函數 (thunk)，可以在 thunk 內執行非同步邏輯或多次 dispatch。

    使用場景:
    - 當需要執行非同步操作（例如 API 請求）並根據結果 dispatch 不同行為時。
    - 在一個 action 中執行多個子 action。
    """
    def __call__(self, store: Any) -> Callable:
        def middleware(next_dispatch: Callable[[Action], Any]) -> Callable[[Any], Any]:
            def dispatch(action: Any) -> Any:
                if callable(action):
                    return action(store.dispatch, lambda: store.state)
                return next_dispatch(action)
            return dispatch
        return middleware


# ———— AwaitableMiddleware ————
class AwaitableMiddleware(BaseMiddleware):
    """
    支援 dispatch coroutine/awaitable，完成後自動 dispatch 返回值。

    使用場景:
    - 當需要直接 dispatch 非同步函數並希望自動處理其結果時。
    """
    def __call__(self, store: Any) -> Callable:
        def middleware(next_dispatch: Callable[[Action], Any]) -> Callable[[Any], Any]:
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

class ErrorMiddleware(BaseMiddleware):
    """
    捕獲 dispatch 過程中的異常，dispatch 全域錯誤 Action，可擴展為上報到 Sentry 等。

    使用場景:
    - 當需要統一處理所有異常並記錄或上報時。
    """
    def __call__(self, store: Any) -> Callable:
        def middleware(next_dispatch: Callable[[Action], Any]) -> Callable[[Action], Any]:
            def dispatch(action: Action) -> Any:
                try:
                    return next_dispatch(action)
                except Exception as err:
                    store.dispatch(global_error({
                        "error": str(err),
                        "action": action.type
                    }))
                    raise
            return dispatch
        return middleware


# ———— ImmutableEnforceMiddleware ————
def _deep_freeze(obj: Any) -> Any:
    """
    遞歸地將 dict 轉為 MappingProxyType，將 list 轉為 tuple，防止誤修改。
    """
    if isinstance(obj, dict):
        return MappingProxyType({k: _deep_freeze(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return tuple(_deep_freeze(v) for v in obj)
    if isinstance(obj, tuple):
        return tuple(_deep_freeze(v) for v in obj)
    return obj

class ImmutableEnforceMiddleware(BaseMiddleware):
    """
    在 on_complete 時深度凍結 next_state。若需要替換 store.state，可在此處調用 store._state = frozen。

    使用場景:
    - 當需要確保 state 不被意外修改時。
    """
    def on_complete(self, next_state: Any, action: Action) -> None:
        frozen = _deep_freeze(next_state)
        # TODO: 若框架支援，可替換實際 state：
        # store._state = frozen


# ———— PersistMiddleware ————
class PersistMiddleware(BaseMiddleware):
    """
    自動持久化指定 keys 的子 state 到檔案，支援重啟恢復。

    使用場景:
    - 當需要在應用重啟後恢復部分重要的 state 時，例如用戶偏好設定或緩存數據。
    """
    def __init__(self, filepath: str, keys: List[str]) -> None:
        self.filepath = filepath
        self.keys = keys

    def on_complete(self, next_state: Dict[str, Any], action: Action) -> None:
        data = {
            k: next_state.get(k)
            for k in self.keys
            if k in next_state
        }
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, default=lambda o: o.dict() if hasattr(o, "dict") else o)
        except Exception as err:
            print(f"[PersistMiddleware] 寫入失敗: {err}")


# ———— DevToolsMiddleware ————
class DevToolsMiddleware(BaseMiddleware):
    """
    記錄每次 action 與 state 快照，支援時間旅行調試。

    使用場景:
    - 當需要回溯 state 的變化歷史以進行調試時。
    """
    def __init__(self) -> None:
        self.history: List[Tuple[Any, Action, Any]] = []

    def on_next(self, action: Action, prev_state: Any) -> None:
        self._prev_state = deepcopy(prev_state)

    def on_complete(self, next_state: Any, action: Action) -> None:
        self.history.append((self._prev_state, action, deepcopy(next_state)))

    def get_history(self) -> List[Tuple[Any, Action, Any]]:
        """返回整個歷史快照列表。"""
        return list(self.history)


# ———— PerformanceMonitorMiddleware ————
class PerformanceMonitorMiddleware(BaseMiddleware):
    """
    統計每次 dispatch 到 reducer 完成所耗時間，單位毫秒。

    使用場景:
    - 當需要分析性能瓶頸或優化 reducer 時。
    """
    def on_next(self, action: Action, prev_state: Any) -> None:
        self._start = time.perf_counter()

    def on_complete(self, next_state: Any, action: Action) -> None:
        elapsed = (time.perf_counter() - self._start) * 1000
        print(f"[Perf] {action.type} took {elapsed:.2f}ms")


# ———— DebounceMiddleware ————
class DebounceMiddleware(BaseMiddleware):
    """
    對同一 action type 做防抖，interval 秒內只 dispatch 最後一條。

    使用場景:
    - 當需要限制高頻率的 action，例如用戶快速點擊按鈕或輸入框事件。
    """
    def __init__(self, interval: float = 0.3) -> None:
        self.interval = interval
        self._timers: Dict[str, threading.Timer] = {}

    def __call__(self, store: Any) -> Callable:
        def middleware(next_dispatch: Callable[[Action], Any]) -> Callable[[Action], None]:
            def dispatch(action: Action) -> None:
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


# ———— BatchMiddleware ————
batch_action = create_action("[Batch] BatchAction", lambda items: items)

class BatchMiddleware(BaseMiddleware):
    """
    收集短時間窗內的 actions，合併成一個 BatchAction 一次性 dispatch。

    使用場景:
    - 當需要減少高頻 action 對性能的影響時，例如批量更新數據。
    """
    def __init__(self, window: float = 0.1) -> None:
        self.window = window
        self.buffer: List[Action] = []
        self._lock = threading.Lock()

    def __call__(self, store: Any) -> Callable:
        def middleware(next_dispatch: Callable[[Action], Any]) -> Callable[[Action], None]:
            def dispatch(action: Action) -> None:
                with self._lock:
                    self.buffer.append(action)
                    if len(self.buffer) == 1:
                        threading.Timer(self.window, self._flush, args=(store,)).start()
            return dispatch
        return middleware

    def _flush(self, store: Any) -> None:
        with self._lock:
            items = list(self.buffer)
            self.buffer.clear()
        store.dispatch(batch_action(items))


# ———— AnalyticsMiddleware ————
class AnalyticsMiddleware(BaseMiddleware):
    """
    行為埋點中介，前後都會調用 callback(action, prev_state, next_state)。

    使用場景:
    - 當需要記錄用戶行為數據以進行分析時，例如埋點統計。
    """
    def __init__(self, callback: Callable[[Action, Any, Any], None]) -> None:
        self.callback = callback

    def on_next(self, action: Action, prev_state: Any) -> None:
        self.callback(action, prev_state, None)

    def on_complete(self, next_state: Any, action: Action) -> None:
        self.callback(action, None, next_state)
