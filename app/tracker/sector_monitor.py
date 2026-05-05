"""
板块异动监控
实时追踪行业/概念板块涨跌、资金流入异动
"""
from typing import List, Dict, Any, Callable
import time
from app.data.akshare_source import AKShareSource


class SectorMonitor:
    """
    板块异动监控器
    功能：
    1. 行业板块实时行情（涨跌/资金）
    2. 概念板块实时行情
    3. 异动检测（涨幅超阈值 / 资金大幅流入）
    """

    CACHE_TTL = 600  # 缓存 10 分钟

    def __init__(self, ds: AKShareSource | None = None):
        from app.data.akshare_source import AKShareSource
        self.ds = ds or AKShareSource()
        self._cache: Dict[str, Any] = {}

    # ── 内部方法 ────────────────────────────────────────────────

    def _get_cached(self, key: str, fetcher: Callable[[], List[Dict]]) -> List[Dict]:
        now = time.time()
        entry = self._cache.get(key)
        if entry and now - entry["ts"] < self.CACHE_TTL:
            return entry["data"]
        data = fetcher()
        self._cache[key] = {"data": data, "ts": now}
        return data

    def _fetch_industry(self) -> List[Dict]:
        try:
            data = self.ds.get_sector_spot()
            if data:
                data.sort(key=lambda x: x.get("pct_chg", 0), reverse=True)
            return data or []
        except Exception as e:
            print(f"行业板块行情获取失败: {e}")
            return []

    def _fetch_concept(self) -> List[Dict]:
        try:
            data = self.ds.get_concept_sectors()
            return data or []
        except Exception as e:
            print(f"概念板块行情获取失败: {e}")
            return []

    # ── 行情（对外接口，带缓存）───────────────────────────────

    def get_industry_sectors(self) -> List[Dict]:
        return self._get_cached("industry", self._fetch_industry)

    def get_concept_sectors(self) -> List[Dict]:
        return self._get_cached("concept", self._fetch_concept)

    def get_sector_money_flow(self, sector_type: str = "industry") -> List[Dict]:
        try:
            data = self.ds.get_sector_money_flow(sector_type)
            return data or []
        except Exception as e:
            print(f"板块资金流获取失败: {e}")
            return []

    # ── 异动检测 ────────────────────────────────────────────────

    def detect_rising(self, min_pct: float = 3.0, top_n: int = 10) -> List[Dict]:
        sectors = self.get_industry_sectors()
        return [s for s in sectors if s.get("pct_chg", 0) >= min_pct][:top_n]

    def detect_inflow(self, min_ratio: float = 3.0, top_n: int = 10) -> List[Dict]:
        flows = self.get_sector_money_flow("industry")
        return [f for f in flows if f.get("net_mf_pct", 0) >= min_ratio][:top_n]

    # ── 综合报告 ────────────────────────────────────────────────

    def get_report(self) -> Dict[str, Any]:
        rising = self.detect_rising(3.0, 10)
        inflow = self.detect_inflow(3.0, 10)
        all_s = self.get_industry_sectors()
        rc = sum(1 for s in all_s if s.get("pct_chg", 0) > 0)
        tc = len(all_s)
        sentiment = "强势" if rc / tc > 0.7 else "弱势" if rc / tc < 0.3 else "震荡"
        return {
            "rising": rising,
            "inflow": inflow,
            "rising_count": rc,
            "total_count": tc,
            "sentiment": sentiment,
        }
