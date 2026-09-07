from aiogram import Bot, Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, FSInputFile
from html import escape
import os

from database.queries import get_or_create_user, get_user
from utils.keyboards import force_join_kb, main_menu
from utils.ui import safe_edit
from utils.branding import brand_emoji

router = Router(name="start")

WELCOME_TEXT = (
    f"{brand_emoji('👋')} স্বাগতম {{name}}!\n\n"
    "এটি আমাদের ডিজিটাল স্টোর বট — এখান থেকে পেইড ভিডিও, ফাইল, ডকুমেন্ট কিনতে পারবেন "
    "🪙 কয়েন অথবা ⭐ Telegram Stars দিয়ে।\n\n"
    "👇 নিচের মেনু থেকে শুরু করুন।"
)
WELCOME_IMAGE_PATH = "assets/welcome.jpg"  # optional — admin can replace this file


async def send_welcome(message: Message, name: str) -> None:
    text = WELCOME_TEXT.format(name=escape(name))
    if os.path.exists(WELCOME_IMAGE_PATH):
        await message.answer_photo(
            FSInputFile(WELCOME_IMAGE_PATH),
            caption=text,
            reply_markup=main_menu(),
            parse_mode="HTML",
        )
    else:
        await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, bot: Bot) -> None:
    ref_code = command.args.strip() if command.args else None
    user = await get_or_create_user(message.from_user.id, message.from_user.username, ref_code)

    if user["is_banned"]:
        await message.answer("🚫 আপনি এই বট ব্যবহার করা থেকে নিষিদ্ধ।")
        return

    from handlers.force_join import missing_channels, sync_referral_membership
    channels = await missing_channels(bot, message.from_user.id)
    if channels:
        await message.answer(
            "📢 বট ব্যবহার করতে আগে নিচের Channel-গুলোতে Join করুন।",
            reply_markup=force_join_kb(channels),
        )
        return

    await sync_referral_membership(bot, message.from_user.id, channels=[])

    await send_welcome(message, message.from_user.first_name or "বন্ধু")


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery) -> None:
    await safe_edit(
        callback,
        WELCOME_TEXT.format(name=escape(callback.from_user.first_name or "বন্ধু")),
        reply_markup=main_menu(),
    )
    await callback.answer()
