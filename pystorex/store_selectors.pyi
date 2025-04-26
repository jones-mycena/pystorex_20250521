"""
PyStoreX Store Selectors 模組的類型存根文件。
提供高精度的類型提示，無實際執行代碼。
"""

from typing import Callable, Any, Optional, overload
from .types import (
    Input, Output, R, StateSelector, ResultSelector,
    MemoizedSelector
)

@overload
def create_selector(selector: StateSelector[Input, Output], *, deep: bool = False, ttl: Optional[float] = None) -> StateSelector[Input, Output]: ...

@overload
def create_selector(*selectors: StateSelector[Input, Any], result_fn: ResultSelector[R], deep: bool = False, ttl: Optional[float] = None) -> StateSelector[Input, R]: ...

def create_selector(*selectors: Callable[[Any], Any], result_fn: Optional[Callable[..., Any]] = None, deep: bool = False, ttl: Optional[float] = None) -> MemoizedSelector: ...