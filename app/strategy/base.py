"""
策略基类
所有量化策略必须继承此类
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import date


class BaseStrategy(ABC):
    """策略抽象基类"""

    name: str = "base_strategy"
    description: str = ""

    @abstractmethod
    def generate_signals(
        self,
        code: str,
        start_date: date,
        end_date: date,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        生成买卖信号
        
        Returns:
            信号列表，每项包含:
            - date: 信号日期
            - direction: 'buy' / 'sell'
            - price: 触发价格
            - score: 信号强度 0-100
            - reason: 信号原因描述
        """
        pass

    @abstractmethod
    def backtest(
        self,
        code: str,
        start_date: date,
        end_date: date,
        initial_cash: float = 100000.0,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        回测策略
        
        Returns:
            回测结果字典:
            - total_return: 总收益率
            - annual_return: 年化收益
            - max_drawdown: 最大回撤
            - sharpe: 夏普比率
            - win_rate: 胜率
            - trades: 交易明细
        """
        pass

    def _calculate_indicators(self, df) -> Dict[str, Any]:
        """计算通用技术指标（子类可复用）"""
        import pandas as pd

        if df.empty:
            return {}

        # MA
        df["ma5"] = df["close"].rolling(5).mean()
        df["ma10"] = df["close"].rolling(10).mean()
        df["ma20"] = df["close"].rolling(20).mean()

        # MACD
        ema12 = df["close"].ewm(span=12, adjust=False).mean()
        ema26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd_dif"] = ema12 - ema26
        df["macd_dea"] = df["macd_dif"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = (df["macd_dif"] - df["macd_dea"]) * 2

        return df
