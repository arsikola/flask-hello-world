import requests

# Вебхук Bitrix24
BITRIX_WEBHOOK = 'https://esprings.bitrix24.ru/rest/1/5s5gfz64192lxuyz'

# Тестовое обновление только одного поля
response = requests.post(f'{BITRIX_WEBHOOK}/crm.deal.update', json={
    "id": 60417,  # ID нужной сделки
    "fields": {
        "UF_CRM_1743763731661": "2025-01-01"  # Тестовое значение
    }
})

print("📬 Ответ от Bitrix:", response.json())
