
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pathlib import Path
import sys
import random
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
    warning_count: int  # 新增警告計數

todo_initial_state = TodoState(
    todos=(), loading=False, error=None, last_updated=None, history=(), max_todos=5, warning_count=0
)

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
    warning_count: int

# ====== 2. 定義 Actions ======
add_todo = create_action("addTodo", lambda text: text)
toggle_todo = create_action("toggleTodo", lambda id: id)
remove_todo = create_action("removeTodo", lambda id: id)
load_todos_request = create_action("loadTodosRequest")
load_todos_success = create_action("loadTodosSuccess", lambda todos: todos)
load_todos_failure = create_action("loadTodosFailure", lambda error: error)
todos_warning = create_action("todosWarning", lambda count: count)
clear_todos = create_action("clearTodos")
batch_add_todos_request = create_action("batchAddTodosRequest", lambda count: count)
batch_add_todos_success = create_action("batchAddTodosSuccess", lambda todos: todos)

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
        "warning_count": 0,
    },
)

@handler.register("addTodo")
def handle_add_todo(state: Map, action: Action[str]) -> Map:
    if len(state["todos"]) >= state["max_todos"]:
        return state.set("warning_count", state["warning_count"] + 1)
    new_todo = TodoItem(id=str(uuid.uuid4()), text=action.payload, completed=False)
    new_todos = state["todos"] + (new_todo,)
    return state.set("todos", new_todos).set("last_updated", time.time()).set("history", state["history"] + (len(new_todos),))

@handler.register("toggleTodo")
def handle_toggle_todo(state: Map, action: Action[str]) -> Map:
    new_todos = tuple(
        ({**todo, "completed": not todo["completed"]} if todo["id"] == action.payload else todo)
        for todo in state["todos"]
    )
    return state.set("todos", new_todos).set("last_updated", time.time())

@handler.register("removeTodo")
def handle_remove_todo(state: Map, action: Action[str]) -> Map:
    new_todos = tuple(todo for todo in state["todos"] if todo["id"] != action.payload)
    return state.set("todos", new_todos).set("last_updated", time.time()).set("history", state["history"] + (len(new_todos),))

@handler.register("loadTodosRequest")
def handle_load_todos_request(state: Map, action: Action[None]) -> Map:
    return state.set("loading", True).set("error", None)

@handler.register("loadTodosSuccess")
def handle_load_todos_success(state: Map, action: Action[List[TodoItem]]) -> Map:
    new_todos = tuple(action.payload)
    return state.set("loading", False).set("todos", new_todos).set("last_updated", time.time()).set("history", state["history"] + (len(new_todos),))

@handler.register("loadTodosFailure")
def handle_load_todos_failure(state: Map, action: Action[str]) -> Map:
    return state.set("loading", False).set("error", action.payload)

@handler.register("todosWarning")
def handle_todos_warning(state: Map, action: Action[int]) -> Map:
    return state.set("warning_count", state["warning_count"] + 1)

@handler.register("clearTodos")
def handle_clear_todos(state: Map, action: Action[None]) -> Map:
    new_todos = ()
    warning_count = state["warning_count"] + 1 if len(state["todos"]) > 0 else state["warning_count"]
    return state.set("todos", new_todos).set("last_updated", time.time()).set("history", state["history"] + (0,)).set("warning_count", warning_count)

@handler.register("batchAddTodosSuccess")
def handle_batch_add_todos_success(state: Map, action: Action[List[TodoItem]]) -> Map:
    new_todos = tuple(state["todos"]) + tuple(action.payload)
    warning_count = state["warning_count"] + 1 if len(new_todos) > state["max_todos"] else state["warning_count"]
    return state.set("todos", new_todos).set("last_updated", time.time()).set("history", state["history"] + (len(new_todos),)).set("warning_count", warning_count)

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
                return load_todos_success([
                    TodoItem(id=str(uuid.uuid4()), text="範例待辦 1", completed=False),
                    TodoItem(id=str(uuid.uuid4()), text="範例待辦 2", completed=True),
                ])
            except Exception as e:
                print(f"[Effect] fetch_todos exception: {e}")
                raise

        def to_observable(_):
            return from_future(asyncio.create_task(fetch_todos()))

        return action_stream.pipe(
            ofType(load_todos_request),
            ops.do_action(lambda _: print("Effect: 正在載入待辦事項...")),
            ops.flat_map(to_observable),
        )

    @create_effect
    def batch_add_todos(self, action_stream):
        async def batch_add(count: int):
            try:
                print(f"[Effect] 開始批量添加 {count} 個待辦事項")
                await asyncio.sleep(0.5)
                todos = [TodoItem(id=str(uuid.uuid4()), text=f"批量待辦 {i+1}", completed=False) for i in range(count)]
                print(f"[Effect] 準備 dispatch batchAddTodosSuccess")
                return batch_add_todos_success(todos)
            except Exception as e:
                print(f"[Effect] batch_add exception: {e}")
                raise

        def to_observable(action):
            return from_future(asyncio.create_task(batch_add(action.payload)))

        return action_stream.pipe(
            ofType(batch_add_todos_request),
            ops.do_action(lambda action: print(f"Effect: 正在批量添加 {action.payload} 個待辦事項...")),
            ops.flat_map(to_observable),
        )

    @create_effect(dispatch=False)
    def log_actions(self, action_stream):
        return action_stream.pipe(
            ops.do_action(lambda action: print(f"[Log] 動作: {action.type}")),
            ops.filter(lambda _: False),
        )
    
    @create_effect
    def handle_todos_warning_trigger(self, action_stream):
        def check_and_dispatch(action, store):
            state = store.state["todo"]
            todos_count = len(state["todos"])
            max_todos = state["max_todos"]
            if action.type == "addTodo" and todos_count >= max_todos:
                return todos_warning(todos_count)
            elif action.type == "clearTodos" and todos_count > 0:
                return todos_warning(0)
            return None
        def to_observable(action):
            result = check_and_dispatch(action, store)
            if result:
                return Observable.of(result)
            return Observable.empty()
        return action_stream.pipe(
            ofType(add_todo, clear_todos),
            ops.flat_map(to_observable),
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
    if action.type not in ["batchAddTodosSuccess"]:  # 減少複雜動作日誌
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
        if action.type in ["addTodo", "toggleTodo", "removeTodo", "loadTodosSuccess", "clearTodos", "batchAddTodosSuccess"]:
            serialized_state = self._serialize_state(next_state)
            try:
                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump(serialized_state, f, ensure_ascii=False)  # 移除 indent
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
get_todo_count = create_selector(get_todo_state, result_fn=lambda todo: len(todo.get("todos", ())))
store.select(get_todo_count).subscribe(lambda c: print(f"待辦事項數量: {c[1]}"))

def todo_count_monitor(count_tuple):
    old_count, new_count = count_tuple
    print(f"待辦事項數量: {old_count} -> {new_count}")

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
        old_count = len(old_state["todo"]["todos"]) if old_state["todo"].get("todos") is not None else 0
        new_count = len(new_state["todo"]["todos"]) if new_state["todo"].get("todos") is not None else 0
        max_todos = new_state["todo"].get("max_todos", 5)
        if new_count >= max_todos and old_count != new_count:  # 放寬條件
            print("todo超過上限！")
            store.dispatch(todos_warning(new_count))
        elif new_count == 0 and old_count > 0:
            print("待辦事項已清空！")
            store.dispatch(todos_warning(0))
    except Exception as e:
        print("狀態結構異常：", e)

store.select().subscribe(todo_warning_monitor)

# ====== 10. 測試函數 ======
async def high_frequency_dispatch():
    print("\n=== 高頻動作分派測試 ===")
    for i in range(50):
        store.dispatch(add_todo(f"高頻待辦 {i+1}"))
    for _ in range(20):
        todos = store.state["todo"]["todos"]
        if todos:
            store.dispatch(remove_todo(todos[0]["id"]))
    for _ in range(10):
        todos = store.state["todo"]["todos"]
        if todos:
            store.dispatch(toggle_todo(todos[0]["id"]))
    await asyncio.sleep(2)  # 等待處理完成

async def async_effects_test():
    print("\n=== 多個異步 Effect 測試 ===")
    for _ in range(5):
        store.dispatch(load_todos_request())
    store.dispatch(batch_add_todos_request(3))  # 批量添加 3 個待辦事項
    await asyncio.sleep(3)  # 等待所有 Effect 完成

async def warning_actions_test():
    print("\n=== 警告動作測試 ===")
    store.dispatch(clear_todos())  # 清空待辦事項，觸發 todosWarning
    await asyncio.sleep(1)

async def stress_test():
    print("\n=== 壓力測試（隨機 100 次動作） ===")
    actions = [
        (add_todo, lambda: f"壓力測試待辦 {random.randint(1, 1000)}"),
        (remove_todo, lambda: store.state["todo"]["todos"][0]["id"] if store.state["todo"]["todos"] else None),
        (toggle_todo, lambda: store.state["todo"]["todos"][0]["id"] if store.state["todo"]["todos"] else None),
        (clear_todos, lambda: None),
    ]
    weights = [0.3, 0.3, 0.3, 0.1]  # 降低 clearTodos 機率
    for _ in range(100):
        if not store.state["todo"]["todos"]:
            store.dispatch(add_todo(f"填充待辦 {random.randint(1, 1000)}"))
        todos = store.state["todo"]["todos"]
        if todos and random.random() < 0.6:
            action_type = random.choice([remove_todo, toggle_todo])
            payload = todos[0]["id"]
        else:
            action_type, payload_fn = random.choices(actions, weights=weights, k=1)[0]
            payload = payload_fn()
            if payload is None and action_type != clear_todos:
                continue
        store.dispatch(action_type(payload) if payload is not None else action_type())
    await asyncio.sleep(3)
    

async def main():
    print("\n=== 開始壓力測試範例 ===")
    store.dispatch(update_reducer())
    # 原有操作
    store.dispatch(add_todo("學習 PyStoreX"))
    store.dispatch(validate_and_add_todo("完成範例程式"))
    store.dispatch(toggle_todo(store.state["todo"]["todos"][0]["id"]))
    store.dispatch(add_todo("測試中介軟體"))
    store.dispatch(add_todo("快速新增1"))
    store.dispatch(add_todo("快速新增2"))
    store.dispatch(add_todo("額外測試項目1"))
    store.dispatch(add_todo("額外測試項目2"))
    store.dispatch(remove_todo(store.state["todo"]["todos"][1]["id"]))
    store.dispatch(load_todos_request())
    
    # 新增測試
    await high_frequency_dispatch()
    await async_effects_test()
    await warning_actions_test()
    await stress_test()
    
    # 輸出最終狀態和性能指標
    print("\n==== 最終狀態 ====")
    todo_state_map = store.state["todo"]
    todo_state_dict = to_dict(todo_state_map)
    todo_state_pydantic = to_pydantic(todo_state_map, TodoState)
    print(f"Todo 字典: {todo_state_dict}")
    print(f"Todo Pydantic: {todo_state_pydantic}")
    
    dev_tools = next(mw for mw in store._middleware if isinstance(mw, DevToolsMiddleware))
    history = dev_tools.get_history()
    print("\n==== DevTools 歷史 ====")
    for prev_state, action, next_state in history[-10:]:  # 僅顯示最後 10 條
        print(f"動作: {action.type}, 狀態變化: {to_dict(prev_state)} -> {to_dict(next_state)}")
    
    perf_monitor = next(mw for mw in store._middleware if isinstance(mw, PerformanceMonitorMiddleware))
    metrics = perf_monitor.get_metrics()
    print("\n==== 性能指標 ====")
    for action_type, data in metrics.items():
        print(f"動作 {action_type}: 平均 {data['avg']:.2f}ms, 最大 {data['max']:.2f}ms, 計數 {data['count']}")

if __name__ == "__main__":
    asyncio.run(main())