"""
💰 基金筛选页面
多维度筛选公募基金 + 净值历史展示
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from web.utils import apply_style

apply_style()

st.title("💰 基金筛选器")

# ── 第一行：基本筛选条件 ──────────────────────────────
p_cols = st.columns([1.2, 1, 1.2])
fund_type = p_cols[0].selectbox("基金类型", ["股票型", "混合型"])
top_n = p_cols[1].number_input("返回数量", min_value=1, max_value=100, value=20)
min_1y = p_cols[2].number_input("近1年收益下限（%）", value=0.0, step=5.0)

# ── 第二行：排序 + 高级筛选 ─────────────────────────────
s_cols = st.columns([1.5, 1, 2])
sort_by = s_cols[0].selectbox("排序字段", ["return_1y", "return_3y", "return_ytd", "nav"])
ascending = s_cols[1].checkbox("升序")

with s_cols[2].expander("高级筛选"):
    name_kw = st.text_input("基金名称含", value="", help="留空表示不筛选")
    min_3y = st.number_input("近3年收益下限（%）", value=None, step=10.0)

st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
run_filter = st.button("🔍 开始筛选", type="primary")

# ── 执行筛选 ─────────────────────────────────────────────────────
if run_filter:
    with st.spinner("正在筛选基金，请稍候…（首次运行需下载数据）"):
        try:
            from app.strategy.fund_screener import FundScreener
            screener = FundScreener()

            if name_kw or min_3y is not None:
                min_return = {}
                if min_1y is not None:
                    min_return["return_1y"] = min_1y
                if min_3y is not None:
                    min_return["return_3y"] = min_3y
                results = screener.screen(
                    name_keyword=name_kw if name_kw else None,
                    min_return=min_return if min_return else None,
                    sort_by=sort_by,
                    ascending=ascending,
                    top_n=top_n,
                )
            else:
                if fund_type == "股票型":
                    results = screener.top_stock_funds(top_n=top_n, min_1y_return=min_1y)
                else:
                    results = screener.top_mixed_funds(top_n=top_n, min_1y_return=min_1y)

        except Exception as e:
            st.exception(e)
            st.stop()

    st.subheader(f"筛选结果（{fund_type}基金）")
    if not results:
        st.warning("未找到符合条件的基金，请降低筛选条件后重试。")
    else:
        st.success(f"共找到 {len(results)} 只符合条件的基金")
        df = pd.DataFrame(results)
        for col in ["return_1y", "return_3y", "return_ytd"]:
            if col in df.columns:
                df[col] = df[col].round(2) if df[col].dtype == "float64" else df[col]
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.subheader("查看净值历史")
        selected_code = st.selectbox(
            "选择基金",
            [r["code"] for r in results],
            format_func=lambda x: f"{x} - {[r['name'] for r in results if r['code']==x][0]}"
        )
        if selected_code and st.button("查看净值走势", key="btn_nav"):
            with st.spinner("获取净值历史…"):
                nav_history = screener.get_fund_nav_history(selected_code, years=1)
            if nav_history:
                df_nav = pd.DataFrame(nav_history)
                df_nav["日期"] = pd.to_datetime(df_nav["date"])
                df_nav["净值"] = df_nav["nav"].astype(float)
                try:
                    import plotly.graph_objects as go
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df_nav["日期"], y=df_nav["净值"],
                        mode="lines", name="单位净值",
                        line=dict(color="#1f77b4", width=2),
                    ))
                    fig.update_layout(
                        title=f"{[r['name'] for r in results if r['code']==selected_code][0]} 净值走势",
                        height=400, xaxis_title="日期", yaxis_title="净值（元）",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except ImportError:
                    st.line_chart(df_nav.set_index("日期")["净值"])
                with st.expander("净值历史数据（最近20条）"):
                    st.dataframe(df_nav.tail(20), use_container_width=True, hide_index=True)
            else:
                st.warning("未获取到净值历史数据")
else:
    st.info("设置筛选条件后点击「开始筛选」")
    st.caption("💡 股票型基金筛选基于近1年收益排名，数据来源于 AKShare")
