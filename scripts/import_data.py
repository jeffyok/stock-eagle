"""
历史数据导入脚本
导入全市场股票基本信息 + 历史K线数据
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.data.akshare_source import AKShareSource
from app.models.stock import StockBasic
from loguru import logger


def import_stock_basic(db: Session):
    """导入股票基本信息"""
    logger.info("开始导入股票基本信息...")
    source = AKShareSource()

    try:
        data = source.get_stock_basic()
        logger.info(f"获取到 {len(data)} 条股票基本信息")

        # 清空并重新导入
        db.query(StockBasic).delete()

        for item in data:
            stock = StockBasic(
                code=item["code"],
                name=item["name"],
            )
            db.add(stock)

        db.commit()
        logger.success(f"✅ 股票基本信息导入完成，共 {len(data)} 条")

    except Exception as e:
        db.rollback()
        logger.exception(f"导入股票基本信息失败: {e}")


def import_history_daily(db: Session, days: int = 365):
    """
    导入历史日线数据
    days: 导入最近 N 天的数据
    """
    import datetime

    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days)

    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")

    logger.info(f"开始导入历史日线数据: {start_str} ~ {end_str}")

    source = AKShareSource()

    # 获取股票列表
    stocks = db.query(StockBasic).all()
    total = len(stocks)
    logger.info(f"共 {total} 只股票待处理")

    from app.models.stock import StockDaily

    success_count = 0
    fail_count = 0

    for idx, stock in enumerate(stocks, 1):
        code = stock.code
        try:
            # 获取历史数据
            data = source.get_stock_daily(code, start_str, end_str)

            if not data:
                fail_count += 1
                continue

            # 批量插入（先删后插，避免重复）
            db.query(StockDaily).filter(
                StockDaily.code == code,
                StockDaily.trade_date >= start_date,
                StockDaily.trade_date <= end_date,
            ).delete()

            for d in data:
                daily = StockDaily(
                    code=code,
                    trade_date=datetime.datetime.strptime(d["date"], "%Y-%m-%d").date(),
                    open=d["open"],
                    close=d["close"],
                    high=d["high"],
                    low=d["low"],
                    volume=d["volume"],
                    amount=d["amount"],
                    pct_chg=d.get("pct_chg", 0),
                    turnover=d.get("turn_over", 0),
                )
                db.add(daily)

            db.commit()
            success_count += 1

            if idx % 50 == 0:
                logger.info(f"进度: {idx}/{total} ({idx/total*100:.1f}%)")

            # 休息一下，避免被限流
            time.sleep(0.2)

        except Exception as e:
            db.rollback()
            fail_count += 1
            logger.warning(f"导入 {code} 失败: {e}")

    logger.success(
        f"✅ 历史日线导入完成！成功: {success_count}，失败: {fail_count}"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="StockEagle 历史数据导入")
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="导入最近 N 天的数据（默认365天）",
    )
    parser.add_argument(
        "--basic-only",
        action="store_true",
        help="仅导入股票基本信息",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        import_stock_basic(db)
        if not args.basic_only:
            import_history_daily(db, days=args.days)
    finally:
        db.close()
