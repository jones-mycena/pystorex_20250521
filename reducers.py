from typing import Dict, Any, Callable, TypeVar
from .actions import Action

S = TypeVar("S")
Reducer = Callable[[S, Action[Any]], S]

def create_reducer(initial_state: S, *handlers) -> Reducer[S]:
    """
    创建一个reducer函数
    
    Args:
        initial_state: 初始状态
        *handlers: 一系列(action_type, handler_fn)元组或者使用on函数创建的处理器
        
    Returns:
        一个reducer函数
    """
    action_handlers = {}
    
    for handler in handlers:
        if isinstance(handler, tuple) and len(handler) == 2:
            action_type, handler_fn = handler
            action_handlers[action_type] = handler_fn
        else:
            action_handlers.update(handler)
    
    def reducer(state: S = initial_state, action: Action = None) -> S:
        if action is None:
            return state
            
        handler = action_handlers.get(action.type)
        if handler:
            return handler(state, action)
        return state
    
    reducer.initial_state = initial_state
    reducer.handlers = action_handlers
    
    return reducer

def on(action_creator_or_type, handler):
    """
    创建一个关联Action类型和处理函数的映射
    
    Args:
        action_creator_or_type: Action创建器函数或Action类型字符串
        handler: 处理该Action的函数，接收(state, action)并返回新状态
        
    Returns:
        一个包含{action_type: handler}的字典
    """
    if callable(action_creator_or_type) and hasattr(action_creator_or_type, 'type'):
        action_type = action_creator_or_type.type
    else:
        action_type = str(action_creator_or_type)
    
    return {action_type: handler}

class ReducerManager:
    """
    管理应用中的所有 reducers，类似于 NgRx 的 MetaReducer
    """
    def __init__(self):
        self._feature_reducers = {}
        self._state = {}  # 存放最新整个 root state

    def add_reducer(self, feature_key: str, reducer: Reducer):
        self._feature_reducers[feature_key] = reducer
        self._state[feature_key] = reducer.initial_state

    def add_reducers(self, reducers: Dict[str, Reducer]):
        for key, r in reducers.items():
            self.add_reducer(key, r)

    def remove_reducer(self, feature_key: str):
        if feature_key in self._feature_reducers:
            del self._feature_reducers[feature_key]
            del self._state[feature_key]

    def get_reducers(self) -> Dict[str, Reducer]:
        return self._feature_reducers.copy()

    def reduce(self, state: Dict[str, Any] = None, action: Action = None) -> Dict[str, Any]:
        """
        使用所有注册的 reducers 处理 action 并返回新状态
        """
        # —— 修复点：第一次 state=None 时，改用内部 _state（已初始化为 {} or 初始 reducers 状态）
        if state is None:
            state = self._state

        # 浅拷贝，避免修改原 state
        new_state = state.copy()

        # 对每个 feature 调用它的 reducer
        for feature_key, reducer in self._feature_reducers.items():
            # 当前 substate，若之前没 key，就用 reducer.initial_state
            prev_substate = state.get(feature_key, reducer.initial_state)
            next_substate = reducer(prev_substate, action)

            # 只有真的变了才更新
            if next_substate is not prev_substate:
                new_state[feature_key] = next_substate

        # 保存最新 state
        self._state = new_state
        return new_state