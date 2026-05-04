"""
BaoStock 数据源实现（历史数据专用）
免费、无限制获取A股历史行情和财务数据
需安装: pip install baostock
"""
import baostock as bs
from typing import Optional, List, Dict, Any


class BaoStockSource:
    """BaoStock 数据源 - 专注历史数据"""

    def __init__(self):
        self._logged_in = False

    def _ensure_login(self):
        """确保已登录（BaoStock 需要登录）"""
        if not self._logged_in:
            lg = bs.login()
            if lg.error_code != "0":
                raise RuntimeError(f"BaoStock 登录失败: {lg.error_msg}")
            self._logged_in = True

    def get_stock_daily(
        self, code: str, start: str, end: str
    ) -> List[Dict[str, Any]]:
        """
        获取历史日线数据
        BaoStock 代码格式: sh.600519 / sz.000001
        """
        self._ensure_login()
        # 转换代码格式
        if code.startswith("sh"):
            bs_code = f"sh.{code[2:]}"
        elif code.startswith("sz"):
            bs_code = f"sz.{code[2:]}"
        else:
            bs_code = code

        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,code,open,high,low,close,volume,amount,turn,pctChg",
            start_date=start,
            end_date=end,
            frequency="d",
            adjustflag="3",  # 3=不复权 2=前复权 1=后复权
        )
        records = []
        while (rs.error_code == "0") and rs.next():
            records.append({
                "date": rs.get_row_data()[0],
                "code": code,
                "open": float(rs.get_row_data()[2] or 0),
                "high": float(rs.get_row_data()[3] or 0),
                "low": float(rs.get_row_data()[4] or 0),
                "close": float(rs.get_row_data()[5] or 0),
                "volume": int(float(rs.get_row_data()[6] or 0)),
                "amount": float(rs.get_row_data()[7] or 0),
                "turn_over": float(rs.get_row_data()[8] or 0),
                "pct_chg": float(rs.get_row_data()[9] or 0),
            })
        return records

    def get_stock_basic(self) -> List[Dict[str, Any]]:
        """获取A股列表（含退市）"""
        self._ensure_login()
        rs = bs.query_stock_basic()
        records = []
        while (rs.error_code == "0") and rs.next():
            code = rs.get_row_data()[0]  # sh.600519
            name = rs.get_row_data()[1]
            # 转换为我们的格式
            if code.startswith("sh."):
                full_code = f"sh{code[3:]}"
            elif code.startswith("sz."):
                full_code = f"sz{code[3:]}"
            else:
                continue
            records.append({
                "code": full_code,
                "name": name,
                "market": "sh" if code.startswith("sh.") else "sz",
            })
        return records

    def __del__(self):
        """析构时登出"""
        if self._logged_in:
            bs.logout()
