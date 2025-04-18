from typing import Any, Callable, Dict
from reactivex import operators as ops
from reactivex import Observable
from .actions import Action
import inspect
import functools


class Effect:
    """
    表示一个副作用处理函数
    """

    def __init__(self, source: Observable):
        self.source = source


def create_effect(effect_fn=None, *, dispatch: bool = True):
    """
    用法：
      @create_effect
      def foo(action$): ...
    或
      @create_effect(dispatch=False)
      def bar(action$): ...
    """
    # 如果没有直接给函数，就返回一个 decorator
    if effect_fn is None:

        def decorator(fn):
            return create_effect(fn, dispatch=dispatch)

        return decorator

    # 下面是原来逻辑，只不过把 dispatch 标记上去
    is_instance_method = (
        inspect.isfunction(effect_fn)
        and effect_fn.__code__.co_varnames
        and effect_fn.__code__.co_varnames[0] == "self"
    )

    @functools.wraps(effect_fn)
    def wrapper(*args, **kwargs):
        # 拿到实际的 action_stream 参数（最后那个）
        action_stream = args[-1]
        # 调用原函数，生成 Observable
        source = (
            effect_fn(*args, **kwargs)
            if is_instance_method
            else effect_fn(action_stream)
        )
        return Effect(source)

    # 标记这个 wrapper 是一个 Effect，并记录 dispatch 标志
    wrapper.is_effect = True
    wrapper.dispatch = dispatch
    wrapper.is_instance_method = is_instance_method
    return wrapper


class EffectsManager:
    """
    管理所有的 Effect 模块
    """

    def __init__(self, store):
        self.store = store
        self.subscriptions = []
        self._effects_modules = []
        self._subs_by_module: Dict[Any, list] = {}  # 按 module 分组
        self._subs_by_effect = {}  # key: (module, effect_name) -> subscription

    def add_effects(self, *effects_items):
        """
        添加效果模块
        """
        new_modules = []
        for item in effects_items:
            instances = self._process_effects_item(item)
            for instance in instances:
                if instance not in self._effects_modules:
                    self._effects_modules.append(instance)
                    new_modules.append(instance)
        if new_modules:
            self._register_effects(new_modules)

    def _process_effects_item(self, item):
        """
        处理单个 effects 项，返回实例列表
        """
        instances = []
        # 列表或元组
        if isinstance(item, (list, tuple)):
            for sub in item:
                instances.extend(self._process_effects_item(sub))
        # 字典配置
        elif isinstance(item, dict) and "class" in item:
            cls = item["class"]
            params = item.get("params", {})
            try:
                instances.append(cls(**params))
            except Exception as e:
                print(f"无法创建 {cls.__name__} 实例: {e}")
        # 类直接实例化
        elif inspect.isclass(item):
            try:
                instances.append(item())
            except Exception as e:
                print(f"无法创建 {item.__name__} 实例: {e}")
        # 已经是实例
        else:
            instances.append(item)
        return instances

    def _register_effects(self, modules):
        """
        注册指定模块中的 Effect
        """
        for module in modules:
            for name, member in inspect.getmembers(module):
                if getattr(member, "is_effect", False):
                    eff: Effect = member(self.store._action_subject)
                    subscription = eff.source.pipe(
                        ops.catch(self._handle_effect_error(module, name))
                    ).subscribe(
                        on_next=self._dispatch_if_action(module, member),
                        on_error=lambda e: print(f"[Effect Error] {e}"),
                    )
                    self._subs_by_module[module].append(subscription)
                    self._subs_by_effect[(module, name)] = subscription

    def _register_effects(self, modules):
        """
        注册指定模块中的 Effect
        """
        action_stream = self.store._action_subject
        for module in modules:
            self._subs_by_module[module] = []
            for name, member in inspect.getmembers(module):
                if getattr(member, "is_effect", False):
                    try:
                        # 直接让 Bound Method 绑定 self，然后把 action_stream 传进去
                        effect_instance = member(action_stream)
                        if isinstance(effect_instance, Effect):
                            # 只订阅 effect_instance.source，而不是整个 action_stream
                            subscription = (
                                effect_instance.source
                                # 只保留 Action
                                .pipe(
                                    ops.filter(lambda a: isinstance(a, Action))
                                ).subscribe(
                                    on_next=(
                                        self.store.dispatch
                                        if getattr(member, "dispatch", True)
                                        else lambda _: None
                                    ),
                                    on_error=lambda err: print(f"副作用错误: {err}"),
                                )
                            )
                            self.subscriptions.append(subscription)
                            self._subs_by_module[module].append(subscription)
                    except Exception as e:
                        print(f"注册效果 {name} 时出错: {e}")

    def _handle_effect_error(self, module, name):
        def catcher(err, source):
            # 统一上报给业务
            print(f"[Error][Effect {module.__class__.__name__}.{name}]:", err)
            # 业务可以在这里插入重试、上报 Sentry、或 dispatch 一个 ERROR Action
            return source  # 或者 source.pipe(...) 继续流

        return catcher

    def _dispatch_if_action(self, module, effect_fn):
        def dispatcher(item):
            # 先检查装饰器上的 dispatch 属性
            if not getattr(effect_fn, "dispatch", True):
                # fire‑and‑forget 模式
                return
            # 再检查类型
            from .actions import Action

            if isinstance(item, Action):
                self.store.dispatch(item)
            else:
                print(
                    f"[Warning] Effect {module.__class__.__name__}.{effect_fn.__name__} "
                    f"emitted non‑Action: {item!r}"
                )

        return dispatcher

    def remove_effects(self, *modules):
        """卸载指定 effects module 的所有订阅，不影响其他模块"""
        for module in modules:
            subs = self._subs_by_module.get(module, [])
            for sub in subs:
                sub.dispose()
            # 清理
            if module in self._subs_by_module:
                del self._subs_by_module[module]
            if module in self._effects_modules:
                self._effects_modules.remove(module)
        # 其余 module 继续生效

    def cancel_effect(self, module, effect_name: str):
        key = (module, effect_name)
        sub = self._subs_by_effect.pop(key, None)
        if sub:
            sub.dispose()
            # 也从模块列表里移除
            self._subs_by_module[module] = [
                s for s in self._subs_by_module[module] if s is not sub
            ]

    def _register_all_effects(self):
        """
        重新注册所有模块中的 Effect
        """
        for sub in self.subscriptions:
            sub.dispose()
        self.subscriptions.clear()
        self._register_effects(self._effects_modules)

    def teardown(self):
        """
        清理所有订阅和模块引用
        """
        for sub in self.subscriptions:
            sub.dispose()
        self.subscriptions.clear()
        self._effects_modules.clear()
