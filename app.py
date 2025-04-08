import os
from flask import Flask, request
import requests
from datetime import datetime

app = Flask(__name__)

# Получаем URL вебхука из переменной окружения
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL")
FIELD_CODE = "UF_CRM_1743763731661"  # Дата последнего ответа клиента

@app.route("/", methods=["POST"])
def wazzup_webhook():
    data = request.get_json()
    print(f"📬 Вебхук от Wazzup: {data}")

    if "messages" not in data:
        print("❗ Ошибка в обработке: 'messages'")
        return "", 200

    message = data["messages"][0]

    if message.get("isEcho") or message.get("status") != "inbound":
        print("➡️ Сообщение не входящее, пропускаем")
        return "", 200

    phone_raw = message["chatId"]
    print(f"📞 Получен номер: {phone_raw}")

    # 🔍 Используем точный номер с +7
    if not phone_raw.startswith("+"):
        phone_full = "+7" + phone_raw[-10:]
    else:
        phone_full = phone_raw
    print(f"📞 Точный номер для поиска: {phone_full}")

    # Поиск контакта по точному номеру
    contact_url = f"{BITRIX_WEBHOOK_URL}/crm.contact.list.json"
    contact_filter = {
        "filter": {
            "=PHONE": phone_full
        },
        "select": ["ID", "PHONE"]
    }
    contact_resp = requests.post(contact_url, json=contact_filter).json()
    print(f"🔍 Ответ на поиск контакта: {contact_resp}")

    contact_id = None
    for contact in contact_resp.get("result", []):
        for phone in contact.get("PHONE", []):
            phone_cleaned = phone["VALUE"].replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
            if phone_cleaned == phone_full:
                contact_id = contact["ID"]
                break
        if contact_id:
            break

    if not contact_id:
        print("❌ Контакт не найден")
        return "", 200

    print(f"✅ Контакт найден: {contact_id}")

    # Поиск сделок по контакту
    deal_url = f"{BITRIX_WEBHOOK_URL}/crm.deal.list.json"
    deal_filter = {
        "filter": {
            "CONTACT_ID": contact_id
        },
        "select": ["ID"]
    }
    deal_resp = requests.post(deal_url, json=deal_filter).json()
    deals = deal_resp.get("result", [])
    print(f"📦 Найдено сделок: {len(deals)}")

    if not deals:
        print("❌ Сделки не найдены")
        return "", 200

    # Используем самую новую (по ID)
    latest_deal = sorted(deals, key=lambda d: int(d["ID"]), reverse=True)[0]
    deal_id = latest_deal["ID"]
    print(f"✅ Сделка найдена: {deal_id}")

    # Обновляем нужное поле в сделке
    update_url = f"{BITRIX_WEBHOOK_URL}/crm.deal.update.json"
    today_str = datetime.now().strftime("%Y-%m-%d")
    update_payload = {
        "id": deal_id,
        "fields": {
            FIELD_CODE: today_str
        }
    }
    print(f"🛠 Обновляем поле {FIELD_CODE} на значение {today_str}")
    update_resp = requests.post(update_url, json=update_payload).json()
    print(f"🛡 Сделка обновлена: {update_resp}")

    return "", 200
