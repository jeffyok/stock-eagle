"""
多因子选股策略
价值 + 成长 + 质量 + 动量 + 波动率
"""
import pandas as pd
from typing import List, Dict, Any
from datetime import date, datetime, timedelta
from app.strategy.base import BaseStrategy
from app.data.akshare_source import AKShareSource


class MultiFactorStrategy(BaseStrategy):
    """多因子选股策略"""

    name = "multi_factor"
    description = "多因子选股：价值/成长/质量/动量/波动率"

    # 因子权重
    WEIGHTS = {
        "value": 0.25,
        "growth": 0.20,
        "quality": 0.20,
        "momentum": 0.20,
        "volatility": 0.15,
    }

    def __init__(self):
        self.source = AKShareSource()
        self._daily_cache: Dict[str, pd.DataFrame] = {}
        self._fin_cache: Dict[str, Dict] = {}

    # ------------------------------------------------------------------ #
    # 公开接口
    # ------------------------------------------------------------------ #

    def generate_signals(
        self,
        code: str,
        start_date: date,
        end_date: date,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        生成买卖信号
        综合评分 >= 45 → 买入信号
        综合评分 <= 40 → 卖出信号（持仓时）
        """
        df = self._get_daily(code, start_date, end_date)
        if df.empty or len(df) < 20:
            return []

        financial = self._get_financial(code)
        price = float(df.iloc[-1]["close"])

        # 计算各因子得分（0~100）
        value_score = self._calc_value_score(financial, price)
        growth_score = self._calc_growth_score(financial)
        quality_score = self._calc_quality_score(financial)
        momentum_score = self._calc_momentum_score(df)
        volatility_score = self._calc_volatility_score(df)

        total = (
            value_score * self.WEIGHTS["value"]
            + growth_score * self.WEIGHTS["growth"]
            + quality_score * self.WEIGHTS["quality"]
            + momentum_score * self.WEIGHTS["momentum"]
            + volatility_score * self.WEIGHTS["volatility"]
        )

        signals = []
        last_row = df.iloc[-1]
        signal_date = pd.to_datetime(last_row["date"]).date() if hasattr(last_row["date"], "strftime") else end_date

        if total >= 45:
            signals.append({
                "date": signal_date,
                "direction": "buy",
                "price": price,
                "score": round(float(total), 2),
                "reason": self._build_reason(
                    value_score, growth_score, quality_score,
                    momentum_score, volatility_score,
                ),
            })
        elif total <= 40:
            signals.append({
                "date": signal_date,
                "direction": "sell",
                "price": price,
                "score": round(float(total), 2),
                "reason": self._build_reason(
                    value_score, growth_score, quality_score,
                    momentum_score, volatility_score,
                ),
            })

        return signals

    def backtest(
        self,
        code: str,
        start_date: date,
        end_date: date,
        initial_cash: float = 100000.0,
        **kwargs,
    ) -> Dict[str, Any]:
        """简易回测：按综合评分每日调仓"""
        df = self._get_daily(code, start_date, end_date)
        if df.empty or len(df) < 60:
            return self._empty_backtest()

        cash = initial_cash
        position = 0  # 持仓股数
        trades = []
        equity_curve = []

        for i in range(20, len(df)):
            window = df.iloc[: i + 1]
            row = window.iloc[-1]
            price = float(row["close"])
            d = pd.to_datetime(row["date"]).date()

            financial = self._get_financial(code)

            value_score = self._calc_value_score(financial, price)
            growth_score = self._calc_growth_score(financial)
            quality_score = self._calc_quality_score(financial)
            momentum_score = self._calc_momentum_score(window)
            volatility_score = self._calc_volatility_score(window)

            total = (
                value_score * self.WEIGHTS["value"]
                + growth_score * self.WEIGHTS["growth"]
                + quality_score * self.WEIGHTS["quality"]
                + momentum_score * self.WEIGHTS["momentum"]
                + volatility_score * self.WEIGHTS["volatility"]
            )

            # 买入
            if total >= 45 and cash >= price * 100:
                qty = int(cash // (price * 100)) * 100
                cash -= qty * price
                position += qty
                trades.append({
                    "date": str(d),
                    "action": "buy",
                    "price": price,
                    "qty": qty,
                    "score": round(float(total), 2),
                })

            # 卖出
            elif total <= 40 and position > 0:
                cash += position * price
                trades.append({
                    "date": str(d),
                    "action": "sell",
                    "price": price,
                    "qty": position,
                    "score": round(float(total), 2),
                })
                position = 0

            # 记录权益
            equity = cash + position * price
            equity_curve.append({"date": str(d), "equity": round(equity, 2)})

        # 最终清仓
        if position > 0:
            last_price = float(df.iloc[-1]["close"])
            cash += position * last_price
            position = 0

        return self._calc_backtest_stats(
            initial_cash, cash, trades, equity_curve, df,
        )

    # ------------------------------------------------------------------ #
    # 因子计算
    # ------------------------------------------------------------------ #

    def _calc_value_score(self, financial: Dict, price: float) -> float:
        """
        价值因子（0~100）：
        低 PE → 高分，低 PB → 高分
        PB = 股价 / 每股净资产（动态计算）
        """
        if not financial:
            return 50.0

        pe = financial.get("pe", 0) or 0
        bps = financial.get("bps", 0) or 0
        pb = price / bps if bps > 0 else 999  # 计算 PB

        # PE 评分：PE < 15 → 100分，PE > 80 → 0分
        if pe <= 0:
            pe_score = 50.0
        else:
            pe_score = max(0, 100 - (pe - 15) / (80 - 15) * 100)
            pe_score = max(0, min(100, pe_score))

        # PB 评分：PB < 1.5 → 100分，PB > 15 → 0分
        if pb <= 0:
            pb_score = 50.0
        else:
            pb_score = max(0, 100 - (pb - 1.5) / (15 - 1.5) * 100)
            pb_score = max(0, min(100, pb_score))

        return round((pe_score * 0.5 + pb_score * 0.5), 2)

    def _calc_growth_score(self, financial: Dict) -> float:
        """
        成长因子（0~100）：
        营收同比增长 > 30% → 高分
        净利润同比增长 > 30% → 高分
        """
        if not financial:
            return 50.0

        rev_growth = financial.get("revenue_growth", 0) or 0
        profit_growth = financial.get("profit_growth", 0) or 0

        # 营收增长评分：-50% ~ 100%，映射到 0~100
        rev_score = max(0, min(100, (rev_growth + 50) / 150 * 100))
        # 净利润增长评分
        profit_score = max(0, min(100, (profit_growth + 50) / 150 * 100))

        return round((rev_score * 0.5 + profit_score * 0.5), 2)

    def _calc_quality_score(self, financial: Dict) -> float:
        """
        质量因子（0~100）：
        ROE 高 → 高分，毛利率高 → 高分，净利率高 → 高分
        """
        if not financial:
            return 50.0

        roe = financial.get("roe", 0) or 0
        gross_margin = financial.get("gross_margin", 0) or 0
        net_margin = financial.get("net_margin", 0) or 0

        # ROE 评分：ROE < 0 → 0分，ROE > 30% → 100分
        roe_score = max(0, min(100, roe / 30 * 100))

        # 毛利率评分：毛利率 < 0 → 0分，毛利率 > 80% → 100分
        gm_score = max(0, min(100, gross_margin / 80 * 100))

        # 净利率评分
        nm_score = max(0, min(100, net_margin / 50 * 100))

        return round((roe_score * 0.4 + gm_score * 0.3 + nm_score * 0.3), 2)

    def _calc_momentum_score(self, df: pd.DataFrame) -> float:
        """
        动量因子（0~100）：
        20日涨幅 → 高分，MACD 金叉 → 加分
        """
        if len(df) < 20:
            return 50.0

        close = df["close"]
        p20 = float(close.iloc[-20])
        p_now = float(close.iloc[-1])
        p5 = float(close.iloc[-5]) if len(df) >= 5 else p20

        # 20日涨幅评分：-20% ~ +50%
        ret20 = (p_now - p20) / p20 * 100
        mom20_score = max(0, min(100, (ret20 + 20) / 70 * 100))

        # 5日涨幅加分
        ret5 = (p_now - p5) / p5 * 100
        mom5_score = max(0, min(100, (ret5 + 10) / 30 * 100))

        # MACD 金叉检测
        macd_score = 50.0
        if len(df) >= 26:
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            dif = ema12 - ema26
            dea = dif.ewm(span=9, adjust=False).mean()
            # 昨天 DIF < DEA，今天 DIF > DEA → 金叉
            if len(dif) >= 2 and dif.iloc[-2] < dea.iloc[-2] and dif.iloc[-1] > dea.iloc[-1]:
                macd_score = 100.0
            elif dif.iloc[-1] > dea.iloc[-1]:
                macd_score = 75.0
            elif dif.iloc[-1] < dea.iloc[-1]:
                macd_score = 25.0

        return round((mom20_score * 0.4 + mom5_score * 0.3 + macd_score * 0.3), 2)

    def _calc_volatility_score(self, df: pd.DataFrame) -> float:
        """
        波动率因子（0~100）：
        低波动 → 高分（日波动率 < 1% → 100分，> 5% → 0分）
        """
        if len(df) < 10:
            return 50.0

        close = df["close"]
        rets = close.pct_change().dropna()
        vol = rets.tail(20).std() * (252 ** 0.5)  # 年化波动率

        # 波动率评分：vol < 0.1 → 100分，vol > 0.6 → 0分
        score = max(0, 100 - (vol - 0.1) / (0.6 - 0.1) * 100)
        return round(max(0, min(100, score)), 2)

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #

    def _get_daily(self, code: str, start: date, end: date) -> pd.DataFrame:
        """获取日K数据（带缓存）"""
        key = f"{code}_{start}_{end}"
        if key in self._daily_cache:
            return self._daily_cache[key]

        raw = self.source.get_stock_daily(
            code, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"),
        )
        if not raw:
            return pd.DataFrame()

        df = pd.DataFrame(raw)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        self._daily_cache[key] = df
        return df

    def _get_financial(self, code: str) -> Dict:
        """获取财务数据（带缓存）"""
        if code in self._fin_cache:
            return self._fin_cache[code]

        data = self.source.get_financial_data(code)
        self._fin_cache[code] = data
        return data or {}

    def _build_reason(self, vs: float, gs: float, qs: float,
                      ms: float, ws: float) -> str:
        parts = []
        if vs >= 70:
            parts.append("价值低估")
        if gs >= 70:
            parts.append("高成长")
        if qs >= 70:
            parts.append("高质量")
        if ms >= 70:
            parts.append("动量强")
        if ws >= 70:
            parts.append("低波动")
        return "、".join(parts) if parts else "综合评分中等"

    def _empty_backtest(self) -> Dict[str, Any]:
        return {
            "strategy": self.name,
            "total_return": 0.0,
            "annual_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe": 0.0,
            "win_rate": 0.0,
            "trades": [],
            "equity_curve": [],
        }

    def _calc_backtest_stats(
        self,
        initial_cash: float,
        final_cash: float,
        trades: List[Dict],
        equity_curve: List[Dict],
        df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """计算回测统计指标"""
        total_return = (final_cash - initial_cash) / initial_cash * 100

        # 年化收益
        days = (pd.to_datetime(df.iloc[-1]["date"]) - pd.to_datetime(df.iloc[0]["date"])).days
        years = max(days / 365.25, 0.01)
        annual_return = ((final_cash / initial_cash) ** (1 / years) - 1) * 100

        # 最大回撤
        max_dd = 0.0
        if equity_curve:
            peaks = []
            cur_peak = equity_curve[0]["equity"]
            for p in equity_curve:
                if p["equity"] > cur_peak:
                    cur_peak = p["equity"]
                dd = (cur_peak - p["equity"]) / cur_peak * 100
                if dd > max_dd:
                    max_dd = dd

        # 夏普比率（简化：假设无风险利率 3%）
        returns = []
        for i in range(1, len(equity_curve)):
            r = (equity_curve[i]["equity"] - equity_curve[i - 1]["equity"]) / equity_curve[i - 1]["equity"]
            returns.append(r)
        sharpe = 0.0
        if returns:
            import math
            mean_r = sum(returns) / len(returns)
            std_r = (sum((r - mean_r) ** 2 for r in returns) / len(returns)) ** 0.5
            if std_r > 0:
                sharpe = (mean_r * 252 - 0.03) / (std_r * (252 ** 0.5))

        # 胜率
        win_rate = 0.0
        if trades:
            wins = sum(1 for t in trades if t.get("action") == "sell" and t.get("price", 0) > 0)
            win_rate = wins / len([t for t in trades if t.get("action") == "sell"]) * 100 if any(t.get("action") == "sell" for t in trades) else 0

        return {
            "strategy": self.name,
            "total_return": round(total_return, 2),
            "annual_return": round(annual_return, 2),
            "max_drawdown": round(max_dd, 2),
            "sharpe": round(sharpe, 2),
            "win_rate": round(win_rate, 2),
            "trades": trades,
            "equity_curve": equity_curve,
        }
