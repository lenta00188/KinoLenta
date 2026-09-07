import asyncio
import logging
import re

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.types import Message

from config import MOVIE_CHANNEL_ID
from database import get_setting, movie_exists, set_movie_available, set_setting, upsert_movie

router = Router(name="channel")

logger = logging.getLogger(__name__)

# ===========================================================================
# 🌟 Premium filmlar rejimi (kanal orqali boshqariladi)
# ===========================================================================
# Admin kanalga oddiy matnli "Premium" postini yuboradi -> shu paytdan
# boshlab yuborilgan BARCHA kinolar (nechta bo'lishidan qat'i nazar) faqat
# "Premium filmlar" bo'limiga tushadi. Admin "Stop" postini yuborsa, rejim
# o'chadi va kinolar odatdagidek (Yangi qo'shilganlar va h.k.) indekslanadi.
# Bu matnli buyruq-postlar o'zi kino sifatida BAZAGA YOZILMAYDI.
CHANNEL_PREMIUM_MODE_KEY = "channel_premium_mode"
PREMIUM_MODE_ON_TRIGGER = "premium"
PREMIUM_MODE_OFF_TRIGGER = "stop"


def _channel_premium_mode_on() -> bool:
    return get_setting(CHANNEL_PREMIUM_MODE_KEY, "0") == "1"


async def _handle_mode_trigger(post: Message) -> bool:
    """Agar post "Premium" yoki "Stop" buyruq-matni bo'lsa, rejimni almashtiradi.

    Faqat SOF matnli postlar (video/rasm/hujjatsiz) buyruq deb hisoblanadi —
    caption'i "Premium" bo'lgan kino postini bu bilan aralashtirib bo'lmaydi,
    chunki video/hujjat postining matni `post.caption`da bo'ladi, `post.text`da
    emas.

    True qaytarsa — chaqiruvchi funksiya postni kino sifatida indekslamasdan
    to'xtashi kerak.
    """
    trigger = (post.text or "").strip().lower()
    if not trigger:
        return False

    if trigger == PREMIUM_MODE_ON_TRIGGER:
        set_setting(CHANNEL_PREMIUM_MODE_KEY, "1")
        logger.info(
            "Kanalda 🌟 PREMIUM rejim YOQILDI — keyingi kinolar "
            "«Premium filmlar» bo'limiga tushadi (msg=%s).", post.message_id,
        )
        return True

    if trigger == PREMIUM_MODE_OFF_TRIGGER:
        set_setting(CHANNEL_PREMIUM_MODE_KEY, "0")
        logger.info(
            "Kanalda 🌟 PREMIUM rejim O'CHIRILDI — kinolar odatdagidek "
            "indekslanadi (msg=%s).", post.message_id,
        )
        return True

    return False

# Janr so'zlari (caption va hashtaglarda qidiriladi)
KNOWN_GENRES = [
    "drama", "komediya", "jangari", "fantastika", "triller", "sarguzasht",
    "detektiv", "melodrama", "dahshat", "qo'rqinchli", "oilaviy", "tarixiy",
    "kriminal", "multfilm", "animatsiya", "musiqa", "musiqiy", "romantika",
    "sport", "dokumental", "biografik", "fantazi", "mif", "superqahramon",
]

YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def parse_caption(caption: str) -> dict:
    """Kino posti caption'idan title, year va genres ni ajratadi.

    Kutilayotgan format:
      <b>Kino nomi</b> (2024)
      Qo'shimcha tavsif...
      #Drama #Komediya
    """
    title = ""
    year = None
    genres = set()

    if not caption:
        return {"title": "", "year": None, "genres": ""}

    lines = [ln.strip() for ln in caption.splitlines() if ln.strip()]

    # Title: birinchi ma'noli qatordan HTML teglar olib tashlanadi
    if lines:
        raw_title = re.sub(r"<[^>]+>", "", lines[0])
        raw_title = raw_title.strip().lstrip("#").strip()
        # Yilni qavslardan va title'dan ajratib chiqaramiz
        year_match = YEAR_RE.search(raw_title)
        if year_match:
            year = int(year_match.group(0))
        # Qavslarni va yilni title'dan olib tashlash
        clean_title = re.sub(r"\s*[\(\[]?\d{4}[\)\]]?\s*", " ", raw_title).strip()
        clean_title = re.sub(r"\s{2,}", " ", clean_title).strip()
        if clean_title:
            title = clean_title

    # Year: agar title'dan topilmagan bo'lsa, butun caption'dan qidiramiz
    if year is None:
        m = YEAR_RE.search(caption)
        if m:
            year = int(m.group(0))

    # Genres: hashtag'lar va ma'lum janr so'zlari.
    # XATO TUZATILDI: avval oddiy `genre in lower` ishlatilardi, natijada
    # "melodrama" ichidan "drama" ham topilib, noto'g'ri janr qo'shilardi.
    lower = caption.lower()
    for tag in re.findall(r"#(\w+)", caption):
        if tag.lower() in KNOWN_GENRES:
            genres.add(tag.lower())
    for genre in KNOWN_GENRES:
        if re.search(rf"(?<!\w){re.escape(genre)}(?!\w)", lower):
            genres.add(genre)

    return {
        "title": title,
        "year": year,
        "genres": ", ".join(sorted(genres)),
    }


def full_caption(post: Message) -> str:
    """Postning to'liq matnini HTML formatlash bilan qaytaradi.

    Foydalanuvchiga kino kartasida aynan shu matn ko'rsatiladi, shuning uchun
    qalin/kursiv/havolalar saqlanib qolishi muhim.
    """
    try:
        html = post.html_text
        if html:
            return html
    except Exception:
        pass
    return post.caption or post.text or ""


@router.channel_post(F.chat.id == MOVIE_CHANNEL_ID)
async def on_new_post(post: Message):
    """Kanalga yangi post tushganda kino sifatida indekslash."""
    if await _handle_mode_trigger(post):
        return  # "Premium" / "Stop" buyruq-posti — kino sifatida yozilmaydi

    caption = full_caption(post)
    meta = parse_caption(caption)
    if not meta["title"]:
        # Caption yo'q — kino baribir raqam orqali topilsin deb indekslaymiz.
        meta["title"] = f"Kino #{post.message_id}"
        logger.warning("Kanal postida nom yo'q, raqam bilan indekslandi: msg %s",
                       post.message_id)
    premium_only = 1 if _channel_premium_mode_on() else 0
    upsert_movie(post.message_id, meta["title"], meta["year"], meta["genres"], caption,
                 premium_only=premium_only)
    logger.info(
        "Yangi kino indekslandi: msg=%s title=%r year=%s genres=%s premium=%s",
        post.message_id, meta["title"], meta["year"], meta["genres"], premium_only,
    )


@router.edited_channel_post(F.chat.id == MOVIE_CHANNEL_ID)
async def on_edit_post(post: Message):
    """Kanal posti tahrirlanganda metadata va matn yangilanadi."""
    if await _handle_mode_trigger(post):
        return

    caption = full_caption(post)
    meta = parse_caption(caption)
    if not meta["title"]:
        meta["title"] = f"Kino #{post.message_id}"
    # premium_only bu yerda BERILMAYDI — tahrirlash paytida kanal rejimi
    # boshlang'ich yuborilgan paytdagidan farq qilishi mumkin, shuning uchun
    # kinoning mavjud premium holati o'zgarishsiz qoladi.
    upsert_movie(post.message_id, meta["title"], meta["year"], meta["genres"], caption)
    logger.info(
        "Kino yangilandi: msg=%s title=%r", post.message_id, meta["title"],
    )


async def backfill_channel(
    bot: Bot,
    target_chat_id: int,
    start_id: int = 1,
    max_id: int = 200_000,
    stop_after_missing: int = 150,
    on_progress=None,
) -> dict:
    """Kanalning barcha mavjud postlarini bazaga indekslaydi (backfill).

    NIMA UCHUN KERAK: Bot API'da kanal postlari tarixini o'qish imkoni yo'q
    (get_chat_history mavjud emas) — bot faqat YANGI postlarni ko'radi. Shuning
    uchun kanal yaratilishidan oldin mavjud bo'lgan 200 ta kino bazada yo'q.

    QANDAY ISHLAYDI: har bir message_id (1, 2, 3, ...) ni bot admin'ning chatiga
    forward qilib tekshiramiz:
      - forward muvaffaqiyatli  -> post mavjud; caption'ini tahlil qilib
        bazaga yozamiz, so'ng vaqtinchalik forward nusxasini o'chiramiz.
      - "message to forward not
        found" xatosi            -> bu ID da post yo'q (o'chirilgan yoki umuman
        mavjud emas), davom etamiz.

    Ketma-ket stop_after_missing ta post topilmasa, skanerlash to'xtaydi — bu
    kanalning haqiqiy oxiri hisoblanadi (oraliqda bo'sh ID lar bo'lishi mumkin).

    Natija: {"indexed": ..., "skipped": ..., "scanned": ...}
    """
    indexed = 0
    skipped = 0
    scanned = 0
    missing_streak = 0
    msg_id = start_id  # loop bo'sh bo'lsa ham on_progress uchun aniqlangan bo'lsin

    for msg_id in range(start_id, max_id + 1):
        # Telegram flood-limitini e'tiborga olish: haddan tashqari tez bo'lmasin
        if scanned and scanned % 20 == 0:
            await asyncio.sleep(0.05)

        try:
            forwarded = await bot.forward_message(
                chat_id=target_chat_id,
                from_chat_id=MOVIE_CHANNEL_ID,
                message_id=msg_id,
            )
        except TelegramRetryAfter as e:
            logger.warning("Flood limit — %s soniya kutamiz...", e.retry_after)
            await asyncio.sleep(e.retry_after)
            continue
        except TelegramBadRequest as e:
            if "not found" in str(e).lower() or "message_id" in str(e).lower():
                missing_streak += 1
                if missing_streak >= stop_after_missing:
                    logger.info(
                        "%s ta ketma-ket post topilmadi — kanal oxiriga yetdik (msg=%s)",
                        stop_after_missing, msg_id,
                    )
                    break
                continue
            # Boshqa xato — log'lab o'tamiz, lekin skanerlashni buzmaymiz
            logger.warning("Forward xatosi msg=%s: %s", msg_id, e)
            continue

        # Post mavjud — vaqtinchalik forward nusxasini darhol o'chiramiz
        scanned += 1
        missing_streak = 0
        try:
            await bot.delete_message(target_chat_id, forwarded.message_id)
        except Exception:
            pass  # o'chirib bo'lmasa ham muammo emas

        caption = full_caption(forwarded)
        meta = parse_caption(caption)
        if not meta["title"]:
            # Nom topilmadi — raqam bilan indekslaymiz
            meta["title"] = f"Kino #{msg_id}"
            skipped += 1

        upsert_movie(msg_id, meta["title"], meta["year"], meta["genres"], caption)
        indexed += 1
        logger.info("Indekslandi: msg=%s title=%r", msg_id, meta["title"])

        if on_progress and indexed % 20 == 0:
            await on_progress(indexed, scanned, msg_id)

    if on_progress:
        await on_progress(indexed, scanned, msg_id, done=True)
    return {"indexed": indexed, "skipped": skipped, "scanned": scanned}


async def delete_movie_from_channel(bot: Bot, message_id: int) -> None:
    """Kanal posti o'chirilsa bazadan belgilash (mavjudligini tekshirish bilan)."""
    if movie_exists(message_id):
        set_movie_available(message_id, 0)
        logger.info("Kino unavailable deb belgilandi: msg=%s", message_id)


async def validate_channel_access(bot: Bot) -> bool:
    """Ishga tushishda botning kino kanalida admin ekanini tekshiradi."""
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(MOVIE_CHANNEL_ID, me.id)
    except Exception as e:
        logger.error("Kanal tekshiruvi muvaffaqiyatsiz: %s", e)
        return False
    if member.status in ("administrator", "creator"):
        return True
    logger.error(
        "Bot kino kanalida (%s) ADMIN emas! Botni kanalga admin qilib qo'shing.",
        MOVIE_CHANNEL_ID,
    )
    return False
