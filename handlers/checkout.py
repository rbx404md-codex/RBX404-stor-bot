from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery

from config import REFERRAL_REWARD_COIN
from database.queries import (
    get_product, get_user, adjust_coins, create_order, bump_sales,
    get_coupon, coupon_is_valid, coupon_already_used, redeem_coupon,
    mark_referral_rewarded, has_purchased, record_notification,
)
from services.channel_delivery import deliver_product
from services.payment_stars import send_stars_invoice
from utils.states import CouponInput

router = Router(name="checkout")


def _apply_coupon_to_price(price: int, coupon: dict) -> int:
    if coupon["discount_type"] == "percent":
        return max(0, price - (price * coupon["discount_value"] // 100))
    if coupon["discount_type"] == "fixed_coin":
        return max(0, price - coupon["discount_value"])
    return price


async def _reward_referrer_if_first_purchase(bot: Bot, buyer_id: int) -> None:
    referrer_id = await mark_referral_rewarded(buyer_id)
    if referrer_id:
        await adjust_coins(referrer_id, REFERRAL_REWARD_COIN, "Referral reward")
        await record_notification(
            referrer_id,
            "referral_reward",
            "Referral reward",
            f"+{REFERRAL_REWARD_COIN} coin যোগ হয়েছে।",
        )
        try:
            await bot.send_message(
                referrer_id,
                f"🎉 আপনার রেফার করা একজন ইউজার প্রথম কেনাকাটা করেছেন!\n"
                f"🪙 +{REFERRAL_REWARD_COIN} কয়েন যোগ হয়েছে।",
            )
        except Exception:  # noqa: BLE001 — user may have blocked the bot
            pass


# ------------------------------------------------------------ coin buy -----
@router.callback_query(F.data.startswith("buy:coin:"))
async def buy_with_coin(callback: CallbackQuery, bot: Bot) -> None:
    product_id = int(callback.data.split(":")[2])
    product = await get_product(product_id)
    if not product or not product["is_active"]:
        await callback.answer("প্রোডাক্টটি পাওয়া যায়নি।", show_alert=True)
        return

    try:
        await adjust_coins(callback.from_user.id, -product["price_coin"], f"Purchase: {product['name']}")
    except ValueError:
        await callback.answer("❌ পর্যাপ্ত কয়েন নেই। Wallet থেকে টপ-আপ করুন।", show_alert=True)
        return

    await create_order(callback.from_user.id, product_id, "coin", product["price_coin"])
    await bump_sales(product_id)
    await deliver_product(bot, callback.from_user.id, product["storage_msg_id"],
                           caption_extra=f"✅ কেনার জন্য ধন্যবাদ! এটি আপনি 📚 My Purchases থেকে যেকোনো সময় আবার পাবেন।")
    await _reward_referrer_if_first_purchase(bot, callback.from_user.id)
    await callback.answer("✅ কেনা সম্পন্ন হয়েছে!")


# ----------------------------------------------------------- stars buy -----
@router.callback_query(F.data.startswith("buy:stars:"))
async def buy_with_stars(callback: CallbackQuery, bot: Bot) -> None:
    product_id = int(callback.data.split(":")[2])
    product = await get_product(product_id)
    if not product or not product["is_active"]:
        await callback.answer("প্রোডাক্টটি পাওয়া যায়নি।", show_alert=True)
        return
    if product["price_stars"] <= 0:
        await callback.answer("এই প্রোডাক্টটি Stars দিয়ে কেনা যাবে না।", show_alert=True)
        return

    await send_stars_invoice(bot, callback.from_user.id, product_id, product["name"],
                              product["description"], product["price_stars"])
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_q: PreCheckoutQuery, bot: Bot) -> None:
    # Always approve unless the product vanished/was disabled meanwhile.
    product_id = int(pre_checkout_q.invoice_payload.split(":")[1])
    product = await get_product(product_id)
    if not product or not product["is_active"]:
        await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=False,
                                             error_message="প্রোডাক্টটি আর পাওয়া যাচ্ছে না।")
        return
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, bot: Bot) -> None:
    payload = message.successful_payment.invoice_payload
    product_id = int(payload.split(":")[1])
    product = await get_product(product_id)
    if not product:
        return

    order_id = await create_order(
        message.from_user.id,
        product_id,
        "stars",
        message.successful_payment.total_amount,
        external_payment_id=message.successful_payment.telegram_payment_charge_id,
    )
    if order_id is None:
        return
    await bump_sales(product_id)
    await record_notification(
        message.from_user.id,
        "purchase",
        "Purchase successful",
        f"{product['name']} Stars payment দিয়ে কেনা হয়েছে।",
    )
    await deliver_product(bot, message.from_user.id, product["storage_msg_id"],
                           caption_extra="✅ Stars পেমেন্ট সফল হয়েছে, এখানে আপনার প্রোডাক্ট।")
    await _reward_referrer_if_first_purchase(bot, message.from_user.id)


# ------------------------------------------------------------- coupon ------
@router.callback_query(F.data.startswith("buy:coupon:"))
async def ask_coupon(callback: CallbackQuery, state: FSMContext) -> None:
    product_id = int(callback.data.split(":")[2])
    await state.update_data(product_id=product_id)
    await state.set_state(CouponInput.waiting_code)
    await callback.message.answer("🎟️ কুপন কোড লিখুন:")
    await callback.answer()


@router.message(CouponInput.waiting_code)
async def apply_coupon(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    product_id = data["product_id"]
    await state.clear()

    product = await get_product(product_id)
    if not product or not product["is_active"]:
        await message.answer("প্রোডাক্টটি আর পাওয়া যাচ্ছে না।")
        return

    code = message.text.strip().upper()
    coupon = await get_coupon(code)
    valid, err = coupon_is_valid(coupon)
    if not valid:
        await message.answer(f"❌ {err}")
        return
    if await coupon_already_used(code, message.from_user.id):
        await message.answer("❌ আপনি ইতিমধ্যে এই কুপন ব্যবহার করেছেন।")
        return

    final_price = _apply_coupon_to_price(product["price_coin"], coupon)
    try:
        await adjust_coins(message.from_user.id, -final_price, f"Purchase w/ coupon {code}: {product['name']}")
    except ValueError:
        await message.answer(f"❌ পর্যাপ্ত কয়েন নেই। কুপন প্রয়োগের পর দাম: 🪙 {final_price}")
        return

    await redeem_coupon(code, message.from_user.id)
    await create_order(message.from_user.id, product_id, "coin", final_price, coupon_code=code)
    await bump_sales(product_id)
    await deliver_product(bot, message.from_user.id, product["storage_msg_id"],
                           caption_extra=f"✅ কুপন '{code}' প্রয়োগ হয়েছে! মূল্য দিতে হয়েছে 🪙 {final_price}")
    await _reward_referrer_if_first_purchase(bot, message.from_user.id)
