from flask import Flask, request 
import requests
from datetime import datetime
import re
import time

app = Flask(__name__)

# Bitrix24 вебхук и поле
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

        # Поиск контакта с логами и паузой
        contact_id = None
        start = 0

        while True:
            try:
                print(f"🔁 Поиск контактов, страница start={start}")
                contact_search_url = f'{BITRIX_WEBHOOK}/crm.contact.list'
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

            result = response.json()
            contacts = result.get('result', [])
            print(f"📦 Получено {len(contacts)} контактов")

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
            time.sleep(0.3)

        if not contact_id:
            print("❌ Контакт не найден")
            return '', 200

        # Поиск последней активной сделки
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
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка запроса к Bitrix (сделки): {e}")
            return '', 500

        deal_result = deal_response.json().get('result', [])
        if not deal_result:
            print("❌ Активные сделки не найдены")
            return '', 200

        deal_id = deal_result[0]['ID']
        print(f"✅ Последняя активная сделка найдена: {deal_id}")

        # Обновляем сделку
        now = datetime.now().strftime('%Y-%m-%d')
        try:
            print(f"📝 Обновление сделки ID {deal_id} полем {FIELD_CODE} = {now}")
            update_url = f'{BITRIX_WEBHOOK}/crm.deal.update'
            update_response = requests.post(update_url, json={
                "id": deal_id,
                "fields": {
                    FIELD_CODE: now
                }
            }, timeout=30)

            print("📝 Ответ от Bitrix:", update_response.text)
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка при обновлении сделки: {e}")
            return '', 500

    except Exception as e:
        print("❗ Общая ошибка обработки:", str(e))
        return '', 500

    return '', 200

if __name__ == '__main__':
    app.run(debug=True)
