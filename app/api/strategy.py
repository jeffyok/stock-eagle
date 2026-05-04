"""
策略选股 API 路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from datetime import date, timedelta

router = APIRouter()
strategy = None  # 延迟初始化


def _get_strategy():
    global strategy
    if strategy is None:
        from app.strategy.multi_factor import MultiFactorStrategy
        strategy = MultiFactorStrategy()
    return strategy


@router.get("/multi-factor")
async def multi_factor_stock_pick(
    codes: str = Query(..., description="逗号分隔的股票代码，如 sh600519,sz000001"),
    min_score: float = Query(60, ge=0, le=100),
    db: Session = Depends(get_db),
):
    """多因子选股：返回综合评分 >= min_score 的买入信号"""
    s = _get_strategy()
    end = date.today()
    start = end - timedelta(days=365)

    results = []
    for code in codes.split(","):
        code = code.strip()
        if not code:
            continue
        try:
            signals = s.generate_signals(code, start, end)
        except Exception as e:
            print(f"生成信号失败({code}): {e}")
            continue
        for sig in signals:
            if sig["direction"] == "buy" and sig["score"] >= min_score:
                results.append({
                    "code": code,
                    "name": "",  # 可后续补全
                    "score": sig["score"],
                    "price": sig["price"],
                    "reason": sig["reason"],
                })

    results.sort(key=lambda x: x["score"], reverse=True)
    return {"total": len(results), "data": results}


@router.get("/technical")
async def technical_strategy(
    strategy: str = Query("macd_golden", description="策略名称"),
    codes: str = Query(..., description="逗号分隔的股票代码"),
    db: Session = Depends(get_db),
):
    """技术策略选股（暂未实现）"""
    return {"message": f"技术策略 {strategy} - 待实现"}


@router.get("/signals")
async def get_signals(
    code: str = Query(..., description="股票代码"),
    start_date: str = Query(...),
    end_date: str = Query(...),
    db: Session = Depends(get_db),
):
    """查看某只股票在时间段内的买卖信号"""
    from datetime import date as date_type
    s = _get_strategy()
    start = date_type.fromisoformat(start_date)
    end = date_type.fromisoformat(end_date)
    signals = s.generate_signals(code, start, end)
    return {"code": code, "total": len(signals), "data": signals}
