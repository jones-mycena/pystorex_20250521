"""
基於 PyStoreX 的 Store 定義模組。

此模組提供狀態容器的核心實現，包括狀態管理、動作分發、
中介軟體支持以及與 Reducer 和 Effects 的交互機制。
"""

import inspect
from typing import Dict, Callable, Any, Generic, Optional, List, Union, cast
from reactivex import Observable, operators as ops
from reactivex import Subject
from .errors import StoreError, global_error_handler, handle_error
from .reducers import ReducerFunction, ReducerManager
from .effects import EffectsManager
from .actions import Action, init_store, update_reducer
from .types import (
    S, T, DispatchFunction, StateSelector, NextDispatch, 
    Middleware as MiddlewareProtocol, MiddlewareFunction
)

class Store(Generic[S]):
    """
    狀態容器，管理應用狀態並通知訂閱者狀態變更。
    支援 reducer 和 middleware 的動態註冊與狀態選擇。
    
    泛型參數:
        S: 狀態類型，通常是字典或嵌套結構
        
    屬性:
        state: 當前狀態的快照，唯讀屬性
        
    範例:
        ```python
        # 創建一個簡單的計數器 store
        from pystorex import create_store, create_reducer, create_action, on
        
        # 定義 actions
        increment = create_action("[Counter] Increment")
        decrement = create_action("[Counter] Decrement")
        
        # 定義初始狀態和 reducer
        counter_reducer = create_reducer(
            0,  # 初始狀態
            on(increment, lambda state, action: state + 1),
            on(decrement, lambda state, action: state - 1)
        )
        
        # 創建並配置 store
        store = create_store()
        store.register_root({"counter": counter_reducer})
        
        # 使用 store
        print(store.state)  # {"counter": 0}
        store.dispatch(increment())
        print(store.state)  # {"counter": 1}
        
        # 監聽狀態變化
        store.select(lambda state: state["counter"]).subscribe(
            on_next=lambda value_tuple: print(f"計數器從 {value_tuple[0]} 變為 {value_tuple[1]}")
        )
        ```
    """

    def __init__(self) -> None:
        """
        初始化一個空的 Store 實例。

        初始化時會建立 reducer 管理器、effects 管理器，以及內部的狀態與動作流。
        """
        # 初始化 reducer 管理器
        self._reducer_manager = ReducerManager()
        # 初始化 effects 管理器，並將當前 Store 傳入
        self._effects_manager = EffectsManager(self)
        # 初始化內部狀態為空字典
        self._state: Dict[str, Any] = {}
        # 初始化動作流（Subject）
        self._action_subject: Subject = Subject()
        # 初始化狀態流（Subject）
        self._state_subject: Subject = Subject()
        # 初始化中介軟體列表
        self._middleware: List[Any] = []
        # 設定原始的 dispatch 方法
        self._raw_dispatch = self._dispatch_core
        # 構建中介軟體鏈後的 dispatch 方法
        self.dispatch = self._apply_middleware_chain()

        # 訂閱動作流，每次 dispatch 時更新狀態
        self._action_subject.subscribe(
            on_next=lambda action: self._update_state(
                self._reducer_manager.reduce(self._state, action)
            ),
            on_error=self._handle_store_error
        )
    
    
    def _handle_store_error(self, err: Exception) -> None:
        """處理 Store 內部錯誤。"""
        store_error = StoreError(
            str(err),
            operation="reduce_state",
            state=self._state
        )
        global_error_handler.handle(store_error)
        print(f"Store 錯誤: {err}")

    def _update_state(self, new_state: Dict[str, Any]) -> None:
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

    def _dispatch_core(self, action: Action[Any]) -> Action[Any]:
        """
        核心的 dispatch 方法，將動作傳遞給動作流。

        Args:
            action: 要分發的 Action。

        Returns:
            傳入的 Action。
        """
        self._action_subject.on_next(action)
        return action

    def _apply_middleware_chain(self) -> DispatchFunction:
        """
        構建中介軟體鏈，將中介軟體按順序包裹在 dispatch 方法外層。

        Returns:
            包裹後的 dispatch 方法。
        """
        # 從最後一個中介軟體開始包裹
        dispatch: DispatchFunction = self._raw_dispatch
        for mw in reversed(self._middleware):
            # 判斷中介軟體是函數還是物件
            if hasattr(mw, "on_next"):
                # 如果是物件，使用物件包裹方法
                dispatch = self._wrap_obj_middleware(mw, dispatch)
            else:
                # 如果是函數，直接調用工廠函數
                dispatch = mw(self)(dispatch)
        return dispatch

    def _wrap_obj_middleware(self, mw: MiddlewareProtocol, next_dispatch: DispatchFunction) -> DispatchFunction:
        """
        包裹物件型中介軟體。

        Args:
            mw: 中介軟體物件，需實現 on_next、on_complete 和 on_error 方法。
            next_dispatch: 下一層的 dispatch 方法。

        Returns:
            包裹後的 dispatch 方法。
        """
        def dispatch(action: Any) -> Any:
            # 抓取 action 傳入前的舊狀態
            prev_state = self._state
            # 這裡明確判斷 callable (Thunk function)
            if callable(action):
                # 若為thunk，直接執行，不調用middleware hooks
                try:
                    return action(self.dispatch, lambda: self.state)
                except Exception as err:
                    mw.on_error(err, action)
                    raise

            # 一般action物件才調用中介軟體的 on_next 方法
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

    def apply_middleware(self, *middlewares: Union[type, MiddlewareProtocol]) -> None:
        """
        一次註冊多個中介軟體，並重建 dispatch 鏈。

        Args:
            *middlewares: 要註冊的中介軟體，可以是類或實例。
            
        範例:
            ```python
            # 註冊日誌和 Thunk 中介軟體
            from pystorex.middleware import LoggerMiddleware, ThunkMiddleware
            
            store = create_store()
            store.apply_middleware(LoggerMiddleware(), ThunkMiddleware())
            ```
        """
        # 接受類和實例，如果是類則直接實例化
        for m in middlewares:
            inst = m() if inspect.isclass(m) else m
            self._middleware.append(inst)
        # 重建 dispatch 鏈
        self.dispatch = self._apply_middleware_chain()

    def dispatch(self, action: Union[Action[Any], Callable]) -> Any:
        """
        分發一個動作，觸發狀態更新。

        Args:
            action: 要分發的 Action 物件或 Thunk 函數。

        Returns:
            根據中介軟體處理不同而異，通常返回原始 Action 或中介軟體的處理結果。
            
        注意:
            此方法會在初始化時被重新賦值為包含所有中介軟體的分發鏈。
        """
        # 此內容不會執行，僅用於類型提示
        return action

    def select(self, selector: Optional[StateSelector[S, T]] = None) -> Observable:
        """
        選擇狀態的一部分進行觀察。

        Args:
            selector: 一個函數，接收整個狀態並返回希望觀察的部分。
                      如果為 None，則返回完整的狀態。

        Returns:
            一個可觀察對象，發送選定的狀態部分。
            發射的每個項目是 (old_value, new_value) 的元組，
            表示狀態變化前後的值。
            
        範例:
            ```python
            # 監聽計數器狀態
            store.select(lambda state: state["counter"]).subscribe(
                on_next=lambda value_tuple: print(f"計數器從 {value_tuple[0]} 變為 {value_tuple[1]}")
            )
            ```
        """
        if selector is None:
            # 返回完整的狀態元組 (old_state, new_state)
            return self._state_subject

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
            
        注意:
            這是一個快照，不會隨狀態變化而更新。
            要監聽狀態變化，請使用 select() 方法。
        """
        return cast(S, self._state)

    @handle_error
    def register_root(self, root_reducers: Dict[str, ReducerFunction]) -> None:
        """
        註冊應用的根級 reducers。

        Args:
            root_reducers: 特性鍵名到 reducer 的映射字典。
            
        範例:
            ```python
            # 註冊根級 reducers
            store.register_root({
                "counter": counter_reducer,
                "todos": todos_reducer
            })
            ```
        """
        self._reducer_manager.add_reducers(root_reducers)
        # 初始化狀態
        self._state = self._reducer_manager.reduce(
            None, init_store()
        )

    @handle_error
    def register_feature(self, feature_key: str, reducer: ReducerFunction) -> 'Store[S]':
        """
        註冊一個特性模組的 reducer。
        
        當應用擴展或動態載入新功能時使用。

        Args:
            feature_key: 特性模組的鍵名。
            reducer: 特性模組的 reducer。
            
        Returns:
            自身，以支持鏈式調用。
            
        範例:
            ```python
            # 動態添加設置功能
            store.register_feature("settings", settings_reducer)
            ```
        """
        self._reducer_manager.add_reducer(feature_key, reducer)
        # 更新狀態以包含新特性
        self._state = self._reducer_manager.reduce(
            self._state, update_reducer()
        )
        return self

    def unregister_feature(self, feature_key: str) -> 'Store[S]':
        """
        卸載一個特性模組，包括其 reducer 和 effects。

        Args:
            feature_key: 特性模組的鍵名。
            
        Returns:
            自身，以支持鏈式調用。
            
        範例:
            ```python
            # 卸載不再需要的功能
            store.unregister_feature("temporary_feature")
            ```
        """
        self._reducer_manager.remove_reducer(feature_key)
        # 重新計算一次狀態，去掉該特性
        self._state = self._reducer_manager.reduce(
            self._state, update_reducer()
        )
        # 同時從 EffectsManager 卸載所有來自該特性的 effects
        self._effects_manager.teardown()
        return self

    def register_effects(self, *effects_modules: Any) -> None:
        """
        註冊一個或多個效果模組。

        Args:
            *effects_modules: 包含 effects 的模組或對象。
            
        範例:
            ```python
            # 註冊處理 API 請求的 effects
            store.register_effects(TodoEffects())
            ```
        """
        self._effects_manager.add_effects(*effects_modules)
    
    def __enter__(self) -> 'Store[S]':
        """
        進入上下文，返回 Store 實例自身。
        
        Returns:
            Store 實例
            
        範例:
            ```python
            with create_store() as store:
                store.register_root({"counter": counter_reducer})
                store.dispatch(increment())
            # 當退出 with 區塊時，store 會自動清理資源
            ```
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        退出上下文時清理資源。
        
        Args:
            exc_type: 異常類型，如果沒有異常則為 None
            exc_val: 異常值，如果沒有異常則為 None
            exc_tb: 異常追蹤信息，如果沒有異常則為 None
        """
        self.teardown()
        
    def teardown(self) -> None:
        """
        清理 Store 的所有資源。
        
        此方法會：
        1. 卸載所有 effects
        2. 關閉所有 Subject
        3. 清理所有中介軟體的資源
        """
        # 清理 effects 管理器
        self._effects_manager.teardown()
        
        # 關閉 Subjects
        self._action_subject.dispose()
        self._state_subject.dispose()
        
        # 清理中介軟體資源
        for mw in self._middleware:
            if hasattr(mw, "teardown") and callable(mw.teardown):
                mw.teardown()


def create_store() -> Store[Dict[str, Any]]:
    """
    創建一個新的 Store 實例。

    Returns:
        一個新的 Store 實例，狀態類型為 Dict[str, Any]。
        
    範例:
        ```python
        # 創建基本 store
        store = create_store()
        ```
    """
    return Store()


class StoreModule:
    """
    用於配置 Store 的工具類，類似於 NgRx 的 StoreModule。
    
    提供一種靜態方法的方式來管理 Store 實例和其 Reducers。
    """

    @staticmethod
    def register_root(reducers: Dict[str, ReducerFunction], store: Optional[Store[S]] = None) -> Store[S]:
        """
        註冊應用的根級 reducers。

        Args:
            reducers: 特性鍵名到 reducer 的映射字典。
            store: 可選的 Store 實例，如果不提供則創建新實例。

        Returns:
            配置好的 Store 實例。
            
        範例:
            ```python
            # 使用 StoreModule 創建並配置 store
            store = StoreModule.register_root({
                "counter": counter_reducer,
                "todos": todos_reducer
            })
            ```
        """
        if store is None:
            store = create_store()

        store.register_root(reducers)
        return store

    @staticmethod
    def register_feature(feature_key: str, reducer: ReducerFunction, store: Store[S]) -> Store[S]:
        """
        註冊一個特性模組的 reducer。

        Args:
            feature_key: 特性模組的鍵名。
            reducer: 特性模組的 reducer。
            store: 要註冊到的 Store 實例。

        Returns:
            更新後的 Store 實例。
            
        範例:
            ```python
            # 使用 StoreModule 添加新功能
            store = StoreModule.register_feature("settings", settings_reducer, store)
            ```
        """
        store.register_feature(feature_key, reducer)
        return store

    @staticmethod
    def unregister_feature(feature_key: str, store: Store[S]) -> Store[S]:
        """
        卸載一個特性模組，包括 reducer 和 effects。

        Args:
            feature_key: 特性模組的鍵名。
            store: 要操作的 Store 實例。

        Returns:
            更新後的 Store 實例。
            
        範例:
            ```python
            # 使用 StoreModule 卸載功能
            store = StoreModule.unregister_feature("temporary_feature", store)
            ```
        """
        store.unregister_feature(feature_key)
        return store


class EffectsModule:
    """
    用於配置 Effects 的工具類，類似於 NgRx 的 EffectsModule。
    
    提供一種靜態方法的方式來管理 Store 實例的 Effects。
    """

    @staticmethod
    def register_root(effects_items: Any, store: Store[S]) -> Store[S]:
        """
        註冊根級的 effects。

        Args:
            effects_items: 可以是單個 effect 類/實例，或包含多個 effect 類/實例的列表。
            store: 要註冊到的 Store 實例。

        Returns:
            更新後的 Store 實例。
            
        範例:
            ```python
            # 使用 EffectsModule 註冊全局 effects
            store = EffectsModule.register_root([LoggingEffects(), ApiEffects()], store)
            ```
        """
        store.register_effects(effects_items)
        return store

    @staticmethod
    def register_feature(effects_item: Any, store: Store[S]) -> Store[S]:
        """
        註冊一個特性模組的 effects。

        Args:
            effects_item: 包含 effects 的類、實例或配置字典。
            store: 要註冊到的 Store 實例。

        Returns:
            更新後的 Store 實例。
            
        範例:
            ```python
            # 使用 EffectsModule 註冊特性模組的 effects
            store = EffectsModule.register_feature(UserEffects(), store)
            ```
        """
        store.register_effects(effects_item)
        return store