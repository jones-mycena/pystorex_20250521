# test_pystorex_core.py

from pystorex.store import create_store, StoreModule
from pystorex.reducers import create_reducer, on
from pystorex.actions import create_action
from pystorex.store_selectors import create_selector

inc = create_action('increment', lambda x: x)
dec = create_action('decrement', lambda x: x)

counter_reducer = create_reducer(
    0,
    on(inc, lambda state, action: state + action.payload),
    on(dec, lambda state, action: state - action.payload),
)

double_selector = create_selector(lambda s: s, result_fn=lambda x: x * 2)

middleware_calls = []
def spy_middleware(store):
    def _next(next_dispatch):
        def _dispatch(action):
            middleware_calls.append(action.type)
            return next_dispatch(action)
        return _dispatch
    return _next

def test_reducer_middleware_selector():
    store = create_store()
    store.apply_middleware(spy_middleware)
    StoreModule.register_root({'counter': counter_reducer}, store)
    store.init_state()  # ✅ 強制送出一次初始狀態

    results = []
    store.select(lambda state: double_selector(state['counter'])).subscribe(
        lambda tpl: results.append(tpl[1])  # 只記錄 new_value
    )

    store.dispatch(create_action("__INIT__"))  # ✅ 讓 selector 收到初始值
    assert store.state['counter'] == 0
    assert results[-1] == 0  # 這裡抓 new_value

    store.dispatch(inc(5))
    assert store.state['counter'] == 5
    assert results[-1] == 10
    assert 'increment' in middleware_calls  # ✅ 或用 middleware_calls[-1] == 'increment'

    store.dispatch(dec(2))
    assert store.state['counter'] == 3
    assert results[-1] == 6
    assert 'decrement' in middleware_calls

def test_feature_unregister():
    store = create_store()
    StoreModule.register_root({'counter': counter_reducer}, store)
    store.dispatch(inc(1))
    assert store.state['counter'] == 1

    StoreModule.unregister_feature('counter', store)
    prev_state = dict(store.state)

    store.dispatch(inc(1))
    assert 'counter' not in store.state or store.state['counter'] == prev_state.get('counter')
