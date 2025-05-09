import sys
sys.path.append(r"c:\work\pystorex")
import time
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel
from reactivex import operators as ops

from pystorex.actions import create_action, Action
from pystorex import create_store, create_reducer, on, create_effect
from pystorex.store_selectors import create_selector
from pystorex.middleware import LoggerMiddleware, ThunkMiddleware

# ====== 1. 定義狀態模型 ======
class TodoItem(BaseModel):
    id: str
    text: str
    completed: bool = False
    priority: int = 1  # 優先級: 1-低, 2-中, 3-高

class UserState(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    preferences: Dict[str, Any] = {}
    
class TodosState(BaseModel):
    items: List[TodoItem] = []
    loading: bool = False
    filter: str = "all"  # all, active, completed
    error: Optional[str] = None

class CounterState(BaseModel):
    count: int = 0
    loading: bool = False
    error: Optional[str] = None
    last_updated: Optional[float] = None

# ====== 2. 定義 Actions ======
# Counter Actions
increment = create_action("[Counter] Increment")
decrement = create_action("[Counter] Decrement")
reset = create_action("[Counter] Reset", lambda value: value)
increment_by = create_action("[Counter] IncrementBy", lambda amount: amount)
load_count_request = create_action("[Counter] LoadCountRequest")
load_count_success = create_action("[Counter] LoadCountSuccess", lambda value: value)
load_count_failure = create_action("[Counter] LoadCountFailure", lambda error: error)
count_warning = create_action("[Counter] CountWarning", lambda count: count)

# Todo Actions
load_todos_request = create_action("[Todos] LoadTodosRequest")
load_todos_success = create_action("[Todos] LoadTodosSuccess", lambda todos: todos)
load_todos_failure = create_action("[Todos] LoadTodosFailure", lambda error: error)
add_todo = create_action("[Todos] AddTodo", lambda todo: todo)
toggle_todo = create_action("[Todos] ToggleTodo", lambda id: id)
remove_todo = create_action("[Todos] RemoveTodo", lambda id: id)
set_todos_filter = create_action("[Todos] SetFilter", lambda filter: filter)

# User Actions
load_user_request = create_action("[User] LoadUserRequest")
load_user_success = create_action("[User] LoadUserSuccess", lambda user: user)
load_user_failure = create_action("[User] LoadUserFailure", lambda error: error)
update_user_preference = create_action("[User] UpdatePreference", 
                                     lambda payload: payload)  # {key, value}

# Notification Actions
notify = create_action("[Notification] Show", 
                     lambda payload: payload)  # {type, message}

# Workload Actions
workload_update = create_action("[Workload] Update", lambda level: level)

# ====== 3. 定義 Reducers ======
# Counter Reducer
def counter_handler(state: CounterState, action: Action) -> CounterState:
    new_state = state.copy(deep=True)
    now = time.time()

    if action.type == increment.type:
        new_state.count += 1
        new_state.last_updated = now
    elif action.type == decrement.type:
        new_state.count -= 1
        new_state.last_updated = now
    elif action.type == reset.type:
        new_state.count = action.payload
        new_state.last_updated = now
    elif action.type == increment_by.type:
        new_state.count += action.payload
        new_state.last_updated = now
    elif action.type == load_count_request.type:
        new_state.loading = True
        new_state.error = None
    elif action.type == load_count_success.type:
        new_state.loading = False
        new_state.count = action.payload
        new_state.last_updated = now
    elif action.type == load_count_failure.type:
        new_state.loading = False
        new_state.error = action.payload
    
    return new_state

counter_reducer = create_reducer(
    CounterState(),
    on(increment, counter_handler),
    on(decrement, counter_handler),
    on(reset, counter_handler),
    on(increment_by, counter_handler),
    on(load_count_request, counter_handler),
    on(load_count_success, counter_handler),
    on(load_count_failure, counter_handler),
)

# Todos Reducer
def todos_handler(state: TodosState, action: Action) -> TodosState:
    new_state = state.copy(deep=True)
    
    if action.type == load_todos_request.type:
        new_state.loading = True
        new_state.error = None
    elif action.type == load_todos_success.type:
        new_state.loading = False
        new_state.items = action.payload
    elif action.type == load_todos_failure.type:
        new_state.loading = False
        new_state.error = action.payload
    elif action.type == add_todo.type:
        new_state.items.append(action.payload)
    elif action.type == toggle_todo.type:
        for item in new_state.items:
            if item.id == action.payload:
                item.completed = not item.completed
    elif action.type == remove_todo.type:
        new_state.items = [item for item in new_state.items if item.id != action.payload]
    elif action.type == set_todos_filter.type:
        new_state.filter = action.payload
    
    return new_state

todos_reducer = create_reducer(
    TodosState(),
    on(load_todos_request, todos_handler),
    on(load_todos_success, todos_handler),
    on(load_todos_failure, todos_handler),
    on(add_todo, todos_handler),
    on(toggle_todo, todos_handler),
    on(remove_todo, todos_handler),
    on(set_todos_filter, todos_handler),
)

# User Reducer
def user_handler(state: UserState, action: Action) -> UserState:
    new_state = state.copy(deep=True)
    
    if action.type == load_user_success.type:
        new_state.id = action.payload.get("id")
        new_state.name = action.payload.get("name")
        new_state.preferences = action.payload.get("preferences", {})
    elif action.type == update_user_preference.type:
        key = action.payload.get("key")
        value = action.payload.get("value")
        if key:
            new_state.preferences[key] = value
    
    return new_state

user_reducer = create_reducer(
    UserState(),
    on(load_user_success, user_handler),
    on(update_user_preference, user_handler),
)

# ====== 4. 定義 Effects ======
class CounterEffects:
    @create_effect
    def load_count(self, action_stream):
        """模擬從 API 載入數據的副作用"""
        return action_stream.pipe(
            ops.filter(lambda action: action.type == load_count_request.type),
            ops.do_action(lambda _: print("Effect: Loading counter...")),
            ops.delay(1.0),  # 延遲 1 秒
            ops.map(lambda _: load_count_success(42))  # 假設 API 回傳 42
        )
    
    @create_effect(dispatch=False)
    def handle_count_warning(self, action_stream):
        """處理計數器警告"""
        return action_stream.pipe(
            ops.filter(lambda action: action.type == count_warning.type),
            ops.do_action(lambda action: print(f"[Warning] 計數器達到高值: {action.payload}")),
            ops.filter(lambda _: False)
        )

class TodosEffects:
    @create_effect
    def load_todos(self, action_stream):
        """模擬從 API 載入待辦事項的副作用"""
        return action_stream.pipe(
            ops.filter(lambda action: action.type == load_todos_request.type),
            ops.do_action(lambda _: print("Effect: Loading todos...")),
            ops.delay(1.5),  # 延遲 1.5 秒
            ops.map(lambda _: load_todos_success([
                TodoItem(id="1", text="學習 PyStoreX", completed=True, priority=2),
                TodoItem(id="2", text="寫文檔", completed=False, priority=3),
                TodoItem(id="3", text="修復 bug", completed=False, priority=3),
                TodoItem(id="4", text="提交代碼", completed=False, priority=1),
            ]))
        )

class UserEffects:
    @create_effect
    def load_user(self, action_stream):
        """模擬從 API 載入用戶資料的副作用"""
        return action_stream.pipe(
            ops.filter(lambda action: action.type == load_user_request.type),
            ops.do_action(lambda _: print("Effect: Loading user...")),
            ops.delay(0.8),  # 延遲 0.8 秒
            ops.map(lambda _: load_user_success({
                "id": "user1",
                "name": "張三",
                "preferences": {"theme": "dark"}
            }))
        )

class WorkloadEffects:
    @create_effect
    def update_notification(self, action_stream):
        """當工作負載變更時發送通知"""
        return action_stream.pipe(
            ops.filter(lambda action: action.type == workload_update.type),
            ops.map(lambda action: notify({
                "type": "info" if action.payload != "高" else "warning",
                "message": f"您的工作負載已更新為【{action.payload}】級別"
            }))
        )

# ====== 5. 建立 Store 與註冊 ======
store = create_store()

# 中間件順序非常重要!
# ThunkMiddleware 必須在 LoggerMiddleware 之前註冊
store.apply_middleware(ThunkMiddleware())
# store.apply_middleware(LoggerMiddleware)

# 註冊 reducers
store.register_root({
    "counter": counter_reducer,
    "todos": todos_reducer,
    "user": user_reducer
})

# 註冊 effects
store.register_effects(CounterEffects(), TodosEffects(), UserEffects(), WorkloadEffects())

# ====== 6. 定義 Selectors ======
# 基礎選擇器
get_counter_state = lambda state: state["counter"]
get_todos_state = lambda state: state["todos"]
get_user_state = lambda state: state["user"]

# Counter 衍生選擇器
get_count = create_selector(
    get_counter_state,
    result_fn=lambda counter: counter.count
)

get_counter_loading = create_selector(
    get_counter_state,
    result_fn=lambda counter: counter.loading
)

# Todos 衍生選擇器
get_todos = create_selector(
    get_todos_state,
    result_fn=lambda todos_state: todos_state.items
)

get_todos_filter = create_selector(
    get_todos_state,
    result_fn=lambda todos_state: todos_state.filter
)

get_todos_loading = create_selector(
    get_todos_state,
    result_fn=lambda todos_state: todos_state.loading
)

# User 衍生選擇器
get_user_name = create_selector(
    get_user_state,
    result_fn=lambda user: user.name
)

get_user_preferences = create_selector(
    get_user_state,
    result_fn=lambda user: user.preferences
)

# 複合選擇器 - 這裡展示 selector 包 selector
get_filtered_todos = create_selector(
    get_todos,
    get_todos_filter,
    result_fn=lambda todos, filter_type: [
        todo for todo in todos if (
            filter_type == "all" or
            (filter_type == "active" and not todo.completed) or
            (filter_type == "completed" and todo.completed)
        )
    ]
)

get_filtered_todos_count = create_selector(
    get_filtered_todos,
    result_fn=lambda filtered_todos: len(filtered_todos)
)

get_high_priority_todos = create_selector(
    get_todos,
    result_fn=lambda todos: [todo for todo in todos if todo.priority == 3]
)

get_completed_todos_count = create_selector(
    get_todos,
    result_fn=lambda todos: sum(1 for todo in todos if todo.completed)
)

# 高級複合選擇器 - 組合多個功能領域的選擇器
get_user_todo_stats = create_selector(
    get_user_name,
    get_todos,
    get_filtered_todos_count,
    get_completed_todos_count,
    get_high_priority_todos,
    get_count,  # 從 counter 模組中獲取數據
    result_fn=lambda user_name, all_todos, filtered_count, completed_count, high_priority_todos, counter: {
        "user_name": user_name,
        "total_todos": len(all_todos),
        "filtered_count": filtered_count,
        "completed_count": completed_count,
        "high_priority_count": len(high_priority_todos),
        "completion_percentage": round((completed_count / len(all_todos)) * 100) if all_todos else 0,
        "counter_value": counter
    }
)

# 獲取使用者工作負荷級別 - 使用另一個選擇器的結果
get_user_workload = create_selector(
    get_user_todo_stats,
    result_fn=lambda stats: (
        "高" if stats["high_priority_count"] >= 2 and stats["completion_percentage"] < 30 else
        "中" if stats["total_todos"] - stats["completed_count"] > 2 else
        "低"
    )
)

# ====== 7. 設置 Selector Monitors ======
# 監控計數器並在超過閾值時發出警告
def count_warning_monitor(value_tuple):
    if value_tuple is None:
        return
    
    old_value, new_value = value_tuple
    if new_value > 8 and (old_value is None or old_value <= 8):
        store.dispatch(count_warning(new_value))

# 監控工作負荷變化
def workload_monitor(value_tuple):
    if value_tuple is None:
        return
    
    old_value, new_value = value_tuple
    if old_value != new_value:
        store.dispatch(workload_update(new_value))

# 註冊監視器
store.select(get_count).subscribe(count_warning_monitor)
store.select(get_user_workload).subscribe(workload_monitor)

# 監控 user_todo_stats 的變化
store.select(get_user_todo_stats).subscribe(
    lambda stats_tuple: print(f"User Todo Stats 更新: {stats_tuple[1] if stats_tuple else 'None'}")
)

# ====== 8. 創建 Thunk Actions ======
def load_all_data():
    """使用 Thunk 載入所有需要的數據"""
    def thunk(dispatch, get_state):
        print("Thunk: 開始載入所有數據")
        # 首先檢查數據是否已經載入
        state = get_state()
        todos_loading = state["todos"].loading
        user_id = state["user"].id
        
        dispatch(load_user_request())
        
        if not todos_loading and not state["todos"].items:
            dispatch(load_todos_request())
            
        dispatch(load_count_request())
        
        return {"status": "loading_started"}
    
    return thunk

def complete_all_todos():
    """使用 Thunk 完成所有待辦事項"""
    def thunk(dispatch, get_state):
        print("Thunk: 完成所有待辦事項")
        state = get_state()
        todos = state["todos"].items
        
        for todo in todos:
            if not todo.completed:
                dispatch(toggle_todo(todo.id))
                
        return {"status": "success", "completed": len(todos)}
    
    return thunk

# ====== 9. 執行示例 ======
def run_demo():
    # 設置訂閱查看變化
    store.select(get_count).subscribe(
        lambda value_tuple: print(f"Count: {value_tuple[1] if value_tuple else 'None'}")
    )
    
    store.select(get_filtered_todos).subscribe(
        lambda todos_tuple: print(f"Filtered Todos: {len(todos_tuple[1]) if todos_tuple and todos_tuple[1] else 0}")
    )
    
    store.select(get_user_workload).subscribe(
        lambda workload_tuple: print(f"User Workload: {workload_tuple[1] if workload_tuple else 'None'}")
    )
    
    # 使用 Thunk 載入所有數據
    print("\n載入所有數據...")
    result = store.dispatch(load_all_data())
    print(f"載入結果: {result}")
    
    # 等待數據載入完成
    time.sleep(2)
    
    # 測試其他動作
    print("\n增加計數值...")
    store.dispatch(increment())
    store.dispatch(increment_by(5))
    
    print("\n增加一個高優先級任務...")
    store.dispatch(add_todo(TodoItem(
        id="5", 
        text="緊急修復生產環境問題", 
        completed=False,
        priority=3
    )))
    
    # 變更篩選器
    print("\n變更篩選器為 'active'...")
    store.dispatch(set_todos_filter("active"))
    
    # 完成部分任務
    print("\n完成一個任務...")
    store.dispatch(toggle_todo("3"))
    
    # 使用另一個 Thunk
    print("\n嘗試完成所有待辦事項...")
    result = store.dispatch(complete_all_todos())
    print(f"完成結果: {result}")
    
    # 嘗試產生高值計數器警告
    print("\n增加計數到警告閾值...")
    store.dispatch(reset(10))
    
    # 最終狀態
    print("\n最終狀態:")
    print(f"計數值: {get_count(store.state)}")
    print(f"工作負荷: {get_user_workload(store.state)}")
    
    stats = get_user_todo_stats(store.state)
    print(f"完成率: {stats['completion_percentage']}%")
    print(f"高優先級任務數: {stats['high_priority_count']}")

if __name__ == "__main__":
    run_demo()