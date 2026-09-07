"""Universal opaque Telegram share links.

The bot stores file IDs server-side and exposes only a short random token.
The browser portal resolves the token back through Telegram's file API.
"""
from datetime import datetime, timedelta
from hashlib import sha256
from html import escape
from io import BytesIO

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import LINK_DEFAULT_EXPIRY_HOURS, PUBLIC_PORTAL_URL
from database.queries import (
    create_shared_link,
    delete_shared_link,
    get_shared_link,
    list_shared_links,
    set_shared_link_active,
)
from utils.keyboards import link_list_kb, main_menu
from utils.states import LinkGenInput

router = Router(name="linkgen")


def _content_from_message(message: Message) -> dict | None:
    if message.text and not message.text.startswith("/"):
        return {"content_type": "text", "text_content": message.text[:10000]}
    if message.document:
        return {
            "content_type": "document",
            "file_id": message.document.file_id,
            "file_name": message.document.file_name or "document",
            "mime_type": message.document.mime_type,
        }
    if message.photo:
        return {
            "content_type": "photo",
            "file_id": message.photo[-1].file_id,
            "file_name": "photo.jpg",
            "mime_type": "image/jpeg",
        }
    if message.video:
        return {
            "content_type": "video",
            "file_id": message.video.file_id,
            "file_name": message.video.file_name or "video.mp4",
            "mime_type": message.video.mime_type or "video/mp4",
        }
    if message.audio:
        return {
            "content_type": "audio",
            "file_id": message.audio.file_id,
            "file_name": message.audio.file_name or "audio",
            "mime_type": message.audio.mime_type or "audio/mpeg",
        }
    if message.voice:
        return {
            "content_type": "voice",
            "file_id": message.voice.file_id,
            "file_name": "voice.ogg",
            "mime_type": "audio/ogg",
        }
    if message.animation:
        return {
            "content_type": "animation",
            "file_id": message.animation.file_id,
            "file_name": message.animation.file_name or "animation.gif",
            "mime_type": message.animation.mime_type or "image/gif",
        }
    return None


def _parse_options(raw: str) -> tuple[str | None, bool, int, str | None]:
    expires_at = None
    one_time = False
    max_views = 0
    password_hash = None
    for part in raw.lower().replace(",", " ").split():
        if part in {"one-time", "onetime", "once"}:
            one_time = True
        elif part.startswith("hours="):
            try:
                hours = max(1, int(part.split("=", 1)[1]))
                expires_at = (datetime.utcnow() + timedelta(hours=hours)).isoformat()
            except ValueError:
                pass
        elif part.startswith("max="):
            try:
                max_views = max(0, int(part.split("=", 1)[1]))
            except ValueError:
                pass
        elif part.startswith("password=") and len(part.split("=", 1)[1]) >= 4:
            password_hash = sha256(part.split("=", 1)[1].encode()).hexdigest()
    if expires_at is None and LINK_DEFAULT_EXPIRY_HOURS > 0:
        expires_at = (
            datetime.utcnow() + timedelta(hours=LINK_DEFAULT_EXPIRY_HOURS)
        ).isoformat()
    return expires_at, one_time, max_views, password_hash


def _public_link(token: str) -> str:
    return f"{PUBLIC_PORTAL_URL}/link/{token}" if PUBLIC_PORTAL_URL else f"/link/{token}"


async def _start_linkgen(message: Message, state: FSMContext) -> None:
    await state.set_state(LinkGenInput.waiting_content)
    await message.answer(
        "🔗 <b>Universal Link Generator</b>\n\n"
        "📤 Text, document, photo, video, audio, voice বা GIF পাঠান।\n"
        "এরপর চাইলে options দিন: <code>hours=24 max=10 one-time password=abcd</code>\n\n"
        "❌ থামাতে /cancel লিখুন।",
        parse_mode="HTML",
    )


@router.message(Command("linkgen"))
async def linkgen_command(message: Message, state: FSMContext) -> None:
    await _start_linkgen(message, state)


@router.callback_query(F.data == "linkgen:start")
async def linkgen_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await _start_linkgen(callback.message, state)
    await callback.answer()


@router.message(LinkGenInput.waiting_content)
async def capture_link_content(message: Message, state: FSMContext) -> None:
    content = _content_from_message(message)
    if not content:
        await message.answer("❌ সমর্থিত text বা media পাঠান।")
        return
    await state.update_data(**content)
    await state.set_state(LinkGenInput.waiting_options)
    await message.answer(
        "⚙️ Link options দিন অথবা <code>skip</code> লিখুন:\n"
        "• <code>hours=24</code> — expiry\n"
        "• <code>max=10</code> — maximum views\n"
        "• <code>one-time</code> — একবার access\n"
        "• <code>password=abcd</code> — password protection",
        parse_mode="HTML",
    )


@router.message(LinkGenInput.waiting_options)
async def create_link(message: Message, state: FSMContext) -> None:
    options = (message.text or "").strip()
    data = await state.get_data()
    expires_at, one_time, max_views, password_hash = _parse_options(
        "" if options.lower() == "skip" else options
    )
    token = await create_shared_link(
        message.from_user.id,
        data["content_type"],
        file_id=data.get("file_id"),
        text_content=data.get("text_content"),
        file_name=data.get("file_name"),
        mime_type=data.get("mime_type"),
        expires_at=expires_at,
        one_time=one_time,
        max_views=max_views,
        password_hash=password_hash,
    )
    await state.clear()
    expiry = expires_at or "Never"
    await message.answer(
        "✅ <b>Link Generated</b>\n\n"
        f"🔗 <code>{escape(_public_link(token))}</code>\n"
        f"👁 Views: <b>0</b>\n"
        f"⏳ Expires: <b>{escape(expiry)}</b>\n"
        f"🛡 Protected: <b>{'Yes' if password_hash else 'No'}</b>",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


@router.message(Command("mylinks"))
async def my_links(message: Message) -> None:
    links = await list_shared_links(message.from_user.id)
    if not links:
        await message.answer("🔗 এখনো কোনো shared link নেই। /linkgen ব্যবহার করুন।")
        return
    await message.answer(
        "🔗 <b>আপনার generated links</b>\n"
        "একটি link disable/enable করতে নিচের token চাপুন।",
        reply_markup=link_list_kb(links),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("link:toggle:"))
async def toggle_link(callback: CallbackQuery) -> None:
    token = callback.data.split(":", 2)[2]
    link = await get_shared_link(token)
    if not link or link["owner_id"] != callback.from_user.id:
        await callback.answer("এই link আপনার নয়।", show_alert=True)
        return
    await set_shared_link_active(token, callback.from_user.id, not bool(link["is_active"]))
    await callback.answer("Link status আপডেট হয়েছে।")


@router.callback_query(F.data.startswith("link:delete:"))
async def delete_link(callback: CallbackQuery) -> None:
    token = callback.data.split(":", 2)[2]
    if not await delete_shared_link(token, callback.from_user.id):
        await callback.answer("এই link পাওয়া যায়নি।", show_alert=True)
        return
    await callback.answer("Link permanently deleted হয়েছে।", show_alert=True)
    await my_links(callback.message)