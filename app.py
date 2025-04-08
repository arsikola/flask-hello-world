from flask import Flask, request 
import requests
from datetime import datetime
import re
import time

app = Flask(__name__)

BITRIX_WEBHOOK = 'https://esprings.bitrix24.ru/rest/1/5s5gfz64192lxuyz'
FIELD_CODE = 'UF_CRM_1743763731661'

def normalize_phone(phone):
    return re.sub(r'\D', '', phone)[-10:]

@app.route('/', methods=['POST'])
def wazzup_webhook():
    data = request.json
    print("📬 Вебхук от Wazzup:", data)

    try:
        if 'messages' not in data or not data['messages']:
            print("⚠️ Нет входящих сообщений — возможно echo или статус")
            return '', 200

        message = data['messages'][0]
        if message.get('status') != 'inbound':
            print("➡️ Сообщение не входящее, пропускаем")
            return '', 200

        phone = message['chatId']
        print("📞 Получен номер:", phone)

        if phone.startswith("7"):
            phone = phone[1:]

        last_10_digits = normalize_phone(phone)
        print(f"📞 Последние 10 цифр номера: {last_10_digits}")

        contact_id = None
        start = 0

        while True:
            print(f"🔁 Поиск контактов, страница start={start}")
            contact_search_url = f'{BITRIX_WEBHOOK}/crm.contact.list'
            try:
                response = requests.post(contact_search_url, json={
                    "select": ["ID", "PHONE"],
                    "filter": {
                        "!PHONE": ""
                    },
                    "start": start
                }, timeout=30)
            except requests.exceptions.RequestException as e:
                print(f"❌ Ошибка запроса к Bitrix (контакты): {e}")
                return '', 500

            # Проверяем статус ответа
            if response.status_code != 200:
                print(f"❌ Неверный HTTP-ответ от Bitrix на странице {start}: {response.status_code}")
                print("📄 Ответ:", response.text)
                return '', 500

            # Пробуем разобрать JSON
            try:
                result = response.json()
            except Exception as e:
                print(f"❌ Ошибка разбора JSON на странице {start}: {e}")
                print("📄 Ответ Bitrix:", response.text)
                return '', 500

            contacts = result.get('result', [])
            print(f"📦 Получено {len(contacts)} контактов")

            if not contacts:
                print(f"⛔ Пустая страница — контакты закончились на start={start}")
                break

            for contact in contacts:
                phones = contact.get('PHONE', [])
                for phone_entry in phones:
                    stored_number = normalize_phone(phone_entry['VALUE'])
                    if stored_number == last_10_digits:
                        contact_id = contact['ID']
                        print(f"✅ Контакт найден: {contact_id}")
                        break
                if contact_id:
                    break

            if contact_id or 'next' not in result:
                break

            start = result['next']
            time.sleep(0.3)

        if not contact_id:
            print("❌ Контакт не найден")
            return '', 200

        try:
            print("🔍 Поиск активных сделок")
            deal_search_url = f'{BITRIX_WEBHOOK}/crm.deal.list'
            deal_response = requests.post(deal_search_url, json={
                "filter": {
                    "CONTACT_ID": contact_id,
                    "!STAGE_SEMANTIC_ID": "F"
                },
                "select": ["ID", "DATE_CREATE"],
                "order": {
                    "DATE_CREATE": "DESC"
                }
            }, timeout=30)

            if deal_response.status_code != 200:
                print(f"❌ Ошибка HTTP при получении сделок: {deal_response.status_code}")
                print("📄 Ответ:", deal_response.text)
                return '', 500

            deal_result = deal_response.json().get('result', [])
        except
