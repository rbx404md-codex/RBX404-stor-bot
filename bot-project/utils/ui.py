"""
Menu navigation calls edit_text() a lot. But the very first message a user
sees (welcome) may be a PHOTO (if assets/welcome.jpg exists), and Telegram
does not allow turning a photo message into a text-only one via edit_text.
This helper tries edit_text, falls back to edit_caption, and finally just
sends a fresh message — so navigation never silently breaks depending on
whether a welcome image is configured.
"""
from aiogram.types import CallbackQuery, InlineKeyboardMarkup


async def safe_edit(callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup | None = None,
                     parse_mode: str | None = "HTML") -> None:
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception:  # noqa: BLE001 — e.g. message is a photo, or text unchanged
        pass
    try:
        await callback.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception:  # noqa: BLE001
        pass
    await callback.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
