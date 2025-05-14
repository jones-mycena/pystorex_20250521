from pystorex.effects import create_effect
from reactivex import operators as ops

from counter_actions import (
    load_count_request,
    load_count_success,
    load_count_failure,
    count_warning
)
from pystorex.rx_operators import ofType



class CounterEffects:
    @create_effect
    def load_count(self, action_stream):
        """模擬從 API 載入數據的副作用，成功後 dispatch load_count_success"""
        return action_stream.pipe(
            # ops.filter(lambda action: action.type == load_count_request.type),
            ofType(load_count_request),
            ops.do_action(lambda _: print("Effect: Loading counter...")),
            ops.delay(1.0),  # 延遲 1 秒
            ops.map(lambda _: load_count_success(42))  # 假設 API 回傳 42
        )

    @create_effect(dispatch=False)
    def log_actions(self, action_stream):
        """只做日誌，不 dispatch 新 action"""
        return action_stream.pipe(
            ops.do_action(lambda action: print(f"[Log] Action: {action.type}")),
            ops.filter(lambda _: False)
        )
        
        
    @create_effect(dispatch=False)
    def handle_count_warning(self, action_stream):
        """處理計數器過高的警告"""
        return action_stream.pipe(
            # ops.filter(lambda action: action.type == count_warning.type),
            ofType(count_warning),
            ops.do_action(
                lambda action: print(
                    f"[Warning] 計數器超過閾值! 目前值: {action.payload}"
                )
            ),
            ops.filter(lambda _: False),
        )
