import requests
from flask import Flask, jsonify

# Создаём приложение Flask
app = Flask(__name__)

# Указываем URL Bitrix24 API
WEBHOOK_URL = 'https://your-bitrix24-domain.bitrix24.ru/rest/1/your-webhook-id'  # Заменить на свой URL

@app.route("/stages", methods=["GET"])
def get_deal_stages():
    url = f"{WEBHOOK_URL}/crm.status.list.json"
    payload = {
        "filter": {
            "ENTITY_ID": "DEAL_STAGE"
        }
    }

    resp = requests.post(url, json=payload).json()
    stages = resp.get("result", [])

    print("📋 Все стадии сделок:")
    for stage in stages:
        print(f"{stage['NAME']} → {stage['STATUS_ID']}")

    return jsonify({"stages": stages}), 200
