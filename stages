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

    return {"stages": stages}, 200
