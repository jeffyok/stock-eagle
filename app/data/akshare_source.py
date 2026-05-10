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
            df = self._ak_retry(ak.stock_zh_a_spot_em)
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
        ak_records = None  # 必须在 try 外初始化，防止 UnboundLocalError
        try:
            market = code[:2]  # sh/sz/bj
            stock_code = code[2:]
            df = self._ak_retry(ak.stock_zh_a_hist,
                symbol=stock_code,
                period="daily",
                start_date=start.replace("-", ""),
                end_date=end.replace("-", ""),
                adjust="qfq",  # 前复权
            )
            if not df.empty:
                ak_records = self._parse_ak_daily(df)
        except Exception as e:
            print(f"[AKShare] 历史日线获取失败({code}): {e}，尝试 westock-data 降级…")

        # 校验主源数据的日期范围是否覆盖请求范围
        # 注意：结束日期允许比请求日期早最多 5 个自然日（周末/节假日无交易数据）
        if ak_records:
            from datetime import datetime as _dt
            dates = [r["date"] for r in ak_records]
            data_start = min(dates).replace("-", "")
            data_end   = max(dates).replace("-", "")
            s_ymd = start.replace("-", "")
            e_ymd = end.replace("-", "")
            # 结束日期：data_end 允许比 e_ymd 早最多 5 天（周末/节假日）
            e_dt = _dt.strptime(e_ymd, "%Y%m%d")
            data_end_dt = _dt.strptime(data_end, "%Y%m%d")
            end_gap = (e_dt - data_end_dt).days
            if data_start > s_ymd or end_gap > 5:
                print(f"[AKShare] 数据范围不足({code}): 请求 {s_ymd}~{e_ymd}，"
                      f"实际 {data_start}~{data_end}，尝试 westock-data 降级…")
                ak_records = None
        if ak_records:
            return ak_records

        # ── 降级：westock-data K线 ────────────────────────────────
        ws_records = None
        try:
            from app.data.westock_data import WestockData
            from datetime import datetime
            s = datetime.strptime(start.replace("-", ""), "%Y%m%d")
            e = datetime.strptime(end.replace("-", ""), "%Y%m%d")
            days = (e - s).days
            count = max(int(days * 1.5), 365)
            records = WestockData().kline(code, period="day", count=count)
            # westock-data 返回 YYYY-MM-DD，转换为 YYYYMMDD 后按日期过滤
            def _to_ymd(d: str) -> str:
                return d.replace("-", "").replace("/", "")
            s_ymd = start.replace("-", "")
            e_ymd = end.replace("-", "")
            filtered = [r for r in records if s_ymd <= _to_ymd(r.get("date", "")) <= e_ymd]
            filtered.sort(key=lambda r: _to_ymd(r.get("date", "")))
            ws_records = filtered if filtered else records
        except Exception as e:
            print(f"[westock-data] 降级失败({code}): {e}")

        # 校验 westock-data 数据日期范围是否覆盖请求范围
        if ws_records:
            from datetime import datetime as _dt
            dates = [r["date"].replace("-", "").replace("/", "") for r in ws_records]
            ws_start = min(dates)
            ws_end   = max(dates)
            s_ymd = start.replace("-", "")
            e_ymd = end.replace("-", "")
            e_dt = _dt.strptime(e_ymd, "%Y%m%d")
            ws_end_dt = _dt.strptime(ws_end, "%Y%m%d")
            end_gap = (e_dt - ws_end_dt).days
            if ws_start <= s_ymd and end_gap <= 5:
                return ws_records
            print(f"[westock-data] 数据范围不足({code}): 请求 {s_ymd}~{e_ymd}，"
                  f"实际 {ws_start}~{ws_end}，尝试 Baostock 降级…")
        else:
            print(f"[westock-data] 无数据({code})，尝试 Baostock 降级…")

        # ── 最终降级：Baostock ─────────────────────────────────────
        try:
            import baostock as bs
            import pandas as pd
            bs.login()
            # Baostock 代码格式：sh.603009
            bs_code = f"{code[:2]}.{code[2:]}"
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,code,open,high,low,close,volume,amount",
                start_date=start,
                end_date=end,
                frequency="d",
                adjustflag="2",  # 2=前复权
            )
            rows = []
            while rs.next():
                rows.append(rs.get_row_data())
            bs.logout()
            if not rows:
                print(f"[Baostock] 无数据({code})")
                return []
            # 转换为统一格式
            records = []
            for row in rows:
                records.append({
                    "date":       row[0],  # date
                    "open":       float(row[2]),
                    "close":      float(row[5]),
                    "high":       float(row[3]),
                    "low":        float(row[4]),
                    "volume":     int(row[6]),
                    "amount":     float(row[7]),
                    "pct_chg":   0.0,  # Baostock 不含涨跌幅，由调用方计算
                    "turnover":  0.0,
                })
            print(f"[Baostock] 获取成功({code}): {len(records)} 条，"
                  f"{records[0]['date']} ~ {records[-1]['date']}")
            return records
        except Exception as e:
            print(f"[Baostock] 降级也失败({code}): {e}")
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
            df = self._ak_retry(ak.stock_info_a_code_name)
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

    def _ak_retry(self, func, *args, retries: int = 3, base_delay: float = 2.0, **kwargs):
        """
        带重试 + 指数退避的 AKShare 调用
        - 处理 RemoteDisconnected、ConnectionAborted 等临时网络故障
        - 每次重试等待 base_delay * 2^attempt 秒（2s → 4s → 8s）
        """
        import time
        last_err = None
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                # 只对网络相关错误重试，代码/数据类错误直接抛
                is_network = any(kw in err_str for kw in [
                    "remote end closed", "connection aborted",
                    "connection reset", "connection refused",
                    "timeout", "read timed out", "max retries",
                    "temporarily unavailable",
                ])
                if is_network and attempt < retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"  ⚠ AKShare 网络波动（{attempt+1}/{retries}），{delay:.1f}s 后重试: {e}")
                    time.sleep(delay)
                else:
                    break
        raise last_err

    def get_sector_spot(self) -> List[Dict]:
        """获取板块实时行情"""
        # ── 主源：AKShare（带重试）──────────────────────────────────
        try:
            df = self._ak_retry(ak.stock_board_industry_name_em)
            if df is None or df.empty:
                raise ValueError("返回空数据")
            df = df.rename(columns={
                "板块代码": "sector_code",
                "板块名称": "sector_name",
                "涨跌幅": "pct_chg",
                "总市值": "total_market",
            })
            records = df.to_dict("records")
            for r in records:
                r["pct_chg"] = self._safe_float(r.get("pct_chg", 0))
                r["total_market"] = self._safe_float(r.get("total_market", 0))
            records.sort(key=lambda x: x.get("pct_chg", 0), reverse=True)
            return records
        except Exception as e:
            print(f"AKShare 板块行情获取失败: {e}，降级到 westock-data…")

        # ── 降级：westock-data ─────────────────────────────────────
        try:
            from app.data.westock_data import WestockData
            data = WestockData().board()
            if data and "sector" in data:
                records = []
                for item in data["sector"]:
                    if item.get("name") == "name":
                        continue
                    try:
                        records.append({
                            "sector_code": "",
                            "sector_name": item.get("name", ""),
                            "pct_chg": self._safe_float(item.get("changePct", 0)),
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
            df = self._ak_retry(ak.stock_individual_fund_flow_rank, indicator="今日")
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
            df = ak.stock_lhb_detail_em(start_date=date_fmt, end_date=date_fmt)
            if df is None or getattr(df, "empty", True) or df.empty:
                return []

            # AKShare 列名兼容：新版本前缀"龙虎榜"，旧版本无前缀
            col_map = {}
            for target, candidates in [
                ("buy", ["龙虎榜买入额", "买入额"]),
                ("sell", ["龙虎榜卖出额", "卖出额"]),
                ("net", ["龙虎榜净买额", "净额"]),
            ]:
                for c in candidates:
                    if c in df.columns:
                        col_map[target] = c
                        break

            records = []
            for _, row in df.iterrows():
                records.append({
                    "code": str(row.get("代码", "")),
                    "name": str(row.get("名称", "")),
                    "reason": str(row.get("上榜原因", "")),
                    "buy_amount": self._safe_float(row.get(col_map.get("buy", ""), 0)),
                    "sell_amount": self._safe_float(row.get(col_map.get("sell", ""), 0)),
                    "net_amount": self._safe_float(row.get(col_map.get("net", ""), 0)),
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
        主力源：akshare stock_fund_flow_individual（即时资金流，5000+股票）
        """

        def _parse_amount(val) -> float:
            """解析 '3.55亿' / '9937.50万' 格式"""
            if val is None or val == '-' or val == '':
                return 0.0
            try:
                s = str(val).strip().replace('%', '')
                if '亿' in s:
                    return float(s.replace('亿', '')) * 1e8
                elif '万' in s:
                    return float(s.replace('万', '')) * 1e4
                else:
                    return float(s)
            except (ValueError, TypeError):
                return 0.0

        def _parse_pct(val) -> float:
            """解析 '20.01%' -> 20.01"""
            if val is None:
                return 0.0
            try:
                return float(str(val).replace('%', ''))
            except (ValueError, TypeError):
                return 0.0

        # ── 主源：AKShare stock_fund_flow_individual（即时，5000+股票）──
        try:
            df = self._ak_retry(ak.stock_fund_flow_individual, symbol='即时')
            if df is None or df.empty:
                raise ValueError("返回空数据")
            records = []
            for _, row in df.iterrows():
                records.append({
                    "code": str(row.get("股票代码", "")),
                    "name": str(row.get("股票简称", "")),
                    "close": self._safe_float(row.get("最新价", 0)),
                    "pct_chg": _parse_pct(row.get("涨跌幅", 0)),
                    "net_mf": _parse_amount(row.get("净额", 0)),        # 净额：正=流入
                    "net_mf_pct": 0.0,
                    "net_mf_big": 0.0,
                    "net_mf_small": 0.0,
                })
            records.sort(key=lambda x: x["net_mf"], reverse=True)
            return records
        except Exception as e:
            print(f"AKShare stock_fund_flow_individual 获取失败: {e}，降级到 westock-data…")

        # ── 降级：westock-data hot() 价格 + asfund() 资金流向 ──
        try:
            from app.data.westock_data import WestockData
            w = WestockData()
            hot_data = w.hot()
            records = []
            for item in hot_data[:30]:
                code = str(item.get("code", ""))
                if code.startswith(("sz", "sh", "bj")):
                    mf = 0.0
                    mf_big = 0.0
                    mf_small = 0.0
                    try:
                        fund_data = w.asfund(code)
                        if fund_data:
                            mf = fund_data.get("net_mf", 0) or 0
                            mf_big = fund_data.get("net_mf_big", 0) or 0
                            mf_small = fund_data.get("net_mf_small", 0) or 0
                    except Exception:
                        pass
                    records.append({
                        "code": code,
                        "name": item.get("name", ""),
                        "close": float(item.get("price", 0)),
                        "pct_chg": float(item.get("pct_chg", 0)),
                        "net_mf": mf,
                        "net_mf_pct": 0.0,
                        "net_mf_big": mf_big,
                        "net_mf_small": mf_small,
                    })
            records.sort(key=lambda x: x["net_mf"], reverse=True)
            return records
        except Exception as e:
            print(f"westock-data 降级也失败: {e}")

        return []

    def get_industry_fund_flow(self, top_n: int = 20) -> List[Dict]:
        """
        获取行业资金流向排行（今日）
        返回：[{name, change_pct, inflow, outflow, net_flow, company_count, leader, leader_pct}]
        单位统一为亿元
        """
        import akshare as ak

        def _parse_amount(val) -> float:
            """解析 '296.00亿' / '144.23万' 格式"""
            if val is None or val == '-' or val == '':
                return 0.0
            try:
                s = str(val).strip()
                if '亿' in s:
                    return float(s.replace('亿', ''))
                elif '万' in s:
                    return float(s.replace('万', '')) / 10000
                else:
                    return float(s)
            except (ValueError, TypeError):
                return 0.0

        try:
            df = self._ak_retry(ak.stock_fund_flow_industry, symbol='即时')
            if df is None or df.empty:
                raise ValueError("返回空数据")

            records = []
            for _, row in df.iterrows():
                records.append({
                    "name":         str(row.get("行业", "")),
                    "change_pct":   self._safe_float(row.get("行业-涨跌幅", 0)),
                    "inflow":       _parse_amount(row.get("流入资金", 0)),
                    "outflow":      _parse_amount(row.get("流出资金", 0)),
                    "net_flow":     _parse_amount(row.get("净额", 0)),
                    "company_count": int(row.get("公司家数", 0) or 0),
                    "leader":       str(row.get("领涨股", "")),
                    "leader_pct":   self._safe_float(row.get("领涨股-涨跌幅", 0)),
                })

            # 按净额降序
            records.sort(key=lambda x: x["net_flow"], reverse=True)
            return records[:top_n]
        except Exception as e:
            print(f"行业资金流向获取失败: {e}")
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
            df = self._ak_retry(ak.stock_board_concept_name_em)
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

        def _parse_amount(val) -> float:
            if val is None or val == '-' or val == '':
                return 0.0
            try:
                s = str(val).strip()
                if '亿' in s:
                    return float(s.replace('亿', ''))
                elif '万' in s:
                    return float(s.replace('万', '')) / 10000
                else:
                    return float(s)
            except (ValueError, TypeError):
                return 0.0

        # ── 主源：AKShare（带重试）─────────────────────────────────
        try:
            if sector_type == "industry":
                df = self._ak_retry(ak.stock_fund_flow_industry, symbol='今日')
            else:
                df = self._ak_retry(ak.stock_fund_flow_concept, symbol='今日')
            if df is None or getattr(df, "empty", False) or df.empty:
                raise ValueError("返回空数据")
            col_name = "行业" if sector_type == "industry" else "概念"
            col_pct = "行业-涨跌幅" if sector_type == "industry" else "概念-涨跌幅"
            records = []
            for _, row in df.iterrows():
                records.append({
                    "sector_name": str(row.get(col_name, "")),
                    "pct_chg": self._safe_float(row.get(col_pct, 0)),
                    "net_mf": _parse_amount(row.get("净额", 0)),
                    "net_mf_pct": 0.0,
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
        """获取北向资金流向（近 N 日）
        
        优先使用 stock_hsgt_fund_flow_summary_em 获取今日数据
        注意：stock_hsgt_hist_em 接口自2024年8月起数据为空
        返回字段：date(日期), north_net(净流入，元), north_index(指数涨跌幅)
        """
        import akshare as ak
        import pandas as pd
        from datetime import datetime, timedelta
        
        # ── 主源：stock_hsgt_fund_flow_summary_em（获取今日数据） ─────
        try:
            df = self._ak_retry(ak.stock_hsgt_fund_flow_summary_em)
            if df is None or getattr(df, "empty", True) or df.empty:
                raise ValueError("返回空数据")
            
            # 筛选北向资金数据（沪股通 + 深股通）
            north_df = df[
                (df["资金方向"] == "北向") & 
                (df["板块"].isin(["沪股通", "深股通"]))
            ]
            
            if north_df.empty:
                raise ValueError("没有找到北向资金数据")
            
            # 按板块汇总北向资金
            total_net = 0.0
            for _, row in north_df.iterrows():
                net_val = row.get("成交净买额") or 0
                if pd.notna(net_val):
                    total_net += float(net_val)
            
            # 获取指数涨跌幅
            index_pct = 0.0
            for _, row in north_df.iterrows():
                pct = row.get("指数涨跌幅") or 0
                if pd.notna(pct):
                    index_pct = float(pct)
                    break
            
            today = datetime.now().strftime("%Y-%m-%d")
            return [{
                "date": today,
                "north_net": total_net * 1e8,  # 转换为元
                "north_index": index_pct,
            }]
        except Exception as e:
            print(f"北向资金获取失败: {e}")

        # ── 降级：尝试 stock_hsgt_hist_em ─────────────────────────
        try:
            df = self._ak_retry(ak.stock_hsgt_hist_em, symbol="北向资金")
            if df is None or getattr(df, "empty", True) or df.empty:
                raise ValueError("返回空数据")
            
            df["日期"] = pd.to_datetime(df["日期"])
            df = df.sort_values("日期", ascending=False).head(days)
            records = []
            for _, row in df.iterrows():
                net_val = row.get("当日成交净买额")
                idx_val = row.get("沪深300")
                records.append({
                    "date": str(row["日期"].date()),
                    "north_net": float(net_val) * 1e8 if pd.notna(net_val) else 0.0,
                    "north_index": float(idx_val) if pd.notna(idx_val) else 0.0,
                })
            return records
        except Exception as e:
            print(f"AKShare 北向资金（备用）获取失败: {e}")

        # ── 降级：返回空列表 ────────────────────────────────────
        print("警告：北向资金数据源暂不可用")
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
            df = self._ak_retry(ak.stock_hot_rank_em)
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
            df = self._ak_retry(ak.stock_hot_rank_em)
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
            df = self._ak_retry(ak.stock_hot_search_baidu, symbol=date)
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
