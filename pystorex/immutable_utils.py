# pystorex/immutable_utils.py
from typing import Any, Type, TypeVar,  overload, get_type_hints
from typing_extensions import TypedDict
from immutables import Map
from pydantic import BaseModel, create_model

T = TypeVar('T', bound=BaseModel)
TD = TypeVar("TD", bound=TypedDict) # type: ignore

def to_immutable(obj: Any) -> Map:
    """將任何對象轉換為不可變形式 (包括 Pydantic 模型)"""
    if isinstance(obj, BaseModel):
        # Pydantic 模型轉為 Map
        return Map({k: to_immutable(v) for k, v in obj.model_dump().items()})
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



def to_dict(obj: Any) -> dict:
    """將 Map 及其巢狀結構轉換為普通字典"""
    if isinstance(obj, Map):
        return {k: to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, tuple):
        return [to_dict(i) for i in obj]
    elif isinstance(obj, frozenset):
        return {to_dict(i) for i in obj}
    return obj


@overload
def to_pydantic(map_obj: Map, model_class: Type[T]) -> T:
    ...

@overload
def to_pydantic(map_obj: Map, typed_dict: Type[TD], *, defaults: dict[str, Any] | None = None) -> BaseModel:
    ...

def to_pydantic(
    map_obj: Map,
    model_class_or_typed_dict: Type[BaseModel] | Type[TypedDict], # type: ignore
    *,
    defaults: dict[str, Any] | None = None
) -> BaseModel:
    """
    將 Map 轉換為 Pydantic 模型，支持兩種方式：
    1. 使用指定的 Pydantic 模型類 (model_class)。
    2. 根據 TypedDict 動態生成 Pydantic 模型。

    參數：
        map_obj: immutables.Map 物件
        model_class_or_typed_dict: Pydantic 模型類或 TypedDict 類
        defaults: 僅用於 TypedDict，指定預設值

    返回：
        Pydantic 模型實例
    """
    # 將 Map 轉為普通字典
    data_dict = to_dict(map_obj)

    # 情況 1：傳入的是 Pydantic 模型類
    if isinstance(model_class_or_typed_dict, type) and issubclass(model_class_or_typed_dict, BaseModel):
        return model_class_or_typed_dict(**data_dict)

    # 情況 2：傳入的是 TypedDict
    if isinstance(model_class_or_typed_dict, type) and hasattr(model_class_or_typed_dict, "__annotations__"):
        defaults = defaults or {}
        # 提取 TypedDict 的型別註解
        annotations = get_type_hints(model_class_or_typed_dict)
        # 構建 Pydantic 欄位
        fields = {}
        for name, annotation in annotations.items():
            # 如果 data_dict 中有值，優先使用；否則使用 defaults
            default = data_dict.get(name, defaults.get(name, None))
            fields[name] = (annotation, default)

        # 動態生成 Pydantic 模型
        pydantic_model = create_model(
            f"{model_class_or_typed_dict.__name__}Model",
            __base__=BaseModel,
            **fields
        )
        return pydantic_model(**data_dict)

    raise ValueError("Second argument must be a Pydantic model class or TypedDict")