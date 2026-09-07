"""
Products are never stored on disk. Each product row only remembers which
message_id in STORAGE_CHANNEL_ID holds the real file. Delivery = copy that
message straight to the buyer's DM. copy_message (not forward_message) is
used so the buyer never sees "Forwarded from <channel>" and can't find the
source channel from the message itself.
"""
from aiogram import Bot

from config import STORAGE_CHANNEL_ID


async def deliver_product(bot: Bot, user_id: int, storage_msg_id: int, caption_extra: str = "") -> None:
    await bot.copy_message(
        chat_id=user_id,
        from_chat_id=STORAGE_CHANNEL_ID,
        message_id=storage_msg_id,
    )
    if caption_extra:
        await bot.send_message(user_id, caption_extra)
