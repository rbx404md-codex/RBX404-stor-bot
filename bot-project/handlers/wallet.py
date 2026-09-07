from aiogram import Router, F
from aiogram.types import CallbackQuery

from database.queries import get_user, coin_history
from utils.keyboards import wallet_kb
from utils.ui import safe_edit

router = Router(name="wallet")


@router.callback_query(F.data == "wallet:open")
async def open_wallet(callback: CallbackQuery) -> None:
    user = await get_user(callback.from_user.id)
    text = (
        f"🪙 <b>Wallet</b>\n\n"
        f"ব্যালেন্স: <b>{user['coin_balance']}</b> কয়েন\n"
        f"মোট কেনাকাটা: {user['total_purchases']} বার"
    )
    await safe_edit(callback, text, reply_markup=wallet_kb())
    await callback.answer()


@router.callback_query(F.data == "wallet:history")
async def wallet_history(callback: CallbackQuery) -> None:
    rows = await coin_history(callback.from_user.id)
    if not rows:
        await callback.answer("কোনো লেনদেন নেই।", show_alert=True)
        return
    lines = []
    for r in rows:
        sign = "➕" if r["amount"] > 0 else "➖"
        lines.append(f"{sign} {abs(r['amount'])} — {r['reason']} ({r['created_at'][:16]})")
    await callback.message.answer("📜 <b>সাম্প্রতিক লেনদেন:</b>\n\n" + "\n".join(lines), parse_mode="HTML")
    await callback.answer()


