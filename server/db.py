import sqlite3
import json
from config import DB_FILE

def init_db():
    """Создает таблицы в базе данных, если они отсутствуют."""
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

def save_credentials(user_id, account_id, credentials):
    """Сохраняет учетные данные пользователя в базу данных."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users_accounts (user_id, account_id, credentials)
        VALUES (?, ?, ?)
    ''', (user_id, account_id, json.dumps(credentials)))
    conn.commit()
    conn.close()
