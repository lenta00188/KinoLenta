"""Maxsus filtrlar.

`ADMIN_IDS` statik ro'yxat bo'lgani uchun `F.from_user.id.in_(ADMIN_IDS)` bazaga
qo'shilgan yangi adminlarni ko'rmaydi. Bu filtr har safar dinamik tekshiradi.
"""
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from utils import is_admin_user, is_owner


class IsAdmin(BaseFilter):
    """Foydalanuvchi .env dagi ega yoki bazadagi admin bo'lsa — True."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = getattr(event, "from_user", None)
        return bool(user) and is_admin_user(user.id)


class IsOwner(BaseFilter):
    """Faqat .env dagi ADMIN_IDS (egalar) uchun."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = getattr(event, "from_user", None)
        return bool(user) and is_owner(user.id)
