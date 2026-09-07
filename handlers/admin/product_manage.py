from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from html import escape

from config import STORAGE_CHANNEL_ID
from database.queries import add_category, list_categories, add_product, list_products, get_product, set_product_active
from utils.filters import IsAdmin
from utils.keyboards import admin_product_list_kb
from utils.states import AdminAddCategory, AdminAddProduct

router = Router(name="admin_products")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# --------------------------------------------------------------- category --
@router.callback_query(F.data == "admin:add_category")
async def start_add_category(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminAddCategory.waiting_name)
    await callback.message.answer("📂 নতুন ক্যাটাগরির নাম লিখুন (ইমোজি সহ চাইলে, যেমন: 🎬 Video Courses):")
    await callback.answer()


@router.message(AdminAddCategory.waiting_name)
async def save_category(message: Message, state: FSMContext) -> None:
    await state.clear()
    name = message.text.strip()
    cat_id = await add_category(name)
    await message.answer(f"✅ ক্যাটাগরি তৈরি হয়েছে: {escape(name)} (ID: {cat_id})")


# ---------------------------------------------------------------- product --
@router.callback_query(F.data == "admin:add_product")
async def start_add_product(callback: CallbackQuery, state: FSMContext) -> None:
    cats = await list_categories()
    if not cats:
        await callback.answer("আগে একটা ক্যাটাগরি বানান।", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    for c in cats:
        kb.button(text=f"{c['icon']} {c['name']}", callback_data=f"admin:addprod:cat:{c['category_id']}")
    kb.adjust(2)
    await state.set_state(AdminAddProduct.waiting_category)
    await callback.message.answer("📂 কোন ক্যাটাগরিতে প্রোডাক্ট যোগ হবে?", reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(AdminAddProduct.waiting_category, F.data.startswith("admin:addprod:cat:"))
async def choose_category(callback: CallbackQuery, state: FSMContext) -> None:
    category_id = int(callback.data.split(":")[3])
    await state.update_data(category_id=category_id)
    await state.set_state(AdminAddProduct.waiting_name)
    await callback.message.answer("✏️ প্রোডাক্টের নাম লিখুন:")
    await callback.answer()


@router.message(AdminAddProduct.waiting_name)
async def set_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(AdminAddProduct.waiting_description)
    await message.answer("📝 বিবরণ লিখুন:")


@router.message(AdminAddProduct.waiting_description)
async def set_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await state.set_state(AdminAddProduct.waiting_price_coin)
    await message.answer("🪙 কয়েন দাম লিখুন (শুধু সংখ্যা, Coin দিয়ে বিক্রি না করলে 0 দিন):")


@router.message(AdminAddProduct.waiting_price_coin)
async def set_price_coin(message: Message, state: FSMContext) -> None:
    if not message.text.strip().isdigit():
        await message.answer("❌ শুধু সংখ্যা দিন।")
        return
    await state.update_data(price_coin=int(message.text.strip()))
    await state.set_state(AdminAddProduct.waiting_price_stars)
    await message.answer("⭐ Stars দাম লিখুন (Stars দিয়ে বিক্রি না করলে 0 দিন):")


@router.message(AdminAddProduct.waiting_price_stars)
async def set_price_stars(message: Message, state: FSMContext) -> None:
    if not message.text.strip().isdigit():
        await message.answer("❌ শুধু সংখ্যা দিন।")
        return
    await state.update_data(price_stars=int(message.text.strip()))
    await state.set_state(AdminAddProduct.waiting_file)
    await message.answer(
        "📎 এবার আসল ফাইলটি (ভিডিও/ডকুমেন্ট/ছবি/ইত্যাদি) এখানে সরাসরি পাঠান — "
        "এটি অটো-স্টোরেজ চ্যানেলে সেভ হয়ে যাবে, সার্ভারে কিছু থাকবে না।"
    )


@router.message(AdminAddProduct.waiting_file, F.content_type.in_({"document", "video", "photo", "audio"}))
async def set_file(message: Message, state: FSMContext, bot: Bot) -> None:
    # copy the admin's uploaded file into the storage channel — that copy's
    # message_id is what we keep forever; the original chat message is irrelevant.
    copied = await bot.copy_message(
        chat_id=STORAGE_CHANNEL_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )
    await state.update_data(storage_msg_id=copied.message_id)
    await state.set_state(AdminAddProduct.waiting_preview)
    await message.answer(
        "🔍 চাইলে একটা প্রিভিউ/স্যাম্পল ফাইল পাঠান (ক্রেতা কেনার আগে দেখতে পারবে), "
        "না দিতে চাইলে /skip লিখুন।"
    )


@router.message(AdminAddProduct.waiting_file)
async def wrong_file_type(message: Message) -> None:
    await message.answer("❌ দয়া করে একটি ফাইল/ভিডিও/ছবি/ডকুমেন্ট পাঠান।")


async def _finalize_product(data: dict, preview_msg_id: int | None, message: Message, state: FSMContext) -> None:
    product_id = await add_product(
        category_id=data["category_id"],
        name=data["name"],
        description=data["description"],
        price_coin=data["price_coin"],
        price_stars=data["price_stars"],
        storage_msg_id=data["storage_msg_id"],
        preview_msg_id=preview_msg_id,
    )
    await state.clear()
    await message.answer(
        f"✅ প্রোডাক্ট যোগ হয়েছে!\nID: {product_id}\nনাম: {escape(data['name'])}"
    )


@router.message(AdminAddProduct.waiting_preview, Command("skip"))
async def skip_preview(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await _finalize_product(data, None, message, state)


@router.message(AdminAddProduct.waiting_preview, F.content_type.in_({"document", "video", "photo", "audio"}))
async def set_preview(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    copied = await bot.copy_message(
        chat_id=STORAGE_CHANNEL_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )
    await _finalize_product(data, copied.message_id, message, state)


@router.message(AdminAddProduct.waiting_preview)
async def wrong_preview_type(message: Message) -> None:
    await message.answer("❌ ফাইল পাঠান অথবা /skip লিখুন।")


# ------------------------------------------------------------ manage list --
@router.callback_query(F.data == "admin:list_products")
async def list_all_products(callback: CallbackQuery) -> None:
    products = await list_products(active_only=False)
    if not products:
        await callback.answer("কোনো প্রোডাক্ট নেই।", show_alert=True)
        return
    await callback.message.edit_text(
        "📋 <b>সব প্রোডাক্ট</b> (ট্যাপ করে Enable/Disable করুন):",
        reply_markup=admin_product_list_kb(products),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:toggle_product:"))
async def toggle_product(callback: CallbackQuery) -> None:
    product_id = int(callback.data.split(":")[2])
    p = await get_product(product_id)
    if not p:
        await callback.answer("প্রোডাক্টটি পাওয়া যায়নি।", show_alert=True)
        return
    await set_product_active(product_id, not bool(p["is_active"]))
    products = await list_products(active_only=False)
    await callback.message.edit_text(
        "📋 <b>সব প্রোডাক্ট</b> (ট্যাপ করে Enable/Disable করুন):",
        reply_markup=admin_product_list_kb(products),
        parse_mode="HTML",
    )
    await callback.answer("✅ স্ট্যাটাস পরিবর্তন হয়েছে।")
