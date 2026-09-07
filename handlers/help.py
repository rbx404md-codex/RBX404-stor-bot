from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from utils.keyboards import help_kb

router = Router(name="help")

HELP_TEXT = (
    "ℹ️ <b>কীভাবে ব্যবহার করবেন</b>\n\n"
    "🛍️ <b>Store</b> থেকে Category ও Product বেছে নিন। "
    "Coin, Telegram Stars অথবা Coupon দিয়ে কিনতে পারবেন।\n\n"
    "🪙 <b>Wallet</b> থেকে Balance, Transaction History ও Coin Top-up দেখুন।\n\n"
    "🎁 <b>Referral</b> থেকে নিজের link share করুন।\n\n"
    "📚 <b>My Purchases</b> থেকে আগে কেনা file আবার download করুন।\n\n"
    "কোনো multi-step কাজ থামাতে `/cancel` লিখুন।"
)

FAQ_TEXT = (
    "❓ <b>FAQ</b>\n\n"
    "<b>কীভাবে কিনব?</b>\nStore থেকে Product বেছে Coin বা Telegram Stars দিয়ে Pay করুন।\n\n"
    "<b>Payment-এর পর file কোথায়?</b>\nPayment সফল হলে file সরাসরি Telegram chat-এ delivery হবে।\n\n"
    "<b>Coin top-up কতক্ষণ লাগে?</b>\nSend Money করে Transaction ID পাঠালে Admin verify করে approve করবেন।\n\n"
    "<b>ভুল Product কিনলে?</b>\nকেনার আগে description ও preview ভালোভাবে দেখে নিন; Support-এ ticket করতে পারেন।"
)

TERMS_TEXT = (
    "📜 <b>Terms of Service</b>\n\n"
    "• Payment দেওয়ার আগে Product, price ও preview যাচাই করুন।\n"
    "• Digital delivery হওয়ার পর refund সাধারণত প্রযোজ্য নয়; সমস্যা হলে Support ticket করুন।\n"
    "• Account abuse, fraud বা payment dispute-এর ক্ষেত্রে access বন্ধ হতে পারে।\n"
    "• Admin verification ছাড়া কোনো Coin balance change হবে না।"
)

PRIVACY_TEXT = (
    "🔒 <b>Privacy Notice</b>\n\n"
    "বট আপনার Telegram user ID, username, wallet/order metadata এবং support/payment "
    "verification-এর জন্য পাঠানো Transaction ID সংরক্ষণ করে।\n\n"
    "আসল digital file bot server-এ রাখা হয় না; Telegram Storage Channel-এ থাকে। "
    "আপনার তথ্য বিক্রি করা হয় না এবং শুধুমাত্র Store service পরিচালনায় ব্যবহার করা হয়।"
)


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=help_kb(), parse_mode="HTML")


@router.callback_query(F.data == "help:open")
async def help_callback(callback: CallbackQuery) -> None:
    await callback.message.answer(HELP_TEXT, reply_markup=help_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "help:faq")
async def faq_callback(callback: CallbackQuery) -> None:
    await callback.message.answer(FAQ_TEXT, reply_markup=help_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "help:terms")
async def terms_callback(callback: CallbackQuery) -> None:
    await callback.message.answer(TERMS_TEXT, reply_markup=help_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "help:privacy")
async def privacy_callback(callback: CallbackQuery) -> None:
    await callback.message.answer(PRIVACY_TEXT, reply_markup=help_kb(), parse_mode="HTML")
    await callback.answer()