"""
Single entry point. `git clone` -> fill .env -> `python main.py` and
everything (db restore/creation, scheduled backups, handlers) wires itself
up automatically. No manual setup steps beyond .env.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent

import config
from database.models import init_db
from database.backup_restore import restore_latest, backup_and_pin
from database.queries import cleanup_shared_links, cleanup_user_activity
from handlers import root_router
from middlewares import AccessMiddleware
from utils.bot import BrandedBot
from web_portal import start_web_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("main")


async def on_error(event: ErrorEvent) -> bool:
    """
    Catches any exception raised inside a handler so one bad update never
    takes the whole bot down — it just gets logged, and the user's update
    is skipped instead of crashing the polling loop.
    """
    log.error("Unhandled error while processing update: %s", event.exception, exc_info=event.exception)
    return True


async def periodic_backup(bot: Bot) -> None:
    if not config.BACKUP_CHANNEL_ID:
        log.info("Automatic backups disabled until BACKUP_CHANNEL_ID is configured.")
        return
    interval = max(5, config.BACKUP_INTERVAL_MINUTES) * 60
    while True:
        await asyncio.sleep(interval)
        try:
            await backup_and_pin(bot, note="auto")
        except Exception as e:  # noqa: BLE001 — never let a backup failure kill the bot
            log.error("Auto-backup failed: %s", e)


async def periodic_maintenance(bot: Bot) -> None:
    from handlers.force_join import revalidate_all_referrals

    while True:
        await asyncio.sleep(15 * 60)
        try:
            removed = await cleanup_shared_links()
            activity_removed = await cleanup_user_activity()
            checked = await revalidate_all_referrals(bot)
            if removed or activity_removed or checked:
                log.info(
                    "Maintenance complete: links_removed=%s activity_removed=%s referrals_checked=%s",
                    removed,
                    activity_removed,
                    checked,
                )
        except Exception as e:  # noqa: BLE001 — maintenance must never stop polling
            log.error("Maintenance failed: %s", e)


async def main() -> None:
    config.validate()

    # Migrate the local database before creating the Telegram HTTP session.
    # If a restored database is used below, the second init_db call migrates
    # that restored file as well.
    await init_db()
    log.info("Database ready at %s", config.DB_PATH)

    bot = BrandedBot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.outer_middleware(AccessMiddleware())
    dp.callback_query.outer_middleware(AccessMiddleware())
    dp.include_router(root_router)
    dp.errors.register(on_error)

    await bot.set_my_commands([
        BotCommand(command="start", description="বট শুরু করুন / মেনু দেখুন"),
        BotCommand(command="help", description="বট ব্যবহারের নিয়ম"),
        BotCommand(command="cancel", description="চলমান কাজ বাতিল করুন"),
        BotCommand(command="admin", description="অ্যাডমিন প্যানেল (শুধু অ্যাডমিনদের জন্য)"),
        BotCommand(command="skip", description="Preview না দিয়ে পরের ধাপে যান"),
        BotCommand(command="search", description="Product search করুন"),
        BotCommand(command="checkin", description="আজকের Daily Bonus নিন"),
        BotCommand(command="support", description="Support ticket খুলুন"),
        BotCommand(command="linkgen", description="Secure share link বানান"),
        BotCommand(command="mylinks", description="আপনার generated links"),
        BotCommand(command="id", description="আপনার Telegram ID"),
        BotCommand(command="ping", description="Bot status check"),
        BotCommand(command="emojiid", description="Custom emoji ID বের করুন"),
        BotCommand(command="language", description="ভাষা পরিবর্তন করুন"),
        BotCommand(command="user", description="Admin: user profile"),
        BotCommand(command="mute", description="Admin: mute/unmute user"),
        BotCommand(command="premium", description="Admin: premium status"),
        BotCommand(command="refund", description="Admin: coin order refund"),
    ])

    log.info("Checking for an existing backup to restore...")
    restored = await restore_latest(bot)
    log.info("Restored from backup channel." if restored else "Starting with local/fresh database.")

    await init_db()
    log.info("Database migration rechecked after restore.")

    await start_web_server(bot)
    log.info("Mini web portal listening on port %s", config.WEB_PORT)
    asyncio.create_task(periodic_backup(bot))
    asyncio.create_task(periodic_maintenance(bot))

    log.info("Bot starting (long polling)...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot stopped.")
