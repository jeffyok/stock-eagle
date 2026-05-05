"""
风控规则 Service（对应 t_risk_rule 表）
使用 SQLAlchemy ORM
"""
from typing import Dict, List, Optional
from sqlalchemy import select, update

from app.database import SessionLocal
from app.models import RiskRule


# ── 规则配置模型（内存，用于初始化）────────────────────────────

RULES = {
    "single_loss_pct":      {"name": "单票亏损报警阈值",     "type": "number", "default": "5"},
    "total_loss_pct":       {"name": "账户总亏损报警阈值",   "type": "number", "default": "10"},
    "position_pct":         {"name": "单票仓位上限报警",     "type": "number", "default": "30"},
    "drawdown_pct":         {"name": "账户最大回撤报警阈值", "type": "number", "default": "15"},
    "stop_loss_triggered":  {"name": "止损价触发报警",       "type": "switch", "default": "1"},
    "take_profit_triggered":{"name": "止盈价触发报警",       "type": "switch", "default": "1"},
}


def _ensure_rules(sess) -> None:
    """确保 t_risk_rule 有全部6条默认规则"""
    for key, meta in RULES.items():
        exists = sess.execute(
            select(RiskRule).where(RiskRule.rule_key == key)
        ).scalar_one_or_none()
        if not exists:
            sess.add(RiskRule(
                rule_key=key,
                rule_name=meta["name"],
                rule_value=meta["default"],
                rule_type=meta["type"],
                description="",
                is_enabled=True,
            ))
    sess.commit()


def get_rules() -> Dict[str, dict]:
    """读取所有规则（含当前值）"""
    with SessionLocal() as sess:
        _ensure_rules(sess)
        rows = sess.execute(select(RiskRule).order_by(RiskRule.id)).scalars().all()
        return {
            r.rule_key: {
                "name":     r.rule_name,
                "value":    r.rule_value,
                "type":     r.rule_type,
                "enabled":  r.is_enabled,
                "description": r.description or "",
            }
            for r in rows
        }


def update_rule(rule_key: str, value: str, enabled: Optional[bool] = None) -> bool:
    """更新规则值 / 启用状态"""
    values = {"rule_value": value}
    if enabled is not None:
        values["is_enabled"] = enabled
    stmt = (
        update(RiskRule)
        .where(RiskRule.rule_key == rule_key)
        .values(**values)
    )
    with SessionLocal() as sess:
        result = sess.execute(stmt)
        sess.commit()
        return result.rowcount > 0
