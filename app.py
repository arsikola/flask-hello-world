from flask import Flask, request
import requests
from datetime import datetime

app = Flask(__name__)

# 🔑 Твой вебхук Bitrix24
BITRIX_WEBHOOK = 'https://esprings.bitrix24.ru/rest/1/5s5gfz64192lxuyz/'  # ← замени на свой!

# Код пользовательского поля "Дата ответа клиента"
FIELD_CODE = 'UF_CRM_1743763731661'

@app.route('/', methods=['POST'])
def wazzup_webhook():
    data = request.json
    print("📬 Вебхук от Wazzup:", data)

    try:
        message = data['messages'][0]
        if message['status'] != 'inbound':
            return '', 200  # Игнорируем исходящие

        phone = message['chatId']  # Номер клиента
        phone = phone[-10:]  # Приводим к формату 9XXXXXXXXX

        # 1. Ищем контакт по телефону
        search_url = f'{BITRIX_WEBHOOK}/crm.contact.list'
        response = requests.post(search_url, json={
            "filter": {"PHONE": phone},
            "select": ["ID"]
        })
        contact_result = response.json()
        if not contact_result['result']:
            print("❌ Контакт не найден")
            return '', 200

        contact_id = contact_result['result'][0]['ID']

        # 2. Ищем сделку по контакту
        deal_url = f'{BITRIX_WEBHOOK}/crm.deal.list'
        response = requests.post(deal_url, json={
            "filter": {"CONTACT_ID": contact_id},
            "select": ["ID"]
        })
        deals = response.json().get('result', [])
        if not deals:
            print("❌ Сделки не найдены")
            return '', 200

        # 3. Обновляем последнюю сделку
        deal_id = deals[0]['ID']
        now = datetime.now().strftime('%Y-%m-%d')
        update_url = f'{BITRIX_WEBHOOK}/crm.deal.update'
        requests.post(update_url, json={
            "id": deal_id,
            "fields": {
                FIELD_CODE: now
            }
        })

        print(f"✅ Обновлена сделка {deal_id}, дата ответа клиента: {now}")
    except Exception as e:
        print("❗ Ошибка:", e)

    return '', 200

@app.route('/', methods=['GET'])
def index():
    return 'Сервер работает! ✅', 200
