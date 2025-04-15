import os
from flask import Flask, request, jsonify
import requests
from datetime import datetime

app = Flask(__name__)
WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL")
FIELD_CODE = "UF_CRM_1743763731661"  # Дата последнего ответа клиента

@app.route("/", methods=["POST"])
def wazzup_webhook():
    data = request.json
    print(f"📬 Вебхук от Wazzup: {data}")

    # Обработка только входящих сообщений
    if "messages" not in data:
        print("❗ Ошибка в обработке: 'messages'")
        return "OK", 200

    message = data["messages"][0]
    if message.get("isEcho") or message.get("status") != "inbound":
        print("➡️ Сообщение не входящее, пропускаем")
        return "OK", 200

    phone_raw = message.get("chatId")
    print(f"📞 Получен номер: {phone_raw}")

    # Генерация форматов телефона
    phone_tail = phone_raw[-10:]
    variants = [
        f"+7{phone_tail}",
        f"+7({phone_tail[:3]}){phone_tail[3:6]}-{phone_tail[6:8]}-{phone_tail[8:]}",
        f"+7 {phone_tail[:3]} {phone_tail[3:6]} {phone_tail[6:8]} {phone_tail[8:]}",
        f"+7-{phone_tail[:3]}-{phone_tail[3:6]}-{phone_tail[6:8]}-{phone_tail[8:]}"
    ]
    print(f"📞 Форматы номера для поиска: {variants}")

    # Поиск контакта по всем вариантам
    contact_id = None
    for variant in variants:
        contact_filter = {
            "filter": {
                "PHONE": variant
            },
            "select": ["ID", "PHONE"]
        }
        contact_url = f"{WEBHOOK_URL}/crm.contact.list.json"
        contact_resp = requests.post(contact_url, json=contact_filter).json()
        print(f"🔍 Ответ на поиск контакта по {variant}: {contact_resp}")

        result = contact_resp.get("result", [])
        for contact in result:
            phones = contact.get("PHONE", [])
            for phone in phones:
                if phone.get("VALUE") == variant:
                    contact_id = contact["ID"]
                    break
            if contact_id:
                break
        if contact_id:
            break

    if not contact_id:
        print("❌ Контакт не найден")
        return "OK", 200

    print(f"✅ Контакт найден: {contact_id}")

    # Поиск сделок по контакту
    deals_url = f"{WEBHOOK_URL}/crm.deal.list.json"
    deals_resp = requests.post(deals_url, json={
        "filter": {"CONTACT_ID": contact_id},
        "select": ["ID"],
        "order": {"ID": "DESC"}
    }).json()

    deals = deals_resp.get("result", [])
    print(f"📦 Найдено сделок: {len(deals)}")

    if not deals:
        print("❌ Сделки не найдены")
        return "OK", 200

    deal_id = deals[0]["ID"]
    print(f"✅ Сделка найдена: {deal_id}")

    # Обновляем поле
    today = datetime.today().strftime("%Y-%m-%d")
    print(f"🛠 Обновляем поле {FIELD_CODE} на значение {today}")

    update_url = f"{WEBHOOK_URL}/crm.deal.update.json"
    update_resp = requests.post(update_url, json={
        "id": deal_id,
        "fields": {
            FIELD_CODE: today
        }
    }).json()
    print(f"🛡 Сделка обновлена: {update_resp}")

    return "OK", 200


# 🔍 Новый эндпоинт для получения всех стадий сделок
@app.route("/stages", methods=["GET"])
def get_deal_stages():
    status_url = f"{WEBHOOK_URL}/crm.status.list.json"
    payload = {
        "filter": {
            "ENTITY_ID": "DEAL_STAGE"
        }
