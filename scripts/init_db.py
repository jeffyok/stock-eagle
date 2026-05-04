"""
数据库初始化脚本
创建所有表结构
"""
import sys
import os

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, engine
from app.models import (  # noqa: F401 - 确保模型被加载
    StockBasic, StockDaily, StockRealtime, StockMoneyFlow, DragonTiger,
    FundBasic, FundNav,
    SectorDaily,
    StrategySignal,
    Portfolio,
    DailyReview,
)
from loguru import logger


def init_db(drop_first: bool = False):
    """初始化数据库"""
    try:
        if drop_first:
            logger.warning("⚠️ 删除所有现有表...")
            Base.metadata.drop_all(bind=engine)
            logger.success("✅ 所有表已删除")

        logger.info("开始创建数据库表...")
        Base.metadata.create_all(bind=engine)
        logger.success("✅ 数据库表创建完成！")

        # 打印已创建的表
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"已创建的表: {', '.join(tables)}")

    except Exception as e:
        logger.exception(f"数据库初始化失败: {e}")
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="StockEagle 数据库初始化")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="删除现有表后重新创建（⚠️ 会丢失所有数据）",
    )
    args = parser.parse_args()

    if args.drop:
        confirm = input("确认删除所有数据？(yes/no): ")
        if confirm.lower() == "yes":
            init_db(drop_first=True)
        else:
            print("已取消")
    else:
        init_db()
