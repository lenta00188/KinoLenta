from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import add_payment, get_premium_until, get_setting, is_premium
from handlers.states import UserStates
from keyboards import (
    CB_PAY_DONE,
    CB_PAY_START,
    main_menu_keyboard,
    pay_done_keyboard,
    payment_notify_keyboard,
    user_cancel_keyboard,
)
from utils import emit, format_ts, notify_admins, notify_admins_photo

router = Router(name="premium")


@router.callback_query(F.data == CB_PAY_START)
async def cb_pay_start(callback: CallbackQuery):
    if is_premium(callback.from_user.id):
        until = get_premium_until(callback.from_user.id)
        await callback.answer(
            f"🌟 Siz allaqachon premium obunachisiz!\n📅 {format_ts(until)} gacha",
            show_alert=True,
        )
        return

    price = get_setting("premium_price", "15 000 so'm")
    days = get_setting("premium_days", "30")
    payment_info = get_setting(
        "payment_info", "Karta: 8600 0000 0000 0000\nQabul qiluvchi: Admin"
    )
    obtained = get_setting("payment_note", "")
    await emit(
        callback,
        "🧾 <b>Premium to'lov</b>\n\n"
        f"🪙 Narx: <b>{price}</b>\n"
        f"📅 Muddat: <b>{days} kun</b>\n\n"
        f"📲 <b>To'lov ma'lumotlari:</b>\n<code>{payment_info}</code>\n\n"
        + (f"{obtained}\n\n" if obtained else "")
        + "To'lovni amalga oshirgach «✅ Men to'ladim» tugmasini bosing.",
        reply_markup=pay_done_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == CB_PAY_DONE)
async def cb_pay_done(callback: CallbackQuery, state: FSMContext):
    if is_premium(callback.from_user.id):
        await callback.answer("🌟 Siz allaqachon premium obunachisiz!", show_alert=True)
        return
    await state.set_state(UserStates.waiting_payment_proof)
    await emit(
        callback,
        "📸 <b>To'lov tasdig'i</b>\n\n"
        "To'lov chekining <b>skrinshotini</b> yoki tranzaksiya ID sini yuboring.\n"
        "Operator tasdiqlagandan so'ng premium avtomatik aktiv bo'ladi.\n\n"
        "⛔ Bekor qilish: /cancel",
        reply_markup=user_cancel_keyboard(),
    )
    await callback.answer()


@router.message(UserStates.waiting_payment_proof, F.photo)
async def receive_payment_proof_photo(message: Message, state: FSMContext):
    await _submit_payment(
        message, state, proof=f"file_id:{message.photo[-1].file_id}", photo=True
    )


@router.message(UserStates.waiting_payment_proof, F.text)
async def receive_payment_proof_text(message: Message, state: FSMContext):
    text = message.text.strip()
    if len(text) < 3:
        await message.answer("❗️ Juda qisqa. Chek skrinshotini yoki tranzaksiya ID sini yuboring.")
        return
    await _submit_payment(message, state, proof=text[:500], photo=False)


@router.message(UserStates.waiting_payment_proof)
async def wrong_payment_proof(message: Message):
    await message.answer(
        "❗️ Iltimos, chek <b>rasmini</b> yoki tranzaksiya <b>ID sini</b> yuboring.\n"
        "⛔ Bekor qilish: /cancel"
    )


async def _submit_payment(message: Message, state: FSMContext, proof: str, photo: bool):
    user_id = message.from_user.id
    amount = get_setting("premium_price", "15 000 so'm")
    payment_id = add_payment(user_id, amount, proof)
    await state.clear()

    await message.answer(
        "✅ <b>To'lov qabul qilindi!</b>\n\n"
        f"🧾 Chek raqami: #{payment_id}\n"
        f"🪙 Summa: {amount}\n\n"
        "Operator tekshiruvidan so'ng premium obunangiz aktiv bo'ladi. "
        "Odatda 24 soat ichida.",
        reply_markup=main_menu_keyboard(),
    )

    uname = f"@{message.from_user.username}" if message.from_user.username else "—"
    caption = (
        "🪙 <b>Yangi to'lov</b>\n\n"
        f"🧾 #{payment_id}\n"
        f"👤 {message.from_user.full_name or uname}\n"
        f"🔗 {uname}\n"
        f"🆔 <code>{user_id}</code>\n"
        f"💵 {amount}"
    )
    kb = payment_notify_keyboard(payment_id)

    # YANGI: admin xabarga to'g'ridan-to'g'ri tasdiqlash/rad etish tugmalari qo'shildi
    # va chek rasmi adminlarga rasm sifatida yuboriladi (avval faqat file_id matni edi).
    if photo:
        await notify_admins_photo(
            message.bot, proof.split("file_id:", 1)[1], caption, keyboard=kb
        )
    else:
        await notify_admins(message.bot, caption + f"\n\n📎 {proof}", keyboard=kb)
