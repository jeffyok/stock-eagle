"""
AI 综合评分引擎
多维度打分：基本面(30%) + 技术面(30%) + 资金面(25%) + 舆情面(15%)
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
from app.data.akshare_source import AKShareSource


class StockScorer:
    """
    A股股票综合评分器（0-100分制）

    评分维度权重：
    - 基本面（30%）：ROE、营收增速、利润增速、PE、PB
    - 技术面（30%）：均线多头、MACD、RSI、布林带
    - 资金面（25%）：主力净流入占比、北向资金
    - 舆情面（15%）：龙虎榜、涨停基因
    """

    def __init__(self, data_source: Optional[AKShareSource] = None):
        self.ds = data_source or AKShareSource()

    def score(self, code: str) -> Dict[str, Any]:
        """
        计算股票综合评分，返回完整评分报告

        :param code: 股票代码，如 sh600519
        :return: 评分字典
        """
        # 1. 基本面评分
        fin = self.ds.get_financial_data(code)
        fin_score = self._score_financial(fin)

        # 2. 技术面评分（近1年日线）
        today = pd.Timestamp.today()
        start = (today - pd.Timedelta(days=365)).strftime("%Y-%m-%d")
        daily = self.ds.get_stock_daily(code, start, today.strftime("%Y-%m-%d"))
        tech_score = self._score_technical(daily)

        # 3. 资金面评分
        mf = self.ds.get_money_flow(code)
        money_score = self._score_money(mf)

        # 4. 舆情面（龙虎榜历史30天 + 近期涨停）
        lhb_score = self._score_dragon_tiger(code)

        # 综合评分（加权）
        total = round(
            fin_score["total"] * 0.30
            + tech_score["total"] * 0.30
            + money_score["total"] * 0.25
            + lhb_score["total"] * 0.15,
            2,
        )

        # 推荐：80+强烈推荐，60+建议买入，40+持有，40-建议观望
        if total >= 80:
            rec = "强烈买入 ⭐⭐⭐"
        elif total >= 60:
            rec = "建议买入 ⭐⭐"
        elif total >= 40:
            rec = "谨慎持有 ⭐"
        else:
            rec = "建议观望"

        return {
            "code": code,
            "total_score": total,
            "recommendation": rec,
            "fundamentals": fin_score,
            "technical": tech_score,
            "money_flow": money_score,
            "sentiment": lhb_score,
            # 页面期望的 sub_scores 格式
            "sub_scores": {
                "fundamental": fin_score.get("total", 0),
                "technical": tech_score.get("total", 0),
                "money": money_score.get("total", 0),
                "sentiment": lhb_score.get("total", 0),
            },
            # 详细数据（中文字段）
            "detail": {
                "总分": f"{total:.0f}",
                "推荐": rec,
                "基本面": f"{fin_score.get('total', 0):.0f} 分",
                "技术面": f"{tech_score.get('total', 0):.0f} 分",
                "资金面": f"{money_score.get('total', 0):.0f} 分",
                "舆情": f"{lhb_score.get('total', 0):.0f} 分",
                "基本面详情": {
                    "ROE": fin.get("roe", 0),
                    "营收增速": f"{fin.get('revenue_growth', 0):.2f}%",
                    "利润增速": f"{fin.get('profit_growth', 0):.2f}%",
                    "市盈率PE": fin.get("pe", 0),
                    "市净率PB": fin.get("bps", 0),
                },
                "技术面详情": {
                    "均线多头": "是" if tech_score.get("details", {}).get("ma_bullish_pct", 0) > 60 else "否",
                    "均线多头排列": f"{tech_score.get('details', {}).get('ma_bullish_pct', 0):.1f}%",
                    "MACD金叉": "是" if tech_score.get("details", {}).get("macd_bullish") else "否",
                    "RSI": tech_score.get("details", {}).get("rsi", 0),
                    "布林带位置": tech_score.get("details", {}).get("bb_position", 0),
                    "量比": tech_score.get("details", {}).get("volume_ratio", 0),
                },
                "资金面详情": {
                    "主力净流入": f"{money_score.get('details', {}).get('net_mf', 0):.2f} 元",
                    "超大单净流入": f"{money_score.get('details', {}).get('net_mf_big', 0):.2f} 元",
                    "小单净流入": f"{money_score.get('details', {}).get('net_mf_small', 0):.2f} 元",
                    "净流入占比": f"{money_score.get('details', {}).get('inflow_ratio', 0):.2f}%",
                },
                "舆情详情": {
                    "30天上榜次数": lhb_score.get("details", {}).get("lhb_count_30d", 0),
                    "净买入金额": f"{lhb_score.get('details', {}).get('lhb_net_amount', 0):.2f} 亿",
                },
            },
        }

    # ── 基本面评分 ───────────────────────────────────────────────────────────

    def _score_financial(self, fin: Optional[Dict]) -> Dict[str, Any]:
        """基本面打分（0-100）"""
        if not fin:
            return {"total": 0, "details": {}, "warning": "财务数据获取失败"}

        # 各因子标准化到 0-100
        roe = self._normalize(fin.get("roe", 0), 0, 30)          # ROE 0-30%
        rev_g = self._normalize(fin.get("revenue_growth", 0), -50, 100)  # 营收增速
        prof_g = self._normalize(fin.get("profit_growth", 0), -100, 200)  # 利润增速

        pe = fin.get("pe", 0)
        # PE 越低越好，<10优秀 >80差
        pe_score = self._normalize(pe, 80, 5, invert=True)

        pb = fin.get("bps", 0)  # 需要用当前股价计算PB，这里用 BPS 近似
        pb_score = self._normalize(pb, 20, 1, invert=True)

        total = round(
            roe * 0.30 + rev_g * 0.20 + prof_g * 0.20 + pe_score * 0.15 + pb_score * 0.15,
            1,
        )
        return {
            "total": total,
            "details": {
                "roe": fin.get("roe", 0),
                "revenue_growth": fin.get("revenue_growth", 0),
                "profit_growth": fin.get("profit_growth", 0),
                "pe": fin.get("pe", 0),
                "bps": fin.get("bps", 0),
                "sub_scores": {
                    "roe": round(roe, 1),
                    "revenue_growth": round(rev_g, 1),
                    "profit_growth": round(prof_g, 1),
                    "pe": round(pe_score, 1),
                    "pb": round(pb_score, 1),
                },
            },
        }

    # ── 技术面评分 ───────────────────────────────────────────────────────────

    def _score_technical(self, daily: List[Dict]) -> Dict[str, Any]:
        """技术面打分（0-100）"""
        if not daily or len(daily) < 30:
            return {"total": 0, "details": {}, "warning": "历史数据不足"}

        df = pd.DataFrame(daily)
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        df = df.dropna(subset=["close"]).tail(120)  # 最近120个交易日

        close = df["close"].values

        # 1) 均线多头排列（MA5>MA10>MA20>MA60）
        ma5 = self._ma(close, 5)
        ma10 = self._ma(close, 10)
        ma20 = self._ma(close, 20)
        ma60 = self._ma(close, 60)
        ma_bullish = sum([ma5 > ma10, ma10 > ma20, ma20 > ma60]) / 3 * 100

        # 2) MACD 金叉（dif > dea，且前一日 dif < dea）
        macd_hist = self._macd(close)
        macd_signal = ma_bullish  # 简化：用最近 MACD 柱方向
        recent_hist = macd_hist[-5:]
        macd_bullish = 100 if recent_hist[-1] > 0 and all(recent_hist > 0) else 50

        # 3) RSI（14日）
        rsi = self._rsi(close, 14)
        rsi_score = self._normalize(rsi, 80, 20)  # RSI 20-80

        # 4) 布林带（价格在中轨上方）
        bb_position = self._bb_position(close)
        bb_score = bb_position * 100

        # 5) 成交量放大（今日量 > 20日均量）
        vol_ma20 = df["volume"].tail(20).mean()
        vol_today = df["volume"].iloc[-1]
        vol_score = 100 if vol_today > vol_ma20 * 1.5 else 50 if vol_today > vol_ma20 else 25

        total = round(
            ma_bullish * 0.25
            + macd_signal * 0.25
            + rsi_score * 0.20
            + bb_score * 0.15
            + vol_score * 0.15,
            1,
        )

        return {
            "total": total,
            "details": {
                "ma_bullish_pct": round(ma_bullish, 1),
                "macd_bullish": bool(macd_signal == 100),
                "rsi": round(rsi, 1),
                "bb_position": round(bb_position, 2),
                "volume_ratio": round(vol_today / vol_ma20, 2) if vol_ma20 > 0 else 0,
                "sub_scores": {
                    "ma_bullish": round(ma_bullish, 1),
                    "macd": round(macd_signal, 1),
                    "rsi": round(rsi_score, 1),
                    "bollinger": round(bb_score, 1),
                    "volume": round(vol_score, 1),
                },
            },
        }

    # ── 资金面评分 ───────────────────────────────────────────────────────────

    def _score_money(self, mf: Optional[Dict]) -> Dict[str, Any]:
        """资金面打分（0-100）"""
        if not mf:
            return {"total": 0, "details": {}, "warning": "资金流向数据获取失败"}

        net_mf = mf.get("net_mf", 0)
        net_mf_big = mf.get("net_mf_big", 0)
        net_mf_small = mf.get("net_mf_small", 0)

        # 主力净流入占比
        total_mf = net_mf + net_mf_big + net_mf_small
        ratio = (net_mf / abs(total_mf)) if total_mf != 0 else 0
        inflow_score = self._normalize(ratio * 100, -100, 100)

        # 超大单净流入（越大越好）
        big_ratio = (net_mf_big / abs(total_mf)) if total_mf != 0 else 0
        big_score = self._normalize(big_ratio * 100, -50, 50)

        total = round(inflow_score * 0.6 + big_score * 0.4, 1)

        return {
            "total": total,
            "details": {
                "net_mf": net_mf,
                "net_mf_big": net_mf_big,
                "net_mf_small": net_mf_small,
                "inflow_ratio": round(ratio * 100, 2),
                "sub_scores": {
                    "main_inflow": round(inflow_score, 1),
                    "super_inflow": round(big_score, 1),
                },
            },
        }

    # ── 舆情面评分 ───────────────────────────────────────────────────────────

    def _score_dragon_tiger(self, code: str) -> Dict[str, Any]:
        """舆情面打分（0-100），基于近30天龙虎榜和涨停基因"""
        try:
            # 近30天龙虎榜
            from datetime import datetime, timedelta
            today = datetime.today()
            lhb_count = 0
            total_net_amount = 0.0

            for i in range(30):
                date = (today - timedelta(days=i + 1)).strftime("%Y-%m-%d")
                records = self.ds.get_dragon_tiger(date)
                for r in records:
                    # 匹配代码（去掉市场前缀）
                    r_code = r.get("code", "")
                    target = code[2:] if len(code) > 2 else code
                    if r_code == target:
                        lhb_count += 1
                        total_net_amount += r.get("net_amount", 0)

            # 龙虎榜得分：出现次数 + 净买入金额
            freq_score = min(lhb_count * 20, 60)  # 最多60分
            amount_score = self._normalize(total_net_amount / 1e8, -1, 5) * 40  # 亿为单位
            total = round(min(freq_score + amount_score, 100), 1)

            return {
                "total": total,
                "details": {
                    "lhb_count_30d": lhb_count,
                    "lhb_net_amount": round(total_net_amount / 1e8, 2),  # 亿
                    "sub_scores": {
                        "freq": round(freq_score, 1),
                        "amount": round(amount_score, 1),
                    },
                },
            }
        except Exception as e:
            return {"total": 0, "details": {}, "warning": f"龙虎榜数据获取失败: {e}"}

    # ── Top N 排行 ───────────────────────────────────────────────────────────

    def rank_top(self, codes: List[str], top_n: int = 20) -> List[Dict]:
        """
        对给定股票列表进行综合评分排序
        返回 Top N
        """
        results = []
        for code in codes:
            try:
                r = self.score(code)
                results.append(r)
            except Exception as e:
                print(f"评分失败 {code}: {e}")

        results.sort(key=lambda x: x["total_score"], reverse=True)
        return results[:top_n]

    def rank_by_financial(self, top_n: int = 20) -> List[Dict]:
        """
        快速基本面评分排行（不依赖历史K线，速度快）
        """
        basic = self.ds.get_stock_basic()
        results = []
        for stock in basic[:500]:  # 先取前500只
            try:
                fin = self.ds.get_financial_data(stock["code"])
                fs = self._score_financial(fin)
                results.append({
                    "code": stock["code"],
                    "name": stock["name"],
                    "fin_score": fs["total"],
                    "details": fs,
                })
            except Exception:
                pass

        results.sort(key=lambda x: x["fin_score"], reverse=True)
        return results[:top_n]

    # ── 工具函数 ─────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize(value: float, min_val: float, max_val: float, invert: bool = False) -> float:
        """线性标准化到 0-100"""
        if max_val == min_val:
            return 50.0
        normalized = (value - min_val) / (max_val - min_val) * 100
        normalized = max(0, min(100, normalized))
        if invert:
            normalized = 100 - normalized
        return round(normalized, 2)

    @staticmethod
    def _ma(close: np.ndarray, n: int) -> float:
        """计算 N 日简单移动平均（最新值）"""
        if len(close) < n:
            return float("nan")
        return float(np.mean(close[-n:]))

    @staticmethod
    def _macd(close: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> np.ndarray:
        """计算 MACD histogram（简化版，无 ta 依赖）"""
        ema_fast = pd.Series(close).ewm(span=fast, adjust=False).mean().values
        ema_slow = pd.Series(close).ewm(span=slow, adjust=False).mean().values
        dif = ema_fast - ema_slow
        signal_line = pd.Series(dif).ewm(span=signal, adjust=False).mean().values
        return dif - signal_line

    @staticmethod
    def _rsi(close: np.ndarray, n: int = 14) -> float:
        """计算 RSI（14日）"""
        if len(close) < n + 1:
            return 50.0
        delta = np.diff(close, prepend=close[-1])
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = pd.Series(gain).rolling(n).mean().values
        avg_loss = pd.Series(loss).rolling(n).mean().values
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return float(rsi[-1])

    @staticmethod
    def _bb_position(close: np.ndarray, n: int = 20, k: float = 2.0) -> float:
        """布林带位置（0=下轨，0.5=中轨，1=上轨）"""
        if len(close) < n:
            return 0.5
        ma = np.mean(close[-n:])
        std = np.std(close[-n:])
        upper = ma + k * std
        lower = ma - k * std
        position = (close[-1] - lower) / (upper - lower + 1e-10)
        return max(0, min(1, position))
