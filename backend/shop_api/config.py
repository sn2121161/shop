import os
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres@localhost/nzw")
JWT_SECRET = os.getenv("JWT_SECRET", "local-development-secret-change-me-32b")
UPLOAD_DIRECTORY = Path(os.getenv("COMMENT_UPLOAD_DIR", ROOT / "uploads"))
PAYMENT_ENCRYPTION_KEY = os.getenv("PAYMENT_ENCRYPTION_KEY")
if not PAYMENT_ENCRYPTION_KEY:
    raise RuntimeError("PAYMENT_ENCRYPTION_KEY 未配置")
CARD_CIPHER = Fernet(PAYMENT_ENCRYPTION_KEY.encode())
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001,http://localhost:5173").split(",") if origin.strip()]
AUTO_CREATE_SCHEMA = os.getenv("AUTO_CREATE_SCHEMA", "true").lower() == "true"
SEED_DEMO_DATA = os.getenv("SEED_DEMO_DATA", "true").lower() == "true"
ADMIN_BOOTSTRAP_PASSWORD = os.getenv("ADMIN_BOOTSTRAP_PASSWORD", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")
SMTP_STARTTLS = os.getenv("SMTP_STARTTLS", "true").lower() == "true"

# Feishu is deliberately optional in local development: orders must still be
# created while a bot is unavailable or has not yet been configured.
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_ORDER_CHAT_ID = os.getenv("FEISHU_ORDER_CHAT_ID", "")
