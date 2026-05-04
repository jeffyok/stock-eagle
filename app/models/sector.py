"""
板块/概念 ORM 模型
"""
from sqlalchemy import (
    Column, String, Integer, DECIMAL, Date, DateTime,
    Enum, Index, UniqueConstraint,
)
from sqlalchemy.sql import func
from app.database import Base


class SectorDaily(Base):
    __tablename__ = "t_sector_daily"

    id = Column(Integer, primary_key=True)
    sector_code = Column(String(10), nullable=False)
    sector_name = Column(String(20))
    sector_type = Column(Enum("industry", "concept", name="sector_enum"), comment="行业/概念")
    trade_date = Column(Date, nullable=False)
    close = Column(DECIMAL(10, 2))
    pct_chg = Column(DECIMAL(10, 4))
    net_mf = Column(DECIMAL(18, 2), comment="板块资金净流入")
    lead_stock = Column(String(10), comment="领涨股代码")
    __table_args__ = (
        UniqueConstraint("sector_code", "trade_date", name="uk_sector_date"),
    )
