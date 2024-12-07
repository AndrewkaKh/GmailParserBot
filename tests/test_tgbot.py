# tests/test_tgbot.py
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from telegram import Update, User, Message, Chat
from telegram.ext import CallbackContext
from tgbot import start, get_emails, fetch_and_send_emails, button_handler


@pytest.fixture
def mock_update_start():
    user = User(id=12345, first_name='TestUser', is_bot=False)
    chat = Chat(id=12345, type='private')
    message = Message(message_id=1, date=None, chat=chat, text='/start', from_user=user)
    update = Update(update_id=1001, message=message)
    return update


@pytest.fixture
def mock_update_get_emails():
    user = User(id=12345, first_name='TestUser', is_bot=False)
    chat = Chat(id=12345, type='private')
    message = Message(message_id=2, date=None, chat=chat, text='/get_emails', from_user=user)
    update = Update(update_id=1002, message=message)
    return update


@pytest.fixture
def mock_update_button():
    user = User(id=12345, first_name='TestUser', is_bot=False)
    chat = Chat(id=12345, type='private')
    message = Message(message_id=3, date=None, chat=chat, text='CallbackQuery')
    callback_query = MagicMock()
    callback_query.data = 'account1'
    callback_query.from_user = user
    callback_query.message = message
    update = Update(update_id=1003, callback_query=callback_query)
    return update


@pytest.fixture
def mock_context():
    return CallbackContex(dispatcher=MagicMock())


@patch('tgbot.Flow')
@patch('tgbot.urljoin', return_value='https://ngrok-url/oauth2callback')
def test_start_command(mock_urljoin, mock_flow, mock_update_start, mock_context):
    with patch.object(mock_update_start.message, 'reply_text') as mock_reply:
        start(mock_update_start, mock_context)

        # Проверка вызова Flow
        mock_flow.from_client_secrets_file.assert_called_once_with(
            'client_secret4.json',
            scopes=['https://www.googleapis.com/auth/gmail.readonly'],
            redirect_uri='https://ngrok-url/oauth2callback'
        )

        # Проверка генерации URL авторизации
        mock_flow.from_client_secrets_file.return_value.authorization_url.assert_called_once()

        # Проверка отправки сообщения пользователю
        mock_reply.assert_called_once()
        args, kwargs = mock_reply.call_args
        assert "Пожалуйста, авторизуйтесь через Gmail" in args[0]


@patch('tgbot.get_user_accounts', return_value=['account1'])
@patch('tgbot.fetch_and_send_emails')
def test_get_emails_command_single_account(mock_fetch_emails, mock_get_user_accounts, mock_update_get_emails,
                                           mock_context):
    with patch.object(mock_update_get_emails.message, 'reply_text') as mock_reply:
        get_emails(mock_update_get_emails, mock_context)

        # Проверка получения аккаунтов пользователя
        mock_get_user_accounts.assert_called_once_with(12345)

        # Проверка вызова функции fetch_and_send_emails
        mock_fetch_and_send_emails.assert_called_once_with(
            mock_update_get_emails,
            mock_context,
            12345,
            'account1'
        )

        # Проверка отсутствия отправки дополнительных сообщений
        mock_reply.assert_not_called()


@patch('tgbot.get_user_accounts', return_value=['account1', 'account2'])
def test_get_emails_command_multiple_accounts(mock_get_user_accounts, mock_update_get_emails, mock_context):
    with patch.object(mock_update_get_emails.message, 'reply_text') as mock_reply:
        get_emails(mock_update_get_emails, mock_context)

        # Проверка получения аккаунтов пользователя
        mock_get_user_accounts.assert_called_once_with(12345)

        # Проверка отправки сообщения с клавиатурой
        mock_reply.assert_called_once()
        args, kwargs = mock_reply.call_args
        assert 'Выберите почтовый ящик' in args[0]
        assert isinstance(kwargs['reply_markup'], MagicMock)  # Проверка типа клавиатуры


@patch('tgbot.fetch_and_send_emails')
def test_button_handler(mock_fetch_emails, mock_update_button, mock_context):
    with patch.object(mock_update_button.callback_query, 'answer') as mock_answer:
        button_handler(mock_update_button, mock_context)

        # Проверка ответа на нажатие кнопки
        mock_answer.assert_called_once()

        # Проверка вызова функции fetch_and_send_emails
        mock_fetch_emails.assert_called_once_with(
            mock_update_button.callback_query,
            mock_context,
            12345,
            'account1'
        )


@patch('tgbot.get_credentials', return_value={
    'token': 'mock_token',
    'refresh_token': 'mock_refresh_token',
    'token_uri': 'https://oauth2.googleapis.com/token',
    'client_id': 'mock_client_id',
    'client_secret': 'mock_client_secret',
    'scopes': ['https://www.googleapis.com/auth/gmail.readonly']
})
@patch('tgbot.build')
@patch('tgbot.save_credentials')
def test_fetch_and_send_emails_success(mock_save_credentials, mock_build, mock_get_credentials, mock_update_get_emails,
                                       mock_context):
    # Настройка мок-сервиса Gmail API
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        'messages': [{'id': 'msg1'}]
    }
    mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = {
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Test Subject'},
                {'name': 'From', 'value': 'sender@example.com'}
            ],
            'parts': [
                {'mimeType': 'text/plain', 'body': {'data': 'VGhpcyBpcyBhIHRlc3QgdGV4dC4='}}
                # "This is a test text." в base64url
            ]
        }
    }

    # Патчим функции обработки текста и классификации спама
    with patch('tgbot.send_processed_email') as mock_send_email:
        fetch_and_send_emails(mock_update_get_emails, mock_context, 12345, 'account1')

        # Проверка вызова Gmail API
        mock_service.users.return_value.messages.return_value.list.assert_called_once_with(
            userId='me', q='is:unread', maxResults=1
        )
        mock_service.users.return_value.messages.return_value.get.assert_called_once_with(
            userId='me', id='msg1', format='full'
        )

        # Проверка вызова функции отправки письма
        mock_send_email.assert_called_once()

        # Проверка отправки сообщения о результате классификации
        with patch.object(mock_update_get_emails.message, 'reply_text') as mock_reply:
            mock_reply.assert_called_once_with("Текст письма получен. Вердикт классификатора: НЕ СПАМ")


@patch('tgbot.get_credentials', return_value=None)
def test_fetch_and_send_emails_no_credentials(mock_get_credentials, mock_update_get_emails, mock_context):
    with patch.object(mock_update_get_emails.message, 'reply_text') as mock_reply:
        fetch_and_send_emails(mock_update_get_emails, mock_context, 12345, 'account1')

        # Проверка вызова get_credentials
        mock_get_credentials.assert_called_once_with(12345, 'account1')

        # Проверка отправки сообщения об отсутствии токенов
        mock_reply.assert_called_once_with("Токены не найдены. Пожалуйста, авторизуйтесь заново с /start.")


@patch('tgbot.get_credentials', return_value={
    'token': 'expired_token',
    'refresh_token': 'mock_refresh_token',
    'token_uri': 'https://oauth2.googleapis.com/token',
    'client_id': 'mock_client_id',
    'client_secret': 'mock_client_secret',
    'scopes': ['https://www.googleapis.com/auth/gmail.readonly']
})
@patch('tgbot.build')
@patch('tgbot.save_credentials')
@patch('tgbot.Credentials.refresh')
def test_fetch_and_send_emails_token_refresh(mock_refresh, mock_save_credentials, mock_build, mock_get_credentials,
                                             mock_update_get_emails, mock_context):
    # Настройка мок-сервиса Gmail API
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        'messages': []
    }

    # Настройка моков Credentials
    mock_credentials = MagicMock()
    mock_credentials.expired = True
    mock_credentials.refresh_token = 'mock_refresh_token'
    mock_credentials.token = 'new_mock_token'
    mock_credentials.refresh.return_value = None  # Успешное обновление токена

    with patch('tgbot.Credentials', return_value=mock_credentials):
        with patch.object(mock_update_get_emails.message, 'reply_text') as mock_reply:
            fetch_and_send_emails(mock_update_get_emails, mock_context, 12345, 'account1')

            # Проверка обновления токена
            mock_credentials.refresh.assert_called_once()

            # Проверка сохранения обновлённых токенов
            updated_credentials = {
                'token': 'new_mock_token',
                'refresh_token': 'mock_refresh_token',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'client_id': 'mock_client_id',
                'client_secret': 'mock_client_secret',
                'scopes': ['https://www.googleapis.com/auth/gmail.readonly']
            }
            mock_save_credentials.assert_called_once_with(12345, 'new_mock_token', updated_credentials)

            # Проверка вызова Gmail API
            mock_service.users.return_value.messages.return_value.list.assert_called_once_with(
                userId='me', q='is:unread', maxResults=1
            )

            # Проверка отправки сообщения об отсутствии новых писем
            mock_reply.assert_called_once_with("Нет новых сообщений.")


@patch('tgbot.get_credentials', side_effect=KeyError('token'))
def test_fetch_and_send_emails_invalid_credentials(mock_get_credentials, mock_update_get_emails, mock_context):
    with patch.object(mock_update_get_emails.message, 'reply_text') as mock_reply:
        fetch_and_send_emails(mock_update_get_emails, mock_context, 12345, 'account1')

        # Проверка отправки сообщения об ошибке учётных данных
        mock_reply.assert_called_once_with(
            "Некорректные учётные данные. Пожалуйста, авторизуйтесь заново с /start."
        )
