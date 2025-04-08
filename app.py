from flask import Flask, request 
import requests
from datetime import datetime
import re

app = Flask(__name__)

# Твой Bitrix24 вебхук
BITRIX_WEBHOOK = 'https://esprings.bitrix24.ru/rest/1/5s5gfz64192lxuyz'
FIELD_CODE = 'UF_CRM_1743763731661'

# Функция нормализации телефона
def normalize_phone(phone):
    return re.sub(r'\D', '', phone)[-10:]

@app.route('/', methods=['POST'])
def wazzup_webhook():
    data = request.json
    print("📬 Вебхук от Wazzup:", data)

    try:
        # Обрабатываем только если есть входящее сообщение
        if 'messages' not in data or not data['messages']:
            print("⚠️ Нет входящих сообщений — возможно статус или echo")
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

        # Поиск контакта по всем страницам
        contact_id = None
        start = 0
        while True:
            contact_search_url = f'{BITRIX_WEBHOOK}/crm.contact.list'
            response = requests.post(contact_search_url, json={
                "select": ["ID", "PHONE"],
                "filter": {
                    "!PHONE": ""
                },
                "start": start
            })

            result = response.json()
            contacts = result.get('result', [])
            if not contacts:
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

        if not contact_id:
            print("❌ Контакт не найден")
            return '', 200

        # Поиск последних активных сделок
        deal_search_url = f'{BITRIX_WEBHOOK}/crm.deal.list'
        deal_response = requests.post(deal_search_url, json={
            "filter": {
                "CONTACT_ID": contact_id,
                "!STAGE_SEMANTIC_ID": "F"  # Исключаем завершённые сделки
            },
            "select": ["ID", "DATE_CREATE"],
            "order": {
                "DATE_CREATE": "DESC"  # Сортируем по дате создания
            }
        })

        deal_result = deal_response.json().get('result', [])
        if not deal_result:
            print("❌ Активные сделки не найдены")
            return '', 200

        deal_id = deal_result[0]['ID']
        print(f"✅ Последняя активная сделка найдена: {deal_id}")

        # Обновляем сделку
        now = datetime.now().strftime('%Y-%m-%d')
        update_url = f'{BITRIX_WEBHOOK}/crm.deal.update'
        update_response = requests.post(update_url, json={
            "id": deal_id,
            "fields": {
                FIELD_CODE: now
            }
        })

        print("📝 Ответ на обновление сделки:", update_response.text)

    except Exception as e:
        print("❗ Ошибка в обработке:", str(e))

    return '', 200

if __name__ == '__main__':
    app.run(debug=True)
