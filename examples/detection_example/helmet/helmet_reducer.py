from immutables import Map, MapMutation
from typing import Dict, List, TypedDict
from pystorex import create_reducer, on
from pystorex.immutable_utils import to_immutable
from shared.constants import (
    HELMET_STATUS,
    VIOLATION_THRESHOLD,
    NORMAL_THRESHOLD,
    NO_PERSON_THRESHOLD
)
from shared.utils import generate_person_id
from shared.detection_actions import visual_recognition

# ========== Model Definitions ==========
class PersonHelmetState(TypedDict):
    status: str  # 當前狀態（NORMAL, WARNING, VIOLATION）
    helmet_count: int  # 正確佩戴安全帽的累計次數
    no_helmet_count: int  # 未佩戴安全帽的累計次數
    no_person_count: int  # 無人偵測的累計次數
    last_position: List[float]  # 最後一次偵測到的位置
    last_seen: int  # 最後一次偵測到的幀數

class InitialState(TypedDict):
    helmet_states: Dict[str, PersonHelmetState]  # 每個人的安全帽狀態
    frameCount: int  # 當前幀數

# 初始狀態值
person_helmet_initial_state: PersonHelmetState = {
    "status": HELMET_STATUS["NORMAL"],
    "helmet_count": 0,
    "no_helmet_count": 0,
    "no_person_count": 0,
    "last_position": [],
    "last_seen": 0
}

initial_state: InitialState = {
    "helmet_states": {},
    "frameCount": 0
}

# ========== Utility Functions ==========
def is_helmet_worn_correctly(person_bbox: List[float], helmet_bbox: List[float]) -> bool:
    """
    判斷安全帽是否正確佩戴（通過檢測人頭部與安全帽的重疊）
    
    Args:
        person_bbox: 人員邊界框 [x, y, width, height, confidence]
        helmet_bbox: 安全帽邊界框 [x, y, width, height, confidence]
        
    Returns:
        bool: 是否正確佩戴
    """
    # 估算頭部區域（假設頭部在人員邊界框的上 1/4 區域）
    head_x = person_bbox[0]
    head_y = person_bbox[1]
    head_width = person_bbox[2]
    head_height = person_bbox[3] * 0.25  # 假設頭部占人高度的 1/4
    
    # 計算重疊區域
    x_overlap = max(0, min(head_x + head_width, helmet_bbox[0] + helmet_bbox[2]) - max(head_x, helmet_bbox[0]))
    y_overlap = max(0, min(head_y + head_height, helmet_bbox[1] + helmet_bbox[3]) - max(head_y, helmet_bbox[1]))
    overlap_area = x_overlap * y_overlap
    
    # 計算頭部區域面積
    head_area = head_width * head_height
    
    # 如果重疊面積超過頭部面積的 30%，認為安全帽佩戴正確
    return (overlap_area / head_area) > 0.3 if head_area > 0 else False

# ========== Helper Functions ==========
def update_person_helmet_state(
    person_data: Map,
    bbox: List[float],
    helmets: List[List[float]],
    frame_count: int
) -> Map:
    """
    更新單個人的安全帽狀態
    
    Args:
        person_data: 當前人員的狀態 (immutables.Map)
        bbox: 人員邊界框
        helmets: 所有安全帽邊界框
        frame_count: 當前幀數
        
    Returns:
        immutables.Map: 更新後的狀態
    """
    new_person_data = person_data.mutate()
    new_person_data["last_position"] = bbox[:4]
    new_person_data["last_seen"] = frame_count + 1
    new_person_data["no_person_count"] = 0  # 重置，因為人員被檢測到

    # 判斷是否正確佩戴安全帽
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

def update_no_person_count(
    helmet_states: Map,
    new_helmet_states: MapMutation,
    detected_pids: set,
    no_person_threshold: int
) -> None:
    """
    更新未檢測到的人員的 no_person_count，並移除達到閾值的記錄
    
    Args:
        helmet_states: 當前 helmet_states (immutables.Map)
        new_helmet_states: helmet_states 的 mutation
        detected_pids: 檢測到的 pid 集合
        no_person_threshold: 移除閾值
    """
    for pid in helmet_states:
        if pid not in detected_pids:
            person_data = helmet_states[pid]
            new_count = person_data["no_person_count"] + 1
            if new_count >= no_person_threshold:
                del new_helmet_states[pid]
            else:
                person_mutation = person_data.mutate()
                person_mutation["no_person_count"] = new_count
                new_helmet_states[pid] = person_mutation.finish()

# ========== Handlers ==========
def visual_recognition_handler(state: InitialState, action) -> InitialState:
    """
    處理 visual_recognition 動作，更新安全帽狀態
    
    Args:
        state: 當前狀態 (immutables.Map)
        action: 動作物件，包含偵測到的人員與安全帽資訊
        
    Returns:
        InitialState: 更新後的狀態 (immutables.Map)
    """

    # 檢查輸入格式
    persons = action.payload.get("persons", [])
    helmets = action.payload.get("helmets", [])
    # if not isinstance(persons, list) or not isinstance(helmets, list):
    #     raise ValueError("action.payload must contain 'persons' and 'helmets' as lists")

    helmet_states = state["helmet_states"]
    frame_count = state["frameCount"]

    # 創建主狀態的 mutation
    new_state = state.mutate()
    new_helmet_states = helmet_states.mutate()

    # 處理檢測到的人員
    detected_pids = set()
    if persons:
        new_state["frameCount"] = frame_count + 1
        for bbox in persons:
            pid = generate_person_id(bbox)
            detected_pids.add(pid)
            person_data = helmet_states.get(pid) or to_immutable(person_helmet_initial_state)
            new_helmet_states[pid] = update_person_helmet_state(
                person_data, bbox, helmets, frame_count
            )

    # 更新未檢測到的人員的 no_person_count（包括無人場景）
    update_no_person_count(helmet_states, new_helmet_states, detected_pids, NO_PERSON_THRESHOLD)

    # 完成修改
    new_state["helmet_states"] = new_helmet_states.finish()
    return new_state.finish()

# ========== Reducer ==========
helmet_status_reducer = create_reducer(
    to_immutable(initial_state),
    on(visual_recognition, visual_recognition_handler)
)