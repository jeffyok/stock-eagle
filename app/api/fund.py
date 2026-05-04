"""
基金相关 API 路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db

router = APIRouter()


@router.get("/list")
async def get_fund_list(
    keyword: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """获取基金列表"""
    from app.models.fund import FundBasic

    query = db.query(FundBasic)
    if keyword:
        query = query.filter(
            (FundBasic.code.like(f"%{keyword}%"))
            | (FundBasic.name.like(f"%{keyword}%"))
        )
    funds = query.limit(limit).all()
    return {
        "total": len(funds),
        "data": [{"code": f.code, "name": f.name} for f in funds],
    }


@router.get("/{code}/nav")
async def get_fund_nav(
    code: str,
    start: str = Query(...),
    end: str = Query(...),
):
    """获取基金净值"""
    from app.data.akshare_source import AKShareSource

    source = AKShareSource()
    data = source.get_fund_nav(code)
    return {"code": code, "total": len(data), "data": data}
