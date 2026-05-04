"""
定时任务定义
"""
import datetime
from loguru import logger
from sqlalchemy.orm import Session
from app.database import SessionLocal


def update_realtime_quotes():
    """
    盘中实时行情更新任务
    每个交易日的 9:30-15:00，每隔 DATA_UPDATE_INTERVAL 秒执行
    """
    from app.data.akshare_source import AKShareSource
    from app.models.stock import StockRealtime

    logger.info("开始更新实时行情...")
    source = AKShareSource()
    db = SessionLocal()
    try:
        data = source.get_stock_realtime  # AKShare 批量接口
        # TODO: 批量写入 stock_realtime 表
        logger.success(f"✅ 实时行情更新完成")
    except Exception as e:
        logger.exception(f"实时行情更新失败: {e}")
    finally:
        db.close()


def update_daily_quotes():
    """
    盘后日线更新任务
    每个交易日的 15:30 执行
    """
    from app.data.akshare_source import AKShareSource
    from app.models.stock import StockDaily

    today = datetime.date.today().strftime("%Y-%m-%d")
    logger.info(f"开始更新日线数据: {today}")

    db = SessionLocal()
    try:
        # TODO: 遍历自选股，更新当日日线
        logger.success(f"✅ 日线数据更新完成")
    except Exception as e:
        logger.exception(f"日线更新失败: {e}")
    finally:
        db.close()


def scan_strategy_signals():
    """
    策略信号扫描任务
    每个交易日盘中及盘后运行
    """
    logger.info("开始扫描策略信号...")
    # TODO: 调用策略引擎，生成买卖信号，写入 strategy_signal 表
    logger.info("策略信号扫描完成")


def daily_review_task():
    """
    每日复盘任务
    每个交易日 16:00 执行
    """
    from app.notify import send_feishu_message
    from app.config import settings

    logger.info("开始生成每日复盘...")
    # TODO: 汇总当日行情、板块、信号，生成复盘报告
    review_text = "StockEagle 每日复盘 - 待实现"

    if settings.FEISHU_WEBHOOK_URL:
        send_feishu_message(settings.FEISHU_WEBHOOK_URL, review_text)
    logger.success("✅ 每日复盘完成并已推送")
