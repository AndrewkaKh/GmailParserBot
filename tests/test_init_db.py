import pytest
import sqlite3
from unittest.mock import patch
from init_db import init_db

@pytest.fixture
def in_memory_db():
    """Создаёт in-memory базу данных для тестирования."""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    yield conn, cursor
    conn.close()

@patch('init_db.sqlite3.connect')
def test_init_db(mock_connect, in_memory_db):
    conn, cursor = in_memory_db
    mock_connect.return_value = conn


    init_db()


    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users_accounts';")
    table = cursor.fetchone()
    assert table is not None, "Таблица 'users_accounts' не создана."

    # Проверка структуры таблицы
    cursor.execute("PRAGMA table_info(users_accounts);")
    columns = cursor.fetchall()
    expected_columns = [
        (0, 'user_id', 'INTEGER', 0, None, 0),
        (1, 'account_id', 'TEXT', 0, None, 0),
        (2, 'credentials', 'TEXT', 0, None, 0)
    ]
    assert columns == expected_columns, "Структура таблицы 'users_accounts' неверна."
