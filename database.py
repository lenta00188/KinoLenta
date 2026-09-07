import datetime as _dt
import logging

from psycopg.errors import IntegrityError
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from config import DATABASE_URL

logger = logging.getLogger(__name__)

# ===========================================================================
# Ulanish (Neon / PostgreSQL)
# ===========================================================================
# Neon serverless PostgreSQL: har bir "connection" haqiqiy TCP ulanish bo'lgani
# uchun ConnectionPool ishlatamiz. Har bir yangi ulanishda soat mintaqasini
# UTC ga o'rnatamiz — TIMESTAMPTZ ustunlari va premium_until to'g'ri ishlashi
# uchun (bazadagi barcha vaqtlar UTC).
_pool: ConnectionPool | None = None


def _dsn() -> str:
    """Neon majburiy SSL talab qiladi — sslmode bo'lmasa qo'shib qo'yamiz."""
    dsn = DATABASE_URL
    if "sslmode" not in dsn.lower():
        sep = "&" if "?" in dsn else "?"
        dsn += f"{sep}sslmode=require"
    return dsn


def _configure_conn(conn) -> None:
    """Har bir yangi ulanishda diksioner qatorlar va UTC soat mintaqasini o'rnatadi."""
    try:
        conn.row_factory = dict_row
        # `with conn:` — SET komandasi amalga oshib, ulanish IDLE holatida qoladi.
        # Aks holda ulanish INTRANS holatida qoladi va pool uni bekor qilib tashlaydi.
        with conn:
            conn.execute("SET TIME ZONE 'UTC'")
    except Exception as e:
        logger.warning("Ulanish sozlanmadi: %s", e)


# ===========================================================================
# Sxema yaratish / migratsiya
# ===========================================================================

SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        is_premium INTEGER DEFAULT 0,
        premium_until TIMESTAMPTZ,
        last_active TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        joined_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );""",
    """CREATE TABLE IF NOT EXISTS movies (
        movie_id BIGINT PRIMARY KEY,          -- Telegram message_id = kino ID
        title TEXT NOT NULL,
        year INTEGER,
        genres TEXT DEFAULT '',                  -- vergul bilan ajratilgan
        views INTEGER DEFAULT 0,
        requests INTEGER DEFAULT 0,
        favorites_count INTEGER DEFAULT 0,
        available INTEGER DEFAULT 1,
        premium_only INTEGER DEFAULT 0,          -- faqat Premium foydalanuvchilar uchunmi
        caption TEXT DEFAULT '',                 -- kanal postining to'liq matni (HTML)
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );""",
    """CREATE TABLE IF NOT EXISTS watchlist (
        user_id BIGINT NOT NULL,
        movie_id BIGINT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, movie_id)
    );""",
    """CREATE TABLE IF NOT EXISTS favorites (
        user_id BIGINT NOT NULL,
        movie_id BIGINT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, movie_id)
    );""",
    """CREATE TABLE IF NOT EXISTS watch_history (
        user_id BIGINT NOT NULL,
        movie_id BIGINT NOT NULL,
        watched_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, movie_id)
    );""",
    """CREATE TABLE IF NOT EXISTS reminders (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id BIGINT NOT NULL,
        movie_id BIGINT NOT NULL,
        reminder_time BIGINT NOT NULL,          -- unix timestamp
        status TEXT DEFAULT 'active',           -- active / done / cancelled
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );""",
    """CREATE TABLE IF NOT EXISTS support_conversations (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id BIGINT NOT NULL,
        status TEXT DEFAULT 'OPEN',             -- OPEN / CLOSED
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );""",
    """CREATE TABLE IF NOT EXISTS support_messages (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        conversation_id BIGINT NOT NULL,
        sender_id BIGINT NOT NULL,
        sender_type TEXT NOT NULL,              -- user / admin
        text TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );""",
    """CREATE TABLE IF NOT EXISTS movie_requests (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id BIGINT NOT NULL,
        title TEXT NOT NULL,
        status TEXT DEFAULT 'OPEN',             -- OPEN / DONE
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );""",
    """CREATE TABLE IF NOT EXISTS payments (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id BIGINT NOT NULL,
        amount TEXT,
        proof TEXT,
        status TEXT DEFAULT 'PENDING',          -- PENDING / APPROVED / REJECTED
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        processed_at TIMESTAMPTZ
    );""",
    """CREATE TABLE IF NOT EXISTS bot_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );""",
    """CREATE TABLE IF NOT EXISTS required_channels (
        chat_id BIGINT PRIMARY KEY,
        title TEXT DEFAULT '',
        username TEXT DEFAULT '',
        invite_link TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );""",
    """CREATE TABLE IF NOT EXISTS daily_views (
        user_id BIGINT NOT NULL,
        day TEXT NOT NULL,
        movie_id BIGINT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, day, movie_id)
    );""",
    """CREATE TABLE IF NOT EXISTS admins (
        user_id BIGINT PRIMARY KEY,
        added_by BIGINT,
        note TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );""",
    # --- movies jadvali uchun migratsiya: caption / premium_only ---
    "ALTER TABLE movies ADD COLUMN IF NOT EXISTS caption TEXT DEFAULT '';",
    "ALTER TABLE movies ADD COLUMN IF NOT EXISTS premium_only INTEGER DEFAULT 0;",
    # --- eski users jadvali uchun migratsiya (yangi ustunlar) ---
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_premium INTEGER DEFAULT 0;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS premium_until TIMESTAMPTZ;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;",
    # --- indekslar ---
    "CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title);",
    "CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_history_user ON watch_history(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(status, reminder_time);",
    "CREATE INDEX IF NOT EXISTS idx_support_status ON support_conversations(status);",
    "CREATE INDEX IF NOT EXISTS idx_support_messages_conv ON support_messages(conversation_id);",
    "CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);",
    "CREATE INDEX IF NOT EXISTS idx_movies_available ON movies(available);",
    "CREATE INDEX IF NOT EXISTS idx_users_premium ON users(is_premium, premium_until);",
    "CREATE INDEX IF NOT EXISTS idx_daily_views ON daily_views(user_id, day);",
    "CREATE INDEX IF NOT EXISTS idx_movies_premium ON movies(premium_only, available);",
]


def init_db() -> None:
    """Neon bazasiga ulanib, barcha jadvallarni yaratadi (mavjud bo'lmasa).

    Eslatma: mavjud (eski) bazadan foydalanilganda eski jadvallar (codes,
    channels, settings) o'chirilmaydi — ularning ma'lumotlari saqlanib qoladi,
    lekin yangi kod ularga bog'liq emas.
    """
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            _dsn(),
            min_size=1,
            max_size=5,
            open=False,
            timeout=30,
            max_waiting=0,
            configure=_configure_conn,
        )
        try:
            _pool.open(wait=True)
        except Exception:
            logger.exception("Neon bazasiga ulanish amalga oshmadi (DATABASE_URL ni tekshiring)")
            raise

    with _pool.connection() as conn:
        with conn:
            for stmt in SCHEMA_STATEMENTS:
                conn.execute(stmt)


def _get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("init_db() avval chaqirilmagan — bazaga ulanish to'g'ri emas")
    return _pool


def _fetchall(query, params=()):
    with _get_pool().connection() as conn:
        with conn:
            return conn.execute(query, params).fetchall()


def _fetchone(query, params=()):
    with _get_pool().connection() as conn:
        with conn:
            return conn.execute(query, params).fetchone()


def _execute(query, params=()) -> int:
    """Bitta bayonotni bajaradi va ta'sirlangan qatorlar sonini qaytaradi.

    Oldingi SQLite versiyada cursor qaytarilardi (cur.rowcount ishlatilardi);
    endi to'g'ridan-to'g'ri qatorlar soni qaytariladi.
    """
    with _get_pool().connection() as conn:
        with conn:
            cur = conn.execute(query, params)
            return cur.rowcount


# ===========================================================================
# Foydalanuvchilar
# ===========================================================================

def save_user(user_id: int, username, full_name: str) -> None:
    with _get_pool().connection() as conn:
        with conn:
            conn.execute(
                "INSERT INTO users (user_id, username, full_name) VALUES (%s, %s, %s) "
                "ON CONFLICT(user_id) DO UPDATE SET username=EXCLUDED.username, "
                "full_name=EXCLUDED.full_name, last_active=CURRENT_TIMESTAMP",
                (user_id, username, full_name),
            )


def touch_user(user_id: int) -> None:
    with _get_pool().connection() as conn:
        with conn:
            conn.execute(
                "UPDATE users SET last_active=CURRENT_TIMESTAMP WHERE user_id=%s",
                (user_id,),
            )


def get_user(user_id: int):
    return _fetchone("SELECT * FROM users WHERE user_id=%s", (user_id,))


def count_users() -> int:
    return _fetchone("SELECT COUNT(*) AS c FROM users")["c"]


def count_active_users(days: int = 7) -> int:
    return _fetchone(
        "SELECT COUNT(*) AS c FROM users "
        "WHERE last_active >= CURRENT_TIMESTAMP + (%s || ' days')::interval",
        (f"-{days}",),
    )["c"]


def count_premium_users() -> int:
    return _fetchone(
        "SELECT COUNT(*) AS c FROM users WHERE is_premium=1 "
        "AND premium_until IS NOT NULL AND premium_until > NOW()"
    )["c"]


def get_all_user_ids() -> list:
    return [r["user_id"] for r in _fetchall("SELECT user_id FROM users")]


# ---------- Premium ----------

def _now_utc() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _coerce_utc(value):
    """psycopg TIMESTAMPTZ dan datetime yoki eski matn sanani tayyor qiladi."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = _dt.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if isinstance(value, _dt.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=_dt.timezone.utc)
        return value
    return None


def is_premium(user_id: int) -> bool:
    row = _fetchone(
        "SELECT is_premium, premium_until FROM users WHERE user_id=%s",
        (user_id,),
    )
    if not row or not row["is_premium"]:
        return False
    until = _coerce_utc(row["premium_until"])
    return bool(until and until > _now_utc())


def set_premium(user_id: int, until_iso) -> None:
    """until_iso — datetime yoki 'YYYY-MM-DD HH:MM:SS' (UTC) matn."""
    with _get_pool().connection() as conn:
        with conn:
            conn.execute(
                "UPDATE users SET is_premium=1, premium_until=%s WHERE user_id=%s",
                (until_iso, user_id),
            )


def get_premium_until(user_id: int):
    row = _fetchone("SELECT premium_until FROM users WHERE user_id=%s", (user_id,))
    if not row:
        return None
    return _coerce_utc(row["premium_until"])


# ===========================================================================
# Kinolar (markaziy kanaldan indekslanadi)
# ===========================================================================

def upsert_movie(movie_id: int, title: str, year=None, genres: str = "",
                 caption: str = "", premium_only: int | None = None) -> None:
    """Kino meta-ma'lumotini bazaga yozadi (mavjud bo'lsa yangilaydi).

    movie_id = Telegram kanalidagi xabar (message) ID si.
    caption  = kanal postidagi TO'LIQ matn (HTML) — foydalanuvchiga shu ko'rsatiladi.
    Videoning o'zi bazada saqlanmaydi — manba Telegram kanali.

    premium_only:
      - 0 yoki 1 berilsa — kino shu holatga aniq belgilanadi (yangi post uchun,
        kanaldagi joriy "Premium rejim"ga qarab).
      - None berilsa (standart) — mavjud yozuvning premium_only qiymati
        o'zgarmaydi (post TAHRIRLANGANDA ishlatiladi, chunki tahrirlash paytida
        kanal rejimi boshqacha bo'lishi mumkin).
    """
    with _get_pool().connection() as conn:
        with conn:
            if premium_only is None:
                conn.execute(
                    "INSERT INTO movies (movie_id, title, year, genres, caption) "
                    "VALUES (%s, %s, %s, %s, %s) "
                    "ON CONFLICT(movie_id) DO UPDATE SET title=EXCLUDED.title, "
                    "year=EXCLUDED.year, genres=EXCLUDED.genres, caption=EXCLUDED.caption",
                    (movie_id, title, year, genres, caption),
                )
            else:
                conn.execute(
                    "INSERT INTO movies (movie_id, title, year, genres, caption, premium_only) "
                    "VALUES (%s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT(movie_id) DO UPDATE SET title=EXCLUDED.title, "
                    "year=EXCLUDED.year, genres=EXCLUDED.genres, caption=EXCLUDED.caption, "
                    "premium_only=EXCLUDED.premium_only",
                    (movie_id, title, year, genres, caption, int(premium_only)),
                )


def movie_exists(movie_id: int) -> bool:
    return _fetchone("SELECT 1 FROM movies WHERE movie_id=%s", (movie_id,)) is not None


def get_movie(movie_id: int):
    return _fetchone("SELECT * FROM movies WHERE movie_id=%s", (movie_id,))


def count_movies() -> int:
    return _fetchone("SELECT COUNT(*) AS c FROM movies WHERE available=1")["c"]


def list_movies(limit: int = 20, offset: int = 0):
    return _fetchall(
        "SELECT * FROM movies WHERE available=1 ORDER BY movie_id DESC LIMIT %s OFFSET %s",
        (limit, offset),
    )


def get_new_movies(limit: int = 10, offset: int = 0):
    return _fetchall(
        "SELECT * FROM movies WHERE available=1 ORDER BY movie_id DESC LIMIT %s OFFSET %s",
        (limit, offset),
    )


def get_premium_movies(limit: int = 10, offset: int = 0):
    """Admin tomonidan «Premium» rejimida yuborilgan kinolar (eng yangisi birinchi)."""
    return _fetchall(
        "SELECT * FROM movies WHERE available=1 AND premium_only=1 "
        "ORDER BY movie_id DESC LIMIT %s OFFSET %s",
        (limit, offset),
    )


def count_premium_movies() -> int:
    return _fetchone(
        "SELECT COUNT(*) AS c FROM movies WHERE available=1 AND premium_only=1"
    )["c"]


def get_random_movie():
    return _fetchone(
        "SELECT * FROM movies WHERE available=1 ORDER BY RANDOM() LIMIT 1"
    )


def increment_views(movie_id: int) -> None:
    _execute("UPDATE movies SET views=views+1 WHERE movie_id=%s", (movie_id,))


def increment_requests(movie_id: int) -> None:
    _execute("UPDATE movies SET requests=requests+1 WHERE movie_id=%s", (movie_id,))


def bump_favorites_count(movie_id: int, delta: int) -> None:
    _execute(
        "UPDATE movies SET favorites_count=GREATEST(0, favorites_count+%s) WHERE movie_id=%s",
        (delta, movie_id),
    )


# ===========================================================================
# Kinolarni ID bo'yicha olish
# ===========================================================================

def get_movies_by_ids(ids: list):
    """Berilgan ID lar bo'yicha kinolarni ID tartibini saqlagan holda qaytaradi."""
    if not ids:
        return []
    placeholders = ",".join("%s" for _ in ids)
    rows = _fetchall(
        f"SELECT * FROM movies WHERE available=1 AND movie_id IN ({placeholders})",
        tuple(ids),
    )
    by_id = {r["movie_id"]: r for r in rows}
    return [by_id[i] for i in ids if i in by_id]


# ===========================================================================
# Janrlar
# ===========================================================================

def get_genres() -> list:
    """Bazadagi barcha janrlar ro'yxati (takrorlarsiz, saralangan)."""
    seen = {}
    for row in _fetchall("SELECT genres FROM movies WHERE available=1 AND genres != ''"):
        for g in (row["genres"] or "").split(","):
            g = g.strip()
            if g and g not in seen:
                seen[g] = True
    return sorted(seen)


def get_movies_by_genre(genre: str, limit: int = 10, offset: int = 0):
    rows = _fetchall(
        "SELECT * FROM movies WHERE available=1 AND genres LIKE %s "
        "ORDER BY movie_id DESC LIMIT %s OFFSET %s",
        (f"%{genre}%", limit, offset),
    )
    total = _fetchone(
        "SELECT COUNT(*) AS c FROM movies WHERE available=1 AND genres LIKE %s",
        (f"%{genre}%",),
    )["c"]
    return rows, total


# ===========================================================================
# Saqlash (Watchlist)
# ===========================================================================

def add_watchlist(user_id: int, movie_id: int) -> bool:
    try:
        _execute(
            "INSERT INTO watchlist (user_id, movie_id) VALUES (%s, %s)",
            (user_id, movie_id),
        )
        return True
    except IntegrityError:
        return False


def remove_watchlist(user_id: int, movie_id: int) -> None:
    _execute("DELETE FROM watchlist WHERE user_id=%s AND movie_id=%s", (user_id, movie_id))


def is_in_watchlist(user_id: int, movie_id: int) -> bool:
    return _fetchone(
        "SELECT 1 FROM watchlist WHERE user_id=%s AND movie_id=%s", (user_id, movie_id)
    ) is not None


def count_watchlist(user_id: int) -> int:
    return _fetchone("SELECT COUNT(*) AS c FROM watchlist WHERE user_id=%s", (user_id,))["c"]


def get_watchlist(user_id: int, limit: int = 10, offset: int = 0):
    return _fetchall(
        "SELECT m.*, w.created_at AS saved_at FROM watchlist w "
        "JOIN movies m ON m.movie_id=w.movie_id "
        "WHERE w.user_id=%s AND m.available=1 "
        "ORDER BY w.created_at DESC LIMIT %s OFFSET %s",
        (user_id, limit, offset),
    )


def count_movie_watchlist(movie_id: int) -> int:
    return _fetchone("SELECT COUNT(*) AS c FROM watchlist WHERE movie_id=%s", (movie_id,))["c"]


# ===========================================================================
# Sevimlilar
# ===========================================================================

def add_favorite(user_id: int, movie_id: int) -> bool:
    try:
        _execute(
            "INSERT INTO favorites (user_id, movie_id) VALUES (%s, %s)",
            (user_id, movie_id),
        )
        bump_favorites_count(movie_id, 1)
        return True
    except IntegrityError:
        return False


def remove_favorite(user_id: int, movie_id: int) -> None:
    if _execute(
        "DELETE FROM favorites WHERE user_id=%s AND movie_id=%s", (user_id, movie_id)
    ) > 0:
        bump_favorites_count(movie_id, -1)


def is_favorite(user_id: int, movie_id: int) -> bool:
    return _fetchone(
        "SELECT 1 FROM favorites WHERE user_id=%s AND movie_id=%s", (user_id, movie_id)
    ) is not None


def count_favorites(user_id: int) -> int:
    return _fetchone("SELECT COUNT(*) AS c FROM favorites WHERE user_id=%s", (user_id,))["c"]


def get_favorites(user_id: int, limit: int = 10, offset: int = 0):
    return _fetchall(
        "SELECT m.*, f.created_at AS fav_at FROM favorites f "
        "JOIN movies m ON m.movie_id=f.movie_id "
        "WHERE f.user_id=%s AND m.available=1 "
        "ORDER BY f.created_at DESC LIMIT %s OFFSET %s",
        (user_id, limit, offset),
    )


# ===========================================================================
# Ko'rish tarixi va "Ko'rdim" holati
# ===========================================================================

def mark_watched(user_id: int, movie_id: int) -> bool:
    """Filmni ko'rilgan deb belgilaydi. Yangi belgilangan bo'lsa True qaytaradi."""
    try:
        _execute(
            "INSERT INTO watch_history (user_id, movie_id) VALUES (%s, %s)",
            (user_id, movie_id),
        )
        return True
    except IntegrityError:
        return False


def unmark_watched(user_id: int, movie_id: int) -> None:
    _execute(
        "DELETE FROM watch_history WHERE user_id=%s AND movie_id=%s", (user_id, movie_id)
    )


def is_watched(user_id: int, movie_id: int) -> bool:
    return _fetchone(
        "SELECT 1 FROM watch_history WHERE user_id=%s AND movie_id=%s", (user_id, movie_id)
    ) is not None


def get_watch_history(user_id: int, limit: int = 10, offset: int = 0):
    return _fetchall(
        "SELECT m.*, h.watched_at FROM watch_history h "
        "JOIN movies m ON m.movie_id=h.movie_id "
        "WHERE h.user_id=%s AND m.available=1 "
        "ORDER BY h.watched_at DESC LIMIT %s OFFSET %s",
        (user_id, limit, offset),
    )


def count_watch_history(user_id: int) -> int:
    return _fetchone(
        "SELECT COUNT(*) AS c FROM watch_history WHERE user_id=%s", (user_id,)
    )["c"]


# ===========================================================================
# Eslatmalar
# ===========================================================================

def add_reminder(user_id: int, movie_id: int, ts: int) -> bool:
    """Yangi eslatma qo'shadi. Shu film uchun faol eslatma mavjud bo'lsa False."""
    existing = _fetchone(
        "SELECT 1 FROM reminders WHERE user_id=%s AND movie_id=%s AND status='active'",
        (user_id, movie_id),
    )
    if existing:
        return False
    with _get_pool().connection() as conn:
        with conn:
            conn.execute(
                "INSERT INTO reminders (user_id, movie_id, reminder_time) VALUES (%s, %s, %s)",
                (user_id, movie_id, ts),
            )
            return True


def cancel_reminder(reminder_id: int, user_id: int) -> bool:
    # XATO TUZATILDI: status shartisiz UPDATE allaqachon bekor qilingan
    # eslatma uchun ham rowcount=1 qaytarardi ("bekor qilindi" ikki marta).
    return _execute(
        "UPDATE reminders SET status='cancelled' "
        "WHERE id=%s AND user_id=%s AND status='active'",
        (reminder_id, user_id),
    ) > 0


def list_reminders(user_id: int, limit: int = 10, offset: int = 0):
    return _fetchall(
        "SELECT r.id, r.movie_id, r.reminder_time, r.status, m.title "
        "FROM reminders r LEFT JOIN movies m ON m.movie_id=r.movie_id "
        "WHERE r.user_id=%s AND r.status='active' "
        "ORDER BY r.reminder_time ASC LIMIT %s OFFSET %s",
        (user_id, limit, offset),
    )


def count_reminders(user_id: int) -> int:
    return _fetchone(
        "SELECT COUNT(*) AS c FROM reminders WHERE user_id=%s AND status='active'",
        (user_id,),
    )["c"]


def get_due_reminders(now_ts: int):
    """Vaqti yetgan faol eslatmalar (kino nomi bilan birga)."""
    return _fetchall(
        "SELECT r.id, r.user_id, r.movie_id, r.reminder_time, m.title, m.year "
        "FROM reminders r LEFT JOIN movies m ON m.movie_id = r.movie_id "
        "WHERE r.status='active' AND r.reminder_time <= %s "
        "ORDER BY r.reminder_time ASC",
        (now_ts,),
    )


def mark_reminder_done(reminder_id: int) -> None:
    _execute("UPDATE reminders SET status='done' WHERE id=%s", (reminder_id,))


# ===========================================================================
# Support chat
# ===========================================================================

def create_conversation(user_id: int) -> int:
    with _get_pool().connection() as conn:
        with conn:
            cur = conn.execute(
                "INSERT INTO support_conversations (user_id) VALUES (%s) RETURNING id",
                (user_id,),
            )
            return cur.fetchone()["id"]


def get_open_conversation(user_id: int):
    return _fetchone(
        "SELECT * FROM support_conversations WHERE user_id=%s AND status='OPEN' "
        "ORDER BY updated_at DESC LIMIT 1",
        (user_id,),
    )


def get_or_create_open_conversation(user_id: int) -> int:
    row = get_open_conversation(user_id)
    if row:
        return row["id"]
    return create_conversation(user_id)


def get_conversation(conv_id: int):
    return _fetchone(
        "SELECT * FROM support_conversations WHERE id=%s", (conv_id,)
    )


def close_conversation(conv_id: int) -> None:
    _execute(
        "UPDATE support_conversations SET status='CLOSED', updated_at=CURRENT_TIMESTAMP "
        "WHERE id=%s",
        (conv_id,),
    )


def reopen_conversation(conv_id: int) -> None:
    _execute(
        "UPDATE support_conversations SET status='OPEN', updated_at=CURRENT_TIMESTAMP "
        "WHERE id=%s",
        (conv_id,),
    )


def touch_conversation(conv_id: int) -> None:
    _execute(
        "UPDATE support_conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=%s",
        (conv_id,),
    )


def list_open_conversations():
    return _fetchall(
        "SELECT c.*, u.username, u.full_name FROM support_conversations c "
        "LEFT JOIN users u ON u.user_id=c.user_id "
        "WHERE c.status='OPEN' ORDER BY c.updated_at DESC"
    )


def count_open_conversations() -> int:
    return _fetchone(
        "SELECT COUNT(*) AS c FROM support_conversations WHERE status='OPEN'",
    )["c"]


def add_support_message(conv_id: int, sender_id: int, sender_type: str, text: str) -> None:
    with _get_pool().connection() as conn:
        with conn:
            conn.execute(
                "INSERT INTO support_messages (conversation_id, sender_id, sender_type, text) "
                "VALUES (%s, %s, %s, %s)",
                (conv_id, sender_id, sender_type, text),
            )
            conn.execute(
                "UPDATE support_conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=%s",
                (conv_id,),
            )


def get_conversation_messages(conv_id: int, limit: int = 50):
    return _fetchall(
        "SELECT * FROM support_messages WHERE conversation_id=%s "
        "ORDER BY id DESC LIMIT %s",
        (conv_id, limit),
    )


# ===========================================================================
# Kino so'rovlari (library'da topilmaganda)
# ===========================================================================

def add_movie_request(user_id: int, title: str) -> int:
    with _get_pool().connection() as conn:
        with conn:
            cur = conn.execute(
                "INSERT INTO movie_requests (user_id, title) VALUES (%s, %s) RETURNING id",
                (user_id, title),
            )
            return cur.fetchone()["id"]


def count_movie_requests() -> int:
    return _fetchone("SELECT COUNT(*) AS c FROM movie_requests")["c"]


def list_open_requests():
    return _fetchall(
        "SELECT r.*, u.username, u.full_name FROM movie_requests r "
        "LEFT JOIN users u ON u.user_id=r.user_id "
        "WHERE r.status='OPEN' ORDER BY r.id DESC LIMIT 20"
    )


# ===========================================================================
# To'lovlar (Premium)
# ===========================================================================

def add_payment(user_id: int, amount: str, proof: str = "") -> int:
    with _get_pool().connection() as conn:
        with conn:
            cur = conn.execute(
                "INSERT INTO payments (user_id, amount, proof) VALUES (%s, %s, %s) RETURNING id",
                (user_id, amount, proof),
            )
            return cur.fetchone()["id"]


def get_payment(payment_id: int):
    return _fetchone("SELECT * FROM payments WHERE id=%s", (payment_id,))


def set_payment_status(payment_id: int, status: str) -> None:
    _execute(
        "UPDATE payments SET status=%s, processed_at=CURRENT_TIMESTAMP WHERE id=%s",
        (status, payment_id),
    )


def list_pending_payments():
    return _fetchall(
        "SELECT p.*, u.username, u.full_name FROM payments p "
        "LEFT JOIN users u ON u.user_id=p.user_id "
        "WHERE p.status='PENDING' ORDER BY p.id DESC"
    )


# ===========================================================================
# Bot sozlamalari (admin tahrirlaydi — kanal bundan mustasno!)
# ===========================================================================

def get_setting(key: str, default: str | None = None) -> str | None:
    row = _fetchone("SELECT value FROM bot_settings WHERE key=%s", (key,))
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with _get_pool().connection() as conn:
        with conn:
            conn.execute(
                "INSERT INTO bot_settings (key, value) VALUES (%s, %s) "
                "ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value",
                (key, value),
            )


# ===========================================================================
# Statistika
# ===========================================================================

def stats_summary() -> dict:
    """Admin panel uchun umumiy statistika."""
    total_views = _fetchone("SELECT COALESCE(SUM(views),0) AS s FROM movies")["s"]
    most_requested = _fetchall(
        "SELECT title, requests FROM movies WHERE available=1 "
        "ORDER BY requests DESC, views DESC LIMIT 5"
    )
    return {
        "users": count_users(),
        "active_users": count_active_users(),
        "movies": count_movies(),
        "all_movies": count_all_movies(),
        "total_views": total_views,
        "premium_users": count_premium_users(),
        "open_support": count_open_conversations(),
        "requests": count_movie_requests(),
        "most_requested": most_requested,
        "top_movies": get_top_movies(5),
        "pending_payments": _fetchone(
            "SELECT COUNT(*) AS c FROM payments WHERE status='PENDING'"
        )["c"],
        "reminders": _fetchone(
            "SELECT COUNT(*) AS c FROM reminders WHERE status='active'"
        )["c"],
    }


# ===========================================================================
# 👑 Adminlar (bir nechta admin — DB orqali boshqariladi)
# ===========================================================================

def add_admin(user_id: int, added_by: int = 0, note: str = "") -> bool:
    """Yangi admin qo'shadi. Allaqachon mavjud bo'lsa False."""
    try:
        _execute(
            "INSERT INTO admins (user_id, added_by, note) VALUES (%s, %s, %s)",
            (user_id, added_by, note),
        )
        return True
    except IntegrityError:
        return False


def remove_admin(user_id: int) -> bool:
    return _execute("DELETE FROM admins WHERE user_id=%s", (user_id,)) > 0


def list_db_admins() -> list:
    return _fetchall(
        "SELECT a.*, u.username, u.full_name FROM admins a "
        "LEFT JOIN users u ON u.user_id = a.user_id ORDER BY a.created_at ASC"
    )


def db_admin_ids() -> list:
    return [r["user_id"] for r in _fetchall("SELECT user_id FROM admins")]


# ===========================================================================
# Broadcast segmentlari
# ===========================================================================

def get_user_ids_by_segment(segment: str = "all") -> list:
    """segment: all | premium | free"""
    if segment == "premium":
        rows = _fetchall(
            "SELECT user_id FROM users WHERE is_premium=1 "
            "AND premium_until IS NOT NULL AND premium_until > NOW()"
        )
    elif segment == "free":
        rows = _fetchall(
            "SELECT user_id FROM users WHERE is_premium=0 "
            "OR premium_until IS NULL OR premium_until <= NOW()"
        )
    else:
        rows = _fetchall("SELECT user_id FROM users")
    return [r["user_id"] for r in rows]


def count_segment(segment: str = "all") -> int:
    return len(get_user_ids_by_segment(segment))


# ===========================================================================
# Premium — berish / bekor qilish
# ===========================================================================

def grant_premium(user_id: int, days: int) -> str:
    """Premium beradi (mavjud obunaga qo'shadi). Yakuniy sanani qaytaradi."""
    now = _now_utc()
    base = get_premium_until(user_id)
    start = now
    if base is not None:
        if base.tzinfo is None:
            base = base.replace(tzinfo=_dt.timezone.utc)
        if base > now:
            start = base
    until = start + _dt.timedelta(days=days)
    set_premium(user_id, until)
    return until.strftime("%Y-%m-%d %H:%M:%S")


def revoke_premium(user_id: int) -> None:
    _execute(
        "UPDATE users SET is_premium=0, premium_until=NULL WHERE user_id=%s",
        (user_id,),
    )


def list_premium_users(limit: int = 30):
    return _fetchall(
        "SELECT user_id, username, full_name, premium_until FROM users "
        "WHERE is_premium=1 AND premium_until IS NOT NULL "
        "AND premium_until > NOW() ORDER BY premium_until DESC LIMIT %s",
        (limit,),
    )


# ===========================================================================
# Kinolar — qo'shimcha
# ===========================================================================

def set_movie_available(movie_id: int, available: int) -> None:
    _execute("UPDATE movies SET available=%s WHERE movie_id=%s", (available, movie_id))


def get_top_movies(limit: int = 5):
    return _fetchall(
        "SELECT title, year, views FROM movies WHERE available=1 "
        "ORDER BY views DESC, favorites_count DESC LIMIT %s",
        (limit,),
    )


def count_all_movies() -> int:
    return _fetchone("SELECT COUNT(*) AS c FROM movies")["c"]


def get_recent_users(limit: int = 15):
    return _fetchall(
        "SELECT * FROM users ORDER BY joined_at DESC, user_id DESC LIMIT %s", (limit,)
    )


def find_user(needle: str):
    """ID yoki @username bo'yicha foydalanuvchini topadi."""
    needle = (needle or "").strip().lstrip("@")
    if not needle:
        return None
    if needle.isdigit():
        row = get_user(int(needle))
        if row:
            return row
    return _fetchone(
        "SELECT * FROM users WHERE lower(username)=lower(%s) LIMIT 1", (needle,)
    )


# ===========================================================================
# 📺 Majburiy obuna kanallari
# ===========================================================================

def add_required_channel(chat_id: int, title: str = "", username: str = "",
                         invite_link: str = "") -> bool:
    try:
        _execute(
            "INSERT INTO required_channels (chat_id, title, username, invite_link) "
            "VALUES (%s, %s, %s, %s)",
            (chat_id, title, username or "", invite_link or ""),
        )
        return True
    except IntegrityError:
        _execute(
            "UPDATE required_channels SET title=%s, username=%s, invite_link=%s "
            "WHERE chat_id=%s",
            (title, username or "", invite_link or "", chat_id),
        )
        return False


def remove_required_channel(chat_id: int) -> bool:
    return _execute("DELETE FROM required_channels WHERE chat_id=%s", (chat_id,)) > 0


def list_required_channels():
    return _fetchall("SELECT * FROM required_channels ORDER BY created_at ASC")


def count_required_channels() -> int:
    return _fetchone("SELECT COUNT(*) AS c FROM required_channels")["c"]


# ===========================================================================
# 🎬 Kunlik bepul limit
# ===========================================================================

def _today() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")


def count_today_views(user_id: int) -> int:
    return _fetchone(
        "SELECT COUNT(*) AS c FROM daily_views WHERE user_id=%s AND day=%s",
        (user_id, _today()),
    )["c"]


def viewed_today(user_id: int, movie_id: int) -> bool:
    return _fetchone(
        "SELECT 1 FROM daily_views WHERE user_id=%s AND day=%s AND movie_id=%s",
        (user_id, _today(), movie_id),
    ) is not None


def register_today_view(user_id: int, movie_id: int) -> None:
    try:
        _execute(
            "INSERT INTO daily_views (user_id, day, movie_id) VALUES (%s, %s, %s)",
            (user_id, _today(), movie_id),
        )
    except IntegrityError:
        pass


def purge_old_daily_views(keep_days: int = 7) -> None:
    _execute(
        "DELETE FROM daily_views WHERE day::date < CURRENT_DATE + (%s || ' days')::interval",
        (f"-{keep_days}",),
    )


# ===========================================================================
# 💎 VIP — yagona imtiyoz: majburiy obunadan ozod bo'lish.
# Bo'lim-darajasidagi tekin/premium rejimlari va foydalanish limitlari olib
# tashlandi — barcha bo'limlar va imkoniyatlar hammaga bir xil ochiq.
# ===========================================================================