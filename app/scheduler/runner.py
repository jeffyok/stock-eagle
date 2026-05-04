"""
调度器运行器
使用 APScheduler 管理所有定时任务
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from app.scheduler.jobs import (
    update_realtime_quotes,
    update_daily_quotes,
    scan_strategy_signals,
    daily_review_task,
)
from app.config import settings


class SchedulerRunner:
    """调度器封装"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()

    def start(self):
        """启动所有定时任务"""

        # 盘中实时行情更新：每 N 秒执行（仅在交易时段）
        # 注意：APScheduler 不支持"仅在交易时段"原生判断，需任务内自行判断
        logger.info(f"注册实时行情更新任务，间隔 {settings.DATA_UPDATE_INTERVAL} 秒")
        self.scheduler.add_job(
            update_realtime_quotes,
            "interval",
            seconds=settings.DATA_UPDATE_INTERVAL,
            id="realtime_update",
            replace_existing=True,
        )

        # 盘后日线更新：每个交易日 15:30
        logger.info("注册盘后日线更新任务：每天 15:30")
        self.scheduler.add_job(
            update_daily_quotes,
            CronTrigger(hour=15, minute=30),
            id="daily_update",
            replace_existing=True,
        )

        # 策略信号扫描：每天 9:15 和 15:10
        logger.info("注册策略信号扫描任务：每天 9:15 和 15:10")
        self.scheduler.add_job(
            scan_strategy_signals,
            CronTrigger(hour=9, minute=15),
            id="signal_scan_morning",
            replace_existing=True,
        )
        self.scheduler.add_job(
            scan_strategy_signals,
            CronTrigger(hour=15, minute=10),
            id="signal_scan_evening",
            replace_existing=True,
        )

        # 每日复盘：每天 16:00
        logger.info("注册每日复盘任务：每天 16:00")
        self.scheduler.add_job(
            daily_review_task,
            CronTrigger(hour=16, minute=0),
            id="daily_review",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.success("✅ 调度器已启动")

    def shutdown(self):
        """停止调度器"""
        self.scheduler.shutdown()
        logger.info("调度器已停止")

    def get_jobs(self):
        """获取所有任务列表"""
        return self.scheduler.get_jobs()
