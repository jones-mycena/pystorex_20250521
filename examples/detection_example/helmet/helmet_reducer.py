from pydantic import BaseModel
from typing import Dict, List
from pystorex import create_reducer, on
from shared.constants import (
    HELMET_STATUS,
    VIOLATION_THRESHOLD,
    NORMAL_THRESHOLD,
    NO_PERSON_THRESHOLD
)
from shared.utils import generate_person_id
from shared.detection_actions import visual_recognition

# ========== Model Definitions ==========
class PersonHelmetState(BaseModel):
    """
    定義每個人的安全帽狀態
    """
    status: str = HELMET_STATUS["NORMAL"]  # 當前狀態（NORMAL, WARNING, VIOLATION）
    helmet_count: int = 0  # 正確佩戴安全帽的累計次數
    no_helmet_count: int = 0  # 未佩戴安全帽的累計次數
    no_person_count: int = 0  # 無人偵測的累計次數
    last_position: List[float] = []  # 最後一次偵測到的位置
    last_seen: int = 0  # 最後一次偵測到的幀數

class InitialState(BaseModel):
    """
    定義初始狀態
    """
    helmet_states: Dict[str, PersonHelmetState] = {}  # 每個人的安全帽狀態
    frameCount: int = 0  # 當前幀數

# ========== Utility Functions ==========
def is_helmet_worn_correctly(person_bbox, helmet_bbox) -> bool:
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

# ========== Handlers ==========
def visual_recognition_handler(state: InitialState, action) -> InitialState:
    """
    處理 visual_recognition 動作，更新安全帽狀態
    
    Args:
        state: 當前狀態
        action: 動作物件，包含偵測到的人員與安全帽資訊
        
    Returns:
        InitialState: 更新後的狀態
    """
    if action.type != visual_recognition.type:
        return state

    # 深複製整個狀態物件
    new_state: InitialState = state.model_copy()
    helmet_states = dict(new_state.helmet_states)  # 拷貝子字典，避免修改原始資料
    persons = action.payload.get("persons", [])
    helmets = action.payload.get("helmets", [])

    # 無人場景：累計 no_person_count，達到閾值後刪除該人的狀態
    if not persons:
        for pid in list(helmet_states.keys()):
            ps = helmet_states[pid]
            ps.no_person_count += 1
            if ps.no_person_count >= NO_PERSON_THRESHOLD:
                del helmet_states[pid]
        return new_state

    # 有人場景：重置所有人的 no_person_count
    for ps in helmet_states.values():
        ps.no_person_count = 0

    # 更新幀數
    new_state.frameCount += 1

    # 處理每個人
    for bbox in persons:
        pid = generate_person_id(bbox)
        # 如果是新偵測到的人，初始化其狀態
        if pid not in helmet_states:
            helmet_states[pid] = PersonHelmetState(
                last_position=bbox[:4],
                last_seen=new_state.frameCount
            )

        ps = helmet_states[pid]
        ps.last_position = bbox[:4]
        ps.last_seen = new_state.frameCount

        # 判斷是否正確佩戴安全帽
        helmet_worn = any(
            is_helmet_worn_correctly(bbox, h) for h in helmets
        )
        if helmet_worn:
            ps.no_helmet_count = 0
            ps.helmet_count += 1
            # 如果之前是 VIOLATION，且連續正常達到閾值，回到 NORMAL
            if (
                ps.status == HELMET_STATUS["VIOLATION"]
                and ps.helmet_count >= NORMAL_THRESHOLD
            ):
                ps.status = HELMET_STATUS["NORMAL"]
                ps.helmet_count = 0
        else:
            ps.helmet_count = 0
            ps.no_helmet_count += 1
            if ps.no_helmet_count >= VIOLATION_THRESHOLD:
                ps.status = HELMET_STATUS["VIOLATION"]
            else:
                ps.status = HELMET_STATUS["WARNING"]

    return new_state

# ========== Reducer ==========
helmet_status_reducer = create_reducer(
    InitialState(),
    on(visual_recognition, visual_recognition_handler)
)
