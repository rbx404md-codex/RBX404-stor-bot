from html import escape

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS, ADMIN_USERNAME, BKASH_NUMBER, NAGAD_NUMBER
from database.queries import (
    create_topup_request,
    user_topup_requests,
)
from utils.keyboards import admin_topup_review_kb, topup_kb, topup_method_kb
from utils.states import TopupInput

router = Router(name="topup")

PAYMENT_METHODS = {
    "bkash": "bKash",
    "nagad": "Nagad",
}


def payment_instructions() -> str:
    return (
        "💳 <b>Coin Top-up</b>\n\n"
        "নিচের নম্বরে <b>Send Money</b> করে Transaction ID জমা দিন। "
        "অ্যাডমিন যাচাই করে অনুমোদন করলে Coin আপনার Wallet-এ যোগ হবে।\n\n"
        f"🟣 bKash: <code>{BKASH_NUMBER}</code>\n"
        f"🟠 Nagad: <code>{NAGAD_NUMBER}</code>\n\n"
        f"👤 সহায়তা: <a href=\"https://t.me/{escape(ADMIN_USERNAME)}\">@{escape(ADMIN_USERNAME)}</a>\n\n"
        "⚠️ Cash Out/Payment নয়—শুধু Send Money ব্যবহার করুন।"
    )


def _status_label(status: str) -> str:
    return {
        "pending": "⏳ Pending",
        "approved": "✅ Approved",
        "rejected": "❌ Rejected",
    }.get(status, status.title())


@router.callback_query(F.data == "topup:status")
async def topup_status(callback: CallbackQuery) -> None:
    requests = await user_topup_requests(callback.from_user.id)
    if not requests:
        await callback.answer("এখনো কোনো Top-up request নেই।", show_alert=True)
        return

    lines = ["📋 <b>আপনার Top-up Requests</b>\n"]
    for request in requests:
        method = PAYMENT_METHODS.get(request["payment_method"], request["payment_method"])
        lines.append(
            f"#{request['request_id']} · {method} · 🪙 {request['coin_amount']}\n"
            f"💰 ৳{request['paid_bdt']} · Txn: <code>{escape(request['transaction_id'])}</code>\n"
            f"{_status_label(request['status'])} · {request['created_at'][:16]}\n"
        )
    await callback.message.answer("\n".join(lines), reply_markup=topup_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "wallet:topup")
async def open_topup(callback: CallbackQuery) -> None:
    await callback.message.answer(
        payment_instructions(),
        reply_markup=topup_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "topup:start")
async def start_topup(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TopupInput.waiting_method)
    await callback.message.answer(
        "💳 কোন মাধ্যমে Send Money করেছেন?",
        reply_markup=topup_method_kb(),
    )
    await callback.answer()


@router.callback_query(TopupInput.waiting_method, F.data.startswith("topup:method:"))
async def choose_topup_method(callback: CallbackQuery, state: FSMContext) -> None:
    method = callback.data.split(":")[2]
    if method not in PAYMENT_METHODS:
        await callback.answer("Payment method সঠিক নয়।", show_alert=True)
        return
    await state.update_data(payment_method=method)
    await state.set_state(TopupInput.waiting_paid_bdt)
    await callback.message.answer("💰 কত টাকা Send Money করেছেন? শুধু সংখ্যা লিখুন।")
    await callback.answer()


@router.message(TopupInput.waiting_paid_bdt)
async def topup_paid_amount(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if not value.isdigit() or int(value) <= 0:
        await message.answer("❌ সঠিক টাকার পরিমাণ লিখুন, যেমন: 100")
        return
    await state.update_data(paid_bdt=int(value))
    await state.set_state(TopupInput.waiting_coin_amount)
    await message.answer(
        "🪙 কত Coin Wallet-এ যোগ করতে চান? "
        "অ্যাডমিন পেমেন্ট দেখে অনুমোদন করবেন।"
    )


@router.message(TopupInput.waiting_coin_amount)
async def topup_coin_amount(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if not value.isdigit() or int(value) <= 0:
        await message.answer("❌ সঠিক Coin amount লিখুন, যেমন: 100")
        return
    await state.update_data(coin_amount=int(value))
    await state.set_state(TopupInput.waiting_transaction_id)
    await message.answer(
        "🧾 এখন bKash/Nagad Transaction ID লিখুন।\n"
        "একই Transaction ID একবারের বেশি ব্যবহার করা যাবে না।"
    )


@router.message(TopupInput.waiting_transaction_id)
async def topup_transaction_id(message: Message, state: FSMContext, bot: Bot) -> None:
    transaction_id = (message.text or "").strip()
    if len(transaction_id) < 3 or len(transaction_id) > 100:
        await message.answer("❌ সঠিক Transaction ID লিখুন।")
        return

    data = await state.get_data()
    request_id = await create_topup_request(
        user_id=message.from_user.id,
        payment_method=data["payment_method"],
        paid_bdt=data["paid_bdt"],
        coin_amount=data["coin_amount"],
        transaction_id=transaction_id,
    )
    if request_id is None:
        await message.answer(
            "❌ এই Transaction ID আগে জমা হয়েছে। সঠিক নতুন Transaction ID দিন।"
        )
        return

    await state.clear()
    await message.answer(
        f"✅ Top-up request জমা হয়েছে!\n\n"
        f"Request ID: <code>#{request_id}</code>\n"
        f"🪙 Coin: <b>{data['coin_amount']}</b>\n"
        f"🧾 Transaction ID: <code>{escape(transaction_id)}</code>\n\n"
        "অ্যাডমিন যাচাই করার পর আপনার Wallet আপডেট হবে।",
        reply_markup=topup_kb(),
        parse_mode="HTML",
    )

    username = (
        f"@{escape(message.from_user.username)}"
        if message.from_user.username
        else "username নেই"
    )
    method = PAYMENT_METHODS[data["payment_method"]]
    admin_text = (
        "🔔 <b>নতুন Coin Top-up Request</b>\n\n"
        f"Request: <code>#{request_id}</code>\n"
        f"User: {username}\n"
        f"User ID: <code>{message.from_user.id}</code>\n"
        f"Method: <b>{method}</b>\n"
        f"Paid: <b>৳{data['paid_bdt']}</b>\n"
        f"Requested: <b>🪙 {data['coin_amount']}</b>\n"
        f"Transaction ID: <code>{escape(transaction_id)}</code>"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                admin_text,
                reply_markup=admin_topup_review_kb(request_id),
                parse_mode="HTML",
            )
        except Exception:
            # An admin may have blocked the bot; the request remains in the panel.
            pass