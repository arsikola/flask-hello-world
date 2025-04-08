import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL")
FIELD_CODE = 'UF_CRM_1743763731661'  # Дата последнего ответа клиента

@app.route('/', methods=['POST'])
def wazzup_webhook():
    data = request.get_json()
    
    # 💬 Обработка только входящих сообщений
    messages = data.get("messages")
    if not messages or messages[0].get("isEcho"):
        print("❗ Ошибка в обработке: 'messages'")
        return jsonify({"status": "ignored"})

    message = messages[0]
    phone_raw = message["chatId"]
    print(f"📞 Получен номер: {phone_raw}")
    phone = "+7" + phone_raw[-10:] if not phone_raw.startswith("+") else phone_raw
    print(f"📞 Точный номер для поиска: {phone}")

    # 🔍 Поиск контакта
    contact_url = f"{BITRIX_WEBHOOK_URL}/crm.contact.list.json"
    contact_filter = {
        "filter": {
            "=PHONE": phone
        },
        "select": ["ID", "PHONE"]
    }
    contact_resp = requests.post(contact_url, json=contact_filter).json()
    print(f"🔍 Ответ на поиск контакта: {contact_resp}")

    if not contact_resp.get("result"):
        print("❌ Контакт не найден")
        return jsonify({"status": "no_contact"})

    contact_id = contact_resp["result"][0]["ID"]
    print(f"✅ Контакт найден: {contact_id}")

    # 📦 Поиск сделок
    deal_url = f"{BITRIX_WEBHOOK_URL}/crm.deal.list.json"
    deal_filter = {
        "filter": {
            "CONTACT_ID": contact_id
        },
        "select": ["ID", "TITLE"]
    }
    deal_resp = requests.post(deal_url, json=deal_filter).json()
    deals = deal_resp.get("result", [])
    print(f"📦 Найдено сделок: {len(deals)}")

    if not deals:
        print("❌ Сделки не найдены")
        return jsonify({"status": "no_deals"})

    deal_id = deals[0]["ID"]
    print(f"✅ Сделка найдена: {deal_id}")

    # 🛠 Обновление поля
    update_url = f"{BITRIX_WEBHOOK_URL}/crm.deal.update.json"
    today = datetime.today().strftime('%Y-%m-%d')
    print(f"🛠 Обновляем поле {FIELD_CODE} на значение {today}")
    update_resp = requests.post(update_url, json={
        "id": deal_id,
        "fields": {
            FIELD_CODE: today
        }
    }).json()
    print(f"🛡 Сделка обновлена: {update_resp}")

    return jsonify({"status": "success"})
