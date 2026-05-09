"""
资金异动监控
主力净流入 + 北向资金 + 超大单跟踪
"""
from typing import List, Dict, Any
from app.data.akshare_source import AKShareSource


class MoneyMonitor:
    """
    资金异动监控器
    功能：
    1. 个股主力净流入排行
    2. 北向资金（沪深港通）实时数据
    3. 超大单资金异动
    """

    def __init__(self, ds: AKShareSource | None = None):
        from app.data.akshare_source import AKShareSource
        self.ds = ds or AKShareSource()

    # ── 个股资金流向 ─────────────────────────────────────────────────

    def stock_rank(self, indicator: str = "今日") -> List[Dict]:
        try:
            return self.ds.get_stock_money_flow_rank(indicator)
        except Exception as e:
            print(f"个股资金流向获取失败: {e}")
            return []

    def top_inflow(self, n: int = 20) -> List[Dict]:
        return self.stock_rank("今日")[:n]

    def top_outflow(self, n: int = 20) -> List[Dict]:
        all_s = self.stock_rank("今日")
        return sorted(all_s, key=lambda x: x.get("net_mf") or 0)[:n]

    # ── 行业资金流向 ─────────────────────────────────────────────────

    def industry_flow(self, top_n: int = 20) -> List[Dict]:
        """获取行业资金流向排行"""
        try:
            return self.ds.get_industry_fund_flow(top_n)
        except Exception as e:
            print(f"行业资金流向获取失败: {e}")
            return []

    # ── 北向资金 ─────────────────────────────────────────────────────

    def north_flow(self, days: int = 5) -> List[Dict]:
        try:
            return self.ds.get_north_money_flow(days)
        except Exception as e:
            print(f"北向资金获取失败: {e}")
            return []

    def north_hold_top(self, market: str = "沪股通", n: int = 20) -> List[Dict]:
        try:
            import akshare as ak
            df = ak.stock_hsgt_hold_stock_em(symbol=market)
            if df is None or df.empty:
                raise ValueError("返回空数据")
            records = []
            for _, row in df.iterrows():
                records.append({
                    "code": str(row.get("代码", "")),
                    "name": str(row.get("名称", "")),
                    "hold_ratio": float(row.get("持股数量", 0) or 0),
                    "pct_chg": float(row.get("涨跌幅", 0) or 0),
                })
            records.sort(key=lambda x: x["hold_ratio"], reverse=True)
            return records[:n]
        except Exception as e:
            print(f"北向持仓获取失败: {e}")
            return []

    # ── 异动检测 ───────────────────────────────────────────────────

    def detect_inflow(self, min_amt: float = 1e8, n: int = 20) -> List[Dict]:
        stocks = self.stock_rank("今日")
        return [s for s in stocks if (s.get("net_mf") or 0) >= min_amt][:n]

    def detect_north(self) -> Dict[str, Any]:
        flow = self.north_flow(5)
        if not flow:
            return {"direction": "unknown", "cumulative": 0}
        cum = sum(f["north_net"] for f in flow)
        direction = (
            "大幅流入" if cum > 20e8
            else "小幅流入" if cum > 0
            else "小幅流出" if cum > -20e8
            else "大幅流出"
        )
        return {"direction": direction, "cumulative": cum, "daily": flow}

    # ── 综合报告 ───────────────────────────────────────────────────

    def get_report(self) -> Dict[str, Any]:
        inflow = self.detect_inflow(1e8, 10)
        outflow = self.top_outflow(10)
        north = self.detect_north()

        in_amt = sum(s.get("net_mf") or 0 for s in inflow)
        out_amt = abs(sum(s.get("net_mf") or 0 for s in outflow))
        sentiment = (
            "资金净流入（做多）" if in_amt > out_amt * 1.5
            else "资金净流出（偏空）" if out_amt > in_amt * 1.5
            else "资金博弈（中性）"
        )
        return {
            "sentiment": sentiment,
            "main_inflow": inflow,
            "main_outflow": outflow,
            "north": north,
        }
