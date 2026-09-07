import os

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Asosiy sozlamalar (.env dan o'qiladi)
# ---------------------------------------------------------------------------

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise ValueError(
        "❌ BOT_TOKEN topilmadi! .env faylida @BotFather dan olingan tokenni kiriting."
    )

ADMIN_IDS = [
    int(a.strip()) for a in os.getenv("ADMIN_IDS", "").split(",") if a.strip()
]
if not ADMIN_IDS:
    raise ValueError("❌ ADMIN_IDS topilmadi! Admin Telegram ID raqamlarini kiriting.")

# .env dagi adminlar — "egalar" (owner). Ular hech qachon o'chirilmaydi va faqat
# ular yangi admin qo'sha/o'chira oladi. Qo'shimcha adminlar bazada saqlanadi.
OWNER_IDS = list(ADMIN_IDS)

# Eslatmalar uchun standart vaqt mintaqasi (masalan: Asia/Tashkent)
DEFAULT_TZ = os.getenv("TZ", "Asia/Tashkent")

# ---------------------------------------------------------------------------
# Neon (PostgreSQL) ma'lumotlar bazasi
# ---------------------------------------------------------------------------
# Render.com da deploy qilayotganda DATABASE_URL ni Neon'ning ulanish satriga
# tenglang. Neon'da loyiha ochib, "Connection string" (PostgreSQL) ni nusxalsangiz
# kifoya — bot shu ma'lumotlarga ulanadi.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise ValueError(
        "❌ DATABASE_URL topilmadi!\n\n"
        "Neon PostgreSQL ulanish satrini .env faylida kiriting:\n"
        "  DATABASE_URL=postgresql://user:password@ep-abc-123-pooler.aws.neon.tech/kino_bot?sslmode=require\n\n"
        "Neon: https://console.neon.tech — loyiha yarating va 'Connection string'ni nusxalang.\n"
        "Render: https://dashboard.render.com — Service > Environment da DATABASE_URL ni o'rnating."
    )

# ---------------------------------------------------------------------------
# MARKAZIY KINO KANALI  —  MUHIM!
# ---------------------------------------------------------------------------
# Bu konfiguratsiya FAQAT .env dan o'qiladi va runtime'da admin panel orqali
# o'zgartirilmaydi. Kanalni almashtirish uchun .env ni tahrirlab, ilovani
# qayta ishga tushirish kerak.
# ---------------------------------------------------------------------------

MOVIE_CHANNEL_ID_RAW = os.getenv("MOVIE_CHANNEL_ID", "").strip()

if not MOVIE_CHANNEL_ID_RAW:
    raise ValueError(
        "❌ MOVIE_CHANNEL_ID topilmadi!\n\n"
        "Markaziy kino kanalining ID raqamini .env faylida kiriting:\n"
        "  MOVIE_CHANNEL_ID=-1001234567890\n\n"
        "ID ni qanday bilish mumkin:\n"
        "  1) @RawDataBot ga kanalning istalgan xabarini forward qiling;\n"
        "  2) undagi 'forward_from_chat' → 'id' qiymatini nusxalang.\n"
        "Bot shu kanalda ADMIN bo'lishi shart."
    )

try:
    MOVIE_CHANNEL_ID = int(MOVIE_CHANNEL_ID_RAW)
except ValueError:
    raise ValueError(
        f"❌ MOVIE_CHANNEL_ID noto'g'ri formatda: {MOVIE_CHANNEL_ID_RAW!r}\n"
        "U butun son (integer) bo'lishi kerak, masalan: -1001234567890"
    )

if not (MOVIE_CHANNEL_ID < 0 and str(MOVIE_CHANNEL_ID).startswith("-100")):
    raise ValueError(
        f"❌ MOVIE_CHANNEL_ID haqiqiy kanal/superguruh ID emas: {MOVIE_CHANNEL_ID}\n"
        "Kanal/superguruh ID lari odatda '-100...' bilan boshlanadi. "
        "@RawDataBot orqali to'g'ri ID ni oling."
    )

# ---------------------------------------------------------------------------
# WEBHOOK (Render.com free web service) — ixtiyoriy
# ---------------------------------------------------------------------------
# Render FREE taraqqiyotida faqat "web" service mumkin; worker bloklangan.
# Shuning uchun bot webhook rejimida ishlaydi. WEBHOOK_URL berilsa — webhook
# rejimi, berilmasa — lokal polling.
#
# MUHIM: Render web servisga asl (haqiqiy) URL ni RENDER_EXTERNAL_URL avtomatik
# beradi (masalan https://kino-bot-zk4t.onrender.com). Shu sababli uni birinchi
# o'rinda ishlatamiz — render.yaml'dagi WEBHOOK_URL faqat fallback (agar
# RENDER_EXTERNAL_URL bo'lmasa).
_WEBHOOK_URL = (os.getenv("RENDER_EXTERNAL_URL", "") or "").strip().rstrip("/")
if not _WEBHOOK_URL:
    _WEBHOOK_URL = (os.getenv("WEBHOOK_URL", "") or "").strip().rstrip("/")
WEBHOOK_URL = _WEBHOOK_URL
WEBHOOK_PATH = (os.getenv("WEBHOOK_PATH", "") or "/webhook").strip() or "/webhook"
WEBHOOK_SECRET = (os.getenv("WEBHOOK_SECRET", "") or "").strip()
WEBHOOK_PORT = int(os.getenv("PORT", "8080"))
