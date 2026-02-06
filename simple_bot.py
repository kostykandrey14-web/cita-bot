import time
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from bs4 import BeautifulSoup

# --- Типи процедур ---
APPOINTMENT_TYPES = {
    "TP": "🟦 Temporary Protection",
    "TIE": "🟩 TIE Card"
}

# --- Змінні для збереження вибору ---
user_temp_type = {}
user_temp_selection = {}
user_language = {}
users = {}

# --- Telegram ---
TOKEN = "8566470882:AAHkH9lzmsLqmE13B-yrR3QqL6ZN2Stv2lM"
CHAT_ID = "329651946"

# --- Сайт ---
URL = "https://icp.administracionelectronica.gob.es/icpplus/index.html"
HEADERS = { "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X)"}

# --- Список провінцій ---
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

# --- Мультимовні тексти ---
TRANSLATIONS = {
    "start_prompt": {
        "uk": "👇 Оберіть тип процедури:",
        "en": "👇 Choose appointment type:",
        "ru": "👇 Выберите тип процедуры:",
        "es": "👇 Elija el tipo de cita:"
    },
    "choose_province": {
        "uk": "👇 Оберіть провінції:",
        "en": "👇 Choose provinces:",
        "ru": "👇 Выберите провинции:",
        "es": "👇 Elija provincias:"
    },
    "saved_choices": {
        "uk": "✅ Вибір збережено!",
        "en": "✅ Your choice has been saved!",
        "ru": "✅ Выбор сохранён!",
        "es": "✅ ¡Su elección ha sido guardada!"
    },
    "no_slots": {
        "uk": "❌ Сіт немає...",
        "en": "❌ No slots available...",
        "ru": "❌ Нет доступных записей...",
        "es": "❌ No hay citas disponibles..."
    },
    "new_slot": {
        "uk": "🚨 З'ЯВИЛАСЬ СІТА!\n",
        "en": "🚨 NEW SLOT AVAILABLE!\n",
        "ru": "🚨 ПОЯВИЛАСЬ СЛОТ!\n",
        "es": "🚨 ¡NUEVA CITA DISPONIBLE!\n"
    },
    "language_prompt": {
        "uk": "🌐 Оберіть мову інтерфейсу:",
        "en": "🌐 Choose your language:",
        "ru": "🌐 Выберите язык интерфейса:",
        "es": "🌐 Elija su idioma:"
    },
    "instructions_clearance": {
        "uk": (
            "ℹ️ Як самостійно розмитнити авто без посередників:\n"
            "1. Підготуйте документи: техпаспорт, договір купівлі, квитанції.\n"
            "2. Перейдіть на офіційний сайт митниці/податкової.\n"
            "3. Заповніть форму для розмитнення (TARIC/DUA).\n"
            "4. Подайте документи онлайн або у відділенні.\n"
            "5. Дочекайтесь підтвердження та сплатіть лише обов’язкові збори."
        ),
        "en": (
            "ℹ️ How to clear your vehicle yourself without intermediaries:\n"
            "1. Prepare documents: registration certificate, purchase contract, receipts.\n"
            "2. Go to the official customs/tax website.\n"
            "3. Fill out the clearance form (TARIC/DUA).\n"
            "4. Submit documents online or in person.\n"
            "5. Wait for confirmation and pay only mandatory fees."
        ),
        "ru": (
            "ℹ️ Как самостоятельно растаможить авто без посредников:\n"
            "1. Подготовьте документы: техпаспорт, договор купли-продажи, квитанции.\n"
            "2. Перейдите на официальный сайт таможни/налоговой.\n"
            "3. Заполните форму растаможки (TARIC/DUA).\n"
            "4. Подайте документы онлайн или в отделении.\n"
            "5. Дождитесь подтверждения и оплатите только обязательные сборы."
        ),
        "es": (
            "ℹ️ Cómo despachar su vehículo usted mismo sin intermediarios:\n"
            "1. Prepare los documentos: registro del vehículo, contrato de compra, recibos.\n"
            "2. Vaya al sitio web oficial de aduanas/impuestos.\n"
            "3. Complete el formulario de despacho (TARIC/DUA).\n"
            "4. Envíe los documentos en línea o en persona.\n"
            "5. Espere la confirmación y pague solo las tasas obligatorias."
        )
    }
}

def t(lang, key):
    lang = lang if lang in ["uk", "en", "ru", "es"] else "en"
    return TRANSLATIONS.get(key, {}).get(lang, "")

# ---------------------- Функції ----------------------

def start(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    lang = update.message.from_user.language_code or "en"
    user_language[chat_id] = lang

    # --- Кнопки для вибору мови ---
    lang_buttons = [
        [InlineKeyboardButton("🇺🇦 Українська", callback_data="LANG_uk"),
         InlineKeyboardButton("🇬🇧 English", callback_data="LANG_en")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="LANG_ru"),
         InlineKeyboardButton("🇪🇸 Español", callback_data="LANG_es")]
    ]
    update.message.reply_text(
        t(lang, "language_prompt"),
        reply_markup=InlineKeyboardMarkup(lang_buttons)
    )

def show_types(update: Update, lang, chat_id):
    keyboard = [[InlineKeyboardButton(v, callback_data=f"TYPE_{k}")] for k,v in APPOINTMENT_TYPES.items()]
    # Додаємо кнопку інструкції розмитнення
    keyboard.append([InlineKeyboardButton("📄 Інструкція розмитнення авто без посередників", callback_data="INSTR_CLEAR")])
    update.message.reply_text(
        t(lang, "start_prompt"),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def send_telegram(text, chat_id=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    target_chat = chat_id if chat_id else CHAT_ID
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

def check_slots():
    r = requests.get(URL, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "lxml")
    available_provinces = []
    for province in PROVINCES:
        if province in soup.text and "No hay citas disponibles" not in soup.text:
            available_provinces.append(province)
    return available_provinces

def show_provinces(query, chat_id, lang="en"):
    keyboard = [
        [InlineKeyboardButton(p, callback_data=f"PROV_{p}")]
        for p in PROVINCES
    ]

    keyboard.append(
        [InlineKeyboardButton("✅ Save", callback_data="SAVE")]
    )

    query.edit_message_text(
        t(lang, "choose_province"),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    data = query.data
    chat_id = str(query.message.chat_id)
    lang = query.from_user.language_code or "en"

    if data.startswith("LANG_"):
        lang = data.replace("LANG_", "")
        user_language[chat_id] = lang
        query.edit_message_text(t(lang, "instructions_clearance"))
        show_types(update, lang, chat_id)
        return

    if data == "INSTR_CLEAR":
        query.edit_message_text(t(lang, "instructions_clearance"))
        return

    # --- Вибір типу процедури ---
    if data.startswith("TYPE_"):
        selected_type = data.replace("TYPE_", "")
        user_temp_type[chat_id] = selected_type

        show_provinces(query, chat_id, lang)
        return

    # --- Вибір провінції ---
    if data.startswith("PROV_"):
        province = data.replace("PROV_", "")

        if chat_id not in user_temp_selection:
            user_temp_selection[chat_id] = []

        if province in user_temp_selection[chat_id]:
            user_temp_selection[chat_id].remove(province)
        else:
            user_temp_selection[chat_id].append(province)

        show_provinces(query, chat_id, lang)
        return

    # --- Збереження вибору ---
    if data == "SAVE":
        users[chat_id] = {
            "types": [user_temp_type.get(chat_id, "")],
            "provinces": user_temp_selection.get(chat_id, [])
        }

        query.edit_message_text(
            t(lang, "saved_choices")
        )
        return

# ---------------------- Моніторинг сіти ----------------------

print("🔍 Бот запущений. Моніторю сіти...")

while True:
    try:
        available = check_slots()
        if available:
            for chat_id, data in users.items():
                user_provinces = data.get("provinces", [])
                matching = [p for p in available if p in user_provinces]
                if matching:
                    provinces_text = ", ".join(matching)
                    send_telegram(f"🚨 З'ЯВИЛАСЬ СІТА у провінціях: {provinces_text}\n{URL}", chat_id)
            time.sleep(600)
        else:
            print(t("uk", "no_slots"))
    except Exception as e:
         print("⚠️ Помилка:", e)
    time.sleep(45)
