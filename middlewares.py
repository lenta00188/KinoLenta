"""Majburiy obuna tekshiruvi.

Foydalanuvchi admin belgilagan barcha kanallarga obuna bo'lmaguncha bot bilan
ishlay olmaydi. Tekshiruv outer-middleware sifatida ishlaydi, shuning uchun
hech bir handler chetlab o'tilmaydi.

Adminlar, `✅ Obuna bo'ldim` tugmasi va kanal postlari tekshiruvdan ozod.
"""
import logging
import time

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from database import is_premium, list_required_channels, save_user
from keyboards import BTN_PREMIUM, CB_CHECK_SUB, CB_PAY_DONE, CB_PAY_START, CB_PREMIUM, subscription_keyboard
from utils import is_admin_user

logger = logging.getLogger(__name__)

SUBSCRIBED_STATUSES = {"member", "administrator", "creator"}

# 🌟 Premium sotib olish yo'lidagi barcha qadamlar majburiy obunadan ozod:
# foydalanuvchi kanallarga a'zo bo'lmasdan ham premiumni to'liq sotib ololishi kerak.
# - CB_PREMIUM / BTN_PREMIUM — "Premium olish" tugmasi (inline va reply-klaviatura)
# - CB_PAY_START — "To'lov qilish" tugmasi (to'lov ma'lumotlarini ko'rsatish)
# - CB_PAY_DONE  — "✅ Men to'ladim" tugmasi (chek yuborishni so'rash)
PREMIUM_FLOW_CALLBACKS = {CB_CHECK_SUB, CB_PREMIUM, CB_PAY_START, CB_PAY_DONE}

# Telegram'ga har bir xabarda so'rov yubormaslik uchun qisqa muddatli kesh.
_CACHE: dict[int, float] = {}
CACHE_TTL = 120  # soniya


async def missing_subscriptions(bot, user_id: int) -> list:
    """Foydalanuvchi obuna bo'lmagan kanallar ro'yxati."""
    channels = list_required_channels()
    if not channels:
        return []

    missing = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch["chat_id"], user_id)
            if member.status not in SUBSCRIBED_STATUSES:
                missing.append(ch)
        except Exception as e:
            # Bot kanalda admin emas yoki kanal o'chirilgan — foydalanuvchini
            # bloklamaymiz, faqat log qoldiramiz.
            logger.warning("Obuna tekshirib bo'lmadi (%s): %s", ch["chat_id"], e)
    return missing


def clear_cache(user_id: int) -> None:
    _CACHE.pop(user_id, None)


def mark_subscribed(user_id: int) -> None:
    """Tekshiruv muvaffaqiyatli o'tgach keshni yangilaydi."""
    _CACHE[user_id] = time.time() + CACHE_TTL


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        bot = data.get("bot")
        if not user or not bot:
            return await handler(event, data)

        # Adminlar tekshiruvdan ozod
        if is_admin_user(user.id):
            return await handler(event, data)

        # 🌟 Premium (premium) foydalanuvchilar majburiy obunadan butunlay ozod
        if is_premium(user.id):
            return await handler(event, data)

        # "✅ Obuna bo'ldim" va butun premium sotib olish yo'li (Premium olish ->
        # to'lov qilish -> men to'ladim) har doim o'tadi — bular aynan
        # kanallarga obuna bo'lmaganlar uchun chiqish yo'li, shuning uchun
        # ularni bloklab bo'lmaydi.
        if isinstance(event, CallbackQuery) and event.data in PREMIUM_FLOW_CALLBACKS:
            return await handler(event, data)

        # Reply-klaviaturadagi "🌟 Premium bo'lish" tugmasi ham xuddi shunday ozod
        # (ba'zi foydalanuvchilarda eski asosiy menyu klaviaturasi ochiq qolgan
        # bo'lishi mumkin — ular ham premiumni to'sqinliksiz sotib ola olishi kerak).
        if isinstance(event, Message) and event.text == BTN_PREMIUM:
            return await handler(event, data)

        # To'lov chekini/ID sini yuborish bosqichi (waiting_payment_proof) —
        # foydalanuvchi hali obuna/premium emas, lekin aynan shu holatda u
        # premium sotib olish jarayonini yakunlamoqda, shuning uchun bu
        # bosqichdagi har qanday xabar (rasm, matn, /cancel) ham o'tadi.
        state = data.get("state")
        if state is not None:
            from handlers.states import UserStates

            current_state = await state.get_state()
            if current_state == UserStates.waiting_payment_proof.state:
                return await handler(event, data)

        # Kesh: yaqinda tekshirilgan bo'lsa qayta so'rov yubormaymiz
        cached = _CACHE.get(user.id, 0)
        if cached > time.time():
            return await handler(event, data)

        missing = await missing_subscriptions(bot, user.id)
        if not missing:
            _CACHE[user.id] = time.time() + CACHE_TTL
            return await handler(event, data)

        save_user(user.id, user.username, user.full_name)
        from handlers.start import build_subscribe_text

        text = build_subscribe_text()
        kb = subscription_keyboard(missing)
        try:
            if isinstance(event, CallbackQuery):
                await event.answer("📡 Avval kanallarga obuna bo'ling.", show_alert=True)
                await event.message.answer(text, reply_markup=kb)
            elif isinstance(event, Message):
                await event.answer(text, reply_markup=kb)
        except Exception as e:
            logger.warning("Obuna xabari yuborilmadi: %s", e)
        return None  # handler chaqirilmaydi
