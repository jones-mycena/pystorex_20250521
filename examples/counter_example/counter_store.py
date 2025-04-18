from pystorex import create_store, StoreModule, EffectsModule
from .counter_reducers import counter_reducer
from .counter_effects import CounterEffects

# 創建Store
store = create_store()

# 註冊Reducer
store = StoreModule.register_root({"counter": counter_reducer}, store)

# 註冊Effects
store = EffectsModule.register_root(CounterEffects, store)
