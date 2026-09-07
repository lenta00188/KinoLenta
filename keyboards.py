from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from database import is_favorite, is_in_watchlist, is_watched
from utils import format_ts

# ===========================================================================
# Callback data prefikslari (konstantalar)
# ===========================================================================

CB_HOME = "home"
CB_MOVIE = "movie:"
CB_WATCH = "watch:"
CB_SAVE = "save:"
CB_FAV = "fav:"
CB_WATCHED = "watched:"
CB_REM = "rem:"
CB_REM_PICK = "rempick:"
CB_CANCEL_REM = "cancelrem:"
CB_BACK = "back"
CB_NEW_PAGE = "new:"
CB_PREMIUM_PAGE = "premmov:"
CB_RANDOM_AGAIN = "rand"
CB_GENRE = "genre:"
CB_GENRE_PAGE = "genref:"
CB_WL_PAGE = "wl:"
CB_FAVL_PAGE = "favl:"
CB_HIST_PAGE = "hist:"
CB_REML_PAGE = "reml:"
CB_PREMIUM = "prem"
CB_PAY_START = "pay:start"
CB_PAY_DONE = "pay:done"
CB_AW_SAVE = "awsave:"
CB_AW_FAV = "awfav:"
CB_AW_WATCHED = "aww:"
CB_SUPPORT_CLOSE = "sup:close"
CB_ADM_SUP_VIEW = "asup:view:"
CB_ADM_SUP_REPLY = "asup:reply:"
CB_ADM_SUP_CLOSE = "asup:close:"
CB_ADM_PAY_VIEW = "apay:view:"
CB_ADM_PAY_APPROVE = "apay:approve:"
CB_ADM_PAY_REJECT = "apay:reject:"
CB_ADM_PREMIUM_EDIT = "aprem:edit:"   # aprem:edit:<field>
CB_ADM_PREMIUM_SECTION_TOGGLE = "aprem:sectoggle"  # "Premium filmlar" bo'limini qulflash on/off
CB_CHECK_SUB = "checksub"
CB_CONTACT = "contact"
CB_ADM_SUB_ADD = "asub:add"
CB_ADM_SUB_DEL = "asub:del:"
CB_ADM_PREMIUM_TEXT = "aprem:text"
CB_ADM_START_TEXT = "astart:text"
CB_ADM_ADMINS = "aadm:list"
CB_ADM_ADMIN_ADD = "aadm:add"
CB_ADM_ADMIN_DEL = "aadm:del:"        # aadm:del:<user_id>
CB_ADM_BC_SEG = "abc:seg:"            # abc:seg:all | premium | free
CB_ADM_PREM_GRANT = "aprem:grant"     # foydalanuvchiga qo'lda premium
CB_ADM_PREM_REVOKE = "aprem:revoke"

# ===========================================================================
# Foydalanuvchi — asosiy menyu (reply keyboard)
# ===========================================================================

BTN_NEW = "✨ Yangi qo'shilganlar"
BTN_PREMIUM_MOVIES = "🌟 Premium filmlar"
BTN_GENRES = "🧩 Janrlar"
BTN_WATCHLIST = "📌 Tanlovlarim"
BTN_FAVORITES = "🧡 Sevimlilar"
BTN_HISTORY = "📜 Tomosha tarixi"
BTN_REMINDERS = "🔔 Eslatmalar"
BTN_RANDOM = "🎯 Kutilmagan tanlov"
BTN_PROFILE = "🪪 Profilim"
BTN_PREMIUM = "🌟 Premium bo'lish"
BTN_CONTACT = "📮 Operator bilan bog'lanish"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Asosiy menyu. Eng yuqorida — 🌟 Premium bo'lish (butun kenglikda)."""
    builder = ReplyKeyboardBuilder()
    builder.button(text=BTN_PREMIUM)      # 1-qator: eng ko'zga tashlanadigan joy
    builder.button(text=BTN_NEW)
    builder.button(text=BTN_PREMIUM_MOVIES)
    builder.button(text=BTN_GENRES)
    builder.button(text=BTN_RANDOM)
    builder.button(text=BTN_WATCHLIST)
    builder.button(text=BTN_FAVORITES)
    builder.button(text=BTN_HISTORY)
    builder.button(text=BTN_REMINDERS)
    builder.button(text=BTN_PROFILE)
    builder.button(text=BTN_CONTACT)
    builder.adjust(1, 2, 2, 2, 2, 2)
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="🔢 Kino raqamini yuboring...",
    )


# ===========================================================================
# Kino kartasi
# ===========================================================================

def movie_card_keyboard(movie_id: int, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🍿 FILMNI TOMOSHA QILISH", callback_data=f"{CB_WATCH}{movie_id}")
    builder.button(
        text=("📌 Saqlangan ✅" if is_in_watchlist(user_id, movie_id) else "📌 Saqlash"),
        callback_data=f"{CB_SAVE}{movie_id}",
    )
    builder.button(
        text=("🧡 Sevimli ✅" if is_favorite(user_id, movie_id) else "🧡 Sevimlilarga"),
        callback_data=f"{CB_FAV}{movie_id}",
    )
    builder.button(
        text=("✅ Ko'rilgan ✔️" if is_watched(user_id, movie_id) else "✅ Ko'rdim"),
        callback_data=f"{CB_WATCHED}{movie_id}",
    )
    builder.button(text="🔔 Eslatma", callback_data=f"{CB_REM}{movie_id}")
    builder.button(text="⬅️ Orqaga", callback_data=CB_BACK)
    builder.adjust(1, 3, 2)
    return builder.as_markup()


def random_movie_keyboard(movie_id: int, user_id: int) -> InlineKeyboardMarkup:
    """Kutilmagan tanlov kartasi — 'yana tasodifiy' tugmasi bilan."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🍿 FILMNI TOMOSHA QILISH", callback_data=f"{CB_WATCH}{movie_id}")
    builder.button(
        text=("📌 Saqlangan ✅" if is_in_watchlist(user_id, movie_id) else "📌 Saqlash"),
        callback_data=f"{CB_SAVE}{movie_id}",
    )
    builder.button(
        text=("🧡 Sevimli ✅" if is_favorite(user_id, movie_id) else "🧡 Sevimlilarga"),
        callback_data=f"{CB_FAV}{movie_id}",
    )
    builder.button(text="🔔 Eslatma", callback_data=f"{CB_REM}{movie_id}")
    builder.button(text="🎯 Boshqasini ko'rsat", callback_data=CB_RANDOM_AGAIN)
    builder.button(text="🧭 Bosh menyu", callback_data=CB_HOME)
    builder.adjust(1, 2, 1, 2)
    return builder.as_markup()


def after_watch_keyboard(movie_id: int, user_id: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=("📌 Saqlangan" if is_in_watchlist(user_id, movie_id) else "📌 Saqlash"),
        callback_data=f"{CB_AW_SAVE}{movie_id}",
    )
    builder.button(
        text=("🧡 Sevimli ✅" if is_favorite(user_id, movie_id) else "🧡 Sevimlilarga"),
        callback_data=f"{CB_AW_FAV}{movie_id}",
    )
    builder.button(
        text=("✅ Ko'rilgan ✔️" if is_watched(user_id, movie_id) else "✅ Ko'rdim"),
        callback_data=f"{CB_AW_WATCHED}{movie_id}",
    )
    builder.button(text="🔔 Eslatma", callback_data=f"{CB_REM}{movie_id}")
    builder.button(text="🌟 Premium bo'lish", callback_data=CB_PREMIUM)
    builder.button(text="🧭 Bosh menyu", callback_data=CB_HOME)
    builder.adjust(3, 2, 1)
    return builder.as_markup()


def reminder_options_keyboard(movie_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🕕 Bugun 18:00", callback_data=f"{CB_REM_PICK}{movie_id}:today18")
    builder.button(text="🌙 Bugun 21:00", callback_data=f"{CB_REM_PICK}{movie_id}:today21")
    builder.button(text="📅 Ertaga", callback_data=f"{CB_REM_PICK}{movie_id}:tomorrow")
    builder.button(text="🗓 Boshqa vaqt", callback_data=f"{CB_REM_PICK}{movie_id}:custom")
    builder.button(text="⬅️ Orqaga", callback_data=f"{CB_MOVIE}{movie_id}")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


# ===========================================================================
# Sahifalash (paginatsiya)
# ===========================================================================

def _clip(text: str, limit: int = 48) -> str:
    """Tugma matni juda uzun bo'lmasligi uchun qisqartiradi."""
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _pager(page: int, total_pages: int, prefix: str, builder: InlineKeyboardBuilder) -> None:
    row = []
    if page > 1:
        row.append(InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}{page-1}"))
    row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        row.append(InlineKeyboardButton(text="➡️", callback_data=f"{prefix}{page+1}"))
    builder.row(*row)


def movie_list_keyboard(
    rows,
    page: int,
    total_pages: int,
    page_prefix: str,
    include_home: bool = True,
) -> InlineKeyboardMarkup:
    """Ro'yxat: har bir kino tugma + sahifalash + bosh menyu."""
    builder = InlineKeyboardBuilder()
    for m in rows:
        label = _clip(m["title"])
        if m["year"]:
            label = f"{label} — {m['year']}"
        builder.button(text=label, callback_data=f"{CB_MOVIE}{m['movie_id']}")
    builder.adjust(1)
    if total_pages > 1:
        _pager(page, total_pages, page_prefix, builder)
    if include_home:
        builder.row(InlineKeyboardButton(text="🧭 Bosh menyu", callback_data=CB_HOME))
    return builder.as_markup()


def genres_keyboard(genres: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for g in genres:
        builder.button(text=g, callback_data=f"{CB_GENRE}{g}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🧭 Bosh menyu", callback_data=CB_HOME))
    return builder.as_markup()


# ===========================================================================
# Eslatmalar ro'yxati (bittasini bekor qilish uchun)
# ===========================================================================

def reminders_list_keyboard(rows, page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for r in rows:
        when = format_ts(r["reminder_time"])
        label = f"❌ {_clip(r['title'] or str(r['movie_id']), 28)} — {when}"
        builder.button(text=label, callback_data=f"{CB_CANCEL_REM}{r['id']}")
    builder.adjust(1)
    if total_pages > 1:
        _pager(page, total_pages, CB_REML_PAGE, builder)
    builder.row(InlineKeyboardButton(text="🧭 Bosh menyu", callback_data=CB_HOME))
    return builder.as_markup()


# ===========================================================================
# Premium
# ===========================================================================

def premium_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🧾 To'lov qilish", callback_data=CB_PAY_START)
    builder.button(text="⬅️ Orqaga", callback_data=CB_HOME)
    builder.adjust(1)
    return builder.as_markup()


def pay_done_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Men to'ladim", callback_data=CB_PAY_DONE)
    builder.button(text="⬅️ Orqaga", callback_data=CB_HOME)
    builder.adjust(1)
    return builder.as_markup()


# ===========================================================================
# Support
# ===========================================================================

def support_close_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔒 Murojatni yakunlash", callback_data=CB_SUPPORT_CLOSE)
    builder.button(text="🧭 Bosh menyu", callback_data=CB_HOME)
    builder.adjust(1)
    return builder.as_markup()


# ===========================================================================
# Admin — asosiy menyu (reply keyboard)
# ===========================================================================

ADM_BTN_STATS = "📊 Statistika"
ADM_BTN_CATALOG = "🍿 Kinolar katalogi"
ADM_BTN_USERS = "👥 Foydalanuvchilar"
ADM_BTN_PREMIUM = "🌟 Premium sozlamalari"
ADM_BTN_TICKETS = "💬 Murojatlar"
ADM_BTN_PAYMENTS = "🪙 To'lovlar"
ADM_BTN_CHANNELS = "📡 Majburiy obuna"
ADM_BTN_ADMINS = "👑 Adminlar"
ADM_BTN_BROADCAST = "📣 Xabar yuborish"
ADM_BTN_START_TEXT = "📝 Start posti"
ADM_BTN_SUBSCRIBE_TEXT = "📝 Majburiy obuna matni"
ADM_BTN_VIP_BUTTON = "📝 Premium tugmasi matni"
ADM_BTN_CHANNEL_BUTTON = "📝 Kanal tugmasi matni"
ADM_BTN_EXIT = "🚪 Chiqish"
ADM_BTN_CANCEL = "❌ Bekor qilish"
ADM_BTN_BACK = "⬅️ Orqaga"


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=ADM_BTN_STATS)
    builder.button(text=ADM_BTN_CATALOG)
    builder.button(text=ADM_BTN_USERS)
    builder.button(text=ADM_BTN_PREMIUM)
    builder.button(text=ADM_BTN_CHANNELS)
    builder.button(text=ADM_BTN_TICKETS)
    builder.button(text=ADM_BTN_PAYMENTS)
    builder.button(text=ADM_BTN_ADMINS)
    builder.button(text=ADM_BTN_BROADCAST)
    builder.button(text=ADM_BTN_START_TEXT)
    builder.button(text=ADM_BTN_SUBSCRIBE_TEXT)
    builder.button(text=ADM_BTN_VIP_BUTTON)
    builder.button(text=ADM_BTN_CHANNEL_BUTTON)
    builder.button(text=ADM_BTN_EXIT)
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=ADM_BTN_CANCEL)
    return builder.as_markup(resize_keyboard=True)


def confirm_broadcast_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="✅ Yuborish")
    builder.button(text=ADM_BTN_CANCEL)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


# --- Admin: support ---

def admin_support_list_keyboard(conversations) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for c in conversations:
        name = c["full_name"] or c["username"] or str(c["user_id"])
        builder.button(
            text=f"#{c['id']} • {name}",
            callback_data=f"{CB_ADM_SUP_VIEW}{c['id']}",
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_back"))
    return builder.as_markup()


def admin_conversation_keyboard(conv_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Javob berish", callback_data=f"{CB_ADM_SUP_REPLY}{conv_id}")
    builder.button(text="🔒 Yopish", callback_data=f"{CB_ADM_SUP_CLOSE}{conv_id}")
    builder.button(text="⬅️ Orqaga", callback_data="adm_back")
    builder.adjust(2, 1)
    return builder.as_markup()


# --- Admin: to'lovlar ---

def admin_payments_keyboard(payments) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in payments:
        name = p["username"] or p["full_name"] or str(p["user_id"])
        builder.button(
            text=f"#{p['id']} • {name} • {p['amount'] or ''}".strip(),
            callback_data=f"apay:view:{p['id']}",
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_back"))
    return builder.as_markup()


def admin_payment_action_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data=f"{CB_ADM_PAY_APPROVE}{payment_id}")
    builder.button(text="❌ Rad etish", callback_data=f"{CB_ADM_PAY_REJECT}{payment_id}")
    builder.adjust(2)
    return builder.as_markup()


# --- Admin: katalog ---

def admin_catalog_keyboard(rows, page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for m in rows:
        label = f"{m['movie_id']} — {_clip(m['title'])}"
        if m["year"]:
            label = f"{label} ({m['year']})"
        builder.button(text=label, callback_data=f"{CB_MOVIE}{m['movie_id']}")
    builder.adjust(1)
    if total_pages > 1:
        _pager(page, total_pages, "admcatalog:", builder)
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_back"))
    return builder.as_markup()


# ===========================================================================
# 👑 Admin — adminlarni boshqarish
# ===========================================================================

def admins_keyboard(admins, owner_ids, can_manage: bool) -> InlineKeyboardMarkup:
    """admins: (user_id, username, full_name) qatorlari; owner_ids o'chirilmaydi."""
    builder = InlineKeyboardBuilder()
    for a in admins:
        uid = a["user_id"]
        name = a["full_name"] or a["username"] or str(uid)
        if uid in owner_ids:
            builder.button(text=f"👑 {name} (ega)", callback_data="noop")
        elif can_manage:
            builder.button(text=f"🗑 {name} — o'chirish",
                           callback_data=f"{CB_ADM_ADMIN_DEL}{uid}")
        else:
            builder.button(text=f"🧰 {name}", callback_data="noop")
    builder.adjust(1)
    if can_manage:
        builder.row(InlineKeyboardButton(text="➕ Admin qo'shish",
                                         callback_data=CB_ADM_ADMIN_ADD))
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_back"))
    return builder.as_markup()


# ===========================================================================
# 📣 Broadcast segmentlari
# ===========================================================================

def broadcast_segment_keyboard(counts: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"👥 Hammaga ({counts.get('all', 0)})",
                   callback_data=f"{CB_ADM_BC_SEG}all")
    builder.button(text=f"🌟 Premium ({counts.get('premium', 0)})",
                   callback_data=f"{CB_ADM_BC_SEG}premium")
    builder.button(text=f"🙋 Oddiy ({counts.get('free', 0)})",
                   callback_data=f"{CB_ADM_BC_SEG}free")
    builder.button(text="⬅️ Orqaga", callback_data="adm_back")
    builder.adjust(1)
    return builder.as_markup()


# ===========================================================================
# Bildirishnoma tugmalari (adminlarga yuboriladigan xabarlar uchun)
# ===========================================================================

def payment_notify_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data=f"{CB_ADM_PAY_APPROVE}{payment_id}")
    builder.button(text="❌ Rad etish", callback_data=f"{CB_ADM_PAY_REJECT}{payment_id}")
    builder.adjust(2)
    return builder.as_markup()


def support_notify_keyboard(conv_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Javob berish", callback_data=f"{CB_ADM_SUP_REPLY}{conv_id}")
    builder.button(text="👁 Suhbatni ochish", callback_data=f"{CB_ADM_SUP_VIEW}{conv_id}")
    builder.button(text="🔒 Yopish", callback_data=f"{CB_ADM_SUP_CLOSE}{conv_id}")
    builder.adjust(2, 1)
    return builder.as_markup()


def premium_manage_keyboard() -> InlineKeyboardMarkup:
    from database import get_setting

    locked = get_setting("premium_movies_locked", "1") == "1"
    toggle_label = (
        "🔒 Premium filmlar: faqat Premium" if locked
        else "🔓 Premium filmlar: hammaga ochiq"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="🪙 Narx", callback_data=f"{CB_ADM_PREMIUM_EDIT}price")
    builder.button(text="📅 Muddat (kun)", callback_data=f"{CB_ADM_PREMIUM_EDIT}days")
    builder.button(text="📲 To'lov ma'lumotlari",
                   callback_data=f"{CB_ADM_PREMIUM_EDIT}payment_info")
    builder.button(text="📝 Premium posti (matn)", callback_data=CB_ADM_PREMIUM_TEXT)
    builder.button(text="🎁 Qo'lda premium berish", callback_data=CB_ADM_PREM_GRANT)
    builder.button(text="🚫 Premiumni bekor qilish", callback_data=CB_ADM_PREM_REVOKE)
    builder.button(text=toggle_label, callback_data=CB_ADM_PREMIUM_SECTION_TOGGLE)
    builder.button(text="⬅️ Orqaga", callback_data="adm_back")
    builder.adjust(2, 1, 1, 1, 1, 1, 1)
    return builder.as_markup()


def user_cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data=CB_HOME)
    return builder.as_markup()


# ===========================================================================
# 📡 Majburiy obuna
# ===========================================================================

def subscription_keyboard(channels) -> InlineKeyboardMarkup:
    """Obuna posti klaviaturasi:
    1) 🌟 Yoki premium sotib oling — eng yuqorida (matnini admin sozlaydi).
       Bu tugma orqali premium sotib olgan foydalanuvchi kanallarga obuna
       bo'lishi shart emas — premium xarid yo'li majburiy obunaga muqobil.
    2) har bir majburiy kanal — alohida tugma (kanalga link, matni admin sozlaydi)
    3) ✅ Obuna bo'ldim — tekshirish
    """
    from database import get_setting

    channel_label = get_setting("channel_button_text", "") or "📡 Obuna bo'lish"
    vip_label = get_setting("vip_button_text", "") or "🌟 Yoki premium sotib oling"

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=vip_label, callback_data=CB_PREMIUM))

    multiple = len(channels) > 1
    for idx, ch in enumerate(channels, start=1):
        url = ch["invite_link"] or (
            f"https://t.me/{ch['username'].lstrip('@')}" if ch["username"] else None
        )
        label = f"{channel_label} {idx}" if multiple else channel_label
        if url:
            builder.button(text=label, url=url)
        else:
            builder.button(text=label, callback_data="noop")
    builder.adjust(1)

    builder.row(InlineKeyboardButton(text="✅ Obuna bo'ldim", callback_data=CB_CHECK_SUB))
    return builder.as_markup()


def admin_channels_keyboard(channels) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        title = _clip(ch["title"] or ch["username"] or str(ch["chat_id"]), 30)
        builder.button(text=f"🗑 {title}", callback_data=f"{CB_ADM_SUB_DEL}{ch['chat_id']}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data=CB_ADM_SUB_ADD))
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_back"))
    return builder.as_markup()


# ===========================================================================
# 🌟 Premium taklifi (funksiya bloklanganda ko'rsatiladi)
# ===========================================================================

def premium_offer_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🌟 Premium bo'lish", callback_data=CB_PREMIUM)
    builder.button(text="🧭 Bosh menyu", callback_data=CB_HOME)
    builder.adjust(1)
    return builder.as_markup()


def contact_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📮 Operator bilan bog'lanish", callback_data=CB_CONTACT)
    builder.button(text="🧭 Bosh menyu", callback_data=CB_HOME)
    builder.adjust(1)
    return builder.as_markup()
