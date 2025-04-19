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
    去重：如果多次出現相同 id，則保留最後一個對象。
    :param entities: 包含多個實體的列表
    :return: 去重後的實體列表
    """
    uniq: Dict[Any, Dict[str, Any]] = {}
    for ent in entities:
        ent_id = ent.get("id")  # 使用實體的 id 作為唯一標識
        uniq[ent_id] = ent  # 保留最後一次出現的實體
    return list(uniq.values())


class EntityAdapter:
    """
    通用 EntityAdapter，提供一系列對集合（ids + entities）操作的方法。
    支援兩種初始狀態：
      - backend (DEV): 包含 last_settlement 元數據
      - basic: 只有 ids + entities
    """

    def __init__(self, use_for: str = "backend"):
        """
        初始化 EntityAdapter。
        :param use_for: 指定模式，'backend' 或 'basic'
        """
        assert use_for in ("backend", "basic"), "use_for 必須是 'backend' 或 'basic'"
        self.use_for = use_for

    def get_initial_state(self, state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        生成初始狀態。
        - basic: {'ids': [], 'entities': {}, **state}
        - backend: 在 basic 之上額外增加開發用的 last_settlement
        :param state: 可選的初始狀態字典
        :return: 初始化後的狀態字典
        """
        base = {"ids": [], "entities": {}}  # 基本結構
        if state:
            base.update(state)  # 合併傳入的狀態

        if self.use_for == "basic":
            return base

        # backend/DEV 模式，增加 last_settlement 和雜湊值
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

    # —— 輔助函式 —— #
    def _clone_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        深度拷貝狀態字典。
        :param state: 原始狀態字典
        :return: 深度拷貝後的狀態字典
        """
        return copy.deepcopy(state)

    # —— Reset last_settlement —— #
    def clone_and_reset(self, state: Dict[str, Any], action_id: Optional[str] = None) -> Dict[str, Any]:
        """
        深度拷貝 state 並重置 last_settlement（僅 backend 模式下有效）。
        :param state: 原始狀態字典
        :param action_id: 可選的操作 ID
        :return: 重置後的狀態字典
        """
        new_state = self._clone_state(state)
        if "last_settlement" in new_state:
            # 重置 last_settlement 的內容
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
        將單個實體加入集合（若已存在，則忽略）。
        :param entity: 要加入的實體
        :param state: 當前狀態字典
        :return: 更新後的狀態字典
        """
        new_state = self.clone_and_reset(state, action_id=None)
        ent_id = entity.get("id")
        if ent_id is None:
            raise ValueError("add_one: entity 必須包含 'id' 字段")

        if ent_id not in new_state["entities"]:
            # 新增實體到集合
            new_state["ids"].append(ent_id)
            new_state["entities"][ent_id] = entity
            self._mark_change(new_state, ent_id, "create")  # 標記為新增
        return new_state

    def add_many(self, entities: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        將多個實體加入集合（內部去重）。
        :param entities: 要加入的實體列表
        :param state: 當前狀態字典
        :return: 更新後的狀態字典
        """
        new_state = self.clone_and_reset(state, action_id=None)
        for ent in _make_entities_unique_by_id(entities):
            new_state = self.add_one(ent, new_state)  # 逐一加入
        return new_state

    def set_one(self, entity: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        替換或插入單個實體。
        :param entity: 要替換或插入的實體
        :param state: 當前狀態字典
        :return: 更新後的狀態字典
        """
        new_state = self.clone_and_reset(state, action_id=None)
        ent_id = entity.get("id")
        if ent_id is None:
            raise ValueError("set_one: entity 必須包含 'id' 字段")

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
        批量替換或插入實體列表。
        :param entities: 要替換或插入的實體列表
        :param state: 當前狀態字典
        :return: 更新後的狀態字典
        """
        new_state = self.clone_and_reset(state, action_id=None)
        for ent in _make_entities_unique_by_id(entities):
            new_state = self.set_one(ent, new_state)
        return new_state

    def set_all(self, entities: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        清空當前集合，並用提供的列表重新填充。
        :param entities: 要填充的實體列表
        :param state: 當前狀態字典
        :return: 更新後的狀態字典
        """
        new_state = self.clone_and_reset(state, action_id=None)
        # 刪除所有
        for _id in list(new_state["ids"]):
            new_state = self.remove_one(_id, new_state)
        # 再添加
        return self.add_many(entities, new_state)

    def remove_one(self, ent_id: Union[str, int], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        從集合中移除指定 id。
        :param ent_id: 要移除的實體 ID
        :param state: 當前狀態字典
        :return: 更新後的狀態字典
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
        :param ent_ids: 要移除的實體 ID 列表
        :param state: 當前狀態字典
        :return: 更新後的狀態字典
        """
        new_state = self.clone_and_reset(state, action_id=None)
        for eid in ent_ids:
            new_state = self.remove_one(eid, new_state)
        return new_state

    def remove_all(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        清空集合。
        :param state: 當前狀態字典
        :return: 更新後的狀態字典
        """
        return self.set_all([], state)

    def update_one(self, entity: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        對現有實體做部分或整體更新；不存在時忽略。
        :param entity: 要更新的實體
        :param state: 當前狀態字典
        :return: 更新後的狀態字典
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
        批量更新實體列表。
        :param entities: 要更新的實體列表
        :param state: 當前狀態字典
        :return: 更新後的狀態字典
        """
        new_state = self.clone_and_reset(state, action_id=None)
        for ent in entities:
            new_state = self.update_one(ent, new_state)
        return new_state

    def upsert_one(self, entity: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        如果存在則 update，否則添加。
        :param entity: 要 upsert 的實體
        :param state: 當前狀態字典
        :return: 更新後的狀態字典
        """
        new_state = self.clone_and_reset(state, action_id=None)
        ent_id = entity.get("id")
        if ent_id in new_state["entities"]:
            return self.update_one(entity, new_state)
        return self.add_one(entity, new_state)

    def upsert_many(self, entities: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        批量 upsert。
        :param entities: 要 upsert 的實體列表
        :param state: 當前狀態字典
        :return: 更新後的狀態字典
        """
        new_state = self.clone_and_reset(state, action_id=None)
        for ent in _make_entities_unique_by_id(entities):
            new_state = self.upsert_one(ent, new_state)
        return new_state

    # —— 內部：標記變更到 last_settlement —— #
    def _mark_change(self, state: Dict[str, Any], ent_id: Any, op: str) -> None:
        """
        在 last_settlement 中記錄 create/update/delete 的元信息。
        僅在 backend 模式下有效。
        :param state: 當前狀態字典
        :param ent_id: 實體的 ID
        :param op: 操作類型（'create', 'update', 'delete'）
        """
        if self.use_for != "backend":
            return  # 僅在 backend 模式下執行
        ls = state.get("last_settlement")
        if not ls:
            return
        ls["is_changed"] = True
        ls["action_id"] = ls.get("action_id") or str(uuid.uuid4())  # 設置操作 ID
        ls["date_time"] = time.time()  # 記錄操作時間
        ls[op].setdefault(ent_id, None)  # 記錄操作類型

def create_entity_adapter(use_for: str = "backend") -> EntityAdapter:
    """
    快速工廠方法：創建 backend 或 basic 模式的 EntityAdapter。
    :param use_for: 指定模式，'backend' 或 'basic'
    :return: EntityAdapter 實例
    """
    return EntityAdapter(use_for)
