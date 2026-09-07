"""
Central configuration. Everything is read from .env so the same codebase
runs unchanged on Termux, a VPS, or Railway — only the .env values differ.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _int_list(raw: str) -> list[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = _int_list(os.getenv("ADMIN_IDS", ""))
ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "@RBX404").lstrip("@")
BKASH_NUMBER: str = os.getenv("BKASH_NUMBER", "01838372430")
NAGAD_NUMBER: str = os.getenv("NAGAD_NUMBER", "01732466920")

STORAGE_CHANNEL_ID: int = int(os.getenv("STORAGE_CHANNEL_ID", "0"))
BACKUP_CHANNEL_ID: int = int(os.getenv("BACKUP_CHANNEL_ID", "0"))

BACKUP_INTERVAL_MINUTES: int = int(os.getenv("BACKUP_INTERVAL_MINUTES", "60"))
REFERRAL_REWARD_COIN: int = int(os.getenv("REFERRAL_REWARD_COIN", "20"))
DAILY_CHECKIN_REWARD: int = int(os.getenv("DAILY_CHECKIN_REWARD", "10"))
CUSTOM_EMOJI_ID: str = os.getenv("CUSTOM_EMOJI_ID", "").strip()
CUSTOM_EMOJI_ENABLED: bool = os.getenv("CUSTOM_EMOJI_ENABLED", "1").strip().lower() not in {"0", "false", "no"}

# Curated from the uploaded emoji preview list. Environment values still
# override these defaults, so the bot can be restyled without code changes.
DEFAULT_CUSTOM_EMOJI_IDS: dict[str, str] = {
    "brand": "5042334757040423886",     # ⚡️
    "success": "5039793437776282663",   # ✅
    "error": "5040042498634810056",     # ❌
    "store": "5039730920232322000",     # 🛍
    "wallet": "5039789890133296083",    # 💰
    "referral": "5041975203853239332",  # 🎁
    "help": "5042306247047513767",      # ℹ️
    "security": "5042328396193864923",  # 🛡
    "support": "5042111805288089118",   # 🔔
    "admin": "5039727497143387500",     # 👑
}

# Optional role-specific Telegram custom emoji document IDs.  When a role is
# not configured, the legacy CUSTOM_EMOJI_ID is used as the shared fallback.
CUSTOM_EMOJI_IDS: dict[str, str] = {
    role: os.getenv(f"CUSTOM_EMOJI_{role.upper()}_ID", "").strip()
    or DEFAULT_CUSTOM_EMOJI_IDS[role]
    for role in DEFAULT_CUSTOM_EMOJI_IDS
}

DB_PATH: str = os.getenv("DB_PATH", "data/bot.db")
BASE_URL: str = os.getenv("BASE_URL", "").rstrip("/")
PUBLIC_PORTAL_URL: str = BASE_URL or (
    f"https://{os.getenv('REPLIT_DEV_DOMAIN', '').strip().rstrip('/')}"
    if os.getenv("REPLIT_DEV_DOMAIN", "").strip()
    else ""
)
WEB_PORT: int = int(os.getenv("WEB_PORT", "8099"))
LINK_DEFAULT_EXPIRY_HOURS: int = int(os.getenv("LINK_DEFAULT_EXPIRY_HOURS", "0"))
LINK_SIGNING_SECRET: str = os.getenv("LINK_SIGNING_SECRET", "") or BOT_TOKEN


def validate() -> None:
    """Fail loudly and clearly instead of crashing with a cryptic trace."""
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not ADMIN_IDS:
        missing.append("ADMIN_IDS")
    if missing:
        raise SystemExit(
            "\n❌ .env এ এই ভ্যালুগুলো সেট করা নেই: "
            + ", ".join(missing)
            + "\n👉 .env.example কপি করে .env বানান এবং মান বসান।\n"
        )
