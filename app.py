import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL")
FIELD_CODE = "UF_CRM_1743763731661"  # Дата последнего ответа клиента

@app.route("/", methods=["POST"])
def wazzup_webhook():
    data = request.get_json()
    print("📬 Вебхук от Wazzup:", data)

    messages = data.get("messages")
    if not messages:
        print("❗ Ошибка в обработке: 'messages'")
        return jsonify(success=True)

    message = messages[0]
    phone_raw = message["chatId"]
    print(f"📞 Получен номер: {phone_raw}")

    # Форматы номера для поиска
    formats = format_phone_variants(phone_raw)
    print("📞 Форматы номера для поиска:", formats)

    contact_id = find_contact_by_phone_variants(formats)
    if not contact_id:
        print("❌ Контакт не найден")
        return jsonify(success=True)
    print("✅ Контакт найден:", contact_id)

    # Поиск сделок по контакту
    deals = requests.post(f"{BITRIX_WEBHOOK_URL}/crm.deal.list.json", json={
        "filter": {"CONTACT_ID": contact_id},
        "select": ["ID"]
    }).json().get("result", [])

    if not deals:
        print("❌ Сделки не найдены")
        return jsonify(success=True)
    
    deal_id = deals[0]["ID"]
    print("✅ Сделка найдена:", deal_id)

    # Обновление поля даты
    date_value = datetime.now().strftime("%Y-%m-%d")
    print(f"🛠 Обновляем поле {FIELD_CODE} на значение {date_value}")

    update_resp = requests.post(f"{BITRIX_WEBHOOK_URL}/crm.deal.update.json", json={
        "id": deal_id,
        "fields": {FIELD_CODE: date_value}
    }).json()

    print("🛡 Сделка обновлена:", update_resp)
    return jsonify(success=True)

def format_phone_variants(phone):
    raw = phone[-10:]
    return [
        f"+7{raw}",
        f"+7({raw[:3]}){raw[3:6]}-{raw[6:8]}-{raw[8:]}",
        f"+7 {raw[:3]} {raw[3:6]} {raw[6:8]} {raw[8:]}",
        f"+7-{raw[:3]}-{raw[3:6]}-{raw[6:8]}-{raw[8:]}"
    ]

def find_contact_by_phone_variants(variants):
    for phone in variants:
        contact_filter = {
            "filter": {"=PHONE": phone},
            "select": ["ID", "PHONE"]
        }
        contact_url = f"{BITRIX_WEBHOOK_URL}/crm.contact.list.json"
        response = requests.post(contact_url, json=contact_filter).json()
        print(f"🔍 Ответ на поиск контакта по {phone}:", response)
        result = response.get("result")
        if result:
            return result[0]["ID"]
    return None

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
