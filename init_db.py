# init_db.py
import sqlite3

def init_db():
    conn = sqlite3.connect('users.db')
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

if __name__ == '__main__':
    init_db()
    print("База данных инициализирована.")
