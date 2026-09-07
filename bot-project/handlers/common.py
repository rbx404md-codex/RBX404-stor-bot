from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.queries import get_user, set_user_language
from utils.i18n import language_kb, tr
from utils.keyboards import main_menu
from utils.branding import render_custom_emojis
router = Router(name="common")


@router.message(Command("cancel"))
async def cancel_any_flow(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current is None:
        await message.answer("কোনো চলমান কাজ নেই।")
        return
    await state.clear()
    await message.answer("❌ বাতিল করা হয়েছে।")


@router.message(Command("id"))
async def show_id(message: Message) -> None:
    await message.answer(
        f"🆔 আপনার Telegram user ID: <code>{message.from_user.id}</code>",
        parse_mode="HTML",
    )


@router.message(Command("emojitest"))
async def emoji_test(message: Message) -> None:
    await message.answer(
        render_custom_emojis(
            "🧪 <b>Custom emoji test</b>\n\n"
            "⚡️ Brand  🛍 Store  💰 Wallet  🎁 Referral\n"
            "✅ Success  ❌ Error  🛡 Security  🔔 Support  👑 Admin  ℹ️ Help"
        ),
        parse_mode="HTML",
    )


@router.message(Command("language"))
async def language_command(message: Message) -> None:
    user = await get_user(message.from_user.id)
    await message.answer(
        tr((user or {}).get("language"), "language_title"),
        reply_markup=language_kb(),
    )


@router.callback_query(F.data == "language:open")
async def language_open(callback: CallbackQuery) -> None:
    user = await get_user(callback.from_user.id)
    await callback.message.answer(
        tr((user or {}).get("language"), "language_title"),
        reply_markup=language_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("language:set:"))
async def language_set(callback: CallbackQuery) -> None:
    language = callback.data.split(":")[2]
    await set_user_language(callback.from_user.id, language)
    await callback.message.edit_text(
        tr(language, "language_saved"),
        reply_markup=main_menu(),
    )
    await callback.answer()


@router.message(Command("ping"))
async def ping(message: Message) -> None:
    await message.answer("🏓 Pong · RBX404 Bot online ✅")


@router.message(Command("emojiid"))
async def emoji_id(message: Message) -> None:
    entities = list(message.entities or []) + list(message.caption_entities or [])
    ids = [entity.custom_emoji_id for entity in entities if entity.type == "custom_emoji" and entity.custom_emoji_id]
    if not ids:
        await message.answer(
            "🎨 এই মেসেজে custom emoji পাওয়া যায়নি। একটি custom emoji একই মেসেজে পাঠিয়ে "
            "<code>/emojiid</code> যোগ করে আবার চেষ্টা করুন।",
            parse_mode="HTML",
        )
        return
    await message.answer(
        "✅ পাওয়া custom emoji ID:\n" + "\n".join(f"<code>{item}</code>" for item in ids),
        parse_mode="HTML",
    )
