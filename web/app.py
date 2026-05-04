"""
StockEagle Streamlit Web UI 主入口
"""
import streamlit as st

st.set_page_config(
    page_title="StockEagle 🦅",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 侧边栏导航
st.sidebar.title("StockEagle 🦅")
st.sidebar.caption("量化智能选股选基系统")

page = st.sidebar.radio(
    "选择页面",
    [
        "📊 实时行情",
        "🎯 策略选股",
        "🧠 智能推荐",
        "🔥 风口追踪",
        "💰 基金筛选",
        "📋 持仓管理",
        "📉 回测验证",
        "📰 每日复盘",
    ],
)

st.sidebar.markdown("---")
st.sidebar.caption(f"版本: 1.0.0  |  数据更新: 待接入")

# 页面路由
if page == "📊 实时行情":
    st.title("📊 实时行情看板")
    st.info("功能开发中，敬请期待...")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("上证指数", "3,245.67", "1.23%")
    with col2:
        st.metric("深证成指", "10,876.23", "-0.45%")
    with col3:
        st.metric("创业板指", "2,187.90", "2.11%")
    with col4:
        st.metric("上涨家数", "2,567", "")

    st.subheader("热门板块涨幅 Top 10")
    st.caption("功能开发中...")

elif page == "🎯 策略选股":
    st.title("🎯 策略选股")
    st.info("功能开发中，敬请期待...")

    strategy = st.selectbox(
        "选择策略",
        ["多因子选股", "MACD金叉", "突破策略", "均线多头"],
    )
    st.caption(f"已选择: {strategy}")

elif page == "🧠 智能推荐":
    st.title("🧠 智能推荐")
    st.info("功能开发中，敬请期待...")

elif page == "🔥 风口追踪":
    st.title("🔥 风口追踪")
    st.info("功能开发中，敬请期待...")

elif page == "💰 基金筛选":
    st.title("💰 基金筛选")
    st.info("功能开发中，敬请期待...")

elif page == "📋 持仓管理":
    st.title("📋 持仓管理")
    st.info("功能开发中，敬请期待...")

elif page == "📉 回测验证":
    st.title("📉 回测验证")
    st.info("功能开发中，敬请期待...")

elif page == "📰 每日复盘":
    st.title("📰 每日复盘")
    st.info("功能开发中，敬请期待...")

# 页脚
st.markdown("---")
st.caption("⚠️ 免责声明：本系统仅供学习研究，不构成投资建议。投资有风险，入市需谨慎。")
