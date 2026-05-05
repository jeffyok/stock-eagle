"""
📰 每日复盘页面（P4 开发中）
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import streamlit as st
from web.utils import apply_style


apply_style()
st.title("📰 每日复盘")
st.info("⚙️ 功能开发中（P4 阶段），当前为预览版本。")

from datetime import date
import pandas as pd

st.subheader("今日市场概览")
c1, c2, c3, c4 = st.columns(4)
c1.metric("上证指数", "3,245.67", "+1.23%")
c2.metric("深证成指", "10,876.23", "-0.45%")
c3.metric("创业板指", "2,187.90", "+2.11%")
c4.metric("上涨家数", "2,567")

st.subheader("今日策略信号")
sig_demo = pd.DataFrame([
    {"时间": "09:35", "股票": "sh600519", "信号": "BUY", "策略": "MACD金叉", "价格": 1702.00},
    {"时间": "10:12", "股票": "sz000063", "信号": "SELL", "策略": "布林带突破", "价格": 28.30},
])
st.dataframe(sig_demo, width='stretch', hide_index=True)

st.subheader("龙虎榜异动（今日）")
st.caption("今日共 12 只股票登上龙虎榜，其中涨停 8 只、跌停 1 只")

st.subheader("板块异动 Top 5")
sector_demo = pd.DataFrame([
    {"板块": "人工智能", "涨跌幅": "+5.23%", "领涨股": "寒武纪"},
    {"板块": "新能源车", "涨跌幅": "+3.89%", "领涨股": "宁德时代"},
])
st.dataframe(sector_demo, width='stretch', hide_index=True)

if st.button("📲 推送今日复盘到飞书", type="primary"):
    st.success("推送成功！（演示）")

st.caption("P4 将实现：自动生成复盘报告 / 飞书推送 / 历史复盘查看")
