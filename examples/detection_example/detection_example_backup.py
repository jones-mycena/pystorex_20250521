"""
安全帽配戴檢測與電子圍籬狀態管理擴充 - 使用NgRx風格架構（重構版）
文件名: helmet_detection_with_fence_example.py
"""

from pystorex import (
    create_action,
    create_reducer,
    on,
    create_store,
    create_effect,
    create_selector,
    Action,
    StoreModule,
    EffectsModule
)
from reactivex import operators as ops
import time
import json
from typing import Dict, List, Optional, Tuple, Any
import copy

# ============== 定義常量 ==============
# 狀態轉換所需的累積次數
VIOLATION_THRESHOLD = 3  # 連續未佩戴安全帽x次被標記為違規
NORMAL_THRESHOLD = 2     # 連續正確佩戴安全帽x次回到正常
NO_PERSON_THRESHOLD = 3  # 連續x次無人檢測則重置該人的狀態
FENCE_VIOLATION_THRESHOLD = 2  # 連續x次進入禁區被標記為闖入違規

# 安全帽佩戴狀態枚舉
HELMET_STATUS = {
    "NORMAL": "正常佩戴",    # 正常佩戴安全帽
    "WARNING": "可能未佩戴",  # 警告狀態，未達到違規閾值
    "VIOLATION": "未佩戴"     # 確認未佩戴安全帽
}

# 禁區狀態枚舉
FENCE_STATUS = {
    "OUTSIDE": "區域外",    # 在禁區外
    "WARNING": "進入警戒",  # 剛進入禁區
    "INTRUSION": "禁區闖入"  # 持續在禁區內
}

# ============== 定義禁區 ==============
# 禁區定義為矩形區域 [x_min, y_min, x_max, y_max]
RESTRICTED_AREAS = [
    [50, 50, 150, 300],     # 禁區1 - 調整y範圍以確保測試數據落在範圍內
    [400, 300, 500, 600]    # 禁區2 - 調整y範圍以確保測試數據落在範圍內
]

# ============== 定義Actions ==============
# 只保留一個action: 視覺辨識
visual_recognition = create_action("visualRecognition")

# ============== 定義初始狀態 ==============
initial_state = {
    "helmet_states": {},  # 鍵為人員ID，值為該人員的安全帽配戴狀態信息
    "fence_states": {},   # 鍵為人員ID，值為該人員的禁區狀態信息
    "timestamp": None,    # 最後更新時間
    "frameCount": 0       # 已處理的幀數
}

# ============== 輔助函數 ==============
def is_helmet_worn_correctly(person_bbox, helmet_bbox) -> bool:
    """
    判斷安全帽是否正確佩戴（通過檢測人頭部與安全帽的重疊）
    
    Args:
        person_bbox: 人員邊界框 [x, y, width, height, confidence]
        helmet_bbox: 安全帽邊界框 [x, y, width, height, confidence]
        
    Returns:
        是否正確佩戴
    """
    # 估計頭部區域 (假設頭部在人員邊界框的上1/4處)
    head_x = person_bbox[0]
    head_y = person_bbox[1]
    head_width = person_bbox[2]
    head_height = person_bbox[3] * 0.25  # 假設頭部占人的高度的1/4
    
    # 計算重疊區域
    x_overlap = max(0, min(head_x + head_width, helmet_bbox[0] + helmet_bbox[2]) - max(head_x, helmet_bbox[0]))
    y_overlap = max(0, min(head_y + head_height, helmet_bbox[1] + helmet_bbox[3]) - max(head_y, helmet_bbox[1]))
    overlap_area = x_overlap * y_overlap
    
    # 計算頭部區域
    head_area = head_width * head_height
    
    # 如果重疊面積超過頭部面積的30%，認為安全帽佩戴正確
    return (overlap_area / head_area) > 0.3 if head_area > 0 else False

def generate_person_id(bbox) -> str:
    """
    根據人員邊界框生成唯一ID (簡化版，實際應用中應使用更複雜的識別算法)
    
    Args:
        bbox: 人員邊界框 [x, y, width, height, confidence]
    
    Returns:
        人員ID字符串
    """
    # 簡化實現：使用位置作為ID的一部分
    # 實際應用中應使用更穩健的特徵或跟蹤算法
    return f"person_{int(bbox[0])}_{int(bbox[1])}"

def is_in_restricted_area(person_bbox) -> Tuple[bool, int]:
    """
    檢查人員是否在禁區內
    
    Args:
        person_bbox: 人員邊界框 [x, y, width, height, confidence]
        
    Returns:
        (是否在禁區內, 禁區索引) - 如果不在任何禁區內，索引為-1
    """
    # 計算人員底部中心點(人在地面上站立的位置)
    person_x = person_bbox[0] + person_bbox[2] / 2
    person_y = person_bbox[1] + person_bbox[3]  # 底部坐標
    
    # 輸出調試信息
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

# ============== Redux 模式：拆分成多個獨立功能的子Reducer ==============

# 1. 處理幀計數和時間戳的Reducer
def frame_info_reducer(state, action: Action):
    """處理幀計數和時間戳更新"""
    if action.type != visual_recognition.type:
        return state
        
    new_state = copy.deepcopy(state)
    new_state["frameCount"] += 1
    new_state["timestamp"] = time.time()
    return new_state

# 2. 處理人員計數和清理的Reducer
def person_count_reducer(state, action: Action):
    """更新無人檢測計數並清理長時間未出現的人員"""
    if action.type != visual_recognition.type:
        return state
        
    frame_data = action.payload
    new_state = copy.deepcopy(state)
    no_persons = len(frame_data.get("persons", [])) == 0
    
    if no_persons:
        # 為所有已知人員增加無人計數
        for person_id in new_state["helmet_states"]:
            if "no_person_count" not in new_state["helmet_states"][person_id]:
                new_state["helmet_states"][person_id]["no_person_count"] = 0
            new_state["helmet_states"][person_id]["no_person_count"] += 1
            
        # 清理長時間未出現的人員
        persons_to_remove = []
        for person_id, person_data in new_state["helmet_states"].items():
            if person_data.get("no_person_count", 0) >= NO_PERSON_THRESHOLD:
                persons_to_remove.append(person_id)
        
        for person_id in persons_to_remove:
            del new_state["helmet_states"][person_id]
            # 同時清理禁區狀態
            if person_id in new_state["fence_states"]:
                del new_state["fence_states"][person_id]
    else:
        # 重置所有人的無人計數
        for person_id in new_state["helmet_states"]:
            new_state["helmet_states"][person_id]["no_person_count"] = 0
            
    return new_state

# 3. 處理安全帽配戴狀態的Reducer
def helmet_status_reducer(state, action: Action):
    """處理安全帽配戴狀態更新"""
    if action.type != visual_recognition.type:
        return state
        
    frame_data = action.payload
    persons = frame_data.get("persons", [])
    
    # 無人場景，直接返回原狀態
    if not persons:
        return state
    
    new_state = copy.deepcopy(state)
    helmets = frame_data.get("helmets", [])
    
    # 處理當前幀中的每個人
    for person_bbox in persons:
        person_id = generate_person_id(person_bbox)
        
        # 檢查此人是否有正確佩戴安全帽
        helmet_worn = False
        for helmet_bbox in helmets:
            if is_helmet_worn_correctly(person_bbox, helmet_bbox):
                helmet_worn = True
                break
        
        # 如果是新人，初始化狀態
        if person_id not in new_state["helmet_states"]:
            new_state["helmet_states"][person_id] = {
                "status": HELMET_STATUS["NORMAL"],
                "no_helmet_count": 0,
                "helmet_count": 0,
                "no_person_count": 0,
                "last_position": person_bbox[:4],  # 存儲位置，不含置信度
                "last_seen": new_state["frameCount"]
            }
        
        # 更新人員狀態
        person_data = new_state["helmet_states"][person_id]
        person_data["last_position"] = person_bbox[:4]
        person_data["last_seen"] = new_state["frameCount"]
        
        if helmet_worn:
            # 重置未佩戴計數，增加佩戴計數
            person_data["no_helmet_count"] = 0
            person_data["helmet_count"] += 1
            
            # 如果連續正確佩戴達到閾值，恢復為正常狀態
            if person_data["status"] == HELMET_STATUS["VIOLATION"] and person_data["helmet_count"] >= NORMAL_THRESHOLD:
                person_data["status"] = HELMET_STATUS["NORMAL"]
                person_data["helmet_count"] = 0
        else:
            # 重置佩戴計數，增加未佩戴計數
            person_data["helmet_count"] = 0
            person_data["no_helmet_count"] += 1
            
            # 如果連續未佩戴達到閾值，設為違規狀態
            if person_data["no_helmet_count"] >= VIOLATION_THRESHOLD:
                person_data["status"] = HELMET_STATUS["VIOLATION"]
            elif person_data["no_helmet_count"] > 0:
                person_data["status"] = HELMET_STATUS["WARNING"]
    
    return new_state

# 4. 處理禁區狀態的Reducer
def fence_status_reducer(state, action: Action):
    """處理禁區狀態更新"""
    if action.type != visual_recognition.type:
        return state
        
    frame_data = action.payload
    persons = frame_data.get("persons", [])
    
    # 無人場景，直接返回原狀態
    if not persons:
        return state
    
    new_state = copy.deepcopy(state)
    
    # 處理當前幀中的每個人
    for person_bbox in persons:
        person_id = generate_person_id(person_bbox)
        
        # 檢查此人是否在禁區內
        in_restricted, area_index = is_in_restricted_area(person_bbox)
        
        # 如果是新人，初始化禁區狀態
        if person_id not in new_state["fence_states"]:
            new_state["fence_states"][person_id] = {
                "status": FENCE_STATUS["OUTSIDE"],
                "intrusion_count": 0,
                "outside_count": 0,
                "area_index": -1,
                "last_position": person_bbox[:4],  # 存儲位置，不含置信度
                "last_seen": new_state["frameCount"]
            }
        
        # 更新人員禁區狀態
        fence_data = new_state["fence_states"][person_id]
        fence_data["last_position"] = person_bbox[:4]
        fence_data["last_seen"] = new_state["frameCount"]
        
        if in_restricted:
            # 增加闖入計數，重置離開計數
            fence_data["intrusion_count"] += 1
            fence_data["outside_count"] = 0
            fence_data["area_index"] = area_index
            
            # 如果連續闖入達到閾值，設為闖入狀態
            if fence_data["intrusion_count"] >= FENCE_VIOLATION_THRESHOLD:
                fence_data["status"] = FENCE_STATUS["INTRUSION"]
            else:
                fence_data["status"] = FENCE_STATUS["WARNING"]
        else:
            # 重置闖入計數
            fence_data["intrusion_count"] = 0
            
            # 如果目前已經是闖入狀態，立即轉為警告狀態
            if fence_data["status"] == FENCE_STATUS["INTRUSION"]:
                fence_data["status"] = FENCE_STATUS["WARNING"]
                
            # 增加離開計數
            fence_data["outside_count"] += 1
            
            # 如果離開達到閾值，恢復為正常狀態
            if fence_data["outside_count"] >= NORMAL_THRESHOLD:
                fence_data["status"] = FENCE_STATUS["OUTSIDE"]
                fence_data["area_index"] = -1
    
    return new_state

# ============== 創建每個獨立的Reducer ==============
frame_info_reducer_obj = create_reducer(
    initial_state,
    on(visual_recognition, frame_info_reducer)
)

person_count_reducer_obj = create_reducer(
    initial_state,
    on(visual_recognition, person_count_reducer)
)

helmet_status_reducer_obj = create_reducer(
    initial_state,
    on(visual_recognition, helmet_status_reducer)
)

fence_status_reducer_obj = create_reducer(
    initial_state,
    on(visual_recognition, fence_status_reducer)
)

# ============== 創建Store 並分別注册 Reducer ==============
# 新版API方式
store = create_store()
StoreModule.register_root({
    "frame_info": frame_info_reducer_obj,
    "person_count": person_count_reducer_obj,
    "helmet_status": helmet_status_reducer_obj,
    "fence_status": fence_status_reducer_obj
}, store)

# ============== 定義Selectors ==============
# 選擇不同feature的狀態
get_frame_info_state = lambda state: state["frame_info"]
get_person_count_state = lambda state: state["person_count"]
get_helmet_status_state = lambda state: state["helmet_status"]
get_fence_status_state = lambda state: state["fence_status"]

# 從不同feature選擇資料
get_frame_count = create_selector(get_frame_info_state, result_fn=lambda state: state.get("frameCount", 0))
get_timestamp = create_selector(get_frame_info_state, result_fn=lambda state: state.get("timestamp"))

get_helmet_states = create_selector(get_helmet_status_state, result_fn=lambda state: state.get("helmet_states", {}))
get_fence_states = create_selector(get_fence_status_state, result_fn=lambda state: state.get("fence_states", {}))

# 複合選擇器
get_all_persons = create_selector(get_helmet_status_state, result_fn=lambda state: state.get("helmet_states", {}))

get_all_fences = create_selector(
    get_fence_status_state, 
    result_fn=lambda state: state.get("fence_states", {})
)

get_violation_persons = create_selector(
    get_helmet_status_state, 
    result_fn=lambda state: {
        person_id: data for person_id, data in state.get("helmet_states", {}).items() 
        if data["status"] == HELMET_STATUS["VIOLATION"]
    }
)

get_intrusion_persons = create_selector(
    get_fence_status_state,
    result_fn=lambda state: {
        person_id: data for person_id, data in state.get("fence_states", {}).items() 
        if data["status"] == FENCE_STATUS["INTRUSION"]
    }
)

get_warning_persons = create_selector(
    get_helmet_status_state,
    result_fn=lambda state: {
        person_id: data for person_id, data in state.get("helmet_states", {}).items() 
        if data["status"] == HELMET_STATUS["WARNING"]
    }
)

get_fence_warning_persons = create_selector(
    get_fence_status_state,
    result_fn=lambda state: {
        person_id: data for person_id, data in state.get("fence_states", {}).items() 
        if data["status"] == FENCE_STATUS["WARNING"]
    }
)

# ============== 定義Effects ==============
class HelmetEffects:
    @create_effect
    def log_violations(action_stream):
        """當有人進入違規狀態時記錄告警"""
        return action_stream.pipe(
            ops.filter(lambda action: action.type == visual_recognition.type),
            ops.map(lambda _: store.state),  # 獲取最新狀態
            ops.map(lambda state: get_violation_persons(state)),
            ops.distinct_until_changed(lambda violations: len(violations)),  # 只在違規人數變化時觸發
            ops.filter(lambda violations: len(violations) > 0),
            ops.map(lambda violations: Action(
                type="logViolation", 
                payload={"violation_count": len(violations), "violations": violations}
            ))
        )
    
    @create_effect
    def log_warnings(action_stream):
        """當有人進入警告狀態時記錄告警"""
        return action_stream.pipe(
            ops.filter(lambda action: action.type == visual_recognition.type),
            ops.map(lambda _: store.state),  # 獲取最新狀態
            ops.map(lambda state: get_warning_persons(state)),
            ops.distinct_until_changed(lambda warnings: len(warnings)),  # 只在警告人數變化時觸發
            ops.filter(lambda warnings: len(warnings) > 0),
            ops.map(lambda warnings: Action(
                type="logWarning", 
                payload={"warning_count": len(warnings), "warnings": warnings}
            ))
        )

class FenceEffects:
    @create_effect
    def log_intrusions(action_stream):
        """當有人闖入禁區時記錄告警"""
        return action_stream.pipe(
            ops.filter(lambda action: action.type == visual_recognition.type),
            ops.map(lambda _: store.state),  # 獲取最新狀態
            ops.map(lambda state: get_intrusion_persons(state)),
            ops.distinct_until_changed(lambda intrusions: len(intrusions)),  # 只在闖入人數變化時觸發
            ops.filter(lambda intrusions: len(intrusions) > 0),
            ops.map(lambda intrusions: Action(
                type="logIntrusion", 
                payload={
                    "intrusion_count": len(intrusions), 
                    "intrusions": intrusions,
                    "areas": [data["area_index"] for person_id, data in intrusions.items()]
                }
            ))
        )
        
    @create_effect
    def log_fence_warnings(action_stream):
        """當有人進入禁區警告狀態時記錄告警"""
        return action_stream.pipe(
            ops.filter(lambda action: action.type == visual_recognition.type),
            ops.map(lambda _: store.state),  # 獲取最新狀態
            ops.map(lambda state: get_fence_warning_persons(state)),
            ops.distinct_until_changed(lambda warnings: len(warnings)),  # 只在警告人數變化時觸發
            ops.filter(lambda warnings: len(warnings) > 0),
            ops.map(lambda warnings: Action(
                type="logFenceWarning", 
                payload={
                    "warning_count": len(warnings), 
                    "warnings": warnings,
                    "areas": [data["area_index"] for person_id, data in warnings.items()]
                }
            ))
        )

# ============== 註冊Effects ==============
# 使用新版API註冊effects
EffectsModule.register_root([HelmetEffects, FenceEffects], store)

# ============== 模擬視覺識別數據 ==============
def create_sample_data():
    """創建10個模擬場景數據，包含所有重要情境"""
    
    # 一些固定的人員和安全帽位置
    person1 = [100, 200, 80, 200, 0.95]  # [x, y, width, height, confidence]
    person2 = [300, 220, 85, 210, 0.92]
    helmet1 = [110, 170, 70, 50, 0.88]    # 正確位置，與person1頭部重疊
    helmet2 = [320, 190, 75, 55, 0.85]    # 正確位置，與person2頭部重疊
    
    # 進入禁區的人員
    person1_restricted = [100, 100, 80, 150, 0.95]  # 在禁區1內，底部中心點(140, 250)
    person2_restricted = [450, 350, 85, 150, 0.92]  # 在禁區2內，底部中心點(492.5, 500)
    
    samples = [
        # 1. 一開始畫面沒人
        {
            "persons": [],
            "helmets": []
        },
        
        # 2. 出現兩人，都沒有戴安全帽
        {
            "persons": [person1, person2],
            "helmets": []
        },
        
        # 3. 這兩人繼續沒戴安全帽，第一人進入禁區
        {
            "persons": [person1_restricted, person2],
            "helmets": []
        },
        
        # 4. 第一人在禁區內戴好安全帽，第二人還是沒戴
        {
            "persons": [person1_restricted, person2],
            "helmets": [helmet1]
        },
        
        # 5. 第二人也進入另一個禁區，但仍未戴安全帽
        {
            "persons": [person1_restricted, person2_restricted],
            "helmets": [helmet1]
        },
        
        # 6. 第二人在禁區中也戴好安全帽
        {
            "persons": [person1_restricted, person2_restricted],
            "helmets": [helmet1, helmet2]
        },
        
        # 7. 第一人消失（離開畫面）
        {
            "persons": [person2_restricted],
            "helmets": [helmet2]
        },
        
        # 8. 第二人離開禁區，但仍戴著安全帽
        {
            "persons": [person2],
            "helmets": [helmet2]
        },
        
        # 9. 第二人也消失（離開畫面）
        {
            "persons": [],
            "helmets": []
        },
        
        # 10. 畫面持續無人
        {
            "persons": [],
            "helmets": []
        }
    ]
    
    return samples

# ============== 處理訂閱資料合併的輔助函數 ==============
def merge_state_data():
    """合併各個feature的資料到一個完整的狀態視圖"""
    complete_state = {
        "helmet_states": get_helmet_states(store.state),
        "fence_states": get_fence_states(store.state),
        "timestamp": get_timestamp(store.state),
        "frameCount": get_frame_count(store.state)
    }
    return complete_state

# ============== 使用示例 ==============
if __name__ == "__main__":
    
    # 訂閱處理
    store.select(get_helmet_states).subscribe(
        on_next=lambda state_tuple: print(f"人員安全帽狀態變化: \n新狀態: {json.dumps(state_tuple[1], ensure_ascii=False, indent=2)}\n")
    )

    store.select(get_fence_states).subscribe(
        on_next=lambda state_tuple: print(f"人員禁區狀態變化: \n新狀態: {json.dumps(state_tuple[1], ensure_ascii=False, indent=2)}\n")
    )
    
    # 訂閱違規狀態的人員
    store.select(get_violation_persons).subscribe(
        on_next=lambda violations_tuple: print(f"違規人員變化: {len(violations_tuple[1])} 人\n") if violations_tuple[1] else None
    )
    
    # 訂閱闖入禁區的人員
    store.select(get_intrusion_persons).subscribe(
        on_next=lambda intrusions_tuple: print(f"闖入禁區人員變化: {len(intrusions_tuple[1])} 人\n") if intrusions_tuple[1] else None
    )
    
    # 生成模擬數據
    sample_data = create_sample_data()
    
    # 模擬視覺識別事件
    print("\n==== 開始模擬視覺識別事件 ====")
    for i, frame_data in enumerate(sample_data):
        print(f"\n=== 第 {i+1} 幀 ===")
        print(f"識別結果: 人數 {len(frame_data['persons'])}, 安全帽數 {len(frame_data['helmets'])}")
        
        # 只分發視覺識別Action
        store.dispatch(visual_recognition(frame_data))
        
        # 暫停以便觀察
        time.sleep(1)
    
    # 打印最終狀態
    print("\n==== 最終狀態 ====")
    print(json.dumps(merge_state_data(), ensure_ascii=False, indent=2))