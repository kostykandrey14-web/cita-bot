import os, sys

lock_file = '/tmp/cita_bot.lock'

if os.path.exists(lock_file):
    print("❌ Bot already running")
    sys.exit(1)

with open(lock_file, 'w') as f:
    f.write(str(os.getpid()))
import time
import requests
import logging
import pytz
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, CallbackContext
)
from apscheduler.schedulers.background 
import BackgroundSchedulerfrom requests.adapters 
import HTTPAdapter
from urllib3.util.retry 
import Retry


# --------------------- Налаштування ---------------------
TOKEN = "8566470882:AAFjaELFYcGKXEvP_-q-x7MxghYl0BlNBHw"  # замініть на свій токен
URL = "https://icp.administracionelectronica.gob.es/icpplus/index.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X)"}
session = requests.Session()

retry = Retry(
    total=5,
    backoff_factor=1.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "HEAD"]
)

adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)
session.mount("http://", adapter)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APPOINTMENT_TYPES = {"NIE": "🟦 NIE", "TIE": "🟩 TIE"}

PROVINCES = [
    "Álava", "Albacete", "Alicante", "Almería", "Asturias", "Ávila",
    "Badajoz", "Barcelona", "Burgos", "Cáceres", "Cádiz", "Cantabria",
    "Castellón", "Ciudad Real", "Córdoba", "Cuenca", "Girona", "Granada",
    "Guadalajara", "Guipúzcoa", "Huelva", "Huesca", "Islas Baleares",
    "Jaén", "La Coruña", "La Rioja", "Las Palmas", "León", "Lleida",
    "Lugo", "Madrid", "Málaga", "Murcia", "Navarra", "Ourense",
    "Palencia", "Pontevedra", "Salamanca", "Santa Cruz de Tenerife",
    "Segovia", "Sevilla", "Soria", "Tarragona", "Teruel", "Toledo",
    "Valencia", "Valladolid", "Vizcaya", "Zamora", "Zaragoza", "Ceuta", "Melilla"
]

# --------------------- Збереження стану ---------------------
user_language = {}
user_temp_type = {}
user_temp_selection = {}
users = {}
daily_slot_count = {}

# --------------------- Мультимовність ---------------------
TRANSLATIONS = {
    "language_prompt": {"uk": "🌐 Оберіть мову інтерфейсу:", "en": "🌐 Choose your language:"},
    "start_prompt": {"uk": "👇 Оберіть тип процедури:", "en": "👇 Choose appointment type:"},
    "choose_province": {"uk": "👇 Оберіть провінції:", "en": "👇 Choose provinces:"},
    "next_button": {"uk": "➡️ Далі", "en": "➡️ Next"},
    "monitoring_started": {"uk": "✅ Почав моніторинг...", "en": "✅ Monitoring started..."},
    "new_slot": {"uk": "🚨 ЗНАЙДЕНА СІТА!\n", "en": "🚨 NEW SLOT AVAILABLE!\n"}
}

def t(lang, key):
    return TRANSLATIONS.get(key, {}).get(lang, key)

# --------------------- Функції ---------------------
def safe_edit_message(query, text, reply_markup=None):
    """Уникаємо помилки Message is not modified"""
    try:
        query.edit_message_text(text, reply_markup=reply_markup)
    except Exception as e:
        logger.debug(f"Edit message skipped: {e}")

def start(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    lang = update.message.from_user.language_code or "en"
    user_language[chat_id] = lang

    buttons = [
        [InlineKeyboardButton("🇺🇦 Українська", callback_data="LANG_uk"),
         InlineKeyboardButton("🇬🇧 English", callback_data="LANG_en")]
    ]
    update.message.reply_text(t(lang, "language_prompt"), reply_markup=InlineKeyboardMarkup(buttons))

def show_types(update: Update, lang, chat_id):
    keyboard = [[InlineKeyboardButton(v, callback_data=f"TYPE_{k}")] for k, v in APPOINTMENT_TYPES.items()]
    update.effective_message.reply_text(t(lang, "start_prompt"), reply_markup=InlineKeyboardMarkup(keyboard))

def show_provinces(update: Update, chat_id, lang):
    buttons = [[InlineKeyboardButton(p, callback_data=f"PROV_{p}")] for p in PROVINCES]
    buttons.append([InlineKeyboardButton(t(lang, "next_button"), callback_data="NEXT")])
    safe_edit_message(update.callback_query, t(lang, "choose_province"), InlineKeyboardMarkup(buttons))

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    chat_id = str(query.message.chat_id)
    lang = user_language.get(chat_id, "en")
    data = query.data

    if data.startswith("LANG_"):
        lang = data.replace("LANG_", "")
        user_language[chat_id] = lang
        show_types(update, lang, chat_id)
        return

    if data.startswith("TYPE_"):
        user_temp_type[chat_id] = data.replace("TYPE_", "")
        show_provinces(update, chat_id, lang)
        return

    if data.startswith("PROV_"):
        province = data.replace("PROV_", "")
        if chat_id not in user_temp_selection:
            user_temp_selection[chat_id] = []
        if province in user_temp_selection[chat_id]:
            user_temp_selection[chat_id].remove(province)
        else:
            user_temp_selection[chat_id].append(province)
        show_provinces(update, chat_id, lang)
        return

    if data == "NEXT":
        users[chat_id] = {
            "types": [user_temp_type.get(chat_id)],
            "provinces": user_temp_selection.get(chat_id, [])
        }
        safe_edit_message(query, t(lang, "monitoring_started"))
        if chat_id not in daily_slot_count:
            daily_slot_count[chat_id] = 0

# --------------------- Моніторинг сіти ---------------------
def check_slots():
    """Парсер всіх провінцій та типів"""
    try:
        r = requests.get(URL, headers=HEADERS, timeout=(10, 45))
        soup = BeautifulSoup(r.text, "lxml")
        slots = []
        for province in PROVINCES:
            if province in soup.text and "No hay citas disponibles" not in soup.text:
                office = f"Oficina {province}"  # Можна замінити на реальні дані
                slots.append({"province": province, "office": office})
        return slots
    except Exception as e:
        logger.error(f"Check slots error: {e}")
        return []

def monitor_job(_):
    slots = check_slots()
    for chat_id, data in users.items():
        for slot in slots:
            if slot["province"] in data["provinces"]:
                daily_slot_count[chat_id] += 1
                text = (
                    f"{t(user_language.get(chat_id, 'en'), 'new_slot')}"
                    f"🧾 Послуга: {data['types'][0]}\n"
                    f"📍 Провінція: {slot['province']}\n"
                    f"🏢 Офіс: {slot['office']}\n"
                    f"🔗 {URL}\n"
                    f"💡 Кількість сіти сьогодні: {daily_slot_count[chat_id]}"
                )
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                              data={"chat_id": chat_id, "text": text})

# --------------------- Основна функція ---------------------
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_handler))

    scheduler = BackgroundScheduler(timezone=pytz.timezone("Europe/Madrid"))
    scheduler.add_job(lambda: monitor_job(dp), "interval", seconds=45)
    scheduler.start()

    logger.info("🚀 Bot started...")
    updater.start_polling()
    updater.idle()
import atexit
atexit.register(lambda: os.remove(lock_file) if os.path.exists(lock_file) else None)

if __name__ == "__main__":
    main()

