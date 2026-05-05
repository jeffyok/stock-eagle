"""
🧠 智能推荐页面
AI综合评分 + 龙虎榜解读
"""
import sys
from pathlib import Path
# web/pages/xxx.py → web/ → stock-eagle/（项目根）
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from web.utils import apply_style
from web.components.stock_autocomplete import stock_autocomplete

apply_style()

st.title("🧠 智能推荐")

tab1, tab2, tab3 = st.tabs(["AI综合评分", "龙虎榜解读", "综合报告"])

# ── Tab1：AI综合评分 ─────────────────────────────────────────
with tab1:
    st.subheader("AI 综合评分（4因子模型）")
    st.caption("基本面 30% ＋ 技术面 30% ＋ 资金面 25% ＋ 舆情 15%")

    code_score = stock_autocomplete(
        label="股票代码",
        placeholder="输入代码或名称，如 贵州茅台",
        key="score_code",
        initial="sh600519",
    )
    run_score = st.button("开始评分", key="btn_score", type="primary")

    if run_score and code_score:
        with st.spinner("正在计算综合评分…"):
            try:
                from app.intelligence.scorer import StockScorer
                scorer = StockScorer()
                result = scorer.score(code_score.strip().lower())
            except Exception as e:
                st.exception(e)
                st.stop()

        # 总评分大字展示
        score = result.get("total_score", 0)
        rec = result.get("recommendation", "N/A")
        score_color = (
            "#ff4b4b" if score >= 80 else
            "#ff8c00" if score >= 60 else
            "#1e90ff" if score >= 40 else "#808080"
        )
        st.markdown(
            f"<h1 style='color:{score_color}; text-align:center;'>"
            f"{score:.0f} 分</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='text-align:center; font-size:1.2em;'>"
            f"推荐：<strong>{rec}</strong></p>",
            unsafe_allow_html=True,
        )

        # 分项分数
        st.subheader("分项评分")
        subs = result.get("sub_scores", {})
        col_data = st.columns(4)
        labels = ["基本面", "技术面", "资金面", "舆情"]
        keys = ["fundamental", "technical", "money", "sentiment"]
        for col, label, key in zip(col_data, labels, keys):
            val = subs.get(key, 0)
            col.metric(label, f"{val:.0f}" if isinstance(val, (int, float)) else val)

        # 详细数据
        with st.expander("详细数据"):
            detail = result.get("detail", {})
            if isinstance(detail, dict):
                for k, v in detail.items():
                    st.write(f"**{k}**：{v}")
            else:
                st.write(detail)

    elif run_score:
        st.warning("请输入股票代码")

# ── Tab2：龙虎榜解读 ────────────────────────────────────────
with tab2:
    st.subheader("龙虎榜解读")
    st.caption("识别游资席位、分析散户行为、发现异动股票")

    lhb_date = st.date_input("选择日期", value=pd.Timestamp.today().date(), key="lhb_date")
    run_lhb = st.button("获取龙虎榜数据", key="btn_lhb", type="primary")

    if run_lhb:
        date_str = lhb_date.strftime("%Y%m%d")
        with st.spinner(f"正在获取 {date_str} 龙虎榜数据…"):
            try:
                from app.intelligence.dragon_tiger import DragonTigerAnalyzer
                analyzer = DragonTigerAnalyzer()
                summary = analyzer.get_lhb_summary(date_str)
            except Exception as e:
                st.exception(e)
                st.stop()

        if not summary:
            st.info(f"{date_str} 无龙虎榜数据（可能是节假日或非交易日）")
        else:
            # 异动汇总
            st.subheader("异动汇总")
            c1, c2, c3 = st.columns(3)
            c1.metric("上榜股票数", summary.get("total_stocks", 0))
            c2.metric("涨停家数", summary.get("up_limit", 0))
            c3.metric("跌停家数", summary.get("down_limit", 0))

            # 上榜股票明细
            st.subheader("上榜股票明细")
            stocks = summary.get("stocks", [])
            if stocks:
                df_stocks = pd.DataFrame(stocks)
                st.dataframe(df_stocks, width='stretch', hide_index=True)
            else:
                st.caption("无明细数据")

            # 游资席位（如果有）
            st.subheader("活跃游资席位 Top 10")
            try:
                hot_seats = analyzer.identify_hot_seats(date_str, top_n=10)
                if hot_seats:
                    df_seats = pd.DataFrame(hot_seats)
                    st.dataframe(df_seats, width='stretch', hide_index=True)
                else:
                    st.caption("未发现活跃游资席位")
            except Exception as e:
                st.caption(f"游资席位分析失败：{e}")

# ── Tab3：综合报告 ───────────────────────────────────────────
with tab3:
    st.subheader("AI 智能推荐综合报告")
    st.caption("综合评分 + 龙虎榜 + 板块异动 + 资金流向")

    run_report = st.button("生成综合报告", key="btn_report", type="primary")
    if run_report:
        with st.spinner("正在生成综合报告…"):
            try:
                from app.intelligence.scorer import StockScorer
                from app.intelligence.dragon_tiger import DragonTigerAnalyzer
                from app.tracker.sector_monitor import SectorMonitor
                from app.tracker.money_monitor import MoneyMonitor

                scorer = StockScorer()
                analyzer = DragonTigerAnalyzer()
                sector_m = SectorMonitor()
                money_m = MoneyMonitor()

                # 综合评分 Top20
                st.subheader("综合评分 Top 20")
                top20 = scorer.rank_by_financial(top_n=20)
                if top20:
                    df_top = pd.DataFrame(top20)
                    st.dataframe(df_top, width='stretch', hide_index=True)
                else:
                    st.caption("暂无评分数据")

                # 龙虎榜简报
                st.subheader("近期龙虎榜异动")
                recent = analyzer.get_recent_lhb(days=7, top_n=20)
                if recent:
                    df_recent = pd.DataFrame(recent)
                    st.dataframe(df_recent, width='stretch', hide_index=True)
                else:
                    st.caption("近7日无龙虎榜数据")

                # 板块异动
                st.subheader("今日板块异动")
                sector_report = sector_m.get_report()
                if sector_report.get("rising_sectors"):
                    df_rise = pd.DataFrame(sector_report["rising_sectors"])
                    st.dataframe(df_rise, width='stretch', hide_index=True)
                else:
                    st.caption("暂无板块异动")

            except Exception as e:
                st.exception(e)

if not any([run_score, run_lhb, run_report]):
    st.info("选择上方标签页，输入参数后点击按钮开始分析")
