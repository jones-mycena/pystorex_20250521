from pystorex import create_selector
from detection_example.shared.constants import HELMET_STATUS

get_helmet_status_state = lambda state: state["helmet_status"]
get_helmet_states = create_selector(
    get_helmet_status_state,
    result_fn=lambda state: state.helmet_states or {}
)

get_violation_persons = create_selector(
    get_helmet_status_state,
    result_fn=lambda state: {
        person_id: data for person_id, data in state.helmet_states.items()
        if data["status"] == HELMET_STATUS["VIOLATION"]
    }
)

get_warning_persons = create_selector(
    get_helmet_status_state,
    result_fn=lambda state: {
        person_id: data for person_id, data in state.helmet_states.items()
        if data["status"] == HELMET_STATUS["WARNING"]
    }
)