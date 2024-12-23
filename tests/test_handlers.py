import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update
from bot.handlers import start, get_emails, button_handler, fetch_and_send_emails


class TestBotFunctions(unittest.TestCase):

    @patch('bot.oauth.db.get_user_accounts')
    @patch('bot.oauth.create_flow')
    @patch('bot.oauth.get_auth_url')
    async def test_start_already_authorized(self, mock_get_auth_url, mock_create_flow):
        # Подготовка
        user_id = 123
        mock_update = MagicMock(spec=Update)
        mock_update.effective_user.id = user_id
        mock_get_user_accounts.return_value = ['account1']

        # Вызов функции
        await start(mock_update, AsyncMock())

        # Проверка результатов
        mock_update.message.reply_text.assert_called_once_with(
            "Вы уже авторизованы. Используйте /get_emails для получения писем."
        )

    @patch('bot.db.get_user_accounts')
    async def test_get_emails_no_accounts(self, mock_get_user_accounts):
        # Подготовка
        user_id = 123
        mock_update = MagicMock(spec=Update)
        mock_update.effective_user.id = user_id
        mock_get_user_accounts.return_value = []

        # Вызов функции
        await get_emails(mock_update, AsyncMock())

        # Проверка результатов
        mock_update.message.reply_text.assert_called_once_with(
            "У вас нет привязанных почтовых ящиков. Используйте /start для авторизации."
        )

    @patch('bot.db.get_user_accounts')
    @patch('bot.fetch_and_send_emails')
    async def test_get_emails_with_one_account(self, mock_fetch_and_send_emails, mock_get_user_accounts):
        # Подготовка
        user_id = 123
        mock_update = MagicMock(spec=Update)
        mock_update.effective_user.id = user_id
        mock_get_user_accounts.return_value = ['account1']

        # Вызов функции
        await get_emails(mock_update, AsyncMock())

        # Проверка вызова fetch_and_send_emails
        mock_fetch_and_send_emails.assert_called_once_with(mock_update, AsyncMock(), user_id, 'account1')

    @patch('bot.fetch_and_send_emails')
    async def test_button_handler(self, mock_fetch_and_send_emails):
        # Подготовка
        user_id = 123
        account_id = 'account1'
        mock_query = MagicMock()
        mock_query.from_user.id = user_id
        mock_query.data = account_id
        mock_query.answer = AsyncMock()

        mock_update = MagicMock()
        mock_update.callback_query = mock_query

        # Вызов функции
        await button_handler(mock_update, AsyncMock())

        # Проверка вызова fetch_and_send_emails
        mock_fetch_and_send_emails.assert_called_once_with(mock_query, AsyncMock(), user_id, account_id)

    @patch('bot.db.get_credentials')
    @patch('bot.oauth.build_credentials_from_dict')
    @patch('bot.gmail.get_service')
    @patch('bot.gmail.fetch_unread_emails')
    @patch('bot.gmail.fetch_email_details')
    async def test_fetch_and_send_emails_no_credentials(self, mock_fetch_email_details, mock_fetch_unread_emails,
                                                        mock_get_service, mock_build_credentials_from_dict,
                                                        mock_get_credentials):
        # Подготовка
        user_id = 123
        account_id = 'account1'
        mock_update = MagicMock()

        mock_get_credentials.return_value = None

        # Вызов функции
        await fetch_and_send_emails(mock_update, AsyncMock(), user_id, account_id)

        # Проверка результата
        mock_update.message.reply_text.assert_called_once_with(
            "Токены не найдены. Пожалуйста, авторизуйтесь заново с /start.")


# Запуск тестов
if __name__ == '__main__':
    unittest.main()
