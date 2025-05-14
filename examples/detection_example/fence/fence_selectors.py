from pystorex import create_selector
from shared.constants import FENCE_STATUS

# 先拿到那個 feature state (InitialState instance)
get_fence_status_state = lambda root_state: root_state["fence_status"]

get_fence_states = create_selector(
    get_fence_status_state,
    result_fn=lambda fs_state: fs_state['fence_states'] or {}
)

get_intrusion_persons = create_selector(
    get_fence_status_state,
    result_fn=lambda fs_state: {
        pid: pstate
        for pid, pstate in fs_state['fence_states'].items()
        if pstate['status'] == FENCE_STATUS["INTRUSION"]
    }
)

get_fence_warning_persons = create_selector(
    get_fence_status_state,
    result_fn=lambda fs_state: {
        pid: pstate
        for pid, pstate in fs_state['fence_states'].items()
        if pstate['status'] == FENCE_STATUS["WARNING"]
    }
)
