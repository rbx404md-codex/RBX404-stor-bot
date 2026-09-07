from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.queries import user_orders, get_product
from services.channel_delivery import deliver_product

router = Router(name="orders")


@router.callback_query(F.data == "orders:mine")
async def my_orders(callback: CallbackQuery) -> None:
    orders = await user_orders(callback.from_user.id)
    if not orders:
        await callback.answer("আপনি এখনো কিছু কেনেননি।", show_alert=True)
        return

    kb = InlineKeyboardBuilder()
    for o in orders:
        kb.button(text=f"📦 {o['product_name']} ({o['created_at'][:10]})",
                   callback_data=f"orders:redownload:{o['product_id']}")
        kb.button(text=f"⭐ Rate #{o['product_id']}", callback_data=f"review:start:{o['product_id']}")
    kb.adjust(1)
    await callback.message.answer("📚 <b>আপনার কেনা প্রোডাক্ট:</b>", reply_markup=kb.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("orders:redownload:"))
async def redownload(callback: CallbackQuery, bot: Bot) -> None:
    product_id = int(callback.data.split(":")[2])
    product = await get_product(product_id)
    if not product:
        await callback.answer("প্রোডাক্টটি আর নেই।", show_alert=True)
        return
    await deliver_product(bot, callback.from_user.id, product["storage_msg_id"])
    await callback.answer("✅ পাঠানো হয়েছে।")
