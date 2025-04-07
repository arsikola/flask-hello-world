from flask import Flask, request

app = Flask(__name__)

@app.route('/', methods=['POST'])
def wazzup_webhook():
    print("✅ Получен вебхук от Wazzup:")
    print(request.json)  # Печать тела запроса в лог
    return '', 200  # <-- Обязательно возвращаем 200 OK

@app.route('/', methods=['GET'])
def index():
    return 'Flask-сервер работает! 🚀'
