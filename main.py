import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat, ErrorEvent

from config import BOT_TOKEN, MOVIE_CHANNEL_ID
from database import init_db
from handlers import (
    admin,
    browse,
    channel,
    movie,
    premium,
    reminders,
    start,
    support,
    user,
)
from middlewares import SubscriptionMiddleware
from scheduler import run_reminder_scheduler
from utils import all_admin_ids

logger = logging.getLogger(__name__)

USER_COMMANDS = [
    BotCommand(command="start", description="🧭 Botni ishga tushirish"),
    BotCommand(command="help", description="❓ Yordam"),
    BotCommand(command="cancel", description="🚫 Amalni bekor qilish"),
]

ADMIN_COMMANDS = USER_COMMANDS + [
    BotCommand(command="admin", description="🧰 Admin panel"),
    BotCommand(command="backfill", description="🔄 Kanaldagi eski kinolarni yuklash"),
]


async def set_bot_commands(bot: Bot) -> None:
    """'/' bosilganda chiqadigan buyruqlar ro'yxati."""
    await bot.set_my_commands(USER_COMMANDS)
    # Adminlar ro'yxati endi dinamik (.env + bazadagi adminlar)
    for admin_id in all_admin_ids():
        try:
            await bot.set_my_commands(
                ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=admin_id)
            )
        except TelegramBadRequest:
            # Admin hali botga /start bermagan bo'lishi mumkin — muammo emas.
            pass


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    # Router tartibi MUHIM:
    #  1) channel  — kanal postlari
    #  2) admin    — dinamik IsAdmin filtri (message + callback)
    #  3) start    — /start, /help, /cancel (oddiy foydalanuvchilar uchun ham)
    #  4) browse / movie / reminders / premium / support
    #  5) user     — oxirgi: raqam -> kino
    for r in (
        channel.router, admin.router, start.router, browse.router,
        movie.router, reminders.router, premium.router, support.router, user.router,
    ):
        dp.include_router(r)

    # 📡 Majburiy obuna — outer middleware, hech bir handler chetlab o'tolmaydi
    dp.message.outer_middleware(SubscriptionMiddleware())
    dp.callback_query.outer_middleware(SubscriptionMiddleware())

    @dp.error()
    async def on_error(event: ErrorEvent) -> bool:
        """Kutilmagan xatolar bot ishini to'xtatmasin — log qilamiz va davom etamiz."""
        logger.exception("Handler xatosi: %s", event.exception)
        try:
            update = event.update
            if update.callback_query:
                await update.callback_query.answer(
                    "⚠️ Xatolik yuz berdi. Qayta urinib ko'ring.", show_alert=True
                )
            elif update.message:
                await update.message.answer(
                    "⚠️ Xatolik yuz berdi. /start bilan qayta boshlang."
                )
        except Exception:
            pass
        return True

    return dp


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher()

    # Kanal huquqlari tekshiruvi — bot kino kanalida admin bo'lishi shart
    if not await channel.validate_channel_access(bot):
        logger.error(
            "Bot kino kanalida (%s) admin emas yoki kanalga kirish imkoni yo'q. "
            "Botni kanalga admin qilib qo'shing va qayta ishga tushiring.",
            MOVIE_CHANNEL_ID,
        )
        await bot.session.close()
        raise SystemExit(1)

    await set_bot_commands(bot)

    scheduler_task = asyncio.create_task(run_reminder_scheduler(bot))

    logger.info("Bot ishga tushdi! Adminlar: %s", all_admin_ids())
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler_task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
