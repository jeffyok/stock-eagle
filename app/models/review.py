"""
每日复盘 ORM 模型
"""
from sqlalchemy import (
    Column, Integer, Date, Text, DateTime,
)
from sqlalchemy.sql import func
from app.database import Base


class DailyReview(Base):
    __tablename__ = "t_daily_review"

    id = Column(Integer, primary_key=True)
    review_date = Column(Date, nullable=False, unique=True)
    market_trend = Column(Text, comment="大盘走势描述")
    hot_sectors = Column(Text, comment="热门板块(JSON)")
    signals = Column(Text, comment="当日信号(JSON)")
    operation = Column(Text, comment="操作建议")
    summary = Column(Text, comment="复盘总结")
    created_at = Column(DateTime, default=func.now())
