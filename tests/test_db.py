import unittest
import os
import json
import sqlite3

from bot.db import init_db, save_credentials, get_credentials, get_user_accounts, save_user_filters, \
    get_user_filters

DB_FILE = 'test_users.db'


class TestUserDatabase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Создает базу данных перед запуском тестов."""
        cls.db_file = DB_FILE
        init_db()

    @classmethod
    def tearDownClass(cls):
        """Удаляет базу данных после завершения тестов."""
        if os.path.exists(cls.db_file):
            os.remove(cls.db_file)

    def test_save_and_get_credentials(self):
        """Тестирование сохранения и получения учетных данных."""
        user_id = 1
        account_id = 'account_1'
        credentials = {'username': 'test_user', 'password': 'test_pass'}

        save_credentials(user_id, account_id, credentials)
        retrieved_credentials = get_credentials(user_id, account_id)

        self.assertEqual(retrieved_credentials, credentials)

    def test_get_credentials_non_existent(self):
        """Тестирование получения учетных данных для несуществующего аккаунта."""
        user_id = 1
        account_id = 'non_existent_account'

        retrieved_credentials = get_credentials(user_id, account_id)
        self.assertIsNone(retrieved_credentials)

    def test_save_and_get_user_filters(self):
        """Тестирование сохранения и получения фильтров пользователя."""
        user_id = 1
        filters = ['filter1', 'filter2', 'filter3']

        save_user_filters(user_id, filters)
        retrieved_filters = get_user_filters(user_id)

        self.assertEqual(retrieved_filters, filters)

    def test_get_user_filters_non_existent(self):
        """Тестирование получения фильтров для несуществующего пользователя."""
        user_id = 2

        retrieved_filters = get_user_filters(user_id)
        self.assertEqual(retrieved_filters, [])

    def test_get_user_accounts(self):
        """Тестирование получения списка аккаунтов пользователя."""
        user_id = 1
        account_ids = ['account_1', 'account_2']

        for account_id in account_ids:
            save_credentials(user_id, account_id, {'username': 'test_user', 'password': 'test_pass'})

        retrieved_accounts = get_user_accounts(user_id)

        self.assertCountEqual(retrieved_accounts, account_ids)

    def test_get_user_accounts_no_accounts(self):
        """Тестирование получения аккаунтов для пользователя без аккаунтов."""
        user_id = 3

        retrieved_accounts = get_user_accounts(user_id)

        self.assertEqual(retrieved_accounts, [])


if __name__ == '__main__':
    unittest.main()