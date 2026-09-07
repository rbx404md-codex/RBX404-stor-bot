from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.queries import get_user, set_ban
from utils.filters import IsAdmin
from utils.states import AdminBan

router = Router(name="admin_ban")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "admin:ban")
async def start_ban(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminBan.waiting_user_id)
    await callback.message.answer("👤 যে ইউজারকে ব্যান/আনব্যান করতে চান তার Telegram ID লিখুন:")
    await callback.answer()


@router.message(AdminBan.waiting_user_id)
async def ban_toggle(message: Message, state: FSMContext) -> None:
    await state.clear()
    if not message.text.strip().isdigit():
        await message.answer("❌ সঠিক Telegram ID দিন।")
        return
    user_id = int(message.text.strip())
    user = await get_user(user_id)
    if not user:
        await message.answer("❌ ইউজার পাওয়া যায়নি।")
        return

    new_status = not bool(user["is_banned"])
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ নিশ্চিত করুন", callback_data=f"admin:ban:confirm:{user_id}:{int(new_status)}")
    await message.answer(
        f"ইউজার {user_id} বর্তমানে {'ব্যানড' if user['is_banned'] else 'সক্রিয়'}। "
        f"{'ব্যান' if new_status else 'আনব্যান'} করতে নিশ্চিত করুন:",
        reply_markup=kb.as_markup(),
    )


@router.callback_query(F.data.startswith("admin:ban:confirm:"))
async def confirm_ban(callback: CallbackQuery) -> None:
    _, _, _, user_id, flag = callback.data.split(":")
    await set_ban(int(user_id), bool(int(flag)))
    await callback.message.edit_text(f"✅ ইউজার {user_id} {'ব্যান' if int(flag) else 'আনব্যান'} করা হয়েছে।")
    await callback.answer()
