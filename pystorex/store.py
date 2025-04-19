import inspect
from typing import Dict, Callable, Any, Generic, Type, TypeVar
from pydantic import BaseModel
from reactivex import Observable, operators as ops
from reactivex import Subject
from .reducers import Reducer, ReducerManager
from .effects import EffectsManager
from .actions import Action, init_store, update_reducer


S = TypeVar("S")


class Store(Generic[S]):
    """
    狀態容器，管理應用狀態並通知訂閱者狀態變更。
    支援 reducer 和 middleware 的動態註冊與狀態選擇。
    """

    def __init__(self):
        """
        初始化一個空的 Store 實例。

        初始化時會建立 reducer 管理器、effects 管理器，以及內部的狀態與動作流。
        """
        # 初始化 reducer 管理器
        self._reducer_manager = ReducerManager()
        # 初始化 effects 管理器，並將當前 Store 傳入
        self._effects_manager = EffectsManager(self)
        # 初始化內部狀態為空字典
        self._state = {}
        # 初始化動作流（Subject）
        self._action_subject = Subject()
        # 初始化狀態流（Subject）
        self._state_subject = Subject()
        # 初始化中介軟體列表
        self._middleware = []
        # 設定原始的 dispatch 方法
        self._raw_dispatch = self._dispatch_core
        # 構建中介軟體鏈後的 dispatch 方法
        self.dispatch = self._apply_middleware_chain()

        # 訂閱動作流，每次 dispatch 時更新狀態
        self._action_subject.subscribe(
            on_next=lambda action: self._update_state(
                self._reducer_manager.reduce(self._state, action)
            ),
            on_error=lambda err: print(f"存儲錯誤: {err}")  # 捕捉錯誤並打印
        )

    def _update_state(self, new_state):
        """
        更新內部狀態並通知訂閱者。

        Args:
            new_state: 新的狀態。
        """
        # 保存舊狀態
        old_state = self._state
        # 更新為新狀態
        self._state = new_state
        # 通知訂閱者，傳遞舊狀態與新狀態的元組
        self._state_subject.on_next((old_state, new_state))

    def _dispatch_core(self, action):
        """
        核心的 dispatch 方法，將動作傳遞給動作流。

        Args:
            action: 要分發的 Action。

        Returns:
            傳入的 Action。
        """
        self._action_subject.on_next(action)
        return action

    def _apply_middleware_chain(self):
        """
        構建中介軟體鏈，將中介軟體按順序包裹在 dispatch 方法外層。

        Returns:
            包裹後的 dispatch 方法。
        """
        # 從最後一個中介軟體開始包裹
        dispatch = self._raw_dispatch
        for mw in reversed(self._middleware):
            # 判斷中介軟體是函數還是物件
            if hasattr(mw, "on_next"):
                # 如果是物件，使用物件包裹方法
                dispatch = self._wrap_obj_middleware(mw, dispatch)
            else:
                # 如果是函數，直接調用工廠函數
                dispatch = mw(self)(dispatch)
        return dispatch

    def _wrap_obj_middleware(self, mw: Any, next_dispatch: Callable[[Action], Any]):
        """
        包裹物件型中介軟體。

        Args:
            mw: 中介軟體物件，需實現 on_next、on_complete 和 on_error 方法。
            next_dispatch: 下一層的 dispatch 方法。

        Returns:
            包裹後的 dispatch 方法。
        """
        def dispatch(action: Action):
            # 抓取 action 傳入前的舊狀態
            prev_state = self._state
            # 調用中介軟體的 on_next 方法
            mw.on_next(action, prev_state)

            try:
                # 真正分發到 reducer / effects
                result = next_dispatch(action)

                # 拿到 action 分發後的新狀態
                next_state = self._state
                # 調用中介軟體的 on_complete 方法
                mw.on_complete(next_state, action)
                return result

            except Exception as err:
                # 捕捉錯誤並調用中介軟體的 on_error 方法
                mw.on_error(err, action)
                raise

        return dispatch

    def apply_middleware(self, *middlewares):
        """
        一次註冊多個中介軟體，並重建 dispatch 鏈。

        Args:
            *middlewares: 要註冊的中介軟體，可以是類或實例。
        """
        # 接受類和實例，如果是類則直接實例化
        for m in middlewares:
            inst = m() if inspect.isclass(m) else m
            self._middleware.append(inst)
        # 重建 dispatch 鏈
        self.dispatch = self._apply_middleware_chain()

    def dispatch(self, action: Action):
        """
        分發一個動作，觸發狀態更新。

        Args:
            action: 要分發的 Action 物件。

        Returns:
            傳入的 Action。
        """
        # 分發動作給訂閱者
        self._action_subject.on_next(action)
        return action

    def select(self, selector: Callable[[S], Any] = None) -> Observable:
        """
        選擇狀態的一部分進行觀察。

        Args:
            selector: 一個函數，接收整個狀態並返回希望觀察的部分。

        Returns:
            一個可觀察對象，發送選定的狀態部分。
        """
        if selector is None:
            # 返回完整的狀態元組 (old_state, new_state)
            return self._state_subject.pipe(ops.ignore_elements())

        return self._state_subject.pipe(
            # 將元組 (old_state, new_state) 轉換為 (selector(old_state), selector(new_state))
            ops.map(
                lambda state_tuple: (selector(state_tuple[0]), selector(state_tuple[1]))
            ),
            # 只有當新狀態變化時才發出
            ops.distinct_until_changed(lambda x: x[1]),
        )

    @property
    def state(self) -> S:
        """
        獲取當前狀態的快照。

        Returns:
            當前狀態。
        """
        return self._state

    def register_root(self, root_reducers: Dict[str, Reducer]):
        """
        註冊應用的根級 reducers。

        Args:
            root_reducers: 特性鍵名到 reducer 的映射字典。
        """
        self._reducer_manager.add_reducers(root_reducers)
        # 初始化狀態
        self._state = self._reducer_manager.reduce(
            None, init_store()
        )

    def register_feature(self, feature_key: str, reducer: Reducer):
        """
        註冊一個特性模組的 reducer。

        Args:
            feature_key: 特性模組的鍵名。
            reducer: 特性模組的 reducer。
        """
        self._reducer_manager.add_reducer(feature_key, reducer)
        # 更新狀態以包含新特性
        self._state = self._reducer_manager.reduce(
            self._state, update_reducer()
        )
        return self

    def unregister_feature(self, feature_key: str):
        """
        卸載一個特性模組，包括其 reducer 和 effects。

        Args:
            feature_key: 特性模組的鍵名。
        """
        self._reducer_manager.remove_reducer(feature_key)
        # 重新計算一次狀態，去掉該特性
        self._state = self._reducer_manager.reduce(
            self._state, update_reducer()
        )
        # 同時從 EffectsManager 卸載所有來自該特性的 effects
        self._effects_manager.teardown()
        return self

    def register_effects(self, *effects_modules):
        """
        註冊一個或多個效果模組。

        Args:
            *effects_modules: 包含 effects 的模組或對象。
        """
        self._effects_manager.add_effects(*effects_modules)


def create_store() -> Store:
    """
    創建一個新的 Store 實例。

    Returns:
        Store: 新創建的 Store 實例。
    """
    return Store()


class StoreModule:
    """
    用於配置 Store 的工具類，類似於 NgRx 的 StoreModule。
    """

    @staticmethod
    def register_root(reducers: Dict[str, Reducer], store: Store = None):
        """
        註冊應用的根級 reducers。

        Args:
            reducers: 特性鍵名到 reducer 的映射字典。
            store: 可選的 Store 實例，如果不提供則創建新實例。

        Returns:
            配置好的 Store 實例。
        """
        if store is None:
            store = create_store()

        store.register_root(reducers)
        return store

    @staticmethod
    def register_feature(feature_key: str, reducer: Reducer, store: Store):
        """
        註冊一個特性模組的 reducer。

        Args:
            feature_key: 特性模組的鍵名。
            reducer: 特性模組的 reducer。
            store: 要註冊到的 Store 實例。

        Returns:
            更新後的 Store 實例。
        """
        store.register_feature(feature_key, reducer)
        return store

    @staticmethod
    def unregister_feature(feature_key: str, store: Store):
        """
        卸載一個特性模組，包括 reducer 和 effects。

        Args:
            feature_key: 特性模組的鍵名。
            store: 要操作的 Store 實例。

        Returns:
            更新後的 Store 實例。
        """
        store.unregister_feature(feature_key)
        return store


class EffectsModule:
    """
    用於配置 Effects 的工具類，類似於 NgRx 的 EffectsModule。
    """

    @staticmethod
    def register_root(effects_items, store: Store):
        """
        註冊根級的 effects。

        Args:
            effects_items: 可以是單個 effect 類/實例，或包含多個 effect 類/實例的列表。
            store: 要註冊到的 Store 實例。

        Returns:
            更新後的 Store 實例。
        """
        store.register_effects(effects_items)
        return store

    @staticmethod
    def register_feature(effects_item, store: Store):
        """
        註冊一個特性模組的 effects。

        Args:
            effects_item: 包含 effects 的類、實例或配置字典。
            store: 要註冊到的 Store 實例。

        Returns:
            更新後的 Store 實例。
        """
        store.register_effects(effects_item)
        return store
