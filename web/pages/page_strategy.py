"""
🎯 策略选股页面
多因子 / 技术策略 信号生成 + 结果展示
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from web.utils import apply_style
from web.components.stock_autocomplete import stock_autocomplete

apply_style()

st.title("🎯 策略选股")

strategy_options = {
    "多因子策略（综合评分）": "MULTI",
    "MACD金叉策略": "MACD",
    "布林带突破策略": "BOLL",
    "均线多头策略": "MA",
}

# ── 第一行：策略选择 ──────────────────────────────────────────
p_cols1 = st.columns([2, 2, 1, 1])
selected_label = p_cols1[0].selectbox("选择策略", list(strategy_options.keys()))
strategy_key = strategy_options[selected_label]
start = p_cols1[2].date_input("开始日期", value=date.today() - timedelta(days=365))
end = p_cols1[3].date_input("结束日期", value=date.today())

# ── 第二行：股票代码 ────────────────────────────────────────
code = stock_autocomplete(
    label="股票代码",
    placeholder="输入代码或名称",
    key="strat_code",
    initial="sh600519",
)

# ── 第三行：操作按钮 ────────────────────────────────────────
c_btn, _ = st.columns([1, 4])
c_sig, gap, c_back = c_btn.columns([10, 8, 10])
run_signal = c_sig.button("📡 生成信号", type="primary")
run_backtest = c_back.button("📈 执行回测")

# 防止按钮文字换行
st.markdown("""
<style>
div[data-testid="stButton"] > button {
    white-space: nowrap !important;
    min-width: fit-content !important;
}
</style>
""", unsafe_allow_html=True)

# ── 信号生成 ───────────────────────────────────────────────────
if run_signal:
    with st.spinner("正在生成信号…"):
        try:
            if strategy_key == "MULTI":
                from app.strategy.multi_factor import MultiFactorStrategy
                engine = MultiFactorStrategy()
            elif strategy_key == "MACD":
                from app.strategy.technical import MACDStrategy
                engine = MACDStrategy()
            elif strategy_key == "BOLL":
                from app.strategy.technical import BollingerBandStrategy
                engine = BollingerBandStrategy()
            else:
                from app.strategy.technical import MAStrategy
                engine = MAStrategy()
            signals = engine.generate_signals(code, start, end)
        except Exception as e:
            st.exception(e)
            st.stop()

    st.subheader(f"交易信号（{selected_label}）")
    if signals:
        df_sig = pd.DataFrame(signals)
        df_show = df_sig.copy()
        if "price" in df_show.columns:
            df_show["price"] = df_show["price"].round(2)
        if "score" in df_show.columns:
            df_show["score"] = df_show["score"].round(2)

        def color_direction(val):
            if val == "buy":
                return "color:#ff4b4b; font-weight:700;"
            elif val == "sell":
                return "color:#00b050; font-weight:700;"
            return ""

        style = df_show.style
        if "direction" in df_show.columns:
            style = style.map(color_direction, subset=pd.IndexSlice[:, ["direction"]])
        st.dataframe(style, use_container_width=True, hide_index=True)

        c1, c2, c3 = st.columns(3)
        buy_count = sum(1 for s in signals if s.get("direction") == "buy")
        sell_count = sum(1 for s in signals if s.get("direction") == "sell")
        c1.metric("买入信号", buy_count)
        c2.metric("卖出信号", sell_count)
        c3.metric("总信号数", len(signals))
    else:
        st.info("该周期内无交易信号")

# ── 回测 ───────────────────────────────────────────────────────
if run_backtest:
    with st.spinner("正在回测…"):
        try:
            if strategy_key == "MULTI":
                from app.strategy.multi_factor import MultiFactorStrategy
                engine = MultiFactorStrategy()
            elif strategy_key == "MACD":
                from app.strategy.technical import MACDStrategy
                engine = MACDStrategy()
            elif strategy_key == "BOLL":
                from app.strategy.technical import BollingerBandStrategy
                engine = BollingerBandStrategy()
            else:
                from app.strategy.technical import MAStrategy
                engine = MAStrategy()
            result = engine.backtest(code, start, end, initial_cash=100000.0)
        except Exception as e:
            st.exception(e)
            st.stop()

    st.subheader("回测结果")
    r = result
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("总收益率", f"{r['total_return']:.2f}%")
    m2.metric("年化收益", f"{r['annual_return']:.2f}%")
    m3.metric("最大回撤", f"{r['max_drawdown']:.2f}%")
    m4.metric("夏普比率", f"{r['sharpe']:.2f}")
    m5.metric("胜率", f"{r['win_rate']:.2f}%")

    with st.expander("交易明细"):
        trades_df = pd.DataFrame(r["trades"])
        if not trades_df.empty:
            st.dataframe(trades_df, use_container_width=True, hide_index=True)
        else:
            st.caption("无交易记录")

if not run_signal and not run_backtest:
    st.info("设置参数后点击「生成信号」或「执行回测」")
