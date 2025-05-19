"""
PyStoreX 的類型定義模組。

此模組集中定義了 PyStoreX 庫中使用的所有類型，以提供更好的 IDE 類型提示。
所有模組使用的類型都集中在這裡，確保一致性和互操作性。
"""

from typing import (
    TypeVar, Generic, Callable, Dict, List, Optional, Union, 
    Protocol, Any, TypedDict, runtime_checkable, Tuple, Literal,
    Final, cast, overload
)
from reactivex import Observable
from reactivex.disposable import Disposable
from reactivex import Subject

# ----------------------
# 基礎類型變量
# ----------------------
S = TypeVar('S')  # 狀態類型
P = TypeVar('P')  # 負載類型
T = TypeVar('T')  # 返回值/選擇器類型
R = TypeVar('R')  # 結果類型
E = TypeVar('E')  # 實體類型

# ----------------------
# Action 相關類型
# ----------------------
ActionType = str
ActionCreator = Callable[..., 'Action[P]']
ActionCreatorWithoutPayload = Callable[[], 'Action[None]']
ActionCreatorWithPayload = Callable[..., 'Action[P]']

class Action(Generic[P]):
    """表示一個有類型和可選負載的動作。"""
    type: str
    payload: Optional[P]

# ----------------------
# Reducer 相關類型
# ----------------------
ReducerFunction = Callable[[S, Action[Any]], S]
ActionHandler = Callable[[S, Action[P]], S]
HandlerMap = Dict[str, ActionHandler]

@runtime_checkable
class Reducer(Protocol, Generic[S]):
    """Reducer 接口協議。"""
    def __call__(self, state: S, action: Action[Any]) -> S: ...
    
    @property
    def initial_state(self) -> S: ...
    
    @property
    def handlers(self) -> HandlerMap: ...

# ----------------------
# Effect 相關類型
# ----------------------
EffectFunction = Callable[[Observable[Action[Any]]], Observable[Any]]
EffectCreator = Callable[..., EffectFunction]
EffectDecorator = Callable[[EffectFunction], Callable[[Observable[Action[Any]]], 'Effect[Any]']]

class Effect(Generic[T]):
    """表示一個副作用處理函數的封裝類別。"""
    source: Observable[T]

@runtime_checkable
class EffectClass(Protocol):
    """Effect 類接口協議。"""
    def __init__(self) -> None: ...

@runtime_checkable
class EffectMethod(Protocol):
    """Effect 方法接口協議。"""
    is_effect: bool
    dispatch: bool
    is_instance_method: bool
    
    def __call__(self, *args: Any, **kwargs: Any) -> Effect[Any]: ...

# ----------------------
# Store 相關類型
# ----------------------
StateSelector = Callable[[S], T]
StoreSubscriber = Callable[[T], None]
StoreUnsubscribe = Callable[[], None]
DispatchFunction = Callable[[Union[Action[Any], Callable]], Any]

class Store(Generic[S]):
    """狀態容器，管理應用狀態並通知訂閱者狀態變更。"""
    
    _state: S
    _action_subject: Subject
    _state_subject: Subject
    
    @property
    def state(self) -> S: ...
    
    def dispatch(self, action: Union[Action[Any], Callable]) -> Any: ...
    
    def select(self, selector: Optional[StateSelector[S, T]] = None) -> Observable[Union[Tuple[S, S], Tuple[T, T]]]: ...
    
    def register_root(self, root_reducers: Dict[str, 'Reducer']) -> None: ...
    
    def register_feature(self, feature_key: str, reducer: 'Reducer') -> 'Store[S]': ...
    
    def unregister_feature(self, feature_key: str) -> 'Store[S]': ...
    
    def register_effects(self, *effects_modules: Any) -> None: ...
    
    def apply_middleware(self, *middlewares: Any) -> None: ...

# ----------------------
# Middleware 相關類型
# ----------------------
NextDispatch = Callable[[Action[Any]], Any]
MiddlewareFunction = Callable[[NextDispatch], DispatchFunction]
MiddlewareFactory = Callable[[Store[Any]], MiddlewareFunction]
class ActionContext(TypedDict):
    action: Any
    prev_state: Any
    next_state: Optional[Any]
    result: Optional[Any]
    error: Optional[Exception]
@runtime_checkable
class Middleware(Protocol):
    """中介軟體接口協議。"""
    def on_next(self, action: Action[Any], prev_state: Any) -> None: ...
    def on_complete(self, next_state: Any, action: Action[Any]) -> None: ...
    def on_error(self, error: Exception, action: Action[Any]) -> None: ...
    
    def __call__(self, store: Store[Any]) -> MiddlewareFunction: ...

# ----------------------
# Thunk 相關類型
# ----------------------
GetState = Callable[[], S]
ThunkFunction = Callable[[DispatchFunction, GetState], Any]

# ----------------------
# Selector 相關類型
# ----------------------
Input = TypeVar('Input')  # 選擇器輸入類型
Output = TypeVar('Output')  # 選擇器輸出類型

ResultSelector = Callable[..., R]  # 將多個選擇器的結果組合為 R 類型的值
MemoizedSelector = Callable[[Any], Any]  # 帶記憶功能的選擇器函數

# 選擇器創建函數的類型
SelectorCreator1 = Callable[
    [StateSelector[Input, Output], bool, Optional[float]],
    StateSelector[Input, Output]
]  # 單一選擇器

SelectorCreatorN = Callable[
    [List[StateSelector[Input, Any]], ResultSelector[Output], bool, Optional[float]],
    StateSelector[Input, Output]
]  # 多選擇器 + 結果函數

# ----------------------
# 實體相關類型
# ----------------------
class EntityState(TypedDict, Generic[E]):
    """代表實體集合的狀態。"""
    ids: List[str]
    entities: Dict[str, E]
    loading: bool
    loaded: bool
    error: Optional[str]

# ----------------------
# 其他通用類型
# ----------------------
ActionStatus = Literal["pending", "fulfilled", "rejected"]  # 異步動作狀態

# 複合類型
AsyncAction = Callable[[], Tuple[ActionType, Any]]
AsyncActionCreator = Callable[..., AsyncAction]