from flask import Flask, request
import requests
from datetime import datetime
import os

app = Flask(__name__)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL")
FIELD_CODE = 'UF_CRM_1743763731661'  # Дата последнего ответа клиента

@app.route("/", methods=["POST"])
def wazzup_webhook():
    data = request.get_json()

    try:
        if "messages" not in data:
            print("❗ Ошибка в обработке: 'messages'")
            return "", 200

        for message in data["messages"]:
            if message.get("isEcho"):
                print("➡️ Сообщение не входящее, пропускаем")
                continue

            phone_raw = message["chatId"]
            print(f"📞 Получен номер: {phone_raw}")
            phone = phone_raw[-10:]
            print(f"📞 Последние 10 цифр номера: {phone}")

            # Поиск контакта по номеру
            contact_filter = {
                "filter": {
                    "PHONE": [{"VALUE": phone}]
                },
                "select": ["ID"]
            }
            contact_url = f"{BITRIX_WEBHOOK_URL}/crm.contact.list.json"
            contact_resp = requests.post(contact_url, json=contact_filter).json()

            print(f"🔍 Ответ на поиск контакта: {contact_resp}")

            if "result" not in contact_resp or not contact_resp["result"]:
                print("❌ Контакт не найден")
                return "", 200

            contact_id = contact_resp["result"][0]["ID"]
            print(f"✅ Контакт найден: {contact_id}")

            # Поиск сделок контакта
            deals_filter = {
                "filter": {"CONTACT_ID": contact_id},
                "select": ["ID", "STAGE_ID", "TITLE", FIELD_CODE],
                "order": {"ID": "DESC"}
            }
            deals_url = f"{BITRIX_WEBHOOK_URL}/crm.deal.list.json"
            deals_resp = requests.post(deals_url, json=deals_filter).json()

            print(f"📦 Найдено сделок: {len(deals_resp.get('result', []))}")
            if not deals_resp.get("result"):
                print("❌ Сделки не найдены")
                return "", 200

            deal_id = deals_resp["result"][0]["ID"]
            print(f"✅ Сделка найдена: {deal_id}")

            # Обновление поля "Дата последнего ответа клиента"
            today = datetime.now().strftime("%Y-%m-%d")
            update_url = f"{BITRIX_WEBHOOK_URL}/crm.deal.update.json"
            update_data = {
                "id": deal_id,
                "fields": {
                    FIELD_CODE: today
                }
            }
            print(f"🛠 Обновляем поле {FIELD_CODE} на значение {today}")
            update_resp = requests.post(update_url, json=update_data).json()
            print(f"🛡 Сделка обновлена: {update_resp}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")

    return "", 200
