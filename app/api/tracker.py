"""
风口追踪 API 路由（P2）
"""
from fastapi import APIRouter, Query
from typing import List, Optional

router = APIRouter()


# ── 板块异动 ─────────────────────────────────────────────────────

@router.get("/sector/industry")
async def sector_industry(top_n: int = Query(20, ge=1, le=100)):
    """行业板块实时行情（按涨跌幅降序）"""
    from app.tracker.sector_monitor import SectorMonitor
    m = SectorMonitor()
    data = m.get_industry_sectors()
    return {"total": len(data), "data": data[:top_n]}


@router.get("/sector/concept")
async def sector_concept(top_n: int = Query(20, ge=1, le=100)):
    """概念板块实时行情"""
    from app.tracker.sector_monitor import SectorMonitor
    m = SectorMonitor()
    data = m.get_concept_sectors()
    return {"total": len(data), "data": data[:top_n]}


@router.get("/sector/money-flow")
async def sector_money_flow(
    sector_type: str = Query("industry", description="industry / concept"),
    top_n: int = Query(20, ge=1, le=100),
):
    """板块资金流向排行"""
    from app.tracker.sector_monitor import SectorMonitor
    m = SectorMonitor()
    data = m.get_sector_money_flow(sector_type)
    return {"total": len(data), "data": data[:top_n]}


@router.get("/sector/rising")
async def sector_rising(
    min_pct: float = Query(3.0, description="最小涨跌幅（%）"),
    top_n: int = Query(10, ge=1, le=50),
):
    """涨幅超阈值的异动板块"""
    from app.tracker.sector_monitor import SectorMonitor
    m = SectorMonitor()
    data = m.detect_rising(min_pct, top_n)
    return {"threshold": min_pct, "total": len(data), "data": data}


@router.get("/sector/report")
async def sector_report():
    """板块异动综合报告"""
    from app.tracker.sector_monitor import SectorMonitor
    m = SectorMonitor()
    return m.get_report()


# ── 资金异动 ─────────────────────────────────────────────────────

@router.get("/money/stock-rank")
async def money_stock_rank(
    indicator: str = Query("今日", description="今日 / 3日排行 / 5日排行 / 10日排行"),
    top_n: int = Query(20, ge=1, le=100),
):
    """个股主力资金流向排行"""
    from app.tracker.money_monitor import MoneyMonitor
    m = MoneyMonitor()
    data = m.stock_rank(indicator)
    return {"total": len(data), "data": data[:top_n]}


@router.get("/money/north-flow")
async def money_north_flow(days: int = Query(5, ge=1, le=30)):
    """北向资金近 N 日流向"""
    from app.tracker.money_monitor import MoneyMonitor
    m = MoneyMonitor()
    return {"days": days, "data": m.north_flow(days)}


@router.get("/money/north-hold")
async def money_north_hold(
    market: str = Query("沪股通", description="沪股通 / 深股通"),
    top_n: int = Query(20, ge=1, le=100),
):
    """北向资金重仓排行"""
    from app.tracker.money_monitor import MoneyMonitor
    m = MoneyMonitor()
    return {"market": market, "data": m.north_hold_top(market, top_n)}


@router.get("/money/report")
async def money_report():
    """资金异动综合报告"""
    from app.tracker.money_monitor import MoneyMonitor
    m = MoneyMonitor()
    return m.get_report()


# ── 热搜监控 ─────────────────────────────────────────────────────

@router.get("/hot/eastmoney")
async def hot_eastmoney(top_n: int = Query(20, ge=1, le=50)):
    """东方财富热搜 Top N"""
    from app.tracker.hot_search import HotSearchMonitor
    m = HotSearchMonitor()
    data = m.eastmoney()
    return {"total": len(data), "data": data[:top_n]}


@router.get("/hot/baidu")
async def hot_baidu(date: Optional[str] = Query(None, description="格式 YYYYMMDD，默认今日")):
    """百度股票热搜"""
    from app.tracker.hot_search import HotSearchMonitor
    m = HotSearchMonitor()
    return {"data": m.baidu(date)}


@router.get("/hot/tencent")
async def hot_tencent():
    """腾讯自选股热搜（通过 westock-data）"""
    from app.tracker.hot_search import HotSearchMonitor
    m = HotSearchMonitor()
    data = m.tencent()
    return {"total": len(data), "data": data}


@router.get("/hot/report")
async def hot_report():
    """热搜综合报告（多平台聚合）"""
    from app.tracker.hot_search import HotSearchMonitor
    m = HotSearchMonitor()
    return m.get_report()


# ── 龙虎榜 ───────────────────────────────────────────────────────

@router.get("/lhbt/recent")
async def lhb_recent(
    days: int = Query(30, ge=1, le=90),
    top_n: int = Query(50, ge=1, le=200),
):
    """近 N 日龙虎榜汇总"""
    from app.intelligence.dragon_tiger import DragonTigerAnalyzer
    a = DragonTigerAnalyzer()
    return {"days": days, "data": a.get_recent_lhb(days, top_n)}


@router.get("/lhbt/stock")
async def lhb_stock(
    code: str = Query(..., description="股票代码，如 sh600519"),
    days: int = Query(90, ge=1, le=365),
):
    """个股龙虎榜历史"""
    from app.intelligence.dragon_tiger import DragonTigerAnalyzer
    a = DragonTigerAnalyzer()
    return a.get_stock_lhb_history(code, days)


@router.get("/lhbt/report")
async def lhb_report(days: int = Query(30, ge=1, le=90)):
    """龙虎榜综合分析报告"""
    from app.intelligence.dragon_tiger import DragonTigerAnalyzer
    a = DragonTigerAnalyzer()
    return a.get_analysis_report(days)


# ── AI 综合评分 ──────────────────────────────────────────────────

@router.get("/score/stock")
async def score_stock(code: str = Query(..., description="股票代码，如 sh600519")):
    """单只股票 AI 综合评分"""
    from app.intelligence.scorer import StockScorer
    s = StockScorer()
    return s.score(code)


@router.get("/score/top")
async def score_top(
    top_n: int = Query(20, ge=1, le=100),
):
    """综合评分 Top N（基于基本面快速排行）"""
    from app.intelligence.scorer import StockScorer
    s = StockScorer()
    return {"total": top_n, "data": s.rank_by_financial(top_n)}
