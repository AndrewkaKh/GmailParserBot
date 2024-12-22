import json
from urllib.parse import urljoin

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
CLIENT_SECRETS_FILE = 'client_secret1.json'
NGROK_URL = 'https://bf3a-5-34-215-156.ngrok-free.app'  # Замените на ваш актуальный URL

def create_flow(user_id):
    """Создает OAuth2 Flow для авторизации пользователя."""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=urljoin(NGROK_URL, '/oauth2callback')
    )
    flow.user_id = user_id  # Сохраняем user_id для использования в state
    return flow

def get_auth_url(flow):
    """Получает URL для авторизации."""
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=str(flow.user_id)
    )
    return auth_url, state

def build_credentials_from_dict(credentials_dict):
    """Создает объект Credentials из словаря."""
    return Credentials(
        token=credentials_dict['token'],
        refresh_token=credentials_dict['refresh_token'],
        token_uri=credentials_dict['token_uri'],
        client_id=credentials_dict['client_id'],
        client_secret=credentials_dict['client_secret'],
        scopes=credentials_dict['scopes']
    )

def refresh_credentials(credentials, save_callback, user_id, account_id):
    """Обновляет токены и вызывает callback для сохранения."""
    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
            # Сохранение обновленных токенов
            creds_dict = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            save_callback(user_id, account_id, creds_dict)
        except Exception as e:
            raise Exception(f"Ошибка обновления токена: {e}")
