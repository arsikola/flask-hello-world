import os
import json
import requests
from datetime import datetime
from flask import Flask, request

app = Flask(__name__)

# 🔐 Вебхук Bitrix24 из переменной окружения
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL")
FIELD_CODE = "UF_CRM_1743763731661"  # Дата последнего ответа клиента

@app.route("/", methods=["POST"])
def wazzup_webhook():
    data = request.json
    print("📬 Вебхук от Wazzup:", data)

    # Пропуск не входящих сообщений
    messages = data.get("messages")
    if not messages:
        print("❗ Ошибка в обработке: 'messages'")
        return "", 200

    message = messages[0]
    if message.get("isEcho"):
        print("➡️ Сообщение не входящее, пропускаем")
        return "", 200

    # Извлекаем номер
    phone_raw = message["chatId"]
    print(f"📞 Получен номер: {phone_raw}")

    # Последние 10 цифр
    phone_last10 = phone_raw[-10:]
    print(f"📞 Последние 10 цифр номера: {phone_last10}")

    # Поиск контакта
    contact_url = f"{BITRIX_WEBHOOK_URL}/crm.contact.list.json"
    contact_filter = {
        "filter": {
            "PHONE": f"%{phone_last10}"
        },
        "select": ["ID", "PHONE"]
    }
    contact_resp = requests.post(contact_url, json=contact_filter).json()
    print("🔍 Ответ на поиск контакта:", contact_resp)

    result = contact_resp.get("result", [])
    if not result:
        print("❌ Контакт не найден")
        return "", 200

    contact_id = result[0]["ID"]
    print(f"✅ Контакт найден: {contact_id}")

    # Поиск сделки по контакту
    deal_url = f"{BITRIX_WEBHOOK_URL}/crm.deal.list.json"
    deal_filter = {
        "filter": {"CONTACT_ID": contact_id},
        "select": ["ID"],
        "order": {"DATE_CREATE": "DESC"}
    }
    deal_resp = requests.post(deal_url, json=deal_filter).json()
    deals = deal_resp.get("result", [])
    print("📦 Найдено сделок:", len(deals))

    if not deals:
        print("❌ Сделки не найдены")
        return "", 200

    deal_id = deals[0]["ID"]
    print(f"✅ Сделка найдена: {deal_id}")

    # Обновление поля "Дата последнего ответа клиента"
    today_str = datetime.today().strftime("%Y-%m-%d")
    print(f"🛠 Обновляем поле {FIELD_CODE} на значение {today_str}")

    update_url = f"{BITRIX_WEBHOOK_URL}/crm.deal.update.json"
    update_data = {
        "id": deal_id,
        "fields": {
            FIELD_CODE: today_str
        }
    }
    update_resp = requests.post(update_url, json=update_data).json()
    print("🛡 Сделка обновлена:", update_resp)

    return "", 200
