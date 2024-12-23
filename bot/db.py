import sqlite3
import json

DB_FILE = 'users.db'

def init_db():
    """Создает таблицу для хранения учетных данных пользователей, если она не существует."""
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

def get_credentials(user_id, account_id):
    """Получает учетные данные для конкретного пользователя и аккаунта."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT credentials FROM users_accounts
        WHERE user_id = ? AND account_id = ?
    ''', (user_id, account_id))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None

def get_user_accounts(user_id):
    """Получает список всех аккаунтов, связанных с пользователем."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT account_id FROM users_accounts
        WHERE user_id = ?
    ''', (user_id,))
    accounts = cursor.fetchall()
    conn.close()
    return [acc[0] for acc in accounts]

def save_user_filters(user_id, filters):
    """Сохраняет список ключевых фраз пользователя в базу данных."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_filters (user_id, filters)
        VALUES (?, ?)
    ''', (user_id, json.dumps(filters)))
    conn.commit()
    conn.close()

def get_user_filters(user_id):
    """Получает список ключевых фраз пользователя из базы данных."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT filters FROM user_filters
        WHERE user_id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return []

def get_all_user_ids():
    """Возвращает список всех пользователей из базы данных."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT user_id FROM users_accounts")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users
