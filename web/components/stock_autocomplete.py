"""
股票代码 autocomplete 组件
st.text_input + 搜索结果列表：输入 → 实时搜索 → 点击确认选择
"""
import streamlit as st

# 预加载股票列表（全局缓存，只加载一次）
_stock_list: list[dict] = []


def _ensure_loaded():
    global _stock_list
    if not _stock_list:
        try:
            from app.data.stock_search import get_stock_list
            _stock_list = get_stock_list()
        except Exception:
            _stock_list = []


def _search_stocks(query: str, top_n: int = 15) -> list[dict]:
    """模糊搜索股票"""
    _ensure_loaded()
    q = query.strip().lower()
    if not q:
        return []

    exact_code = [s for s in _stock_list if s["code"].lower() == q]
    code_prefix = [s for s in _stock_list
                   if s["code"][2:].lower().startswith(q) and s not in exact_code]
    name_hit = [s for s in _stock_list
                if q in s["name"].lower() and s not in exact_code and s not in code_prefix]

    seen = set()
    result = []
    for s in exact_code + code_prefix + name_hit:
        key = s["code"]
        if key not in seen:
            seen.add(key)
            result.append(s)
            if len(result) >= top_n:
                break
    return result


def stock_autocomplete(
    label: str = "股票代码",
    placeholder: str = "输入代码或名称，如 贵州茅台",
    key: str = "stock_code",
    initial: str = "sh600519",
    help_text: str = "支持代码（600519）或名称（贵州茅台）模糊搜索",
) -> str:
    """
    股票代码联想输入框。
    输入 → 实时显示搜索结果列表 → 点击按钮确认选择 → 返回带前缀的代码（如 sh600519）

    Returns:
        str: 选中的股票代码，如 "sh600519"
    """
    # 初始化 session_state
    if key not in st.session_state:
        st.session_state[key] = initial
        st.session_state[f"{key}_input"] = initial

    # 文本输入框：显示「代码 名字」格式（有点击选择时更新）
    raw = st.text_input(
        label,
        value=st.session_state.get(f"{key}_input", ""),
        placeholder=placeholder,
        help=help_text,
        label_visibility="collapsed",
        key=f"{key}_text_input",
    )
    st.session_state[f"{key}_input"] = raw

    # 实时搜索
    results = _search_stocks(raw)

    if results:
        # 用户已输入但未选择 → 显示联想结果
        st.caption(f"🔍 找到 {len(results)} 条结果，点击选择：")
        cols = st.columns(min(len(results), 3))
        for i, stock in enumerate(results[:min(len(results), 12)]):
            col = cols[i % len(cols)]
            label_text = f"{stock['code']} {stock['name']}（{stock['market']}）"
            if col.button(label_text, key=f"{key}_btn_{stock['code']}"):
                chosen_code = stock["code"]
                chosen_name = stock["name"]
                st.session_state[key] = chosen_code
                # 输入框直接显示「代码 名字」
                st.session_state[f"{key}_input"] = f"{chosen_code} {chosen_name}"
                st.rerun()

    elif raw and len(raw) >= 2:
        st.warning(f"⚠️ 未找到「{raw}」")

    return st.session_state.get(key, initial)
