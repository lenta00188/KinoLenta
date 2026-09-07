#!/usr/bin/env python3
"""Kino kanalidagi MAVJUD (eski) postlarni bazaga yuklash.

Nima uchun kerak: Telegram Bot API'da kanal postlari tarixini o'qish imkoni
yo'q (get_chat_history mavjud emas). Bot kanalga qo'shilishidan oldin qo'yilgan
postlar avtomatik indekslanmaydi. Bu skript har bir message_id ni forward qilib
borib, mavjud postlarni topadi va ularni movies jadvaliga yozadi.

Ishga tushirish:
    python backfill.py                # 1-id dan boshlab, hammasini skanerlaydi
    python backfill.py --from 150     # 150-id dan boshlaydi (to'xtab qolsa davom)
    python backfill.py --max 3000     # maksimal tekshiriladigan id (chegara)

Talablar:
  - .env da BOT_TOKEN, ADMIN_IDS, MOVIE_CHANNEL_ID to'g'ri sozlangan bo'lsin
  - Bot kino kanalida ADMIN bo'lsin
  - Birinchi ADMIN_IDS dagi odam botga /start bergan bo'lsin (forward qilish
    uchun uning chatiga yozish mumkin bo'lishi kerak)

Jarayon davomida admin'ning chatiga har bir post qisqa vaqt ichida forward
qilinadi va darhol o'chiriladi (konvertlarda miltillab ko'rinadi). Bu muammo emas.
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Loyiha ildizini import yo'liga qo'shamiz (config, database, handlers topilishi uchun)
sys.path.insert(0, str(Path(__file__).resolve().parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("backfill")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Kino kanali backfill")
    parser.add_argument("--from", dest="start_id", type=int, default=1,
                        help="Qaysi message_id dan boshlash (default: 1)")
    parser.add_argument("--max", dest="max_id", type=int, default=200_000,
                        help="Maksimal tekshiriladigan message_id (default: 200000)")
    args = parser.parse_args()

    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    from config import ADMIN_IDS, BOT_TOKEN, MOVIE_CHANNEL_ID
    from database import init_db
    from handlers.channel import backfill_channel

    init_db()

    if not ADMIN_IDS:
        logger.error("ADMIN_IDS bo'sh — .env ni tekshiring.")
        return

    target = ADMIN_IDS[0]

    print("=" * 56)
    print(f"🍿  Kino kanali:    {MOVIE_CHANNEL_ID}")
    print(f"👤  Forward manzil: {target}")
    print(f"🔢  ID oralig'i:    {args.start_id} .. {args.max_id}")
    print("=" * 56)

    async def _progress(indexed, scanned, msg_id, done=False) -> None:
        if not done and indexed and indexed % 20 == 0:
            print(f"   ✅ {indexed} ta kino indekslandi (post #{msg_id})...")

    async with Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    ) as bot:
        result = await backfill_channel(
            bot,
            target_chat_id=target,
            start_id=args.start_id,
            max_id=args.max_id,
            on_progress=_progress,
        )

    print("=" * 56)
    print("✅  Backfill tugadi!")
    print(f"   🍿  Indekslangan:         {result['indexed']}")
    print(f"   📄  Tekshirilgan postlar: {result['scanned']}")
    print(f"   ⏭️   Tashlab ketilgan:     {result['skipped']}")
    print("=" * 56)


if __name__ == "__main__":
    asyncio.run(main())
