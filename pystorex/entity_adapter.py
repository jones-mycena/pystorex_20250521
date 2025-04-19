# pystorex/entity_adapter.py

import copy
import time
import uuid
from typing import Any, Dict, List, Optional, Union

__all__ = [
    "create_entity_adapter",
    "EntityAdapter",
    "clone_and_reset",
]

def _make_entities_unique_by_id(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    去重：如果多次出现相同 id，则保留最后一个对象。
    """
    uniq: Dict[Any, Dict[str, Any]] = {}
    for ent in entities:
        ent_id = ent.get("id")
        uniq[ent_id] = ent
    return list(uniq.values())


class EntityAdapter:
    """
    通用 EntityAdapter，提供一系列对集合（ids + entities）操作的方法。
    支持两种初始状态：
      - backend (DEV): 包含 last_settlement 元数据
      - basic: 只有 ids + entities
    """

    def __init__(self, use_for: str = "backend"):
        assert use_for in ("backend", "basic"), "use_for 必须是 'backend' 或 'basic'"
        self.use_for = use_for

    def get_initial_state(self, state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        生成初始状态。
        - basic: {'ids': [], 'entities': {}, **state}
        - backend: 在 basic 之上额外增加开发用的 last_settlement
        """
        base = {"ids": [], "entities": {}}
        if state:
            base.update(state)

        if self.use_for == "basic":
            return base

        # backend/DEV 模式
        return {
            **base,
            "_previous_hash": None,
            "_current_hash": f"{uuid.uuid4()}",
            "last_settlement": {
                "is_changed": False,
                "action_id": None,
                "date_time": None,
                "create": {},
                "update": {},
                "delete": {},
            },
        }

    # —— 辅助函数 —— #
    def _clone_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return copy.deepcopy(state)

    # —— Reset last_settlement —— #
    def clone_and_reset(self, state: Dict[str, Any], action_id: Optional[str] = None) -> Dict[str, Any]:
        """
        深度拷贝 state 并重置 last_settlement（仅 backend 模式下有效）。
        action_id: 如果提供，则填入新的 last_settlement['action_id']
        """
        new_state = self._clone_state(state)
        if "last_settlement" in new_state:
            new_state["last_settlement"] = {
                "is_changed": False,
                "action_id": action_id,
                "date_time": None,
                "create": {},
                "update": {},
                "delete": {},
            }
        return new_state

    # —— ADD/SET/REMOVE/UPDATE/UPSERT 操作 —— #

    def add_one(self, entity: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        将单个实体加入集合（若已存在，则忽略）。
        """
        new_state = self.clone_and_reset(state, action_id=None)
        ent_id = entity.get("id")
        if ent_id is None:
            raise ValueError("add_one: entity 必须包含 'id' 字段")

        if ent_id not in new_state["entities"]:
            new_state["ids"].append(ent_id)
            new_state["entities"][ent_id] = entity
            self._mark_change(new_state, ent_id, "create")
        return new_state

    def add_many(self, entities: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        将多个实体加入集合（内部去重）。
        """
        new_state = self.clone_and_reset(state, action_id=None)
        for ent in _make_entities_unique_by_id(entities):
            new_state = self.add_one(ent, new_state)
        return new_state

    def set_one(self, entity: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        替换或插入单个实体。
        """
        new_state = self.clone_and_reset(state, action_id=None)
        ent_id = entity.get("id")
        if ent_id is None:
            raise ValueError("set_one: entity 必须包含 'id' 字段")

        old = new_state["entities"].get(ent_id)
        if old != entity:
            if ent_id not in new_state["entities"]:
                new_state["ids"].append(ent_id)
                self._mark_change(new_state, ent_id, "create")
            else:
                self._mark_change(new_state, ent_id, "update")
            new_state["entities"][ent_id] = entity
        return new_state

    def set_many(self, entities: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        批量替换或插入实体列表。
        """
        new_state = self.clone_and_reset(state, action_id=None)
        for ent in _make_entities_unique_by_id(entities):
            new_state = self.set_one(ent, new_state)
        return new_state

    def set_all(self, entities: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        清空当前集合，并用提供的列表重新填充。
        """
        new_state = self.clone_and_reset(state, action_id=None)
        # 删除所有
        for _id in list(new_state["ids"]):
            new_state = self.remove_one(_id, new_state)
        # 再添加
        return self.add_many(entities, new_state)

    def remove_one(self, ent_id: Union[str, int], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        从集合中移除指定 id。
        """
        new_state = self.clone_and_reset(state, action_id=None)
        if ent_id in new_state["entities"]:
            del new_state["entities"][ent_id]
            new_state["ids"].remove(ent_id)
            self._mark_change(new_state, ent_id, "delete")
        return new_state

    def remove_many(self, ent_ids: List[Union[str, int]], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        批量移除指定 id 列表。
        """
        new_state = self.clone_and_reset(state, action_id=None)
        for eid in ent_ids:
            new_state = self.remove_one(eid, new_state)
        return new_state

    def remove_all(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        清空集合。
        """
        return self.set_all([], state)

    def update_one(self, entity: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        对现有实体做部分或整体更新；不存在时忽略。
        """
        new_state = self.clone_and_reset(state, action_id=None)
        ent_id = entity.get("id")
        if ent_id in new_state["entities"]:
            old = new_state["entities"][ent_id]
            merged = {**old, **entity}
            if merged != old:
                new_state["entities"][ent_id] = merged
                self._mark_change(new_state, ent_id, "update")
        return new_state

    def update_many(self, entities: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        批量更新实体列表。
        """
        new_state = self.clone_and_reset(state, action_id=None)
        for ent in entities:
            new_state = self.update_one(ent, new_state)
        return new_state

    def upsert_one(self, entity: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        如果存在则 update，否则添加。
        """
        new_state = self.clone_and_reset(state, action_id=None)
        ent_id = entity.get("id")
        if ent_id in new_state["entities"]:
            return self.update_one(entity, new_state)
        return self.add_one(entity, new_state)

    def upsert_many(self, entities: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        批量 upsert。
        """
        new_state = self.clone_and_reset(state, action_id=None)
        for ent in _make_entities_unique_by_id(entities):
            new_state = self.upsert_one(ent, new_state)
        return new_state

    # —— 内部：标记变更到 last_settlement —— #
    def _mark_change(self, state: Dict[str, Any], ent_id: Any, op: str) -> None:
        """
        在 last_settlement 中记录 create/update/delete 的元信息。
        仅在 backend 模式下有效。
        """
        if self.use_for != "backend":
            return
        ls = state.get("last_settlement")
        if not ls:
            return
        ls["is_changed"] = True
        ls["action_id"] = ls.get("action_id") or str(uuid.uuid4())
        ls["date_time"] = time.time()
        ls[op].setdefault(ent_id, None)


def create_entity_adapter(use_for: str = "backend") -> EntityAdapter:
    """
    快速工厂：backend 或 basic。
    """
    return EntityAdapter(use_for)
