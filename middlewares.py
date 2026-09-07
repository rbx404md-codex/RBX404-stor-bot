import time

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS
from database.queries import get_setting, get_user, touch_user
from handlers.force_join import missing_channels
from utils.keyboards import force_join_kb


class AccessMiddleware(BaseMiddleware):
    """Applies maintenance mode and force-join rules to all user updates."""

    def __init__(self) -> None:
        self._rate: dict[int, list[float]] = {}

    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if not user or user.id in ADMIN_IDS:
            return await handler(event, data)

        current = time.monotonic()
        bucket = [stamp for stamp in self._rate.get(user.id, []) if current - stamp < 10]
        if len(bucket) >= 12:
            if isinstance(event, CallbackQuery):
                await event.answer("অনেক দ্রুত action হচ্ছে। একটু পরে চেষ্টা করুন।", show_alert=True)
            else:
                await event.answer("অনেক দ্রুত message আসছে। ১০ সেকেন্ড পরে চেষ্টা করুন।")
            return None
        bucket.append(current)
        self._rate[user.id] = bucket

        db_user = await get_user(user.id)
        if db_user and db_user.get("is_banned"):
            if isinstance(event, CallbackQuery):
                await event.answer("আপনার access বন্ধ করা হয়েছে।", show_alert=True)
            else:
                await event.answer("🚫 আপনি এই বট ব্যবহার করতে পারবেন না।")
            return None
        if db_user and db_user.get("is_muted"):
            if isinstance(event, CallbackQuery):
                await event.answer("আপনার messaging access সাময়িকভাবে বন্ধ।", show_alert=True)
            else:
                await event.answer("🔇 আপনার messaging access সাময়িকভাবে বন্ধ।")
            return None

        if db_user:
            await touch_user(user.id, "callback" if isinstance(event, CallbackQuery) else "message")

        if isinstance(event, Message) and (event.text or "").startswith("/start"):
            return await handler(event, data)
        if isinstance(event, CallbackQuery) and event.data == "forcejoin:check":
            return await handler(event, data)

        if await get_setting("maintenance_mode", "0") == "1":
            if isinstance(event, CallbackQuery):
                await event.answer("বট maintenance mode-এ আছে।", show_alert=True)
            else:
                await event.answer("🛠️ বট আপডেট করা হচ্ছে। কিছুক্ষণ পরে চেষ্টা করুন।")
            return None

        bot: Bot = data["bot"]
        channels = await missing_channels(bot, user.id)
        if channels:
            if isinstance(event, CallbackQuery):
                await event.answer("আগে Required Channel-এ Join করুন।", show_alert=True)
                await event.message.answer(
                    "📢 বট ব্যবহার করতে নিচের Channel-গুলোতে Join করুন।",
                    reply_markup=force_join_kb(channels),
                )
            else:
                await event.answer(
                    "📢 বট ব্যবহার করতে আগে Required Channel-এ Join করুন।",
                    reply_markup=force_join_kb(channels),
                )
            return None

        return await handler(event, data)