"""
使用Python NgRx风格架构的简单计数器示例
文件名: counter_example.py
"""

import json
from pystorex import (
    Action,
    create_action,
    create_reducer,
    on,
    Store,
    create_store,
    StoreModule,
    EffectsModule,
    Effect,
    create_effect,
    create_selector,
)
from reactivex import operators as ops
import time

# ============== 定义Actions ==============
increment = create_action("increment")
decrement = create_action("decrement")
reset = create_action("reset", lambda value=0: value)  # 使用prepare函数
increment_by = create_action("incrementBy")
load_count_request = create_action("loadCountRequest")
load_count_success = create_action("loadCountSuccess")
load_count_failure = create_action("loadCountFailure")

# ============== 定义初始状态 ==============
initial_state = {"count": 0, "loading": False, "error": None, "lastUpdated": None}


# ============== 定义Reducer ==============
def handle_increment(state, action):
    return {**state, "count": state["count"] + 1, "lastUpdated": time.time()}


def handle_decrement(state, action):
    return {**state, "count": state["count"] - 1, "lastUpdated": time.time()}


def handle_reset(state, action):
    return {**state, "count": action.payload, "lastUpdated": time.time()}


def handle_increment_by(state, action):
    return {
        **state,
        "count": state["count"] + action.payload,
        "lastUpdated": time.time(),
    }


def handle_load_request(state, action):
    return {**state, "loading": True, "error": None}


def handle_load_success(state, action):
    return {
        **state,
        "loading": False,
        "count": action.payload,
        "lastUpdated": time.time(),
    }


def handle_load_failure(state, action):
    return {**state, "loading": False, "error": action.payload}


# 使用create_reducer和on函数组合成reducer
counter_reducer = create_reducer(
    initial_state,
    on(increment, handle_increment),
    on(decrement, handle_decrement),
    on(reset, handle_reset),
    on(increment_by, handle_increment_by),
    on(load_count_request, handle_load_request),
    on(load_count_success, handle_load_success),
    on(load_count_failure, handle_load_failure),
)

# ============== 创建Store ==============
# 首先创建一个空的Store
store = create_store()

# 使用StoreModule注册根reducer
store = StoreModule.register_root({"counter": counter_reducer}, store)

# ============== 定义Selectors ==============
get_counter_state = lambda state: state.get("counter", {})
get_count = create_selector(
    get_counter_state, result_fn=lambda counter: counter.get("count", 0)
)
get_loading = create_selector(
    get_counter_state, result_fn=lambda counter: counter.get("loading", False)
)
get_error = create_selector(
    get_counter_state, result_fn=lambda counter: counter.get("error", None)
)
get_last_updated = create_selector(
    get_counter_state, result_fn=lambda counter: counter.get("lastUpdated", None)
)

# 创建一个复合选择器
get_counter_info = create_selector(
    get_count,
    get_last_updated,
    result_fn=lambda count, last_updated: {"count": count, "lastUpdated": last_updated},
)


# ============== 定义Effects ==============
class CounterEffects:
    @create_effect
    def load_count(self, action_stream):
        """模拟从API加载数据的副作用"""
        return action_stream.pipe(
            ops.filter(lambda action: action.type == load_count_request.type),
            ops.delay(1.0),  # 模拟网络延迟
            ops.map(lambda _: load_count_success(42)),  # 假设API总是返回42
            # 在实际应用中，这里会是一个HTTP请求
            # 还可以添加catchError处理失败情况
        )

    @create_effect
    def log_actions(self, action_stream):
        """记录所有action的副作用 - 这只是一个示例，不产生新的action"""
        return action_stream.pipe(
            ops.do_action(lambda action: print(f"Effect日志: {action.type}")),
            ops.filter(lambda _: False),  # 这个effect不产生新的action
        )


# ============== 注册Effects ==============
store = EffectsModule.register_root(CounterEffects, store)

# ============== 使用示例 ==============
if __name__ == "__main__":
    # 订阅状态变化 - 在日志中显示变化前后的对比
    # 订阅旧→新 两个值
    store.select(get_count).subscribe(
        on_next=lambda t: print(f"计数变化: {t[0]} -> {t[1]}")
    )

    store.select(get_counter_info).subscribe(
        on_next=lambda info_tuple: print(
            f"计数器信息更新: {json.dumps(info_tuple[1], ensure_ascii=False, indent=2)}"
        )
    )

    # 分发actions
    print("\n==== 开始测试基本操作 ====")
    store.dispatch(increment())
    store.dispatch(increment_by(5))
    store.dispatch(decrement())
    store.dispatch(reset(10))

    # 触发异步action
    print("\n==== 开始测试异步操作 ====")
    store.dispatch(load_count_request())

    # 保持程序运行，以便观察异步效果
    time.sleep(2)

    # 打印最终状态
    print("\n==== 最终状态 ====")
    print(store.state)
