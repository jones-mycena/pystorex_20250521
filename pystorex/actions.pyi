"""
PyStoreX Actions 模組的類型存根文件。
提供高精度的類型提示，無實際執行代碼。
"""

from typing import TypeVar, Generic, Callable, NamedTuple, Optional, Dict, Any, List, overload
from .types import E, P, ActionCreator, ActionCreatorWithoutPayload, ActionCreatorWithPayload

class Action(Generic[P], NamedTuple):
    type: str
    payload: Optional[P] = ...

@overload
def create_action(action_type: str) -> ActionCreatorWithoutPayload: ...

@overload
def create_action(action_type: str, prepare_fn: Callable[..., P]) -> ActionCreatorWithPayload[P]: ...

def create_action(action_type: str, prepare_fn: Optional[Callable[..., Any]] = None) -> ActionCreator[Any]: ...

# 根 Actions
init_store: ActionCreatorWithoutPayload
update_reducer: ActionCreatorWithoutPayload

# 實體 Actions - 泛型版本
add_one: ActionCreatorWithPayload[E]
add_many: ActionCreatorWithPayload[List[E]]
set_one: ActionCreatorWithPayload[E]
set_many: ActionCreatorWithPayload[List[E]]
set_all: ActionCreatorWithPayload[List[E]]
remove_one: ActionCreatorWithPayload[str]
remove_many: ActionCreatorWithPayload[List[str]]
remove_all: ActionCreatorWithoutPayload
update_one: ActionCreatorWithPayload[E]
update_many: ActionCreatorWithPayload[List[E]]
upsert_one: ActionCreatorWithPayload[E]
upsert_many: ActionCreatorWithPayload[List[E]]