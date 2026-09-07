import asyncio
import logging

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import OWNER_IDS
from database import (
    add_admin,
    add_required_channel,
    count_active_users,
    count_movies,
    count_required_channels,
    count_premium_users,
    count_segment,
    count_users,
    find_user,
    get_payment,
    get_recent_users,
    get_setting,
    get_user,
    get_user_ids_by_segment,
    grant_premium,
    is_premium,
    list_required_channels,
    list_db_admins,
    list_movies,
    list_open_conversations,
    list_pending_payments,
    list_premium_users,
    remove_admin,
    remove_required_channel,
    revoke_premium,
    save_user,
    set_payment_status,
    set_setting,
    stats_summary,
)
from handlers.filters import IsAdmin
from handlers.states import AdminStates
from keyboards import (
    ADM_BTN_ADMINS,
    ADM_BTN_BROADCAST,
    ADM_BTN_CANCEL,
    ADM_BTN_CATALOG,
    ADM_BTN_CHANNELS,
    ADM_BTN_EXIT,
    ADM_BTN_PAYMENTS,
    ADM_BTN_PREMIUM,
    ADM_BTN_STATS,
    ADM_BTN_START_TEXT,
    ADM_BTN_SUBSCRIBE_TEXT,
    ADM_BTN_TICKETS,
    ADM_BTN_USERS,
    ADM_BTN_VIP_BUTTON,
    ADM_BTN_CHANNEL_BUTTON,
    CB_ADM_ADMIN_ADD,
    CB_ADM_ADMIN_DEL,
    CB_ADM_ADMINS,
    CB_ADM_BC_SEG,
    CB_ADM_PAY_APPROVE,
    CB_ADM_PAY_REJECT,
    CB_ADM_PAY_VIEW,
    CB_ADM_PREM_GRANT,
    CB_ADM_PREM_REVOKE,
    CB_ADM_PREMIUM_EDIT,
    CB_ADM_PREMIUM_SECTION_TOGGLE,
    CB_ADM_PREMIUM_TEXT,
    CB_ADM_SUB_ADD,
    CB_ADM_SUB_DEL,
    admin_catalog_keyboard,
    admin_channels_keyboard,
    admin_menu_keyboard,
    admin_payment_action_keyboard,
    admin_payments_keyboard,
    admin_support_list_keyboard,
    admins_keyboard,
    broadcast_segment_keyboard,
    cancel_keyboard,
    confirm_broadcast_keyboard,
    main_menu_keyboard,
    premium_manage_keyboard,
)
from utils import emit, format_ts, is_owner

router = Router(name="admin")
# MUHIM: filtr endi DINAMIK. Avval `F.from_user.id.in_(ADMIN_IDS)` ishlatilgan edi,
# u bazaga qo'shilgan yangi adminlarni ko'rmasdi. Bundan tashqari callback'lar
# umuman filtrlanmagan edi — bu xavfsizlik xatosi (har kim to'lov tasdiqlay olardi).
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

logger = logging.getLogger(__name__)

MENU_TEXT = "🧰 <b>Admin panel</b>\n\nKerakli bo'limni pastdagi tugmalardan tanlang:"
CATALOG_PAGE_SIZE = 8
SEGMENT_LABELS = {"all": "👥 Hammaga", "premium": "🌟 Premium", "free": "🙋 Oddiy"}
PREMIUM_FIELDS = {
    "price": ("🪙 Narx", "premium_price"),
    "days": ("📅 Muddat (kun)", "premium_days"),
    "payment_info": ("📲 To'lov ma'lumotlari", "payment_info"),
}


# ===========================================================================
# Panelni ochish / bekor qilish
# ===========================================================================

@router.message(Command("admin"), StateFilter("*"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    save_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    await message.answer(MENU_TEXT, reply_markup=admin_menu_keyboard())


@router.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🚫 Bekor qilindi.", reply_markup=admin_menu_keyboard())


@router.message(F.text == ADM_BTN_CANCEL, StateFilter("*"))
async def btn_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🚫 Bekor qilindi.", reply_markup=admin_menu_keyboard())


@router.message(F.text == ADM_BTN_EXIT, StateFilter("*"))
async def btn_exit_admin(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ Admin paneldan chiqdingiz.", reply_markup=main_menu_keyboard())


# ===========================================================================
# Backfill — kanaldagi MAVJUD postlarni bazaga indekslash
# ===========================================================================

@router.message(Command("backfill"), StateFilter("*"))
async def cmd_backfill(message: Message, state: FSMContext):
    from handlers.channel import backfill_channel

    await state.clear()
    chat_id = message.chat.id
    holder = {}

    await message.answer(
        "🔄 <b>Backfill boshlandi!</b>\n\n"
        "Kanaldagi mavjud postlar skanerlanmoqda. Bu bir necha daqiqa olishi "
        "mumkin. Jarayon davomida bu chatga progress yozib boraman."
    )

    async def _progress(indexed, scanned, msg_id, done=False):
        if done:
            skipped = holder.get("skipped", 0)
            await message.bot.send_message(
                chat_id,
                f"✅ <b>Backfill tugadi!</b>\n\n"
                f"🍿 <b>Indekslangan:</b> {indexed} ta kino\n"
                f"📄 Tekshirilgan postlar: {scanned}\n"
                f"ℹ️ Caption'siz / tashlab ketilgan: {skipped}\n\n"
                "Endi barcha postlar bazada — qidiruv, janrlar va raqam orqali "
                "topish ishlaydi.",
            )
        else:
            await message.bot.send_message(
                chat_id, f"📊 {indexed} ta kino indekslandi (post #{msg_id})..."
            )

    async def _run():
        try:
            result = await backfill_channel(message.bot, chat_id, on_progress=_progress)
            holder["skipped"] = result["skipped"]
        except Exception as e:
            logger.exception("Backfill xatosi")
            await message.bot.send_message(chat_id, f"❌ Backfill xatosi: {e}")

    asyncio.create_task(_run())


# ===========================================================================
# 📊 Statistika
# ===========================================================================

@router.message(F.text == ADM_BTN_STATS)
async def btn_stats(message: Message, state: FSMContext):
    await state.clear()
    s = stats_summary()
    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{s['users']}</b>\n"
        f"🟢 Faol (7 kun): <b>{s['active_users']}</b>\n"
        f"🌟 Premium: <b>{s['premium_users']}</b>\n"
        f"🍿 Kinolar: <b>{s['movies']}</b> (jami bazada: {s['all_movies']})\n"
        f"👁 Umumiy ko'rishlar: <b>{s['total_views']}</b>\n"
        f"🔔 Faol eslatmalar: <b>{s['reminders']}</b>\n"
        f"💬 Ochiq support: <b>{s['open_support']}</b>\n"
        f"🪙 Kutilayotgan to'lovlar: <b>{s['pending_payments']}</b>\n"
        f"📡 Majburiy obuna kanallari: <b>{count_required_channels()}</b>"
    )
    if s["top_movies"]:
        top = "\n".join(
            f"{i}. {r['title']}"
            f"{(' (' + str(r['year']) + ')') if r['year'] else ''} — {r['views']} ko'rish"
            for i, r in enumerate(s["top_movies"], 1)
        )
        text += f"\n\n🔥 <b>Eng ko'p ko'rilganlar:</b>\n{top}"
    if s["most_requested"]:
        req = "\n".join(f"• {r['title']} — {r['requests']}" for r in s["most_requested"][:5])
        text += f"\n\n📈 <b>Eng ko'p so'ralgan:</b>\n{req}"
    await message.answer(text, reply_markup=admin_menu_keyboard())


# ===========================================================================
# 🍿 Kinolar katalogi
# ===========================================================================

@router.message(F.text == ADM_BTN_CATALOG)
async def btn_catalog(message: Message, state: FSMContext):
    await state.clear()
    await _show_catalog(message, 1)


@router.callback_query(F.data.startswith("admcatalog:"))
async def cb_catalog_page(callback: CallbackQuery):
    page = int(callback.data.rsplit(":", 1)[1])
    await _show_catalog(callback, page)
    await callback.answer()


async def _show_catalog(target, page: int):
    total = count_movies()
    total_pages = max(1, -(-total // CATALOG_PAGE_SIZE))
    page = max(1, min(page, total_pages))
    rows = list_movies(CATALOG_PAGE_SIZE, (page - 1) * CATALOG_PAGE_SIZE)
    if not rows:
        await emit(
            target,
            "🍿 Katalog bo'sh. Kinolarni kanalga post qiling — ular avtomatik "
            "indekslanadi. Eski postlar uchun /backfill.",
            reply_markup=admin_menu_keyboard(),
        )
        return
    await emit(
        target,
        f"🍿 <b>Kinolar katalogi</b> ({total})\n\n"
        "Format: <code>ID — Nom (yil)</code>\nFilmni tanlang:",
        reply_markup=admin_catalog_keyboard(rows, page, total_pages),
    )


# ===========================================================================
# 👥 Foydalanuvchilar
# ===========================================================================

@router.message(F.text == ADM_BTN_USERS)
async def btn_users(message: Message, state: FSMContext):
    await state.clear()
    lines = []
    for u in get_recent_users(15):
        name = u["full_name"] or u["username"] or str(u["user_id"])
        badge = " 🌟" if is_premium(u["user_id"]) else ""
        lines.append(f"• <code>{u['user_id']}</code> {name}{badge}")

    text = (
        "👥 <b>Foydalanuvchilar</b>\n\n"
        f"Jami: <b>{count_users()}</b> | Faol (7 kun): <b>{count_active_users()}</b> | "
        f"Premium: <b>{count_premium_users()}</b>\n\n"
    )
    text += ("<b>Oxirgi qo'shilganlar:</b>\n" + "\n".join(lines)) if lines else "Hozircha foydalanuvchilar yo'q."

    prem_rows = list_premium_users(10)
    if prem_rows:
        text += "\n\n🌟 <b>Premium foydalanuvchilar:</b>\n" + "\n".join(
            f"• <code>{p['user_id']}</code> {p['full_name'] or p['username'] or ''} — "
            f"{format_ts(p['premium_until'])} gacha"
            for p in prem_rows
        )
    await message.answer(text, reply_markup=admin_menu_keyboard())


# ===========================================================================
# 🌟 Premium sozlamalari
# ===========================================================================

def _premium_settings_text() -> str:
    price = get_setting("premium_price", "15 000 so'm")
    days = get_setting("premium_days", "30")
    payment_info = get_setting("payment_info", "Karta: 8600 0000 0000 0000")
    locked = get_setting("premium_movies_locked", "1") == "1"
    lock_status = "🔒 Faqat Premium foydalanuvchilar uchun" if locked else "🔓 Barcha foydalanuvchilar uchun ochiq"
    return (
        "🌟 <b>Premium sozlamalari</b>\n\n"
        f"🪙 Narx: <b>{price}</b>\n"
        f"📅 Muddat: <b>{days} kun</b>\n"
        f"📲 To'lov ma'lumotlari:\n<code>{payment_info}</code>\n\n"
        f"👤 Faol premium foydalanuvchilar: <b>{count_premium_users()}</b>\n"
        f"🍿 «Premium filmlar» bo'limi: <b>{lock_status}</b>\n\n"
        "O'zgartirish uchun tugmani bosing:"
    )


@router.message(F.text == ADM_BTN_PREMIUM)
async def btn_premium_settings(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(_premium_settings_text(), reply_markup=premium_manage_keyboard())


@router.callback_query(F.data.startswith(CB_ADM_PREMIUM_EDIT))
async def cb_premium_edit(callback: CallbackQuery, state: FSMContext):
    field = callback.data.rsplit(":", 1)[1]
    if field not in PREMIUM_FIELDS:
        await callback.answer("Noma'lum sozlama.", show_alert=True)
        return
    label = PREMIUM_FIELDS[field][0]
    await state.set_state(AdminStates.waiting_premium_value)
    await state.update_data(prem_field=field)
    prompts = {
        "price": "Yangi narxni yozing (masalan: <code>50 000 so'm</code>):",
        "days": "Yangi muddatni kunlarda yozing (masalan: <code>30</code>):",
        "payment_info": "Yangi to'lov ma'lumotlarini yozing (karta raqami, qabul qiluvchi):",
    }
    await callback.message.answer(
        f"✏️ <b>{label}</b>\n\n{prompts[field]}\n\n⛔ Bekor qilish: /cancel",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_premium_value, F.text)
async def receive_premium_value(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data.get("prem_field")
    if field not in PREMIUM_FIELDS:
        await state.clear()
        await message.answer("⚠️ Sozlama tanlanmagan.", reply_markup=admin_menu_keyboard())
        return
    value = message.text.strip()
    if field == "days" and (not value.isdigit() or int(value) <= 0):
        await message.answer(
            "❗️ Muddat musbat butun son bo'lishi kerak (kun). Qayta yozing yoki /cancel."
        )
        return
    await state.clear()
    set_setting(PREMIUM_FIELDS[field][1], value)
    await message.answer(
        f"✅ {PREMIUM_FIELDS[field][0]} yangilandi: <b>{value}</b>",
        reply_markup=admin_menu_keyboard(),
    )
    await message.answer(_premium_settings_text(), reply_markup=premium_manage_keyboard())


@router.message(AdminStates.waiting_premium_value)
async def wrong_premium_value(message: Message):
    await message.answer("❗️ Iltimos, matn yuboring yoki /cancel.")


# --- 🌟 «Premium filmlar» bo'limini qulflash on/off ---

@router.callback_query(F.data == CB_ADM_PREMIUM_SECTION_TOGGLE)
async def cb_premium_section_toggle(callback: CallbackQuery):
    locked = get_setting("premium_movies_locked", "1") == "1"
    new_value = "0" if locked else "1"
    set_setting("premium_movies_locked", new_value)

    status = "faqat Premium foydalanuvchilar uchun 🔒" if new_value == "1" else "barcha foydalanuvchilar uchun ochiq 🔓"
    await callback.answer(f"✅ «Premium filmlar» bo'limi endi {status}.", show_alert=True)
    await emit(callback, _premium_settings_text(), reply_markup=premium_manage_keyboard())


# --- Qo'lda premium berish / bekor qilish ---

@router.callback_query(F.data == CB_ADM_PREM_GRANT)
async def cb_prem_grant(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_premium_grant)
    await callback.message.answer(
        "🎁 <b>Qo'lda premium berish</b>\n\n"
        "Formatda yozing: <code>&lt;user_id yoki @username&gt; &lt;kun&gt;</code>\n"
        "Masalan: <code>123456789 30</code> yoki <code>@user 90</code>\n\n"
        "Kun ko'rsatilmasa, sozlamalardagi standart muddat olinadi.\n"
        "⛔ Bekor qilish: /cancel",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_premium_grant, F.text)
async def receive_prem_grant(message: Message, state: FSMContext):
    parts = message.text.split()
    user = find_user(parts[0]) if parts else None
    if not user:
        await message.answer(
            "❌ Foydalanuvchi topilmadi. U avval botga /start bergan bo'lishi kerak.\n"
            "Qayta urinib ko'ring yoki /cancel."
        )
        return
    days_raw = parts[1] if len(parts) > 1 else (get_setting("premium_days", "30") or "30")
    if not str(days_raw).isdigit() or int(days_raw) <= 0:
        await message.answer("❗️ Kun musbat butun son bo'lishi kerak.")
        return

    days = int(days_raw)
    until = grant_premium(user["user_id"], days)
    await state.clear()
    await message.answer(
        "✅ <b>Premium berildi</b>\n\n"
        f"👤 {user['full_name'] or user['username'] or user['user_id']}\n"
        f"🆔 <code>{user['user_id']}</code>\n"
        f"📅 {days} kun (gacha: {format_ts(until)})",
        reply_markup=admin_menu_keyboard(),
    )
    try:
        await message.bot.send_message(
            user["user_id"],
            "🎉 <b>Sizga premium berildi!</b>\n\n"
            f"🌟 Muddat: {days} kun\n"
            f"📅 Amal qiladi: {format_ts(until)} gacha",
        )
    except Exception:
        pass


@router.callback_query(F.data == CB_ADM_PREM_REVOKE)
async def cb_prem_revoke(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_premium_revoke)
    await callback.message.answer(
        "🚫 <b>Premiumni bekor qilish</b>\n\n"
        "Foydalanuvchi ID yoki @username yozing.\n⛔ Bekor qilish: /cancel",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_premium_revoke, F.text)
async def receive_prem_revoke(message: Message, state: FSMContext):
    user = find_user(message.text.strip())
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi. Qayta urinib ko'ring yoki /cancel.")
        return
    revoke_premium(user["user_id"])
    await state.clear()
    await message.answer(
        f"✅ <code>{user['user_id']}</code> foydalanuvchining premiumi bekor qilindi.",
        reply_markup=admin_menu_keyboard(),
    )


# ===========================================================================
# 👑 Adminlar (bir nechta admin: qo'shish / o'chirish)
# ===========================================================================

async def _show_admins(target):
    can_manage = is_owner(target.from_user.id)
    rows = []
    for owner_id in OWNER_IDS:
        u = get_user(owner_id)
        rows.append({
            "user_id": owner_id,
            "username": u["username"] if u else None,
            "full_name": u["full_name"] if u else None,
        })
    for r in list_db_admins():
        if r["user_id"] not in OWNER_IDS:
            rows.append({
                "user_id": r["user_id"],
                "username": r["username"],
                "full_name": r["full_name"],
            })

    text = (
        "👑 <b>Adminlar</b>\n\n"
        f"Jami: <b>{len(rows)}</b> ta\n\n"
        "👑 — ega (.env orqali, o'chirilmaydi)\n"
        "🧰 — qo'shimcha admin\n\n"
    )
    if not can_manage:
        text += "ℹ️ Admin qo'shish/o'chirishni faqat egalar bajara oladi."
    await emit(target, text, reply_markup=admins_keyboard(rows, OWNER_IDS, can_manage))


@router.message(F.text == ADM_BTN_ADMINS)
async def btn_admins(message: Message, state: FSMContext):
    await state.clear()
    await _show_admins(message)


@router.callback_query(F.data == CB_ADM_ADMINS)
async def cb_admins(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await _show_admins(callback)
    await callback.answer()


@router.callback_query(F.data == CB_ADM_ADMIN_ADD)
async def cb_admin_add(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        await callback.answer("⛔ Faqat egalar admin qo'sha oladi.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_admin_id)
    await callback.message.answer(
        "➕ <b>Admin qo'shish</b>\n\n"
        "Yangi adminning <b>Telegram ID</b> raqamini yoki <b>@username</b> ini yuboring.\n"
        "ID ni @userinfobot orqali bilish mumkin.\n\n"
        "⛔ Bekor qilish: /cancel",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_admin_id, F.text)
async def receive_admin_id(message: Message, state: FSMContext):
    raw = message.text.strip().lstrip("@")
    user = find_user(raw)
    if user:
        new_id, name = user["user_id"], (user["full_name"] or user["username"] or str(user["user_id"]))
    elif raw.isdigit():
        new_id, name = int(raw), raw
    else:
        await message.answer(
            "❌ Foydalanuvchi topilmadi. Raqamli ID yuboring yoki u avval botga "
            "/start bersin.\n⛔ Bekor qilish: /cancel"
        )
        return

    await state.clear()
    if new_id in OWNER_IDS:
        await message.answer("ℹ️ Bu foydalanuvchi allaqachon ega.",
                             reply_markup=admin_menu_keyboard())
    elif add_admin(new_id, added_by=message.from_user.id):
        await message.answer(f"✅ <b>{name}</b> admin qilib tayinlandi.",
                             reply_markup=admin_menu_keyboard())
        try:
            await message.bot.send_message(
                new_id,
                "👑 <b>Sizga admin huquqi berildi!</b>\n\n"
                "Panelni ochish uchun /admin buyrug'ini yuboring.",
            )
        except Exception:
            pass
    else:
        await message.answer("ℹ️ Bu foydalanuvchi allaqachon admin.",
                             reply_markup=admin_menu_keyboard())
    await _show_admins(message)


@router.callback_query(F.data.startswith(CB_ADM_ADMIN_DEL))
async def cb_admin_del(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("⛔ Faqat egalar adminni o'chira oladi.", show_alert=True)
        return
    target_id = int(callback.data.rsplit(":", 1)[1])
    if target_id in OWNER_IDS:
        await callback.answer("⛔ Egani o'chirib bo'lmaydi.", show_alert=True)
        return
    remove_admin(target_id)
    await callback.answer("🗑 Admin o'chirildi.")
    await _show_admins(callback)


# ===========================================================================
# 💬 Support
# ===========================================================================

@router.message(F.text == ADM_BTN_TICKETS)
async def btn_support(message: Message, state: FSMContext):
    await state.clear()
    conversations = list_open_conversations()
    if not conversations:
        await message.answer("📮 Hozircha ochiq murojatlar yo'q.",
                             reply_markup=admin_menu_keyboard())
        return
    await message.answer(
        f"📮 <b>Ochiq murojatlar</b> ({len(conversations)}):\n\n"
        "Murojatni ochish uchun bosing:",
        reply_markup=admin_support_list_keyboard(conversations),
    )


# ===========================================================================
# 🪙 To'lovlar
# ===========================================================================

@router.message(F.text == ADM_BTN_PAYMENTS)
async def btn_payments(message: Message, state: FSMContext):
    await state.clear()
    payments = list_pending_payments()
    if not payments:
        await message.answer("🪙 Hozircha kutilayotgan to'lovlar yo'q.",
                             reply_markup=admin_menu_keyboard())
        return
    await message.answer(
        f"🪙 <b>Kutilayotgan to'lovlar</b> ({len(payments)}):\n\nKo'rish uchun bosing:",
        reply_markup=admin_payments_keyboard(payments),
    )


@router.callback_query(F.data.startswith(CB_ADM_PAY_VIEW))
async def cb_payment_view(callback: CallbackQuery):
    payment_id = int(callback.data.rsplit(":", 1)[1])
    p = get_payment(payment_id)
    if not p:
        await callback.answer("To'lov topilmadi.", show_alert=True)
        return
    user = get_user(p["user_id"])
    name = (user["full_name"] or user["username"]) if user else str(p["user_id"])
    uname = f"@{user['username']}" if user and user["username"] else "—"
    proof = p["proof"] or ""
    text = (
        f"🪙 <b>To'lov #{p['id']}</b>\n\n"
        f"👤 {name} ({uname})\n"
        f"🆔 <code>{p['user_id']}</code>\n"
        f"💵 {p['amount']}\n"
        f"📜 {format_ts(p['created_at'])}\n"
        f"📌 Holat: <b>{p['status']}</b>"
    )
    kb = admin_payment_action_keyboard(payment_id) if p["status"] == "PENDING" else None
    if proof.startswith("file_id:"):
        await callback.message.answer_photo(
            proof.split("file_id:", 1)[1],
            caption=text + "\n\n📎 To'lov cheki",
            reply_markup=kb,
        )
    else:
        await callback.message.answer(
            text + f"\n\n📎 <b>Tasdiq:</b> {proof or '—'}", reply_markup=kb
        )
    await callback.answer()


async def _finish_payment(callback: CallbackQuery, done_text: str):
    """Xabarni (matn yoki rasm bo'lishidan qat'i nazar) yakuniy holatga o'tkazadi."""
    from aiogram.exceptions import TelegramBadRequest

    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=done_text)
        else:
            await callback.message.edit_text(done_text)
    except TelegramBadRequest:
        await callback.message.answer(done_text)


@router.callback_query(F.data.startswith(CB_ADM_PAY_APPROVE))
async def cb_payment_approve(callback: CallbackQuery):
    payment_id = int(callback.data.rsplit(":", 1)[1])
    p = get_payment(payment_id)
    if not p:
        await callback.answer("To'lov topilmadi.", show_alert=True)
        return
    if p["status"] != "PENDING":
        await callback.answer(
            f"Bu to'lov allaqachon ko'rib chiqilgan ({p['status']}).", show_alert=True
        )
        return

    raw_days = get_setting("premium_days", "30") or "30"
    days = int(raw_days) if str(raw_days).isdigit() else 30
    until = grant_premium(p["user_id"], days)
    set_payment_status(payment_id, "APPROVED")

    try:
        await callback.bot.send_message(
            p["user_id"],
            "🎉 <b>Premium aktiv!</b>\n\n"
            f"✅ #{payment_id} to'lov tasdiqlandi.\n"
            f"🌟 Premium {days} kunga berildi.\n"
            f"📅 Amal qiladi: {format_ts(until)} gacha\n\n"
            "Barcha imtiyozlardan zavqlaning!",
        )
    except Exception as e:
        logger.warning("Premium xabari yuborilmadi (%s): %s", p["user_id"], e)

    await _finish_payment(
        callback, f"✅ #{payment_id} to'lov tasdiqlandi. Premium {days} kunga berildi."
    )
    await callback.answer("✅ Tasdiqlandi")


@router.callback_query(F.data.startswith(CB_ADM_PAY_REJECT))
async def cb_payment_reject(callback: CallbackQuery):
    payment_id = int(callback.data.rsplit(":", 1)[1])
    p = get_payment(payment_id)
    if not p:
        await callback.answer("To'lov topilmadi.", show_alert=True)
        return
    if p["status"] != "PENDING":
        await callback.answer(
            f"Bu to'lov allaqachon ko'rib chiqilgan ({p['status']}).", show_alert=True
        )
        return
    set_payment_status(payment_id, "REJECTED")
    try:
        await callback.bot.send_message(
            p["user_id"],
            "❌ <b>To'lov rad etildi</b>\n\n"
            f"#{payment_id} to'lov tekshiruvdan o'tmadi.\n"
            "Savollar bo'lsa, «💬 Support» orqali bog'laning.",
        )
    except Exception as e:
        logger.warning("Rad etish xabari yuborilmadi (%s): %s", p["user_id"], e)

    await _finish_payment(callback, f"❌ #{payment_id} to'lov rad etildi.")
    await callback.answer("❌ Rad etildi")


# ===========================================================================
# 📣 Broadcast (segmentlar bilan)
# ===========================================================================

@router.message(F.text == ADM_BTN_BROADCAST)
async def btn_broadcast(message: Message, state: FSMContext):
    await state.clear()
    counts = {
        "all": count_segment("all"),
        "premium": count_segment("premium"),
        "free": count_segment("free"),
    }
    await message.answer(
        "📣 <b>Xabar yuborish</b>\n\nKimga yuboriladi?",
        reply_markup=broadcast_segment_keyboard(counts),
    )


@router.callback_query(F.data.startswith(CB_ADM_BC_SEG))
async def cb_broadcast_segment(callback: CallbackQuery, state: FSMContext):
    segment = callback.data.rsplit(":", 1)[1]
    if segment not in SEGMENT_LABELS:
        await callback.answer("Noto'g'ri segment.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_broadcast_text)
    await state.update_data(bc_segment=segment)
    await callback.message.answer(
        f"📨 <b>{SEGMENT_LABELS[segment]}</b> ({count_segment(segment)} ta foydalanuvchi)\n\n"
        "Yuboriladigan matnni yozing. HTML formatlash ishlaydi.\n\n⛔ Bekor qilish: /cancel",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_broadcast_text, F.text)
async def receive_broadcast_text(message: Message, state: FSMContext):
    data = await state.get_data()
    segment = data.get("bc_segment", "all")
    body = message.html_text or message.text
    await state.update_data(broadcast_text=body)
    await state.set_state(AdminStates.waiting_broadcast_confirm)
    line = "─" * 20
    await message.answer(
        f"📨 <b>{SEGMENT_LABELS.get(segment, segment)}</b> — "
        f"{count_segment(segment)} ta foydalanuvchiga quyidagi matn yuboriladi:\n\n"
        f"{line}\n{body}\n{line}\n\nTasdiqlaysizmi?",
        reply_markup=confirm_broadcast_keyboard(),
    )


@router.message(AdminStates.waiting_broadcast_confirm, F.text == "✅ Yuborish")
async def confirm_broadcast_send(message: Message, state: FSMContext):
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    segment = data.get("bc_segment", "all")
    await state.clear()
    if not text.strip():
        await message.answer("⚠️ Matn bo'sh.", reply_markup=admin_menu_keyboard())
        return
    await message.answer("🚀 Yuborish boshlandi...", reply_markup=admin_menu_keyboard())
    asyncio.create_task(_send_broadcast(message.bot, message, text, segment))


@router.message(AdminStates.waiting_broadcast_confirm, F.text)
async def cancel_broadcast_confirm(message: Message, state: FSMContext):
    if message.text == ADM_BTN_CANCEL:
        await state.clear()
        await message.answer("🚫 Bekor qilindi.", reply_markup=admin_menu_keyboard())
        return
    await message.answer("❗️ «✅ Yuborish» tugmasini bosing yoki bekor qiling.")


async def _send_broadcast(bot: Bot, message: Message, text: str, segment: str) -> None:
    """Broadcast fon vazifasida yuboriladi — panel bloklanmaydi."""
    user_ids = get_user_ids_by_segment(segment)
    sent, failed, blocked = 0, 0, 0
    for user_id in user_ids:
        try:
            await bot.send_message(chat_id=user_id, text=text)
            sent += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(chat_id=user_id, text=text)
                sent += 1
            except Exception:
                failed += 1
        except TelegramForbiddenError:
            blocked += 1
        except Exception as e:
            logger.warning("Broadcast xatosi (user %s): %s", user_id, e)
            failed += 1
        await asyncio.sleep(0.05)

    await message.answer(
        "📣 <b>Broadcast yakunlandi</b>\n\n"
        f"🎯 Segment: {SEGMENT_LABELS.get(segment, segment)}\n"
        f"✅ Yuborildi: <b>{sent}</b>\n"
        f"🚫 Bloklagan: <b>{blocked}</b>\n"
        f"❌ Xatolik: <b>{failed}</b>",
        reply_markup=admin_menu_keyboard(),
    )


# ===========================================================================
# 📝 Premium posti (matn) — admin o'zi tahrirlaydi
# ===========================================================================

PREMIUM_TEXT_HELP = (
    "📝 <b>Premium posti</b>\n\n"
    "Foydalanuvchi «🌟 Premium bo'lish» tugmasini bosganda ko'radigan matnni yozing.\n"
    "HTML formatlash ishlaydi: <code>&lt;b&gt;qalin&lt;/b&gt;</code>, "
    "<code>&lt;i&gt;kursiv&lt;/i&gt;</code>\n\n"
    "<b>O'rinbosarlar:</b>\n"
    "<code>{price}</code> — narx\n"
    "<code>{days}</code> — muddat (kun)\n\n"
    "Standart matnni qaytarish uchun <code>-</code> yuboring.\n"
    "⛔ Bekor qilish: /cancel"
)


@router.callback_query(F.data == CB_ADM_PREMIUM_TEXT)
async def cb_premium_text(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_premium_text)
    current = get_setting("premium_text", "")
    extra = f"\n\n<b>Joriy matn:</b>\n{current}" if current else "\n\n<i>Hozir standart matn ishlatilmoqda.</i>"
    await callback.message.answer(PREMIUM_TEXT_HELP + extra, reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminStates.waiting_premium_text, F.text)
async def receive_premium_text(message: Message, state: FSMContext):
    from handlers.browse import build_premium_text

    await state.clear()
    value = (message.html_text or message.text).strip()
    if value == "-":
        set_setting("premium_text", "")
        await message.answer("✅ Standart premium matni qaytarildi.",
                             reply_markup=admin_menu_keyboard())
    else:
        set_setting("premium_text", value)
        await message.answer("✅ Premium posti yangilandi.",
                             reply_markup=admin_menu_keyboard())
    await message.answer("👁 <b>Ko'rinishi:</b>\n\n" + build_premium_text())


# ===========================================================================
# 📝 Start posti (matn) — admin o'zi tahrirlaydi
# ===========================================================================

START_TEXT_HELP = (
    "📝 <b>Start posti</b>\n\n"
    "Foydalanuvchi botni <code>/start</code> qilganda (va allaqachon barcha "
    "majburiy kanallarga obuna bo'lgan bo'lsa) ko'radigan matnni yozing.\n"
    "HTML formatlash ishlaydi: <code>&lt;b&gt;qalin&lt;/b&gt;</code>, "
    "<code>&lt;i&gt;kursiv&lt;/i&gt;</code>, <code>&lt;a href=\"...\"&gt;havola&lt;/a&gt;</code>\n\n"
    "Standart matnni qaytarish uchun <code>-</code> yuboring.\n"
    "⛔ Bekor qilish: /cancel"
)


@router.message(F.text == ADM_BTN_START_TEXT)
async def btn_start_text(message: Message, state: FSMContext):
    from handlers.start import build_start_text

    await state.set_state(AdminStates.waiting_start_text)
    current = get_setting("start_text", "")
    extra = f"\n\n<b>Joriy matn:</b>\n{current}" if current else "\n\n<i>Hozir standart matn ishlatilmoqda.</i>"
    await message.answer(START_TEXT_HELP + extra, reply_markup=cancel_keyboard())
    await message.answer("👁 <b>Ko'rinishi:</b>\n\n" + build_start_text())


@router.message(AdminStates.waiting_start_text, F.text)
async def receive_start_text(message: Message, state: FSMContext):
    from handlers.start import build_start_text

    await state.clear()
    value = (message.html_text or message.text).strip()
    if value == "-":
        set_setting("start_text", "")
        await message.answer("✅ Standart start matni qaytarildi.",
                             reply_markup=admin_menu_keyboard())
    else:
        set_setting("start_text", value)
        await message.answer("✅ Start posti yangilandi.",
                             reply_markup=admin_menu_keyboard())
    await message.answer("👁 <b>Ko'rinishi:</b>\n\n" + build_start_text())


# ===========================================================================
# 📝 Majburiy obuna posti sarlavhasi — admin o'zi tahrirlaydi
# ===========================================================================

SUBSCRIBE_TEXT_HELP = (
    "📝 <b>Majburiy obuna posti</b>\n\n"
    "Foydalanuvchi hali barcha majburiy kanallarga obuna bo'lmagan bo'lsa "
    "ko'radigan matn (sarlavha). Kanallar ro'yxati va tugmalar matn ostida "
    "avtomatik chiqadi — ularni bu matnga qo'shishning hojati yo'q.\n"
    "HTML formatlash ishlaydi: <code>&lt;b&gt;qalin&lt;/b&gt;</code>\n\n"
    "Standart matnni qaytarish uchun <code>-</code> yuboring.\n"
    "⛔ Bekor qilish: /cancel"
)


@router.message(F.text == ADM_BTN_SUBSCRIBE_TEXT)
async def btn_subscribe_text(message: Message, state: FSMContext):
    from handlers.start import build_subscribe_text

    await state.set_state(AdminStates.waiting_subscribe_text)
    current = get_setting("subscribe_text", "")
    extra = f"\n\n<b>Joriy matn:</b>\n{current}" if current else "\n\n<i>Hozir standart matn ishlatilmoqda.</i>"
    await message.answer(SUBSCRIBE_TEXT_HELP + extra, reply_markup=cancel_keyboard())
    await message.answer("👁 <b>Ko'rinishi:</b>\n\n" + build_subscribe_text())


@router.message(AdminStates.waiting_subscribe_text, F.text)
async def receive_subscribe_text(message: Message, state: FSMContext):
    from handlers.start import build_subscribe_text

    await state.clear()
    value = (message.html_text or message.text).strip()
    if value == "-":
        set_setting("subscribe_text", "")
        await message.answer("✅ Standart majburiy obuna matni qaytarildi.",
                             reply_markup=admin_menu_keyboard())
    else:
        set_setting("subscribe_text", value)
        await message.answer("✅ Majburiy obuna posti yangilandi.",
                             reply_markup=admin_menu_keyboard())
    await message.answer("👁 <b>Ko'rinishi:</b>\n\n" + build_subscribe_text())


# ===========================================================================
# 📝 Premium tugmasi matni — admin o'zi tahrirlaydi
# ===========================================================================

VIP_BUTTON_HELP = (
    "📝 <b>Premium tugmasi matni</b>\n\n"
    "Majburiy obuna postida eng yuqorida chiqadigan Premium tugmasining matnini "
    "yozing (masalan: <code>🌟 Yoki premium sotib oling</code>).\n\n"
    "Standart matnni qaytarish uchun <code>-</code> yuboring.\n"
    "⛔ Bekor qilish: /cancel"
)


@router.message(F.text == ADM_BTN_VIP_BUTTON)
async def btn_vip_button_text(message: Message, state: FSMContext):
    await state.set_state(AdminStates.waiting_vip_button_text)
    current = get_setting("vip_button_text", "")
    extra = (
        f"\n\n<b>Joriy matn:</b> {current}" if current
        else "\n\n<i>Hozir standart matn ishlatilmoqda: 🌟 Yoki premium sotib oling</i>"
    )
    await message.answer(VIP_BUTTON_HELP + extra, reply_markup=cancel_keyboard())


@router.message(AdminStates.waiting_vip_button_text, F.text)
async def receive_vip_button_text(message: Message, state: FSMContext):
    await state.clear()
    value = (message.text or "").strip()
    if value == "-":
        set_setting("vip_button_text", "")
        await message.answer("✅ Standart Premium tugma matni qaytarildi.",
                             reply_markup=admin_menu_keyboard())
    else:
        set_setting("vip_button_text", value)
        await message.answer(f"✅ Premium tugma matni yangilandi: {value}",
                             reply_markup=admin_menu_keyboard())


# ===========================================================================
# 📝 Kanal tugmasi matni — admin o'zi tahrirlaydi
# ===========================================================================

CHANNEL_BUTTON_HELP = (
    "📝 <b>Kanal tugmasi matni</b>\n\n"
    "Majburiy obuna postida har bir kanalga o'tadigan tugmaning matnini "
    "yozing (masalan: <code>📡 Obuna bo'lish</code>). Bir nechta kanal "
    "bo'lsa, har biriga avtomatik raqam qo'shiladi (masalan «📡 Obuna "
    "bo'lish 1», «📡 Obuna bo'lish 2»).\n\n"
    "Standart matnni qaytarish uchun <code>-</code> yuboring.\n"
    "⛔ Bekor qilish: /cancel"
)


@router.message(F.text == ADM_BTN_CHANNEL_BUTTON)
async def btn_channel_button_text(message: Message, state: FSMContext):
    await state.set_state(AdminStates.waiting_channel_button_text)
    current = get_setting("channel_button_text", "")
    extra = f"\n\n<b>Joriy matn:</b> {current}" if current else "\n\n<i>Hozir standart matn ishlatilmoqda: 📡 Obuna bo'lish</i>"
    await message.answer(CHANNEL_BUTTON_HELP + extra, reply_markup=cancel_keyboard())


@router.message(AdminStates.waiting_channel_button_text, F.text)
async def receive_channel_button_text(message: Message, state: FSMContext):
    await state.clear()
    value = (message.text or "").strip()
    if value == "-":
        set_setting("channel_button_text", "")
        await message.answer("✅ Standart kanal tugma matni qaytarildi.",
                             reply_markup=admin_menu_keyboard())
    else:
        set_setting("channel_button_text", value)
        await message.answer(f"✅ Kanal tugma matni yangilandi: {value}",
                             reply_markup=admin_menu_keyboard())


# ===========================================================================
# 📡 Majburiy obuna kanallari
# ===========================================================================

def _channels_text() -> str:
    channels = list_required_channels()
    if not channels:
        return (
            "📡 <b>Majburiy obuna</b>\n\n"
            "Hozircha majburiy kanal yo'q — bot hamma uchun ochiq.\n\n"
            "Kanal qo'shsangiz, foydalanuvchilar unga a'zo bo'lmaguncha botdan "
            "foydalana olmaydi."
        )
    lines = ["📡 <b>Majburiy obuna</b>\n", f"Jami: <b>{len(channels)}</b> ta kanal\n"]
    for ch in channels:
        name = ch["title"] or ch["username"] or str(ch["chat_id"])
        link = ch["username"] or ch["invite_link"] or "—"
        lines.append(f"• <b>{name}</b>\n  <code>{ch['chat_id']}</code> • {link}")
    lines.append("\n🗑 O'chirish uchun kanal ustiga bosing.")
    return "\n".join(lines)


@router.message(F.text == ADM_BTN_CHANNELS)
async def btn_channels(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(_channels_text(),
                         reply_markup=admin_channels_keyboard(list_required_channels()))


@router.callback_query(F.data == CB_ADM_SUB_ADD)
async def cb_channel_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_channel_add)
    await callback.message.answer(
        "➕ <b>Majburiy kanal qo'shish</b>\n\n"
        "Quyidagilardan birini yuboring:\n"
        "• Kanal <b>@username</b> (masalan <code>@mykino</code>)\n"
        "• Kanal <b>ID</b> raqami (masalan <code>-1001234567890</code>)\n"
        "• Yoki shu kanaldagi istalgan xabarni <b>forward</b> qiling\n\n"
        "⚠️ Bot shu kanalda <b>admin</b> bo'lishi shart, aks holda obunani "
        "tekshira olmaydi.\n\n⛔ Bekor qilish: /cancel",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_channel_add)
async def receive_channel(message: Message, state: FSMContext):
    # 1) Forward qilingan xabardan kanalni aniqlash
    target = None
    fwd = getattr(message, "forward_from_chat", None)
    if fwd is not None:
        target = fwd.id
    elif message.text:
        raw = message.text.strip()
        if raw.startswith("/"):
            return
        target = raw if raw.startswith("@") else raw
    if target is None:
        await message.answer("❗️ @username, ID yuboring yoki kanaldan xabar forward qiling.")
        return

    try:
        chat = await message.bot.get_chat(target)
    except Exception as e:
        await message.answer(
            f"❌ Kanal topilmadi yoki botning kirish huquqi yo'q.\n<code>{e}</code>\n\n"
            "Botni kanalga admin qilib qo'shing va qayta urinib ko'ring, yoki /cancel."
        )
        return

    # Bot kanalda admin ekanini tekshiramiz
    try:
        me = await message.bot.get_me()
        member = await message.bot.get_chat_member(chat.id, me.id)
        if member.status not in ("administrator", "creator"):
            await message.answer(
                "⚠️ Bot bu kanalda admin emas. Avval botni kanalga <b>admin</b> qilib "
                "qo'shing, keyin qayta yuboring.\n⛔ Bekor qilish: /cancel"
            )
            return
    except Exception:
        await message.answer(
            "⚠️ Botning kanaldagi holatini tekshirib bo'lmadi. Botni admin qiling.\n"
            "⛔ Bekor qilish: /cancel"
        )
        return

    invite = ""
    try:
        invite = chat.invite_link or ""
        if not invite and not chat.username:
            invite = await message.bot.export_chat_invite_link(chat.id)
    except Exception:
        pass

    await state.clear()
    add_required_channel(
        chat.id, chat.title or "", f"@{chat.username}" if chat.username else "", invite
    )
    await message.answer(
        f"✅ <b>{chat.title}</b> majburiy obuna kanallariga qo'shildi.",
        reply_markup=admin_menu_keyboard(),
    )
    await message.answer(_channels_text(),
                         reply_markup=admin_channels_keyboard(list_required_channels()))


@router.callback_query(F.data.startswith(CB_ADM_SUB_DEL))
async def cb_channel_del(callback: CallbackQuery):
    chat_id = int(callback.data.rsplit(":", 1)[1])
    remove_required_channel(chat_id)
    await callback.answer("🗑 Kanal o'chirildi.")
    await emit(callback, _channels_text(),
               reply_markup=admin_channels_keyboard(list_required_channels()))
