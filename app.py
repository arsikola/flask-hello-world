from flask import Flask, request
import requests

app = Flask(__name__)

BITRIX_WEBHOOK = 'https://esprings.bitrix24.ru/rest/1/5s5gfz64192lxuyz'

@app.route('/fields', methods=['GET'])
def get_fields():
    response = requests.get(f'{BITRIX_WEBHOOK}/crm.deal.fields')
    fields = response.json().get('result', {})

    result_lines = []
    for code, info in fields.items():
        if code.startswith("UF_CRM"):
            label = info.get('listLabel') or info.get('formLabel') or info.get('editFormLabel') or "—"
            result_lines.append(f"{code}: {label}")
    
    result_text = "\n".join(result_lines)
    print("📋 Список пользовательских полей:\n" + result_text)
    return f"<pre>{result_text}</pre>"

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

        if phone.startswith("7"):
            phone = phone[1:]
        last_10 = phone[-10:]
        print("📞 Последние 10 цифр номера:", last_10)

        contact_search = requests.post(f'{BITRIX_WEBHOOK}/crm.contact.list', json={
            "filter": {"*PHONE": last_10},
            "select": ["ID", "PHONE"],
            "start": 0
        })

        contacts = contact_search.json().get('result', [])
        print(f"📦 Получено {len(contacts)} контактов")
        if not contacts:
            print("❌ Контакт не найден")
            return '', 200

        contact_id = contacts[0]['ID']
        print(f"✅ Контакт найден: {contact_id}")

    except Exception as e:
        print("❗ Ошибка в обработке:", str(e))

    return '', 200

if __name__ == '__main__':
    app.run(debug=True)
