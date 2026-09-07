from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database.queries import (
    get_user,
    refund_order,
    set_user_muted,
    set_user_premium,
    user_report,
)
from utils.filters import IsAdmin

router = Router(name="admin_security")
router.message.filter(IsAdmin())


@router.message(Command("user"))
async def user_command(message: Message) -> None:
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("ব্যবহার: <code>/user 123456789</code>", parse_mode="HTML")
        return
    report = await user_report(int(parts[1]))
    if not report:
        await message.answer("❌ User পাওয়া যায়নি।")
        return
    username = f"@{escape(report['username'])}" if report.get("username") else "username নেই"
    await message.answer(
        "👤 <b>User Profile</b>\n\n"
        f"ID: <code>{report['user_id']}</code>\n"
        f"Username: {username}\n"
        f"Balance: 🪙 {report['coin_balance']}\n"
        f"Orders: {report['order_count']}\n"
        f"Active referrals: {report['active_referrals']}\n"
        f"Generated links: {report['link_count']}\n"
        f"Language: {report['language']}\n"
        f"Premium: {'Yes' if report.get('is_premium') else 'No'}\n"
        f"Muted: {'Yes' if report.get('is_muted') else 'No'}\n"
        f"Banned: {'Yes' if report.get('is_banned') else 'No'}\n"
        f"Joined: {report['joined_at']}\n"
        f"Last seen: {report.get('last_seen_at') or '—'}",
        parse_mode="HTML",
    )


@router.message(Command("mute"))
async def mute_command(message: Message) -> None:
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("ব্যবহার: <code>/mute 123456789</code>", parse_mode="HTML")
        return
    user_id = int(parts[1])
    if not await get_user(user_id):
        await message.answer("❌ User পাওয়া যায়নি।")
        return
    user = await get_user(user_id)
    muted = not bool(user.get("is_muted"))
    await set_user_muted(user_id, muted)
    await message.answer(f"✅ User {'muted' if muted else 'unmuted'} হয়েছে।")


@router.message(Command("premium"))
async def premium_command(message: Message) -> None:
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("ব্যবহার: <code>/premium 123456789</code>", parse_mode="HTML")
        return
    user_id = int(parts[1])
    user = await get_user(user_id)
    if not user:
        await message.answer("❌ User পাওয়া যায়নি।")
        return
    premium = not bool(user.get("is_premium"))
    await set_user_premium(user_id, premium)
    await message.answer(f"✅ Premium status {'enabled' if premium else 'disabled'} হয়েছে।")


@router.message(Command("refund"))
async def refund_command(message: Message, bot) -> None:
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("ব্যবহার: <code>/refund ORDER_ID</code>", parse_mode="HTML")
        return
    result = await refund_order(int(parts[1]), message.from_user.id)
    if not result:
        await message.answer("❌ শুধু completed coin order একবার refund করা যায়।")
        return
    await message.answer(
        f"✅ Order <code>#{result['order_id']}</code> refund হয়েছে।\n"
        f"🪙 {result['amount_paid']} coin ফেরত। নতুন balance: {result['new_balance']}",
        parse_mode="HTML",
    )
    try:
        await bot.send_message(
            result["user_id"],
            f"✅ আপনার order <code>#{result['order_id']}</code> refund হয়েছে।\n"
            f"🪙 {result['amount_paid']} coin wallet-এ ফেরত দেওয়া হয়েছে।",
            parse_mode="HTML",
        )
    except Exception:
        pass