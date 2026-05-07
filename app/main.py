"""
StockEagle - FastAPI 主应用
"""
import logging
import sys
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.api import api_router
from app.config import settings

# 配置根日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("stockeagle")
logger.setLevel(logging.INFO)

app = FastAPI(
    title="StockEagle API",
    version="0.1.0",
    description="开源量化智能选股选基系统",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AccessLogMiddleware(BaseHTTPMiddleware):
    """打印每个请求的日志"""

    async def dispatch(self, request: Request, call_next):
        log = logging.getLogger("stockeagle")
        log.info(f"📥 {request.method} {request.url.path}")
        response = await call_next(request)
        log.info(f"📤 {request.method} {request.url.path} → {response.status_code}")
        return response


app.add_middleware(AccessLogMiddleware)

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
