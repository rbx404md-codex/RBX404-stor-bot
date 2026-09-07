"""
The sqlite file is the entire state of the bot. We never rely on the local
disk surviving (Termux gets killed, Railway disks are ephemeral) — instead
we push the db file to a private Telegram channel on a timer, and on every
boot we try to pull the newest copy down before starting the bot, if no
local copy exists yet.

This is what lets you `git clone` the project on a brand-new machine,
just fill in .env, run `python main.py`, and get your real data back.
"""
import os
import logging

from aiogram import Bot
from aiogram.types import BufferedInputFile, FSInputFile

from config import DB_PATH, BACKUP_CHANNEL_ID

log = logging.getLogger("backup")


async def backup_now(bot: Bot, note: str = "scheduled") -> None:
    if not BACKUP_CHANNEL_ID:
        log.warning("Backup skipped: BACKUP_CHANNEL_ID is not configured.")
        return
    if not os.path.exists(DB_PATH):
        log.warning("Backup skipped: no local db file yet.")
        return
    await bot.send_document(
        chat_id=BACKUP_CHANNEL_ID,
        document=FSInputFile(DB_PATH, filename="bot_backup.db"),
        caption=f"🗄 DB Backup ({note})",
    )
    log.info("Backup uploaded to backup channel (%s).", note)


async def restore_latest(bot: Bot) -> bool:
    """
    Returns True if a backup was found and restored.
    Scans the backup channel's recent history for the most recent
    document named bot_backup.db and downloads it to DB_PATH.
    """
    if os.path.exists(DB_PATH) or not BACKUP_CHANNEL_ID:
        return False  # local data already present, don't overwrite it

    try:
        # aiogram has no "list channel history" call for bots, so we keep
        # a pinned message convention: the LATEST backup is always pinned.
        chat = await bot.get_chat(BACKUP_CHANNEL_ID)
        pinned = chat.pinned_message
        if not pinned or not pinned.document:
            log.warning("No pinned backup found in backup channel — starting fresh.")
            return False

        os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
        file = await bot.get_file(pinned.document.file_id)
        await bot.download_file(file.file_path, destination=DB_PATH)
        log.info("Database restored from backup channel.")
        return True
    except Exception as e:  # noqa: BLE001 — boot-time safety net, log and continue
        log.error("Restore failed, starting with a fresh database: %s", e)
        return False


async def backup_and_pin(bot: Bot, note: str = "scheduled") -> None:
    if not BACKUP_CHANNEL_ID:
        return
    """Uploads a fresh backup and pins it, replacing the previous pin."""
    if not os.path.exists(DB_PATH):
        return
    msg = await bot.send_document(
        chat_id=BACKUP_CHANNEL_ID,
        document=FSInputFile(DB_PATH, filename="bot_backup.db"),
        caption=f"🗄 DB Backup ({note})",
    )
    try:
        await bot.pin_chat_message(chat_id=BACKUP_CHANNEL_ID, message_id=msg.message_id, disable_notification=True)
    except Exception:  # noqa: BLE001 — pin can fail on permission edge-cases, non-fatal
        log.warning("Could not pin backup message — check bot admin rights on backup channel.")
