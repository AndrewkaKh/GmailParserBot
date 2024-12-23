import unittest
from unittest.mock import MagicMock, patch
from bot.gmail import fetch_unread_emails, fetch_email_details, extract_email_body

class TestGmailAPI(unittest.TestCase):

    @patch('bot.gmail.build')
    def test_fetch_unread_emails(self, mock_build):
        """Тестирование получения непрочитанных сообщений."""
        # Создаем мок-сервис
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Настраиваем возврат для метода list()
        mock_service.users().messages().list.return_value.execute.return_value = {
            'messages': [{'id': '123'}, {'id': '456'}]
        }

        # Вызываем функцию
        emails = fetch_unread_emails(mock_service)

        # Проверяем результаты
        self.assertEqual(len(emails), 2)
        self.assertEqual(emails[0]['id'], '123')
        self.assertEqual(emails[1]['id'], '456')

    @patch('bot.gmail.build')
    def test_fetch_email_details(self, mock_build):
        """Тестирование получения деталей письма по ID."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Настраиваем возврат для метода get()
        mock_service.users().messages().get.return_value.execute.return_value = {
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Test Subject'},
                    {'name': 'From', 'value': 'test@example.com'},
                ],
                'parts': [],
                'body': {
                    'data': 'SGVsbG8gd29ybGQ='
                }
            }
        }

        # Вызываем функцию
        email_details = fetch_email_details(mock_service, '123')

        # Проверяем результаты
        self.assertEqual(email_details['id'], '123')
        self.assertEqual(email_details['subject'], 'Test Subject')
        self.assertEqual(email_details['from'], 'test@example.com')
        self.assertEqual(email_details['body'], 'Hello world')

    def test_extract_email_body(self):
        """Тестирование извлечения тела письма."""
        message = {
            'payload': {
                'parts': [{
                    'mimeType': 'text/plain',
                    'body': {
                        'data': 'SGVsbG8gd29ybGQ='
                    }
                }]
            }
        }

        body = extract_email_body(message)
        self.assertEqual(body, 'Hello world')

    def test_extract_email_body_no_parts(self):
        """Тестирование извлечения тела письма без частей."""
        message = {
            'payload': {
                'body': {
                    'data': 'SGVsbG8gd29ybGQ='
                }
            }
        }

        body = extract_email_body(message)
        self.assertEqual(body, 'Hello world')

    def test_extract_email_body_no_body(self):
        """Тестирование извлечения тела письма без тела."""
        message = {
            'payload': {}
        }

        body = extract_email_body(message)
        self.assertEqual(body, "Текст письма отсутствует.")

    def test_decode_base64(self):
        """Тестирование декодирования base64."""
        data = 'SGVsbG8gd29ybGQ='  # "Hello world"
        decoded = decode_base64(data)
        self.assertEqual(decoded, 'Hello world')

    def test_decode_base64_invalid(self):
        """Тестирование декодирования некорректных данных."""
        data = 'InvalidBase64'
        decoded = decode_base64(data)
        self.assertEqual(decoded, "Не удалось декодировать текст.")

if __name__ == '__main__':
    unittest.main()