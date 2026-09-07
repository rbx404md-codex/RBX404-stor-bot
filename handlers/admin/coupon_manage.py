from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from html import escape

from database.queries import create_coupon
from utils.filters import IsAdmin
from utils.states import AdminCoupon

router = Router(name="admin_coupon")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "admin:add_coupon")
async def start_coupon(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminCoupon.waiting_code)
    await callback.message.answer("🎟️ কুপন কোড লিখুন (যেমন: EID20):")
    await callback.answer()


@router.message(AdminCoupon.waiting_code)
async def coupon_code(message: Message, state: FSMContext) -> None:
    await state.update_data(code=message.text.strip().upper())
    kb = InlineKeyboardBuilder()
    kb.button(text="% Percent Discount", callback_data="admin:coupontype:percent")
    kb.button(text="🪙 Fixed Coin Discount", callback_data="admin:coupontype:fixed_coin")
    kb.adjust(1)
    await state.set_state(AdminCoupon.waiting_type)
    await message.answer("ধরন বেছে নিন:", reply_markup=kb.as_markup())


@router.callback_query(AdminCoupon.waiting_type, F.data.startswith("admin:coupontype:"))
async def coupon_type(callback: CallbackQuery, state: FSMContext) -> None:
    discount_type = callback.data.split(":")[2]
    await state.update_data(discount_type=discount_type)
    await state.set_state(AdminCoupon.waiting_value)
    hint = "শতকরা হার (যেমন 20 মানে ২০%)" if discount_type == "percent" else "কতো কয়েন কম হবে (যেমন 50)"
    await callback.message.answer(f"মান লিখুন — {hint}:")
    await callback.answer()


@router.message(AdminCoupon.waiting_value)
async def coupon_value(message: Message, state: FSMContext) -> None:
    if not message.text.strip().isdigit():
        await message.answer("❌ শুধু সংখ্যা দিন।")
        return
    await state.update_data(discount_value=int(message.text.strip()))
    await state.set_state(AdminCoupon.waiting_limit)
    await message.answer("সর্বোচ্চ কতবার ব্যবহার করা যাবে? (0 = আনলিমিটেড)")


@router.message(AdminCoupon.waiting_limit)
async def coupon_limit(message: Message, state: FSMContext) -> None:
    if not message.text.strip().isdigit():
        await message.answer("❌ শুধু সংখ্যা দিন।")
        return
    data = await state.get_data()
    await state.clear()
    await create_coupon(
        code=data["code"],
        discount_type=data["discount_type"],
        discount_value=data["discount_value"],
        usage_limit=int(message.text.strip()),
    )
    await message.answer(f"✅ কুপন '{escape(data['code'])}' তৈরি হয়েছে।")
