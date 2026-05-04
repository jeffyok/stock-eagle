"""
数据源基类 + 统一数据服务接口
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class BaseDataSource(ABC):
    """数据源抽象基类"""

    @abstractmethod
    def get_stock_realtime(self, code: str) -> Optional[Dict]:
        """获取实时行情"""
        pass

    @abstractmethod
    def get_stock_daily(self, code: str, start: str, end: str) -> List[Dict]:
        """获取历史日线"""
        pass

    @abstractmethod
    def get_stock_basic(self) -> List[Dict]:
        """获取股票基本信息"""
        pass

    @abstractmethod
    def get_fund_nav(self, code: str) -> List[Dict]:
        """获取基金净值"""
        pass


class DataService:
    """统一数据服务（外观模式）"""

    def __init__(self, primary: BaseDataSource, fallback: Optional[BaseDataSource] = None):
        self.primary = primary
        self.fallback = fallback

    def _call(self, method_name: str, *args, **kwargs):
        """调用主数据源，失败则切换备用源"""
        try:
            method = getattr(self.primary, method_name)
            return method(*args, **kwargs)
        except Exception as e:
            if self.fallback:
                try:
                    method = getattr(self.fallback, method_name)
                    return method(*args, **kwargs)
                except Exception:
                    raise e
            raise

    def get_stock_realtime(self, code: str) -> Optional[Dict]:
        return self._call("get_stock_realtime", code)

    def get_stock_daily(self, code: str, start: str, end: str) -> List[Dict]:
        return self._call("get_stock_daily", code, start, end)

    def get_stock_basic(self) -> List[Dict]:
        return self._call("get_stock_basic")

    def get_fund_nav(self, code: str) -> List[Dict]:
        return self._call("get_fund_nav", code)
