import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import (
    add_support_message,
    close_conversation,
    get_conversation,
    get_conversation_messages,
    get_open_conversation,
    get_or_create_open_conversation,
    get_user,
)
from handlers.states import AdminStates, UserStates
from keyboards import (
    CB_ADM_SUP_CLOSE,
    CB_ADM_SUP_REPLY,
    CB_ADM_SUP_VIEW,
    CB_SUPPORT_CLOSE,
    admin_conversation_keyboard,
    admin_menu_keyboard,
    main_menu_keyboard,
    support_close_keyboard,
    support_notify_keyboard,
)
from utils import emit, format_ts, is_admin_user, notify_admins

router = Router(name="support")
logger = logging.getLogger(__name__)

MAX_HISTORY = 25


# ===========================================================================
# 👤 Foydalanuvchi tomoni
# ===========================================================================

@router.message(UserStates.support_chat, F.text)
async def user_message_to_support(message: Message, state: FSMContext):
    """📮 Operator bilan bog'lanish: xabar bazaga yoziladi va barcha adminlarga yuboriladi.

    Admin xuddi shu suhbat orqali javob yozadi, javob foydalanuvchiga keladi.
    """
    conv = get_open_conversation(message.from_user.id)
    if not conv:
        # Suhbat yopilgan bo'lsa, avtomatik yangisini ochamiz (uzilib qolmasin)
        conv_id = get_or_create_open_conversation(message.from_user.id)
    else:
        conv_id = conv["id"]

    add_support_message(conv_id, message.from_user.id, "user", message.text)
    await message.answer(
        "✅ <b>Xabaringiz adminga yuborildi.</b>\n"
        "Javob shu yerga keladi. Yana yozishingiz mumkin.",
        reply_markup=support_close_keyboard(),
    )

    uname = f"@{message.from_user.username}" if message.from_user.username else "—"
    await notify_admins(
        message.bot,
        f"📮 <b>Yangi murojat</b> (#{conv_id})\n\n"
        f"👤 {message.from_user.full_name or uname}\n"
        f"🔗 {uname}\n"
        f"🆔 <code>{message.from_user.id}</code>\n\n"
        f"{message.text}",
        keyboard=support_notify_keyboard(conv_id),
    )


@router.message(UserStates.support_chat, ~F.text)
async def user_non_text_to_support(message: Message):
    await message.answer(
        "ℹ️ Iltimos, murojatingizni <b>matn</b> ko'rinishida yozing.",
        reply_markup=support_close_keyboard(),
    )


@router.callback_query(F.data == CB_SUPPORT_CLOSE)
async def cb_support_close(callback: CallbackQuery, state: FSMContext):
    conv = get_open_conversation(callback.from_user.id)
    if conv:
        close_conversation(conv["id"])
    await state.clear()
    # XATO TUZATILDI: avval edit_text() ga ReplyKeyboardMarkup berilardi —
    # Telegram buni qabul qilmaydi va handler qulardi.
    await emit(callback, "🔒 Murojat yakunlandi.")
    await callback.message.answer(
        "Yana savolingiz bo'lsa, «📮 Operator bilan bog'lanish» tugmasini bosing.",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


# ===========================================================================
# 🧰 Admin tomoni
# ===========================================================================
# Diqqat: bu handlerlar admin routerida emas, shuning uchun huquq tekshiruvi
# qo'lda bajariladi.

def _deny(callback: CallbackQuery) -> bool:
    return not is_admin_user(callback.from_user.id)


@router.callback_query(F.data.startswith(CB_ADM_SUP_VIEW))
async def cb_adm_sup_view(callback: CallbackQuery, state: FSMContext):
    if _deny(callback):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return

    conv_id = int(callback.data.rsplit(":", 1)[1])
    conv = get_conversation(conv_id)
    if not conv:
        await callback.answer("Suhbat topilmadi.", show_alert=True)
        return

    messages = get_conversation_messages(conv_id, limit=MAX_HISTORY)
    await state.set_state(AdminStates.support_reply)
    await state.update_data(adm_conv_id=conv_id)

    user = get_user(conv["user_id"])
    name = (user["full_name"] or user["username"]) if user else str(conv["user_id"])
    lines = [
        f"📮 <b>Murojat #{conv_id}</b> — {conv['status']}",
        f"👤 {name} • <code>{conv['user_id']}</code>\n",
    ]
    if not messages:
        lines.append("<i>Xabarlar yo'q.</i>")
    for m in reversed(messages):
        # XATO TUZATILDI: created_at — matn sana, format_ts esa unix timestamp
        # kutardi va TypeError bilan qulardi. Endi format_ts ikkalasini ham oladi.
        who = "🧰 Admin" if m["sender_type"] == "admin" else "👤 Foydalanuvchi"
        lines.append(f"{who} • {format_ts(m['created_at'])}\n{m['text']}\n")

    await callback.message.answer(
        "\n".join(lines)[:4000], reply_markup=admin_conversation_keyboard(conv_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith(CB_ADM_SUP_REPLY))
async def cb_adm_sup_reply(callback: CallbackQuery, state: FSMContext):
    if _deny(callback):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    conv_id = int(callback.data.rsplit(":", 1)[1])
    if not get_conversation(conv_id):
        await callback.answer("Suhbat topilmadi.", show_alert=True)
        return
    await state.set_state(AdminStates.support_reply)
    await state.update_data(adm_conv_id=conv_id)
    await callback.message.answer(
        f"✍️ <b>Murojat #{conv_id}</b>\n\nJavobingizni yozing — u to'g'ridan-to'g'ri "
        "foydalanuvchiga boradi.\n⛔ Bekor qilish: /cancel"
    )
    await callback.answer()


@router.callback_query(F.data.startswith(CB_ADM_SUP_CLOSE))
async def cb_adm_sup_close(callback: CallbackQuery, state: FSMContext):
    if _deny(callback):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    conv_id = int(callback.data.rsplit(":", 1)[1])
    conv = get_conversation(conv_id)
    close_conversation(conv_id)
    await state.clear()
    if conv:
        try:
            await callback.bot.send_message(
                conv["user_id"],
                "🔒 Admin murojatni yakunladi. Savol qolsa, «📮 Operator bilan bog'lanish» "
                "orqali qayta yozing.",
                reply_markup=main_menu_keyboard(),
            )
        except Exception:
            pass
    await callback.message.answer(f"✅ Murojat #{conv_id} yopildi.",
                                  reply_markup=admin_menu_keyboard())
    await callback.answer()


@router.message(AdminStates.support_reply, F.text)
async def admin_reply_to_user(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user.id):
        await state.clear()
        return

    data = await state.get_data()
    conv_id = data.get("adm_conv_id")
    conv = get_conversation(conv_id) if conv_id else None
    if not conv:
        await state.clear()
        await message.answer("⚠️ Murojat tanlanmagan yoki topilmadi.",
                             reply_markup=admin_menu_keyboard())
        return

    add_support_message(conv_id, message.from_user.id, "admin", message.text)
    try:
        await message.bot.send_message(
            conv["user_id"],
            f"👤 <b>Admin javobi:</b>\n\n{message.text}\n\n"
            "Savol qolgan bo'lsa, yozishingiz mumkin.",
            reply_markup=support_close_keyboard(),
        )
        await message.answer(
            "✅ Javob yuborildi. Yana yozishingiz mumkin yoki /cancel bilan chiqing."
        )
    except Exception as e:
        logger.warning("Support javobi yuborilmadi (%s): %s", conv["user_id"], e)
        await message.answer("⚠️ Foydalanuvchiga yuborishda xatolik (bot bloklangan?).")
