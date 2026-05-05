"""
持仓管理 ORM 模型（对应 t_portfolio 表）
"""
from sqlalchemy import (
    Column, String, Integer, DECIMAL, Date, DateTime,
)
from sqlalchemy.sql import func
from decimal import Decimal
from typing import Optional

from app.database import Base


class Portfolio(Base):
    """持仓表 ORM"""
    __allow_unmapped__ = True
    __tablename__ = "t_portfolio"

    id = Column(Integer, primary_key=True)
    code = Column(String(10), nullable=False, index=True, comment="股票代码 sh600519")
    name = Column(String(20), nullable=False, comment="股票名称")
    cost = Column(DECIMAL(12, 2), nullable=False, comment="持仓成本（元/股）")
    quantity = Column(Integer, nullable=False, comment="持仓数量（股）")
    buy_date = Column(Date, nullable=False, comment="买入日期")
    stop_loss = Column(DECIMAL(12, 2), comment="止损价（元）")
    take_profit = Column(DECIMAL(12, 2), comment="止盈价（元）")
    note = Column(String(255), comment="备注")
    deleted_at = Column(DateTime, comment="软删除时间")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 非持久化字段：实时价格（由 service 层填充，避开 name mangling）
    _rt_price: Optional[Decimal] = None

    def current_price(self) -> Optional[Decimal]:
        """获取实时价格"""
        return self._rt_price

    def set_current_price(self, price: Optional[Decimal]):
        """设置实时价格（供 service 层调用）"""
        self._rt_price = price

    def market_value(self) -> Optional[Decimal]:
        """市值 = 现价 × 数量"""
        price = self.current_price()
        if price is None:
            return None
        return price * self.quantity

    def profit_loss(self) -> Optional[Decimal]:
        """盈亏金额 = (现价 - 成本) × 数量"""
        price = self.current_price()
        if price is None:
            return None
        return (price - self.cost) * self.quantity

    def profit_loss_pct(self) -> Optional[float]:
        """盈亏比例 = (现价 - 成本) / 成本 × 100"""
        if self.cost == 0:
            return None
        price = self.current_price()
        if price is None:
            return None
        return float((price - self.cost) / self.cost * 100)

    def stop_loss_triggered(self) -> Optional[bool]:
        """是否触发止损"""
        price = self.current_price()
        if price is None or self.stop_loss is None:
            return None
        return price <= self.stop_loss

    def take_profit_triggered(self) -> Optional[bool]:
        """是否触发止盈"""
        price = self.current_price()
        if price is None or self.take_profit is None:
            return None
        return price >= self.take_profit
