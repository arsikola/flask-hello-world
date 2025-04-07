from flask import Flask, request
import requests
from datetime import datetime

app = Flask(__name__)

# Твой Bitrix24 вебхук
BITRIX_WEBHOOK = 'https://esprings.bitrix24.ru/rest/1/5s5gfz64192lxuyz'
FIELD_CODE = 'UF_CRM_1743763731661'

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

        # Убираем первую цифру "7", если она есть
        if phone.startswith("7"):
            phone = phone[1:]

        # Извлекаем последние 10 цифр
        last_10_digits = phone[-10:]

        # Поиск контакта по номеру
        contact_search_url = f'{BITRIX_WEBHOOK}/crm.contact.list'
        search_response = requests.post(contact_search_url, json={
            "filter": {
                "*PHONE": last_10_digits  # Ищем по любому типу номера телефона
            },
            "select": ["ID", "PHONE"]
        })

        print("🔍 Ответ на поиск контакта:", search_response.text)
        contact_result = search_response.json()

        if not contact_result.get('result'):
            print("❌ Контакт не найден")
            return '', 200

        contact_id = None
        # Проверяем найденные контакты
        for contact in contact_result.get('result', []):
            phones = contact.get('PHONE', [])
            for phone_entry in phones:
                if last_10_digits in phone_entry.get('VALUE', ''):
                    contact_id = contact['ID']
                    print("✅ Контакт найден:", contact_id)
                    break
            if contact_id:
                break

        if not contact_id:
            print("❌ Контакт не найден")
            return '', 200

        # Ищем сделку по контакту
        deal_search_url = f'{BITRIX_WEBHOOK}/crm.deal.list'
        deal_response = requests.post(deal_search_url, json={
            "filter": {
                "CONTACT_ID": contact_id
            },
            "select": ["ID"]
        })

        print("🔍 Ответ на поиск сделки:", deal_response.text)
        deal_result = deal_response.json().get('result', [])
        if not deal_result:
            print("❌ Сделки не найдены")
            return '', 200

        # Возьмем первую сделку из списка
        deal_id = deal_result[0]['ID']
        print("✅ Сделка найдена:", deal_id)

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
