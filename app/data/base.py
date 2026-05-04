"""
数据源抽象基类
所有数据源实现必须继承此类
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class BaseDataSource(ABC):
    """数据源抽象基类 - 定义统一接口"""

    @abstractmethod
    def get_stock_realtime(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取实时行情
        
        Args:
            code: 股票代码，带市场前缀，如 sh600519, sz000001
            
        Returns:
            字典包含: code, name, price, pct_chg, volume, amount,
            high, low, open, yesterday
        """
        pass

    @abstractmethod
    def get_stock_daily(
        self, code: str, start: str, end: str
    ) -> List[Dict[str, Any]]:
        """
        获取历史日线数据
        
        Args:
            code: 股票代码，带市场前缀
            start: 开始日期 YYYY-MM-DD
            end: 结束日期 YYYY-MM-DD
            
        Returns:
            列表，每项为字典: date, open, close, high, low,
            volume, amount, pct_chg, turn_over
        """
        pass

    @abstractmethod
    def get_stock_basic(self) -> List[Dict[str, Any]]:
        """
        获取股票基本信息列表
        
        Returns:
            列表，每项为字典: code, name, industry, market, list_date
        """
        pass

    @abstractmethod
    def get_fund_nav(self, code: str) -> List[Dict[str, Any]]:
        """
        获取基金净值历史
        
        Args:
            code: 基金代码
            
        Returns:
            列表，每项为字典: date, nav, acc_nav, pct_chg
        """
        pass

    # --- 可选方法（子类可选择性实现）---

    def get_sector_spot(self) -> List[Dict[str, Any]]:
        """获取板块实时行情 - 可选实现"""
        raise NotImplementedError("该数据源不支持板块行情查询")

    def get_money_flow(self, code: str) -> Optional[Dict[str, Any]]:
        """获取个股资金流向 - 可选实现"""
        raise NotImplementedError("该数据源不支持资金流向查询")

    def get_dragon_tiger(self, date: str) -> List[Dict[str, Any]]:
        """获取龙虎榜数据 - 可选实现"""
        raise NotImplementedError("该数据源不支持龙虎榜查询")

    def get_fund_realtime(self, code: str) -> Optional[Dict[str, Any]]:
        """获取基金实时估值 - 可选实现"""
        raise NotImplementedError("该数据源不支持基金实时估值")
