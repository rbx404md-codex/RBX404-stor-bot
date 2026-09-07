from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.queries import get_user, adjust_coins
from utils.filters import IsAdmin
from utils.states import AdminCoin

router = Router(name="admin_coin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "admin:coin")
async def start_coin(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminCoin.waiting_user_id)
    await callback.message.answer("👤 ইউজারের Telegram ID লিখুন:")
    await callback.answer()


@router.message(AdminCoin.waiting_user_id)
async def coin_user_id(message: Message, state: FSMContext) -> None:
    if not message.text.strip().lstrip("-").isdigit():
        await message.answer("❌ সঠিক Telegram ID দিন।")
        return
    user_id = int(message.text.strip())
    user = await get_user(user_id)
    if not user:
        await message.answer("❌ এই আইডির ইউজার বটে পাওয়া যায়নি।")
        return
    await state.update_data(user_id=user_id)
    await state.set_state(AdminCoin.waiting_amount)
    await message.answer(
        f"বর্তমান ব্যালেন্স: {user['coin_balance']}\n"
        "➕ যোগ করতে ধনাত্মক সংখ্যা লিখুন (যেমন: 100), ➖ কাটতে ঋণাত্মক লিখুন (যেমন: -50):"
    )


@router.message(AdminCoin.waiting_amount)
async def coin_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    text = message.text.strip()
    if not text.lstrip("-").isdigit():
        await message.answer("❌ শুধু সংখ্যা দিন (ঋণাত্মক হতে পারে)।")
        return
    data = await state.get_data()
    await state.clear()
    amount = int(text)
    try:
        new_balance = await adjust_coins(data["user_id"], amount, f"Admin adjustment by {message.from_user.id}")
    except ValueError:
        await message.answer("❌ এত কয়েন কাটা সম্ভব না, ইউজারের ব্যালেন্স যথেষ্ট নেই।")
        return

    await message.answer(f"✅ সম্পন্ন। নতুন ব্যালেন্স: {new_balance}")
    try:
        sign = "➕" if amount > 0 else "➖"
        await bot.send_message(data["user_id"], f"{sign} আপনার ওয়ালেটে {abs(amount)} কয়েন {'যোগ' if amount>0 else 'কাটা'} হয়েছে।")
    except Exception:  # noqa: BLE001
        pass
