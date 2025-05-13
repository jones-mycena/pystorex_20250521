# pystorex/immutable_utils.py
from typing import Any, Dict, Type, TypeVar, Union, Optional, List, Tuple
from immutables import Map
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

def to_immutable(obj: Any) -> Any:
    """將任何對象轉換為不可變形式 (包括 Pydantic 模型)"""
    if isinstance(obj, BaseModel):
        # Pydantic 模型轉為 Map
        return Map({k: to_immutable(v) for k, v in obj.dict().items()})
    elif isinstance(obj, dict):
        # 字典轉為 Map
        return Map({k: to_immutable(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        # 列表轉為元組
        return tuple(to_immutable(i) for i in obj)
    elif isinstance(obj, (set, frozenset)):
        # 集合轉為凍結集合
        return frozenset(to_immutable(i) for i in obj)
    # 其他類型直接返回
    return obj

def to_pydantic(map_obj: Map, model_class: Type[T]) -> T:
    """將 Map 轉換回 Pydantic 模型 (僅在需要時使用)"""
    # 將 Map 轉為字典
    data_dict = to_dict(map_obj)
    # 使用字典建立 Pydantic 模型
    return model_class(**data_dict)

def to_dict(obj: Any) -> Any:
    """將 Map 及其巢狀結構轉換為普通字典"""
    if isinstance(obj, Map):
        return {k: to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, tuple):
        return [to_dict(i) for i in obj]
    elif isinstance(obj, frozenset):
        return {to_dict(i) for i in obj}
    return obj