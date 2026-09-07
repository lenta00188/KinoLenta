import logging

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from config import MOVIE_CHANNEL_ID
from database import (
    add_favorite,
    add_watchlist,
    get_movie,
    increment_requests,
    increment_views,
    is_favorite,
    is_in_watchlist,
    is_watched,
    mark_watched,
    remove_favorite,
    register_today_view,
    remove_watchlist,
    set_movie_available,
    unmark_watched,
)
from handlers.browse import restore_nav
from keyboards import (
    CB_AW_FAV,
    CB_AW_SAVE,
    CB_AW_WATCHED,
    CB_BACK,
    CB_FAV,
    CB_MOVIE,
    CB_SAVE,
    CB_WATCH,
    CB_WATCHED,
    admin_menu_keyboard,
    after_watch_keyboard,
    main_menu_keyboard,
    movie_card_keyboard,
)
from utils import (
    emit,
    is_admin_user,
    load_nav,
    movie_card_text,
    notify_admins,
    safe_edit_markup,
)

router = Router(name="movie")
logger = logging.getLogger(__name__)


def _movie_id(callback: CallbackQuery) -> int:
    """Callback data'dan kino ID sini xavfsiz ajratadi."""
    return int(callback.data.rsplit(":", 1)[1])


# ===========================================================================
# Kino kartasi
# ===========================================================================

@router.callback_query(F.data.startswith(CB_MOVIE))
async def cb_movie(callback: CallbackQuery):
    movie_id = _movie_id(callback)
    movie = get_movie(movie_id)
    if not movie or not movie["available"]:
        await callback.answer("❌ Bu kino hozircha mavjud emas.", show_alert=True)
        return
    increment_requests(movie_id)
    await emit(
        callback,
        movie_card_text(movie),
        reply_markup=movie_card_keyboard(movie_id, callback.from_user.id),
    )
    await callback.answer()


# ===========================================================================
# ▶️ Tomosha qilish (copy_message orqali yetkazish)
# ===========================================================================

@router.callback_query(F.data.startswith(CB_WATCH))
async def cb_watch(callback: CallbackQuery):
    movie_id = _movie_id(callback)
    movie = get_movie(movie_id)
    if not movie or not movie["available"]:
        await callback.answer("❌ Bu kino hozircha mavjud emas.", show_alert=True)
        return

    user_id = callback.from_user.id

    try:
        await callback.bot.copy_message(
            chat_id=user_id,
            from_chat_id=MOVIE_CHANNEL_ID,
            message_id=movie_id,
        )
    except TelegramBadRequest as e:
        msg = str(e).lower()
        if "not found" in msg or "message id" in msg or "message_id" in msg:
            set_movie_available(movie_id, 0)
            await callback.answer(
                "❌ Bu kino kanaldan o'chirilgan va endi mavjud emas.", show_alert=True
            )
            await notify_admins(
                callback.bot,
                f"⚠️ <b>Kino topilmadi</b>\n\n🍿 {movie['title']}\n"
                f"🔢 <code>{movie_id}</code>\n\nKanalda post yo'q — bazada "
                "«mavjud emas» deb belgilandi.",
            )
        else:
            logger.warning("copy_message xatosi (movie=%s): %s", movie_id, e)
            await callback.answer(
                "⚠️ Kinoni yuborishda xatolik. Iltimos, keyinroq urinib ko'ring.",
                show_alert=True,
            )
        return
    except TelegramForbiddenError:
        await callback.answer(
            "⚠️ Botning kanalga kirish huquqi yo'q. Admin xabardor qilindi.",
            show_alert=True,
        )
        await notify_admins(
            callback.bot,
            "🚨 <b>Bot kanalga kira olmayapti!</b>\n\n"
            "Botni kino kanalida admin qilib qo'ying.",
        )
        return

    increment_views(movie_id)
    register_today_view(user_id, movie_id)
    mark_watched(user_id, movie_id)  # avtomatik ko'rish tarixiga qo'shish

    await callback.answer()

    footer = f"🍿 <b>{movie['title']}</b> — yoqimli tomosha!"
    await callback.message.answer(
        footer + "\n\nYana nima qilishni xohlaysiz?",
        reply_markup=after_watch_keyboard(movie_id, user_id),
    )


# ===========================================================================
# 📌 Saqlash / 🧡 Sevimlilar / ✅ Ko'rdim
# ===========================================================================

async def _toggle_watchlist(callback: CallbackQuery) -> str | None:
    """Watchlist holatini almashtiradi."""
    movie_id = _movie_id(callback)
    user_id = callback.from_user.id
    if is_in_watchlist(user_id, movie_id):
        remove_watchlist(user_id, movie_id)
        return "📌 Ro'yxatdan olib tashlandi."
    add_watchlist(user_id, movie_id)
    return "📌 Ro'yxatga saqlandi!"


async def _toggle_favorite(callback: CallbackQuery) -> str | None:
    movie_id = _movie_id(callback)
    user_id = callback.from_user.id
    if is_favorite(user_id, movie_id):
        remove_favorite(user_id, movie_id)
        return "🧡 Sevimlilardan olib tashlandi."
    add_favorite(user_id, movie_id)
    return "🧡 Sevimlilarga qo'shildi!"


def _toggle_watched(callback: CallbackQuery) -> str:
    movie_id = _movie_id(callback)
    user_id = callback.from_user.id
    if is_watched(user_id, movie_id):
        unmark_watched(user_id, movie_id)
        return "✅ «Ko'rdim» belgisi olib tashlandi."
    mark_watched(user_id, movie_id)
    return "✅ Ko'rilgan deb belgilandi!"


# --- Kino kartasidagi tugmalar ---

@router.callback_query(F.data.startswith(CB_SAVE))
async def cb_save(callback: CallbackQuery):
    toast = await _toggle_watchlist(callback)
    if toast is None:
        return
    await safe_edit_markup(callback, movie_card_keyboard(_movie_id(callback), callback.from_user.id))
    await callback.answer(toast)


@router.callback_query(F.data.startswith(CB_FAV))
async def cb_fav(callback: CallbackQuery):
    toast = await _toggle_favorite(callback)
    if toast is None:
        return
    await safe_edit_markup(callback, movie_card_keyboard(_movie_id(callback), callback.from_user.id))
    await callback.answer(toast)


@router.callback_query(F.data.startswith(CB_WATCHED))
async def cb_watched(callback: CallbackQuery):
    toast = _toggle_watched(callback)
    await safe_edit_markup(callback, movie_card_keyboard(_movie_id(callback), callback.from_user.id))
    await callback.answer(toast)


# --- Tomoshadan keyingi tugmalar ---
# XATO TUZATILDI: CB_AW_WATCHED prefiksida ikki nuqta yo'q edi ("aww"), shuning
# uchun callback.data.split(":")[1] IndexError bilan qulardi. Endi "aww:".

@router.callback_query(F.data.startswith(CB_AW_SAVE))
async def cb_aw_save(callback: CallbackQuery):
    toast = await _toggle_watchlist(callback)
    if toast is None:
        return
    await safe_edit_markup(callback, after_watch_keyboard(_movie_id(callback), callback.from_user.id))
    await callback.answer(toast)


@router.callback_query(F.data.startswith(CB_AW_FAV))
async def cb_aw_fav(callback: CallbackQuery):
    toast = await _toggle_favorite(callback)
    if toast is None:
        return
    await safe_edit_markup(callback, after_watch_keyboard(_movie_id(callback), callback.from_user.id))
    await callback.answer(toast)


@router.callback_query(F.data.startswith(CB_AW_WATCHED))
async def cb_aw_watched(callback: CallbackQuery):
    toast = _toggle_watched(callback)
    await safe_edit_markup(callback, after_watch_keyboard(_movie_id(callback), callback.from_user.id))
    await callback.answer(toast)


# ===========================================================================
# ⬅️ Orqaga
# ===========================================================================

@router.callback_query(F.data == CB_BACK)
async def cb_back(callback: CallbackQuery, state: FSMContext):
    nav = await load_nav(state)
    if nav and nav.get("list") not in (None, "home"):
        await restore_nav(callback, nav, edit=True)
        await callback.answer()
        return

    await state.clear()
    if is_admin_user(callback.from_user.id):
        await callback.message.answer("🧰 <b>Admin panel</b>", reply_markup=admin_menu_keyboard())
    else:
        await callback.message.answer("🧭 Bosh menyu", reply_markup=main_menu_keyboard())
    await callback.answer()
