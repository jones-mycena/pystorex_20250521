from shared.effects_utils import make_log_effect
from pystorex import create_effect, Action
from reactivex import operators as ops
from shared.constants import HELMET_STATUS
from shared import store
from .helmet_selectors import get_violation_persons, get_warning_persons
from .helmet_actions import log_violation, log_warning

class HelmetEffects:
    @create_effect
    def log_violations(action_stream):
        """當有人進入違規狀態時記錄告警"""
        return action_stream.pipe(
            make_log_effect(get_violation_persons, log_violation)
            # ops.filter(lambda action: action.type == "visualRecognition"),
            # ops.map(lambda _: store.state),  # 獲取最新狀態
            # ops.map(lambda state: get_violation_persons(state)),
            # ops.distinct_until_changed(lambda violations: len(violations)),  # 只在違規人數變化時觸發
            # ops.filter(lambda violations: len(violations) > 0),
            # ops.map(lambda vs: log_violation(vs))
        )

    @create_effect
    def log_warnings(action_stream):
        """當有人進入警告狀態時記錄告警"""
        return action_stream.pipe(
            make_log_effect(get_warning_persons, log_warning)
            # ops.filter(lambda action: action.type == "visualRecognition"),
            # ops.map(lambda _: store.state),  # 獲取最新狀態
            # ops.map(lambda state: get_warning_persons(state)),
            # ops.distinct_until_changed(lambda warnings: len(warnings)),  # 只在警告人數變化時觸發
            # ops.filter(lambda warnings: len(warnings) > 0),
            # ops.map(lambda ws: log_warning(ws))
        )