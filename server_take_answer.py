# server.py
import os
import json
import logging
import sqlite3
from flask import Flask, request
from google_auth_oauthlib.flow import Flow

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CLIENT_SECRETS_FILE = 'client_secret3.json'
DB_FILE = 'users.db'

app = Flask(__name__)

# Функции для работы с базой данных
def save_credentials(user_id, account_id, credentials):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users_accounts (user_id, account_id, credentials)
        VALUES (?, ?, ?)
    ''', (user_id, account_id, json.dumps(credentials)))
    conn.commit()
    conn.close()

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users_accounts (
            user_id INTEGER,
            account_id TEXT,
            credentials TEXT,
            PRIMARY KEY (user_id, account_id)
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/oauth2callback')
def oauth2callback():
    state = request.args.get('state')
    code = request.args.get('code')

    if not state or not code:
        logger.error("Некорректный запрос: отсутствует state или code.")
        return "Некорректный запрос.", 400

    user_id = state  # Предполагается, что state содержит user_id

    logger.info(f"Получен запрос авторизации от пользователя: {user_id}")

    try:
        # Используем фиксированный Redirect URI
        fixed_redirect_uri = 'https://da59-5-34-215-156.ngrok-free.app/oauth2callback'

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=fixed_redirect_uri
        )
        logger.info(f"Создан Flow с redirect_uri: {flow.redirect_uri}")
        flow.fetch_token(code=code)

        credentials = flow.credentials
        account_id = credentials.token  # Используем токен как уникальный идентификатор аккаунта

        creds_dict = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }

        save_credentials(int(user_id), account_id, creds_dict)

        logger.info(f"Авторизация завершена для пользователя: {user_id}")

        return "Авторизация прошла успешно! Вы можете закрыть это окно и вернуться в Telegram."
    except Exception as e:
        logger.error(f"Ошибка при обработке авторизации: {e}")
        return "Произошла ошибка при авторизации.", 500

if __name__ == '__main__':
    # Инициализация базы данных
    init_db()

    # Запуск Flask-сервера
    app.run(host='0.0.0.0', port=5000)
