from pystorex import create_selector

# 定義Selectors
get_counter_state = lambda state: state["counter"]
get_count = create_selector(
    get_counter_state, result_fn=lambda counter: counter.count or 0
)
get_loading = create_selector(
    get_counter_state, result_fn=lambda counter: counter.loading or False
)
get_error = create_selector(
    get_counter_state, result_fn=lambda counter: counter.error or None
)
get_last_updated = create_selector(
    get_counter_state, result_fn=lambda counter: counter.last_updated or None
)
# 创建一个复合选择器
get_counter_info = create_selector(
    get_count,
    get_last_updated,
    result_fn=lambda count, last_updated: {"count": count, "last_updated": last_updated},
)
