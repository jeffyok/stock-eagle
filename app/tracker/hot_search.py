"""
热搜监控
追踪东方财富/百度热搜，腾讯热搜通过 westock-data 获取
"""
from typing import List, Dict, Any


class HotSearchMonitor:
    """
    热搜监控器
    功能：
    1. 东方财富个股热搜  (akshare)
    2. 百度股票热搜      (akshare)
    3. 腾讯自选股热搜    (westock-data)
    """

    def eastmoney(self) -> List[Dict]:
        """东方财富个股热搜 Top 20"""
        try:
            import akshare as ak
            df = ak.stock_hot_rank_em()
            if df is None or df.empty:
                return []
            records = []
            for _, row in df.iterrows():
                records.append({
                    "rank": len(records) + 1,
                    "code": str(row.get("代码", "")),
                    "name": str(row.get("股票名称", "")),
                    "pct_chg": float(row.get("涨跌幅", 0) or 0),
                })
            return records[:20]
        except Exception as e:
            print(f"东财热搜获取失败: {e}")
            return []

    def baidu(self, date: str | None = None) -> List[Dict]:
        """百度股票热搜（date 格式 YYYYMMDD，默认今日）"""
        try:
            import akshare as ak
            import datetime
            d = date or datetime.datetime.now().strftime("%Y%m%d")
            # 正确签名：symbol="A股"（默认），date="20260505"
            df = ak.stock_hot_search_baidu(symbol="A股", date=d)
            if df is None or getattr(df, "empty", True) or df.empty:
                return []
            records = []
            for _, row in df.iterrows():
                records.append({
                    "rank": len(records) + 1,
                    "keyword": str(row.get("名称/代码", "")).strip(),
                    "hot_index": float(row.get("综合热度", 0) or 0),
                })
            return records[:20]
        except Exception as e:
            print(f"百度热搜获取失败: {e}")
            return []

    def tencent(self) -> List[Dict]:
        """
        腾讯自选股热搜 Top 20
        通过 AKShare 的 stock_hot_rank_tencent 获取
        """
        try:
            from app.data.akshare_source import AKShareSource
            return AKShareSource().get_hot_search_tencent()
        except Exception as e:
            print(f"腾讯热搜获取失败: {e}")
            return []

    # ── 综合报告 ──────────────────────────────────────────

    def get_report(self) -> Dict[str, Any]:
        em = self.eastmoney()
        bd = self.baidu()
        tc = self.tencent()

        em_names = {r.get("name", "") for r in em if r.get("name")}
        tc_names = {r.get("name", "") for r in tc if r.get("name")}
        common = em_names & tc_names

        hot_tags = []
        if em:
            hot_tags.append(f"东财热搜#{em[0].get('name', '未知')}")
        if tc:
            hot_tags.append(f"腾讯热搜#{tc[0].get('name', '未知')}")
        if bd:
            hot_tags.append(f"百度热搜#{bd[0].get('keyword', '未知')}")

        # all_hot: 合并东方财富和腾讯热搜（有股票名称的），用于综合报告展示
        all_hot = []
        for r in em:
            all_hot.append({"rank": len(all_hot) + 1, "source": "东方财富", **r})
        for r in tc:
            if r.get("name") and r.get("name") not in {x["name"] for x in all_hot}:
                all_hot.append({"rank": len(all_hot) + 1, "source": "腾讯", **r})

        summary = []
        if em:
            summary.append(f"东方财富热搜 Top1：{em[0].get('name', 'N/A')}（{em[0].get('pct_chg', 0):+.2f}%）")
        if tc:
            summary.append(f"腾讯热搜 Top1：{tc[0].get('name', 'N/A')}（{tc[0].get('pct_chg', 0):+.2f}%）")
        if bd:
            summary.append(f"百度热搜 Top1：{bd[0].get('keyword', 'N/A')}（热度 {bd[0].get('hot_index', 0):.0f}）")
        if common:
            summary.append(f"跨平台共同关注：{', '.join(list(common)[:3])}")

        return {
            "eastmoney": em,
            "baidu": bd,
            "tencent": tc,
            "all_hot": all_hot,
            "summary": summary,
            "cross_platform": list(common),
            "hot_tags": hot_tags,
        }
