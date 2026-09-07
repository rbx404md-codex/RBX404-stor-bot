from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from database.queries import sales_summary, top_products
from database.backup_restore import backup_and_pin
from utils.filters import IsAdmin
from utils.keyboards import admin_menu_kb

router = Router(name="admin_panel")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    await message.answer("👑 <b>Admin Panel</b>", reply_markup=admin_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "admin:panel")
async def admin_panel_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text("👑 <b>Admin Panel</b>", reply_markup=admin_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery) -> None:
    s = await sales_summary()
    products = await top_products(5)
    top_lines = "\n".join(
        f"• {p['name']}: {p['sales_count']} sales" for p in products
    ) or "—"
    text = (
        "📊 <b>Sales Dashboard</b>\n\n"
        f"👥 মোট ইউজার: {s['total_users']} · Active: {s['active_users']}\n"
        f"📦 সক্রিয় প্রোডাক্ট: {s['active_products']}\n\n"
        f"⭐ Stars বিক্রি: {s['stars_orders']} অর্ডার — মোট {s['stars_revenue']} XTR\n"
        f"🪙 Coin বিক্রি: {s['coin_orders']} অর্ডার — মোট {s['coin_revenue']} কয়েন\n"
        f"🕒 গত ২৪ ঘণ্টার অর্ডার: {s['orders_24h']}\n"
        f"🔗 Active links: {s['active_links']}\n\n"
        f"🔥 <b>Top products</b>\n{top_lines}"
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:backup_now")
async def admin_backup_now(callback: CallbackQuery, bot: Bot) -> None:
    await backup_and_pin(bot, note=f"manual by {callback.from_user.id}")
    await callback.answer("✅ ব্যাকআপ চ্যানেলে পাঠানো হয়েছে।", show_alert=True)
