from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    waiting_reminder_time = State()  # "Boshqa vaqt" — vaqtni kutish
    waiting_payment_proof = State()  # premium to'lov tasdig'ini kutish
    support_chat = State()           # support suhbat holati


class AdminStates(StatesGroup):
    waiting_broadcast_text = State()
    waiting_broadcast_confirm = State()
    waiting_premium_value = State()   # data: prem_field -> narx / muddat / to'lov info
    support_reply = State()           # data: adm_conv_id
    waiting_admin_id = State()        # 👑 yangi admin ID si
    waiting_premium_grant = State()   # 🎁 qo'lda premium: "<user> <kun>"
    waiting_premium_revoke = State()  # 🚫 premiumni bekor qilish: "<user>"
    waiting_channel_add = State()     # 📺 majburiy obuna kanali
    waiting_premium_text = State()    # 📝 premium posti matni
    waiting_start_text = State()      # 📝 /start posti matni
    waiting_subscribe_text = State()  # 📝 majburiy obuna posti sarlavhasi
    waiting_vip_button_text = State() # 📝 VIP tugmasi matni
    waiting_channel_button_text = State()  # 📝 kanal tugmasi matni
