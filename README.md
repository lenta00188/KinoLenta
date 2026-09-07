# 🎬 Kino Bot V3 — Telegram kinoteatri

Kino kanaliga asoslangan Telegram kino platformasi. Kinolar **markaziy
Telegram kanalida** saqlanadi, bot ularni avtomatik indekslab, raqam bo'yicha
qidirish, ro'yxat, sevimlilar, tarix, eslatmalar va support taqdim etadi.
Majburiy obuna yoqilganda, faqat **💎 VIP** obunachilar undan ozod bo'ladi.

---

## 🆕 V3 yangiliklari

### 📺 Majburiy obuna
Admin panel → **📺 Majburiy obuna** bo'limida kanallar qo'shiladi (@username, ID
yoki kanaldan forward). Foydalanuvchi barcha kanallarga a'zo bo'lmaguncha botdan
foydalana olmaydi. Tekshiruv **outer middleware** orqali ishlaydi — hech bir
handler chetlab o'tolmaydi. Adminlar tekshiruvdan ozod, natija 2 daqiqa keshlanadi.

> Bot har bir kanalda **admin** bo'lishi shart. Bot admin bo'lmagan kanal
> foydalanuvchini bloklamaydi (xato logga yoziladi).

### 🔢 Faqat raqam bilan ishlash
Nom bo'yicha qidiruv **butunlay olib tashlandi**. Endi oqim:

1. Foydalanuvchi raqam yuboradi → **kanal postidagi to'liq matn** chiqadi
   (HTML formatlash saqlanadi: qalin, kursiv, havolalar)
2. **«🎬 KINONI KO'RISH»** tugmasi bosiladi → videoning o'zi yuboriladi

Buning uchun `movies.caption` ustuni qo'shildi va kanal postining `html_text` i
saqlanadi. Post tahrirlansa — matn ham yangilanadi.

### 🎛 Yangi tugmalar tartibi
Eng yuqorida, butun kenglikda — **💎 Premium olish**. Keyin qolgan bo'limlar
juft-juft. «🔎 Kino qidirish» olib tashlandi, «💬 Support» → **«✉️ Adminga murojat»**.

### ✉️ Adminga murojat
Foydalanuvchi yozgan har bir xabar barcha adminlarga **«✍️ Javob berish»**
tugmasi bilan boradi. Admin javobi to'g'ridan-to'g'ri foydalanuvchiga keladi,
suhbat ikki tomonlama davom etadi.

### ⚙️ VIP — yagona imtiyoz: majburiy obunadan ozod bo'lish
Barcha bo'limlar (🆕 Yangi, 🎭 Janrlar, 🎲 Tasodifiy, ⭐ Ro'yxat,
❤️ Sevimlilar, 🕐 Tarix, ⏰ Eslatmalar) va kino ko'rish **hammaga cheksiz va
tekin** ochiq — hech qanday kunlik limit yoki bo'lim-darajasidagi qulflash yo'q.
Yagona istisno — quyidagi **💎 Premium filmlar** bo'limi.

VIP (💎 Premium) olishning yana bir ma'nosi: **majburiy obuna kanallariga a'zo
bo'lmasdan** botdan foydalanish. Majburiy obuna yoqilgan bo'lsa, VIP bo'lmagan
foydalanuvchi kanallarga a'zo bo'lmaguncha botni ishlata olmaydi; VIP
foydalanuvchi esa bundan butunlay ozod.

### 📝 VIP postini admin tahrirlaydi
Admin panel → 💎 Premium sozlamalari → **📝 Premium posti (matn)**.
O'rinbosarlar: `{price}`, `{days}`.
`-` yuborilsa standart matn qaytariladi.

### 💎 Premium filmlar bo'limi
Asosiy menyudagi **«🔥 Mashhur kinolar»** bo'limi **«💎 Premium filmlar»**ga
almashtirildi. Endi bu bo'limga kinolar reyting bo'yicha emas, balki
**admin qo'lda tanlab** joylaydi:

1. Admin markaziy kino kanaliga oddiy matnli **`Premium`** postini yuboradi.
2. Shu paytdan boshlab yuborilgan **BARCHA** kinolar (nechtasi bo'lishidan
   qat'i nazar) avtomatik ravishda «💎 Premium filmlar» bo'limiga tushadi.
3. Admin **`Stop`** postini yuborsa, rejim o'chadi va keyingi kinolar
   yana odatdagidek (faqat 🆕 Yangi kinolar va janrlar bo'yicha) indekslanadi.

`Premium` / `Stop` matnli postlarning o'zi kino sifatida bazaga yozilmaydi —
ular faqat rejimni yoqish/o'chirish buyrug'i sifatida ishlaydi.

Bo'lim standart holatda **faqat 💎 Premium foydalanuvchilar** uchun ochiq.
Admin buni istalgan payt **Admin panel → 💎 Premium sozlamalari →
🔒/🔓 «Premium filmlar»** tugmasi orqali yoqib/o'chirib qo'yishi mumkin —
o'chirilsa, bo'lim barcha foydalanuvchilar uchun ochiladi.

---

## 🐞 V2 da tuzatilgan xatolar

### Tuzatilgan xatolar

| # | Xato | Oqibati | Yechim |
|---|------|---------|--------|
| 1 | `CB_AW_WATCHED = "aww"` prefiksida ikki nuqta yo'q edi | Tomoshadan keyin **«✅ Ko'rdim»** bosilsa `IndexError` — tugma umuman ishlamasdi | `"aww:"` ga o'zgartirildi |
| 2 | `admin_payments_keyboard` da `p.get('amount')` | `sqlite3.Row` da `.get()` yo'q → **💰 To'lovlar bo'limi butunlay qulardi** | `p['amount']` |
| 3 | Support suhbatida `format_ts(created_at)` | `created_at` matn sana, `format_ts` unix kutardi → **suhbatni ochish `TypeError` bilan qulardi** | `format_ts` endi ikkala formatni ham oladi |
| 4 | `/cancel` faqat admin routerida edi | Oddiy foydalanuvchi eslatma/to'lov/support holatida **qotib qolardi** | `start.py` ga umumiy `/cancel` qo'shildi |
| 5 | Admin **callback**'lari filtrlanmagan edi | Har qanday foydalanuvchi to'lovni tasdiqlashi mumkin edi | `router.callback_query.filter(IsAdmin())` |
| 6 | `edit_text()` ga `ReplyKeyboardMarkup` berilardi | Support yopilganda va bo'sh ro'yxatlarda `TelegramBadRequest` | `emit()` endi avtomatik yangi xabar yuboradi |
| 7 | Janr aniqlash `genre in caption` | «melo**drama**» → «drama» janri ham qo'shilardi | So'z chegarasi (regex) |
| 8 | Fuzzy qidiruv sahifalanmasdi | `total` noto'g'ri, sahifalar buzilardi | To'g'ri offset/limit |
| 9 | `cancel_reminder` status shartisiz | Bekor qilingan eslatma qayta «bekor qilindi» derdi | `AND status='active'` |
| 10 | «message is not modified» yutilmasdi | Bir xil sahifa bosilganda xatolik | `emit` / `safe_edit_markup` |
| 11 | `backfill` da `msg_id` aniqlanmagan bo'lishi mumkin edi | `UnboundLocalError` | Oldindan qiymat berildi |
| 12 | Caption'siz postlar tashlab ketilardi | Kino bazaga tushmasdi, raqam orqali topilmasdi | `Kino #<id>` nomi bilan indekslanadi |

### Yangi imkoniyatlar

- **🔢 Raqam orqali kino** — `26` deb yozilsa 26-kino kartasi ochiladi
  (post `message_id` = kino raqami). Avval raqam oddiy matn sifatida qidirilardi.
- **👑 Bir nechta admin** — admin panelda qo'shish/o'chirish. `.env` dagilar «ega»
  hisoblanadi va o'chirilmaydi; faqat ular yangi admin tayinlaydi.
- **📢 Segmentli broadcast** — Hammaga / 💎 Premium / 🙋 Oddiy. Fon vazifasida
  ishlaydi, oxirida yuborildi/bloklagan/xatolik hisoboti chiqadi.
- **💰 To'lovni bir bosishda tasdiqlash** — admin xabarining o'zida
  ✅/❌ tugmalari; chek **rasm sifatida** yuboriladi.
- **💬 Support bildirishnomasi** — «✍️ Javob berish / 👁 Ochish / 🔒 Yopish» tugmalari
  to'g'ridan-to'g'ri xabarda; bir nechta admin javob bera oladi.
- **⏰ Eslatmalarda kino nomi va hafta kuni** — «Seshanba, 18:00 (11.08.2026) — Interstellar».
- **🎁 Qo'lda premium** berish va **🚫 bekor qilish** (ID yoki @username orqali).
- **📊 Kengaytirilgan statistika** — eng ko'p ko'rilganlar, faol eslatmalar,
  kutilayotgan to'lovlar.
- **🎲 «Boshqasini ko'rsat»** tugmasi tasodifiy kinoda.
- **🛡 Global error handler** — kutilmagan xato botni to'xtatmaydi.
- **⏳ Eskirgan tugmalar** javobsiz qolmaydi.

---

## ✨ To'liq imkoniyatlar ro'yxati

**🎥 Kino tizimi**
- 🎬 Markaziy kino kanali (har bir post = bitta kino, video bazada saqlanmaydi)
- 🤖 Avtomatik indekslash (nom, yil, janr, to'liq matn caption'dan)
- 🔢 Raqam → to'liq matn → «🎬 KINONI KO'RISH» → video
- 🆕 Yangi • 💎 Premium filmlar (admin qo'lda belgilaydi) • 🎲 Tasodifiy • 🎭 Janrlar

**⭐ Shaxsiy**
- ⭐ Watchlist • ❤️ Sevimlilar • 🕐 Ko'rish tarixi • ✅ Ko'rdim
- ⏰ Eslatmalar (tezkor tanlov + ixtiyoriy vaqt) • 👤 Profil

**💎 VIP**
- Narx / muddat / to'lov ma'lumotlari admin tomonidan sozlanadi (standart: 15 000 so'm / 30 kun)
- Chek yuborish → admin tasdiqlaydi → VIP avtomatik aktiv
- Yagona imtiyoz: **majburiy obuna kanallariga a'zo bo'lmasdan** botdan foydalanish

**👑 Admin**
- 📊 Statistika • 🎬 Katalog • 👥 Foydalanuvchilar • 💎 Premium
- 💬 Support • 💰 To'lovlar • 👑 Adminlar • 📢 Broadcast

---

## 📁 Tuzilma

```
kino2/
├── main.py            # Ishga tushirish + global error handler
├── backfill.py        # Kanaldagi MAVJUD postlarni bazaga yuklovchi CLI skript
├── config.py          # .env sozlamalari (ADMIN_IDS = egalar, OWNER_IDS, DATABASE_URL)
├── database.py        # PostgreSQL (Neon) sxemasi va barcha DB funksiyalari
├── keyboards.py       # Reply + inline klaviaturalar, callback prefikslar
├── utils.py           # emit(), dinamik adminlar, vaqt, kino kartasi, notify
├── scheduler.py       # Eslatmalar fon vazifasi
├── middlewares.py     # 📺 Majburiy obuna tekshiruvi (outer middleware)
├── handlers/
│   ├── filters.py     # IsAdmin / IsOwner (DINAMIK — bazadagi adminlarni ko'radi)
│   ├── states.py      # UserStates / AdminStates (FSM)
│   ├── start.py       # /start, /help, /cancel, /id
│   ├── browse.py      # Menyu tugmalari, ro'yxatlar, restore_nav
│   ├── movie.py       # Kino kartasi, tomosha, saqlash/sevimli/ko'rdim
│   ├── reminders.py   # Eslatma sozlash
│   ├── premium.py     # To'lov jarayoni
│   ├── support.py     # ✉️ Adminga murojat (user + admin ikki tomonlama)
│   ├── admin.py       # To'liq admin panel (/admin)
│   ├── channel.py     # Kanal postlarini avtomatik indekslash + backfill
│   └── user.py        # Raqam -> kino kartasi, eskirgan tugmalar
├── requirements.txt
├── render.yaml        # Render.com Blueprint (deploy)
├── .env.example
├── Dockerfile
└── fly.toml
```

---

## 🚀 O'rnatish (lokal)

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # va to'ldiring
python main.py
```

`.env` maydonlari:
- `BOT_TOKEN` — @BotFather dan
- `ADMIN_IDS` — **egalar** ID lari (@userinfobot orqali). Qolgan adminlar panel orqali qo'shiladi.
- `MOVIE_CHANNEL_ID` — markaziy kino kanali ID si (`-100...` bilan boshlanadi)
- `TZ` — eslatmalar vaqt mintaqasi (standart `Asia/Tashkent`)
- `DATABASE_URL` — **Neon (PostgreSQL)** ulanish satri. Neon.tech da loyiha
  yarating va "Connect → Pooled connection string" ni nusxalang
  (`postgresql://...-pooler.aws.neon.tech/dbname?sslmode=require`).

> 🗄️ **Ma'lumotlar bazasi:** loyiha endi Neon PostgreSQL ishlatadi (SQLite
> o'rniga). `init_db()` ishga tushganda barcha jadvallarni avtomatik yaratadi —
> qo'lda migratsiya shart emas. Neon'ning boshlang'ich (free) 0.5 GB hajmi bot
> uchun yetarli.

---

## 🎬 Markaziy kino kanalini sozlash

1. Kanal yarating va **botni administrator** qiling.
2. ID ni oling: kanaldagi xabarni @RawDataBot ga forward qiling →
   `forward_from_chat` → `id`.
3. `.env` da `MOVIE_CHANNEL_ID=-1001234567890`.
4. Kanalga video post qiling. Caption formati:

```
<b>Kino nomi</b> (2024)

🎭 Janr: Drama, Komediya
🌍 Davlat: AQSH
🎙 Tarjima: O'zbek tilida

#Drama #Komediya
```

> Postdagi **butun matn** saqlanadi va foydalanuvchi raqam yuborganda aynan shu
> matn ko'rsatiladi. Birinchi qatordan nom va yil, hashtaglardan janr ajratiladi.

> Bot kanalda admin bo'lmasa ishga tushmaydi (`validate_channel_access`).
> Caption bo'lmasa ham post `Kino #<id>` nomi bilan indekslanadi — raqam orqali topiladi.

---

## 🔄 Backfill — eski postlarni yuklash

Bot API'da kanal tarixini o'qish imkoni yo'q, shuning uchun bot qo'shilishidan
oldingi postlar bazada bo'lmaydi.

```bash
python backfill.py                # 1-id dan boshlab
python backfill.py --from 150     # to'xtab qolsa davom ettirish
python backfill.py --max 3000     # id chegarasi
```

Yoki botda: admin sifatida `/backfill`.

---

## 🛠 Admin panel (/admin)

| Bo'lim | Nima qiladi |
|---|---|
| 📊 Statistika | Foydalanuvchilar, kinolar, ko'rishlar, top kinolar, to'lovlar, so'rovlar |
| 🎬 Kinolar katalogi | `ID — Nom (yil)` ko'rinishida sahifalangan ro'yxat |
| 👥 Foydalanuvchilar | Jami/faol/premium, oxirgilar, premium ro'yxati |
| 💎 Premium sozlamalari | Narx, muddat, to'lov ma'lumotlari, **VIP posti matni**, qo'lda berish/bekor qilish |
| 📺 Majburiy obuna | Kanal qo'shish/o'chirish |
| 💬 Murojatlar | Ochiq murojatlar, javob berish, yopish |
| 💰 To'lovlar | Kutilayotganlar, chek rasmi, tasdiqlash/rad etish |
| 👑 Adminlar | Admin qo'shish/o'chirish (faqat egalar) |
| 📢 Xabar yuborish | Hammaga / Premium / Oddiy segmentlariga broadcast |
| 🚪 Chiqish | Panelni yopish |

Har qanday bosqichda `/cancel` yoki **❌ Bekor qilish**.

---

## ☁️ Render.com da deploy (Blueprint — FREE reja)

`render.yaml` fayli Render'ga loyihani bir tugma bilan deploy qilishga tayyor.
Service turi `worker` — bot HTTP server talab qilmaydi.

**Neon bazani tayyorlash (tekin loyiha yetarli):**
1. https://console.neon.tech → "New Project" → region yaqinroq bo'lganini tanlang.
2. "Connect" tugmasi → **Pooled connection string** (PostgreSQL) ni nusxalang:
   `postgresql://...-pooler.aws.neon.tech/kino_bot?sslmode=require`
3. (Istalgan holat) Neon'da dastlabki baza bo'sh — `init_db()` jadvallarni
   o'zi yaratadi.

**Render deployi (FREE plan):**
```bash
# 1) Kodni GitHub'ga push qiling
git add . && git commit -m "Neon + Render" && git push

# 2) Render dashboard → New + → Blueprint → reponi tanlang
#    render.yaml avtomatik topiladi va servis yaratiladi.

# 3) Deploy paytida quyidagilar so'raladi (sync: false):
#    BOT_TOKEN, ADMIN_IDS, MOVIE_CHANNEL_ID, DATABASE_URL(yuqoridagi satr)
```

Servis ishga tushgach Render konsolidagi loglarda `Bot ishga tushdi!` deb
chiqishi kerak. `/backfill` yoki `python backfill.py` orqali eski kinolarni
yuklang.

> ⚠️ **Free tier eslatmasi:** Render free `worker` servisi faoliyatsizlikda
> uxlab qolishi mumkin. Bot polling (so'rov) rejimida ishlagani uchun Telegram
> xabarlari kelayotganda uxlamaydi; qayta ishga tushganda esa avtomatik ulanadi.
> Barcha ma'lumot Neon'da saqlanadi, shuning uchun restart hech narsani
> yo'qotmaydi. Agar doimiy ishlash kerak bo'lsa, `starter` planiga o'tish
> yetarli (`render.yaml` dagi `plan: starter`).

`render.yaml` dagi `plan` qiymatini `free` / `starter` qilib o'zgartirishingiz
mumkin. `.env` serverga yuklanmaydi (`.dockerignore`), qolgan barcha maxfiy
ma'lumotlar Render Environment'da o'rnatiladi.
