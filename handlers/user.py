from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import get_movie, increment_requests, save_user, touch_user
from keyboards import (
    BTN_CONTACT,
    BTN_FAVORITES,
    BTN_GENRES,
    BTN_HISTORY,
    BTN_NEW,
    BTN_PREMIUM_MOVIES,
    BTN_PREMIUM,
    BTN_PROFILE,
    BTN_RANDOM,
    BTN_REMINDERS,
    BTN_WATCHLIST,
    contact_admin_keyboard,
    movie_card_keyboard,
)
from utils import emit, movie_card_text, save_nav

router = Router(name="user")

# Asosiy menyu tugmalari — ular maxsus handlerlarda ishlanadi.
_MENU_BUTTONS = {
    BTN_PREMIUM, BTN_NEW, BTN_PREMIUM_MOVIES, BTN_GENRES, BTN_RANDOM, BTN_WATCHLIST,
    BTN_FAVORITES, BTN_HISTORY, BTN_REMINDERS, BTN_PROFILE, BTN_CONTACT,
}

HINT = (
    "🔢 <b>Kino raqamini yuboring</b>\n\n"
    "Har bir kinoning o'z raqami bor. Masalan: <code>26</code>\n\n"
    "Raqamni kanaldagi post ostidan yoki quyidagi bo'limlardan topishingiz mumkin:\n"
    "✨ Yangi qo'shilganlar • 🌟 Premium filmlar • 🧩 Janrlar"
)


# ===========================================================================
# 🔢 Raqam orqali kino
# ===========================================================================
# Nom bo'yicha qidiruv butunlay olib tashlandi — bot faqat raqam bilan ishlaydi.

async def show_movie_by_number(target, raw: str) -> bool:
    """Raqamga mos kinoning TO'LIQ matnini ko'rsatadi (video hali yuborilmaydi)."""
    text = raw.strip().lstrip("#").strip()
    if not text.isdigit():
        return False
    movie_id = int(text)
    movie = get_movie(movie_id)
    if not movie or not movie["available"]:
        return False

    increment_requests(movie_id)
    await emit(
        target,
        movie_card_text(movie),
        reply_markup=movie_card_keyboard(movie_id, target.from_user.id),
    )
    return True


@router.message(F.text)
async def handle_text(message: Message, state: FSMContext):
    """Har qanday matn: raqam bo'lsa — kino, aks holda — yo'riqnoma."""
    text = (message.text or "").strip()
    if not text or text in _MENU_BUTTONS or text.startswith("/"):
        return

    save_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    touch_user(message.from_user.id)

    if await show_movie_by_number(message, text):
        await save_nav(state, {"list": "home"})
        return

    if text.lstrip("#").strip().isdigit():
        await message.answer(
            f"❌ <b>{text} raqamli kino topilmadi</b>\n\n"
            "Raqamni tekshirib qayta yuboring yoki adminga murojat qiling.",
            reply_markup=contact_admin_keyboard(),
        )
        return

    await message.answer(HINT, reply_markup=contact_admin_keyboard())


@router.message()
async def handle_other(message: Message):
    """Matn bo'lmagan xabarlar (stiker, rasm va h.k.)."""
    await message.answer(HINT)


@router.callback_query()
async def fallback_callback(callback: CallbackQuery):
    """Hech bir handlerga tushmagan callback'lar (eskirgan tugmalar, ruxsatsiz
    admin tugmalari). Javob berilmasa, Telegram'da tugma cheksiz "aylanadi"."""
    from utils import is_admin_user

    data = callback.data or ""
    admin_prefixes = ("apay:", "aadm:", "aprem:", "abc:", "admcatalog:", "asup:",
                      "asub:", "afeat:", "alim:")
    if data.startswith(admin_prefixes) and not is_admin_user(callback.from_user.id):
        await callback.answer("⛔ Bu amal uchun ruxsatingiz yo'q.", show_alert=True)
        return
    await callback.answer("⏳ Bu tugma eskirgan. /start bilan yangilang.", show_alert=True)
