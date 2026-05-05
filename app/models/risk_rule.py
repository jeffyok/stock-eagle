"""
风控规则配置 ORM 模型（对应 t_risk_rule 表）
"""
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
)
from sqlalchemy.sql import func
from app.database import Base


class RiskRule(Base):
    """风控规则表"""
    __tablename__ = "t_risk_rule"

    id = Column(Integer, primary_key=True)
    rule_key = Column(String(30), unique=True, nullable=False, comment="规则键")
    rule_name = Column(String(50), nullable=False, comment="规则名称")
    rule_value = Column(String(50), nullable=False, comment="规则值")
    rule_type = Column(String(10), nullable=False, comment="类型：number / switch")
    description = Column(Text, comment="规则说明")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
