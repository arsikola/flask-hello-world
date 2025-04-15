import os
from flask import Flask, request
import requests
from datetime import datetime

app = Flask(__name__)

# Вставляем ссылки на вебхуки
WEBHOOK_URL_CONTACTS = "https://esprings.bitrix24.ru/rest/1/yrad0suj5361davr/"  # Вебхук для crm.contact.list
WEBHOOK_URL_DEALS = "https://esprings.bitrix24.ru/rest/1/ii7i0pazh2ky1nlg/"  # Вебхук для crm.deal.list и crm.deal.update

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
        contact_resp = requests.post(f"{WEBHOOK_URL_CONTACTS}crm.contact.list.json", json=contact_filter).json()
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
    deals_url = f"{WEBHOOK_URL_DEALS}crm.deal.list.json"
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

    }).json()
    print(f"🛡 Сделка обновлена: {update_resp}")

    return "OK", 200
