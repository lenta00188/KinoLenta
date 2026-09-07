from aiogram import Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import get_setting, save_user
from keyboards import CB_CHECK_SUB, main_menu_keyboard

router = Router(name="start")

DEFAULT_WELCOME_TEXT = (
    "🍿 <b>KinoLentaUzBot</b>\n\n"
    "Assalomu alaykum! Kino ko'rish juda oson:\n\n"
    "1️⃣ Kanaldagi kino ostidagi <b>raqamni</b> yuboring\n"
    "2️⃣ Kino haqidagi ma'lumot chiqadi\n"
    "3️⃣ «🍿 FILMNI TOMOSHA QILISH» tugmasini bosing\n\n"
    "Pastdagi tugmalardan ham foydalanishingiz mumkin."
)


def build_start_text() -> str:
    """/start posti (obuna talab qilinmaydigan / allaqachon obuna bo'lgan holat).

    Admin panel → 📝 Start posti orqali admin o'z matnini qo'yishi mumkin.
    Matn qo'yilmagan bo'lsa — standart matn ishlatiladi.
    """
    custom = get_setting("start_text", "")
    return custom if custom else DEFAULT_WELCOME_TEXT


DEFAULT_SUBSCRIBE_TEXT = (
    "📡 <b>Botdan foydalanish uchun quyidagi kanal(lar)ga obuna bo'ling</b>\n\n"
    "A'zo bo'lgach, «✅ Obuna bo'ldim» tugmasini bosing.\n"
    "❗️ Kanallarga obuna bo'lishni istamasangiz, yuqoridagi "
    "«🌟 Yoki premium sotib oling» tugmasi orqali premium sotib olib, "
    "obunasiz botdan to'liq foydalanishingiz mumkin."
)


def build_subscribe_text() -> str:
    """📡 Majburiy obuna posti sarlavhasi (kanal ro'yxati tugmalarda chiqadi).

    Admin panel → 📝 Majburiy obuna matni orqali admin o'z matnini qo'yishi
    mumkin. Matn qo'yilmagan bo'lsa — standart matn ishlatiladi.
    """
    custom = get_setting("subscribe_text", "")
    return custom if custom else DEFAULT_SUBSCRIBE_TEXT


HELP_TEXT = (
    "❓ <b>Yordam</b>\n\n"
    "🔢 <b>Raqam orqali</b> — kino raqamini yuboring (masalan: <code>26</code>)\n"
    "✨ <b>Yangi qo'shilganlar</b> — eng so'nggi qo'shilganlar\n"
    "🌟 <b>Premium filmlar</b> — faqat Premium foydalanuvchilar uchun\n"
    "🧩 <b>Janrlar</b> — janr bo'yicha saralash\n"
    "📌 <b>Tanlovlarim</b> — saqlangan filmlar\n"
    "🧡 <b>Sevimlilar</b> — sevimli filmlar\n"
    "📜 <b>Tomosha tarixi</b> — ko'rgan filmlar\n"
    "🔔 <b>Eslatmalar</b> — kino eslatmalari\n"
    "🎯 <b>Kutilmagan tanlov</b> — kun tanlovi\n"
    "🪪 <b>Profilim</b> — shaxsiy statistika\n"
    "🌟 <b>Premium bo'lish</b> — cheksiz kino va imtiyozlar\n"
    "📮 <b>Operator bilan bog'lanish</b> — savol, taklif, kino so'rash\n\n"
    "⛔ Har qanday bosqichda /cancel — bekor qilish."
)


@router.message(CommandStart(), StateFilter("*"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    save_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    await message.answer(build_start_text(), reply_markup=main_menu_keyboard())


@router.message(Command("help"), StateFilter("*"))
async def cmd_help(message: Message, state: FSMContext):
    save_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    await message.answer(HELP_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext):
    """XATO TUZATILDI: avval /cancel faqat admin routerida bor edi, shuning uchun
    oddiy foydalanuvchilar eslatma/to'lov/support holatlarida qotib qolardi."""
    await state.clear()
    await message.answer("🚫 Bekor qilindi.", reply_markup=main_menu_keyboard())


@router.message(Command("id"), StateFilter("*"))
async def cmd_id(message: Message):
    await message.answer(f"🆔 Sizning ID: <code>{message.from_user.id}</code>")


# ===========================================================================
# 📡 «✅ Obuna bo'ldim» tekshiruvi
# ===========================================================================

@router.callback_query(F.data == CB_CHECK_SUB)
async def cb_check_subscription(callback: CallbackQuery, state: FSMContext):
    from middlewares import mark_subscribed, missing_subscriptions

    missing = await missing_subscriptions(callback.bot, callback.from_user.id)
    if missing:
        await callback.answer(
            "❌ Hali barcha kanallarga obuna bo'lmagansiz.\n"
            "Obuna bo'lib, qaytadan tekshiring.",
            show_alert=True,
        )
        return

    mark_subscribed(callback.from_user.id)
    await state.clear()
    save_user(callback.from_user.id, callback.from_user.username,
              callback.from_user.full_name)
    await callback.answer("✅ Rahmat! Botdan foydalanishingiz mumkin.")
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(build_start_text(), reply_markup=main_menu_keyboard())
