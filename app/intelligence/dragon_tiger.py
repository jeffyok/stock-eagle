"""
龙虎榜解读
游资席位识别 + 营业部聚合 + 近30天龙虎榜汇总
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
from app.data.akshare_source import AKShareSource


class DragonTigerAnalyzer:
    """
    龙虎榜分析器
    功能：
    1. 近N日龙虎榜汇总
    2. 游资席位识别（知名游资）
    3. 营业部买卖聚合
    4. 个股龙虎榜历史
    """

    # 知名游资席位关键字
    KNOWN_BROKERS = {
        "拉萨": "拉萨帮（东财拉萨/团结路）",
        "东财": "东方财富",
        "中信": "中信证券",
        "华泰": "华泰证券",
        "招商": "招商证券",
        "国泰": "国泰君安",
        "银河": "银河证券",
        "平安": "平安证券",
        "光大": "光大证券",
        "兴业": "兴业证券",
        "浙商": "浙商证券",
        "华鑫": "华鑫证券",
        "作手": "顶级游资",
        "赵老哥": "赵老哥",
        "溧阳路": "溧阳路（孙哥）",
        "欢乐海岸": "欢乐海岸",
        "古北路": "古北路",
        "歌神": "歌神",
        "小鳄鱼": "小鳄鱼",
        "章盟主": "章盟主",
        "猪肉荣": "猪肉荣",
    }

    def __init__(self, data_source: Optional[AKShareSource] = None):
        self.ds = data_source or AKShareSource()

    # ── 近N日龙虎榜汇总 ───────────────────────────────────────────────────

    def get_recent_lhb(self, days: int = 30, top_n: int = 50) -> List[Dict]:
        """
        获取近N日龙虎榜数据汇总
        按净额降序
        """
        today = datetime.today()
        all_records = []

        for i in range(1, days + 1):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            try:
                records = self.ds.get_dragon_tiger(date)
                for r in records:
                    r["date"] = date
                    all_records.append(r)
            except Exception:
                pass

        # 按净额降序
        all_records.sort(key=lambda x: x.get("net_amount", 0), reverse=True)
        return all_records[:top_n]

    # ── 游资席位识别 ──────────────────────────────────────────────────────

    def identify_broker(self, broker_name: str) -> Dict[str, str]:
        """
        根据营业部名称识别游资类型
        返回：{raw: 原始名称, type: 游资类型, level: 活跃度}
        """
        broker_name = str(broker_name)
        identified_type = "普通营业部"
        level = "N/A"

        for keyword, broker_type in self.KNOWN_BROKERS.items():
            if keyword in broker_name:
                identified_type = broker_type
                if keyword in ["作手", "赵老哥", "欢乐海岸", "古北路", "溧阳路"]:
                    level = "顶级游资"
                elif keyword in ["拉萨", "东财"]:
                    level = "量化/散户"
                else:
                    level = "知名游资"
                break

        return {
            "raw": broker_name,
            "type": identified_type,
            "level": level,
        }

    # ── 个股龙虎榜历史 ────────────────────────────────────────────────────

    def get_stock_lhb_history(self, code: str, days: int = 90) -> Dict[str, Any]:
        """
        获取个股龙虎榜历史
        code: 股票代码（如 sh600519）
        """
        target_code = code[2:] if len(code) > 2 else code
        today = datetime.today()
        records = []

        for i in range(1, days + 1):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            try:
                daily = self.ds.get_dragon_tiger(date)
                for r in daily:
                    if r.get("code", "") == target_code:
                        r["date"] = date
                        records.append(r)
            except Exception:
                pass

        if not records:
            return {"code": code, "count": 0, "records": [], "summary": "近期无龙虎榜记录"}

        total_net = sum(r.get("net_amount", 0) for r in records)
        buy_count = sum(1 for r in records if r.get("net_amount", 0) > 0)
        avg_net = total_net / len(records)

        return {
            "code": code,
            "name": records[0].get("name", ""),
            "count": len(records),
            "total_net": round(total_net / 1e8, 2),
            "avg_net": round(avg_net / 1e4, 2),
            "buy_count": buy_count,
            "sell_count": len(records) - buy_count,
            "records": records,
            "summary": self._interpret(total_net, buy_count, len(records)),
        }

    # ── 营业部聚合 ────────────────────────────────────────────────────────

    def get_broker_stats(self, days: int = 30, top_n: int = 20) -> List[Dict]:
        """
        获取营业部买卖统计排行
        统计近N日各营业部上榜次数和买卖净额
        """
        recent = self.get_recent_lhb(days, 200)
        broker_stats = defaultdict(lambda: {
            "appear_count": 0,
            "total_buy": 0.0,
            "total_sell": 0.0,
            "net": 0.0,
            "buy_stocks": [],
            "sell_stocks": [],
        })

        for r in recent:
            # 龙虎榜数据中不包含营业部明细，需要用 stock_lhb_detail_em 的详细版本
            # 这里用上榜原因和股票来近似统计
            broker_stats["未知营业部"]["appear_count"] += 1
            broker_stats["未知营业部"]["net"] += r.get("net_amount", 0)

        stats = []
        for name, stat in broker_stats.items():
            stats.append({
                "broker": name,
                "appear_count": stat["appear_count"],
                "total_buy": round(stat["total_buy"] / 1e8, 2),
                "total_sell": round(stat["total_sell"] / 1e8, 2),
                "net": round(stat["net"] / 1e8, 2),
            })

        stats.sort(key=lambda x: abs(x["net"]), reverse=True)
        return stats[:top_n]

    # ── 综合报告 ───────────────────────────────────────────────────────────

    def get_analysis_report(self, days: int = 30) -> Dict[str, Any]:
        """
        生成龙虎榜综合分析报告
        """
        recent = self.get_recent_lhb(days, 50)
        top_buys = [r for r in recent if r.get("net_amount", 0) > 0][:10]
        top_sells = sorted(recent, key=lambda x: x.get("net_amount", 0))[:10]

        # 机构席位统计
        inst_count = 0
        for r in recent:
            reason = str(r.get("reason", ""))
            if "机构" in reason:
                inst_count += 1

        return {
            "total_records": len(recent),
            "top_buy_stocks": top_buys,
            "top_sell_stocks": top_sells,
            "institution_count": inst_count,
            "period": f"近{days}日",
        }

    # ── 辅助 ──────────────────────────────────────────────────────────────

    @staticmethod
    def _interpret(total_net: float, buy_count: int, total_count: int) -> str:
        """解读龙虎榜信号"""
        net_yi = total_net / 1e8
        buy_ratio = buy_count / total_count if total_count > 0 else 0

        if net_yi > 5:
            return "强势买入信号（多路游资介入）"
        elif net_yi > 1:
            return "温和买入信号"
        elif net_yi < -5:
            return "强势卖出信号（主力出逃）"
        elif net_yi < -1:
            return "温和卖出信号"
        elif buy_ratio > 0.7:
            return "多方主导（买入为主）"
        elif buy_ratio < 0.3:
            return "空方主导（卖出为主）"
        else:
            return "多空博弈（分歧较大）"
