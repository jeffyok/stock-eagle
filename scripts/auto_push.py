"""
每日定时推送脚本（供自动化任务调用）
每日 16:00 自动执行，推送持仓预警到飞书
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.portfolio.service import get_positions, enrich_with_realtime
from app.notify import push_portfolio_alerts
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auto_push")


def main():
    webhook = getattr(settings, "FEISHU_WEBHOOK_URL", None)
    if not webhook:
        logger.error("未配置 FEISHU_WEBHOOK_URL，跳过推送")
        return

    logger.info("开始获取持仓数据...")
    positions = get_positions()
    if not positions:
        logger.info("无持仓，跳过推送")
        return

    positions = enrich_with_realtime(positions)
    logger.info(f"获取到 {len(positions)} 条持仓，开始推送...")

    ok = push_portfolio_alerts(positions, webhook_url=webhook)
    if ok:
        logger.info("推送成功")
    else:
        logger.error("推送失败")


if __name__ == "__main__":
    main()
