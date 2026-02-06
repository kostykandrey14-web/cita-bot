import requests

TOKEN = "8566470882:AAHkH9lzmsLqmE13B-yrR3QqL6ZN2Stv2lM"
CHAT_ID = "329651946"

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    response = requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    print("Статус:", response.status_code)
    print("Відповідь:", response.text)

send_telegram("🚀 Бот Telegram підключений і працює!")

