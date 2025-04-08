from flask import Flask, request
import requests

app = Flask(__name__)

# 🔐 Вебхук Bitrix24
BITRIX_WEBHOOK = 'https://esprings.bitrix24.ru/rest/1/5s5gfz64192lxuyz'

@app.route('/', methods=['POST'])
def wazzup_webhook():
    data = request.json
    print("📬 Вебхук от Wazzup:", data)

    try:
        if 'messages' not in data:
            print("⚠️ Нет входящих сообщений — возможно статус или echo")
            return '', 200

        message = data['messages'][0]
        if message.get('status') != 'inbound':
            print("➡️ Сообщение не входящее, пропускаем")
            return '', 200

        phone = message.get('chatId', '')
        print("📞 Получен номер:", phone)

        # Убираем "7" в начале и оставляем последние 10 цифр
        if phone.startswith("7"):
            phone = phone[1:]
        last_10 = phone[-10:]
        print("📞 Последние 10 цифр номера:", last_10)

        # Пример простого поиска контакта (ограничение 50)
        search_response = requests.post(f'{BITRIX_WEBHOOK}/crm.contact.list', json={
            "filter": {"*PHONE": last_10},
            "select": ["ID", "PHONE"],
            "start": 0
        })
        result = search_response.json()
        contacts = result.get('result', [])
        print(f"📦 Получено {len(contacts)} контактов")
        if not contacts:
            print("❌ Контакт не найден")
            return '', 200

        contact_id = contacts[0]['ID']
        print(f"✅ Контакт найден: {contact_id}")

    except Exception as e:
        print("❗ Ошибка в обработке:", str(e))

    return '', 200

# 🚀 Вспомогательная проверка — вывести все поля сделки
def print_all_deal_fields():
    print("\n🔍 Получение списка всех пользовательских полей сделки...\n")
    response = requests.get(f'{BITRIX_WEBHOOK}/crm.deal.fields')
    fields = response.json().get('result', {})

    for code, info in fields.items():
        if code.startswith("UF_CRM"):
            label = info.get('listLabel') or info.get('formLabel') or info.get('editFormLabel') or "—"
            print(f"{code}: {label}")

# ⚠️ ЭТО ВЫПОЛНИТСЯ ПРИ ЗАПУСКЕ Render
print_all_deal_fields()

if __name__ == '__main__':
    app.run(debug=True)
