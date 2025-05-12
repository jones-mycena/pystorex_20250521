"""
基於 PyStoreX 的 Action 定義模組。

此模組提供 Action 類別以及創建 Action 的功能。
Actions 是描述狀態變更意圖的不可變對象。
"""
from typing import Generic, Callable, List, Optional, Dict, Any, Union, overload, TypeVar
from .types import E, P, ActionCreator, ActionCreatorWithoutPayload, ActionCreatorWithPayload

try:
    from immutables import Map as ImmutableMap
    HAS_IMMUTABLES = True
except ImportError:
    HAS_IMMUTABLES = False
    ImmutableMap = Dict  # 類型別名，實際使用普通 dict


class Action(Generic[P]):
    """
    表示一個有類型和可選負載的動作。
    
    泛型參數:
        P: 負載的類型
    
    屬性:
        type: 動作的類型字符串
        payload: 動作的負載數據（可選）
    """
    __slots__ = ('type', 'payload')
    
    def __init__(self, type: str, payload: Optional[P] = None):
        super().__setattr__('type', type)
        super().__setattr__('payload', payload)
    
    def __setattr__(self, name, value):
        if name not in self.__slots__:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        if hasattr(self, name):
            raise AttributeError(f"Cannot modify immutable instance attribute '{name}'")
        super().__setattr__(name, value)
    
    def __eq__(self, other):
        if not isinstance(other, Action):
            return False
        return self.type == other.type and self.payload == other.payload
    
    def __hash__(self):
        return hash((self.type, self.payload))
    
    def __repr__(self):
        return f"Action(type='{self.type}', payload={repr(self.payload)})"


class ActionPool:
    """
    Action 對象池，用於重用頻繁創建的相同 Action 對象。
    主要針對無負載或簡單負載的 Action 進行池化。
    """
    _no_payload_pool: Dict[str, Action] = {}  # type -> Action (無負載)
    _simple_payload_pool: Dict[str, Dict[Any, Action]] = {}  # type -> {payload -> Action}
    
    @classmethod
    def get(cls, action_type: str, payload: Any = None) -> Action:
        """
        從池中獲取 Action 對象，如不存在則創建並加入池中。
        
        Args:
            action_type: Action 的類型
            payload: Action 的負載，默認為 None
            
        Returns:
            Action 對象
        """
        # 無負載 Action 池化
        if payload is None:
            if action_type in cls._no_payload_pool:
                return cls._no_payload_pool[action_type]
            
            action = Action(action_type, None)
            cls._no_payload_pool[action_type] = action
            return action
        
        # 簡單負載 Action 池化 (僅支持可哈希的基本類型)
        if isinstance(payload, (int, str, bool, float, tuple, frozenset)) or payload is None:
            if action_type not in cls._simple_payload_pool:
                cls._simple_payload_pool[action_type] = {}
                
            payload_pool = cls._simple_payload_pool[action_type]
            if payload in payload_pool:
                return payload_pool[payload]
            
            action = Action(action_type, payload)
            payload_pool[payload] = action
            return action
        
        # 複雜負載不池化，直接創建新對象
        return Action(action_type, payload)


def _process_payload(payload: Any) -> Any:
    """
    處理 payload，將字典轉換為不可變結構（如有可能）。
    
    Args:
        payload: 原始 payload
        
    Returns:
        處理後的 payload
    """
    if HAS_IMMUTABLES and isinstance(payload, dict):
        return ImmutableMap(payload)
    return payload


@overload
def create_action(action_type: str) -> 'ActionCreatorWithoutPayload':
    """
    創建一個無負載的 Action 生成器函數。
    
    Args:
        action_type: Action 的類型標識符
        
    Returns:
        一個可調用的函數，用於生成指定類型的 Action，無負載
    """
    ...


@overload
def create_action(action_type: str, prepare_fn: Callable[..., P]) -> 'ActionCreatorWithPayload[P]':
    """
    創建一個帶負載的 Action 生成器函數。
    
    Args:
        action_type: Action 的類型標識符
        prepare_fn: 預處理函數，用於在創建 Action 前處理輸入參數
        
    Returns:
        一個可調用的函數，用於生成指定類型的 Action，帶負載
    """
    ...


def create_action(action_type: str, prepare_fn: Optional[Callable[..., Any]] = None) -> 'ActionCreator[Any]':
    """
    創建一個 Action 生成器函數。
    
    Args:
        action_type: Action 的類型標識符
        prepare_fn: 可選的預處理函數，用於在創建 Action 前處理輸入參數
        
    Returns:
        一個可調用的函數，用於生成指定類型的 Action
    
    範例:
        >>> increment = create_action("[Counter] Increment")
        >>> increment()  # 返回 Action(type="[Counter] Increment", payload=None)
        >>> 
        >>> add = create_action("[Counter] Add", lambda amount: amount)
        >>> add(5)  # 返回 Action(type="[Counter] Add", payload=5)
    """
    def action_creator(*args: Any, **kwargs: Any) -> Action[Any]:
        if prepare_fn:
            payload = prepare_fn(*args, **kwargs)
            payload = _process_payload(payload)
            return ActionPool.get(action_type, payload)
        elif len(args) == 1 and not kwargs:
            payload = args[0]
            payload = _process_payload(payload)
            return ActionPool.get(action_type, payload)
        elif args or kwargs:
            payload: Dict[Union[int, str], Any] = dict(zip(range(len(args)), args))
            payload.update(kwargs)
            payload = _process_payload(payload)
            return ActionPool.get(action_type, payload)
        
        # 無參數，無負載
        return ActionPool.get(action_type)
        
    # 添加 type 屬性以便於識別
    action_creator.type = action_type  # type: ignore
    
    return action_creator


# 根 Actions
init_store: ActionCreatorWithoutPayload = create_action("[Root] Init Store")
update_reducer: ActionCreatorWithoutPayload = create_action("[Root] Update Reducer")


# 實體 Actions
# payload 都是 dict 或 list[dict]
add_one: 'ActionCreatorWithPayload[E]' = create_action("[Entity] AddOne", lambda e: e)
add_many: 'ActionCreatorWithPayload[List[E]]' = create_action("[Entity] AddMany", lambda es: es)
set_one: 'ActionCreatorWithPayload[E]' = create_action("[Entity] SetOne", lambda e: e)
set_many: 'ActionCreatorWithPayload[List[E]]' = create_action("[Entity] SetMany", lambda es: es)
set_all: 'ActionCreatorWithPayload[List[E]]' = create_action("[Entity] SetAll", lambda es: es)
remove_one: 'ActionCreatorWithPayload[str]' = create_action("[Entity] RemoveOne", lambda id: id)
remove_many: 'ActionCreatorWithPayload[List[str]]' = create_action("[Entity] RemoveMany", lambda ids: ids)
remove_all: 'ActionCreatorWithoutPayload' = create_action("[Entity] RemoveAll")  # 無 payload
update_one: 'ActionCreatorWithPayload[E]' = create_action("[Entity] UpdateOne", lambda e: e)
update_many: 'ActionCreatorWithPayload[List[E]]' = create_action("[Entity] UpdateMany", lambda es: es)
upsert_one: 'ActionCreatorWithPayload[E]' = create_action("[Entity] UpsertOne", lambda e: e)
upsert_many: 'ActionCreatorWithPayload[List[E]]' = create_action("[Entity] UpsertMany", lambda es: es)