from pystorex import create_action

# 定義Actions

increment = create_action("increment")
decrement = create_action("decrement")
reset = create_action("reset", lambda value: value)
increment_by = create_action("incrementBy", lambda amount: amount)


load_count_request = create_action("loadCountRequest")
load_count_success = create_action("loadCountSuccess")
load_count_failure = create_action("loadCountFailure")
