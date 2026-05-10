"""
定时任务定义
"""
import datetime
from loguru import logger
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


def daily_review_task(push: bool = True):
    """
    每日复盘任务
    每个交易日 16:00 执行
    :param push: 是否推送到飞书，定时任务默认 True，页面手动生成可传 False
    """
    from app.notify import push_daily_review
    from app.config import settings
    from app.data.akshare_source import AKShareSource
    from app.portfolio.service import get_positions, enrich_with_realtime
    from app.risk import check_portfolio
    from app.models.review import DailyReview
    from app.database import SessionLocal
    import akshare as ak
    import datetime

    logger.info(f"开始生成每日复盘（push={push}）...")

    today = datetime.date.today()
    today_str = today.strftime("%Y%m%d")
    lines = []
    src = AKShareSource()
    positions = []

    # ── 标题 ────────────────────────────────────────────────────────
    lines.append(f"📰 StockEagle 每日复盘报告")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📅 日期：{today.strftime('%Y-%m-%d')}")
    lines.append("")

    # ── 1. 市场概况 ───────────────────────────────────────────────
    lines.append("📊 市场概况")
    try:
        # 上证指数(000001)、深证成指(399001)、创业板指(399006)
        df = ak.stock_zh_index_spot_em()
        index_map = {"000001": "上证指数", "399001": "深证成指", "399006": "创业板指"}
        for _, row in df.iterrows():
            code = str(row.get("代码", ""))
            if code in index_map:
                name = index_map[code]
                price = float(row.get("最新价", 0))
                pct = float(row.get("涨跌幅", 0))
                sign = "+" if pct >= 0 else ""
                lines.append(f"  {name}：{price:.2f}  {sign}{pct:.2f}%")
        lines.append("")
    except Exception as e:
        logger.warning(f"市场概况获取失败: {e}")
        lines.append("  数据获取失败")
        lines.append("")

    # ── 2. 持仓概览 ───────────────────────────────────────────────
    lines.append("💼 持仓概览")
    try:
        positions = get_positions()
        if positions:
            positions = enrich_with_realtime(positions)
            total_cost = sum(p.cost * p.quantity for p in positions)
            total_mv = sum(p.market_value() or 0 for p in positions)
            total_pl = total_mv - total_cost
            total_pl_pct = (total_pl / total_cost * 100) if total_cost > 0 else 0
            sign = "+" if total_pl >= 0 else ""
            lines.append(f"  账户总市值：¥{total_mv:,.2f}")
            lines.append(f"  浮动盈亏：{sign}¥{total_pl:,.2f}（{sign}{total_pl_pct:.2f}%）")
            lines.append(f"  持仓数量：{len(positions)} 只")
        else:
            lines.append("  暂无持仓")
        lines.append("")
    except Exception as e:
        logger.warning(f"持仓概览获取失败: {e}")
        lines.append("  数据获取失败")
        lines.append("")

    # ── 3. 风控预警（今日）───────────────────────────────────────
    lines.append("🚨 风控预警（今日）")
    try:
        if positions:
            alerts = check_portfolio(positions)
            if not alerts:
                lines.append("  ✅ 暂无预警，一切正常！")
            else:
                for a in alerts:
                    if a.level == "red":
                        lines.append(f"  🔴 {a.name}（{a.code}）— {a.rule}：{a.current_val}")
                    elif a.level == "yellow":
                        lines.append(f"  🟡 {a.name}（{a.code}）— {a.rule}：{a.current_val}")
                    else:
                        lines.append(f"  🟢 {a.name}（{a.code}）— {a.rule}：{a.current_val}")
        else:
            lines.append("  无持仓，无预警")
        lines.append("")
    except Exception as e:
        logger.warning(f"风控预警获取失败: {e}")
        lines.append("  数据获取失败")
        lines.append("")

    # ── 4. 龙虎榜异动（今日）────────────────────────────────────
    lines.append("🐉 龙虎榜异动（今日）")
    try:
        lhb_data = src.get_dragon_tiger(today_str)
        if lhb_data:
            rise = sum(1 for r in lhb_data if "涨" in r.get("reason", ""))
            fall = sum(1 for r in lhb_data if "跌" in r.get("reason", ""))
            lines.append(f"  共 {len(lhb_data)} 只股票上榜，涨停约{rise} 只、跌停约{fall} 只")
            # 展示前3条
            for r in lhb_data[:3]:
                lines.append(f"  • {r['name']}（{r['code']}）{r['reason']} 净买额：{r.get('net_amount', 0):.0f}万")
        else:
            lines.append("  今日无龙虎榜数据")
        lines.append("")
    except Exception as e:
        logger.warning(f"龙虎榜数据获取失败: {e}")
        lines.append("  数据获取失败")
        lines.append("")

    # ── 5. 板块异动 Top 5 ────────────────────────────────────────
    lines.append("🔥 板块异动 Top 5")
    try:
        sector_data = src.get_sector_spot()
        if sector_data:
            for i, s in enumerate(sector_data[:5], 1):
                pct = float(s.get("pct_chg", 0))
                sign = "+" if pct >= 0 else ""
                lines.append(f"  {i}. {s['sector_name']}  {sign}{pct:.2f}%")
        else:
            lines.append("  无板块数据")
        lines.append("")
    except Exception as e:
        logger.warning(f"板块异动数据获取失败: {e}")
        lines.append("  数据获取失败")
        lines.append("")

    # ── 6. 今日策略信号 ──────────────────────────────────────────
    lines.append("📡 今日策略信号")
    try:
        db = SessionLocal()
        try:
            from app.models.signal import StrategySignal
            import datetime as dt
            today_start = datetime.datetime.combine(today, datetime.time(0, 0))
            signals = db.query(StrategySignal).filter(
                StrategySignal.signal_date >= today_start,
                StrategySignal.is_expired == 0,
            ).all()
            if signals:
                strategy_names = {"multi_factor": "多因子", "macd": "MACD", "bollinger": "布林带", "ma": "均线"}
                for sig in signals[:10]:
                    name = strategy_names.get(sig.signal_type, sig.signal_type)
                    direction = "BUY" if sig.direction == "buy" else "SELL"
                    lines.append(f"  {sig.code}  {direction}  {name}  价格：{sig.price:.2f}")
            else:
                lines.append("  今日暂无新策略信号")
            db.close()
        except Exception:
            db.close()
    except Exception as e:
        logger.warning(f"策略信号获取失败: {e}")
        lines.append("  数据获取失败")
    lines.append("")

    # ── 结尾 ───────────────────────────────────────────────────────
    import datetime as dt
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"由 StockEagle 🦅 自动生成 | {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    review_text = "\n".join(lines)
    logger.info(f"复盘报告生成完成，长度：{len(review_text)} 字符")

    # ── 保存到 t_daily_review ──────────────────────────────────────
    db = SessionLocal()
    try:
        existing = db.query(DailyReview).filter(DailyReview.review_date == today).first()
        if existing:
            existing.market_trend = review_text
            existing.summary = f"自动生成 {today}"
            existing.created_at = datetime.datetime.now()
        else:
            review = DailyReview(
                review_date=today,
                market_trend=review_text,
                summary=f"自动生成 {today}",
            )
            db.add(review)
        db.commit()
        logger.success("✅ 复盘报告已保存到数据库")
    except Exception as e:
        logger.exception(f"保存复盘报告失败: {e}")
        db.rollback()
    finally:
        db.close()

    # ── 推送到飞书 ────────────────────────────────────────────────
    if push and settings.FEISHU_WEBHOOK_URL:
        ok = push_daily_review(review_text)
        if ok:
            logger.success("✅ 每日复盘推送完成")
        else:
            logger.warning("每日复盘推送失败")
    else:
        logger.info("未配置 FEISHU_WEBHOOK_URL，跳过推送")


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
