from typing import Any, Callable, Dict
from reactivex import operators as ops
from reactivex import Observable
from .actions import Action
import inspect
import functools


class Effect:
    """
    表示一個副作用處理函數的封裝類別。
    """

    def __init__(self, source: Observable):
        """
        初始化 Effect 實例。

        :param source: 一個 Observable，表示副作用的資料流。
        """
        self.source = source


def create_effect(effect_fn=None, *, dispatch: bool = True):
    """
    創建一個副作用裝飾器，用於標記函數為 Effect。

    用法：
      @create_effect
      def foo(action$): ...
    或
      @create_effect(dispatch=False)
      def bar(action$): ...

    :param effect_fn: 被裝飾的函數，默認為 None。
    :param dispatch: 是否自動 dispatch Action，默認為 True。
    :return: 包裝後的函數或裝飾器。
    """
    # 如果沒有直接給函數，就返回一個 decorator
    if effect_fn is None:
        def decorator(fn):
            return create_effect(fn, dispatch=dispatch)
        return decorator

    # 判斷是否為實例方法
    is_instance_method = (
        inspect.isfunction(effect_fn)
        and effect_fn.__code__.co_varnames
        and effect_fn.__code__.co_varnames[0] == "self"
    )

    @functools.wraps(effect_fn)
    def wrapper(*args, **kwargs):
        """
        包裝函數，處理 action_stream 並返回 Effect 實例。
        """
        # 拿到實際的 action_stream 參數（最後一個參數）
        action_stream = args[-1]
        # 調用原函數，生成 Observable
        source = (
            effect_fn(*args, **kwargs)
            if is_instance_method
            else effect_fn(action_stream)
        )
        return Effect(source)

    # 標記這個 wrapper 是一個 Effect，並記錄 dispatch 標誌
    wrapper.is_effect = True
    wrapper.dispatch = dispatch
    wrapper.is_instance_method = is_instance_method
    return wrapper


class EffectsManager:
    """
    管理所有的 Effect 模組，負責註冊、取消和清理 Effect。
    """

    def __init__(self, store):
        """
        初始化 EffectsManager。

        :param store: 存儲對象，用於管理 Action 和 State。
        """
        self.store = store
        self.subscriptions = []  # 儲存所有的訂閱
        self._effects_modules = []  # 儲存所有的 Effect 模組
        self._subs_by_module: Dict[Any, list] = {}  # 按模組分組的訂閱
        self._subs_by_effect = {}  # 按 (模組, Effect 名稱) 分組的訂閱

    def add_effects(self, *effects_items):
        """
        添加效果模組。

        :param effects_items: 一個或多個 Effect 模組或配置。
        """
        new_modules = []
        for item in effects_items:
            # 處理每個 Effect 項，並獲取實例
            instances = self._process_effects_item(item)
            for instance in instances:
                if instance not in self._effects_modules:
                    self._effects_modules.append(instance)
                    new_modules.append(instance)
        if new_modules:
            # 註冊新的 Effect 模組
            self._register_effects(new_modules)

    def _process_effects_item(self, item):
        """
        處理單個 effects 項，返回實例列表。

        :param item: Effect 項，可以是類別、實例、字典或列表。
        :return: 包含所有處理後實例的列表。
        """
        instances = []
        # 如果是列表或元組，遞歸處理每個子項
        if isinstance(item, (list, tuple)):
            for sub in item:
                instances.extend(self._process_effects_item(sub))
        # 如果是字典配置，嘗試實例化類別
        elif isinstance(item, dict) and "class" in item:
            cls = item["class"]
            params = item.get("params", {})
            try:
                instances.append(cls(**params))
            except Exception as e:
                print(f"無法創建 {cls.__name__} 實例: {e}")
        # 如果是類別，直接實例化
        elif inspect.isclass(item):
            try:
                instances.append(item())
            except Exception as e:
                print(f"無法創建 {item.__name__} 實例: {e}")
        # 如果已經是實例，直接添加
        else:
            instances.append(item)
        return instances

    def _register_effects(self, modules):
        """
        註冊指定模組中的 Effect。

        :param modules: 包含需要註冊的 Effect 模組的列表。
        """
        action_stream = self.store._action_subject  # Action 的資料流
        for module in modules:
            self._subs_by_module[module] = []  # 初始化模組的訂閱列表
            for name, member in inspect.getmembers(module):
                if getattr(member, "is_effect", False):  # 檢查是否為 Effect
                    try:
                        # 綁定 self，並傳入 action_stream
                        effect_instance = member(action_stream)
                        if isinstance(effect_instance, Effect):
                            # 訂閱 Effect 的資料流
                            subscription = (
                                effect_instance.source
                                .pipe(
                                    ops.filter(lambda a: isinstance(a, Action))  # 過濾 Action
                                ).subscribe(
                                    on_next=(
                                        self.store.dispatch
                                        if getattr(member, "dispatch", True)  # 是否自動 dispatch
                                        else lambda _: None
                                    ),
                                    on_error=lambda err: print(f"副作用錯誤: {err}"),
                                )
                            )
                            self.subscriptions.append(subscription)
                            self._subs_by_module[module].append(subscription)
                    except Exception as e:
                        print(f"註冊效果 {name} 時出錯: {e}")

    def _handle_effect_error(self, module, name):
        """
        處理 Effect 執行過程中的錯誤。

        :param module: 發生錯誤的模組。
        :param name: 發生錯誤的 Effect 名稱。
        :return: 錯誤捕獲函數。
        """
        def catcher(err, source):
            print(f"[Error][Effect {module.__class__.__name__}.{name}]:", err)
            # 可以在這裡插入重試、上報或其他處理邏輯
            return source  # 返回原始資料流以繼續處理
        return catcher

    def _dispatch_if_action(self, module, effect_fn):
        """
        如果輸出是 Action，則自動 dispatch。

        :param module: Effect 所屬的模組。
        :param effect_fn: Effect 函數。
        :return: 處理輸出的函數。
        """
        def dispatcher(item):
            if not getattr(effect_fn, "dispatch", True):  # 檢查 dispatch 屬性
                return
            if isinstance(item, Action):  # 檢查是否為 Action
                self.store.dispatch(item)
            else:
                print(
                    f"[Warning] Effect {module.__class__.__name__}.{effect_fn.__name__} "
                    f"emitted non‑Action: {item!r}"
                )
        return dispatcher

    def remove_effects(self, *modules):
        """
        卸載指定模組的所有訂閱，不影響其他模組。

        :param modules: 需要卸載的模組列表。
        """
        for module in modules:
            subs = self._subs_by_module.get(module, [])
            for sub in subs:
                sub.dispose()  # 取消訂閱
            # 清理相關數據
            if module in self._subs_by_module:
                del self._subs_by_module[module]
            if module in self._effects_modules:
                self._effects_modules.remove(module)

    def cancel_effect(self, module, effect_name: str):
        """
        取消指定模組中的某個 Effect。

        :param module: 模組實例。
        :param effect_name: Effect 的名稱。
        """
        key = (module, effect_name)
        sub = self._subs_by_effect.pop(key, None)
        if sub:
            sub.dispose()  # 取消訂閱
            # 從模組的訂閱列表中移除
            self._subs_by_module[module] = [
                s for s in self._subs_by_module[module] if s is not sub
            ]

    def _register_all_effects(self):
        """
        重新註冊所有模組中的 Effect。
        """
        for sub in self.subscriptions:
            sub.dispose()  # 取消所有訂閱
        self.subscriptions.clear()
        self._register_effects(self._effects_modules)  # 重新註冊

    def teardown(self):
        """
        清理所有訂閱和模組引用。
        """
        for sub in self.subscriptions:
            sub.dispose()  # 取消所有訂閱
        self.subscriptions.clear()
        self._effects_modules.clear()  # 清空模組列表
