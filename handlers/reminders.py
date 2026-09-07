from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import add_reminder, get_movie
from handlers.states import UserStates
from keyboards import (
    CB_REM,
    CB_REM_PICK,
    CB_HOME,
    main_menu_keyboard,
    reminder_options_keyboard,
)
from keyboards import movie_card_keyboard
from utils import (
    emit,
    format_ts_human,
    parse_reminder_input,
    reminder_quick_choice,
)

router = Router(name="reminders")


@router.callback_query(F.data.startswith(CB_REM))
async def cb_reminder(callback: CallbackQuery):
    movie_id = int(callback.data.rsplit(":", 1)[1])
    movie = get_movie(movie_id)
    if not movie or not movie["available"]:
        await callback.answer("❌ Bu kino mavjud emas.", show_alert=True)
        return
    await emit(
        callback,
        f"🔔 <b>Eslatma</b>\n\n🍿 {movie['title']}\n\nQachon eslatishimni xohlaysiz?",
        reply_markup=reminder_options_keyboard(movie_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(CB_REM_PICK))
async def cb_reminder_pick(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":", 1)[1]  # <movie_id>:<choice>
    movie_id_raw, choice = parts.rsplit(":", 1)
    movie_id = int(movie_id_raw)
    user_id = callback.from_user.id
    movie = get_movie(movie_id)
    if not movie or not movie["available"]:
        await callback.answer("❌ Bu kino mavjud emas.", show_alert=True)
        return

    if choice == "custom":
        await state.set_state(UserStates.waiting_reminder_time)
        await state.update_data(rem_movie_id=movie_id)
        await emit(
            callback,
            "🗓 <b>Boshqa vaqt</b>\n\n"
            f"🍿 {movie['title']}\n\n"
            "Vaqtni kiriting:\n"
            "• <code>18:30</code> — bugun (o'tgan bo'lsa ertaga)\n"
            "• <code>25.12 14:00</code>\n"
            "• <code>25.12.2026 10:00</code>\n\n"
            "⛔ Bekor qilish: /cancel"
        )
        await callback.answer()
        return

    ts = reminder_quick_choice(choice, movie_id)
    if ts is None:
        await callback.answer("⚠️ Noto'g'ri vaqt.", show_alert=True)
        return

    added = add_reminder(user_id, movie_id, ts)
    if not added:
        await callback.answer("⚠️ Shu film uchun allaqachon faol eslatma bor.", show_alert=True)
        return

    await emit(
        callback,
        "✅ <b>Eslatma o'rnatildi!</b>\n\n"
        f"🍿 Kino: <b>{movie['title']}</b>\n"
        f"📜 Vaqt: {format_ts_human(ts)}\n\n"
        "Belgilangan vaqtda sizga xabar yuboraman.",
        reply_markup=movie_card_keyboard(movie_id, user_id),
    )
    await callback.answer("🔔 Eslatma qo'shildi!")


@router.message(UserStates.waiting_reminder_time, F.text)
async def receive_custom_reminder(message: Message, state: FSMContext):
    data = await state.get_data()
    movie_id = data.get("rem_movie_id")
    if not movie_id:
        await state.clear()
        await message.answer("⚠️ Jarayon uzilib qoldi.", reply_markup=main_menu_keyboard())
        return

    ts = parse_reminder_input(message.text)
    if ts is None:
        await message.answer(
            "❗️ Noto'g'ri format yoki o'tgan vaqt.\n"
            "Masalan: <code>18:30</code> yoki <code>25.12 14:00</code>\n"
            "Bekor qilish uchun /cancel yuboring."
        )
        return

    user_id = message.from_user.id
    added = add_reminder(user_id, movie_id, ts)
    await state.clear()
    if not added:
        await message.answer(
            "⚠️ Shu film uchun allaqachon faol eslatma bor.",
            reply_markup=main_menu_keyboard(),
        )
        return

    movie = get_movie(movie_id)
    await message.answer(
        "✅ <b>Eslatma o'rnatildi!</b>\n\n"
        f"🍿 Kino: <b>{movie['title'] if movie else movie_id}</b>\n"
        f"📜 Vaqt: {format_ts_human(ts)}\n\n"
        "Belgilangan vaqtda sizga xabar yuboraman.",
        reply_markup=main_menu_keyboard(),
    )
