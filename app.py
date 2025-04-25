import os
from flask import Flask, request
import requests
from datetime import datetime

app = Flask(__name__)

# Вставляем ссылки на вебхуки
WEBHOOK_URL_CONTACTS = "https://esprings.bitrix24.ru/rest/1/yrad0suj5361davr/"
WEBHOOK_URL_DEALS = "https://esprings.bitrix24.ru/rest/1/ii7i0pazh2ky1nlg/"

# Идентификаторы полей
OUR_LAST_MESSAGE_DATE_FIELD = "UF_CRM_1743763719781"  # Дата нашего последнего сообщения
CLIENT_LAST_REPLY_DATE_FIELD = "UF_CRM_1743763731661"  # Дата последнего ответа клиента

# Стадии
TARGET_STAGE = "3"  # ID стадии "Без ответа"
CURRENT_STAGE = "PREPARATION"  # Текущая стадия сделки ("Стоимость озвучена")

# Параметры времени
DAYS_LIMIT_AFTER_MESSAGE = 10  # Сколько дней ждать ответа от клиента

@app.route("/", methods=["POST"])
def wazzup_webhook():
    data = request.json
    print(f"📬 Вебхук от Wazzup: {data}")

    if "messages" not in data:
        print("❗ Ошибка в обработке: 'messages'")
        return "OK", 200

    message = data["messages"][0]
    if message.get("isEcho") or message.get("status") != "inbound":
        print("➡️ Сообщение не входящее, пропускаем")
        return "OK", 200

    phone_raw = message.get("chatId")
    print(f"📞 Получен номер: {phone_raw}")

    # Генерация вариантов номера
    phone_tail = phone_raw[-10:]
    variants = [
        f"+7{phone_tail}",
        f"+7({phone_tail[:3]}){phone_tail[3:6]}-{phone_tail[6:8]}-{phone_tail[8:]}",
        f"+7 {phone_tail[:3]} {phone_tail[3:6]} {phone_tail[6:8]} {phone_tail[8:]}",
        f"+7-{phone_tail[:3]}-{phone_tail[3:6]}-{phone_tail[6:8]}-{phone_tail[8:]}"
    ]
    print(f"📞 Форматы номера для поиска: {variants}")

    # Поиск контакта
    contact_id = None
    for variant in variants:
        contact_filter = {
            "filter": {"PHONE": variant},
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

    # Поиск сделок в стадии CURRENT_STAGE
    deals_resp = requests.post(f"{WEBHOOK_URL_DEALS}crm.deal.list.json", json={
        "filter": {"CONTACT_ID": contact_id, "STAGE_ID": CURRENT_STAGE},
        "select": ["ID", "STAGE_ID", OUR_LAST_MESSAGE_DATE_FIELD, CLIENT_LAST_REPLY_DATE_FIELD],
        "order": {"ID": "DESC"}
    }).json()

    deals = deals_resp.get("result", [])
    print(f"📦 Найдено сделок в стадии '{CURRENT_STAGE}': {len(deals)}")

    if not deals:
        print("❌ Сделки в нужной стадии не найдены")
        return "OK", 200

    today = datetime.today().strftime("%Y-%m-%d")
    print(f"🕑 Текущая дата: {today}")

    for deal in deals:
        deal_id = deal["ID"]
        print(f"✅ Работаем со сделкой: {deal_id}")

        # 1️⃣ Обновляем дату последнего ответа клиента
        update_resp = requests.post(f"{WEBHOOK_URL_DEALS}crm.deal.update.json", json={
            "id": deal_id,
            "fields": {
                CLIENT_LAST_REPLY_DATE_FIELD: today
            }
        }).json()
        print(f"🛡 Обновили дату последнего ответа клиента для сделки {deal_id}: {update_resp}")

        # 2️⃣ Проверяем: прошло ли 10 дней без ответа клиента
        last_message_date_str = deal.get(OUR_LAST_MESSAGE_DATE_FIELD)
        if not last_message_date_str:
            print(f"⚠️ Нет даты нашего последнего сообщения для сделки {deal_id}")
            continue

        try:
            last_message_date = datetime.strptime(last_message_date_str, "%Y-%m-%d")
        except ValueError:
            print(f"⚠️ Неверный формат даты в поле OUR_LAST_MESSAGE_DATE_FIELD для сделки {deal_id}")
            continue

        days_passed = (datetime.today() - last_message_date).days
        print(f"📅 Прошло дней с последнего сообщения: {days_passed}")

        if days_passed >= DAYS_LIMIT_AFTER_MESSAGE:
            print(f"🔔 Переводим сделку {deal_id} в стадию 'Без ответа'")

            move_resp = requests.post(f"{WEBHOOK_URL_DEALS}crm.deal.update.json", json={
                "id": deal_id,
                "fields": {
                    "STAGE_ID": TARGET_STAGE
                }
            }).json()
            print(f"✅ Сделка {deal_id} переведена в стадию 'Без ответа': {move_resp}")

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
