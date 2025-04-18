class BaseMiddleware:
    def on_next(self, action):        pass
    def on_error(self, error, action): pass
    def on_complete(self, result, action): pass

# 例：一个带日志的 middleware
class LoggerMiddleware(BaseMiddleware):
    def on_next(self, action):
        print(f"▶️ dispatching {action.type}")
    def on_complete(self, result, action):
        print(f"✅ state after {action.type}: {action.store.state}")
    def on_error(self, err, action):
        print(f"❌ error in {action.type}: {err}")
