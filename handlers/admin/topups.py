from html import escape

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

from database.queries import (
    approve_topup_request,
    get_topup_request,
    pending_topup_requests,
    reject_topup_request,
)
from utils.filters import IsAdmin
from utils.keyboards import admin_topup_list_kb, admin_topup_review_kb

router = Router(name="admin_topups")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def _request_text(request: dict, title: str = "💳 Top-up Request") -> str:
    username = (
        f"@{escape(request['username'])}"
        if request.get("username")
        else "username নেই"
    )
    method = {"bkash": "bKash", "nagad": "Nagad"}.get(
        request["payment_method"], request["payment_method"]
    )
    status = {
        "pending": "⏳ Pending",
        "approved": "✅ Approved",
        "rejected": "❌ Rejected",
    }.get(request["status"], request["status"])
    return (
        f"<b>{title}</b>\n\n"
        f"Request: <code>#{request['request_id']}</code>\n"
        f"User: {username}\n"
        f"User ID: <code>{request['user_id']}</code>\n"
        f"Method: <b>{method}</b>\n"
        f"Paid: <b>৳{request['paid_bdt']}</b>\n"
        f"Coins: <b>🪙 {request['coin_amount']}</b>\n"
        f"Transaction ID: <code>{escape(request['transaction_id'])}</code>\n"
        f"Status: {status}\n"
        f"Submitted: {request['created_at'][:16]}"
    )


@router.callback_query(F.data == "admin:topups")
async def list_topups(callback: CallbackQuery) -> None:
    requests = await pending_topup_requests()
    if not requests:
        await callback.answer("কোনো Pending top-up নেই।", show_alert=True)
        return
    await callback.message.edit_text(
        "💳 <b>Pending Top-up Requests</b>\n\n"
        "একটি request খুলে payment যাচাই করে Approve বা Reject করুন।",
        reply_markup=admin_topup_list_kb(requests),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:topup:view:"))
async def view_topup(callback: CallbackQuery) -> None:
    request_id = int(callback.data.split(":")[3])
    request = await get_topup_request(request_id)
    if not request:
        await callback.answer("Request পাওয়া যায়নি।", show_alert=True)
        return
    await callback.message.edit_text(
        _request_text(request),
        reply_markup=(
            admin_topup_review_kb(request_id)
            if request["status"] == "pending"
            else None
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:topup:approve:"))
async def approve_topup(callback: CallbackQuery, bot: Bot) -> None:
    request_id = int(callback.data.split(":")[3])
    result = await approve_topup_request(request_id, callback.from_user.id)
    if not result:
        await callback.answer("এই request ইতিমধ্যে review করা হয়েছে।", show_alert=True)
        return

    await callback.message.edit_text(
        "✅ <b>Top-up Approved</b>\n\n"
        f"Request: <code>#{result['request_id']}</code>\n"
        f"🪙 <b>{result['coin_amount']}</b> Coin যোগ হয়েছে\n"
        f"নতুন Balance: <b>{result['new_balance']}</b>",
        parse_mode="HTML",
    )
    try:
        await bot.send_message(
            result["user_id"],
            "✅ <b>আপনার Top-up Approved!</b>\n\n"
            f"🪙 <b>{result['coin_amount']}</b> Coin Wallet-এ যোগ হয়েছে।\n"
            f"বর্তমান Balance: <b>{result['new_balance']}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer("Approved এবং Coin যোগ হয়েছে।")


@router.callback_query(F.data.startswith("admin:topup:reject:"))
async def reject_topup(callback: CallbackQuery, bot: Bot) -> None:
    request_id = int(callback.data.split(":")[3])
    result = await reject_topup_request(request_id, callback.from_user.id)
    if not result:
        await callback.answer("এই request ইতিমধ্যে review করা হয়েছে।", show_alert=True)
        return

    await callback.message.edit_text(
        "❌ <b>Top-up Rejected</b>\n\n"
        f"Request: <code>#{result['request_id']}</code>\n"
        "কোনো Coin যোগ করা হয়নি।",
        parse_mode="HTML",
    )
    try:
        await bot.send_message(
            result["user_id"],
            "❌ আপনার Top-up request Reject করা হয়েছে।\n"
            "Transaction ID বা payment তথ্য যাচাই করে আবার চেষ্টা করুন।",
        )
    except Exception:
        pass
    await callback.answer("Request rejected হয়েছে।")