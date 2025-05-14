from typing import Any, Callable, List, TypeVar, Union, Protocol
from reactivex import Observable, operators as ops

class ActionLike(Protocol):
    """定義類似 Action 的協議類型"""
    type: str

T = TypeVar("T", bound=ActionLike)
ActionOrType = Union[T, str]

def ofType(*actions_or_types: ActionOrType) -> Callable[[Observable[T]], Observable[T]]:
    """
    自訂 operator，根據指定的 action 類型進行過濾。
    
    類似於 NgRx 的 ofType 操作符，用於在效果流程中過濾特定類型的 actions。
    
    Args:
        *actions_or_types: 一個或多個 action 物件或 action type 字串。
    
    Returns:
        一個 operator，過濾出符合條件的 actions。
    """
    action_types = set()
    
    for item in actions_or_types:
        if isinstance(item, str):
            action_types.add(item)
        elif hasattr(item, 'type'):
            action_types.add(item.type)
        else:
            raise TypeError(f"Unsupported type: {type(item)}. Expected action object with 'type' attribute or string.")
    
    if not action_types:
        raise ValueError("At least one action type must be specified.")
    
    # 凍結集合以提高效能
    frozen_types = frozenset(action_types)
    
    # 返回過濾 operator
    return ops.filter(lambda action: hasattr(action, 'type') and action.type in frozen_types)
