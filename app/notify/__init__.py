"""
飞书推送模块
使用 Webhook 推送到飞书群，并记录推送日志到 t_push_log
"""
import sys
from pathlib import Path
import requests
import json
from typing import Optional, List
import pymysql
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings
from app.risk import RiskAlert, check_portfolio


# ── 数据库访问（推送日志）─────────────────────────────────────────

def _conn():
    return pymysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        passwd=settings.MYSQL_PASSWORD,
        db=settings.MYSQL_DATABASE,
        charset="utf8mb4",
    )


def _log_push(push_type: str, title: str, content: str, status: str, error_msg: str = None):
    """写入推送日志 t_push_log"""
    sql = (
        "INSERT INTO t_push_log (push_type, title, content, status, error_msg) "
        "VALUES (%s, %s, %s, %s, %s)"
    )
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (push_type, title, content[:2000], status, error_msg))
                conn.commit()
    except Exception:
        pass


# ── 基础推送函数 ───────────────────────────────────────────────────

def push_text(content: str, webhook_url: Optional[str] = None) -> bool:
    """
    推送纯文本消息到飞书
    """
    url = webhook_url or getattr(settings, "FEISHU_WEBHOOK_URL", None)
    if not url:
        return False

    payload = {
        "msg_type": "text",
        "content": {"text": content}
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        result = resp.json()
        ok = result.get("code") == 0
        _log_push("text", "文本推送", content, "success" if ok else "failed",
                  None if ok else str(result))
        return ok
    except Exception as e:
        _log_push("text", "文本推送", content, "failed", str(e))
        return False


def push_markdown(title: str, content: str, webhook_url: Optional[str] = None) -> bool:
    """
    推送 Markdown 格式消息到飞书（使用 interactive card）
    """
    url = webhook_url or getattr(settings, "FEISHU_WEBHOOK_URL", None)
    if not url:
        return False

    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue"
            },
            "elements": [
                {"tag": "markdown", "content": content}
            ]
        }
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        result = resp.json()
        ok = result.get("code") == 0
        _log_push("alert" if "预警" in title else "daily_review",
                  title, content, "success" if ok else "failed",
                  None if ok else str(result))
        return ok
    except Exception as e:
        _log_push("alert" if "预警" in title else "daily_review",
                  title, content, "failed", str(e))
        return False


# ── 业务推送函数 ───────────────────────────────────────────────────

def push_portfolio_alerts(positions: list, webhook_url: Optional[str] = None) -> bool:
    """
    推送持仓风控预警到飞书
    :param positions: Portfolio ORM 对象列表
    :param webhook_url: 可选，覆盖默认配置
    :return: 是否推送成功（无预警时返回 True 不推送）
    """
    alerts = check_portfolio(positions)
    if not alerts:
        return True  # 无预警，不推送

    lines = ["**🚨 持仓风控预警**\n"]
    red_lines = []
    yellow_lines = []
    green_lines = []

    for a in alerts:
        line = f"- **{a.name}**（{a.code}）{a.rule}：{a.current_val}"
        if a.level == "red":
            red_lines.append("🔴 " + line)
        elif a.level == "yellow":
            yellow_lines.append("🟡 " + line)
        else:
            green_lines.append("🟢 " + line)

    if red_lines:
        lines.append("**🔴 严重预警**")
        lines.extend(red_lines)
        lines.append("")
    if yellow_lines:
        lines.append("**🟡 注意预警**")
        lines.extend(yellow_lines)
        lines.append("")
    if green_lines:
        lines.append("**🟢 止盈提醒**")
        lines.extend(green_lines)

    content = "\n".join(lines)
    return push_markdown(title="🚨 持仓风控预警", content=content, webhook_url=webhook_url)


def push_daily_review(review_text: str) -> bool:
    """
    推送每日复盘到飞书
    :param review_text: 复盘内容（Markdown 格式）
    :return: 是否推送成功
    """
    return push_markdown(title="📊 每日复盘", content=review_text)


def push_strategy_signals(signals: List[dict], webhook_url: Optional[str] = None) -> bool:
    """
    推送策略信号到飞书
    :param signals: 信号列表，每项包含 code/name/strategy/direction/score/reason
    :param webhook_url: 可选，覆盖默认配置
    :return: 是否推送成功（无信号时返回 True 不推送）
    """
    if not signals:
        return True

    # 按方向分组
    buy_signals = [s for s in signals if s.get("direction") == "buy"]
    sell_signals = [s for s in signals if s.get("direction") == "sell"]

    if not buy_signals and not sell_signals:
        return True

    # 策略名称映射
    strategy_names = {
        "multi_factor": "多因子",
        "macd": "MACD",
        "bollinger": "布林带",
        "ma": "均线",
    }

    lines = ["**📡 策略信号扫描报告**\n"]

    if buy_signals:
        lines.append("**🟢 买入信号**")
        for s in buy_signals[:10]:  # 最多显示10条
            name = strategy_names.get(s.get("strategy", ""), s.get("strategy", ""))
            score = s.get("score", 0)
            score_bar = "▓" * int(score / 10) + "░" * (10 - int(score / 10))
            lines.append(
                f"- **{s.get('name', s.get('code', ''))}** "
                f"`{s.get('code', '')}` {name} "
                f"评分 {score:.0f} {score_bar}"
            )
        if len(buy_signals) > 10:
            lines.append(f"_...还有 {len(buy_signals) - 10} 条买入信号_")
        lines.append("")

    if sell_signals:
        lines.append("**🔴 卖出信号**")
        for s in sell_signals[:10]:
            name = strategy_names.get(s.get("strategy", ""), s.get("strategy", ""))
            score = s.get("score", 0)
            score_bar = "▓" * int(score / 10) + "░" * (10 - int(score / 10))
            lines.append(
                f"- **{s.get('name', s.get('code', ''))}** "
                f"`{s.get('code', '')}` {name} "
                f"评分 {score:.0f} {score_bar}"
            )
        if len(sell_signals) > 10:
            lines.append(f"_...还有 {len(sell_signals) - 10} 条卖出信号_")

    content = "\n".join(lines)
    return push_markdown(title="📡 策略信号扫描", content=content, webhook_url=webhook_url)


def push_custom_text(text: str) -> bool:
    """
    推送自定义文本到飞书
    """
    return push_text(content=text)


# ── 便捷函数 ────────────────────────────────────────────────────────

def get_push_history(limit: int = 50) -> list:
    """
    获取推送历史
    """
    sql = (
        "SELECT id, push_type, title, status, error_msg, created_at "
        "FROM t_push_log "
        "ORDER BY id DESC LIMIT %s"
    )
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            return cur.fetchall()


def save_webhook_url(url: str) -> bool:
    """
    保存 Webhook URL 到 .env 文件（持久化）
    """
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent.parent
    env_file = root / ".env"

    lines = []
    updated = False
    if env_file.exists():
        lines = env_file.read_text(encoding="utf-8").splitlines()

    new_lines = []
    for line in lines:
        if line.strip().startswith("FEISHU_WEBHOOK_URL"):
            new_lines.append(f'FEISHU_WEBHOOK_URL="{url}"')
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f'FEISHU_WEBHOOK_URL="{url}"')

    try:
        env_file.write_text("\n".join(new_lines), encoding="utf-8")
        return True
    except Exception:
        return False

