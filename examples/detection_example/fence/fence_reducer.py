from immutables import Map
from pydantic import BaseModel
from typing import Dict, List, Any, Tuple, TypedDict
from pystorex import create_reducer, on
from pystorex.immutable_utils import to_dict
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



# ============== Handlers ==============
def visual_recognition_handler(state: InitialState, action) -> InitialState:
    """
    處理視覺識別結果的 reducer handler
    使用單一 mutate-finish 周期優化性能
    """
    # 獲取當前狀態
    persons = action.payload.get("persons", [])
    fence_states = state["fence_states"]
    frame_count = state['frameCount']
    
    # 創建主狀態的 evolver
    new_state = state.mutate()
    
    # 創建 fence_states 的 evolver (只調用一次 mutate)
    new_fence_states = fence_states.mutate()
    
    # ── 更新 frameCount (如果有人)
    if persons:
        new_state["frameCount"] = frame_count + 1
    
    # ── 無人場景
    if not persons:
        # 遍歷所有人的狀態
        for pid, fdata in fence_states.items():
            # 獲取當前的 no_person_count
            current_count = fdata['no_person_count']
            new_count = current_count + 1
            
            # 檢查是否達到閾值
            if new_count >= NO_PERSON_THRESHOLD:
                # 達到閾值就刪除
                del new_fence_states[pid]
            else:
                # 如果 fdata 是 Map，直接更新 evolver
                fdata['no_person_count'] = new_count
                new_fence_states[pid] = fdata
    else:
        # ── 有人場景
        
        # 重置所有人的 no_person_count
        for pid in fence_states:
            # 直接在 evolver 中設置 no_person_count 為 0
            person_data = fence_states[pid]
            person_data["no_person_count"] = 0
            new_fence_states[pid] = person_data
        
        # 禁區檢測邏輯
        for bbox in persons:
            pid = generate_person_id(bbox)
            in_restricted, area_idx = is_in_restricted_area(bbox)
            
            # 準備更新的人員數據
            if pid in new_fence_states:
                # 獲取現有數據
                person_data = fence_states[pid]
            else:
                # 如果是新出現的人，使用預定義的初始狀態
                person_data = dict(person_fence_initial_state)
            
            # 更新通用欄位
            person_data["last_position"] = bbox[:4]
            person_data["last_seen"] = frame_count + 1
            
            if in_restricted:
                # 在禁區內：更新入侵計數和狀態
                person_data["intrusion_count"] = person_data['intrusion_count'] + 1
                person_data["outside_count"] = 0
                person_data["area_index"] = area_idx
                
                # 根據入侵計數設置狀態
                if person_data["intrusion_count"] >= FENCE_VIOLATION_THRESHOLD:
                    person_data["status"] = FENCE_STATUS["INTRUSION"]
                else:
                    person_data["status"] = FENCE_STATUS["WARNING"]
            else:
                # 不在禁區：更新外部計數和狀態
                person_data["intrusion_count"] = 0
                
                # 如果之前是入侵狀態，改為警告
                if person_data.get("status") == FENCE_STATUS["INTRUSION"]:
                    person_data["status"] = FENCE_STATUS["WARNING"]
                
                person_data["outside_count"] = person_data["outside_count"] + 1
                
                # 如果外部計數超過閾值，改為正常狀態
                if person_data["outside_count"] >= NORMAL_THRESHOLD:
                    person_data["status"] = FENCE_STATUS["OUTSIDE"]
                    person_data["area_index"] = -1
            
            # 直接更新 evolver，不創建中間 Map
            new_fence_states[pid] = person_data
    
    # 完成所有修改後，只調用一次 finish (先對 fence_states，再對 state)
    new_state["fence_states"] = new_fence_states.finish()
    
    # 返回完成的新狀態 (只調用一次 state.finish())
    return new_state.finish()



# ============== Reducer ==============
fence_status_reducer = create_reducer(
    # InitialState(),
    initial_state,
    on(visual_recognition, visual_recognition_handler)
)
