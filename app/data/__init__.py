"""
数据源模块
支持多数据源自动切换
"""
from app.data.base import BaseDataSource
from app.data.data_service import DataService
from app.data.akshare_source import AKShareSource
from app.data.ashare_source import AshareSource
from app.data.baostock_source import BaoStockSource
from app.data.efinance_source import EFinanceSource

__all__ = [
    "BaseDataSource",
    "DataService",
    "AKShareSource",
    "AshareSource",
    "BaoStockSource",
    "EFinanceSource",
]
