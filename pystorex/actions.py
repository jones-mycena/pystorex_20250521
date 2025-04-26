"""
基於 PyStoreX 的 Action 定義模組。

此模組提供 Action 類別以及創建 Action 的功能。
Actions 是描述狀態變更意圖的不可變對象。
"""

from typing import  Generic, Callable, List, NamedTuple, Optional, Dict,  Any, Union,  overload
from .types import E, P, ActionCreator, ActionCreatorWithoutPayload, ActionCreatorWithPayload

class Action(Generic[P], NamedTuple):
    """
    表示一個有類型和可選負載的動作。
    
    泛型參數:
        P: 負載的類型
    
    屬性:
        type: 動作的類型字符串
        payload: 動作的負載數據（可選）
    """
    type: str
    payload: Optional[P] = None


@overload
def create_action(action_type: str) -> ActionCreatorWithoutPayload:
    """
    創建一個無負載的 Action 生成器函數。
    
    Args:
        action_type: Action 的類型標識符
        
    Returns:
        一個可調用的函數，用於生成指定類型的 Action，無負載
    """
    ...

@overload
def create_action(action_type: str, prepare_fn: Callable[..., P]) -> ActionCreatorWithPayload[P]:
    """
    創建一個帶負載的 Action 生成器函數。
    
    Args:
        action_type: Action 的類型標識符
        prepare_fn: 預處理函數，用於在創建 Action 前處理輸入參數
        
    Returns:
        一個可調用的函數，用於生成指定類型的 Action，帶負載
    """
    ...

def create_action(action_type: str, prepare_fn: Optional[Callable[..., Any]] = None)  -> ActionCreator[Any]:
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
            return Action(type=action_type, payload=payload)
        elif len(args) == 1 and not kwargs:
            return Action(type=action_type, payload=args[0])
        elif args or kwargs:
            payload: Dict[Union[int, str], Any] = dict(zip(range(len(args)), args))
            payload.update(kwargs)
            return Action(type=action_type, payload=payload)
        return Action(type=action_type, payload=None)
        
    # 添加 type 屬性以便於識別
    action_creator.type = action_type  # type: ignore
    
    return action_creator


# 根 Actions
init_store: ActionCreatorWithoutPayload  = create_action("[Root] Init Store")
update_reducer: ActionCreatorWithoutPayload = create_action("[Root] Update Reducer")


# 實體 Actions
# payload 都是 dict 或 list[dict]
add_one: ActionCreatorWithPayload[E] = create_action("[Entity] AddOne", lambda e: e)
add_many: ActionCreatorWithPayload[List[E]] = create_action("[Entity] AddMany", lambda es: es)
set_one: ActionCreatorWithPayload[E] = create_action("[Entity] SetOne", lambda e: e)
set_many: ActionCreatorWithPayload[List[E]] = create_action("[Entity] SetMany", lambda es: es)
set_all: ActionCreatorWithPayload[List[E]] = create_action("[Entity] SetAll", lambda es: es)
remove_one: ActionCreatorWithPayload[str] = create_action("[Entity] RemoveOne", lambda id: id)
remove_many: ActionCreatorWithPayload[List[str]] = create_action("[Entity] RemoveMany", lambda ids: ids)
remove_all: ActionCreatorWithoutPayload = create_action("[Entity] RemoveAll")   # 無 payload
update_one: ActionCreatorWithPayload[E] = create_action("[Entity] UpdateOne", lambda e: e)
update_many: ActionCreatorWithPayload[List[E]] = create_action("[Entity] UpdateMany", lambda es: es)
upsert_one: ActionCreatorWithPayload[E] = create_action("[Entity] UpsertOne", lambda e: e)
upsert_many: ActionCreatorWithPayload[List[E]] = create_action("[Entity] UpsertMany", lambda es: es)