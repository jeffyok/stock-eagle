"""
股票相关 API 路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db

router = APIRouter()


@router.get("/list")
async def get_stock_list(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """获取股票列表"""
    from app.models.stock import StockBasic

    query = db.query(StockBasic)
    if keyword:
        query = query.filter(
            (StockBasic.code.like(f"%{keyword}%"))
            | (StockBasic.name.like(f"%{keyword}%"))
        )
    stocks = query.limit(limit).all()
    return {
        "total": len(stocks),
        "data": [{"code": s.code, "name": s.name} for s in stocks],
    }


@router.get("/{code}/realtime")
async def get_stock_realtime(code: str):
    """获取实时行情"""
    from app.data.akshare_source import AKShareSource

    source = AKShareSource()
    data = source.get_stock_realtime(code)
    if not data:
        return {"error": "获取行情失败"}
    return data


@router.get("/{code}/daily")
async def get_stock_daily(
    code: str,
    start: str = Query(..., description="YYYY-MM-DD"),
    end: str = Query(..., description="YYYY-MM-DD"),
):
    """获取历史日线"""
    from app.data.akshare_source import AKShareSource

    source = AKShareSource()
    data = source.get_stock_daily(code, start, end)
    return {"total": len(data), "data": data}
