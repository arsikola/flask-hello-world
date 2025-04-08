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
        if message['status'] != 'inbound':
            print("➡️ Сообщение не входящее, пропускаем")
            return '', 200

        phone = message['chatId']
        print("📞 Получен номер:", phone)

        if phone.startswith("7"):
            phone = phone[1:]

        last_10_digits = normalize_phone(phone)
        print(f"📞 Последние 10 цифр номера: {last_10_digits}")

        # Поиск контакта по номеру (без перебора страниц)
        contact_search_url = f'{BITRIX_WEBHOOK}/crm.contact.list'
        search_response = requests.post(contact_search_url, json={
            "filter": {
                "*PHONE": last_10_digits
            },
            "select": ["ID"]
        })

        contact_result = search_response.json()
        print("🔍 Ответ на поиск контакта:", contact_result)

        if not contact_result.get('result'):
            print("❌ Контакт не найден")
            return '', 200

        contact_id = contact_result['result'][0]['ID']
        print(f"✅ Контакт найден: {contact_id}")

        # Поиск сделки по контакту (первая попавшаяся)
        deal_search_url = f'{BITRIX_WEBHOOK}/crm.deal.list'
        deal_response = requests.post(deal_search_url, json={
            "filter": {
                "CONTACT_ID": contact_id
            },
            "select": ["ID"],
            "order": {
                "DATE_CREATE": "DESC"
            }
        })

        deal_result = deal_response.json().get('result', [])
        print("🔍 Ответ на поиск сделки:", deal_result)

        if not deal_result:
            print("❌ Сделки не найдены")
            return '', 200

        deal_id = deal_result[0]['ID']
        print(f"✅ Сделка найдена: {deal_id}")

        # Обновляем только нужное поле
        now = datetime.now().strftime('%Y-%m-%d')
        update_url = f'{BITRIX_WEBHOOK}/crm.deal.update'
        update_response = requests.post(update_url, json={
            "id": deal_id,
            "fields": {
                FIELD_CODE: now
            }
        })

        print("🛡 Сделка обновлена:", update_response.text)

    except Exception as e:
        print("❗ Ошибка в обработке:", str(e))

    return '', 200

if __name__ == '__main__':
    app.run(debug=True)
