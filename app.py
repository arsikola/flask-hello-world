from flask import Flask, request
import requests
from datetime import datetime

app = Flask(__name__)

# Твой Bitrix24 вебхук
BITRIX_WEBHOOK = 'https://esprings.bitrix24.ru/rest/1/5s5gfz64192lxuyz'

# ✅ Код поля: Дата последнего ответа клиента
FIELD_CODE = 'UF_CRM_1743763731661'

@app.route('/', methods=['POST'])
def wazzup_webhook():
    data = request.json
    print("📬 Вебхук от Wazzup:", data)

    try:
        # Проверяем наличие сообщений
        if 'messages' not in data:
            print("⚠️ Нет входящих сообщений — возможно статус или echo")
            return '', 200

        message = data['messages'][0]

        # Обрабатываем только входящие сообщения
        if message.get('status') != 'inbound':
            print("➡️ Сообщение не входящее, пропускаем")
            return '', 200

        # Получаем номер
        phone = message.get('chatId', '')
        print("📞 Получен номер:", phone)

        if phone.startswith("7"):
            phone = phone[1:]
        last_10_digits = phone[-10:]
        print(f"📞 Последние 10 цифр номера: {last_10_digits}")

        # Поиск контакта по номеру
        contact_search_url = f'{BITRIX_WEBHOOK}/crm.contact.list'
        contact_response = requests.post(contact_search_url, json={
            "filter": {
                "*PHONE": last_10_digits
            },
            "select": ["ID"],
            "start": 0
        })
        contacts = contact_response.json().get('result', [])
        print(f"📦 Получено {len(contacts)} контактов")

        if not contacts:
            print("❌ Контакт не найден")
            return '', 200

        contact_id = contacts[0]['ID']
        print(f"✅ Контакт найден: {contact_id}")

        # Поиск сделок по контакту
        deal_search_url = f'{BITRIX_WEBHOOK}/crm.deal.list'
        deal_response = requests.post(deal_search_url, json={
            "filter": {
                "CONTACT_ID": contact_id
            },
            "select": ["ID"],
            "order": {"DATE_CREATE": "DESC"}
        })
        deals = deal_response.json().get('result', [])
        print(f"📦 Найдено сделок: {len(deals)}")

        if not deals:
            print("❌ Сделки не найдены")
            return '', 200

        # Берём самую свежую сделку
        deal_id = deals[0]['ID']
        print(f"✅ Сделка найдена: {deal_id}")

        # Обновляем поле "Дата последнего ответа клиента"
        now = datetime.now().strftime('%Y-%m-%d')
        update_url = f'{BITRIX_WEBHOOK}/crm.deal.update'
        update_response = requests.post(update_url, json={
            "id": deal_id,
            "fields": {
                FIELD_CODE: now
            }
        })

        print(f"🛠 Обновляем поле {FIELD
