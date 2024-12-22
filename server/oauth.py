import logging
from urllib.parse import urljoin
from flask import request
from google_auth_oauthlib.flow import Flow
from config import NGROK_URL, CLIENT_SECRETS_FILE, SCOPES
from server.db import save_credentials

logger = logging.getLogger(__name__)

def handle_oauth2_callback():
    """Обрабатывает запросы к маршруту /oauth2callback."""
    state = request.args.get('state')
    code = request.args.get('code')

    if not state or not code:
        logger.error("Некорректный запрос: отсутствует state или code.")
        return "Некорректный запрос.", 400

    user_id = state  # Предполагается, что state содержит user_id
    logger.info(f"Получен запрос авторизации от пользователя: {user_id}")

    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=urljoin(NGROK_URL, '/oauth2callback')
        )
        flow.fetch_token(code=code)

        credentials = flow.credentials
        account_id = credentials.token

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
