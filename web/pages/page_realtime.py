"""
📊 实时行情页面
K线图 + 实时价格 + 资金流向
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

st.title("📊 实时行情看板")

# ── 股票代码联想输入 ─────────────────────────────────────────────
code = stock_autocomplete(
    label="股票代码",
    placeholder="输入代码或名称，如 贵州茅台 / 600519",
    key="realtime_code",
    initial="sh600519",
)

# ── 数据获取 ─────────────────────────────────────────────────────
if code:
    try:
        from app.data.akshare_source import AKShareSource
        src = AKShareSource()

        end = date.today()
        start = end - timedelta(days=180)

        with st.spinner("获取行情数据…"):
            records = src.get_stock_daily(code, start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))

        if not records:
            st.warning("未获取到数据，请检查股票代码是否正确。")
            st.stop()

        df = pd.DataFrame(records)
        rename_map = {
            "date": "日期",
            "open": "开盘",
            "close": "收盘",
            "high": "最高",
            "low": "最低",
            "volume": "成交量",
            "amount": "成交额",
            "pct_chg": "涨跌幅",
            "turnover": "换手率",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        df["日期"] = pd.to_datetime(df["日期"])

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else latest

        # ── 关键指标卡片（涨跌颜色：涨红跌绿，CSS 美化）─────────────
        st.subheader(f"{latest.get('name', '')}（{code}）")

        price = float(latest.get("收盘", latest.get("close", 0)))
        pre_close = float(prev.get("收盘", prev.get("close", price)))
        chg = (price - pre_close) / pre_close * 100 if pre_close else 0
        vol = float(latest.get("成交量", latest.get("volume", 0))) / 1e8
        amt = float(latest.get("成交额", latest.get("amount", 0))) / 1e8
        turn = float(latest.get("换手率", latest.get("turnover", 0)))
        ma5 = df["收盘"].astype(float).tail(5).mean()
        ma20 = df["收盘"].astype(float).tail(20).mean()

        chg_color = "#ff4b4b" if chg >= 0 else "#00b050"
        chg_icon = "▲" if chg >= 0 else "▼"
        price_card_class = "metric-card metric-card-price-up" if chg >= 0 else "metric-card metric-card-price-down"

        def card(label, value_html, delta_html="", extra_class=""):
            """用 CSS class 渲染指标卡片，确保所有列完全对齐"""
            delta_part = f"<div class='delta'>{delta_html}</div>" if delta_html else ""
            cls = f"metric-card {extra_class}".strip()
            return (
                f"<div class='{cls}'>"
                f"<div class='label'>{label}</div>"
                f"<div class='value'>{value_html}</div>"
                f"{delta_part}"
                f"</div>"
            )

        # 第一行：价格 + 开/高/低/量
        r1 = st.columns([1.2, 1, 1, 1, 1.2])
        r1[0].markdown(
            card("最新价",
                  f"<span style='color:{chg_color}'>{price:.2f}</span>",
                  f"<span style='color:{chg_color}'>{chg_icon} {chg:+.2f}%</span>",
                  price_card_class),
            unsafe_allow_html=True)
        r1[1].markdown(card("今开", f"{latest.get('开盘', latest.get('open', 0)):.2f}"), unsafe_allow_html=True)
        r1[2].markdown(card("最高", f"{latest.get('最高', latest.get('high', 0)):.2f}"), unsafe_allow_html=True)
        r1[3].markdown(card("最低", f"{latest.get('最低', latest.get('low', 0)):.2f}"), unsafe_allow_html=True)
        r1[4].markdown(card("成交量", f"{vol:.2f}亿手"), unsafe_allow_html=True)

        # 第二行：成交/换手/昨收/MA
        r2 = st.columns(5)
        r2[0].markdown(card("成交额", f"{amt:.2f}亿元"), unsafe_allow_html=True)
        r2[1].markdown(card("换手率", f"{turn:.2f}%"), unsafe_allow_html=True)
        r2[2].markdown(card("昨收", f"{pre_close:.2f}"), unsafe_allow_html=True)
        r2[3].markdown(card("MA5", f"{ma5:.2f}"), unsafe_allow_html=True)
        r2[4].markdown(card("MA20", f"{ma20:.2f}"), unsafe_allow_html=True)

        # ── K线图（plotly） ───────────────────────────────────────
        st.subheader("K线走势")
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots

            df_plot = df.copy().sort_values("日期")

            fig = make_subplots(
                rows=2, cols=1,
                row_heights=[0.75, 0.25],
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=("K线", "成交量"),
            )

            fig.add_trace(
                go.Candlestick(
                    x=df_plot["日期"],
                    open=df_plot["开盘"].astype(float),
                    high=df_plot["最高"].astype(float),
                    low=df_plot["最低"].astype(float),
                    close=df_plot["收盘"].astype(float),
                    name="K线",
                    increasing_line_color="#ff4b4b",
                    decreasing_line_color="#00b050",
                ),
                row=1, col=1,
            )

            for period, color in [(5, "orange"), (20, "cyan"), (60, "magenta")]:
                if len(df_plot) >= period:
                    ma = df_plot["收盘"].astype(float).rolling(period).mean()
                    fig.add_trace(
                        go.Scatter(x=df_plot["日期"], y=ma, name=f"MA{period}",
                                   line=dict(color=color, width=1)),
                        row=1, col=1,
                    )

            colors = ["#ff4b4b" if c >= o else "#00b050"
                       for c, o in zip(df_plot["收盘"].astype(float),
                                       df_plot["开盘"].astype(float))]
            fig.add_trace(
                go.Bar(x=df_plot["日期"], y=df_plot["成交量"].astype(float),
                        name="成交量", marker_color=colors, showlegend=False),
                row=2, col=1,
            )

            fig.update_layout(
                height=600,
                xaxis_rangeslider_visible=False,
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            fig.update_yaxes(title_text="价格（元）", row=1, col=1)
            fig.update_yaxes(title_text="成交量", row=2, col=1)

            st.plotly_chart(fig, use_container_width=True)

        except ImportError:
            st.info("安装 plotly 可显示交互式 K线图：pip install plotly")

        # ── 资金流向（使用 westock-data，速度更快）────────────────────
        st.subheader("资金流向")
        mf = None
        try:
            import subprocess
            result = subprocess.run(
                ["npx", "--yes", "westock-data-skillhub@latest", "asfund", code],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                lines = [l for l in result.stdout.strip().split("\n") if l.startswith("|")]
                if len(lines) >= 2:
                    headers = [h.strip() for h in lines[0].strip("|").split("|")]
                    data_line = lines[1].strip("|").split("|")
                    data_dict = dict(zip(headers, data_line))
                    mf = {
                        "net_mf": float(data_dict.get("MainNetFlow", data_dict.get(" MainNetFlow", 0)).strip() or 0),
                        "net_mf_big": float(data_dict.get("JumboNetFlow", data_dict.get(" JumboNetFlow", 0)).strip() or 0),
                        "net_mf_small": float(data_dict.get("SmallNetFlow", data_dict.get(" SmallNetFlow", 0)).strip() or 0),
                    }
        except Exception:
            pass

        if mf is None:
            try:
                mf = src.get_money_flow(code)
            except Exception:
                pass

        if mf and mf.get("net_mf"):
            c_mf1, c_mf2, c_mf3 = st.columns(3)
            c_mf1.metric("主力净流入", f"{mf.get('net_mf', 0) / 1e8:+.2f} 亿")
            c_mf2.metric("超大单净流入", f"{mf.get('net_mf_big', 0) / 1e8:+.2f} 亿")
            c_mf3.metric("小单净流入", f"{mf.get('net_mf_small', 0) / 1e8:+.2f} 亿")
            color = "#ff4b4b" if mf.get('net_mf', 0) >= 0 else "#00b050"
            st.markdown(f"主力资金整体方向：<span style='color:{color}'>{'净流入 ▲' if mf.get('net_mf', 0) >= 0 else '净流出 ▼'}</span>", unsafe_allow_html=True)
        else:
            st.caption("暂无资金流向数据（需在交易时间内获取）")

        # ── 近期数据表 ────────────────────────────────────────────
        with st.expander("近期日线数据（最近20条）"):
            show_cols = [c for c in df.columns if c in ["日期","开盘","最高","最低","收盘","成交量","成交额","换手率"]]
            st.dataframe(df[show_cols].tail(20), use_container_width=True)

    except Exception as e:
        st.exception(e)
else:
    st.info("请输入股票代码，例如 `sh600519`（贵州茅台）或 `sz000063`（中兴通讯）")
