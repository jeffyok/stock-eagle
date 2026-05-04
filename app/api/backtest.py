"""
回测 API 路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from datetime import date as date_type

router = APIRouter()
strategy = None


def _get_strategy():
    global strategy
    if strategy is None:
        from app.strategy.multi_factor import MultiFactorStrategy
        strategy = MultiFactorStrategy()
    return strategy


@router.post("/run")
async def run_backtest(
    strategy: str = Query(..., description="策略名称，当前仅支持 multi_factor"),
    codes: str = Query(..., description="逗号分隔的股票代码，暂只取第一只"),
    start_date: str = Query(...),
    end_date: str = Query(...),
    initial_cash: float = Query(100000.0),
    db: Session = Depends(get_db),
):
    """运行回测"""
    if strategy != "multi_factor":
        return {"error": f"暂不支持策略: {strategy}"}

    code = codes.split(",")[0].strip()
    s = _get_strategy()
    start = date_type.fromisoformat(start_date)
    end = date_type.fromisoformat(end_date)
    result = s.backtest(code, start, end, initial_cash)
    return result


@router.get("/report/{task_id}")
async def get_backtest_report(task_id: str):
    """获取回测报告（待实现：需要异步任务支持）"""
    return {"message": "回测报告查询 - 待实现", "task_id": task_id}
