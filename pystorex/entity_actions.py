from typing import Any
from .actions import Action

def create_entity_action(op: str):
    """
    生成一個通用的 Entity‐CRUD Action Creator。
    op: AddOne, AddMany, SetOne, ...
    用法：
        add_one = create_entity_action("AddOne")
        act = add_one("User", {"id":"u1","name":"Alice"})
        act.type == "[User] AddOne"
        act.payload == {"id":"u1","name":"Alice"}
    """
    def creator(entity_name: str, payload: Any = None) -> Action[Any]:
        return Action(type=f"[{entity_name}] {op}", payload=payload)
    # 為方便識別，也可把 op 暴露出來
    creator.op = op
    return creator

# 建立各個 Op 的 Action Creator
add_one     = create_entity_action("AddOne")
add_many    = create_entity_action("AddMany")
set_one     = create_entity_action("SetOne")
set_many    = create_entity_action("SetMany")
set_all     = create_entity_action("SetAll")
remove_one  = create_entity_action("RemoveOne")
remove_many = create_entity_action("RemoveMany")
remove_all  = create_entity_action("RemoveAll")
update_one  = create_entity_action("UpdateOne")
update_many = create_entity_action("UpdateMany")
upsert_one  = create_entity_action("UpsertOne")
upsert_many = create_entity_action("UpsertMany")
