if __name__ == '__main__':
    # ====== ТЕСТОВОЕ ОБНОВЛЕНИЕ ОДНОЙ СДЕЛКИ ======
    import requests
    from datetime import datetime

    BITRIX_WEBHOOK = 'https://esprings.bitrix24.ru/rest/1/5s5gfz64192lxuyz'
    DEAL_ID = 91771  # замени на ID нужной сделки
    FIELD_CODE = ''
    TEST_DATE = '2025-01-01'

    response = requests.post(f'{BITRIX_WEBHOOK}/crm.deal.update', json={
        "id": DEAL_ID,
        "fields": {
            FIELD_CODE: TEST_DATE
        }
    })

    print("🔄 Ответ от Bitrix:", response.json())

    # ====== (опционально) запустить сервер, если нужен ======
    # app.run(debug=True)
