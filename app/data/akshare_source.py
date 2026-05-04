"""
AKShare 数据源实现
覆盖：实时行情、历史K线、财务、资金流向、龙虎榜、板块、基金
"""
import akshare as ak
import pandas as pd
from typing import Optional, List, Dict, Any
from app.data.base import BaseDataSource


class AKShareSource(BaseDataSource):
    """AKShare 数据源（主数据源）"""

    def get_stock_realtime(self, code: str) -> Optional[Dict]:
        """获取实时行情 - 需要市场前缀代码如 sh600519"""
        try:
            df = ak.stock_zh_a_spot_em()
            row = df[df["代码"] == code.replace("sh", "").replace("sz", "").replace("bj", "")]
            if row.empty:
                return None
            r = row.iloc[0]
            return {
                "code": code,
                "name": r.get("名称", ""),
                "price": float(r.get("最新价", 0)),
                "pct_chg": float(r.get("涨跌幅", 0)),
                "volume": int(r.get("成交量", 0)),
                "amount": float(r.get("成交额", 0)),
                "high": float(r.get("最高", 0)),
                "low": float(r.get("最低", 0)),
                "open": float(r.get("今开", 0)),
                "yesterday": float(r.get("昨收", 0)),
            }
        except Exception as e:
            print(f"AKShare 实时行情获取失败: {e}")
            return None

    def get_stock_daily(self, code: str, start: str, end: str) -> List[Dict]:
        """获取历史日线"""
        try:
            market = code[:2]  # sh/sz/bj
            stock_code = code[2:]
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start.replace("-", ""),
                end_date=end.replace("-", ""),
                adjust="qfq",  # 前复权
            )
            if df.empty:
                return []
            records = []
            for _, row in df.iterrows():
                records.append({
                    "date": str(row["日期"]),
                    "open": float(row["开盘"]),
                    "close": float(row["收盘"]),
                    "high": float(row["最高"]),
                    "low": float(row["最低"]),
                    "volume": int(row["成交量"]),
                    "amount": float(row["成交额"]),
                    "pct_chg": float(row["涨跌幅"]),
                    "turnover": float(row.get("换手率", 0)),
                })
            return records
        except Exception as e:
            print(f"AKShare 历史日线获取失败: {e}")
            return []

    def get_stock_basic(self) -> List[Dict]:
        """获取股票基本信息"""
        try:
            df = ak.stock_info_a_code_name()
            records = []
            for _, row in df.iterrows():
                code = str(row["code"])
                # 判断市场
                if code.startswith("6"):
                    full_code = f"sh{code}"
                elif code.startswith("0") or code.startswith("3"):
                    full_code = f"sz{code}"
                else:
                    full_code = f"bj{code}"
                records.append({
                    "code": full_code,
                    "name": str(row["name"]),
                })
            return records
        except Exception as e:
            print(f"AKShare 股票基本信息获取失败: {e}")
            return []

    def get_fund_nav(self, code: str) -> List[Dict]:
        """获取基金净值"""
        try:
            df = ak.fund_open_fund_info_em(
                fund=code,
                indicator="单位净值走势",
            )
            if df.empty:
                return []
            records = []
            for _, row in df.iterrows():
                records.append({
                    "date": str(row["净值日期"]),
                    "nav": float(row["单位净值"]),
                    "acc_nav": float(row.get("累计净值", 0)),
                    "pct_chg": float(row.get("日增长率", 0)),
                })
            return records
        except Exception as e:
            print(f"AKShare 基金净值获取失败: {e}")
            return []

    # --- 扩展方法（AKShare 特有）---

    def get_sector_spot(self) -> List[Dict]:
        """获取板块实时行情"""
        try:
            df = ak.stock_board_industry_name_em()
            records = []
            for _, row in df.iterrows():
                records.append({
                    "sector_code": str(row.get("板块代码", "")),
                    "sector_name": str(row.get("板块名称", "")),
                    "pct_chg": float(row.get("涨跌幅", 0)),
                    "total_market": float(row.get("总市值", 0)),
                })
            return records
        except Exception as e:
            print(f"AKShare 板块行情获取失败: {e}")
            return []

    def get_money_flow(self, code: str) -> Optional[Dict]:
        """获取个股资金流向"""
        try:
            stock_code = code[2:]
            df = ak.stock_individual_fund_flow_rank(indicator="今日")
            row = df[df["代码"] == stock_code]
            if row.empty:
                return None
            r = row.iloc[0]
            return {
                "code": code,
                "net_mf": float(r.get("主力净流入-净额", 0)),
                "net_mf_big": float(r.get("超大单净流入-净额", 0)),
                "net_mf_small": float(r.get("小单净流入-净额", 0)),
            }
        except Exception as e:
            print(f"AKShare 资金流向获取失败: {e}")
            return None

    def get_dragon_tiger(self, date: str) -> List[Dict]:
        """获取龙虎榜数据"""
        try:
            date_fmt = date.replace("-", "")
            df = ak.stock_lhb_detail_em(date=date_fmt)
            if df.empty:
                return []
            records = []
            for _, row in df.iterrows():
                records.append({
                    "code": str(row.get("代码", "")),
                    "name": str(row.get("名称", "")),
                    "reason": str(row.get("上榜原因", "")),
                    "buy_amount": float(row.get("买入额", 0)),
                    "sell_amount": float(row.get("卖出额", 0)),
                    "net_amount": float(row.get("净额", 0)),
                })
            return records
        except Exception as e:
            print(f"AKShare 龙虎榜获取失败: {e}")
            return []

    # --- 财务数据 ---

    def _code_to_em_format(self, code: str) -> str:
        """将 sh600519 / sz000001 格式转换为 600519.SH / 000001.SZ 格式"""
        market = code[:2]
        stock_code = code[2:]
        if market == "sh":
            return f"{stock_code}.SH"
        elif market == "sz":
            return f"{stock_code}.SZ"
        elif market == "bj":
            return f"{stock_code}.BJ"
        return code

    def get_financial_data(self, code: str, indicator: str = "按报告期") -> Optional[Dict]:
        """
        获取股票主要财务指标（来自东方财富）
        返回最新一期的财务指标字典
        """
        try:
            em_code = self._code_to_em_format(code)
            df = ak.stock_financial_analysis_indicator_em(symbol=em_code, indicator=indicator)
            if df.empty:
                return None
            # 取最新一期（第一行）
            row = df.iloc[0]
            return {
                # 估值
                "pe": float(row.get("PER_TOI", 0) or 0),
                "bps": float(row.get("BPS", 0) or 0),  # 每股净资产（用于计算 PB）
                # 盈利
                "roe": float(row.get("ROEJQ", 0) or 0),
                "gross_margin": float(row.get("XSMLL", 0) or 0),
                "net_margin": float(row.get("XSJLL", 0) or 0),
                # 成长
                "revenue_growth": float(row.get("YYZSRGDHBZC", 0) or 0),
                "profit_growth": float(row.get("NETPROFITRPHBZC", 0) or 0),
                # 每股
                "eps": float(row.get("EPSJB", 0) or 0),
                "bps": float(row.get("BPS", 0) or 0),
                "ocf_per_share": float(row.get("MGJYXJJE", 0) or 0),
                # 报告期
                "report_date": str(row.get("REPORT_DATE", "")),
            }
        except Exception as e:
            print(f"AKShare 财务数据获取失败({code}): {e}")
            return None
