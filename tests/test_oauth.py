import json
import unittest
from unittest.mock import patch, MagicMock
from google.oauth2.credentials import Credentials
from bot.oauth import create_flow, get_auth_url, build_credentials_from_dict, refresh_credentials


class TestOAuthFunctions(unittest.TestCase):

    @patch('bot.oauth.Flow.from_client_secrets_file')
    @patch('bot.oauth.urljoin')
    def test_create_flow(self, mock_urljoin, mock_from_client_secrets_file):
        # Подготовка
        user_id = 'test_user'
        mock_urljoin.return_value = 'https://example.com/oauth2callback'

        # Вызов функции
        flow = create_flow(user_id)

        # Проверка
        mock_from_client_secrets_file.assert_called_once_with(
            'client_secret1.json',
            scopes=['https://www.googleapis.com/auth/gmail.modify'],
            redirect_uri='https://example.com/oauth2callback'
        )
        self.assertEqual(flow.user_id, user_id)

    @patch('bot.oauth.Flow.authorization_url')
    def test_get_auth_url(self, mock_authorization_url):
        # Подготовка
        mock_flow = MagicMock()
        mock_flow.user_id = 'test_user'
        mock_authorization_url.return_value = ('https://auth.url', 'state123')

        # Вызов функции
        auth_url, state = get_auth_url(mock_flow)

        # Проверка
        mock_authorization_url.assert_called_once_with(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state='test_user'
        )
        self.assertEqual(auth_url, 'https://auth.url')
        self.assertEqual(state, 'state123')

    def test_build_credentials_from_dict(self):
        # Подготовка
        credentials_dict = {
            'token': 'test_token',
            'refresh_token': 'test_refresh_token',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'scopes': ['https://www.googleapis.com/auth/gmail.modify']
        }

        # Вызов функции
        credentials = build_credentials_from_dict(credentials_dict)

        # Проверка
        self.assertIsInstance(credentials, Credentials)
        self.assertEqual(credentials.token, 'test_token')
        self.assertEqual(credentials.refresh_token, 'test_refresh_token')

    @patch('bot.oauth.Request')
    @patch('bot.oauth.Credentials.refresh')
    def test_refresh_credentials(self, mock_refresh, mock_request):
        # Подготовка
        mock_credentials = MagicMock()
        mock_credentials.expired = True
        mock_credentials.refresh_token = 'test_refresh_token'
        mock_credentials.token = 'new_token'

        save_callback = MagicMock()
        user_id = 'test_user'
        account_id = 'test_account'

        # Вызов функции
        refresh_credentials(mock_credentials, save_callback, user_id, account_id)

        # Проверка
        mock_refresh.assert_called_once_with(mock_request)
        save_callback.assert_called_once_with(
            user_id,
            account_id,
            {
                'token': 'new_token',
                'refresh_token': mock_credentials.refresh_token,
                'token_uri': mock_credentials.token_uri,
                'client_id': mock_credentials.client_id,
                'client_secret': mock_credentials.client_secret,
                'scopes': mock_credentials.scopes
            }
        )

    @patch('bot.oauth.Request')
    @patch('bot.oauth.Credentials.refresh')
    def test_refresh_credentials_no_refresh_token(self, mock_refresh, mock_request):
        # Подготовка
        mock_credentials = MagicMock()
        mock_credentials.expired = True