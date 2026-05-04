"""
持仓管理 API 路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db

router = APIRouter()


@router.get("/list")
async def get_portfolio(db: Session = Depends(get_db)):
    """获取持仓列表"""
    return {"message": "持仓列表接口 - 待实现"}


@router.post("/buy")
async def buy_stock():
    """买入股票/基金"""
    return {"message": "买入接口 - 待实现"}


@router.post("/sell")
async def sell_stock():
    """卖出股票/基金"""
    return {"message": "卖出接口 - 待实现"}
