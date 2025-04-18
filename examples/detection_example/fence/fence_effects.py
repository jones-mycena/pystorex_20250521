from detection_example.shared.effects_utils import make_log_effect
from pystorex import create_effect, Action
from reactivex import operators as ops
from detection_example.shared.constants import FENCE_STATUS
from detection_example.shared import store
from detection_example.shared.detection_actions import visual_recognition
from .fence_selectors import get_intrusion_persons, get_fence_warning_persons
from .fence_actions import log_intrusion, log_fence_warning

class FenceEffects:
    @create_effect
    def log_intrusions(action_stream):
        """當有人闖入禁區時記錄告警"""
        return action_stream.pipe(
            
            make_log_effect(get_intrusion_persons, log_intrusion)
            # ops.filter(lambda action: action.type == visual_recognition.type),
            # ops.map(lambda _: store.state),  # 獲取最新狀態
            # ops.map(lambda state: get_intrusion_persons(state)),
            # ops.distinct_until_changed(lambda intrusions: len(intrusions)),  # 只在闖入人數變化時觸發
            # ops.filter(lambda intrusions: len(intrusions) > 0),
            # ops.map(lambda intrusions: log_intrusion(intrusions))
        )
        
    @create_effect
    def log_fence_warnings(action_stream):
        """當有人進入禁區警告狀態時記錄告警"""
        return action_stream.pipe(
            make_log_effect(get_fence_warning_persons, log_fence_warning)
            # ops.filter(lambda action: action.type == visual_recognition.type),
            # ops.map(lambda _: store.state),  # 獲取最新狀態
            # ops.map(lambda state: get_fence_warning_persons(state)),
            # ops.distinct_until_changed(lambda warnings: len(warnings)),  # 只在警告人數變化時觸發
            # ops.filter(lambda warnings: len(warnings) > 0),
            # ops.map(lambda warnings: log_fence_warning(warnings))
        )