"""
技术策略
- MACDStrategy：MACD 金叉买入，死叉卖出
- BollingerBandStrategy：布林带突破策略
- MAStrategy：均线多头排列策略
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from datetime import date
from app.strategy.base import BaseStrategy
from app.data.akshare_source import AKShareSource


# ──────────────────────────────────────────────────────────────────────────────
# 通用指标计算
# ──────────────────────────────────────────────────────────────────────────────

def _calc_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """计算 MACD / 布林带 / 均线，追加到 df 返回（不修改原始）"""
    df = df.copy()
    close = df["close"]

    # MACD（参数可外部传入，保留默认值）
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd_dif"] = ema12 - ema26
    df["macd_dea"] = df["macd_dif"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = (df["macd_dif"] - df["macd_dea"]) * 2

    # 布林带（默认 20日，2倍标准差）
    df["bb_mid"] = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * bb_std
    df["bb_lower"] = df["bb_mid"] - 2 * bb_std

    # 均线
    for n in [5, 10, 20, 60]:
        df[f"ma{n}"] = close.rolling(n).mean()

    return df


def _get_daily(source: AKShareSource, code: str, start: date, end: date) -> pd.DataFrame:
    """拉取并整理日K数据"""
    raw = source.get_stock_daily(code, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    if not raw:
        return pd.DataFrame()
    df = pd.DataFrame(raw)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


# ──────────────────────────────────────────────────────────────────────────────
# 策略 1：MACD 金叉/死叉
# ──────────────────────────────────────────────────────────────────────────────

class MACDStrategy(BaseStrategy):
    """
    MACD 策略
    - DIF 从下往上穿越 DEA → 金叉买入
    - DIF 从上往下穿越 DEA → 死叉卖出
    """

    name = "macd"
    description = "MACD 金叉买入，死叉卖出"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.source = AKShareSource()
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self._cache: Dict[str, pd.DataFrame] = {}

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
        ema_fast = df["close"].ewm(span=self.fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=self.slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=self.signal, adjust=False).mean()
        df["dif"] = dif
        df["dea"] = dea
        df["hist"] = (dif - dea) * 2

        signals = []
        for i in range(1, len(df)):
            prev_dif, prev_dea = float(df["dif"].iloc[i - 1]), float(df["dea"].iloc[i - 1])
            curr_dif, curr_dea = float(df["dif"].iloc[i]), float(df["dea"].iloc[i])
            d = df["date"].iloc[i].date()
            price = float(df["close"].iloc[i])

            # 金叉：DIF 从负转正，或 DIF 上穿 DEA
            if prev_dif <= prev_dea and curr_dif > curr_dea:
                # 计算柱状图增幅作为信号强度
                score = min(100, 50 + float(df["hist"].iloc[i]) * 10)
                signals.append({
                    "date": d,
                    "direction": "buy",
                    "price": price,
                    "score": round(float(score), 2),
                    "reason": f"MACD金叉 DIF={curr_dif:.3f} DEA={curr_dea:.3f}",
                })
            # 死叉：DIF 从上往下穿越 DEA
            elif prev_dif >= prev_dea and curr_dif < curr_dea:
                score = min(100, 50 - float(df["hist"].iloc[i]) * 10)
                signals.append({
                    "date": d,
                    "direction": "sell",
                    "price": price,
                    "score": round(float(score), 2),
                    "reason": f"MACD死叉 DIF={curr_dif:.3f} DEA={curr_dea:.3f}",
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
        def check_buy(df: pd.DataFrame, i: int) -> bool:
            dif0 = float(df["macd_dif"].iloc[i])
            dea0 = float(df["macd_dea"].iloc[i])
            dif1 = float(df["macd_dif"].iloc[i - 1])
            dea1 = float(df["macd_dea"].iloc[i - 1])
            return dif1 <= dea1 and dif0 > dea0  # 金叉

        def check_sell(df: pd.DataFrame, i: int) -> bool:
            dif0 = float(df["macd_dif"].iloc[i])
            dea0 = float(df["macd_dea"].iloc[i])
            dif1 = float(df["macd_dif"].iloc[i - 1])
            dea1 = float(df["macd_dea"].iloc[i - 1])
            return dif1 >= dea1 and dif0 < dea0  # 死叉

        df_raw = _get_daily(self.source, code, start_date, end_date)
        df_indicators = _calc_indicators(df_raw)
        if df_indicators.empty or len(df_indicators) < 30:
            return self._empty_result()

        cash = initial_cash
        position = 0
        trades = []
        equity_curve = []
        held = False

        for i in range(30, len(df_indicators)):
            row = df_indicators.iloc[i]
            price = float(row["close"])
            d = row["date"].date()

            if not held and check_buy(df_indicators, i) and cash >= price * 100:
                qty = int(cash // (price * 100)) * 100
                cash -= qty * price
                position += qty
                held = True
                trades.append({"date": str(d), "action": "buy", "price": price, "qty": qty})
            elif held and check_sell(df_indicators, i):
                cash += position * price
                trades.append({"date": str(d), "action": "sell", "price": price, "qty": position})
                position = 0
                held = False

            equity_curve.append({"date": str(d), "equity": round(cash + position * price, 2)})

        if position > 0:
            last_price = float(df_indicators.iloc[-1]["close"])
            cash += position * last_price
            trades.append({
                "date": str(df_indicators.iloc[-1]["date"].date()),
                "action": "sell",
                "price": last_price,
                "qty": position,
                "reason": "回测结束清仓",
            })

        return self._calc_stats(initial_cash, cash, trades, equity_curve, df_indicators)

    def _empty_result(self) -> Dict[str, Any]:
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

    def _calc_stats(
        self,
        init: float,
        final: float,
        trades: List[Dict],
        equity: List[Dict],
        df: pd.DataFrame,
    ) -> Dict[str, Any]:
        total_return = (final - init) / init * 100
        days = (df["date"].iloc[-1] - df["date"].iloc[0]).days
        years = max(days / 365.25, 0.01)
        annual_return = ((final / init) ** (1 / years) - 1) * 100

        max_dd = 0.0
        peak = equity[0]["equity"] if equity else init
        for p in equity:
            if p["equity"] > peak:
                peak = p["equity"]
            dd = (peak - p["equity"]) / peak * 100
            if dd > max_dd:
                max_dd = dd

        returns = [(equity[i]["equity"] - equity[i - 1]["equity"]) / equity[i - 1]["equity"]
                   for i in range(1, len(equity)) if equity[i - 1]["equity"] > 0]
        sharpe = 0.0
        if returns:
            mean_r = sum(returns) / len(returns)
            std_r = (sum((r - mean_r) ** 2 for r in returns) / len(returns)) ** 0.5
            if std_r > 0:
                sharpe = (mean_r * 252 - 0.03) / (std_r * (252 ** 0.5))

        pairs = [(trades[i], trades[i + 1]) for i in range(len(trades) - 1)
                 if trades[i]["action"] == "buy" and trades[i + 1]["action"] == "sell"]
        win_rate = sum(1 for b, s in pairs if s["price"] > b["price"]) / len(pairs) * 100 if pairs else 0.0

        return {
            "strategy": self.name,
            "total_return": round(total_return, 2),
            "annual_return": round(annual_return, 2),
            "max_drawdown": round(max_dd, 2),
            "sharpe": round(sharpe, 2),
            "win_rate": round(win_rate, 2),
            "trades": trades,
            "equity_curve": equity,
        }


# ──────────────────────────────────────────────────────────────────────────────
# 策略 2：布林带突破
# ──────────────────────────────────────────────────────────────────────────────

class BollingerBandStrategy(BaseStrategy):
    """
    布林带突破策略
    - 价格上穿布林带上轨 → 买入（突破信号）
    - 价格下穿布林带下轨 → 卖出（超跌信号）
    - 价格触及布林带中轨且下跌 → 卖出
    """

    name = "bollinger"
    description = "布林带突破策略：突破上轨买入，跌破下轨卖出"

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.source = AKShareSource()
        self.period = period
        self.std_dev = std_dev
        self._cache: Dict[str, pd.DataFrame] = {}

    def generate_signals(
        self,
        code: str,
        start_date: date,
        end_date: date,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        df = _get_daily(self.source, code, start_date, end_date)
        if df.empty or len(df) < self.period + 5:
            return []

        df = _calc_indicators(df)
        signals = []

        for i in range(self.period, len(df)):
            row = df.iloc[i]
            price = float(row["close"])
            upper = float(row["bb_upper"])
            mid = float(row["bb_mid"])
            lower = float(row["bb_lower"])
            prev_price = float(df["close"].iloc[i - 1])
            d = row["date"].date()

            # 买入：当日突破上轨（前一日在上轨以下）
            if prev_price <= upper and price > upper:
                spread = (price - upper) / upper * 100
                score = min(100, 50 + spread * 5)
                signals.append({
                    "date": d,
                    "direction": "buy",
                    "price": price,
                    "score": round(float(score), 2),
                    "reason": f"突破布林上轨 {upper:.2f}，偏离{spread:.2f}%",
                })
            # 卖出：当日跌破下轨
            elif prev_price >= lower and price < lower:
                spread = (lower - price) / lower * 100
                score = min(100, 50 + spread * 5)
                signals.append({
                    "date": d,
                    "direction": "sell",
                    "price": price,
                    "score": round(float(score), 2),
                    "reason": f"跌破布林下轨 {lower:.2f}，偏离{spread:.2f}%",
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
        df = _get_daily(self.source, code, start_date, end_date)
        if df.empty or len(df) < self.period + 5:
            return self._empty_result()

        df = _calc_indicators(df)
        cash = initial_cash
        position = 0
        trades = []
        equity_curve = []
        bought = False

        for i in range(self.period, len(df)):
            row = df.iloc[i]
            price = float(row["close"])
            upper = float(row["bb_upper"])
            lower = float(row["bb_lower"])
            prev_price = float(df["close"].iloc[i - 1])
            d = row["date"].date()

            # 买入信号
            if not bought and prev_price <= upper and price > upper:
                if cash >= price * 100:
                    qty = int(cash // (price * 100)) * 100
                    cash -= qty * price
                    position += qty
                    bought = True
                    trades.append({
                        "date": str(d),
                        "action": "buy",
                        "price": price,
                        "qty": qty,
                        "reason": "布林上轨突破",
                    })

            # 卖出信号
            elif bought and prev_price >= lower and price < lower:
                cash += position * price
                trades.append({
                    "date": str(d),
                    "action": "sell",
                    "price": price,
                    "qty": position,
                    "reason": "布林下轨跌破",
                })
                position = 0
                bought = False

            equity_curve.append({"date": str(d), "equity": round(cash + position * price, 2)})

        # 清仓
        if position > 0:
            last_price = float(df.iloc[-1]["close"])
            cash += position * last_price
            trades.append({
                "date": str(df.iloc[-1]["date"].date()),
                "action": "sell",
                "price": last_price,
                "qty": position,
                "reason": "回测结束清仓",
            })

        return self._calc_stats(initial_cash, cash, trades, equity_curve, df)

    def _empty_result(self) -> Dict[str, Any]:
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

    @staticmethod
    def _calc_stats(
        init: float,
        final: float,
        trades: List[Dict],
        equity: List[Dict],
        df: pd.DataFrame,
    ) -> Dict[str, Any]:
        total_return = (final - init) / init * 100
        days = (df["date"].iloc[-1] - df["date"].iloc[0]).days
        years = max(days / 365.25, 0.01)
        annual_return = ((final / init) ** (1 / years) - 1) * 100

        max_dd = 0.0
        peak = equity[0]["equity"] if equity else init
        for p in equity:
            if p["equity"] > peak:
                peak = p["equity"]
            dd = (peak - p["equity"]) / peak * 100
            if dd > max_dd:
                max_dd = dd

        returns = [(equity[i]["equity"] - equity[i - 1]["equity"]) / equity[i - 1]["equity"]
                   for i in range(1, len(equity)) if equity[i - 1]["equity"] > 0]
        sharpe = 0.0
        if returns:
            mean_r = sum(returns) / len(returns)
            std_r = (sum((r - mean_r) ** 2 for r in returns) / len(returns)) ** 0.5
            if std_r > 0:
                sharpe = (mean_r * 252 - 0.03) / (std_r * (252 ** 0.5))

        pairs = [(trades[i], trades[i + 1]) for i in range(len(trades) - 1)
                 if trades[i]["action"] == "buy" and trades[i + 1]["action"] == "sell"]
        win_rate = sum(1 for b, s in pairs if s["price"] > b["price"]) / len(pairs) * 100 if pairs else 0.0

        return {
            "strategy": "bollinger",
            "total_return": round(total_return, 2),
            "annual_return": round(annual_return, 2),
            "max_drawdown": round(max_dd, 2),
            "sharpe": round(sharpe, 2),
            "win_rate": round(win_rate, 2),
            "trades": trades,
            "equity_curve": equity,
        }


# ──────────────────────────────────────────────────────────────────────────────
# 策略 3：均线多头排列
# ──────────────────────────────────────────────────────────────────────────────

class MAStrategy(BaseStrategy):
    """
    均线多头排列策略
    - MA5 > MA10 > MA20 → 多头排列，买入
    - MA5 < MA10 < MA20 → 空头排列，卖出
    - 附加：MA5 上穿 MA20 金叉买入，MA5 下穿 MA20 死叉卖出
    """

    name = "ma"
    description = "均线多头排列：MA5>MA10>MA20买入，MA5<MA10<MA20卖出"

    def __init__(self, short: int = 5, mid: int = 10, long: int = 20):
        self.source = AKShareSource()
        self.short = short
        self.mid = mid
        self.long = long

    def generate_signals(
        self,
        code: str,
        start_date: date,
        end_date: date,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        df = _get_daily(self.source, code, start_date, end_date)
        if df.empty or len(df) < self.long + 5:
            return []

        df = _calc_indicators(df)
        signals = []
        was_bull = None  # None / True(多头) / False(空头)

        for i in range(self.long, len(df)):
            row = df.iloc[i]
            price = float(row["close"])
            ma5 = float(row[f"ma{self.short}"])
            ma10 = float(row[f"ma{self.mid}"])
            ma20 = float(row[f"ma{self.long}"])
            prev_row = df.iloc[i - 1]
            prev_ma5 = float(prev_row[f"ma{self.short}"])
            prev_ma10 = float(prev_row[f"ma{self.mid}"])
            prev_ma20 = float(prev_row[f"ma{self.long}"])
            d = row["date"].date()

            # 当前排列
            is_bull = ma5 > ma10 > ma20
            is_bear = ma5 < ma10 < ma20

            # 由空转多（买入）
            if not was_bull and is_bull:
                score = 60 + (ma5 - ma10) / ma10 * 100
                signals.append({
                    "date": d,
                    "direction": "buy",
                    "price": price,
                    "score": round(float(min(100, max(0, score))), 2),
                    "reason": f"均线多头排列 MA{self.short}>{self.mid}>{self.long}",
                })
                was_bull = True

            # 由多转空（卖出）
            elif was_bull and is_bear:
                score = 60 + (ma10 - ma5) / ma5 * 100
                signals.append({
                    "date": d,
                    "direction": "sell",
                    "price": price,
                    "score": round(float(min(100, max(0, score))), 2),
                    "reason": f"均线空头排列 MA{self.short}<{self.mid}<{self.long}",
                })
                was_bull = False

            # 金叉/死叉辅助
            elif was_bull is not None:
                # MA5 上穿 MA20
                if prev_ma5 <= prev_ma20 and ma5 > ma20 and not is_bull:
                    signals.append({
                        "date": d,
                        "direction": "buy",
                        "price": price,
                        "score": 55.0,
                        "reason": f"MA{self.short}上穿MA{self.long}金叉",
                    })
                # MA5 下穿 MA20
                elif prev_ma5 >= prev_ma20 and ma5 < ma20 and is_bull:
                    signals.append({
                        "date": d,
                        "direction": "sell",
                        "price": price,
                        "score": 55.0,
                        "reason": f"MA{self.short}下穿MA{self.long}死叉",
                    })

            # 更新状态
            if is_bull:
                was_bull = True
            elif is_bear:
                was_bull = False

        return signals

    def backtest(
        self,
        code: str,
        start_date: date,
        end_date: date,
        initial_cash: float = 100000.0,
        **kwargs,
    ) -> Dict[str, Any]:
        df = _get_daily(self.source, code, start_date, end_date)
        if df.empty or len(df) < self.long + 5:
            return self._empty_result()

        df = _calc_indicators(df)
        cash = initial_cash
        position = 0
        trades = []
        equity_curve = []
        was_bull = None

        for i in range(self.long, len(df)):
            row = df.iloc[i]
            price = float(row["close"])
            ma5 = float(row[f"ma{self.short}"])
            ma10 = float(row[f"ma{self.mid}"])
            ma20 = float(row[f"ma{self.long}"])
            prev_row = df.iloc[i - 1]
            prev_ma5 = float(prev_row[f"ma{self.short}"])
            prev_ma20 = float(prev_row[f"ma{self.long}"])
            d = row["date"].date()

            is_bull = ma5 > ma10 > ma20
            is_bear = ma5 < ma10 < ma20

            # 买入
            if not was_bull and is_bull and cash >= price * 100:
                qty = int(cash // (price * 100)) * 100
                cash -= qty * price
                position += qty
                trades.append({"date": str(d), "action": "buy", "price": price, "qty": qty})
                was_bull = True

            # 卖出
            elif was_bull and (is_bear or (prev_ma5 >= prev_ma20 and ma5 < ma20)) and position > 0:
                cash += position * price
                trades.append({"date": str(d), "action": "sell", "price": price, "qty": position})
                position = 0
                was_bull = False

            # MA5 下穿 MA20 辅助止损
            elif was_bull and prev_ma5 >= prev_ma20 and ma5 < ma20 and position > 0:
                cash += position * price
                trades.append({"date": str(d), "action": "sell", "price": price, "qty": position, "reason": "MA死叉止损"})
                position = 0
                was_bull = False

            if is_bull:
                was_bull = True
            elif is_bear:
                was_bull = False

            equity_curve.append({"date": str(d), "equity": round(cash + position * price, 2)})

        # 清仓
        if position > 0:
            last_price = float(df.iloc[-1]["close"])
            cash += position * last_price
            trades.append({"date": str(df.iloc[-1]["date"].date()), "action": "sell", "price": last_price, "qty": position, "reason": "回测结束"})

        return self._calc_stats(initial_cash, cash, trades, equity_curve, df)

    def _empty_result(self) -> Dict[str, Any]:
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

    @staticmethod
    def _calc_stats(
        init: float,
        final: float,
        trades: List[Dict],
        equity: List[Dict],
        df: pd.DataFrame,
    ) -> Dict[str, Any]:
        total_return = (final - init) / init * 100
        days = (df["date"].iloc[-1] - df["date"].iloc[0]).days
        years = max(days / 365.25, 0.01)
        annual_return = ((final / init) ** (1 / years) - 1) * 100

        max_dd = 0.0
        peak = equity[0]["equity"] if equity else init
        for p in equity:
            if p["equity"] > peak:
                peak = p["equity"]
            dd = (peak - p["equity"]) / peak * 100
            if dd > max_dd:
                max_dd = dd

        returns = [(equity[i]["equity"] - equity[i - 1]["equity"]) / equity[i - 1]["equity"]
                   for i in range(1, len(equity)) if equity[i - 1]["equity"] > 0]
        sharpe = 0.0
        if returns:
            mean_r = sum(returns) / len(returns)
            std_r = (sum((r - mean_r) ** 2 for r in returns) / len(returns)) ** 0.5
            if std_r > 0:
                sharpe = (mean_r * 252 - 0.03) / (std_r * (252 ** 0.5))

        pairs = [(trades[i], trades[i + 1]) for i in range(len(trades) - 1)
                 if trades[i]["action"] == "buy" and trades[i + 1]["action"] == "sell"]
        win_rate = sum(1 for b, s in pairs if s["price"] > b["price"]) / len(pairs) * 100 if pairs else 0.0

        return {
            "strategy": "ma",
            "total_return": round(total_return, 2),
            "annual_return": round(annual_return, 2),
            "max_drawdown": round(max_dd, 2),
            "sharpe": round(sharpe, 2),
            "win_rate": round(win_rate, 2),
            "trades": trades,
            "equity_curve": equity,
        }
