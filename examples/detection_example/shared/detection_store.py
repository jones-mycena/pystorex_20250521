# from fence import FenceEffects
# from helmet import HelmetEffects
from pystorex import create_store
# from helmet.helmet_reducer import helmet_status_reducer
# from fence.fence_reducer import fence_status_reducer

store = create_store()

# store.register_root({
#     "helmet_status": helmet_status_reducer,
#     "fence_status": fence_status_reducer
# })

# store.register_root([HelmetEffects, FenceEffects])