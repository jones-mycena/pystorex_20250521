from pathlib import Path
import sys

# 設置 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import time
import json
from typing import List, Dict, Tuple, Any, Optional, TypedDict
from immutables import Map, MapMutation
from pystorex.actions import create_action
from pystorex import create_reducer, on, create_store, EffectsModule, create_effect, StoreModule
from pystorex.store_selectors import create_selector
from pystorex.immutable_utils import to_immutable
from pystorex.rx_operators import ofType
from reactivex import operators as ops

# ============== 常量與禁區設定 ==============
VIOLATION_THRESHOLD = 3
NORMAL_THRESHOLD = 2
NO_PERSON_THRESHOLD = 2
FENCE_VIOLATION_THRESHOLD = 2

HELMET_STATUS = {
    "NORMAL": "正常佩戴",
    "WARNING": "可能未佩戴",
    "VIOLATION": "未佩戴"
}
FENCE_STATUS = {
    "OUTSIDE": "區域外",
    "WARNING": "進入警戒",
    "INTRUSION": "禁區闖入"
}
RESTRICTED_AREAS = [
    [50, 50, 150, 300],
    [400, 300, 500, 600]
]

# ============== Action Creators ==============
visual_recognition = create_action("visualRecognition")
log_violation = create_action("logViolation", lambda viols: {"violation_count": len(viols), "violations": viols})
log_warning = create_action("logWarning", lambda warns: {"warning_count": len(warns), "warnings": warns})
log_intrusion = create_action("logIntrusion", lambda intrs: {"intrusion_count": len(intrs), "intrusions": intrs, "areas": [st["area_index"] for st in intrs.values()]})
log_fence_warning = create_action("logFenceWarning", lambda warns: {"warning_count": len(warns), "warnings": warns, "areas": [st["area_index"] for st in warns.values()]})

# ============== State Models ==============
class FrameInfo(TypedDict):
    frameCount: int
    timestamp: Optional[float]

class PersonHelmetState(TypedDict):
    status: str
    helmet_count: int
    no_helmet_count: int
    no_person_count: int
    last_position: List[float]
    last_seen: int

class PersonFenceState(TypedDict):
    status: str
    intrusion_count: int
    outside_count: int
    area_index: int
    last_position: List[float]
    last_seen: int

# 初始狀態值
frame_info_initial_state: FrameInfo = {
    "frameCount": 0,
    "timestamp": None
}

person_helmet_initial_state: PersonHelmetState = {
    "status": HELMET_STATUS["NORMAL"],
    "helmet_count": 0,
    "no_helmet_count": 0,
    "no_person_count": 0,
    "last_position": [],
    "last_seen": 0
}

person_fence_initial_state: PersonFenceState = {
    "status": FENCE_STATUS["OUTSIDE"],
    "intrusion_count": 0,
    "outside_count": 0,
    "area_index": -1,
    "last_position": [],
    "last_seen": 0
}

# ============== Helper Functions ==============
def generate_person_id(bbox: List[float]) -> str:
    return f"person_{int(bbox[0])}_{int(bbox[1])}"

def is_helmet_worn_correctly(person_bbox: List[float], helmet_bbox: List[float]) -> bool:
    head_x, head_y, w, h, _ = person_bbox
    head_h = h * 0.25
    x_overlap = max(0, min(head_x + w, helmet_bbox[0] + helmet_bbox[2]) - max(head_x, helmet_bbox[0]))
    y_overlap = max(0, min(head_y + head_h, helmet_bbox[1] + helmet_bbox[3]) - max(head_y, helmet_bbox[1]))
    return (x_overlap * y_overlap) / (w * head_h) > 0.3 if (w * head_h) > 0 else False

def is_in_restricted_area(person_bbox: List[float]) -> Tuple[bool, int]:
    x = person_bbox[0] + person_bbox[2] / 2
    y = person_bbox[1] + person_bbox[3]
    for idx, area in enumerate(RESTRICTED_AREAS):
        if area[0] <= x <= area[2] and area[1] <= y <= area[3]:
            return True, idx
    return False, -1

def update_no_person_count(
    states: Map,
    new_states: MapMutation,
    detected_pids: set,
    no_person_threshold: int
) -> None:
    """更新未檢測到的人員的 no_person_count，並移除達到閾值的記錄"""
    for pid in states:
        if pid not in detected_pids:
            person_data = states[pid]
            new_count = person_data["no_person_count"] + 1
            if new_count >= no_person_threshold:
                print(f"Removing person {pid} due to no_person_count={new_count}")
                del new_states[pid]
            else:
                person_mutation = person_data.mutate()
                person_mutation["no_person_count"] = new_count
                new_states[pid] = person_mutation.finish()

# ============== Reducers ==============
def frame_info_handler(state: Map, action: Any) -> Map:
    if action.type != visual_recognition.type:
        return state
    persons = action.payload.get("persons", [])
    
    if not persons:
        return state
    new_state = state.mutate()
    new_state["frameCount"] = state["frameCount"] + 1
    new_state["timestamp"] = time.time()
    return new_state.finish()

frame_info_reducer = create_reducer(
    to_immutable(frame_info_initial_state),
    on(visual_recognition, frame_info_handler)
)

def update_person_helmet_state(
    person_data: Map,
    bbox: List[float],
    helmets: List[List[float]],
    frame_count: int
) -> Map:
    new_person_data = person_data.mutate()
    new_person_data["last_position"] = bbox[:4]
    new_person_data["last_seen"] = frame_count + 1
    new_person_data["no_person_count"] = 0  # 重置，因為人員被檢測到

    helmet_worn = any(is_helmet_worn_correctly(bbox, h) for h in helmets)
    if helmet_worn:
        new_person_data["no_helmet_count"] = 0
        new_person_data["helmet_count"] = person_data["helmet_count"] + 1
        if (
            person_data["status"] == HELMET_STATUS["VIOLATION"]
            and new_person_data["helmet_count"] >= NORMAL_THRESHOLD
        ):
            new_person_data["status"] = HELMET_STATUS["NORMAL"]
            new_person_data["helmet_count"] = 0
    else:
        new_person_data["helmet_count"] = 0
        new_person_data["no_helmet_count"] = person_data["no_helmet_count"] + 1
        new_person_data["status"] = (
            HELMET_STATUS["VIOLATION"]
            if new_person_data["no_helmet_count"] >= VIOLATION_THRESHOLD
            else HELMET_STATUS["WARNING"]
        )

    return new_person_data.finish()

def helmet_status_handler(state: Map, action: Any) -> Map:
    if action.type != visual_recognition.type:
        return state
    persons = action.payload.get("persons", [])
    helmets = action.payload.get("helmets", [])
    

    frame_count = store.state['frame_info']["frameCount"]
    new_states = state.mutate()
    detected_pids = set()

    if persons:
        for bbox in persons:
            pid = generate_person_id(bbox)
            detected_pids.add(pid)
            person_data = state.get(pid) or to_immutable(person_helmet_initial_state)
            new_states[pid] = update_person_helmet_state(person_data, bbox, helmets, frame_count)

    update_no_person_count(state, new_states, detected_pids, NO_PERSON_THRESHOLD)
    return new_states.finish()

helmet_status_reducer = create_reducer(
    to_immutable({}),
    on(visual_recognition, helmet_status_handler)
)

def update_person_fence_state(
    person_data: Map,
    bbox: List[float],
    in_restricted: bool,
    area_idx: int,
    frame_count: int
) -> Map:
    new_person_data = person_data.mutate()
    new_person_data["last_position"] = bbox[:4]
    new_person_data["last_seen"] = frame_count + 1
    new_person_data["no_person_count"] = 0  # 重置，因為人員被檢測到

    if in_restricted:
        new_person_data["intrusion_count"] = person_data["intrusion_count"] + 1
        new_person_data["outside_count"] = 0
        new_person_data["area_index"] = area_idx
        new_person_data["status"] = (
            FENCE_STATUS["INTRUSION"]
            if new_person_data["intrusion_count"] >= FENCE_VIOLATION_THRESHOLD
            else FENCE_STATUS["WARNING"]
        )
    else:
        new_person_data["intrusion_count"] = 0
        new_person_data["outside_count"] = person_data["outside_count"] + 1
        new_person_data["area_index"] = -1
        new_person_data["status"] = (
            FENCE_STATUS["OUTSIDE"]
            if new_person_data["outside_count"] >= NORMAL_THRESHOLD
            else FENCE_STATUS["WARNING"]
            if person_data["status"] == FENCE_STATUS["INTRUSION"]
            else person_data["status"]
        )

    return new_person_data.finish()

def fence_status_handler(state: Map, action: Any) -> Map:
    if action.type != visual_recognition.type:
        return state
    persons = action.payload.get("persons", [])

    frame_count = store.state['frame_info']["frameCount"]
    new_states = state.mutate()
    detected_pids = set()

    if persons:
        for bbox in persons:
            pid = generate_person_id(bbox)
            detected_pids.add(pid)
            in_restricted, area_idx = is_in_restricted_area(bbox)
            person_data = state.get(pid) or to_immutable(person_fence_initial_state)
            new_states[pid] = update_person_fence_state(person_data, bbox, in_restricted, area_idx, frame_count)

    update_no_person_count(state, new_states, detected_pids, NO_PERSON_THRESHOLD)
    return new_states.finish()

fence_status_reducer = create_reducer(
    to_immutable({}),
    on(visual_recognition, fence_status_handler)
)

# StoreModule.register_root({
#     "frame_info": frame_info_reducer,
#     "helmet_states": helmet_status_reducer,
#     "fence_states": fence_status_reducer
# }, store)

# ============== Selectors ==============
get_frame_info = create_selector(lambda s: s["frame_info"])
get_helmet_states = create_selector(lambda s: s["helmet_states"])
get_fence_states = create_selector(lambda s: s["fence_states"])
get_violation_persons = create_selector(
    get_helmet_states,
    result_fn=lambda d: {pid: ps for pid, ps in d.items() if ps["status"] == HELMET_STATUS["VIOLATION"]}
)
get_warning_persons = create_selector(
    get_helmet_states,
    result_fn=lambda d: {pid: ps for pid, ps in d.items() if ps["status"] == HELMET_STATUS["WARNING"]}
)
get_intrusion_persons = create_selector(
    get_fence_states,
    result_fn=lambda d: {pid: fs for pid, fs in d.items() if fs["status"] == FENCE_STATUS["INTRUSION"]}
)
get_fence_warning_persons = create_selector(
    get_fence_states,
    result_fn=lambda d: {pid: fs for pid, fs in d.items() if fs["status"] == FENCE_STATUS["WARNING"]}
)

# ============== Effects ==============
class HelmetEffects:
    @create_effect
    def watch_violations(self, action_stream):
        return action_stream.pipe(
            ofType(visual_recognition),
            ops.flat_map(lambda _: store.select(get_violation_persons)),  # 使用 flat_map 處理 Observable
            # ops.map(lambda _: store.select(get_violation_persons).value),
            ops.filter(lambda v: bool(v)),
            ops.map(lambda v: log_violation(v))
        )

    @create_effect
    def watch_warnings(self, action_stream):
        return action_stream.pipe(
            ofType(visual_recognition),
            ops.flat_map(lambda _: store.select(get_warning_persons)),  # 使用 flat_map 處理 Observable
            # ops.map(lambda _: store.select(get_warning_persons).value),
            ops.filter(lambda v: bool(v)),
            ops.map(lambda v: log_warning(v))
        )

class FenceEffects:
    @create_effect
    def watch_intrusions(self, action_stream):
        return action_stream.pipe(
            ofType(visual_recognition),
            ops.flat_map(lambda _: store.select(get_intrusion_persons)),  # 使用 flat_map 處理 Observable
            # ops.map(lambda _: store.select(get_intrusion_persons).value),
            ops.filter(lambda i: bool(i)),
            ops.map(lambda i: log_intrusion(i))
        )

    @create_effect
    def watch_fence_warnings(self, action_stream):
        return action_stream.pipe(
            ofType(visual_recognition),
            ops.flat_map(lambda _: store.select(get_fence_warning_persons)),  # 使用 flat_map 處理 Observable
            # ops.map(lambda _: store.select(get_fence_warning_persons).value),
            ops.filter(lambda i: bool(i)),
            ops.map(lambda i: log_fence_warning(i))
        )

# EffectsModule.register_root([HelmetEffects, FenceEffects], store)

# ============== Store 註冊 ==============
store = create_store()
store.register_root(
    {
        "frame_info": frame_info_reducer,
        "helmet_states": helmet_status_reducer,
        "fence_states": fence_status_reducer
    }
)
store.register_effects(HelmetEffects, FenceEffects)
# ============== 測試模擬資料 ==============
def create_sample_data():
    p1 = [100, 200, 80, 200, 0.95]
    p2 = [300, 220, 85, 210, 0.92]
    h1 = [110, 170, 70, 50, 0.88]
    h2 = [320, 190, 75, 55, 0.85]
    pr1 = [100, 100, 80, 150, 0.95]
    pr2 = [450, 350, 85, 150, 0.92]
    return [
        {"persons": [], "helmets": []},
        {"persons": [p1, p2], "helmets": []},
        {"persons": [pr1, p2], "helmets": []},
        {"persons": [pr1, p2], "helmets": [h1]},
        {"persons": [pr1, pr2], "helmets": [h1]},
        {"persons": [pr1, pr2], "helmets": [h1, h2]},
        {"persons": [pr2], "helmets": [h2]},
        {"persons": [p2], "helmets": [h2]},
        {"persons": [], "helmets": []},
        {"persons": [], "helmets": []}
    ]

# ============== 主程序 ==============
if __name__ == "__main__":
    # 訂閱示例
    store.select(get_frame_info).subscribe(lambda t: print(f"Frame: {t[1]['frameCount']}"))
    store.select(get_helmet_states).subscribe(lambda t: print("Helmet states:", t[1]))
    store.select(get_violation_persons).subscribe(lambda t: print("Violations:", t[1]))
    store.select(get_fence_states).subscribe(lambda t: print("Fence states:", t[1]))
    store.select(get_intrusion_persons).subscribe(lambda t: print("Intrusions:", t[1]))

    print("\n==== 開始模擬事件 ====")
    for i, frame in enumerate(create_sample_data(), 1):
        print(f"\n--- Frame {i}: persons={len(frame['persons'])}, helmets={len(frame['helmets'])} ---")
        store.dispatch(visual_recognition(frame))
        time.sleep(0.5)
    print("\n==== 完成 ====")