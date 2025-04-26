"""
PyStoreX Effects 模組的類型存根文件。
提供高精度的類型提示，無實際執行代碼。
"""

from typing import Any, Callable, Dict, List, Optional, Tuple, overload
from reactivex import Observable
from reactivex.disposable import Disposable
from .actions import Action
from .types import (
    T, EffectFunction, EffectCreator, EffectDecorator, 
    Effect as EffectType, Store
)

class Effect(EffectType[T]):
    """表示一個副作用處理函數的封裝類別。"""
    
    source: Observable[T]
    
    def __init__(self, source: Observable[T]) -> None: ...

@overload
def create_effect(effect_fn: EffectFunction) -> Callable[[Observable[Action[Any]]], Effect[Any]]: ...

@overload
def create_effect(*, dispatch: bool = True) -> EffectDecorator: ...

def create_effect(effect_fn=None, *, dispatch: bool = True) -> Any: ...

class EffectsManager:
    """管理所有的 Effect 模組，負責註冊、取消和清理 Effect。"""
    
    store: Store[Any]
    subscriptions: List[Disposable]
    _effects_modules: List[Any]
    _subs_by_module: Dict[Any, List[Disposable]]
    _subs_by_effect: Dict[Tuple[Any, str], Disposable]
    
    def __init__(self, store: Store[Any]) -> None: ...
    
    def add_effects(self, *effects_items: Any) -> None: ...
    
    def _process_effects_item(self, item: Any) -> List[Any]: ...
    
    def _register_effects(self, modules: List[Any]) -> None: ...
    
    def _handle_effect_error(self, module: Any, name: str) -> Callable[[Exception, Observable], Observable]: ...
    
    def _dispatch_if_action(self, module: Any, effect_fn: Callable) -> Callable[[Any], None]: ...
    
    def remove_effects(self, *modules: Any) -> None: ...
    
    def cancel_effect(self, module: Any, effect_name: str) -> None: ...
    
    def _register_all_effects(self) -> None: ...
    
    def teardown(self) -> None: ...