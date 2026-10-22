import logging
import smtplib
import ssl
from email.message import EmailMessage

from .config import SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_STARTTLS, SMTP_USERNAME


def send_password_reset_email(recipient: str, username: str, reset_url: str) -> None:
    """Deliver a single-use reset link without persisting mail credentials or tokens."""
    if not all((SMTP_HOST, SMTP_FROM)):
        logging.getLogger("shop.auth").warning("Password-reset email not sent: SMTP is not configured")
        return
    message = EmailMessage()
    message["Subject"] = "重置 Molecule Shop 密码"
    message["From"] = SMTP_FROM
    message["To"] = recipient
    message.set_content(
        f"你好，{username}：\n\n请在 30 分钟内打开以下链接重置密码：\n{reset_url}\n\n"
        "如果不是你本人发起的请求，请忽略此邮件。"
    )
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as client:
        if SMTP_STARTTLS:
            client.starttls(context=ssl.create_default_context())
        if SMTP_USERNAME:
            client.login(SMTP_USERNAME, SMTP_PASSWORD)
        client.send_message(message)
