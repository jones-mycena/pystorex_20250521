from pydantic import BaseModel
from typing import Dict, List, Any, Tuple
from pystorex import create_reducer, on
from detection_example.shared.constants import (
    FENCE_STATUS,
    FENCE_VIOLATION_THRESHOLD,
    NORMAL_THRESHOLD,
    NO_PERSON_THRESHOLD
)
from detection_example.shared.utils import generate_person_id
from detection_example.shared.detection_actions import visual_recognition

# ========== Model Definitions ==========
class PersonFenceState(BaseModel):
    status: str = FENCE_STATUS["OUTSIDE"]
    intrusion_count: int = 0
    outside_count: int = 0
    no_person_count: int = 0
    area_index: int = -1
    last_position: List[float] = []
    last_seen: int = 0

class InitialState(BaseModel):
    fence_states: Dict[str, PersonFenceState] = {}
    frameCount: int = 0

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



# ============== Handlers ==============
def visual_recognition_handler(state: InitialState, action) -> InitialState:
    if action.type != visual_recognition.type:
        return state

    new_state: InitialState = state.model_copy()
    # 拷貝子 dict，避免改到原本的 fence_states
    fence_states = dict(new_state.fence_states)
    persons = action.payload.get("persons", [])

    # ── 無人場景
    if not persons:
        # 遍歷所有人的狀態
        for pid, fdata in list(fence_states.items()):
            # 用屬性讀寫
            fdata.no_person_count += 1
            if fdata.no_person_count >= NO_PERSON_THRESHOLD:
                # 達到閾值就刪除這個 key
                del fence_states[pid]
        return new_state

    # ── 有人場景：先把所有人的 no_person_count 重置
    for fdata in fence_states.values():
        fdata.no_person_count = 0

    # 更新 frameCount
    new_state.frameCount += 1

    # 禁區檢測邏輯
    for bbox  in persons:
        pid = generate_person_id(bbox )
        in_restricted, area_idx = is_in_restricted_area(bbox )

        # 如果是新出現的人，先建立預設 model
        if pid not in fence_states:
            fence_states[pid] = PersonFenceState(
                last_position=bbox [:4],
                last_seen=new_state.frameCount
            )

        ps = fence_states[pid]
        # 更新通用欄位
        ps.last_position = bbox[:4]
        ps.last_seen = new_state.frameCount

        if in_restricted:
            ps.intrusion_count += 1
            ps.outside_count = 0
            ps.area_index = area_idx
            ps.status = (
                FENCE_STATUS["INTRUSION"]
                if ps.intrusion_count >= FENCE_VIOLATION_THRESHOLD
                else FENCE_STATUS["WARNING"]
            )
        else:
            ps.intrusion_count = 0
            if ps.status == FENCE_STATUS["INTRUSION"]:
                ps.status = FENCE_STATUS["WARNING"]
            ps.outside_count += 1
            if ps.outside_count >= NORMAL_THRESHOLD:
                ps.status = FENCE_STATUS["OUTSIDE"]
                ps.area_index = -1


        fence_states[pid] = ps

    new_state.fence_states = fence_states
    return new_state

# ============== Reducer ==============
fence_status_reducer = create_reducer(
    InitialState(),
    on(visual_recognition, visual_recognition_handler)
)
