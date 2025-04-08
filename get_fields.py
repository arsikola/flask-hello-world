import requests

# 🔐 Укажи свой Bitrix24 вебхук
BITRIX_WEBHOOK = 'https://esprings.bitrix24.ru/rest/1/5s5gfz64192lxuyz'

# 🔎 Получаем список всех полей сделки
response = requests.get(f'{BITRIX_WEBHOOK}/crm.deal.fields')

fields = response.json().get('result', {})

print("\n📋 Пользовательские поля сделки:")
print("----------------------------------")

for code, info in fields.items():
    if code.startswith("UF_CRM"):
        label = info.get('listLabel') or info.get('formLabel') or info.get('editFormLabel') or '—'
        print(f"{code}: {label}")
