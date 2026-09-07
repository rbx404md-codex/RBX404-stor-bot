"""
Telegram Stars payments use currency code 'XTR' and need NO payment
provider token (Stars are native to Telegram). Amount is in whole Stars.
"""
from aiogram import Bot
from aiogram.types import LabeledPrice


async def send_stars_invoice(bot: Bot, chat_id: int, product_id: int, title: str,
                              description: str, price_stars: int) -> None:
    await bot.send_invoice(
        chat_id=chat_id,
        title=title[:32],
        description=description[:255] or "Digital product",
        payload=f"product:{product_id}",
        provider_token="",          # empty for Telegram Stars
        currency="XTR",
        prices=[LabeledPrice(label=title[:32], amount=price_stars)],
    )
