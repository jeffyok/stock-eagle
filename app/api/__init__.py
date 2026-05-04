"""
API 路由模块
"""
from fastapi import APIRouter
from app.api import stock, fund, strategy, portfolio, tracker, backtest

api_router = APIRouter()
api_router.include_router(stock.router, prefix="/stock", tags=["股票"])
api_router.include_router(fund.router, prefix="/fund", tags=["基金"])
api_router.include_router(strategy.router, prefix="/strategy", tags=["策略"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["持仓"])
api_router.include_router(tracker.router, prefix="/tracker", tags=["追踪"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["回测"])
