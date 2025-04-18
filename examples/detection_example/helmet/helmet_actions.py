# helmet_actions.py
from pystorex.actions import create_action

# 當有人進入違規狀態時的 action creator
log_violation = create_action(
    "logViolation",
    lambda violations: {
        "violation_count": len(violations),
        "violations": violations
    }
)

# 當有人進入警告狀態時的 action creator
log_warning = create_action(
    "logWarning",
    lambda warnings: {
        "warning_count": len(warnings),
        "warnings": warnings
    }
)
