from typing import Callable, Dict
from .entity_adapter import create_entity_adapter, EntityAdapter
from .reducers import create_reducer, on

# CRUD 方法對應到 adapter 的 attr 名稱
_CRUD_METHODS = {
    "AddOne":    "add_one",
    "AddMany":   "add_many",
    "SetOne":    "set_one",
    "SetMany":   "set_many",
    "SetAll":    "set_all",
    "RemoveOne": "remove_one",
    "RemoveMany":"remove_many",
    "RemoveAll": "remove_all",
    "UpdateOne": "update_one",
    "UpdateMany":"update_many",
    "UpsertOne": "upsert_one",
    "UpsertMany":"upsert_many",
}

def create_entity_reducer(
    entity_name: str,
    use_for: str = "backend"
) -> Callable:
    """
    建立一個針對 entity_name 的 reducer。

    - 初始 state 由 EntityAdapter.get_initial_state() 提供
    - 只要 dispatch(add_one("User", payload))，
      reducer 就會自動呼叫 adapter.add_one(payload, state)
    """
    # 1) 建立對應的 adapter
    adapter: EntityAdapter = create_entity_adapter(use_for)
    initial_state = adapter.get_initial_state()

    # 2) 根據 CRUD 方法自動生成 on(...) 處理器
    handlers = []
    for op, method_name in _CRUD_METHODS.items():
        action_type = f"[{entity_name}] {op}"
        # handler 必須 freeze method_name
        def make_handler(mname):
            return lambda state, action: getattr(adapter, mname)(action.payload, state)
        handlers.append(on(action_type, make_handler(method_name)))

    # 3) 回傳整合好的 reducer
    return create_reducer(initial_state, *handlers)
