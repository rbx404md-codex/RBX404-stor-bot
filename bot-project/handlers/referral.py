from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from database.queries import get_user, referral_stats
from config import REFERRAL_REWARD_COIN
from utils.keyboards import referral_kb

router = Router(name="referral")


@router.callback_query(F.data == "referral:open")
async def open_referral(callback: CallbackQuery, bot: Bot) -> None:
    user = await get_user(callback.from_user.id)
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={user['referral_code']}"
    stats = await referral_stats(callback.from_user.id)

    text = (
        f"🎁 <b>Referral Program</b>\n\n"
        f"আপনার লিংক:\n<code>{link}</code>\n\n"
        f"👥 মোট রেফার: {stats['total']}\n"
        f"✅ Active: {stats['active']} · ⏳ Pending: {stats['pending']}\n"
        f"🚫 Invalid/Left: {stats['invalid']}\n"
        f"🪙 রিওয়ার্ড পাওয়া গেছে: {stats['rewarded']} জনের থেকে\n\n"
        f"প্রতি রেফারকৃত ইউজার প্রথমবার কিছু কিনলে আপনি পাবেন 🪙 {REFERRAL_REWARD_COIN} কয়েন।"
    )
    await callback.message.answer(text, reply_markup=referral_kb(), parse_mode="HTML")
    await callback.answer()
