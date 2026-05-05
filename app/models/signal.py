"""
策略信号 ORM 模型
"""
from sqlalchemy import (
    Column, String, Integer, DECIMAL, Date, DateTime, Text,
    Enum, Index,
)
from sqlalchemy.sql import func
from app.database import Base


class StrategySignal(Base):
    __tablename__ = "t_strategy_signal"

    id = Column(Integer, primary_key=True)
    code = Column(String(10), nullable=False, index=True)
    name = Column(String(50), comment="股票名称")
    signal_type = Column(String(20), nullable=False, comment="策略类型: multi_factor/macd/bollinger/ma")
    direction = Column(Enum("buy", "sell", name="direction_enum"), nullable=False)
    price = Column(DECIMAL(10, 2), comment="信号价格")
    score = Column(DECIMAL(5, 2), comment="信号强度0-100")
    reason = Column(Text, comment="信号原因")
    signal_date = Column(DateTime, nullable=False)
    is_expired = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    __table_args__ = (
        Index("idx_code_type", "code", "signal_type"),
        Index("idx_date", "signal_date"),
    )
