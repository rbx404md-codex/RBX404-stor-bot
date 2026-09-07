from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS, DAILY_CHECKIN_REWARD
from database.queries import (
    add_review,
    claim_daily_checkin,
    create_support_ticket,
    get_product,
    get_user,
    is_wishlisted,
    product_rating,
    product_reviews,
    referral_leaderboard,
    search_products,
    toggle_wishlist,
    user_wishlist,
    has_purchased,
)
from utils.keyboards import (
    rating_kb,
    search_results_kb,
    support_admin_kb,
    wishlist_kb,
)
from utils.states import ReviewInput, SearchInput, SupportInput

router = Router(name="features")


@router.callback_query(F.data == "search:start")
async def start_search(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SearchInput.waiting_query)
    await callback.message.answer("🔎 Product name বা keyword লিখুন:")
    await callback.answer()


@router.message(Command("search"))
async def search_command(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchInput.waiting_query)
    await message.answer("🔎 Product name বা keyword লিখুন:")


@router.message(SearchInput.waiting_query)
async def search_submit(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()
    if len(query) < 2:
        await message.answer("❌ অন্তত ২টি অক্ষর লিখুন।")
        return
    await state.clear()
    products = await search_products(query)
    if not products:
        await message.answer(f"🔎 “{escape(query)}” দিয়ে কোনো Product পাওয়া যায়নি।")
        return
    await message.answer(
        f"🔎 <b>{escape(query)}</b> — {len(products)}টি result",
        reply_markup=search_results_kb(products),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "wishlist:list")
async def wishlist_list(callback: CallbackQuery) -> None:
    products = await user_wishlist(callback.from_user.id)
    if not products:
        await callback.answer("আপনার Wishlist এখনো খালি।", show_alert=True)
        return
    await callback.message.answer(
        "❤️ <b>আপনার Wishlist</b>",
        reply_markup=wishlist_kb(products),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("wishlist:toggle:"))
async def wishlist_toggle(callback: CallbackQuery) -> None:
    product_id = int(callback.data.split(":")[2])
    product = await get_product(product_id)
    if not product or not product["is_active"]:
        await callback.answer("Product পাওয়া যায়নি।", show_alert=True)
        return
    added = await toggle_wishlist(callback.from_user.id, product_id)
    await callback.answer("❤️ Wishlist-এ যোগ হয়েছে।" if added else "Wishlist থেকে সরানো হয়েছে।")


@router.callback_query(F.data.startswith("product:reviews:"))
async def show_reviews(callback: CallbackQuery) -> None:
    product_id = int(callback.data.split(":")[2])
    product = await get_product(product_id)
    if not product:
        await callback.answer("Product পাওয়া যায়নি।", show_alert=True)
        return
    rating = await product_rating(product_id)
    reviews = await product_reviews(product_id)
    lines = [
        f"⭐ <b>{escape(product['name'])}</b>",
        f"Rating: <b>{rating['average']}/5</b> ({rating['count']}টি review)\n",
    ]
    for item in reviews:
        author = f"@{escape(item['username'])}" if item.get("username") else "একজন ক্রেতা"
        text = escape(item["review"]) if item["review"] else "শুধু rating দিয়েছেন"
        lines.append(f"⭐ {item['rating']}/5 · {author}\n{text}\n")
    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "daily:checkin")
async def daily_checkin(callback: CallbackQuery) -> None:
    new_balance = await claim_daily_checkin(callback.from_user.id, DAILY_CHECKIN_REWARD)
    if new_balance is None:
        await callback.answer("আজকের Daily Bonus ইতিমধ্যে নেওয়া হয়েছে।", show_alert=True)
        return
    await callback.message.answer(
        f"🎁 আজকের Bonus পেয়েছেন: <b>+{DAILY_CHECKIN_REWARD} Coin</b>\n"
        f"বর্তমান Balance: <b>{new_balance}</b>",
        parse_mode="HTML",
    )
    await callback.answer("Daily Bonus যোগ হয়েছে।")


@router.message(Command("checkin"))
async def daily_command(message: Message) -> None:
    new_balance = await claim_daily_checkin(message.from_user.id, DAILY_CHECKIN_REWARD)
    if new_balance is None:
        await message.answer("আজকের Daily Bonus ইতিমধ্যে নেওয়া হয়েছে।")
        return
    await message.answer(
        f"🎁 +{DAILY_CHECKIN_REWARD} Coin যোগ হয়েছে। Balance: {new_balance}"
    )


@router.callback_query(F.data == "referral:leaderboard")
async def referral_leaderboard_view(callback: CallbackQuery) -> None:
    rows = await referral_leaderboard()
    if not rows:
        await callback.answer("Leaderboard-এ এখনো কোনো data নেই।", show_alert=True)
        return
    lines = ["🏆 <b>Referral Leaderboard</b>\n"]
    for index, row in enumerate(rows, 1):
        user = await get_user(row["referrer_id"])
        name = f"@{escape(user['username'])}" if user and user.get("username") else str(row["referrer_id"])
        lines.append(f"{index}. {name} — {row['cnt']} জন")
    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "support:open")
async def support_open(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SupportInput.waiting_message)
    await callback.message.answer(
        "🆘 আপনার সমস্যা বা প্রশ্নটি লিখুন।\n"
        "অ্যাডমিন reply না করা পর্যন্ত ticket Open থাকবে।"
    )
    await callback.answer()


@router.message(Command("support"))
async def support_command(message: Message, state: FSMContext) -> None:
    await state.set_state(SupportInput.waiting_message)
    await message.answer("🆘 আপনার সমস্যা বা প্রশ্নটি লিখুন:")


@router.message(SupportInput.waiting_message)
async def support_submit(message: Message, state: FSMContext, bot: Bot) -> None:
    text = (message.text or "").strip()
    if len(text) < 5:
        await message.answer("❌ একটু বিস্তারিত লিখুন।")
        return
    ticket_id = await create_support_ticket(message.from_user.id, text)
    await state.clear()
    await message.answer(
        f"✅ Support ticket <code>#{ticket_id}</code> তৈরি হয়েছে।\n"
        "অ্যাডমিন শিগগিরই উত্তর দেবেন।",
        parse_mode="HTML",
    )
    username = f"@{escape(message.from_user.username)}" if message.from_user.username else "username নেই"
    admin_text = (
        "🆘 <b>নতুন Support Ticket</b>\n\n"
        f"Ticket: <code>#{ticket_id}</code>\n"
        f"User: {username}\n"
        f"User ID: <code>{message.from_user.id}</code>\n\n"
        f"{escape(text)}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                admin_text,
                reply_markup=support_admin_kb(ticket_id),
                parse_mode="HTML",
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("review:start:"))
async def start_review(callback: CallbackQuery, state: FSMContext) -> None:
    product_id = int(callback.data.split(":")[2])
    if not await has_purchased(callback.from_user.id, product_id):
        await callback.answer("কেনার পরেই review দিতে পারবেন।", show_alert=True)
        return
    await state.update_data(product_id=product_id)
    await state.set_state(ReviewInput.waiting_rating)
    await callback.message.answer("এই Product-কে কত ⭐ rating দেবেন?", reply_markup=rating_kb(product_id))
    await callback.answer()


@router.callback_query(ReviewInput.waiting_rating, F.data.startswith("review:rating:"))
async def review_rating(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    product_id, rating = int(parts[2]), int(parts[3])
    await state.update_data(product_id=product_id, rating=rating)
    await state.set_state(ReviewInput.waiting_review)
    await callback.message.answer("এক লাইনে review লিখুন, না চাইলে `-` লিখুন:")
    await callback.answer()


@router.message(ReviewInput.waiting_review)
async def review_submit(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    review = (message.text or "").strip()
    await add_review(
        message.from_user.id,
        data["product_id"],
        data["rating"],
        "" if review == "-" else review[:500],
    )
    await state.clear()
    await message.answer("✅ আপনার review সংরক্ষণ হয়েছে। ধন্যবাদ!")