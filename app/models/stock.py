"""
股票相关 ORM 模型
"""
from sqlalchemy import (
    Column, String, Integer, DECIMAL, Date, DateTime,
    Text, Enum, Index, UniqueConstraint,
)
from sqlalchemy.sql import func
from app.database import Base


class StockBasic(Base):
    __tablename__ = "t_stock_basic"

    code = Column(String(10), primary_key=True, comment="股票代码 sh600519")
    name = Column(String(20), nullable=False, comment="股票名称")
    industry = Column(String(20), comment="所属行业")
    market = Column(Enum("sh", "sz", "bj", name="market_enum"), comment="市场")
    list_date = Column(Date, comment="上市日期")
    status = Column(Integer, default=1, comment="1-正常 0-退市")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class StockDaily(Base):
    __tablename__ = "t_stock_daily"

    id = Column(Integer, primary_key=True)
    code = Column(String(10), nullable=False, index=True)
    trade_date = Column(Date, nullable=False)
    open = Column(DECIMAL(10, 2))
    close = Column(DECIMAL(10, 2))
    high = Column(DECIMAL(10, 2))
    low = Column(DECIMAL(10, 2))
    volume = Column(Integer, comment="成交量(手)")
    amount = Column(DECIMAL(18, 2), comment="成交额")
    turnover = Column(DECIMAL(10, 4), comment="换手率%")
    pct_chg = Column(DECIMAL(10, 4), comment="涨跌幅%")
    __table_args__ = (
        UniqueConstraint("code", "trade_date", name="uk_code_date"),
        Index("idx_trade_date", "trade_date"),
    )


class StockRealtime(Base):
    __tablename__ = "t_stock_realtime"

    code = Column(String(10), primary_key=True)
    name = Column(String(20))
    price = Column(DECIMAL(10, 2), comment="当前价")
    pct_chg = Column(DECIMAL(10, 4), comment="涨跌幅%")
    volume = Column(Integer)
    amount = Column(DECIMAL(18, 2))
    buy1_price = Column(DECIMAL(10, 2))
    sell1_price = Column(DECIMAL(10, 2))
    high = Column(DECIMAL(10, 2))
    low = Column(DECIMAL(10, 2))
    open = Column(DECIMAL(10, 2))
    yesterday = Column(DECIMAL(10, 2), comment="昨收")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class StockMoneyFlow(Base):
    __tablename__ = "t_stock_money_flow"

    id = Column(Integer, primary_key=True)
    code = Column(String(10), nullable=False, index=True)
    trade_date = Column(Date, nullable=False)
    net_mf = Column(DECIMAL(18, 2), comment="主力净流入")
    net_mf_big = Column(DECIMAL(18, 2), comment="大单净流入")
    net_mf_small = Column(DECIMAL(18, 2), comment="小单净流入")
    __table_args__ = (
        UniqueConstraint("code", "trade_date", name="uk_code_date"),
    )


class DragonTiger(Base):
    __tablename__ = "t_dragon_tiger"

    id = Column(Integer, primary_key=True)
    code = Column(String(10), nullable=False, index=True)
    trade_date = Column(Date, nullable=False)
    reason = Column(String(100), comment="上榜原因")
    buy_amount = Column(DECIMAL(18, 2), comment="买入额")
    sell_amount = Column(DECIMAL(18, 2), comment="卖出额")
    net_amount = Column(DECIMAL(18, 2), comment="净额")
    buy_depts = Column(Text, comment="买入营业部(JSON)")
    sell_depts = Column(Text, comment="卖出营业部(JSON)")
    __table_args__ = (
        Index("idx_date", "trade_date"),
    )
