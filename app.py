from flask import Flask, request

app = Flask(__name__)

@app.route('/', methods=['POST'])
def wazzup_webhook():
    data = request.json
    print("📬 Вебхук от Wazzup:")
    print(data)
    return '', 200

@app.route('/', methods=['GET'])
def index():
    return '✅ Сервер работает!', 200
