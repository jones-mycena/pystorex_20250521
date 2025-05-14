
from pystorex.actions import create_action

# 當有人闖入禁區時的 action creator
log_intrusion = create_action(
    "logIntrusion",
    lambda intrusions: {
        "intrusion_count": len(intrusions),
        "intrusions": intrusions,
        "areas": [pstate['area_index'] for pstate in intrusions.values()],
    }
)
# 當有人進入禁區警告狀態時的 action creator
log_fence_warning = create_action(
    "logFenceWarning",
    lambda warnings: {
        "warning_count": len(warnings),
        "warnings": warnings,
        "areas": [pstate['area_index'] for pstate in warnings.values()],
    }
)