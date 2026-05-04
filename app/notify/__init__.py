"""
推送通知模块
支持飞书、企业微信等渠道
"""
from typing import Optional


def send_feishu_message(webhook_url: str, content: str) -> bool:
    """
    发送飞书消息
    
    Args:
        webhook_url: 飞书机器人 webhook 地址
        content: 消息内容（支持 Markdown）
        
    Returns:
        是否发送成功
    """
    if not webhook_url:
        return False

    try:
        import httpx

        payload = {
            "msg_type": "text",
            "content": {
                "text": content,
            },
        }
        resp = httpx.post(webhook_url, json=payload, timeout=10)
        result = resp.json()

        if result.get("code") == 0:
            return True
        else:
            print(f"飞书推送失败: {result}")
            return False
    except Exception as e:
        print(f"飞书推送异常: {e}")
        return False


def send_signal_notification(
    code: str,
    name: str,
    direction: str,  # buy / sell
    price: float,
    reason: str,
    webhook_url: Optional[str] = None,
) -> bool:
    """
    发送买卖信号通知
    
    Args:
        code: 股票/基金代码
        name: 名称
        direction: 方向 buy/sell
        price: 价格
        reason: 信号原因
        webhook_url: 飞书 webhook（为空则读配置）
    """
    from app.config import settings

    url = webhook_url or settings.FEISHU_WEBHOOK_URL
    if not url:
        return False

    direction_text = "🟢 买入信号" if direction == "buy" else "🔴 卖出信号"
    content = (
        f"{direction_text}\n"
        f"代码: {code}\n"
        f"名称: {name}\n"
        f"价格: {price}\n"
        f"原因: {reason}"
    )
    return send_feishu_message(url, content)
