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
    扫 t_portfolio 持仓股，写入 t_stock_realtime
    """
    from app.data.akshare_source import AKShareSource
    from app.models.portfolio import Portfolio
    from app.models.stock import StockRealtime

    logger.info("开始更新实时行情...")
    source = AKShareSource()
    db = SessionLocal()
    try:
        # 获取所有持仓股
        positions = db.query(Portfolio).filter(Portfolio.deleted_at.is_(None)).all()
        if not positions:
            logger.info("无持仓股，跳过")
            return

        now = datetime.datetime.now()
        for p in positions:
            try:
                data = source.get_stock_realtime(p.code)
                if not data:
                    continue

                def safe_float(v, default=0.0):
                    if v is None or v == "-":
                        return default
                    try:
                        return float(v)
                    except (ValueError, TypeError):
                        return default

                # upsert
                existing = db.query(StockRealtime).filter(
                    StockRealtime.code == p.code
                ).first()
                if existing:
                    existing.price = safe_float(data.get("price"))
                    existing.pct_chg = safe_float(data.get("pct_chg"))
                    existing.volume = int(safe_float(data.get("volume")))
                    existing.amount = safe_float(data.get("amount"))
                    existing.high = safe_float(data.get("high"))
                    existing.low = safe_float(data.get("low"))
                    existing.open = safe_float(data.get("open"))
                    existing.yesterday = safe_float(data.get("yesterday"))
                    existing.updated_at = now
                else:
                    rt = StockRealtime(
                        code=p.code,
                        name=data.get("name", p.name),
                        price=safe_float(data.get("price")),
                        pct_chg=safe_float(data.get("pct_chg")),
                        volume=int(safe_float(data.get("volume"))),
                        amount=safe_float(data.get("amount")),
                        high=safe_float(data.get("high")),
                        low=safe_float(data.get("low")),
                        open=safe_float(data.get("open")),
                        yesterday=safe_float(data.get("yesterday")),
                        updated_at=now,
                    )
                    db.add(rt)
            except Exception:
                pass

        db.commit()
        logger.success(f"✅ 实时行情更新完成，共处理 {len(positions)} 只")
    except Exception as e:
        logger.exception(f"实时行情更新失败: {e}")
    finally:
        db.close()


def update_daily_quotes():
    """
    盘后日线更新任务
    扫 t_portfolio 持仓股，更新当日日K到 t_stock_daily
    """
    from app.data.akshare_source import AKShareSource
    from app.models.portfolio import Portfolio
    from app.models.stock import StockDaily

    today = datetime.date.today()
    end_str = today.strftime("%Y%m%d")
    start_str = (today - datetime.timedelta(days=30)).strftime("%Y%m%d")
    logger.info(f"开始更新日线数据: {today}")

    source = AKShareSource()
    db = SessionLocal()
    try:
        positions = db.query(Portfolio).filter(Portfolio.deleted_at.is_(None)).all()
        if not positions:
            logger.info("无持仓股，跳过")
            return

        updated_count = 0
        for p in positions:
            try:
                records = source.get_stock_daily(p.code, start_str, end_str)
                if not records:
                    continue

                # 取最后一条（当日）
                latest = records[-1]
                trade_date_str = latest.get("date", today.strftime("%Y-%m-%d"))

                existing = db.query(StockDaily).filter(
                    StockDaily.code == p.code,
                    StockDaily.trade_date == trade_date_str,
                ).first()

                if existing:
                    existing.open = latest.get("open")
                    existing.close = latest.get("close")
                    existing.high = latest.get("high")
                    existing.low = latest.get("low")
                    existing.volume = latest.get("volume")
                    existing.amount = latest.get("amount")
                    existing.pct_chg = latest.get("pct_chg")
                    existing.turnover = latest.get("turnover")
                else:
                    daily = StockDaily(
                        code=p.code,
                        trade_date=trade_date_str,
                        open=latest.get("open"),
                        close=latest.get("close"),
                        high=latest.get("high"),
                        low=latest.get("low"),
                        volume=latest.get("volume"),
                        amount=latest.get("amount"),
                        pct_chg=latest.get("pct_chg"),
                        turnover=latest.get("turnover"),
                    )
                    db.add(daily)
                updated_count += 1
            except Exception:
                pass

        db.commit()
        logger.success(f"✅ 日线数据更新完成，共处理 {updated_count} 只")
    except Exception as e:
        logger.exception(f"日线更新失败: {e}")
    finally:
        db.close()


def scan_strategy_signals():
    """
    策略信号扫描任务
    每个交易日盘中(9:15)及盘后(15:10)运行
    - 扫描持仓股，生成多因子/MACD/布林带/均线信号
    - 写入 t_strategy_signal 表，过期旧信号
    - 推送飞书通知
    """
    from app.strategy.multi_factor import MultiFactorStrategy
    from app.strategy.technical import MACDStrategy, BollingerBandStrategy, MAStrategy
    from app.models.portfolio import Portfolio
    from app.models.signal import StrategySignal
    from app.notify import push_strategy_signals
    from app.config import settings
    from datetime import timedelta

    logger.info("开始扫描策略信号...")
    db = SessionLocal()

    try:
        # 1. 获取持仓股列表
        positions = db.query(Portfolio).filter(Portfolio.deleted_at.is_(None)).all()
        if not positions:
            logger.info("无持仓股，跳过信号扫描")
            return

        today = datetime.date.today()
        start = today - timedelta(days=120)  # 至少需要120天数据
        end = today

        # 2. 初始化策略引擎
        strategies = [
            ("multi_factor", MultiFactorStrategy()),
            ("macd", MACDStrategy()),
            ("bollinger", BollingerBandStrategy()),
            ("ma", MAStrategy()),
        ]

        all_signals = []
        scan_stats = {"total": 0, "buy": 0, "sell": 0, "stocks": 0}

        # 3. 扫描每只持仓股
        for pos in positions:
            stock_signals = []
            for strategy_name, engine in strategies:
                try:
                    signals = engine.generate_signals(pos.code, start, end)
                    for sig in signals:
                        sig["code"] = pos.code
                        sig["name"] = pos.name
                        sig["strategy_type"] = strategy_name
                        stock_signals.append(sig)
                except Exception as e:
                    logger.warning(f"策略 {strategy_name} 执行失败 {pos.code}: {e}")

            # 4. 去重：同一策略同一方向只保留最新信号
            latest_by_strategy = {}
            for sig in stock_signals:
                key = (sig["strategy_type"], sig["direction"])
                if key not in latest_by_strategy:
                    latest_by_strategy[key] = sig
                elif sig.get("date", "") > latest_by_strategy[key].get("date", ""):
                    latest_by_strategy[key] = sig

            stock_signals = list(latest_by_strategy.values())

            # 5. 写入数据库
            for sig in stock_signals:
                signal_date = sig.get("date")
                if hasattr(signal_date, "strftime"):
                    signal_date_str = signal_date.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    signal_date_str = str(signal_date) if signal_date else datetime.datetime.now()

                # 检查是否已存在相同信号（当天同策略同方向）
                existing = db.query(StrategySignal).filter(
                    StrategySignal.code == pos.code,
                    StrategySignal.signal_type == sig["strategy_type"],
                    StrategySignal.direction == sig["direction"],
                    StrategySignal.signal_date >= datetime.datetime.combine(
                        today, datetime.time(0, 0)
                    ),
                ).first()

                if not existing:
                    record = StrategySignal(
                        code=pos.code,
                        name=pos.name,
                        signal_type=sig["strategy_type"],
                        direction=sig["direction"],
                        price=float(sig.get("price", 0) or 0),
                        score=float(sig.get("score", 0) or 0),
                        reason=sig.get("reason", ""),
                        signal_date=signal_date_str,
                        is_expired=0,
                    )
                    db.add(record)
                    all_signals.append({
                        "code": pos.code,
                        "name": pos.name,
                        "strategy": sig["strategy_type"],
                        "direction": sig["direction"],
                        "score": sig.get("score", 0),
                        "reason": sig.get("reason", ""),
                    })
                    scan_stats["total"] += 1
                    if sig["direction"] == "buy":
                        scan_stats["buy"] += 1
                    else:
                        scan_stats["sell"] += 1

            if stock_signals:
                scan_stats["stocks"] += 1

        # 6. 标记过期信号（3个交易日前的未触发信号）
        expire_date = datetime.datetime.combine(
            today - timedelta(days=3), datetime.time(23, 59, 59)
        )
        db.query(StrategySignal).filter(
            StrategySignal.is_expired == 0,
            StrategySignal.signal_date < expire_date,
        ).update({"is_expired": 1})

        db.commit()

        # 7. 推送飞书通知
        if all_signals and settings.FEISHU_WEBHOOK_URL:
            push_strategy_signals(all_signals, webhook_url=settings.FEISHU_WEBHOOK_URL)

        logger.success(
            f"✅ 策略信号扫描完成: "
            f"扫描{scan_stats['stocks']}只持仓股, "
            f"新增买入信号{scan_stats['buy']}个, "
            f"卖出信号{scan_stats['sell']}个"
        )

    except Exception as e:
        logger.exception(f"策略信号扫描失败: {e}")
    finally:
        db.close()


def daily_review_task():
    """
    每日复盘任务
    每个交易日 16:00 执行
    """
    from app.notify import push_daily_review
    from app.config import settings

    logger.info("开始生成每日复盘...")
    # TODO: 汇总当日行情、板块、信号，生成复盘报告
    review_text = "StockEagle 每日复盘 - 待实现"

    if settings.FEISHU_WEBHOOK_URL:
        push_daily_review(review_text)
    logger.success("每日复盘推送完成")


def push_portfolio_alerts_task():
    """
    持仓预警推送任务
    每个交易日 16:05 执行（晚于复盘，确保证据数据更新完毕）
    """
    from app.portfolio.service import get_positions, enrich_with_realtime
    from app.notify import push_portfolio_alerts
    from app.config import settings

    logger.info("开始检查持仓预警...")
    positions = get_positions()
    if not positions:
        logger.info("无持仓，跳过预警推送")
        return

    positions = enrich_with_realtime(positions)
    ok = push_portfolio_alerts(positions, webhook_url=settings.FEISHU_WEBHOOK_URL)
    if ok:
        logger.success("持仓预警推送完成")
    else:
        logger.warning("持仓预警推送失败或无需推送")
