# shared/effects_utils.py
from reactivex import operators as ops, compose
from pystorex.rx_operators import ofType
from shared.detection_store import store
from shared.detection_actions import visual_recognition

def make_log_effect(selector, action_creator):
    """
    返回一个复合 operator，执行：
      filter visualRecognition ->
      map to store.state ->
      map selector ->
      distinct(len) ->
      filter non‑empty ->
      map to action_creator
    """
    return compose(
        # 1. 只处理 visualRecognition
        # ops.filter(lambda action: action.type == visual_recognition.type),
        ofType(visual_recognition),
        # 2. 拿最新 state
        ops.map(lambda _: store.state),
        # 3. 过滤／转成「集合」
        ops.map(selector),
        # 4. 只在 len 变化时才往下走
        ops.distinct_until_changed(lambda items: len(items)),
        # 5. 非空才继续
        ops.filter(lambda items: len(items) > 0),
        # 6. map 到最终要 dispatch 的 action
        ops.map(action_creator)
    )
