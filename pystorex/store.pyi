"""
PyStoreX Store 模組的類型存根文件。
提供高精度的類型提示，無實際執行代碼。
"""

from typing import Dict, Callable, Any, Generic, TypeVar, Optional, List, Union, Tuple, type
from reactivex import Observable, Subject
from .reducers import ReducerFunction, ReducerManager
from .effects import EffectsManager
from .actions import Action
from .types import (
    S, T, DispatchFunction, StateSelector, NextDispatch,
    Middleware as MiddlewareProtocol
)

class Store(Generic[S]):
    """狀態容器，管理應用狀態並通知訂閱者狀態變更。"""
    
    _reducer_manager: ReducerManager
    _effects_manager: EffectsManager
    _state: Dict[str, Any]
    _action_subject: Subject
    _state_subject: Subject
    _middleware: List[Any]
    _raw_dispatch: Callable[[Action[Any]], Action[Any]]
    dispatch: DispatchFunction
    
    def __init__(self) -> None: ...
    
    def _update_state(self, new_state: Dict[str, Any]) -> None: ...
    
    def _dispatch_core(self, action: Action[Any]) -> Action[Any]: ...
    
    def _apply_middleware_chain(self) -> DispatchFunction: ...
    
    def _wrap_obj_middleware(self, mw: MiddlewareProtocol, next_dispatch: DispatchFunction) -> DispatchFunction: ...
    
    def apply_middleware(self, *middlewares: Union[type, MiddlewareProtocol]) -> None: ...
    
    def dispatch(self, action: Union[Action[Any], Callable]) -> Any: ...
    
    def select(self, selector: Optional[StateSelector[S, T]] = None) -> Observable: ...
    
    @property
    def state(self) -> S: ...
    
    def register_root(self, root_reducers: Dict[str, ReducerFunction]) -> None: ...
    
    def register_feature(self, feature_key: str, reducer: ReducerFunction) -> 'Store[S]': ...
    
    def unregister_feature(self, feature_key: str) -> 'Store[S]': ...
    
    def register_effects(self, *effects_modules: Any) -> None: ...
    
    def __enter__(self) -> 'Store[S]': ...
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...
    
    def teardown(self) -> None: ...


def create_store() -> Store[Dict[str, Any]]: ...


class StoreModule:
    """用於配置 Store 的工具類，類似於 NgRx 的 StoreModule。"""
    
    @staticmethod
    def register_root(reducers: Dict[str, ReducerFunction], store: Optional[Store[S]] = None) -> Store[S]: ...
    
    @staticmethod
    def register_feature(feature_key: str, reducer: ReducerFunction, store: Store[S]) -> Store[S]: ...
    
    @staticmethod
    def unregister_feature(feature_key: str, store: Store[S]) -> Store[S]: ...


class EffectsModule:
    """用於配置 Effects 的工具類，類似於 NgRx 的 EffectsModule。"""
    
    @staticmethod
    def register_root(effects_items: Any, store: Store[S]) -> Store[S]: ...
    
    @staticmethod
    def register_feature(effects_item: Any, store: Store[S]) -> Store[S]: ...