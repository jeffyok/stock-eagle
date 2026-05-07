"""
持仓管理服务：CRUD + 实时行情
"""
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.portfolio import Portfolio


class PortfolioService:
    """持仓服务类"""

    @staticmethod
    def add(code: str, name: str, cost: float, quantity: int,
            buy_date: date, stop_loss: Optional[float] = None,
            take_profit: Optional[float] = None, note: Optional[str] = None) -> int:
        """新增持仓，返回新记录 id"""
        now = datetime.now()
        pos = Portfolio(
            code=code,
            name=name,
            cost=Decimal(str(cost)),
            quantity=quantity,
            buy_date=buy_date,
            stop_loss=Decimal(str(stop_loss)) if stop_loss is not None else None,
            take_profit=Decimal(str(take_profit)) if take_profit is not None else None,
            note=note,
            created_at=now,
            updated_at=now,
        )
        sess = SessionLocal()
        try:
            sess.add(pos)
            sess.commit()
            return pos.id
        finally:
            sess.close()

    @staticmethod
    def delete(pos_id: int) -> bool:
        """软删除（设置 deleted_at）"""
        sql = (
            update(Portfolio)
            .where(Portfolio.id == pos_id, Portfolio.deleted_at.is_(None))
            .values(deleted_at=datetime.now(), updated_at=datetime.now())
        )
        sess = SessionLocal()
        try:
            result = sess.execute(sql)
            sess.commit()
            return result.rowcount > 0
        finally:
            sess.close()

    @staticmethod
    def update(pos_id: int, **kwargs) -> bool:
        """更新持仓（可更新 cost/quantity/stop_loss/take_profit/note/name/buy_date）"""
        allowed = {"cost", "quantity", "stop_loss", "take_profit", "note", "name", "buy_date"}
        values = {}
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                if k in ("cost", "stop_loss", "take_profit"):
                    values[k] = Decimal(str(v))
                else:
                    values[k] = v
        if not values:
            return False
        values["updated_at"] = datetime.now()
        sql = (
            update(Portfolio)
            .where(Portfolio.id == pos_id, Portfolio.deleted_at.is_(None))
            .values(**values)
        )
        sess = SessionLocal()
        try:
            result = sess.execute(sql)
            sess.commit()
            return result.rowcount > 0
        finally:
            sess.close()

    @staticmethod
    def get_all(include_deleted: bool = False) -> List[Portfolio]:
        """获取持仓列表（默认不包含已删除）"""
        sess = SessionLocal()
        try:
            query = select(Portfolio)
            if not include_deleted:
                query = query.where(Portfolio.deleted_at.is_(None))
            query = query.order_by(Portfolio.id.desc())
            result = sess.execute(query)
            return list(result.scalars().all())
        finally:
            sess.close()

    @staticmethod
    def get_by_id(pos_id: int) -> Optional[Portfolio]:
        """根据 ID 获取单条持仓"""
        sess = SessionLocal()
        try:
            query = select(Portfolio).where(
                Portfolio.id == pos_id,
                Portfolio.deleted_at.is_(None)
            )
            result = sess.execute(query)
            return result.scalar_one_or_none()
        finally:
            sess.close()

    @staticmethod
    def enrich_realtime(positions: List[Portfolio]) -> List[Portfolio]:
        """逐只拉取最近日K收盘价，填充到 position._current_price"""
        if not positions:
            return positions
        from app.data.westock_data import WestockData
        w = WestockData()

        for p in positions:
            try:
                # 优先用 westock-data 获取K线
                kline = w.kline(p.code, period="day", count=10)
                if kline:
                    # 按日期升序排序，确保最后一条是最新的
                    kline.sort(key=lambda x: x.get("date", ""))
                    latest = kline[-1]
                    close = float(latest.get("close", 0))
                    if close > 0:
                        p.set_current_price(Decimal(str(close)))
                        continue
            except Exception as e:
                print(f"westock-data 获取 {p.code} 失败: {e}")

            # 降级：尝试 akshare
            try:
                import akshare as ak
                from datetime import date, timedelta
                end = date.today()
                start = end - timedelta(days=10)
                market = p.code[:2]  # sh / sz / bj
                stock_code = p.code[2:]
                df = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period="daily",
                    start_date=start.strftime("%Y%m%d"),
                    end_date=end.strftime("%Y%m%d"),
                    adjust="qfq",
                )
                if df is not None and not df.empty:
                    df = df.sort_values(by="日期", ascending=True)
                    latest = df.iloc[-1]
                    close = float(latest.get("收盘", 0))
                    if close > 0:
                        p.set_current_price(Decimal(str(close)))
            except Exception as e:
                print(f"akshare 获取 {p.code} 也失败: {e}")

        return positions


# ── 便捷函数（兼容旧接口）─────────────────────────────────────────────

def add_position(code: str, name: str, cost: float, quantity: int,
                 buy_date: str, stop_loss: Optional[float] = None,
                 take_profit: Optional[float] = None, note: Optional[str] = None) -> int:
    """新增持仓，返回新记录 id"""
    if isinstance(buy_date, str):
        buy_date = date.fromisoformat(buy_date)
    return PortfolioService.add(
        code=code, name=name, cost=cost, quantity=quantity,
        buy_date=buy_date, stop_loss=stop_loss,
        take_profit=take_profit, note=note,
    )


def delete_position(pos_id: int) -> bool:
    """软删除"""
    return PortfolioService.delete(pos_id)


def update_position(pos_id: int, **kwargs) -> bool:
    """更新持仓"""
    return PortfolioService.update(pos_id, **kwargs)


def get_positions(include_deleted: bool = False) -> List[Portfolio]:
    """获取持仓列表"""
    return PortfolioService.get_all(include_deleted=include_deleted)


def get_position(pos_id: int) -> Optional[Portfolio]:
    """根据 ID 获取持仓"""
    return PortfolioService.get_by_id(pos_id)


def enrich_with_realtime(positions: List[Portfolio]) -> List[Portfolio]:
    """填充实时行情"""
    return PortfolioService.enrich_realtime(positions)
