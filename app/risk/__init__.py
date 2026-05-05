"""
风控模块入口
导出：service 层函数、RiskAlert 数据类、check_portfolio 引擎
"""
from app.risk.service import get_rules, update_rule
from app.risk.engine import RiskAlert, check_portfolio

__all__ = ["get_rules", "update_rule", "RiskAlert", "check_portfolio"]
