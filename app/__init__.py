"""
StockEagle - 量化智能选股选基系统
FastAPI 主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import stock, fund, strategy, portfolio, tracker, backtest

app = FastAPI(
    title="StockEagle API",
    description="量化智能选股选基系统 API",
    version="1.0.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(stock.router, prefix="/api/stock", tags=["股票"])
app.include_router(fund.router, prefix="/api/fund", tags=["基金"])
app.include_router(strategy.router, prefix="/api/strategy", tags=["策略"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["持仓"])
app.include_router(tracker.router, prefix="/api/tracker", tags=["追踪"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["回测"])


@app.get("/")
async def root():
    return {
        "name": "StockEagle 🦅",
        "version": "1.0.0",
        "description": "量化智能选股选基系统",
        "endpoints": {
            "股票": "/api/stock",
            "基金": "/api/fund",
            "策略": "/api/strategy",
            "持仓": "/api/portfolio",
            "追踪": "/api/tracker",
            "回测": "/api/backtest",
            "文档": "/docs",
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
