"""
风控检查引擎
遍历持仓 → 逐条检查规则 → 返回 RiskAlert 列表
"""
from typing import List
from decimal import Decimal

from app.models.portfolio import Portfolio
from app.risk.service import get_rules


class RiskAlert:
    def __init__(self, level: str, code: str, name: str,
                 rule: str, current_val: str, threshold: str):
        self.level = level        # "red" / "yellow" / "green"
        self.code = code
        self.name = name
        self.rule = rule
        self.current_val = current_val
        self.threshold = threshold

    def __repr__(self):
        return f"[{self.level}] {self.name}({self.code}) {self.rule}：{self.current_val}（阈值：{self.threshold}）"


def check_portfolio(positions: List[Portfolio]) -> List[RiskAlert]:
    """
    遍历持仓，逐条检查风控规则，返回预警列表
    """
    rules = get_rules()
    alerts = []

    # 计算账户总市值 / 总成本
    total_market = Decimal("0")
    total_cost = Decimal("0")
    for p in positions:
        mv = p.market_value()
        if mv is not None:
            total_market += mv
        total_cost += p.cost * p.quantity

    # ── 1. 止损 / 止盈触发检查 ───────────────────────────────
    if rules.get("stop_loss_triggered", {}).get("enabled"):
        for p in positions:
            triggered = p.stop_loss_triggered()
            if triggered:
                alerts.append(RiskAlert(
                    level="red",
                    code=p.code, name=p.name,
                    rule="止损价触发",
                    current_val=f"现价 {p.current_price()}",
                    threshold=f"止损价 {p.stop_loss}",
                ))

    if rules.get("take_profit_triggered", {}).get("enabled"):
        for p in positions:
            triggered = p.take_profit_triggered()
            if triggered:
                alerts.append(RiskAlert(
                    level="green",
                    code=p.code, name=p.name,
                    rule="止盈价触发",
                    current_val=f"现价 {p.current_price()}",
                    threshold=f"止盈价 {p.take_profit}",
                ))

    # ── 2. 单票亏损检查 ─────────────────────────────────────
    single_loss_pct = float(rules.get("single_loss_pct", {}).get("value", 5))
    for p in positions:
        pct = p.profit_loss_pct()
        if pct is not None and pct <= -single_loss_pct:
            alerts.append(RiskAlert(
                level="yellow",
                code=p.code, name=p.name,
                rule=f"单票亏损超 {single_loss_pct}%",
                current_val=f"{pct:.2f}%",
                threshold=f"-{single_loss_pct}%",
            ))

    # ── 3. 单票仓位检查 ─────────────────────────────────────
    if total_market > 0:
        position_pct = float(rules.get("position_pct", {}).get("value", 30))
        for p in positions:
            mv = p.market_value()
            if mv is not None:
                pct = float(mv / total_market * 100)
                if pct >= position_pct:
                    alerts.append(RiskAlert(
                        level="yellow",
                        code=p.code, name=p.name,
                        rule=f"单票仓位超 {position_pct}%",
                        current_val=f"{pct:.1f}%",
                        threshold=f"{position_pct}%",
                    ))

    # ── 4. 账户总亏损检查 ───────────────────────────────────
    if total_cost > 0:
        total_pl = float((total_market - total_cost) / total_cost * 100)
        total_loss_pct = float(rules.get("total_loss_pct", {}).get("value", 10))
        if total_pl <= -total_loss_pct:
            alerts.append(RiskAlert(
                level="red",
                code="-", name="账户总仓位",
                rule=f"账户总亏损超 {total_loss_pct}%",
                current_val=f"{total_pl:.2f}%",
                threshold=f"-{total_loss_pct}%",
            ))

    return alerts
