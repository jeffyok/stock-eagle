"""
腾讯自选股 westock-data 数据源
覆盖 K线、技术指标、资金流向、龙虎榜、筹码、板块等

依赖：npx + westock-data-skillhub
代码格式：沪市 sh / 深市 sz / 港股 hk / 美股 us
"""
import subprocess
import json
import re
from typing import Any, Dict, List, Optional


def _parse_table(raw: str) -> List[Dict]:
    """
    解析 westock-data 返回的 markdown 表格格式。
    跳过 XML/CLIXML 元数据行，只保留 | 分隔的表格行。
    """
    lines = raw.strip().split("\n")
    rows = []
    headers = []
    for line in lines:
        line = line.strip()
        # 跳过元数据行
        if line.startswith("<Objs") or line.startswith("#") or line.startswith("**"):
            continue
        cols = [c.strip() for c in line.split("|")]
        # 跳过分隔行：| --- | --- | ...（只检查非空列）
        non_empty = [c for c in cols if c]
        if non_empty and all(c.startswith("-") for c in non_empty):
            continue
        # 有效行必须以 | 开头和结尾
        if len(cols) < 3:
            continue
        # 第一行作为表头（去掉首尾空列）
        if not headers:
            headers = cols[1:-1]
            continue
        # 数据行：去掉首尾空列后对齐表头
        vals = cols[1:-1]
        if len(vals) == len(headers):
            rows.append(dict(zip(headers, vals)))
    return rows


def _safe_float(v: Any, default: float = 0.0) -> float:
    """安全转 float"""
    if v is None or v == "" or v == "-":
        return default
    try:
        return float(str(v).replace(",", ""))
    except (ValueError, TypeError):
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    """安全转 int"""
    if v is None or v == "" or v == "-":
        return default
    try:
        return int(float(str(v).replace(",", "")))
    except (ValueError, TypeError):
        return default


class WestockData:
    """
    westock-data 腾讯数据源封装类

    用法示例：
        ws = WestockData()
        ws.kline("sh600519", period="day", count=20)  # 日K
        ws.technical("sh600519", indicator="macd")     # 技术指标
        ws.asfund("sh600519")                          # A股资金流向
        ws.chip("sh600519")                            # 筹码成本
        ws.hot()                                      # 热搜
        ws.board()                                    # 板块
    """

    _TIMEOUT = 30  # 单次调用超时（秒）

    def _call(self, *args: str) -> str:
        """调用 westock-data，返回原始输出字符串"""
        npx_args = " ".join(["--yes", "westock-data-skillhub@latest"] + list(args))
        cmd = ["powershell", "-Command", f"npx {npx_args}"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self._TIMEOUT,
        )
        if result.returncode != 0:
            raise RuntimeError(f"westock-data 调用失败: {result.stderr.strip()}")
        return result.stdout

    # ── 行情 K线 ────────────────────────────────────────────────────────

    def kline(self, code: str, period: str = "day", count: int = 20) -> List[Dict]:
        """
        K线数据
        :param code:  sh600519 / sz000001 / hk00700 / usAAPL
        :param period: day / week / month / 5m / 15m / 30m / 60m
        :param count:  获取条数
        :return: [{date, open, last, high, low, volume, amount, exchange}]
        """
        rows = _parse_table(self._call("kline", code, period, str(count)))
        records = []
        for r in rows:
            records.append({
                "date":    r.get("date", ""),
                "open":    _safe_float(r.get("open")),
                "close":   _safe_float(r.get("last")),
                "high":    _safe_float(r.get("high")),
                "low":     _safe_float(r.get("low")),
                "volume":  _safe_float(r.get("volume")),
                "amount":  _safe_float(r.get("amount")),
                "pct_chg": _safe_float(r.get("exchange")),  # 涨跌幅(%)
            })
        return records

    def minute(self, code: str) -> List[Dict]:
        """
        分时数据
        :return: [{time, price, volume, amount, pct_chg}]
        """
        rows = _parse_table(self._call("minute", code))
        records = []
        for r in rows:
            records.append({
                "time":    r.get("time", ""),
                "price":   _safe_float(r.get("price")),
                "volume":  _safe_float(r.get("volume")),
                "amount":  _safe_float(r.get("amount")),
                "pct_chg": _safe_float(r.get("pct_chg")),
            })
        return records

    # ── 技术指标 ────────────────────────────────────────────────────────

    def technical(self, code: str, indicator: str = "macd") -> List[Dict]:
        """
        技术指标（支持逗号分隔多指标）
        :param indicator: macd / kdj / rsi / boll / bias / wr / dmi / sar /
                          obv / vr / bbi / trix / dpo / psy / enne / cci / amdef
        :return: [{date, closePrice, macd.DIF, macd.DEA, macd.MACD, kdj.K, ...}]
        """
        rows = _parse_table(self._call("technical", code, indicator))
        return rows

    # ── 资金流向 ────────────────────────────────────────────────────────

    def asfund(self, code: str) -> Optional[Dict]:
        """
        A股资金流向（单股）
        :return: {code, name, MainNetFlow, JumboNetFlow, SmallNetFlow, MainInFlow, ...}
        """
        rows = _parse_table(self._call("asfund", code))
        if not rows:
            return None
        r = rows[0]
        # 解析嵌套 JSON
        def _parse_json(key: str) -> Dict:
            raw = r.get(key, "{}")
            try:
                return json.loads(raw)
            except Exception:
                return {}

        lhb = _parse_json("LhbTradingDetails")
        margin = _parse_json("MarginTradeInfos")
        block = _parse_json("BlockTradingInfos")

        return {
            "code":          r.get("SecuCode", r.get("code", "")),
            "close":         _safe_float(r.get("ClosePrice")),
            "last":          _safe_float(r.get("FwdClosePrice")),
            "net_mf":        _safe_float(r.get("MainNetFlow")),
            "net_mf_10d":    _safe_float(r.get("MainNetFlow10D")),
            "net_mf_5d":     _safe_float(r.get("MainNetFlow5D")),
            "net_mf_20d":    _safe_float(r.get("MainNetFlow20D")),
            "net_mf_big":    _safe_float(r.get("JumboNetFlow")),
            "net_mf_small":  _safe_float(r.get("SmallNetFlow")),
            "main_in":       _safe_float(r.get("MainInFlow")),
            "main_out":      _safe_float(r.get("MainOutFlow")),
            "retail_in":     _safe_float(r.get("RetailInFlow")),
            "retail_out":    _safe_float(r.get("RetailOutFlow")),
            "block_trades":  block,
            "lhb_details":   lhb,
            "margin":        margin,
        }

    def hkfund(self, code: str) -> Optional[Dict]:
        """港股资金流向"""
        rows = _parse_table(self._call("hkfund", code))
        if not rows:
            return None
        r = rows[0]
        return {
            "code":       r.get("code", ""),
            "south_net":  _safe_float(r.get("south_net")),
            "south_in":   _safe_float(r.get("south_in")),
            "south_out":  _safe_float(r.get("south_out")),
        }

    def usfund(self, code: str) -> Optional[Dict]:
        """美股做空数据"""
        rows = _parse_table(self._call("usfund", code))
        if not rows:
            return None
        r = rows[0]
        return {
            "code":       r.get("code", ""),
            "short_vol":  _safe_float(r.get("short_vol")),
            "short_ratio": _safe_float(r.get("short_ratio")),
        }

    # ── 龙虎榜 ──────────────────────────────────────────────────────────

    def lhb(self, code: str) -> Dict:
        """
        龙虎榜数据（仅沪深）
        :return: {code, date, reason, buy_list: [{dept, amount}, ...], sell_list: [...]}
        """
        raw = self._call("lhb", code)
        if "当日无龙虎榜数据" in raw or not _parse_table(raw):
            return {"code": code, "date": "", "reason": "", "buy_list": [], "sell_list": []}
        rows = _parse_table(raw)
        return {
            "code":      rows[0].get("code", code),
            "date":      rows[0].get("date", ""),
            "reason":    rows[0].get("reason", ""),
            "buy_list":  [r.get("buy", "") for r in rows if r.get("buy")],
            "sell_list": [r.get("sell", "") for r in rows if r.get("sell")],
        }

    # ── 筹码成本 ────────────────────────────────────────────────────────

    def chip(self, code: str) -> Optional[Dict]:
        """
        筹码成本（仅沪深京A股）
        :return: {code, name, date, closePrice, chipProfitRate, chipAvgCost,
                  chipConcentration90, chipConcentration70}
        """
        rows = _parse_table(self._call("chip", code))
        if not rows:
            return None
        r = rows[0]
        return {
            "code":                r.get("code", ""),
            "name":               r.get("name", ""),
            "date":               r.get("date", ""),
            "close":              _safe_float(r.get("closePrice")),
            "profit_rate":        _safe_float(r.get("chipProfitRate")),
            "avg_cost":           _safe_float(r.get("chipAvgCost")),
            "concentration_90":   _safe_float(r.get("chipConcentration90")),
            "concentration_70":   _safe_float(r.get("chipConcentration70")),
        }

    # ── 股东结构 ────────────────────────────────────────────────────────

    def shareholder(self, code: str) -> List[Dict]:
        """股东结构（A股/港股）"""
        rows = _parse_table(self._call("shareholder", code))
        records = []
        for r in rows:
            records.append({
                "holder":    r.get("holder", ""),
                "hold_num":  _safe_float(r.get("hold_num")),
                "hold_pct":  _safe_float(r.get("hold_pct")),
                "change_pct": _safe_float(r.get("change_pct")),
            })
        return records

    # ── 分红除权 ────────────────────────────────────────────────────────

    def dividend(self, code: str) -> List[Dict]:
        """分红数据"""
        rows = _parse_table(self._call("dividend", code))
        records = []
        for r in rows:
            records.append({
                "date":        r.get("date", ""),
                "dividend":    _safe_float(r.get("dividend")),
                "bonus_share": _safe_float(r.get("bonus_share")),
                "rights_issue": _safe_float(r.get("rights_issue")),
            })
        return records

    # ── ETF ─────────────────────────────────────────────────────────────

    def etf(self, code: str) -> Optional[Dict]:
        """ETF 详情"""
        rows = _parse_table(self._call("etf", code))
        if not rows:
            return None
        r = rows[0]
        return {
            "code":        r.get("code", ""),
            "name":        r.get("name", ""),
            "nav":         _safe_float(r.get("nav")),
            "pct_chg":     _safe_float(r.get("pct_chg")),
            "volume":      _safe_float(r.get("volume")),
            "amount":      _safe_float(r.get("amount")),
        }

    def etf_holdings(self, code: str) -> List[Dict]:
        """ETF 持仓明细"""
        rows = _parse_table(self._call("etf-holdings", code))
        records = []
        for r in rows:
            records.append({
                "code":      r.get("code", ""),
                "name":      r.get("name", ""),
                "hold_pct":  _safe_float(r.get("hold_pct")),
                "num":       _safe_float(r.get("num")),
            })
        return records

    # ── 热搜 ─────────────────────────────────────────────────────────────

    def hot(self) -> List[Dict]:
        """
        腾讯自选股热搜 Top 50
        :return: [{code, name, zdf, zxj, status, stock_type}]
        """
        rows = _parse_table(self._call("hot"))
        records = []
        for r in rows:
            zdf_str = r.get("zdf", "0").strip()
            records.append({
                "code":      r.get("code", ""),
                "name":      r.get("name", ""),
                "pct_chg":   _safe_float(zdf_str),
                "price":     _safe_float(r.get("zxj", "")),
                "status":    r.get("status", ""),
                "stock_type": r.get("stock_type", ""),
            })
        return records

    # ── 板块 ─────────────────────────────────────────────────────────────

    def board(self) -> Dict[str, List[Dict]]:
        """
        行业/概念板块行情
        :return: {
            "sector": [{name, changePct, turnoverRate, leadStock}, ...],
            "concept": [...],
            "sector_fund": [{name, mainNetInflow}, ...]
        }
        """
        raw = self._call("board")
        lines = raw.strip().split("\n")
        sections = {"sector": [], "concept": [], "sector_fund": []}
        current_section = None

        for line in lines:
            line = line.strip()
            if "行业板块涨幅排名" in line:
                current_section = "sector"
                continue
            elif "概念板块涨幅排名" in line:
                current_section = "concept"
                continue
            elif "行业资金流入" in line:
                current_section = "sector_fund"
                continue

            cols = [c.strip() for c in line.split("|")]
            if all(re.match(r"^-+$", c) or c == "" for c in cols):
                continue
            if not cols or len(cols) < 3 or line.startswith("#") or not line.startswith("|"):
                continue
            if current_section is None:
                continue

            vals = [c for c in cols if c]
            headers_map = {
                "sector": ["name", "changePct", "turnoverRate", "changePct5d", "changePct20d", "leadStock"],
                "concept": ["name", "changePct", "turnoverRate", "changePct5d", "changePct20d", "leadStock"],
                "sector_fund": ["name", "changePct", "mainNetInflow", "mainNetInflow5d", "upDownRatio"],
            }
            headers = headers_map.get(current_section, [])
            if len(vals) == len(headers):
                row = dict(zip(headers, vals))
                sections[current_section].append(row)

        return sections

    # ── 投资日历 ────────────────────────────────────────────────────────

    def calendar(self, date: str) -> List[Dict]:
        """投资日历（IPO、财报、派息等）"""
        rows = _parse_table(self._call("calendar", date))
        records = []
        for r in rows:
            records.append({
                "date":    r.get("date", ""),
                "event":   r.get("event", ""),
                "code":    r.get("code", ""),
                "name":    r.get("name", ""),
            })
        return records

    # ── 新股 ─────────────────────────────────────────────────────────────

    def ipo(self, market: str = "hs") -> List[Dict]:
        """新股日历（hs=沪深）"""
        rows = _parse_table(self._call("ipo", market))
        records = []
        for r in rows:
            records.append({
                "code":     r.get("code", ""),
                "name":     r.get("name", ""),
                "ipo_date": r.get("ipo_date", ""),
                "price":    _safe_float(r.get("price")),
                "pe":       _safe_float(r.get("pe")),
            })
        return records

    # ── 业绩预告 ────────────────────────────────────────────────────────

    def reserve(self, code: str) -> List[Dict]:
        """业绩预告"""
        rows = _parse_table(self._call("reserve", code))
        records = []
        for r in rows:
            records.append({
                "date":      r.get("date", ""),
                "type":      r.get("type", ""),
                "profit":    _safe_float(r.get("profit")),
                "profit_min": _safe_float(r.get("profit_min")),
                "profit_max": _safe_float(r.get("profit_max")),
            })
        return records

    # ── 停复牌 ──────────────────────────────────────────────────────────

    def suspension(self, market: str = "hs") -> List[Dict]:
        """停复牌信息"""
        rows = _parse_table(self._call("suspension", market))
        records = []
        for r in rows:
            records.append({
                "code":    r.get("code", ""),
                "name":    r.get("name", ""),
                "status":  r.get("status", ""),
                "reason":  r.get("reason", ""),
            })
        return records

    # ── 融资融券 ────────────────────────────────────────────────────────

    def margintrade(self, code: str) -> List[Dict]:
        """融资融券（仅沪深）"""
        rows = _parse_table(self._call("margintrade", code))
        records = []
        for r in rows:
            records.append({
                "date":          r.get("date", ""),
                "margin_balance": _safe_float(r.get("margin_balance")),
                "short_balance":  _safe_float(r.get("short_balance")),
                "margin_buy":     _safe_float(r.get("margin_buy")),
                "short_sell":     _safe_float(r.get("short_sell")),
            })
        return records

    # ── 大宗交易 ─────────────────────────────────────────────────────────

    def blocktrade(self, code: str) -> List[Dict]:
        """大宗交易（仅沪深）"""
        rows = _parse_table(self._call("blocktrade", code))
        records = []
        for r in rows:
            records.append({
                "date":        r.get("date", ""),
                "price":       _safe_float(r.get("price")),
                "volume":      _safe_float(r.get("volume")),
                "amount":      _safe_float(r.get("amount")),
                "premium":     _safe_float(r.get("premium")),
            })
        return records

    # ── 搜索 ─────────────────────────────────────────────────────────────

    def search(self, keyword: str) -> List[Dict]:
        """搜索股票/ETF/指数"""
        rows = _parse_table(self._call("search", keyword))
        records = []
        for r in rows:
            records.append({
                "code":       r.get("code", ""),
                "name":       r.get("name", ""),
                "stock_type": r.get("stock_type", ""),
            })
        return records
