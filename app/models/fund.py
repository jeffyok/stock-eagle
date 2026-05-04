"""
基金相关 ORM 模型
"""
from sqlalchemy import (
    Column, String, Integer, DECIMAL, Date, DateTime, Text,
    Index, UniqueConstraint,
)
from sqlalchemy.sql import func
from app.database import Base


class FundBasic(Base):
    __tablename__ = "t_fund_basic"

    code = Column(String(10), primary_key=True, comment="基金代码")
    name = Column(String(50), nullable=False, comment="基金名称")
    fund_type = Column(String(20), comment="股票型/混合型/债券型/指数型")
    manager = Column(String(30), comment="基金经理")
    size = Column(DECIMAL(18, 2), comment="规模(亿)")
    establish_date = Column(Date)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class FundNav(Base):
    __tablename__ = "t_fund_nav"

    id = Column(Integer, primary_key=True)
    code = Column(String(10), nullable=False, index=True)
    nav_date = Column(Date, nullable=False)
    nav = Column(DECIMAL(10, 4), comment="单位净值")
    acc_nav = Column(DECIMAL(10, 4), comment="累计净值")
    pct_chg = Column(DECIMAL(10, 4), comment="日涨跌幅%")
    __table_args__ = (
        UniqueConstraint("code", "nav_date", name="uk_code_date"),
    )
