import sys
sys.path.append(r"c:\work\pystorex")
import sys
import time
import json
from typing import List, Dict, Tuple, Any, Optional
from pydantic import BaseModel
from pystorex.actions import create_action
from pystorex import create_reducer, on, create_store, EffectsModule, create_effect, StoreModule
from pystorex.store_selectors import create_selector
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
log_violation    = create_action("logViolation",    lambda viols: {"violation_count": len(viols), "violations": viols})
log_warning      = create_action("logWarning",      lambda warns: {"warning_count": len(warns), "warnings": warns})
log_intrusion    = create_action("logIntrusion",    lambda intrs: {"intrusion_count": len(intrs), "intrusions": intrs, "areas":[st.area_index for st in intrs.values()]})
log_fence_warning= create_action("logFenceWarning", lambda warns: {"warning_count": len(warns), "warnings": warns, "areas":[st.area_index for st in warns.values()]})

# ============== State Models ==============
class FrameInfo(BaseModel):
    frameCount: int = 0
    timestamp: Optional[float] = None

class PersonHelmetState(BaseModel):
    status: str = HELMET_STATUS["NORMAL"]
    helmet_count: int = 0
    no_helmet_count: int = 0
    no_person_count: int = 0
    last_position: List[float] = []
    last_seen: int = 0

class PersonFenceState(BaseModel):
    status: str = FENCE_STATUS["OUTSIDE"]
    intrusion_count: int = 0
    outside_count: int = 0
    area_index: int = -1
    last_position: List[float] = []
    last_seen: int = 0

# ============== Helper Functions ==============
def generate_person_id(bbox) -> str:
    return f"person_{int(bbox[0])}_{int(bbox[1])}"

def is_helmet_worn_correctly(person_bbox, helmet_bbox) -> bool:
    head_x, head_y, w, h, _ = person_bbox
    head_h = h * 0.25
    x_overlap = max(0, min(head_x + w, helmet_bbox[0] + helmet_bbox[2]) - max(head_x, helmet_bbox[0]))
    y_overlap = max(0, min(head_y + head_h, helmet_bbox[1] + helmet_bbox[3]) - max(head_y, helmet_bbox[1]))
    return (x_overlap * y_overlap) / (w * head_h) > 0.3 if (w*head_h)>0 else False

def is_in_restricted_area(person_bbox) -> Tuple[bool,int]:
    x = person_bbox[0] + person_bbox[2]/2
    y = person_bbox[1] + person_bbox[3]
    for idx, area in enumerate(RESTRICTED_AREAS):
        if area[0] <= x <= area[2] and area[1] <= y <= area[3]:
            return True, idx
    return False, -1

# ============== Reducers ==============
def frame_info_handler(state: FrameInfo, action) -> FrameInfo:
    if action.type != visual_recognition.type:
        return state
    new = state.copy(deep=True)
    new.frameCount += 1
    new.timestamp = time.time()
    return new

frame_info_reducer = create_reducer(FrameInfo(), on(visual_recognition, frame_info_handler))


def helmet_status_handler(state: Dict[str, PersonHelmetState], action) -> Dict[str, PersonHelmetState]:
    if action.type != visual_recognition.type:
        return state
    data = action.payload
    persons = data.get("persons", [])
    helmets = data.get("helmets", [])
    # cleanup missing
    for pid, ps in list(state.items()):
        ps.no_person_count += 1
        if ps.no_person_count >= NO_PERSON_THRESHOLD:
            del state[pid]
    new = {pid: ps for pid, ps in state.items() if ps.no_person_count<NO_PERSON_THRESHOLD}
    # update current persons
    for bbox in persons:
        pid = generate_person_id(bbox)
        ps = new.get(pid, PersonHelmetState(last_position=bbox[:4], last_seen=0))
        ps.no_person_count = 0
        ps.last_position  = bbox[:4]
        ps.last_seen      = frame_count+1 if False else ps.last_seen
        worn = any(is_helmet_worn_correctly(bbox,h) for h in helmets)
        if worn:
            ps.helmet_count += 1; ps.no_helmet_count=0
            if ps.status==HELMET_STATUS["VIOLATION"] and ps.helmet_count>=NORMAL_THRESHOLD:
                ps.status=HELMET_STATUS["NORMAL"]; ps.helmet_count=0
        else:
            ps.no_helmet_count +=1; ps.helmet_count=0
            ps.status = HELMET_STATUS["VIOLATION"] if ps.no_helmet_count>=VIOLATION_THRESHOLD else HELMET_STATUS["WARNING"]
        new[pid]=ps
    return new

helmet_status_reducer = create_reducer({}, on(visual_recognition, helmet_status_handler))


def fence_status_handler(state: Dict[str, PersonFenceState], action) -> Dict[str, PersonFenceState]:
    if action.type != visual_recognition.type:
        return state
    data=action.payload
    persons=data.get("persons",[])
    new=state.copy()
    for bbox in persons:
        pid=generate_person_id(bbox)
        fs=new.get(pid, PersonFenceState(last_position=bbox[:4],last_seen=0))
        fs.last_position=bbox[:4]
        fs.last_seen     +=1
        in_re, idx = is_in_restricted_area(bbox)
        if in_re:
            fs.intrusion_count+=1; fs.outside_count=0; fs.area_index=idx
            fs.status = FENCE_STATUS["INTRUSION"] if fs.intrusion_count>=FENCE_VIOLATION_THRESHOLD else FENCE_STATUS["WARNING"]
        else:
            fs.intrusion_count=0
            if fs.status==FENCE_STATUS["INTRUSION"]: fs.status=FENCE_STATUS["WARNING"]
            fs.outside_count+=1
            if fs.outside_count>=NORMAL_THRESHOLD:
                fs.status=FENCE_STATUS["OUTSIDE"]; fs.area_index=-1
        new[pid]=fs
    return new

fence_status_reducer = create_reducer({}, on(visual_recognition, fence_status_handler))

# ============== Store 註冊 ==============
store = create_store()
StoreModule.register_root({
    "frame_info": frame_info_reducer,
    "helmet_states": helmet_status_reducer,
    "fence_states": fence_status_reducer
}, store)

# ============== Selectors ==============
get_frame_info    = create_selector(lambda s:s["frame_info"])  
get_helmet_states = create_selector(lambda s:s["helmet_states"])  
get_fence_states  = create_selector(lambda s:s["fence_states"])
get_violation_persons = create_selector(get_helmet_states, result_fn=lambda d:{pid:ps for pid,ps in d.items() if ps.status==HELMET_STATUS["VIOLATION"]})
get_intrusion_persons = create_selector(get_fence_states, result_fn=lambda d:{pid:fs for pid,fs in d.items() if fs.status==FENCE_STATUS["INTRUSION"]})

# ============== Effects ==============
class HelmetEffects:
    @create_effect
    def watch_helmet(self, action_stream):
        return action_stream.pipe(
            ops.filter(lambda a: a.type==visual_recognition.type),
            ops.map(lambda _: store.state),
            ops.map(lambda s:get_violation_persons(s)),
            ops.filter(lambda v:bool(v)),
            ops.map(lambda v: log_violation(v))
        )

class FenceEffects:
    @create_effect
    def watch_fence(self, action_stream):
        return action_stream.pipe(
            ops.filter(lambda a:a.type==visual_recognition.type),
            ops.map(lambda _: store.state),
            ops.map(lambda s:get_intrusion_persons(s)),
            ops.filter(lambda i:bool(i)),
            ops.map(lambda i: log_intrusion(i))
        )

EffectsModule.register_root([HelmetEffects, FenceEffects], store)

# ============== 測試模擬資料 ==============
def create_sample_data():
    p1=[100,200,80,200,0.95]; p2=[300,220,85,210,0.92]
    h1=[110,170,70,50,0.88]; h2=[320,190,75,55,0.85]
    pr1=[100,100,80,150,0.95]; pr2=[450,350,85,150,0.92]
    return [
        {"persons":[],"helmets":[]},
        {"persons":[p1,p2],"helmets":[]},
        {"persons":[pr1,p2],"helmets":[]},
        {"persons":[pr1,p2],"helmets":[h1]},
        {"persons":[pr1,pr2],"helmets":[h1]},
        {"persons":[pr1,pr2],"helmets":[h1,h2]},
        {"persons":[pr2],"helmets":[h2]},
        {"persons":[p2],"helmets":[h2]},
        {"persons":[],"helmets":[]},
        {"persons":[],"helmets":[]}
    ]

if __name__=="__main__":
    # 訂閱示例
    store.select(lambda s:(None,s["frame_info"].frameCount)).subscribe(lambda t: print(f"Frame: {t[1]}"))
    store.select(get_helmet_states).subscribe(lambda tpl: print("Helmet states:",tpl[1]))
    store.select(get_violation_persons).subscribe(lambda tpl: print("Violations:",tpl[1]))
    store.select(get_fence_states).subscribe(lambda tpl: print("Fence states:",tpl[1]))
    store.select(get_intrusion_persons).subscribe(lambda tpl: print("Intrusions:",tpl[1]))

    print("\n==== 開始模擬事件 ====")
    for i,frame in enumerate(create_sample_data(),1):
        print(f"\n--- Frame {i}: persons={len(frame['persons'])}, helmets={len(frame['helmets'])} ---")
        store.dispatch(visual_recognition(frame))
        time.sleep(0.5)
    print("\n==== 完成 ====")
