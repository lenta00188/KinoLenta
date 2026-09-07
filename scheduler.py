import asyncio
import logging
import time

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import get_due_reminders, mark_reminder_done
from keyboards import CB_HOME, CB_MOVIE, CB_WATCH
from utils import format_ts_human

logger = logging.getLogger(__name__)


async def send_due_reminders(bot: Bot) -> None:
    """Vaqti yetgan barcha faol eslatmalarni yuboradi va 'done' qilib belgilaydi."""
    now = int(time.time())
    due = get_due_reminders(now)
    if not due:
        return

    for rem in due:
        # YANGILANDI: eslatmada endi kino nomi ham bor
        # ("Seshanba, 18:00 — kino nomi").
        title = rem["title"] or f"#{rem['movie_id']}"
        year = f" ({rem['year']})" if rem["year"] else ""
        text = (
            "🔔 <b>Kino eslatmasi</b>\n\n"
            f"🍿 <b>{title}</b>{year}\n"
            f"📜 {format_ts_human(rem['reminder_time'])}\n\n"
            "Vaqti keldi — yoqimli tomosha!"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="▶️ TOMOSHA QILISH",
                                      callback_data=f"{CB_WATCH}{rem['movie_id']}")],
                [
                    InlineKeyboardButton(text="🍿 Kino haqida",
                                         callback_data=f"{CB_MOVIE}{rem['movie_id']}"),
                    InlineKeyboardButton(text="🧭 Bosh menyu", callback_data=CB_HOME),
                ],
            ]
        )
        try:
            await bot.send_message(chat_id=rem["user_id"], text=text, reply_markup=kb)
            mark_reminder_done(rem["id"])
        except TelegramForbiddenError:
            # Foydalanuvchi botni bloklagan — qayta urinishning foydasi yo'q.
            mark_reminder_done(rem["id"])
        except TelegramRetryAfter as e:
            logger.warning("Flood limit — %s soniya kutamiz", e.retry_after)
            await asyncio.sleep(e.retry_after)
        except Exception as e:
            logger.warning("Eslatma yuborilmadi (id=%s): %s", rem["id"], e)
            # Vaqtinchalik xato bo'lishi mumkin — keyingi siklda qayta uriniladi.
        await asyncio.sleep(0.05)


async def run_reminder_scheduler(bot: Bot, interval: int = 30) -> None:
    """Eslatmalarni tekshiradigan asosiy fon vazifasi (har `interval` soniya)."""
    logger.info("Eslatma scheduler ishga tushdi (interval=%ss)", interval)
    while True:
        try:
            await send_due_reminders(bot)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Schedulerda kutilmagan xato: %s", e)
        await asyncio.sleep(interval)
