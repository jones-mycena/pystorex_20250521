"""
基於 PyStoreX 的錯誤處理模組。

此模組定義了 PyStoreX 使用的自定義異常類型及錯誤處理工具。
提供具體的錯誤類型、豐富的上下文信息和結構化的錯誤報告機制。
"""

from typing import Dict, Any, Optional, List, Tuple, Union
import traceback


class PyStoreXError(Exception):
    """所有 PyStoreX 異常的基礎類。"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        初始化基礎異常。
        
        Args:
            message: 錯誤訊息
            details: 錯誤的詳細資訊字典
        """
        self.message = message
        self.details = details or {}
        # 捕獲堆疊信息
        self.traceback = traceback.format_exc()
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        將異常轉換為結構化字典，方便序列化和記錄。
        
        Returns:
            包含所有錯誤信息的字典
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "traceback": self.traceback
        }
    
    def __str__(self) -> str:
        """自定義字符串表示，顯示更多有用的信息。"""
        details_str = ", ".join(f"{k}={v}" for k, v in self.details.items()) if self.details else ""
        return f"{self.__class__.__name__}: {self.message} [{details_str}]"


class ActionError(PyStoreXError):
    """與 Action 相關的錯誤。"""
    
    def __init__(self, message: str, action_type: str, payload: Any = None, **kwargs):
        """
        初始化 Action 錯誤。
        
        Args:
            message: 錯誤訊息
            action_type: 發生錯誤的 Action 類型
            payload: Action 的負載
            **kwargs: 其他錯誤詳情
        """
        details = {
            "action_type": action_type,
            "payload": payload,
            **kwargs
        }
        super().__init__(message, details)


class ReducerError(PyStoreXError):
    """與 Reducer 相關的錯誤。"""
    
    def __init__(self, message: str, reducer_name: str, action_type: str, state: Any = None, **kwargs):
        """
        初始化 Reducer 錯誤。
        
        Args:
            message: 錯誤訊息
            reducer_name: 發生錯誤的 Reducer 名稱
            action_type: 處理時的 Action 類型
            state: 處理時的狀態
            **kwargs: 其他錯誤詳情
        """
        details = {
            "reducer_name": reducer_name,
            "action_type": action_type,
            "state": state,
            **kwargs
        }
        super().__init__(message, details)


class EffectError(PyStoreXError):
    """與 Effect 相關的錯誤。"""
    
    def __init__(self, message: str, effect_name: str, module_name: str, action_type: Optional[str] = None, **kwargs):
        """
        初始化 Effect 錯誤。
        
        Args:
            message: 錯誤訊息
            effect_name: 發生錯誤的 Effect 名稱
            module_name: Effect 所屬的模組名稱
            action_type: 觸發 Effect 的 Action 類型（如有）
            **kwargs: 其他錯誤詳情
        """
        details = {
            "effect_name": effect_name,
            "module_name": module_name,
            "action_type": action_type,
            **kwargs
        }
        super().__init__(message, details)


class SelectorError(PyStoreXError):
    """與 Selector 相關的錯誤。"""
    
    def __init__(self, message: str, selector_name: Optional[str] = None, input_state: Any = None, **kwargs):
        """
        初始化 Selector 錯誤。
        
        Args:
            message: 錯誤訊息
            selector_name: 發生錯誤的 Selector 名稱
            input_state: 選擇器的輸入狀態
            **kwargs: 其他錯誤詳情
        """
        details = {
            "selector_name": selector_name,
            "input_state": input_state,
            **kwargs
        }
        super().__init__(message, details)


class StoreError(PyStoreXError):
    """與 Store 相關的錯誤。"""
    
    def __init__(self, message: str, operation: str, **kwargs):
        """
        初始化 Store 錯誤。
        
        Args:
            message: 錯誤訊息
            operation: 發生錯誤的操作名稱
            **kwargs: 其他錯誤詳情
        """
        details = {
            "operation": operation,
            **kwargs
        }
        super().__init__(message, details)


class MiddlewareError(PyStoreXError):
    """與 Middleware 相關的錯誤。"""
    
    def __init__(self, message: str, middleware_name: str, action_type: Optional[str] = None, **kwargs):
        """
        初始化 Middleware 錯誤。
        
        Args:
            message: 錯誤訊息
            middleware_name: 發生錯誤的 Middleware 名稱
            action_type: 處理時的 Action 類型
            **kwargs: 其他錯誤詳情
        """
        details = {
            "middleware_name": middleware_name,
            "action_type": action_type,
            **kwargs
        }
        super().__init__(message, details)


class ValidationError(PyStoreXError):
    """資料驗證錯誤。"""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None, expected_type: Optional[str] = None, **kwargs):
        """
        初始化驗證錯誤。
        
        Args:
            message: 錯誤訊息
            field: 驗證失敗的欄位名
            value: 驗證失敗的值
            expected_type: 預期的類型
            **kwargs: 其他錯誤詳情
        """
        details = {
            "field": field,
            "value": value,
            "expected_type": expected_type,
            **kwargs
        }
        super().__init__(message, details)


class ConfigurationError(PyStoreXError):
    """配置相關的錯誤。"""
    
    def __init__(self, message: str, component: str, config_key: Optional[str] = None, **kwargs):
        """
        初始化配置錯誤。
        
        Args:
            message: 錯誤訊息
            component: 配置錯誤的組件名稱
            config_key: 錯誤的配置鍵
            **kwargs: 其他錯誤詳情
        """
        details = {
            "component": component,
            "config_key": config_key,
            **kwargs
        }
        super().__init__(message, details)


# 全局錯誤處理器
class ErrorHandler:
    """集中式錯誤處理器，用於捕獲、日誌記錄和錯誤報告。"""
    
    def __init__(self, log_to_console: bool = True, log_to_file: bool = False, log_file: Optional[str] = None):
        """
        初始化錯誤處理器。
        
        Args:
            log_to_console: 是否將錯誤記錄到控制台
            log_to_file: 是否將錯誤記錄到文件
            log_file: 日誌文件路徑
        """
        self.log_to_console = log_to_console
        self.log_to_file = log_to_file
        self.log_file = log_file
        self.handlers: List[Callable[[PyStoreXError], None]] = []
    
    def register_handler(self, handler: Callable[[PyStoreXError], None]) -> None:
        """
        註冊錯誤處理函數。
        
        Args:
            handler: 接收 PyStoreXError 的處理函數
        """
        self.handlers.append(handler)
    
    def handle(self, error: Union[PyStoreXError, Exception]) -> None:
        """
        處理錯誤，日誌記錄並調用註冊的處理器。
        
        Args:
            error: 需要處理的錯誤
        """
        # 將標準異常包裝為 PyStoreXError
        if not isinstance(error, PyStoreXError):
            error = PyStoreXError(str(error), {"original_error": str(type(error))})
        
        # 控制台日誌
        if self.log_to_console:
            print(f"[ERROR] {error}")
        
        # 文件日誌
        if self.log_to_file and self.log_file:
            try:
                with open(self.log_file, "a") as f:
                    f.write(f"{error}\n{error.traceback}\n")
            except Exception as e:
                print(f"[ERROR] 無法寫入日誌: {e}")
        
        # 調用所有處理器
        for handler in self.handlers:
            try:
                handler(error)
            except Exception as e:
                print(f"[ERROR] 錯誤處理器執行錯誤: {e}")


# 單例錯誤處理器
global_error_handler = ErrorHandler()


def handle_error(func):
    """
    裝飾器，用於自動捕獲函數中的異常並交給錯誤處理器。
    
    Args:
        func: 需要錯誤處理的函數
    
    Returns:
        包裝後的函數
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if isinstance(e, PyStoreXError):
                global_error_handler.handle(e)
            else:
                # 依據函數的名稱和參數，構造更有意義的錯誤
                error = PyStoreXError(
                    f"{func.__name__} 執行時發生錯誤: {str(e)}",
                    {
                        "function": func.__name__,
                        "args": str(args),
                        "kwargs": str(kwargs)
                    }
                )
                global_error_handler.handle(error)
            raise
    return wrapper