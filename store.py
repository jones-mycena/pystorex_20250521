import inspect
from typing import Dict, Callable, Any, Generic, Type, TypeVar
from pydantic import BaseModel
from reactivex import Observable, operators as ops
from reactivex import Subject
from .reducers import Reducer, ReducerManager
from .effects import EffectsManager
from .actions import Action, create_action


S = TypeVar("S")


class Store(Generic[S]):
    """
    状态容器，管理应用状态并通知订阅者状态变更
    """

    def __init__(self):
        """初始化一个空的 Store"""

        self._reducer_manager = ReducerManager()
        self._effects_manager = EffectsManager(self)
        self._state = {}
        self._action_subject = Subject()
        self._state_subject = Subject()
        self._middleware = []
        self._raw_dispatch = self._dispatch_core
        self.dispatch = self._apply_middleware_chain()

        # 当新的action分发时，应用reducer并更新状态
        self._action_subject.pipe(
            ops.scan(
                lambda state, action: self._reducer_manager.reduce(state, action),
                self._state,
            )
        ).subscribe(
            on_next=self._update_state, on_error=lambda err: print(f"存储错误: {err}")
        )


    def _update_state(self, new_state):
        """更新内部状态并通知订阅者"""
        old_state = self._state
        self._state = new_state
        self._state_subject.on_next((old_state, new_state))  # 发送旧状态和新状态元组

    def _dispatch_core(self, action):
        self._action_subject.on_next(action)
        return action

    def _apply_middleware_chain(self):
        # 从最后一个 middleware 开始包裹
        dispatch = self._raw_dispatch
        for mw in reversed(self._middleware):
            # 支持函数式或面向对象的 middleware
            if hasattr(mw, "on_next"):
                # mw 是实例
                dispatch = self._wrap_obj_middleware(mw, dispatch)
            else:
                # mw 是工厂函数：store→next→dispatch
                dispatch = mw(self)(dispatch)
        return dispatch

    def _wrap_obj_middleware(self, mw: Any, next_dispatch: Callable[[Action], Any]):
        def dispatch(action: Action):
            mw.on_next(action)
            try:
                result = next_dispatch(action)
                mw.on_complete(result, action)
                return result
            except Exception as err:
                mw.on_error(err, action)
                raise

        return dispatch

    def apply_middleware(self, *middlewares):
        """一次注册多个 middleware，然后重建 dispatch 链"""
        # 接受类和实例，如果是类则直接实例化
        for m in middlewares:
            inst = m() if inspect.isclass(m) else m
            self._middleware.append(inst)
        self.dispatch = self._apply_middleware_chain()

    def dispatch(self, action: Action):
        """
        分发一个action，触发状态更新

        Args:
            action: 要分发的Action对象
        """
        # 首先记录动作日志
        # print(f"分发动作: {action.type} - 负载: {action.payload}")

        # 然后分发给订阅者
        self._action_subject.on_next(action)
        return action

    def select(self, selector: Callable[[S], Any] = None) -> Observable:
        """
        选择状态的一部分进行观察

        Args:
            selector: 一个函数，接收整个状态并返回希望观察的部分

        Returns:
            一个可观察对象，发送选定的状态部分
        """
        if selector is None:
            # 返回完整的状态元组 (old_state, new_state)
            return self._state_subject

        return self._state_subject.pipe(
            # 将元组 (old_state, new_state) 转换为 (selector(old_state), selector(new_state))
            ops.map(
                lambda state_tuple: (selector(state_tuple[0]), selector(state_tuple[1]))
            ),
            ops.distinct_until_changed(lambda x: x[1]),  # 只有当新状态变化时才发出
        )

    @property
    def state(self) -> S:
        """获取当前状态的快照"""
        return self._state

    def register_root(self, root_reducers: Dict[str, Reducer]):
        """
        注册应用的根级 reducers

        Args:
            root_reducers: 特性键名到 reducer 的映射字典
        """
        self._reducer_manager.add_reducers(root_reducers)
        # 初始化状态
        self._state = self._reducer_manager.reduce(
            None, create_action("@ngrx/store/init")
        )

    def register_feature(self, feature_key: str, reducer: Reducer):
        """
        注册一个特性模块的 reducer

        Args:
            feature_key: 特性模块的键名
            reducer: 特性模块的 reducer
        """
        self._reducer_manager.add_reducer(feature_key, reducer)
        # 更新状态以包含新特性
        self._state = self._reducer_manager.reduce(
            self._state, create_action("@ngrx/store/update-reducers")
        )
        return self

    def unregister_feature(self, feature_key: str):
        self._reducer_manager.remove_reducer(feature_key)
        # 重新计算一次 state，去掉该 feature
        self._state = self._reducer_manager.reduce(
            self._state, create_action("@ngrx/store/update-reducers")
        )
        # 同时从 EffectsManager 卸载所有来自该 feature 的 effects
        self._effects_manager.teardown()  # or provide a more granular remove_effects
        return self

    def register_effects(self, *effects_modules):
        """
        注册一个或多个效果模块

        Args:
            *effects_modules: 包含effects的模块或对象
        """
        self._effects_manager.add_effects(*effects_modules)


def create_store() -> Store:
    """
    用户在这里传入自己的 RootState 实例
    例如： create_store(MyRootModel())
    """
    return Store()


class StoreModule:
    """
    用于配置 Store 的工具类，类似于 NgRx 的 StoreModule
    """

    @staticmethod
    def register_root(reducers: Dict[str, Reducer], store: Store = None):
        """
        注册应用的根级 reducers

        Args:
            reducers: 特性键名到 reducer 的映射字典
            store: 可选的 Store 实例，如果不提供则创建新实例

        Returns:
            配置好的 Store 实例
        """
        if store is None:
            store = create_store()

        store.register_root(reducers)
        return store

    @staticmethod
    def register_feature(feature_key: str, reducer: Reducer, store: Store):
        """
        注册一个特性模块的 reducer

        Args:
            feature_key: 特性模块的键名
            reducer: 特性模块的 reducer
            store: 要注册到的 Store 实例

        Returns:
            更新后的 Store 实例
        """
        store.register_feature(feature_key, reducer)
        return store

    @staticmethod
    def unregister_feature(feature_key: str, store: Store):
        """卸载一个 feature，包括 reducer 和 effects"""
        store.unregister_feature(feature_key)
        return store


class EffectsModule:
    """
    用于配置 Effects 的工具类，类似于 NgRx 的 EffectsModule
    """

    @staticmethod
    def register_root(effects_items, store: Store):
        """
        注册根级的 effects

        Args:
            effects_items: 可以是单个 effect 类/实例，或包含多个 effect 类/实例的列表
            store: 要注册到的 Store 实例

        Returns:
            更新后的 Store 实例
        """
        store.register_effects(effects_items)
        return store

    @staticmethod
    def register_feature(effects_item, store: Store):
        """
        注册一个特性模块的 effects

        Args:
            effects_item: 包含 effects 的类、实例或配置字典
            store: 要注册到的 Store 实例

        Returns:
            更新后的 Store 实例
        """
        store.register_effects(effects_item)
        return store
