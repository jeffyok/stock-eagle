"""
StockEagle Streamlit Web UI - 主入口（P3）
使用 st.navigation 实现多页面导航
"""
import sys
from pathlib import Path

# ── 关键：将项目根目录加入 sys.path（必须最优先！）───────────────
# 防止 web/app.py 被误认为 app 包，遮住根目录下的 app/ 包
ROOT = Path(__file__).parent.parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="StockEagle 🦅",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 侧边栏顶部：纯文字 logo（不用图片，绝对左对齐）────────────
st.sidebar.markdown(
    """<div style="text-align:left;padding:10px 0 6px 0;">
  <div style="font-size:28px;font-weight:bold;color:#FFA500;line-height:1.3;">StockEagle 🦅</div>
  <div style="font-size:16px;color:#BBBBBB;line-height:1.4;margin-top:2px;">猎鹰智能选股选基系统</div>
</div>""",
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    "<hr style='margin:4px 0;'>"
    "<div style='font-size:0.65rem;color:#aaa;line-height:1.2;margin:0;'>"
    "⚠️ 免责声明：仅供学习研究，不构成投资建议。"
    "</div>",
    unsafe_allow_html=True,
)

# ── 页面注册（st.navigation，Streamlit 1.18+）──────────────
pg = st.navigation([
    st.Page("pages/page_realtime.py",    title="📊 实时行情"),
    st.Page("pages/page_strategy.py",    title="🎯 策略选股"),
    st.Page("pages/page_intelligence.py",title="🧠 智能推荐"),
    st.Page("pages/page_sector.py",      title="🔥 风口追踪"),
    st.Page("pages/page_fund.py",         title="💰 基金筛选"),
    st.Page("pages/page_backtest.py",    title="📈 回测验证"),
    st.Page("pages/page_portfolio.py",   title="📋 持仓管理"),
    st.Page("pages/page_risk.py",        title="🛡️ 风控管理"),
    st.Page("pages/page_notify.py",      title="📢 推送管理"),
    st.Page("pages/page_review.py",       title="📰 每日复盘"),
])

pg.run()
