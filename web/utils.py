"""
Streamlit Web UI - 公共工具函数
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd

# 将项目根目录加入 sys.path，使页面文件能直接 import app
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ── 样式 ──────────────────────────────────────────────────────────

def apply_style():
    """注入自定义 CSS，统一视觉风格（中国A股配色：涨红跌绿）"""
    st.markdown(
        """
        <style>
        /* 涨跌颜色 */
        .metric-up   {color:#ff4b4b; font-weight:700;}
        .metric-down {color:#00b050; font-weight:700;}
        .score-A  {color:#ff4b4b; font-weight:800; font-size:1.2em;}
        .score-B  {color:#ff8c00; font-weight:700;}
        .score-C  {color:#1e90ff;}
        .score-D  {color:#808080;}

        /* 指标卡片通用样式 */
        .metric-card {
            border: 1px solid #e6e6e6 !important;
            border-radius: 12px !important;
            padding: 14px 12px !important;
            text-align: center;
            background: white !important;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
            height: 100%;
            margin: 0 4px 0 0 !important;
            min-width: 0;
        }
        .metric-card .label {
            font-size: 0.78em;
            color: #999;
            margin-bottom: 6px;
        }
        .metric-card .value {
            font-size: 1.6em;
            font-weight: 700;
            margin: 4px 0;
            color: #333;
        }
        .metric-card .delta {
            font-size: 0.95em;
        }

        /* 最新价卡片：涨/跌背景色 */
        .metric-card-price-up {
            border-color: #ffcccc !important;
            background: linear-gradient(135deg, #fff5f5, #fff0f0) !important;
        }
        .metric-card-price-down {
            border-color: #ccefdd !important;
            background: linear-gradient(135deg, #f5fffa, #f0fff4) !important;
        }
        .metric-card-price-up .value,
        .metric-card-price-up .delta { color: #ff4b4b !important; }
        .metric-card-price-down .value,
        .metric-card-price-down .delta { color: #00b050 !important; }

        /* Streamlit 列间距 */
        section[data-testid="stMainBlockContainer"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            padding: 0 8px !important;
        }

        /* 主内容区上边距：给标题留空间 */
        section[data-testid="stMainBlockContainer"] {
            padding-top: 3rem !important;
            padding-bottom: 1rem !important;
        }
        div[data-testid="stMainContainer"] {
            padding-top: 2rem !important;
        }

        /* 去掉 Streamlit 默认的顶部内边距（保留菜单按钮空间） */
        .st-emotion-cache-zy6yx3 {
            padding-top: 2rem !important;
        }

        /* 主内容区全宽（侧边栏收起时） */
        section[data-testid="stMain"] {
            margin-left: 0 !important;
            width: 100% !important;
            max-width: 100% !important;
        }

        /* 隐藏左侧导航栏滚动条 */
        [data-testid="stSidebar"] {
            overflow-y: hidden !important;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            overflow-y: auto !important;
            scrollbar-width: none !important;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"]::-webkit-scrollbar {
            display: none !important;
        }

        /* 美化 checkbox（升序等） */
        [data-testid="stCheckbox"] input[type="checkbox"] {
            accent-color: #ff4b4b;
            width: 16px;
            height: 16px;
            cursor: pointer;
        }
        [data-testid="stCheckbox"] label {
            cursor: pointer;
            font-size: 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ── 数据展示 ──────────────────────────────────────────────────────

def style_pct_series(s: pd.Series, inplace: bool = False) -> pd.Series:
    """
    将小数形式的涨跌幅序列格式化为带颜色的 HTML 字符串，
    用于 st.markdown（不安全HTML）渲染。
    返回新 Series，不修改原数据。
    """
    def _fmt(v):
        if pd.isna(v):
            return ""
        v = float(v)
        cls = "metric-up" if v >= 0 else "metric-down"
        sign = "+" if v >= 0 else ""
        return f'<span class="{cls}">{sign}{v:.2f}%</span>'

    return s.apply(_fmt)


def render_stock_link(code: str, name: str = "") -> str:
    """生成可点击的股票链接（跳转到东方财富）"""
    label = name or code
    market = "sh" if code.startswith("6") else "sz"
    url = f"https://quote.eastmoney.com/{market}{code[-6:]}.html"
    return f"[🔗 {label}]({url})"


# ── 错误兜底 ─────────────────────────────────────────────────────

def safe_run(func, *args, **kwargs):
    """
    包装数据获取函数，捕获异常并以 streamlit 方式报错，
    返回 (success: bool, data: any)
    """
    try:
        return True, func(*args, **kwargs)
    except Exception as e:
        st.error(f"数据获取失败：{e}")
        return False, None
