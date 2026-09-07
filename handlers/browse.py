from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import (
    count_favorites,
    count_movies,
    count_premium_movies,
    count_reminders,
    count_watch_history,
    count_watchlist,
    get_favorites,
    get_genres,
    get_movies_by_genre,
    get_new_movies,
    get_premium_movies,
    get_random_movie,
    list_reminders,
    get_setting,
    get_watch_history,
    get_watchlist,
    is_premium,
    get_premium_until,
    get_or_create_open_conversation,
)
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
    CB_BACK,
    CB_CANCEL_REM,
    CB_GENRE,
    CB_GENRE_PAGE,
    CB_HIST_PAGE,
    CB_HOME,
    CB_NEW_PAGE,
    CB_PREMIUM_PAGE,
    CB_PREMIUM as CB_PREMIUM_BTN,
    CB_RANDOM_AGAIN,
    CB_REML_PAGE,
    CB_CONTACT,
    CB_SUPPORT_CLOSE,
    CB_WL_PAGE,
    CB_FAVL_PAGE,
    genres_keyboard,
    main_menu_keyboard,
    movie_card_keyboard,
    movie_list_keyboard,
    premium_keyboard,
    premium_offer_keyboard,
    random_movie_keyboard,
    reminders_list_keyboard,
    support_close_keyboard,
)
from utils import (
    clear_nav,
    emit,
    format_ts,
    movie_card_text,
    movie_row_text,
    notify_admins,
    pagination_pages,
    save_nav,
)

router = Router(name="browse")

PAGE_SIZE = 10


# ===========================================================================
# ✨ Yangi qo'shilganlar
# ===========================================================================

@router.message(F.text == BTN_NEW)
async def menu_new(message: Message, state: FSMContext):
    await _show_new(message, 1, state)


async def _show_new(target, page: int, state=None):
    rows = get_new_movies(PAGE_SIZE, (page - 1) * PAGE_SIZE)
    total = count_movies()
    total_pages = pagination_pages(total, PAGE_SIZE)
    if not rows:
        await emit(target, "✨ Hozircha yangi kinolar yo'q.", reply_markup=main_menu_keyboard())
        return
    kb = movie_list_keyboard(rows, page, total_pages, CB_NEW_PAGE)
    await emit(target, f"✨ <b>Yangi qo'shilganlar</b> ({total})", reply_markup=kb)
    if state:
        await save_nav(state, {"list": "new", "page": page})


@router.callback_query(F.data.startswith(CB_NEW_PAGE))
async def cb_new_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.rsplit(":", 1)[1])
    await _show_new(callback, page, state)
    await callback.answer()


# ===========================================================================
# 🌟 Premium filmlar
# ===========================================================================
# Bu bo'limga faqat admin kanalga "Premium" so'zini yozib, ketidan yuborgan
# kinolar tushadi ("Stop" yozilgunga qadar). Bo'lim faqat Premium
# foydalanuvchilar uchun ishlaydi — buni admin panel orqali yoqib/o'chirib
# qo'yish mumkin (⚙️ standart holat — yoqilgan).

def _premium_movies_locked() -> bool:
    return get_setting("premium_movies_locked", "1") == "1"


@router.message(F.text == BTN_PREMIUM_MOVIES)
async def menu_premium_movies(message: Message, state: FSMContext):
    await _show_premium_movies(message, 1, state)


async def _show_premium_movies(target, page: int, state=None):
    user_id = _user_id(target)

    if _premium_movies_locked() and not is_premium(user_id):
        text = (
            "🔒 <b>Premium filmlar</b>\n\n"
            "Bu bo'lim faqat Premium foydalanuvchilar uchun ochiq.\n"
            "🌟 Premium sotib olib, maxsus kinolarga kirish imkoniyatiga ega bo'ling!"
        )
        await emit(target, text, reply_markup=premium_offer_keyboard())
        return

    rows = get_premium_movies(PAGE_SIZE, (page - 1) * PAGE_SIZE)
    total = count_premium_movies()
    total_pages = pagination_pages(total, PAGE_SIZE)
    if not rows:
        await emit(target, "🌟 Hozircha Premium filmlar yo'q.", reply_markup=main_menu_keyboard())
        return
    kb = movie_list_keyboard(rows, page, total_pages, CB_PREMIUM_PAGE)
    await emit(target, f"🌟 <b>Premium filmlar</b> ({total})", reply_markup=kb)
    if state:
        await save_nav(state, {"list": "premium_movies", "page": page})


@router.callback_query(F.data.startswith(CB_PREMIUM_PAGE))
async def cb_premium_movies_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.rsplit(":", 1)[1])
    await _show_premium_movies(callback, page, state)
    await callback.answer()


# ===========================================================================
# 🎯 Kutilmagan tanlov
# ===========================================================================

@router.message(F.text == BTN_RANDOM)
async def menu_random(message: Message):
    await _show_random(message)


@router.callback_query(F.data == CB_RANDOM_AGAIN)
async def cb_random_again(callback: CallbackQuery):
    await _show_random(callback)
    await callback.answer()


async def _show_random(target):
    movie = get_random_movie()
    if not movie:
        await emit(target, "🎯 Hozircha kutubxonada kino yo'q.", reply_markup=main_menu_keyboard())
        return
    await emit(
        target,
        "🎯 <b>Tasodifiy tavsiya</b>\n\n" + movie_card_text(movie),
        reply_markup=random_movie_keyboard(movie["movie_id"], _user_id(target)),
    )


# ===========================================================================
# 🧩 Janrlar
# ===========================================================================

@router.message(F.text == BTN_GENRES)
async def menu_genres(message: Message):
    genres = get_genres()
    if not genres:
        await message.answer("🧩 Hozircha janrlar yo'q.", reply_markup=main_menu_keyboard())
        return
    await message.answer("🧩 <b>Janrlar</b>\n\nKerakli janrni tanlang:", reply_markup=genres_keyboard(genres))


@router.callback_query(F.data.startswith(CB_GENRE))
async def cb_genre(callback: CallbackQuery, state: FSMContext):
    genre = callback.data.split(":", 1)[1]
    await _show_genre(callback, genre, 1, state)
    await callback.answer()


@router.callback_query(F.data.startswith(CB_GENRE_PAGE))
async def cb_genre_page(callback: CallbackQuery, state: FSMContext):
    genre, page = callback.data.split(":", 1)[1].rsplit(":", 1)
    await _show_genre(callback, genre, int(page), state)
    await callback.answer()


async def _show_genre(target, genre: str, page: int, state=None):
    rows, total = get_movies_by_genre(genre, PAGE_SIZE, (page - 1) * PAGE_SIZE)
    total_pages = pagination_pages(total, PAGE_SIZE)
    if not rows:
        await emit(target, f"🧩 «{genre}» janrida kino yo'q.", reply_markup=main_menu_keyboard())
        return
    kb = movie_list_keyboard(rows, page, total_pages, f"{CB_GENRE_PAGE}{genre}:", include_home=True)
    await emit(target, f"🧩 <b>{genre}</b> — {total} ta kino", reply_markup=kb)
    if state:
        await save_nav(state, {"list": "genre", "genre": genre, "page": page})


# ===========================================================================
# 📌 Tanlovlarim
# ===========================================================================

@router.message(F.text == BTN_WATCHLIST)
async def menu_watchlist(message: Message, state: FSMContext):
    await _show_watchlist(message, 1, state)


async def _show_watchlist(target, page: int, state=None):
    user_id = _user_id(target)
    rows = get_watchlist(user_id, PAGE_SIZE, (page - 1) * PAGE_SIZE)
    total = count_watchlist(user_id)
    total_pages = pagination_pages(total, PAGE_SIZE)
    if not rows:
        await emit(target, "📌 Ro'yxatingiz bo'sh.\nFilm nomini yozib saqlang!", reply_markup=main_menu_keyboard())
        return
    kb = movie_list_keyboard(rows, page, total_pages, CB_WL_PAGE)
    await emit(target, f"📌 <b>Tanlovlarim</b> ({total})", reply_markup=kb)
    if state:
        await save_nav(state, {"list": "watchlist", "page": page})


@router.callback_query(F.data.startswith(CB_WL_PAGE))
async def cb_wl_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.rsplit(":", 1)[1])
    await _show_watchlist(callback, page, state)
    await callback.answer()


# ===========================================================================
# 🧡 Sevimlilar
# ===========================================================================

@router.message(F.text == BTN_FAVORITES)
async def menu_favorites(message: Message, state: FSMContext):
    await _show_favorites(message, 1, state)


async def _show_favorites(target, page: int, state=None):
    user_id = _user_id(target)
    rows = get_favorites(user_id, PAGE_SIZE, (page - 1) * PAGE_SIZE)
    total = count_favorites(user_id)
    total_pages = pagination_pages(total, PAGE_SIZE)
    if not rows:
        await emit(target, "🧡 Sevimlilar ro'yxatingiz bo'sh.", reply_markup=main_menu_keyboard())
        return
    kb = movie_list_keyboard(rows, page, total_pages, CB_FAVL_PAGE)
    await emit(target, f"🧡 <b>Sevimlilar</b> ({total})", reply_markup=kb)
    if state:
        await save_nav(state, {"list": "favorites", "page": page})


@router.callback_query(F.data.startswith(CB_FAVL_PAGE))
async def cb_favl_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.rsplit(":", 1)[1])
    await _show_favorites(callback, page, state)
    await callback.answer()


# ===========================================================================
# 📜 Tomosha tarixi
# ===========================================================================

@router.message(F.text == BTN_HISTORY)
async def menu_history(message: Message, state: FSMContext):
    await _show_history(message, 1, state)


async def _show_history(target, page: int, state=None):
    user_id = _user_id(target)
    rows = get_watch_history(user_id, PAGE_SIZE, (page - 1) * PAGE_SIZE)
    total = count_watch_history(user_id)
    total_pages = pagination_pages(total, PAGE_SIZE)
    if not rows:
        await emit(target, "📜 Tomosha tarixingiz bo'sh.", reply_markup=main_menu_keyboard())
        return
    kb = movie_list_keyboard(rows, page, total_pages, CB_HIST_PAGE)
    await emit(target, f"📜 <b>Tomosha tarixi</b> ({total})", reply_markup=kb)
    if state:
        await save_nav(state, {"list": "history", "page": page})


@router.callback_query(F.data.startswith(CB_HIST_PAGE))
async def cb_hist_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.rsplit(":", 1)[1])
    await _show_history(callback, page, state)
    await callback.answer()


# ===========================================================================
# 🔔 Eslatmalar ro'yxati
# ===========================================================================

@router.message(F.text == BTN_REMINDERS)
async def menu_reminders(message: Message, state: FSMContext):
    await _show_reminders(message, 1, state)


async def _show_reminders(target, page: int, state=None):
    user_id = _user_id(target)
    rows = list_reminders(user_id, PAGE_SIZE, (page - 1) * PAGE_SIZE)
    total = count_reminders(user_id)
    total_pages = pagination_pages(total, PAGE_SIZE)
    if not rows:
        await emit(target, "🔔 Sizda faol eslatmalar yo'q.\nFilm kartasidagi «🔔 Eslatma» tugmasini bosing.", reply_markup=main_menu_keyboard())
        return
    kb = reminders_list_keyboard(rows, page, total_pages)
    await emit(target, f"🔔 <b>Eslatmalarim</b> ({total})", reply_markup=kb)
    if state:
        await save_nav(state, {"list": "reminders", "page": page})


@router.callback_query(F.data.startswith(CB_REML_PAGE))
async def cb_reml_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.rsplit(":", 1)[1])
    await _show_reminders(callback, page, state)
    await callback.answer()


# ===========================================================================
# 🪪 Profilim
# ===========================================================================

@router.message(F.text == BTN_PROFILE)
async def menu_profile(message: Message):
    user_id = message.from_user.id
    watched = count_watch_history(user_id)
    saved = count_watchlist(user_id)
    favs = count_favorites(user_id)
    rems = count_reminders(user_id)
    active = is_premium(user_id)
    prem = "✅ Aktiv" if active else "❌ Yo'q"
    until = get_premium_until(user_id)
    prem_line = f"\n🌟 <b>Premium:</b> {prem}"
    if until and active:
        prem_line += f"\n📅 Amal qiladi: {format_ts(until)} gacha"

    text = (
        f"🪪 <b>Mening profilim</b>\n\n"
        f"🍿 Ko'rilgan: {watched}\n"
        f"📌 Saqlangan: {saved}\n"
        f"🧡 Sevimlilar: {favs}\n"
        f"🔔 Eslatmalar: {rems}"
        f"{prem_line}"
    )
    await message.answer(text, reply_markup=main_menu_keyboard())


# ===========================================================================
# 🌟 Premium
# ===========================================================================

@router.message(F.text == BTN_PREMIUM)
async def menu_premium(message: Message):
    await _show_premium(message)


@router.callback_query(F.data == CB_PREMIUM_BTN)
async def cb_premium(callback: CallbackQuery):
    await _show_premium(callback)
    await callback.answer()


async def _show_premium(target):
    user_id = _user_id(target)
    if is_premium(user_id):
        until = get_premium_until(user_id)
        text = (
            "🌟 <b>Premium obuna</b>\n\n"
            f"✅ Sizning Premium obunangiz faol.\n"
            f"📅 Amal qilish muddati: {format_ts(until)} gacha\n\n"
            "🔓 Majburiy kanallarga a'zo bo'lmasdan ham kinolarni bemalol ko'ra olasiz!"
        )
        await emit(target, text, reply_markup=premium_keyboard())
        return

    await emit(target, build_premium_text(), reply_markup=premium_keyboard())


def build_premium_text() -> str:
    """Premium posti.

    Admin `📝 Premium posti (matn)` orqali o'z matnini qo'yishi mumkin.
    Matnda quyidagi o'rinbosarlar ishlaydi:
      {price} {days}
    Matn qo'yilmagan bo'lsa — standart post avtomatik yig'iladi.
    """
    price = get_setting("premium_price", "15 000 so'm")
    days = get_setting("premium_days", "30")

    custom = get_setting("premium_text", "")
    if custom:
        return (custom
                .replace("{price}", str(price))
                .replace("{days}", str(days)))

    lines = ["🌟 <b>Premium OBUNA</b>\n"]
    lines.append("🔒 Botdan foydalanish uchun odatda kanallarga a'zo bo'lish shart.")
    lines.append("")
    lines.append("🌟 <b>Premium bilan:</b>")
    lines.append("✅ Majburiy kanallarga a'zo bo'lmasdan kinolarni bemalol ko'rasiz!")
    lines.append("")
    lines.append(f"💵 Narx: <b>{price}</b>")
    lines.append(f"📅 Muddat: <b>{days} kun</b>")
    return "\n".join(lines)


# ===========================================================================
# 💬 Support
# ===========================================================================

@router.message(F.text == BTN_CONTACT)
async def menu_contact(message: Message, state: FSMContext):
    await _open_contact(message, state)


@router.callback_query(F.data == CB_CONTACT)
async def cb_contact(callback: CallbackQuery, state: FSMContext):
    await _open_contact(callback, state)
    await callback.answer()


async def _open_contact(target, state: FSMContext):
    """📮 Operator bilan bog'lanish — yozilgan har bir xabar to'g'ridan-to'g'ri adminga boradi."""
    from handlers.states import UserStates

    user_id = _user_id(target)
    await state.set_state(UserStates.support_chat)
    conv_id = get_or_create_open_conversation(user_id)
    await state.update_data(conv_id=conv_id)

    text = (
        f"📮 <b>Operator bilan bog'lanish</b>  <i>(#{conv_id})</i>\n\n"
        "Savolingiz yoki taklifingizni yozing — xabaringiz to'g'ridan-to'g'ri "
        "adminga yetkaziladi va u shu yerda javob beradi.\n\n"
        "💡 Kino so'ramoqchi bo'lsangiz, kino nomini yozing.\n"
        "🔒 Yakunlash uchun pastdagi tugmani bosing."
    )
    if isinstance(target, CallbackQuery):
        await target.message.answer(text, reply_markup=support_close_keyboard())
    else:
        await target.answer(text, reply_markup=support_close_keyboard())


# ===========================================================================
# CB_HOME — bosh menyu
# ===========================================================================

@router.callback_query(F.data == CB_HOME)
async def cb_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("🧭 Bosh menyu", reply_markup=main_menu_keyboard())
    await callback.answer()


# ===========================================================================
# CB_BACK — film kartasi orqaga qaytish
# ===========================================================================


# ===========================================================================
# Eslatma bekor qilish (eslatmalar ro'yxatidan)
# ===========================================================================

@router.callback_query(F.data.startswith(CB_CANCEL_REM))
async def cb_cancel_reminder(callback: CallbackQuery, state: FSMContext):
    from database import cancel_reminder

    reminder_id = int(callback.data.rsplit(":", 1)[1])
    if not cancel_reminder(reminder_id, callback.from_user.id):
        await callback.answer("⚠️ Eslatma topilmadi yoki allaqachon bekor qilingan.",
                              show_alert=True)
        return
    await callback.answer("🔔 Eslatma bekor qilindi.")
    # Ro'yxatni yangilab ko'rsatamiz (bo'sh bo'lsa — bosh menyu)
    await _show_reminders(callback, 1, state)


# ===========================================================================
# "Yana kino qidirish" — qidiruvga qaytaradi
# ===========================================================================

# ===========================================================================
# `noop` tugma (sahifalash raqami)
# ===========================================================================

@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "adm_back")
async def cb_adm_back(callback: CallbackQuery, state: FSMContext):
    from keyboards import admin_menu_keyboard
    from utils import is_admin_user

    await state.clear()
    if not is_admin_user(callback.from_user.id):
        await callback.message.answer("🧭 Bosh menyu", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    await callback.message.answer("🧰 <b>Admin panel</b>", reply_markup=admin_menu_keyboard())
    await callback.answer()


# ===========================================================================
# Yordamchi
# ===========================================================================

def _user_id(target) -> int:
    from aiogram.types import Message, CallbackQuery

    if isinstance(target, CallbackQuery):
        return target.from_user.id
    if isinstance(target, Message):
        return target.from_user.id
    raise TypeError(f"target: {type(target)}")


async def restore_nav(target, nav: dict, edit: bool = True):
    """Navigatsiya kontekstini qayta tiklaydi (orqaga qaytish uchun)."""
    kind = nav.get("list")
    page = nav.get("page", 1)

    if kind == "new":
        await _show_new(target, page)
    elif kind == "premium_movies":
        await _show_premium_movies(target, page)
    elif kind == "genre":
        await _show_genre(target, nav.get("genre", ""), page)
    elif kind == "watchlist":
        await _show_watchlist(target, page)
    elif kind == "favorites":
        await _show_favorites(target, page)
    elif kind == "history":
        await _show_history(target, page)
    elif kind == "reminders":
        await _show_reminders(target, page)
    elif kind == "home":
        await emit(target, "🧭 Bosh menyu", reply_markup=main_menu_keyboard())
    else:
        await emit(target, "🧭 Bosh menyu", reply_markup=main_menu_keyboard())
