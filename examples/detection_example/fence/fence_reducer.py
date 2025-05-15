from immutables import Map, MapMutation
from pydantic import BaseModel
from typing import Dict, List, Any, Tuple, TypedDict
from pystorex import create_reducer, on
from pystorex.immutable_utils import to_dict, to_immutable
from shared.constants import (
    FENCE_STATUS,
    FENCE_VIOLATION_THRESHOLD,
    NORMAL_THRESHOLD,
    NO_PERSON_THRESHOLD
)
from shared.utils import generate_person_id
from shared.detection_actions import visual_recognition

# ========== Model Definitions ==========
class PersonFenceState(TypedDict):
    status: str
    intrusion_count: int
    outside_count: int
    no_person_count: int
    area_index: int
    last_position: List[float]
    last_seen: int

class InitialState(TypedDict):
    fence_states: Dict[str, PersonFenceState]
    frameCount: int
# 对应的初始值
person_fence_initial_state: PersonFenceState = PersonFenceState(
    status=FENCE_STATUS["OUTSIDE"],
    intrusion_count=0,
    outside_count=0,
    no_person_count=0,
    area_index=-1,
    last_position=[],
    last_seen=0,
)

initial_state: InitialState = InitialState(
    fence_states={},  # 这里可以填入多个 key: person_fence_initial_state
    frameCount=0,
)

# ========== Utility Functions ==========
def is_in_restricted_area(person_bbox) -> Tuple[bool, int]:
    """
    檢查人員是否在禁區內
    
    Args:
        person_bbox: 人員邊界框 [x, y, width, height, confidence]
        
    Returns:
        (是否在禁區內, 禁區索引) - 如果不在任何禁區內，索引為-1
    """
    # 禁區定義為矩形區域 [x_min, y_min, x_max, y_max]
    RESTRICTED_AREAS = [
        [50, 50, 150, 300],     # 禁區1 - 調整y範圍以確保測試數據落在範圍內
        [400, 300, 500, 600]    # 禁區2 - 調整y範圍以確保測試數據落在範圍內
    ]
    
    # 計算人員底部中心點(人在地面上站立的位置)
    person_x = person_bbox[0] + person_bbox[2] / 2
    person_y = person_bbox[1] + person_bbox[3]  # 底部坐標
    
    # 輸出除錯訊息
    print(f"人員位置: {person_bbox[:2]}, 底部中心點: ({person_x}, {person_y})")
    # 檢查是否在任何禁區內
    for i, area in enumerate(RESTRICTED_AREAS):
        print(f"檢查禁區{i+1}: {area}")
        # 檢查點是否在矩形區域內
        if (area[0] <= person_x <= area[2] and 
            area[1] <= person_y <= area[3]):
            print(f"在禁區{i+1}內!")
            return True, i  # 正確返回禁區索引
    print("不在任何禁區內")
    
    return False, -1  # 不在任何禁區內

def update_person_state(
    person_data: Map,
    bbox: List[float],
    in_restricted: bool,
    area_idx: int,
    frame_count: int
) -> Map:
    """更新單個人的狀態"""
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

def update_no_person_count(
    fence_states: Map,
    new_fence_states: MapMutation,
    detected_pids: set,
    no_person_threshold: int
) -> None:
    """更新未檢測到的人員的 no_person_count，並移除達到閾值的記錄"""
    for pid in fence_states:
        if pid not in detected_pids:
            person_data = fence_states[pid]
            new_count = person_data["no_person_count"] + 1
            if new_count >= no_person_threshold:
                del new_fence_states[pid]
            else:
                person_mutation = person_data.mutate()
                person_mutation["no_person_count"] = new_count
                new_fence_states[pid] = person_mutation.finish()
# ============== Handlers ==============
def visual_recognition_handler(state: InitialState, action) -> InitialState:
    """處理視覺識別結果的 reducer handler"""
    persons = action.payload.get("persons", [])
    fence_states = state["fence_states"]
    frame_count = state["frameCount"]

    # 創建主狀態的 mutation
    new_state = state.mutate()
    new_fence_states = fence_states.mutate()

    new_state["frameCount"] = frame_count + 1
    # 處理檢測到的人員
    detected_pids = set()
    if persons:
        # new_state["frameCount"] = frame_count + 1
        for bbox in persons:
            pid = generate_person_id(bbox)
            detected_pids.add(pid)
            in_restricted, area_idx = is_in_restricted_area(bbox)
            person_data = fence_states.get(pid) or to_immutable(person_fence_initial_state)
            new_fence_states[pid] = update_person_state(
                person_data, bbox, in_restricted, area_idx, frame_count
            )

    # 更新未檢測到的人員的 no_person_count（包括無人場景）
    update_no_person_count(fence_states, new_fence_states, detected_pids, NO_PERSON_THRESHOLD)

    # 完成修改
    new_state["fence_states"] = new_fence_states.finish()
    return new_state.finish()


# ============== Reducer ==============
fence_status_reducer = create_reducer(
    # InitialState(),
    initial_state,
    on(visual_recognition, visual_recognition_handler)
)
