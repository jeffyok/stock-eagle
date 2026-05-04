"""
StockEagle - FastAPI 主应用
"""
from fastapi import FastAPI
from app.api import api_router
from app.config import settings

app = FastAPI(
    title="StockEagle API",
    version="0.1.0",
    description="开源量化智能选股选基系统",
)

# 注册路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": "StockEagle",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
