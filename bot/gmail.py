import base64
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

def get_service(credentials):
    """Создает Gmail API сервис."""
    return build('gmail', 'v1', credentials=credentials)

def fetch_unread_emails(service, max_results=1):
    """Получает список непрочитанных сообщений."""
    try:
        results = service.users().messages().list(userId='me', q='is:unread', maxResults=max_results).execute()
        return results.get('messages', [])
    except HttpError as e:
        logger.error(f"Ошибка получения сообщений: {e}")
        return []

def fetch_email_details(service, message_id):
    """Получает детали письма по ID."""
    try:
        message = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        headers = message.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Без темы')
        from_ = next((h['value'] for h in headers if h['name'] == 'From'), 'Неизвестно')
        return {
            "id": message_id,
            "subject": subject,
            "from": from_,
            "body": extract_email_body(message)
        }
    except HttpError as e:
        logger.error(f"Ошибка получения письма {message_id}: {e}")
        return None

def extract_email_body(message):
    """Извлекает текст из тела письма."""
    try:
        payload = message.get('payload', {})
        parts = payload.get('parts', [])
        if not parts:
            body_data = payload.get('body', {}).get('data', '')
            return decode_base64(body_data)

        for part in parts:
            if part.get('mimeType') == 'text/plain':
                body_data = part.get('body', {}).get('data', '')
                return decode_base64(body_data)
        return "Текст письма отсутствует."
    except Exception as e:
        logger.error(f"Ошибка извлечения тела письма: {e}")
        return "Ошибка извлечения текста письма."

def decode_base64(data):
    """Декодирует строку в формате base64."""
    try:
        decoded_bytes = base64.urlsafe_b64decode(data + '==')
        return decoded_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"Ошибка декодирования данных: {e}")
        return "Не удалось декодировать текст."
