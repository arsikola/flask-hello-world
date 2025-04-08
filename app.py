from flask import Flask, request 
import requests
from datetime import datetime
import re
import time
import traceback

app = Flask(__name__)

BITRIX_WEBHOOK = 'https://esprings.bitrix24.ru/rest/1/5s5gfz64192lxuyz'
FIELD_CODE = 'UF_CRM_1743763731661'
MAX_PAGES = 3000

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
        pages_checked = 0

        while pages_checked < MAX_PAGES:
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

                if response.status_code != 200:
                    print(f"❌ HTTP {response.status_code} от Bitrix")
                    print("📄 Ответ:", response.text)
                    return '', 200

                try:
                    result = response.json()
                except Exception as e:
                    print(f"❌ Ошибка JSON: {e}")
                    print("📄 Ответ Bitrix:", response.text)
                    return '', 200

                if "result" not in result or not isinstance(result["result"], list):
                    print(f"⚠️ Невалидный формат ответа на странице {start}:")
                    print(result)
                    return '', 200

                contacts = result["result"]
                print(f"📦 Получено {len(contacts)} контактов")

                if not contacts:
                    print(f"⛔ Контакты закончились на странице {start}")
                    break

                for contact in contacts:
                    for phone_entry in contact.get('PHONE', []):
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
                pages_checked += 1
                time.sleep(0.3)

            except Exception:
                print("❗ Исключение в цикле поиска контактов:")
                traceback.print_exc()
                return '', 200

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
                return '', 200

            deal_result = deal_response.json().get('result', [])
        except Exception:
            print("❗ Ошибка при получении сделок:")
            traceback.print_exc()
            return '', 200

        if not deal_result:
            print("❌ Активные сделки не найдены")
            return '', 200

        deal_id = deal_result[0]['ID']
        print(f"✅ Последняя активная сделка найдена: {deal_id}")

        now = datetime.now().strftime('%Y-%m-%d')

        try:
            print(f"🛡 Обновляем сделку {deal_id}, только поле {FIELD_CODE} = {now}")
            update_url = f'{BITRIX_WEBHOOK}/crm.deal.update'
            update_response = requests.post(update_url, json={
                "id": deal_id,
                "fields": {
                    FIELD_CODE: now
                }
            }, timeout=30)

            if update_response.status_code != 200:
                print(f"❌ Ошибка HTTP при обновлении сделки: {update_response.status_code}")
                print("📄 Ответ:", update_response.text)
                return '', 200

            print("🛡 Сделка обновлена без изменений стадии")
        except Exception:
            print("❗ Ошибка при обновлении сделки:")
            traceback.print_exc()
            return '', 200

    except Exception:
        print("❗ Общая ошибка в верхнем уровне:")
        traceback.print_exc()
        return '', 200

    return '', 200

if __name__ == '__main__':
    app.run(debug=True)
