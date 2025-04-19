from typing import TypeVar, Generic, Callable, NamedTuple, Optional

P = TypeVar("P")

class Action(Generic[P], NamedTuple):
    type: str
    payload: Optional[P] = None  # 將 payload 設為可選屬性


def create_action(action_type: str, prepare_fn: Callable = None):
    """
    創建一個 Action 生成器函數
    
    Args:
        action_type: Action 的類型標識符
        prepare_fn: 可選的預處理函數，用於在創建 Action 前處理輸入參數
        
    Returns:
        一個可調用的函數，用於生成指定類型的 Action
    """
    def action_creator(*args, **kwargs):
        if prepare_fn:
            payload = prepare_fn(*args, **kwargs)
            return Action(type=action_type, payload=payload)
        elif len(args) == 1 and not kwargs:
            return Action(type=action_type, payload=args[0])
        elif args or kwargs:
            payload = dict(zip(range(len(args)), args))
            payload.update(kwargs)
            return Action(type=action_type, payload=payload)
        return Action(type=action_type, payload=None)  # 明確設置 payload 為 None
        
    action_creator.type = action_type
    
    return action_creator


init_store = create_action("[Root] Init Store")
update_reducer = create_action("[Root] Update Reducer")


from typing import Any, Dict, List
from .actions import create_action

# payload 都是 dict 或 list[dict]
add_one      = create_action("[Entity] AddOne",      lambda e: e)
add_many     = create_action("[Entity] AddMany",     lambda es: es)
set_one      = create_action("[Entity] SetOne",      lambda e: e)
set_many     = create_action("[Entity] SetMany",     lambda es: es)
set_all      = create_action("[Entity] SetAll",      lambda es: es)
remove_one   = create_action("[Entity] RemoveOne",   lambda id: id)
remove_many  = create_action("[Entity] RemoveMany",  lambda ids: ids)
remove_all   = create_action("[Entity] RemoveAll")   # 無 payload
update_one   = create_action("[Entity] UpdateOne",   lambda e: e)
update_many  = create_action("[Entity] UpdateMany",  lambda es: es)
upsert_one   = create_action("[Entity] UpsertOne",   lambda e: e)
upsert_many  = create_action("[Entity] UpsertMany",  lambda es: es)