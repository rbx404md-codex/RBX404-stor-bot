from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery
import time

from database.queries import (
    list_force_join_channels,
    referral_revalidation_targets,
    get_setting,
    set_referral_status,
)
from utils.keyboards import force_join_kb, main_menu

router = Router(name="force_join")
_membership_cache: dict[tuple[int, int], tuple[float, bool]] = {}
MEMBERSHIP_CACHE_SECONDS = 120


async def missing_channels(bot: Bot, user_id: int) -> list[dict]:
    if await get_setting("force_join_enabled", "1") != "1":
        return []
    missing = []
    for channel in await list_force_join_channels():
        cache_key = (channel["channel_id"], user_id)
        cached = _membership_cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < MEMBERSHIP_CACHE_SECONDS:
            if not cached[1]:
                missing.append(channel)
            continue
        try:
            member = await bot.get_chat_member(channel["channel_id"], user_id)
            joined = member.status not in {"left", "kicked"}
            _membership_cache[cache_key] = (time.monotonic(), joined)
            if not joined:
                missing.append(channel)
        except Exception:
            _membership_cache[cache_key] = (time.monotonic(), False)
            missing.append(channel)
    return missing


async def sync_referral_membership(bot: Bot, user_id: int, channels: list[dict] | None = None) -> bool:
    channels = await missing_channels(bot, user_id) if channels is None else channels
    if channels:
        await set_referral_status(user_id, "left", "required membership missing")
        return False
    await set_referral_status(user_id, "active")
    return True


async def send_join_prompt(callback: CallbackQuery, channels: list[dict]) -> None:
    await callback.message.answer(
        "📢 বট ব্যবহার করতে আগে নিচের Channel-গুলোতে Join করুন।",
        reply_markup=force_join_kb(channels),
    )


async def revalidate_all_referrals(bot: Bot) -> int:
    """Re-check referral membership in the background and return the count checked."""
    checked = 0
    for user_id in await referral_revalidation_targets():
        await sync_referral_membership(bot, user_id)
        checked += 1
    return checked


@router.callback_query(F.data == "forcejoin:check")
async def check_force_join(callback: CallbackQuery, bot: Bot) -> None:
    _membership_cache.clear()
    channels = await missing_channels(bot, callback.from_user.id)
    if channels:
        await callback.answer("সব Channel-এ Join করা হয়নি।", show_alert=True)
        await send_join_prompt(callback, channels)
        return
    await sync_referral_membership(bot, callback.from_user.id, channels=[])
    await callback.message.answer(
        "✅ Join verify হয়েছে। এখন বট ব্যবহার করতে পারবেন।",
        reply_markup=main_menu(),
    )
    await callback.answer()