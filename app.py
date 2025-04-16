import os
from flask import Flask, request
import requests
from datetime import datetime

app = Flask(__name__)

# Вставляем ссылки на вебхуки
WEBHOOK_URL_CONTACTS = "https://esprings.bitrix24.ru/rest/1/yrad0suj5361davr/"  # Вебхук для crm.contact.list
WEBHOOK_URL_DEALS = "https://esprings.bitrix24.ru/rest/1/ii7i0pazh2ky1nlg/"  # Вебхук для crm.deal.list и crm.deal.update

# Идентификаторы полей
OUR_LAST_MESSAGE_DATE_FIELD = "UF_CRM_1743763719781"  # Дата нашего последнего сообщения
CLIENT_LAST_REPLY_DATE_FIELD = "UF_CRM_1743763731661"  # Дата последнего ответа клиента

# Стадии
TARGET_STAGE = "3"  # Стадия "Без ответа" (ID: 3)
CURRENT_STAGE = "PREPARATION"  # Стадия "Стоимость озвучена"

# Параметры времени
DAYS_LIMIT_AFTER_MESSAGE = 10  # Если не было ответа через 10 дней после нашего последнего сообщения

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

    # Поиск сделок по контакту в стадии "PREPARATION"
    deals_url = f"{WEBHOOK_URL_DEALS}crm.deal.list.json"
    deals_resp = requests.post(deals_url, json={
        "filter": {"CONTACT_ID": contact_id, "STAGE_ID": "PREPARATION"},  # Фильтруем по стадии "PREPARATION"
        "select": ["ID", "STAGE_ID", OUR_LAST_MESSAGE_DATE_FIELD, CLIENT_LAST_REPLY_DATE_FIELD],  # Получаем ID и даты
        "order": {"ID": "DESC"}
    }).json()

    deals = deals_resp.get("result", [])
    print(f"📦 Найдено сделок в стадии 'PREPARATION': {len(deals)}")

    if not deals:
        print("❌ Сделки в стадии 'PREPARATION' не найдены")
        return "OK", 200

    # Текущая дата
    today = datetime.today().strftime("%Y-%m-%d")
    
    # Обновляем поле "Дата последнего сообщения" для каждой найденной сделки
    for deal in deals:
        deal_id = deal["ID"]
        print(f"✅ Сделка найдена: {deal_id}")

        # Получаем дату нашего последнего сообщения
        last_message_date_str = deal.get(OUR_LAST_MESSAGE_DATE_FIELD)
        if not last_message_date_str:
            continue  # Если поле пустое — неизвестно когда было сообщение

        last_message_date = datetime.strptime(last_message_date_str, "%Y-%m-%d")

        # Проверка, прошло ли 10 дней с момента нашего последнего сообщения
        if (datetime.today() - last_message_date).days >= DAYS_LIMIT_AFTER_MESSAGE:
            print(f"✅ Сделка {deal_id} молчит уже {DAYS_LIMIT_AFTER_MESSAGE} дней после нашего сообщения.")
            
            # Получаем все входящие сообщения от клиента
            messages_resp = requests.post(f"{WEBHOOK_URL_DEALS}crm.activity.list.json", json={
                "filter": {"DEAL_ID": deal_id},
                "order": {"ID": "DESC"},
                "select": ["ID", "COMMENT", "TYPE_ID"]
            }).json()

            messages = messages_resp.get("result", [])
            client_replied = False

            # Проверяем, есть ли входящее сообщение от клиента
            for message in messages:
                if message["TYPE_ID"] == "INCOMING" and message.get("COMMENT", "").strip():
                    client_replied = True
                    break  # Если найдено входящее сообщение от клиента, прекращаем поиск

            # Если нет входящего сообщения от клиента
            if not client_replied:
                print(f"🔕 Сделка {deal_id} не получила ответа от клиента за 10 дней, переводим в стадию 'Без ответа'...")

                # Перемещаем сделку в стадию "Без ответа" (ID: 3)
                update_resp = requests.post(f"{WEBHOOK_URL_DEALS}crm.deal.update.json", json={
                    "id": deal_id,
                    "fields": {
                        "STAGE_ID": TARGET_STAGE  # ID стадии "Без ответа"
                    }
                }).json()
                print(f"✅ Сделка {deal_id} перемещена в стадию 'Без ответа'.")
            else:
                print(f"💬 Сделка {deal_id} ожидает ответа клиента или уже был ответ.")
        
        # Обновляем поле "Дата последнего сообщения"
        update_url = f"{WEBHOOK_URL_DEALS}crm.deal.update.json"
        update_resp = requests.post(update_url, json={
            "id": deal_id,
            "fields": {
                OUR_LAST_MESSAGE_DATE_FIELD: today  # Устанавливаем текущую дату в поле "Дата последнего сообщения"
            }
        }).json()
        print(f"🛡 Сделка обновлена: {update_resp}")

    return "OK", 200
