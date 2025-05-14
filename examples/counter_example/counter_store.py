from pystorex import create_store, StoreModule, EffectsModule
from counter_reducers import counter_reducer
from counter_effects import CounterEffects
from pystorex.middleware import LoggerMiddleware

# 創建Store
store = create_store()

store.apply_middleware(LoggerMiddleware)
# 註冊Reducer
store = StoreModule.register_root({"counter": counter_reducer}, store)

# 註冊Effects
store = EffectsModule.register_root(CounterEffects, store)
