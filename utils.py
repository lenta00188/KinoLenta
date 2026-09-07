import logging
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot

from config import DEFAULT_TZ, OWNER_IDS

logger = logging.getLogger(__name__)

# ===========================================================================
# Vaqt / vaqt mintaqasi
# ===========================================================================


def get_tz() -> ZoneInfo:
    try:
        return ZoneInfo(DEFAULT_TZ)
    except Exception:
        return ZoneInfo("UTC")


def local_now() -> datetime:
    return datetime.now(get_tz())


def to_local_ts(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, get_tz())


def format_ts(ts) -> str:
    """Unix timestamp (int), datetime yoki matn sanasini o'qiladigan ko'rinishga o'tkazadi.

    PostgreSQL (Neon) TIMESTAMPTZ ustunlari psycopg orqali datetime obyekti
    bo'lib qaytadi — shu holat ham qo'llab-quvvatlanadi.
    """
    if ts is None:
        return "-"
    if isinstance(ts, (int, float)):
        return to_local_ts(int(ts)).strftime("%d.%m.%Y %H:%M")
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=ZoneInfo("UTC"))
        return ts.astimezone(get_tz()).strftime("%d.%m.%Y %H:%M")
    text = str(ts).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text, fmt).replace(tzinfo=ZoneInfo("UTC"))
            return dt.astimezone(get_tz()).strftime("%d.%m.%Y %H:%M")
        except ValueError:
            continue
    return text


WEEKDAYS_UZ = [
    "Dushanba", "Seshanba", "Chorshanba", "Payshanba",
    "Juma", "Shanba", "Yakshanba",
]


def format_ts_human(ts: int) -> str:
    """'Seshanba, 18:00 (12.08.2026)' ko'rinishidagi eslatma vaqti."""
    try:
        dt = to_local_ts(int(ts))
    except (TypeError, ValueError, OSError):
        return format_ts(ts)
    return f"{WEEKDAYS_UZ[dt.weekday()]}, {dt.strftime('%H:%M')} ({dt.strftime('%d.%m.%Y')})"


def parse_reminder_input(text: str) -> int | None:
    """Foydalanuvchi kiritgan vaqtni unix timestamp'ga aylantiradi.

    Qo'llab-quvvatlanadigan formatlar:
      HH:MM                          -> bugun, o'tib ketgan bo'lsa ertaga
      DD.MM HH:MM                    -> shu yil
      DD.MM.YYYY HH:MM
      YYYY-MM-DD HH:MM
    Noto'g'ri format yoki o'tgan vaqt -> None
    """
    text = (text or "").strip()
    tz = get_tz()
    now = local_now()

    patterns = [
        (r"^(\d{1,2}):(\d{2})$", "HM"),
        (r"^(\d{1,2})\.(\d{1,2})[ .](\d{1,2}):(\d{2})$", "DMHM"),
        (r"^(\d{1,2})\.(\d{1,2})\.(\d{4})[ .](\d{1,2}):(\d{2})$", "DDMMYYYYHM"),
        (r"^(\d{4})-(\d{1,2})-(\d{1,2})[ .](\d{1,2}):(\d{2})$", "YYYYMMDDHM"),
    ]

    for pattern, kind in patterns:
        m = re.match(pattern, text)
        if not m:
            continue
        try:
            if kind == "HM":
                h, mi = int(m.group(1)), int(m.group(2))
                if not (0 <= h <= 23 and 0 <= mi <= 59):
                    return None
                dt = now.replace(hour=h, minute=mi, second=0, microsecond=0)
                if dt <= now:
                    dt += timedelta(days=1)
            elif kind == "DMHM":
                d, mo, h, mi = (int(m.group(i)) for i in range(1, 5))
                dt = datetime(now.year, mo, d, h, mi, tzinfo=tz)
            elif kind == "DDMMYYYYHM":
                d, mo, y, h, mi = (int(m.group(i)) for i in range(1, 6))
                dt = datetime(y, mo, d, h, mi, tzinfo=tz)
            else:  # YYYYMMDDHM
                y, mo, d, h, mi = (int(m.group(i)) for i in range(1, 6))
                dt = datetime(y, mo, d, h, mi, tzinfo=tz)

            if dt <= now:
                return None
            return int(dt.timestamp())
        except (ValueError, OverflowError):
            return None
    return None


def reminder_quick_choice(choice: str, movie_id: int) -> int | None:
    """Eslatma tezkor tanlovlari uchun unix timestamp qaytaradi."""
    now = local_now()
    if choice == "today18":
        dt = now.replace(hour=18, minute=0, second=0, microsecond=0)
        if dt <= now:
            dt += timedelta(days=1)
    elif choice == "today21":
        dt = now.replace(hour=21, minute=0, second=0, microsecond=0)
        if dt <= now:
            dt += timedelta(days=1)
    elif choice == "tomorrow":
        dt = now.replace(hour=18, minute=0, second=0, microsecond=0) + timedelta(days=1)
    else:
        return None
    return int(dt.timestamp())


# ===========================================================================
# Adminlarga xabar yuborish
# ===========================================================================

def all_admin_ids() -> list:
    """.env dagi egalar + bazadagi qo'shimcha adminlar (takrorlarsiz)."""
    try:
        from database import db_admin_ids

        extra = db_admin_ids()
    except Exception:
        extra = []
    seen, out = set(), []
    for uid in list(OWNER_IDS) + list(extra):
        if uid not in seen:
            seen.add(uid)
            out.append(uid)
    return out


def is_admin_user(user_id: int) -> bool:
    return user_id in all_admin_ids()


def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS


async def notify_admins(bot: Bot, text: str, keyboard=None) -> None:
    """Barcha adminlarga xabar yuboradi. Xatolarni e'tiborsiz qoldiradi."""
    for admin_id in all_admin_ids():
        try:
            await bot.send_message(chat_id=admin_id, text=text, reply_markup=keyboard)
        except Exception as e:
            logger.warning("Admin xabari yuborilmadi (%s): %s", admin_id, e)


async def notify_admins_photo(bot: Bot, file_id: str, caption: str, keyboard=None) -> None:
    """Adminlarga rasm (masalan, to'lov cheki) yuboradi."""
    for admin_id in all_admin_ids():
        try:
            await bot.send_photo(
                chat_id=admin_id, photo=file_id, caption=caption, reply_markup=keyboard
            )
        except Exception as e:
            logger.warning("Admin rasmi yuborilmadi (%s): %s", admin_id, e)


# ===========================================================================
# Xabar jo'natish yordamchisi (Message yoki CallbackQuery uchun)
# ===========================================================================

async def emit(target, text: str, reply_markup=None):
    """Message yoki CallbackQuery'ga qarab yangi xabar yuboradi yoki tahrirlaydi.

    Muhim: `edit_text` FAQAT InlineKeyboardMarkup bilan ishlaydi. Agar reply
    (pastki) klaviatura berilgan bo'lsa, tahrirlash o'rniga yangi xabar yuboriladi.
    Shuningdek "message is not modified" xatosi yutiladi.
    """
    from aiogram.exceptions import TelegramBadRequest
    from aiogram.types import (
        CallbackQuery,
        InlineKeyboardMarkup,
        Message,
        ReplyKeyboardMarkup,
    )

    if isinstance(target, CallbackQuery):
        can_edit = reply_markup is None or isinstance(reply_markup, InlineKeyboardMarkup)
        if can_edit:
            try:
                return await target.message.edit_text(text, reply_markup=reply_markup)
            except TelegramBadRequest as e:
                if "message is not modified" in str(e).lower():
                    return None
                # Tahrirlab bo'lmadi (masalan, media xabar) — yangisini yuboramiz
        return await target.message.answer(text, reply_markup=reply_markup)

    if isinstance(target, Message):
        return await target.answer(text, reply_markup=reply_markup)

    raise TypeError(f"Noto'g'ri target turi: {type(target)}")


async def safe_edit_markup(callback, reply_markup):
    """Inline klaviaturani xavfsiz yangilaydi ("not modified" xatosisiz)."""
    from aiogram.exceptions import TelegramBadRequest

    try:
        await callback.message.edit_reply_markup(reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            logger.debug("edit_reply_markup: %s", e)


# ===========================================================================
# Kino kartasi matni
# ===========================================================================

def row_get(row, key, default=None):
    """DB qatoridan xavfsiz o'qish (ustun mavjud bo'lmasa ham qulamaydi).

    psycopg dict_row / sqlite3.Row ikkalasi ham ishlaydi.
    """
    try:
        value = row[key]
    except (IndexError, KeyError):
        return default
    return default if value is None else value


CAPTION_LIMIT = 3200


def movie_card_text(movie) -> str:
    """Kino kartasi = kanal postidagi TO'LIQ matn + qisqa meta.

    Foydalanuvchi raqam yozganda avval shu matn ko'rsatiladi, keyin
    «🍿 FILMNI TOMOSHA QILISH» tugmasi orqali videoning o'zi yuboriladi.
    """
    caption = str(row_get(movie, "caption", "") or "").strip()
    title = (movie["title"] or "Nomsiz").strip() or "Nomsiz"

    if caption:
        body = caption[:CAPTION_LIMIT]
        if len(caption) > CAPTION_LIMIT:
            body += "…"
    else:
        # Kanal postida matn bo'lmasa — mavjud meta'dan karta yig'amiz
        parts = [f"🍿 <b>{title}</b>"]
        meta = []
        if movie["year"]:
            meta.append(f"📅 {movie['year']}")
        if movie["genres"]:
            meta.append(f"🧩 {movie['genres']}")
        if meta:
            parts.append("  ".join(meta))
        body = "\n".join(parts)

    footer = (
        f"\n\n➖➖➖➖➖➖➖➖➖\n"
        f"👁 Ko'rishlar: {movie['views']}   🔢 Raqam: <code>{movie['movie_id']}</code>"
    )
    return body + footer


def movie_row_text(movie) -> str:
    """Ro'yxatlar uchun bitta qatorda kino nomi + yil."""
    title = (movie["title"] or "Nomsiz").strip()
    if movie["year"]:
        return f"{title} — {movie['year']}"
    return title


def pagination_pages(total: int, limit: int) -> int:
    if total <= 0:
        return 1
    return max(1, (total + limit - 1) // limit)


# ===========================================================================
# Navigatsiya konteksti (orqaga qaytish)
# ===========================================================================

async def save_nav(state, ctx: dict) -> None:
    """Oxirgi ochilgan ro'yxat kontekstini saqlaydi (orqaga qaytish uchun)."""
    await state.update_data(nav=ctx)


async def load_nav(state) -> dict | None:
    data = await state.get_data()
    return data.get("nav")


async def clear_nav(state) -> None:
    await state.update_data(nav=None)


# ===========================================================================
# 🌟 Premium — yagona imtiyoz: majburiy obunadan ozod bo'lish.
# Barcha bo'lim va limitlar hammaga bir xil ochiq, shuning uchun alohida
# funksiya-darajasidagi qulflash endi kerak emas.
# ===========================================================================
