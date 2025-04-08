import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Конфигурация
WEBHOOK_TOKEN = os.getenv("BITRIX_WEBHOOK")
FIELD_CODE = "UF_CRM_1743763731661"  # Дата последнего ответа клиента

@app.route("/", methods=["POST"])
def wazzup_webhook():
    data = request.json

    # Если это не входящее сообщение — игнорируем
    if "messages" not in data or not data["messages"]:
        print("❗ Ошибка в обработке: 'messages'")
        return "", 200

    message = data["messages"][0]
    if message.get("isEcho") or message.get("type") != "text":
        print("➡️ Сообщение не входящее, пропускаем")
        return "", 200

    phone_raw = message["chatId"]
    phone = phone_raw[-10:]  # Последние 10 цифр
    print(f"📞 Получен номер: {phone_raw}")
    print(f"📞 Последние 10 цифр номера: {phone}")

    # Поиск контакта
    contact_url = f"{WEBHOOK_TOKEN}/crm.contact.list.json"
    contact_filter = {"filter": { "PHONE": phone }, "select": ["ID"]}
    contact_resp = requests.post(contact_url, json=contact_filter).json()

    contact_list = contact_resp.get("result", [])
    if not contact_list:
        print("❌ Контакт не найден")
        return "", 200

    contact_id = contact_list[0]["ID"]
    print(f"✅ Контакт найден: {contact_id}")

    # Поиск одной сделки
    deal_url = f"{WEBHOOK_TOKEN}/crm.deal.list.json"
    deal_filter = {
        "filter": { "CONTACT_ID": contact_id },
        "select": ["ID", "DATE_CREATE"],
        "order": { "DATE_CREATE": "DESC" },
        "start": 0
    }
    deal_resp = requests.post(deal_url, json=deal_filter).json()
    deals = deal_resp.get("result", [])
    if not deals:
        print("❌ Сделка не найдена")
        return "", 200

    deal_id = deals[0]["ID"]
    print(f"✅ Сделка найдена: {deal_id}")

    # Обновление поля
    update_url = f"{WEBHOOK_TOKEN}/crm.deal.update.json"
    payload = {
        "id": deal_id,
        "fields": {
            FIELD_CODE: datetime.now().strftime("%Y-%m-%d")
        }
    }
    print(f"🛠 Обновляем поле {FIELD_CODE} на значение {payload['fields'][FIELD_CODE]}")
    update_resp = requests.post(update_url, json=payload).json()
    print(f"🛡 Сделка обновлена: {update_resp}")

    return "", 200
