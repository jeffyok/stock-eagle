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
        """获取历史日线（AKShare 主源，westock-data 降级）"""
        # ── 主源：AKShare ────────────────────────────────────────
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
            if not df.empty:
                return self._parse_ak_daily(df)
        except Exception as e:
            print(f"[AKShare] 历史日线获取失败({code}): {e}，尝试 westock-data 降级…")

        # ── 降级：westock-data K线 ────────────────────────────────
        try:
            from app.data.westock_data import WestockData
            # 计算需要的条数（自然日→交易日 约 0.67 倍，最少 30 条）
            from datetime import datetime
            s = datetime.strptime(start.replace("-", ""), "%Y%m%d")
            e = datetime.strptime(end.replace("-", ""), "%Y%m%d")
            days = (e - s).days
            count = max(days * 2 // 3, 30)
            records = WestockData().kline(code, period="day", count=count)
            # westock-data 返回 YYYY-MM-DD，转换为 YYYYMMDD 后按日期过滤
            def _to_ymd(d: str) -> str:
                return d.replace("-", "").replace("/", "")
            s_ymd = start.replace("-", "")
            e_ymd = end.replace("-", "")
            filtered = [r for r in records if s_ymd <= _to_ymd(r.get("date", "")) <= e_ymd]
            # 按日期升序排序（从旧到新）
            filtered.sort(key=lambda r: _to_ymd(r.get("date", "")))
            return filtered if filtered else records
        except Exception as e:
            print(f"[westock-data] 降级也失败({code}): {e}")
            return []

    @staticmethod
    def _parse_ak_daily(df) -> List[Dict]:
        """解析 AKShare 历史日线 DataFrame"""
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
        """获取板块实时行情（优化：to_dict 替代 iterrows）"""
        # ── 主源：AKShare ────────────────────────────────────────
        try:
            df = ak.stock_board_industry_name_em()
            if df.empty:
                raise ValueError("返回空数据")
            df = df.rename(columns={
                "板块代码": "sector_code",
                "板块名称": "sector_name",
                "涨跌幅": "pct_chg",
                "总市值": "total_market",
            })
            records = df.to_dict("records")
            for r in records:
                r["pct_chg"] = float(r.get("pct_chg", 0))
                r["total_market"] = float(r.get("total_market", 0))
            records.sort(key=lambda x: x.get("pct_chg", 0), reverse=True)
            return records
        except Exception as e:
            print(f"AKShare 板块行情获取失败: {e}，降级到 westock-data…")

        # ── 降级：westock-data ────────────────────────────────
        try:
            from app.data.westock_data import WestockData
            data = WestockData().board()
            if data and "sector" in data:
                records = []
                for item in data["sector"]:
                    # 跳过表头行
                    if item.get("name") == "name":
                        continue
                    try:
                        records.append({
                            "sector_code": "",
                            "sector_name": item.get("name", ""),
                            "pct_chg": float(item.get("changePct", 0)),
                            "total_market": 0,
                        })
                    except (ValueError, TypeError):
                        continue
                records.sort(key=lambda x: x.get("pct_chg", 0), reverse=True)
                return records
        except Exception as e:
            print(f"westock-data 板块行情也失败: {e}")

        return []

    def get_money_flow(self, code: str) -> Optional[Dict]:
        """获取个股资金流向"""
        try:
            stock_code = code[2:]
            df = ak.stock_individual_fund_flow_rank(indicator="今日")
            if df is None or df.empty:
                raise ValueError("返回空数据")
            row = df[df["代码"] == stock_code]
            if row.empty:
                return None
            r = row.iloc[0]
            return {
                "code": code,
                "net_mf": float(r.get("今日主力净流入-净额", 0)),
                "net_mf_big": float(r.get("今日超大单净流入-净额", 0)),
                "net_mf_small": float(r.get("今日小单净流入-净额", 0)),
            }
        except Exception as e:
            print(f"AKShare 资金流向获取失败: {e}，降级到 westock-data…")

        # ── 降级：westock-data ────────────────────────────────
        try:
            from app.data.westock_data import WestockData
            chip = WestockData().chip(code)
            if chip and "close" in chip:
                return {
                    "code": code,
                    "net_mf": 0,
                    "net_mf_big": 0,
                    "net_mf_small": 0,
                }
        except Exception:
            pass

        return None

    def get_dragon_tiger(self, date: str) -> List[Dict]:
        """
        获取龙虎榜数据（单日）
        date: 格式 YYYYMMDD 或 YYYY-MM-DD
        """
        try:
            date_fmt = date.replace("-", "")
            # stock_lhb_detail_em 参数为 start_date/end_date
            df = ak.stock_lhb_detail_em(start_date=date_fmt, end_date=date_fmt)
            if df is None or df.empty:
                return []
            records = []
            for _, row in df.iterrows():
                records.append({
                    "code": str(row.get("代码", "")),
                    "name": str(row.get("名称", "")),
                    "reason": str(row.get("上榜原因", "")),
                    "buy_amount": self._safe_float(row.get("买入额", 0)),
                    "sell_amount": self._safe_float(row.get("卖出额", 0)),
                    "net_amount": self._safe_float(row.get("净额", 0)),
                })
            return records
        except Exception as e:
            print(f"AKShare 龙虎榜获取失败: {e}")
            return []

    def get_lhb_active_brokers(self, date: str = None) -> List[Dict]:
        """
        获取龙虎榜活跃营业部（来自东方财富）
        返回字段：营业部名称、上榜日、买入个股数、卖出个股数、总买卖净额、买入股票
        date: 可选，格式 YYYYMMDD 或 YYYY-MM-DD，用于过滤上榜日
        """
        try:
            import pandas as pd
            df = ak.stock_lhb_hyyyb_em()
            if df is None or df.empty:
                return []
            records = []
            for _, row in df.iterrows():
                record = {
                    "broker_name": str(row.get("营业部名称", "")),
                    "list_date": str(row.get("上榜日", "")),
                    "buy_stocks": int(row.get("买入个股数", 0)),
                    "sell_stocks": int(row.get("卖出个股数", 0)),
                    "buy_amount": self._safe_float(row.get("买入总金额", 0)),
                    "sell_amount": self._safe_float(row.get("卖出总金额", 0)),
                    "net_amount": self._safe_float(row.get("总买卖净额", 0)),
                    "stocks": str(row.get("买入股票", "")),
                    "broker_code": str(row.get("营业部代码", "")),
                }
                # 按日期过滤（如果指定了 date）
                if date:
                    date_norm = date.replace("-", "")
                    rec_date = record["list_date"].replace("-", "")
                    if rec_date != date_norm:
                        continue
                records.append(record)
            return records
        except Exception as e:
            print(f"AKShare 活跃营业部获取失败: {e}")
            return []

    def get_stock_money_flow_rank(self, indicator: str = "今日") -> List[Dict]:
        """
        获取个股资金流向排行榜
        indicator: '今日' | '3日' | '5日' | '10日'
        兼容带"排行"后缀的旧格式：'3日排行' -> '3日'
        """
        _indicator_map = {
            "今日": "今日",
            "3日排行": "3日",
            "5日排行": "5日",
            "10日排行": "10日",
            "3日": "3日",
            "5日": "5日",
            "10日": "10日",
        }
        ak_indicator = _indicator_map.get(indicator, indicator)
        prefix = ak_indicator

        # ── 主源：AKShare ────────────────────────────────────────
        try:
            df = ak.stock_individual_fund_flow_rank(indicator=ak_indicator)
            if df is None or df.empty:
                raise ValueError("返回空数据")
            records = []
            for _, row in df.iterrows():
                records.append({
                    "code": str(row.get("代码", "")),
                    "name": str(row.get("名称", "")),
                    "close": self._safe_float(row.get("最新价", 0)),
                    "pct_chg": self._safe_float(row.get(f"{prefix}涨跌幅", 0)),
                    "net_mf": self._safe_float(row.get(f"{prefix}主力净流入-净额", 0)),
                    "net_mf_pct": self._safe_float(row.get(f"{prefix}主力净流入-净占比", 0)),
                    "net_mf_big": self._safe_float(row.get(f"{prefix}超大单净流入-净额", 0)),
                    "net_mf_small": self._safe_float(row.get(f"{prefix}小单净流入-净额", 0)),
                })
            records.sort(key=lambda x: x["net_mf"], reverse=True)
            return records
        except Exception as e:
            print(f"AKShare 资金流向排行获取失败: {e}，降级到 westock-data…")

        # ── 降级：westock-data chip（取收盘价/涨跌幅）───────
        try:
            from app.data.westock_data import WestockData
            w = WestockData()
            hot_data = w.hot()
            records = []
            for item in hot_data[:30]:
                code = str(item.get("code", ""))
                if code.startswith(("sz", "sh", "bj")):
                    records.append({
                        "code": code,
                        "name": item.get("name", ""),
                        "close": float(item.get("price", 0)),
                        "pct_chg": float(item.get("pct_chg", 0)),
                        "net_mf": 0,
                        "net_mf_pct": 0,
                        "net_mf_big": 0,
                        "net_mf_small": 0,
                    })
            # 按涨跌幅排序
            records.sort(key=lambda x: x["pct_chg"], reverse=True)
            return records
        except Exception as e:
            print(f"westock-data 降级也失败: {e}")

        return []

    @staticmethod
    def _safe_float(val, default: float = 0.0) -> float:
        """安全转 float，容忍 '-' 等无效字符"""
        if val is None:
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

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

    # --- 基金相关 ---

    def get_fund_rank(self) -> List[Dict]:
        """
        获取开放式基金排行数据（全量，不做类型过滤）
        数据来源：东方财富 fund_open_fund_rank_em()
        返回字段：code, name, nav, nav_acc, pct_chg_1d,
                 return_1w/1m/3m/6m/1y/2y/3y/ytd/total
        """
        try:
            df = ak.fund_open_fund_rank_em()
            if df.empty:
                return []
            records = []
            for _, row in df.iterrows():
                # 将收益率字段转为数值，无法解析的设为 None
                def _to_float(val):
                    try:
                        return float(val)
                    except Exception:
                        return None

                records.append({
                    "code":        str(row.get("基金代码", "")),
                    "name":        str(row.get("基金简称", "")),
                    "nav":         float(row.get("单位净值", 0) or 0),
                    "nav_acc":     float(row.get("累计净值", 0) or 0),
                    "pct_chg_1d":  _to_float(row.get("日增长率")),
                    "return_1w":   _to_float(row.get("近1周")),
                    "return_1m":   _to_float(row.get("近1月")),
                    "return_3m":   _to_float(row.get("近3月")),
                    "return_6m":   _to_float(row.get("近6月")),
                    "return_1y":   _to_float(row.get("近1年")),
                    "return_2y":   _to_float(row.get("近2年")),
                    "return_3y":   _to_float(row.get("近3年")),
                    "return_ytd":  _to_float(row.get("今年来")),
                    "return_total": _to_float(row.get("成立来")),
                })
            return records
        except Exception as e:
            print(f"AKShare 基金排行获取失败: {e}")
            return []

    def get_fund_nav_history(self, code: str, years: int = 1) -> List[Dict]:
        """
        获取单只基金历史净值（最近 N 年）
        AKShare 接口：fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        """
        try:
            df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
            if df.empty:
                return []
            df["净值日期"] = pd.to_datetime(df["净值日期"])
            cutoff = pd.Timestamp.now() - pd.Timedelta(days=365 * years)
            df = df[df["净值日期"] >= cutoff]
            records = []
            for _, row in df.iterrows():
                records.append({
                    "date":    str(row["净值日期"].date()),
                    "nav":     float(row.get("单位净值", 0) or 0),
                    "nav_acc": float(row.get("累计净值", 0) or 0),
                    "pct_chg": float(row.get("日增长率", 0) or 0),
                })
            return records
        except Exception as e:
            print(f"AKShare 基金净值历史获取失败({code}): {e}")
            return []

    # ─── 板块/概念 ───────────────────────────────────────────────────────

    def get_concept_sectors(self) -> List[Dict]:
        """获取概念板块实时行情（优化：to_dict 替代 iterrows）"""
        import akshare as ak

        # ── 主源：AKShare ────────────────────────────────────────
        try:
            df = ak.stock_board_concept_name_em()
            if df.empty:
                raise ValueError("返回空数据")
            df = df.rename(columns={
                "板块代码": "sector_code",
                "板块名称": "sector_name",
                "涨跌幅": "pct_chg",
                "总市值": "total_market",
            })
            records = df.to_dict("records")
            for r in records:
                r["pct_chg"] = float(r.get("pct_chg", 0))
                r["total_market"] = float(r.get("total_market", 0) or 0)
            records.sort(key=lambda x: x["pct_chg"], reverse=True)
            return records
        except Exception as e:
            print(f"AKShare 概念板块获取失败: {e}，降级到 westock-data…")

        # ── 降级：westock-data ────────────────────────────────
        try:
            from app.data.westock_data import WestockData
            data = WestockData().board()
            if data and "concept" in data:
                records = []
                for item in data["concept"]:
                    # 跳过表头行
                    if item.get("name") == "name":
                        continue
                    try:
                        records.append({
                            "sector_code": "",
                            "sector_name": item.get("name", ""),
                            "pct_chg": float(item.get("changePct", 0)),
                            "total_market": 0,
                        })
                    except (ValueError, TypeError):
                        continue
                records.sort(key=lambda x: x.get("pct_chg", 0), reverse=True)
                return records
        except Exception as e:
            print(f"westock-data 概念板块也失败: {e}")

        return []

    def get_sector_money_flow(self, sector_type: str = "industry") -> List[Dict]:
        """获取板块资金流向排行"""
        import akshare as ak

        # ── 主源：AKShare ────────────────────────────────────────
        try:
            if sector_type == "industry":
                df = ak.stock_board_industry_fund_flow_rank_em()
            else:
                df = ak.stock_board_concept_fund_flow_rank_em()
            if df.empty:
                raise ValueError("返回空数据")
            records = []
            for _, row in df.iterrows():
                records.append({
                    "sector_name": str(row.get("名称", "")),
                    "pct_chg": float(row.get("今日涨跌幅", 0) or 0),
                    "net_mf": float(row.get("今日主力净流入-净额", 0) or 0),
                    "net_mf_pct": float(row.get("今日主力净流入-净占比", 0) or 0),
                })
            records.sort(key=lambda x: x["net_mf"], reverse=True)
            return records
        except Exception as e:
            print(f"AKShare 板块资金流获取失败: {e}，降级到 westock-data…")

        # ── 降级：westock-data ────────────────────────────────
        try:
            from app.data.westock_data import WestockData
            data = WestockData().board()
            if data and "sector_fund" in data:
                records = []
                for item in data["sector_fund"]:
                    # 跳过表头行
                    if item.get("name") == "name":
                        continue
                    try:
                        net_str = item.get("mainNetInflow", "0")
                        net_val = float(net_str) if net_str else 0.0
                        records.append({
                            "sector_name": item.get("name", ""),
                            "pct_chg": float(item.get("changePct", 0)),
                            "net_mf": net_val,
                            "net_mf_pct": 0.0,  # westock-data 无此字段
                        })
                    except (ValueError, TypeError):
                        continue
                records.sort(key=lambda x: x["net_mf"], reverse=True)
                return records
        except Exception as e:
            print(f"westock-data 板块资金流也失败: {e}")

        return []

    # ─── 北向资金 ───────────────────────────────────────────────────────

    def get_north_money_flow(self, days: int = 5) -> List[Dict]:
        """获取北向资金流向（近 N 日），使用 stock_hsgt_hist_em(symbol="北向资金")
        实际列名：日期, 当日成交净买额(亿), 沪深300(收盘指数)
        """
        import akshare as ak
        import pandas as pd

        # ── 主源：AKShare ────────────────────────────────────────
        try:
            df = ak.stock_hsgt_hist_em(symbol="北向资金")
            if df is None or getattr(df, "empty", True) or df.empty:
                raise ValueError("返回空数据")
            df["日期"] = pd.to_datetime(df["日期"])
            df = df.sort_values("日期", ascending=False).head(days)
            records = []
            for _, row in df.iterrows():
                net_val = row.get("当日成交净买额") or 0
                idx_val = row.get("沪深300") or 0
                records.append({
                    "date": str(row["日期"].date()),
                    "north_net": float(net_val) * 1e8 if pd.notna(net_val) else 0.0,
                    "north_index": float(idx_val) if pd.notna(idx_val) else 0.0,
                })
            return records
        except Exception as e:
            print(f"AKShare 北向资金获取失败: {e}，降级到 westock-data…")

        # ── 降级：暂时返回模拟数据 ───────────────────────────────
        # 注：westock-data 无直接北向资金接口，返回空列表
        print("警告：无北向资金降级数据源")
        return []

    # ─── 热搜 ─────────────────────────────────────────────────────────

    def get_hot_search_tencent(self) -> List[Dict]:
        """
        腾讯自选股热搜 Top 50
        优先 westock-data（腾讯数据源），失败时降级到东方财富人气榜
        """
        # 优先用 westock-data 腾讯原生接口
        try:
            from app.data.westock_data import WestockData
            records = WestockData().hot()
            if records:
                # 添加排名
                for i, r in enumerate(records, 1):
                    r["rank"] = i
                return records[:50]
        except Exception:
            pass

        # 降级到东方财富人气榜
        try:
            import akshare as ak
            df = ak.stock_hot_rank_em()
            if df is None or df.empty:
                return []
            records = []
            for idx, row in df.iterrows():
                records.append({
                    "rank": idx + 1,
                    "code": str(row.get("代码", "")),
                    "name": str(row.get("股票名称", "")),
                    "pct_chg": float(row.get("涨跌幅", 0) or 0),
                })
            return records[:20]
        except Exception as e:
            print(f"AKShare 腾讯热搜获取失败: {e}")
            return []

    def get_hot_search_eastmoney(self) -> List[Dict]:
        """东方财富个股热搜 Top 20"""
        import akshare as ak

        try:
            df = ak.stock_hot_rank_em()
            if df is None or df.empty:
                return []
            records = []
            for _, row in df.iterrows():
                records.append({
                    "code": str(row.get("代码", "")),
                    "name": str(row.get("名称", "")),
                    "pct_chg": float(row.get("涨跌幅", 0) or 0),
                })
            return records[:20]
        except Exception as e:
            print(f"AKShare 东方财富热搜获取失败: {e}")
            return []

    def get_hot_search_baidu(self, date: str = None) -> List[Dict]:
        """百度股票热搜"""
        import akshare as ak

        try:
            if date is None:
                import datetime
                date = datetime.datetime.now().strftime("%Y%m%d")
            df = ak.stock_hot_search_baidu(symbol=date)
            if df is None or df.empty:
                return []
            records = []
            for _, row in df.iterrows():
                records.append({
                    "keyword": str(row.get("关键词", "")),
                    "hot_index": float(row.get("热度指数", 0) or 0),
                })
            return records[:20]
        except Exception as e:
            print(f"AKShare 百度热搜获取失败: {e}")
            return []
