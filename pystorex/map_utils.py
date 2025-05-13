# pystorex/map_utils.py

from typing import Any, Callable, Dict, List
from immutables import Map

from .immutable_utils import to_immutable


def update_in(map_obj: Map, path: List[str], updater_fn: Callable[[Any], Any]) -> Map:
    """深層更新，保持路徑上的不可變性"""
    if not path:
        return map_obj
        
    if len(path) == 1:
        key = path[0]
        current = map_obj.get(key)
        new_value = updater_fn(current)
        # 確保新值也是不可變的
        return map_obj.set(key, to_immutable(new_value) if new_value is not current else current)
        
    key = path[0]
    rest_path = path[1:]
    
    # 獲取當前節點，如果不存在則創建空 Map
    current = map_obj.get(key, Map())
    if not isinstance(current, Map):
        # 非 Map 類型，轉換為 Map
        current = to_immutable(current) if current is not None else Map()
    
    # 遞迴更新
    updated = update_in(current, rest_path, updater_fn)
    return map_obj.set(key, updated)

def batch_update(map_obj: Map, updates: Dict[str, Any]) -> Map:
    """使用 evolver 高效批量更新"""
    # 創建 evolver 進行批量操作
    e = map_obj.mutate()
    
    # 批量設置值 (同時確保值是不可變的)
    for k, v in updates.items():
        e[k] = to_immutable(v)
    
    # 完成更新並返回新 Map
    return e.finish()