"""
📈 回测验证页面
运行策略回测 + 收益曲线可视化
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

st.title("📈 回测验证")

# ── 第一行：股票代码 ─────────────────────────────────────────────
code = stock_autocomplete(
    label="股票代码",
    placeholder="输入代码或名称",
    key="backtest_code",
    initial="sh600519",
)

# ── 第二行：日期 / 策略 / 初始资金 ─────────────────────────────────
p_cols = st.columns([1, 1, 1.5, 1.5])
start = p_cols[0].date_input("开始日期", value=date.today() - timedelta(days=365))
end = p_cols[1].date_input("结束日期", value=date.today())
strategy_options = {
    "MACD策略": "MACD",
    "布林带策略": "BOLL",
    "均线策略": "MA",
    "多因子策略": "MULTI",
}
selected_label = p_cols[2].selectbox("选择策略", list(strategy_options.keys()))
strategy_key = strategy_options[selected_label]
initial_cash = p_cols[3].number_input("初始资金（元）", value=200000.0, min_value=10000.0, step=10000.0)

st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
run = st.button("🚀 开始回测", type="primary")

# ── 回测执行 ─────────────────────────────────────────────────────
if run:
    if start >= end:
        st.error("开始日期必须早于结束日期！")
        st.stop()

    with st.spinner(f"正在回测 {code} …"):
        try:
            if strategy_key == "MACD":
                from app.strategy.technical import MACDStrategy
                engine = MACDStrategy()
            elif strategy_key == "BOLL":
                from app.strategy.technical import BollingerBandStrategy
                engine = BollingerBandStrategy()
            elif strategy_key == "MA":
                from app.strategy.technical import MAStrategy
                engine = MAStrategy()
            else:
                from app.strategy.multi_factor import MultiFactorStrategy
                engine = MultiFactorStrategy()

            result = engine.backtest(code, start, end, initial_cash=initial_cash)

        except Exception as e:
            st.exception(e)
            st.stop()

    st.subheader("回测结果")
    r = result
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("总收益率", f"{r['total_return']:.2f}%")
    m2.metric("年化收益", f"{r['annual_return']:.2f}%")
    m3.metric("最大回撤", f"{r['max_drawdown']:.2f}%")
    m4.metric("夏普比率", f"{r['sharpe']:.2f}")
    m5.metric("胜率", f"{r['win_rate']:.2f}%")
    m6.metric("交易次数", f"{len(r['trades'])}")

    st.subheader("收益曲线")
    try:
        import plotly.graph_objects as go

        equity_list = r.get("equity_curve", [])
        if equity_list:
            eq_df = pd.DataFrame(equity_list)
            eq_df["日期"] = pd.to_datetime(eq_df["date"])
            eq_df = eq_df.sort_values("日期")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=eq_df["日期"], y=eq_df["equity"],
                mode="lines", name="账户权益",
                line=dict(color="#1f77b4", width=2),
            ))
            fig.add_hline(y=initial_cash, line_dash="dash", line_color="gray", annotation_text="初始资金")
            fig.update_layout(height=400, xaxis_title="日期", yaxis_title="账户价值（元）", hovermode="x unified")
            st.plotly_chart(fig, width='stretch')
        else:
            st.caption("无权益曲线数据（请确认回测期内有数据）")
    except ImportError:
        st.info("安装 plotly：pip install plotly")
    except Exception as e:
        st.caption(f"收益曲线渲染失败：{e}")

    st.subheader("交易明细")
    if r["trades"]:
        trades_show = pd.DataFrame(r["trades"])
        for col in ["price", "portfolio_value"]:
            if col in trades_show.columns:
                trades_show[col] = trades_show[col].round(2)
        if "return_pct" in trades_show.columns:
            trades_show["return_pct"] = trades_show["return_pct"].round(2)
        st.dataframe(trades_show, width='stretch')
    else:
        st.info("该周期内无交易信号")
else:
    st.info("设置参数后点击「开始回测」")
    st.caption("支持的股票代码格式：sh600519（沪市）/ sz000063（深市）")
