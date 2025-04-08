from flask import Flask, request
import requests
from datetime import datetime
import re

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
        message = data['messages'][0]
        if message.get('status') != 'inbound':
            print("➡️ Сообщение не входящее, пропускаем")
            return '', 200

        phone = message.get('chatId', '')
        print("📞 Получен номер:", phone)

        if phone.startswith("7"):
            phone = phone[1:]

        last_10_digits = normalize_phone(phone)
        print(f"📞 Последние 10 цифр номера: {last_10_digits}")

        # Получаем первые 50 контактов (пока без start)
        contact_search_url = f'{BITRIX_WEBHOOK}/crm.contact.list'
        search_response = requests.post(contact_search_url, json={
            "select": ["ID", "PHONE"],
            "filter": {"!PHONE": ""}
        })

        contact_result = search_response.json()
        contacts = contact_result.get('result', [])
        print(f"📦 Получено {len(contacts)} контактов")

        contact_id = None

        # Поиск номера вручную
        for contact in contacts:
            for phone_entry in contact.get('PHONE', []):
                stored = normalize_phone(phone_entry.get('VALUE', ''))
                if stored == last_10_digits:
                    contact_id = contact['ID']
                    print(f"✅ Контакт найден: {contact_id}")
                    break
            if contact_id:
                break

        if not contact_id:
            print("❌ Контакт не найден")
            return '', 200

        # Ищем последнюю сделку
        deal_search_url = f'{BITRIX_WEBHOOK}/crm.deal.list'
        deal_response = requests.post(deal_search_url, json={
            "filter": {
                "CONTACT_ID": contact_id
            },
            "select": ["ID", "DATE_CREATE"],
            "order": {
                "DATE_CREATE": "DESC"
            }
        })

        deals = deal_response.json().get('result', [])
        if not deals:
            print("❌ Сделки не найдены")
            return '', 200

        deal_id = deals[0]['ID']
        print(f"✅ Сделка найдена: {deal_id}")

        # Обновляем ТОЛЬКО пользовательское поле
        now = datetime.now().strftime('%Y-%m-%d')
        update_url = f'{BITRIX_WEBHOOK}/crm.deal.update'
        update_response = requests.post(update_url, json={
            "id": deal_id,
            "fields": {
                FIELD_CODE: now
            }
        })

        print("🛡 Обновлено только поле:", update_response.text)

    except Exception as e:
        print("❗ Ошибка в обработке:", str(e))

    return '', 200

if __name__ == '__main__':
    app.run(debug=True)
