"""
📋 持仓管理页面（P4 开发中）
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import streamlit as st
from web.utils import apply_style


apply_style()
st.title("📋 持仓管理")
st.info("⚙️ 功能开发中（P4 阶段），当前为预览版本。")

st.subheader("持仓列表（示例）")
import pandas as pd
demo = pd.DataFrame([
    {"股票代码": "sh600519", "股票名称": "贵州茅台", "持仓成本": 1680.0, "当前价": 1720.50, "盈亏": "+2.41%", "仓位": "30%"},
    {"股票代码": "sz000063", "股票名称": "中兴通讯", "持仓成本": 28.50, "当前价": 27.80, "盈亏": "-2.46%", "仓位": "20%"},
])
st.dataframe(demo, use_container_width=True, hide_index=True)

st.subheader("止损止盈设置（示例）")
c1, c2, c3 = st.columns(3)
c1.metric("账户总市值", "¥1,023,400")
c2.metric("累计收益", "+2.34%")
c3.metric("持仓数量", "2 只")

st.caption("P4 将实现：持仓增删改查 / 动态更新 / 止损止盈规则引擎 / 飞书推送")
