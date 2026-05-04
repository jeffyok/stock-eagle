"""
基金筛选器
- FundScreener：多维度筛选公募基金（股票型/债券型/混合型/指数型）
- 支持按收益率、排序方向、返回数量筛选
"""
from typing import List, Dict, Any, Optional

import pandas as pd

from app.data.akshare_source import AKShareSource


class FundScreener:
    """
    基金筛选器

    使用方式：
        screener = FundScreener()
        results = screener.screen(
            min_return={"return_1y": 20.0},
            top_n=10,
        )

    支持筛选维度：
    - 收益率：return_1w / return_1m / return_3m / return_6m /
               return_1y / return_2y / return_3y / return_ytd / return_total
    - 排序字段 + 方向
    - 返回数量上限

    注意：
    fund_open_fund_rank_em() 不返回"基金类型"字段，
    如需按类型筛选，可通过基金简称关键字过滤（如 "股票" / "混合" / "债券" / "指数"）。
    """

    # get_fund_rank() 返回的收益率字段名
    RETURN_FIELDS = [
        "return_1w", "return_1m", "return_3m", "return_6m",
        "return_1y", "return_2y", "return_3y", "return_ytd", "return_total",
    ]

    def __init__(self):
        self.source = AKShareSource()

    # ──────────────────────────────────────────────────────────────────
    # 公开方法
    # ──────────────────────────────────────────────────────────────────

    def screen(
        self,
        name_keyword: Optional[str] = None,
        min_return: Optional[Dict[str, float]] = None,
        sort_by: str = "return_1y",
        ascending: bool = False,
        top_n: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        筛选基金

        Args:
            name_keyword: 基金简称关键字过滤，如 "混合"、"股票"、"指数"
            min_return:  最低收益率要求，
                         如 {"return_1y": 20.0} 表示近1年收益率 >= 20%
            sort_by:     排序字段，默认 "return_1y"（近1年收益率）
            ascending:   是否升序，默认 False（降序，收益高的在前）
            top_n:       返回前 N 只基金

        Returns:
            基金列表，每只包含：
                code, name, nav, nav_acc, pct_chg_1d,
                return_1w/1m/3m/6m/1y/2y/3y/ytd/total
        """
        funds = self.source.get_fund_rank()
        if not funds:
            return []

        df = pd.DataFrame(funds)

        # 将收益率字段转为数值
        for col in self.RETURN_FIELDS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # 按基金简称关键字过滤（替代基金类型过滤）
        if name_keyword:
            df = df[df["name"].str.contains(name_keyword, na=False)]

        # 过滤收益率
        if min_return:
            for field_key, threshold in min_return.items():
                if field_key not in df.columns:
                    print(f"[FundScreener] 警告：字段 {field_key} 不存在，跳过")
                    continue
                df = df[df[field_key] >= threshold]

        if df.empty:
            return []

        # 排序
        sort_field = sort_by if sort_by in df.columns else "return_1y"
        if sort_field in df.columns:
            df = df.sort_values(sort_field, ascending=ascending)

        # 取前 N 只
        df = df.head(top_n)

        return df.to_dict("records")

    def get_fund_nav_history(
        self,
        code: str,
        years: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        获取单只基金的历史净值（最近 N 年）
        委托给 AKShareSource.get_fund_nav_history()
        """
        return self.source.get_fund_nav_history(code, years)

    # ──────────────────────────────────────────────────────────────────
    # 便捷方法：按常见场景快速筛选
    # 通过基金简称关键字过滤类型（"混合"/"股票"/"债券"/"指数"）
    # ──────────────────────────────────────────────────────────────────

    def top_stock_funds(self, top_n: int = 10, min_1y_return: float = 0.0) -> List[Dict]:
        """股票型基金排行榜（按近1年收益率降序）"""
        return self.screen(
            name_keyword="股票",
            min_return={"return_1y": min_1y_return} if min_1y_return > 0 else None,
            sort_by="return_1y",
            ascending=False,
            top_n=top_n,
        )

    def top_mixed_funds(self, top_n: int = 10, min_1y_return: float = 0.0) -> List[Dict]:
        """混合型基金排行榜"""
        return self.screen(
            name_keyword="混合",
            min_return={"return_1y": min_1y_return} if min_1y_return > 0 else None,
            sort_by="return_1y",
            ascending=False,
            top_n=top_n,
        )

    def top_bond_funds(self, top_n: int = 10) -> List[Dict]:
        """债券型基金排行榜（稳健，按近1年收益率降序）"""
        return self.screen(
            name_keyword="债券",
            sort_by="return_1y",
            ascending=False,
            top_n=top_n,
        )

    def top_index_funds(self, top_n: int = 10) -> List[Dict]:
        """指数型基金排行榜"""
        return self.screen(
            name_keyword="指数",
            sort_by="return_1y",
            ascending=False,
            top_n=top_n,
        )
