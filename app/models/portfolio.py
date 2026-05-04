"""
持仓管理 ORM 模型
"""
from sqlalchemy import (
    Column, String, Integer, DECIMAL, Date, DateTime,
    Enum,
)
from sqlalchemy.sql import func
from app.database import Base


class Portfolio(Base):
    __tablename__ = "t_portfolio"

    id = Column(Integer, primary_key=True)
    code = Column(String(10), nullable=False, index=True)
    name = Column(String(20))
    asset_type = Column(
        Enum("stock", "fund", name="asset_type_enum"),
        default="stock",
    )
    buy_price = Column(DECIMAL(10, 2), nullable=False, comment="买入价")
    buy_date = Column(Date, nullable=False)
    quantity = Column(Integer, nullable=False, comment="持有数量(股/份)")
    cost = Column(DECIMAL(18, 2), comment="总成本")
    target_price = Column(DECIMAL(10, 2), comment="目标价")
    stop_price = Column(DECIMAL(10, 2), comment="止损价")
    status = Column(
        Enum("holding", "sold", name="status_enum"),
        default="holding",
    )
    sell_price = Column(DECIMAL(10, 2))
    sell_date = Column(Date)
    profit = Column(DECIMAL(18, 2), comment="盈亏金额")
    profit_pct = Column(DECIMAL(10, 4), comment="盈亏比例%")
    created_at = Column(DateTime, default=func.now())
