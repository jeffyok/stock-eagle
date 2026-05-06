"""
🔥 风口追踪页面
板块异动 + 资金流向 + 热搜监控
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

st.title("🔥 风口追踪")

tab1, tab2, tab3, tab4 = st.tabs(["板块异动", "资金流向", "热搜监控", "综合报告"])

# ── Tab1：板块异动 ─────────────────────────────────────────
with tab1:
    st.subheader("板块异动监控")
    st.caption("行业/概念板块实时涨跌幅 + 异动预警")

    col1, col2 = st.columns([1, 3])
    with col1:
        sector_type = st.selectbox("板块类型", ["industry", "concept"], format_func=lambda x: "行业板块" if x=="industry" else "概念板块")
        min_pct = st.number_input("异动阈值（%）", value=3.0, step=0.5)
        run_sector = st.button("刷新板块数据", key="btn_sector", type="primary")

    with col2:
        if run_sector or "sector_data" not in st.session_state:
            st.session_state["sector_data"] = None  # 重置状态
            with st.spinner("获取板块数据（首次约 10s，已缓存则秒开）…"):
                try:
                    from app.tracker.sector_monitor import SectorMonitor
                    m = SectorMonitor()

                    if sector_type == "industry":
                        all_data = m.get_industry_sectors()
                    else:
                        all_data = m.get_concept_sectors()

                    # 异动筛选（detect_rising 只支持行业板块，手动兼容概念板块）
                    all_data_filtered = all_data
                    rising = [
                        s for s in all_data_filtered
                        if s.get("pct_chg", 0) >= min_pct
                    ][:10]

                    st.session_state["sector_data"] = all_data
                    st.session_state["sector_rising"] = rising
                    st.session_state["sector_type"] = sector_type

                except Exception as e:
                    st.exception(e)

        # 展示异动板块
        if "sector_rising" in st.session_state and st.session_state.get("sector_rising"):
            rising = st.session_state["sector_rising"]
            st.success(f"发现 {len(rising)} 个异动板块（涨幅 > {min_pct}%）")
            df_rise = pd.DataFrame(rising)
            st.dataframe(df_rise, width='stretch', hide_index=True)
        elif "sector_rising" in st.session_state:
            st.info(f"当前无异动板块（阈值 {min_pct}%）")

        # 全部板块排行
        with st.expander("全部板块排行（Top 30）"):
            if "sector_data" in st.session_state and st.session_state.get("sector_data"):
                df_all = pd.DataFrame(st.session_state["sector_data"][:30])
                st.dataframe(df_all, width='stretch', hide_index=True)

# ── Tab2：资金流向 ─────────────────────────────────────────
with tab2:
    st.subheader("资金流向监控")
    st.caption("主力资金净流入排行 + 北向资金动态")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**主力资金排行**")
        if st.button("清除缓存", key="btn_clear_money", help="清除旧缓存数据，强制重新获取"):
            for k in ["money_rank", "north_flow"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
        indicator = st.selectbox("排行类型", ["今日", "3日", "5日", "10日"], key="mf_indicator")
        run_money = st.button("刷新资金数据", key="btn_money", type="primary")

        if run_money:
            with st.spinner("获取资金流向…"):
                try:
                    from app.tracker.money_monitor import MoneyMonitor
                    m = MoneyMonitor()
                    rank_data = m.stock_rank(indicator)
                    st.session_state["money_rank"] = rank_data
                except Exception as e:
                    st.exception(e)

        if "money_rank" in st.session_state and st.session_state["money_rank"]:
            df_money = pd.DataFrame(st.session_state["money_rank"][:30]).copy()
            # 单位转换：元 → 亿
            for col in ["net_mf", "net_mf_big", "net_mf_small"]:
                if col in df_money.columns:
                    df_money[col] = df_money[col] / 1e8
            df_money = df_money.rename(columns={
                "code": "代码", "name": "名称", "close": "最新价",
                "pct_chg": "涨跌幅(%)", "net_mf": "主力净流入(亿)",
                "net_mf_pct": "净占比(%)", "net_mf_big": "超大单(亿)", "net_mf_small": "小单(亿)"
            })
            st.dataframe(df_money, width='stretch', hide_index=True)
        else:
            st.caption("暂无数据，请点击刷新")

    with col2:
        st.markdown("**北向资金（沪深港通）**")
        days_north = st.number_input("查询近 N 日", value=5, min_value=1, max_value=30, key="north_days")

        if st.button("刷新北向资金", key="btn_north", type="primary"):
            with st.spinner("获取北向资金…"):
                try:
                    from app.tracker.money_monitor import MoneyMonitor
                    m = MoneyMonitor()
                    north_data = m.north_flow(days_north)
                    st.session_state["north_flow"] = north_data
                except Exception as e:
                    st.exception(e)

        if "north_flow" in st.session_state and st.session_state["north_flow"]:
            df_north = pd.DataFrame(st.session_state["north_flow"]).rename(columns={
                "date": "日期", "north_net": "北向净流入(元)", "north_index": "收盘指数"
            })
            st.dataframe(df_north, width='stretch', hide_index=True)

# ── Tab3：热搜监控 ─────────────────────────────────────────
with tab3:
    st.subheader("热搜监控")
    st.caption("东方财富 + 百度 + 腾讯，三源聚合")

    col1, col2 = st.columns([1, 2])

    with col1:
        source = st.selectbox("数据源", ["东方财富", "百度", "腾讯", "全部聚合"])
        top_n = st.slider("显示条数", min_value=5, max_value=50, value=20)
        run_hot = st.button("获取热搜", key="btn_hot", type="primary")

    with col2:
        if run_hot:
            with st.spinner("获取热搜数据…"):
                try:
                    from app.tracker.hot_search import HotSearchMonitor
                    m = HotSearchMonitor()

                    if source == "东方财富" or source == "全部聚合":
                        em_data = m.eastmoney()[:top_n]
                        if em_data:
                            st.markdown("**东方财富热搜**")
                            df_em = pd.DataFrame(em_data).rename(columns={
                                "rank": "排名", "code": "代码", "name": "股票名称", "pct_chg": "涨跌幅(%)"
                            })
                            st.dataframe(df_em, width='stretch', hide_index=True)

                    if source == "百度" or source == "全部聚合":
                        try:
                            baidu_data = m.baidu()
                            if baidu_data:
                                st.markdown("**百度股票热搜**")
                                df_bd = pd.DataFrame(baidu_data).rename(columns={
                                    "rank": "排名", "keyword": "关键词", "hot_index": "热度指数"
                                })
                                st.dataframe(df_bd, width='stretch', hide_index=True)
                        except Exception:
                            st.caption("百度热搜获取失败（可能接口不可用）")

                    if source == "腾讯" or source == "全部聚合":
                        try:
                            tx_data = m.tencent()
                            if tx_data:
                                st.markdown("**腾讯自选股热搜**")
                                df_tx = pd.DataFrame(tx_data).rename(columns={
                                    "rank": "排名", "code": "代码", "name": "股票名称", "pct_chg": "涨跌幅(%)"
                                })
                                st.dataframe(df_tx, width='stretch', hide_index=True)
                        except Exception:
                            st.caption("腾讯热搜获取失败（需要 westock-data）")

                    if source == "全部聚合":
                        report = m.get_report()
                        if report.get("summary"):
                            st.markdown("**聚合摘要**")
                            for line in report["summary"]:
                                st.write(f"• {line}")

                except Exception as e:
                    st.exception(e)

# ── Tab4：综合报告 ─────────────────────────────────────────
with tab4:
    st.subheader("风口追踪综合报告")
    if st.button("生成综合报告", key="btn_sector_report", type="primary"):
        with st.spinner("正在生成综合报告…"):
            try:
                from app.tracker.sector_monitor import SectorMonitor
                from app.tracker.money_monitor import MoneyMonitor
                from app.tracker.hot_search import HotSearchMonitor

                sm = SectorMonitor()
                mm = MoneyMonitor()
                hm = HotSearchMonitor()

                sector_rpt = sm.get_report()
                money_rpt = mm.get_report()
                hot_rpt = hm.get_report()

                # 板块异动摘要
                st.markdown("**板块异动**")
                rising = sector_rpt.get("rising_sectors", [])
                if rising:
                    st.dataframe(pd.DataFrame(rising[:10]), width='stretch', hide_index=True)
                else:
                    st.caption("今日无异动板块")

                # 资金流向摘要
                st.markdown("**主力资金异动**")
                money_stocks = money_rpt.get("top_inflow", [])
                if money_stocks:
                    df_money = pd.DataFrame(money_stocks[:10]).copy()
                    # 单位转换：元 → 亿
                    for col in ["net_mf", "net_mf_big", "net_mf_small"]:
                        if col in df_money.columns:
                            df_money[col] = df_money[col] / 1e8
                    df_money = df_money.rename(columns={
                        "code": "代码", "name": "名称", "close": "最新价",
                        "pct_chg": "涨跌幅(%)", "net_mf": "主力净流入(亿)",
                        "net_mf_pct": "净占比(%)", "net_mf_big": "超大单(亿)", "net_mf_small": "小单(亿)"
                    })
                    st.dataframe(df_money, width='stretch', hide_index=True)

                # 热搜摘要
                st.markdown("**市场热搜 Top 10**")
                hot_list = hot_rpt.get("all_hot", [])
                if hot_list:
                    df_hot = pd.DataFrame(hot_list[:10]).rename(columns={
                        "rank": "排名", "source": "来源", "code": "代码", "name": "股票名称", "pct_chg": "涨跌幅(%)"
                    })
                    st.dataframe(df_hot, width='stretch', hide_index=True)

            except Exception as e:
                st.exception(e)
