"""
PyStoreX 範例：待辦事項應用，展示所有中介軟體的使用
"""

import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import uuid
import time
import asyncio
from typing import List, Optional, Tuple
from typing_extensions import TypedDict

from pydantic import BaseModel
from reactivex import Observable, operators as ops, from_future
from reactivex.scheduler.eventloop import AsyncIOScheduler
from immutables import Map

from pystorex.effects import create_effect
from pystorex.rx_operators import ofType
from pystorex.actions import create_action, Action, update_reducer
from pystorex import create_store, create_reducer_from_function_handler
from pystorex.store_selectors import create_selector
from pystorex.middleware import (
    LoggerMiddleware,
    ThunkMiddleware,
    AwaitableMiddleware,
    ErrorMiddleware,
    PersistMiddleware,
    DevToolsMiddleware,
    PerformanceMonitorMiddleware,
    DebounceMiddleware,
    BatchMiddleware,
    AnalyticsMiddleware,
    ErrorReportMiddleware,
)
from pystorex.immutable_utils import to_dict, to_pydantic
from pystorex.action_handlers import TypedActionHandler


# ====== 1. 定義狀態模型 ======
class TodoItem(TypedDict):
    id: str
    text: str
    completed: bool


class TodoState(TypedDict):
    todos: Tuple[TodoItem, ...]
    loading: bool
    error: Optional[str]
    last_updated: Optional[float]
    history: Tuple[int, ...]
    max_todos: int


todo_initial_state = TodoState(
    todos=(), loading=False, error=None, last_updated=None, history=(), max_todos=5
)


# Pydantic 模型，用於序列化
class TodoItemModel(BaseModel):
    id: str
    text: str
    completed: bool


class TodoStateModel(BaseModel):
    todos: List[TodoItemModel]
    loading: bool
    error: Optional[str]
    last_updated: Optional[float]
    history: List[int]
    max_todos: int


# ====== 2. 定義 Actions ======
add_todo = create_action("addTodo", lambda text: text)
toggle_todo = create_action("toggleTodo", lambda id: id)
remove_todo = create_action("removeTodo", lambda id: id)
load_todos_request = create_action("loadTodosRequest")
load_todos_success = create_action("loadTodosSuccess", lambda todos: todos)
load_todos_failure = create_action("loadTodosFailure", lambda error: error)
todos_warning = create_action("todosWarning", lambda count: count)

# 新動作
clear_todos = create_action("clearTodos")
batch_add_todos_request = create_action("batchAddTodosRequest")
batch_add_todos_success = create_action("batchAddTodosSuccess")

# ====== 3. 定義 Reducer ======
handler = TypedActionHandler(
    TodoState,
    initial_values={
        "todos": (),
        "loading": False,
        "error": None,
        "last_updated": None,
        "history": (),
        "max_todos": 5,
    },
)


@handler.register("addTodo")
def handle_add_todo(state: Map, action: Action[str]) -> Map:
    if len(state["todos"]) >= state["max_todos"]:
        print("[提示] 待辦事項數量過多，無法新增 (可選)")
        # return state  # 或觸發 todosWarning .
    new_todo = TodoItem(id=str(uuid.uuid4()), text=action.payload, completed=False)
    new_todos = state["todos"] + (new_todo,)
    return (state
            .set("todos", new_todos)
            .set("last_updated", time.time())
            .set("history", state["history"] + (len(new_todos),)))


@handler.register("toggleTodo")
def handle_toggle_todo(state: Map, action: Action[str]) -> Map:
    new_todos = tuple(
        (
            {**todo, "completed": not todo["completed"]}
            if todo["id"] == action.payload
            else todo
        )
        for todo in state["todos"]
    )
    return state.set("todos", new_todos).set("last_updated", time.time())


@handler.register("removeTodo")
def handle_remove_todo(state: Map, action: Action[str]) -> Map:
    new_todos = tuple(todo for todo in state["todos"] if todo["id"] != action.payload)
    return (
        state.set("todos", new_todos)
        .set("last_updated", time.time())
        .set("history", state["history"] + (len(new_todos),))
    )


@handler.register("loadTodosRequest")
def handle_load_todos_request(state: Map, action: Action[None]) -> Map:
    return state.set("loading", True).set("error", None)


@handler.register("loadTodosSuccess")
def handle_load_todos_success(state: Map, action: Action[List[TodoItem]]) -> Map:
    new_todos = tuple(action.payload)
    return (
        state.set("loading", False)
        .set("todos", new_todos)
        .set("last_updated", time.time())
        .set("history", state["history"] + (len(new_todos),))
    )


@handler.register("loadTodosFailure")
def handle_load_todos_failure(state: Map, action: Action[str]) -> Map:
    return state.set("loading", False).set("error", action.payload)


@handler.register("todosWarning")
def handle_todos_warning(state: Map, action: Action[int]) -> Map:
    return state


todo_reducer = create_reducer_from_function_handler(handler)


# ====== 4. 定義 Effects ======
class TodoEffects:
    @create_effect
    def load_todos(self, action_stream):
        async def fetch_todos():
            try:
                print("[Effect] 開始異步 fetch_todos()")
                await asyncio.sleep(1)
                print("[Effect] 準備 dispatch loadTodosSuccess")
                return load_todos_success(
                    [
                        TodoItem(
                            id=str(uuid.uuid4()), text="範例待辦 1", completed=False
                        ),
                        TodoItem(
                            id=str(uuid.uuid4()), text="範例待辦 2", completed=True
                        ),
                    ]
                )
            except Exception as e:
                print(f"[Effect] fetch_todos exception: {e}")
                raise

        def to_observable(_):
            # loop = asyncio.get_event_loop()
            # return from_future(
            #     asyncio.ensure_future(fetch_todos(), loop=loop)
            # )
            return from_future(asyncio.create_task(fetch_todos()))

        return action_stream.pipe(
            ofType(load_todos_request),
            ops.do_action(lambda _: print("Effect: 正在載入待辦事項...")),
            ops.flat_map(to_observable),
        )

    @create_effect(dispatch=False)
    def log_actions(self, action_stream):
        return action_stream.pipe(
            ops.do_action(lambda action: print(f"[Log] 動作: {action.type}")),
            ops.filter(lambda _: False),
        )

    @create_effect(dispatch=False)
    def handle_todos_warning(self, action_stream):
        return action_stream.pipe(
            ofType(todos_warning),
            ops.do_action(
                lambda action: print(
                    f"[警告] {'待辦事項內容不能為空!' if action.payload == 0 else f'待辦事項數量過多! 目前數量: {action.payload}'}"
                )
            ),
            ops.filter(lambda _: False),
        )


# ====== 5. 定義 Thunk ======
def validate_and_add_todo(text: str):
    def thunk(dispatch, get_state):
        state = get_state()
        current_todo_count = len(state["todo"]["todos"])
        max_todos = state["todo"]["max_todos"]

        if not text.strip():
            print("[提示] 輸入的待辦事項不可為空")
            return

        if current_todo_count >= max_todos:
            dispatch(todos_warning(current_todo_count))
        else:
            dispatch(add_todo(text))

    return thunk


# ====== 6. 定義 Analytics Callback ======
def analytics_callback(action, prev_state, next_state, session_id=None):
    print(f"[Analytics] 動作: {action.type}, Session: {session_id}")
    if next_state:
        todo_count = len(next_state.get("todo", {}).get("todos", ()))
        print(f"[Analytics] 待辦事項數量: {todo_count}")


# ====== 7. 自訂 PersistMiddleware ======
class CustomPersistMiddleware(PersistMiddleware):
    def _serialize_state(self, state):
        serializable_state = to_dict(state)
        print(f"[Persist] 序列化狀態: {serializable_state}")

        todo_state = serializable_state.get("todo", {})
        return {
            "todos": todo_state.get("todos", []),
            "max_todos": todo_state.get("max_todos", 5),
            "last_updated": todo_state.get("last_updated"),
        }

    def on_complete(self, next_state, action):
        if action.type in ["addTodo", "toggleTodo", "removeTodo", "loadTodosSuccess"]:
            serialized_state = self._serialize_state(next_state)
            print(f"[Persist] 處理動作: {action.type}")

            try:
                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump(serialized_state, f, ensure_ascii=False, indent=2)
            except Exception as err:
                print(f"[PersistMiddleware] 寫入失敗: {err}")


# ====== 8. 建立 Store、註冊模組 ======
store = create_store()
store.apply_middleware(
    ErrorReportMiddleware(report_file="todo_errors.html"),
    AnalyticsMiddleware(analytics_callback),
    DebounceMiddleware(interval=0.3),
    BatchMiddleware(window=0.1),
    ThunkMiddleware(),
    AwaitableMiddleware(),
    ErrorMiddleware(),
    CustomPersistMiddleware(filepath="todos.json", keys=["todos"]),
    DevToolsMiddleware(),
    PerformanceMonitorMiddleware(threshold_ms=50, log_all=True),
    LoggerMiddleware(),
)
store.register_root({"todo": todo_reducer})
store.register_effects(TodoEffects)

# ====== 9. 訂閱狀態與監控 ======
store.select().subscribe(lambda s: print(f"狀態變化: {to_dict(s[1])}"))

get_todo_state = lambda state: state["todo"]
get_todo_count = create_selector(
    get_todo_state, result_fn=lambda todo: len(todo.get("todos", ()))
)
store.select(get_todo_count).subscribe(lambda c: print(f"待辦事項數量: {c[1]}"))


def todo_count_monitor(count_tuple):
    old_count, new_count = count_tuple
    print(f"待辦事項數量: {old_count} -> {new_count}")
    # 如果只是要列印、記錄數量變化，這樣即可


store.select(get_todo_count).subscribe(todo_count_monitor)


def print_pydantic_when_needed(value_tuple):
    _, new_state = value_tuple
    todo_map = new_state["todo"]
    if len(todo_map.get("todos", ())) > 3:
        todo_pydantic = to_pydantic(todo_map, TodoState)
        print(f"Pydantic 模型: {todo_pydantic}")
        print(f"JSON: {todo_pydantic.model_dump_json(indent=2)}")


store.select().subscribe(print_pydantic_when_needed)


def todo_warning_monitor(state_tuple):
    old_state, new_state = state_tuple
    try:
        old_count = (
            len(old_state["todo"]["todos"])
            if old_state["todo"].get("todos") is not None
            else 0
        )
        new_count = (
            len(new_state["todo"]["todos"])
            if new_state["todo"].get("todos") is not None
            else 0
        )
        max_todos = new_state["todo"].get("max_todos", 5)
    except Exception as e:
        print("狀態結構異常：", e)
        return

    if (
        new_count is not None
        and max_todos is not None
        and new_count > max_todos
        and old_count != new_count
    ):
        print("todo超過上限！")
        store.dispatch(todos_warning(new_count))


store.select().subscribe(todo_warning_monitor)

import asyncio


async def main():
    store.dispatch(load_todos_request())
    await asyncio.sleep(2)  # 等待異步 Effect 完成


# ====== 10. 執行操作示例 ======
if __name__ == "__main__":
    print("開始執行待辦事項範例...")
    store.dispatch(update_reducer())
    store.dispatch(add_todo("學習 PyStoreX"))
    store.dispatch(validate_and_add_todo("完成範例程式"))
    store.dispatch(toggle_todo(store.state["todo"]["todos"][0]["id"]))
    store.dispatch(add_todo("測試中介軟體"))
    store.dispatch(add_todo("快速新增1"))
    store.dispatch(add_todo("快速新增2"))
    store.dispatch(add_todo("額外測試項目1"))
    store.dispatch(add_todo("額外測試項目2"))

    store.dispatch(remove_todo(store.state["todo"]["todos"][1]["id"]))

    asyncio.run(main())
    # store.dispatch(load_todos_request())
    store.dispatch(validate_and_add_todo(""))

    time.sleep(3)  # 等待持久化和異步效果完成

    print("\n==== 最終狀態 ====")
    todo_state_map = store.state["todo"]
    todo_state_dict = to_dict(todo_state_map)
    todo_state_pydantic = to_pydantic(todo_state_map, TodoState)
    print(f"Todo 字典: {todo_state_dict}")
    print(f"Todo Pydantic: {todo_state_pydantic}")

    dev_tools = next(
        mw for mw in store._middleware if isinstance(mw, DevToolsMiddleware)
    )
    history = dev_tools.get_history()
    print("\n==== DevTools 歷史 ====")
    for prev_state, action, next_state in history:
        print(
            f"動作: {action.type}, 狀態變化: {to_dict(prev_state)} -> {to_dict(next_state)}"
        )

    perf_monitor = next(
        mw for mw in store._middleware if isinstance(mw, PerformanceMonitorMiddleware)
    )
    metrics = perf_monitor.get_metrics()
    print("\n==== 性能指標 ====")
    for action_type, data in metrics.items():
        print(
            f"動作 {action_type}: 平均 {data['avg']:.2f}ms, 最大 {data['max']:.2f}ms, 計數 {data['count']}"
        )
