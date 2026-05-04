"""
策略组合模块
- CombinedStrategy：多策略投票组合，支持多数/全票/任意等投票规则
"""
import pandas as pd
from typing import List, Dict, Any
from datetime import date

from app.strategy.base import BaseStrategy
from app.strategy.technical import _calc_indicators, _get_daily
from app.data.akshare_source import AKShareSource


# ──────────────────────────────────────────────────────────────────────────────
# 投票规则辅助
# ──────────────────────────────────────────────────────────────────────────────

VOTING_RULES = ("majority", "unanimous", "any")


def _vote(votes: List[int], rule: str) -> int:
    """
    根据投票规则和各家投票，返回组合意见：
    1  = 看多（买入/持有）
    0  = 看空（卖出/空仓）
    """
    n = len(votes)
    s = sum(votes)
    if rule == "unanimous":
        return 1 if s == n else 0
    elif rule == "any":
        return 1 if s >= 1 else 0
    else:  # majority
        return 1 if s >= (n + 1) // 2 else 0


# ──────────────────────────────────────────────────────────────────────────────
# CombinedStrategy
# ──────────────────────────────────────────────────────────────────────────────

class CombinedStrategy(BaseStrategy):
    """
    多策略投票组合策略

    投票规则（voting_rule）：
    - "majority" ：超过半数策略看多才买入（默认）
    - "unanimous"：全票通过才买入（最保守）
    - "any"      ：任意一个策略看多就买入（最激进）

    每个子策略的"每日观点"通过其 signals 推导：
      遇到 buy 信号 → 开始看多（持仓=1）
      遇到 sell 信号 → 结束看多（持仓=0）
    然后按投票规则汇总所有子策略的观点，产生组合信号。
    """

    name = "combined"
    description = "多策略投票组合"

    def __init__(
        self,
        strategies: List[BaseStrategy],
        voting_rule: str = "majority",
    ):
        if not strategies:
            raise ValueError("CombinedStrategy 至少需要一个子策略")
        if voting_rule not in VOTING_RULES:
            raise ValueError(f"voting_rule 必须是 {VOTING_RULES} 之一")
        self.strategies = strategies
        self.voting_rule = voting_rule
        self.source = AKShareSource()

    # ──────────────────────────────────────────────────────────────────────
    # 内部：获取单个策略的每日持仓序列（0/1）
    # ──────────────────────────────────────────────────────────────────────

    def _get_position_series(
        self,
        strategy: BaseStrategy,
        code: str,
        start_date: date,
        end_date: date,
        date_index: Dict[date, int],
    ) -> List[int]:
        """
        根据策略的 signals 推导每日持仓建议（0=空仓，1=持有）。
        date_index: {date: row_index_in_df}
        """
        signals = strategy.generate_signals(code, start_date, end_date)
        # 按日期排序
        signals_sorted = sorted(signals, key=lambda x: x["date"])

        n = len(date_index)
        positions = [0] * n
        current_pos = 0
        sig_idx = 0

        for d, idx in sorted(date_index.items(), key=lambda x: x[1]):
            # 处理所有日期 <= d 的 signals
            while sig_idx < len(signals_sorted) and signals_sorted[sig_idx]["date"] <= d:
                sig = signals_sorted[sig_idx]
                if sig["direction"] == "buy":
                    current_pos = 1
                elif sig["direction"] == "sell":
                    current_pos = 0
                sig_idx += 1
            positions[idx] = current_pos

        return positions

    # ──────────────────────────────────────────────────────────────────────
    # generate_signals
    # ──────────────────────────────────────────────────────────────────────

    def generate_signals(
        self,
        code: str,
        start_date: date,
        end_date: date,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        df = _get_daily(self.source, code, start_date, end_date)
        if df.empty or len(df) < 30:
            return []

        df = df.copy()
        df["date"] = pd.to_datetime(df["date"]).dt.date
        date_index = {row["date"]: i for i, row in df.iterrows()}

        # 获取所有子策略的持仓序列
        all_positions = []
        for st in self.strategies:
            pos = self._get_position_series(st, code, start_date, end_date, date_index)
            all_positions.append(pos)

        # 投票产生组合持仓序列
        n_strategies = len(all_positions)
        combined = [0] * len(df)
        for j in range(len(df)):
            votes = [all_positions[i][j] for i in range(n_strategies)]
            combined[j] = _vote(votes, self.voting_rule)

        # 根据组合持仓变化产生信号
        signals = []
        was_in = False
        for j in range(len(df)):
            d = df.iloc[j]["date"]
            price = float(df.iloc[j]["close"])
            now_in = combined[j]

            if not was_in and now_in:
                # 买入：从空仓 → 持仓
                votes_detail = {st.name: all_positions[i][j] for i, st in enumerate(self.strategies)}
                buy_count = sum(votes_detail.values())
                signals.append({
                    "date": d,
                    "direction": "buy",
                    "price": price,
                    "score": round(buy_count / n_strategies * 100, 2),
                    "reason": (
                        f"组合投票买入（{self.voting_rule}规则，"
                        f"{buy_count}/{n_strategies} 策略看多）"
                        f" {votes_detail}"
                    ),
                })
                was_in = True
            elif was_in and not now_in:
                # 卖出：从持仓 → 空仓
                sell_count = sum(1 - all_positions[i][j] for i in range(n_strategies))
                signals.append({
                    "date": d,
                    "direction": "sell",
                    "price": price,
                    "score": round(sell_count / n_strategies * 100, 2),
                    "reason": (
                        f"组合投票卖出（{self.voting_rule}规则，"
                        f"{sell_count}/{n_strategies} 策略看空）"
                    ),
                })
                was_in = False

        return signals

    # ──────────────────────────────────────────────────────────────────────
    # backtest
    # ──────────────────────────────────────────────────────────────────────

    def backtest(
        self,
        code: str,
        start_date: date,
        end_date: date,
        initial_cash: float = 100000.0,
        **kwargs,
    ) -> Dict[str, Any]:
        df = _get_daily(self.source, code, start_date, end_date)
        if df.empty or len(df) < 30:
            return self._empty_result()

        df = _calc_indicators(df)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        date_index = {row["date"]: i for i, row in df.iterrows()}

        # 获取所有子策略的持仓序列
        all_positions = []
        for st in self.strategies:
            pos = self._get_position_series(st, code, start_date, end_date, date_index)
            all_positions.append(pos)

        # 投票产生组合持仓序列（从足够数据开始的索引）
        start_idx = 30
        n_strategies = len(all_positions)
        combined = [0] * len(df)

        for j in range(start_idx, len(df)):
            votes = [all_positions[i][j] for i in range(n_strategies)]
            combined[j] = _vote(votes, self.voting_rule)

        # 回测主循环
        cash = initial_cash
        position = 0
        trades = []
        equity_curve = []
        held = False

        for j in range(start_idx, len(df)):
            row = df.iloc[j]
            price = float(row["close"])
            d = row["date"]
            should_hold = combined[j]

            if not held and should_hold and cash >= price * 100:
                qty = int(cash // (price * 100)) * 100
                cash -= qty * price
                position += qty
                held = True
                trades.append({
                    "date": str(d),
                    "action": "buy",
                    "price": price,
                    "qty": qty,
                    "reason": f"组合投票买入（{self.voting_rule}）",
                })
            elif held and not should_hold:
                cash += position * price
                trades.append({
                    "date": str(d),
                    "action": "sell",
                    "price": price,
                    "qty": position,
                    "reason": f"组合投票卖出（{self.voting_rule}）",
                })
                position = 0
                held = False

            equity_curve.append({"date": str(d), "equity": round(cash + position * price, 2)})

        # 清仓
        if position > 0:
            last_price = float(df.iloc[-1]["close"])
            last_date = str(df.iloc[-1]["date"])
            cash += position * last_price
            trades.append({
                "date": last_date,
                "action": "sell",
                "price": last_price,
                "qty": position,
                "reason": "回测结束清仓",
            })

        return self._calc_stats(initial_cash, cash, trades, equity_curve, df)

    # ──────────────────────────────────────────────────────────────────────
    # 辅助方法
    # ──────────────────────────────────────────────────────────────────────

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "strategy": f"combined({self.voting_rule})",
            "total_return": 0.0,
            "annual_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe": 0.0,
            "win_rate": 0.0,
            "trades": [],
            "equity_curve": [],
        }

    def _calc_stats(
        self,
        init: float,
        final: float,
        trades: List[Dict],
        equity: List[Dict],
        df: pd.DataFrame,
    ) -> Dict[str, Any]:
        total_return = (final - init) / init * 100
        days = (pd.to_datetime(df["date"].iloc[-1]) - pd.to_datetime(df["date"].iloc[0])).days
        years = max(days / 365.25, 0.01)
        annual_return = ((final / init) ** (1 / years) - 1) * 100

        # 最大回撤
        max_dd = 0.0
        peak = equity[0]["equity"] if equity else init
        for p in equity:
            if p["equity"] > peak:
                peak = p["equity"]
            dd = (peak - p["equity"]) / peak * 100
            if dd > max_dd:
                max_dd = dd

        # 夏普比率
        returns = [
            (equity[i]["equity"] - equity[i - 1]["equity"]) / equity[i - 1]["equity"]
            for i in range(1, len(equity)) if equity[i - 1]["equity"] > 0
        ]
        sharpe = 0.0
        if returns:
            mean_r = sum(returns) / len(returns)
            std_r = (sum((r - mean_r) ** 2 for r in returns) / len(returns)) ** 0.5
            if std_r > 0:
                sharpe = (mean_r * 252 - 0.03) / (std_r * (252 ** 0.5))

        # 胜率
        pairs = [
            (trades[i], trades[i + 1])
            for i in range(len(trades) - 1)
            if trades[i]["action"] == "buy" and trades[i + 1]["action"] == "sell"
        ]
        win_rate = (
            sum(1 for b, s in pairs if s["price"] > b["price"]) / len(pairs) * 100
            if pairs else 0.0
        )

        return {
            "strategy": f"combined({self.voting_rule})",
            "total_return": round(total_return, 2),
            "annual_return": round(annual_return, 2),
            "max_drawdown": round(max_dd, 2),
            "sharpe": round(sharpe, 2),
            "win_rate": round(win_rate, 2),
            "trades": trades,
            "equity_curve": equity,
        }
