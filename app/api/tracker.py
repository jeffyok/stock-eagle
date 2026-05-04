"""
风口追踪 API 路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db

router = APIRouter()


@router.get("/sector-hot")
async def get_hot_sectors(
    top_n: int = Query(10, ge=1, le=50),
    min_pct: float = Query(0.0, description="最小涨跌幅过滤"),
):
    """获取热门板块"""
    from app.data.akshare_source import AKShareSource

    source = AKShareSource()
    sectors = source.get_sector_spot()

    # 按涨跌幅排序
    sectors.sort(key=lambda x: x.get("pct_chg", 0), reverse=True)
    filtered = [s for s in sectors if s.get("pct_chg", 0) >= min_pct]
    return {"total": len(filtered[:top_n]), "data": filtered[:top_n]}


@router.get("/money-flow")
async def get_money_flow(
    top_n: int = Query(20, ge=1, le=100),
    direction: str = Query("in", description="in=流入 out=流出"),
):
    """获取资金流向排行"""
    from app.data.akshare_source import AKShareSource

    source = AKShareSource()
    # 获取全部A股资金流向，排序返回 Top N
    return {"message": "资金流向排行 - 待完整实现"}


@router.get("/hot-search")
async def get_hot_search(top_n: int = Query(20, ge=1, le=50)):
    """获取热搜股票"""
    return {"message": "热搜股票 - 待实现（调用 westock-data）"}


@router.get("/dragon-tiger")
async def get_dragon_tiger(date: str = Query(...)):
    """获取龙虎榜数据"""
    from app.data.akshare_source import AKShareSource

    source = AKShareSource()
    data = source.get_dragon_tiger(date)
    return {"date": date, "total": len(data), "data": data}
