"""RBX404 visual language helpers.

Telegram custom emoji are represented in HTML as ``<tg-emoji>`` entities.
The bot keeps Unicode fallbacks so the same source remains portable and the
UI still works when no custom emoji IDs have been configured.
"""
import re

from config import CUSTOM_EMOJI_ENABLED, CUSTOM_EMOJI_ID, CUSTOM_EMOJI_IDS


_CUSTOM_EMOJI_TAG = re.compile(r"<tg-emoji\b[^>]*>.*?</tg-emoji>", re.DOTALL)
_EMOJI_ROLES = {
    "👋": "brand",
    "⚡": "brand",
    "⚡️": "brand",
    "✨": "brand",
    "🎉": "brand",
    "🛍": "store",
    "🛍️": "store",
    "📦": "store",
    "📂": "store",
    "🎬": "store",
    "🔍": "store",
    "🪙": "wallet",
    "💰": "wallet",
    "💳": "wallet",
    "➕": "wallet",
    "🎁": "referral",
    "🏆": "referral",
    "👥": "referral",
    "👤": "admin",
    "👇": "help",
    "👉": "help",
    "🔎": "store",
    "❤️": "store",
    "❤": "store",
    "⭐": "brand",
    "⭐️": "brand",
    "🎟": "store",
    "🎟️": "store",
    "✅": "success",
    "👍": "success",
    "❌": "error",
    "🚫": "error",
    "⚠️": "error",
    "⚠": "error",
    "🗑": "error",
    "🗑️": "error",
    "🆘": "support",
    "📎": "support",
    "📝": "support",
    "🔔": "support",
    "✍️": "support",
    "✍": "support",
    "ℹ️": "help",
    "ℹ": "help",
    "❓": "help",
    "📜": "help",
    "🔒": "security",
    "🛡️": "security",
    "🛡": "security",
    "👑": "admin",
    "📊": "admin",
    "📌": "admin",
    "🛠️": "admin",
    "🛠": "admin",
    "🧰": "admin",
    "🗄": "admin",
    "🗄️": "admin",
    "📢": "support",
    "📣": "support",
    "🧾": "wallet",
    "📋": "help",
    "📚": "store",
    "⏳": "help",
    "🔗": "store",
    "🔥": "store",
    "🟠": "store",
    "🟣": "store",
}
_EMOJI_PATTERN = re.compile(
    "|".join(re.escape(item) for item in sorted(_EMOJI_ROLES, key=len, reverse=True))
)


def custom_emoji(role: str, fallback: str) -> str:
    """Return a Telegram custom emoji entity or the supplied Unicode fallback."""
    if not CUSTOM_EMOJI_ENABLED:
        return fallback
    emoji_id = CUSTOM_EMOJI_IDS.get(role) or CUSTOM_EMOJI_ID
    if emoji_id.isdigit():
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback


def brand_emoji(fallback: str = "✨") -> str:
    return custom_emoji("brand", fallback)


def _render_plain_segment(text: str) -> str:
    return _EMOJI_PATTERN.sub(
        lambda match: custom_emoji(_EMOJI_ROLES[match.group(0)], match.group(0)),
        text,
    )


def render_custom_emojis(text: str) -> str:
    """Convert known Unicode UI emoji to configured custom emoji entities.

    Existing ``tg-emoji`` tags are protected, making the function idempotent.
    This lets the transport layer cover messages across all handlers without
    requiring every feature module to manually wrap its labels.
    """
    if not CUSTOM_EMOJI_ENABLED:
        return text
    if not (CUSTOM_EMOJI_ID.isdigit() or any(value.isdigit() for value in CUSTOM_EMOJI_IDS.values())):
        return text

    parts: list[str] = []
    cursor = 0
    for match in _CUSTOM_EMOJI_TAG.finditer(text):
        parts.append(_render_plain_segment(text[cursor:match.start()]))
        parts.append(match.group(0))
        cursor = match.end()
    parts.append(_render_plain_segment(text[cursor:]))
    return "".join(parts)