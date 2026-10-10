"""Reliable outbound Feishu notifications for newly created orders."""

import json
import logging
from collections.abc import Callable

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from .config import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_ORDER_CHAT_ID
from .models import Order, OrderNotification, utcnow

LOGGER = logging.getLogger("shop.notifications")
MAX_NOTIFICATION_ATTEMPTS = 6
FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
FEISHU_MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"


def is_configured() -> bool:
    return bool(FEISHU_APP_ID and FEISHU_APP_SECRET and FEISHU_ORDER_CHAT_ID)


def _delivery_address(order: Order) -> str:
    fulfillment = order.fulfillment
    if fulfillment.pickup_store:
        return f"{fulfillment.pickup_store}（{fulfillment.pickup_phone}）"
    return "".join(part for part in [fulfillment.province, fulfillment.city, fulfillment.district, fulfillment.detail] if part)


def build_order_card(order: Order) -> dict:
    """Create a compact card where each fulfilment detail stays on its own row."""
    items = "\n".join(f"{item.product_name} × {item.quantity}" for item in order.items)
    fulfillment = order.fulfillment
    address_title = "自提点" if fulfillment.pickup_store else "配送地址"
    rows = [
        f"**订单号**：#{order.id}",
        f"**购买商品**：{items}",
        f"**下单账号**：{order.customer.username}",
        f"**手机号**：{fulfillment.recipient_phone or fulfillment.pickup_phone}",
        f"**配送服务**：{fulfillment.delivery_service}",
        f"**{address_title}**：{_delivery_address(order)}",
    ]
    return {
        "config": {"wide_screen_mode": True},
        "header": {"template": "green", "title": {"tag": "plain_text", "content": "新订单待处理"}},
        "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": "\n\n".join(rows)}}],
    }


def _send_card(card: dict, post: Callable[..., httpx.Response] | None = None) -> None:
    if not is_configured():
        raise RuntimeError("飞书订单通知尚未配置")
    post = post or httpx.post
    token_response = post(FEISHU_TOKEN_URL, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=10)
    token_response.raise_for_status()
    token_payload = token_response.json()
    if token_payload.get("code") != 0 or not token_payload.get("tenant_access_token"):
        raise RuntimeError(f"飞书令牌获取失败：{token_payload.get('msg', 'unknown error')}")
    response = post(
        FEISHU_MESSAGE_URL,
        headers={"Authorization": f"Bearer {token_payload['tenant_access_token']}"},
        json={"receive_id": FEISHU_ORDER_CHAT_ID, "msg_type": "interactive", "content": json.dumps(card, ensure_ascii=False)},
        timeout=10,
    )
    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError(f"飞书消息响应不是 JSON：HTTP {response.status_code}") from error
    if payload.get("code") != 0:
        raise RuntimeError(f"飞书消息发送失败：{payload.get('msg', 'unknown error')}")
    response.raise_for_status()


def send_test_card() -> None:
    """Send only an explicitly-labelled connectivity check, never a fake order."""
    _send_card({
        "config": {"wide_screen_mode": True},
        "header": {"template": "blue", "title": {"tag": "plain_text", "content": "订单机器人连通性测试"}},
        "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": "订单通知机器人已完成连通性验证。此消息不是订单。"}}],
    })


def deliver_order_notification(order_id: int, sessions: sessionmaker[Session]) -> None:
    """Attempt delivery once. A failure remains durable and never aborts an order."""
    if not is_configured():
        return
    with sessions() as session:
        notification = session.scalar(select(OrderNotification).where(OrderNotification.order_id == order_id))
        if not notification or notification.status in {"notified", "failed"} or notification.attempt_count >= MAX_NOTIFICATION_ATTEMPTS:
            return
        order = session.get(Order, order_id)
        try:
            _send_card(build_order_card(order))
        except (httpx.HTTPError, RuntimeError, ValueError) as error:
            notification.attempt_count += 1
            notification.last_error = str(error)[:500]
            notification.status = "failed" if notification.attempt_count >= MAX_NOTIFICATION_ATTEMPTS else "pending"
            session.commit()
            LOGGER.warning("Order %s Feishu notification attempt %s failed: %s", order_id, notification.attempt_count, notification.last_error)
            return
        notification.attempt_count += 1
        notification.status = "notified"
        notification.notified_at = utcnow()
        notification.last_error = None
        session.commit()


def retry_pending_notifications(sessions: sessionmaker[Session]) -> None:
    """Run at startup and on a five-minute schedule; only pending orders are retried."""
    if not is_configured():
        return
    with sessions() as session:
        order_ids = list(session.scalars(select(OrderNotification.order_id).where(OrderNotification.status == "pending", OrderNotification.attempt_count < MAX_NOTIFICATION_ATTEMPTS)))
    for order_id in order_ids:
        deliver_order_notification(order_id, sessions)
